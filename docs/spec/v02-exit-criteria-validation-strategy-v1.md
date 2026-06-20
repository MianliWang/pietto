# v0.2 Exit Criteria And Validation Strategy v1

## Status

Phase 29 Slice 5 is complete as a v0.2 exit criteria and validation strategy
contract and static audit slice only.

This contract defines the criteria required before a later phase may declare
Pietto v0.2 complete as a stable single-file typed SQL authoring compiler. It
does not declare v0.2 complete.

Phase 30 Core Type System Stabilization I, Phase 31 Core Type System
Stabilization II And Dialect Matrix Hardening, and Phase 32 v0.2 Single-file
Stable Completion Audit remain required before the v0.2 stable completion
status can be locked. Phase 32 remains the actual v0.2 single-file stable
completion audit.

This contract does not authorize source implementation changes, grammar
changes, generated ANTLR changes, AST or parser changes, public API changes,
CLI behavior changes, JSON behavior or schema changes, IR behavior changes,
SQL lowering changes, semantic behavior changes, aggregate behavior changes,
diagnostic behavior changes, runtime execution, project or multi-file
behavior, relationship/JOIN behavior, schema introspection, type-system
behavior changes, fixture or golden changes, validation script changes, CI
workflow changes, package metadata changes, package version changes, release
tags, release artifacts, publication, package upload, signing, attestation,
JSON v2, or public MySQL API expansion.

## Exit Criteria

A later v0.2 completion audit must verify all of these criteria before v0.2 is
declared complete:

| Area | v0.2 exit criterion | Validation evidence | Explicit non-goals |
|---|---|---|---|
| Stable single-file language surface | The accepted language remains the current single-file compiler surface with no project/multi-file syntax, source loading, or JSON v2 behavior. | Phase 29 boundary contract, current parser/semantic tests, and `uv run python scripts/validate.py`. | No grammar, generated ANTLR, AST, parser, project, or multi-file change. |
| Aggregate surface freeze | The Phase 19 through Phase 28 aggregate and result-scope surface remains frozen except for bug fixes. | `docs/spec/v02-aggregate-surface-freeze-v1.md`, focused Phase 29 aggregate freeze audit, golden guard, and full validation. | No aggregate expansion, new diagnostics, fixture/golden change, SQL lowering change, or aggregate behavior change. |
| Deferred feature register | Every deferred feature remains outside v0.2 unless its register entry permits contracts/tests, readiness decisions, or explicitly approved Phase 30/31 stabilization. | `docs/spec/v02-deferred-feature-register-v1.md` and focused register audit. | No implementation of registered deferred features. |
| Core type-system gap matrix | Phase 30 and Phase 31 must resolve or explicitly carry forward the core type-system gaps identified by Slice 4. | `docs/spec/v02-core-type-system-gap-matrix-v1.md`, Phase 30 completion audit, and Phase 31 completion audit. | No Slice 5 type model, semantic, diagnostic, or SQL behavior change. |
| Phase 30 prerequisites | Canonical scalar registry, nullability propagation, Bool and predicate semantics, Date/Timestamp, Decimal precision/scale contract, and operator/comparison matrices have accepted Phase 30 disposition. | Phase 30 plan/spec/tests and completion audit. | No Phase 30 implementation in Slice 5. |
| Phase 31 prerequisites | Aggregate result matrix, numeric and Decimal boundaries, Date/Timestamp SQL compatibility, UUID/Enum readiness, and diagnostic plus CLI/JSON type output hardening have accepted Phase 31 disposition. | Phase 31 plan/spec/tests and completion audit. | No Phase 31 implementation in Slice 5. |
| Phase 32 completion audit | Phase 32 performs the v0.2 candidate release contract, language surface freeze audit, CLI/JSON/public API stability audit, docs/golden completion audit, full validation, package smoke, and v0.2 status lock. | Phase 32 completion audit and status documentation. | Slice 5 does not declare v0.2 complete. |
| CLI stability | Current `pietto check` and `pietto emit-sql` command forms, text defaults, `--format`, `--dialect`, `--output`, exit-code boundaries, and stdout/stderr separation remain stable. | CLI tests, JSON tests, package smoke installed CLI checks, and full validation. | No CLI command, option, help, exit-code, output, or behavior change. |
| JSON v1 stability | JSON schema version 1 remains the single-file machine-readable contract with no silent field, type, meaning, or schema change. | `docs/spec/cli-json-v1.md`, JSON-focused tests, golden JSON structural checks, and full validation. | No JSON v1 change and no JSON v2 implementation. |
| Public API stability | The public SQL API remains PostgreSQL-only through `emit_postgres_sql`; MySQL remains private to explicit CLI dispatch. | `src/pietto/sql/__init__.py`, public API tests, and full validation. | No public MySQL API expansion and no generic public SQL dispatcher. |
| Diagnostics stability | Diagnostic codes keep canonical `PIE-*` format; severities, ordering, location handling, text CLI rendering, and JSON diagnostic shape remain stable. | `docs/spec/diagnostics.md`, CLI diagnostic tests, JSON diagnostic tests, and full validation. | No diagnostic code, severity, wording, presentation, or behavior change in Slice 5. |
| SQL golden stability | Reviewed PostgreSQL and MySQL SQL goldens remain stable and owned by tests. | `uv run python scripts/check_goldens.py` and golden-output tests. | No fixture or golden inventory/content change in Slice 5. |
| Generated-file stability | Generated ANTLR files remain byte-for-byte reproducible from the reviewed jar and grammar. | `uv run python scripts/check_generated.py`. | No grammar or generated file change in Slice 5. |
| Package smoke expectations | Package smoke builds sdist and wheel in a temporary directory, inspects metadata and generated inventory, installs the wheel in a clean venv, and checks installed CLI behavior. | `uv run python scripts/package_smoke.py`. | No package metadata, version, dependency, build backend, release artifact, upload, signing, publication, or attestation change. |
| Docs, examples, and README readiness | Phase 32 must confirm README, examples, specs, plans, and golden/documentation references match the v0.2 single-file boundary. | Phase 32 docs/examples/golden/documentation audit. | No broad status docs update in Slice 5 unless validation proves a narrow static-audit update necessary. |
| CI expectations | CI continues to orchestrate the accepted local commands on Python 3.12 and Python 3.13 without duplicating their logic. | `.github/workflows/ci.yml` and the latest exact-head GitHub Actions run for the release-candidate commit. | No CI workflow change in Slice 5. |

## Required Validation Stack

The minimum Slice 5 local validation stack is:

```bash
uv run pytest tests/test_phase29_v02_exit_criteria_validation_strategy.py
uv run pytest tests/test_phase29_v02_core_type_system_gap_matrix.py
uv run pytest tests/test_phase29_v02_aggregate_surface_freeze.py
uv run pytest tests/test_phase29_v02_deferred_feature_register.py
uv run pytest tests/test_phase29_v02_stabilization_candidate_decision.py
uv run python scripts/check_generated.py
uv run python scripts/check_goldens.py
uv run python scripts/package_smoke.py
uv run python scripts/validate.py
```

A later Phase 32 v0.2 completion audit must run the full local validation
stack and verify a successful exact-head CI run for the candidate commit before
locking v0.2 completion status.

## Explicit v0.2 Non-Goals

v0.2 exit criteria do not authorize:

- source implementation changes;
- grammar, generated ANTLR, AST, or parser changes;
- public API changes;
- CLI behavior, command, option, help, or exit-code changes;
- JSON v1 changes or JSON v2 implementation;
- IR implementation or IR model changes;
- SQL backend or SQL lowering changes;
- semantic implementation or semantic behavior changes;
- aggregate expansion or aggregate behavior changes;
- diagnostic behavior changes;
- fixture, golden, script, dependency, lockfile, package metadata, CI, or
  package version changes;
- package release, release tag, release artifact, publication, package upload,
  signing, or attestation;
- public MySQL API expansion;
- project or multi-file implementation;
- relationship or JOIN implementation;
- schema introspection, database pull, connector execution, SQL execution, or
  runtime/database behavior;
- DateTime, Time, timezone, Interval, Currency, or Money primitives;
- semantic annotation syntax;
- explain/audit output;
- LSP, playground, web UI, Arrow, or dataframe integration.
