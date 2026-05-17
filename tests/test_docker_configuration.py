"""Tests for local Docker configuration files."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_project_file(relative_path: str) -> str:
    """Read a repository file as UTF-8 text."""
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_dockerfile_runs_api_as_non_root_with_healthcheck() -> None:
    """The API image should run as a non-root user and expose /healthz health checks."""
    dockerfile = read_project_file("Dockerfile")

    assert "useradd --system" in dockerfile
    assert "USER app" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "http://127.0.0.1:8000/healthz" in dockerfile
    assert 'CMD ["uvicorn", "carbon_platform_api.main:app"' in dockerfile


def test_compose_declares_required_services_ports_and_healthchecks() -> None:
    """Docker Compose should define the local API, Postgres, and Redis stack."""
    compose = read_project_file("docker-compose.yml")

    assert "  api:" in compose
    assert "  postgres:" in compose
    assert "  redis:" in compose
    assert '"${API_HOST_PORT:-8000}:8000"' in compose
    assert '"${POSTGRES_HOST_PORT:-5432}:5432"' in compose
    assert '"${REDIS_HOST_PORT:-6379}:6379"' in compose
    assert "http://127.0.0.1:8000/healthz" in compose
    assert "CARBON_API_AUTH_ENABLED" in compose
    assert "CARBON_API_AUTH_API_KEYS" in compose
    assert "CARBON_API_DATABASE_URL" in compose
    assert "pg_isready" in compose
    assert "redis-cli" in compose


def test_quality_gate_validates_compose_configuration() -> None:
    """The full project gate should validate Docker Compose syntax when present."""
    quality_gate = read_project_file("scripts/quality-gate.sh")

    assert '[[ -f "docker-compose.yml" ]]' in quality_gate
    assert "docker compose config" in quality_gate
    assert "alembic upgrade head" in quality_gate
