# API_Next ERP Testing and Development Makefile

.PHONY: help install test test-unit test-integration test-api test-workflow test-security test-performance test-slow test-all quality coverage clean lint format pre-commit setup-dev docker-test

# Default target
help:
	@echo "API_Next ERP Development Commands"
	@echo "================================="
	@echo ""
	@echo "Testing Commands:"
	@echo "  test          - Run unit tests (default)"
	@echo "  test-unit     - Run unit tests with coverage"
	@echo "  test-integration - Run integration tests"
	@echo "  test-api      - Run API endpoint tests"
	@echo "  test-workflow - Run workflow system tests"
	@echo "  test-security - Run security and permission tests"
	@echo "  test-performance - Run performance tests"
	@echo "  test-slow     - Run slow/comprehensive tests"
	@echo "  test-all      - Run complete test suite"
	@echo ""
	@echo "Quality Commands:"
	@echo "  quality       - Run all code quality checks"
	@echo "  lint          - Run linting (Ruff)"
	@echo "  format        - Run code formatting"
	@echo "  security      - Run security analysis (Bandit)"
	@echo "  coverage      - Generate coverage report"
	@echo ""
	@echo "Development Commands:"
	@echo "  setup-dev     - Setup development environment"
	@echo "  install       - Install dependencies"
	@echo "  pre-commit    - Install pre-commit hooks"
	@echo "  clean         - Clean up generated files"
	@echo ""
	@echo "Docker Commands:"
	@echo "  docker-test   - Run tests in Docker container"

# Installation and setup
install:
	pip install -e .
	pip install pytest pytest-cov pytest-mock pytest-asyncio factory-boy freezegun

setup-dev: install
	pip install pre-commit ruff bandit black isort
	pre-commit install
	@echo "✅ Development environment setup complete!"

pre-commit:
	pre-commit install
	pre-commit install --hook-type pre-push

# Testing commands
test: test-unit

test-unit:
	@echo "🧪 Running unit tests..."
	python scripts/test_runner.py --unit --verbose

test-integration:
	@echo "🔗 Running integration tests..."
	python scripts/test_runner.py --integration --verbose

test-api:
	@echo "🌐 Running API tests..."
	python scripts/test_runner.py --api --verbose

test-workflow:
	@echo "⚡ Running workflow tests..."
	python scripts/test_runner.py --workflow --verbose

test-security:
	@echo "🔒 Running security tests..."
	python scripts/test_runner.py --security --verbose

test-performance:
	@echo "🚀 Running performance tests..."
	python scripts/test_runner.py --performance --verbose

test-slow:
	@echo "🐌 Running slow tests..."
	python scripts/test_runner.py --slow --verbose

test-all:
	@echo "🎯 Running complete test suite..."
	python scripts/test_runner.py --all --verbose

# Quality commands
quality:
	@echo "🔍 Running code quality checks..."
	python scripts/test_runner.py --quality

lint:
	@echo "🔍 Running Ruff linting..."
	ruff check api_next/

format:
	@echo "🎨 Running code formatting..."
	ruff format api_next/
	ruff check api_next/ --select=I --fix

security:
	@echo "🔒 Running security analysis..."
	bandit -r api_next/ -x api_next/tests/

coverage:
	@echo "📊 Generating coverage report..."
	pytest --cov=api_next --cov-report=html --cov-report=term-missing api_next/tests/
	@echo "Coverage report: htmlcov/index.html"

# Development commands
clean:
	@echo "🧹 Cleaning up generated files..."
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf benchmark-results.json
	rm -rf test-report.json

# Docker commands
docker-test:
	@echo "🐳 Running tests in Docker..."
	docker-compose -f .docker/docker-compose.yml exec frappe bash -c "cd apps/api_next && make test-all"

# Frappe-specific commands (when in Frappe environment)
frappe-test:
	@echo "🔧 Running Frappe tests..."
	bench run-tests --app api_next --coverage

frappe-install:
	@echo "📦 Installing API_Next app in Frappe..."
	bench get-app api_next .
	bench install-app api_next

# CI/CD shortcuts
ci-test: quality test-all

ci-quick: lint test-unit

# Watch mode for development (requires entr)
watch-test:
	@echo "👀 Watching for changes..."
	find api_next/ -name "*.py" | entr -r make test-unit

# Benchmark comparison (requires previous benchmark)
benchmark:
	@echo "📈 Running performance benchmarks..."
	pytest -m performance --benchmark-json=benchmark-current.json
	@if [ -f benchmark-previous.json ]; then \
		echo "Comparing with previous benchmark..."; \
		pytest-benchmark compare benchmark-previous.json benchmark-current.json; \
	fi
	@mv benchmark-current.json benchmark-previous.json

# Database commands for testing
test-db-setup:
	@echo "🗄️  Setting up test database..."
	@echo "This should be run in a Frappe environment"

test-db-reset:
	@echo "🗄️  Resetting test database..."
	@echo "This should be run in a Frappe environment"

# Documentation generation (if needed)
docs:
	@echo "📚 Generating documentation..."
	@echo "Documentation generation not implemented yet"

# Full development cycle
dev-cycle: clean setup-dev quality test-all
	@echo "✅ Development cycle complete!"

# Release preparation
release-check: quality test-all security coverage
	@echo "🚀 Release checks complete!"