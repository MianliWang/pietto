"""Whole-result oracle laws and exact helper closure, without an Arrow dependency."""

from copy import deepcopy
from pathlib import Path
import sys

import pytest

import _pietto_phase67_result_product_probe as product
import _pietto_phase67_whole_result_probe as whole


def test_current_manifest_and_transitive_helpers_are_closed():
    assert len(product.CASES) == len(set(product.CASES)) == 120
    assert product.CASES[-10:] == whole.GROUPS
    assert len(whole.damage()) == 10
    integration = product._integration()
    assert "_pietto_phase67_whole_result_probe" in integration.HELPERS
    for closure in (product.input_closure, integration.input_closure):
        entries = closure(Path(__file__).resolve().parents[1])
        assert any(
            "_pietto_phase67_whole_result_probe.py" in str(entry) for entry in entries
        )
    assert "pyarrow" not in sys.modules


def test_original_expected_values_do_not_use_input_decoder_or_observer(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("expected oracle called input decoder/observer")

    monkeypatch.setattr(product, "finite_rows", forbidden)
    monkeypatch.setattr(product, "finite_snapshot", forbidden)
    value = whole.expected(product)
    assert value["rows"][0][2] == ["int", 9007199254740993]
    assert value["rows"][0][3] == ["bool", False]
    assert value["rows"][2][3] == ["null"]
    assert value["rows"][0][4] == ["float64", "8000000000000000"]
    assert value["rows"][0][7] == ["decimal", "1234", 2]
    assert value["rows"][0][9] == ["civil_us", -1]
    assert value["rows"][0][10] == ["uuid", "00112233445566778899aabbccddeeff"]


@pytest.mark.parametrize("mutation", whole.MUTATIONS)
def test_whole_oracle_distinguishes_sequence_from_typed_multiplicity(mutation):
    original = product.finite_expected()["rows"]
    altered = whole.changed(original, mutation)
    original_tags, altered_tags = whole.tagged(original), whole.tagged(altered)
    with pytest.raises(ValueError, match="correspondence"):
        whole.exact(altered_tags, original_tags)
    assert (whole.bag(altered_tags) == whole.bag(original_tags)) == (
        mutation == "reorder"
    )
    # Loss of one repeated row defeats a set but not this oracle.
    if mutation == "duplicate_loss":
        assert set(whole.bag(altered_tags)) == set(whole.bag(original_tags))


@pytest.mark.parametrize(
    "ordinal,bad", [(0, True), (3, 0), (4, -0.0), (7, 1234), (9, False)]
)
def test_scalar_type_tags_fail_closed(ordinal, bad):
    rows = deepcopy(product.finite_expected()["rows"])
    rows[0][ordinal] = bad
    with pytest.raises(ValueError, match="scalar type"):
        whole.tagged(rows)


@pytest.mark.parametrize("state", whole.STATES)
def test_empty_and_nullable_still_have_complete_explicit_fields(state):
    value = whole.expected(product, state)
    assert len(value["fields"]) == 13
    assert value["fields"][0]["label"] == value["fields"][12]["label"] == "repeated"
    assert value["fields"][0]["type"] == value["fields"][12]["type"] == "int16"
    assert value["valid"] == [[v != ["null"] for v in row] for row in value["rows"]]
    assert whole.allowance(
        product.finite_expected(state=state)["rows"]
    ) == product.finite_charge(state=state)


def test_approved_physical_changes_preserve_tagged_logical_values():
    original = whole.expected(product)
    alternative = whole.expected(product, alternative=True)
    assert original["rows"] == alternative["rows"]
    assert [
        i
        for i, (a, b) in enumerate(
            zip(original["fields"], alternative["fields"], strict=True)
        )
        if a != b
    ] == [0, 5, 7, 10]


def test_order_witness_is_at_existing_descriptor_layer(tmp_path):
    result = whole.ordered(product, tmp_path)
    assert result == {
        name: dict(
            layer="descriptor-only",
            original=["desc", tag],
            changed="asc",
            refusal="CORRESPONDENCE",
        )
        for name, tag in (("descriptors", "name"), ("imported", "binary"))
    }
    assert "pyarrow" not in sys.modules


def test_exact_saved_observation_does_not_accept_bool_as_counter():
    with pytest.raises(ValueError):
        whole.exact({"rows": True}, {"rows": 1})


@pytest.mark.parametrize("bad", [{}, {whole.GROUPS[0]: None}, {whole.GROUPS[0]: []}])
def test_malformed_whole_report_uses_existing_value_error_boundary(bad):
    with pytest.raises(ValueError, match="whole-result"):
        whole.verify(bad, product)
