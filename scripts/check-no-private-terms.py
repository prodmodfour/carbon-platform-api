#!/usr/bin/env python3
"""Fail when repository text files contain obvious private or internal markers."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

_SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
}
_MAX_TEXT_FILE_BYTES = 2_000_000


@dataclass(frozen=True)
class SensitivePattern:
    """A named pattern that identifies non-public content."""

    name: str
    regex: re.Pattern[str]


@dataclass(frozen=True)
class Finding:
    """A detected private-term finding."""

    path: Path
    line_number: int
    pattern_name: str


_DEFAULT_PATTERNS: tuple[SensitivePattern, ...] = (
    SensitivePattern(
        "private-key-block",
        re.compile(r"-----BEGIN[ A-Z0-9_-]*PRIVATE KEY-----"),
    ),
    SensitivePattern(
        "aws-access-key-id",
        re.compile(r"\b(?:A3T[A-Z0-9]|AKIA|ASIA)[A-Z0-9]{16}\b"),
    ),
    SensitivePattern(
        "github-token",
        re.compile(r"\bgh(?:p|o|u|s|r)_[A-Za-z0-9_]{30,}\b"),
    ),
    SensitivePattern(
        "slack-token",
        re.compile(r"\bxox(?:b|p|a|r|s)-[A-Za-z0-9-]{20,}\b"),
    ),
    SensitivePattern(
        "internal-use-label",
        re.compile(
            r"\bfor\s+internal\s+use\s+only\b"
            r"|\binternal\s+only\b"
            r"|\bdo\s+not\s+distribute\b"
            r"|\bconfiden"
            r"tial\b",
            re.IGNORECASE,
        ),
    ),
    SensitivePattern(
        "non-public-hostname",
        re.compile(
            r"\b[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
            r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*"
            r"\.(?:corp|internal|intranet)\b",
            re.IGNORECASE,
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Scan repository text files for obvious private, employer, or internal "
            "markers. Set CARBON_API_PRIVATE_TERMS to a comma-separated list of "
            "project-specific terms to block."
        )
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--paths",
        nargs="*",
        type=Path,
        help="Specific files or directories to scan instead of git-tracked files.",
    )
    return parser.parse_args()


def main() -> int:
    """Run the private-term scan."""
    args = parse_args()
    root = args.root.resolve()
    patterns = (*_DEFAULT_PATTERNS, *_custom_patterns())
    files = list(_selected_files(root=root, paths=args.paths))

    findings: list[Finding] = []
    for path in files:
        findings.extend(_scan_file(path, patterns))

    if findings:
        print("Private or internal markers were found:", file=sys.stderr)
        for finding in findings:
            relative_path = _relative_to_root(finding.path, root)
            print(
                f"- {relative_path}:{finding.line_number}: {finding.pattern_name}",
                file=sys.stderr,
            )
        print(
            "Remove the marker or replace it with public-safe sample data.",
            file=sys.stderr,
        )
        return 1

    print("private-term check passed")
    return 0


def _custom_patterns() -> tuple[SensitivePattern, ...]:
    raw_terms = os.environ.get("CARBON_API_PRIVATE_TERMS", "")
    terms = [term.strip() for term in raw_terms.split(",") if term.strip()]
    return tuple(
        SensitivePattern(
            name=f"custom-private-term-{index}",
            regex=re.compile(re.escape(term), re.IGNORECASE),
        )
        for index, term in enumerate(terms, start=1)
    )


def _selected_files(root: Path, paths: list[Path] | None) -> Iterable[Path]:
    if paths:
        for path in paths:
            resolved_path = path if path.is_absolute() else root / path
            yield from _expand_path(resolved_path.resolve())
        return

    candidate_paths = _git_candidate_files(root)
    for relative_path in candidate_paths:
        yield root / relative_path


def _git_candidate_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    output = result.stdout.decode("utf-8")
    return [Path(item) for item in output.split("\0") if item]


def _expand_path(path: Path) -> Iterable[Path]:
    if not path.exists():
        return
    if path.is_file():
        yield path
        return
    for child in path.rglob("*"):
        if child.is_dir() or any(part in _SKIP_DIRS for part in child.parts):
            continue
        if child.is_file():
            yield child


def _scan_file(path: Path, patterns: tuple[SensitivePattern, ...]) -> list[Finding]:
    if _should_skip_path(path):
        return []

    try:
        data = path.read_bytes()
    except OSError:
        return []

    if b"\0" in data or len(data) > _MAX_TEXT_FILE_BYTES:
        return []

    text = data.decode("utf-8", errors="replace")
    findings: list[Finding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for pattern in patterns:
            if pattern.regex.search(line):
                findings.append(
                    Finding(
                        path=path,
                        line_number=line_number,
                        pattern_name=pattern.name,
                    )
                )
    return findings


def _should_skip_path(path: Path) -> bool:
    return any(part in _SKIP_DIRS for part in path.parts)


def _relative_to_root(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path


if __name__ == "__main__":
    raise SystemExit(main())
