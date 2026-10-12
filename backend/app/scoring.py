from .models import Exercise, ExerciseType


def _normalize(s: str) -> str:
    return " ".join(s.strip().lower().split())


def auto_score(exercise: Exercise, answer: str) -> float | None:
    """QCM corrigé automatiquement. Code / texte libre : None = correction par le formateur.

    Piste d'évolution : exécuter des tests unitaires pour le type `code`
    ou proposer une note IA que le formateur valide.
    """
    if exercise.type == ExerciseType.qcm:
        return 1.0 if _normalize(answer) == _normalize(exercise.solution) else 0.0
    return None
