"""`pietto lsp`: Pietto check diagnostics for editors over the Language Server
Protocol (alpha), on standard input and output, with the standard library
only. The contract is docs/editor-lsp.md."""

from __future__ import annotations

import json
import os
import queue
import re
import sys
import threading
from dataclasses import dataclass
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from types import MappingProxyType
from typing import BinaryIO, Mapping, Protocol
from urllib.parse import unquote, urlsplit

from pietto._editor_facts import (
    EditorDeclaration,
    EditorFacts,
    EditorUse,
    single_file_editor_facts,
)
from pietto._project.check import (
    ProjectDiagnosticsReport,
    ProjectEditorDiagnostics,
    check_project_editor_diagnostics,
    selected_project_paths,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.parser_api import parse_source
from pietto.semantic import analyze

_EOF = object()
_FRAMING_ERROR = object()
_INVALID_JSON = object()
_MAX_HEADER = 65536
_CHUNK = 65536
_LINE_BREAK = re.compile(r"\r\n|\r|\n")
_LONE_SURROGATE = re.compile("[\ud800-\udfff]")
_WINDOWS_DRIVE = re.compile(r"/[A-Za-z]:")
_ROOTS_ERROR = "projectRoots must be a list of distinct absolute paths"
_WHOLE_CHANGES = "Pietto needs whole-document changes; reopen this file."
_CONFIG = "pietto.toml"

# A unit is ("root", index) or ("file", uri). An owner of a URI is a unit, or
# ("roots", indexes) for a path two or more roots select, ("uris", uris) for a
# selected path open under two or more URIs, or ("refused", uri) for a
# document whose change was refused.
type _Key = tuple[str, object]


class _Inbox(Protocol):
    def get(self) -> object: ...
    def get_nowait(self) -> object: ...


class _Closed(Exception):
    """Standard output is closed."""


def serve(stdin: BinaryIO, stdout: BinaryIO, *, version: str) -> int:
    """Serve one editor session and return the process exit code."""

    inbox: queue.Queue[object] = queue.Queue()
    threading.Thread(
        target=_read_frames, args=(stdin.fileno(), inbox), daemon=True
    ).start()
    return _Server(inbox, stdout, version).run()


def _read_frames(stdin: int, inbox: queue.Queue[object]) -> None:
    """Queue each decoded message, then `_EOF` or `_FRAMING_ERROR`. Reading
    on a thread lets the server see a newer change before it publishes; it
    reads the descriptor directly, so no stream lock is held at exit. Any
    failure ends with a sentinel, so the server never waits on a dead
    reader."""

    try:
        _read_messages(stdin, inbox)
    except Exception:
        inbox.put(_FRAMING_ERROR)


def _read_messages(stdin: int, inbox: queue.Queue[object]) -> None:
    buffer = bytearray()
    while True:
        while (end := buffer.find(b"\r\n\r\n")) < 0:
            chunk = os.read(stdin, _CHUNK) if len(buffer) < _MAX_HEADER else b""
            if not chunk:
                inbox.put(_FRAMING_ERROR if buffer else _EOF)
                return
            buffer += chunk
        length: int | None = None
        for line in bytes(buffer[:end]).split(b"\r\n"):
            name, colon, value = line.partition(b":")
            if not colon:
                length = None
                break
            if name.strip().lower() == b"content-length":
                length = int(value) if value.strip().isdigit() else -1
        start = end + 4
        if length is None or length < 0:
            inbox.put(_FRAMING_ERROR)
            return
        # Read what arrives, never the declared length at once.
        while len(buffer) < start + length:
            chunk = os.read(stdin, min(start + length - len(buffer), _CHUNK))
            if not chunk:
                inbox.put(_FRAMING_ERROR)
                return
            buffer += chunk
        body = bytes(buffer[start : start + length])
        del buffer[: start + length]
        try:
            message = json.loads(body.decode("utf-8"))
        except Exception:
            message = _INVALID_JSON
        inbox.put(message)


@dataclass(slots=True)
class _Document:
    uri: str
    path: Path | None
    text: str
    version: int | None
    refused: bool = False


@dataclass(frozen=True, slots=True)
class _EditorSnapshot:
    """Facts for exactly one LSP unit and analysis epoch."""

    epoch: int
    facts: Mapping[Path | None, EditorFacts]
    tables: Mapping[Path | None, _Lines]

    def __post_init__(self) -> None:
        object.__setattr__(self, "facts", MappingProxyType(dict(self.facts)))
        object.__setattr__(self, "tables", MappingProxyType(dict(self.tables)))


class _Server:
    def __init__(self, inbox: _Inbox, stdout: BinaryIO, version: str) -> None:
        self.inbox = inbox
        self.stdout = stdout
        self.version = version
        self.state = "new"
        self.exit_code: int | None = None
        self.roots: tuple[Path, ...] = ()
        self.related = False
        self.hover_plaintext = False
        self.hierarchical_symbols = False
        self.documents: dict[str, _Document] = {}
        self.dirty: dict[_Key, None] = {}
        self.epochs: dict[_Key, int] = {}
        self.snapshots: dict[_Key, _EditorSnapshot] = {}
        self.selections: list[frozenset[Path]] = []
        self.extras: list[frozenset[Path]] = []
        self.published: dict[str, tuple[_Key, Path | None]] = {}
        self.shown: dict[int, str] = {}

    def run(self) -> int:
        try:
            while self.exit_code is None:
                self._handle(self.inbox.get())
                self._drain()
                while self.exit_code is None and self.state == "running" and self.dirty:
                    self._analyse(min(self.dirty, key=_unit_order))
        except _Closed:
            return 1
        assert self.exit_code is not None
        return self.exit_code

    def _drain(self) -> None:
        while self.exit_code is None:
            try:
                message = self.inbox.get_nowait()
            except queue.Empty:
                return
            self._handle(message)

    # Messages.

    def _handle(self, message: object) -> None:
        if message is _EOF:
            self.exit_code = 0 if self.state == "shutdown" else 1
        elif message is _FRAMING_ERROR:
            if sys.stderr is not None:
                sys.stderr.write("pietto lsp: invalid message header; stopping\n")
                sys.stderr.flush()
            self.exit_code = 1
        elif message is _INVALID_JSON:
            self._error(None, -32700, "Parse error")
        elif isinstance(message, list):
            self._error(None, -32600, "Batch messages are not supported")
        elif not isinstance(message, dict):
            self._error(None, -32600, "Invalid request")
        else:
            self._handle_object(message)

    def _handle_object(self, message: dict[str, object]) -> None:
        method = message.get("method")
        params = message.get("params")
        params = params if isinstance(params, dict) else {}
        if "id" not in message:
            if isinstance(method, str):
                self._notification(method, params)
            else:
                self._error(None, -32600, "Invalid request")
            return
        request_id = message["id"]
        if not isinstance(method, str):
            if "result" not in message and "error" not in message:
                self._error(None, -32600, "Invalid request")
            return
        if isinstance(request_id, bool) or not isinstance(request_id, int | str):
            self._error(None, -32600, "Invalid request")
        elif self.state == "new":
            if method == "initialize":
                self._initialize(request_id, params)
            else:
                self._error(request_id, -32002, "Server not initialized")
        elif self.state == "shutdown":
            self._error(request_id, -32600, "Server is shut down")
        elif method == "shutdown":
            self.state = "shutdown"
            self.dirty.clear()
            self._send({"jsonrpc": "2.0", "id": request_id, "result": None})
        elif method == "initialize":
            self._error(request_id, -32600, "Server is already initialized")
        elif method in {
            "textDocument/hover",
            "textDocument/definition",
            "textDocument/documentSymbol",
        }:
            self._editor_request(request_id, method, params)
        else:
            self._error(request_id, -32601, f"Method not found: {method}")

    def _initialize(self, request_id: int | str, params: dict[str, object]) -> None:
        # No options, or no projectRoots, is no roots; any other shape fails.
        options = params.get("initializationOptions")
        options = {} if options is None else options
        roots = options.get("projectRoots", []) if isinstance(options, dict) else None
        if not isinstance(roots, list) or not all(
            isinstance(root, str) and os.path.isabs(root) for root in roots
        ):
            self._error(request_id, -32602, _ROOTS_ERROR)
            return
        normalized = tuple(Path(os.path.normpath(root)) for root in roots)
        # Two spellings of one directory, as through a symbolic link, are one.
        if len({Path(os.path.realpath(root)) for root in normalized}) < len(roots):
            self._error(request_id, -32602, _ROOTS_ERROR)
            return
        self.roots = normalized
        self.selections = [frozenset()] * len(normalized)
        self.extras = [frozenset()] * len(normalized)
        self.related = (
            _field(params, "capabilities", "textDocument", "publishDiagnostics").get(
                "relatedInformation"
            )
            is True
        )
        formats = _field(params, "capabilities", "textDocument", "hover").get(
            "contentFormat"
        )
        self.hover_plaintext = isinstance(formats, list) and "plaintext" in formats
        self.hierarchical_symbols = (
            _field(params, "capabilities", "textDocument", "documentSymbol").get(
                "hierarchicalDocumentSymbolSupport"
            )
            is True
        )
        self.state = "running"
        self._send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "capabilities": {
                        "positionEncoding": "utf-16",
                        "textDocumentSync": {"openClose": True, "change": 1},
                        "hoverProvider": True,
                        "definitionProvider": True,
                        "documentSymbolProvider": True,
                    },
                    "serverInfo": {"name": "pietto", "version": self.version},
                },
            }
        )
        for index in range(len(normalized)):
            self.dirty[("root", index)] = None

    def _notification(self, method: str, params: dict[str, object]) -> None:
        if method == "exit":
            self.exit_code = 0 if self.state == "shutdown" else 1
            return
        if self.state != "running":
            return
        item = _field(params, "textDocument")
        uri = item.get("uri")
        if not isinstance(uri, str):
            return
        version = item.get("version")
        version = version if type(version) is int else None
        document = self.documents.get(uri)
        if method == "textDocument/didOpen":
            text = item.get("text")
            if isinstance(text, str):
                self.documents.pop(uri, None)
                path = uri_to_path(uri)
                document = _Document(
                    uri,
                    Path(path) if path is not None and path.is_absolute() else None,
                    _LONE_SURROGATE.sub("\ufffd", text),
                    version,
                )
                self.documents[uri] = document
                self._touch(document)
        elif method == "textDocument/didChange":
            if document is None or document.refused:
                return
            if (
                version is not None
                and document.version is not None
                and version <= document.version
            ):
                return
            if version is not None:
                document.version = version
            changes = params.get("contentChanges")
            change = changes[0] if isinstance(changes, list) and changes else None
            if (
                not isinstance(changes, list)
                or len(changes) != 1
                or not isinstance(change, dict)
                or "range" in change
                or not isinstance(change.get("text"), str)
            ):
                document.refused = True
                self._publish(
                    uri,
                    ("refused", uri),
                    document.path,
                    [_editor_diagnostic(_WHOLE_CHANGES)],
                    version,
                )
            else:
                document.text = _LONE_SURROGATE.sub("\ufffd", str(change["text"]))
            self._touch(document)
        elif method == "textDocument/didClose" and document is not None:
            del self.documents[uri]
            self._touch(document)

    def _touch(self, document: _Document) -> None:
        """Mark the units a document event can change, and make any analysis
        of them running now stale."""

        units: list[_Key] = [("file", document.uri)]
        if document.path is not None:
            units.extend(
                ("root", index)
                for index, root in enumerate(self.roots)
                if document.path.is_relative_to(root)
            )
        for unit in units:
            self.epochs[unit] = self.epochs.get(unit, 0) + 1
            self.snapshots.pop(unit, None)
            self.dirty[unit] = None

    # Analysis.

    def _analyse(self, unit: _Key) -> None:
        """Check one unit, then publish its result unless a message received
        meanwhile made it stale, as the server never publishes diagnostics of
        a text older than the newest one it has received."""

        del self.dirty[unit]
        epoch = self.epochs.get(unit, 0)
        kind, value = unit
        if kind == "root":
            assert isinstance(value, int)
            checked, selections = self._check_root(value)
            self._drain()
            if self._current(unit, epoch):
                self._set_root_snapshot(unit, epoch, value, checked)
                self._publish_root(
                    value, checked.report if checked is not None else None, selections
                )
        else:
            assert isinstance(value, str)
            document = self.documents.get(value)
            if document is None or self._owner(value, document.path) != unit:
                self._sweep()
                return
            diagnostics, facts = _check_text_with_editor_facts(
                document.text,
                path=str(document.path) if document.path is not None else None,
            )
            self._drain()
            if self._current(unit, epoch):
                self.snapshots[unit] = _EditorSnapshot(
                    epoch,
                    {document.path: facts},
                    {document.path: _Lines(document.text, open_buffer=True)},
                )
                table = _Lines(document.text, open_buffer=True)
                self._publish(
                    value,
                    unit,
                    document.path,
                    [
                        _lsp_diagnostic(diagnostic, table.range(diagnostic.location))
                        for diagnostic in diagnostics
                    ],
                    document.version,
                )
                self._sweep()

    def _current(self, unit: _Key, epoch: int) -> bool:
        if self.exit_code is not None or self.state != "running":
            return False
        if self.epochs.get(unit, 0) != epoch:
            self.dirty[unit] = None
            return False
        return True

    def _check_root(
        self, index: int
    ) -> tuple[ProjectEditorDiagnostics | None, list[frozenset[Path]]]:
        root = self.roots[index]
        # A buffer is keyed by the selected entry its path matches, as a URI
        # may spell it in another letter case where paths ignore case. A
        # path open under two or more URIs has no one buffer: it is checked
        # from the disk, and each URI gets only the alias error. A path that
        # two entries name is checked from the disk too, and gets only the
        # names error.
        entries = _entries(root)
        overlays = {
            entry: document.text
            for document in self.documents.values()
            if document.path is not None
            and not document.refused
            and (entry := entries.get(document.path)) is not None
            and len(self._uris(document.path)) == 1
        }
        try:
            checked = check_project_editor_diagnostics(root, overlays=overlays)
        except (OSError, ValueError):
            checked = None
        selections = [
            frozenset(_join(root, path) for path in checked.report.paths)
            if position == index and checked is not None
            else frozenset(_entries(other))
            for position, other in enumerate(self.roots)
        ]
        return checked, selections

    def _set_root_snapshot(
        self,
        unit: _Key,
        epoch: int,
        index: int,
        checked: ProjectEditorDiagnostics | None,
    ) -> None:
        if checked is None:
            self.snapshots.pop(unit, None)
            return
        root = self.roots[index]
        report = checked.report
        tables: dict[Path | None, _Lines] = {}
        facts: dict[Path | None, EditorFacts] = {}
        path_counts: dict[Path, int] = {}
        for relative in report.paths:
            path = _join(root, relative)
            path_counts[path] = path_counts.get(path, 0) + 1
        for relative, item in checked.facts.items():
            path = _join(root, relative)
            if path_counts.get(path) != 1:
                continue
            uris = self._uris(path)
            document = self.documents.get(uris[0]) if len(uris) == 1 else None
            tables[path] = _Lines(
                report.texts.get(relative),
                open_buffer=document is not None and not document.refused,
            )
            facts[path] = _root_editor_facts(item, root)
        self.snapshots[unit] = _EditorSnapshot(epoch, facts, tables)

    def _publish_root(
        self,
        index: int,
        report: ProjectDiagnosticsReport | None,
        selections: list[frozenset[Path]],
    ) -> None:
        root = self.roots[index]
        config = root / _CONFIG
        self.selections = selections
        found: dict[Path, list[dict[str, object]]] = {
            _join(root, path): [] for path in (report.paths if report else ())
        }
        root_errors: list[str] = []
        if report is None:
            root_errors.append(
                "project error: project_root: Project root could not be pinned."
            )
        else:
            for error in report.errors:
                text = f"project error: {error.kind.value}: {error.message}"
                if error.path is None:
                    root_errors.append(text)
                else:
                    found.setdefault(_join(root, error.path), []).append(
                        _editor_diagnostic(text)
                    )
            tables: dict[Path, _Lines] = {}
            for diagnostic in report.diagnostics:
                path = diagnostic.location.path
                target = _join(root, path) if path is not None else config
                related = [
                    {
                        "location": self._location(root, report, location),
                        "message": "Related location",
                    }
                    for location in report.related_locations.get(diagnostic, ())
                    if self.related and location.path is not None
                ]
                found.setdefault(target, []).append(
                    _lsp_diagnostic(
                        diagnostic,
                        self._table(root, report, target, tables).range(
                            diagnostic.location
                        ),
                        related,
                    )
                )
            # A module that partial analysis left out says why, at its import.
            for location, text in report.not_checked:
                assert location.path is not None
                target = _join(root, location.path)
                found.setdefault(target, []).append(
                    {
                        "range": self._table(root, report, target, tables).range(
                            location
                        ),
                        "severity": 3,
                        "source": "pietto",
                        "message": text,
                    }
                )
            # Names that differ only in letter case, where paths ignore case,
            # name one file to the editor: it shows neither file's diagnostics.
            names: dict[Path, list[str]] = {}
            for path in report.paths:
                names.setdefault(_join(root, path), []).append(path)
            for path, named in names.items():
                if len(named) > 1:
                    found[path] = [
                        _alert(
                            "is selected under {} names that differ only in"
                            " letter case: {}. Rename one of them.",
                            sorted(named),
                        )
                    ]
        message = "\n".join(root_errors)
        if root_errors and config.is_file():
            found.setdefault(config, []).extend(
                _editor_diagnostic(text) for text in root_errors
            )
            message = ""
        if message and self.shown.get(index) != message:
            self._send(
                {
                    "jsonrpc": "2.0",
                    "method": "window/showMessage",
                    "params": {
                        "type": 1,
                        "message": f"Pietto project root {root}: {message}",
                    },
                }
            )
        self.shown[index] = message
        for key, path in tuple(self.published.values()):
            if key == ("root", index) and path is not None:
                found.setdefault(path, [])
        # A root keeps an unselected path only while it has diagnostics there;
        # a path left with none is cleared and handed on by `_sweep`.
        self.extras[index] = (
            frozenset(path for path, diagnostics in found.items() if diagnostics)
            | {config}
        ) - selections[index]
        for path, diagnostics in found.items():
            for uri in self._uris(path) or (path.as_uri(),):
                owner = self._owner(uri, path)
                document = self.documents.get(uri)
                if owner == ("root", index) and (
                    diagnostics or uri in self.published or document is not None
                ):
                    self._publish(
                        uri,
                        ("root", index),
                        path,
                        diagnostics,
                        document.version if document else None,
                    )
                elif owner is not None and owner[0] in ("roots", "uris"):
                    self._publish_alert(uri, owner, path)
        self._sweep()

    def _sweep(self) -> None:
        """Clear each published URI whose owner changed and hand it to its
        new owner, so that no unit overwrites or clears another's."""

        for uri, (key, path) in list(self.published.items()):
            owner = self._owner(uri, path)
            if owner == key or uri not in self.published:  # or cleared meanwhile
                continue
            if owner is not None and owner[0] in ("roots", "uris"):
                self._publish_alert(uri, owner, path)
                continue
            document = self.documents.get(uri)
            self._publish(uri, key, path, [], document.version if document else None)
            if owner is not None and owner[0] in ("root", "file"):
                self.dirty[owner] = None

    def _publish_alert(self, uri: str, owner: _Key, path: Path | None) -> None:
        """Publish the one error of a path that two or more roots select, or
        that is open under two or more URIs; neither picks a winner."""

        if self.published.get(uri, (None,))[0] == owner:
            return
        kind, members = owner
        assert isinstance(members, tuple)
        if kind == "roots":
            names = [str(self.roots[index]) for index in members]
            text = "belongs to {} project roots: {}. Keep one of them in projectRoots."
        else:
            names = [str(member) for member in members]
            text = "is open under {} URIs: {}. Keep one of them open."
        document = self.documents.get(uri)
        self._publish(
            uri,
            owner,
            path,
            [_alert(text, names)],
            document.version if document else None,
        )

    def _owner(self, uri: str, path: Path | None) -> _Key | None:
        document = self.documents.get(uri)
        if document is not None and document.refused:
            return ("refused", uri)
        if path is not None:
            indexes = (
                tuple(
                    index
                    for index, selection in enumerate(self.selections)
                    if path in selection
                )
                or tuple(
                    index for index, extra in enumerate(self.extras) if path in extra
                )[:1]
            )
            if indexes:
                uris = self._uris(path)
                if len(uris) > 1:
                    return ("uris", uris) if uri in uris else None
                if uri != self._uri(path):
                    return None
                return ("root", indexes[0]) if len(indexes) == 1 else ("roots", indexes)
        return ("file", uri) if document is not None else None

    def _uris(self, path: Path) -> tuple[str, ...]:
        """The URIs of the open documents at `path`, in code-point order."""

        return tuple(
            sorted(
                uri for uri, document in self.documents.items() if document.path == path
            )
        )

    def _uri(self, path: Path) -> str:
        """The URI of the one open document at `path`, or else the file URI."""

        uris = self._uris(path)
        return uris[0] if len(uris) == 1 else path.as_uri()

    def _table(
        self,
        root: Path,
        report: ProjectDiagnosticsReport,
        path: Path,
        tables: dict[Path, _Lines],
    ) -> _Lines:
        if path not in tables:
            relative = path.relative_to(root).as_posix() if path != root else ""
            uris = self._uris(path)
            document = self.documents.get(uris[0]) if len(uris) == 1 else None
            tables[path] = _Lines(
                report.texts.get(relative),
                open_buffer=document is not None and not document.refused,
            )
        return tables[path]

    def _location(
        self,
        root: Path,
        report: ProjectDiagnosticsReport,
        location: SourceLocation,
    ) -> dict[str, object]:
        assert location.path is not None
        path = _join(root, location.path)
        return {
            "uri": self._uri(path),
            "range": self._table(root, report, path, {}).range(location),
        }

    def _editor_request(
        self, request_id: int | str, method: str, params: dict[str, object]
    ) -> None:
        item = _field(params, "textDocument")
        uri = item.get("uri")
        if not isinstance(uri, str):
            self._error(request_id, -32602, "Invalid params")
            return
        position = (
            _position(params) if method != "textDocument/documentSymbol" else None
        )
        if method != "textDocument/documentSymbol" and position is None:
            self._error(request_id, -32602, "Invalid params")
            return
        document = self.documents.get(uri)
        path = document.path if document is not None else _absolute_uri_path(uri)
        owner = self._owner(uri, path)
        if owner is None or owner[0] not in {"file", "root"}:
            self._send_editor_result(request_id, method, None, uri=uri)
            return
        snapshot = self.snapshots.get(owner)
        if snapshot is None or snapshot.epoch != self.epochs.get(owner, 0):
            self._send_editor_result(request_id, method, None, uri=uri)
            return
        facts = snapshot.facts.get(path)
        if facts is None:
            self._send_editor_result(request_id, method, None, uri=uri)
            return
        if method == "textDocument/documentSymbol":
            self._send_editor_result(request_id, method, facts, snapshot.tables, uri)
            return
        assert position is not None
        table = snapshot.tables.get(path)
        if table is None:
            self._send_editor_result(request_id, method, None, uri=uri)
            return
        result = _editor_use_at(facts, table, position)
        if (
            result is not None
            and result.target is not None
            and not self._target_available(result.target, owner)
        ):
            result = None
        self._send_editor_result(request_id, method, result, snapshot.tables, uri)

    def _target_available(self, target: EditorDeclaration, owner: _Key) -> bool:
        if target.location.path is None:
            return owner[0] == "file"
        path = Path(target.location.path)
        uri = self._uri(path)
        snapshot = self.snapshots.get(owner)
        return (
            self._owner(uri, path) == owner
            and snapshot is not None
            and path in snapshot.facts
        )

    def _send_editor_result(
        self,
        request_id: int | str,
        method: str,
        value: EditorFacts | EditorUse | None,
        tables: Mapping[Path | None, _Lines] | None = None,
        uri: str | None = None,
    ) -> None:
        tables = {} if tables is None else tables
        if method == "textDocument/documentSymbol":
            facts = value if isinstance(value, EditorFacts) else EditorFacts()
            result: object = _document_symbols(
                facts, self.hierarchical_symbols, tables, uri
            )
        elif method == "textDocument/hover":
            result = (
                _hover(value, self.hover_plaintext, tables)
                if isinstance(value, EditorUse)
                else None
            )
        else:
            target_uri = uri
            if (
                isinstance(value, EditorUse)
                and value.target is not None
                and value.target.location.path is not None
            ):
                target_uri = self._uri(Path(value.target.location.path))
            result = (
                _definition(value, tables, target_uri)
                if isinstance(value, EditorUse)
                else None
            )
        self._send({"jsonrpc": "2.0", "id": request_id, "result": result})

    # Output.

    def _publish(
        self,
        uri: str,
        owner: _Key,
        path: Path | None,
        diagnostics: list[dict[str, object]],
        version: int | None,
    ) -> None:
        if diagnostics and path is not None:
            # A client may take another URI of this path for the same file,
            # so a set that no unit owns there (never an open one) is cleared
            # first, never after.
            for other, (key, other_path) in list(self.published.items()):
                if other != uri and other_path == path and not self._owner(other, path):
                    self._publish(other, key, path, [], None)
        params: dict[str, object] = {"uri": uri, "diagnostics": diagnostics}
        if version is not None:
            params["version"] = version
        self._send(
            {
                "jsonrpc": "2.0",
                "method": "textDocument/publishDiagnostics",
                "params": params,
            }
        )
        if diagnostics:
            self.published[uri] = (owner, path)
        else:
            self.published.pop(uri, None)

    def _error(self, request_id: int | str | None, code: int, message: str) -> None:
        self._send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": code, "message": message},
            }
        )

    def _send(self, message: dict[str, object]) -> None:
        body = json.dumps(message, separators=(",", ":")).encode("ascii")
        try:
            self.stdout.write(b"Content-Length: %d\r\n\r\n%b" % (len(body), body))
            self.stdout.flush()
        except (OSError, ValueError) as error:
            raise _Closed from error


class _Lines:
    """Converts Pietto locations (one-based lines, one-based code-point
    columns, a leading BOM not counted) to LSP UTF-16 ranges in one text."""

    def __init__(self, text: str | None, *, open_buffer: bool) -> None:
        text = text or ""
        bom = text.startswith("\ufeff")
        self.lines = _LINE_BREAK.split(text[1:] if bom else text)
        # An editor shows a disk file without its BOM, but an open buffer
        # that starts with U+FEFF holds it on line 1.
        self.shift = 1 if bom and open_buffer else 0

    def range(self, location: SourceLocation) -> dict[str, object]:
        start = self.position(location.line, location.column)
        end = (
            start
            if location.end_line is None or location.end_column is None
            else self.position(location.end_line, location.end_column)
        )
        return {"start": start, "end": end}

    def position(self, line: int, column: int) -> dict[str, int]:
        if line > len(self.lines):
            index, prefix = len(self.lines) - 1, self.lines[-1]
        else:
            index = max(line, 1) - 1
            prefix = self.lines[index][: max(column, 1) - 1]
        character = len(prefix.encode("utf-16-le")) // 2
        return {
            "line": index,
            "character": character + (self.shift if index == 0 else 0),
        }


def uri_to_path(uri: str, *, windows: bool = os.name == "nt") -> PurePath | None:
    """The filesystem path of a `file:` URI, or None for any other URI."""

    parts = urlsplit(uri)
    if parts.scheme.lower() != "file":
        return None
    path = unquote(parts.path)
    host = unquote(parts.netloc)
    host = "" if host.lower() == "localhost" else host
    if windows:
        if host:
            return PureWindowsPath(f"//{host}{path}")
        return PureWindowsPath(path[1:] if _WINDOWS_DRIVE.match(path) else path)
    return None if host else PurePosixPath(path)


def _check_text(text: str) -> tuple[Diagnostic, ...]:
    """The diagnostics of `pietto check FILE --format json` for `text`."""

    diagnostics, _ = _check_text_with_editor_facts(text)
    return diagnostics


def _check_text_with_editor_facts(
    text: str, *, path: str | None = None
) -> tuple[tuple[Diagnostic, ...], EditorFacts]:
    """Check one buffer once and retain facts only on semantic success."""

    parsed = parse_source(text)
    if parsed.ast is None or any(
        diagnostic.severity is Severity.ERROR for diagnostic in parsed.diagnostics
    ):
        return parsed.diagnostics, EditorFacts()
    semantic = analyze(parsed.ast)
    diagnostics = (*parsed.diagnostics, *semantic.diagnostics)
    if any(diagnostic.severity is Severity.ERROR for diagnostic in diagnostics):
        return diagnostics, EditorFacts()
    return diagnostics, single_file_editor_facts(parsed.ast, semantic.model, path=path)


def _absolute_uri_path(uri: str) -> Path | None:
    path = uri_to_path(uri)
    return Path(path) if path is not None and path.is_absolute() else None


def _position(params: dict[str, object]) -> dict[str, int] | None:
    position = _field(params, "position")
    line, character = position.get("line"), position.get("character")
    if type(line) is not int or type(character) is not int or line < 0 or character < 0:
        return None
    return {"line": line, "character": character}


def _editor_use_at(
    facts: EditorFacts, lines: _Lines, position: dict[str, int]
) -> EditorUse | None:
    matches = tuple(
        use for use in facts.uses if _contains(lines.range(use.location), position)
    )
    return matches[0] if len(matches) == 1 else None


def _contains(range_: dict[str, object], position: dict[str, int]) -> bool:
    start = range_["start"]
    end = range_["end"]
    assert isinstance(start, dict) and isinstance(end, dict)
    lower = (start["line"], start["character"])
    upper = (end["line"], end["character"])
    point = (position["line"], position["character"])
    return lower <= point < upper


def _hover(
    use: EditorUse, plaintext: bool, tables: Mapping[Path | None, _Lines]
) -> dict[str, object] | None:
    range_ = _fact_range(use.location, tables)
    if range_ is None:
        return None
    contents: object = (
        {"kind": "plaintext", "value": use.detail}
        if plaintext
        else {"language": "pietto", "value": use.detail}
    )
    return {"contents": contents, "range": range_}


def _definition(
    use: EditorUse, tables: Mapping[Path | None, _Lines], target_uri: str | None
) -> dict[str, object] | None:
    target = use.target
    if target is None:
        return None
    range_ = _fact_range(target.location, tables)
    if range_ is None:
        return None
    if target_uri is None:
        return None
    return {
        "uri": target_uri,
        "range": range_,
    }


def _document_symbols(
    facts: EditorFacts,
    hierarchical: bool,
    tables: Mapping[Path | None, _Lines],
    uri: str | None,
) -> list[dict[str, object]]:
    if hierarchical:
        return [
            {
                "name": item.name,
                "detail": item.detail,
                "kind": item.kind,
                "range": range_,
                "selectionRange": range_,
            }
            for item in facts.declarations
            if (range_ := _fact_range(item.location, tables)) is not None
        ]
    return [
        {
            "name": item.name,
            "kind": item.kind,
            "location": {
                "uri": uri,
                "range": range_,
            },
        }
        for item in facts.declarations
        if uri is not None
        and (range_ := _fact_range(item.location, tables)) is not None
    ]


def _fact_range(
    location: SourceLocation, tables: Mapping[Path | None, _Lines]
) -> dict[str, object] | None:
    path = Path(location.path) if location.path is not None else None
    table = tables.get(path)
    return table.range(location) if table is not None else None


def _root_editor_facts(facts: EditorFacts, root: Path) -> EditorFacts:
    """Attach one selected root while retaining each exact relative occurrence."""

    declarations = tuple(
        _root_editor_declaration(item, root) for item in facts.declarations
    )
    return EditorFacts(
        declarations=declarations,
        uses=tuple(
            EditorUse(
                location=_root_location(item.location, root),
                detail=item.detail,
                target=(
                    _root_editor_declaration(item.target, root)
                    if item.target is not None
                    else None
                ),
            )
            for item in facts.uses
        ),
    )


def _root_editor_declaration(item: EditorDeclaration, root: Path) -> EditorDeclaration:
    return EditorDeclaration(
        location=_root_location(item.location, root),
        name=item.name,
        kind=item.kind,
        detail=item.detail,
    )


def _root_location(location: SourceLocation, root: Path) -> SourceLocation:
    return SourceLocation(
        path=(str(_join(root, location.path)) if location.path is not None else None),
        line=location.line,
        column=location.column,
        end_line=location.end_line,
        end_column=location.end_column,
    )


def _entries(root: Path) -> dict[Path, str | None]:
    """Each path that `check --project` selects at `root`, mapped to its
    selected entry, or to None where two entries name one path (spellings
    that differ only in letter case, where paths ignore case)."""

    try:
        paths = selected_project_paths(root)
    except (OSError, ValueError):
        return {}
    entries: dict[Path, str | None] = {}
    for path in paths:
        joined = _join(root, path)
        entries[joined] = None if joined in entries else path
    return entries


def _join(root: Path, relative: str) -> Path:
    return root.joinpath(*relative.split("/"))


def _unit_order(unit: _Key) -> tuple[int, str]:
    kind, value = unit
    return (0, f"{value:08d}") if kind == "root" else (1, str(value))


def _field(value: object, *names: str) -> dict[str, object]:
    for name in names:
        value = value.get(name) if isinstance(value, dict) else None
    return value if isinstance(value, dict) else {}


def _lsp_diagnostic(
    diagnostic: Diagnostic,
    range_: dict[str, object],
    related: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    message = diagnostic.message
    # A hint that the message already carries is shown once.
    if diagnostic.suggestion is not None and diagnostic.suggestion not in message:
        message = f"{message}\n{diagnostic.suggestion}"
    item: dict[str, object] = {
        "range": range_,
        "severity": 1 if diagnostic.severity is Severity.ERROR else 2,
        "code": diagnostic.code,
        "source": "pietto",
        "message": message,
    }
    if related:
        item["relatedInformation"] = related
    return item


def _alert(text: str, names: list[str]) -> dict[str, object]:
    """The one error of a file that two or more roots, URIs or names share;
    `text` takes the count and the listed names."""

    count = "two" if len(names) == 2 else str(len(names))
    listed = f"{', '.join(names[:-1])} and {names[-1]}"
    return _editor_diagnostic("This file " + text.format(count, listed))


def _editor_diagnostic(message: str) -> dict[str, object]:
    """An editor-only error at the file start, without a PIE code."""

    zero = {"line": 0, "character": 0}
    return {
        "range": {"start": zero, "end": zero},
        "severity": 1,
        "source": "pietto",
        "message": message,
    }
