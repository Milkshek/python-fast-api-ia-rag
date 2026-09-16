# J6 — Découper le texte en chunks traçables

Statut pédagogique : à relire. Pas encore d'embeddings ni de recherche sémantique.

## Essayer le parcours

Dans Swagger : upload → extract → chunk → GET chunks.
POST /documents/{id}/chunk attend le résultat, puis retourne le document CHUNKED.
GET /documents/{id}/chunks?limit=20&offset=0 renvoie les passages dans leur ordre.

Le découpage exige EXTRACTED. Les autres états non traitables donnent 409 ; un
UUID absent donne 404. CHUNKED retourne le résultat existant sans recalcul, même
si la configuration du chunker change. Une modification future de stratégie
nécessitera une opération explicite de reconstruction et de réindexation.

## Pourquoi découper ?

Le futur moteur de recherche devra retrouver les passages utiles à une question,
puis fournir au LLM un contexte de taille limitée. Une page ou un document entier
n'est pas nécessairement une bonne unité de recherche.

Notre première stratégie utilise des fenêtres de 1000 caractères Python avec
200 caractères de recouvrement. Exemple réduit avec taille 8 et recouvrement 2 :

```text
Texte : abcdefghijklmnopq
Chunk 1 : abcdefgh           [0, 8)
Chunk 2 :       ghijklmn     [6, 14)
Chunk 3 :             mnopq [12, 17)
```

Le recouvrement répète un peu de contexte autour d'une coupure. Il augmente aussi
le volume indexé et peut produire des résultats redondants. Il n'est pas une
preuve d'amélioration de la pertinence : cela devra être évalué en J10.

On ne traverse pas les pages. C'est simple pour les citations mais une phrase
à cheval sur deux pages ne bénéficiera pas du recouvrement entre ces pages.
Le découpage peut couper un mot ou une phrase ; il ne comprend pas le texte.
Une stratégie par paragraphes ou tokens sera envisagée si les résultats l'exigent.
1000 caractères ne signifie ni 1000 tokens ni une limite garantie du modèle.

## Traçabilité

Chaque chunk possède :

- un UUID stable après enregistrement ;
- document_id et page_number ;
- chunk_index global, commençant à 1 ;
- start_offset inclus et end_offset exclu ;
- le texte exact de `page.text[start_offset:end_offset]`.

Les offsets comptent les caractères Python du texte normalisé en base, pas les
octets du PDF ni les coordonnées visuelles de la page. Les caractères Unicode
composés peuvent contenir plusieurs points de code. Aucun nettoyage supplémentaire
n'est fait pendant le découpage : il fausserait la correspondance avec les offsets.
Les fenêtres entièrement blanches sont ignorées ; les pages vides restent en base.

La clé étrangère composée lie chaque chunk à une page réelle de son document.
Une contrainte interdit deux chunks de même index dans un document. La suppression
d'un document entraîne celle des pages, puis des chunks par cascade SQL.

## Responsabilités et lecture

1. `chunking.py` : TextChunker, algorithme pur sans SQL ni HTTP ; TextChunk est une
   dataclass figée qui porte le résultat d'une fenêtre.
2. `chunking_service.py` : charger les pages, construire les chunks, publier.
3. `repository.py` : SQL ordonné et ajout des chunks, aucun commit.
4. `models.py` et migration 0004 : intégrité, unicité et cascade.
5. `router.py` et `schemas.py` : contrats HTTP et pagination.
6. `tests/test_text_chunker.py` et tests de parcours/pannes : frontières et garanties.

Le service expose le déroulé et nomme les opérations internes `_build_chunks()`
et `_publish_chunks()`. Le chunker reste indépendant de SQL et peut être testé
sur une simple chaîne de caractères.

## Transactions, relance et concurrence

Le service lit les pages, ferme la transaction, puis calcule les chunks. Avant de
publier, il verrouille et recharge le document : une suppression a pu commencer
pendant le calcul. Dans ce cas, les résultats ne sont pas enregistrés.

Les chunks et CHUNKED sont enregistrés dans une seule transaction. Si une écriture
échoue, rien n'est conservé et le document reste EXTRACTED, donc réessayable.
Deux requêtes peuvent calculer simultanément, mais la première publication gagne ;
l'autre retrouve CHUNKED et n'insère pas de doublons. Les UUID restent inchangés.
Les pages sont immuables dans l'API actuelle après extraction : aucun endpoint
ne les modifie pendant le calcul.

Relancer extract sur CHUNKED conserve les pages, les chunks et le statut. Cela
évite une rétrogradation silencieuse du pipeline. Une extraction déjà en cours
ne doit pas non plus écraser un succès publié pendant son parsing.

La migration descendante supprime les chunks et remet CHUNKED à EXTRACTED ; les
pages et le PDF restent disponibles. Il faudra refaire le découpage.

## Limites et suite

Le traitement est synchrone, sans tâche de fond. Les pages et les chunks sont
chargés en mémoire ; le volume de texte est borné par les limites de J5. La copie
du recouvrement a un coût raisonnable pour cette configuration et ce périmètre.
Pas d'appel réseau fournisseur, de coût de modèle ni d'index vectoriel à ce stade.

J7 transformera ces passages en embeddings. CHUNKED indique seulement que les
unités à indexer existent, pas qu'une question peut déjà recevoir une réponse.

## Questions de compréhension

1. Pourquoi faire se chevaucher deux chunks, et quel coût cela ajoute-t-il ?
2. À quoi servent page_number et les deux offsets en plus du texte ?
3. Pourquoi les identifiants ne changent-ils pas quand on relance chunk ?
4. Que devient le document si l'enregistrement des chunks échoue ?
5. Quelle limite de notre stratégie pourrait justifier un découpage par paragraphes ?
