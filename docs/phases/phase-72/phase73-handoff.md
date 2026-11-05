# Phase72 handoff — Phase73 readiness

This handoff takes effect when Phase72 closes under its
[completion audit](completion-audit.md). On 2026-11-05 the owner let Phase73
start before that: its Gate 1 is recorded, its Gate 0 is provisional on the
Phase72 batch-2 integration tree and rebinds to `main` once the batch-2 head
passes natural CI and tag `v0.1.9` exists, and its lanes replay onto that
head. Phase73 publishes nothing before `0.1.9`. Check live `main`, its tree
and its CI before acting on any hash here.

## What Phase73 receives

- `0.1.9` contains all of Phase72: `pietto fmt`, `concat`, `same_value`,
  `stddev`, project typing of always-None numbers, fewer false JOIN fan-out
  refusals with grouped keys as unique keys, one `Float` value contract, the
  PostgreSQL backward asof JOIN and the PIE-P1012 header warning. The
  [release notes](../../release-notes.md) list every change, refusal and
  known limitation.
- Phase73 releases as `0.1.10`: versions stay on `0.1.x` patches until about
  the end of Phase80 (owner, 2026-11-05).
- The test tree had its first whole-tree reorganization: no phase-named
  helper and no test-to-test import is left. Its leftover list is below; the
  next pass is due by the Phase75 close.
- Phase73 inputs: the Phase72 section of the
  [engineering lessons](../../references/engineering-lessons.md#phase72), the
  latest qualified CI health, the joint Phase72–75 plan (scope lines T-A,
  T-L, T-G, T-K and T-S, each with its MySQL stance) and the owner answers
  J5–J8, J12 and J28, which the Phase73 Gate 1 confirmed. The
  [roadmap](../../roadmap.md#future-roadmap-v6) states the reroutes.

## Deferred decision points (carried from the Phase72 handoff)

These rows are carried verbatim from the
[Phase72 handoff](../phase-71/phase72-handoff.md). Phase72 did not change
them, except that it restored the D-11 and D-12 cases its Gate 1 case list
accepted; the rest of that row stays as written.

| 事项 | 主责 / 会审 | 最晚决定点；当前处置 |
|---|---|---|
| 多层collection | NestedRelation semantic owner；type/result/compiled owners会审 | 首个依赖多层的扩展Gate1或设计冻结前，取先发生者；Phase72开局明确仍unsupported，不新增phase号/预算 |
| nested UNION、ordinary RIGHT/FULL carry、nested windows | ProjectSQLPlan owner；semantic/target/result会审 | 对应形状首次准入Gate1前，闭合类型、grain、lineage与lowering；现有拒绝保留 |
| capture let读取另一个capture let | scope/capture semantic owner；SQLPlan会审 | nested correlation首次准入Gate1前；不得从普通capture能力推得支持 |
| child级恢复、nested R2、relay/sink | execution/recovery owner；jobs/result/relay会审 | 对应入口开放的Gate1/实施前先定durable coordinates、effect identity与ACK合同；保留拒绝，无虚构未来phase |
| D-11/D-12整体恢复 | Pietto lead协调既有semantic owners | 未排期恢复责任；在提出相应放宽之前完整审阅。已有定点修复不等于整体完成 |
| G18 / Teach mechanism | Pietto lead；所有者作信任决定 | 当前HOLD；任何机制/marker/rebootstrap变化前重新派发，保持host-only Gate2 |

The Phase73 Gate 1 deferred multi-level collections, capture-of-capture,
nested carry and windows, and child-level recovery, R2 and sink again, each
with a negative example.

## Items routed to Phase72 that its lanes did not take (J3)

| Item | Where it goes |
| --- | --- |
| Query header parameters of type `Decimal`, `Date`, `Timestamp` and `UUID` (D70.01; today PIE-S2353 accepts only `Bool`, `Int`, `Float` and `Text`) | Phase73 small-features line (T-S); a new compiled parameter kind, so save, R1 and export each get a witness; MySQL goes to the Phase74 catch-up (Phase73 Gate 1) |
| The external nullability v2 proposal and general narrowing after `x is not None` | decided after a read-only lead review (Phase73 Gate 1); at the latest before any narrowing rule is adopted and before the Phase82 freeze |
| `==`, `same_value` and ordering of nested values, and set operations over rows with nested values (PIE-S2805 today) | stay refused (Phase73 Gate 1); Phase73 adds only nested GROUP/DISTINCT keys (C1) |
| The shared type part of database arrays and JSON | Phase76, for information |
| `Float` field arithmetic, unary minus on a field, `/` and `%`, and `Float` beside an `Int` literal (`price > 1`) | after the `Float` contract (B15); unscheduled. Division by zero differs: PostgreSQL raises an error, MySQL returns NULL |

## Open follow-ups

| Follow-up | State and owner |
| --- | --- |
| A capture `let` with `LIMIT 1` is accepted without a uniqueness proof, so ties pick any row; and a general at-most-one grain fact for a `LIMIT 1` LATERAL `let` | the Phase73 Gate 1 keeps the behaviour and documents it, with no new code or refusal; the grain fact is deferred |
| Single-file MySQL `SUM(Int)` returns `DECIMAL`; single-file PostgreSQL `CASE ... THEN 1` returns `integer` | observed in the Phase72 runs; values correct; type contract to review with the Phase74 MySQL catch-up |
| MySQL sends `LONG` for a project comparison column that is a GROUP BY key or DISTINCT column, where the emission document declares `my_signed_bool` | the reader accepts it since `0.1.3`; values correct; the documents state it |
| For a `==` column of `select distinct` after a UNION, the test decoder `probe.decode_public` expects nullable `true` where the emission document says unknown | not caused by Phase72; unknown is the conservative public value; Phase73 decides whether the decoder or the product value changes |
| Asof JOIN in project contexts the lowering does not cover (a relation `let NAME:` block, a table-function FROM) and project aggregates after an asof JOIN without a unique-key match | refused with fixed diagnostics; widen only with a new spike and its own Gate 1 item |
| Leftovers of the whole-tree reorganization: the `*audit*` owners, about 45 other history-named owners, source-substring locks without a behaviour test, misplaced owners from before Phase72, and test files that product source names as capability evidence (renaming them needs a `src/` change) | the second whole-tree pass, due by the Phase75 close |

## Process inputs

- The owner allows up to 10 coding lanes at once; each runs at `nice -n 19`
  with `pytest -n 2` at most; one real-database run at a time. Gate 2 runs on
  the integration host only; since 2026-11-05 it runs when ready, announced
  first by the lead, without waiting for the owner's Windows applications to
  be idle.
- A lane delivers a diff identified by its sha256 and never commits; the lead
  integrates in dependency order and runs one Gate 2 per batch head.
