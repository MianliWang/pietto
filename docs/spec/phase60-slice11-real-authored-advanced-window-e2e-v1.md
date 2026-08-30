# Phase 60 Slice 11 Real Authored Advanced-Window E2E v1

## Answer And Scope

Slice 11 proves the published advanced-window architecture from real authored
`.pietto` files through production parser, semantic, IR, SQL, CLI, Project,
package-graph, and private-inspection entry points. It adds tests and lifecycle
evidence only: no production, grammar, generated, golden, package, workflow,
public schema, Project Explain, or dependency path changes.

The predecessor is commit
`9d42564a73228c2ee3137372d84c220d6650778d`, tree
`ac793531cffbca7ac937d49815a96be8742de307`, with successful natural
exact-head CI `33288658967` on push attempt 1 for Python 3.12 and 3.13.

The E2E test writes authored source/config/package inputs under pytest-owned
temporary roots. It never constructs final `WindowCallIR`, `RelationIR`,
`NamedWindowLoweringDecision`, `WindowResultProjectFact`,
`PackageGraphSnapshot`, or inspection records/links. The reused CLI, Project,
and package helpers are locked to real file creation followed by production
entry points.

## Bounded Authored Corpus

The five-source corpus is small and orthogonal:

1. PostgreSQL native reorder uses a source-order forward base reference with
   `row_number`, `first_value`, and `lag` over one hierarchy. The emitted
   reachable `WINDOW` order is base then child, the unused declaration is
   absent, `row_number` remains direct, and `first_value` receives its
   effective `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW EXCLUDE NO
   OTHERS` frame use-locally. `HAVING`, `WINDOW`, relation `ORDER BY`, and
   `LIMIT` remain in exact order.
2. PostgreSQL exact inline fallback uses a framed `GROUPS BETWEEN 1 PRECEDING
   AND CURRENT ROW EXCLUDE TIES` base, a derived named window, and
   `nth_value(value, 2) FROM FIRST RESPECT NULLS`. Its SQL bytes equal an
   independently authored inline program, with no emitted `WINDOW` clause and
   no identity merge.
3. PostgreSQL inline frame coverage adds authored `ROWS ... EXCLUDE CURRENT
   ROW` and offset-free `RANGE CURRENT ROW EXCLUDE GROUP` calls. Together with
   the first two sources, the corpus covers ROWS/RANGE/GROUPS and all four
   EXCLUDE states through legal frame-value callers.
4. MySQL native preserve uses a source-order forward alias, an extended named
   use with ROWS, `nth_value FROM FIRST RESPECT NULLS`, and an unused
   declaration. The reachable declarations remain child then base and the
   unused declaration is absent from exact SQL.
5. The PostgreSQL native and MySQL preserve sources are passed as actual files
   through the paired `pietto emit-sql` CLI harness. Both return zero, emit no
   stderr, and match exact SQL including one final newline.

This Slice does not widen Slice 9's bounded frame-value input contract beyond
direct fields/scalar literals. Capability negatives, `NOT_LOWERABLE`, hash
seeds, relocation, installed-wheel parity, and environment differential work
remain Slice 12.

## Project, Lineage, And Inspection

The PostgreSQL native source is reused unchanged as the Project/package source
of truth. Production results prove four CONCRETE named window outputs with
exact authored uses and named targets. Inherited PARTITION/ORDER dependencies
retain the base declaration component locations. Argument, default,
partition, order, and relation-input roles remain ordered real dependencies;
frame, exclusion, NULL treatment, FROM direction, and spelling add no fake row
edge.

`WindowSemanticProvenance` retains inherited component origins, effective
RANGE/NO OTHERS frames, explicit RESPECT NULLS, and explicit FROM FIRST for
`nth_value`.
Package construction retains existing package/module/declaration/field refs,
projects source-ordered child/unused/base named-window records plus four
semantic records, and exposes exact child-to-base and use-to-child links.
Repeated private inspection is byte-identical and pure evaluation is `OK`.
Semantic window provenance remains separate from Phase 59 direct data-lineage
steps.

## Reader Closure

The exact Slice 11 changed-path allowlist is:

```text
docs/roadmap.md
docs/spec/phase60-slice11-real-authored-advanced-window-e2e-v1.md
docs/status.md
tests/test_active_phase_lifecycle.py
tests/test_phase60_slice11_real_authored_advanced_window_e2e.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A2/M4/D0`, six paths. Dynamic Phase-60 test discovery already admits
the new test and requires no reader edit. Historical Slice 1–10 specifications
remain immutable.

## Lifecycle And Publication

The candidate records Phase 60 active, Slices 1–10 completed, Slice 11
current, and Slice 12 next/unstarted. Natural exact-head CI owns completion
without a status-only follow-up commit. The exact ordinary commit subject is:

```text
Add Phase 60 real authored advanced-window E2E
```
