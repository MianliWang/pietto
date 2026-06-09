# Phase 3: Semantic IR Plan

## Status

Planning only. No Phase 3 IR classes, builder, diagnostics, or SQL backend are
implemented yet.

## Goal

Lower a successfully analyzed public parser `Script` plus its readonly
`SemanticModel` into an immutable Semantic IR.

```text
Pietto AST + readonly SemanticModel -> Semantic IR
```

The IR is the compiler boundary between semantic analysis and later SQL
backends. It should contain resolved, canonical compiler data rather than
requiring a backend to reinterpret parser AST syntax.

## Non-Goals

Phase 3 does not implement:

- SQL string generation;
- SQLGlot AST generation or backend integration;
- database connections or execution;
- connector runtime behavior;
- schema introspection;
- optimizer passes;
- CLI runtime behavior;
- UI;
- DML;
- new grammar syntax or parser AST changes;
- cross-file or module analysis;
- deferred Phase 2 semantic hardening.

## Public API

The first core API should be:

```python
def build_ir(
    script: Script,
    semantic_model: SemanticModel,
) -> IrResult:
    ...
```

The caller must run `analyze()` first and call `build_ir()` only when semantic
analysis has no `ERROR` diagnostics. `build_ir()` does not rerun semantic
analysis. A `compile_to_ir()` convenience wrapper is not part of the initial
slice.

The planned result shape is:

```python
@dataclass(frozen=True)
class IrResult:
    ir: ScriptIR | None
    diagnostics: tuple[Diagnostic, ...]
```

An IR-lowering error returns `ir=None`. Warnings do not prevent a usable IR.
Semantic diagnostics remain `PIE-Sxxxx`; IR-lowering diagnostics use
`PIE-Ixxxx`. This plan does not reserve specific IR diagnostic numbers before
the corresponding checks exist.

## Model Principles

IR nodes should use frozen dataclasses, tuples, and readonly mappings. Public
IR must not contain ANTLR objects, parser contexts, tokens, or parser AST
objects.

The IR should preserve:

- useful source spans and diagnostic locations;
- top-level definition ordering;
- projection and row-schema field ordering;
- resolved symbol identities;
- declared and canonical types;
- effective nullability;
- row schemas;
- relation dependency references;
- source connector names and static arguments without executing connectors.

Resolved references should use a stable `SymbolId`, based initially on
namespace plus name, rather than relying only on unresolved strings.

## IR Categories

The initial model should include or provide equivalents for:

### Top Level

- `ScriptIR`

### Declarations

- `TypeIR`
- `EnumIR`
- `ShapeIR`
- `ConstraintIR`
- `DeriveIR`

### Sources and Relations

- `SourceIR`
- `RelationIR`

`RelationIR` may use focused variants for tables and queries if their lowered
forms diverge. The initial design should avoid encoding backend-specific SQL
constructs.

### Relation Operations

- `ProjectionIR`
- `FilterIR`

### Expressions

- `FieldRefIR`
- `LiteralIR`
- `CallIR`
- unary expression IR;
- binary expression IR;
- comparison IR;
- between IR;
- is-null IR.

These categories cover the current parser expression surface. They do not
promise new operators, overloads, or advanced expression semantics.

### Schema and Type Metadata

- `RowSchemaIR`
- `RowFieldIR`
- `TypeRefIR`
- stable `SymbolId`

Type metadata should preserve both declared identity and canonical semantic
type where that distinction is useful.

## Semantic Model Dependency

Phase 3 consumes Phase 2 facts rather than resolving names or types again.
Lowering should use the readonly `SemanticModel` for:

- namespace symbols;
- resolved and expanded types;
- effective nullability;
- source and relation row schemas;
- resolved `from` targets;
- expression value types;
- relation dependency information represented by resolved references.

Missing or inconsistent required facts should produce deterministic,
structured `PIE-Ixxxx` diagnostics instead of ordinary uncaught exceptions.
The builder must not mutate either `Script` or `SemanticModel`.

## Diagnostics Policy

- Keep diagnostics ordered deterministically by source location and code.
- Preserve severity as a separate field.
- Reuse the existing public `Diagnostic` structure.
- Do not duplicate semantic diagnostics during lowering.
- Treat invalid or missing semantic prerequisites as IR-lowering failures.
- Use Unknown-compatible internal handling where useful to avoid cascading
  diagnostics, while returning `ir=None` if a valid complete IR cannot be
  built.

## Implementation Slices

### 1. Package Scaffold and Readonly Models

- Create the IR package public API.
- Define immutable core models, `IrResult`, and `build_ir()`.
- Add AST/model immutability and public-isolation tests.
- Do not lower definitions yet beyond trivial script metadata.

### 2. Symbol, Type, Nullability, and Schema Lowering

- Introduce stable `SymbolId` values.
- Lower declared and canonical type references.
- Lower effective nullability.
- Lower ordered source and relation row schemas.

### 3. Expression Lowering

- Lower the complete minimal expression surface already represented by the
  parser AST.
- Attach existing semantic value types and resolved references.
- Keep unsupported or inconsistent semantic facts diagnostic-driven.

### 4. Declaration Lowering

- Lower type, enum, shape, constraint, derive, and source declarations.
- Preserve declaration order, spans, contracts, and static connector data.
- Do not execute or validate connectors beyond Phase 2 facts.

### 5. Relation Lowering

- Lower table and query definitions.
- Represent filters, projections, output schemas, and resolved dependencies.
- Preserve projection order and stable output names.
- Do not generate SQL.

### 6. Diagnostic and Unknown Hardening

- Make missing semantic facts produce deterministic `PIE-Ixxxx` diagnostics.
- Verify that failures do not leak partial mutable state.
- Audit Unknown handling and diagnostic cascade suppression.

### 7. Examples and Completion Audit

- Parse and analyze every committed example.
- Build IR for every example without IR `ERROR` diagnostics.
- Audit docs, diagnostics, spans, ordering, and public API isolation.
- Confirm that no SQL or runtime behavior entered Phase 3.

## Testing Strategy

Each slice should add focused tests for:

- frozen IR and result objects;
- readonly public mappings and tuple collections;
- no mutation of `Script` or `SemanticModel`;
- no ANTLR or parser AST leakage through public IR;
- stable spans, definition order, projection order, and row-schema order;
- accurate copying of semantic symbols, canonical types, nullability, and
  schemas;
- deterministic structured diagnostics for missing semantic facts;
- no ordinary exceptions for expected lowering failures.

By Phase 3 completion, all committed `examples/**/*.pie` files should parse,
analyze, and build IR without IR errors. Tests must not generate SQL, connect
to databases, execute connectors, or require network access.

## Roadmap

- **Phase 2: Semantic Checker MVP** - complete; advanced semantic hardening is
  deferred.
- **Phase 3: Semantic IR** - lower AST plus `SemanticModel` into immutable,
  backend-neutral IR.
- **Phase 4: PostgreSQL SQL Generation** - compile basic table and query IR
  first; add constraint validation SQL in later backend slices.
- **Phase 5: CLI and Developer Tooling** - expose check, IR inspection, and
  compilation workflows after compiler APIs are stable.

Phase 3 explicitly excludes SQL strings, SQLGlot integration, execution,
connector runtime, optimizer behavior, UI, CLI runtime, and new language
syntax.

## Completion Criteria

Phase 3 is complete when:

- `build_ir()` consumes a public `Script` and readonly `SemanticModel`;
- `IrResult` and all public IR nodes are immutable;
- current supported declarations, relations, and expressions lower without
  re-running semantic analysis;
- resolved symbols, canonical types, nullability, row schemas, dependencies,
  ordering, and useful spans are preserved;
- lowering failures produce deterministic `PIE-Ixxxx` diagnostics;
- all committed examples build IR without IR errors;
- no SQL generation, execution, connector runtime, CLI runtime, optimizer,
  UI, grammar, or parser behavior has been added.
