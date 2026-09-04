# Phase 63 Slice 15 Inspection, Pure Boundary, And Differential Assurance v1

## Status

This private contract owns the final Phase-63 observation and assurance layer.
It consumes one exact VERIFIED Slice-14 analysis bundle and adds no parser,
semantic, completion, IR-construction, SQL, CLI, JSON, optimizer, or executor
behavior. Phase 63 remains active; Slice 16 and Phase 64 are not implemented.

## Baseline And Budgets

Gate 0 rebound the exact published Slice-14 authority:

```text
commit = 23c9d9c4e657501b07664c7f65ee4e455ff7bb0f
tree = 34e654d856463cc6aa63fbf4cc3591e788c1e493
parent = 8b56db95ab45933d05db2123b3e89fb81b8ac2fa
subject = Add Phase 63 query-block Project IR
natural CI = 33877240716
push / main / attempt 1 / success
Python 3.12/3.13 = success
```

The synchronized baseline was clean at divergence `0/0`, with empty index and
untracked inventory, no active Git operation, and `NUL` absent. Slice-15
governance starts at:

```text
production repairs = 0/12
mechanical closure = 0/12
authoritative validator starts = 0/4
```

## Authority Closure Matrix

This matrix was reviewed against the published Slice-14 tree before either
Slice-15 production owner was created. “Exact” means retained object identity
and complete tuple membership in canonical runtime/source order.

| Authority | Producer | Retaining carrier | Exact root | Membership proof | Inspection section | Portable representation | Winner-free query | Forbidden reconstruction | Foreign-root adversarial case |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Effective owner entry | Slice 12 effective-output completion | `ProjectIRQueryBlockEntry.semantic_entry` | `bundle.root.completed.effective_outputs.entries` | identity-aligned zip with `owners` and Slice-14 `entries` | `entries` plus four variant tuples | `owner_entry` record with document-local `owner_entry` ref | owner occurrence identity -> complete entry tuple | name lookup or latest declaration | same owner identity carrying an entry from another snapshot |
| Active output | Slice 14 concrete ledger entry | `entry.active_output` | exact `ProjectIRReusedEffectiveOutput`, `ProjectIRReboundExistingOutput`, or `ProjectIRCompletedQueryBlockOutput` | the explicit field is a member of the entry's authoritative output family and matches `active_properties.output` | `active_outputs` | explicit `owner_entry.active_output -> output_value` ref | owner identity -> complete active-output tuple | `row_outputs[-1]`, highest coordinate, or terminal fallback | foreign active output grafted onto an otherwise local entry |
| Active properties | Slice 14 concrete ledger entry | `entry.active_properties` | the same exact concrete ledger entry | the explicit field occurs exactly once in that entry's property family and owns `active_output` | `active_properties` | explicit `owner_entry.active_property -> relational_property` ref | owner identity -> complete active-property tuple | `row_properties[-1]` or matching by output value equality | foreign property object whose values resemble the local property |
| Query-block operator | Slice 14 IR construction | completed-entry `operators` or rebound fragment `logical_stage.operators` | `bundle.root.entries` | exact tuple item and exact attached `node`/row-output producer | `operators` | `operator` record with owner, ordinal, node, row output, kind, and provenance | plan-node ref -> complete operator tuple | infer sequence from node coordinates or output order | reordered operator storage or an operator from a foreign entry |
| Relation-input edge | Slice 14 reuse/rebind construction | `entry.relation_input` | rebound/completed concrete entry | exact dependency, authority, slot, use, compatibility, and upstream active roots | `relation_inputs` | owner-entry fields for upstream owner, use, and compatibility | owner identity or use ref -> complete edge tuple | infer upstream from the last output or rebuild a cross edge | local consumer with a foreign upstream output/use |
| Final field identity | Slice 12 final-output completion | `ProjectIRQueryBlockRowField.final_identity` | `entry.semantic_entry.fields[*].identity` | exact identity object retained by the final projection field | `final_field_identities` and `query_block_row_fields` | `row_field` final-owner/kind/position/name fields | exact field identity -> complete field tuple | field name, ordinal, or row-shape reconstruction | equal-looking field identity from another completed root |
| Window selected scalar | Slices 10/12 and Slice 14 output allocation | `ProjectIRQueryBlockScalarOutput` plus its selected semantic source | completed entry and its exact WINDOW_EVALUATION evidence | scalar source is the selected evidence and its occurrence is a real structural output | `selected_window_scalars` and `window_evidence` | `window_selected` record referring to operator, scalar output, and row field | output ref or operator ref -> complete selected tuple | synthesize a scalar from hidden evidence | selected evidence/output pair split across snapshots |
| Hidden window evidence | Slices 10/12 | `ProjectIRQueryBlockWindowEvidence.hidden` | exact completed-output root | exact retained hidden tuple; no member has a Slice-14 scalar output | `hidden_window_evidence` | `window_hidden` record with no output field in its closed schema | operator ref -> complete hidden-evidence tuple | manufacture an output from hidden QUALIFY computation | hidden evidence taken from a foreign completed root |
| Grouped/global grain origin | Slice 14 grain-origin extension | `ProjectIRQueryBlockGrainOriginExtension.origins` | `bundle.root.grain_origins` | exact context/operator; GROUPED retains its exact factor and GLOBAL retains none | `grain_origins`, `grain_factors`, `grain_dependencies` | `grain_origin` and `grain_factor` refs plus property-local dependency records | operator ref or exact factor identity -> complete tuple | infer grain from GROUP BY text, empty keys, or pre-aggregation JOIN grain | origin/context/factor drawn from another snapshot |
| Terminal blocker | Slice 14 all-or-none ledger | `ProjectIRQueryBlockTerminal.blocker` | exact terminal entry | reason-specific identity proof in the terminal carrier; zero Slice-14 allocation | `terminals` and `terminal_blockers` | terminal owner-entry reason, blocker kind, optional blocker entry/use refs; no active refs | owner identity -> complete why-not tuple | generic missing-output reason or partial IR recovery | foreign upstream terminal/compatibility/JOIN-use blocker |
| Combined reverse use | Slice 14 verified analysis builder | `ProjectIRQueryBlockAnalysisBundle.combined_reverse_uses` | the admitted analysis bundle | one source-ordered entry per exact combined output with every direct use | `combined_reverse_uses` | `analysis_reverse_use` record with output and complete use refs | output ref -> complete reverse-use tuple | first/last use, deduplication, or reconstructed semantic edges | reverse entry from an equal-looking foreign graph |
| Topological entry | Slice 14 verified analysis builder | `combined_topological_order` | the admitted analysis bundle | exact node occurrence membership and complete acyclic order | `combined_topological_order` | `analysis_topological` record with ordinal and node ref | node ref -> complete topological tuple | sorting node names or treating allocation order as authority | node from a foreign scope at a local ordinal |
| Reachability entry | Slice 14 verified analysis builder | `combined_reachability` | the admitted analysis bundle | exact source occurrence and complete source-order reachable tuple | `combined_reachability` | `analysis_reachability` record with source and reachable refs | source node ref -> complete reachability tuple | partial search, cached winners, or name-based reachability | local source paired with a foreign reachable tuple |

The active-root and final-field laws are literal:

```text
active output -> entry.active_output
not row_outputs[-1]

active properties -> entry.active_properties
not row_properties[-1]

final field -> retained Slice12 identity
not name/ordinal reconstruction
```

## Admission And Runtime Inspection

The sole positive admission is an exact `ProjectIRQueryBlockAnalysisBundle`
whose retained verification has status `VERIFIED` and zero issues. A bare
snapshot, a bare verification result, a subtype, or an equal-looking foreign
carrier is not admission. Inspection retains identity through Slice 14,
Slice 13, Slice 12, the Phase-62 verification/JOIN root, and the Phase-61
Project plan. It does not rerun construction or verification.

Runtime sections are occurrence-complete, identity-retaining tuples. Queries
accept exact typed owner identities or runtime refs and return all matching
items. Cross-snapshot refs fail closed. There is no `get_best_*`,
`get_latest_*`, `get_last_*`, name resolver, free-form query language, or
single-item winner convention.

Historical rich observation remains owned by `ProjectIRInspection` and
`ProjectPhase62Inspection`; Slice 15 neither duplicates those models nor
changes their formats.

## Pure Boundary

The additive marker is:

```text
pietto.phase63-query-block-ir-inspection.v1
```

The pure owner is standard-library-only and uses closed document-local ref
domains. It serializes no opaque snapshot scope, Python object identity,
address, hash, `repr()`, cwd, absolute temporary root, clock, locale, random
state, or environment path. A bare integer is never a runtime ref.

The document records VERIFIED admission; Slice-14 allocation boundaries;
owner, dependency, and schedule order; ledger variants and explicit active
roots; combined topology; operators including additive `qualify`; row fields
and retained final identities; relational classes, keys, FDs, FD-index
membership, grain origins/factors/dependencies; selected and hidden windows;
ORDER, LIMIT, and conservative effects; and all three combined analyses.

The total evaluator returns either `OK` with canonical bytes or one closed
normalized rejection with numeric record/field coordinates and no bytes. It
validates document shape, sections, bounded values, dense refs, domains,
endpoints, entry/active/terminal laws, property locality, grain links,
window-output separation, and reverse/topological/reachability consistency.
It does not compile expressions or reproduce relationship, JOIN, key, FD,
grain, window, or QUALIFY semantics.

Canonical-byte equality is not runtime identity, semantic identity, Project
field identity, rewrite equivalence, or cache/content identity. No digest or
persistent registry is introduced, and exactly one canonical encoder owns the
format.

## Real Authored And Differential Assurance

The checked-in probe starts with real `.pietto` text and follows only normal
builders:

```text
check_project_parse_only
-> build_empty_project_semantic_result
-> build_project_completed_semantic_result
-> build_project_query_block_ir
-> verify_project_query_block_ir
-> build_project_query_block_ir_analysis_bundle
-> build_project_query_block_ir_inspection
-> pure document
-> canonical bytes
```

The bounded corpus covers reuse, rebound chains, joined projection, INNER and
LEFT JOIN, accumulated multi-hop JOIN, WHERE, GROUPED and GLOBAL aggregation,
satisfying, selected and hidden windows, QUALIFY, relation ORDER, LIMIT, mixed
tails, duplicate-name intermediate fields, semantic terminals, and the
effective-JOIN rebind terminal. A reviewed checked-in manifest compares full
observations, records, and bytes; SHA-256 is only a review summary.

The outer pytest owns interpreter discovery, source relocation, wheel
construction, subprocess orchestration, and environment normalization. The
source matrix is Python 3.12/3.13 across `PYTHONHASHSEED` 0, 1, 7, and
4294967295; seed 7 also runs relocated source and an isolated installed wheel
for every available supported interpreter. It supports serial execution and
xdist `--dist=loadfile`. Negative comparison uses typed normalized outcomes,
never CPython exception text.

## Historical Compatibility And Non-goals

`pietto.project-ir-inspection.v1` and `pietto.phase62-inspection.v1` remain
byte- and evaluator-compatible for unchanged historical inputs. The new
format is additive and does not wrap or upgrade either old document.

Slice 15 creates no parser/AST or semantic authority, active-root decision,
query-block construction rule, JOIN/window/QUALIFY/ORDER/LIMIT law, SQL,
CLI/JSON, Project Explain, package behavior, workflow behavior, optimizer, or
executor. Generic JOIN over effective outputs remains Phase 64.

## Frozen Closure And Handoff

The pre-mutation core closure is `A5/M5/D0`, ten paths: two private production
owners, this spec, one self-contained probe, one principal assurance test,
`docs/roadmap.md`, `docs/status.md`, the sole mutable lifecycle reader, the
differential-probe aggregation reader, and the inventory-count reader.
Production Python moves from 177 to 179 files and tests from 419 to 421. No
grammar, generated parser, golden, public CLI/JSON, or packaging file changes.

On exact-head publication, Phase 63 remains `ACTIVE`, Slices 1–15 are
`COMPLETED / PUBLISHED`, Slice 16 is `NEXT / NOT IMPLEMENTED`, and Phase 64 is
`NOT STARTED`.
