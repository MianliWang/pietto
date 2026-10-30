from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from _pietto_project_join import _completed, _parsed
from _pietto_sql_emission import _declared_source, fixture as emission_fixture
from pietto import cli
from pietto._project import check as project_check
from pietto._project import project_join_conditions as conditions
from pietto._project.model import (
    ProjectRowFieldNullability,
    ProjectRowResultRole,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
    build_project_completed_semantic_result,
)
from pietto._project.project_completion import ProjectExistingEffectiveOutput
from pietto._project.project_final_outputs import ProjectCompletedEffectiveOutput
from pietto._project.project_row_keys import (
    ProjectExactRowOutputConstraintScope,
    ProjectRelationshipConstraintScopeKind,
)
from pietto._project.project_relationship_predicates import (
    ProjectRelationshipPredicateCatalog,
)
from pietto._project.project_row_keys import (
    ProjectRowUniquenessEvidence,
    build_project_row_keys,
)
from pietto.ast_nodes import (
    BinaryExpr,
    ComparisonExpr,
    DottedNameExpr,
    EnumDef,
    Node,
    QueryDef,
    ShapeDef,
    Script,
    TableDef,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.ir import build_ir
from pietto.ir.model import ScriptIR
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.sql import emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql


def _semantic_project(root: Path, files: dict[str, str]) -> ProjectSemanticResult:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    for relative, source in files.items():
        (root / relative).write_text(source, encoding="utf-8")
    parsed = project_check.check_project_parse_only(root)
    assert parsed.ok, parsed.diagnostics
    return build_empty_project_semantic_result(parsed)


def _completed_files(
    root: Path, files: dict[str, str]
) -> ProjectConcreteCompletedSemanticResult:
    result = build_project_completed_semantic_result(_semantic_project(root, files))
    assert isinstance(result, ProjectConcreteCompletedSemanticResult)
    return result


def _project_files() -> dict[str, str]:
    return {
        "a.pietto": """from "b.pietto" import shape CustomerRow as ImportedCustomerRow, source customers as ImportedCustomers
shape OrderRow:
    id: Int
    tenant_id: Int
    customer_id: Int | None
source orders: OrderRow = postgres.table("orders")
table order_view:
    from orders
    select id, tenant_id, customer_id
query order_counts:
    from orders
    group by tenant_id
    select tenant_id, total = count(id)
shape EmployeeRow:
    id: Int
source employees: EmployeeRow = postgres.table("employees")
relationship single(order: OrderRow, customer: ImportedCustomerRow):
    order.customer_id == customer.id
relationship composite(order: OrderRow, customer: ImportedCustomerRow):
    order.tenant_id == customer.tenant_id and order.customer_id == customer.id
relationship reversed_repeated(order: OrderRow, customer: ImportedCustomerRow):
    customer.id == order.customer_id and order.customer_id == customer.id
relationship self_link(employee: EmployeeRow, manager: EmployeeRow):
    employee.id == manager.id
query single_match:
    from orders
    let customer = ImportedCustomers
    inner join customer on single(orders, customer)
    select id = orders.id
query composite_match:
    from orders
    let customer = ImportedCustomers
    inner join customer on composite(orders, customer)
    select id = orders.id
query reversed_match:
    from orders
    let customer = ImportedCustomers
    inner join customer on reversed_repeated(orders, customer)
    select id = orders.id
query self_match:
    from employees
    let manager = employees
    inner join manager on self_link(employees, manager)
    select id = employees.id
query view_match:
    from order_view
    let customer = ImportedCustomers
    inner join customer on order_view.customer_id == customer.id
    select id = order_view.id
query aggregate_match:
    from order_counts
    let customer = ImportedCustomers
    inner join customer on order_counts.total == customer.id
    select total = order_counts.total
""",
        "b.pietto": """shape CustomerRow:
    id: Int
    tenant_id: Int
source customers: CustomerRow = postgres.table("customers")
export shape CustomerRow, source customers
""",
    }


def _named(
    result: ProjectConcreteCompletedSemanticResult, name: str
) -> conditions.ProjectJoinCondition:
    (condition,) = tuple(
        item
        for item in result.roots.join_conditions.entries
        if item.ledger.owner.definition.name == name
    )
    return condition


def test_typed_relationship_body_retains_expression_spans_and_order() -> None:
    path = Path("relationships/matches.pietto")
    body = "    left.tenant_id == right.tenant_id and left.id == right.left_id"
    result = parse_source(
        "relationship matched(left: LeftRow, right: RightRow):\n" + body + "\n",
        path=path,
    )
    assert result.diagnostics == () and isinstance(result.ast, Script)
    (matched,) = result.ast.relationship_templates
    expression = matched.body
    assert expression.span.path == str(path)
    assert (expression.span.line, expression.span.column) == (2, 5)
    assert (expression.span.end_line, expression.span.end_column) == (2, len(body) + 1)
    assert isinstance(expression, BinaryExpr) and expression.operator == "and"
    assert isinstance(expression.left, ComparisonExpr)
    assert isinstance(expression.right, ComparisonExpr)
    assert expression.left is not expression.right
    assert expression.left.operator == expression.right.operator == "=="
    operands = (
        expression.left.left,
        expression.left.right,
        expression.right.left,
        expression.right.right,
    )
    parts = []
    for item in operands:
        assert isinstance(item, DottedNameExpr)
        parts.append(item.parts)
    assert tuple(parts) == (
        ("left", "tenant_id"),
        ("right", "tenant_id"),
        ("left", "id"),
        ("right", "left_id"),
    )


def test_current_conditions_retain_order_fields_types_and_authority(
    tmp_path: Path,
) -> None:
    completed = _completed_files(tmp_path, _project_files())
    assert completed.ok, completed.diagnostics
    single = _named(completed, "single_match")
    assert single.ready and len(single.mandatory_equalities) == 1
    equality = single.mandatory_equalities[0]
    assert equality.condition is single and equality.comparison is single.conjuncts[0]
    assert equality.left is single.references[0].target
    assert equality.right is single.references[1].target
    assert equality.left.nullability is ProjectRowFieldNullability.NULLABLE
    assert equality.left.value_type.resolved_type.name == "Int"
    assert equality.right.binding.target is not None
    assert (
        equality.right.binding.target.target_occurrence.identity.module_path
        == "b.pietto"
    )
    predicate = single.environment.predicate_expression
    assert predicate is not None
    assert equality.calls == predicate.calls and len(equality.calls) == 1
    for argument, binding in zip(
        equality.calls[0].arguments, single.ledger.bindings, strict=True
    ):
        assert argument.occurrence is binding.site
        assert binding.target is not None
        assert argument.relation is binding.target.target_occurrence.definition
    for name, field_name, role, producer in (
        (
            "view_match",
            "customer_id",
            ProjectRowResultRole.ORDINARY_ROW_VALUE,
            ProjectExistingEffectiveOutput,
        ),
        (
            "aggregate_match",
            "total",
            ProjectRowResultRole.AGGREGATE_RESULT,
            ProjectCompletedEffectiveOutput,
        ),
    ):
        fact = _named(completed, name)
        # A hand-written equality is a match equality without any call.
        assert fact.ready and len(fact.mandatory_equalities) == 1
        assert fact.mandatory_equalities[0].calls == ()
        left = fact.references[0].target
        assert left is not None and left.input_field.evidence.name == field_name
        assert left.input_field.evidence.result_role is role
        assert left.binding.target is not None
        target = left.binding.target.target_occurrence
        (entry,) = tuple(
            item for item in completed.effective_outputs.entries if item.owner is target
        )
        assert type(entry) is producer
        if type(entry) is ProjectCompletedEffectiveOutput:
            # A grouped producer read as a current JOIN input keeps its value
            # authority at its own completed output field.
            published = entry.schema.fields[field_name]
        else:
            facts = completed.semantic_result.module_semantic_facts
            assert facts is not None
            (owner,) = facts.find_owner(target)
            assert owner.state.schema is not None
            published = owner.state.schema.fields[field_name]
        assert left.input_field.evidence is published
    composite = _named(completed, "composite_match")
    assert tuple(item.conjunct_position for item in composite.mandatory_equalities) == (
        0,
        1,
    )
    assert tuple(
        (item.left.input_field.evidence.name, item.right.input_field.evidence.name)
        for item in composite.mandatory_equalities
    ) == (("tenant_id", "tenant_id"), ("customer_id", "id"))
    assert all(item.condition is composite for item in composite.mandatory_equalities)


def test_reversed_repeated_and_self_reads_never_collapse_identity(
    tmp_path: Path,
) -> None:
    completed = _completed_files(tmp_path, _project_files())
    assert completed.ok, completed.diagnostics
    reversed_repeated = _named(completed, "reversed_match")
    first, second = reversed_repeated.mandatory_equalities
    assert first is not second and first.comparison is not second.comparison
    assert (first.conjunct_position, second.conjunct_position) == (0, 1)
    assert first.left.binding is second.right.binding
    assert first.right.binding is second.left.binding
    assert first.left.input_field is second.right.input_field
    assert first.right.input_field is second.left.input_field
    assert tuple(reference.position for reference in reversed_repeated.references) == (
        0,
        1,
        2,
        3,
    )
    assert (
        len({id(reference.expression) for reference in reversed_repeated.references})
        == 4
    )
    self_link = _named(completed, "self_match")
    (equality,) = self_link.mandatory_equalities
    assert equality.left.binding is not equality.right.binding
    assert equality.left.binding.site is not equality.right.binding.site
    assert (
        equality.left.binding.target is not None
        and equality.right.binding.target is not None
    )
    assert (
        equality.left.binding.target.target_occurrence
        is equality.right.binding.target.target_occurrence
    )
    assert equality.left.input_field.evidence is equality.right.input_field.evidence
    assert self_link.references[0].expression is not self_link.references[1].expression


def test_source_unique_scope_rejects_nonunconditional_kind(tmp_path: Path) -> None:
    parsed = _parsed(
        tmp_path,
        """shape Row:
    id: Int
    row_key = unique(id)
source rows: Row = postgres.table("rows")
""",
    )
    assert parsed.ok, parsed.diagnostics
    semantic = build_empty_project_semantic_result(parsed)
    keys = build_project_row_keys(semantic)
    (evidence,) = keys.subjects
    assert type(evidence) is ProjectRowUniquenessEvidence
    assert len(evidence.determinants) == 1
    scope = evidence.scope
    assert type(scope) is ProjectExactRowOutputConstraintScope
    assert scope.owner == evidence.identity.source
    assert scope.relation is evidence.source_semantic
    with pytest.raises(ValueError, match="only exact-row-output"):
        replace(scope, kind=ProjectRelationshipConstraintScopeKind.UNDER_PREDICATE)


def test_condition_construction_is_cwd_and_environment_independent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    completed = _completed_files(tmp_path / "project", _project_files())
    assert completed.ok, completed.diagnostics
    uses = completed.roots.join_conditions.uses
    first = conditions.build_project_join_conditions(uses)
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)
    monkeypatch.setenv("PIETTO_UNRELATED_RELATIONSHIP_CONDITION", "ignored")
    second = conditions.build_project_join_conditions(uses)

    def observation(result: conditions.ProjectJoinConditionSet) -> tuple[object, ...]:
        assert result.entries and any(
            item.mandatory_equalities for item in result.entries
        )
        return tuple(
            (
                id(item.ledger.owner),
                id(item.use),
                item.state,
                item.diagnostics,
                item.conjuncts,
                tuple(
                    (
                        id(call.call),
                        tuple(id(argument.occurrence) for argument in call.arguments),
                    )
                    for call in (
                        ()
                        if item.environment.predicate_expression is None
                        else item.environment.predicate_expression.calls
                    )
                ),
                tuple(
                    (
                        reference.position,
                        reference.state,
                        tuple(id(binding) for binding in reference.binding_candidates),
                        None
                        if reference.target is None
                        else (
                            id(reference.target.binding),
                            id(reference.target.input_field.evidence),
                        ),
                    )
                    for reference in item.references
                ),
            )
            for item in result.entries
        )

    assert observation(first) == observation(second)
    assert first.diagnostics == second.diagnostics


@pytest.mark.parametrize("dialect", ["postgres", "mysql"])
def test_unused_typed_relationship_has_zero_query_ir_and_sql_delta(
    dialect: str,
) -> None:
    program = f"""shape Row:
    id: Int
source left_rows: Row = {dialect}.table("left_rows")
source right_rows: Row = {dialect}.table("right_rows")
table selected:
    from left_rows
    select id
"""
    declaration = """relationship link(left: Row, right: Row):
    left.id == right.id
"""
    analyzed = []
    lowered = []
    for source in (program, program + declaration):
        parsed = parse_source(source)
        assert parsed.ast is not None and parsed.diagnostics == ()
        semantic = analyze(parsed.ast)
        assert semantic.diagnostics == () and semantic.script is not None
        assert semantic.model.relationship_calls == ()
        query = semantic.model.relation_symbols["selected"]
        assert isinstance(query, TableDef)
        assert query.join_clauses == ()
        assert (
            semantic.model.from_resolutions[query.from_clause]
            is semantic.model.relation_symbols["left_rows"]
        )
        analyzed.append(semantic.model.relation_row_schemas[query])
        ir = build_ir(semantic.script, semantic.model)
        assert ir.diagnostics == () and isinstance(ir.ir, ScriptIR)
        lowered.append(ir.ir)
    assert analyzed[0] == analyzed[1]
    assert lowered[0] == lowered[1]
    emit = emit_postgres_sql if dialect == "postgres" else emit_mysql_sql
    baseline, extended = (emit(item) for item in lowered)
    assert baseline.diagnostics == extended.diagnostics == ()
    assert baseline.artifacts and baseline == extended


@pytest.mark.parametrize(
    ("endpoint", "condition"),
    [
        ("orders", "order.customer_id == customer.id and order.amount == customer.id"),
        (
            "orders",
            "order.customer_id == customer.id and order.customer_id == customer.code",
        ),
        (
            "orders",
            "order.customer_id == customer.id and order.customer_id == customer.id",
        ),
        ("order_view", "order.a == customer.id and order.b == customer.code"),
    ],
    ids=["same_target", "same_source", "same_equality", "equal_source_outputs"],
)
@pytest.mark.parametrize(
    ("kind", "refinement"),
    [
        (None, False),
        *(
            (kind, refinement)
            for kind in ("inner", "left", "right", "full", "semi", "anti")
            for refinement in (False, True)
        ),
    ],
)
def test_repeated_condition_operands_check_in_every_join_kind(
    tmp_path: Path, endpoint: str, condition: str, kind: str | None, refinement: bool
) -> None:
    source = """shape Customer:
    id: Int
    code: Int
shape Order:
    id: Int
    customer_id: Int
    amount: Int
source customers: Customer = postgres.table("customers")
source orders: Order = postgres.table("orders")
query order_view:
    from orders
    select id, a = customer_id, b = customer_id
"""
    if endpoint == "orders":
        source += (
            "relationship order_customer(order: Order, customer: Customer):\n"
            + f"    {condition}\n"
        )
        match = "order_customer(orders, cust)"
    else:
        match = condition.replace("order.", "order_view.").replace("customer.", "cust.")
    source += f"query q:\n    from {endpoint}\n"
    refine = f" and {endpoint}.id == cust.id" if refinement else ""
    if kind in ("semi", "anti"):
        # A JOIN-prefix `[not] any` (a semi/anti JOIN before S6) is one hidden
        # SEMI/ANTI JOIN whose ON is the predicate; a later JOIN follows it.
        negation = "not " if kind == "anti" else ""
        source += (
            f"    let cust = customers\n"
            f"    where {negation}any({match}{refine} for cust in cust)\n"
            "    let later = customers\n    cross join later\n"
        )
    elif kind is not None:
        source += f"    let cust = customers\n    {kind} join cust on {match}{refine}\n"
    source += f"    select key = {endpoint}.id\n"
    completed = _completed(tmp_path, source)
    assert completed.ok and completed.diagnostics == ()
    if kind is None or (kind in {"inner", "left"} and not refinement):
        parsed = parse_source(source, path="main.pietto")
        assert parsed.ast is not None and parsed.diagnostics == ()
        assert analyze(parsed.ast).diagnostics == ()
    if kind is not None:
        fact = (
            completed.roots.join_conditions.entries[0]
            if kind in ("semi", "anti")
            else _named(completed, "q")
        )
        assert fact.ledger.owner.definition.name == "q"
        assert fact.ready and len(fact.conjuncts) == (3 if refinement else 2)
        expected_parts = tuple(
            operand.strip().split(".")
            for equality in condition.split(" and ")
            for operand in equality.split(" == ")
        )
        # The hidden JOIN of an `any` binds its row by its own generated name.
        bound = "_pietto_any_1" if kind in ("semi", "anti") else "cust"
        expected_parts = tuple(
            (endpoint if part[0] == "order" else bound, part[1])
            for part in expected_parts
        ) + (((endpoint, "id"), (bound, "id")) if refinement else ())
        assert (
            tuple(
                reference.expression.parts
                for reference in fact.references
                if isinstance(reference.expression, DottedNameExpr)
            )
            == expected_parts
        )
        assert len(fact.references) == len(expected_parts)
        assert len({id(reference.expression) for reference in fact.references}) == len(
            expected_parts
        )
        assert all(reference.target is not None for reference in fact.references)
        # Every conjunct is an equality of two exact field reads, whether a
        # call's body or hand-written; only the call's equalities carry it.
        assert len(fact.mandatory_equalities) == (3 if refinement else 2)
        assert [bool(item.calls) for item in fact.mandatory_equalities] == [
            endpoint == "orders"
        ] * 2 + ([False] if refinement else [])
    if endpoint == "order_view":
        facts = completed.semantic_result.module_semantic_facts
        assert facts is not None
        (view,) = tuple(
            relation
            for env in facts.environments
            for relation in env.relation_facts
            if relation.owner.identity.declared_name == "order_view"
        )
        first, second = view.select_facts[1:]
        assert first.output_name == "a" and second.output_name == "b"
        assert first.item is not second.item and first.field is not second.field
        assert first.references[0].input_field is not None
        assert first.references[0].input_field is second.references[0].input_field
        # Derived rows have no declared Shape for an unused typed predicate.
        if kind is None:
            assert completed.roots.join_conditions.entries == ()


def test_language_grouped_join_example_retains_real_key_and_match_proofs(
    tmp_path: Path,
) -> None:
    source = """shape Customer:
    id: Int
    name: Text
    customer_key = unique(id)
shape Order:
    id: Int
    customer_id: Int
    amount: Int
source customers: Customer = postgres.table("customers")
source orders: Order = postgres.table("orders")
relationship order_customer(order: Order, customer: Customer):
    order.customer_id == customer.id
query orders_per_customer:
    from orders
    let customer = customers
    inner join customer on order_customer(orders, customer)
    group by customer.name
    select:
        customer_name = customer.name
        order_count = count(orders.id)
        largest = max(orders.amount)
"""
    completed = _completed(tmp_path, source)
    assert completed.ok and completed.diagnostics == ()
    (condition,) = completed.roots.join_conditions.entries
    assert condition.ready and len(condition.mandatory_equalities) == 1
    matches = tuple(
        item
        for item in condition.key_matches
        if item.binding is condition.use.target_binding
    )
    assert len(matches) == 1
    assert matches[0].equalities == condition.mandatory_equalities
    assert matches[0].maximum.value == "at_most_one"
    assert any(item is matches[0].key for item in matches[0].properties.keys)
    equality = condition.mandatory_equalities[0]
    assert equality.calls and equality.left.input_field.evidence.name == "customer_id"
    assert equality.right.input_field.evidence.name == "id"
    definition = condition.ledger.owner.definition
    assert isinstance(definition, QueryDef)
    assert tuple(item.alias for item in definition.select_items) == (
        "customer_name",
        "order_count",
        "largest",
    )


def _project_diagnostics(root: Path, files: dict[str, str]) -> tuple[Diagnostic, ...]:
    return _completed_files(root, files).diagnostics


def _checked_both_ways(
    root: Path, source: str
) -> tuple[tuple[Diagnostic, ...], tuple[Diagnostic, ...]]:
    single = parse_source(source, path="main.pietto")
    assert single.ast is not None and single.diagnostics == ()
    return _project_diagnostics(root, {"main.pietto": source}), analyze(
        single.ast
    ).diagnostics


_CONDITION_SOURCE = """shape Customer:
    id: Int
    name: Text
    customer_key = unique(id)
shape Region:
    id: Int
source customers: Customer = postgres.table("customers")
source regions: Region = postgres.table("regions")
relationship customer_region(customer: Customer, region: Region):
    {condition}
"""
_UNUSED_QUERY = "query q:\n    from customers\n    select id\n"
_JOIN_QUERY = """query q:
    from customers
    let region = regions
    inner join region on customer_region(customers, region)
    select customer_id = customers.id
"""


@pytest.mark.parametrize("used", [False, True])
def test_valid_relationship_conditions_check_clean_in_both_modes(
    tmp_path: Path, used: bool
) -> None:
    source = _CONDITION_SOURCE.format(condition="customer.id == region.id") + (
        _JOIN_QUERY if used else _UNUSED_QUERY
    )
    assert _checked_both_ways(tmp_path, source) == ((), ())


def test_alias_enum_decimal_same_row_and_ordered_comparisons_are_valid(
    tmp_path: Path,
) -> None:
    source = """type CustomerKey = Int
enum Status:
    active
    closed
shape Customer:
    id: Int
    status: Status
    balance: Decimal(10, 2)
shape Order:
    id: Int
    customer_id: CustomerKey
    status: Status
    balance: Decimal(10, 2)
source customers: Customer = postgres.table("customers")
source orders: Order = postgres.table("orders")
relationship accepted(order: Order, customer: Customer):
    order.customer_id == customer.id and order.status == customer.status and order.balance == customer.balance and order.id == order.customer_id and order.id > customer.id
query q:
    from orders
    select id
"""
    assert _checked_both_ways(tmp_path, source) == ((), ())


def _diagnostic_at(node: Node, code: str, message: str) -> Diagnostic:
    span = node.span
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def test_invalid_templates_keep_every_error_and_the_later_valid_declaration(
    tmp_path: Path,
) -> None:
    source = """shape OrderRow:
    id: Int
    tenant_id: Int
    customer_id: Int | None
    label: Text
    payload: Json | None
    amount: Decimal(10, 2)
shape CustomerRow:
    id: Int
    tenant_id: Int
    payload: Json | None
    amount: Decimal(12, 2)
shape UnknownRow:
    mystery: MissingType | None
source orders: OrderRow = postgres.table("orders")
source customers: CustomerRow = postgres.table("customers")
source unknowns: UnknownRow = postgres.table("unknowns")
relationship unknown_field(order: OrderRow, customer: CustomerRow):
    order.missing == customer.id
relationship both_unknown_fields(order: OrderRow, customer: CustomerRow):
    order.missing == customer.missing
relationship incompatible(order: OrderRow, customer: CustomerRow):
    order.label == customer.id
relationship same_endpoint(order: OrderRow, customer: CustomerRow):
    order.id == order.customer_id
relationship unsupported_or(order: OrderRow, customer: CustomerRow):
    order.id == customer.id or order.tenant_id == customer.tenant_id
relationship residual(order: OrderRow, customer: CustomerRow):
    order.id == customer.id and len(order.label) == customer.id
relationship traversal_path(order: OrderRow, customer: CustomerRow):
    order.nested.id == customer.id
relationship literal_equality(order: OrderRow, customer: CustomerRow):
    order.id == 1
relationship greater_than(order: OrderRow, customer: CustomerRow):
    order.id > customer.id
relationship unknown_role(order: OrderRow, customer: CustomerRow):
    missing.id == customer.id
relationship deferred_builtin(order: OrderRow, customer: CustomerRow):
    order.payload == customer.payload
relationship deferred_decimal(order: OrderRow, customer: CustomerRow):
    order.amount == customer.amount
relationship unavailable_type(unknown: UnknownRow, customer: CustomerRow):
    unknown.mystery == customer.id
relationship final_valid(order: OrderRow, customer: CustomerRow):
    order.id == customer.id
query result:
    from orders
    let customer = customers
    inner join customer on final_valid(orders, customer)
    select id = orders.id
"""
    semantic = _semantic_project(tmp_path, {"main.pietto": source})
    (module,) = semantic.modules
    assert module.parsed_input is not None
    script = module.parsed_input.script
    assert tuple(item.name for item in script.relationship_templates) == (
        "unknown_field",
        "both_unknown_fields",
        "incompatible",
        "same_endpoint",
        "unsupported_or",
        "residual",
        "traversal_path",
        "literal_equality",
        "greater_than",
        "unknown_role",
        "deferred_builtin",
        "deferred_decimal",
        "unavailable_type",
        "final_valid",
    )
    declarations = {item.name: item for item in script.relationship_templates}

    def comparison(name: str) -> ComparisonExpr:
        body = declarations[name].body
        assert isinstance(body, ComparisonExpr)
        return body

    expected = (
        _diagnostic_at(
            comparison("unknown_field").left,
            "PIE-S2604",
            "Unknown relationship parameter field: order.missing",
        ),
        _diagnostic_at(
            comparison("both_unknown_fields").left,
            "PIE-S2604",
            "Unknown relationship parameter field: order.missing",
        ),
        _diagnostic_at(
            comparison("both_unknown_fields").right,
            "PIE-S2604",
            "Unknown relationship parameter field: customer.missing",
        ),
        _diagnostic_at(
            comparison("incompatible"),
            "PIE-S2105",
            "Invalid operands for operator ==: expected comparable operands",
        ),
        _diagnostic_at(
            comparison("traversal_path").left,
            "PIE-S2604",
            "Unknown relationship parameter field: order.nested.id",
        ),
        _diagnostic_at(
            comparison("unknown_role").left,
            "PIE-S2604",
            "Unknown relationship parameter field: missing.id",
        ),
    )
    catalog = ProjectRelationshipPredicateCatalog(semantic_result=semantic)
    assert catalog.diagnostics == expected
    assert tuple(
        item.declaration.name for item in catalog.templates["main.pietto"]
    ) == (
        "same_endpoint",
        "unsupported_or",
        "residual",
        "literal_equality",
        "greater_than",
        "deferred_builtin",
        "deferred_decimal",
        "unavailable_type",
        "final_valid",
    )
    assert catalog.diagnostics[1] is not catalog.diagnostics[2]
    (unknown_shape,) = tuple(
        item
        for item in script.definitions
        if isinstance(item, ShapeDef) and item.name == "UnknownRow"
    )
    unknown_type = _diagnostic_at(
        unknown_shape.fields[0].type_expr, "PIE-S2002", "Unknown type: MissingType"
    )
    assert semantic.diagnostics == (unknown_type,)
    completed = build_project_completed_semantic_result(semantic)
    assert isinstance(completed, ProjectConcreteCompletedSemanticResult)
    assert not completed.ok
    # The source whose shape has an unknown type reports only that, as in a
    # single file; before, a PIE-S2333 at the source followed.
    assert completed.diagnostics == (unknown_type, *expected)
    single = parse_source(source, path="main.pietto")
    assert single.ast is not None and single.diagnostics == ()
    assert analyze(single.ast).diagnostics == (unknown_type, *expected)
    (final_valid,) = completed.roots.join_conditions.entries
    assert final_valid.ready and final_valid.diagnostics == ()
    assert len(final_valid.mandatory_equalities) == 1
    assert (
        final_valid.mandatory_equalities[0].calls[0].template.declaration
        is declarations["final_valid"]
    )


def test_condition_types_expand_aliases_of_renamed_outputs_in_both_modes(
    tmp_path: Path,
) -> None:
    source = """type CustomerKey = Int
type OrderKey = CustomerKey
shape Customer:
    id: Int
    name: Text
shape Order:
    customer_id: CustomerKey
    order_key: OrderKey
source customers: Customer = postgres.table("customers")
source orders: Order = postgres.table("orders")
table renamed:
    from orders
    select key = customer_id
query passed:
    from renamed
    select key, again = key
query renamed_customer:
    from renamed
    let c = customers
    inner join c on renamed.key == c.id and renamed.key == c.name
    select key = renamed.key
query passed_customer:
    from passed
    let c = customers
    inner join c on passed.key == c.name and passed.again == c.name
    select key = passed.key
query chained_customer:
    from orders
    let c = customers
    inner join c on orders.order_key == c.id and orders.order_key == c.name
    select key = orders.order_key
"""
    completed = _completed(tmp_path, source)
    conditions_in_order = completed.roots.join_conditions.entries
    assert tuple(item.ledger.owner.definition.name for item in conditions_in_order) == (
        "renamed_customer",
        "passed_customer",
        "chained_customer",
    )
    assert all(
        not item.ready and item.mandatory_equalities == ()
        for item in conditions_in_order
    )
    first, passed, chained = conditions_in_order
    assert tuple(len(item.conjuncts) for item in conditions_in_order) == (2, 2, 2)
    errors = tuple(
        _diagnostic_at(
            expression,
            "PIE-S2105",
            "Invalid operands for operator ==: expected comparable operands",
        )
        for expression in (
            first.conjuncts[1],
            passed.conjuncts[0],
            passed.conjuncts[1],
            chained.conjuncts[1],
        )
    )
    assert completed.diagnostics == errors
    parsed = parse_source(source, path="main.pietto")
    assert parsed.ast is not None and parsed.diagnostics == ()
    assert analyze(parsed.ast).diagnostics == errors
    for condition in conditions_in_order:
        assert len(condition.references) == 4
        for reference in condition.references:
            assert reference.target is not None
            expected_type = (
                "Text"
                if reference.target.input_field.evidence.name == "name"
                else "Int"
            )
            assert reference.target.value_type.resolved_type.name == expected_type
    key, again = passed.references[0].target, passed.references[2].target
    assert key is not None and again is not None
    assert key.binding is again.binding
    assert key.input_field is not again.input_field
    assert (key.input_field.evidence.name, again.input_field.evidence.name) == (
        "key",
        "again",
    )
    assert key.input_field.evidence.field_def is not None
    assert key.input_field.evidence.field_def is again.input_field.evidence.field_def


def test_same_named_types_of_different_modules_retain_exact_origins(
    tmp_path: Path,
) -> None:
    files = {
        "left.pietto": """enum Status:
    open
    closed
shape Row:
    id: Int
    status: Status
source lefts: Row = postgres.table("lefts")
export source lefts
""",
        "main.pietto": """enum Status:
    open
    closed
shape Row:
    id: Int
    status: Status
source rights: Row = postgres.table("rights")
from "left.pietto" import source lefts
query pair:
    from lefts
    let r = rights
    inner join r on lefts.id == r.id and lefts.status == r.status
    select id = lefts.id
""",
    }
    completed = _completed_files(tmp_path, files)
    (condition,) = completed.roots.join_conditions.entries
    assert not completed.ok and not condition.ready
    assert len(condition.conjuncts) == 2 and len(condition.references) == 4
    expected = _diagnostic_at(
        condition.conjuncts[1],
        "PIE-S2105",
        "Invalid operands for operator ==: expected comparable operands",
    )
    assert completed.diagnostics == condition.diagnostics == (expected,)
    left, right = condition.references[2].target, condition.references[3].target
    assert left is not None and right is not None
    assert (
        left.value_type.resolved_type.name
        == right.value_type.resolved_type.name
        == "Status"
    )
    left_definition = left.value_type.resolved_type.definition
    right_definition = right.value_type.resolved_type.definition
    assert isinstance(left_definition, EnumDef) and isinstance(
        right_definition, EnumDef
    )
    assert left_definition is not right_definition
    assert (left_definition.span.path, right_definition.span.path) == (
        "left.pietto",
        "main.pietto",
    )
    for field, path, definition in (
        (left, "left.pietto", left_definition),
        (right, "main.pietto", right_definition),
    ):
        assert field.binding.target is not None
        assert field.binding.target.target_occurrence.identity.module_path == path
        (module,) = tuple(
            item for item in completed.semantic_result.modules if item.path == path
        )
        assert module.parsed_input is not None
        (declared,) = tuple(
            item
            for item in module.parsed_input.script.definitions
            if isinstance(item, EnumDef) and item.name == "Status"
        )
        assert definition is declared


@pytest.mark.parametrize(
    ("condition", "code", "message", "later_comparison"),
    [
        (
            "custx.id == region.id",
            "PIE-S2604",
            "Unknown relationship parameter field: custx.id",
            False,
        ),
        (
            "customer.region_id == region.id",
            "PIE-S2604",
            "Unknown relationship parameter field: customer.region_id",
            False,
        ),
        (
            "customer.id == region.id and customer.name == region.id",
            "PIE-S2105",
            "Invalid operands for operator ==: expected comparable operands",
            True,
        ),
    ],
    ids=["unknown_parameter", "unknown_field", "incompatible_tail"],
)
@pytest.mark.parametrize("used", [False, True])
def test_invalid_predicate_definitions_and_calls_retain_only_their_actual_errors(
    tmp_path: Path,
    condition: str,
    code: str,
    message: str,
    later_comparison: bool,
    used: bool,
) -> None:
    source = _CONDITION_SOURCE.format(condition=condition) + (
        _JOIN_QUERY if used else _UNUSED_QUERY
    )
    parsed = parse_source(source, path="main.pietto")
    assert parsed.ast is not None and parsed.diagnostics == ()
    (declaration,) = parsed.ast.relationship_templates
    if later_comparison:
        assert isinstance(declaration.body, BinaryExpr)
        offending = declaration.body.right
    else:
        assert isinstance(declaration.body, ComparisonExpr)
        offending = declaration.body.left
    primary = _diagnostic_at(offending, code, message)
    project = _project_diagnostics(tmp_path, {"main.pietto": source})
    single = analyze(parsed.ast).diagnostics
    if used:
        (query,) = tuple(
            item for item in parsed.ast.definitions if isinstance(item, QueryDef)
        )
        (join,) = query.join_clauses
        assert join.on_clause is not None
        failed_call = _diagnostic_at(
            join.on_clause.expression,
            "PIE-S2604",
            "Relationship predicate customer_region has no unambiguous checked declaration",
        )
        # The declaration's error first, in a project as in a single file.
        assert project == single == (primary, failed_call)
    else:
        assert project == single == (primary,)


@pytest.mark.parametrize("valid", [True, False])
@pytest.mark.parametrize("used", [False, True])
@pytest.mark.parametrize("command", ["check", "emit-sql"])
def test_long_predicate_keeps_every_authored_comparison_before_public_depth_refusal(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    valid: bool,
    used: bool,
    command: str,
) -> None:
    last = "customer.id" if valid else "customer.name"
    condition = " and ".join(
        ["customer.id == region.id"] * 2999 + [f"{last} == region.id"]
    )
    source = _CONDITION_SOURCE.format(condition=condition) + (
        _JOIN_QUERY if used else _UNUSED_QUERY
    )
    parsed = _parsed(tmp_path, source)
    assert parsed.ok, parsed.diagnostics
    (module,) = parsed.modules
    assert module.parsed_input is not None
    (declaration,) = module.parsed_input.script.relationship_templates
    pending = [declaration.body]
    comparisons = []
    while pending:
        expression = pending.pop()
        if isinstance(expression, BinaryExpr):
            assert expression.operator == "and"
            pending.extend((expression.right, expression.left))
        else:
            assert isinstance(expression, ComparisonExpr)
            comparisons.append(expression)
    assert len(comparisons) == len({id(item) for item in comparisons}) == 3000
    for ordinal, comparison in enumerate(comparisons):
        left_name = "name" if not valid and ordinal == 2999 else "id"
        assert comparison.operator == "=="
        assert isinstance(comparison.left, DottedNameExpr)
        assert isinstance(comparison.right, DottedNameExpr)
        assert comparison.left.parts == ("customer", left_name)
        assert comparison.right.parts == ("region", "id")
        column = 5 + ordinal * len("customer.id == region.id and ")
        assert (comparison.span.line, comparison.span.column) == (10, column)
        assert (comparison.span.end_line, comparison.span.end_column) == (
            10,
            column + len(f"customer.{left_name} == region.id"),
        )
    argv = [command, "--project", str(tmp_path), "--format", "json"]
    if command == "emit-sql":
        contract = json.loads(emission_fixture("postgres")["contract"])
        representations = {
            field["name"]: field["representation"]
            for field in contract["sources"][0]["fields"]
        }
        id_field = {
            "name": "id",
            "column": "id",
            "representation": representations["id"],
        }
        name_field = {
            "name": "name",
            "column": "name",
            "representation": representations["text"],
        }
        contract["sources"] = [
            _declared_source(
                "postgres", "customers", "customers", [id_field, name_field]
            ),
            _declared_source("postgres", "regions", "regions", [id_field]),
        ]
        contract["environment"].append(
            {"key": "identifier_case", "scope": "statement", "value": "quoted_exact"}
        )
        (tmp_path / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
        argv.extend(
            [
                "--module",
                "main.pietto",
                "--kind",
                "query",
                "--name",
                "q",
                "--dialect",
                "postgres",
                "--emission-contract",
                "contract.json",
            ]
        )
    assert cli.main(argv) == 1
    captured = capsys.readouterr()
    assert captured.err == ""
    payload = json.loads(captured.out)
    expected = {
        "code": "PIE-S2006",
        "severity": "error",
        "message": "Semantic analysis recursion limit exceeded while processing source.",
        "location": {
            "path": "main.pietto",
            "line": 1,
            "column": 1,
            "end_line": len(source.splitlines()),
            "end_column": len(source.splitlines()[-1]) + 1,
        },
        "suggestion": None,
    }
    if command == "check":
        expected["related_locations"] = []
        assert payload["ok"] is False
    else:
        assert payload["status"] == "BLOCKED" and payload["artifact"] is None
        assert payload["blockers"] == []
    assert payload["cli_errors"] == []
    assert payload["diagnostics"] == [expected]


@pytest.mark.parametrize("valid", [True, False])
@pytest.mark.parametrize("used", [False, True])
def test_bounded_predicate_checks_the_final_comparison_and_every_match_occurrence(
    tmp_path: Path, valid: bool, used: bool
) -> None:
    # This supported-depth control is separate from the 3000-term refusal cases.
    last = "customer.id" if valid else "customer.name"
    condition = " and ".join(
        ["customer.id == region.id"] * 31 + [f"{last} == region.id"]
    )
    source = _CONDITION_SOURCE.format(condition=condition) + (
        _JOIN_QUERY if used else _UNUSED_QUERY
    )
    parsed = parse_source(source, path="main.pietto")
    assert parsed.ast is not None and parsed.diagnostics == ()
    (declaration,) = parsed.ast.relationship_templates
    assert isinstance(declaration.body, BinaryExpr)
    tail = declaration.body.right
    assert isinstance(tail, ComparisonExpr)
    assert tail.span.column == 5 + 31 * len("customer.id == region.id and ")
    completed = _completed(tmp_path, source)
    single = analyze(parsed.ast).diagnostics
    if valid:
        assert completed.ok and completed.diagnostics == single == ()
        if used:
            (fact,) = completed.roots.join_conditions.entries
            assert fact.ready and len(fact.mandatory_equalities) == 32
            assert (
                len({id(item.comparison) for item in fact.mandatory_equalities}) == 32
            )
            assert tuple(
                item.conjunct_position for item in fact.mandatory_equalities
            ) == tuple(range(32))
            assert tuple(item.position for item in fact.references) == tuple(range(64))
        else:
            assert completed.roots.join_conditions.entries == ()
    else:
        primary = _diagnostic_at(
            tail,
            "PIE-S2105",
            "Invalid operands for operator ==: expected comparable operands",
        )
        assert not completed.ok
        if used:
            (query,) = tuple(
                item for item in parsed.ast.definitions if isinstance(item, QueryDef)
            )
            (join,) = query.join_clauses
            assert join.on_clause is not None
            failed_call = _diagnostic_at(
                join.on_clause.expression,
                "PIE-S2604",
                "Relationship predicate customer_region has no unambiguous checked declaration",
            )
            # The declaration's error first, in a project as in a single file.
            assert completed.diagnostics == single == (primary, failed_call)
        else:
            assert completed.diagnostics == single == (primary,)
