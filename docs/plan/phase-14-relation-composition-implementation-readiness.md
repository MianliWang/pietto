# Phase 14: Relation Composition Implementation Readiness

## Status

**Phase 14 Slice 1: Final Transition Readiness Gate is complete.**

**Phase 14 Slice 2: First Implementation Candidate Decision is complete.**

**Phase 14 implementation has not started.**

**Slices 3 through 4 require separate explicit authorization.**

Slice 1 is planning-only. It creates the final broad readiness gate between
the completed Phase 13 planning contracts and a future narrowly authorized
implementation. It adds no accepted Pietto syntax and changes no grammar,
generated ANTLR content, parser, AST, semantic analysis, IR, SQL backend, CLI,
JSON, runtime, dependency, public API, package metadata, version, CI, or
golden behavior.

Phase 14 must not become another broad planning phase. Phase 13 already
completed the major relation-composition planning, contract, and audit work.
Slice 2 chose the relationship and endpoint metadata syntax foundation and
defined the exact proposed boundary for Slice 3. The candidate decision is
documented in
`docs/plan/phase-14-first-implementation-candidate-decision.md`.

## Inputs And Preserved Baseline

This readiness gate uses the following completed Phase 13 artifacts as
immutable planning inputs:

- `docs/plan/phase-13-relation-composition-planning.md`;
- `docs/spec/relationship-relation-role-contract-v1.md`;
- `docs/spec/composition-scope-name-resolution-contract-v1.md`;
- `docs/spec/composition-sql-shape-contract-v1.md`;
- `docs/spec/composition-security-diagnostics-contract-v1.md`;
- `tests/test_phase13_completion_audit.py`.

Phase 13 remains complete as planning, contract, and audit work only. Its
conceptual terms are not accepted syntax, final grammar terms, keywords,
reserved words, runtime capabilities, or security guarantees.

The preserved implementation baseline remains:

- `.pietto` is the only official source suffix;
- JSON schema version 1 is the only runtime CLI JSON schema;
- diagnostic families remain `PIE-Pxxxx`, `PIE-Sxxxx`, `PIE-Ixxxx`, and
  `PIE-Bxxxx`;
- the public SQL API exposes `pietto.sql.emit_postgres_sql`;
- `pietto.sql.mysql.emit_mysql_sql` remains private;
- no generic public `emit_sql(...)` exists;
- current `ORDER BY` resolution remains input-scope only, and projection
  aliases do not enter that scope;
- the production dependency remains exactly
  `antlr4-python3-runtime>=4.13.2`;
- the package version remains `0.1.0`;
- the 15 reviewed golden files remain unchanged;
- CI remains the existing Python 3.12 and 3.13 validation workflow with
  read-only repository permissions and Node 24-compatible checkout.

## Why The Next Step Is Not JOIN

Relation composition crosses grammar, source spans, scope ownership,
diagnostics, IR, selected-dialect SQL lowering, PostgreSQL/MySQL parity,
cardinality, fanout, and security-claim boundaries. A direct JOIN
implementation would force several unresolved decisions into one change and
could turn Pietto into a generic SQL builder.

The first real implementation candidate must therefore establish one narrow
foundation without combining relations or emitting new SQL. It must preserve
the existing single-input query model and leave cardinality, fanout, SQL
shape, and runtime concerns unimplemented.

## Fixed Four-Slice Transition

Phase 14 has four slices. Slice 1 is the only broad readiness slice.

1. **Final Transition Readiness Gate**: complete. Record the immutable Phase
   13 inputs, two concrete candidate directions, required decision output,
   implementation gates, compatibility locks, and hard non-goals.
2. **First Implementation Candidate Decision**: complete. Slice 2 chose the
   relationship and endpoint metadata syntax foundation, deferred the
   ambiguity and name-ownership foundation, and fixed a decision-complete
   proposed boundary for Slice 3 without implementing the candidate.
3. **Explicitly Authorized Minimal Vertical Slice**: planned and
   unauthorized. Implement only the candidate and file boundary approved
   after Slice 2 review. Authorization for Slice 1 or Slice 2 does not
   authorize this slice.
4. **Backend Compatibility And Completion Audit**: planned and unauthorized.
   Verify the resulting narrow implementation, unchanged backend behavior
   where required, compatibility locks, and all still-deferred capabilities.

No additional broad planning-only slices should be inserted between Slice 2
and the explicitly authorized implementation decision.

## Two Candidate Directions

Slice 1 did not choose between these candidates. Slice 2 chose the
relationship and endpoint metadata syntax foundation and deferred the
ambiguity and name-ownership foundation for the first implementation slice.

| Candidate | Value | Risk | Surface area | Testability |
|---|---|---|---|---|
| Relationship and endpoint metadata syntax foundation | Establishes a concrete source representation for future static relationship metadata and gives source spans an explicit owner. | Premature syntax can freeze keywords, declaration shape, endpoint naming, or metadata meaning before semantic use is proven. | Likely grammar, regenerated ANTLR, parser/AST construction, parser tests, and documentation; semantic, IR, SQL, CLI, and JSON should remain unchanged for a parse-only implementation. | Positive and negative parser cases, AST shape, source-span ownership, and unchanged semantic/backend behavior can be tested without JOIN. |
| Ambiguity and name-ownership foundation | Establishes deterministic ownership and ambiguous-name outcomes before multiple relation inputs are introduced. | An internal abstraction can become speculative if it has no precise synthetic inputs, ownership rules, or migration path into semantic analysis. | Likely a small internal resolver or test-only semantic foundation; grammar and AST may remain unchanged, while production semantic integration must be explicitly decided. | Synthetic scope tests can cover unique, unknown, unavailable, and ambiguous ownership without adding relation composition or SQL lowering. |

Neither candidate includes JOIN, multiple relation inputs, composition
predicates, cardinality behavior, SQL shape lowering, backend rendering,
runtime authorization, or database enforcement.

## Required Slice 2 Decision

Slice 2 is complete as a concrete decision slice, not a continuation of
general planning. Its decision document answers every question below for the
selected candidate.

| Required decision | Required output |
|---|---|
| First real implementation candidate | Choose one candidate by name and state why the other is deferred. |
| Files to touch | Provide an exact allowlist of production, generated, test, fixture, and documentation files for Slice 3. |
| Files to keep untouched | Name the compiler stages and repository surfaces that Slice 3 must not modify. |
| Grammar impact | State whether `grammar/Pietto.g4` and generated ANTLR files change. |
| AST impact | State whether AST nodes or AST construction change and define the reviewed shape if they do. |
| Semantic impact | State whether semantic analysis observes, ignores, validates, or remains unaware of the candidate. |
| IR impact | State whether Semantic IR changes; absence of an IR change must be explicit. |
| SQL impact | State whether PostgreSQL or MySQL output changes; the default expectation is no SQL change. |
| CLI and JSON impact | State whether CLI behavior or JSON v1 changes; the default expectation is no change. |
| Deferred behavior | Enumerate the syntax, semantics, diagnostics, composition, backend, runtime, and security behavior that remains unimplemented. |

Slice 2 also defines positive, negative, compatibility, and absence tests for
Slice 3. It does not use an undecided prototype, generic risk register, or
future follow-up as a substitute for these answers.

## Gates Before Slice 3

No implementation may start until all of the following are reviewed:

- one candidate is selected and the other is explicitly deferred;
- the exact Slice 3 file allowlist and untouched-file boundary are fixed;
- grammar impact and generated-file provenance are decided;
- any AST shape and source-span ownership are reviewed;
- semantic scope and name-ownership effects are decided;
- IR inclusion or exclusion is explicit;
- SQL backend non-impact or fail-closed behavior is explicit;
- PostgreSQL/MySQL parity expectations are explicit;
- diagnostic family ownership is decided without reserving a code in Slice 1;
- parser, semantic, compatibility, and absence tests are enumerated;
- fixture and golden policy is explicit;
- JSON v1 and public API compatibility are confirmed;
- no runtime or security claim is introduced;
- CI and all local validation commands pass;
- the complete actual diff is reviewed before commit.

## Hard Non-Goals For Slice 1

Slice 1 does not add or authorize:

- JOIN or relation composition;
- multiple relation inputs, composition predicates, CTEs, or subqueries;
- SQL shape implementation or backend composition lowering;
- relationship, endpoint, relationship-role, or relation-role syntax;
- relationship metadata semantics or cardinality enforcement;
- a relation alias or qualifier syntax;
- a permission gate, runtime authorization, or runtime security;
- access control, privacy enforcement, database grants, row-level security,
  masking, policy isolation, or safe data sharing;
- a threat model or security guarantee;
- a new diagnostic code or diagnostic-code reservation;
- SQL execution, database or connector connection, or schema introspection;
- JSON v2, project mode, multi-file behavior, watch mode, LSP, Web UI, or a
  playground;
- SQLGlot or another dependency;
- a public MySQL emitter or generic public SQL emitter;
- release, publish, deployment, signing, upload, or attestation behavior.

Any safety language in this plan describes future compiler decision gates
only. Pietto currently does not enforce authorization, privacy, row-level
security, masking, policy isolation, or safe data sharing.

## Compatibility Locks

For Slice 1:

- production code is unchanged;
- grammar and generated ANTLR files are unchanged;
- parser, AST, semantic, IR, and both SQL backends are unchanged;
- SQL artifacts and all golden bytes are unchanged;
- CLI behavior and JSON schema version 1 are unchanged;
- dependencies, `pyproject.toml`, and `uv.lock` are unchanged;
- package metadata and version are unchanged;
- public APIs are unchanged;
- the PostgreSQL emitter remains public and the MySQL emitter remains private;
- CI and workflow permissions are unchanged;
- `.pietto` remains the only official source suffix.

The Slice 1 static audit locks these bytes and boundaries. A later Slice 3 may
change only the exact surfaces approved by the Slice 2 decision and a new
explicit implementation authorization.

## Handoff

Slice 2 selected the relationship and endpoint metadata syntax foundation and
deferred the ambiguity and name-ownership foundation. The exact proposed
Slice 3 allowlist, stage impacts, tests, and untouched boundaries are in
`docs/plan/phase-14-first-implementation-candidate-decision.md`.

Slice 2 did not implement either candidate. Slice 3 remains unauthorized
until its exact boundary is reviewed and explicitly approved. Relation
composition, JOIN, SQL shape lowering, runtime security, database behavior,
and all other hard non-goals remain deferred.
