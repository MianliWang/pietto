"""`pietto lsp`: lifecycle, protocol errors, single-file and project
diagnostics, overlays, overlapping roots, versions, stale results and
cancellation, through an in-test JSON-RPC client."""

from __future__ import annotations

import contextlib
import io
import json
import queue
import subprocess
import sys
import threading
from collections.abc import Callable
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from typing import Any, cast

import pytest

from pietto import _lsp, cli
from pietto.errors import SourceLocation

DEADLINE = 30
PROGRAM = "import sys; from pietto.cli import main; sys.exit(main(sys.argv[1:]))"
TOML = 'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n'
MODELS = """shape User:
    id: UUID
    email: Text | None
    deleted_at: Timestamp | None

source users: User = postgres.table("public.users")

export (
    shape User,
    source users,
)
"""
A_OK = """from "models.pietto" import (
    source users,
)

table active_users:
    from users
    where deleted_at is None
    select:
        id
        email
"""
A_BAD = A_OK.replace("where deleted_at is None", "where nope_a is None")
B_BAD = A_BAD.replace("active_users", "emails").replace("nope_a", "nope_b")
SINGLE = """shape User:
    id: UUID
    email: Text | None

source users: User = postgres.table("public.users")

table active_users:
    from users
    where email == "x" and nope_u is None
    select:
        id
"""
INIT = {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}}
SHUTDOWN = {"jsonrpc": "2.0", "id": 99, "method": "shutdown"}
EXIT = {"jsonrpc": "2.0", "method": "exit"}

type Message = dict[str, Any]


def frame(message: object) -> bytes:
    body = json.dumps(message).encode("utf-8")
    return b"Content-Length: %d\r\n\r\n%b" % (len(body), body)


def frames(data: bytes) -> list[Message]:
    """Every message on a server's stdout; any stray byte fails."""

    messages: list[Message] = []
    while data:
        header, separator, rest = data.partition(b"\r\n\r\n")
        assert separator and header.startswith(b"Content-Length: "), data[:80]
        length = int(header[len(b"Content-Length: ") :])
        assert len(rest) >= length
        messages.append(json.loads(rest[:length]))
        data = rest[length:]
    return messages


def init(*roots: Path, related: bool = False) -> Message:
    params: Message = {
        "initializationOptions": {"projectRoots": [str(r) for r in roots]}
    }
    if related:
        params["capabilities"] = {
            "textDocument": {"publishDiagnostics": {"relatedInformation": True}}
        }
    return {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": params}


def notify(method: str, **params: object) -> Message:
    return {"jsonrpc": "2.0", "method": method, "params": params}


def opened(uri: str, text: str, version: int = 1) -> Message:
    document = {"uri": uri, "languageId": "pietto", "version": version, "text": text}
    return notify("textDocument/didOpen", textDocument=document)


def changed(uri: str, text: str, version: int, *, ranged: bool = False) -> Message:
    change: Message = {"text": text}
    if ranged:
        zero = {"line": 0, "character": 0}
        change["range"] = {"start": zero, "end": zero}
    return notify(
        "textDocument/didChange",
        textDocument={"uri": uri, "version": version},
        contentChanges=[change],
    )


def closed(uri: str) -> Message:
    return notify("textDocument/didClose", textDocument={"uri": uri})


class Script:
    """A scripted inbox. The server reads each batch as already received and
    analyses only when the batch is used up; a callable runs when reached."""

    def __init__(self, *batches: list[object]) -> None:
        self.batches = [list(batch) for batch in batches]

    def get(self) -> object:
        while self.batches and not self.batches[0]:
            self.batches.pop(0)
        return self._next() if self.batches else _lsp._EOF

    def get_nowait(self) -> object:
        if not self.batches or not self.batches[0]:
            raise queue.Empty
        return self._next()

    def _next(self) -> object:
        item = self.batches[0].pop(0)
        if callable(item):
            cast(Callable[[], None], item)()
            return self.get_nowait() if self.batches[0] else self.get()
        return item


def session(
    first: Message, *batches: list[object], script: Script | None = None
) -> list[Message]:
    """Run one in-process session: `first` with `initialized`, each batch,
    then shutdown and exit; return everything the server wrote."""

    script = script or Script()
    script.batches = [
        [first, notify("initialized")],
        *(list(batch) for batch in batches),
        [SHUTDOWN, EXIT],
    ]
    out = io.BytesIO()
    assert _lsp._Server(script, out, "test").run() == 0
    return frames(out.getvalue())


def publishes(messages: list[Message], uri: str | None = None) -> list[Message]:
    return [
        message["params"]
        for message in messages
        if message.get("method") == "textDocument/publishDiagnostics"
        and (uri is None or message["params"]["uri"] == uri)
    ]


def run_process(data: bytes, *arguments: str) -> tuple[int, list[Message], bytes]:
    result = subprocess.run(
        [sys.executable, "-c", PROGRAM, "lsp", *arguments],
        input=data,
        capture_output=True,
        timeout=DEADLINE,
        check=False,
    )
    return result.returncode, frames(result.stdout), result.stderr


def expected(text: str, items: list[Message], *, open_buffer: bool) -> list[Message]:
    """CLI JSON diagnostics as the server must publish them."""

    lines = _lsp._Lines(text, open_buffer=open_buffer)
    return [
        {
            "range": lines.range(
                SourceLocation(
                    None,
                    item["location"]["line"],
                    item["location"]["column"],
                    item["location"]["end_line"],
                    item["location"]["end_column"],
                )
            ),
            "severity": 1 if item["severity"] == "error" else 2,
            "code": item["code"],
            "source": "pietto",
            "message": item["message"]
            + (
                ""
                if item["suggestion"] is None or item["suggestion"] in item["message"]
                else "\n" + item["suggestion"]
            ),
        }
        for item in items
    ]


def cli_json(*arguments: str) -> Message:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        cli.main([*arguments, "--format", "json"])
    return json.loads(out.getvalue())


def project(tmp_path: Path, name: str = "harbor", **sources: str) -> Path:
    root = tmp_path / name
    root.mkdir(parents=True)
    (root / "pietto.toml").write_text(TOML, encoding="utf-8")
    for file, text in sources.items():
        (root / f"{file}.pietto").write_bytes(text.encode("utf-8"))
    return root


class FoldedPath(Path):
    """A path whose equality ignores letter case, as a Windows path's does;
    a test sets it as the server's `Path` to apply that rule on any
    platform."""

    def __eq__(self, other: object) -> bool:
        return isinstance(other, PurePath) and str(self).lower() == str(other).lower()

    def __hash__(self) -> int:
        return hash(str(self).lower())


def project_expected(root: Path) -> dict[str, list[Message]]:
    """Per file URI, the CLI project check as the server must publish it."""

    items = cli_json("check", "--project", str(root))["diagnostics"]
    grouped: dict[str, list[Message]] = {}
    for item in items:
        grouped.setdefault(item["location"]["path"], []).append(item)
    return {
        (root / path).as_uri(): expected(
            (root / path).read_text(encoding="utf-8"), group, open_buffer=False
        )
        for path, group in grouped.items()
    }


def test_lifecycle_over_a_process() -> None:
    code, messages, stderr = run_process(
        frame(INIT) + frame(notify("initialized")) + frame(SHUTDOWN) + frame(EXIT),
        "--stdio",
    )
    assert (code, stderr) == (0, b"")
    assert messages == [
        {
            "jsonrpc": "2.0",
            "id": 0,
            "result": {
                "capabilities": {
                    "positionEncoding": "utf-16",
                    "textDocumentSync": {"openClose": True, "change": 1},
                },
                "serverInfo": {"name": "pietto", "version": cli._package_version()},
            },
        },
        {"jsonrpc": "2.0", "id": 99, "result": None},
    ]
    assert cli.main(["lsp", "--help"]) == 0
    assert cli.main(["lsp", "extra"]) == 2


def test_protocol_errors_over_a_process() -> None:
    hover = {"jsonrpc": "2.0", "id": 1, "method": "textDocument/hover"}
    deep = b"[" * 100_000 + b"]" * 100_000
    data = (
        frame(hover)
        + b"Content-Length: 1\r\n\r\n{"
        + b"Content-Length: %d\r\n\r\n%b" % (len(deep), deep)
        + frame([hover])
        + frame(INIT)
        + frame({"jsonrpc": "2.0", "id": 3, "method": "textDocument/hover"})
        + frame(notify("pietto/unknown"))
        + frame(notify("$/cancelRequest", id=3))
        + frame({**INIT, "id": 4})
        + frame(SHUTDOWN)
        + frame({**INIT, "id": 6})
    )
    code, messages, stderr = run_process(data)
    assert (code, stderr) == (0, b"")
    assert [(m.get("id"), m.get("error", {}).get("code")) for m in messages] == [
        (1, -32002),
        (None, -32700),
        (None, -32700),
        (None, -32600),
        (0, None),
        (3, -32601),
        (4, -32600),
        (99, None),
        (6, -32600),
    ]
    assert run_process(frame(INIT) + frame(EXIT))[0] == 1
    assert run_process(frame(INIT))[0] == 1
    # Past the int digit limit, and longer than the input: never a hang.
    for length in (b"x", b"9" * 5000, b"1000000000000"):
        code, messages, stderr = run_process(b"Content-Length: %b\r\n\r\n{}" % length)
        assert (code, messages) == (1, [])
        assert stderr.decode().splitlines() == [
            "pietto lsp: invalid message header; stopping"
        ]


def initialize_with(options: object) -> list[Message]:
    script = Script(
        [{**INIT, "params": {"initializationOptions": options}}],
        [EXIT],
    )
    out = io.BytesIO()
    assert _lsp._Server(script, out, "test").run() == 1
    return frames(out.getvalue())


ROOTS_REFUSED = [
    {
        "jsonrpc": "2.0",
        "id": 0,
        "error": {
            "code": -32602,
            "message": "projectRoots must be a list of distinct absolute paths",
        },
    }
]


@pytest.mark.parametrize(
    "options",
    [
        {"projectRoots": "relative"},
        {"projectRoots": ["relative/root"]},
        {"projectRoots": ["/abs/root", "/abs/root/."]},
        {"projectRoots": [1]},
        {"projectRoots": None},
        ["/abs/root"],
        "/abs/root",
    ],
)
def test_project_roots_must_be_distinct_absolute_paths(options: object) -> None:
    assert initialize_with(options) == ROOTS_REFUSED


@pytest.mark.parametrize("options", [None, {}, {"projectRoots": []}])
def test_no_project_roots_option_means_no_roots(options: object) -> None:
    assert "result" in initialize_with(options)[0]


def test_two_spellings_of_one_root_directory_are_not_distinct(tmp_path: Path) -> None:
    root = project(tmp_path, models=MODELS)
    (tmp_path / "link").symlink_to(root, target_is_directory=True)
    assert initialize_with({"projectRoots": [str(root), str(tmp_path / "link")]}) == (
        ROOTS_REFUSED
    )


@pytest.mark.parametrize(
    "text",
    [
        SINGLE.replace(" and nope_u is None", ""),
        SINGLE.replace("    select:\n", "    select\n"),
        SINGLE,
        A_OK,
        "#" * 1_048_577,
        "\ufeff" + SINGLE,
        SINGLE.replace("\n", "\r\n"),
        SINGLE.replace("\n", "\r"),
        SINGLE.replace('"x"', '"\U0001f600\U0001f600"'),
        SINGLE.replace("nope_u is None", "(\n        nope_u is None\n    )"),
    ],
    ids=[
        "valid",
        "syntax",
        "semantic",
        "import-warning",
        "too-large",
        "bom",
        "crlf",
        "cr",
        "astral",
        "multi-line",
    ],
)
def test_single_file_diagnostics_equal_check_json(tmp_path: Path, text: str) -> None:
    path = tmp_path / "single.pietto"
    path.write_bytes(text.encode("utf-8"))
    uri = path.as_uri()
    messages = session(init(), [opened(uri, text, 3)])
    want = expected(text, cli_json("check", str(path))["diagnostics"], open_buffer=True)
    assert publishes(messages) == [{"uri": uri, "diagnostics": want, "version": 3}]


HINTS = """shape User:
    id: Int
    region: Text
    score: Float

source users: User = postgres.table("public.users")

table paid:
    from users
    group by region
    select region, t = any(o.score for o in group)

table spread:
    from users
    select id, v = var(score), w = nope_u
"""


def test_a_suggestion_the_message_already_carries_is_shown_once(
    tmp_path: Path,
) -> None:
    path = tmp_path / "hints.pietto"
    path.write_bytes(HINTS.encode("utf-8"))
    uri = path.as_uri()
    items = cli_json("check", str(path))["diagnostics"]
    # One diagnostic of each kind: a suggestion apart from the message, a
    # suggestion the message ends with, and no suggestion.
    assert [(i["code"], i["suggestion"]) for i in items] == [
        ("PIE-S2202", "write the body as a test, such as `o.score > 0`"),
        ("PIE-S2103", items[1]["message"].removeprefix("Unknown function: var; ")),
        ("PIE-S2102", None),
    ]
    (published,) = publishes(session(init(), [opened(uri, HINTS)]))
    assert [d["message"] for d in published["diagnostics"]] == [
        "Expected Bool expression in ANY predicate\n"
        "write the body as a test, such as `o.score > 0`",
        items[1]["message"],
        "Unknown field: nope_u",
    ]
    assert published["diagnostics"] == expected(HINTS, items, open_buffer=True)


_SALES = """shape Sale:
    id: Int
    region: Text
    amount: Decimal(10, 2)
    paid: Bool

source sales: Sale = postgres.table("public.sales")
"""


@pytest.mark.parametrize(
    ("body", "codes"),
    [
        pytest.param(
            "\ntable mixed:\n    from sales\n    select id, d = amount * 2.0, n = amount + 2.0\n",
            ["PIE-S2105", "PIE-S2105"],
            id="decimal_float_operands",
        ),
        pytest.param(
            "\ntable flags:\n    from sales\n    group by region\n"
            "    select region, f = not all(o.paid for o in group)\n",
            ["PIE-S2310"],
            id="around_an_aggregate",
        ),
    ],
)
def test_a_hint_that_ends_the_message_is_shown_once(
    tmp_path: Path, body: str, codes: list[str]
) -> None:
    """The Decimal PIE-S2105 texts and the PIE-S2310 route end their message
    and are its JSON suggestion too; the editor shows the message alone."""

    text = _SALES + body
    path = tmp_path / "hints.pietto"
    path.write_bytes(text.encode("utf-8"))
    items = cli_json("check", str(path))["diagnostics"]
    assert [i["code"] for i in items] == codes
    for item in items:
        assert item["suggestion"] and item["message"] != item["suggestion"]
        assert item["message"].endswith(item["suggestion"])
    (published,) = publishes(session(init(), [opened(path.as_uri(), text)]))
    assert [d["message"] for d in published["diagnostics"]] == [
        i["message"] for i in items
    ]
    assert published["diagnostics"] == expected(text, items, open_buffer=True)


def test_positions_count_utf16_units_against_the_shown_text() -> None:
    def at(text: str, line: int, column: int, *, open_buffer: bool = True) -> object:
        location = SourceLocation(None, line, column)
        return _lsp._Lines(text, open_buffer=open_buffer).range(location)["start"]

    assert at("ab\U0001f600c", 1, 4) == {"line": 0, "character": 4}
    assert at("\ufeffab", 1, 2) == {"line": 0, "character": 2}
    assert at("\ufeffab", 1, 2, open_buffer=False) == {"line": 0, "character": 1}
    assert at("\ufeffa\nb", 2, 2) == {"line": 1, "character": 1}
    assert at("a\r\nb\rc\nd", 4, 1) == {"line": 3, "character": 0}
    assert at("ab", 1, 99) == {"line": 0, "character": 2}
    assert at("ab\ncd", 9, 1) == {"line": 1, "character": 2}
    full = SourceLocation(None, 1, 1, 1, 3)
    assert _lsp._Lines("ab", open_buffer=True).range(full) == {
        "start": {"line": 0, "character": 0},
        "end": {"line": 0, "character": 2},
    }


@pytest.mark.parametrize(
    ("uri", "windows", "path"),
    [
        ("file:///home/ada/a%23b.pietto", False, PurePosixPath("/home/ada/a#b.pietto")),
        (
            "file://localhost/home/ada/a.pietto",
            False,
            PurePosixPath("/home/ada/a.pietto"),
        ),
        ("file://server/home/a.pietto", False, None),
        ("untitled:Untitled-1", False, None),
        (
            "file:///c%3A/Users/ada/a.pietto",
            True,
            PureWindowsPath("C:/Users/ada/a.pietto"),
        ),
        ("file:///C:/x%20y/a.pietto", True, PureWindowsPath("c:/x y/a.pietto")),
        (
            "file://server/share/a.pietto",
            True,
            PureWindowsPath("//server/share/a.pietto"),
        ),
        # The host as Path.as_uri() and VS Code spell \\wsl$\Ubuntu.
        (
            "file://wsl%24/Ubuntu/home/ada/a.pietto",
            True,
            PureWindowsPath("//wsl$/Ubuntu/home/ada/a.pietto"),
        ),
    ],
)
def test_file_uris_map_to_paths(uri: str, windows: bool, path: object) -> None:
    assert _lsp.uri_to_path(uri, windows=windows) == path


def test_root_publishes_open_and_closed_modules(tmp_path: Path) -> None:
    b_text = "\ufeff" + B_BAD.replace('"models.pietto"', '"nope.pietto"')
    root = project(tmp_path, models=MODELS, a=A_BAD, b=b_text)
    a_uri, b_uri = (root / "a.pietto").as_uri(), (root / "b.pietto").as_uri()
    disk = project_expected(root)
    messages = session(
        init(root),
        [],
        [opened(a_uri, A_OK, 1)],
        [opened(b_uri, b_text[1:], 1)],
        [closed(a_uri), closed(b_uri)],
    )
    a_sets = publishes(messages, a_uri)
    b_sets = publishes(messages, b_uri)
    assert a_sets == [
        {"uri": a_uri, "diagnostics": disk[a_uri]},
        {"uri": a_uri, "diagnostics": [], "version": 1},
        {"uri": a_uri, "diagnostics": [], "version": 1},
        {"uri": a_uri, "diagnostics": disk[a_uri]},
    ]
    assert disk[b_uri][0]["range"]["start"]["line"] == 0
    assert [item.get("version") for item in b_sets] == [None, None, 1, None]
    # A closed file with a BOM and its opened buffer without one: one range.
    assert all(item["diagnostics"] == disk[b_uri] for item in b_sets)
    assert publishes(messages, (root / "models.pietto").as_uri()) == []


def test_overlays_follow_the_buffer_and_write_nothing(tmp_path: Path) -> None:
    root = project(tmp_path, models=MODELS, a=A_OK)
    (root / "c.pietto").write_bytes(b"\xff")
    before = sorted(
        (str(p), p.stat().st_size, p.stat().st_mtime_ns) for p in root.rglob("*")
    )
    a_uri, c_uri = (root / "a.pietto").as_uri(), (root / "c.pietto").as_uri()
    toml_uri = (root / "pietto.toml").as_uri()
    messages = session(
        init(root),
        [],
        [opened(c_uri, B_BAD.replace("emails", "c_rows"), 1)],
        [opened(a_uri, A_BAD, 1), opened(toml_uri, "not toml", 1)],
        [changed(a_uri, "#" * 1_048_577, 2)],
    )
    first, *rest = publishes(messages, c_uri)
    assert first["diagnostics"][0]["message"] == (
        "project error: source_read: Project source file must be valid UTF-8."
    )
    # The oversized buffer stops the check at a; partial analysis still checks
    # c, which does not import a.
    assert [[d["code"] for d in item["diagnostics"]] for item in rest] == [
        ["PIE-S2102"],
        ["PIE-S2102"],
        ["PIE-S2102"],
    ]
    assert [
        [d["code"] for d in item["diagnostics"]] for item in publishes(messages, a_uri)
    ] == [["PIE-S2102"], ["PIE-P1006"]]
    assert publishes(messages, toml_uri) == []
    after = sorted(
        (str(p), p.stat().st_size, p.stat().st_mtime_ns) for p in root.rglob("*")
    )
    assert after == before


def test_a_module_left_out_says_which_import_has_errors(tmp_path: Path) -> None:
    root = project(tmp_path, models=MODELS.replace("id: UUID", "id UUID"), a=A_BAD)
    a_uri, models_uri = (root / "a.pietto").as_uri(), (root / "models.pietto").as_uri()
    messages = session(init(root), [], [opened(models_uri, MODELS, 1)])
    hint = {
        "range": {
            "start": {"line": 0, "character": 5},
            "end": {"line": 0, "character": 20},
        },
        "severity": 3,
        "source": "pietto",
        "message": "Not checked: this module imports models.pietto, which has errors.",
    }
    # Information at the import, without a code, until the import is fixed.
    first, second = publishes(messages, a_uri)
    assert first == {"uri": a_uri, "diagnostics": [hint]}
    assert [d["code"] for d in second["diagnostics"]] == ["PIE-S2102"]


def test_a_root_error_without_a_config_file_is_shown_once(tmp_path: Path) -> None:
    root = tmp_path / "absent"
    inside = (root / "draft.pietto").as_uri()
    messages = session(init(root), [], [opened(inside, SINGLE, 1)])
    shown = [m["params"] for m in messages if m.get("method") == "window/showMessage"]
    assert len(shown) == 1 and shown[0]["type"] == 1
    assert shown[0]["message"].startswith(
        f"Pietto project root {root}: project error: "
    )
    # A file no root selects is checked on its own.
    assert [p.get("version") for p in publishes(messages, inside)] == [1]


def test_a_root_error_is_published_at_the_config_until_it_is_fixed(
    tmp_path: Path,
) -> None:
    root = project(tmp_path, a=A_OK)
    (root / "pietto.toml").write_text("schema_version = 9\n", encoding="utf-8")
    toml_uri = (root / "pietto.toml").as_uri()
    a_uri = (root / "a.pietto").as_uri()

    def fix() -> None:
        (root / "pietto.toml").write_text(TOML, encoding="utf-8")

    messages = session(init(root), [], [fix, opened(a_uri, SINGLE, 1)])
    sets = publishes(messages, toml_uri)
    assert [len(item["diagnostics"]) for item in sets] == [1, 0]
    assert sets[0]["diagnostics"][0]["message"].startswith("project error: config_")
    assert "code" not in sets[0]["diagnostics"][0]
    assert [m for m in messages if m.get("method") == "window/showMessage"] == []


@pytest.mark.parametrize("outer_first", [True, False])
def test_overlapping_roots_publish_only_the_overlap_error(
    tmp_path: Path, outer_first: bool
) -> None:
    outer = project(tmp_path, "port", top=A_OK, models=MODELS)
    (outer / "pietto.toml").write_text(
        TOML.replace('"*.pietto"', '"**/*.pietto"'), encoding="utf-8"
    )
    inner = project(outer, "sub", inner=A_BAD.replace("models.pietto", "x.pietto"))
    roots = (outer, inner) if outer_first else (inner, outer)
    inner_uri = (inner / "inner.pietto").as_uri()
    lone = tmp_path / "lone.pietto"

    def end_overlap() -> None:
        (outer / "pietto.toml").write_text(TOML, encoding="utf-8")

    messages = session(
        init(*roots),
        [],
        [opened(lone.as_uri(), A_OK, 1)],
        [end_overlap, opened((outer / "top.pietto").as_uri(), A_OK, 1)],
    )
    names = " and ".join(str(root) for root in roots)
    overlap = {
        "range": {
            "start": {"line": 0, "character": 0},
            "end": {"line": 0, "character": 0},
        },
        "severity": 1,
        "source": "pietto",
        "message": (
            f"This file belongs to two project roots: {names}."
            " Keep one of them in projectRoots."
        ),
    }
    inner_sets = publishes(messages, inner_uri)
    assert inner_sets[0] == {"uri": inner_uri, "diagnostics": [overlap]}
    assert inner_sets[-1]["diagnostics"] == project_expected(inner)[inner_uri]
    assert all(item["diagnostics"] in ([overlap], []) for item in inner_sets[:-1])
    assert publishes(messages, (outer / "top.pietto").as_uri()) == [
        {"uri": (outer / "top.pietto").as_uri(), "diagnostics": [], "version": 1}
    ]
    lone_codes = [
        (d["code"], d["severity"])
        for d in publishes(messages, lone.as_uri())[0]["diagnostics"]
    ]
    assert lone_codes[0] == ("PIE-S2708", 2)
    assert ("PIE-S2301", 1) in lone_codes


@pytest.mark.parametrize("spelling", ["./a.pietto", "A.pietto"])
@pytest.mark.parametrize("plain_first", [True, False])
def test_a_file_open_under_two_uris_gets_only_the_alias_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spelling: str, plain_first: bool
) -> None:
    if spelling == "A.pietto":
        # Where paths ignore letter case, as on Windows, so do the URIs.
        monkeypatch.setattr(_lsp, "Path", FoldedPath)
    root = project(tmp_path, models=MODELS, a=A_OK)
    plain, other = (root / "a.pietto").as_uri(), f"{root.as_uri()}/{spelling}"
    opens: list[object] = [
        opened(plain, A_BAD, 1),
        opened(other, A_BAD.replace("nope_a", "nope_d"), 1),
    ]
    messages = session(
        init(root),
        [],
        opens if plain_first else opens[::-1],
        [closed(other)],
    )
    alias = {
        "range": {
            "start": {"line": 0, "character": 0},
            "end": {"line": 0, "character": 0},
        },
        "severity": 1,
        "source": "pietto",
        "message": (
            f"This file is open under two URIs: {other} and {plain}."
            " Keep one of them open."
        ),
    }
    plain_sets = publishes(messages, plain)
    # Whichever opened first, no buffer wins; the disk text has no error.
    assert plain_sets[0] == {"uri": plain, "diagnostics": [alias], "version": 1}
    assert publishes(messages, other) == [
        {"uri": other, "diagnostics": [alias], "version": 1},
        {"uri": other, "diagnostics": []},
    ]
    # Once one URI is left, its buffer is checked again.
    assert [d["code"] for d in plain_sets[-1]["diagnostics"]] == ["PIE-S2102"]
    assert "nope_a" in plain_sets[-1]["diagnostics"][0]["message"]
    assert len(plain_sets) == 2


@pytest.mark.parametrize("spelling", ["./a.pietto", "A.pietto"])
def test_another_uri_of_a_module_is_cleared_before_the_module_is_published(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spelling: str
) -> None:
    if spelling == "A.pietto":
        monkeypatch.setattr(_lsp, "Path", FoldedPath)
    root = project(tmp_path, models=MODELS, a=A_BAD)
    plain, other = (root / "a.pietto").as_uri(), f"{root.as_uri()}/{spelling}"
    messages = session(init(root), [], [opened(other, A_BAD, 1)], [closed(other)])
    # A client such as VS Code may take both URIs for one file (on Windows,
    # file:///C:/... and file:///c%3A/...), so a set of one URI is never
    # cleared after the other URI got its set.
    assert [
        (item["uri"], [d["code"] for d in item["diagnostics"]])
        for item in publishes(messages)
        if item["uri"] in (plain, other)
    ] == [
        (plain, ["PIE-S2102"]),
        (plain, []),
        (other, ["PIE-S2102"]),
        (other, []),
        (plain, ["PIE-S2102"]),
    ]


def test_a_uri_in_another_letter_case_checks_its_buffer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Where paths ignore letter case, as on Windows, the buffer is keyed by
    # the selected entry, not by the URI's spelling.
    monkeypatch.setattr(_lsp, "Path", FoldedPath)
    root = project(tmp_path, models=MODELS, a=A_OK)
    uri = (root / "A.pietto").as_uri()
    messages = session(init(root), [], [opened(uri, A_BAD, 1)], [changed(uri, A_OK, 2)])
    assert [
        (item.get("version"), [d["code"] for d in item["diagnostics"]])
        for item in publishes(messages, uri)
    ] == [(1, ["PIE-S2102"]), (2, [])]
    assert publishes(messages, (root / "a.pietto").as_uri()) == []


def test_two_selected_names_of_one_path_get_only_the_names_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = project(tmp_path, models=MODELS, a=A_BAD)
    if (root / "A.pietto").exists():
        pytest.skip("needs two file names that differ only in letter case")
    (root / "A.pietto").write_bytes(B_BAD.encode("utf-8"))
    # Where paths ignore letter case, as in a case-sensitive directory on
    # Windows, both selected files have one path.
    monkeypatch.setattr(_lsp, "Path", FoldedPath)
    seen: list[dict[str, str]] = []
    real = _lsp.check_project_diagnostics

    def checking(root: Path, *, overlays: dict[str, str]) -> object:
        seen.append(dict(overlays))
        return real(root, overlays=overlays)

    monkeypatch.setattr(_lsp, "check_project_diagnostics", checking)
    upper, lower = (root / "A.pietto").as_uri(), (root / "a.pietto").as_uri()
    messages = session(
        init(root),
        [],
        [opened(lower, A_OK, 7), opened((root / "models.pietto").as_uri(), MODELS, 1)],
    )
    # Neither name wins the buffer, and neither file's diagnostics are shown.
    assert seen == [{}, {"models.pietto": MODELS}]
    zero = {"line": 0, "character": 0}
    names = {
        "range": {"start": zero, "end": zero},
        "severity": 1,
        "source": "pietto",
        "message": (
            "This file is selected under two names that differ only in letter"
            " case: A.pietto and a.pietto. Rename one of them."
        ),
    }
    assert publishes(messages, upper) == [
        {"uri": upper, "diagnostics": [names]},
        {"uri": upper, "diagnostics": []},
    ]
    assert publishes(messages, lower) == [
        {"uri": lower, "diagnostics": [names], "version": 7}
    ]


def test_a_file_renamed_out_of_its_root_is_checked_alone_at_once(
    tmp_path: Path,
) -> None:
    root = project(tmp_path, models=MODELS, a=A_BAD)
    uri = (root / "a.pietto").as_uri()

    def rename() -> None:
        (root / "a.pietto").rename(root / "b.pietto")

    messages = session(
        init(root), [], [opened(uri, A_BAD, 1)], [rename, changed(uri, A_BAD, 2)]
    )
    alone = cli_json("check", str(root / "b.pietto"))["diagnostics"]
    # The root clears what it published, and the same change checks the
    # buffer on its own.
    assert publishes(messages, uri)[-2:] == [
        {"uri": uri, "diagnostics": [], "version": 2},
        {
            "uri": uri,
            "diagnostics": expected(A_BAD, alone, open_buffer=True),
            "version": 2,
        },
    ]


class ProcessClient:
    """A `pietto lsp` process whose stdout a reader thread parses frame by
    frame, so every wait has a deadline and any stray byte fails."""

    def __init__(self) -> None:
        self.process = subprocess.Popen(
            [sys.executable, "-c", PROGRAM, "lsp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.messages: queue.Queue[Message | str | None] = queue.Queue()
        self.received: list[Message] = []
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        stream = self.process.stdout
        assert stream is not None
        while header := stream.readline():
            if (
                not header.startswith(b"Content-Length: ")
                or stream.readline() != b"\r\n"
            ):
                self.messages.put(f"stray output: {header!r}")
                break
            self.messages.put(json.loads(stream.read(int(header[16:]))))
        self.messages.put(None)

    def receive(self) -> Message | None:
        message = self.messages.get(timeout=DEADLINE)
        assert not isinstance(message, str), message
        if message is not None:
            self.received.append(message)
        return message

    def send(self, *messages: object) -> None:
        assert self.process.stdin is not None
        self.process.stdin.write(b"".join(frame(m) for m in messages))
        self.process.stdin.flush()

    def finish(self) -> int:
        self.send(SHUTDOWN, EXIT)
        assert self.process.stdin is not None
        self.process.stdin.close()
        while self.receive() is not None:
            pass
        return self.process.wait(timeout=DEADLINE)


def test_versions_increase_and_the_last_publish_is_the_last_version(
    tmp_path: Path,
) -> None:
    def text(version: int) -> str:
        return SINGLE.replace("nope_u", "nope_" * version)

    uri = (tmp_path / "typing.pietto").as_uri()
    client = ProcessClient()
    client.send(init(), notify("initialized"), opened(uri, text(1), 1))
    client.send(*(changed(uri, text(v), v) for v in range(2, 21)))
    # Whatever the timing, the server publishes version 20 last.
    while not any(p.get("version") == 20 for p in publishes(client.received, uri)):
        assert client.receive() is not None
    assert client.finish() == 0
    sets = publishes(client.received, uri)
    versions = [p["version"] for p in sets]
    assert versions == sorted(set(versions)) and versions[-1] == 20
    for params in sets:
        file = tmp_path / f"v{params['version']}.pietto"
        file.write_text(text(params["version"]), encoding="utf-8")
        assert params["diagnostics"] == expected(
            text(params["version"]),
            cli_json("check", str(file))["diagnostics"],
            open_buffer=True,
        )


def test_a_result_made_stale_while_checking_is_dropped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = project(tmp_path, models=MODELS, a=A_OK)
    uri = (root / "a.pietto").as_uri()
    script = Script()
    real = _lsp.check_project_diagnostics

    def checking(root: Path, *, overlays: dict[str, str]) -> object:
        if overlays.get("a.pietto") == A_BAD:
            script.batches[0].append(changed(uri, A_OK, 2))
        return real(root, overlays=overlays)

    monkeypatch.setattr(_lsp, "check_project_diagnostics", checking)
    messages = session(init(root), [opened(uri, A_BAD, 1)], script=script)
    assert publishes(messages, uri) == [{"uri": uri, "diagnostics": [], "version": 2}]


def test_cancel_has_no_effect_and_shutdown_discards_pending_work(
    tmp_path: Path,
) -> None:
    uri = (tmp_path / "x.pietto").as_uri()
    script = Script(
        [
            INIT,
            opened(uri, SINGLE, 1),
            notify("$/cancelRequest", id=0),
            SHUTDOWN,
        ],
        [EXIT],
    )
    out = io.BytesIO()
    assert _lsp._Server(script, out, "test").run() == 0
    assert [m.get("id") for m in frames(out.getvalue())] == [0, 99]


def test_a_ranged_change_is_refused_until_the_file_reopens(tmp_path: Path) -> None:
    x_uri, y_uri = (tmp_path / "x.pietto").as_uri(), (tmp_path / "y.pietto").as_uri()
    messages = session(
        init(),
        [opened(x_uri, SINGLE, 1)],
        [changed(x_uri, "", 2, ranged=True), opened(y_uri, SINGLE, 1)],
        [changed(x_uri, SINGLE, 3)],
        [opened(x_uri, SINGLE, 4)],
    )
    x_sets = publishes(messages, x_uri)
    assert [(p.get("version"), len(p["diagnostics"])) for p in x_sets] == [
        (1, 1),
        (2, 1),
        (4, 1),
    ]
    assert x_sets[1]["diagnostics"][0]["message"] == (
        "Pietto needs whole-document changes; reopen this file."
    )
    assert "code" not in x_sets[1]["diagnostics"][0]
    assert [p.get("version") for p in publishes(messages, y_uri)] == [1]


def test_related_locations_are_sent_only_when_the_client_supports_them(
    tmp_path: Path,
) -> None:
    cycle = """from "{other}.pietto" import (
    table {theirs},
)

table {mine}:
    from {theirs}
    select:
        id

export (
    table {mine},
)
"""
    root = project(
        tmp_path,
        c=cycle.format(other="d", theirs="dt", mine="ct"),
        d=cycle.format(other="c", theirs="ct", mine="dt"),
    )
    plain = publishes(session(init(root), []))
    rich = publishes(session(init(root, related=True), []))
    assert plain and all(
        "relatedInformation" not in d for p in plain for d in p["diagnostics"]
    )
    related = [d for p in rich for d in p["diagnostics"] if "relatedInformation" in d]
    assert related
    assert all(
        item["location"]["uri"].startswith(root.as_uri())
        for d in related
        for item in d["relatedInformation"]
    )
