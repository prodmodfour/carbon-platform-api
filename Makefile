.PHONY: install test lint typecheck run

install:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

typecheck:
	uv run mypy src tests

run:
	uv run uvicorn carbon_platform_api.main:app --reload
