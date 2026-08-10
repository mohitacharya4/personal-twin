# Personal Twin — developer entry points. `make help` lists them.
.DEFAULT_GOAL := help
.PHONY: help sync lint fmt type test test-all cov ingest serve eval clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

sync: ## Resolve and install the workspace
	uv sync --all-extras --dev

lint: ## Lint with ruff
	uv run ruff check .

fmt: ## Auto-format with ruff
	uv run ruff format .
	uv run ruff check --fix .

type: ## Type-check with mypy (strict)
	uv run mypy packages apps

test: ## Run unit tests with coverage gate
	uv run pytest -m "not integration" --cov --cov-report=term-missing

test-all: ## Run every test, including integration (needs a live model / services)
	uv run pytest --cov --cov-report=term-missing

ingest: ## Index configured sources into the vector store
	uv run twin ingest

serve: ## Run the API (auto-reload)
	uv run twin serve --reload

eval: ## Run the evaluation sweep
	uv run python evals/run_evals.py

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
