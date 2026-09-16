# J5 — Extraire le texte et conserver les pages

Statut pédagogique : à relire. Le fonctionnement technique ne vaut pas validation.

## Essayer dans Swagger

1. Importer un vrai PDF avec POST /documents/upload et relever son UUID.
2. Appeler POST /documents/{id}/extract. La requête attend le résultat.
3. Lire GET /documents/{id}/pages?limit=20&offset=0.
4. Relancer l'extraction : les pages existantes sont conservées sans doublons.

EXTRACTED signifie que le texte a été extrait. L'indexation et le RAG viendront
ensuite. UPLOADED signifie uniquement que le fichier est stocké.

## Responsabilités et ordre de lecture

- `router.py` : contrats HTTP, pagination et traduction des exceptions.
- `extraction_service.py` : cas d'usage, transactions et règles de concurrence.
- `extraction.py` : parsing pypdf et normalisation, sans HTTP ni SQL.
- `storage.py` : ouverture du fichier avec fermeture garantie par le context manager.
- `repository.py` : écritures et lectures SQL, sans commit.
- `models.py` et migration `0003_document_pages.py` : pages et statuts persistés.

Un service distinct évite de faire grossir le service d'upload et de CRUD. Les
composants restent concrets ; pas de couche générique ni de framework de pipeline.
`ExtractedPage` est une dataclass figée qui transporte numéro et texte : elle
n'est ni une entité SQLAlchemy ni un modèle HTTP Pydantic.

## Flux et transactions

Une première transaction lit le document et vérifie son état. METADATA_ONLY et
DELETING sont incompatibles avec l'extraction. Si EXTRACTED, on retourne le résultat
existant : il ne s’agit pas d’une commande de réextraction forcée. Depuis J6,
CHUNKED conserve également les résultats existants, sans modifier les chunks.

Le fichier est ensuite ouvert et parsé **hors transaction SQL**. Une deuxième
transaction verrouille la ligne, vérifie à nouveau son existence et son état,
puis écrit les pages et EXTRACTED ensemble. Une erreur SQL annule cet ensemble.
On ne garde pas une connexion transactionnelle occupée pendant le parsing.

La clé primaire composée `(document_id, page_number)` interdit deux entrées pour
la même page d'un document. La clé étrangère `ON DELETE CASCADE` supprime les pages
lorsque le document est supprimé, y compris sans relation ORM chargée en mémoire.

Une suppression concurrente peut avoir marqué DELETING ou retiré le document
pendant le parsing. Le recontrôle bloque alors la publication du résultat.
Deux extractions peuvent calculer simultanément ; seule la première publie,
l'autre retrouve EXTRACTED. On évite les doublons en base sans construire un
ordonnanceur pour ce petit traitement local.

Il n'y a pas de tâche de fond ni de statut PROCESSING persistant. Un arrêt avant
publication laisse le document réessayable. Si un commit aboutit mais sa confirmation
se perd, une nouvelle requête retrouve EXTRACTED. Le fichier source n'est pas modifié.

## Texte, pages et normalisation

Les numéros commencent à 1 et correspondent aux pages physiques du PDF, pas aux
numéros imprimés dans le contenu. Une page vide garde son numéro et un texte vide :
les pages suivantes ne sont jamais renumérotées.

Le nettoyage applique Unicode NFC, uniformise CRLF/CR vers LF, retire les caractères
NUL et les espaces en fin de ligne, puis les blancs aux extrémités de la page.
Il ne fusionne pas les mots coupés, n'invente pas de paragraphes et ne supprime pas
les en-têtes : ces heuristiques pourraient altérer le sens ou les futures sources.

L'ordre de lecture et les tableaux complexes ne sont pas garantis. Un PDF est
une description de page, pas un document contenant nécessairement une structure
sémantique exploitable. Le texte extrait doit pouvoir être vérifié contre l'original.

## Erreurs et limites

| Cas | HTTP | Conséquence |
| --- | --- | --- |
| Document absent | 404 | Pas de résultat publié |
| Métadonnées seules ou suppression commencée | 409 | État conservé |
| `invalid_pdf` | 422 | FAILED, erreur mémorisée |
| `encrypted_pdf` | 422 | FAILED ; aucun mot de passe traité |
| `no_extractable_text` | 422 | FAILED ; aucun texte exploitable dans tout le document |
| `extraction_limit_exceeded` | 422 | FAILED ; limite de pages ou caractères dépassée |
| Fichier absent ou disque indisponible | 503 | État conservé, incident de stockage |

Le code d'erreur est exposé dans `extraction_error`. Un document FAILED peut être
réessayé ; un succès remet cette valeur à null. Un fichier invalide inchangé restera
invalide : la relance n'est pas une réparation. Une panne de SQL reste une erreur
serveur et ne doit pas être présentée comme un PDF invalide.

Le parsing strict rejette les anomalies détectées par pypdf ; ce n'est pas un
validateur exhaustif de conformité PDF. Un scan sans couche texte échoue sans OCR.
Un document mixte peut réussir avec des pages sans texte ; celles-ci ne seront pas
interrogeables par le futur RAG. Les images ne sont pas transcrites.

Limites par défaut : 200 pages et 2 millions de caractères normalisés au total.
Elles bornent les résultats acceptés, **pas les pics mémoire ni le temps CPU du
parseur** : une page doit être interprétée avant le comptage de son texte. Les 10 Mio
d'upload ne limitent pas la taille décompressée des flux PDF. Cette étape vise de
petits PDF locaux de confiance ; une exposition publique demanderait une isolation
et des limites d'exécution adaptées. Les routes `def` utilisent des threads, mais
le parsing reste synchrone et le client attend sa fin.

Une migration descendante retire le texte et les erreurs, et repasse EXTRACTED /
FAILED à UPLOADED. Elle conserve les métadonnées et les fichiers, mais perd les
résultats d'extraction : un rollback de schéma n'est pas une sauvegarde.

## Questions de compréhension

1. Pourquoi conserver une page vide plutôt que renuméroter les suivantes ?
2. Pourquoi parser hors transaction puis relire le document sous verrou ?
3. Que garantit l'enregistrement des pages et du statut dans la même transaction ?
4. Pourquoi EXTRACTED ne signifie-t-il pas encore que le document est interrogeable ?
5. Pourquoi la taille du fichier PDF ne suffit-elle pas à borner la mémoire du parsing ?

Références : [extraction pypdf](https://pypdf.readthedocs.io/en/stable/user/extract-text.html),
[parsing strict](https://pypdf.readthedocs.io/en/stable/user/robustness.html).
