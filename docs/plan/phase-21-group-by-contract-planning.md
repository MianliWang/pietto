# Phase 21 GROUP BY Contract Planning

## Status

Phase 21 Slice 1 is complete as baseline and candidate decision work only.
It is docs/audit only. It does not implement GROUP BY or any compiler
behavior.

Trusted Phase 20 baseline:

- HEAD: `e67bf35cc130332aeb786a913fa5d76dac00fca9`;
- no-GROUP `count()`, `sum(field)`, and `avg(field)` aggregate MVP is
  complete;
- semantic validation, Semantic IR lowering, PostgreSQL SQL lowering, and
  MySQL SQL lowering are complete for that MVP;
- reviewed SQL goldens and the Phase 20 completion audit are complete.

Phase 21 Slice 1 adds no grammar/generated, AST, semantic, IR, SQL, CLI, JSON,
fixture, golden, dependency, CI, runtime, UI, LSP, policy DSL, or database
behavior change.

## Strategic Priority

Pietto prioritizes core language capability. The goal is a powerful, concise,
easy-to-use, safe, typed, SQL-native DSL, not only CLI polish or packaging.

Syntax design quality is central. Pietto syntax should remain readable,
Python-indentation-friendly, diagnostic-first, and fail-closed. The language
should preserve explicit SQL-native semantics while avoiding casual syntax
drift.

The current source syntax remains:

- `source name: Shape is connector`;
- `alias = expression` for select aliases;
- no Pietto source-level `AS`;
- no `source name: Shape = connector` syntax.

## Candidate Comparison Summary

| Candidate | Summary | Phase 21 Slice 1 outcome |
|---|---|---|
| GROUP BY aggregate syntax and semantic contract | Highest-value next core-language step after no-GROUP aggregates. It can define grouped aggregate source shape, clause scope, output schema rules, unsupported cases, and fail-closed diagnostics before implementation. | Chosen as the next core language direction. Contract planning only. |
| GROUP BY implementation MVP | High user value, but it would touch grammar, AST, semantic analysis, Semantic IR, PostgreSQL/MySQL SQL, diagnostics, fixtures, and goldens. | Deferred until the syntax and semantic contract is complete and separately authorized. |
| Result predicate / HAVING-like design | Useful after grouped aggregates, but result-scope lookup, aggregate aliases, and backend lowering shape are not settled. Pietto should not expose SQL HAVING as user syntax. | Deferred. No `satisfying`, post-select `where`, `such that`, `filter`, or SQL HAVING user syntax is implemented. |
| Aggregate expression arguments | Valuable future expressiveness such as `sum(amount + tax)`, but it changes aggregate argument typing and SQL rendering. | Deferred. Direct field arguments remain the completed MVP boundary. |
| Relationship-driven safe composition / JOIN planning | Strategically important but crosses multi-input scope, fanout, ambiguity, relationship authority, and SQL shape boundaries. | Deferred. Relationship metadata remains read-only metadata and not query behavior. |
| Nested table / structured result planning | Potentially useful but less immediate than grouped SQL-native aggregates and likely dialect-sensitive. | Deferred. No nested table or structured result semantics are introduced. |
| Project / multi-file language organization | Important for scale, but it is workflow and compiler orchestration rather than the strongest next query-language capability. | Deferred. No project configuration, project mode, or multi-file behavior is implemented. |
| CLI/docs/examples usability fallback | Useful non-core fallback, especially for status and examples, but it should not displace core language capability. | Deferred as a fallback only. Slice 1 adds only this candidate decision audit surface. |

## Decision

Phase 21 selects **GROUP BY aggregate syntax and semantic contract** as the
next core language direction.

This decision does not implement GROUP BY. Implementation is explicitly
deferred. Slice 1 does not change accepted source syntax, grammar, generated
ANTLR files, AST nodes, parser behavior, semantic analysis, Semantic IR,
PostgreSQL or MySQL SQL rendering, CLI behavior, JSON output, public APIs,
fixtures, SQL goldens, dependencies, CI, runtime behavior, database behavior,
or relationship-driven query behavior.

The selected direction is a contract-first path because GROUP BY affects
clause order, expression scope, aggregate validation, row schema propagation,
IR representation, SQL lowering, diagnostics, and SQL byte stability. Those
decisions must be reviewed before any implementation slice.

## Proposed Future Phase 21 Slices

1. **Slice 1: Baseline And Candidate Decision**: complete as docs/audit only.
   Record the trusted Phase 20 baseline, compare candidate directions, select
   GROUP BY contract planning, and explicitly defer implementation.
2. **Slice 2: Syntax And Clause-Scope Contract**: future planning slice.
   Define the exact future GROUP BY source shape, clause order, group-key
   scope, select projection rules, and syntax constraints without compiler
   implementation.
3. **Slice 3: Semantic / IR / SQL / Diagnostics Contract**: future planning
   slice. Define future semantic validation, row-schema behavior, IR shape,
   selected-dialect SQL shape, diagnostic ownership, and fail-closed
   unsupported behavior without implementation.
4. **Slice 4: Completion Audit And Status Lock**: future audit slice. Verify
   the Phase 21 planning boundary and prove no unauthorized compiler,
   runtime, database, or broad documentation behavior was added.

## Explicit Out Of Scope

Phase 21 Slice 1 does not implement or authorize:

- GROUP BY implementation;
- grammar or source syntax changes;
- generated ANTLR changes;
- parser or AST changes;
- semantic model changes;
- Semantic IR model, export, builder, or lowering changes;
- PostgreSQL or MySQL SQL renderer changes;
- CLI, JSON, or public API changes;
- fixture, SQL golden, or `scripts/check_goldens.py` changes;
- dependency, package, lockfile, or CI changes;
- README, AGENTS, `docs/spec/pietto-v0.9.md`, or
  `docs/spec/diagnostics.md` changes;
- runtime or database execution;
- connector execution or schema introspection;
- relationship-driven query behavior;
- JOIN or relation composition;
- SQL HAVING user syntax;
- `satisfying`, `filter`, post-select `where`, or `such that`
  implementation;
- aggregate expression argument implementation;
- Decimal aggregate semantics;
- casts;
- project configuration or multi-file implementation;
- UI, playground, or LSP implementation;
- policy DSL or runtime security implementation.

Unsupported future behavior must remain diagnostic-first and fail-closed when
it is eventually authorized. Existing Phase 20 no-GROUP aggregate behavior and
SQL bytes remain the compatibility baseline.
