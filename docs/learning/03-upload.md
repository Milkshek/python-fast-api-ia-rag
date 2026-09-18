# J4 — Upload PDF, stockage et cohérence

Statut : à relire. J3 est validé ; les notions de J4 ne le sont pas encore.

## Ce qui a été ajouté

POST /documents/upload reçoit un formulaire multipart avec `title` et `file`.
Le fichier est copié dans un volume Docker et les métadonnées sont enregistrées
dans PostgreSQL. La réponse expose le statut et la taille en octets.
POST /documents conserve son contrat JSON de création de métadonnées.

| Statut | Signification |
| --- | --- |
| METADATA_ONLY | Aucun fichier importé, notamment les documents créés avant J4 |
| UPLOADED | Fichier stocké ; extraction et indexation pas encore réalisées |
| DELETING | Suppression commencée ; une nouvelle requête DELETE peut la terminer |

Les statuts de traitement seront ajoutés avec le pipeline. UPLOADED ne signifie
pas que le document est prêt à répondre à des questions.

## Ordre de lecture

1. `app/documents/routes/documents.py` : formulaire HTTP, validation, réponses d'erreur.
2. `app/documents/dependencies.py` : stockage concret et session injectés au service.
3. `app/documents/service.py` : upload, compensation et suppression reprenable.
4. `app/documents/storage.py` : copie par blocs, fichier temporaire, suppression.
5. `app/documents/status.py`, `models.py` et `schemas.py` : état persisté et exposé.
6. `migrations/versions/0002_document_upload.py` : adaptation des documents existants.
7. `tests/test_uploads.py`, `test_upload_failures.py` et `test_document_migration.py`.

## Flux de l'upload

FastAPI parse le multipart et fournit un `UploadFile`. Son `.file` est un objet
fichier temporaire manipulable par du code Python synchrone. Le router transmet
ce flux au service, pas l'objet HTTP lui-même. FastAPI ferme l'UploadFile après
utilisation ; notre code ferme le fichier de destination via un `with`.

Le service vérifie l'extension et l'en-tête `%PDF-`. Il génère un UUID puis demande
au stockage de copier le flux. La copie lit des blocs de 64 Kio, compte les octets
et refuse de dépasser 10 Mio. Elle écrit d'abord `.UUID.part`, puis renomme le
fichier en `UUID.pdf`. Un échec de copie déclenche le nettoyage du temporaire.

Le service ouvre ensuite une transaction courte pour enregistrer la ligne SQL.
Il n'occupe pas une transaction SQL pendant la copie du fichier. Si l'INSERT/flush
échoue avant le commit, il tente de supprimer le fichier : c'est une **compensation**.
Une fois le commit commencé, son résultat peut être incertain si la connexion tombe.
Le fichier est alors conservé et son UUID journalisé, même si l'API retourne une
erreur : on préfère un éventuel orphelin à la perte d'un fichier déjà référencé.

Le nom reçu, même s'il contient des séparateurs de chemin, reste une métadonnée.
Il ne décide jamais où le serveur écrit. Deux PDF appelés `contrat.pdf` ont des
UUID différents et ne s'écrasent pas. Le type MIME déclaré par le client ne sert
pas de preuve du format du fichier.

## Pourquoi une suppression en plusieurs étapes ?

Une transaction SQL ne peut pas annuler un `unlink()` sur le disque.

Les documents METADATA_ONLY sont supprimés uniquement en SQL, sans dépendre du
disque. Pour les documents importés :

1. Une transaction marque DELETING, avec verrouillage de la ligne.
2. Le stockage supprime le fichier ; son absence est considérée comme un succès.
3. Une autre transaction supprime la ligne PostgreSQL.

Si le disque échoue, le router retourne 503 et la ligne reste DELETING. Si le
dernier commit est annulé, la ligne reste également DELETING, sans fichier.
Si seule sa confirmation est perdue, la ligne peut déjà avoir disparu.
DELETE peut être rejoué. Après une suppression complète,
une nouvelle suppression donne 404, comme auparavant.

Ce sont volontairement plusieurs transactions autour d'une opération impliquant
deux systèmes. Le service reste responsable de leur orchestration ; le repository
ne commit jamais. La logique J2 « une transaction par méthode » était adaptée au
CRUD purement SQL ; elle ne suffit plus pour coordonner SQL et le disque.

## Limites explicites de cette étape locale

- L'en-tête et l'extension ne prouvent pas que tout le PDF est valide. Le parsing,
  les PDF corrompus, chiffrés ou sans texte seront traités en J5.
- La limite est appliquée au fichier après parsing multipart et pendant la copie.
  Elle ne bloque pas tout le corps HTTP avant réception : UploadFile a déjà pu
  utiliser du stockage temporaire. Une limite réseau sera nécessaire avant une
  exposition publique ; le serveur reste accessible localement uniquement.
- Un arrêt brutal entre la copie et le commit SQL peut laisser un fichier orphelin.
  Un échec du nettoyage après un flush refusé, ou un résultat de commit incertain,
  est journalisé. Il n'y a pas encore de
  tâche de réconciliation automatique ; ne pas présenter cette solution comme une
  transaction distribuée atomique.
- Les fichiers et PostgreSQL sont dans deux volumes distincts : sauvegarder les
  deux ensemble. `docker compose down --volumes` supprime les deux jeux de données.

Les tests simulent une interruption de lecture, un échec de commit, un échec de
suppression et un échec du commit final. Les opérations PostgreSQL restent réelles.
Le stockage de test utilise des répertoires temporaires indépendants du volume local.

## Repères et questions

`UploadFile` est proche d'un UploadedFile Symfony. Le service correspond au cas
d'usage d'import ; le stockage est un composant concret dédié aux fichiers.
`try/except` permet la compensation, `with` garantit la fermeture d'une ressource.

1. Pourquoi ne pas stocker le fichier sous le nom fourni par le client ?
2. Pourquoi un rollback SQL ne suffit-il pas à annuler l'import complet ?
3. Pourquoi garder DELETING si la suppression du fichier échoue ?
4. Que garantit la vérification `%PDF-`, et que ne garantit-elle pas ?
5. Pourquoi copier par blocs plutôt que charger tout le fichier en mémoire ?

Références : [UploadFile et multipart](https://fastapi.tiangolo.com/tutorial/request-files/),
[types Enum et contraintes SQLAlchemy](https://docs.sqlalchemy.org/en/20/core/type_basics.html).
