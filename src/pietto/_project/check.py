"""Private project check orchestration."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

import pietto.parser_api as parser_api
from pietto._builtin_shadows import imported_nodes
from pietto.ast_nodes import (
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
from pietto._project.path_trust import ProjectPinnedRoot
from pietto._project.selected_input_index import ProjectSelectedInputEntry
from pietto._project.source_selection import select_project_sources
from pietto._project.trusted_source import (
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


def check_project_parse_only(root: str | Path) -> ProjectParseCheckResult:
    """Load, select, read, and parse project sources without semantic analysis."""

    result = _check_project_parse_only(root)
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


def _check_project_parse_only(root: str | Path) -> ProjectParseCheckResult:
    config_result = load_project_config(root)
    selection_result = select_project_sources(root, config_result)
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
    trusted_source_snapshots: list[ProjectTrustedSourceSnapshot] = []
    explicit_modules = (
        selection_result.compilation_mode is ProjectCompilationMode.EXPLICIT_MODULES
    )
    # Every input is read and admitted first, so imports bind each def to
    # its declaring module before any def call is inlined;
    # each input still reports in selected order.
    read: list[_ReadInput | _InputOutcome] = []
    for entry in selected_input_index.entries:
        outcome = _read_selected_input(
            pinned_root, entry, explicit_modules=explicit_modules
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


# The import and export items that only inlining reads: a def's, and a
# relationship's, which admission refuses until it is bound.
_CALLABLE_ITEM_KINDS = frozenset(
    {ModuleDeclarationKind.DEF, ModuleDeclarationKind.RELATIONSHIP}
)


@dataclass(frozen=True, slots=True)
class _DefImports:
    """How each module of an explicit-module project that imports or exports
    a def binds the defs it imports, found before any call is inlined.

    ``bound`` maps a module path to each local name it imports a def under,
    with the declaring module's path and the def's name there. A module in
    ``blocked`` imports a def along an import cycle; its calls
    are not inlined. A def import that fails, a blocked one, or one bound to
    a built-in name (PIE-S2398) or to a relationship of the module (a collision)
    ``stop``s the check before semantic analysis, as a def error does, with
    the module errors in ``facts`` and the others in ``diagnostics``."""

    bound: Mapping[str, Mapping[str, tuple[str, str]]]
    blocked: frozenset[str]
    facts: ProjectModuleDiagnosticSet
    diagnostics: tuple[Diagnostic, ...]
    stop: bool


def _def_imports(
    selected_input_index: ProjectSelectedInputIndex,
    read: list[_ReadInput | _InputOutcome],
) -> _DefImports | None:
    """Bind the def imports of an explicit-module project whose every module
    parsed and passed syntax admission, through the same exports and
    bindings as every other import, each def a declaration of its module.
    A project without a def import or export item has none."""

    from pietto._project.module_graph import def_import_collision

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
        ProjectParsedInput(path=item.entry.identity.path, script=item.script)
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
        issue.request.source_item.declaration_kind is ModuleDeclarationKind.DEF
        for surface in exports.surfaces
        for issue in surface.issues
    ) or any(
        issue.request.source_item.declaration_kind is ModuleDeclarationKind.DEF
        for environment in bindings.environments
        for issue in environment.issues
    )
    bound: dict[str, dict[str, tuple[str, str]]] = {}
    blocked: set[str] = set()
    found: list[Diagnostic] = []
    for environment in bindings.environments:
        path = environment.module.path
        relationships = {
            item.name
            for item in parsed[
                environment.module.position
            ].script.relationship_templates
        }
        for binding in environment.bindings:
            request = binding.request
            if request.source_item.declaration_kind is not ModuleDeclarationKind.DEF:
                continue
            local = binding.identity.local_binding_name
            if path in cycle_of and cycle_of[path] == cycle_of.get(
                request.target_module_path
            ):
                blocked.add(path)
            elif reserved_import_name(local):
                found.append(
                    _span_diagnostic(
                        "PIE-S2398",
                        f"Import binding {local} has the name of a built-in "
                        "function; a def cannot shadow one",
                        request.source_item.span,
                        path,
                    )
                )
            elif local in relationships:
                found.append(def_import_collision(request))
            else:
                bound.setdefault(path, {})[local] = (
                    binding.target_identity.module_path,
                    binding.target_identity.declared_name,
                )
    return _DefImports(
        bound=bound,
        blocked=frozenset(blocked),
        facts=facts,
        diagnostics=tuple(found),
        stop=stop or bool(blocked) or bool(found),
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
    ProjectTrustedSourceSnapshot | None,
    tuple[ProjectDiscoveryError, ...],
    tuple[Diagnostic, ...],
]


@dataclass(frozen=True, slots=True)
class _ReadInput:
    """A selected input that parsed, read up to its syntax admission, before
    its def calls are inlined."""

    entry: ProjectSelectedInputEntry
    trusted_source: ProjectTrustedSourceSnapshot
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
    explicit_modules: bool = False,
) -> _ReadInput | _InputOutcome:
    try:
        trusted_source = _load_trusted_source(
            pinned_root,
            selected_input,
            byte_limit=_PROJECT_SOURCE_UTF8_BYTES,
        )
    except UnicodeDecodeError:
        return _source_read_failure(
            selected_input.project_input,
            "Project source file must be valid UTF-8.",
        )
    except ProjectTrustedSourceError as error:
        return _trusted_source_failure(selected_input.project_input, error.reason)
    except OSError:
        return _source_read_failure(
            selected_input.project_input,
            "Project source file is not readable.",
        )

    if isinstance(trusted_source, Diagnostic):
        return (
            ProjectInput(path=selected_input.identity.path, status=_ERROR_STATUS),
            None,
            None,
            (),
            (trusted_source,),
        )

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

    script = parse_result.ast
    read = _ReadInput(
        entry=selected_input,
        trusted_source=trusted_source,
        ast=script,
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
        if explicit_modules:
            from pietto._project.module_graph import module_item_refusals

            refused = module_item_refusals(script)
            if refused:
                gate = tuple(sorted((*gate, *refused), key=source_order))
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
    capture_diagnostics_out: list[Diagnostic] | None = None,
    parameter_positions_out: list[Diagnostic] | None = None,
    unadmitted_paths_out: set[str] | None = None,
) -> _InputOutcome:
    """Inline the def calls of a read input, with the defs it imports in
    ``imported``, and run its capture and header checks. A ``blocked`` input
    keeps its def calls, as one that fails admission does; when it imports a
    def that ``failed`` in its own module, its own defs are still checked."""

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
            exported_defs=tuple(
                item.local_name
                for statement in read.ast.module_statements
                if type(statement) is ExportStatement
                for item in statement.items
                if item.declaration_kind is ModuleDeclarationKind.DEF
            ),
            imported_nodes=imported_spans,
        ),
        read.trusted_source,
        (),
        diagnostics,
    )


def _source_read_failure(
    selected_input: ProjectInput,
    message: str,
) -> tuple[
    ProjectInput,
    ProjectParsedInput | None,
    ProjectTrustedSourceSnapshot | None,
    tuple[ProjectDiscoveryError, ...],
    tuple[Diagnostic, ...],
]:
    return (
        ProjectInput(path=selected_input.path, status=_ERROR_STATUS),
        None,
        None,
        (
            ProjectDiscoveryError(
                ProjectDiscoveryErrorKind.SOURCE_READ,
                message,
                selected_input.path,
            ),
        ),
        (),
    )


def _trusted_source_failure(
    selected_input: ProjectInput,
    reason: ProjectTrustedSourceFailure,
) -> tuple[
    ProjectInput,
    ProjectParsedInput | None,
    ProjectTrustedSourceSnapshot | None,
    tuple[ProjectDiscoveryError, ...],
    tuple[Diagnostic, ...],
]:
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
    return (
        ProjectInput(path=selected_input.path, status=_ERROR_STATUS),
        None,
        None,
        (ProjectDiscoveryError(kind, message, path),),
        (),
    )


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
