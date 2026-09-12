"""Independent checks of supplied binding witnesses and complete SQL plans."""

from __future__ import annotations

from math import isfinite
from pietto.semantic.model import TypeKind, ValueType
from pietto._project import project_sql_plan_literals as literals

from pietto._project import project_sql_plan_aggregation as aggregation
from pietto._project import project_sql_plan_windows as windows
from pietto._project import project_sql_plan_results as results
from pietto._project import project_sql_plan_sets as sets

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
    ProjectIRCompletedSetOperationOutput,
    ProjectIRCompletedQueryBlockOutput,
    ProjectIRReboundExistingOutput,
    ProjectIRQueryBlockOperatorExtensionKind,
    _active_output_identities,
)
from pietto._project.project_ir_operators import ProjectIRLogicalOperatorKind
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleCandidateBucketStatus,
    ProjectModuleLetBindingFact,
    ProjectModuleWhereReferenceRole,
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
from pietto.ast_nodes import SelectItem, WindowExpr
from pietto.ast_nodes import (
    SourceDef,
    SetRelationDef,
    TableDef,
    QueryDef,
    CallExpr,
    LiteralExpr,
    NameExpr,
    DottedNameExpr,
)
from pietto.errors import Severity

from pietto._project import project_sql_plan_expressions as row
from pietto._project.project_scalar_namespaces import ProjectScalarNamespaceStage
from pietto._project import project_sql_plan_joins as joining
from pietto.ast_nodes import AuthoredJoinKind
from pietto._project.project_join_conditions import (
    ProjectJoinReferenceState,
    ProjectJoinConditionState,
)
from pietto._project.project_scalar_references import (
    ProjectScalarReferenceResolution,
    _source_field_parts,
)
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleExpressionReferenceFact,
)
from pietto._project.let_scope_facts import ProjectLetScopeFactsStatus
from pietto._project.project_final_outputs import (
    ProjectNoJoinScalarExpression,
    ProjectRelationOrderDirection,
)
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleClauseDependencyFact,
    ProjectModuleOrderReferenceFact,
)
from pietto._project.project_row_equivalence import ProjectRowEquivalenceInput
from pietto._project.project_sql_plan import _operators
from pietto._project.project_joined_row_filter import _SQL_ROW_RETENTION_EFFECTS
from pietto.ast_nodes import (
    UnaryExpr,
    BinaryExpr,
    ComparisonExpr,
    IsNullExpr,
    BetweenExpr,
    LetBinding,
)
from pietto.semantic.model import ValueTypeKind


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
    LITERAL_TRANSPORT = "literal_transport"
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
        (type(value) in cls if isinstance(cls, tuple) else type(value) is cls)
        and _ref(value.ref, scope, kind, i)
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
        for position, (port, actual, identity) in enumerate(
            zip(definition.exports, fields, identities, strict=True)
        ):
            if (
                type(port) is not ProjectSQLPort
                or not _ref(port.ref, scope, kind, len(target))
                or port.owner is not definition.ref
                or port.field is not actual
                or port.identity is not identity
                or port.producer_port is not None
                or actual.output is not entry.active_output
                or type(actual.field_position) is not int
                or actual.field_position != position
                or type(identity.field_position) is not int
                or identity.field_position != position
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


def _projection_shape(entry, aggregate=None, window=None) -> bool:
    definition = entry.owner.definition
    if not isinstance(definition, (TableDef, QueryDef)):
        return False
    expected: list[
        ProjectIRLogicalOperatorKind | ProjectIRQueryBlockOperatorExtensionKind
    ] = [] if definition.join_clauses else [ProjectIRLogicalOperatorKind.RELATION_INPUT]
    if definition.where_clause is not None:
        expected.append(ProjectIRLogicalOperatorKind.ROW_FILTER)
    if aggregate is not None:
        expected.append(ProjectIRLogicalOperatorKind.GROUP_AGGREGATE)
        if definition.satisfying_clause is not None:
            expected.append(ProjectIRLogicalOperatorKind.RESULT_FILTER)
    elif (
        definition.group_by_clause is not None
        or definition.satisfying_clause is not None
    ):
        return False
    if window is not None:
        expected.append(ProjectIRLogicalOperatorKind.WINDOW_EVALUATION)
        if window.qualify is not None:
            expected.append(ProjectIRQueryBlockOperatorExtensionKind.QUALIFY)
    expected.append(ProjectIRLogicalOperatorKind.FINAL_PROJECTION)
    if definition.distinct_clause is not None:
        expected.append(ProjectIRQueryBlockOperatorExtensionKind.DISTINCT)
    if definition.order_by_clause is not None:
        expected.append(ProjectIRLogicalOperatorKind.RELATION_ORDERING)
    if definition.limit_clause is not None:
        expected.append(ProjectIRLogicalOperatorKind.LIMIT)
    return tuple(o.kind for o in _operators(entry)) == tuple(expected)


def _join_structure(plan) -> bool:
    K = ProjectSQLPlanRefKind
    for values, cls, kind in (
        (plan.joins, joining.ProjectSQLJoin, K.JOIN),
        (plan.join_inputs, joining.ProjectSQLJoinInput, K.JOIN_INPUT),
        (plan.join_ports, joining.ProjectSQLJoinPort, K.JOIN_PORT),
        (
            plan.relationship_matches,
            joining.ProjectSQLRelationshipMatch,
            K.RELATIONSHIP_MATCH,
        ),
        (plan.join_tails, joining.ProjectSQLJoinTail, K.JOIN_TAIL),
        (plan.single_matches, joining.ProjectSQLSingleMatch, K.SINGLE_MATCH),
        (
            plan.single_match_proofs,
            joining.ProjectSQLSingleMatchProof,
            K.SINGLE_MATCH_PROOF,
        ),
    ):
        if not _inventory(values, cls, plan.scope, kind):
            return False
    root = plan.scope.analysis_bundle.root
    definitions = {id(d.entry.owner): d for d in plan.bindings.definitions}
    bindings = {id(use.edge): use for use in plan.bindings.input_uses}
    rows = {
        AuthoredJoinKind.INNER: joining.ProjectSQLJoinRows.MATCHED_PAIRS,
        AuthoredJoinKind.LEFT: joining.ProjectSQLJoinRows.LEFT_PRESERVED,
        AuthoredJoinKind.CROSS: joining.ProjectSQLJoinRows.CARTESIAN_PAIRS,
        AuthoredJoinKind.RIGHT: joining.ProjectSQLJoinRows.RIGHT_PRESERVED,
        AuthoredJoinKind.FULL: joining.ProjectSQLJoinRows.BOTH_PRESERVED,
        AuthoredJoinKind.SEMI: joining.ProjectSQLJoinRows.LEFT_EXISTS,
        AuthoredJoinKind.ANTI: joining.ProjectSQLJoinRows.LEFT_NOT_EXISTS,
    }
    by_image = {}
    ports_by_ref = {p.ref: p for p in plan.join_ports}
    joins_position = input_position = port_position = equality_position = (
        tail_position
    ) = 0
    for definition in plan.bindings.definitions:
        images = joining.join_images(root, definition.entry)
        if not images:
            continue
        for position, image in enumerate(images):
            value = plan.joins[joins_position]
            joins_position += 1
            if (
                value.source is not image
                or value.definition is not definition.ref
                or type(value.position) is not int
                or value.position != position
                or value.kind is not image.source.use.kind
                or value.rows is not rows[value.kind]
            ):
                return False
            local_inputs = plan.join_inputs[input_position : input_position + 2]
            input_position += 2
            if len(local_inputs) != 2 or not _same(
                value.inputs, tuple(item.ref for item in local_inputs)
            ):
                return False
            match_ports = []
            keys = joining.condition_field_keys(image)
            for ordinal, (given, source) in enumerate(
                zip(local_inputs, image.inputs, strict=True)
            ):
                previous = joining.input_predecessor(source, images[:position])
                if source.producer is not None:
                    producer = definitions[id(source.producer)]
                    if source.use.output is not producer.entry.active_output.occurrence:
                        return False
                    upstream = producer.exports
                    producer_ref, previous_ref = producer.ref, None
                else:
                    previous_plan = by_image[id(previous)]
                    upstream = tuple(ports_by_ref[ref] for ref in previous_plan.outputs)
                    producer_ref, previous_ref = None, previous_plan.ref
                bound = bindings.get(id(source))
                if (
                    given.join is not value.ref
                    or given.source is not source
                    or type(given.ordinal) is not int
                    or given.ordinal != ordinal
                    or given.producer is not producer_ref
                    or given.predecessor is not previous_ref
                    or given.binding_use is not (None if bound is None else bound.ref)
                    or len(upstream) != len(source.source_properties.fields)
                ):
                    return False
                expected_ports = plan.join_ports[
                    port_position : port_position + len(upstream)
                ]
                port_position += len(upstream)
                if len(expected_ports) != len(upstream) or not _same(
                    given.ports, tuple(p.ref for p in expected_ports)
                ):
                    return False
                for i, (port, previous_port, original, key) in enumerate(
                    zip(
                        expected_ports,
                        upstream,
                        source.source_properties.fields,
                        keys[ordinal],
                        strict=True,
                    )
                ):
                    field = previous_port.field
                    nulling = (
                        field.nulling_joins
                        if isinstance(field, joining.ProjectIRJoinedRowField)
                        else ()
                    )
                    if (
                        port.block is not value.ref
                        or port.kind is not joining.ProjectSQLJoinPortKind.MATCH
                        or type(port.position) is not int
                        or port.position != i
                        or port.input is not given.ref
                        or port.source is not previous_port.ref
                        or port.original is not original
                        or port.field is not field
                        or port.key is not (field if key is None else key)
                        or not _same(port.nulling, nulling)
                    ):
                        return False
                match_ports.extend(expected_ports)
            matches = joining.base_matches(image)
            provided_matches = plan.relationship_matches[
                equality_position : equality_position + len(matches)
            ]
            equality_position += len(matches)
            if len(provided_matches) != len(matches) or not _same(
                value.equalities, tuple(m.ref for m in provided_matches)
            ):
                return False
            for equality, (source, guarantee, left, right) in zip(
                provided_matches, matches, strict=True
            ):
                comparison = (
                    source.correspondence
                    if isinstance(source, joining.ProjectIRJoinMatchFieldPair)
                    else source
                )
                left_ref, right_ref = (
                    local_inputs[0].ports[left],
                    local_inputs[1].ports[right],
                )
                authored = (
                    (left_ref, right_ref)
                    if comparison.authored_left.endpoint is guarantee.direction.source
                    else (right_ref, left_ref)
                )
                if (
                    equality.join is not value.ref
                    or equality.source is not source
                    or equality.guarantee is not guarantee
                    or equality.left is not left_ref
                    or equality.right is not right_ref
                    or not _same(equality.authored_operands, authored)
                ):
                    return False
            condition = image.condition
            if (
                condition.ready is not True
                or condition.state is not ProjectJoinConditionState.READY
                or type(condition.use.identity.join_position) is not int
                or any(
                    type(field.position) is not int or field.position != i
                    for i, field in enumerate(condition.environment.fields)
                )
            ):
                return False
            if condition.expression is None:
                if value.on is not None or value.site is not None:
                    return False
            else:
                site = value.site
                if (
                    type(site) is not row.ProjectSQLMatchSite
                    or site.owner is not definition.entry.owner
                    or site.block is not value.ref
                    or site.role is not row.ProjectSQLExpressionRole.MATCH
                    or type(site.ordinal) is not int
                    or site.ordinal != condition.use.identity.join_position
                    or site.occurrence is not condition.use.clause.on_clause
                    or site.evidence is not condition
                    or not _same(site.references, condition.references)
                    or value.on is None
                ):
                    return False
            outputs = plan.join_ports[
                port_position : port_position + len(image.output.row_shape.fields)
            ]
            port_position += len(outputs)
            if len(outputs) != len(image.output.row_shape.fields) or not _same(
                value.outputs, tuple(p.ref for p in outputs)
            ):
                return False
            for i, (port, original, current) in enumerate(
                zip(
                    outputs,
                    image.source.output.row_shape.fields,
                    image.output.row_shape.fields,
                    strict=True,
                )
            ):
                if (
                    port.block is not value.ref
                    or port.kind is not joining.ProjectSQLJoinPortKind.OUTPUT
                    or type(port.position) is not int
                    or port.position != i
                    or port.input is not None
                    or port.source is not match_ports[i].ref
                    or port.original is not original
                    or port.field is not current
                    or port.key is not current
                    or not _same(port.nulling, current.nulling_joins)
                ):
                    return False
            entry = definition.entry
            properties = (
                image.source_properties
                if entry.join_prefix is None
                else next(
                    (
                        p.relational
                        for p in entry.join_properties
                        if p.output is image.output
                    ),
                    None,
                )
            )
            if value.properties is not properties:
                return False
            by_image[id(image)] = value
        tail = plan.join_tails[tail_position]
        tail_position += 1
        source = joining.joined_tail(definition.entry)
        if source is None:
            return False
        finals = tuple(
            image
            for image in images
            if image.source.output is source.joined_semantics.final_output
        )
        if len(finals) != 1:
            return False
        final = by_image[id(finals[0])]
        fields = source.joined_semantics.namespaces.binding_environment.visible_fields
        field_ports = {
            id(old): ref
            for old, ref in zip(
                final.source.source.output.row_shape.fields, final.outputs, strict=True
            )
        }
        if (
            tail.definition is not definition.ref
            or tail.source is not source
            or tail.join is not final.ref
            or not _same(tail.fields, fields)
            or not _same(
                tail.ports,
                tuple(field_ports[id(field.source_field)] for field in fields),
            )
        ):
            return False
    if (
        joins_position,
        input_position,
        port_position,
        equality_position,
        tail_position,
    ) != (
        len(plan.joins),
        len(plan.join_inputs),
        len(plan.join_ports),
        len(plan.relationship_matches),
        len(plan.join_tails),
    ):
        return False
    return _single_matches(plan)


def _single_matches(plan) -> bool:
    expected = tuple(
        source
        for source in plan.scope.analysis_bundle.root.requirements
        if source.owner_entry is not None
        and any(source.owner_entry is d.entry for d in plan.bindings.definitions)
    )
    if len(expected) != len(plan.single_matches):
        return False
    definitions = {id(d.entry): d.ref for d in plan.bindings.definitions}
    proofs = {p.ref: p for p in plan.single_match_proofs}
    visited = []

    def join_for(source):
        matches = tuple(
            j for j in plan.joins if j.source is source or j.source.source is source
        )
        if len(matches) != 1:
            raise ValueError("Obligation requires one retained matching boundary.")
        return matches[0]

    for value, retained in zip(plan.single_matches, expected, strict=True):
        assessment = retained.assessment
        joins = tuple(join_for(source) for source in retained.boundaries)
        if (
            value.source is not retained
            or value.request is not assessment.request
            or value.assessment is not assessment
            or value.diagnostic is not assessment.diagnostic
            or value.downstream_enforcement_required
            is not assessment.downstream_enforcement_required
            or not _same(value.joins, tuple(j.ref for j in joins))
            or type(value.input_pairs) is not tuple
            or len(value.input_pairs) != len(joins)
            or any(
                not _same(pair, join.inputs)
                for pair, join in zip(value.input_pairs, joins, strict=True)
            )
            or type(value.proofs) is not tuple
            or len(value.proofs) != len(retained.proofs)
        ):
            return False
        pending = [
            (source, ref, None)
            for source, ref in reversed(
                tuple(zip(retained.proofs, value.proofs, strict=True))
            )
        ]
        while pending:
            source, ref, parent = pending.pop()
            proof = proofs[ref]
            visited.append(proof)
            if (
                proof.source is not source
                or proof.obligation is not value.ref
                or proof.parent is not parent
                or not _same(
                    proof.joins,
                    tuple(join_for(boundary).ref for boundary in source.boundaries),
                )
                or not _same(
                    proof.producers,
                    tuple(definitions[id(entry)] for entry in source.producers),
                )
                or type(proof.children) is not tuple
                or len(proof.children) != len(source.children)
            ):
                return False
            pending.extend(
                (child, ref, proof.ref)
                for child, ref in reversed(
                    tuple(zip(source.children, proof.children, strict=True))
                )
            )
    return _same(tuple(visited), plan.single_match_proofs)


def _row_site(
    site,
    entry,
    authority,
    block,
    role,
    ordinal,
    occurrence,
    evidence,
    references,
    bindings,
) -> bool:
    if (
        site.owner is not entry.owner
        or site.block is not block.ref
        or site.role is not role
        or type(site.ordinal) is not int
        or site.ordinal != ordinal
        or site.occurrence is not occurrence
        or site.evidence is not evidence
        or not _same(site.references, references)
    ):
        return False
    if isinstance(site, windows.ProjectSQLQualifySite):
        view = windows.authority(entry)
        if isinstance(evidence, windows.ProjectNoJoinQualify):
            context = evidence.input_context
            if (
                view is None
                or not isinstance(view.root, windows.ProjectConcreteNoJoinReplay)
                or context is None
                or context.owner is not entry.owner
                or context.scope is not view.root.window_scope
                or context.input_schema is not view.root.input_schema
                or context.let_scope is not view.root.let_scope
                or context.base_schema is not view.root.base_state.schema
                or not windows.project_targets_valid(context)
            ):
                return False
        return (
            role is row.ProjectSQLExpressionRole.QUALIFY
            and view is not None
            and view.qualify is evidence
            and occurrence is entry.owner.definition.qualify_clause
            and (site.aggregate is None)
            is (aggregation.authority(block.ref.scope.completed, entry) is None)
        )
    if isinstance(site, aggregation.ProjectSQLAggregateSite):
        if role is row.ProjectSQLExpressionRole.AGGREGATE_ARGUMENT:
            if (
                not isinstance(occurrence, SelectItem)
                or not isinstance(occurrence.expression, CallExpr)
                or len(occurrence.expression.arguments) != 1
            ):
                return False
            if site.expression is not occurrence.expression.arguments[0]:
                return False
            if isinstance(evidence, aggregation.ProjectAggregateExpressionAnalysis):
                return (
                    isinstance(authority, row.ProjectSQLRowAuthority)
                    and evidence.definition is entry.owner.definition
                    and evidence.item is occurrence
                    and evidence.input_schema is authority.input_schema
                    and evidence.let_scope is authority.let_scope
                )
            return (
                isinstance(authority, row.ProjectSQLJoinedRowAuthority)
                and isinstance(evidence, row.ProjectConcreteJoinedNamespaceExpression)
                and evidence.namespace is authority.namespaces.post_let
                and evidence.expression is site.expression
            )
        return (
            role is row.ProjectSQLExpressionRole.SATISFYING
            and site.expression is occurrence.expression
            and site.authority.satisfying is evidence
        )
    if isinstance(authority, row.ProjectSQLJoinedRowAuthority):
        if (
            type(site) is not row.ProjectSQLJoinedSite
            or site.namespace is not evidence.namespace
            or site.namespace.binding_environment is not authority.binding_environment
        ):
            return False
        if isinstance(evidence, row.ProjectJoinedLetValue):
            return (
                evidence.occurrence is authority.namespaces.occurrences[ordinal]
                and evidence.namespace
                is authority.namespaces.binding_namespaces[ordinal]
                and evidence.occurrence.binding is occurrence
                and type(site.namespace.binding_ordinal) is int
                and site.namespace.binding_ordinal == ordinal
                and site.namespace.stage is ProjectScalarNamespaceStage.LET_BINDING
                and _same(site.namespace.let_values, authority.lets[:ordinal])
            )
        return (
            evidence.namespace is authority.namespaces.post_let
            and site.namespace.stage is ProjectScalarNamespaceStage.POST_LET
            and site.namespace.binding_ordinal is None
            and _same(site.namespace.let_values, authority.lets)
            and evidence.expression is occurrence.expression
        )
    if type(site) is not row.ProjectSQLExpressionSite:
        return False
    prefix = (
        bindings[:ordinal] if role is row.ProjectSQLExpressionRole.LET else bindings
    )
    if (
        site.input_schema is not authority.input_schema
        or site.let_scope is not authority.let_scope
        or not _same(site.let_prefix, prefix)
    ):
        return False
    if isinstance(evidence, ProjectNoJoinScalarExpression):
        return (
            evidence.owner is entry.owner
            and evidence.input_schema is authority.input_schema
            and evidence.let_scope is authority.let_scope
            and evidence.expression is occurrence.expression
        )
    if isinstance(evidence, ProjectModuleLetBindingFact):
        return (
            evidence.scope_facts is authority.let_scope
            and evidence.value_type
            is authority.let_scope.value_types.get(occurrence.name)
        )
    return (
        evidence.owner is entry.owner
        and evidence.input_schema is authority.input_schema
        and evidence.let_scope is authority.let_scope
    )


def _aggregate_authority_matches(actual, expected):
    if type(actual) is not aggregation.ProjectSQLAggregationAuthority:
        return False
    if any(
        getattr(actual, name) is not getattr(expected, name)
        for name in ("source", "mode", "context", "properties", "satisfying")
    ):
        return False
    if any(
        not _same(getattr(actual, name), getattr(expected, name))
        for name in (
            "keys",
            "aggregates",
            "output_keys",
            "outputs",
            "risks",
            "satisfying_references",
        )
    ):
        return False
    return all(
        len(getattr(actual, name)) == len(getattr(expected, name))
        and all(
            _same(a, b) for a, b in zip(getattr(actual, name), getattr(expected, name))
        )
        for name in ("key_references", "argument_references")
    )


def _aggregate_structure(plan):
    K = ProjectSQLPlanRefKind
    for values, cls, kind in (
        (plan.aggregations, aggregation.ProjectSQLAggregation, K.AGGREGATION),
        (plan.group_keys, aggregation.ProjectSQLGroupKey, K.GROUP_KEY),
        (plan.aggregates, aggregation.ProjectSQLAggregate, K.AGGREGATE),
        (
            plan.aggregate_projections,
            aggregation.ProjectSQLAggregateProjection,
            K.AGGREGATE_PROJECTION,
        ),
        (plan.aggregate_risks, aggregation.ProjectSQLAggregateRisk, K.AGGREGATE_RISK),
    ):
        if not _inventory(values, cls, plan.scope, kind):
            return False
    ports = {p.ref: p for p in plan.stage_ports}
    blocks = {b.ref: b for b in plan.blocks}
    stages = {a.definition: a for a in plan.aggregations}
    if len(stages) != len(plan.aggregations):
        return False
    key_count = value_count = projection_count = risk_count = stage_count = 0
    for definition in plan.bindings.definitions:
        original = aggregation.authority(plan.scope.completed, definition.entry)
        stage = stages.get(definition.ref)
        if original is None:
            if stage is not None:
                return False
            continue
        if stage is None or not _aggregate_authority_matches(stage.authority, original):
            return False
        if plan.aggregations[stage_count] is not stage:
            return False
        stage_count += 1
        block = blocks.get(stage.block)
        if (
            block is None
            or block.definition is not definition.ref
            or block.kind is not row.ProjectSQLStageKind.AGGREGATE
            or stage.mode is not original.mode
            or not _same(stage.inputs, block.inputs)
        ):
            return False
        empty = (
            aggregation.ProjectSQLAggregateEmptyInput.ONE_GLOBAL_ROW
            if original.mode is aggregation.ProjectJoinedAggregationMode.GLOBAL
            else aggregation.ProjectSQLAggregateEmptyInput.NO_GROUPS
        )
        if stage.empty_input is not empty:
            return False
        keys = plan.group_keys[key_count : key_count + len(original.keys)]
        key_count += len(original.keys)
        values = plan.aggregates[value_count : value_count + len(original.aggregates)]
        value_count += len(original.aggregates)
        if (
            len(keys) != len(original.keys)
            or len(values) != len(original.aggregates)
            or not values
        ):
            return False
        if (
            not _same(stage.keys, tuple(k.ref for k in keys))
            or not _same(stage.aggregates, tuple(v.ref for v in values))
            or not _same(stage.results, tuple(v.result for v in (*keys, *values)))
        ):
            return False
        for i, (key, source, refs) in enumerate(
            zip(keys, original.keys, original.key_references, strict=True)
        ):
            incoming, result = ports.get(key.input), ports.get(key.result)
            if (
                not refs
                or incoming is None
                or result is None
                or key.aggregation is not stage.ref
                or type(key.position) is not int
                or key.position != i
                or key.source is not source
                or key.reference is not refs[0]
            ):
                return False
            reference = refs[0]
            if isinstance(source, aggregation.ProjectGroupKeyFact):
                if (
                    not isinstance(reference, ProjectModuleExpressionReferenceFact)
                    or reference.owner is not definition.entry.owner
                    or reference.role is not ProjectModuleFactOccurrenceRole.GROUP_KEY
                    or type(reference.container_ordinal) is not int
                    or reference.container_ordinal != i
                    or type(reference.dependency_ordinal) is not int
                    or reference.dependency_ordinal != 0
                    or reference.status
                    is not ProjectModuleCandidateBucketStatus.CONCRETE
                ):
                    return False
                if (
                    reference.input_field is not None
                    and reference.input_field is not source.input_field
                ):
                    return False
            elif (
                type(source.source_ordinal) is not int
                or source.source_ordinal != i
                or not isinstance(
                    original.source, aggregation.ProjectConcreteJoinedAggregation
                )
                or source.input_filter is not original.source.input_filter
                or not isinstance(refs[-1], ProjectScalarReferenceResolution)
                or refs[-1].target is not source.field_semantics.scalar_field
            ):
                return False
            target = row.reference_key(reference)
            evidence = (
                source.input_field
                if isinstance(source, aggregation.ProjectGroupKeyFact)
                else source.value_type
            )
            if (
                incoming.block is not block.ref
                or incoming.kind is not row.ProjectSQLStagePortKind.INPUT
                or incoming.key is not target
                or result.block is not block.ref
                or result.kind is not row.ProjectSQLStagePortKind.EXPORT
                or result.key is not source
                or result.source is not key.ref
                or result.type_evidence is not evidence
            ):
                return False
            if (
                source.item
                is not definition.entry.owner.definition.group_by_clause.items[i]
                or row.reference_expression(refs[0]) is not source.item.key
            ):
                return False
        for i, (value, source) in enumerate(
            zip(values, original.aggregates, strict=True)
        ):
            result = ports.get(value.result)
            call = source.item.expression
            if (
                result is None
                or not isinstance(call, CallExpr)
                or value.source is not source
                or value.aggregation is not stage.ref
                or type(value.position) is not int
                or value.position != i
                or len(value.arguments) != len(call.arguments)
                or value.value_type is not source.result_value_type
            ):
                return False
            if (
                result.block is not block.ref
                or result.kind is not row.ProjectSQLStagePortKind.EXPORT
                or result.key is not source.item
                or result.source is not value.ref
                or result.type_evidence is not source.result_value_type
            ):
                return False
        expected_sites = [
            (row.ProjectSQLExpressionRole.AGGREGATE_ARGUMENT, i, source.item)
            for i, source in enumerate(original.aggregates)
            if aggregation.arguments(source)
        ]
        if original.satisfying is not None:
            expected_sites.append(
                (
                    row.ProjectSQLExpressionRole.SATISFYING,
                    0,
                    definition.entry.owner.definition.satisfying_clause,
                )
            )
        sites = tuple(
            site
            for site in plan.expression_sites
            if isinstance(site, aggregation.ProjectSQLAggregateSite)
            and site.aggregation is stage.ref
        )
        if len(sites) != len(expected_sites):
            return False
        for site, (role, i, occurrence) in zip(sites, expected_sites, strict=True):
            if (
                site.authority is not stage.authority
                or site.owner is not definition.entry.owner
                or site.role is not role
                or type(site.ordinal) is not int
                or site.ordinal != i
                or site.occurrence is not occurrence
            ):
                return False
        projections = plan.aggregate_projections[
            projection_count : projection_count + len(original.outputs)
        ]
        projection_count += len(original.outputs)
        rows = row.row_authority(plan.scope.completed, definition.entry)
        if rows is None or len(projections) != sum(
            not isinstance(f.item.expression, WindowExpr) for f in rows.selections
        ):
            return False
        for projection, source, key, export, semantic in zip(
            projections,
            original.outputs,
            original.output_keys,
            tuple(
                export
                for export, semantic in zip(
                    definition.exports, rows.selections, strict=True
                )
                if not isinstance(semantic.item.expression, WindowExpr)
            ),
            tuple(
                semantic
                for semantic in rows.selections
                if not isinstance(semantic.item.expression, WindowExpr)
            ),
            strict=True,
        ):
            port = ports.get(projection.input)
            projection_block = blocks.get(projection.block)
            if (
                port is None
                or projection_block is None
                or projection_block.definition is not definition.ref
                or projection_block.kind is not row.ProjectSQLStageKind.PROJECTION
                or projection.aggregation is not stage.ref
                or projection.semantic is not semantic
                or projection.source is not source
                or projection.export is not export.ref
                or port.block is not projection.block
                or port.kind is not row.ProjectSQLStagePortKind.INPUT
                or port.key is not key
            ):
                return False
            expected_field = (
                definition.entry.semantic_entry.fields[
                    semantic.selected_output_ordinal
                ].field
                if isinstance(definition.entry, ProjectIRCompletedQueryBlockOutput)
                else semantic.field
            )
            if export.field.evidence is not expected_field:
                return False
        risks = plan.aggregate_risks[risk_count : risk_count + len(original.risks)]
        risk_count += len(original.risks)
        if len(risks) != len(original.risks) or any(
            r.aggregation is not stage.ref or r.source is not source
            for r, source in zip(risks, original.risks, strict=True)
        ):
            return False
    return (stage_count, key_count, value_count, projection_count, risk_count) == (
        len(plan.aggregations),
        len(plan.group_keys),
        len(plan.aggregates),
        len(plan.aggregate_projections),
        len(plan.aggregate_risks),
    )


def _window_structure(plan):
    K = ProjectSQLPlanRefKind
    for values, cls, kind in (
        (plan.windows, windows.ProjectSQLWindow, K.WINDOW),
        (plan.window_uses, windows.ProjectSQLWindowUse, K.WINDOW_USE),
        (plan.window_arguments, windows.ProjectSQLWindowArgument, K.WINDOW_ARGUMENT),
        (plan.window_policies, windows.ProjectSQLWindowPolicy, K.WINDOW_POLICY),
        (
            plan.window_projections,
            windows.ProjectSQLWindowProjection,
            K.WINDOW_PROJECTION,
        ),
    ):
        if not _inventory(values, cls, plan.scope, kind):
            return False
    ports = {p.ref: p for p in plan.stage_ports}
    blocks = {b.ref: b for b in plan.blocks}
    window_position = use_position = argument_position = policy_position = (
        projection_position
    ) = 0
    for definition in plan.bindings.definitions:
        view = windows.authority(definition.entry)
        if view is None:
            continue
        aggregate = aggregation.authority(plan.scope.completed, definition.entry)
        selected = {id(windows.selected_source(item)): item for item in view.selected}
        local_windows = {}
        for position, source in enumerate(windows.sources(view)):
            value = plan.windows[window_position]
            window_position += 1
            block = blocks.get(value.block)
            original_analysis = windows.analysis(source)
            context = windows.input_context(source)
            effective = windows.effective(source)
            if (
                block is None
                or block.definition is not definition.ref
                or block.kind is not row.ProjectSQLStageKind.WINDOW
                or value.definition is not definition.ref
                or type(value.position) is not int
                or value.position != position
                or value.source is not source
                or value.context is not context
                or value.selected is not selected.get(id(source))
                or value.authored is not windows.authored(source)
                or value.effective is not effective
                or value.function is not effective.identity
                or value.value_type is not windows.result_type(source)
                or not _same(value.inputs, block.inputs)
            ):
                return False
            if isinstance(source, windows.ProjectModuleWindowOutputFact):
                if (
                    not isinstance(context, windows.WindowComputationInput)
                    or source.owner is not definition.entry.owner
                    or context.analysis is not source.analysis
                ):
                    return False
                rows = row.row_authority(plan.scope.completed, definition.entry)
                if (
                    not isinstance(rows, row.ProjectSQLRowAuthority)
                    or context.project_schema is not rows.input_schema
                ):
                    return False
                if (
                    context.item is not source.item
                    or context.definition is not definition.entry.owner.definition
                ):
                    return False
            elif isinstance(source, windows.ProjectNoJoinHiddenWindowComputation):
                if (
                    not isinstance(view.root, windows.ProjectConcreteNoJoinReplay)
                    or not isinstance(context, windows.ProjectNoJoinWindowInput)
                    or not isinstance(
                        source.analysis, windows.WindowComputationAnalysis
                    )
                    or context.owner is not definition.entry.owner
                    or context.scope is not view.root.window_scope
                    or context.input_schema is not view.root.input_schema
                    or context.let_scope is not view.root.let_scope
                    or context.base_schema is not view.root.base_state.schema
                    or source.expression is not effective
                    or source.analysis.expression is not effective
                ):
                    return False
            elif (
                not isinstance(view.root, windows.ProjectConcreteJoinedQualify)
                or source.input_namespace is not view.root.window_stage.pre_window
            ):
                return False
            result = ports.get(value.result)
            if (
                result is None
                or result.block is not block.ref
                or result.kind is not row.ProjectSQLStagePortKind.EXPORT
                or result.source is not value.ref
                or result.key is not source
                or result.type_evidence is not value.value_type
            ):
                return False
            # Independently enumerate admitted direct source roles, not the builder ledger.
            call = effective.call
            value_dependent = effective.identity.name in {
                "lag",
                "lead",
                "first_value",
                "last_value",
                "nth_value",
            }
            arguments = (
                (call.arguments[0],)
                if value_dependent
                and isinstance(call.arguments[0], (NameExpr, DottedNameExpr))
                else ()
            )
            defaults = (
                (call.arguments[2],)
                if effective.identity.name in {"lag", "lead"}
                and len(call.arguments) == 3
                and isinstance(call.arguments[2], (NameExpr, DottedNameExpr))
                else ()
            )
            R = windows.WindowDependencyRole
            expected = (
                *(
                    (R.RELATION_INPUT, e)
                    for e in (() if arguments or defaults else (call,))
                ),
                *((R.WINDOW_ARGUMENT, e) for e in arguments),
                *((R.WINDOW_DEFAULT, e) for e in defaults),
                *((R.WINDOW_PARTITION, e) for e in effective.spec.partition_by),
                *(
                    (R.WINDOW_ORDER, item.expression)
                    for item in effective.spec.order_by
                ),
            )
            originals = windows.input_uses(source)
            uses = plan.window_uses[use_position : use_position + len(expected)]
            use_position += len(expected)
            if (
                len(originals) != len(expected)
                or len(uses) != len(expected)
                or not _same(value.uses, tuple(use.ref for use in uses))
            ):
                return False
            role_positions = {}
            for ordinal, (use, original, (role, expression)) in enumerate(
                zip(uses, originals, expected, strict=True)
            ):
                role_position = role_positions.get(role, 0)
                role_positions[role] = role_position + 1
                if (
                    use.window is not value.ref
                    or use.source is not original
                    or use.expression is not expression
                    or original.expression is not expression
                    or use.role is not role
                    or original.role is not role
                    or type(use.position) is not int
                    or use.position != ordinal
                    or type(original.global_ordinal) is not int
                    or original.global_ordinal != ordinal
                    or type(use.role_position) is not int
                    or use.role_position != role_position
                    or type(original.role_ordinal) is not int
                    or original.role_ordinal != role_position
                    or use.value_type is not windows.use_type(source, original)
                ):
                    return False
                binding = (
                    original.target
                    if isinstance(original, windows.ProjectWindowDependencyOccurrence)
                    and role is not R.RELATION_INPUT
                    else None
                    if isinstance(original, windows.ProjectWindowDependencyOccurrence)
                    else original.binding
                )
                if isinstance(original, windows.WindowDependencyOccurrence):
                    expected_result_role = (
                        None
                        if original.binding is None
                        else {
                            windows.WindowInputOriginKind.GROUP_KEY: windows.ProjectRowResultRole.GROUP_KEY,
                            windows.WindowInputOriginKind.AGGREGATE_RESULT: windows.ProjectRowResultRole.AGGREGATE_RESULT,
                        }.get(original.binding.origin)
                    )
                    if original.target_result_role is not expected_result_role:
                        return False
                if use.binding is not binding:
                    return False
                if role is R.RELATION_INPUT:
                    if (
                        use.binding is not None
                        or use.input is not None
                        or use.value_type is not None
                    ):
                        return False
                    if (
                        isinstance(original, windows.ProjectWindowDependencyOccurrence)
                        and original.target is not context
                    ):
                        return False
                    continue
                if (
                    not isinstance(
                        binding,
                        (
                            windows.WindowInputBinding,
                            windows.ProjectJoinedWindowInputBinding,
                        ),
                    )
                    or use.value_type is None
                    or binding.value_type != use.value_type
                ):
                    return False
                if isinstance(original, windows.ProjectWindowDependencyOccurrence):
                    if not isinstance(
                        source, windows.ProjectConcreteWindowComputation
                    ) or not isinstance(
                        context, windows.ProjectJoinedWindowInputNamespace
                    ):
                        return False
                    if original.site is not source.site or not any(
                        binding is candidate for candidate in context.bindings
                    ):
                        return False
                elif isinstance(original, windows.ProjectNoJoinHiddenWindowInputUse):
                    if not isinstance(
                        source, windows.ProjectNoJoinHiddenWindowComputation
                    ) or not isinstance(context, windows.ProjectNoJoinWindowInput):
                        return False
                    if (
                        original.context is not context
                        or original.hidden is not source.expression
                    ):
                        return False
                    pairs = tuple(
                        target
                        for candidate, target in zip(
                            context.scope.bindings, context.targets, strict=True
                        )
                        if candidate is binding
                    )
                    if len(pairs) != 1 or pairs[0] is not original.target:
                        return False
                elif (
                    not isinstance(context, windows.WindowComputationInput)
                    or original.computation is not context
                    or not any(
                        binding is candidate for candidate in context.scope.bindings
                    )
                ):
                    return False
                key = windows.input_target(source, original, aggregate)
                port = ports.get(use.input)
                if (
                    port is None
                    or port.block is not block.ref
                    or port.kind is not row.ProjectSQLStagePortKind.INPUT
                    or port.key is not key
                    or not any(port.ref is ref for ref in block.inputs)
                ):
                    return False
            arguments = plan.window_arguments[
                argument_position : argument_position + len(call.arguments)
            ]
            argument_position += len(call.arguments)
            if not _same(
                value.arguments, tuple(argument.ref for argument in arguments)
            ) or len(arguments) != len(call.arguments):
                return False
            for ordinal, (argument, expression) in enumerate(
                zip(arguments, call.arguments, strict=True)
            ):
                matched = tuple(use for use in uses if use.expression is expression)
                if (
                    argument.window is not value.ref
                    or type(argument.position) is not int
                    or argument.position != ordinal
                    or argument.expression is not expression
                    or argument.role is not windows.argument_role(source, ordinal)
                    or argument.value_type is not windows.argument_type(source, ordinal)
                    or len(matched) > 1
                    or argument.use is not (None if not matched else matched[0].ref)
                ):
                    return False
            policy = plan.window_policies[policy_position]
            policy_position += 1
            ir_operator, ir_policy, ir_effect = windows.ir_evidence(
                source, definition.entry
            )
            _, _, ranking, distribution, bucket, navigation, frame_value, modifiers = (
                windows.components(source)
            )
            partitions, orders, *_ = windows.components(source)
            if (
                policy.ref is not value.policy
                or policy.ir_operator is not ir_operator
                or policy.ir_policy is not ir_policy
                or policy.ir_effect is not ir_effect
                or not any(ir_operator is operator for operator in block.operators)
                or policy.window is not value.ref
                or policy.specification is not original_analysis.validated_specification
                or not _same(policy.partitions, partitions)
                or not _same(policy.orders, orders)
                or policy.modifiers is not modifiers
                or policy.named_use is not original_analysis.resolved_named_use
                or policy.namespace is not view.named
                or policy.ranking is not ranking
                or policy.distribution is not distribution
                or policy.bucket_count != bucket
                or (
                    policy.bucket_count is not None
                    and type(policy.bucket_count) is not int
                )
                or policy.navigation is not navigation
                or policy.frame_value is not frame_value
                or policy.specification.argument_expressions is not call.arguments
            ):
                return False
            if policy.named_use is not None:
                if (
                    policy.namespace is None
                    or policy.named_use.composed.expression is not value.authored
                ):
                    return False
                template = policy.named_use.composed.target_template
                if not any(template is item for item in policy.namespace.templates):
                    return False
            local_windows[id(source)] = value
        rows = row.row_authority(plan.scope.completed, definition.entry)
        if rows is None:
            return False
        selected_by_item = {id(item.item): item for item in view.selected}
        for semantic, export in zip(rows.selections, definition.exports, strict=True):
            selected_result = selected_by_item.get(id(semantic.item))
            if selected_result is None:
                continue
            projection = plan.window_projections[projection_position]
            projection_position += 1
            value = local_windows[id(windows.selected_source(selected_result))]
            port = ports.get(projection.input)
            block = blocks.get(projection.block)
            field = (
                definition.entry.semantic_entry.fields[
                    semantic.selected_output_ordinal
                ].field
                if isinstance(definition.entry, ProjectIRCompletedQueryBlockOutput)
                else semantic.field
            )
            if (
                projection.window is not value.ref
                or projection.source is not selected_result
                or projection.semantic is not semantic
                or projection.export is not export.ref
                or export.field.evidence is not field
                or block is None
                or block.kind is not row.ProjectSQLStageKind.PROJECTION
                or block.definition is not definition.ref
                or port is None
                or port.block is not block.ref
                or port.kind is not row.ProjectSQLStagePortKind.INPUT
                or port.key is not value.source
            ):
                return False
    return (
        window_position,
        use_position,
        argument_position,
        policy_position,
        projection_position,
    ) == (
        len(plan.windows),
        len(plan.window_uses),
        len(plan.window_arguments),
        len(plan.window_policies),
        len(plan.window_projections),
    )


def _whole_plan(plan: ProjectSQLPlan) -> tuple[ProjectSQLPlanVerificationIssue, ...]:
    Issue, K = ProjectSQLPlanVerificationIssue, ProjectSQLPlanRefKind
    bindings = plan.bindings
    definitions = tuple(
        d
        for d in bindings.definitions
        if not isinstance(d.entry.owner.definition, SourceDef)
    )
    if any(
        not _projection_shape(
            d.entry,
            aggregation.authority(plan.scope.completed, d.entry),
            windows.authority(d.entry),
        )
        for d in definitions
        if not isinstance(d.entry.owner.definition, SetRelationDef)
    ):
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
        )
    ):
        return (Issue.STRUCTURE,)
    selected = tuple(
        d for d in definitions if d.entry.owner is plan.scope.selected_owner
    )
    if len(selected) != 1 or not _same(plan.exports, selected[0].exports):
        return (Issue.PORTS_AND_PROJECTIONS,)
    for values, cls, kind in (
        (plan.blocks, ProjectSQLSelectBlock, K.SELECT_BLOCK),
        (
            plan.expression_sites,
            (
                row.ProjectSQLExpressionSite,
                row.ProjectSQLJoinedSite,
                row.ProjectSQLMatchSite,
                aggregation.ProjectSQLAggregateSite,
                windows.ProjectSQLQualifySite,
            ),
            K.EXPRESSION_SITE,
        ),
        (plan.stage_ports, row.ProjectSQLStagePort, K.STAGE_PORT),
        (plan.let_values, row.ProjectSQLLetValue, K.LET_VALUE),
        (plan.filters, row.ProjectSQLFilter, K.FILTER),
        (plan.projections, ProjectSQLProjection, K.PROJECTION),
        (plan.operands, row.ProjectSQLExpressionOperand, K.OPERAND),
    ):
        if not _inventory(values, cls, plan.scope, kind):
            return (Issue.STRUCTURE,)
    if type(plan.expressions) is not tuple or any(
        not _ref(e.ref, plan.scope, K.EXPRESSION, i)
        for i, e in enumerate(plan.expressions)
    ):
        return (Issue.STRUCTURE,)
    if (
        not _join_structure(plan)
        or not _aggregate_structure(plan)
        or not _window_structure(plan)
        or not _result_structure(plan)
        or not _set_structure(plan)
    ):
        return (Issue.STRUCTURE,)
    join_by_definition = {d.ref: [] for d in definitions}
    for joined in plan.joins:
        join_by_definition[joined.definition].append(joined)
    tails = {tail.definition: tail for tail in plan.join_tails}
    boundaries = {b.use.consumer: b for b in bindings.boundaries}
    uses = {d.ref: [] for d in definitions}
    for use in plan.input_uses:
        uses[use.consumer].append(use)
    ports = {p.ref: p for p in plan.stage_ports}
    expressions = {e.ref: e for e in plan.expressions}
    symbols = {s.subject: s for s in plan.symbols[len(bindings.symbols) :]}
    binding_symbols = {s.subject: s for s in bindings.symbols}
    if len(ports) != len(plan.stage_ports) or len(expressions) != len(plan.expressions):
        return (Issue.STRUCTURE,)
    # Consume the authored stage ledger; a missing whole site cannot verify vacuously.
    block_position = site_position = port_position = let_position = filter_position = (
        projection_position
    ) = 0
    site_specs = []
    root_by_site = {}
    for definition in definitions:
        entry, authored = definition.entry, definition.entry.owner.definition
        if isinstance(authored, SetRelationDef):
            continue
        if not isinstance(authored, (TableDef, QueryDef)):
            return (Issue.UNSUPPORTED_SHAPE,)
        authority = row.row_authority(plan.scope.completed, entry)
        if authority is None:
            return (Issue.UNSUPPORTED_SHAPE,)
        aggregate = aggregation.authority(plan.scope.completed, entry)
        window_view = windows.authority(entry)
        aggregate_stage = next(
            (a for a in plan.aggregations if a.definition is definition.ref), None
        )
        expected_bindings = (
            () if authored.let_clause is None else authored.let_clause.bindings
        )
        if (
            len(authority.selections) != len(definition.exports)
            or (
                aggregate is None
                and len(authority.selected_evidence) != len(authority.selections)
            )
            or (
                aggregate is None
                and len(authority.selected_references) != len(authority.selections)
            )
            or not _same(
                tuple(f.item for f in authority.selections), authored.select_items
            )
            or any(
                type(f.selected_output_ordinal) is not int
                or f.selected_output_ordinal != i
                for i, f in enumerate(authority.selections)
            )
        ):
            return (Issue.STRUCTURE,)
        if isinstance(authority, row.ProjectSQLJoinedRowAuthority):
            if not _same(
                tuple(value.occurrence.binding for value in authority.lets),
                expected_bindings,
            ) or any(
                type(value.occurrence.source_ordinal) is not int
                or value.occurrence.source_ordinal != i
                for i, value in enumerate(authority.lets)
            ):
                return (Issue.STRUCTURE,)
            boundary = tails[definition.ref]
            use = None
            original = {}
            carries = [
                (port, field, field.value_type)
                for port, field in zip(boundary.ports, boundary.fields, strict=True)
            ]
            predecessor = boundary.join
            for joined in join_by_definition[definition.ref]:
                site = joined.site
                if site is not None:
                    if plan.expression_sites[site_position] is not site:
                        return (Issue.STRUCTURE,)
                    site_position += 1
                    inputs = tuple(
                        p
                        for p in plan.join_ports
                        if p.block is joined.ref
                        and p.kind is joining.ProjectSQLJoinPortKind.MATCH
                    )
                    site_specs.append((site, inputs))
                    root_by_site[site.ref] = joined.on
        else:
            if (
                authority.let_scope.status
                not in {
                    ProjectLetScopeFactsStatus.ABSENT,
                    ProjectLetScopeFactsStatus.CONCRETE,
                }
                or not _same(authority.let_scope.bindings, expected_bindings)
                or authority.let_scope.definition is not authored
                or authority.let_scope.input_schema is not authority.input_schema
                or not _same(
                    tuple(f.binding for f in authority.lets), expected_bindings
                )
                or any(
                    type(f.binding_ordinal) is not int or f.binding_ordinal != i
                    for i, f in enumerate(authority.lets)
                )
                or len(uses[definition.ref]) != 1
            ):
                return (Issue.STRUCTURE,)
            use = uses[definition.ref][0]
            boundary = boundaries[definition.ref]
            keys = tuple(port.field.evidence for port in use.ports)
            if isinstance(entry, ProjectIRReboundExistingOutput):
                compatibility = entry.relation_input.compatibility
                if (
                    use.edge is not entry.relation_input
                    or not compatibility.satisfied
                    or compatibility.output is not use.edge.producer.output
                    or not _same(
                        compatibility.required_fields,
                        tuple(authority.input_schema.fields.values()),
                    )
                    or len(compatibility.required_fields) != len(use.ports)
                    or any(
                        port.field.output is not compatibility.output
                        for port in use.ports
                    )
                ):
                    return (Issue.PORTS_AND_PROJECTIONS,)
                keys = compatibility.required_fields
            original = {
                id(key): port for key, port in zip(keys, use.ports, strict=True)
            }
            if {id(f) for f in authority.input_schema.fields.values()} != set(original):
                return (Issue.PORTS_AND_PROJECTIONS,)
            carries = [
                (port.ref, key, port.field.evidence)
                for key, port in zip(keys, use.ports, strict=True)
            ]
            predecessor = use.ref
        stage_kinds = [row.ProjectSQLStageKind.LET] * len(expected_bindings)
        if authored.where_clause is not None:
            stage_kinds.append(row.ProjectSQLStageKind.WHERE)
        if aggregate is not None:
            stage_kinds.append(row.ProjectSQLStageKind.AGGREGATE)
            if aggregate.satisfying is not None:
                stage_kinds.append(row.ProjectSQLStageKind.SATISFYING)
        if window_view is not None:
            stage_kinds.append(row.ProjectSQLStageKind.WINDOW)
            if window_view.qualify is not None:
                stage_kinds.append(row.ProjectSQLStageKind.QUALIFY)
        stage_kinds.append(row.ProjectSQLStageKind.PROJECTION)
        for local_position, kind in enumerate(stage_kinds):
            block = plan.blocks[block_position]
            block_position += 1
            if (
                block.definition is not definition.ref
                or block.selected is not entry
                or type(block.position) is not int
                or block.position != local_position
                or block.kind is not kind
                or block.predecessor is not predecessor
                or block.boundary is not boundary
                or not _same(
                    block.operators,
                    tuple(
                        operator
                        for operator in _operators(entry)
                        if (
                            operator.kind is ProjectIRLogicalOperatorKind.RELATION_INPUT
                            and local_position == 0
                        )
                        or (
                            operator.kind is ProjectIRLogicalOperatorKind.ROW_FILTER
                            and kind is row.ProjectSQLStageKind.WHERE
                        )
                        or (
                            operator.kind
                            is ProjectIRLogicalOperatorKind.GROUP_AGGREGATE
                            and kind is row.ProjectSQLStageKind.AGGREGATE
                        )
                        or (
                            operator.kind is ProjectIRLogicalOperatorKind.RESULT_FILTER
                            and kind is row.ProjectSQLStageKind.SATISFYING
                        )
                        or (
                            kind is row.ProjectSQLStageKind.WINDOW
                            and operator.kind.value == "window_evaluation"
                        )
                        or (
                            kind is row.ProjectSQLStageKind.QUALIFY
                            and operator.kind.value == "qualify"
                        )
                        or (
                            operator.kind
                            is ProjectIRLogicalOperatorKind.FINAL_PROJECTION
                            and kind is row.ProjectSQLStageKind.PROJECTION
                        )
                    ),
                )
            ):
                return (Issue.STRUCTURE,)
            incoming = plan.stage_ports[port_position : port_position + len(carries)]
            port_position += len(carries)
            if not _same(block.inputs, tuple(p.ref for p in incoming)) or len(
                incoming
            ) != len(carries):
                return (Issue.PORTS_AND_PROJECTIONS,)
            for port, (source, key, type_evidence) in zip(
                incoming, carries, strict=True
            ):
                if (
                    port.block is not block.ref
                    or port.kind is not row.ProjectSQLStagePortKind.INPUT
                    or port.source is not source
                    or port.key is not key
                    or port.type_evidence is not type_evidence
                ):
                    return (Issue.PORTS_AND_PROJECTIONS,)
            if kind is row.ProjectSQLStageKind.LET:
                fact = authority.lets[local_position]
                if isinstance(fact, row.ProjectJoinedLetValue) and isinstance(
                    authority, row.ProjectSQLJoinedRowAuthority
                ):
                    if (
                        fact.occurrence.owner is not entry.owner
                        or fact.namespace
                        is not authority.namespaces.binding_namespaces[local_position]
                    ):
                        return (Issue.STRUCTURE,)
                    specs = [
                        (
                            row.ProjectSQLExpressionRole.LET,
                            local_position,
                            fact.occurrence.binding,
                            fact,
                            fact.resolutions,
                        )
                    ]
                elif isinstance(fact, ProjectModuleLetBindingFact) and isinstance(
                    authority, row.ProjectSQLRowAuthority
                ):
                    if (
                        fact.owner is not entry.owner
                        or fact.scope_facts is not authority.let_scope
                        or fact.binding_ordinal != local_position
                    ):
                        return (Issue.STRUCTURE,)
                    specs = [
                        (
                            row.ProjectSQLExpressionRole.LET,
                            local_position,
                            fact.binding,
                            fact,
                            fact.references,
                        )
                    ]
                else:
                    return (Issue.STRUCTURE,)
            elif kind is row.ProjectSQLStageKind.WHERE:
                if authority.where is None or authored.where_clause is None:
                    return (Issue.STRUCTURE,)
                specs = [
                    (
                        row.ProjectSQLExpressionRole.WHERE,
                        0,
                        authored.where_clause,
                        authority.where,
                        authority.where_references,
                    )
                ]
            elif kind is row.ProjectSQLStageKind.AGGREGATE:
                assert aggregate is not None
                specs = [
                    (
                        row.ProjectSQLExpressionRole.AGGREGATE_ARGUMENT,
                        i,
                        source.item,
                        aggregation.argument_evidence(source),
                        refs,
                    )
                    for i, (source, refs) in enumerate(
                        zip(
                            aggregate.aggregates,
                            aggregate.argument_references,
                            strict=True,
                        )
                    )
                    if aggregation.arguments(source)
                ]
            elif kind is row.ProjectSQLStageKind.SATISFYING:
                assert aggregate is not None and authored.satisfying_clause is not None
                specs = [
                    (
                        row.ProjectSQLExpressionRole.SATISFYING,
                        0,
                        authored.satisfying_clause,
                        aggregate.satisfying,
                        aggregate.satisfying_references,
                    )
                ]
            elif kind is row.ProjectSQLStageKind.WINDOW:
                specs = []
            elif kind is row.ProjectSQLStageKind.QUALIFY:
                assert window_view is not None and window_view.qualify is not None
                specs = [
                    (
                        row.ProjectSQLExpressionRole.QUALIFY,
                        0,
                        authored.qualify_clause,
                        window_view.qualify,
                        windows.qualifier_references(window_view.qualify),
                    )
                ]
            elif aggregate is not None:
                specs = []
            else:
                specs = [
                    (row.ProjectSQLExpressionRole.SELECT, i, fact.item, evidence, refs)
                    for i, (fact, evidence, refs) in enumerate(
                        zip(
                            authority.selections,
                            authority.selected_evidence,
                            authority.selected_references,
                            strict=True,
                        )
                    )
                    if not isinstance(fact.item.expression, WindowExpr)
                ]
            local_sites = []
            for role, ordinal, occurrence, evidence, references in specs:
                site = plan.expression_sites[site_position]
                site_position += 1
                if not _row_site(
                    site,
                    entry,
                    authority,
                    block,
                    role,
                    ordinal,
                    occurrence,
                    evidence,
                    references,
                    expected_bindings,
                ):
                    return (Issue.STRUCTURE,)
                if isinstance(
                    site, windows.ProjectSQLQualifySite
                ) and site.aggregate is not (
                    None if aggregate_stage is None else aggregate_stage.authority
                ):
                    return (Issue.STRUCTURE,)
                site_specs.append((site, incoming))
                local_sites.append(site)
            if kind is row.ProjectSQLStageKind.PROJECTION:
                if not _same(block.exports, tuple(p.ref for p in definition.exports)):
                    return (Issue.PORTS_AND_PROJECTIONS,)
                for site in local_sites:
                    i = site.ordinal
                    export = definition.exports[i]
                    projection = plan.projections[projection_position]
                    projection_position += 1
                    root_by_site[site.ref] = projection.expression
                    direct = None
                    if (
                        isinstance(site, row.ProjectSQLExpressionSite)
                        and isinstance(
                            site.occurrence.expression, (NameExpr, DottedNameExpr)
                        )
                        and len(site.references) == 1
                    ):
                        direct = original.get(id(site.references[0].input_field))
                    semantic = authority.selections[i]
                    field = (
                        entry.semantic_entry.fields[i].field
                        if isinstance(entry, ProjectIRCompletedQueryBlockOutput)
                        else semantic.field
                    )
                    if (
                        projection.site is not site
                        or projection.block is not block.ref
                        or projection.input_use
                        is not (None if use is None else use.ref)
                        or projection.export is not export.ref
                        or projection.semantic is not semantic
                        or export.field.evidence is not field
                        or projection.input_port
                        is not (None if direct is None else direct.ref)
                        or projection.source_port
                        is not (None if direct is None else direct.producer_port)
                        or projection.symbol
                        is not (None if direct is None else binding_symbols[direct.ref])
                    ):
                        return (Issue.PORTS_AND_PROJECTIONS,)
            elif kind is row.ProjectSQLStageKind.AGGREGATE:
                assert aggregate_stage is not None
                outgoing = plan.stage_ports[
                    port_position : port_position + len(aggregate_stage.results)
                ]
                port_position += len(aggregate_stage.results)
                if not _same(block.exports, aggregate_stage.results) or not _same(
                    tuple(p.ref for p in outgoing), aggregate_stage.results
                ):
                    return (Issue.PORTS_AND_PROJECTIONS,)
                for site in local_sites:
                    matches = tuple(
                        a
                        for a in plan.aggregates
                        if a.aggregation is aggregate_stage.ref
                        and a.source.item is site.occurrence
                    )
                    if len(matches) != 1 or len(matches[0].arguments) != 1:
                        return (Issue.STRUCTURE,)
                    root_by_site[site.ref] = matches[0].arguments[0]
                carries = [(p.ref, p.key, p.type_evidence) for p in outgoing]
            else:
                outgoing = plan.stage_ports[
                    port_position : port_position + len(incoming)
                ]
                port_position += len(incoming)
                if len(outgoing) != len(incoming):
                    return (Issue.PORTS_AND_PROJECTIONS,)
                for port, previous in zip(outgoing, incoming, strict=True):
                    if (
                        port.block is not block.ref
                        or port.kind is not row.ProjectSQLStagePortKind.EXPORT
                        or port.key is not previous.key
                        or port.source is not previous.ref
                        or port.type_evidence is not previous.type_evidence
                    ):
                        return (Issue.PORTS_AND_PROJECTIONS,)
                if kind is row.ProjectSQLStageKind.LET:
                    value = plan.let_values[let_position]
                    let_position += 1
                    port = plan.stage_ports[port_position]
                    port_position += 1
                    site = local_sites[0]
                    root_by_site[site.ref] = value.expression
                    if (
                        value.site is not site
                        or value.port is not port.ref
                        or port.block is not block.ref
                        or port.kind is not row.ProjectSQLStagePortKind.EXPORT
                        or port.key
                        is not (
                            site.evidence.occurrence
                            if isinstance(site, row.ProjectSQLJoinedSite)
                            and isinstance(site.evidence, row.ProjectJoinedLetValue)
                            else site.occurrence
                        )
                        or port.source is not value.expression
                        or port.type_evidence
                        is not authority.lets[local_position].value_type
                    ):
                        return (Issue.PORTS_AND_PROJECTIONS,)
                    outgoing = (*outgoing, port)
                elif kind is row.ProjectSQLStageKind.WINDOW:
                    local_windows = tuple(
                        value for value in plan.windows if value.block is block.ref
                    )
                    results = plan.stage_ports[
                        port_position : port_position + len(local_windows)
                    ]
                    port_position += len(local_windows)
                    if not _same(
                        tuple(port.ref for port in results),
                        tuple(value.result for value in local_windows),
                    ):
                        return (Issue.STRUCTURE,)
                    outgoing = (*outgoing, *results)
                else:
                    item = plan.filters[filter_position]
                    filter_position += 1
                    site = local_sites[0]
                    root_by_site[site.ref] = item.predicate
                    if item.site is not site or item.retention_effects is not (
                        windows.qualify_effects(window_view.qualify)
                        if kind is row.ProjectSQLStageKind.QUALIFY
                        and window_view is not None
                        and window_view.qualify is not None
                        else aggregation.satisfying_effects(aggregate)
                        if aggregate is not None
                        and kind is row.ProjectSQLStageKind.SATISFYING
                        else _SQL_ROW_RETENTION_EFFECTS
                    ):
                        return (Issue.STRUCTURE,)
                    predicate = expressions[item.predicate]
                    if (
                        predicate.value_type.kind is not ValueTypeKind.KNOWN
                        or predicate.value_type.resolved_type.name != "Bool"
                    ):
                        return (Issue.STRUCTURE,)
                if not _same(block.exports, tuple(p.ref for p in outgoing)):
                    return (Issue.PORTS_AND_PROJECTIONS,)
                carries = [(p.ref, p.key, p.type_evidence) for p in outgoing]
            predecessor = block.ref
    if (
        block_position,
        site_position,
        port_position,
        let_position,
        filter_position,
        projection_position,
    ) != (
        len(plan.blocks),
        len(plan.expression_sites),
        len(plan.stage_ports),
        len(plan.let_values),
        len(plan.filters),
        len(plan.projections),
    ):
        return (Issue.STRUCTURE,)
    if not _row_expressions(plan, site_specs, root_by_site, symbols):
        return (Issue.PORTS_AND_PROJECTIONS,)
    if not _row_symbols(plan):
        return (Issue.SYMBOLS,)
    return _row_origins_and_demands(plan)


def _row_expressions(plan, site_specs, root_by_site, symbols) -> bool:
    position = operand_position = 0
    variants = {
        LiteralExpr: row.ProjectSQLLiteral,
        NameExpr: row.ProjectSQLReference,
        DottedNameExpr: row.ProjectSQLReference,
        UnaryExpr: row.ProjectSQLUnary,
        BinaryExpr: row.ProjectSQLBinary,
        ComparisonExpr: row.ProjectSQLComparison,
        IsNullExpr: row.ProjectSQLIsNull,
        BetweenExpr: row.ProjectSQLBetween,
    }
    roles = {
        row.ProjectSQLExpressionRole.LET: ProjectModuleFactOccurrenceRole.LET_VALUE,
        row.ProjectSQLExpressionRole.SELECT: ProjectModuleFactOccurrenceRole.SELECT_VALUE,
        row.ProjectSQLExpressionRole.WHERE: ProjectModuleWhereReferenceRole.WHERE_VALUE,
    }
    for site, incoming in site_specs:
        aggregate_site = isinstance(site, aggregation.ProjectSQLAggregateSite)
        qualify_site = isinstance(site, windows.ProjectSQLQualifySite)
        result_site = (
            aggregate_site and site.role is row.ProjectSQLExpressionRole.SATISFYING
        )
        atomic = (
            {id(row.reference_expression(r)) for r in site.references}
            if result_site or qualify_site
            else set()
        )
        reference_type = (
            windows.ProjectSQLWindowReference
            if qualify_site
            else aggregation.ProjectSQLResultReference
            if result_site
            else row.ProjectSQLMatchReference
            if isinstance(site, row.ProjectSQLMatchSite)
            else row.ProjectSQLJoinedReference
            if isinstance(site, row.ProjectSQLJoinedSite)
            or (
                aggregate_site
                and isinstance(
                    site.evidence, row.ProjectConcreteJoinedNamespaceExpression
                )
            )
            else row.ProjectSQLReference
        )
        variants[NameExpr] = variants[DottedNameExpr] = reference_type
        variants[CallExpr] = aggregation.ProjectSQLAggregateArgumentCall
        # Traverse actual source independently of the expression allocator.
        pending, nodes = (
            [site.expression if aggregate_site else site.occurrence.expression],
            [],
        )
        while pending:
            node = pending.pop()
            nodes.append(node)
            if id(node) in atomic:
                children = ()
            elif isinstance(node, (BinaryExpr, ComparisonExpr)):
                children = (node.left, node.right)
            elif (
                isinstance(node, CallExpr)
                and aggregate_site
                and site.role is row.ProjectSQLExpressionRole.AGGREGATE_ARGUMENT
            ):
                children = node.arguments
            elif isinstance(node, UnaryExpr):
                children = (node.operand,)
            elif isinstance(node, IsNullExpr):
                children = (node.value,)
            elif isinstance(node, BetweenExpr):
                children = (node.value, node.lower, node.upper)
            elif isinstance(node, (LiteralExpr, NameExpr, DottedNameExpr)):
                children = ()
            else:
                return False
            pending.extend(reversed(children))
        values = plan.expressions[position : position + len(nodes)]
        position += len(nodes)
        if len(values) != len(nodes) or root_by_site[site.ref] is not values[0].ref:
            return False
        if isinstance(
            site.evidence, (ProjectModuleLetBindingFact, row.ProjectJoinedLetValue)
        ) and (values[0].value_type is not site.evidence.value_type):
            return False
        local = {id(n): value for n, value in zip(nodes, values, strict=True)}
        if len(local) != len(nodes):
            return False
        types = {id(n): (n, v) for n, v in row.evidence_types(site.evidence).items()}
        references = iter(site.references)
        environment = {id(port.key): port for port in incoming}
        reference_position = 0
        for node, value in zip(nodes, values, strict=True):
            variants[LiteralExpr] = (
                row.ProjectSQLBoundLiteral
                if type(value) is row.ProjectSQLBoundLiteral
                else row.ProjectSQLLiteral
            )
            if (
                type(value)
                is not (
                    reference_type if id(node) in atomic else variants.get(type(node))
                )
                or value.site is not site
                or value.expression is not node
                or id(node) not in types
                or types[id(node)][0] is not node
                or value.value_type is not types[id(node)][1]
                or value.value_type.kind is not ValueTypeKind.KNOWN
            ):
                return False
            if isinstance(
                value,
                (
                    row.ProjectSQLReference,
                    row.ProjectSQLJoinedReference,
                    row.ProjectSQLMatchReference,
                    aggregation.ProjectSQLResultReference,
                    windows.ProjectSQLWindowReference,
                ),
            ):
                reference = next(references, None)
                if (
                    reference is None
                    or value.reference is not reference
                    or row.reference_expression(reference) is not node
                ):
                    return False
                if qualify_site:
                    if not _same(
                        site.references, windows.qualifier_references(site.evidence)
                    ):
                        return False
                    if isinstance(
                        reference,
                        (
                            windows.ProjectNoJoinHiddenWindowComputation,
                            windows.ProjectConcreteWindowComputation,
                        ),
                    ):
                        hidden = (
                            site.evidence.hidden_attempts
                            if isinstance(site.evidence, windows.ProjectNoJoinQualify)
                            else site.evidence.hidden_computations
                        )
                        if not any(reference is value for value in hidden):
                            return False
                    elif not any(
                        reference is value for value in site.evidence.references
                    ):
                        return False
                elif result_site:
                    assert isinstance(site, aggregation.ProjectSQLAggregateSite)
                    original = site.authority.source
                    if isinstance(
                        reference, aggregation.ProjectJoinedSatisfyingOutputReference
                    ):
                        if not isinstance(
                            original, aggregation.ProjectConcreteJoinedAggregation
                        ) or not any(
                            reference.output is output
                            for output in original.stage_outputs
                        ):
                            return False
                    elif isinstance(
                        reference, aggregation.ProjectJoinedSatisfyingAggregateReference
                    ):
                        if not isinstance(
                            original, aggregation.ProjectConcreteJoinedAggregation
                        ) or not any(
                            reference.aggregate is source
                            for source in original.aggregates
                        ):
                            return False
                    elif isinstance(
                        reference, aggregation.ProjectRelationClauseDependencyFact
                    ):
                        if (
                            not isinstance(
                                original,
                                aggregation.ProjectAggregateGroupedClauseReadiness,
                            )
                            or original.finalization.candidate is None
                        ):
                            return False
                        targets = tuple(
                            output
                            for item, output in original.finalization.candidate.selected_results.items()
                            if item is reference.target_occurrence
                        )
                        if (
                            len(targets) != 1
                            or reference.target_field is not targets[0].field
                            or reference.aggregate_result_fact
                            is not (
                                targets[0].fact
                                if isinstance(
                                    targets[0],
                                    aggregation.ProjectAggregateSelectedResult,
                                )
                                else targets[0].aggregate_fact
                            )
                        ):
                            return False
                    else:
                        return False
                elif aggregate_site and isinstance(
                    site.evidence, aggregation.ProjectAggregateExpressionAnalysis
                ):
                    if not isinstance(reference, ProjectModuleExpressionReferenceFact):
                        return False
                    definition = site.evidence.definition
                    if (
                        reference.owner is not site.owner
                        or reference.role
                        is not ProjectModuleFactOccurrenceRole.SELECT_VALUE
                        or type(reference.container_ordinal) is not int
                        or reference.container_ordinal < 0
                        or reference.container_ordinal >= len(definition.select_items)
                        or definition.select_items[reference.container_ordinal]
                        is not site.occurrence
                        or type(reference.dependency_ordinal) is not int
                        or reference.dependency_ordinal != reference_position
                        or reference.status
                        is not ProjectModuleCandidateBucketStatus.CONCRETE
                        or reference.selected_output_candidates
                        or any(
                            not any(
                                binding is allowed
                                for allowed in site.evidence.let_scope.bindings
                            )
                            for binding in reference.let_candidates
                        )
                    ):
                        return False
                elif isinstance(site, row.ProjectSQLExpressionSite):
                    if not isinstance(reference, ProjectModuleExpressionReferenceFact):
                        return False
                    if (
                        reference.owner is not site.owner
                        or reference.role is not roles[site.role]
                        or type(reference.container_ordinal) is not int
                        or reference.container_ordinal != site.ordinal
                        or type(reference.dependency_ordinal) is not int
                        or reference.dependency_ordinal != reference_position
                        or reference.status
                        is not ProjectModuleCandidateBucketStatus.CONCRETE
                        or reference.selected_output_candidates
                        or any(
                            not any(binding is b for b in site.let_prefix)
                            for binding in reference.let_candidates
                        )
                    ):
                        return False
                elif isinstance(site, row.ProjectSQLMatchSite):
                    if (
                        type(reference) is not row.ProjectJoinConditionReference
                        or reference.environment is not site.evidence.environment
                        or type(reference.position) is not int
                        or reference.position != reference_position
                        or reference.state is not ProjectJoinReferenceState.RESOLVED
                        or reference.target is None
                        or not _same(reference.candidates, (reference.target,))
                        or not any(
                            reference.target is field
                            for field in site.evidence.environment.fields
                        )
                        or value.value_type is not reference.target.value_type
                    ):
                        return False
                else:
                    if not isinstance(
                        reference,
                        (
                            row.ProjectJoinedLetReferenceResolution,
                            ProjectScalarReferenceResolution,
                        ),
                    ):
                        return False
                    if isinstance(site, aggregation.ProjectSQLAggregateSite):
                        if not isinstance(
                            site.evidence, row.ProjectConcreteJoinedNamespaceExpression
                        ):
                            return False
                        namespace = site.evidence.namespace
                    else:
                        if not isinstance(site, row.ProjectSQLJoinedSite):
                            return False
                        namespace = site.namespace
                    if (
                        reference.reference.environment
                        is not namespace.binding_environment.scalar_environment
                    ):
                        return False
                    if isinstance(reference, row.ProjectJoinedLetReferenceResolution):
                        if reference.namespace is not namespace or not any(
                            reference.target is v for v in namespace.let_values
                        ):
                            return False
                    elif isinstance(reference, ProjectScalarReferenceResolution):
                        if (
                            reference.target is None
                            or reference.status
                            is not ProjectModuleCandidateBucketStatus.CONCRETE
                            or not _same(reference.candidates, (reference.target,))
                            or not any(
                                reference.target is field
                                for field in namespace.visible_fields
                            )
                        ):
                            return False
                    else:
                        return False
                    if (
                        reference.target is None
                        or value.value_type is not reference.target.value_type
                    ):
                        return False
                if qualify_site:
                    assert isinstance(
                        reference,
                        (
                            windows.ProjectNoJoinQualifyReferenceResolution,
                            windows.ProjectQualifyReferenceResolution,
                            windows.ProjectNoJoinHiddenWindowComputation,
                            windows.ProjectConcreteWindowComputation,
                        ),
                    )
                    key = windows.qualify_target(
                        site.evidence, reference, site.aggregate
                    )
                elif result_site:
                    assert isinstance(site, aggregation.ProjectSQLAggregateSite)
                    if isinstance(reference, row.ProjectJoinConditionReference):
                        return False
                    key = aggregation.result_key(
                        site, cast(aggregation.Reference, reference)
                    )
                else:
                    key = row.reference_key(reference)
                port = environment.get(id(key))
                if (
                    port is None
                    or port.key is not key
                    or value.port is not port.ref
                    or value.symbol is not symbols.get(port.ref)
                    or value.symbol.scope is not site.block
                ):
                    return False
                reference_position += 1
                children = ()
            elif isinstance(value, aggregation.ProjectSQLAggregateArgumentCall):
                children = tuple(local[id(argument)].ref for argument in node.arguments)
                if not _same(value.arguments, children):
                    return False
            elif isinstance(value, (row.ProjectSQLLiteral, row.ProjectSQLBoundLiteral)):
                children = ()
            elif isinstance(value, row.ProjectSQLUnary):
                children = (local[id(node.operand)].ref,)
                if value.operand is not children[0]:
                    return False
            elif isinstance(value, (row.ProjectSQLBinary, row.ProjectSQLComparison)):
                children = (local[id(node.left)].ref, local[id(node.right)].ref)
                if value.left is not children[0] or value.right is not children[1]:
                    return False
            elif isinstance(value, row.ProjectSQLIsNull):
                children = (local[id(node.value)].ref,)
                if value.value is not children[0]:
                    return False
            else:
                children = (
                    local[id(node.value)].ref,
                    local[id(node.lower)].ref,
                    local[id(node.upper)].ref,
                )
                if (
                    value.value is not children[0]
                    or value.lower is not children[1]
                    or value.upper is not children[2]
                ):
                    return False
            for i, child in enumerate(children):
                operand = plan.operands[operand_position]
                operand_position += 1
                if (
                    operand.site is not site
                    or operand.parent is not value.ref
                    or type(operand.position) is not int
                    or operand.position != i
                    or operand.child is not child
                ):
                    return False
        if next(references, None) is not None:
            return False
    return position == len(plan.expressions) and operand_position == len(plan.operands)


def _row_symbols(plan) -> bool:
    prefix = len(plan.bindings.symbols)
    if not _same(plan.symbols[:prefix], plan.bindings.symbols):
        return False
    expected_ports = []
    for definition in plan.bindings.definitions:
        for join in plan.joins:
            if join.definition is definition.ref:
                expected_ports.extend(
                    port for port in plan.join_ports if port.block is join.ref
                )
        for block in plan.blocks:
            if block.definition is definition.ref:
                expected_ports.extend(
                    port for port in plan.stage_ports if port.block is block.ref
                )
    if len(expected_ports) != len(plan.stage_ports) + len(plan.join_ports) or len(
        plan.symbols
    ) != prefix + len(expected_ports):
        return False
    positions = {scope.ref: 0 for scope in (*plan.blocks, *plan.joins)}
    for i, (symbol, port) in enumerate(
        zip(plan.symbols[prefix:], expected_ports, strict=True)
    ):
        label = (
            port.field.evidence.name
            if isinstance(port, joining.ProjectSQLJoinPort)
            else row.stage_key_label(port.key)
        )
        if (
            type(symbol) is not ProjectSQLSymbol
            or not _ref(
                symbol.ref, plan.scope, ProjectSQLPlanRefKind.SYMBOL, prefix + i
            )
            or symbol.scope is not port.block
            or symbol.subject is not port.ref
            or symbol.namespace is not ProjectSQLSymbolNamespace.FIELD_PORT
            or type(symbol.position) is not int
            or symbol.position != positions[port.block]
            or type(symbol.label) is not str
            or symbol.label != label
        ):
            return False
        positions[port.block] += 1
    return True


def _row_origins_and_demands(plan):
    Issue, R, P, K = (
        ProjectSQLPlanVerificationIssue,
        ProjectSQLOriginRole,
        ProjectSQLOriginProvenance,
        ProjectSQLPlanRefKind,
    )
    bindings = plan.bindings
    join_by_ref = {j.ref: j for j in plan.joins}
    blocks = {b.ref: b for b in plan.blocks}
    expressions = {e.ref: e for e in plan.expressions}
    ports = {p.ref: p for p in plan.stage_ports}
    exports = {p.ref: p for p in plan.all_exports}
    specs = []
    for block in plan.blocks:
        specs.append(
            (
                block.ref,
                R.SELECT_BLOCK,
                P.GENERATED_STRUCTURE,
                block.selected.owner,
                block.selected.owner.definition,
                block.selected,
                (block.predecessor, block.boundary.ref)
                if isinstance(block.boundary, joining.ProjectSQLJoinTail)
                else (block.predecessor,),
            )
        )
    for port in plan.stage_ports:
        owner = blocks[port.block].selected.owner
        cause = (
            port.key.binding
            if isinstance(port.key, row.ProjectJoinedLetOccurrence)
            else port.key
            if isinstance(port.key, LetBinding)
            else owner.definition.from_clause
        )
        specs.append(
            (
                port.ref,
                R.STAGE_PORT,
                P.VALUE,
                owner,
                cause,
                port.type_evidence,
                (port.source,),
            )
        )
    for site in plan.expression_sites:
        specs.append(
            (
                site.ref,
                R.EXPRESSION_SITE,
                P.TYPE_PROOF,
                site.owner,
                site.occurrence,
                site.evidence,
                join_by_ref[site.block].inputs
                if isinstance(site, row.ProjectSQLMatchSite)
                else (site.block,),
            )
        )
    for value in plan.expressions:
        dependencies = (
            (value.port,)
            if isinstance(
                value,
                (
                    row.ProjectSQLReference,
                    row.ProjectSQLJoinedReference,
                    row.ProjectSQLMatchReference,
                    aggregation.ProjectSQLResultReference,
                    windows.ProjectSQLWindowReference,
                ),
            )
            else ()
        )
        specs.append(
            (
                value.ref,
                R.EXPRESSION,
                P.VALUE,
                value.site.owner,
                value.expression,
                value.value_type,
                (value.site.ref, *dependencies),
            )
        )
    for operand in plan.operands:
        specs.append(
            (
                operand.ref,
                R.OPERAND,
                P.VALUE,
                operand.site.owner,
                expressions[operand.parent].expression,
                expressions[operand.child].value_type,
                (operand.parent, operand.child),
            )
        )
    for value in plan.let_values:
        specs.append(
            (
                value.ref,
                R.LET_VALUE,
                P.VALUE,
                value.site.owner,
                value.site.occurrence,
                value.site.evidence,
                (value.expression, value.port),
            )
        )
    for item in plan.filters:
        specs.append(
            (
                item.ref,
                R.FILTER,
                P.MEMBERSHIP,
                item.site.owner,
                item.site.occurrence,
                item.site.evidence,
                (item.site.block, item.predicate),
            )
        )
    for projection in plan.projections:
        specs.extend(
            (
                (
                    projection.ref,
                    R.PROJECTION,
                    P.VALUE,
                    projection.site.owner,
                    projection.semantic.item,
                    projection.semantic,
                    (projection.expression,),
                ),
                (
                    projection.export,
                    R.EXPORT,
                    P.VALUE,
                    projection.site.owner,
                    projection.semantic.item,
                    exports[projection.export].field,
                    (projection.ref,),
                ),
            )
        )
    for symbol in plan.symbols[len(bindings.symbols) :]:
        if symbol.subject not in ports:
            continue
        port = ports[symbol.subject]
        block = blocks[port.block]
        specs.append(
            (
                symbol.ref,
                R.SYMBOL,
                P.GENERATED_STRUCTURE,
                block.selected.owner,
                block.selected.owner.definition,
                port.type_evidence,
                (port.ref,),
            )
        )
    prefix = len(bindings.origins)
    if not _same(plan.origins[:prefix], bindings.origins):
        return (Issue.ORIGINS,)
    for i, spec in enumerate(specs):
        if not _origin_matches(plan.origins[prefix + i], spec, plan.scope, prefix + i):
            return (Issue.ORIGINS,)
    source_origins = {
        spec[0]: plan.origins[prefix + i].ref for i, spec in enumerate(specs)
    }
    demand_prefix = len(bindings.demands)
    if not _same(plan.demands[:demand_prefix], bindings.demands):
        return (Issue.DEMANDS,)
    subjects = (*plan.expressions, *plan.stage_ports, *plan.filters, *plan.blocks)
    join_count = sum(
        len(values)
        for values in (
            plan.joins,
            plan.join_inputs,
            plan.join_ports,
            plan.relationship_matches,
            plan.join_tails,
            plan.single_matches,
            plan.single_match_proofs,
        )
    )
    aggregate_count = sum(
        len(values)
        for values in (
            plan.aggregations,
            plan.group_keys,
            plan.aggregates,
            plan.aggregate_projections,
            plan.aggregate_risks,
        )
    )
    window_count = sum(
        len(values)
        for values in (
            plan.windows,
            plan.window_uses,
            plan.window_arguments,
            plan.window_policies,
            plan.window_projections,
        )
    )
    result_count = sum(
        len(values)
        for values in (
            plan.result_boundaries,
            plan.result_ports,
            plan.distincts,
            plan.quotient_fields,
            plan.orders,
            plan.order_items,
            plan.order_expressions,
            plan.order_uses,
            plan.hidden_order_requirements,
            plan.result_limits,
            plan.result_exports,
        )
    )
    set_count = (
        len(plan.set_bodies)
        + len(plan.set_operands)
        + len(plan.set_inputs)
        + len(plan.set_columns)
    )
    set_demands = (
        set_count
        + len(plan.set_bodies)
        + sum(body.requires_equivalence for body in plan.set_bodies)
    )
    if len(plan.demands) != demand_prefix + len(
        subjects
    ) + join_count + aggregate_count + window_count + result_count + set_demands + len(
        plan.bind_uses
    ) or len(plan.origins) != prefix + len(specs) + len(
        subjects
    ) + 2 * join_count + len(plan.join_ports) + 2 * aggregate_count + len(
        plan.aggregate_projections
    ) + 2 * window_count + len(
        plan.window_projections
    ) + 2 * result_count + set_count + set_demands + len(plan.literal_sites) + len(
        plan.literal_slots
    ) + len(plan.fixed_envelope.values) + 2 * len(plan.bind_uses):
        return (Issue.DEMANDS,)
    operand_types = {e.ref: [] for e in plan.expressions}
    for operand in plan.operands:
        operand_types[operand.parent].append(expressions[operand.child].value_type)
    for i, subject in enumerate(subjects):
        demand = plan.demands[demand_prefix + i]
        origin_position = prefix + len(specs) + i
        origin = plan.origins[origin_position]
        if (
            not _ref(demand.ref, plan.scope, K.DEMAND, demand_prefix + i)
            or demand.subject is not subject.ref
            or demand.origin is not origin.ref
        ):
            return (Issue.DEMANDS,)
        if subject.ref in expressions:
            value = subject
            valid = (
                type(demand) is row.ProjectSQLExpressionDemand
                and demand.site is value.site
                and demand.expression is value.expression
                and demand.value_type is value.value_type
                and _same(demand.operand_types, tuple(operand_types[value.ref]))
            )
            spec = (
                demand.ref,
                R.DEMAND,
                P.TYPE_PROOF,
                value.site.owner,
                value.expression,
                value.value_type,
                (source_origins[value.ref],),
            )
        elif isinstance(subject, row.ProjectSQLStagePort):
            block = blocks[subject.block]
            valid = (
                type(demand) is row.ProjectSQLStageValueDemand
                and demand.block is subject.block
                and demand.type_evidence is subject.type_evidence
            )
            spec = (
                demand.ref,
                R.DEMAND,
                P.TYPE_PROOF,
                block.selected.owner,
                block.selected.owner.definition,
                subject.type_evidence,
                (source_origins[subject.ref],),
            )
        elif isinstance(subject, row.ProjectSQLFilter):
            valid = (
                type(demand) is row.ProjectSQLFilterDemand
                and demand.site is subject.site
                and demand.value_type is expressions[subject.predicate].value_type
                and demand.retention_effects is subject.retention_effects
            )
            spec = (
                demand.ref,
                R.DEMAND,
                P.MEMBERSHIP,
                subject.site.owner,
                subject.site.occurrence,
                subject.site.evidence,
                (source_origins[subject.ref],),
            )
        else:
            valid = (
                type(demand) is row.ProjectSQLScopeDemand
                and demand.predecessor is subject.predecessor
                and _same(demand.inputs, subject.inputs)
                and _same(demand.exports, subject.exports)
            )
            spec = (
                demand.ref,
                R.DEMAND,
                P.GENERATED_STRUCTURE,
                subject.selected.owner,
                subject.selected.owner.definition,
                subject.selected,
                (source_origins[subject.ref],),
            )
        if not valid:
            return (Issue.DEMANDS,)
        if not _origin_matches(origin, spec, plan.scope, origin_position):
            return (Issue.ORIGINS,)
    return _join_origins_and_demands(
        plan, prefix + len(specs) + len(subjects), demand_prefix + len(subjects)
    )


def _join_origins_and_demands(plan, origin_start, demand_start):
    Issue, R, P, K = (
        ProjectSQLPlanVerificationIssue,
        ProjectSQLOriginRole,
        ProjectSQLOriginProvenance,
        ProjectSQLPlanRefKind,
    )
    joins = {join.ref: join for join in plan.joins}
    ports = {port.ref: port for port in plan.join_ports}
    obligations = {value.ref: value for value in plan.single_matches}
    witnesses = (
        *plan.joins,
        *plan.join_inputs,
        *plan.join_ports,
        *plan.relationship_matches,
        *plan.join_tails,
        *plan.single_matches,
        *plan.single_match_proofs,
    )
    for i, witness in enumerate(witnesses):
        if isinstance(witness, joining.ProjectSQLJoin):
            kind, role, provenance = (
                joining.ProjectSQLJoinDemandKind.JOIN_ROWS,
                R.JOIN,
                P.MEMBERSHIP,
            )
            owner, cause = (
                witness.source.condition.use.owner,
                witness.source.condition.use.clause,
            )
            antecedents = (
                *witness.inputs,
                *witness.equalities,
                *(() if witness.on is None else (witness.on,)),
            )
        elif isinstance(witness, joining.ProjectSQLJoinInput):
            kind, role, provenance = (
                joining.ProjectSQLJoinDemandKind.MATCH_INPUT,
                R.JOIN_INPUT,
                P.MEMBERSHIP,
            )
            join = joins[witness.join]
            owner, cause = (
                join.source.condition.use.owner,
                join.source.condition.use.clause,
            )
            antecedents = (
                (witness.producer,)
                if witness.producer is not None
                else (witness.predecessor,)
            )
        elif isinstance(witness, joining.ProjectSQLJoinPort):
            matching = witness.kind is joining.ProjectSQLJoinPortKind.MATCH
            kind = (
                joining.ProjectSQLJoinDemandKind.MATCH_FIELD
                if matching
                else joining.ProjectSQLJoinDemandKind.OUTPUT_FIELD
            )
            role, provenance = R.JOIN_PORT, P.MEMBERSHIP if matching else P.VALUE
            join = joins[witness.block]
            owner, cause = (
                join.source.condition.use.owner,
                join.source.condition.use.clause,
            )
            antecedents = (
                (witness.source, witness.input)
                if matching
                else (witness.source, witness.block)
            )
        elif isinstance(witness, joining.ProjectSQLRelationshipMatch):
            kind, role, provenance = (
                joining.ProjectSQLJoinDemandKind.RELATIONSHIP_EQUALITY,
                R.RELATIONSHIP_MATCH,
                P.MEMBERSHIP,
            )
            join = joins[witness.join]
            source = (
                witness.source.correspondence
                if isinstance(witness.source, joining.ProjectIRJoinMatchFieldPair)
                else witness.source
            )
            owner, cause, antecedents = (
                join.source.condition.use.owner,
                source.comparison,
                witness.authored_operands,
            )
        elif isinstance(witness, joining.ProjectSQLJoinTail):
            kind, role, provenance = (
                joining.ProjectSQLJoinDemandKind.POST_MATCH_SCOPE,
                R.JOIN_TAIL,
                P.GENERATED_STRUCTURE,
            )
            owner = joins[witness.join].source.condition.use.owner
            cause, antecedents = owner.definition, (witness.join, *witness.ports)
        elif isinstance(witness, joining.ProjectSQLSingleMatch):
            kind, role, provenance = (
                joining.ProjectSQLJoinDemandKind.SINGLE_MATCH,
                R.SINGLE_MATCH,
                P.TYPE_PROOF,
            )
            owner, cause, antecedents = (
                witness.request.owner,
                witness.request.use.clause,
                (*witness.joins, *witness.proofs),
            )
        else:
            kind, role, provenance = (
                joining.ProjectSQLJoinDemandKind.PROOF_CONTEXT,
                R.SINGLE_MATCH_PROOF,
                P.TYPE_PROOF,
            )
            request = obligations[witness.obligation].request
            owner, cause, antecedents = (
                request.owner,
                request.use.clause,
                (*witness.joins, *witness.producers, *witness.children),
            )
        offset = origin_start + 2 * i
        origin, demand_origin = plan.origins[offset : offset + 2]
        demand = plan.demands[demand_start + i]
        if not _origin_matches(
            origin,
            (witness.ref, role, provenance, owner, cause, witness, antecedents),
            plan.scope,
            offset,
        ):
            return (Issue.ORIGINS,)
        if (
            type(demand) is not joining.ProjectSQLJoinDemand
            or not _ref(demand.ref, plan.scope, K.DEMAND, demand_start + i)
            or demand.subject is not witness.ref
            or demand.kind is not kind
            or demand.witness is not witness
            or demand.origin is not demand_origin.ref
        ):
            return (Issue.DEMANDS,)
        if not _origin_matches(
            demand_origin,
            (demand.ref, R.DEMAND, provenance, owner, cause, witness, (origin.ref,)),
            plan.scope,
            offset + 1,
        ):
            return (Issue.ORIGINS,)
    offset = origin_start + 2 * len(witnesses)
    symbols = tuple(
        symbol
        for symbol in plan.symbols[len(plan.bindings.symbols) :]
        if symbol.subject in ports
    )
    for i, symbol in enumerate(symbols):
        port = ports[symbol.subject]
        join = joins[port.block]
        spec = (
            symbol.ref,
            R.SYMBOL,
            P.GENERATED_STRUCTURE,
            join.source.condition.use.owner,
            join.source.condition.use.clause,
            port,
            (port.ref,),
        )
        if not _origin_matches(plan.origins[offset + i], spec, plan.scope, offset + i):
            return (Issue.ORIGINS,)
    return _aggregate_origins_and_demands(
        plan, offset + len(symbols), demand_start + len(witnesses)
    )


def _aggregate_origins_and_demands(plan, origin_position, demand_position):
    Issue, R, P, K = (
        ProjectSQLPlanVerificationIssue,
        ProjectSQLOriginRole,
        ProjectSQLOriginProvenance,
        ProjectSQLPlanRefKind,
    )
    stages = {a.ref: a for a in plan.aggregations}
    blocks = {b.ref: b for b in plan.blocks}
    exports = {p.ref: p for p in plan.all_exports}
    for witness in (
        *plan.aggregations,
        *plan.group_keys,
        *plan.aggregates,
        *plan.aggregate_projections,
        *plan.aggregate_risks,
    ):
        stage = (
            witness
            if isinstance(witness, aggregation.ProjectSQLAggregation)
            else stages[witness.aggregation]
        )
        owner = blocks[stage.block].selected.owner
        if isinstance(witness, aggregation.ProjectSQLAggregation):
            kind, role, provenance = (
                aggregation.ProjectSQLAggregateDemandKind.GROUPING_AND_EMPTY_INPUT,
                R.AGGREGATION,
                P.MEMBERSHIP,
            )
            cause, antecedents = owner.definition, (witness.block,)
        elif isinstance(witness, aggregation.ProjectSQLGroupKey):
            kind, role, provenance = (
                aggregation.ProjectSQLAggregateDemandKind.GROUP_COMPARISON,
                R.GROUP_KEY,
                P.VALUE,
            )
            cause, antecedents = (
                witness.source.item,
                (witness.aggregation, witness.input),
            )
        elif isinstance(witness, aggregation.ProjectSQLAggregate):
            kind, role, provenance = (
                aggregation.ProjectSQLAggregateDemandKind.AGGREGATE_OPERATION,
                R.AGGREGATE,
                P.VALUE,
            )
            cause, antecedents = (
                witness.source.item,
                (witness.aggregation, *witness.arguments),
            )
        elif isinstance(witness, aggregation.ProjectSQLAggregateProjection):
            kind, role, provenance = (
                aggregation.ProjectSQLAggregateDemandKind.RESULT_PROJECTION,
                R.AGGREGATE_PROJECTION,
                P.VALUE,
            )
            cause, antecedents = (
                witness.semantic.item,
                (witness.aggregation, witness.input),
            )
        else:
            kind, role, provenance = (
                aggregation.ProjectSQLAggregateDemandKind.RETAINED_RISK,
                R.AGGREGATE_RISK,
                P.TYPE_PROOF,
            )
            cause, antecedents = owner.definition, (witness.aggregation,)
        origin, demand_origin = plan.origins[origin_position : origin_position + 2]
        demand = plan.demands[demand_position]
        if not _origin_matches(
            origin,
            (witness.ref, role, provenance, owner, cause, witness, antecedents),
            plan.scope,
            origin_position,
        ):
            return (Issue.ORIGINS,)
        if (
            type(demand) is not aggregation.ProjectSQLAggregateDemand
            or not _ref(demand.ref, plan.scope, K.DEMAND, demand_position)
            or demand.kind is not kind
            or demand.subject is not witness.ref
            or demand.witness is not witness
            or demand.origin is not demand_origin.ref
        ):
            return (Issue.DEMANDS,)
        if not _origin_matches(
            demand_origin,
            (demand.ref, R.DEMAND, provenance, owner, cause, witness, (origin.ref,)),
            plan.scope,
            origin_position + 1,
        ):
            return (Issue.ORIGINS,)
        origin_position += 2
        demand_position += 1
        if isinstance(witness, aggregation.ProjectSQLAggregateProjection):
            if not _origin_matches(
                plan.origins[origin_position],
                (
                    witness.export,
                    R.EXPORT,
                    P.VALUE,
                    owner,
                    witness.semantic.item,
                    exports[witness.export].field,
                    (witness.ref,),
                ),
                plan.scope,
                origin_position,
            ):
                return (Issue.ORIGINS,)
            origin_position += 1
    return _window_origins_and_demands(plan, origin_position, demand_position)


def _window_origins_and_demands(plan, origin_position, demand_position):
    Issue, R, P, K = (
        ProjectSQLPlanVerificationIssue,
        ProjectSQLOriginRole,
        ProjectSQLOriginProvenance,
        ProjectSQLPlanRefKind,
    )
    values = {value.ref: value for value in plan.windows}
    blocks = {block.ref: block for block in plan.blocks}
    exports = {export.ref: export for export in plan.all_exports}
    for witness in (
        *plan.windows,
        *plan.window_uses,
        *plan.window_arguments,
        *plan.window_policies,
        *plan.window_projections,
    ):
        value = (
            witness
            if isinstance(witness, windows.ProjectSQLWindow)
            else values[witness.window]
        )
        owner = blocks[value.block].selected.owner
        if isinstance(witness, windows.ProjectSQLWindow):
            kind, role, provenance = (
                windows.ProjectSQLWindowDemandKind.INPUT_BAG_AND_RESULT,
                R.WINDOW,
                P.MEMBERSHIP,
            )
            cause, antecedents = witness.authored, (witness.block, *witness.inputs)
        elif isinstance(witness, windows.ProjectSQLWindowUse):
            kind, role, provenance = (
                windows.ProjectSQLWindowDemandKind.INPUT_USE,
                R.WINDOW_USE,
                P.VALUE,
            )
            cause, antecedents = (
                witness.expression,
                (witness.window,)
                if witness.input is None
                else (witness.window, witness.input),
            )
        elif isinstance(witness, windows.ProjectSQLWindowArgument):
            kind, role, provenance = (
                windows.ProjectSQLWindowDemandKind.ARGUMENT,
                R.WINDOW_ARGUMENT,
                P.VALUE,
            )
            cause, antecedents = (
                witness.expression,
                (witness.window,)
                if witness.use is None
                else (witness.window, witness.use),
            )
        elif isinstance(witness, windows.ProjectSQLWindowPolicy):
            kind, role, provenance = (
                windows.ProjectSQLWindowDemandKind.POLICY,
                R.WINDOW_POLICY,
                P.TYPE_PROOF,
            )
            cause, antecedents = value.authored, (witness.window,)
        else:
            kind, role, provenance = (
                windows.ProjectSQLWindowDemandKind.PROJECTION,
                R.WINDOW_PROJECTION,
                P.VALUE,
            )
            cause, antecedents = witness.semantic.item, (witness.window, witness.input)
        original, demand_origin = plan.origins[origin_position : origin_position + 2]
        demand = plan.demands[demand_position]
        if not _origin_matches(
            original,
            (witness.ref, role, provenance, owner, cause, witness, antecedents),
            plan.scope,
            origin_position,
        ):
            return (Issue.ORIGINS,)
        if (
            type(demand) is not windows.ProjectSQLWindowDemand
            or not _ref(demand.ref, plan.scope, K.DEMAND, demand_position)
            or demand.subject is not witness.ref
            or demand.kind is not kind
            or demand.witness is not witness
            or demand.origin is not demand_origin.ref
        ):
            return (Issue.DEMANDS,)
        if not _origin_matches(
            demand_origin,
            (demand.ref, R.DEMAND, provenance, owner, cause, witness, (original.ref,)),
            plan.scope,
            origin_position + 1,
        ):
            return (Issue.ORIGINS,)
        origin_position += 2
        demand_position += 1
        if isinstance(witness, windows.ProjectSQLWindowProjection):
            if not _origin_matches(
                plan.origins[origin_position],
                (
                    witness.export,
                    R.EXPORT,
                    P.VALUE,
                    owner,
                    witness.semantic.item,
                    exports[witness.export].field,
                    (witness.ref,),
                ),
                plan.scope,
                origin_position,
            ):
                return (Issue.ORIGINS,)
            origin_position += 1
    return _result_origins_and_demands(plan, origin_position, demand_position)


def _order_input_linkage(order, entry, rows, aggregate, window):
    from pietto._project.module_semantic_fact_preservation import (
        ProjectModuleOrderReferenceRole,
    )

    if (
        type(order) is not results.ProjectRelationOrdering
        or order.owner is not entry.owner
        or order.clause is not entry.owner.definition.order_by_clause
        or type(order.inputs) is not tuple
        or len(order.items) != len(order.clause.items)
        or len(order.inputs) != len(order.items)
    ):
        return False
    source_root = (
        entry.semantic_entry.root
        if isinstance(entry, ProjectIRCompletedQueryBlockOutput)
        else entry.semantic_entry.fragment.semantic_facts
    )
    for ordinal, (item, original, uses) in enumerate(
        zip(order.items, order.clause.items, order.inputs, strict=True)
    ):
        if (
            type(item) is not results.ProjectRelationOrderItem
            or item.owner is not entry.owner
            or item.clause is not order.clause
            or type(item.source_ordinal) is not int
            or item.source_ordinal != ordinal
            or item.item is not original
            or item.expression is not original.expression
            or type(item.direction) is not ProjectRelationOrderDirection
            or item.direction.value
            != ("asc" if original.direction is None else original.direction)
            or item.value_type.kind is not ValueTypeKind.KNOWN
            or type(uses) is not tuple
        ):
            return False
        source = item.source
        scalar = isinstance(
            source,
            (
                results.ProjectNoJoinScalarExpression,
                results.ProjectConcreteJoinedNamespaceExpression,
            ),
        )
        if scalar:
            if (
                source.expression is not item.expression
                or source.value_type is not item.value_type
            ):
                return False
            expected = tuple(
                n
                for n in row.scalar_nodes(item.expression)
                if isinstance(n, (NameExpr, DottedNameExpr))
            )
            if isinstance(source, results.ProjectNoJoinScalarExpression):
                if (
                    not isinstance(rows, row.ProjectSQLRowAuthority)
                    or source.owner is not entry.owner
                    or source.input_schema is not rows.input_schema
                    or source.let_scope is not rows.let_scope
                    or source.status.value != "concrete"
                ):
                    return False
            elif (
                not isinstance(rows, row.ProjectSQLJoinedRowAuthority)
                or source.namespace is not rows.namespaces.post_let
            ):
                return False
        else:
            expected = (item.expression,)
            if isinstance(source, windows.ProjectModuleWindowOutputFact):
                if window is None or not any(
                    source is selected for selected in window.selected
                ):
                    return False
            elif isinstance(source, windows.ProjectSelectedWindowResultBinding):
                if window is None or not any(
                    source is selected for selected in window.selected
                ):
                    return False
            elif isinstance(source, windows.ProjectJoinedWindowInputBinding):
                if not isinstance(
                    source_root, windows.ProjectConcreteJoinedQualify
                ) or not any(
                    source is target
                    for target in source_root.window_stage.post_window.pre_window.bindings
                ):
                    return False
            else:
                if (
                    type(source) is not ProjectModuleClauseDependencyFact
                    or isinstance(source_root, windows.ProjectConcreteJoinedQualify)
                    or source.owner is not entry.owner
                    or type(source.source_ordinal) is not int
                    or source.source_ordinal != ordinal
                    or source.status is not ProjectModuleCandidateBucketStatus.CONCRETE
                    or not any(source is f for f in source_root.clause_dependencies)
                    or source.source_occurrence is not item.item
                    or len(source.target_occurrences) != 1
                ):
                    return False
        if not _same(tuple(use.expression for use in uses), expected):
            return False
        types = {id(node): value for node, value in results.order_types(item).items()}
        for position, use in enumerate(uses):
            if (
                type(use) is not results.ProjectRelationOrderInput
                or use.item is not item
                or type(use.position) is not int
                or use.position != position
                or use.value_type is not types.get(id(use.expression))
            ):
                return False
            resolution = use.resolution
            if isinstance(source, results.ProjectNoJoinScalarExpression):
                if (
                    type(resolution) is not ProjectModuleOrderReferenceFact
                    or resolution.owner is not entry.owner
                    or resolution.item is not item.item
                    or resolution.expression is not use.expression
                    or resolution.role
                    is not ProjectModuleOrderReferenceRole.ORDER_VALUE
                    or type(resolution.container_ordinal) is not int
                    or resolution.container_ordinal != ordinal
                    or type(resolution.dependency_ordinal) is not int
                    or resolution.dependency_ordinal != position
                    or resolution.status
                    is not ProjectModuleCandidateBucketStatus.CONCRETE
                ):
                    return False
                target = resolution.input_field
                if target is not None:
                    if not any(
                        target is field for field in source.input_schema.fields.values()
                    ):
                        return False
                else:
                    if len(resolution.let_candidates) != 1 or not any(
                        resolution.let_candidates[0] is binding
                        for binding in source.let_scope.bindings
                    ):
                        return False
                    target = resolution.let_candidates[0]
                if use.target is not target or use.determination_target is not (
                    target.expression if isinstance(target, LetBinding) else target
                ):
                    return False
            elif isinstance(source, results.ProjectConcreteJoinedNamespaceExpression):
                if (
                    not isinstance(
                        resolution,
                        (
                            row.ProjectJoinedLetReferenceResolution,
                            ProjectScalarReferenceResolution,
                        ),
                    )
                    or len(source.resolutions) != len(uses)
                    or source.resolutions[position] is not resolution
                    or use.determination_target is not resolution.target
                    or use.target
                    is not (
                        resolution.target.occurrence
                        if isinstance(
                            resolution, row.ProjectJoinedLetReferenceResolution
                        )
                        else resolution.target
                    )
                ):
                    return False
                if (
                    resolution.reference.expression is not use.expression
                    or resolution.reference.environment
                    is not source.namespace.binding_environment.scalar_environment
                    or resolution.target is None
                    or use.value_type is not resolution.target.value_type
                ):
                    return False
                if isinstance(resolution, row.ProjectJoinedLetReferenceResolution):
                    if resolution.namespace is not source.namespace or not any(
                        resolution.target is value
                        for value in source.namespace.let_values
                    ):
                        return False
                elif (
                    resolution.status is not ProjectModuleCandidateBucketStatus.CONCRETE
                    or type(resolution.target.position) is not int
                    or resolution.target.position < 0
                    or len(resolution.candidates) != 1
                    or resolution.candidates[0] is not resolution.target
                    or not any(
                        resolution.target is field
                        for field in source.namespace.visible_fields
                    )
                ):
                    return False
                if isinstance(resolution, ProjectScalarReferenceResolution):
                    original_position, original_field, _ = _source_field_parts(
                        resolution.target.source_field
                    )
                    if (
                        type(original_position) is not int
                        or resolution.target.position != original_position
                        or resolution.target.evidence is not original_field
                    ):
                        return False
            else:
                if resolution is not source:
                    return False
                if isinstance(source, windows.ProjectJoinedWindowInputBinding):
                    target, determination = source, source.stage_output
                elif isinstance(source, ProjectModuleClauseDependencyFact):
                    target = determination = source.target_occurrences[0]
                else:
                    target = determination = source
                if (
                    use.target is not target
                    or use.determination_target is not determination
                ):
                    return False
    return True


def _supplied_strict_proof(
    proof, properties, seed_targets, requested_targets, target_index
):
    """Check this supplied derivation; never search the FD graph for another proof."""
    from pietto._project.project_ir_relational_properties import (
        ProjectIROutputDeterminationStatus,
    )
    from pietto._project.project_row_keys import ProjectRowUniquenessStrength

    if (
        type(proof) is not results.ProjectIROutputDeterminationResult
        or proof.status is not ProjectIROutputDeterminationStatus.PROVEN
    ):
        return False
    index = properties.fd_index
    if any(
        type(field.field_position) is not int
        or field.field_position != position
        or field.output is not properties.output
        for position, field in enumerate(properties.fields)
    ):
        return False
    if any(
        type(index.positions.get(group)) is not int
        or index.positions[group] != position
        for position, group in enumerate(index.universe)
    ):
        return False
    if len(index.positions) != len(index.universe):
        return False
    seed = results.class_targets(target_index, seed_targets)
    requested = results.class_targets(target_index, requested_targets)
    if (
        any(group is None for group in requested)
        or proof.seed.index is not index
        or proof.requested.index is not index
        or proof.closure.seed is not proof.seed
        or proof.closure.classes.index is not index
    ):
        return False
    if not _same(
        proof.seed.classes,
        tuple(
            group for group in index.universe if any(group is target for target in seed)
        ),
    ) or not _same(
        proof.requested.classes,
        tuple(
            group
            for group in index.universe
            if any(group is target for target in requested)
        ),
    ):
        return False
    known = {id(group) for group in proof.seed.classes}
    universe = {id(group): group for group in index.universe}
    if not _same(index.universe, properties.value_classes) or not _same(
        index.facts, properties.fds
    ):
        return False
    for step in proof.closure.witness:
        fact = step.fact
        if (
            not any(fact is value for value in index.facts)
            or fact.strength is not ProjectRowUniquenessStrength.STRICT
            or not any(rule.fact is fact for rule in index.strict_rules)
            or any(rule.fact is fact for rule in index.lax_rules)
            or fact.output is not properties.output
            or any(id(group) not in known for group in fact.determinants)
        ):
            return False
        derived = tuple(group for group in fact.dependents if id(group) not in known)
        if (
            not _same(step.derived, derived)
            or not derived
            or any(
                universe.get(id(group)) is not group
                for group in (*fact.determinants, *fact.dependents)
            )
        ):
            return False
        known.update(id(group) for group in derived)
    if not _same(
        proof.closure.classes.classes,
        tuple(group for group in index.universe if id(group) in known),
    ) or any(id(group) not in known for group in proof.requested.classes):
        return False
    for classes in (proof.seed, proof.requested, proof.closure.classes):
        if type(classes.mask) is not int or classes.mask != sum(
            1 << i
            for i, group in enumerate(index.universe)
            if any(group is member for member in classes.classes)
        ):
            return False
    return True


def _equivalence_links(distinct, entry, completed):
    source = distinct.source
    semantic = entry.semantic_entry
    if (
        type(source) is not results.ProjectDistinct
        or semantic.row_domain.distinct is not source
        or source.owner is not entry.owner
        or source.root is not semantic.root
        or source.clause is not entry.owner.definition.distinct_clause
        or source.fields is not semantic.fields
        or source.equivalence.fields is not source.fields
        or source.equivalence.types is not source.types
        or source.types is not completed.semantic_result.module_type_source_resolutions
    ):
        return False
    fields = source.equivalence.evidence
    if any(
        selected.owner is not entry.owner
        or type(selected.selected_output_ordinal) is not int
        or selected.selected_output_ordinal != position
        or type(selected.identity.field_position) is not int
        or selected.identity.field_position != position
        for position, selected in enumerate(source.fields)
    ):
        return False
    if (
        not fields
        or len(fields) != len(source.fields)
        or len(fields) != len(entry.owner.definition.select_items)
        or type(distinct.global_input) is not bool
        or distinct.global_input is not source.global_input
        or distinct.input_domain is not source.input_domain
        or distinct.origin is not source.origin
        or distinct.uniqueness is not source.uniqueness
        or source.uniqueness.distinct is not source
        or source.uniqueness.nulls_equal is not True
        or source.origin.witness is not source
    ):
        return False
    pending: list[
        tuple[
            results.ProjectRowEquivalenceField,
            results.ProjectCompletedOutputField | ProjectRowEquivalenceInput,
        ]
    ] = list(zip(fields, source.fields, strict=True))
    seen = set()
    resolutions = {
        id(value): value
        for environment in source.types.environments
        for value in environment.type_resolutions
    }
    while pending:
        value, selected = pending.pop()
        if (id(value), id(selected)) in seen:
            continue
        seen.add((id(value), id(selected)))
        if (
            value.selected is not selected
            or value.types is not source.types
            or value.reason is not None
            or value.parents is not selected.type_sources
        ):
            return False
        if (
            value.resolution is not None
            and resolutions.get(id(value.resolution)) is not value.resolution
        ):
            return False
        if selected.field.field_def is not None and (
            value.resolution is None
            or value.resolution.reference.type_expr
            is not selected.field.field_def.type_expr
        ):
            return False
        if value.decimal is not None:
            if (
                type(value.decimal.precision) is not int
                or type(value.decimal.scale) is not int
            ):
                return False
            if value.parents and value.decimal is not value.parents[0].decimal:
                return False
            if not value.parents and value.decimal_type_expr is None:
                return False
        pending.extend((parent, parent.selected) for parent in value.parents)
    return True


def _result_structure(plan):
    K = ProjectSQLPlanRefKind
    orderings = results.order_index(plan.scope.completed)
    class_indexes = {}
    inventories = (
        ("result_boundaries", results.ProjectSQLResultBoundary, K.RESULT_BOUNDARY),
        ("result_ports", results.ProjectSQLResultPort, K.RESULT_PORT),
        ("distincts", results.ProjectSQLDistinct, K.DISTINCT),
        ("quotient_fields", results.ProjectSQLQuotientField, K.QUOTIENT_FIELD),
        ("orders", results.ProjectSQLOrder, K.ORDER),
        ("order_items", results.ProjectSQLOrderItem, K.ORDER_ITEM),
        ("order_expressions", results.ProjectSQLOrderExpression, K.ORDER_EXPRESSION),
        ("order_uses", results.ProjectSQLOrderUse, K.ORDER_USE),
        (
            "hidden_order_requirements",
            results.ProjectSQLHiddenOrderRequirement,
            K.HIDDEN_ORDER_REQUIREMENT,
        ),
        ("result_limits", results.ProjectSQLResultLimit, K.RESULT_LIMIT),
        ("result_exports", results.ProjectSQLResultExport, K.RESULT_EXPORT),
    )
    for name, cls, kind in inventories:
        if not _inventory(getattr(plan, name), cls, plan.scope, kind):
            return False
    cursors = {name: 0 for name, _, _ in inventories}

    def take(name, count=1):
        start = cursors[name]
        cursors[name] += count
        values = getattr(plan, name)[start : start + count]
        if len(values) != count:
            raise ValueError("Incomplete result inventory")
        return values

    projections = {
        p.export: p
        for p in (
            *plan.projections,
            *plan.aggregate_projections,
            *plan.window_projections,
        )
    }
    blocks = {
        b.definition: b
        for b in plan.blocks
        if b.kind is row.ProjectSQLStageKind.PROJECTION
    }
    stage_ports = {p.ref: p for p in plan.stage_ports}
    set_bodies = {body.definition: body for body in plan.set_bodies}
    set_columns = {column.ref: column for column in plan.set_columns}
    for definition in plan.bindings.definitions:
        entry, authored = definition.entry, definition.entry.owner.definition
        if isinstance(authored, SetRelationDef):
            if not isinstance(entry, ProjectIRCompletedSetOperationOutput):
                return False
            body = set_bodies[definition.ref]
            outputs = take("result_ports", len(definition.exports))
            if not _same(body.outputs, tuple(port.ref for port in outputs)) or len(
                body.columns
            ) != len(outputs):
                return False
            for i, (port, canonical, column_ref, semantic) in enumerate(
                zip(
                    outputs,
                    definition.exports,
                    body.columns,
                    entry.semantic_entry.fields,
                    strict=True,
                )
            ):
                column = set_columns[column_ref]
                if (
                    port.definition is not definition.ref
                    or port.boundary is not body.ref
                    or port.role is not results.ProjectSQLResultPortRole.OUTPUT
                    or type(port.position) is not int
                    or port.position != i
                    or port.canonical is not canonical
                    or port.key is not semantic
                    or port.type_evidence is not semantic.field
                    or port.source is not column.ref
                    or column.output is not port.ref
                ):
                    return False
            exports = take("result_exports", len(outputs))
            if any(
                image.definition is not definition.ref
                or image.canonical is not canonical
                or image.port is not port.ref
                for image, canonical, port in zip(
                    exports, definition.exports, outputs, strict=True
                )
            ):
                return False
            continue
        if not isinstance(authored, (TableDef, QueryDef)):
            continue
        expected_kinds = []
        if authored.distinct_clause is not None:
            expected_kinds.append("distinct")
        if authored.order_by_clause is not None:
            expected_kinds.append("relation_ordering")
        if authored.limit_clause is not None:
            expected_kinds.append("limit")
        operators = tuple(
            op
            for op in _operators(entry)
            if op.kind.value in {"distinct", "relation_ordering", "limit"}
        )
        if tuple(op.kind.value for op in operators) != tuple(expected_kinds):
            return False
        projection = blocks[definition.ref]
        aggregate = aggregation.authority(plan.scope.completed, entry)
        rows = row.row_authority(plan.scope.completed, entry)
        window = windows.authority(entry)
        order = results.ordering(entry, orderings)
        quotient = results.distinct(entry)
        if (quotient is None) is not (authored.distinct_clause is None) or (
            authored.order_by_clause is not None
            and not _order_input_linkage(order, entry, rows, aggregate, window)
        ):
            return False
        pre_projection = {
            id(stage_ports[p].key): stage_ports[p] for p in projection.inputs
        }
        specs = [
            (projections[p.ref].ref, p, p, p.field.evidence) for p in definition.exports
        ]
        if order is not None and quotient is None:
            seen = set()
            for uses in order.inputs:
                for use in uses:
                    key = results.order_key(use, aggregate)
                    if id(key) in seen:
                        continue
                    seen.add(id(key))
                    source = pre_projection[id(key)]
                    if source.key is not key:
                        return False
                    specs.append((source.ref, None, key, source.type_evidence))
        carried = take("result_ports", len(specs))
        for i, (port, (source, canonical, key, evidence)) in enumerate(
            zip(carried, specs, strict=True)
        ):
            if (
                port.definition is not definition.ref
                or port.boundary is not projection.ref
                or port.role is not results.ProjectSQLResultPortRole.PROJECTION
                or type(port.position) is not int
                or port.position != i
                or port.source is not source
                or port.canonical is not canonical
                or port.key is not key
                or port.type_evidence is not evidence
            ):
                return False
        predecessor = projection.ref
        targets = results.selected_targets(plan.scope.completed, entry)
        for position, operator in enumerate(operators):
            (boundary,) = take("result_boundaries")
            if (
                boundary.definition is not definition.ref
                or type(boundary.position) is not int
                or boundary.position != position
                or type(boundary.kind) is not results.ProjectSQLResultKind
                or boundary.kind.value != operator.kind.value
                or boundary.predecessor is not predecessor
                or boundary.operator is not operator
                or boundary.properties is not results.result_properties(entry, operator)
            ):
                return False
            inputs = take("result_ports", len(carried))
            visible = tuple(p for p in inputs if p.canonical is not None)
            outputs = take("result_ports", len(visible))
            if (
                not _same(boundary.inputs, tuple(p.ref for p in inputs))
                or not _same(boundary.outputs, tuple(p.ref for p in outputs))
                or not _same(tuple(p.canonical for p in visible), definition.exports)
            ):
                return False
            for role, values, sources in (
                (results.ProjectSQLResultPortRole.INPUT, inputs, carried),
                (results.ProjectSQLResultPortRole.OUTPUT, outputs, visible),
            ):
                for i, (port, original) in enumerate(zip(values, sources, strict=True)):
                    if (
                        port.definition is not definition.ref
                        or port.boundary is not boundary.ref
                        or port.role is not role
                        or type(port.position) is not int
                        or port.position != i
                        or port.source is not original.ref
                        or port.canonical is not original.canonical
                        or port.key is not original.key
                        or port.type_evidence is not original.type_evidence
                    ):
                        return False
            if boundary.kind is results.ProjectSQLResultKind.DISTINCT:
                if quotient is None:
                    return False
                (value,) = take("distincts")
                if (
                    value.boundary is not boundary.ref
                    or not _equivalence_links(value, entry, plan.scope.completed)
                    or type(value.comparison) is not results.ProjectIRDistinctComparison
                    or value.comparison is not operator.evidence
                    or value.comparison.semantic is not quotient
                    or len(inputs) != len(definition.exports)
                ):
                    return False
                comparison = value.comparison
                projection_ops = tuple(
                    op
                    for op in _operators(entry)
                    if op.kind.value == "final_projection"
                )
                if (
                    len(projection_ops) != 1
                    or comparison.input_output.row_shape.operator
                    is not projection_ops[0]
                    or len(comparison.fields) != len(quotient.fields)
                    or any(
                        field.semantic_source is not selected
                        or field.final_identity is not selected.identity
                        for field, selected in zip(
                            comparison.fields, quotient.fields, strict=True
                        )
                    )
                ):
                    return False
                fields = take("quotient_fields", len(inputs))
                if not _same(value.fields, tuple(f.ref for f in fields)):
                    return False
                for i, (field, incoming, outgoing, evidence) in enumerate(
                    zip(
                        fields,
                        inputs,
                        outputs,
                        quotient.equivalence.evidence,
                        strict=True,
                    )
                ):
                    if (
                        field.distinct is not value.ref
                        or type(field.position) is not int
                        or field.position != i
                        or field.canonical is not definition.exports[i]
                        or field.input is not incoming.ref
                        or field.output is not outgoing.ref
                        or field.equivalence is not evidence
                    ):
                        return False
            elif boundary.kind is results.ProjectSQLResultKind.ORDER:
                if (
                    not isinstance(order, results.ProjectRelationOrdering)
                    or order.inputs is None
                ):
                    return False
                (value,) = take("orders")
                if value.boundary is not boundary.ref or value.source is not order:
                    return False
                if (
                    isinstance(entry, ProjectIRCompletedQueryBlockOutput)
                    and operator.evidence is not order
                ):
                    return False
                visible_targets = {}
                for original_targets, port in zip(targets, inputs):
                    for target in original_targets:
                        visible_targets.setdefault(id(target), []).append(port.ref)
                helpers = {id(p.key): p for p in inputs if p.canonical is None}
                items = take("order_items", len(order.items))
                if not _same(value.items, tuple(item.ref for item in items)):
                    return False
                for i, (item, source, original_uses) in enumerate(
                    zip(items, order.items, order.inputs, strict=True)
                ):
                    proof = None if quotient is None else quotient.order_proofs[i]
                    if (
                        item.ordering is not value.ref
                        or type(item.position) is not int
                        or item.position != i
                        or item.source is not source
                        or item.determination is not proof
                    ):
                        return False
                    requirement = None
                    if proof is not None:
                        if (
                            type(proof) is not tuple
                            or len(proof) not in {2, 3}
                            or proof[0] is not source
                        ):
                            return False
                        visible_sources = tuple(t for group in targets for t in group)
                        requested_sources = tuple(
                            use.determination_target for use in original_uses
                        )
                        if len(proof) == 3:
                            if (
                                not _same(proof[1], visible_sources)
                                or not _same(proof[2], requested_sources)
                                or any(
                                    id(target) not in visible_targets
                                    for target in requested_sources
                                )
                            ):
                                return False
                        else:
                            if quotient is None:
                                return False
                            (requirement,) = take("hidden_order_requirements")
                            properties = results.proof_properties(quotient)
                            if properties is None:
                                return False
                            if id(properties) not in class_indexes:
                                class_indexes[id(properties)] = (
                                    results.class_target_index(properties)
                                )
                            target_index = class_indexes[id(properties)]
                            if (
                                properties is None
                                or requirement.item is not item.ref
                                or requirement.scope is not boundary.ref
                                or requirement.source is not source
                                or requirement.proof is not proof[1]
                                or requirement.properties is not properties
                                or requirement.value_type is not source.value_type
                                or not _supplied_strict_proof(
                                    proof[1],
                                    properties,
                                    visible_sources,
                                    requested_sources,
                                    target_index,
                                )
                                or requirement.requested
                                is not proof[1].requested.classes
                            ):
                                return False
                            by_class = {}
                            for original_targets, port in zip(targets, inputs):
                                for group in results.class_targets(
                                    target_index, original_targets
                                ):
                                    if group is not None:
                                        by_class.setdefault(id(group), []).append(
                                            port.ref
                                        )
                            if len(requirement.determinants) != len(
                                proof[1].seed.classes
                            ) or any(
                                group is not expected
                                or not _same(
                                    ports, tuple(by_class.get(id(expected), ()))
                                )
                                or not ports
                                for (group, ports), expected in zip(
                                    requirement.determinants,
                                    proof[1].seed.classes,
                                    strict=True,
                                )
                            ):
                                return False
                            if len(requirement.input_images) != len(
                                original_uses
                            ) or any(
                                use is not original
                                or image
                                is not pre_projection[
                                    id(results.order_key(original, aggregate))
                                ].ref
                                for (use, image), original in zip(
                                    requirement.input_images, original_uses, strict=True
                                )
                            ):
                                return False
                    uses = take("order_uses", len(original_uses))
                    if not _same(item.uses, tuple(use.ref for use in uses)):
                        return False
                    for j, (use, original) in enumerate(
                        zip(uses, original_uses, strict=True)
                    ):
                        expected_ports = (
                            (
                                ()
                                if requirement is not None
                                else tuple(
                                    visible_targets.get(
                                        id(original.determination_target), ()
                                    )
                                )
                            )
                            if quotient is not None
                            else (
                                helpers[id(results.order_key(original, aggregate))].ref,
                            )
                        )
                        if (
                            use.item is not item.ref
                            or type(use.position) is not int
                            or use.position != j
                            or use.source is not original
                            or use.scope is not boundary.ref
                            or not _same(use.ports, expected_ports)
                            or use.requirement
                            is not (None if requirement is None else requirement.ref)
                        ):
                            return False
                    nodes = row.scalar_nodes(
                        source.expression,
                        tuple(use.expression for use in original_uses),
                    )
                    expressions = take("order_expressions", len(nodes))
                    by_expression = {id(e.expression): e for e in expressions}
                    by_use = {id(use.source.expression): use for use in uses}
                    if (
                        len(by_expression) != len(nodes)
                        or item.expression is not expressions[0].ref
                        or item.value
                        is not (
                            item.expression if requirement is None else requirement.ref
                        )
                    ):
                        return False
                    types = {
                        id(node): value
                        for node, value in results.order_types(source).items()
                    }
                    for j, (expression, node) in enumerate(
                        zip(expressions, nodes, strict=True)
                    ):
                        use = by_use.get(id(node))
                        children = (
                            ()
                            if use is not None
                            else tuple(
                                by_expression[id(child)].ref
                                for child in row.scalar_children(node)
                            )
                        )
                        if (
                            expression.item is not item.ref
                            or type(expression.position) is not int
                            or expression.position != j
                            or expression.expression is not node
                            or expression.value_type is not types.get(id(node))
                            or expression.value_type.kind is not ValueTypeKind.KNOWN
                            or not _same(expression.operands, children)
                            or expression.use is not (None if use is None else use.ref)
                            or type(node)
                            not in {
                                NameExpr,
                                DottedNameExpr,
                                LiteralExpr,
                                UnaryExpr,
                                BinaryExpr,
                                ComparisonExpr,
                                BetweenExpr,
                                IsNullExpr,
                            }
                        ):
                            return False
            else:
                (value,) = take("result_limits")
                source = entry.active_properties.cardinality
                clause = authored.limit_clause
                if (
                    clause is None
                    or type(clause.expression) is not LiteralExpr
                    or type(clause.expression.value) is not int
                    or type(value.value) is not int
                    or type(value.row_count_upper_bound) is not int
                    or type(value.maximum) is not int
                    or value.boundary is not boundary.ref
                    or value.source is not source
                    or value.clause is not clause
                    or value.literal is not clause.expression
                    or value.value != clause.expression.value
                    or value.maximum != results.MAX_RELATION_LIMIT
                    or not 0 <= value.value <= value.maximum
                ):
                    return False
                if type(source) is results.ProjectRelationLimit:
                    if (
                        source.owner is not entry.owner
                        or source.clause is not clause
                        or source.literal is not value.literal
                        or type(source.value) is not int
                        or source.value != value.value
                        or source.row_count_upper_bound != value.value
                        or operator.evidence is not source
                    ):
                        return False
                    bound = source.row_count_upper_bound
                elif type(source) is results.ProjectIRProvidedCardinalityUpperBound:
                    if (
                        not isinstance(
                            entry.semantic_entry, results.ProjectExistingEffectiveOutput
                        )
                        or source.evidence
                        is not entry.semantic_entry.fragment.semantic_facts
                        or source.evidence.owner is not entry.owner
                    ):
                        return False
                    bound = source.upper_bound
                else:
                    return False
                if (
                    type(bound) is not int
                    or value.row_count_upper_bound != bound
                    or bound != value.value
                ):
                    return False
            carried, predecessor = outputs, boundary.ref
        exports = take("result_exports", len(definition.exports))
        for export, canonical, port in zip(
            exports, definition.exports, carried, strict=True
        ):
            if (
                export.definition is not definition.ref
                or export.canonical is not canonical
                or export.port is not port.ref
            ):
                return False
    return all(cursors[name] == len(getattr(plan, name)) for name, _, _ in inventories)


def _result_origins_and_demands(plan, origin_position, demand_position):
    Issue, R, K = (
        ProjectSQLPlanVerificationIssue,
        ProjectSQLOriginRole,
        ProjectSQLPlanRefKind,
    )
    context = results.origin_context(plan)
    for witness in (
        *plan.result_boundaries,
        *plan.result_ports,
        *plan.distincts,
        *plan.quotient_fields,
        *plan.orders,
        *plan.order_items,
        *plan.order_expressions,
        *plan.order_uses,
        *plan.hidden_order_requirements,
        *plan.result_limits,
        *plan.result_exports,
    ):
        definition, cause, antecedents, kind, provenance = results.origin_parts(
            witness, context
        )
        owner = context["definitions"][definition]
        original, demand_origin = plan.origins[origin_position : origin_position + 2]
        demand = plan.demands[demand_position]
        if not _origin_matches(
            original,
            (
                witness.ref,
                R(witness.ref.kind.value),
                provenance,
                owner,
                cause,
                witness,
                antecedents,
            ),
            plan.scope,
            origin_position,
        ):
            return (Issue.ORIGINS,)
        if (
            type(demand) is not results.ProjectSQLResultDemand
            or not _ref(demand.ref, plan.scope, K.DEMAND, demand_position)
            or demand.subject is not witness.ref
            or demand.kind is not kind
            or demand.witness is not witness
            or demand.origin is not demand_origin.ref
        ):
            return (Issue.DEMANDS,)
        if not _origin_matches(
            demand_origin,
            (demand.ref, R.DEMAND, provenance, owner, cause, witness, (original.ref,)),
            plan.scope,
            origin_position + 1,
        ):
            return (Issue.ORIGINS,)
        origin_position += 2
        demand_position += 1
    return _set_origins_and_demands(plan, origin_position, demand_position)


def _set_type_evidence(evidence, completed, entries, identities, resolutions, checked):
    """Check retained type-parent links iteratively, including UNION ALL's non-equality cases."""
    from pietto._project.project_final_outputs import (
        ProjectCompletedOutputField,
        ProjectEffectiveJoinInputAuthority,
    )

    pending = [(evidence, False)]
    active = set()
    types = completed.semantic_result.module_type_source_resolutions
    while pending:
        value, closing = pending.pop()
        if closing:
            active.remove(id(value))
            checked.add(id(value))
            continue
        if id(value) in active:
            return False
        if id(value) in checked:
            continue
        if (
            type(value) is not results.ProjectRowEquivalenceField
            or value.types is not types
            or not value.type_concrete
        ):
            return False
        selected = value.selected
        if isinstance(selected, ProjectRowEquivalenceInput):
            authority = selected.authority
            if (
                type(authority) is not ProjectEffectiveJoinInputAuthority
                or authority.completion is not completed.completion
                or entries.get(id(authority.entry)) is not authority.entry
            ):
                return False
            source = authority.entry
            original_fields = (
                source.properties.fields
                if isinstance(source, results.ProjectExistingEffectiveOutput)
                else source.fields
            )
            position = selected.field_position
            if type(position) is not int or not 0 <= position < len(original_fields):
                return False
            if isinstance(source, results.ProjectExistingEffectiveOutput):
                original = source.properties.fields[position]
                original_field = original.evidence
                parents = ()
            else:
                original = source.fields[position]
                original_field = original.field
                parents = original.type_sources
            if (
                selected.original is not original
                or selected.field is not original_field
                or selected.identity is not identities[(id(source), position)]
                or not _same(selected.type_sources, parents)
            ):
                return False
        elif isinstance(selected, ProjectCompletedOutputField):
            source = entries.get(id(selected.owner))
            if source is None or not any(selected is field for field in source.fields):
                return False
        else:
            return False
        if (
            type(value.parents) is not tuple
            or value.parents is not selected.type_sources
        ):
            return False
        resolution = value.resolution
        if resolution is not None and resolutions.get(id(resolution)) is not resolution:
            return False
        field_def = selected.field.field_def
        if field_def is not None and (
            resolution is None
            or resolution.reference.type_expr is not field_def.type_expr
        ):
            return False
        if value.decimal is not None:
            if (
                type(value.decimal.precision) is not int
                or type(value.decimal.scale) is not int
            ):
                return False
            if value.parents and value.decimal is not value.parents[0].decimal:
                return False
            if not value.parents and value.decimal_type_expr is None:
                return False
        active.add(id(value))
        pending.append((value, True))
        pending.extend((parent, False) for parent in reversed(value.parents))
    return True


def _set_structure(plan):
    from pietto._project.project_final_outputs import (
        ProjectCompletedSetOutput,
        ProjectEffectiveJoinInputAuthority,
    )
    from pietto._project.project_set_operations import (
        ProjectSetInputScope,
        ProjectSetOperandUse,
        ProjectSetOperation,
        ProjectSetColumn,
        ProjectSetMultiplicityLaw,
    )
    from pietto._project.model import ProjectRowResultRole
    from pietto._project.project_row_equivalence import compatible_row_types
    from pietto.ast_nodes import SetOperationKind, SetOperationQuantifier

    K = ProjectSQLPlanRefKind
    for values, cls, kind in (
        (plan.set_bodies, sets.ProjectSQLSetBody, K.SET_BODY),
        (plan.set_operands, sets.ProjectSQLSetOperand, K.SET_OPERAND),
        (plan.set_inputs, sets.ProjectSQLSetInput, K.SET_INPUT),
        (plan.set_columns, sets.ProjectSQLSetColumn, K.SET_COLUMN),
    ):
        if not _inventory(values, cls, plan.scope, kind):
            return False
    definitions = tuple(
        d
        for d in plan.bindings.definitions
        if isinstance(d.entry.owner.definition, SetRelationDef)
    )
    if len(plan.set_bodies) != len(definitions):
        return False
    completed = plan.scope.completed
    by_entry = {id(d.entry): d for d in plan.bindings.definitions}
    uses = {id(use.edge): use for use in plan.input_uses}
    terminals = results.terminal_index(plan)
    result_ports = {port.ref: port for port in plan.result_ports}
    entries = {id(entry): entry for entry in completed.effective_outputs.entries}
    entries.update(
        (id(entry.owner), entry) for entry in completed.effective_outputs.entries
    )
    identities = {
        (id(d.entry.semantic_entry), i): port.identity
        for d in plan.bindings.definitions
        for i, port in enumerate(d.exports)
    }
    type_root = completed.semantic_result.module_type_source_resolutions
    if type_root is None:
        return False
    resolutions = {
        id(value): value
        for environment in type_root.environments
        for value in environment.type_resolutions
    }
    checked_types = set()
    scheduled = (
        tuple(completed.completion.topology.blocked_owners)
        + completed.completion.schedule
    )
    positions = {id(owner): i for i, owner in enumerate(scheduled)}
    actual_by_owner = {
        id(entry.owner): entry for entry in completed.effective_outputs.entries
    }
    operand_cursor = input_cursor = column_cursor = 0
    for body, definition in zip(plan.set_bodies, definitions, strict=True):
        entry = definition.entry
        if not isinstance(entry, ProjectIRCompletedSetOperationOutput):
            return False
        semantic = entry.semantic_entry
        if type(semantic) is not ProjectCompletedSetOutput:
            return False
        operation = semantic.root
        authored = definition.entry.owner.definition
        if (
            not isinstance(authored, SetRelationDef)
            or type(operation) is not ProjectSetOperation
        ):
            return False
        ast_body = authored.body
        scope = operation.scope
        if (
            body.definition is not definition.ref
            or body.source is not entry
            or body.operation is not operation
            or operation.owner is not entry.owner
            or type(scope) is not ProjectSetInputScope
            or scope.completion is not completed.completion
            or scope.base_entry is not semantic.base_entry
            or not any(
                scope.base_entry is candidate
                for candidate in completed.completion.entries
            )
            or type(body.kind) is not SetOperationKind
            or body.kind is not ast_body.kind
            or type(body.quantifier) is not SetOperationQuantifier
            or body.quantifier is not ast_body.quantifier
            or type(body.multiplicity) is not ProjectSetMultiplicityLaw
            or body.multiplicity is not operation.multiplicity
            or body.multiplicity.value != f"{body.kind.value}_{body.quantifier.value}"
            or type(body.fold) is not str
            or body.fold != "source_order_left_fold"
            or type(body.requires_equivalence) is not bool
            or body.requires_equivalence is not operation.requires_equivalence
            or body.requires_equivalence
            is not (
                (body.kind, body.quantifier)
                != (SetOperationKind.UNION, SetOperationQuantifier.ALL)
            )
            or type(body.full_row_unique) is not bool
            or body.full_row_unique is not operation.full_row_unique
            or body.full_row_unique
            is not (body.quantifier is SetOperationQuantifier.DISTINCT)
            or body.row_domain is not semantic.row_domain
            or body.properties is not entry.active_properties
            or body.uniqueness is not semantic.uniqueness
            or (body.uniqueness is None) is body.full_row_unique
            or semantic.ordering is not None
            or semantic.limit is not None
            or entry.active_properties.ordering is not None
            or entry.active_properties.cardinality is not None
            or entry.active_properties.output is not entry.active_output
            or entry.operator.evidence is not semantic
            or entry.operator.kind.value != "set_operation"
            or entry.active_output.row_shape.operator is not entry.operator
        ):
            return False
        if body.uniqueness is not None and (
            body.uniqueness.output is not semantic
            or body.uniqueness.nulls_equal is not True
        ):
            return False
        origin = body.row_domain.set_origin
        if (
            origin is None
            or origin.witness is not operation
            or body.row_domain.kind.value != "set"
        ):
            return False
        expected_available = tuple(
            actual_by_owner[id(owner)]
            for owner in scheduled[: positions[id(entry.owner)]]
        )
        if not _same(scope.available, expected_available) or not _same(
            scope.references, tuple(use.resolution for use in operation.uses)
        ):
            return False
        arity, width = len(ast_body.operands), len(definition.exports)
        if (
            arity < 2
            or len(operation.uses) != arity
            or len(entry.operands) != arity
            or len(semantic.dependencies) != arity
            or len(operation.columns) != width
            or len(semantic.fields) != width
            or len(body.columns) != width
            or len(body.outputs) != width
        ):
            return False
        operands = plan.set_operands[operand_cursor : operand_cursor + arity]
        operand_cursor += arity
        if len(operands) != arity or not _same(
            body.operands, tuple(operand.ref for operand in operands)
        ):
            return False
        input_rows = []
        for i, (operand, image, original, source_ast, dependency) in enumerate(
            zip(
                operands,
                entry.operands,
                operation.uses,
                ast_body.operands,
                semantic.dependencies,
                strict=True,
            )
        ):
            if (
                type(image) is not sets.ProjectIRSetOperandInput
                or type(original) is not ProjectSetOperandUse
            ):
                return False
            use = uses.get(id(image))
            producer = by_entry.get(id(image.producer))
            authority = original.authority
            reference = original.resolution.reference
            if (
                use is None
                or producer is None
                or operand.body is not body.ref
                or type(operand.position) is not int
                or operand.position != i
                or operand.source is not image
                or operand.use is not use
                or operand.producer is not producer.ref
                or use.producer is not producer.ref
                or use.consumer is not definition.ref
                or use.dependency is not dependency
                or use.edge is not image
                or image.source is not original
                or original.scope is not scope
                or original.dependency is not dependency
                or dependency.evidence is not original.resolution
                or type(dependency.dependency_ordinal) is not int
                or dependency.dependency_ordinal != i
                or reference.owner is not entry.owner
                or reference.operand is not source_ast
                or type(reference.operand_ordinal) is not int
                or reference.operand_ordinal != i
                or type(authority) is not ProjectEffectiveJoinInputAuthority
                or authority.entry is not image.producer.semantic_entry
                or authority.owner is not image.producer.owner
                or authority.completion is not completed.completion
                or original.resolution.target_symbol is not use.binding
                or use.binding.target_occurrence is not image.producer.owner
                or image.use.output is not image.producer.active_output.occurrence
                or image.use.slot.consumer is not entry.operator.node
                or type(image.use.slot.input_ordinal) is not int
                or image.use.slot.input_ordinal != i
                or len(original.fields) != width
                or len(use.ports) != width
                or len(producer.exports) != width
            ):
                return False
            local = plan.set_inputs[input_cursor : input_cursor + width]
            input_cursor += width
            if len(local) != width or not _same(
                operand.fields, tuple(field_image.ref for field_image in local)
            ):
                return False
            for j, (field_image, binding, canonical, evidence) in enumerate(
                zip(local, use.ports, producer.exports, original.fields, strict=True)
            ):
                selected = evidence.selected
                if (
                    field_image.operand is not operand.ref
                    or type(field_image.position) is not int
                    or field_image.position != j
                    or field_image.binding is not binding
                    or binding.producer_port is not canonical.ref
                    or field_image.terminal is not terminals.get(canonical.ref)
                    or field_image.evidence is not evidence
                    or type(selected) is not ProjectRowEquivalenceInput
                    or selected.authority is not authority
                    or type(selected.field_position) is not int
                    or selected.field_position != j
                    or selected.identity is not canonical.identity
                    or selected.field is not canonical.field.evidence
                    or (body.requires_equivalence and evidence.reason is not None)
                    or not _set_type_evidence(
                        evidence,
                        completed,
                        entries,
                        identities,
                        resolutions,
                        checked_types,
                    )
                ):
                    return False
            input_rows.append(local)
        columns = plan.set_columns[column_cursor : column_cursor + width]
        column_cursor += width
        if len(columns) != width or not _same(
            body.columns, tuple(column.ref for column in columns)
        ):
            return False
        for i, (column, source, field_image, canonical, ir_field) in enumerate(
            zip(
                columns,
                operation.columns,
                semantic.fields,
                definition.exports,
                entry.active_output.row_shape.fields,
                strict=True,
            )
        ):
            members = tuple(fields[i].ref for fields in input_rows)
            evidence = tuple(use.fields[i] for use in operation.uses)
            output = result_ports[column.output]
            if (
                column.body is not body.ref
                or type(column.position) is not int
                or column.position != i
                or type(source) is not ProjectSetColumn
                or column.source is not source
                or type(source.position) is not int
                or source.position != i
                or source.kind is not body.kind
                or source.uses is not operation.uses
                or not _same(source.inputs, evidence)
                or column.semantic is not field_image
                or column.field is not canonical.field
                or not _same(column.inputs, members)
                or not _same(
                    column.value_inputs,
                    members[:1] if body.kind is SetOperationKind.EXCEPT else members,
                )
                or output.canonical is not canonical
                or output.key is not field_image
                or output.source is not column.ref
                or output.boundary is not body.ref
                or body.outputs[i] is not output.ref
                or field_image.root is not operation
                or field_image.source is not source
                or field_image.owner is not entry.owner
                or type(field_image.output_position) is not int
                or field_image.output_position != i
                or field_image.identity is not canonical.identity
                or field_image.identity is evidence[0].selected.identity
                or field_image.output_name != evidence[0].selected.identity.name
                or field_image.identity.owner.identity is not entry.owner.identity
                or field_image.field is not canonical.field.evidence
                or field_image.field.resolved_type is not source.resolved_type
                or field_image.field.nullability is not source.nullability
                or canonical.field.effective_nullability is not source.nullability
                or field_image.field.result_role
                is not ProjectRowResultRole.ORDINARY_ROW_VALUE
                or field_image.type_sources is not source.inputs
                or ir_field.semantic_source is not field_image
                or ir_field.final_identity is not field_image.identity
                or ir_field.evidence is not field_image.field
                or any(not compatible_row_types(evidence[0], item) for item in evidence)
            ):
                return False
    return (
        operand_cursor == len(plan.set_operands)
        and input_cursor == len(plan.set_inputs)
        and column_cursor == len(plan.set_columns)
    )


def _set_origins_and_demands(plan, origin_position, demand_position):
    Issue, R, P, K = (
        ProjectSQLPlanVerificationIssue,
        ProjectSQLOriginRole,
        ProjectSQLOriginProvenance,
        ProjectSQLPlanRefKind,
    )
    context = sets.origin_context(plan)
    owners = {
        definition.ref: definition.entry.owner
        for definition in plan.bindings.definitions
    }
    for witness in (
        *plan.set_bodies,
        *plan.set_operands,
        *plan.set_inputs,
        *plan.set_columns,
    ):
        definition, cause, antecedents, provenance, kinds = sets.origin_parts(
            witness, context
        )
        owner = owners[definition]
        origin = plan.origins[origin_position]
        if not _origin_matches(
            origin,
            (
                witness.ref,
                R(witness.ref.kind.value),
                provenance,
                owner,
                cause,
                witness,
                antecedents,
            ),
            plan.scope,
            origin_position,
        ):
            return (Issue.ORIGINS,)
        origin_position += 1
        for kind in kinds:
            demand, demand_origin = (
                plan.demands[demand_position],
                plan.origins[origin_position],
            )
            if (
                type(demand) is not sets.ProjectSQLSetDemand
                or not _ref(demand.ref, plan.scope, K.DEMAND, demand_position)
                or demand.subject is not witness.ref
                or demand.kind is not kind
                or demand.witness is not witness
                or demand.origin is not demand_origin.ref
            ):
                return (Issue.DEMANDS,)
            if not _origin_matches(
                demand_origin,
                (
                    demand.ref,
                    R.DEMAND,
                    P.TYPE_PROOF,
                    owner,
                    cause,
                    witness,
                    (origin.ref,),
                ),
                plan.scope,
                origin_position,
            ):
                return (Issue.ORIGINS,)
            origin_position += 1
            demand_position += 1
    return _literal_origins_and_demands(plan, origin_position, demand_position)


def _literal_schema(plan, policy):
    """Independently check roles/types/transport against pure retained traversal."""
    L, K = literals, ProjectSQLPlanRefKind
    if (
        type(policy) is not L.ProjectSQLLiteralPolicy
        or plan.scope is not plan.bindings.scope
        or plan.literal_policy is not policy
        or not _inventory(
            plan.literal_sites, L.ProjectSQLLiteralSite, plan.scope, K.LITERAL_SITE
        )
        or not _inventory(
            plan.literal_slots, L.ProjectSQLLiteralSlot, plan.scope, K.LITERAL_SLOT
        )
        or not _inventory(plan.bind_uses, L.ProjectSQLBindUse, plan.scope, K.BIND_USE)
    ):
        return False
    expected = tuple(L.positions(plan))
    if len(expected) != len(plan.literal_sites):
        return False
    bound = []
    transports = {}
    for site, position in zip(plan.literal_sites, expected, strict=True):
        actual = site.position
        if (
            type(actual) is not L.ProjectSQLLiteralPosition
            or any(
                getattr(actual, name) is not getattr(position, name)
                for name in (
                    "definition",
                    "owner",
                    "context",
                    "context_ref",
                    "role",
                    "literal",
                    "value_type",
                    "evidence",
                    "expression",
                )
            )
            or site.span is not position.literal.span
        ):
            return False
        if type(actual.ancestry) is not tuple or len(actual.ancestry) != len(
            position.ancestry
        ):
            return False
        for supplied, original in zip(actual.ancestry, position.ancestry, strict=True):
            if (
                type(supplied) is not tuple
                or len(supplied) != 2
                or supplied[0] is not original[0]
                or type(supplied[1]) is not int
                or supplied[1] != original[1]
            ):
                return False
        # Do not use the builder's classifier, type solver or host-value typing.
        R, Why = L.ProjectSQLLiteralRole, L.ProjectSQLLiteralReason
        value_type, value = position.value_type, position.literal.value
        if policy is L.ProjectSQLLiteralPolicy.PRESERVE_LITERALS:
            reason = Why.POLICY
        elif position.role in (
            R.AGGREGATE_ARGUMENT,
            R.SATISFYING,
            R.QUALIFY,
            R.WINDOW_ARGUMENT,
            R.WINDOW_PARTITION,
            R.WINDOW_ORDER,
            R.FRAME,
            R.ORDER,
            R.LIMIT,
            R.CONNECTOR,
            R.TYPE,
        ):
            reason = Why.SPECIALIZED
        elif (
            position.role not in (R.SELECT, R.LET, R.WHERE, R.ON)
            or position.expression is None
        ):
            reason = Why.UNKNOWN_CONTEXT
        elif any(type(parent) is CallExpr for parent, _ in position.ancestry):
            reason = Why.CALL_ARGUMENT
        elif any(
            type(parent)
            not in (UnaryExpr, BinaryExpr, ComparisonExpr, IsNullExpr, BetweenExpr)
            for parent, _ in position.ancestry
        ):
            reason = Why.UNKNOWN_CONTEXT
        elif value is None:
            reason = Why.NULL
        elif (
            type(value_type) is not ValueType
            or value_type.kind is not ValueTypeKind.KNOWN
        ):
            reason = Why.TYPE_UNAVAILABLE
        elif (
            value_type.resolved_type.kind is not TypeKind.BUILTIN
            or value_type.resolved_type.definition is not None
            or value_type.resolved_type.name not in ("Bool", "Int", "Text", "Float")
        ):
            reason = Why.NON_BUILTIN
        elif (
            value_type.resolved_type.name == "Float"
            and type(value) is float
            and not isfinite(value)
        ):
            reason = Why.NONFINITE
        elif not L.same_value(
            L.ProjectSQLLiteralTag(value_type.resolved_type.name), value, value
        ):
            reason = Why.VALUE_REPRESENTATION
        else:
            reason = None
        disposition = (
            L.ProjectSQLLiteralDisposition.BOUND
            if reason is None
            else L.ProjectSQLLiteralDisposition.PRESERVED_WITH_REASON
        )
        if site.reason is not reason or site.disposition is not disposition:
            return False
        if position.expression is not None:
            if position.expression in transports:
                return False
            transports[position.expression] = site
        if reason is None:
            bound.append(site)
    if len(bound) != len(plan.literal_slots) or len(bound) != len(plan.bind_uses):
        return False
    uses = {}
    for site, slot, use in zip(bound, plan.literal_slots, plan.bind_uses, strict=True):
        if (
            slot.site is not site
            or slot.value_type is not site.position.value_type
            or type(slot.tag) is not L.ProjectSQLLiteralTag
            or slot.tag.value != slot.value_type.resolved_type.name
            or use.slot is not slot
            or use.expression is not site.position.expression
        ):
            return False
        uses[use.expression] = use
    seen = set()
    for expression in plan.expressions:
        if not isinstance(expression.expression, LiteralExpr):
            continue
        site = transports.get(expression.ref)
        if site is None:
            return False
        use = uses.get(expression.ref)
        if use is None:
            if type(expression) is not row.ProjectSQLLiteral:
                return False
        elif (
            type(expression) is not row.ProjectSQLBoundLiteral
            or expression.use is not use
        ):
            return False
        seen.add(expression.ref)
    return seen == set(transports)


def verify_fixed_literal_envelope(
    plan: ProjectSQLPlan,
    envelope: literals.ProjectSQLFixedEnvelope,
    *,
    literal_policy: literals.ProjectSQLLiteralPolicy = literals.ProjectSQLLiteralPolicy.PRESERVE_LITERALS,
) -> bool:
    """Check a supplied immutable envelope against the rooted fixed schema/source.

    Whole-plan verification separately owns all pre-existing plan/semantic/IR
    invariants. This checker never accepts caller replacements or constructs types.
    """
    L, K = literals, ProjectSQLPlanRefKind
    try:
        if (
            type(plan) is not ProjectSQLPlan
            or not _literal_schema(plan, literal_policy)
            or type(envelope) is not L.ProjectSQLFixedEnvelope
            or envelope.scope is not plan.scope
            or envelope.policy is not literal_policy
            or not _same(envelope.slots, plan.literal_slots)
            or not _inventory(
                envelope.values,
                L.ProjectSQLFixedLiteralValue,
                plan.scope,
                K.FIXED_LITERAL_VALUE,
            )
            or len(envelope.values) != len(plan.literal_slots)
        ):
            return False
        return all(
            value.slot is slot
            and value.tag is slot.tag
            and L.same_value(value.tag, value.value, slot.site.position.literal.value)
            for slot, value in zip(plan.literal_slots, envelope.values, strict=True)
        )
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        return False


def _literal_origins_and_demands(plan, origin_position, demand_position):
    L, Issue, K, R, P = (
        literals,
        ProjectSQLPlanVerificationIssue,
        ProjectSQLPlanRefKind,
        ProjectSQLOriginRole,
        ProjectSQLOriginProvenance,
    )
    original_refs = {}
    for witness in (
        *plan.literal_sites,
        *plan.literal_slots,
        *plan.fixed_envelope.values,
        *plan.bind_uses,
    ):
        site, antecedents, provenance = L.origin_parts(witness)
        original = plan.origins[origin_position]
        if not _origin_matches(
            original,
            (
                witness.ref,
                R(witness.ref.kind.value),
                provenance,
                site.position.owner,
                site.position.literal,
                witness,
                antecedents,
            ),
            plan.scope,
            origin_position,
        ):
            return (Issue.ORIGINS,)
        original_refs[witness.ref] = original.ref
        origin_position += 1
    if len(plan.bind_uses) != len(plan.fixed_envelope.values):
        return (Issue.LITERAL_TRANSPORT,)
    contexts = L.context_index(plan)
    for use, value in zip(plan.bind_uses, plan.fixed_envelope.values, strict=True):
        demand, origin = plan.demands[demand_position], plan.origins[origin_position]
        site = use.slot.site
        if (
            type(demand) is not L.ProjectSQLLiteralDemand
            or not _ref(demand.ref, plan.scope, K.DEMAND, demand_position)
            or demand.subject is not use.ref
            or demand.use is not use
            or demand.value is not value
            or not _same(demand.contexts, L.demand_contexts(site, contexts))
            or not _same(demand.requirements, tuple(L.ProjectSQLLiteralRequirement))
            or demand.origin is not origin.ref
        ):
            return (Issue.DEMANDS,)
        if not _origin_matches(
            origin,
            (
                demand.ref,
                R.DEMAND,
                P.TYPE_PROOF,
                site.position.owner,
                site.position.literal,
                use,
                (
                    original_refs[use.ref],
                    original_refs[use.slot.ref],
                    original_refs[value.ref],
                ),
            ),
            plan.scope,
            origin_position,
        ):
            return (Issue.ORIGINS,)
        origin_position += 1
        demand_position += 1
    return (
        ()
        if origin_position == len(plan.origins) and demand_position == len(plan.demands)
        else (Issue.DEMANDS,)
    )


def _verify(plan, completed, bundle, selected, policy, envelope):
    Issue = ProjectSQLPlanVerificationIssue
    if type(plan) is not ProjectSQLPlan:
        return (Issue.NON_CONCRETE,)
    try:
        issues = _verify_bindings(plan.bindings, completed, bundle, selected)
        if issues:
            return issues
        issues = _whole_plan(plan)
        if issues:
            return issues
        if envelope is not plan.fixed_envelope or not verify_fixed_literal_envelope(
            plan, envelope, literal_policy=policy
        ):
            return (Issue.LITERAL_TRANSPORT,)
        return ()
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        return (Issue.STRUCTURE,)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLPlanVerification:
    plan: ProjectSQLPlan | ProjectSQLPlanUnavailable
    completed: ProjectConcreteCompletedSemanticResult
    analysis_bundle: ProjectIRQueryBlockAnalysisBundle
    selected_owner: ProjectDeclarationOccurrence
    literal_policy: literals.ProjectSQLLiteralPolicy = (
        literals.ProjectSQLLiteralPolicy.PRESERVE_LITERALS
    )
    envelope: literals.ProjectSQLFixedEnvelope | None = None
    issues: tuple[ProjectSQLPlanVerificationIssue, ...] = field(init=False)

    def __post_init__(self) -> None:
        if self.envelope is None and type(self.plan) is ProjectSQLPlan:
            object.__setattr__(
                self, "envelope", getattr(self.plan, "fixed_envelope", None)
            )
        object.__setattr__(
            self,
            "issues",
            _verify(
                self.plan,
                self.completed,
                self.analysis_bundle,
                self.selected_owner,
                self.literal_policy,
                self.envelope,
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
    *,
    literal_policy: literals.ProjectSQLLiteralPolicy = literals.ProjectSQLLiteralPolicy.PRESERVE_LITERALS,
    envelope: literals.ProjectSQLFixedEnvelope | None = None,
) -> ProjectSQLPlanVerification:
    return ProjectSQLPlanVerification(
        plan=plan,
        completed=completed,
        analysis_bundle=analysis_bundle,
        selected_owner=selected_owner,
        literal_policy=literal_policy,
        envelope=envelope,
    )
