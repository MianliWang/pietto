from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

import _phase54_active_gate2_manifest as active_gate2_manifest
import _pietto_publication_topology as topology
import _pietto_reader_closure as closure
import _pietto_runtime_journal as journal

REPO_ROOT = Path(__file__).resolve().parents[1]

AGENTS_REL = "AGENTS.md"
GOVERNANCE_REL = "docs/spec/pietto-semantic-slice-convergence-governance-v1.md"
RECONCILIATION_REL = (
    "docs/plan/phase-54-post-slice12-workflow-hardening-and-midphase-route-"
    "reconciliation.md"
)
ROADMAP_REL = "docs/spec/pietto-active-roadmap-phase53-70-v2.md"
MASTER_PLAN_REL = "docs/plan/phase-54-local-import-module-export-foundation.md"
SKILLS_ROOT = REPO_ROOT / ".claude" / "skills"
SKILL_NAMES = (
    "pietto-mechanical-closure",
    "pietto-publication-topology",
    "pietto-semantic-convergence",
)
CONVERGENCE_HEADING = "Semantic Slice Convergence"
TOOLING_RELS = (
    "tests/_pietto_publication_topology.py",
    "tests/_pietto_reader_closure.py",
    "tests/_pietto_runtime_journal.py",
)
FORBIDDEN_DIFF_PATHS = (
    ".github/workflows/ci.yml",
    "Makefile",
    "README.md",
    "grammar",
    "pyproject.toml",
    "pyrightconfig.json",
    "pyrightconfig.tests.json",
    "scripts",
    "src",
    "tests/fixtures",
    "uv.lock",
)
SLICE12_SEED_REL = "tests/test_phase54_semantic_fact_preservation.py"


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _normalized(relative: str) -> str:
    return " ".join(_read(relative).split())


def _headings(text: str, level: int) -> tuple[str, ...]:
    pattern = rf"^{'#' * level} (?!#)(.+?)\s*$"
    return tuple(match.group(1) for match in re.finditer(pattern, text, re.MULTILINE))


def _section(text: str, heading: str) -> str:
    marker = f"\n## {heading}\n"
    start = text.index(marker) + len(marker)
    remainder = text[start:]
    end = remainder.find("\n## ")
    return remainder if end == -1 else remainder[:end]


def _frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise AssertionError("skill must begin with a frontmatter fence")
    end = text.index("\n---\n", 3)
    fields: dict[str, str] = {}
    for line in text[4:end].splitlines():
        key, separator, value = line.partition(":")
        if not separator:
            raise AssertionError(f"frontmatter line is not a mapping: {line}")
        fields[key.strip()] = value.strip()
    return fields


def _skill_body(text: str) -> str:
    return text[text.index("\n---\n", 3) + 5 :]


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def _valid_payload() -> dict[str, object]:
    return {
        "authority": journal.AUTHORITY_MARKER,
        "gate_state": {"gate0": "PASS"},
        "interlude": "post-slice12-workflow-hardening",
        "journal_kind": "pietto-workflow-hardening-interlude-progress",
        "journal_version": 1,
        "lifecycle": {"phase54": "ACTIVE"},
        "outranked_by": list(journal.REQUIRED_OUTRANKING),
        "replacement": journal.REPLACEMENT_MARKER,
        "revalidation": journal.REVALIDATION_MARKER,
        "trusted_base_sha": "bd6bdcf17361b11d3067beec534432d37ffe6f05",
        "trusted_base_tree": "b4691181f4d535ab10757e89d75dd881a37f418b",
    }


def test_agents_convergence_section_is_present_and_concise() -> None:
    agents = _read(AGENTS_REL)
    assert f"\n## {CONVERGENCE_HEADING}\n" in agents
    section = _section(agents, CONVERGENCE_HEADING)
    bullets = [line for line in section.splitlines() if line.startswith("- ")]
    assert 5 <= len(bullets) <= 8
    assert len(section.splitlines()) < 40


def test_agents_convergence_section_links_resolve_to_tracked_documents() -> None:
    section = _section(_read(AGENTS_REL), CONVERGENCE_HEADING)
    assert GOVERNANCE_REL in section
    assert ".claude/skills/" in section
    assert (REPO_ROOT / GOVERNANCE_REL).is_file()
    visible = set(_git("ls-files").splitlines()) | set(
        _git("ls-files", "--others", "--exclude-standard").splitlines()
    )
    assert GOVERNANCE_REL in visible


def test_agents_heading_levels_are_exact_and_unambiguous() -> None:
    agents = _read(AGENTS_REL)
    level_two = _headings(agents, 2)
    level_three = _headings(agents, 3)
    assert CONVERGENCE_HEADING in level_two
    assert CONVERGENCE_HEADING not in level_three
    assert level_two.count(CONVERGENCE_HEADING) == 1
    assert agents.count(f"\n## {CONVERGENCE_HEADING}\n") == 1
    assert agents.count(f"\n### {CONVERGENCE_HEADING}\n") == 0


def test_agents_convergence_section_excludes_procedural_and_status_material() -> None:
    section = _section(_read(AGENTS_REL), CONVERGENCE_HEADING)
    for forbidden in (
        "```",
        "uv run",
        "git ",
        "Slice 12",
        "Slice 13",
        "Phase 54",
        "repair generation 1",
    ):
        assert forbidden not in section, forbidden


def test_governance_specification_headings_and_ownership_are_exact() -> None:
    governance = _read(GOVERNANCE_REL)
    assert _headings(governance, 1) == (
        "Pietto Semantic Slice Convergence Governance v1",
    )
    level_two = _headings(governance, 2)
    for required in (
        "Applicability",
        "Authority-root Design",
        "Canonical Root-derived Projections",
        "Complete Collection And State Algebra",
        "Semantic Convergence Before Mechanical Closure",
        "Exact-tree Finding Batching",
        "Architecture Reset",
        "Property-first Testing",
        "Semantic Versus Mechanical Classification",
        "Reader, Hash, And Digest Closure",
        "Publication Topology",
        "Runtime Journal Non-authority",
        "Gate And Publication Boundaries",
        "Reusable Slice Planning Guidance",
    ):
        assert required in level_two, required
    assert len(level_two) == len(set(level_two))


def test_governance_specification_owns_the_detailed_convergence_contract() -> None:
    governance = _normalized(GOVERNANCE_REL)
    for required in (
        "Roots are named by object identity, never by structural equality",
        "one canonical projection derived from the roots",
        "zero addition",
        "zero delta",
        "Review comment arrival order must not define repair generations",
        "negative-compatibility matrix",
        "non-authoritative",
        "model neutral and client neutral",
    ):
        assert required in governance, required


def test_governance_specification_declares_versioning_and_non_goals() -> None:
    governance = _read(GOVERNANCE_REL)
    versioning = " ".join(_section(governance, "Versioning And Change Control").split())
    assert "convergence schema is v1" in versioning
    assert "separately authorized new version" in versioning
    non_goals = " ".join(
        _section(governance, "Non-goals And Separate Authorization").split()
    )
    for phrase in (
        "does not authorize a slice",
        "change a route",
        "irreversible publication operation",
    ):
        assert phrase in non_goals, phrase


def test_reconciliation_record_contains_the_required_sections() -> None:
    record = _read(RECONCILIATION_REL)
    level_two = _headings(record, 2)
    for required in (
        "Status And Interlude Identity",
        "Slices 9 Through 12 Causal-root Postmortem",
        "Slice 12 Generation-14 Analysis",
        "Workflow-cost Analysis",
        "Slices 13 Through 16 Reconciliation",
        "Readiness Ledger",
        "Current Route Posture",
        "Recommended But Not Authorized",
        "Exact Prerequisites Carried Into Slice 13",
        "Interlude Lifecycle State",
    ):
        assert required in level_two, required


def test_reconciliation_record_states_generation_root_and_revision_counts() -> None:
    analysis = _section(_read(RECONCILIATION_REL), "Slice 12 Generation-14 Analysis")
    for phrase in (
        "review generation",
        "causal-root family",
        "publication revision",
        "not** fourteen independent architecture",
        "iatrogenic",
    ):
        assert phrase in analysis, phrase


def test_reconciliation_record_readiness_ledger_uses_the_exact_vocabulary() -> None:
    ledger = _section(_read(RECONCILIATION_REL), "Readiness Ledger")
    vocabulary = (
        "IMPLEMENT_NOW",
        "PRIVATE_READINESS_NOW",
        "CONTRACT_ONLY_NOW",
        "DEFER_BY_NECESSITY",
        "OUT_OF_SCOPE",
    )
    for value in vocabulary:
        assert value in ledger, value
    for row in ledger.splitlines():
        if not row.startswith("| R"):
            continue
        assert sum(row.count(value) for value in vocabulary) == 1, row


def test_reconciliation_record_preserves_the_sixteen_slice_route() -> None:
    record = _read(RECONCILIATION_REL)
    assert "sixteen-Slice route" in record
    assert "adds no seventeenth Slice" not in record
    reconciliation = _section(record, "Slices 13 Through 16 Reconciliation")
    for title in (
        "Package-neutral Identity Layering",
        "Private Module Inspection And Canonical Serialization",
        "Rust-ready Pure Boundaries",
        "Completion Audit, Status Lock, And Phase 55 Handoff",
    ):
        assert title in reconciliation, title
    posture = _section(record, "Current Route Posture")
    assert "**SAFE**" in posture
    assert "minimum authorized change required is none" in posture


def test_active_roadmap_and_master_plan_record_the_published_slice12_state() -> None:
    roadmap = _read(ROADMAP_REL)
    plan = _read(MASTER_PLAN_REL)
    for text in (roadmap, plan):
        assert "bd6bdcf17361b11d3067beec534432d37ffe6f05" in text
        assert "b4691181f4d535ab10757e89d75dd881a37f418b" in text
        assert "PHASE54_SLICE13_GATE0_GATE1" in text
    assert "Slice 12 Gate 2 candidate" in plan
    assert "## Status And Slice 12 Lifecycle" in plan
    assert "governance-schema successor" in roadmap


def test_exactly_three_project_skills_exist_with_unique_names() -> None:
    directories = tuple(sorted(entry.name for entry in SKILLS_ROOT.iterdir()))
    assert directories == SKILL_NAMES
    names = []
    for name in SKILL_NAMES:
        fields = _frontmatter((SKILLS_ROOT / name / "SKILL.md").read_text("utf-8"))
        names.append(fields["name"])
    assert tuple(sorted(names)) == SKILL_NAMES
    assert len(set(names)) == 3


def test_every_skill_declares_valid_frontmatter() -> None:
    for name in SKILL_NAMES:
        text = (SKILLS_ROOT / name / "SKILL.md").read_text("utf-8")
        fields = _frontmatter(text)
        assert set(fields) == {"name", "description", "disable-model-invocation"}
        assert fields["name"] == name
        assert 40 <= len(fields["description"]) <= 1024
        assert fields["description"].endswith(".")


def test_every_skill_is_explicit_invocation_only() -> None:
    for name in SKILL_NAMES:
        fields = _frontmatter((SKILLS_ROOT / name / "SKILL.md").read_text("utf-8"))
        assert fields["disable-model-invocation"] == "true"


def test_every_skill_references_only_existing_supporting_files() -> None:
    for name in SKILL_NAMES:
        directory = SKILLS_ROOT / name
        files = tuple(sorted(entry.name for entry in directory.iterdir()))
        assert files == ("SKILL.md", "reference.md")
        body = _skill_body((directory / "SKILL.md").read_text("utf-8"))
        assert "reference.md" in body
        assert (directory / "reference.md").read_text("utf-8").strip()


def test_skill_bodies_cover_their_required_topics() -> None:
    required: dict[str, tuple[str, ...]] = {
        "pietto-semantic-convergence": (
            "Authority-root checklist",
            "Canonical projection",
            "Complete collection and state algebra",
            "Exact-tree finding batching",
            "Causal-root grouping",
            "Architecture reset",
            "Property and state-space matrix",
            "Semantic freeze",
            "Runtime journal use",
        ),
        "pietto-mechanical-closure": (
            "Reader and reader-of-reader discovery",
            "Reader classes to sweep",
            "Dependency graph and components",
            "Dependency-first expected values",
            "Reviewed patch proposal",
            "Zero addition and zero delta",
        ),
        "pietto-publication-topology": (
            "dirty gate candidate",
            "clean topic candidate",
            "non-amend repair child",
            "pull-request merge",
            "shallow pull-request checkout",
            "squashed main",
            "natural main push",
            "refs, parents, merge base, shallow boundary, event metadata",
        ),
    }
    for name, phrases in required.items():
        raw = _skill_body((SKILLS_ROOT / name / "SKILL.md").read_text("utf-8"))
        body = " ".join(raw.split())
        for phrase in phrases:
            assert phrase in body, f"{name}: {phrase}"


def test_skills_are_not_an_independent_lifecycle_authority() -> None:
    for name in SKILL_NAMES:
        body = _skill_body((SKILLS_ROOT / name / "SKILL.md").read_text("utf-8"))
        assert GOVERNANCE_REL in body
        assert "not an independent" in body or "Normative contract" in body


def test_reader_discovery_finds_direct_readers_of_a_changed_path(
    tmp_path: Path,
) -> None:
    (tmp_path / "target.md").write_text("# target\n", encoding="utf-8")
    (tmp_path / "reader_a.py").write_text('X = "target.md"\n', encoding="utf-8")
    (tmp_path / "reader_b.py").write_text("Y = 1\n", encoding="utf-8")
    edges = closure.discover_edges(
        repo_root=tmp_path,
        universe=("reader_a.py", "reader_b.py"),
        targets=("target.md",),
    )
    assert closure.readers_of(edges, ("target.md",)) == ("reader_a.py",)
    assert edges[0].kind == closure.READER_KIND_PATH_LITERAL
    assert edges[0].occurrences == 1


def test_reader_discovery_omits_non_readers(tmp_path: Path) -> None:
    (tmp_path / "target.md").write_text("# target\n", encoding="utf-8")
    (tmp_path / "unrelated.py").write_text('X = "other.md"\n', encoding="utf-8")
    edges = closure.discover_edges(
        repo_root=tmp_path,
        universe=("unrelated.py",),
        targets=("target.md",),
    )
    assert edges == ()
    assert closure.readers_of(edges, ("target.md",)) == ()


def test_reader_discovery_detects_count_literal_readers(tmp_path: Path) -> None:
    (tmp_path / "counts.py").write_text("assert total == 461\n", encoding="utf-8")
    edges = closure.discover_edges(
        repo_root=tmp_path,
        universe=("counts.py",),
        count_literals=("== 461",),
    )
    assert len(edges) == 1
    assert edges[0].kind == closure.READER_KIND_COUNT_LITERAL


def test_reader_discovery_fails_closed_on_a_missing_path(tmp_path: Path) -> None:
    with pytest.raises(closure.ClosureError):
        closure.discover_edges(
            repo_root=tmp_path, universe=("absent.py",), targets=("x",)
        )
    with pytest.raises(closure.ClosureError):
        closure.discover_edges(repo_root=tmp_path, universe=(), targets=("x",))


def test_reader_discovery_fails_closed_outside_the_repository_root(
    tmp_path: Path,
) -> None:
    inside = tmp_path / "inside"
    inside.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("X = 1\n", encoding="utf-8")
    with pytest.raises(closure.ClosureError):
        closure.read_source(inside, "../outside.py")


def test_transitive_readers_follow_reader_of_reader_edges() -> None:
    graph = closure.build_graph({"leaf": [], "middle": ["leaf"], "outer": ["middle"]})
    assert closure.transitive_readers(graph, ["leaf"]) == ("middle", "outer")
    assert closure.transitive_readers(graph, ["outer"]) == ()


def test_transitive_readers_fail_closed_on_an_unknown_seed() -> None:
    graph = closure.build_graph({"a": ["b"]})
    with pytest.raises(closure.ClosureError):
        closure.transitive_readers(graph, ["missing"])


def test_graph_and_components_are_correct_on_an_acyclic_example() -> None:
    graph = closure.build_graph({"a": ["b"], "b": ["c"], "c": []})
    assert graph.nodes == ("a", "b", "c")
    components = closure.strongly_connected_components(graph)
    assert components == (("a",), ("b",), ("c",))
    assert all(len(component) == 1 for component in components)


def test_graph_and_components_are_correct_on_a_cyclic_example() -> None:
    graph = closure.build_graph({"x": ["y"], "y": ["z"], "z": ["x"], "w": ["x"]})
    components = closure.strongly_connected_components(graph)
    assert ("x", "y", "z") in components
    assert ("w",) in components
    assert len(components) == 2


def test_condensation_order_places_targets_before_readers() -> None:
    graph = closure.build_graph({"a": ["b"], "b": ["c"], "c": []})
    order = closure.condensation_order(graph)
    flattened = [member for component in order for member in component]
    assert flattened.index("c") < flattened.index("b") < flattened.index("a")
    cyclic = closure.build_graph({"x": ["y"], "y": ["x"], "w": ["x"]})
    cyclic_order = closure.condensation_order(cyclic)
    assert cyclic_order[0] == ("x", "y")
    assert cyclic_order[1] == ("w",)


def test_reader_omission_is_detected_by_zero_addition() -> None:
    missing = closure.verify_zero_addition(
        discovered=("a.py", "b.py"), frozen=("a.py",)
    )
    assert missing == ("b.py",)


def test_reader_injection_is_detected_by_zero_addition() -> None:
    assert (
        closure.verify_zero_addition(discovered=("a.py",), frozen=("a.py", "b.py"))
        == ()
    )
    frozen_only = set(("a.py", "b.py")) - set(("a.py",))
    assert frozen_only == {"b.py"}


def test_expected_replacements_are_deterministic_and_ordered(tmp_path: Path) -> None:
    (tmp_path / "one.py").write_text("total = 461\ntotal2 = 461\n", encoding="utf-8")
    (tmp_path / "two.py").write_text("total = 461\n", encoding="utf-8")
    rules = (closure.ReplacementRule(old="461", new="462"),)
    first = closure.calculate_replacements(
        repo_root=tmp_path, paths=("two.py", "one.py"), rules=rules
    )
    second = closure.calculate_replacements(
        repo_root=tmp_path, paths=("one.py", "two.py"), rules=rules
    )
    assert first == second
    assert first.order == ("one.py", "two.py")
    assert first.total_occurrences == 3
    assert first.applied is False
    ordered = closure.calculate_replacements(
        repo_root=tmp_path,
        paths=("one.py", "two.py"),
        rules=rules,
        order=("two.py", "one.py"),
    )
    assert ordered.order == ("two.py", "one.py")


def test_replacement_rules_fail_closed_on_no_op_and_duplicate_rules(
    tmp_path: Path,
) -> None:
    (tmp_path / "one.py").write_text("total = 461\n", encoding="utf-8")
    with pytest.raises(closure.ClosureError):
        closure.ReplacementRule(old="461", new="461")
    with pytest.raises(closure.ClosureError):
        closure.ReplacementRule(old="", new="462")
    with pytest.raises(closure.ClosureError):
        closure.calculate_replacements(repo_root=tmp_path, paths=("one.py",), rules=())
    duplicate = (
        closure.ReplacementRule(old="461", new="462"),
        closure.ReplacementRule(old="461", new="463"),
    )
    with pytest.raises(closure.ClosureError):
        closure.calculate_replacements(
            repo_root=tmp_path, paths=("one.py",), rules=duplicate
        )
    with pytest.raises(closure.ClosureError):
        closure.calculate_replacements(
            repo_root=tmp_path,
            paths=("one.py",),
            rules=(closure.ReplacementRule(old="461", new="462"),),
            order=("two.py",),
        )


def test_replacement_plan_is_dry_run_and_writes_nothing(tmp_path: Path) -> None:
    source = tmp_path / "one.py"
    source.write_text("total = 461\n", encoding="utf-8")
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    listing_before = tuple(sorted(entry.name for entry in tmp_path.iterdir()))
    plan = closure.calculate_replacements(
        repo_root=tmp_path,
        paths=("one.py",),
        rules=(closure.ReplacementRule(old="461", new="462"),),
    )
    assert plan.total_occurrences == 1
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    assert tuple(sorted(entry.name for entry in tmp_path.iterdir())) == listing_before
    assert '"applied": false' in closure.plan_as_json(plan)


def test_zero_delta_verification_refuses_an_empty_check(tmp_path: Path) -> None:
    (tmp_path / "one.py").write_text("total = 461\n", encoding="utf-8")
    rules = (closure.ReplacementRule(old="461", new="462"),)
    with pytest.raises(closure.ClosureError):
        closure.verify_zero_delta(repo_root=tmp_path, paths=(), rules=rules)
    with pytest.raises(closure.ClosureError):
        closure.verify_zero_delta(repo_root=tmp_path, paths=("one.py",), rules=())
    assert closure.main(["--repo-root", str(tmp_path), "--mode", "verify"]) == 2
    assert closure.main(["--repo-root", str(tmp_path), "--mode", "discover"]) == 2


def test_replacement_plan_rejects_interacting_rules(tmp_path: Path) -> None:
    (tmp_path / "one.py").write_text("aaa\n", encoding="utf-8")
    overlapping = (
        closure.ReplacementRule(old="aa", new="b"),
        closure.ReplacementRule(old="a", new="c"),
    )
    with pytest.raises(closure.ClosureError):
        closure.calculate_replacements(
            repo_root=tmp_path, paths=("one.py",), rules=overlapping
        )
    chained = (
        closure.ReplacementRule(old="x", new="y"),
        closure.ReplacementRule(old="y", new="z"),
    )
    with pytest.raises(closure.ClosureError):
        closure.calculate_replacements(
            repo_root=tmp_path, paths=("one.py",), rules=chained
        )
    with pytest.raises(closure.ClosureError):
        closure.calculate_replacements(
            repo_root=tmp_path,
            paths=("one.py",),
            rules=(closure.ReplacementRule(old="aaa", new="b"),),
            order=("one.py", "one.py"),
        )
    with pytest.raises(closure.ClosureError):
        closure.calculate_replacements(
            repo_root=tmp_path,
            paths=(),
            rules=(closure.ReplacementRule(old="aaa", new="b"),),
        )


def test_discovery_summary_includes_count_literal_readers(tmp_path: Path) -> None:
    (tmp_path / "counts.py").write_text("assert total == 461\n", encoding="utf-8")
    edges = closure.discover_edges(
        repo_root=tmp_path, universe=("counts.py",), count_literals=("== 461",)
    )
    assert closure.readers_of(edges, ("== 461",)) == ("counts.py",)
    assert (
        closure.main(
            [
                "--repo-root",
                str(tmp_path),
                "--mode",
                "discover",
                "--path",
                "counts.py",
                "--count-literal",
                "== 461",
            ]
        )
        == 0
    )


def test_zero_delta_verification_is_independent_of_the_plan(tmp_path: Path) -> None:
    source = tmp_path / "one.py"
    source.write_text("total = 461\n", encoding="utf-8")
    rules = (closure.ReplacementRule(old="461", new="462"),)
    assert closure.verify_zero_delta(
        repo_root=tmp_path, paths=("one.py",), rules=rules
    ) == ("one.py:461:1",)
    source.write_text("total = 462\n", encoding="utf-8")
    assert (
        closure.verify_zero_delta(repo_root=tmp_path, paths=("one.py",), rules=rules)
        == ()
    )


def test_reader_closure_module_exposes_no_apply_function() -> None:
    source = _read("tests/_pietto_reader_closure.py")
    for forbidden in ("write_text(", "unlink(", "rename(", "os.replace"):
        assert forbidden not in source, forbidden
    assert "read-only" in source


def test_every_standardized_projection_builds_and_self_verifies(
    tmp_path: Path,
) -> None:
    fixtures = topology.build_all(tmp_path)
    assert len(fixtures) == len(topology.TOPOLOGY_KINDS)
    for fixture in fixtures:
        topology.assert_topology(fixture)
        assert topology.verify(fixture.observation, fixture.expectation) == ()


def test_projection_set_is_complete_and_sorted() -> None:
    assert topology.TOPOLOGY_KINDS == tuple(sorted(topology.TOPOLOGY_KINDS))
    assert len(topology.TOPOLOGY_KINDS) == 7
    assert topology.sequence_is_complete(topology.TOPOLOGY_KINDS)
    assert not topology.sequence_is_complete(topology.TOPOLOGY_KINDS[:-1])


def test_pull_request_merge_projection_has_two_ordered_parents(tmp_path: Path) -> None:
    fixture = topology.build_topology(
        topology.TOPOLOGY_PULL_REQUEST_MERGE, tmp_path / "merge"
    )
    assert len(fixture.observation.head_parents) == 2
    assert fixture.observation.head_parents[0] == fixture.refs["base"]
    assert fixture.observation.head_parents[1] == fixture.refs["topic"]
    assert fixture.observation.event_name == topology.EVENT_PULL_REQUEST
    assert fixture.observation.branch == "HEAD"


def test_shallow_projection_has_no_parents_and_no_merge_base(tmp_path: Path) -> None:
    fixture = topology.build_topology(
        topology.TOPOLOGY_SHALLOW_PULL_REQUEST, tmp_path / "shallow"
    )
    assert fixture.observation.shallow is True
    assert fixture.observation.head_parents == ()
    assert fixture.observation.merge_base == ""


def test_shallow_projection_models_the_integration_merge_checkout(
    tmp_path: Path,
) -> None:
    fixture = topology.build_topology(
        topology.TOPOLOGY_SHALLOW_PULL_REQUEST, tmp_path / "shallow"
    )
    assert fixture.observation.branch == "HEAD"
    assert fixture.observation.head == fixture.refs["merge"]
    assert fixture.observation.head != fixture.refs["topic"]
    assert fixture.observation.head_tree == fixture.expectation.head_tree
    assert fixture.observation.event_name == topology.EVENT_PULL_REQUEST
    assert topology.verify(fixture.observation, fixture.expectation) == ()


def test_observation_reports_staged_paths_and_rejects_a_clean_expectation(
    tmp_path: Path,
) -> None:
    root = tmp_path / "clean"
    fixture = topology.build_topology(topology.TOPOLOGY_CLEAN_TOPIC, root)
    assert fixture.observation.staged_paths == ()
    (root / "AUTHORITY.md").write_text("# authority\n\nstaged\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "AUTHORITY.md"], cwd=root, check=True, capture_output=True
    )
    staged = topology.observe(
        root,
        event_name=topology.EVENT_LOCAL,
        event_head_ref="",
        event_base_ref="",
        base_ref="refs/heads/main",
    )
    assert staged.staged_paths == ("AUTHORITY.md",)
    assert topology.verify(staged, fixture.expectation)


def test_observation_fails_closed_on_an_unrecognized_status_record(
    tmp_path: Path,
) -> None:
    root = tmp_path / "renamed"
    topology.build_topology(topology.TOPOLOGY_CLEAN_TOPIC, root)
    subprocess.run(
        ["git", "mv", "reader.txt", "renamed.txt"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    with pytest.raises(topology.TopologyError):
        topology.observe(
            root,
            event_name=topology.EVENT_LOCAL,
            event_head_ref="",
            event_base_ref="",
            base_ref="refs/heads/main",
        )


def test_squash_projection_tree_equals_the_topic_tree(tmp_path: Path) -> None:
    fixture = topology.build_topology(
        topology.TOPOLOGY_SQUASH_MAIN, tmp_path / "squash"
    )
    assert fixture.observation.head_parents == (fixture.refs["base"],)
    assert fixture.observation.head_tree == fixture.expectation.head_tree
    assert fixture.observation.branch == topology.MAIN_BRANCH


def test_main_push_projection_models_the_integration_depth_one_checkout(
    tmp_path: Path,
) -> None:
    fixture = topology.build_topology(
        topology.TOPOLOGY_MAIN_PUSH, tmp_path / "mainpush"
    )
    assert fixture.observation.shallow is True
    assert fixture.observation.head_parents == ()
    assert fixture.observation.merge_base == ""
    assert fixture.observation.branch == topology.MAIN_BRANCH
    assert fixture.observation.event_name == topology.EVENT_PUSH
    assert fixture.observation.head == fixture.refs["squash"]
    assert topology.verify(fixture.observation, fixture.expectation) == ()
    local = topology.build_topology(
        topology.TOPOLOGY_SQUASH_MAIN, tmp_path / "localsquash"
    )
    assert local.observation.shallow is False
    assert local.observation.head_parents == (local.refs["base"],)


def test_clean_topic_predicate_rejects_a_replaced_tree(tmp_path: Path) -> None:
    trailer = active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_REVIEWED_TREE_TRAILER
    subject = active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_REPAIR2_SUBJECT
    matches = active_gate2_manifest._phase54_post_slice12_interlude_message_matches_tree
    tree = "a" * 40
    other = "b" * 40
    assert matches(f"{subject}\n\n{trailer}: {tree}", tree, subject)
    assert not matches(f"{subject}\n\n{trailer}: {other}", tree, subject)
    assert not matches(f"{subject}\n\n{trailer}: {tree}", other, subject)
    assert not matches(f"Other subject\n\n{trailer}: {tree}", tree, subject)
    assert not matches(subject, tree, subject)
    assert not matches(
        f"{subject}\n\n{trailer}: {tree}\n{trailer}: {tree}", tree, subject
    )
    assert not matches(f"{subject}\n\n{trailer}: {tree}", "not-a-tree", subject)
    shapes = active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_CHILD_SHAPES
    trees = active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_PUBLISHED_TREES
    assert len(shapes) == len({base for base, _ in shapes})
    assert len(shapes) == len({child for _, child in shapes})
    assert len(trees) == len(set(trees))
    assert all(len(tree) == 40 for tree in trees)
    assert active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_TREE == trees[0]


def test_wrong_parent_reference_tree_shallow_and_event_are_rejected(
    tmp_path: Path,
) -> None:
    fixture = topology.build_topology(topology.TOPOLOGY_CLEAN_TOPIC, tmp_path / "clean")
    variants = topology.rejected_variants(fixture.expectation)
    names = tuple(sorted(name for name, _ in variants))
    assert names == (
        "wrong_dirty_set",
        "wrong_event",
        "wrong_head",
        "wrong_parent",
        "wrong_ref",
        "wrong_shallow",
        "wrong_staged_set",
        "wrong_tree",
    )
    for name, corrupted in variants:
        assert topology.verify(fixture.observation, corrupted), name


def test_projections_can_be_built_from_a_real_repository_and_run_commands(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=source, check=True)
    (source / "marker.txt").write_text("real content\n", encoding="utf-8")
    (source / "nested").mkdir()
    (source / "nested" / "reader.txt").write_text("count=1\n", encoding="utf-8")
    fixture = topology.build_topology(
        topology.TOPOLOGY_CLEAN_TOPIC, tmp_path / "projected", source=source
    )
    assert (fixture.root / "marker.txt").read_text("utf-8") == "real content\n"
    assert (fixture.root / "nested" / "reader.txt").is_file()
    assert not (fixture.root / "reader.txt").is_file()
    result = topology.run_in_projection(fixture, ["git", "rev-parse", "HEAD"])
    assert result.returncode == 0
    assert result.stdout.strip() == fixture.observation.head
    with pytest.raises(topology.TopologyError):
        topology.run_in_projection(fixture, [])
    empty = tmp_path / "empty"
    empty.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=empty, check=True)
    with pytest.raises(topology.TopologyError):
        topology.build_topology(
            topology.TOPOLOGY_CLEAN_TOPIC, tmp_path / "fromempty", source=empty
        )


def test_topology_fixture_rejects_a_non_empty_root(tmp_path: Path) -> None:
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "stray.txt").write_text("stray\n", encoding="utf-8")
    with pytest.raises(topology.TopologyError):
        topology.build_topology(topology.TOPOLOGY_CLEAN_TOPIC, occupied)
    with pytest.raises(topology.TopologyError):
        topology.build_topology("unknown_projection", tmp_path / "unknown")


def test_topology_module_never_touches_the_primary_repository() -> None:
    source = _read("tests/_pietto_publication_topology.py")
    for forbidden in ("REPO_ROOT", "parents[1]", "http://", "https://"):
        assert forbidden not in source, forbidden
    assert "temporary" in source


def test_runtime_journal_requires_non_authority_markers() -> None:
    assert journal.AUTHORITY_MARKER == "NON_AUTHORITATIVE"
    assert journal.REPLACEMENT_MARKER == "SAFE_TO_REPLACE_ATOMICALLY"
    assert journal.REVALIDATION_MARKER == "LIVE_STATE_MUST_BE_REVALIDATED"
    payload = _valid_payload()
    assert journal.validate_payload(payload) == ()
    for key, marker in journal.REQUIRED_MARKERS.items():
        broken = dict(payload)
        broken[key] = "AUTHORITATIVE"
        problems = journal.validate_payload(broken)
        assert any(marker in problem for problem in problems)


def test_runtime_journal_rejects_a_boolean_version() -> None:
    payload = _valid_payload()
    payload["journal_version"] = True
    problems = journal.validate_payload(payload)
    assert any("journal_version" in problem for problem in problems)
    payload["journal_version"] = 0
    assert journal.validate_payload(payload)
    payload["journal_version"] = "1"
    assert journal.validate_payload(payload)
    payload["journal_version"] = 1
    assert journal.validate_payload(payload) == ()


def test_runtime_journal_requires_the_outranking_authorities() -> None:
    payload = _valid_payload()
    payload["outranked_by"] = ["git"]
    problems = journal.validate_payload(payload)
    assert any("outranked_by omits" in problem for problem in problems)
    payload["outranked_by"] = "git"
    assert journal.validate_payload(payload)


def test_runtime_journal_rejects_an_incomplete_payload_without_writing(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "journal.json"
    destination.write_text('{"previous": true}\n', encoding="utf-8")
    before = destination.read_bytes()
    incomplete = _valid_payload()
    del incomplete["trusted_base_sha"]
    with pytest.raises(journal.JournalError):
        journal.atomic_replace(destination, incomplete)
    assert destination.read_bytes() == before
    assert tuple(sorted(entry.name for entry in tmp_path.iterdir())) == (
        "journal.json",
    )


def test_runtime_journal_replacement_is_atomic(tmp_path: Path) -> None:
    destination = tmp_path / "journal.json"
    payload = _valid_payload()
    journal.atomic_replace(destination, payload)
    assert journal.load(destination) == payload
    payload["journal_version"] = 2
    journal.atomic_replace(destination, payload)
    assert journal.load(destination)["journal_version"] == 2
    assert tuple(sorted(entry.name for entry in tmp_path.iterdir())) == (
        "journal.json",
    )
    with pytest.raises(journal.JournalError):
        journal.atomic_replace(tmp_path / "absent" / "journal.json", payload)


def test_runtime_journal_refuses_a_repository_destination(tmp_path: Path) -> None:
    payload = _valid_payload()
    with pytest.raises(journal.JournalError):
        journal.atomic_replace(
            REPO_ROOT / "runtime-journal.json", payload, repo_root=REPO_ROOT
        )
    outside = tmp_path / "journal.json"
    journal.atomic_replace(outside, payload, repo_root=REPO_ROOT)
    assert outside.is_file()


def test_runtime_journal_refuses_a_repository_destination_without_a_hint() -> None:
    payload = _valid_payload()
    with pytest.raises(journal.JournalError):
        journal.atomic_replace(REPO_ROOT / "runtime-journal.json", payload)
    with pytest.raises(journal.JournalError):
        journal.atomic_replace(REPO_ROOT / "tests" / "runtime-journal.json", payload)
    assert not (REPO_ROOT / "runtime-journal.json").exists()
    assert not (REPO_ROOT / "tests" / "runtime-journal.json").exists()


def test_runtime_journal_load_validates_the_schema(tmp_path: Path) -> None:
    destination = tmp_path / "journal.json"
    payload = _valid_payload()
    journal.atomic_replace(destination, payload)
    assert journal.load(destination) == payload
    destination.write_text('{"authority": "AUTHORITATIVE"}\n', encoding="utf-8")
    with pytest.raises(journal.JournalError):
        journal.load(destination)
    incomplete = dict(payload)
    del incomplete["outranked_by"]
    destination.write_text(
        json.dumps(incomplete, sort_keys=True) + "\n", encoding="utf-8"
    )
    with pytest.raises(journal.JournalError):
        journal.load(destination)


def test_runtime_journal_is_never_authoritative(tmp_path: Path) -> None:
    payload = _valid_payload()
    assert journal.is_authoritative(payload) is False
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("[]\n", encoding="utf-8")
    with pytest.raises(journal.JournalError):
        journal.load(corrupt)
    corrupt.write_text("not json\n", encoding="utf-8")
    with pytest.raises(journal.JournalError):
        journal.load(corrupt)


def test_historical_reader_inventory_benchmarks_reproduce() -> None:
    readers = active_gate2_manifest.MECHANICAL_READER_PATHS
    assert len(readers) == 173
    assert SLICE12_SEED_REL in active_gate2_manifest.ADDED_PATHS
    assert SLICE12_SEED_REL not in readers
    assert len(set(readers) | {SLICE12_SEED_REL}) == 174
    costs = _section(_read(RECONCILIATION_REL), "Workflow-cost Analysis")
    assert "64 at Gate 0, 65 at the primary Gate 2, 173 final" in costs
    assert "174" in costs


def test_historical_allowlist_arithmetic_reproduces() -> None:
    added = active_gate2_manifest.ADDED_PATHS
    non_reader = active_gate2_manifest.NON_READER_MODIFIED_PATHS
    readers = active_gate2_manifest.MECHANICAL_READER_PATHS
    assert (len(added), len(non_reader), len(readers)) == (3, 6, 173)
    assert len(active_gate2_manifest.MODIFIED_PATHS) == len(non_reader) + len(readers)
    assert len(active_gate2_manifest.ALLOWLIST_PATHS) == 182


def test_published_reader_graph_condensation_is_deterministic_and_total() -> None:
    readers = tuple(
        sorted(active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_READER_PATHS)
    )
    edges = closure.discover_edges(
        repo_root=REPO_ROOT, universe=readers, targets=readers
    )
    graph = closure.graph_from_edges(edges)
    assert graph.nodes == tuple(sorted(set(graph.nodes)))
    components = closure.strongly_connected_components(graph)
    members = [member for component in components for member in component]
    assert sorted(members) == list(graph.nodes)
    assert len(members) == len(set(members))
    order = closure.condensation_order(graph)
    assert len(order) == len(components)
    assert sorted(order, key=lambda component: component[0]) == list(components)
    assert closure.strongly_connected_components(graph) == components


def test_interlude_manifest_state_and_allowlist_are_exact() -> None:
    added = active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_ADDED_PATHS
    non_reader = (
        active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_NON_READER_MODIFIED_PATHS
    )
    readers = active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_READER_PATHS
    assert (len(added), len(non_reader), len(readers)) == (12, 4, 40)
    assert (
        len(active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_MODIFIED_PATHS) == 44
    )
    assert (
        len(active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_ALLOWLIST_PATHS) == 56
    )
    assert active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_BASE == (
        "bd6bdcf17361b11d3067beec534432d37ffe6f05"
    )
    assert active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_BRANCH == (
        "phase54/post-slice12-workflow-hardening"
    )
    for relative in added:
        assert (REPO_ROOT / relative).is_file(), relative
    publication_states = (
        active_gate2_manifest.phase54_post_slice12_interlude_is_active(),
        active_gate2_manifest.phase54_post_slice12_interlude_clean_topic_is_active(),
    )
    assert sum(publication_states) <= 1
    if any(publication_states):
        assert (
            active_gate2_manifest.phase54_post_slice12_interlude_publication_is_active()
        )


def test_no_compiler_runtime_or_public_surface_changes() -> None:
    diff = _git("diff", "--name-only", "--", *FORBIDDEN_DIFF_PATHS)
    assert diff == ""
    for relative in TOOLING_RELS:
        source = _read(relative)
        assert "import pietto" not in source
        assert "from pietto" not in source
    assert '"0.1.0"' in _read("pyproject.toml")
