"""Private installed Project emit-SQL command over the verified emission pipeline.

The coordinator owns exact argument validation, explicit project and contract
input, owner selection, the call into the existing plan/emission/serialization
owners, atomic artifact-file publication and the JSON/text presentation bytes.
It never builds a VERIFIED document itself and never writes process streams;
``pietto.cli`` writes the returned bytes.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

from pietto._project.check import check_project_parse_only
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.module_carrier import ProjectCompilationMode
from pietto._project.path_trust import (
    ProjectFilesystemState,
    ProjectIdentityUnavailableError,
    ProjectPinnedRoot,
    ProjectRootChangedError,
    _fstat_state,
    _open_pinned_file,
    _verify_pinned_root,
)
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
    build_project_completed_semantic_result,
)
from pietto._project.project_query_block_ir import build_project_query_block_ir
from pietto._project.project_query_block_ir_verification import (
    build_project_query_block_ir_analysis_bundle,
    verify_project_query_block_ir,
)
from pietto._project.project_sql_emission import (
    EmissionOutcome,
    realize_project_sql,
    serialize_project_sql_emission,
)
from pietto._project.project_sql_emission_contract import (
    MAX_INPUT_BYTES,
    InputError,
    PreparationFailure,
    canonical,
    prepare_project_sql_emission,
)
from pietto._project.project_sql_plan import build_project_sql_plan
from pietto._project.project_sql_plan_literals import ProjectSQLLiteralPolicy
from pietto._project.project_sql_plan_verification import verify_project_sql_plan

__all__: tuple[str, ...] = ()

USAGE = (
    "usage: pietto emit-sql --project PATH --module LOGICAL_MODULE"
    " --kind {table,query}\n"
    "                       --name NAME --dialect {postgres,mysql}"
    " --emission-contract FILE\n"
    "                       [--literal-policy {preserve,bind-safe}]"
    " [--format {text,json}] [--output FILE]"
)
POLICIES = {
    "preserve": ProjectSQLLiteralPolicy.PRESERVE_LITERALS,
    "bind-safe": ProjectSQLLiteralPolicy.BIND_SAFE_LITERALS,
}
KINDS = ("table", "query")
EXITS = {"VERIFIED": 0, "BLOCKED": 1, "INPUT_REJECTED": 2}


def project_mode_requested(arguments: Sequence[str]) -> bool:
    """Return whether an emit-sql argv explicitly selects project mode."""

    for argument in arguments:
        if argument == "--":
            return False
        if argument == "--project" or argument.startswith("--project="):
            return True
    return False


def text_presentation_requested(arguments: Sequence[str]) -> bool:
    """Return whether argv unambiguously asks for text before parsing succeeds."""

    formats: list[str] = []
    tokens = list(arguments)
    for index, argument in enumerate(tokens):
        if argument == "--":
            break
        if argument == "--format" and index + 1 < len(tokens):
            formats.append(tokens[index + 1])
        elif argument.startswith("--format="):
            formats.append(argument[len("--format=") :])
    return formats == ["text"]


@dataclass(frozen=True, slots=True)
class ProjectEmitResult:
    """Complete process outcome: exit code, stream bytes and file state."""

    exit_code: int
    stdout: bytes
    stderr: str
    written: bool


class _UsageError(Exception):
    """A project-mode argument error rendered through the new failure family."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise _UsageError(message)


class _Once(argparse.Action):
    """Store one value and reject a repeated singleton option."""

    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(namespace, self.dest) is not None:
            parser.error(f"argument {option_string}: option given more than once")
        setattr(namespace, self.dest, values)


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="pietto emit-sql", usage=USAGE[7:], allow_abbrev=False)
    parser.add_argument("path", nargs="?", help="legacy single-file source (exclusive)")
    parser.add_argument("--project", action=_Once, help="explicit Pietto project root")
    parser.add_argument("--module", action=_Once, help="logical module path")
    parser.add_argument("--kind", action=_Once, choices=KINDS)
    parser.add_argument("--name", action=_Once, help="declaration name")
    parser.add_argument("--dialect", action=_Once, choices=("postgres", "mysql"))
    parser.add_argument(
        "--emission-contract", action=_Once, help="project-relative contract file"
    )
    parser.add_argument("--literal-policy", action=_Once, choices=tuple(POLICIES))
    parser.add_argument("--format", action=_Once, choices=("text", "json"))
    parser.add_argument("--output", action=_Once, help="artifact file destination")
    return parser


def run_project_emit_sql(arguments: Sequence[str]) -> ProjectEmitResult | int:
    """Run one project emit-sql invocation; an int is an argparse help exit."""

    text = text_presentation_requested(arguments)
    try:
        namespace = _build_parser().parse_args(list(arguments))
    except _UsageError as error:
        return _usage(str(error), text)
    except SystemExit as error:
        return error.code if type(error.code) is int else 0 if error.code is None else 1
    if namespace.path is not None:
        return _usage("path and --project are mutually exclusive", text)
    missing = [
        option
        for option in (
            "--module",
            "--kind",
            "--name",
            "--dialect",
            "--emission-contract",
        )
        if getattr(namespace, option[2:].replace("-", "_")) is None
    ]
    if missing:
        return _usage(
            "the following arguments are required: " + ", ".join(missing), text
        )
    text = namespace.format == "text"
    policy = POLICIES[namespace.literal_policy or "preserve"]
    output = None if namespace.output is None else Path(namespace.output)
    diagnostics: tuple[Any, ...] = ()
    protected: list[tuple[Path, tuple[int, int]]] = []
    written = False

    def finish(outcome: EmissionOutcome) -> ProjectEmitResult:
        nonlocal written
        data = serialize_project_sql_emission(outcome)
        document = json.loads(data)
        if document["status"] == "VERIFIED" and output is not None:
            errors = _publish(output, data, protected)
            if errors:
                return finish(
                    EmissionOutcome("INPUT_REJECTED", diagnostics, cli_errors=errors)
                )
            written = True
        code = EXITS[document["status"]]
        if not text:
            return ProjectEmitResult(code, data, "", written)
        if code == 0:
            return ProjectEmitResult(
                0, _render_verified(document).encode("utf-8"), "", written
            )
        return ProjectEmitResult(code, b"", _render_failure(document), written)

    def rejected(*errors: InputError) -> ProjectEmitResult:
        return finish(EmissionOutcome("INPUT_REJECTED", diagnostics, cli_errors=errors))

    if output is not None:
        problem = _validate_output(output)
        if problem is not None:
            return rejected(problem)
    try:
        parsed = check_project_parse_only(Path(namespace.project))
    except (OSError, ValueError):
        return rejected(InputError("project_root", "Project root could not be pinned."))
    diagnostics = parsed.diagnostics
    if parsed.errors:
        return rejected(
            *(InputError(e.kind.value, e.message, e.path) for e in parsed.errors)
        )
    if parsed.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES:
        return rejected(
            InputError(
                "config_schema",
                "Project emit-sql requires the explicit-module project mode.",
                "pietto.toml",
            )
        )
    pinned_root = parsed.pinned_root
    index = parsed.selected_input_index
    if pinned_root is None or index is None or parsed.config_path is None:
        return rejected(
            InputError("project_resource", "Project trust facts are unavailable.")
        )
    contract = _read_contract(pinned_root, namespace.emission_contract)
    if isinstance(contract, InputError):
        return rejected(contract)
    contract_bytes, contract_path, contract_state = contract
    try:
        config_stat = os.stat(pinned_root.canonical_path / parsed.config_path.path)
    except OSError:
        return rejected(
            InputError(
                "config_read",
                "Project configuration identity is unavailable.",
                parsed.config_path.path,
            )
        )
    protected.append(
        (
            pinned_root.canonical_path / parsed.config_path.path,
            (config_stat.st_dev, config_stat.st_ino),
        )
    )
    protected.extend(
        (
            entry.canonical_path,
            (
                entry.final_target_state.physical_identity.device,
                entry.final_target_state.physical_identity.inode,
            ),
        )
        for entry in index.entries
    )
    protected.append(
        (
            contract_path,
            (
                contract_state.physical_identity.device,
                contract_state.physical_identity.inode,
            ),
        )
    )
    if not parsed.ok:
        return finish(EmissionOutcome("BLOCKED", diagnostics))
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(parsed)
    )
    diagnostics = completed.diagnostics
    if (
        type(completed) is not ProjectConcreteCompletedSemanticResult
        or not completed.ok
    ):
        return finish(EmissionOutcome("BLOCKED", diagnostics))
    try:
        ir = build_project_query_block_ir(completed)
        bundle = build_project_query_block_ir_analysis_bundle(
            verify_project_query_block_ir(ir)
        )
        modules = completed.semantic_result.modules
        # The same three public owner coordinates the artifact publishes.
        owners = [
            owner
            for owner in ir.owners
            if modules[owner.module_position].path == namespace.module
            and owner.identity.declaration_kind.value == namespace.kind
            and owner.definition.name == namespace.name
        ]
        if len(owners) != 1:
            return rejected(
                InputError(
                    "emission_selector", "Selected owner is absent or ambiguous."
                )
            )
        plan = build_project_sql_plan(
            completed, bundle, owners[0], literal_policy=policy
        )
        checked = verify_project_sql_plan(
            plan, completed, bundle, owners[0], literal_policy=policy
        )
    except (TypeError, ValueError):
        return rejected(
            InputError("emission_selector", "Project planning roots are unavailable.")
        )
    prepared = prepare_project_sql_emission(checked, contract_bytes)
    if type(prepared) is PreparationFailure:
        return finish(
            EmissionOutcome(
                "INPUT_REJECTED" if prepared.errors else "BLOCKED",
                prepared.diagnostics,
                blockers=prepared.blockers,
                cli_errors=prepared.errors,
            )
        )
    if prepared.family != namespace.dialect:
        return rejected(
            InputError(
                "emission_contract_schema",
                "Emission contract target family conflicts with --dialect.",
                "target/family",
            )
        )
    return finish(realize_project_sql(prepared))


def _usage(message: str, text: bool) -> ProjectEmitResult:
    if text:
        return ProjectEmitResult(
            2, b"", f"{USAGE}\npietto emit-sql: error: {_escape(message)}\n", False
        )
    outcome = EmissionOutcome(
        "INPUT_REJECTED", (), cli_errors=(InputError("usage", message),)
    )
    return ProjectEmitResult(2, serialize_project_sql_emission(outcome), "", False)


def _read_contract(
    pinned_root: ProjectPinnedRoot, argument: str
) -> tuple[bytes, Path, ProjectFilesystemState] | InputError:
    """Read the accepted contract bytes once through the pinned-root open contract."""

    parts = Path(argument).parts
    if (
        Path(argument).is_absolute()
        or not parts
        or any(part in {"..", "."} for part in parts)
        or "/".join(parts) != argument.replace(os.sep, "/")
    ):
        return InputError(
            "emission_contract_read",
            "Emission contract path must be a normalized project-relative path.",
        )
    logical = "/".join(parts)
    path = pinned_root.canonical_path.joinpath(*parts)
    descriptor = -1
    try:
        descriptor = _open_pinned_file(pinned_root, path)
        opened = _fstat_state(descriptor)
        if not stat.S_ISREG(opened.file_type):
            return InputError(
                "emission_contract_read",
                "Emission contract path must be a regular file.",
                logical,
            )
        data = b""
        while len(data) <= MAX_INPUT_BYTES:
            chunk = os.read(descriptor, MAX_INPUT_BYTES + 1 - len(data))
            if not chunk:
                break
            data += chunk
        final = _fstat_state(descriptor)
    except ProjectRootChangedError:
        return InputError(
            "emission_contract_read",
            "Project root identity changed while reading the emission contract.",
            logical,
        )
    except ProjectIdentityUnavailableError:
        return InputError(
            "emission_contract_read",
            "Project filesystem identity is unavailable.",
            logical,
        )
    except (OSError, ValueError):
        return InputError(
            "emission_contract_read",
            "Emission contract file could not be opened inside the project root.",
            logical,
        )
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(data) > MAX_INPUT_BYTES:
        return InputError(
            "emission_contract_read",
            f"Emission contract exceeds the maximum supported size of {MAX_INPUT_BYTES} bytes.",
            logical,
        )
    if final != opened:
        return InputError(
            "emission_contract_read",
            "Emission contract file changed while being read.",
            logical,
        )
    try:
        _verify_pinned_root(pinned_root)
    except OSError:
        return InputError(
            "emission_contract_read",
            "Project root identity changed while reading the emission contract.",
            logical,
        )
    return data, path, opened


def _validate_output(output: Path) -> InputError | None:
    """Reject unsuitable destinations before any compilation or mutation."""

    if output.is_symlink():
        return InputError("output_path", "Output path must not be a symbolic link.")
    if output.exists() and not output.is_file():
        return InputError("output_path", "Output path must be a regular file.")
    if not output.parent.is_dir():
        return InputError("output_path", "Output directory does not exist.")
    return None


def _publish(
    output: Path, data: bytes, protected: Sequence[tuple[Path, tuple[int, int]]]
) -> tuple[InputError, ...]:
    """Atomically replace one regular file with the complete artifact bytes."""

    problem = _validate_output(output)
    if problem is not None:
        return (problem,)
    resolved = output.resolve(strict=False)
    try:
        state = os.stat(output)
        identity: tuple[int, int] | None = (state.st_dev, state.st_ino)
    except OSError:
        identity = None
    for path, protected_identity in protected:
        if resolved == path.resolve(strict=False) or identity == protected_identity:
            return (
                InputError(
                    "output_path",
                    "Output path must differ from the project configuration,"
                    " sources and emission contract.",
                ),
            )
    errors: list[InputError] = []
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=output.parent,
            prefix=f".{output.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(data)
        os.replace(temporary, output)
        temporary = None
    except OSError:
        errors.append(InputError("output_write", "Output file could not be written."))
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                errors.append(
                    InputError(
                        "output_write", "Temporary output file could not be removed."
                    )
                )
    return tuple(errors)


def _escape(value: str) -> str:
    """Escape C0 controls and DEL for single-line terminal presentation."""

    return "".join(
        character
        if ord(character) >= 0x20 and character != "\x7f"
        else f"\\x{ord(character):02x}"
        for character in value
    )


def _diagnostic_line(diagnostic: dict[str, Any]) -> str:
    location = diagnostic["location"]
    return (
        f"{_escape(str(location['path']))}:{location['line']}:{location['column']}"
        f" {_escape(diagnostic['code'])} {_escape(diagnostic['severity'])}:"
        f" {_escape(diagnostic['message'])}"
    )


def _records(label: str, records: list[Any]) -> list[str]:
    return [f"{label} ({len(records)}):"] + [
        "  " + canonical(record).decode("utf-8") for record in records
    ]


def _render_verified(document: dict[str, Any]) -> str:
    """Present the already-serialized VERIFIED document as labeled UTF-8 text."""

    target, request = document["target"], document["request"]
    owner = request["owner"]
    lines = [
        f"{document['format']} {document['status']}",
        f"target: {target['family']} {target['release']}",
        *_records("environment", target["environment"]),
        f"owner: {owner['module']} {owner['kind']} {owner['name']}",
        f"literal_policy: {request['literal_policy']}",
        *_records("sources", request["sources"]),
        "contract: " + canonical(request["contract"]).decode("utf-8"),
        "sql:",
        document["sql"],
        "end sql",
        *_records("fixed_values", document["fixed_values"]),
        *_records("parameter_uses", document["parameter_uses"]),
        *_records("columns", document["columns"]),
        *_records("requirements", document["requirements"]),
        *_records("ranges", document["ranges"]),
        f"diagnostics ({len(document['diagnostics'])}):",
        *("  " + _diagnostic_line(d) for d in document["diagnostics"]),
    ]
    return "\n".join(lines) + "\n"


def _render_failure(document: dict[str, Any]) -> str:
    """Present a failure document as labeled text for stderr."""

    lines = [f"{document['format']} {document['status']}"]
    for error in document["cli_errors"]:
        line = f"error {error['kind']}: {_escape(error['message'])}"
        if error["path"] is not None:
            line += f" (path: {_escape(error['path'])})"
        lines.append(line)
    for blocker in document["blockers"]:
        subject = blocker["subject"]
        line = f"blocker {blocker['code']} {blocker['reason']}: {_escape(subject['detail'])}"
        location = blocker["location"]
        if location is not None and location["path"] is not None:
            line += f" ({_escape(str(location['path']))}:{location['line']}:{location['column']})"
        lines.append(line)
    lines.extend(_diagnostic_line(d) for d in document["diagnostics"])
    return "\n".join(lines) + "\n"
