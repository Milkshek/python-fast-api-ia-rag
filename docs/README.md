# Documentation

## Utiliser et développer l’application

- [Démonstration reproductible](demo/README.md) : installation, PDF synthétique et parcours utilisateur.
- [Référence API](api.md) : routes, statuts et limites du pipeline.
- [Développement](development.md) : configuration, persistance, dépendances et contrôles.
- [Bilan d’évaluation du RAG](evaluation/2026-09-21-rag-baseline.md) : résultats observés et limites du corpus.

## Comprendre les choix techniques

Les guides suivent la progression du projet. Ils complètent la documentation
actuelle par les notions étudiées, les compromis et les questions de compréhension.

| Sujet | Guide |
| --- | --- |
| API Documents, SQLAlchemy et transactions | [Socle backend](learning/01-documents-api.md) |
| Lint, types et dépendances | [Outillage](learning/02-tooling.md) |
| Fichiers, stockage et compensation | [Upload PDF](learning/03-upload.md) |
| Pages et normalisation | [Extraction](learning/04-extraction.md) |
| Passages, offsets et recouvrement | [Chunking](learning/05-chunking.md) |
| Vecteurs et indexation | [Embeddings](learning/06-embeddings.md) |
| Similarité et filtrage | [Recherche sémantique](learning/07-semantic-search.md) |
| Contexte, génération et citations | [Réponses sourcées](learning/08-grounded-answers.md) |
| Fidélité des réponses et corpus | [Évaluation du RAG](learning/09-rag-evaluation.md) |
| État, effets et appels API | [Interface React](learning/10-react-documents.md) |
| Historique et publication atomique | [Conversations](learning/11-conversations.md) |
| Pages, fichiers et surlignage | [Navigation vers les sources](learning/12-source-navigation.md) |
| Reprises bornées et erreurs fournisseur | [Résilience](learning/13-generation-resilience.md) |
| Démonstration et architecture globale | [Livraison](learning/14-delivery.md) |

Le [programme initial](../document-intelligence-training.md) donne le contexte
pédagogique. Les plans de travail, notes personnelles et rapports bruts restent
locaux et ne sont pas versionnés.
