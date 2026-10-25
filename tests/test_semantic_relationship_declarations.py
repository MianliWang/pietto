from __future__ import annotations

from dataclasses import fields, replace
from pathlib import Path

import pytest

from _pietto_repository_facts import REPOSITORY_FACTS
from pietto._project.project_ir_operators import ProjectIRLogicalOperatorKind
from pietto import ast_nodes as ast
from pietto.ast_nodes import Script
from pietto.errors import Diagnostic
from pietto.ir.model import RelationIR, ScriptIR
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.model import (
    RelationshipTemplateInfo,
    SemanticModel,
    SemanticResult,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice2-relationship-declaration-identity-endpoint-roles-module-local-resolution-construction-states-v1.md"
)
SOURCE = REPO_ROOT / "src/pietto/_project/project_relationships.py"

SPEC_HEADINGS = (
    "Answer And Exact Owner",
    "Starting Authority",
    "Frozen Reader And Changed-path Closure",
    "Existing Semantic And Project Authority",
    "Private Carriers And Identity Laws",
    "Module Ownership Endpoint Roles And Resolution",
    "Construction States Completeness And Ordering",
    "Implementation Boundary And Non-goals",
    "Focused Assurance",
    "Compatibility And Production Delta",
    "Later-owner Boundaries",
    "Slice 3 Handoff",
    "Review And Repair Accounting",
    "Gate Lifecycle And Publication",
)


def _located(diagnostics: tuple[Diagnostic, ...]) -> list[tuple[str, str, int, int]]:
    return [
        (item.code, item.message, item.location.line, item.location.column)
        for item in diagnostics
    ]


def test_existing_public_semantic_ir_and_project_ir_shapes_are_unchanged() -> None:
    assert tuple(item.name for item in fields(SemanticModel)) == (
        "mode",
        "type_symbols",
        "callable_symbols",
        "relation_symbols",
        "type_resolutions",
        "type_expansions",
        "type_nullability",
        "decimal_precision_scales",
        "decimal_expression_precision_scales",
        "source_row_schemas",
        "from_resolutions",
        "relation_row_schemas",
        "expression_value_types",
        "window_expression_analyses",
        "named_window_namespaces",
        "result_predicates",
        "let_scopes",
        "relation_joins",
        "relationships",
        "relationship_templates",
        "relationship_calls",
        "existence_generators",
        "any_values",
    )
    assert tuple(item.name for item in fields(RelationIR)) == (
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
        "named_windows",
        "inputs",
        "joins",
    )
    assert tuple(item.name for item in fields(ScriptIR)) == ("definitions",)
    assert tuple(item.name for item in ProjectIRLogicalOperatorKind) == (
        "RELATION_INPUT",
        "ROW_FILTER",
        "GROUP_AGGREGATE",
        "RESULT_FILTER",
        "WINDOW_EVALUATION",
        "FINAL_PROJECTION",
        "RELATION_ORDERING",
        "LIMIT",
    )


def test_source_uses_existing_resolution_and_semantic_authority_without_scans() -> None:
    facts = REPOSITORY_FACTS.python(SOURCE)
    assert {
        "pietto._project.model",
        "pietto._project.module_carrier",
        "pietto._project.module_relation_resolution",
        "pietto.semantic.relationship_metadata",
        "pietto.semantic.model",
    } <= facts.imported_modules
    assert (
        not {
            "pietto.ir",
            "pietto.sql",
            "pathlib",
            "os",
        }
        & facts.imported_modules
    )
    for forbidden in (
        "sorted",
        "sort",
        "glob",
        "rglob",
        "getcwd",
        "cwd",
        "sha256",
        "hash",
    ):
        assert forbidden not in facts.identifiers
    for required in (
        "check_relationship_metadata",
        "find_module_path",
        "find_relation_name",
        "target_occurrence",
        "semantic_relationships",
    ):
        assert required in facts.identifiers


def test_contract_locks_slice_owner_non_goals_handoff_and_gate() -> None:
    document = SPEC.read_text(encoding="utf-8")
    assert (
        tuple(
            line.removeprefix("## ")
            for line in document.splitlines()
            if line.startswith("## ")
        )
        == SPEC_HEADINGS
    )
    normalized = " ".join(document.split())
    for evidence in (
        "998eaa5655bbe64d4ae13b8ac03f413ce84343ff",
        "d3a698a3a4916cac39a0852bb43ef4243876b18e",
        "33463294917",
        "existing public RelationshipSemanticInfo != private Project relationship occurrence",
        "relationship declaration occurrence != endpoint occurrence",
        "endpoint local role/name != endpoint identity",
        "CONCRETE UNKNOWN DEFERRED BLOCKED AMBIGUOUS",
        "deterministic order != semantic identity",
        "field correspondences",
        "UNIQUE/key semantics",
        "value FD engine",
        "grain",
        "referential coverage/cardinality",
        "relationship paths/fanout",
        "authored JOIN syntax/use",
        "Project IR JOIN region",
        "multi-fact alignment",
        "relationship import/export",
        "public relationship schema",
        "Phase 62 Slice 3 — Exact Field Correspondences, ON/WHERE Separation, Equality/Null Behavior, And Constraint-Scope Boundary",
        "Add Phase 62 relationship identity foundation",
        "PASS — PHASE62_SLICE2_RELATIONSHIP_DECLARATION_IDENTITY_ENDPOINT_ROLES_MODULE_LOCAL_RESOLUTION_CONSTRUCTION_STATES_END_TO_END",
    ):
        assert evidence in normalized


def _predicate_example() -> tuple[
    Script,
    ast.ShapeDef,
    ast.SourceDef,
    ast.QueryDef,
    tuple[RelationshipTemplateInfo, ...],
    ast.CallExpr,
]:
    """Authored nodes isolate the predicate owner from parser migration."""
    from pietto.semantic.model import EffectiveNullability, ResolvedType, TypeKind
    from pietto.semantic.relationship_predicates import check_relationship_templates

    span = ast.Span(
        path="predicates.pietto", line=1, column=1, end_line=1, end_column=20
    )
    integer = ast.TypeExpr(
        span=span, name="Int", arguments=(), nullability=ast.Nullability.NOT_NULL
    )
    text_type = ast.TypeExpr(
        span=span, name="Text", arguments=(), nullability=ast.Nullability.NULLABLE
    )
    fields = tuple(
        ast.FieldDef(
            span=span,
            name=name,
            type_expr=kind,
            derive_expression=None,
            annotations=(),
            ensure_clauses=(),
        )
        for name, kind in (
            ("id", integer),
            ("parent_id", integer),
            ("status", text_type),
        )
    )
    shape = ast.ShapeDef(span=span, name="Customer", items=fields)
    source = ast.SourceDef(
        span=span,
        name="customers",
        shape_name="Customer",
        connector=ast.LiteralExpr(span=span, value="customers"),
    )
    eq = ast.ComparisonExpr(
        span=span,
        operator="==",
        left=ast.DottedNameExpr(span=span, parts=("child", "parent_id")),
        right=ast.DottedNameExpr(span=span, parts=("parent", "id")),
    )
    active = ast.ComparisonExpr(
        span=span,
        operator="==",
        left=ast.DottedNameExpr(span=span, parts=("parent", "status")),
        right=ast.LiteralExpr(span=span, value="active"),
    )
    template = ast.RelationshipTemplate(
        span=span,
        name="ActiveParent",
        parameters=tuple(
            ast.RelationshipParameter(span=span, name=name, shape_name="Customer")
            for name in ("child", "parent")
        ),
        body=ast.BinaryExpr(span=span, operator="and", left=eq, right=active),
    )
    from_clause = ast.FromClause(span=span, source_name="customers")
    join = ast.JoinClause(
        span=span,
        kind=ast.AuthoredJoinKind.LEFT,
        target_relation_name="customers",
        target_binding_name="parent",
        source_binding_name=None,
    )
    owner = ast.QueryDef(
        span=span,
        name="q",
        from_clause=from_clause,
        where_clause=None,
        group_by_clause=None,
        select_items=(),
        join_clauses=(join,),
    )
    script = ast.Script(
        span=span,
        header=None,
        definitions=(shape, source, owner),
        relationship_templates=(template,),
    )
    checked, diagnostics = check_relationship_templates(
        script,
        shape_candidates={"Customer": (shape,)},
        type_resolutions={
            integer: ResolvedType("Int", TypeKind.BUILTIN),
            text_type: ResolvedType("Text", TypeKind.BUILTIN),
        },
        type_expansions={},
        type_nullability={
            integer: EffectiveNullability.NON_NULL,
            text_type: EffectiveNullability.NULLABLE,
        },
    )
    assert diagnostics == ()
    call = ast.CallExpr(
        span=span,
        callee=ast.NameExpr(span=span, name="ActiveParent"),
        arguments=tuple(
            ast.NameExpr(span=span, name=name) for name in ("customers", "parent")
        ),
    )
    return script, shape, source, owner, checked, call


def test_row_predicate_keeps_self_join_occurrences_and_filter() -> None:
    from pietto.semantic.relationship_predicates import bind_relationship_expression

    _, shape, source, owner, templates, call = _predicate_example()
    occurrences = {"customers": owner.from_clause, "parent": owner.join_clauses[0]}
    expanded, uses, diagnostics, failures = bind_relationship_expression(
        call,
        templates=templates,
        declared_names=frozenset({"ActiveParent"}),
        resolve_row=lambda argument: ((occurrences[argument.name], source, shape),),
        owner=owner,
        context=ast.JoinOnClause(span=call.span, expression=call),
    )
    assert diagnostics == () and failures == ()
    assert len(uses) == 1
    use = uses[0]
    assert use.call is call and use.template is templates[0]
    assert use.arguments[0].occurrence is owner.from_clause
    assert use.arguments[1].occurrence is owner.join_clauses[0]
    assert use.arguments[0].relation is use.arguments[1].relation is source
    assert type(expanded) is ast.BinaryExpr and expanded.operator == "and"
    assert isinstance(expanded.right, ast.ComparisonExpr)
    assert isinstance(expanded.right.right, ast.LiteralExpr)
    assert expanded.right.right.value == "active"
    assert len(use.mandatory_equalities) == 1
    assert isinstance(use.mandatory_equalities[0].left, ast.DottedNameExpr)
    assert isinstance(use.mandatory_equalities[0].right, ast.DottedNameExpr)
    assert use.mandatory_equalities[0].left.parts == ("customers", "parent_id")
    assert use.mandatory_equalities[0].right.parts == ("parent", "id")


@pytest.mark.parametrize("duplicate", [False, True])
def test_row_predicate_refuses_shape_lookalikes_and_ambiguous_occurrences(
    duplicate: bool,
) -> None:
    from pietto.semantic.relationship_predicates import bind_relationship_expression

    _, shape, source, owner, templates, call = _predicate_example()
    same_bytes_other_identity = replace(shape)
    rows = (
        ((owner.from_clause, source, shape),) * 2
        if duplicate
        else ((owner.from_clause, source, same_bytes_other_identity),)
    )
    result, uses, diagnostics, failures = bind_relationship_expression(
        call,
        templates=templates,
        declared_names=frozenset({"ActiveParent"}),
        resolve_row=lambda argument: rows,
        owner=owner,
        context=owner,
    )
    assert result is call
    assert uses == ()
    (failure,) = failures
    assert failure.call is call and failure.expression is result
    assert len(failure.diagnostics) == len(diagnostics)
    assert all(a is b for a, b in zip(failure.diagnostics, diagnostics, strict=True))
    assert len(diagnostics) == 2
    assert all(
        ("Ambiguous" if duplicate else "different shape identity") in item.message
        for item in diagnostics
    )


def test_row_predicate_or_not_are_values_without_mandatory_equality_proofs() -> None:
    from pietto.semantic.relationship_predicates import (
        bind_relationship_expression,
        mandatory_field_equalities,
    )

    _, shape, source, owner, templates, call = _predicate_example()
    expression = ast.BinaryExpr(
        span=call.span,
        operator="or",
        left=call,
        right=ast.UnaryExpr(
            span=call.span,
            operator="not",
            operand=replace(call, span=replace(call.span, column=2)),
        ),
    )
    expanded, uses, diagnostics, failures = bind_relationship_expression(
        expression,
        templates=templates,
        declared_names=frozenset({"ActiveParent"}),
        resolve_row=lambda argument: (
            (
                owner.from_clause
                if argument.name == "customers"
                else owner.join_clauses[0],
                source,
                shape,
            ),
        ),
        owner=owner,
        context=owner,
    )
    assert diagnostics == () and failures == ()
    assert len(uses) == 2
    assert uses[0].call is call
    assert isinstance(expression.right, ast.UnaryExpr)
    assert uses[1].call is expression.right.operand
    assert mandatory_field_equalities(expanded) == ()
    assert all(use.mandatory_equalities == () for use in uses)
    assert isinstance(expanded, ast.BinaryExpr)
    assert isinstance(expanded.right, ast.UnaryExpr)
    assert expanded.operator == "or" and expanded.right.operator == "not"


def test_row_predicate_stays_inside_coalesce_and_conditional() -> None:
    from pietto.semantic.relationship_predicates import bind_relationship_expression

    _, shape, source, owner, templates, call = _predicate_example()
    coalesce = ast.CallExpr(
        span=call.span,
        callee=ast.NameExpr(span=call.span, name="coalesce"),
        arguments=(call, ast.LiteralExpr(span=call.span, value=False)),
    )
    expression = ast.ConditionalExpr(
        span=call.span,
        when_true=coalesce,
        condition=ast.LiteralExpr(span=call.span, value=True),
        when_false=ast.LiteralExpr(span=call.span, value=None),
    )
    expanded, uses, diagnostics, failures = bind_relationship_expression(
        expression,
        templates=templates,
        declared_names=frozenset({"ActiveParent"}),
        resolve_row=lambda argument: ((owner.from_clause, source, shape),),
        owner=owner,
        context=owner,
    )
    assert diagnostics == () and failures == () and len(uses) == 1
    assert type(expanded) is ast.ConditionalExpr
    assert isinstance(expanded.when_true, ast.CallExpr)
    assert isinstance(expanded.when_true.callee, ast.NameExpr)
    assert isinstance(expanded.when_true.arguments[1], ast.LiteralExpr)
    assert isinstance(expanded.when_false, ast.LiteralExpr)
    assert expanded.when_true.callee.name == "coalesce"
    assert expanded.when_true.arguments[1].value is False
    assert expanded.when_false.value is None


def test_analyzer_binds_every_predicate_copy_inside_scalar_helper() -> None:
    script, shape, source, owner, _, call = _predicate_example()
    span = call.span
    template = script.relationship_templates[0]
    template = replace(
        template,
        parameters=(template.parameters[0],),
        body=ast.ComparisonExpr(
            span=span,
            operator=">",
            left=ast.DottedNameExpr(span=span, parts=("child", "id")),
            right=ast.LiteralExpr(span=span, value=0),
        ),
    )
    boolean = ast.TypeExpr(
        span=span, name="Bool", arguments=(), nullability=ast.Nullability.NULLABLE
    )
    keep = ast.FunctionDef(
        span=span,
        name="keep",
        parameters=(ast.Parameter(span=span, name="value", type=boolean),),
        return_type=boolean,
        body=ast.BinaryExpr(
            span=span,
            operator="and",
            left=ast.NameExpr(span=span, name="value"),
            right=ast.NameExpr(span=span, name="value"),
        ),
    )
    call = replace(call, arguments=(call.arguments[0],))
    wrapper = ast.CallExpr(
        span=span, callee=ast.NameExpr(span=span, name="keep"), arguments=(call,)
    )
    source = replace(
        source,
        connector=ast.CallExpr(
            span=span,
            callee=ast.DottedNameExpr(span=span, parts=("postgres", "table")),
            arguments=(ast.LiteralExpr(span=span, value="customers"),),
        ),
    )
    owner = replace(
        owner,
        join_clauses=(),
        select_items=(ast.SelectItem(span=span, alias="ok", expression=wrapper),),
    )
    result = analyze(
        replace(
            script,
            definitions=(shape, source, keep, owner),
            relationship_templates=(template,),
        )
    )
    assert result.diagnostics == ()
    assert len(result.model.relationship_calls) == 2
    first, second = result.model.relationship_calls
    assert first.arguments[0].occurrence is second.arguments[0].occurrence
    assert first.arguments[0].relation is second.arguments[0].relation is source
    assert first.call.span != second.call.span
    assert result.script is not None
    normalized = result.script.definitions[-1]
    assert isinstance(normalized, ast.QueryDef)
    expression = normalized.select_items[0].expression
    assert isinstance(expression, ast.BinaryExpr)
    assert isinstance(expression.left, ast.ComparisonExpr)
    assert isinstance(expression.right, ast.ComparisonExpr)
    assert result.model.expression_value_types[expression].resolved_type.name == "Bool"


def test_modern_let_resolves_relation_and_scalar_roles_and_normalizes_once() -> None:
    from pietto.semantic.modern_inputs import normalize_query_names

    script, shape, source, owner, _, _ = _predicate_example()
    span = owner.span
    alias = ast.QueryLetDeclaration(
        span=replace(span, line=2, end_line=2),
        name="parent",
        name_span=span,
        expression=ast.NameExpr(span=span, name="customers"),
    )
    scalar = ast.QueryLetDeclaration(
        span=replace(span, line=5, end_line=5),
        name="flag",
        name_span=span,
        expression=ast.LiteralExpr(span=span, value=True),
    )
    owner = replace(
        owner,
        from_clause=replace(owner.from_clause, span=replace(span, line=3, end_line=3)),
        join_clauses=(
            replace(
                owner.join_clauses[0],
                span=replace(span, line=4, end_line=4),
                target_relation_name="parent",
            ),
        ),
        naming_declarations=(alias, scalar),
    )
    normalized, diagnostics = normalize_query_names(
        replace(script, definitions=(shape, source, owner))
    )
    assert diagnostics == ()
    query = normalized.definitions[-1]
    assert isinstance(query, ast.QueryDef)
    assert query.join_clauses[0].target_relation_name == "customers"
    assert query.join_clauses[0].target_binding_name == "parent"
    assert query.let_clause is not None
    assert tuple(item.name for item in query.let_clause.bindings) == ("flag",)
    assert query.naming_declarations == ()
    again, diagnostics = normalize_query_names(normalized)
    assert diagnostics == () and again == normalized


def test_modern_let_refuses_relation_scalar_ambiguity() -> None:
    from pietto.semantic.modern_inputs import normalize_query_names

    script, shape, source, owner, _, _ = _predicate_example()
    shape = replace(
        shape, items=(*shape.items, replace(shape.fields[0], name="customers"))
    )
    span = replace(owner.span, line=2, end_line=2)
    alias = ast.QueryLetDeclaration(
        span=span,
        name="buyer",
        name_span=span,
        expression=ast.NameExpr(span=span, name="customers"),
    )
    owner = replace(owner, naming_declarations=(alias,))
    _, diagnostics = normalize_query_names(
        replace(script, definitions=(shape, source, owner))
    )
    assert any(
        "Ambiguous relation or scalar name: customers" in item.message
        for item in diagnostics
    )


def test_modern_let_cannot_read_future_join_input() -> None:
    from pietto.semantic.modern_inputs import normalize_query_names

    script, shape, source, owner, _, _ = _predicate_example()
    span = replace(owner.span, line=2, end_line=2)
    scalar = ast.QueryLetDeclaration(
        span=span,
        name="id_copy",
        name_span=span,
        expression=ast.DottedNameExpr(span=span, parts=("parent", "id")),
    )
    owner = replace(
        owner,
        join_clauses=(
            replace(owner.join_clauses[0], span=replace(span, line=3, end_line=3)),
        ),
        naming_declarations=(scalar,),
    )
    _, diagnostics = normalize_query_names(
        replace(script, definitions=(shape, source, owner))
    )
    assert any(
        "A row-value let must follow FROM and every JOIN and precede WHERE"
        in item.message
        for item in diagnostics
    )


def test_row_predicate_binds_an_unused_parameter() -> None:
    from pietto.semantic.relationship_predicates import bind_relationship_expression

    _, shape, source, owner, templates, call = _predicate_example()
    template = replace(
        templates[0],
        declaration=replace(
            templates[0].declaration, body=ast.LiteralExpr(span=call.span, value=True)
        ),
    )
    expanded, uses, diagnostics, failures = bind_relationship_expression(
        call,
        templates=(template,),
        declared_names=frozenset({"ActiveParent"}),
        resolve_row=lambda argument: (
            ((owner.from_clause, source, shape),)
            if argument.name == "customers"
            else ()
        ),
        owner=owner,
        context=ast.JoinOnClause(span=call.span, expression=call),
    )
    assert expanded is call and uses == ()
    (failure,) = failures
    assert failure.call is call and failure.expression is expanded
    assert failure.diagnostics[0] is diagnostics[0]
    assert len(diagnostics) == 1
    assert "parameter parent" in diagnostics[0].message


def test_selected_row_predicate_produces_no_required_equality_proof() -> None:
    from pietto.semantic.relationship_predicates import bind_relationship_expression

    _, shape, source, owner, templates, call = _predicate_example()
    _, uses, diagnostics, failures = bind_relationship_expression(
        call,
        templates=templates,
        declared_names=frozenset({"ActiveParent"}),
        resolve_row=lambda argument: ((owner.from_clause, source, shape),),
        owner=owner,
        context=ast.SelectItem(span=call.span, alias="matches", expression=call),
    )
    assert diagnostics == () and failures == () and len(uses) == 1
    assert uses[0].mandatory_equalities == ()


def test_row_predicate_refuses_an_ambiguous_scalar_interpretation() -> None:
    from pietto.semantic.relationship_predicates import bind_relationship_expression

    _, shape, source, owner, templates, call = _predicate_example()
    expanded, uses, diagnostics, failures = bind_relationship_expression(
        call,
        templates=templates,
        declared_names=frozenset({"ActiveParent"}),
        resolve_row=lambda argument: ((owner.from_clause, source, shape),),
        owner=owner,
        context=owner,
        scalar_names=frozenset({"ActiveParent"}),
        scalar_argument_names=frozenset({"customers", "parent"}),
    )
    assert expanded is call and uses == ()
    (failure,) = failures
    assert failure.call is call and failure.expression is expanded
    assert failure.diagnostics[0] is diagnostics[0]
    assert len(diagnostics) == 1
    assert "Ambiguous scalar or relationship call" in diagnostics[0].message


_MODERN_PREDICATE_INPUTS = """shape Item:
    id: Int
    owner_id: Int
    item_key = unique(id)
shape Owner:
    id: Int
    status: Text | None
    owner_key = unique(id)
source items: Item = postgres.table("shop.items")
source owners: Owner = postgres.table("shop.owners")
relationship ActiveOwner(item: Item, owner: Owner):
    item.owner_id == owner.id and owner.status == "active"
"""


def _modern_predicate_result(source: str) -> SemanticResult:
    parsed = parse_source(source, path="modern-predicates.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None, parsed.diagnostics
    return analyze(parsed.ast)


def test_modern_predicate_normalization_keeps_actual_join_occurrences_and_sql() -> None:
    from pietto.ir import build_ir
    from pietto.semantic.model import EffectiveNullability
    from pietto.sql.postgres import emit_postgres_sql

    text = (
        _MODERN_PREDICATE_INPUTS
        + """query result:
    let base = items
    from base
    let buyer = owners
    left join buyer on ActiveOwner(base, buyer)
    select:
        item_id = base.id
        owner_id = buyer.id
        accepted = coalesce(ActiveOwner(base, buyer), False)
"""
    )
    result = _modern_predicate_result(text)
    assert result.diagnostics == ()
    assert result.script is not None
    query = result.model.relation_symbols["result"]
    assert isinstance(query, ast.QueryDef)
    assert (query.from_clause.source_name, query.from_clause.binding_name) == (
        "items",
        "base",
    )
    join = query.join_clauses[0]
    assert join.source_binding_name is None and join.uses_named_input
    assert (join.target_relation_name, join.target_binding_name) == ("owners", "buyer")
    info = result.model.relation_joins[query]
    assert [item.binding for item in info.inputs] == ["base", "buyer"]
    assert [item.relation.name for item in info.inputs] == ["items", "owners"]
    assert (
        result.model.relation_row_schemas[query].fields["owner_id"].nullability
        is EffectiveNullability.NULLABLE
    )
    assert len(result.model.relationship_calls) == 2
    first, selected = result.model.relationship_calls
    assert first.owner is query and first.context is join.on_clause
    assert selected.owner is query and selected.context is query.select_items[2]
    for call in (first, selected):
        assert call.arguments[0].occurrence is query.from_clause
        assert call.arguments[1].occurrence is join
        assert call.arguments[0].relation is info.inputs[0].relation
        assert call.arguments[1].relation is info.inputs[1].relation
    assert len(first.mandatory_equalities) == 1 and selected.mandatory_equalities == ()
    assert info.joins[0].equalities == ()
    emitted = []
    for source in (
        text,
        text.replace(
            "ActiveOwner(base, buyer)",
            '(base.owner_id == buyer.id and buyer.status == "active")',
        ),
    ):
        analyzed = _modern_predicate_result(source)
        assert analyzed.diagnostics == () and analyzed.script is not None
        lowered = build_ir(analyzed.script, analyzed.model)
        assert lowered.diagnostics == () and lowered.ir is not None
        sql = emit_postgres_sql(lowered.ir)
        assert sql.diagnostics == ()
        emitted.append(sql.artifacts)
    assert emitted[0] == emitted[1]
    assert '"shop"."items"' in emitted[0][0].sql
    assert '"shop"."owners"' in emitted[0][0].sql


@pytest.mark.parametrize("context", ("on", "where"))
def test_required_predicate_equalities_protect_fanout_without_fabricating_legacy_facts(
    context: str,
) -> None:
    joining = (
        "left join buyer on ActiveOwner(items, buyer)"
        if context == "on"
        else "cross join buyer\n    where ActiveOwner(items, buyer)"
    )
    result = _modern_predicate_result(
        _MODERN_PREDICATE_INPUTS
        + f"""query result:
    from items
    let buyer = owners
    {joining}
    select:
        n = count(items.id)
"""
    )
    assert result.diagnostics == ()
    query = result.model.relation_symbols["result"]
    assert isinstance(query, ast.QueryDef)
    (call,) = result.model.relationship_calls
    assert call.context is (
        query.join_clauses[0].on_clause if context == "on" else query.where_clause
    )
    assert len(call.mandatory_equalities) == 1
    assert result.model.relationships == ()
    assert result.model.relation_joins[query].joins[0].equalities == ()


@pytest.mark.parametrize(
    "condition",
    (
        "ActiveOwner(items, buyer) or False",
        "not ActiveOwner(items, buyer)",
        "coalesce(ActiveOwner(items, buyer), False)",
        "ActiveOwner(items, buyer) if items.id > 0 else False",
        'items.owner_id == buyer.id and buyer.status == "active"',
    ),
)
def test_nonmandatory_calls_and_handwritten_on_do_not_gain_key_proofs(
    condition: str,
) -> None:
    result = _modern_predicate_result(
        _MODERN_PREDICATE_INPUTS
        + f"""query result:
    from items
    let buyer = owners
    left join buyer on {condition}
    select:
        n = count(items.id)
"""
    )
    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2381"]
    assert all(
        call.mandatory_equalities == () for call in result.model.relationship_calls
    )


@pytest.mark.parametrize("order", ((0, 1, 2, 3), (3, 2, 1, 0), (2, 0, 3, 1)))
def test_predicate_composite_key_uses_all_calls_and_alternative_determinants(
    order: tuple[int, ...],
) -> None:
    source = """shape Seed:
    id: Int
    seed_key = unique(id)
shape Pair:
    x: Int
    y: Int
    pair_key = unique(x, y)
source seeds: Seed = postgres.table("seeds")
source pairs: Pair = postgres.table("pairs")
relationship MatchX(seed: Seed, pair: Pair):
    seed.id == pair.x
relationship MatchY(seed: Seed, pair: Pair):
    seed.id == pair.y
query result:
    from seeds
    let alternative = seeds
    cross join alternative
    let other = seeds
    cross join other
    let pair = pairs
    inner join pair on MatchX(seeds, pair) and MatchX(alternative, pair) and MatchY(other, pair) and MatchX(alternative, pair)
    select:
        n = count(alternative.id + other.id)
"""
    conditions = (
        "MatchX(seeds, pair)",
        "MatchX(alternative, pair)",
        "MatchY(other, pair)",
        "MatchX(alternative, pair)",
    )
    source = source.replace(
        " and ".join(conditions), " and ".join(conditions[index] for index in order)
    )
    result = _modern_predicate_result(source)
    assert result.diagnostics == ()
    assert len(result.model.relationship_calls) == 4
    assert [
        len(call.mandatory_equalities) for call in result.model.relationship_calls
    ] == [1, 1, 1, 1]
    query = result.model.relation_symbols["result"]
    assert isinstance(query, ast.QueryDef)
    assert all(
        call.context is query.join_clauses[-1].on_clause
        for call in result.model.relationship_calls
    )
    occurrences = (
        query.from_clause,
        query.join_clauses[0],
        query.join_clauses[1],
        query.join_clauses[0],
    )
    assert all(
        call.arguments[0].occurrence is occurrences[index]
        for call, index in zip(result.model.relationship_calls, order, strict=True)
    )
    partial = _modern_predicate_result(
        source.replace(
            " and ".join(conditions[index] for index in order),
            " and ".join(conditions[index] for index in order if index != 2),
        )
    )
    assert [diagnostic.code for diagnostic in partial.diagnostics] == ["PIE-S2381"]


def test_from_alias_reads_through_let_grouping_satisfying_and_ir() -> None:
    from pietto.ir import build_ir
    from pietto.sql.postgres import emit_postgres_sql

    result = _modern_predicate_result(
        _MODERN_PREDICATE_INPUTS
        + """query result:
    let chosen = items
    from chosen
    let group_key = chosen.id
    where chosen.id > 0
    group by:
        group_key
    select:
        id = chosen.id
        n = count()
    having:
        n > 0
    order by:
        id
"""
    )
    assert result.diagnostics == () and result.script is not None
    query = result.model.relation_symbols["result"]
    assert isinstance(query, ast.QueryDef)
    assert result.model.from_resolutions[query.from_clause].name == "items"
    lowered = build_ir(result.script, result.model)
    assert lowered.diagnostics == () and lowered.ir is not None
    sql = emit_postgres_sql(lowered.ir)
    assert sql.diagnostics == ()
    assert '"shop"."items"' in sql.artifacts[0].sql


def test_where_and_select_predicate_wrappers_keep_all_value_occurrences() -> None:
    result = _modern_predicate_result(
        _MODERN_PREDICATE_INPUTS
        + """query result:
    from items
    let buyer = owners
    left join buyer on ActiveOwner(items, buyer)
    where ActiveOwner(items, buyer) or not ActiveOwner(items, buyer)
    select:
        accepted = coalesce(ActiveOwner(items, buyer), False)
        conditional = ActiveOwner(items, buyer) if items.id > 0 else None
"""
    )
    assert result.diagnostics == ()
    assert len(result.model.relationship_calls) == 5
    assert [
        len(call.mandatory_equalities) for call in result.model.relationship_calls
    ] == [1, 0, 0, 0, 0]
    assert [call.ordinal for call in result.model.relationship_calls] == list(range(5))


def test_modern_multi_join_predicates_keep_accumulated_left_occurrences() -> None:
    from pietto.ir import build_ir
    from pietto.semantic.model import EffectiveNullability
    from pietto.sql.postgres import emit_postgres_sql

    result = _modern_predicate_result("""shape Order:
    id: Int
    customer_id: Int
    order_key = unique(id)
shape Customer:
    id: Int
    status: Text | None
    region_id: Int | None
    customer_key = unique(id)
shape Region:
    id: Int
    name: Text
    region_key = unique(id)
source orders: Order = postgres.table("shop.orders")
source customers: Customer = postgres.table("shop.customers")
source regions: Region = postgres.table("shop.regions")
relationship ActiveOrderCustomer(order: Order, customer: Customer):
    order.customer_id == customer.id and customer.status == "active"
relationship CustomerRegion(customer: Customer, region: Region):
    customer.region_id == region.id
query order_customers:
    from orders
    let buyer = customers
    left join buyer on ActiveOrderCustomer(orders, buyer)
    let region = regions
    left join region on CustomerRegion(buyer, region)
    select:
        order_id = orders.id
        customer_id = buyer.id
        region_name = region.name
""")
    assert result.diagnostics == () and result.script is not None
    query = result.model.relation_symbols["order_customers"]
    assert isinstance(query, ast.QueryDef)
    first, second = result.model.relationship_calls
    assert first.owner is second.owner is query
    assert first.arguments[1].occurrence is query.join_clauses[0]
    assert second.arguments[0].occurrence is query.join_clauses[0]
    assert second.arguments[1].occurrence is query.join_clauses[1]
    assert all(
        join.source_binding_name is None and join.uses_named_input
        for join in query.join_clauses
    )
    fields = result.model.relation_row_schemas[query].fields
    assert tuple(fields) == ("order_id", "customer_id", "region_name")
    assert fields["order_id"].nullability is EffectiveNullability.NON_NULL
    assert (
        fields["customer_id"].nullability
        is fields["region_name"].nullability
        is EffectiveNullability.NULLABLE
    )
    lowered = build_ir(result.script, result.model)
    assert lowered.diagnostics == () and lowered.ir is not None
    sql = emit_postgres_sql(lowered.ir)
    assert sql.diagnostics == ()
    assert sql.artifacts[0].sql.count("LEFT JOIN") == 2
    assert "'active'" in sql.artifacts[0].sql


def test_predicate_key_proof_rejects_same_bytes_foreign_input_occurrence() -> None:
    from pietto.semantic.join_fanout import join_fanout_diagnostics

    result = _modern_predicate_result(
        _MODERN_PREDICATE_INPUTS
        + """query result:
    from items
    let buyer = owners
    left join buyer on ActiveOwner(items, buyer)
    select:
        n = count(items.id)
"""
    )
    assert result.diagnostics == ()
    query = result.model.relation_symbols["result"]
    assert isinstance(query, ast.QueryDef)
    (call,) = result.model.relationship_calls
    foreign = replace(
        call,
        arguments=(
            call.arguments[0],
            replace(call.arguments[1], occurrence=replace(query.join_clauses[0])),
        ),
    )
    diagnostics = join_fanout_diagnostics(
        query,
        result.model.relation_joins[query],
        type_symbols=result.model.type_symbols,
        source_row_schemas=result.model.source_row_schemas,
        let_expressions={},
        relationship_calls=(foreign,),
    )
    assert [item.code for item in diagnostics] == ["PIE-S2381"]


@pytest.mark.parametrize("reversed_calls", (False, True))
def test_predicate_dependency_cycle_cannot_borrow_same_relation_occurrence(
    reversed_calls: bool,
) -> None:
    calls: tuple[str, ...] = ("Same(first, second)", "Same(second, first)")
    if reversed_calls:
        calls = tuple(reversed(calls))
    result = _modern_predicate_result(
        """shape Row:
    id: Int
    row_key = unique(id)
source rows: Row = postgres.table("rows")
relationship Same(a: Row, b: Row):
    a.id == b.id
query result:
    from rows
    let first = rows
    cross join first
    let second = rows
    inner join second on """
        + " and ".join(calls)
        + """
    select:
        n = count(rows.id)
"""
    )
    assert [item.code for item in result.diagnostics] == ["PIE-S2381"]
    assert len(result.model.relationship_calls) == 2


@pytest.mark.parametrize("foreign", ("context", "handwritten_equality"))
def test_predicate_key_proof_requires_its_own_exact_context_and_expansion(
    foreign: str,
) -> None:
    from pietto.semantic.join_fanout import join_fanout_diagnostics

    result = _modern_predicate_result(
        _MODERN_PREDICATE_INPUTS
        + """relationship Accept(item: Item, owner: Owner):
    True
query result:
    from items
    let buyer = owners
    left join buyer on Accept(items, buyer) and items.owner_id == buyer.id
    select:
        n = count(items.id)
"""
    )
    assert [item.code for item in result.diagnostics] == ["PIE-S2381"]
    query = result.model.relation_symbols["result"]
    assert isinstance(query, ast.QueryDef)
    on = query.join_clauses[0].on_clause
    assert on is not None and isinstance(on.expression, ast.BinaryExpr)
    assert isinstance(on.expression.right, ast.ComparisonExpr)
    (call,) = result.model.relationship_calls
    forged = replace(call, mandatory_equalities=(on.expression.right,))
    if foreign == "context":
        forged = replace(forged, context=replace(on))
    diagnostics = join_fanout_diagnostics(
        query,
        result.model.relation_joins[query],
        type_symbols=result.model.type_symbols,
        source_row_schemas=result.model.source_row_schemas,
        let_expressions={},
        relationship_calls=(forged,),
    )
    assert [item.code for item in diagnostics] == ["PIE-S2381"]


def test_modern_join_satisfying_resolves_a_let_renamed_group_key() -> None:
    from pietto.ir import build_ir

    result = _modern_predicate_result(
        _MODERN_PREDICATE_INPUTS
        + """query result:
    let chosen = items
    from chosen
    let buyer = owners
    left join buyer on ActiveOwner(chosen, buyer)
    let grouped_id = chosen.id
    group by:
        grouped_id
    select:
        key = chosen.id
        n = count()
    having:
        key > 0 and n > 0
"""
    )
    assert result.diagnostics == () and result.script is not None
    query = result.model.relation_symbols["result"]
    assert isinstance(query, ast.QueryDef)
    assert query in result.model.result_predicates
    lowered = build_ir(result.script, result.model)
    assert lowered.diagnostics == () and lowered.ir is not None


@pytest.mark.parametrize("with_join", (False, True))
def test_modern_from_alias_separates_sql_binding_and_relation_identity(
    with_join: bool,
) -> None:
    from pietto.ir import build_ir
    from pietto.sql.postgres import emit_postgres_sql

    join = (
        "    let buyer = owners\n    left join buyer on ActiveOwner(base, buyer)\n"
        if with_join
        else ""
    )
    result = _modern_predicate_result(
        _MODERN_PREDICATE_INPUTS
        + "query q:\n    let base = items\n    from base\n"
        + join
        + "    select:\n        id = base.id\n"
    )
    assert result.diagnostics == () and result.script is not None
    lowered = build_ir(result.script, result.model)
    assert lowered.diagnostics == () and lowered.ir is not None
    relation = next(
        item for item in lowered.ir.definitions if isinstance(item, RelationIR)
    )
    assert relation.source.name == "base" and relation.source.target.name == "items"
    if with_join:
        assert relation.inputs[0].binding == "base"
        assert relation.inputs[0].target == relation.source.target
    emitted = emit_postgres_sql(lowered.ir)
    assert emitted.diagnostics == ()
    sql = emitted.artifacts[0].sql
    assert 'FROM "shop"."items" AS "base"' in sql
    assert '"base"."id"' in sql


@pytest.mark.parametrize("window", (None, "inline", "named"))
def test_modern_alias_grouped_let_order_and_window_keep_actual_field_owner(
    window: str | None,
) -> None:
    from pietto.ir import build_ir
    from pietto.sql.postgres import emit_postgres_sql

    window_item = (
        ""
        if window is None
        else "        rn = row_number() window ordered\n"
        if window == "named"
        else "        rn = row_number() window(order by grouped_id)\n"
    )
    declaration = (
        "    let ordered = window(order by grouped_id)\n" if window == "named" else ""
    )
    result = _modern_predicate_result(
        _MODERN_PREDICATE_INPUTS
        + """query q:
    let base = items
    from base
    let grouped_id = base.id
"""
        + declaration
        + """    group by:
        grouped_id
    select:
        id = base.id
        n = count()
"""
        + window_item
        + "    order by:\n        grouped_id\n"
    )
    assert result.diagnostics == () and result.script is not None
    lowered = build_ir(result.script, result.model)
    assert lowered.diagnostics == () and lowered.ir is not None
    relation = next(
        item for item in lowered.ir.definitions if isinstance(item, RelationIR)
    )
    assert relation.group_keys[0].field is not None
    assert relation.group_keys[0].field.owner is not None
    assert relation.group_keys[0].field.owner.name == "items"
    sql = emit_postgres_sql(lowered.ir)
    assert sql.diagnostics == ()
    assert 'FROM "shop"."items" AS "base"' in sql.artifacts[0].sql


@pytest.mark.parametrize("projection", ("id", "rows.id"))
def test_modern_input_role_ambiguity_includes_default_derived_output_names(
    projection: str,
) -> None:
    result = _modern_predicate_result(
        """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
source id: Row = postgres.table("other_rows")
query base:
    from rows
    select:
        """
        + projection
        + """
query q:
    from base
    let chosen = id
    cross join chosen
    select:
        value = base.id
"""
    )
    assert [(item.code, item.message) for item in result.diagnostics] == [
        ("PIE-S2604", "Ambiguous relation or scalar name: id")
    ]


@pytest.mark.parametrize("placement", ("absent", "before", "after"))
def test_unrelated_shape_fields_do_not_change_row_predicate_argument_binding(
    placement: str,
) -> None:
    unused = "shape Unused:\n    rows: Int\n"
    source = """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
relationship Positive(row: Row):
    row.id > 0
query q:
    from rows
    let accepted = Positive(rows)
    select:
        ok = accepted
"""
    if placement == "before":
        source = unused + source
    elif placement == "after":
        source += unused
    result = _modern_predicate_result(source)
    assert result.diagnostics == ()
    query = result.model.relation_symbols["q"]
    assert isinstance(query, ast.QueryDef)
    (call,) = result.model.relationship_calls
    assert call.arguments[0].occurrence is query.from_clause
    assert (
        call.arguments[0].relation is result.model.from_resolutions[query.from_clause]
    )


@pytest.mark.parametrize("before", ("from", "join"))
def test_scalar_query_let_cannot_move_across_an_input_boundary(before: str) -> None:
    body = (
        "    let value = 1\n    from items\n"
        if before == "from"
        else "    from items\n    let value = 1\n    let buyer = owners\n    cross join buyer\n"
    )
    result = _modern_predicate_result(
        _MODERN_PREDICATE_INPUTS
        + "query q:\n"
        + body
        + "    select:\n        out = value\n"
    )
    assert [(item.code, item.message) for item in result.diagnostics] == [
        (
            "PIE-S2604",
            "A row-value let must follow FROM and every JOIN and precede WHERE",
        )
    ]


def test_failed_row_predicate_arity_retains_exact_failure() -> None:
    from pietto.semantic.relationship_predicates import bind_relationship_expression

    _, shape, source, owner, templates, original = _predicate_example()
    call = replace(original, arguments=original.arguments[:1])
    expanded, uses, diagnostics, failures = bind_relationship_expression(
        call,
        templates=templates,
        declared_names=frozenset({"ActiveParent"}),
        resolve_row=lambda argument: ((owner.from_clause, source, shape),),
        owner=owner,
        context=owner,
    )
    assert uses == () and expanded is call
    assert _located(diagnostics) == [
        (
            "PIE-S2604",
            "Invalid arguments for relationship ActiveParent: expected 2, got 1",
            1,
            1,
        )
    ]
    (failure,) = failures
    assert failure.call is call and failure.expression is expanded
    assert len(failure.diagnostics) == 1 and failure.diagnostics[0] is diagnostics[0]


@pytest.mark.parametrize("argument", ("future", "Missing()"))
def test_failed_predicate_on_keeps_real_errors_and_no_join_facts(argument: str) -> None:
    source = (
        _MODERN_PREDICATE_INPUTS
        + f"""query q:
    from items
    let current = owners
    inner join current on ActiveOwner(items, {argument}) and Missing()
    let future = owners
    inner join future on items.owner_id == future.id
    select:
        id = items.id
"""
    )
    result = _modern_predicate_result(source)
    unavailable = (
        "Unavailable row argument for relationship ActiveOwner parameter owner"
    )
    missing = "Unknown function: Missing"
    expected = (
        [("PIE-S2604", unavailable, 16, 46), ("PIE-S2103", missing, 16, 58)]
        if argument == "future"
        else [
            ("PIE-S2103", missing, 16, 46),
            ("PIE-S2604", unavailable, 16, 46),
            ("PIE-S2103", missing, 16, 61),
        ]
    )
    assert _located(result.diagnostics) == expected
    query = result.model.relation_symbols["q"]
    assert isinstance(query, ast.QueryDef)
    assert query not in result.model.relation_joins


def test_failed_predicates_preserve_occurrences_and_invalid_body_order() -> None:
    source = """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
relationship Broken(row: Row):
    row.missing > 0
query q:
    from rows
    let n = 1
    let answer = Broken(n + Missing()) and Broken(rows) and Missing()
    select:
        id = rows.id
"""
    result = _modern_predicate_result(source)
    refused = "Relationship predicate Broken has no unambiguous checked declaration"
    assert _located(result.diagnostics) == [
        ("PIE-S2604", "Unknown relationship parameter field: row.missing", 5, 5),
        ("PIE-S2604", refused, 9, 18),
        ("PIE-S2103", "Unknown function: Missing", 9, 29),
        ("PIE-S2604", refused, 9, 44),
        ("PIE-S2103", "Unknown function: Missing", 9, 61),
    ]
    call_diags = [result.diagnostics[index] for index in (1, 3)]
    assert call_diags[0] is not call_diags[1]
    assert call_diags[0].location != call_diags[1].location


def test_failed_predicate_cannot_read_a_hidden_semi_join_row() -> None:
    result = _modern_predicate_result(
        _MODERN_PREDICATE_INPUTS
        + """query q:
    from items
    let hidden = owners
    where any(items.owner_id == hidden.id for hidden in hidden)
    let current = owners
    inner join current on ActiveOwner(items, hidden)
    select:
        id = items.id
"""
    )
    assert _located(result.diagnostics) == [
        (
            "PIE-S2604",
            "Unavailable row argument for relationship ActiveOwner parameter owner",
            18,
            46,
        )
    ]
    query = result.model.relation_symbols["q"]
    assert isinstance(query, ast.QueryDef)
    assert query not in result.model.relation_joins


def test_failed_predicate_same_name_and_span_keeps_both_occurrences() -> None:
    from pietto.semantic.relationship_predicates import bind_relationship_expression

    _, _, _, owner, templates, first = _predicate_example()
    second = replace(first)
    expression = ast.BinaryExpr(
        span=first.span, operator="and", left=first, right=second
    )
    expanded, uses, diagnostics, failures = bind_relationship_expression(
        expression,
        templates=templates,
        declared_names=frozenset({"ActiveParent"}),
        resolve_row=lambda argument: (),
        owner=owner,
        context=owner,
    )
    assert expanded is expression and uses == () and len(failures) == 2
    child = "Unavailable row argument for relationship ActiveParent parameter child"
    parent = "Unavailable row argument for relationship ActiveParent parameter parent"
    # Two equal-looking calls keep both of their own parameter errors.
    assert _located(diagnostics) == [
        ("PIE-S2604", child, 1, 1),
        ("PIE-S2604", parent, 1, 1),
        ("PIE-S2604", child, 1, 1),
        ("PIE-S2604", parent, 1, 1),
    ]
    assert failures[0].call is failures[0].expression is first
    assert failures[1].call is failures[1].expression is second
    assert all(
        retained is actual
        for retained, actual in zip(
            (d for failure in failures for d in failure.diagnostics),
            diagnostics,
            strict=True,
        )
    )


def test_failed_predicate_identity_survives_a_written_def_argument() -> None:
    result = _modern_predicate_result("""shape Row:
    id: Int
source rows: Row = postgres.table("rows")
relationship Same(a: Row, b: Row):
    a.id == b.id
def Identity(value: Bool) -> Bool:
    return value
query q:
    from rows
    let n = None
    where Identity(Same(rows, n + Missing()) and n > 0) and Missing()
    select:
        id = rows.id
""")
    # `n > 0` reads a name bound to null: an independent sibling error.
    assert _located(result.diagnostics) == [
        (
            "PIE-S2604",
            "Unavailable row argument for relationship Same parameter b",
            11,
            31,
        ),
        ("PIE-S2103", "Unknown function: Missing", 11, 35),
        (
            "PIE-S2105",
            "Invalid operands for operator >: comparison with null is never true",
            11,
            50,
        ),
        ("PIE-S2103", "Unknown function: Missing", 11, 61),
    ]


def test_failed_predicate_aggregate_argument_keeps_its_scanned_child_error() -> None:
    result = _modern_predicate_result("""shape Row:
    id: Int
source rows: Row = postgres.table("rows")
relationship Same(a: Row, b: Row):
    a.id == b.id
query q:
    from rows
    select:
        total = sum(Same(1 + Missing(), 2))
""")
    # The aggregate-shape refusal stays; the rejected call's scanned Missing()
    # stays once, between its two row-argument errors in source order.
    assert _located(result.diagnostics) == [
        (
            "PIE-S2315",
            "Aggregate function sum requires a direct field argument; "
            "expression arguments are not supported yet",
            9,
            17,
        ),
        (
            "PIE-S2604",
            "Unavailable row argument for relationship Same parameter a",
            9,
            26,
        ),
        ("PIE-S2103", "Unknown function: Missing", 9, 30),
        (
            "PIE-S2604",
            "Unavailable row argument for relationship Same parameter b",
            9,
            41,
        ),
    ]


def test_failed_predicate_row_argument_is_no_scalar_read_or_let_dependency() -> None:
    ambiguous = _modern_predicate_result("""shape Row:
    id: Int
source rows: Row = postgres.table("rows")
relationship Positive(row: Row):
    row.id > 0
query q:
    from rows
    let other = rows
    inner join other on True
    where Positive(id) and Missing()
    select:
        id = rows.id
""")
    # `id` is refused as a row argument, never read as the ambiguous field.
    assert _located(ambiguous.diagnostics) == [
        (
            "PIE-S2604",
            "Unavailable row argument for relationship Positive parameter row",
            10,
            20,
        ),
        ("PIE-S2103", "Unknown function: Missing", 10, 28),
    ]
    itself = _modern_predicate_result(
        _MODERN_PREDICATE_INPUTS
        + """query q:
    from items
    let a = ActiveOwner(items, a)
    select:
        id = items.id
        flag = a
"""
    )
    # A row argument is no LET dependency, so `a` is no self-reference.
    assert _located(itself.diagnostics) == [
        (
            "PIE-S2604",
            "Unavailable row argument for relationship ActiveOwner parameter owner",
            15,
            32,
        )
    ]


_FAILED_ANY = (
    "any(ActiveOwner(items, candidate.id + Missing()) and items.id > 0 "
    "for candidate in owners)"
)
# Each query body after `from items`, with the ANY line and the columns of the
# rejected call's complex row argument and of the real unknown call inside it.
_FAILED_ANY_QUERIES = {
    "on": (
        "    let buyer = owners\n"
        f"    inner join buyer on {_FAILED_ANY}\n"
        "    select:\n"
        "        id = items.id\n",
        (16, 48, 63),
    ),
    "where": (
        f"    where {_FAILED_ANY}\n    select:\n        id = items.id\n",
        (15, 34, 49),
    ),
    "select": (
        f"    select:\n        id = items.id\n        ok = {_FAILED_ANY}\n",
        (17, 37, 52),
    ),
    "let": (
        f"    let ok = {_FAILED_ANY}\n"
        "    select:\n"
        "        id = items.id\n"
        "        flag = ok\n",
        (15, 37, 52),
    ),
    "joined_where": (
        "    let buyer = owners\n"
        "    inner join buyer on ActiveOwner(items, buyer)\n"
        f"    where {_FAILED_ANY}\n"
        "    select:\n"
        "        id = items.id\n",
        (17, 34, 49),
    ),
}


@pytest.mark.parametrize("placement", tuple(_FAILED_ANY_QUERIES))
def test_failed_predicate_in_any_keeps_real_errors_without_scalar_cascade(
    placement: str,
) -> None:
    body, (line, argument, missing) = _FAILED_ANY_QUERIES[placement]
    result = _modern_predicate_result(
        _MODERN_PREDICATE_INPUTS + "query q:\n    from items\n" + body
    )
    assert _located(result.diagnostics) == [
        (
            "PIE-S2604",
            "Unavailable row argument for relationship ActiveOwner parameter owner",
            line,
            argument,
        ),
        ("PIE-S2103", "Unknown function: Missing", line, missing),
    ]
    query = result.model.relation_symbols["q"]
    assert isinstance(query, ast.QueryDef)
    # A body with a rejected call acquires no checked ANY facts.
    assert dict(result.model.any_values) == {}
    if placement == "joined_where":
        (call,) = result.model.relationship_calls
        assert call.context is query.join_clauses[0].on_clause
    else:
        assert result.model.relationship_calls == ()
    if placement == "on":
        assert query not in result.model.relation_joins


_TABLE_ROW_BODY = """table owner_rows:
    from owners
    select:
        id, status
        {target}
query q:
    from items
    {reader}
    select:
        id = items.id
        {own}
query ranked:
    from items
    select:
        id
        {other}
"""
_TABLE_ROW_UNAVAILABLE = (
    "Unavailable row argument for relationship ActiveOwner parameter owner"
)
_TABLE_ROW_READ = (
    "`owner_rows` is a table of this file; single-file SQL reads it by name, so "
    "the SQL runs only where the database already has a relation named "
    "owner_rows (an EXPLICIT_MODULES project emits it as a CTE)"
)
# Each reader passes the same-file table `owner_rows` as the Owner row on line
# 20, with what the file reports without a window.
_TABLE_ROW_READERS = {
    "on": (
        "left join owner_rows on ActiveOwner(items, owner_rows)",
        [
            ("PIE-S2382", _TABLE_ROW_READ, 20, 5),
            ("PIE-S2604", _TABLE_ROW_UNAVAILABLE, 20, 48),
        ],
    ),
    "any": (
        "where any(ActiveOwner(items, candidate) for candidate in owner_rows)",
        [("PIE-S2604", _TABLE_ROW_UNAVAILABLE, 20, 34)],
    ),
}
# A selected window in the table the call reads (line 17), in the reader's own
# query (line 23) or in an unrelated query (line 28).
_TABLE_ROW_WINDOWS = {
    "target": ("target", "n = row_number() window(order by id)"),
    "own": ("own", "n = row_number() window(order by items.id)"),
    "other": ("other", "n = row_number() window(order by id)"),
}


def _table_row_source(reader: str, slot: str = "", text: str = "") -> str:
    slots: dict[str, str] = dict.fromkeys(("target", "own", "other"), "# no window")
    if slot:
        slots[slot] = text
    return _MODERN_PREDICATE_INPUTS + _TABLE_ROW_BODY.format(
        reader=_TABLE_ROW_READERS[reader][0], **slots
    )


@pytest.mark.parametrize("window", tuple(_TABLE_ROW_WINDOWS))
@pytest.mark.parametrize("reader", tuple(_TABLE_ROW_READERS))
def test_failed_predicate_reports_alike_beside_a_selected_window(
    reader: str, window: str
) -> None:
    expected = _TABLE_ROW_READERS[reader][1]
    control = _modern_predicate_result(_table_row_source(reader))
    assert _located(control.diagnostics) == expected
    result = _modern_predicate_result(
        _table_row_source(reader, *_TABLE_ROW_WINDOWS[window])
    )
    # A window anywhere in the file adds only what it earns itself: one over
    # the JOIN rows of `q` is refused there.
    earned = (
        [
            (
                "PIE-S2334",
                "Window functions over JOIN rows are available only when an "
                "EXPLICIT_MODULES project (schema version 2) completes them.",
                23,
                13,
            )
        ]
        if (reader, window) == ("on", "own")
        else []
    )
    assert _located(result.diagnostics) == expected + earned


def test_failed_predicate_in_a_window_argument_keeps_both_errors() -> None:
    result = _modern_predicate_result(
        _table_row_source(
            "any",
            "other",
            "n = lag(ActiveOwner(items, owner_rows)) window(order by id)",
        )
    )
    assert _located(result.diagnostics) == [
        ("PIE-S2604", _TABLE_ROW_UNAVAILABLE, 20, 34),
        (
            "PIE-S2104",
            "Invalid arguments for function lag: value must be a direct field "
            "or Bool, Text, Int, Float, or NULL literal",
            28,
            13,
        ),
        ("PIE-S2604", _TABLE_ROW_UNAVAILABLE, 28, 36),
    ]


@pytest.mark.parametrize(
    "command",
    (
        ("check",),
        ("emit-sql", "--dialect", "postgres"),
        ("emit-sql", "--dialect", "mysql"),
        ("explain",),
    ),
)
def test_failed_predicate_beside_a_window_reports_in_each_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], command: tuple[str, ...]
) -> None:
    from pietto import cli

    path = tmp_path / "main.pietto"
    path.write_text(
        _table_row_source("on", *_TABLE_ROW_WINDOWS["other"]), encoding="utf-8"
    )
    assert cli.main([command[0], str(path), *command[1:]]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        f"{path}:20:5 PIE-S2382 warning: {_TABLE_ROW_READ}\n"
        f"{path}:20:48 PIE-S2604 error: {_TABLE_ROW_UNAVAILABLE}\n"
    )


def test_failed_predicate_beside_a_window_reports_in_a_legacy_flat_project(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from pietto import cli

    (tmp_path / "pietto.toml").write_text(
        'schema_version = 1\n\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (tmp_path / "main.pietto").write_text(
        _table_row_source("on", *_TABLE_ROW_WINDOWS["other"]), encoding="utf-8"
    )
    assert cli.main(["check", "--project", str(tmp_path)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "main.pietto:20:26 PIE-S2334 error: JOIN owner_rows: a schema_version = 1 "
        "project has no JOIN in the current syntax; set schema_version = 2 to "
        "check it.\n"
    )
