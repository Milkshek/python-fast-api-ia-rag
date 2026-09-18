# J8 — Recherche sémantique dans un document

## Ce qui est construit

`POST /documents/{id}/search` accepte :

```json
{"question": "Quelle est la durée du préavis ?", "top_k": 5}
```

La question est nettoyée aux extrémités et limitée à 1–2000 caractères. `top_k`
est un entier de 1 à 10, par défaut 5. La réponse contient au plus ce nombre de
passages, chacun sous la forme `{ "chunk": { ... }, "score": 0.72 }`.
Le chunk contient son identifiant, le document, la page, les offsets et le texte.
Le score illustré est une similarité, pas une probabilité de réponse correcte.

## Fichiers à relire

1. `app/documents/routes/search.py` : contrat HTTP et traduction des erreurs.
2. `app/documents/schemas.py` : validation et structure de réponse.
3. `app/documents/search_service.py` : orchestration et vérifications.
4. `app/ai/embeddings.py` : `embed_query()` et appel Gemini.
5. `app/documents/repository.py` : `search_chunks()` et requête pgvector.
6. `tests/test_search.py` : classement réel en PostgreSQL et erreurs.

## Flux de la recherche

```text
Question + document sélectionné
  → vérifier INDEXED, modèle et dimensions dans une transaction courte
  → fermer la transaction
  → encoder la question avec Gemini
  → ouvrir une transaction courte et verrouiller/revérifier le document
  → filtrer les chunks du document en SQL
  → trier par distance cosinus puis ordre du chunk
  → limiter à top_k
  → retourner textes, positions et scores
```

Le vecteur de la question est temporaire. La recherche ne modifie ni l'index ni
le statut du document et ne conserve pas encore d'historique de questions.

## Compatibilité des embeddings

Questions et documents utilisent `gemini-embedding-2`, 768 dimensions et la même
normalisation. Gemini distingue les rôles avec des préfixes compatibles :

- document : `title: none | text: ...` ;
- question : `task: question answering | query: ...`.

Ces formats suivent la [documentation officielle Gemini](https://ai.google.dev/gemini-api/docs/embeddings).
Le modèle et la dimension enregistrés sont vérifiés avant la comparaison. Changer
le modèle impose de réindexer ; 768 nombres issus d'un autre modèle ne deviennent
pas compatibles simplement parce que leur longueur est identique.

## Distance, classement et top-k

pgvector calcule la distance cosinus directement dans PostgreSQL. Plus la distance
est petite, plus les directions des vecteurs sont proches. La réponse expose
`score = 1 - distance` : le score le plus grand arrive en premier. La similarité
cosinus va théoriquement de -1 à 1, avec des approximations numériques possibles.

Le filtre `document_id` intervient avant le classement limité : un meilleur
passage d'un autre document ne doit ni apparaître ni prendre une place du top-k.
L'ordre `chunk_index` départage les distances identiques de manière déterministe.

Il s'agit d'une recherche exacte, sans index approximatif HNSW/IVFFlat. Avec le
périmètre actuel de petits documents, cela garde un classement simple à vérifier.
Le nombre de vecteurs stockés et le coût de lecture devront être mesurés avant
une optimisation pour un corpus important.

**Top-k ne signifie pas k passages pertinents garantis.** Même une question hors
sujet peut obtenir des résultats. Aucun seuil de confiance arbitraire n'est ajouté.
La sélection du contexte et la réponse/abstention seront travaillées en J9–J10.

## Transactions et concurrence

L'appel Gemini a lieu hors transaction SQL pour ne pas retenir une connexion
pendant le réseau. Après cet appel, le document est relu avec `populate_existing`
pour actualiser l'objet ORM et un verrou `FOR UPDATE` protège la courte lecture
contre les écritures concurrentes du pipeline.

Une suppression terminée donne 404 ; un document passé en DELETING ou un modèle
incompatible donne 409. Si une réindexation compatible a terminé entre-temps,
la recherche peut utiliser le nouvel index. Si elle attend le verrou, la recherche
voit l'ancien index complet. Aucune publication partielle n'est visible.
Le verrou sérialise aussi brièvement les recherches du même document ; aucun
verrou n'est conservé pendant Gemini. Ce compromis convient au périmètre local.

## Erreurs

| Statut | Cause |
| --- | --- |
| 404 | Document absent |
| 409 | Document non indexé ou modèle/dimensions incompatibles |
| 422 | Question ou top_k invalide |
| 429 | Quota Gemini atteint |
| 502 | Vecteur fournisseur invalide |
| 503 | Clé absente, réseau ou fournisseur indisponible |

Les tests simulent seulement le fournisseur. Classement, filtrage et persistance
utilisent PostgreSQL/pgvector réels. Un essai Gemini contrôlé complète ces tests,
sans prouver la qualité sur tous les documents.

## Notions Python et architecture

`DocumentSearchHit` est une petite `dataclass` : elle regroupe chunk et score sans
être un modèle SQL ni un DTO HTTP. Pydantic sérialise ce résultat à la frontière
API. Le repository renvoie chunk et distance ; le service construit le résultat
métier. Aucun repository générique ni framework RAG supplémentaire n'est requis.

## Questions de compréhension

1. Pourquoi filtrer le document avant de limiter à top-k ?
2. Quelle différence entre distance cosinus, score et probabilité de bonne réponse ?
3. Pourquoi revérifier l'état et le modèle après l'appel Gemini ?
4. Que se passe-t-il pour une question sans rapport avec le document ?
5. Pourquoi cette route retourne-t-elle des passages plutôt qu'une réponse rédigée ?
