"""Modèle de données.

Tables du modèle minimal : users, courses, lessons, exercises, exams, attempts.
Ajouts indispensables pour que les questions du chatbot aient une réponse :
  - exercises.notion       -> « sur quelle notion la classe bloque-t-elle ? »
  - assignments            -> « qui n'a pas terminé l'examen ? » (il faut savoir qui devait le passer)
  - status (brouillon/publié) + generated_by_ai -> l'humain valide avant publication
"""
import enum
from datetime import datetime

from sqlalchemy import (JSON, Column, DateTime, Enum, Float, ForeignKey, String, Table, Text,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, utcnow


class Role(str, enum.Enum):
    admin = "admin"
    formateur = "formateur"
    apprenant = "apprenant"


class ExerciseType(str, enum.Enum):
    qcm = "qcm"
    code = "code"
    texte = "texte"


class Difficulty(str, enum.Enum):
    debutant = "debutant"
    intermediaire = "intermediaire"
    avance = "avance"


class Status(str, enum.Enum):
    brouillon = "brouillon"
    publie = "publie"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Course(Base):
    """Une matière (ex. « Python — débutant »)."""
    __tablename__ = "courses"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    lessons: Mapped[list["Lesson"]] = relationship(
        back_populates="course", cascade="all, delete-orphan", order_by="Lesson.position")
    exams: Mapped[list["Exam"]] = relationship(back_populates="course", cascade="all, delete-orphan")


class Lesson(Base):
    __tablename__ = "lessons"
    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, default="")  # Markdown
    position: Mapped[int] = mapped_column(default=0)
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.brouillon)

    course: Mapped[Course] = relationship(back_populates="lessons")
    exercises: Mapped[list["Exercise"]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan")


class Exercise(Base):
    __tablename__ = "exercises"
    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    statement: Mapped[str] = mapped_column(Text)            # énoncé
    type: Mapped[ExerciseType] = mapped_column(Enum(ExerciseType))
    choices: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)  # QCM uniquement
    solution: Mapped[str] = mapped_column(Text)             # corrigé (jamais envoyé à l'apprenant)
    difficulty: Mapped[Difficulty] = mapped_column(Enum(Difficulty))
    notion: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.brouillon)
    generated_by_ai: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    lesson: Mapped[Lesson] = relationship(back_populates="exercises")


exam_exercises = Table(
    "exam_exercises", Base.metadata,
    Column("exam_id", ForeignKey("exams.id", ondelete="CASCADE"), primary_key=True),
    Column("exercise_id", ForeignKey("exercises.id", ondelete="CASCADE"), primary_key=True),
)


class Exam(Base):
    __tablename__ = "exams"
    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime)
    duration_minutes: Mapped[int] = mapped_column(default=60)
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.brouillon)

    course: Mapped[Course] = relationship(back_populates="exams")
    exercises: Mapped[list[Exercise]] = relationship(secondary=exam_exercises)
    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="exam", cascade="all, delete-orphan")


class Assignment(Base):
    """Qui doit passer quel examen."""
    __tablename__ = "assignments"
    __table_args__ = (UniqueConstraint("exam_id", "user_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    exam: Mapped[Exam] = relationship(back_populates="assignments")
    user: Mapped[User] = relationship()


class Attempt(Base):
    """Une réponse d'un apprenant à un exercice. C'est la matière première du chatbot d'analyse."""
    __tablename__ = "attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"), index=True)
    exam_id: Mapped[int | None] = mapped_column(ForeignKey("exams.id", ondelete="SET NULL"), nullable=True)
    answer: Mapped[str] = mapped_column(Text)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0..1, None = à corriger
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
