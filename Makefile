.PHONY: help install install-dev test lint format run docker-build docker-run docker-stop docker-logs

help:
	@echo "Burraco Bot — Makefile Commands"
	@echo ""
	@echo "Development:"
	@echo "  make install        - Install production dependencies"
	@echo "  make install-dev    - Install dev dependencies (testing, linting)"
	@echo "  make test           - Run unit tests"
	@echo "  make lint           - Run linting (pylint, flake8)"
	@echo "  make format         - Auto-format code (black)"
	@echo "  make run            - Run bot locally (requires .env)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build   - Build Docker image"
	@echo "  make docker-run     - Run bot in Docker (requires .env)"
	@echo "  make docker-stop    - Stop Docker container"
	@echo "  make docker-logs    - View Docker logs (follow mode)"
	@echo ""
	@echo "Utility:"
	@echo "  make env-setup      - Create .env from template"
	@echo "  make clean          - Remove Python cache files"

# Installation targets
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

# Test & Quality
test:
	pytest tests/ -v --tb=short

test-cov:
	pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html

lint:
	pylint bot.py database.py || true
	flake8 bot.py database.py

mypy:
	mypy bot.py database.py --ignore-missing-imports || true

format:
	black bot.py database.py

# Local development
run:
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found!"; \
		echo "Run: cp .env.example .env"; \
		echo "Then fill in the values"; \
		exit 1; \
	fi
	python bot.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/ .coverage htmlcov/

# Docker
docker-build:
	docker build -t burraco_bot:latest .

docker-run:
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found!"; \
		echo "Run: cp .env.example .env"; \
		echo "Then fill in the values"; \
		exit 1; \
	fi
	docker-compose up -d

docker-stop:
	docker-compose down

docker-logs:
	docker-compose logs -f bot

docker-shell:
	docker-compose exec bot sh

# Environment setup
env-setup:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ Created .env from .env.example"; \
		echo "⚠️  Remember to fill in TELEGRAM_TOKEN and SUPABASE_KEY!"; \
	else \
		echo "ℹ️  .env already exists"; \
	fi

# Full CI-like check locally
check: lint mypy test
	@echo "✅ All checks passed!"
