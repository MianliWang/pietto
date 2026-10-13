from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "docs/spec/phase58-project-explain-portability-scope-lock-v1.md"

EXPECTED_ROUTE = (
    (
        "1",
        "Architecture/scope/route lock; artifact identity; target denominator; single-file explain compatibility",
    ),
    (
        "2",
        "Public common model and success/failure envelope; logical paths; evidence posture; request/resolution/result vocabulary",
    ),
    (
        "3",
        "Package and requirement provenance projection; `declared_by`/`requested_by`",
    ),
    (
        "4",
        "Public requirement/target compatibility matrix; evaluation states; five checked statuses and reasons",
    ),
    (
        "5",
        "Public extension-catalog evidence projection; catalog coordinate/target/digest; selection; matchability/exposure; bounded provenance",
    ),
    ("6", "Conservative requirement/project portability derivation"),
    (
        "7",
        "Cross-section composition; artifact-local references; integrity; deterministic ordering; authority separation",
    ),
    (
        "8",
        "Public JSON v1 schema; deterministic serialization; success/failure envelopes; privacy and schema-evolution locks",
    ),
    (
        "9",
        "`pietto explain --project` text/JSON integration; existing single-file explain zero-delta",
    ),
    (
        "10",
        "Real multi-target E2E scenarios spanning package, capability, catalog, all evaluation states, and all checked result classes",
    ),
    (
        "11",
        "Public pure/differential compatibility boundary; goldens; Python 3.12/3.13; hash seed; relocation; installed wheel",
    ),
    (
        "12",
        "Completion audit; Phase 59 handoff; Phase 60/64/69 readiness reconciliation",
    ),
)
HISTORICAL_ROUTE_16 = (
    *EXPECTED_ROUTE[:8],
    ("9", "Runtime authority architecture and evidence-backed route expansion lock"),
    ("10", "Package-owned capability requirement declaration authority"),
    (
        "11",
        "Project-owned evaluated-target, profile, and catalog-availability authority",
    ),
    ("12", "Project Explain runtime authority builder and exact orchestration"),
    (
        "13",
        "`pietto explain --project` text/JSON integration; existing single-file explain zero-delta",
    ),
    (
        "14",
        "Real multi-target E2E scenarios spanning package, capability, catalog, all evaluation states, and all checked result classes",
    ),
    (
        "15",
        "Public pure/differential compatibility boundary; goldens; Python 3.12/3.13; hash seed; relocation; installed wheel",
    ),
    (
        "16",
        "Completion audit; Phase 59 handoff; Phase 60/64/67/69 readiness reconciliation",
    ),
)
CURRENT_ROUTE_17 = (
    *HISTORICAL_ROUTE_16[:11],
    ("12", "Package-owned extension-signature typed physical selector authority"),
    ("13", "Project Explain runtime authority builder and zero-context adaptation"),
    (
        "14",
        "`pietto explain --project` text/JSON integration; existing single-file explain zero-delta",
    ),
    (
        "15",
        "Real multi-target E2E scenarios spanning package, capability, catalog, all evaluation states, and all checked result classes",
    ),
    (
        "16",
        "Public pure/differential compatibility boundary; goldens; Python 3.12/3.13; hash seed; relocation; installed wheel",
    ),
    (
        "17",
        "Completion audit; Phase 59 handoff; Phase 60/64/67/69 readiness reconciliation",
    ),
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


def _table_rows(section: str) -> tuple[tuple[str, ...], ...]:
    return tuple(
        tuple(cell.strip() for cell in line.strip("|").split("|"))
        for line in section.splitlines()
        if line.startswith("| ") and not line.startswith("| ---")
    )


def _headings(document: str) -> tuple[str, ...]:
    return tuple(
        line.removeprefix("## ")
        for line in document.splitlines()
        if line.startswith("## ")
    )


def _function_names(path: Path) -> frozenset[str]:
    tree = ast.parse(_read(path), filename=path.as_posix())
    return frozenset(
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    )


def _argument_names(source: str, function_name: str) -> tuple[str, ...]:
    tree = ast.parse(source)
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == function_name
    )
    names: list[str] = []
    for node in ast.walk(function):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            names.append(node.args[0].value)
    return tuple(names)
