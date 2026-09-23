# Référence API

L’API locale est disponible sur `http://localhost:8000`. Après `make up`, utiliser
[Swagger UI](http://localhost:8000/docs) pour les schémas complets et les essais.
Cette application locale ne fournit pas d’authentification.

## Documents et pipeline

| Méthode | Route | Rôle |
| --- | --- | --- |
| POST | `/documents` | Créer uniquement les métadonnées (`title`, `filename`), 201 |
| POST | `/documents/upload` | Importer un PDF multipart (`title`, `file`), 201 |
| GET | `/documents` | Liste paginée avec `limit` / `offset` |
| GET | `/documents/{id}` | Consulter les métadonnées et le statut |
| DELETE | `/documents/{id}` | Supprimer le document et ses données associées, 204 |
| POST | `/documents/{id}/extract` | Extraire et normaliser le texte par page |
| GET | `/documents/{id}/pages` | Lister les pages, avec `limit` / `offset` |
| GET | `/documents/{id}/pages/{page_number}` | Lire une page extraite précise |
| GET | `/documents/{id}/file` | Transférer le PDF original, inline, avec support `Range` |
| POST | `/documents/{id}/chunk` | Découper les pages en passages |
| GET | `/documents/{id}/chunks` | Lister les passages et positions, avec `limit` / `offset` |
| POST | `/documents/{id}/index` | Calculer et stocker les embeddings |
| POST | `/documents/{id}/search` | Retourner les passages classés par similarité |
| POST | `/documents/{id}/ask` | Générer une réponse sourcée sans persister l’échange |

Les créations retournent un en-tête `Location`. Les listes acceptent au maximum
100 éléments par page. La liste Documents est ordonnée par date de création puis
UUID. Les UUID ou paramètres invalides donnent 422, les documents absents 404.

### Import et préparation

```sh
curl --fail http://localhost:8000/documents/upload \
  -F 'title=Contrat de démonstration' \
  -F 'file=@/chemin/vers/contrat.pdf;type=application/pdf'

# Remplacer UUID par l’identifiant retourné.
curl --fail -X POST http://localhost:8000/documents/UUID/extract
curl --fail -X POST http://localhost:8000/documents/UUID/chunk
curl --fail -X POST http://localhost:8000/documents/UUID/index
```

Les étapes sont synchrones et explicites : `UPLOADED` → `EXTRACTED` → `CHUNKED`
→ `INDEXED`. Une création JSON sans fichier donne `METADATA_ONLY`. Une erreur
d’extraction donne `FAILED` avec `extraction_error`. Une suppression interrompue
reste `DELETING` et peut être relancée avec DELETE.

Le titre accepte 1 à 200 caractères ; le nom de fichier 1 à 255 après nettoyage.
Le nom original reste une métadonnée : seul l’UUID détermine le chemin local.
Les champs supplémentaires des corps JSON sont refusés.

| Étape | Limites et comportement |
| --- | --- |
| Upload | 10 Mio ; en-tête `%PDF-` et extension contrôlés ; ce contrôle ne valide pas le PDF entier |
| Extraction | 200 pages, 2 millions de caractères normalisés ; refus des PDF illisibles, chiffrés ou sans texte extractible |
| Découpage | 1 000 caractères, 200 de recouvrement, page par page ; texte, page et offsets conservés |
| Indexation | 100 chunks maximum ; `gemini-embedding-2`, 768 dimensions |
| Génération | Au plus 5 passages complets, 5 000 caractères de contexte documentaire ; `gemini-3.1-flash-lite` |

La limite d’upload intervient après parsing multipart ; celle de l’extraction ne
borne pas la mémoire du parseur. Pas d’OCR ni de traitement en arrière-plan.
Une relance réussie d’extraction/découpage conserve le résultat existant.
L’indexation conserve l’index existant sauf `?force=true` ; une réindexation échouée
conserve l’ancien index. Les embeddings ne sont pas réessayés automatiquement.

### Recherche et réponse

Envoyer à `/documents/{id}/search` :

```json
{"question": "Quelle est la durée du préavis ?", "top_k": 5}
```

La question accepte 1 à 2 000 caractères après nettoyage ; `top_k` va de 1 à 10,
avec 5 par défaut. La recherche encode la question avec Gemini, filtre sur le
document puis classe les chunks par distance cosinus. Le score n’est pas une
probabilité de bonne réponse. La recherche ne modifie pas l’index.

Envoyer à `/documents/{id}/ask` uniquement le champ `question`. La réponse contient
`answer`, `abstained` et `sources`. Chaque source contient un identifiant et le chunk
avec document, page, offsets et texte. Les citations sont contrôlées et reconstruites
côté backend. En cas d’abstention, la liste des sources est vide. Cela ne garantit
pas que le modèle détectera toujours une information manquante ou interprétera
correctement une condition.

## Conversations

| Méthode | Route | Rôle |
| --- | --- | --- |
| POST | `/conversations` | Créer avec `{"document_id":"UUID"}`, document indexé requis |
| GET | `/conversations?document_id=UUID` | Liste, plus récentes d’abord, avec `limit` / `offset` |
| GET | `/conversations/{id}` | Consulter une conversation |
| GET | `/conversations/{id}/messages` | Échanges par séquence croissante, avec `limit` / `offset` |
| POST | `/conversations/{id}/messages` | Poser une question et enregistrer l’échange, 201 |

Un message contient la question, la réponse, l’abstention éventuelle et un instantané
des sources. Les appels Gemini sont hors transaction SQL ; la publication finale
est atomique après revérification et verrouillage. Les échecs fournisseur ne créent
pas d’échange incomplet. Une réponse HTTP perdue après commit laisse toutefois
l’échange enregistré : relire l’historique avant un renvoi manuel.

Les questions sont indépendantes ; l’historique n’est pas transmis au modèle.
Supprimer un document supprime aussi ses pages, chunks, embeddings et conversations,
ainsi que le fichier original. Les écritures SQL et le stockage disque ne partagent
pas une transaction : voir les [limites de compensation](learning/03-upload.md).

## Sources et erreurs

La page extraite est du texte en base, pas une reproduction visuelle du PDF.
Le lien `/documents/{id}/file#page=2` laisse le lecteur PDF interpréter le fragment.
Une suppression concurrente après contrôle du fichier peut faire échouer le transfert.
La transaction SQL est terminée avant celui-ci. Le surlignage React vérifie que le
texte actuel correspond toujours à l’instantané de la citation.

| HTTP | Cas principaux |
| --- | --- |
| 400 / 413 / 415 | Fichier vide / trop volumineux / format refusé |
| 404 | Document, conversation ou page absent |
| 409 | État incompatible avec l’opération demandée |
| 422 | Données invalides ou PDF non exploitable à l’extraction |
| 429 | Quota Gemini atteint |
| 502 | Réponse Gemini invalide, bloquée ou tronquée |
| 503 | Stockage ou fournisseur indisponible, erreur réseau ou configuration manquante |

Les 503 de **génération** sont repris au maximum deux fois, après 1 puis 2 secondes,
avec budget de relance de 30 secondes. Les timeouts sont limités au temps restant
mais s’appliquent par phase réseau, pas comme une deadline absolue. Ni recherche ni
persistance ne sont rejouées. Quota, timeout, autres statuts et réponse invalide ne
sont pas réessayés. Après échec persistant, une erreur spécifique indique
l’indisponibilité temporaire du modèle. Voir le [guide de résilience](learning/13-generation-resilience.md).
