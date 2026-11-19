COMPOSE := docker compose -f infra/docker-compose.yml

.PHONY: help up down logs test lint migrate seed env clean

help:
	@echo "GapScout targets:"
	@echo "  make up       build and start db, redis, api, worker, beat, web, scraper"
	@echo "  make down     stop and remove containers"
	@echo "  make logs     follow logs from all services"
	@echo "  make test     run API tests in the api container"
	@echo "  make lint     ruff + eslint + typecheck"
	@echo "  make migrate  alembic upgrade head (available from Prompt 2)"
	@echo "  make seed     run scripts/seed.py"
	@echo "  make env      copy .env.example to .env if missing"
	@echo "  make clean    stop and delete volumes (destroys local data)"

up:
	$(COMPOSE) up -d --build
	$(COMPOSE) ps

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=100

test:
	$(COMPOSE) run --rm --no-deps api pytest

lint:
	$(COMPOSE) run --rm --no-deps api ruff check app tests
	$(COMPOSE) run --rm --no-deps api ruff format --check app tests
	$(COMPOSE) run --rm --no-deps web npm run lint
	$(COMPOSE) run --rm --no-deps web npm run format:check
	$(COMPOSE) run --rm --no-deps web npm run typecheck

migrate:
	$(COMPOSE) exec api alembic upgrade head

seed:
	$(COMPOSE) exec api python /scripts/seed.py

env:
	python -c "import os,shutil; print('.env already exists') if os.path.exists('.env') else (shutil.copy('.env.example','.env'), print('created .env from .env.example'))"

clean:
	$(COMPOSE) down -v
