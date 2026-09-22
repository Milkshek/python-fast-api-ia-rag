# J3 — Dépendances et contrôles de qualité

Statut : à relire. J2 est validé ; ces outils constituent de nouvelles notions.

## Ce que chaque outil vérifie

| Outil | Responsabilité | Analogie utile |
| --- | --- | --- |
| pip-tools | Résoudre et verrouiller les versions Python | composer.lock / package-lock.json |
| Ruff format | Présentation cohérente du code | PHP-CS-Fixer / Prettier |
| Ruff check | Imports, erreurs usuelles et conventions | Linter / ESLint |
| mypy | Cohérence des annotations de types sans exécuter l'application | PHPStan / vérification TypeScript |
| pytest | Comportement réel sur des scénarios exécutés | PHPUnit / Jest |

Mypy ne remplace pas Pydantic : le premier analyse le code, le second valide les
données reçues à l'exécution. Aucun des deux ne remplace les tests de transactions.

## Dépendances directes et transitives

`backend/requirements.in` décrit nos besoins applicatifs. `backend/requirements-dev.in` ajoute
les outils et clients de test, avec une contrainte sur le lock applicatif pour
utiliser les mêmes versions. `make lock` génère les deux fichiers `.txt`.

Les `.txt` contiennent les versions exactes et les hashes des distributions.
Docker les installe avec `--require-hashes`. On versionne les sources `.in` et
les résultats `.txt` ; on ne modifie pas manuellement une version dans un lock.

Les locks sont résolus dans notre environnement Docker Linux/Python 3.13. Ils
ne promettent pas une installation identique sur tous les OS et toutes les versions
Python. Les images système Docker restent des tags : les paquets Python sont
verrouillés, pas l'intégralité des binaires du système.

## Routine de développement

```sh
make format        # Modifie le format et trie les imports
make lint          # Vérifie le lint et le format sans modification
make typecheck     # Vérifie backend/app/ en mode strict
make quality       # Lint, types, puis tests avec PostgreSQL isolé
```

Ruff couvre `backend/app/`, `backend/tests/` et `backend/migrations/`. Mypy strict couvre `backend/app/` ; les tests
et migrations ne sont pas encore inclus dans son périmètre. Un contrôle vert ne
garantit pas l'absence de défaut, il vérifie uniquement ses règles et son périmètre.

```sh
# Après modification d'un fichier .in
make lock
make quality
make up

# Mise à jour volontaire des dépendances compatibles
make lock LOCK_ARGS=--upgrade
make quality
```

Sans `--upgrade`, pip-tools conserve autant que possible les versions déjà verrouillées.
Relire les différences des locks avant commit, comme pour composer.lock.

Les outils utilisent `compose.tools.yaml`, sans PostgreSQL. Le code est monté pour
permettre le formatage. Le runtime n'installe ni Ruff, ni mypy, ni pytest. `make test`
utilise toujours une base séparée de celle du développement.

## Compatibilité du client de test

Starlette recommande `httpx2` pour son TestClient. Sa version 1.6 utilise encore un
alias AnyIO déprécié dans la série 4.15 ; la borne temporaire `anyio<4.15` est
explicitée dans `backend/requirements.in`. La retirer lorsque Starlette corrige cet appel,
puis régénérer et vérifier les locks. Pytest traite les avertissements comme des
erreurs, sans filtre destiné à cacher ces dépréciations.

## Questions de relecture

1. Pourquoi versionner à la fois les fichiers `.in` et `.txt` ?
2. Quelle différence entre `make format` et `make lint` ?
3. Pourquoi mypy peut-il passer alors qu'un test fonctionnel échoue ?
4. Pourquoi les outils de développement ne sont-ils pas dans l'image runtime ?

Références : [pip-tools](https://github.com/jazzband/pip-tools/blob/main/README.md),
[Ruff](https://docs.astral.sh/ruff/configuration/),
[mypy](https://mypy.readthedocs.io/en/stable/config_file.html),
[TestClient Starlette](https://www.starlette.io/testclient/).
