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
Python sont verrouillées avec leurs dépendances transitives et hashes dans les
fichiers requirements.txt et requirements-dev.txt (Linux / Python 3.13).

## API Documents

L’API gère les **métadonnées et l’import de PDF**. L’extraction du texte par page est disponible.
L’indexation Gemini est disponible ; la recherche, les réponses LLM et
l’authentification ne sont pas encore implémentées.

| Méthode | Chemin | Résultat |
| --- | --- | --- |
| POST | `/documents` | Créer les métadonnées, HTTP 201 et Location |
| POST | `/documents/upload` | Importer un PDF en multipart, HTTP 201 et Location |
| POST | `/documents/{id}/extract` | Extraire le texte, HTTP 200 |
| POST | `/documents/{id}/chunk` | Découper le texte extrait, HTTP 200 |
| POST | `/documents/{id}/index` | Calculer et stocker les embeddings, HTTP 200 |
| GET | `/documents/{id}/chunks?limit=20&offset=0` | Lire les chunks et leurs positions |
| GET | `/documents/{id}/pages?limit=20&offset=0` | Lire les pages extraites |
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
Pytest traite les avertissements comme des erreurs. Les contraintes temporaires
de compatibilité sont expliquées dans requirements.in et le guide J3.
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

## Qualité et dépendances

```sh
make format        # Formater et trier les imports
make lint          # Contrôler le lint et le format
make typecheck     # Mypy strict sur app/
make quality       # Lint + types + tests
make lock          # Résoudre après modification des .in
make lock LOCK_ARGS=--upgrade # Actualiser les versions compatibles
```

Ces commandes utilisent Docker ; les outils n'ont pas besoin d'être installés
sur la machine hôte. Les fichiers `.in` décrivent les dépendances directes et
les `.txt` sont générés par pip-tools. Versionner les deux après validation.
Le lock de développement est contraint par celui du runtime.

Après modification des dépendances : `make lock`, `make quality`, puis `make up`.
Les contrôles statiques ne nécessitent pas de base de données. `make check` reste
la validation de Compose ; `make quality` contrôle le code et son comportement.

Voir [le guide J3](docs/learning/02-tooling.md) pour les limites, la maintenance des
contraintes de compatibilité et les comparaisons PHP/TypeScript.

## Importer un PDF

```sh
make up
curl --fail http://localhost:8000/documents/upload \
  -F 'title=Contrat de démonstration' \
  -F 'file=@/chemin/vers/contrat.pdf;type=application/pdf'
```

Remplacer le chemin par un PDF local. Le formulaire est aussi disponible dans
Swagger. Limite : **10 Mio par fichier**. La réponse fournit `status=UPLOADED`
et `size_bytes`. Les créations JSON et anciennes lignes sont `METADATA_ONLY`.

Fichier vide : 400 ; extension/signature non PDF : 415 ; taille excessive : 413 ;
métadonnées invalides : 422 ; stockage indisponible : 503. L’en-tête `%PDF-` est
vérifié à l’upload ; le parsing strict est effectué à l’étape d’extraction.
La taille est contrôlée après parsing multipart, pas avant réception réseau.

Les fichiers sont nommés `UUID.pdf` dans `/data/documents`, persisté par le volume
`document_files`. Le nom original n’est jamais utilisé comme chemin serveur.
Une suppression interrompue reste `DELETING` et peut être relancée avec DELETE.
Un crash pendant l’upload peut laisser un fichier orphelin : les limites de cette
coordination SQL/disque sont détaillées dans [le guide J4](docs/learning/03-upload.md).

`docker compose down` conserve base et fichiers. `docker compose down --volumes`
**supprime les deux**. Les tests utilisent uniquement des répertoires temporaires.


## Extraire le texte d'un PDF

Après l'upload, utiliser l'UUID retourné :

```sh
curl --fail -X POST http://localhost:8000/documents/UUID/extract
curl --fail 'http://localhost:8000/documents/UUID/pages?limit=20&offset=0'
```

La requête attend l'extraction. Le statut devient `EXTRACTED`, puis les pages
numérotées à partir de 1 sont consultables. Une relance réussie ne duplique pas les
pages ; supprimer le document supprime également ses pages en base.

Un PDF illisible, chiffré, sans texte extractible ou dépassant les limites de
traitement retourne 422 avec un code d'erreur, mémorisé dans `extraction_error`
et le statut `FAILED`. Une relance est possible. Limites actuelles : 200 pages et
2 millions de caractères normalisés. Elles ne bornent pas la mémoire du parseur.
Pas d'OCR, de traitement en arrière-plan ni d'indexation à cette étape.
Les PDF locaux de confiance avec texte constituent le périmètre de démonstration.

Voir [le guide J5](docs/learning/04-extraction.md) pour les transactions, la
normalisation, les limites de mise en page et les questions de compréhension.


## Découper en passages

Après extraction, appeler `POST /documents/{id}/chunk`, puis consulter
`GET /documents/{id}/chunks?limit=20&offset=0`. Le statut devient `CHUNKED`.
Le découpage utilise 1000 caractères avec 200 de recouvrement, page par page.
Chaque passage conserve un UUID, son ordre, sa page et ses offsets dans le texte
normalisé. Une relance conserve le résultat existant ; supprimer le document
supprime aussi ses chunks. Un document non extrait retourne 409.

Ce découpage simple peut couper les phrases et ne constitue pas encore une
indexation vectorielle. Voir [le guide J6](docs/learning/05-chunking.md) pour
l'algorithme, les limites et les garanties transactionnelles.


## Indexer avec Gemini (J7)

Configurer `GEMINI_API_KEY` dans `.env` local, avec une clé de projet utilisant
l'offre gratuite, puis `make up`. Aucune clé dans Git. Le texte des chunks est
transmis à Google ; aucun modèle n'est installé localement. L'application ne peut
pas détecter si la facturation a été activée sur le compte associé à une clé.

Après upload/extract/chunk, appeler `POST /documents/{id}/index` : le statut devient
`INDEXED`, avec `embedding_model=gemini-embedding-2` et `embedding_dimensions=768`.
PostgreSQL 17 embarque désormais pgvector, en conservant le volume de données.
Une relance garde l'index existant ; `?force=true` demande un recalcul explicite.
La réindexation conserve l'ancien résultat si le calcul ou la transaction échoue.

Maximum 100 chunks par indexation ; un appel Gemini par chunk, sans retry automatique.
Quota atteint : 429 ; clé absente/erreur fournisseur : 503 ; réponse invalide : 502.
Les tests automatiques simulent Gemini et utilisent une vraie base pgvector.
Les offres gratuites sont soumises aux quotas du fournisseur ; aucun fallback payant
n'est implémenté. La recherche sémantique sera ajoutée en J8.

Voir [le guide J7](docs/learning/06-embeddings.md) pour le protocole, les transactions,
la reprise, les limites et les questions de compréhension.
