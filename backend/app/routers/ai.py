from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from ..ai.analysis import analyze
from ..ai.generation import generate_exercises
from ..auth import require_staff
from ..db import get_db
from ..models import Exercise, Status, User
from ..permissions import owned_lesson
from ..schemas import AnalyzeIn, AnalyzeOut, ExerciseIn, ExerciseOut, GenerateIn, GenerateOut

router = APIRouter(prefix="/ai", tags=["ia"])


@router.post("/generate", response_model=GenerateOut)
def generate(data: GenerateIn, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    """Usage 1 : génération. Tout arrive en BROUILLON, le formateur relit puis publie."""
    lesson = owned_lesson(db, data.lesson_id, user)
    try:
        proposals = generate_exercises(
            consigne=data.consigne, count=data.count, difficulty=data.difficulty.value,
            type_=data.type.value if data.type else None,
            lesson_title=lesson.title, lesson_content=lesson.content)
    except Exception as exc:  # erreur réseau / quota / clé
        raise HTTPException(502, f"Échec de la génération : {exc}")

    created, rejected = [], 0
    for item in proposals:
        try:
            valid = ExerciseIn.model_validate({**item, "difficulty": data.difficulty})
        except ValidationError:
            rejected += 1
            continue
        exercise = Exercise(lesson_id=lesson.id, status=Status.brouillon, generated_by_ai=True,
                            **valid.model_dump())
        db.add(exercise)
        created.append(exercise)
    db.commit()
    return GenerateOut(created=[ExerciseOut.model_validate(e) for e in created], rejected=rejected)


@router.post("/analyze", response_model=AnalyzeOut)
def analyze_endpoint(data: AnalyzeIn, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    """Usage 2 : analyse des résultats, limitée aux cours du formateur."""
    try:
        return analyze(data.question, db, user)
    except Exception as exc:
        raise HTTPException(502, f"Échec de l'analyse : {exc}")
