"""Données de démo : `python -m app.seed`.

Sans tentatives, le chatbot d'analyse n'a rien à dire : on en crée donc un jeu réaliste.
"""
from datetime import timedelta

from sqlalchemy import select

from .auth import hash_password
from .db import Base, SessionLocal, engine, utcnow
from .models import (Assignment, Attempt, Course, Difficulty, Exam, Exercise, ExerciseType, Lesson,
                     Role, Status, User)

PASSWORD = "demo1234"


def run():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if db.scalar(select(User.id).limit(1)):
            print("Base déjà initialisée, rien à faire.")
            return

        def user(email, name, role):
            u = User(email=email, full_name=name, role=role, hashed_password=hash_password(PASSWORD))
            db.add(u)
            return u

        user("admin@demo.fr", "Admin Démo", Role.admin)
        prof = user("formateur@demo.fr", "Camille Formatrice", Role.formateur)
        alice = user("alice@demo.fr", "Alice Martin", Role.apprenant)
        bob = user("bob@demo.fr", "Bob Durand", Role.apprenant)
        chloe = user("chloe@demo.fr", "Chloé Bernard", Role.apprenant)
        db.flush()

        course = Course(title="Python — débutant", description="Les bases du langage", owner_id=prof.id)
        lesson = Lesson(course=course, title="Les boucles", status=Status.publie, content=(
            "# Les boucles\n\n`for` parcourt une séquence, `while` répète tant qu'une condition est vraie.\n\n"
            "```python\nfor i in range(3):\n    print(i)  # 0, 1, 2\n```\n\n"
            "`break` sort de la boucle, `continue` passe à l'itération suivante."))
        db.add(course)

        def qcm(title, statement, choices, solution, notion):
            return Exercise(lesson=lesson, title=title, statement=statement, type=ExerciseType.qcm,
                            choices=choices, solution=solution, notion=notion,
                            difficulty=Difficulty.debutant, status=Status.publie)

        e1 = qcm("range(3)", "Qu'affiche `for i in range(3): print(i)` ?",
                 ["1, 2, 3", "0, 1, 2", "0, 1, 2, 3"], "0, 1, 2", "boucle for")
        e2 = qcm("Boucle infinie", "Laquelle de ces boucles ne s'arrête jamais ?",
                 ["while True: pass", "for i in range(10): pass", "while False: pass"],
                 "while True: pass", "boucle while")
        e3 = qcm("break ou continue", "Quel mot-clé passe directement à l'itération suivante ?",
                 ["break", "continue", "pass", "return"], "continue", "break / continue")
        e4 = Exercise(lesson=lesson, title="Somme de 1 à n", type=ExerciseType.code,
                      statement="Écrire une fonction `somme(n)` qui renvoie 1 + 2 + … + n avec une boucle.",
                      solution="def somme(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i\n    return total",
                      notion="boucle for", difficulty=Difficulty.debutant, status=Status.publie)
        db.add_all([e1, e2, e3, e4])

        exam = Exam(course=course, title="Contrôle — les boucles", status=Status.publie,
                    scheduled_at=utcnow() - timedelta(days=5), duration_minutes=30,
                    exercises=[e1, e2, e3])
        db.add(exam)
        db.flush()
        for learner in (alice, bob, chloe):
            db.add(Assignment(exam_id=exam.id, user_id=learner.id))

        t0 = exam.scheduled_at + timedelta(minutes=10)

        def attempt(u, ex, answer, score, in_exam=True, days=0):
            db.add(Attempt(user_id=u.id, exercise_id=ex.id, exam_id=exam.id if in_exam else None,
                           answer=answer, score=score, submitted_at=t0 + timedelta(days=days)))

        # Examen : Alice a tout rendu, Bob 2/3, Chloé rien
        attempt(alice, e1, "0, 1, 2", 1.0)
        attempt(alice, e2, "while True: pass", 1.0)
        attempt(alice, e3, "break", 0.0)
        attempt(bob, e1, "1, 2, 3", 0.0)
        attempt(bob, e2, "while True: pass", 1.0)
        # Entraînement hors examen
        attempt(chloe, e3, "break", 0.0, in_exam=False, days=-2)
        attempt(bob, e3, "pass", 0.0, in_exam=False, days=-1)
        attempt(chloe, e1, "0, 1, 2", 1.0, in_exam=False, days=-2)
        attempt(alice, e4, "def somme(n):\n    return sum(range(n+1))", 0.5, in_exam=False, days=-3)

        db.commit()
        print(f"Base initialisée. Comptes : admin@ / formateur@ / alice@ / bob@ / chloe@demo.fr "
              f"— mot de passe « {PASSWORD} »")
    finally:
        db.close()


if __name__ == "__main__":
    run()
