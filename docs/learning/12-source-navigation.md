# J13 — Consulter les pages et le PDF depuis une citation

## Ce qui a été construit

Chaque source d’une réponse possède un bouton « Voir la page N ». Il ouvre le texte
complet de cette page dans une boîte de dialogue, avec le passage cité mis en
évidence s’il correspond encore à l’instantané enregistré. Un lien ouvre également
le PDF original dans un nouvel onglet, avec la page demandée dans l’URL.

## Lecture conseillée

1. `backend/app/documents/routes/content.py` : réponses HTTP fichier et page.
2. `backend/app/documents/services/documents.py` : `file_path()` et `get_page()`.
3. `backend/app/documents/storage.py` : résolution du chemin à partir de l’UUID,
   contrôle de fichier régulier et traduction des erreurs disque.
4. `backend/app/documents/repository.py` : lecture d’une page précise.
5. `frontend/src/conversations/ExchangeCard.tsx` : sélection d’une source.
6. `frontend/src/conversations/SourceDialog.tsx` : dialog, chargement, offsets et lien.
7. `compose.smoke.yaml`, `backend/evaluation/smoke_install.py` et `Makefile` :
   contrôle d’installation isolé, sans IA.

## Deux lectures différentes

- `GET /documents/{id}/pages/{page_number}` lit le texte extrait dans PostgreSQL.
- `GET /documents/{id}/file` transfère le PDF original conservé sur disque.

La première permet de consulter une page sans dépendre d’un lecteur PDF dans le
navigateur. Elle ne reproduit pas sa mise en page, ses illustrations ou sa typographie.
La seconde permet de vérifier le document original.

Le backend répond 404 pour un document ou une page inconnus. Un document en cours
de suppression est refusé avec 409 ; un document constitué uniquement de métadonnées
n’a pas de fichier à servir. Un fichier absent ou inaccessible donne 503 lors du
contrôle du stockage : c’est une incohérence ou indisponibilité côté serveur.

## Fichier, chemin et HTTP

Le chemin local dépend uniquement de l’UUID validé. Le nom envoyé lors de l’upload
ne sert jamais à choisir le fichier à lire. Le contrôle `lstat` refuse un lien
symbolique et exige un fichier régulier. Le nom présenté pour le PDF est UUID.pdf.

La route construit une `FileResponse`, avec `application/pdf` et une disposition
`inline`. Starlette gère le transfert par blocs et les requêtes HTTP `Range` : un
lecteur peut demander une partie des octets, avec une réponse 206 plutôt que charger
systématiquement tout le fichier. La bibliothèque fournit aussi longueur et en-têtes
associés. `no-store` demande de ne pas stocker la réponse dans les caches HTTP ;
`nosniff` évite une réinterprétation du type déclaré.

Référence : [FileResponse dans Starlette](https://www.starlette.io/responses/#fileresponse).

La transaction SQL est terminée avant le contrôle disque et le transfert réseau.
Une suppression concurrente peut encore survenir entre le contrôle du chemin et
l’ouverture du fichier par Starlette : le transfert peut alors échouer. On ne
conserve pas un verrou SQL durant le téléchargement pour empêcher cette course.

## Page demandée et fragment d’URL

Le lien est de la forme `/api/documents/UUID/file#page=2`. Le fragment `#page=2`
est interprété par le lecteur PDF ; il n’est pas envoyé au backend et ne représente
pas une plage d’octets HTTP. La prise en charge dépend du navigateur. La vue texte
ouvre toujours la page demandée, même si le lecteur ignore le fragment.

`target="_blank"` ouvre un nouvel onglet et `rel="noopener noreferrer"` évite de
lui donner une relation d’ouverture exploitable ou de transmettre le référent.
Le bouton de fermeture et Échap utilisent le dialog natif ; le navigateur gère
le focus modal. Le chargement est annulé à la fermeture et les réponses obsolètes
ne modifient pas l’affichage.

## Surligner sans falsifier une ancienne citation

La source historique conserve texte et offsets. Avant de surligner la page actuelle,
on vérifie que sa portion `[start_offset, end_offset)` est exactement égale au texte
cité. Sinon, on affiche la page sans surlignage et on signale la différence. L’ancien
extrait reste disponible dans la réponse enregistrée.

Attention aux chaînes Unicode : les offsets Python comptent les points de code,
alors que `slice()` sur une chaîne JavaScript utilise des unités UTF-16. Un emoji
peut donc décaler un surlignage naïf. `Array.from(page.text)` fournit ici les points
de code utilisés pour découper selon les offsets backend. Il ne s’agit pas de
compter les caractères visuels composés (« graphèmes »).

Le texte et le passage sont rendus comme texte React. Aucun HTML provenant du PDF
ou du modèle n’est injecté dans la page.

## Contrôle d’installation

`make smoke-install` construit et démarre un projet Compose séparé, initialise
une base vide, applique les migrations puis vérifie upload, extraction, chunking,
page, PDF, Range, erreurs et proxy frontend. La clé Gemini est vide. L’indexation
retourne donc l’erreur attendue sans requête au fournisseur.

Le projet n’expose aucun port et possède ses propres volumes. Le nettoyage retire
ces volumes, même en cas d’échec. Ne pas lancer deux `make smoke-install` simultanément :
le nom de projet de test est fixe. Les volumes de développement sont distincts.
Ce contrôle complète les tests pytest/React et l’essai réel du RAG ; il ne remplace
pas l’évaluation de la qualité des réponses.

## Comparaison Symfony / NestJS

`FileResponse` joue un rôle proche d’une réponse fichier Symfony ou d’un mécanisme
de transfert de fichier NestJS. Le service décide si le contenu est consultable,
le stockage résout le fichier et le router choisit la représentation HTTP.
La séparation des responsabilités reste celle du projet.

## Points à expliquer

1. Pourquoi lire le PDF à partir de l’UUID plutôt qu’à partir du nom fourni à l’upload ?
2. Pourquoi la transaction SQL est-elle terminée avant le transfert du PDF ?
3. Quelle différence entre la page extraite, le fragment `#page=2` et une requête `Range` ?
4. Pourquoi vérifier le texte avant de surligner les offsets d’une ancienne source ?
5. Pourquoi un contrôle sur une base vide complète-t-il les tests exécutés habituellement ?

Statut pédagogique : à relire.
