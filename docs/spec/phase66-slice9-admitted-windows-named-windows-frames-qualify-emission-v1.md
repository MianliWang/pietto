# Phase66 Slice9: Admitted Windows, Named Windows, Frames, QUALIFY And Window Terminal Membership v1

Slice9 delivers T07 and the Slice9 member of the amended R11/C09 schedule. It
changes no product semantics: every admitted shape comes from the already
published R14-R17 domain, and every refusal is an exact typed blocker.

## Delivered semantic domain

| Family | Delivered |
| --- | --- |
| Ranking (R14) | `row_number`, `rank`, `dense_rank` |
| Distribution (R14) | `percent_rank`, `cume_dist`, `ntile(n)` |
| Navigation (R14) | `lag(v[,off[,def]])`, `lead(v[,off[,def]])` |
| Frame value (R15) | `first_value`, `last_value`, `nth_value(v,n)` |
| Specification | PARTITION BY, window ORDER BY with its retained direction |
| Frames (R15) | ROWS and RANGE finite static bounds, offset RANGE under its premises |
| Named windows (R14) | native `WINDOW` clause, generated `w0`, `w1`, … symbols |
| Selected / hidden (R17) | both computed; a hidden result never reaches the public schema |
| QUALIFY (R17) | outer TRUE-only filter over established window ports |
| Composition | aggregate -> window, JOIN -> window, window producer -> JOIN and ordinary use |
| R11/C09 | SEMI/ANTI over the complete right window/QUALIFY terminal |

Identity always comes from the retained `WindowFunctionIdentity`, never from an
authored spelling, and no generic SQL function registry or callable SPI exists.

## Exact target differences

| Feature | PostgreSQL | MySQL |
| --- | --- | --- |
| ROWS, RANGE (incl. offset RANGE) | emitted | emitted |
| `GROUPS`, `EXCLUDE …` | emitted | `window_frame_groups_approved_non_support_on_mysql` |
| `RESPECT NULLS`, `FROM FIRST` | identity omission, no spelling emitted | identity omission |
| `IGNORE NULLS` | `window_ignore_nulls_approved_non_support_in_phase66` | same |
| `FROM LAST` | `window_from_last_approved_non_support_in_phase66` | same |

A MySQL GROUPS refusal is feature-specific: the adjacent ROWS and RANGE windows
of the same body still emit, which the target matrix witnesses. No unsupported
feature is emulated with `WHERE`, `CASE`, a reversed ORDER or index arithmetic.

Window ORDER is not Slice10 relation ORDER. Every window witness orders by a
non-null key, so no target's NULL posture can change a result and no NULL
discriminator is introduced; an offset RANGE never receives one.

## Implementation route

The upstream plan already published `ProjectSQLStageKind.WINDOW` and `QUALIFY`,
so no plan change was needed. Emission gained one owned module,
`project_sql_emission_windows.py`, which builds the window stage; the stage law
`let -> where -> aggregate -> satisfying -> window -> qualify -> projection` is
enforced by the single existing schedule owner. A window block carries its
pre-window inputs forward and appends one result column per occurrence, so two
declarations that spell the same window remain two occurrences. QUALIFY is the
outer predicate stage over those established ports and can never be pushed
before the window or recompute it.

`_promoted_scalar_producer` in `project_final_outputs.py` gained exactly one
further admitted body: a completed window or QUALIFY producer consumed by an
authored JOIN, whose QUALIFY predicate is concrete, whose hidden attempts all
resolved, and which carries no relation ORDER or LIMIT barrier. Lineage status,
`PIE-S2333` and every relationship boundary are untouched, and transportability
grants no relationship endpoint and no M1/M2/M4 guarantee.

Every window result publishes its own physical realization rather than
inheriting an input's: a ranking result is the target's own non-null signed64
integer, a bucket result is the non-null integer width that target returns
(`int4` on PostgreSQL, a bigint on MySQL), a distribution result is the target's
own double travelling through the V06 boundary, and a navigation or
frame-sensitive result carries its value argument's representation and gains only
the possibility of NULL.

## Verification

Plan-to-AST and events-to-bytes stay separately verified. The independent
verifier re-derives every window column from the retained plan alone — function,
policy, modifiers, partitions, orders, directions, frame, arguments and result
port — and the byte verifier re-derives the exact token sequence including the
function name, parentheses, argument order, `OVER`, a generated window symbol,
`PARTITION BY`, `ORDER BY`, `ASC`/`DESC`, the frame unit, both bounds, `EXCLUDE`
and the `WINDOW` clause. Generated requirements carry their own causes:
`window_computation` and the comparison domains to R14, `window_specification`
to R15, `window_result_projection` to R17. The retained demands publish the same
domain: the occurrence, its input uses and its arguments to R14, its policy to
R15, its visible projection to R17. A window result read in a later stage stays
an ordinary reference demand under R01, like every other established port read.

One limit is recorded deliberately. An independent byte verifier detects drift
between the builder and the verifier; it cannot detect a feature both omit.
Five such defects were found during this Slice only by reading the emitted bytes
and their published facts: arguments rendered as empty parentheses, a frame built
and semantically checked but never emitted, a result type inherited from the
order key, retained window demands attributed to R02, and a window reference
classified as a literal demand. A sixth needed the live targets themselves:
PostgreSQL's `ntile` sends int4 where its ranking functions send int8, so the
published bucket storage was wrong until R25 executed it. Real target
execution is what closes that class, which is why R25's live evidence is
mandatory rather than advisory.

## Manifest denominator

43 cases and 119 public documents per target, from 35 cases and 107 documents at
Slice8.

| Target | VERIFIED | INPUT_REJECTED | BLOCKED |
| --- | ---: | ---: | ---: |
| PostgreSQL | 90 | 3 | 26 |
| MySQL | 87 | 3 | 29 |

The window families contribute eight cases and twelve variants. Their row
oracles are written from the four published source rows by hand: ordering by the
non-null duplicated key gives exactly one peer group, which is what separates
`row_number` from `rank` and `dense_rank`, makes a GROUPS frame observable, and
keeps the distribution values exactly representable in binary64.

## R11/C09 closure

Slice9 closes the window/QUALIFY member: SEMI and ANTI wrap the complete right
terminal, which keeps its own window computation and its own QUALIFY, and the
right's selected or hidden result never reaches the left schema. A right without
its window is a different, weaker terminal, retained as the negative control.

```
R11/C09 outstanding membership differences: Slice10 LIMIT0/LIMIT1; Slice11 SET.
```

R03 outstanding joint execution: Slice10 ordinary/rebound/completed ORDER and
ORDER/LIMIT sharing; Slice11 repeated UNION ALL and two import facades.

## Changed-path and lifecycle lock

The grammar, generated parser, public legacy SQL emitter, `pyproject.toml`,
`uv.lock`, target pins, Docker configuration, `.github/workflows/ci.yml`,
`scripts/validate.py` and the package version are untouched. No skip, xfail or
marker filter was added, no target case was removed, and the Interlude IV
`NO_GAIN` closure and its four-worker ceiling stand.

```
Phase65 = COMPLETED
Phase66 = ACTIVE
Phase66 Slices1-9 = COMPLETED/PUBLISHED
Phase66 Slice10 = NEXT / NOT IMPLEMENTED
N66 = 16
```
