# Lire le premier socle Documents

État : code disponible, notions **à relire**. Le checkpoint Python/FastAPI
sera validé après discussion des réponses ; l'authentification n'en est pas
un prérequis dans le périmètre actuel d'AGENTS.md.

## Ordre de lecture

1. `app/documents/schemas.py` : les données acceptées et retournées par l'API.
2. `app/documents/models.py` : leur représentation persistante dans PostgreSQL.
3. `app/database/session.py` : création du moteur et session par requête.
4. `app/documents/router.py` : contrat HTTP et traduction des erreurs métier.
5. `app/documents/dependencies.py` : construction du service avec la session injectée.
6. `app/documents/service.py` : cas d’usage et transactions.
7. `app/documents/repository.py` : requêtes SQLAlchemy sans commit.
8. `migrations/versions/0001_documents.py` : évolution versionnée du schéma.
9. `tests/test_documents.py` : comportements HTTP attendus.
10. `tests/test_document_layers.py` : intégration du repository et du service avec PostgreSQL.

## Chemin d'un POST

FastAPI reçoit le JSON et Pydantic le valide dans `DocumentCreate`. Si le titre
est vide ou qu'un champ inconnu apparaît, la réponse est 422. La route reçoit
un service grâce à `Depends(get_document_service)`. Cette dépendance reçoit
elle-même la session fournie par `get_session`.

La route appelle `service.create(title=..., filename=...)`. Le service ouvre une
transaction avec `with self._session.begin()`, crée l'entité et appelle
`repository.add(document)`. Le repository ajoute l'objet à la session sans commit.

À la sortie normale du bloc `begin()`, SQLAlchemy effectue le flush puis le commit.
En cas d'exception, le bloc effectue le rollback et propage l'erreur. Le service
retourne donc après validation de la transaction. `expire_on_commit=False` garde
les attributs chargés accessibles pour la sérialisation sans nouvelle lecture SQL.

La route ajoute l'en-tête Location et retourne l'objet ; `DocumentRead` définit
les champs exposés dans la réponse HTTP 201. La dépendance avec `yield` ferme la
session après utilisation : elle gère sa durée de vie, le service gère les transactions.

Chaque opération publique du service possède sa transaction, y compris une lecture.
Ce service utilise une session dédiée sans transaction déjà ouverte par son appelant.
Si un futur cas d'usage coordonne plusieurs écritures atomiques, il devra les réunir
sous une même transaction plutôt que chaîner des méthodes qui valident chacune.

Le repository renvoie `None` pour un document absent. Le service décide que le cas
d'usage exige un document et lève `DocumentNotFound`. Le router traduit cette erreur
en HTTP 404. Service et repository n'importent pas FastAPI.

## Repères Symfony / NestJS

| Élément | Rôle | Analogie |
| --- | --- | --- |
| Router FastAPI | Points d'entrée HTTP | Controller Symfony/NestJS |
| Modèle Pydantic | Validation et contrat JSON | DTO + Validator / class-validator |
| Entité SQLAlchemy | Table et objet persistant | Entité Doctrine / TypeORM |
| Session SQLAlchemy | Suivi des objets et transaction | Proche de l'EntityManager Doctrine |
| Depends | Fournir une dépendance par requête | Injection de dépendances |
| Alembic | Historique des changements SQL | Doctrine Migrations / migrations TypeORM |

`Mapped[str]` décrit un attribut ORM typé. `Annotated[Session, Depends(...)]`
combine un type Python et une information exploitée par FastAPI. Les annotations
Python seules ne valident pas une valeur à l'exécution ; ici Pydantic assure cette
validation pour les données HTTP.

Les routes SQL sont des fonctions `def` : FastAPI les exécute dans son pool de
threads. Mettre `async def` autour d'appels SQL synchrones bloquerait la boucle
asynchrone. Une future version asynchrone nécessiterait aussi un pilote et une
session SQL adaptés. `async` n'est pas un synonyme de « plus rapide ».

La convention du projet sépare les responsabilités même pour ce CRUD : router,
service et repository concrets. Le service construit son repository avec la même
session ; aucune interface générique n'est nécessaire à ce stade. Cette séparation
permet de relire les requêtes et les cas d'usage indépendamment du protocole HTTP.

## Relecture et questions

Prendre le temps de suivre le POST dans les fichiers avant de répondre.

1. Pourquoi `DocumentCreate`, `DocumentRead` et `Document` sont-ils séparés ?
2. Où a lieu le commit ? Que devient une écriture après `flush()` si une erreur
   survient avant le commit ?
3. Pourquoi la dépendance utilise-t-elle `yield` dans un `with` ?
4. Pourquoi les routes qui interrogent PostgreSQL utilisent-elles `def` ?
5. Quelle différence entre modifier le modèle ORM et appliquer une migration ?
6. Qu'apporte ici PostgreSQL dans les tests par rapport à un repository simulé ?

Les réponses seront discutées avant de marquer les notions comme comprises.

Références : [sessions SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/session_basics.html),
[dépendances avec yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/),
[migrations Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html).
