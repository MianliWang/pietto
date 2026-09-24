# Phase66 Pre-Slice16 Completion Corrective Closure v1

## Authority and lifecycle

This contract records `PHASE66_UNNUMBERED_PRE_SLICE16_COMPLETION_CORRECTIVE_CLOSURE`, an
unnumbered corrective publication authorized by the user after the first Slice16
completion-audit attempt ended in HOLD. It is not a numbered Slice: it is neither Slice16
nor Slice17, N66 remains 16, and it starts no later phase. The audit found two
Phase66-owned product defects and five missing promised witnesses of the
[route lock](phase66-dialect-sql-emission-product-phase-initiation-gate-route-lock-v1.md).
This closure repairs G1 and G3 in production, closes G2, G4, G5 and G6 with evidence only,
and preserves every promise of the route lock unchanged. Its first full MySQL run then found
G7, a window value result published with its input's width; the user's continuation
decisions add the G7 repair, the PostgreSQL repair P1 of the same family, and one new
explicit MySQL boundary B1, all recorded below.

Phase66 remains `ACTIVE`; Slices1–15 remain `COMPLETED / PUBLISHED`; Slice16 remains
`NEXT / NOT IMPLEMENTED`, and its prior attempt stays HOLD and needs a new audit bound to
this publication. The closure is `COMPLETED / PUBLISHED` only upon successful natural
exact-head CI on its ordinary commit with Python 3.12, Python 3.13, Target postgres,
Target mysql and Target conformance aggregate, and strictly verified fresh raw receipts.
The package and CLI stay 0.1.0.

## G1: a named declaration is not a use-local specification

Before this closure every use of one named window declaration reused the generated
definition built from the declaration's first use. A use that extended the declaration,
for example `row_number() window base: partition by: id` beside a plain
`rank() window base`, was emitted as `OVER "w0"` without its partition while the artifact
stayed VERIFIED; with the extended use first, the plain use was wrongly partitioned.

The complete realized use-local specification is now the lowering authority. The builder
shares one generated `WINDOW` definition only for the same retained declaration and the
same complete specification: the same partition reads in order, the same order reads with
equal direction and NULL posture, and the same frame unit, bound kinds, exact offsets and
exclusion. Different specifications get their own complete definitions `w0`, `w1`, … in
encounter order; distinct declarations never merge, and identical uses keep their existing
bytes. The renderer is unchanged: every `OVER <symbol>` now names the right definition.

The independent verifier re-derives each occurrence's complete specification from its
retained policy and the established pre-window ports, requires exactly one definition to
carry the occurrence's symbol, to name its declaration and to equal that specification,
and requires every definition to be referenced in its exact generated order and spelling.
A swapped definition, one definition shared by incompatible uses and a first-use-collapse
constructor fault each meet `plan_ast_correspondence` (`PIE-B1008` for the fault).

## G3: R15-INT-OFFSET-V1

The user decision R15-INT-OFFSET-V1 concretizes R15's exact arithmetic premise; it adds no
rule number, frame type or key type. With I64 = [-9223372036854775808,
9223372036854775807]:

- every finite offset of ROWS, PostgreSQL GROUPS and integer offset RANGE is an exact
  non-negative integer `0 <= n <= 9223372036854775807`. ROWS and GROUPS offsets count
  rows or peer groups and never depend on the ORDER key's storage, domain or the fixture
  row count; MySQL GROUPS stays approved non-support;
- an offset RANGE keeps its single non-null signed Int ORDER key. The key's retained exact
  domain [L, U] must lie inside its reviewed signed storage, and for each actual finite
  endpoint the translated interval — [L−n, U−n] for ASC PRECEDING and DESC FOLLOWING,
  [L+n, U+n] for ASC FOLLOWING and DESC PRECEDING — must lie inside I64. The threshold is
  compared with the key, never stored in it, so it may be wider than the key's own
  storage: a SMALLINT key over [0, 99] admits `range between 40000 preceding`.

| Condition | Blocker |
| --- | --- |
| no exact static non-negative integer offset (unchanged) | `PIE-B1004` `window_frame_offset_evidence_missing` |
| exact offset above 9223372036854775807 | `PIE-B1002` `window_frame_offset_out_of_signed64_range` |
| no usable exact integer key domain or reviewed signed storage | `PIE-B1004` `window_range_arithmetic_evidence_missing` |
| key domain outside its reviewed storage | `PIE-B1002` `window_range_key_domain_out_of_storage_range` |
| a translated endpoint interval outside I64 | `PIE-B1002` `window_range_boundary_out_of_signed64_range` |

Existing target unit and exclusion refusals are checked first, so MySQL GROUPS keeps its
own blocker. The five offsets reported by the HOLD (`100000000000000000000` and
`18446744073709551616` RANGE, `100000000000000000000` and `9223372036854775808` ROWS) now
refuse their representation, and `9223372036854775807` RANGE over the published key domain
±9007199254740993 refuses its translated boundary. No server error is claimed for them.

Each use keeps two new generated R15 requirements directly after its
`window_specification`: `window_frame_offset_domain` when its frame has a finite offset
(premises: none; the static bounds and reviewed target rules are its roots), and
`window_range_arithmetic` for such a RANGE frame (premises: the statement
`operator_environment`, with the key domain carried by the scanned field's source
representation). The builder, the runtime verifier, the private pure checker and the public
decoder enumerate them independently; the verifier re-derives offsets and intervals from the
retained policy with its own arithmetic, and the pure checker and decoder check the
serialized offsets and key domains data-only. Pure consistency is not proof that a source
domain holds in a database.

## G7, P and B: window value result representation

Before this closure a `lag`, `lead`, `first_value`, `last_value` or `nth_value` result
copied its value argument's storage and interval. That was not what either target returns,
and three wrong successes of one family were disclosed: G7, MySQL returns a signed integer
window value in its own materialized width; P, PostgreSQL's three-argument `lag`/`lead` is
`anycompatible`, so an integer default joins the result type; and B, MySQL returns a Bool
value's window result as an INT. The result owner now derives each result from its value
carrier and default, and the runtime verifier, the private pure checker and the public
decoder re-derive it independently.

**Interval.** An Int result keeps its value's interval [L, U]; a non-null integer default
`d` makes it the least enclosure [min(L, d), max(U, d)], which encloses the union and does
not claim that intermediate integers occur. An omitted or NULL default adds no value, and
nullability stays the retained semantic policy. The enclosure must fit the chosen storage
(`PIE-B1002` `window_value_domain_out_of_storage_range` otherwise); a default outside signed64
is `PIE-B1002` `window_default_integer_out_of_signed64_range` on both targets.

**R14-PG-NAVIGATION-RESULT-V1.** On PostgreSQL the value carrier's own `pg_int2 < pg_int4 <
pg_int8` width is kept, except that an uncast integer default of `lag`/`lead` takes its own
literal type, int4 inside signed32 and int8 beyond, and the wider of the two is published.
The offset never takes part, and first/last/nth value, ranking, aggregation and SET widths
are untouched. `pg_int2` with an omitted or NULL default stays `pg_int2`; with `0` or
`100000` it is `pg_int4`; `pg_int4` with `2147483647` stays `pg_int4` and with `2147483648`
is `pg_int8`; `pg_int8` with `0` stays `pg_int8`. Each of these, and the carried and
two-window-stage shapes, was observed natively by one focused PostgreSQL command over
generated SQL, and `pg_int2` with an int4 default again by the full manifest. Source basis: PostgreSQL REL_18_6
`pg_proc.dat` (three-argument `lag`/`lead` `anycompatible`), `parse_node.c` (integer literal
type) and `parse_coerce.c` (`select_common_type_from_oids`).

**R15-MYSQL-WINDOW-RESULT-V1.** MySQL materializes a signed integer window value result as
INT below ten display characters and as BIGINT from ten (`sql_tmp_table.cc`,
`create_tmp_field_from_item`). The characters are the carrier column's field-class display,
SMALLINT 6, INT 11 and BIGINT 20, or for a `lag`/`lead` default of d digits d + 1, the sign
place `Item_int::set_max_size` adds. So SMALLINT publishes `my_int` with an omitted, NULL or
at most eight-digit default and `my_bigint` from nine digits, while INT and BIGINT publish
`my_bigint`. Only two carrier classes are reviewed: a source field of `my_smallint`,
`my_int` or `my_bigint`, and an earlier window result, each through any exact carry. A carry
repeats no computation and keeps its width, while a second window re-evaluates the carried
INT as BIGINT. Any other MySQL Int carrier, such as a literal, an aggregate result or a
computed value that a merged CTE may hand to the window as an expression, is `PIE-B1002`
`mysql_window_integer_result_origin_not_supported_in_phase66`. Text, Decimal and Float
results keep their carrier's representation.

| MySQL mapping | Scope |
| --- | --- |
| SMALLINT/INT/BIGINT source column, all five functions, raw SELECT and generated CTE shape | observed natively (LONG / LONGLONG / LONGLONG) |
| SMALLINT with a 1- or 6-digit default; with an 11-digit default | observed natively (LONG; LONGLONG) |
| SMALLINT with an 8-digit versus a 9- or 10-digit default | observed natively by the focused MySQL command over generated SQL (LONG; LONGLONG), and the 9-digit side again by the full-manifest `high` column |
| window result carried through a table stage; a second window over it | observed natively (LONG; LONGLONG) |
| a window-result BIGINT carrier | source only (the field class of an observed BIGINT column) |

**B1: explicit MySQL Bool window boundary.** For MySQL, a reachable `first_value`,
`last_value`, `nth_value`, `lag` or `lead` whose value has logical type Bool, from a source
or any admitted carrier, is `PIE-B1002`
`mysql_bool_window_result_representation_not_supported_in_phase66`, bound to that window use
after every earlier check. It is a new support decision: B was an existing wrong success in
which `my_bool01` was published for an INT 0/1/NULL result, and it was not always a boundary.
No storage tag, schema field, CAST or Int reinterpretation is added. PostgreSQL, MySQL Bool
scans, fixed Bool values, Boolean expressions and integer window values are unchanged.
Accurate MySQL Bool window results remain a separate future MySQL-depth decision.

The public decoder gained the two consumer paths the rule needs. A window result carried
through a named body is now checked through its `window_transport` provenance rather than
being taken for an aggregate transport. A window result projected by a non-final body now
advances the window projection identity, so a later body's window projection keeps its own
number. Both are checked against the generated carried and two-window-stage documents,
together with wrong-width, wrong-producer and wrong-port forgeries.

## Evidence closures

| Finding | Promise | Witness |
| --- | --- | --- |
| G2 R09/C14 | PostgreSQL FULL over [1,2,NULL] and [2,3,NULL] | `V_join_full/null_keys`: `"phase66 set left é".value` FULL JOIN a producer over `"phase66 agg é"` where rid > 11; BAG (2,2), (1,NULL), (NULL,3) and (NULL,NULL) twice; MySQL keeps `mysql_full_join_approved_non_support`. Offline: a non-operation ON root, inequality, `!=`, an extra ON term, OR, same-side, non-direct operand and non-reviewed Int pairing each keep their exact detail; `full_join_requires_cross_input_equality` stays a defensive branch the AST builder never reaches. |
| G4 R16 | nullable lag / first_value under the admitted identity | `A_window_named/use_local` over nullable `value`; `respect nulls` and `from first` spellings emit byte-identical SQL to the defaults, so the executed default is their result; the rows distinguish ignoring NULLs. IGNORE NULLS and FROM LAST keep their blockers. |
| G5 C06 | physical row domains of inheritance, views and partitions | new case `G_scan_row_domains`: PostgreSQL parent + INHERITS child repeating key 1 (MySQL: a family view over two keyed tables), a parent-only view and a SMALLINT LIST-partitioned root, each declared by its own relation; no ONLY and no uniqueness inferred. A false or missing `row_domain_matches` stays `PIE-B1001` `row_domain_matches_declaration_required`. |
| G6 R04/R21 | BIND_SAFE never binds a structural LIMIT | `G_scan_row_domains/inherited_parent` under BIND_SAFE: the data literal `0` is one fixed Int slot and native use, `LIMIT 5` stays a literal token and is absent from fixed values; LIMIT 5 exceeds the three rows, so truncation stays `O_result_limit`'s claim. |
| G1 / G3 | use-local windows; R15-INT-OFFSET-V1 | `A_window_named/use_local`: one declaration used plainly first (`lag`) and extended by a frame second (`first_value` over one preceding row), executed on both targets; a first-use collapse would give the extended use the default frame. The other encounter order, a PARTITION extension, equal-content declarations and an EXCLUDE difference are offline witnesses, and the inherited `A_window_named/shared` keeps identical uses sharing one definition. `G_scan_row_domains/partitioned_root` executes an offset wider than its SMALLINT key; the inherited `A_window_frame/range` keeps an ordinary finite RANGE on both targets. |
| G7 / P | window value widths and default intervals | `G_scan_row_domains/partitioned_root` also executes `high = lag(id, 1, 999999999)`: PostgreSQL `low` int2 and `high` int4 ([0, 999999999]); MySQL `low` INT and `high` BIGINT, with its rows unchanged except the new column. The full width matrix, the carried and two-window-stage chains and their forgeries are offline tests; one bounded focused command per target observes the default boundary, the PostgreSQL defaults and both propagations natively. |

The fixture relations are created by the facility's owned target containers after every
inherited relation, before the query role's grants, and are removed with the containers.
No inherited relation, row, case or variant changes.

## Denominator and receipts

The target corpus is 63 cases / 195 public documents per target (189 API and 6 console
documents): PostgreSQL 162 VERIFIED / 4 INPUT_REJECTED / 29 BLOCKED; MySQL 158 VERIFIED / 4
INPUT_REJECTED / 33 BLOCKED. The receipt format stays `pietto.target-conformance-receipt.v2`
with the approved ceiling 33 MiB = 34,603,008 bytes; the witnesses declare only the fields
they read so that every required document is carried in full inside that ceiling.

## Controlling references

- [Phase66 route lock](phase66-dialect-sql-emission-product-phase-initiation-gate-route-lock-v1.md)
- [Slice2 isolated target facility](phase66-isolated-target-conformance-facility-v1.md)
- [Slice9 window contract](phase66-slice9-admitted-windows-named-windows-frames-qualify-emission-v1.md)
- [Slice15 conformance contract](phase66-slice15-expanded-target-differential-metamorphic-conformance-v1.md)
