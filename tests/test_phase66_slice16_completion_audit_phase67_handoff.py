"""Bounded static traceability, not runtime or native correctness evidence.

The audit reads behavior assertions; existing suites and bound receipts execute
those obligations. These checks need neither Git history nor user-local evidence.
"""

from __future__ import annotations

import ast
from functools import cache
from pathlib import Path
import re

from _pietto_repository_facts import REPOSITORY_FACTS


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/spec/phase66-completion-audit-phase67-handoff-v1.md"
ROUTE = (
    ROOT
    / "docs/spec/phase66-dialect-sql-emission-product-phase-initiation-gate-route-lock-v1.md"
)


def _rows(document: str, prefix: str) -> list[list[str]]:
    return [
        [cell.strip() for cell in line.strip("|").split("|")]
        for line in document.splitlines()
        if re.match(r"^\| " + prefix + r" \|", line)
    ]


@cache
def _definitions(relative: str) -> set[str]:
    tree = ast.parse(REPOSITORY_FACTS.python(ROOT / relative).text)
    result = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            result.add(node.name)
            if isinstance(node, ast.ClassDef):
                result.update(
                    f"{node.name}.{member.name}"
                    for member in node.body
                    if isinstance(member, ast.FunctionDef)
                )
    return result


def test_canonical_ledgers_are_complete_unique_and_disposed() -> None:
    document = SPEC.read_text(encoding="utf-8")
    for prefix, first, last in (
        ("D66.", 1, 16),
        ("I", 1, 12),
        ("T", 1, 12),
        ("R", 1, 26),
        ("C", 1, 32),
        ("E", 1, 10),
        ("L", 67, 97),
    ):
        rows = _rows(document, re.escape(prefix) + r"\d{2}")
        assert [row[0] for row in rows] == [
            f"{prefix}{number:02}" for number in range(first, last + 1)
        ]
        assert all(all(row) for row in rows)
        if prefix != "L":
            assert all("CLOSED" in row[-1] for row in rows)
    assert re.findall(r"^### (Q\d{2}) —", document, re.M) == [
        f"Q{number:02}" for number in range(1, 14)
    ]
    assert set(re.findall(r"\bQ\d{2}\b", document)) <= {
        f"Q{number:02}" for number in range(1, 14)
    }
    assert [row[0] for row in _rows(document, r"A\d{2}[^|]*")] == [
        "A01 Slice4",
        "A02 Slice5",
        "A03 Slice7",
        "A04 Slice8/9",
        "A05 Slice12/13/14",
        "A06 Slice15",
        "A07 corrective",
        "A08 residual",
        "A09 post-guard audit dispatch",
        "A10 G8 publication",
        "A11 post-G8 audit dispatch",
    ]


def test_original_exits_and_minimum_rule_witnesses_are_not_redefined() -> None:
    document = SPEC.read_text(encoding="utf-8")
    original = ROUTE.read_text(encoding="utf-8")
    assert [row[:3] for row in _rows(document, r"E\d{2}")] == _rows(original, r"E\d{2}")
    assert [row[:3] for row in _rows(document, r"R\d{2}")] == [
        [row[0], row[5], row[6]] for row in _rows(original, r"R\d{2}")
    ]
    assert [row[:3] for row in _rows(document, r"C\d{2}")] == [
        row[:3] for row in _rows(original, r"C\d{2}")
    ]
    for prefix in ("I", "T"):
        assert [row[:3] for row in _rows(document, prefix + r"\d{2}")] == _rows(
            original, prefix + r"\d{2}"
        )
    decisions = _rows(document, r"D66\.\d{2}")
    assert [row[0] for row in decisions if row[2] == "ARCHITECTURE_DECISION"] == [
        "D66.06",
        "D66.11",
        "D66.12",
        "D66.14",
    ]


def test_each_later_atom_keeps_its_classification_and_exact_owner() -> None:
    original = _rows(ROUTE.read_text(encoding="utf-8"), r"L\d{2}")
    current = _rows(SPEC.read_text(encoding="utf-8"), r"L\d{2}")
    atom = re.compile(
        r"(?:^|[；;])\s*([^:]+):\s*"
        r"(MINIMUM_NOW|CONTRACT_ONLY_NOW|DEFER_BY_NECESSITY|NO_CURRENT_USE)"
    )
    for before, after in zip(original, current, strict=True):
        assert before[:2] == after[:2]
        expected = atom.findall(before[2])
        assert expected and atom.findall(after[2]) == expected
        if int(after[0][1:]) >= 91:
            assert "TENTATIVE / OWNER ONLY" in after[1]


def test_cited_nodes_and_local_document_references_exist() -> None:
    document = SPEC.read_text(encoding="utf-8")
    citations = re.findall(r"`((?:src|tests)/[^`]+\.py)::([\w.]+)`", document)
    assert citations
    for relative, name in citations:
        assert name in _definitions(relative), (relative, name)
    # Node existence does not prove assertions ran, or that their logic is adequate.
    for target in re.findall(r"\]\(([^)]+)\)", document):
        if not target.startswith(("https://", "#")):
            assert (SPEC.parent / target.split("#", 1)[0]).is_file(), target


def test_acceptance_is_conditional_and_evidence_domains_remain_separate() -> None:
    document = SPEC.read_text(encoding="utf-8")
    for marker in (
        "Conditional completion",
        "ACTIVE / AUDIT CANDIDATE",
        "Python 3.12",
        "Python 3.13",
        "Target postgres",
        "Target mysql",
        "Target conformance aggregate",
        "strict per-target",
        "aggregate verification",
        "original authority / amendments",
        "current code / assertions read",
        "inherited native execution",
        "downloaded raw verification",
        "compiler / process execution",
        "static traceability",
        "R15-INT-OFFSET-V1",
        "mysql_bool_window_result_representation_not_supported_in_phase66",
        "R-A",
        "R-B",
        "R-C",
        "G8 exact same-submission native evidence",
        "F9",
        "coordinated all-left/empty",
        "source-only",
        "MISSING_EVIDENCE",
    ):
        assert marker in document
    assert "## Phase66 retrospective and engineering lessons" in document
    lessons = _rows(document, r"J\d{2}[^|]*")
    assert 3 <= len(lessons) <= 7 and all(len(row) == 5 and all(row) for row in lessons)
    for marker in (
        "Macro-planning decisions ACCEPTED",
        "Phase67 NEXT / NOT STARTED",
        "pre-activation candidate",
        "不创建或激活 N67",
        "Phase68",
        "Phase69",
        "Phase83",
        "Phase90",
        "NOT AUTHORIZED / NOT STARTED",
    ):
        assert marker in document
