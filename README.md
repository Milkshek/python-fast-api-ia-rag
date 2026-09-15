# Document Intelligence Assistant

Projet de formation Python, FastAPI et IA décrit dans
[le programme](document-intelligence-training.md).

## Démarrage local

Prérequis : Docker avec Compose v2 ou supérieur, moteur Docker démarré, et `make`.
Depuis la racine du dépôt :

```sh
make up
```

`make up` crée `.env` à partir de `.env.example` uniquement s'il n'existe pas,
puis construit et démarre les services et applique les migrations Alembic.
Les réglages locaux sont conservés.
Les identifiants d'exemple sont destinés au développement.

| Service | Accès | Rôle |
| --- | --- | --- |
| `api` | http://localhost:8000/docs | FastAPI et documentation interactive |
| `db` | localhost:5432 | PostgreSQL 17, stockage persistant |

La route http://localhost:8000/health retourne `{"status":"ok"}`.
Elle vérifie uniquement le serveur HTTP. L'API Documents utilise PostgreSQL ;
`make health` vérifie également l'accès SQL.

## Commandes utiles

`make` ou `make help` affiche les commandes disponibles.

```sh
make up               # Construire et démarrer, attendre les services sains
make down             # Arrêter et retirer les conteneurs, conserver les données
make restart          # Redémarrer les conteneurs existants
make build            # Construire les images uniquement
make ps               # État des services
make logs             # Suivre les 100 dernières lignes puis les nouveaux logs
make logs SERVICE=api # Logs du backend uniquement
make shell            # Shell dans le backend
make db-shell         # Console PostgreSQL
make check            # Valider la configuration Compose
make health           # Vérifier HTTP interne et une requête SQL
make migrate          # Appliquer les migrations restantes
make test             # Tests et migrations sur PostgreSQL isolé
```

`make health` nécessite des services démarrés. Pour vérifier aussi l'accès HTTP
depuis la machine hôte : `curl --fail http://localhost:8000/health`.
Les cibles du Makefile exécutent les commandes `docker compose` correspondantes.

Le code de `app/` est monté dans le conteneur : Uvicorn recharge l'application
après une modification. Après une modification des dépendances ou du Dockerfile,
relancer `make up`. `make restart` ne reconstruit pas les images et n'applique pas
les changements de configuration Compose ou de variables d'environnement.

## Configuration et persistance

`.env` est ignoré par Git. `API_PORT` et `POSTGRES_PORT` permettent de changer
les ports locaux s'ils sont déjà occupés. Les ports internes restent 8000 et 5432.
Depuis un conteneur, PostgreSQL est joignable sous le nom `db`, pas `localhost`.
Les variables `PG*` du service API configurent la connexion SQLAlchemy/psycopg.

Le volume `postgres_data` conserve la base après un arrêt ou une reconstruction.
`docker compose down --volumes` **supprime les données** : réserver cette commande
à une remise à zéro volontaire. Les variables `POSTGRES_*` initialisent une base
vide ; les modifier ne change pas les identifiants d'une base déjà créée.

L'API attend que PostgreSQL soit disponible au démarrage. Compose contrôle ensuite
la santé des deux services ; ces contrôles ne redémarrent pas automatiquement un
service devenu indisponible.

Ce socle est destiné au développement local. Le frontend, le pipeline documentaire
et les capacités IA seront ajoutés selon les étapes du programme. Les dépendances
Python sont actuellement bornées, mais pas encore verrouillées exactement.

## API Documents

Cette première étape gère uniquement les **métadonnées** ; elle ne transfère pas
encore les fichiers PDF et ne propose pas encore d'authentification.

| Méthode | Chemin | Résultat |
| --- | --- | --- |
| POST | `/documents` | Créer, HTTP 201 et en-tête Location |
| GET | `/documents?limit=20&offset=0` | Liste paginée, HTTP 200 |
| GET | `/documents/{id}` | Consulter, HTTP 200 ou 404 |
| DELETE | `/documents/{id}` | Supprimer, HTTP 204 ou 404 |

```sh
curl --fail http://localhost:8000/documents \
  -H 'Content-Type: application/json' \
  -d '{"title":"Contrat de démonstration","filename":"contrat.pdf"}'
```

Le titre accepte 1 à 200 caractères, le nom de fichier 1 à 255 après suppression
des espaces aux extrémités. Les champs supplémentaires sont refusés. Les UUID et
paramètres invalides donnent HTTP 422. La pagination est limitée à 100 éléments
et ordonnée par date de création, puis UUID. `filename` est une métadonnée, jamais
un chemin utilisé pour lire ou écrire sur disque.

## Tests et migrations

`make test` construit une image avec pytest et lance un PostgreSQL distinct
(`compose.test.yaml`), sans port publié, avec données temporaires en mémoire.
La suite utilise de vraies requêtes SQL et vérifie le cycle HTTP, la validation,
la pagination, le commit et l'annulation des transactions inachevées.
Elle vérifie aussi l'alignement modèle/migration et un aller-retour des migrations.
Les conteneurs de test sont retirés à la fin, même en cas d'échec.
La version actuelle du client de test émet deux avertissements de dépréciation
dans Starlette (compatibilité httpx et alias AnyIO) ; les tests passent.
Ne pas lancer deux `make test` en parallèle : ils partagent le même projet de test.

Les fixtures refusent de nettoyer une base autre que `document_intelligence_test`
sur `db-test`. La base de développement n'est jamais visée par ces tests.

Les migrations sont versionnées dans `migrations/versions/`. La création des
tables passe par Alembic, jamais par `create_all()` au démarrage de l'application.
Après une nouvelle migration : `make migrate` (ou `make up`).

Guide pédagogique : [lecture du socle Documents](docs/learning/01-documents-api.md).

## Repères de lecture

- `Dockerfile` construit l'image Python et exécute l'API avec un utilisateur non root.
- `compose.yaml` assemble les services, le réseau, les contrôles de santé et le volume.
- `app/main.py` fournit le serveur minimal nécessaire pour vérifier le démarrage.

À la relecture : pourquoi l'API utilise-t-elle `db` pour joindre PostgreSQL ?
Quelle différence entre le montage du code et le volume de données ?
Pourquoi attendre un service sain plutôt que simplement un conteneur démarré ?

Références : [Docker avec FastAPI](https://fastapi.tiangolo.com/deployment/docker/)
et [image officielle PostgreSQL](https://hub.docker.com/_/postgres).
