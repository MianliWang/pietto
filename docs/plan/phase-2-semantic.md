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
objects. It is built incrementally as Phase 2 slices are completed.

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

The exact severity policy for untyped sources and unnamed computed projections
is defined when their implementation slices begin. Those decisions must remain
documented and covered by mode-matrix tests.

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
definition nodes. Duplicate declarations produce `P2001` at the later
definition's span, while the first declaration remains bound. Built-in
registration is deferred to the minimal type and expression slices.

No type, expression, field, callable, or relation reference resolution is
implemented yet.

Current test status:

```text
274 passed
```

### 3. Minimal Type Resolution

- Resolve built-in and user-defined type names.
- Resolve type aliases without mutating `TypeExpr`.
- Record effective nullability separately from parser nullability syntax.
- Apply the fixed implicit-nullability mode policy.
- Introduce Unknown types and suppress dependent cascades.
- Validate only the initial explicit built-in type argument forms.

Do not implement a complete numeric hierarchy, overloads, or generic types.

### 4. Shape Field Checks

- Build field symbol tables and initial row schemas for shapes.
- Diagnose duplicate field and shape-item names according to the chosen local
  namespace policy.
- Resolve field types.
- Validate that `unique` and `index` targets name existing fields.
- Keep annotations as unvalidated metadata.

Field expressions, derived-field dependencies, predicate types, and cycle
checks may remain for later slices.

### 5. Minimal Expression Typing

- Add expression typing incrementally for literals, names, dotted names, basic
  calls, unary arithmetic, basic arithmetic, comparisons, Boolean operators,
  `between`, `like`, and `is null`.
- Start with a small explicit built-in function catalog.
- Define local scopes for `self`, parameters, shape fields, and relation rows
  only as required by each consumer.
- Record expression value types in `SemanticModel`.

This slice does not promise complete expression typing. Numeric promotion,
function overloads, dialect functions, and advanced nullable-flow analysis
remain out of scope.

Nullability guard refinement is a later expression sub-slice after basic
expression typing is stable. It should initially target simple guards such as
`x is not null and ...` without becoming a general control-flow engine.

### 6. Constraint and Derive Validation

- Resolve parameter and return types.
- Diagnose duplicate parameters and unknown names.
- Require constraint return types and bodies to be compatible with `Bool`.
- Require derive bodies to be compatible with their declared return types.
- Restrict calls to the explicit built-in and user callable catalogs.

Purity, recursion, and dependency cycles should be introduced conservatively
and may be completed in the dependency hardening slice.

### 7. Source, Table, and Query Checks

- Resolve typed source shape references.
- Treat untyped source row schemas as Unknown and apply the documented
  mode-sensitive policy.
- Resolve `from` references in the relation namespace.
- Build table and query row schemas from ordered select items.
- Require known `where` expressions to be Boolean-compatible.
- Resolve relation fields against the input row schema.
- Apply the documented mode-sensitive policy to unnamed computed projections.

Do not connect to databases or validate physical connector targets.

### 8. Dependency and Cycle Hardening

- Detect type-alias cycles.
- Detect callable recursion and dependency cycles.
- Detect derived-field dependency cycles.
- Detect table/query relation cycles.
- Ensure one primary cycle diagnostic is reported for each relevant cycle.
- Keep diagnostics deterministic and suppress dependent cascades.

### 9. Phase 2 Examples and Documentation Audit

- Make every committed `examples/**/*.pie` file self-contained.
- Require each normal example to have no semantic errors under the default
  checked mode.
- Keep negative semantic programs in test fixtures rather than normal
  examples.
- Update the specification, project guidance, and this plan to distinguish
  completed semantic behavior from later phases.

Warnings may remain in examples only when they intentionally demonstrate
documented checked-mode behavior.

## Diagnostics

Semantic diagnostics reuse `Diagnostic`, `Severity`, and `SourceLocation` from
the existing frontend. They must include stable codes, source locations, and
suggestions where a useful correction is known.

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

## Acceptance Criteria

Phase 2 is complete when:

- `analyze()` accepts a public parser `Script`;
- `SemanticResult` exposes ordered diagnostics and a readonly
  `SemanticModel`;
- all three namespaces and forward references behave as documented;
- known correctness failures produce structured diagnostics;
- Unknown placeholders prevent dependent diagnostic cascades;
- mode-sensitive behavior is documented and tested;
- implemented AST expressions and definitions have the planned semantic
  coverage;
- dependency cycles are diagnosed deterministically;
- every committed normal example is self-contained and has no semantic errors
  in default checked mode;
- no IR, SQL, execution, database, CLI runtime, UI, optimizer, DML, module,
  import, cross-file, or concurrency behavior has been introduced.

Run after each implementation slice:

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
```
