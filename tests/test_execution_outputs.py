"""General correspondence: fresh original identities, unchanged old branch."""

from dataclasses import replace
import json
import sys
from types import SimpleNamespace
from typing import cast

import pytest

from _pietto_execution_rows_cases import CASES, build
import _pietto_results_nested as nested
import _pietto_results_product as probe
from pietto._project.project_result_output import prepare_output, verify_output
from pietto._project.project_result_binding import ProducerFieldBinding, bind_producer
from pietto._project.project_result_contract import ResultError
from pietto._project.project_execution import ExecutionLimits
from pietto._project import project_execution_reader as reader
from pietto._project.project_execution_reader import bind_postgres_output
from pietto._project import project_arrow_result as scalar


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("case,variant", CASES)
def test_current_admitted_output_domain(tmp_path, target, case, variant):
    outcome = build(tmp_path, target, case, variant)
    if outcome.status == "BLOCKED":
        assert target == "mysql" and (case, variant) in (
            ("V_join_full", "null_keys"),
            ("A_window_groups", "exclude"),
        )
        return
    assert outcome.artifact is not None
    output = prepare_output(outcome.artifact)
    assert verify_output(output, outcome.artifact, output.contract) is output.columns
    assert len(output.columns) == len(outcome.artifact.request.plan.exports)
    assert all(
        c.export is f.port
        for c, f in zip(output.columns, output.contract.shape.fields, strict=True)
    )


def test_computed_metadata_and_original_damage(tmp_path):
    outcome = build(tmp_path, "postgres", "T_row_direct", "query_bind")
    artifact = outcome.artifact
    output = prepare_output(artifact)
    type_codes = {"pg_int2": 21, "pg_int4": 23, "pg_int8": 20, "pg_bool": 16}
    metadata = tuple(
        SimpleNamespace(
            name=c.label,
            type_code=type_codes[c.realization.storage["kind"]],
            null_ok=None,
        )
        for c in output.columns
    )
    binding = bind_postgres_output(output, metadata)
    assert binding.fields[
        1
    ].nullable  # original UNKNOWN is retained, never non-null proof
    assert binding.fields[1].field.nullability.value == "unknown"
    assert scalar._value(2147483648, binding.fields[1]) == 2147483648
    with pytest.raises(ResultError, match="^VALUE_DOMAIN$"):
        scalar._value(2147483649, binding.fields[1])
    with pytest.raises(ResultError, match="^VALUE_DOMAIN$"):
        scalar._value(True, binding.fields[1])
    with pytest.raises(ResultError, match="^PRODUCER_UNSUPPORTED$"):
        bind_producer(
            output.contract,
            artifact,
            tuple(cast(ProducerFieldBinding, f).observation for f in binding.fields),
        )
    for columns, code in (
        (output.columns[::-1], "COLUMNS"),
        (output.columns[:-1], "INVENTORY"),
        ((*output.columns, output.columns[0]), "INVENTORY"),
        ((output.columns[0], *output.columns[:-1]), "COLUMNS"),
        (
            (replace(output.columns[0], source_field=None), *output.columns[1:]),
            "REALIZATION",
        ),
        (
            (
                output.columns[0],
                replace(output.columns[1], source_field=output.columns[0].source_field),
                *output.columns[2:],
            ),
            "REALIZATION",
        ),
        (
            (replace(output.columns[0], terminal=artifact), *output.columns[1:]),
            "COLUMNS",
        ),
    ):
        with pytest.raises(ValueError, match="^OUTPUT_%s$" % code):
            verify_output(replace(output, columns=columns), artifact, output.contract)
    # Coordinated native description cannot certify a corrupted original range.
    real = output.columns[1].realization
    saved = dict(real.domain)
    try:
        real.domain["max"] = "9223372036854775807"
        with pytest.raises(
            ValueError,
            match="^Emission inspection requires a verified artifact: plan_ast_correspondence$",
        ):
            bind_postgres_output(output, metadata)
    finally:
        real.domain.clear()
        real.domain.update(saved)


def test_outer_join_and_set_have_result_authority(tmp_path):
    outer = prepare_output(
        build(tmp_path / "join", "postgres", "W_join_values", "left_marker").artifact
    )
    nullable = outer.columns[1]
    assert nullable.realization.nullable is True
    assert nullable.source_field is not None
    selected = prepare_output(
        build(tmp_path / "set", "postgres", "S_set_forms", "union_all").artifact
    )
    assert selected.columns[0].source_field is None
    assert len(selected.columns[0].original.inputs) == 2
    with pytest.raises(ResultError, match="^OUTPUT_INVENTORY$"):
        verify_output(
            replace(outer, units=selected.units), outer.artifact, outer.contract
        )


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("precision", (39, 65))
@pytest.mark.parametrize("state", ("values", "empty", "null"))
def test_seven_scalar_original_meanings(tmp_path, target, precision, state):
    from _pietto_execution_rows_cases import seven_artifact

    output = prepare_output(
        seven_artifact(tmp_path / "compiled", target, precision=precision, state=state)
    )
    assert {c.realization.tag for c in output.columns} == {
        "Int",
        "Bool",
        "Float",
        "Text",
        "Decimal",
        "Timestamp",
        "UUID",
    }
    for column in output.columns[:4]:
        assert column.field.meaning is not None
        assert column.field.meaning.source_port.field is column.source_field.field


def test_value_sensitive_fact_root_and_same_type_swap(tmp_path):
    import _pietto_results_product as product
    import _pietto_sql_emission as emission
    from pietto._project.project_execution_template import bind_values, prepare_template
    from pietto._project.project_execution import (
        prepare_bound_execution,
        PostgresAccess,
    )

    source = product.source("postgres").replace("renamed = id", "renamed = id + 1")
    document = json.loads(product.emission_input("postgres", lower=-10, upper=10))
    document["sources"][0]["fields"][0]["representation"]["storage"] = {
        "kind": "pg_int4"
    }
    document["environment"] += [
        {"key": "identifier_case", "scope": "statement", "value": "quoted_exact"},
        {
            "key": "parameter_protocol",
            "scope": "statement",
            "value": "postgres_extended",
        },
    ]
    _, emitted = emission.build_case(
        tmp_path / "template", source, json.dumps(document), "bind_safe_literals"
    )
    assert emitted.status == "VERIFIED" and emitted.artifact is not None
    t = prepare_template(emitted.artifact)
    a = bind_values(t, ((t.slots[0], 1),))
    b = bind_values(t, ((t.slots[0], 5),))
    output = prepare_output(a.artifact, binding=a)
    access = PostgresAccess(
        "127.0.0.1", 5432, "test", "pietto_query", "private", "disable"
    )
    with pytest.raises(ValueError, match="^ROOT$"):
        prepare_bound_execution(b, access, output=output)
    assert output.columns[0].realization.domain["max"] == "2147483648"
    assert (
        prepare_output(b.artifact, binding=b).columns[0].realization.domain["max"]
        == "2147483652"
    )
    with pytest.raises(ValueError, match="^OUTPUT_COLUMNS$"):
        verify_output(
            replace(output, columns=output.columns[::-1]),
            a.artifact,
            output.contract,
            binding=a,
        )


@pytest.mark.parametrize(
    "case,variant,damage",
    (
        ("X_aggregate_global", "bag", "count"),
        ("W_join_values", "left_marker", "outer"),
        ("S_set_forms", "union_all", "set"),
    ),
)
def test_family_authority_cannot_be_replaced_by_matching_shape(
    tmp_path, case, variant, damage
):
    output = prepare_output(build(tmp_path, "postgres", case, variant).artifact)
    if damage == "count":
        column = next(
            c for c in output.columns if c.realization.domain.get("min") == "0"
        )
        column.realization.domain["max"] = "10"
    elif damage == "outer":
        object.__setattr__(output.columns[1].realization, "nullable", False)
    else:
        original = output.columns[0].original
        object.__setattr__(original, "inputs", original.inputs[::-1])
    with pytest.raises(
        ValueError,
        match="^Emission inspection requires a verified artifact: plan_ast_correspondence$",
    ):
        verify_output(output, output.artifact, output.contract)


# -- S10: the strict pg_column_arrays_v1 decoder (Arrow-free) -----------------


@pytest.fixture(scope="module")
def collect_producer(tmp_path_factory):
    """The rows reader's binding of a real Collect: renamed, then c(i, b, t)."""
    return nested.real(probe, tmp_path_factory.mktemp("decoder") / "collect")


GOOD = (7, 2, [7, 7], [True, None], ["a", ""])
DECODED = (7, ([7, 7], [True, None], ["a", ""]))


def test_the_carrier_decodes_to_logical_nested_values(collect_producer):
    arrow = "pyarrow" in sys.modules
    rows = (GOOD, (0, 0, None, None, None), (1, 1, [5], [None], [None]))
    decoded, children = reader.decode_carrier_rows(collect_producer, rows, 3)
    # The empty collection is the count 0 with NULL arrays; an all-NULL child
    # row is still one child row.
    assert decoded == (DECODED, (0, ((), (), ())), (1, ([5], [None], [None])))
    assert children == 3
    with pytest.raises(ResultError, match="^EXECUTION_RESOURCE_LIMIT$"):
        reader.decode_carrier_rows(collect_producer, rows, 2)
    # Binding and decoding never import Arrow.
    assert ("pyarrow" in sys.modules) is arrow


CARRIER_DAMAGE = {
    "count_bool": ((7, True, [7], [True], ["a"]), "EXECUTION_CARRIER"),
    "count_text": ((7, "1", [7], [True], ["a"]), "EXECUTION_CARRIER"),
    "count_negative": ((7, -1, None, None, None), "EXECUTION_CARRIER"),
    "count_over_cap": ((7, (1 << 20) + 1, None, None, None), "EXECUTION_CARRIER"),
    "empty_as_arrays": ((7, 0, [], [], []), "EXECUTION_CARRIER"),
    "empty_one_array": ((7, 0, None, [], None), "EXECUTION_CARRIER"),
    "short_array": ((7, 2, [7, 7], [True], ["a", "b"]), "EXECUTION_CARRIER"),
    "long_array": ((7, 1, [7], [True, False], ["a"]), "EXECUTION_CARRIER"),
    "null_array": ((7, 1, [7], None, ["a"]), "EXECUTION_CARRIER"),
    "tuple_array": ((7, 1, (7,), [True], ["a"]), "EXECUTION_CARRIER"),
    "absent_non_null_container": ((7, None, None, None, None), "NULL"),
    "two_dimensional": ((7, 1, [[7]], [True], ["a"]), "VALUE_DOMAIN"),
    "outside_int64": ((7, 1, [99999999999999999999], [True], ["a"]), "VALUE_DOMAIN"),
    "bool_as_int": ((7, 1, [True], [True], ["a"]), "VALUE_DOMAIN"),
    "int_as_bool": ((7, 1, [7], [1], ["a"]), "VALUE_DOMAIN"),
    "text_too_long": ((7, 1, [7], [True], ["x" * 257]), "VALUE_DOMAIN"),
    "text_nul": ((7, 1, [7], [True], ["a\0b"]), "VALUE_DOMAIN"),
    "null_in_non_null_child": ((7, 1, [None], [True], ["a"]), "NULL"),
    "row_short": ((7, 1, [7], [True]), "EXECUTION_METADATA"),
    "row_long": ((7, 1, [7], [True], ["a"], None), "EXECUTION_METADATA"),
}


@pytest.mark.parametrize("name", sorted(CARRIER_DAMAGE))
def test_a_malformed_carrier_row_is_refused(collect_producer, name):
    row, category = CARRIER_DAMAGE[name]
    with pytest.raises(ResultError) as caught:
        reader.decode_carrier_rows(collect_producer, (GOOD, row), 1 << 20)
    assert caught.value.category == category


def test_an_absent_container_has_only_null_arrays(collect_producer):
    """S16's NULLABLE container: the count and every array are NULL together."""
    first, bound = collect_producer.fields
    optional = replace(collect_producer, fields=(first, replace(bound, nullable=True)))
    decoded, children = reader.decode_carrier_rows(
        optional, ((7, None, None, None, None),), 0
    )
    assert (decoded, children) == (((7, None),), 0)
    with pytest.raises(ResultError, match="^EXECUTION_CARRIER$"):
        reader.decode_carrier_rows(optional, ((7, None, [7], None, None),), 1)


def test_child_rows_are_counted_per_execution_before_allocation(
    collect_producer, monkeypatch
):
    built = []
    monkeypatch.setattr(
        reader.interop,
        "build_managed_batch",
        lambda binding, rows, limits: (
            built.append(rows) or SimpleNamespace(usage=(1, 1), close=lambda: None)
        ),
    )
    payloads = object.__new__(reader.ExecutionPayloads)
    state = dict(
        request=SimpleNamespace(limits=ExecutionLimits()),
        producer=collect_producer,
        binding=None,
        nested=True,
        rows=0,
        batches=0,
        bytes=0,
        children=0,
    )
    for name, value in state.items():
        setattr(payloads, name, value)
    cap = 1 << 20
    first = ((1, cap - 1, [0] * (cap - 1), [None] * (cap - 1), [None] * (cap - 1)),)
    payloads.accept(first)
    # Parents stay the only row unit; the child rows have their own counter.
    assert (payloads.rows, payloads.children, len(built)) == (1, cap - 1, 1)
    with pytest.raises(ResultError, match="^EXECUTION_RESOURCE_LIMIT$"):
        payloads.accept(((2, 2, [1, 2], [True, False], ["x", "y"]),))
    assert (payloads.rows, payloads.children, len(built)) == (1, cap - 1, 1)
    payloads.accept(((3, 1, [3], [False], ["z"]),))
    assert (payloads.rows, payloads.children, len(built)) == (2, cap, 2)
    assert built[1] == ((3, ([3], [False], ["z"])),)
