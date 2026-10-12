from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_staff
from ..db import get_db
from ..models import Lesson, Role, Status, User
from ..permissions import owned_exercise, owned_lesson
from ..schemas import ExerciseIn, ExerciseOut, ExercisePublic, ExerciseUpdate
from ..models import Exercise

router = APIRouter(tags=["exercices"])


@router.get("/lessons/{lesson_id}/exercises")
def list_exercises(lesson_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == Role.apprenant:
        lesson = db.get(Lesson, lesson_id)
        if not lesson or lesson.status != Status.publie:
            raise HTTPException(404, "Leçon introuvable")
        return [ExercisePublic.model_validate(e) for e in lesson.exercises if e.status == Status.publie]
    lesson = owned_lesson(db, lesson_id, user)
    return [ExerciseOut.model_validate(e) for e in lesson.exercises]


@router.post("/lessons/{lesson_id}/exercises", response_model=ExerciseOut, status_code=201)
def create_exercise(lesson_id: int, data: ExerciseIn, db: Session = Depends(get_db),
                    user: User = Depends(require_staff)):
    owned_lesson(db, lesson_id, user)
    exercise = Exercise(lesson_id=lesson_id, **data.model_dump())
    db.add(exercise)
    db.commit()
    return exercise


@router.patch("/exercises/{exercise_id}", response_model=ExerciseOut)
def update_exercise(exercise_id: int, data: ExerciseUpdate, db: Session = Depends(get_db),
                    user: User = Depends(require_staff)):
    exercise = owned_exercise(db, exercise_id, user)
    merged = ExerciseOut.model_validate(exercise).model_dump() | data.model_dump(exclude_none=True)
    validated = ExerciseIn.model_validate(merged)  # revalide la cohérence (ex. QCM)
    for field, value in validated.model_dump().items():
        setattr(exercise, field, value)
    db.commit()
    return exercise


@router.post("/exercises/{exercise_id}/publish", response_model=ExerciseOut)
def publish_exercise(exercise_id: int, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    """Validation humaine : seul un formateur fait passer un exercice (généré ou non) en publié."""
    exercise = owned_exercise(db, exercise_id, user)
    exercise.status = Status.publie
    db.commit()
    return exercise


@router.delete("/exercises/{exercise_id}", status_code=204)
def delete_exercise(exercise_id: int, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    exercise = owned_exercise(db, exercise_id, user)
    db.delete(exercise)
    db.commit()
