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


def test_replacement_plan_rejects_partially_overlapping_literals(
    tmp_path: Path,
) -> None:
    assert closure.literals_can_interact("ab", "bc")
    assert closure.literals_can_interact("bc", "ab")
    assert closure.literals_can_interact("aa", "a")
    assert not closure.literals_can_interact("ab", "cd")
    assert not closure.literals_can_interact("== 100", "!= 200")
    (tmp_path / "one.py").write_text("abc\n", encoding="utf-8")
    partial = (
        closure.ReplacementRule(old="ab", new="X"),
        closure.ReplacementRule(old="bc", new="Y"),
    )
    with pytest.raises(closure.ClosureError):
        closure.calculate_replacements(
            repo_root=tmp_path, paths=("one.py",), rules=partial
        )
    independent = (
        closure.ReplacementRule(old="== 100", new="== 101"),
        closure.ReplacementRule(old="!= 200", new="!= 201"),
    )
    plan = closure.calculate_replacements(
        repo_root=tmp_path, paths=("one.py",), rules=independent
    )
    assert plan.total_occurrences == 0


def _commit_source(source: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=source, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=T",
            "-c",
            "user.email=t@x",
            "commit",
            "-q",
            "-m",
            message,
        ],
        cwd=source,
        check=True,
    )


def _source_tree(source: Path, revision: str) -> str:
    return subprocess.run(
        ["git", "rev-parse", f"{revision}^{{tree}}"],
        cwd=source,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def test_journal_refuses_a_git_metadata_destination(tmp_path: Path) -> None:
    repository = tmp_path / "clone"
    repository.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=repository, check=True)
    payload = _valid_payload()
    for destination in (
        repository / ".git" / "journal.json",
        repository / ".git" / "HEAD",
        repository / ".git" / "refs" / "journal.json",
        repository / "journal.json",
    ):
        with pytest.raises(journal.JournalError):
            journal.atomic_replace(destination, payload)
    assert (repository / ".git" / "HEAD").read_text("utf-8").startswith("ref:")
    outside = tmp_path / "state"
    outside.mkdir()
    written = journal.atomic_replace(outside / "journal.json", payload)
    assert journal.load(written)["authority"] == journal.AUTHORITY_MARKER


def test_journal_refuses_bare_and_separate_git_directories(tmp_path: Path) -> None:
    payload = _valid_payload()
    bare = tmp_path / "bare.git"
    subprocess.run(["git", "init", "--bare", "--quiet", str(bare)], check=True)
    for destination in (bare / "HEAD", bare / "config", bare / "refs" / "journal.json"):
        with pytest.raises(journal.JournalError):
            journal.atomic_replace(destination, payload)
    assert (bare / "HEAD").read_text("utf-8").startswith("ref:")
    worktree = tmp_path / "work"
    worktree.mkdir()
    metadata = tmp_path / "meta"
    subprocess.run(
        ["git", "init", "--quiet", "--separate-git-dir", str(metadata), str(worktree)],
        check=True,
    )
    with pytest.raises(journal.JournalError):
        journal.atomic_replace(metadata / "HEAD", payload)
    assert (metadata / "HEAD").read_text("utf-8").startswith("ref:")


def test_replacement_plan_normalizes_aliased_paths(tmp_path: Path) -> None:
    (tmp_path / "one.py").write_text("total = 461\n", encoding="utf-8")
    assert closure.normalized_path(tmp_path, "./one.py") == "one.py"
    rules = (closure.ReplacementRule(old="461", new="462"),)
    with pytest.raises(closure.ClosureError):
        closure.calculate_replacements(
            repo_root=tmp_path, paths=("one.py", "./one.py"), rules=rules
        )
    with pytest.raises(closure.ClosureError):
        closure.calculate_replacements(
            repo_root=tmp_path,
            paths=("one.py",),
            rules=rules,
            order=("one.py", "./one.py"),
        )
    plan = closure.calculate_replacements(
        repo_root=tmp_path, paths=("./one.py",), rules=rules
    )
    assert plan.order == ("one.py",)
    assert plan.total_occurrences == 1
    assert closure.verify_zero_delta(
        repo_root=tmp_path, paths=("one.py", "./one.py"), rules=rules
    ) == ("one.py:461:1",)


def test_source_projection_removes_a_dangling_symlink(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=source, check=True)
    (source / "kept.py").write_text("kept\n", encoding="utf-8")
    (source / "dangling").symlink_to("missing-target")
    _commit_source(source, "first")
    (source / "dangling").unlink()

    entries = topology.candidate_entries(source)
    assert set(entries) == {"kept.py"}
    fixture = topology.build_topology(
        topology.TOPOLOGY_CLEAN_TOPIC, tmp_path / "clean", source=source
    )
    assert not (fixture.root / "dangling").is_symlink()
    listed = topology.run_in_projection(fixture, ["git", "ls-files"])
    assert listed.stdout.split() == ["kept.py"]


def test_replacement_rule_rejects_a_literal_surviving_its_own_result() -> None:
    with pytest.raises(closure.ClosureError):
        closure.ReplacementRule(old="v1", new="v10")
    with pytest.raises(closure.ClosureError):
        closure.ReplacementRule(old="461", new="461")
    with pytest.raises(closure.ClosureError):
        closure.ReplacementRule(old="", new="x")
    assert closure.ReplacementRule(old="461", new="462").new == "462"


def test_source_backed_projection_carries_the_exact_candidate_tree(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    (source / "docs").mkdir(parents=True)
    subprocess.run(["git", "init", "--quiet"], cwd=source, check=True)
    (source / "docs" / "spec.md").write_text("# spec\n", encoding="utf-8")
    (source / "reader.py").write_text("assert total == 1\n", encoding="utf-8")
    _commit_source(source, "first")
    (source / "reader.py").write_text("assert total == 2\n", encoding="utf-8")
    _commit_source(source, "second")
    (source / "reader.py").write_text("assert total == 3\n", encoding="utf-8")
    (source / "docs" / "added.md").write_text("# added\n", encoding="utf-8")
    expected = ("docs/added.md", "docs/spec.md", "reader.py")

    dirty = topology.build_topology(
        topology.TOPOLOGY_DIRTY_GATE2, tmp_path / "dirty", source=source
    )
    assert dirty.expectation.added_paths == ("docs/added.md",)
    assert dirty.expectation.modified_paths == ("reader.py",)
    assert topology.verify(dirty.observation, dirty.expectation) == ()

    for kind in (topology.TOPOLOGY_CLEAN_TOPIC, topology.TOPOLOGY_REPAIR_CHILD):
        fixture = topology.build_topology(kind, tmp_path / kind, source=source)
        listed = topology.run_in_projection(fixture, ["git", "ls-files"])
        assert tuple(sorted(listed.stdout.split())) == expected, kind
        assert not (fixture.root / "AUTHORITY.md").exists(), kind
        assert not (fixture.root / "added.md").exists(), kind
        assert (fixture.root / "reader.py").read_text("utf-8") == "assert total == 3\n"
        assert topology.verify(fixture.observation, fixture.expectation) == (), kind

    repair = topology.build_topology(
        topology.TOPOLOGY_REPAIR_CHILD, tmp_path / "threetrees", source=source
    )
    trees = topology.run_in_projection(
        repair, ["git", "log", "--format=%T", "-n", "3", "HEAD"]
    ).stdout.split()
    assert len(set(trees)) == 3
    assert trees[1:] == [
        _source_tree(source, "HEAD"),
        _source_tree(source, topology.source_base_revision(source)),
    ]


def test_replacement_plan_rejects_a_rule_recreated_across_the_seam(
    tmp_path: Path,
) -> None:
    (tmp_path / "one.py").write_text("abb\n", encoding="utf-8")
    with pytest.raises(closure.ClosureError):
        closure.calculate_replacements(
            repo_root=tmp_path,
            paths=("one.py",),
            rules=(closure.ReplacementRule(old="ab", new="a"),),
        )
    (tmp_path / "two.py").write_text("total = 461\n", encoding="utf-8")
    plan = closure.calculate_replacements(
        repo_root=tmp_path,
        paths=("two.py",),
        rules=(closure.ReplacementRule(old="461", new="462"),),
    )
    assert plan.total_occurrences == 1


def test_source_projections_are_anchored_to_the_main_authority(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    subprocess.run(["git", "init", "--quiet", "--initial-branch", "main"], cwd=source)
    (source / "reader.py").write_text("assert total == 1\n", encoding="utf-8")
    _commit_source(source, "main baseline")
    main_tree = _source_tree(source, "refs/heads/main")
    subprocess.run(["git", "checkout", "-q", "-b", "topic"], cwd=source, check=True)
    (source / "reader.py").write_text("assert total == 2\n", encoding="utf-8")
    _commit_source(source, "topic child")
    (source / "reader.py").write_text("assert total == 3\n", encoding="utf-8")

    assert topology.source_base_revision(source) == "refs/heads/main"
    for kind in (
        topology.TOPOLOGY_CLEAN_TOPIC,
        topology.TOPOLOGY_PULL_REQUEST_MERGE,
        topology.TOPOLOGY_SQUASH_MAIN,
    ):
        fixture = topology.build_topology(kind, tmp_path / kind, source=source)
        base_tree = topology.run_in_projection(
            fixture, ["git", "rev-parse", f"{fixture.refs['base']}^{{tree}}"]
        ).stdout.strip()
        assert base_tree == main_tree, kind
        assert topology.verify(fixture.observation, fixture.expectation) == (), kind

    clean = tmp_path / "cleansource"
    clean.mkdir()
    subprocess.run(["git", "init", "--quiet", "--initial-branch", "main"], cwd=clean)
    (clean / "reader.py").write_text("only\n", encoding="utf-8")
    _commit_source(clean, "only commit")
    with pytest.raises(topology.TopologyError):
        topology.build_topology(
            topology.TOPOLOGY_REPAIR_CHILD, tmp_path / "norepair", source=clean
        )


def test_repair_child_projects_a_committed_repair_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    subprocess.run(["git", "init", "--quiet", "--initial-branch", "main"], cwd=source)
    (source / "reader.py").write_text("assert total == 1\n", encoding="utf-8")
    _commit_source(source, "main baseline")
    main_tree = _source_tree(source, "refs/heads/main")
    subprocess.run(["git", "checkout", "-q", "-b", "topic"], cwd=source, check=True)
    (source / "reader.py").write_text("assert total == 2\n", encoding="utf-8")
    _commit_source(source, "topic child")
    topic_tree = _source_tree(source, "HEAD")
    (source / "reader.py").write_text("assert total == 3\n", encoding="utf-8")
    _commit_source(source, "committed repair child")
    repair_tree = _source_tree(source, "HEAD")

    assert not topology.source_is_dirty(source)
    fixture = topology.build_topology(
        topology.TOPOLOGY_REPAIR_CHILD, tmp_path / "repair", source=source
    )
    trees = topology.run_in_projection(
        fixture, ["git", "log", "--format=%T", "-n", "3", "HEAD"]
    ).stdout.split()
    assert trees == [repair_tree, topic_tree, main_tree]
    assert topology.verify(fixture.observation, fixture.expectation) == ()


def test_source_projection_refuses_a_gitlink_source(tmp_path: Path) -> None:
    inner = tmp_path / "inner"
    inner.mkdir()
    subprocess.run(["git", "init", "--quiet", "--initial-branch", "main"], cwd=inner)
    (inner / "inner.py").write_text("inner\n", encoding="utf-8")
    _commit_source(inner, "inner")
    source = tmp_path / "source"
    source.mkdir()
    subprocess.run(["git", "init", "--quiet", "--initial-branch", "main"], cwd=source)
    (source / "reader.py").write_text("reader\n", encoding="utf-8")
    _commit_source(source, "first")
    subprocess.run(
        [
            "git",
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "add",
            "--quiet",
            str(inner),
            "vendor",
        ],
        cwd=source,
        check=True,
    )
    _commit_source(source, "add submodule")
    staged = subprocess.run(
        ["git", "ls-files", "--stage"],
        cwd=source,
        check=True,
        text=True,
        capture_output=True,
    ).stdout
    assert "160000" in staged
    with pytest.raises(topology.TopologyError):
        topology.candidate_entries(source)
    with pytest.raises(topology.TopologyError):
        topology.build_topology(
            topology.TOPOLOGY_CLEAN_TOPIC, tmp_path / "clean", source=source
        )


def test_discovery_universe_uses_one_identity_per_reader(tmp_path: Path) -> None:
    (tmp_path / "reader.py").write_text("assert total == 461\n", encoding="utf-8")
    edges = closure.discover_edges(
        repo_root=tmp_path,
        universe=("reader.py", "./reader.py"),
        count_literals=("== 461",),
    )
    assert len(edges) == 1
    assert edges[0].reader == "reader.py"
    assert closure.readers_of(edges, ("== 461",)) == ("reader.py",)
    graph = closure.graph_from_edges(edges)
    assert graph.nodes == ("== 461", "reader.py")


def test_discovery_targets_use_one_identity_per_path(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "target.md").write_text("# target\n", encoding="utf-8")
    (tmp_path / "reader.py").write_text('SPEC = "docs/target.md"\n', encoding="utf-8")
    edges = closure.discover_edges(
        repo_root=tmp_path,
        universe=("reader.py",),
        targets=("./docs/target.md", "docs/target.md"),
    )
    assert len(edges) == 1
    assert edges[0].target == "docs/target.md"
    assert closure.readers_of(edges, ("docs/target.md",)) == ("reader.py",)
    with pytest.raises(closure.ClosureError):
        closure.discover_edges(
            repo_root=tmp_path, universe=("reader.py",), targets=("docs/missing.md",)
        )


def test_source_projection_propagates_a_deleted_path(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=source, check=True)
    (source / "kept.py").write_text("kept\n", encoding="utf-8")
    (source / "removed.py").write_text("removed\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=source, check=True)
    subprocess.run(
        ["git", "-c", "user.name=T", "-c", "user.email=t@x", "commit", "-q", "-m", "b"],
        cwd=source,
        check=True,
    )
    (source / "removed.py").unlink()

    added, modified, deleted = topology.source_dirty_paths(source)
    assert (added, modified, deleted) == ((), (), ("removed.py",))
    dirty = topology.build_topology(
        topology.TOPOLOGY_DIRTY_GATE2, tmp_path / "dirty", source=source
    )
    assert dirty.expectation.deleted_paths == ("removed.py",)
    assert topology.verify(dirty.observation, dirty.expectation) == ()

    clean = topology.build_topology(
        topology.TOPOLOGY_CLEAN_TOPIC, tmp_path / "clean", source=source
    )
    listed = topology.run_in_projection(clean, ["git", "ls-files"])
    assert listed.stdout.split() == ["kept.py"]
    assert not (clean.root / "removed.py").exists()


def test_publication_identity_rejects_a_replaced_tree_on_a_known_shape() -> None:
    manifest_module = active_gate2_manifest
    matches = (
        manifest_module._phase54_post_slice12_interlude_publication_identity_matches
    )
    identities = active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_CHILD_IDENTITIES
    trailer = active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_REVIEWED_TREE_TRAILER
    base = active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_BASE
    squash_subject = active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_SUBJECT
    first_base, first_subject, first_tree = identities[0]
    second_base, second_subject, second_tree = identities[1]
    assert matches((first_base,), first_subject, first_tree, first_subject)
    assert not matches((first_base,), first_subject, second_tree, first_subject)
    assert not matches((second_base,), second_subject, first_tree, second_subject)
    assert not matches(
        (second_base,),
        second_subject,
        first_tree,
        f"{second_subject}\n\n{trailer}: {first_tree}",
    )
    squash_tree = "d" * 40
    assert matches(
        (base,),
        squash_subject,
        squash_tree,
        f"{squash_subject}\n\n{trailer}: {squash_tree}",
    )
    # A forge-composed squash body may carry earlier historical trailers; only
    # the final line is authoritative for the squashed tree.
    assert matches(
        (base,),
        squash_subject,
        squash_tree,
        f"{squash_subject}\n\n* one\n\n{trailer}: {first_tree}\n\n"
        f"* two\n\n{trailer}: {squash_tree}",
    )
    assert not matches(
        (base,),
        squash_subject,
        squash_tree,
        f"{squash_subject}\n\n{trailer}: {squash_tree}\n\n{trailer}: {first_tree}",
    )
    assert not matches((base,), squash_subject, squash_tree, squash_subject)
    assert not matches((base,), squash_subject, squash_tree, f"{squash_subject}\n\nx")


def test_replacement_plan_rejects_a_match_created_by_an_earlier_rule(
    tmp_path: Path,
) -> None:
    (tmp_path / "one.py").write_text("ay\n", encoding="utf-8")
    with pytest.raises(closure.ClosureError):
        closure.calculate_replacements(
            repo_root=tmp_path,
            paths=("one.py",),
            rules=(
                closure.ReplacementRule(old="a", new="x"),
                closure.ReplacementRule(old="xy", new="z"),
            ),
        )


def test_source_projection_preserves_entry_type_and_mode(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=source, check=True)
    plain = source / "plain.py"
    plain.write_text("plain\n", encoding="utf-8")
    script = source / "run.sh"
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    script.chmod(0o755)
    (source / "link.py").symlink_to("plain.py")
    subprocess.run(["git", "add", "-A"], cwd=source, check=True)
    subprocess.run(
        ["git", "-c", "user.name=T", "-c", "user.email=t@x", "commit", "-q", "-m", "b"],
        cwd=source,
        check=True,
    )
    script.write_text("#!/bin/sh\necho hi\n", encoding="utf-8")

    expected = topology.candidate_entries(source)
    assert expected["run.sh"][0] == "100755"
    assert expected["link.py"][0] == "120000"
    assert expected["plain.py"][0] == "100644"

    fixture = topology.build_topology(
        topology.TOPOLOGY_CLEAN_TOPIC, tmp_path / "clean", source=source
    )
    listing = topology.run_in_projection(fixture, ["git", "ls-tree", "-r", "HEAD"])
    observed = {}
    for line in listing.stdout.splitlines():
        metadata, _, relative = line.partition("\t")
        fields = metadata.split()
        observed[relative] = (fields[0], fields[2])
    assert observed == expected
    assert (fixture.root / "link.py").is_symlink()

    other = tmp_path / "other"
    other.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=other, check=True)
    (other / "plain.py").write_text("different\n", encoding="utf-8")
    with pytest.raises(topology.TopologyError):
        topology._verify_candidate(fixture.root, other, committed=True)


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


def test_discovery_refuses_an_empty_target_set_before_reading(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "counts.py").write_text("assert total == 461\n", encoding="utf-8")
    exit_code = closure.main(
        [
            "--repo-root",
            str(tmp_path),
            "--mode",
            "discover",
            "--path",
            "counts.py",
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "discovery requires at least one target" in captured.err


def test_discovery_command_line_reaches_inventory_root_readers(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "inventory.py").write_text(
        'ROOTS = ("docs/spec/",)\n', encoding="utf-8"
    )
    edges = closure.discover_edges(
        repo_root=tmp_path, universe=("inventory.py",), inventory_roots=("docs/spec/",)
    )
    assert closure.readers_of(edges, ("docs/spec/",)) == ("inventory.py",)
    exit_code = closure.main(
        [
            "--repo-root",
            str(tmp_path),
            "--mode",
            "discover",
            "--path",
            "inventory.py",
            "--inventory-root",
            "docs/spec/",
        ]
    )
    reported = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert reported["readers"] == ["inventory.py"]
    assert reported["edges"][0]["kind"] == closure.READER_KIND_INVENTORY


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


def test_each_published_child_shape_is_bound_to_its_reviewed_tree() -> None:
    identities = active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_CHILD_IDENTITIES
    shapes = active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_CHILD_SHAPES
    trees = active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_PUBLISHED_TREES
    newest = (
        active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_UNREGISTERED_CHILD_SHAPE
    )
    assert trees == tuple(tree for _, _, tree in identities)
    assert shapes == (*((base, subject) for base, subject, _ in identities), newest)
    assert newest not in tuple((base, subject) for base, subject, _ in identities)
    assert newest[0] not in trees
    assert newest == (
        active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_REPAIR17_BASE,
        active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_REPAIR17_SUBJECT,
    )
    for base, subject, tree in identities:
        assert re.fullmatch(r"[0-9a-f]{40}", base), base
        assert re.fullmatch(r"[0-9a-f]{40}", tree), tree
        assert subject.startswith(("Add Pietto workflow", "Fix Pietto workflow"))


def test_clean_topic_rejects_a_published_tree_grafted_onto_another_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identities = active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_CHILD_IDENTITIES
    newest = (
        active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_UNREGISTERED_CHILD_SHAPE
    )
    trailer = active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_REVIEWED_TREE_TRAILER
    base_head = active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_BASE
    branch = active_gate2_manifest.PHASE54_POST_SLICE12_INTERLUDE_BRANCH
    state = active_gate2_manifest.Phase54Gate2RepositoryState(
        marker=active_gate2_manifest.PHASE54_ACTIVE_GATE2_MARKER,
        branch_oid="c" * 40,
        branch_head=branch,
        branch_upstream=f"origin/{branch}",
        ahead=0,
        behind=0,
        added_paths=frozenset(),
        modified_paths=frozenset(),
        deleted_paths=frozenset(),
        staged_paths=frozenset(),
        other_paths=frozenset(),
        worktree_count=1,
        shallow=False,
        active_git_operation=False,
    )

    matches_clean = (
        active_gate2_manifest._matches_phase54_post_slice12_interlude_clean_topic
    )

    def _recognized(parent: str, subject: str, tree: str, message: str) -> bool:
        def _output(args: list[str]) -> str:
            if args[:2] == ["rev-list", "--parents"]:
                return f"{'c' * 40} {parent}"
            if args[:3] == ["show", "-s", "--format=%s"]:
                return subject
            if args == ["rev-parse", "HEAD^{tree}"]:
                return tree
            if args[:2] == ["rev-parse", "--verify"]:
                return base_head
            raise AssertionError(args)

        monkeypatch.setattr(active_gate2_manifest, "_git_output", _output)
        monkeypatch.setattr(
            active_gate2_manifest, "_git_commit_message", lambda revision: message
        )
        return matches_clean(state)

    first_base, first_subject, first_tree = identities[0]
    last_tree = identities[-1][2]
    assert _recognized(first_base, first_subject, first_tree, first_subject)
    assert not _recognized(first_base, first_subject, last_tree, first_subject)
    assert not _recognized(first_base, first_subject, "d" * 40, first_subject)
    assert not _recognized(
        first_base,
        first_subject,
        last_tree,
        f"{first_subject}\n\n{trailer}: {last_tree}",
    )
    assert not _recognized(first_base, identities[1][1], first_tree, first_subject)
    newest_tree = "e" * 40
    assert _recognized(
        newest[0], newest[1], newest_tree, f"{newest[1]}\n\n{trailer}: {newest_tree}"
    )
    assert not _recognized(newest[0], newest[1], newest_tree, newest[1])
    assert not _recognized(
        newest[0], newest[1], newest_tree, f"{newest[1]}\n\n{trailer}: {first_tree}"
    )
    assert not _recognized("f" * 40, newest[1], newest_tree, newest[1])


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
    subprocess.run(["git", "add", "-A"], cwd=source, check=True)
    subprocess.run(
        ["git", "-c", "user.name=T", "-c", "user.email=t@x", "commit", "-q", "-m", "b"],
        cwd=source,
        check=True,
    )
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


def test_each_projection_declares_its_own_integration_event_environment(
    tmp_path: Path,
) -> None:
    leaked = {
        "GITHUB_EVENT_NAME": "pull_request",
        "GITHUB_HEAD_REF": "leaked/head",
        "GITHUB_BASE_REF": "leaked/base",
        "GITHUB_REF": "refs/pull/9999/merge",
        "GITHUB_SHA": "9" * 40,
        "PATH": "/usr/bin",
    }
    seen: dict[str, dict[str, str]] = {}
    for fixture in topology.build_all(tmp_path / "all"):
        environment = topology.projection_environment(fixture.expectation, leaked)
        seen[fixture.kind] = environment
        assert environment["PATH"] == "/usr/bin"
        if fixture.expectation.event_name == topology.EVENT_LOCAL:
            for name in topology.CI_EVENT_VARIABLES:
                assert name not in environment, (fixture.kind, name)
            continue
        assert environment["GITHUB_EVENT_NAME"] == fixture.expectation.event_name
        assert environment["GITHUB_SHA"] == fixture.expectation.head
        if fixture.expectation.event_name == topology.EVENT_PULL_REQUEST:
            assert environment["GITHUB_HEAD_REF"] == fixture.expectation.event_head_ref
    push = seen[topology.TOPOLOGY_MAIN_PUSH]
    assert push["GITHUB_REF"] == f"refs/heads/{topology.MAIN_BRANCH}"
    # A push event exposes neither pull-request reference.
    assert "GITHUB_BASE_REF" not in push
    assert "GITHUB_HEAD_REF" not in push
    for kind in (
        topology.TOPOLOGY_PULL_REQUEST_MERGE,
        topology.TOPOLOGY_SHALLOW_PULL_REQUEST,
    ):
        assert seen[kind]["GITHUB_REF"] == topology.PULL_REQUEST_MERGE_REF
        assert seen[kind]["GITHUB_BASE_REF"] == topology.MAIN_BRANCH


def test_pull_request_projections_carry_an_isolated_event_payload(
    tmp_path: Path,
) -> None:
    leaked = tmp_path / "host-event.json"
    leaked.write_text("{}", encoding="utf-8")
    for kind in (
        topology.TOPOLOGY_PULL_REQUEST_MERGE,
        topology.TOPOLOGY_SHALLOW_PULL_REQUEST,
    ):
        fixture = topology.build_topology(kind, tmp_path / kind)
        assert fixture.event_path is not None, kind
        assert fixture.root not in fixture.event_path.parents, kind
        payload = json.loads(fixture.event_path.read_text("utf-8"))
        request = payload["pull_request"]
        assert request["base"]["sha"] == fixture.refs["base"], kind
        assert request["head"]["sha"] == fixture.refs["topic"], kind
        assert request["base"]["ref"] == topology.MAIN_BRANCH, kind
        assert request["head"]["ref"] == topology.TOPIC_BRANCH, kind
        reported = topology.run_in_projection(
            fixture,
            [
                "python3",
                "-c",
                "import json, os; print(json.dumps(os.environ.get('GITHUB_EVENT_PATH')))",
            ],
        )
        assert json.loads(reported.stdout) == str(fixture.event_path), kind
        assert "GITHUB_EVENT_PATH" in topology.CI_EVENT_VARIABLES
        assert "GITHUB_EVENT_PATH" not in topology.projection_environment(
            fixture.expectation, {"GITHUB_EVENT_PATH": str(leaked)}
        ), kind


def test_source_projection_refuses_a_staged_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=source, check=True)
    (source / "kept.py").write_text("kept\n", encoding="utf-8")
    _commit_source(source, "first")
    (source / "kept.py").write_text("staged\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=source, check=True)
    with pytest.raises(topology.TopologyError):
        topology.source_dirty_paths(source)
    with pytest.raises(topology.TopologyError):
        topology.build_topology(
            topology.TOPOLOGY_CLEAN_TOPIC, tmp_path / "clean", source=source
        )


def test_projection_commands_run_under_the_projection_event(tmp_path: Path) -> None:
    fixture = topology.build_topology(topology.TOPOLOGY_MAIN_PUSH, tmp_path / "push")
    result = topology.run_in_projection(
        fixture,
        [
            "python3",
            "-c",
            "import json, os; print(json.dumps({k: os.environ.get(k) "
            "for k in ('GITHUB_EVENT_NAME', 'GITHUB_REF', 'GITHUB_SHA', "
            "'GITHUB_HEAD_REF')}))",
        ],
    )
    assert result.returncode == 0
    reported = json.loads(result.stdout)
    assert reported["GITHUB_EVENT_NAME"] == topology.EVENT_PUSH
    assert reported["GITHUB_REF"] == f"refs/heads/{topology.MAIN_BRANCH}"
    assert reported["GITHUB_SHA"] == fixture.observation.head
    assert reported["GITHUB_HEAD_REF"] is None


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
