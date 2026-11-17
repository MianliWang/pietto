"""Publish a pietto release: annotated tag, GitHub pre-release with the wheel,
sdist and SHA256SUMS, PyPI upload, then byte checks of both channels.

--commit must be a commit whose tree is --tree, the tree that Gate 2 passed on.

Dry run by default. A dry run reads only local Git objects and --dist-dir,
writes SHA256SUMS into the new directory --out, prints every action it would
take, reads no credential and opens no network connection.

--execute is refused before anything else where the environment variable CI or
GITHUB_ACTIONS is set: CI runs only the dry run and the self-tests. Otherwise
it performs the actions in this order, stopping at the first failure:
remote state, natural CI of the commit, tag, GitHub pre-release, PyPI upload,
channel checks. It reads the tokens only from the environment variables
PIETTO_RELEASE_GH_TOKEN and PIETTO_PYPI_TOKEN and never prints them; set them
in the command line that runs it, never with `set -x`. Each token is stripped of
surrounding whitespace (a CRLF file) and must then be 20 or more letters,
digits, `_` or `-`; otherwise it stops naming only the variable. Both variables are read and
removed from the environment before the first git command, so no git process
inherits a token and `uv` gets only UV_PUBLISH_TOKEN. Removing them does not
clear the environment block that this process (and uv, for UV_PUBLISH_TOKEN)
started with: /proc/<pid>/environ shows it to every process of the same user
until the process exits, so --execute runs while no other agent session or
workflow runs on the host. `uv` must be on PATH
before anything touches the network, and it uploads only to
https://upload.pypi.org/legacy/. Only https://api.github.com and
https://uploads.github.com get the GitHub token, in a header that a redirect
does not carry. In --execute, an exception other than a stop prints only its
type, and any text that the server or uv returned is withheld when it holds 4
characters of a token in a row (a window that lies wholly inside the public
prefix github_pat_, ghp_ or pypi- does not count) before it is cut to 500
characters. tests/test_repo_release_notes_fragments.py checks this offline.

The owner's conditions that this script cannot see stay with the operator:
the owner permitted this release, the release commit passed Gate 2, its batch
audit is CLEAN, every checklist item passed, and the wheel install smoke of
--dist-dir passed.

usage: python3 -I -B scripts/publish_release.py --repo ROOT --commit SHA --tree TREE
           --version X --dist-dir DIR --out DIR --ci-jobs N [--execute]
"""

from __future__ import annotations

import argparse
import base64
import configparser
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
import zipfile

OWNER_REPO = "MianliWang/pietto"
REMOTE = "origin"
NAME = "Mianli Wang"
EMAIL = "mianli.wang@mail.utoronto.ca"
API = "https://api.github.com"
PYPI_JSON = "https://pypi.org/pypi/pietto/{version}/json"
AGENT = "release-script"
TOKEN_VARIABLES = ("PIETTO_RELEASE_GH_TOKEN", "PIETTO_PYPI_TOKEN")
TOKEN = re.compile(r"[A-Za-z0-9_-]{20,}")
CI_VARIABLES = ("CI", "GITHUB_ACTIONS")
# git grep -E patterns that the tag would freeze, with the paths each reads (between releases only the third
# matches: README's links to main, which `release_prep.py bump` pins): a fill
# placeholder or the rehearsal's stand-in for one, a candidate's <FACT-NAME> placeholder, a README link to main
# (PyPI shows that README), and the DuckDB route page's pre-B1 state.
STALE = {
    r"LEAD:|#ANCHOR|REHEARSAL-PLACEHOLDER": ("docs", "README.md"),
    r"<[A-Z][A-Z0-9_.]*-[A-Z0-9_.-]*[A-Z0-9]>": ("docs", "README.md"),
    r"MianliWang/pietto/(blob|tree)/main/": ("README.md",),
    r"Construction state: PLANNED|Until S04 lands the route": (
        "docs/spec/duckdb-arrow-route-v1.md",
    ),
}
GITHUB_HOSTS = {"api.github.com", "uploads.github.com"}
PUBLIC_PREFIXES = ("github_pat_", "ghp_", "pypi-")
PYPI_UPLOAD = "https://upload.pypi.org/legacy/"
# The dist-info members that uv_build writes for pyproject.toml's license-files. Any other
# member (a .pth) is refused, so a release that adds a license file adds it here too. binding_problems()
# checks the content of each.
DIST_INFO = {
    "",
    "METADATA",
    "WHEEL",
    "RECORD",
    "entry_points.txt",
    "licenses/",
    "licenses/LICENSE",
    "licenses/THIRD_PARTY_NOTICES.md",
    "licenses/LICENSES/",
    "licenses/LICENSES/SOURCES.md",
    "licenses/LICENSES/ANTLR-4.13.2.txt",
    "licenses/LICENSES/ANTLR-4.13.2-Python3-template-header.txt",
    "licenses/LICENSES/PostgreSQL-18.6.txt",
    "licenses/LICENSES/pgvector-0.8.6.txt",
}


class Stop(Exception):
    pass


def read_tokens(environ) -> tuple[str, ...]:
    """Both tokens, stripped and removed from environ; a malformed one stops naming only its variable."""
    tokens = tuple(environ.pop(name, "").strip() for name in TOKEN_VARIABLES)
    for name, token in zip(TOKEN_VARIABLES, tokens):
        if not TOKEN.fullmatch(token):
            raise Stop(
                f"{name} is unset or not a token (20 or more letters, digits, '_' or '-')"
            )
    return tokens


def shown(text: str, secrets: tuple[str, ...]) -> str:
    """text, unless it holds 4 characters of a secret in a row outside its public prefix."""
    for secret in secrets:
        # A window wholly inside github_pat_, ghp_ or pypi- is public ("gith" is in every GitHub URL).
        start = max(
            (
                len(prefix) - 3
                for prefix in PUBLIC_PREFIXES
                if secret.startswith(prefix)
            ),
            default=0,
        )
        if any(secret[i : i + 4] in text for i in range(start, len(secret) - 3)):
            return "<withheld: the text holds part of a token>\n"
    return text


def git(repo: Path, *args: str, binary: bool = False):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    if result.returncode != 0:
        raise Stop(
            f"git {' '.join(args)}: {result.stderr.decode(errors='replace').strip()}"
        )
    return result.stdout if binary else result.stdout.decode()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def slug(text: str) -> str:
    text = (
        re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text).replace("`", "").replace("*", "")
    )
    text = "".join(c for c in text.strip().lower() if c.isalnum() or c in "_- ")
    return text.replace(" ", "-")


def preflight(
    repo: Path, commit: str, tree: str, version: str, dist: Path
) -> tuple[str, dict[str, bytes], list[str]]:
    """Local checks only. Returns (release-notes heading, artifact bytes, problems)."""
    problems: list[str] = []
    show = lambda path: git(repo, "show", f"{commit}:{path}", binary=True)  # noqa: E731
    if (actual := git(repo, "rev-parse", f"{commit}^{{tree}}").strip()) != tree:
        problems.append(
            f"the tree of {commit[:12]} is {actual}, not the Gate 2 tree {tree}"
        )
    project = tomllib.loads(show("pyproject.toml").decode())
    if project["project"]["version"] != version:
        problems.append(
            f"pyproject.toml at {commit[:12]} says {project['project']['version']}"
        )
    if f'_FALLBACK_VERSION = "{version}"'.encode() not in show("src/pietto/cli.py"):
        problems.append("src/pietto/cli.py fallback version differs")
    notes = show("docs/release-notes.md").decode()
    titles = re.findall(rf"^## (.* — {re.escape(version)})$", notes, re.MULTILINE)
    if len(titles) != 1:
        problems.append(
            f"docs/release-notes.md has {len(titles)} '## ... — {version}' headings"
        )
    left = [
        p
        for p in git(
            repo, "ls-tree", "--name-only", f"{commit}:docs/release-notes.d"
        ).split()
        if p != "README.md"
    ]
    if left:
        problems.append(f"fragments not assembled: {left}")
    for pattern, paths in STALE.items():
        found = subprocess.run(
            ["git", "-C", str(repo), "grep", "-n", "-E", pattern, commit, "--", *paths],
            capture_output=True,
        )
        if found.returncode not in (0, 1):  # 1: no match
            raise Stop(
                f"git grep {pattern}: {found.stderr.decode(errors='replace').strip()}"
            )
        problems.extend(
            f"{hit.removeprefix(commit + ':')} matches {pattern}"
            for hit in found.stdout.decode().splitlines()
        )
    author = git(repo, "log", "-1", "--format=%an <%ae>%n%cn <%ce>%n%B", commit)
    if author.splitlines()[:2] != [f"{NAME} <{EMAIL}>"] * 2:
        problems.append(
            f"commit identity is not {NAME} <{EMAIL}>: {author.splitlines()[:2]}"
        )
    if re.search(r"(?im)^co-authored-by:", author):
        problems.append("commit message has a Co-Authored-By trailer")
    if (
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "rev-parse",
                "-q",
                "--verify",
                f"refs/tags/v{version}",
            ],
            capture_output=True,
        ).returncode
        == 0
    ):
        problems.append(f"local tag v{version} already exists")
    wheel_name, sdist_name = (
        f"pietto-{version}-py3-none-any.whl",
        f"pietto-{version}.tar.gz",
    )
    # `uv build` also writes a `.gitignore` into its output directory.
    names = (
        sorted(p.name for p in dist.iterdir() if p.name != ".gitignore")
        if dist.is_dir()
        else []
    )
    if names != sorted([wheel_name, sdist_name]):
        raise Stop(
            f"{dist} must hold exactly {wheel_name} and {sdist_name}, holds {names}"
        )
    data = {name: (dist / name).read_bytes() for name in names}
    tracked = git(
        repo, "ls-tree", "-r", "-z", "--name-only", commit, "src/pietto"
    ).split("\0")[:-1]
    problems.extend(
        binding_problems(show, data[wheel_name], data[sdist_name], version, tracked)
    )
    return (titles[0] if len(titles) == 1 else ""), data, problems


def odd(name: str) -> bool:
    """A member name with an empty, . or .. component: a second name for a path, or a way out of the archive."""
    return any(part in ("", ".", "..") for part in name.removesuffix("/").split("/"))


def binding_problems(
    show, wheel: bytes, sdist: bytes, version: str, tracked: list[str]
) -> list[str]:
    """Every packaged file must be the commit's blob, byte for byte, and every
    file in tracked (the commit's src/pietto) must be in both archives; so must
    the commit's license-files (in the wheel under dist-info/licenses/) and,
    in the sdist, its readme.

    No member name has an empty, . or .. component. The wheel has no duplicate
    member and, outside pietto/, only the DIST_INFO members; each directory
    member is empty and holds a file member. Its entry_points.txt has exactly
    the commit's pyproject.toml scripts, its WHEEL says Root-Is-Purelib: true
    and the one Tag py3-none-any, and its RECORD lists each file member's
    sha256 and size, with an empty row for itself. The sdist holds only
    directories and regular files under pietto-<version>/. PKG-INFO is generated;
    it and the wheel METADATA must carry the commit's README.md and dependencies.
    uv_build rewrites pyproject.toml, which must still parse to the commit's
    pyproject.toml, and keeps the original as pyproject.toml.orig, which must be
    the commit's blob.
    """
    problems: list[str] = []
    project = tomllib.loads(show("pyproject.toml").decode())["project"]
    # shortcut: readme and license-files as the literal paths that pietto's pyproject.toml gives; a readme
    # table or a license-files glob would need resolving here.
    licenses = project.get("license-files", [])
    info = f"pietto-{version}.dist-info/"
    with zipfile.ZipFile(io.BytesIO(wheel)) as archive:
        names = archive.namelist()
        files = [name for name in names if not name.endswith("/")]
        meta = archive.read(f"{info}METADATA")
        if f"\nVersion: {version}\n" not in meta.decode():
            problems.append("wheel METADATA has another Version")
        problems.extend(metadata_problems("wheel METADATA", meta, show))
        if len(names) != len(set(names)):
            problems.append("wheel has duplicate members")
        for name in names:
            if odd(name):
                problems.append(
                    f"wheel member {name} has an empty, . or .. path component"
                )
            elif name.endswith("/") and (
                archive.getinfo(name).file_size
                or not any(f.startswith(name) for f in files)
            ):
                # odd() drops the slash and the content check skips it: pietto/cli.py/ would pass both.
                problems.append(
                    f"wheel directory member {name} has content or no file member under it"
                )
            elif name.startswith("pietto/"):
                if not name.endswith("/") and archive.read(name) != _blob(
                    show, f"src/{name}"
                ):
                    problems.append(f"wheel {name} differs from the commit")
            elif not (name.startswith(info) and name.removeprefix(info) in DIST_INFO):
                problems.append(
                    f"wheel member {name} is neither under pietto/ nor a known dist-info member"
                )
            elif (
                (path := name.removeprefix(f"{info}licenses/")) != name
                and not name.endswith("/")
                and archive.read(name) != _blob(show, path)
            ):
                problems.append(f"wheel {name} differs from the commit")
        problems.extend(
            f"wheel lacks {path}"
            for path in sorted(set(tracked) - {f"src/{name}" for name in names})
        )
        problems.extend(
            f"wheel lacks {info}licenses/{path}"
            for path in licenses
            if f"{info}licenses/{path}" not in names
        )
        scripts = configparser.ConfigParser(delimiters=("=",), interpolation=None)
        scripts.optionxform = str  # script names keep their case
        scripts.read_string(archive.read(f"{info}entry_points.txt").decode())
        groups = {
            "console_scripts": project.get("scripts", {}),
            "gui_scripts": project.get("gui-scripts", {}),
            **project.get("entry-points", {}),
        }
        if {group: dict(scripts[group]) for group in scripts.sections()} != {
            g: e for g, e in groups.items() if e
        }:
            problems.append(
                "wheel entry_points.txt differs from the commit's pyproject.toml scripts"
            )
        fields = [
            line.partition(": ")[::2]
            for line in archive.read(f"{info}WHEEL").decode().splitlines()
        ]
        if sorted(f for f in fields if f[0] in ("Root-Is-Purelib", "Tag")) != [
            ("Root-Is-Purelib", "true"),
            ("Tag", "py3-none-any"),
        ]:
            problems.append(
                "wheel WHEEL is not Root-Is-Purelib: true with the one Tag py3-none-any"
            )
        rows = [[f"{info}RECORD", "", ""]]
        for name in files:
            if name != f"{info}RECORD":
                data = archive.read(name)
                digest = (
                    base64.urlsafe_b64encode(hashlib.sha256(data).digest())
                    .rstrip(b"=")
                    .decode()
                )
                rows.append([name, f"sha256={digest}", str(len(data))])
        if sorted(
            csv.reader(archive.read(f"{info}RECORD").decode().splitlines())
        ) != sorted(rows):
            problems.append(
                "wheel RECORD does not list each file member's sha256 and size"
            )
    original = False
    seen = set()
    with tarfile.open(fileobj=io.BytesIO(sdist), mode="r:gz") as archive:
        prefix = f"pietto-{version}/"
        for member in archive.getmembers():
            if odd(member.name):
                problems.append(
                    f"sdist member {member.name} has an empty, . or .. path component"
                )
                continue
            if member.name != prefix[:-1] and not member.name.startswith(prefix):
                problems.append(f"sdist member {member.name} is outside {prefix}")
                continue
            if not member.isfile():
                if not member.isdir():
                    problems.append(
                        f"sdist member {member.name} is not a regular file or directory"
                    )
                continue
            path = member.name.removeprefix(prefix)
            seen.add(path)
            content = archive.extractfile(member).read()
            if path == "PKG-INFO":
                if f"\nVersion: {version}\n" not in content.decode():
                    problems.append("sdist PKG-INFO has another Version")
                problems.extend(metadata_problems("sdist PKG-INFO", content, show))
            elif path == "pyproject.toml.orig":
                original = content == _blob(show, "pyproject.toml")
            elif path == "pyproject.toml":
                if tomllib.loads(content.decode()) != tomllib.loads(
                    show("pyproject.toml").decode()
                ):
                    problems.append(
                        "sdist pyproject.toml does not parse to the commit's pyproject.toml"
                    )
            elif content != _blob(show, path):
                problems.append(f"sdist {path} differs from the commit")
    required = {*tracked, project["readme"], *licenses, "PKG-INFO", "pyproject.toml"}
    problems.extend(f"sdist lacks {path}" for path in sorted(required - seen))
    if not original:
        problems.append(
            "sdist pyproject.toml.orig is missing or differs from the commit's pyproject.toml"
        )
    return problems


def metadata_problems(label: str, meta: bytes, show) -> list[str]:
    """PyPI's page shows the first upload's metadata: its body must be the
    commit's README.md byte for byte, and its Requires-Dist and Provides-Extra
    lines must be the commit's pyproject.toml dependencies and extras."""
    head, _, body = meta.partition(b"\n\n")
    problems = (
        []
        if body == _blob(show, "README.md")
        else [f"{label} description is not the commit's README.md"]
    )
    project = tomllib.loads(show("pyproject.toml").decode())["project"]
    extras = project.get("optional-dependencies", {})
    # shortcut: uv_build's spelling of each requirement, compared verbatim; a requirement with spaces or a
    # marker in pyproject.toml would need packaging's normalization here.
    want = [
        *project.get("dependencies", []),
        *(f"{r} ; extra == '{e}'" for e, rs in extras.items() for r in rs),
    ]
    fields = [line.partition(": ")[::2] for line in head.decode().splitlines()]
    if sorted(v for k, v in fields if k == "Requires-Dist") != sorted(want):
        problems.append(
            f"{label} Requires-Dist differs from the commit's pyproject.toml"
        )
    if sorted(v for k, v in fields if k == "Provides-Extra") != sorted(extras):
        problems.append(
            f"{label} Provides-Extra differs from the commit's pyproject.toml"
        )
    return problems


def _blob(show, path: str) -> bytes | None:
    try:
        return show(path)
    except Stop:
        return None


def write_sums(out: Path, data: dict[str, bytes]) -> bytes:
    out.mkdir(parents=True, exist_ok=False)
    sums = "".join(f"{sha256(data[name])}  {name}\n" for name in sorted(data)).encode()
    (out / "SHA256SUMS").write_bytes(sums)
    return sums


def pypi_problems(document: dict, local: dict[str, bytes]) -> list[str]:
    """Compare the PyPI JSON document of the version with the local files."""
    remote = {
        item["filename"]: item["digests"]["sha256"] for item in document.get("urls", [])
    }
    expected = {name: sha256(content) for name, content in local.items()}
    if remote == expected:
        return []
    return [f"PyPI lists {remote}, local is {expected}"]


def http(
    url: str,
    token: str | None = None,
    method: str = "GET",
    body: bytes | None = None,
    content_type: str = "application/json",
) -> tuple[int, bytes]:
    headers = {"User-Agent": AGENT}
    parts = urllib.parse.urlsplit(url)
    github = parts.scheme == "https" and parts.hostname in GITHUB_HOSTS
    if github:
        headers |= {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    if body is not None:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    if github and token:
        # Unredirected: urllib does not carry it to a redirect's host.
        request.add_unredirected_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def must(status_body: tuple[int, bytes], *ok: int) -> dict:
    status, body = status_body
    if status not in ok:
        # Whole body: shown() must see all of it before the print cuts it.
        raise Stop(f"HTTP {status}: {body.decode(errors='replace')}")
    return json.loads(body) if body and status < 300 else {}


def check_ci(commit: str, jobs: int, token: str) -> str:
    """The line to print (it quotes the server's run id) when the natural CI of commit passed."""
    runs = must(
        http(
            f"{API}/repos/{OWNER_REPO}/actions/runs?head_sha={commit}&event=push&branch=main&per_page=100",
            token,
        ),
        200,
    )
    ci = [r for r in runs["workflow_runs"] if r["path"] == ".github/workflows/ci.yml"]
    # Natural CI only: one run, attempt 1, never a rerun (Lean Gate v3).
    if (
        len(ci) != 1
        or ci[0]["run_attempt"] != 1
        or ci[0]["status"] != "completed"
        or ci[0]["conclusion"] != "success"
    ):
        raise Stop(
            f"natural CI of {commit[:12]}: {[(r['id'], r['run_attempt'], r['status'], r['conclusion']) for r in ci]}"
        )
    listed = must(
        http(
            f"{API}/repos/{OWNER_REPO}/actions/runs/{ci[0]['id']}/jobs?per_page=100",
            token,
        ),
        200,
    )
    done = [j for j in listed["jobs"] if j["conclusion"] == "success"]
    if listed["total_count"] != jobs or len(done) != jobs:
        raise Stop(
            f"CI run {ci[0]['id']}: {len(done)} of {listed['total_count']} jobs succeeded, need {jobs}/{jobs}"
        )
    return f"natural CI run {ci[0]['id']} attempt {ci[0]['run_attempt']}: {jobs}/{jobs} jobs succeeded\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--tree", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--dist-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ci-jobs", type=int, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    run = args.execute
    version, tag = args.version, f"v{args.version}"
    secrets: tuple[str, ...] = ()
    try:
        if run:
            if set(CI_VARIABLES) & os.environ.keys():
                raise Stop(
                    f"--execute is refused where {' or '.join(CI_VARIABLES)} is set; nothing was done"
                )
            # Before the first git command, so no child process inherits a token.
            secrets = read_tokens(os.environ)
        commit = git(args.repo, "rev-parse", f"{args.commit}^{{commit}}").strip()
        title, data, problems = preflight(
            args.repo, commit, args.tree, version, args.dist_dir
        )
        sums = write_sums(args.out, data)
    except (Stop, FileExistsError) as error:
        print(f"STOP {shown(str(error), secrets)}", file=sys.stderr)
        return 1
    except Exception as error:  # noqa: BLE001
        if not run:
            raise  # no token was read: the traceback is safe and says where
        # As below: a message or traceback can quote what the tokens were near, so only the type is printed.
        print(f"STOP {type(error).__name__} (message not printed)", file=sys.stderr)
        return 1
    print(
        f"{'EXECUTE' if run else 'DRY RUN'}: pietto {version} from {commit} (Gate 2 tree {args.tree})"
    )
    print(f"SHA256SUMS written to {args.out / 'SHA256SUMS'}:\n{sums.decode()}", end="")
    for problem in problems:
        print(f"PREFLIGHT {problem}", file=sys.stderr)
    # The comparator itself: equal digests pass, one changed digest fails.
    fake = {
        "urls": [
            {"filename": n, "digests": {"sha256": sha256(c)}} for n, c in data.items()
        ]
    }
    assert pypi_problems(fake, data) == []
    fake["urls"][0]["digests"]["sha256"] = "0" * 64
    assert pypi_problems(fake, data) != []
    notes_url = f"https://github.com/{OWNER_REPO}/blob/{tag}/docs/release-notes.md#{slug(title)}"
    body = (
        f"pietto {version} public alpha.\n\nRelease notes: {notes_url}\n\n"
        "The wheel and sdist are the files on PyPI. Check downloaded files with "
        "`sha256sum --ignore-missing -c SHA256SUMS`.\n"
    )
    release = {
        "tag_name": tag,
        "target_commitish": commit,
        "name": f"pietto {version}",
        "body": body,
        "draft": True,
        "prerelease": True,
    }
    assets = {**data, "SHA256SUMS": sums}
    plan = [
        f"git ls-remote {REMOTE} refs/heads/main refs/tags/{tag}: main must be {commit}, no tag",
        f"GET {API}/repos/{OWNER_REPO}/actions/runs?head_sha={commit}&event=push&branch=main: CI {args.ci_jobs}/{args.ci_jobs} success",
        f"GET {API}/repos/{OWNER_REPO}/releases/tags/{tag}: must be 404",
        f"GET {PYPI_JSON.format(version=version)}: must be 404",
        f"git -c user.name='{NAME}' -c user.email={EMAIL} tag -a {tag} -m 'pietto {version}' {commit}",
        f"git push {REMOTE} refs/tags/{tag}; ls-remote must show {tag}^{{}} = {commit}",
        f"POST {API}/repos/{OWNER_REPO}/releases {json.dumps(release)}",
        *(
            f"POST <upload_url>?name={name} ({len(content)} bytes, sha256 {sha256(content)})"
            for name, content in assets.items()
        ),
        "PATCH the release: draft false, prerelease true; download each asset and compare sha256",
        f"UV_PUBLISH_TOKEN=<env> uv publish --trusted-publishing never --publish-url {PYPI_UPLOAD} --check-url https://pypi.org/simple/ {' '.join(sorted(data))}",
        f"GET {PYPI_JSON.format(version=version)} until both files are listed; compare digests; download each file and compare sha256",
    ]
    if not run:
        print("\nwould do, in order:")
        for step in plan:
            print(f"  - {step}")
        print("comparator self-check passed; no credential read, no network used")
        return 1 if problems else 0
    if problems:
        print("STOP preflight failed; nothing was done", file=sys.stderr)
        return 1
    try:
        gh, pypi = secrets
        uv = shutil.which("uv")
        if uv is None:
            raise Stop("uv not found on PATH")
        remote = git(
            args.repo, "ls-remote", REMOTE, "refs/heads/main", f"refs/tags/{tag}"
        )
        if remote.split() != [commit, "refs/heads/main"]:
            raise Stop(f"remote is not main = {commit} without {tag}: {remote.split()}")
        print(shown(check_ci(commit, args.ci_jobs, gh), secrets), end="")
        must(http(f"{API}/repos/{OWNER_REPO}/releases/tags/{tag}", gh), 404)
        must(http(PYPI_JSON.format(version=version)), 404)
        git(
            args.repo,
            "-c",
            f"user.name={NAME}",
            "-c",
            f"user.email={EMAIL}",
            "tag",
            "-a",
            tag,
            "-m",
            f"pietto {version}",
            commit,
        )
        tagger = git(
            args.repo,
            "for-each-ref",
            f"refs/tags/{tag}",
            "--format=%(taggername) %(taggeremail)",
        ).strip()
        if tagger != f"{NAME} <{EMAIL}>":
            raise Stop(f"tagger is {tagger}")
        git(args.repo, "push", REMOTE, f"refs/tags/{tag}")
        peeled = git(args.repo, "ls-remote", REMOTE, f"refs/tags/{tag}^{{}}").split()
        if peeled[:1] != [commit]:
            raise Stop(f"remote {tag} peels to {peeled}")
        print(f"tag {tag} pushed")
        created = must(
            http(
                f"{API}/repos/{OWNER_REPO}/releases",
                gh,
                "POST",
                json.dumps(release).encode(),
            ),
            201,
        )
        upload = created["upload_url"].split("{")[0]
        for name, content in assets.items():
            must(
                http(
                    f"{upload}?name={name}",
                    gh,
                    "POST",
                    content,
                    "application/octet-stream",
                ),
                201,
            )
        published = must(
            http(
                f"{API}/repos/{OWNER_REPO}/releases/{created['id']}",
                gh,
                "PATCH",
                json.dumps({"draft": False, "prerelease": True}).encode(),
            ),
            200,
        )
        listed = {a["name"]: a["browser_download_url"] for a in published["assets"]}
        if sorted(listed) != sorted(assets):
            raise Stop(f"release assets are {sorted(listed)}")
        for name, url in listed.items():
            status, content = http(url)
            if status != 200 or sha256(content) != sha256(assets[name]):
                raise Stop(
                    f"GitHub asset {name}: HTTP {status}, sha256 {sha256(content)}"
                )
        print(
            shown(
                f"GitHub pre-release {published['html_url']}: 3 assets byte-equal\n",
                secrets,
            ),
            end="",
        )
        env = {**os.environ, "UV_PUBLISH_TOKEN": pypi}
        files = [str(args.dist_dir / name) for name in sorted(data)]
        upload_run = subprocess.run(
            [
                uv,
                "publish",
                "--trusted-publishing",
                "never",
                "--publish-url",
                PYPI_UPLOAD,
                "--check-url",
                "https://pypi.org/simple/",
                *files,
            ],
            env=env,
            capture_output=True,
            text=True,
        )
        print(shown(upload_run.stdout + upload_run.stderr, secrets), end="")
        if upload_run.returncode != 0:
            raise Stop(f"uv publish exited {upload_run.returncode}")
        for attempt in range(20):
            status, raw = http(PYPI_JSON.format(version=version))
            document = json.loads(raw) if status == 200 else {}
            if status == 200 and len(document.get("urls", [])) == len(data):
                break
            time.sleep(15)
        else:
            raise Stop("PyPI did not list both files within 5 minutes")
        if found := pypi_problems(document, data):
            raise Stop(found[0])
        for item in document["urls"]:
            status, content = http(item["url"])
            if status != 200 or sha256(content) != sha256(data[item["filename"]]):
                raise Stop(
                    f"PyPI file {item['filename']}: HTTP {status}, sha256 {sha256(content)}"
                )
        print(f"PyPI {version}: both files listed and downloaded byte-equal")
    except Stop as error:
        print(f"STOP {shown(str(error), secrets)[:500]}", file=sys.stderr)
        return 1
    except Exception as error:  # noqa: BLE001
        # A message can quote a request header, so only the type is printed.
        print(f"STOP {type(error).__name__} (message not printed)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
