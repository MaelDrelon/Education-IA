from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import Difficulty, ExerciseType, Role, Status


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Utilisateurs -----------------------------------------------------------
class UserOut(ORM):
    id: int
    email: str
    full_name: str
    role: Role
    is_active: bool


class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str = Field(min_length=4)
    role: Role


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: Role | None = None
    is_active: bool | None = None
    password: str | None = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --- Cours & leçons ----------------------------------------------------------
class CourseIn(BaseModel):
    title: str
    description: str = ""


class CourseOut(ORM):
    id: int
    title: str
    description: str
    owner_id: int


class LessonIn(BaseModel):
    title: str
    content: str = ""
    position: int = 0


class LessonUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    position: int | None = None


class LessonOut(ORM):
    id: int
    course_id: int
    title: str
    content: str
    position: int
    status: Status


# --- Exercices -------------------------------------------------------------
class ExerciseIn(BaseModel):
    title: str
    statement: str
    type: ExerciseType
    choices: list[str] | None = None
    solution: str
    difficulty: Difficulty
    notion: str

    @model_validator(mode="after")
    def check_qcm(self):
        if self.type == ExerciseType.qcm:
            if not self.choices or len(self.choices) < 2:
                raise ValueError("Un QCM doit avoir au moins 2 choix")
            if self.solution not in self.choices:
                raise ValueError("Le corrigé d'un QCM doit être l'un des choix")
        else:
            self.choices = None
        return self


class ExerciseUpdate(BaseModel):
    title: str | None = None
    statement: str | None = None
    type: ExerciseType | None = None
    choices: list[str] | None = None
    solution: str | None = None
    difficulty: Difficulty | None = None
    notion: str | None = None


class ExerciseOut(ORM):
    """Vue formateur (avec corrigé)."""
    id: int
    lesson_id: int
    title: str
    statement: str
    type: ExerciseType
    choices: list[str] | None
    solution: str
    difficulty: Difficulty
    notion: str
    status: Status
    generated_by_ai: bool


class ExercisePublic(ORM):
    """Vue apprenant : pas de corrigé."""
    id: int
    title: str
    statement: str
    type: ExerciseType
    choices: list[str] | None
    difficulty: Difficulty
    notion: str


# --- Examens -----------------------------------------------------------------
class ExamIn(BaseModel):
    title: str
    scheduled_at: datetime
    duration_minutes: int = 60
    exercise_ids: list[int] = Field(min_length=1)


class AssignIn(BaseModel):
    user_ids: list[int]


# --- Tentatives --------------------------------------------------------------
class AttemptIn(BaseModel):
    exercise_id: int
    exam_id: int | None = None
    answer: str


class AttemptOut(ORM):
    id: int
    user_id: int
    exercise_id: int
    exam_id: int | None
    answer: str
    score: float | None
    submitted_at: datetime


class GradeIn(BaseModel):
    score: float = Field(ge=0, le=1)


# --- IA ----------------------------------------------------------------------
class GenerateIn(BaseModel):
    lesson_id: int
    consigne: str
    count: int = Field(5, ge=1, le=20)
    difficulty: Difficulty = Difficulty.debutant
    type: ExerciseType | None = None


class GenerateOut(BaseModel):
    created: list[ExerciseOut]
    rejected: int  # propositions de l'IA invalides, écartées


class AnalyzeIn(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class ToolTrace(BaseModel):
    name: str
    input: dict[str, Any]
    result: Any


class AnalyzeOut(BaseModel):
    answer: str
    trace: list[ToolTrace]
