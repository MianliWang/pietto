"""Release-note fragments and the release scripts.

Each slice writes its notes as docs/release-notes.d/<phase>-<slice>-<topic>.md;
the release commit assembles them into docs/release-notes.md (see
docs/development.md, Lean Gate v3). scripts/release_notes.py checks and
assembles them, and both commands run on a temporary copy. The release commit
also uses scripts/release_prep.py, and scripts/publish_release.py tags and
publishes it; their tests below are their self-tests.
"""

from __future__ import annotations

import base64
import contextlib
import functools
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import urllib.request
import warnings
import zipfile
from pathlib import Path
from typing import NamedTuple
from unittest import mock

import pytest

from scripts import publish_release, release_notes, release_prep

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
    assert f"`[Inline](../language.md#literal)`\n\n{FENCE}markdown\n" in notes
    assert "[Fence](../execution.md#literal)" in notes


# Forty code spans in one link text: a backtracking matcher takes hours on them.
KEYS = " ".join(f"`k{index}`" for index in range(40))


# Link text and code spans may run over the lines of one paragraph, but never
# out of it: a blank line or a new block ends the paragraph, as in CommonMark.
@pytest.mark.parametrize(
    ("link", "relocated"),
    [
        (
            "[the `../language.md` page](../language.md)",
            "[the `../language.md` page](language.md)",
        ),
        (
            "[the ``a`b`` page](../language.md)",
            "[the ``a`b`` page](language.md)",
        ),
        ("[the `a\nb` page](../language.md)", "[the `a\nb` page](language.md)"),
        ("[language\n  page](../language.md)", "[language\n  page](language.md)"),
        ('[x](../language.md\n"t")', '[x](language.md\n"t")'),
        ("`a\n[x](../language.md)`", "`a\n[x](../language.md)`"),
        (
            "``now()` x`` and\n[x](../language.md) `b`",
            "``now()` x`` and\n[x](language.md) `b`",
        ),
        ("``a [x](../language.md) `b`", "``a [x](language.md) `b`"),
        ("`a``b` [x](../language.md) `c`", "`a``b` [x](language.md) `c`"),
        ("`a\n\n[x](../language.md) `b`", "`a\n\n[x](language.md) `b`"),
        ("`a\n- [x](../language.md) `b`", "`a\n- [x](language.md) `b`"),
        ("`a\n1. [x](../language.md) `b`", "`a\n1. [x](language.md) `b`"),
        ("`a\n#### [x](../language.md) `b`", "`a\n#### [x](language.md) `b`"),
        ("`a\n> [x](../language.md) `b`", "`a\n> [x](language.md) `b`"),
        ("[x](../language.md\n\nnot a title)", "[x](../language.md\n\nnot a title)"),
        ("`a\n  - [x](../language.md) `b`", "`a\n  - [x](language.md) `b`"),
        ("`a\n2. [x](../language.md) `b`", "`a\n2. [x](../language.md) `b`"),
        (
            "`a\n- b `c\n2. [x](../language.md) `d`",
            "`a\n- b `c\n2. [x](language.md) `d`",
        ),
        (
            "`a\n- b\n\n  c `d\n2. [x](../language.md) `e`",
            "`a\n- b\n\n  c `d\n2. [x](language.md) `e`",
        ),
        (
            "`a\n#### b `c\n[x](../language.md) `d`",
            "`a\n#### b `c\n[x](language.md) `d`",
        ),
        ("`a\n***\n[x](../language.md) `b`", "`a\n***\n[x](language.md) `b`"),
        ("`a\n---\n[x](../language.md) `b`", "`a\n---\n[x](language.md) `b`"),
        ("`a\n===\n[x](../language.md) `b`", "`a\n===\n[x](language.md) `b`"),
        (
            "[`a`] b [x](../language.md) `c` [y](../language.md#z)",
            "[`a`] b [x](language.md) `c` [y](language.md#z)",
        ),
        (
            "[a `b` [x] `c](../language.md)` [y](../language.md)",
            "[a `b` [x] `c](../language.md)` [y](language.md)",
        ),
        (f"[{KEYS}] [x](../language.md)", f"[{KEYS}] [x](language.md)"),
        (
            f"`a\n{FENCE}\n[x](../language.md)\n{FENCE}\n[y](../language.md) `b`",
            f"`a\n{FENCE}\n[x](../language.md)\n{FENCE}\n[y](language.md) `b`",
        ),
        (
            "~~~\n`a\n~~~\n[x](../language.md) `b`",
            "~~~\n`a\n~~~\n[x](language.md) `b`",
        ),
        (
            f"1. `a\n   {FENCE}\n   b\n   {FENCE}\n   [x](../language.md) `c`",
            f"1. `a\n   {FENCE}\n   b\n   {FENCE}\n   [x](language.md) `c`",
        ),
        ("`a\n**\n[x](../language.md) `b`", "`a\n**\n[x](../language.md) `b`"),
        ("`a\n1) [x](../language.md) `b`", "`a\n1) [x](language.md) `b`"),
        ("`a\n#x\n[x](../language.md) `b`", "`a\n#x\n[x](../language.md) `b`"),
        ("[a] b](../language.md)", "[a] b](../language.md)"),
        (
            '[a](../language.md "[t](../language.md)")',
            '[a](language.md "[t](../language.md)")',
        ),
        ("[a](`x`)", "[a](release-notes.d/`x`)"),
        ("[a](`../language.md` b)", "[a](`../language.md` b)"),
        ("[a](../language.md `b)` c", "[a](../language.md `b)` c"),
    ],
    ids=[
        "inline-code",
        "inline-code-with-backtick",
        "inline-code-across-lines",
        "across-lines",
        "title-across-lines",
        "code-across-lines",
        "after-code-with-backtick",
        "after-unclosed-run",
        "after-code-with-run",
        "after-blank-line",
        "after-list-item",
        "after-ordered-item",
        "after-heading",
        "after-quote",
        "title-after-blank-line",
        "after-indented-item",
        "ordered-item-not-numbered-1",
        "after-next-item",
        "after-next-item-of-a-paragraph-in-a-list",
        "after-heading-line",
        "after-thematic-break",
        "after-setext-dashes",
        "after-setext-equals",
        "after-bracketed-code",
        "code-holding-link-syntax",
        "forty-code-spans",
        "after-fence",
        "after-tilde-fence",
        "after-indented-fence",
        "after-two-stars",
        "after-ordered-item-with-parenthesis",
        "after-hash-without-space",
        "bracket-before-link-text",
        "title-holding-link-syntax",
        "code-in-target",
        "unquoted-title",
        "title-into-code",
    ],
)
def test_assemble_relocates_links_whose_text_holds_code_or_spans_lines(
    tmp_path: Path, link: str, relocated: str
) -> None:
    root = _tree(tmp_path, {"76-s01-links.md": f"### Links\n\nSee {link}.\n"})

    assert (
        release_notes.assemble(root, "0.1.11", "New public alpha release notes") == []
    )
    notes = (root / "docs/release-notes.md").read_text(encoding="utf-8")
    assert f"See {relocated}.\n" in notes


@pytest.mark.parametrize(
    "link",
    [
        "[Unreleased](release-notes.d/76-s01-a.md)",
        "[`76-s01` notes](release-notes.d/76-s01-a.md)",
        "[Unreleased\nnotes](release-notes.d/76-s01-a.md)",
        "``now()` x`` and\n[Unreleased](release-notes.d/76-s01-a.md) `y`",
        "| `x |\n| [Unreleased](release-notes.d/76-s01-a.md) `y` |",
        "[`a`] b [Unreleased](release-notes.d/76-s01-a.md) `c` [y](other.md)",
        "a \\`b\n[Unreleased](release-notes.d/76-s01-a.md) `c`",
        "a `b\n<!-- c -->\n[Unreleased](release-notes.d/76-s01-a.md) `d`",
    ],
    ids=[
        "plain",
        "inline-code",
        "across-lines",
        "after-code-with-backtick",
        "after-table-row",
        "after-bracketed-code",
        "after-escaped-backtick",
        "after-html-line",
    ],
)
def test_assemble_requires_documentation_to_migrate_fragment_links(
    tmp_path: Path, link: str
) -> None:
    root = _tree(tmp_path, {"76-s01-a.md": "### A\n"})
    (root / "docs/capabilities.md").write_text(f"{link}\n", encoding="utf-8")

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


# The release scripts. publish_release.py --execute runs here only against
# fakes of git, preflight, HTTP and uv, or up to one of its refusals; no test
# reads a credential or opens a network connection.

PUBLISH = REPO_ROOT / "scripts/publish_release.py"
COMMIT = "1" * 40
# Every 4-character window of each fake token's secret part holds an upper-case
# letter, so none can occur by chance in the script's own messages, paths,
# digests or the servers' URLs. The last two have the real public prefixes,
# split so that no secret scanner reads a token in this file.
GH, PYPI = "Qz7Xw3Vk9Pl2Mn8Rt4Yb6Cd", "Jd6Hs0Gq5Fa1Ec9Wu3Ox7Lk"
PAT = "github_pat" + (
    "_D0rY1mT2hO3cJ4xE5sZ6nU_F2tA3oV4jQ5eL6zG7uB8pW9kR0fM1aH2vC3qX4lS5gN6bI7wD8rY9mT0hO1"
)
PYPI_REAL = "pypi" + "-L8zG9uB0pW1kR2fM3aH4vC5qX6lS7gN8bI9wD0rY"
GH_VARIABLE, PYPI_VARIABLE = publish_release.TOKEN_VARIABLES
CRLF = {GH_VARIABLE: f"{GH}\r\n", PYPI_VARIABLE: f" {PYPI}\r\n"}
REAL = {GH_VARIABLE: f"{PAT}\n", PYPI_VARIABLE: f"{PYPI_REAL}\n"}
SDIST = {"pietto-7.8.9.tar.gz": b"s"}
ASSETS = {
    **SDIST,
    "SHA256SUMS": f"{hashlib.sha256(b's').hexdigest()}  pietto-7.8.9.tar.gz\n".encode(),
}
ECHO_UV = (1, "Uploading pietto-7.8.9.tar.gz\n", f"error: token ending {PYPI[-7:]}\n")
QUIET_UV = (1, "Uploading pietto-7.8.9.tar.gz\n", "error: rejected\n")


def _fragments(*tokens: str) -> set[str]:
    """Every 4-character window of each token that is not wholly inside its public prefix."""
    windows: set[str] = set()
    for token in tokens:
        start = max(
            (
                len(p) - 3
                for p in publish_release.PUBLIC_PREFIXES
                if token.startswith(p)
            ),
            default=0,
        )
        windows |= {token[i : i + 4] for i in range(start, len(token) - 3)}
    return windows


FRAGMENTS, REAL_FRAGMENTS = _fragments(GH, PYPI), _fragments(PAT, PYPI_REAL)


class _Run(NamedTuple):
    code: int
    output: str  # stdout, stderr and every file written
    calls: list[tuple[str, ...]]
    tokens: list[str | None]  # the token of each HTTP request
    uv_runs: list[tuple[list[str], dict[str, str], dict[str, str]]]
    inherited: list[str]  # the steps that ran while a token variable was set


def _github(
    url,
    token=None,
    method="GET",
    body=None,
    content_type=None,
    run_id: object = 7,  # a test may make it echo the token
    html_url="https://github.com/r",
):
    """GitHub and PyPI that accept every step before `uv publish`."""
    if "/actions/runs?" in url:
        runs = [
            {
                "id": run_id,
                "path": ".github/workflows/ci.yml",
                "run_attempt": 1,
                "status": "completed",
                "conclusion": "success",
            }
        ]
        return 200, json.dumps({"workflow_runs": runs}).encode()
    if url.endswith("/jobs?per_page=100"):
        return 200, json.dumps(
            {"total_count": 21, "jobs": [{"conclusion": "success"}] * 21}
        ).encode()
    if method == "POST":
        return 201, json.dumps(
            {"upload_url": "https://uploads.github.com/u{?name}", "id": 9}
        ).encode()
    if method == "PATCH":
        listed = [
            {"name": name, "browser_download_url": f"https://github.com/d/{name}"}
            for name in ASSETS
        ]
        return 200, json.dumps({"html_url": html_url, "assets": listed}).encode()
    if url.startswith("https://github.com/d/"):
        return 200, ASSETS[url.rsplit("/", 1)[1]]
    return 404, b"{}"


def _raising(url, token=None, *rest, **keywords):
    # http.client's message for a bad header quotes the header, token included.
    raise ValueError(f"Invalid header value b'Bearer {token}\\r'")


def _echoing(url, token=None, *rest, **keywords):
    return 401, f'{{"message": "Bad credentials", "sent": "{token}"}}'.encode()


def _forbidden(url, token=None, *rest, **keywords):
    return 403, (
        b'{"message": "Resource not accessible by personal access token", '
        b'"documentation_url": "https://docs.github.com/rest/actions"}'
    )


def _answering(body: bytes):
    return lambda *arguments, **keywords: (401, body)


def _quoting_preflight(*arguments):
    raise publish_release.Stop(f"git show: fatal: path {GH} does not exist")


def _crashing_preflight(*arguments):
    # Not a Stop: a malformed archive or pyproject.toml raises before the network.
    raise KeyError(f"pietto-7.8.9.dist-info/{GH}")


def _run(
    work: Path,
    environ: dict[str, str],
    http,
    *,
    uv: str | None = "/fake/bin/uv",
    uv_output: tuple[int, str, str] = ECHO_UV,
    preflight=None,
    execute: bool = True,
) -> _Run:
    """main(--execute, or a dry run) with fakes of git, preflight, HTTP and uv."""
    calls: list[tuple[str, ...]] = []
    tokens: list[str | None] = []
    uv_runs: list[tuple[list[str], dict[str, str], dict[str, str]]] = []
    inherited: list[str] = []

    def note_environment(step: str) -> None:
        if set(publish_release.TOKEN_VARIABLES) & os.environ.keys():
            inherited.append(step)

    def fake_git(repo, *args, binary=False):
        calls.append(("git", *args))
        note_environment(f"git {args[0]}")
        if args[0] == "rev-parse":
            return f"{COMMIT}\n"
        if args[0] == "ls-remote":
            return f"{COMMIT}\t{args[-1] if args[-1].endswith('^{}') else 'refs/heads/main'}\n"
        if args[0] == "for-each-ref":
            return f"{publish_release.NAME} <{publish_release.EMAIL}>\n"
        if args[0] in ("-c", "push"):  # tag -a, and its push
            return ""
        raise AssertionError(f"unexpected git {args}")

    def fake_preflight(*arguments):
        note_environment("preflight")
        return "T — 7.8.9", SDIST, []

    def recorded_http(
        url, token=None, method="GET", body=None, content_type="application/json"
    ):
        calls.append(("http", method, url))
        tokens.append(token)
        return http(url, token, method, body, content_type)

    def fake_uv(command, env, **keywords):
        uv_runs.append((command, env, dict(os.environ)))
        return subprocess.CompletedProcess(command, *uv_output)

    # A CI marker in this process's environment would stop every --execute run first.
    kept = {
        k: v for k, v in os.environ.items() if k not in publish_release.CI_VARIABLES
    }
    captured = io.StringIO()
    with (
        mock.patch.dict(os.environ, {**kept, **environ}, clear=True),
        mock.patch.object(publish_release, "git", fake_git),
        mock.patch.object(publish_release, "http", recorded_http),
        mock.patch.object(publish_release, "preflight", preflight or fake_preflight),
        mock.patch.object(publish_release.shutil, "which", {"uv": uv}.get),
        mock.patch.object(publish_release.subprocess, "run", fake_uv),
        contextlib.redirect_stdout(captured),
        contextlib.redirect_stderr(captured),
    ):
        code = publish_release.main(
            [
                "--repo",
                str(work),
                "--commit",
                "HEAD",
                "--tree",
                "2" * 40,
                "--version",
                "7.8.9",
                "--dist-dir",
                str(work),
                "--out",
                str(work / "sums"),
                "--ci-jobs",
                "21",
                *(["--execute"] if execute else []),
            ]
        )
    written = "".join(
        path.read_text(errors="replace") for path in work.rglob("*") if path.is_file()
    )
    return _Run(code, captured.getvalue() + written, calls, tokens, uv_runs, inherited)


def _check(run: _Run, *expected: str, secret: set[str] = FRAGMENTS) -> None:
    leaked = sorted(fragment for fragment in secret if fragment in run.output)
    assert run.code == 1, run.output
    assert not leaked, ("token fragments in the output", len(leaked))
    assert not run.inherited, (
        "a token variable was in the environment during",
        run.inherited,
    )
    for text in expected:
        assert text in run.output, (text, run.output)


def test_publish_release_fake_tokens_cannot_occur_by_chance() -> None:
    assert all(
        any(c.isupper() for c in window) for window in FRAGMENTS | REAL_FRAGMENTS
    )


def test_publish_release_strips_the_tokens_and_hides_an_exception_message(
    tmp_path: Path,
) -> None:
    run = _run(tmp_path, CRLF, _raising)

    _check(run, "STOP ValueError (message not printed)")
    assert run.tokens == [GH], "the token reached http unstripped"


@pytest.mark.parametrize(
    ("environ", "http", "options", "expected", "secret"),
    [
        pytest.param(
            CRLF,
            _echoing,
            {},
            ("<withheld:",),
            FRAGMENTS,
            id="a stop message that quotes the token",
        ),
        pytest.param(
            CRLF,
            _echoing,
            {"preflight": _quoting_preflight},
            ("STOP <withheld:",),
            FRAGMENTS,
            id="a preflight stop that quotes the token",
        ),
        pytest.param(
            CRLF,
            _echoing,
            {"preflight": _crashing_preflight},
            ("STOP KeyError (message not printed)",),
            FRAGMENTS,
            id="a preflight exception that quotes the token",
        ),
        # A 500-byte cut before shown() left 7 characters of the token here.
        pytest.param(
            CRLF,
            _answering(b"x" * 493 + GH.encode() + b'"}'),
            {},
            ("<withheld:",),
            FRAGMENTS,
            id="an HTTP body that echoes the token from byte 493",
        ),
        pytest.param(
            CRLF,
            _answering(b'{"m": "' + GH[5:9].encode() + b'"}'),
            {},
            ("<withheld:",),
            FRAGMENTS,
            id="an HTTP body with exactly 4 characters of the token",
        ),
        pytest.param(
            CRLF,
            functools.partial(_github, run_id=f"7{GH}"),
            {"uv_output": QUIET_UV},
            ("<withheld:", "STOP uv publish exited 1"),
            FRAGMENTS,
            id="a CI run id that echoes the token",
        ),
        pytest.param(
            CRLF,
            functools.partial(_github, html_url=f"https://github.com/r/{GH}"),
            {"uv_output": QUIET_UV},
            ("<withheld:", "STOP uv publish exited 1"),
            FRAGMENTS,
            id="a release html_url that echoes the token",
        ),
        pytest.param(
            REAL,
            _forbidden,
            {},
            ("STOP HTTP 403", "docs.github.com"),
            REAL_FRAGMENTS,
            id="github_pat_ token, a 403 that links docs.github.com",
        ),
        pytest.param(
            REAL,
            _echoing,
            {},
            ("<withheld:",),
            REAL_FRAGMENTS,
            id="github_pat_ token, a stop message that quotes it",
        ),
        pytest.param(
            REAL,
            _answering(b'{"m": "' + PAT[10:14].encode() + b'"}'),
            {},
            ("<withheld:",),
            REAL_FRAGMENTS,
            id="github_pat_ token, 4 characters across its public prefix",
        ),
        pytest.param(
            REAL,
            _github,
            {
                "uv_output": (
                    1,
                    "Uploading pietto-7.8.9.tar.gz to https://upload.pypi.org/legacy/\n",
                    "error: 403 Forbidden\n",
                )
            },
            (
                "https://upload.pypi.org/legacy/",
                "GitHub pre-release https://github.com/r",
                "STOP uv publish exited 1",
            ),
            REAL_FRAGMENTS,
            id="pypi- token, uv output that names upload.pypi.org",
        ),
    ],
)
def test_publish_release_execute_never_prints_a_token(
    tmp_path: Path, environ, http, options, expected: tuple[str, ...], secret: set[str]
) -> None:
    _check(_run(tmp_path, environ, http, **options), *expected, secret=secret)


def test_publish_release_gives_uv_only_its_token_and_the_pypi_upload_url(
    tmp_path: Path,
) -> None:
    run = _run(tmp_path, CRLF, _github)

    _check(run, "<withheld:", "STOP uv publish exited 1")
    ((command, env, environ),) = run.uv_runs
    assert command[0] == "/fake/bin/uv" and env["UV_PUBLISH_TOKEN"] == PYPI, (
        "uv or its token"
    )
    assert (
        command[command.index("--publish-url") + 1] == "https://upload.pypi.org/legacy/"
    ), command
    assert not set(publish_release.TOKEN_VARIABLES) & (env.keys() | environ.keys())


@pytest.mark.parametrize(
    ("environ", "options", "message", "calls"),
    [
        pytest.param(
            {**CRLF, GH_VARIABLE: f"{GH[:9]}\r{GH[9:]}"},
            {},
            "STOP PIETTO_RELEASE_GH_TOKEN is unset or not a token",
            [],
            id="a CR inside a token",
        ),
        pytest.param(
            {GH_VARIABLE: GH, PYPI_VARIABLE: ""},
            {},
            "STOP PIETTO_PYPI_TOKEN is unset or not a token",
            [],
            id="an empty token",
        ),
        pytest.param(
            {**CRLF, "CI": "true"},
            {},
            "STOP --execute is refused where CI or GITHUB_ACTIONS is set",
            [],
            id="CI",
        ),
        pytest.param(
            {**CRLF, "GITHUB_ACTIONS": "true"},
            {},
            "STOP --execute is refused where CI or GITHUB_ACTIONS is set",
            [],
            id="GitHub Actions",
        ),
        pytest.param(
            CRLF,
            {"uv": None},
            "STOP uv not found on PATH",
            [("git", "rev-parse", "HEAD^{commit}")],
            id="no uv on PATH",
        ),
    ],
)
def test_publish_release_execute_stops_before_any_action(
    tmp_path: Path,
    environ: dict[str, str],
    options,
    message: str,
    calls: list[tuple[str, ...]],
) -> None:
    run = _run(tmp_path, environ, _github, **options)

    _check(run, message)
    assert run.calls == calls


def test_publish_release_dry_run_keeps_a_preflight_traceback(tmp_path: Path) -> None:
    # A dry run reads no token, so an exception keeps its traceback.
    with pytest.raises(KeyError):
        _run(tmp_path, {}, _github, preflight=_crashing_preflight, execute=False)


class _Response(io.BytesIO):
    status = 200


@pytest.mark.parametrize(
    ("url", "authorized"),
    [
        ("https://api.github.com/repos/x", True),
        ("https://uploads.github.com/u?name=a", True),
        ("https://evil.example/?api.github.com", False),
        ("https://api.github.com.evil.example/", False),
        ("https://evil.example/uploads.github.com/", False),
        ("http://api.github.com/repos/x", False),
        ("http://uploads.github.com/u?name=a", False),
    ],
)
def test_publish_release_sends_the_github_token_only_to_github(
    url: str, authorized: bool
) -> None:
    requests: list[urllib.request.Request] = []

    def urlopen(request: urllib.request.Request, timeout: float) -> _Response:
        requests.append(request)
        return _Response(b"{}")

    with mock.patch.object(publish_release.urllib.request, "urlopen", urlopen):
        publish_release.http(url, GH)

    (request,) = requests
    if authorized:
        assert request.unredirected_hdrs == {"Authorization": f"Bearer {GH}"}
        assert "Authorization" not in request.headers
    else:
        assert not request.has_header("Authorization")


# A commit that publish_release.py binds archives to, and archives in uv_build's shape.
BLOBS = {
    "pyproject.toml": b'[project]\nname = "pietto"\nversion = "7.8.9"\nreadme = "README.md"\n'
    b'license-files = ["LICENSE"]\nkeywords = ["sql", "dsl"]\ndependencies = ["a==1"]\n\n'
    b'[project.optional-dependencies]\nx = ["b==2", "a==1"]\n\n'
    b'[project.scripts]\npietto = "pietto.cli:main"\n',
    "README.md": b"r\n",
    "LICENSE": b"l\n",
    "src/pietto/cli.py": b'_FALLBACK_VERSION = "7.8.9"\n',
}
INFO = "pietto-7.8.9.dist-info/"
LICENSE = f"{INFO}licenses/LICENSE"
ENTRY_POINTS = b"[console_scripts]\npietto = pietto.cli:main\n\n"
TAGS = b"Wheel-Version: 1.0\nGenerator: uv 0.13.8\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
HEAD = b"Metadata-Version: 2.4\nName: pietto\nVersion: 7.8.9\nRequires-Dist: a==1\n"
EXTRA_X = b"Requires-Dist: b==2 ; extra == 'x'\nRequires-Dist: a==1 ; extra == 'x'\nProvides-Extra: x\n"
METADATA = (
    HEAD + EXTRA_X + b"\n" + BLOBS["README.md"]
)  # headers, a blank line, README.md


def _show(path: str) -> bytes:
    path = path.removeprefix(
        "./"
    )  # git reads rev:./path from the work tree's root, as -C repo sets it
    if path not in BLOBS:
        raise publish_release.Stop(f"no {path}")
    return BLOBS[path]


def _wheel(
    *extra: tuple[str, bytes],
    without: str = "",
    metadata: bytes = METADATA,
    license: bytes = BLOBS["LICENSE"],
    entry_points: bytes = ENTRY_POINTS,
    wheel_file: bytes = TAGS,
    record: bytes | None = None,
) -> bytes:
    """uv_build's shape; its RECORD lists each file member as written, unless record replaces it."""
    members = [
        ("pietto/", b""),
        ("pietto/cli.py", BLOBS["src/pietto/cli.py"]),
        (f"{INFO}METADATA", metadata),
        (f"{INFO}entry_points.txt", entry_points),
        (f"{INFO}WHEEL", wheel_file),
        (LICENSE, license),
        *extra,
    ]
    members = [(name, content) for name, content in members if name != without]

    def digest(content: bytes) -> str:
        return (
            base64.urlsafe_b64encode(hashlib.sha256(content).digest())
            .rstrip(b"=")
            .decode()
        )

    written = "".join(
        f"{name},sha256={digest(content)},{len(content)}\n"
        for name, content in members
        if not name.endswith("/")
    )
    buffer = io.BytesIO()
    # A duplicate name warns.
    with (
        warnings.catch_warnings(action="ignore"),
        zipfile.ZipFile(buffer, "w") as archive,
    ):
        for name, content in [
            *members,
            (f"{INFO}RECORD", record or f"{written}{INFO}RECORD,,\n".encode()),
        ]:
            archive.writestr(name, content)
    return buffer.getvalue()


def _member(
    name: str, kind: bytes = tarfile.REGTYPE, target: str = ""
) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.type, info.linkname = kind, target
    info.size = len(BLOBS["README.md"]) if kind == tarfile.REGTYPE else 0
    return info


def _sdist(
    changes: dict[str, bytes | None] | None = None, *extra: tarfile.TarInfo
) -> bytes:
    """uv_build's shape: directory entries, PKG-INFO, a reformatted pyproject.toml and its .orig."""
    files = {
        "PKG-INFO": METADATA,
        "pyproject.toml": b'[project]\nname = "pietto"\nversion = "7.8.9"\nreadme = "README.md"\n'
        b'license-files = [\n    "LICENSE",\n]\nkeywords = [\n    "sql",\n    "dsl",\n]\n'
        b'dependencies = [\n    "a==1",\n]\n\n[project.optional-dependencies]\nx = [\n    "b==2",\n    "a==1",\n]\n\n'
        b'[project.scripts]\npietto = "pietto.cli:main"\n',
        "pyproject.toml.orig": BLOBS["pyproject.toml"],
        "README.md": BLOBS["README.md"],
        "LICENSE": BLOBS["LICENSE"],
        "src/pietto/cli.py": BLOBS["src/pietto/cli.py"],
    } | (changes or {})
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for directory in (
            "pietto-7.8.9",
            "pietto-7.8.9/src",
            "pietto-7.8.9/src/pietto",
        ):
            archive.addfile(_member(directory, tarfile.DIRTYPE))
        for path, content in files.items():
            if content is not None:
                info = tarfile.TarInfo(f"pietto-7.8.9/{path}")
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))
        for info in extra:
            archive.addfile(
                info, io.BytesIO(BLOBS["README.md"]) if info.isfile() else None
            )
    return buffer.getvalue()


ORIG = [
    "sdist pyproject.toml.orig is missing or differs from the commit's pyproject.toml"
]
LACKS = ["sdist lacks src/pietto/cli.py"]
CLI = "pietto-7.8.9/src/pietto/cli.py"
BINDING_CASES = [
    ("uv_build's shape", _wheel(), _sdist(), []),
    (
        "an .orig that is not the commit's pyproject.toml",
        _wheel(),
        _sdist({"pyproject.toml.orig": b"other"}),
        ORIG,
    ),
    ("no .orig", _wheel(), _sdist({"pyproject.toml.orig": None}), ORIG),
    (
        "a file outside the commit",
        _wheel(),
        _sdist({"notes.txt": b"n"}),
        ["sdist notes.txt differs from the commit"],
    ),
    (
        "an sdist without a tracked file",
        _wheel(),
        _sdist({"src/pietto/cli.py": None}),
        LACKS,
    ),
    (
        "a wheel without a tracked file",
        _wheel(without="pietto/cli.py"),
        _sdist(),
        [
            "wheel directory member pietto/ has content or no file member under it",
            "wheel lacks src/pietto/cli.py",
        ],
    ),
    (
        "a symlink in place of a source file",
        _wheel(),
        _sdist(
            {"src/pietto/cli.py": None}, _member(CLI, tarfile.SYMTYPE, "/etc/passwd")
        ),
        [f"sdist member {CLI} is not a regular file or directory", *LACKS],
    ),
    (
        "a hard link in place of a source file",
        _wheel(),
        _sdist(
            {"src/pietto/cli.py": None},
            _member(CLI, tarfile.LNKTYPE, "pietto-7.8.9/pyproject.toml"),
        ),
        [f"sdist member {CLI} is not a regular file or directory", *LACKS],
    ),
    (
        "an extra symlink",
        _wheel(),
        _sdist(
            {}, _member("pietto-7.8.9/src/pietto/evil.py", tarfile.SYMTYPE, "../../x")
        ),
        [
            "sdist member pietto-7.8.9/src/pietto/evil.py is not a regular file or directory"
        ],
    ),
    (
        "a pyproject.toml with another build backend",
        _wheel(),
        _sdist({"pyproject.toml": b'[build-system]\nrequires = ["evil"]\n'}),
        ["sdist pyproject.toml does not parse to the commit's pyproject.toml"],
    ),
    (
        "no rewritten pyproject.toml",
        _wheel(),
        _sdist({"pyproject.toml": None}),
        ["sdist lacks pyproject.toml"],
    ),
    (
        "a commit file outside pietto-7.8.9/",
        _wheel(),
        _sdist({}, _member("README.md")),
        ["sdist member README.md is outside pietto-7.8.9/"],
    ),
    (
        "an unknown dist-info member",
        _wheel(("pietto-7.8.9.dist-info/evil.pth", b"import os\n")),
        _sdist(),
        [
            "wheel member pietto-7.8.9.dist-info/evil.pth is neither under pietto/ nor a known dist-info member"
        ],
    ),
    (
        "a second entry_points.txt",
        _wheel(
            (
                "pietto-7.8.9.dist-info/entry_points.txt",
                b"[console_scripts]\nx = os:system\n",
            )
        ),
        _sdist(),
        [
            "wheel has duplicate members",
            "wheel entry_points.txt differs from the commit's pyproject.toml scripts",
            "wheel RECORD does not list each file member's sha256 and size",
        ],
    ),
    (
        "a wheel description from another README",
        _wheel(metadata=HEAD + EXTRA_X + b"\nother\n"),
        _sdist(),
        ["wheel METADATA description is not the commit's README.md"],
    ),
    (
        "a PKG-INFO description from another README",
        _wheel(),
        _sdist({"PKG-INFO": HEAD + EXTRA_X + b"\nother\n"}),
        ["sdist PKG-INFO description is not the commit's README.md"],
    ),
    (
        "a wheel with another Requires-Dist",
        _wheel(metadata=HEAD + b"Requires-Dist: evil==1\n" + EXTRA_X + b"\nr\n"),
        _sdist(),
        ["wheel METADATA Requires-Dist differs from the commit's pyproject.toml"],
    ),
    (
        "a wheel without one extra's Requires-Dist",
        _wheel(
            metadata=HEAD
            + EXTRA_X.replace(b"Requires-Dist: a==1 ; extra == 'x'\n", b"")
            + b"\nr\n"
        ),
        _sdist(),
        ["wheel METADATA Requires-Dist differs from the commit's pyproject.toml"],
    ),
    (
        "a wheel without its Provides-Extra",
        _wheel(metadata=HEAD + EXTRA_X.replace(b"Provides-Extra: x\n", b"") + b"\nr\n"),
        _sdist(),
        ["wheel METADATA Provides-Extra differs from the commit's pyproject.toml"],
    ),
    # The sdist once had to hold only src/pietto, PKG-INFO and pyproject.toml.
    (
        "an sdist without the readme",
        _wheel(),
        _sdist({"README.md": None}),
        ["sdist lacks README.md"],
    ),
    (
        "an sdist without a license file",
        _wheel(),
        _sdist({"LICENSE": None}),
        ["sdist lacks LICENSE"],
    ),
    (
        "a wheel without a license file",
        _wheel(without=LICENSE),
        _sdist(),
        [f"wheel lacks {LICENSE}"],
    ),
    (
        "a wheel license file that is not the commit's",
        _wheel(license=b"other\n"),
        _sdist(),
        [f"wheel {LICENSE} differs from the commit"],
    ),
    # A ./ member is a second name for a commit file (git show reads rev:./x as x).
    (
        "an sdist member named through ./",
        _wheel(),
        _sdist({}, _member("pietto-7.8.9/./README.md")),
        ["sdist member pietto-7.8.9/./README.md has an empty, . or .. path component"],
    ),
    (
        "a wheel member named through ./",
        _wheel(("pietto/./cli.py", BLOBS["src/pietto/cli.py"])),
        _sdist(),
        ["wheel member pietto/./cli.py has an empty, . or .. path component"],
    ),
    (
        "a wheel member named through ..",
        _wheel(("pietto/../cli.py", BLOBS["src/pietto/cli.py"])),
        _sdist(),
        ["wheel member pietto/../cli.py has an empty, . or .. path component"],
    ),
    (
        "an sdist member with an empty path component",
        _wheel(),
        _sdist({}, _member("pietto-7.8.9/src//pietto/cli.py")),
        [
            "sdist member pietto-7.8.9/src//pietto/cli.py has an empty, . or .. path component"
        ],
    ),
    # odd() drops a trailing / and the content check skips directory members.
    (
        "a wheel directory member with content",
        _wheel(("pietto/cli.py/", b"x = 2\n")),
        _sdist(),
        [
            "wheel directory member pietto/cli.py/ has content or no file member under it"
        ],
    ),
    (
        "an empty wheel directory member without a file under it",
        _wheel(("pietto/b/", b"")),
        _sdist(),
        ["wheel directory member pietto/b/ has content or no file member under it"],
    ),
    # The generated dist-info members were allowed by name only.
    (
        "an extra console script",
        _wheel(
            entry_points=ENTRY_POINTS.replace(b"\n\n", b"\npip = pietto.cli:main\n\n")
        ),
        _sdist(),
        ["wheel entry_points.txt differs from the commit's pyproject.toml scripts"],
    ),
    (
        "a wheel tagged for one platform",
        _wheel(wheel_file=TAGS.replace(b"py3-none-any", b"py3-none-linux_x86_64")),
        _sdist(),
        ["wheel WHEEL is not Root-Is-Purelib: true with the one Tag py3-none-any"],
    ),
    (
        "a wheel that is not purelib",
        _wheel(wheel_file=TAGS.replace(b": true", b": false")),
        _sdist(),
        ["wheel WHEEL is not Root-Is-Purelib: true with the one Tag py3-none-any"],
    ),
    (
        "a RECORD that is not the members'",
        _wheel(record=f"pietto/cli.py,sha256=x,6\n{INFO}RECORD,,\n".encode()),
        _sdist(),
        ["wheel RECORD does not list each file member's sha256 and size"],
    ),
]


@pytest.mark.parametrize(
    ("wheel", "sdist", "expected"),
    [
        pytest.param(wheel, sdist, expected, id=name)
        for name, wheel, sdist, expected in BINDING_CASES
    ],
)
def test_publish_release_binds_both_archives_to_the_commit(
    wheel: bytes, sdist: bytes, expected: list[str]
) -> None:
    assert (
        publish_release.binding_problems(
            _show, wheel, sdist, "7.8.9", ["src/pietto/cli.py"]
        )
        == expected
    )


# The preflight's git grep -E patterns, read here by Python re: these are the same in both dialects.
FILL, PLACEHOLDER, MAIN_LINK, PLANNED = publish_release.STALE


@pytest.mark.parametrize(
    ("pattern", "hits", "misses"),
    [
        (
            FILL,
            ("- LEAD: add each", "[x](#ANCHOR)", "  REHEARSAL-PLACEHOLDER state S06's"),
            ("the lead: x", "#anchor", "REHEARSAL"),
        ),
        (
            PLACEHOLDER,
            (
                "<BATCH-HEAD>",
                "<D76.12-RULING>",
                "<INT1-AD78.02-ROW>",
                "<P79-S06-RESULT>",
                "x <PL-0200-ROW>.",
            ),
            # Angle-bracket words that the documents hold.
            ("<PHASE>", "<N>", "<NA>", "<KIND>", "<a-b>", "<B->"),
        ),
        (
            MAIN_LINK,
            ("https://github.com/MianliWang/pietto/tree/main/docs",),
            ("https://github.com/MianliWang/pietto/blob/v7.8.9/docs/x.md",),
        ),
        (
            PLANNED,
            (
                "Construction state: PLANNED. S02 lands",
                "qualification. Until S04 lands the route, a compiled",
            ),
            ("Construction state: IMPLEMENTED", "Until S04 landed the route"),
        ),
    ],
)
def test_publish_release_stale_text_patterns(
    pattern: str, hits: tuple[str, ...], misses: tuple[str, ...]
) -> None:
    assert all(re.search(pattern, text) for text in hits)
    assert not any(re.search(pattern, text) for text in misses)


def test_publish_release_preflight_finds_no_stale_text_in_this_tree() -> None:
    # Between releases only README's links to main match; `release_prep.py bump` pins them.
    hits = [
        f"{path.relative_to(REPO_ROOT)}:{number} matches {pattern}"
        for pattern, roots in publish_release.STALE.items()
        if pattern != MAIN_LINK
        for root in roots
        for path in [REPO_ROOT / root, *sorted((REPO_ROOT / root).rglob("*"))]
        if path.is_file()
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if re.search(pattern, line)
    ]
    assert hits == []


def _environment(**extra: str) -> dict[str, str]:
    """This environment without tokens, CI markers, GIT_ variables or the user's git configuration."""
    skip = {*publish_release.TOKEN_VARIABLES, *publish_release.CI_VARIABLES}
    kept = {
        k: v
        for k, v in os.environ.items()
        if k not in skip and not k.startswith("GIT_")
    }
    return {
        **kept,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        **extra,
    }


def _release_ready(
    tmp_path: Path, extra: dict[str, bytes] | None = None
) -> tuple[Path, str, str, Path]:
    """A repository whose HEAD is release 7.8.9, its commit and tree, and the release's dist directory."""
    repo, dist = tmp_path / "repo", tmp_path / "dist"
    files = {
        **BLOBS,
        "docs/release-notes.md": "# Notes\n\n## Title — 7.8.9\n".encode(),
        "docs/release-notes.d/README.md": b"# Fragments\n",
        **(extra or {}),
    }
    for path, content in files.items():
        (repo / path).parent.mkdir(parents=True, exist_ok=True)
        (repo / path).write_bytes(content)
    identity = (
        "-c",
        f"user.name={publish_release.NAME}",
        "-c",
        f"user.email={publish_release.EMAIL}",
    )
    for command in (
        ("init", "-q"),
        ("add", "-A"),
        (*identity, "commit", "-q", "-m", "Release 7.8.9"),
    ):
        subprocess.run(
            ("git", "-C", str(repo), *command), env=_environment(), check=True
        )
    commit, tree = subprocess.run(
        ("git", "-C", str(repo), "rev-parse", "HEAD", "HEAD^{tree}"),
        env=_environment(),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    dist.mkdir()
    (dist / "pietto-7.8.9-py3-none-any.whl").write_bytes(_wheel())
    (dist / "pietto-7.8.9.tar.gz").write_bytes(_sdist())
    return repo, commit, tree, dist


def _publish(
    tmp_path: Path, repo: Path, tree: str, dist: Path, *options: str, **environment: str
):
    """scripts/publish_release.py as the release checklist runs it."""
    arguments = (
        "--repo",
        repo,
        "--commit",
        "HEAD",
        "--tree",
        tree,
        "--version",
        "7.8.9",
        "--dist-dir",
        dist,
        "--out",
        tmp_path / "sums",
        "--ci-jobs",
        "30",
        *options,
    )
    return subprocess.run(
        (sys.executable, "-I", "-B", str(PUBLISH), *map(str, arguments)),
        env=_environment(**environment),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_publish_release_dry_run_of_a_release_ready_commit(tmp_path: Path) -> None:
    repo, commit, tree, dist = _release_ready(tmp_path)

    result = _publish(tmp_path, repo, tree, dist)

    names = ("pietto-7.8.9-py3-none-any.whl", "pietto-7.8.9.tar.gz")
    sums = "".join(
        f"{hashlib.sha256((dist / name).read_bytes()).hexdigest()}  {name}\n"
        for name in names
    )
    assert (result.returncode, result.stderr) == (0, "")
    assert (tmp_path / "sums/SHA256SUMS").read_text(encoding="utf-8") == sums
    assert result.stdout.startswith(
        f"DRY RUN: pietto 7.8.9 from {commit} (Gate 2 tree {tree})\n"
    )
    assert "blob/v7.8.9/docs/release-notes.md#title--789" in result.stdout
    assert result.stdout.endswith(
        "comparator self-check passed; no credential read, no network used\n"
    )


def test_publish_release_dry_run_reports_each_preflight_problem(tmp_path: Path) -> None:
    repo, commit, tree, dist = _release_ready(
        tmp_path,
        {
            "docs/x.md": b"- LEAD: fill\n",
            "docs/release-notes.d/81-p14-x.md": b"### X\n",
        },
    )

    result = _publish(tmp_path, repo, "2" * 40, dist)

    assert result.returncode == 1
    assert result.stderr.splitlines() == [
        f"PREFLIGHT the tree of {commit[:12]} is {tree}, not the Gate 2 tree {'2' * 40}",
        "PREFLIGHT fragments not assembled: ['81-p14-x.md']",
        "PREFLIGHT docs/x.md:1:- LEAD: fill matches LEAD:|#ANCHOR|REHEARSAL-PLACEHOLDER",
    ]
    assert (tmp_path / "sums/SHA256SUMS").is_file()


def test_publish_release_refuses_execute_in_ci_before_any_action(
    tmp_path: Path,
) -> None:
    repo, _, tree, dist = _release_ready(tmp_path)

    result = _publish(tmp_path, repo, tree, dist, "--execute", CI="true")

    assert (result.returncode, result.stdout) == (1, "")
    assert (
        result.stderr
        == "STOP --execute is refused where CI or GITHUB_ACTIONS is set; nothing was done\n"
    )
    assert not (tmp_path / "sums").exists()


@pytest.mark.parametrize(
    ("text", "targets"),
    [
        (
            "see [`Float` statistics](77-s05.md) and [plain](a.md#x)",
            ["77-s05.md", "a.md#x"],
        ),
        ("code `[x](inside.md)` then [y](out.md)", ["out.md"]),
        ("![img](pic.png) [t](<sp ace.md>)", ["sp ace.md"]),
        ('```\n[f](fenced.md)\n```\n[`a` `b`](z.md "title")', ["z.md"]),
        (
            "the [language\n  page](../language.md) and [`a\nb` c](d.md)",
            ["../language.md", "d.md"],
        ),
        ("[two\n\nparagraphs](no.md) `code\nspan [x](in.md)` [y](\n", []),
    ],
)
def test_release_prep_link_grammar(text: str, targets: list[str]) -> None:
    assert release_prep.links(release_notes, text) == targets


def test_release_prep_bump_writes_nothing_while_one_version_owner_is_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    texts: dict[str, str] = {}
    for path, pattern, _ in (*release_prep.EXACT, *release_prep.EVERY):
        texts[path] = texts.get(path, "") + pattern.format(o="7.8.8") + "\n"
    texts["README.md"] = texts["README.md"].replace(
        "**Version 7.8.8, public alpha.**\n", ""
    )
    for path, text in texts.items():
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text(text, encoding="utf-8")

    assert release_prep.bump(tmp_path, "7.8.8", "7.8.9") == 1
    assert capsys.readouterr().err == (
        "PROBLEM README.md: '**Version 7.8.8, public alpha.**' occurs 0 times, expected 1\nnothing written\n"
    )
    assert {
        path: (tmp_path / path).read_text(encoding="utf-8") for path in texts
    } == texts


def test_release_prep_fill_refuses_a_part_that_holds_the_preflight_placeholder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _tree(tmp_path, {})
    draft = tmp_path / "draft.md"
    draft.write_text(
        "<!-- BEGIN head -->\n- LEAD: the status\n<!-- END head -->\n<!-- BEGIN tail -->\nTail.\n<!-- END tail -->\n",
        encoding="utf-8",
    )

    assert release_prep.fill(root, draft, "0.1.10") == 1
    assert (
        capsys.readouterr().err
        == "PROBLEM the draft's head part still holds a LEAD: placeholder\n"
    )
    assert (root / "docs/release-notes.md").read_text(encoding="utf-8") == NOTES
