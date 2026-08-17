# Phase 55 Slice 2 Explicit Package Activation, Compatibility, And Immutable Package Carrier v1

## Purpose And Current Lifecycle

Phase 55 is **Semantic Package Asset Schema And Deterministic Local Loading**.
Slice 2 is **Explicit Package Activation, Compatibility, And Immutable Package
Carrier**. This specification is the exact product and architecture authority
for Slice 2.

The Gate 0 baseline is commit `5de57b2c078742253aa64d3a5ad627cd602290cd`,
tree `9bc952f6eedca6a953c9edd94e0172b02451f74c`, and natural main `push` CI
attempt 1 run `31874242101` successful. The immutable Gate 0/Gate 1 authority
is
`/home/mianliwang/.local/state/pietto/evidence/pietto-phase55-slice2-gate0-gate1-explicit-package-activation-carrier-plan.txt`
with SHA-256
`3030dd8eabb8b0879569f992fbad4f946cc4ab0a46a8f06995f9e3e29d133a7e`.

The earlier Phase 55 Slice 1 PR workflow text is historical. The temporary
single-developer authority makes the forward lifecycle Phase 54 `COMPLETED`,
Phase 55 `ACTIVE`, Slice 1 `COMPLETED`, Slice 2 `IMPLEMENTED_UNPUBLISHED`, and
Slices 3 through 12 `UNSTARTED`, with `next=PHASE55_SLICE2_GATE3`. This does
not assert that the late PR #62 review-thread closure passed or authorize any
change to that historical debt.

## Product Decisions

### P01 — Exclusive Explicit Activation

`schema_version = 3` plus exactly one `[package]` root table is the only
package-mode activation. It yields `PACKAGE_ROOT`. Schema v1 yields
`LEGACY_FLAT`; schema v2 yields `EXPLICIT_MODULES`. There is no heuristic,
ambient discovery, manifest-presence activation, or mixed activation.

### P02 — Exact Version/Table Compatibility

Versions are exact non-boolean integers. Schema v1 and v2 allow exactly
`schema_version` and `[sources]`, require `[sources]`, and reject `[package]`.
Schema v3 allows exactly `schema_version` and `[package]`, requires `[package]`,
and rejects `[sources]`. A v3 config has no source-selection model.

### P03 — Exact Root Declaration

`[package]` contains exactly these five non-empty decoded string fields, in
the authored configuration boundary:

```text
path
namespace
name
version
sha256
```

Unknown, missing, duplicate semantic, non-string, or empty fields fail through
the existing configuration-schema envelope. This Slice performs no slug,
SemVer, or SHA-256 semantic validation; `namespace`, `name`, `version`, and
`sha256` retain their decoded authored string values.

### P04 — Structural Root Path

`path` is either `.` or a normalized project-relative directory path. It
rejects absolute paths, Windows drive forms, backslashes, NUL, empty segments,
an intermediate `.` or `..` segment, and a leading, repeated, or trailing
slash. The structural check neither resolves nor opens the path; trusted
containment and locator behavior are later Slice 6 work.

### P05 — Private Immutable Carrier

`ProjectRootPackageActivation` lives only in `pietto._project.model`. It is a
private frozen, slotted, hashable value with exactly `path`, `namespace`,
`name`, `version`, and `sha256`. It is the accepted structural root declaration
only, not normalized package identity, manifest authority, digest, locator, or
public API.

### P06 — Strict ProjectConfig Tagged Union

`ProjectConfig` is the complete activation root and has ordered fields
`(schema_version, sources, compilation_mode, root_package)`. For v1/v2,
`sources` is present and `root_package is None`; v1 uses `LEGACY_FLAT` and v2
uses `EXPLICIT_MODULES`. For v3, `sources is None`, `root_package` is present,
and the mode is `PACKAGE_ROOT`. Invalid combinations are rejected at
construction and parsing boundaries.

### P07 — Existing Module Identity Remains Layered

`ProjectLogicalModule` and its builder reject `PACKAGE_ROOT`. Existing
`ProjectModuleIdentity` remains unchanged: it does not become a package
identity and no outer package/module identity is introduced in this Slice.

### P08 — Source-selection Fail-closed Boundary

After the existing pinned project-root verification and before any source
traversal, manifest I/O, module construction, or selected-input I/O,
`select_project_sources()` returns the existing `CONFIG_SCHEMA` discovery
envelope for package mode. Its exact message is:

```text
Schema-v3 package activation does not use project source selection.
```

It returns no partial inputs, modules, or index. Existing check and CLI error
propagation remain unchanged; no package-specific public diagnostic, JSON
field, or CLI option is created.

### P09 — Semantic Pipeline Exclusion

Manually constructed package-mode parse results cannot enter either legacy or
schema-v2 semantic pipeline. Before an existing failed-parse short circuit,
semantic construction rejects injected selected inputs, parsed inputs, logical
modules, selected-input index, source snapshots, or semantic sidecars. A valid
package-mode semantic result is unavailable (`model is None`) and contains no
module/index/snapshot/sidecar facts.

### P10 — Exact Compatibility And No Fallback

Schema v1 and package-absent schema v2 preserve their existing accepted bytes,
selection, parsing, semantic facts, CLI behavior, and public/private boundary.
Schema v3 never falls back to these modes and does not inspect
`pietto-package.toml`.

## Architecture Decisions

### A01 — One Config-root Authority

The accepted `ProjectConfig.root_package` is the only Slice 2 package carrier.
Discovery, parse, and semantic result carriers gain no package fields.

### A02 — No Speculative Carrier Module

The root carrier is added to the existing private model module rather than a
new package carrier module. Its five structural fields are the minimum seam
that prevents immediate carrier redesign without implementing later product.

### A03 — Parser And Constructor Enforce the Same Union

Config parsing validates the version/table/field boundary; immutable model
construction independently rejects invalid tagged-union combinations. Neither
layer depends on the other for correctness.

### A04 — One Explicit Dispatch Boundary

Only `EXPLICIT_MODULES` enters the existing module pipeline. `PACKAGE_ROOT` is
rejected by module construction and by semantic assembly; it cannot acquire a
legacy or schema-v2 fallback.

### A05 — One Early Selection Guard

The source-selection function owns one package-mode guard after pinned-root
verification and before traversal. Existing caller error propagation is reused,
so no CLI/check or public-envelope redesign is needed.

### A06 — No Manifest or Filesystem Package Product

Slice 2 does not probe, open, parse, normalize, or report a
`pietto-package.toml` file. A missing manifest has no Slice 2-specific result.

### A07 — Private Surface Only

No `PIE-*` identifier, public export, JSON field, Artifact/IR/SQL field, CLI
option, dependency, lockfile, workflow, version, tag, Release, publication,
signing, or attestation is added.

### A08 — External Reviewed-tree Authority

The immutable external Gate 2 evidence, not a commit trailer, binds the sealed
reviewed tree. The Gate 3 direct-main check is `commit.parent ==
SLICE2_BASELINE` and `commit.tree == sealed_tree`, plus exact allowlist
staging. `Pietto-Reviewed-Tree` is a redundant descriptive consistency check
only and cannot authorize the tree it describes.

## Later-owner Boundary

Slice 3 owns `pietto-package.toml` input schema and canonical normalization.
Slice 4 owns final package identity, exact SemVer, and content digest. Slice 5
owns typed assets/catalog. Slice 6 owns trusted locator and containment. Slice
7 owns package loading and package/module integration. Slices 8 and 9 own
dependencies, load planning, collision/cycle/rejection behavior. Slice 10 owns
private package inspection; Slice 11 owns pure/differential/e2e hardening;
Slice 12 owns Phase 55 completion and Phase 56 handoff. Phase 59 owns the
package graph product, Phase 67 remote packages, and Phase 68 ranges, solver,
lockfile, and production Rust.

## Gate 2 Review, Closure, And Validation

The candidate is an unstaged dirty overlay on `main`; Gate 2 creates no branch,
commit, push, CI action, PR, tag, Release, publication, signing, or
attestation. Its exact allowlist is the Gate 0/Gate 1 projected `A2_M75_D0`
set, extended only by deterministic executing-reader fixed-point discovery.
Final counts are sealed-tree facts, not predictions.

Review is by complete generations only:

1. Implement the complete candidate.
2. Inspect the complete frozen review surface without modifying it.
3. Freeze the whole finding set.
4. Group findings by causal root.
5. Make one batched repair pass.
6. Re-review the new exact tree from the beginning.

If a following generation repeats the causal defect family targeted by the
prior repair, classify architecture non-convergence and revisit the authority
root rather than adding another leaf guard. Reader discovery may happen early,
but reader/hash/digest rewrites occur only after semantic freeze and conclude
with `reader_additions=0` and `digest_delta=0`.

Required validation includes focused/property/adversarial activation tests,
schema-v1/v2 compatibility, Python 3.12 and 3.13 full pytest, Ruff
check-only/lint, production and test Pyright, generated and golden checks,
`uv lock --check`, offline package smoke, installed CLI `0.1.0`, direct-main
topology projections, two canonical patches, identity manifest, and independent
tree reconstruction.

## Direct-main Gate 3

Before publication, prove remote `main` still equals `SLICE2_BASELINE` and the
dirty overlay tree equals the external sealed tree. Stage exactly the sealed
allowlist and make one non-amend commit on `main` with subject
`Add Phase 55 explicit package activation carrier` and descriptive trailer
`Pietto-Reviewed-Tree: <sealed_tree>`. The commit parent and tree must match
the external evidence as specified by A08; then push normally and await the
natural attempt 1 CI for that exact head.

If that CI fails, preserve it. Only an in-scope mechanical repair may create a
new non-amend child commit after full offline validation and append-only Gate 2
recovery evidence; that new exact head receives its own natural attempt 1.
Baseline, scope, or architecture drift returns to Gate 0/Gate 1. Do not amend,
rebase, force-push, manually rerun/cancel CI, create a topic branch, tag,
Release, publish, sign, or attest.

The Gate 2 evidence target is
`/home/mianliwang/.local/state/pietto/evidence/pietto-phase55-slice2-gate2-explicit-package-activation-compatibility-and-immutable-package-carrier.txt`.
It is created only after the sealed tree and all Gate 2 closure. It is a
regular `0644` no-follow exclusive-create file with complete-byte writes,
file fsync, reopen byte verification, SHA-256 verification, and exactly one
EOF terminal; single-write syscall count is not a governance requirement.
