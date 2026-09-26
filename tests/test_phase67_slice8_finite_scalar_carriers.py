"""Real source identities and request validation remain available without Arrow."""

from copy import copy
from dataclasses import fields, replace
import importlib.util
from typing import Any, cast

import pytest

import _pietto_phase67_result_product_probe as probe
from pietto._project import project_arrow_result as arrow
from pietto._project import project_result_binding as binding
from pietto._project import project_result_contract as contract


@pytest.fixture(scope="module")
def products(tmp_path_factory):
    root = tmp_path_factory.mktemp("finite-scalars")
    return {
        (target, nullable): probe.finite_fixture(
            root / f"{target}-{nullable}", target, all_nullable=nullable
        )
        for target in ("postgres", "mysql")
        for nullable in (False, True)
    }


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("nullable", (False, True))
def test_real_finite_root_identity_and_policy_before_optional_arrow(
    products, target, nullable
):
    checked, meaning, artifact, neutral, producer, _ = products[target, nullable]
    contract.verify_result_contract(neutral, checked)
    binding.verify_producer_binding(producer, neutral, artifact)
    assert neutral.scalar_meaning is artifact.request.scalar_meaning is meaning
    assert len(neutral.shape.fields) == 13
    assert [f.ordinal for f in neutral.shape.fields] == list(range(13))
    assert [f.shape.canonical.name for f in neutral.shape.fields] == [
        k.split("(")[0] for k in probe.FINITE_KINDS
    ]
    for i, field in enumerate(neutral.shape.fields):
        assert field.port is checked.plan.exports[i]
        assert field.label == probe.FINITE_LABELS[i]
        assert field.shape.canonical is field.port.field.evidence.resolved_type
        assert field.provenance is field.port.field.evidence.provenance
    assert len({id(f.port) for f in neutral.shape.fields}) == 13
    assert len({id(f.column.source_field.field) for f in producer.fields}) == 13
    policy = probe.finite_policy(producer)
    assert arrow._field_labels(producer, policy["field_labels"]) == tuple(
        "repeated" if i in (0, 5, 12) else name
        for i, name in enumerate(probe.FINITE_LABELS)
    )
    assert arrow._field_labels(producer, None) == probe.FINITE_LABELS
    assert importlib.util.find_spec("pyarrow") is None
    with pytest.raises(contract.ResultError, match="ARROW_DEPENDENCY_MISSING"):
        arrow.bind_arrow(producer, **policy)


@pytest.mark.parametrize(
    "damage",
    (
        "arity",
        "extra",
        "list",
        "wrong_kind",
        "foreign",
        "reordered",
        "reused",
        "deleted_label",
        "deleted_field",
    ),
)
def test_label_policy_exact_occurrences_and_deleted_slots(products, damage):
    producer = products["postgres", False][4]
    requests = tuple(
        arrow.ArrowFieldLabelRequest(b.field, "x") for b in producer.fields
    )
    bad: Any = requests
    if damage == "arity":
        bad = requests[:-1]
    elif damage == "extra":
        bad = (*requests, None)
    elif damage == "list":
        bad = list(requests)
    elif damage == "wrong_kind":
        bad = (arrow.IntegerWidthRequest(producer.fields[0].field, 16), *requests[1:])
    elif damage == "foreign":
        bad = (
            replace(requests[0], field=products["postgres", True][4].fields[0].field),
            *requests[1:],
        )
    elif damage == "reordered":
        bad = requests[::-1]
    elif damage == "reused":
        bad = (requests[0], requests[0], *requests[2:])
    else:
        request = copy(requests[0])
        object.__delattr__(request, damage.removeprefix("deleted_"))
        bad = (request, *requests[1:])
    with pytest.raises(contract.ResultError, match="ARROW_LABELS"):
        arrow.bind_arrow(producer, field_labels=bad)


class LabelSubclass(str):
    pass


@pytest.mark.parametrize(
    "label",
    (
        "",
        "a\0b",
        "\ud800",
        "\udfff",
        "a" * 1025,
        "😀" * 257,
        "é" * 513,
        b"x",
        True,
        LabelSubclass("x"),
    ),
)
def test_explicit_label_validation_precedes_arrow(products, label):
    producer = products["postgres", False][4]
    requests = (
        arrow.ArrowFieldLabelRequest(producer.fields[0].field, cast(Any, label)),
    ) + (None,) * 12
    with pytest.raises(contract.ResultError, match="ARROW_LABELS"):
        arrow.bind_arrow(producer, field_labels=requests)


@pytest.mark.parametrize("label", ("a" * 1024, "😀" * 256, "é" * 512, "e\u0301", " "))
def test_label_exact_utf8_boundary_and_no_normalization(products, label):
    producer = products["postgres", False][4]
    requests = (arrow.ArrowFieldLabelRequest(producer.fields[0].field, label),) + (
        None,
    ) * 12
    assert arrow._field_labels(producer, requests)[0] == label


def test_appended_storage_preserves_positional_binding_and_deleted_policy_is_typed(
    products,
):
    producer = products["postgres", False][4]
    value = arrow.ArrowResultBinding(producer, None)
    assert value.field_labels is None
    assert [f.name for f in fields(value)] == [
        "producer",
        "schema",
        "integer_widths",
        "text_offset_widths",
        "decimal_widths",
        "uuid_representations",
        "field_labels",
    ]
    object.__delattr__(value, "field_labels")
    with pytest.raises(contract.ResultError, match="ARROW_LABELS"):
        arrow.verify_arrow_binding(value, producer)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_labels_cannot_repair_producer_observation_or_missing_meaning(products, target):
    from pietto._project.project_sql_emission import emit_project_sql

    checked, _, _, _, producer, encoded = products[target, False]
    assert emit_project_sql(checked, encoded).status == "BLOCKED"
    broken = replace(
        producer,
        fields=(
            replace(
                producer.fields[0],
                observation=replace(producer.fields[0].observation, label="repeated"),
            ),
            *producer.fields[1:],
        ),
    )
    with pytest.raises(contract.ResultError, match="PRODUCER_OBSERVATION"):
        arrow.bind_arrow(broken, **probe.finite_policy(broken))


@pytest.mark.parametrize(
    "state,wide,expected",
    (
        ("empty", False, 12),
        ("empty", True, 16),
        ("null", False, 321),
        ("null", True, 365),
    ),
)
def test_combined_resource_allowance_is_independent(products, state, wide, expected):
    producer = products["postgres", True][4]
    value = arrow.ArrowResultBinding(
        producer, None, **probe.finite_policy(producer, wide=wide)
    )
    row_count = 0 if state == "empty" else 2
    assert probe.finite_charge(state=state, wide=wide) == expected
    assert (
        arrow._base_charge(value, row_count, arrow.BatchLimits(bytes=expected))
        == expected
    )
    with pytest.raises(contract.ResultError, match="LIMIT"):
        arrow._base_charge(value, row_count, arrow.BatchLimits(bytes=expected - 1))


@pytest.mark.parametrize(
    "slot",
    ("integer_widths", "text_offset_widths", "decimal_widths", "uuid_representations"),
)
def test_deleted_representation_storage_fails_before_schema(products, slot):
    producer = products["postgres", False][4]
    value = arrow.ArrowResultBinding(producer, None, **probe.finite_policy(producer))
    object.__delattr__(value, slot)
    with pytest.raises(contract.ResultError, match="ARROW_ADAPTATION"):
        arrow.verify_arrow_binding(value, producer)
