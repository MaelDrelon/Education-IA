from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_staff
from ..db import get_db
from ..models import Course, Exercise, Lesson, Role, Status, User
from ..permissions import owned_course, owned_lesson
from ..schemas import CourseIn, CourseOut, ExerciseOut, LessonIn, LessonOut, LessonUpdate

router = APIRouter(tags=["cours"])


@router.get("/courses", response_model=list[CourseOut])
def list_courses(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = select(Course).order_by(Course.id)
    if user.role == Role.formateur:
        q = q.where(Course.owner_id == user.id)
    return db.scalars(q).all()


@router.post("/courses", response_model=CourseOut, status_code=201)
def create_course(data: CourseIn, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    course = Course(**data.model_dump(), owner_id=user.id)
    db.add(course)
    db.commit()
    return course


@router.get("/courses/{course_id}/lessons", response_model=list[LessonOut])
def list_lessons(course_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == Role.apprenant:
        course = db.get(Course, course_id)
        if not course:
            raise HTTPException(404, "Cours introuvable")
        return [l for l in course.lessons if l.status == Status.publie]
    return owned_course(db, course_id, user).lessons


@router.post("/courses/{course_id}/lessons", response_model=LessonOut, status_code=201)
def create_lesson(course_id: int, data: LessonIn, db: Session = Depends(get_db),
                  user: User = Depends(require_staff)):
    owned_course(db, course_id, user)
    lesson = Lesson(course_id=course_id, **data.model_dump())
    db.add(lesson)
    db.commit()
    return lesson


@router.get("/courses/{course_id}/exercises", response_model=list[ExerciseOut])
def list_course_exercises(course_id: int, published_only: bool = False, db: Session = Depends(get_db),
                          user: User = Depends(require_staff)):
    """Pratique pour composer un examen à partir de toutes les leçons d'un cours."""
    owned_course(db, course_id, user)
    q = select(Exercise).join(Lesson).where(Lesson.course_id == course_id).order_by(Exercise.id)
    if published_only:
        q = q.where(Exercise.status == Status.publie)
    return db.scalars(q).all()


@router.get("/lessons/{lesson_id}", response_model=LessonOut)
def get_lesson(lesson_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == Role.apprenant:
        lesson = db.get(Lesson, lesson_id)
        if not lesson or lesson.status != Status.publie:
            raise HTTPException(404, "Leçon introuvable")
        return lesson
    return owned_lesson(db, lesson_id, user)


@router.patch("/lessons/{lesson_id}", response_model=LessonOut)
def update_lesson(lesson_id: int, data: LessonUpdate, db: Session = Depends(get_db),
                  user: User = Depends(require_staff)):
    lesson = owned_lesson(db, lesson_id, user)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(lesson, field, value)
    db.commit()
    return lesson


@router.post("/lessons/{lesson_id}/publish", response_model=LessonOut)
def publish_lesson(lesson_id: int, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    lesson = owned_lesson(db, lesson_id, user)
    lesson.status = Status.publie
    db.commit()
    return lesson
