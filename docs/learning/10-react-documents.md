# J11 — Une interface React pour les documents

## Ce qui a été construit

Une application React / TypeScript, servie par Vite dans Docker : bibliothèque
paginée, import PDF, sélection et lancement explicite des trois étapes du pipeline.
Les statuts proviennent de FastAPI. Les erreurs et les attentes sont visibles.
Les questions et les conversations appartiennent aux étapes suivantes.

## Lecture conseillée

1. `frontend/src/documents/types.ts` : contrat TypeScript des réponses de l’API.
2. `frontend/src/documents/api.ts` : appels HTTP, multipart et erreurs.
3. `frontend/src/App.tsx` : état partagé, chargement, sélection et opérations.
4. `UploadForm.tsx`, `DocumentList.tsx`, `DocumentDetails.tsx` dans `documents/` :
   responsabilités des composants et communication par props/callbacks.
5. `frontend/vite.config.ts`, `compose.yaml`, `frontend/Dockerfile` : trajet réseau.
6. `frontend/src/App.test.tsx` : comportements utilisateur, API simulée.

## Flux d’un import

Formulaire → fichier sélectionné et titre → callback du parent → `FormData` →
`fetch('/api/documents/upload')` → proxy Vite → FastAPI → service → stockage et SQL →
réponse `DocumentRead` → état React → affichage recalculé.

Le navigateur choisit le `Content-Type` multipart et sa boundary. Le fixer à la
main risquerait de rendre le fichier illisible côté FastAPI.
La taille est vérifiée côté interface pour aider l’utilisateur ; le backend reste
l’autorité pour la validation. Le fichier choisi est conservé dans l’état du
formulaire, puis oublié et le formulaire vidé après un import réussi.

## État, effets et responsabilités

`App` possède la liste, le document sélectionné, la page et les états d’opération.
Les enfants reçoivent les données et demandent une action via un callback.
`useState` conserve des valeurs entre les rendus ; sa fonction de mise à jour
planifie un nouveau rendu. Modifier une variable ordinaire ne suffit pas.

`useEffect` synchronise la liste avec la page demandée. Son nettoyage annule le
chargement précédent avec `AbortController`. On vérifie aussi `signal.aborted`
avant de mettre à jour l’état : une réponse ancienne ne doit pas remplacer la
nouvelle, ni terminer prématurément son indicateur de chargement.
`StrictMode` aide à détecter les effets mal nettoyés pendant le développement.

Les opérations mutantes partent des événements utilisateur, pas d’un effet de
montage. Les actions sont désactivées pendant l’attente. On affiche le statut
renvoyé par l’API, sans déduire un succès du simple clic.
L’extraction peut enregistrer `FAILED` puis répondre 422 : on relit alors le document.
Un quota Gemini laisse les passages disponibles ; la reprise reste manuelle.

La pagination demande 21 éléments pour afficher les 20 premiers et savoir s’il
existe une page suivante. L’offset avance de 20, pour ne pas sauter le 21e.
Un document fraîchement importé peut être sélectionné hors de la page courante ;
il n’est pas injecté arbitrairement dans une liste ordonnée par le backend.

## TypeScript et Python

Le type `DocumentRecord` aide le compilateur et l’éditeur. Il ne valide pas les
réponses JSON à l’exécution : contrairement à un modèle Pydantic, l’annotation
TypeScript disparaît à la compilation. Le backend reste propriétaire du contrat.
Une génération depuis OpenAPI pourrait éviter leur duplication si ce besoin grandit.

Un composant React organise l’affichage et les événements ; ce n’est pas un
controller Symfony/NestJS. Le service backend garde les transactions et règles
métier. Le client HTTP frontend transporte la requête, sans accès SQL ni clé Gemini.

## Vérifier

- `make frontend-check` : ESLint, format Prettier, TypeScript, build Vite et Vitest.
- `make frontend-format` : applique Prettier ; modifie les fichiers.
- `make quality` : contrôles backend et frontend.

Les tests React utilisent Testing Library et simulent `fetch`. Ils vérifient les
comportements visibles, pas PostgreSQL ni Gemini. Le test multipart déclenche la
soumission du formulaire explicitement : jsdom ne raccorde pas complètement le
fichier simulé par user-event à sa validation native `required`. L’import réel a
également été vérifié dans le navigateur avec un PDF synthétique, jusqu’au statut
`INDEXED` via Gemini. Ce document de test a ensuite été supprimé.
Les neuf tests couvrent notamment la pagination, le pipeline réussi, la reprise
après erreur et le blocage des actions pendant une requête en cours.

## Points à expliquer

1. Pourquoi l’état sélectionné se trouve-t-il dans `App` plutôt que dans chaque composant ?
2. Pourquoi annuler et ignorer un chargement devenu obsolète ?
3. Pourquoi conserver les validations backend malgré celles du formulaire ?
4. Quelle différence entre le type TypeScript et la validation Pydantic ?
5. Quel trajet suit un clic sur « Indexer », et où se trouve la clé Gemini ?

Statut pédagogique : à relire. Une interface fonctionnelle ne valide pas encore
la compréhension de React.
