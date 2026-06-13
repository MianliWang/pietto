# Phase 14 Slice 2: First Implementation Candidate Decision

## Status

**Phase 14 Slice 2 is complete as a candidate decision only.**

**Phase 14 implementation has not started.**

**Slice 3 remains unauthorized until separately reviewed and approved.**

This slice changes no grammar, generated ANTLR content, parser, AST, semantic
analysis, IR, SQL backend, CLI, JSON, runtime, dependency, public API, package
metadata, version, CI, or golden behavior. It defines the exact proposed
boundary for a future implementation slice without implementing that
boundary.

## Inputs

This decision uses the final Slice 1 readiness gate and the completed Phase 13
planning contracts:

- `docs/plan/phase-14-relation-composition-implementation-readiness.md`;
- `docs/plan/phase-13-relation-composition-planning.md`;
- `docs/spec/relationship-relation-role-contract-v1.md`;
- `docs/spec/composition-scope-name-resolution-contract-v1.md`;
- `docs/spec/composition-sql-shape-contract-v1.md`;
- `docs/spec/composition-security-diagnostics-contract-v1.md`;
- `tests/test_phase13_completion_audit.py`;
- `tests/test_phase14_planning_audit.py`.

Those inputs define conceptual and compatibility boundaries only. They do not
provide current relationship syntax, relation-role semantics, composition,
runtime security, or database enforcement.

## Decision

**Chosen candidate: Relationship and endpoint metadata syntax foundation.**

**Deferred candidate: Ambiguity and name-ownership foundation.**

The chosen candidate is a better first implementation step because it adds a
small, observable language-surface foundation with direct parser and AST
tests. Phase 13 already established the conceptual distinction among
relationships, endpoints, roles, cardinality, scope, and runtime security.
A parse-only and AST-only slice can now give future metadata explicit source
ownership without claiming semantic or SQL behavior.

The ambiguity and name-ownership foundation is valuable but deferred. With
the current single-input relation model, it has no production multi-input
scope to resolve. Implementing it first would risk creating an internal
abstraction whose callers, ownership inputs, and semantic integration remain
speculative. It should be reconsidered after relationship metadata has a
reviewed source and AST representation or when a separately authorized
composition slice introduces a concrete multi-scope requirement.

## Candidate Comparison

| Dimension | Relationship and endpoint metadata syntax foundation | Ambiguity and name-ownership foundation |
|---|---|---|
| User-visible value | Adds a small parseable language surface and inspectable AST metadata without promising executable behavior. | Adds no accepted source capability and is visible primarily through internal or synthetic tests. |
| Implementation risk | Moderate and bounded if syntax is minimal, parse-only, and isolated from semantic definitions. | Moderate because an unused resolver can encode premature ownership rules or require later replacement. |
| Grammar risk | Requires a narrowly reviewed grammar addition and keyword or contextual-token decision. | No grammar change is required. |
| AST risk | Requires new immutable metadata nodes, ordered endpoint preservation, and exact source spans. | May avoid public AST changes but needs a stable internal input and result model. |
| Semantic risk | Low only if relationship metadata remains outside the existing semantic definition stream and receives no validation or meaning. | Higher than it appears because choosing resolver inputs and outcomes implicitly shapes future semantic analysis. |
| IR risk | None for the chosen parse-only boundary; relationship metadata must not enter Semantic IR. | None if test-only, but production semantic integration would create a later IR handoff question. |
| SQL and backend risk | None; no SQL artifact, capability, dispatch, or diagnostic changes are allowed. | None initially, though resolver decisions would later constrain qualification lowering. |
| CLI and JSON risk | No command, exit-code, presentation, or JSON v1 schema change is allowed. | No command, exit-code, presentation, or JSON v1 schema change is expected. |
| Testability | Direct positive and negative parsing, AST shape, source-order, source-span, and unchanged pipeline tests. | Synthetic unique, unknown, unavailable, and ambiguous ownership tests without a current source producer. |
| Future query composition usefulness | Establishes source-owned relationship and endpoint metadata that later contracts can validate before composition. | Establishes deterministic ownership logic once multiple visible scopes exist. |
| Future nested semantics usefulness | Provides metadata that can later describe relation boundaries without implementing nested tables. | Could later support nested ownership, but current nested table semantics are absent. |
| Future semantic query core usefulness | Gives a concrete syntax-to-AST input for later semantic contracts while preserving stage isolation. | Gives an internal lookup primitive but not the language facts that populate it. |

The choice does not mean relationship syntax is implemented in this slice.
It selects only the boundary that a separately authorized Slice 3 should
implement.

## Proposed Slice 3 Behavior

The future Slice 3 should add one minimal relationship metadata declaration
surface and preserve it in immutable parse-only AST nodes. The exact accepted
surface must first be fixed in a normative syntax contract. This decision
document does not define final spelling, keywords, punctuation, clauses, or
reserved words.

The future AST boundary should:

- preserve one declaration name;
- preserve exactly two source-ordered endpoints;
- preserve each endpoint's local metadata name and referenced relation name;
- preserve the full declaration span and each endpoint span;
- store relationship metadata separately from the existing semantic
  definition stream so current semantic analysis remains unaware of it;
- use immutable dataclasses consistent with the existing AST;
- preserve an empty default for scripts that contain no relationship
  metadata.

The future parser should accept only the syntax fixed by the Slice 3 syntax
contract and reject malformed declarations deterministically through existing
parser behavior. Slice 3 should not reserve or add a new diagnostic code.

The future `check` and `emit-sql` pipelines must retain their current behavior
for all existing programs. Relationship metadata receives no semantic
validation, no Semantic IR representation, and no SQL artifact. Slice 3 must
not claim that successfully parsing metadata makes a relationship valid,
composable, authorized, cardinality-safe, or executable.

## Exact Proposed Slice 3 Allowlist

Slice 3 may modify only the following files after separate authorization.

### Production And Grammar

- `grammar/Pietto.g4`;
- `src/pietto/ast_nodes.py`;
- `src/pietto/ast_builder.py`.

No other handwritten production file is allowed. In particular,
`src/pietto/parser_api.py`, `src/pietto/errors.py`, every
`src/pietto/semantic/**` file, every `src/pietto/ir/**` file, every
`src/pietto/sql/**` file, `src/pietto/cli.py`, and
`src/pietto/cli_json.py` must remain unchanged.

### Generated ANTLR Files

- `src/pietto/generated/Pietto.interp`;
- `src/pietto/generated/Pietto.tokens`;
- `src/pietto/generated/PiettoLexer.interp`;
- `src/pietto/generated/PiettoLexer.py`;
- `src/pietto/generated/PiettoLexer.tokens`;
- `src/pietto/generated/PiettoParser.py`;
- `src/pietto/generated/PiettoVisitor.py`.

`src/pietto/generated/__init__.py` must remain unchanged. Generated files must
be produced only through the repository generation command and pass the
independent provenance check.

### Focused Tests

- `tests/test_phase14_relationship_metadata_parser.py`;
- `tests/test_phase14_relationship_metadata_completion_audit.py`.

The parser test must cover accepted structure, source order, exact AST fields,
source spans, malformed forms, and compatibility with scripts that contain no
relationship metadata. The completion audit must prove semantic, IR, SQL,
CLI, JSON v1, API, dependency, CI, and golden non-impact.

### Existing Fixed-Hash Audits

The following tests may change only where necessary to replace fixed hashes
affected by the authorized grammar, AST, builder, or generated-file bytes.
Assertions must not be removed, weakened, bypassed, or converted into
unchecked dynamic values.

- `tests/test_phase8_completion_audit.py`;
- `tests/test_phase9_completion_audit.py`;
- `tests/test_phase10_dialect_dispatch_design.py`;
- `tests/test_phase10_mysql_backend_skeleton.py`;
- `tests/test_phase10_completion_audit.py`;
- `tests/test_phase11_planning_audit.py`;
- `tests/test_phase11_ci_workflow.py`;
- `tests/test_phase11_generated_guard.py`;
- `tests/test_phase11_golden_policy.py`;
- `tests/test_phase11_packaging_smoke.py`;
- `tests/test_phase11_validation_entrypoint.py`;
- `tests/test_phase11_completion_audit.py`;
- `tests/test_phase12_planning_audit.py`;
- `tests/test_phase12_order_limit_contract.py`;
- `tests/test_phase12_composition_cli_json_goldens.py`;
- `tests/test_phase12_completion_audit.py`;
- `tests/test_phase13_planning_audit.py`;
- `tests/test_phase13_completion_audit.py`;
- `tests/test_phase14_planning_audit.py`;
- `tests/test_phase14_candidate_decision_audit.py`.

Every changed hash must be explained as the direct result of an authorized
grammar, AST, builder, or generated-file change. Historical semantic, IR,
backend, CLI, JSON, workflow, dependency, package, and golden locks remain
unchanged.

### Documentation

- `docs/spec/relationship-endpoint-metadata-syntax-v1.md`;
- `docs/plan/phase-14-relation-composition-implementation-readiness.md`;
- `docs/plan/phase-14-first-implementation-candidate-decision.md`;
- `README.md`;
- `AGENTS.md`;
- `docs/spec/pietto-v0.9.md`.

The new syntax contract must define the exact minimal accepted surface,
keyword or contextual-token impact, AST mapping, spans, malformed forms,
semantic non-impact, and compatibility rules before implementation is
reviewed.

### Explicitly Untouched Repository Surfaces

Slice 3 must not modify:

- semantic analysis, symbol tables, relation schemas, or name resolution;
- Semantic IR models, builders, or public IR APIs;
- PostgreSQL or MySQL emitters and SQL artifact bytes;
- CLI commands, options, exit codes, output files, or presentation;
- JSON schema version 1 or serialization;
- examples, fixtures, or golden files;
- dependencies, `pyproject.toml`, `uv.lock`, package metadata, or version;
- `.github/workflows/ci.yml`, validation scripts, or Makefile;
- public Python exports or the private MySQL emitter boundary;
- any Phase 13 contract.

If implementation requires any file outside this allowlist, work must stop
and request explicit scope expansion before that file is modified. In short,
work must stop and request explicit scope expansion rather than silently
expanding the allowlist.

## Stage Impact Decision

| Stage or surface | Slice 3 decision |
|---|---|
| Grammar | Yes. Add only the exact minimal declaration surface approved by the syntax contract. |
| Generated ANTLR | Yes. Regenerate the seven listed artifacts; do not edit them manually. |
| Parser and AST builder | AST builder only. Map the new parse tree into immutable metadata nodes and keep metadata outside semantic definitions. |
| AST | Yes. Add parse-only relationship and endpoint metadata nodes plus a backward-compatible empty script collection. |
| Parser API | No change. Existing parser entry points return the extended immutable script. |
| Semantic analysis | No change. No relationship lookup, validation, symbol, role, cardinality, or diagnostic behavior. |
| IR | No change. Relationship metadata does not enter Semantic IR. |
| PostgreSQL and MySQL SQL | No change. No artifact, qualification, JOIN, capability, or backend diagnostic behavior. |
| CLI | No command, option, exit-code, or presentation change. |
| JSON | No schema or serialization change; JSON v1 remains the only runtime contract. |
| Runtime and database | No execution, connection, introspection, authorization, or enforcement behavior. |

## Readiness Gates Before Slice 3

Slice 3 may begin only after explicit approval and review of:

- a normative exact syntax contract;
- keyword, contextual-token, and reserved-word impact;
- ANTLR generation and provenance expectations;
- immutable AST node names, fields, tuple ordering, and defaults;
- declaration and endpoint source-span ownership;
- separation from the semantic definition stream;
- explicit semantic non-impact;
- explicit IR non-impact;
- explicit PostgreSQL/MySQL and artifact-byte non-impact;
- JSON v1, CLI, and public API compatibility;
- positive parser and AST tests;
- negative malformed-form tests using existing parser diagnostics;
- compatibility tests for existing source and empty metadata collections;
- unchanged examples, fixtures, and all 15 goldens;
- necessary fixed-hash updates with an explanation for each;
- full local and CI validation;
- complete actual diff review before commit.

## Hard Non-Goals

Neither this decision slice nor the recommended future Slice 3 authorizes:

- JOIN or relation composition;
- multiple relation inputs, composition predicates, CTEs, or subqueries;
- SQL shape implementation or SQL lowering;
- relationship semantic validation;
- relation-role semantics or endpoint-role enforcement;
- cardinality or fanout behavior;
- measures, dimensions, aggregates, grouping, or HAVING;
- nested table semantics;
- ambiguity or name-ownership resolution;
- permission gates, runtime authorization, or runtime security;
- access control, privacy enforcement, row-level security, masking, policy
  isolation, safe data sharing, or capability or authority tokens;
- a threat model or security guarantee;
- a new diagnostic code or diagnostic-code reservation;
- SQL or connector execution, database connection, or schema introspection;
- JSON v2, project mode, multi-file compilation, watch mode, LSP, Web UI, or
  a playground;
- SQLGlot or another dependency;
- release, publish, deployment, signing, upload, or attestation behavior.

## Handoff

Slice 3 remains unauthorized until this decision and its exact proposed
allowlist are reviewed and separately approved. If approved, Slice 3 must
follow the chosen relationship and endpoint metadata syntax foundation and
remain parse-only and AST-only.

Any need for semantic, IR, SQL, CLI, JSON, runtime, database, dependency,
public API, fixture, golden, CI, or unlisted file changes is a scope expansion
and requires work to stop before modification.
