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
    ProjectIRCompletedQueryBlockOutput,
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

from pietto._project import project_sql_plan_expressions as row
from pietto._project.project_scalar_namespaces import ProjectScalarNamespaceStage
from pietto._project import project_sql_plan_joins as joining
from pietto.ast_nodes import AuthoredJoinKind
from pietto._project.project_join_conditions import (
    ProjectJoinReferenceState,
    ProjectJoinConditionState,
)
from pietto._project.project_scalar_references import ProjectScalarReferenceResolution
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleExpressionReferenceFact,
)
from pietto._project.let_scope_facts import ProjectLetScopeFactsStatus
from pietto._project.project_final_outputs import ProjectNoJoinScalarExpression
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
    definition = entry.owner.definition
    if not isinstance(definition, (TableDef, QueryDef)) or any(
        (
            definition.group_by_clause,
            definition.satisfying_clause,
            definition.named_windows,
            definition.qualify_clause,
            definition.distinct_clause,
            definition.order_by_clause,
            definition.limit_clause,
        )
    ):
        return False
    expected = (
        [] if definition.join_clauses else [ProjectIRLogicalOperatorKind.RELATION_INPUT]
    )
    if definition.where_clause is not None:
        expected.append(ProjectIRLogicalOperatorKind.ROW_FILTER)
    expected.append(ProjectIRLogicalOperatorKind.FINAL_PROJECTION)
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


def _whole_plan(plan: ProjectSQLPlan) -> tuple[ProjectSQLPlanVerificationIssue, ...]:
    Issue, K = ProjectSQLPlanVerificationIssue, ProjectSQLPlanRefKind
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
    if not _join_structure(plan):
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
        if not isinstance(authored, (TableDef, QueryDef)):
            return (Issue.UNSUPPORTED_SHAPE,)
        authority = row.row_authority(plan.scope.completed, entry)
        if authority is None:
            return (Issue.UNSUPPORTED_SHAPE,)
        expected_bindings = (
            () if authored.let_clause is None else authored.let_clause.bindings
        )
        if (
            len(authority.selections) != len(definition.exports)
            or len(authority.selected_evidence) != len(authority.selections)
            or len(authority.selected_references) != len(authority.selections)
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
            original = {id(p.field.evidence): p for p in use.ports}
            if {id(f) for f in authority.input_schema.fields.values()} != set(original):
                return (Issue.PORTS_AND_PROJECTIONS,)
            carries = [(p.ref, p.field.evidence, p.field.evidence) for p in use.ports]
            predecessor = use.ref
        stage_kinds = [row.ProjectSQLStageKind.LET] * len(expected_bindings)
        if authored.where_clause is not None:
            stage_kinds.append(row.ProjectSQLStageKind.WHERE)
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
                site_specs.append((site, incoming))
                local_sites.append(site)
            if kind is row.ProjectSQLStageKind.PROJECTION:
                if not _same(block.exports, tuple(p.ref for p in definition.exports)):
                    return (Issue.PORTS_AND_PROJECTIONS,)
                for i, (site, export) in enumerate(
                    zip(local_sites, definition.exports, strict=True)
                ):
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
                else:
                    item = plan.filters[filter_position]
                    filter_position += 1
                    site = local_sites[0]
                    root_by_site[site.ref] = item.predicate
                    if (
                        item.site is not site
                        or item.retention_effects is not _SQL_ROW_RETENTION_EFFECTS
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
        reference_type = (
            row.ProjectSQLMatchReference
            if isinstance(site, row.ProjectSQLMatchSite)
            else row.ProjectSQLJoinedReference
            if isinstance(site, row.ProjectSQLJoinedSite)
            else row.ProjectSQLReference
        )
        variants[NameExpr] = variants[DottedNameExpr] = reference_type
        # Traverse actual source independently of the expression allocator.
        pending, nodes = [site.occurrence.expression], []
        while pending:
            node = pending.pop()
            nodes.append(node)
            if isinstance(node, (BinaryExpr, ComparisonExpr)):
                children = (node.left, node.right)
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
            if (
                type(value) is not variants[type(node)]
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
                ),
            ):
                reference = next(references, None)
                if (
                    reference is None
                    or value.reference is not reference
                    or row.reference_expression(reference) is not node
                ):
                    return False
                if isinstance(site, row.ProjectSQLExpressionSite):
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
            elif isinstance(value, row.ProjectSQLLiteral):
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
    if len(plan.demands) != demand_prefix + len(subjects) + join_count or len(
        plan.origins
    ) != prefix + len(specs) + len(subjects) + 2 * join_count + len(plan.join_ports):
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
                and demand.retention_effects is _SQL_ROW_RETENTION_EFFECTS
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
