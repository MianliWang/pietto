"""Private project check orchestration."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, cast

import pietto.parser_api as parser_api
from pietto._builtin_shadows import imported_nodes
from pietto._editor_facts import (
    EditorFacts,
    authored_declarations,
    editor_declaration,
    editor_use,
)
from pietto.ast_nodes import (
    Definition,
    ExportStatement,
    FunctionDef,
    ImportStatement,
    ModuleDeclarationKind,
    Script,
    Span,
)
from pietto._flat_relational_admission import legacy_flat_refused
from pietto._syntax_admission import (
    source_order,
    unadmitted_syntax_diagnostics,
)
from pietto._project.query_parameters import (
    query_parameter_diagnostics,
    query_parameter_unbound_naming_diagnostics,
)
from pietto._project.relation_captures import capture_diagnostics
from pietto._project.config import load_project_config
from pietto._project.module_carrier import (
    ProjectCompilationMode,
    _build_project_logical_modules,
)
from pietto._project.model import (
    ProjectConfigPath,
    ProjectDiscoveryError,
    ProjectDiscoveryErrorKind,
    ProjectDiscoveryResult,
    ProjectInput,
    ProjectParsedInput,
    ProjectParseCheckResult,
    ProjectRoot,
    ProjectSemanticResult,
)
from pietto._project.path_trust import (
    ProjectPinnedRoot,
    _open_pinned_directory,
    _supports_directory_relative_open,
)
from pietto._project.selected_input_index import ProjectSelectedInputEntry
from pietto._project.source_selection import select_project_sources
from pietto._project.trusted_source import (
    ProjectOverlaySource,
    ProjectSource,
    ProjectTrustedSourceError,
    ProjectTrustedSourceFailure,
    ProjectTrustedSourceSnapshot,
    _load_trusted_source,
)
from pietto.errors import (
    PIPE_HINT,
    Diagnostic,
    Severity,
    SourceLocation,
    with_unjoined_pipe_hints,
)
from pietto.semantic.analyzer import (
    analyze_project_namespace,
    module_statement_diagnostics,
    name_uncallable_calls,
    recursion_limit_diagnostic,
)
from pietto.semantic.constructor_calls import builtin_shadows
from pietto.semantic.existence_generators import without_any
from pietto.semantic.inline_functions import (
    DefTemplate,
    drop_repeated_operand_diagnostics,
    inline_functions,
    reserved_import_name,
)
from pietto.semantic.modern_inputs import normalize_query_names

if TYPE_CHECKING:
    from pietto._project.json_v2 import RelatedLocations
    from pietto._project.module_bindings import ProjectModuleBindingEnvironmentSet
    from pietto._project.module_carrier import ProjectLogicalModule
    from pietto._project.module_exports import ProjectModuleExportSurfaceSet
    from pietto._project.module_graph import (
        ProjectModuleDiagnosticSet,
        ProjectModuleGraph,
    )
    from pietto._project.selected_input_index import ProjectSelectedInputIndex
    from pietto.semantic.existence_generators import AnyUseInfo, AnyValueTrace

_PROJECT_ROOT_PATH = "."
_PROJECT_CONFIG_PATH = "pietto.toml"
_PROJECT_SOURCE_UTF8_BYTES = 1_048_576
_PARSED_STATUS = "parsed"
_ERROR_STATUS = "error"


# The most passes partial analysis runs: one for each stop that can hide a
# later one (a read, parse or admission error; a header or def import error;
# a naming error; an error of the checks after naming) and one that completes.
_PARTIAL_PASSES = 5


@dataclass(frozen=True, slots=True)
class ProjectDiagnosticsReport:
    """The diagnostics of one project check, for an editor: the discovery
    errors, the selected paths in input order, the diagnostics grouped by
    path in that order (in CLI order within a path, pathless ones last) with
    their related locations, the text each path was
    checked from, and the location and message of each module that was not
    checked. It holds no semantic result and no source carrier."""

    errors: tuple[ProjectDiscoveryError, ...]
    paths: tuple[str, ...]
    diagnostics: tuple[Diagnostic, ...]
    related_locations: RelatedLocations
    texts: Mapping[str, str]
    not_checked: tuple[tuple[SourceLocation, str], ...]


@dataclass(frozen=True, slots=True)
class ProjectEditorDiagnostics:
    """Private diagnostics-plus-facts result for the editor's one-pass check."""

    report: ProjectDiagnosticsReport
    facts: Mapping[str, EditorFacts]

    def __post_init__(self) -> None:
        object.__setattr__(self, "facts", MappingProxyType(dict(self.facts)))


def check_project_diagnostics(
    root: str | Path, *, overlays: Mapping[str, str]
) -> ProjectDiagnosticsReport:
    """Check a project for an editor, past the modules that stop the check.

    Each selected path in `overlays` (project-relative path to editor text)
    is read from the overlay instead of the disk.
    A pass is the check that `check --project --format json` reports. When an
    explicit-module pass stops, the modules it fails (`_failed_modules`) and
    every module that imports one of them, directly or through other modules,
    are left out, and the other modules are checked again, in at most
    `_PARTIAL_PASSES` passes. Each module reports the diagnostics of the last
    pass that checked it, so one that no pass failed or left out reports
    what the CLI reports with the left-out modules in `[sources].exclude`.
    A left-out module that no pass failed, and a failed one without an error
    of its own (a member of an import cycle), reports one message instead, at
    its first import of a left-out module, naming each failed module with an
    error of its own that it imports, directly or through other modules. The
    CLI never calls this."""

    report, _ = _check_project_editor_diagnostics(
        root, overlays=overlays, editor_facts=False
    )
    return report


def check_project_editor_diagnostics(
    root: str | Path, *, overlays: Mapping[str, str]
) -> ProjectEditorDiagnostics:
    """Run the editor's project check once and return detached successful facts."""

    report, facts = _check_project_editor_diagnostics(
        root, overlays=overlays, editor_facts=True
    )
    return ProjectEditorDiagnostics(report=report, facts=facts)


def _check_project_editor_diagnostics(
    root: str | Path, *, overlays: Mapping[str, str], editor_facts: bool
) -> tuple[ProjectDiagnosticsReport, Mapping[str, EditorFacts]]:
    """Shared check path; only this private caller retains pure editor facts."""

    passes = [_check_pass(root, frozenset(), overlays, editor_facts=editor_facts)]
    paths = tuple(item.path for item in passes[0][0].inputs)
    imports: dict[str, tuple[ImportStatement, ...]] = {}
    failed: set[str] = set()
    blocked: set[str] = set()
    while True:
        parse, _, _, stopped, _ = passes[-1]
        imports.update(
            (
                parsed.path,
                tuple(
                    statement
                    for statement in parsed.script.module_statements
                    if type(statement) is ImportStatement
                ),
            )
            for parsed in parse.parsed_inputs
        )
        if not stopped or len(passes) == _PARTIAL_PASSES:
            break
        failed |= stopped
        blocked = {
            path
            for path in paths
            if path not in failed and _imported(imports, path) & failed
        }
        if failed | blocked >= set(paths):
            break
        passes.append(
            _check_pass(
                root, frozenset(failed | blocked), overlays, editor_facts=editor_facts
            )
        )
    checked = {
        item.path: position
        for position, (parse, _, _, _, _) in enumerate(passes)
        for item in parse.inputs
    }
    errors: list[ProjectDiscoveryError] = []
    diagnostics: list[Diagnostic] = []
    related: dict[Diagnostic, tuple[SourceLocation, ...]] = {}
    texts: dict[str, str] = {}
    not_checked: list[tuple[SourceLocation, str]] = []
    facts_by_path: dict[str, EditorFacts] = {}
    own_errors = {
        path: [error for error in passes[checked[path]][0].errors if error.path == path]
        for path in paths
    }
    own = {
        path: tuple(
            item for item in passes[checked[path]][1] if item.location.path == path
        )
        for path in paths
    }
    # Every import cycle has a member with the cycle error, so each module
    # not checked reaches at least one failed module with an error.
    erring = {path for path in failed if own_errors[path] or _has_errors(own[path])}
    for path in paths:
        parse, _, found_related, _, pass_facts = passes[checked[path]]
        texts.update(
            (source.path, source.source_text)
            for source in parse.trusted_source_snapshots
            if source.path == path
        )
        if path in blocked or path in failed - erring:
            not_checked.append(
                _not_checked(
                    path,
                    imports[path],
                    failed | blocked,
                    sorted(_imported(imports, path) & erring),
                )
            )
        if path not in blocked:
            errors.extend(own_errors[path])
            diagnostics.extend(own[path])
            related.update(
                (item, found_related[item])
                for item in own[path]
                if item in found_related
            )
        if (
            path not in failed
            and path not in blocked
            and not own_errors[path]
            and not _has_errors(own[path])
        ):
            facts = pass_facts.get(path)
            if facts is not None:
                facts_by_path[path] = facts
    parse, found, found_related, _, _ = passes[-1]
    errors.extend(error for error in parse.errors if error.path not in paths)
    rest = tuple(item for item in found if item.location.path not in paths)
    diagnostics.extend(rest)
    related.update(
        (item, found_related[item]) for item in rest if item in found_related
    )
    return ProjectDiagnosticsReport(
        errors=tuple(errors),
        paths=paths,
        diagnostics=tuple(diagnostics),
        related_locations=related,
        texts=texts,
        not_checked=tuple(not_checked),
    ), facts_by_path


def _check_pass(
    root: str | Path,
    excluded: frozenset[str],
    overlays: Mapping[str, str],
    *,
    editor_facts: bool,
) -> tuple[
    ProjectParseCheckResult,
    tuple[Diagnostic, ...],
    RelatedLocations,
    frozenset[str],
    Mapping[str, EditorFacts],
]:
    """One project check without the modules in ``excluded``: its parse
    check, the diagnostics and related locations the CLI reports for it, and
    the modules it fails when it stops, none when it completes."""

    from pietto._project.json_v2 import module_related_locations

    parse = check_project_parse_only(root, overlays=overlays, exclude=excluded)
    related = module_related_locations(parse)
    explicit = parse.compilation_mode is ProjectCompilationMode.EXPLICIT_MODULES
    if parse.ok:
        diagnostics, ok, semantic_related, facts = _check_project_semantics_with_facts(
            parse, editor_facts=editor_facts
        )
        # Semantic analysis stops only at an import cycle.
        return (
            parse,
            (*parse.diagnostics, *diagnostics),
            {**related, **semantic_related},
            _failed_modules(_module_diagnostics(parse), (), ())
            if explicit and not ok
            else frozenset(),
            facts,
        )
    paths = {item.path for item in parse.inputs}
    if not explicit or any(error.path not in paths for error in parse.errors):
        return parse, parse.diagnostics, related, frozenset(), {}
    return (
        parse,
        parse.diagnostics,
        related,
        _failed_modules(parse.module_diagnostic_facts, parse.errors, parse.diagnostics)
        & paths,
        {},
    )


def _failed_modules(
    facts: ProjectModuleDiagnosticSet | None,
    errors: tuple[ProjectDiscoveryError, ...],
    diagnostics: tuple[Diagnostic, ...],
) -> frozenset[str]:
    """The modules a stopped explicit-module check fails: each member of an
    import cycle, and each module with a discovery error or an error
    diagnostic other than a module import or export error. Such an error
    stops no check, unless it is one of a def or relationship item, which
    stops the check before semantic analysis (`_def_imports`)."""

    members: set[str] = set()
    kept: set[Diagnostic] = set()
    for fact in facts.facts if facts is not None else ():
        cycles = [issue.cycle for issue in fact.graph_issues if issue.cycle is not None]
        members.update(
            member.identity.path
            for cycle in cycles
            for member in cycle.component.members
        )
        requests = (
            *(issue.request for issue in (*fact.export_issues, *fact.binding_issues)),
            *(request for issue in fact.graph_issues for request in issue.requests),
        )
        if not cycles and all(
            request.source_item.declaration_kind not in _CALLABLE_ITEM_KINDS
            for request in requests
        ):
            kept.add(fact.diagnostic)
    return frozenset(
        {
            *members,
            *(error.path for error in errors if error.path is not None),
            *(
                item.location.path
                for item in diagnostics
                if item.severity is Severity.ERROR
                and item not in kept
                and item.location.path is not None
            ),
        }
    )


def _imported(
    imports: Mapping[str, tuple[ImportStatement, ...]], path: str
) -> set[str]:
    """The modules ``path`` imports, directly or through other modules."""

    found: set[str] = set()
    pending = [path]
    while pending:
        for statement in imports.get(pending.pop(), ()):
            if statement.target not in found:
                found.add(statement.target)
                pending.append(statement.target)
    return found


def _not_checked(
    path: str,
    statements: tuple[ImportStatement, ...],
    left_out: set[str],
    reached: list[str],
) -> tuple[SourceLocation, str]:
    """Why a module was not checked: the failed modules with errors that it
    imports, at the target of its first import of a module that was left
    out."""

    span = min(
        (statement for statement in statements if statement.target in left_out),
        key=lambda statement: (statement.span.line, statement.span.column),
    ).target_span
    listed = (
        reached[0]
        if len(reached) == 1
        else f"{', '.join(reached[:-1])} and {reached[-1]}"
    )
    return (
        SourceLocation(
            path=path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
        f"Not checked: this module imports {listed}, which "
        f"{'has' if len(reached) == 1 else 'have'} errors.",
    )


def selected_project_paths(root: str | Path) -> tuple[str, ...]:
    """The project-relative paths that `check --project` selects at `root`, in
    input order, without reading them."""

    selection = select_project_sources(root, load_project_config(root))
    return tuple(item.path for item in selection.inputs)


def check_project_semantics(
    parse_result: ProjectParseCheckResult,
) -> tuple[tuple[Diagnostic, ...], bool, RelatedLocations]:
    """Check project semantics; as in a single file, exhausting the recursion
    limit is PIE-S2006.

    Every diagnostic that a project check reports after the parse check's own
    comes from here, with the related locations its module owner computed. As
    the project JSON v2 contract states, an explicit-module check reports a
    diagnostic equal to an earlier one once, at its first position; the parse
    check applies that rule to its own diagnostics."""

    diagnostics, ok, related, _ = _check_project_semantics_with_facts(
        parse_result, editor_facts=False
    )
    return diagnostics, ok, related


def _check_project_semantics_with_facts(
    parse_result: ProjectParseCheckResult, *, editor_facts: bool
) -> tuple[tuple[Diagnostic, ...], bool, RelatedLocations, Mapping[str, EditorFacts]]:
    """Run one semantic pass and detach editor facts only after it succeeds."""

    from pietto._project.json_v2 import module_related_locations
    from pietto._project.model import build_empty_project_semantic_result

    related: RelatedLocations = {}
    facts: Mapping[str, EditorFacts] = {}
    try:
        semantic_result = build_empty_project_semantic_result(parse_result)
        related = module_related_locations(semantic_result)
        diagnostics, ok = project_semantic_boundary(semantic_result)
        if ok and editor_facts:
            facts = _project_editor_facts(semantic_result)
    except RecursionError:
        diagnostics, ok = (project_recursion_limit_diagnostic(parse_result),), False
    if parse_result.compilation_mode is ProjectCompilationMode.EXPLICIT_MODULES:
        earlier = set(parse_result.diagnostics)
        diagnostics = tuple(
            diagnostic
            for diagnostic in dict.fromkeys(diagnostics)
            if diagnostic not in earlier
        )
    return diagnostics, ok, related, facts


def _project_editor_facts(
    semantic_result: ProjectSemanticResult,
) -> Mapping[str, EditorFacts]:
    """Detach exact schema-v2 declaration, type and FROM resolution facts."""

    if semantic_result.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES:
        return {}
    type_roots = semantic_result.module_type_source_resolutions
    relation_roots = semantic_result.module_relation_resolutions
    if type_roots is None or relation_roots is None:
        return {}
    types = {
        environment.module.path: environment for environment in type_roots.environments
    }
    relations = {
        environment.module.path: environment
        for environment in relation_roots.environments
    }
    facts: dict[str, EditorFacts] = {}
    for module in semantic_result.modules:
        parsed = module.parsed_input
        if parsed is None:
            continue
        declarations = tuple(
            declaration
            for definition in authored_declarations(parsed.script)
            if (declaration := editor_declaration(definition, path=module.path))
            is not None
        )
        uses = []
        relation_environment = relations.get(module.path)
        if relation_environment is not None:
            for resolution in relation_environment.resolutions:
                target = resolution.target_symbol.target_occurrence
                target_declaration = editor_declaration(
                    target.definition, path=target.identity.module_path
                )
                if target_declaration is None:
                    continue
                uses.append(
                    editor_use(
                        resolution.reference.from_clause,
                        f"{target.identity.declaration_kind.value} "
                        f"{target.identity.declared_name}",
                        target_declaration,
                        path=module.path,
                    )
                )
        type_environment = types.get(module.path)
        if type_environment is not None:
            for resolution in type_environment.type_resolutions:
                symbol = resolution.direct_symbol
                target_declaration = (
                    editor_declaration(
                        symbol.target_occurrence.definition,
                        path=symbol.target_occurrence.identity.module_path,
                    )
                    if symbol is not None
                    else None
                )
                uses.append(
                    editor_use(
                        resolution.reference.type_expr,
                        f"{resolution.canonical_kind.value} {resolution.canonical_name}",
                        target_declaration,
                        path=module.path,
                    )
                )
        facts[module.path] = EditorFacts(
            declarations=declarations,
            uses=tuple(uses),
        )
    return MappingProxyType(facts)


def project_semantic_boundary(
    semantic_result: ProjectSemanticResult,
) -> tuple[tuple[Diagnostic, ...], bool]:
    """Select the completed boundary for explicit-module Project checks and the
    legacy-flat semantic checks for legacy-flat ones."""

    from pietto._project.project_completed_semantics import (
        build_project_completed_semantic_result,
    )

    if semantic_result.compilation_mode is ProjectCompilationMode.EXPLICIT_MODULES:
        completed = build_project_completed_semantic_result(semantic_result)
        return completed.diagnostics, completed.ok
    if semantic_result.compilation_mode is ProjectCompilationMode.LEGACY_FLAT:
        return check_legacy_flat_semantics(semantic_result)
    return semantic_result.diagnostics, semantic_result.ok


def check_project_parse_only(
    root: str | Path,
    *,
    overlays: Mapping[str, str] | None = None,
    exclude: frozenset[str] = frozenset(),
) -> ProjectParseCheckResult:
    """Load, select, read, and parse project sources without semantic
    analysis, leaving out each project-relative path in ``exclude``. A
    selected path in `overlays` is read from that editor text, an untrusted
    overlay source, instead of the disk."""

    result = _check_project_parse_only(root, overlays or {}, exclude)
    if result.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES:
        return result
    from pietto._project.module_bindings import (
        _build_project_module_binding_environment_set,
    )
    from pietto._project.module_catalog import _build_project_module_catalog_set
    from pietto._project.module_exports import (
        _build_project_module_export_surface_set,
    )
    from pietto._project.module_graph import import_hints

    def exports() -> ProjectModuleExportSurfaceSet:
        assert result.selected_input_index is not None
        catalogs = _build_project_module_catalog_set(result.modules)
        bindings = _build_project_module_binding_environment_set(
            result.selected_input_index, result.modules, catalogs
        )
        return _build_project_module_export_surface_set(
            catalogs, imported_binding_candidates=bindings.imported_export_candidates
        )

    hinted = import_hints(result.diagnostics, result.parsed_inputs, exports)
    if hinted is not result.diagnostics:
        result = replace(result, diagnostics=hinted)
    # As the project JSON v2 contract states, an explicit-module check reports
    # a diagnostic equal to an earlier one once, at its first position. A check
    # reads some text more than once, such as a comparison chain's inner
    # operand or a def argument, and so can find one error in it more than once.
    unique = tuple(dict.fromkeys(result.diagnostics))
    if len(unique) == len(result.diagnostics):
        # Readers compare the result and its diagnostics by identity.
        return result
    return replace(result, diagnostics=unique)


def _check_project_parse_only(
    root: str | Path, overlays: Mapping[str, str], exclude: frozenset[str]
) -> ProjectParseCheckResult:
    config_result = load_project_config(root)
    selection_result = select_project_sources(root, config_result, exclude=exclude)
    if selection_result.errors:
        return ProjectParseCheckResult(
            root=selection_result.root,
            config_path=selection_result.config_path,
            inputs=selection_result.inputs,
            errors=selection_result.errors,
            diagnostics=(),
            compilation_mode=selection_result.compilation_mode,
            modules=selection_result.modules,
            pinned_root=selection_result.pinned_root,
            selected_input_index=selection_result.selected_input_index,
        )

    pinned_root = selection_result.pinned_root
    selected_input_index = selection_result.selected_input_index
    if pinned_root is None or selected_input_index is None:
        return _selection_resource_error(selection_result)

    inputs: list[ProjectInput] = []
    parsed_inputs: list[ProjectParsedInput] = []
    errors: list[ProjectDiscoveryError] = []
    diagnostics: list[Diagnostic] = []
    raw_capture_diagnostics: list[Diagnostic] = []
    raw_parameter_positions: list[Diagnostic] = []
    unadmitted_paths: set[str] = set()
    trusted_source_snapshots: list[ProjectSource] = []
    explicit_modules = (
        selection_result.compilation_mode is ProjectCompilationMode.EXPLICIT_MODULES
    )
    # Every input is read and admitted first, so imports bind each def to
    # its declaring module before any def call is inlined;
    # each input still reports in selected order.
    read: list[_ReadInput | _InputOutcome] = []
    for entry in selected_input_index.entries:
        outcome = _read_selected_input(
            pinned_root,
            entry,
            overlay=overlays.get(entry.identity.path),
            explicit_modules=explicit_modules,
        )
        read.append(outcome)
        if type(outcome) is tuple and outcome[3] and outcome[3][0].path is None:
            break
    def_imports = _def_imports(selected_input_index, read) if explicit_modules else None
    finished: dict[int, tuple[_InputOutcome, list[Diagnostic], list[Diagnostic]]] = {}
    templates: dict[str, dict[str, DefTemplate]] = {}
    for position in _inline_order(read, def_imports):
        item = read[position]
        assert type(item) is _ReadInput
        imported, failed, blocked = _imported_templates(
            item, def_imports, templates, read
        )
        own: dict[str, DefTemplate] = {}
        captured: list[Diagnostic] = []
        parameter_positions: list[Diagnostic] = []
        finished[position] = (
            _finish_selected_input(
                item,
                explicit_modules=explicit_modules,
                imported=imported,
                failed=failed,
                blocked=blocked,
                templates_out=own,
                imported_relationships=(
                    ()
                    if def_imports is None
                    else def_imports.relationships.get(item.entry.identity.path, ())
                ),
                capture_diagnostics_out=captured,
                parameter_positions_out=parameter_positions,
                unadmitted_paths_out=unadmitted_paths,
            ),
            captured,
            parameter_positions,
        )
        templates[item.entry.identity.path] = own
    for position, item in enumerate(read):
        if isinstance(item, _ReadInput):
            outcome, captured, parameter_positions = finished[position]
            raw_capture_diagnostics.extend(captured)
            raw_parameter_positions.extend(parameter_positions)
        else:
            outcome = item
        (
            parsed_input,
            parsed_semantic_input,
            trusted_source_snapshot,
            input_errors,
            input_diagnostics,
        ) = outcome
        entry = selected_input_index.entries[position]
        inputs.append(parsed_input)
        if parsed_semantic_input is not None:
            parsed_inputs.append(parsed_semantic_input)
        if trusted_source_snapshot is not None:
            trusted_source_snapshots.append(trusted_source_snapshot)
        errors.extend(input_errors)
        diagnostics.extend(input_diagnostics)
        if input_errors and input_errors[0].path is None:
            inputs.extend(
                ProjectInput(path=remaining.identity.path, status=_ERROR_STATUS)
                for remaining in selected_input_index.entries[entry.position + 1 :]
            )
            break

    if (
        selection_result.compilation_mode is ProjectCompilationMode.LEGACY_FLAT
        and any(item.message.endswith(PIPE_HINT) for item in diagnostics)
        and any(
            parser_api.source_declares_concat(item.source_text)
            for item in trusted_source_snapshots
        )
    ):
        # One namespace: a file's `concat` names another file's callable.
        diagnostics = list(with_unjoined_pipe_hints(diagnostics))
    final_inputs = tuple(inputs)
    final_parsed_inputs = tuple(parsed_inputs)
    result = ProjectParseCheckResult(
        root=selection_result.root or ProjectRoot(path=_PROJECT_ROOT_PATH),
        config_path=selection_result.config_path
        or ProjectConfigPath(path=_PROJECT_CONFIG_PATH),
        inputs=final_inputs,
        errors=tuple(errors),
        diagnostics=tuple(diagnostics),
        parsed_inputs=final_parsed_inputs,
        compilation_mode=selection_result.compilation_mode,
        modules=_build_project_logical_modules(
            selection_result.compilation_mode,
            final_inputs,
            final_parsed_inputs,
        ),
        pinned_root=pinned_root,
        selected_input_index=selected_input_index,
        trusted_source_snapshots=tuple(trusted_source_snapshots),
    )

    if result.compilation_mode is ProjectCompilationMode.EXPLICIT_MODULES:
        from pietto._project.project_relationship_predicates import (
            normalize_project_query_names,
        )

        # These occurrences need canonical aliases/LET dependencies. All other
        # header errors stop the check here, after the module errors once
        # every module parsed and passed syntax admission; parse and
        # admission errors stop it before them.
        deferred_ids = {
            id(item) for item in (*raw_capture_diagnostics, *raw_parameter_positions)
        }
        naming_input = replace(
            result,
            diagnostics=tuple(
                item for item in result.diagnostics if id(item) not in deferred_ids
            ),
        )
        if not naming_input.ok or (def_imports is not None and def_imports.stop):
            if (
                result.errors
                or unadmitted_paths
                or any(item.status != _PARSED_STATUS for item in result.inputs)
            ):
                return result
            return _with_module_diagnostics(
                result, result, result.diagnostics, def_imports
            )
        normalized = normalize_project_query_names(naming_input)
        positions = {item.path: position for position, item in enumerate(result.inputs)}
        if normalized.ok:
            prior_positions: dict[Diagnostic, deque[Diagnostic]] = {}
            for item in raw_parameter_positions:
                prior_positions.setdefault(item, deque()).append(item)
            admission: list[Diagnostic] = []
            for source, authored in zip(
                normalized.parsed_inputs, naming_input.parsed_inputs, strict=True
            ):
                admission.extend(
                    _with_project_relative_path(item, source.path)
                    for item in sorted(
                        capture_diagnostics(source.script), key=source_order
                    )
                )
                admission.extend(
                    _with_project_relative_path(item, source.path)
                    for item in query_parameter_unbound_naming_diagnostics(
                        authored.script, source.script
                    )
                )
                for item in query_parameter_diagnostics(source.script):
                    diagnostic = _with_project_relative_path(item, source.path)
                    prior = prior_positions.get(diagnostic)
                    # Reuse each original occurrence once; equal values may
                    # have multiple distinct diagnostics, never one winner.
                    admission.append(prior.popleft() if prior else diagnostic)
            admitted = tuple(
                sorted(
                    (*normalized.diagnostics, *admission),
                    key=lambda item: positions[item.location.path or ""],
                )
            )
            if not _has_errors(admitted):
                return replace(normalized, diagnostics=admitted)
            return _with_module_diagnostics(
                normalized, naming_input, admitted, def_imports
            )
        return _with_module_diagnostics(
            normalized,
            naming_input,
            tuple(
                sorted(
                    (
                        *normalized.diagnostics,
                        *raw_capture_diagnostics,
                        *raw_parameter_positions,
                    ),
                    key=lambda item: (
                        positions[item.location.path or ""],
                        *source_order(item)[1:],
                    ),
                )
            ),
            def_imports,
        )
    if (
        result.compilation_mode is ProjectCompilationMode.LEGACY_FLAT
        and result.ok
        and result.parsed_inputs
    ):
        return _resolve_legacy_flat_query_names(result)
    return result


def _with_module_diagnostics(
    result: ProjectParseCheckResult,
    authored: ProjectParseCheckResult,
    diagnostics: tuple[Diagnostic, ...],
    def_imports: _DefImports | None = None,
) -> ProjectParseCheckResult:
    """`result`, a parse check of an explicit-module project whose every
    module parsed and passed syntax admission but which stops before
    semantic analysis on a `def`, def import, header, parameter, capture or
    naming error, with `diagnostics` after the module import and export
    errors of the `authored` modules and their related locations. Semantic
    analysis reports those errors first, so no such error in any module
    masks one. A project whose def import or export items failed reports the
    errors they were bound with (`def_imports`), each def a declaration of
    its module. Otherwise a module whose `def` calls are not inlined still
    holds its `def` declarations, which no module imports or exports, so
    they are left out, as inlining leaves them out of the modules semantic
    analysis reads. Without module errors, a result with these diagnostics
    is kept as it is."""

    if def_imports is not None and def_imports.stop:
        module_diagnostics = def_imports.facts
        return replace(
            result,
            module_diagnostic_facts=module_diagnostics,
            diagnostics=(
                *module_diagnostics.diagnostics,
                *def_imports.diagnostics,
                *diagnostics,
            ),
        )
    parsed_inputs = tuple(
        replace(
            parsed,
            script=replace(
                parsed.script,
                definitions=tuple(
                    item
                    for item in parsed.script.definitions
                    if type(item) is not FunctionDef
                ),
            ),
        )
        if any(type(item) is FunctionDef for item in parsed.script.definitions)
        else parsed
        for parsed in authored.parsed_inputs
    )
    if any(new is not old for new, old in zip(parsed_inputs, authored.parsed_inputs)):
        authored = replace(
            authored,
            parsed_inputs=parsed_inputs,
            modules=_build_project_logical_modules(
                authored.compilation_mode, authored.inputs, parsed_inputs
            ),
        )
    module_diagnostics = _module_diagnostics(authored)
    if not module_diagnostics.diagnostics and diagnostics is result.diagnostics:
        return result
    return replace(
        result,
        module_diagnostic_facts=module_diagnostics,
        diagnostics=(*module_diagnostics.diagnostics, *diagnostics),
    )


def _module_diagnostics(result: ProjectParseCheckResult) -> ProjectModuleDiagnosticSet:
    """The module import and export errors of a parsed explicit-module
    project, in their semantic-check order, and their facts."""

    assert result.selected_input_index is not None
    return _module_facts(result.selected_input_index, result.modules)[3]


def _module_facts(
    selected_input_index: ProjectSelectedInputIndex,
    modules: tuple[ProjectLogicalModule, ...],
) -> tuple[
    ProjectModuleBindingEnvironmentSet,
    ProjectModuleExportSurfaceSet,
    ProjectModuleGraph,
    ProjectModuleDiagnosticSet,
]:
    """The import bindings, export surfaces, import graph and module errors
    of the parsed modules of an explicit-module project."""

    from pietto._project.module_bindings import (
        _build_project_module_binding_environment_set,
    )
    from pietto._project.module_catalog import _build_project_module_catalog_set
    from pietto._project.module_exports import (
        _build_project_module_export_surface_set,
    )
    from pietto._project.module_graph import (
        _build_project_module_diagnostic_set,
        _build_project_module_graph,
    )

    catalogs = _build_project_module_catalog_set(modules)
    bindings = _build_project_module_binding_environment_set(
        selected_input_index, modules, catalogs
    )
    exports = _build_project_module_export_surface_set(
        catalogs, imported_binding_candidates=bindings.imported_export_candidates
    )
    graph = _build_project_module_graph(selected_input_index, modules, bindings)
    return (
        bindings,
        exports,
        graph,
        _build_project_module_diagnostic_set(graph, exports, bindings),
    )


# The import and export items that only inlining and relationship binding
# read: a def's and a relationship's.
_CALLABLE_ITEM_KINDS = frozenset(
    {ModuleDeclarationKind.DEF, ModuleDeclarationKind.RELATIONSHIP}
)


@dataclass(frozen=True, slots=True)
class _DefImports:
    """How each module of an explicit-module project that imports or exports
    a def or a relationship binds the defs and relationships it imports,
    found before any call is inlined or bound.

    ``bound`` maps a module path to each local name it imports a def under,
    with the declaring module's path and the def's name there, and
    ``relationships`` to each relationship it imports likewise. A module in
    ``blocked`` imports a def along an import cycle; its calls
    are not inlined. A def or relationship import or export that fails, one
    along an import cycle, or one bound to a built-in name (PIE-S2398)
    ``stop``s the check before semantic analysis, as a def error does, with
    the module errors in ``facts`` and the others in ``diagnostics``."""

    bound: Mapping[str, Mapping[str, tuple[str, str]]]
    relationships: Mapping[str, tuple[tuple[str, str, str], ...]]
    blocked: frozenset[str]
    facts: ProjectModuleDiagnosticSet
    diagnostics: tuple[Diagnostic, ...]
    stop: bool


def _def_imports(
    selected_input_index: ProjectSelectedInputIndex,
    read: list[_ReadInput | _InputOutcome],
) -> _DefImports | None:
    """Bind the def and relationship imports of an explicit-module project
    whose every module parsed and passed syntax admission, through the same
    exports and bindings as every other import, each def and relationship a
    declaration of its module (`_callable_view`). A project without a def or
    relationship import or export item has none."""

    inputs = tuple(item for item in read if type(item) is _ReadInput)
    if (
        len(inputs) != len(selected_input_index.entries)
        or any(
            item.recursion or item.gate or item.existence_diagnostics for item in inputs
        )
        or not any(_callable_items(item.script) for item in inputs)
    ):
        return None
    parsed = tuple(
        ProjectParsedInput(
            path=item.entry.identity.path, script=_callable_view(item.script)
        )
        for item in inputs
    )
    modules = _build_project_logical_modules(
        ProjectCompilationMode.EXPLICIT_MODULES,
        tuple(ProjectInput(path=item.path, status=_PARSED_STATUS) for item in parsed),
        parsed,
    )
    bindings, exports, graph, facts = _module_facts(selected_input_index, modules)
    cycle_of = {
        member.identity.path: position
        for position, component in enumerate(graph.components)
        if component.is_cyclic
        for member in component.members
    }
    stop = any(
        issue.request.source_item.declaration_kind in _CALLABLE_ITEM_KINDS
        for surface in exports.surfaces
        for issue in surface.issues
    ) or any(
        issue.request.source_item.declaration_kind in _CALLABLE_ITEM_KINDS
        for environment in bindings.environments
        for issue in environment.issues
    )
    bound: dict[str, dict[str, tuple[str, str]]] = {}
    relationships: dict[str, list[tuple[str, str, str]]] = {}
    blocked: set[str] = set()
    found: list[Diagnostic] = []
    for environment in bindings.environments:
        path = environment.module.path
        for binding in environment.bindings:
            request = binding.request
            kind = request.source_item.declaration_kind
            if kind not in _CALLABLE_ITEM_KINDS:
                continue
            local = binding.identity.local_binding_name
            target = binding.target_identity
            if path in cycle_of and cycle_of[path] == cycle_of.get(
                request.target_module_path
            ):
                stop = True
                if kind is ModuleDeclarationKind.DEF:
                    blocked.add(path)
            elif reserved_import_name(local):
                found.append(
                    _span_diagnostic(
                        "PIE-S2398",
                        f"Import binding {local} has the name of a built-in "
                        f"function; a {kind.value} cannot shadow one",
                        request.source_item.span,
                        path,
                    )
                )
            elif kind is ModuleDeclarationKind.DEF:
                bound.setdefault(path, {})[local] = (
                    target.module_path,
                    target.declared_name,
                )
            else:
                relationships.setdefault(path, []).append(
                    (local, target.module_path, target.declared_name)
                )
    return _DefImports(
        bound=bound,
        relationships={path: tuple(items) for path, items in relationships.items()},
        blocked=frozenset(blocked),
        facts=facts,
        diagnostics=tuple(found),
        stop=stop or bool(found),
    )


def _callable_view(script: Script) -> Script:
    """``script`` with its relationships among its definitions, in source
    order, so that its exports and imports bind a relationship as any other
    declaration; no later reader sees this view."""

    if not script.relationship_templates:
        return script
    return replace(
        script,
        definitions=cast(
            tuple[Definition, ...],
            tuple(
                sorted(
                    (*script.definitions, *script.relationship_templates),
                    key=lambda item: (item.span.line, item.span.column),
                )
            ),
        ),
    )


def _callable_items(script: Script) -> bool:
    """Whether ``script`` imports or exports a def or a relationship."""

    return any(
        item.declaration_kind in _CALLABLE_ITEM_KINDS
        for statement in script.module_statements
        for item in statement.items
    )


def _inline_order(
    read: list[_ReadInput | _InputOutcome], def_imports: _DefImports | None
) -> list[int]:
    """The positions of the read inputs, each after the modules that declare
    a def it imports, otherwise in selected order."""

    positions = {
        item.entry.identity.path: position
        for position, item in enumerate(read)
        if type(item) is _ReadInput
    }
    ordered: dict[int, None] = {}
    for root in positions.values():
        pending = [(root, False)]
        while pending:
            position, ready = pending.pop()
            if position in ordered:
                continue
            if ready:
                ordered[position] = None
                continue
            pending.append((position, True))
            item = read[position]
            assert type(item) is _ReadInput
            path = item.entry.identity.path
            if def_imports is None or path in def_imports.blocked:
                continue
            pending.extend(
                (positions[declaring], False)
                for declaring, _ in reversed(
                    tuple(def_imports.bound.get(path, {}).values())
                )
                if positions[declaring] not in ordered
            )
    return list(ordered)


def _imported_templates(
    item: _ReadInput,
    def_imports: _DefImports | None,
    templates: Mapping[str, Mapping[str, DefTemplate]],
    read: list[_ReadInput | _InputOutcome],
) -> tuple[dict[str, DefTemplate], dict[str, FunctionDef], bool]:
    """The checked defs a module imports, by the names it binds, the defs it
    imports whose own module did not inline them (an error that module
    reports), and whether it is blocked: its def imports are not bound, or
    one of them is such a def."""

    path = item.entry.identity.path
    if def_imports is None:
        return (
            {},
            {},
            any(
                imported_item.declaration_kind is ModuleDeclarationKind.DEF
                for statement in item.script.module_statements
                if type(statement) is ImportStatement
                for imported_item in statement.items
            ),
        )
    if path in def_imports.blocked:
        return {}, {}, True
    imported: dict[str, DefTemplate] = {}
    failed: dict[str, FunctionDef] = {}
    for local, (declaring, name) in def_imports.bound.get(path, {}).items():
        template = templates.get(declaring, {}).get(name)
        if template is not None:
            imported[local] = template
            continue
        failed[local] = next(
            definition
            for other in read
            if type(other) is _ReadInput and other.entry.identity.path == declaring
            for definition in other.script.definitions
            if type(definition) is FunctionDef and definition.name == name
        )
    return imported, failed, bool(failed)


def _without_callable_items(script: Script) -> Script:
    """``script`` without its def and relationship import and export items,
    which no later reader sees, and so no compiled record holds."""

    if not _callable_items(script):
        return script
    return replace(
        script,
        module_statements=tuple(
            replace(
                statement,
                items=tuple(
                    item
                    for item in statement.items
                    if item.declaration_kind not in _CALLABLE_ITEM_KINDS
                ),
            )
            for statement in script.module_statements
        ),
    )


def _exported(script: Script, kind: ModuleDeclarationKind) -> tuple[str, ...]:
    """The names of the declarations of ``kind`` that ``script`` exports."""

    return tuple(
        item.local_name
        for statement in script.module_statements
        if type(statement) is ExportStatement
        for item in statement.items
        if item.declaration_kind is kind
    )


def _span_diagnostic(code: str, message: str, span: Span, path: str) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        location=SourceLocation(
            path=span.path or path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _resolve_legacy_flat_query_names(
    result: ProjectParseCheckResult,
) -> ProjectParseCheckResult:
    """Resolve each `let name = value` of a legacy-flat project in its one
    shared namespace, as the project's semantic analysis does, so the project
    model reads a let binding or a relation alias as a single file does.

    That analysis reads the parsed scripts and reports each diagnostic of the
    resolution, after the project model's, so none is reported here.
    """

    resolved, _ = normalize_query_names(
        _shared_namespace(tuple(parsed.script for parsed in result.parsed_inputs))
    )
    definitions = iter(resolved.definitions)
    parsed_inputs = []
    for parsed in result.parsed_inputs:
        own = tuple(next(definitions) for _ in parsed.script.definitions)
        if all(new is old for new, old in zip(own, parsed.script.definitions)):
            parsed_inputs.append(parsed)
        else:
            parsed_inputs.append(
                replace(
                    parsed,
                    script=replace(parsed.script, definitions=own),
                    authored_script=parsed.script,
                )
            )
    if all(new is old for new, old in zip(parsed_inputs, result.parsed_inputs)):
        return result
    return replace(
        result,
        parsed_inputs=tuple(parsed_inputs),
        modules=_build_project_logical_modules(
            result.compilation_mode, result.inputs, tuple(parsed_inputs)
        ),
    )


def _shared_namespace(scripts: tuple[Script, ...]) -> Script:
    """The selected scripts of a legacy-flat project read as one script in
    module order."""

    return replace(
        scripts[0],
        header=None,
        definitions=tuple(item for script in scripts for item in script.definitions),
        relationships=tuple(
            item for script in scripts for item in script.relationships
        ),
        relationship_templates=tuple(
            item for script in scripts for item in script.relationship_templates
        ),
        module_statements=tuple(
            item for script in scripts for item in script.module_statements
        ),
    )


def project_recursion_limit_diagnostic(
    parse_result: ProjectParseCheckResult,
) -> Diagnostic:
    """Report PIE-S2006 once project processing exceeds the recursion limit.

    As in a single file it spans one whole source: the parsed module whose
    syntax nests deepest, the first such module in module order. A
    LEGACY_FLAT module is measured as parsed, the script its semantic checks
    analyze; any other as the script its project reads.
    """

    legacy_flat = parse_result.compilation_mode is ProjectCompilationMode.LEGACY_FLAT
    return recursion_limit_diagnostic(
        *(
            (parsed.authored_script if legacy_flat else None) or parsed.script
            for parsed in parse_result.parsed_inputs
        )
    )


def check_legacy_flat_semantics(
    semantic_result: ProjectSemanticResult,
) -> tuple[tuple[Diagnostic, ...], bool]:
    """Complete a legacy-flat project check with the semantic checks.

    The selected sources share one namespace, so they are analyzed as parsed,
    as one script in module order, after the project model's diagnostics, none
    of which is repeated. The model refuses each JOIN and each any(...)
    (PIE-S2334), so the script is analyzed without its any(...), which then
    holds back no check of the rest, and no diagnostic inside a JOIN or an
    any(...) is kept. A project is not held to the single-file expression
    bound, so analysis that reaches it (PIE-S2006) adds nothing. Only an
    EXPLICIT_MODULES project reads import and export statements, so each is
    an error (PIE-S2708), after the model's diagnostics.
    """

    model = semantic_result.model
    if model is None or not model.inputs:
        return semantic_result.diagnostics, semantic_result.ok
    namespace = _shared_namespace(
        tuple(parsed.authored_script or parsed.script for parsed in model.inputs)
    )
    statements = module_statement_diagnostics(namespace, legacy_flat=True)
    refused = tuple(node.span for node in legacy_flat_refused(namespace))
    analyzed = tuple(
        diagnostic
        for diagnostic in analyze_project_namespace(without_any(namespace)).diagnostics
        if not any(_inside(diagnostic.location, span) for span in refused)
    )
    if any(diagnostic.code == "PIE-S2006" for diagnostic in analyzed):
        if not statements:
            return semantic_result.diagnostics, semantic_result.ok
        analyzed = ()
    reported = set(semantic_result.diagnostics)
    diagnostics = (
        *semantic_result.diagnostics,
        *statements,
        *(diagnostic for diagnostic in analyzed if diagnostic not in reported),
    )
    return diagnostics, not _has_errors(diagnostics)


def _inside(location: SourceLocation, span: Span) -> bool:
    return (
        location.path == span.path
        and (span.line, span.column) <= (location.line, location.column)
        and (
            location.end_line or location.line,
            location.end_column or location.column,
        )
        <= (span.end_line, span.end_column)
    )


_InputOutcome = tuple[
    ProjectInput,
    ProjectParsedInput | None,
    ProjectSource | None,
    tuple[ProjectDiscoveryError, ...],
    tuple[Diagnostic, ...],
]


@dataclass(frozen=True, slots=True)
class _ReadInput:
    """A selected input that parsed, read up to its syntax admission, before
    its def calls are inlined."""

    entry: ProjectSelectedInputEntry
    trusted_source: ProjectSource
    ast: Script
    diagnostics: tuple[Diagnostic, ...]
    script: Script
    existence_generators: tuple[AnyUseInfo, ...] = ()
    existence_diagnostics: tuple[Diagnostic, ...] = ()
    any_trace: AnyValueTrace | None = None
    gate: tuple[Diagnostic, ...] = ()
    recursion: bool = False


def _parse_selected_input(
    pinned_root: ProjectPinnedRoot,
    selected_input: ProjectSelectedInputEntry,
    *,
    explicit_modules: bool = False,
    capture_diagnostics_out: list[Diagnostic] | None = None,
    parameter_positions_out: list[Diagnostic] | None = None,
    unadmitted_paths_out: set[str] | None = None,
) -> _InputOutcome:
    """Read, parse and admit one selected input that imports no def."""

    read = _read_selected_input(
        pinned_root, selected_input, explicit_modules=explicit_modules
    )
    if not isinstance(read, _ReadInput):
        return read
    return _finish_selected_input(
        read,
        explicit_modules=explicit_modules,
        capture_diagnostics_out=capture_diagnostics_out,
        parameter_positions_out=parameter_positions_out,
        unadmitted_paths_out=unadmitted_paths_out,
    )


def _read_selected_input(
    pinned_root: ProjectPinnedRoot,
    selected_input: ProjectSelectedInputEntry,
    *,
    overlay: str | None = None,
    explicit_modules: bool = False,
) -> _ReadInput | _InputOutcome:
    trusted_source = (
        _read_selected_source(pinned_root, selected_input)
        if overlay is None
        else _overlay_source(selected_input, overlay)
    )
    failed = ProjectInput(path=selected_input.identity.path, status=_ERROR_STATUS)
    if isinstance(trusted_source, ProjectDiscoveryError):
        return failed, None, None, (trusted_source,), ()
    if isinstance(trusted_source, Diagnostic):
        return failed, None, None, (), (trusted_source,)

    parse_result = parser_api.parse_source(
        trusted_source.source_text,
        path=selected_input.identity.path,
    )
    diagnostics = tuple(
        _with_project_relative_path(diagnostic, selected_input.identity.path)
        for diagnostic in parse_result.diagnostics
    )
    if _has_errors(diagnostics):
        return (
            ProjectInput(path=selected_input.identity.path, status=_ERROR_STATUS),
            None,
            trusted_source,
            (),
            diagnostics,
        )
    if parse_result.ast is None:
        return (
            ProjectInput(path=selected_input.identity.path, status=_ERROR_STATUS),
            None,
            trusted_source,
            (
                ProjectDiscoveryError(
                    ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
                    "Project parser produced no AST.",
                    selected_input.identity.path,
                ),
            ),
            diagnostics,
        )
    from pietto._asof_join import lower_latest_rows
    from pietto.semantic.existence_generators import (
        AnyValueTrace,
        normalize_existence_generators,
    )
    from pietto.semantic.generators import group_any_calls

    # A SELECT item's `any(... for o in group)` is the test of a group.
    script = group_any_calls(parse_result.ast)
    read = _ReadInput(
        entry=selected_input,
        trusted_source=trusted_source,
        ast=parse_result.ast,
        diagnostics=diagnostics,
        script=script,
    )
    try:
        existence_generators: tuple[AnyUseInfo, ...] = ()
        existence_diagnostics: tuple[Diagnostic, ...] = ()
        any_trace = None
        if explicit_modules:
            # An admitted asof JOIN reads its latest row through `not any(...)`.
            script = lower_latest_rows(script)
            any_trace = AnyValueTrace(script)
            # A schema_version = 2 project selects the conditional count that
            # an `any(... for o in group)` hint names.
            script, existence_generators, existence_diagnostics = (
                normalize_existence_generators(
                    script, occurrence_observer=any_trace.record, group_hint=True
                )
            )
        gate = unadmitted_syntax_diagnostics(script, explicit_modules=explicit_modules)
    except RecursionError:
        return replace(read, recursion=True)
    return replace(
        read,
        script=script,
        existence_generators=existence_generators,
        existence_diagnostics=existence_diagnostics,
        any_trace=any_trace,
        gate=gate,
    )


def _finish_selected_input(
    read: _ReadInput,
    *,
    explicit_modules: bool = False,
    imported: Mapping[str, DefTemplate] | None = None,
    failed: Mapping[str, FunctionDef] | None = None,
    blocked: bool = False,
    templates_out: dict[str, DefTemplate] | None = None,
    imported_relationships: tuple[tuple[str, str, str], ...] = (),
    capture_diagnostics_out: list[Diagnostic] | None = None,
    parameter_positions_out: list[Diagnostic] | None = None,
    unadmitted_paths_out: set[str] | None = None,
) -> _InputOutcome:
    """Inline the def calls of a read input, with the defs it imports in
    ``imported``, and run its capture and header checks. A ``blocked`` input
    keeps its def calls, as one that fails admission does; when it imports a
    def that ``failed`` in its own module, its own defs are still checked.
    The relationships it imports are kept for relationship binding."""

    from pietto.semantic.existence_generators import (
        collect_any_values,
        rebind_existence_generators,
    )
    from pietto.semantic.generators import normalize_group_generators

    selected_input = read.entry
    script = read.script
    existence_generators = read.existence_generators
    existence_values = ()
    any_trace = read.any_trace
    existence_diagnostics = read.existence_diagnostics
    gate = read.gate
    captures: tuple[Diagnostic, ...] = ()
    parameter_positions: list[Diagnostic] = []
    imported_spans: frozenset[Span] = frozenset()
    try:
        if read.recursion:
            raise RecursionError
        inlined: tuple[Diagnostic, ...] = ()
        if failed and any_trace is not None and not gate and not existence_diagnostics:
            # A call of a failed def adds no error, and nor does a def that
            # calls one; each other error of this module's defs is reported.
            with builtin_shadows(read.ast):
                inlined = inline_functions(
                    script, imported=imported or {}, failed=failed
                )[1]
            inlined = name_uncallable_calls(inlined, read.ast)
        elif (
            any_trace is not None
            and not gate
            and not existence_diagnostics
            and not blocked
        ):
            # An admitted generator's member field `o.f` reads the input row's
            # field `f`, as in a single file.
            before_generators = script
            script = normalize_group_generators(script)
            existence_generators = rebind_existence_generators(
                before_generators, script, existence_generators
            )
            # Every later reader, and the capture and header checks, see each
            # def call inlined.
            before_inlining = script
            with builtin_shadows(read.ast):
                script, inlined = inline_functions(
                    script,
                    occurrence_observer=any_trace.record,
                    imported=imported or {},
                    templates_out=templates_out,
                )
                imported_spans = imported_nodes()
            existence_generators = rebind_existence_generators(
                before_inlining, script, existence_generators
            )
            inlined = name_uncallable_calls(inlined, read.ast)
        if any_trace is not None:
            existence_values = collect_any_values(script, trace=any_trace)
        captures = (
            capture_diagnostics(script) if explicit_modules and not inlined else ()
        )
        # A comparison chain's inner operand is read once per comparison and
        # written once, so each error in it is reported once, as in a file.
        admission = drop_repeated_operand_diagnostics(
            read.ast,
            inlined
            or (
                # Capture refusals are pre-admission diagnostics: one source
                # order with the gate's, then the header checks.
                *sorted(
                    (
                        *existence_diagnostics,
                        *gate,
                        *captures,
                    ),
                    key=source_order,
                ),
                *(
                    query_parameter_diagnostics(
                        script, position_diagnostics_out=parameter_positions
                    )
                    if explicit_modules
                    else ()
                ),
            ),
        )
        if (gate or existence_diagnostics) and unadmitted_paths_out is not None:
            unadmitted_paths_out.add(selected_input.identity.path)
    except RecursionError:
        admission = (recursion_limit_diagnostic(read.ast),)
        if unadmitted_paths_out is not None:
            unadmitted_paths_out.add(selected_input.identity.path)
    rebased_admission = tuple(
        _with_project_relative_path(item, selected_input.identity.path)
        for item in admission
    )
    if capture_diagnostics_out is not None:
        capture_ids = {id(item) for item in captures}
        capture_diagnostics_out.extend(
            rebased
            for item, rebased in zip(admission, rebased_admission, strict=True)
            if id(item) in capture_ids
        )
    if parameter_positions_out is not None:
        position_ids = {id(item) for item in parameter_positions}
        parameter_positions_out.extend(
            rebased
            for item, rebased in zip(admission, rebased_admission, strict=True)
            if id(item) in position_ids
        )
    diagnostics = (*read.diagnostics, *rebased_admission)
    return (
        ProjectInput(path=selected_input.identity.path, status=_PARSED_STATUS),
        ProjectParsedInput(
            path=selected_input.identity.path,
            script=_without_callable_items(script),
            existence_generators=existence_generators,
            existence_values=existence_values,
            scalar_callables=tuple(
                item for item in read.ast.definitions if type(item) is FunctionDef
            ),
            exported_defs=_exported(read.ast, ModuleDeclarationKind.DEF),
            exported_relationships=_exported(
                read.ast, ModuleDeclarationKind.RELATIONSHIP
            ),
            imported_relationships=imported_relationships,
            imported_nodes=imported_spans,
        ),
        read.trusted_source,
        (),
        diagnostics,
    )


def _overlay_source(
    selected_input: ProjectSelectedInputEntry, text: str
) -> ProjectOverlaySource | Diagnostic:
    """Editor text read in place of a selected file, under the file's limit."""

    if len(text.encode("utf-8")) > _PROJECT_SOURCE_UTF8_BYTES:
        return Diagnostic(
            code="PIE-P1006",
            severity=Severity.ERROR,
            message=(
                "Source exceeds the maximum supported size of "
                f"{_PROJECT_SOURCE_UTF8_BYTES} UTF-8 bytes."
            ),
            location=SourceLocation(
                path=selected_input.identity.path, line=1, column=1
            ),
        )
    return ProjectOverlaySource(selected_input=selected_input, source_text=text)


def read_explicit_module_sources(
    root: str | Path,
    command: str,
    *,
    opened_directories: dict[Path, tuple[ProjectPinnedRoot, int]] | None = None,
) -> tuple[
    tuple[ProjectDiscoveryError, ...],
    tuple[
        tuple[ProjectSelectedInputEntry, ProjectTrustedSourceSnapshot | Diagnostic],
        ...,
    ],
]:
    """Read, without parsing, every selected source of a schema_version 2
    project in module order: its selected entry with the trusted text, or
    with the PIE-P1006 diagnostic of a source over the size limit, and the
    project errors; one without a path stops the reading. `command` names
    the caller in the refusal of any other schema version. The formatter may
    retain one opened parent per directory; its caller owns closing every
    descriptor in ``opened_directories``, including on errors."""

    config_result = load_project_config(root)
    config = config_result.config
    if config is not None and (
        config.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES
    ):
        hint = (
            "Set schema_version = 2 and declare the names a file uses from"
            " another file with import and export."
            if config.compilation_mode is ProjectCompilationMode.LEGACY_FLAT
            else "Select the package's modules with a schema_version = 2"
            " pietto.toml in the package directory."
        )
        return (
            ProjectDiscoveryError(
                ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
                f"{command} needs schema_version = 2 (explicit modules); this"
                f" project uses schema_version {config.schema_version}. {hint}",
                _PROJECT_CONFIG_PATH,
            ),
        ), ()
    selection = select_project_sources(root, config_result)
    if selection.pinned_root is None or selection.selected_input_index is None:
        return selection.errors or _selection_resource_error(selection).errors, ()
    errors: list[ProjectDiscoveryError] = []
    sources: list[
        tuple[ProjectSelectedInputEntry, ProjectTrustedSourceSnapshot | Diagnostic]
    ] = []
    for entry in selection.selected_input_index.entries:
        if opened_directories is not None and _supports_directory_relative_open():
            parent = entry.canonical_path.parent
            if parent not in opened_directories:
                try:
                    descriptor = _open_pinned_directory(selection.pinned_root, parent)
                except OSError:
                    errors.append(
                        ProjectDiscoveryError(
                            ProjectDiscoveryErrorKind.SOURCE_READ,
                            "Project source file is not readable.",
                            entry.identity.path,
                        )
                    )
                    continue
                opened_directories[parent] = (selection.pinned_root, descriptor)
        source = _read_selected_source(selection.pinned_root, entry)
        if not isinstance(source, ProjectDiscoveryError):
            sources.append((entry, source))
            continue
        errors.append(source)
        if source.path is None:
            break
    return tuple(errors), tuple(sources)


def _read_selected_source(
    pinned_root: ProjectPinnedRoot,
    selected_input: ProjectSelectedInputEntry,
) -> ProjectTrustedSourceSnapshot | Diagnostic | ProjectDiscoveryError:
    """The trusted text of one selected source, the PIE-P1006 diagnostic of a
    source over the size limit, or the project error that refuses it."""

    try:
        return _load_trusted_source(
            pinned_root,
            selected_input,
            byte_limit=_PROJECT_SOURCE_UTF8_BYTES,
        )
    except UnicodeDecodeError:
        message = "Project source file must be valid UTF-8."
    except ProjectTrustedSourceError as error:
        return _trusted_source_failure(selected_input.project_input, error.reason)
    except OSError:
        message = "Project source file is not readable."
    return ProjectDiscoveryError(
        ProjectDiscoveryErrorKind.SOURCE_READ, message, selected_input.identity.path
    )


def _trusted_source_failure(
    selected_input: ProjectInput,
    reason: ProjectTrustedSourceFailure,
) -> ProjectDiscoveryError:
    kind, message, path = {
        ProjectTrustedSourceFailure.ROOT_CHANGED: (
            ProjectDiscoveryErrorKind.PROJECT_ROOT,
            "Project root identity changed during project loading.",
            None,
        ),
        ProjectTrustedSourceFailure.IDENTITY_UNAVAILABLE: (
            ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
            "Project filesystem identity is unavailable.",
            None,
        ),
        ProjectTrustedSourceFailure.SYMBOLIC_LINK_CHANGED: (
            ProjectDiscoveryErrorKind.SOURCE_READ,
            "Project source symbolic link changed after selection.",
            selected_input.path,
        ),
        ProjectTrustedSourceFailure.SOURCE_CHANGED: (
            ProjectDiscoveryErrorKind.SOURCE_READ,
            "Project source file changed after selection.",
            selected_input.path,
        ),
        ProjectTrustedSourceFailure.OPENED_IDENTITY_MISMATCH: (
            ProjectDiscoveryErrorKind.SOURCE_READ,
            "Project source opened identity does not match the selected file.",
            selected_input.path,
        ),
        ProjectTrustedSourceFailure.NOT_REGULAR: (
            ProjectDiscoveryErrorKind.SOURCE_READ,
            "Project source path must resolve to a regular file.",
            selected_input.path,
        ),
        ProjectTrustedSourceFailure.READ_MUTATION: (
            ProjectDiscoveryErrorKind.SOURCE_READ,
            "Project source file changed while being read.",
            selected_input.path,
        ),
    }[reason]
    return ProjectDiscoveryError(kind, message, path)


def _with_project_relative_path(
    diagnostic: Diagnostic,
    relative_path: str,
) -> Diagnostic:
    return replace(
        diagnostic,
        location=replace(diagnostic.location, path=relative_path),
    )


def _has_errors(diagnostics: tuple[Diagnostic, ...]) -> bool:
    return any(diagnostic.severity is Severity.ERROR for diagnostic in diagnostics)


def _root_error(
    message: str,
    *,
    compilation_mode: ProjectCompilationMode = ProjectCompilationMode.LEGACY_FLAT,
) -> ProjectParseCheckResult:
    return ProjectParseCheckResult(
        root=None,
        config_path=None,
        inputs=(),
        errors=(
            ProjectDiscoveryError(
                ProjectDiscoveryErrorKind.PROJECT_ROOT,
                message,
                None,
            ),
        ),
        diagnostics=(),
        compilation_mode=compilation_mode,
    )


def _selection_resource_error(
    selection_result: ProjectDiscoveryResult,
) -> ProjectParseCheckResult:
    return ProjectParseCheckResult(
        root=selection_result.root,
        config_path=selection_result.config_path,
        inputs=selection_result.inputs,
        errors=(
            ProjectDiscoveryError(
                ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
                "Project selected-input index is unavailable.",
                None,
            ),
        ),
        diagnostics=(),
        compilation_mode=selection_result.compilation_mode,
        modules=selection_result.modules,
        pinned_root=selection_result.pinned_root,
        selected_input_index=selection_result.selected_input_index,
    )
