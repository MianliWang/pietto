# Phase66 Slice11: Six SET Forms, Positional Types And Operand-Local Boundaries v1

Slice11 delivers T11 of the Phase66 route: PostgreSQL and MySQL emission for the
six SET forms of R22 over their admitted inputs, positional type and output
correspondence, exact operand terminals and nesting boundaries, and the last
R03 and R11/C09 joint-execution members. It changes no product semantics: every
admitted shape comes from the already verified Phase65 Slice9 SET plan, and every
refusal is an exact typed blocker or the inherited upstream rejection.

## Delivered semantic domain

| Family | Delivered |
| --- | --- |
| Forms (R22) | `UNION ALL`, `UNION DISTINCT`, `INTERSECT ALL`, `INTERSECT DISTINCT`, `EXCEPT ALL`, `EXCEPT DISTINCT`, always with the explicit quantifier |
| Structure | one SET unit per SET definition: `(o0) OP (o1)` for two operands and `((o0) OP (o1)) OP (o2)` beyond, so the authored source-order left fold is spelled rather than left to precedence; a nested SET producer is its own CTE and is never inlined |
| Operands | wrapper SELECTs over each producer's complete terminal (physical scan fields or the producer CTE's terminal columns), positionally, labelled with the SET-owned output labels; no operand body is recomputed |
| Positions (C17/C18) | corresponding columns align by position; labels come from the first authored operand; identity belongs to the SET owner |
| Domains (R22) | V01 Int with width-equal storage and merged exact ranges, V02 Bool, V03 Text with identical encoding/collation/padding premises, V04 validated Decimal(p, s) identical across operands; UNION ALL additionally transports finite Float (signed zero preserved) without any equality requirement |
| Nullability | the published operation-specific rule (EXCEPT left, INTERSECT non-null if any operand is, otherwise nullable if any operand is), cross-checked against every operand's realization |
| Operand-local boundaries (C13/C19) | ORDER, LIMIT (absent, zero, positive) and DISTINCT stay inside the operand's own CTE; the SET body itself carries no ORDER/LIMIT; an outer consumer keeps its WHERE/ORDER/LIMIT above the SET |
| Producers | row/LET/WHERE, grouped/GLOBAL/satisfying, window/QUALIFY, DISTINCT/ORDER/LIMIT operands; a SET output feeds named uses, JOIN inputs, window and result consumers as an established terminal |
| R03 (C19/C32) | the repeated UNION ALL graph (`O_named_later/union_dag`) and the two import facades (`O_named_later/two_facades`) execute on both targets through the installed pipeline; a shared definition is one CTE, every use is its own operand, and facades resolve through their real modules |
| R11/C09 | SEMI/ANTI wrap the complete right SET terminal with the existing EXISTS/NOT EXISTS lowering; SET NULL equivalence inside the right side stays distinct from TRUE-only ON matching |
| Literals | PRESERVE and BIND values inside a shared operand keep one rendered occurrence, one slot and one server index across two uses |

Refusals: `set_column_physical_representation_mismatch` (PIE-B1002) when two
individually valid operands carry different physical Int widths, storages or
domains; `set_column_text_domain_mismatch` and
`set_column_decimal_parameter_mismatch` (PIE-B1005); `set_column_nullability_drift`
and `set_column_logical_type_drift` (PIE-B1002); `set_row_equivalence_domain_unsupported`
(PIE-B1003) for an equality form over a non-V01–V04 column. Float in the five
equality forms stays the upstream `PIE-S2344`, arity and logical-type mismatches
stay `PIE-S2342`/`PIE-S2343`, and a SET directly into GROUP/GLOBAL stays the
inherited `PIE-S2333`. None of these is emulated.

## Implementation route

The upstream plan already published `ProjectSQLSetBody`, operands, inputs and
positional columns, so no plan change and no completion change was needed; the
Gate1 probes showed every promised composition reaching an independently
verified plan. Emission gained one owned module, `project_sql_emission_sets.py`,
which builds the SET unit; the row-shape and JOIN-shape gates admit SET bodies,
the aggregation admission check excludes SET definitions from its stage-block
inventory (a SET owns no stage block by design), and a plan with a SET body is
rendered as an ordered unit list like a JOIN plan. Membership, named-use and
JOIN consumers bind the SET unit through the existing definition/terminal
machinery, so a right side can only read the post-SET terminal.

## Verification

Plan-to-AST and events-to-bytes stay separately verified. The independent
verifier re-derives from the retained plan alone: the operand inventory and
order, each operand's complete terminal read, the positional column map, every
output's realization (width, storage, domain, parameters and nullability rule),
the SET-owned labels and the terminal image; a producer read through anything
but its terminal CTE is a drift. The byte verifier re-derives the operand
parentheses, the spelled `<KIND> <QUANTIFIER>` operator, the explicit fold
grouping, every carried column, alias and label and the producer references.
Generated requirements carry their own causes: `set_operation`, `set_operand`,
`set_column` (with the client-encoding premise for Text) and
`set_row_equivalence` to R22, a physical operand's scan and field
representations to R01/R02, `complete_right_terminal` to R11; the retained SET
demands publish R22. The public `pietto.sql-emission.v1` envelope is unchanged;
a SET-final column gains `correspondence.set_origin` with the body, column,
kind, quantifier, fold, per-operand input/terminal and the terminal port, and
the independent data-only decoder parses SET units, re-derives their
realizations and denominators, and validates that provenance.

## Manifest denominator

60 cases and 181 public documents per target, from 50 cases and 141 documents at
Slice10. Ten new cases contribute 40 variants and the two `O_named_later` SET
variants migrate to `VERIFIED`. Four additive relations carry the witnesses:
`phase66 set left é` (key = 1, 1, NULL; value = 1, 2, NULL), `phase66 set right é`
(key = 1, NULL, NULL), `phase66 set sextet é` (1, 1, 1, NULL, NULL, NULL) and
`phase66 set outer é` (1, 1, 2, NULL). Every oracle is written by hand from those
rows and the published multiplicity laws.

| Target | VERIFIED | INPUT_REJECTED | BLOCKED |
| --- | ---: | ---: | ---: |
| PostgreSQL | 150 | 3 | 28 |
| MySQL | 147 | 3 | 31 |

## R03 and R11/C09 closure

Slice11 executes the last members. Upon successful local dual-target acceptance
and natural exact-head CI:

```
R03 outstanding joint execution: none.
R11/C09 outstanding membership differences: none.
```

## Changed-path and lifecycle lock

The grammar, generated parser, public legacy SQL emitter, `pyproject.toml`,
`uv.lock`, target pins, Docker configuration, `.github/workflows/ci.yml`,
`scripts/validate.py`, upstream completion and the package version are
untouched. No skip, xfail or marker filter was added, no target case was
removed, and the Interlude IV `NO_GAIN` closure and its four-worker ceiling
stand. Slice11 completion is not Phase66 completion.

```
Phase65 = COMPLETED
Phase66 = ACTIVE
Phase66 Slices1-11 = COMPLETED/PUBLISHED
Phase66 Slice12 = NEXT / NOT IMPLEMENTED
N66 = 16
```
