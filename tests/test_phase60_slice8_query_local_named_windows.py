from __future__ import annotations

import ast
from dataclasses import fields, replace
from pathlib import Path
from typing import cast

import pytest

import pietto.ir.model as ir_model
from pietto import _window_identity
from pietto.ast_nodes import (
    AuthoredWindowFrameExclusion,
    NameExpr,
    NamedWindowDeclaration,
    QueryDef,
    TableDef,
    WindowExpr,
    WindowFrameUnit,
    WindowUseKind,
)
from pietto.ir import build_ir
from pietto.ir.lowering import lower_expr
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.window_semantics import (
    ComposedNamedWindowUse,
    NamedWindowBaseResolution,
    NamedWindowComponentProvenance,
    NamedWindowComponentKind,
    NamedWindowResolutionFailure,
    NamedWindowResolutionIssueKind,
    NamedWindowUseResolutionFailure,
    ResolvedNamedWindowNamespace,
    ResolvedNamedWindowTemplate,
    ResolvedNamedWindowUse,
    WindowComponentOrigin,
    WindowFrameApplicability,
    WindowFunctionFramePolicy,
    WindowFunctionFramePolicyKind,
    compose_named_window_use,
    resolve_composed_named_window_use,
    resolve_named_window_namespace,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "docs/spec/phase60-slice8-query-local-named-windows-v1.md"
PREFIX = (
    "shape Row:\n"
    "    id: Int not null\n"
    "    account_id: Int not null\n"
    "    value: Int not null\n"
    'source rows: Row is postgres.table("rows")\n'
)

EXPECTED_PROVENANCE_ORIGIN_MATRIX = (
    (
        "template",
        NamedWindowComponentKind.PARTITION,
        (WindowComponentOrigin.LOCALLY_AUTHORED, WindowComponentOrigin.INHERITED),
    ),
    (
        "template",
        NamedWindowComponentKind.ORDER,
        (WindowComponentOrigin.LOCALLY_AUTHORED, WindowComponentOrigin.INHERITED),
    ),
    (
        "template",
        NamedWindowComponentKind.FRAME,
        (WindowComponentOrigin.LOCALLY_AUTHORED, WindowComponentOrigin.INHERITED),
    ),
    (
        "composed_use",
        NamedWindowComponentKind.PARTITION,
        (WindowComponentOrigin.LOCALLY_AUTHORED, WindowComponentOrigin.INHERITED),
    ),
    (
        "composed_use",
        NamedWindowComponentKind.ORDER,
        (WindowComponentOrigin.LOCALLY_AUTHORED, WindowComponentOrigin.INHERITED),
    ),
    (
        "composed_use",
        NamedWindowComponentKind.FRAME,
        (WindowComponentOrigin.LOCALLY_AUTHORED, WindowComponentOrigin.INHERITED),
    ),
    (
        "resolved_use",
        NamedWindowComponentKind.PARTITION,
        (
            WindowComponentOrigin.LOCALLY_AUTHORED,
            WindowComponentOrigin.INHERITED,
            WindowComponentOrigin.EFFECTIVE_DEFAULT,
        ),
    ),
    (
        "resolved_use",
        NamedWindowComponentKind.ORDER,
        (
            WindowComponentOrigin.LOCALLY_AUTHORED,
            WindowComponentOrigin.INHERITED,
            WindowComponentOrigin.EFFECTIVE_DEFAULT,
        ),
    ),
    (
        "resolved_use",
        NamedWindowComponentKind.FRAME,
        (
            WindowComponentOrigin.LOCALLY_AUTHORED,
            WindowComponentOrigin.INHERITED,
            WindowComponentOrigin.EFFECTIVE_DEFAULT,
            WindowComponentOrigin.NOT_APPLICABLE,
        ),
    ),
)

CROSS_SLOT_KIND_MATRIX = (
    (NamedWindowComponentKind.PARTITION, NamedWindowComponentKind.ORDER),
    (NamedWindowComponentKind.PARTITION, NamedWindowComponentKind.FRAME),
    (NamedWindowComponentKind.ORDER, NamedWindowComponentKind.PARTITION),
    (NamedWindowComponentKind.ORDER, NamedWindowComponentKind.FRAME),
    (NamedWindowComponentKind.FRAME, NamedWindowComponentKind.PARTITION),
    (NamedWindowComponentKind.FRAME, NamedWindowComponentKind.ORDER),
)


def _parse(source: str):
    parsed = parse_source(PREFIX + source, path="slice8.pietto")
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    return parsed.ast


def _query(script, name: str) -> QueryDef:
    return cast(
        QueryDef,
        next(
            definition
            for definition in script.definitions
            if isinstance(definition, QueryDef) and definition.name == name
        ),
    )


def _window(query: QueryDef, position: int = 0) -> WindowExpr:
    expression = query.select_items[position].expression
    assert type(expression) is WindowExpr
    return expression


def _namespace(query: TableDef | QueryDef) -> ResolvedNamedWindowNamespace:
    result = resolve_named_window_namespace(query)
    assert type(result) is ResolvedNamedWindowNamespace
    return result


def _resolution_names(namespace: ResolvedNamedWindowNamespace) -> tuple[str, ...]:
    return tuple(
        namespace.declarations[occurrence.declaration_position].name
        for occurrence in namespace.resolution_order
    )


def _resolve_use(
    composed: ComposedNamedWindowUse,
    applicability: WindowFrameApplicability,
) -> ResolvedNamedWindowUse:
    policy = WindowFunctionFramePolicy(
        identity=composed.expression.identity,
        kind=(
            WindowFunctionFramePolicyKind.FRAME_SENSITIVE
            if applicability is WindowFrameApplicability.APPLICABLE
            else WindowFunctionFramePolicyKind.FRAME_INSENSITIVE_EXPLICIT_FORBIDDEN
        ),
    )
    return resolve_composed_named_window_use(
        composed,
        function_identity=composed.expression.identity,
        function_policy=policy,
    )


def _adversarial_state() -> tuple[
    ResolvedNamedWindowNamespace,
    ResolvedNamedWindowNamespace,
    ResolvedNamedWindowTemplate,
    ResolvedNamedWindowTemplate,
    ResolvedNamedWindowTemplate,
    ResolvedNamedWindowTemplate,
    ComposedNamedWindowUse,
    ComposedNamedWindowUse,
    ComposedNamedWindowUse,
    ComposedNamedWindowUse,
]:
    script = _parse(
        "query binding:\n"
        "    from rows\n"
        "    select:\n"
        "        direct = row_number() window a\n"
        "        partitioned = row_number() window a:\n"
        "            partition by:\n"
        "                account_id\n"
        "        local_frame = row_number() window a:\n"
        "            rows current row\n"
        "        inherited_frame = row_number() window framed\n"
        "    window a:\n"
        "        order by:\n"
        "            id\n"
        "    window b:\n"
        "        order by:\n"
        "            id\n"
        "    window framed = a:\n"
        "        groups current row exclude ties\n"
        "query other:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "    window a:\n"
        "        order by:\n"
        "            id\n"
    )
    binding_query = _query(script, "binding")
    binding = _namespace(binding_query)
    other = _namespace(_query(script, "other"))
    a = binding.template_for_name("a")
    b = binding.template_for_name("b")
    framed = binding.template_for_name("framed")
    other_a = other.template_for_name("a")
    assert (
        a is not None and b is not None and framed is not None and other_a is not None
    )
    composed = tuple(
        compose_named_window_use(
            binding,
            _window(binding_query, position),
            selected_output_ordinal=position,
        )
        for position in range(4)
    )
    assert all(type(item) is ComposedNamedWindowUse for item in composed)
    direct, partitioned, local_frame, inherited_frame = cast(
        tuple[
            ComposedNamedWindowUse,
            ComposedNamedWindowUse,
            ComposedNamedWindowUse,
            ComposedNamedWindowUse,
        ],
        composed,
    )
    return (
        binding,
        other,
        a,
        b,
        framed,
        other_a,
        direct,
        partitioned,
        local_frame,
        inherited_frame,
    )


def _empty_resolved_use(
    applicability: WindowFrameApplicability,
) -> ResolvedNamedWindowUse:
    query = _query(
        _parse(
            "query empty_use:\n"
            "    from rows\n"
            "    select:\n"
            "        result = row_number() window root\n"
            "    window root\n"
        ),
        "empty_use",
    )
    namespace = _namespace(query)
    composed = compose_named_window_use(
        namespace,
        _window(query),
        selected_output_ordinal=0,
    )
    assert type(composed) is ComposedNamedWindowUse
    return _resolve_use(composed, applicability)


def _provenance_carrier_matrix() -> dict[
    tuple[str, NamedWindowComponentKind, WindowComponentOrigin],
    tuple[
        ResolvedNamedWindowTemplate | ComposedNamedWindowUse | ResolvedNamedWindowUse,
        str,
    ],
]:
    query = _query(
        _parse(
            "query provenance_matrix:\n"
            "    from rows\n"
            "    select:\n"
            "        inherited = row_number() window all\n"
            "        local_partition = row_number() window empty:\n"
            "            partition by:\n"
            "                account_id\n"
            "        local_order = row_number() window empty:\n"
            "            order by:\n"
            "                id\n"
            "        local_frame = row_number() window empty:\n"
            "            rows current row\n"
            "        defaults = row_number() window empty\n"
            "    window empty\n"
            "    window partitioned:\n"
            "        partition by:\n"
            "            account_id\n"
            "    window ordered = partitioned:\n"
            "        order by:\n"
            "            id\n"
            "    window all = ordered:\n"
            "        rows current row\n"
            "    window inherited_all = all\n"
        ),
        "provenance_matrix",
    )
    namespace = _namespace(query)
    partitioned = namespace.template_for_name("partitioned")
    ordered = namespace.template_for_name("ordered")
    all_components = namespace.template_for_name("all")
    inherited_all = namespace.template_for_name("inherited_all")
    assert all(
        type(item) is ResolvedNamedWindowTemplate
        for item in (partitioned, ordered, all_components, inherited_all)
    )
    partitioned, ordered, all_components, inherited_all = cast(
        tuple[
            ResolvedNamedWindowTemplate,
            ResolvedNamedWindowTemplate,
            ResolvedNamedWindowTemplate,
            ResolvedNamedWindowTemplate,
        ],
        (partitioned, ordered, all_components, inherited_all),
    )
    composed = tuple(
        compose_named_window_use(
            namespace,
            _window(query, position),
            selected_output_ordinal=position,
        )
        for position in range(5)
    )
    assert all(type(item) is ComposedNamedWindowUse for item in composed)
    inherited, local_partition, local_order, local_frame, defaults = cast(
        tuple[
            ComposedNamedWindowUse,
            ComposedNamedWindowUse,
            ComposedNamedWindowUse,
            ComposedNamedWindowUse,
            ComposedNamedWindowUse,
        ],
        composed,
    )
    resolved_inherited = _resolve_use(
        inherited,
        WindowFrameApplicability.APPLICABLE,
    )
    resolved_local_partition = _resolve_use(
        local_partition,
        WindowFrameApplicability.APPLICABLE,
    )
    resolved_local_order = _resolve_use(
        local_order,
        WindowFrameApplicability.APPLICABLE,
    )
    resolved_local_frame = _resolve_use(
        local_frame,
        WindowFrameApplicability.APPLICABLE,
    )
    resolved_defaults = _resolve_use(defaults, WindowFrameApplicability.APPLICABLE)
    resolved_not_applicable = _resolve_use(
        defaults,
        WindowFrameApplicability.NOT_APPLICABLE,
    )
    return {
        (
            "template",
            NamedWindowComponentKind.PARTITION,
            WindowComponentOrigin.LOCALLY_AUTHORED,
        ): (partitioned, "partition_provenance"),
        (
            "template",
            NamedWindowComponentKind.ORDER,
            WindowComponentOrigin.LOCALLY_AUTHORED,
        ): (ordered, "ordering_provenance"),
        (
            "template",
            NamedWindowComponentKind.FRAME,
            WindowComponentOrigin.LOCALLY_AUTHORED,
        ): (all_components, "frame_provenance"),
        (
            "template",
            NamedWindowComponentKind.PARTITION,
            WindowComponentOrigin.INHERITED,
        ): (ordered, "partition_provenance"),
        ("template", NamedWindowComponentKind.ORDER, WindowComponentOrigin.INHERITED): (
            all_components,
            "ordering_provenance",
        ),
        ("template", NamedWindowComponentKind.FRAME, WindowComponentOrigin.INHERITED): (
            inherited_all,
            "frame_provenance",
        ),
        (
            "composed_use",
            NamedWindowComponentKind.PARTITION,
            WindowComponentOrigin.LOCALLY_AUTHORED,
        ): (local_partition, "partition_provenance"),
        (
            "composed_use",
            NamedWindowComponentKind.ORDER,
            WindowComponentOrigin.LOCALLY_AUTHORED,
        ): (local_order, "ordering_provenance"),
        (
            "composed_use",
            NamedWindowComponentKind.FRAME,
            WindowComponentOrigin.LOCALLY_AUTHORED,
        ): (local_frame, "frame_provenance"),
        (
            "composed_use",
            NamedWindowComponentKind.PARTITION,
            WindowComponentOrigin.INHERITED,
        ): (inherited, "partition_provenance"),
        (
            "composed_use",
            NamedWindowComponentKind.ORDER,
            WindowComponentOrigin.INHERITED,
        ): (inherited, "ordering_provenance"),
        (
            "composed_use",
            NamedWindowComponentKind.FRAME,
            WindowComponentOrigin.INHERITED,
        ): (inherited, "frame_provenance"),
        (
            "resolved_use",
            NamedWindowComponentKind.PARTITION,
            WindowComponentOrigin.LOCALLY_AUTHORED,
        ): (resolved_local_partition, "partition_provenance"),
        (
            "resolved_use",
            NamedWindowComponentKind.ORDER,
            WindowComponentOrigin.LOCALLY_AUTHORED,
        ): (resolved_local_order, "ordering_provenance"),
        (
            "resolved_use",
            NamedWindowComponentKind.FRAME,
            WindowComponentOrigin.LOCALLY_AUTHORED,
        ): (resolved_local_frame, "frame_provenance"),
        (
            "resolved_use",
            NamedWindowComponentKind.PARTITION,
            WindowComponentOrigin.INHERITED,
        ): (resolved_inherited, "partition_provenance"),
        (
            "resolved_use",
            NamedWindowComponentKind.ORDER,
            WindowComponentOrigin.INHERITED,
        ): (resolved_inherited, "ordering_provenance"),
        (
            "resolved_use",
            NamedWindowComponentKind.FRAME,
            WindowComponentOrigin.INHERITED,
        ): (resolved_inherited, "frame_provenance"),
        (
            "resolved_use",
            NamedWindowComponentKind.PARTITION,
            WindowComponentOrigin.EFFECTIVE_DEFAULT,
        ): (resolved_defaults, "partition_provenance"),
        (
            "resolved_use",
            NamedWindowComponentKind.ORDER,
            WindowComponentOrigin.EFFECTIVE_DEFAULT,
        ): (resolved_defaults, "ordering_provenance"),
        (
            "resolved_use",
            NamedWindowComponentKind.FRAME,
            WindowComponentOrigin.EFFECTIVE_DEFAULT,
        ): (resolved_defaults, "frame_provenance"),
        (
            "resolved_use",
            NamedWindowComponentKind.FRAME,
            WindowComponentOrigin.NOT_APPLICABLE,
        ): (resolved_not_applicable, "frame_provenance"),
    }


def test_all_six_named_window_forms_parse_into_typed_authorship() -> None:
    parsed = parse_source(
        "shape Row:\n"
        "    id: Int not null\n"
        'source rows: Row is postgres.table("rows")\n'
        "query ranked:\n"
        "    from rows\n"
        "    select:\n"
        "        direct = row_number() window alias\n"
        "        extended = row_number() window recent:\n"
        "            partition by:\n"
        "                id\n"
        "    window whole\n"
        "    window recent:\n"
        "        order by:\n"
        "            id\n"
        "    window alias = recent\n"
        "    window rolling = recent:\n"
        "        partition by:\n"
        "            id\n",
        path="slice8.pietto",
    )
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    query = cast(QueryDef, parsed.ast.definitions[-1])
    assert tuple(type(item) for item in query.named_windows) == (
        NamedWindowDeclaration,
        NamedWindowDeclaration,
        NamedWindowDeclaration,
        NamedWindowDeclaration,
    )
    direct = cast(WindowExpr, query.select_items[0].expression)
    extended = cast(WindowExpr, query.select_items[1].expression)
    assert direct.use_kind is WindowUseKind.NAMED_DIRECT
    assert extended.use_kind is WindowUseKind.NAMED_EXTENDED
    whole, recent, alias, rolling = query.named_windows
    assert (whole.name, whole.base, whole.spec) == ("whole", None, None)
    assert recent.name == "recent" and recent.base is None
    assert recent.spec is not None and recent.spec.order_by
    assert alias.base is not None and alias.base.name == "recent"
    assert alias.spec is None
    assert rolling.base is not None and rolling.base.name == "recent"
    assert rolling.spec is not None and rolling.spec.partition_by
    assert direct.base is not None and direct.base.name == "alias"
    assert not direct.spec.has_components
    assert extended.base is not None and extended.base.name == "recent"
    assert extended.spec.has_components


def test_existing_inline_form_remains_distinct_and_zero_delta() -> None:
    script = _parse(
        "query ranked:\n"
        "    from rows\n"
        "    select:\n"
        "        result = row_number() window:\n"
        "            order by:\n"
        "                id\n"
    )
    query = _query(script, "ranked")
    expression = _window(query)
    assert expression.use_kind is WindowUseKind.INLINE
    assert expression.base is None
    semantic = analyze(script)
    assert semantic.diagnostics == ()
    lowered = build_ir(script, semantic.model)
    assert lowered.diagnostics == ()
    assert lowered.ir is not None


@pytest.mark.parametrize(
    "tail",
    (
        "    window empty:\n",
        "    window broken =\n",
        "    window multiple = first = second\n",
        "    order by:\n        id\n    window late\n",
    ),
)
def test_malformed_or_misplaced_named_declarations_remain_parser_negative(
    tail: str,
) -> None:
    result = parse_source(
        PREFIX + "query invalid:\n    from rows\n    select:\n        id\n" + tail
    )
    assert result.ast is None
    assert result.diagnostics


@pytest.mark.parametrize(
    "source",
    (
        "query q:\n    from rows\n    select:\n        result = row_number() over (id)\n",
        "query outer:\n    from rows\n    select:\n        query inner:\n            from rows\n            select:\n                id\n",
    ),
)
def test_sql_over_and_nested_query_syntax_remain_negative(source: str) -> None:
    result = parse_source(PREFIX + source)
    assert result.ast is None
    assert result.diagnostics


def test_collection_first_namespace_resolves_forward_backward_aliases_and_roots() -> (
    None
):
    query = _query(
        _parse(
            "query resolved:\n"
            "    from rows\n"
            "    select:\n"
            "        first = row_number() window alias\n"
            "        second = row_number() window backward\n"
            "    window alias = recent\n"
            "    window recent:\n"
            "        order by:\n"
            "            id\n"
            "    window backward = recent\n"
            "    window whole\n"
            "    window empty_alias = whole\n"
        ),
        "resolved",
    )
    namespace = _namespace(query)
    assert tuple(item.name for item in namespace.declarations) == (
        "alias",
        "recent",
        "backward",
        "whole",
        "empty_alias",
    )
    assert _resolution_names(namespace) == (
        "recent",
        "alias",
        "backward",
        "whole",
        "empty_alias",
    )
    whole = namespace.template_for_name("whole")
    empty_alias = namespace.template_for_name("empty_alias")
    alias = namespace.template_for_name("alias")
    assert whole is not None and whole.component_kinds == frozenset()
    assert empty_alias is not None and empty_alias.component_kinds == frozenset()
    assert empty_alias.base is not None
    assert empty_alias.base.target is whole.occurrence
    assert empty_alias.occurrence != whole.occurrence
    assert alias is not None and alias.order_by
    assert alias.occurrence != whole.occurrence


def test_declaration_order_does_not_change_acyclic_resolved_components() -> None:
    script = _parse(
        "query forward:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "    window derived = base:\n"
        "        partition by:\n"
        "            account_id\n"
        "    window base:\n"
        "        order by:\n"
        "            id desc\n"
        "query backward:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "    window base:\n"
        "        order by:\n"
        "            id desc\n"
        "    window derived = base:\n"
        "        partition by:\n"
        "            account_id\n"
    )
    first = _namespace(_query(script, "forward")).template_for_name("derived")
    second = _namespace(_query(script, "backward")).template_for_name("derived")
    assert first is not None and second is not None
    assert (
        tuple(cast(NameExpr, item).name for item in first.partition_by)
        == tuple(cast(NameExpr, item).name for item in second.partition_by)
        == ("account_id",)
    )
    assert (
        tuple(item.direction for item in first.order_by)
        == tuple(item.direction for item in second.order_by)
        == ("desc",)
    )


def test_duplicate_declarations_retain_every_occurrence_and_publish_no_namespace() -> (
    None
):
    script = _parse(
        "query duplicate:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "    window repeated\n"
        "    window repeated:\n"
        "        order by:\n"
        "            id\n"
    )
    query = _query(script, "duplicate")
    result = resolve_named_window_namespace(query)
    assert type(result) is NamedWindowResolutionFailure
    assert tuple(issue.kind for issue in result.issues) == (
        NamedWindowResolutionIssueKind.DUPLICATE_NAME,
    )
    assert len(result.issues[0].occurrences) == 2
    assert [item.code for item in analyze(script).diagnostics] == ["PIE-S2110"]


def test_declaration_and_use_dangling_references_fail_without_cross_block_capture() -> (
    None
):
    declaration_script = _parse(
        "query dangling:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "    window child = missing\n"
    )
    declaration = resolve_named_window_namespace(_query(declaration_script, "dangling"))
    assert type(declaration) is NamedWindowResolutionFailure
    assert declaration.issues[0].kind is (
        NamedWindowResolutionIssueKind.DANGLING_REFERENCE
    )
    assert [item.code for item in analyze(declaration_script).diagnostics] == [
        "PIE-S2111"
    ]

    script = _parse(
        "query outer:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "    window shared:\n"
        "        order by:\n"
        "            id\n"
        "query inner:\n"
        "    from outer\n"
        "    select:\n"
        "        result = row_number() window shared\n"
    )
    outer = _namespace(_query(script, "outer"))
    inner = _namespace(_query(script, "inner"))
    assert outer.query_block != inner.query_block
    failure = compose_named_window_use(
        inner, _window(_query(script, "inner")), selected_output_ordinal=0
    )
    assert type(failure) is NamedWindowUseResolutionFailure
    assert failure.issues[0].kind is NamedWindowResolutionIssueKind.DANGLING_REFERENCE
    assert [item.code for item in analyze(script).diagnostics] == ["PIE-S2111"]


def test_same_spelling_in_distinct_query_blocks_is_legal_and_identity_distinct() -> (
    None
):
    script = _parse(
        "query first:\n"
        "    from rows\n"
        "    select:\n"
        "        result = row_number() window shared\n"
        "    window shared:\n"
        "        order by:\n"
        "            id\n"
        "query second:\n"
        "    from rows\n"
        "    select:\n"
        "        result = row_number() window shared\n"
        "    window shared:\n"
        "        order by:\n"
        "            id\n"
    )
    first = _namespace(_query(script, "first")).template_for_name("shared")
    second = _namespace(_query(script, "second")).template_for_name("shared")
    assert first is not None and second is not None
    assert first.occurrence != second.occurrence
    assert first.occurrence.query_block != second.occurrence.query_block
    assert analyze(script).diagnostics == ()


def test_table_and_query_blocks_with_same_window_spelling_are_distinct() -> None:
    script = _parse(
        "table table_block:\n"
        "    from rows\n"
        "    select:\n"
        "        result = row_number() window shared\n"
        "    window shared:\n"
        "        order by:\n"
        "            id\n"
        "query query_block:\n"
        "    from rows\n"
        "    select:\n"
        "        result = row_number() window shared\n"
        "    window shared:\n"
        "        order by:\n"
        "            id\n"
    )
    table = cast(
        TableDef,
        next(item for item in script.definitions if isinstance(item, TableDef)),
    )
    query = _query(script, "query_block")
    table_template = _namespace(table).template_for_name("shared")
    query_template = _namespace(query).template_for_name("shared")
    assert table_template is not None and query_template is not None
    assert table_template.occurrence != query_template.occurrence
    assert analyze(script).diagnostics == ()


@pytest.mark.parametrize(
    ("declarations", "witness"),
    (
        (("window a = a",), "a -> a"),
        (("window a = b", "window b = a"), "a -> b -> a"),
        (
            ("window a = b", "window b = c", "window c = a"),
            "a -> b -> c -> a",
        ),
    ),
)
def test_self_two_node_and_long_cycles_reject_with_canonical_witness(
    declarations: tuple[str, ...],
    witness: str,
) -> None:
    declaration_source = "".join(f"    {item}\n" for item in declarations)
    script = _parse(
        "query cyclic:\n    from rows\n    select:\n        id\n" + declaration_source
    )
    result = resolve_named_window_namespace(_query(script, "cyclic"))
    assert type(result) is NamedWindowResolutionFailure
    assert tuple(issue.kind for issue in result.issues) == (
        NamedWindowResolutionIssueKind.CYCLE,
    )
    assert result.issues[0].name == witness
    assert [item.code for item in analyze(script).diagnostics] == ["PIE-S2112"]


@pytest.mark.parametrize(
    ("base_body", "child_body", "component"),
    (
        (
            "        partition by:\n            id\n",
            "        partition by:\n            account_id\n",
            NamedWindowComponentKind.PARTITION,
        ),
        (
            "        order by:\n            id\n",
            "        order by:\n            account_id\n",
            NamedWindowComponentKind.ORDER,
        ),
        (
            "        rows current row\n",
            "        range current row\n",
            NamedWindowComponentKind.FRAME,
        ),
    ),
)
def test_declaration_component_repetition_rejects_without_override(
    base_body: str,
    child_body: str,
    component: NamedWindowComponentKind,
) -> None:
    script = _parse(
        "query conflict:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "    window base:\n" + base_body + "    window child = base:\n" + child_body
    )
    result = resolve_named_window_namespace(_query(script, "conflict"))
    assert type(result) is NamedWindowResolutionFailure
    assert result.issues[0].kind is NamedWindowResolutionIssueKind.COMPONENT_CONFLICT
    assert result.issues[0].component is component
    assert [item.code for item in analyze(script).diagnostics] == ["PIE-S2113"]


def test_extended_use_component_repetition_precedes_function_policy() -> None:
    script = _parse(
        "query conflict:\n"
        "    from rows\n"
        "    select:\n"
        "        result = row_number() window base:\n"
        "            order by:\n"
        "                account_id\n"
        "    window base:\n"
        "        order by:\n"
        "            id\n"
    )
    assert [item.code for item in analyze(script).diagnostics] == ["PIE-S2113"]


def test_defaults_follow_template_and_use_composition_without_false_conflicts() -> None:
    query = _query(
        _parse(
            "query defaults:\n"
            "    from rows\n"
            "    select:\n"
            "        result = row_number() window filled\n"
            "    window root\n"
            "    window filled = root:\n"
            "        partition by:\n"
            "            account_id\n"
            "        order by:\n"
            "            id\n"
            "        rows current row exclude current row\n"
        ),
        "defaults",
    )
    namespace = _namespace(query)
    root = namespace.template_for_name("root")
    filled = namespace.template_for_name("filled")
    assert root is not None and root.component_kinds == frozenset()
    assert filled is not None and filled.component_kinds == frozenset(
        NamedWindowComponentKind
    )
    composed = compose_named_window_use(
        namespace,
        _window(query),
        selected_output_ordinal=0,
    )
    assert type(composed) is ComposedNamedWindowUse
    resolved = _resolve_use(composed, WindowFrameApplicability.APPLICABLE)
    assert resolved.resolved.frame.origin is WindowComponentOrigin.INHERITED
    assert resolved.frame_provenance.origin is WindowComponentOrigin.INHERITED


def test_one_template_resolves_under_distinct_policies_without_mutation() -> None:
    query = _query(
        _parse(
            "query policies:\n"
            "    from rows\n"
            "    select:\n"
            "        result = row_number() window ordered\n"
            "    window ordered:\n"
            "        order by:\n"
            "            id\n"
        ),
        "policies",
    )
    namespace = _namespace(query)
    template = namespace.template_for_name("ordered")
    assert template is not None and template.frame is None
    composed = compose_named_window_use(
        namespace,
        _window(query),
        selected_output_ordinal=0,
    )
    assert type(composed) is ComposedNamedWindowUse
    absent = _resolve_use(composed, WindowFrameApplicability.NOT_APPLICABLE)
    defaulted = _resolve_use(composed, WindowFrameApplicability.APPLICABLE)
    assert absent.resolved.frame.origin is WindowComponentOrigin.NOT_APPLICABLE
    assert defaulted.resolved.frame.origin is WindowComponentOrigin.EFFECTIVE_DEFAULT
    assert defaulted.resolved.ordering_origin is WindowComponentOrigin.INHERITED
    assert template.frame is None


def test_direct_provenance_reconstructs_multi_hop_component_chain() -> None:
    query = _query(
        _parse(
            "query provenance:\n"
            "    from rows\n"
            "    select:\n"
            "        result = row_number() window c\n"
            "    window a:\n"
            "        order by:\n"
            "            id\n"
            "    window b = a:\n"
            "        partition by:\n"
            "            account_id\n"
            "    window c = b:\n"
            "        rows current row\n"
        ),
        "provenance",
    )
    namespace = _namespace(query)
    a = namespace.template_for_name("a")
    b = namespace.template_for_name("b")
    c = namespace.template_for_name("c")
    assert a is not None and b is not None and c is not None
    assert b.ordering_provenance is not None
    assert b.ordering_provenance.source is a.occurrence
    assert c.ordering_provenance is not None
    assert c.ordering_provenance.source is b.occurrence
    composed = compose_named_window_use(
        namespace,
        _window(query),
        selected_output_ordinal=0,
    )
    assert type(composed) is ComposedNamedWindowUse
    assert composed.partition_provenance is not None
    assert composed.partition_provenance.source is c.occurrence
    assert composed.ordering_provenance is not None
    assert composed.ordering_provenance.source is c.occurrence
    assert composed.frame_provenance is not None
    assert composed.frame_provenance.source is c.occurrence
    with pytest.raises(ValueError, match="place every base first"):
        replace(namespace, resolution_order=tuple(reversed(namespace.resolution_order)))
    with pytest.raises(ValueError, match="components must match exact composition"):
        replace(composed, order_by=())
    resolved = _resolve_use(composed, WindowFrameApplicability.APPLICABLE)
    with pytest.raises(ValueError, match="ordering provenance must survive"):
        replace(resolved, ordering_provenance=resolved.partition_provenance)


def test_direct_and_extended_uses_remain_distinct_when_effective_frames_match() -> None:
    query = _query(
        _parse(
            "query uses:\n"
            "    from rows\n"
            "    select:\n"
            "        direct = row_number() window base\n"
            "        extended = row_number() window base:\n"
            "            range between unbounded preceding and current row exclude no others\n"
            "    window base:\n"
            "        order by:\n"
            "            id\n"
        ),
        "uses",
    )
    namespace = _namespace(query)
    direct = compose_named_window_use(
        namespace,
        _window(query, 0),
        selected_output_ordinal=0,
    )
    extended = compose_named_window_use(
        namespace,
        _window(query, 1),
        selected_output_ordinal=1,
    )
    assert type(direct) is ComposedNamedWindowUse
    assert type(extended) is ComposedNamedWindowUse
    assert direct.occurrence != extended.occurrence
    assert direct.occurrence.kind is WindowUseKind.NAMED_DIRECT
    assert extended.occurrence.kind is WindowUseKind.NAMED_EXTENDED
    direct_resolved = _resolve_use(direct, WindowFrameApplicability.APPLICABLE)
    extended_resolved = _resolve_use(
        extended,
        WindowFrameApplicability.APPLICABLE,
    )
    first = direct_resolved.resolved.frame
    second = extended_resolved.resolved.frame
    assert (first.unit, first.start, first.end, first.exclusion) == (
        second.unit,
        second.start,
        second.end,
        second.exclusion,
    )
    assert direct_resolved.frame_provenance.origin is (
        WindowComponentOrigin.EFFECTIVE_DEFAULT
    )
    assert extended_resolved.frame_provenance.origin is (
        WindowComponentOrigin.LOCALLY_AUTHORED
    )


def test_inherited_explicit_frame_reaches_existing_function_policy() -> None:
    script = _parse(
        "query framed:\n"
        "    from rows\n"
        "    select:\n"
        "        result = row_number() window framed_window\n"
        "    window framed_window:\n"
        "        order by:\n"
        "            id\n"
        "        groups current row exclude ties\n"
    )
    diagnostics = analyze(script).diagnostics
    assert [(item.code, item.message) for item in diagnostics] == [
        (
            "PIE-S2104",
            "Invalid window frame for function row_number: explicit GROUPS frame is not allowed",
        )
    ]
    query = _query(script, "framed")
    namespace = _namespace(query)
    template = namespace.template_for_name("framed_window")
    assert template is not None and template.frame is not None
    assert template.frame.unit is WindowFrameUnit.GROUPS
    assert template.frame.exclusion is AuthoredWindowFrameExclusion.TIES
    composed = compose_named_window_use(
        namespace,
        _window(query),
        selected_output_ordinal=0,
    )
    assert type(composed) is ComposedNamedWindowUse
    resolved = _resolve_use(composed, WindowFrameApplicability.APPLICABLE)
    assert resolved.resolved.frame.authored is template.frame
    assert resolved.resolved.frame.origin is WindowComponentOrigin.INHERITED


def test_named_resolution_failure_precedes_inherited_frame_policy() -> None:
    script = _parse(
        "query duplicate:\n"
        "    from rows\n"
        "    select:\n"
        "        result = row_number() window framed\n"
        "    window framed:\n"
        "        order by:\n"
        "            id\n"
        "        rows current row\n"
        "    window framed\n"
    )
    assert [item.code for item in analyze(script).diagnostics] == ["PIE-S2110"]


def test_legal_named_source_reaches_semantics_but_fails_closed_before_ir() -> None:
    script = _parse(
        "query legal:\n"
        "    from rows\n"
        "    select:\n"
        "        result = row_number() window ordered\n"
        "    window ordered:\n"
        "        order by:\n"
        "            id\n"
    )
    query = _query(script, "legal")
    expression = _window(query)
    semantic = analyze(script)
    assert semantic.diagnostics == ()
    assert expression in semantic.model.expression_value_types
    lowered_expression = lower_expr(expression, semantic.model)
    assert lowered_expression.expression is None
    assert "named window lowering authority" in (
        lowered_expression.diagnostics[0].message
    )
    lowered = build_ir(script, semantic.model)
    assert lowered.ir is None
    assert [item.code for item in lowered.diagnostics] == ["PIE-I1000"]


def test_named_window_ir_sql_capability_and_phase59_boundaries_stay_absent() -> None:
    assert tuple(field.name for field in fields(ir_model.WindowSpecIR)) == (
        "partition_by",
        "order_by",
        "span",
        "frame",
    )
    assert tuple(field.name for field in fields(ir_model.RelationIR)) == (
        "symbol",
        "name",
        "kind",
        "source",
        "filter",
        "projections",
        "row_schema",
        "span",
        "order_by",
        "limit",
        "group_keys",
        "result_predicate",
    )
    assert not hasattr(ir_model, "NamedWindowIR")
    for relative in (
        "src/pietto/sql/expressions.py",
        "src/pietto/sql/mysql_expressions.py",
        "src/pietto/sql/relations.py",
        "src/pietto/sql/mysql_relations.py",
    ):
        tree = ast.parse((REPO_ROOT / relative).read_text(encoding="utf-8"))
        names = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef))
        }
        assert not any("named_window" in name for name in names)


def test_reference_spelling_cannot_target_another_declaration() -> None:
    _namespace_value, _other, _a, b, _framed, _other_a, direct, *_rest = (
        _adversarial_state()
    )
    with pytest.raises(ValueError, match="spelling must match"):
        NamedWindowBaseResolution(
            owner=direct.occurrence,
            reference=direct.base.reference,
            target_declaration=b.declaration,
            target=b.occurrence,
        )


def test_same_spelling_in_another_query_block_cannot_cross_bind() -> None:
    _namespace_value, _other, _a, _b, _framed, other_a, direct, *_rest = (
        _adversarial_state()
    )
    with pytest.raises(ValueError, match="owners must match"):
        NamedWindowBaseResolution(
            owner=direct.occurrence,
            reference=direct.base.reference,
            target_declaration=other_a.declaration,
            target=other_a.occurrence,
        )


def test_reference_owner_and_target_owner_mismatch_rejects() -> None:
    _namespace_value, other, a, _b, _framed, _other_a, direct, *_rest = (
        _adversarial_state()
    )
    foreign_owner = replace(direct.occurrence, query_block=other.query_block)
    with pytest.raises(ValueError, match="owners must match"):
        NamedWindowBaseResolution(
            owner=foreign_owner,
            reference=direct.base.reference,
            target_declaration=a.declaration,
            target=a.occurrence,
        )


def test_use_occurrence_and_target_template_mismatch_rejects() -> None:
    _namespace_value, _other, _a, b, _framed, _other_a, direct, *_rest = (
        _adversarial_state()
    )
    with pytest.raises(ValueError, match="base evidence must be exact"):
        replace(direct, target_template=b)


def test_semantically_equivalent_declaration_cannot_substitute_for_bound_target() -> (
    None
):
    _namespace_value, _other, _a, b, _framed, _other_a, direct, *_rest = (
        _adversarial_state()
    )
    assert tuple(
        (cast(NameExpr, item.expression).name, item.direction)
        for item in direct.target_template.order_by
    ) == tuple(
        (cast(NameExpr, item.expression).name, item.direction) for item in b.order_by
    )
    reference_to_b = replace(direct.base.reference, name="b")
    valid_b_binding = NamedWindowBaseResolution(
        owner=direct.occurrence,
        reference=reference_to_b,
        target_declaration=b.declaration,
        target=b.occurrence,
    )
    with pytest.raises(ValueError, match="base evidence must be exact"):
        replace(
            direct,
            base=valid_b_binding,
            target_template=b,
        )


def test_occurrence_source_and_use_kind_must_be_exact() -> None:
    namespace, *_prefix, direct, _partitioned, _local_frame, _inherited_frame = (
        _adversarial_state()
    )
    with pytest.raises(ValueError, match="span path or relation name"):
        replace(
            namespace.query_block,
            source_id="forged",
            span=replace(namespace.query_block.span, path=None),
        )
    with pytest.raises(TypeError, match="window-use kind must be exact"):
        replace(direct.occurrence, kind=direct.occurrence.kind.value)


@pytest.mark.parametrize("path", (None, "other.pietto"))
def test_file_backed_owner_rejects_missing_or_foreign_child_paths(
    path: str | None,
) -> None:
    _namespace_value, _other, a, _b, _framed, _other_a, direct, *_rest = (
        _adversarial_state()
    )
    with pytest.raises(ValueError, match="span path must match"):
        replace(a.occurrence, span=replace(a.occurrence.span, path=path))
    with pytest.raises(ValueError, match="span path must match"):
        replace(
            direct.occurrence,
            span=replace(direct.occurrence.span, path=path),
        )
    assert direct.ordering_provenance is not None
    assert direct.ordering_provenance.source is not None
    with pytest.raises(ValueError, match="span path must match"):
        replace(
            direct.ordering_provenance.source,
            span=replace(direct.ordering_provenance.source.span, path=path),
        )
    reference = replace(
        direct.base.reference,
        span=replace(direct.base.reference.span, path=path),
    )
    with pytest.raises(ValueError, match="belong to its owner block"):
        replace(direct.base, reference=reference)


def test_in_memory_owner_accepts_exact_children_but_rejects_another_block() -> None:
    parsed = parse_source(
        PREFIX + "query first:\n"
        "    from rows\n"
        "    select:\n"
        "        result = row_number() window shared\n"
        "    window shared:\n"
        "        order by:\n"
        "            id\n"
        "query second:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "    window shared:\n"
        "        order by:\n"
        "            id\n"
    )
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    first_query = _query(parsed.ast, "first")
    first_namespace = _namespace(first_query)
    first_use = compose_named_window_use(
        first_namespace,
        _window(first_query),
        selected_output_ordinal=0,
    )
    assert type(first_use) is ComposedNamedWindowUse
    assert first_use.occurrence.query_block.span.path is None
    assert first_use.occurrence.span.path is None
    assert first_use.base.reference.span.path is None

    other = _namespace(_query(parsed.ast, "second")).template_for_name("shared")
    assert other is not None
    with pytest.raises(ValueError, match="owners must match"):
        NamedWindowBaseResolution(
            owner=first_use.occurrence,
            reference=first_use.base.reference,
            target_declaration=other.declaration,
            target=other.occurrence,
        )


def test_unresolved_references_still_require_the_exact_file_owner() -> None:
    namespace, _other, _a, _b, framed, _other_a, direct, *_rest = _adversarial_state()
    missing_use_reference = replace(
        direct.base.reference,
        name="missing",
        span=replace(direct.base.reference.span, path=None),
    )
    missing_use = replace(direct.expression, base=missing_use_reference)
    definition = replace(
        namespace.definition,
        select_items=(
            replace(namespace.definition.select_items[0], expression=missing_use),
            *namespace.definition.select_items[1:],
        ),
    )
    use_namespace = resolve_named_window_namespace(definition)
    assert type(use_namespace) is ResolvedNamedWindowNamespace
    with pytest.raises(ValueError, match="belong to its owner block"):
        compose_named_window_use(
            use_namespace,
            missing_use,
            selected_output_ordinal=0,
        )

    assert framed.declaration.base is not None
    missing_declaration_base = replace(
        framed.declaration.base,
        name="missing",
        span=replace(framed.declaration.base.span, path=None),
    )
    missing_declaration = replace(
        framed.declaration,
        base=missing_declaration_base,
    )
    declarations = tuple(
        missing_declaration if item is framed.declaration else item
        for item in namespace.declarations
    )
    with pytest.raises(ValueError, match="belong to its owner block"):
        resolve_named_window_namespace(
            replace(namespace.definition, named_windows=declarations)
        )


def test_not_applicable_provenance_is_frame_only() -> None:
    with pytest.raises(ValueError, match="requires a frame component"):
        NamedWindowComponentProvenance(
            component=NamedWindowComponentKind.PARTITION,
            origin=WindowComponentOrigin.NOT_APPLICABLE,
            source=None,
        )


def test_equal_cloned_template_is_not_namespace_authority() -> None:
    *_prefix, direct, _partitioned, _local_frame, _inherited_frame = (
        _adversarial_state()
    )
    cloned_template = replace(
        direct.target_template,
        declaration=replace(direct.target_template.declaration),
    )
    cloned_base = replace(
        direct.base,
        target_declaration=cloned_template.declaration,
    )
    assert cloned_template == direct.target_template
    assert cloned_template is not direct.target_template
    with pytest.raises(ValueError, match="target its exact namespace"):
        replace(direct, target_template=cloned_template, base=cloned_base)


def test_direct_carrier_construction_cannot_bypass_component_conflicts() -> None:
    carriers = _provenance_carrier_matrix()
    partitioned = cast(
        ResolvedNamedWindowTemplate,
        carriers[
            (
                "template",
                NamedWindowComponentKind.PARTITION,
                WindowComponentOrigin.LOCALLY_AUTHORED,
            )
        ][0],
    )
    ordered = cast(
        ResolvedNamedWindowTemplate,
        carriers[
            (
                "template",
                NamedWindowComponentKind.ORDER,
                WindowComponentOrigin.LOCALLY_AUTHORED,
            )
        ][0],
    )
    conflicting_declaration = replace(
        ordered.declaration,
        spec=partitioned.declaration.spec,
    )
    assert conflicting_declaration.base is not None
    assert conflicting_declaration.spec is not None
    assert ordered.base is not None
    conflicting_base = replace(
        ordered.base,
        reference=conflicting_declaration.base,
    )
    local_partition_provenance = NamedWindowComponentProvenance(
        component=NamedWindowComponentKind.PARTITION,
        origin=WindowComponentOrigin.LOCALLY_AUTHORED,
        source=ordered.occurrence,
    )
    with pytest.raises(ValueError, match="cannot be local and inherited"):
        ResolvedNamedWindowTemplate(
            declaration=conflicting_declaration,
            occurrence=ordered.occurrence,
            base=conflicting_base,
            base_template=partitioned,
            partition_by=conflicting_declaration.spec.partition_by,
            order_by=(),
            frame=None,
            partition_provenance=local_partition_provenance,
            ordering_provenance=None,
            frame_provenance=None,
        )

    inherited = cast(
        ComposedNamedWindowUse,
        carriers[
            (
                "composed_use",
                NamedWindowComponentKind.PARTITION,
                WindowComponentOrigin.INHERITED,
            )
        ][0],
    )
    conflicting_expression = replace(
        inherited.expression,
        spec=replace(
            inherited.expression.spec,
            partition_by=inherited.partition_by,
        ),
        use_kind=WindowUseKind.NAMED_EXTENDED,
    )
    selected_item = replace(
        inherited.namespace.definition.select_items[0],
        expression=conflicting_expression,
    )
    definition = replace(
        inherited.namespace.definition,
        select_items=(
            selected_item,
            *inherited.namespace.definition.select_items[1:],
        ),
    )
    namespace = resolve_named_window_namespace(definition)
    assert type(namespace) is ResolvedNamedWindowNamespace
    target = namespace.template_for_name("all")
    assert target is not None
    assert conflicting_expression.base is not None
    occurrence = replace(
        inherited.occurrence,
        kind=WindowUseKind.NAMED_EXTENDED,
    )
    base = NamedWindowBaseResolution(
        owner=occurrence,
        reference=conflicting_expression.base,
        target_declaration=target.declaration,
        target=target.occurrence,
    )
    use_partition_provenance = NamedWindowComponentProvenance(
        component=NamedWindowComponentKind.PARTITION,
        origin=WindowComponentOrigin.LOCALLY_AUTHORED,
        source=occurrence,
    )
    with pytest.raises(ValueError, match="cannot be local and inherited"):
        ComposedNamedWindowUse(
            expression=conflicting_expression,
            occurrence=occurrence,
            namespace=namespace,
            base=base,
            target_template=target,
            partition_by=conflicting_expression.spec.partition_by,
            order_by=target.order_by,
            frame=target.frame,
            partition_provenance=use_partition_provenance,
            ordering_provenance=inherited.ordering_provenance,
            frame_provenance=inherited.frame_provenance,
        )


def test_local_component_cannot_carry_inherited_provenance() -> None:
    _namespace_value, _other, a, _b, _framed, _other_a, _direct, partitioned, *_ = (
        _adversarial_state()
    )
    forged = NamedWindowComponentProvenance(
        component=NamedWindowComponentKind.PARTITION,
        origin=WindowComponentOrigin.INHERITED,
        source=a.occurrence,
    )
    with pytest.raises(ValueError, match="local use partition"):
        replace(partitioned, partition_provenance=forged)


def test_inherited_component_cannot_name_unrelated_reachable_declaration() -> None:
    _namespace_value, _other, _a, b, _framed, _other_a, direct, *_rest = (
        _adversarial_state()
    )
    forged = NamedWindowComponentProvenance(
        component=NamedWindowComponentKind.ORDER,
        origin=WindowComponentOrigin.INHERITED,
        source=b.occurrence,
    )
    with pytest.raises(ValueError, match="direct base"):
        replace(direct, ordering_provenance=forged)


def test_inherited_component_cannot_name_cross_block_declaration() -> None:
    _namespace_value, _other, _a, _b, _framed, other_a, direct, *_rest = (
        _adversarial_state()
    )
    forged = NamedWindowComponentProvenance(
        component=NamedWindowComponentKind.ORDER,
        origin=WindowComponentOrigin.INHERITED,
        source=other_a.occurrence,
    )
    with pytest.raises(ValueError, match="direct base"):
        replace(direct, ordering_provenance=forged)


def test_defaulted_frame_cannot_masquerade_as_explicit_origin() -> None:
    *_prefix, direct, _partitioned, _local_frame, _inherited_frame = (
        _adversarial_state()
    )
    resolved = _resolve_use(direct, WindowFrameApplicability.APPLICABLE)
    forged = NamedWindowComponentProvenance(
        component=NamedWindowComponentKind.FRAME,
        origin=WindowComponentOrigin.LOCALLY_AUTHORED,
        source=direct.occurrence,
    )
    with pytest.raises(ValueError, match="frame origin must match"):
        replace(resolved, frame_provenance=forged)


def test_explicit_local_frame_cannot_carry_inherited_origin() -> None:
    (
        _namespace_value,
        _other,
        a,
        _b,
        _framed,
        _other_a,
        _direct,
        _partitioned,
        local_frame,
        _,
    ) = _adversarial_state()
    forged = NamedWindowComponentProvenance(
        component=NamedWindowComponentKind.FRAME,
        origin=WindowComponentOrigin.INHERITED,
        source=a.occurrence,
    )
    with pytest.raises(ValueError, match="local use frame"):
        replace(local_frame, frame_provenance=forged)


def test_explicit_inherited_frame_requires_exact_supplying_declaration() -> None:
    _namespace_value, _other, _a, b, _framed, _other_a, *_prefix, inherited_frame = (
        _adversarial_state()
    )
    forged = NamedWindowComponentProvenance(
        component=NamedWindowComponentKind.FRAME,
        origin=WindowComponentOrigin.INHERITED,
        source=b.occurrence,
    )
    with pytest.raises(ValueError, match="direct base"):
        replace(inherited_frame, frame_provenance=forged)


def test_applicability_from_another_function_identity_rejects() -> None:
    *_prefix, direct, partitioned, _local_frame, _inherited_frame = _adversarial_state()
    resolved = _resolve_use(direct, WindowFrameApplicability.NOT_APPLICABLE)
    other_identity = _window_identity.WindowFunctionIdentity(
        namespace=(),
        name="rank",
        role=_window_identity.WindowFunctionRole.WINDOW_FUNCTION,
    )
    other_policy = WindowFunctionFramePolicy(
        identity=other_identity,
        kind=WindowFunctionFramePolicyKind.FRAME_INSENSITIVE_EXPLICIT_FORBIDDEN,
    )
    with pytest.raises(ValueError, match="function policy identity must match"):
        replace(
            resolved,
            function_identity=other_identity,
            function_policy=other_policy,
        )
    with pytest.raises(ValueError, match="exact local authored components"):
        replace(resolved, composed=partitioned)


def test_equal_but_distinct_local_partition_authorship_rejects() -> None:
    *_prefix, _direct, partitioned, _local_frame, _inherited_frame = (
        _adversarial_state()
    )
    resolved = _resolve_use(partitioned, WindowFrameApplicability.APPLICABLE)
    authored = resolved.resolved.authored
    cloned_partition = tuple(replace(item) for item in authored.partition_by)
    assert cloned_partition == authored.partition_by
    assert cloned_partition is not authored.partition_by
    assert cloned_partition[0] is not authored.partition_by[0]
    forged_authored = replace(authored, partition_by=cloned_partition)
    forged_resolved = replace(resolved.resolved, authored=forged_authored)
    with pytest.raises(ValueError, match="exact local authored components"):
        replace(resolved, resolved=forged_resolved)


def test_equal_but_distinct_local_order_authorship_rejects() -> None:
    query = _query(
        _parse(
            "query local_order:\n"
            "    from rows\n"
            "    select:\n"
            "        result = row_number() window root:\n"
            "            order by:\n"
            "                id\n"
            "    window root\n"
        ),
        "local_order",
    )
    namespace = _namespace(query)
    composed = compose_named_window_use(
        namespace,
        _window(query),
        selected_output_ordinal=0,
    )
    assert type(composed) is ComposedNamedWindowUse
    resolved = _resolve_use(composed, WindowFrameApplicability.APPLICABLE)
    authored = resolved.resolved.authored
    cloned_order = tuple(replace(item) for item in authored.order_by)
    assert cloned_order == authored.order_by
    assert cloned_order is not authored.order_by
    assert cloned_order[0] is not authored.order_by[0]
    forged_authored = replace(authored, order_by=cloned_order)
    forged_resolved = replace(resolved.resolved, authored=forged_authored)
    with pytest.raises(ValueError, match="exact local authored components"):
        replace(resolved, resolved=forged_resolved)


def test_inherited_component_cannot_masquerade_as_local_use_provenance() -> None:
    *_prefix, direct, _partitioned, _local_frame, _inherited_frame = (
        _adversarial_state()
    )
    forged = NamedWindowComponentProvenance(
        component=NamedWindowComponentKind.ORDER,
        origin=WindowComponentOrigin.LOCALLY_AUTHORED,
        source=direct.occurrence,
    )
    with pytest.raises(ValueError, match="inherited use ordering"):
        replace(direct, ordering_provenance=forged)


def test_explicit_frame_cannot_carry_defaulted_origin() -> None:
    *_prefix, _direct, _partitioned, local_frame, _inherited_frame = (
        _adversarial_state()
    )
    forged = NamedWindowComponentProvenance(
        component=NamedWindowComponentKind.FRAME,
        origin=WindowComponentOrigin.EFFECTIVE_DEFAULT,
        source=None,
    )
    with pytest.raises(ValueError, match="local use frame"):
        replace(local_frame, frame_provenance=forged)


def test_wrong_multi_hop_node_cannot_substitute_for_direct_provenance() -> None:
    query = _query(
        _parse(
            "query chain:\n"
            "    from rows\n"
            "    select:\n"
            "        result = row_number() window c\n"
            "    window a:\n"
            "        order by:\n"
            "            id\n"
            "    window b = a\n"
            "    window c = b\n"
        ),
        "chain",
    )
    namespace = _namespace(query)
    a = namespace.template_for_name("a")
    assert a is not None
    composed = compose_named_window_use(
        namespace,
        _window(query),
        selected_output_ordinal=0,
    )
    assert type(composed) is ComposedNamedWindowUse
    forged = NamedWindowComponentProvenance(
        component=NamedWindowComponentKind.ORDER,
        origin=WindowComponentOrigin.INHERITED,
        source=a.occurrence,
    )
    with pytest.raises(ValueError, match="direct base"):
        replace(composed, ordering_provenance=forged)


def test_use_occurrence_ordinal_must_select_the_exact_authored_expression() -> None:
    *_prefix, direct, _partitioned, _local_frame, _inherited_frame = (
        _adversarial_state()
    )
    wrong_occurrence = replace(direct.occurrence, selected_output_ordinal=1)
    wrong_base = replace(direct.base, owner=wrong_occurrence)
    with pytest.raises(ValueError, match="base evidence must be exact"):
        replace(direct, occurrence=wrong_occurrence, base=wrong_base)


def test_applicability_evidence_from_another_use_with_shared_spec_rejects() -> None:
    state = _adversarial_state()
    namespace = state[0]
    definition = namespace.definition
    first_item = definition.select_items[0]
    second_item = definition.select_items[1]
    first_expression = cast(WindowExpr, first_item.expression)
    second_expression = replace(first_expression, span=second_item.expression.span)
    second_definition = replace(
        definition,
        select_items=(
            first_item,
            replace(second_item, expression=second_expression),
            *definition.select_items[2:],
        ),
    )
    second_namespace = resolve_named_window_namespace(second_definition)
    assert type(second_namespace) is ResolvedNamedWindowNamespace
    first = compose_named_window_use(
        second_namespace,
        first_expression,
        selected_output_ordinal=0,
    )
    second = compose_named_window_use(
        second_namespace,
        second_expression,
        selected_output_ordinal=1,
    )
    assert type(first) is ComposedNamedWindowUse
    assert type(second) is ComposedNamedWindowUse
    first_resolved = _resolve_use(first, WindowFrameApplicability.APPLICABLE)
    second_resolved = _resolve_use(second, WindowFrameApplicability.APPLICABLE)
    with pytest.raises(ValueError, match="exact local authored components"):
        replace(
            first_resolved,
            composed=second,
            partition_provenance=second_resolved.partition_provenance,
            ordering_provenance=second_resolved.ordering_provenance,
            frame_provenance=second_resolved.frame_provenance,
        )


def test_equal_reconstructed_typed_occurrence_and_provenance_remain_valid() -> None:
    *_prefix, direct, _partitioned, _local_frame, _inherited_frame = (
        _adversarial_state()
    )
    reconstructed_occurrence = replace(direct.occurrence)
    reconstructed_base = replace(direct.base, owner=reconstructed_occurrence)
    assert direct.ordering_provenance is not None
    reconstructed_provenance = replace(direct.ordering_provenance)
    reconstructed = replace(
        direct,
        occurrence=reconstructed_occurrence,
        base=reconstructed_base,
        ordering_provenance=reconstructed_provenance,
    )
    assert reconstructed.occurrence == direct.occurrence
    assert reconstructed.occurrence is not direct.occurrence
    resolved = _resolve_use(reconstructed, WindowFrameApplicability.APPLICABLE)
    reconstructed_resolved_provenance = replace(resolved.ordering_provenance)
    assert (
        replace(
            resolved,
            ordering_provenance=reconstructed_resolved_provenance,
        ).ordering_provenance
        == resolved.ordering_provenance
    )


def test_invariant_matrix_declares_every_live_layer_slot_and_origin() -> None:
    assert len(EXPECTED_PROVENANCE_ORIGIN_MATRIX) == 9
    assert {entry[:2] for entry in EXPECTED_PROVENANCE_ORIGIN_MATRIX} == {
        (layer, component)
        for layer in ("template", "composed_use", "resolved_use")
        for component in NamedWindowComponentKind
    }
    assert CROSS_SLOT_KIND_MATRIX == (
        (NamedWindowComponentKind.PARTITION, NamedWindowComponentKind.ORDER),
        (NamedWindowComponentKind.PARTITION, NamedWindowComponentKind.FRAME),
        (NamedWindowComponentKind.ORDER, NamedWindowComponentKind.PARTITION),
        (NamedWindowComponentKind.ORDER, NamedWindowComponentKind.FRAME),
        (NamedWindowComponentKind.FRAME, NamedWindowComponentKind.PARTITION),
        (NamedWindowComponentKind.FRAME, NamedWindowComponentKind.ORDER),
    )
    for layer, component, origins in EXPECTED_PROVENANCE_ORIGIN_MATRIX:
        if component is NamedWindowComponentKind.FRAME and layer == "resolved_use":
            assert WindowComponentOrigin.NOT_APPLICABLE in origins
        else:
            assert WindowComponentOrigin.NOT_APPLICABLE not in origins
        if layer == "resolved_use":
            assert WindowComponentOrigin.EFFECTIVE_DEFAULT in origins
        else:
            assert WindowComponentOrigin.EFFECTIVE_DEFAULT not in origins


def test_cross_slot_matrix_rejects_every_representable_origin() -> None:
    carriers = _provenance_carrier_matrix()
    expected = {
        (layer, component, origin)
        for layer, component, origins in EXPECTED_PROVENANCE_ORIGIN_MATRIX
        for origin in origins
    }
    assert set(carriers) == expected
    assert len(expected) == 22
    attempts = 0
    for (layer, slot, origin), (carrier, field) in carriers.items():
        provenance = cast(
            NamedWindowComponentProvenance,
            getattr(carrier, field),
        )
        assert (provenance.component, provenance.origin) == (slot, origin)
        for expected_slot, wrong_kind in CROSS_SLOT_KIND_MATRIX:
            if expected_slot is not slot:
                continue
            attempts += 1
            with pytest.raises(ValueError):
                replace(
                    carrier,
                    **{field: replace(provenance, component=wrong_kind)},
                )
    assert attempts == 44


def test_slice8_spec_locks_semantic_only_and_later_owner_boundaries() -> None:
    document = " ".join(SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "window whole",
        "window recent:",
        "window alias = recent",
        "window rolling = recent:",
        "call(...) window recent",
        "call(...) window recent:",
        "Slice 8 is semantic-only",
        "Slice 9 owns frame-value functions, modifiers, and first legal inline explicit-frame SQL activation",
        "Slice 10 owns named-window target-lowerability strategy and capability",
        "Slice 11 owns real authored advanced-window SQL E2E",
        "Add Phase 60 query-local named windows",
    ):
        assert evidence in document
