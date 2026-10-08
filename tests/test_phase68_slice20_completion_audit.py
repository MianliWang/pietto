"""Offline audit support, not a proof of completion or of any historical execution.

It detects drift between the Phase68 completion audit and the actual private owners,
the S19 checker's independent matrix derivation, the brief's original requirement
rows and the promoted lessons. No database, Arrow, driver, network or private
evidence path is used.
"""

import importlib
from pathlib import Path
import re

import _pietto_phase68_slice19_check as check
from _pietto_repository_facts import REPOSITORY_FACTS

ROOT = Path(__file__).resolve().parents[1]
PHASE = ROOT / "docs/phases/phase-68"
AUDIT = PHASE / "completion-audit.md"
ENTRY = PHASE / "slice-20.md"
HANDOFF = PHASE / "phase69-handoff.md"
BRIEF = PHASE / "brief.md"
LESSONS = ROOT / "docs/references/engineering-lessons.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1, heading
    return document.split(marker, 1)[1].split("\n## ", 1)[0]


def test_links_resolve_and_named_owners_are_private_callables():
    for path in (AUDIT, HANDOFF, ENTRY):
        text = _read(path)
        targets = re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", text)
        assert targets, path.name
        for target in targets:
            resolved = (path.parent / target).resolve()
            assert resolved.is_relative_to(ROOT) and resolved.exists(), target
        assert "/home/" not in text and "~/" not in text, path.name
    # Each owner link names its module (or one of its callables) and is followed
    # by the callables the audit relies on; all must exist in a private module.
    owners = re.findall(
        r"\[(\w+)\]\(\.\./\.\./\.\./src/pietto/_project/(\w+)\.py\)([^\[|]*)",
        _section(_read(AUDIT), "权威与证据索引"),
    )
    assert owners
    for text, name, trailing in owners:
        module = importlib.import_module("pietto._project." + name)
        assert module.__all__ == ()
        named = re.findall(r"`(\w+)`", trailing) + ([text] if text != name else [])
        assert named, name
        for entry in named:
            assert callable(getattr(module, entry)), (name, entry)


def test_matrix_accounting_follows_the_independent_derivation():
    rows = {}
    for line in _section(_read(AUDIT), "全矩阵对账").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if line.startswith("| ") and cells[0] in check.ROUTES:
            rows[cells[0]] = cells[1:]
    assert sorted(rows) == sorted(check.ROUTES)
    for target, row in rows.items():
        routes, declared, excluded, cells, matrix, r2, seen, recovered = row[:8]
        no_basis, drift, r1 = (int(value) for value in row[8:])
        required, exclusions = check.required(target)
        designated = [c for c in required if c[3] == "refined_violation_outside_page"]
        assert routes == ", ".join(check.ROUTES[target])
        assert (int(declared), int(excluded)) == check.TOTALS[target][:2]
        assert int(excluded) == len(exclusions) == len(check.EXCLUSIONS[target])
        assert int(cells) == len(required)
        assert int(matrix) == sum(c[7] == "MATRIX" for c in required) == int(seen)
        assert int(r2) == sum(c[7] == "R2" for c in required)
        # The named guard-refusal case owns exactly the NO_R2_BASIS cells.
        assert {c[7] for c in designated} == {"R2"} and no_basis == len(designated)
        assert int(recovered) == int(r2) - no_basis == r1
        assert drift == len(check.ROUTES[target])


def test_every_original_requirement_has_one_audited_row():
    original = re.findall(r"^\| (P68-A\d\d) ([^|]+?)\s*\|", _read(BRIEF), re.MULTILINE)
    assert [identifier for identifier, _ in original] == [
        f"P68-A{number:02d}" for number in range(1, 23)
    ]
    rows = [
        line
        for line in _section(_read(AUDIT), "A01–A22 三层矩阵").splitlines()
        if line.startswith("| P68-A")
    ]
    assert len(rows) == len(original)
    for (identifier, name), row in zip(original, rows):
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        assert cells[0].startswith(f"{identifier} {name.strip()}："), identifier
        assert len(cells) == 7 and all(cells), identifier
        assert cells[-1] == "SATISFIED_IN_RECORDED_DOMAIN", identifier


def test_candidate_has_one_closure_rule_and_an_external_record():
    entry = _read(ENTRY)
    assert entry.count("\n## 唯一闭环规则\n") == 1
    for path in (AUDIT, HANDOFF):
        assert "slice-20.md#唯一闭环规则" in _read(path)
    for fact in (
        "ACTIVE / CANDIDATE",
        "completion candidate pending S20 closure",
        "当前 S20 不是已完成发布",
        "pietto-phase68-slice20-final-state.json",
        "当前文档不预言它们",
        "status-only follow-up commit",
        "APPROVED / QUEUED / NOT STARTED",
    ):
        assert fact in entry, fact


def test_product_code_imports_neither_changed_dependency():
    changed = {"importlib_resources", "typing_extensions"}
    for path in sorted((ROOT / "src/pietto").rglob("*.py")):
        imported = REPOSITORY_FACTS.python(path).imported_modules
        assert not {name.split(".", 1)[0] for name in imported} & changed, path
    section = _section(_read(AUDIT), "产品与依赖两个证据域")
    for fact in (
        "importlib_resources 6.5.2",
        "typing_extensions 4.15.0",
        "importlib-resources 7.1.0",
        "typing-extensions 4.16.0",
        "`adbc_driver_postgresql._driver_path()`",
        "NOT_OBSERVED",
    ):
        assert fact in section, fact


def test_completion_lessons_link_to_existing_contracts():
    section = _section(_read(LESSONS), "Phase68 完成审计的耐久教训")
    targets = re.findall(r"\]\(([^)]+)\)", section)
    assert len(targets) >= 5
    for target in targets:
        relative, _, anchor = target.partition("#")
        resolved = (LESSONS.parent / relative).resolve()
        assert resolved.is_relative_to(ROOT) and resolved.is_file(), target
        assert not anchor or f"\n## {anchor}\n" in _read(resolved), target
