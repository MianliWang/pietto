# Phase75 route — 10 slices

Phase75 owns the Phase 75 row of the
[roadmap](../../roadmap.md#future-roadmap-v6): formatter follow-ups, editor
diagnostics with `pietto lsp` and partial analysis, diagnostic hints, the
Python compile API, the relation column view and the retirement of header
lines. Its Gate 0 binds `main` at the Phase74 completion commit `24645b36`
(tree `22b2b05a`), whose natural exact-head CI `42316298753` attempt 1 accepted
all 21 jobs. Its Gate 1 is D75.01–D75.18 in the
[decision record](../../decisions.md#phase75--owner-decisions-2026-11-05-to-2026-11-07).
Phase75 ships in `0.1.10` together with Phase73 and Phase74, after Phase75
closes, with separate approval; its batches publish to `main` with no tag or
PyPI upload in between (D75.16).

The owner let the first Phase75 lines start on 2026-11-05, beside Phase74
(J13, D74.13). Their work was built on earlier heads and replays onto `main`.
Gate 0 takes the Phase74 [completion audit](../phase-74/completion-audit.md),
its [Phase75 handoff](../phase-74/phase75-handoff.md) and the Phase74
[engineering lessons](../../references/engineering-lessons.md#phase74) as
inputs. This route is published by an unnumbered documentation-only commit,
the first Phase75 commit on `main`. Each slice binds its exact inputs, write
set, checks and acceptance when it is integrated; this table fixes coverage,
dependencies and batches only.

## Lines

| Line | Delivers | Not included |
| --- | --- | --- |
| 75-V | `pietto explain --project ROOT` on a `schema_version = 2` project lists the output columns of each table and query: name, type and nullability (`non_null`, `nullable` or `unknown`), as text or as the alpha JSON document `pietto.project-relation-columns.v1` (J17) | source columns; columns of `schema_version = 4` package roots; canonical type names, `Decimal` precision and scale; a single-file column view for relations with a JOIN, let, capture or Collect |
| 75-A | `compile_sql` and `compile_all_sql` in `pietto.compiler`, whose `SqlEmission(status, document)` is byte-equal to `pietto emit-sql --project ... --format json` (alpha, J18) | an executable batch `compile_queries(...)` (D75.03); a cache; a single-file Python entry; any change to `compile_query` |
| 75-F | `pietto fmt --project ROOT` with `--check` or `--write` (J15 d); the fmt gate over every `pietto` block of `README.md` and `docs/*.md`; one spelling for strings, one-line import and export lists and `order by` keys (J15 a–c) | partial formatting, a line width, style options, a JSON output, new diagnostic codes; retiring any equivalent spelling (J16); the layout items of the Phase75 handoff (gaps between the tokens of a line, a head comment paragraph attached to the first declaration) |
| 75-H | Every header line is refused with PIE-P1000 and a hint for that line, in every command, check mode and dependency package; `migrate` still deletes them; PIE-P1012 is retired | removing the header rule and its tokens from the grammar (Phase76 Gate 1, Phase82 freeze input); `migrate --write` (J22) |
| 75-D | `pietto emit-sql --help` names the project batch form; the capability page `docs/capabilities.md`; hints for the eight implicit rules of the external audit D8 and a named `Decimal` rule in PIE-S2105, as message and suggestion text only | relaxing those rules; new diagnostic codes; any change of code, location, order or acceptance |
| 75-E | `pietto lsp` over standard input and output, diagnostics only, standard library only; editor partial analysis, so one broken module no longer hides the others; five editor-only messages without a PIE code; the VS Code acceptance with the owner's extension, which takes its diagnostics from `pietto lsp` (J19, J20, D75.13) | hover, definition, completion, symbols, an editor fact format, format or migrate previews; backend refusals (PIE-B...) in the editor; root discovery; the extension's own changes, made in its repository (D75.13) |

Phase75 changes no SQL output, no grammar, no IR and no compiled record, so
it needs no real-database run. `pietto check --project` stays all or nothing;
partial analysis is for the editor only. Every new public surface is alpha
until the Phase82 freeze, and the release notes list each exact new text.

## Slices

| Batch | Slice | Content | Depends on |
| --- | --- | --- | --- |
| B1 | S01 | Relation column view: the schema-2 routing read, the column builder, text and JSON output, the spec `project-relation-columns-v1.md`, the package smoke | route publication |
| B1 | S02 | Python compile API: `pietto/compiler.py`, the spec `python-compile-api-v1.md`, the guide section, the package smoke inventory | S01 (merge order) |
| B1 | S03 | `fmt --project`: one read of the selected modules, the whole-project refusal, the write pre-pass, atomic writes in module order | S02 (merge order) |
| B1 | S04 | Header-line retirement: the PIE-P1000 refusal with a hint per line, `migrate` still deletes the lines, PIE-P1012 retired, the fmt header code deleted | S03 (`source_format.py`, `language.md`) |
| B1 | S05 | Diagnostics and documentation, in two commits. The first: the `emit-sql --help` batch form, the documentation fmt gate, `docs/capabilities.md` probed on its base. The second, after S07: the D8 hints and the named `Decimal` rule of PIE-S2105 | S04 (shared rows of `diagnostics.md`); the second commit S07 |
| B1 | S06 | Editor partial analysis: `check_project_diagnostics`, the exact-path `exclude` of the source selection, at most five passes, the not-checked message | S03 (the source reader) |
| B1 | S07 | `pietto lsp`: JSON-RPC over standard input and output, editor buffers as their own type, the five editor-only messages, a suggestion that the message already carries shown once, `docs/editor-lsp.md`, the installed-CLI smoke | S06 |
| — | midpoint | exit criteria below | B1 head CI |
| B2 | S08 | fmt spelling normalization: double-quoted strings, a one-line parenthesized import or export list written bare, no redundant `asc`; the self-check compares tokens after the declared normalization; documentation examples reformatted | S04, S05 |
| B2 | S09 | Closeout code: the second whole-tree test pass and the acquisition consolidation, with the acquisition debt of the Phase75 handoff | S01–S08 |
| B2 | S10 | Audit only: completion audit with the VS Code acceptance record, Phase76 handoff, Phase82 freeze inputs, lessons | S09 |

S01–S07 merge in that order, and the second S05 commit follows S07, so B1 is
nine commits. A VS Code acceptance that fails on the B1 candidate is repaired
before the B1 push; one that fails on the B1 head gets a repair slice in B2
before S09. Lean Gate v2 batch rules apply: one commit per slice, two for S05;
one authoritative validation, one fast-forward push and natural exact-head CI
per batch; a failed head is kept and repaired by a child. The root integrates
the lines and writes the shared documents with each batch. Phase75 does not
change the compiled `VERSIONS` (D75.17).

**Midpoint (after the B1 head CI).** S01–S07 are on `main`, and the Windows
jobs passed the new editor and partial-analysis tests. The VS Code acceptance
with the owner's extension passed against a wheel built from the B1 candidate
before the push and again against a wheel built from the B1 head, and both
results are recorded. The measured rate projects within the caps, including the
reserve, and CI health is read. B2 seals only after the midpoint passes.

**Closure.** Phase75 closes when S01–S10 are delivered, the VS Code acceptance
passed on the B1 head, and the S10 commit is on `main` with green natural
exact-head CI. The `0.1.10` release of Phase73, Phase74 and Phase75 follows,
with separate approval.

## Budget

Cumulative repair caps (stop and ask at any cap): C120/F350/D1500/S10
(D75.18). The line work done before this route counts toward them. Phase75
has no real-database run. Every line is protected scope (J20): the owner named
a client for `pietto lsp`, and the editor features that would be cut first are
not in Phase75. Nothing is cut without asking.
