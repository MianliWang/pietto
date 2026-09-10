"""Static source and immutable-history assurance for the Phase64 audit."""

from __future__ import annotations

import ast
from pathlib import Path
import re
import subprocess

import pytest

from _pietto_repository_facts import REPOSITORY_FACTS


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "docs/spec/phase64-completion-audit-phase65-handoff-v1.md"
ROUTE = (
    REPO_ROOT
    / "docs/spec/phase64-flat-relational-algebra-product-phase-initiation-gate-v3-source-audit-architecture-route-lock-v1.md"
)
PHASE_ENTRY = "bb52135038973b40638ff86367ba478846f898c6"
BASELINE = "ceccba408d042c3bfe08c90a9c67b57cd690541a"
BASELINE_TREE = "6462e82c508a2b9cbe06094e6dfc0166a243ec2e"
EXIT_IDS = tuple(f"E{number:02}" for number in range(1, 13))
# Independently reviewed Git/CI identities, not derived from the audit text.
PUBLISHED = (
    ("f483d2d3a73edbfd6b203fb3014758095e398e23", "34049044651"),
    ("691245e48c387357f700d19b9f7318bbf79f3045", "34077572865"),
    ("ac32bd5d8f98c7952f4276f8ba2a8c7bdc332c73", "34092606235"),
    ("317ae65440447997740b58bb4eac774aa7df19b8", "34102086024"),
    ("dae18c78ab38e4d6fbe517218b92d6f2506da489", "34165657512"),
    ("dc194d3932656af7d41b1fd7bcabb5c4f7c59c03", "34192534911"),
    ("32632ea8dd5057034d2b5add861c1d2850ae5dee", "34194052736"),
    ("04b234a38cb92f647e3a4a869117b15fa1163928", "34205094377"),
    ("241be04da179969ddb1bd50381ee9ac58cea1641", "34238303080"),
    ("66c0e08628834c88e0a68013d036e32baad24e56", "34253791709"),
    ("73fcb2bcdbe27775fc3bf9500df8d68006a62578", "34265355099"),
    ("9333faeae1e544f1be70f17bfcb67d06fd57f9c4", "34305449725"),
    ("ceccba408d042c3bfe08c90a9c67b57cd690541a", "34451916850"),
)

# One required existing witness per original exit; every extra cited node is checked too.
WITNESSES = (
    (
        "E01",
        "tests/test_phase64_slice4_effective_output_join_first_generic_vertical_closure.py::test_minimal_generic_and_refined_vertical_completion",
    ),
    (
        "E02",
        "tests/test_phase64_slice5_cross_right_full_output_shapes_null_extension_property_transfer.py::test_minimal_new_kinds_complete_exact_rows",
    ),
    (
        "E03",
        "tests/test_phase64_slice6_semi_anti_left_occurrence_retention_existence_semantics.py::test_authored_existence_retains_exact_left_fields_and_both_input_uses",
    ),
    (
        "E04",
        "tests/test_phase64_slice3_generic_on_condition_semantics_authority_separation.py::test_refinement_keeps_base_and_conjunct_occurrences",
    ),
    (
        "E05",
        "tests/test_phase64_slice10_project_ir_composition_verification_invalidation_inspection_pure_boundary.py::test_effective_input_vertical_to_verified_private_observation",
    ),
    (
        "E06",
        "tests/test_phase64_slice7_single_match_direction_unit_scoped_proof_obligation_warning_diagnostics.py::test_unproved_actual_matches_warn_on_success_in_every_mode",
    ),
    (
        "E07",
        "tests/test_phase64_slice8_row_equivalence_distinct_quotient_grain_origin.py::test_join_outputs_compare_only_visible_projection",
    ),
    (
        "E08",
        "tests/test_phase64_slice9_set_operations_explicit_all_distinct_output_identity.py::test_six_laws_include_zero_and_null_class",
    ),
    (
        "E09",
        "tests/test_phase64_slice5_cross_right_full_output_shapes_null_extension_property_transfer.py::test_new_kinds_use_the_existing_tail_builders",
    ),
    (
        "E10",
        "tests/test_phase64_slice10_ir_corruption_and_invalidation.py::test_semantic_evidence_changes_require_rebuild_and_fresh_verification",
    ),
    (
        "E11",
        "tests/test_phase64_slice6_semi_anti_left_occurrence_retention_existence_semantics.py::test_real_explicit_project_check_and_unchanged_json_shape",
    ),
    (
        "E12",
        "tests/test_phase64_slice10_ir_corruption_and_invalidation.py::test_all_except_membership_and_repeated_uses_reach_the_consumer",
    ),
)


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


def _definitions(relative: str) -> dict[str, ast.FunctionDef | ast.ClassDef]:
    path = REPO_ROOT / relative
    tree = ast.parse(REPOSITORY_FACTS.python(path).text, filename=str(path))
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.ClassDef))
    }


def _publication_rows() -> tuple[tuple[str, ...], ...]:
    section = _section(SPEC.read_text(encoding="utf-8"), "Published Scope And Lineage")
    return tuple(
        tuple(cell.strip().strip("`") for cell in line.strip("|").split("|"))
        for line in section.splitlines()
        if re.match(r"^\| \d+ \|", line)
    )


def _git(*arguments: str) -> str:
    return subprocess.check_output(
        ("git", *arguments), cwd=REPO_ROOT, text=True
    ).strip()


def test_original_exits_decisions_and_supplements_remain_distinct() -> None:
    document = SPEC.read_text(encoding="utf-8")
    original = ROUTE.read_text(encoding="utf-8")
    assert tuple(re.findall(r"^(E\d{2}) ", original, re.MULTILINE)) == EXIT_IDS
    assert (
        tuple(
            re.findall(
                r"^\| (E\d{2}) \|",
                _section(document, "E01–E12 Acceptance Map"),
                re.MULTILINE,
            )
        )
        == EXIT_IDS
    )
    for number in range(1, 9):
        assert f"D{number:02}" in document and f"### D{number:02} " in original
    for phrase in (
        "N=11",
        "D07-FLOAT-DEFERRED",
        "S9-NAME-1",
        "补充决定单独注明时点，不回填原D07或D04/D06",
        "Phase64 material exits = 12/12 within the explicitly approved support domain",
        "Phase64 self-owned-open = 0",
    ):
        assert phrase in document


@pytest.mark.parametrize("exit_id,witness", WITNESSES)
def test_exit_has_a_real_producer_consumer_and_required_behavior_witness(
    exit_id: str, witness: str
) -> None:
    document = SPEC.read_text(encoding="utf-8")
    rows = tuple(
        line for line in document.splitlines() if line.startswith(f"| {exit_id} |")
    )
    assert len(rows) == 1 and rows[0].endswith("| 0 |")
    assert f"`{witness}`" in rows[0]
    sources = re.findall(r"`(src/[^`]+\.py)::(\w+)`", rows[0])
    assert len(sources) == 2
    for relative, name in sources:
        assert name in _definitions(relative)


def test_all_cited_behavior_nodes_and_private_handoff_entrypoints_exist() -> None:
    document = SPEC.read_text(encoding="utf-8")
    nodes = re.findall(r"`(tests/[^`]+\.py)::(test_\w+)`", document)
    assert nodes
    for relative, name in nodes:
        function = _definitions(relative)[name]
        assert isinstance(function, ast.FunctionDef)
        assert any(isinstance(node, ast.Assert) for node in ast.walk(function))
    section = _section(document, "Phase-65 Consumer Handoff")
    for filename, names in (
        (
            "project_completed_semantics.py",
            (
                "build_project_completed_semantic_result",
                "with_project_single_match_requests",
            ),
        ),
        ("project_query_block_ir.py", ("build_project_query_block_ir",)),
        (
            "project_query_block_ir_verification.py",
            (
                "verify_project_query_block_ir",
                "build_project_query_block_ir_analysis_bundle",
            ),
        ),
        (
            "project_query_block_ir_inspection.py",
            ("build_project_query_block_ir_inspection",),
        ),
        (
            "project_query_block_ir_pure_boundary.py",
            ("evaluate_project_query_block_ir_document",),
        ),
    ):
        for name in names:
            assert name in _definitions(f"src/pietto/_project/{filename}")
            assert f"`{name}`" in section
    assert tuple(re.findall(r"^\| (H\d{2}) ", section, re.MULTILINE)) == tuple(
        f"H{i:02}" for i in range(1, 9)
    )
    for fact in (
        "active_output",
        "active_properties",
        "ProjectIRJoinInputCorrespondence",
        "membership",
        "source spans",
        "nulling",
        "order_proofs",
        "Decimal",
        "enforcement_required",
        "Phase62 VERIFIED prerequisite",
    ):
        assert fact in section


def test_publication_roles_and_observation_sources_are_not_conflated() -> None:
    rows = _publication_rows()
    assert len(rows) == len(PUBLISHED) == 13
    for position, (row, (commit, run)) in enumerate(
        zip(rows, PUBLISHED, strict=True), 1
    ):
        assert row[0] == str(position) and row[2] == commit
        assert row[4] == (PHASE_ENTRY if position == 1 else PUBLISHED[position - 2][0])
        assert (
            f"[{run}](https://github.com/MianliWang/pietto/actions/runs/{run})"
            == row[5]
        )
        assert row[6].isdigit() and row[7].isdigit() and row[6] != row[7]
    assert rows[0][1] == "Slice1 initial publication"
    assert rows[1][1] == "Slice1 reconciliation terminal"
    assert rows[2][1] == "Unnumbered F01/F02 repair"
    assert rows[6][1] == "Dependabot PR73 maintenance"
    section = " ".join(
        _section(
            SPEC.read_text(encoding="utf-8"), "Published Scope And Lineage"
        ).split()
    )
    for phrase in (
        "**不是failed head**",
        "不是一Slice一commit",
        "Ruff0.16.4 -> 0.16.6",
        "47项corrective accounting",
        "不是47次失败publication",
        "12568 passed",
        "12564 passed /4 skipped",
        "不从数值推断skip原因",
    ):
        assert phrase in section


def test_fixed_immutable_git_lineage_and_maintenance_delta() -> None:
    for commit in (PHASE_ENTRY, *(row[0] for row in PUBLISHED)):
        present = subprocess.run(
            ("git", "cat-file", "-e", f"{commit}^{{commit}}"),
            cwd=REPO_ROOT,
            capture_output=True,
        )
        if present.returncode:
            pytest.skip(f"exact historical Git object {commit} is unavailable")
    assert _git(
        "rev-list", "--first-parent", "--reverse", f"{PHASE_ENTRY}..{BASELINE}"
    ).splitlines() == [row[0] for row in PUBLISHED]
    assert _git("merge-base", PHASE_ENTRY, BASELINE) == PHASE_ENTRY
    for row in _publication_rows():
        assert _git("show", "-s", "--format=%T %P", row[2]) == f"{row[3]} {row[4]}"
    assert _git("show", "-s", "--format=%T", BASELINE) == BASELINE_TREE
    maintenance = PUBLISHED[6][0]
    assert _git("diff", "--name-only", f"{maintenance}^", maintenance).splitlines() == [
        "tests/test_phase63_slice1_joined_query_block_product_architecture_source_audit_future_roadmap_route_lock.py",
        "uv.lock",
    ]
    assert _git(
        "log", "--format=%H", f"{PHASE_ENTRY}..{BASELINE}", "--", "uv.lock"
    ).splitlines() == [maintenance]
    assert not _git(
        "diff",
        "--name-only",
        PHASE_ENTRY,
        BASELINE,
        "--",
        "src/pietto/_project/json_v2.py",
        "pyproject.toml",
        ".github/workflows",
    )


def test_support_and_unapproved_phase65_planning_are_explicit() -> None:
    document = SPEC.read_text(encoding="utf-8")
    support = _section(document, "Support And Non-Goal Ledger")
    for phrase in (
        "EXPLICIT_MODULES",
        "LEGACY_FLAT",
        "PACKAGE_ROOT",
        "PIE-S2337",
        "LOOSE/CHECKED/STRICT",
        "WARNING",
        "PIE-S2338",
        "ERROR",
        "Float/aliases",
        "无finite-literal例外",
        "UNION ALL只要求shape/type",
        "S9-NAME-1",
        "Phase66",
        "Phase68",
        "Phase72",
        "Phase73",
        "check success、runtime IR VERIFIED、pure-document OK、backend lowerability、runtime fulfillment互不等同",
    ):
        assert phrase in support
    planning = " ".join(
        _section(document, "Phase-65 Open Questions And Planning Preference").split()
    )
    for phrase in (
        "Q65.1",
        "Q65.2",
        "Q65.3",
        "Q65.4",
        "Q65.5",
        "no approved numbered route",
        "compare 14–16 real delivery Slices; 16 is the preferred initial candidate",
        "不是approved N=16",
        "principal invariant",
        "first consumer",
    ):
        assert phrase in planning


def test_private_format_retains_historical_version_identity() -> None:
    for filename, marker in (
        ("project_ir_pure_boundary.py", "pietto.project-ir-inspection.v1"),
        ("project_phase62_pure_boundary.py", "pietto.phase62-inspection.v1"),
        (
            "project_query_block_ir_pure_boundary.py",
            "pietto.phase63-query-block-ir-inspection.v1",
        ),
        (
            "project_query_block_ir_pure_boundary.py",
            "pietto.phase64-flat-relational-ir-inspection.v1",
        ),
    ):
        assert (
            marker
            in REPOSITORY_FACTS.python(
                REPO_ROOT / "src/pietto/_project" / filename
            ).string_literals
        )
    assert "不重新命名旧version或假称lifted bytes未变" in SPEC.read_text(
        encoding="utf-8"
    )
