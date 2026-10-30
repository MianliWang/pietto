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
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, NoReturn

from pietto._output_file import (
    is_owned_by_another_user,
    is_read_only,
    open_replacement,
)
from pietto._project.check import check_project_parse_only
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.module_carrier import ProjectCompilationMode
from pietto._project.path_trust import (
    ProjectFilesystemState,
    ProjectIdentityUnavailableError,
    ProjectOpenedFileChangedError,
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
from pietto._project.project_sql_emission_ast import PREMISE_VALUES
from pietto._project.project_sql_emission_contract import (
    MAX_INPUT_BYTES,
    RELEASES,
    InputError,
    bounded_listing,
    PreparationFailure,
    canonical,
    prepare_project_sql_emission,
)
from pietto._project.project_sql_plan import build_project_sql_plan
from pietto._project.project_sql_plan_literals import ProjectSQLLiteralPolicy
from pietto._project.project_sql_plan_verification import verify_project_sql_plan
from pietto._terminal_text import escape_unicode_controls
from pietto.semantic.analyzer import recursion_limit_diagnostic

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


class _Help(Exception):
    """The --help text, which the CLI writes to stdout like any result."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise _UsageError(message)

    def _print_message(self, message: str, file: object = None) -> None:
        # Only --help prints here; usage errors raise _UsageError instead.
        raise _Help(message)


class _Once(argparse.Action):
    """Store one value and reject a repeated singleton option."""

    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(namespace, self.dest) is not None:
            parser.error(f"argument {option_string}: option given more than once")
        setattr(namespace, self.dest, values)


def _project_root(value: str) -> str:
    """An explicit project root; an empty one would silently be the working
    directory, which project mode never discovers."""

    if not value:
        raise argparse.ArgumentTypeError("Project root must be a non-empty path.")
    return value


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="pietto emit-sql", usage=USAGE[7:], allow_abbrev=False)
    parser.add_argument("path", nargs="?", help="legacy single-file source (exclusive)")
    parser.add_argument(
        "--project",
        action=_Once,
        type=_project_root,
        help="explicit Pietto project root",
    )
    parser.add_argument(
        "--module",
        action=_Once,
        help="project-relative module path, e.g. models/queries.pietto",
    )
    parser.add_argument("--kind", action=_Once, choices=KINDS)
    parser.add_argument("--name", action=_Once, help="declaration name")
    parser.add_argument("--dialect", action=_Once, choices=("postgres", "mysql"))
    parser.add_argument(
        "--emission-contract", action=_Once, help="project-relative contract file"
    )
    parser.add_argument("--literal-policy", action=_Once, choices=tuple(POLICIES))
    parser.add_argument("--format", action=_Once, choices=("text", "json"))
    parser.add_argument(
        "--output",
        action=_Once,
        help="write the JSON artifact (JSON in either --format)",
    )
    return parser


def run_project_emit_sql(arguments: Sequence[str]) -> ProjectEmitResult:
    """Run one project emit-sql invocation, --help included."""

    text = text_presentation_requested(arguments)
    try:
        namespace = _build_parser().parse_args(list(arguments))
    except _UsageError as error:
        return _usage(str(error), text)
    except _Help as help_text:
        return ProjectEmitResult(0, str(help_text).encode("utf-8"), "", False)
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

    def finish(
        outcome: EmissionOutcome,
        protected: Sequence[tuple[Path, tuple[int, int]]] = (),
    ) -> ProjectEmitResult:
        data = serialize_project_sql_emission(outcome)
        document = json.loads(data)
        written = False
        if document["status"] == "VERIFIED" and output is not None:
            errors = _publish(output, data, protected)
            if errors:
                return finish(
                    EmissionOutcome(
                        "INPUT_REJECTED", outcome.diagnostics, cli_errors=errors
                    )
                )
            written = True
        code = EXITS[document["status"]]
        if not text:
            return ProjectEmitResult(code, data, "", written)
        if code == 0:
            return ProjectEmitResult(
                0, _render_verified(document).encode("utf-8"), "", written
            )
        return ProjectEmitResult(
            code, b"", _render_failure(document, namespace.dialect), written
        )

    if output is not None:
        problem = _validate_output(output)
        if problem is not None:
            return finish(EmissionOutcome("INPUT_REJECTED", (), cli_errors=(problem,)))
    return finish(
        *emit_project(
            namespace.project,
            namespace.module,
            namespace.kind,
            namespace.name,
            namespace.dialect,
            namespace.emission_contract,
            policy,
        )
    )


def emit_project(
    project: str | os.PathLike[str],
    module: str,
    kind: str,
    name: str,
    dialect: str,
    contract: str,
    policy: ProjectSQLLiteralPolicy,
) -> tuple[EmissionOutcome, tuple[tuple[Path, tuple[int, int]], ...]]:
    """Run the verified emission pipeline once for one selected owner.

    Returns the outcome and the identities of the configuration, sources and
    contract that an output file must not replace. The CLI and the public
    Python compile entry share it, so the same input reaches the same
    artifact or the same failure document on both.
    """
    diagnostics: tuple[Any, ...] = ()
    protected: list[tuple[Path, tuple[int, int]]] = []
    unnamed: tuple[str, ...] = ()

    def failure(
        status: str,
        found: tuple[Any, ...],
        *errors: InputError,
        blockers: tuple[Any, ...] = (),
    ) -> tuple[EmissionOutcome, tuple[tuple[Path, tuple[int, int]], ...]]:
        # An emission document is UTF-8 text, where a file name that is not
        # UTF-8 has none. A message naming one shows it escaped, as
        # project_path does; a diagnostic or blocker located in such a file
        # is left out, an input error about one has path null, and a
        # project_path error names the file instead.
        found = tuple(
            item
            if all(_utf8(text) for text in (item.message, item.suggestion or ""))
            else replace(
                item,
                message=_escaped(item.message),
                suggestion=None
                if item.suggestion is None
                else _escaped(item.suggestion),
            )
            for item in found
        )
        errors = tuple(
            error
            if _utf8(error.message)
            else replace(error, message=_escaped(error.message))
            for error in errors
        )
        places = (
            *(item.location.path for item in found),
            *(
                getattr(location, "path", None)
                for blocker in blockers
                for location in (blocker.location, *blocker.related)
            ),
            *(error.path for error in errors),
        )
        located = next(
            (path for path in places if path is not None and not _utf8(path)), None
        )
        if located is not None:
            status = "INPUT_REJECTED"
            found = tuple(
                item
                for item in found
                if item.location.path is None or _utf8(item.location.path)
            )
            blockers = tuple(
                blocker
                for blocker in blockers
                if all(
                    getattr(location, "path", None) is None or _utf8(location.path)
                    for location in (blocker.location, *blocker.related)
                )
            )
            errors = tuple(
                dict.fromkeys(
                    (
                        *(
                            error
                            if error.path is None or _utf8(error.path)
                            else replace(error, path=None)
                            for error in errors
                        ),
                        _unnamed_path(located),
                    )
                )
            )
        return EmissionOutcome(status, found, blockers=blockers, cli_errors=errors), ()

    def rejected(
        *errors: InputError,
    ) -> tuple[EmissionOutcome, tuple[tuple[Path, tuple[int, int]], ...]]:
        return failure("INPUT_REJECTED", diagnostics, *errors)

    try:
        parsed = check_project_parse_only(Path(project))
    except (OSError, ValueError):
        return rejected(InputError("project_root", "Project root could not be pinned."))
    unnamed = tuple(item.path for item in parsed.inputs if not _utf8(item.path))
    diagnostics = parsed.diagnostics
    if parsed.errors:
        return rejected(
            *(InputError(e.kind.value, e.message, e.path) for e in parsed.errors)
        )
    if parsed.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES:
        return rejected(
            InputError(
                "config_schema",
                "emit-sql --project needs schema_version = 2 (explicit modules);"
                " this project uses schema_version 1. Set schema_version = 2 and"
                " declare the names a file uses from another file with import"
                " and export.",
                "pietto.toml",
            )
        )
    pinned_root = parsed.pinned_root
    index = parsed.selected_input_index
    if pinned_root is None or index is None or parsed.config_path is None:
        return rejected(
            InputError("project_resource", "Project trust facts are unavailable.")
        )
    read = _read_contract(pinned_root, contract)
    if isinstance(read, InputError):
        return rejected(read)
    contract_bytes, contract_path, contract_state = read
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
        return failure("BLOCKED", diagnostics)
    # Exhausting the recursion limit is PIE-S2006, as in single-file analysis:
    # over the module that nests deepest while the whole project is completed
    # and built, then over the selected owner's module, the only one planning
    # and emission walk.
    scripts = tuple(parsed_input.script for parsed_input in parsed.parsed_inputs)
    try:
        completed = build_project_completed_semantic_result(
            build_empty_project_semantic_result(parsed)
        )
        diagnostics = completed.diagnostics
        if (
            type(completed) is not ProjectConcreteCompletedSemanticResult
            or not completed.ok
        ):
            return failure("BLOCKED", diagnostics)
        try:
            ir = build_project_query_block_ir(completed)
            bundle = build_project_query_block_ir_analysis_bundle(
                verify_project_query_block_ir(ir)
            )
            modules = completed.semantic_result.modules
            # The same three public owner coordinates the artifact publishes; a
            # relation let is a block of its declaration, never a selectable owner.
            selectable = [owner for owner in ir.owners if not owner.block_local]
            owners = [
                owner
                for owner in selectable
                if modules[owner.module_position].path == module
                and owner.identity.declaration_kind.value == kind
                and owner.definition.name == name
            ]
            if not owners:
                return rejected(
                    InputError(
                        "emission_selector",
                        _absent_owner(modules, module, kind, selectable),
                    )
                )
            if len(owners) != 1:
                return rejected(
                    InputError(
                        "emission_selector", "Selected owner is absent or ambiguous."
                    )
                )
            scripts = tuple(
                parsed_input.script
                for parsed_input in parsed.parsed_inputs
                if parsed_input.path == module
            )
            plan = build_project_sql_plan(
                completed, bundle, owners[0], literal_policy=policy
            )
            checked = verify_project_sql_plan(
                plan, completed, bundle, owners[0], literal_policy=policy
            )
        except (TypeError, ValueError):
            return rejected(
                InputError(
                    "emission_selector", "Project planning roots are unavailable."
                )
            )
        prepared = prepare_project_sql_emission(checked, contract_bytes)
        if type(prepared) is PreparationFailure:
            return failure(
                "INPUT_REJECTED" if prepared.errors else "BLOCKED",
                prepared.diagnostics,
                *prepared.errors,
                blockers=prepared.blockers,
            )
        if prepared.family != dialect:
            return rejected(
                InputError(
                    "emission_contract_schema",
                    "Emission contract target family conflicts with --dialect.",
                    "target/family",
                )
            )
        try:
            outcome = realize_project_sql(prepared)
        except UnicodeEncodeError:
            # In place of SQL: the artifact, measured last, names every
            # selected source in request.sources.
            if not unnamed:
                raise
            return rejected(_unnamed_path(unnamed[0]))
        if outcome.status != "VERIFIED":
            return failure(
                outcome.status,
                outcome.diagnostics,
                *outcome.cli_errors,
                blockers=outcome.blockers,
            )
        return outcome, tuple(protected)
    except RecursionError:
        return failure("BLOCKED", (recursion_limit_diagnostic(*scripts),))


def _utf8(text: str) -> bool:
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _escaped(text: str) -> str:
    """Text whose characters that UTF-8 cannot hold, such as the \\udcff of
    a file name byte, are shown as escapes."""

    return text.encode("utf-8", "backslashreplace").decode("utf-8")


def _unnamed_path(path: str) -> InputError:
    return InputError(
        "project_path",
        "Project source path must be valid UTF-8 to emit SQL:"
        f" {json.dumps(path)}; rename it.",
    )


def _absent_owner(modules, module: str, kind: str, owners) -> str:
    """Why --module, --kind and --name select nothing, naming only project
    module paths and declarations, never the raw --module argument."""

    paths = [current.path for current in modules]
    if module not in paths:
        message = (
            "No project module matches --module; project modules:"
            f" {bounded_listing(paths)}."
        )
        if "\\" in module:
            message += " --module uses / as the separator."
        return message
    names = [
        owner.definition.name
        for owner in owners
        if modules[owner.module_position].path == module
        and owner.identity.declaration_kind.value == kind
    ]
    plural = {"table": "tables", "query": "queries"}[kind]
    return (
        f"{module} declares no {kind} named by --name; its {plural}:"
        f" {bounded_listing(names)}."
    )


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
    # An error document is UTF-8 text, where a path that is not UTF-8 has none.
    logical = "/".join(parts) if _utf8(argument) else None
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
    except ProjectOpenedFileChangedError:
        return InputError(
            "emission_contract_read",
            "Emission contract file changed while being read.",
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
    """Reject unsuitable destinations before any compilation or mutation.

    Only a destination shown to be unsuitable is rejected. One that cannot be
    inspected is left to the write, which cannot reach it either and reports
    output_write.
    """

    try:
        if output.is_symlink():
            return InputError("output_path", "Output path must not be a symbolic link.")
        if output.exists() and not output.is_file():
            return InputError("output_path", "Output path must be a regular file.")
        try:
            parent_mode = os.stat(output.parent).st_mode
        except (FileNotFoundError, NotADirectoryError):
            return InputError("output_path", "Output directory does not exist.")
        if not stat.S_ISDIR(parent_mode):
            return InputError("output_path", "Output directory does not exist.")
    except OSError:
        # A parent that cannot be inspected (a symbolic-link loop, say) is not
        # shown to be unsuitable; the write reports output_write.
        pass
    return None


def _publish(
    output: Path, data: bytes, protected: Sequence[tuple[Path, tuple[int, int]]]
) -> tuple[InputError, ...]:
    """Atomically replace one regular file with the complete artifact bytes."""

    problem = _validate_output(output)
    if problem is not None:
        return (problem,)
    try:
        resolved: Path | None = output.resolve(strict=False)
    except (OSError, RuntimeError):
        resolved = None  # Python 3.12 reports a symbolic-link loop as RuntimeError.
    try:
        state = os.stat(output)
        identity: tuple[int, int] | None = (state.st_dev, state.st_ino)
    except OSError:
        identity = None
    for path, protected_identity in protected:
        if (
            resolved is not None and resolved == path.resolve(strict=False)
        ) or identity == protected_identity:
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
        # A destination whose state cannot be read is a failed write too.
        if is_read_only(output):
            return (InputError("output_write", "Output file is read-only."),)
        if is_owned_by_another_user(output):
            return (InputError("output_write", "Output file belongs to another user."),)
        handle, temporary = open_replacement(output)
        with handle:
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
    """Escape controls for single-line terminal presentation.

    C0 controls and DEL become \\xNN; C1, separator and bidi controls become
    \\uNNNN, as in every CLI text output.
    """

    return escape_unicode_controls(
        "".join(
            character
            if ord(character) >= 0x20 and character != "\x7f"
            else f"\\x{ord(character):02x}"
            for character in value
        )
    )


def _diagnostic_line(diagnostic: dict[str, Any]) -> str:
    location = diagnostic["location"]
    return (
        f"{_escape(str(location['path']))}:{location['line']}:{location['column']}"
        f" {_escape(diagnostic['code'])} {_escape(diagnostic['severity'])}:"
        f" {_escape(diagnostic['message'])}"
    )


def _record(value: object) -> str:
    """One canonical JSON record as single-line terminal text.

    JSON already escapes C0 controls; DEL and the C1, separator and bidi
    controls it leaves raw become \\uNNNN too, so the line still decodes to
    the same value.
    """

    text = canonical(value).decode("utf-8")
    return escape_unicode_controls(text).replace("\x7f", "\\u007f")


def _records(label: str, records: list[Any]) -> list[str]:
    return [f"{label} ({len(records)}):"] + [
        "  " + _record(record) for record in records
    ]


def _render_verified(document: dict[str, Any]) -> str:
    """Present the already-serialized VERIFIED document as labeled UTF-8 text."""

    target, request = document["target"], document["request"]
    owner = request["owner"]
    lines = [
        f"{document['format']} {document['status']}",
        f"target: {_escape(target['family'])} {_escape(target['release'])}",
        *_records("environment", target["environment"]),
        f"owner: {_escape(owner['module'])} {_escape(owner['kind'])}"
        f" {_escape(owner['name'])}",
        f"literal_policy: {request['literal_policy']}",
        *_records("sources", request["sources"]),
        "contract: " + _record(request["contract"]),
        "sql:",
        document["sql"],
        "end sql",
        *_records("fixed_values", document["fixed_values"]),
        *(
            _records("parameters", document["parameters"])
            if "parameters" in document
            else ()
        ),
        *_records("parameter_uses", document["parameter_uses"]),
        *(
            _records("binding_obligations", document["binding_obligations"])
            if "binding_obligations" in document
            else ()
        ),
        *_records("columns", document["columns"]),
        *_records("requirements", document["requirements"]),
        *_records("ranges", document["ranges"]),
        f"diagnostics ({len(document['diagnostics'])}):",
        *("  " + _diagnostic_line(d) for d in document["diagnostics"]),
    ]
    return "\n".join(lines) + "\n"


def _render_failure(document: dict[str, Any], family: str | None = None) -> str:
    """Present a failure document as labeled text for stderr; with the target
    family, a blocker an author can resolve in the contract or the source is
    followed by a hint naming the reviewed value or the remedy."""

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
        related = [
            f"{_escape(str(r['path']))}:{r['line']}:{r['column']}"
            for r in blocker["related"]
            if r is not None and r["path"] is not None
        ]
        if family is not None and related:
            lines.append(f"  related: {', '.join(related)}")
        hint = None if family is None else _blocker_hint(subject["detail"], family)
        if hint is not None:
            lines.append(f"  hint: {_escape(hint)}")
    lines.extend(_diagnostic_line(d) for d in document["diagnostics"])
    return "\n".join(lines) + "\n"


def _blocker_hint(detail: str, family: str) -> str | None:
    """The remedy of one blocker detail, for text output only."""

    for key, values in PREMISE_VALUES.items():
        premise = _record({"key": key, "scope": "statement", "value": values[family]})
        if detail == f"{key}_declaration_missing":
            return f'add {premise} to "environment"'
        if detail in {f"{key}_declaration_mismatch", f"{key}_mismatch"}:
            return f"the reviewed {family} value is {premise}"
    if detail in {
        "row_domain_matches_declaration_required",
        "read_only_object_declaration_required",
    }:
        key = detail.removesuffix("_declaration_required")
        premise = _record({"key": key, "scope": "source", "value": True})
        return f'add {premise} to the source\'s "premises"'
    if detail == "complete_ordered_source_schema_required":
        return (
            'map every field of the source\'s shape once in "fields", in shape'
            " order; related lists the fields left out or out of order"
        )
    if detail == "target_release_not_reviewed":
        return f'the reviewed {family} release is "{RELEASES[family]}"'
    if detail == "order":
        return (
            "without GROUP BY, a key must be an input field, a restated selected"
            " expression or a selected let name, of a type that orders"
        )
    if detail in {
        "arithmetic_outside_physical_range",
        "unary_result_outside_physical_range",
        "abs_result_outside_physical_range",
    }:
        return (
            "an Int field ranges over its whole storage type; its declared"
            " int_range does not narrow that, so the result must fit the"
            " storage type"
        )
    return None
