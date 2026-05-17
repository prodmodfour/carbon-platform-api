"""Tests for automation hardening scripts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_TERMS_SCRIPT = ROOT / "scripts" / "check-no-private-terms.py"
LAYERING_SCRIPT = ROOT / "scripts" / "check-layering.py"
BUILD_LOOP_SCRIPT = ROOT / "scripts" / "build-loop.sh"
QUALITY_GATE_SCRIPT = ROOT / "scripts" / "quality-gate.sh"


def run_script(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a Python automation script and capture its output."""
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_private_term_check_allows_public_safety_documentation() -> None:
    """Public-safety policy text should not be treated as private content."""
    result = run_script(PRIVATE_TERMS_SCRIPT, "--paths", "AGENTS.md", "README.md")

    assert result.returncode == 0, result.stderr


def test_private_term_check_flags_sensitive_markers(tmp_path: Path) -> None:
    """The private-term check should catch obvious non-public labels."""
    sample = tmp_path / "notes.md"
    sample.write_text(
        "deploy notes: " + "for " + "internal use only\n",
        encoding="utf-8",
    )

    result = run_script(PRIVATE_TERMS_SCRIPT, "--paths", str(sample))

    assert result.returncode == 1
    assert "internal-use-label" in result.stderr


def test_private_term_check_flags_non_public_hostnames(tmp_path: Path) -> None:
    """The private-term check should catch non-public host suffixes."""
    sample = tmp_path / "hosts.txt"
    sample.write_text("api.service." + "corp\n", encoding="utf-8")

    result = run_script(PRIVATE_TERMS_SCRIPT, "--paths", str(sample))

    assert result.returncode == 1
    assert "non-public-hostname" in result.stderr


def test_layering_check_allows_route_to_schema_and_service_imports(
    tmp_path: Path,
) -> None:
    """Route modules may depend on schemas and services."""
    routes_dir = tmp_path / "routes"
    routes_dir.mkdir()
    (routes_dir / "workspaces.py").write_text(
        "from carbon_platform_api.schemas.health import HealthCheckResponse\n"
        "from carbon_platform_api.services.workspaces import WorkspaceService\n",
        encoding="utf-8",
    )

    result = run_script(LAYERING_SCRIPT, "--routes-dir", str(routes_dir))

    assert result.returncode == 0, result.stderr


def test_layering_check_blocks_repository_imports(tmp_path: Path) -> None:
    """Route modules must not import repositories directly."""
    routes_dir = tmp_path / "routes"
    routes_dir.mkdir()
    (routes_dir / "workspaces.py").write_text(
        "from carbon_platform_api.repositories.workspaces import WorkspaceRepository\n",
        encoding="utf-8",
    )

    result = run_script(LAYERING_SCRIPT, "--routes-dir", str(routes_dir))

    assert result.returncode == 1
    assert "carbon_platform_api.repositories" in result.stderr


def test_layering_check_blocks_sqlalchemy_session_imports(tmp_path: Path) -> None:
    """Route modules must not import SQLAlchemy directly."""
    routes_dir = tmp_path / "routes"
    routes_dir.mkdir()
    (routes_dir / "workspaces.py").write_text(
        "from sqlalchemy.ext.asyncio import AsyncSession\n",
        encoding="utf-8",
    )

    result = run_script(LAYERING_SCRIPT, "--routes-dir", str(routes_dir))

    assert result.returncode == 1
    assert "sqlalchemy" in result.stderr


def test_quality_gate_runs_automation_checks() -> None:
    """The full quality gate should include the automation hardening checks."""
    quality_gate = QUALITY_GATE_SCRIPT.read_text(encoding="utf-8")

    assert "check-no-private-terms.py" in quality_gate
    assert "check-layering.py" in quality_gate
    assert "bash -n scripts/build-loop.sh" in quality_gate


def test_build_loop_prompt_and_remote_sync_guards_are_explicit() -> None:
    """The build loop should require ordered tickets and remote sync safety."""
    build_loop = BUILD_LOOP_SCRIPT.read_text(encoding="utf-8")

    assert "lowest-numbered TODO or IN_PROGRESS ticket" in build_loop
    assert "git pull --ff-only" in build_loop
    assert "--allow-ahead" in build_loop
    assert "advanced during the cycle" in build_loop
