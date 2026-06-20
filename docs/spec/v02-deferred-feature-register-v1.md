# v0.2 Deferred Feature Register v1

## Status

Phase 29 Slice 2 is complete as a deferred-feature register contract and
static audit slice only.

This register records features that are outside the v0.2 stable single-file
typed SQL authoring compiler boundary. It does not authorize implementation,
syntax, public API changes, CLI behavior changes, JSON v1 changes, JSON v2,
IR behavior changes, SQL lowering changes, semantic behavior changes,
aggregate behavior changes, runtime execution, schema introspection, project
or multi-file behavior, relationship/JOIN behavior, public MySQL API expansion,
DateTime primitives, Currency/Money primitives, or semantic annotation syntax.

The allowed-before-v0.2 column uses exactly these categories:

- bug fixes only;
- contracts/tests only;
- readiness or narrow-MVP decision only;
- Phase 30/31 stabilization only if explicitly approved;
- no before v0.2.

## Register

| Feature | Why deferred | Blocking prerequisites | Unfreeze condition | Target | Allowed before v0.2 | Explicit non-goals |
|---|---|---|---|---|---|---|
| Aggregate expansion | Phase 19 through Phase 28 aggregate work is frozen for v0.2 to stop aggregate churn. | Phase 30/31 aggregate result, scalar type, and dialect matrix stabilization. | After v0.2 or by explicit bug-fix exception that does not expand the aggregate surface. | v0.3+ | bug fixes only | No new aggregate functions, modifiers, filters, window functions, `count(expression)`, `min(expression)`, or `max(expression)`. |
| Numeric expression expansion | Operator, comparison, numeric promotion, and Decimal semantics are not yet fully contracted. | Phase 30 operator/comparison and Decimal contracts, plus Phase 31 numeric boundary tests. | Phase 30/31 matrices are complete and a later implementation slice is approved. | Phase 31+/v0.3 | contracts/tests only | No division, modulo, casts, mixed promotion widening, Decimal widening, or scalar-expression feature expansion. |
| DateTime/timezone/Time/Interval | Pietto has no portable temporal model beyond current `Date` and `Timestamp` names. | Phase 30 Date/Timestamp formalization and cross-dialect temporal compatibility decisions. | A later temporal contract approves a portable model after Date/Timestamp stabilization. | v0.3+ | no before v0.2 | No `DateTime`, timezone, `Time`, or `Interval` primitive and no temporal arithmetic. |
| UUID | `UUID` exists as a built-in name, but SQL behavior and dialect compatibility are not stabilized. | Canonical scalar registry and Phase 31 UUID readiness or narrow-MVP decision. | Phase 31 accepts a UUID readiness or narrow-MVP contract. | Phase 31 decision | readiness or narrow-MVP decision only | No UUID functions, casts, literals, storage semantics, DDL, or SQL behavior. |
| Enum | Enum syntax/metadata exists, but enum SQL behavior is not stabilized. | Canonical scalar registry and Phase 31 enum readiness or lowering decision. | Phase 31 accepts an enum readiness, narrow-MVP, or explicit deferral decision. | Phase 31+ | readiness or narrow-MVP decision only | No enum DDL, runtime mapping, SQL lowering, value validation changes, or public API changes. |
| Decimal precision/scale | Current type facts have no precision/scale carrier or propagation contract. | Phase 30 Decimal precision/scale contract and Phase 31 Decimal boundary tests. | Phase 30/31 explicitly approve precision/scale stabilization work. | Phase 30/31 | Phase 30/31 stabilization only if explicitly approved | No Decimal syntax, carriers, semantic behavior, SQL behavior, precision propagation, or widening in Slice 2. |
| Native DB type metadata | Native database metadata would bind Pietto to physical schemas before dialect contracts are stable. | Dialect source metadata contract and stable type registry. | A later native metadata phase is approved with explicit dialect scope. | v0.3+ | no before v0.2 | No physical schema binding, native type annotations, connector metadata, or DDL behavior. |
| DB pull/schema introspection | Schema introspection crosses the runtime/database boundary. | Runtime threat model, connector auth policy, resource limits, and source metadata contract. | A separate runtime/introspection authorization phase is approved. | post-v0.2 | no before v0.2 | No network calls, database connections, credential handling, DB pull, schema import, or introspection behavior. |
| Prisma bridge | External ecosystem integration depends on stable schema, project, and type contracts. | Stable type registry, project model, schema metadata, and dependency review. | A dedicated bridge plan approves integration scope and dependency policy. | v0.4+ | no before v0.2 | No Prisma dependency, code generation, schema conversion, or CLI bridge behavior. |
| Project/multi-file | v0.2 is a single-file compiler boundary. | Project loader, path model, config model, cross-file semantics, and JSON v2 approval. | A separate project/multi-file implementation phase is approved. | post-v0.2 | no before v0.2 | No `--project`, imports, modules, root discovery, config loading, or multi-file JSON output. |
| Relationship/JOIN | Relationship querying crosses composition, ambiguity, fanout, and SQL shape boundaries. | Relationship composition contract, JOIN SQL shape contract, and name-resolution authority. | A separate relationship query/JOIN implementation phase is approved. | post-v0.2 | no before v0.2 | No JOIN implementation, relation composition, endpoint-qualified lookup, or relationship-aware querying. |
| Relationship cardinality/grain/fanout diagnostics | Cardinality and fanout diagnostics require relationship-aware query semantics. | Relationship/JOIN model, grain model, and diagnostic contract. | Relationship query design is accepted and diagnostic scope is explicitly approved. | post-v0.2 | no before v0.2 | No fanout analysis, grain inference, cardinality warnings, or BI-style relationship diagnostics. |
| Semantic/domain annotations | Domain annotations require a stable type system and annotation syntax contract. | Core type-system stabilization, annotation contract, and syntax approval. | A later annotation phase approves syntax and metadata semantics. | v0.3+ | no before v0.2 | No money, currency_code, email, percent, unit, country_code syntax; Money and Currency are not primitive scalar types. |
| Explain/audit output | Explain/audit output needs a separate output contract and CLI/JSON stability decision. | v0.2 boundary, diagnostic model, output contract, and JSON/API decision. | A later explain/audit contract is accepted. | v0.3+ | contracts/tests only | No `pietto explain`, audit JSON, provenance output, CLI option, or JSON v2 output. |
| LSP/playground | Editor and playground tooling need stable project, source, and diagnostic models. | v0.2 compiler stability, project/source model, and diagnostic transport contract. | A tooling phase approves editor/server/playground scope. | post-v0.2 | no before v0.2 | No LSP server, playground, web UI, file watching, or editor protocol behavior. |
| Runtime/database execution | Pietto remains a SQL authoring compiler, not an execution runtime. | Runtime threat model, connector auth, transaction policy, execution policy, and resource controls. | A separate runtime authorization phase is approved; not part of v0.2. | not v0.2 | no before v0.2 | No SQL execution, connector execution, transactions, database connections, credential handling, or runtime services. |
| Arrow/dataframe integration | Dataframe integration requires data materialization and dependency policy decisions. | Runtime/data model, Arrow dependency review, and execution/materialization contract. | A dedicated integration plan approves scope and dependencies. | v0.4+ | no before v0.2 | No Arrow/PyArrow dependency, dataframe API, data export, or materialized execution path. |

## Register Non-Goals

This register does not implement any deferred feature. It also does not reserve
new syntax, add keywords, change accepted grammar, add diagnostics, alter JSON
v1 output, implement JSON v2, expose a public MySQL API, add runtime execution,
add schema introspection, add project/multi-file behavior, add relationship or
JOIN behavior, add DateTime primitives, add Currency/Money primitives, add
semantic annotation syntax, or expand aggregate behavior.
