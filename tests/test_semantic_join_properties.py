from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from _pietto_ir_join_differential import PRIMARY_MAIN_SOURCE, _build
from pietto._project import check as project_check
from pietto._project import project_joined_row_semantics as joined_semantics
from pietto._project import project_scalar_namespaces as scalar_namespaces
from pietto._project.model import (
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
    ProjectRowFieldNullability,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.module_attribution import (
    ProjectModuleAttributionFactSet,
    ProjectModuleProjectionKind,
    ProjectModuleRowFieldKind,
)
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
    build_project_completed_semantic_result,
)
from pietto._project.project_current_joins import (
    ProjectCurrentBinaryJoin,
    ProjectCurrentJoinGrainWitness,
)
from pietto._project.project_final_outputs import (
    ProjectCompletedEffectiveOutput,
    ProjectConcreteNoJoinReplay,
)
from pietto._project.project_ir_joins import (
    ProjectIRJoinUnavailableProperty,
)
from pietto._project.project_ir_properties import (
    ProjectIRPropertyAvailability,
    ProjectIRProvidedNullExtension,
)
from pietto._project.project_multifact import ProjectCurrentMultiFactRegion
from pietto._project.project_query_block import ProjectCurrentJoinedRowSource
from pietto._project.project_row_keys import ProjectRowUniquenessStrength


BRIDGE_SOURCE = """
query direct_renamed_orders:
    from orders
    select:
        customer_key = customer_id
        raw_amount = amount
query renamed_upstream_join:
    from customers
    let renamed = direct_renamed_orders
    inner join renamed on customers.id == renamed.customer_key
    select:
        id
query computed_orders:
    from orders
    select:
        customer_id
        adjusted = amount + 1
query computed_upstream_join:
    from customers
    let computed = computed_orders
    inner join computed on customers.id == computed.customer_id
    select:
        id
query let_orders:
    from orders
    let adjusted = amount + 1
    select:
        customer_id
        adjusted
query let_upstream_join:
    from customers
    let derived = let_orders
    inner join derived on customers.id == derived.customer_id
    select:
        id
query source_multihop_left:
    from customers
    let ordered = orders
    left join ordered on customer_orders_raw(customers, ordered)
    let returned = returns
    left join returned on composite_raw(ordered, returned)
    select:
        id
query source_multihop_full:
    from customers
    let ordered = orders
    left join ordered on customer_orders_raw(customers, ordered)
    let returned = returns
    full join returned on composite_raw(ordered, returned)
    select:
        id
query repeated_source_join:
    from customers
    let first_orders = orders
    inner join first_orders on customer_orders_raw(customers, first_orders)
    let second_orders = orders
    inner join second_orders on customer_orders_raw(customers, second_orders)
    select:
        id
query nullable_inner_join:
    from orders
    let returned = returns
    inner join returned on nullable_amounts(orders, returned)
    select:
        id
query let_attached_join:
    from orders
    let customer = customers
    left join customer on orders_customer_unique_target(orders, customer)
    let maybe_customer = customer.id
    select:
        amount
query invalid_let_stage_join:
    from orders
    let customer = customers
    left join customer on orders_customer_unique_target(orders, customer)
    let bad = bad + amount
    select:
        amount
"""


@dataclass(frozen=True, slots=True)
class _Built:
    semantic: ProjectSemanticResult
    completed: ProjectConcreteCompletedSemanticResult
    attribution: ProjectModuleAttributionFactSet
    results: dict[str, joined_semantics.ProjectJoinedRowSemanticsResult]
    namespaces: dict[str, scalar_namespaces.ProjectJoinedLetNamespaceResult]


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    semantic, completed, _, _ = _build(
        tmp_path_factory.mktemp("joined-properties") / "project",
        PRIMARY_MAIN_SOURCE + BRIDGE_SOURCE,
        reverse_creation=False,
    )
    assert isinstance(completed, ProjectConcreteCompletedSemanticResult)
    attribution = semantic.module_attribution_facts
    assert attribution is not None
    results = {
        region.ledger.owner.definition.name: result
        for region, result in zip(
            completed.effective_outputs.current_regions,
            completed.effective_outputs.current_readiness,
            strict=True,
        )
    }
    return _Built(
        semantic=semantic,
        completed=completed,
        attribution=attribution,
        results=results,
        namespaces={name: result.namespaces for name, result in results.items()},
    )


def _result(
    built: _Built,
    name: str,
) -> joined_semantics.ProjectJoinedRowSemanticsResult:
    return built.results[name]


def _concrete(
    built: _Built,
    name: str,
) -> joined_semantics.ProjectConcreteJoinedRowSemantics:
    result = _result(built, name)
    assert type(result) is joined_semantics.ProjectConcreteJoinedRowSemantics
    return result


def test_exact_current_properties_and_post_let_roots_are_retained(
    built: _Built,
) -> None:
    namespaces = built.namespaces["let_attached_join"]
    assert type(namespaces) is scalar_namespaces.ProjectConcreteJoinedLetNamespaces
    result = _concrete(built, "let_attached_join")
    (region,) = tuple(
        item
        for item in built.completed.effective_outputs.current_regions
        if item is namespaces.binding_environment.region
    )
    expected_region = result.multifact_region
    assert type(expected_region) is ProjectCurrentMultiFactRegion
    assert expected_region.region is region
    assert region.input_scope is not None
    block = namespaces.binding_environment.scalar_environment.query_block
    assert block.owner_bridge.owner is region.ledger.owner
    assert block.row_source is result.row_source
    assert type(result.row_source) is ProjectCurrentJoinedRowSource
    assert result.row_source.base_verification is built.completed.verification
    assert region.operative == tuple(
        condition
        for condition in built.completed.roots.join_conditions.entries
        if condition.ledger is region.ledger
    )
    assert all(
        join.condition is condition
        for join, condition in zip(region.joins, region.operative, strict=True)
    )
    bridge = result.property_bridge
    assert result.namespaces is namespaces
    assert result.post_let is namespaces.post_let
    assert result.let_values is namespaces.values
    assert result.row_source is namespaces.binding_environment.row_source
    assert result.final_output is result.row_source.final_output
    assert result.multifact_region is expected_region
    assert bridge.multifact_region is expected_region
    assert bridge.properties is expected_region.final_properties
    assert bridge.properties.join is result.row_source.region.joins[-1]
    assert bridge.relational is bridge.properties.relational
    assert bridge.null_extension is bridge.properties.null_extension
    assert bridge.ordering is bridge.properties.ordering
    assert bridge.keys is bridge.relational.keys
    assert bridge.fds is bridge.relational.fds
    assert bridge.fd_index is bridge.relational.fd_index
    assert bridge.grain is bridge.relational.grain
    historical = result.row_source.historical_semantic_facts.state
    assert historical.status is ProjectRelationRowSchemaStatus.DEFERRED
    assert historical.reason is ProjectRelationRowSchemaReason.AUTHORED_JOIN_DEFERRED


def test_every_final_occurrence_is_covered_once_without_duplicate_collapse(
    built: _Built,
) -> None:
    result = _concrete(built, "unique_target_left")
    scalar_fields = result.namespaces.binding_environment.scalar_environment.fields
    joined_fields = result.final_output.row_shape.fields
    property_fields = result.property_bridge.relational.fields
    assert len(result.fields) == len(scalar_fields) == len(joined_fields) == 5
    assert tuple(item.scalar_field for item in result.fields) == scalar_fields
    assert tuple(item.joined_field for item in result.fields) == joined_fields
    assert tuple(item.property_field for item in result.fields) == property_fields
    assert tuple(item.joined_field.field_position for item in result.fields) == tuple(
        range(5)
    )
    ids = tuple(
        item for item in result.fields if item.joined_field.evidence.name == "id"
    )
    assert len(ids) == 2
    assert ids[0].joined_field is not ids[1].joined_field
    assert ids[0].property_field is not ids[1].property_field
    assert ids[0].canonical_field is not ids[1].canonical_field


def test_nullability_coheres_for_original_inner_left_and_transitive_cases(
    built: _Built,
) -> None:
    inner = _concrete(built, "nullable_inner_join")
    matched_amounts = tuple(
        item for item in inner.fields if item.joined_field.evidence.name == "amount"
    )
    assert len(matched_amounts) == 2
    assert all(
        item.joined_field.evidence.nullability is ProjectRowFieldNullability.NULLABLE
        and item.effective_nullability is ProjectRowFieldNullability.NON_NULL
        and item.scalar_field.value_type.nullability.value
        == item.effective_nullability.value
        for item in matched_amounts
    )

    left = _concrete(built, "let_attached_join")
    base_amount = next(
        item
        for item in left.fields
        if item.joined_field.evidence.name == "amount" and not item.nulling_joins
    )
    target_id = left.fields[-1]
    assert (
        base_amount.joined_field.evidence.nullability
        is ProjectRowFieldNullability.NULLABLE
    )
    assert base_amount.effective_nullability is ProjectRowFieldNullability.NULLABLE
    assert (
        target_id.joined_field.evidence.nullability
        is ProjectRowFieldNullability.NON_NULL
    )
    assert target_id.effective_nullability is ProjectRowFieldNullability.NULLABLE
    assert len(target_id.nulling_joins) == 1

    multihop = _concrete(built, "source_multihop_left")
    assert (
        type(multihop.property_bridge.null_extension) is ProjectIRProvidedNullExtension
    )
    nulled = tuple(item for item in multihop.fields if item.nulling_joins)
    assert nulled
    assert all(
        item.effective_nullability is ProjectRowFieldNullability.NULLABLE
        for item in nulled
    )
    first, second = multihop.row_source.region.joins
    assert isinstance(first, ProjectCurrentBinaryJoin)
    assert second.left_input is first.properties.relational
    middle = multihop.fields[1:5]
    assert all(item.nulling_joins == (first.node.ref,) for item in middle)
    assert all(item.nulling_joins == (second.node.ref,) for item in multihop.fields[5:])

    full = _concrete(built, "source_multihop_full")
    first_full, second_full = full.row_source.region.joins
    assert isinstance(first_full, ProjectCurrentBinaryJoin)
    assert second_full.left_input is first_full.properties.relational
    assert all(
        item.nulling_joins == (first_full.node.ref, second_full.node.ref)
        and item.effective_nullability is ProjectRowFieldNullability.NULLABLE
        for item in full.fields[1:5]
    )

    no_nulling = _concrete(built, "unique_target_inner")
    unavailable = no_nulling.property_bridge.null_extension
    assert type(unavailable) is ProjectIRJoinUnavailableProperty
    assert unavailable.availability is ProjectIRPropertyAvailability.NOT_APPLICABLE
    assert (
        no_nulling.property_bridge.ordering.availability
        is ProjectIRPropertyAvailability.UNKNOWN
    )


ENUM_JOIN_SOURCE = """enum Status:
    active
    suspended
shape Order:
    id: Int
    customer_id: Int
    status: Status{modifier}
source orders: Order = postgres.table("orders")
shape Customer:
    id: Int
    status: Status{modifier}
source customers: Customer = postgres.table("customers")
relationship order_customer(order: Order, customer: Customer):
    order.customer_id == customer.id
{inputs}query q:
    from {left}
    let c = {right}
    {kind} join c{condition}    select:
        id = {left}.id
"""
ENUM_JOIN_ON = " on orders.customer_id == c.id\n"
ENUM_JOIN_FORMS = {
    **{
        f"{kind}_on": (kind, ENUM_JOIN_ON)
        for kind in ("inner", "left", "right", "full", "semi", "anti")
    },
    "cross": ("cross", "\n"),
    **{
        f"{kind}_predicate": (kind, " on order_customer(orders, c)\n")
        for kind in ("inner", "left", "right", "full", "semi", "anti")
    },
}


def _completed_diagnostics(root: Path, source: str) -> list[tuple[str, str, int, int]]:
    root.mkdir(parents=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
    )
    (root / "main.pietto").write_text(source)
    parsed = project_check.check_project_parse_only(root)
    assert parsed.ok
    located = []
    for item in build_project_completed_semantic_result(
        build_empty_project_semantic_result(parsed)
    ).diagnostics:
        assert item.location is not None
        located.append(
            (item.code, item.message, item.location.line, item.location.column)
        )
    return located


@pytest.mark.parametrize("form", ENUM_JOIN_FORMS)
def test_an_enum_field_joins_whatever_its_declared_nullability(
    tmp_path: Path, form: str
) -> None:
    # Scalar typing reads an enum field as its enum, as a single file does,
    # whatever the JOIN makes of the field: the JOIN completes, and so does a
    # read of the field after it, for every modifier. `semi` and `anti` are
    # the tail `any` and `not any` tests over the same relation and predicate.
    kind, condition = ENUM_JOIN_FORMS[form]
    reads = ("orders.status",) + (() if kind in {"semi", "anti"} else ("c.status",))
    for position, modifier in enumerate(("", " | None")):
        source = ENUM_JOIN_SOURCE.format(
            modifier=modifier,
            inputs="",
            left="orders",
            kind=kind,
            right="customers",
            condition=condition,
        )
        if kind in {"semi", "anti"}:
            negation = "not " if kind == "anti" else ""
            predicate = condition.removeprefix(" on ").removesuffix("\n")
            source = source.replace(
                f"    {kind} join c{condition}",
                f"    where {negation}any({predicate} for c in c)\n",
            )
        assert _completed_diagnostics(tmp_path / f"{position}", source) == []
        for ordinal, read in enumerate(reads):
            assert (
                _completed_diagnostics(
                    tmp_path / f"{position}-{ordinal}", f"{source}        s = {read}\n"
                )
                == []
            )


@pytest.mark.parametrize("kind", ("inner", "left", "full", "cross"))
@pytest.mark.parametrize(
    "relation",
    [
        "table b:\n    from orders\n    select:\n        id\n        status\n",
        "table b:\n    from orders\n    group by:\n        id\n        status\n"
        "    select:\n        id\n        status\n        n = count()\n",
    ],
    ids=("selected", "grouped"),
)
def test_a_relation_output_with_an_enum_field_joins_whatever_its_nullability(
    tmp_path: Path, kind: str, relation: str
) -> None:
    condition = "\n" if kind == "cross" else " on b.id == c.id\n"
    for position, modifier in enumerate(("", " | None")):
        source = ENUM_JOIN_SOURCE.format(
            modifier=modifier,
            inputs=relation,
            left="b",
            kind=kind,
            right="b",
            condition=condition,
        )
        assert _completed_diagnostics(tmp_path / f"{position}", source) == []
        assert (
            _completed_diagnostics(
                tmp_path / f"{position}-read", f"{source}        s = c.status\n"
            )
            == []
        )


ENUM_GROUPED = "    group by:\n        orders.id\n        c.status\n"
ENUM_WINDOW = "        rn = row_number() window(partition by {} order by {})\n"
ENUM_LET = (
    "query q:\n    let x:\n        from orders\n        select:\n"
    "            id\n            customer_id\n            status\n"
)
# (before SELECT, after its first output, expected diagnostics) per read of
# c.status after a LEFT JOIN, as docs/language.md states them: each is checked
# as a single file checks a read of an enum field.
ENUM_JOINED_READS = {
    "where_is_null": ("    where c.status is None\n", "", []),
    "where_comparisons": (
        '    where c.status == "active" or c.id > 0\n',
        "",
        [],
    ),
    "where_coalesce": (
        '    where coalesce(c.status, "x") == "active"\n',
        "",
        [
            (
                "PIE-S2104",
                "Invalid argument types for function coalesce: expected same "
                "canonical type",
                'coalesce(c.status, "x")',
            )
        ],
    ),
    "select_comparison": ("", '        v = c.status != "active"\n', []),
    "let_test": ("    let v = c.status is not None\n", "", []),
    "order_comparison": ("", '    order by:\n        c.status >= "active"\n', []),
    # Before: a literal that is not a label of the enum was not checked.
    "order_comparison_not_a_label": (
        "",
        '    order by:\n        c.status >= "b"\n',
        [
            (
                "PIE-S2105",
                "Invalid operands for operator >=: expected comparable operands",
                'c.status >= "b"',
            )
        ],
    ),
    "group_key": (ENUM_GROUPED, "        n = count()\n", []),
    # Before: a list of labels was refused, as if each label were Text.
    "where_in": ('    where c.status in ("active", "suspended")\n', "", []),
    "where_in_not_a_label": (
        '    where c.status in ("active", "gone")\n',
        "",
        [
            (
                "PIE-S2105",
                "Invalid operands for operator in: expected same canonical "
                "membership operands",
                'c.status in ("active", "gone")',
            )
        ],
    ),
    "where_between": (
        '    where "active" <= c.status <= "suspended"\n',
        "",
        [],
    ),
    "where_between_not_labels": (
        '    where "a" <= c.status <= "z"\n',
        "",
        [
            (
                "PIE-S2105",
                "Invalid operands for operator between: expected comparable operands",
                '"a" <= c.status <= "z"',
            )
        ],
    ),
    "where_not_like": (
        '    where c.status not like "a%"\n',
        "",
        [
            (
                "PIE-S2105",
                "Invalid operands for operator not like: expected Text operands",
                'c.status not like "a%"',
            )
        ],
    ),
    "select_call": (
        "",
        "        v = lower(c.status)\n",
        [
            (
                "PIE-S2104",
                "Invalid argument type for function lower at position 1: "
                "expected Text, got Status",
                "lower(c.status)",
            )
        ],
    ),
    "order_field": ("", "    order by:\n        c.status\n", []),
    # The joined row has two `Status` fields; their equal type symbols are no
    # conflict, so an output of that enum is typed as with one.
    "group_key_selected": (
        ENUM_GROUPED,
        "        v = c.status\n        n = count()\n",
        [],
    ),
    "let_selected": ("    let e = c.status\n", "        v = e\n", []),
    "computed_selected": (
        "",
        "        v = coalesce(c.status, orders.status)\n",
        [],
    ),
    "aggregate": (
        "    group by:\n        orders.id\n",
        "        n = count(c.status)\n",
        [
            (
                "PIE-S2314",
                "Aggregate function count expects concrete non-Any field "
                "argument, got Status",
                "count(c.status)",
            )
        ],
    ),
    "window_partition": ("", ENUM_WINDOW.format("c.status", "orders.id"), []),
    "window_order": ("", ENUM_WINDOW.format("orders.id", "c.status"), []),
}


@pytest.mark.parametrize("read", ENUM_JOINED_READS)
def test_after_a_join_an_enum_field_reads_as_its_enum(
    tmp_path: Path, read: str
) -> None:
    before, after, expected = ENUM_JOINED_READS[read]
    for position, modifier in enumerate(("", " | None")):
        source = ENUM_JOIN_SOURCE.format(
            modifier=modifier,
            inputs="",
            left="orders",
            kind="left",
            right="customers",
            condition=ENUM_JOIN_ON + before,
        )
        source += after
        located = []
        for code, message, expression in expected:
            assert source.count(expression) == 1
            offset = source.index(expression)
            line = source[:offset].count("\n") + 1
            column = offset - source.rfind("\n", 0, offset)
            located.append((code, message, line, column))
        assert _completed_diagnostics(tmp_path / f"{position}", source) == located


@pytest.mark.parametrize(
    ("left", "right", "condition"),
    [
        ("x", "customers", " on x.customer_id == c.id\n"),
        ("customers", "x", " on customers.id == c.customer_id\n"),
    ],
    ids=("from", "target"),
)
def test_a_relation_let_with_an_enum_field_is_a_join_input(
    tmp_path: Path, left: str, right: str, condition: str
) -> None:
    # Its enum field is typed, so its rows complete as a JOIN input, with the
    # field or without it.
    for position, modifier in enumerate(("", " | None")):
        source = ENUM_JOIN_SOURCE.format(
            modifier=modifier,
            inputs="",
            left=left,
            kind="inner",
            right=right,
            condition=condition,
        ).replace("query q:\n", ENUM_LET)
        assert _completed_diagnostics(tmp_path / f"{position}", source) == []
        without_field = source.replace("            status\n", "")
        assert _completed_diagnostics(tmp_path / f"{position}-", without_field) == []


def test_source_and_renamed_relation_lineage_reuse_exact_attribution(
    built: _Built,
) -> None:
    source = _concrete(built, "source_multihop_left")
    assert all(
        item.canonical_field.kind is ProjectModuleRowFieldKind.SOURCE_FIELD
        and item.source_origin is not None
        and item.source_origin.source_field is item.canonical_field
        and item.output_attribution is None
        and item.lineage is not None
        and item.lineage.paths[0].root_field is item.canonical_field
        for item in source.fields
    )
    assert all(item.source_roots == (item.canonical_field,) for item in source.fields)

    renamed = _concrete(built, "renamed_upstream_join")
    relation_fields = tuple(
        item
        for item in renamed.fields
        if item.canonical_field.kind is ProjectModuleRowFieldKind.RELATION_OUTPUT
    )
    assert tuple(item.canonical_field.name for item in relation_fields) == (
        "customer_key",
        "raw_amount",
    )
    assert all(
        item.output_attribution is not None
        and item.output_attribution.identity is item.canonical_field
        and built.attribution.find_relation_output_field(item.canonical_field)
        == (item.output_attribution,)
        for item in relation_fields
    )
    assert relation_fields[0].lineage is not None
    assert relation_fields[1].lineage is not None
    assert (
        relation_fields[0].lineage.paths[0].hops[0].projection_kind
        is ProjectModuleProjectionKind.RENAMED
    )
    assert (
        relation_fields[1].lineage.paths[0].hops[0].projection_kind
        is ProjectModuleProjectionKind.RENAMED
    )


@pytest.mark.parametrize(
    "name, producer",
    (
        ("computed_upstream_join", "computed_orders"),
        ("let_upstream_join", "let_orders"),
    ),
)
def test_computed_and_let_inputs_retain_completed_field_authority(
    built: _Built, name: str, producer: str
) -> None:
    result = _concrete(built, name)
    (entry,) = tuple(
        item
        for item in built.completed.effective_outputs.entries
        if item.owner.definition.name == producer
    )
    assert type(entry) is ProjectCompletedEffectiveOutput
    assert type(entry.root) is ProjectConcreteNoJoinReplay
    assert entry.root.owner is entry.owner
    assert entry.root.base_entry is entry.base_entry
    assert entry.dependencies is entry.base_entry.dependencies
    assert not entry.schema.is_unknown
    fields = result.fields[1:]
    (historical,) = built.attribution.find_row_lineage(fields[0].canonical_field.owner)
    assert historical.status is not ProjectRelationRowSchemaStatus.CONCRETE
    assert tuple(item.canonical_field.name for item in fields) == (
        "customer_id",
        "adjusted",
    )
    for item, original in zip(fields, entry.fields, strict=True):
        current = item.current_input
        assert current is not None
        assert current.authority.entry is entry
        assert current.original is original
        assert original.owner is entry.owner
        assert (
            current.evidence
            is entry.schema.fields[original.output_name]
            is original.field
        )
        assert item.canonical_field is original.identity
        assert item.lineage is item.source_roots is item.output_attribution is None
    assert type(result.row_source) is ProjectCurrentJoinedRowSource
    (condition,) = result.row_source.region.operative
    # The hand-written equality matches the declared customer key, not a key
    # of the derived input.
    (equality,) = condition.mandatory_equalities
    assert equality.calls == () and equality.left.binding.name == "customers"
    (match,) = condition.key_matches
    assert match.binding is equality.left.binding and match.equalities == (equality,)


def test_repeated_and_unselected_occurrences_keep_distinct_rows_and_shared_roots(
    built: _Built,
) -> None:
    repeated = _concrete(built, "repeated_source_join")
    environment = repeated.namespaces.binding_environment
    first = next(
        item for item in environment.bindings if item.binding.name == "first_orders"
    )
    second = next(
        item for item in environment.bindings if item.binding.name == "second_orders"
    )
    first_semantics = tuple(
        item
        for item in repeated.fields
        if any(item.scalar_field is field for field in first.fields)
    )
    second_semantics = tuple(
        item
        for item in repeated.fields
        if any(item.scalar_field is field for field in second.fields)
    )
    assert len(first_semantics) == len(second_semantics) == 4
    for left, right in zip(first_semantics, second_semantics, strict=True):
        assert left.joined_field is not right.joined_field
        assert left.property_field is not right.property_field
        assert left.introduction_use is not right.introduction_use
        assert left.canonical_field is right.canonical_field
        assert left.source_roots == right.source_roots

    multihop = _concrete(built, "source_multihop_left")
    environment = multihop.namespaces.binding_environment
    assert environment.hidden_fields == ()
    (middle,) = tuple(
        item for item in environment.bindings if item.binding.name == "ordered"
    )
    unselected = tuple(
        item
        for item in multihop.fields
        if any(item.scalar_field is field for field in middle.fields)
    )
    assert tuple(item.scalar_field for item in unselected) == middle.fields
    assert len(unselected) == 4
    assert all(item.lineage is not None and item.lineage.paths for item in unselected)
    first, second = multihop.row_source.region.joins
    assert isinstance(first, ProjectCurrentBinaryJoin)
    assert second.left_input is first.properties.relational
    assert all(item.introduction_use is first.input_uses[1] for item in unselected)


def test_let_success_absence_and_failure_attach_without_partial_stage(
    built: _Built,
) -> None:
    with_let = built.namespaces["let_attached_join"]
    no_let = built.namespaces["unique_target_left"]
    invalid = built.namespaces["invalid_let_stage_join"]
    assert type(with_let) is scalar_namespaces.ProjectConcreteJoinedLetNamespaces
    assert type(no_let) is scalar_namespaces.ProjectConcreteJoinedLetNamespaces
    assert type(invalid) is scalar_namespaces.ProjectNonConcreteJoinedLetNamespaces
    assert _concrete(built, "let_attached_join").post_let is with_let.post_let
    no_let_result = _concrete(built, "unique_target_left")
    assert no_let_result.post_let is no_let.post_let
    assert no_let_result.let_values == ()
    blocked = _result(built, "invalid_let_stage_join")
    assert type(blocked) is joined_semantics.ProjectNonConcreteJoinedRowSemantics
    assert (
        blocked.reason
        is joined_semantics.ProjectJoinedRowSemanticsNonConcreteReason.LET_NAMESPACE_NON_CONCRETE
    )
    assert blocked.upstream_blocker is invalid
    assert blocked.post_let is None
    assert blocked.property_bridge is None
    assert blocked.fields == ()


def test_historical_join_owner_never_receives_new_field_identity_or_state(
    built: _Built,
) -> None:
    result = _concrete(built, "let_attached_join")
    owner = result.row_source.region.ledger.owner
    historical = result.row_source.historical_semantic_facts
    assert historical.owner is owner
    assert historical.state.status is ProjectRelationRowSchemaStatus.DEFERRED
    assert (
        historical.state.reason is ProjectRelationRowSchemaReason.AUTHORED_JOIN_DEFERRED
    )
    assert (
        built.attribution.find_relation_output_fields(
            result.final_output.row_shape.relation.identity
        )
        == ()
    )
    assert all(
        item.canonical_field.owner != result.final_output.row_shape.relation.identity
        for item in result.fields
    )


def test_current_keys_fds_and_grain_keep_real_input_evidence(built: _Built) -> None:
    strict = _concrete(built, "unique_target_inner").property_bridge
    nullable = _concrete(built, "source_multihop_full").property_bridge
    assert strict.keys and all(
        key.strength is ProjectRowUniquenessStrength.STRICT for key in strict.keys
    )
    assert nullable.keys and all(
        key.strength is ProjectRowUniquenessStrength.LAX for key in nullable.keys
    )
    for bridge in (strict, nullable):
        assert bridge.fds
        assert bridge.fd_index.facts is bridge.fds
        assert all(
            fact.output is bridge.relational.output and fact.supports
            for fact in bridge.fds
        )
        assert bridge.grain.factors and bridge.grain.active
        assert all(
            any(active is factor.identity for factor in bridge.grain.factors)
            for active in bridge.grain.active
        )
        join = bridge.properties.join
        witness = bridge.grain.witness
        assert isinstance(witness, ProjectCurrentJoinGrainWitness)
        assert witness.condition is join.condition
        assert witness.left is join.left_input.grain
        assert witness.right is join.right_input.grain


def test_current_properties_reject_foreign_roots_and_field_grafts(
    built: _Built, tmp_path: Path
) -> None:
    _, foreign, _, _ = _build(
        tmp_path / "foreign",
        PRIMARY_MAIN_SOURCE + BRIDGE_SOURCE,
        reverse_creation=False,
    )
    (other,) = tuple(
        result
        for result in foreign.effective_outputs.current_readiness
        if result.namespaces.binding_environment.ledger.owner.definition.name
        == "let_attached_join"
    )
    assert type(other) is joined_semantics.ProjectConcreteJoinedRowSemantics
    local = _concrete(built, "let_attached_join")
    with pytest.raises(ValueError, match="exact"):
        replace(local.property_bridge, multifact_region=other.multifact_region)
    with pytest.raises(ValueError, match="exact"):
        replace(local.fields[0], input_field=other.fields[0].input_field)
    with pytest.raises(ValueError, match="exact"):
        replace(local.fields[0], property_field=local.fields[-1].property_field)
    with pytest.raises(ValueError, match="same project semantic root"):
        joined_semantics.build_project_joined_row_semantics(
            namespaces=local.namespaces, attribution=other.attribution
        )


def test_a_layered_join_dag_matches_grain_factors_without_a_quadratic_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Each layer joins the layer below with the one below that. Each JOIN
    # once matched every input factor against every result factor; it now
    # indexes the result factors once by value, base and retained source, so
    # the factor tests it makes grow with the grain's factors and their
    # source chains, not with their square. The grain itself still grows
    # exponentially with the layers, a known limitation deferred in the
    # roadmap, so this pins only the matching, not linear analysis.
    from pietto._project import project_ir_joins

    depth = 12
    source = (
        "shape Item:\n    id: Int\n    price: Int\n\n"
        'source items: Item = postgres.table("items")\n\n'
        "table q0:\n    from items\n    select:\n        id\n        price\n"
    ) + "".join(
        f"\ntable q{i}:\n    from q{i - 1}\n    let z = q{max(i - 2, 0)}\n"
        f"    inner join z on z.id == q{i - 1}.id\n    select:\n"
        f"        id = q{i - 1}.id\n        price = q{i - 1}.price\n"
        for i in range(1, depth + 1)
    )
    root = tmp_path / "dag"
    root.mkdir()
    (root / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
    )
    (root / "main.pietto").write_text(source)
    tests = 0
    is_join_factor = project_ir_joins._is_join_factor

    def counted(factor: object) -> bool:
        nonlocal tests
        tests += 1
        return is_join_factor(factor)

    monkeypatch.setattr(project_ir_joins, "_is_join_factor", counted)
    parsed = project_check.check_project_parse_only(root)
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(parsed)
    )
    assert isinstance(completed, ProjectConcreteCompletedSemanticResult)
    assert completed.ok and completed.diagnostics == ()
    results = {
        region.ledger.owner.definition.name: result
        for region, result in zip(
            completed.effective_outputs.current_regions,
            completed.effective_outputs.current_readiness,
            strict=True,
        )
    }
    sizes = []
    for layer in range(1, depth + 1):
        result = results[f"q{layer}"]
        assert type(result) is joined_semantics.ProjectConcreteJoinedRowSemantics
        sizes.append(len(result.property_bridge.grain.active))
    # Matching every factor against every factor made 2,630,440 tests here.
    assert tests <= 4 * depth * sum(sizes)
