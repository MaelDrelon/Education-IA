"""Contrôles d'appartenance : un formateur n'agit que sur SES cours. L'admin voit tout."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from .models import Course, Exam, Exercise, Lesson, Role, User


def _404(what: str):
    return HTTPException(404, f"{what} introuvable")


def owned_course(db: Session, course_id: int, user: User) -> Course:
    course = db.get(Course, course_id)
    if not course:
        raise _404("Cours")
    if user.role == Role.formateur and course.owner_id != user.id:
        raise HTTPException(403, "Ce cours ne vous appartient pas")
    return course


def owned_lesson(db: Session, lesson_id: int, user: User) -> Lesson:
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise _404("Leçon")
    owned_course(db, lesson.course_id, user)
    return lesson


def owned_exercise(db: Session, exercise_id: int, user: User) -> Exercise:
    exercise = db.get(Exercise, exercise_id)
    if not exercise:
        raise _404("Exercice")
    owned_lesson(db, exercise.lesson_id, user)
    return exercise


def owned_exam(db: Session, exam_id: int, user: User) -> Exam:
    exam = db.get(Exam, exam_id)
    if not exam:
        raise _404("Examen")
    owned_course(db, exam.course_id, user)
    return exam
