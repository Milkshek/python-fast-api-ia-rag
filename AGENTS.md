# AGENTS.md --- Document Intelligence Assistant

## Mission

Construire en **3 semaines (\~90 heures maximum)** une application de
Document Intelligence servant de support de formation à **Python,
FastAPI et l'IA appliquée**.

Le projet est principalement développé avec l'aide de l'IA. L'objectif
pédagogique est que l'apprenant puisse **relire, comprendre et expliquer
le code, les flux et les choix techniques**.

Le projet doit rester suffisamment concret et propre pour être présenté
sur GitHub et expliqué en entretien.

## Priorités absolues

1.  **Code standard, idiomatique et conforme aux bonnes pratiques de
    l'écosystème**
2.  **Compréhension pédagogique**
3.  **Simplicité et lisibilité**
4.  **Qualité et tests pertinents**
5.  **Respect du scope fonctionnel**
6.  **Deadline de 3 semaines**

Si la deadline entre en conflit avec les quatre premières priorités,
**réduire le scope plutôt que dégrader la qualité du code**.

> La contrainte de temps doit réduire le périmètre, jamais conduire à
> apprendre de mauvaises pratiques.

## Standard de code

### Python

Le code doit être du **Python idiomatique**, et non une transposition de
patterns PHP/Symfony ou TypeScript/NestJS.

Respecter notamment :

-   PEP 8 ;
-   type hints modernes lorsque pertinents ;
-   noms explicites en anglais ;
-   petites fonctions avec responsabilités claires ;
-   exceptions explicites ;
-   context managers lorsque pertinents ;
-   `async` / `await` uniquement avec justification technique ;
-   éviter les abstractions prématurées ;
-   préférer la bibliothèque standard lorsqu'elle suffit.

Lorsqu'une pratique Python diffère de Symfony/NestJS, utiliser la
pratique Python standard puis **expliquer la différence**.

### FastAPI

Utiliser FastAPI de manière conventionnelle :

-   `APIRouter` pour organiser les routes ;
-   Pydantic pour validation et modèles d'entrée/sortie ;
-   `Depends` lorsque pertinent ;
-   statuts HTTP cohérents ;
-   gestion explicite des erreurs ;
-   OpenAPI propre ;
-   séparation raisonnable route / logique métier / persistence ;
-   pas de Clean Architecture artificielle.

Convention retenue avec l'apprenant pour ce projet : router / service / repository.
Le router gère HTTP, le service les cas d'usage et les transactions, le repository
les opérations SQLAlchemy sans commit. Les erreurs métier sont traduites en HTTP
à la frontière API. Utiliser des composants concrets, sans repository générique
ni interfaces ajoutées systématiquement.

### Persistence

-   PostgreSQL ;
-   SQLAlchemy **2.x** et son API moderne ;
-   Alembic pour les migrations ;
-   transactions explicites lorsque nécessaire ;
-   repositories pour isoler les requêtes selon la convention du projet ;
-   ne pas masquer SQLAlchemy derrière des abstractions inutiles.

### Tests

Utiliser **pytest**.

Tester prioritairement :

-   logique métier ;
-   comportements importants des endpoints ;
-   persistence lorsque pertinent ;
-   pipeline documentaire ;
-   composants RAG critiques.

Ne pas viser artificiellement 100 % de couverture.

### Tooling

Utiliser des outils modernes, standards et largement adoptés pour le
formatting, linting, type checking, tests et la gestion des dépendances.

Éviter les dépendances exotiques lorsqu'une solution standard suffit.

## Historique Git

- Créer des commits atomiques : un changement cohérent par commit, avec ses
  tests nécessaires. Éviter de mélanger fonctionnalité et nettoyage sans rapport.
- Rattacher les corrections à leur commit d'origine avec
  `git commit --fixup=<commit>`.
- Intégrer les fixups avec un rebase autosquash avant intégration, sur les
  commits locaux non partagés. Ne pas réécrire un historique partagé sans
  autorisation explicite.

## Méthode pédagogique

Codex / l'agent **peut implémenter des features complètes**.

L'apprentissage repose principalement sur :

``` text
Implémentation
    ↓
Lecture du code
    ↓
Explication
    ↓
Questions de compréhension
    ↓
Correction
    ↓
Validation
```

Il n'est pas demandé à l'apprenant de recoder systématiquement les
features en autonomie.

Une feature qui fonctionne n'est **pas considérée comme comprise**.

## LEARNING_NOTES.md

Ce document reste local : il est ignoré par Git et ne doit pas être commité.

Après chaque grande étape, créer ou mettre à jour `LEARNING_NOTES.md`
avec :

1.  ce qui a été construit ;
2.  les fichiers importants à relire ;
3.  le flux principal ;
4.  les nouvelles notions ;
5.  les choix techniques importants ;
6.  les différences utiles avec Symfony / NestJS ;
7.  les points que l'apprenant doit savoir expliquer.

Le document doit rester synthétique.

## Questions de validation

Éviter les quiz trivia et les questions purement syntaxiques.

Privilégier :

-   Pourquoi ce composant existe-t-il ?
-   Quel est son rôle ?
-   Quel est le flux complet de cette requête ?
-   Pourquoi utilise-t-on cette dépendance ici ?
-   Pourquoi cette fonction est-elle `async` ?
-   Où est gérée la transaction ?
-   Que se passe-t-il en cas d'erreur ?
-   Quelle alternative aurait été possible ?
-   Comment Symfony/NestJS traiterait ce problème ?
-   Pourquoi cette solution est-elle plus idiomatique en Python ?

L'objectif est de pouvoir **défendre le code en entretien technique**.

## Planning --- 3 semaines

### Semaine 1 --- Python / FastAPI / PostgreSQL

-   fondamentaux Python nécessaires ;
-   FastAPI ;
-   Pydantic ;
-   SQLAlchemy 2.x ;
-   Alembic ;
-   PostgreSQL ;
-   API Documents ;
-   tests essentiels.

**Checkpoint : Python + FastAPI**

### Semaine 2 --- Documents / Embeddings / RAG

-   upload PDF ;
-   extraction ;
-   normalisation ;
-   chunking ;
-   embeddings ;
-   vector store ;
-   recherche vectorielle ;
-   LLM ;
-   Structured Outputs ;
-   **RAG complet avec réponses sourcées**.

**Checkpoint : Pipeline documentaire + LLM + Embeddings + RAG**

Le RAG est une **priorité obligatoire**.

### Semaine 3 --- React / Tool Calling / Agent

-   interface React / TypeScript minimale mais propre ;
-   intégration FastAPI ;
-   multi-document si le temps le permet ;
-   tool calling ;
-   agent simple ;
-   tests critiques ;
-   Docker ;
-   documentation ;
-   nettoyage du repository.

**Checkpoint : React + Tool Calling + Agents + architecture globale**

## Scope obligatoire

Le MVP doit permettre :

1.  importer un document ;
2.  extraire son contenu ;
3.  le découper en chunks ;
4.  produire et stocker ses embeddings ;
5.  rechercher les chunks pertinents ;
6.  poser une question ;
7.  générer une réponse avec un LLM ;
8.  afficher les sources utilisées ;
9.  utiliser l'application depuis React.

Si le temps le permet :

10. multi-document ;
11. extraction structurée avancée ;
12. tool calling ;
13. agent simple.

## Hors scope par défaut

Ne pas ajouter sans besoin pédagogique explicite :

-   microservices ;
-   Kubernetes pour le déploiement ;
-   architecture enterprise ;
-   event sourcing ;
-   CQRS ;
-   authentification complexe ;
-   permissions avancées ;
-   observabilité complète ;
-   infrastructure cloud avancée ;
-   optimisation prématurée ;
-   framework agentique lourd ;
-   abstractions anticipant des besoins hypothétiques ;
-   couverture de tests exhaustive.

## RAG --- règle d'explicitation

Le premier RAG doit laisser apparaître clairement :

``` text
Document
    ↓
Extraction
    ↓
Chunking
    ↓
Embeddings
    ↓
Vector Store
    ↓
Retrieval
    ↓
Construction du contexte
    ↓
LLM
    ↓
Réponse + Sources
```

Ne pas masquer ce pipeline derrière une abstraction opaque avant que les
concepts aient été compris.

Même règle pour les agents :

``` text
Demande
    ↓
Décision
    ↓
Tool Call
    ↓
Exécution
    ↓
Résultat
    ↓
Réponse
```

## Produit cible

L'utilisateur importe des documents puis les interroge en langage
naturel.

Exemples :

-   « Quelle est la durée du préavis ? »
-   « Résume ce document. »
-   « Compare ces deux contrats. »
-   « Quels documents parlent de RabbitMQ ? »
-   « Quelles sont les clauses importantes ? »

Toute réponse documentaire doit autant que possible indiquer ses
**sources**.

## API initiale

``` http
POST   /documents
GET    /documents
GET    /documents/{id}
DELETE /documents/{id}

POST   /conversations
GET    /conversations/{id}
POST   /conversations/{id}/messages
```

## Architecture initiale

``` text
app/
├── api/
├── documents/
├── conversations/
├── ai/
├── database/
├── infrastructure/
└── main.py
```

Cette structure est une base et non une obligation dogmatique. Elle
évolue uniquement lorsqu'un besoin concret le justifie.

## Phases techniques

### Python moderne

Notions importantes :

-   structures de données ;
-   fonctions et classes ;
-   modules et packages ;
-   typing ;
-   dataclasses ;
-   exceptions ;
-   generators ;
-   context managers ;
-   async / await ;
-   pytest.

### FastAPI

Notions importantes :

-   routers ;
-   dependency injection ;
-   Pydantic ;
-   validation ;
-   erreurs ;
-   SQLAlchemy ;
-   PostgreSQL ;
-   Alembic ;
-   OpenAPI ;
-   tests ;
-   async.

Comparaisons utiles :

``` text
Symfony             NestJS              FastAPI

Controller       →  Controller       →  Router
Service          →  Provider         →  Service
DTO              →  DTO              →  Pydantic Model
Validator        →  class-validator  →  Pydantic
Doctrine         →  TypeORM          →  SQLAlchemy
Migrations       →  TypeORM          →  Alembic
DI               →  DI NestJS        →  Depends
```

### Traitement documentaire

``` text
Document
   ↓
Extraction
   ↓
Normalisation
   ↓
Chunking
   ↓
Indexation
```

À comprendre :

-   upload ;
-   PDF ;
-   métadonnées ;
-   stratégies de chunking ;
-   sync vs async ;
-   erreurs ;
-   statuts ;
-   idempotence.

### LLM et Structured Outputs

À comprendre :

-   system / user messages ;
-   tokens ;
-   context window ;
-   température ;
-   hallucinations ;
-   prompt engineering ;
-   structured outputs.

### Embeddings et recherche vectorielle

À comprendre :

-   embeddings ;
-   similarité ;
-   vectorisation ;
-   recherche sémantique ;
-   top-k ;
-   métadonnées ;
-   vector store.

### RAG

``` text
Question
   ↓
Recherche
   ↓
Contexte pertinent
   ↓
LLM
   ↓
Réponse
   ↓
Sources
```

À comprendre :

-   retrieval ;
-   grounding ;
-   ranking ;
-   citations ;
-   réduction des hallucinations ;
-   traçabilité.

### Multi-document

-   questions sur plusieurs documents ;
-   comparaison ;
-   recherche globale ;
-   filtres ;
-   historique.

### Tool Calling

Outils possibles :

``` python
search_documents()
get_document_page()
compare_documents()
extract_structured_data()
generate_summary()
```

À comprendre :

-   schemas ;
-   validation des arguments ;
-   orchestration ;
-   erreurs ;
-   contrôle des actions.

### Agent IA

À comprendre :

-   workflow vs agent ;
-   autonomie contrôlée ;
-   boucles ;
-   erreurs ;
-   tracing ;
-   coûts ;
-   sécurité.

Ne pas commencer avec un framework agentique complexe.

### React

Interface minimale :

``` text
┌─────────────────┬──────────────────────────┐
│   Documents     │      Conversation        │
│                 │                          │
│ contrat.pdf     │ User: ...                │
│ facture.pdf     │                          │
│ specs.pdf       │ AI: ...                  │
└─────────────────┴──────────────────────────┘
```

Fonctionnalités :

-   upload ;
-   liste et statut des documents ;
-   sélection ;
-   conversation ;
-   affichage des sources ;
-   navigation vers une source.

## Principes d'architecture

Toujours privilégier :

-   KISS ;
-   YAGNI ;
-   forte cohésion ;
-   faible couplage ;
-   responsabilités explicites ;
-   code testable ;
-   dépendances maîtrisées ;
-   lisibilité avant sophistication.

SOLID est utilisé lorsqu'il améliore réellement le code, pas pour
multiplier les couches.

Rechercher un compromis entre lisibilité, performance et maintenance humaine :

- Extraire une fonction lorsqu'elle nomme une responsabilité cohérente et facilite
  la compréhension ; éviter le découpage qui multiplie les allers-retours sans gain.
- Tenir compte des coûts concrets : requêtes SQL, entrées/sorties, mémoire et
  complexité algorithmique, dès la conception.
- Justifier les optimisations qui compliquent le code par un besoin concret ou
  des mesures ; ne pas sacrifier la lisibilité pour un gain hypothétique.
- Garder le flux principal et les comportements en cas d'erreur faciles à suivre
  pour une personne qui découvre le code.

> **Si deux solutions répondent au besoin, choisir celle qui expose le
> mieux les concepts à apprendre avec le moins de complexité
> accidentelle.**

## Validation des notions

Statuts :

``` text
À découvrir
À relire
Compris
Validé
```

Une notion est `Validée` lorsque :

-   elle a été rencontrée dans le projet ;
-   le code correspondant a été relu ;
-   son rôle est compris ;
-   les questions importantes reçoivent des réponses correctes ;
-   le choix technique peut être expliqué avec ses propres mots.

Aucun exercice de recodage autonome n'est obligatoire.

## Checkpoints

### Checkpoint 1 --- Python + FastAPI

-   typing ;
-   Pydantic ;
-   routers ;
-   dependency injection ;
-   SQLAlchemy ;
-   Alembic ;
-   async / await ;
-   cycle d'une requête ;
-   tests.

### Checkpoint 2 --- Pipeline documentaire + RAG

-   traitement de fichiers ;
-   statuts ;
-   idempotence ;
-   chunking ;
-   embeddings ;
-   recherche vectorielle ;
-   retrieval ;
-   grounding ;
-   ranking ;
-   sources.

### Checkpoint 3 --- Tool Calling + Agents + Full Stack

-   architecture React ;
-   appels API ;
-   gestion des erreurs ;
-   tool schemas ;
-   orchestration ;
-   workflow vs agent ;
-   autonomie ;
-   sécurité ;
-   coûts ;
-   flux complet frontend → backend → IA → sources.

## Definition of Done

Le projet est terminé lorsque l'utilisateur peut :

1.  importer plusieurs documents ;
2.  attendre leur traitement ;
3.  sélectionner un ou plusieurs documents ;
4.  poser une question ;
5.  obtenir une réponse basée sur les documents ;
6.  consulter les sources utilisées ;
7.  utiliser l'ensemble depuis React.

Selon le temps restant :

8.  comparer plusieurs documents ;
9.  demander des extractions structurées ;
10. utiliser du tool calling ;
11. utiliser un agent simple.

Le projet final doit être :

-   testé sur les comportements critiques ;
-   dockerisé ;
-   documenté ;
-   versionné avec Git ;
-   présentable sur GitHub ;
-   explicable techniquement en entretien.

## Compétences visées

``` text
Python
FastAPI
Pydantic
SQLAlchemy 2.x
Alembic
PostgreSQL
pytest
React
TypeScript
Docker

LLM Integration
Structured Outputs
Embeddings
Vector Search
RAG
Tool Calling
AI Agents
```

Le but n'est pas de devenir Data Scientist ou ML Engineer.

> **Positionnement cible : Senior Full Stack Software Engineer capable
> de concevoir un produit web complet et d'y intégrer des
> fonctionnalités IA modernes.**
