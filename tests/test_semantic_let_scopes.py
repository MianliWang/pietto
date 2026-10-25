from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import re
from typing import cast

import pytest

from _pietto_ir_join_differential import PRIMARY_MAIN_SOURCE, _build
from _pietto_repository_facts import REPOSITORY_FACTS
from _pietto_project_join import _parsed
from pietto._project import project_scalar_namespaces as scalar_namespaces
from pietto._project import project_scalar_references as scalar_references
from pietto._project.check import check_project_parse_only
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleCandidateBucketStatus,
)
from pietto._project.project_completed_semantics import (
    build_project_completed_semantic_result,
    ProjectConcreteCompletedSemanticResult,
)
from pietto.ast_nodes import (
    BinaryExpr,
    DottedNameExpr,
    NameExpr,
    QueryDef,
    Script,
    SourceDef,
    Span,
)
from pietto.errors import Diagnostic, Severity
from pietto.parser_api import parse_source
from pietto.semantic.let_bindings import (
    admitted_relation_let_expressions,
    analyze_relation_let_bindings,
    join_reserved_let_names,
)
from pietto.semantic.modern_inputs import normalize_query_names
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    RowField,
    RowSchema,
    TypeKind,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = REPO_ROOT / "src/pietto/_project/project_scalar_namespaces.py"
LET_PREFIX = """
shape ProfileRow:
    id: Int
    label: Text
    profile_key = unique(id)
source profiles: ProfileRow = postgres.table("profiles")
relationship customer_profiles(customer: CustomerRow, profile: ProfileRow):
    customer.id == profile.id
"""

LET_SOURCE = (
    LET_PREFIX
    + """query let_chain_join:
    from orders
    let customer = customers
    left join customer on orders_customer_unique_target(orders, customer)
    let subtotal = amount + 1
    let doubled = subtotal + customer.id
    let maybe_customer = customer.id
    select:
        doubled_value = doubled
query let_call_join:
    from customers
    let profile = profiles
    inner join profile on customer_profiles(customers, profile)
    let normalized = lower(profile.label)
    let size = len(normalized)
    select:
        normalized_value = normalized
query no_let_join:
    from orders
    let customer = customers
    left join customer on orders_customer_unique_target(orders, customer)
    select:
        amount
query self_let_join:
    from orders
    let customer = customers
    left join customer on orders_customer_unique_target(orders, customer)
    let gross = gross + amount
    select:
        amount
query self_field_let_join:
    from orders
    let customer = customers
    left join customer on orders_customer_unique_target(orders, customer)
    let amount = amount + 1
    select:
        product_id
query forward_let_join:
    from orders
    let customer = customers
    left join customer on orders_customer_unique_target(orders, customer)
    let gross = net + amount
    let net = amount
    select:
        amount
query field_shadow_let_join:
    from orders
    let customer = customers
    left join customer on orders_customer_unique_target(orders, customer)
    let amount = product_id
    select:
        product_id
query ambiguous_field_shadow_let_join:
    from orders
    let customer = customers
    left join customer on orders_customer_unique_target(orders, customer)
    let id = amount
    select:
        product_id
query relation_shadow_let_join:
    from orders
    let customer = customers
    left join customer on orders_customer_unique_target(orders, customer)
    let customers = amount
    select:
        amount
query base_relation_shadow_let_join:
    from orders
    let customer = customers
    left join customer on orders_customer_unique_target(orders, customer)
    let orders = amount
    select:
        amount
query projection_collision_let_join:
    from orders
    let customer = customers
    left join customer on orders_customer_unique_target(orders, customer)
    let gross = amount + 1
    select:
        gross = amount
query direct_selected_let_join:
    from orders
    let customer = customers
    left join customer on orders_customer_unique_target(orders, customer)
    let gross = amount + 1
    select:
        gross
query projection_alias_leak_let_join:
    from orders
    let customer = customers
    left join customer on orders_customer_unique_target(orders, customer)
    let gross = later_alias + amount
    select:
        later_alias = amount
query qualified_let_join:
    from orders
    let customer = customers
    left join customer on orders_customer_unique_target(orders, customer)
    let gross = amount + 1
    let net = orders.gross
    select:
        amount
query aggregate_let_join:
    from orders
    let customer = customers
    left join customer on orders_customer_unique_target(orders, customer)
    let gross = sum(amount)
    select:
        amount
query unknown_function_let_join:
    from orders
    let customer = customers
    left join customer on orders_customer_unique_target(orders, customer)
    let gross = not_a_builtin(amount)
    select:
        amount
query unknown_then_reference_let_join:
    from orders
    let customer = customers
    left join customer on orders_customer_unique_target(orders, customer)
    let bad = not_a_builtin(amount)
    let later = bad + 1
    select:
        amount
query invalid_operator_let_join:
    from customers
    let profile = profiles
    inner join profile on customer_profiles(customers, profile)
    let bad = profile.label + 1
    select:
        id
query hidden_name_let_join:
    from customers
    let coarse_orders = orders_by_customer
    inner join coarse_orders on customers.id == coarse_orders.customer_id
    let coarse_returns = returns_by_customer
    inner join coarse_returns on coarse_orders.customer_id == coarse_returns.customer_id
    let order_count = 1
    select:
        order_count
query hidden_lookup_let_join:
    from customers
    let coarse_orders = orders_by_customer
    inner join coarse_orders on customers.id == coarse_orders.customer_id
    let coarse_returns = returns_by_customer
    inner join coarse_returns on coarse_orders.customer_id == coarse_returns.customer_id
    let leaked = orders_by_customer.order_count
    select:
        id
"""
)

EARLY_LET_SOURCES = {
    "duplicate_let_join": """query duplicate_let_join:
    from orders
    let customer = customers
    left join customer on orders_customer_unique_target(orders, customer)
    let gross = amount + 1
    let gross = amount - 1
    select:
        amount
""",
    "binding_shadow_let_join": """query binding_shadow_let_join:
    from orders
    let customer = customers
    left join customer on orders_customer_unique_target(orders, customer)
    let customer = amount
    select:
        amount
""",
}
SINGLE_INPUT_PREFIX = """shape Order:
    id: Int
    amount: Int | None
    product_id: Int
source orders: Order = postgres.table("orders")
"""


def _joined_namespaces(
    completed: ProjectConcreteCompletedSemanticResult,
    name: str,
) -> scalar_namespaces.ProjectJoinedLetNamespaceResult:
    matches = tuple(
        readiness.namespaces
        for readiness in completed.effective_outputs.current_readiness
        if readiness.namespaces.binding_environment.ledger.owner.definition.name == name
    )
    assert len(matches) == 1
    result = matches[0]
    assert any(
        result.binding_environment.region is region
        for region in completed.effective_outputs.current_regions
    )
    return result


@pytest.fixture(scope="module")
def environments(
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, scalar_namespaces.ProjectJoinedLetNamespaceResult]:
    _, completed, _, _ = _build(
        tmp_path_factory.mktemp("joined-let-scopes") / "project",
        PRIMARY_MAIN_SOURCE + LET_SOURCE,
        reverse_creation=False,
    )
    names = tuple(
        line.removeprefix("query ").removesuffix(":")
        for line in LET_SOURCE.splitlines()
        if line.startswith("query ")
    )
    return {name: _joined_namespaces(completed, name) for name in names}


def _analyze(
    environments: dict[str, scalar_namespaces.ProjectJoinedLetNamespaceResult],
    name: str,
) -> scalar_namespaces.ProjectJoinedLetNamespaceResult:
    return environments[name]


def _reference(
    namespace: scalar_namespaces.ProjectJoinedScalarNamespace,
    expression: NameExpr | DottedNameExpr,
) -> scalar_namespaces.ProjectJoinedNamespaceReferenceResolution:
    return scalar_namespaces.resolve_project_joined_namespace_reference(
        namespace,
        scalar_references.ProjectScalarReferenceOccurrence(
            environment=namespace.binding_environment.scalar_environment,
            expression=expression,
        ),
    )


def _span(column: int) -> Span:
    return Span(
        path="slice5.pietto",
        line=1,
        column=column,
        end_line=1,
        end_column=column + 1,
    )


def _error_codes(diagnostics: tuple[Diagnostic, ...]) -> tuple[str, ...]:
    return tuple(
        diagnostic.code
        for diagnostic in diagnostics
        if diagnostic.severity is Severity.ERROR
    )


def test_namespace_chain_retains_exact_root_occurrences_and_prefixes(
    environments: dict[str, scalar_namespaces.ProjectJoinedLetNamespaceResult],
) -> None:
    environment = environments["let_chain_join"].binding_environment
    result = _analyze(environments, "let_chain_join")
    assert type(result) is scalar_namespaces.ProjectConcreteJoinedLetNamespaces
    definition = cast(QueryDef, environment.ledger.owner.definition)
    assert definition.let_clause is not None
    assert result.binding_environment is environment
    assert result.post_join_input.binding_environment is environment
    assert result.post_join_input.bindings is environment.bindings
    assert result.post_join_input.visible_fields is environment.visible_fields
    assert result.post_join_input.hidden_fields is environment.hidden_fields
    assert result.post_join_input.let_values == ()
    assert result.post_join_input.projection_aliases == ()
    assert all(
        occurrence.binding is binding
        and occurrence.owner is environment.ledger.owner
        and occurrence.source_ordinal == ordinal
        for ordinal, (occurrence, binding) in enumerate(
            zip(
                result.occurrences,
                definition.let_clause.bindings,
                strict=True,
            )
        )
    )
    assert tuple(
        tuple(value.occurrence.binding.name for value in namespace.let_values)
        for namespace in result.binding_namespaces
    ) == ((), ("subtotal",), ("subtotal", "doubled"))
    assert tuple(value.occurrence.binding.name for value in result.values) == (
        "subtotal",
        "doubled",
        "maybe_customer",
    )
    assert result.post_let.let_values is result.values
    assert result.post_let.projection_aliases == ()
    assert all(
        value.namespace is result.binding_namespaces[position]
        for position, value in enumerate(result.values)
    )
    for value in result.values:
        leaves = scalar_references.scalar_field_reference_leaves(
            value.occurrence.expression
        )
        assert len(value.resolutions) == len(leaves)
        for resolution, leaf in zip(value.resolutions, leaves, strict=True):
            assert resolution.reference.expression is leaf
            assert resolution.reference.environment is environment.scalar_environment
            assert resolution.target is not None
            assert value.value_types[leaf] is resolution.target.value_type
            if isinstance(
                resolution, scalar_namespaces.ProjectJoinedLetReferenceResolution
            ):
                assert resolution.namespace is value.namespace
                assert any(
                    resolution.target is earlier
                    for earlier in value.namespace.let_values
                )
    with pytest.raises(FrozenInstanceError):
        setattr(
            result.post_let,
            "stage",
            scalar_namespaces.ProjectScalarNamespaceStage.POST_JOIN_INPUT,
        )

    no_let = _analyze(environments, "no_let_join")
    assert type(no_let) is scalar_namespaces.ProjectConcreteJoinedLetNamespaces
    assert no_let.occurrences == ()
    assert no_let.binding_namespaces == ()
    assert no_let.post_let.let_values == ()


def test_retained_let_resolutions_are_complete_and_validation_does_not_resolve(
    environments: dict[str, scalar_namespaces.ProjectJoinedLetNamespaceResult],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _analyze(environments, "let_chain_join")
    assert isinstance(result, scalar_namespaces.ProjectConcreteJoinedLetNamespaces)
    value = result.values[1]
    assert len(value.resolutions) == 2

    def forbidden(*args, **kwargs):
        raise AssertionError("Retention checks must not resolve or infer")

    monkeypatch.setattr(
        scalar_namespaces, "resolve_project_joined_namespace_reference", forbidden
    )
    monkeypatch.setattr(scalar_namespaces, "infer_row_expression", forbidden)
    copied = replace(value)
    assert copied.resolutions is value.resolutions
    for resolutions in (
        (),
        value.resolutions[:1],
        tuple(reversed(value.resolutions)),
        (value.resolutions[0], value.resolutions[0]),
        result.values[0].resolutions,
    ):
        with pytest.raises(ValueError):
            replace(value, resolutions=resolutions)


def test_post_let_lookup_keeps_bare_let_and_qualified_field_domains_distinct(
    environments: dict[str, scalar_namespaces.ProjectJoinedLetNamespaceResult],
) -> None:
    result = _analyze(environments, "let_chain_join")
    assert type(result) is scalar_namespaces.ProjectConcreteJoinedLetNamespaces
    bare = _reference(result.post_let, NameExpr(span=_span(1), name="subtotal"))
    field = _reference(
        result.post_let,
        DottedNameExpr(span=_span(2), parts=("customer", "id")),
    )
    qualified_let = _reference(
        result.post_let,
        DottedNameExpr(span=_span(3), parts=("orders", "subtotal")),
    )
    relation_fallback = _reference(
        result.post_let,
        DottedNameExpr(span=_span(4), parts=("customers", "id")),
    )
    projection_alias = _reference(
        result.post_let,
        NameExpr(span=_span(5), name="doubled_value"),
    )
    current = _reference(
        result.binding_namespaces[0],
        NameExpr(span=_span(6), name="subtotal"),
    )
    prior = _reference(
        result.binding_namespaces[1],
        NameExpr(span=_span(7), name="subtotal"),
    )
    assert type(bare) is scalar_namespaces.ProjectJoinedLetReferenceResolution
    assert bare.target is result.values[0]
    assert type(field) is scalar_references.ProjectScalarReferenceResolution
    assert field.status is ProjectModuleCandidateBucketStatus.CONCRETE
    environment_field = result.post_let.visible_fields[-1]
    assert field.target is environment_field
    assert environment_field.evidence.name == "id"
    assert type(prior) is scalar_namespaces.ProjectJoinedLetReferenceResolution
    assert prior.target is result.values[0]
    for absent in (qualified_let, relation_fallback, projection_alias, current):
        assert type(absent) is scalar_references.ProjectScalarReferenceResolution
        assert absent.status is ProjectModuleCandidateBucketStatus.ABSENT
        assert absent.target is None


def test_type_kernel_reuse_covers_chains_calls_and_left_null_extension(
    environments: dict[str, scalar_namespaces.ProjectJoinedLetNamespaceResult],
) -> None:
    chain = _analyze(environments, "let_chain_join")
    call = _analyze(environments, "let_call_join")
    assert type(chain) is scalar_namespaces.ProjectConcreteJoinedLetNamespaces
    assert type(call) is scalar_namespaces.ProjectConcreteJoinedLetNamespaces
    assert tuple(value.value_type.resolved_type.name for value in chain.values) == (
        "Int",
        "Int",
        "Int",
    )
    assert chain.values[2].value_type.nullability is EffectiveNullability.NULLABLE
    assert tuple(value.value_type.resolved_type.name for value in call.values) == (
        "Text",
        "Int",
    )
    assert all(value.diagnostics == () for value in (*chain.values, *call.values))


def test_duplicate_let_and_input_names_reject_before_join_namespaces(
    tmp_path: Path,
) -> None:
    source = PRIMARY_MAIN_SOURCE + LET_PREFIX + "".join(EARLY_LET_SOURCES.values())
    authored = parse_source(source, path="main.pietto")
    assert authored.ast is not None and authored.diagnostics == ()
    queries = tuple(
        item
        for item in authored.ast.definitions
        if isinstance(item, QueryDef) and item.name in EARLY_LET_SOURCES
    )
    assert tuple(query.name for query in queries) == tuple(EARLY_LET_SOURCES)
    duplicate, shadowed = queries
    assert tuple(item.name for item in duplicate.naming_declarations) == (
        "customer",
        "gross",
        "gross",
    )
    assert duplicate.naming_declarations[1] is not duplicate.naming_declarations[2]
    assert tuple(item.name for item in shadowed.naming_declarations) == (
        "customer",
        "customer",
    )
    assert shadowed.naming_declarations[0] is not shadowed.naming_declarations[1]
    parsed = _parsed(tmp_path, source)
    assert not parsed.ok and parsed.errors == ()
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in parsed.diagnostics
    ] == [
        (
            "PIE-S2604",
            "Duplicate query local name: gross",
            duplicate.naming_declarations[2].span.line,
            duplicate.naming_declarations[2].span.column,
        ),
        (
            "PIE-S2604",
            "Duplicate query local name: customer",
            shadowed.naming_declarations[1].span.line,
            shadowed.naming_declarations[1].span.column,
        ),
    ]
    single = parse_source(
        SINGLE_INPUT_PREFIX
        + "query comparison:\n    from orders\n    let gross = amount + 1\n    let gross = amount - 1\n    select amount\n"
    )
    assert single.ast is not None and single.diagnostics == ()
    _, diagnostics = normalize_query_names(single.ast)
    assert [(item.code, item.message) for item in diagnostics] == [
        ("PIE-S2604", "Duplicate query local name: gross")
    ]

    duplicate_row = _parsed(
        tmp_path / "duplicate-row-local",
        """shape Row:
    id: Int
    key: Int | None
    flag: Bool | None
source rows: Row = postgres.table("rows")
query result:
    from rows
    let a = id
    let a = key
    select:
        value = a
""",
    )
    assert not duplicate_row.ok and duplicate_row.errors == ()
    assert [
        (
            item.code,
            item.severity,
            item.message,
            item.location.path,
            item.location.line,
            item.location.column,
            item.location.end_line,
            item.location.end_column,
            item.suggestion,
        )
        for item in duplicate_row.diagnostics
    ] == [
        (
            "PIE-S2604",
            Severity.ERROR,
            "Duplicate query local name: a",
            "main.pietto",
            9,
            5,
            9,
            16,
            None,
        )
    ]


def test_dependency_failures_publish_no_post_let_or_winner(
    environments: dict[str, scalar_namespaces.ProjectJoinedLetNamespaceResult],
) -> None:
    self_reference = _analyze(environments, "self_let_join")
    forward = _analyze(environments, "forward_let_join")
    self_field = _analyze(environments, "self_field_let_join")
    for result in (self_reference, forward, self_field):
        assert type(result) is scalar_namespaces.ProjectNonConcreteJoinedLetNamespaces
        assert result.post_let is None
    self_reference = cast(
        scalar_namespaces.ProjectNonConcreteJoinedLetNamespaces,
        self_reference,
    )
    forward = cast(
        scalar_namespaces.ProjectNonConcreteJoinedLetNamespaces,
        forward,
    )
    self_field = cast(
        scalar_namespaces.ProjectNonConcreteJoinedLetNamespaces,
        self_field,
    )
    assert _error_codes(self_reference.diagnostics) == ("PIE-S2330",)
    assert _error_codes(forward.diagnostics) == ("PIE-S2330",)
    assert _error_codes(self_field.diagnostics) == ("PIE-S2329", "PIE-S2330")
    assert self_field.blocking_resolutions == ()
    definition = cast(
        QueryDef,
        environments["self_field_let_join"].binding_environment.ledger.owner.definition,
    )
    assert definition.let_clause is not None
    expression = definition.let_clause.bindings[0].expression
    assert type(expression) is BinaryExpr
    assert self_field.blocked_dependency_references[0] is expression.left


@pytest.mark.parametrize(
    "name",
    (
        "field_shadow_let_join",
        "ambiguous_field_shadow_let_join",
        "relation_shadow_let_join",
        "base_relation_shadow_let_join",
    ),
)
def test_visible_fields_bindings_and_relation_names_all_block_shadowing(
    environments: dict[str, scalar_namespaces.ProjectJoinedLetNamespaceResult],
    name: str,
) -> None:
    result = _analyze(environments, name)
    assert type(result) is scalar_namespaces.ProjectNonConcreteJoinedLetNamespaces
    assert len(result.inadmissible_occurrences) == 1
    assert _error_codes(result.diagnostics) == ("PIE-S2329",)
    assert result.post_let is None


def test_explicit_intermediate_fields_block_shadowing_and_raw_relation_qualifiers(
    environments: dict[str, scalar_namespaces.ProjectJoinedLetNamespaceResult],
) -> None:
    shadowed = _analyze(environments, "hidden_name_let_join")
    blocked = _analyze(environments, "hidden_lookup_let_join")
    assert type(shadowed) is scalar_namespaces.ProjectNonConcreteJoinedLetNamespaces
    assert shadowed.post_join_input.hidden_fields == ()
    middle = tuple(
        binding
        for binding in shadowed.binding_environment.bindings
        if binding.binding.name == "coarse_orders"
    )
    assert len(middle) == 1
    assert tuple(item.evidence.name for item in middle[0].fields) == (
        "customer_id",
        "total",
        "order_count",
    )
    assert tuple(item.binding.name for item in shadowed.inadmissible_occurrences) == (
        "order_count",
    )
    assert _error_codes(shadowed.diagnostics) == ("PIE-S2329",)
    assert shadowed.post_let is None
    assert type(blocked) is scalar_namespaces.ProjectNonConcreteJoinedLetNamespaces
    assert len(blocked.blocking_resolutions) == 1
    assert (
        blocked.blocking_resolutions[0].status
        is ProjectModuleCandidateBucketStatus.ABSENT
    )
    assert blocked.blocking_resolutions[0].candidates == ()
    assert blocked.post_let is None


def test_projection_collision_alias_visibility_and_direct_selection_laws(
    environments: dict[str, scalar_namespaces.ProjectJoinedLetNamespaceResult],
) -> None:
    collision = _analyze(environments, "projection_collision_let_join")
    direct = _analyze(environments, "direct_selected_let_join")
    alias_leak = _analyze(environments, "projection_alias_leak_let_join")
    qualified = _analyze(environments, "qualified_let_join")
    assert type(collision) is scalar_namespaces.ProjectNonConcreteJoinedLetNamespaces
    assert _error_codes(collision.diagnostics) == ("PIE-S2329",)
    assert type(direct) is scalar_namespaces.ProjectConcreteJoinedLetNamespaces
    assert tuple(value.occurrence.binding.name for value in direct.values) == ("gross",)
    for result in (alias_leak, qualified):
        assert type(result) is scalar_namespaces.ProjectNonConcreteJoinedLetNamespaces
        assert len(result.blocking_resolutions) == 1
        assert (
            result.blocking_resolutions[0].status
            is ProjectModuleCandidateBucketStatus.ABSENT
        )
        assert all(
            namespace.projection_aliases == ()
            for namespace in result.binding_namespaces
        )


def test_existing_aggregate_and_kernel_diagnostics_are_retained(
    environments: dict[str, scalar_namespaces.ProjectJoinedLetNamespaceResult],
) -> None:
    aggregate = _analyze(environments, "aggregate_let_join")
    unknown_function = _analyze(environments, "unknown_function_let_join")
    invalid_operator = _analyze(environments, "invalid_operator_let_join")
    assert type(aggregate) is scalar_namespaces.ProjectNonConcreteJoinedLetNamespaces
    assert (
        type(unknown_function)
        is scalar_namespaces.ProjectNonConcreteJoinedLetNamespaces
    )
    assert (
        type(invalid_operator)
        is scalar_namespaces.ProjectNonConcreteJoinedLetNamespaces
    )
    assert _error_codes(aggregate.diagnostics) == ("PIE-S2308",)
    assert _error_codes(unknown_function.diagnostics) == ("PIE-S2103",)
    assert _error_codes(invalid_operator.diagnostics) == ("PIE-S2105",)


def test_prior_unknown_type_is_not_misclassified_as_forward_dependency(
    environments: dict[str, scalar_namespaces.ProjectJoinedLetNamespaceResult],
) -> None:
    result = _analyze(environments, "unknown_then_reference_let_join")
    assert type(result) is scalar_namespaces.ProjectNonConcreteJoinedLetNamespaces
    assert _error_codes(result.diagnostics) == ("PIE-S2103",)
    assert result.blocked_dependency_references == ()
    assert tuple(
        occurrence.binding.name for occurrence in result.unknown_type_occurrences
    ) == ("bad",)
    assert len(result.blocking_resolutions) == 1
    definition = cast(
        QueryDef,
        environments[
            "unknown_then_reference_let_join"
        ].binding_environment.ledger.owner.definition,
    )
    assert definition.let_clause is not None
    expression = definition.let_clause.bindings[1].expression
    assert type(expression) is BinaryExpr
    assert result.blocking_resolutions[0].reference.expression is expression.left


_JOINED_LET_SOURCE = """shape T:
    id: Int
    t: Text
    t_key = unique(id)
shape O:
    oid: Int
    tid: Int
    o_key = unique(oid)
source src: T = postgres.table("src")
source oth: O = postgres.table("oth")
def lk(x: Text, p: Text) -> Bool | None: return x like p
def tnn(x: Text) -> Text: return x
def inl(x: Int | None) -> Int | None: return x
"""


def _joined_let_diagnostics(
    root: Path, queries: tuple[tuple[str, str], ...]
) -> list[tuple[str, str, int, int]]:
    (root / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (root / "main.pietto").write_text(
        _JOINED_LET_SOURCE
        + "".join(
            f"query {name}:\n    from src\n    let o = oth\n"
            f"    inner join o on o.tid == src.id\n{body}"
            for name, body in queries
        ),
        encoding="utf-8",
    )
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(check_project_parse_only(root))
    )
    offset = _JOINED_LET_SOURCE.count("\n")
    return [
        (d.code, d.message, d.location.line - offset, d.location.column)
        for d in completed.diagnostics
    ]


_ESCAPE = (
    "Invalid operands for operator like: expected a pattern that does not end "
    "in the escape character ! (write !! for a literal !)"
)


def test_a_joined_let_name_bound_to_a_pattern_is_checked_as_the_pattern(
    tmp_path: Path,
) -> None:
    """A LIKE pattern read through a `let:` name of a relation with JOIN inputs
    is checked as the literal it is bound to, as without JOIN inputs, in a
    later binding, the WHERE, a SELECT item and a def argument: a pattern
    ending in an unpaired `!` is PIE-S2105 at the test. Before, it passed and
    emission wrote a pattern PostgreSQL rejects."""
    assert _joined_let_diagnostics(
        tmp_path,
        (
            (
                "in_let",
                '    let pp = "a!"\n    let m = src.t like pp\n    select:\n        id = src.id\n',
            ),
            (
                "in_where",
                '    let pp = "a!"\n    where src.t like pp\n    select:\n        id = src.id\n',
            ),
            (
                "in_select",
                '    let pp = "a!"\n    select:\n        id = src.id\n        m = src.t like pp\n',
            ),
            (
                "in_def",
                '    let pp = "a!"\n    where lk(src.t, pp)\n    select:\n        id = src.id\n',
            ),
            (
                "paired",
                '    let pp = "a!!"\n    where src.t like pp\n    select:\n        id = src.id\n',
            ),
        ),
    ) == [
        ("PIE-S2105", _ESCAPE, 6, 13),
        ("PIE-S2105", _ESCAPE, 14, 11),
        ("PIE-S2105", _ESCAPE, 24, 13),
        ("PIE-S2105", _ESCAPE, 30, 11),
    ]


def test_a_joined_null_binding_is_written_into_later_bindings(
    tmp_path: Path,
) -> None:
    """A `let:` binding of unknown type without an error of its own, such as
    `k = null`, and one that reads it, are written into a later binding's def
    argument and null test, as without JOIN inputs, so their errors are
    reported; the relation stays non-concrete, so it fails closed with
    PIE-S2333 when no binding has an error. Before, every relation here was
    PIE-S2333."""
    lets = "    let k = None\n    let w = coalesce(k, o.oid)\n"
    assert _joined_let_diagnostics(
        tmp_path,
        (
            ("unfit", f"{lets}    let v = tnn(w)\n    select:\n        x = v\n"),
            ("never", f"{lets}    let v = o.oid == k\n    select:\n        x = v\n"),
            ("closed", f"{lets}    select:\n        x = w\n"),
        ),
    ) == [
        (
            "PIE-S2395",
            "Invalid argument for def tnn at position 1 (x): expected Text, got Int",
            7,
            13,
        ),
        (
            "PIE-S2105",
            "Invalid operands for operator ==: comparison with null is never "
            "true; write `is None` instead",
            16,
            13,
        ),
        (
            "PIE-S2333",
            "Project relation semantic completion is unavailable: closed",
            19,
            1,
        ),
    ]


def test_a_joined_def_argument_reads_let_values_with_their_join_fields(
    tmp_path: Path,
) -> None:
    """With JOIN inputs, a def argument that reads a `let:` binding whose value
    reads a JOIN field and another binding is checked with the value written
    in, typed with the types of the fields it reads, as without JOIN inputs:
    in a SELECT item, a WHERE or a later binding it fits its `Int | None`
    parameter, and passed to a `Text` parameter it is PIE-S2395.
    Before, the value written in had no type for its JOIN field, so it was of
    unknown type and the relations but the WHERE one were PIE-S2333."""
    lets = "    let a = src.id\n    let c = a + o.oid\n"
    assert _joined_let_diagnostics(
        tmp_path,
        (
            ("selected", f"{lets}    select:\n        x = inl(c)\n"),
            (
                "filtered",
                f"{lets}    where inl(c) > 0\n    select:\n        x = o.oid\n",
            ),
            ("bound", f"{lets}    let d = inl(c)\n    select:\n        x = d\n"),
            ("unfit", f"{lets}    select:\n        x = tnn(c)\n"),
        ),
    ) == [
        (
            "PIE-S2395",
            "Invalid argument for def tnn at position 1 (x): expected Text, "
            "got Int of unknown nullability",
            34,
            13,
        )
    ]


def test_a_joined_def_argument_reads_join_fields_at_any_depth(
    tmp_path: Path,
) -> None:
    """A JOIN field the value of a `let:` binding reads below a part that is
    written as it is, as in `-o.oid`, `o.oid * 2`, `len(src.t)`, a condition
    or an `in` test, types that value as without JOIN inputs: a def argument
    that reads the binding fits its `Int | None` parameter, and passed to a
    `Text` parameter in a WHERE it is PIE-S2395. Before, such a value
    had no type: the relations whose argument fits but the WHERE one were
    PIE-S2333, and the unfit argument passed."""
    lets = "    let a = src.id\n"
    assert _joined_let_diagnostics(
        tmp_path,
        (
            (
                "negated",
                f"{lets}    let c = a + (-o.oid)\n    select:\n        x = inl(c)\n",
            ),
            (
                "scaled",
                f"{lets}    let c = a + o.oid * 2\n    let d = inl(c)\n"
                "    select:\n        x = d\n",
            ),
            (
                "called",
                f"{lets}    let c = a + len(src.t)\n    where inl(c) > 0\n"
                "    select:\n        x = o.oid\n",
            ),
            (
                "tested",
                f"{lets}    let c = a if not (o.oid in (1, 2)) else 0\n"
                "    select:\n        x = inl(c)\n",
            ),
            (
                "unfit",
                f"{lets}    let c = a + (-o.oid)\n    where tnn(c) is not None\n"
                "    select:\n        x = o.oid\n",
            ),
        ),
    ) == [
        (
            "PIE-S2395",
            "Invalid argument for def tnn at position 1 (x): expected Text, "
            "got Int of unknown nullability",
            41,
            11,
        )
    ]


def test_a_joined_read_of_a_null_binding_is_typed_where_it_stands(
    tmp_path: Path,
) -> None:
    """With JOIN inputs, a read of a binding bound to `null` takes its type
    from where it stands and a binding that reads one has the type of its
    value as written, as without JOIN inputs, so a later binding, SELECT item
    or WHERE that is ill-typed with those types reports its error: with
    `k = null` and `j = coalesce(k, 1)`, `d = len(j)` and `x = lower(j)` are
    PIE-S2104. Before, each relation here was a bare PIE-S2333."""
    lets = "    let k = None\n    let j = coalesce(k, 1)\n"
    assert _joined_let_diagnostics(
        tmp_path,
        (
            ("binding", f"{lets}    let d = len(j)\n    select:\n        x = o.oid\n"),
            ("selected", f"{lets}    select:\n        x = lower(j)\n"),
            (
                "filtered",
                '    let k = None\n    where coalesce(k, o.oid) == "a"\n    select:\n        x = o.oid\n',
            ),
        ),
    ) == [
        (
            "PIE-S2104",
            "Invalid argument type for function len at position 1: expected Text, "
            "got Int",
            7,
            13,
        ),
        (
            "PIE-S2104",
            "Invalid argument type for function lower at position 1: expected "
            "Text, got Int",
            17,
            13,
        ),
        (
            "PIE-S2105",
            "Invalid operands for operator ==: expected comparable operands",
            23,
            11,
        ),
    ]


def _single_input_decision(body: str) -> tuple[bool, tuple[str, ...]]:
    parsed = parse_source(
        SINGLE_INPUT_PREFIX + "query comparison:\n" + body,
        path="single-input-let.pietto",
    )
    assert parsed.ast is not None and parsed.diagnostics == ()
    script, naming_diagnostics = normalize_query_names(parsed.ast)
    assert naming_diagnostics == ()
    source = cast(SourceDef, script.definitions[-2])
    definition = cast(QueryDef, script.definitions[-1])
    int_type = ResolvedType(name="Int", kind=TypeKind.BUILTIN)
    row_schema = RowSchema(
        fields={
            name: RowField(
                name=name,
                resolved_type=int_type,
                nullability=(
                    EffectiveNullability.NULLABLE
                    if name == "amount"
                    else EffectiveNullability.NON_NULL
                ),
            )
            for name in ("id", "amount", "product_id")
        }
    )
    scopes, _, diagnostics = analyze_relation_let_bindings(
        script.definitions,
        from_resolutions={definition.from_clause: source},
        source_row_schemas={source: row_schema},
        relation_row_schemas={},
        allow_unaliased_selected_let_outputs=True,
    )
    codes = tuple(
        diagnostic.code
        for diagnostic in diagnostics
        if diagnostic.severity is Severity.ERROR
    )
    return bool(definition in scopes and not codes), codes


@pytest.mark.parametrize(
    ("joined_name", "single_body"),
    (
        (
            "self_let_join",
            "    from orders\n    let gross = gross + amount\n    select:\n        amount\n",
        ),
        (
            "forward_let_join",
            "    from orders\n    let gross = net + amount\n    let net = amount\n    select:\n        amount\n",
        ),
        (
            "field_shadow_let_join",
            "    from orders\n    let amount = product_id\n    select:\n        product_id\n",
        ),
        (
            "base_relation_shadow_let_join",
            "    from orders\n    let orders = amount\n    select:\n        amount\n",
        ),
        (
            "projection_collision_let_join",
            "    from orders\n    let gross = amount + 1\n    select:\n        gross = amount\n",
        ),
        (
            "direct_selected_let_join",
            "    from orders\n    let gross = amount + 1\n    select:\n        gross\n",
        ),
        (
            "unknown_then_reference_let_join",
            "    from orders\n    let bad = not_a_builtin(amount)\n    let later = bad + 1\n    select:\n        amount\n",
        ),
    ),
)
def test_single_input_let_decisions_match_existing_semantics(
    environments: dict[str, scalar_namespaces.ProjectJoinedLetNamespaceResult],
    joined_name: str,
    single_body: str,
) -> None:
    joined = _analyze(environments, joined_name)
    joined_codes = _error_codes(joined.diagnostics)
    existing_concrete, existing_codes = _single_input_decision(single_body)
    assert (
        type(joined) is scalar_namespaces.ProjectConcreteJoinedLetNamespaces
    ) is existing_concrete
    assert joined_codes == existing_codes


def test_slice5_scope_dependency_and_contract_are_exact() -> None:
    facts = REPOSITORY_FACTS.python(PRODUCTION)
    assert scalar_namespaces.__all__ == ()
    assert not re.search(r"^class .*Identity", facts.text, re.MULTILINE)
    for required in (
        "ProjectJoinedScalarBindingEnvironment",
        "ProjectScalarReferenceResolution",
        "infer_row_expression",
        "_dependency_diagnostics",
        "_binding_conflicts_with_projection_output",
    ):
        assert required in facts.identifiers
    for forbidden in (
        "registry",
        "cache",
        "rowschema(fields=",
        "whereclause",
        "groupbyclause",
        "windowexpr",
        "qualify",
        "executor",
        "sql",
        "arrow",
    ):
        assert forbidden not in facts.text.casefold()
    for relative in (
        "src/pietto/_project/project_scalar_bindings.py",
        "src/pietto/_project/project_scalar_references.py",
        "src/pietto/_project/module_semantic_fact_preservation.py",
        "src/pietto/semantic/let_bindings.py",
        "src/pietto/semantic/expressions.py",
    ):
        assert not any(
            name.endswith(".project_scalar_namespaces")
            for name in REPOSITORY_FACTS.python(REPO_ROOT / relative).imported_modules
        )


JOIN_LET_SOURCE = (
    "shape Order:\n"
    "    id: Int\n"
    "    customer_id: Int | None\n"
    "shape Customer:\n"
    "    id: Int\n"
    "    name: Text\n"
    "shape Region:\n"
    "    id: Int\n"
    "    label: Text\n"
    'source orders: Order = postgres.table("orders")\n'
    'source customers: Customer = postgres.table("customers")\n'
    'source regions: Region = postgres.table("regions")\n'
    "query joined:\n"
    "    from orders\n"
    "    let customer = customers\n"
    "    left join customer on orders.customer_id == customer.id\n"
    "    let name = 1\n"
    "    let id = 2\n"
    "    let customer = 3\n"
    "    let customers = 4\n"
    "    let region = 5\n"
    "    let regions = 6\n"
    "    let lost = 7\n"
    "    let label = 8\n"
    "    let total = 9\n"
    "    where any(customer.id == region.id for region in regions)"
    " and not any(orders.customer_id == lost.id for lost in customers)\n"
    "    select:\n"
    "        order_id = orders.id\n"
)


def _join_let_script() -> Script:
    """JOIN_LET_SOURCE with its names resolved: the value `let` named like the
    JOIN input is a duplicate query local name, and stays a value binding; the
    names bound only inside `any(...)` are no query local names."""

    parsed = parse_source(JOIN_LET_SOURCE, path="join-lets.pietto")
    assert parsed.ast is not None and parsed.diagnostics == ()
    script, naming_diagnostics = normalize_query_names(parsed.ast)
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in naming_diagnostics
    ] == [("PIE-S2604", "Duplicate query local name: customer", 19, 5)]
    return script


def _join_let_row(*fields: tuple[str, str], joined: bool = False) -> RowSchema:
    return RowSchema(
        fields={
            name: RowField(
                name=name,
                resolved_type=ResolvedType(name=type_name, kind=TypeKind.BUILTIN),
                nullability=EffectiveNullability.NON_NULL,
            )
            for name, type_name in fields
        },
        joined=joined,
    )


def _join_let_analysis(
    *, joined: bool
) -> tuple[QueryDef, list[str], list[tuple[str, str, int, int]]]:
    script = _join_let_script()
    orders = cast(SourceDef, script.definitions[-4])
    definition = cast(QueryDef, script.definitions[-1])
    # The tail row: FROM and the LEFT JOIN binding; an `any` row is not in it.
    tail_row = _join_let_row(
        ("orders.id", "Int"),
        ("orders.customer_id", "Int"),
        ("customer.id", "Int"),
        ("customer.name", "Text"),
        joined=True,
    )
    scopes, _, diagnostics = analyze_relation_let_bindings(
        script.definitions,
        from_resolutions={definition.from_clause: orders},
        source_row_schemas={
            orders: _join_let_row(("id", "Int"), ("customer_id", "Int"))
        },
        relation_row_schemas={},
        joined_inputs={definition: tail_row} if joined else None,
        reserved_let_names=(
            {definition: join_reserved_let_names(definition)} if joined else None
        ),
    )
    return (
        definition,
        list(scopes[definition].value_types),
        [
            (
                diagnostic.code,
                diagnostic.message,
                diagnostic.location.line,
                diagnostic.location.column,
            )
            for diagnostic in diagnostics
        ],
    )


def test_join_let_names_cannot_shadow_a_visible_field_binding_or_relation() -> None:
    definition, admitted, diagnostics = _join_let_analysis(joined=True)

    assert join_reserved_let_names(definition) == {"orders", "customer", "customers"}
    # `region`, `lost` and `regions` are bound only inside `any(...)`, and
    # `label` is a field of an `any` row only, so they stay free.
    assert admitted == ["region", "regions", "lost", "label", "total"]
    assert diagnostics == [
        ("PIE-S2329", "Let binding cannot shadow input field: name", 17, 5),
        ("PIE-S2329", "Let binding cannot shadow input field: id", 18, 5),
        ("PIE-S2329", "Let binding cannot shadow input relation: customer", 19, 5),
        ("PIE-S2329", "Let binding cannot shadow input relation: customers", 20, 5),
    ]


def test_join_let_names_keep_the_from_input_rules_without_the_join_keywords() -> None:
    _, admitted, diagnostics = _join_let_analysis(joined=False)

    assert admitted == [
        "name",
        "customer",
        "customers",
        "region",
        "regions",
        "lost",
        "label",
        "total",
    ]
    assert diagnostics == [
        ("PIE-S2329", "Let binding cannot shadow input field: id", 18, 5),
    ]


def test_admitted_join_lets_leave_out_the_reserved_names() -> None:
    definition = cast(QueryDef, _join_let_script().definitions[-1])
    tail_row = _join_let_row(("customer.name", "Text"), joined=True)

    assert list(
        admitted_relation_let_expressions(
            definition,
            tail_row,
            reserved_names=join_reserved_let_names(definition),
        )
    ) == ["id", "region", "regions", "lost", "label", "total"]
    assert list(admitted_relation_let_expressions(definition, tail_row)) == [
        "id",
        "customer",
        "customers",
        "region",
        "regions",
        "lost",
        "label",
        "total",
    ]
