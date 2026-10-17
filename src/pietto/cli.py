"""Command-line entry point for Pietto developer tooling."""

from __future__ import annotations

import argparse
import errno
import os
import stat
import sys
from collections.abc import Callable, Sequence
from dataclasses import replace
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import IO, NoReturn

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
from pietto._project.check import (
    check_project_parse_only,
    project_recursion_limit_diagnostic,
)
from pietto._project.project_completed_semantics import (
    build_project_completed_semantic_result,
)
from pietto._project.json_v2 import (
    project_check_result_to_json_dict,
    render_project_json_document,
)
from pietto._project.module_carrier import ProjectCompilationMode
from pietto._project.project_sql_emission_cli import (
    project_mode_requested,
    run_project_emit_sql,
)
from pietto._project_explain.json_v1 import serialize_project_explain_json_document
from pietto._project_explain.runtime_builder import (
    ProjectExplainRuntimeOutcome,
    _build_project_explain_runtime,
)
from pietto._project_explain.text import render_project_explain_text
from pietto._project.model import (
    ProjectDiscoveryError,
    ProjectParseCheckResult,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._output_file import (
    is_owned_by_another_user,
    is_read_only,
    open_replacement,
)
from pietto._terminal_text import escape_unicode_controls
from pietto.errors import Diagnostic, Severity

_FALLBACK_VERSION = "0.1.3"
_EXIT_DIAGNOSTIC_ERROR = 1
_EXIT_USAGE_ERROR = 2
_FORMAT_TEXT = "text"
_FORMAT_JSON = "json"
_ENABLED_SQL_DIALECTS = ("postgres", "mysql")
_CHECK_MODES = tuple(mode.value for mode in semantic_api.CheckMode)
_CHECK_MODE_HELP = "check mode; overrides a source header mode (default: checked)"
_PROJECT_EMIT_SQL_USAGE = (
    "project mode: pietto emit-sql --project PATH --module LOGICAL_MODULE"
    " --kind {table,query} --name NAME --dialect {postgres,mysql}"
    " --emission-contract FILE [--literal-policy {preserve,bind-safe}]"
    " [--format {text,json}] [--output FILE]"
)
_METADATA_FAILURE_MESSAGES = {
    "parse": "Semantic Metadata Artifact v1 metadata is unavailable because parsing failed.",
    "semantic": "Semantic Metadata Artifact v1 metadata is unavailable because semantic analysis failed.",
    "ir": "Semantic Metadata Artifact v1 metadata is unavailable because IR construction failed.",
}
_OS_ERROR_CLASS_REASONS: tuple[tuple[type[OSError], str], ...] = (
    (FileNotFoundError, "No such file or directory"),
    (IsADirectoryError, "Is a directory"),
    (NotADirectoryError, "Not a directory"),
    (PermissionError, "Permission denied"),
    (FileExistsError, "File exists"),
)
_OS_ERROR_ERRNO_REASONS: dict[int | None, str] = {
    errno.ENOSPC: "No space left on device",
    errno.EROFS: "Read-only file system",
    errno.ENAMETOOLONG: "File name too long",
    errno.ELOOP: "Too many levels of symbolic links",
}
type _SqlEmitter = Callable[[ir_api.ScriptIR], sql_api.SqlResult]


class _JsonUsageError(Exception):
    """A command argument error rendered through a JSON result contract."""


class _StdoutWriteError(Exception):
    """Standard output is closed or rejected command output; see __cause__.

    An optional argument is a command's own notice, reported even for a
    broken pipe in place of the default notices.
    """


class _CliArgumentParser(argparse.ArgumentParser):
    """Route argparse output through the CLI stream writers.

    Help and --version are command output on stdout, so a closed or failing
    stdout is handled like any other result; usage errors are escaped and go
    to stderr, never falling back to stdout when stderr is closed.
    """

    def _print_message(self, message: str, file: object = None) -> None:
        if not message:
            return
        # argparse passes sys.stdout or sys.stderr, None when it is closed. A
        # None that is not a closed stdout is a closed stderr: drop the text.
        if file is sys.stdout:
            _write_stdout(message)
        else:
            _write_stderr(message)

    def error(self, message: str) -> NoReturn:
        """Print one safe usage error and terminate argument parsing."""

        _write_stderr(
            f"{self.format_usage()}{self.prog}: error: {_escape_cli_text(message)}\n"
        )
        self.exit(_EXIT_USAGE_ERROR)


def main(argv: Sequence[str] | None = None) -> int:
    """Run Pietto developer tooling and return a process exit code."""

    try:
        exit_code = _main(argv)
        _flush_stdout()
    except UnicodeEncodeError:
        _print_output_encoding_error()
        exit_code = _EXIT_USAGE_ERROR
    except _StdoutWriteError as error:
        _discard(sys.stdout)
        cause = error.__cause__
        if error.args:
            _write_stderr(f"{error}\n")
        elif not isinstance(cause, OSError):
            _write_stderr("pietto: error: standard output is closed\n")
        elif not _reader_closed(cause):
            _write_stderr(
                "pietto: error: standard output could not be written: "
                f"{_cli_error_message(cause, None)}\n"
            )
        exit_code = _EXIT_USAGE_ERROR
    _flush_stderr()
    return exit_code


def _reader_closed(error: OSError) -> bool:
    """Whether stdout failed because its reader closed the pipe, a quiet exit.

    Windows reports a pipe whose reader has gone as EINVAL rather than EPIPE,
    which CPython also treats as a closed pipe (bpo-19612, bpo-30418).
    """

    return isinstance(error, BrokenPipeError) or (
        sys.platform == "win32" and error.errno == errno.EINVAL
    )


def _main(argv: Sequence[str] | None = None) -> int:
    """Run one CLI command after terminal encoding is available."""

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
        return _run_check(
            namespace.path,
            output_format=_FORMAT_JSON,
            check_mode=_check_mode(namespace.check_mode),
        )

    if arguments[0] == "emit-sql" and project_mode_requested(arguments[1:]):
        return _run_project_emit_sql(arguments[1:])

    if _is_emit_sql_json_request(arguments):
        return _run_emit_sql_json_command(arguments[1:])

    try:
        namespace = parser.parse_args(arguments)
    except SystemExit as error:
        return _system_exit_code(error)
    if namespace.command == "check":
        return _run_check_command(namespace)
    if namespace.command == "emit-sql":
        if namespace.format == _FORMAT_JSON:
            # Reached when "--" precedes the subcommand, so the pre-scan saw none.
            command_end = arguments.index(namespace.command) + 1
            return _run_emit_sql_json_command(arguments[command_end:])
        return _run_emit_sql(
            namespace.path,
            dialect=namespace.dialect,
            output_path=namespace.output,
            check_mode=_check_mode(namespace.check_mode),
        )
    if namespace.command == "explain":
        return _run_explain_command(namespace)
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
        help="emit SQL for one Pietto file or one explicit project owner",
        epilog=_PROJECT_EMIT_SQL_USAGE,
    )
    _configure_emit_sql_parser(emit_parser)
    explain_parser = subparsers.add_parser(
        "explain",
        help="explain one Pietto file or project",
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
    parser.add_argument("--check-mode", choices=_CHECK_MODES, help=_CHECK_MODE_HELP)


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
    parser.add_argument("--check-mode", choices=_CHECK_MODES, help=_CHECK_MODE_HELP)


def _configure_explain_parser(parser: argparse.ArgumentParser) -> None:
    """Add the file-or-project explain arguments to one parser."""

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
    parser.add_argument("--check-mode", choices=_CHECK_MODES, help=_CHECK_MODE_HELP)


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
    parser.add_argument("--check-mode", choices=_CHECK_MODES, help=_CHECK_MODE_HELP)
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
    parser.add_argument("--check-mode", choices=_CHECK_MODES, help=_CHECK_MODE_HELP)
    return parser


class _JsonArgumentParser(_CliArgumentParser):
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
    return _selects_json_format(arguments)


def _selects_json_format(arguments: Sequence[str]) -> bool:
    """Return whether argparse would resolve --format to valid values ending in json."""

    values = _option_values(arguments, "--format")
    return (
        bool(values)
        and values[-1] == _FORMAT_JSON
        and all(value in (_FORMAT_TEXT, _FORMAT_JSON) for value in values)
    )


def _has_project_flag(arguments: Sequence[str]) -> bool:
    """Return whether argv mentions project mode explicitly."""

    return bool(_option_values(arguments, "--project"))


def _option_values(arguments: Sequence[str], option: str) -> list[str]:
    """Return the values argparse would read for one check or emit-sql option.

    Like argparse, this stops at "--" and accepts any unique prefix of the
    option from three characters on; no two options of those commands share
    their first letter.
    """

    values: list[str] = []
    for index, argument in enumerate(arguments):
        if argument == "--":
            break
        name, separator, value = argument.partition("=")
        if len(name) < len("--f") or not option.startswith(name):
            continue
        if not separator:
            value = arguments[index + 1] if index + 1 < len(arguments) else ""
        values.append(value)
    return values


def _is_emit_sql_json_request(arguments: Sequence[str]) -> bool:
    """Return whether argv reliably selects emit-sql JSON presentation."""

    if not arguments or arguments[0] != "emit-sql":
        return False
    return _selects_json_format(arguments)


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
        check_mode=_check_mode(namespace.check_mode),
    )


def _check_mode(value: str | None) -> semantic_api.CheckMode | None:
    """Return the explicit --check-mode; None keeps the header or the default."""

    return None if value is None else semantic_api.CheckMode(value)


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
    check_mode = _check_mode(namespace.check_mode)

    if path is None and project_root is None:
        _print_check_usage_error("the following arguments are required: path")
        return _EXIT_USAGE_ERROR
    if path is not None and project_root is not None:
        _print_check_usage_error("path and --project are mutually exclusive")
        return _EXIT_USAGE_ERROR
    if project_root is not None and check_mode is not None:
        _print_check_usage_error("--check-mode and --project are mutually exclusive")
        return _EXIT_USAGE_ERROR
    if project_root is not None:
        return _run_project_check(project_root, output_format=output_format)
    if path is None:
        raise AssertionError("check path was required before single-file mode")
    return _run_check(path, output_format=output_format, check_mode=check_mode)


def _run_project_check(root: Path, *, output_format: str) -> int:
    """Run project check in text or project JSON v2 mode."""

    parse_result = check_project_parse_only(root)
    if output_format == _FORMAT_JSON:
        if parse_result.ok:
            semantic_diagnostics, semantic_ok = _project_check_semantics(parse_result)
            _print_project_check_json(
                parse_result,
                semantic_diagnostics=semantic_diagnostics,
            )
            if not semantic_ok:
                return _EXIT_DIAGNOSTIC_ERROR
            return 0

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

    semantic_diagnostics, semantic_ok = _project_check_semantics(parse_result)
    _render_diagnostics(semantic_diagnostics, fallback_path=Path("."))
    if not semantic_ok:
        return _EXIT_DIAGNOSTIC_ERROR

    _write_stdout(f"Project check OK: .\nFiles checked: {len(parse_result.inputs)}\n")
    return 0


def _project_check_semantics(
    parse_result: ProjectParseCheckResult,
) -> tuple[tuple[Diagnostic, ...], bool]:
    """Check project semantics; as in a single file, exhausting the recursion
    limit is PIE-S2006."""

    try:
        return _project_semantic_boundary(
            build_empty_project_semantic_result(parse_result)
        )
    except RecursionError:
        return (project_recursion_limit_diagnostic(parse_result),), False


def _project_semantic_boundary(
    semantic_result: ProjectSemanticResult,
) -> tuple[tuple[Diagnostic, ...], bool]:
    """Select the completed boundary only for explicit-module Project checks."""

    if semantic_result.compilation_mode is ProjectCompilationMode.EXPLICIT_MODULES:
        completed = build_project_completed_semantic_result(semantic_result)
        return completed.diagnostics, completed.ok
    return semantic_result.diagnostics, semantic_result.ok


def _print_project_check_json(
    parse_result: ProjectParseCheckResult,
    *,
    semantic_diagnostics: Sequence[Diagnostic] = (),
) -> None:
    """Print one complete project JSON v2 check document to stdout."""

    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_diagnostics,
    )
    _write_stdout(render_project_json_document(document))


def _print_check_usage_error(message: str) -> None:
    """Render one check usage error after cross-argument validation."""

    _write_stderr(
        "usage: pietto check [-h] [--project PROJECT] [--format {text,json}]"
        " [--check-mode {loose,checked,strict}] [path]\n"
        f"pietto check: error: {_escape_cli_text(message)}\n"
    )


def _print_project_error(error: ProjectDiscoveryError) -> None:
    """Render one project discovery error without leaking host paths."""

    message = f"project error: {error.kind.value}: {_escape_cli_text(error.message)}"
    if error.path is not None:
        message = f"{message} (path: {_escape_cli_text(error.path)})"
    _write_stderr(f"{message}\n")


def _run_check(
    path: Path,
    *,
    output_format: str = _FORMAT_TEXT,
    check_mode: semantic_api.CheckMode | None = None,
) -> int:
    """Parse and semantically analyze one Pietto source file."""

    try:
        parse_result = parser_api.parse_file(path)
    except (OSError, UnicodeError) as error:
        message = _cli_error_message(error, path)
        if output_format == _FORMAT_JSON:
            _print_check_json(
                path=path,
                cli_errors=(
                    cli_json.CliError(
                        kind="file_read",
                        message=message,
                        path=path,
                    ),
                ),
            )
            return _EXIT_USAGE_ERROR
        _print_cli_error(path, message)
        return _EXIT_USAGE_ERROR

    if output_format == _FORMAT_JSON:
        return _run_check_json(path, parse_result, check_mode)

    _render_diagnostics(parse_result.diagnostics, fallback_path=path)
    if _has_errors(parse_result.diagnostics):
        return _EXIT_DIAGNOSTIC_ERROR

    if parse_result.ast is None:
        _print_cli_error(path, "parser produced no AST")
        return _EXIT_DIAGNOSTIC_ERROR

    semantic_result = semantic_api.analyze(parse_result.ast, mode_override=check_mode)
    _render_diagnostics(semantic_result.diagnostics, fallback_path=path)
    if _has_errors(semantic_result.diagnostics):
        return _EXIT_DIAGNOSTIC_ERROR

    _write_stdout(f"OK: {_escape_cli_text(str(path))}\n")
    return 0


def _run_check_json(
    path: Path,
    parse_result: parser_api.ParseResult,
    check_mode: semantic_api.CheckMode | None,
) -> int:
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

    semantic_result = semantic_api.analyze(parse_result.ast, mode_override=check_mode)
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
    _write_stdout(cli_json.render_json_document(document))


def _run_explain(
    path: Path,
    *,
    output_format: str = _FORMAT_TEXT,
    check_mode: semantic_api.CheckMode | None = None,
) -> int:
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
        _print_cli_error(path, _cli_error_message(error, path))
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

    semantic_result = semantic_api.analyze(parse_result.ast, mode_override=check_mode)
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
    if artifact.path is not None:
        artifact = replace(artifact, path=_escape_cli_text(artifact.path))
    _write_stdout(f"{render_semantic_metadata_text(artifact)}\n")
    return 0


def _run_explain_command(namespace: argparse.Namespace) -> int:
    """Dispatch explain between the existing file and explicit project modes."""

    path: Path | None = namespace.path
    project_root: Path | None = namespace.project
    output_format: str = namespace.format
    check_mode = _check_mode(namespace.check_mode)
    if path is None and project_root is None:
        _print_explain_usage_error("the following arguments are required: path")
        return _EXIT_USAGE_ERROR
    if path is not None and project_root is not None:
        _print_explain_usage_error("path and --project are mutually exclusive")
        return _EXIT_USAGE_ERROR
    if project_root is not None and check_mode is not None:
        _print_explain_usage_error("--check-mode and --project are mutually exclusive")
        return _EXIT_USAGE_ERROR
    if project_root is not None:
        return _run_project_explain(project_root, output_format=output_format)
    if path is None:
        raise AssertionError("explain path was required before file mode")
    return _run_explain(path, output_format=output_format, check_mode=check_mode)


def _print_explain_usage_error(message: str) -> None:
    _write_stderr(
        "usage: pietto explain [-h] [--project PROJECT] [--format {text,json}]"
        " [--check-mode {loose,checked,strict}] [path]\n"
        f"pietto explain: error: {_escape_cli_text(message)}\n"
    )


def _run_project_explain(root: Path, *, output_format: str) -> int:
    """Render one Slice 13 runtime result through the selected public surface."""

    result = _build_project_explain_runtime(root)
    if output_format == _FORMAT_JSON:
        _write_stdout(serialize_project_explain_json_document(result.envelope))
    elif result.outcome is ProjectExplainRuntimeOutcome.SUCCESS:
        _write_stdout(render_project_explain_text(result.envelope))
    else:
        _write_stderr(render_project_explain_text(result.envelope))
    if result.outcome is ProjectExplainRuntimeOutcome.SUCCESS:
        return 0
    if result.outcome is ProjectExplainRuntimeOutcome.DIAGNOSTIC_ERROR:
        return _EXIT_DIAGNOSTIC_ERROR
    return _EXIT_USAGE_ERROR


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

    _write_stdout(cli_json.render_json_document(document))


def _run_emit_sql_json(
    path: Path,
    *,
    dialect: str,
    emitter: _SqlEmitter,
    output_path: Path | None,
    check_mode: semantic_api.CheckMode | None,
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
                        message=_cli_error_message(error, output_path),
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
                    message=_cli_error_message(error, path),
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

    semantic_result = semantic_api.analyze(parse_result.ast, mode_override=check_mode)
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
        except (OSError, ValueError) as error:
            _print_emit_sql_json(
                path=path,
                dialect=dialect,
                diagnostics=diagnostics,
                cli_errors=(
                    cli_json.CliError(
                        kind="output_write",
                        message=_cli_error_message(error, output_path),
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
    _write_stdout(cli_json.render_json_document(document))


def _run_project_emit_sql(arguments: Sequence[str]) -> int:
    """Run the explicit project emit-sql mode and write its exact stream bytes."""

    result = run_project_emit_sql(arguments)
    if result.stderr:
        _write_stderr(result.stderr)
    if result.stdout:
        try:
            _write_stdout(result.stdout)
            _flush_stdout()
        except _StdoutWriteError as error:
            note = "pietto emit-sql: error: standard output could not be written"
            if result.written:
                note += "; the replaced artifact file is kept"
            raise _StdoutWriteError(note) from error.__cause__
    return result.exit_code


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
    check_mode: semantic_api.CheckMode | None,
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
            _print_cli_error(output_path, _cli_error_message(error, output_path))
            return _EXIT_USAGE_ERROR

    try:
        parse_result = parser_api.parse_file(path)
    except (OSError, UnicodeError) as error:
        _print_cli_error(path, _cli_error_message(error, path))
        return _EXIT_USAGE_ERROR

    _render_diagnostics(parse_result.diagnostics, fallback_path=path)
    if _has_errors(parse_result.diagnostics):
        return _EXIT_DIAGNOSTIC_ERROR

    if parse_result.ast is None:
        _print_cli_error(path, "parser produced no AST")
        return _EXIT_DIAGNOSTIC_ERROR

    semantic_result = semantic_api.analyze(parse_result.ast, mode_override=check_mode)
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
        except (OSError, ValueError) as error:
            _print_cli_error(output_path, _cli_error_message(error, output_path))
            return _EXIT_USAGE_ERROR
    if has_backend_errors:
        return _EXIT_DIAGNOSTIC_ERROR
    return 0


def _print_sql_artifacts(artifacts: tuple[sql_api.SqlArtifact, ...]) -> None:
    """Print ordered SQL artifacts without changing their stored text."""

    if artifacts:
        _write_stdout(f"{_format_sql_artifacts(artifacts)}\n")


def _write_sql_artifacts(
    artifacts: tuple[sql_api.SqlArtifact, ...],
    output_path: Path,
) -> None:
    """Atomically replace one regular output file with rendered SQL text."""

    if not artifacts:
        raise ValueError("no SQL artifacts to write; the output file was not changed")
    if is_read_only(output_path):
        raise ValueError("output file is read-only; the output file was not changed")
    if is_owned_by_another_user(output_path):
        raise ValueError(
            "output file belongs to another user; the output file was not changed"
        )
    data = f"{_format_sql_artifacts(artifacts)}\n".encode("utf-8")
    temporary_path: Path | None = None
    try:
        temporary, temporary_path = open_replacement(output_path)
        with temporary:
            temporary.write(data)
        os.replace(temporary_path, output_path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def _validate_output_path(input_path: Path, output_path: Path) -> None:
    """Reject unsafe output destinations before compilation begins.

    Only a provable symbolic link, an existing object that is neither a
    regular file nor a directory, or the same file is rejected. A path that
    cannot be inspected is left to the later steps: the input read reports
    file_read, and the output write, which cannot reach a path lstat or stat
    could not, reports output_write.
    """

    try:
        is_symlink = output_path.is_symlink()
    except OSError:
        is_symlink = False
    if is_symlink:
        raise ValueError("output path must not be a symbolic link")
    try:
        mode = os.stat(output_path).st_mode
    except OSError:
        mode = None
    if mode is not None and not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
        raise ValueError("output path must be a regular file")
    if _paths_refer_to_same_file(input_path, output_path):
        raise ValueError("output path must differ from the input file")


def _paths_refer_to_same_file(input_path: Path, output_path: Path) -> bool:
    """Compare existing files and normalized paths without requiring output."""

    try:
        if input_path.resolve(strict=False) == output_path.resolve(strict=False):
            return True
    except RuntimeError:
        pass  # Python 3.12 reports a symbolic-link loop from resolve() this way.
    try:
        return os.path.samestat(input_path.stat(), output_path.stat())
    except OSError:
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
        _write_stderr(
            f"{_format_diagnostic(diagnostic, fallback_path=fallback_path)}\n"
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

    _write_stderr(
        f"{_escape_cli_text(str(path))}: error: {_escape_cli_text(message)}\n"
    )


def _cli_error_message(error: Exception, path: Path | None) -> str:
    """Describe a handled read/write error about one user path or stdout.

    Non-OSError text is already fixed English and is kept; an OSError gets a
    fixed reason and its codes, never OS-supplied names or text.
    """

    if not isinstance(error, OSError):
        return str(error)
    reason = next(
        (text for kind, text in _OS_ERROR_CLASS_REASONS if isinstance(error, kind)),
        _OS_ERROR_ERRNO_REASONS.get(error.errno, "Operating system error"),
    )
    if isinstance(error, PermissionError) and path is not None:
        # Windows reports opening or replacing a directory as EACCES; the stat
        # only words the message and never changes the failure.
        try:
            if path.is_dir():
                reason = "Is a directory"
        except OSError:
            pass
    codes = [] if error.errno is None else [f"errno {error.errno}"]
    winerror = getattr(error, "winerror", None)
    if winerror is not None:
        codes.append(f"winerror {winerror}")
    return f"{reason} ({', '.join(codes)})" if codes else reason


def _print_output_encoding_error() -> None:
    """Report a terminal encoding failure without repeating unencodable text."""

    _write_stderr("pietto: error: terminal output could not be encoded\n")


def _write_stdout(output: str | bytes) -> None:
    """Write command output; bytes go to the binary buffer when there is one.

    A closed stdout or a failed write raises _StdoutWriteError instead of
    dropping the output or escaping as a traceback.
    """

    stream = sys.stdout
    if stream is None:
        raise _StdoutWriteError
    try:
        if isinstance(output, str):
            stream.write(output)
        elif (buffer := getattr(stream, "buffer", None)) is None:
            stream.write(output.decode("utf-8"))
        else:
            buffer.write(output)
    except UnicodeEncodeError:
        raise
    except (OSError, ValueError) as error:
        raise _StdoutWriteError from error


def _flush_stdout() -> None:
    """Flush buffered output so its failure is handled before interpreter exit."""

    if sys.stdout is None:
        return
    try:
        sys.stdout.flush()
    except (OSError, ValueError) as error:
        raise _StdoutWriteError from error


def _discard(stream: IO[str] | None) -> None:
    """Point a failed standard stream at the null device, as the Python docs advise.

    Output still buffered then cannot fail again in the interpreter's exit
    flush, which would print "Exception ignored" and exit 120. Only the
    interpreter's own stdout and stderr are redirected, never a stream that a
    caller installed.
    """

    if stream is None or (
        stream is not sys.__stdout__ and stream is not sys.__stderr__
    ):
        return
    try:
        descriptor = stream.fileno()
        null = os.open(os.devnull, os.O_WRONLY)
    except (OSError, ValueError):
        return
    if null == descriptor:
        return  # The descriptor was closed and the null device now holds it.
    try:
        os.dup2(null, descriptor)
    except OSError:
        pass
    finally:
        os.close(null)


def _write_stderr(text: str) -> None:
    """Write to stderr without letting it change the command's result.

    A closed stderr (None) drops the text, where print(file=sys.stderr) would
    fall back to stdout and mix notices into the command output. A failing
    stderr is discarded, so the command still finishes, writes its stdout and
    exits with its own code.
    """

    stream = sys.stderr
    if stream is None:
        return
    try:
        stream.write(text)
    except UnicodeEncodeError:
        raise
    except (OSError, ValueError):
        _discard(stream)


def _flush_stderr() -> None:
    """Flush stderr so its failure is handled before interpreter exit."""

    stream = sys.stderr
    if stream is None:
        return
    try:
        stream.flush()
    except (OSError, ValueError):
        _discard(stream)


def _escape_cli_text(value: str) -> str:
    r"""Escape controls for single-line terminal output.

    Tab, LF and CR become \t, \n and \r, the other C0 controls and DEL
    become \xNN, and C1, separator and bidi controls become \uNNNN, so source
    text cannot drive the terminal, break the line or reorder it.
    """

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
    return escape_unicode_controls("".join(escaped))


def _has_errors(diagnostics: tuple[Diagnostic, ...]) -> bool:
    """Return whether a compiler phase produced an error diagnostic."""

    return any(diagnostic.severity is Severity.ERROR for diagnostic in diagnostics)


def _package_version() -> str:
    """Read installed package metadata with a source-tree fallback."""

    try:
        return version("pietto")
    except PackageNotFoundError:
        return _FALLBACK_VERSION
