"""Tests for final portfolio readiness bookkeeping."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_project_file(relative_path: str) -> str:
    """Read a repository file as UTF-8 text."""
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_build_backlog_and_automation_status_are_complete() -> None:
    """The final audit should leave every ticket and automation status complete."""
    tickets = read_project_file("BUILD_TICKETS.md")
    notes = read_project_file("BUILD_NOTES.md")

    ticket_statuses = re.findall(r"^Status: (\w+)$", tickets, flags=re.MULTILINE)

    assert ticket_statuses
    assert set(ticket_statuses) == {"DONE"}
    assert "AUTOMATION_STATUS: DONE" in tickets
    assert "AUTOMATION_STATUS: DONE" in notes
    assert "Recommended next ticket: None — backlog complete." in notes
