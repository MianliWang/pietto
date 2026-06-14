# Phase 16: Language Direction And Safety Mode

## Status

**Phase 16 Slice 1: Language Direction and Syntax Philosophy is complete as
design, specification, and audit work only.**

**Phase 16 Slice 2: Safety Surface Deferral and SQL Portability Contract is
complete as design, specification, and audit work only.**

**Phase 16 Slice 3: Current Syntax Surface Audit is complete as
syntax-surface audit only.**

**Phase 16 Slice 4: Phase 16 Completion Audit is complete as final audit and
status work only.**

**Phase 16 Language Direction And Safety Mode is complete as design,
specification, and audit work only.**

Phase 16 introduced no accepted syntax changes. Phase 16 introduced no
compiler, runtime, or database behavior changes. Future work requires
separate explicit authorization; Phase 16 completion does not authorize Phase
17 or any production implementation automatically.

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

The Slice 2 portability and deferral contract is
`docs/spec/safety-deferral-and-sql-portability-v1.md`. It re-centers future
design on lossless lowering within explicit dialect subsets and keeps
speculative safety and policy syntax deferred.

The Slice 3 syntax inventory is
`docs/spec/current-syntax-surface-audit-v1.md`. It records the accepted
grammar and parser surface without changing or authorizing syntax.

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

## Slice 2: Safety Surface Deferral and SQL Portability Contract

Slice 2 is complete as design, specification, and audit work only. It adds
only:

- `docs/spec/safety-deferral-and-sql-portability-v1.md`;
- `tests/test_phase16_safety_deferral_sql_portability.py`;
- this plan and minimal status-document updates;
- the necessary fixed plan hash and Slice 2 status adjustment in the Slice 1
  audit.

The contract prioritizes deterministic, lossless lowering within documented
dialect subsets, explicit backend contracts, reviewed SQL goldens, no silent
semantic approximation, and fail-closed unsupported behavior. It defers
exposure, purpose, permission, authority, capability-token, Rust-like
`impl`/evidence, and new safety/policy strict-mode syntax or implementation.
The existing compile-time `mode strict` vocabulary remains unchanged and is
not redefined as policy or runtime security.

Relationship metadata remains frozen as secondary read-only metadata. Slice 2
adds no relationship composition, JOIN lowering, endpoint-qualified lookup,
role enforcement, security model, mode, CLI option, parser form, semantic
rule, diagnostic code, runtime guarantee, or database behavior.

## Slice 3: Current Syntax Surface Audit

Slice 3 is complete as syntax-surface audit only. It adds only:

- `docs/spec/current-syntax-surface-audit-v1.md`;
- `tests/test_phase16_current_syntax_surface_audit.py`;
- this plan and minimal status-document updates;
- necessary fixed plan hash and Slice 3 status adjustments in the prior
  Phase 16 audits.

The audit inventories the existing header, definition, relation, relationship
metadata, and expression syntax. It confirms that typed source connector
syntax still uses `is`, existing `mode strict` remains compile-time checking
vocabulary, relationship metadata remains secondary read-only metadata, and
all speculative safety, policy, JOIN, composition, and endpoint-qualified
forms remain deferred and unimplemented.

Slice 3 changes no grammar, generated ANTLR, AST, parser, semantic analysis,
IR, SQL, CLI, JSON, example, fixture, golden, diagnostic code, dependency,
CI, version, package metadata, runtime, or database behavior.

## Slice 4: Phase 16 Completion Audit

Slice 4 is complete as final audit and status work only. It adds only
`tests/test_phase16_completion_audit.py` and completion status documentation.

The final audit byte-locks all three Phase 16 specifications and focused audit
tests. It locks the unchanged grammar, generated ANTLR, AST, parser, semantic
analysis, Semantic IR, SQL backends, CLI, JSON version 1, examples, fixtures,
goldens, public API, dependencies, package metadata, version, CI, runtime,
database, release, and publication boundaries.

Slice 4 adds no language, compiler, runtime, database, diagnostic, dependency,
package, version, or workflow behavior.

## Compatibility Boundary

Phase 16 changes no grammar, generated ANTLR, AST node, AST builder, parser
API, semantic analysis, Semantic IR, PostgreSQL or MySQL backend, CLI, JSON
serializer, example, fixture, golden, public API, dependency, lockfile,
package metadata, version, or CI workflow.

The public SQL API remains PostgreSQL-only. The MySQL emitter remains private
to explicit CLI dispatch. JSON version 1 remains the authoritative
machine-readable CLI interface.

## Deferred Work

Phase 16 Slices 1 through 4 do not implement or authorize strict-mode changes,
relationship-aware querying, JOIN, relation composition, SQL lowering,
aggregates, measures, project workflow, runtime authorization, access control,
privacy enforcement, database connections, connector or SQL execution,
schema introspection, JSON version 2, SQLGlot, a public MySQL emitter, a
generic SQL emitter, release, publication, signing, upload, deployment, or
attestation behavior.

Phase 16 is complete. Every future phase, slice, syntax change, or production
implementation requires separate explicit authorization.
