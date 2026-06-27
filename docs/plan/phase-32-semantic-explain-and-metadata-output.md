# Phase 32 Semantic Explain And Metadata Output MVP

## 1. Status And Trusted Handoff

Phase 32 Slice 1 is complete as Candidate Decision, Roadmap Alignment, And
v0.2 Handoff Audit work only. Phase 32 Slice 2 is complete as Semantic
Metadata Artifact v1 Contract work only. Phase 32 Slice 3 is complete as
Private Metadata Model And Builder MVP work only. Phase 32 Slice 4 is complete
as Definition, Schema, Type, And Nullability Metadata work only.

Trusted handoff:

- baseline HEAD: `a2677114269f98c24c250376b3626a7f0178038c`;
- baseline commit: `Complete Phase 31 v0.2 stable completion audit`;
- Phase 31 complete;
- Pietto v0.2 single-file stable complete;
- package version remains `0.1.0`;
- no release tag, package release, publishing, upload, signing, or attestation
  operation is part of this slice.

Phase 32 has started. Phase 32 as a whole is not complete.

## 2. Baseline Evidence

Slice 1 records the repository-local Phase 31 completion handoff. The trusted
baseline is clean and untagged at
`a2677114269f98c24c250376b3626a7f0178038c`.

Repository facts carried forward:

- `docs/spec/pietto-v0.9.md` remains the current specification document path
  and label; it is not the package version and is not a release tag;
- `v0.2` is the internal single-file stable compiler boundary;
- package and installed CLI version remain `0.1.0`;
- existing CLI JSON v1 covers current `check` and `emit-sql` command results;
- current public Python SQL API remains PostgreSQL-only.

## 3. Candidate Decision

The selected Phase 32 direction is:

**Semantic Explain And Metadata Output MVP**

The selected public artifact identity is:

**Semantic Metadata Artifact v1**

Slice 1 is a docs/spec/static-audit/status-only slice. It records the selected
direction and boundary decisions. It does not implement `pietto explain`, does
not define the final Artifact v1 JSON schema, and does not add metadata DTOs,
builders, serializers, or text renderers.

## 4. Approved Roadmap Alignment

Current post-v0.2 roadmap:

- Phase 32: Semantic Explain And Metadata Output MVP;
- Phase 33: JSON v2 And Project / Multi-file MVP;
- Phase 34: Relationship Grain And Narrow JOIN MVP;
- Phase 35: Developer Experience And Delivery Pipeline MVP;
- Phase 36: Post-v0.2 Core Type System Expansion MVP;
- Phase 37: Post-v0.2 Aggregate Surface Expansion MVP.

Semantic Graph / ERD / AI Metadata Export remains a post-Phase-37 deferred
candidate without an assigned phase number.

Completed Phase 29 through Phase 31 plan/spec artifacts may retain historical
roadmap wording. Current status documents and this Phase 32 plan supersede that
old split for active roadmap purposes.

## 5. Semantic Metadata Artifact v1 Boundary

Semantic Metadata Artifact v1 is a new public artifact identity for Phase 32.
It has a separate version domain from:

- existing CLI JSON v1 for `check` and `emit-sql`;
- future project-level JSON v2.

Slice 1 does not define exact JSON property names, a success envelope, an error
envelope, DTO class names, builder module names, serializer module names, or
normative JSON examples. Those are Slice 2 or later decisions.

Allowed high-level Artifact v1 facts are semantic metadata facts that can be
truthfully derived from the accepted single-file compiler pipeline, including
definition names, row-schema posture, resolved type posture, effective
nullability posture, aggregate posture, query posture, diagnostics posture, and
narrow basic lineage posture.

## 6. Dedicated Explain CLI Direction

The approved target CLI direction is:

```text
pietto explain <file> [--format text|json]
```

The default format is text. JSON is the future normative machine-readable
Semantic Metadata Artifact v1 presentation. Text is a human-readable renderer
derived from the same normalized artifact.

Phase 32 MVP does not add:

- `--dialect` for `explain`;
- `--output` for `explain`;
- a project flag;
- database or runtime options.

## 7. Existing JSON v1 Compatibility Boundary

Existing `check` and `emit-sql` CLI JSON v1 remains exactly unchanged:

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

Semantic Metadata Artifact v1 is not a mutation of CLI JSON v1.

## 8. Fail-closed And No-partial-metadata Policy

Explain may use this compiler pipeline:

```text
parse
-> semantic analysis
-> existing IR construction
-> normalized metadata artifact
```

Explain must not invoke SQL lowering, database connections, SQL execution, or
runtime behavior.

Metadata is emitted only after parse, semantic analysis, and IR construction all
succeed. On parse, semantic, or IR failure, Phase 32 returns diagnostics or
error information only and must not expose partial definitions, relations,
schemas, projections, aggregates, or lineage.

Exact JSON envelope field names belong to Slice 2.

## 9. Source Path And Deterministic Ordering Policy

Phase 32 uses the existing user-supplied string / `str(path)` posture. It does
not canonicalize paths by default, promise absolute paths, promise
project-relative paths, or introduce project-root semantics.

Phase 32 is single-file only. It preserves deterministic source/IR order and
does not define multi-file ordering.

## 10. Basic Lineage Boundary

Basic lineage is limited to:

- direct source relation and field provenance for direct field projections;
- normalized direct field leaves used by currently supported bounded
  expressions;
- normalized direct field leaves used by currently supported aggregate
  arguments.

Artifact v1 must not expose raw `SymbolId`, raw `FieldId`, AST node identity,
raw IR nodes, relationship traversal, JOIN lineage, multi-file lineage, graph
lineage, physical database lineage, or runtime lineage.

## 11. Relationship, Dialect, Deferred, And Security Boundaries

Relationship metadata is not part of Semantic Metadata Artifact v1. Cardinality,
direction, optionality, grain, fanout, traversal, and JOIN remain Phase 34 work.

Artifact v1 has no SQL dialect field and does not describe selected backend
capabilities.

Artifact v1 has no global per-program `deferred` field that serializes roadmap
documentation. Actual unsupported behavior remains represented by compiler
diagnostics.

Artifact v1 must not expose connector literal internals, connector
configuration values, credential-like values, secrets, or raw connector
implementation structures.

## 12. Tooling And Release Boundaries

Phase 32 Slice 1 adopts no new tooling. Pyright remains the blocking source of
truth for type checking.

Slice 1 does not add `ty`, does not place `ty` in `scripts/validate.py`, does
not add a global coverage threshold, does not make generated ANTLR files a
coverage target, does not add Hypothesis, does not add deptry/import-linter,
does not add mutation testing, does not add nightly jobs, and does not add
automatic PyPI publication.

Slice 1 performs no package version bump, release tag, package release,
publishing, upload, signing, or attestation operation.

## 13. Eight-slice Phase 32 Master Plan

1. **Candidate Decision, Roadmap Alignment, And v0.2 Handoff Audit**
   Complete as docs/spec/static-audit/status work only. Locks the handoff,
   selected direction, roadmap, and Phase 32 boundaries.

2. **Semantic Metadata Artifact v1 Contract**
   Complete as docs/spec/static-audit/contract-only work. Defines the normative
   Artifact v1 contract in `docs/spec/semantic-metadata-artifact-v1.md`,
   including version domain,
   high-level field categories, success/failure envelope policy, path policy,
   ordering policy, and compatibility posture. Exact JSON field names belong
   here, not Slice 1. Adds
   `tests/test_phase32_semantic_metadata_artifact_contract.py` and no source,
   CLI, JSON v1, semantic, IR, SQL, diagnostic, fixture, golden, example,
   package, dependency, workflow, version, release, tooling, tag, publish,
   upload, signing, or attestation behavior changes.

3. **Private Metadata Model And Builder MVP**
   Complete as private source, tests, status, and hash-lock work only. Adds a
   private `_metadata` model and success-only builder that consumes parse,
   semantic, and existing IR facts and emits a normalized internal artifact only
   after the pipeline succeeds. Slice 3 implements no `pietto explain` CLI
   behavior, JSON serializer, text renderer, public API, JSON v1 mutation, SQL,
   semantic behavior, IR behavior, grammar, generated file, fixture, golden,
   example, package, dependency, workflow, version, release, tag, publish,
   upload, signing, or attestation behavior changes.

4. **Definition, Schema, Type, And Nullability Metadata**
   Complete as tests, status, and hash-lock work only. Hardens private metadata
   definition/schema/type/nullability coverage for definitions,
   relation/table/query schemas, field names, resolved type posture, and
   effective nullability posture. Slice 4 implements no `pietto explain` CLI
   behavior, JSON serializer, text renderer, public API, JSON v1 mutation, SQL
   behavior, semantic behavior change, IR behavior change, grammar, generated
   file, fixture, golden, example, package, dependency, workflow, version,
   release, tag, publish, upload, signing, or attestation behavior changes.

5. **Query Posture, Aggregate, And Basic Lineage Metadata**
   Populate query posture, aggregate posture, and narrow basic lineage facts
   without relationship, JOIN, graph, database, runtime, or multi-file lineage.

6. **JSON Serializer And Fail-closed Error Envelope**
   Add the Artifact v1 JSON serializer and diagnostics/error-only failure
   envelope while preserving existing CLI JSON v1.

7. **Explain CLI Text/JSON Integration, Docs, Examples, And Package Smoke Readiness**
   Integrate `pietto explain <file> [--format text|json]`, derive text from the
   normalized artifact, and update docs/examples/package-smoke readiness as
   separately approved.

8. **Completion Audit And Status Lock**
   Lock Phase 32 completion with final validation, status docs, hash-locks, and
   Gate 3 commit/CI proof.

## 14. Slice 1 Implementation Scope

Allowed Slice 1 artifacts:

- `docs/plan/phase-32-semantic-explain-and-metadata-output.md`;
- `docs/spec/semantic-metadata-artifact-candidate-decision-v1.md`;
- `tests/test_phase32_semantic_metadata_candidate_decision.py`;
- minimal current status updates in `README.md`, `AGENTS.md`, and
  `docs/spec/pietto-v0.9.md`;
- exact digest-only hash-lock updates where status documents changed;
- preserve the existing hash algorithm;
- preserve path lists;
- preserve path counts;
- preserve ordering;
- preserve helper functions;
- preserve all unrelated digest values;
- narrow current-status assertion updates in existing Phase 31 tests when those
  assertions refer to the old active roadmap.

Slice 1 does not implement `pietto explain`, CLI behavior, metadata DTOs,
metadata builders, metadata serializers, text renderers, final JSON property
names, source behavior, grammar changes, generated changes, semantic changes,
IR changes, SQL changes, diagnostic changes, fixtures, goldens, examples,
package-smoke changes, public API changes, dependency changes, tooling changes,
workflow changes, package version changes, or release operations.

## 15. Validation Strategy

Slice 2 validation:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pytest tests/test_phase32_semantic_metadata_artifact_contract.py
uv run pytest
uv run python scripts/check_generated.py
uv run python scripts/check_goldens.py
uv run python scripts/package_smoke.py
uv run python scripts/validate.py
git diff --check
git diff -- \
  examples \
  tools \
  src \
  grammar \
  tests/fixtures \
  scripts \
  pyproject.toml \
  uv.lock \
  .github \
  Makefile \
  pyrightconfig.json \
  pyrightconfig.tests.json
```

The forbidden-path diff must have no output.

Slice 2 does not implement `pietto explain`, CLI behavior, metadata DTOs,
metadata builders, metadata serializers, text renderers, final runtime JSON
output, source behavior, grammar changes, generated changes, semantic changes,
IR changes, SQL changes, diagnostic changes, fixtures, goldens, examples,
package-smoke changes, public API changes, dependency changes, tooling changes,
workflow changes, package version changes, release operations, or tooling
adoption.

## 16. Gate 2 Evidence Requirements

Gate 2 must include:

- `git status --short --untracked-files=all`;
- `git diff --check`;
- `git diff --cached --check`;
- `git diff --stat`;
- `git diff --cached --stat`;
- `git diff --cached`;
- `git diff --name-status`;
- full `git diff`;
- no-index diffs for all new untracked Slice 1 files;
- full `cat` output for every new plan/spec/test file;
- focused status-document diffs;
- exact hash-lock diffs;
- the table `file | locked path | old digest | new digest | reason`;
- forbidden-path diff;
- complete validation output.

No summary may replace the full new plan, spec, test, or diff in Gate 2.

## 17. Gate 3 Commit/CI Requirements

Gate 3 requires separate explicit approval. After approval, stage only reviewed
Slice 1 files, commit with the approved message, push, poll GitHub Actions using
`sleep 15`, and report final commit SHA, CI run id, CI conclusion, CI headSha,
exact headSha match, tag output, and final clean worktree status.

## 18. Deferred Decisions And Later-phase Roadmap

Deferred to Slice 2:

- exact Artifact v1 JSON property names;
- exact success envelope;
- exact error envelope;
- normative JSON examples.

Deferred to later Phase 32 slices:

- private model names;
- builder module names;
- serializer module names;
- text renderer format;
- CLI integration details beyond the approved command shape;
- package-smoke updates, if any.

Deferred beyond Phase 32:

- JSON v2 and project/multi-file: Phase 33;
- relationship grain and narrow JOIN: Phase 34;
- developer experience and delivery pipeline: Phase 35;
- core type system expansion II: Phase 36;
- aggregate expansion II: Phase 37;
- Semantic Graph / ERD / AI Metadata Export: post-Phase-37 deferred candidate
  without an assigned phase number.
