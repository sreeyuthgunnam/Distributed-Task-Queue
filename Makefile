# Distributed Task Queue - Makefile
# Run `make help` to see available commands

.PHONY: help install dev test lint format typecheck build up down logs clean

# Default target
.DEFAULT_GOAL := help

# Colors for terminal output
CYAN := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RESET := \033[0m

# Project settings
PYTHON := python
PIP := pip
PYTEST := pytest
DOCKER_COMPOSE := docker-compose

##@ General

help: ## Display this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\n$(CYAN)Usage:$(RESET)\n  make $(GREEN)<target>$(RESET)\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(GREEN)%-15s$(RESET) %s\n", $$1, $$2 } /^##@/ { printf "\n$(YELLOW)%s$(RESET)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development

install: ## Install all dependencies
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt
	cd frontend && npm install

dev: ## Start development environment with hot reload
	$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml up --build

dev-backend: ## Start only backend services in development mode
	$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml up redis api worker-1 --build

dev-frontend: ## Start frontend development server
	cd frontend && npm run dev

run-api: ## Run API server locally (requires Redis)
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

run-worker: ## Run a worker locally (requires Redis)
	$(PYTHON) -m src.worker.main --worker-id local-worker --queues default,emails,images,data

##@ Testing

test: ## Run all tests
	$(PYTEST) tests/ -v

test-cov: ## Run tests with coverage report
	$(PYTEST) tests/ -v --cov=src --cov-report=html --cov-report=term-missing

test-broker: ## Run broker tests only
	$(PYTEST) tests/test_broker.py -v

test-worker: ## Run worker tests only
	$(PYTEST) tests/test_worker.py -v

test-api: ## Run API tests only
	$(PYTEST) tests/test_api.py -v

test-watch: ## Run tests in watch mode
	$(PYTEST) tests/ -v --watch

##@ Code Quality

lint: ## Run linter (ruff)
	ruff check src/ tests/

lint-fix: ## Run linter and fix auto-fixable issues
	ruff check src/ tests/ --fix

format: ## Format code with ruff
	ruff format src/ tests/

format-check: ## Check code formatting without changes
	ruff format --check src/ tests/

typecheck: ## Run type checker (mypy)
	mypy src/ --ignore-missing-imports

security: ## Run security checks
	bandit -r src/ -ll
	safety check -r requirements.txt || true

check: lint typecheck test ## Run all checks (lint, typecheck, test)

##@ Docker

build: ## Build all Docker images
	$(DOCKER_COMPOSE) build

build-api: ## Build API Docker image
	docker build -t taskqueue-api -f docker/Dockerfile.api .

build-worker: ## Build Worker Docker image
	docker build -t taskqueue-worker -f docker/Dockerfile.worker .

build-frontend: ## Build Frontend Docker image
	docker build -t taskqueue-frontend -f docker/Dockerfile.frontend .

up: ## Start all services in production mode
	$(DOCKER_COMPOSE) up -d

down: ## Stop all services
	$(DOCKER_COMPOSE) down

restart: ## Restart all services
	$(DOCKER_COMPOSE) restart

logs: ## View logs from all services
	$(DOCKER_COMPOSE) logs -f

logs-api: ## View API logs
	$(DOCKER_COMPOSE) logs -f api

logs-worker: ## View worker logs
	$(DOCKER_COMPOSE) logs -f worker-1 worker-2 worker-3

scale-workers: ## Scale workers (usage: make scale-workers N=5)
	$(DOCKER_COMPOSE) up -d --scale worker-1=$(N)

##@ Database

redis-cli: ## Connect to Redis CLI
	docker exec -it taskqueue-redis redis-cli

redis-flush: ## Flush all Redis data (CAUTION!)
	docker exec -it taskqueue-redis redis-cli FLUSHALL

##@ Cleanup

clean: ## Remove build artifacts and cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	rm -rf frontend/node_modules frontend/dist 2>/dev/null || true

clean-docker: ## Remove all Docker containers and volumes
	$(DOCKER_COMPOSE) down -v --remove-orphans
	docker system prune -f

##@ Documentation

docs: ## Generate documentation
	@echo "Documentation generation not yet implemented"

##@ Release

version: ## Show current version
	@cat pyproject.toml | grep "^version" | head -1

release-patch: ## Create a patch release
	@echo "Bump patch version and create release"
	# Implementation depends on your versioning tool

release-minor: ## Create a minor release
	@echo "Bump minor version and create release"

release-major: ## Create a major release
	@echo "Bump major version and create release"
