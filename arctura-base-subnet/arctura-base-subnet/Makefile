# Arctura Base Subnet · Makefile
# Arcturian Council · Coreweaver · base.arctura.network

.PHONY: help install verify test lint fmt typecheck security clean

# ── Help ──────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "arctura-base-subnet · Available commands"
	@echo "────────────────────────────────────────"
	@echo "  make install      Install all dependencies (including dev)"
	@echo "  make verify       Run full CI check: lint + typecheck + test + security"
	@echo "  make test         Run pytest suite with coverage"
	@echo "  make lint         Run ruff linter"
	@echo "  make fmt          Auto-format with black"
	@echo "  make typecheck    Run mypy type checker"
	@echo "  make security     Run bandit security scan"
	@echo "  make env          Generate .env interactively"
	@echo "  make env-verify   Verify existing .env"
	@echo "  make clean        Remove build artifacts"
	@echo ""

# ── Install ───────────────────────────────────────────────────────────────

install:
	pip install -e ".[dev]"
	pre-commit install

# ── The main CI gate — all checks must pass ───────────────────────────────

verify: lint typecheck test security
	@echo ""
	@echo "✓ All checks passed. Ready to submit PR."
	@echo ""

# ── Individual checks ─────────────────────────────────────────────────────

test:
	pytest tests/ -v --cov=arctura_base --cov-report=term-missing

lint:
	ruff check arctura_base/ neurons/ tests/
	black --check arctura_base/ neurons/ tests/

fmt:
	black arctura_base/ neurons/ tests/
	ruff check arctura_base/ neurons/ tests/ --fix

typecheck:
	mypy arctura_base/ --ignore-missing-imports

security:
	bandit -r arctura_base/ neurons/ -ll

# ── Environment ───────────────────────────────────────────────────────────

env:
	python scripts/generate_env.py

env-verify:
	python scripts/generate_env.py --verify

# ── Cleanup ───────────────────────────────────────────────────────────────

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ Clean"
