.DEFAULT_GOAL := help

COMPOSE := docker compose
TEST_COMPOSE := docker compose -f compose.test.yaml

.PHONY: help init up build down restart ps logs shell db-shell check health migrate test

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
