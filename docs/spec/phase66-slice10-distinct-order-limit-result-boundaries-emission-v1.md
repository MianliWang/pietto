# Phase66 Slice10: DISTINCT, ORDER And LIMIT Result Boundaries v1

Slice10 delivers T10 of the Phase66 route: the visible-row DISTINCT of R18, the
three relation ORDER carriers of R19, the R20 hidden STRICT-FD non-support, the
static LIMIT of R21, the Slice10 members of the amended R03 and R11/C09
schedules, and their composition with the published Slice9 window/QUALIFY
results. It changes no product semantics: every admitted shape comes from the
already verified Phase65 Slice8 result stages, and every refusal is an exact
typed blocker.

## Result-stage law

The emitted pipeline consumes the verified `ProjectSQLPlan` result stages and
never infers a stage from SQL text:

```
row / JOIN -> LET -> WHERE -> aggregation -> satisfying -> window -> QUALIFY
-> visible projection -> DISTINCT -> relation ORDER -> LIMIT -> terminal
```

A definition whose plan carries result boundaries ends in one further generated
SELECT, the result body, owned by `project_sql_emission_results.py`. Its visible
projection becomes a closed stage whose terminals are the projection-role result
ports; the result body reads that stage through its own alias and realizes
DISTINCT, ORDER BY and LIMIT in one SELECT, whose SQL evaluation order is the
plan order. The result body is the definition's terminal: a named use, a JOIN
input and a SEMI/ANTI right side bind its post-LIMIT output ports. A non-final
definition keeps its DISTINCT/ORDER/LIMIT inside its own CTE, so a nested LIMIT
is never flattened and an inner ORDER is never an outer presentation promise.

## Delivered semantic domain

| Family | Delivered |
| --- | --- |
| DISTINCT (R18) | native `SELECT DISTINCT` over exactly the visible positional tuple, after projection; NULL-equal; Int/Bool/Text/Decimal comparison domain |
| Hidden values (C12) | a hidden window result, a hidden grouping determinant and a hidden ORDER helper never enter the quotient or the public tuple |
| Ordinary ORDER (R03/R19) | `ProjectIRReusedEffectiveOutput` with its historical provided relation ordering |
| Rebound ORDER (R03/R19/C32) | `ProjectIRReboundExistingOutput` with the provided ordering of its rebuilt stage output, sharing the authored items with the active ordering while naming a different output |
| Completed ORDER (R03/R19) | `ProjectIRCompletedQueryBlockOutput` whose operator evidence is the `ProjectRelationOrdering` itself |
| ORDER items | source order, position, direction, exact established value port; a LET-established constant is a value column and never `ORDER BY <ordinal>` |
| NULL posture (R19) | the language authors none, so the retained policy is target-defined: no `NULLS FIRST/LAST` and no MySQL discriminator; each target's native posture is observed separately |
| Hidden STRICT-FD ORDER (R20) | `hidden_strict_fd_order_approved_non_support`; the visible-key ORDER over the same unique input succeeds |
| Static LIMIT (R21) | `LIMIT <canonical base-10 value>` at the result boundary; absent, `LIMIT 0` and positive stay distinct; never before ORDER or DISTINCT |
| Nested LIMIT (C13) | an inner ORDER/LIMIT producer keeps its boundary; `LIMIT 1` then `> 0` is empty while `> 0` then `LIMIT 1` yields one row |
| R03 sharing (C19) | one ordered and limited producer used twice by an INNER self join; each use binds the same post-LIMIT terminal |
| R11/C09 membership | SEMI/ANTI wrap the complete right result body: right `LIMIT 0` makes SEMI empty and ANTI the whole left BAG, right `ORDER BY ... LIMIT 1` selects exactly one membership key |
| Slice9 composition | QUALIFY -> DISTINCT, selected window -> relation ORDER, QUALIFY -> DISTINCT -> ORDER -> LIMIT, all through established stage ports |

Refusals: `order_expression_requires_established_port` for a computed ORDER tree
(no literal leaves the fixed envelope), `order_comparison_domain_unsupported`
for a Float key, `order_carrier_not_recognized` when an ORDER boundary matches
none of the three carriers, and `distinct_field_equivalence_unsupported` for an
unsupported quotient field. Float DISTINCT never reaches emission: it remains the
upstream `PIE-S2339` error and the target facility records it as `BLOCKED`.

## Exact target differences

| Feature | PostgreSQL | MySQL |
| --- | --- | --- |
| DISTINCT, ORDER BY, LIMIT | emitted | emitted |
| ascending nullable Bool key | NULL sorts last | NULL sorts first |
| NULLS FIRST/LAST | never emitted | no native spelling; no helper generated |

The nullable-key oracle is per target by design: the authored posture is
unspecified, so the facility observes each target's native order rather than
inventing a determinism the source never promised.

## Verification

Plan-to-AST and events-to-bytes stay separately verified. The independent
verifier re-derives from the retained plan alone: the boundary chain and its
input/output ports, the quotient fields and their equivalence, every ORDER
item's carrier, port, direction and posture, the static LIMIT, the terminal
image and the closed projection's helper carries. The byte verifier re-derives
`DISTINCT`, every carried column, `ORDER BY`, each key as a quoted carried
column of the stage alias, `ASC`/`DESC`, the absence of any NULLS spelling, and
`LIMIT` with its canonical digits. A right side bound to its projection instead
of its result body is rejected as a terminal drift. Generated requirements carry
their own causes: `distinct_quotient` and `quotient_field_comparison` to R18,
`relation_ordering`, `order_item` and `order_null_posture` to R19,
`static_limit` and `inner_result_boundary` to R21, `result_terminal_column` to
R03 and `complete_right_terminal` to R11; the retained result demands publish
R18/R19/R20/R21 by subject kind while a projection-role result port and a
canonical export keep their prior generic attribution. The public
`pietto.sql-emission.v1` envelope is unchanged; a terminal column gains
`correspondence.result_origin` with its terminal, projection port and per-stage
image, and the DISTINCT/ORDER/LIMIT tokens appear in `ranges` with their plan
subjects.

## Upstream

No completion route changed. The Gate0 probe showed that a field-only ORDER/LIMIT
producer already reaches a JOIN input on its base route, which is all R03
sharing and R11/C09 membership require. The Slice9 window-producer promotion
still excludes an ORDER or LIMIT barrier, and that retained negative is
unchanged.

## Manifest denominator

50 cases and 141 public documents per target, from 43 cases and 119 documents at
Slice9. Seven new cases contribute 22 variants and the three `O_named_later`
ORDER variants migrate to `VERIFIED`; one four-row relation
(`phase66 agg dupes é`, value = 1, 1, NULL, NULL) carries the exact R18 witness.

| Target | VERIFIED | INPUT_REJECTED | BLOCKED |
| --- | ---: | ---: | ---: |
| PostgreSQL | 112 | 3 | 26 |
| MySQL | 109 | 3 | 29 |

## R03 and R11/C09 closure

```
R03 outstanding joint execution: Slice11 repeated UNION ALL and two import facades.
R11/C09 outstanding membership differences: Slice11 SET.
```

## Changed-path and lifecycle lock

The grammar, generated parser, public legacy SQL emitter, `pyproject.toml`,
`uv.lock`, target pins, Docker configuration, `.github/workflows/ci.yml`,
`scripts/validate.py`, upstream completion and the package version are
untouched. No skip, xfail or marker filter was added, no target case was
removed, and the Interlude IV `NO_GAIN` closure and its four-worker ceiling
stand. A grouped body carrying its own relation ORDER/LIMIT still fails
upstream with `PIE-S2333`; that pre-existing boundary is recorded, not repaired.

```
Phase65 = COMPLETED
Phase66 = ACTIVE
Phase66 Slices1-10 = COMPLETED/PUBLISHED
Phase66 Slice11 = NEXT / NOT IMPLEMENTED
N66 = 16
```
