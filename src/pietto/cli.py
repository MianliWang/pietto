"""Command-line entry point for Pietto developer tooling."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import pietto.parser_api as parser_api
import pietto.semantic as semantic_api
import pietto.ir as ir_api
import pietto.sql as sql_api
from pietto.errors import Diagnostic, Severity

_FALLBACK_VERSION = "0.1.0"
_EXIT_DIAGNOSTIC_ERROR = 1
_EXIT_USAGE_ERROR = 2


def main(argv: Sequence[str] | None = None) -> int:
    """Run Pietto developer tooling and return a process exit code."""

    parser = _build_parser()
    arguments = list(argv) if argv is not None else sys.argv[1:]
    if arguments == []:
        parser.print_help()
        return 0

    try:
        namespace = parser.parse_args(arguments)
    except SystemExit as error:
        return int(error.code)
    if namespace.command == "check":
        return _run_check(namespace.path)
    if namespace.command == "emit-sql":
        return _run_emit_sql(namespace.path, output_path=namespace.output)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Build the Phase 5 single-file developer CLI."""

    parser = argparse.ArgumentParser(
        prog="pietto",
        description="Pietto semantic SQL authoring tools.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_package_version()}",
    )
    subparsers = parser.add_subparsers(dest="command")
    check_parser = subparsers.add_parser(
        "check",
        help="parse and semantically check one Pietto file",
    )
    check_parser.add_argument("path", type=Path, help="Pietto source file")
    emit_parser = subparsers.add_parser(
        "emit-sql",
        help="emit PostgreSQL SQL for one Pietto file",
    )
    emit_parser.add_argument("path", type=Path, help="Pietto source file")
    emit_parser.add_argument(
        "--dialect",
        choices=("postgres",),
        required=True,
        help="SQL dialect",
    )
    emit_parser.add_argument(
        "--output",
        type=Path,
        help="write SQL artifacts to this file instead of stdout",
    )
    return parser


def _run_check(path: Path) -> int:
    """Parse and semantically analyze one Pietto source file."""

    try:
        parse_result = parser_api.parse_file(path)
    except (OSError, UnicodeError) as error:
        print(f"{path}: error: {error}", file=sys.stderr)
        return _EXIT_USAGE_ERROR

    _render_diagnostics(parse_result.diagnostics, fallback_path=path)
    if _has_errors(parse_result.diagnostics):
        return _EXIT_DIAGNOSTIC_ERROR

    if parse_result.ast is None:
        print(f"{path}: error: parser produced no AST", file=sys.stderr)
        return _EXIT_DIAGNOSTIC_ERROR

    semantic_result = semantic_api.analyze(parse_result.ast)
    _render_diagnostics(semantic_result.diagnostics, fallback_path=path)
    if _has_errors(semantic_result.diagnostics):
        return _EXIT_DIAGNOSTIC_ERROR

    print(f"OK: {path}")
    return 0


def _run_emit_sql(path: Path, *, output_path: Path | None) -> int:
    """Compile one Pietto file and print PostgreSQL SQL artifacts."""

    try:
        parse_result = parser_api.parse_file(path)
    except (OSError, UnicodeError) as error:
        print(f"{path}: error: {error}", file=sys.stderr)
        return _EXIT_USAGE_ERROR

    _render_diagnostics(parse_result.diagnostics, fallback_path=path)
    if _has_errors(parse_result.diagnostics):
        return _EXIT_DIAGNOSTIC_ERROR

    if parse_result.ast is None:
        print(f"{path}: error: parser produced no AST", file=sys.stderr)
        return _EXIT_DIAGNOSTIC_ERROR

    semantic_result = semantic_api.analyze(parse_result.ast)
    _render_diagnostics(semantic_result.diagnostics, fallback_path=path)
    if _has_errors(semantic_result.diagnostics):
        return _EXIT_DIAGNOSTIC_ERROR

    ir_result = ir_api.build_ir(parse_result.ast, semantic_result.model)
    _render_diagnostics(ir_result.diagnostics, fallback_path=path)
    if _has_errors(ir_result.diagnostics):
        return _EXIT_DIAGNOSTIC_ERROR

    if ir_result.ir is None:
        print(f"{path}: error: IR builder produced no IR", file=sys.stderr)
        return _EXIT_DIAGNOSTIC_ERROR

    sql_result = sql_api.emit_postgres_sql(ir_result.ir)
    _render_diagnostics(sql_result.diagnostics, fallback_path=path)
    has_backend_errors = _has_errors(sql_result.diagnostics)
    if output_path is None:
        _print_sql_artifacts(sql_result.artifacts)
    elif not has_backend_errors:
        try:
            _write_sql_artifacts(sql_result.artifacts, output_path)
        except OSError as error:
            print(f"{output_path}: error: {error}", file=sys.stderr)
            return _EXIT_USAGE_ERROR
    if has_backend_errors:
        return _EXIT_DIAGNOSTIC_ERROR
    return 0


def _print_sql_artifacts(artifacts: tuple[sql_api.SqlArtifact, ...]) -> None:
    """Print ordered SQL artifacts without changing their stored text."""

    if artifacts:
        print(_format_sql_artifacts(artifacts))


def _write_sql_artifacts(
    artifacts: tuple[sql_api.SqlArtifact, ...],
    output_path: Path,
) -> None:
    """Overwrite one output file with ordered SQL artifact text."""

    sql = _format_sql_artifacts(artifacts)
    output_path.write_text(f"{sql}\n" if sql else "", encoding="utf-8")


def _format_sql_artifacts(artifacts: tuple[sql_api.SqlArtifact, ...]) -> str:
    """Join ordered artifact text with one blank line."""

    return "\n\n".join(artifact.sql for artifact in artifacts)


def _render_diagnostics(
    diagnostics: tuple[Diagnostic, ...],
    *,
    fallback_path: Path,
) -> None:
    """Render ordered diagnostics as stable single-line stderr records."""

    for diagnostic in diagnostics:
        print(
            _format_diagnostic(diagnostic, fallback_path=fallback_path), file=sys.stderr
        )


def _format_diagnostic(diagnostic: Diagnostic, *, fallback_path: Path) -> str:
    """Format one compiler diagnostic without color or source snippets."""

    location = diagnostic.location
    path = location.path or str(fallback_path)
    return (
        f"{path}:{location.line}:{location.column} "
        f"{diagnostic.code} {diagnostic.severity.value}: "
        f"{diagnostic.message}"
    )


def _has_errors(diagnostics: tuple[Diagnostic, ...]) -> bool:
    """Return whether a compiler phase produced an error diagnostic."""

    return any(diagnostic.severity is Severity.ERROR for diagnostic in diagnostics)


def _package_version() -> str:
    """Read installed package metadata with a source-tree fallback."""

    try:
        return version("pietto")
    except PackageNotFoundError:
        return _FALLBACK_VERSION
