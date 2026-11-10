# LSP editor facts v1 — implementation contract

ED.02 approves the standard-LSP, ephemeral-snapshot direction for the selected
editor work: hover, go-to-definition and document symbols. ED.03 adds
[formatting](#formatting) of the open buffer, which reads no snapshot. This
alpha contract is implemented by `pietto lsp`. It adds no CLI command, JSON
artifact, or post-alpha compatibility promise. [LSP diagnostics
v1](lsp-diagnostics-v1.md) continues to specify the diagnostic protocol.

## Boundary

The server keeps one immutable, in-process snapshot for an analysis
of one current document or project epoch. It answers the standard LSP
`textDocument/hover`, `textDocument/definition` and
`textDocument/documentSymbol` requests, the fact requests, only from such
snapshots. The fact requests do not parse, analyze, check a project, build
IR, read disk, select a root, or fall back to a name lookup. Formatting, the
one request that parses, parses only its own buffer.

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

A fact request waits while an analysis of its URI, or of a project root that
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

## Formatting

ED.03 revises ED.02 so that `textDocument/formatting` alone parses at request
time, and only its own buffer. The server answers it as soon as it reads the
request and never holds it for a scheduled analysis, although an analysis
already running when it arrives ends before the server reads it (see
[Performance and verification](#performance-and-verification)). It runs
`pietto fmt`'s pure `format_source` on the whole current text of the document
open at the request's URI. It reads no snapshot, disk file, project root or configuration,
starts no analysis, calls no semantic, project or IR code, and writes nothing.
The result is:

- one `TextEdit` when formatting changes the buffer. Its range runs from line
  0, character 0, to the end of the buffer: the line after the last CRLF, CR
  or LF break, at that line's length in UTF-16 code units, where a leading
  U+FEFF counts as one unit of line 0, as the buffer holds it. Its `newText` is
  the formatted source, so the edit gives the bytes that `pietto fmt` prints
  for a file of the buffer's text: it keeps the leading U+FEFF and writes
  every line break as the buffer's first one, CRLF, CR or LF (LF when it has
  none);
- `[]` when the buffer is already formatted;
- `null` when `pietto fmt` would refuse the buffer: a parser error, a retired
  header line among them (PIE-P1000), a buffer over the 1,048,576-byte UTF-8
  size limit (PIE-P1006), or a `FormatRefusedError`, whose formatted source
  would exceed that limit or not keep the buffer's tokens, comments and
  blocks. It is also `null` when the URI is not open;
  for a document whose change was refused, until it is opened again; and for
  a buffer whose last open or change had unpaired UTF-16 surrogates, which the
  server holds as U+FFFD and so could not return as the client wrote them.

A refusal publishes no diagnostic and shows no message; the published
diagnostics and `pietto check` report the parser errors. `FormattingOptions`
are ignored, whatever they hold, because `pietto fmt` has one layout (D75.05):
tab size, spaces, trailing whitespace and final newlines change nothing. A
`textDocument.uri` that is not a string returns JSON-RPC `-32602`. A URI that
maps to no path, such as `untitled:Untitled-1`, formats like any other open
buffer. Formatting depends only on the buffer at its URI, so a file open under
two URIs formats each buffer apart and no root, URI or buffer wins. Range and
on-type formatting are not provided. `fmt` output may change before the
Phase82 freeze (D75.05), and the edit follows it.

## Capability and client boundary

`initialize` advertises
`hoverProvider`, `definitionProvider`, `documentSymbolProvider` and
`documentFormattingProvider` alongside
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

No completion, references, workspace symbols, code action, range or on-type
formatting, model view, capability matrix, SQL preview change, execution, or
workspace mutation is included.

## Performance and verification

Facts are projected at most once per existing analysis: from a single file's
successful check, or from a project's final pass when it does not stop. The
projection is bounded by the checked modules' declaration and exact-resolution
occurrences. Each fact request performs only current-epoch index lookup: zero
parse, semantic-analysis, project-check, or IR calls. Formatting makes one
`format_source` call on its buffer and no other. There is no persistent
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

The server reads no message while an analysis runs, so any request that
arrives then, formatting included, is answered only after that analysis ends.
Formatting then answers at once; a fact request also waits for the analyses
above.

Tests must cover single-file and cross-module type/from targets; import aliases
and re-exports; stale versions and requests that wait for an analysis; root
and URI aliases; UTF-16 with CRLF and lone CR; partial-project omissions and
modules with errors of their own; overlapping ranges; source ordering; and
proof that each request makes no analysis call. Each returned range and target
must come from the exact retained occurrence, not a reconstructed name.
Formatting tests must cover byte equality with `pietto fmt` over the `fmt`
corpus, end positions with a leading U+FEFF, CRLF, lone CR and astral
characters, every refusal path, ignored options, buffers that differ from the
disk, and an answer that no analysis holds.

### Latency measurement (ED.03 M1)

M1 measured the editor latency on 2026-11-10. ED.01 and ED.02 set no budget,
and the earlier ED01 observation, which kept no raw record, is no baseline.
The driver and the raw timings stay in the lane's scratch folder, outside Git.

- **Tree.** The Gate 0 head `ab972f36` (tree `821be1cc`), exported read-only:
  `src` tree `48358767`, `examples` tree `fb7bec97`, `tests/fixtures` tree
  `533db0f3`, `docs/worked-example.md` blob `4e226aa0`. The formatting-request
  figures and the formatting budget below are of `textDocument/formatting`,
  which ED.03 C1 adds to this contract; they ran on the C1 candidate: that
  tree with C1's `src/pietto/_lsp.py` (sha256 `3d3db78a…5608`).
- **Host.** CPython 3.13.13 on Linux x86-64 (WSL2, glibc 2.43, 32 logical
  CPUs), the shared integration host at `nice -n 19`. It was not a quiet host:
  other lanes were active, the one-minute load was 1.2 to 4.7, and a fixed
  10⁷-step reference loop took 0.150 to 0.156 s before and after every series.
  Whether these figures suffice to record the budget, or a quiet host must
  measure again, is the lead's decision at the E-C midpoint.
- **Corpus.** `examples/**/*.pietto` (11 files) and `tests/fixtures/**/*.pietto`
  (33), which together are the `fmt` test corpus; the four `pietto` blocks of
  `docs/worked-example.md`, as `rides.pietto` alone and as the schema-v2
  projects `bikes-project` (one module) and `bikes-modules` (two; the edits
  change `report.pietto`) with the page's `pietto.toml`; and generated layered
  JOIN DAGs. A DAG of depth N is one schema-v2 module `dag.pietto` with a shape
  of two `Int` fields, one source, `q0` reading the source, `q1` reading `q0`,
  and for each i from 2 to N a `query qi` reading `q(i-1)` with `inner join
  q(i-2) on q(i-1).id == q(i-2).id` and selecting two fields, at N = 4, 8, 12,
  14, 16, 18, 20 and 22, also as a single file, and at N = 24 in process only.
- **In process.** The server's own entry points, five repeats (three at N = 20
  and 22, one at 24): a single file's check with its fact projection, which
  is also timed alone; a root's check with its snapshot; `format_source`.
- **End to end.** A real `pietto lsp` over stdio, from writing a message to
  reading its answer: an open or change to the `publishDiagnostics` of that
  version (five changes, three at N ≥ 20, alternating the text with and
  without one trailing comment line); hover, definition, document symbols and
  formatting on an idle server, five each, at the first retained use; a hover
  sent with a change, and a formatting request sent 20 ms after one, five
  each (three for DAGs).

Results, as medians in milliseconds (largest sample in parentheses):

| Measure | Result |
| --- | --- |
| Single-file check with facts | examples 1.3 (9.0); fixtures 2.9 (35.7, `tests/fixtures/*/join_mvp.pietto`, 3.9 KB); `rides.pietto` 27.7; DAG files 5.6 at N = 4 to 26.3 at N = 22 |
| Fact projection alone | at most 0.1 for a file, at most 0.3 for a root snapshot, at every N |
| Root check with snapshot | `bikes-project` 24.0; `bikes-modules` 21.5; DAG N = 4: 15, 8: 26, 12: 61, 14: 120, 16: 291, 18: 790, 20: 2225, 22: 6540, 24: 19009 |
| Change to published diagnostics | examples 1.7 (10.4); fixtures 3.5 (45.1); `rides.pietto` 27.5 (30.3); DAG files 6.6 to 26.6; `bikes-project` 26.1; `bikes-modules` 22.7 (28.3); DAG roots N = 12: 61, 14: 123 (142), 16: 301 (321), 18: 802 (845), 20: 2312 (2368), 22: 6800 (7095) |
| Idle hover, definition, document symbols | 0.1 to 0.2 (0.6) on every input |
| Hover sent with a change | the analysis time: within a few ms of the publication row |
| `format_source` | examples 1.5 (6.1); fixtures 2.5 (26.5); `rides.pietto` 16.4; DAG files 4.6 to 22.1 |
| Idle formatting request | 3.3 to 20.3 (27.2) on the project modules |
| Formatting sent 20 ms after a change | the rest of the running analysis: `bikes-modules` 5.1 (19.6), DAG N = 14: 112, 16: 286, 18: 780, 20: 2252, 22: 6529 |
| Server start | `initialize` round trip 436 to 471; the first root analysis of a session 511 to 629 for roots up to N = 14, imports included |

**Proposed budget.** The lead records the budget as an ARCHITECTURE_DECISION
at the E-C midpoint; this is M1's proposal, with no wall-time test:

- a fact request on a current snapshot answers within 5 ms (seen: 0.6);
- an idle formatting request answers within 50 ms for a buffer of up to 4 KB
  (seen: 27);
- diagnostics follow a change within 100 ms for a single file of the corpus,
  and within 250 ms for its project roots up to N = 14 (seen: 45 and 142);
- a request that waits for, or arrives during, an analysis answers within that
  analysis's budget plus the request's own idle budget (5 ms for a fact
  request, 50 ms for formatting).

**What must come first.** Neither linear JOIN-DAG analysis nor the FD sharing
of PMS-6 must come before an E-C slice. Each new request is a lookup or one
`format_source` call within the budget on every input, and the projection
stays at 0.3 ms or less at N = 24, so C4 adds no analysis cost. Layered JOIN
DAG roots leave the project budget from N = 16 (about 0.3 s), growing about
2.4 to 2.9 times for every two layers, to 6.8 s at 22 and 19 s at 24, where a
single file of 22 layers takes 26 ms. A fact request on such a root, and a
formatting request that arrives during its analysis, waits as long. Linear
JOIN-DAG analysis is therefore a prerequisite for claiming the project budget
beyond 14 layers, not for E-C. This corpus does not isolate PMS-6: its
JOIN-heaviest files check in 36 ms, and the `0.1.8` release-notes figures for
one query of 60 to 120 JOINs (1.6 to 11 s) were not measured again. So, as
for DAG roots beyond 14 layers, the single-file budget is not claimed for such
wide JOIN queries until PMS-6 lands or they are measured again; scheduling
either is an owner item.

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

The ED.03 records below read, on 2026-11-10, the LSP 3.17 specification page
at 16:57:23Z and, for comparison, the LSP 3.18 page at 16:58:14Z (the site
now marks 3.18 current and 3.17 previous; the route pins 3.17), the VS Code
documentation at 16:58:41Z, and the VS Code 1.145.2 source at 17:01:26Z
(UTC). The pages were read as text converted from their HTML, so their layout
and images were not checked. VS Code source describes one version and
promises nothing.

Formatting (ED.03 C1):

| Field | Review |
| --- | --- |
| Snapshot/date | [LSP 3.17 `textDocument/formatting`](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#textDocument_formatting), with the base protocol's rule for a `null` result, read 2026-11-10T16:57:23Z; the 3.18 page keeps the same result type. |
| Problem/constraints | Return `pietto fmt`'s layout of the open buffer through the existing connection, without an analysis, a disk read or a write. |
| Semantic/identity model | The request names a document by URI and carries `FormattingOptions`: `tabSize`, `insertSpaces`, the optional `trimTrailingWhitespace`, `insertFinalNewline` and `trimFinalNewlines`, and other keys. The result, `TextEdit[] \| null`, describes the modification to the document. A `null` result signals a successful request, and the section gives `null` and `[]` no different meaning: both mean no change. It fixes no result for a buffer that cannot be formatted. |
| Layering/dependency direction | `format_source` owns the layout; the server wraps its output as one edit of the buffer; the client applies it. |
| Algorithms/data structures/complexity | The protocol fixes none; one `format_source` call, O(source) under the size limit. |
| Interface/version/capability model | `documentFormattingProvider` is a boolean or `DocumentFormattingOptions`, and the request has no partial result; Pietto advertises `true`. The specification does not say how a server treats `insertSpaces: false` or the other options, so ignoring them, as one spaces-only layout requires (D75.05), is the server's choice. |
| Testing/operational lifecycle | Byte equality with `pietto fmt`, UTF-16 end positions, each refusal path, ignored options and no analysis call, through the public session. |
| Pitfalls/migration costs | A client cannot tell a refusal (`null`) from a formatted buffer (`[]`), so a refusal reaches the user only through the published diagnostics; telling them apart would need an error response or another channel. |
| Disposition | Keep one whole-document edit, `[]` or `null`, ignored options, and no range or on-type formatting. |
| WHAT_NOT_TO_COPY | No layout taken from the client's options, no error response for a refusal, no partial result. |
| Pietto owner affected | LSP server; `source_format.py` is unchanged. |

VS Code format on save (ED.03 C1):

| Field | Review |
| --- | --- |
| Snapshot/date | The VS Code [Formatting](https://code.visualstudio.com/docs/editing/codebasics#_formatting) documentation, page dated 11/4/2026, read 2026-11-10T16:58:41Z; for what it leaves out, the VS Code 1.145.2 source [`format.ts`](https://github.com/microsoft/vscode/blob/1.145.2/src/vs/editor/contrib/format/browser/format.ts) and its format-on-save setting and save participant, read 2026-11-10T17:01:26Z. |
| Problem/constraints | Know what a VS Code user gets from formatting and saving a `.pietto` file through the published extension's standard client. |
| Semantic/identity model | The documentation names Format Document and Format Selection, says that formatting on type, save and paste is off by default, and describes `editor.formatOnSave` as "Format a file on save."; format on paste needs a formatter of a selection or range. In the 1.145.2 source the setting can be set per language, `editor.formatOnSaveMode` defaults to `file`, which formats the whole document, `modifications` needs range formatting and source control, and an automatic save does not format. |
| Layering/dependency direction | VS Code decides when to ask and applies the edits; the server answers every formatting request alike, whichever action sent it. |
| Algorithms/data structures/complexity | In the 1.145.2 source VS Code first makes the edits more minimal; a missing or empty result applies nothing, and on the API path the next formatter is asked. |
| Interface/version/capability model | The user turns `editor.formatOnSave` on, for every file or for Pietto alone; Format Document and an explicit save in `file` mode ask for whole-document formatting. Format Selection, format on paste and `modifications` mode need range formatting, which Pietto does not provide. |
| Testing/operational lifecycle | The route's connected VS Code check (the 1.145.2 test host and the extension at `e61444f`) must observe Format Document and a save with format on save on; until it runs, this behaviour is read, not observed. |
| Pitfalls/migration costs | A missing and an empty result behave alike in 1.145.2, so the refusal paths cannot be seen in the editor; how the client passes a `null` on was not read. Neither the documentation nor this snapshot states a time limit for formatting on save, so whether a request answered only after a long running analysis misses a save (route risk 1) is still pending. The source may change in any release. |
| Disposition | No server change: whole-document formatting serves Format Document and format on save in `file` mode, and range formatting stays out of scope. |
| WHAT_NOT_TO_COPY | No reliance on VS Code's edit minimizing, its fallback to another formatter, or a save-time limit. |
| Pietto owner affected | LSP server and `docs/editor-lsp.md`; the extension repository is unchanged. |
