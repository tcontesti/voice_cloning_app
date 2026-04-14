SHELL := /bin/bash
BASE  := docker compose -f infra/docker-compose.yml -f infra/docker-compose.override.dev.yml --env-file .env
OBS   := $(BASE) -f infra/docker-compose.observability.yml
KC    := $(BASE) -f infra/docker-compose.keycloak.yml
VLT   := $(BASE) -f infra/docker-compose.vault.yml
FULL  := $(BASE) \
         -f infra/docker-compose.observability.yml \
         -f infra/docker-compose.keycloak.yml \
         -f infra/docker-compose.vault.yml

.PHONY: help up down logs ps restart rebuild test lint format clean env \
        observe keycloak vault full load helm-lint helm-template

help:
	@echo "Voice Cloning App — make targets"
	@echo ""
	@echo "Core stack:"
	@echo "  up        Start core services (backend+deps)"
	@echo "  down      Stop core services"
	@echo "  logs      Tail logs"
	@echo "  ps        Service status"
	@echo "  test      Run backend tests"
	@echo "  clean     Down + remove volumes (destructive)"
	@echo ""
	@echo "Optional profiles:"
	@echo "  observe   + Prometheus + Grafana + Loki + exporters"
	@echo "  keycloak  + Keycloak 26 (realm vcapp auto-imported)"
	@echo "  vault     + Vault dev server (root token: vcapp-dev-root)"
	@echo "  full      core + observability + keycloak + vault"
	@echo ""
	@echo "Load + Helm:"
	@echo "  load           Run locust against localhost:8000"
	@echo "  helm-lint      Lint the Helm chart"
	@echo "  helm-template  Render templates with default values"

env:
	@test -f .env || (cp .env.example .env && echo ".env created from .env.example — edit secrets")

up: env
	$(BASE) up -d --build
	@echo "Backend: https://localhost/ · MinIO: http://localhost:9001 · RMQ: http://localhost:15672"

down:
	$(BASE) down

logs:
	$(BASE) logs -f --tail=100

ps:
	$(BASE) ps

restart:
	$(BASE) restart

rebuild:
	$(BASE) build --no-cache

test:
	$(BASE) exec -T backend pytest -q

lint:
	$(BASE) exec -T backend ruff check . && $(BASE) exec -T backend mypy app

format:
	$(BASE) exec -T backend ruff format .

clean:
	$(BASE) down -v

observe: env
	$(OBS) up -d prometheus grafana loki promtail postgres-exporter redis-exporter
	@echo "Prometheus: http://localhost:9090 · Grafana: http://localhost:3001 (admin/admin)"

keycloak: env
	$(KC) up -d keycloak
	@echo "Keycloak: http://localhost:8081 (admin/admin)  realm=vcapp"

vault: env
	$(VLT) up -d vault
	@echo "Vault: http://localhost:8200 (root token: vcapp-dev-root)"
	@echo "Bootstrap: bash scripts/vault_bootstrap.sh"

full: env
	$(FULL) up -d --build
	@echo "All profiles up — see 'make observe / keycloak / vault' for URLs"

load:
	@command -v locust >/dev/null || (echo "pip install locust" && exit 1)
	locust -f tests/load/locustfile.py --host http://localhost:8000

helm-lint:
	helm lint infra/helm/vcapp

helm-template:
	helm template vcapp infra/helm/vcapp --debug
