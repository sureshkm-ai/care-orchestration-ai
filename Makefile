.PHONY: setup lint typecheck test test-coverage seed run run-docker clean

setup:
	uv sync --all-extras
	uv run pre-commit install

lint:
	uv run ruff check src/ tests/ governance/ golden_tests/
	uv run ruff format --check src/ tests/ governance/ golden_tests/

format:
	uv run ruff check --fix src/ tests/ governance/ golden_tests/
	uv run ruff format src/ tests/ governance/ golden_tests/

typecheck:
	uv run mypy src/

test:
	uv run pytest -v

test-coverage:
	uv run pytest --cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=80

test-golden:
	uv run pytest golden_tests/ -v

seed:
	uv run python scripts/seed_data.py

run:
	uv run python scripts/run_all.py

run-docker:
	docker compose -f docker/docker-compose.yml up --build

deploy-aws:
	cd infra && cdk deploy --all

clean:
	rm -rf data/db/*.db .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
