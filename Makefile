# =============================================================================
# LCMGoCloud-CAGenAI Makefile
# =============================================================================
# Local development commands that mirror CI/CD pipeline stages.
# Run 'make help' for available targets.
# =============================================================================

.PHONY: help install lint test build plan apply clean format

PYTHON := python3.11
PIP := pip
TF_DIR := infra/terraform

# Default target
help:
	@echo "LCMGoCloud-CAGenAI Development Commands"
	@echo "========================================"
	@echo ""
	@echo "Available targets:"
	@echo "  install  - Install Python dependencies"
	@echo "  lint     - Run linters (ruff, black, mypy)"
	@echo "  format   - Auto-format code with black and ruff"
	@echo "  test     - Run tests with coverage"
	@echo "  build    - Build Lambda layers (Linux only)"
	@echo "  plan     - Run terraform plan"
	@echo "  apply    - Run terraform apply"
	@echo "  clean    - Clean build artifacts"
	@echo ""
	@echo "CI/CD workflow:"
	@echo "  make lint test   # Validate before commit"
	@echo "  make plan        # Preview infrastructure changes"
	@echo ""

# -----------------------------------------------------------------------------
# Development Setup
# -----------------------------------------------------------------------------

install:
	$(PIP) install -e ".[dev]"
	$(PIP) install pytest pytest-cov moto boto3 ruff black mypy boto3-stubs types-requests

# -----------------------------------------------------------------------------
# Code Quality
# -----------------------------------------------------------------------------

lint:
	@echo "Running ruff..."
	ruff check src/ lambda/
	@echo ""
	@echo "Running black..."
	black --check src/ lambda/
	@echo ""
	@echo "Running mypy..."
	mypy src/ --ignore-missing-imports
	@echo ""
	@echo "All linting passed!"

format:
	@echo "Formatting with black..."
	black src/ lambda/
	@echo ""
	@echo "Fixing with ruff..."
	ruff check --fix src/ lambda/
	@echo ""
	@echo "Code formatted!"

# -----------------------------------------------------------------------------
# Testing
# -----------------------------------------------------------------------------

test:
	pytest tests/ -v --cov=src/lcmgo_cagenai --cov-report=term-missing

test-quick:
	pytest tests/ -v

# -----------------------------------------------------------------------------
# Lambda Layers
# -----------------------------------------------------------------------------

build:
	@echo "Building Lambda layers..."
	@if [ -f scripts/ci/build-layers.sh ]; then \
		chmod +x scripts/ci/build-layers.sh && ./scripts/ci/build-layers.sh; \
	else \
		echo "ERROR: scripts/ci/build-layers.sh not found"; \
		echo "On Windows, use PowerShell scripts in lambda/ directories"; \
		exit 1; \
	fi

# -----------------------------------------------------------------------------
# Terraform
# -----------------------------------------------------------------------------

plan:
	cd $(TF_DIR) && terraform init && terraform plan

apply:
	cd $(TF_DIR) && terraform init && terraform apply

validate-tf:
	cd $(TF_DIR) && terraform init -backend=false && terraform fmt -check && terraform validate

# -----------------------------------------------------------------------------
# Cleanup
# -----------------------------------------------------------------------------

clean:
	@echo "Cleaning build artifacts..."
	rm -rf lambda/*/*.zip 2>/dev/null || true
	rm -rf lambda/*/layer 2>/dev/null || true
	rm -rf lambda/*/package_layer 2>/dev/null || true
	rm -rf lambda/*/*_layer 2>/dev/null || true
	rm -rf .pytest_cache 2>/dev/null || true
	rm -rf .coverage 2>/dev/null || true
	rm -rf coverage.xml 2>/dev/null || true
	rm -rf htmlcov 2>/dev/null || true
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete!"
