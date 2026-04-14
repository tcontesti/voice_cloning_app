SHELL := /bin/bash
COMPOSE := docker compose -f infra/docker-compose.yml -f infra/docker-compose.override.dev.yml --env-file .env

.PHONY: help up down logs ps restart rebuild test lint format clean env

help:
	@echo "Voice Cloning App — make targets"
	@echo "  env       Copy .env.example to .env if missing"
	@echo "  up        Start all services (dev profile)"
	@echo "  down      Stop all services"
	@echo "  logs      Tail all service logs"
	@echo "  ps        Show service status"
	@echo "  restart   Restart all services"
	@echo "  rebuild   Rebuild images without cache"
	@echo "  test      Run backend tests inside container"
	@echo "  lint      Ruff + mypy on backend"
	@echo "  format    Ruff format"
	@echo "  clean     Down + remove volumes (destructive)"

env:
	@test -f .env || (cp .env.example .env && echo ".env created from .env.example — edit secrets")

up: env
	$(COMPOSE) up -d --build
	@echo ""
	@echo "Services:"
	@echo "  Backend (via nginx):  https://localhost/"
	@echo "  Backend (direct):     http://localhost:8000/health"
	@echo "  MinIO console:        http://localhost:9001/"
	@echo "  RabbitMQ management:  http://localhost:15672/"
	@echo "  Postgres:             localhost:5432"
	@echo "  Redis:                localhost:6379"

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=100

ps:
	$(COMPOSE) ps

restart:
	$(COMPOSE) restart

rebuild:
	$(COMPOSE) build --no-cache

test:
	$(COMPOSE) exec backend pytest -q

lint:
	$(COMPOSE) exec backend ruff check . && $(COMPOSE) exec backend mypy app

format:
	$(COMPOSE) exec backend ruff format .

clean:
	$(COMPOSE) down -v
