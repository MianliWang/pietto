"""Release-note fragments: scripts/release_notes.py checks and assembles them.

Each slice writes its notes as docs/release-notes.d/<phase>-<slice>-<topic>.md;
the release commit assembles them into docs/release-notes.md (see
docs/development.md, Lean Gate v3). Both commands run on a temporary copy.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from scripts import release_notes

REPO_ROOT = Path(__file__).resolve().parents[1]
# Built so that the bare-code law does not read this file as one.
BARE = "S" + "2333"
FENCE = "`" * 3
NOTES = (
    "# Pietto release notes\n"
    "\n"
    "## Earlier public alpha release notes — 0.1.10\n"
    "\n"
    "### Earlier\n"
    "\n"
    "- Earlier.\n"
)


def _tree(tmp_path: Path, fragments: dict[str, str]) -> Path:
    (tmp_path / "docs/release-notes.d").mkdir(parents=True)
    (tmp_path / "docs/release-notes.md").write_text(NOTES, encoding="utf-8")
    for name, text in {"README.md": "# Fragments\n", **fragments}.items():
        (tmp_path / "docs/release-notes.d" / name).write_text(text, encoding="utf-8")
    return tmp_path


def _names(root: Path) -> list[str]:
    return sorted(path.name for path in (root / "docs/release-notes.d").iterdir())


def test_the_repository_fragments_pass_the_check() -> None:
    assert release_notes.check(REPO_ROOT) == []


def test_check_reports_every_malformed_fragment(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _tree(
        tmp_path,
        {
            "76-s01-good.md": (
                "### Good\n\n"
                f"{FENCE}bash\n# a comment, not a heading\n{FENCE}\n\n"
                f"{FENCE}pietto\nshape User:\n    id: Int\n{FENCE}\n\n"
                "#### Detail\n\n- PIE-S2333 stays.\n"
            ),
            "notes.md": "### Misnamed\n",
            "76-s02-levels.md": "### A\n\n## B\n\n# C\n",
            "76-s03-start.md": "Text first.\n",
            "76-s04-code.md": f"### Code\n\n- {BARE} is refused.\n",
            "76-s05-format.md": f"### Format\n\n{FENCE}pietto\nshape User:\n  id: Int\n{FENCE}\n",
            "76-s06-newline.md": "### Newline\n\n- One.\n\n",
            "76-s07-fence.md": f"### Fence\n\n{FENCE}pietto\nshape User:\n",
        },
    )

    assert release_notes.main(["--root", str(root), "check"]) == 1
    assert capsys.readouterr().err.splitlines() == [
        "76-s02-levels.md: line 3: a ## heading",
        "76-s02-levels.md: line 5: a # heading",
        "76-s03-start.md: does not start with a ### heading",
        f"76-s04-code.md: bare diagnostic code {BARE}",
        "76-s05-format.md: line 3: the pietto block is not formatted",
        "76-s06-newline.md: does not end with exactly one newline",
        "76-s07-fence.md: a ```pietto fence is not closed",
        "notes.md: not named <phase>-<slice>-<topic>.md",
    ]
    for path in (root / "docs/release-notes.d").iterdir():
        if path.name not in {"README.md", "76-s01-good.md"}:
            path.unlink()
    assert release_notes.main(["--root", str(root), "check"]) == 0
    assert capsys.readouterr().out == "1 fragment(s) ok\n"


def test_assemble_writes_one_section_in_order_and_deletes_the_fragments(
    tmp_path: Path,
) -> None:
    root = _tree(
        tmp_path,
        {
            "100-s01-later.md": "### Phase100\n\n- Later.\n",
            "76-s10-tenth.md": "### Tenth\n\n- Ten.\n",
            "76-s02-zeta.md": "### Zeta\n\n- Z.\n",
            "76-s02-alpha.md": "### Alpha\n\n- A.\n\n#### Detail\n\n- D.\n",
        },
    )
    argv = ["--root", str(root), "assemble", "--version", "0.1.11"]

    assert release_notes.main([*argv, "--title", "New public alpha release notes"]) == 0
    assert (root / "docs/release-notes.md").read_text(encoding="utf-8") == (
        "# Pietto release notes\n"
        "\n"
        "## New public alpha release notes — 0.1.11\n"
        "\n"
        "### Alpha\n\n- A.\n\n#### Detail\n\n- D.\n"
        "\n"
        "### Zeta\n\n- Z.\n"
        "\n"
        "### Tenth\n\n- Ten.\n"
        "\n"
        "### Phase100\n\n- Later.\n"
        "\n"
        "## Earlier public alpha release notes — 0.1.10\n"
        "\n"
        "### Earlier\n"
        "\n"
        "- Earlier.\n"
    )
    assert _names(root) == ["README.md"]


def test_assemble_relocates_fragment_links_without_touching_code_literals(
    tmp_path: Path,
) -> None:
    root = _tree(
        tmp_path,
        {
            "76-s01-links.md": (
                "### Links\n\n"
                "[Float values](../language.md#float-values)\n"
                "[Results](../execution.md#results)\n"
                "[Capabilities](../capabilities.md)\n\n"
                "[Self](#links) [Pietto](https://example.test/pietto)\n\n"
                "`[Inline](../language.md#literal)`\n\n"
                f"{FENCE}markdown\n[Fence](../execution.md#literal)\n{FENCE}\n"
            )
        },
    )

    assert (
        release_notes.assemble(root, "0.1.11", "New public alpha release notes") == []
    )
    notes = (root / "docs/release-notes.md").read_text(encoding="utf-8")
    assert "[Float values](language.md#float-values)" in notes
    assert "[Results](execution.md#results)" in notes
    assert "[Capabilities](capabilities.md)" in notes
    assert "[Self](#links) [Pietto](https://example.test/pietto)" in notes
    assert "`[Inline](../language.md#literal)`" in notes
    assert "[Fence](../execution.md#literal)" in notes


def test_assemble_requires_documentation_to_migrate_fragment_links(
    tmp_path: Path,
) -> None:
    root = _tree(tmp_path, {"76-s01-a.md": "### A\n"})
    (root / "docs/capabilities.md").write_text(
        "[Unreleased](release-notes.d/76-s01-a.md)\n", encoding="utf-8"
    )

    problems = release_notes.assemble(root, "0.1.11", "New public alpha release notes")

    assert problems == [
        "docs/capabilities.md: link to a release-note fragment must be migrated to the "
        "assembled release-notes.md section"
    ]
    assert (root / "docs/release-notes.md").read_text(encoding="utf-8") == NOTES
    assert _names(root) == ["76-s01-a.md", "README.md"]


def test_assemble_requires_the_root_readme_to_migrate_fragment_links(
    tmp_path: Path,
) -> None:
    root = _tree(tmp_path, {"76-s01-a.md": "### A\n"})
    (root / "README.md").write_text(
        "[Unreleased](docs/release-notes.d/76-s01-a.md)\n", encoding="utf-8"
    )

    problems = release_notes.assemble(root, "0.1.11", "New public alpha release notes")

    assert problems == [
        "README.md: link to a release-note fragment must be migrated to the "
        "assembled release-notes.md section"
    ]
    assert (root / "docs/release-notes.md").read_text(encoding="utf-8") == NOTES
    assert _names(root) == ["76-s01-a.md", "README.md"]


@pytest.mark.parametrize(
    ("fragments", "version", "title", "problem"),
    [
        ({}, "0.1.11", "New", "no fragments to assemble"),
        ({"76-s01-a.md": "### A\n"}, "0.1.10", "New", "already has a 0.1.10 section"),
        ({"76-s01-a.md": "### A\n"}, "next", "New", "version 'next' is not X.Y.Z"),
        ({"76-s01-a.md": "### A\n"}, "0.1.11", " New", "is not one trimmed line"),
        ({"76-s01-a.md": "### A\n\n## B\n"}, "0.1.11", "New", "line 3: a ## heading"),
    ],
)
def test_assemble_refuses_and_changes_nothing(
    tmp_path: Path, fragments: dict[str, str], version: str, title: str, problem: str
) -> None:
    root = _tree(tmp_path, fragments)
    names = _names(root)

    problems = release_notes.assemble(root, version, title)

    assert len(problems) == 1 and problem in problems[0], problems
    assert (root / "docs/release-notes.md").read_text(encoding="utf-8") == NOTES
    assert _names(root) == names


def test_assemble_rolls_back_when_a_fragment_cannot_be_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _tree(
        tmp_path,
        {
            "76-s01-first.md": "### First\n\n- First.\n",
            "76-s02-second.md": "### Second\n\n- Second.\n",
        },
    )
    original_replace = os.replace

    def fail_second(source: str | Path, target: str | Path) -> None:
        if Path(source).name == "76-s02-second.md":
            raise OSError("cannot remove fragment")
        original_replace(source, target)

    monkeypatch.setattr(release_notes.os, "replace", fail_second)

    problems = release_notes.assemble(root, "0.1.11", "New public alpha release notes")

    assert problems == [
        "could not remove "
        + str(root / "docs/release-notes.d/76-s02-second.md")
        + ": cannot remove fragment"
    ]
    assert (root / "docs/release-notes.md").read_text(encoding="utf-8") == NOTES
    assert _names(root) == ["76-s01-first.md", "76-s02-second.md", "README.md"]
    assert not list((root / "docs").glob(".release-notes-*"))


def test_assemble_removes_its_temporary_notes_if_staging_cannot_be_created(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _tree(tmp_path, {"76-s01-a.md": "### A\n"})

    def fail_staging(**_: object) -> str:
        raise OSError("cannot stage fragments")

    monkeypatch.setattr(release_notes.tempfile, "mkdtemp", fail_staging)

    assert release_notes.assemble(root, "0.1.11", "New public alpha release notes") == [
        "could not stage release-note fragments: cannot stage fragments"
    ]
    assert (root / "docs/release-notes.md").read_text(encoding="utf-8") == NOTES
    assert _names(root) == ["76-s01-a.md", "README.md"]
    assert not list((root / "docs").glob(".release-notes.md-*"))


def test_assemble_restores_fragments_if_replacing_notes_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _tree(tmp_path, {"76-s01-a.md": "### A\n"})
    original_replace = os.replace

    def fail_notes_replace(source: str | Path, target: str | Path) -> None:
        if Path(source).name.startswith(".release-notes.md-"):
            raise OSError("cannot replace notes")
        original_replace(source, target)

    monkeypatch.setattr(release_notes.os, "replace", fail_notes_replace)

    assert release_notes.assemble(root, "0.1.11", "New public alpha release notes") == [
        "could not update docs/release-notes.md: cannot replace notes"
    ]
    assert (root / "docs/release-notes.md").read_text(encoding="utf-8") == NOTES
    assert _names(root) == ["76-s01-a.md", "README.md"]
    assert not list((root / "docs").glob(".release-notes-*"))


def test_assemble_reports_the_recovery_path_when_rollback_cannot_restore_a_fragment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _tree(
        tmp_path,
        {
            "76-s01-first.md": "### First\n\n- First.\n",
            "76-s02-second.md": "### Second\n\n- Second.\n",
        },
    )
    original_replace = os.replace

    def fail_move_and_restore(source: str | Path, target: str | Path) -> None:
        source_path = Path(source)
        if source_path.name == "76-s02-second.md":
            raise OSError("cannot remove fragment")
        if source_path.name == "76-s01-first.md" and source_path.parent.name.startswith(
            ".release-notes-fragments-"
        ):
            raise OSError("cannot restore fragment")
        original_replace(source, target)

    monkeypatch.setattr(release_notes.os, "replace", fail_move_and_restore)

    problems = release_notes.assemble(root, "0.1.11", "New public alpha release notes")

    recovery = next((root / "docs").glob(".release-notes-fragments-*"))
    assert problems == [
        "could not remove "
        + str(root / "docs/release-notes.d/76-s02-second.md")
        + ": cannot remove fragment",
        "could not restore "
        + str(root / "docs/release-notes.d/76-s01-first.md")
        + "; original bytes remain recoverable at "
        + str(recovery / "76-s01-first.md")
        + ": cannot restore fragment",
    ]
    assert (root / "docs/release-notes.md").read_text(encoding="utf-8") == NOTES
    assert _names(root) == ["76-s02-second.md", "README.md"]
    assert (recovery / "76-s01-first.md").read_text(
        encoding="utf-8"
    ) == "### First\n\n- First.\n"
    assert not list((root / "docs").glob(".release-notes.md-*"))
