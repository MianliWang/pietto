"""Private project carriers for future window result readiness."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import StrEnum

from pietto._project.model import (
    ProjectRowSchema,
    ProjectRowFieldProvenance,
    ProjectRowFieldProvenanceKind,
    ProjectRowResultRole,
    ProjectSymbol,
)
from pietto._project.row_dependency_graph import (
    ProjectRowDependencyNode,
    ProjectRowDependencyNodeKind,
)
from pietto.ast_nodes import (
    DottedNameExpr,
    Expression,
    NameExpr,
    QueryDef,
    SelectItem,
    Span,
    TableDef,
    WindowExpr,
    WindowUseKind,
)
from pietto.errors import Diagnostic, SourceLocation
from pietto.semantic.window_semantics import (
    WindowExpressionAnalysis,
    WindowExpressionSemanticFact,
    WindowExpressionUnsupported,
    WindowOccurrenceIdentity,
)
from pietto.semantic.model import ValueType
from pietto.semantic.window_input_analysis import (
    WindowInputOriginKind,
    WindowInputScope,
    build_window_input_scope,
)

__all__: tuple[str, ...] = ()

_PROJECT_NAMED_WINDOW_INTEGRATION_DEFERRED = "project named-window integration deferred"


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowResultIdentity:
    """One explicit project-local output identity for a window result."""

    definition: TableDef | QueryDef
    output_name: str
    occurrence: WindowOccurrenceIdentity
    role: ProjectRowResultRole = ProjectRowResultRole.WINDOW_RESULT

    def __post_init__(self) -> None:
        if type(self.definition) not in {TableDef, QueryDef}:
            raise TypeError("definition must be an exact TableDef or QueryDef")
        if type(self.output_name) is not str:
            raise TypeError("output_name must be an exact string")
        if not self.output_name.strip():
            raise ValueError("output_name must be nonblank")
        if type(self.occurrence) is not WindowOccurrenceIdentity:
            raise TypeError("occurrence must be an exact WindowOccurrenceIdentity")
        if type(self.role) is not ProjectRowResultRole:
            raise TypeError("role must be an exact ProjectRowResultRole")
        if self.role is not ProjectRowResultRole.WINDOW_RESULT:
            raise ValueError("window result identity role must be WINDOW_RESULT")
        if self.definition.name != self.occurrence.relation_name:
            raise ValueError("definition name must equal occurrence relation_name")


class WindowDependencyRole(StrEnum):
    """Source-ordered dependency roles for private window readiness."""

    RELATION_INPUT = "relation_input"
    WINDOW_ARGUMENT = "window_argument"
    WINDOW_DEFAULT = "window_default"
    WINDOW_PARTITION = "window_partition"
    WINDOW_ORDER = "window_order"


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowDependencyOccurrence:
    """One duplicate-preserving resolved dependency occurrence."""

    global_ordinal: int
    role_ordinal: int
    role: WindowDependencyRole
    target: ProjectRowDependencyNode
    location: SourceLocation
    target_result_role: ProjectRowResultRole | None = None

    def __post_init__(self) -> None:
        if type(self.global_ordinal) is not int:
            raise TypeError("global_ordinal must be an exact integer")
        if self.global_ordinal < 0:
            raise ValueError("global_ordinal must be nonnegative")
        if type(self.role_ordinal) is not int:
            raise TypeError("role_ordinal must be an exact integer")
        if self.role_ordinal < 0:
            raise ValueError("role_ordinal must be nonnegative")
        if type(self.role) is not WindowDependencyRole:
            raise TypeError("role must be an exact WindowDependencyRole")
        if type(self.target) is not ProjectRowDependencyNode:
            raise TypeError("target must be an exact ProjectRowDependencyNode")
        if type(self.location) is not SourceLocation:
            raise TypeError("location must be an exact SourceLocation")
        if self.role is WindowDependencyRole.RELATION_INPUT:
            if self.target.kind is not ProjectRowDependencyNodeKind.RELATION_INPUT:
                raise ValueError("RELATION_INPUT requires a relation-input target")
        elif self.target.kind not in {
            ProjectRowDependencyNodeKind.UPSTREAM_FIELD,
            ProjectRowDependencyNodeKind.LET_BINDING,
            ProjectRowDependencyNodeKind.OUTPUT_FIELD,
        }:
            raise ValueError(
                "window expression dependencies require bounded field targets"
            )
        _validate_target_result_role(self.target, self.target_result_role)


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowDependencyEdge:
    """One first-occurrence-deduplicated role and target pair."""

    role: WindowDependencyRole
    target: ProjectRowDependencyNode
    target_result_role: ProjectRowResultRole | None = None

    def __post_init__(self) -> None:
        if type(self.role) is not WindowDependencyRole:
            raise TypeError("role must be an exact WindowDependencyRole")
        if type(self.target) is not ProjectRowDependencyNode:
            raise TypeError("target must be an exact ProjectRowDependencyNode")
        if self.role is WindowDependencyRole.RELATION_INPUT:
            if self.target.kind is not ProjectRowDependencyNodeKind.RELATION_INPUT:
                raise ValueError("RELATION_INPUT requires a relation-input target")
        elif self.target.kind not in {
            ProjectRowDependencyNodeKind.UPSTREAM_FIELD,
            ProjectRowDependencyNodeKind.LET_BINDING,
            ProjectRowDependencyNodeKind.OUTPUT_FIELD,
        }:
            raise ValueError(
                "window expression dependencies require bounded field targets"
            )
        _validate_target_result_role(self.target, self.target_result_role)


def deduplicate_window_dependency_edges(
    occurrences: tuple[WindowDependencyOccurrence, ...],
) -> tuple[WindowDependencyEdge, ...]:
    """Return role-target edges in deterministic first-occurrence order."""

    if type(occurrences) is not tuple:
        raise TypeError("occurrences must be an exact tuple")
    if any(type(item) is not WindowDependencyOccurrence for item in occurrences):
        raise TypeError("occurrences must contain exact WindowDependencyOccurrence")

    seen: dict[
        tuple[WindowDependencyRole, ProjectRowDependencyNode],
        ProjectRowResultRole | None,
    ] = {}
    edges: list[WindowDependencyEdge] = []
    for occurrence in occurrences:
        key = (occurrence.role, occurrence.target)
        if key in seen:
            if seen[key] is not occurrence.target_result_role:
                raise ValueError("one role-target pair cannot carry conflicting roles")
            continue
        seen[key] = occurrence.target_result_role
        edges.append(
            WindowDependencyEdge(
                role=occurrence.role,
                target=occurrence.target,
                target_result_role=occurrence.target_result_role,
            )
        )
    return tuple(edges)


def _validate_target_result_role(
    target: ProjectRowDependencyNode,
    target_result_role: ProjectRowResultRole | None,
) -> None:
    if target.kind is ProjectRowDependencyNodeKind.OUTPUT_FIELD:
        if target_result_role not in {
            ProjectRowResultRole.GROUP_KEY,
            ProjectRowResultRole.AGGREGATE_RESULT,
        }:
            raise ValueError(
                "OUTPUT_FIELD window dependency requires GROUP_KEY or AGGREGATE_RESULT"
            )
        return
    if target_result_role is not None:
        raise ValueError("non-output window dependency forbids target_result_role")


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowResultProjectFact:
    """Atomic private result, dependency, and immediate-provenance evidence."""

    semantic_fact: WindowExpressionSemanticFact
    result_identity: WindowResultIdentity
    dependency_occurrences: tuple[WindowDependencyOccurrence, ...]
    dependency_edges: tuple[WindowDependencyEdge, ...]
    provenance: ProjectRowFieldProvenance

    def __post_init__(self) -> None:
        if type(self.semantic_fact) is not WindowExpressionSemanticFact:
            raise TypeError("semantic_fact must be exact WindowExpressionSemanticFact")
        if type(self.result_identity) is not WindowResultIdentity:
            raise TypeError("result_identity must be an exact WindowResultIdentity")
        if type(self.dependency_occurrences) is not tuple:
            raise TypeError("dependency_occurrences must be an exact tuple")
        if any(
            type(item) is not WindowDependencyOccurrence
            for item in self.dependency_occurrences
        ):
            raise TypeError(
                "dependency_occurrences require exact WindowDependencyOccurrence"
            )
        if type(self.dependency_edges) is not tuple:
            raise TypeError("dependency_edges must be an exact tuple")
        if any(
            type(item) is not WindowDependencyEdge for item in self.dependency_edges
        ):
            raise TypeError("dependency_edges require exact WindowDependencyEdge")
        if type(self.provenance) is not ProjectRowFieldProvenance:
            raise TypeError("provenance must be an exact ProjectRowFieldProvenance")

        if self.semantic_fact.occurrence != self.result_identity.occurrence:
            raise ValueError("semantic and result occurrences must match")
        if (
            self.result_identity.definition.name
            != self.semantic_fact.occurrence.relation_name
        ):
            raise ValueError("output relation identity must be consistent")

        expected_global_ordinals = tuple(range(len(self.dependency_occurrences)))
        if (
            tuple(item.global_ordinal for item in self.dependency_occurrences)
            != expected_global_ordinals
        ):
            raise ValueError("dependency global ordinals must be contiguous")

        role_order = tuple(WindowDependencyRole)
        role_positions = tuple(
            role_order.index(item.role) for item in self.dependency_occurrences
        )
        if role_positions != tuple(sorted(role_positions)):
            raise ValueError("dependency occurrences must preserve role block order")
        for role in role_order:
            role_occurrences = tuple(
                item for item in self.dependency_occurrences if item.role is role
            )
            if tuple(item.role_ordinal for item in role_occurrences) != tuple(
                range(len(role_occurrences))
            ):
                raise ValueError("dependency role ordinals must be contiguous")

        expected_edges = deduplicate_window_dependency_edges(
            self.dependency_occurrences
        )
        if self.dependency_edges != expected_edges:
            raise ValueError("dependency edges must equal first-occurrence derivation")

        relation_occurrences = tuple(
            item
            for item in self.dependency_occurrences
            if item.role is WindowDependencyRole.RELATION_INPUT
        )
        relation_edges = tuple(
            item
            for item in self.dependency_edges
            if item.role is WindowDependencyRole.RELATION_INPUT
        )
        has_argument_or_default = any(
            item.role
            in {
                WindowDependencyRole.WINDOW_ARGUMENT,
                WindowDependencyRole.WINDOW_DEFAULT,
            }
            for item in self.dependency_occurrences
        )
        if not has_argument_or_default:
            if len(relation_occurrences) != 1 or len(relation_edges) != 1:
                raise ValueError(
                    "dependency-free window readiness requires one relation input"
                )
        elif relation_occurrences or relation_edges:
            raise ValueError(
                "argument-dependent window readiness forbids relation input"
            )

        if type(self.provenance.kind) is not ProjectRowFieldProvenanceKind:
            raise TypeError(
                "provenance kind must be an exact ProjectRowFieldProvenanceKind"
            )
        if self.provenance.kind is not ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION:
            raise ValueError("window result provenance must be DERIVED_EXPRESSION")
        if (
            self.provenance.symbol is not None
            and type(self.provenance.symbol) is not ProjectSymbol
        ):
            raise TypeError("provenance symbol must be an exact ProjectSymbol")
        if (
            self.provenance.location is not None
            and type(self.provenance.location) is not SourceLocation
        ):
            raise TypeError("provenance location must be an exact SourceLocation")
        span = self.semantic_fact.occurrence.span
        expected_location = SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        )
        if self.provenance.location != expected_location:
            raise ValueError("provenance location must match occurrence location")


def build_window_result_project_fact(
    *,
    definition: TableDef | QueryDef,
    item: SelectItem,
    selected_output_ordinal: int,
    source_id: str,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    let_value_types: Mapping[str, ValueType] | None = None,
    let_expressions: Mapping[str, Expression] | None = None,
) -> WindowResultProjectFact | WindowExpressionUnsupported:
    """Build one transient project fact for any recognized window success."""

    from pietto._project.row_expression_type_facts import (
        project_row_schema_to_semantic_row_schema,
    )
    from pietto.semantic.window_analysis import analyze_window_expression

    diagnostics: list[Diagnostic] = []
    let_value_types = let_value_types or {}
    let_expressions = let_expressions or {}
    semantic_input_schema = project_row_schema_to_semantic_row_schema(input_schema)
    value_types: dict[Expression, ValueType] = {}
    semantic_result = analyze_window_expression(
        definition=definition,
        item=item,
        selected_output_ordinal=selected_output_ordinal,
        source_id=source_id,
        input_schema=semantic_input_schema,
        field_qualifier=definition.from_clause.source_name,
        value_types=value_types,
        diagnostics=diagnostics,
        let_value_types=let_value_types,
        let_expressions=let_expressions,
    )
    semantic_result = _project_window_analysis_boundary(item, semantic_result)
    if isinstance(semantic_result, WindowExpressionUnsupported):
        return semantic_result
    if type(semantic_result) is not WindowExpressionAnalysis:
        raise AssertionError("recognized window analyzer returned an unknown fact")
    input_scope = build_window_input_scope(
        definition=definition,
        input_schema=semantic_input_schema,
        field_qualifier=definition.from_clause.source_name,
        value_types=value_types,
        let_value_types=let_value_types,
        let_expressions=let_expressions,
    )
    return _build_window_result_project_fact(
        semantic_fact=semantic_result.semantic_fact,
        definition=definition,
        item=item,
        upstream_symbol=upstream_symbol,
        input_scope=input_scope,
    )


def build_ranking_window_result_project_fact(
    *,
    definition: TableDef | QueryDef,
    item: SelectItem,
    selected_output_ordinal: int,
    source_id: str,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    let_value_types: Mapping[str, ValueType] | None = None,
    let_expressions: Mapping[str, Expression] | None = None,
) -> WindowResultProjectFact | WindowExpressionUnsupported:
    """Build one transient project fact for an exact ranking semantic success."""

    from pietto._project.row_expression_type_facts import (
        project_row_schema_to_semantic_row_schema,
    )
    from pietto.semantic.window_analysis import (
        analyze_ranking_window_expression,
    )

    diagnostics: list[Diagnostic] = []
    let_value_types = let_value_types or {}
    let_expressions = let_expressions or {}
    semantic_input_schema = project_row_schema_to_semantic_row_schema(input_schema)
    value_types: dict[Expression, ValueType] = {}
    semantic_result = analyze_ranking_window_expression(
        definition=definition,
        item=item,
        selected_output_ordinal=selected_output_ordinal,
        source_id=source_id,
        input_schema=semantic_input_schema,
        field_qualifier=definition.from_clause.source_name,
        value_types=value_types,
        diagnostics=diagnostics,
        let_value_types=let_value_types,
        let_expressions=let_expressions,
    )
    if isinstance(semantic_result, WindowExpressionUnsupported):
        return _retain_project_window_unsupported_authorship(item, semantic_result)
    input_scope = build_window_input_scope(
        definition=definition,
        input_schema=semantic_input_schema,
        field_qualifier=definition.from_clause.source_name,
        value_types=value_types,
        let_value_types=let_value_types,
        let_expressions=let_expressions,
    )
    return _build_window_result_project_fact(
        semantic_fact=semantic_result.semantic_fact,
        definition=definition,
        item=item,
        upstream_symbol=upstream_symbol,
        input_scope=input_scope,
    )


def build_navigation_window_result_project_fact(
    *,
    definition: TableDef | QueryDef,
    item: SelectItem,
    selected_output_ordinal: int,
    source_id: str,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    let_value_types: Mapping[str, ValueType] | None = None,
    let_expressions: Mapping[str, Expression] | None = None,
) -> WindowResultProjectFact | WindowExpressionUnsupported:
    """Build one transient project fact for an exact navigation success."""

    from pietto._project.row_expression_type_facts import (
        project_row_schema_to_semantic_row_schema,
    )
    from pietto.semantic.window_analysis import (
        analyze_navigation_window_expression,
    )

    diagnostics: list[Diagnostic] = []
    let_value_types = let_value_types or {}
    let_expressions = let_expressions or {}
    semantic_input_schema = project_row_schema_to_semantic_row_schema(input_schema)
    value_types: dict[Expression, ValueType] = {}
    semantic_result = analyze_navigation_window_expression(
        definition=definition,
        item=item,
        selected_output_ordinal=selected_output_ordinal,
        source_id=source_id,
        input_schema=semantic_input_schema,
        field_qualifier=definition.from_clause.source_name,
        value_types=value_types,
        diagnostics=diagnostics,
        let_value_types=let_value_types,
        let_expressions=let_expressions,
    )
    if isinstance(semantic_result, WindowExpressionUnsupported):
        return _retain_project_window_unsupported_authorship(item, semantic_result)
    input_scope = build_window_input_scope(
        definition=definition,
        input_schema=semantic_input_schema,
        field_qualifier=definition.from_clause.source_name,
        value_types=value_types,
        let_value_types=let_value_types,
        let_expressions=let_expressions,
    )
    return _build_window_result_project_fact(
        semantic_fact=semantic_result.semantic_fact,
        definition=definition,
        item=item,
        upstream_symbol=upstream_symbol,
        input_scope=input_scope,
    )


def build_row_number_window_result_project_fact(
    *,
    definition: TableDef | QueryDef,
    item: SelectItem,
    selected_output_ordinal: int,
    source_id: str,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    let_value_types: Mapping[str, ValueType] | None = None,
    let_expressions: Mapping[str, Expression] | None = None,
) -> WindowResultProjectFact | WindowExpressionUnsupported:
    """Retain the Slice 7 project-fact result shape through the ranking builder."""

    return build_ranking_window_result_project_fact(
        definition=definition,
        item=item,
        selected_output_ordinal=selected_output_ordinal,
        source_id=source_id,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        let_value_types=let_value_types,
        let_expressions=let_expressions,
    )


def _build_window_result_project_fact(
    *,
    semantic_fact: WindowExpressionSemanticFact,
    definition: TableDef | QueryDef,
    item: SelectItem,
    upstream_symbol: ProjectSymbol,
    input_scope: WindowInputScope,
) -> WindowResultProjectFact | WindowExpressionUnsupported:
    """Convert eligible inline semantics or defer named Project integration."""

    deferred = _project_named_window_deferral(item, semantic_fact)
    if deferred is not None:
        return deferred

    if item.alias is None:
        raise AssertionError("successful window project fact requires an alias")

    expression = semantic_fact.expression
    partition_expressions = expression.spec.partition_by
    order_expressions = tuple(
        order_item.expression for order_item in expression.spec.order_by
    )
    navigation_arguments: tuple[Expression, ...] = ()
    navigation_defaults: tuple[Expression, ...] = ()
    if semantic_fact.identity.name in {
        "lag",
        "lead",
        "first_value",
        "last_value",
        "nth_value",
    }:
        value_expression = expression.call.arguments[0]
        if type(value_expression) in {NameExpr, DottedNameExpr}:
            navigation_arguments = (value_expression,)
        if len(expression.call.arguments) == 3:
            default_expression = expression.call.arguments[2]
            if type(default_expression) in {NameExpr, DottedNameExpr}:
                navigation_defaults = (default_expression,)

    relation_input = ProjectRowDependencyNode(
        kind=ProjectRowDependencyNodeKind.RELATION_INPUT,
        name=upstream_symbol.name,
        relation_name=upstream_symbol.name,
        source_name=upstream_symbol.name,
    )
    partition_fields = tuple(
        _window_input_dependency(
            expression=partition_expression,
            definition=definition,
            upstream_symbol=upstream_symbol,
            input_scope=input_scope,
        )
        for partition_expression in partition_expressions
    )
    order_fields = tuple(
        _window_input_dependency(
            expression=order_expression,
            definition=definition,
            upstream_symbol=upstream_symbol,
            input_scope=input_scope,
        )
        for order_expression in order_expressions
    )
    argument_fields = tuple(
        _window_input_dependency(
            expression=argument_expression,
            definition=definition,
            upstream_symbol=upstream_symbol,
            input_scope=input_scope,
        )
        for argument_expression in navigation_arguments
    )
    default_fields = tuple(
        _window_input_dependency(
            expression=default_expression,
            definition=definition,
            upstream_symbol=upstream_symbol,
            input_scope=input_scope,
        )
        for default_expression in navigation_defaults
    )

    role_inputs: tuple[
        tuple[
            WindowDependencyRole,
            tuple[
                tuple[
                    Expression,
                    ProjectRowDependencyNode,
                    ProjectRowResultRole | None,
                ],
                ...,
            ],
        ],
        ...,
    ] = (
        (
            WindowDependencyRole.RELATION_INPUT,
            ()
            if argument_fields or default_fields
            else ((expression.call, relation_input, None),),
        ),
        (
            WindowDependencyRole.WINDOW_ARGUMENT,
            tuple(
                (source, target, target_role)
                for source, (target, target_role) in zip(
                    navigation_arguments,
                    argument_fields,
                    strict=True,
                )
            ),
        ),
        (
            WindowDependencyRole.WINDOW_DEFAULT,
            tuple(
                (source, target, target_role)
                for source, (target, target_role) in zip(
                    navigation_defaults,
                    default_fields,
                    strict=True,
                )
            ),
        ),
        (
            WindowDependencyRole.WINDOW_PARTITION,
            tuple(
                (source, target, target_role)
                for source, (target, target_role) in zip(
                    partition_expressions,
                    partition_fields,
                    strict=True,
                )
            ),
        ),
        (
            WindowDependencyRole.WINDOW_ORDER,
            tuple(
                (source, target, target_role)
                for source, (target, target_role) in zip(
                    order_expressions,
                    order_fields,
                    strict=True,
                )
            ),
        ),
    )
    occurrences_list: list[WindowDependencyOccurrence] = []
    for role, inputs in role_inputs:
        for role_ordinal, (
            source_expression,
            target,
            target_result_role,
        ) in enumerate(inputs):
            occurrences_list.append(
                WindowDependencyOccurrence(
                    global_ordinal=len(occurrences_list),
                    role_ordinal=role_ordinal,
                    role=role,
                    target=target,
                    location=_source_location(source_expression.span),
                    target_result_role=target_result_role,
                )
            )
    occurrences = tuple(occurrences_list)
    return WindowResultProjectFact(
        semantic_fact=semantic_fact,
        result_identity=WindowResultIdentity(
            definition=definition,
            output_name=item.alias,
            occurrence=semantic_fact.occurrence,
        ),
        dependency_occurrences=occurrences,
        dependency_edges=deduplicate_window_dependency_edges(occurrences),
        provenance=ProjectRowFieldProvenance(
            kind=ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION,
            symbol=upstream_symbol,
            location=_source_location(expression.span),
        ),
    )


def _project_window_analysis_boundary(
    item: SelectItem,
    analysis: WindowExpressionAnalysis | WindowExpressionUnsupported,
) -> WindowExpressionAnalysis | WindowExpressionUnsupported:
    if isinstance(analysis, WindowExpressionUnsupported):
        return _retain_project_window_unsupported_authorship(item, analysis)
    deferred = _project_named_window_deferral(item, analysis.semantic_fact)
    return analysis if deferred is None else deferred


def _retain_project_window_unsupported_authorship(
    item: SelectItem,
    unsupported: WindowExpressionUnsupported,
) -> WindowExpressionUnsupported:
    expression = item.expression
    if type(expression) is not WindowExpr:
        raise TypeError("project window boundary requires an exact window item")
    if expression.use_kind is WindowUseKind.INLINE:
        return unsupported
    return replace(unsupported, expression=expression)


def _project_named_window_deferral(
    item: SelectItem,
    semantic_fact: WindowExpressionSemanticFact,
) -> WindowExpressionUnsupported | None:
    expression = item.expression
    if type(expression) is not WindowExpr:
        raise TypeError("project window boundary requires an exact window item")
    if expression.use_kind is WindowUseKind.INLINE:
        return None
    return WindowExpressionUnsupported(
        occurrence=semantic_fact.occurrence,
        expression=expression,
        identity=semantic_fact.identity,
        reason=_PROJECT_NAMED_WINDOW_INTEGRATION_DEFERRED,
    )


def _window_input_dependency(
    *,
    expression: Expression,
    definition: TableDef | QueryDef,
    upstream_symbol: ProjectSymbol,
    input_scope: WindowInputScope,
) -> tuple[ProjectRowDependencyNode, ProjectRowResultRole | None]:
    """Translate one validated transient origin to a project dependency."""

    binding = input_scope.resolve(
        expression,
        field_qualifier=definition.from_clause.source_name,
    )
    if binding is None:
        raise AssertionError("validated window input must have one transient origin")
    if binding.origin is WindowInputOriginKind.UPSTREAM_FIELD:
        node = ProjectRowDependencyNode(
            kind=ProjectRowDependencyNodeKind.UPSTREAM_FIELD,
            name=f"{upstream_symbol.name}.{binding.target_name}",
            relation_name=upstream_symbol.name,
            source_name=upstream_symbol.name,
            field_name=binding.target_name,
        )
        return node, None
    if binding.origin is WindowInputOriginKind.LET_BINDING:
        node = ProjectRowDependencyNode(
            kind=ProjectRowDependencyNodeKind.LET_BINDING,
            name=binding.target_name,
            relation_name=definition.name,
            binding_name=binding.target_name,
        )
        return node, None

    target_result_role = (
        ProjectRowResultRole.GROUP_KEY
        if binding.origin is WindowInputOriginKind.GROUP_KEY
        else ProjectRowResultRole.AGGREGATE_RESULT
    )
    node = ProjectRowDependencyNode(
        kind=ProjectRowDependencyNodeKind.OUTPUT_FIELD,
        name=binding.target_name,
        relation_name=definition.name,
        output_name=binding.target_name,
    )
    return node, target_result_role


def _source_location(span: Span) -> SourceLocation:
    if type(span) is not Span:
        raise TypeError("span must be an exact Span")
    return SourceLocation(
        path=span.path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )
