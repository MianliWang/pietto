"""Intrinsic public Timestamp/UUID meaning stays source-bound and fail-closed."""

from __future__ import annotations

import json

import _pietto_results_product as probe
import pytest

from pietto._project.project_result_contract import build_result_contract
from pietto._project.project_sql_emission import emit_project_sql


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_project_emission_derives_builtin_temporal_uuid_meaning(tmp_path, target):
    checked = probe.build_neutral(
        tmp_path / target,
        {"main.pietto": probe.temporal_source(target)},
    )

    outcome = emit_project_sql(checked, probe.temporal_input(target))

    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    meaning = outcome.artifact.request.scalar_meaning
    assert meaning is not None
    assert [entry.canonical.name for entry in meaning.entries] == [
        "Timestamp",
        "Timestamp",
        "UUID",
        "UUID",
    ]
    contract = build_result_contract(checked, scalar_meaning=meaning)
    assert contract.scalar_meaning is meaning
    assert [field.meaning for field in contract.shape.fields] == list(meaning.entries)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_non_temporal_project_emission_keeps_no_meaning_carrier(tmp_path, target):
    checked = probe.build_neutral(
        tmp_path / target,
        {"main.pietto": probe.source(target)},
    )

    outcome = emit_project_sql(checked, probe.emission_input(target))

    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    assert outcome.artifact.request.scalar_meaning is None


def test_alias_and_physical_mismatch_stay_fail_closed(tmp_path):
    source = "type Stamp = Timestamp\n" + probe.temporal_source("postgres").replace(
        "stamp: Timestamp", "stamp: Stamp"
    )
    checked = probe.build_neutral(tmp_path / "alias", {"main.pietto": source})
    alias = emit_project_sql(checked, probe.temporal_input("postgres"))
    assert alias.status == "BLOCKED" and alias.artifact is None
    assert {(blocker.code, blocker.detail) for blocker in alias.blockers} == {
        ("PIE-B1004", "logical_temporal_or_uuid_meaning_missing")
    }

    exact = probe.build_neutral(
        tmp_path / "physical",
        {"main.pietto": probe.temporal_source("postgres")},
    )
    document = json.loads(probe.temporal_input("postgres"))
    document["sources"][0]["fields"][0]["representation"]["storage"][
        "fractional_seconds"
    ] = 3
    mismatch = emit_project_sql(exact, json.dumps(document).encode())
    assert mismatch.status == "INPUT_REJECTED" and mismatch.artifact is None
    assert mismatch.cli_errors
