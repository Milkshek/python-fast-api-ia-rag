# J7 — Embeddings Gemini et PostgreSQL/pgvector

Statut pédagogique : à relire. J7 indexe les passages ; J8 ajoutera leur recherche.

## Ce qui est connecté

Le client appelle réellement Gemini : modèle `gemini-embedding-2`, sortie de
768 dimensions. Le fournisseur calcule un vecteur pour chaque chunk. L'application
normalise ce vecteur, puis le conserve dans PostgreSQL grâce à l'extension pgvector.
Aucun modèle n'est exécuté sur le Mac ; aucune génération de réponse LLM n'a encore
été ajoutée. Le modèle de génération sera choisi pour J9.

L'utilisateur a choisi Gemini et confirmé une clé associée à un projet gratuit.
L'offre gratuite reste soumise aux quotas du compte. Le client ne peut pas vérifier
le plan de facturation d'une clé et n'active jamais de facturation ni de fallback.
L'envoi réel transmet le texte des chunks à Google. Utiliser des documents adaptés
aux conditions du compte ; le test de connexion emploie seulement du texte synthétique.

## Essayer

Ajouter `GEMINI_API_KEY` dans `.env` local ignoré, sans la commiter ni la copier dans
les captures ou logs. Lancer `make up` après changement de clé : l'environnement du
conteneur doit être recréé. PostgreSQL garde son volume ; une image PostgreSQL 17
avec le paquet pgvector remplace l'image de base, sans changer de version majeure.

Parcours Swagger : upload → extract → chunk → index.

- POST /documents/{id}/index : calcule les vecteurs et passe à INDEXED.
- GET /documents/{id} : expose embedding_model et embedding_dimensions.
- Même indexation répétée : ne rappelle pas Gemini si le modèle/dimension correspondent.
- POST /documents/{id}/index?force=true : recalcule explicitement les embeddings.

Les valeurs des vecteurs ne sont pas ajoutées aux réponses Documents/Chunks : leur
volume n'aide pas l'utilisateur du produit. Elles sont stockées en base et testées.

## Flux à relire

1. `router.py` : HTTP et traduction des erreurs.
2. `dependencies.py` : clé d'environnement, client HTTP fermé via yield/with.
3. `indexing_service.py` : lecture des chunks, calcul distant, publication atomique.
4. `app/ai/embeddings.py` : protocole Gemini, contrôle de la réponse et normalisation.
5. `repository.py`, `models.py`, migration 0005 : vecteurs persistés et cascade.

Le service utilise un client Gemini concret, pas un framework RAG ou une interface
universelle. HTTPX2 était déjà utilisé dans les tests ; il devient une dépendance
runtime pour l'appel REST. pgvector-python fournit le type SQLAlchemy Vector ; la
bibliothèque n'annonce pas de types mypy, d'où une exemption ciblée à son import.

Un vecteur est une liste de nombres ; 768 est sa dimension, pas le nombre de mots,
de caractères ou de chunks. Les embeddings ne sont pas un résumé lisible du passage.
Pour les comparer, il faudra utiliser le même modèle, la même dimension et les
formats adaptés aux documents et aux questions.

## Contrat Gemini

Chaque requête embedContent reçoit exactement un chunk, précédé de
`title: none | text: `. Gemini Embedding 2 peut agréger plusieurs entrées en un seul
vecteur : on ne concatène donc pas tous les chunks dans un même appel. Ce choix
simple implique un appel par chunk ; il consomme davantage de requêtes qu'un
traitement groupé à concevoir ultérieurement selon les quotas et tarifs.

Le client demande 768 dimensions et désactive la troncature automatique. Il vérifie
la forme de la réponse, le nombre de valeurs, leur caractère numérique et fini,
puis refuse le vecteur nul. La normalisation divise chaque composante par la norme.
La clé est envoyée en en-tête, jamais dans l'URL. Les réponses d'erreur fournisseur
et le contenu des requêtes ne sont pas exposés dans les erreurs métier.

L'endpoint est fixe en HTTPS ; pas de redirection automatique ni de changement de
modèle. Pas de retry automatique : un nouvel essai doit être explicite.

## Transactions et reprise

Les appels Gemini sont faits hors transaction SQL. Une panne au milieu du calcul
ne laisse aucun embedding partiel en base ; les appels déjà effectués peuvent
néanmoins avoir consommé du quota. Une relance recalculera ces résultats.

Après calcul, le service recharge le document sous verrou. Il vérifie l'état et
l'identifiant de génération de l'index. Cet UUID sert à détecter si une autre
indexation a terminé entre-temps. Dans ce cas, publication refusée avec 409.

La suppression de l'ancien index, l'insertion du nouveau et le statut INDEXED sont
validés ensemble. Un échec SQL conserve l'ancien index lors d'une réindexation ;
sans index précédent, le document reste CHUNKED. Une suppression concurrente
empêche la publication. La cascade suit document → pages → chunks → embeddings.

Une extraction/chunking relancée après INDEXED conserve l'index. Les gardes de
publication de l'extraction préservent aussi une indexation terminée pendant qu'une
ancienne extraction calculait encore son résultat.

## Limites et erreurs

| Situation | HTTP | État conservé |
| --- | --- | --- |
| Document absent | 404 | Aucun résultat publié |
| Pas de chunks, modèle incompatible sans force, ou publication concurrente | 409 | État précédent |
| Plus de 100 chunks | 413 | État précédent |
| Quota Gemini atteint | 429 | État précédent |
| Réponse vectorielle invalide | 502 | État précédent |
| Clé absente, erreur fournisseur ou réseau | 503 | État précédent |

Cette première version synchrone vise de petits documents : maximum 100 chunks.
Chaque opération réseau a un timeout de 15 secondes, réduit selon un budget de
120 secondes vérifié entre les appels. Ce budget n'est pas une interruption dure
de tout le traitement : HTTPX applique les timeouts aux phases réseau. Aucun
ordonnanceur, cache intermédiaire ni reprise chunk par chunk à cette étape.

Le modèle et la dimension sont stockés sur le document, communs à tous ses vecteurs.
La colonne PostgreSQL est vector(768). Changer la dimension demandera une migration ;
changer de modèle demandera une réindexation explicite. On ne compare pas arbitrairement
les vecteurs de modèles différents. La recherche exacte et son filtre arrivent en J8 ;
aucun index approximatif n'est nécessaire pour notre petit corpus initial.

La migration descendante supprime les vecteurs et les métadonnées d'indexation,
repasse INDEXED à CHUNKED et conserve le texte. L'extension vector reste installée
car d'autres tables pourraient l'utiliser.

## Vérification et questions

Les tests utilisent PostgreSQL/pgvector réels et un transport HTTP simulé pour
Gemini : pas de quota consommé par make quality. Un essai réel distinct sur texte
synthétique valide la connexion, la dimension et l'indexation du compte gratuit.

1. Pourquoi doit-on encoder la question avec le même modèle que les chunks ?
2. Que signifie la dimension 768 ?
3. Pourquoi appeler Gemini hors transaction SQL ?
4. Que devient l'ancien index si une réindexation échoue ?
5. Pourquoi une nouvelle requête après un quota atteint peut-elle recalculer des vecteurs ?

Sources : [Gemini embeddings](https://ai.google.dev/gemini-api/docs/embeddings),
[protocole REST](https://ai.google.dev/api/embeddings),
[offres et tarifs](https://ai.google.dev/gemini-api/docs/pricing),
[pgvector](https://github.com/pgvector/pgvector).

## Organisation des routes HTTP

`app/documents/router.py` assemble les `APIRouter` avec `include_router()` :

- `routes/documents.py` : création, upload, liste, lecture et suppression ;
- `routes/processing.py` : extraction et lecture des pages, découpage et lecture
  des chunks, indexation ;
- `routes/search.py` : recherche sémantique ajoutée en J8.

Le préfixe `/documents` et le tag OpenAPI sont définis une seule fois dans le
routeur principal. Les sous-routeurs conservent la validation HTTP et la traduction
des erreurs métier ; les services conservent les cas d’usage et les transactions.
Il s’agit de modules Python et de composition de routeurs FastAPI, sans classes
de contrôleurs supplémentaires. Les URL et les réponses restent identiques.
