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


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _first_heading(document: str) -> str:
    match = re.match(r"^# ([^\n]+)\n", document)
    assert match is not None
    return match.group(1)


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
