"""Finite Phase66 design traceability, not SQL or database conformance proof."""

from __future__ import annotations

import ast
from functools import cache
from pathlib import Path
import re

from _pietto_repository_facts import REPOSITORY_FACTS


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / (
    "docs/spec/phase66-dialect-sql-emission-product-phase-initiation-"
    "gate-route-lock-v1.md"
)
CLASSIFICATIONS = {
    "CORE_NOW",
    "MINIMUM_NOW",
    "CONTRACT_ONLY_NOW",
    "DEFER_BY_NECESSITY",
    "NO_CURRENT_USE",
}
# Actual future-roadmap atoms, independently fixed for this initiation review.
LATER_ATOMS = (
    ("Arrow interchange foundation", "Pietto result contract"),
    (
        "executor SPI",
        "ADBC",
        "DBAPI",
        "connection/session/transaction",
        "streaming",
        "cancellation",
        "backpressure",
        "runtime enforcement",
    ),
    (
        "public alpha release engineering",
        "unified safe entrypoints",
        "partial-error policy",
    ),
    (
        "open/composite plans",
        "authored nonrecursive CTE",
        "authored subqueries",
        "VALUES",
        "table functions",
        "outer captures",
        "authored EXISTS",
        "IN",
        "LATERAL",
        "bounded decorrelation",
        "effect authority",
        "caller rebind",
    ),
    (
        "NestedRelation",
        "Collect",
        "Unnest",
        "flatten",
        "outer/inner grain",
        "nested Arrow",
    ),
    (
        "advanced equality",
        "advanced types",
        "nullability",
        "temporal relationships",
        "range relationships",
        "ASOF",
        "Float row equivalence",
    ),
    (
        "aggregate algebra",
        "aggregate state",
        "grouping extensions",
        "fanout-safe reaggregation",
    ),
    (
        "reusable local semantic assets",
        "derived relationships",
        "function SPI",
        "plugin SPI",
    ),
    (
        "formatter",
        "LSP",
        "editor",
        "diagnostics tooling",
        "syntax editions",
        "migrations",
    ),
    ("PostgreSQL deep adaptation",),
    ("MySQL deep adaptation",),
    ("SQLite deep adaptation",),
    ("DuckDB deep adaptation",),
    ("pandas", "Polars", "NumPy", "SciPy", "Matplotlib"),
    (
        "high-intensity real-DB",
        "differential",
        "metamorphic",
        "fuzz",
        "performance assurance",
    ),
    ("public schemas", "API", "CLI", "syntax", "support-matrix freeze"),
    ("stable1.0 audit", "publication"),
    ("remote assets", "registry", "transport", "signing", "trust"),
    ("dependency solver", "canonical lockfile", "reproducible resolution"),
    ("RDKit", "geospatial", "sparse", "DLPack", "device-framework adapters"),
    ("catalog", "constraints", "statistics", "runtime data quality", "chase"),
    ("logical optimizer memo", "join-order search", "hypergraph search"),
    (
        "Yannakakis",
        "WCOJ",
        "Free Join",
        "predicate transfer",
        "materialization strategy",
    ),
    ("Rust kernels", "PyO3", "maturin", "parity", "wheel matrix"),
    (
        "persistent incremental-cache identity",
        "incremental Project IR",
        "differential Project IR",
    ),
    (
        "recursive relations",
        "fixpoints",
        "iterative planning",
        "bounded recursive provenance",
    ),
    ("formal rewrite certification",),
    ("cloud semantics", "federation semantics", "federation planning", "transport"),
    ("DML", "DDL", "migrations"),
    ("governance", "security policy semantics"),
    ("continuous query semantics", "streaming query semantics"),
)


def _section(document: str, heading: str, level: int = 2) -> str:
    marker = f"{'#' * level} {heading}\n"
    assert document.count(marker) == 1
    return re.split(
        r"\n#{1," + str(level) + r"} ", document.split(marker, 1)[1], maxsplit=1
    )[0]


def _rows(document: str, pattern: str) -> tuple[tuple[str, ...], ...]:
    return tuple(
        tuple(cell.strip() for cell in line.strip("|").split("|"))
        for line in document.splitlines()
        if re.match(pattern, line)
    )


@cache
def _definitions(relative: str) -> dict[str, ast.FunctionDef | ast.ClassDef]:
    tree = ast.parse(REPOSITORY_FACTS.python(ROOT / relative).text, filename=relative)
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


def test_fresh_gate_has_thirty_answers_and_all_cross_cutting_groups() -> None:
    document = SPEC.read_text(encoding="utf-8")
    gate = _section(document, "Thirty mandatory answers")
    answers = _rows(gate, r"^\| \d+ \|")
    assert tuple(row[0] for row in answers) == tuple(map(str, range(1, 31)))
    assert all(len(row) == 3 and all(row) for row in answers)
    assert all(row[2] not in {"UNKNOWN", "NOT_APPLICABLE"} for row in answers)
    assert tuple(row[0].split()[0] for row in _rows(gate, r"^\| [A-L] ")) == tuple(
        "ABCDEFGHIJKL"
    )
    assert tuple(row[0].split()[0] for row in _rows(gate, r"^\| X\d ")) == tuple(
        f"X{n}" for n in range(1, 9)
    )
    assert tuple(re.findall(r"^### (D66\.\d{2}) —", document, re.M)) == tuple(
        f"D66.{n:02}" for n in range(1, 17)
    )
    assert "71c1fa13c152d7be317c4bffee48615a39f1c2e4" in document
    assert "57f26514eb3db18213d369851a6b7975916cea92" in document
    assert "128388bc258d6ee861c0128c42324fca712c0dcc" in document


def test_exclusive_assets_and_every_later_atom_have_an_owner_and_reason() -> None:
    document = SPEC.read_text(encoding="utf-8")
    inherited = _rows(_section(document, "INHERITED_CLOSED", 3), r"^\| I\d{2} \|")
    transferred = _rows(
        _section(document, "TRANSFERRED_TO_PHASE66", 3), r"^\| T\d{2} \|"
    )
    later = _rows(
        _section(document, "RETAINED_LATER: every Phase67–97 atom", 3), r"^\| L\d{2} \|"
    )
    assert tuple(r[0] for r in inherited) == tuple(f"I{n:02}" for n in range(1, 13))
    assert tuple(r[0] for r in transferred) == tuple(f"T{n:02}" for n in range(1, 13))
    assert tuple(r[0] for r in later) == tuple(f"L{n}" for n in range(67, 98))
    rows = (*inherited, *transferred, *later)
    assert len({row[0] for row in rows}) == len(rows)
    assert all(len(row) == 3 and all(row) for row in rows)
    assert all(row[1] == "CORE_NOW" for row in transferred)
    for phase, row, expected in zip(range(67, 98), later, LATER_ATOMS, strict=True):
        assert row[1].startswith(f"Phase{phase} ")
        atoms = tuple(part.strip() for part in row[2].split("；"))
        assert tuple(part.split(": ", 1)[0] for part in atoms) == expected
        for atom in atoms:
            disposition, reason = atom.split(": ", 1)[1].split("，", 1)
            assert disposition in CLASSIFICATIONS and reason
        if phase >= 91:
            assert "TENTATIVE / OWNER ONLY" in row[1]


def test_handoff_questions_are_answered_without_reopening_phase65() -> None:
    document = SPEC.read_text(encoding="utf-8")
    handoff = _section(document, "Handoff reconciliation")
    for prefix in ("H", "Q"):
        rows = _rows(handoff, rf"^\| {prefix}\d{{2}} \|")
        assert tuple(r[0] for r in rows) == tuple(
            f"{prefix}{n:02}" for n in range(1, 9)
        )
        assert all(len(row) == 3 and all(row) for row in rows)
    assert "F65S15-01" in document and "F65S15-02" in document
    assert "ProjectIRProvidedRelationOrdering" in document
    assert "ProjectRelationOrdering" in document
    assert "ordinary/rebound" in document and "completed" in document


def test_rules_have_positive_negative_environment_and_delivery_boundaries() -> None:
    document = SPEC.read_text(encoding="utf-8")
    section = _section(document, "Finite rule and support ledger")
    rules = _rows(section, r"^\| R\d{2} \|")
    assert tuple(row[0] for row in rules) == tuple(f"R{n:02}" for n in range(1, 27))
    assert all(len(row) == 8 and all(row) for row in rules)
    for row in rules:
        assert "PLANNED" in row[3] or "APPROVED_NON_SUPPORT" in row[3]
        assert re.search(r"(?<!\d)(?:0?[2-9]|1[0-5])(?!\d)", row[7])
    for state in (
        "MISSING_OBSERVATION",
        "PROMISED_DOMAIN_DEFECT",
        "APPROVED_NON_SUPPORT",
    ):
        assert state in section
    assert "builtin equality" in document and "MySQL FULL" in document
    assert "hidden STRICT-FD" in document and "whole-target-positive" in document


def test_counterexamples_route_and_exits_are_finite_and_connected() -> None:
    document = SPEC.read_text(encoding="utf-8")
    cases = _rows(_section(document, "Counterexample obligations"), r"^\| C\d{2} \|")
    assert tuple(row[0] for row in cases) == tuple(f"C{n:02}" for n in range(1, 33))
    rule_ids = {f"R{n:02}" for n in range(1, 27)}
    for row in cases:
        assert len(row) == 4 and all(row)
        refs = re.findall(r"R\d{2}", row[2])
        assert refs and set(refs) <= rule_ids
    route = _section(document, "Sixteen-Slice delivery route")
    deliveries = _rows(route, r"^\| \d{2} \|")
    assert tuple(row[0] for row in deliveries) == tuple(f"{n:02}" for n in range(1, 17))
    assert all(len(row) == 5 and all(row) for row in deliveries)
    assert "legacy-generated + independently specified SQL" in deliveries[1][2]
    assert "installed minimal emission" in deliveries[2][2]
    assert "audit only" in deliveries[15][2]
    for alternative in ("**12:**", "**14:**", "**16 (selected):**"):
        assert alternative in route
    exits = _rows(_section(document, "E01–E10 phase exits"), r"^\| E\d{2} \|")
    assert tuple(row[0] for row in exits) == tuple(f"E{n:02}" for n in range(1, 11))
    assert all(len(row) == 3 and all(row) for row in exits)
    assert "Phase66 exits are NOT SATISFIED by Slice1" in document


def test_current_source_citations_resolve_through_shared_fact_acquisition() -> None:
    document = SPEC.read_text(encoding="utf-8")
    findings = _rows(
        _section(document, "Source findings and consumer consequences"),
        r"^\| F\d{2} \|",
    )
    assert tuple(row[0] for row in findings) == tuple(f"F{n:02}" for n in range(1, 15))
    assert all(len(row) == 6 and "::test_" in row[3] and all(row) for row in findings)
    citations = re.findall(r"`((?:src|tests|scripts)/[^`]+\.py)::([\w.]+)`", document)
    assert citations
    for relative, name in citations:
        node = _definitions(relative)[name]
        if name.startswith("test_"):
            assert relative.startswith("tests/") and isinstance(node, ast.FunctionDef)
        # Helpers may own assertions; AST existence is not behavioral proof.
    references = _section(document, "Controlling repository references")
    for path in re.findall(r"\]\(([^)]+)\)", references):
        assert not path.startswith("http") and (SPEC.parent / path).is_file()


def test_explicit_input_atomic_artifact_and_legacy_boundaries_are_recorded() -> None:
    document = SPEC.read_text(encoding="utf-8")
    interface = _section(document, "Concrete request, output and state contract")
    branches = _rows(
        _section(document, "Public envelope schema", 3),
        r"^\| (?:VERIFIED|INPUT_REJECTED|BLOCKED) \|",
    )
    assert tuple(row[0] for row in branches) == (
        "VERIFIED",
        "INPUT_REJECTED",
        "BLOCKED",
    )
    success_keys = (
        "format,status,target,request,sql,fixed_values,parameter_uses,columns,"
        "ranges,requirements,diagnostics"
    )
    failure_keys = "format,status,artifact,blockers,diagnostics,cli_errors"
    assert tuple(row[1] for row in branches) == (
        success_keys,
        failure_keys,
        failure_keys,
    )
    assert all(len(row) == 3 and row[2] for row in branches)
    assert "初始allowlist恰为(postgres,18.6)、(mysql,8.4.12)" in interface
    assert "BLOCKED / PIE-B1003 / exit1，cli_errors为空" in interface
    assert "INPUT_REJECTED / emission_contract_schema / exit2" in interface
    assert "Slice3首次公共artifact序列化即有独立data-only decoder/consumer" in interface
    for phrase in (
        "--project PATH --module LOGICAL_MODULE --kind {table,query}",
        "--emission-contract FILE",
        "pietto.emission-contract.v1",
        "pietto.sql-emission.v1",
        "pietto.sql-emission-observation.v1",
        "{ordinal, name, column, representation}",
        "INPUT_REJECTED",
        "BLOCKED",
        "VERIFIED",
        "artifact:null",
        "fixed_values,parameter_uses,columns,ranges,requirements,diagnostics",
        "zero-based half-open UTF-8",
        "Semantic Metadata Artifact v1",
        "project-cli-json-v2.md",
        "PIE-B1008 ARTIFACT_INTEGRITY",
    ):
        assert phrase in interface
    for phrase in (
        "two complete denominators",
        "without usable partial SQL success",
        "nullable Bool scalar results",
        "Quoting alone does not prevent name capture",
        "Do not count tokens by searching SQL strings",
        "unknown effects",
    ):
        assert phrase.casefold() in document.casefold()


def test_infrastructure_has_explicit_owners_and_no_empty_success() -> None:
    document = SPEC.read_text(encoding="utf-8")
    prerequisites = _section(document, "Future infrastructure prerequisites")
    rows = _rows(prerequisites, r"^\| P\d{2} ")
    assert tuple(row[0].split()[0] for row in rows) == tuple(
        f"P{n:02}" for n in range(1, 11)
    )
    assert all(len(row) == 3 and all(row) and "Slice2" in row[1] for row in rows)
    for phrase in (
        "NOT_ACQUIRED→ACQUIRED→READY→RUNNING",
        "RECOVERY_FAILED",
        "CLEANUP_FAILED",
        "UNRESOLVED_ATTRIBUTION",
        "missing/skipped/cancelled/empty",
        "candidate→installed wheel→artifact→submitted SQL/params",
        "pyproject.toml",
        "uv.lock",
        ".github/workflows/ci.yml",
    ):
        assert phrase in prerequisites


def test_external_records_have_exact_eleven_fields_and_observation_limits() -> None:
    document = SPEC.read_text(encoding="utf-8")
    external = _section(document, "Primary-source review records")
    assert tuple(re.findall(r"^### (XREF\d{2}) ", external, re.M)) == tuple(
        f"XREF{n:02}" for n in range(1, 9)
    )
    for record in re.split(r"\n### XREF\d{2} ", external)[1:]:
        assert tuple(re.findall(r"^(\d+)\. ", record, re.M)) == tuple(
            map(str, range(1, 12))
        )
        assert "WHAT_NOT_TO_COPY" in record and "2026-09-15" in record
        assert re.search(r"\]\(https://", record)
    for phrase in (
        "Server Docker image security update",
        "3.3.6.dev1",
        "stable adapter pins",
        "Author/Ponytail/internal read-only review is not third-party review",
        "Documentation/source research is not target execution or implementation proof",
    ):
        assert phrase in document


def test_current_native_adapter_amendment_preserves_historical_cursor_scope() -> None:
    document = SPEC.read_text(encoding="utf-8")
    for phrase in (
        "cmd_stmt_prepare/cmd_stmt_execute/get_rows/cmd_stmt_close",
        "former prepared-cursor API remains the historical Slice2–4 choice",
        "D66.10, R04/R25 and prerequisite P02/P09",
        "actual prepare/command-send byte identity",
        "历史v1不认证新路由",
        "选择?不证明cursor避免rewrite",
    ):
        assert phrase in document
