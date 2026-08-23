# Phase 52 Private Capability Key, Disposition, Evidence, And Fact Foundation v1

## Status And Authority

This contract defines Phase 52 Slice 2 only. It adds a private, descriptive,
non-authoritative capability fact foundation. It does not change accepted
Pietto programs, compiler decisions, diagnostics, IR, SQL, CLI, JSON, project
behavior, runtime behavior, database behavior, or any public API.

The source owner is
`src/pietto/semantic/capability_facts.py`. The module is stdlib-only, exports
nothing through `__all__`, is not re-exported by `pietto.semantic`, and is not
consumed by any current compiler or presentation layer.

## Private Module And Exact Vocabulary

The module defines exactly five private `StrEnum` vocabularies.

`CapabilityDomain` has exactly:

- `LOGICAL_TYPE = "logical_type"`;
- `LITERAL = "literal"`;
- `PARAMETER = "parameter"`;
- `SCALAR_FUNCTION = "scalar_function"`;
- `UNARY_OPERATOR = "unary_operator"`;
- `BINARY_OPERATOR = "binary_operator"`;
- `COMPARISON = "comparison"`;
- `NULL_TEST = "null_test"`;
- `CLAUSE = "clause"`;
- `AGGREGATE = "aggregate"`;
- `EXPRESSION_STAGE = "expression_stage"`;
- `CONVERSION = "conversion"`;
- `DIALECT_LOWERING = "dialect_lowering"`;
- `EXTENSION_SIGNATURE = "extension_signature"`.

`CapabilitySupport` has exactly `SUPPORTED = "supported"` and
`EXPLICITLY_UNSUPPORTED = "explicitly_unsupported"`.

`CapabilityDispositionKind` has exactly `NONE = "none"`,
`DEFERRED = "deferred"`, and `OUT_OF_SCOPE = "out_of_scope"`.

`CapabilityEvidenceSource` has exactly `GRAMMAR_AST = "grammar_ast"`,
`SEMANTIC_CATALOG = "semantic_catalog"`,
`SEMANTIC_PROCEDURE = "semantic_procedure"`,
`SEMANTIC_MODEL = "semantic_model"`, `IR = "ir"`, `BACKEND = "backend"`,
`PROJECT = "project"`, `PUBLIC = "public"`, `ROADMAP = "roadmap"`,
`TEST = "test"`, and `SPEC = "spec"`.

`CapabilityReasonCode` has exactly `NO_CATALOG_ENTRY = "no_catalog_entry"`,
`NOT_EVIDENCED = "not_evidenced"`,
`NO_CURRENT_RESULT_RULE = "no_current_result_rule"`,
`UNRESOLVED_EXPRESSION = "unresolved_expression"`,
`NULL_LITERAL_NO_CONCRETE_TYPE = "null_literal_no_concrete_type"`,
`UNKNOWN_NULLABILITY = "unknown_nullability"`,
`SQL_THREE_VALUED_TRUTH = "sql_three_valued_truth"`,
`DIALECT_LOWERING_GAP = "dialect_lowering_gap"`,
`CONFLICTING_EVIDENCE = "conflicting_evidence"`,
`EXTENSION_CATALOG_UNDECLARED = "extension_catalog_undeclared"`,
`EXTENSION_CATALOG_SELECTION_AMBIGUOUS = "extension_catalog_selection_ambiguous"`,
`EXTENSION_CATALOG_SELECTION_CONFLICT = "extension_catalog_selection_conflict"`,
`EXTENSION_CATALOG_TARGET_MISMATCH = "extension_catalog_target_mismatch"`,
`EXTENSION_CATALOG_NOT_PROVIDER_ELIGIBLE = "extension_catalog_not_provider_eligible"`,
`EXTENSION_CATALOGED_UNMODELED = "extension_cataloged_unmodeled"`,
`EXTENSION_CATALOG_COMPLETENESS_INCOMPLETE = "extension_catalog_completeness_incomplete"`,
`EXTENSION_CATALOG_COMPLETENESS_CONFLICT = "extension_catalog_completeness_conflict"`,
and `EXTENSION_CATALOG_COMPLETENESS_UNAVAILABLE = "extension_catalog_completeness_unavailable"`.

`CONVERSION` is reserved vocabulary and receives no Slice 2 fact. None of the
reason codes is a `PIE-*` diagnostic or public identifier.

## Capability Key Contract

`CapabilityKey` is a frozen, slots dataclass with this exact field order:

```python
domain: CapabilityDomain
subject: str | None = None
operation: str | None = None
operands: tuple[str, ...] = ()
context: str | None = None
dialect: str | None = None
extension: str | None = None
```

The domain is an exact enum member. At least one of `subject` and `operation`
is present. Every present text and every operand is an exact, nonempty,
non-whitespace `str`; values are never stripped, lowercased, casefolded, or
otherwise normalized. Operands are defensively frozen to a tuple, preserve
caller order, may repeat, and are identity-significant. `extension` requires
`dialect`. Backend implementation identity is not a key dimension.

Representative identities include logical type `Int`, `lower(Text)`,
`matches(Text, Text)`, `Int + Float`, and `count()`. These examples describe
keys only and populate no registry or fact.

## Current Support And Roadmap Disposition

`CapabilitySupport` records only exact-current evidenced posture. It does not
grant compiler authority and does not imply lowering, portability, roadmap
priority, or lookup presence.

`CapabilityDisposition` is a frozen, slots dataclass with exact fields:

```python
kind: CapabilityDispositionKind
owner: str | None = None
reason: str | None = None
```

`NONE` is valid if and only if owner and reason are both absent. `DEFERRED` and
`OUT_OF_SCOPE` each require exact nonblank owner and reason text. Partial or
blank ownership fails closed. The free roadmap reason is independent from the
bounded `CapabilityReasonCode` vocabulary.

Current support and roadmap disposition are orthogonal. All six combinations
of the two support values and three disposition kinds are structurally valid.

## Atomic Evidence And Generic Fact Contract

`CapabilityEvidence` is a frozen, slots dataclass with exact field order:

```python
source: CapabilityEvidenceSource
source_path: str
source_reference: str
reason: CapabilityReasonCode | None = None
dialect: str | None = None
backend: str | None = None
extension: str | None = None
```

Path and reference are exact nonblank strings and are not filesystem-
normalized. Optional scope text is exact and nonblank. Evidence `extension`
requires evidence `dialect`; backend is independent provenance and does not
infer a dialect. Test nodes and specification headings are atomic `TEST` and
`SPEC` evidence entries, not nested pointers on another authority.

`CapabilityFact` is the single generic frozen, slots composition carrier:

```python
key: CapabilityKey
support: CapabilitySupport
disposition: CapabilityDisposition
evidence: tuple[CapabilityEvidence, ...]
```

Evidence is defensively tuple-frozen, nonempty, exact-entry typed, ordered,
and equality-significant. Exact duplicate entries fail closed; distinct
disagreeing entries remain in caller order. The fact does not compare key and
evidence scope, choose a winner, or infer support or disposition.

## Bounded Reason-code Contract

The 18 reason codes are private evidence and lookup-ready vocabulary. They
are not all one lookup outcome. In particular:

- `NO_CATALOG_ENTRY` is vocabulary for a later absent result;
- `NOT_EVIDENCED` and `NO_CURRENT_RESULT_RULE` describe bounded uncertainty;
- `UNRESOLVED_EXPRESSION` is distinct from a null literal lacking a concrete
  type;
- `UNKNOWN_NULLABILITY` is distinct from SQL three-valued truth;
- `DIALECT_LOWERING_GAP` records backend evidence without deciding semantic
  support;
- `CONFLICTING_EVIDENCE` preserves disagreement without precedence.
- the nine `EXTENSION_CATALOG_*` values preserve distinct Slice 8 selection,
  target, eligibility, unmodeled, and completeness uncertainty without adding
  a lookup-result variant.

Slice 3 owns the later admissibility of reasons for lookup result variants.

## Structural Invariants And Determinism

All four carriers are frozen and slots-based with default `order=False`.
Stored fields are enums, exact strings, `None`, tuples, or other frozen
carriers, so equality and hashing are stable. No comparison method, explicit
sort key, mutable container, mapping payload, or arbitrary note is added.

Local construction invariants raise `ValueError`. They validate private
carrier shape only and never validate a Pietto program. Character strings are
not accepted as tuple-input iterables. Valid padded text remains byte-exact.

## Privacy And No-behavior Boundary

The module has `__all__: tuple[str, ...] = ()`, uses only `dataclasses` and
`enum` plus `__future__`, and creates no module-level carrier instance,
registry, catalog, mapping, builder, lookup function, or import-time mutation.

There is no re-export or consumer in the semantic analyzer, semantic compiler
procedures, IR, SQL backends, CLI, JSON, metadata serializers, `_project`,
runtime, or database code. Direct focused-test import from the dedicated
module does not create a public API.

This slice adds no `Found`, `Absent`, `Unknown`, `Conflict`,
`CapabilityLookupResult`, concrete Slice 4-7 fact family, serializer, public
identifier, or diagnostic. Existing compiler procedures remain the sole
behavior authority.

## Conflict-ledger Preservation

Slice 2 resolves none of the eight current conflicts:

1. `count(alias/Shape)`;
2. semantic `LIKE` versus PostgreSQL/private MySQL lowering;
3. `matches(Text, Text)` dialect posture;
4. non-Decimal type arguments;
5. division `/`;
6. null literal versus unresolved-expression unknown carriers;
7. generic comparison compatibility;
8. global aggregate post-filtering.

The carriers may later retain evidence and reasons about these conflicts, but
Slice 2 populates no facts, selects no precedence, and changes no outcome.

## Slice Ownership And Validation Locks

Slice 2 owns only the private key, support, disposition, evidence, generic
fact, and bounded reason-code foundation plus focused tests and compatibility
hash refreshes. Slice 3 owns fail-closed lookup results and precedence.
Slices 4-7 own concrete fact families and population. Later slices own parity,
privacy closure, and completion audit.

The compiler boundary grows only because the private module becomes a packaged
source input. The direct semantic group and the Phase 15 semantic subset grow
by that same file. This inventory/hash change adds no compiler behavior.

Grammar, generated ANTLR, AST, parser, analyzer, `SemanticModel`, IR, SQL,
diagnostics, CLI, JSON v1, Project JSON v2, Semantic Metadata Artifact v1,
fixtures, goldens, examples, workflows, dependencies, lockfile, package
version, tags, releases, publication, signing, and attestation remain
unchanged. Package version remains `0.1.0`.
