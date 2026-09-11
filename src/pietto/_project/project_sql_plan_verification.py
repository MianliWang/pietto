"""Independent exact-root verification of supplied private SQL plans.

This owner inspects the original semantic/IR evidence and the supplied graph.
It never invokes the planner, semantic builders or SQL renderers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import cast

from pietto._project.model import ProjectRowFieldProvenanceKind, ProjectRowResultRole
from pietto._project.module_attribution import ProjectModuleRowFieldKind
from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleCandidateBucketStatus,
    ProjectModuleFactOccurrenceRole,
)
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
)
from pietto._project.project_ir_operators import ProjectIRLogicalOperatorKind
from pietto._project.project_ir_properties import ProjectIRRowField, ProjectIRRowShape
from pietto._project.project_query_block_ir import ProjectIRReusedEffectiveOutput
from pietto._project.project_query_block_ir_verification import (
    ProjectIRQueryBlockAnalysisBundle,
)
from pietto._project.project_sql_plan import (
    ProjectSQLPlan,
    ProjectSQLPlanUnavailable,
    ProjectSQLPlanRef,
    ProjectSQLPlanRefKind,
    ProjectSQLPlanScope,
    ProjectSQLSourceBinding,
    ProjectSQLSelectBlock,
    ProjectSQLInputUse,
    ProjectSQLPort,
    ProjectSQLProjection,
    ProjectSQLOrigin,
    ProjectSQLOriginRole,
    ProjectSQLOriginProvenance,
    ProjectSQLSourceRealizationDemand,
    ProjectSQLExportRepresentationDemand,
    _require_roots,
    _one,
)
from pietto.ast_nodes import (
    CallExpr,
    DottedNameExpr,
    LiteralExpr,
    NameExpr,
    QueryDef,
    SourceDef,
    TableDef,
)
from pietto.errors import Severity

__all__: tuple[str, ...] = ()


class ProjectSQLPlanVerificationIssue(StrEnum):
    NON_CONCRETE = "non_concrete"
    ROOT_CONTINUITY = "root_continuity"
    UNSUPPORTED_SHAPE = "unsupported_shape"
    STRUCTURE = "structure"
    PORTS_AND_PROJECTIONS = "ports_and_projections"
    ORIGINS = "origins"
    DEMANDS = "demands"


def _same(actual: tuple[object, ...], expected: tuple[object, ...]) -> bool:
    return (
        type(actual) is tuple
        and len(actual) == len(expected)
        and all(a is b for a, b in zip(actual, expected, strict=True))
    )


def _refs(values, cls, scope: ProjectSQLPlanScope, kind: ProjectSQLPlanRefKind) -> bool:
    return type(values) is tuple and all(
        type(value) is cls
        and type(value.ref) is ProjectSQLPlanRef
        and value.ref.scope is scope
        and value.ref.kind is kind
        and type(value.ref.position) is int
        and value.ref.position == i
        for i, value in enumerate(values)
    )


def _shape(
    selected: ProjectIRReusedEffectiveOutput, source: ProjectIRReusedEffectiveOutput
) -> bool:
    definition = selected.owner.definition
    if (
        type(definition) not in {TableDef, QueryDef}
        or type(source.owner.definition) is not SourceDef
        or selected.owner.module_position != source.owner.module_position
    ):
        return False
    definition = cast(TableDef | QueryDef, definition)
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
    ):
        return False
    if any(
        type(item.expression) not in {NameExpr, DottedNameExpr}
        for item in definition.select_items
    ):
        return False
    fragment = selected.semantic_entry.fragment
    facts = fragment.semantic_facts
    if any(
        (
            facts.let_bindings,
            facts.window_outputs,
            facts.aggregate_result_facts,
            facts.group_key_occurrences,
            facts.aggregate_grouped_clause_readiness,
            facts.named_window_namespace,
            facts.clause_dependencies,
        )
    ):
        return False
    K = ProjectIRLogicalOperatorKind
    return (
        tuple(o.kind for o in fragment.logical_stage.operators)
        == (K.RELATION_INPUT, K.FINAL_PROJECTION)
        and tuple(
            o.kind for o in source.semantic_entry.fragment.logical_stage.operators
        )
        == (K.RELATION_INPUT,)
        and _same(tuple(f.item for f in facts.select_facts), definition.select_items)
    )


def _structure(
    plan: ProjectSQLPlan,
    selected: ProjectIRReusedEffectiveOutput,
    source: ProjectIRReusedEffectiveOutput,
    dependency,
) -> bool:
    K, scope = ProjectSQLPlanRefKind, plan.scope
    if not (
        len(plan.sources) == len(plan.blocks) == len(plan.input_uses) == 1
        and _refs(plan.sources, ProjectSQLSourceBinding, scope, K.SOURCE)
        and _refs(plan.blocks, ProjectSQLSelectBlock, scope, K.BLOCK)
        and _refs(plan.input_uses, ProjectSQLInputUse, scope, K.INPUT_USE)
    ):
        return False
    binding, block, use = plan.sources[0], plan.blocks[0], plan.input_uses[0]
    bundle = scope.analysis_bundle
    fragment = selected.semantic_entry.fragment
    edges = tuple(
        e for e in bundle.root.base_plan.cross_relation_edges if e.consumer is fragment
    )
    if len(edges) != 1:
        return False
    edge = edges[0]
    source_def = source.owner.definition
    if not isinstance(source_def, SourceDef):
        return False
    connector = source_def.connector
    if not isinstance(connector, CallExpr) or len(connector.arguments) != 1:
        return False
    argument = connector.arguments[0]
    spelling = (
        connector.callee.name
        if isinstance(connector.callee, NameExpr)
        else ".".join(connector.callee.parts)
    )
    modules = tuple(
        c.module
        for c in bundle.root.base_plan.semantic_facts.authority.catalogs.catalogs
        if any(o is source.owner for o in c.occurrences)
    )
    return (
        binding.source is source
        and binding.declaration is source_def
        and binding.connector is connector
        and type(argument) is LiteralExpr
        and type(argument.value) is str
        and spelling in {"postgres.table", "mysql.table"}
        and len(modules) == 1
        and binding.module is modules[0]
        and block.selected is selected
        and _same(block.operators, fragment.logical_stage.operators)
        and use.producer is binding.ref
        and use.consumer is block.ref
        and use.edge is edge
        and use.dependency is dependency
        and edge.producer is source.semantic_entry.fragment
        and edge.authority.resolution is dependency.evidence
        and edge.use.output is source.active_output.occurrence
        and edge.use.slot is edge.input_slot
        and edge.input_slot.consumer is block.operators[0].node
        and edge.use.anchor is edge.authority
        and selected.active_properties.output is selected.active_output
        and source.active_properties.output is source.active_output
        and selected.active_output is fragment.root_relation_output
        and selected.active_output.occurrence.producer is block.operators[1].node
    )


def _ports(
    plan: ProjectSQLPlan,
    selected: ProjectIRReusedEffectiveOutput,
    source: ProjectIRReusedEffectiveOutput,
) -> bool:
    K, scope = ProjectSQLPlanRefKind, plan.scope
    for ports, kind, owner, entry, identity_kind in (
        (
            plan.source_ports,
            K.SOURCE_PORT,
            plan.sources[0].ref,
            source,
            ProjectModuleRowFieldKind.SOURCE_FIELD,
        ),
        (
            plan.input_ports,
            K.INPUT_PORT,
            plan.input_uses[0].ref,
            source,
            ProjectModuleRowFieldKind.SOURCE_FIELD,
        ),
        (
            plan.exports,
            K.EXPORT,
            plan.blocks[0].ref,
            selected,
            ProjectModuleRowFieldKind.RELATION_OUTPUT,
        ),
    ):
        fields = entry.active_properties.relational.fields
        shape = entry.active_output.row_shape
        if (
            not _refs(ports, ProjectSQLPort, scope, kind)
            or type(shape) is not ProjectIRRowShape
            or len(ports) != len(shape.fields)
            or len(ports) != len(fields)
        ):
            return False
        for port, row, semantic in zip(ports, shape.fields, fields, strict=True):
            if (
                type(row) is not ProjectIRRowField
                or port.owner is not owner
                or port.field is not semantic
                or port.identity is not row.anchor.identity
                or port.identity.kind is not identity_kind
                or semantic.evidence is not row.evidence
                or semantic.output is not entry.active_output
            ):
                return False
    facts = selected.semantic_entry.fragment.semantic_facts
    if (
        not _refs(plan.projections, ProjectSQLProjection, scope, K.PROJECTION)
        or len(plan.projections) != len(facts.select_facts)
        or len(plan.exports) != len(plan.projections)
    ):
        return False
    images_by_label = {
        a.field.evidence.name: (a, b)
        for a, b in zip(plan.source_ports, plan.input_ports, strict=True)
    }
    for projection, export, semantic in zip(
        plan.projections, plan.exports, facts.select_facts, strict=True
    ):
        if len(semantic.references) != 1:
            return False
        reference = semantic.references[0]
        image = (
            images_by_label.get(reference.input_field.name)
            if reference.input_field is not None
            else None
        )
        if image is None:
            return False
        source_port, input_port = image
        if (
            projection.semantic is not semantic
            or projection.block is not plan.blocks[0].ref
            or projection.input_use is not plan.input_uses[0].ref
            or projection.source_port is not source_port.ref
            or projection.input_port is not input_port.ref
            or projection.export is not export.ref
            or source_port.field is not input_port.field
            or source_port.field.evidence is not reference.input_field
            or reference.owner is not selected.owner
            or reference.expression is not semantic.item.expression
            or reference.status is not ProjectModuleCandidateBucketStatus.CONCRETE
            or reference.role is not ProjectModuleFactOccurrenceRole.SELECT_VALUE
            or reference.let_candidates
            or reference.selected_output_candidates
            or semantic.field is not export.field.evidence
            or semantic.aggregate_result_fact is not None
            or export.field.evidence.result_role
            is not ProjectRowResultRole.ORDINARY_ROW_VALUE
            or export.field.evidence.provenance is None
            or export.field.evidence.provenance.kind
            is not ProjectRowFieldProvenanceKind.DIRECT_PROJECTION
        ):
            return False
    return True


def _origins(
    plan: ProjectSQLPlan,
    selected: ProjectIRReusedEffectiveOutput,
    source: ProjectIRReusedEffectiveOutput,
) -> bool:
    K, R, P = ProjectSQLPlanRefKind, ProjectSQLOriginRole, ProjectSQLOriginProvenance
    if not _refs(plan.origins, ProjectSQLOrigin, plan.scope, K.ORIGIN):
        return False
    definition = cast(TableDef | QueryDef, selected.owner.definition)
    binding, block, use = plan.sources[0], plan.blocks[0], plan.input_uses[0]
    # Enumerate mandatory sites from the actual supported shape, not supplied origins.
    expected = [
        (
            plan.scope,
            R.SELECTED_OWNER,
            P.GENERATED_STRUCTURE,
            selected.owner,
            definition,
            selected.owner,
            (),
        ),
        (
            binding.ref,
            R.SOURCE_DESCRIPTOR,
            P.GENERATED_STRUCTURE,
            source.owner,
            source.owner.definition,
            source.owner,
            (),
        ),
        (
            use.ref,
            R.INPUT_USE,
            P.GENERATED_STRUCTURE,
            selected.owner,
            definition.from_clause,
            use.edge,
            (binding.ref,),
        ),
        (
            block.ref,
            R.SELECT_BLOCK,
            P.GENERATED_STRUCTURE,
            selected.owner,
            definition,
            selected.owner,
            (use.ref,),
        ),
    ]
    expected.extend(
        (
            p.ref,
            R.SOURCE_PORT,
            P.VALUE,
            source.owner,
            source.owner.definition,
            p.field,
            (binding.ref,),
        )
        for p in plan.source_ports
    )
    expected.extend(
        (
            p.ref,
            R.INPUT_PORT,
            P.VALUE,
            selected.owner,
            definition.from_clause,
            p.field,
            (use.ref, s.ref),
        )
        for p, s in zip(plan.input_ports, plan.source_ports, strict=True)
    )
    for projection, export in zip(plan.projections, plan.exports, strict=True):
        expected.append(
            (
                projection.ref,
                R.PROJECTION,
                P.VALUE,
                selected.owner,
                projection.semantic.item,
                projection.semantic,
                (projection.input_port,),
            )
        )
        expected.append(
            (
                export.ref,
                R.EXPORT,
                P.VALUE,
                selected.owner,
                projection.semantic.item,
                export.field,
                (projection.ref,),
            )
        )
    if len(plan.demands) != 1 + len(plan.exports):
        return False
    expected.append(
        (
            plan.demands[0].ref,
            R.DEMAND,
            P.GENERATED_STRUCTURE,
            source.owner,
            source.owner.definition,
            source.owner,
            (binding.ref,),
        )
    )
    expected.extend(
        (
            d.ref,
            R.DEMAND,
            P.TYPE_PROOF,
            selected.owner,
            p.semantic.item,
            e.field,
            (e.ref,),
        )
        for d, p, e in zip(
            plan.demands[1:], plan.projections, plan.exports, strict=True
        )
    )
    return len(plan.origins) == len(expected) and all(
        _same((o.subject, o.role, o.provenance, o.owner, o.cause, o.evidence), row[:6])
        and _same(o.antecedents, row[6])
        for o, row in zip(plan.origins, expected, strict=True)
    )


def _demands(plan: ProjectSQLPlan, selected: ProjectIRReusedEffectiveOutput) -> bool:
    # One realization site plus one representation site per canonical final field.
    expected_count = 1 + len(selected.active_output.row_shape.fields)
    if type(plan.demands) is not tuple or len(plan.demands) != expected_count:
        return False
    origins = tuple(o for o in plan.origins if o.role is ProjectSQLOriginRole.DEMAND)
    if len(origins) != expected_count:
        return False
    for i, demand in enumerate(plan.demands):
        if (
            type(demand.ref) is not ProjectSQLPlanRef
            or demand.ref.scope is not plan.scope
            or demand.ref.kind is not ProjectSQLPlanRefKind.DEMAND
            or type(demand.ref.position) is not int
            or demand.ref.position != i
        ):
            return False
        origin = origins[i]
        if origin.subject is not demand.ref or demand.origin is not origin.ref:
            return False
        if i == 0:
            if (
                type(demand) is not ProjectSQLSourceRealizationDemand
                or demand.subject is not plan.sources[0].ref
                or demand.source is not plan.sources[0]
            ):
                return False
        else:
            export = plan.exports[i - 1]
            if (
                type(demand) is not ProjectSQLExportRepresentationDemand
                or demand.subject is not export.ref
                or demand.field is not export.field
                or demand.logical_type is not export.field.evidence.resolved_type
                or demand.nullability is not export.field.effective_nullability
            ):
                return False
    return True


def _verify(
    plan: ProjectSQLPlan | ProjectSQLPlanUnavailable,
    completed: ProjectConcreteCompletedSemanticResult,
    bundle: ProjectIRQueryBlockAnalysisBundle,
    selected_owner: ProjectDeclarationOccurrence,
) -> tuple[ProjectSQLPlanVerificationIssue, ...]:
    Issue = ProjectSQLPlanVerificationIssue
    if type(plan) is not ProjectSQLPlan:
        return (Issue.NON_CONCRETE,)
    try:
        selected = _require_roots(completed, bundle, selected_owner)
        scope = plan.scope
        if (
            type(scope) is not ProjectSQLPlanScope
            or scope.completed is not completed
            or scope.analysis_bundle is not bundle
            or scope.selected_owner is not selected_owner
            or not completed.ok
            or any(d.severity is Severity.ERROR for d in completed.diagnostics)
        ):
            return (Issue.ROOT_CONTINUITY,)
    except (AttributeError, TypeError, ValueError):
        return (Issue.ROOT_CONTINUITY,)
    try:
        dependency = _one(
            tuple(d for d in bundle.root.dependencies if d.consumer is selected_owner),
            "selected dependency",
        )
        source = _one(bundle.root.find_owner(dependency.target), "direct source")
        if (
            type(selected) is not ProjectIRReusedEffectiveOutput
            or type(source) is not ProjectIRReusedEffectiveOutput
            or not _shape(selected, source)
            or any(d.consumer is source.owner for d in bundle.root.dependencies)
        ):
            return (Issue.UNSUPPORTED_SHAPE,)
    except (AttributeError, TypeError, ValueError):
        return (Issue.UNSUPPORTED_SHAPE,)
    issues = []
    for issue, check in (
        (Issue.STRUCTURE, lambda: _structure(plan, selected, source, dependency)),
        (Issue.PORTS_AND_PROJECTIONS, lambda: _ports(plan, selected, source)),
        (Issue.ORIGINS, lambda: _origins(plan, selected, source)),
        (Issue.DEMANDS, lambda: _demands(plan, selected)),
    ):
        try:
            valid = check()
        except (AttributeError, IndexError, TypeError, ValueError):
            valid = False
        if not valid:
            issues.append(issue)
    return tuple(issues)


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
