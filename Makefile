.PHONY: help setup dev test migrate clean lint format type-check

# Default target
help:
	@echo "ScholarSync Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make setup          - Install all dependencies"
	@echo "  make setup-dev      - Install with dev dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make dev            - Start all services (docker-compose)"
	@echo "  make dev-api        - Start API server locally"
	@echo "  make dev-worker     - Start worker locally"
	@echo ""
	@echo "Database:"
	@echo "  make migrate        - Run database migrations"
	@echo "  make migrate-create - Create new migration"
	@echo "  make db-init        - Initialize database"
	@echo "  make db-seed        - Seed database with test data"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run all tests"
	@echo "  make test-unit      - Run unit tests"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-cov       - Run tests with coverage"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint           - Run linters"
	@echo "  make format         - Format code"
	@echo "  make type-check     - Run type checker"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean          - Remove cache and build files"
	@echo "  make clean-docker   - Stop and remove Docker containers"

# Setup
setup:
	pip install -r requirements.txt
	pip install -e .

setup-dev: setup
	pip install -e ".[dev]"
	pnpm install

# Development
dev:
	docker-compose up

dev-api:
	uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

dev-worker:
	celery -A apps.worker.celery_app worker --loglevel=info

# Database
migrate:
	alembic upgrade head

migrate-create:
	@read -p "Migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

db-init:
	python scripts/init_db.py

db-seed:
	python scripts/seed_db.py

# Testing
test:
	pytest tests/

test-unit:
	pytest tests/unit/

test-integration:
	pytest tests/integration/

test-cov:
	pytest tests/ --cov=packages/core --cov=apps/api --cov-report=html

# Code Quality
lint:
	ruff check packages/core apps/api scripts/
	mypy packages/core apps/api --ignore-missing-imports

format:
	black packages/core apps/api scripts/
	ruff check --fix packages/core apps/api scripts/

type-check:
	mypy packages/core apps/api --ignore-missing-imports

# Cleanup
clean:
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -r {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage

clean-docker:
	docker-compose down -v
	docker-compose -f docker-compose.test.yml down -v

