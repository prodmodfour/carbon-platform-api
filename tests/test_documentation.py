"""Tests for public portfolio documentation consistency."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DOC_PATHS = (
    "README.md",
    "docs/architecture.md",
    "docs/runbook.md",
    "docs/api-walkthrough.md",
)
ADR_PATHS = (
    "docs/adr/0001-project-scope.md",
    "docs/adr/0002-layered-architecture-and-mockable-boundaries.md",
    "docs/adr/0003-async-postgresql-and-local-docker-stack.md",
    "docs/adr/0004-demo-carbon-calculation-and-cache-first-intensity.md",
    "docs/adr/0005-observability-and-quality-guardrails.md",
)
EXPECTED_ENDPOINTS = (
    "GET /healthz",
    "GET /readyz",
    "GET /metrics",
    "POST /workspaces",
    "GET /workspaces",
    "GET /workspaces/{workspace_id}",
    "POST /workspaces/{workspace_id}/usage-samples",
    "GET /workspaces/{workspace_id}/reports/summary",
    "GET /reports/summary",
)


def read_project_file(relative_path: str) -> str:
    """Read a repository file as UTF-8 text."""
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_markdown_relative_links_point_to_existing_files() -> None:
    """Documentation index links should not drift from files in the repository."""
    markdown_link_pattern = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
    for relative_path in (*PUBLIC_DOC_PATHS, *ADR_PATHS):
        document_path = ROOT / relative_path
        document = document_path.read_text(encoding="utf-8")
        for match in markdown_link_pattern.finditer(document):
            raw_target = match.group(1).strip()
            if raw_target.startswith(("http://", "https://", "mailto:", "#")):
                continue

            target_without_anchor = raw_target.split("#", maxsplit=1)[0]
            if not target_without_anchor:
                continue

            resolved_target = (document_path.parent / target_without_anchor).resolve()
            assert resolved_target.exists(), (
                f"{relative_path} links to missing file {raw_target}"
            )


def test_public_safety_and_limitations_are_visible() -> None:
    """Reader-facing docs should state public-safety rules and known limitations."""
    for relative_path in PUBLIC_DOC_PATHS:
        document = read_project_file(relative_path).lower()
        assert "public-safe" in document

    readme = read_project_file("README.md")
    runbook = read_project_file("docs/runbook.md")

    assert "## Known limitations" in readme
    assert "API key authentication is a simple portfolio-demo mechanism" in readme
    assert "## Current operational limitations" in runbook
    assert "API key auth is a simple local demo mechanism" in runbook
    assert "Carbon calculation factors" in runbook


def test_readme_and_architecture_document_current_api_surface() -> None:
    """Main docs should list the implemented API without omitting endpoints."""
    readme = read_project_file("README.md")
    architecture = read_project_file("docs/architecture.md")

    for endpoint in EXPECTED_ENDPOINTS:
        assert endpoint in readme
        assert endpoint in architecture


def test_documentation_index_links_walkthrough_and_adrs() -> None:
    """README should guide readers to the walkthrough and accepted ADRs."""
    readme = read_project_file("README.md")

    assert "[Sample API walkthrough](docs/api-walkthrough.md)" in readme
    for adr_path in ADR_PATHS:
        assert adr_path in readme
        assert "## Status\n\nAccepted" in read_project_file(adr_path)


def test_walkthrough_uses_fake_data_and_core_flow() -> None:
    """The sample walkthrough should exercise core API behavior with fake data."""
    walkthrough = read_project_file("docs/api-walkthrough.md")

    assert "sample-cloud" in walkthrough
    assert "sample-region-1" in walkthrough
    assert "Demo Workspace" in walkthrough
    assert "uv run alembic upgrade head" in walkthrough
    assert "POST" in walkthrough
    assert "/usage-samples" in walkthrough
    assert "/reports/summary" in walkthrough
    assert "local_admin" in walkthrough
