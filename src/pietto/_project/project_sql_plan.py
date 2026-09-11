"""Private selected static scan/direct-projection SQL planning.

Names are presentation. References belong to one immutable planning scope;
semantic fields, producer definitions and input uses remain distinct.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Never, cast

from pietto._project.model import (
    ProjectResolvedType,
    ProjectRowFieldNullability,
    ProjectSymbolKind,
)
from pietto._project.module_attribution import ProjectModuleRowFieldIdentity
from pietto._project.module_carrier import ProjectCompilationMode, ProjectLogicalModule
from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.module_semantic_fact_preservation import ProjectModuleSelectFact
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
)
from pietto._project.project_completion import ProjectCompletionDependency
from pietto._project.project_ir_composition import ProjectIRCrossRelationEdge
from pietto._project.project_ir_operators import (
    ProjectIRLogicalOperatorKind,
    ProjectIRLogicalOperatorOccurrence,
)
from pietto._project.project_ir_properties import ProjectIRRowField
from pietto._project.project_ir_relational_properties import (
    ProjectIROutputFieldOccurrence,
)
from pietto._project.project_query_block_ir import (
    ProjectIRQueryBlockEntry,
    ProjectIRQueryBlockTerminal,
    ProjectIRReusedEffectiveOutput,
    ProjectIRReboundExistingOutput,
    ProjectIRCompletedQueryBlockOutput,
    ProjectIRQueryBlockOperatorOccurrence,
)
from pietto._project.project_query_block_ir_verification import (
    ProjectIRQueryBlockAnalysisBundle,
)
from pietto.ast_nodes import (
    CallExpr,
    DottedNameExpr,
    FromClause,
    LiteralExpr,
    NameExpr,
    QueryDef,
    SelectItem,
    SetRelationDef,
    SourceDef,
    TableDef,
    JoinClause,
    LetBinding,
    WhereClause,
    GroupByClause,
    SatisfyingClause,
    NamedWindowDeclaration,
    QualifyClause,
    DistinctClause,
    OrderByClause,
    LimitClause,
)
from pietto.errors import Diagnostic

__all__: tuple[str, ...] = ()


def _one[T](values: tuple[T, ...], label: str) -> T:
    if len(values) != 1:
        raise ValueError(f"ProjectSQLPlan requires one exact {label}.")
    return values[0]


def _require_roots(
    completed: ProjectConcreteCompletedSemanticResult,
    bundle: ProjectIRQueryBlockAnalysisBundle,
    selected: ProjectDeclarationOccurrence,
) -> ProjectIRQueryBlockEntry:
    if (
        type(completed) is not ProjectConcreteCompletedSemanticResult
        or type(bundle) is not ProjectIRQueryBlockAnalysisBundle
    ):
        raise TypeError("ProjectSQLPlan requires exact completed and analysis roots.")
    root = bundle.root
    if (
        completed.semantic_result.compilation_mode
        is not ProjectCompilationMode.EXPLICIT_MODULES
        or not bundle.verification.verified
        or bundle.verification.issues
        or root.completed is not completed
        or completed.roots.semantic_result is not completed.semantic_result
        or completed.roots.verification is not completed.verification
        or completed.roots.completion is not completed.completion
        or completed.roots.effective_outputs is not completed.effective_outputs
        or root.base_plan is not completed.completion.plan
        or root.base_plan is not completed.verification.root.evaluation.project_plan
        or root.join_stage is not completed.verification.root.join_regions
        or completed.effective_outputs.base is not completed.completion
        or root.owners is not completed.effective_outputs.owners
        or root.dependencies is not completed.effective_outputs.dependencies
        or root.schedule is not completed.effective_outputs.schedule
    ):
        raise ValueError("ProjectSQLPlan roots are not continuous.")
    # These checks inspect retained graph products; they do not resolve semantics.
    root.__post_init__()
    bundle.__post_init__()
    if type(selected) is not ProjectDeclarationOccurrence or not any(
        o is selected for o in root.owners
    ):
        raise ValueError("ProjectSQLPlan selected owner is foreign or absent.")
    if selected.identity.declaration_kind not in {
        ProjectSymbolKind.TABLE,
        ProjectSymbolKind.QUERY,
    }:
        raise ValueError("ProjectSQLPlan selection requires TABLE or QUERY.")
    return _one(root.find_owner(selected), "selected entry")


def _closure(
    bundle: ProjectIRQueryBlockAnalysisBundle, selected: ProjectDeclarationOccurrence
) -> tuple[ProjectIRQueryBlockEntry, ...]:
    # Coordinates index already-owned occurrences; every edge checks object identity.
    root = bundle.root
    owners = {(o.module_position, o.declaration_position): o for o in root.owners}
    incoming: dict[tuple[int, int], list[ProjectCompletionDependency]] = {
        k: [] for k in owners
    }
    for dependency in root.dependencies:
        consumer = (
            dependency.consumer.module_position,
            dependency.consumer.declaration_position,
        )
        target = (
            dependency.target.module_position,
            dependency.target.declaration_position,
        )
        if (
            owners.get(consumer) is not dependency.consumer
            or owners.get(target) is not dependency.target
        ):
            raise ValueError("ProjectSQLPlan dependency has foreign endpoints.")
        incoming[consumer].append(dependency)
    pending = [(selected.module_position, selected.declaration_position)]
    reached: set[tuple[int, int]] = set()
    while pending:
        key = pending.pop()
        if key not in reached:
            reached.add(key)
            pending.extend(
                (d.target.module_position, d.target.declaration_position)
                for d in incoming[key]
            )
    return tuple(
        e
        for e in root.entries
        if (e.owner.module_position, e.owner.declaration_position) in reached
    )


class ProjectSQLPlanBlockerKind(StrEnum):
    SEMANTIC_RESULT_UNSUCCESSFUL = "semantic_result_unsuccessful"
    ACTIVE_OUTPUT_UNAVAILABLE = "active_output_unavailable"
    NAMED_PRODUCER = "named_producer"
    STATIC_SOURCE_UNAVAILABLE = "static_source_unavailable"
    LET = "let"
    JOIN = "join"
    WHERE = "where"
    GROUP = "group"
    SATISFYING = "satisfying"
    WINDOW = "window"
    QUALIFY = "qualify"
    SCALAR = "scalar"
    DISTINCT = "distinct"
    ORDER = "order"
    LIMIT = "limit"
    SET_OPERATION = "set_operation"
    IR_STAGE = "ir_stage"


type ProjectSQLBlockedStage = (
    JoinClause
    | LetBinding
    | WhereClause
    | GroupByClause
    | SatisfyingClause
    | NamedWindowDeclaration
    | QualifyClause
    | SelectItem
    | DistinctClause
    | OrderByClause
    | LimitClause
    | ProjectIRLogicalOperatorOccurrence
    | ProjectIRQueryBlockOperatorOccurrence
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLPlanBlocker:
    position: int
    kind: ProjectSQLPlanBlockerKind
    owner: ProjectDeclarationOccurrence
    evidence: (
        ProjectIRQueryBlockEntry
        | ProjectCompletionDependency
        | ProjectConcreteCompletedSemanticResult
    )
    site: ProjectSQLBlockedStage | None = None


def _operators(
    entry: ProjectIRQueryBlockEntry,
) -> tuple[
    ProjectIRLogicalOperatorOccurrence | ProjectIRQueryBlockOperatorOccurrence, ...
]:
    if isinstance(entry, ProjectIRReusedEffectiveOutput):
        return entry.semantic_entry.fragment.logical_stage.operators
    if isinstance(entry, ProjectIRReboundExistingOutput):
        return entry.rebuilt_fragment.logical_stage.operators
    if isinstance(entry, ProjectIRCompletedQueryBlockOutput):
        return entry.operators
    return ()


def _static_connector(source: SourceDef) -> CallExpr | None:
    call = source.connector
    if (
        type(call) is not CallExpr
        or len(call.arguments) != 1
        or type(call.arguments[0]) is not LiteralExpr
        or type(call.arguments[0].value) is not str
    ):
        return None
    spelling = (
        call.callee.name
        if isinstance(call.callee, NameExpr)
        else ".".join(call.callee.parts)
    )
    return call if spelling in {"postgres.table", "mysql.table"} else None


def _blockers(
    completed: ProjectConcreteCompletedSemanticResult,
    bundle: ProjectIRQueryBlockAnalysisBundle,
    selected: ProjectDeclarationOccurrence,
) -> tuple[ProjectSQLPlanBlocker, ...]:
    result: list[ProjectSQLPlanBlocker] = []

    def add(
        kind: ProjectSQLPlanBlockerKind,
        owner: ProjectDeclarationOccurrence,
        evidence: ProjectIRQueryBlockEntry
        | ProjectCompletionDependency
        | ProjectConcreteCompletedSemanticResult,
        site: ProjectSQLBlockedStage | None = None,
    ) -> None:
        result.append(
            ProjectSQLPlanBlocker(
                position=len(result),
                kind=kind,
                owner=owner,
                evidence=evidence,
                site=site,
            )
        )

    K = ProjectSQLPlanBlockerKind
    dependencies: dict[tuple[int, int], list[ProjectCompletionDependency]] = {}
    for dependency in bundle.root.dependencies:
        owner = dependency.consumer
        dependencies.setdefault(
            (owner.module_position, owner.declaration_position), []
        ).append(dependency)
    if not completed.ok:
        add(K.SEMANTIC_RESULT_UNSUCCESSFUL, selected, completed)
    for entry in _closure(bundle, selected):
        owner, definition = entry.owner, entry.owner.definition
        if isinstance(entry, ProjectIRQueryBlockTerminal):
            add(K.ACTIVE_OUTPUT_UNAVAILABLE, owner, entry)
        for dependency in dependencies.get(
            (owner.module_position, owner.declaration_position), ()
        ):
            if (
                not isinstance(dependency.target.definition, SourceDef)
                or dependency.target.module_position != owner.module_position
            ):
                add(K.NAMED_PRODUCER, owner, dependency)
        if isinstance(definition, SourceDef):
            if _static_connector(definition) is None:
                add(K.STATIC_SOURCE_UNAVAILABLE, owner, entry)
        elif isinstance(definition, SetRelationDef):
            add(K.SET_OPERATION, owner, entry)
        elif isinstance(definition, (TableDef, QueryDef)):
            for clause in definition.join_clauses:
                add(K.JOIN, owner, entry, clause)
            if definition.let_clause is not None:
                for binding in definition.let_clause.bindings:
                    add(K.LET, owner, entry, binding)
            for present, kind in (
                (definition.where_clause, K.WHERE),
                (definition.group_by_clause, K.GROUP),
                (definition.satisfying_clause, K.SATISFYING),
            ):
                if present:
                    add(kind, owner, entry, present)
            for window in definition.named_windows:
                add(K.WINDOW, owner, entry, window)
            if definition.qualify_clause is not None:
                add(K.QUALIFY, owner, entry, definition.qualify_clause)
            for item in definition.select_items:
                if type(item.expression) not in {NameExpr, DottedNameExpr}:
                    add(K.SCALAR, owner, entry, item)
            for present, kind in (
                (definition.distinct_clause, K.DISTINCT),
                (definition.order_by_clause, K.ORDER),
                (definition.limit_clause, K.LIMIT),
            ):
                if present:
                    add(kind, owner, entry, present)
            # Capture operator-only stages (e.g. GLOBAL aggregation or inline window).
            for operator in _operators(entry):
                if operator.kind not in {
                    ProjectIRLogicalOperatorKind.RELATION_INPUT,
                    ProjectIRLogicalOperatorKind.FINAL_PROJECTION,
                }:
                    add(K.IR_STAGE, owner, entry, operator)
    return tuple(result)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLPlanUnavailable:
    completed: ProjectConcreteCompletedSemanticResult
    analysis_bundle: ProjectIRQueryBlockAnalysisBundle
    selected_owner: ProjectDeclarationOccurrence
    blockers: tuple[ProjectSQLPlanBlocker, ...] = field(init=False)
    plan: None = field(init=False, default=None)

    def __post_init__(self) -> None:
        _require_roots(self.completed, self.analysis_bundle, self.selected_owner)
        blockers = _blockers(self.completed, self.analysis_bundle, self.selected_owner)
        if not blockers:
            raise ValueError("Unavailable planning requires actual blockers.")
        object.__setattr__(self, "blockers", blockers)

    @property
    def diagnostics(self) -> tuple[Diagnostic, ...]:
        return self.completed.diagnostics


class ProjectSQLPlanRefKind(StrEnum):
    SOURCE = "source"
    BLOCK = "block"
    INPUT_USE = "input_use"
    SOURCE_PORT = "source_port"
    INPUT_PORT = "input_port"
    EXPORT = "export"
    PROJECTION = "projection"
    ORIGIN = "origin"
    DEMAND = "demand"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLPlanScope:
    completed: ProjectConcreteCompletedSemanticResult
    analysis_bundle: ProjectIRQueryBlockAnalysisBundle
    selected_owner: ProjectDeclarationOccurrence


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLPlanRef:
    scope: ProjectSQLPlanScope
    kind: ProjectSQLPlanRefKind
    position: int


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSourceBinding:
    ref: ProjectSQLPlanRef
    source: ProjectIRReusedEffectiveOutput
    module: ProjectLogicalModule
    declaration: SourceDef
    connector: CallExpr


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSelectBlock:
    ref: ProjectSQLPlanRef
    selected: ProjectIRReusedEffectiveOutput
    operators: tuple[ProjectIRLogicalOperatorOccurrence, ...]


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLInputUse:
    ref: ProjectSQLPlanRef
    producer: ProjectSQLPlanRef
    consumer: ProjectSQLPlanRef
    edge: ProjectIRCrossRelationEdge
    dependency: ProjectCompletionDependency


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLPort:
    ref: ProjectSQLPlanRef
    owner: ProjectSQLPlanRef
    field: ProjectIROutputFieldOccurrence
    identity: ProjectModuleRowFieldIdentity


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLProjection:
    ref: ProjectSQLPlanRef
    block: ProjectSQLPlanRef
    input_use: ProjectSQLPlanRef
    source_port: ProjectSQLPlanRef
    input_port: ProjectSQLPlanRef
    export: ProjectSQLPlanRef
    semantic: ProjectModuleSelectFact


class ProjectSQLOriginRole(StrEnum):
    SELECTED_OWNER = "selected_owner"
    SOURCE_DESCRIPTOR = "source_descriptor"
    INPUT_USE = "input_use"
    SELECT_BLOCK = "select_block"
    SOURCE_PORT = "source_port"
    INPUT_PORT = "input_port"
    PROJECTION = "projection"
    EXPORT = "export"
    DEMAND = "demand"


class ProjectSQLOriginProvenance(StrEnum):
    VALUE = "value"
    TYPE_PROOF = "type_proof"
    GENERATED_STRUCTURE = "generated_structure"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLOrigin:
    ref: ProjectSQLPlanRef
    subject: ProjectSQLPlanScope | ProjectSQLPlanRef
    role: ProjectSQLOriginRole
    provenance: ProjectSQLOriginProvenance
    owner: ProjectDeclarationOccurrence
    cause: SourceDef | TableDef | QueryDef | FromClause | SelectItem
    evidence: (
        ProjectDeclarationOccurrence
        | ProjectIRCrossRelationEdge
        | ProjectModuleSelectFact
        | ProjectIROutputFieldOccurrence
    )
    antecedents: tuple[ProjectSQLPlanRef, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSourceRealizationDemand:
    ref: ProjectSQLPlanRef
    subject: ProjectSQLPlanRef
    source: ProjectSQLSourceBinding
    origin: ProjectSQLPlanRef


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLExportRepresentationDemand:
    ref: ProjectSQLPlanRef
    subject: ProjectSQLPlanRef
    field: ProjectIROutputFieldOccurrence
    logical_type: ProjectResolvedType
    nullability: ProjectRowFieldNullability
    origin: ProjectSQLPlanRef


type ProjectSQLDemand = (
    ProjectSQLSourceRealizationDemand | ProjectSQLExportRepresentationDemand
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False, init=False)
class ProjectSQLPlan:
    scope: ProjectSQLPlanScope
    sources: tuple[ProjectSQLSourceBinding, ...]
    blocks: tuple[ProjectSQLSelectBlock, ...]
    input_uses: tuple[ProjectSQLInputUse, ...]
    source_ports: tuple[ProjectSQLPort, ...]
    input_ports: tuple[ProjectSQLPort, ...]
    exports: tuple[ProjectSQLPort, ...]
    projections: tuple[ProjectSQLProjection, ...]
    origins: tuple[ProjectSQLOrigin, ...]
    demands: tuple[ProjectSQLDemand, ...]

    def __init__(self) -> Never:
        raise TypeError("ProjectSQLPlan is closed; use build_project_sql_plan.")

    @property
    def diagnostics(self) -> tuple[Diagnostic, ...]:
        return self.scope.completed.diagnostics


def build_project_sql_plan(
    completed: ProjectConcreteCompletedSemanticResult,
    analysis_bundle: ProjectIRQueryBlockAnalysisBundle,
    selected_owner: ProjectDeclarationOccurrence,
) -> ProjectSQLPlan | ProjectSQLPlanUnavailable:
    selected = _require_roots(completed, analysis_bundle, selected_owner)
    if _blockers(completed, analysis_bundle, selected_owner):
        return ProjectSQLPlanUnavailable(
            completed=completed,
            analysis_bundle=analysis_bundle,
            selected_owner=selected_owner,
        )
    if type(selected) is not ProjectIRReusedEffectiveOutput:
        raise ValueError(
            "Minimal direct planning requires exact historical output authority."
        )
    dependency = _one(
        tuple(
            d for d in analysis_bundle.root.dependencies if d.consumer is selected_owner
        ),
        "source dependency",
    )
    source = _one(analysis_bundle.root.find_owner(dependency.target), "source entry")
    if (
        type(source) is not ProjectIRReusedEffectiveOutput
        or type(source.owner.definition) is not SourceDef
    ):
        raise ValueError("Minimal source authority is unavailable.")
    definition = cast(TableDef | QueryDef, selected_owner.definition)
    source_def = source.owner.definition
    connector = _static_connector(source_def)
    if connector is None:
        raise ValueError("Static source authority is unavailable.")
    fragment = selected.semantic_entry.fragment
    edge = _one(
        tuple(
            e
            for e in analysis_bundle.root.base_plan.cross_relation_edges
            if e.consumer is fragment and e.producer is source.semantic_entry.fragment
        ),
        "source input use",
    )
    module = _one(
        tuple(
            c.module
            for c in analysis_bundle.root.base_plan.semantic_facts.authority.catalogs.catalogs
            if any(o is source.owner for o in c.occurrences)
        ),
        "source module",
    )
    scope = ProjectSQLPlanScope(
        completed=completed,
        analysis_bundle=analysis_bundle,
        selected_owner=selected_owner,
    )

    def ref(kind: ProjectSQLPlanRefKind, position: int = 0) -> ProjectSQLPlanRef:
        return ProjectSQLPlanRef(scope=scope, kind=kind, position=position)

    K = ProjectSQLPlanRefKind
    binding = ProjectSQLSourceBinding(
        ref=ref(K.SOURCE),
        source=source,
        module=module,
        declaration=source_def,
        connector=connector,
    )
    block = ProjectSQLSelectBlock(
        ref=ref(K.BLOCK), selected=selected, operators=fragment.logical_stage.operators
    )
    use = ProjectSQLInputUse(
        ref=ref(K.INPUT_USE),
        producer=binding.ref,
        consumer=block.ref,
        edge=edge,
        dependency=dependency,
    )

    def ports(
        entry: ProjectIRReusedEffectiveOutput,
        kind: ProjectSQLPlanRefKind,
        owner: ProjectSQLPlanRef,
    ) -> tuple[ProjectSQLPort, ...]:
        return tuple(
            ProjectSQLPort(
                ref=ref(kind, i),
                owner=owner,
                field=f,
                identity=cast(
                    ProjectIRRowField, entry.active_output.row_shape.fields[i]
                ).anchor.identity,
            )
            for i, f in enumerate(entry.active_properties.relational.fields)
        )

    source_ports = ports(source, K.SOURCE_PORT, binding.ref)
    input_ports = ports(source, K.INPUT_PORT, use.ref)
    exports = ports(selected, K.EXPORT, block.ref)
    # The source schema has unique labels; labels index candidates, never prove identity.
    source_positions = {
        port.field.evidence.name: i for i, port in enumerate(source_ports)
    }
    projections: list[ProjectSQLProjection] = []
    for i, semantic in enumerate(fragment.semantic_facts.select_facts):
        reference = _one(semantic.references, "direct projection reference")
        position = (
            source_positions.get(reference.input_field.name)
            if reference.input_field is not None
            else None
        )
        if position is None:
            raise ValueError("Direct projection lacks an exact source field image.")
        source_port, input_port = source_ports[position], input_ports[position]
        if (
            semantic.field is not exports[i].field.evidence
            or reference.expression is not semantic.item.expression
            or source_port.field.evidence is not reference.input_field
            or input_port.field is not source_port.field
        ):
            raise ValueError(
                "Direct projection lacks exact final/source correspondence."
            )
        projections.append(
            ProjectSQLProjection(
                ref=ref(K.PROJECTION, i),
                block=block.ref,
                input_use=use.ref,
                source_port=source_port.ref,
                input_port=input_port.ref,
                export=exports[i].ref,
                semantic=semantic,
            )
        )
    origins: list[ProjectSQLOrigin] = []
    R, P = ProjectSQLOriginRole, ProjectSQLOriginProvenance

    def origin(
        subject: ProjectSQLPlanScope | ProjectSQLPlanRef,
        role: ProjectSQLOriginRole,
        provenance: ProjectSQLOriginProvenance,
        owner: ProjectDeclarationOccurrence,
        cause: SourceDef | TableDef | QueryDef | FromClause | SelectItem,
        evidence: ProjectDeclarationOccurrence
        | ProjectIRCrossRelationEdge
        | ProjectModuleSelectFact
        | ProjectIROutputFieldOccurrence,
        antecedents: tuple[ProjectSQLPlanRef, ...] = (),
    ) -> ProjectSQLPlanRef:
        value = ProjectSQLOrigin(
            ref=ref(K.ORIGIN, len(origins)),
            subject=subject,
            role=role,
            provenance=provenance,
            owner=owner,
            cause=cause,
            evidence=evidence,
            antecedents=antecedents,
        )
        origins.append(value)
        return value.ref

    origin(
        scope,
        R.SELECTED_OWNER,
        P.GENERATED_STRUCTURE,
        selected_owner,
        definition,
        selected_owner,
    )
    origin(
        binding.ref,
        R.SOURCE_DESCRIPTOR,
        P.GENERATED_STRUCTURE,
        source.owner,
        source_def,
        source.owner,
    )
    origin(
        use.ref,
        R.INPUT_USE,
        P.GENERATED_STRUCTURE,
        selected_owner,
        definition.from_clause,
        edge,
        (binding.ref,),
    )
    origin(
        block.ref,
        R.SELECT_BLOCK,
        P.GENERATED_STRUCTURE,
        selected_owner,
        definition,
        selected_owner,
        (use.ref,),
    )
    for port in source_ports:
        origin(
            port.ref,
            R.SOURCE_PORT,
            P.VALUE,
            source.owner,
            source_def,
            port.field,
            (binding.ref,),
        )
    for port, source_port in zip(input_ports, source_ports, strict=True):
        origin(
            port.ref,
            R.INPUT_PORT,
            P.VALUE,
            selected_owner,
            definition.from_clause,
            port.field,
            (use.ref, source_port.ref),
        )
    for projection, export in zip(projections, exports, strict=True):
        origin(
            projection.ref,
            R.PROJECTION,
            P.VALUE,
            selected_owner,
            projection.semantic.item,
            projection.semantic,
            (projection.input_port,),
        )
        origin(
            export.ref,
            R.EXPORT,
            P.VALUE,
            selected_owner,
            projection.semantic.item,
            export.field,
            (projection.ref,),
        )
    demands: list[ProjectSQLDemand] = []
    demand_ref = ref(K.DEMAND)
    demand_origin = origin(
        demand_ref,
        R.DEMAND,
        P.GENERATED_STRUCTURE,
        source.owner,
        source_def,
        source.owner,
        (binding.ref,),
    )
    demands.append(
        ProjectSQLSourceRealizationDemand(
            ref=demand_ref, subject=binding.ref, source=binding, origin=demand_origin
        )
    )
    for i, (export, projection) in enumerate(zip(exports, projections, strict=True), 1):
        demand_ref = ref(K.DEMAND, i)
        demand_origin = origin(
            demand_ref,
            R.DEMAND,
            P.TYPE_PROOF,
            selected_owner,
            projection.semantic.item,
            export.field,
            (export.ref,),
        )
        demands.append(
            ProjectSQLExportRepresentationDemand(
                ref=demand_ref,
                subject=export.ref,
                field=export.field,
                logical_type=export.field.evidence.resolved_type,
                nullability=export.field.effective_nullability,
                origin=demand_origin,
            )
        )
    # Allocate only after every mandatory correspondence has been established.
    plan = object.__new__(ProjectSQLPlan)
    for name, value in (
        ("scope", scope),
        ("sources", (binding,)),
        ("blocks", (block,)),
        ("input_uses", (use,)),
        ("source_ports", source_ports),
        ("input_ports", input_ports),
        ("exports", exports),
        ("projections", tuple(projections)),
        ("origins", tuple(origins)),
        ("demands", tuple(demands)),
    ):
        object.__setattr__(plan, name, value)
    return plan
