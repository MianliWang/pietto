from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import pytest

from _pietto_ir_join_differential import PRIMARY_MAIN_SOURCE, _build
from _pietto_repository_facts import REPOSITORY_FACTS
from pietto._project import check as project_check
from pietto._project import project_joined_row_semantics as joined_semantics
from pietto._project import project_query_block as query_blocks
from pietto._project import project_scalar_bindings as scalar_bindings
from pietto._project import project_scalar_namespaces as scalar_namespaces
from pietto._project import project_scalar_references as scalar_references
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
from pietto._project.module_carrier import ProjectCompilationMode
from pietto._project.project_completed_semantics import (
    build_project_completed_semantic_result,
)
from pietto._project.project_ir_joins import (
    ProjectIRConcreteJoinRegion,
    ProjectIRJoinUnavailableProperty,
)
from pietto._project.project_ir_properties import (
    ProjectIRPropertyAvailability,
    ProjectIRProvidedNullExtension,
)
from pietto._project.project_multifact import ProjectMultiFactAnalysis
from pietto._project.project_phase62_verification import (
    ProjectPhase62VerificationResult,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = REPO_ROOT / "src/pietto/_project/project_joined_row_semantics.py"
BRIDGE_SOURCE = """
query direct_renamed_orders:
    from orders
    select:
        customer_key = customer_id
        raw_amount = amount
relationship customer_direct_renamed_orders:
    endpoint customer: customers
    endpoint renamed: direct_renamed_orders
    on customer.id == renamed.customer_key
query renamed_upstream_join:
    from customers
    inner join direct_renamed_orders as renamed:
        from customers
        via customer_direct_renamed_orders: customer -> renamed
    select:
        id
query computed_orders:
    from orders
    select:
        customer_id
        adjusted = amount + 1
relationship customer_computed_orders:
    endpoint customer: customers
    endpoint computed: computed_orders
    on customer.id == computed.customer_id
query computed_upstream_join:
    from customers
    inner join computed_orders as computed:
        from customers
        via customer_computed_orders: customer -> computed
    select:
        id
query let_orders:
    from orders
    let:
        adjusted = amount + 1
    select:
        customer_id
        adjusted
relationship customer_let_orders:
    endpoint customer: customers
    endpoint derived: let_orders
    on customer.id == derived.customer_id
query let_upstream_join:
    from customers
    inner join let_orders as derived:
        from customers
        via customer_let_orders: customer -> derived
    select:
        id
query source_multihop_left:
    from customers
    left join returns as returned:
        from customers
        via customer_orders_raw: customer -> orders
        via composite_raw: orders -> returns
    select:
        id
query repeated_source_join:
    from customers
    inner join orders as first_orders:
        from customers
        via customer_orders_raw: customer -> orders
    inner join orders as second_orders:
        from customers
        via customer_orders_raw: customer -> orders
    select:
        id
query nullable_inner_join:
    from orders
    inner join returns as returned:
        from orders
        via nullable_amounts: orders -> returns
    select:
        id
query let_attached_join:
    from orders
    left join customers as customer:
        from orders
        via orders_customer_unique_target: orders -> customer
    let:
        maybe_customer = customer.id
    select:
        amount
query invalid_let_stage_join:
    from orders
    left join customers as customer:
        from orders
        via orders_customer_unique_target: orders -> customer
    let:
        bad = bad + amount
    select:
        amount
"""


@dataclass(frozen=True, slots=True)
class _Built:
    semantic: ProjectSemanticResult
    analysis: ProjectMultiFactAnalysis
    attribution: ProjectModuleAttributionFactSet
    verification: ProjectPhase62VerificationResult
    namespaces: dict[str, scalar_namespaces.ProjectJoinedLetNamespaceResult]


def _namespace(
    analysis: ProjectMultiFactAnalysis,
    verification: ProjectPhase62VerificationResult,
    name: str,
) -> scalar_namespaces.ProjectJoinedLetNamespaceResult:
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
    bindings = scalar_bindings.build_project_joined_scalar_binding_environment(
        scalar_environment
    )
    return scalar_namespaces.build_project_joined_let_namespaces(bindings)


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    semantic, analysis, bundle, _ = _build(
        tmp_path_factory.mktemp("p63s6") / "project",
        PRIMARY_MAIN_SOURCE + BRIDGE_SOURCE,
        reverse_creation=False,
    )
    attribution = semantic.module_attribution_facts
    assert attribution is not None
    names = (
        "unique_target_inner",
        "unique_target_left",
        "direct_renamed_orders",
        "renamed_upstream_join",
        "computed_upstream_join",
        "let_upstream_join",
        "source_multihop_left",
        "repeated_source_join",
        "nullable_inner_join",
        "let_attached_join",
        "invalid_let_stage_join",
    )
    return _Built(
        semantic=semantic,
        analysis=analysis,
        attribution=attribution,
        verification=bundle.verification,
        namespaces={
            name: _namespace(analysis, bundle.verification, name)
            for name in names
            if name != "direct_renamed_orders"
        },
    )


def _result(
    built: _Built,
    name: str,
) -> joined_semantics.ProjectJoinedRowSemanticsResult:
    return joined_semantics.build_project_joined_row_semantics(
        namespaces=built.namespaces[name],
        attribution=built.attribution,
    )


def _concrete(
    built: _Built,
    name: str,
) -> joined_semantics.ProjectConcreteJoinedRowSemantics:
    result = _result(built, name)
    assert type(result) is joined_semantics.ProjectConcreteJoinedRowSemantics
    return result


def test_exact_final_property_multifact_and_post_let_roots_are_retained(
    built: _Built,
) -> None:
    namespaces = built.namespaces["let_attached_join"]
    assert type(namespaces) is scalar_namespaces.ProjectConcreteJoinedLetNamespaces
    result = _concrete(built, "let_attached_join")
    expected_region = next(
        item
        for item in built.analysis.concrete_regions
        if item.region is namespaces.binding_environment.region
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
    assert max(len(item.nulling_joins) for item in nulled) == 2

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
    id: Int not null
    customer_id: Int not null
    status: Status{modifier}
source orders: Order is postgres.table("orders")
shape Customer:
    id: Int not null
    status: Status{modifier}
source customers: Customer is postgres.table("customers")
relationship order_customer:
    endpoint order: orders
    endpoint customer: customers
    on order.customer_id == customer.id
{inputs}query q:
    from {left}
    {kind} join {right} as c:
        from {left}
{condition}    select:
        id = {left}.id
"""
ENUM_JOIN_ON = "        on orders.customer_id == c.id\n"
ENUM_JOIN_FORMS = {
    "inner_on": ("inner", ENUM_JOIN_ON),
    "left_on": ("left", ENUM_JOIN_ON),
    "right_on": ("right", ENUM_JOIN_ON),
    "full_on": ("full", ENUM_JOIN_ON),
    "semi_on": ("semi", ENUM_JOIN_ON),
    "anti_on": ("anti", ENUM_JOIN_ON),
    "cross": ("cross", ""),
    "inner_relationship": ("inner", ""),
    "left_relationship": ("left", ""),
    "right_relationship": ("right", ""),
    "full_relationship": ("full", ""),
    "semi_relationship": ("semi", ""),
    "anti_relationship": ("anti", ""),
    "left_via": ("left", "        via order_customer: order -> customer\n"),
}
ENUM_READ_UNAVAILABLE = "Project relation semantic completion is unavailable: q"


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
    # read of the field after it, for every modifier.
    kind, condition = ENUM_JOIN_FORMS[form]
    reads = ("orders.status",) + (() if kind in {"semi", "anti"} else ("c.status",))
    for position, modifier in enumerate(("", " nullable", " not null")):
        source = ENUM_JOIN_SOURCE.format(
            modifier=modifier,
            inputs="",
            left="orders",
            kind=kind,
            right="customers",
            condition=condition,
        )
        assert _completed_diagnostics(tmp_path / f"{position}", source) == []
        for ordinal, read in enumerate(reads):
            assert (
                _completed_diagnostics(
                    tmp_path / f"{position}-{ordinal}", f"{source}        s = {read}\n"
                )
                == []
            )


@pytest.mark.parametrize("kind", ("inner", "left", "right", "full", "semi", "anti"))
@pytest.mark.parametrize(
    "join",
    (
        "    {kind} join customers as c\n",
        "    {kind} join customers as c: via order_customer\n",
    ),
    ids=("inferred", "inferred_roles"),
)
def test_an_enum_field_joins_through_an_inferred_relationship_join_as_written(
    tmp_path: Path, kind: str, join: str
) -> None:
    # The JOIN that infers its source or its VIA roles completes, and so does a
    # read of the field after it, exactly as the JOIN written with `from`.
    for position, modifier in enumerate(("", " nullable", " not null")):
        written = ENUM_JOIN_SOURCE.format(
            modifier=modifier,
            inputs="",
            left="orders",
            kind=kind,
            right="customers",
            condition="",
        )
        inferred = written.replace(
            f"    {kind} join customers as c:\n        from orders\n",
            join.format(kind=kind),
        )
        assert inferred != written
        for suffix, expected in (
            ("", []),
            ("        s = orders.status\n", []),
        ):
            for name, source in (("written", written), ("inferred", inferred)):
                directory = tmp_path / f"{position}-{bool(suffix)}-{name}"
                assert _completed_diagnostics(directory, source + suffix) == expected


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
    condition = "" if kind == "cross" else "        on b.id == c.id\n"
    for position, modifier in enumerate(("", " nullable", " not null")):
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


ENUM_UNAVAILABLE_AT_QUERY = [("PIE-S2333", ENUM_READ_UNAVAILABLE, 17, 1)]
ENUM_GROUPED = "    group by:\n        orders.id\n        c.status\n"
ENUM_WINDOW = (
    "        rn = row_number() window:\n            partition by:\n"
    "                {}\n            order by:\n                {}\n"
)
ENUM_LET = (
    "query q:\n    let x:\n        from orders\n        select:\n"
    "            id\n            customer_id\n            status\n"
)
# (before SELECT, after its first output, expected diagnostics) per read of
# c.status after a LEFT JOIN, as docs/language.md states them: each is checked
# as a single file checks a read of an enum field.
ENUM_JOINED_READS = {
    "where_is_null": ("    where c.status is null\n", "", []),
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
                22,
                11,
            )
        ],
    ),
    "select_comparison": ("", '        v = c.status != "active"\n', []),
    "let_test": ("    let:\n        v = c.status is not null\n", "", []),
    "order_comparison": ("", '    order by:\n        c.status >= "b"\n', []),
    "group_key": (ENUM_GROUPED, "        n = count()\n", []),
    "where_in": (
        '    where c.status in ("active")\n',
        "",
        [
            (
                "PIE-S2105",
                "Invalid operands for operator in: expected same canonical "
                "membership operands",
                22,
                11,
            )
        ],
    ),
    "where_between": ('    where c.status between "a" and "z"\n', "", []),
    "where_not_like": (
        '    where c.status not like "a%"\n',
        "",
        [
            (
                "PIE-S2105",
                "Invalid operands for operator not like: expected Text operands",
                22,
                11,
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
                24,
                13,
            )
        ],
    ),
    "order_field": ("", "    order by:\n        c.status\n", []),
    "group_key_selected": (
        ENUM_GROUPED,
        "        v = c.status\n        n = count()\n",
        ENUM_UNAVAILABLE_AT_QUERY,
    ),
    "aggregate": (
        "    group by:\n        orders.id\n",
        "        n = count(c.status)\n",
        [
            (
                "PIE-S2314",
                "Aggregate function count expects concrete non-Any field "
                "argument, got Status",
                26,
                13,
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
    for position, modifier in enumerate(("", " nullable", " not null")):
        source = ENUM_JOIN_SOURCE.format(
            modifier=modifier,
            inputs="",
            left="orders",
            kind="left",
            right="customers",
            condition=ENUM_JOIN_ON + before,
        )
        assert (
            _completed_diagnostics(tmp_path / f"{position}", source + after) == expected
        )


@pytest.mark.parametrize(
    ("left", "right", "condition"),
    [
        ("x", "customers", "        on x.customer_id == c.id\n"),
        ("customers", "x", "        on customers.id == c.customer_id\n"),
    ],
    ids=("from", "target"),
)
def test_a_relation_let_with_an_enum_field_is_a_join_input(
    tmp_path: Path, left: str, right: str, condition: str
) -> None:
    # Its enum field is typed, so its rows complete as a JOIN input, with the
    # field or without it.
    for position, modifier in enumerate(("", " nullable", " not null")):
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


@pytest.mark.parametrize("name", ("computed_upstream_join", "let_upstream_join"))
def test_existing_nonconcrete_computed_or_let_lineage_fails_closed(
    built: _Built,
    name: str,
) -> None:
    result = _result(built, name)
    assert type(result) is joined_semantics.ProjectNonConcreteJoinedRowSemantics
    assert (
        result.reason
        is joined_semantics.ProjectJoinedRowSemanticsNonConcreteReason.UPSTREAM_LINEAGE_NON_CONCRETE
    )
    assert result.post_let is None
    assert result.property_bridge is None
    assert result.fields == ()
    assert result.lineage_issues
    assert all(
        issue.canonical_field.kind is ProjectModuleRowFieldKind.RELATION_OUTPUT
        and issue.lineage.status is not ProjectRelationRowSchemaStatus.CONCRETE
        and built.attribution.find_row_lineage(issue.canonical_field.owner)
        == (issue.lineage,)
        for issue in result.lineage_issues
    )


def test_repeated_and_hidden_occurrences_keep_distinct_rows_and_shared_roots(
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
    hidden = multihop.namespaces.binding_environment.hidden_fields
    hidden_semantics = tuple(
        item
        for item in multihop.fields
        if any(item.scalar_field is field for field in hidden)
    )
    assert tuple(item.scalar_field for item in hidden_semantics) == hidden
    assert hidden_semantics
    assert all(
        item.lineage is not None and item.lineage.paths for item in hidden_semantics
    )


def test_slice5_success_no_let_and_failure_attach_without_partial_stage(
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


def test_slice6_scope_dependency_and_contract_are_exact() -> None:
    facts = REPOSITORY_FACTS.python(PRODUCTION)
    assert joined_semantics.__all__ == ()
    assert not re.search(r"^class .*FieldIdentity", facts.text, re.MULTILINE)
    for required in (
        "ProjectIRJoinedRowField",
        "ProjectIROutputFieldOccurrence",
        "ProjectModuleRowFieldIdentity",
        "ProjectModuleRowFieldLineage",
        "ProjectMultiFactConcreteRegion",
        "ProjectIRJoinOutputProperties",
    ):
        assert required in facts.identifiers
    for forbidden in (
        "build_project_ir_join_region",
        "build_project_multifact_analysis",
        "projectrowschema",
        "dependencygraph",
        "filter",
        "grouping",
        "windowexpr",
        "qualify",
        "scheduler",
        "effective_output",
        "executor",
    ):
        assert forbidden not in facts.text.casefold()
    assert "pietto._project.row_lineage" not in facts.imported_modules
    for relative in (
        "src/pietto/_project/project_scalar_namespaces.py",
        "src/pietto/_project/project_ir_properties.py",
        "src/pietto/_project/project_ir_relational_properties.py",
        "src/pietto/_project/project_ir_joins.py",
        "src/pietto/_project/project_multifact.py",
        "src/pietto/_project/project_phase62_verification.py",
        "src/pietto/_project/module_attribution.py",
    ):
        assert not any(
            name.endswith(".project_joined_row_semantics")
            for name in REPOSITORY_FACTS.python(REPO_ROOT / relative).imported_modules
        )
