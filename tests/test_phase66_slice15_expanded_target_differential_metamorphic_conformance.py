"""Phase66 Slice15: expanded target, differential and metamorphic conformance."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import time
from typing import Any

import pytest

import _pietto_phase66_sql_emission_probe as probe
import _pietto_target_conformance as facility
import _pietto_target_conformance_cases as cases
import test_phase66_slice2_isolated_target_conformance_facility as facility_tests
from pietto._project import project_sql_emission as emitter
from pietto._project import project_sql_emission_ast as sql_ast
from pietto._project import project_sql_emission_joins as joins
from pietto._project import project_sql_emission_portable as portable
from pietto._project import project_sql_emission_pure_boundary as pure
from pietto._project.project_sql_emission import serialize_project_sql_emission
from pietto._project.project_sql_emission_rendering import render_join_sql
from pietto._project.project_sql_emission_verification import (
    verify_project_sql_emission,
)

TARGETS = ("postgres", "mysql")
CASE = "M_metamorphic_composition"
SPEC = (
    Path(__file__).resolve().parents[1]
    / "docs/spec/phase66-slice15-expanded-target-differential-metamorphic-conformance-v1.md"
)
# The cases whose VERIFIED rows the target-side laws read, plus A_legacy.
RELATION_CASES = (
    "P_native_identifiers",
    "R_fixed_direct",
    "S_fixed_named",
    "T_row_direct",
    "U_row_named",
    "W_join_shapes",
    "W_join_values",
    CASE,
    "X_aggregate_global",
    "X_aggregate_grouped",
    "Y_aggregate_constant",
    "A_window_ranking",
    "A_window_named",
    "A_window_qualify",
    "O_result_distinct",
    "O_result_limit",
    "O_result_membership",
    "S_set_forms",
    "S_set_multiplicity",
    "S_set_positions",
    "S_set_domains",
    "S_set_nesting",
    "S_set_boundaries",
    "S_set_producers",
    "S_set_membership",
    "S_set_literals",
)


def _build(root: Path, item: dict[str, Any]) -> tuple[Any, Any]:
    return probe.build_case(root, item["source"], item["contract"], item["policy"])


def _oracle_rows(target: str, case: str, variant: str) -> list[Any]:
    """The rows each per-case checker states for one VERIFIED variant."""
    if case in {"R_fixed_direct", "S_fixed_named"}:
        return cases.fixed_rows(
            target, named=case == "S_fixed_named", empty=variant.startswith("empty")
        )
    if case == "P_native_identifiers":
        number = "7" if variant.startswith("plain") else "11"
        return [] if variant.startswith("empty") else [[cases._integer(number)]] * 2
    if variant == "truth_table":
        return cases.truth_rows(target)
    if case in {"T_row_direct", "U_row_named"}:
        return cases.row_result_rows(target, empty=variant.startswith("empty"))
    if case in {"W_join_shapes", "W_join_values"}:
        return cases.join_rows(variant)
    if case == CASE:
        return cases.metamorphic_expectation(target, variant)[0]
    if case in probe.AGGREGATE_CASES:
        return cases.aggregate_rows(target, case, variant)
    if case in probe.WINDOW_CASES:
        return cases.WINDOW_EXPECTATIONS[cases.window_key(case, variant)]
    if case in probe.RESULT_CASES:
        return cases.result_expectation(target, case, variant)[0]
    return cases.set_expectation(target, case, variant)[0]


def _oracle_cases(target: str) -> list[dict[str, Any]]:
    """Receipt-shaped case entries whose observed rows are the case oracles."""
    result: list[dict[str, Any]] = [
        {"id": "A_legacy", "observations": [{"rows": cases.expected_rows("A_legacy")}]}
    ]
    for case in RELATION_CASES:
        entry: dict[str, Any] = {"id": case, "observations": [], "variants": []}
        for variant in probe.VARIANTS[case]:
            verified = probe.expected_status(case, variant, target) == "VERIFIED"
            if verified:
                rows = deepcopy(_oracle_rows(target, case, variant))
                entry["observations"].append({"rows": rows})
            entry["variants"].append(
                {
                    "variant": variant,
                    "submission_before": 0,
                    "submission_after": int(verified),
                }
            )
        result.append(entry)
    return result


def _rows(receipt_cases: list[dict[str, Any]], case: str, variant: str) -> Any:
    entry = next(item for item in receipt_cases if item["id"] == case)
    verified = [
        v["variant"]
        for v in entry["variants"]
        if v["submission_after"] != v["submission_before"]
    ]
    return entry["observations"][verified.index(variant)]


@pytest.mark.parametrize("target", TARGETS)
def test_metamorphic_premises_are_real_verified_emissions(
    tmp_path_factory: pytest.TempPathFactory, target: str
) -> None:
    root = tmp_path_factory.mktemp("slice15-premises-" + target)
    sql = {}
    for variant in probe.VARIANTS[CASE]:
        _, outcome = _build(root / variant, probe.fixture(target, CASE, variant))
        assert outcome.status == probe.expected_status(CASE, variant, target)
        assert outcome.status == "VERIFIED"
        document = probe.decode_public(serialize_project_sql_emission(outcome))
        _, labels, _ = cases.metamorphic_expectation(target, variant)
        assert [c["label"] for c in document["columns"]] == list(labels)
        assert document["request"]["owner"] == {
            "module": "main.pietto",
            "kind": "query",
            "name": "result",
        }
        sql[variant] = document["sql"]
        artifact = outcome.artifact
        assert artifact is not None
        data = portable.export_emission_observation(
            artifact, artifact.request
        ).canonical_bytes
        assert data is not None
        assert portable.verify_emission_observation(
            data, artifact, artifact.request
        ).corresponds
        decoded = pure.parse_emission_observation(data)
        assert decoded.status is pure.Status.OK and decoded.view is not None
        if variant != "join_chain_accumulated":
            continue
        # The RIGHT JOIN unit reads the LEFT JOIN unit as its left input: a
        # predecessor JOIN input, reachable without any multi-hop path.
        assert type(artifact.ast) is sql_ast.SQLJoinQuery
        units = artifact.ast.units
        assert [type(unit) for unit in units] == [
            joins.JoinBody,
            joins.JoinBody,
            sql_ast.RowBody,
        ]
        assert [unit.join.kind.value for unit in units[:2]] == ["left", "right"]
        assert units[1].inputs[0].producer is units[0]
        assert any(
            record.fields["producer"] == pure.Ref("join_body", 0)
            for record in decoded.view.kind("join_input")
        )
    # The two UNION ALL forms are different programs with one law between them.
    assert sql["union_filter_outer"] != sql["union_filter_operands"]


@pytest.mark.parametrize("policy", ("named_preserve", "named_bind"))
@pytest.mark.parametrize("target", TARGETS)
def test_alpha_renaming_and_unused_context_emit_identical_sql(
    tmp_path_factory: pytest.TempPathFactory, target: str, policy: str
) -> None:
    root = tmp_path_factory.mktemp("slice15-alpha-" + target)
    base = probe.native_fixture(target, policy)
    header = base["source"].split("table first:", 1)[0]

    def emitted(name: str, carried: str) -> Any:
        item = dict(base)
        item["source"] = header + (
            "table renamed_stage:\n    from rows\n    select:\n"
            f"        carried = {carried}\n"
            "table unrelated_valid:\n    from rows\n    select:\n"
            "        spare = decoy\n"
            "query result:\n    from renamed_stage\n    select:\n"
            "        id = carried\n"
        )
        return _build(root / name, item)[1]

    original = _build(root / "original", base)[1].artifact
    renamed = emitted("renamed", "id").artifact
    other = emitted("other", "decoy").artifact
    assert original is not None and renamed is not None and other is not None
    assert renamed.rendered.sql == original.rendered.sql
    assert renamed.parameter_uses == original.parameter_uses
    # Renaming onto another column is a different program, never an alias.
    assert other.rendered.sql != original.rendered.sql


@pytest.mark.parametrize("target", TARGETS)
def test_coordinated_drift_and_constructor_faults_meet_the_independent_walk(
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
) -> None:
    root = tmp_path_factory.mktemp("slice15-independence-" + target)
    item = probe.fixture(target, CASE, "join_chain_accumulated")
    artifact = _build(root / "base", item)[1].artifact
    assert artifact is not None and type(artifact.ast) is sql_ast.SQLJoinQuery
    request, query = artifact.request, artifact.ast
    for position in (2, 1):
        units = list(query.units)
        units[position] = (
            _swapped_outputs(units[2])
            if position == 2
            else replace(units[1], inputs=tuple(reversed(units[1].inputs)))
        )
        drifted = replace(query, units=tuple(units))
        rendered = render_join_sql(drifted)
        original, generated = sql_ast.build_row_requirements(request, drifted)
        assert rendered.sql != artifact.rendered.sql
        # SQL bytes, ranges, both denominators and parameters were rebuilt from
        # the drifted AST and agree with it; only plan correspondence refuses.
        checked = verify_project_sql_emission(
            replace(
                artifact,
                ast=drifted,
                rendered=rendered,
                original_requirements=original,
                generated_requirements=generated,
            ),
            request,
        )
        assert checked.issues == ("plan_ast_correspondence",)
    # The applicability gate the verifier shares with construction reports no
    # problem here, so a constructor fault meets only the independent walk.
    assert sql_ast.emission_blockers(request) == ()
    constructed = emitter.realize_rows

    def faulty(prepared: Any) -> Any:
        realization = constructed(prepared)
        built = realization.query
        assert type(built) is sql_ast.SQLJoinQuery
        units = tuple(
            _swapped_outputs(unit) if type(unit) is sql_ast.RowBody else unit
            for unit in built.units
        )
        return replace(realization, query=replace(built, units=units))

    monkeypatch.setattr(emitter, "realize_rows", faulty)
    blocked = _build(root / "fault", item)[1]
    assert blocked.status == "BLOCKED" and blocked.artifact is None
    assert [(b.code, b.detail) for b in blocked.blockers] == [
        ("PIE-B1008", "plan_ast_correspondence")
    ]


def _swapped_outputs(body: Any) -> Any:
    return replace(
        body,
        columns=tuple(reversed(body.columns)),
        terminals=tuple(reversed(body.terminals)),
    )


@pytest.mark.parametrize("target", TARGETS)
def test_multi_hop_path_join_stays_outside_the_admitted_join_domain(
    tmp_path_factory: pytest.TempPathFactory, target: str
) -> None:
    item = probe.join_witness(
        target,
        "query result:\n    from lhs\n"
        "    inner join lhs as r:\n        from lhs\n"
        "        via link: l -> r\n        via link: r -> l\n"
        "    select:\n        a = lhs.id\n",
        link=True,
    )
    checked, outcome = _build(tmp_path_factory.mktemp("slice15-via-" + target), item)
    assert not joins.admitted_join_shape(checked.plan)
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert {b.code for b in outcome.blockers} == {"PIE-B1003"}
    assert any(
        getattr(getattr(b.subject, "kind", None), "value", None) == "join"
        for b in outcome.blockers
    )


@pytest.mark.parametrize("target", TARGETS)
def test_oracle_rows_satisfy_every_metamorphic_law(target: str) -> None:
    cases.check_relations(_oracle_cases(target))


MUTATIONS = {
    "F1 R_fixed_direct query_preserve": ("R_fixed_direct", "query_bind", "drop"),
    "F2 named producer": ("P_native_identifiers", "named_preserve", "drop"),
    "F2 column identity": ("P_native_identifiers", "plain_preserve", "eleven"),
    "F3 intersect": ("S_set_forms", "intersect_all", "double"),
    "F3 union distinct": ("S_set_forms", "union_distinct", "double"),
    "F4 filter over union": (CASE, "union_filter_operands", "drop"),
    "F5 join partition": ("W_join_shapes", "anti", "zero"),
    "F6 noncommutation": ("O_result_limit", "inner_then_filter", "one"),
    "F7 global": ("X_aggregate_global", "where_false", "double"),
    "F8 nesting": ("S_set_nesting", "left_fold_except", "one"),
    "F9 named window": ("A_window_named", "shared", "drop"),
    "F9 peers": ("A_window_ranking", "peers", "rank"),
    "F9 qualify partition": ("A_window_qualify", "hidden", "drop"),
    "F9 qualify selection": ("A_window_qualify", "selected", "drop"),
    "F10 left": ("W_join_values", "left_marker", "marker"),
    "F10 chain": (CASE, "join_chain_accumulated", "zero_b"),
}


@pytest.mark.parametrize("law", sorted(MUTATIONS))
@pytest.mark.parametrize("target", TARGETS)
def test_each_law_rejects_a_single_changed_execution(target: str, law: str) -> None:
    receipt_cases = _oracle_cases(target)
    case, variant, change = MUTATIONS[law]
    observation = _rows(receipt_cases, case, variant)
    rows = observation["rows"]
    if change == "drop":
        rows.pop()
    elif change == "double":
        rows.extend(deepcopy(rows))
    elif change == "eleven":
        observation["rows"] = [[cases._integer("11")]] * 2
    elif change == "zero":
        rows.append([cases._integer("0")])
    elif change == "one":
        rows.append([cases._integer("1")])
    elif change == "rank":
        rows[0][2] = cases._integer("99")
    elif change == "marker":
        unmatched = next(row for row in rows if row[1] == cases.NULL)
        unmatched[2] = cases._integer("1")
    else:
        assert change == "zero_b"
        rows[0][1] = cases._integer("0")
    with pytest.raises(ValueError, match="metamorphic relation violated") as error:
        cases.check_relations(receipt_cases)
    assert law in str(error.value).split(": ", 1)[1].split(", ")


def test_a_missing_premise_execution_is_never_a_vacuous_law() -> None:
    receipt_cases = [c for c in _oracle_cases("postgres") if c["id"] != CASE]
    with pytest.raises(KeyError):
        cases.check_relations(receipt_cases)


class ReachedResources(facility_tests.FakeResources):
    """Acquisition succeeds, so the run reaches its case execution stage."""

    def acquire(self) -> None:
        self.manager = facility_tests.FakeConnection()
        self.startup_started = time.monotonic()

    def role_statements(self) -> tuple[tuple[str, bool], ...]:
        return ()

    def connect(self, *, query: bool) -> Any:
        return facility_tests.FakeConnection()


def test_a_relation_failure_routes_to_unresolved_attribution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt_cases = {c["id"]: c for c in _oracle_cases("postgres")}
    _rows(list(receipt_cases.values()), CASE, "union_filter_operands")["rows"].pop()

    def execute(case_id: str, *args: Any) -> None:
        result = args[-1]
        result.update(deepcopy(receipt_cases.get(case_id, {"variants": []})))
        result["id"] = case_id

    monkeypatch.setattr(facility, "Resources", ReachedResources)
    monkeypatch.setattr(facility, "installed_generation", lambda *args: {})
    monkeypatch.setattr(facility, "driver_info", lambda *args: {})
    monkeypatch.setattr(facility, "environment", lambda *args: {})
    monkeypatch.setattr(facility, "verify_environment", lambda *args: None)
    monkeypatch.setattr(facility, "transport", lambda *args: {})
    monkeypatch.setattr(facility, "verify_transport", lambda *args: None)
    monkeypatch.setattr(facility, "execute_case", execute)
    monkeypatch.setattr(cases, "setup", lambda target: ())
    # Per-case oracles are bypassed: only the cross-execution law can fail.
    monkeypatch.setattr(cases, "check_case", lambda *args: None)
    receipt = facility_tests._injected_run(tmp_path, monkeypatch)
    assert [c["id"] for c in receipt["cases"]] == list(cases.CASE_IDS)
    assert [
        (failure["stage"], failure["kind"], failure["category"])
        for failure in receipt["failures"]
    ] == [("case_execution", "ValueError", "UNRESOLVED_ATTRIBUTION")]
    assert "F4 filter over union" in receipt["failures"][0]["message"]
    assert receipt["cleanup"]["status"] == "success"


def test_slice15_contract_records_its_denominator_and_boundaries() -> None:
    document = " ".join(SPEC.read_text(encoding="utf-8").split())
    assert "33 MiB" in document and "34,603,008" in document
    assert "62 cases/190 public documents per target" in document
    assert "postgres157 VERIFIED,4 INPUT_REJECTED,29 BLOCKED" in document
    assert "mysql154 VERIFIED,4 INPUT_REJECTED,32 BLOCKED" in document
    for family in ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10"):
        assert f"| {family} |" in document
    assert facility.MAX_RECEIPT == 34_603_008


@pytest.mark.parametrize("target", TARGETS)
def test_g8_coordinated_base_scan_shortcut_fails_the_independent_ranking(target):
    receipt_cases = _oracle_cases(target)
    left = deepcopy(_rows(receipt_cases, "O_result_membership", "anti_limit0")["rows"])
    _rows(receipt_cases, "A_window_qualify", "selected")["rows"] = left
    _rows(receipt_cases, "A_window_qualify", "hidden")["rows"] = []
    # Partition/disjointness alone would accept this coordinated wrong result.
    with pytest.raises(ValueError, match="F9 qualify selection"):
        cases.check_relations(receipt_cases)
