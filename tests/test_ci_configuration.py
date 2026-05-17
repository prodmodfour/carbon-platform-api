"""Tests for the GitHub Actions CI workflow configuration."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ".github/workflows/ci.yml"


def read_project_file(relative_path: str) -> str:
    """Read a repository file as UTF-8 text."""
    return (ROOT / relative_path).read_text(encoding="utf-8")


def load_ci_workflow() -> dict[str, Any]:
    """Load the CI workflow as parsed YAML."""
    yaml: Any = importlib.import_module("yaml")
    loaded = yaml.safe_load(read_project_file(WORKFLOW_PATH))
    assert isinstance(loaded, dict)
    return cast(dict[str, Any], loaded)


def test_ci_workflow_has_valid_yaml_and_safe_triggers() -> None:
    """CI should run on pull requests and pushes to the default branch only."""
    workflow = load_ci_workflow()
    triggers = workflow["on"]

    assert workflow["name"] == "CI"
    assert workflow["permissions"] == {"contents": "read"}
    assert triggers["push"]["branches"] == ["main"]
    assert "pull_request" in triggers


def test_ci_workflow_provides_postgresql_for_integration_tests() -> None:
    """Repository tests should have a public-safe local PostgreSQL service in CI."""
    workflow = load_ci_workflow()
    quality_job = workflow["jobs"]["quality"]
    postgres_service = quality_job["services"]["postgres"]
    job_environment = quality_job["env"]

    assert postgres_service["image"] == "postgres:16-alpine"
    assert postgres_service["env"] == {
        "POSTGRES_DB": "carbon_platform_api",
        "POSTGRES_USER": "carbon_platform_api",
        "POSTGRES_PASSWORD": "local_dev_password",
    }
    assert postgres_service["ports"] == ["5432:5432"]
    assert "pg_isready" in postgres_service["options"]
    assert job_environment["CARBON_API_DATABASE_URL"].endswith(
        "@127.0.0.1:5432/carbon_platform_api"
    )
    assert job_environment["CARBON_API_TEST_DATABASE_ADMIN_URL"].endswith(
        "@127.0.0.1:5432/postgres"
    )


def test_ci_workflow_runs_local_quality_gate_checks() -> None:
    """CI should run the same substantive checks as the local quality gate."""
    workflow = load_ci_workflow()
    steps = workflow["jobs"]["quality"]["steps"]
    run_commands = "\n".join(step.get("run", "") for step in steps)
    uses_actions = {step.get("uses", "") for step in steps}

    assert "actions/checkout@v4" in uses_actions
    assert "astral-sh/setup-uv@v5" in uses_actions
    assert "actions/setup-python@v5" in uses_actions
    assert "uv sync --locked --all-groups" in run_commands
    assert "bash -n scripts/build-loop.sh" in run_commands
    assert "bash -n scripts/quality-gate.sh" in run_commands
    assert "uv run python scripts/check-no-private-terms.py" in run_commands
    assert "uv run python scripts/check-layering.py" in run_commands
    assert "uv run ruff check ." in run_commands
    assert "uv run ruff format --check ." in run_commands
    assert "uv run mypy src tests" in run_commands
    assert "docker compose config >/dev/null" in run_commands
    assert "uv run alembic upgrade head" in run_commands
    assert "uv run pytest --cov=src --cov-report=term-missing" in run_commands


def test_ci_workflow_caches_dependencies_without_secret_dependent_jobs() -> None:
    """The workflow should cache uv dependencies and avoid deployment/upload jobs."""
    workflow = load_ci_workflow()
    workflow_text = read_project_file(WORKFLOW_PATH).lower()
    setup_uv_steps = [
        step
        for step in workflow["jobs"]["quality"]["steps"]
        if step.get("uses") == "astral-sh/setup-uv@v5"
    ]
    job_names = {str(name).lower() for name in workflow["jobs"]}

    assert setup_uv_steps == [
        {
            "name": "Install uv",
            "uses": "astral-sh/setup-uv@v5",
            "with": {"enable-cache": True, "cache-dependency-glob": "uv.lock"},
        }
    ]
    assert all("deploy" not in name for name in job_names)
    assert "secrets." not in workflow_text
    assert "codecov" not in workflow_text
