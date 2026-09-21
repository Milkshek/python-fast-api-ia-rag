.DEFAULT_GOAL := help

COMPOSE := docker compose
TEST_COMPOSE := docker compose -f compose.test.yaml
TOOLS_COMPOSE := docker compose -f compose.tools.yaml
TOOLS_RUN := $(TOOLS_COMPOSE) run --build --rm --no-deps tools
LOCK_ARGS ?=

.PHONY: help init up build down restart ps logs shell db-shell check health migrate test
.PHONY: format lint typecheck quality lock evaluate frontend-check frontend-format

help: ## Afficher les commandes disponibles
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  make %-12s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

init: ## Créer .env s'il n'existe pas, sans écraser les réglages locaux
	@test -e .env || cp .env.example .env

up: init ## Construire et démarrer les services, puis attendre leur disponibilité
	$(COMPOSE) up --build --wait
	$(MAKE) migrate

build: ## Construire les images
	$(COMPOSE) build

down: ## Arrêter et retirer les conteneurs en conservant les données
	$(COMPOSE) down

restart: ## Redémarrer les services existants (sans reconstruire les images)
	$(COMPOSE) restart

ps: ## Afficher l'état des services
	$(COMPOSE) ps

logs: ## Suivre les logs ; SERVICE=api ou SERVICE=db pour filtrer
	$(COMPOSE) logs --follow --tail=100 $(SERVICE)

shell: ## Ouvrir un shell dans le conteneur API
	$(COMPOSE) exec api sh

db-shell: ## Ouvrir la console PostgreSQL
	$(COMPOSE) exec db sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

check: init ## Valider la configuration Docker Compose
	$(COMPOSE) config --quiet

health: ## Vérifier HTTP dans le conteneur API et exécuter une requête SQL
	$(COMPOSE) exec -T api python -c 'import json, urllib.request; data = json.load(urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=3)); assert data == {"status": "ok"}, data; print("API : OK")'
	$(COMPOSE) exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -c "SELECT 1 AS connection_ok;"'

migrate: ## Appliquer les migrations Alembic (API démarrée)
	$(COMPOSE) exec -T api alembic upgrade head

test: ## Tester sur PostgreSQL isolé, puis retirer les conteneurs de test
	@set -eu; trap '$(TEST_COMPOSE) down --volumes' 0; \
		$(TEST_COMPOSE) run --build --rm tests

format: ## Formater le code et organiser les imports
	$(TOOLS_RUN) sh -c 'ruff check --select I --fix app tests migrations evaluation && ruff format app tests migrations evaluation'

lint: ## Vérifier les règles de lint et le format sans modifier les fichiers
	$(TOOLS_RUN) sh -c 'ruff check app tests migrations evaluation && ruff format --check app tests migrations evaluation'

typecheck: ## Vérifier les types du code applicatif avec mypy strict
	$(TOOLS_RUN) mypy

quality: ## Vérifier le backend et le frontend (lint, types, build, tests)
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) test
	$(MAKE) frontend-check

frontend-check: ## Vérifier React : lint, types, build et tests d'interface
	$(COMPOSE) run --build --rm --no-deps frontend npm run check

frontend-format: ## Formater les sources et la configuration React avec Prettier
	$(TOOLS_COMPOSE) run --build --rm --no-deps frontend-tools npm run format

lock: ## Générer les locks ; LOCK_ARGS=--upgrade pour actualiser les versions
	$(TOOLS_RUN) sh -c 'pip-compile --quiet --generate-hashes $(LOCK_ARGS) -o requirements.txt requirements.in && pip-compile --quiet --generate-hashes $(LOCK_ARGS) -o requirements-dev.txt requirements-dev.in'


evaluate: ## Évaluer le RAG réel via l'API démarrée (consomme le quota Gemini)
	@mkdir -p reports
	EVALUATION_UID=$$(id -u) EVALUATION_GID=$$(id -g) $(COMPOSE) -f compose.yaml -f compose.eval.yaml run --build --rm --no-deps evaluation
