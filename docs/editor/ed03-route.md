# E-C route — editor core work package

The owner approved this Gate 1 on 2026-11-10 (America/Toronto) with the
decision sheet's recommended answers. The [decision record](../decisions.md)
keeps them: the rows PL.01–PL.06 shared with Phase78–80, and the editor rows
ED.03–ED.06. E-C, the editor core work package whose scope ED.03 fixes, is a
work package of the [editor line](../roadmap.md#editor-work-package), not a
phase. It has no phase number and is not part of the `0.2.0` gate. Its route
and completion audit live under `docs/editor/`; its decisions live in
`docs/decisions.md`. Local implementation and validation are authorized from
Gate 0 (PL.01, PL.02). Each batch publishes under D77.06's conditions
(ED.05). No tag, release, package upload, write or push to the extension
repository, or Marketplace action is authorized (PL.01).

Gate 0 binds the head and its natural CI; the read of that CI's eligible health and alerts and the re-measured Phase77 overlap are pending until the package's first implementation batch records them.

Before Gate 0, these runs happened besides paper records (PL.02). The PyPI
metadata and hash fetch and isolated install probe of PL.05 (a), which sheet
Q3 A authorizes, read PyPI JSON at 2026-11-10T11:32:46Z; the lead's record of
the owner's approval of Q3 A that day carries the earlier `modified` time
11:32:37Z. Earlier, during the read-only Gate 1 drafting and before that
approval, the SQLite draft ran an in-memory `sqlite3` probe that its critique
repeated, and the Phase80 draft took a PyPI reading. No authorization is
recorded for these two: they were unauthorized preparation, and their results
are not evidence. Phase78 Q0 measures the SQLite build and its listed cells in
the Gate 0 environment, and the PL.05 probe replaces the PyPI reading. Every
implementation slice starts from the published head that Gate 0 binds (PL.02).

## Starting point

This route was drafted on `569c365d` (tree
`5561238f181887274dbadbdd5fa848998cfa1872`), an unpublished candidate of the
maintenance/editor batch. That batch was published instead as `befa5de8`,
`6a1eb9c9` and `ab972f36` on `f8ccd2c4`, so `569c365d` is not an ancestor of
`main`.

Gate 0 is bound to the head that published the D77.04 batch: `main` at
`ab972f362c433b234a74f542c5d274d22c8cdeae` (tree
`821be1ccf7bb6f3e14b8d00d80f1f30d3cc087fe`), whose natural exact-head CI
`42831340276`, push/main attempt 1, passed all 21 jobs (PL.02). At that head
Gate 0 rebinds the branch, tree, remote and natural CI; the ED.01/ED.02
publication in `6a1eb9c9`; [LSP diagnostics
v1](../spec/lsp-diagnostics-v1.md), [LSP editor facts
v1](../spec/lsp-editor-facts-v1.md) and [editor support](../editor-lsp.md).
It also reads that head's eligible CI health and alerts (a short history does
not prove the head green) and measures the Phase77 overlap again on that
head. Line references below are to `ab972f36`; the lines they name are the
same on `569c365d`.

There is no Phase77 completion audit yet, so the gate's "consume the previous
completion audit" item is NOT_APPLICABLE; its owner is Phase77 S27 (PL.01).
In its place Gate 1 reads the [Phase76 completion
audit](../phases/phase-76/completion-audit.md), the facts of Phase77's
published batches and these [engineering
lessons](../references/engineering-lessons.md): 72-1 and 72-2 (type-check
touched tests; run the repository-wide owners on the integrated tree), 73-7
(two lanes that change one walker can collide in meaning), 74-2 and 75-1
(name the base and carry base deltas), 75-2 (one file, many URIs), 75-3
(count skips) and 75-4 (scratch under the lane's own name).

The overlap with Phase77 is known only in part. Write sets were measured for 8
of its 27 slices (decimal, S08, S10, S11, S12, S14, S16, S25). All eight sit
on the scratch commit `bd18a4c3` (tree `825448a9`), which descends from
neither `569c365d` nor `ab972f36` and differs from `ab972f36` in 17 files,
among them `_lsp.py`, `_editor_facts.py`, `_project/check.py` and the editor
test owners. None of the eight writes `_lsp.py`, `_editor_facts.py`, the
editor-facts segment of `_project/check.py`, `source_format.py`, the two LSP
specs, `editor-lsp.md` or the editor test owners. The unmeasured slices widen
the overlap: S09 plans changes to `project_completed_semantics.py`, S21–S24
change the live, compiled, Arrow and saved readers, and S26 closes
capabilities and packaging. C4 is the only slice that reads semantic results
those slices change.

## Outcome

`pietto lsp` gains these alpha surfaces, which stay alpha until the Phase82
freeze:

- formatting of the open buffer;
- workspace symbols;
- document links on import module paths;
- completion from the static vocabulary;
- hover and definition for fields, lets, parameters and calls, taken from
  exact existing bindings.

M1 also measures an editor latency budget. The published VS Code extension
consumes all of these through its standard LSP client, with no change on the
extension side.

Not included:

- semantic tokens (C3);
- references and rename (C6);
- capability facts (K1);
- quick fixes that carry edits;
- context-aware completion and signature help;
- watched files;
- the model view;
- target-readiness (`PIE-B...`) diagnostics in the editor;
- JOIN key, grain or fan-out facts (reminder 8);
- navigation of import or export list items.

E-C also changes none of the following: CLI commands, JSON artifacts, the
semantic metadata artifact, the relation column view, compiled records, PIE
codes, editor-only messages, the grammar or the built-in catalog. Because the
grammar and the built-in catalog stay unchanged, no extension sync under
D76.12 is triggered.

## Decisions

| Id | Rule in this route | Source |
| --- | --- | --- |
| PL.01–PL.06 | The answers shared with Phase78–80: parallel start, lane rules and the previous-audit item (PL.01); Gate 0 and the work before it (PL.02); host pytest workers (PL.03); integration and version line (PL.04); dependencies and CI, which E-C does not use (PL.05); the planning ledger (PL.06) | Sheet Q1 A, Q2 A, Q3 A |
| ED.03 | Scope above; ED.02 revised so that formatting alone parses its buffer at request time; static-vocabulary completion supersedes D75.09's "no completion"; semantic tokens wait for M1 and a separate owner decision | Q5 A |
| ED.04 | The E-C cumulative ledger `C70/F210/D2400/S6`, its planning allocations and the acquisition reserve of the Budget section | Q1 A; sheet §3.2 |
| ED.05 | Batches EB1 and EB2 reach `main` and widen the `0.1.11` alpha surface, each published under D77.06's conditions | Q2 A, whose separate push authorization for each batch the owner replaced on 2026-11-10 at 14:41Z |
| ED.06 | Later steps: K1 gets a new versioned capability document (Q10 A chose the carrier before the weighing, revising the 2026-11-07 Editor line order; the K1 Gate 1 records the weighing against the semantic metadata artifact v1 that ED.01 requires, and a result for the artifact v1 returns the carrier to the owner; Gate 1 design now, implementation after Phase77 S26); references only complete, rename its own Gate 1; no location field in the column view before the freeze; the PIE-B view is an extension interim; the extension lane stays planning-only apart from the local X1 and X3 of EX.01 | Q10, Q11, Q12, Q13; Q4 not approved; EX.01 (lead, inform) |

These existing decisions still bind E-C:

- ED.01 and ED.02, as ED.03 revises ED.02.
- D75.05: `fmt` output may change before the freeze, with a release-note line.
- D75.09: no PIE-B diagnostics in the server.
- D75.10: an unsaved buffer is its own type.
- D75.11 and D75.12: partial analysis and the editor-only messages.
- D76.12: an extension sync is needed only for a grammar or catalog change.
- D76.14: `0.1.11` is approved separately.
- D76.15: the lane rules, as PL.01 continues them.
- D76.17: how D is counted.
- Reminder 8: JOIN facts.
- D77.04: the batch whose published head Gate 0 binds.
- D77.06: the publication conditions that ED.05 applies to each E-C batch.

AD78.01–AD78.03 and the D78, D79 and D80 rows do not bind E-C.

## Slices

| Slice | Delivers | Depends on | Write set | Checks | C/F/D/S |
| --- | --- | --- | --- | --- | --- |
| M1 | Latency measurement on a named corpus: the repository's example sources, the worked example, the `fmt` test corpus, and generated schema-v2 projects of layered JOIN DAGs at rising depth. It measures snapshot construction for single files and projects, publication of diagnostics after each edit, the three existing request families, and `format_source`. It proposes the budget, and states whether linear JOIN-DAG analysis or the FD sharing of PMS-6 must come first. | Gate 0 | The "Performance and verification" section of `docs/spec/lsp-editor-facts-v1.md`. The driver and raw timings stay in the lane's scratch folder, outside Git. | Runs under the lane rules on a quiet host. Each figure names its tree, Python, corpus paths, generator parameters and repeat count. No wall-time test is added: count laws are the only test bound. | 5/15/200/1 |
| C1 | `textDocument/formatting` runs the pure `format_source` on the request's current buffer text. It answers when the request is read and never holds it for analysis. The result is one whole-document edit, `[]` when nothing changes, and `null` for a parse error (header lines included), `FormatRefusedError`, the size limit, or a URI that is not open. `FormattingOptions` are ignored (one layout, D75.05). It does no disk read or write. | Gate 0 | `src/pietto/_lsp.py`; a formatting section in `lsp-editor-facts-v1.md`; the method list of `lsp-diagnostics-v1.md`; `docs/editor-lsp.md`; `tests/test_cli_lsp.py`; `docs/release-notes.d/77-e02-lsp-formatting.md`; `scripts/package_smoke.py`, whose installed `pietto lsp` round trip expects the advertised capabilities (DERIVED_MECHANICAL). `source_format.py` is only read. | Byte equality with `pietto fmt` on the corpus; BOM, CRLF, lone CR and UTF-16 end positions; every refusal path; no semantic, project or IR call; advertised capability; `test_cli_format.py` and `test_parser_format.py` unchanged | 10/30/300/1 |
| C2 | `workspace/symbol` over the current snapshots, waiting while any analysis is scheduled or running. It returns every retained declaration in root, module and source order, without deduplication, and a module without facts contributes none. `textDocument/documentLink` covers an import module path that resolves exactly to a module of the same selected-root analysis, with nothing for an unresolved, ambiguous, blocked or omitted module. Both use standard shapes, and the spec fixes the matching rule. | C1 merged | `_lsp.py`; `src/pietto/_editor_facts.py`; `_project_editor_facts` in `src/pietto/_project/check.py`; both LSP specs; `editor-lsp.md`; `tests/test_cli_lsp.py`; `tests/test_project_editor_overlays.py`; `77-e03-lsp-workspace-symbols.md`; `scripts/package_smoke.py`, whose installed `pietto lsp` round trip expects the advertised capabilities (DERIVED_MECHANICAL) | Occurrence completeness and order; URI spellings; partial-project omission; legacy-flat root; conflict suppression; zero analysis calls per request; `test_project_check_partial.py` unchanged | 15/45/350/1 |
| C5 | `textDocument/completion` returns one complete list in a fixed order that does not depend on position: the keywords authored code can write, and the builtin types, scalar functions and aggregates of the core catalog. It excludes extension catalogs, which are not callable (D76.11), and names refused everywhere. It does no lexing, parsing or analysis, and offers no resolve or trigger characters. | C1 merged | `_lsp.py`; new private `src/pietto/_editor_completion.py`, which reads `semantic/catalog.py` and the generated lexer vocabulary without changing them; both LSP specs; `editor-lsp.md`; `tests/test_cli_lsp.py`; `77-e04-lsp-completion.md`; `scripts/package_smoke.py`, whose installed `pietto lsp` round trip expects the advertised capabilities (DERIVED_MECHANICAL) | An oracle written before the code: every item is accepted by `pietto check` in at least one authored position, and every accepted catalog entry appears. Deterministic output; zero parse or analysis calls; generated parser untouched | 10/30/250/1 |
| C4 | Hover and definition for field references, `let` bindings, `def` and relationship parameters, and `def` and relationship calls. Each fact comes from a binding that the single-file `SemanticModel` or the project module environments already retain. Facts are kept per occurrence, without deduplication. A use with no retained exact binding has no fact. | M1 budget recorded; C2 merged; overlap measured again | `_editor_facts.py`; `_project_editor_facts`; `_lsp.py` if the projection changes; the "First facts" table, extended before the code; `editor-lsp.md`; both test owners; `77-e05-lsp-hover-definition.md`. Excluded: `semantic/**`, `_project/project_*`, IR | The exact-target table per context; stale, wait, alias and partial cases; zero analysis calls; projection bounded by occurrences (count test); a semantic-collision review against the published Phase77 batches (lesson 73-7) | 25/75/800/2 |
| Z1 | Acquisition consolidation against the Gate 0 baseline. Shared hunks: the editor rows of `docs/status.md`; the editor section and a Phase82 freeze-ledger row of `docs/roadmap.md`, which also names the extension as a consumer of `pietto.cli.main(argv)` (DERIVED_MECHANICAL); `README.md:582` | C4 merged | Those documents and any test owner that the review consolidates | Exact coverage equivalence; fresh witnesses kept; the ten-slowest-node profile per [development](../development.md#phase-end-acquisition-consolidation); the closeout read of the latest published head's eligible CI health and alerts | 5/15/100/0, shared with Z2 (acquisition reserve) |
| Z2 | Audit only: `docs/editor/ed03-completion-audit.md`, with the three acceptance layers, lessons, Gate 2 duration and the handoff to the next editor step | Z1 | That file | Independent audit read | from the Z1 reserve |

Each Pietto test sits in its existing owner, and no new test file is planned.
A use whose binding is not yet retained gets no fact rather than a new
semantic retention. Changing a semantic owner is a scope repair (S): it needs
the collision review, and the owner when it changes semantic identity.

**Batches.** EB1 holds M1, C1 and C2. EB2 holds C5, C4, Z1 and Z2. C1 → C2 →
C5 → C4 merge in that order because they share the dispatch set
(`_lsp.py:243-250`) and the capability dictionary (`:292-298`). M1 is
independent. Each slice is one commit. Each batch gets one Gate 2 on its final
tree, one fast-forward push and natural CI on its head.

## Qualification

Acceptance has three layers:

- **Observable.** Protocol tests run through the real `pietto lsp` stdio
  process (`tests/test_cli_lsp.py`), and project facts run through
  `tests/test_project_editor_overlays.py`.
- **Existing.** The diagnostic protocol, the ED.01/ED.02 facts, `fmt` CLI
  bytes, partial analysis, and zero analysis calls for every fact request do
  not regress.
- **Connected.** A VS Code host check exercises each new capability through the
  published extension head `e61444f`. It runs in a scratch copy with
  scratch-only host steps, and nothing is written to the extension's canonical
  worktree, committed or pushed. It uses only the VS Code 1.145.2 test host and
  the `node_modules` already on the host from the ED.01/ED.02 acceptance
  ([status](../status.md)); any VS Code or npm download is a fetch that this
  route rules out and needs the owner. It counts skips beside passes and covers
  each URI spelling the client sends. If the check cannot run, its slice
  records it as NOT_RUN and does not claim the connected layer.

While implementing, lanes run:

- the focused owners above and Ruff;
- `pyright` on `src/`;
- `pyright --project pyrightconfig.tests.json` on the changed tests;
- `scripts/release_notes.py check`;
- the repository-wide owners (`tests/test_repo_*` and the layering tests),
  on the lane tree and again on the integrated tree.

Gate 2 runs the authoritative Python 3.13 validation once per batch, on the
integration host. Package smoke runs once per batch, because each batch
changes the installed modules. No golden or generated check runs, because no
grammar or SQL output changes; any golden or generated difference is a stop.
Natural CI owns Python 3.12 and 3.13. There is no database run, container or
dependency fetch.

The 11-field external-reference records are pending. C1 writes the records
for LSP 3.17 formatting and for VS Code's format-on-save behaviour. C2 writes
the records for `workspace/symbol` and `documentLink`, and C5 writes the
record for `completion`. Each record comes before its slice's acceptance and
needs the read the lead's dispatch allows; while a record is missing, its
slice waits.

## Dependencies and pins

| Input | Pin | State |
| --- | --- | --- |
| Gate 0 head | `ab972f36`, the published D77.04 head; natural exact-head CI `42831340276` passed all 21 jobs | bound |
| CI health | that head's eligible health and alerts | pending |
| Python | CPython 3.13.13 for Gate 2; 3.12 and 3.13 in natural CI | existing |
| Runtime dependencies | none added; `pietto lsp` stays standard library only (D75.09) | existing |
| LSP | 3.17 specification pages of the four new methods | pending snapshot |
| VS Code | the 1.145.2 test host already on the integration host from the ED.01/ED.02 acceptance; no download | existing; the host check records the version it ran |
| Extension | `MianliWang/pietto-vscode-extension` at `e61444f`, read only, with the `node_modules` already on the host; `vscode-languageclient` 9.0.1 as the editor draft observed | rebound at the host check |
| Formatter and catalog | `source_format.py`, `semantic/catalog.py` and the generated lexer at the Gate 0 tree, unchanged | existing |

## Budget

The cumulative E-C ledger is `C70/F210/D2400/S6` (ED.04). D counts one per
diagnostic command, and a loop inside one command counts once (D76.17). The
per-slice figures above are planning allocations, not separate allowances. They
follow the sheet's E-C figures, except that C5/F15/D100 of the sheet's C5 draft
(15/45/350/1) is moved into the acquisition reserve of Z1 and Z2 (5/15/100/0)
that the initiation gate requires at the start and at the midpoint. Together
they come to `C70/F210/D2000/S6`; the remaining 400 D is the replay reserve,
and every replay onto a moved head draws on it. The midpoint re-estimates the
acquisition reserve; if it does not fit, the lead asks the owner. The planning
entry charged here is the editor draft's 21 and this route's drafting 17 shell
commands, plus any later fix of this route and E-C's share of the shared
passes after the approval. PL.06 records the shared sheet, critique, review,
consolidation and fix-pass commands once and keeps those before the approval
on Phase77. At any cap the lead stops and asks. No handoff or lane resets the
ledger, and every failure stays counted.

## Lanes and integration

- E-C runs beside Phase77 and the Phase78–80 lanes (PL.01). Its lanes start
  from the latest integration head, name their base tree, and rebase before
  delivery. A rebase carries the base delta with plumbing and compares each
  step's changed lines before and after.
- Lanes follow the lane rules of PL.01 and the pytest worker rule of PL.03.
  Scratch, temporary indexes and logs stay in the lane's own folder.
- Gate 2 shares the integration host under PL.01, with the authoritative
  worker cap of PL.03.
- New files come first. Each slice's code, tests, spec and fragment land
  before any shared hunk. At each batch end, the lead adds the shared hunks
  (`status.md`, `roadmap.md`, `README.md`, `decisions.md`) one at a time on
  the integration tree.
- Batches reach `main` and widen the `0.1.11` alpha surface (PL.04, ED.05),
  under D77.06's conditions: a push needs Gate 2 on the exact tree, a clean
  batch audit and a `main` that has not moved since the rebind, and it is
  fast-forward only. A failed head is kept and repaired
  by a child, never rerun. A batch audit is one round; a second round opens
  only after a medium or worse finding.
- No E-C batch carries Phase78–80 files. The sheet Q2 option-C check at the
  Phase77 midpoint follows PL.04.
- The third whole-tree test pass, due before the end of Phase78, is
  scheduled so that it does not run against an open E-C lane on the same
  test owners.

Route and decision records (documentation only, with no code and no
release-note fragment) may reach `main` before the `0.1.11` cut, in a Phase77
batch under D77.06 or in a documentation and tool batch under D77.14;
Phase78–80 code and fragments may not. By the lead's ruling (PL.04, lead,
inform), this route reaches `main` in a Phase77 batch under D77.06, because
the batch also carries a Phase77 repair, counted on Phase77's ledger, that
returns PIE-B1003 refusals of project `/` and `%` instead of crashing. D77.14,
a rule for a whole documentation and tool batch, does not cover it.

## Midpoint, unfreeze and closure

**Midpoint (after the EB1 natural CI).** The midpoint passes when:

- M1's budget is recorded as an ARCHITECTURE_DECISION row;
- C1 and C2 are on `main` with green natural exact-head CI;
- the EB1 health and alerts have been read;
- the ledger projects within its caps;
- the Phase77 overlap has been measured again;
- the new and changed tests since Gate 0 are listed for Z1.

EB2 seals only after the midpoint passes.

**Unfreeze conditions.** Any of the following needs the owner:

- a slice or LSP method beyond this route;
- a public text changed outside the rows a slice lists;
- any semantic, IR, SQL, grammar, catalog, CLI JSON, metadata or column-view
  change;
- a new dependency;
- a write to the extension repository;
- a budget under which C4 needs JOIN-DAG or PMS-6 work, or a threaded
  analysis, first.

**Closure.** E-C closes when five conditions hold:

- M1's budget is recorded;
- each of C1, C2, C5 and C4 is on `main` with green natural exact-head CI, or
  the owner has withdrawn it;
- Z1 is done;
- the closeout has read the eligible CI health and alerts of the latest
  published head;
- Z2 is on `main` with green natural exact-head CI.

## Risks

1. **The single-threaded server.** A formatting request can queue behind a
   running project analysis and miss the client's save timeout, which is an
   external fact still pending review. C1 answers each request when it is
   read, and M1 measures the delay. A fix that needs a new threading model is
   an owner stop.
2. **A moving Phase77 base.** C4 can collide in meaning with decimal, S09 and
   S21–S24 while replays repeat. C4 comes last and reads semantic results
   without changing them. It gets a collision review, and replays draw from
   the 400 D reserve.
3. **A wider alpha surface.** The new surfaces enter `0.1.11` and light up in
   the published extension automatically, while the extension's own
   documentation cannot follow under Q4. `fmt` output may also change before
   the freeze. Each fragment says its surface is alpha, Z1 adds the
   freeze-ledger row, and the documentation gap of the extension waits for
   its lane.

## Initiation-gate fields

| # | Answer |
| ---: | --- |
| 1 | Drafting base `569c365d`; Gate 0 is bound to the published D77.04 head `ab972f36` with natural CI `42831340276`, and rebinds its remote, tree and the controlling contracts and decisions listed above. |
| 2 | The five LSP surfaces and the M1 budget above. Success does not include the non-goals in Outcome or any `0.1.11` release. |
| 3 | Pietto semantics, project semantics and IR stay the authority. The editor projects their exact results, the module graph's import resolution, the core catalog and `format_source`, and derives no semantic fact. |
| 4 | Identity domains: document URI and version, selected root and epoch, module, declaration occurrence, use occurrence, import-path occurrence, catalog entry. No name- or spelling-based target, no deduplication by spelling, type or target, no winner among roots or URIs (D75.12), and no canonical path in place of an unsaved buffer URI. |
| 5 | A snapshot is absent, pending, current or discarded; facts come only from a current one. Formatting returns refused (`null`), unchanged (`[]`) or one edit from the buffer it reads. Completion is constant for the running package. |
| 6 | Asserted: spec text. Derived: projected facts. Verified: protocol and count tests. Observed: M1 timings and the host check on the existing VS Code 1.145.2 test host. Unknown: client timeouts and the LSP snapshot (pending records). Disproven: none. Local, Gate 2, natural CI and release claims stay apart. |
| 7 | `_lsp.py` owns protocol, dispatch, capabilities and waits. `_editor_facts.py` and `_project_editor_facts` own the detached projection. `_editor_completion.py` owns the vocabulary projection. `source_format.py` and `semantic/catalog.py` stay unchanged owners. |
| 8 | The editor layer depends on the formatter, semantic and project results and the catalog, never the reverse. No editor branch in semantic, IR or SQL code, and no re-decision of a type, binding or module. Layering tests run on the integrated tree. |
| 9 | Additive capabilities in `initialize`; every surface is alpha until Phase82. No CLI JSON, metadata, column-view, compiled-record or `VERSIONS` change. `fmt` output may change before the freeze (D75.05). No migration. |
| 10 | Client capabilities govern the representation. The server advertises only the methods it implements. Target readiness and capability facts stay out (D75.09, ED.06). |
| 11 | Only JSON-RPC 2.0 over stdio, with standard LSP result shapes. No snapshot, cache or artifact leaves the process. |
| 12 | No database or SQL execution. The server runs only the existing in-process check and the pure formatter; the execution plane is untouched. |
| 13 | Snapshots live for one analysis epoch. Formatting state lives for one request. The completion list lives for one session. `shutdown` answers held requests with no result. No thread, file handle or process is added. |
| 14 | Buffers stay their own type (D75.10). Formatting reads no disk and writes nothing. A document link targets only an exact resolved module and never a path built from the import string. No network, credentials or environment configuration. The extension repository is untouched. |
| 15 | Existing snapshot lookups; a linear scan for workspace symbols with a fixed match rule; a precomputed vocabulary tuple; the existing formatter. No new index or cache. |
| 16 | Projection is bounded by declarations and exact-resolution occurrences. A workspace symbol request costs O(declarations), completion O(vocabulary), and formatting O(source) under the UTF-8 size limit. M1 measures the known exponential growth of layered JOIN DAGs; E-C does not fix it. |
| 17 | New facts are discarded with their snapshot on open, change, close, conflict, a configuration change or a newer epoch. Import link targets are recomputed for each analysis. Formatting and completion keep no derived state. |
| 18 | No persistent or cross-session cache. The snapshot is not authority beyond its epoch. |
| 19 | The server loop stays single-threaded. Formatting and completion answer when read. Fact requests wait under the existing rule, and a workspace symbol request waits while any analysis is pending. No response order is promised. Lane concurrency follows PL.01 and PL.03. |
| 20 | No new PIE code or editor-only message, and no change of diagnostic order, location or text. A refused new request returns `null` or `[]`, malformed parameters return `-32602`, and unsupported methods return `-32601`. |
| 21 | Every new request is read-only inspection. Formatting proposes edits and applies none. No resolution or construction happens at request time, except the parse that formatting needs. |
| 22 | Satisfied: E-C adds no authored spelling, so no usability row is needed. Discovery is through the advertised capabilities and `editor-lsp.md`, and the spec lists unsupported behavior. |
| 23 | LSP 3.17 shapes; the two alpha LSP contracts as normative; byte equality of formatting with `pietto fmt`; protocol tests plus the host check as independent checks. |
| 24 | Differential checks: formatting against `pietto fmt`, completion against the prewritten catalog oracle, and facts against exact bindings. Metamorphic checks: URI spellings, BOM, CRLF and CR. Repeated runs must give the same output. A new fuzz framework is NOT_APPLICABLE: each new request is a deterministic projection of an existing result or of `format_source`, over finite, closed input classes (URI spellings, line endings, refusal paths, the fixed vocabulary) that these checks enumerate; the formatter's own assurance stays with its existing owners. Owner of high-intensity assurance: Phase81. |
| 25 | One new private module in the existing wheel. No dependency, extra, entry point or generated file. Package smoke runs per batch. |
| 26 | CPython 3.12 and 3.13; the Linux/WSL integration host; the host check on Linux only. Native Windows editor acceptance belongs to Phase81. No dialect change. |
| 27 | Batches on `main` under D77.06's conditions, shipping as alpha in `0.1.11` (D76.14, ED.05). Fragments `77-e02` to `77-e05`. A rollback is a revert in a later batch. No deprecation. Phase82 rules on the freeze-ledger row. |
| 28 | Pending prerequisites: the Gate 0 head's health (lead), the overlap measurement (lead), the external records (C1, C2, C5). Deferred: C3 (owner, after M1), C6 (own Gate 1), K1 (Gate 1 design, then after Phase77 S26), quick fixes (after the Phase81 diagnostic review), T1 (the interim PIE-B view), X0 and X2 (the extension patch with its CI, the model view) and extension CI (Q4, unapproved), X1 and X3 (the previews, code actions and restart) beyond their local development under EX.01 (all defined in the decision record's Gate 1 introduction), context-aware completion and signature help (an ARCHITECTURE_DECISION after M1), watched files (a later ARCHITECTURE_DECISION), `pietto.cli.main` (Phase82), JOIN facts (reminder 8 owner), the column-view location field (not before the freeze), JOIN-DAG linearity and PMS-6 (the owner, if M1 puts them first). The previous-audit item is NOT_APPLICABLE (owner Phase77 S27; PL.01). |
| 29 | M1 alongside C1 → C2 → C5 → C4 → Z1 → Z2, in batches EB1 and EB2, with the write sets above and the Outcome non-goals. |
| 30 | `C70/F210/D2400/S6`, cumulative. Stop at a cap, an unproved exact identity, a semantic, IR or SQL change, a new dependency, a required extension write, a public text outside the listed rows, a trust regression, a budget that needs an architecture change, or a Phase77 collision outside the write set. Failed candidates and heads are kept; each batch publishes under D77.06's conditions (ED.05). |

## Activation record

The owner approved this Gate 1 on 2026-11-10. Work before Gate 0 follows the
PL.02 rule stated at the top of this route. The lead binds each slice's exact
inputs and write set and re-measures the overlap when the slice opens. A local
candidate certifies no Gate 2, publication or package completion.
