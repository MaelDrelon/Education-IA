# Edu IA — template

Un formateur crée des cours, des exercices et des examens avec l'aide d'une IA, les assigne à des
apprenants, puis interroge un chatbot qui analyse les résultats.

| Brique | Techno | Rôle |
|---|---|---|
| Back | FastAPI, SQLAlchemy 2, JWT | Référentiel (matières, leçons, exercices, examens, tentatives) et contrôle des rôles |
| Front | React + Vite | Éditeur de leçons/exercices, passage d'examen, chat d'analyse |
| IA | API Claude (tool use) | 1. Génération d'exercices · 2. Analyse des résultats |

## Démarrer

**Docker (Postgres)**
```bash
cp .env.example .env
docker compose up --build
```
Front : http://localhost:5173 · API + Swagger : http://localhost:8000/docs

**En local (SQLite)**
```bash
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp ../.env.example .env
python -m app.seed && uvicorn app.main:app --reload
# autre terminal
cd frontend && npm install && npm run dev
```

**Comptes de démo** (mot de passe `demo1234`) : `admin@demo.fr`, `formateur@demo.fr`,
`alice@demo.fr`, `bob@demo.fr`, `chloe@demo.fr`.

Par défaut `LLM_PROVIDER=fake` : tout fonctionne sans clé API, avec des réponses simulées.
Pour la vraie IA : `LLM_PROVIDER=anthropic` et `ANTHROPIC_API_KEY=...`.

**Tests** : `cd backend && pytest`

### IA locale avec Ollama

```bash
ollama pull qwen3:8b          # un modèle qui gère les appels d'outils
# .env
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen3:8b
OLLAMA_URL=http://localhost:11434            # back lancé en local
# OLLAMA_URL=http://host.docker.internal:11434  # back dans Docker, Ollama sur l'hôte
```
Ou tout dans Docker : `docker compose --profile ollama up`, puis
`docker compose exec ollama ollama pull qwen3:8b` et `OLLAMA_URL=http://ollama:11434`.

Le code est dans `app/ai/ollama.py`. La génération utilise la sortie JSON contrainte par schéma (`format`),
l'analyse utilise les appels d'outils (`tools`), avec **les mêmes outils et le même cloisonnement** qu'avec Claude.
Aucune donnée ne sort de la machine.

## Rôles

| Rôle | Peut |
|---|---|
| admin | Gérer les comptes (création, rôle, désactivation). Voit tout. |
| formateur | Créer cours, leçons, exercices, examens ; assigner ; corriger ; utiliser l'IA. **Uniquement sur ses propres cours.** |
| apprenant | Voir les examens qui lui sont assignés et publiés ; rendre ses réponses. Ne reçoit jamais les corrigés. |

## Modèle de données

```
users ─┬─< courses ─< lessons ─< exercises >─┐
       │       └─< exams >──< exam_exercises ┘
       ├─< assignments >── exams
       └─< attempts >── exercises (+ exam_id optionnel)
```

Par rapport au modèle minimal, trois ajouts, chacun justifié par une question du chatbot :

- `exercises.notion` : sans notion, impossible de répondre à « sur quelle notion la classe bloque-t-elle ? ».
- `assignments` : pour savoir qui **n'a pas** terminé un examen, il faut savoir qui devait le passer.
- `status` (brouillon / publié) et `generated_by_ai` : matérialisent la validation humaine.

`attempts.score` est entre 0 et 1. Il vaut `NULL` tant qu'une réponse libre (code, texte) n'a pas été corrigée ;
les QCM sont corrigés automatiquement. Les analyses ne portent que sur les tentatives corrigées.

## L'IA

### 1. Génération (`POST /ai/generate`)
- Le modèle répond via un outil au schéma imposé (`tool_choice`), pas en texte libre : pas de parsing fragile.
- Chaque proposition est revalidée par le back (ex. le corrigé d'un QCM doit être l'un des choix) ; les invalides sont écartées et comptées.
- Tout arrive **en brouillon**. Un apprenant ne voit jamais un brouillon, et un examen refuse un exercice non validé.
  **L'humain reste responsable du contenu publié.**

### 2. Analyse (`POST /ai/analyze`)
Le modèle **n'écrit pas de SQL**. Il choisit parmi des requêtes d'analyse codées et testées
(`app/ai/analysis.py`) et en fournit les paramètres :

| Outil | Répond à |
|---|---|
| `taux_reussite_par_exercice` | « Quel exercice a le plus faible taux de réussite ? » |
| `apprenants_examen_non_termine` | « Qui n'a pas terminé l'examen de la semaine dernière ? » |
| `difficulte_par_notion` | « Sur quelle notion la classe bloque-t-elle ? » |
| `progression_apprenant` | « Où en est Bob ? » |
| `lister_examens`, `lister_cours` | Retrouver un identifiant avant une autre requête |

Arguments à défendre :
- **Sécurité** : aucune requête arbitraire, donc ni injection ni requête destructrice.
- **Cloisonnement** : le filtre « cours du formateur » est appliqué par le back, quoi que demande le modèle.
- **Traçabilité** : la réponse contient la trace des requêtes et leurs résultats, affichée sous chaque réponse du chat.
  Les chiffres viennent de la base, pas du modèle.
- **Extensible** : une nouvelle question = une nouvelle fonction + sa déclaration dans `TOOLS`.

Limite assumée : une question non prévue n'a pas de réponse. Évolution possible : un outil text-to-SQL
exécuté avec un rôle Postgres en lecture seule, sur des vues filtrées par formateur.

## Arborescence

```
backend/app/
  main.py, config.py, db.py, models.py, schemas.py
  auth.py          JWT + dépendances par rôle
  permissions.py   « ce cours appartient-il à ce formateur ? »
  scoring.py       correction automatique des QCM
  routers/         auth, users, courses, exercises, exams, attempts, ai
  ai/              llm.py, generation.py, analysis.py
  seed.py          données de démo (dont des tentatives)
backend/tests/     tests d'API (rôles, brouillons, correction, analyse, cloisonnement)
frontend/src/
  pages/admin      gestion des comptes
  pages/formateur  cours, éditeur de leçon + génération IA, examens, chat d'analyse
  pages/apprenant  mes examens, passage d'examen
```

## Pistes

- Migrations Alembic (aujourd'hui `create_all` au démarrage).
- Correction des exercices `code` par exécution de tests en bac à sable.
- Proposition de note par l'IA sur les réponses libres, validée par le formateur.
- Mode entraînement pour l'apprenant (exercices publiés hors examen ; l'API le permet déjà).
- Historique de conversation dans le chat d'analyse.
- Rendu Markdown des leçons et énoncés côté front.
