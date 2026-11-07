"""Check and assemble the release-note fragments of docs/release-notes.d.

``check``: every fragment is named ``<phase>-<slice>-<topic>.md``, starts with
a ``###`` heading, has no ``#`` or ``##`` heading, ends with one newline,
writes every diagnostic code with its ``PIE-`` prefix and every ``pietto``
block as ``pietto fmt`` writes it.

``assemble --version X --title T``: puts ``## T — X`` and the fragments,
ordered by phase, slice and topic, above the previous release in
docs/release-notes.md, then deletes the fragments.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
import os
import re
import sys
import tempfile
from pathlib import Path

from pietto.source_format import format_source

REPO_ROOT = Path(__file__).resolve().parents[1]
FRAGMENTS = Path("docs/release-notes.d")
NOTES = Path("docs/release-notes.md")
NAME = re.compile(r"(\d+)-([a-z]\d{2})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md")
VERSION = re.compile(r"\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?")
HEADING = re.compile(r"(#+) ")
BARE_CODE = re.compile(r"(?<!PIE-)\b[PSIB][0-9]{4}\b")
BLOCK = re.compile(r"^```pietto([^\n]*)\n(.*?)^```$", re.MULTILINE | re.DOTALL)
LINK = re.compile(
    r"(?<!!)\[[^\]\n]+\]\((?P<target><[^>\n]+>|[^\s)\n]+)(?P<tail>\s+[^)\n]+)?\)"
)


def fragments(root: Path) -> list[Path]:
    """The well-named fragments, in assembly order."""
    named = (
        (match, path)
        for path in (root / FRAGMENTS).glob("*.md")
        if (match := NAME.fullmatch(path.name)) is not None
    )
    ordered = sorted(named, key=lambda item: (int(item[0][1]), item[0][2], item[0][3]))
    return [path for _, path in ordered]


def check(root: Path) -> list[str]:
    """Every problem of every fragment, by file name."""
    problems: list[str] = []
    for path in sorted((root / FRAGMENTS).glob("*")):
        if path.name == "README.md":
            continue
        if NAME.fullmatch(path.name) is None or not path.is_file():
            problems.append(f"{path.name}: not named <phase>-<slice>-<topic>.md")
            continue
        text = path.read_text(encoding="utf-8")
        problems.extend(f"{path.name}: {problem}" for problem in _problems(text))
    return problems


def _problems(text: str) -> list[str]:
    problems: list[str] = []
    if not text.startswith("### "):
        problems.append("does not start with a ### heading")
    if not text.endswith("\n") or text.endswith("\n\n"):
        problems.append("does not end with exactly one newline")
    fenced = False
    for number, line in enumerate(text.splitlines(), 1):
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and (heading := HEADING.match(line)) and len(heading[1]) < 3:
            problems.append(f"line {number}: a {heading[1]} heading")
    problems.extend(f"bare diagnostic code {m[0]}" for m in BARE_CODE.finditer(text))
    blocks = list(BLOCK.finditer(text))
    if len(blocks) != text.count("```pietto"):
        problems.append("a ```pietto fence is not closed")
    for block in blocks:
        if format_source(block[2]).source != block[2]:
            line = text.count("\n", 0, block.start()) + 1
            problems.append(f"line {line}: the pietto block is not formatted")
    return problems


def _rewrite_links_outside_code(
    text: str, rewrite: Callable[[re.Match[str]], str]
) -> str:
    """Rewrite Markdown links, leaving fenced and inline code literal."""
    fenced = False
    lines: list[str] = []
    for line in text.splitlines(keepends=True):
        if line.startswith("```"):
            fenced = not fenced
            lines.append(line)
            continue
        if fenced:
            lines.append(line)
            continue
        pieces = line.split("`")
        for index in range(0, len(pieces), 2):
            pieces[index] = LINK.sub(rewrite, pieces[index])
        lines.append("`".join(pieces))
    return "".join(lines)


def _link_target(match: re.Match[str]) -> str:
    target = match["target"]
    return target[1:-1] if target.startswith("<") else target


def _relocate_fragment_links(path: Path, notes_path: Path) -> str:
    """Keep a fragment's local Markdown links valid after it moves to notes."""

    def relocate(match: re.Match[str]) -> str:
        target = _link_target(match)
        location, separator, anchor = target.partition("#")
        if not location or location.startswith(("/", "http:", "https:", "mailto:")):
            return match[0]
        destination = (path.parent / location).resolve()
        relative = os.path.relpath(destination, notes_path.parent.resolve()).replace(
            os.sep, "/"
        )
        suffix = f"#{anchor}" if separator else ""
        return match[0].replace(match["target"], relative + suffix, 1)

    return _rewrite_links_outside_code(path.read_text(encoding="utf-8"), relocate)


def _fragment_link_problems(root: Path, paths: list[Path]) -> list[str]:
    """Reject documentation links that disappear when assembled fragments do."""
    fragment_paths = {path.resolve() for path in paths}
    problems: list[str] = []
    documents = [root / "README.md", *sorted((root / "docs").rglob("*.md"))]
    for document in documents:
        if not document.is_file():
            continue
        if document.resolve() in fragment_paths:
            continue

        def reject(match: re.Match[str]) -> str:
            target = _link_target(match)
            location = target.split("#", 1)[0]
            if location and (document.parent / location).resolve() in fragment_paths:
                problems.append(
                    f"{document.relative_to(root)}: link to a release-note fragment "
                    "must be migrated to the assembled release-notes.md section"
                )
            return match[0]

        _rewrite_links_outside_code(document.read_text(encoding="utf-8"), reject)
    return problems


def assemble(root: Path, version: str, title: str) -> list[str]:
    """Write the release section or leave notes unchanged and recover fragments."""
    problems = check(root)
    paths = fragments(root)
    notes_path = root / NOTES
    notes = notes_path.read_text(encoding="utf-8")
    if not paths:
        problems.append("no fragments to assemble")
    if VERSION.fullmatch(version) is None:
        problems.append(f"version {version!r} is not X.Y.Z")
    if not title or title != " ".join(title.split()):
        problems.append(f"title {title!r} is not one trimmed line")
    if re.search(rf"^## .* — {re.escape(version)}$", notes, re.MULTILINE):
        problems.append(f"{NOTES} already has a {version} section")
    problems.extend(_fragment_link_problems(root, paths))
    if problems:
        return problems
    section = f"## {title} — {version}\n\n" + "\n".join(
        _relocate_fragment_links(path, notes_path) for path in paths
    )
    top, found, rest = notes.partition("\n## ")
    if found:
        notes = f"{top}\n{section}\n## {rest}"
    else:
        notes = notes.rstrip("\n") + "\n\n" + section
    temporary_notes: str | None = None
    staging: Path | None = None
    moved: list[tuple[Path, Path]] = []
    try:
        temporary_notes = _write_temporary(notes_path, notes)
        try:
            staging = Path(
                tempfile.mkdtemp(
                    prefix=".release-notes-fragments-", dir=notes_path.parent
                )
            )
        except OSError as error:
            return [f"could not stage release-note fragments: {error}"]
        for path in paths:
            staged = staging / path.name
            try:
                os.replace(path, staged)
            except OSError as error:
                return _failed_assembly(
                    f"could not remove {path}: {error}", moved, staging
                )
            moved.append((path, staged))
        try:
            os.replace(temporary_notes, notes_path)
        except OSError as error:
            return _failed_assembly(
                f"could not update {NOTES}: {error}", moved, staging
            )
    finally:
        if temporary_notes is not None:
            Path(temporary_notes).unlink(missing_ok=True)
    try:
        for _, staged in moved:
            staged.unlink()
        staging.rmdir()
    except OSError:
        # The release section is already durable and fragments are no longer visible.
        pass
    return []


def _write_temporary(path: Path, text: str) -> str:
    """Write replacement bytes beside their target for an atomic rename."""
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(text)
    return temporary


def _failed_assembly(
    problem: str, moved: list[tuple[Path, Path]], staging: Path
) -> list[str]:
    """Restore each moved fragment, retaining any irrecoverable bytes in staging."""
    problems = [problem]
    for path, staged in reversed(moved):
        try:
            os.replace(staged, path)
        except OSError as error:
            problems.append(
                f"could not restore {path}; original bytes remain recoverable at {staged}: {error}"
            )
    if len(problems) == 1:
        try:
            staging.rmdir()
        except OSError as error:
            problems.append(
                f"could not remove empty fragment staging directory {staging}: {error}"
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Release-note fragments.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="check every fragment")
    assembly = commands.add_parser("assemble", help="write the release section")
    assembly.add_argument("--version", required=True)
    assembly.add_argument("--title", required=True)
    args = parser.parse_args(argv)
    count = len(fragments(args.root))
    if args.command == "check":
        problems = check(args.root)
    else:
        problems = assemble(args.root, args.version, args.title)
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 1
    done = "assembled into docs/release-notes.md" if args.command != "check" else "ok"
    print(f"{count} fragment(s) {done}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
