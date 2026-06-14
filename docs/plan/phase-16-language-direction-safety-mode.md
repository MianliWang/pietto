# Phase 16: Language Direction And Safety Mode

## Status

**Phase 16 Slice 1: Language Direction and Syntax Philosophy is complete as
design, specification, and audit work only.**

**Phase 16 Slice 2: Safety Surface and Strict Mode Contract is planned only.**

**Phase 16 Slice 3: Current Syntax Surface Audit is planned only.**

**Phase 16 Slice 4: Phase 16 Completion Audit is planned only.**

Phase 16 is design and audit work only unless a later request grants separate
explicit implementation authorization. Completion of a planning slice does
not authorize the next slice or any production change.

## Direction

Phase 16 records Pietto's identity as a readable, indentation-based, typed SQL
authoring DSL with a small compiler-safe core, diagnostic-first failures, and
explicit handling of dangerous or ambiguous operations.

The normative language-direction contract is
`docs/spec/language-direction-v1.md`. Its fixed slogan is:

> Simple by default, explicit when dangerous, fail closed on ambiguity.

The phase keeps compile-time checking separate from runtime and database
security claims. It does not turn relationship metadata into the center of
query authoring or authorize relationship-aware query behavior.

## Slice 1: Language Direction and Syntax Philosophy

Slice 1 adds only:

- `docs/spec/language-direction-v1.md`;
- this Phase 16 plan;
- `tests/test_phase16_language_direction_audit.py`;
- minimal status updates in `README.md`, `AGENTS.md`, and
  `docs/spec/pietto-v0.9.md`.

The slice fixes the language identity, syntax-style principles, relationship
metadata position, compile-time versus runtime boundary, equal future
candidate directions, and explicit non-goals. It adds no accepted source
syntax, compiler behavior, diagnostic code, public API, dependency, runtime,
or database capability.

## Slice 2: Safety Surface and Strict Mode Contract

Slice 2 is planned as contract and audit work only. It will inventory the
current safety surface and distinguish existing check-mode behavior from any
future strict-mode concept. It may define design criteria for explicitness,
ambiguity rejection, diagnostic escalation, and compatibility, but it may not
add a mode, CLI option, parser form, semantic rule, diagnostic code, or
runtime guarantee without separate authorization.

## Slice 3: Current Syntax Surface Audit

Slice 3 is planned as audit work only. It will compare the currently accepted
syntax with the language-direction contract, identify consistent and
inconsistent areas, and record candidates for future separately authorized
work. It may not modify grammar, generated ANTLR, AST, parser, semantic
analysis, IR, SQL, CLI, JSON, examples, fixtures, or goldens.

## Slice 4: Phase 16 Completion Audit

Slice 4 is planned as final static audit and status work only. It will lock
the Phase 16 documents, prior-slice audit results, unchanged production
surfaces, public API, JSON version 1, dependencies, package metadata, version,
CI, examples, fixtures, and goldens. It will not implement any language,
compiler, runtime, or database behavior.

## Compatibility Boundary

Phase 16 changes no grammar, generated ANTLR, AST node, AST builder, parser
API, semantic analysis, Semantic IR, PostgreSQL or MySQL backend, CLI, JSON
serializer, example, fixture, golden, public API, dependency, lockfile,
package metadata, version, or CI workflow.

The public SQL API remains PostgreSQL-only. The MySQL emitter remains private
to explicit CLI dispatch. JSON version 1 remains the authoritative
machine-readable CLI interface.

## Deferred Work

Phase 16 Slice 1 does not implement or authorize strict mode,
relationship-aware querying, JOIN, relation composition, SQL lowering,
aggregates, measures, project workflow, runtime authorization, access control,
privacy enforcement, database connections, connector or SQL execution,
schema introspection, JSON version 2, SQLGlot, a public MySQL emitter, a
generic SQL emitter, release, publication, signing, upload, deployment, or
attestation behavior.

Every future implementation requires separate explicit authorization.
