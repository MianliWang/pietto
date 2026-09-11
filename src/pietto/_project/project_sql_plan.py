"""Private selected static scan/direct-projection SQL planning.

Names are presentation. References belong to one immutable planning scope;
semantic fields, producer definitions and input uses remain distinct.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Never, cast
from collections.abc import Mapping
from types import MappingProxyType

from pietto._project.model import (
    ProjectResolvedType,
    ProjectRowFieldNullability,
    ProjectSymbolKind,
)
from pietto._project.module_attribution import (
    ProjectModuleRowFieldIdentity,
    ProjectModuleOriginPath,
)
from pietto._project.module_relation_resolution import (
    ProjectResolvedModuleRelationReference,
    ProjectResolvedModuleRelationSymbol,
    ProjectResolvedSetOperand,
)
from pietto._project.project_relationship_uses import ProjectRelationBindingOccurrence
from pietto._project.project_query_block_ir_algebra import (
    ProjectIRJoinInputCorrespondence,
)
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
from pietto._project.project_ir_relational_properties import (
    ProjectIROutputFieldOccurrence,
)
from pietto._project.project_query_block_ir import (
    ProjectIRQueryBlockEntry,
    ProjectIRConcreteQueryBlockEntry,
    ProjectIRCompletedSetOperationOutput,
    ProjectIRQueryBlockRelationInputEdge,
    ProjectIRSetOperandInput,
    _active_output_identities,
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
    SetOperand,
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
    if not completed.ok:
        add(K.SEMANTIC_RESULT_UNSUCCESSFUL, selected, completed)
    for entry in _closure(bundle, selected):
        owner, definition = entry.owner, entry.owner.definition
        if isinstance(entry, ProjectIRQueryBlockTerminal):
            add(K.ACTIVE_OUTPUT_UNAVAILABLE, owner, entry)
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
    DEFINITION = "definition"
    INPUT_USE = "input_use"
    SOURCE_PORT = "source_port"
    INPUT_PORT = "input_port"
    EXPORT = "export"
    PROJECTION = "projection"
    BOUNDARY = "boundary"
    SYMBOL = "symbol"
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
class ProjectSQLPort:
    ref: ProjectSQLPlanRef
    owner: ProjectSQLPlanRef
    field: ProjectIROutputFieldOccurrence
    identity: ProjectModuleRowFieldIdentity
    producer_port: ProjectSQLPlanRef | None = None


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLDefinition:
    """An upstream named value, not an assertion of a SQL SELECT body."""

    ref: ProjectSQLPlanRef
    entry: ProjectIRConcreteQueryBlockEntry
    exports: tuple[ProjectSQLPort, ...]


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSourceBinding:
    ref: ProjectSQLPlanRef
    source: ProjectIRReusedEffectiveOutput
    module: ProjectLogicalModule
    declaration: SourceDef
    connector: CallExpr


type ProjectSQLInputEdge = (
    ProjectIRCrossRelationEdge
    | ProjectIRQueryBlockRelationInputEdge
    | ProjectIRSetOperandInput
    | ProjectIRJoinInputCorrespondence
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLInputUse:
    ref: ProjectSQLPlanRef
    producer: ProjectSQLPlanRef
    consumer: ProjectSQLPlanRef
    edge: ProjectSQLInputEdge
    dependency: ProjectCompletionDependency
    binding: ProjectResolvedModuleRelationSymbol
    origin_path: ProjectModuleOriginPath
    ports: tuple[ProjectSQLPort, ...]


class ProjectSQLBoundaryReason(StrEnum):
    SOURCE_INPUT = "source_input"
    NAMED_INPUT = "named_input"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLBoundary:
    ref: ProjectSQLPlanRef
    use: ProjectSQLInputUse
    reason: ProjectSQLBoundaryReason


class ProjectSQLSymbolNamespace(StrEnum):
    RELATION_USE = "relation_use"
    FIELD_PORT = "field_port"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSymbol:
    ref: ProjectSQLPlanRef
    scope: ProjectSQLPlanRef
    namespace: ProjectSQLSymbolNamespace
    position: int
    subject: ProjectSQLPlanRef
    label: str


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSelectBlock:
    ref: ProjectSQLPlanRef
    selected: ProjectIRReusedEffectiveOutput
    operators: tuple[ProjectIRLogicalOperatorOccurrence, ...]
    boundary: ProjectSQLBoundary


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLProjection:
    ref: ProjectSQLPlanRef
    block: ProjectSQLPlanRef
    input_use: ProjectSQLPlanRef
    source_port: ProjectSQLPlanRef
    input_port: ProjectSQLPlanRef
    export: ProjectSQLPlanRef
    semantic: ProjectModuleSelectFact
    symbol: ProjectSQLSymbol


class ProjectSQLOriginRole(StrEnum):
    SELECTED_OWNER = "selected_owner"
    DEFINITION = "definition"
    SOURCE_DESCRIPTOR = "source_descriptor"
    INPUT_USE = "input_use"
    SELECT_BLOCK = "select_block"
    SOURCE_PORT = "source_port"
    INPUT_PORT = "input_port"
    STAGE_EXPORT = "stage_export"
    PROJECTION = "projection"
    EXPORT = "export"
    BOUNDARY = "boundary"
    SYMBOL = "symbol"
    DEMAND = "demand"


class ProjectSQLOriginProvenance(StrEnum):
    VALUE = "value"
    MEMBERSHIP = "membership"
    TYPE_PROOF = "type_proof"
    GENERATED_STRUCTURE = "generated_structure"


type ProjectSQLCause = (
    SourceDef
    | TableDef
    | QueryDef
    | SetRelationDef
    | FromClause
    | JoinClause
    | SetOperand
    | SelectItem
)

type ProjectSQLOriginEvidence = (
    ProjectDeclarationOccurrence
    | ProjectIRQueryBlockEntry
    | ProjectCompletionDependency
    | ProjectModuleSelectFact
    | ProjectIROutputFieldOccurrence
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLOrigin:
    ref: ProjectSQLPlanRef
    subject: ProjectSQLPlanScope | ProjectSQLPlanRef
    role: ProjectSQLOriginRole
    provenance: ProjectSQLOriginProvenance
    owner: ProjectDeclarationOccurrence
    cause: ProjectSQLCause
    evidence: ProjectSQLOriginEvidence
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
class ProjectSQLBindings:
    scope: ProjectSQLPlanScope
    definitions: tuple[ProjectSQLDefinition, ...]
    sources: tuple[ProjectSQLSourceBinding, ...]
    input_uses: tuple[ProjectSQLInputUse, ...]
    source_ports: tuple[ProjectSQLPort, ...]
    input_ports: tuple[ProjectSQLPort, ...]
    all_exports: tuple[ProjectSQLPort, ...]
    boundaries: tuple[ProjectSQLBoundary, ...]
    symbols: tuple[ProjectSQLSymbol, ...]
    origins: tuple[ProjectSQLOrigin, ...]
    demands: tuple[ProjectSQLDemand, ...]

    def __init__(self) -> Never:
        raise TypeError("SQL bindings are closed; use build_project_sql_bindings.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False, init=False)
class ProjectSQLPlan:
    scope: ProjectSQLPlanScope
    bindings: ProjectSQLBindings
    sources: tuple[ProjectSQLSourceBinding, ...]
    blocks: tuple[ProjectSQLSelectBlock, ...]
    input_uses: tuple[ProjectSQLInputUse, ...]
    source_ports: tuple[ProjectSQLPort, ...]
    input_ports: tuple[ProjectSQLPort, ...]
    all_exports: tuple[ProjectSQLPort, ...]
    exports: tuple[ProjectSQLPort, ...]
    projections: tuple[ProjectSQLProjection, ...]
    boundaries: tuple[ProjectSQLBoundary, ...]
    symbols: tuple[ProjectSQLSymbol, ...]
    origins: tuple[ProjectSQLOrigin, ...]
    demands: tuple[ProjectSQLDemand, ...]

    def __init__(self) -> Never:
        raise TypeError("ProjectSQLPlan is closed; use build_project_sql_plan.")

    @property
    def diagnostics(self) -> tuple[Diagnostic, ...]:
        return self.scope.completed.diagnostics


def _owner_key(owner: ProjectDeclarationOccurrence) -> tuple[int, int]:
    return owner.module_position, owner.declaration_position


def _dependency_symbol(
    dependency: ProjectCompletionDependency,
) -> ProjectResolvedModuleRelationSymbol:
    evidence = dependency.evidence
    symbol = (
        evidence.target
        if isinstance(evidence, ProjectRelationBindingOccurrence)
        else evidence.target_symbol
    )
    if symbol is None or symbol.target_occurrence is not dependency.target:
        raise ValueError("Input binding requires an exact resolved target.")
    return symbol


def _dependency_site(
    dependency: ProjectCompletionDependency,
) -> FromClause | JoinClause | SetOperand:
    evidence = dependency.evidence
    if isinstance(evidence, ProjectRelationBindingOccurrence):
        return evidence.site
    if isinstance(evidence, ProjectResolvedSetOperand):
        return evidence.reference.operand
    return evidence.reference.from_clause


def _binding_label(dependency: ProjectCompletionDependency) -> str:
    evidence = dependency.evidence
    return (
        evidence.name
        if isinstance(evidence, ProjectRelationBindingOccurrence)
        else _dependency_symbol(dependency).local_name
    )


def _origin_index(
    scope: ProjectSQLPlanScope,
) -> dict[tuple[str, int, int], ProjectModuleOriginPath]:
    """Index existing complete origin paths; no path construction or name lookup."""
    result: dict[tuple[str, int, int], ProjectModuleOriginPath] = {}
    attribution = scope.analysis_bundle.root.base_plan.attribution
    for origin in attribution.origins:
        if origin.import_occurrence is not None:
            occurrence = origin.import_occurrence
            key = (
                origin.owning_module_path,
                occurrence.module_statement_position,
                occurrence.item_position,
            )
        else:
            assert origin.local_occurrence is not None
            occurrence = origin.local_occurrence
            key = (origin.owning_module_path, -1, occurrence.declaration_position)
        if key in result:
            raise ValueError("Origin occurrence index must not choose a winner.")
        result[key] = origin
    return result


def _binding_origin(
    symbol: ProjectResolvedModuleRelationSymbol,
    index: Mapping[tuple[str, int, int], ProjectModuleOriginPath],
) -> ProjectModuleOriginPath:
    imported = symbol.imported_binding
    key = (
        (
            imported.identity.owning_module_path,
            imported.request.module_statement_position,
            imported.request.item_position,
        )
        if imported is not None
        else (
            symbol.owning_module_path,
            -1,
            symbol.target_occurrence.declaration_position,
        )
    )
    origin = index.get(key)
    if (
        origin is None
        or origin.target_occurrence.identity is not symbol.target_occurrence.identity
    ):
        raise ValueError("Resolved binding requires its retained defining origin path.")
    return origin


def _root_inventory(
    scope: ProjectSQLPlanScope,
) -> tuple[
    tuple[ProjectIRConcreteQueryBlockEntry, ...],
    tuple[ProjectCompletionDependency, ...],
    tuple[ProjectSQLInputEdge, ...],
]:
    """Read exact upstream ledgers/active edges, without allocating plan records."""
    root = scope.analysis_bundle.root
    reached = {
        _owner_key(e.owner): e
        for e in _closure(scope.analysis_bundle, scope.selected_owner)
    }
    entries = tuple(
        reached[_owner_key(o)] for o in root.schedule if _owner_key(o) in reached
    )
    if len(entries) != len(reached) or any(
        isinstance(e, ProjectIRQueryBlockTerminal) for e in entries
    ):
        raise ValueError("Bindings require every exact active upstream entry.")
    concrete = cast(tuple[ProjectIRConcreteQueryBlockEntry, ...], entries)
    dependencies = tuple(
        d for d in root.dependencies if _owner_key(d.consumer) in reached
    )
    historical: dict[tuple[int, int], list[ProjectIRCrossRelationEdge]] = {}
    for edge in root.base_plan.cross_relation_edges:
        historical.setdefault(
            _owner_key(edge.consumer.semantic_facts.owner), []
        ).append(edge)
    by_owner = {_owner_key(e.owner): e for e in concrete}
    per_owner: dict[tuple[int, int], list[ProjectCompletionDependency]] = {}
    for dep in dependencies:
        dep.__post_init__()
        per_owner.setdefault(_owner_key(dep.consumer), []).append(dep)
    images: dict[tuple[tuple[int, int], int], ProjectSQLInputEdge] = {}
    for entry in concrete:
        key = _owner_key(entry.owner)
        deps = per_owner.get(key, ())
        if isinstance(entry.owner.definition, SourceDef):
            if deps:
                raise ValueError("A source definition cannot have relation inputs.")
            continue
        if isinstance(entry, ProjectIRReusedEffectiveOutput):
            edge = _one(tuple(historical.get(key, ())), "historical cross edge")
            if len(deps) != 1 or edge.consumer is not entry.semantic_entry.fragment:
                raise ValueError("Historical consumer requires one exact cross edge.")
            images[(key, deps[0].dependency_ordinal)] = edge
        elif isinstance(entry, ProjectIRCompletedSetOperationOutput):
            if len(deps) != len(entry.operands):
                raise ValueError("Set bindings must retain every operand occurrence.")
            for dep, operand in zip(deps, entry.operands, strict=True):
                if operand.source.resolution is not dep.evidence:
                    raise ValueError(
                        "Set binding lost its original operand resolution."
                    )
                images[(key, dep.dependency_ordinal)] = operand
        elif entry.relation_input is not None:
            if (
                len(deps) != 1
                or entry.relation_input.dependency is not deps[0]
                or entry.relation_input.producer
                is not by_owner[_owner_key(deps[0].target)].active_properties
            ):
                raise ValueError("Rebound input must use its active relation edge.")
            images[(key, deps[0].dependency_ordinal)] = entry.relation_input
        elif (
            isinstance(entry, ProjectIRCompletedQueryBlockOutput)
            and entry.join_prefix is not None
        ):
            prefix = entry.join_prefix
            external = tuple(
                i for j in prefix.joins for i in j.inputs if i.producer is not None
            )
            selected: list[ProjectIRJoinInputCorrespondence] = []
            right_inputs: dict[
                JoinClause, list[tuple[JoinClause, ProjectIRJoinInputCorrespondence]]
            ] = {}
            for joined in prefix.joins:
                clause = joined.condition.use.clause
                right_inputs.setdefault(clause, []).append((clause, joined.inputs[1]))
            for dep in deps:
                binding = dep.evidence
                if not isinstance(binding, ProjectRelationBindingOccurrence):
                    raise ValueError(
                        "JOIN input requires the original binding occurrence."
                    )
                matches = (
                    (prefix.joins[0].inputs[0],)
                    if binding.identity.binding_position == 0
                    else tuple(
                        image
                        for clause, image in right_inputs.get(
                            cast(JoinClause, binding.site), ()
                        )
                        if clause is binding.site and image.producer is dep.target
                    )
                )
                image = _one(matches, "authored JOIN input image")
                if image.producer is not dep.target:
                    raise ValueError("JOIN input image has a different named producer.")
                selected.append(image)
                images[(key, dep.dependency_ordinal)] = image
            if len(selected) != len(external) or any(
                a is not b for a, b in zip(selected, external, strict=True)
            ):
                raise ValueError("Binding seam requires complete external JOIN images.")
        else:
            raise ValueError("Active input correspondence is unavailable.")
    return (
        concrete,
        dependencies,
        tuple(
            images[(_owner_key(d.consumer), d.dependency_ordinal)] for d in dependencies
        ),
    )


def _field_site(
    entry: ProjectIRConcreteQueryBlockEntry, position: int
) -> SourceDef | TableDef | QueryDef | SetRelationDef | SelectItem:
    definition = entry.owner.definition
    if isinstance(definition, (TableDef, QueryDef)) and len(
        definition.select_items
    ) == len(entry.active_properties.relational.fields):
        return definition.select_items[position]
    if isinstance(definition, (SourceDef, TableDef, QueryDef, SetRelationDef)):
        return definition
    raise ValueError("Only relation definitions own exported fields.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLBlockContext:
    """Invocation-local lookup indexes; labels are never lookup authority."""

    definition: ProjectSQLDefinition
    symbols: Mapping[ProjectSQLPlanRef, ProjectSQLSymbol]
    subjects: Mapping[ProjectSQLPlanRef, ProjectSQLInputUse | ProjectSQLPort]

    def lookup(
        self, reference: ProjectSQLPlanRef
    ) -> ProjectSQLInputUse | ProjectSQLPort:
        symbol = self.symbols.get(reference)
        if (
            symbol is None
            or symbol.ref is not reference
            or symbol.scope is not self.definition.ref
        ):
            raise ValueError("Symbol does not belong to this block scope.")
        subject = self.subjects.get(symbol.subject)
        if subject is None or subject.ref is not symbol.subject:
            raise ValueError("Symbol subject is not a member of this block scope.")
        if type(symbol.namespace) is not ProjectSQLSymbolNamespace or (
            symbol.namespace is ProjectSQLSymbolNamespace.RELATION_USE
        ) is not isinstance(subject, ProjectSQLInputUse):
            raise ValueError("Symbol namespace does not match its subject role.")
        return subject


def _binding_contexts(
    bindings: ProjectSQLBindings,
) -> dict[ProjectSQLPlanRef, ProjectSQLBlockContext]:
    subjects: dict[
        ProjectSQLPlanRef, dict[ProjectSQLPlanRef, ProjectSQLInputUse | ProjectSQLPort]
    ] = {d.ref: {p.ref: p for p in d.exports} for d in bindings.definitions}
    symbols: dict[ProjectSQLPlanRef, dict[ProjectSQLPlanRef, ProjectSQLSymbol]] = {
        d.ref: {} for d in bindings.definitions
    }
    for use in bindings.input_uses:
        bucket = subjects[use.consumer]
        bucket[use.ref] = use
        bucket.update((p.ref, p) for p in use.ports)
    for symbol in bindings.symbols:
        symbols[symbol.scope][symbol.ref] = symbol
    return {
        d.ref: ProjectSQLBlockContext(
            definition=d,
            symbols=MappingProxyType(symbols[d.ref]),
            subjects=MappingProxyType(subjects[d.ref]),
        )
        for d in bindings.definitions
    }


def build_project_sql_bindings(
    completed: ProjectConcreteCompletedSemanticResult,
    analysis_bundle: ProjectIRQueryBlockAnalysisBundle,
    selected_owner: ProjectDeclarationOccurrence,
) -> ProjectSQLBindings | ProjectSQLPlanUnavailable:
    """The real planner's binding seam; binding success never certifies SQL bodies."""
    _require_roots(completed, analysis_bundle, selected_owner)
    prerequisites = {
        ProjectSQLPlanBlockerKind.SEMANTIC_RESULT_UNSUCCESSFUL,
        ProjectSQLPlanBlockerKind.ACTIVE_OUTPUT_UNAVAILABLE,
        ProjectSQLPlanBlockerKind.STATIC_SOURCE_UNAVAILABLE,
    }
    if any(
        b.kind in prerequisites
        for b in _blockers(completed, analysis_bundle, selected_owner)
    ):
        return ProjectSQLPlanUnavailable(
            completed=completed,
            analysis_bundle=analysis_bundle,
            selected_owner=selected_owner,
        )
    scope = ProjectSQLPlanScope(
        completed=completed,
        analysis_bundle=analysis_bundle,
        selected_owner=selected_owner,
    )
    entries, dependencies, edges = _root_inventory(scope)
    K = ProjectSQLPlanRefKind
    counters = {kind: 0 for kind in K}

    def ref(kind: ProjectSQLPlanRefKind) -> ProjectSQLPlanRef:
        value = ProjectSQLPlanRef(scope=scope, kind=kind, position=counters[kind])
        counters[kind] += 1
        return value

    definitions: list[ProjectSQLDefinition] = []
    sources: list[ProjectSQLSourceBinding] = []
    for entry in entries:
        definition_ref = ref(K.DEFINITION)
        is_source = isinstance(entry.owner.definition, SourceDef)
        identities = _active_output_identities(entry.active_output)
        ports = tuple(
            ProjectSQLPort(
                ref=ref(K.SOURCE_PORT if is_source else K.EXPORT),
                owner=definition_ref,
                field=f,
                identity=identity,
            )
            for f, identity in zip(
                entry.active_properties.relational.fields, identities, strict=True
            )
        )
        definitions.append(
            ProjectSQLDefinition(ref=definition_ref, entry=entry, exports=ports)
        )
        if is_source:
            source_def = cast(SourceDef, entry.owner.definition)
            connector = _static_connector(source_def)
            if (
                not isinstance(entry, ProjectIRReusedEffectiveOutput)
                or connector is None
            ):
                raise ValueError("Static source binding lacks exact authority.")
            module = completed.semantic_result.modules[entry.owner.module_position]
            sources.append(
                ProjectSQLSourceBinding(
                    ref=definition_ref,
                    source=entry,
                    module=module,
                    declaration=source_def,
                    connector=connector,
                )
            )
    by_owner = {_owner_key(d.entry.owner): d for d in definitions}
    uses: list[ProjectSQLInputUse] = []
    origin_index = _origin_index(scope)
    for dependency, edge in zip(dependencies, edges, strict=True):
        producer, consumer = (
            by_owner[_owner_key(dependency.target)],
            by_owner[_owner_key(dependency.consumer)],
        )
        if edge.use.output is not producer.entry.active_output.occurrence:
            raise ValueError("Binding must consume the actual active producer output.")
        use_ref = ref(K.INPUT_USE)
        ports = tuple(
            ProjectSQLPort(
                ref=ref(K.INPUT_PORT),
                owner=use_ref,
                field=p.field,
                identity=p.identity,
                producer_port=p.ref,
            )
            for p in producer.exports
        )
        binding = _dependency_symbol(dependency)
        uses.append(
            ProjectSQLInputUse(
                ref=use_ref,
                producer=producer.ref,
                consumer=consumer.ref,
                edge=edge,
                dependency=dependency,
                binding=binding,
                origin_path=_binding_origin(binding, origin_index),
                ports=ports,
            )
        )
    by_ref = {d.ref: d for d in definitions}
    boundaries = tuple(
        ProjectSQLBoundary(
            ref=ref(K.BOUNDARY),
            use=u,
            reason=ProjectSQLBoundaryReason.SOURCE_INPUT
            if isinstance(by_ref[u.producer].entry.owner.definition, SourceDef)
            else ProjectSQLBoundaryReason.NAMED_INPUT,
        )
        for u in uses
    )
    per_consumer: dict[ProjectSQLPlanRef, list[ProjectSQLInputUse]] = {
        d.ref: [] for d in definitions
    }
    for use in uses:
        per_consumer[use.consumer].append(use)
    symbols: list[ProjectSQLSymbol] = []
    for definition in definitions:
        local_uses = per_consumer[definition.ref]
        for i, use in enumerate(local_uses):
            symbols.append(
                ProjectSQLSymbol(
                    ref=ref(K.SYMBOL),
                    scope=definition.ref,
                    namespace=ProjectSQLSymbolNamespace.RELATION_USE,
                    position=i,
                    subject=use.ref,
                    label=_binding_label(use.dependency),
                )
            )
        for i, port in enumerate(
            (*[p for u in local_uses for p in u.ports], *definition.exports)
        ):
            symbols.append(
                ProjectSQLSymbol(
                    ref=ref(K.SYMBOL),
                    scope=definition.ref,
                    namespace=ProjectSQLSymbolNamespace.FIELD_PORT,
                    position=i,
                    subject=port.ref,
                    label=port.identity.name,
                )
            )
    origins: list[ProjectSQLOrigin] = []
    R, P = ProjectSQLOriginRole, ProjectSQLOriginProvenance

    def origin(
        subject: ProjectSQLPlanScope | ProjectSQLPlanRef,
        role: ProjectSQLOriginRole,
        provenance: ProjectSQLOriginProvenance,
        owner: ProjectDeclarationOccurrence,
        cause: ProjectSQLCause,
        evidence: ProjectSQLOriginEvidence,
        antecedents: tuple[ProjectSQLPlanRef, ...] = (),
    ) -> ProjectSQLPlanRef:
        value = ProjectSQLOrigin(
            ref=ref(K.ORIGIN),
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
        cast(TableDef | QueryDef | SetRelationDef, selected_owner.definition),
        selected_owner,
    )
    for definition in definitions:
        entry = definition.entry
        origin(
            definition.ref,
            R.DEFINITION,
            P.GENERATED_STRUCTURE,
            entry.owner,
            cast(
                SourceDef | TableDef | QueryDef | SetRelationDef, entry.owner.definition
            ),
            entry,
        )
        for i, port in enumerate(definition.exports):
            origin(
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
    for source in sources:
        origin(
            source.ref,
            R.SOURCE_DESCRIPTOR,
            P.GENERATED_STRUCTURE,
            source.source.owner,
            source.declaration,
            source.source.owner,
        )
    input_by_ref = {u.ref: u for u in uses}
    for use in uses:
        dep = use.dependency
        provenance = (
            P.GENERATED_STRUCTURE
            if isinstance(dep.evidence, ProjectResolvedModuleRelationReference)
            else P.MEMBERSHIP
        )
        origin(
            use.ref,
            R.INPUT_USE,
            provenance,
            dep.consumer,
            _dependency_site(dep),
            dep,
            (use.producer,),
        )
        for port in use.ports:
            assert port.producer_port is not None
            origin(
                port.ref,
                R.INPUT_PORT,
                P.VALUE,
                dep.consumer,
                _dependency_site(dep),
                port.field,
                (use.ref, port.producer_port),
            )
    for boundary in boundaries:
        dep = boundary.use.dependency
        origin(
            boundary.ref,
            R.BOUNDARY,
            P.GENERATED_STRUCTURE,
            dep.consumer,
            _dependency_site(dep),
            dep,
            (boundary.use.ref,),
        )
    ports_by_ref = {p.ref: p for d in definitions for p in d.exports} | {
        p.ref: p for u in uses for p in u.ports
    }
    for symbol in symbols:
        owner = by_ref[symbol.scope].entry.owner
        if symbol.namespace is ProjectSQLSymbolNamespace.RELATION_USE:
            dep = input_by_ref[symbol.subject].dependency
            cause, evidence = _dependency_site(dep), dep
        else:
            port = ports_by_ref[symbol.subject]
            cause = (
                _dependency_site(input_by_ref[port.owner].dependency)
                if port.owner in input_by_ref
                else _field_site(by_ref[port.owner].entry, port.field.field_position)
            )
            evidence = port.field
        origin(
            symbol.ref,
            R.SYMBOL,
            P.GENERATED_STRUCTURE,
            owner,
            cause,
            evidence,
            (symbol.subject,),
        )
    demands: list[ProjectSQLDemand] = []
    for source in sources:
        demand_ref = ref(K.DEMAND)
        demand_origin = origin(
            demand_ref,
            R.DEMAND,
            P.GENERATED_STRUCTURE,
            source.source.owner,
            source.declaration,
            source.source.owner,
            (source.ref,),
        )
        demands.append(
            ProjectSQLSourceRealizationDemand(
                ref=demand_ref, subject=source.ref, source=source, origin=demand_origin
            )
        )
    for definition in definitions:
        if isinstance(definition.entry.owner.definition, SourceDef):
            continue
        for i, port in enumerate(definition.exports):
            demand_ref = ref(K.DEMAND)
            demand_origin = origin(
                demand_ref,
                R.DEMAND,
                P.TYPE_PROOF,
                definition.entry.owner,
                _field_site(definition.entry, i),
                port.field,
                (port.ref,),
            )
            demands.append(
                ProjectSQLExportRepresentationDemand(
                    ref=demand_ref,
                    subject=port.ref,
                    field=port.field,
                    logical_type=port.field.evidence.resolved_type,
                    nullability=port.field.effective_nullability,
                    origin=demand_origin,
                )
            )
    bindings = object.__new__(ProjectSQLBindings)
    for name, value in dict(
        scope=scope,
        definitions=tuple(definitions),
        sources=tuple(sources),
        input_uses=tuple(uses),
        source_ports=tuple(
            p
            for d in definitions
            if isinstance(d.entry.owner.definition, SourceDef)
            for p in d.exports
        ),
        input_ports=tuple(p for u in uses for p in u.ports),
        all_exports=tuple(
            p
            for d in definitions
            if not isinstance(d.entry.owner.definition, SourceDef)
            for p in d.exports
        ),
        boundaries=boundaries,
        symbols=tuple(symbols),
        origins=tuple(origins),
        demands=tuple(demands),
    ).items():
        object.__setattr__(bindings, name, value)
    return bindings


def build_project_sql_plan(
    completed: ProjectConcreteCompletedSemanticResult,
    analysis_bundle: ProjectIRQueryBlockAnalysisBundle,
    selected_owner: ProjectDeclarationOccurrence,
) -> ProjectSQLPlan | ProjectSQLPlanUnavailable:
    _require_roots(completed, analysis_bundle, selected_owner)
    if _blockers(completed, analysis_bundle, selected_owner):
        return ProjectSQLPlanUnavailable(
            completed=completed,
            analysis_bundle=analysis_bundle,
            selected_owner=selected_owner,
        )
    bindings = build_project_sql_bindings(completed, analysis_bundle, selected_owner)
    if isinstance(bindings, ProjectSQLPlanUnavailable):
        return bindings
    contexts = _binding_contexts(bindings)
    boundary_by_consumer = {b.use.consumer: b for b in bindings.boundaries}
    symbol_by_subject = {s.subject: s for s in bindings.symbols}
    blocks: list[ProjectSQLSelectBlock] = []
    projections: list[ProjectSQLProjection] = []
    origins = list(bindings.origins)
    K, R, P = ProjectSQLPlanRefKind, ProjectSQLOriginRole, ProjectSQLOriginProvenance

    def origin(subject, role, owner, cause, evidence, antecedents):
        origins.append(
            ProjectSQLOrigin(
                ref=ProjectSQLPlanRef(
                    scope=bindings.scope, kind=K.ORIGIN, position=len(origins)
                ),
                subject=subject,
                role=role,
                provenance=P.GENERATED_STRUCTURE if role is R.SELECT_BLOCK else P.VALUE,
                owner=owner,
                cause=cause,
                evidence=evidence,
                antecedents=antecedents,
            )
        )

    for definition in bindings.definitions:
        entry = definition.entry
        if isinstance(entry.owner.definition, SourceDef):
            continue
        if not isinstance(entry, ProjectIRReusedEffectiveOutput):
            raise ValueError(
                "Direct named projection requires its current exact fragment."
            )
        context = contexts[definition.ref]
        local_uses = tuple(
            s for s in context.subjects.values() if isinstance(s, ProjectSQLInputUse)
        )
        use = _one(local_uses, "direct projection input use")
        boundary = boundary_by_consumer[definition.ref]
        block = ProjectSQLSelectBlock(
            ref=definition.ref,
            selected=entry,
            operators=entry.semantic_entry.fragment.logical_stage.operators,
            boundary=boundary,
        )
        blocks.append(block)
        origin(
            block.ref,
            R.SELECT_BLOCK,
            entry.owner,
            entry.owner.definition,
            entry,
            (boundary.ref,),
        )
        input_by_label = {p.field.evidence.name: p for p in use.ports}
        for semantic, export in zip(
            entry.semantic_entry.fragment.semantic_facts.select_facts,
            definition.exports,
            strict=True,
        ):
            reference = _one(semantic.references, "direct projection reference")
            port = (
                input_by_label.get(reference.input_field.name)
                if reference.input_field is not None
                else None
            )
            if (
                port is None
                or port.field.evidence is not reference.input_field
                or semantic.field is not export.field.evidence
                or port.producer_port is None
            ):
                raise ValueError(
                    "Projection must reference the immediate producer field."
                )
            symbol = symbol_by_subject[port.ref]
            if context.lookup(symbol.ref) is not port:
                raise ValueError("Projection input is outside its block context.")
            projection = ProjectSQLProjection(
                ref=ProjectSQLPlanRef(
                    scope=bindings.scope, kind=K.PROJECTION, position=len(projections)
                ),
                block=block.ref,
                input_use=use.ref,
                source_port=port.producer_port,
                input_port=port.ref,
                export=export.ref,
                semantic=semantic,
                symbol=symbol,
            )
            projections.append(projection)
            origin(
                projection.ref,
                R.PROJECTION,
                entry.owner,
                semantic.item,
                semantic,
                (port.ref,),
            )
            origin(
                export.ref,
                R.EXPORT,
                entry.owner,
                semantic.item,
                export.field,
                (projection.ref,),
            )
    selected = _one(
        tuple(d for d in bindings.definitions if d.entry.owner is selected_owner),
        "selected definition",
    )
    plan = object.__new__(ProjectSQLPlan)
    for name, value in dict(
        scope=bindings.scope,
        bindings=bindings,
        sources=bindings.sources,
        blocks=tuple(blocks),
        input_uses=bindings.input_uses,
        source_ports=bindings.source_ports,
        input_ports=bindings.input_ports,
        all_exports=bindings.all_exports,
        exports=selected.exports,
        projections=tuple(projections),
        boundaries=bindings.boundaries,
        symbols=bindings.symbols,
        origins=tuple(origins),
        demands=bindings.demands,
    ).items():
        object.__setattr__(plan, name, value)
    return plan
