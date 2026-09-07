"""Phase 64 Slice 1 product gate, source audit, architecture and route-lock principal."""

from __future__ import annotations

from pathlib import Path
import ast
import re
import subprocess

import pytest

from _pietto_repository_facts import REPOSITORY_FACTS
from pietto._project.module_attribution import ProjectModuleRowFieldKind
from pietto._project.project_bag_null_oracle import (
    ProjectBagNullEntry,
    ProjectBagNullEqualityCorrespondence,
    ProjectBagNullJoinKind,
    ProjectBagNullJoinSpecification,
    ProjectBagNullRow,
    ProjectFiniteBag,
    evaluate_project_bag_null_join,
    project_bag_int,
)
from pietto._project.project_grain import ProjectGrainOriginKind
from pietto._project.project_ir_joins import ProjectIRBinaryJoinKind
from pietto._project.project_relationship_conditions import (
    ProjectRelationshipConditionScope,
)
from pietto.ast_nodes import AuthoredJoinKind
from pietto.errors import Severity


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase64-flat-relational-algebra-product-phase-initiation-gate-v3-source-audit-architecture-route-lock-v1.md"
)

BASELINE = "bb52135038973b40638ff86367ba478846f898c6"
BASELINE_TREE = "8244d6ecf9c98af0895992a39cac93dd9352481d"
BASELINE_PARENT = "461e5ef59b689b61a1815f039b93331bed3ac576"

CLASSIFICATIONS = frozenset(
    {
        "IMPLEMENT_NOW",
        "PRIVATE_READINESS_NOW",
        "CONTRACT_ONLY_NOW",
        "DEFER_BY_NECESSITY",
        "OUT_OF_SCOPE",
    }
)
QUESTION_GROUPS = tuple("ABCDEFGHIJKL")
DECISIONS = tuple(f"D0{index}" for index in range(1, 9))
LAWS = tuple(f"L{index:02d}" for index in range(1, 11))
CASES = tuple(f"C{index:02d}" for index in range(1, 11))
FINDINGS = tuple(f"F{index:02d}" for index in range(1, 14))
EXITS = tuple(f"E{index:02d}" for index in range(1, 13))

# Historical facts: exact member sets frozen at the immutable baseline only.
BASELINE_ENUM_SETS = (
    ("src/pietto/ast_nodes.py", "AuthoredJoinKind", ("INNER", "LEFT")),
    (
        "src/pietto/_project/project_ir_joins.py",
        "ProjectIRBinaryJoinKind",
        ("INNER", "LEFT"),
    ),
    (
        "src/pietto/_project/project_grain.py",
        "ProjectGrainOriginKind",
        ("SOURCE_ROW_DOMAIN", "GROUPED_RESULT", "GLOBAL_AGGREGATE"),
    ),
)
# Historical facts: member presence frozen at the immutable baseline only.
BASELINE_ENUM_MEMBERS = (
    (
        "src/pietto/_project/project_completion.py",
        "ProjectEffectiveOutputTerminalReason",
        "EFFECTIVE_UPSTREAM_JOIN_UNSUPPORTED",
    ),
    (
        "src/pietto/_project/project_query_block_ir.py",
        "ProjectIRQueryBlockTerminalReason",
        "EFFECTIVE_JOIN_INPUT_REBIND_UNSUPPORTED",
    ),
)
# Durable laws: existing members must survive every future legal extension.
DURABLE_RETENTIONS = (
    ("AuthoredJoinKind", frozenset({"INNER", "LEFT"})),
    ("ProjectIRBinaryJoinKind", frozenset({"INNER", "LEFT"})),
    (
        "ProjectRelationshipConditionScope",
        frozenset(
            {
                "RELATIONSHIP_BASE_MATCH",
                "JOIN_LOCAL_ON_REFINEMENT",
                "POST_JOIN_FILTER",
            }
        ),
    ),
    ("ProjectModuleRowFieldKind", frozenset({"RELATION_OUTPUT"})),
    (
        "ProjectGrainOriginKind",
        frozenset({"SOURCE_ROW_DOMAIN", "GROUPED_RESULT", "GLOBAL_AGGREGATE"}),
    ),
    ("Severity", frozenset({"ERROR", "WARNING"})),
    ("ProjectBagNullJoinKind", frozenset({"INNER", "LEFT"})),
)
LIVE_ENUMS = {
    "AuthoredJoinKind": AuthoredJoinKind,
    "ProjectIRBinaryJoinKind": ProjectIRBinaryJoinKind,
    "ProjectRelationshipConditionScope": ProjectRelationshipConditionScope,
    "ProjectModuleRowFieldKind": ProjectModuleRowFieldKind,
    "ProjectGrainOriginKind": ProjectGrainOriginKind,
    "Severity": Severity,
    "ProjectBagNullJoinKind": ProjectBagNullJoinKind,
}


def _document() -> str:
    return SPEC.read_text(encoding="utf-8")


def _normalized() -> str:
    return " ".join(_document().split())


def _section(heading: str) -> str:
    document = _document()
    marker = f"## {heading}\n"
    assert document.count(marker) == 1, heading
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


def _rows(section: str) -> tuple[tuple[str, ...], ...]:
    parsed: list[tuple[str, ...]] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = tuple(
            cell.strip().replace("\\|", "|")
            for cell in re.split(r"(?<!\\)\|", stripped[1:-1])
        )
        if all(set(cell) <= set("-: ") for cell in cells):
            continue
        parsed.append(cells)
    return tuple(parsed)


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    assert completed.stderr == ""
    return completed.stdout.strip()


def _has_object(revision: str) -> bool:
    completed = subprocess.run(
        ("git", "cat-file", "-e", f"{revision}^{{commit}}"),
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
    )
    return completed.returncode == 0


def _baseline_source(path: str) -> str:
    """Read one explicit file from the immutable baseline without executing it."""

    return _git("show", f"{BASELINE}:{path}")


def _baseline_enum_members(path: str, name: str) -> tuple[str, ...]:
    """Statically parse one baseline enum's declared member names."""

    module = ast.parse(_baseline_source(path))
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return tuple(
                target.id
                for statement in node.body
                if isinstance(statement, ast.Assign)
                for target in statement.targets
                if isinstance(target, ast.Name)
            )
    raise AssertionError(f"{name} is absent from {path} at the baseline")


def test_gate_v3_answers_every_numbered_field_without_unknown() -> None:
    rows = _rows(_section("Product/Phase Initiation Gate v3 Coverage"))
    header, *body = rows
    assert header[0] == "#"
    numbered = tuple(row for row in body if row[0].isdigit())
    assert tuple(int(row[0]) for row in numbered) == tuple(range(1, 31))
    for row in numbered:
        assert len(row) == 4, row[0]
        answer, evidence = row[2], row[3]
        assert answer and evidence, row[0]
        assert "UNKNOWN" not in answer, row[0]
        assert "OPEN" not in answer, row[0]
        if "NOT_APPLICABLE" in answer:
            assert "reason=" in answer and "owner=" in answer, row[0]

    normalized = " ".join(_section("Product/Phase Initiation Gate v3 Coverage").split())
    assert "没有 `UNKNOWN`" in normalized
    assert "四处 `NOT_APPLICABLE`（#13、#18、#19、#27）" in normalized


def test_reusable_question_groups_and_cross_cutting_additions_are_covered() -> None:
    section = _section("Reusable Question-Set Coverage")
    covered = tuple(row[0].split()[0] for row in _rows(section)[1:])
    assert covered == QUESTION_GROUPS
    normalized = " ".join(section.split())
    for addition in (
        "observable equivalence/algebra",
        "minimal counterexample",
        "unknown 与 obligation 的分离",
        "error/evaluation effect",
        "safety/liveness 与 atomic",
        "evolution/reversibility",
        "evidence strength 与 independent validation",
        "total workflow/resource cost",
    ):
        assert addition in normalized, addition


def test_source_audit_findings_are_structurally_complete() -> None:
    rows = _rows(_section("Live Pietto Source Audit"))[1:]
    assert tuple(row[0] for row in rows) == FINDINGS
    for row in rows:
        assert len(row) == 4 and all(row), row[0]
    normalized = " ".join(_section("Live Pietto Source Audit").split())
    # F12 is a baseline fact about relationship comparison, not the future domain.
    assert "**历史基线事实**" in normalized
    assert "**不是** Phase-64 row-equivalence 规范" in normalized


def test_frozen_fact_classification_table_is_exhaustive_and_disjoint() -> None:
    """Every frozen fact is declared HISTORICAL or DURABLE, and nothing else."""

    rows = _rows(_section("Reader And Inventory Ownership"))[1:]
    assert rows
    classes = tuple(row[1].strip("`") for row in rows)
    assert set(classes) == {"HISTORICAL", "DURABLE"}
    historical = tuple(row for row in rows if row[1].strip("`") == "HISTORICAL")
    durable = tuple(row for row in rows if row[1].strip("`") == "DURABLE")
    # Historical rows are checked against the baseline; durable rows against live source.
    assert all("baseline" in row[2] for row in historical), historical
    assert all(row[2].startswith("live") for row in durable), durable

    declared_historical = len(BASELINE_ENUM_SETS) + len(BASELINE_ENUM_MEMBERS)
    # Plus the deferred-equality literal and the authored grammar text.
    assert len(historical) == declared_historical + 2
    assert len(durable) == len(DURABLE_RETENTIONS)

    normalized = " ".join(_section("Reader And Inventory Ownership").split())
    assert "principal 不得对 live 枚举做精确集合比对" in normalized


def test_historical_absence_facts_read_immutable_baseline_source() -> None:
    """Exact member sets are frozen at the baseline, never pinned on live enums."""

    if not _has_object(BASELINE):
        pytest.skip(f"baseline object {BASELINE} is unavailable in a shallow checkout")
    for path, name, expected in BASELINE_ENUM_SETS:
        assert _baseline_enum_members(path, name) == expected, (path, name)
    for path, name, member in BASELINE_ENUM_MEMBERS:
        assert member in _baseline_enum_members(path, name), (path, name, member)
    conditions = _baseline_source(
        "src/pietto/_project/project_relationship_conditions.py"
    )
    assert (
        '_DEFERRED_EQUALITY_BUILTINS = frozenset({"Any", "Bytes", "Decimal", "Json"})'
        in conditions
    )


def test_durable_live_laws_are_retention_only() -> None:
    """Live checks assert retention, so a legal Phase-64 extension cannot break them."""

    for name, retained in DURABLE_RETENTIONS:
        live = {member.name for member in LIVE_ENUMS[name]}
        assert retained <= live, name

    # F05/F06: the seams Phase 64 builds on are present in live source.
    assert ProjectRelationshipConditionScope.JOIN_LOCAL_ON_REFINEMENT in tuple(
        ProjectRelationshipConditionScope
    )
    assert ProjectModuleRowFieldKind.RELATION_OUTPUT in tuple(ProjectModuleRowFieldKind)
    # D05: the existing severity channel carries WARNING without a new mechanism.
    assert Severity.WARNING in tuple(Severity)
    # F13: the bounded oracle stays available to later slices, which may extend it.
    assert {ProjectBagNullJoinKind.INNER, ProjectBagNullJoinKind.LEFT} <= set(
        ProjectBagNullJoinKind
    )


def test_pull_forward_classifications_are_exclusive_and_cover_every_later_owner() -> (
    None
):
    rows = _rows(_section("Whole-Roadmap Pull-Forward Audit"))[1:]
    assert rows
    covered: set[int] = set()
    for row in rows:
        assert len(row) == 4, row
        owner, item, classification, reason = row
        assert item and reason, owner
        assert classification.strip("`") in CLASSIFICATIONS, classification
        for part in owner.replace("–", "-").split("-"):
            digits = "".join(character for character in part if character.isdigit())
            if digits:
                covered.add(int(digits))
        if "-" in owner.replace("–", "-"):
            low, high = (
                int("".join(c for c in part if c.isdigit()))
                for part in owner.replace("–", "-").split("-")
            )
            covered.update(range(low, high + 1))
    assert set(range(65, 98)) <= covered

    normalized = " ".join(_section("Whole-Roadmap Pull-Forward Audit").split())
    assert "没有 placeholder abstraction 被提出" in normalized
    assert "`production Python = 179`" in normalized


def test_three_ledgers_stay_distinct() -> None:
    section = _section("Ledgers")
    for heading in ("CURRENT_PRODUCTION", "CURRENT_READINESS", "RETAINED_LATER"):
        assert f"### {heading}" in section, heading
    normalized = " ".join(section.split())
    assert "Readiness 不等于 compiler acceptance" in normalized
    assert "未发生任何 public/backend/execution/release ownership 的静默重指派" in (
        normalized
    )


def test_law_records_carry_premises_evidence_and_counterexamples() -> None:
    rows = _rows(_section("Semantic Laws And Rewriting Premises"))[1:]
    assert tuple(row[0] for row in rows) == LAWS
    for row in rows:
        assert len(row) == 6, row[0]
        _, statement, domain, premises, evidence, counterexample = row
        assert statement and domain and premises and evidence and counterexample, row[0]
    normalized = " ".join(_section("Semantic Laws And Rewriting Premises").split())
    assert "不使用无条件的 `is_associative` / `is_commutative` 标志" in normalized


def test_counterexample_records_are_complete_and_bounded() -> None:
    rows = _rows(_section("Reference Cases And Counterexamples"))[1:]
    assert tuple(row[0] for row in rows) == CASES
    for row in rows:
        assert len(row) == 4 and all(row), row[0]
    normalized = " ".join(_section("Reference Cases And Counterexamples").split())
    assert "有限用例只能**反驳**全称主张，不能证明它们" in normalized
    assert "不证明 SQL 语义正确性" in normalized
    assert "本 Slice **不**添加 parser production" in normalized


def _bag(*rows: tuple[int, ...]) -> ProjectFiniteBag:
    return ProjectFiniteBag(
        entries=tuple(
            ProjectBagNullEntry(
                row=ProjectBagNullRow(
                    values=tuple(project_bag_int(value) for value in row)
                ),
                multiplicity=1,
            )
            for row in rows
        )
    )


def _join(
    kind: ProjectBagNullJoinKind,
    left: ProjectFiniteBag,
    right: ProjectFiniteBag,
    *,
    left_width: int,
    right_width: int,
    pairs: tuple[tuple[int, int], ...],
) -> ProjectFiniteBag:
    return evaluate_project_bag_null_join(
        ProjectBagNullJoinSpecification(
            kind=kind,
            left_width=left_width,
            right_width=right_width,
            correspondences=tuple(
                ProjectBagNullEqualityCorrespondence(
                    left_position=left_position,
                    right_position=right_position,
                )
                for left_position, right_position in pairs
            ),
        ),
        left,
        right,
    )


def _total(bag: ProjectFiniteBag) -> int:
    return sum(entry.multiplicity for entry in bag.entries)


def test_stepwise_whole_path_and_required_hop_multiplicities_are_reproduced() -> None:
    """Reproduce C01 through the existing bounded BAG/NULL oracle."""

    a = _bag((1,))
    b = _bag((1, 10), (1, 11))
    empty_c = ProjectFiniteBag(entries=())

    a_left_b = _join(
        ProjectBagNullJoinKind.LEFT,
        a,
        b,
        left_width=1,
        right_width=2,
        pairs=((0, 0),),
    )
    assert _total(a_left_b) == 2

    stepwise = _join(
        ProjectBagNullJoinKind.LEFT,
        a_left_b,
        empty_c,
        left_width=3,
        right_width=2,
        pairs=((2, 0),),
    )
    required = _join(
        ProjectBagNullJoinKind.INNER,
        a_left_b,
        empty_c,
        left_width=3,
        right_width=2,
        pairs=((2, 0),),
    )
    b_inner_c = _join(
        ProjectBagNullJoinKind.INNER,
        b,
        empty_c,
        left_width=2,
        right_width=2,
        pairs=((1, 0),),
    )
    whole_path = _join(
        ProjectBagNullJoinKind.LEFT,
        a,
        b_inner_c,
        left_width=1,
        right_width=4,
        pairs=((0, 0),),
    )

    assert (_total(stepwise), _total(whole_path), _total(required)) == (2, 1, 0)


def test_documented_set_operation_multiplicity_arithmetic_holds() -> None:
    left = {"x": 2, "y": 3}
    right = {"y": 1, "z": 4}
    later = ({"y": 1, "z": 4}, {"z": 1})
    classes = ("x", "y", "z")

    union_all = {key: left.get(key, 0) + right.get(key, 0) for key in classes}
    union_distinct = {
        key: int(left.get(key, 0) > 0 or right.get(key, 0) > 0) for key in classes
    }
    intersect_all = {key: min(left.get(key, 0), right.get(key, 0)) for key in classes}
    intersect_distinct = {
        key: int(left.get(key, 0) > 0 and right.get(key, 0) > 0) for key in classes
    }
    except_all = {
        key: max(left.get(key, 0) - sum(item.get(key, 0) for item in later), 0)
        for key in classes
    }
    except_distinct = {
        key: int(left.get(key, 0) > 0 and all(item.get(key, 0) == 0 for item in later))
        for key in classes
    }

    assert union_all == {"x": 2, "y": 4, "z": 4}
    assert union_distinct == {"x": 1, "y": 1, "z": 1}
    assert intersect_all == {"x": 0, "y": 1, "z": 0}
    assert intersect_distinct == {"x": 0, "y": 1, "z": 0}
    assert except_all == {"x": 2, "y": 2, "z": 0}
    assert except_distinct == {"x": 1, "y": 0, "z": 0}

    laws = " ".join(_section("Reference Cases And Counterexamples").split())
    for operation in ("UNION ALL", "INTERSECT ALL", "EXCEPT ALL"):
        assert operation in laws, operation


def test_decision_set_is_confirmed_and_records_its_alternatives() -> None:
    section = _section("Resolved Decision Set")
    for decision in DECISIONS:
        assert f"### {decision} " in section, decision
    assert section.count("`CONFIRMED`") >= len(DECISIONS)
    normalized = " ".join(section.split())
    for evidence in (
        "未采纳的备选",
        "扩展现有 `joinBody`",
        "只作用于**直接二元**右输入",
        "以既有命名关系作为唯一显式组合边界",
        "`ALL` 或 `DISTINCT` **必须显式书写**",
        "三种模式下一律为 `WARNING`",
        "授权对 `project_final_outputs.py` 做窄重构",
        "`Decimal` 进入支持域，要求精度与标度完全相同",
        "拆分「当前 IR 产物」与「未来 SQLPlan 契约」",
        "记为 **proposal**，未被采纳为 authority",
    ):
        assert evidence in normalized, evidence


def test_route_comparison_and_per_slice_contracts_are_complete() -> None:
    section = _section("Route Selection")
    screen = _rows(section)[1:]
    screened = {row[0].strip("*") for row in screen if row[0].strip("*")[0].isdigit()}
    assert {"8", "9", "10", "11", "12"} <= screened
    assert any("13" in item and "16" in item for item in screened)

    route = tuple(
        (row[0], row[1]) for row in _rows(section) if row[0].isdigit() and len(row) == 2
    )
    assert tuple(item[0] for item in route) == tuple(str(n) for n in range(1, 12))

    contracts = tuple(
        row for row in _rows(section) if row[0].isdigit() and len(row) == 7
    )
    assert tuple(row[0] for row in contracts) == tuple(str(n) for n in range(2, 12))
    for row in contracts:
        assert all(cell for cell in row), row[0]

    normalized = " ".join(section.split())
    assert "**选定**" in normalized
    assert "**早期垂直闭合**" in normalized
    # The comparison is qualitative; it must not claim a computed weighted total.
    assert "**没有**计算加权总分，也没有回溯打分矩阵" in normalized
    assert "本文件不声称任何数值比较结果" in normalized
    for exit_id in EXITS:
        assert exit_id in normalized, exit_id
    for consumer in ("Phase 65", "Phase 67", "Phase 68", "Phase 73", "Phase 88"):
        assert consumer in normalized, consumer
    assert "都不需要从名字、最后输出或规范化字节重建缺失语义" in normalized


def test_compatibility_exit_and_zero_delta_boundary_are_exact() -> None:
    public = " ".join(_section("Public And Compatibility Exit").split())
    for evidence in (
        "`0.1.0` | UNCHANGED",
        "既有 78 个码、消息与顺序不变",
        "top-level schema/keys 不变",
        "`__all__ == ()`",
        "ZERO DELTA",
        "本 Slice 对上述每一项的实际 delta 均为零",
        "additive public",
        "把整个 Phase 64 称作「additive private only」是不准确的",
        "JSON schema 未变与 「无公开行为变更」是两件事",
    ):
        assert evidence in public, evidence

    layers = tuple(
        row
        for row in _rows(_section("Public And Compatibility Exit"))
        if row and row[0] in {"Slice 1", "Phase 64（Slices 2–9）", "Phase 64 运行期"}
    )
    assert len(layers) == 3, layers

    zero = _section("Slice 1 Zero-Delta Boundary")
    for line in (
        "production delta = 0",
        "grammar / generated delta = 0",
        "public API / CLI / JSON / SQL delta = 0",
        "package / dependency / lockfile / workflow / version delta = 0",
        "Phase-64 implementation delta = 0",
    ):
        assert line in zero, line


def test_changed_path_closure_and_inventory_transition_are_exact() -> None:
    section = _section("Exact Changed-Path Closure")
    rows = _rows(section)[1:]
    assert len(rows) == 6
    statuses = [row[0] for row in rows]
    assert statuses.count("A") == 2 and statuses.count("M") == 4
    for _, path in rows:
        assert (REPO_ROOT / path).is_file(), path
        assert not path.startswith(("src/", "grammar/", "scripts/", ".github/")), path
    for line in (
        "A2/M4/D0",
        "6 paths",
        "production Python: 179 -> 179",
        "tests: 428 -> 429",
    ):
        assert line in section, line


def test_reader_and_inventory_ownership_is_declared() -> None:
    normalized = " ".join(_section("Reader And Inventory Ownership").split())
    for evidence in (
        "唯一 mutable lifecycle-document reader",
        "它不读取、不命名、也不伪装引用 mutable lifecycle 文档路径",
        "专属 inventory reader 继续独占 current whole-repository Python inventory",
        "不做动态 inventory scan",
        "bb52135038973b40638ff86367ba478846f898c6` 的 immutable source/Git 对象",
        "decision/route/static assurance 仍然执行",
        "也不从 pytest 内部拉取历史",
        "不创建任何永久禁止未来 Phase-64 语法出现在 current HEAD 的断言",
        "历史 delta 使用两个 immutable commit",
        "测试不访问网络",
    ):
        assert evidence in normalized, evidence


def test_exact_immutable_starting_evidence_is_bound() -> None:
    document = _normalized()
    for evidence in (
        BASELINE,
        BASELINE_TREE,
        BASELINE_PARENT,
        "Complete validation performance interlude II",
        "34002966434",
        "push / main / 1 / success",
        "101405014835",
        "101405014976",
        "production Python = 179",
        "test Python = 428",
        "collected tests = 11526",
    ):
        assert evidence in document, evidence

    if not _has_object(BASELINE) or not _has_object(BASELINE_PARENT):
        pytest.skip("baseline lineage objects are unavailable in a shallow checkout")
    assert _git("show", "-s", "--format=%T", BASELINE) == BASELINE_TREE
    assert _git("show", "-s", "--format=%P", BASELINE) == BASELINE_PARENT
    # Historical delta between two immutable commits, never against a future HEAD.
    assert (
        _git("diff", "--name-only", BASELINE_PARENT, BASELINE, "--", "src", "grammar")
        == ""
    )


def test_phase64_absence_is_asserted_against_the_immutable_baseline_only() -> None:
    """Bind the pre-implementation absence to the frozen baseline, not current HEAD."""

    if not _has_object(BASELINE):
        pytest.skip(f"baseline object {BASELINE} is unavailable in a shallow checkout")
    grammar = _git("show", f"{BASELINE}:grammar/Pietto.g4")
    assert "(INNER | LEFT) JOIN identifier AS identifier" in grammar
    for absent in (
        "CROSS",
        "RIGHT",
        "FULL",
        "SEMI",
        "ANTI",
        "UNION",
        "INTERSECT",
        "EXCEPT",
        "DISTINCT",
    ):
        assert f"{absent}:" not in grammar, absent
    ast_nodes = _git("show", f"{BASELINE}:src/pietto/ast_nodes.py")
    assert "One authored INNER or LEFT relationship JOIN occurrence." in ast_nodes


def test_slice1_accounting_and_publication_contract_are_exact() -> None:
    accounting = _section("Slice 1 Accounting")
    for line in (
        "documentation/static-test root-cause repairs = 0/12",
        "additional mechanical historical doc/test-reader paths = 0/12",
        "authoritative validator process starts = 0/4",
        "production mutations = 0",
    ):
        assert line in accounting, line
    assert "不消耗 repair batch" in " ".join(accounting.split())

    publication = _section("Validation And Publication")
    assert "UV_PYTHON=3.13 uv run python scripts/validate.py --timings" in publication
    assert "Establish Phase 64 flat relational algebra route" in publication
    assert (
        "PASS — PHASE64_SLICE1_PRODUCT_PHASE_INITIATION_EXPANSION_READINESS_"
        "DESIGN_ROUTE_LOCK_END_TO_END" in publication.replace("\n", "")
    )


def test_external_review_records_use_the_current_eleven_field_shape() -> None:
    section = _section("External Reference Review")
    records = tuple(line for line in section.splitlines() if line.startswith("### R"))
    assert len(records) == 11
    assert records[0].startswith("### R17 ") and records[-1].startswith("### R27 ")
    for index in range(1, 12):
        assert f"\n{index}. " in section, index
    normalized = " ".join(section.split())
    for evidence in (
        "WHAT_NOT_TO_COPY",
        "不是产品对等声明",
        "在 `2026-09-06` DNS 解析失败",
        "**未确立**",
        "本次未刷新",
        "所有测试保持 network-free",
    ):
        assert evidence in normalized, evidence


def _route_owner_labels() -> dict[str, str]:
    section = _section("Route Selection")
    return {
        row[0]: row[1] for row in _rows(section) if len(row) == 2 and row[0].isdigit()
    }


def test_decision_owner_references_agree_with_the_selected_route() -> None:
    """Every cited Slice exists, and syntax/semantic/IR stages stay distinguishable."""

    owners = _route_owner_labels()
    assert set(owners) == {str(index) for index in range(1, 12)}

    section = _section("Resolved Decision Set")
    cited = tuple(
        line for line in section.splitlines() if line.startswith("- 实现 owner：")
    )
    # D08 classifies atomic rows rather than naming an implementation owner.
    assert len(cited) == len(DECISIONS) - 1
    for line in cited:
        referenced = set(re.findall(r"Slice (\d+)", line))
        assert referenced, line
        assert referenced <= set(owners), line

    stages = ("syntax owner", "semantic owner", "IR consumer")
    joined = "\n".join(cited)
    for stage in stages:
        assert f"**{stage}**" in joined, stage

    # The specific owner corrections: each decision names its true semantic stage.
    expected = {
        "D04": "Slice 9",
        "D05": "Slice 7",
        "D06": "Slice 9",
        "D07": "Slice 8",
    }
    for decision, owner in expected.items():
        start = section.index(f"### {decision} ")
        end = section.find("\n### ", start)
        body = section[start:] if end == -1 else section[start:end]
        assert owner in body, (decision, owner)

    # Slice 2 owns the authored surface for JOIN syntax and set-operation clauses.
    assert "set-operation" in owners["2"]
    assert "grammar" in owners["2"]

    start = section.index("### D08 ")
    end = section.find("\n### ", start)
    d08 = " ".join((section[start:] if end == -1 else section[start:end]).split())
    assert "不得为了保住「两项」这个数字" in d08
    assert "`IMPLEMENT_NOW`" in d08 and "`DEFER_BY_NECESSITY`" in d08


def test_route_alternatives_differ_structurally_from_the_selected_route() -> None:
    """A rejected candidate may not be described as a split the selection already made."""

    owners = _route_owner_labels()
    section = _section("Route Selection")
    rows = {
        row[0].strip("*"): row[1]
        for row in _rows(section)
        if len(row) == 3 and row[0].strip("*") and row[0].strip("*")[0].isdigit()
    }
    assert "12" in rows
    # The selected route already separates grammar/AST (2) from ON semantics (3),
    # so that split can never be what distinguishes a 12-slice candidate.
    assert "grammar" in owners["2"] and "条件语义" in owners["3"]
    assert "grammar/AST 与 ON 语义拆开" not in rows["12"]
    # The recorded alternative must name a slice the selected route actually has.
    assert "Slice 4" in rows["12"]

    normalized = " ".join(section.split())
    assert "那是**错误**的" in normalized
    assert "也从未存在过一次同分或一次数值比较" in normalized


def test_authored_mode_source_map_is_consistent_and_keeps_base_authority() -> None:
    section = _section("Authored Mode Source Map")
    rows = _rows(section)[1:]
    assert tuple(row[0] for row in rows) == ("M1", "M2", "M3", "M4", "M5")
    for row in rows:
        assert len(row) == 6 and all(row), row[0]

    modes = {row[0]: row for row in rows}
    # Generic ON performs no relationship discovery; refinement retains the base.
    assert "**无**关系发现" in modes["M3"][2]
    assert "base condition 保留" in modes["M4"][2]
    assert "JOIN_LOCAL_ON_REFINEMENT" in modes["M4"][3]
    assert "RELATIONSHIP_BASE_MATCH" in modes["M1"][3]
    assert "base AND refinement" in modes["M4"][4]
    # CROSS carries no match condition at all.
    assert "无 condition" in modes["M5"][3]

    normalized = " ".join(section.split())
    assert "在当前 baseline **不可解析**" in normalized
    assert "JOIN body 内是否存在关系遍历" in normalized
    assert "`WHERE` 在 JOIN **之后**过滤" in normalized
    assert "已批准表面**不包含**多跳 `VIA` 加 `ON` refinement" in normalized
    assert "本文件不代为选择、也不声称已闭合" in normalized

    # Examples must use existing scalar spelling: `==` is comparison, `=` is an alias.
    grammar = (REPO_ROOT / "grammar/Pietto.g4").read_text(encoding="utf-8")
    assert "EQ: '=='" in grammar and "ASSIGN: '='" in grammar
    for row in rows:
        example = row[1]
        for predicate in re.findall(r"`  on ([^`]+)`", example):
            assert "==" in predicate, (row[0], predicate)
            assert not re.search(r"(?<![=!<>])=(?!=)", predicate), (row[0], predicate)
    # Qualified references name declared bindings, never an invented alias.
    joined = " ".join(row[1] for row in rows)
    declared = set(re.findall(r"as (\w+):", joined)) | set(
        re.findall(r"from (\w+)", joined)
    )
    for qualified in re.findall(r"on (\w+)\.\w+ == (\w+)\.\w+", joined):
        assert set(qualified) <= declared, (qualified, declared)


def test_decimal_support_agrees_across_decision_law_and_pull_forward() -> None:
    decision = _section("Resolved Decision Set")
    start = decision.index("### D07 ")
    end = decision.find("\n### ", start)
    d07 = " ".join((decision[start:] if end == -1 else decision[start:end]).split())
    for evidence in (
        "`Decimal` 进入支持域，要求精度与标度完全相同",
        "nullability 是**独立证据**",
        "参数缺失或未传播时**不猜测**",
        "不做隐式拓宽、不做舍入、不从聚合结果反推",
        "`Any`、`Bytes`、`Json` 仍在已批准 row-equivalence 支持域之外",
        "历史 relationship 比较的支持范围不因本决定顺带放宽",
    ):
        assert evidence in d07, evidence

    # UNION ALL must not inherit a row-equivalence prerequisite.
    assert "`UNION ALL` 只要求形状与类型兼容，**不要求**重复比较能力" in d07

    law = next(
        row
        for row in _rows(_section("Semantic Laws And Rewriting Premises"))
        if row[0] == "L08"
    )
    assert "精确同参" in law[3]
    assert "Decimal" in law[5] and "参数缺失或不一致" in law[5]
    assert "`Decimal`/`Json`" not in law[5]

    pull_forward = " ".join(_section("Whole-Roadmap Pull-Forward Audit").split())
    assert "支持域按 D07 划定（含精确同参 `Decimal(p,s)`）" in pull_forward
    assert "不沿用历史 relationship 比较推迟表" in pull_forward


def test_current_ir_products_and_future_sqlplan_occupy_distinct_rows() -> None:
    rows = _rows(_section("Whole-Roadmap Pull-Forward Audit"))[1:]
    core = tuple(row for row in rows if row[0] == "64 core")
    assert len(core) == 2
    assert all(row[2].strip("`") == "IMPLEMENT_NOW" for row in core), core

    phase65 = tuple(row for row in rows if row[0] == "65")
    assert len(phase65) == 2
    classes = {row[2].strip("`") for row in phase65}
    assert classes == {"CONTRACT_ONLY_NOW", "DEFER_BY_NECESSITY"}

    deferred = next(row for row in phase65 if row[2].strip("`") == "DEFER_BY_NECESSITY")
    # The deferral names missing SQL planning interfaces, not an unselected backend.
    assert "SQL planning/legality 接口本身" in deferred[3]
    assert "这与「尚未选定后端」无关" in deferred[3]

    consumers = {
        row[0]: row
        for row in _rows(_section("Route Selection"))
        if len(row) == 3 and row[0].startswith("Phase ")
    }
    # Phase 68 consumes the single-match cardinality meaning despite no resources.
    assert "基数错误含义" in consumers["Phase 68"][1]
    assert "资源与 effect 的缺席不等于没有下游 consumer" in consumers["Phase 68"][2]


def test_external_default_facts_are_recorded_accurately() -> None:
    section = _section("External Reference Review")
    start = section.index("### R26 ")
    end = section.find("\n### ", start)
    r26 = " ".join((section[start:] if end == -1 else section[start:end]).split())
    for evidence in (
        "`union(self, table, /, *rest, distinct: bool = False)`",
        "`intersect(self, table, /, *rest, distinct: bool = True)`",
        "`difference(self, table, /, *rest, distinct: bool = True)`",
        "`append` 等价于 `UNION ALL`",
        "`remove` 等价于 `EXCEPT ALL`",
        "`intersect` 等价于 `INTERSECT ALL`",
        "并不统一去重",
        "不能作为任何 Pietto 默认值的依据",
        "**产品决定**",
        "它不是 fail-closed / no-winner 规则的推论",
    ):
        assert evidence in r26, evidence
    assert "两者的 set operation **默认去重**" not in r26

    start = section.index("### R25 ")
    end = section.find("\n### ", start)
    r25 = " ".join((section[start:] if end == -1 else section[start:end]).split())
    for evidence in (
        "`Condition` 与 `ConditionalApplier`",
        "运行期检查",
        "不等于**证明**该改写及其前提是可靠的",
        "这是**范围**决定",
        "不是「egg 无法表达条件」的能力主张",
    ):
        assert evidence in r25, evidence
    assert "引擎不验证前提" not in r25

    decisions = _section("Resolved Decision Set")
    start = decisions.index("### D04 ")
    end = decisions.find("\n### ", start)
    d04 = " ".join((decisions[start:] if end == -1 else decisions[start:end]).split())
    assert "这是一项**产品决定**，不是 fail-closed / no-winner 规则的推论" in d04
    assert "生态默认值**并不一致**" in d04


def test_reconciliation_lineage_preserves_the_original_publication_facts() -> None:
    section = _section("Slice 1 Reconciliation Lineage")
    for line in (
        "original publication commit = f483d2d3a73edbfd6b203fb3014758095e398e23",
        "original publication tree   = 008c88eb2a6aadb63172bb2ee3b326971dfe058d",
        "original publication parent = bb52135038973b40638ff86367ba478846f898c6",
        "original publication CI     = 34049044651 / push / main / attempt 1 / success",
        "original publication closure = A2/M4/D0, 6 paths",
        "correction closure = A0/M5/D0",
        "production delta   = 0",
        "production Python  = 179 (unchanged)",
        "test-file inventory = 429 (unchanged)",
    ):
        assert line in section, line
    normalized = " ".join(section.split())
    assert "**不是** failed head" in normalized
    assert "不是 Slice 2、 不是新的 numbered Slice" in normalized
    assert "不改变任何已确认的产品选择、N=11 或 E01–E12" in normalized


def test_principal_never_pins_an_exact_live_enum_member_set() -> None:
    """Structural guard for R1: live enums may only be checked for retention.

    An equality comparison against a live enum would fail the moment a Phase-64
    slice legally extends it, so the principal must never contain one.
    """

    module = ast.parse(REPOSITORY_FACTS.python(Path(__file__).resolve()).text)
    offenders: list[str] = []
    for node in ast.walk(module):
        if not isinstance(node, ast.Compare):
            continue
        if not any(isinstance(operator, ast.Eq) for operator in node.ops):
            continue
        referenced = {
            child.id
            for child in ast.walk(node)
            if isinstance(child, ast.Name) and child.id in LIVE_ENUMS
        }
        if referenced:
            offenders.append(f"line {node.lineno}: {sorted(referenced)}")
    assert not offenders, offenders

    # The historical counterpart must exist for every live enum whose exact set
    # is a baseline fact, so removing the equality did not remove the coverage.
    frozen = {name for _, name, _ in BASELINE_ENUM_SETS}
    assert frozen <= set(LIVE_ENUMS)
