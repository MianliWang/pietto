# Phase75 handoff — Phase76 readiness

This handoff takes effect when Phase75 closes under its
[completion audit](completion-audit.md). Check live `main`, its tree and its
CI before acting on any hash here. The owner's Gate 1 answers of 2026-11-07
route the Phase75 leftovers below; a roadmap-input report written for the
owner is an input to the Phase76 Phase Start, not authority.

## What Phase76 receives

- `main` with all of Phase75: the relation column view
  (`pietto explain --project`, `pietto.project-relation-columns.v1`), the
  Python compile API `pietto.compiler`, `pietto fmt --project` and one fmt
  spelling for strings, one-line import and export lists and `order by` keys,
  the PIE-P1000 refusal of every header line (PIE-P1012 retired), the
  `emit-sql --help` batch form, the [capability page](../../capabilities.md),
  the D8 hints and the named `Decimal` rule of PIE-S2105, editor partial
  analysis and `pietto lsp` with five editor-only messages, and the Phase74
  follow-up for a false PIE-S2315. The [release notes](../../release-notes.md)
  list every change, refusal and compatibility row under `0.1.10`.
- `0.1.10`: Phase73, Phase74 and Phase75 ship together as `0.1.10` (D75.16).
  Its release commit is the last commit of batch 2; on 2026-11-07 the owner
  approved the publication chain (fast-forward push, tag `v0.1.10`, GitHub
  pre-release, PyPI upload by the owner). The Phase76 Phase Start comes after
  that publication.
- Compiled `VERSIONS` is `(7, 1, 7, 1)`, unchanged in Phase75 (D75.17). Once
  `0.1.10` is cut, a compiled record change needs its own change of that
  value.
- Alpha surfaces until the Phase82 freeze: `pietto.compiler`,
  `pietto.project-relation-columns.v1` (with the kinds `type_alias` and
  `unknown`, which no project produces today), the fmt output, `pietto lsp`,
  editor partial analysis and the five editor-only messages.
- Tests: the second whole-tree test pass is done (S09). The naming law in
  `tests/test_repo_test_layout.py` lists its recorded exceptions by name; a
  new test file or helper follows it, and an exception that goes away leaves
  the list in the same change.
- Inputs: the Phase75 section of the
  [engineering lessons](../../references/engineering-lessons.md#phase75), the
  latest qualified CI health and the Phase 76 row of the
  [roadmap](../../roadmap.md#future-roadmap-v6).

## MySQL items after Phase75

Phase75 changed no SQL output and opened no MySQL form. Every row of the
[Phase75 handoff's MySQL table](../phase-74/phase75-handoff.md#mysql-items-after-phase74)
stays as written, with its refusal and its release-note entry. Phase75 adds
one: the MySQL part of the project FULL or CROSS JOIN that an unread
`Timestamp` or `UUID` field blocks (below) goes to the Phase77 Gate 1
(D75.14).

## Deferred decision points

The tables of the [Phase75 handoff](../phase-74/phase75-handoff.md#deferred-decision-points)
and the earlier handoffs stay as written; Phase75 changed none of their rows.
Phase75 adds these:

| Item | Owner | Latest point |
| --- | --- | --- |
| Removing the header rule and its tokens from the grammar, and the `Header.mode` that `pietto.semantic.analyze` still reads on a hand-built AST (D75.06) | Phase76 Gate 1 | Phase82 freeze input |
| Relaxing three D8 rules: grouping by a computed `let` in a single file, a scalar around an aggregate such as `round(avg(x), 2)`, `round` of a `Float` with digits (D75.14) | Phase76 Gate 1 | each needs a two-database differential |
| A check that the contract relation matches the source table string (D75.14) | Phase76 Gate 1 | — |
| A project FULL or CROSS JOIN blocked with PIE-B1003 `scalar_meaning_requires_field_projection` by an unread `Timestamp` or `UUID` field (D75.14; a known limitation in the `0.1.10` release notes) | Phase76 Gate 1 for PostgreSQL, Phase77 Gate 1 for MySQL | — |
| `Decimal` times `Int` and a sign on a `Decimal`: PIE-S2105 names the rule, while `amount + 1` passes; Phase75 changed the text only (Gate 1 Q8) | the lead finds the cause; a defect goes to Phase76 with the FULL/CROSS item | — |
| The extra PIE-S2104 before PIE-S2310 for `round(avg(x), 2)` (Gate 1 Q8) | Phase82 diagnostic review | it changes the diagnostic list and order |
| An executable batch `compile_queries(...)` (D75.03) | Phase80 Gate 1 candidate | — |
| The import time of `pietto.execution` (D75.03) | its own performance item | — |
| Source columns, `schema_version = 4` columns, canonical type names and `Decimal` precision and scale, and single-file relations with a JOIN, let, capture or Collect in the column view (D75.14) | the Explain-for-explicit-modules follow-up | — |
| Hover, definition, completion, symbols, an editor fact format, format or migrate previews (D75.13) | unscheduled; they may return on public contracts | — |
| `fmt` layout: the gaps between the tokens of a line, a head comment paragraph attached to the first declaration; a line width, style options, a JSON output (route 75-F, D75.14) | formatter owner | Phase82 freeze input, with whether the fmt output freezes |
| Whether `pietto.cli.main(argv)`, which the owner's extension launches as `pietto lsp`, is a documented entry point | the lead, then the owner | Phase82 freeze input |
| Server-side file watching (`workspace/didChangeWatchedFiles`), so that a `pietto.toml` edit or a module changed outside the editor is seen without a restart | LSP owner | the first Gate 1 that takes an editor item |

## Open follow-ups

The open follow-ups of the [Phase75 handoff](../phase-74/phase75-handoff.md#open-follow-ups)
stay open except where this table says otherwise.

| Follow-up | State and owner |
| --- | --- |
| The second whole-tree test pass (Phase74 handoff) | done in S09 |
| The project JSON v2 aggregate `function` values `filtered_count`, `filtered_sum`, `count_distinct_tuple`, `group_any` and `group_all` (Phase75 handoff) | decided on 2026-11-07: the five names are kept; a later rename is a public format change that the release notes list |
| [`docs/editor-lsp.md`](../../editor-lsp.md) described VS Code only with a generic LSP client; the owner's extension is the tested client (D75.13), and its README links that page | done: the `0.1.10` release commit adds a section for the extension |
| A project root nested inside another root through a symbolic link publishes its modules under both spellings without the overlap message; the server compares root paths by spelling | LSP owner |
| Beside a let/projection name conflict, a `schema_version = 2` project still differs from a single file where an `order by` key of `first` or `last` reads a refused `let` (a missed or misnamed PIE-S2104), where `count_distinct` reads a refused `let` (the same `let`-map cause) and for `stddev` of a refused `let`; the PIE-S2315 follow-up fixed only the false PIE-S2315 of `first` and `last` | aggregation semantic owner |
| `0 - x` of a `Decimal` passes the check, while project `emit-sql` refuses every `Decimal`/`Int` pair with PIE-B1003 `arithmetic_requires_signed_int_operands`, so a user meets the emission refusal after the check hint | project emission owner, with the `Decimal` times `Int` item above |
| `fmt --project --write` replaces each module atomically; a failure its pre-pass cannot predict (no space, an access rule that `os.access` does not show) surfaces in the write pass after the earlier modules are replaced. Whole-project atomicity would need a two-phase design (D75.04) | formatter owner |
| The VS Code acceptance did not run on native Windows Python, the Windows desktop `wsl.exe` launcher, Remote WSL, macOS or the oldest admitted VS Code, and showed only the two-roots message in the editor | extension owner, in the extension repository; a CI there and an extension version policy are owner items |
| The naming-law exceptions: `test_sql_emission_closure.py` (named by a `ci/workloads.toml` cost entry, so its rename is a placement change), and `_pietto_mysql_native_prepared.py` (its rename touches twelve files, `scripts/phase68_executor_premise.py` among them) | the lead; the next whole-tree pass |
| `AGENTS.md` said an owner "may still have a history-named file until the second whole-tree pass", and its list of current documentation did not name the Phase75 contracts | done: the Phase76 route publication commit drops the clause and names the contracts (owner answer of 2026-11-07, D76.18) |

## Acquisition debt

- The bounded ten-slowest profile is due on Phase75's final natural CI
  health: each of the ten slowest in-process nodes alone under cProfile on a
  quiet host, reusing the Phase73 review for unchanged nodes. S09 did not run
  it.
- F3: `scripts/ci_workloads.py::place` deals each requirement's sorted nodes
  round-robin over the three general-runtime shards, so a module-scoped
  fixture can be built in up to three CI shards
  (`test_harness_target_conformance.py::valid_receipts` among them). Changing
  it is placement policy, which needs its own evidence and authority.
- Merges S09 left for the next whole-tree pass: the IR aggregate owners (nine
  files, 151 nodes), the CLI aggregate JSON owners (five files, 83 nodes),
  the near-duplicate `let` CLI checks of the row-level semantics and IR
  owners, and the `_check` helper that `test_project_def_imports.py` and
  `test_project_relationship_imports.py` each copy, with the other
  duplicated private helpers of the S09 inventory.
- The Phase72 F1 and F2 product debts stand as recorded; F4, the test-side
  receipt decode, is fixed (S09).

## Process inputs

- The owner's pre-approval of each Phase73–75 batch push after its Gate 2
  (2026-11-05) ends with Phase75; a Phase76 push needs its own authority.
  The owner approved the `0.1.10` publication chain on 2026-11-07.
- Lanes run at `nice -n 19` with at most `pytest -n 2` unless a dispatch says
  otherwise, write only in their own worktree and evidence folders, and never
  commit; the lead runs one Gate 2 per batch head on the integration host.
- A lane starts from the head it will publish on, or names the base tree its
  replay carries (see the Phase75 lessons).
