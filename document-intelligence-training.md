# Document Intelligence Assistant

## Projet de formation Python / FastAPI / IA

### Objectif

Construire une application de **Document Intelligence** permettant
d'importer des documents, d'en extraire le contenu et de les interroger
en langage naturel avec des réponses sourcées.

Le projet est avant tout un support de formation pour progresser sur :

-   Python moderne
-   FastAPI
-   Pydantic
-   SQLAlchemy / Alembic
-   PostgreSQL
-   pytest
-   React / TypeScript
-   Docker
-   LLM
-   Structured Outputs
-   Embeddings
-   RAG
-   Vector Search
-   Tool Calling
-   Agents IA

L'objectif est de faire développer l'application principalement par
l'IA, puis de **relire et comprendre le code produit**. La formation ne
repose pas sur la réalisation autonome d'exercices : les notions
importantes sont validées par des **questions de compréhension après les
grandes étapes du plan de développement**.

------------------------------------------------------------------------

## Méthode pédagogique

Le projet est développé principalement avec l'aide de l'IA. L'objectif
pédagogique est de **comprendre le code généré, les choix techniques et
les notions importantes**, et non de coder chaque feature manuellement.

Pour chaque grande étape du plan :

1.  développer la fonctionnalité prévue ;
2.  relire le code produit ;
3.  expliquer les nouvelles notions rencontrées ;
4.  les comparer à Symfony et/ou NestJS lorsque pertinent ;
5.  identifier les choix d'architecture et leurs conséquences ;
6.  poser une série de questions ciblées sur les notions importantes ;
7.  corriger et expliquer les réponses incomplètes ou incorrectes ;
8.  valider l'étape lorsque les notions essentielles sont comprises.

Une notion est **validée par la compréhension**, au travers des réponses
aux questions de révision.

Les questions doivent privilégier : - le rôle d'un composant ; - le
cheminement d'une requête ou d'une donnée ; - les responsabilités des
différentes couches ; - les raisons d'un choix technique ; - les
alternatives possibles ; - les erreurs et risques courants ; - les
différences avec Symfony / NestJS lorsque cela aide à comprendre.

L'IA agit comme **développeur, formateur et reviewer**. Elle peut
produire le code du projet, mais doit ensuite aider à le relire et
vérifier que les notions structurantes sont comprises.

------------------------------------------------------------------------

## Produit cible

``` text
Upload PDF
    ↓
Extraction
    ↓
Chunking
    ↓
Embeddings
    ↓
Vector Store
    ↓
Question
    ↓
Recherche des passages pertinents
    ↓
LLM
    ↓
Réponse + sources
```

Exemples :

-   « Quelle est la durée du préavis ? »
-   « Résume ce document. »
-   « Compare ces deux contrats. »
-   « Quels documents parlent de RabbitMQ ? »
-   « Quelles sont les clauses importantes ? »

Toute réponse basée sur un document doit autant que possible indiquer
ses **sources**.

------------------------------------------------------------------------

# Phase 1 --- Python moderne

Avant FastAPI :

-   syntaxe et structures de données ;
-   fonctions ;
-   classes ;
-   modules et packages ;
-   environnements virtuels ;
-   typing ;
-   dataclasses ;
-   exceptions ;
-   generators ;
-   context managers ;
-   async / await ;
-   pytest.

Comparaisons utiles :

``` text
PHP / TypeScript       Python

Type hints          →  typing
DTO / objets data   →  dataclass / Pydantic
Promise             →  coroutine / async-await
PHPUnit / Jest      →  pytest
```

------------------------------------------------------------------------

# Phase 2 --- FastAPI

Construire une vraie API avant toute IA.

Notions :

-   FastAPI ;
-   routers ;
-   dependency injection ;
-   Pydantic ;
-   validation ;
-   gestion des erreurs ;
-   SQLAlchemy ;
-   PostgreSQL ;
-   Alembic ;
-   authentification ;
-   OpenAPI ;
-   tests unitaires ;
-   tests d'intégration ;
-   async.

Comparaisons :

``` text
Symfony             NestJS              FastAPI

Controller       →  Controller       →  Router
Service          →  Provider         →  Service
DTO              →  DTO              →  Pydantic Model
Validator        →  class-validator  →  Pydantic
Doctrine         →  TypeORM          →  SQLAlchemy
Migrations       →  TypeORM          →  Alembic
Dependency
Injection        →  DI NestJS        →  Depends
```

API initiale :

``` http
POST   /documents
GET    /documents
GET    /documents/{id}
DELETE /documents/{id}
```

Aucun LLM à ce stade.

------------------------------------------------------------------------

# Phase 3 --- Traitement documentaire

Pipeline :

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

À apprendre :

-   upload ;
-   PDF ;
-   métadonnées ;
-   stratégies de chunking ;
-   sync vs async ;
-   gestion des erreurs ;
-   statuts ;
-   idempotence.

Statuts possibles :

``` text
UPLOADED
PROCESSING
READY
FAILED
```

------------------------------------------------------------------------

# Phase 4 --- LLM

Commencer simplement :

``` text
Document → Résumé
```

Puis :

``` text
Texte → Extraction structurée
```

Notions :

-   system / user messages ;
-   tokens ;
-   context window ;
-   température ;
-   hallucinations ;
-   prompt engineering ;
-   Structured Outputs.

Exemple :

``` json
{
  "document_type": "contract",
  "parties": [],
  "start_date": null,
  "notice_period": null
}
```

------------------------------------------------------------------------

# Phase 5 --- Embeddings et recherche vectorielle

Comprendre :

-   embeddings ;
-   similarité ;
-   vectorisation ;
-   recherche sémantique ;
-   top-k ;
-   métadonnées ;
-   vector store.

``` text
Chunks
   ↓
Embeddings
   ↓
Vector Store
```

Puis :

``` text
Question
   ↓
Embedding
   ↓
Recherche vectorielle
   ↓
Chunks pertinents
```

------------------------------------------------------------------------

# Phase 6 --- RAG

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

Objectifs :

-   grounding ;
-   réduction des hallucinations ;
-   traçabilité ;
-   citations ;
-   retrieval ;
-   ranking.

Exemple :

``` json
{
  "answer": "Le préavis est de trois mois.",
  "sources": [
    {
      "document_id": "...",
      "page": 7
    }
  ]
}
```

------------------------------------------------------------------------

# Phase 7 --- Multi-document

Ajouter :

-   questions sur plusieurs documents ;
-   comparaison ;
-   recherche globale ;
-   filtres ;
-   historique des conversations.

Exemple :

> Compare les clauses de résiliation de ces deux contrats.

------------------------------------------------------------------------

# Phase 8 --- Tool Calling

Créer des outils :

``` python
search_documents()
get_document_page()
compare_documents()
extract_structured_data()
generate_summary()
```

Pipeline :

``` text
Question
   ↓
Choix d'un outil
   ↓
Exécution
   ↓
Résultat
   ↓
Réponse
```

À apprendre :

-   schemas ;
-   validation des arguments ;
-   orchestration ;
-   gestion des erreurs ;
-   contrôle des actions.

------------------------------------------------------------------------

# Phase 9 --- Agent IA

``` text
Utilisateur
   ↓
Agent
   ├── search_documents
   ├── get_document_page
   ├── compare_documents
   └── generate_summary
```

Objectifs :

-   workflow vs agent ;
-   autonomie contrôlée ;
-   boucles ;
-   erreurs ;
-   tracing ;
-   coûts ;
-   sécurité.

Ne pas commencer par un framework agentique complexe : comprendre
d'abord le mécanisme.

------------------------------------------------------------------------

# Phase 10 --- React

Interface cible :

``` text
┌─────────────────┬──────────────────────────┐
│   Documents     │      Conversation        │
│                 │                          │
│ contrat.pdf     │ User: ...                │
│ facture.pdf     │                          │
│ specs.pdf       │ AI: ...                  │
└─────────────────┴──────────────────────────┘
```

Features :

-   upload ;
-   liste des documents ;
-   statut ;
-   sélection ;
-   conversation ;
-   sources ;
-   navigation vers une source.

------------------------------------------------------------------------

# Tests

## Unitaires

Une unité isolée :

-   chunking ;
-   validation ;
-   services métier.

## Intégration

``` text
Repository
   ↓
SQLAlchemy
   ↓
PostgreSQL
```

ou :

``` text
EmbeddingService
   ↓
Vector Store
```

## Fonctionnels

``` text
POST /documents
   ↓
FastAPI
   ↓
Service
   ↓
Database
   ↓
HTTP 201
```

## IA

Tester progressivement :

-   Structured Outputs ;
-   présence des sources ;
-   absence de source pertinente ;
-   documents incomplets ;
-   comportement du retrieval.

------------------------------------------------------------------------

# Architecture

Commencer simplement :

``` text
app/
├── api/
├── documents/
├── conversations/
├── infrastructure/
├── ai/
├── database/
└── main.py
```

Principes :

-   KISS ;
-   YAGNI ;
-   SOLID lorsque pertinent ;
-   forte cohésion ;
-   faible couplage ;
-   code testable.

Ne faire évoluer l'architecture que lorsqu'un besoin réel apparaît.

------------------------------------------------------------------------

# Règles d'utilisation de l'IA pendant la formation

L'IA peut participer directement au développement du projet, y compris
produire des features complètes et proposer l'architecture.

La contrainte pédagogique est différente : **aucune grande étape ne doit
être considérée comme acquise uniquement parce que le code fonctionne**.

Après chaque grande étape :

1.  présenter les fichiers et composants importants créés ou modifiés ;
2.  expliquer le flux principal de la feature ;
3.  signaler les nouvelles notions à connaître ;
4.  laisser le temps de relire le code ;
5.  poser des questions de validation ;
6.  revenir sur les réponses incorrectes ou imprécises ;
7.  seulement ensuite marquer les notions correspondantes comme
    validées.

Les questions doivent être adaptées à un développeur backend expérimenté
: éviter les questions triviales de syntaxe lorsque la notion importante
concerne plutôt l'architecture, le framework, Python, FastAPI ou l'IA.

Exemples de questions :

-   Pourquoi utilise-t-on un modèle Pydantic à cet endroit ?
-   Quelle différence avec un DTO NestJS ou Symfony ?
-   Quel est le rôle de `Depends` dans cette route ?
-   Pourquoi cette opération est-elle `async` ?
-   Où commence et où s'arrête la transaction SQL ?
-   Que se passe-t-il si le traitement du document échoue ?
-   Pourquoi découper le document en chunks ?
-   Pourquoi ne pas envoyer le PDF complet au LLM ?
-   Quelle différence entre recherche vectorielle et recherche SQL
    classique ?
-   Comment les sources permettent-elles de réduire le risque
    d'hallucination ?
-   Dans ce workflow, qu'est-ce qui relève réellement d'un agent ?

------------------------------------------------------------------------

# Suivi des compétences

``` text
[ ] Python typing
[ ] Python async
[ ] pytest
[ ] FastAPI
[ ] Pydantic
[ ] SQLAlchemy
[ ] Alembic
[ ] PostgreSQL
[ ] Tests unitaires
[ ] Tests d'intégration
[ ] Traitement documentaire
[ ] LLM APIs
[ ] Structured Outputs
[ ] Embeddings
[ ] Vector Search
[ ] RAG
[ ] Tool Calling
[ ] Agents
[ ] React integration
```

Statuts :

``` text
À découvrir
À relire
Compris
Validé
```

`Validé` signifie que la notion a été rencontrée dans le projet, relue
dans le code et correctement expliquée lors des questions de validation.

Il n'est pas nécessaire de réaliser un exercice ou une feature en
autonomie pour valider une notion.

------------------------------------------------------------------------

# Checkpoints de validation

Les validations sont regroupées après les grandes étapes plutôt qu'après
chaque petite notion.

## Checkpoint 1 --- Python + FastAPI

À valider après la construction du socle backend et de l'API Documents.

Questions sur : - typing Python ; - modèles Pydantic ; - routers ; -
dependency injection ; - SQLAlchemy ; - Alembic ; - async / await ; -
cycle d'une requête FastAPI ; - tests.

## Checkpoint 2 --- Pipeline documentaire

À valider après upload, extraction, normalisation, chunking et
indexation.

Questions sur : - traitement de fichiers ; - statuts ; - idempotence ; -
sync vs async ; - gestion des erreurs ; - stratégie de chunking.

## Checkpoint 3 --- LLM + Structured Outputs

Questions sur : - messages ; - tokens ; - context window ; -
hallucinations ; - prompts ; - sorties structurées ; - validation des
réponses.

## Checkpoint 4 --- Embeddings + RAG

Questions sur : - embeddings ; - similarité ; - recherche vectorielle
; - top-k ; - retrieval ; - grounding ; - ranking ; - sources.

## Checkpoint 5 --- Tool Calling + Agents

Questions sur : - tool schemas ; - orchestration ; - validation des
arguments ; - workflow vs agent ; - autonomie ; - boucles ; - sécurité
; - coûts ; - tracing.

## Checkpoint 6 --- React et intégration Full Stack

Questions sur : - architecture frontend ; - état ; - appels API ; -
gestion des erreurs ; - intégration avec FastAPI ; - flux complet
utilisateur → frontend → backend → IA → sources.

------------------------------------------------------------------------

# Definition of Done

L'utilisateur peut :

1.  créer un compte ;
2.  importer plusieurs documents ;
3.  attendre leur traitement ;
4.  sélectionner des documents ;
5.  poser une question ;
6.  obtenir une réponse fondée sur les documents ;
7.  consulter les sources ;
8.  comparer plusieurs documents ;
9.  demander une extraction structurée ;
10. utiliser des fonctionnalités basées sur du tool calling.

Le projet est :

-   testé ;
-   dockerisé ;
-   documenté ;
-   versionné avec Git ;
-   présentable sur GitHub ;
-   explicable techniquement en entretien.

------------------------------------------------------------------------

# Compétences visées

À la fin du projet :

``` text
Python
FastAPI
Pydantic
SQLAlchemy
PostgreSQL
pytest
React
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
