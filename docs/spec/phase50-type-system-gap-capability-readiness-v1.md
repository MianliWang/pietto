# Phase 50 Slice 4 Type-System Gap And Capability Readiness v1

## Purpose And Slice Identity

Phase 50 Slice 4 is **Type-System Gap And Capability Readiness**. It is
docs/spec/static-audit-only readiness work. It reconciles current type-system
facts and gaps without changing what Pietto parses, accepts, rejects, stores,
lowers, renders, or exposes.

The trusted baseline is `main` at
`7bd50022859a5e3d202c26d67bed1a723388048a`, subject
`Add Phase 50 aggregate grouped schema readiness`, with local `origin/main` at
the same commit. Phase 50 Slice 3 completed at that commit after documented
natural CI run `29082580976`, workflow/event `CI / push`, completed/success,
with an exact `headSha` match.

Slice 4 implements no compiler or runtime behavior.

Slice 4 is not complete before successful Gate 3. Its completion requires a
separately authorized commit, push, and exact natural push-CI success. Slice 4
does not start Slice 5 or Phase 52. Phase 50 remains in progress, Slices 5
through 11 remain pending, and Phase 52 remains unstarted.

## Authority And Evidence Hierarchy

Current production source is authoritative for actual accepted, rejected,
stored, lowered, and exposed behavior. Current focused behavior tests and
completion audits corroborate diagnostics and compatibility boundaries.
Completed Phase 29-49 contracts are historical design evidence, with later
completed work superseding earlier risk descriptions where explicitly stated.
The Phase 50 plan, Slice 1 scope lock, Slice 2 inventory, and Slice 3 readiness
contract control current Phase 50 ownership and non-authorization.

Repository-local Gate evidence documents completed execution but is not a
runtime dependency and is not repository policy. This contract depends on no
parent Git object, network state, GitHub query, or temporary evidence file.

When a historical description and current source differ, current source is
recorded first and the historical posture remains identified as history. Every
implementation, public schema, or later phase requires separate authorization.
No production capability API is designed by Slice 4.

## Canonical Type Inventory

The current builtin registry contains exactly 11 names, in source order:

1. `Any`
2. `Bool`
3. `Bytes`
4. `Date`
5. `Decimal`
6. `Float`
7. `Int`
8. `Json`
9. `Text`
10. `Timestamp`
11. `UUID`

`Enum` is not a builtin. It is declaration-backed semantic/IR metadata using
`TypeKind.ENUM` and `TypeKindIR.ENUM`. Type aliases retain their declared
identity and canonical expansion. Shapes are schema/type definitions, not
scalar builtin names.

`UNKNOWN` is a sentinel and non-concrete state, not a source scalar type.
`Null` is not a canonical scalar type; the null literal has no concrete
canonical type fact. DateTime, Time, and Interval are not current builtin
names. Money, Currency, domains, native database types, and
extension-provided types are not current builtin identities. Slice 4 adds no
twelfth builtin and renames no identity.

## Classification Vocabulary

Phase 50 uses exactly these inventory/readiness classifications:

- `IMPLEMENTED_STABLE`
- `IMPLEMENTED_LIMITED`
- `PRIVATE_FOUNDATION`
- `READINESS_CONTRACT_ONLY`
- `EXPLICITLY_DEFERRED`
- `OUT_OF_SCOPE`
- `NOT_EVIDENCED`

They are inventory/readiness classifications only. They do not create a
production enum, JSON schema, manifest field, or Python API.

They do not replace or reinterpret existing public Semantic Metadata Artifact
`support_posture` values, including `current`, `limited_frozen`,
`deferred_builtin`, `metadata_only`, and `unknown`. Slice 4 changes no public
metadata vocabulary and introduces no public classification schema.

## Layer-by-layer Support Matrix

Identity/resolution, declaration, literal, projection/reference,
operator/scalar-function behavior, aggregate behavior, semantic/IR carrier,
private project carrier, public metadata, backend expression lowering, and
native database mapping are independent layers. A type is not globally
implemented merely because it resolves.

| Identity | Resolution / declaration | Literal | Projection / reference | Operator / scalar call | Aggregate | Semantic / IR | Private project | Public metadata | Backend expression lowering | Native mapping |
|---|---|---|---|---|---|---|---|---|---|---|
| `Any` | builtin | none | generic bounded path | no dynamic-typing contract | rejected where unsupported | logical identity | generic identity only | `current` remains existing posture | accepted forms only | none |
| `Bool` | builtin | `true`, `false` | current | `and`/`or`, generic comparison | direct count/count_distinct | logical identity | builtin row fact | `current` | accepted expressions | none |
| `Bytes` | builtin | none | current generic path | risky shared path, no stable special contract | direct count only | logical identity | builtin row fact | `deferred_builtin` | direct-count form | none |
| `Date` | builtin | no typed literal | current | generic comparison only | count/count_distinct/min/max direct | logical identity | builtin row fact | `current` | accepted forms only | none |
| `Decimal` | builtin; optional validated `(p,s)` | none | current | bounded `+`/`-` | bounded count/count_distinct/sum/avg/min/max | logical identity; private `(p,s)` fact | logical row fact only | public precision absent | logical accepted forms | no `(p,s)` guarantee |
| `Float` | builtin | numeric | current | unary numeric and bounded arithmetic | bounded count/distinct/sum/avg/min/max | logical identity | builtin row fact | `current` | accepted expressions | none |
| `Int` | builtin | numeric | current | unary numeric and bounded arithmetic | bounded count/distinct/sum/avg/min/max | logical identity | builtin row fact | `current` | accepted expressions | none |
| `Json` | builtin | no Json literal | current generic path | risky shared path, no path/operator contract | direct count only | logical identity | builtin row fact | `deferred_builtin` | direct-count form | none |
| `Text` | builtin | string | current | lower/trim/len/matches; no concatenation | count/count_distinct and bounded transforms | logical identity | builtin row fact | `current` | accepted expressions/functions | none |
| `Timestamp` | builtin | no typed literal | current | generic comparison only | count/count_distinct/min/max direct | logical identity | builtin row fact | `current` | accepted forms only | none |
| `UUID` | builtin | none | current bounded path | no UUID-specific contract | direct count/count_distinct | logical identity | builtin row fact | `limited_frozen` | accepted forms only | none |
| declared `Enum` | non-builtin declaration | no member literal/reference | metadata/readiness path | no stable pair contract | fails closed | enum semantic/IR metadata | symbol-dependent | `metadata_only` | no enum-specific lowering contract | none |
| type alias | declared plus canonical identity | no new literal | symbol-dependent | canonical target does not grant every operation | may remain closed by declared kind | alias semantic/IR facts | symbol-dependent | declared/canonical metadata | accepted forms only | no domain mapping |
| shape | schema/type definition | none | schema context | not a scalar operation domain | none | shape semantic/IR facts | project schema context | existing schema metadata | none | none |
| unknown sentinel | non-concrete/fail closed | null may produce unknown value type | non-concrete | propagate or diagnose | rejected/non-concrete | explicit sentinel | non-concrete schema state | `unknown` | never lowered as a native type | none |

The matrix records current bounded evidence only. Type identity does not imply
operation support, and backend expression success does not imply native
storage support.

## Core Scalar Types

Bool, Int, Float, Decimal, Text, Date, and Timestamp are the documented
concrete core builtin identities. Only Bool, Text, Int, and Float have current
concrete source literals.

Int and Float have current unary numeric and bounded binary numeric behavior,
including current Int/Float promotion. Bool has current `and`/`or` behavior.
Text has exactly these scalar signatures:

- `lower(Text) -> Text`
- `trim(Text) -> Text`
- `len(Text) -> Int`
- `matches(Text, Text) -> Bool`

Text concatenation is not implemented. Generic known-child comparisons and
`between` produce Bool with conservative unknown nullability; they are current
shared behavior, not a final pair-specific compatibility guarantee. `is null`
and `is not null` produce non-null Bool.

## Temporal Types

Date and Timestamp are current builtin identities. Timestamp is the current
canonical date-plus-time spelling. DateTime is not a builtin or alias. Time
and Interval are unsupported/non-builtin.

Direct Date/Timestamp fields have only current bounded projection, generic
comparison, direct count/count_distinct, and direct min/max surfaces. There is
no Date/Timestamp typed literal syntax, temporal arithmetic, timezone
semantics, timestamp precision model, interval algebra, temporal function
catalog, cast behavior, or native mapping contract.

Current Date/Timestamp behavior is `IMPLEMENTED_LIMITED`. The missing temporal
surfaces are `EXPLICITLY_DEFERRED` or `OUT_OF_SCOPE` according to their owning
layer. Phase 52's first target does not authorize DateTime, Time, or Interval
implementation.

## Decimal Precision And Scale

Current logical Decimal behavior, current private precision/scale facts, and
absent public/backend guarantees are separate.

Current logical behavior:

- Decimal is a canonical builtin.
- Decimal/Decimal `+` and `-` return logical Decimal.
- Decimal/Int and Int/Decimal `+` and `-` return logical Decimal.
- supported Decimal aggregate results remain logical Decimal.

Current private facts:

- `Decimal(p,s)` semantic validation requires current valid integer arguments;
- precision range is `1..38`;
- scale range is `0..precision`;
- invalid arguments use existing `PIE-S2004`;
- private `DecimalPrecisionScale` stores validated facts;
- declaration/type-alias propagation exists only where currently evidenced;
- private expression precision facts cover direct Decimal field references
  only.

Absent or deferred guarantees:

- no Decimal literal;
- no computed-expression precision fusion;
- no aggregate-result precision fusion;
- no Float/Decimal promotion;
- no complete Decimal multiplication/division semantics;
- no public precision/scale fields;
- no `TypeRefIR` precision/scale;
- no Project JSON precision/scale;
- no SQL `DECIMAL(p,s)` guarantee;
- no backend-native precision contract; and
- no overflow or rounding formula.

A bounded Phase 52 handoff may reference existing private facts but must not
implement or promise computed/aggregate fusion formulas.

## UUID And Enum

UUID is a builtin identity with a limited/frozen current surface. Its bounded
surface is declaration/resolution, projection, direct count, and direct
count_distinct. Its public posture remains `limited_frozen`. UUID has no
literal, cast, native mapping, or UUID-specific operation contract. Generic
shared comparison/order/group paths are not stable UUID guarantees.

Enum is a declaration-backed non-builtin semantic/IR kind with public
`metadata_only` posture. `count(Enum field)` fails closed with `PIE-S2314`, and
other aggregate families remain rejected. There are no Enum member
literals/references, casts, ordering/grouping guarantee, DDL, native mapping,
or extension mapping contract. Phase 52's first target may represent these
current facts but may not widen UUID or Enum behavior.

## Any Bytes And Json

Any, Bytes, and Json are builtin identities. Any is a boundary/top-like
logical identity, not runtime dynamic typing. Unsupported Any aggregate
arguments fail aggregate validation.

Direct `count(Bytes field)` and `count(Json field)` are currently accepted.
Other aggregate families remain bounded or rejected. Bytes and Json preserve
public `deferred_builtin` posture. They have no Bytes/Json literal, JSON
path/operator contract, coercion behavior, runtime value system, or native
mapping contract.

No operation support is inferred from builtin membership.

## Aliases Domains And Refinements

Aliases are current declared identities. They preserve declared and canonical
identity, support current forward/chained resolution, and fail cycles with
existing `PIE-S2003`. Canonical expansion does not automatically grant every
operation or aggregate surface.

Parsed `ensure` syntax is not evidence of a completed domain type system.
Money, Currency, units, user domains, refinement predicates, validation
execution, native domains, and coercion semantics are not current behavior.
Domain/refinement implementation and native domain mapping remain outside the
current Phase 51-60 route absent an evidence-backed later replan. Slice 4
designs no domain syntax or API.

## Operator And Type-pair Capabilities

Operation facts are pair-specific where current behavior requires it. Result
type, nullability, status, diagnostic, context/dialect boundary, and Phase 52
relevance remain separate.

| Operation | Current operands | Result | Nullability | Current status / diagnostic | Context / dialect boundary | Phase 52 relevance |
|---|---|---|---|---|---|---|
| unary `+`, `-` | Int or Float | same type | preserve operand | implemented limited; unsupported known operand `PIE-S2105` | semantic fact; selected backend lowers accepted expression | record exact current fact |
| binary `+`, `-`, `*` | Int/Float current matrix | Int or promoted Float | `UNKNOWN` | implemented limited; unsupported known pair `PIE-S2105` | expression-specific lowering | record ordered pair/result |
| binary `+`, `-` | Decimal/Decimal | Decimal | `UNKNOWN` | implemented limited | expression-specific lowering | record exact pair/result |
| binary `+`, `-` | Decimal/Int or Int/Decimal | Decimal | `UNKNOWN` | implemented limited | expression-specific lowering | record both ordered pairs |
| binary `*` | Decimal-involving pair | none | unknown/non-concrete | fail closed with `PIE-S2105` for known unsupported pair | no authorized lowering | negative current fact |
| `%` | Int/Int | Int | `UNKNOWN` | implemented limited; other known pairs `PIE-S2105` | expression-specific lowering | record exact pair |
| `/` | current parsed operands | unknown | `UNKNOWN` | incomplete/unknown without completed pair matrix | no stable semantic capability claim | record unsupported/incomplete posture |
| `and`, `or` | Bool/Bool | Bool | `UNKNOWN` | implemented limited; other known pairs `PIE-S2105` | semantic expression fact | record exact pair |
| comparisons | known children | Bool | `UNKNOWN` | generic current behavior; no final pair diagnostic matrix | expression-specific lowering | retain risky/generic status |
| `between` | known children | Bool | `UNKNOWN` | generic current behavior; no final pair matrix | expression-specific lowering | retain risky/generic status |
| `is null`, `is not null` | any current expression | Bool | `NON_NULL` | implemented limited | expression-specific lowering | record null-check fact |
| `lower` | Text | Text | `UNKNOWN` | exact builtin signature | selected backend function spelling | record signature |
| `trim` | Text | Text | `UNKNOWN` | exact builtin signature | selected backend function spelling | record signature |
| `len` | Text | Int | `UNKNOWN` | exact builtin signature | selected backend function spelling | record signature |
| `matches` | Text, Text | Bool | `UNKNOWN` | exact builtin signature | selected backend function spelling | record signature |

No broad `numeric`, `comparable`, `orderable`, `supports_type`, or equivalent
universal boolean replaces these facts. Slice 4 widens no operator.

## Aggregate Type Capabilities

Aggregate family, direct versus expression argument shape, input canonical
type, result canonical type, result nullability, diagnostics, and deferred
widening are independent facts.

| Aggregate / shape | Current input | Result | Nullability | Current failure / deferred boundary |
|---|---|---|---|---|
| `count()` | no argument | Int | `NON_NULL` | only existing zero-argument form |
| direct `count(field)` | Bool, Bytes, Date, Decimal, Float, Int, Json, Text, Timestamp, UUID | Int | `NON_NULL` | Any, Enum, unknown, unresolved fail closed; unsupported direct type uses `PIE-S2314` |
| bounded `count(expression)` | current field-bearing accepted typed expression | Int | `NON_NULL` | literal-only/general expression widening remains deferred through existing bounded diagnostics |
| direct `count_distinct` | Bool, Int, Float, Decimal, Text, Date, Timestamp, UUID | Int | `NON_NULL` | unsupported direct type uses `PIE-S2314` |
| transformed `count_distinct` | bounded lower/trim Text chain | Int | `NON_NULL` | broad expression widening remains deferred |
| `sum(Int)` | direct or current bounded field-bearing numeric expression | Int | `NULLABLE` | unsupported type/shape uses existing aggregate diagnostics |
| `sum(Float)` | direct or current bounded field-bearing numeric expression | Float | `NULLABLE` | unsupported type/shape uses existing aggregate diagnostics |
| `sum(Decimal)` | direct or current bounded field-bearing numeric expression | logical Decimal | `NULLABLE` | no aggregate precision/scale fact |
| `avg(Int/Float)` | direct or current bounded field-bearing numeric expression | Float | `NULLABLE` | unsupported type/shape uses existing aggregate diagnostics |
| `avg(Decimal)` | direct or current bounded field-bearing numeric expression | logical Decimal | `NULLABLE` | no aggregate precision/scale fact |
| direct `min/max` | Int, Float, Decimal, Date, Timestamp | same canonical type | `NULLABLE` | unsupported direct type uses `PIE-S2314`; expression widening deferred |

The count family result is always `Int NON_NULL` on accepted forms.
Sum/avg/min/max result nullability remains `NULLABLE`; this is a compile-time
result fact and not a database runtime proof. Enum and Any remain fail-closed
boundaries. Bytes/Json remain bounded to direct count. There is no whole-type
`aggregate-capable` flag and no aggregate Decimal precision/scale fact.

## Nullability Capabilities

The exact nullability vocabulary is:

1. `NON_NULL`
2. `NULLABLE`
3. `UNKNOWN`

Unknown type identity, unknown nullability, SQL three-valued-logic `UNKNOWN`,
and non-concrete project schema availability are distinct.

Current bounded rules are:

- source fields preserve known nullability;
- Bool/Text/Int/Float literals are `NON_NULL`;
- the null literal has no concrete canonical type fact;
- unary numeric expressions preserve operand nullability;
- many binary and scalar expressions use conservative `UNKNOWN`;
- `is null` and `is not null` return `Bool NON_NULL`;
- accepted count results are `NON_NULL`;
- accepted sum/avg/min/max results are `NULLABLE`; and
- project row facts remain private and unserialized.

Compile-time nullability is not runtime truth. It does not infer database
constraints, empty-input runtime guarantees, or collapse SQL three-valued
logic.

## IR SQL And Backend Boundaries

`TypeRefIR` carries declared/canonical identity and nullability. It carries no
Decimal precision/scale and no native database mapping. Semantic identity, IR
representability, SQL expression lowering, and native database mapping are
independent dimensions.

Accepted PostgreSQL/private MySQL expression lowering is expression-specific.
Pietto emits no DDL/type catalog. It does not infer physical mappings from
emitted SQL. Existing private project type/nullability facts remain private;
Project JSON v2 and Semantic Metadata Artifact v1 receive no Slice 4 field or
vocabulary change.

## Native Database Mapping Boundary

No complete physical/native type table exists. No schema introspection,
`db pull`, driver conversion, storage precision, collation model, timezone
model, extension discovery, DDL, or runtime conversion exists.

Backend expression success does not imply native storage support. Native
database mapping remains outside the current Phase 51-60 route absent a later
evidence-backed replan. Slice 4 records that boundary and adds no mapping.

## Private Capability Dimension Model

The readiness model has exactly these 19 orthogonal documentation dimensions:

1. Identity and classification
2. Declaration and resolution
3. Literal construction
4. Cast/coercion
5. Projection/reference
6. Null-check behavior
7. Equality/comparison
8. Ordering/grouping
9. Arithmetic
10. Scalar function
11. Aggregate argument
12. Aggregate result
13. General nullability propagation
14. Window readiness
15. Private project representation
16. IR representability
17. Backend expression lowering
18. Public metadata posture
19. Native database mapping

Slice 4 adds no production carrier. Future separately authorized private facts
may be keyed by capability kind, subject type, optional right-hand type,
operation/function, context, optional dialect/extension overlay, status,
evidence, and fail-closed reason.

Missing or conflicting capability evidence fails closed. Type-wide identity
does not imply operation support. Backend expression success does not imply
native storage support. No public enum, JSON schema, manifest field, or Python
API is committed.

## Cross-phase Dependencies

- Phase 51 may consume Slice 3 aggregate/grouped private output-schema
  readiness together with existing type/nullability facts.
- Phase 53 window readiness will need explicit argument, ordering, result-type,
  and nullability capability questions.
- Phase 55 semantic package assets will need static type identity and
  attribution without executable package resolution.
- Phase 56 capability profile schema/checking may consume later private facts
  only after separate authorization.
- Phase 57 PostgreSQL extension signature catalogs will need base capability
  versus declared extension-overlay separation.
- Phase 58 explain/portability/public metadata requires a separate privacy and
  schema contract before any exposure.
- Phase 59 package graph/lineage integration may attribute private evidence
  without making packages executable.
- Phase 60 is a multi-dialect completion checkpoint, not automatic widening.

None of these dependencies starts a phase, authorizes behavior, exposes
private facts, or creates package/runtime/database authority.

## Bounded Phase 52 Handoff

The bounded planning direction is **Phase 52 — Core Type-System Capability
Foundation**. Phase 52 remains unstarted.

Its first separately authorized implementation target may be private,
immutable, deterministic, current-behavior-only capability facts covering the
exact 11 builtins plus declaration-backed Enum, aliases, shapes where
identity-relevant, and unknown/non-concrete state. It may record current
resolution, literal, operator-pair, scalar-function, aggregate, nullability,
private-project, IR, and expression-lowering evidence with fail-closed missing
capability lookup and no acceptance/rejection change.

Initial exclusions are exact: no new builtin; no parser/grammar syntax; no
DateTime/Time/Interval implementation; no new literal or cast; no operator
widening; no Decimal fusion/formula; no UUID/Enum widening; no
domain/refinement behavior; no native database mapping; no public metadata;
no CLI/JSON change; no package manifest; no extension catalog; no backend
expansion; no runtime/database work; and no release work.

Slice 4 does not finalize Phase 52 implementation slices.

## Explicit Deferrals And Non-goals

Deferred surfaces include temporal literals/functions/arithmetic/timezones,
DateTime/Time/Interval, casts, Text concatenation, final pair-specific
comparison, Decimal multiplication/division completion, Float/Decimal
promotion, Decimal literals, computed/aggregate precision fusion,
UUID-specific operations, Enum member semantics, Json operators/literals,
Bytes operations, broader alias aggregates, and window behavior.

Package manifests/resolution/installation, capability-profile public schema,
extension catalogs, multi-dialect checking, public explain/metadata, and
package graph integration remain owned by separately authorized later slices
and phases.

Runtime/database execution, schema introspection, native database mapping/DDL,
database domains, drivers, migrations, storage constraints, package registry
or network behavior, and arbitrary plugin execution are out of scope.

Slice 4 adds no parser, grammar, generated artifact, AST, semantic behavior,
IR behavior, SQL behavior, CLI, JSON, diagnostic, source, public metadata,
project-model behavior, dependency, workflow, fixture, golden, example,
package metadata, or release behavior.

## Package Version And Release Boundary

Package version remains `0.1.0`. Slice 4 authorizes no package version change,
tag, release, publish, upload, signing, or attestation. It authorizes no CI
trigger, rerun, watch, or cancellation and no stage, commit, or push in Gate 2.

## Separate Authorization And Stop Conditions

Every implementation requires separate authorization. Slice 4 is not complete
in Gate 2 and Phase 50 remains in progress. Gate 3, Slice 5, and Phase 52 are
not prepared or started by this contract.

Stop without repair or scope expansion if the exact six-file allowlist cannot
hold; the roadmap, historical register, completed Slice 1-3 specs, source,
public schema, or release surface would change; the exact 11 builtins cannot
be preserved; Enum would need to become builtin; a production carrier appears
necessary; documentation implies widened behavior; compatibility requires
weakening a historical lock; validation fails; or Slice 5/Phase 52 work
appears necessary.
