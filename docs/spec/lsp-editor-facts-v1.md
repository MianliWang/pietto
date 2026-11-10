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

A server makes a snapshot only from the same analysis that produces the
current diagnostics. A single file has facts only when its check succeeds, and
uses the existing semantic result. For an explicit-module project, the editor
check projects facts from its final partial-analysis pass, only when that pass
does not stop and stays within the recursion limit;
`ProjectDiagnosticsReport` remains diagnostics-only. The editor pass projects
no facts for a legacy-flat (`schema_version = 1`) root, so its selected
modules have none.

Every entry binds its selected-root identity, exact source URI, document epoch,
and overlay provenance. A snapshot is discarded on open, change, close, root
conflict, URI or selected-name conflict, refusal, observed configuration/source-selection change, or a
newer analysis epoch. A failed or omitted module, or one with an error of its
own, produces no facts. Any other module keeps its facts from that pass,
except a type use whose canonical type is unknown, as when an alias base or an
imported name is unknown, ambiguous, blocked or cyclic. A use whose target
belongs to a module without facts has neither hover nor definition. The server
does not replace an ambiguous overlay with disk text.

There is no filesystem watcher or configuration-update method in this version.
Closed project files belong to the most recent observed root epoch; document
notifications trigger reanalysis. Requests do not inspect disk to detect an
otherwise unobserved external edit.

The projection preserves every retained exact occurrence and its source
order. It must not deduplicate uses by spelling, canonical name, type, path,
or target. A lookup whose range covers more than one retained fact, or whose
identity is absent, returns no result.

Returned locations retain the unique open URI spelling for their document;
closed project targets use their filesystem URI. A canonical path must not
replace the URI of an unsaved buffer. Conflicting selected names suppress
both that document's facts and uses that would navigate to it. Facts follow
the unit whose analysis produces the document's diagnostics: a URI that
receives the URI-alias conflict diagnostic has no facts, and no use navigates
to its path. A URI whose document is checked as its own file, with
diagnostics of its own, answers from its own buffer, and a target in that
buffer is returned under that URI, never under another spelling of its path.

## First facts

The first definition-capable facts are only these exact resolution paths:

| Context | Use | Exact target |
| --- | --- | --- |
| Single file | `FromClause.span` | `SemanticModel.from_resolutions[from_clause]`, then that authored declaration's span |
| Single file | `TypeExpr.span` | `SemanticModel.type_resolutions[type_expr].definition`; a builtin or unresolved type has no target |
| Schema-v2 project | relation `FromClause.span` | the owning module environment's `find_from_clause`, then `target_symbol.target_occurrence`; a relation let or a table-function input is no top-level declaration, so a use that reads one has no fact |
| Schema-v2 project | `TypeExpr.span` | the owning module type environment's `find_type_expr`, then `direct_symbol.target_occurrence`; a builtin or missing direct symbol has no target |

The project target is valid only when its declaration occurrence belongs to a
module with facts in the same selected-root analysis. A bare module path,
name, import alias, re-export, field, let, parameter, or same-spelling
declaration is never used to choose a replacement target.

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

A request waits while an analysis of its URI, or of a project root that
contains its path, is scheduled or running; that includes a root analysis
that an edit of another file of the root schedules. Pending analyses of other
units do not hold it, although they can run before one it waits for (see
[Performance and verification](#performance-and-verification)). A waiting
request starts
no analysis and is answered once those analyses end, from the snapshots they
leave. If an open, change or close of its URI arrives first, the request is
stale and has no result. No response order is promised: a request on another
document can be answered before an earlier one that still waits. `shutdown`
stops pending analysis, so it answers each waiting request with no result
before its own response; `$/cancelRequest` adds no behavior.

Hover and definition return `null`, and document symbols return `[]`, for a
missing snapshot, a stale request, a refused document, an omitted
partial-project module, a module with an error of its own, a module of a
legacy-flat root, or a URI that receives a root, URI or selected-name alias
conflict diagnostic. A use whose
type is unknown, or whose target belongs to a module without facts, has
neither hover nor definition. An unsupported or ambiguous position has no
hover or definition result. A builtin can have a known hover type but has no
authored definition target; that does not suppress the document's other
symbols. These paths do not publish an editor-only diagnostic, reread the
document, or change diagnostics. Malformed request parameters return JSON-RPC
`-32602` at once, rather than masquerading as an unknown symbol. A string URI
that maps to no filesystem path, such as a `file:` URI that does not parse, is
not malformed: it names a standalone document, so a request on it is answered
like any other, with no result unless that URI is open.

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

Facts are projected at most once per existing analysis: from a single file's
successful check, or from a project's final pass when it does not stop. The
projection is bounded by the checked modules' declaration and exact-resolution
occurrences. Each request performs only current-epoch index lookup: zero
parse, semantic-analysis, project-check, or IR calls. There is no persistent
cache.

The server runs one analysis at a time, and always the first pending one in a
fixed order: every root, in `projectRoots` order, before any document checked
as its own file, and those in URI code-point order. A waiting request is
answered once no analysis of its URI, or of a root that contains its path, is
pending, including analyses that later edits of other files of that root
schedule. Until then, pending analyses earlier in that order also run first,
so a request on a document checked as its own file, even one outside every
root, waits while any root is analysed again before its own document is. A
wait has no bound while edits keep an analysis that it waits for, or one
earlier in that order, pending.

No retained measurement covers editor latency. An earlier ED01 observation of
the diagnostics server alone kept no raw record, so it is neither a baseline
nor evidence for JOIN, FD, large-project, cancellation, Windows, or UI
behavior. ED.01 and ED.02 set no latency budget; a later editor Gate 1 sets a
representative corpus and budget after measuring snapshot construction and
all three request families.

Tests must cover single-file and cross-module type/from targets; import aliases
and re-exports; stale versions and requests that wait for an analysis; root
and URI aliases; UTF-16 with CRLF and lone CR; partial-project omissions and
modules with errors of their own; overlapping ranges; source ordering; and
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
