# J9 — Réponse rédigée et sources

## Ce qui est construit

Après upload, extraction, chunking et indexation :

```http
POST /documents/{id}/ask
Content-Type: application/json

{"question": "Quelle est la durée du préavis ?"}
```

La réponse contient `answer` (texte), `abstained` (booléen) et `sources`
(liste de `{id, chunk}`). Chaque chunk contient UUID, document, page, offsets et
texte exact. Les identifiants de source 1 à 5 sont locaux à cette réponse ; ils
ne remplacent pas les UUID persistants des chunks.

## Lecture conseillée

1. `app/documents/routes/answers.py` : HTTP et traduction des erreurs.
2. `app/documents/services/answers.py` : orchestration RAG, contexte et citations.
3. `app/ai/answers.py` : prompt, appel REST Gemini et validation de sortie.
4. `app/documents/schemas/answers.py` : modèles d'entrée/sortie HTTP.
5. `tests/test_answers.py`, `tests/test_answer_client.py` : garanties testées.

## Flux visible du premier RAG

```text
Question
  → recherche J8 : embedding → filtre document → top-5 passages
  → sélection d'un contexte borné
  → question + passages envoyés au modèle de génération
  → JSON du modèle validé par Pydantic
  → vérification des identifiants cités
  → relecture du document après l'appel réseau
  → texte de réponse + sources reconstruites depuis les chunks locaux
```

Les embeddings restent produits par `gemini-embedding-2`. Le texte de réponse est
produit par `gemini-3.1-flash-lite`, avec la même clé `GEMINI_API_KEY`. Ces deux modèles
ont des rôles différents : recherche et génération. Les vecteurs ne sont jamais
envoyés au modèle de génération ; on lui envoie le texte des passages.

Ce modèle figure dans l'[offre gratuite Gemini](https://ai.google.dev/gemini-api/docs/pricing)
consultée pour J9. L'accès effectif dépend du compte et des quotas. Aucun retry,
fallback payant ou changement de modèle automatique. L'application ne vérifie pas
l'état de facturation du projet ; conserver le projet gratuit choisi en J7.

## Contexte et limites

Le service récupère cinq passages au maximum et transmet un préfixe de cette liste
ne dépassant pas 5000 caractères de texte. Les passages restent complets : pas de
troncature qui fausserait leurs offsets. Si le prochain passage dépasse le budget,
la sélection s'arrête. La question est limitée à 2000 caractères.

Les caractères et les tokens ne sont pas équivalents. Un token est une unité de
texte du modèle, parfois un mot, souvent une partie de mot. Le budget de contexte
borne ici les textes en caractères, auxquels s'ajoutent les consignes et la
structure JSON. La génération est limitée à 2048 tokens de sortie. Un arrêt
`MAX_TOKENS` est refusé : on ne publie pas une réponse partielle.

Le timeout HTTP est de 30 secondes par phase réseau, pas une échéance globale
stricte du RAG. La recherche ajoute son propre appel d'embedding et ses lectures SQL.

## Prompt et sortie structurée

`systemInstruction` porte les règles : répondre à partir des passages, traiter
les instructions du document comme des données et s'abstenir si l'information
manque. Le message utilisateur contient un JSON avec question et passages.
Ce cloisonnement guide le modèle ; ce n'est pas une garantie absolue contre une
injection de prompt ou une hallucination.

Le contrat de génération contient :

```json
{"answer": "Le préavis est de trois mois.", "abstained": false, "source_ids": [1]}
```

Le schéma envoyé au fournisseur contraint la forme. Pydantic vérifie encore la
réponse côté backend : types stricts, champs attendus, taille du texte et IDs.
Cela ne prouve pas la véracité du contenu.

Le service vérifie en plus :

- chaque référence correspond à un passage effectivement envoyé ;
- aucun doublon ;
- une réponse affirmative cite au moins un passage ;
- une abstention ne cite aucun passage.

Le modèle ne fournit ni UUID, ni page, ni offsets : le backend les récupère à partir
des sources sélectionnées. Une citation valide prouve sa traçabilité, **pas que le
passage soutient chaque affirmation**. Cette qualité sera évaluée en J10.

Référence technique : [GenerateContent et sa configuration](https://ai.google.dev/api/generate-content).

## Abstention, erreurs et transactions

Sans contexte, le service s'abstient sans appeler le modèle de génération.
Si le modèle s'abstient, le backend utilise un message fixe : les passages disponibles
ne permettent pas de répondre. On ne prétend pas que tout le document ne contient
pas la réponse : la recherche a peut-être manqué un passage utile.

Aucune transaction SQL n'est ouverte pendant les deux appels Gemini. Après la
génération, une courte transaction recharge le document sous verrou et vérifie
qu'il existe encore, qu'il est INDEXED et compatible. Une réindexation compatible
est acceptable car elle ne change pas les chunks. La réponse représente les
passages lus ; elle ne garantit pas leur conservation après la fin de la requête.

| Code | Situation |
| --- | --- |
| 404 | Document absent ou supprimé pendant l'appel |
| 409 | Document non indexé, en suppression ou index incompatible |
| 422 | Question invalide |
| 429 | Quota fournisseur atteint |
| 502 | Sortie JSON/citations invalides, réponse bloquée ou tronquée |
| 503 | Clé absente, erreur réseau ou fournisseur indisponible |

L'index n'est pas modifié. Les questions/réponses ne sont pas persistées ; les
conversations et leur historique viendront en J12.

## Notions à expliquer

- Retrieval : choisir les passages ; génération : rédiger à partir des passages.
- Grounding : ancrer la réponse dans les données fournies.
- Structured output : contraindre la forme de sortie, sans garantir la vérité.
- Prompt : règles système + question + contexte documentaire.
- Dataclasses : résultats internes ; Pydantic : contrats HTTP et fournisseur.

## Questions de compréhension

1. Pourquoi ne pas envoyer les vecteurs au modèle qui rédige la réponse ?
2. Qu'apporte le JSON structuré, et que ne garantit-il pas ?
3. Pourquoi reconstruire les sources côté backend ?
4. Quelle différence entre « aucune information dans les passages récupérés » et
   « aucune information dans le document » ?
5. Pourquoi une réponse avec des citations valides peut-elle quand même être fausse ?
