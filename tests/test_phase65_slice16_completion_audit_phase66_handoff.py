"""Bounded source/reference traceability for the Phase65 completion audit.

Behavior correctness is established by the cited existing tests and execution
receipts. These checks do not run a second conformance or history acquisition.
"""

from __future__ import annotations

import ast
from functools import cache
from pathlib import Path
import re

from _pietto_repository_facts import REPOSITORY_FACTS


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/spec/phase65-completion-audit-phase66-handoff-v1.md"
ROUTE = (
    ROOT
    / "docs/spec/phase65-project-sql-plan-product-phase-initiation-gate-source-audit-architecture-route-lock-v1.md"
)
PHASE_ENTRY = "d7af544dd4ce48891d5fe2596ab23e494f48d4ab"
BASELINE = "128388bc258d6ee861c0128c42324fca712c0dcc"
# Independently read back from Git and natural attempt1 CI during this audit.
# No unavailable Git objects or online services are required by these tests.
PUBLISHED = (
    (
        "S01/publication",
        "3d89ebb45a59cee243e03a293f479f3011807f9f",
        "29dfc9b7be09a16336861ed497727de2fa21f75e",
        "d7af544dd4ce48891d5fe2596ab23e494f48d4ab",
        "34512999929",
        "success",
    ),
    (
        "S02/publication",
        "adb55b84e60f1fc1439e5b7f6e2d9fae81dba12b",
        "b349f9c50d6d3fc28f9cdb621d7ba7d7b1fe2bba",
        "3d89ebb45a59cee243e03a293f479f3011807f9f",
        "34556059755",
        "success",
    ),
    (
        "S03/publication",
        "56fe50b685692ff5ed9e58202d7116ae5a221775",
        "f99b74e38d81bdc61aaffeea5abf0072734238c3",
        "adb55b84e60f1fc1439e5b7f6e2d9fae81dba12b",
        "34562319623",
        "success",
    ),
    (
        "S04/publication",
        "d87070d9ab0a261dd0f55f7ef1aceeee966b03dc",
        "d001229f4ab6815d76ab27eb7963e472cb86d983",
        "56fe50b685692ff5ed9e58202d7116ae5a221775",
        "34574113991",
        "success",
    ),
    (
        "S05/publication",
        "ec0a9f3a535dc4e4284e1d064c676a217750dc43",
        "4ef49bbce9019699c2c3875249b51e1c52b08182",
        "d87070d9ab0a261dd0f55f7ef1aceeee966b03dc",
        "34651949568",
        "success",
    ),
    (
        "S06/publication",
        "720a296a5ac7aa3181afb82ccd42453186ebba1c",
        "b0977930d42ddb3214021cb0a1174a1b3ef0900c",
        "ec0a9f3a535dc4e4284e1d064c676a217750dc43",
        "34669857637",
        "success",
    ),
    (
        "S07/publication",
        "0966ecb309f6243baf4490a423ebcb47af1f909c",
        "3d4d7f967680309f9ac5a9a339e510fe174903bb",
        "720a296a5ac7aa3181afb82ccd42453186ebba1c",
        "34682271444",
        "success",
    ),
    (
        "S08/publication",
        "86bf4e6e5a525e0c099339f0ea29c4b51ab57f04",
        "a813b16992cb2d355aa61a8eac259c3ee715bc69",
        "0966ecb309f6243baf4490a423ebcb47af1f909c",
        "34686688681",
        "success",
    ),
    (
        "S09/publication",
        "9de7991498e2258bf41557bae95f91152c9670f3",
        "27dfeff90478e366eb3589544f1b9e07108d0c99",
        "86bf4e6e5a525e0c099339f0ea29c4b51ab57f04",
        "34715387544",
        "success",
    ),
    (
        "S10/publication",
        "0c025b1060a93b9ab0999f71575830b7c25757ed",
        "3416da1d1f04614e30e6b525c4f91b603edb6051",
        "9de7991498e2258bf41557bae95f91152c9670f3",
        "34723478209",
        "success",
    ),
    (
        "S11/publication",
        "a7a48a1e3c7b288e051213fdb163dd7226d0cd60",
        "c9472766324a40c543c97c2f17bce897a7dfdd27",
        "0c025b1060a93b9ab0999f71575830b7c25757ed",
        "34739921800",
        "success",
    ),
    (
        "S12/publication",
        "a0e235f9c858187a7b5f25e47c1413e61a8899fe",
        "eb0bcb33e2291a7114ab9c464959fdc8488ee551",
        "a7a48a1e3c7b288e051213fdb163dd7226d0cd60",
        "34744544990",
        "success",
    ),
    (
        "S13/publication",
        "079ed2ecfbcf71e9adc11dec898a1a61120ae7f5",
        "d227daf60175a6100be6dca2d07023b75b53b240",
        "a0e235f9c858187a7b5f25e47c1413e61a8899fe",
        "34750296114",
        "success",
    ),
    (
        "S14/initial-failed",
        "a4db6382dd9d01867529605b14c902aef135bfd2",
        "3c17ad7ec1703d4e743494ba4c0525ae4fa23d2a",
        "079ed2ecfbcf71e9adc11dec898a1a61120ae7f5",
        "34792068365",
        "failure",
    ),
    (
        "S14/repair-child",
        "b6278c94b74f60fb32b4314e992c22974d4519a0",
        "20460df34ed65dc07dfb5a536f7fcf7b511ea17c",
        "a4db6382dd9d01867529605b14c902aef135bfd2",
        "34793858855",
        "success",
    ),
    (
        "S15/publication",
        "128388bc258d6ee861c0128c42324fca712c0dcc",
        "75ba55ccbd70cf482cde8b3a9be10055955babd7",
        "b6278c94b74f60fb32b4314e992c22974d4519a0",
        "34842205857",
        "success",
    ),
)
REQUIRED_WITNESSES = {
    "P01": "tests/test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan.py::test_root_and_selection_are_explicit_and_never_name_resolved",
    "P02": "tests/test_phase65_slice3_named_producer_graph_repeated_imported_uses_scope_local_symbols.py::test_named_chain_uses_immediate_exports",
    "P03": "tests/test_phase65_slice5_seven_join_kinds_match_scopes_obligation_retention.py::test_accumulated_left_has_all_previous_and_current_nulling",
    "P04": "tests/test_phase65_slice10_typed_fixed_literal_envelope_bind_use_layout.py::test_equal_values_remain_separate_and_let_references_do_not_reextract",
    "P05": "tests/test_phase65_slice12_forward_reverse_source_map_queries.py::test_flat_original_inventory_and_exact_forward_reverse_relations",
    "P06": "tests/test_phase65_slice11_complete_demand_obligation_report.py::test_layer1_rejects_missing_demands_and_literal_constituents",
    "P07": "tests/test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan.py::test_verifier_and_inspection_never_call_construction",
    "P08": "tests/test_phase65_slice14_portable_boundary_minimal_process_integration.py::test_coherent_document_is_not_runtime_authentication",
    "P09": "tests/test_phase65_slice14_portable_boundary_minimal_process_integration.py::test_registered_process_matrix_and_same_child_origins",
    "P10": "tests/test_phase65_slice13_explicit_target_profile_requirement_assessment.py::test_new_consumers_remain_private_without_dynamic_or_renderer_access",
}


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    value = document.split(marker, 1)[1]
    return value.split("\n## ", 1)[0]


def _rows(document: str, pattern: str) -> tuple[tuple[str, ...], ...]:
    return tuple(
        tuple(cell.strip() for cell in line.strip("|").split("|"))
        for line in document.splitlines()
        if re.match(pattern, line)
    )


@cache
def _definitions(relative: str) -> dict[str, ast.FunctionDef | ast.ClassDef]:
    path = ROOT / relative
    tree = ast.parse(REPOSITORY_FACTS.python(path).text, filename=relative)
    result = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.ClassDef))
    }
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            result.update(
                (f"{node.name}.{member.name}", member)
                for member in node.body
                if isinstance(member, (ast.FunctionDef, ast.ClassDef))
            )
    return result


def test_publication_inputs_keep_exact_roles_trees_parents_and_ci() -> None:
    document = SPEC.read_text(encoding="utf-8")
    rows = _rows(_section(document, "Published Slice1–15 lineage"), r"^\| S\d{2}/")
    actual = []
    for row in rows:
        match = re.search(r"\[(\d+)\]", row[4])
        assert match is not None and "; push/main/1" in row[4]
        actual.append(
            (
                row[0],
                *(item.strip("`") for item in row[1:4]),
                match[1],
                row[5].split()[0],
            )
        )
    assert tuple(actual) == PUBLISHED
    previous = PHASE_ENTRY
    for _, commit, tree, parent, run, outcome in PUBLISHED:
        assert re.fullmatch(r"[0-9a-f]{40}", commit)
        assert re.fullmatch(r"[0-9a-f]{40}", tree)
        assert parent == previous and run.isascii() and run.isdigit()
        assert outcome in {"success", "failure"}
        previous = commit
    assert previous == BASELINE
    assert [r[0] for r in PUBLISHED if r[5] == "failure"] == ["S14/initial-failed"]
    assert [r[0] for r in PUBLISHED if r[0].endswith("repair-child")] == [
        "S14/repair-child"
    ]
    assert "failure (3.12 failed;3.13 success)" in rows[13][5]


def test_exits_keep_original_meanings_qualified_acceptance_and_behavior_links() -> None:
    document = SPEC.read_text(encoding="utf-8")
    original = ROUTE.read_text(encoding="utf-8")
    current = _rows(_section(document, "P01–P10 material acceptance"), r"^\| P\d{2} \|")
    source = _rows(_section(original, "9. Phase-65 completion exits"), r"^\| P\d{2} \|")
    assert tuple(row[0] for row in current) == tuple(f"P{n:02}" for n in range(1, 11))
    assert tuple((row[0], row[1]) for row in current) == tuple(source)
    for row in current:
        assert len(row) == 6 and row[5] == "0"
        assert f"`{REQUIRED_WITNESSES[row[0]]}`" in row[3]
        assert "::" in row[2] and row[4]
    assert (
        "Phase65 material exits = 10/10 within the explicitly approved support domain"
        in document
    )
    assert "Phase65 self-owned-open = 0" in document
    assert (
        "静态traceability" in document
        and "不是runtime correctness的替代证明" in document
    )


def test_decisions_and_all_counterexamples_have_unique_current_dispositions() -> None:
    document = SPEC.read_text(encoding="utf-8")
    original = ROUTE.read_text(encoding="utf-8")
    decisions = _rows(document, r"^\| D65\.\d{2} \|")
    source_decisions = _rows(original, r"^\| D65\.\d{2} \|")
    assert tuple((r[0], r[1]) for r in decisions) == tuple(
        (r[0], r[1]) for r in source_decisions
    )
    assert tuple(r[0] for r in decisions) == tuple(f"D65.{n:02}" for n in range(1, 13))
    assert all(len(row) == 5 and all(row) for row in decisions)
    questions = _rows(document, r"^\| K\d{2} \|")
    assert tuple(row[0] for row in questions) == tuple(f"K{n:02}" for n in range(1, 8))
    examples = _rows(_section(document, "C01–C43 disposition"), r"^\| C\d{2} \|")
    original_examples = _rows(original, r"^\| C\d{2} \|")
    assert (
        tuple(r[0] for r in examples)
        == tuple(r[0] for r in original_examples)
        == tuple(f"C{n:02}" for n in range(1, 44))
    )
    assert all(len(row) == 3 and row[1] and "::test_" in row[2] for row in examples)
    assert "UNAPPROVED_PRODUCT_POLICY" in questions[5][2]


def test_inherited_transferred_and_later_atoms_are_complete_and_distinct() -> None:
    document = SPEC.read_text(encoding="utf-8")
    original = ROUTE.read_text(encoding="utf-8")
    inherited = _rows(document, r"^\| I\d{2} \|")
    transferred = _rows(document, r"^\| T\d{2} \|")
    later = _rows(document, r"^\| L\d{2} ")
    assert tuple(r[0] for r in inherited) == tuple(f"I{n:02}" for n in range(1, 13))
    assert tuple(r[0] for r in transferred) == tuple(f"T{n:02}" for n in range(1, 9))
    assert tuple(r[0].split()[0] for r in later) == tuple(
        f"L{n}" for n in range(66, 98)
    )
    for row in (*inherited, *transferred):
        assert f"| {row[1]} |" in original
    assert all("INHERITED_CLOSED" in r[2] for r in inherited)
    assert all("DELIVERED within approved domain" in r[3] for r in transferred)
    assert all("TENTATIVE / OWNER ONLY" in r[2] for r in later if int(r[0][1:3]) >= 91)
    assert "PIE-S2333" in document and "explicit SELECT bridge" in document
    assert "Float binding不解除Float/alias row-equivalence" in document


def test_every_cited_current_entrypoint_and_behavior_node_exists() -> None:
    document = SPEC.read_text(encoding="utf-8")
    citations = re.findall(r"`((?:src|tests)/[^`]+\.py)::([\w.]+)`", document)
    assert citations
    for relative, name in citations:
        node = _definitions(relative)[name]
        if name.startswith("test_"):
            assert relative.startswith("tests/") and isinstance(node, ast.FunctionDef)
        else:
            assert isinstance(node, (ast.FunctionDef, ast.ClassDef))
    # A test may delegate its assertions; existence does not prove its behavior.
    for target in re.findall(
        r"\]\(([^)]+)\)", _section(document, "Controlling references")
    ):
        assert not target.startswith("http") and (SPEC.parent / target).is_file()


def test_real_consumer_handoff_does_not_approve_phase66_implementation() -> None:
    document = SPEC.read_text(encoding="utf-8")
    handoff = _rows(_section(document, "Phase66 consumer map"), r"^\| H\d{2} \|")
    decisions = _rows(_section(document, "Pending Phase66 decisions"), r"^\| Q\d{2} \|")
    assert tuple(r[0] for r in handoff) == tuple(f"H{n:02}" for n in range(1, 9))
    assert tuple(r[0] for r in decisions) == tuple(f"Q{n:02}" for n in range(1, 9))
    assert all(len(r) == 5 and "::" in r[2] and r[3] and r[4] for r in handoff)
    assert "UNAPPROVED_IMPLEMENTATION_DECISION" in document
    for phrase in (
        "fresh phase-initiation discussion和route approval",
        "不预设Slice数、编号路线或第一个实现Slice",
        "每statement actual use-to-slot map",
        "target-only须新assessment，不改neutral plan",
        "Pietto已有legacy SQL generation",
        "新ProjectSQLPlan pipeline在Phase65不交付dialect SQL AST/text emission",
        "Phase67保留result/Arrow，68保留actual resources/fulfillment",
    ):
        assert phrase in " ".join(document.split())


def test_repair_history_and_observation_denominators_remain_honest() -> None:
    document = " ".join(SPEC.read_text(encoding="utf-8").split())
    for phrase in (
        "F65S15-01",
        "F65S15-02",
        "ProjectIRProvidedRelationOrdering",
        "ProjectRelationOrdering",
        "ordinary/rebound property/ORDER links",
        "source-bearing",
        "pure OK不认证source/runtime roots/DB",
        "single-interpreter",
        "双版本insertion order",
        "supported Python3.12/3.13不保证每个runner同时安装两者",
        "Single portable document",
        "Aggregate differential envelope",
        "不是一个Document",
        "不是永久quota",
        "不冻结未来registry topology",
        "不猜skip causes",
        "observation unavailable",
        "直接publication approval未改变source/test/document",
        "本文不嵌入未来自己的Git身份",
    ):
        assert phrase in document
