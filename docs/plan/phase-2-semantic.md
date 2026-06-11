# Phase 2: Semantic Checker Plan

## Goal

Build a single-file semantic checker over the existing public parser AST.
Phase 2 accepts a successfully parsed `Script` and produces structured,
ordered diagnostics plus a readonly semantic model for later compiler phases.

Phase 2 does not mutate or annotate the parser AST.

## Boundaries

Implement only semantic analysis for syntax already supported by Phase 1.

Do not implement:

- semantic IR or other lowering;
- SQL generation or validation SQL generation;
- SQL execution or database connections;
- DML;
- optimizer behavior;
- CLI runtime behavior;
- UI or visualization;
- runtime or concurrency features;
- module/import syntax;
- cross-file analysis;
- new grammar or parser AST syntax.

## Current Status

**Phase 2 Semantic MVP: Complete.**

The MVP checker covers the supported single-file namespaces, type alias
expansion, shape and relation structure, minimal expression typing, callable
and field body compatibility, relation and derived-field cycles, source row
schemas, and static `postgres.table(Text)` connector signatures.

Current MVP acceptance status:

```text
529 passed
10 committed examples checked
1 intentional checked-mode warning: PIE-S2303
```

The following semantic hardening and later compiler work is intentionally
deferred beyond the Phase 2 MVP:

- user-defined callable calls inside expressions;
- callable call-graph analysis and top-level callable recursion detection;
- purity checking;
- nullability guard refinement and unsafe nullable-use checking;
- casts, implicit conversions, and subtyping;
- overload resolution and generics;
- full SQL type compatibility;
- database schema introspection;
- IR and SQL generation;
- SQL execution and CLI runtime behavior.

These are future semantic-hardening slices or later compiler phases. MVP
completion does not mean that Pietto has a complete semantic type system.

## Public API

The semantic package exposes an AST-based entry point:

```python
def analyze(
    script: Script,
    *,
    mode_override: CheckMode | None = None,
) -> SemanticResult:
    ...
```

`CheckMode` has three values:

```python
class CheckMode(StrEnum):
    LOOSE = "loose"
    CHECKED = "checked"
    STRICT = "strict"
```

The effective mode is selected in this order:

1. `mode_override`, when provided;
2. `script.header.mode`, when declared;
3. `CheckMode.CHECKED`.

`SemanticResult` contains:

- ordered `Diagnostic` values;
- a readonly `SemanticModel`.

The analyzer receives an AST rather than source text. Parsing remains the
responsibility of `parser_api.py`, and parser diagnostics are not recreated by
the semantic layer.

## Semantic Model

`SemanticModel` is immutable from the public API and must not contain ANTLR
objects. The Phase 2 MVP built it incrementally across the slices below.

The foundation slice contains only top-level symbol tables. Later slices add:

- resolved `TypeExpr` values;
- inferred expression value types;
- resolved name and callable references;
- shape and relation row schemas;
- dependency information needed for cycle diagnostics.

The model must keep references to existing AST nodes rather than copying or
rewriting the parser AST. Public collections should use tuples or readonly
mapping interfaces.

## Namespaces

Phase 2 uses three independent top-level namespaces.

### Type Namespace

Contains:

- built-in types;
- `TypeDef`;
- `EnumDef`;
- `ShapeDef`.

### Callable Namespace

Contains:

- built-in functions;
- `ConstraintDef`;
- `DeriveDef`.

### Relation Namespace

Contains:

- `SourceDef`;
- `TableDef`;
- `QueryDef`.

A duplicate is an error only when two declarations occupy the same namespace.
The same spelling may appear once in each different namespace.

## Forward References

Forward references are allowed within one `Script`. Analysis first collects
all top-level symbols and only then resolves references.

Definition source ordering remains available for diagnostics and presentation,
but it does not control visibility. Dependency cycles are diagnosed in later
hardening slices after the relevant dependency graphs exist.

## Unknown Handling

An unknown symbol, type, field, callable, or relation produces one primary
diagnostic at the originating reference.

The analyzer then uses an internal Unknown placeholder so dependent checks can
continue without producing cascades of misleading type errors. Operations
whose inputs are Unknown normally produce Unknown without another
incompatibility diagnostic.

Checks unrelated to the unknown value continue. Unknown placeholders are
internal semantic state and are not added to the parser AST.

## Mode Behavior

Correctness failures are errors in every mode. Examples include duplicate
symbols, unknown names, invalid references, incompatible known types, and
dependency cycles.

The following checks are mode-sensitive:

- implicit nullability;
- sources without an attached shape;
- computed select expressions without an explicit alias.

Implicit nullability has a fixed Phase 2 policy:

| Mode | Behavior |
|---|---|
| `loose` | no diagnostic |
| `checked` | warning |
| `strict` | error |

Untyped sources follow the same mode matrix: loose is silent, checked emits a
warning, and strict emits an error. Unnamed computed projections follow the
same mode matrix.

## Built-in Catalog

Start with a small, explicit catalog containing only the portable types and
functions needed by the implemented syntax and committed examples.

The catalog should use typed declarations rather than ad hoc name checks. It
must be straightforward to extend without changing parser AST classes.

The first catalog does not promise:

- a complete numeric promotion hierarchy;
- function overload resolution;
- generics or type variables;
- all SQL dialect functions;
- a connector plugin or extension system;
- automatic discovery from a database.

Unknown built-ins are handled through the normal Unknown diagnostic policy.

## Implementation Slices

Each slice should be independently testable and should update this plan with
its completion status and current test count.

### 1. Plan and Package Scaffold: Completed

- Create the semantic package structure.
- Define `CheckMode`, `SemanticResult`, and the initial readonly
  `SemanticModel`.
- Add diagnostic helpers that reuse the existing public diagnostic types.
- Add `analyze()` without implementing reference or type validation.

This slice must not change parser behavior or AST classes.

Implemented the public AST-based `analyze()` entry point, effective mode
selection, empty readonly namespace mappings, and empty semantic diagnostics.
No symbol collection or semantic validation is implemented yet.

Current test status:

```text
262 passed
```

### 2. Symbol Collection: Completed

- Register all user-defined top-level definitions in the three namespaces.
- Preserve declaration spans and source ordering in symbol metadata.
- Diagnose duplicates within a namespace.
- Allow identical names across different namespaces.
- Verify that forward declarations are visible after collection.

Implemented readonly namespace mappings whose values are the existing AST
definition nodes. Duplicate declarations produce `PIE-S2001` at the later
definition's span, while the first declaration remains bound. Built-in
function registration remains deferred to the minimal expression slice.

No expression, field-name, callable, or relation reference resolution is
implemented yet.

Current test status:

```text
274 passed
```

### 3. Minimal Type Resolution and Alias Expansion: Completed

- Resolve built-in and user-defined type names.
- Preserve type alias identity while expanding aliases to canonical targets.
- Diagnose direct and indirect type alias cycles.
- Record effective nullability separately from parser nullability syntax.
- Apply the fixed implicit-nullability mode policy.
- Introduce Unknown types and suppress dependent cascades.
- Defer type argument validation to a later semantic slice.

Do not implement a complete numeric hierarchy, overloads, or generic types.

Implemented an explicit portable built-in type catalog, readonly
`TypeExpr` identity resolution, canonical expansion, and effective-nullability
mappings. `SemanticModel.type_resolutions` preserves alias identity while
`SemanticModel.type_expansions` exposes the final built-in, enum, shape, or
Unknown target. Alias chains expand transitively, and direct or indirect cycles
produce `PIE-S2003`. Unknown types produce `PIE-S2002`; implicit nullability
produces mode-sensitive `PIE-S2005`.

Type argument validation, generics, subtyping, implicit casts, and full type
compatibility remain unimplemented.

Current test status:

```text
477 passed
```

### 4. Shape Structural Checks: Completed

- Treat field, check, unique, and index names as one local shape-item
  namespace.
- Diagnose duplicate shape-item names.
- Validate that `unique` and `index` targets name existing fields.
- Diagnose repeated target fields within one `unique` or `index`.
- Keep annotations as unvalidated metadata.

Implemented `PIE-S2501` for duplicate shape-item names, `PIE-S2502` for unknown
unique/index target fields, and `PIE-S2503` for repeated targets. Checks continue
across all shapes and diagnostics retain deterministic source ordering.

Unique and index target names are currently stored as strings without
individual AST spans, so target diagnostics use the containing item's span.

No public shape row schema or dependency analysis is implemented in this
structural slice. Shape predicate and field derive validation are tracked in
the expression slice below; derived-field cycles are tracked in the dependency
hardening slice.

Current test status:

```text
311 passed
```

### 5. Source Checks and Row Schemas: Completed

- Resolve typed source shape names against the type namespace.
- Require typed source bindings to name a `ShapeDef`.
- Build ordered readonly source row schemas from shape fields.
- Represent missing, invalid, and untyped source schemas as Unknown.
- Apply the documented mode-sensitive policy to untyped sources.
- Validate the static signature of the initial built-in source connector.

Implemented readonly `RowSchema` and `RowField` models that reuse existing
resolved types and effective nullability. `SemanticModel.source_row_schemas`
maps every `SourceDef` to a known or Unknown schema. `PIE-S2303` reports missing or
non-shape bindings and mode-sensitive untyped sources.

The only recognized source connector is `postgres.table(Text)`. Unknown
connectors, non-call connector expressions, wrong arity, and known non-Text
arguments produce `PIE-S2306`. Unknown argument types suppress this dependent
diagnostic. Connector arguments use the incremental expression typer, but the
connector call itself remains outside the normal built-in function catalog.

No database connection, credential handling, schema introspection, physical
table validation, or row-schema inference from connector metadata is
implemented. Typed source row schemas still come exclusively from the
declared shape.

Current test status:

```text
527 passed
```

### 6. Minimal Expression Typing Scaffold: Completed

- Record immutable expression value types in `SemanticModel`.
- Type scalar literals as portable built-in values.
- Resolve bare field names against known relation input schemas.
- Type calls to the initial explicit pure built-in function catalog.
- Type simple comparisons and `is null` predicates as `Bool`.
- Preserve Unknown values without cascading dependent diagnostics.

Implemented public `ValueTypeKind` and `ValueType` models plus the readonly
`SemanticModel.expression_value_types` mapping. Typing currently runs for
source connector arguments, shape check bodies, index predicates, and
table/query `where` and select expressions. Supported recursive forms are
literals, bare names, built-in calls, simple comparisons, and `is null`/`is
not null`. Unsupported forms remain opaque Unknown values.

The initial exact-signature function catalog supports `lower(Text) -> Text`,
`trim(Text) -> Text`, `len(Text) -> Int`, and
`matches(Text, Text) -> Bool`. Unknown functions produce `PIE-S2103`; wrong
arity or known incompatible arguments produce `PIE-S2104`. Unknown arguments
suppress dependent call diagnostics.

Known table/query `where` expressions are validated as `Bool`. A known
non-Bool expression produces `PIE-S2202`; Unknown expression types suppress
this dependent diagnostic.

Shape check bodies and index predicates use the same `PIE-S2202` policy
against their enclosing shape's field environment.

Field derive expressions are typed against all fields in their enclosing
shape. Known canonical types that do not match the declared field type produce
`PIE-S2402`; Unknown expression or field types suppress the dependent
diagnostic. Alias expansion is applied to both referenced and target field
types.

No overloads, generics, arithmetic typing, dotted-name resolution, complex
projection inference, other consumer validation, or nullability-guard
refinement is implemented.

Current test status:

```text
499 passed
```

### 7. Constraint and Derive Validation: Completed

- Resolve parameter and return types.
- Diagnose duplicate parameters and unknown names.
- Require constraint return types and bodies to be compatible with `Bool`.
- Require derive bodies to be compatible with their declared return types.
- Restrict calls to the explicit built-in catalog.

Purity, recursion, and dependency cycles should be introduced conservatively
and may be completed in the dependency hardening slice.

Duplicate parameters produce `PIE-S2001` at the later parameter, and
constraints whose known canonical return type is not the built-in `Bool`
produce `PIE-S2401`. Constraint and derive bodies are typed in a local
parameter environment using the incremental expression checker. Known body
types that do not match the required canonical return type produce
`PIE-S2402`; Unknown body or return types suppress this dependent diagnostic.
Type aliases are expanded before parameter use and body/return comparison.

Only the explicit built-in function catalog is callable in bodies.
User-defined callable resolution, recursion, purity, and dependency analysis
are not implemented. Field derive expressions use the same built-in-only
expression boundary.

Current test status:

```text
489 passed
```

### 8. Relation From-Target Resolution: Completed

- Resolve `from` references in the relation namespace.
- Allow source, table, and query targets, including forward references.
- Preserve first-binding behavior for duplicate relation symbols.
- Record successful resolutions without mutating parser AST nodes.

Implemented readonly `SemanticModel.from_resolutions`, keyed by `FromClause`.
Unknown targets produce `PIE-S2301` at the from-clause span. Resolution continues
after unknown targets. Relation cycles are diagnosed by the dedicated cycle
slice.

No table/query row schemas, field resolution, expression typing, projection
checking, or schema inference is implemented in this slice.

Current test status:

```text
340 passed
```

### 9. Minimal Relation Row Schema and Projection Names: Completed

- Propagate known source, table, and query input schemas.
- Build ordered output schemas for stable projection names.
- Diagnose unknown bare fields without cascading through Unknown schemas.
- Diagnose duplicate projection output names.
- Require aliases for computed projections according to the active mode.
- Preserve aliased and dotted-name outputs with Unknown value types.

Implemented readonly `SemanticModel.relation_row_schemas` for every table and
query. `PIE-S2102` reports an unknown field selected from a known input schema;
`PIE-S2304` reports an unnamed computed projection according to the
loose/checked/strict mode policy; `PIE-S2305` reports duplicate output names.
Aliases determine output names, bare fields retain their names, and bare
dotted names use their final segment. Aliased and dotted-name outputs retain
Unknown types until expression typing expands.

Unknown inputs, unresolved relations, unknown bare fields, and cyclic
relations produce Unknown row schemas that suppress dependent field
diagnostics. No complex projection type inference or dotted-name resolution is
implemented. Connector signatures are checked by the source slice, while
physical database targets remain unchecked.

Current test status:

```text
428 passed
```

### 10. Relation Cycle Diagnostics: Completed

- Build table/query dependency edges from resolved `from` clauses.
- Treat source dependencies as leaves.
- Diagnose direct and indirect table/query cycles.
- Keep cyclic relation row schemas Unknown to suppress dependent diagnostics.

Implemented deterministic DFS cycle detection over table and query
dependencies. Each distinct cycle produces one `PIE-S2302` at the `FromClause`
edge that closes the cycle. Self-cycles and mixed table/query cycles are
supported; unknown relations remain covered only by `PIE-S2301`.

Callable cycle checks remain unimplemented. Type-alias and derived-field
cycles are covered by their dedicated semantic slices.

Current test status:

```text
369 passed
```

### 11. Derived-Field Dependency Hardening: Completed

- Detect derived-field dependency cycles.
- Ensure one primary cycle diagnostic is reported for each relevant cycle.
- Keep diagnostics deterministic and suppress dependent cascades.

Derived-field cycle detection is complete. Each shape gets an independent
graph whose edges come from bare same-shape field references inside currently
supported expression forms. Non-derived fields are leaves, unknown names do
not create edges, and function call targets are not field dependencies.
Strongly connected components provide a stable reporting strategy: each
cyclic component produces one `PIE-S2504` at its earliest field in source
order.

Top-level callable recursion, callable dependency graphs, and purity checking
are deferred beyond the Phase 2 MVP.

Current test status:

```text
513 passed
```

### 12. Phase 2 Examples and Documentation Audit: Completed

- Make every committed `examples/**/*.pietto` file self-contained.
- Require each normal example to have no semantic errors under the default
  checked mode.
- Keep negative semantic programs in test fixtures rather than normal
  examples.
- Update the specification, project guidance, and this plan to distinguish
  completed semantic behavior from later phases.

Warnings may remain in examples only when they intentionally demonstrate
documented checked-mode behavior.

Completed the semantic example gate: every committed `examples/**/*.pietto` file
is parsed and analyzed under the default checked mode, and the test suite
rejects semantic errors with path-specific diagnostic details. Normal examples
are self-contained. The only intentional checked-mode warning is
`examples/sources/users.pietto:11:1`, where untyped `raw_events` produces
`PIE-S2303`; a regression test fixes this expectation explicitly.

Current coverage and test status:

```text
10 examples
529 passed
```

## Diagnostics

Semantic diagnostics reuse `Diagnostic`, `Severity`, and `SourceLocation` from
the existing frontend. They use the canonical `PIE-Sxxxx` format documented in
`docs/spec/diagnostics.md` and must include stable source locations and
suggestions where a useful correction is known. Severity remains a separate
field.

Diagnostic output is sorted deterministically by:

1. source path when available;
2. line;
3. column;
4. diagnostic code.

Each implementation slice should reserve and document only the diagnostic
codes it actually introduces. The plan does not preallocate a large code
matrix before checks exist.

## Testing Strategy

Add focused tests with each slice:

- positive and negative symbol resolution;
- same-namespace duplicates and allowed cross-namespace names;
- forward references;
- mode-sensitive nullability behavior;
- Unknown cascade suppression;
- readonly model behavior and parser AST immutability;
- no ANTLR leakage through semantic public APIs;
- stable diagnostic ordering, paths, and source locations;
- type, shape, expression, callable, and relation checks as they are added;
- dependency cycles once graph analysis exists;
- all committed examples under default checked mode by Phase 2 completion.

Tests must not require a database, network access, SQL generation, or SQL
execution.

## MVP Acceptance Criteria

The Phase 2 semantic MVP is complete. It satisfies the following criteria:

- `analyze()` accepts a public parser `Script`;
- `SemanticResult` exposes ordered diagnostics and a readonly
  `SemanticModel`;
- all three namespaces and forward references behave as documented;
- known correctness failures produce structured diagnostics;
- Unknown placeholders prevent dependent diagnostic cascades;
- mode-sensitive behavior is documented and tested;
- implemented AST expressions and definitions have the documented MVP
  semantic coverage;
- implemented relation, type-alias, and derived-field dependency cycles are
  diagnosed deterministically;
- every committed normal example is self-contained and has no semantic errors
  in default checked mode;
- no IR, SQL, execution, database, CLI runtime, UI, optimizer, DML, module,
  import, cross-file, or concurrency behavior has been introduced.

Callable graphs and recursion, purity, nullability refinement, casts,
subtyping, overloads, generics, full SQL type compatibility, and schema
introspection remain explicit post-MVP work.

Run after each implementation slice:

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
```
