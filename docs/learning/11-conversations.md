# J12 — Conversations persistées et questions depuis React

## Ce qui a été construit

Une conversation appartient à un document. On peut en créer plusieurs, retrouver
leur historique et poser une question depuis React. Le pipeline RAG de J9 est
réutilisé : recherche de passages, contexte, génération et validation des citations.
Les échanges sont stockés dans PostgreSQL et survivent au rechargement de la page.

## Lecture conseillée

1. `backend/app/conversations/models.py` et la migration `0006_conversations.py` :
   relations, cascade, ordre des échanges et stockage des sources.
2. `backend/app/conversations/schemas.py` : contrats HTTP.
3. `backend/app/conversations/repository.py` : SQL sans commit.
4. `backend/app/conversations/service.py` : orchestration et transactions.
5. `backend/app/conversations/router.py` et `dependencies.py` : frontière HTTP et
   construction des services avec une session commune à la requête.
6. `frontend/src/conversations/ConversationPanel.tsx` : liste et sélection.
7. `ConversationThread.tsx`, `ExchangeCard.tsx` et `api.ts` dans le même répertoire :
   historique, envoi de question, affichage et transport HTTP.
8. `frontend/src/api/client.ts` : transport commun Documents/Conversations.

## Flux d’une question

Bouton → callback du formulaire → POST `/conversations/{id}/messages` → validation
Pydantic → `ConversationService.ask()` → lecture du document associé →
`DocumentAnswerService.ask()` → recherche et génération Gemini → validation des
sources → transaction de publication → réponse HTTP → rechargement de l’historique
→ composants React.

Le navigateur ne choisit pas librement un autre document à chaque question : le
backend utilise celui de la conversation. La clé Gemini reste dans le backend.
Une création de conversation ne déclenche aucun appel au fournisseur.

## Un échange complet dans une ligne

`ConversationMessage` représente ici un échange : question, réponse, abstention
éventuelle et sources. Ce choix simple correspond au fonctionnement question/réponse
actuel. Ce n’est pas encore une liste générique de messages avec rôles system,
user, assistant ou tool : ces rôles ne sont pas nécessaires à ce périmètre.

Une panne Gemini ne laisse pas une demi-conversation avec une question orpheline.
L’échange n’est inséré qu’après une génération et une validation réussies.
Une erreur pendant l’écriture annule toute la publication.
Une abstention valide est une réponse réussie et reste enregistrée avec zéro source.

Cela ne fournit pas une garantie « exactement une fois » entre HTTP et PostgreSQL :
si la réponse HTTP est perdue après le commit, le client peut croire à un échec alors
que l’échange existe. L’interface invite à recharger avant de renvoyer ; aucune
relance automatique. Une clé d’idempotence serait une évolution possible.

## Transactions courtes et concurrence

Les appels externes s’exécutent sans transaction SQL ouverte. Après génération,
le service vérifie de nouveau le document sous verrou : existence, statut INDEXED,
modèle et dimensions compatibles. Il verrouille ensuite la conversation et
attribue le numéro de séquence suivant avant l’insertion, dans la même transaction.

L’ordre de verrouillage reste document puis conversation. Deux publications
concurrentes ne peuvent pas choisir la même séquence ; une contrainte unique
`(conversation_id, sequence)` complète cette règle côté base. L’ordre enregistré
est celui des publications, pas forcément celui des clics si plusieurs clients
interrogent la conversation simultanément.

## Sources et suppression

Les sources sont des instantanés JSONB validés : texte du passage, numéro de page,
positions et identifiants au moment de la réponse. Une ancienne réponse garde
ainsi les extraits qui la justifiaient, même si les chunks évoluent. JSONB reste
un type de colonne PostgreSQL ; la structure des éléments est validée par Pydantic.

Supprimer un document supprime également ses conversations et leurs échanges via
les clés étrangères avec `ON DELETE CASCADE`. L’historique n’est donc pas une archive
indépendante du document. Une suppression échouée au niveau fichier peut laisser
le document en DELETING ; aucune nouvelle question n’y est autorisée.

## Historique stocké et contexte du modèle

**Conserver un historique ne donne pas automatiquement une mémoire au LLM.**
Pour cette étape, chaque génération reçoit uniquement la question actuelle et
les passages retrouvés. L’interface l’indique explicitement.

« Quelle est la durée du préavis ? » peut fonctionner. Après cette question,
« Et pendant celle-ci ? » reste ambigu : le modèle ne reçoit pas l’échange précédent.
Il faut reformuler une question autonome. Ajouter une mémoire demanderait de
choisir quels échanges transmettre, de borner les tokens et de tester les relances.

## React et erreurs

Le panneau est associé au document via sa `key`, le fil à la conversation via sa
propre `key`. Changer de sélection recrée l’état correspondant. Les effets nettoient
les anciens chargements et ignorent leurs réponses devenues obsolètes.

Pendant un envoi, les changements de document et de conversation sont bloqués pour
éviter d’afficher une réponse dans le mauvais fil. Après un quota ou une panne,
le texte saisi est conservé et les contrôles sont réactivés.
La pagination demande 21 éléments, en affiche 20 et avance par 20. Après publication,
la séquence du nouvel échange permet de charger la page qui le contient.

Les réponses et extraits sont affichés en texte React, sans HTML injecté. Les
citations restent consultables comme extraits ; l’ouverture du PDF à la page citée
appartient à J13.

## Différences utiles avec Symfony / NestJS

Les responsabilités métier restent familières : controller/router, service et
repository. En Python, `with session.begin()` délimite la transaction ; le service
concret existant est injecté avec `Depends`, sans introduire d’interface systématique.
Le context manager du router centralise la traduction des exceptions métier en
HTTP pour ses routes. Le service ne connaît toujours pas `HTTPException`.

## Points à expliquer

1. Pourquoi enregistrer question, réponse et sources dans la même transaction ?
2. Pourquoi l’historique affiché ne permet-il pas encore des relances implicites ?
3. Pourquoi copier le texte des sources dans l’échange plutôt que garder seulement les IDs des chunks ?
4. Pourquoi relire et verrouiller le document après l’appel Gemini ?
5. Que vérifier si l’interface annonce une erreur réseau alors que le backend a peut-être terminé ?

Statut pédagogique : à relire.
