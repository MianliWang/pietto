"""Independent checks of supplied binding witnesses and complete SQL plans."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import cast

from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
)
from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.project_query_block_ir_verification import (
    ProjectIRQueryBlockAnalysisBundle,
)
from pietto._project.project_query_block_ir import (
    ProjectIRReusedEffectiveOutput,
    _active_output_identities,
)
from pietto._project.project_ir_operators import ProjectIRLogicalOperatorKind
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleCandidateBucketStatus,
    ProjectModuleFactOccurrenceRole,
)
from pietto._project.module_relation_resolution import (
    ProjectResolvedModuleRelationReference,
)
from pietto._project.project_sql_plan import (
    ProjectSQLCause,
    ProjectSQLOriginEvidence,
    ProjectSQLPlan,
    ProjectSQLBindings,
    ProjectSQLPlanUnavailable,
    ProjectSQLPlanScope,
    ProjectSQLPlanRef,
    ProjectSQLPlanRefKind,
    ProjectSQLDefinition,
    ProjectSQLSourceBinding,
    ProjectSQLPort,
    ProjectSQLInputUse,
    ProjectSQLBoundary,
    ProjectSQLBoundaryReason,
    ProjectSQLSymbol,
    ProjectSQLSymbolNamespace,
    ProjectSQLOrigin,
    ProjectSQLOriginRole,
    ProjectSQLOriginProvenance,
    ProjectSQLSourceRealizationDemand,
    ProjectSQLExportRepresentationDemand,
    ProjectSQLSelectBlock,
    ProjectSQLProjection,
    _require_roots,
    _root_inventory,
    _owner_key,
    _dependency_symbol,
    _dependency_site,
    _binding_label,
    _binding_origin,
    _origin_index,
    _field_site,
)
from pietto.ast_nodes import (
    SourceDef,
    TableDef,
    QueryDef,
    CallExpr,
    LiteralExpr,
    NameExpr,
    DottedNameExpr,
)
from pietto.errors import Severity

__all__: tuple[str, ...] = ()

type _OriginSpec = tuple[
    ProjectSQLPlanScope | ProjectSQLPlanRef,
    ProjectSQLOriginRole,
    ProjectSQLOriginProvenance,
    ProjectDeclarationOccurrence,
    ProjectSQLCause,
    ProjectSQLOriginEvidence,
    tuple[ProjectSQLPlanRef, ...],
]


class ProjectSQLPlanVerificationIssue(StrEnum):
    NON_CONCRETE = "non_concrete"
    ROOT_CONTINUITY = "root_continuity"
    UNSUPPORTED_SHAPE = "unsupported_shape"
    STRUCTURE = "structure"
    PORTS_AND_PROJECTIONS = "ports_and_projections"
    ORIGINS = "origins"
    DEMANDS = "demands"
    SYMBOLS = "symbols"


def _same(actual: tuple[object, ...], expected: tuple[object, ...]) -> bool:
    return (
        type(actual) is tuple
        and len(actual) == len(expected)
        and all(a is b for a, b in zip(actual, expected, strict=True))
    )


def _ref(ref, scope, kind, position) -> bool:
    return (
        type(ref) is ProjectSQLPlanRef
        and ref.scope is scope
        and ref.kind is kind
        and type(ref.position) is int
        and ref.position == position
    )


def _inventory(values, cls, scope, kind) -> bool:
    return type(values) is tuple and all(
        type(value) is cls and _ref(value.ref, scope, kind, i)
        for i, value in enumerate(values)
    )


def _origin_matches(origin, spec, scope, position) -> bool:
    return (
        type(origin) is ProjectSQLOrigin
        and _ref(origin.ref, scope, ProjectSQLPlanRefKind.ORIGIN, position)
        and _same(
            (
                origin.subject,
                origin.role,
                origin.provenance,
                origin.owner,
                origin.cause,
                origin.evidence,
            ),
            spec[:6],
        )
        and _same(origin.antecedents, spec[6])
    )


def _binding_structure(
    bindings: ProjectSQLBindings, entries, dependencies, edges
) -> bool:
    scope, K = bindings.scope, ProjectSQLPlanRefKind
    definitions = bindings.definitions
    if not _inventory(
        definitions, ProjectSQLDefinition, scope, K.DEFINITION
    ) or not _same(tuple(d.entry for d in definitions), entries):
        return False
    by_owner = {_owner_key(d.entry.owner): d for d in definitions}
    source_defs = tuple(
        d for d in definitions if isinstance(d.entry.owner.definition, SourceDef)
    )
    if type(bindings.sources) is not tuple or len(bindings.sources) != len(source_defs):
        return False
    for source, definition in zip(bindings.sources, source_defs, strict=True):
        entry = definition.entry
        ast = entry.owner.definition
        if not isinstance(ast, SourceDef):
            return False
        connector = ast.connector
        if (
            not isinstance(connector, CallExpr)
            or len(connector.arguments) != 1
            or not isinstance(connector.arguments[0], LiteralExpr)
            or type(connector.arguments[0].value) is not str
        ):
            return False
        spelling = (
            connector.callee.name
            if isinstance(connector.callee, NameExpr)
            else ".".join(connector.callee.parts)
        )
        if (
            type(source) is not ProjectSQLSourceBinding
            or source.ref is not definition.ref
            or source.source is not entry
            or source.declaration is not ast
            or source.connector is not connector
            or spelling not in {"postgres.table", "mysql.table"}
            or source.module
            is not scope.completed.semantic_result.modules[entry.owner.module_position]
        ):
            return False
    if not _inventory(
        bindings.input_uses, ProjectSQLInputUse, scope, K.INPUT_USE
    ) or len(bindings.input_uses) != len(dependencies):
        return False
    origins = _origin_index(scope)
    for use, dep, edge in zip(bindings.input_uses, dependencies, edges, strict=True):
        producer, consumer = (
            by_owner[_owner_key(dep.target)],
            by_owner[_owner_key(dep.consumer)],
        )
        if (
            use.dependency is not dep
            or use.edge is not edge
            or use.producer is not producer.ref
            or use.consumer is not consumer.ref
            or producer.ref.position >= consumer.ref.position
            or edge.use.output is not producer.entry.active_output.occurrence
            or use.binding is not _dependency_symbol(dep)
            or use.origin_path is not _binding_origin(use.binding, origins)
        ):
            return False
    if not _inventory(
        bindings.boundaries, ProjectSQLBoundary, scope, K.BOUNDARY
    ) or len(bindings.boundaries) != len(bindings.input_uses):
        return False
    for boundary, use in zip(bindings.boundaries, bindings.input_uses, strict=True):
        expected = (
            ProjectSQLBoundaryReason.SOURCE_INPUT
            if isinstance(use.dependency.target.definition, SourceDef)
            else ProjectSQLBoundaryReason.NAMED_INPUT
        )
        if boundary.use is not use or boundary.reason is not expected:
            return False
    return True


def _binding_ports(bindings: ProjectSQLBindings) -> bool:
    K, scope = ProjectSQLPlanRefKind, bindings.scope
    source_ports, all_exports, input_ports = [], [], []
    for definition in bindings.definitions:
        entry = definition.entry
        identities = _active_output_identities(entry.active_output)
        fields = entry.active_properties.relational.fields
        if type(definition.exports) is not tuple or len(definition.exports) != len(
            fields
        ):
            return False
        target = (
            source_ports
            if isinstance(entry.owner.definition, SourceDef)
            else all_exports
        )
        kind = (
            K.SOURCE_PORT if isinstance(entry.owner.definition, SourceDef) else K.EXPORT
        )
        for port, actual, identity in zip(
            definition.exports, fields, identities, strict=True
        ):
            if (
                type(port) is not ProjectSQLPort
                or not _ref(port.ref, scope, kind, len(target))
                or port.owner is not definition.ref
                or port.field is not actual
                or port.identity is not identity
                or port.producer_port is not None
                or actual.output is not entry.active_output
            ):
                return False
            target.append(port)
    definitions = {d.ref: d for d in bindings.definitions}
    for use in bindings.input_uses:
        producer = definitions[use.producer]
        if type(use.ports) is not tuple or len(use.ports) != len(producer.exports):
            return False
        for port, export in zip(use.ports, producer.exports, strict=True):
            if (
                type(port) is not ProjectSQLPort
                or not _ref(port.ref, scope, K.INPUT_PORT, len(input_ports))
                or port.owner is not use.ref
                or port.producer_port is not export.ref
                or port.field is not export.field
                or port.identity is not export.identity
            ):
                return False
            input_ports.append(port)
    return (
        _same(bindings.source_ports, tuple(source_ports))
        and _same(bindings.input_ports, tuple(input_ports))
        and _same(bindings.all_exports, tuple(all_exports))
    )


def _symbols(bindings: ProjectSQLBindings) -> bool:
    if not _inventory(
        bindings.symbols, ProjectSQLSymbol, bindings.scope, ProjectSQLPlanRefKind.SYMBOL
    ):
        return False
    uses = {d.ref: [] for d in bindings.definitions}
    for use in bindings.input_uses:
        uses[use.consumer].append(use)
    expected = []
    for definition in bindings.definitions:
        local = uses[definition.ref]
        expected.extend(
            (
                definition.ref,
                ProjectSQLSymbolNamespace.RELATION_USE,
                i,
                u.ref,
                _binding_label(u.dependency),
            )
            for i, u in enumerate(local)
        )
        ports = tuple(p for u in local for p in u.ports) + definition.exports
        expected.extend(
            (
                definition.ref,
                ProjectSQLSymbolNamespace.FIELD_PORT,
                i,
                p.ref,
                p.identity.name,
            )
            for i, p in enumerate(ports)
        )
    return len(expected) == len(bindings.symbols) and all(
        s.scope is scope
        and s.namespace is namespace
        and type(s.position) is int
        and s.position == position
        and s.subject is subject
        and s.label == label
        for s, (scope, namespace, position, subject, label) in zip(
            bindings.symbols, expected, strict=True
        )
    )


def _binding_origins(bindings: ProjectSQLBindings) -> bool:
    R, P = ProjectSQLOriginRole, ProjectSQLOriginProvenance
    scope = bindings.scope
    owner = scope.selected_owner
    expected: list[_OriginSpec] = [
        (
            scope,
            R.SELECTED_OWNER,
            P.GENERATED_STRUCTURE,
            owner,
            cast(ProjectSQLCause, owner.definition),
            owner,
            (),
        )
    ]
    definitions = {d.ref: d for d in bindings.definitions}
    uses = {u.ref: u for u in bindings.input_uses}
    ports = {p.ref: p for d in bindings.definitions for p in d.exports} | {
        p.ref: p for p in bindings.input_ports
    }
    for definition in bindings.definitions:
        entry = definition.entry
        expected.append(
            (
                definition.ref,
                R.DEFINITION,
                P.GENERATED_STRUCTURE,
                entry.owner,
                cast(ProjectSQLCause, entry.owner.definition),
                entry,
                (),
            )
        )
        for i, port in enumerate(definition.exports):
            expected.append(
                (
                    port.ref,
                    R.SOURCE_PORT
                    if isinstance(entry.owner.definition, SourceDef)
                    else R.STAGE_EXPORT,
                    P.VALUE,
                    entry.owner,
                    _field_site(entry, i),
                    port.field,
                    (definition.ref,),
                )
            )
    expected.extend(
        (
            s.ref,
            R.SOURCE_DESCRIPTOR,
            P.GENERATED_STRUCTURE,
            s.source.owner,
            s.declaration,
            s.source.owner,
            (),
        )
        for s in bindings.sources
    )
    for use in bindings.input_uses:
        dep = use.dependency
        provenance = (
            P.GENERATED_STRUCTURE
            if isinstance(dep.evidence, ProjectResolvedModuleRelationReference)
            else P.MEMBERSHIP
        )
        expected.append(
            (
                use.ref,
                R.INPUT_USE,
                provenance,
                dep.consumer,
                _dependency_site(dep),
                dep,
                (use.producer,),
            )
        )
        expected.extend(
            (
                p.ref,
                R.INPUT_PORT,
                P.VALUE,
                dep.consumer,
                _dependency_site(dep),
                p.field,
                (use.ref, cast(ProjectSQLPlanRef, p.producer_port)),
            )
            for p in use.ports
        )
    for boundary in bindings.boundaries:
        dep = boundary.use.dependency
        expected.append(
            (
                boundary.ref,
                R.BOUNDARY,
                P.GENERATED_STRUCTURE,
                dep.consumer,
                _dependency_site(dep),
                dep,
                (boundary.use.ref,),
            )
        )
    for symbol in bindings.symbols:
        owner = definitions[symbol.scope].entry.owner
        if symbol.namespace is ProjectSQLSymbolNamespace.RELATION_USE:
            dep = uses[symbol.subject].dependency
            cause, evidence = _dependency_site(dep), dep
        else:
            port = ports[symbol.subject]
            cause = (
                _dependency_site(uses[port.owner].dependency)
                if port.owner in uses
                else _field_site(
                    definitions[port.owner].entry, port.field.field_position
                )
            )
            evidence = port.field
        expected.append(
            (
                symbol.ref,
                R.SYMBOL,
                P.GENERATED_STRUCTURE,
                owner,
                cause,
                evidence,
                (symbol.subject,),
            )
        )
    if len(bindings.demands) != len(bindings.sources) + len(bindings.all_exports):
        return False
    i = 0
    for source in bindings.sources:
        expected.append(
            (
                bindings.demands[i].ref,
                R.DEMAND,
                P.GENERATED_STRUCTURE,
                source.source.owner,
                source.declaration,
                source.source.owner,
                (source.ref,),
            )
        )
        i += 1
    for definition in bindings.definitions:
        if isinstance(definition.entry.owner.definition, SourceDef):
            continue
        for j, port in enumerate(definition.exports):
            expected.append(
                (
                    bindings.demands[i].ref,
                    R.DEMAND,
                    P.TYPE_PROOF,
                    definition.entry.owner,
                    _field_site(definition.entry, j),
                    port.field,
                    (port.ref,),
                )
            )
            i += 1
    return (
        type(bindings.origins) is tuple
        and len(bindings.origins) == len(expected)
        and all(
            _origin_matches(o, spec, scope, i)
            for i, (o, spec) in enumerate(zip(bindings.origins, expected, strict=True))
        )
    )


def _binding_demands(bindings: ProjectSQLBindings) -> bool:
    if type(bindings.demands) is not tuple or len(bindings.demands) != len(
        bindings.sources
    ) + len(bindings.all_exports):
        return False
    origins = tuple(
        o for o in bindings.origins if o.role is ProjectSQLOriginRole.DEMAND
    )
    if len(origins) != len(bindings.demands):
        return False
    for i, (demand, origin) in enumerate(zip(bindings.demands, origins, strict=True)):
        if (
            not _ref(demand.ref, bindings.scope, ProjectSQLPlanRefKind.DEMAND, i)
            or demand.origin is not origin.ref
            or origin.subject is not demand.ref
        ):
            return False
        if i < len(bindings.sources):
            source = bindings.sources[i]
            if (
                type(demand) is not ProjectSQLSourceRealizationDemand
                or demand.source is not source
                or demand.subject is not source.ref
            ):
                return False
        else:
            port = bindings.all_exports[i - len(bindings.sources)]
            if (
                type(demand) is not ProjectSQLExportRepresentationDemand
                or demand.subject is not port.ref
                or demand.field is not port.field
                or demand.logical_type is not port.field.evidence.resolved_type
                or demand.nullability is not port.field.effective_nullability
            ):
                return False
    return True


def _verify_bindings(bindings, completed, bundle, selected):
    Issue = ProjectSQLPlanVerificationIssue
    if type(bindings) is not ProjectSQLBindings:
        return (Issue.NON_CONCRETE,)
    try:
        _require_roots(completed, bundle, selected)
        scope = bindings.scope
        if (
            type(scope) is not ProjectSQLPlanScope
            or scope.completed is not completed
            or scope.analysis_bundle is not bundle
            or scope.selected_owner is not selected
            or not completed.ok
            or any(d.severity is Severity.ERROR for d in completed.diagnostics)
        ):
            return (Issue.ROOT_CONTINUITY,)
        entries, dependencies, edges = _root_inventory(scope)
    except (AttributeError, KeyError, TypeError, ValueError):
        return (Issue.ROOT_CONTINUITY,)
    issues = []
    for issue, check in (
        (
            Issue.STRUCTURE,
            lambda: _binding_structure(bindings, entries, dependencies, edges),
        ),
        (Issue.PORTS_AND_PROJECTIONS, lambda: _binding_ports(bindings)),
        (Issue.SYMBOLS, lambda: _symbols(bindings)),
        (Issue.ORIGINS, lambda: _binding_origins(bindings)),
        (Issue.DEMANDS, lambda: _binding_demands(bindings)),
    ):
        try:
            valid = check()
        except (AttributeError, IndexError, KeyError, TypeError, ValueError):
            valid = False
        if not valid:
            issues.append(issue)
    return tuple(issues)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLBindingVerification:
    bindings: ProjectSQLBindings | ProjectSQLPlanUnavailable
    completed: ProjectConcreteCompletedSemanticResult
    analysis_bundle: ProjectIRQueryBlockAnalysisBundle
    selected_owner: ProjectDeclarationOccurrence
    issues: tuple[ProjectSQLPlanVerificationIssue, ...] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "issues",
            _verify_bindings(
                self.bindings, self.completed, self.analysis_bundle, self.selected_owner
            ),
        )

    @property
    def verified(self) -> bool:
        return not self.issues


def verify_project_sql_bindings(
    bindings: ProjectSQLBindings | ProjectSQLPlanUnavailable,
    completed: ProjectConcreteCompletedSemanticResult,
    analysis_bundle: ProjectIRQueryBlockAnalysisBundle,
    selected_owner: ProjectDeclarationOccurrence,
) -> ProjectSQLBindingVerification:
    return ProjectSQLBindingVerification(
        bindings=bindings,
        completed=completed,
        analysis_bundle=analysis_bundle,
        selected_owner=selected_owner,
    )


def _projection_shape(entry) -> bool:
    if not isinstance(entry, ProjectIRReusedEffectiveOutput) or not isinstance(
        entry.owner.definition, (TableDef, QueryDef)
    ):
        return False
    definition = entry.owner.definition
    if any(
        (
            definition.join_clauses,
            definition.let_clause,
            definition.where_clause,
            definition.group_by_clause,
            definition.satisfying_clause,
            definition.named_windows,
            definition.qualify_clause,
            definition.distinct_clause,
            definition.order_by_clause,
            definition.limit_clause,
        )
    ) or any(
        type(i.expression) not in {NameExpr, DottedNameExpr}
        for i in definition.select_items
    ):
        return False
    facts = entry.semantic_entry.fragment.semantic_facts
    return (
        not any(
            (
                facts.let_bindings,
                facts.window_outputs,
                facts.aggregate_result_facts,
                facts.group_key_occurrences,
                facts.aggregate_grouped_clause_readiness,
                facts.named_window_namespace,
                facts.clause_dependencies,
            )
        )
        and tuple(o.kind for o in entry.semantic_entry.fragment.logical_stage.operators)
        == (
            ProjectIRLogicalOperatorKind.RELATION_INPUT,
            ProjectIRLogicalOperatorKind.FINAL_PROJECTION,
        )
        and _same(tuple(f.item for f in facts.select_facts), definition.select_items)
    )


def _whole_plan(plan: ProjectSQLPlan) -> tuple[ProjectSQLPlanVerificationIssue, ...]:
    Issue, K, R, P = (
        ProjectSQLPlanVerificationIssue,
        ProjectSQLPlanRefKind,
        ProjectSQLOriginRole,
        ProjectSQLOriginProvenance,
    )
    bindings = plan.bindings
    definitions = tuple(
        d
        for d in bindings.definitions
        if not isinstance(d.entry.owner.definition, SourceDef)
    )
    if any(not _projection_shape(d.entry) for d in definitions):
        return (Issue.UNSUPPORTED_SHAPE,)
    if plan.scope is not bindings.scope or any(
        not _same(getattr(plan, name), getattr(bindings, name))
        for name in (
            "sources",
            "input_uses",
            "source_ports",
            "input_ports",
            "all_exports",
            "boundaries",
            "symbols",
            "demands",
        )
    ):
        return (Issue.STRUCTURE,)
    selected = tuple(
        d for d in definitions if d.entry.owner is plan.scope.selected_owner
    )
    if len(selected) != 1 or not _same(plan.exports, selected[0].exports):
        return (Issue.PORTS_AND_PROJECTIONS,)
    if type(plan.blocks) is not tuple or len(plan.blocks) != len(definitions):
        return (Issue.STRUCTURE,)
    uses = {d.ref: [] for d in definitions}
    for use in plan.input_uses:
        uses[use.consumer].append(use)
    boundaries = {b.use.ref: b for b in bindings.boundaries}
    symbols = {s.subject: s for s in bindings.symbols}
    expected_origins = []
    projection_position = 0
    for block, definition in zip(plan.blocks, definitions, strict=True):
        entry = definition.entry
        assert isinstance(entry, ProjectIRReusedEffectiveOutput)
        if (
            type(block) is not ProjectSQLSelectBlock
            or block.ref is not definition.ref
            or block.selected is not entry
            or len(uses[definition.ref]) != 1
        ):
            return (Issue.STRUCTURE,)
        use = uses[definition.ref][0]
        if block.boundary is not boundaries[use.ref] or not _same(
            block.operators, entry.semantic_entry.fragment.logical_stage.operators
        ):
            return (Issue.STRUCTURE,)
        expected_origins.append(
            (
                block.ref,
                R.SELECT_BLOCK,
                P.GENERATED_STRUCTURE,
                entry.owner,
                entry.owner.definition,
                entry,
                (block.boundary.ref,),
            )
        )
        inputs = {p.field.evidence.name: p for p in use.ports}
        facts = entry.semantic_entry.fragment.semantic_facts.select_facts
        if len(facts) != len(definition.exports):
            return (Issue.PORTS_AND_PROJECTIONS,)
        for semantic, export in zip(facts, definition.exports, strict=True):
            projection = plan.projections[projection_position]
            if len(semantic.references) != 1:
                return (Issue.PORTS_AND_PROJECTIONS,)
            reference = semantic.references[0]
            port = (
                inputs.get(reference.input_field.name)
                if reference.input_field is not None
                else None
            )
            if (
                port is None
                or type(projection) is not ProjectSQLProjection
                or not _ref(
                    projection.ref, plan.scope, K.PROJECTION, projection_position
                )
                or projection.block is not block.ref
                or projection.input_use is not use.ref
                or projection.source_port is not port.producer_port
                or projection.input_port is not port.ref
                or projection.export is not export.ref
                or projection.semantic is not semantic
                or projection.symbol is not symbols[port.ref]
                or projection.symbol.scope is not block.ref
                or reference.input_field is not port.field.evidence
                or semantic.field is not export.field.evidence
                or reference.owner is not entry.owner
                or reference.expression is not semantic.item.expression
                or reference.status is not ProjectModuleCandidateBucketStatus.CONCRETE
                or reference.role is not ProjectModuleFactOccurrenceRole.SELECT_VALUE
                or reference.let_candidates
                or reference.selected_output_candidates
                or semantic.aggregate_result_fact is not None
            ):
                return (Issue.PORTS_AND_PROJECTIONS,)
            expected_origins.append(
                (
                    projection.ref,
                    R.PROJECTION,
                    P.VALUE,
                    entry.owner,
                    semantic.item,
                    semantic,
                    (port.ref,),
                )
            )
            expected_origins.append(
                (
                    export.ref,
                    R.EXPORT,
                    P.VALUE,
                    entry.owner,
                    semantic.item,
                    export.field,
                    (projection.ref,),
                )
            )
            projection_position += 1
    if (
        type(plan.projections) is not tuple
        or len(plan.projections) != projection_position
    ):
        return (Issue.PORTS_AND_PROJECTIONS,)
    start = len(bindings.origins)
    if (
        not _same(plan.origins[:start], bindings.origins)
        or len(plan.origins) != start + len(expected_origins)
        or any(
            not _origin_matches(o, spec, plan.scope, start + i)
            for i, (o, spec) in enumerate(
                zip(plan.origins[start:], expected_origins, strict=True)
            )
        )
    ):
        return (Issue.ORIGINS,)
    return ()


def _verify(plan, completed, bundle, selected):
    Issue = ProjectSQLPlanVerificationIssue
    if type(plan) is not ProjectSQLPlan:
        return (Issue.NON_CONCRETE,)
    try:
        issues = _verify_bindings(plan.bindings, completed, bundle, selected)
        if issues:
            return issues
        return _whole_plan(plan)
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        return (Issue.STRUCTURE,)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLPlanVerification:
    plan: ProjectSQLPlan | ProjectSQLPlanUnavailable
    completed: ProjectConcreteCompletedSemanticResult
    analysis_bundle: ProjectIRQueryBlockAnalysisBundle
    selected_owner: ProjectDeclarationOccurrence
    issues: tuple[ProjectSQLPlanVerificationIssue, ...] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "issues",
            _verify(
                self.plan, self.completed, self.analysis_bundle, self.selected_owner
            ),
        )

    @property
    def verified(self) -> bool:
        return not self.issues


def verify_project_sql_plan(
    plan: ProjectSQLPlan | ProjectSQLPlanUnavailable,
    completed: ProjectConcreteCompletedSemanticResult,
    analysis_bundle: ProjectIRQueryBlockAnalysisBundle,
    selected_owner: ProjectDeclarationOccurrence,
) -> ProjectSQLPlanVerification:
    return ProjectSQLPlanVerification(
        plan=plan,
        completed=completed,
        analysis_bundle=analysis_bundle,
        selected_owner=selected_owner,
    )
