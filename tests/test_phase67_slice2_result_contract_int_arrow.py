"""Ordinary Arrow-free tests: real authored roots and independent boundary damage."""

from dataclasses import replace
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

import _pietto_phase67_result_product_probe as probe
from pietto._project import project_result_contract as c
from pietto._project import project_result_binding as p
from pietto._project import project_arrow_result as a


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    root = tmp_path_factory.mktemp("result-roots")
    result = {}
    for target in ("postgres", "mysql"):
        checked, artifact = probe.build_source(root / target, target)
        contract = c.build_result_contract(checked)
        producer = p.bind_producer(contract, artifact, probe.observations(target))
        result[target] = checked, artifact, contract, producer
    return result


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_real_ordered_neutral_contract_and_producer(built, target):
    checked, artifact, contract, producer = built[target]
    c.verify_result_contract(contract, checked)
    p.verify_producer_binding(producer, contract, artifact)
    assert [f.label for f in contract.shape.fields] == ["renamed", "other"]
    assert [f.ordinal for f in contract.shape.fields] == [0, 1]
    assert [b.nullable for b in producer.fields] == [False, True]
    for field, port in zip(contract.shape.fields, checked.plan.exports, strict=True):
        assert field.port is port
        assert field.shape.canonical is port.field.evidence.resolved_type
        assert field.shape.declared is port.field.evidence.field_def.type_expr
    assert len(repr(contract)) < 200 and len(repr(producer)) < 100
    assert contract.ordering is None


@pytest.mark.parametrize(
    "damage",
    (
        "drop",
        "swap",
        "duplicate",
        "ordinal",
        "label",
        "shape",
        "declared",
        "canonical",
        "owner",
        "output",
        "ordering",
        "multiplicity",
    ),
)
def test_contract_checks_complete_authority_not_its_own_flag(built, damage):
    checked, _, contract, _ = built["postgres"]
    leaves = contract.shape.fields
    if damage in ("drop", "swap", "duplicate"):
        changed = {
            "drop": leaves[:1],
            "swap": leaves[::-1],
            "duplicate": (leaves[0], leaves[0]),
        }[damage]
        bad = replace(contract, shape=c.ResultShape(changed))
    elif damage in ("ordinal", "label", "shape", "declared", "canonical"):
        if damage == "ordinal":
            leaf = replace(leaves[0], ordinal=True)
        elif damage == "label":
            leaf = replace(leaves[0], label="other")
        elif damage == "shape":
            leaf = replace(leaves[0], shape={})
        else:
            leaf = replace(
                leaves[0], shape=replace(leaves[0].shape, **{damage: object()})
            )
        bad = replace(contract, shape=c.ResultShape((leaf, leaves[1])))
    else:
        bad = replace(contract, **{damage: object()})
    with pytest.raises(c.ResultError):
        c.verify_result_contract(bad, checked)


def test_equal_looking_foreign_source_is_not_identity(built, tmp_path):
    checked, artifact = probe.build_source(tmp_path / "other", "postgres")
    _, _, contract, _ = built["postgres"]
    with pytest.raises(c.ResultError, match="ROOT"):
        c.verify_result_contract(contract, checked)
    with pytest.raises(c.ResultError, match="ROOT"):
        p.bind_producer(contract, artifact, probe.observations("postgres"))


@pytest.mark.parametrize(
    "damage",
    (
        "family",
        "storage",
        "lower",
        "upper",
        "ordinal",
        "label",
        "width",
        "nullability",
        "root",
        "order",
        "drop",
    ),
)
def test_producer_refuses_complete_field_mismatch(built, damage):
    _, artifact, contract, producer = built["postgres"]
    changes = {
        "family": "mysql",
        "storage": "pg_int4",
        "lower": -1,
        "upper": 1,
        "ordinal": True,
        "label": "other",
    }
    if damage in changes:
        obs = replace(producer.fields[0].observation, **{damage: changes[damage]})
        bad = replace(
            producer,
            fields=(replace(producer.fields[0], observation=obs), producer.fields[1]),
        )
    elif damage == "width":
        bad = replace(
            producer,
            fields=(
                replace(
                    producer.fields[0],
                    observation=replace(producer.fields[0].observation, upper=2**63),
                ),
                producer.fields[1],
            ),
        )
    elif damage == "nullability":
        bad = replace(
            producer,
            fields=(replace(producer.fields[0], nullable=True), producer.fields[1]),
        )
    elif damage == "root":
        bad = replace(producer, artifact=built["mysql"][1])
    elif damage == "order":
        bad = replace(producer, fields=producer.fields[::-1])
    else:
        bad = replace(producer, fields=producer.fields[:1])
    with pytest.raises(c.ResultError):
        p.verify_producer_binding(bad, contract, artifact)


def test_protocol_nullability_is_not_logical_authority(built):
    _, artifact, contract, _ = built["postgres"]
    for nullable in (None, False, True):
        observed = tuple(
            replace(o, protocol_nullable=nullable)
            for o in probe.observations("postgres")
        )
        binding = p.bind_producer(contract, artifact, observed)
        assert [f.nullable for f in binding.fields] == [False, True]


@pytest.mark.parametrize("value", (True, 1.0, Decimal(1), "1", 2**63, -(2**63) - 1))
def test_int_domain_is_exact_without_coercion(built, value):
    with pytest.raises(c.ResultError, match="VALUE_DOMAIN"):
        a._value(value, built["postgres"][3].fields[0])


def test_arrow_absence_is_lazy_and_deterministic(built):
    assert importlib.util.find_spec("pyarrow") is None
    assert "pyarrow" not in sys.modules
    with pytest.raises(c.ResultError, match="ARROW_DEPENDENCY_MISSING"):
        a.bind_arrow(built["postgres"][3])
    assert "pyarrow" not in sys.modules
    command = [
        sys.executable,
        "-c",
        "import sys; import pietto; from pietto._project import project_result_contract, project_result_binding, project_arrow_result; assert 'pyarrow' not in sys.modules",
    ]
    subprocess.run(command, check=True)


@pytest.mark.parametrize(
    "dimensions",
    (
        (65, 1, a.BatchLimits()),
        (2, 4097, a.BatchLimits()),
        (2, 1, a.BatchLimits(bytes=17)),
        (2, 1, a.BatchLimits(rows=True)),
    ),
)
def test_dimensions_refuse_before_allocation(dimensions):
    with pytest.raises(c.ResultError, match="LIMIT"):
        a._dimensions(*dimensions)


def test_exit_zero_does_not_supply_product_evidence():
    with pytest.raises(ValueError):
        probe.verify_report({"exit": 0}, {}, {})
    with pytest.raises(ValueError):
        probe.verify_report(
            {
                "format": probe.FORMAT,
                "context": {},
                "pin": probe.PIN,
                "inputs": {},
                "origins": {},
                "prefix": "/tmp/isolated",
                "cases": {},
            },
            {},
            {},
        )


def test_private_product_does_not_change_public_api_or_optional_lock():
    import pietto

    assert not hasattr(pietto, "PiettoResultContract")
    root = Path(__file__).resolve().parents[1]
    assert "pyarrow" not in (root / "pyproject.toml").read_text().lower()
    assert "pyarrow" not in (root / "uv.lock").read_text().lower()
    assert json.loads(probe.emission_input("mysql"))["target"]["family"] == "mysql"


@pytest.mark.parametrize("bad", (None, {}, object()))
def test_optional_boundary_rejects_malformed_roots(bad):
    with pytest.raises(c.ResultError, match="PRODUCER_ROOT"):
        a.bind_arrow(bad)
    with pytest.raises(c.ResultError, match="ARROW_BINDING"):
        a.build_owned_batch(bad, [])


def test_ci_requires_separate_installed_product_evidence():
    from scripts import ci_validation as ci

    with pytest.raises(ValueError, match="missing required installed product"):
        ci.check_product(None, {})
    workflow = (
        Path(__file__).resolve().parents[1] / ".github/workflows/ci.yml"
    ).read_text()
    assert workflow.count("Run installed Int result product consumer") == 2
    assert workflow.count("Download required installed result product evidence") == 2
    assert workflow.count('--product "$RUNNER_TEMP/product-reports/') == 2
