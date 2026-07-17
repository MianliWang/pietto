# Phase 52 Expression Stage And Clause Capability Facts v1

## Status And Authority

This document is the Phase 52 Slice 6 private expression-stage and clause
capability-fact contract. It records descriptive facts from the current
single-file compiler. These facts are not compiler authority, do not replace
procedural semantic checks, and cannot accept or reject a Pietto program.

The inventory contains exactly 18 unique `CapabilityFact` values: seven
expression-stage facts followed by eleven clause-capability facts. The clause
facts split into five supported facts and six explicitly unsupported facts.
All expression-stage facts and eight clause facts have a
`CapabilityDispositionKind.NONE` disposition. Three explicitly unsupported
clause facts have an exact `POST60_ADVANCED_AGGREGATION_GROUPING` deferred
owner and reason.

Aggregate signatures, overloads, argument/result algebra, null elimination,
and empty-input behavior belong to Phase 52 Slice 7. Window functions belong
to Phase 53. Slice 6 records only current stage and clause posture and does not
complete either of those future families. Phase 52 remains active and
incomplete.

## Private Context Module And Ordering

`src/pietto/semantic/capability_contexts.py` owns three immutable tuples:

```text
_EXPRESSION_STAGE_FACTS
_CLAUSE_CAPABILITY_FACTS
_CAPABILITY_CONTEXT_FACTS
```

`_CAPABILITY_CONTEXT_FACTS` combines the first two tuples in exactly that
family order. Fact order within each tuple and evidence order within each fact
are significant.

The module has `__all__: tuple[str, ...] = ()` and imports only
`collections.abc` and the private `capability_facts.py` carriers. It does not
import `capability_lookup.py`. Its freezer requires exact `CapabilityFact`
values, rejects completely identical duplicate facts, and preserves distinct
same-key facts in input order. It does not sort facts or select a winner.

`stage_clause_lookup_inputs` is a pure private helper with this exact shape:

```python
def stage_clause_lookup_inputs(
    key: CapabilityKey,
) -> tuple[
    tuple[CapabilityFact, ...],
    bool,
    CapabilityReasonCode | None,
]: ...
```

The helper returns the exact target-family tuple, an exact-key-schema
completeness flag, and an optional unknown reason. It performs no lookup,
normalization, fallback, IO, filesystem scan, cache, registry, environment
access, mutation, or compiler classification.

## Stage Vocabulary And Key Encoding

The expression-stage completeness schema ID is
`expression_stage.single_file_compiler.v1`. Every populated stage key uses:

```text
domain = CapabilityDomain.EXPRESSION_STAGE
subject = one exact seven-subject category atom
operation = observed_stage
operands = (one exact CONSTANT/ROW/GROUP/UNKNOWN atom,)
context = expression
dialect = None
extension = None
```

The exact stage vocabulary is uppercase text in the existing key operands:

- `CONSTANT` means a literal or recognized scalar composition whose recursive
  dependencies are literals only and contain no row, local, or group
  dependency.
- `ROW` means a resolved row/local reference or scalar composition with at
  least one resolved row/local dependency and no aggregate dependency.
- `GROUP` means a direct global or keyed aggregate, an aggregate-dependent
  composition, or a grouped result output reference.
- `WINDOW` is reserved to Phase 53, has no current fact, and is excluded from
  Slice 6 completeness.
- `UNKNOWN` is a source-backed unresolved-reference expression category. It
  is a populated stage fact and is not a Slice 3 lookup `Unknown` result.

`ValueTypeKind.UNKNOWN`, `EffectiveNullability.UNKNOWN`, SQL `NULL`, SQL
three-valued truth `UNKNOWN`, and the absence of a concrete division result
rule are independent dimensions. None automatically selects stage `UNKNOWN`.

The stage schema is complete only for one of the seven exact subjects,
`operation="observed_stage"`, exactly one operand in
`CONSTANT`/`ROW`/`GROUP`/`UNKNOWN`, `context="expression"`, and no dialect or
extension. A known subject with an incorrect current non-window stage claim is
a complete zero match. Window, future-subject, wrong-context,
dialect/extension, malformed-tail, project, and public questions are
incomplete.

## Expression Stage Facts

All seven facts have `CapabilitySupport.SUPPORTED` and a `NONE` disposition
with no owner or reason. Their exact source order is:

| ID | Subject | Operation | Operands | Context |
|---|---|---|---|---|
| ES01 | `literal_expression` | `observed_stage` | `(CONSTANT,)` | `expression` |
| ES02 | `constant_scalar_expression` | `observed_stage` | `(CONSTANT,)` | `expression` |
| ES03 | `resolved_row_reference` | `observed_stage` | `(ROW,)` | `expression` |
| ES04 | `row_scalar_expression` | `observed_stage` | `(ROW,)` | `expression` |
| ES05 | `aggregate_dependent_expression` | `observed_stage` | `(GROUP,)` | `expression` |
| ES06 | `group_output_reference` | `observed_stage` | `(GROUP,)` | `expression` |
| ES07 | `unresolved_reference_expression` | `observed_stage` | `(UNKNOWN,)` | `expression` |

ES01 records every `LiteralExpr` as dependency-constant. A null literal has no
concrete type, recorded by `NULL_LITERAL_NO_CONCRETE_TYPE`, but remains at
`CONSTANT` stage. Its ordered evidence is grammar literal syntax, `LiteralExpr`,
semantic literal inference, the semantic value-type map, `LiteralIR`, literal
IR lowering, the literal semantic test, the Slice 4 literal inventory, and the
Phase 52 expression-stage contract.

ES02 records recognized scalar calls and unary, binary, comparison, between,
and null-test composites with literal-only dependencies as `CONSTANT`. Its
ordered evidence is expression grammar, the six scalar composite AST classes,
`BUILTIN_FUNCTIONS`, recursive semantic inference, the semantic value-type
map, scalar IR classes, scalar lowering, function tests, operator tests, the
operator matrix, and the Phase 52 expression-stage contract.

ES03 records resolved relation fields, qualified fields, callable parameters,
shape fields, admitted row lets, and group-key inputs as `ROW` references. Its
ordered evidence is dotted-name grammar, name AST nodes, semantic row/name
resolution, relation-let inference, row/let semantic models, `FieldRefIR`, name
lowering, bare-field tests, callable-body tests, derive tests, row-let tests,
group-key row-let tests, and the row-level scope contract.

ES04 records a recognized scalar composition with at least one resolved
row/local dependency and no aggregate dependency as `ROW`. Its ordered
evidence is composite grammar and AST classes, builtin catalog, recursive
semantic inference, row-let dependency inference, value/row semantic models,
scalar IR classes and lowering, nested scalar tests, scalar operator tests,
row-let composite tests, the row-level scope contract, and the Phase 52
expression-stage contract.

ES05 records direct global/keyed aggregates and recursively
aggregate-dependent expressions as `GROUP`, independently of whether a
particular clause rejects them. Its ordered evidence is call/composite grammar
and AST, the semantic aggregate catalog and dependency walk, aggregate
projection and grouped-schema procedures, relation schema facts,
`AggregateCallIR`, aggregate lowering, the Phase 52 roadmap, count tests,
grouped schema tests, and the expression-stage contract. This fact does not
enumerate aggregate signatures.

ES06 records only a grouped result-scope selected output reference as `GROUP`.
Its ordered evidence is select/satisfying/order grammar and AST, satisfying and
grouped-order name procedures, satisfying semantic metadata, result-predicate
and order IR, grouped lowering, satisfying aggregate/group-key alias tests,
grouped order tests, the aggregate surface freeze, and the grouped-result
scope contract.

ES07 records unresolved bare/qualified references and unknown calls as a
source-backed `UNKNOWN` stage. Its semantic procedure/model evidence carries
`UNRESOLVED_EXPRESSION`; no IR or backend support is claimed. Its ordered
evidence is dotted-name/call grammar and AST, unknown semantic procedures,
`ValueTypeKind.UNKNOWN`, unknown-field and unknown-function tests, the bounded
reason-code contract, and the Phase 52 conflict/stage contract.

## Clause Key Encoding And Completeness

The clause completeness schema ID is
`clause.single_file_compiler.admissibility.v1`. Every clause key uses:

```text
domain = CapabilityDomain.CLAUSE
subject = where | group_by | satisfying | order_by
operation = admit
operands = (
    clause_required_stage,
    required_result_posture,
    expression_shape,
    name_scope,
    alias_policy,
)
context = one exact compiler clause context
dialect = None
extension = None
```

Clause-required stage is the clause evaluation phase, not the observed stage
of every expression leaf. For example, literal `true` is an ES01 `CONSTANT`
expression while `where` executes at `ROW` phase.

The closed position-specific atoms are:

```text
stage:
  ROW, GROUP

result:
  Bool_when_known, Bool, no_result_type_constraint

shape:
  current_nonaggregate_expression
  direct_input_field_or_direct_field_row_let
  bounded_result_predicate
  bare_selected_output_or_matching_group_key_row_let
  aggregate_dependent_expression
  non_field_group_key
  global_aggregate_postfilter
  non_bare_or_unselected_grouped_order_expression

scope:
  input_fields_and_row_lets
  selected_group_key_and_aggregate_outputs
  no_group_aggregate_outputs
  unselected_raw_input_fields
  grouped_input_or_unselected_outputs

alias policy:
  select_output_aliases_forbidden
  selected_output_names_with_matching_aggregate_let_exception
  selected_output_names_with_matching_group_key_let_exception
  selected_output_aliases_do_not_create_satisfying_scope
  selected_output_names_required
```

The six complete subject/context pairs are:

```text
where/pre_group_filter
group_by/group_key
satisfying/grouped_result_filter
satisfying/no_group_result_filter
order_by/input_order
order_by/grouped_result_order
```

`Bool_when_known` is exact for `where`: current predicate checking rejects a
known non-Bool but emits no predicate diagnostic for a missing or unknown
value type. `Bool` is exact for bounded grouped satisfying predicates. Group
keys and both order modes have no independent result-type/orderability
consumer and therefore use `no_result_type_constraint`.

A key is complete only when its pair is in the six-pair set, it has exactly
five operands from the corresponding position vocabularies, its required
stage is `ROW` or `GROUP`, and it has no dialect or extension. A complete
closed-atom combination need not be populated.

## Where And Group By Clause Facts

The exact `where` and `group_by` facts are:

| ID | Support / disposition | Exact key tail |
|---|---|---|
| C01 | `SUPPORTED / NONE` | `where/admit/(ROW,Bool_when_known,current_nonaggregate_expression,input_fields_and_row_lets,select_output_aliases_forbidden)/pre_group_filter` |
| C02 | `SUPPORTED / NONE` | `group_by/admit/(ROW,no_result_type_constraint,direct_input_field_or_direct_field_row_let,input_fields_and_row_lets,select_output_aliases_forbidden)/group_key` |
| C06 | `EXPLICITLY_UNSUPPORTED / NONE` | `where/admit/(ROW,Bool_when_known,aggregate_dependent_expression,input_fields_and_row_lets,select_output_aliases_forbidden)/pre_group_filter` |
| C07 | `EXPLICITLY_UNSUPPORTED / DEFERRED` | `group_by/admit/(ROW,no_result_type_constraint,non_field_group_key,input_fields_and_row_lets,select_output_aliases_forbidden)/group_key` |

C01 is supported because current nonaggregate row-scope expressions are
admitted and only known non-Bool results fail. Its evidence proceeds from
where grammar and AST through expression/predicate semantic procedures,
division and null-literal reason evidence, semantic models, filter IR and
lowering, PostgreSQL then private MySQL rendering, roadmap, where/qualified
field/row-let tests, and the Bool predicate contract.

C02 is supported because grammar and resolution close current group keys to a
direct input field or a row let resolving to a direct field. Its evidence
proceeds from group grammar/AST through group-key resolution, row model, IR and
lowering, PostgreSQL then private MySQL validation, project corroboration,
roadmap, grouped-schema and row-let tests, and the Phase 43 scope contract.

C06 is explicitly unsupported because the semantic aggregate dependency check
affirmatively rejects aggregate-dependent `where` expressions before IR or
backend lowering. Its disposition is `NONE`; this current rejection does not
invent a future owner.

C07 is explicitly unsupported and deferred to
`POST60_ADVANCED_AGGREGATION_GROUPING`, with exact reason
`broad expression group keys require separate authorization`. Current grammar
and resolution close the shape, while broad expression group keys already
have that exact roadmap owner.

## Satisfying Clause Facts

The exact `satisfying` facts are:

| ID | Support / disposition | Exact key tail |
|---|---|---|
| C03 | `SUPPORTED / NONE` | `satisfying/admit/(GROUP,Bool,bounded_result_predicate,selected_group_key_and_aggregate_outputs,selected_output_names_with_matching_aggregate_let_exception)/grouped_result_filter` |
| C08 | `EXPLICITLY_UNSUPPORTED / DEFERRED` | `satisfying/admit/(GROUP,Bool,global_aggregate_postfilter,no_group_aggregate_outputs,selected_output_aliases_do_not_create_satisfying_scope)/no_group_result_filter` |
| C09 | `EXPLICITLY_UNSUPPORTED / NONE` | `satisfying/admit/(GROUP,Bool,bounded_result_predicate,unselected_raw_input_fields,selected_output_names_required)/grouped_result_filter` |

C03 is supported only for the bounded GROUP BY result predicate. Its scope is
selected group-key and aggregate outputs plus the exact matching
aggregate-let exception. Ordered evidence proceeds from satisfying grammar and
AST through the satisfying procedure/model, result-predicate IR and lowering,
PostgreSQL then private MySQL HAVING rendering, project corroboration,
roadmap, aggregate/group-key alias and aggregate-let tests, and the aggregate
surface and Phase 43 contracts.

C08 records the affirmative current rejection of no-GROUP satisfying and
global-aggregate post-filtering. It is deferred to the existing
`POST60_ADVANCED_AGGREGATION_GROUPING` aggregate-filter owner with exact reason
`global aggregate post-filtering requires separate authorization`. Reusing
that owner creates no new owner, transfer, or implementation authorization.
No IR/backend support fact is claimed.

C09 records the affirmative rejection of an unselected raw input reference in
grouped satisfying. An unaliased selected group-key name is still a valid
selected output. Its disposition is `NONE`.

## Order By Clause Facts

The exact `order_by` facts are:

| ID | Support / disposition | Exact key tail |
|---|---|---|
| C04 | `SUPPORTED / NONE` | `order_by/admit/(ROW,no_result_type_constraint,current_nonaggregate_expression,input_fields_and_row_lets,select_output_aliases_forbidden)/input_order` |
| C05 | `SUPPORTED / NONE` | `order_by/admit/(GROUP,no_result_type_constraint,bare_selected_output_or_matching_group_key_row_let,selected_group_key_and_aggregate_outputs,selected_output_names_with_matching_group_key_let_exception)/grouped_result_order` |
| C10 | `EXPLICITLY_UNSUPPORTED / NONE` | `order_by/admit/(ROW,no_result_type_constraint,aggregate_dependent_expression,input_fields_and_row_lets,select_output_aliases_forbidden)/input_order` |
| C11 | `EXPLICITLY_UNSUPPORTED / DEFERRED` | `order_by/admit/(GROUP,no_result_type_constraint,non_bare_or_unselected_grouped_order_expression,grouped_input_or_unselected_outputs,selected_output_names_required)/grouped_result_order` |

C04 is supported because no-GROUP input ordering reuses row expression typing
and has no independent result-type or orderability check. Select output aliases
do not create its name scope. Evidence proceeds from order grammar/AST through
row inference/model, order IR and lowering, PostgreSQL then private MySQL
rendering, roadmap, input-order/alias/qualified-field/row-let tests, and the
order and row-let contracts.

C05 is supported only for a bare supported selected group-key or aggregate
output, or a row let matching a selected group key. Evidence proceeds through
grouped order semantic/model/IR layers, PostgreSQL then private MySQL
validation, project corroboration, roadmap, grouped-order and row-let tests,
and the grouped-order/Phase 43 contracts.

C10 is explicitly unsupported because current no-GROUP input ordering rejects
aggregate-dependent expressions before IR/backend lowering. Its disposition is
`NONE`.

C11 is explicitly unsupported and deferred to
`POST60_ADVANCED_AGGREGATION_GROUPING`, with exact reason
`broad grouped result ordering requires separate authorization`. Current
grouped ordering rejects non-bare or unselected forms; broader ordering remains
separately owned.

## Unknown Window Aggregate And Omission Policy

`WINDOW` exists only as reserved vocabulary. Slice 6 contains no window fact,
and window is excluded from both completeness schemas. Every
WINDOW/OVER/PARTITION/frame/named-window/QUALIFY question is incomplete and
returns `Unknown(NOT_EVIDENCED)`, never `Absent` or an invented explicitly
unsupported fact. Phase 53 owns the first window-function contract, and
`POST60_ADVANCED_WINDOWS` retains later advanced windows.

Slice 6 may state that an aggregate-dependent expression is `GROUP` and may
record its current clause admission or rejection. It does not enumerate
aggregate names, arities, arguments, result types, result nullability,
empty-input behavior, null elimination, algebra, result role, overloads, or
backend portability. Those facts remain exclusively Phase 52 Slice 7.

The following audited contexts are intentionally omitted from the populated
clause family:

- select/output, whose aggregate parts belong to Slice 7;
- relation `let`, which is a binding and scope mechanism;
- `limit`, which is a special static-integer validator;
- `from`, which contains no expression;
- shape check and index predicates;
- type/field `ensure`, which has no current semantic-stage authority;
- field derive, callable body, connector arguments, and source metadata;
- pure grouping and grouped projection-output rules;
- projection aliases as expression leaves;
- aggregate signatures and algebra;
- all window questions;
- CASE, casts, runtime parameters, user-facing HAVING, and QUALIFY; and
- dialect, extension, project, and public variants.

Every omitted candidate is schema-incomplete. Their zero matches are
`Unknown`, never inferred `Absent` or an unsupported fact.

## Four-result Lookup And Conflict Preservation

Focused consumers pass the three helper outputs verbatim to Slice 3
`lookup_capability`:

- all exact 18 populated keys produce `Found`;
- a complete-schema zero match produces `Absent`, which does not mean
  unsupported;
- an incomplete question produces `Unknown(NOT_EVIDENCED)`; and
- distinct same-key facts produce ordered
  `Conflict(CONFLICTING_EVIDENCE)` with no winner and no evidence loss.

The ES07 key with `operands=("UNKNOWN",)` produces `Found`; it is not a lookup
`Unknown`. The helper always returns `unknown_reason=None`, allowing the Slice
3 default `NOT_EVIDENCED` reason for incomplete questions.

The active eight-item fail-closed conflict ledger remains unchanged:

1. `count(alias/Shape)`.
2. Semantic `LIKE` versus PostgreSQL/private MySQL lowering.
3. `matches(Text, Text)` across PostgreSQL and private MySQL.
4. Non-Decimal type arguments parsed but not generally consumed semantically.
5. Division `/` without a concrete semantic result rule.
6. Null literal versus unresolved-expression unknown carriers.
7. Generic comparison outer Bool UNKNOWN versus pairwise compatibility.
8. No-GROUP global aggregate post-filtering versus satisfying's GROUP BY
   requirement.

Slice 6 also preserves aggregate row/group tension, generic typing versus
bounded satisfying, exact Phase 43 let exceptions, grouped-output narrowing,
backend renderability versus semantic admission, project/compiler scope
differences, project roles versus stages, and reserved-window readiness. No
source class receives winner precedence.

## Evidence Ordering And Authority Boundaries

Each evidence entry uses the exact ordered fields
`source`, `source_path`, `source_reference`, `reason`, `dialect`, `backend`, and
`extension`. The canonical source-class order is:

1. `GRAMMAR_AST`
2. `SEMANTIC_CATALOG`
3. `SEMANTIC_PROCEDURE`
4. `SEMANTIC_MODEL`
5. `IR`
6. PostgreSQL `BACKEND`
7. private MySQL `BACKEND`
8. `PROJECT`
9. `PUBLIC`
10. `ROADMAP`
11. `TEST`
12. `SPEC`

Absent layers are omitted. Every evidence entry has `extension=None`.
Backend entries alone carry exact dialect/backend scope.
PostgreSQL evidence precedes private MySQL evidence. Project and public entries are corroborating
scope evidence and never single-file compiler authority. Roadmap evidence
records disposition, not compiler acceptance. No backend winner or semantic
override is selected. A genuine same-key disagreement remains distinct facts
and resolves as `Conflict`.

The current semantic procedures in `expressions.py`, `predicate_checks.py`,
`aggregates.py`, `let_bindings.py`, `group_by.py`, and `satisfying.py` are the
single-file clause authority. Semantic models and IR preserve accepted facts,
and SQL renderers consume accepted IR; neither downstream layer can establish
semantic admission. The private `_project` grouped-clause read model is not
single-file compiler authority.

## Privacy Static Compatibility And Validation Locks

The context module defines no new class, enum, domain, carrier field, reason
code, diagnostic, registry, cache, environment lookup, filesystem scan, or
public export. It remains unconsumed by analyzer, catalog, semantic
procedures/model, IR, SQL, `_project`, CLI, JSON, metadata serializers,
runtime, and database code. Focused tests access its facts only through private
module attributes.

The prior private modules remain byte-identical:

```text
src/pietto/semantic/capability_facts.py
src/pietto/semantic/capability_lookup.py
src/pietto/semantic/capability_inventory.py
src/pietto/semantic/capability_signatures.py
```

Slice 6 changes no grammar, generated artifact, AST, parser, accepted syntax,
semantic behavior, diagnostic, type/nullability inference, IR, SQL byte,
project/public metadata, CLI/JSON output, dependency, lockfile, workflow,
fixture, golden, example, runtime, or database behavior. Validation must use
the exact Gate 2 allowlist and the planned offline lock, Ruff, production and
test Pyright, Tier 1, Tier 2, and `git diff --check` gates. It must not run an
unfiltered local pytest suite.

## Slice Ownership Lifecycle And Release Boundary

This specification is private Slice 6 descriptive evidence only. It creates no
public API or compiler behavior. Slice 7 retains aggregate signatures and
algebra. Phase 53 retains window functions. The existing conflict ledger and
later POST60 owners remain unchanged and receive no implementation authority
from this slice.

Package version remains `0.1.0`. Slice 6 performs no version bump, tag,
release, publish, upload, signing, or attestation operation. Gate 2 performs no
stage, commit, push, or CI operation. Gate 3, if separately authorized after
all evidence passes, uses the exact commit subject
`Add Phase 52 private expression stage and clause facts` and observes only the
natural push CI run.

No staging, commit, push, tag, release, publication, signing, or attestation.

Phase 52 remains active and incomplete after Slice 6. Completion of this slice
does not authorize Slice 7, Phase 53, POST60 grouping, or any public/runtime
behavior.
