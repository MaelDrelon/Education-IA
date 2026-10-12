from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import require_apprenant, require_staff
from ..db import get_db
from ..models import Attempt, Exam, Exercise, Status, User
from ..permissions import owned_exercise
from ..schemas import AttemptIn, AttemptOut, GradeIn
from ..scoring import auto_score

router = APIRouter(tags=["tentatives"])


@router.post("/attempts", response_model=AttemptOut, status_code=201)
def submit_attempt(data: AttemptIn, db: Session = Depends(get_db), user: User = Depends(require_apprenant)):
    exercise = db.get(Exercise, data.exercise_id)
    if not exercise or exercise.status != Status.publie:
        raise HTTPException(404, "Exercice introuvable")
    if data.exam_id is not None:
        exam = db.get(Exam, data.exam_id)
        if (not exam or exam.status != Status.publie
                or user.id not in {a.user_id for a in exam.assignments}):
            raise HTTPException(404, "Examen introuvable")
        if exercise.id not in {e.id for e in exam.exercises}:
            raise HTTPException(400, "Cet exercice ne fait pas partie de l'examen")
        if db.scalar(select(Attempt.id).where(Attempt.exam_id == exam.id, Attempt.user_id == user.id,
                                              Attempt.exercise_id == exercise.id)):
            raise HTTPException(409, "Exercice déjà rendu pour cet examen")
    attempt = Attempt(user_id=user.id, exercise_id=exercise.id, exam_id=data.exam_id,
                      answer=data.answer, score=auto_score(exercise, data.answer))
    db.add(attempt)
    db.commit()
    return attempt


@router.get("/attempts/me", response_model=list[AttemptOut])
def my_attempts(db: Session = Depends(get_db), user: User = Depends(require_apprenant)):
    return db.scalars(select(Attempt).where(Attempt.user_id == user.id)
                      .order_by(Attempt.submitted_at.desc())).all()


@router.get("/exercises/{exercise_id}/attempts", response_model=list[AttemptOut])
def exercise_attempts(exercise_id: int, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    owned_exercise(db, exercise_id, user)
    return db.scalars(select(Attempt).where(Attempt.exercise_id == exercise_id)
                      .order_by(Attempt.submitted_at.desc())).all()


@router.patch("/attempts/{attempt_id}/grade", response_model=AttemptOut)
def grade_attempt(attempt_id: int, data: GradeIn, db: Session = Depends(get_db),
                  user: User = Depends(require_staff)):
    """Correction manuelle (code, texte libre)."""
    attempt = db.get(Attempt, attempt_id)
    if not attempt:
        raise HTTPException(404, "Tentative introuvable")
    owned_exercise(db, attempt.exercise_id, user)
    attempt.score = data.score
    db.commit()
    return attempt
