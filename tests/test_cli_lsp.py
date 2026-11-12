"""`pietto lsp`: lifecycle, protocol errors, single-file and project
diagnostics, overlays, overlapping roots, versions, stale results and
cancellation, through an in-test JSON-RPC client."""

from __future__ import annotations

import contextlib
import dataclasses
import io
import json
import queue
import re
import subprocess
import sys
import threading
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from typing import Any, cast

import pytest
from antlr4 import InputStream

from pietto import _editor_completion, _lsp, cli, source_format
from pietto.errors import SourceLocation
from pietto.generated.PiettoLexer import PiettoLexer
from pietto.generated.PiettoParser import PiettoParser
from pietto.parser_api import _parse_migration_source
from pietto.semantic.aggregates import (
    GROUP_TEST_AGGREGATE_NAMES,
    SEMANTIC_AGGREGATE_NAMES,
)
from pietto.semantic.catalog import (
    BUILTIN_FUNCTIONS,
    BUILTIN_TYPE_NAMES,
    SPECIAL_BUILTIN_FUNCTION_NAMES,
)

DEADLINE = 30
REPO_ROOT = Path(__file__).resolve().parents[1]
FORMAT_CORPUS = sorted(
    path
    for folder in ("examples", "tests/fixtures")
    for path in (REPO_ROOT / folder).rglob("*.pietto")
)
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


def init(
    *roots: Path,
    related: bool = False,
    plaintext_hover: bool = False,
    hierarchical_symbols: bool = False,
) -> Message:
    params: Message = {
        "initializationOptions": {"projectRoots": [str(r) for r in roots]}
    }
    if related:
        params["capabilities"] = {
            "textDocument": {"publishDiagnostics": {"relatedInformation": True}}
        }
    if plaintext_hover or hierarchical_symbols:
        capabilities = cast(dict[str, object], params.setdefault("capabilities", {}))
        text_document = cast(
            dict[str, object], capabilities.setdefault("textDocument", {})
        )
        if plaintext_hover:
            text_document["hover"] = {"contentFormat": ["plaintext"]}
        if hierarchical_symbols:
            text_document["documentSymbol"] = {
                "hierarchicalDocumentSymbolSupport": True
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


def request(
    request_id: int,
    method: str,
    uri: str,
    line: int | None = None,
    character: int | None = None,
) -> Message:
    params: Message = {"textDocument": {"uri": uri}}
    if line is not None and character is not None:
        params["position"] = {"line": line, "character": character}
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}


class Script:
    """A scripted inbox. The server reads each batch as already received and
    analyses only when the batch is used up; a callable runs when reached."""

    def __init__(self, *batches: Sequence[object]) -> None:
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
    first: Message, *batches: Sequence[object], script: Script | None = None
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


def response(messages: list[Message], request_id: int) -> Message:
    return next(item for item in messages if item.get("id") == request_id)


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
                    "completionProvider": {},
                    "hoverProvider": True,
                    "definitionProvider": True,
                    "documentSymbolProvider": True,
                    "documentFormattingProvider": True,
                    "workspaceSymbolProvider": True,
                    "documentLinkProvider": {"resolveProvider": False},
                },
                "serverInfo": {"name": "pietto", "version": cli._package_version()},
            },
        },
        {"jsonrpc": "2.0", "id": 99, "result": None},
    ]
    assert cli.main(["lsp", "--help"]) == 0
    assert cli.main(["lsp", "extra"]) == 2


def test_formatting_over_a_process() -> None:
    uri, text = "untitled:Untitled-1", "shape A:\r\n  id: Int  # \xe9\U0001d11e\r\n"
    code, messages, stderr = run_process(
        frame(INIT)
        + frame(notify("initialized"))
        + frame(opened(uri, text))
        + frame(formatting(1, uri))
        + frame(closed(uri))
        + frame(SHUTDOWN)
        + frame(EXIT),
        "--stdio",
    )
    assert (code, stderr) == (0, b"")
    # The only notifications are the buffer's diagnostics, which the reader
    # thread's timing may place before or after an answer.
    assert all(
        message["method"] == "textDocument/publishDiagnostics"
        and message["params"]["uri"] == uri
        for message in messages
        if "method" in message
    )
    assert [message for message in messages if "method" not in message] == [
        response(messages, 0),
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": [
                {
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 2, "character": 0},
                    },
                    "newText": "shape A:\r\n    id: Int  # \xe9\U0001d11e\r\n",
                }
            ],
        },
        {"jsonrpc": "2.0", "id": 99, "result": None},
    ]


@pytest.mark.parametrize("method", ["textDocument/hover", "textDocument/definition"])
@pytest.mark.parametrize(
    "position", [None, {"line": True, "character": 0}, {"line": 0, "character": -1}]
)
def test_editor_positions_are_checked_without_a_snapshot(
    tmp_path: Path, method: str, position: object
) -> None:
    uri = (tmp_path / "x.pietto").as_uri()
    message = request(1, method, uri)
    if position is not None:
        message["params"]["position"] = position
    messages = session(init(), [message])
    assert response(messages, 1)["error"]["code"] == -32602
    # It is refused at once while an analysis of its document is pending, not
    # held and then answered with no result when shutdown stops that analysis.
    script = Script([INIT, opened(uri, SINGLE, 1), message, SHUTDOWN], [EXIT])
    out = io.BytesIO()
    assert _lsp._Server(script, out, "test").run() == 0
    assert response(frames(out.getvalue()), 1)["error"]["code"] == -32602


def test_single_file_editor_requests_use_one_current_semantic_snapshot(
    tmp_path: Path,
) -> None:
    text = """shape User:
    id: Int

source users: User = postgres.table("public.users")

table rows:
    from users
    select id
"""
    path = tmp_path / "rows.pietto"
    uri = path.as_uri()
    messages = session(
        init(),
        [opened(uri, text, 1)],
        [
            request(1, "textDocument/hover", uri, 1, 8),
            request(2, "textDocument/definition", uri, 6, 9),
            request(3, "textDocument/documentSymbol", uri),
            request(4, "textDocument/hover", uri, 7, 11),
        ],
    )
    assert response(messages, 1)["result"] == {
        "contents": {"language": "pietto", "value": "builtin Int"},
        "range": {
            "start": {"line": 1, "character": 8},
            "end": {"line": 1, "character": 11},
        },
    }
    assert response(messages, 2)["result"] == {
        "uri": uri,
        "range": {
            "start": {"line": 3, "character": 0},
            "end": {"line": 3, "character": 51},
        },
    }
    assert response(messages, 3)["result"] == [
        {
            "name": "User",
            "kind": 5,
            "location": {
                "uri": uri,
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 1, "character": 11},
                },
            },
        },
        {
            "name": "users",
            "kind": 13,
            "location": {
                "uri": uri,
                "range": {
                    "start": {"line": 3, "character": 0},
                    "end": {"line": 3, "character": 51},
                },
            },
        },
        {
            "name": "rows",
            "kind": 5,
            "location": {
                "uri": uri,
                "range": {
                    "start": {"line": 5, "character": 0},
                    "end": {"line": 7, "character": 13},
                },
            },
        },
    ]
    assert response(messages, 4)["result"] is None


def test_editor_requests_wait_for_the_pending_epoch_and_drop_stale_positions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = "shape User:\n    id: Int\n"
    second = "shape Account:\n    id: Int\n"
    uri = (tmp_path / "shape.pietto").as_uri()
    script = Script()
    real = _lsp._check_text_with_editor_facts

    def checking(text: str, *, path: str | None = None) -> object:
        # A request received while this epoch is analysed waits for it.
        script.batches[0].append(request(3, "textDocument/documentSymbol", uri))
        return real(text, path=path)

    monkeypatch.setattr(_lsp, "_check_text_with_editor_facts", checking)
    messages = session(
        init(),
        [
            opened(uri, first, 1),
            request(1, "textDocument/documentSymbol", uri),
            changed(uri, second, 2),
            request(2, "textDocument/documentSymbol", uri),
        ],
        script=script,
    )
    # The document changed before its first request could be answered.
    assert response(messages, 1)["result"] == []
    assert response(messages, 2)["result"][0]["name"] == "Account"
    assert response(messages, 3)["result"][0]["name"] == "Account"
    # Each request has exactly one answer; on one document the waiting
    # requests are answered in arrival order.
    assert [item["id"] for item in messages if "id" in item] == [0, 1, 2, 3, 99]


@pytest.mark.parametrize("reopened", [False, True], ids=["closed", "reopened"])
def test_a_waiting_request_is_stale_once_its_document_closes(
    tmp_path: Path, reopened: bool
) -> None:
    root = project(tmp_path, models=MODELS, a=A_OK)
    uri = (root / "a.pietto").as_uri()
    renamed = A_OK.replace("active_users", "renamed")
    messages = session(
        init(root),
        [
            opened(uri, A_OK, 1),
            request(1, "textDocument/documentSymbol", uri),
            closed(uri),
            *([opened(uri, renamed, 1)] if reopened else []),
            request(2, "textDocument/documentSymbol", uri),
        ],
    )
    # The analysis that both requests wait for leaves facts at this path,
    # from the disk text or from the reopened buffer, but only the second
    # request was sent for the document that is open now.
    assert response(messages, 1)["result"] == []
    assert [item["name"] for item in response(messages, 2)["result"]] == [
        "renamed" if reopened else "active_users"
    ]


def test_untitled_document_symbols_and_definition_stay_in_the_open_document() -> None:
    text = """shape User:
    id: Int

source users: User = postgres.table("users")

table rows:
    from users
    select id
"""
    uri = "untitled:rows"
    messages = session(
        init(),
        [opened(uri, text, 1)],
        [
            request(1, "textDocument/documentSymbol", uri),
            request(2, "textDocument/definition", uri, 6, 9),
        ],
    )
    assert [item["name"] for item in response(messages, 1)["result"]] == [
        "User",
        "users",
        "rows",
    ]
    assert response(messages, 2)["result"]["uri"] == uri


@pytest.mark.parametrize("hierarchical", [False, True], ids=["flat", "hierarchical"])
def test_document_symbols_keep_constants_and_relationships_in_source_order(
    tmp_path: Path, hierarchical: bool
) -> None:
    text = """shape User:
    id: Int

cutoff: Int = 1

relationship same(a: User, b: User): a.id == b.id

def positive(x: Int) -> Bool:
    return x > 0

source users: User = postgres.table("users")
"""
    uri = (tmp_path / "symbols.pietto").as_uri()
    messages = session(
        init(hierarchical_symbols=hierarchical),
        [opened(uri, text, 1)],
        [request(1, "textDocument/documentSymbol", uri)],
    )
    symbols = [
        ("User", 5, "shape User"),
        ("cutoff", 14, "constant cutoff"),
        ("same", 12, "relationship same"),
        ("positive", 12, "def positive"),
        ("users", 13, "source users"),
    ]
    assert [
        (item["name"], item["kind"], item.get("detail"))
        for item in response(messages, 1)["result"]
    ] == [
        (name, kind, detail if hierarchical else None) for name, kind, detail in symbols
    ]


def test_project_document_symbols_keep_relationships_between_relations(
    tmp_path: Path,
) -> None:
    text = """shape User:
    id: Int

source users: User = postgres.table("users")

table all_users:
    from users
    select:
        id

relationship same(a: User, b: User): a.id == b.id

def positive(x: Int) -> Bool:
    return x > 0

query visible_users:
    from all_users
    select:
        id

query both:
    union all all_users, visible_users

query seeded:
    values(id: Int):
        1
"""
    root = project(tmp_path, symbols=text)
    uri = (root / "symbols.pietto").as_uri()
    messages = session(
        init(root, hierarchical_symbols=True),
        [opened(uri, text, 1)],
        [request(1, "textDocument/documentSymbol", uri)],
    )
    assert publishes(messages, uri)[-1]["diagnostics"] == []
    symbols = response(messages, 1)["result"]
    # A set or VALUES body keeps its authored keyword, and a def is listed
    # as in a single file.
    assert [
        (symbol["name"], symbol["kind"], symbol["detail"]) for symbol in symbols
    ] == [
        ("User", 5, "shape User"),
        ("users", 13, "source users"),
        ("all_users", 5, "table all_users"),
        ("same", 12, "relationship same"),
        ("positive", 12, "def positive"),
        ("visible_users", 5, "query visible_users"),
        ("both", 5, "query both"),
        ("seeded", 5, "query seeded"),
    ]
    assert symbols[3]["range"]["start"] == {"line": 10, "character": 0}


@pytest.mark.parametrize("project_mode", [False, True], ids=["single", "project"])
def test_from_hover_shows_the_authored_keyword_of_a_set_or_values_relation(
    tmp_path: Path, project_mode: bool
) -> None:
    text = """shape User:
    id: Int

source users: User = postgres.table("users")

table all_users:
    from users
    select:
        id

query both:
    union all all_users, all_users

table from_both:
    from both
    select:
        id

query seeded:
    values(id: Int):
        1

table from_seeded:
    from seeded
    select:
        id
"""
    if project_mode:
        root = project(tmp_path, relations=text)
        uri = (root / "relations.pietto").as_uri()
        initialization = init(root)
    else:
        uri = (tmp_path / "relations.pietto").as_uri()
        initialization = init()
    messages = session(
        initialization,
        [opened(uri, text, 1)],
        [
            request(1, "textDocument/hover", uri, 14, 9),
            request(2, "textDocument/definition", uri, 14, 9),
            request(3, "textDocument/hover", uri, 23, 9),
            request(4, "textDocument/definition", uri, 23, 9),
        ],
    )
    diagnostics = publishes(messages, uri)[-1]["diagnostics"]
    if not project_mode:
        # A single file refuses set and VALUES bodies (PIE-S2334, PIE-S2347),
        # so its check keeps no facts and no single-file use reads one.
        assert any(item["severity"] == 1 for item in diagnostics)
        assert [response(messages, item)["result"] for item in (1, 2, 3, 4)] == [
            None
        ] * 4
        return
    assert diagnostics == []
    assert response(messages, 1)["result"]["contents"]["value"] == "query both"
    assert response(messages, 2)["result"]["range"]["start"] == {
        "line": 10,
        "character": 0,
    }
    assert response(messages, 3)["result"]["contents"]["value"] == "query seeded"
    assert response(messages, 4)["result"]["range"]["start"] == {
        "line": 18,
        "character": 0,
    }


def test_a_from_that_reads_a_relation_let_defines_it_and_a_table_function_has_none(
    tmp_path: Path,
) -> None:
    text = """shape User:
    id: Int

source users: User = postgres.table("users")

table kept:
    let picked:
        from users
        select:
            id
    from picked
    select:
        id

query days:
    from generate_series(1, 31, 1) as n
    select:
        n

table again:
    from kept
    select:
        id
"""
    root = project(tmp_path, kept=text)
    uri = (root / "kept.pietto").as_uri()
    messages = session(
        init(root),
        [opened(uri, text, 1)],
        [
            request(1, "textDocument/hover", uri, 10, 9),
            request(2, "textDocument/definition", uri, 10, 9),
            request(3, "textDocument/hover", uri, 15, 9),
            request(4, "textDocument/definition", uri, 15, 9),
            request(5, "textDocument/hover", uri, 7, 13),
            request(6, "textDocument/documentSymbol", uri),
            request(7, "textDocument/hover", uri, 20, 9),
            request(8, "textDocument/definition", uri, 20, 9),
            request(9, "textDocument/hover", uri, 9, 13),
            request(10, "textDocument/definition", uri, 9, 13),
            request(11, "textDocument/hover", uri, 12, 9),
            request(12, "textDocument/definition", uri, 12, 9),
        ],
    )
    assert publishes(messages, uri)[-1]["diagnostics"] == []
    # A FROM that reads the relation let defines that let's occurrence; a
    # table-function input is no declaration a use can name, so it has no
    # fact. The let's own FROM keeps its fact, and so does a FROM that reads
    # the declaration holding the let.
    assert response(messages, 1)["result"]["contents"]["value"] == "let picked"
    assert response(messages, 2)["result"] == {
        "uri": uri,
        "range": {
            "start": {"line": 6, "character": 4},
            "end": {"line": 9, "character": 14},
        },
    }
    assert [response(messages, item)["result"] for item in (3, 4)] == [None] * 2
    assert response(messages, 5)["result"]["contents"]["value"] == "source users"
    # A field that the let reads from the source defines the shape field; the
    # same name read from the let is its field, with no authored target.
    assert response(messages, 9)["result"]["contents"]["value"] == "field id"
    assert response(messages, 10)["result"]["range"] == {
        "start": {"line": 1, "character": 4},
        "end": {"line": 1, "character": 11},
    }
    assert response(messages, 11)["result"]["contents"]["value"] == "field id"
    assert response(messages, 12)["result"] is None
    assert [item["name"] for item in response(messages, 6)["result"]] == [
        "User",
        "users",
        "kept",
        "days",
        "again",
    ]
    assert response(messages, 7)["result"]["contents"]["value"] == "table kept"
    assert response(messages, 8)["result"]["uri"] == uri
    assert response(messages, 8)["result"]["range"]["start"] == {
        "line": 5,
        "character": 0,
    }


JOINED = """shape Order:
    id: Int
    customer_id: Int | None
    amount: Int
shape Customer:
    id: Int
    name: Text
source orders: Order = postgres.table("shop.orders")
source customers: Customer = postgres.table("shop.customers")
relationship order_customer(order: Order, customer: Customer):
    order.customer_id == customer.id
def double(x: Int) -> Int: return x * 2

query order_names:
    from orders
    let customer = customers
    inner join customer on order_customer(orders, customer)
    select:
        order_id = orders.id
        customer_name = customer.name

query plain:
    from orders
    let twice = double(amount)
    where twice > id
    select:
        id
        twice
"""


def _field_and_call_uses(text: str) -> list[tuple[object, ...]]:
    diagnostics, facts = _lsp._check_text_with_editor_facts(text)
    assert diagnostics == ()
    return [
        (
            (use.location.line, use.location.column, use.location.end_column),
            use.detail,
            None
            if use.target is None
            else (use.target.location.line, use.target.location.column),
        )
        for use in facts.uses
        if use.detail.startswith(("field ", "relationship "))
    ]


def test_single_file_join_field_reads_and_relationship_calls_define_their_targets(
    tmp_path: Path,
) -> None:
    """A JOIN relation's field read defines the source's shape field and a
    relationship call its template, one fact per authored occurrence; the
    reads that expanding the call adds, a read outside a JOIN, a let use, a
    def call and a relationship parameter have none."""

    assert _field_and_call_uses(JOINED) == [
        ((19, 20, 29), "field id", (2, 5)),
        ((20, 25, 38), "field name", (7, 5)),
        ((17, 28, 42), "relationship order_customer", (10, 1)),
    ]
    for count in (1, 6):
        repeated = JOINED.replace(
            "        customer_name = customer.name\n",
            "".join(f"        n{item} = customer.name\n" for item in range(count)),
        )
        uses = _field_and_call_uses(repeated)
        assert [detail for _, detail, _ in uses].count("field name") == count
        assert len(uses) == count + 2
    uri = (tmp_path / "joined.pietto").as_uri()
    positions = [(19, 30), (16, 30), (16, 45), (10, 6), (23, 25), (23, 18)]
    positions += [(24, 12), (26, 9)]
    messages = session(
        init(),
        [opened(uri, JOINED, 1)],
        [
            request(number, method, uri, line, character)
            for index, (line, character) in enumerate(positions)
            for number, method in (
                (2 * index + 1, "textDocument/hover"),
                (2 * index + 2, "textDocument/definition"),
            )
        ],
    )
    assert publishes(messages, uri)[-1]["diagnostics"] == []
    assert response(messages, 1)["result"]["contents"]["value"] == "field name"
    assert response(messages, 2)["result"] == {
        "uri": uri,
        "range": {
            "start": {"line": 6, "character": 4},
            "end": {"line": 6, "character": 14},
        },
    }
    assert (
        response(messages, 3)["result"]["contents"]["value"]
        == "relationship order_customer"
    )
    assert response(messages, 4)["result"]["range"]["start"] == {
        "line": 9,
        "character": 0,
    }
    assert [response(messages, number)["result"] for number in range(5, 17)] == [
        None
    ] * 12


@pytest.mark.parametrize("ending", ["\r\n", "\r"], ids=["crlf", "cr"])
def test_definition_ranges_keep_utf16_bom_and_astral_coordinates(
    tmp_path: Path, ending: str
) -> None:
    source_line = 'source users: User = postgres.table("\U0001f600")'
    text = "\ufeff" + ending.join(
        (
            "shape User:",
            "    id: Int",
            "",
            source_line,
            "",
            "table rows:",
            "    from users",
            "    select id",
            "",
        )
    )
    uri = (tmp_path / "coordinates.pietto").as_uri()
    messages = session(
        init(),
        [opened(uri, text, 1)],
        [request(1, "textDocument/definition", uri, 6, 9)],
    )
    assert response(messages, 1)["result"] == {
        "uri": uri,
        "range": {
            "start": {"line": 3, "character": 0},
            "end": {
                "line": 3,
                "character": len(source_line.encode("utf-16-le")) // 2,
            },
        },
    }


def test_closed_and_noncanonical_request_uris_have_no_editor_snapshot(
    tmp_path: Path,
) -> None:
    text = "shape User:\n    id: Int\n"
    uri = (tmp_path / "shape.pietto").as_uri()
    other = f"{tmp_path.as_uri()}/./shape.pietto"
    messages = session(
        init(),
        [opened(uri, text, 1)],
        [
            request(1, "textDocument/documentSymbol", other),
            closed(uri),
            request(2, "textDocument/documentSymbol", uri),
        ],
    )
    assert response(messages, 1)["result"] == []
    assert response(messages, 2)["result"] == []


def test_editor_request_does_not_start_a_second_analysis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    text = """shape User:
    id: Int

source users: User = postgres.table("users")

table rows:
    from users
    select id
"""
    uri = (tmp_path / "shape.pietto").as_uri()
    script = Script()
    real = _lsp._check_text_with_editor_facts

    def checked(value: str, *, path: str | None = None) -> object:
        result = real(value, path=path)
        monkeypatch.setattr(
            _lsp,
            "_check_text_with_editor_facts",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("second analysis")
            ),
        )
        return result

    monkeypatch.setattr(_lsp, "_check_text_with_editor_facts", checked)
    messages = session(
        init(),
        [opened(uri, text, 1), request(1, "textDocument/hover", uri, 1, 8)],
        [
            request(2, "textDocument/definition", uri, 6, 9),
            request(3, "textDocument/documentSymbol", uri),
        ],
        script=script,
    )
    assert response(messages, 1)["result"]["contents"]["value"] == "builtin Int"
    assert response(messages, 2)["result"]["uri"] == uri
    assert response(messages, 3)["result"][0]["name"] == "User"


@pytest.mark.parametrize("project_mode", [False, True], ids=["single", "project"])
def test_navigation_targets_use_the_unique_open_uri(
    tmp_path: Path, project_mode: bool
) -> None:
    text = """shape User:
    id: Int

source users: User = postgres.table("public.users")

table rows:
    from users
    select id
"""
    if project_mode:
        root = project(tmp_path, models=MODELS, a=A_OK)
        target_uri = f"{root.as_uri()}/./models.pietto"
        source_uri = (root / "a.pietto").as_uri()
        initialization = init(root)
        opened_documents = [opened(target_uri, MODELS, 1), opened(source_uri, A_OK, 1)]
        source_line = 5
    else:
        target_uri = source_uri = f"{tmp_path.as_uri()}/./single.pietto"
        initialization = init()
        opened_documents = [opened(source_uri, text, 1)]
        source_line = 6
    messages = session(
        initialization,
        opened_documents,
        [
            request(1, "textDocument/definition", source_uri, source_line, 9),
            request(2, "textDocument/documentSymbol", target_uri),
        ],
    )
    assert response(messages, 1)["result"]["uri"] == target_uri
    symbols = response(messages, 2)["result"]
    assert symbols
    assert all(item["location"]["uri"] == target_uri for item in symbols)


@pytest.mark.parametrize("project_mode", [False, True], ids=["single", "project"])
def test_alias_hover_shows_the_canonical_type_and_defines_the_alias(
    tmp_path: Path, project_mode: bool
) -> None:
    text = """type Email = Text
type Contact = Email

shape User:
    contact: Contact
"""
    if project_mode:
        root = project(tmp_path, models=text)
        uri = (root / "models.pietto").as_uri()
        initialization = init(root)
    else:
        uri = (tmp_path / "models.pietto").as_uri()
        initialization = init()
    messages = session(
        initialization,
        [opened(uri, text, 1)],
        [
            request(1, "textDocument/hover", uri, 4, 13),
            request(2, "textDocument/definition", uri, 4, 13),
        ],
    )
    assert response(messages, 1)["result"]["contents"]["value"] == "builtin Text"
    assert response(messages, 2)["result"] == {
        "uri": uri,
        "range": {
            "start": {"line": 1, "character": 0},
            "end": {"line": 1, "character": 20},
        },
    }


def test_project_definition_uses_the_exact_imported_relation_occurrence(
    tmp_path: Path,
) -> None:
    root = project(tmp_path, models=MODELS, a=A_OK)
    a_uri = (root / "a.pietto").as_uri()
    models_uri = (root / "models.pietto").as_uri()
    messages = session(
        init(root),
        [],
        [opened(a_uri, A_OK, 1), request(1, "textDocument/definition", a_uri, 5, 9)],
    )
    assert response(messages, 1)["result"] == {
        "uri": models_uri,
        "range": {
            "start": {"line": 5, "character": 0},
            "end": {"line": 5, "character": 51},
        },
    }


def test_project_type_definition_and_capability_response_shapes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = project(tmp_path, models=MODELS, a=A_OK)
    models_uri = (root / "models.pietto").as_uri()
    script = Script()
    real = _lsp.check_project_editor_diagnostics
    later = [request(4, "textDocument/documentSymbol", models_uri)]

    def checking(root: str | Path, *, overlays: Mapping[str, str]) -> object:
        # A request on another module, received while the root analysis
        # that the edit of a.pietto schedules runs, waits for it.
        if "a.pietto" in overlays:
            script.batches[0].extend(later)
            later.clear()
        return real(root, overlays=overlays)

    monkeypatch.setattr(_lsp, "check_project_editor_diagnostics", checking)
    messages = session(
        init(root, plaintext_hover=True, hierarchical_symbols=True),
        [],
        [
            opened((root / "a.pietto").as_uri(), A_OK, 1),
            request(1, "textDocument/hover", models_uri, 1, 8),
            request(2, "textDocument/definition", models_uri, 1, 8),
            request(3, "textDocument/documentSymbol", models_uri),
        ],
        script=script,
    )
    assert later == []
    assert response(messages, 4)["result"] == response(messages, 3)["result"]
    assert response(messages, 1)["result"] == {
        "contents": {"kind": "plaintext", "value": "builtin UUID"},
        "range": {
            "start": {"line": 1, "character": 8},
            "end": {"line": 1, "character": 12},
        },
    }
    assert response(messages, 2)["result"] is None
    symbols = response(messages, 3)["result"]
    assert [symbol["name"] for symbol in symbols] == ["User", "users"]
    assert all("selectionRange" in symbol for symbol in symbols)


def test_project_definition_keeps_the_reexported_alias_target_occurrence(
    tmp_path: Path,
) -> None:
    a = """from "models.pietto" import (
    source users as local_users,
)

export (
    source local_users,
)
"""
    b = """from "a.pietto" import (
    source local_users as again,
)

table rows:
    from again
    select id
"""
    root = project(tmp_path, models=MODELS, a=a, b=b)
    b_uri = (root / "b.pietto").as_uri()
    messages = session(
        init(root),
        [],
        [opened(b_uri, b, 1)],
        [request(1, "textDocument/definition", b_uri, 5, 9)],
    )
    assert response(messages, 1)["result"] == {
        "uri": (root / "models.pietto").as_uri(),
        "range": {
            "start": {"line": 5, "character": 0},
            "end": {"line": 5, "character": 51},
        },
    }


def test_project_type_definition_keeps_the_reexported_alias_target_occurrence(
    tmp_path: Path,
) -> None:
    models = """shape Row:
    id: Int

export (
    shape Row,
)
"""
    a = """from "models.pietto" import (
    shape Row as Local,
)

export (
    shape Local,
)
"""
    b = """from "a.pietto" import (
    shape Local as Remote,
)

shape Wrapper:
    value: Remote
"""
    root = project(tmp_path, models=models, a=a, b=b)
    b_uri = (root / "b.pietto").as_uri()
    messages = session(
        init(root),
        [],
        [opened(b_uri, b, 1)],
        [request(1, "textDocument/definition", b_uri, 5, 12)],
    )
    assert response(messages, 1)["result"] == {
        "uri": (root / "models.pietto").as_uri(),
        "range": {
            "start": {"line": 0, "character": 0},
            "end": {"line": 1, "character": 11},
        },
    }


def test_legacy_flat_root_modules_have_no_editor_facts(tmp_path: Path) -> None:
    flat = MODELS.split("\nexport (")[0]
    root = project(tmp_path, models=flat)
    (root / "pietto.toml").write_text(
        TOML.replace("schema_version = 2", "schema_version = 1"), encoding="utf-8"
    )
    uri = (root / "models.pietto").as_uri()
    requests = [
        request(1, "textDocument/documentSymbol", uri),
        request(2, "textDocument/hover", uri, 1, 8),
    ]
    messages = session(init(root), [opened(uri, flat, 1)], requests)
    assert publishes(messages, uri)[-1]["diagnostics"] == []
    assert response(messages, 1)["result"] == []
    assert response(messages, 2)["result"] is None
    # Checked alone, this self-contained text has these facts, so the
    # legacy-flat root is what leaves them out.
    alone = session(init(), [opened(uri, flat, 1)], requests)
    assert [item["name"] for item in response(alone, 1)["result"]] == ["User", "users"]
    assert response(alone, 2)["result"]["contents"]["value"] == "builtin UUID"


def test_partial_project_omissions_have_no_editor_snapshot(tmp_path: Path) -> None:
    root = project(
        tmp_path,
        models=MODELS.replace("id: UUID", "id UUID"),
        a=A_OK,
        b="shape Standalone:\n    id: Int\n",
    )
    a_uri = (root / "a.pietto").as_uri()
    b_uri = (root / "b.pietto").as_uri()
    messages = session(
        init(root),
        [],
        [
            request(1, "textDocument/documentSymbol", a_uri),
            request(2, "textDocument/documentSymbol", b_uri),
            request(3, "textDocument/documentLink", a_uri),
        ],
    )
    assert response(messages, 1)["result"] == []
    assert [item["name"] for item in response(messages, 2)["result"]] == ["Standalone"]
    assert response(messages, 3)["result"] == []


def test_a_semantic_error_leaves_other_modules_their_editor_facts(
    tmp_path: Path,
) -> None:
    # A semantic error stops no check: each module without an error of its
    # own keeps its facts, but no use navigates into a module with an error.
    # y's Email resolves through x to w's unknown base, so that use has no
    # fact although x and y have no error of their own.
    base = "type Base = Nope\n\nexport (\n    type Base,\n)\n"
    alias = """from "w.pietto" import (
    type Base,
)

type Email = Base

export (
    type Email,
)
"""
    use = """from "x.pietto" import (
    type Email,
)

shape Row:
    email: Email
"""
    copied = """from "a.pietto" import (
    table active_users,
)

table copied:
    from active_users
    select:
        id
"""
    root = project(
        tmp_path,
        models=MODELS,
        a=A_BAD + "\nexport (\n    table active_users,\n)\n",
        b=A_OK.replace("active_users", "emails"),
        c=copied,
        w=base,
        x=alias,
        y=use,
    )
    models_uri = (root / "models.pietto").as_uri()
    c_uri = (root / "c.pietto").as_uri()
    y_uri = (root / "y.pietto").as_uri()
    messages = session(
        init(root),
        [],
        [
            request(1, "textDocument/documentSymbol", models_uri),
            request(2, "textDocument/definition", (root / "b.pietto").as_uri(), 5, 9),
            request(3, "textDocument/documentSymbol", (root / "a.pietto").as_uri()),
            request(4, "textDocument/hover", y_uri, 5, 12),
            request(5, "textDocument/definition", y_uri, 5, 12),
            request(6, "textDocument/documentSymbol", y_uri),
            request(7, "textDocument/hover", c_uri, 5, 9),
            request(8, "textDocument/definition", c_uri, 5, 9),
            request(9, "textDocument/documentSymbol", c_uri),
        ],
    )
    assert [item["name"] for item in response(messages, 1)["result"]] == [
        "User",
        "users",
    ]
    assert response(messages, 2)["result"] == {
        "uri": models_uri,
        "range": {
            "start": {"line": 5, "character": 0},
            "end": {"line": 5, "character": 51},
        },
    }
    assert response(messages, 3)["result"] == []
    assert response(messages, 4)["result"] is None
    assert response(messages, 5)["result"] is None
    assert [item["name"] for item in response(messages, 6)["result"]] == ["Row"]
    # c reads a's exported table exactly, but a has an error of its own.
    assert response(messages, 7)["result"] is None
    assert response(messages, 8)["result"] is None
    assert [item["name"] for item in response(messages, 9)["result"]] == ["copied"]


def test_a_target_open_under_two_uris_has_no_hover_or_definition(
    tmp_path: Path,
) -> None:
    root = project(tmp_path, models=MODELS, a=A_OK)
    a_uri = (root / "a.pietto").as_uri()
    models_uri = (root / "models.pietto").as_uri()
    alias_uri = f"{root.as_uri()}/./models.pietto"
    messages = session(
        init(root),
        [],
        [
            opened(a_uri, A_OK, 1),
            opened(models_uri, MODELS, 1),
            opened(alias_uri, MODELS, 1),
        ],
        [
            request(1, "textDocument/definition", a_uri, 5, 9),
            request(2, "textDocument/hover", a_uri, 5, 9),
        ],
    )
    assert response(messages, 1)["result"] is None
    assert response(messages, 2)["result"] is None


def test_an_unselected_file_open_under_two_uris_navigates_in_each_buffer(
    tmp_path: Path,
) -> None:
    text = """shape User:
    id: Int

source users: User = postgres.table("public.users")

table rows:
    from users
    select id
"""
    plain = (tmp_path / "rows.pietto").as_uri()
    other = f"{tmp_path.as_uri()}/./rows.pietto"
    messages = session(
        init(),
        [opened(plain, text, 1), opened(other, "\n\n" + text, 1)],
        [
            request(1, "textDocument/definition", plain, 6, 9),
            request(2, "textDocument/definition", other, 8, 9),
            request(3, "textDocument/hover", other, 8, 9),
        ],
    )
    # No root selects the file, so each URI is checked as its own file and
    # gets its own diagnostics, not the URI conflict.
    for uri in (plain, other):
        assert publishes(messages, uri) == [
            {"uri": uri, "diagnostics": [], "version": 1}
        ]
    assert response(messages, 1)["result"] == {
        "uri": plain,
        "range": {
            "start": {"line": 3, "character": 0},
            "end": {"line": 3, "character": 51},
        },
    }
    assert response(messages, 2)["result"] == {
        "uri": other,
        "range": {
            "start": {"line": 5, "character": 0},
            "end": {"line": 5, "character": 51},
        },
    }
    assert response(messages, 3)["result"]["contents"]["value"] == "source users"


def test_target_omitted_on_a_later_root_analysis_has_no_stale_definition(
    tmp_path: Path,
) -> None:
    root = project(tmp_path, models=MODELS, a=A_OK)
    a_uri = (root / "a.pietto").as_uri()
    models_uri = (root / "models.pietto").as_uri()
    broken = MODELS.replace("id: UUID", "id UUID")
    messages = session(
        init(root),
        [],
        [request(1, "textDocument/definition", a_uri, 5, 9)],
        [opened(models_uri, broken, 2)],
        [request(2, "textDocument/definition", a_uri, 5, 9)],
    )
    assert response(messages, 1)["result"]["uri"] == models_uri
    assert response(messages, 2)["result"] is None


def symbols(request_id: int, query: object) -> Message:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "workspace/symbol",
        "params": {"query": query},
    }


def test_workspace_symbols_list_every_retained_declaration_in_order(
    tmp_path: Path,
) -> None:
    """Every root in `projectRoots` order with its modules in selection
    order, then every document checked as its own file in URI code-point
    order: each lists exactly its flat document symbols, under the URI they
    carry, with no name, path or text deduplicated."""

    root = project(tmp_path, models=MODELS, a=A_OK, b="shape User:\n    id: Int\n")
    other = project(tmp_path, "other", models=MODELS)
    alias = f"{root.as_uri()}/./models.pietto"
    loose = (tmp_path / "loose.pietto").as_uri()
    loose_alias = f"{tmp_path.as_uri()}/./loose.pietto"
    untitled = "untitled:Untitled-1"
    # U+212A KELVIN SIGN, which Unicode lowers to k, is no ASCII letter.
    queries = ["", "AcUs", "zd", "uSeRs", "ua", "\u212a"]
    documents = [
        (root / "a.pietto").as_uri(),
        (root / "b.pietto").as_uri(),
        alias,
        (other / "models.pietto").as_uri(),
        loose_alias,
        loose,
        untitled,
    ]
    messages = session(
        init(root, other),
        [],
        [
            opened(untitled, "shape Zed:\n    id: Int\n"),
            opened(loose, "shape Lock:\n    id: Int\n"),
            opened(loose_alias, "shape Lock:\n    id: Int\n"),
            opened(alias, MODELS),
        ],
        [
            *(symbols(number, query) for number, query in enumerate(queries, 1)),
            *(
                request(number, "textDocument/documentSymbol", uri)
                for number, uri in enumerate(documents, 10)
            ),
        ],
    )
    listed = response(messages, 1)["result"]
    assert [
        (item["location"]["uri"], item["name"], item["kind"]) for item in listed
    ] == [
        (documents[0], "active_users", 5),
        (documents[1], "User", 5),
        (alias, "User", 5),
        (alias, "users", 13),
        (documents[3], "User", 5),
        (documents[3], "users", 13),
        (loose_alias, "Lock", 5),
        (loose, "Lock", 5),
        (untitled, "Zed", 5),
    ]
    for number, uri in enumerate(documents, 10):
        flat = response(messages, number)["result"]
        assert flat
        assert [item for item in listed if item["location"]["uri"] == uri] == flat
    # The characters of the query appear in order, an ASCII letter in either
    # case; no other letter is folded.
    assert [
        [item["name"] for item in response(messages, number)["result"]]
        for number in range(2, len(queries) + 1)
    ] == [["active_users"], ["Zed"], ["active_users", "users", "users"], [], []]


def test_workspace_symbols_leave_out_documents_without_facts(tmp_path: Path) -> None:
    """A failed or omitted module, one with an error of its own, a
    legacy-flat root, a refused document, a module open under two URIs and a
    module that two roots select list nothing, under no root; once the URI
    conflict and the refusal end, both list again."""

    root = project(
        tmp_path,
        models=MODELS.replace("id: UUID", "id UUID"),
        a=A_OK,
        b="shape Standalone:\n    id: Int\n",
        c="shape Bad:\n    id: Nope\n",
        d="shape Twice:\n    id: Int\n",
    )
    flat = project(tmp_path, "flat", models=MODELS.split("\nexport (")[0])
    (flat / "pietto.toml").write_text(
        TOML.replace("schema_version = 2", "schema_version = 1"), encoding="utf-8"
    )
    outer = project(tmp_path, "port", top="shape Top:\n    id: Int\n")
    (outer / "pietto.toml").write_text(
        TOML.replace('"*.pietto"', '"**/*.pietto"'), encoding="utf-8"
    )
    project(outer, "sub", models=MODELS)
    d_uri, d_alias = (root / "d.pietto").as_uri(), f"{root.as_uri()}/./d.pietto"
    refused = (tmp_path / "refused.pietto").as_uri()
    messages = session(
        init(root, flat, outer, outer / "sub"),
        [
            opened(d_uri, "shape Twice:\n    id: Int\n"),
            opened(d_alias, "shape Twice:\n    id: Int\n"),
            opened(refused, "shape Refused:\n    id: Int\n", 1),
        ],
        [changed(refused, "shape Refused:\n    id: Int\n", 2, ranged=True)],
        [symbols(1, "")],
        [closed(d_alias), opened(refused, "shape Reopened:\n    id: Int\n", 3)],
        [symbols(2, "")],
    )
    names = [[item["name"] for item in response(messages, n)["result"]] for n in (1, 2)]
    # port and port/sub both select sub/models.pietto, so neither root lists
    # its User or users, while port keeps top.pietto's Top.
    assert names == [
        ["Standalone", "Top"],
        ["Standalone", "Twice", "Top", "Reopened"],
    ]


def test_workspace_symbols_and_links_wait_and_call_no_analysis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A workspace symbol request waits while any analysis is pending, even
    of a unit outside every root, and a link request as the other requests
    on its document do. Answering either calls no analysis entry point;
    shutdown answers a waiting one with no items, and malformed parameters
    and resolve requests are errors."""

    root = project(tmp_path, models=MODELS, a=A_OK)
    a_uri, alone = (root / "a.pietto").as_uri(), (tmp_path / "x.pietto").as_uri()
    script = Script()
    real = _lsp._check_text_with_editor_facts
    inside: list[str] = []

    def checking(text: str, *, path: str | None = None) -> object:
        # A request received while this analysis runs waits for it.
        script.batches[0].append(symbols(3, ""))
        return real(text, path=path)

    def guard(owner: object, name: str) -> None:
        wrapped = getattr(owner, name)

        def guarded(*args: Any, **kwargs: Any) -> object:
            assert not inside, f"{name} while answering"
            return wrapped(*args, **kwargs)

        monkeypatch.setattr(owner, name, guarded)

    def answering(name: str) -> None:
        wrapped = getattr(_lsp._Server, name)

        def answer(*args: Any, **kwargs: Any) -> object:
            inside.append(name)
            try:
                return wrapped(*args, **kwargs)
            finally:
                inside.pop()

        monkeypatch.setattr(_lsp._Server, name, answer)

    monkeypatch.setattr(_lsp, "_check_text_with_editor_facts", checking)
    for name in (
        "_check_text_with_editor_facts",
        "check_project_editor_diagnostics",
        "selected_project_paths",
        "parse_source",
        "analyze",
        "format_source",
    ):
        guard(_lsp, name)
    for name in ("_touch", "_analyse"):
        guard(_lsp._Server, name)
    for name in ("_answer", "_answer_symbols"):
        answering(name)
    messages = session(
        init(root),
        [
            opened(a_uri, A_OK),
            opened(alone, "shape Alone:\n    id: Int\n"),
            symbols(1, ""),
            request(2, "textDocument/documentLink", a_uri),
        ],
        [
            symbols(4, 7),
            {"jsonrpc": "2.0", "id": 5, "method": "workspace/symbol"},
            {**request(6, "textDocument/documentLink", a_uri), "params": {}},
            {"jsonrpc": "2.0", "id": 7, "method": "workspaceSymbol/resolve"},
            {"jsonrpc": "2.0", "id": 8, "method": "documentLink/resolve"},
        ],
        script=script,
    )
    order = [item.get("id", item.get("params", {}).get("uri")) for item in messages]
    # The link request waits only for its root; the symbol requests also for
    # the file outside it.
    assert order.index(a_uri) < order.index(2) < order.index(alone)
    assert order.index(alone) < order.index(1) < order.index(3)
    everything = response(messages, 1)["result"]
    assert [item["name"] for item in everything] == [
        "active_users",
        "User",
        "users",
        "Alone",
    ]
    assert response(messages, 3)["result"] == everything
    assert response(messages, 2)["result"] == [
        {
            "range": {
                "start": {"line": 0, "character": 5},
                "end": {"line": 0, "character": 20},
            },
            "target": (root / "models.pietto").as_uri(),
        }
    ]
    assert [response(messages, n)["error"]["code"] for n in (4, 5, 6, 7, 8)] == [
        -32602,
        -32602,
        -32602,
        -32601,
        -32601,
    ]
    script = Script(
        [init(root), notify("initialized")],
        [
            opened(a_uri, A_OK),
            symbols(1, ""),
            request(2, "textDocument/documentLink", a_uri),
            SHUTDOWN,
        ],
        [EXIT],
    )
    out = io.BytesIO()
    assert _lsp._Server(script, out, "test").run() == 0
    answers = [item for item in frames(out.getvalue()) if "id" in item]
    assert [(item["id"], item["result"]) for item in answers[1:]] == [
        (1, []),
        (2, []),
        (99, None),
    ]


def test_import_paths_link_to_the_exact_module_of_the_same_analysis(
    tmp_path: Path,
) -> None:
    """Each import statement of a module with facts links, at its path, to
    the module whose path the import names, under that module's URI, even
    when that module has an error of its own. A module with an error of its
    own and a single file have none, and none leads to a module open under
    two URIs, one whose change was refused until it reopens, or one that two
    roots select."""

    exported = A_OK + "\nexport (\n    table active_users,\n)\n"
    b = """from "a.pietto" import (
    table active_users,
)

from "models.pietto" import (
    shape User,
    source users,
)

from "models.pietto" import (
    source users as again,
)

table copied:
    from active_users
    select:
        id
"""
    base = "type Base = Nope\n\nexport (\n    type Base,\n)\n"
    alias = 'from "w.pietto" import (\n    type Base,\n)\n\ntype Email = Base\n'
    root = project(
        tmp_path,
        models=MODELS,
        a=exported,
        b=b,
        c=A_BAD.replace("active_users", "emails"),
        w=base,
        x=alias,
    )
    models_alias = f"{root.as_uri()}/./models.pietto"
    a_uri, b_uri = (root / "a.pietto").as_uri(), (root / "b.pietto").as_uri()
    single = "untitled:Untitled-1"
    single_text = 'from "models.pietto" import (\n    shape User,\n)\n\nshape Row:\n'
    single_text += "    id: Int\n"

    def link(line: int, end: int, target: str) -> Message:
        return {
            "range": {
                "start": {"line": line, "character": 5},
                "end": {"line": line, "character": end},
            },
            "target": target,
        }

    messages = session(
        init(root),
        [opened(models_alias, MODELS), opened(single, single_text)],
        [
            request(1, "textDocument/documentLink", b_uri),
            request(2, "textDocument/documentLink", (root / "x.pietto").as_uri()),
            request(3, "textDocument/documentLink", (root / "c.pietto").as_uri()),
            request(4, "textDocument/documentLink", models_alias),
            request(5, "textDocument/documentLink", f"{root.as_uri()}/./b.pietto"),
            request(6, "textDocument/documentLink", single),
            request(7, "textDocument/documentSymbol", single),
        ],
        [opened(a_uri, exported), opened(f"{root.as_uri()}/./a.pietto", exported)],
        [request(8, "textDocument/documentLink", b_uri)],
        [
            closed(f"{root.as_uri()}/./a.pietto"),
            changed(models_alias, MODELS, 2, ranged=True),
        ],
        [
            request(9, "textDocument/documentLink", b_uri),
            request(10, "textDocument/documentSymbol", b_uri),
        ],
        [opened(models_alias, MODELS, 3)],
        [request(11, "textDocument/documentLink", b_uri)],
    )
    # One link per statement, whatever its items, and one per statement that
    # names the same module.
    to_models = [link(4, 20, models_alias), link(9, 20, models_alias)]
    assert response(messages, 1)["result"] == [link(0, 15, a_uri), *to_models]
    # w has an error of its own, which leaves the link to it.
    w_uri = (root / "w.pietto").as_uri()
    assert response(messages, 2)["result"] == [link(0, 15, w_uri)]
    assert [response(messages, n)["result"] for n in (3, 4, 5, 6)] == [[]] * 4
    # The single file has facts but resolves no import (PIE-S2708 warns).
    assert [item["name"] for item in response(messages, 7)["result"]] == ["Row"]
    # Once a.pietto is open under two URIs, no link leads there.
    assert response(messages, 8)["result"] == to_models
    # Nor, until it reopens, to models.pietto once its change is refused,
    # though b keeps its facts.
    assert response(messages, 9)["result"] == [link(0, 15, a_uri)]
    assert [item["name"] for item in response(messages, 10)["result"]] == ["copied"]
    assert response(messages, 11)["result"] == [link(0, 15, a_uri), *to_models]

    top = """from "sub/models.pietto" import (
    shape User,
)

from "local.pietto" import (
    shape Local,
)
"""
    local = "shape Local:\n    id: Int\n\nexport (\n    shape Local,\n)\n"
    outer = project(tmp_path, "port", top=top, local=local)
    (outer / "pietto.toml").write_text(
        TOML.replace('"*.pietto"', '"**/*.pietto"'), encoding="utf-8"
    )
    project(outer, "sub", models=MODELS)
    messages = session(
        init(outer, outer / "sub"),
        [],
        [request(1, "textDocument/documentLink", (outer / "top.pietto").as_uri())],
    )
    # Two roots select sub/models.pietto, so only the other import links.
    assert response(messages, 1)["result"] == [
        link(4, 19, (outer / "local.pietto").as_uri())
    ]


def test_workspace_symbols_and_links_keep_percent_encoded_and_non_ascii_uris(
    tmp_path: Path,
) -> None:
    """Under a root whose path holds a space and a non-ASCII letter, symbols
    and link targets name a closed module by its file URI as
    `Path.as_uri()` escapes it. Once the client opens the modules under
    another spelling of their paths, with lower-case escapes, both name each
    module by the client's URI."""

    root = project(tmp_path, "bay é", models=MODELS, a=A_OK)
    a_file, models_file = (
        (root / "a.pietto").as_uri(),
        (root / "models.pietto").as_uri(),
    )
    assert "/bay%20%C3%A9/" in a_file
    a_open, models_open = (
        uri.replace("%C3%A9", "%c3%a9") for uri in (a_file, models_file)
    )

    def located(result: list[Message]) -> list[tuple[str, str]]:
        return [(item["location"]["uri"], item["name"]) for item in result]

    def link(target: str) -> list[Message]:
        start, end = {"line": 0, "character": 5}, {"line": 0, "character": 20}
        return [{"range": {"start": start, "end": end}, "target": target}]

    messages = session(
        init(root),
        [],
        [symbols(1, ""), request(2, "textDocument/documentLink", a_file)],
        [opened(models_open, MODELS), opened(a_open, A_OK)],
        [symbols(3, ""), request(4, "textDocument/documentLink", a_open)],
    )
    assert located(response(messages, 1)["result"]) == [
        (a_file, "active_users"),
        (models_file, "User"),
        (models_file, "users"),
    ]
    assert response(messages, 2)["result"] == link(models_file)
    assert located(response(messages, 3)["result"]) == [
        (a_open, "active_users"),
        (models_open, "User"),
        (models_open, "users"),
    ]
    assert response(messages, 4)["result"] == link(models_open)


def formatting(request_id: int, uri: object, **options: object) -> Message:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "textDocument/formatting",
        "params": {
            "textDocument": {"uri": uri},
            "options": options or {"tabSize": 4, "insertSpaces": True},
        },
    }


def offset(text: str, position: Mapping[str, int]) -> int:
    """The index in `text` of an LSP position, as a client counts it: lines
    end at CRLF, CR or LF, and an astral character takes two UTF-16 units."""

    starts = [0, *(item.end() for item in re.finditer(r"\r\n|\r|\n", text))]
    index, units = starts[position["line"]], 0
    while units < position["character"]:
        units += 2 if ord(text[index]) > 0xFFFF else 1
        index += 1
    return index


def applied(text: str, edits: list[Message]) -> str:
    """The buffer once a client applies `edits`, last first."""

    for edit in reversed(edits):
        start, end = (offset(text, edit["range"][key]) for key in ("start", "end"))
        text = text[:start] + edit["newText"] + text[end:]
    return text


def test_formatting_edits_the_buffer_into_the_bytes_fmt_prints(
    tmp_path: Path, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    """Over the fmt corpus, as written and with its layout spoiled, and two
    sources fmt refuses, the one edit turns the open buffer into what
    `pietto fmt` prints for the same bytes; `[]` answers a file fmt leaves
    alone, and no result one it refuses. Each buffer closes before any
    analysis runs."""

    refused = ["shape A:\n\tid: Int\n", "pietto 1\nshape A:\n  id: Int\n"]
    buffers: list[tuple[Path, str]] = []
    for number, path in enumerate(FORMAT_CORPUS):
        text = path.read_bytes().decode("utf-8")
        spoiled = re.sub(r"(?m)^( +)", r"\1\1", text).replace("\n", "  \r\n")
        for name, value in (("written", text), ("spoiled", spoiled)):
            buffers.append((tmp_path / f"{number}-{name}-{path.name}", value))
    buffers += [(tmp_path / f"refused-{n}.pietto", v) for n, v in enumerate(refused)]
    for copy, value in buffers:
        copy.write_bytes(value.encode("utf-8"))
    batch: list[object] = []
    for number, (copy, value) in enumerate(buffers, start=1):
        batch += [opened(copy.as_uri(), value), formatting(number, copy.as_uri())]
        batch.append(closed(copy.as_uri()))
    messages = session(init(), batch)
    assert publishes(messages) == []
    outcomes: set[str] = set()
    for number, (copy, value) in enumerate(buffers, start=1):
        code = cli.main(["fmt", str(copy)])
        printed = capsysbinary.readouterr().out
        result = response(messages, number)["result"]
        if code != 0:
            assert (result, printed) == (None, b"")
            outcomes.add("refused")
        elif printed == value.encode("utf-8"):
            assert result == []
            outcomes.add("unchanged")
        else:
            (edit,) = result
            assert edit["range"]["start"] == {"line": 0, "character": 0}
            assert offset(value, edit["range"]["end"]) == len(value)
            assert applied(value, result).encode("utf-8") == printed
            outcomes.add("changed")
    assert outcomes == {"refused", "unchanged", "changed"}


@pytest.mark.parametrize(
    ("text", "end"),
    [
        pytest.param("\ufeff# \U0001d11e  ", (0, 7), id="bom_on_the_one_line"),
        pytest.param("shape A:\r\n  id: Int  # \U0001d11e\r\n", (2, 0), id="crlf"),
        pytest.param("shape A:\r  id: Int  # \U0001d11e", (1, 15), id="lone_cr"),
        pytest.param("\ufeffshape A:\n  id: Int  # \xe9\U0001d11e", (1, 16), id="lf"),
    ],
)
def test_a_formatting_edit_ends_at_the_utf16_end_of_the_buffer(
    text: str, end: tuple[int, int]
) -> None:
    uri = "untitled:Untitled-1"
    messages = session(init(), [opened(uri, text), formatting(1, uri), closed(uri)])
    (edit,) = response(messages, 1)["result"]
    assert edit["range"] == {
        "start": {"line": 0, "character": 0},
        "end": {"line": end[0], "character": end[1]},
    }
    assert offset(text, edit["range"]["end"]) == len(text)
    assert applied(text, [edit]) == source_format.format_source(text).source


def test_formatting_reads_only_the_open_buffer_and_writes_nothing(
    tmp_path: Path,
) -> None:
    path = tmp_path / "a.pietto"
    path.write_bytes(b"shape A:\n  id: Int\n")
    uri, untitled = path.as_uri(), "untitled:Untitled-1"
    buffer = "shape B:\n  name: Text\n"
    formatted = "shape B:\n    name: Text\n"
    messages = session(
        init(),
        [
            formatting(1, uri),
            opened(uri, buffer),
            formatting(2, uri),
            formatting(3, uri, tabSize=2, insertSpaces=False, trimFinalNewlines=False),
            opened(untitled, buffer),
            formatting(4, untitled),
            changed(uri, formatted, 2),
            formatting(5, uri),
        ],
        [closed(uri), formatting(6, uri)],
    )
    edit = {
        "range": {
            "start": {"line": 0, "character": 0},
            "end": {"line": 2, "character": 0},
        },
        "newText": formatted,
    }
    # The options change nothing: fmt has one layout.
    assert [response(messages, number)["result"] for number in range(1, 7)] == [
        None,
        [edit],
        [edit],
        [edit],
        [],
        None,
    ]
    assert path.read_bytes() == b"shape A:\n  id: Int\n"


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("shape A:\n\tid: Int\n", id="parse_error"),
        pytest.param("pietto 1\nshape A:\n  id: Int\n", id="header_line"),
        pytest.param("# " + "x" * 1_048_576 + "\nshape A:\n  id: Int\n", id="size"),
        pytest.param("shape A:\n  id: Int  # \ud800\n", id="unpaired_surrogate"),
    ],
)
def test_formatting_has_no_result_for_a_buffer_fmt_would_refuse(text: str) -> None:
    uri = "untitled:Untitled-1"
    whole = "shape A:\n  id: Int\n"
    messages = session(
        init(),
        [opened(uri, text), formatting(1, uri), changed(uri, whole, 2)],
        [formatting(2, uri), changed(uri, text, 3), formatting(3, uri)],
    )
    assert response(messages, 1)["result"] is None
    assert response(messages, 2)["result"][0]["newText"] == "shape A:\n    id: Int\n"
    assert response(messages, 3)["result"] is None


def test_formatting_has_no_result_when_fmt_refuses_its_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uri = "untitled:Untitled-1"
    text = "shape A:\n  id: Int\n"
    refused: list[tuple[object, str, object]] = [
        (source_format, "_render", lambda lines, newline: "shape B:\n    id: Int\n"),
        (
            source_format.parser_api,
            "_source_exceeds_utf8_budget",
            lambda value: len(value) > len(text),
        ),
    ]
    for owner, name, replacement in refused:
        with monkeypatch.context() as patched:
            patched.setattr(owner, name, replacement)
            with pytest.raises(source_format.FormatRefusedError):
                source_format.format_source(text)
            messages = session(init(), [opened(uri, text), formatting(1, uri)])
        assert response(messages, 1)["result"] is None


def test_formatting_a_refused_document_or_malformed_params(tmp_path: Path) -> None:
    uri = (tmp_path / "x.pietto").as_uri()
    text = "shape A:\n  id: Int\n"
    messages = session(
        init(),
        [opened(uri, text, 1)],
        [
            changed(uri, "shape B:\n  id: Int\n", 2, ranged=True),
            formatting(1, uri),
            formatting(2, 7),
            {"jsonrpc": "2.0", "id": 3, "method": "textDocument/formatting"},
        ],
        [opened(uri, text, 3), formatting(4, uri)],
    )
    assert response(messages, 1)["result"] is None
    assert response(messages, 2)["error"]["code"] == -32602
    assert response(messages, 3)["error"]["code"] == -32602
    assert response(messages, 4)["result"][0]["newText"] == "shape A:\n    id: Int\n"


def test_formatting_answers_at_once_and_calls_no_analysis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """While it handles a formatting request, before or after the analyses of
    its buffer, the server makes one format_source call on that buffer, calls
    no analysis entry point, schedules, holds or forgets nothing and sends
    only the answer, so the symbols request that the root analysis holds gets
    its symbols and the session publishes what it publishes without
    formatting."""

    root = project(tmp_path, models=MODELS, a=A_OK)
    a_uri, alone = (root / "a.pietto").as_uri(), (tmp_path / "x.pietto").as_uri()
    messy, alone_text = A_OK.replace("\n", "  \n"), SINGLE.replace("\n", "  \n")
    batch = [
        opened(a_uri, messy),
        request(1, "textDocument/documentSymbol", a_uri),
        formatting(2, a_uri),
        opened(alone, alone_text),
        formatting(3, alone),
    ]
    later = [formatting(4, a_uri), formatting(5, alone)]
    plain = session(
        init(root),
        [item for item in batch if item["method"] != "textDocument/formatting"],
    )
    symbols = response(plain, 1)["result"]
    assert symbols
    inside: list[object] = []
    formatted: list[str] = []
    sent: list[Message] = []
    seen: list[tuple[int, ...]] = []
    real_format, real_send = _lsp._Server._format, _lsp._Server._send
    real_format_source = _lsp.format_source

    def kept(server: _lsp._Server) -> object:
        return (
            {uri: dataclasses.replace(item) for uri, item in server.documents.items()},
            dict(server.epochs),
            dict(server.dirty),
            list(server.held),
            dict(server.snapshots),
            list(server.selections),
            list(server.extras),
            dict(server.published),
            dict(server.shown),
        )

    def format_once(
        server: _lsp._Server, request_id: int | str, params: dict[str, object]
    ) -> None:
        state = kept(server)
        seen.append(
            (
                len(server.snapshots),
                len(server.published),
                sum(map(len, server.selections)),
                sum(map(len, server.extras)),
                len(server.shown),
            )
        )
        start = len(sent)
        inside.append(request_id)
        try:
            real_format(server, request_id, params)
        finally:
            inside.pop()
        assert kept(server) == state
        assert [message.get("id") for message in sent[start:]] == [request_id]

    def format_source(text: str, **options: Any) -> object:
        assert inside, "format_source outside formatting"
        formatted.append(text)
        return real_format_source(text, **options)

    def send(server: _lsp._Server, message: Message) -> None:
        sent.append(message)
        real_send(server, message)

    def guard(owner: object, name: str) -> None:
        real = getattr(owner, name)

        def guarded(*args: Any, **kwargs: Any) -> object:
            assert not inside, f"{name} while formatting"
            return real(*args, **kwargs)

        monkeypatch.setattr(owner, name, guarded)

    for name in (
        "_check_text_with_editor_facts",
        "check_project_editor_diagnostics",
        "selected_project_paths",
        "parse_source",
        "analyze",
    ):
        guard(_lsp, name)
    for name in ("_touch", "_analyse"):
        guard(_lsp._Server, name)
    monkeypatch.setattr(_lsp, "format_source", format_source)
    monkeypatch.setattr(_lsp._Server, "_format", format_once)
    monkeypatch.setattr(_lsp._Server, "_send", send)
    messages = session(init(root), batch, later)
    assert formatted == [messy, alone_text] * 2
    # The later requests find the root and the file unit analysed, the
    # file's diagnostics published, and the root's selection, extra paths
    # and message kept from its analyses, so a formatting that forgot any of
    # them would show; the first ones find documents, epochs, units to
    # analyse and a waiting request.
    assert seen == [(0, 0, 2, 1, 1)] * 2 + [(2, 1, 2, 1, 1)] * 2
    order = [message.get("id", message.get("method")) for message in messages]
    published = order.index("textDocument/publishDiagnostics")
    # The root analysis that the open schedules holds the symbols request, but
    # not the formatting of either buffer.
    assert order.index(2) < order.index(3) < published < order.index(1)
    assert response(messages, 1)["result"] == symbols
    assert publishes(messages) == publishes(plain)
    assert applied(messy, response(messages, 2)["result"]) == A_OK
    assert applied(alone_text, response(messages, 3)["result"]) == SINGLE
    for number in (4, 5):
        assert (
            response(messages, number)["result"]
            == response(messages, number - 2)["result"]
        )


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
        (3, -32602),
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
POSIX_NAMES = pytest.mark.skipif(sys.platform == "win32", reason="POSIX file names")


@pytest.mark.parametrize(
    "options",
    [
        {"projectRoots": "relative"},
        {"projectRoots": ["relative/root"]},
        {"projectRoots": ["/abs/root", "/abs/root/."]},
        # No POSIX file has these names: a NUL, or a surrogate the file system
        # encoding refuses. Windows realpath accepts both, so only POSIX refuses.
        pytest.param({"projectRoots": ["/abs/a\x00b"]}, marks=POSIX_NAMES),
        pytest.param({"projectRoots": ["/abs/r\ud800"]}, marks=POSIX_NAMES),
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
        ("file://[::1/x.pietto", False, None),
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


def test_a_file_uri_that_does_not_parse_names_a_standalone_document() -> None:
    # The host bracket is never closed, so the URI maps to no path.
    uri, other = "file://[::1/x.pietto", "file://[::1/y.pietto"
    messages = session(
        init(),
        [
            request(1, "textDocument/hover", other, 0, 0),
            request(2, "textDocument/documentSymbol", other),
        ],
        [opened(uri, "shape User:\n    id: Int\n", 1)],
        [request(3, "textDocument/documentSymbol", uri)],
    )
    # Neither a request on such a URI nor its didOpen stops the server.
    assert response(messages, 1)["result"] is None
    assert response(messages, 2)["result"] == []
    assert publishes(messages, uri) == [{"uri": uri, "diagnostics": [], "version": 1}]
    assert [item["name"] for item in response(messages, 3)["result"]] == ["User"]


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


def test_editor_facts_refuse_selected_name_collisions_and_their_targets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    copied = """from "a.pietto" import (
    table active_users,
)

table copied:
    from active_users
    select:
        id
"""
    exported = A_OK + "\nexport (\n    table active_users,\n)\n"
    root = project(tmp_path, models=MODELS, a=exported, copied=copied)
    if (root / "A.pietto").exists():
        pytest.skip("needs two file names that differ only in letter case")
    (root / "A.pietto").write_text(
        exported.replace("active_users", "other_users"), encoding="utf-8"
    )
    monkeypatch.setattr(_lsp, "Path", FoldedPath)
    uri = (root / "a.pietto").as_uri()
    copied_uri = (root / "copied.pietto").as_uri()
    messages = session(
        init(root),
        [opened(uri, exported, 1), opened(copied_uri, copied, 1)],
        [
            request(1, "textDocument/documentSymbol", uri),
            request(2, "textDocument/hover", uri, 5, 9),
            request(3, "textDocument/definition", copied_uri, 5, 9),
            request(4, "textDocument/hover", copied_uri, 5, 9),
            request(5, "textDocument/documentSymbol", copied_uri),
            request(6, "textDocument/documentLink", copied_uri),
            symbols(7, ""),
        ],
    )
    assert "two names" in publishes(messages, uri)[-1]["diagnostics"][0]["message"]
    assert response(messages, 1)["result"] == []
    assert response(messages, 2)["result"] is None
    assert response(messages, 3)["result"] is None
    assert response(messages, 4)["result"] is None
    assert [item["name"] for item in response(messages, 5)["result"]] == ["copied"]
    # Neither name lists its declarations, and no import path links there.
    assert response(messages, 6)["result"] == []
    assert [item["name"] for item in response(messages, 7)["result"]] == [
        "copied",
        "User",
        "users",
    ]


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
    real = _lsp.check_project_editor_diagnostics

    def checking(root: Path, *, overlays: dict[str, str]) -> object:
        seen.append(dict(overlays))
        return real(root, overlays=overlays)

    monkeypatch.setattr(_lsp, "check_project_editor_diagnostics", checking)
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
    real = _lsp.check_project_editor_diagnostics

    def checking(root: Path, *, overlays: dict[str, str]) -> object:
        if overlays.get("a.pietto") == A_BAD:
            script.batches[0].append(changed(uri, A_OK, 2))
        return real(root, overlays=overlays)

    monkeypatch.setattr(_lsp, "check_project_editor_diagnostics", checking)
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


def test_only_a_pending_analysis_of_its_own_units_holds_a_request(
    tmp_path: Path,
) -> None:
    root = project(tmp_path, models=MODELS, a=A_OK)
    other = project(tmp_path, "other", models=MODELS)
    (root / "sub").mkdir()
    # No root selects the loose file, so it is checked alone; the root
    # still contains its path. The single file is outside both roots.
    loose = (root / "sub" / "loose.pietto").as_uri()
    single = (tmp_path / "single.pietto").as_uri()
    other_uri = (other / "models.pietto").as_uri()
    script = Script(
        [init(root, other)],
        [
            opened(loose, "shape Loose:\n    id: Int\n", 1),
            opened(single, "shape User:\n    id: Int\n", 1),
            opened(other_uri, MODELS, 1),
        ],
        [
            opened((root / "a.pietto").as_uri(), A_OK, 1),
            request(1, "textDocument/documentSymbol", loose),
            notify("$/cancelRequest", id=1),
            request(2, "textDocument/hover", loose, 1, 8),
            request(3, "textDocument/documentSymbol", single),
            request(4, "textDocument/documentSymbol", other_uri),
            SHUTDOWN,
        ],
        [EXIT],
    )
    out = io.BytesIO()
    assert _lsp._Server(script, out, "test").run() == 0
    messages = frames(out.getvalue())
    # The root analysis that the edit of a.pietto schedules holds the loose
    # file's requests, but neither the single file's nor one in the other
    # root. Shutdown stops it, and so answers each waiting request with no
    # result, not from the loose file's own snapshot.
    assert [item["id"] for item in messages if "id" in item] == [0, 3, 4, 1, 2, 99]
    assert [item["name"] for item in response(messages, 3)["result"]] == ["User"]
    assert [item["name"] for item in response(messages, 4)["result"]] == [
        "User",
        "users",
    ]
    assert response(messages, 1)["result"] == []
    assert response(messages, 2)["result"] is None


def test_nothing_is_written_after_exit_arrives_during_an_analysis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    uri = (tmp_path / "x.pietto").as_uri()
    script = Script(
        [INIT, opened(uri, SINGLE, 1), request(1, "textDocument/documentSymbol", uri)]
    )
    real = _lsp._check_text_with_editor_facts

    def checking(text: str, *, path: str | None = None) -> object:
        # The waiting request becomes stale, then the session ends.
        script.batches[0].extend([changed(uri, SINGLE, 2), EXIT])
        return real(text, path=path)

    monkeypatch.setattr(_lsp, "_check_text_with_editor_facts", checking)
    out = io.BytesIO()
    assert _lsp._Server(script, out, "test").run() == 1
    assert [m.get("id") for m in frames(out.getvalue())] == [0]


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


# The completion oracle, written before `pietto._editor_completion`. Each
# program passes `pietto check`, and together they write every keyword of
# COMPLETION_ORACLE where the parser reads it as a keyword, not only as a
# name, every builtin type as a type and every scalar function and aggregate
# as a call.
COMPLETION_WITNESSES = (
    """type UserId = UUID
type Percent = Float ensure 0 <= self <= 1

type Username = Text(max = 32):
    ensure len(self) >= 3

enum Status:
    draft
    paid

constraint positive(x: Int) -> Bool:
    return x > 0

derive normalized(x: Text) -> Text:
    return lower(trim(x))

def doubled(x: Int) -> Int:
    return x * 2

shape User:
    id: Int
    name: Text
    score: Int | None
    ratio: Float
    born: Date
    seen: Timestamp
    amount: Decimal
    active: Bool
    key: UUID
    raw: Bytes
    doc: Json
    anything: Any

    unique_name = unique(name)
    name_idx = index(name) when score is None
    valid = check(ratio >= 0)

source users: User = postgres.table("users")

table scalars:
    from users
    where score is not None and not active or name like "a%"
    select:
        id
        big = score if score > 10 else 0
        listed = id in (1, 2, 3)
        a = lower(name)
        b = upper(name)
        c = trim(name)
        d = len(name)
        e = substr(name, 1, 2)
        f = replace(name, "a", "b")
        g = lpad(name, 5, "x")
        h = contains(name, "a")
        i = starts_with(name, "a")
        j = ends_with(name, "a")
        k = abs(amount)
        l = date_of(seen)
        m = hour(seen)
        n = minute(seen)
        o = add_months(born, 1)
        p = matches(name, "^a")
        q = coalesce(score, 0)
        r = nullif(id, 0)
        s = sign(id)
        t = year(born)
        u = month(born)
        v = day(born)
        w = round(amount, 2)
        x = date_trunc("month", seen)
        y = concat(name, "x")
        z = same_value(score, score)
        now_at = now()

query top_users:
    from users
    select id, score
    order by score desc, id asc
    limit 10
""",
    """shape Sale:
    id: Int
    category: Text
    qty: Int | None
    ratio: Float
    amount: Decimal | None
    paid: Bool

    sale_id = unique(id)

source sales: Sale = postgres.table("sales")

query summary:
    from sales
    group by category
    select:
        category
        a = count()
        b = count_distinct(qty)
        c = sum(qty)
        d = avg(amount)
        e = min(qty)
        f = max(qty)
        g = stddev(ratio)
        h = variance(ratio)
        i = pvariance(ratio)
        j = pstdev(ratio)
        k = median(ratio)
        l = quantile(ratio, 0.5)
        m = string_agg(category, ",", order by id)
        n = first(qty, order by id)
        o = last(qty, order by id)
        p = any(s.paid for s in group)
        q = all(s.paid for s in group)
    having a > 1
""",
    """shape Item:
    id: Int
    category: Text
    value: Int | None

    item_id = unique(id)

source items: Item = postgres.table("items")

query windowed:
    from items
    let base = window(partition by category order by id rows between unbounded preceding and current row)
    select:
        id
        position = row_number() window(order by id)
        running = sum(value) window base
        a = last_value(value) window(order by id range between unbounded preceding and unbounded following)
        b = nth_value(value, 2) from last ignore nulls window(order by id groups between 1 preceding and current row exclude current row)
        c = nth_value(value, 2) from first respect nulls window(order by id desc groups between 1 preceding and 1 following exclude ties)
        d = first_value(value) window(order by id rows between 1 preceding and current row exclude no others)
        e = first_value(value) window(order by id range current row exclude group)
    qualify position <= 3
""",
    """cutoff: Int = 3

shape Order:
    id: Int
    customer_id: Int
    ordered_at: Timestamp

    order_key = unique(id)

shape Customer:
    id: Int

    customer_key = unique(id)

shape Price:
    customer_id: Int
    valid_from: Timestamp

    price_key = unique(customer_id, valid_from)

source orders: Order = postgres.table("orders")

source customers: Customer = postgres.table("customers")

source prices: Price = postgres.table("prices")

relationship OrderCustomer(order: Order, customer: Customer):
    order.customer_id == customer.id

query joined:
    from orders
    let a = customers
    let b = customers
    let c = customers
    let d = customers
    let e = customers
    inner join a on OrderCustomer(orders, a)
    left join b on orders.customer_id == b.id
    right join c on orders.customer_id == c.id
    full join d on orders.customer_id == d.id
    cross join e
    where orders.id > cutoff
    select order_id = orders.id, yes = True, no = False

query priced:
    from orders
    let price = prices
    asof left join price on orders.customer_id == price.customer_id and orders.ordered_at >= price.valid_from
    select order_id = orders.id
""",
)
COMPLETION_PROJECT = {
    "models": """shape Order:
    id: Int
    customer_id: Int
    total: Int

    order_key = unique(id)

shape Customer:
    id: Int
    tier: Text

    customer_key = unique(id)

source orders: Order = postgres.table("orders")

source customers: Customer = postgres.table("customers")

export source orders, source customers
""",
    "report": """from "models.pietto" import (
    source orders,
    source customers as clients,
)

query vip_report(cutoff: Int):
    let vip:
        from clients
        where tier == "gold"
        select id
    let big:
        from orders
        where customer_id in vip
        select latest = max(total)
    from orders
    where total >= cutoff and customer_id not in vip
    select id, biggest = scalar big.latest

query with_recent:
    let recent:
        capture clients
        from orders
        where orders.customer_id == clients.id
        select id
    from clients
    where exists recent
    select id

query union_codes:
    let seed:
        values(id: Int, label: Text | None):
            1, "new"
            2, None
    let more:
        values(id: Int, label: Text | None)
    let combined:
        union all seed, more
    from combined
    select id

query shared_codes:
    let seed:
        values(id: Int)
    let combined:
        intersect distinct seed, seed
    from combined
    select id

query other_codes:
    let seed:
        values(id: Int)
    let combined:
        except all seed, seed
    from combined
    select id

query tiers:
    from clients
    select distinct tier

query nested:
    let recent:
        from orders
        select id
        order by id
    from orders
    select:
        customer_id
        recent_orders = collect recent

export query vip_report
""",
}
COMPLETION_BASE = """shape User:
    id: Int
    name: Text | None

source users: User = postgres.table("users")

"""
# Words that no accepted source writes as a keyword or calls, each with a
# program that `pietto check` refuses where it writes it so, beside lines
# that check accepts. The retired header words are still names, and
# `encoding` a type argument name.
COMPLETION_REFUSED = {
    **{
        word: f"{line}\n\nshape A:\n    id: Int\n"
        for word, line in (
            ("pietto", "pietto 1"),
            ("mode", "mode loose"),
            ("loose", "mode loose"),
            ("checked", "mode checked"),
            ("strict", "mode strict"),
            ("dialect", "dialect postgres"),
            ("encoding", "encoding utf8"),
        )
    },
    "nullable": "shape A:\n    id: Int nullable\n",
    "null": "shape A:\n    id: Int not null\n",
    **{
        word: COMPLETION_BASE + f"query q:\n    from users\n{body}"
        for word, body in (
            ("cast", "    select f = cast(id as Float)\n"),
            (
                "satisfying",
                "    group by id\n    select id, n = count()\n"
                "    satisfying:\n        n > 1\n",
            ),
            (
                "semi",
                "    let u = users\n    semi join u on users.id == u.id\n"
                "    select id\n",
            ),
            (
                "anti",
                "    let u = users\n    anti join u on users.id == u.id\n"
                "    select id\n",
            ),
            ("via", "    inner join users as u: via r\n    select id\n"),
            ("similarity", '    select s = similarity(name, "a")\n'),
            ("cosine_distance", "    select s = cosine_distance(id, id)\n"),
        )
    },
    "endpoint": COMPLETION_BASE
    + "relationship r:\n    endpoint a: users\n    endpoint b: users\n",
}
# The words of the generated lexer's literal names.
LEXER_WORDS = {
    name[1:-1]
    for name in PiettoLexer.literalNames
    if name.startswith("'") and name[1:-1].isidentifier()
}
TEXT, KEYWORD, CLASS, FUNCTION = 1, 14, 7, 3
COMPLETION_ORACLE = [
    *(
        (word, KEYWORD)
        for word in """False None True all and any as asc asof between by capture
        check collect constraint cross current def derive desc distinct else
        ensure enum except exclude exists export first following for from full
        group groups having if ignore import in index inner intersect is join
        last left let like limit no not nulls on or order others partition
        preceding qualify query range relationship respect return right row rows
        scalar select shape source table ties type unbounded union unique values
        when where window""".split()
    ),
    *(
        (name, CLASS)
        for name in "Any Bool Bytes Date Decimal Float Int Json Text Timestamp UUID".split()
    ),
    *(
        (name, FUNCTION)
        for name in """abs add_months coalesce concat contains date_of date_trunc day
        ends_with hour len lower lpad matches minute month now nullif replace round
        same_value sign starts_with substr trim upper year""".split()
    ),
    *(
        (name, FUNCTION)
        for name in """all any avg count count_distinct first last max median min
        pstdev pvariance quantile stddev string_agg sum variance""".split()
    ),
]


def completion_roles(text: str) -> set[tuple[str, str]]:
    """Each `(word, role)` of `text` as the parser reads it: `keyword`
    for a keyword token that is no name, `type` for the name of a type
    reference and `call` for a word followed by `(`."""

    _, tree = _parse_migration_source(text, modern=True)
    assert tree is not None
    keywords = {PiettoLexer.TRUE, PiettoLexer.FALSE} | {
        getattr(PiettoLexer, word.upper()) for word in LEXER_WORDS
    }
    names = {
        PiettoParser.RULE_identifier,
        PiettoParser.RULE_softKeyword,
        PiettoParser.RULE_typeArgumentName,
    }
    terminals: list[Any] = []
    stack: list[Any] = [tree]
    while stack:
        node = stack.pop()
        children = getattr(node, "children", None)
        if children is not None:
            stack.extend(reversed(children))
        elif hasattr(node, "symbol"):
            terminals.append(node)
    roles: set[tuple[str, str]] = set()
    for node, after in zip(terminals, [*terminals[1:], None], strict=True):
        token, parent = node.symbol, node.parentCtx
        if token.type in keywords and parent.getRuleIndex() not in names:
            roles.add((token.text, "keyword"))
        if (
            parent.getRuleIndex() == PiettoParser.RULE_identifier
            and parent.parentCtx.getRuleIndex() == PiettoParser.RULE_typeReference
        ):
            roles.add((token.text, "type"))
        if after is not None and after.symbol.type == PiettoLexer.LPAREN:
            roles.add((token.text, "call"))
    return roles


def test_the_completion_oracle_is_what_check_accepts(tmp_path: Path) -> None:
    witnessed: set[tuple[str, str]] = set()
    for index, text in enumerate(COMPLETION_WITNESSES):
        path = tmp_path / f"witness_{index}.pietto"
        path.write_text(text, encoding="utf-8")
        diagnostics = cli_json("check", str(path))["diagnostics"]
        assert [d for d in diagnostics if d["severity"] == "error"] == [], index
        witnessed |= completion_roles(text)
    root = project(tmp_path, **COMPLETION_PROJECT)
    assert cli_json("check", "--project", str(root))["diagnostics"] == []
    for text in COMPLETION_PROJECT.values():
        witnessed |= completion_roles(text)
    role_of = {KEYWORD: "keyword", CLASS: "type", FUNCTION: "call"}
    assert [
        item
        for item in COMPLETION_ORACLE
        if (item[0], role_of[item[1]]) not in witnessed
    ] == []
    labels = {label for label, _ in COMPLETION_ORACLE}
    accepted = COMPLETION_BASE + "query q:\n    from users\n    select id\n"
    extension = {"similarity", "cosine_distance"}
    for word, text in {"": accepted, **COMPLETION_REFUSED}.items():
        path = tmp_path / f"refused_{word}.pietto"
        path.write_text(text, encoding="utf-8")
        errors = [
            (d["code"], d["location"]["line"])
            for d in cli_json("check", str(path))["diagnostics"]
            if d["severity"] == "error"
        ]
        if not word:
            assert errors == []
            continue
        # The one error refuses the word on the line that writes it; a
        # retired relationship block is refused at its header, the line
        # before its first `endpoint`.
        line = next(
            n
            for n, row in enumerate(text.splitlines(), 1)
            if re.search(rf"\b{word}\b", row)
        )
        code = "PIE-S2103" if word in extension else "PIE-P1000"
        assert errors == [(code, line - 1 if word == "endpoint" else line)], word
        assert word not in labels
        assert {(word, "keyword"), (word, "call")} & completion_roles(text), word
    # The oracle is complete: every lexer word is offered or refused, and so
    # is every builtin of the core catalog; no extension function is offered.
    keywords = {label for label, kind in COMPLETION_ORACLE if kind == KEYWORD}
    assert LEXER_WORDS - keywords == set(COMPLETION_REFUSED) - extension
    assert keywords - LEXER_WORDS == {"True", "False"}
    assert {label for label, kind in COMPLETION_ORACLE if kind == CLASS} == set(
        BUILTIN_TYPE_NAMES
    )
    catalog = [
        *sorted({*BUILTIN_FUNCTIONS, *SPECIAL_BUILTIN_FUNCTION_NAMES}),
        *sorted({*SEMANTIC_AGGREGATE_NAMES, *GROUP_TEST_AGGREGATE_NAMES}),
    ]
    assert [label for label, kind in COMPLETION_ORACLE if kind == FUNCTION] == catalog


def test_completion_answers_the_oracle_at_once_at_every_position(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    items = [{"label": label, "kind": kind} for label, kind in COMPLETION_ORACLE]
    code, messages, stderr = run_process(
        frame(INIT)
        + frame(request(1, "textDocument/completion", "untitled:Untitled-1", 0, 0))
        + frame(SHUTDOWN)
        + frame(EXIT)
    )
    assert (code, stderr) == (0, b"")
    assert response(messages, 0)["result"]["capabilities"]["completionProvider"] == {}
    assert response(messages, 1)["result"] == items
    # Requests on a document whose analysis is pending, past its end, on a
    # module of a root and on a URI that is not open are answered when read
    # and start no analysis; the open buffer adds its identifiers, and the
    # others get the static list.
    root = project(tmp_path, models=MODELS)
    uri = (tmp_path / "x.pietto").as_uri()
    analyses: list[str] = []
    running: list[str] = []
    guarded: set[str] = set()
    check_file = _lsp._check_text_with_editor_facts
    check_root = _lsp.check_project_editor_diagnostics

    def checked_file(text: str, *, path: str | None = None) -> object:
        analyses.append("file")
        running.append("file")
        try:
            return check_file(text, path=path)
        finally:
            running.pop()

    def checked_root(root: str | Path, *, overlays: Mapping[str, str]) -> object:
        analyses.append("root")
        running.append("root")
        try:
            return check_root(root, overlays=overlays)
        finally:
            running.pop()

    def analysing(name: str, function: Callable[..., object]) -> Callable[..., object]:
        # Lexing, parsing and analysis run only inside the two analyses.
        def call(*args: object, **kwargs: object) -> object:
            assert running, f"{name} outside an analysis"
            guarded.add(name)
            return function(*args, **kwargs)

        return call

    monkeypatch.setattr(_lsp, "_check_text_with_editor_facts", checked_file)
    monkeypatch.setattr(_lsp, "check_project_editor_diagnostics", checked_root)
    for owner, name in (
        (_lsp, "parse_source"),
        (_lsp, "analyze"),
        (PiettoLexer, "__init__"),
    ):
        monkeypatch.setattr(owner, name, analysing(name, getattr(owner, name)))
    messages = session(
        init(root),
        [
            opened(uri, SINGLE, 1),
            request(1, "textDocument/completion", uri, 0, 0),
            request(2, "textDocument/completion", uri, 99, 99),
            request(
                3, "textDocument/completion", (root / "models.pietto").as_uri(), 2, 4
            ),
            request(4, "textDocument/completion", "untitled:Untitled-1", 0, 0),
        ],
        [request(5, "textDocument/completion", uri, 8, 10)],
    )
    published = next(
        index
        for index, message in enumerate(messages)
        if message.get("method") == "textDocument/publishDiagnostics"
        and message["params"]["uri"] == uri
    )
    single = [
        *items,
        *(
            {"label": word, "kind": TEXT}
            for word in "User active_users email id nope_u postgres users".split()
        ),
    ]
    assert [response(messages, n)["result"] for n in range(1, 6)] == [
        single,
        single,
        items,
        items,
        [item for item in single if item["label"] != "email"],
    ]
    assert all(messages.index(response(messages, n)) < published for n in range(1, 5))
    assert analyses == ["root", "file"]
    assert guarded == {"parse_source", "analyze", "__init__"}
    # With no document open, answering lexes, parses and analyses nothing
    # either; malformed parameters are refused as for the other position
    # requests.

    def refused(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("lexed, parsed or analysed")

    for owner, name in (
        (_lsp, "parse_source"),
        (_lsp, "analyze"),
        (_lsp, "_check_text_with_editor_facts"),
        (_lsp, "check_project_editor_diagnostics"),
        (PiettoLexer, "__init__"),
    ):
        monkeypatch.setattr(owner, name, refused)
    malformed = [
        {"position": {"line": 0, "character": 0}},
        {"textDocument": {"uri": 1}, "position": {"line": 0, "character": 0}},
        {"textDocument": {"uri": uri}},
        {"textDocument": {"uri": uri}, "position": {"line": -1, "character": 0}},
        {"textDocument": {"uri": uri}, "position": {"line": 0, "character": True}},
    ]
    messages = session(
        init(),
        [
            request(1, "textDocument/completion", uri, 0, 0),
            *(
                {
                    "jsonrpc": "2.0",
                    "id": 2 + index,
                    "method": "textDocument/completion",
                    "params": params,
                }
                for index, params in enumerate(malformed)
            ),
        ],
    )
    assert response(messages, 1)["result"] == items
    assert [response(messages, 2 + n)["error"]["code"] for n in range(5)] == [
        -32602
    ] * 5


# Buffers whose comments, strings, numbers, keywords and unknown characters
# border on identifiers.
COMPLETION_SCANS = (
    "",
    "﻿shape Zed:\n    a_1: Int\n",
    "x = 'it\\'s fromage' # words in a comment\ny = \"a\\\"b c\" z\n",
    's = "unterminated words\nnext_line = 1_000 + 1_a + 2.5x + 3._y + 4__z\n',
    "t = 'escaped \\\nnewline' after\n\"\\\r\nend\n",
    "café naïve _ __ True true False false None null mode fromage from_ select\n",
    "\r\nwin\rmac\r\n#only\n'''\n\"\"\nx@y{z}`w`\n",
    's = "a\\\\" b "c"\n',
)


def test_completion_adds_the_identifier_tokens_of_the_open_buffer() -> None:
    # The scan finds exactly the generated lexer's IDENTIFIER tokens.
    for text in (
        *COMPLETION_WITNESSES,
        *COMPLETION_PROJECT.values(),
        *COMPLETION_REFUSED.values(),
        SINGLE,
        MODELS,
        *COMPLETION_SCANS,
    ):
        tokens = PiettoLexer(InputStream(text)).getAllTokens()
        identifiers = {t.text for t in tokens if t.type == PiettoLexer.IDENTIFIER}
        assert _editor_completion.buffer_identifiers(text) == sorted(identifiers)
    # Each request reads only its own document's current buffer. The word
    # that touches the position (UTF-16 units over `\r`, `\r\n` and `\n`
    # lines; past a line's end is its end, and a line past the last one
    # leaves nothing out) is left out, a word that is already a label, such as
    # `Int` or `count`, is not repeated, and a refused or closed document gets
    # the static list. A document whose unpaired surrogate the server replaced
    # is not refused; U+FFFD is one UTF-16 unit, as the surrogate was, so its
    # identifiers and positions are the client's.
    items = [{"label": label, "kind": kind} for label, kind in COMPLETION_ORACLE]

    def words(*labels: str) -> list[dict[str, object]]:
        return [*items, *({"label": label, "kind": TEXT} for label in labels)]

    uri, other = "file:///w/words.pietto", "untitled:Untitled-2"
    lone = "file:///w/lone.pietto"
    zebra = "# zebra\rshape Zebra:\r\n    zebra_id: Int\n    count: Int\nzebr\n"
    messages = session(
        init(),
        [
            opened(uri, SINGLE, 1),
            opened(other, "query walrus_report:\n    from users\n", 1),
            request(1, "textDocument/completion", uri, 0, 0),
            changed(uri, zebra + "\U0001f600\U0001f600\U0001f600 ab cd", 2),
            request(2, "textDocument/completion", uri, 4, 4),
            request(3, "textDocument/completion", uri, 2, 6),
            request(4, "textDocument/completion", uri, 2, 99),
            request(5, "textDocument/completion", uri, 5, 7),
            request(6, "textDocument/completion", uri, 6, 0),
            request(7, "textDocument/completion", other, 0, 0),
            opened(lone, "alpha = '\ud800' beta\n", 1),
            request(8, "textDocument/completion", lone, 0, 12),
            changed(uri, "quokka", 3, ranged=True),
            request(9, "textDocument/completion", uri, 0, 0),
            closed(other),
            request(10, "textDocument/completion", other, 0, 0),
        ],
    )
    assert [response(messages, n)["result"] for n in range(1, 11)] == [
        words("User", "active_users", "email", "id", "nope_u", "postgres", "users"),
        words("Zebra", "ab", "cd", "zebra_id"),
        words("Zebra", "ab", "cd", "zebr"),
        words("Zebra", "ab", "cd", "zebr", "zebra_id"),
        words("Zebra", "cd", "zebr", "zebra_id"),
        words("Zebra", "ab", "cd", "zebr", "zebra_id"),
        words("users", "walrus_report"),
        words("alpha"),
        items,
        items,
    ]
