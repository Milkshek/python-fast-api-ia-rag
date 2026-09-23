# Démonstration locale — Document Intelligence

## Préparer l’application

Docker/Compose et `make` suffisent ; aucun Python, Node.js ou modèle local requis.
Depuis la racine :

```sh
make init
# Renseigner GEMINI_API_KEY dans .env avec sa propre clé, sans la versionner.
make up
make health
```

Utiliser un projet Gemini disposant du quota approprié. Cette application ne vérifie
pas la facturation du compte. Les appels réels transmettent la question et le texte
utile à Google. La démonstration ci-dessous utilise uniquement du texte synthétique.
Après une modification de `.env`, relancer `make up`, pas seulement `make restart`.

## Créer un PDF synthétique de deux pages

La fonction de génération existe déjà dans le module d’évaluation. Cette commande
ne contacte pas Gemini et écrit uniquement dans `reports/`, ignoré par Git :

```sh
mkdir -p reports
EVALUATION_UID=$(id -u) EVALUATION_GID=$(id -g) \
  docker compose -f compose.yaml -f compose.eval.yaml run --build --rm --no-deps \
  evaluation python -c 'from pathlib import Path; from evaluation.run import make_pdf; Path("reports/demo.pdf").write_bytes(make_pdf(["This document describes the support policy.", "The support team responds within 48 hours."]))'
```

## Parcours à présenter (environ cinq minutes)

Ouvrir http://localhost:5173, puis :

1. Importer `reports/demo.pdf`, titre « Démonstration support ».
2. Sélectionner le document et lancer Extraction, Découpage, puis Indexation.
   Expliquer que chaque étape est explicite ; l’indexation utilise Gemini.
3. Créer une conversation. Demander « Quel est le délai de réponse du support ? ».
4. Vérifier la réponse attendue : 48 heures. Ouvrir les sources puis « Voir la page 2 ».
   Vérifier le passage surligné. Le lien PDF ouvre le fichier original ; le fragment
   de page dépend du lecteur du navigateur.
5. Demander « Quel est le salaire du responsable ? ». Attendre une abstention sans
   source. Le modèle peut se tromper : une déviation est un résultat à analyser.
6. Recharger la page, sélectionner le document puis la conversation : retrouver
   les deux échanges. L’historique est conservé, mais n’est pas envoyé au modèle.

Pour illustrer la persistance, `docker compose restart api`, puis `make health` une
fois le backend disponible, et recharger l’historique. Aucune réindexation nécessaire.

Après la démo, conserver le PDF synthétique ou supprimer uniquement ce document via
`DELETE /documents/{id}` dans http://localhost:8000/docs ; relever l’UUID exact dans
`GET /documents`. La suppression retire aussi fichiers, pages, chunks et conversations.
Ne pas utiliser `docker compose down --volumes` pour nettoyer une démonstration.

## Si Gemini ne répond pas

Un 503 de génération déclenche au maximum deux reprises supplémentaires, avec budget
de relance. Si le fournisseur reste indisponible, montrer l’erreur plutôt que promettre
une réponse. Un 429 nécessite d’attendre le renouvellement du quota. Une clé absente
ou refusée nécessite de vérifier la configuration. Pas de changement automatique de modèle.

Après une coupure réseau, recharger les échanges avant de renvoyer : un commit peut
avoir réussi malgré une réponse HTTP perdue. La question reste saisie lors d’un échec.

Le [statut Gemini](https://aistudio.google.com/status) est un indicateur global, pas
une garantie de disponibilité pour chaque requête. `make health` vérifie notre API
et PostgreSQL, pas Gemini. On peut présenter pages/chunks et les tests hors ligne
si le fournisseur est indisponible ; cela ne constitue pas une nouvelle démo RAG réussie.

## Vérification reproductible

```sh
make quality        # Tests, lint, types, build et migrations ; sans Gemini
make smoke-install  # Base et volumes isolés ; nettoyés à la sortie ; sans Gemini
make evaluate       # Optionnel : corpus RAG réel, utilise le quota Gemini
```

Une seule exécution de `make smoke-install` à la fois. Le corpus d’évaluation écrit
un rapport local dans `reports/` et retire les documents qu’il crée. Relire les réponses
humainement : la validité des citations ne garantit pas la justesse de l’interprétation.

## Présenter l’architecture

React → HTTP/proxy Vite → router FastAPI → service métier → repository SQLAlchemy
→ PostgreSQL/pgvector. Les clients Gemini gèrent les appels externes. Le PDF original
est stocké dans un volume séparé ; ses pages et chunks sont en base.

Pour une question : embedding de la question → recherche dans le document sélectionné
→ contexte borné → génération structurée → contrôle des citations → transaction
courte pour publier l’échange → affichage de la réponse et des sources.

## Limites à annoncer

- Application locale de développement : Vite/Uvicorn avec rechargement, sans authentification.
- Plusieurs PDF dans la bibliothèque, un seul document interrogé par conversation.
- Texte extractible uniquement ; pas d’OCR, de compréhension des images/tableaux garantie.
- Découpage par caractères, contexte et top-k limités : une absence dans les passages
  ne prouve pas une absence dans le document complet.
- Les sources sont vérifiables mais n’éliminent pas les erreurs d’interprétation.
- Questions indépendantes, pas de relances implicites ni de clé d’idempotence.
- Traitement synchrone, limites de fichiers/chunks et disponibilité/quota Gemini.
- Multi-document, tool calling et agent : non implémentés.
