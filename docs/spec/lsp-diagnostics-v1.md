# LSP diagnostics v1

`pietto lsp` is an alpha Language Server Protocol server. This page specifies
its diagnostic protocol; [editor facts v1](lsp-editor-facts-v1.md) specifies
hover, definition and document symbols. Neither contract adds
an editor facts format, a CLI JSON command, or any compiler semantics.

The server checks a document or project for editor diagnostics and facts. It has no
completion, references, workspace symbols, code actions, formatting,
SQL preview, execution, package, compiled-build, workspace-edit or
configuration-update operation. A request for an unsupported method receives
JSON-RPC `-32601` after initialization.

This contract remains alpha until the Phase82 freeze. Editor consumers must
not infer facts or stability beyond the advertised, specified capabilities.

## Transport and lifecycle

The command is `pietto lsp`; `pietto lsp --stdio` is an equivalent spelling.
It uses JSON-RPC 2.0 over standard input and standard output with LSP
`Content-Length` framing and UTF-8 request bodies. Standard output contains
only framed JSON-RPC messages. A malformed header or truncated frame writes
`pietto lsp: invalid message header; stopping` to standard error and exits
with status 1. Invalid JSON produces JSON-RPC `-32700` and does not by itself
end a valid session. Batch requests are rejected with `-32600`.

The session begins in the uninitialized state. `initialize` is the sole
accepted request there; another request receives `-32002`. A successful
`shutdown` request returns `null`, stops pending analysis, and moves the
session to the shutdown state; later requests receive `-32600`. The `exit`
notification ends with status 0 only after shutdown, and with status 1
otherwise. Unknown notifications and `$/cancelRequest` add no behavior.

The successful `initialize` result has exactly these advertised capabilities:

```json
{
  "positionEncoding": "utf-16",
  "textDocumentSync": {"openClose": true, "change": 1},
  "hoverProvider": true,
  "definitionProvider": true,
  "documentSymbolProvider": true
}
```

It also includes `serverInfo` with name `pietto` and the running package
version. `change: 1` means full-document synchronization.

## Initialization and roots

`initializationOptions.projectRoots` is optional. If present, it must be a
list of distinct absolute filesystem paths. Paths are normalized and resolved
for duplicate detection, so two spellings of a directory, including a symlink,
are not distinct. Any other shape, a relative path, or a duplicate returns
`-32602` with:

```
projectRoots must be a list of distinct absolute paths
```

No option or an empty list means that no project roots exist. The server never
derives roots from a workspace folder, current directory, URI, or configuration
file. Roots are fixed for the session; changing them requires a new server.

For every root, the server uses the same project selection as
`pietto check --project ROOT`. It publishes diagnostics for selected open and
closed modules. A selected module with exactly one open `file:` URI uses that
whole unsaved buffer as a diagnostic overlay. The overlay changes no source
file and is never a trusted source read, compilation input, emission input,
package input, or execution input.

For a schema-version-2 project, partial analysis may omit an erroneous module
and its direct or transitive importers, then check the remaining modules. It
uses at most five passes. An omitted importer receives the Information
diagnostic described below. Other schema versions retain the command-line
all-or-nothing project behavior.

A document that is not selected by exactly one configured root is checked as
the equivalent of `pietto check FILE` against its whole open text. An isolated
module can therefore show unresolved-import diagnostics until its root is
configured.

## Documents, paths, and freshness

The server consumes `textDocument/didOpen`, `textDocument/didChange`, and
`textDocument/didClose`. `languageId` is not an admission check. A supported
change has exactly one `contentChanges` item with a string `text` and no
`range`; an empty text string is valid. A ranged change, an empty or multi-item
`contentChanges` list, or another malformed change refuses the document until
a new `didOpen` arrives. The refusal publishes the editor-only message in the
table below.

When document versions are integers, a change whose version is no newer than
the stored version is ignored. A diagnostic set calculated for an older
document epoch is dropped, rather than published after a newer open, change,
or close. Each published set for a versioned open document carries that
document version.

Positions use zero-based UTF-16 code units. Pietto source locations are
converted from their one-based source positions; CRLF, CR, and LF are line
breaks, astral characters use two UTF-16 units, and ranges clamp at the last
available position. An opened buffer retains a leading U+FEFF in its shown
range, while a closed disk document does not. Unpaired UTF-16 surrogate code
points in an opened buffer are replaced by U+FFFD before checking.

Only `file:` URIs map to filesystem paths. `localhost` is local; on Windows,
drive-letter, UNC, and `wsl$` file URIs map through Windows path rules. Other
URI schemes remain standalone documents.

One logical file may not choose a winner among aliases. If multiple configured
roots select it, or it is open under multiple URIs, each relevant URI receives
only the corresponding editor-only conflict diagnostic. Its project check then
uses disk content rather than any competing buffer. Before a previously owned
URI is replaced by a diagnostic set for the same path, the server clears the
unowned stale URI first.

## Diagnostics

The server emits `textDocument/publishDiagnostics` with the URI, ordered
diagnostics, and a version when one is available. Compiler diagnostics preserve
the existing diagnostic code, compiler order, source range, and `source` value
`pietto`. Error severity is LSP `1`; warning severity is LSP `2`. The displayed
message is the compiler message plus a newline and suggestion only when that
suggestion is not already a substring of the message.

If the client sets
`capabilities.textDocument.publishDiagnostics.relatedInformation` to `true`, a
project diagnostic with related locations includes ordered
`relatedInformation` items. Without that capability the field is omitted.

Project loading/configuration errors are not compiler `PIE-*` diagnostics.
They are editor-only errors formatted as `project error: <kind>: <message>`.
They publish at their named file when present, otherwise at `pietto.toml` when
it exists, otherwise once through `window/showMessage` as
`Pietto project root <root>: <messages>`.

The following editor-only diagnostics have no `code`, use `source: "pietto"`,
LSP Error severity `1`, and a zero-length range at the document start unless
noted otherwise. They do not reserve a `PIE-*` code.

| Condition | Message |
| --- | --- |
| Two or more roots select one file | `This file belongs to two project roots: <root 1> and <root 2>. Keep one of them in projectRoots.` |
| One file is open under two or more URIs | `This file is open under two URIs: <uri 1> and <uri 2>. Keep one of them open.` |
| A case-insensitive path represents two selected names that differ only by letter case | `This file is selected under two names that differ only in letter case: <name 1> and <name 2>. Rename one of them.` |
| Unsupported partial `didChange` | `Pietto needs whole-document changes; reopen this file.` |
| Project loading/configuration failure | `project error: <kind>: <message>` |

The first three lists are in code-point order. They replace every ordinary
diagnostic for the affected file; they do not select a root, URI, filename, or
buffer winner.

When partial project analysis skips an importer, it instead receives one
Information diagnostic: `Not checked: this module imports <file>, which has
errors.` It has LSP severity `3`, `source: "pietto"`, no `code`, and the
range of the import. More than one file is listed in code-point order using
the ordinary English list form.

## Resource and trust boundaries

The server reads and analyzes input for diagnostics and detached editor facts. It
does not write documents, format files, open database connections, emit SQL,
compile, package, execute, discover a workspace root, or use editor text as
trusted bytes. A selected project still applies its normal source-selection,
read, parse, semantic, and import rules to every non-overlay input.

The three editor requests use detached facts from the same analysis, under
[their contract](lsp-editor-facts-v1.md). The protocol provides no general
editor-model artifact, semantic-metadata dump or backend capability state.
Consumers must not depend on private server implementation details.
