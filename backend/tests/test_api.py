import os
import tempfile

_db_file = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file}"
os.environ["LLM_PROVIDER"] = "fake"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import seed  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    seed.run()
    with TestClient(app) as c:
        yield c


def login(client, email):
    r = client.post("/auth/login", data={"username": email, "password": seed.PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_apprenant_ne_voit_pas_le_corrige(client):
    h = login(client, "alice@demo.fr")
    exams = client.get("/exams", headers=h).json()
    assert exams and "solution" not in exams[0]["exercises"][0]


def test_apprenant_interdit_sur_ia(client):
    h = login(client, "alice@demo.fr")
    assert client.post("/ai/analyze", json={"question": "test ?"}, headers=h).status_code == 403


def test_generation_en_brouillon_puis_publication(client):
    h = login(client, "formateur@demo.fr")
    lesson_id = client.get("/courses/1/lessons", headers=h).json()[0]["id"]
    r = client.post("/ai/generate", headers=h,
                    json={"lesson_id": lesson_id, "consigne": "boucles", "count": 2})
    created = r.json()["created"]
    assert len(created) == 2 and all(e["status"] == "brouillon" and e["generated_by_ai"] for e in created)

    # L'apprenant ne voit pas les brouillons
    ha = login(client, "alice@demo.fr")
    visibles = {e["id"] for e in client.get(f"/lessons/{lesson_id}/exercises", headers=ha).json()}
    assert created[0]["id"] not in visibles

    # Un examen refuse un exercice non validé
    r = client.post("/courses/1/exams", headers=h, json={
        "title": "x", "scheduled_at": "2026-12-01T10:00:00", "exercise_ids": [created[0]["id"]]})
    assert r.status_code == 400

    assert client.post(f"/exercises/{created[0]['id']}/publish", headers=h).json()["status"] == "publie"


def test_tentative_qcm_corrigee_automatiquement(client):
    h = login(client, "chloe@demo.fr")
    exam = client.get("/exams", headers=h).json()[0]
    ex = exam["exercises"][0]
    r = client.post("/attempts", headers=h, json={"exercise_id": ex["id"], "exam_id": exam["id"],
                                                  "answer": "0, 1, 2"})
    assert r.status_code == 201 and r.json()["score"] == 1.0
    # Pas de double rendu
    r = client.post("/attempts", headers=h, json={"exercise_id": ex["id"], "exam_id": exam["id"],
                                                  "answer": "0, 1, 2"})
    assert r.status_code == 409


def test_analyse(client):
    h = login(client, "formateur@demo.fr")
    r = client.post("/ai/analyze", headers=h, json={"question": "Sur quelle notion la classe bloque-t-elle ?"})
    result = r.json()["trace"][0]["result"]
    assert result[0]["notion"] == "break / continue" and result[0]["taux_reussite"] == 0.0

    r = client.post("/ai/analyze", headers=h,
                    json={"question": "Qui n'a pas terminé l'examen de la semaine dernière ?"})
    noms = {row["apprenant"] for row in r.json()["trace"][0]["result"]}
    assert "Bob Durand" in noms and "Alice Martin" not in noms


def test_formateur_isole(client):
    ha = login(client, "admin@demo.fr")
    client.post("/users", headers=ha, json={"email": "autre@demo.fr", "full_name": "Autre",
                                            "password": "abcd", "role": "formateur"})
    h = login_custom(client, "autre@demo.fr", "abcd")
    assert client.get("/courses/1/lessons", headers=h).status_code == 403
    r = client.post("/ai/analyze", headers=h, json={"question": "notion qui bloque ?"})
    assert r.json()["trace"][0]["result"] == []


def login_custom(client, email, password):
    r = client.post("/auth/login", data={"username": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# --- Fournisseur Ollama (serveur simulé) ---------------------------------------------
def test_ollama_analyse_boucle_outils(client, monkeypatch):
    from app.ai import ollama
    from app.config import settings

    calls = []

    def fake_chat(messages, **extra):
        calls.append(messages)
        if messages[-1]["role"] == "user":  # 1er tour : le modèle appelle un outil
            return {"role": "assistant", "content": "", "tool_calls": [
                {"function": {"name": "difficulte_par_notion", "arguments": {}}}]}
        assert messages[-1]["role"] == "tool" and messages[-1]["tool_name"] == "difficulte_par_notion"
        return {"role": "assistant", "content": "La notion la plus difficile est break / continue."}

    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(ollama, "_chat", fake_chat)
    h = login(client, "formateur@demo.fr")
    r = client.post("/ai/analyze", headers=h, json={"question": "Quelle notion bloque ?"})
    body = r.json()
    assert r.status_code == 200 and "break / continue" in body["answer"]
    assert body["trace"][0]["result"][0]["notion"] == "break / continue"
    assert len(calls) == 2


def test_ollama_generation_json(client, monkeypatch):
    import json as _json
    from app.ai import ollama
    from app.config import settings

    def fake_chat(messages, **extra):
        assert extra["format"]["required"] == ["exercices"]
        return {"role": "assistant", "content": _json.dumps({"exercices": [
            {"title": "T", "statement": "S", "type": "qcm", "choices": ["a", "b"], "solution": "a", "notion": "n"},
            {"title": "T2", "statement": "S", "type": "qcm", "choices": ["a", "b"], "solution": "z", "notion": "n"},
        ]})}

    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(ollama, "_chat", fake_chat)
    h = login(client, "formateur@demo.fr")
    r = client.post("/ai/generate", headers=h, json={"lesson_id": 1, "consigne": "x", "count": 2})
    assert r.json()["rejected"] == 1 and len(r.json()["created"]) == 1  # corrigé hors des choix -> écarté
