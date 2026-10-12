from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_staff
from ..db import get_db
from ..models import Assignment, Attempt, Course, Exam, Exercise, Lesson, Role, Status, User
from ..permissions import owned_course, owned_exam
from ..schemas import AssignIn, ExamIn, ExerciseOut, ExercisePublic

router = APIRouter(tags=["examens"])


def exam_view(exam: Exam, staff: bool, done_ids: list[int] | None = None) -> dict:
    data = {
        "id": exam.id, "course_id": exam.course_id, "title": exam.title,
        "scheduled_at": exam.scheduled_at, "duration_minutes": exam.duration_minutes,
        "status": exam.status,
    }
    if staff:
        data["exercises"] = [ExerciseOut.model_validate(e) for e in exam.exercises]
        data["assigned_user_ids"] = [a.user_id for a in exam.assignments]
    else:
        data["exercises"] = [ExercisePublic.model_validate(e) for e in exam.exercises]
        data["done_exercise_ids"] = done_ids or []
    return data


@router.get("/exams")
def list_exams(course_id: int | None = None, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    if user.role == Role.apprenant:
        q = (select(Exam).join(Assignment).where(Assignment.user_id == user.id,
                                                 Exam.status == Status.publie))
    else:
        q = select(Exam).join(Course)
        if user.role == Role.formateur:
            q = q.where(Course.owner_id == user.id)
    if course_id:
        q = q.where(Exam.course_id == course_id)
    exams = db.scalars(q.order_by(Exam.scheduled_at.desc())).all()
    staff = user.role != Role.apprenant
    return [exam_view(e, staff) for e in exams]


@router.post("/courses/{course_id}/exams", status_code=201)
def create_exam(course_id: int, data: ExamIn, db: Session = Depends(get_db),
                user: User = Depends(require_staff)):
    owned_course(db, course_id, user)
    exercises = db.scalars(
        select(Exercise).join(Lesson)
        .where(Exercise.id.in_(data.exercise_ids), Lesson.course_id == course_id)).all()
    if len(exercises) != len(set(data.exercise_ids)):
        raise HTTPException(400, "Certains exercices n'existent pas ou n'appartiennent pas à ce cours")
    if any(e.status != Status.publie for e in exercises):
        raise HTTPException(400, "Un examen ne peut contenir que des exercices validés (publiés)")
    exam = Exam(course_id=course_id, title=data.title, scheduled_at=data.scheduled_at.replace(tzinfo=None),
                duration_minutes=data.duration_minutes, exercises=list(exercises))
    db.add(exam)
    db.commit()
    return exam_view(exam, staff=True)


@router.get("/exams/{exam_id}")
def get_exam(exam_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == Role.apprenant:
        exam = db.get(Exam, exam_id)
        assigned = exam and any(a.user_id == user.id for a in exam.assignments)
        if not exam or exam.status != Status.publie or not assigned:
            raise HTTPException(404, "Examen introuvable")
        done = db.scalars(select(Attempt.exercise_id).where(
            Attempt.exam_id == exam_id, Attempt.user_id == user.id)).all()
        return exam_view(exam, staff=False, done_ids=sorted(set(done)))
    return exam_view(owned_exam(db, exam_id, user), staff=True)


@router.post("/exams/{exam_id}/assign")
def assign_exam(exam_id: int, data: AssignIn, db: Session = Depends(get_db),
                user: User = Depends(require_staff)):
    exam = owned_exam(db, exam_id, user)
    learners = db.scalars(select(User).where(User.id.in_(data.user_ids),
                                             User.role == Role.apprenant)).all()
    if len(learners) != len(set(data.user_ids)):
        raise HTTPException(400, "Seuls des apprenants existants peuvent être assignés")
    already = {a.user_id for a in exam.assignments}
    for learner in learners:
        if learner.id not in already:
            db.add(Assignment(exam_id=exam.id, user_id=learner.id))
    db.commit()
    db.refresh(exam)
    return exam_view(exam, staff=True)


@router.post("/exams/{exam_id}/publish")
def publish_exam(exam_id: int, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    exam = owned_exam(db, exam_id, user)
    exam.status = Status.publie
    db.commit()
    return exam_view(exam, staff=True)
