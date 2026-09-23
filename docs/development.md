# Développement local

Toutes les commandes `make` s’exécutent depuis la racine du dépôt, dans Docker.
Pour travailler hors Docker, le projet Python se trouve dans `backend/` ; dans les
conteneurs, ce dossier correspond à `/workspace` et les imports restent `from app...`.

## Configuration

`make init` copie `.env.example` vers `.env` uniquement si ce dernier n’existe pas.
Les identifiants fournis sont destinés au développement. `.env` est ignoré par Git.

- `GEMINI_API_KEY` : clé utilisée uniquement par le backend pour les appels Gemini.
- `API_PORT`, `FRONTEND_PORT`, `POSTGRES_PORT` : ports publiés sur localhost.
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` : initialisation PostgreSQL.

Compose fournit les variables `PG*` à l’API. Depuis son conteneur, PostgreSQL est
joignable sous `db:5432`, pas sous `localhost`. Le proxy Vite relaie `/api` vers
`http://api:8000`, sans configuration CORS supplémentaire pour ce parcours local.

Les variables PostgreSQL initialisent une base vide : les modifier ne change pas
les identifiants d’une base existante. Après modification de `.env`, de Compose,
d’un Dockerfile ou des dépendances, utiliser `make up`. `make restart` redémarre
seulement les conteneurs existants.

## Persistance et cycle de vie

- `postgres_data` conserve les données SQL, vecteurs et conversations.
- `document_files` conserve les PDF sous `/data/documents/UUID.pdf`.
- `make down` conserve ces volumes ; `docker compose down --volumes` les supprime.

Les sources backend et React sont montées pour le rechargement à chaud.
Vite et Uvicorn avec `--reload` constituent une configuration de développement.
Les contrôles de santé Compose n’assurent pas un redémarrage automatique en cas
d’indisponibilité ultérieure.

`/health` vérifie seulement que FastAPI répond. `make health` ajoute une requête
SQL. Aucun de ces contrôles ne vérifie Gemini. Pour vérifier l’accès depuis l’hôte :

```sh
curl --fail http://localhost:8000/health
```

## Dépendances et migrations

Les `.in` Python décrivent les dépendances directes ; les `.txt`, générés par
pip-tools, verrouillent les dépendances transitives avec hashes. Le lock de
développement est contraint par celui du runtime. Le frontend utilise
`package.json`, `package-lock.json` et `npm ci`.

```sh
make lock                    # Après modification des .in
make lock LOCK_ARGS=--upgrade # Actualiser les versions compatibles
make quality
make up
```

Les migrations Alembic sont dans `backend/migrations/versions/`. Les tables ne sont
pas créées avec `create_all()` au démarrage. `make up` applique les migrations ;
`make migrate` les applique à une API déjà démarrée.

## Vérifications

| Commande | Contrôles |
| --- | --- |
| `make check` | Validité de la configuration Compose |
| `make lint` | Ruff et format Python, sans modification |
| `make typecheck` | Mypy strict sur l’application et l’évaluation |
| `make test` | Pytest, cohérence des migrations, downgrade puis upgrade |
| `make frontend-check` | ESLint, Prettier, TypeScript, build Vite et Vitest |
| `make quality` | Lint, types et tests backend/frontend |
| `make smoke-install` | Installation vide, pipeline sans IA et proxy frontend |
| `make evaluate` | Corpus avec Gemini réel et rapport à relire humainement |

`make test` utilise PostgreSQL/pgvector dans un projet isolé, sans port publié,
avec stockage temporaire. Les fixtures refusent de nettoyer une autre base que
`document_intelligence_test` sur `db-test`. Pytest traite les avertissements comme
des erreurs. Les clients Gemini sont simulés ; les requêtes SQL sont réelles.

`make smoke-install` utilise ses propres volumes et une clé Gemini vide ; le
nettoyage retire uniquement son projet et ses volumes. Les commandes de test
partagent chacune un nom de projet fixe : ne pas lancer deux instances de la
même commande en parallèle.

Les tests React sont à côté des composants, sous `frontend/src/`. Ils utilisent
Vitest/jsdom, Testing Library et des appels HTTP simulés. Les vérifications navigateur
manuelles sont complémentaires ; aucune suite E2E automatisée n’est fournie.

`make evaluate` nécessite les services déjà démarrés avec `make up`.
Les rapports sont écrits dans `reports/`, ignoré par Git. La campagne
supprime les documents synthétiques qu’elle crée et consigne les erreurs de nettoyage.
Les limites et critères de relecture sont dans le [guide d’évaluation](learning/09-rag-evaluation.md).

## Historique Git

Créer des commits atomiques avec leurs tests pertinents. Rattacher les corrections
à leur commit d’origine avec `git commit --fixup`, puis autosquasher les commits
locaux avant intégration. Ne pas réécrire l’historique partagé sans accord explicite.
