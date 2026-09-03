from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
import re
from typing import cast

import pytest

from _pietto_phase62_join_differential_probe import PRIMARY_MAIN_SOURCE, _build
from _pietto_repository_facts import REPOSITORY_FACTS
from pietto._project import project_query_block as query_blocks
from pietto._project import project_scalar_bindings as scalar_bindings
from pietto._project import project_scalar_namespaces as scalar_namespaces
from pietto._project import project_scalar_references as scalar_references
from pietto._project.module_carrier import ProjectCompilationMode
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleCandidateBucketStatus,
)
from pietto._project.project_ir_joins import ProjectIRConcreteJoinRegion
from pietto._project.project_multifact import ProjectMultiFactAnalysis
from pietto._project.project_phase62_verification import (
    ProjectPhase62VerificationResult,
)
from pietto.ast_nodes import (
    BinaryExpr,
    DottedNameExpr,
    NameExpr,
    QueryDef,
    SourceDef,
    Span,
)
from pietto.errors import Diagnostic, Severity
from pietto.parser_api import parse_source
from pietto.semantic.let_bindings import analyze_relation_let_bindings
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    RowField,
    RowSchema,
    TypeKind,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = REPO_ROOT / "src/pietto/_project/project_scalar_namespaces.py"
SPEC = (
    REPO_ROOT
    / "docs/spec/phase63-slice5-let-stage-namespace-lattice-shadowing-alias-laws-v1.md"
)
LET_SOURCE = """
shape ProfileRow:
    id: Int not null
    label: Text not null
    unique profile_key on id
source profiles: ProfileRow is postgres.table("profiles")
relationship customer_profiles:
    endpoint customer: customers
    endpoint profile: profiles
    on customer.id == profile.id
query let_chain_join:
    from orders
    left join customers as customer:
        from orders
        via orders_customer_unique_target: orders -> customer
    let:
        subtotal = amount + 1
        doubled = subtotal + customer.id
        maybe_customer = customer.id
    select:
        doubled_value = doubled
query let_call_join:
    from customers
    inner join profiles as profile:
        from customers
        via customer_profiles: customer -> profile
    let:
        normalized = lower(profile.label)
        size = len(normalized)
    select:
        normalized_value = normalized
query no_let_join:
    from orders
    left join customers as customer:
        from orders
        via orders_customer_unique_target: orders -> customer
    select:
        amount
query duplicate_let_join:
    from orders
    left join customers as customer:
        from orders
        via orders_customer_unique_target: orders -> customer
    let:
        gross = amount + 1
        gross = amount - 1
    select:
        amount
query self_let_join:
    from orders
    left join customers as customer:
        from orders
        via orders_customer_unique_target: orders -> customer
    let:
        gross = gross + amount
    select:
        amount
query self_field_let_join:
    from orders
    left join customers as customer:
        from orders
        via orders_customer_unique_target: orders -> customer
    let:
        amount = amount + 1
    select:
        product_id
query forward_let_join:
    from orders
    left join customers as customer:
        from orders
        via orders_customer_unique_target: orders -> customer
    let:
        gross = net + amount
        net = amount
    select:
        amount
query field_shadow_let_join:
    from orders
    left join customers as customer:
        from orders
        via orders_customer_unique_target: orders -> customer
    let:
        amount = product_id
    select:
        product_id
query ambiguous_field_shadow_let_join:
    from orders
    left join customers as customer:
        from orders
        via orders_customer_unique_target: orders -> customer
    let:
        id = amount
    select:
        product_id
query binding_shadow_let_join:
    from orders
    left join customers as customer:
        from orders
        via orders_customer_unique_target: orders -> customer
    let:
        customer = amount
    select:
        amount
query relation_shadow_let_join:
    from orders
    left join customers as customer:
        from orders
        via orders_customer_unique_target: orders -> customer
    let:
        customers = amount
    select:
        amount
query base_relation_shadow_let_join:
    from orders
    left join customers as customer:
        from orders
        via orders_customer_unique_target: orders -> customer
    let:
        orders = amount
    select:
        amount
query projection_collision_let_join:
    from orders
    left join customers as customer:
        from orders
        via orders_customer_unique_target: orders -> customer
    let:
        gross = amount + 1
    select:
        gross = amount
query direct_selected_let_join:
    from orders
    left join customers as customer:
        from orders
        via orders_customer_unique_target: orders -> customer
    let:
        gross = amount + 1
    select:
        gross
query projection_alias_leak_let_join:
    from orders
    left join customers as customer:
        from orders
        via orders_customer_unique_target: orders -> customer
    let:
        gross = later_alias + amount
    select:
        later_alias = amount
query qualified_let_join:
    from orders
    left join customers as customer:
        from orders
        via orders_customer_unique_target: orders -> customer
    let:
        gross = amount + 1
        net = orders.gross
    select:
        amount
query aggregate_let_join:
    from orders
    left join customers as customer:
        from orders
        via orders_customer_unique_target: orders -> customer
    let:
        gross = sum(amount)
    select:
        amount
query unknown_function_let_join:
    from orders
    left join customers as customer:
        from orders
        via orders_customer_unique_target: orders -> customer
    let:
        gross = not_a_builtin(amount)
    select:
        amount
query unknown_then_reference_let_join:
    from orders
    left join customers as customer:
        from orders
        via orders_customer_unique_target: orders -> customer
    let:
        bad = not_a_builtin(amount)
        later = bad + 1
    select:
        amount
query invalid_operator_let_join:
    from customers
    inner join profiles as profile:
        from customers
        via customer_profiles: customer -> profile
    let:
        bad = profile.label + 1
    select:
        id
query hidden_name_let_join:
    from customers
    inner join returns_by_customer as returns:
        from customers
        via customer_orders_coarse: customer -> orders
        via orders_returns_aligned: orders -> returns
    let:
        order_count = 1
    select:
        order_count
query hidden_lookup_let_join:
    from customers
    inner join returns_by_customer as returns:
        from customers
        via customer_orders_coarse: customer -> orders
        via orders_returns_aligned: orders -> returns
    let:
        leaked = orders_by_customer.order_count
    select:
        id
"""
SINGLE_INPUT_PREFIX = """shape Order:
    id: Int not null
    amount: Int nullable
    product_id: Int not null
source orders: Order is postgres.table("orders")
"""
SPEC_HEADINGS = (
    "Decision And Live Authority",
    "Existing LET Authority",
    "Occurrence Identity And Name Admissibility",
    "Immutable Namespace Chain",
    "Reference Lookup And Type-Kernel Reuse",
    "Closed Non-Concrete Results",
    "Projection And Later-Stage Boundary",
    "Differential Compatibility",
    "Exact Changed-Path Closure",
    "Assurance And Publication",
    "Slice 6 Handoff",
)


def _joined_environment(
    analysis: ProjectMultiFactAnalysis,
    verification: ProjectPhase62VerificationResult,
    name: str,
) -> scalar_bindings.ProjectJoinedScalarBindingEnvironment:
    matches = tuple(
        region
        for region in analysis.join_regions.regions
        if type(region) is ProjectIRConcreteJoinRegion
        and region.ledger.owner.definition.name == name
    )
    assert len(matches) == 1
    region = matches[0]
    query_block = query_blocks.build_project_query_block_from_join_region(
        compilation_mode=ProjectCompilationMode.EXPLICIT_MODULES,
        owner=region.ledger.owner,
        verification=verification,
        region=region,
    )
    assert type(query_block) is query_blocks.ProjectConcreteQueryBlock
    scalar_environment = scalar_references.build_project_scalar_environment(query_block)
    assert (
        type(scalar_environment) is scalar_references.ProjectConcreteScalarEnvironment
    )
    return scalar_bindings.build_project_joined_scalar_binding_environment(
        scalar_environment
    )


@pytest.fixture(scope="module")
def environments(
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, scalar_bindings.ProjectJoinedScalarBindingEnvironment]:
    _, analysis, bundle, _ = _build(
        tmp_path_factory.mktemp("p63s5") / "project",
        PRIMARY_MAIN_SOURCE + LET_SOURCE,
        reverse_creation=False,
    )
    names = tuple(
        line.removeprefix("query ").removesuffix(":")
        for line in LET_SOURCE.splitlines()
        if line.startswith("query ")
    )
    return {
        name: _joined_environment(analysis, bundle.verification, name) for name in names
    }


def _analyze(
    environments: dict[str, scalar_bindings.ProjectJoinedScalarBindingEnvironment],
    name: str,
) -> scalar_namespaces.ProjectJoinedLetNamespaceResult:
    return scalar_namespaces.build_project_joined_let_namespaces(environments[name])


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
    environments: dict[str, scalar_bindings.ProjectJoinedScalarBindingEnvironment],
) -> None:
    environment = environments["let_chain_join"]
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


def test_post_let_lookup_keeps_bare_let_and_qualified_field_domains_distinct(
    environments: dict[str, scalar_bindings.ProjectJoinedScalarBindingEnvironment],
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
    environments: dict[str, scalar_bindings.ProjectJoinedScalarBindingEnvironment],
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


def test_dependency_and_duplicate_failures_publish_no_post_let_or_winner(
    environments: dict[str, scalar_bindings.ProjectJoinedScalarBindingEnvironment],
) -> None:
    duplicate = _analyze(environments, "duplicate_let_join")
    self_reference = _analyze(environments, "self_let_join")
    forward = _analyze(environments, "forward_let_join")
    self_field = _analyze(environments, "self_field_let_join")
    for result in (duplicate, self_reference, forward, self_field):
        assert type(result) is scalar_namespaces.ProjectNonConcreteJoinedLetNamespaces
        assert result.post_let is None
    duplicate = cast(
        scalar_namespaces.ProjectNonConcreteJoinedLetNamespaces,
        duplicate,
    )
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
    assert tuple(
        occurrence.source_ordinal for occurrence in duplicate.inadmissible_occurrences
    ) == (0, 1)
    assert all(namespace.let_values == () for namespace in duplicate.binding_namespaces)
    assert _error_codes(duplicate.diagnostics) == ("PIE-S2329",)
    assert _error_codes(self_reference.diagnostics) == ("PIE-S2330",)
    assert _error_codes(forward.diagnostics) == ("PIE-S2330",)
    assert _error_codes(self_field.diagnostics) == ("PIE-S2329", "PIE-S2330")
    assert self_field.blocking_resolutions == ()
    definition = cast(
        QueryDef,
        environments["self_field_let_join"].ledger.owner.definition,
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
        "binding_shadow_let_join",
        "relation_shadow_let_join",
        "base_relation_shadow_let_join",
    ),
)
def test_visible_fields_bindings_and_relation_names_all_block_shadowing(
    environments: dict[str, scalar_bindings.ProjectJoinedScalarBindingEnvironment],
    name: str,
) -> None:
    result = _analyze(environments, name)
    assert type(result) is scalar_namespaces.ProjectNonConcreteJoinedLetNamespaces
    assert len(result.inadmissible_occurrences) == 1
    assert _error_codes(result.diagnostics) == ("PIE-S2329",)
    assert result.post_let is None


def test_hidden_intermediate_names_remain_non_fields_but_may_name_a_let(
    environments: dict[str, scalar_bindings.ProjectJoinedScalarBindingEnvironment],
) -> None:
    admitted = _analyze(environments, "hidden_name_let_join")
    blocked = _analyze(environments, "hidden_lookup_let_join")
    assert type(admitted) is scalar_namespaces.ProjectConcreteJoinedLetNamespaces
    assert tuple(item.evidence.name for item in admitted.post_let.hidden_fields) == (
        "customer_id",
        "total",
        "order_count",
    )
    assert tuple(value.occurrence.binding.name for value in admitted.values) == (
        "order_count",
    )
    assert type(blocked) is scalar_namespaces.ProjectNonConcreteJoinedLetNamespaces
    assert len(blocked.blocking_resolutions) == 1
    assert (
        blocked.blocking_resolutions[0].status
        is ProjectModuleCandidateBucketStatus.ABSENT
    )
    assert blocked.post_let is None


def test_projection_collision_alias_visibility_and_direct_selection_laws(
    environments: dict[str, scalar_bindings.ProjectJoinedScalarBindingEnvironment],
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
    environments: dict[str, scalar_bindings.ProjectJoinedScalarBindingEnvironment],
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
    environments: dict[str, scalar_bindings.ProjectJoinedScalarBindingEnvironment],
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
        environments["unknown_then_reference_let_join"].ledger.owner.definition,
    )
    assert definition.let_clause is not None
    expression = definition.let_clause.bindings[1].expression
    assert type(expression) is BinaryExpr
    assert result.blocking_resolutions[0].reference.expression is expression.left


def _single_input_decision(body: str) -> tuple[bool, tuple[str, ...]]:
    parsed = parse_source(
        SINGLE_INPUT_PREFIX + "query comparison:\n" + body,
        path="single-input-let.pietto",
    )
    assert parsed.ast is not None and parsed.diagnostics == ()
    source = cast(SourceDef, parsed.ast.definitions[-2])
    definition = cast(QueryDef, parsed.ast.definitions[-1])
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
        parsed.ast.definitions,
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
            "duplicate_let_join",
            "    from orders\n"
            "    let:\n"
            "        gross = amount + 1\n"
            "        gross = amount - 1\n"
            "    select:\n"
            "        amount\n",
        ),
        (
            "self_let_join",
            "    from orders\n"
            "    let:\n"
            "        gross = gross + amount\n"
            "    select:\n"
            "        amount\n",
        ),
        (
            "forward_let_join",
            "    from orders\n"
            "    let:\n"
            "        gross = net + amount\n"
            "        net = amount\n"
            "    select:\n"
            "        amount\n",
        ),
        (
            "field_shadow_let_join",
            "    from orders\n"
            "    let:\n"
            "        amount = product_id\n"
            "    select:\n"
            "        product_id\n",
        ),
        (
            "base_relation_shadow_let_join",
            "    from orders\n"
            "    let:\n"
            "        orders = amount\n"
            "    select:\n"
            "        amount\n",
        ),
        (
            "projection_collision_let_join",
            "    from orders\n"
            "    let:\n"
            "        gross = amount + 1\n"
            "    select:\n"
            "        gross = amount\n",
        ),
        (
            "direct_selected_let_join",
            "    from orders\n"
            "    let:\n"
            "        gross = amount + 1\n"
            "    select:\n"
            "        gross\n",
        ),
        (
            "unknown_then_reference_let_join",
            "    from orders\n"
            "    let:\n"
            "        bad = not_a_builtin(amount)\n"
            "        later = bad + 1\n"
            "    select:\n"
            "        amount\n",
        ),
    ),
)
def test_single_input_let_decisions_match_existing_semantics(
    environments: dict[str, scalar_bindings.ProjectJoinedScalarBindingEnvironment],
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
    document = SPEC.read_text(encoding="utf-8")
    assert tuple(re.findall(r"^## (.+)$", document, re.MULTILINE)) == SPEC_HEADINGS
    changed_paths = tuple(
        re.findall(r"^\| `([AM])` \| `([^`]+)` \|$", document, re.MULTILINE)
    )
    assert len(changed_paths) == len(set(changed_paths)) == 7
    assert sum(status == "A" for status, _ in changed_paths) == 3
    assert sum(status == "M" for status, _ in changed_paths) == 4
    normalized = " ".join(document.split()).replace("`", "")
    for evidence in (
        "exact root plus source ordinal plus exact LetBinding AST object",
        "all occurrences of a duplicate spelling are inadmissible",
        "POST_JOIN_INPUT -> LET_BINDING(i) -> POST_LET",
        "projection alias != row/LET namespace binding",
        "compiled index != normative fact",
        "existing PIE-S2329, PIE-S2330, PIE-S2308",
        "production 166 -> 167 and tests 409 -> 410",
        "Slice 6 becomes NEXT / NOT IMPLEMENTED",
        "Slice 6 is not begun here",
    ):
        assert evidence in normalized

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
