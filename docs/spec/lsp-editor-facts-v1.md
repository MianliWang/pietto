# LSP editor facts v1 — implementation contract

ED.02 approves the standard-LSP, ephemeral-snapshot direction for the selected
editor work: hover, go-to-definition and document symbols. This alpha contract
is implemented by `pietto lsp`. It adds no CLI command, JSON artifact, or
post-alpha compatibility promise. [LSP diagnostics v1](lsp-diagnostics-v1.md)
continues to specify the diagnostic protocol.

## Boundary

The server keeps one immutable, in-process snapshot for an analysis
of one current document or project epoch. It answers only standard LSP
`textDocument/hover`, `textDocument/definition`, and
`textDocument/documentSymbol` requests from that snapshot. The requests do
not parse, analyze, check a project, build IR, read disk, select a root, or
fall back to a name lookup.

The snapshot is not serialized, returned as an artifact, retained across a
server session, or shared with another process. It holds detached values only:
URI, document/root epoch, source ranges, declaration kind, display/type text,
and exact target identity. It never exposes AST, semantic/project result,
overlay source, trusted opened bytes, source carrier, or resolver object.

The Semantic Metadata Artifact v1 is not this snapshot: it is single-file,
requires parse, semantics and IR success, and deliberately exposes no partial
facts. The project relation-column view also cannot supply this contract: it
has no use ranges, overlay/version identity, or partial-project facts. Neither
format changes here.

## Snapshot admission and invalidation

A server makes a snapshot only from the same successful analysis that produces
the current diagnostics. A single file may use the existing semantic result.
For an explicit-module project, a sibling internal editor pass projects facts
from the same final partial-analysis pass; `ProjectDiagnosticsReport` remains
diagnostics-only.

Every entry binds its selected-root identity, exact source URI, document epoch,
and overlay provenance. A snapshot is discarded on open, change, close, root
conflict, URI or selected-name conflict, refusal, observed configuration/source-selection change, or a
newer analysis epoch. A failed or omitted module produces no facts. The server
does not replace an ambiguous overlay with disk text.

There is no filesystem watcher or configuration-update method in this version.
Closed project files belong to the most recent observed root epoch; document
notifications trigger reanalysis. Requests do not inspect disk to detect an
otherwise unobserved external edit.

The projection preserves all occurrences and their source order. It must not
deduplicate uses by spelling, canonical name, type, path, or target. A lookup
whose range covers more than one retained fact, or whose identity is absent,
returns no result.

Returned locations retain the unique open URI spelling for their document;
closed project targets use their filesystem URI. A canonical path must not
replace the URI of an unsaved buffer. Conflicting selected names suppress
both that document's facts and uses that would navigate to it.

## First facts

The first definition-capable facts are only these exact resolution paths:

| Context | Use | Exact target |
| --- | --- | --- |
| Single file | `FromClause.span` | `SemanticModel.from_resolutions[from_clause]`, then that authored declaration's span |
| Single file | `TypeExpr.span` | `SemanticModel.type_resolutions[type_expr].definition`; a builtin or unresolved type has no target |
| Schema-v2 project | relation `FromClause.span` | the owning module environment's `find_from_clause`, then `target_symbol.target_occurrence` |
| Schema-v2 project | `TypeExpr.span` | the owning module type environment's `find_type_expr`, then `direct_symbol.target_occurrence`; a builtin or missing direct symbol has no target |

The project target is valid only when its declaration occurrence belongs to the
same successful selected-root analysis. A bare module path, name, import alias,
re-export, field, let, parameter, or same-spelling declaration is never used to
choose a replacement target.

Hover may return a plain-text declaration kind and canonical type/display text
only when the snapshot holds both a unique source range and that exact fact. It
does not infer a type from a name or emit a partial approximation. Definition
returns one standard `Location` only for a retained exact target; otherwise it
returns `null`.

Document symbols list retained named top-level declarations in authored source order.
Until a separate source-range fact exists, both `range` and `selectionRange`
are the declaration's full span. Symbols have no definition target merely
because they are shown.

## Fail-closed request behavior

Hover and definition return `null`, and document symbols return `[]`, for a
missing or stale snapshot, a refused document, an omitted partial-project
module, or a root, URI or selected-name alias conflict. An unsupported or ambiguous position
has no hover or definition result. A builtin can have a known hover type but
has no authored definition target; that does not suppress the document's
other symbols. These paths do not publish an editor-only diagnostic, reread
the document, or change diagnostics. Malformed request parameters return
JSON-RPC `-32602`, rather than masquerading as an unknown symbol.

## Capability and client boundary

`initialize` advertises
`hoverProvider`, `definitionProvider`, and `documentSymbolProvider` alongside
the existing diagnostic capabilities. The existing VS Code LSP client can
consume these standard capabilities; it needs no private-core import, custom
transport, or editor-facts artifact.

Client capabilities govern representation: use a plaintext `MarkupContent`
hover when the client supports it, otherwise a standard language/value
`MarkedString`. Return `DocumentSymbol[]` when hierarchical document symbols
are supported and flat `SymbolInformation[]` otherwise. Keep both projections
in the same source order, use supported symbol kinds, and never mix the two
array formats. Definition uses `Location`, so no location-link capability is
required.

No completion, references, workspace symbols, code action, formatting, model
view, capability matrix, SQL preview change, execution, or workspace mutation
is included.

## Performance and verification

Snapshot construction runs once per existing analysis and is bounded by the
retained declaration and exact-resolution occurrences. Each request performs
only current-epoch index lookup: zero parse, semantic-analysis, project-check,
or IR calls. There is no persistent cache.

The ED01 observation at `/tmp/pietto-ed01-lsp-observation/RESULT.md` measured
the current diagnostics server only: a 45–109 byte single file and a two-module
199 byte schema-v2 project. It is not a latency budget or evidence for JOIN,
FD, large-project, cancellation, Windows, or UI behavior. Gate 1 must set a
representative corpus and budget after measuring snapshot construction and all
three request families.

Tests must cover single-file and cross-module type/from targets; import aliases
and re-exports; stale versions; root and URI aliases; UTF-16 with CRLF and
lone CR; partial-project omissions; overlapping ranges; source ordering; and
proof that each request makes no analysis call. Each returned range and target
must come from the exact retained occurrence, not a reconstructed name.

## External-reference review

The reviewed source is Microsoft's LSP 3.17 specification:
[hover](https://raw.githubusercontent.com/microsoft/language-server-protocol/gh-pages/_specifications/lsp/3.17/language/hover.md),
[definition](https://raw.githubusercontent.com/microsoft/language-server-protocol/gh-pages/_specifications/lsp/3.17/language/definition.md), and
[document symbols](https://raw.githubusercontent.com/microsoft/language-server-protocol/gh-pages/_specifications/lsp/3.17/language/documentSymbol.md).

| Field | Review |
| --- | --- |
| Snapshot/date | LSP 3.17 source, reviewed 2026-11-08. |
| Problem/constraints | Supply three editor features through the existing LSP connection. |
| Semantic/identity model | Protocol ranges and locations carry Pietto-owned identity; they do not establish binding. |
| Layering/dependency direction | Core facts feed protocol responses; the extension consumes them. |
| Algorithms/data structures/complexity | The protocol selects no analysis algorithm; this proposal uses bounded ephemeral facts. |
| Interface/version/capability model | Standard responses and client capability negotiation; Pietto features remain alpha. |
| Testing/operational lifecycle | Test response variants, ranges, stale epochs and empty results through the public session. |
| Pitfalls/migration costs | Rich symbols and hover content require capability handling; full spans have less precise selection. |
| Disposition | Reuse the existing standard wire messages. |
| WHAT_NOT_TO_COPY | No inferred bindings, new artifact, client-side semantic resolver or persistent cache. |
| Pietto owner affected | Semantic projection, project editor analysis and LSP server. |
