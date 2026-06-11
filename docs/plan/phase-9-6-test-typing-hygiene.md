# Phase 9.6: Test Typing Hygiene

## Status

**Phase 9.6 Test Typing Hygiene is complete.**

Phase 9.6 removes test-suite Pyright diagnostics without changing production
behavior or weakening the Phase 9.5 handwritten-production gate.

## Baseline

The initial `uvx pyright tests --outputjson` run analyzed 77 test files and
reported 89 errors and no warnings:

- 57 `reportAttributeAccessIssue`;
- 15 `reportOptionalMemberAccess`;
- 12 `reportArgumentType`;
- 2 `reportIndexIssue`;
- 2 `reportGeneralTypeIssues`;
- 1 `reportReturnType`.

Generated ANTLR files remained isolated by the existing targeted
`src/pietto/generated` configuration. They were not edited.

## Cleanup

The test-only cleanup uses:

- narrow `TypedDict` views for CLI JSON assertions;
- explicit `ParseResult` helper parameters;
- exact AST and IR `isinstance` narrowing;
- constrained generic helpers for retrieving specific AST and IR nodes;
- explicit non-`None` checks for optional headers, clauses, and expressions;
- dataclass narrowing before reflection;
- mutable `dict` casts only where tests intentionally exercise readonly
  mappings;
- explicit `StaticValue` annotations for parametrized SQL literal tests;
- direct `importlib.util.find_spec` imports.

No broad ignore, global diagnostic override, or production type-checking
reduction was added.

## Gate Boundary

The mandatory `uvx pyright` command remains the Phase 9.5 gate for handwritten
production source in standard mode. `pyrightconfig.tests.json` provides an
explicit non-blocking test command:

```bash
uvx pyright --project pyrightconfig.tests.json
```

The test suite is now clean enough to be considered for a future mandatory
gate, but this slice does not change CI or the required production gate.

## Result

The final test configuration analyzes 78 test files with zero errors and zero
warnings. The ordinary production configuration also remains at zero errors
and zero warnings.

Phase 9.6 changes no production source, generated ANTLR file, grammar,
dependency, lockfile, language behavior, CLI or JSON contract, SQL output,
semantic or IR behavior, public API, or runtime capability.
