"""Static decision traceability; future ProjectSQLPlan behavior is not implemented."""

from __future__ import annotations

import ast
import io
from pathlib import Path
import re
import subprocess
import tarfile

import pytest

from _pietto_repository_facts import REPOSITORY_FACTS


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / (
    "docs/spec/phase65-project-sql-plan-product-phase-initiation-gate-"
    "source-audit-architecture-route-lock-v1.md"
)
BASELINE = "d7af544dd4ce48891d5fe2596ab23e494f48d4ab"
BASELINE_TREE = "39725359e10660ef425eb831164e100cbf649e0b"
BASELINE_PARENT = "ceccba408d042c3bfe08c90a9c67b57cd690541a"
DECISIONS = tuple(f"D65.{i:02}" for i in range(1, 13))


def _section(document: str, heading: str, level: int = 2) -> str:
    marker = f"{'#' * level} {heading}\n"
    assert document.count(marker) == 1
    tail = document.split(marker, 1)[1]
    return re.split(r"\n#{1," + str(level) + r"} ", tail, maxsplit=1)[0]


def _rows(section: str) -> tuple[tuple[str, ...], ...]:
    return tuple(
        tuple(cell.strip() for cell in line.strip("|").split("|"))
        for line in section.splitlines()
        if line.startswith("| ") and not line.startswith("| ---")
    )[1:]


def test_full_gate_decisions_questions_and_cross_checks_have_answers() -> None:
    document = SPEC.read_text(encoding="utf-8")
    assert tuple(re.findall(r"^### (D65\.\d{2}) —", document, re.M)) == DECISIONS
    gate = _section(document, "4. Full mandatory Gate: thirty answers")
    answers = _rows(gate.split("### Twelve question groups", 1)[0])
    assert tuple(row[0] for row in answers) == tuple(map(str, range(1, 31)))
    assert all(len(row) == 3 and row[2].strip() for row in answers)
    groups = gate.split("| Group | Actual answer |", 1)[1]
    groups, cross = groups.split("| Cross-cutting check", 1)
    assert tuple(re.findall(r"^\| ([A-L]) ", groups, re.M)) == tuple("ABCDEFGHIJKL")
    assert tuple(re.findall(r"^\| (X\d) ", cross, re.M)) == tuple(
        f"X{i}" for i in range(1, 9)
    )
    assert "Covered by" not in groups


def test_decisions_have_current_source_test_and_future_acceptance_trace() -> None:
    document = SPEC.read_text(encoding="utf-8")
    trace = _rows(
        _section(document, "Current source reconciliation and decision trace", 3)
    )
    assert tuple(row[0] for row in trace) == DECISIONS
    for row in trace:
        assert len(row) == 8
        assert row[1] in {"USER_DECISION_REQUIRED", "ARCHITECTURE_DECISION"}
        assert len(re.findall(r"`src/[^`]+\.py::\w+`", " ".join(row))) == 2
        assert re.fullmatch(r"`tests/test_[^`]+\.py::test_\w+`", row[4])
        assert re.findall(r"C\d{2}", row[5]) and row[6] and row[7]
    # Positive current-law checks use the existing shared acquisition owner.
    lookup = REPOSITORY_FACTS.python(
        REPO_ROOT / "src/pietto/semantic/capability_lookup.py"
    )
    assert {"domain_complete", "unknown_reason", "evidence"} <= lookup.identifiers
    assert "without normalization, inference, or fallback" in lookup.text
    architecture = (
        REPO_ROOT / "docs/architecture/identity-and-authority-laws-v1.md"
    ).read_text(encoding="utf-8")
    assert "canonical bytes != semantic identity" in architecture
    assert "use occurrence != declaration" in architecture


def test_exclusive_ledgers_and_every_future_owner_have_actual_dispositions() -> None:
    document = SPEC.read_text(encoding="utf-8")
    inherited = _rows(
        _section(document, "3A. INHERITED_CLOSED — reuse, do not reimplement", 3)
    )
    transferred = _rows(
        _section(
            document, "3B. TRANSFERRED_TO_PHASE65 — actual current deliverables", 3
        )
    )
    assert inherited and transferred
    for ledger in (inherited, transferred):
        assert len(ledger) == len({row[0] for row in ledger})
    handoff = _rows(_section(document, "H01–H08 actual input handoff", 3))
    assert tuple(row[0] for row in handoff) == tuple(f"H{i:02}" for i in range(1, 9))
    assert all(len(row) == 4 and all(row) for row in handoff)
    assert set(row[0] for row in inherited).isdisjoint(row[0] for row in transferred)
    later = _section(document, "3C. RETAINED_LATER — exact remaining owners", 3)
    assert "section 6" in later and "not claimed to exist" in later
    owners = _rows(_section(document, "6. Whole-roadmap readiness: every Phase66–97"))
    assert tuple(row[0].split()[0] for row in owners) == tuple(map(str, range(66, 98)))
    assert all(len(row) == 4 and all(row) for row in owners)
    for row in owners:
        assert any(
            word in row[1]
            for word in (
                "CORE_NOW",
                "MINIMUM_NOW",
                "CONTRACT_ONLY_NOW",
                "DEFER_BY_NECESSITY",
                "NO_CURRENT_USE",
            )
        )


def test_sixteen_deliveries_cover_every_counterexample_and_completion_exit() -> None:
    document = SPEC.read_text(encoding="utf-8")
    route = _section(document, "8. Selected sixteen-Slice route")
    deliveries = _rows(route.split("### Actual 14/15/16 alternatives", 1)[0])
    assert tuple(row[0] for row in deliveries) == tuple(map(str, range(1, 17)))
    assert all(len(row) == 6 and all(row) for row in deliveries)
    counterexamples = tuple(re.findall(r"^\| (C\d{2}) \|", document, re.M))
    assert counterexamples == tuple(f"C{i:02}" for i in range(1, 44))
    assert set(counterexamples) <= set(
        re.findall(r"C\d{2}", " ".join(row[4] for row in deliveries))
    )
    exits = _rows(_section(document, "9. Phase-65 completion exits"))
    assert tuple(row[0] for row in exits) == tuple(f"P{i:02}" for i in range(1, 11))
    alternatives = _section(document, "Actual 14/15/16 alternatives", 3)
    assert all(
        label in alternatives for label in ("**14:**", "**15:**", "**16 (selected):**")
    )
    assert "minimum registered process" in deliveries[13][2]
    assert "no production catch-up" in deliveries[14][4]
    assert "audit only" in deliveries[15][4]


def test_primary_records_and_historical_live_claims_are_separate() -> None:
    document = SPEC.read_text(encoding="utf-8")
    external = _section(
        document, "10. External design review (eleven required fields per reference)"
    )
    records = re.split(r"\n### R\d{2} ", external)[1:]
    assert len(records) == 11
    assert tuple(re.findall(r"^### (R\d{2}) ", external, re.M)) == tuple(
        f"R{i:02}" for i in range(1, 12)
    )
    for record in records:
        record = record.split("### Current primary-source", 1)[0]
        assert tuple(re.findall(r"^(\d+)\. ", record, re.M)) == tuple(
            map(str, range(1, 12))
        )
        assert "WHAT_NOT_TO_COPY" in record
    for text in (
        "PLANNED",
        "没有 Phase65 production PASS",
        "self-review",
        "ProjectDistinct.order_proofs",
        "PRESERVED_WITH_REASON",
        "NOT_ASSESSED",
        "not a caller-rebindable query API",
        "not automatically redacted",
        "not an immutable release certificate",
        "only by successful Slice1 publication",
    ):
        assert text in document
    handoff = (
        REPO_ROOT / "docs/spec/phase64-completion-audit-phase65-handoff-v1.md"
    ).read_text(encoding="utf-8")
    assert "不是approved N=16" in handoff
    assert "不是编号route" in handoff


def test_fixed_git_baseline_and_historical_source_references() -> None:
    # Exact historical names/absence bind this object, never future HEAD.
    object_ref = f"{BASELINE}^{{commit}}"
    present = subprocess.check_output(
        ("git", "cat-file", "--batch-check=%(objectname) %(objecttype)"),
        input=object_ref + "\n",
        cwd=REPO_ROOT,
        text=True,
    ).strip()
    if present == f"{object_ref} missing":
        pytest.skip(f"exact historical Git object {BASELINE} is unavailable")
    assert present == f"{BASELINE} commit"
    identity = subprocess.check_output(
        ("git", "show", "-s", "--format=%T %P", BASELINE), cwd=REPO_ROOT, text=True
    ).strip()
    assert identity == f"{BASELINE_TREE} {BASELINE_PARENT}"
    document = SPEC.read_text(encoding="utf-8")
    references = re.findall(r"`((?:src|tests)/[^`]+\.py)::(\w+)`", document)
    assert references
    paths = sorted({path for path, _ in references})
    archive = subprocess.check_output(
        ("git", "archive", BASELINE, *paths), cwd=REPO_ROOT
    )
    definitions: dict[str, dict[str, ast.FunctionDef | ast.ClassDef]] = {}
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        for path in paths:
            stream = bundle.extractfile(path)
            assert stream is not None
            tree = ast.parse(stream.read().decode("utf-8"), filename=path)
            definitions[path] = {
                node.name: node
                for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.ClassDef))
            }
    for path, name in references:
        node = definitions[path][name]
        if path.startswith("tests/"):
            assert isinstance(node, ast.FunctionDef)
            assert any(isinstance(child, ast.Assert) for child in ast.walk(node))
    historical_files = subprocess.check_output(
        ("git", "ls-tree", "-r", "--name-only", BASELINE, "src/pietto"),
        cwd=REPO_ROOT,
        text=True,
    ).splitlines()
    assert not any("project_sql_plan" in path for path in historical_files)
