# J15 — Livrer et expliquer le MVP

## Ce qui est livré

Une application locale React/FastAPI permettant d’importer des PDF contenant du
texte, lancer extraction/découpage/indexation, poser des questions indépendantes à
un document et relire les réponses sourcées dans des conversations persistées.
Les pages peuvent être consultées avec le passage cité surligné et le PDF original.
La reprise de génération après 503 reste bornée et ne garantit pas la disponibilité
externe. Le projet n’implémente pas de comparaison multi-document, tool calling ou agent.

La [démonstration](../demo/README.md) décrit l’installation, la création d’un PDF
synthétique, le parcours et les erreurs à présenter. Ce document est une documentation
publique ; le planning et les notes d’apprentissage restent locaux et ignorés.

## Trois preuves différentes

- `make quality` : qualité statique, tests de comportement et migrations. Les clients
  Gemini sont simulés ; cela ne prouve pas que Google soit disponible.
- `make smoke-install` : installation et pipeline sans IA dans une base vide isolée,
  avec vérification du proxy frontend ; les volumes de développement sont conservés.
- Essai Gemini réel : valide un cas concret au moment de l’essai. Ni garantie permanente
  de disponibilité, ni preuve générale de justesse des réponses.

Pour expliquer la fiabilité du RAG, reprendre aussi le guide J10 et le bilan du corpus.
Un jeu d’essais fini ne prouve pas l’absence d’hallucinations sur tous les documents.

## Présentation technique en trois minutes

1. Besoin utilisateur et limites : PDF texte, question sur un document, source consultable.
2. Préparation : fichier sur disque, pages/chunks en SQL, embeddings dans pgvector.
3. Question : vecteur compatible, filtrage document avant top-k, contexte borné,
   génération JSON, validation et reconstruction des sources.
4. Persistance : service responsable de transactions courtes, appels externes hors SQL,
   échange publié atomiquement. Fichier et SQL ne partagent pas une transaction.
5. Interface : état partagé, données chargées par HTTP, gestion des réponses obsolètes,
   historique persistant mais questions indépendantes côté modèle.
6. Exploitation locale : Docker, migrations, dépendances verrouillées, tests, limites
   fournisseur et secrets conservés dans l’environnement backend.

## Revue Git

Les changements sont regroupés en commits cohérents. Une correction peut utiliser
un fixup, puis être autosquashée tant que les commits sont locaux et non partagés.
Ne pas réécrire un historique partagé sans accord explicite. À la revue J15, un ancien
fixup est déjà inclus dans la référence locale `origin/master` ; il est conservé.
Aucun push, tag de release ou déploiement n’est réalisé par cette étape.

## Checkpoint final

1. Décris le trajet complet d’une question depuis React jusqu’à une réponse sourcée,
   en précisant où ont lieu les appels Gemini et la transaction de publication.
2. Comment distinguer une API locale saine, une base accessible et un modèle disponible ?
3. Une réponse cite une page qui existe : pourquoi cela ne suffit-il pas à garantir sa justesse ?
4. Quelles données survivent à un redémarrage, et que se passe-t-il après un échec avant
   commit ou une coupure HTTP après commit ?
5. Quels compromis annoncerais-tu en entretien, et quelle extension choisirais-tu
   ensuite pour répondre à un besoin concret ?

Le jalon technique de livraison ne valide pas automatiquement ces explications.
Tool calling et agents ne sont pas des compétences validées par ce MVP.
