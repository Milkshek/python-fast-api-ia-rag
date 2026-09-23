# J14 — Reprendre une génération temporairement indisponible

## Problème et comportement

Gemini a renvoyé HTTP 503 UNAVAILABLE avec un message de forte demande. L’embedding
fonctionnait et les quotas affichés n’étaient pas atteints. Cela n’empêche pas une
saturation temporaire du modèle de génération.

Le client de génération accepte maintenant au maximum **trois appels** pour une
question : appel initial, puis deux reprises uniquement après une réponse HTTP 503.
Les pauses sont de 1 puis 2 secondes. Le modèle et le contenu envoyé restent les mêmes.
Chaque tentative peut consommer du quota et ajoute de la latence.

Un budget de relance de 30 secondes est mesuré avec `monotonic()` : l’heure système
peut être corrigée, alors qu’une horloge monotone convient à une durée écoulée.
On ne commence pas une nouvelle tentative si ce budget est épuisé. Le timeout de
chaque appel est réduit au temps restant. Les timeouts HTTP s’appliquent aux phases
réseau : ce mécanisme ne constitue pas une limite absolue de durée murale de la requête.
Un succès déjà reçu est utilisé même si le temps écoulé a dépassé le budget.

## Ce qui est rejoué

```text
Question → embedding → recherche → contexte
                                   ↓
                         génération (503 ? reprise bornée)
                                   ↓
                      validation réponse et sources
                                   ↓
                     publication unique de l’échange
```

La reprise se trouve dans `GeminiAnswerClient._generate_response()`, pas dans le
service de conversation ni dans React. La recherche et l’embedding sont effectués
une seule fois. Aucune transaction SQL ne reste ouverte pendant l’appel ou la pause.
Une réponse valide permet ensuite au service de publier un seul échange ; l’échec
final n’en publie aucun. Cela ne résout pas le cas distinct d’un double envoi manuel
ou d’une réponse HTTP perdue après commit : relire l’historique avant de renvoyer.

Le code synchrone utilise `sleep` : le thread de cette requête attend pendant la
pause, mais aucune connexion SQL n’est retenue. C’est un compromis limité au MVP
synchrone, pas une file de tâches adaptée à une forte charge.

## Erreurs et diagnostic

- 503 : reprise limitée, puis `AnswerTemporarilyUnavailable`.
- 429 : quota atteint, aucun nouvel appel automatique.
- Timeout ou autre erreur réseau : aucun nouvel appel automatique. L’absence de
  réponse ne prouve pas que le fournisseur n’a rien exécuté.
- Autre statut HTTP, clé absente, JSON invalide ou citations invalides : pas de reprise.

Les deux routes de questions traduisent l’indisponibilité temporaire en 503 avec un
message précis. React conserve la question et ne renvoie pas automatiquement le POST.
Les logs de diagnostic contiennent uniquement l’opération, le modèle, la tentative
et le statut HTTP. Ni clé, ni question, ni passages, ni corps d’erreur fournisseur.

## Lecture et validation

Lire `backend/app/ai/answers.py`, puis les routes `documents/routes/answers.py` et
`conversations/router.py`. Les tests du client utilisent un transport HTTP simulé
et une horloge simulée pour vérifier les pauses et les limites sans attendre.
Les tests d’intégration PostgreSQL vérifient la publication unique, l’absence de
transaction pendant les essais et l’absence d’écriture après échec. Le test React
vérifie la question conservée et l’absence de deuxième POST.

Dans Symfony/NestJS, ce mécanisme pourrait aussi vivre dans le client du fournisseur.
Ici une petite boucle privée suffit : pas de framework de retry ni de décorateur
qui masquerait les conditions de reprise.

## Questions de compréhension

1. Pourquoi placer la reprise dans le client Gemini plutôt qu’autour du service de conversation ?
2. Pourquoi ne pas réessayer toutes les exceptions de la même manière ?
3. Pourquoi limiter à la fois le nombre d’appels et le budget de relance ?
4. Quelles ressources sont occupées pendant `sleep`, et lesquelles restent disponibles ?
5. Pourquoi cette reprise ne garantit-elle pas l’absence de doublon après un renvoi manuel ?
