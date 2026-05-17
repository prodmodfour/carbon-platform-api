#!/usr/bin/env python3
"""Fail when route modules bypass service-layer boundaries."""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

_BLOCKED_ABSOLUTE_PREFIXES = (
    "alembic",
    "sqlalchemy",
    "carbon_platform_api.db",
    "carbon_platform_api.models",
    "carbon_platform_api.repositories",
)
_BLOCKED_RELATIVE_PREFIXES = ("db", "models", "repositories")


@dataclass(frozen=True)
class ImportFinding:
    """A blocked import found in a route module."""

    path: Path
    line_number: int
    imported_module: str


@dataclass(frozen=True)
class ImportCandidate:
    """An import target extracted from Python AST."""

    module: str
    line_number: int


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Check route modules for imports that bypass the service layer."
    )
    parser.add_argument(
        "--routes-dir",
        type=Path,
        default=Path("src/carbon_platform_api/routes"),
        help="Route package directory to scan.",
    )
    return parser.parse_args()


def main() -> int:
    """Run the layering check."""
    args = parse_args()
    routes_dir = args.routes_dir

    if not routes_dir.exists():
        print(f"Route directory does not exist: {routes_dir}", file=sys.stderr)
        return 1

    findings = list(_scan_routes(routes_dir))
    if findings:
        print(
            "Route modules import persistence-layer modules directly:",
            file=sys.stderr,
        )
        for finding in findings:
            print(
                f"- {finding.path}:{finding.line_number}: {finding.imported_module}",
                file=sys.stderr,
            )
        print(
            "Route handlers must depend on schemas/services, not SQLAlchemy, "
            "Alembic, database sessions, models, or repositories.",
            file=sys.stderr,
        )
        return 1

    print("layering check passed")
    return 0


def _scan_routes(routes_dir: Path) -> Iterable[ImportFinding]:
    for path in sorted(routes_dir.rglob("*.py")):
        yield from _scan_file(path)


def _scan_file(path: Path) -> Iterable[ImportFinding]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        yield ImportFinding(
            path=path,
            line_number=exc.lineno or 1,
            imported_module="<syntax-error>",
        )
        return

    for node in ast.walk(tree):
        for candidate in _import_candidates(node):
            if _is_blocked_import(candidate.module):
                yield ImportFinding(
                    path=path,
                    line_number=candidate.line_number,
                    imported_module=candidate.module,
                )


def _import_candidates(node: ast.AST) -> Iterable[ImportCandidate]:
    if isinstance(node, ast.Import):
        for alias in node.names:
            yield ImportCandidate(module=alias.name, line_number=node.lineno)
        return

    if isinstance(node, ast.ImportFrom):
        module = _import_from_module(node)
        if module:
            yield ImportCandidate(module=module, line_number=node.lineno)

        for alias in node.names:
            if alias.name == "*":
                continue
            imported_name = f"{module}.{alias.name}" if module else alias.name
            yield ImportCandidate(module=imported_name, line_number=node.lineno)


def _import_from_module(node: ast.ImportFrom) -> str:
    module = node.module or ""
    if node.level == 0:
        return module
    return f"{'.' * node.level}{module}" if module else "." * node.level


def _is_blocked_import(module: str) -> bool:
    normalized = module.lstrip(".")
    if _matches_prefix(normalized, _BLOCKED_ABSOLUTE_PREFIXES):
        return True
    return _matches_prefix(normalized, _BLOCKED_RELATIVE_PREFIXES)


def _matches_prefix(module: str, prefixes: tuple[str, ...]) -> bool:
    return any(
        module == prefix or module.startswith(f"{prefix}.") for prefix in prefixes
    )


if __name__ == "__main__":
    raise SystemExit(main())
