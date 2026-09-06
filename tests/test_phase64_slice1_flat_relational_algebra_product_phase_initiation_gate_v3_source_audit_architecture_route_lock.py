"""Phase 64 Slice 1 product gate, source audit, architecture and route-lock principal."""

from __future__ import annotations

from pathlib import Path
import re
import subprocess

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
from pietto._project.project_completion import ProjectEffectiveOutputTerminalReason
from pietto._project.project_grain import ProjectGrainOriginKind
from pietto._project.project_ir_joins import ProjectIRBinaryJoinKind
from pietto._project.project_query_block_ir import ProjectIRQueryBlockTerminalReason
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


def test_source_audit_findings_match_the_live_source_they_cite() -> None:
    rows = _rows(_section("Live Pietto Source Audit"))[1:]
    assert tuple(row[0] for row in rows) == FINDINGS
    for row in rows:
        assert len(row) == 4 and all(row), row[0]

    # F01/F03: the authored and binary JOIN kind sets are still exactly INNER/LEFT.
    assert tuple(AuthoredJoinKind) == (AuthoredJoinKind.INNER, AuthoredJoinKind.LEFT)
    assert tuple(ProjectIRBinaryJoinKind) == (
        ProjectIRBinaryJoinKind.INNER,
        ProjectIRBinaryJoinKind.LEFT,
    )
    # F05: the refinement and post-JOIN condition scopes already exist.
    assert {scope.name for scope in ProjectRelationshipConditionScope} == {
        "RELATIONSHIP_BASE_MATCH",
        "JOIN_LOCAL_ON_REFINEMENT",
        "POST_JOIN_FILTER",
    }
    # F06: the relation-output identity domain exists.
    assert ProjectModuleRowFieldKind.RELATION_OUTPUT in tuple(ProjectModuleRowFieldKind)
    # F09: both transferred fail-closed terminals are live.
    assert (
        ProjectEffectiveOutputTerminalReason.EFFECTIVE_UPSTREAM_JOIN_UNSUPPORTED
        in tuple(ProjectEffectiveOutputTerminalReason)
    )
    assert (
        ProjectIRQueryBlockTerminalReason.EFFECTIVE_JOIN_INPUT_REBIND_UNSUPPORTED
        in tuple(ProjectIRQueryBlockTerminalReason)
    )
    # F11: no quotient or set-alternative grain origin exists yet.
    assert {origin.name for origin in ProjectGrainOriginKind} == {
        "SOURCE_ROW_DOMAIN",
        "GROUPED_RESULT",
        "GLOBAL_AGGREGATE",
    }
    # F12/D07: the deferred equality builtins are exactly the documented four.
    conditions = REPOSITORY_FACTS.python(
        REPO_ROOT / "src/pietto/_project/project_relationship_conditions.py"
    ).text
    assert (
        '_DEFERRED_EQUALITY_BUILTINS = frozenset({"Any", "Bytes", "Decimal", "Json"})'
        in conditions
    )
    # D05: the existing severity channel already carries WARNING.
    assert {severity.name for severity in Severity} == {"ERROR", "WARNING"}


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
    assert "平局取较少" in normalized
    assert "**早期垂直闭合**" in normalized
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
        "Slice 1 本身对上述每一项的实际 delta 均为零",
    ):
        assert evidence in public, evidence

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
        "绑定到本文件的 immutable baseline tree 与 blob 证据",
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
        return
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
        return
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
