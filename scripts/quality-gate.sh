#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f "pyproject.toml" ]]; then
  echo "pyproject.toml not found. The project skeleton has not been created yet." >&2
  exit 1
fi

if command -v uv >/dev/null 2>&1; then
  uv run ruff check .
  uv run ruff format --check .
  uv run mypy src tests
  uv run pytest --cov=src --cov-report=term-missing
else
  python -m ruff check .
  python -m ruff format --check .
  python -m mypy src tests
  python -m pytest --cov=src --cov-report=term-missing
fi

if [[ -f "docker-compose.yml" ]]; then
  docker compose config >/dev/null
fi

echo "quality gate passed"
