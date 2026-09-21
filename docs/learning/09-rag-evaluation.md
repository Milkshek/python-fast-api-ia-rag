# J10 — Évaluer le RAG

## Objectif

J9 sait produire une réponse sourcée. J10 cherche à savoir si cette réponse est
correcte et réellement soutenue par les passages. Un HTTP 200, un JSON valide et
un UUID existant ne suffisent pas à le prouver.

## Corpus reproductible

`evaluation/corpus.json` contient trois documents entièrement fictifs, six pages
chacun, et dix questions : huit réponses attendues et deux abstentions.
Les PDF sont générés en mémoire par `evaluation/run.py` ; aucun fichier personnel
n'est transmis. Les pages et les attendus sont lisibles dans le JSON versionné.

Les cas couvrent :

- questions factuelles et formulations différentes du texte ;
- exception au préavis pendant l'essai ;
- réponse appuyée sur deux pages ;
- consigne parasite demandant un faux plafond de remboursement, incluse dans le
  même chunk que la règle correcte pour vérifier son exposition au modèle ;
- information absente ;
- question dont la réponse existe uniquement dans un autre document.

Avec six pages par document et cinq passages récupérés au maximum, le modèle ne
reçoit pas systématiquement tout le document. Le corpus reste petit et peu ambigu :
il constitue une démonstration, pas un benchmark général de qualité.

## Lancer l'évaluation réelle

```sh
make up
make evaluate
```

Cette seconde commande consomme le quota Gemini du projet configuré. Elle reste
séparée de `make test` et de `make quality`, qui utilisent des doublures du fournisseur.
Pour ce corpus : 18 embeddings de pages, puis au plus dix embeddings de questions
et dix générations, hors échecs précoces. Aucun retry ni bascule de fournisseur.

Le conteneur d'évaluation utilise l'UID/GID de l'utilisateur hôte pour écrire le
rapport, y compris sous Linux. Il appelle l'API via le réseau Compose. Il ne reçoit pas la
clé Gemini : l'API la possède déjà. Aucun package supplémentaire n'est nécessaire.
Le corpus/runner sont inclus uniquement dans la cible Docker de test, pas runtime.

## Rapport local et nettoyage

Chaque exécution produit un fichier unique `reports/rag-*.json`, ignoré par Git.
Le rapport contient empreinte du corpus, modèles configurés dans le code du runner,
attendus, réponses, sources, codes HTTP, temps de réponse et erreurs éventuelles.
Ces noms de modèles ne sont pas une attestation du serveur distant : utiliser
`make up` pour exécuter la même version de code dans les services locaux.

Les documents temporaires restent tous indexés pendant les questions : cela permet
de vérifier l'isolation entre documents. Ils sont supprimés dans un `finally`,
même après une erreur, en utilisant uniquement les UUID créés pendant cette exécution.
Les documents personnels préexistants ne sont jamais supprimés.

Un quota 429 pendant les questions interrompt la boucle. Un échec de préparation
interrompt la campagne ; les résultats restent disponibles. Une suppression échouée
est consignée dans `cleanup_errors` avec l'UUID à reprendre. Une interruption brutale
du processus peut empêcher le `finally` : le rapport enregistre les UUID au fur et à
mesure de leur création pour permettre un nettoyage manuel ciblé.

## Trois niveaux de vérification

1. **Contrat et traçabilité** : forme de réponse, abstention attendue, présence des
   pages attendues et égalité des sources avec les chunks réels du document.
2. **Justesse** : comparaison de la réponse avec l'attendu, y compris conditions,
   unités, exceptions et absence d'information.
3. **Soutien factuel** : lecture des passages cités pour vérifier qu'ils justifient
   réellement les affirmations, sans information inventée.

Le runner automatise le premier niveau. Il ne cherche pas seulement des mots-clés
et n'utilise pas un autre LLM comme juge. Les deux derniers niveaux exigent une
relecture explicite. Le champ `human_review` reste vide pour permettre cette revue ;
un éventuel bilan rédigé par Codex ne constitue pas la validation de l'apprenant.

Une sortie de commande réussie signifie « campagne terminée, contrôles mécaniques
réussis et nettoyage terminé », pas « toutes les réponses sont vraies ».

## Critères du checkpoint

Le plan vise au moins huit résultats sur dix corrects, les deux abstentions réussies
et aucune citation inconnue. Pour les huit questions factuelles, vérifier également
les passages réellement cités. Le bilan doit publier les nombres et les limites,
pas seulement déclarer « le RAG fonctionne ».

Les cas PDF invalide, quota, réseau, sortie tronquée et citation inconnue sont
également couverts par les tests déterministes des étapes J5–J9. Ils ne nécessitent
pas de provoquer volontairement des erreurs coûteuses chez le fournisseur.

## Limites et prochaines évaluations

- Un résultat réussi aujourd'hui ne garantit pas une réponse identique demain.
- Un corpus synthétique simple ne représente pas tous les PDF réels.
- Une seule consigne parasite ignorée ne prouve pas une résistance générale aux
  injections. Les textes documentaires restent des données non fiables.
- La durée mesurée est celle de `/ask`, incluant embedding, retrieval et génération,
  pas un décompte des tokens ni un audit du coût fournisseur.
- En cas d'échec, distinguer un passage manqué par la recherche d'un passage bien
  trouvé mais mal interprété. La route `/search` aide au diagnostic.

Ne pas modifier une réponse attendue uniquement pour faire passer le modèle.
Toute correction doit répondre à un défaut observé, avec un test pertinent si le
comportement peut être vérifié de manière déterministe.

## Lecture et questions

Relire `evaluation/corpus.json`, `evaluation/run.py`, `tests/test_evaluation.py`,
puis le bilan dans `docs/evaluation/` lorsqu'il est disponible.

1. Pourquoi les tests avec un fournisseur simulé ne suffisent-ils pas à évaluer la
   pertinence réelle du RAG ?
2. Si les sources existent mais la réponse ignore une exception, quel contrôle échoue ?
3. Pourquoi garder tous les documents du corpus pendant les questions ?
4. Que prouve une campagne réussie sur dix questions, et que ne prouve-t-elle pas ?


## Défauts trouvés pendant J10

Une première réponse « le salaire n’est pas précisé » utilisait `abstained=false`.
La consigne système précise désormais que l’absence de la valeur demandée implique
une abstention, même lorsque cette absence est explicitement écrite dans un passage.

Une seconde campagne a révélé des abstentions correctes rejetées par le backend :
le modèle produisait `answer=""`, `abstained=true`, `source_ids=[]`. La contrainte
inconditionnelle de texte non vide a été remplacée par un `model_validator` Pydantic :
une réponse affirmative doit avoir du texte ; une abstention peut en être dépourvue.
Le service fournit toujours son message fixe et continue de refuser les incohérences
de sources. Trois tests rouges ont reproduit le défaut avant sa correction.

Cette évaluation a donc trouvé un problème de contrat de sortie, sans imposer une
réécriture du retrieval ni ajouter une heuristique de détection des réponses fausses.

Résultats observés : [bilan du 21 septembre](../evaluation/2026-09-21-rag-baseline.md).
