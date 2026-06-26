# Semantic Metadata Artifact Candidate Decision v1

## 1. Status

This document is the Phase 32 Slice 1 candidate-decision contract for Semantic
Metadata Artifact v1.

Slice 1 is complete as docs/spec/static-audit/status work only. Phase 32 has
started, but Phase 32 as a whole is not complete.

## 2. Purpose

Phase 32 selects **Semantic Explain And Metadata Output MVP**.

The purpose of Semantic Metadata Artifact v1 is to provide a future
machine-readable semantic metadata artifact for one accepted Pietto source file.
Slice 1 defines the artifact identity and boundaries only. It does not define
the final JSON schema.

## 3. Trusted Inputs And Non-goals

Trusted handoff:

- Phase 31 is complete;
- Pietto v0.2 single-file stable is complete;
- trusted baseline HEAD is `a2677114269f98c24c250376b3626a7f0178038c`;
- package version remains `0.1.0`.

Slice 1 does not implement `pietto explain`, metadata DTOs, metadata builders,
metadata serializers, text renderers, final JSON property names, source
behavior, grammar changes, generated changes, semantic changes, IR changes, SQL
changes, diagnostic changes, public API changes, tooling changes, dependency
changes, workflow changes, package version changes, or release operations.

## 4. Artifact Identity And Version Domain

The public artifact identity selected for Phase 32 is:

**Semantic Metadata Artifact v1**

This is a separate version domain from:

- existing single-file CLI JSON v1;
- future project-level JSON v2.

Semantic Metadata Artifact v1 is not a change to CLI JSON v1 and is not the
future project JSON v2 contract.

## 5. Approved CLI Direction

The approved target CLI direction is:

```text
pietto explain <file> [--format text|json]
```

Default format is text. JSON is the future normative machine-readable Semantic
Metadata Artifact v1 presentation. Text is derived from the same normalized
artifact.

Phase 32 MVP does not include `--dialect`, `--output`, a project flag, database
options, or runtime options for `explain`.

## 6. Compiler Pipeline Boundary

Explain may use:

```text
parse
-> semantic analysis
-> existing IR construction
-> normalized metadata artifact
```

Explain must not invoke SQL lowering, connector execution, database
connections, SQL execution, or runtime behavior.

## 7. Success And Failure Contract

Metadata is emitted only after parse, semantic analysis, and IR construction all
succeed.

On parse failure, semantic failure, or IR failure, the future explain command
returns diagnostics or error information only. It must not expose partial
definitions, partial relations, partial schemas, partial projections, partial
aggregates, or partial lineage.

Exact success and failure JSON envelope field names are Slice 2 decisions.

## 8. Public Facts Allowed In Artifact v1

Artifact v1 may expose stable semantic metadata facts that are derived from the
accepted single-file compiler pipeline, including:

- source identity posture;
- definition names;
- relation/table/query names;
- input and output row-schema posture;
- field names;
- resolved value type posture;
- effective nullability posture;
- aggregate posture;
- aggregate argument posture;
- aggregate result type posture;
- group, where, satisfying, ordering, and limit posture;
- diagnostics posture;
- narrow direct-field lineage posture.

This section names fact categories only. It does not define exact JSON property
names.

## 9. Internal Facts Not To Expose

Artifact v1 must not expose raw AST node identity, raw `SemanticModel`
implementation shape, raw `SymbolId`, raw `FieldId`, raw IR nodes, connector
literal internals, connector configuration values, credential-like values,
secrets, or raw connector implementation structures.

## 10. Basic Lineage Boundary

Basic lineage is limited to:

- direct source relation and field provenance for direct field projections;
- normalized direct field leaves used by currently supported bounded
  expressions;
- normalized direct field leaves used by currently supported aggregate
  arguments.

Artifact v1 does not include relationship traversal, JOIN lineage, multi-file
lineage, graph lineage, physical database lineage, or runtime lineage.

## 11. Existing CLI JSON v1 Compatibility

Existing `check` and `emit-sql` CLI JSON v1 remains unchanged:

- no new JSON v1 fields;
- no removed JSON v1 fields;
- no JSON v1 field type changes;
- no JSON v1 semantic changes;
- no JSON v1 stream changes;
- no JSON v1 exit-code changes;
- no JSON v1 ordering changes;
- no JSON v1 path-policy changes;
- no JSON v1 artifact/output changes;
- no JSON v1 schema-version changes.

Incompatible changes to existing CLI JSON v1 remain future JSON v2 work.

## 12. Path And Ordering Contract

Phase 32 uses the existing user-supplied string / `str(path)` posture. It does
not canonicalize paths by default, promise absolute paths, promise
project-relative paths, or introduce project-root semantics.

Phase 32 is single-file only. Artifact v1 preserves deterministic source/IR
order and does not define multi-file ordering.

## 13. Relationship/Dialect/Deferred/Security Exclusions

Relationship metadata is not part of Semantic Metadata Artifact v1. Cardinality,
direction, optionality, grain, fanout, traversal, and JOIN remain Phase 34 work.

Artifact v1 has no SQL dialect field and does not describe selected backend
capabilities.

Artifact v1 has no global per-program `deferred` field that serializes roadmap
documentation. Actual unsupported behavior remains represented by compiler
diagnostics.

Artifact v1 must not expose connector secrets or raw connector structures.

## 14. Public API And Tooling Posture

Phase 32 MVP does not add a new public Python API. A private artifact model and
builder may be planned in later Phase 32 slices.

Phase 32 Slice 1 adopts no new tooling. Pyright remains the blocking source of
truth. Slice 1 does not add `ty`, a global coverage threshold, Hypothesis,
deptry/import-linter, mutation testing, nightly jobs, or automatic PyPI
publication.

Slice 1 performs no package version bump, release tag, package release,
publishing, upload, signing, or attestation operation.

## 15. Roadmap Alignment

Current post-v0.2 roadmap:

- Phase 32: Semantic Explain And Metadata Output MVP;
- Phase 33: JSON v2 And Project / Multi-file MVP;
- Phase 34: Relationship Grain And Narrow JOIN MVP;
- Phase 35: Developer Experience And Delivery Pipeline MVP;
- Phase 36: Core Type System Expansion II;
- Phase 37: Aggregate Expansion II.

Semantic Graph / ERD / AI Metadata Export remains a post-Phase-37 deferred
candidate without an assigned phase number.

Historical Phase 29 through Phase 31 plan/spec artifacts may retain old roadmap
wording. Current Phase 32 status documents supersede that wording for active
roadmap purposes.

If status-document edits trigger hash-lock fallout, Slice 1 may make
digest-only replacements. Those replacements must preserve the existing hash
algorithm, preserve path lists, preserve path counts, preserve ordering,
preserve helper functions, and preserve all unrelated digest values. Gate 2
must report each replacement with:

```text
file | locked path | old digest | new digest | reason
```

## 16. Slice 2 Handoff

Slice 2 should define the Semantic Metadata Artifact v1 contract, including
exact JSON property names, success envelope, failure envelope, field categories,
ordering policy, path policy, and compatibility posture.

Slice 2 should still avoid implementation unless separately approved for that
slice. Slice 1 does not pre-authorize source changes.
