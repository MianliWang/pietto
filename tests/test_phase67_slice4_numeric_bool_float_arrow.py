"""Real upstream scalar roots, lossless-domain requests and exact ingress predicates."""

from dataclasses import replace
from decimal import Decimal
import importlib.util
from typing import Any, cast

import pytest

import _pietto_phase67_result_product_probe as probe
from pietto._project import project_arrow_result as arrow
from pietto._project import project_result_binding as producer
from pietto._project import project_result_contract as contract
from pietto._project import project_result_contract_portable as writer
from pietto._project import project_result_contract_correspondence as correspondence
from pietto._project import project_result_contract_pure_boundary as pure


@pytest.fixture(scope="module")
def roots(tmp_path_factory):
    root = tmp_path_factory.mktemp("numeric-scalar-roots")
    return {
        target: probe.scalar_fixture(root / target, target)
        for target in ("postgres", "mysql")
    }


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("bits", (16, 32, 64))
def test_verified_storage_widths_and_integer_endpoints(tmp_path, target, bits):
    _, artifact, neutral, bound = probe.width_fixture(tmp_path / "width", target, bits)
    producer.verify_producer_binding(bound, neutral, artifact)
    assert arrow._widths(bound, None) == (bits, bits)
    assert arrow._widths(
        bound, tuple(arrow.IntegerWidthRequest(f.field, 64) for f in bound.fields)
    ) == (64, 64)
    low, high = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
    for value in (low, high, 0, -1, low):
        assert arrow._value(value, bound.fields[0]) == value
    for value in (low - 1, high + 1):
        with pytest.raises(contract.ResultError, match="VALUE_DOMAIN"):
            arrow._value(value, bound.fields[0])


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_domain_total_narrowing_is_independent_of_payload(
    tmp_path, target, monkeypatch
):
    _, _, _, bound = probe.width_fixture(
        tmp_path / "contained", target, 64, lower=-100, upper=100
    )
    requests = tuple(arrow.IntegerWidthRequest(f.field, 16) for f in bound.fields)
    assert arrow._widths(bound, requests) == (16, 16)
    _, _, _, full = probe.width_fixture(tmp_path / "full", target, 64)
    bad = (arrow.IntegerWidthRequest(full.fields[0].field, 16), None)

    def forbidden():
        raise AssertionError("conversion/dependency considered before domain check")

    monkeypatch.setattr(arrow, "_arrow", forbidden)
    for rows in ([], [[0, None]]):
        with pytest.raises(contract.ResultError, match="ARROW_ADAPTATION"):
            arrow.build_owned_batch(arrow.bind_arrow(full, integer_widths=bad), rows)
    for request in (
        [],
        (),
        requests,
        (arrow.IntegerWidthRequest(full.fields[0].field, True), None),
        (arrow.IntegerWidthRequest(full.fields[0].field, 128), None),
    ):
        with pytest.raises(contract.ResultError, match="ARROW_ADAPTATION"):
            arrow.bind_arrow(full, integer_widths=request)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_producer_precedes_even_legal_widening(roots, target, monkeypatch):
    _, artifact, neutral, bound = roots[target]
    fields = list(bound.fields)
    fields[0] = replace(
        fields[0],
        observation=replace(
            fields[0].observation, storage=probe.width_storage(target, 16)
        ),
    )
    bad = replace(bound, fields=tuple(fields))

    def forbidden():
        raise AssertionError("Arrow cannot repair a producer mismatch")

    monkeypatch.setattr(arrow, "_arrow", forbidden)
    with pytest.raises(contract.ResultError, match="PRODUCER_OBSERVATION"):
        arrow.bind_arrow(
            bad,
            integer_widths=(
                arrow.IntegerWidthRequest(neutral.shape.fields[0], 64),
                None,
                None,
                None,
                None,
                None,
            ),
        )
    producer.verify_producer_binding(bound, neutral, artifact)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "position,changes",
    (
        (2, {"domain": "int_range"}),
        (2, {"carrier": "int"}),
        (2, {"lower": 0}),
        (4, {"domain": "bool01"}),
        (4, {"carrier": "int"}),
        (4, {"upper": 1}),
    ),
)
def test_physical_domain_and_carrier_are_explicit(roots, target, position, changes):
    _, artifact, neutral, bound = roots[target]
    observations = [f.observation for f in bound.fields]
    observations[position] = replace(observations[position], **changes)
    with pytest.raises(contract.ResultError, match="PRODUCER_OBSERVATION"):
        producer.bind_producer(neutral, artifact, tuple(observations))


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_bool_physical_rows_and_logical_arrow_scalars_are_distinct(roots, target):
    bound = roots[target][3].fields[2]
    for raw, expected in (
        ((False, False), (True, True))
        if target == "postgres"
        else ((0, False), (1, True))
    ):
        value = arrow._value(raw, bound)
        assert type(value) is bool and value is expected
        assert arrow._value(expected, bound, logical=True) is expected
    bad = (0, 1) if target == "postgres" else (False, True)
    for value in (*bad, 2, -1, 0.0, "1", Decimal(1), object()):
        with pytest.raises(contract.ResultError, match="VALUE_DOMAIN"):
            arrow._value(value, bound)
    with pytest.raises(contract.ResultError, match="VALUE_DOMAIN"):
        arrow._value(1, bound, logical=True)


@pytest.mark.parametrize(
    "value",
    (True, 0, Decimal("0.125"), "0.125", float("nan"), float("inf"), float("-inf")),
)
def test_float_requires_exact_finite_binary64(roots, value):
    with pytest.raises(contract.ResultError, match="VALUE_DOMAIN"):
        arrow._value(value, roots["postgres"][3].fields[4])


def test_float_sign_bits_and_magnitudes_survive_scalar_validation(roots):
    import struct

    values = [row[4] for row in probe.scalar_rows("postgres")]
    actual = [arrow._value(value, roots["postgres"][3].fields[4]) for value in values]
    assert [struct.pack(">d", value).hex() for value in actual] == list(
        probe.FLOAT_BITS
    )


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_nullability_is_logical_and_no_sample_is_required(roots, target):
    bound = roots[target][3]
    for i, field in enumerate(bound.fields):
        if i % 2:
            assert arrow._value(None, field) is None
        else:
            with pytest.raises(contract.ResultError, match="NULL"):
                arrow._value(None, field)
    assert arrow._widths(bound, None) == (64, 64, None, None, None, None)
    assert importlib.util.find_spec("pyarrow") is None
    with pytest.raises(contract.ResultError, match="ARROW_DEPENDENCY_MISSING"):
        arrow.bind_arrow(bound)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_mixed_descriptors_use_unchanged_codec_and_live_authority(roots, target):
    checked, _, neutral, bound = roots[target]
    exported = writer.export_result_contract(neutral, checked)
    view = pure.decode_contract(exported.canonical_bytes)
    assert pure.encode_document(view.document) == exported.canonical_bytes
    assert [f["canonical"]["name"] for f in view.document["fields"]] == [
        "Int",
        "Int",
        "Bool",
        "Bool",
        "Float",
        "Float",
    ]
    assert [f["label"] for f in view.document["fields"]] == list(probe.SCALAR_LABELS)
    correspondence.verify_bound_export(exported, checked)
    with pytest.raises(contract.ResultError, match="ARROW_ADAPTATION"):
        arrow.bind_arrow(
            bound,
            integer_widths=(
                None,
                None,
                arrow.IntegerWidthRequest(neutral.shape.fields[2], 16),
                None,
                None,
                None,
            ),
        )
    with pytest.raises(contract.ResultError, match="PRODUCER_ROOT"):
        arrow.bind_arrow(cast(Any, view))


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "lower,upper,accepted",
    ((-32768, 32767, True), (-32769, 32767, False), (-32768, 32768, False)),
)
def test_explicit_narrowing_checks_both_complete_domain_endpoints(
    tmp_path, target, lower, upper, accepted
):
    _, _, _, bound = probe.width_fixture(
        tmp_path / "edge", target, 64, lower=lower, upper=upper
    )
    requests = tuple(arrow.IntegerWidthRequest(f.field, 16) for f in bound.fields)
    if accepted:
        assert arrow._widths(bound, requests) == (16, 16)
    else:
        with pytest.raises(contract.ResultError, match="ARROW_ADAPTATION"):
            arrow.bind_arrow(bound, integer_widths=requests)
    for bad in ((requests[0], requests[0]), requests[::-1], (object(), None)):
        with pytest.raises(contract.ResultError, match="ARROW_ADAPTATION"):
            arrow.bind_arrow(bound, integer_widths=bad)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("position", (0, 2, 4))
def test_scalar_coercion_methods_are_never_called(roots, target, position):
    with pytest.raises(contract.ResultError, match="VALUE_DOMAIN"):
        arrow._value(probe.CoercibleScalar(), roots[target][3].fields[position])
