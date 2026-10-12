"""Usage 1 — génération d'exercices.

On force une sortie structurée via un « outil » (tool_choice) plutôt que de parser du JSON libre :
le modèle remplit un schéma, le back revalide chaque exercice, et tout est enregistré en brouillon.
"""
from ..config import settings
from . import ollama
from .llm import anthropic_client, use_fake

EXERCISE_TOOL = {
    "name": "proposer_exercices",
    "description": "Enregistre des exercices proposés. Ils seront relus par un formateur avant publication.",
    "input_schema": {
        "type": "object",
        "properties": {
            "exercices": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Titre court"},
                        "statement": {"type": "string", "description": "Énoncé complet, en Markdown"},
                        "type": {"type": "string", "enum": ["qcm", "code", "texte"]},
                        "choices": {"type": "array", "items": {"type": "string"},
                                    "description": "Obligatoire si type=qcm (3 ou 4 choix), sinon omis"},
                        "solution": {"type": "string",
                                     "description": "Corrigé. Pour un QCM : le texte EXACT du bon choix."},
                        "notion": {"type": "string",
                                   "description": "Notion travaillée, 1 à 3 mots (ex. 'boucle for')"},
                    },
                    "required": ["title", "statement", "type", "solution", "notion"],
                },
            }
        },
        "required": ["exercices"],
    },
}

SYSTEM = (
    "Tu es un assistant pédagogique qui aide un formateur à préparer des exercices. "
    "Tu écris en français, des énoncés clairs et sans ambiguïté, adaptés au niveau demandé. "
    "Chaque exercice a un corrigé exact. Reste dans le périmètre de la leçon fournie. "
    "Utilise des notions courtes et réutilisables d'un exercice à l'autre, car elles servent ensuite "
    "à analyser sur quoi la classe bloque."
)


def generate_exercises(consigne: str, count: int, difficulty: str, type_: str | None,
                       lesson_title: str, lesson_content: str) -> list[dict]:
    if use_fake():
        return _fake(consigne, count, type_)

    prompt = (
        f"Leçon : {lesson_title}\n\n"
        f"Contenu de la leçon :\n{lesson_content[:8000] or '(vide)'}\n\n"
        f"Consigne du formateur : {consigne}\n"
        f"Nombre d'exercices : {count}\n"
        f"Niveau : {difficulty}\n"
        + (f"Type imposé : {type_}\n" if type_ else "Types au choix : qcm, code ou texte\n")
    )
    if settings.llm_provider == "ollama":
        data = ollama.structured(SYSTEM, prompt, EXERCISE_TOOL["input_schema"])
        return list(data.get("exercices", []))[:count]

    response = anthropic_client().messages.create(
        model=settings.llm_model,
        max_tokens=8000,
        system=SYSTEM,
        tools=[EXERCISE_TOOL],
        tool_choice={"type": "tool", "name": EXERCISE_TOOL["name"]},
        messages=[{"role": "user", "content": prompt}],
    )
    block = next(b for b in response.content if b.type == "tool_use")
    return list(block.input.get("exercices", []))[:count]


def _fake(consigne: str, count: int, type_: str | None) -> list[dict]:
    items = []
    for i in range(1, count + 1):
        if (type_ or "qcm") == "qcm":
            items.append({
                "title": f"[Simulé] Question {i}",
                "statement": f"Exercice simulé à partir de la consigne : « {consigne} ».",
                "type": "qcm", "choices": ["Réponse A", "Réponse B", "Réponse C"],
                "solution": "Réponse A", "notion": "notion simulée",
            })
        else:
            items.append({
                "title": f"[Simulé] Exercice {i}",
                "statement": f"Exercice simulé à partir de la consigne : « {consigne} ».",
                "type": type_, "solution": "Corrigé simulé", "notion": "notion simulée",
            })
    return items
