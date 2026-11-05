from __future__ import annotations

from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS = REPO_ROOT / "AGENTS.md"
ARCHITECTURE_ROOT = REPO_ROOT / "docs/architecture"
PRODUCT_ARCHITECTURE = ARCHITECTURE_ROOT / "product-architecture-v1.md"
PHASE_INITIATION_GATE = ARCHITECTURE_ROOT / "phase-initiation-gate-v1.md"
IDENTITY_LAWS = ARCHITECTURE_ROOT / "identity-and-authority-laws-v1.md"
LAYERING_LAWS = ARCHITECTURE_ROOT / "layering-and-coupling-laws-v1.md"
PRODUCT_LESSONS = REPO_ROOT / "docs/references/product-design-lessons-v1.md"
PLAN_README = REPO_ROOT / "docs/plan/README.md"
PRODUCT_PLAN_SNAPSHOT = REPO_ROOT / "docs/plan/pietto_product_plan_2026-09-02.md"
PREREQUISITE_SPEC = (
    REPO_ROOT
    / "docs/spec/phase63-repository-architecture-authority-extraction-prerequisite-v1.md"
)
PUBLISHED_PHASE63_SPEC = (
    REPO_ROOT
    / "docs/spec/phase63-joined-query-block-product-architecture-source-audit-future-roadmap-route-lock-v1.md"
)
ARCHITECTURE_DOCUMENTS = (
    PRODUCT_ARCHITECTURE,
    PHASE_INITIATION_GATE,
    IDENTITY_LAWS,
    LAYERING_LAWS,
)
NEW_AUTHORITY_DOCUMENTS = (
    *ARCHITECTURE_DOCUMENTS,
    PRODUCT_LESSONS,
    PLAN_README,
    PRODUCT_PLAN_SNAPSHOT,
    PREREQUISITE_SPEC,
)
EXPECTED_TITLES = (
    "Pietto Product Architecture v1",
    "Product/Phase Initiation Gate v1",
    "Pietto Identity And Authority Laws v1",
    "Pietto Layering And Coupling Laws v1",
    "Pietto Product Design Lessons v1",
    "Historical Planning Material",
    "Pietto 产品规划历史快照",
    "Phase 63 Repository Architecture Authority Extraction Prerequisite v1",
)
_ROADMAP_PATH = "docs/" + "road" + "map.md"
_STATUS_PATH = "docs/" + "status" + ".md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _first_heading(document: str) -> str:
    match = re.match(r"^# ([^\n]+)\n", document)
    assert match is not None
    return match.group(1)


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


def _link_targets(document: str) -> tuple[str, ...]:
    return tuple(re.findall(r"\[[^\]]+\]\(([^)]+)\)", document))


def _relative_link_paths(path: Path) -> tuple[Path, ...]:
    targets = []
    for raw_target in _link_targets(_read(path)):
        if raw_target.startswith(("http://", "https://", "#")):
            continue
        target = raw_target.split("#", 1)[0]
        if target:
            targets.append((path.parent / target).resolve())
    return tuple(targets)


def test_authority_documents_titles_navigation_and_links_are_closed() -> None:
    assert all(path.is_file() for path in NEW_AUTHORITY_DOCUMENTS)
    titles = tuple(_first_heading(_read(path)) for path in NEW_AUTHORITY_DOCUMENTS)
    assert titles == EXPECTED_TITLES
    assert len(titles) == len(set(titles))

    agents_links = set(_link_targets(_read(AGENTS)))
    assert {
        "docs/architecture/product-architecture-v1.md",
        "docs/architecture/phase-initiation-gate-v1.md",
        "docs/architecture/identity-and-authority-laws-v1.md",
        "docs/architecture/layering-and-coupling-laws-v1.md",
        "docs/references/product-design-lessons-v1.md",
    } <= agents_links

    for path in (AGENTS, *NEW_AUTHORITY_DOCUMENTS):
        relative_targets = _relative_link_paths(path)
        assert all(target.exists() for target in relative_targets), path


def test_authority_ownership_is_explicit_and_non_competing() -> None:
    product = " ".join(_read(PRODUCT_ARCHITECTURE).split())
    prerequisite = " ".join(_read(PREREQUISITE_SPEC).split())
    for evidence in (
        "current repository entry point for durable, cross-phase",
        "phase-level future ownership and release milestones",
        "exact phase-specific routes, decisions, and publication evidence",
        "lifecycle summary subordinate to live Git and natural exact-head CI",
        "historical planning evidence only",
        "Source and tests",
    ):
        assert evidence in product
    for evidence in (
        "Authority Ownership After Extraction",
        "Authority is separated by owner",
        "current durable cross-phase",
        "never independent Pietto authority",
    ):
        assert evidence in prerequisite


def test_product_architecture_preserves_layers_boundaries_and_arrow_laws() -> None:
    product_text = _read(PRODUCT_ARCHITECTURE)
    product = " ".join(product_text.split())
    assert (
        ".pietto -> parser -> AST -> semantic authority -> Project IR / Query Block IR "
        "-> ProjectSQLPlan -> dialect SQL AST -> SQL"
    ) in product
    assert (
        "completed semantic/query authority -> PiettoResultContract -> Arrow "
        "interchange -> Python/data-science ecosystem adapters -> domain/device "
        "adapters"
    ) in product
    for boundary in (
        "semantic compiler",
        "target-independent logical/query authority",
        "target-neutral SQL planning and lowering requirements",
        "selected-backend lowering",
        "Optional execution",
        "stable result boundary",
        "explicit adapters",
        "Optimizer and physical planning",
        "DBMS",
        "transaction manager",
        "job scheduler",
        "general Python runtime",
        "remote package registry or dependency solver",
        "DML, DDL, or migration runtime",
    ):
        assert boundary in product
    for arrow_law in (
        "Arrow is typed tabular and nested interchange",
        "Arrow field name != Pietto field occurrence",
        "Arrow `List<Struct>` != Pietto `NestedRelation` semantics",
        "Arrow metadata != key, grain, or lineage authority",
        "does not define Pietto semantic identity",
        "does not define RDKit semantics",
        "arbitrary SciPy lowering",
        "database execution",
        "not the sole GPU/device interchange mechanism",
    ):
        assert arrow_law in product
    for planning_law in (
        "downstream of semantic authority",
        "upstream of, or a planning side-plane to",
        "not downstream of PiettoResultContract / Arrow or ecosystem adapters",
        "Phases 88–89 own their exact future internal topology",
        "neither implements those phases nor defines an optimizer IR",
    ):
        assert planning_law in product
    assert re.search(r"^\| Slice ", product_text, re.MULTILINE) is None


def test_historical_plan_categories_and_snapshot_are_non_authoritative() -> None:
    readme = " ".join(_read(PLAN_README).split())
    snapshot_text = _read(PRODUCT_PLAN_SNAPSHOT)
    snapshot = " ".join(
        line.removeprefix("> ").strip() for line in snapshot_text.splitlines()
    )
    for evidence in (
        "historical planning evidence",
        "older phase-planning documents",
        "dated product/roadmap snapshots",
        "not current architecture, lifecycle, phase-route, or implementation authority",
        "Neither category authorizes implementation",
        "`pietto_product_plan_2026-09-02.md`",
    ):
        assert evidence in readme
    for evidence in (
        "2026-09-02",
        "historical planning evidence",
        "不是 current implementation authorization",
        "也不是 competing roadmap",
        "Durable architecture authority",
        "current phase-level ownership",
        "exact phase/slice authority",
        "live Git + natural exact-head CI",
        "repository working authority",
    ):
        assert evidence in snapshot

    expected_targets = {
        ARCHITECTURE_ROOT.resolve(),
        (REPO_ROOT / _ROADMAP_PATH).resolve(),
        (REPO_ROOT / _STATUS_PATH).resolve(),
        (REPO_ROOT / "docs/spec").resolve(),
        AGENTS.resolve(),
    }
    assert expected_targets <= set(_relative_link_paths(PRODUCT_PLAN_SNAPSHOT))

    snapshot_route = _section(snapshot_text, "11. Phase 63 frozen 16 slices")
    published = _read(PUBLISHED_PHASE63_SPEC)
    published_route = _section(published, "Exact Phase-63 Route")
    snapshot_numbers = tuple(
        int(value) for value in re.findall(r"^(\d+)\. ", snapshot_route, re.MULTILINE)
    )
    published_numbers = tuple(
        int(value)
        for value in re.findall(r"^\| (\d+) \|", published_route, re.MULTILINE)
    )
    assert snapshot_numbers == published_numbers == tuple(range(1, 17))
    for frozen_owner in (
        "Query-block owner bridge",
        "QUALIFY",
        "Completion audit",
    ):
        assert frozen_owner in snapshot_route
        assert frozen_owner in published_route
    assert "Slice 2 = NEXT / NOT IMPLEMENTED" in snapshot

    snapshot_future = _section(snapshot_text, "7. Future Roadmap v6")
    published_future = _section(published, "Future Roadmap v6")
    for frozen_owner in (
        "Joined Query Block semantic completion and QUALIFY",
        "Target-neutral ProjectSQLPlan",
        "Arrow interchange foundation",
        "Explicit executor SPI",
        "Logical optimizer memo",
        "Profiling-driven Rust kernels",
    ):
        assert frozen_owner in snapshot_future
        assert frozen_owner in published_future
