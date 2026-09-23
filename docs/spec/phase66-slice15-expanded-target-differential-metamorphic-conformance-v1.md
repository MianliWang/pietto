# Phase66 Slice15 Expanded Target, Differential And Metamorphic Conformance v1

## Authority and scope

This contract delivers Phase66 route row 15 (expanded C01–C32 combinations and C30,
contributing E03/E04/E09) under the
[Phase66 route lock](phase66-dialect-sql-emission-product-phase-initiation-gate-route-lock-v1.md).
It adds conformance evidence only: one target case with three generated artifacts,
cross-execution metamorphic laws over each full target run, local independence and
boundary controls, and C30 attribution routing. It adds no emitter, lowering rule,
renderer, verifier rule, public format, CLI flag, public Python export, process family or
receipt field, and it changes no production module.

The receipt stays `pietto.target-conformance-receipt.v2` with unchanged structure and
meaning. By explicit user decision its file ceiling rises from 32 MiB to 33 MiB
(34,603,008 bytes), because the three new witnesses (about 0.46 MB per target, every
VERIFIED document carried in full twice) did not fit the Slice14 MySQL headroom of about
0.18 MB. No other limit, representation, compression, deduplication or sidecar changes.

## Promise-to-evidence ledger

Every route rule keeps its completing Slice's real witness; Slice15 adds a law or control
where one discriminates more than the existing oracle:

- R01–R05 (scan, values, named DAG, parameters, row expressions): F1 and F2; R03 also
  gains the executed predecessor JOIN unit below.
- R06 (three-valued predicates): the NULL-dropping filter of F4.
- R07/R08/R11 (CROSS/INNER, LEFT/RIGHT, SEMI/ANTI): F5 and F10 plus the JOIN chain.
- R09/R10 (restricted FULL): unchanged PostgreSQL positive and MySQL negative.
- R12/R13, R14–R17, R18, R21, R22: F7, F9, F3, F6, F3/F8 respectively; R19/R20 keep their
  oracles and negatives.
- R23: the independence controls below. R24 and R26: unchanged console case and `phase66`
  process family. R25: relation checking inside each full run and the C30 routing
  control.
- C07/C08 gain F10 and the chain, C09 F5, C04 F7, C13 F6, C17 the F3 derivation, C20–C25
  the independence controls, C30 the routing control; every other C keeps its existing
  witness.

No row is reclassified. No `MISSING_OBSERVATION`, `PROMISED_DOMAIN_DEFECT` or
`APPROVED_NON_SUPPORT` entry is created.

## Verification independence

The complete verifier's row route starts with `emission_blockers(request)`, which reuses
the construction walk `realize_rows` only for applicability, resource and generated-scope
problems. The candidate AST's plan correspondence, the events-to-bytes check, both
requirement denominators, parameter uses and the node recount are independent of
construction. Two controls fix this:

- coordinated drift: swapping the published outputs of the final row body, or the two
  inputs of the second JOIN unit, and rebuilding SQL bytes, ranges and both denominators
  from the drifted AST leaves exactly one issue, `plan_ast_correspondence`;
- constructor fault: the same swap injected into the emitter's construction step is
  refused as `BLOCKED` with the single blocker `PIE-B1008 plan_ast_correspondence`.

## Predecessor JOIN inputs and multi-hop paths

A JOIN whose left input is the preceding JOIN of the same definition is admitted: the
chain `rows LEFT JOIN r ON rows.id > r.id RIGHT JOIN last ON r.id == last.id` emits two
JOIN units, the second reading the first, and exports, corresponds and decodes with a
`join_input` whose producer is `join_body` 0. The Slice14 statement that multi-hop path
JOINs are the only source of predecessor JOIN inputs was wrong; that historical contract
stays unchanged and this contract records the correction. A two-hop `via` path still
fails `admitted_join_shape` (its first hop's right input has a producer without a binding
use) and stays `BLOCKED` with `PIE-B1003` join blockers: it is outside the Slice7 finite
JOIN input domain, not a new non-support decision.

## Target case

`M_metamorphic_composition` (owner `main.pietto` query `result`, VERIFIED on both targets):

| Variant | Source over | Independent oracle |
| --- | --- | --- |
| `join_chain_accumulated` | one-column `phase66_rows` (ids 1, 1) | `a, b` = `[NULL, 1]` twice |
| `union_filter_outer` | native table (id 11, neighbor NULL, twice) | `k` = `[11]` twice |
| `union_filter_operands` | the same table, filter inside each operand | `k` = `[11]` twice |

`rows.id > r.id` never holds on equal ids, so the LEFT JOIN null-extends `r` and the RIGHT
JOIN on that NULL keeps each `last` row unmatched: the accumulated nulling of C08 through a
predecessor unit. The two UNION ALL forms are distinct SQL programs.

## Metamorphic laws

`cases.check_relations` reads the rows of every VERIFIED submission of one full run and
never reads a case oracle, so an oracle that agrees with a wrong result still has to
satisfy it. It runs after the case loop of every full-manifest target run (a failure is a
`case_execution` failure) and in strict receipt verification. It adds no receipt bytes.

| Family | Law and premise |
| --- | --- |
| F1 | Literal policy: every `*_preserve`/`*_bind` pair of P, R, S fixed values and SET literals returns equal BAGs. |
| F2 | Alpha renaming and context: a renaming producer, an imported module and a row producer are invisible (P named = direct, S named = imported, U = T); naming another column is not (P plain differs). |
| F3 | BAG duplication: with A = sa.key (EXCEPT ALL against an empty operand) and B = UNION ALL − A, INTERSECT/EXCEPT ALL are min/difference and the DISTINCT forms are their supports; X ⊎ X has even multiplicity (DISTINCT operands exactly two), X ∪ X is duplicate-free, visible DISTINCT is the support of all ids. |
| F4 | Filter over BAG union: the outer filter over UNION ALL equals the filter distributed into the operands. |
| F5 | SEMI/ANTI partition: against one right input they partition the left BAG (empty and LIMIT 1 rights, JOIN shapes, SET membership); SEMI has INNER's support; CROSS repeats each left row once per right row. |
| F6 | Result stages: LIMIT 0 is empty, LIMIT 2 keeps at most two input rows, and LIMIT-then-filter is contained in but differs from filter-then-LIMIT. |
| F7 | Emptiness: GLOBAL over a filter keeping nothing equals GLOBAL over an empty relation (one row); GROUPED and constant-grouped over no row are empty; a GLOBAL empty operand doubles under UNION ALL. |
| F8 | SET nesting and position: A−A−A is empty while A−(A−A) is the support of (A⊎A)−all A; the first column of a relabelled two-column UNION ALL is the key UNION ALL. |
| F9 | Windows: a named window equals its inline twin, hiding a QUALIFY value keeps the rows, ranks follow peers and ROW_NUMBER is a permutation. |
| F10 | Outer null extension: LEFT keeps every left id and null-extends all right columns jointly; RIGHT and the JOIN chain keep every right id. |

Controls: the case oracles satisfy every law on both targets; one changed execution breaks
its law; a missing premise execution is an error, never a vacuous law; and in a complete
receipt an observation mutated together with its own oracle (F4, F5, F9) passes the case
check and is refused by the law.

## Attribution (C30)

A relation failure inside a full run is recorded at stage `case_execution` with category
`UNRESOLVED_ATTRIBUTION`; the facility still assigns `INFRASTRUCTURE_FAILURE` only to
acquisition failures and never assigns a compiler or target defect automatically.
Handwritten SQL never substitutes for generated-artifact execution: every submission must
equal its artifact's SQL and parameters.

## Process and historical compatibility

The `phase66` process family keeps its eleven fixtures (98 requests over 16 cells with both
interpreters) and every historical process subset is unchanged; its private-observation
corpus test now covers 303 VERIFIED generation inputs (postgres153, mysql150). Legacy SQL,
JSON, CLI and golden outputs are unchanged.

## Denominator

The target corpus is 62 cases/190 public documents per target (184 API and 6 console
documents): postgres157 VERIFIED,4 INPUT_REJECTED,29 BLOCKED; mysql154 VERIFIED,4
INPUT_REJECTED,32 BLOCKED. Fresh full receipts on both targets are required.

## Lifecycle

Phase66 remains `ACTIVE`; Slice15 completes only upon successful natural exact-head CI;
Slice16 (completion audit and handoff, audit only) is next and not implemented. N66 remains
16 and the package version remains 0.1.0.
