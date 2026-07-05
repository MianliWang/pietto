"""Command-line entry point for Pietto developer tooling."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from collections.abc import Callable, Sequence
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import NoReturn

import pietto.parser_api as parser_api
import pietto.semantic as semantic_api
import pietto.ir as ir_api
import pietto.sql as sql_api
import pietto.sql.mysql as mysql_backend
from pietto import cli_json
from pietto._metadata.builder import build_semantic_metadata_artifact
from pietto._metadata.serializer import (
    SemanticMetadataFailureStage,
    build_semantic_metadata_error_envelope,
    semantic_metadata_artifact_to_json_dict,
)
from pietto._metadata.text import render_semantic_metadata_text
from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import (
    project_check_result_to_json_dict,
    render_project_json_document,
)
from pietto._project.model import ProjectDiscoveryError, ProjectParseCheckResult
from pietto.errors import Diagnostic, Severity

_FALLBACK_VERSION = "0.1.0"
_EXIT_DIAGNOSTIC_ERROR = 1
_EXIT_USAGE_ERROR = 2
_FORMAT_TEXT = "text"
_FORMAT_JSON = "json"
_ENABLED_SQL_DIALECTS = ("postgres", "mysql")
_METADATA_FAILURE_MESSAGES = {
    "parse": "Semantic Metadata Artifact v1 metadata is unavailable because parsing failed.",
    "semantic": "Semantic Metadata Artifact v1 metadata is unavailable because semantic analysis failed.",
    "ir": "Semantic Metadata Artifact v1 metadata is unavailable because IR construction failed.",
}

type _SqlEmitter = Callable[[ir_api.ScriptIR], sql_api.SqlResult]


class _JsonUsageError(Exception):
    """A command argument error rendered through a JSON result contract."""


class _CliArgumentParser(argparse.ArgumentParser):
    """Escape control characters in argparse error details."""

    def error(self, message: str) -> NoReturn:
        """Print one safe usage error and terminate argument parsing."""

        self.print_usage(sys.stderr)
        self.exit(
            _EXIT_USAGE_ERROR,
            f"{self.prog}: error: {_escape_cli_text(message)}\n",
        )


def main(argv: Sequence[str] | None = None) -> int:
    """Run Pietto developer tooling and return a process exit code."""

    arguments = list(argv) if argv is not None else sys.argv[1:]
    parser = _build_parser()
    if arguments == []:
        parser.print_help()
        return 0

    if _is_check_json_request(arguments):
        try:
            namespace = _build_check_json_parser().parse_args(arguments[1:])
        except _JsonUsageError as error:
            _print_check_json(
                path=None,
                cli_errors=(
                    cli_json.CliError(
                        kind="usage",
                        message=str(error),
                    ),
                ),
            )
            return _EXIT_USAGE_ERROR
        except SystemExit as error:
            return _system_exit_code(error)
        return _run_check(namespace.path, output_format=_FORMAT_JSON)

    if _is_emit_sql_json_request(arguments):
        return _run_emit_sql_json_command(arguments[1:])

    try:
        namespace = parser.parse_args(arguments)
    except SystemExit as error:
        return _system_exit_code(error)
    if namespace.command == "check":
        return _run_check_command(namespace)
    if namespace.command == "emit-sql":
        return _run_emit_sql(
            namespace.path,
            dialect=namespace.dialect,
            output_path=namespace.output,
        )
    if namespace.command == "explain":
        return _run_explain(namespace.path, output_format=namespace.format)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Build the Phase 5 single-file developer CLI."""

    parser = _CliArgumentParser(
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
    _configure_check_parser(check_parser)
    emit_parser = subparsers.add_parser(
        "emit-sql",
        help="emit SQL for one Pietto file",
    )
    _configure_emit_sql_parser(emit_parser)
    explain_parser = subparsers.add_parser(
        "explain",
        help="explain semantic metadata for one Pietto file",
    )
    _configure_explain_parser(explain_parser)
    return parser


def _configure_check_parser(parser: argparse.ArgumentParser) -> None:
    """Add the check arguments to one parser."""

    parser.add_argument("path", type=Path, nargs="?", help="Pietto source file")
    parser.add_argument(
        "--project",
        type=Path,
        help="explicit Pietto project root",
    )
    parser.add_argument(
        "--format",
        choices=(_FORMAT_TEXT, _FORMAT_JSON),
        default=_FORMAT_TEXT,
        help="output format",
    )


def _configure_emit_sql_parser(parser: argparse.ArgumentParser) -> None:
    """Add the text-compatible emit-sql arguments to one parser."""

    parser.add_argument("path", type=Path, help="Pietto source file")
    parser.add_argument(
        "--dialect",
        choices=_ENABLED_SQL_DIALECTS,
        required=True,
        help="SQL dialect",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="write SQL artifacts to this file instead of stdout",
    )
    parser.add_argument(
        "--format",
        choices=(_FORMAT_TEXT, _FORMAT_JSON),
        default=_FORMAT_TEXT,
        help="output format",
    )


def _configure_explain_parser(parser: argparse.ArgumentParser) -> None:
    """Add the single-file explain arguments to one parser."""

    parser.add_argument("path", type=Path, help="Pietto source file")
    parser.add_argument(
        "--format",
        choices=(_FORMAT_TEXT, _FORMAT_JSON),
        default=_FORMAT_TEXT,
        help="output format",
    )


def _build_check_json_parser() -> argparse.ArgumentParser:
    """Build a check-only parser whose usage errors stay structured."""

    parser = _JsonArgumentParser(
        prog="pietto check",
        add_help=True,
    )
    parser.add_argument("path", type=Path, help="Pietto source file")
    parser.add_argument(
        "--format",
        choices=(_FORMAT_TEXT, _FORMAT_JSON),
        default=_FORMAT_JSON,
        help="output format",
    )
    return parser


def _build_emit_sql_json_parser() -> argparse.ArgumentParser:
    """Build an emit-sql parser that preserves raw JSON command values."""

    parser = _JsonArgumentParser(
        prog="pietto emit-sql",
        add_help=True,
    )
    parser.add_argument("path", type=Path, nargs="?", help="Pietto source file")
    parser.add_argument("--dialect", help="SQL dialect")
    parser.add_argument(
        "--output",
        type=Path,
        help="write SQL artifacts to this file instead of stdout",
    )
    parser.add_argument(
        "--format",
        choices=(_FORMAT_TEXT, _FORMAT_JSON),
        default=_FORMAT_JSON,
        help="output format",
    )
    return parser


class _JsonArgumentParser(argparse.ArgumentParser):
    """Raise command usage errors for JSON rendering instead of printing them."""

    def error(self, message: str) -> NoReturn:
        """Raise one structured command usage error."""

        raise _JsonUsageError(message)


def _system_exit_code(error: SystemExit) -> int:
    """Normalize a caught SystemExit using Python's process-exit semantics."""

    if error.code is None:
        return 0
    if isinstance(error.code, int):
        return error.code
    return 1


def _is_check_json_request(arguments: Sequence[str]) -> bool:
    """Return whether argv reliably selects check JSON presentation."""

    if not arguments or arguments[0] != "check" or _has_project_flag(arguments):
        return False
    return any(
        argument == "--format=json"
        or (
            argument == "--format"
            and index + 1 < len(arguments)
            and arguments[index + 1] == _FORMAT_JSON
        )
        for index, argument in enumerate(arguments)
    )


def _has_project_flag(arguments: Sequence[str]) -> bool:
    """Return whether argv mentions project mode explicitly."""

    return any(
        argument == "--project" or argument.startswith("--project=")
        for argument in arguments
    )


def _is_emit_sql_json_request(arguments: Sequence[str]) -> bool:
    """Return whether argv reliably selects emit-sql JSON presentation."""

    if not arguments or arguments[0] != "emit-sql":
        return False
    return any(
        argument == "--format=json"
        or (
            argument == "--format"
            and index + 1 < len(arguments)
            and arguments[index + 1] == _FORMAT_JSON
        )
        for index, argument in enumerate(arguments)
    )


def _run_emit_sql_json_command(arguments: Sequence[str]) -> int:
    """Validate one emit-sql JSON command before entering compilation."""

    try:
        namespace, unknown = _build_emit_sql_json_parser().parse_known_args(arguments)
    except _JsonUsageError as error:
        _print_emit_sql_json(
            path=None,
            dialect=None,
            cli_errors=(cli_json.CliError(kind="usage", message=str(error)),),
        )
        return _EXIT_USAGE_ERROR
    except SystemExit as error:
        return _system_exit_code(error)

    if unknown:
        _print_emit_sql_json(
            path=None,
            dialect=None,
            cli_errors=(
                cli_json.CliError(
                    kind="usage",
                    message=f"unrecognized arguments: {' '.join(unknown)}",
                ),
            ),
            output=_unwritten_output(namespace.output),
        )
        return _EXIT_USAGE_ERROR

    path: Path | None = namespace.path
    dialect: str | None = namespace.dialect
    output_path: Path | None = namespace.output
    output = _unwritten_output(output_path)
    if path is None:
        _print_emit_sql_json(
            path=None,
            dialect=dialect,
            cli_errors=(
                cli_json.CliError(
                    kind="usage",
                    message="the following arguments are required: path",
                ),
            ),
            output=output,
        )
        return _EXIT_USAGE_ERROR
    if dialect is None:
        _print_emit_sql_json(
            path=path,
            dialect=None,
            cli_errors=(
                cli_json.CliError(
                    kind="usage",
                    message="the following arguments are required: --dialect",
                ),
            ),
            output=output,
        )
        return _EXIT_USAGE_ERROR
    selected_emitter = _select_sql_emitter(dialect)
    if selected_emitter is None:
        _print_emit_sql_json(
            path=path,
            dialect=dialect,
            cli_errors=(
                cli_json.CliError(
                    kind="unsupported_dialect",
                    message=f"unsupported SQL dialect: {dialect}",
                ),
            ),
            output=output,
        )
        return _EXIT_USAGE_ERROR
    return _run_emit_sql_json(
        path,
        dialect=dialect,
        emitter=selected_emitter,
        output_path=output_path,
    )


def _select_sql_emitter(dialect: str) -> _SqlEmitter | None:
    """Select one dedicated backend from the closed enabled dialect set."""

    if dialect not in _ENABLED_SQL_DIALECTS:
        return None
    if dialect == "postgres":
        return sql_api.emit_postgres_sql
    if dialect == "mysql":
        return mysql_backend.emit_mysql_sql
    raise AssertionError(f"enabled SQL dialect has no emitter: {dialect}")


def _run_check_command(namespace: argparse.Namespace) -> int:
    """Dispatch check between single-file and project-root modes."""

    path: Path | None = namespace.path
    project_root: Path | None = namespace.project
    output_format: str = namespace.format

    if path is None and project_root is None:
        _print_check_usage_error("the following arguments are required: path")
        return _EXIT_USAGE_ERROR
    if path is not None and project_root is not None:
        _print_check_usage_error("path and --project are mutually exclusive")
        return _EXIT_USAGE_ERROR
    if project_root is not None:
        return _run_project_check(project_root, output_format=output_format)
    if path is None:
        raise AssertionError("check path was required before single-file mode")
    return _run_check(path, output_format=output_format)


def _run_project_check(root: Path, *, output_format: str) -> int:
    """Run project check in text or project JSON v2 mode."""

    parse_result = check_project_parse_only(root)
    if output_format == _FORMAT_JSON:
        _print_project_check_json(parse_result)
        if parse_result.errors:
            return _EXIT_USAGE_ERROR
        if _has_errors(parse_result.diagnostics):
            return _EXIT_DIAGNOSTIC_ERROR
        return 0

    if parse_result.errors:
        for error in parse_result.errors:
            _print_project_error(error)
        _render_diagnostics(parse_result.diagnostics, fallback_path=Path("."))
        return _EXIT_USAGE_ERROR

    _render_diagnostics(parse_result.diagnostics, fallback_path=Path("."))
    if _has_errors(parse_result.diagnostics):
        return _EXIT_DIAGNOSTIC_ERROR

    print("Project check OK: .")
    print(f"Files checked: {len(parse_result.inputs)}")
    return 0


def _print_project_check_json(parse_result: ProjectParseCheckResult) -> None:
    """Print one complete project JSON v2 check document to stdout."""

    document = project_check_result_to_json_dict(parse_result)
    print(render_project_json_document(document), end="")


def _print_check_usage_error(message: str) -> None:
    """Render one check usage error after cross-argument validation."""

    print(
        "usage: pietto check [-h] [--project PROJECT] [--format {text,json}] [path]",
        file=sys.stderr,
    )
    print(f"pietto check: error: {_escape_cli_text(message)}", file=sys.stderr)


def _print_project_error(error: ProjectDiscoveryError) -> None:
    """Render one project discovery error without leaking host paths."""

    message = f"project error: {error.kind.value}: {_escape_cli_text(error.message)}"
    if error.path is not None:
        message = f"{message} (path: {_escape_cli_text(error.path)})"
    print(message, file=sys.stderr)


def _run_check(path: Path, *, output_format: str = _FORMAT_TEXT) -> int:
    """Parse and semantically analyze one Pietto source file."""

    try:
        parse_result = parser_api.parse_file(path)
    except (OSError, UnicodeError) as error:
        if output_format == _FORMAT_JSON:
            _print_check_json(
                path=path,
                cli_errors=(
                    cli_json.CliError(
                        kind="file_read",
                        message=str(error),
                        path=path,
                    ),
                ),
            )
            return _EXIT_USAGE_ERROR
        _print_cli_error(path, str(error))
        return _EXIT_USAGE_ERROR

    if output_format == _FORMAT_JSON:
        return _run_check_json(path, parse_result)

    _render_diagnostics(parse_result.diagnostics, fallback_path=path)
    if _has_errors(parse_result.diagnostics):
        return _EXIT_DIAGNOSTIC_ERROR

    if parse_result.ast is None:
        _print_cli_error(path, "parser produced no AST")
        return _EXIT_DIAGNOSTIC_ERROR

    semantic_result = semantic_api.analyze(parse_result.ast)
    _render_diagnostics(semantic_result.diagnostics, fallback_path=path)
    if _has_errors(semantic_result.diagnostics):
        return _EXIT_DIAGNOSTIC_ERROR

    print(f"OK: {_escape_cli_text(str(path))}")
    return 0


def _run_check_json(path: Path, parse_result: parser_api.ParseResult) -> int:
    """Complete check and render one JSON result without human output."""

    diagnostics = parse_result.diagnostics
    if _has_errors(diagnostics):
        _print_check_json(path=path, diagnostics=diagnostics)
        return _EXIT_DIAGNOSTIC_ERROR

    if parse_result.ast is None:
        _print_check_json(
            path=path,
            cli_errors=(
                cli_json.CliError(
                    kind="usage",
                    message="parser produced no AST",
                    path=path,
                ),
            ),
        )
        return _EXIT_DIAGNOSTIC_ERROR

    semantic_result = semantic_api.analyze(parse_result.ast)
    diagnostics = (*diagnostics, *semantic_result.diagnostics)
    _print_check_json(path=path, diagnostics=diagnostics)
    if _has_errors(semantic_result.diagnostics):
        return _EXIT_DIAGNOSTIC_ERROR
    return 0


def _print_check_json(
    *,
    path: str | Path | None,
    diagnostics: Sequence[Diagnostic] = (),
    cli_errors: Sequence[cli_json.CliError] = (),
) -> None:
    """Print one complete check JSON document to stdout."""

    document = cli_json.check_result_to_json_dict(
        path=path,
        diagnostics=diagnostics,
        cli_errors=cli_errors,
    )
    print(cli_json.render_json_document(document), end="")


def _run_explain(path: Path, *, output_format: str = _FORMAT_TEXT) -> int:
    """Build and render Semantic Metadata Artifact v1 for one Pietto file."""

    try:
        parse_result = parser_api.parse_file(path)
    except (OSError, UnicodeError) as error:
        if output_format == _FORMAT_JSON:
            _print_explain_failure_json(
                path=path,
                stage="parse",
                diagnostics=(),
                message=(
                    "Semantic Metadata Artifact v1 metadata is unavailable "
                    "because the input file could not be read or decoded."
                ),
            )
            return _EXIT_USAGE_ERROR
        _print_cli_error(path, str(error))
        return _EXIT_USAGE_ERROR

    diagnostics = parse_result.diagnostics
    if _has_errors(diagnostics):
        return _render_explain_failure(
            path=path,
            output_format=output_format,
            stage="parse",
            diagnostics=diagnostics,
        )

    if parse_result.ast is None:
        return _render_explain_failure(
            path=path,
            output_format=output_format,
            stage="parse",
            diagnostics=diagnostics,
            fallback_message="parser produced no AST",
        )

    semantic_result = semantic_api.analyze(parse_result.ast)
    diagnostics = (*diagnostics, *semantic_result.diagnostics)
    if _has_errors(semantic_result.diagnostics):
        return _render_explain_failure(
            path=path,
            output_format=output_format,
            stage="semantic",
            diagnostics=diagnostics,
        )

    ir_result = ir_api.build_ir(parse_result.ast, semantic_result.model)
    diagnostics = (*diagnostics, *ir_result.diagnostics)
    if _has_errors(ir_result.diagnostics):
        return _render_explain_failure(
            path=path,
            output_format=output_format,
            stage="ir",
            diagnostics=diagnostics,
        )

    if ir_result.ir is None:
        return _render_explain_failure(
            path=path,
            output_format=output_format,
            stage="ir",
            diagnostics=diagnostics,
            fallback_message="IR builder produced no IR",
        )

    artifact = build_semantic_metadata_artifact(
        path=path,
        script=parse_result.ast,
        semantic_result=semantic_result,
        ir=ir_result.ir,
        diagnostics=diagnostics,
    )
    if output_format == _FORMAT_JSON:
        _print_explain_json(semantic_metadata_artifact_to_json_dict(artifact))
        return 0

    _render_diagnostics(diagnostics, fallback_path=path)
    print(render_semantic_metadata_text(artifact))
    return 0


def _render_explain_failure(
    *,
    path: Path,
    output_format: str,
    stage: SemanticMetadataFailureStage,
    diagnostics: tuple[Diagnostic, ...],
    fallback_message: str | None = None,
) -> int:
    if output_format == _FORMAT_JSON:
        _print_explain_failure_json(
            path=path,
            stage=stage,
            diagnostics=diagnostics,
            message=_METADATA_FAILURE_MESSAGES[stage],
        )
    else:
        _render_diagnostics(diagnostics, fallback_path=path)
        if fallback_message is not None:
            _print_cli_error(path, fallback_message)
    return _EXIT_DIAGNOSTIC_ERROR


def _print_explain_failure_json(
    *,
    path: str | Path | None,
    stage: SemanticMetadataFailureStage,
    diagnostics: Sequence[Diagnostic],
    message: str,
) -> None:
    _print_explain_json(
        build_semantic_metadata_error_envelope(
            path=path,
            stage=stage,
            diagnostics=diagnostics,
            message=message,
        )
    )


def _print_explain_json(document: dict[str, object]) -> None:
    """Print one complete Semantic Metadata Artifact v1 JSON document."""

    print(cli_json.render_json_document(document), end="")


def _run_emit_sql_json(
    path: Path,
    *,
    dialect: str,
    emitter: _SqlEmitter,
    output_path: Path | None,
) -> int:
    """Compile one file and render the ordered emit-sql JSON result."""

    output = _unwritten_output(output_path)
    if output_path is not None:
        try:
            _validate_output_path(path, output_path)
        except (OSError, ValueError) as error:
            _print_emit_sql_json(
                path=path,
                dialect=dialect,
                cli_errors=(
                    cli_json.CliError(
                        kind="output_path",
                        message=str(error),
                        path=output_path,
                    ),
                ),
                output=output,
            )
            return _EXIT_USAGE_ERROR

    try:
        parse_result = parser_api.parse_file(path)
    except (OSError, UnicodeError) as error:
        _print_emit_sql_json(
            path=path,
            dialect=dialect,
            cli_errors=(
                cli_json.CliError(
                    kind="file_read",
                    message=str(error),
                    path=path,
                ),
            ),
            output=output,
        )
        return _EXIT_USAGE_ERROR

    diagnostics = parse_result.diagnostics
    if _has_errors(diagnostics):
        _print_emit_sql_json(
            path=path,
            dialect=dialect,
            diagnostics=diagnostics,
            output=output,
        )
        return _EXIT_DIAGNOSTIC_ERROR

    if parse_result.ast is None:
        _print_emit_sql_json(
            path=path,
            dialect=dialect,
            cli_errors=(
                cli_json.CliError(
                    kind="usage",
                    message="parser produced no AST",
                    path=path,
                ),
            ),
            output=output,
        )
        return _EXIT_USAGE_ERROR

    semantic_result = semantic_api.analyze(parse_result.ast)
    diagnostics = (*diagnostics, *semantic_result.diagnostics)
    if _has_errors(semantic_result.diagnostics):
        _print_emit_sql_json(
            path=path,
            dialect=dialect,
            diagnostics=diagnostics,
            output=output,
        )
        return _EXIT_DIAGNOSTIC_ERROR

    ir_result = ir_api.build_ir(parse_result.ast, semantic_result.model)
    diagnostics = (*diagnostics, *ir_result.diagnostics)
    if _has_errors(ir_result.diagnostics):
        _print_emit_sql_json(
            path=path,
            dialect=dialect,
            diagnostics=diagnostics,
            output=output,
        )
        return _EXIT_DIAGNOSTIC_ERROR

    if ir_result.ir is None:
        _print_emit_sql_json(
            path=path,
            dialect=dialect,
            diagnostics=diagnostics,
            cli_errors=(
                cli_json.CliError(
                    kind="usage",
                    message="IR builder produced no IR",
                    path=path,
                ),
            ),
            output=output,
        )
        return _EXIT_USAGE_ERROR

    sql_result = emitter(ir_result.ir)
    diagnostics = (*diagnostics, *sql_result.diagnostics)
    if _has_errors(sql_result.diagnostics):
        _print_emit_sql_json(
            path=path,
            dialect=dialect,
            diagnostics=diagnostics,
            artifacts=sql_result.artifacts,
            output=output,
        )
        return _EXIT_DIAGNOSTIC_ERROR

    if output_path is not None:
        try:
            _write_sql_artifacts(sql_result.artifacts, output_path)
        except OSError as error:
            _print_emit_sql_json(
                path=path,
                dialect=dialect,
                diagnostics=diagnostics,
                cli_errors=(
                    cli_json.CliError(
                        kind="output_write",
                        message=str(error),
                        path=output_path,
                    ),
                ),
                artifacts=sql_result.artifacts,
                output=output,
            )
            return _EXIT_USAGE_ERROR
        output = cli_json.OutputStatus(path=output_path, written=True)

    _print_emit_sql_json(
        path=path,
        dialect=dialect,
        diagnostics=diagnostics,
        artifacts=sql_result.artifacts,
        output=output,
    )
    return 0


def _print_emit_sql_json(
    *,
    path: str | Path | None,
    dialect: str | None,
    diagnostics: Sequence[Diagnostic] = (),
    cli_errors: Sequence[cli_json.CliError] = (),
    artifacts: Sequence[sql_api.SqlArtifact] = (),
    output: cli_json.OutputStatus | None = None,
) -> None:
    """Print one complete emit-sql JSON document to stdout."""

    document = cli_json.emit_sql_result_to_json_dict(
        path=path,
        dialect=dialect,
        diagnostics=diagnostics,
        cli_errors=cli_errors,
        artifacts=artifacts,
        output=output,
    )
    print(cli_json.render_json_document(document), end="")


def _unwritten_output(output_path: Path | None) -> cli_json.OutputStatus | None:
    """Return the requested JSON output status before a successful write."""

    if output_path is None:
        return None
    return cli_json.OutputStatus(path=output_path, written=False)


def _run_emit_sql(
    path: Path,
    *,
    dialect: str,
    output_path: Path | None,
) -> int:
    """Compile one Pietto file with the explicitly selected SQL backend."""

    emitter = _select_sql_emitter(dialect)
    if emitter is None:
        _print_cli_error(path, f"unsupported SQL dialect: {dialect}")
        return _EXIT_USAGE_ERROR

    if output_path is not None:
        try:
            _validate_output_path(path, output_path)
        except (OSError, ValueError) as error:
            _print_cli_error(output_path, str(error))
            return _EXIT_USAGE_ERROR

    try:
        parse_result = parser_api.parse_file(path)
    except (OSError, UnicodeError) as error:
        _print_cli_error(path, str(error))
        return _EXIT_USAGE_ERROR

    _render_diagnostics(parse_result.diagnostics, fallback_path=path)
    if _has_errors(parse_result.diagnostics):
        return _EXIT_DIAGNOSTIC_ERROR

    if parse_result.ast is None:
        _print_cli_error(path, "parser produced no AST")
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
        _print_cli_error(path, "IR builder produced no IR")
        return _EXIT_DIAGNOSTIC_ERROR

    sql_result = emitter(ir_result.ir)
    _render_diagnostics(sql_result.diagnostics, fallback_path=path)
    has_backend_errors = _has_errors(sql_result.diagnostics)
    if output_path is None:
        _print_sql_artifacts(sql_result.artifacts)
    elif not has_backend_errors:
        try:
            _write_sql_artifacts(sql_result.artifacts, output_path)
        except OSError as error:
            _print_cli_error(output_path, str(error))
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
    """Atomically replace one regular output file with rendered SQL text."""

    sql = _format_sql_artifacts(artifacts)
    text = f"{sql}\n" if sql else ""
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(text)
        os.replace(temporary_path, output_path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def _validate_output_path(input_path: Path, output_path: Path) -> None:
    """Reject unsafe output destinations before compilation begins."""

    if output_path.is_symlink():
        raise ValueError("output path must not be a symbolic link")
    if _paths_refer_to_same_file(input_path, output_path):
        raise ValueError("output path must differ from the input file")


def _paths_refer_to_same_file(input_path: Path, output_path: Path) -> bool:
    """Compare existing files and normalized paths without requiring output."""

    if input_path.resolve(strict=False) == output_path.resolve(strict=False):
        return True
    try:
        return input_path.samefile(output_path)
    except FileNotFoundError:
        return False


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
        f"{_escape_cli_text(path)}:{location.line}:{location.column} "
        f"{_escape_cli_text(diagnostic.code)} "
        f"{_escape_cli_text(diagnostic.severity.value)}: "
        f"{_escape_cli_text(diagnostic.message)}"
    )


def _print_cli_error(path: Path, message: str) -> None:
    """Render one escaped path-prefixed CLI error."""

    print(
        f"{_escape_cli_text(str(path))}: error: {_escape_cli_text(message)}",
        file=sys.stderr,
    )


def _escape_cli_text(value: str) -> str:
    """Escape C0 controls and DEL for single-line terminal output."""

    named_escapes = {
        "\x00": r"\x00",
        "\t": r"\t",
        "\n": r"\n",
        "\r": r"\r",
        "\x1b": r"\x1b",
        "\x7f": r"\x7f",
    }
    escaped: list[str] = []
    for character in value:
        replacement = named_escapes.get(character)
        if replacement is not None:
            escaped.append(replacement)
        elif ord(character) < 0x20:
            escaped.append(f"\\x{ord(character):02x}")
        else:
            escaped.append(character)
    return "".join(escaped)


def _has_errors(diagnostics: tuple[Diagnostic, ...]) -> bool:
    """Return whether a compiler phase produced an error diagnostic."""

    return any(diagnostic.severity is Severity.ERROR for diagnostic in diagnostics)


def _package_version() -> str:
    """Read installed package metadata with a source-tree fallback."""

    try:
        return version("pietto")
    except PackageNotFoundError:
        return _FALLBACK_VERSION
