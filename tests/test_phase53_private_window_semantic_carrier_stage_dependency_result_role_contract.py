from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass
import inspect
from pathlib import Path
from typing import Any, cast


import pytest

import pietto._project as project_package
import pietto._project.window_semantics as project_window_semantics
import pietto.semantic.window_semantics as semantic_window_semantics
from pietto._project.model import (
    ProjectRowFieldProvenance,
    ProjectRowFieldProvenanceKind,
    ProjectRowResultRole,
)
from pietto._project.row_dependency_graph import (
    ProjectRowDependencyNode,
    ProjectRowDependencyNodeKind,
)
from pietto._project.window_semantics import (
    WindowDependencyEdge,
    WindowDependencyOccurrence,
    WindowDependencyRole,
    WindowResultIdentity,
    WindowResultProjectFact,
    WindowSemanticProvenance,
    deduplicate_window_dependency_edges,
)
from pietto._window_identity import WindowFunctionIdentity, WindowFunctionRole
from pietto.ast_nodes import (
    CallExpr,
    FromClause,
    NameExpr,
    QueryDef,
    Span,
    TableDef,
    WindowExpr,
    WindowSpec,
    WindowUseKind,
)
from pietto.errors import SourceLocation
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    TypeKind,
    ValueType,
    ValueTypeKind,
)
from pietto.semantic.window_semantics import (
    NavigationWindowSemanticFact,
    WindowComponentOrigin,
    WindowExpressionAnalysis,
    WindowExpressionSemanticFact,
    WindowExpressionStage,
    WindowExpressionUnsupported,
    WindowFrameApplicability,
    WindowOccurrenceIdentity,
    WindowResultAvailability,
    WindowResultAvailabilityKind,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = REPO_ROOT / "src/pietto/_project/model.py"
# Filled after the single write formatter; later edits are literal-only.
ANALYZER_CATALOG_DIAGNOSTIC_PATHS = (
    "src/pietto/semantic/analyzer.py",
    "src/pietto/semantic/catalog.py",
    "src/pietto/semantic/expressions.py",
)


def _span(
    *,
    path: str | None = "query.pietto",
    line: int = 3,
    column: int = 9,
    end_line: int = 3,
    end_column: int = 43,
) -> Span:
    return Span(
        path=path,
        line=line,
        column=column,
        end_line=end_line,
        end_column=end_column,
    )


def _identity(name: str = "row_number") -> WindowFunctionIdentity:
    return WindowFunctionIdentity(
        namespace=(),
        name=name,
        role=WindowFunctionRole.WINDOW_FUNCTION,
    )


def _window_expression(
    *,
    span: Span | None = None,
    identity: WindowFunctionIdentity | None = None,
    argument_count: int = 0,
) -> WindowExpr:
    expression_span = span or _span()
    function_identity = identity or _identity()
    callee = NameExpr(span=expression_span, name=function_identity.name)
    arguments = tuple(
        NameExpr(span=expression_span, name=f"arg_{index}")
        for index in range(argument_count)
    )
    call = CallExpr(
        span=expression_span,
        callee=callee,
        arguments=arguments,
    )
    partition = NameExpr(span=expression_span, name="account_id")
    spec = WindowSpec(
        span=expression_span,
        partition_by=(partition,),
        order_by=(),
    )
    return WindowExpr(
        span=expression_span,
        call=call,
        spec=spec,
        identity=function_identity,
    )


def _occurrence(
    *,
    source_id: str = "query.pietto",
    relation_name: str = "ranked",
    ordinal: int = 0,
    span: Span | None = None,
) -> WindowOccurrenceIdentity:
    return WindowOccurrenceIdentity(
        source_id=source_id,
        relation_name=relation_name,
        selected_output_ordinal=ordinal,
        span=span or _span(path=source_id),
    )


def _value_type(
    *,
    name: str = "Int",
    nullability: EffectiveNullability = EffectiveNullability.NON_NULL,
    kind: ValueTypeKind = ValueTypeKind.KNOWN,
) -> ValueType:
    return ValueType(
        resolved_type=ResolvedType(name=name, kind=TypeKind.BUILTIN),
        nullability=nullability,
        kind=kind,
    )


def _availability(
    *,
    nullability: EffectiveNullability = EffectiveNullability.NON_NULL,
) -> WindowResultAvailability:
    return WindowResultAvailability(
        kind=WindowResultAvailabilityKind.CONCRETE,
        value_type=_value_type(nullability=nullability),
    )


def _semantic_fact(
    *,
    occurrence: WindowOccurrenceIdentity | None = None,
    expression: WindowExpr | None = None,
    result: WindowResultAvailability | None = None,
    argument_count: int = 0,
) -> WindowExpressionSemanticFact:
    actual_occurrence = occurrence or _occurrence()
    actual_expression = expression or _window_expression(
        span=actual_occurrence.span,
        argument_count=argument_count,
    )
    return WindowExpressionSemanticFact(
        occurrence=actual_occurrence,
        expression=actual_expression,
        identity=actual_expression.identity,
        result=result or _availability(),
    )


def _definition(
    *,
    kind: str = "query",
    name: str = "ranked",
    span: Span | None = None,
) -> TableDef | QueryDef:
    definition_span = span or _span()
    values: dict[str, object] = {
        "span": definition_span,
        "name": name,
        "from_clause": FromClause(span=definition_span, source_name="rows"),
        "where_clause": None,
        "group_by_clause": None,
        "select_items": (),
    }
    if kind == "table":
        return TableDef(**cast(Any, values))
    return QueryDef(**cast(Any, values))


def _location(span: Span | None = None) -> SourceLocation:
    source_span = span or _span()
    return SourceLocation(
        path=source_span.path,
        line=source_span.line,
        column=source_span.column,
        end_line=source_span.end_line,
        end_column=source_span.end_column,
    )


def _node(kind: ProjectRowDependencyNodeKind) -> ProjectRowDependencyNode:
    if kind is ProjectRowDependencyNodeKind.RELATION_INPUT:
        return ProjectRowDependencyNode(
            kind=kind,
            name="rows",
            relation_name="rows",
            source_name="rows",
        )
    if kind is ProjectRowDependencyNodeKind.LET_BINDING:
        return ProjectRowDependencyNode(
            kind=kind,
            name="local_score",
            relation_name="ranked",
            binding_name="local_score",
        )
    if kind is ProjectRowDependencyNodeKind.OUTPUT_FIELD:
        return ProjectRowDependencyNode(
            kind=kind,
            name="ranked.rn",
            relation_name="ranked",
            output_name="rn",
        )
    return ProjectRowDependencyNode(
        kind=kind,
        name="rows.score",
        relation_name="rows",
        field_name="score",
    )


def _dependency(
    *,
    global_ordinal: int,
    role_ordinal: int,
    role: WindowDependencyRole,
    kind: ProjectRowDependencyNodeKind | None = None,
) -> WindowDependencyOccurrence:
    target_kind = kind
    if target_kind is None:
        target_kind = (
            ProjectRowDependencyNodeKind.RELATION_INPUT
            if role is WindowDependencyRole.RELATION_INPUT
            else ProjectRowDependencyNodeKind.UPSTREAM_FIELD
        )
    return WindowDependencyOccurrence(
        global_ordinal=global_ordinal,
        role_ordinal=role_ordinal,
        role=role,
        target=_node(target_kind),
        location=_location(),
    )


def _project_fact(
    *,
    argument_count: int,
    occurrences: tuple[WindowDependencyOccurrence, ...],
    provenance: ProjectRowFieldProvenance | None = None,
    semantic_fact: WindowExpressionSemanticFact | None = None,
) -> WindowResultProjectFact:
    fact = semantic_fact or _semantic_fact(argument_count=argument_count)
    analysis = object.__new__(WindowExpressionAnalysis)
    for name, value in (
        ("semantic_fact", fact),
        ("ranking_fact", None),
        ("distribution_fact", None),
        ("partition_binding_fact", None),
        ("order_binding_fact", None),
        ("validated_specification", None),
        ("navigation_fact", None),
        ("frame_value_fact", None),
        ("resolved_named_use", None),
    ):
        object.__setattr__(analysis, name, value)
    semantic_provenance = object.__new__(WindowSemanticProvenance)
    for name, value in (
        ("analysis", analysis),
        ("function_identity", fact.identity),
        ("use_kind", WindowUseKind.INLINE),
        ("named_target", None),
        ("partition_origin", WindowComponentOrigin.LOCALLY_AUTHORED),
        ("order_origin", WindowComponentOrigin.EFFECTIVE_DEFAULT),
        ("frame_origin", WindowComponentOrigin.NOT_APPLICABLE),
        ("frame_applicability", WindowFrameApplicability.NOT_APPLICABLE),
        ("frame_unit", None),
        ("frame_start", None),
        ("frame_end", None),
        ("frame_exclusion", None),
        ("null_treatment", None),
        ("null_treatment_is_explicit", False),
        ("nth_direction", None),
        ("nth_direction_is_explicit", False),
    ):
        object.__setattr__(semantic_provenance, name, value)
    result_identity = WindowResultIdentity(
        definition=_definition(name=fact.occurrence.relation_name),
        output_name="rn",
        occurrence=fact.occurrence,
    )
    return WindowResultProjectFact(
        semantic_fact=fact,
        analysis=analysis,
        semantic_provenance=semantic_provenance,
        result_identity=result_identity,
        dependency_occurrences=occurrences,
        dependency_edges=deduplicate_window_dependency_edges(occurrences),
        provenance=provenance
        or ProjectRowFieldProvenance(
            kind=ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION,
            location=_location(fact.occurrence.span),
        ),
    )


def test_semantic_private_module_enum_carrier_and_privacy_shapes_are_exact() -> None:
    assert semantic_window_semantics.__all__ == ()
    assert tuple(WindowExpressionStage) == (WindowExpressionStage.WINDOW,)
    assert WindowExpressionStage.WINDOW.value == "WINDOW"
    expected = {
        WindowOccurrenceIdentity: (
            "source_id",
            "relation_name",
            "selected_output_ordinal",
            "span",
        ),
        WindowResultAvailability: ("kind", "value_type", "reason"),
        WindowExpressionSemanticFact: (
            "occurrence",
            "expression",
            "identity",
            "result",
            "stage",
        ),
        WindowExpressionUnsupported: (
            "occurrence",
            "expression",
            "identity",
            "reason",
        ),
    }
    for carrier, names in expected.items():
        assert is_dataclass(carrier)
        assert hasattr(carrier, "__slots__")
        assert tuple(field.name for field in fields(carrier)) == names
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in inspect.signature(cast(Any, carrier)).parameters.values()
        )
    occurrence = _occurrence()
    with pytest.raises(FrozenInstanceError):
        setattr(occurrence, "relation_name", "other")


def test_project_private_module_enum_carrier_and_privacy_shapes_are_exact() -> None:
    assert project_window_semantics.__all__ == ()
    assert tuple((item.name, item.value) for item in WindowDependencyRole) == (
        ("RELATION_INPUT", "relation_input"),
        ("WINDOW_ARGUMENT", "window_argument"),
        ("WINDOW_DEFAULT", "window_default"),
        ("WINDOW_PARTITION", "window_partition"),
        ("WINDOW_ORDER", "window_order"),
    )
    expected = {
        WindowResultIdentity: ("definition", "output_name", "occurrence", "role"),
        WindowDependencyOccurrence: (
            "global_ordinal",
            "role_ordinal",
            "role",
            "target",
            "location",
            "target_result_role",
        ),
        WindowDependencyEdge: ("role", "target", "target_result_role"),
        WindowResultProjectFact: (
            "semantic_fact",
            "analysis",
            "semantic_provenance",
            "result_identity",
            "dependency_occurrences",
            "dependency_edges",
            "provenance",
        ),
        WindowSemanticProvenance: (
            "analysis",
            "function_identity",
            "use_kind",
            "named_target",
            "partition_origin",
            "order_origin",
            "frame_origin",
            "frame_applicability",
            "frame_unit",
            "frame_start",
            "frame_end",
            "frame_exclusion",
            "null_treatment",
            "null_treatment_is_explicit",
            "nth_direction",
            "nth_direction_is_explicit",
        ),
    }
    for carrier, names in expected.items():
        assert is_dataclass(carrier)
        assert hasattr(carrier, "__slots__")
        assert tuple(field.name for field in fields(carrier)) == names
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in inspect.signature(cast(Any, carrier)).parameters.values()
        )
    with pytest.raises(TypeError):
        deduplicate_window_dependency_edges(cast(Any, []))
    with pytest.raises(TypeError):
        deduplicate_window_dependency_edges(cast(Any, (object(),)))


@pytest.mark.parametrize(
    ("source_id", "relation_name", "ordinal", "span"),
    (
        ("query.pietto", "ranked", 0, _span()),
        ("query.pietto", "Ranked", 7, _span(line=10, end_line=12)),
        ("memory://unit", "r", 2, _span(path="memory://unit")),
        ("anonymous", "result", 99, _span(path=None)),
    ),
)
def test_window_occurrence_identity_valid_matrix_is_exact(
    source_id: str,
    relation_name: str,
    ordinal: int,
    span: Span,
) -> None:
    occurrence = WindowOccurrenceIdentity(
        source_id=source_id,
        relation_name=relation_name,
        selected_output_ordinal=ordinal,
        span=span,
    )
    assert (
        occurrence.source_id,
        occurrence.relation_name,
        occurrence.selected_output_ordinal,
        occurrence.span,
    ) == (source_id, relation_name, ordinal, span)


@pytest.mark.parametrize("different", (False, True))
def test_window_occurrence_identity_equality_hash_repr_and_repeatability_are_exact(
    different: bool,
) -> None:
    first = _occurrence(ordinal=1)
    second = _occurrence(ordinal=2 if different else 1)
    assert (first == second) is (not different)
    assert (hash(first) == hash(second)) is (not different)
    assert repr(_occurrence(ordinal=1)) == repr(first)


@pytest.mark.parametrize(
    "scenario",
    (
        "source_none",
        "source_int",
        "source_empty",
        "source_blank",
        "relation_none",
        "relation_int",
        "relation_empty",
        "relation_blank",
        "ordinal_bool",
        "ordinal_float",
        "ordinal_string",
        "ordinal_none",
        "ordinal_negative",
        "span_none",
        "span_object",
        "span_path_mismatch",
    ),
)
def test_window_occurrence_identity_malformed_matrix_fails_closed(
    scenario: str,
) -> None:
    values: dict[str, object] = {
        "source_id": "query.pietto",
        "relation_name": "ranked",
        "selected_output_ordinal": 0,
        "span": _span(),
    }
    replacements: dict[str, tuple[str, object]] = {
        "source_none": ("source_id", None),
        "source_int": ("source_id", 1),
        "source_empty": ("source_id", ""),
        "source_blank": ("source_id", "  "),
        "relation_none": ("relation_name", None),
        "relation_int": ("relation_name", 1),
        "relation_empty": ("relation_name", ""),
        "relation_blank": ("relation_name", "\t"),
        "ordinal_bool": ("selected_output_ordinal", True),
        "ordinal_float": ("selected_output_ordinal", 1.0),
        "ordinal_string": ("selected_output_ordinal", "1"),
        "ordinal_none": ("selected_output_ordinal", None),
        "ordinal_negative": ("selected_output_ordinal", -1),
        "span_none": ("span", None),
        "span_object": ("span", object()),
        "span_path_mismatch": ("span", _span(path="other.pietto")),
    }
    key, value = replacements[scenario]
    values[key] = value
    error = (
        ValueError
        if scenario
        in {
            "source_empty",
            "source_blank",
            "relation_empty",
            "relation_blank",
            "ordinal_negative",
            "span_path_mismatch",
        }
        else TypeError
    )
    with pytest.raises(error):
        WindowOccurrenceIdentity(**cast(Any, values))


@pytest.mark.parametrize(
    ("name", "nullability"),
    (
        ("Int", EffectiveNullability.NON_NULL),
        ("Text", EffectiveNullability.NULLABLE),
        ("Timestamp", EffectiveNullability.NON_NULL),
    ),
)
def test_concrete_window_result_availability_matrix_is_exact(
    name: str,
    nullability: EffectiveNullability,
) -> None:
    value_type = _value_type(name=name, nullability=nullability)
    result = WindowResultAvailability(
        kind=WindowResultAvailabilityKind.CONCRETE,
        value_type=value_type,
    )
    assert result.value_type is value_type
    assert result.reason is None


@pytest.mark.parametrize(
    "kind",
    (
        WindowResultAvailabilityKind.UNKNOWN,
        WindowResultAvailabilityKind.DEFERRED,
        WindowResultAvailabilityKind.BLOCKED,
    ),
)
def test_nonconcrete_window_result_availability_matrix_is_exact(
    kind: WindowResultAvailabilityKind,
) -> None:
    result = WindowResultAvailability(kind=kind, reason=f"private {kind.value}")
    assert result.kind is kind
    assert result.value_type is None
    assert result.reason == f"private {kind.value}"


@pytest.mark.parametrize(
    "scenario",
    (
        "kind_string",
        "concrete_missing_value",
        "concrete_unknown_kind",
        "concrete_unknown_nullability",
        "concrete_reason",
        "unknown_with_value",
        "deferred_with_value",
        "blocked_with_value",
        "unknown_missing_reason",
        "deferred_blank_reason",
        "value_wrong_type",
        "reason_wrong_type",
    ),
)
def test_window_result_availability_malformed_matrix_fails_closed(
    scenario: str,
) -> None:
    values: dict[str, object] = {
        "kind": WindowResultAvailabilityKind.CONCRETE,
        "value_type": _value_type(),
        "reason": None,
    }
    if scenario == "kind_string":
        values["kind"] = "concrete"
    elif scenario == "concrete_missing_value":
        values["value_type"] = None
    elif scenario == "concrete_unknown_kind":
        values["value_type"] = _value_type(kind=ValueTypeKind.UNKNOWN)
    elif scenario == "concrete_unknown_nullability":
        values["value_type"] = _value_type(nullability=EffectiveNullability.UNKNOWN)
    elif scenario == "concrete_reason":
        values["reason"] = "not allowed"
    elif scenario in {
        "unknown_with_value",
        "deferred_with_value",
        "blocked_with_value",
    }:
        values["kind"] = WindowResultAvailabilityKind(
            scenario.removesuffix("_with_value")
        )
        values["reason"] = "private"
    elif scenario == "unknown_missing_reason":
        values.update(kind=WindowResultAvailabilityKind.UNKNOWN, value_type=None)
    elif scenario == "deferred_blank_reason":
        values.update(
            kind=WindowResultAvailabilityKind.DEFERRED,
            value_type=None,
            reason=" ",
        )
    elif scenario == "value_wrong_type":
        values["value_type"] = object()
    elif scenario == "reason_wrong_type":
        values.update(
            kind=WindowResultAvailabilityKind.BLOCKED,
            value_type=None,
            reason=1,
        )
    error = (
        TypeError
        if scenario in {"kind_string", "value_wrong_type", "reason_wrong_type"}
        else ValueError
    )
    with pytest.raises(error):
        WindowResultAvailability(**cast(Any, values))


@pytest.mark.parametrize("deferred", (False, True))
def test_window_semantic_fact_has_fixed_stage_and_exact_identity(
    deferred: bool,
) -> None:
    occurrence = _occurrence()
    expression = _window_expression(span=occurrence.span)
    result = (
        WindowResultAvailability(
            kind=WindowResultAvailabilityKind.DEFERRED,
            reason="binding belongs to a future slice",
        )
        if deferred
        else _availability()
    )
    fact = WindowExpressionSemanticFact(
        occurrence=occurrence,
        expression=expression,
        identity=expression.identity,
        result=result,
    )
    assert fact.stage is WindowExpressionStage.WINDOW
    assert fact.identity == expression.identity
    assert fact.result is result


@pytest.mark.parametrize("reason", ("unknown function", "future binding"))
def test_window_semantic_unsupported_evidence_is_structural_only(
    reason: str,
) -> None:
    occurrence = _occurrence()
    expression = _window_expression(span=occurrence.span)
    unsupported = WindowExpressionUnsupported(
        occurrence=occurrence,
        expression=expression,
        identity=expression.identity,
        reason=reason,
    )
    assert unsupported.reason == reason
    assert not hasattr(unsupported, "diagnostic")
    assert not hasattr(unsupported, "result")


@pytest.mark.parametrize(
    "scenario",
    (
        "occurrence_type",
        "expression_type",
        "identity_type",
        "result_type",
        "stage_type",
        "identity_mismatch",
        "span_mismatch",
        "unsupported_blank_reason",
    ),
)
def test_window_semantic_fact_mismatch_matrix_fails_closed(scenario: str) -> None:
    occurrence = _occurrence()
    expression = _window_expression(span=occurrence.span)
    values: dict[str, object] = {
        "occurrence": occurrence,
        "expression": expression,
        "identity": expression.identity,
        "result": _availability(),
        "stage": WindowExpressionStage.WINDOW,
    }
    if scenario == "occurrence_type":
        values["occurrence"] = object()
    elif scenario == "expression_type":
        values["expression"] = expression.call
    elif scenario == "identity_type":
        values["identity"] = object()
    elif scenario == "result_type":
        values["result"] = object()
    elif scenario == "stage_type":
        values["stage"] = "WINDOW"
    elif scenario == "identity_mismatch":
        values["identity"] = _identity("rank")
    elif scenario == "span_mismatch":
        values["expression"] = _window_expression(span=_span(line=7))
    else:
        with pytest.raises(ValueError):
            WindowExpressionUnsupported(
                occurrence=occurrence,
                expression=expression,
                identity=expression.identity,
                reason=" ",
            )
        return
    error = (
        ValueError if scenario in {"identity_mismatch", "span_mismatch"} else TypeError
    )
    with pytest.raises(error):
        WindowExpressionSemanticFact(**cast(Any, values))


def test_window_carriers_do_not_store_generic_or_nullability_formula_evidence() -> None:
    assert tuple(field.name for field in fields(WindowExpressionSemanticFact)) == (
        "occurrence",
        "expression",
        "identity",
        "result",
        "stage",
    )
    assert tuple(field.name for field in fields(NavigationWindowSemanticFact))[-2:] == (
        "signature_match",
        "nullability_match",
    )
    base_source = inspect.getsource(WindowExpressionSemanticFact)
    assert "signature_match" not in base_source
    assert "nullability_match" not in base_source


@pytest.mark.parametrize("scenario", ("table", "blank_alias", "wrong_occurrence"))
def test_window_result_identity_requires_explicit_alias_and_occurrence(
    scenario: str,
) -> None:
    occurrence = _occurrence()
    if scenario == "table":
        identity = WindowResultIdentity(
            definition=_definition(kind="table"),
            output_name="rn",
            occurrence=occurrence,
        )
        assert type(identity.definition) is TableDef
        assert identity.output_name == "rn"
        assert identity.occurrence is occurrence
        assert identity.role is ProjectRowResultRole.WINDOW_RESULT
        return
    if scenario == "blank_alias":
        with pytest.raises(ValueError):
            WindowResultIdentity(
                definition=_definition(),
                output_name=" ",
                occurrence=occurrence,
            )
        return
    with pytest.raises(TypeError):
        WindowResultIdentity(
            definition=_definition(),
            output_name="rn",
            occurrence=cast(Any, object()),
        )


def test_project_row_result_role_window_result_extension_is_exact() -> None:
    assert tuple((role.name, role.value) for role in ProjectRowResultRole) == (
        ("ORDINARY_ROW_VALUE", "ordinary_row_value"),
        ("GROUP_KEY", "group_key"),
        ("AGGREGATE_RESULT", "aggregate_result"),
        ("WINDOW_RESULT", "window_result"),
    )
    assert MODEL_PATH.read_text().count('WINDOW_RESULT = "window_result"') == 1
    occurrence = _occurrence()
    with pytest.raises(ValueError):
        WindowResultIdentity(
            definition=_definition(),
            output_name="rn",
            occurrence=occurrence,
            role=ProjectRowResultRole.AGGREGATE_RESULT,
        )


def test_window_dependency_role_inventory_and_phase60_frame_absence_are_exact() -> None:
    assert tuple((role.name, role.value) for role in WindowDependencyRole) == (
        ("RELATION_INPUT", "relation_input"),
        ("WINDOW_ARGUMENT", "window_argument"),
        ("WINDOW_DEFAULT", "window_default"),
        ("WINDOW_PARTITION", "window_partition"),
        ("WINDOW_ORDER", "window_order"),
    )
    assert not hasattr(WindowDependencyRole, "WINDOW_FRAME")
    assert not hasattr(WindowDependencyRole, "RESULT_ROLE")


@pytest.mark.parametrize(
    ("role", "kind"),
    (
        (
            WindowDependencyRole.RELATION_INPUT,
            ProjectRowDependencyNodeKind.RELATION_INPUT,
        ),
        (
            WindowDependencyRole.WINDOW_ARGUMENT,
            ProjectRowDependencyNodeKind.UPSTREAM_FIELD,
        ),
        (
            WindowDependencyRole.WINDOW_ARGUMENT,
            ProjectRowDependencyNodeKind.LET_BINDING,
        ),
        (
            WindowDependencyRole.WINDOW_DEFAULT,
            ProjectRowDependencyNodeKind.UPSTREAM_FIELD,
        ),
        (
            WindowDependencyRole.WINDOW_PARTITION,
            ProjectRowDependencyNodeKind.UPSTREAM_FIELD,
        ),
        (
            WindowDependencyRole.WINDOW_PARTITION,
            ProjectRowDependencyNodeKind.LET_BINDING,
        ),
        (
            WindowDependencyRole.WINDOW_ORDER,
            ProjectRowDependencyNodeKind.UPSTREAM_FIELD,
        ),
        (
            WindowDependencyRole.WINDOW_ORDER,
            ProjectRowDependencyNodeKind.LET_BINDING,
        ),
    ),
)
def test_window_dependency_occurrence_positive_role_target_matrix_is_exact(
    role: WindowDependencyRole,
    kind: ProjectRowDependencyNodeKind,
) -> None:
    occurrence = _dependency(
        global_ordinal=0,
        role_ordinal=0,
        role=role,
        kind=kind,
    )
    edge = WindowDependencyEdge(role=role, target=occurrence.target)
    assert occurrence.role is role
    assert occurrence.target.kind is kind
    assert edge == deduplicate_window_dependency_edges((occurrence,))[0]


@pytest.mark.parametrize(
    "scenario",
    (
        "global_bool",
        "global_float",
        "global_negative",
        "role_bool",
        "role_float",
        "role_negative",
        "role_string",
        "target_object",
        "location_object",
        "relation_upstream",
        "relation_let",
        "argument_relation",
        "default_relation",
        "partition_relation",
        "order_relation",
        "argument_output",
    ),
)
def test_window_dependency_occurrence_role_payload_negative_matrix_fails_closed(
    scenario: str,
) -> None:
    values: dict[str, object] = {
        "global_ordinal": 0,
        "role_ordinal": 0,
        "role": WindowDependencyRole.WINDOW_ARGUMENT,
        "target": _node(ProjectRowDependencyNodeKind.UPSTREAM_FIELD),
        "location": _location(),
    }
    if scenario == "global_bool":
        values["global_ordinal"] = True
    elif scenario == "global_float":
        values["global_ordinal"] = 1.0
    elif scenario == "global_negative":
        values["global_ordinal"] = -1
    elif scenario == "role_bool":
        values["role_ordinal"] = True
    elif scenario == "role_float":
        values["role_ordinal"] = 1.0
    elif scenario == "role_negative":
        values["role_ordinal"] = -1
    elif scenario == "role_string":
        values["role"] = "window_argument"
    elif scenario == "target_object":
        values["target"] = object()
    elif scenario == "location_object":
        values["location"] = object()
    elif scenario == "relation_upstream":
        values.update(
            role=WindowDependencyRole.RELATION_INPUT,
            target=_node(ProjectRowDependencyNodeKind.UPSTREAM_FIELD),
        )
    elif scenario == "relation_let":
        values.update(
            role=WindowDependencyRole.RELATION_INPUT,
            target=_node(ProjectRowDependencyNodeKind.LET_BINDING),
        )
    elif scenario in {
        "argument_relation",
        "default_relation",
        "partition_relation",
        "order_relation",
    }:
        role_name = scenario.removesuffix("_relation")
        values.update(
            role={
                "argument": WindowDependencyRole.WINDOW_ARGUMENT,
                "default": WindowDependencyRole.WINDOW_DEFAULT,
                "partition": WindowDependencyRole.WINDOW_PARTITION,
                "order": WindowDependencyRole.WINDOW_ORDER,
            }[role_name],
            target=_node(ProjectRowDependencyNodeKind.RELATION_INPUT),
        )
    else:
        values["target"] = _node(ProjectRowDependencyNodeKind.OUTPUT_FIELD)
    error = (
        TypeError
        if scenario
        in {
            "global_bool",
            "global_float",
            "role_bool",
            "role_float",
            "role_string",
            "target_object",
            "location_object",
        }
        else ValueError
    )
    with pytest.raises(error):
        WindowDependencyOccurrence(**cast(Any, values))


@pytest.mark.parametrize(
    "scenario",
    (
        "valid",
        "global_starts_one",
        "global_gap",
        "role_starts_one",
        "role_duplicate",
        "role_block_reverse",
    ),
)
def test_window_dependency_global_and_role_local_ordering_matrix_is_exact(
    scenario: str,
) -> None:
    first = _dependency(
        global_ordinal=0,
        role_ordinal=0,
        role=WindowDependencyRole.WINDOW_ARGUMENT,
    )
    second = _dependency(
        global_ordinal=1,
        role_ordinal=0,
        role=WindowDependencyRole.WINDOW_PARTITION,
    )
    occurrences = (first, second)
    if scenario == "global_starts_one":
        occurrences = (
            _dependency(
                global_ordinal=1,
                role_ordinal=0,
                role=WindowDependencyRole.WINDOW_ARGUMENT,
            ),
        )
    elif scenario == "global_gap":
        occurrences = (
            first,
            _dependency(
                global_ordinal=2,
                role_ordinal=0,
                role=WindowDependencyRole.WINDOW_PARTITION,
            ),
        )
    elif scenario == "role_starts_one":
        occurrences = (
            _dependency(
                global_ordinal=0,
                role_ordinal=1,
                role=WindowDependencyRole.WINDOW_ARGUMENT,
            ),
        )
    elif scenario == "role_duplicate":
        occurrences = (
            first,
            _dependency(
                global_ordinal=1,
                role_ordinal=0,
                role=WindowDependencyRole.WINDOW_ARGUMENT,
            ),
        )
    elif scenario == "role_block_reverse":
        occurrences = (
            _dependency(
                global_ordinal=0,
                role_ordinal=0,
                role=WindowDependencyRole.WINDOW_ORDER,
            ),
            _dependency(
                global_ordinal=1,
                role_ordinal=0,
                role=WindowDependencyRole.WINDOW_PARTITION,
            ),
        )
    if scenario == "valid":
        fact = _project_fact(argument_count=1, occurrences=occurrences)
        assert fact.dependency_occurrences == occurrences
        return
    with pytest.raises(ValueError):
        _project_fact(argument_count=1, occurrences=occurrences)


@pytest.mark.parametrize("repeat_count", (1, 2, 3, 4, 5))
def test_repeated_dependency_occurrences_are_preserved_and_edges_first_deduped(
    repeat_count: int,
) -> None:
    target = _node(ProjectRowDependencyNodeKind.UPSTREAM_FIELD)
    occurrences = tuple(
        WindowDependencyOccurrence(
            global_ordinal=index,
            role_ordinal=index,
            role=WindowDependencyRole.WINDOW_ARGUMENT,
            target=target,
            location=_location(),
        )
        for index in range(repeat_count)
    )
    edges = deduplicate_window_dependency_edges(occurrences)
    assert len(occurrences) == repeat_count
    assert edges == (
        WindowDependencyEdge(
            role=WindowDependencyRole.WINDOW_ARGUMENT,
            target=target,
        ),
    )
    fact = _project_fact(argument_count=1, occurrences=occurrences)
    assert fact.dependency_edges == edges


@pytest.mark.parametrize(
    ("first_role", "second_role"),
    (
        (
            WindowDependencyRole.WINDOW_ARGUMENT,
            WindowDependencyRole.WINDOW_DEFAULT,
        ),
        (
            WindowDependencyRole.WINDOW_ARGUMENT,
            WindowDependencyRole.WINDOW_PARTITION,
        ),
        (
            WindowDependencyRole.WINDOW_PARTITION,
            WindowDependencyRole.WINDOW_ORDER,
        ),
    ),
)
def test_same_target_across_dependency_roles_remains_distinct(
    first_role: WindowDependencyRole,
    second_role: WindowDependencyRole,
) -> None:
    target = _node(ProjectRowDependencyNodeKind.UPSTREAM_FIELD)
    occurrences = (
        WindowDependencyOccurrence(
            global_ordinal=0,
            role_ordinal=0,
            role=first_role,
            target=target,
            location=_location(),
        ),
        WindowDependencyOccurrence(
            global_ordinal=1,
            role_ordinal=0,
            role=second_role,
            target=target,
            location=_location(),
        ),
    )
    edges = deduplicate_window_dependency_edges(occurrences)
    assert tuple(edge.role for edge in edges) == (first_role, second_role)
    assert edges[0].target == edges[1].target


@pytest.mark.parametrize(
    "scenario",
    ("relation_only", "relation_partition_order", "missing_relation", "two_relations"),
)
def test_zero_argument_relation_input_readiness_and_failure_matrix_is_exact(
    scenario: str,
) -> None:
    relation = _dependency(
        global_ordinal=0,
        role_ordinal=0,
        role=WindowDependencyRole.RELATION_INPUT,
    )
    occurrences: tuple[WindowDependencyOccurrence, ...] = (relation,)
    if scenario == "relation_partition_order":
        occurrences = (
            relation,
            _dependency(
                global_ordinal=1,
                role_ordinal=0,
                role=WindowDependencyRole.WINDOW_PARTITION,
            ),
            _dependency(
                global_ordinal=2,
                role_ordinal=0,
                role=WindowDependencyRole.WINDOW_ORDER,
            ),
        )
    elif scenario == "missing_relation":
        occurrences = ()
    elif scenario == "two_relations":
        occurrences = (
            relation,
            _dependency(
                global_ordinal=1,
                role_ordinal=1,
                role=WindowDependencyRole.RELATION_INPUT,
            ),
        )
    if scenario.startswith("relation_"):
        fact = _project_fact(argument_count=0, occurrences=occurrences)
        assert (
            sum(
                item.role is WindowDependencyRole.RELATION_INPUT
                for item in fact.dependency_occurrences
            )
            == 1
        )
        return
    with pytest.raises(ValueError):
        _project_fact(argument_count=0, occurrences=occurrences)


@pytest.mark.parametrize(
    "role",
    (
        WindowDependencyRole.WINDOW_ARGUMENT,
        WindowDependencyRole.WINDOW_DEFAULT,
        WindowDependencyRole.WINDOW_PARTITION,
        WindowDependencyRole.WINDOW_ORDER,
    ),
)
def test_same_select_and_nested_window_dependencies_are_nonrepresentable(
    role: WindowDependencyRole,
) -> None:
    with pytest.raises(ValueError):
        WindowDependencyOccurrence(
            global_ordinal=0,
            role_ordinal=0,
            role=role,
            target=_node(ProjectRowDependencyNodeKind.OUTPUT_FIELD),
            location=_location(),
        )
    with pytest.raises(ValueError):
        WindowDependencyEdge(
            role=role,
            target=_node(ProjectRowDependencyNodeKind.OUTPUT_FIELD),
        )


@pytest.mark.parametrize("argument_count", (0, 1, 3))
def test_window_result_uses_existing_derived_expression_provenance(
    argument_count: int,
) -> None:
    occurrences = (
        (
            _dependency(
                global_ordinal=0,
                role_ordinal=0,
                role=WindowDependencyRole.RELATION_INPUT,
            ),
        )
        if argument_count == 0
        else (
            _dependency(
                global_ordinal=0,
                role_ordinal=0,
                role=WindowDependencyRole.WINDOW_ARGUMENT,
            ),
        )
    )
    fact = _project_fact(argument_count=argument_count, occurrences=occurrences)
    assert fact.provenance.kind is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION
    assert fact.provenance.location == _location(fact.semantic_fact.occurrence.span)
    assert not hasattr(ProjectRowFieldProvenanceKind, "WINDOW_RESULT")


@pytest.mark.parametrize(
    "scenario",
    (
        "wrong_type",
        "wrong_kind",
        "missing_location",
        "wrong_path",
        "wrong_line",
        "wrong_symbol_type",
    ),
)
def test_window_result_provenance_mismatch_matrix_fails_closed(scenario: str) -> None:
    occurrence = _dependency(
        global_ordinal=0,
        role_ordinal=0,
        role=WindowDependencyRole.WINDOW_ARGUMENT,
    )
    if scenario == "wrong_type":
        with pytest.raises(TypeError):
            _project_fact(
                argument_count=1,
                occurrences=(occurrence,),
                provenance=cast(Any, object()),
            )
        return
    location = _location()
    kind = ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION
    symbol: object | None = None
    if scenario == "wrong_kind":
        kind = ProjectRowFieldProvenanceKind.AGGREGATE
    elif scenario == "missing_location":
        location = cast(Any, None)
    elif scenario == "wrong_path":
        location = SourceLocation(
            path="other.pietto", line=3, column=9, end_line=3, end_column=43
        )
    elif scenario == "wrong_line":
        location = SourceLocation(
            path="query.pietto", line=4, column=9, end_line=4, end_column=43
        )
    elif scenario == "wrong_symbol_type":
        symbol = object()
    provenance = ProjectRowFieldProvenance(
        kind=kind,
        symbol=cast(Any, symbol),
        location=location,
    )
    error = TypeError if scenario == "wrong_symbol_type" else ValueError
    with pytest.raises(error):
        _project_fact(
            argument_count=1,
            occurrences=(occurrence,),
            provenance=provenance,
        )


@pytest.mark.parametrize("argument_count", (0, 1))
def test_window_result_project_fact_is_frozen_hashable_and_repeatable(
    argument_count: int,
) -> None:
    occurrences = (
        (
            _dependency(
                global_ordinal=0,
                role_ordinal=0,
                role=WindowDependencyRole.RELATION_INPUT,
            ),
        )
        if argument_count == 0
        else (
            _dependency(
                global_ordinal=0,
                role_ordinal=0,
                role=WindowDependencyRole.WINDOW_ARGUMENT,
            ),
        )
    )
    first = _project_fact(argument_count=argument_count, occurrences=occurrences)
    second = _project_fact(argument_count=argument_count, occurrences=occurrences)
    assert first == second
    assert hash(first) == hash(second)
    assert repr(first) == repr(second)
    with pytest.raises(FrozenInstanceError):
        setattr(first, "dependency_edges", ())


@pytest.mark.parametrize(
    "scenario",
    ("ranking_concrete", "navigation_nullable", "slice12_unknown", "slice12_deferred"),
)
def test_slice7_and_slice12_construction_readiness_matrix_is_exact(
    scenario: str,
) -> None:
    zero_argument = scenario == "ranking_concrete"
    result = _availability(
        nullability=(
            EffectiveNullability.NULLABLE
            if scenario == "navigation_nullable"
            else EffectiveNullability.NON_NULL
        )
    )
    if scenario == "slice12_unknown":
        result = WindowResultAvailability(
            kind=WindowResultAvailabilityKind.UNKNOWN,
            reason="future generic binding unavailable",
        )
    elif scenario == "slice12_deferred":
        result = WindowResultAvailability(
            kind=WindowResultAvailabilityKind.DEFERRED,
            reason="future nullability evaluation unavailable",
        )
    semantic_fact = _semantic_fact(
        argument_count=0 if zero_argument else 1,
        result=result,
    )
    occurrences = (
        (
            _dependency(
                global_ordinal=0,
                role_ordinal=0,
                role=WindowDependencyRole.RELATION_INPUT,
            ),
        )
        if zero_argument
        else (
            _dependency(
                global_ordinal=0,
                role_ordinal=0,
                role=WindowDependencyRole.WINDOW_ARGUMENT,
            ),
        )
    )
    fact = _project_fact(
        argument_count=0 if zero_argument else 1,
        occurrences=occurrences,
        semantic_fact=semantic_fact,
    )
    assert fact.semantic_fact.result is result


@pytest.mark.parametrize(
    "relative",
    ANALYZER_CATALOG_DIAGNOSTIC_PATHS,
)
def test_current_analyzer_catalog_and_diagnostic_nonintegration_is_exact(
    relative: str,
) -> None:
    path = REPO_ROOT / relative
    source = path.read_text()
    if relative == "src/pietto/semantic/expressions.py":
        assert "semantic.window_semantics" in source
        assert "WindowExpressionAnalysis" in source
        assert "WindowResultAvailabilityKind" in source
        assert "analyze_window_expression(" in source
        window_analysis = (
            REPO_ROOT / "src/pietto/semantic/window_analysis.py"
        ).read_text()
        assert "def analyze_row_number_window_expression(" in window_analysis
        assert "WindowExpressionSemanticFact" in window_analysis
        assert "WindowExpressionUnsupported" in window_analysis
    elif relative == "src/pietto/semantic/analyzer.py":
        assert "if TYPE_CHECKING:" in source
        assert "semantic.window_semantics import (" in source
        assert "WindowExpressionAnalysis" in source
        assert "ResolvedNamedWindowNamespace" in source
        assert "WindowExpressionUnsupported" not in source
    else:
        assert "semantic.window_semantics" not in source
        assert "WindowExpressionSemanticFact" not in source
        assert "WindowExpressionUnsupported" not in source


@pytest.mark.parametrize(
    "relative",
    (
        "src/pietto/_project/model.py",
        "src/pietto/_project/check.py",
        "src/pietto/_project/json_v2.py",
        "src/pietto/_project/__init__.py",
    ),
)
def test_project_model_checker_and_serializers_have_no_window_population(
    relative: str,
) -> None:
    path = REPO_ROOT / relative
    source = path.read_text()
    if relative == "src/pietto/_project/model.py":
        assert "WindowResultProjectFact" in source
        assert "relation_window_result_facts" in source
        assert "_validate_project_window_result_facts(" in source
        assert "build_window_result_project_fact(" not in source
    else:
        assert "WindowResultProjectFact" not in source
        assert "relation_window_result_facts" not in source
        assert "window_semantics" not in source
    assert not hasattr(project_package, "WindowResultProjectFact")
