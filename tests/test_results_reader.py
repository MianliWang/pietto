"""Arrow-free declaration/inventory checks; real pulls run in installed consumers."""

from dataclasses import replace
import importlib.util
from typing import Any, cast

import pytest

import _pietto_results_product as probe
from pietto._project import project_arrow_result as arrow
from pietto._project import project_result_binding as producers
from pietto._project import project_result_contract as c
from pietto._project import project_result_reader as reader
from pietto._project.project_result_contract import ResultError


@pytest.mark.parametrize("total", (None, True, 1.0, -1, "0", object(), 1048577))
def test_extent_is_explicit_exact_and_checked_before_optional_sdk(total):
    with pytest.raises(ResultError, match="READER_DECLARATION"):
        reader.open_finite_reader(None, None, expected_rows=total)
    assert importlib.util.find_spec("pyarrow") is None


@pytest.mark.parametrize(
    "name,value",
    (
        ("max_batches", True),
        ("max_batches", -1),
        ("max_batches", 1025),
        ("max_total_rows", 1048577),
        ("max_total_bytes", 67108865),
        ("max_total_bytes", 1.0),
        ("batch", None),
    ),
)
def test_reader_limits_are_closed_and_can_only_tighten(name, value):
    limits = replace(reader.FiniteReaderLimits(), **{name: cast(Any, value)})
    with pytest.raises(ResultError, match="LIMIT"):
        reader.open_finite_reader(None, None, expected_rows=0, limits=limits)


def test_zero_limits_are_zero_and_deleted_limits_fail_closed():
    assert reader._limits_values(
        reader.FiniteReaderLimits(max_batches=0, max_total_rows=0, max_total_bytes=0)
    ) == (0, 0, 0, 64, 4096, 8388608)
    limits = reader.FiniteReaderLimits()
    object.__delattr__(limits, "max_total_bytes")
    with pytest.raises(ResultError, match="LIMIT"):
        reader.open_finite_reader(None, None, expected_rows=0, limits=limits)
    for batch in (
        arrow.BatchLimits(fields=65),
        arrow.BatchLimits(rows=4097),
        arrow.BatchLimits(bytes=8388609),
    ):
        with pytest.raises(ResultError, match="LIMIT"):
            reader._limits_values(reader.FiniteReaderLimits(batch=batch))


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_current_finite_source_retains_exact_identity_before_reader(tmp_path, target):
    checked, meaning, artifact, neutral, producer, _ = probe.finite_fixture(
        tmp_path / target, target
    )
    assert neutral.scalar_meaning is artifact.request.scalar_meaning is meaning
    assert len(producer.fields) == 13
    assert [b.field.label for b in producer.fields] == list(probe.FINITE_LABELS)
    assert len({id(b.column.source_field.field) for b in producer.fields}) == 13
    assert neutral.authority is checked
    with pytest.raises(ResultError, match="ARROW_DEPENDENCY_MISSING"):
        arrow.bind_arrow(producer, **probe.finite_policy(producer))


def test_unconstructed_receipts_and_missing_session_storage_cannot_complete():
    with pytest.raises(ResultError, match="READER_IDENTITY"):
        reader.verify_finite_completion(None, None, None)
    uninitialized = object.__new__(reader.CheckedFiniteReader)
    with pytest.raises(ResultError, match="READER_IDENTITY"):
        reader.verify_finite_completion(uninitialized, None, None)
    assert reader.__all__ == () and importlib.util.find_spec("pyarrow") is None


def test_frozen_reader_manifests_and_independent_layout_arithmetic():
    assert len(probe.CASES) == len(set(probe.CASES))
    assert tuple(probe.CASES[64:74]) == probe.READER_GROUPS
    assert "project_result_reader" in probe.PRODUCTS
    assert probe.reader_expected(probe.READER_LAYOUTS["whole"])["charge"] == 630
    assert probe.reader_expected(probe.READER_LAYOUTS["uneven"])["charge"] == 1584
    assert (
        probe.reader_expected(probe.READER_LAYOUTS["empty_interleaved"])["charge"]
        == 1620
    )


@pytest.mark.parametrize("exception", (KeyboardInterrupt, SystemExit))
def test_identical_primary_cleanup_control_exception_is_not_duplicated(
    exception, monkeypatch
):
    session = object.__new__(reader.CheckedFiniteReader)
    error = exception()
    monkeypatch.setattr(session, "_close_once", lambda: error)
    with pytest.raises(exception) as raised:
        session._fail(error, "READER_VALIDATION")
    assert raised.value is error and session.state == "FAILED"


def test_session_root_snapshot_retains_protocol_observation(tmp_path):
    *_, producer, _ = probe.finite_fixture(tmp_path / "snapshot", "postgres")
    binding = arrow.ArrowResultBinding(producer, None)
    captured = reader._roots(binding)
    contract = producer.contract
    flat = (
        producer,
        producer.fields,
        contract,
        producer.artifact,
        contract.authority,
        contract.shape,
        contract.scalar_meaning,
    )
    for bound in producer.fields:
        assert isinstance(bound, producers.ProducerFieldBinding)
        flat += (bound.observation, bound.observation.protocol_nullable)
    assert len(captured) == len(flat)
    assert all(a is b for a, b in zip(captured, flat, strict=True))
    observation = cast(producers.ProducerFieldBinding, producer.fields[0]).observation
    object.__setattr__(observation, "protocol_nullable", True)
    assert any(
        a is not b for a, b in zip(captured, reader._roots(binding), strict=True)
    )


def _nested_binding(producer):
    """Real Int8/Bool/Text child leaves under one assembled nested field."""
    contract = producer.contract
    children = (producer.fields[2], producer.fields[3], producer.fields[5])
    shape = c.NestedShape(
        None,
        contract.owner,
        contract.output,
        contract.multiplicity,
        contract.ordering,
        tuple(child.field for child in children),
    )
    field = replace(contract.shape.fields[0], label="c", shape=shape)
    count = producers.ProducerObservation(
        0, "c", "postgres", "pg_int8", 0, 1048576, domain="child_count"
    )
    bound = producers.ProducerNestedBinding(field, None, count, children, False)
    nested = producers.ProducerResultBinding(
        replace(contract, shape=c.ResultShape((field,))), producer.artifact, (bound,)
    )
    return arrow.ArrowResultBinding(nested, None), bound


@pytest.mark.parametrize("change", ("child_observation", "count_protocol", "children"))
def test_session_root_snapshot_covers_nested_count_and_children(tmp_path, change):
    *_, producer, _ = probe.finite_fixture(tmp_path / "nested", "postgres")
    binding, bound = _nested_binding(producer)
    nested = binding.producer
    roots = reader._roots(binding)
    children = bound.children
    expected = (
        nested,
        nested.fields,
        nested.contract,
        nested.artifact,
        nested.contract.authority,
        nested.contract.shape,
        nested.contract.scalar_meaning,
        bound,
        bound.field,
        bound.count,
        None,
        children,
    )
    for child in children:
        expected += (child.observation, None)
    assert len(roots) == len(expected) == 18
    assert all(a is b for a, b in zip(roots, expected, strict=True))
    policies = reader._policy_snapshot(binding)
    # Unchanged, the identity check passes and S07-A's contract authority refuses.
    with pytest.raises(ResultError) as unchanged:
        reader._verify_binding_snapshot(binding, roots, None, policies)
    assert unchanged.value.category == "FIELD"
    if change == "child_observation":
        child = children[1]
        object.__setattr__(child, "observation", replace(child.observation))
    elif change == "count_protocol":
        object.__setattr__(bound.count, "protocol_nullable", False)
    else:
        object.__setattr__(bound, "children", children[:2])
    with pytest.raises(ResultError, match="READER_IDENTITY"):
        reader._verify_binding_snapshot(binding, roots, None, policies)
    assert importlib.util.find_spec("pyarrow") is None
