"""Release-commit helpers for a pietto release.

Run every command, from any directory, with the python of a venv whose pietto is
ROOT's own; ROOT is the release worktree. `migrate` and `audit` import
ROOT/scripts/release_notes.py for its fragment list, NOTES, _link_target and
_fragment_link_problems only: they find and rewrite links with this file's own
single-backtick grammar (CODE_OR_LINK below), which can see other links than the
repository's. The backstops are the repository's _fragment_link_problems, which
`migrate` runs last, and the release checklist's greps.

  release_prep.py migrate ROOT VERSION      links to fragments -> release-notes.md#anchor;
                                            a fragment's link to another fragment -> #anchor;
                                            a fragment's link to release-notes.md#a -> #a
  release_prep.py bump ROOT OLD NEW         exact version-owner replacements, all or nothing;
                                            pins README's blob/main and tree/main links to vNEW
  release_prep.py fill ROOT DRAFT VERSION   insert the hand-written head and tail parts;
                                            refuses a part that holds LEAD: (the marker
                                            publish_release.py's preflight refuses)
  release_prep.py audit BEFORE AFTER        release-notes.md anchors: none missing, none moved;
                                            covers relative links and README's
                                            github.com/MianliWang/pietto/blob/<ref>/ links
                                            (a 40-hex commit ref is skipped), and reports
                                            each relative link whose file does not exist
                                            and that BEFORE did not already have (DEAD: a
                                            fragment that assembly deleted, or a link that
                                            assembly did not relocate)
  release_prep.py manifest-digest ROOT LOG [--write]
                                            join-differential common manifest digest
"""

from __future__ import annotations

from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib

ANCHOR_ID = re.compile(r'<a id="([^"]+)"')
# README links to the notes as https://github.com/MianliWang/pietto/blob/<ref>/docs/release-notes.md#...
BLOB = re.compile(r"https://github\.com/MianliWang/pietto/blob/([^/]+)/(.+)")
# This file's own link grammar, as rehearsed for 0.1.12: a code span is one backtick on
# each side, and code spans and link text may run over the lines of a paragraph, never
# over a blank line. The repository's release_notes.py follows CommonMark instead (a code
# span closes on a backtick run of its own length; a list item, quote, heading, table row
# or thematic break ends a paragraph), so the two can see different links, in both
# directions: ``now()` x`` hides later links of its paragraph here only, and
# "[a\n- b](x)" is a link here only. A link to a fragment that only the repository sees
# fails migrate's closing _fragment_link_problems call; a fragment's link to another
# fragment or to ../release-notes.md left unrewritten fails the release checklist's greps.
BREAK = r"\n(?![ \t]*\n)"  # a line break inside a paragraph
CODE_OR_LINK = re.compile(
    rf"(?P<code>`(?:[^`\n]|{BREAK})*`)"
    rf"|(?<!!)\[(?:[^\]\n`]|`(?:[^`\n]|{BREAK})*`|{BREAK})+\]"
    r"\((?P<target><[^>\n]+>|[^\s)\n]+)(?:\s+[^)\n]+)?\)"
)


def load_release_notes(root: Path):
    spec = importlib.util.spec_from_file_location(
        "release_notes_of_root", root / "scripts/release_notes.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def slug(text: str) -> str:
    """GitHub heading slug (validated in the 2026-11-12 rehearsal on 43 links)."""
    text = (
        re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text).replace("`", "").replace("*", "")
    )
    text = text.strip().lower()
    text = "".join(c for c in text if c.isalnum() or c in "_- ")
    return text.replace(" ", "-")


def headings(text: str) -> list[tuple[int, int, str]]:
    """(line, level, title) of every heading outside fenced code."""
    found = []
    fenced = False
    for number, line in enumerate(text.splitlines(), 1):
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and (match := re.match(r"(#{1,6}) (.*)", line)):
            found.append((number, len(match[1]), match[2]))
    return found


def anchors(text: str) -> dict[str, tuple[int, str]]:
    """anchor -> (line, enclosing ## title), with GitHub duplicate numbering."""
    seen: Counter[str] = Counter()
    found: dict[str, tuple[int, str]] = {}
    section = ""
    fenced = False
    for number, line in enumerate(text.splitlines(), 1):
        if line.startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        for explicit in ANCHOR_ID.findall(line):
            found[explicit] = (number, section)
        match = re.match(r"(#{1,6}) (.*)", line)
        if not match:
            continue
        if len(match[1]) == 2:
            section = match[2]
        base = slug(match[2])
        found[base if seen[base] == 0 else f"{base}-{seen[base]}"] = (number, section)
        seen[base] += 1
    return found


def rewrite_links(text: str, rewrite) -> str:
    """Rewrite Markdown links outside fenced and inline code, code in link text included."""
    fenced = False
    out: list[str] = []
    prose: list[str] = []

    def flush() -> None:
        out.append(
            CODE_OR_LINK.sub(
                lambda m: m[0] if m["code"] else rewrite(m), "".join(prose)
            )
        )
        prose.clear()

    for line in text.splitlines(keepends=True):
        if line.startswith("```"):
            if not fenced:
                flush()
            fenced = not fenced
            out.append(line)
        elif fenced:
            out.append(line)
        else:
            prose.append(line)
    flush()
    return "".join(out)


def links(rn, text: str) -> list[str]:
    """Every Markdown link target outside fenced and inline code."""
    targets: list[str] = []

    def collect(match: re.Match[str]) -> str:
        targets.append(rn._link_target(match))
        return match[0]

    rewrite_links(text, collect)
    return targets


def documents(root: Path) -> list[Path]:
    return [root / "README.md", *sorted((root / "docs").rglob("*.md"))]


def migrate(root: Path, version: str) -> int:
    rn = load_release_notes(root)
    paths = rn.fragments(root)
    if not paths:
        print("no fragments: nothing to migrate")
        return 0
    notes = (root / rn.NOTES).resolve()
    # The new section becomes the first ## of the notes, so a fragment heading's
    # duplicate number counts only the same slugs earlier in that section.
    seen: Counter[str] = Counter()
    final: dict[tuple[Path, str], str] = {}
    for path in paths:
        local: Counter[str] = Counter()
        for index, (_, _, title) in enumerate(
            headings(path.read_text(encoding="utf-8"))
        ):
            base = slug(title)
            here = base if local[base] == 0 else f"{base}-{local[base]}"
            there = base if seen[base] == 0 else f"{base}-{seen[base]}"
            local[base] += 1
            seen[base] += 1
            final[(path.resolve(), here)] = there
            if index == 0:
                final[(path.resolve(), "")] = there
    problems: list[str] = []
    fragment_set = {path.resolve() for path in paths}
    for document in documents(root):
        if not document.is_file():
            continue
        # A fragment becomes part of the notes, so its link to another fragment becomes #anchor.
        inside = document.resolve() in fragment_set
        text = document.read_text(encoding="utf-8")

        def rewrite(match: re.Match[str]) -> str:
            target = rn._link_target(match)
            location, _, anchor = target.partition("#")
            if not location:
                return match[0]
            resolved = (document.parent / location).resolve()
            if inside and anchor and resolved == notes:
                # Inside the notes #x is the plain form; the repository's assemble now also relocates
                # such a link with code in its text (0.2.0's 77-f01), but to release-notes.md#x
                print(f"{document.relative_to(root)}: {target} -> #{anchor}")
                return match[0].replace(match["target"], f"#{anchor}", 1)
            if resolved not in fragment_set:
                return match[0]
            new_anchor = final.get((resolved, anchor))
            if new_anchor is None:
                problems.append(
                    f"{document.relative_to(root)}: {target}: anchor not in fragment"
                )
                return match[0]
            relative = (
                ""
                if inside
                else os.path.relpath(notes, document.parent.resolve()).replace(
                    os.sep, "/"
                )
            )
            new = match[0].replace(match["target"], f"{relative}#{new_anchor}", 1)
            if not inside and re.match(r"\[[Uu]nreleased\]\(", new):
                new = f"[{version}](" + new[len("[Unreleased](") :]
            print(f"{document.relative_to(root)}: {target} -> {relative}#{new_anchor}")
            return new

        new_text = rewrite_links(text, rewrite)
        if new_text != text:
            document.write_text(new_text, encoding="utf-8")
            for number, line in enumerate([] if inside else new_text.splitlines(), 1):
                if "release-notes.md#" in line and re.search(
                    r"(?i)unreleased|candidate", line
                ):
                    print(
                        f"  REVIEW {document.relative_to(root)}:{number}: prose says unreleased/candidate"
                    )
    problems.extend(rn._fragment_link_problems(root, paths))
    for problem in problems:
        print(f"PROBLEM {problem}", file=sys.stderr)
    return 1 if problems else 0


# (path, old, new): each old occurs exactly once; README links: every occurrence, at least one.
EXACT = (
    ("pyproject.toml", 'version = "{o}"', 'version = "{n}"'),
    ("pyproject.toml", "/tree/v{o}/docs", "/tree/v{n}/docs"),
    ("src/pietto/cli.py", '_FALLBACK_VERSION = "{o}"', '_FALLBACK_VERSION = "{n}"'),
    ("uv.lock", 'name = "pietto"\nversion = "{o}"', 'name = "pietto"\nversion = "{n}"'),
    (
        "tests/_pietto_results_consumer.py",
        'distribution.version != "{o}"',
        'distribution.version != "{n}"',
    ),
    (
        "THIRD_PARTY_NOTICES.md",
        "For the {o} release candidate",
        "For the {n} release candidate",
    ),
    (
        "THIRD_PARTY_NOTICES.md",
        "`pietto-{o}-py3-none-any.whl` and `pietto-{o}.tar.gz`",
        "`pietto-{n}-py3-none-any.whl` and `pietto-{n}.tar.gz`",
    ),
    ("THIRD_PARTY_NOTICES.md", "`v{o}` source tar.gz", "`v{n}` source tar.gz"),
    (
        "README.md",
        "![Package version {o}](https://img.shields.io/badge/package-{o}-",
        "![Package version {n}](https://img.shields.io/badge/package-{n}-",
    ),
    ("README.md", "**Version {o}, public alpha.**", "**Version {n}, public alpha.**"),
    (
        "README.md",
        "./dist/pietto-{o}-py3-none-any.whl",
        "./dist/pietto-{n}-py3-none-any.whl",
    ),
)
# README links stay on blob/main and tree/main between releases; the release commit pins
# every one of them (0.1.11 pinned nine blob/main links by hand), the post-release docs commit
# moves them back. A README without such a link is a problem, not a silent no-op.
EVERY = (
    (
        "README.md",
        "github.com/MianliWang/pietto/blob/main/",
        "github.com/MianliWang/pietto/blob/v{n}/",
    ),
    (
        "README.md",
        "github.com/MianliWang/pietto/tree/main/",
        "github.com/MianliWang/pietto/tree/v{n}/",
    ),
)
HISTORY = (
    ":!docs/release-notes.md",
    ":!docs/decisions.md",
    ":!docs/phases",
    ":!docs/release-notes.d",
    ":!tests/test_repo_release_notes_fragments.py",
)


def bump(root: Path, old: str, new: str) -> int:
    texts: dict[str, str] = {}
    problems: list[str] = []
    for path, pattern, replacement in EXACT:
        text = texts.setdefault(path, (root / path).read_text(encoding="utf-8"))
        before, after = pattern.format(o=old), replacement.format(n=new)
        if text.count(before) != 1:
            problems.append(
                f"{path}: {before!r} occurs {text.count(before)} times, expected 1"
            )
            continue
        texts[path] = text.replace(before, after)
        print(f"{path}: 1 x {before!r}")
    for path, pattern, replacement in EVERY:
        text = texts.setdefault(path, (root / path).read_text(encoding="utf-8"))
        before, after = pattern.format(o=old), replacement.format(n=new)
        count = text.count(before)
        if count == 0:
            problems.append(f"{path}: {before!r} occurs 0 times, expected 1 or more")
            continue
        texts[path] = text.replace(before, after)
        print(f"{path}: {count} x {before!r}")
    if problems:
        for problem in problems:
            print(f"PROBLEM {problem}", file=sys.stderr)
        print("nothing written", file=sys.stderr)
        return 1
    for path, text in texts.items():
        (root / path).write_text(text, encoding="utf-8")
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["version"] == new, project["project"]["version"]
    listed = subprocess.run(
        ["git", "-C", str(root), "grep", "-n", "-F", old, "--", ".", *HISTORY],
        capture_output=True,
        text=True,
    )
    if (
        listed.returncode > 1
    ):  # 1 means no match; more means git failed, so "none" would be a lie
        print(
            f"PROBLEM written, but git grep failed: {listed.stderr.strip()}",
            file=sys.stderr,
        )
        return 1
    print(f"\nremaining {old} outside history (review each by hand):")
    print(listed.stdout or "  none")
    return 0


def fill(root: Path, draft: Path, version: str) -> int:
    source = draft.read_text(encoding="utf-8")
    parts = {}
    for name in ("head", "tail"):
        match = re.search(
            rf"^<!-- BEGIN {name} -->\n(.*?)^<!-- END {name} -->$",
            source,
            re.MULTILINE | re.DOTALL,
        )
        if match is None:
            print(f"PROBLEM draft has no {name} part", file=sys.stderr)
            return 1
        parts[name] = match[1].strip("\n") + "\n"
        if "LEAD:" in parts[name]:
            print(
                f"PROBLEM the draft's {name} part still holds a LEAD: placeholder",
                file=sys.stderr,
            )
            return 1
    notes_path = root / "docs/release-notes.md"
    notes = notes_path.read_text(encoding="utf-8")
    heads = list(
        re.finditer(rf"^## .* — {re.escape(version)}\n\n", notes, re.MULTILINE)
    )
    if len(heads) != 1:
        print(
            f"PROBLEM {len(heads)} '## ... — {version}' headings, expected 1",
            file=sys.stderr,
        )
        return 1
    start = heads[0].end()
    end = notes.find("\n## ", start) + 1
    if end == 0 or "\n### Highlights\n" in notes[start:end]:
        print(
            "PROBLEM no next ## section, or the section is already filled",
            file=sys.stderr,
        )
        return 1
    notes = (
        notes[:start]
        + parts["head"]
        + "\n"
        + notes[start:end]
        + parts["tail"]
        + "\n"
        + notes[end:]
    )
    notes_path.write_text(notes, encoding="utf-8")
    print(
        f"filled the {version} section: head {parts['head'].count(chr(10))} lines, tail {parts['tail'].count(chr(10))} lines"
    )
    return 0


def dead(rn, root: Path) -> Counter[tuple[str, str]]:
    """(document, target) of each relative link whose file does not exist."""
    found: Counter[tuple[str, str]] = Counter()
    for document in documents(root):
        if document.is_file():
            for target in links(rn, document.read_text(encoding="utf-8")):
                location = target.partition("#")[0]
                relative_file = location and not re.match(
                    r"[A-Za-z][A-Za-z0-9+.-]*:|/", location
                )
                if relative_file and not (document.parent / location).exists():
                    found[(str(document.relative_to(root)), target)] += 1
    return found


def audit(before_root: Path, after_root: Path) -> int:
    rn = load_release_notes(after_root)
    notes = (after_root / "docs/release-notes.md").resolve()
    before = anchors(
        (before_root / "docs/release-notes.md").read_text(encoding="utf-8")
    )
    after = anchors(notes.read_text(encoding="utf-8"))
    problems = checked = 0
    dead_after, dead_before = dead(rn, after_root), dead(rn, before_root)
    for (relative, target), count in sorted((dead_after - dead_before).items()):
        problems += count
        print(
            f"DEAD    {relative} {target}: no such file (a fragment that assembly deleted, "
            "or a link that assembly did not relocate)"
        )
    for relative, target in sorted(dead_after & dead_before):
        print(f"note    {relative} {target}: dead in BEFORE too, not counted")
    for document in documents(after_root):
        if not document.is_file():
            continue
        relative = document.relative_to(after_root)
        old_exists = (before_root / relative).exists()
        for target in links(rn, document.read_text(encoding="utf-8")):
            location, _, anchor = target.partition("#")
            if not anchor or (str(relative), target) in dead_after:
                continue
            if blob := BLOB.fullmatch(location):
                if re.fullmatch(r"[0-9a-f]{40}", blob[1]):
                    continue  # a link pinned to a commit reads that commit's own file
                path = (after_root / blob[2]).resolve()
            else:
                path = (
                    (document.parent / location).resolve()
                    if location
                    else document.resolve()
                )
            if path != notes:
                continue
            checked += 1
            got = after.get(anchor)
            was = before.get(anchor) if old_exists else None
            if got is None:
                problems += 1
                print(f"MISSING {relative} #{anchor}")
            elif was is not None and was[1] != got[1]:
                problems += 1
                print(
                    f"MOVED   {relative} #{anchor}: was in '{was[1]}', now in '{got[1]}'"
                )
    print(f"checked {checked} links to release-notes.md anchors; problems {problems}")
    return 1 if problems else 0


DIFFERS = re.compile(r"AssertionError: Common manifest differs in (\S+):$")
CONSTANT = re.compile(
    r'(EXPECTED_COMMON_MANIFEST_SHA256: str \| None = \(\n    ")([0-9a-f]{64})("\n\))'
)


def manifest_digest(root: Path, log: Path, write: bool) -> int:
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    for index, line in enumerate(lines):
        if (match := DIFFERS.search(line)) is not None:
            break
    else:
        print(
            "PROBLEM no 'Common manifest differs' failure in the log", file=sys.stderr
        )
        return 1
    body = []
    for line in lines[index + 1 :]:
        if not line.startswith("E"):
            break
        body.append(line[1:])
    indent = len(body[0]) - len(body[0].lstrip(" "))
    manifest, _ = json.JSONDecoder().raw_decode("\n".join(row[indent:] for row in body))
    sys.path.insert(0, str(root / "tests"))
    from _pietto_project_join_differential import _digest  # the test's own digest

    version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["version"]
    digest = _digest(manifest)
    print(
        f"cell {match[1]}: package_version {manifest['package_version']}, digest {digest}"
    )
    if manifest["package_version"] != version:
        print(
            f"PROBLEM the cell reports {manifest['package_version']}, pyproject says {version}: "
            "re-run `uv sync --locked` for this venv and run the test again",
            file=sys.stderr,
        )
        return 1
    if write:
        path = root / "tests/_pietto_project_join_differential.py"
        text = path.read_text(encoding="utf-8")
        new, count = CONSTANT.subn(rf"\g<1>{digest}\g<3>", text)
        if count != 1:
            print(
                f"PROBLEM the constant occurs {count} times, expected 1",
                file=sys.stderr,
            )
            return 1
        path.write_text(new, encoding="utf-8")
        print(f"wrote {digest} to {path.relative_to(root)}; rerun the test to confirm")
    return 0


def main(argv: list[str]) -> int:
    command, *args = argv
    if command == "migrate":
        return migrate(Path(args[0]), args[1])
    if command == "bump":
        return bump(Path(args[0]), args[1], args[2])
    if command == "fill":
        return fill(Path(args[0]), Path(args[1]), args[2])
    if command == "audit":
        return audit(Path(args[0]), Path(args[1]))
    if command == "manifest-digest":
        return manifest_digest(Path(args[0]), Path(args[1]), "--write" in args[2:])
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
