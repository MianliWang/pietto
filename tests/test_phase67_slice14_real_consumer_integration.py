"""Offline controls; synthetic records here are never native execution evidence."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import struct

import pytest

import _pietto_phase67_real_consumer_probe as probe


@pytest.mark.parametrize(
    "tag,value,expected",
    (
        ("bool", True, True),
        ("int", "9007199254740993", 9007199254740993),
        ("text", "trail 😀  ", "trail 😀  "),
        ("bytes", "00ff", b"\x00\xff"),
        ("decimal", "12.30", Decimal("12.30")),
        ("float", "-0x0.0p+0", -0.0),
    ),
)
def test_exact_observation_scalar_decoder(tag, value, expected):
    actual = probe.decode_scalar(dict(kind=tag, value=value))
    assert type(actual) is type(expected) and actual == expected
    if tag == "float":
        assert struct.pack(">d", actual).hex() == "8000000000000000"
    if tag == "decimal":
        assert isinstance(actual, Decimal)
        assert actual.as_tuple().exponent == -2
    assert probe.decode_scalar({"kind": "null"}) is None


@pytest.mark.parametrize(
    "bad",
    (
        None,
        [],
        {},
        {"kind": "null", "value": None},
        {"kind": "unknown", "value": "1"},
        {"kind": "bool", "value": 1},
        {"kind": "int", "value": True},
        {"kind": "int", "value": "1.0"},
        {"kind": "int", "value": "01"},
        {"kind": "int", "value": "9" * 33},
        {"kind": "float", "value": "nan"},
        {"kind": "float", "value": "inf"},
        {"kind": "float", "value": "1.5"},
        {"kind": "decimal", "value": "NaN"},
        {"kind": "decimal", "value": "Infinity"},
        {"kind": "bytes", "value": "f"},
        {"kind": "text", "value": 1},
        {"kind": "text", "value": "x" * 4097},
        {"kind": "int", "value": "1", "extra": True},
    ),
)
def test_unknown_coercive_or_malformed_scalar_is_rejected(bad):
    with pytest.raises(ValueError):
        probe.decode_scalar(bad)


@pytest.mark.parametrize("bad", (None, {}, [[{"kind": "null"}]], [[]] * 33))
def test_closed_row_shape_and_bound(bad):
    with pytest.raises(ValueError):
        probe.decode_rows(bad)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_declared_domain_and_observed_protocol_facts_remain_separate(target):
    emission = probe.helpers()[0]
    recipe = emission.fixture(target, "G_emission_table_bag", "bag")
    metadata = probe.metadata_fixture(target)
    observations = probe.producer_observations(target, metadata, recipe)
    assert observations[1].lower == -9007199254740993
    assert observations[1].upper == 9007199254740993
    assert (
        observations[0].text is not None and observations[0].text.max_characters == 64
    )
    assert observations[3].decimal is not None and observations[3].decimal.scale == 2
    if target == "postgres":
        assert all(o.protocol_nullable is None for o in observations)
    for column, index, bad in (
        (0, 0, "wrong"),
        (1, 1, 20 if target == "mysql" else 8),
        (2, 1, True),
    ):
        damaged = deepcopy(metadata)
        damaged[column][index] = bad
        with pytest.raises(ValueError):
            probe.producer_observations(target, damaged, recipe)
    with pytest.raises(ValueError):
        probe.producer_observations("wrong", metadata, recipe)


@pytest.fixture(scope="module")
def synthetic_receipts(tmp_path_factory):
    """Actual compiled documents plus deliberately synthetic observer controls."""
    root = tmp_path_factory.mktemp("integration-synthetic")
    emission = probe.helpers()[0]
    from pietto._project.project_sql_emission import serialize_project_sql_emission

    context = dict(checkout="a" * 40, run_id="synthetic-unit", run_attempt=1)
    result = {}
    for target in ("postgres", "mysql"):
        cases, generation, inputs = [], [], []
        for case, variant in probe.RECIPES:
            recipe = emission.fixture(target, case, variant)
            _, outcome = emission.build_case(root / target / case, **recipe)
            public = serialize_project_sql_emission(outcome)
            document = emission.decode_public(public)
            source_sha, contract_sha = (
                probe.digest(recipe["source"].encode()),
                probe.digest(recipe["contract"].encode()),
            )
            inputs.append(
                dict(
                    id=case,
                    variant=variant,
                    source_sha256=source_sha,
                    contract_sha256=contract_sha,
                    policy=recipe["policy"],
                )
            )
            generation.append(
                dict(
                    id=case,
                    variant=variant,
                    source_sha256=source_sha,
                    contract_sha256=contract_sha,
                    public=public.decode(),
                    public_sha256=probe.digest(public),
                )
            )
            observation = dict(
                sql=document["sql"],
                sql_sha256=probe.digest(document["sql"].encode()),
                parameters=[],
                identity="query",
                prepared=True,
                failures=[],
                status="success",
                execute="success",
                fetch="success",
                close="success",
                metadata=probe.metadata_fixture(target),
                rows=probe.fixture_tags(target, variant == "empty"),
                api="psycopg.RawCursor"
                if target == "postgres"
                else "mysql.native-prepared.v1",
                native=None
                if target == "postgres"
                else dict(
                    prepare="success",
                    terminal=dict(kind="rowset_eof"),
                    unread_final=False,
                    close_send="complete_no_ack",
                ),
            )
            cases.append(
                dict(
                    id=case,
                    variants=[
                        dict(
                            variant=variant,
                            public=public.decode(),
                            public_sha256=probe.digest(public),
                            submission_before=0,
                            submission_after=1,
                        )
                    ],
                    observations=[observation],
                )
            )
        result[target] = dict(
            format="pietto.target-conformance-receipt.v2",
            commit=context["checkout"],
            run_id=context["run_id"],
            run_attempt=1,
            target=target,
            status="success",
            full_manifest=True,
            failures=[],
            cleanup=dict(status="success", failures=[]),
            cases=cases,
            inputs=dict(emission_inputs={target: inputs}),
            generation=dict(emission=dict(records=generation)),
        )
    return result, context


def test_selected_observations_use_actual_rows_and_never_expected(synthetic_receipts):
    receipts, context = deepcopy(synthetic_receipts)
    selected = probe.selected_observations(receipts, context)
    assert len(selected) == 8
    receipt = receipts["postgres"]
    observation = receipt["cases"][0]["observations"][0]
    observation["expected"] = deepcopy(observation["rows"])
    observation["rows"][0][1]["value"] = "8"
    changed = probe.selected_observations(receipts, context)
    assert (
        changed[probe.key(probe.CELLS[0])]["observation"]["rows"][0][1]["value"] == "8"
    )
    # Post-validation mutation is selected as actual data, then fails the independent oracle.
    with pytest.raises(ValueError, match="multiplicity"):
        probe.compare_bag(
            changed[probe.key(probe.CELLS[0])]["observation"]["rows"],
            probe.fixture_tags("postgres"),
        )


@pytest.mark.parametrize(
    "mutation",
    (
        lambda r: r["postgres"].update(commit="b" * 40),
        lambda r: r["postgres"].update(run_id="foreign"),
        lambda r: r["postgres"].update(run_attempt=True),
        lambda r: r["postgres"].update(target="mysql"),
        lambda r: r["postgres"]["cases"].pop(),
        lambda r: r["postgres"]["cases"][0]["variants"][0].update(variant="empty"),
        lambda r: r["postgres"]["cases"][0]["variants"][0].update(
            public_sha256="0" * 64
        ),
        lambda r: r["postgres"]["inputs"]["emission_inputs"]["postgres"][0].update(
            source_sha256="0" * 64
        ),
        lambda r: r["postgres"]["cases"][0]["observations"][0].update(execute="failed"),
        lambda r: r["postgres"]["cases"][0]["observations"][0].update(
            fetch="not_started"
        ),
        lambda r: r["postgres"]["cases"][0]["observations"][0].update(close="failed"),
        lambda r: r["mysql"]["cases"][0]["observations"][0]["native"].update(
            terminal={"kind": "missing"}
        ),
        lambda r: r["mysql"]["cases"][0]["observations"][0]["native"].update(
            close_send="failed"
        ),
        lambda r: r["postgres"]["cases"][0]["observations"][0]["metadata"][
            0
        ].__setitem__(0, "wrong"),
    ),
)
def test_post_validation_selection_controls_are_not_valid_native_evidence(
    synthetic_receipts, mutation
):
    receipts, context = deepcopy(synthetic_receipts)
    mutation(receipts)
    with pytest.raises(ValueError):
        probe.selected_observations(receipts, context)


def test_case_and_public_artifact_context_cannot_be_substituted(synthetic_receipts):
    receipts, context = synthetic_receipts
    selected = probe.selected_observations(receipts, context)
    first = selected[probe.key(probe.CELLS[0])]["association"]
    for field, value in (
        ("policy", "bind_safe_literals"),
        ("case", "H_emission_query_bag"),
        ("target", "mysql"),
        ("source_sha256", "0" * 64),
    ):
        bad = dict(first, **{field: value})
        with pytest.raises(ValueError):
            probe.verify_association(probe.CELLS[0], bad)


def test_data_only_report_rejects_flags_truncation_missing_origins_and_references():
    assert len(probe.GROUPS) == len(set(probe.GROUPS)) == 8
    for value in ({"passed": True}, {}, {"format": probe.FORMAT}):
        with pytest.raises(ValueError):
            probe.verify_replay_report(value, {}, {}, {}, {}, "a" * 64)
        with pytest.raises(ValueError):
            probe.verify_fixture_groups(value, {})
    with pytest.raises(ValueError):
        probe.verify_origins(
            dict(
                prefix="/tmp/extra",
                wheel=dict(path="/tmp/candidate.whl", sha256="a" * 64),
                pyarrow=dict(version="25.0.1", path="/checkout/pyarrow/__init__.py"),
                origins={},
            ),
            {},
        )
    assert importlib.util.find_spec("pyarrow") is None


def test_required_sidecar_is_bounded_and_native_pair_is_separate(tmp_path: Path):
    with pytest.raises(ValueError, match="2 MiB"):
        probe.write_report(
            tmp_path / "too-large.json", {"data": "x" * probe.MAX_REPORT}
        )
    path = tmp_path / "sidecar.json"
    probe.write_report(path, {"small": True})
    assert json.loads(path.read_bytes()) == {"small": True}
    with pytest.raises(FileExistsError):
        probe.write_report(path, {"small": True})
    with pytest.raises(ValueError, match="pair-only"):
        probe.receipt_files(tmp_path, dict(run_id="x", run_attempt=1))


def test_original_value_oracle_does_not_reuse_the_input_decoder(monkeypatch):
    def changed(_):
        return [["lost", 0, True, Decimal("0.00"), 0.0]]

    monkeypatch.setattr(probe, "decode_rows", changed)
    original = probe.snapshot_expected(probe.fixture_tags("postgres"), "postgres")
    assert original["rows"][0][1] == 9007199254740993
    assert original["rows"][0][3:] == ["1230", "8000000000000000"]
    assert len(original["rows"]) == 4 and original["rows"][0] == original["rows"][1]


def test_aggregate_replay_is_required_after_original_strict_and_keeps_topology():
    from test_phase11_ci_workflow import _job

    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github/workflows/ci.yml").read_text()
    aggregate = _job(workflow, "target_conformance_aggregate")
    steps = [
        "Verify all required conformance outcomes",
        "Prepare isolated Arrow-extra integration consumer",
        "Replay strictly verified current native observations",
        "Upload required real-consumer integration",
        "Verify raw integration sidecar identity",
        "Report workload health and bounded trusted history",
    ]
    positions = [aggregate.index(name) for name in steps]
    assert positions == sorted(positions)
    assert (
        "phase67-consumer-integration-${{ github.run_id }}-${{ github.run_attempt }}.json"
        in aggregate
    )
    assert '"$RUNNER_TEMP/integration-reports/' in aggregate
    assert "--artifact-id" in aggregate and "--artifact-digest" in aggregate
    assert "--extra-env" in _job(workflow, "checks_twelve")
    assert "--extra-env" in _job(workflow, "checks_thirteen")
    assert "_pietto_phase67_result_product_probe.py" not in aggregate
    assert "_pietto_phase67_arrow_compatibility_probe.py" not in aggregate
    assert "needs: [python_twelve, python_thirteen, target_conformance]" in aggregate


@pytest.mark.parametrize(
    "change",
    (
        lambda r: r["postgres"].update(format="pietto.target-conformance-receipt.v3"),
        lambda r: r["postgres"]["cases"][0]["variants"][0].update(
            submission_before=False
        ),
    ),
)
def test_selected_receipt_envelope_is_exact(synthetic_receipts, change):
    receipts, context = deepcopy(synthetic_receipts)
    change(receipts)
    with pytest.raises(ValueError):
        probe.selected_observations(receipts, context)


def test_saved_context_does_not_accept_boolean_attempt_as_integer():
    context = dict(
        checkout="a" * 40,
        run_id="test",
        run_attempt=1,
        python="3.13",
        python_version="3.13.13",
    )
    value = dict(
        format=probe.FORMAT,
        mode="captured-native-replay",
        context=dict(context, run_attempt=True),
        inputs={},
        receipts={},
        installation={},
        cells={probe.key(c): {} for c in probe.CELLS},
    )
    with pytest.raises(ValueError, match="report context/input/denominator"):
        probe.verify_replay_report(value, context, {}, {}, {}, "a" * 64)


def test_replay_cannot_mislabel_the_actual_interpreter(monkeypatch, capsys):
    import sys

    other = "3.12" if sys.version_info[:2] == (3, 13) else "3.13"
    monkeypatch.setattr(sys, "argv", [str(probe.__file__), "replay", "--python", other])
    with pytest.raises(SystemExit) as result:
        probe.main()
    assert result.value.code == 2
    assert "actual interpreter" in capsys.readouterr().err
