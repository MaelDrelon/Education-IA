"""Usage 2 — chatbot d'analyse des résultats.

Choix d'architecture : le modèle n'écrit PAS de SQL. Il choisit parmi des requêtes d'analyse
écrites et testées à la main (« outils »), avec des paramètres typés. Avantages à défendre :
  - aucune injection / requête destructrice possible ;
  - le périmètre est imposé par le back (un formateur ne voit que SES cours) ;
  - les chiffres viennent de la base, pas du modèle : la trace des appels est renvoyée au front.
Pour ajouter une question, on ajoute un outil. Le text-to-SQL (sur un rôle Postgres en lecture
seule) reste une évolution possible pour les questions non prévues.
"""
import json
from datetime import timedelta

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import utcnow
from ..models import Assignment, Attempt, Course, Exam, Exercise, Lesson, Role, User
from ..schemas import AnalyzeOut, ToolTrace
from . import ollama
from .llm import anthropic_client, use_fake

MAX_TOOL_ROUNDS = 6


# --- Requêtes d'analyse ---------------------------------------------------------
def _scope(q, user: User):
    """Restreint toute requête aux cours du formateur (l'admin voit tout)."""
    return q.where(Course.owner_id == user.id) if user.role == Role.formateur else q


def lister_cours(db: Session, user: User) -> list[dict]:
    q = _scope(select(Course.id, Course.title), user).order_by(Course.id)
    return [{"course_id": r.id, "titre": r.title} for r in db.execute(q)]


def lister_examens(db: Session, user: User, depuis_jours: int | None = None) -> list[dict]:
    q = (select(Exam.id, Exam.title, Exam.scheduled_at, Course.title.label("cours"),
                func.count(distinct(Assignment.user_id)).label("nb_assignes"))
         .join(Course, Course.id == Exam.course_id)
         .outerjoin(Assignment, Assignment.exam_id == Exam.id)
         .group_by(Exam.id, Exam.title, Exam.scheduled_at, Course.title)
         .order_by(Exam.scheduled_at.desc()))
    if depuis_jours:
        q = q.where(Exam.scheduled_at >= utcnow() - timedelta(days=depuis_jours))
    return [{"exam_id": r.id, "titre": r.title, "date": r.scheduled_at.isoformat(timespec="minutes"),
             "cours": r.cours, "nb_assignes": r.nb_assignes} for r in db.execute(_scope(q, user))]


def taux_reussite_par_exercice(db: Session, user: User, course_id: int | None = None,
                               ordre: str = "asc", limite: int = 10, min_tentatives: int = 1) -> list[dict]:
    taux = func.avg(Attempt.score)
    q = (select(Exercise.id, Exercise.title, Exercise.notion,
                func.count(Attempt.id).label("nb"), taux.label("taux"))
         .join(Attempt, Attempt.exercise_id == Exercise.id)
         .join(Lesson, Lesson.id == Exercise.lesson_id)
         .join(Course, Course.id == Lesson.course_id)
         .where(Attempt.score.is_not(None))
         .group_by(Exercise.id, Exercise.title, Exercise.notion)
         .having(func.count(Attempt.id) >= min_tentatives)
         .order_by(taux.desc() if ordre == "desc" else taux.asc())
         .limit(min(max(limite, 1), 50)))
    if course_id:
        q = q.where(Course.id == course_id)
    return [{"exercise_id": r.id, "titre": r.title, "notion": r.notion, "nb_tentatives": r.nb,
             "taux_reussite": round(float(r.taux) * 100, 1)} for r in db.execute(_scope(q, user))]


def difficulte_par_notion(db: Session, user: User, course_id: int | None = None) -> list[dict]:
    taux = func.avg(Attempt.score)
    q = (select(Exercise.notion, func.count(Attempt.id).label("nb"),
                func.count(distinct(Attempt.user_id)).label("nb_apprenants"), taux.label("taux"))
         .join(Attempt, Attempt.exercise_id == Exercise.id)
         .join(Lesson, Lesson.id == Exercise.lesson_id)
         .join(Course, Course.id == Lesson.course_id)
         .where(Attempt.score.is_not(None))
         .group_by(Exercise.notion)
         .order_by(taux.asc()))
    if course_id:
        q = q.where(Course.id == course_id)
    return [{"notion": r.notion, "nb_tentatives": r.nb, "nb_apprenants": r.nb_apprenants,
             "taux_reussite": round(float(r.taux) * 100, 1)} for r in db.execute(_scope(q, user))]


def apprenants_examen_non_termine(db: Session, user: User, exam_id: int | None = None,
                                  depuis_jours: int = 7) -> list[dict]:
    q = select(Exam).join(Course, Course.id == Exam.course_id)
    if exam_id:
        q = q.where(Exam.id == exam_id)
    else:
        now = utcnow()
        q = q.where(Exam.scheduled_at >= now - timedelta(days=depuis_jours), Exam.scheduled_at <= now)
    results = []
    for exam in db.scalars(_scope(q, user)):
        total = len(exam.exercises)
        for assignment in exam.assignments:
            done = db.scalar(select(func.count(distinct(Attempt.exercise_id))).where(
                Attempt.exam_id == exam.id, Attempt.user_id == assignment.user_id)) or 0
            if done < total:
                results.append({"exam_id": exam.id, "examen": exam.title,
                                "apprenant": assignment.user.full_name, "email": assignment.user.email,
                                "exercices_rendus": done, "exercices_total": total})
    return results


def progression_apprenant(db: Session, user: User, recherche: str) -> list[dict]:
    """Résultats d'un apprenant (recherche par nom ou email), par notion."""
    taux = func.avg(Attempt.score)
    q = (select(User.full_name, Exercise.notion, func.count(Attempt.id).label("nb"), taux.label("taux"))
         .join(Attempt, Attempt.user_id == User.id)
         .join(Exercise, Exercise.id == Attempt.exercise_id)
         .join(Lesson, Lesson.id == Exercise.lesson_id)
         .join(Course, Course.id == Lesson.course_id)
         .where(Attempt.score.is_not(None),
                (User.full_name.ilike(f"%{recherche}%")) | (User.email.ilike(f"%{recherche}%")))
         .group_by(User.full_name, Exercise.notion)
         .order_by(User.full_name, taux.asc()))
    return [{"apprenant": r.full_name, "notion": r.notion, "nb_tentatives": r.nb,
             "taux_reussite": round(float(r.taux) * 100, 1)} for r in db.execute(_scope(q, user))]


# --- Déclaration des outils pour le modèle ---------------------------------------------
_course = {"course_id": {"type": "integer", "description": "Optionnel : restreindre à un cours"}}

TOOLS = [
    {"name": "lister_cours", "description": "Liste les cours accessibles (id et titre).",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "lister_examens",
     "description": "Liste les examens (id, titre, date, nb d'apprenants assignés), du plus récent au plus ancien.",
     "input_schema": {"type": "object", "properties": {
         "depuis_jours": {"type": "integer", "description": "Uniquement les examens des N derniers jours"}}}},
    {"name": "taux_reussite_par_exercice",
     "description": "Taux de réussite moyen (en %) par exercice, sur les tentatives corrigées.",
     "input_schema": {"type": "object", "properties": {
         **_course,
         "ordre": {"type": "string", "enum": ["asc", "desc"], "description": "asc = les plus ratés d'abord"},
         "limite": {"type": "integer", "description": "Nombre de lignes (défaut 10)"},
         "min_tentatives": {"type": "integer", "description": "Ignorer les exercices peu tentés"}}}},
    {"name": "difficulte_par_notion",
     "description": "Taux de réussite (en %) par notion, des plus difficiles aux plus maîtrisées.",
     "input_schema": {"type": "object", "properties": {**_course}}},
    {"name": "apprenants_examen_non_termine",
     "description": "Apprenants assignés à un examen qui n'ont pas rendu tous les exercices. "
                    "Sans exam_id : examens passés des N derniers jours.",
     "input_schema": {"type": "object", "properties": {
         "exam_id": {"type": "integer"},
         "depuis_jours": {"type": "integer", "description": "Défaut 7"}}}},
    {"name": "progression_apprenant",
     "description": "Résultats d'un apprenant par notion (recherche partielle sur nom ou email).",
     "input_schema": {"type": "object", "properties": {"recherche": {"type": "string"}},
                      "required": ["recherche"]}},
]

IMPLEMENTATIONS = {
    "lister_cours": lister_cours,
    "lister_examens": lister_examens,
    "taux_reussite_par_exercice": taux_reussite_par_exercice,
    "difficulte_par_notion": difficulte_par_notion,
    "apprenants_examen_non_termine": apprenants_examen_non_termine,
    "progression_apprenant": progression_apprenant,
}


def run_tool(name: str, args: dict, db: Session, user: User):
    func_ = IMPLEMENTATIONS.get(name)
    if not func_:
        return {"erreur": f"outil inconnu : {name}"}
    try:
        return func_(db, user, **args)
    except TypeError as exc:
        return {"erreur": f"paramètres invalides : {exc}"}


def _system_prompt() -> str:
    return (
        "Tu es l'assistant d'analyse d'une plateforme de formation. Tu réponds aux questions d'un "
        "formateur sur les résultats de ses apprenants, en français, de façon concise.\n"
        "Règles :\n"
        "- Les chiffres viennent UNIQUEMENT des outils. N'invente jamais une donnée.\n"
        "- Si les données sont insuffisantes (peu de tentatives, aucun résultat), dis-le.\n"
        "- Le taux de réussite est un pourcentage moyen sur les réponses corrigées.\n"
        "- Termine si utile par une piste pédagogique concrète, en la présentant comme une suggestion.\n"
        f"Date du jour : {utcnow().date().isoformat()}."
    )


# --- Boucle principale -----------------------------------------------------------------
def analyze(question: str, db: Session, user: User) -> AnalyzeOut:
    if use_fake():
        return _fake_analyze(question, db, user)
    if settings.llm_provider == "ollama":
        return _ollama_analyze(question, db, user)

    client = anthropic_client()
    messages = [{"role": "user", "content": question}]
    trace: list[ToolTrace] = []

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.messages.create(model=settings.llm_model, max_tokens=2000,
                                          system=_system_prompt(), tools=TOOLS, messages=messages)
        if response.stop_reason != "tool_use":
            answer = "".join(b.text for b in response.content if b.type == "text").strip()
            return AnalyzeOut(answer=answer, trace=trace)

        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type == "tool_use":
                output = run_tool(block.name, dict(block.input), db, user)
                trace.append(ToolTrace(name=block.name, input=dict(block.input), result=output))
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": json.dumps(output, ensure_ascii=False, default=str)})
        messages.append({"role": "user", "content": results})

    return AnalyzeOut(answer="Analyse interrompue : trop d'étapes. Reformulez la question.", trace=trace)


def _ollama_analyze(question: str, db: Session, user: User) -> AnalyzeOut:
    trace: list[ToolTrace] = []

    def execute(name: str, args: dict):
        output = run_tool(name, args, db, user)  # même périmètre et mêmes requêtes qu'avec Claude
        trace.append(ToolTrace(name=name, input=args, result=output))
        return output

    answer = ollama.tool_loop(_system_prompt(), question, TOOLS, execute, MAX_TOOL_ROUNDS)
    if answer is None:
        answer = "Analyse interrompue : trop d'étapes. Reformulez la question."
    return AnalyzeOut(answer=answer, trace=trace)


def _fake_analyze(question: str, db: Session, user: User) -> AnalyzeOut:
    """Routage par mots-clés, pour développer sans clé API. Renvoie les données brutes."""
    q = question.lower()
    if "notion" in q or "bloqu" in q:
        name, args = "difficulte_par_notion", {}
    elif "termin" in q or "pas fini" in q or "rendu" in q:
        name, args = "apprenants_examen_non_termine", {"depuis_jours": 7}
    elif "réussite" in q or "reussite" in q or "raté" in q or "difficile" in q:
        name, args = "taux_reussite_par_exercice", {"ordre": "asc", "limite": 5}
    else:
        name, args = "lister_examens", {}
    result = run_tool(name, args, db, user)
    lines = "\n".join(f"- {json.dumps(r, ensure_ascii=False, default=str)}" for r in result) or "- (aucune donnée)"
    answer = f"[Mode simulé — outil « {name} »]\n{lines}"
    return AnalyzeOut(answer=answer, trace=[ToolTrace(name=name, input=args, result=result)])
