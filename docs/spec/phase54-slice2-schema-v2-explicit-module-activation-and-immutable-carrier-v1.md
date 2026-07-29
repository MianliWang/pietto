# Phase 54 Slice 2 Schema-v2 Explicit-module Activation And Immutable Project / Module Carrier v1

## Status And Lifecycle

Phase 54 is `ACTIVE` and Slice 1 is `COMPLETED` at trusted base
`53d8767fc3bdbe5e3f631178652222bbe51f6a33`. Slice 2 remains incomplete
through Gate 2. It becomes `COMPLETED` only after exact reviewed-tree
publication, natural exact-head pull-request CI attempt 1, squash-tree
equality, natural exact-head `main` CI attempt 1, ff-only reconciliation,
publication-branch cleanup, and immutable Gate 3 evidence. The next state is
then `PHASE54_SLICE3_GATE0_GATE1`; Slice 3 does not begin here.

## Exact Schema-version Activation

The accepted configuration versions are exact integers 1 and 2. TOML
booleans, strings, floats, missing values, and every other integer fail
through the existing private config-schema error boundary.

Schema version 1 maps to stable private value `legacy_flat`. Schema version 2
maps to stable private value `explicit_modules`. The mode is project-wide and
is derived once from the loaded configuration. There is no `[modules]` table,
mode string, filename heuristic, source-level declaration, or mixed per-file
mode. Existing `[sources]` include/exclude normalization and deterministic
ordering apply identically to both versions.

## Immutable Compilation-mode Carrier

`ProjectCompilationMode` is a private `StrEnum` with exactly
`LEGACY_FLAT = "legacy_flat"` and
`EXPLICIT_MODULES = "explicit_modules"`. Its values do not depend on Python
object identity.

`ProjectConfig.compilation_mode` records the derived mode.
`ProjectDiscoveryResult`, `ProjectParseCheckResult`, and
`ProjectSemanticResult` each retain `compilation_mode`. Defaults on private
result constructors preserve legacy-flat compatibility.
`ProjectConfigLoadResult` and `ProjectSemanticModel` gain no field.

## Immutable Ordered Logical-module Carrier

`ProjectLogicalModule` is a private frozen, slotted, hashable dataclass with
exact field order:

```text
compilation_mode
path
position
project_input
parsed_input
```

`position` is the zero-based ordinal from deterministic selected-input order.
`path` is the exact normalized selected project-relative path. One carrier
exists per current input. Selection carriers reference the selected
`ProjectInput` and have no parsed input. Parse/check rebuilds carriers against
the final parsed/error `ProjectInput` values and attaches the matching
`ProjectParsedInput` when parsing succeeds. Failed inputs keep their carrier,
position, path, and mode with `parsed_input=None`.

The carrier rejects non-enum modes, non-normalized paths, bool or negative
positions, path mismatches, duplicate input paths, duplicate parsed paths, and
unmatched parsed inputs.

## Propagation Boundary

The mode is computed only by config loading. Source selection creates the
first ordered carriers. Parse/check retains the mode and rebuilds carrier
references from its final immutable inputs. The semantic entrypoint copies the
same mode and modules into its private result. No downstream consumer re-reads
`pietto.toml`, scans source text for a mode, or infers module identity from a
filename convention.

## Explicit-mode Flat-catalog Guard

`build_empty_project_semantic_result` permits only `LEGACY_FLAT` to reach
`_build_project_semantic_catalog`. For `EXPLICIT_MODULES`, it returns first
with `model=None`, no semantic diagnostics, and the same private mode/modules.
This is a deliberately unavailable semantic result, not module resolution.
No `PIE-S2701` through `PIE-S2707` code is added or emitted.

## Exact Transitional CLI And JSON Behavior

For a valid schema-v2 project whose sources parse, text project check returns
exit 1 with empty stdout and stderr and prints no `Project check OK` claim.
JSON project check returns exit 1 while preserving the existing Project JSON
v2 parse-result envelope exactly. Its existing `ok` value remains `true` when
the serialized error arrays are empty; `diagnostics` and `cli_errors` remain
empty. Project JSON v2 intentionally does not encode numeric process exit
status. No module or compilation-mode key is serialized.

Schema-v1 text and JSON output remain exact. Single-file `check`, `explain`,
and `emit-sql` behavior remains unchanged.

## Retained-later Boundary

Slice 3 retains pinned-root loading, canonical/opened physical identity,
symlink and TOCTOU checks, deduplication, exact-byte digest, and trust facts.
Slice 4 retains contextual import/export grammar, generated parser, and AST.
Slice 5 retains module-qualified declaration identity and per-module catalogs.
Slices 6-7 retain exports, re-exports, imports, aliases, bindings, and
collisions. Slice 8 retains module graph, cycles, and `PIE-S2701` through
`PIE-S2707`. Slices 9-10 retain cross-module semantic resolution. Later Phase
54 and Phases 55-70 retain their active-roadmap ownership.

The Slice 2 carrier contains no canonical physical target, device/inode,
opened descriptor, digest, pinned-root evidence, import/export AST,
declaration catalog, graph edge, package identity, registry identity, or
public serializer fact.

## Privacy And Compatibility Lock

The carrier sidecar has empty `__all__` and is not exported by the package.
Grammar, generated parser, AST, diagnostics inventory, SQL, CLI flags and
commands, CLI JSON v1, Semantic Metadata Artifact v1, Project JSON v2 keys,
public Python exports, dependencies, lockfile, workflow, package version,
fixtures, goldens, releases, signing, attestation, and Rust are unchanged.
Package and installed CLI version remain `0.1.0`.

## Tests And Exact Counts

The new module
`tests/test_phase54_schema_v2_explicit_module_carrier.py` contains exactly 16
top-level, non-parametrized tests. It covers exact modes and config failures,
identical source selection, carrier invariants, selection and parse
propagation, failure retention, explicit-mode guard, legacy `PIE-S2001`, exact
text/JSON transition, public privacy, single-file compatibility, grammar/AST/
diagnostic exclusions, and this contract. Projected clean collection is
10,830.

The executing mechanical reader closure contains exactly 48 modules. The sole
write-mode formatter invocation contains exactly 55 literal Python paths.
Generated inventory remains 8. Goldens remain 37: 32 SQL and 5 JSON. Package
smoke must pass and installed CLI remains 0.1.0.

## Exact Gate 2 Allowlist

Authority is `A3_M54_D0`.

Added A3:

```text
docs/spec/phase54-slice2-schema-v2-explicit-module-activation-and-immutable-carrier-v1.md
src/pietto/_project/module_carrier.py
tests/test_phase54_schema_v2_explicit_module_carrier.py
```

Core/status modified M6:

```text
docs/plan/phase-54-local-import-module-export-foundation.md
src/pietto/_project/config.py
src/pietto/_project/model.py
src/pietto/_project/source_selection.py
src/pietto/_project/check.py
tests/test_phase44_project_config_loader.py
```

Mechanical reader modified M48 is the exact fixed point frozen in immutable
Gate 0 evidence. It includes the Phase 54 scope-lock, Phase 11/12 root
readers, Phase 21/24/26-30/33 readers, Phase 51/52 direct and directory
readers, and the Phase 53 reader-of-reader chain. No deletion is authorized.

## Offline Validation And Evidence

Every `uv` invocation uses `UV_OFFLINE=1`; authoritative validation also uses
`UV_NO_SYNC=1`. The index stays empty. Exact focused, reader, SCC, formatter,
lint, production/test Pyright, validation entrypoint, isolated clean full
pytest, generated, golden, package, installed-CLI, and topology checks must
pass before immutable Gate 2 evidence is created with
`O_CREAT | O_EXCL | O_NOFOLLOW`, mode 0644.

## Publication And Completion

Gate 3 uses branch `phase54/slice2-schema-v2-module-carrier` and commit/PR title
`Add Phase 54 schema v2 module activation carrier`. It permits one exact-set
stage, one commit, one normal branch push, one ready PR, natural exact-head PR
CI attempt 1, exact-tree squash, natural exact-head `main` CI attempt 1,
fetch/ff-only reconciliation, branch cleanup, and immutable evidence. It
forbids amend, rebase, force-push, direct-main push, manual CI action, tag,
Release, package publication, upload, signing, and attestation.

## Stop And Next State

A product or production-path change outside this contract, flat-catalog
leakage, excluded-surface change, non-mechanical validation failure, Gate 2
network access, CI mismatch, or tree mismatch is a substantive stop. Bounded
mechanical reader/hash/inventory/topology repair inside the frozen closure is
not a product decision.

After exact completion: `Phase54=ACTIVE`, `Slice2=COMPLETED`,
`next=PHASE54_SLICE3_GATE0_GATE1`. Do not begin Slice 3.
