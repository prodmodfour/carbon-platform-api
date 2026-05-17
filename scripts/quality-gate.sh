#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f "pyproject.toml" ]]; then
  echo "pyproject.toml not found. The project skeleton has not been created yet." >&2
  exit 1
fi

run_tool() {
  if command -v uv >/dev/null 2>&1; then
    uv run "$@"
  else
    python -m "$@"
  fi
}

run_python_script() {
  if command -v uv >/dev/null 2>&1; then
    uv run python "$@"
  else
    python "$@"
  fi
}

COMPOSE_PROJECT_NAME=${CARBON_API_QUALITY_GATE_COMPOSE_PROJECT_NAME:-carbon-platform-api-quality-gate}
POSTGRES_DB=carbon_platform_api
POSTGRES_USER=carbon_platform_api
POSTGRES_PASSWORD=local_dev_password
POSTGRES_HOST_PORT=${CARBON_API_TEST_POSTGRES_HOST_PORT:-55432}
export POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD POSTGRES_HOST_PORT

postgres_started=0
cleanup() {
  if [[ "${postgres_started}" == "1" ]]; then
    docker compose --project-name "${COMPOSE_PROJECT_NAME}" down --volumes --remove-orphans >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

start_postgres() {
  docker compose --project-name "${COMPOSE_PROJECT_NAME}" up --detach postgres
  postgres_started=1

  for _ in $(seq 1 30); do
    if docker compose --project-name "${COMPOSE_PROJECT_NAME}" exec -T postgres \
      pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done

  docker compose --project-name "${COMPOSE_PROJECT_NAME}" logs postgres >&2
  echo "PostgreSQL did not become ready for the quality gate." >&2
  return 1
}

bash -n scripts/build-loop.sh
bash -n scripts/quality-gate.sh
run_python_script scripts/check-no-private-terms.py
run_python_script scripts/check-layering.py
run_tool ruff check .
run_tool ruff format --check .
run_tool mypy src tests

if [[ -f "docker-compose.yml" ]]; then
  docker compose config >/dev/null
  start_postgres
  export CARBON_API_DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@127.0.0.1:${POSTGRES_HOST_PORT}/${POSTGRES_DB}"
  export CARBON_API_TEST_DATABASE_ADMIN_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@127.0.0.1:${POSTGRES_HOST_PORT}/postgres"
  run_tool alembic upgrade head
fi

run_tool pytest --cov=src --cov-report=term-missing

echo "quality gate passed"
