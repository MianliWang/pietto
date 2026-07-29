# Phase 54 Slice 3 — Module Identity, Selected-input Index, Trusted Local Loader, And Path / Symlink Boundary v1

## Status And Authority

Phase 54 is `ACTIVE`. Slices 1 and 2 are `COMPLETED`. During Slice 3 Gate 2,
Slice 3 remains incomplete and Slices 4-16 remain `UNSTARTED`. The exact trusted
base is `d8a5e9ab3de70ce30575513c73560c86430eca63`, with tree
`0952c0ba099850489d6223f894cef4fe03741a5d`.

This contract implements the Phase 54 P5/A1/A2 local trust boundary. It does
not authorize import/export grammar, module catalogs, visibility, resolution,
module graphs, cross-module semantics, public serialization, remote/package
loading, dependency changes, workflow changes, version changes, or release
operations. No `PIE-S2701` through `PIE-S2707` code is added or emitted.

The original Gate 0 / Gate 1 authority was `A5_M55_D0`. Corrective addendum 1
adds one executing mechanical reader and freezes the reviewed-tree authority as
`A5_M56_D0`. Gate 2 keeps the Git index empty and is fully offline. Gate 3
alone owns publication.

## Stable Module Identity

`ProjectModuleIdentity` is a private frozen, slotted, keyword-only value with
one field in exact order:

1. `path: str`

The value is an exact normalized project-relative path ending in lowercase
`.pietto`. Equality and hashing use only that path. There is no case folding,
Unicode normalization, canonical path, physical identity, digest, AST identity,
source span, or source location in semantic module identity.

`ProjectLogicalModule.identity` derives this path-only value without changing
the Slice 2 five-field carrier. `ProjectLogicalModule` remains exactly:

1. `compilation_mode`
2. `path`
3. `position`
4. `project_input`
5. `parsed_input`

## Pinned-root Trust Model

`src/pietto/_project/path_trust.py` privately owns:

- `ProjectPhysicalIdentity(device, inode)`;
- `ProjectFilesystemState(physical_identity, file_type, size, mtime_ns,
  ctime_ns)`;
- `ProjectPinnedRoot(display_path, invocation_path, canonical_path,
  physical_identity)`.

All are frozen and slotted. Host paths and filesystem identity/state fields are
excluded from repr. Config loading records the absolute lexical invocation path,
calls `Path(root).resolve(strict=True)` exactly once, requires a directory with
meaningful device/inode identity, and stores the canonical target. Later stages
receive the same `ProjectPinnedRoot` object and never resolve the original root.
Both invocation-target and canonical-root identities are verified at stage
boundaries. A stable invocation-root symlink is accepted; retarget or replacement
fails closed.

No live descriptor crosses a result boundary. Where `os.open` supports
`dir_fd`, `O_DIRECTORY`, and `O_NOFOLLOW`, the loader uses a transient verified
root descriptor and no-follow child open. Else it uses the stored canonical path
with mandatory root, leaf, and descriptor identity checks. `O_NONBLOCK`, where
available, prevents a raced non-regular replacement from blocking before
`fstat`. Filesystems without meaningful stable device/inode facts fail closed.

## Config Trust Boundary

Config loading owns one once-pinned root. It constructs
`canonical_root/pietto.toml`, obtains no-follow leaf state, rejects a symlink,
and requires a regular file. It opens in binary exactly once, requires opened
regular identity to equal inspected identity, performs exactly one accepted
bytes read, and verifies pre/post descriptor and root state. Those exact bytes
are decoded as UTF-8 and supplied to `tomllib`; the config path is never reopened.

Both schema versions share this safety policy because `schema_version` is not
trusted until after the config read. Stable valid schema-v1 and schema-v2
behavior is retained. Newly unsafe config states use the existing project-error
envelope.

## Immutable Selected-input Index

`src/pietto/_project/selected_input_index.py` privately owns
`ProjectSelectedInputEntry` with fields in exact order:

1. `identity`
2. `position`
3. `project_input`
4. `canonical_path`
5. `logical_leaf_state`
6. `final_target_state`
7. `final_leaf_is_symlink`
8. `symlink_target`

`ProjectSelectedInputIndex` contains the same pinned root, an ordered entries
tuple, and a copied private `MappingProxyType` exact lookup excluded from repr,
comparison, and hashing. Positions are exactly `0..n-1`; logical paths and final
physical identities are unique; each entry path matches its module identity;
lookup by exact identity or path performs no filesystem access.

Traversal begins at the pinned canonical root. It retains and verifies directory
no-follow state before and after enumeration, never descends through a symlink
directory, and preserves deterministic path order. Each selected final leaf
retains separate no-follow leaf state, optional exact `readlink` text, followed
target state, and one selection-time canonical target. A final source symlink is
accepted only when its target is a regular file inside the pinned root. Escape,
non-regular targets, and duplicate final physical identities fail closed.

If selection has any error, `selected_input_index` is absent. A retained earlier
display input in a duplicate report is never a usable index winner.

## Trusted Local Loader And Snapshot

`src/pietto/_project/trusted_source.py` privately owns
`ProjectTrustedSourceSnapshot` with fields in exact order:

1. `selected_input`
2. `byte_count`
3. `sha256`
4. `source_text`
5. `opened_target_state`

It is frozen and slotted. Selected input, source text, digest, and opened trust
facts are repr-hidden. Identity, path, and position are delegated read-only to
the exact index entry. The snapshot enforces exact opened state, UTF-8 byte
count, and lowercase SHA-256 agreement.

The loader accepts only the pinned root, one exact selected-index entry, and the
exact `1048576` byte limit. It verifies root and logical leaf/readlink/followed
target facts; opens only the stored canonical target without resolve or
discovery; requires a regular `fstat` match; performs one buffered
`read(limit + 1)`; verifies pre/post descriptor and post root/leaf/target state;
computes lowercase SHA-256 over the exact accepted raw bytes; decodes those same
bytes exactly once; and returns a snapshot.

`check_project_parse_only` parses only `snapshot.source_text`. It does not
reconstruct or reopen `root / logical_path`. Oversize, unreadable,
trust-mismatched, mutated, or invalid-UTF-8 sources produce no snapshot. A
parse-invalid but successfully read and decoded source retains its snapshot.
Every transient root, config, and source descriptor closes on every success and
failure path.

The metadata sandwich detects observed changes to physical identity, file type,
size, mtime, or ctime. It is a portable metadata-consistency contract, not a
claim to detect a hostile same-inode rewrite that perfectly preserves every
observable metadata fact.

## Result Propagation And Privacy

The exact trailing private fields are:

- `ProjectConfigLoadResult.pinned_root`;
- `ProjectDiscoveryResult.pinned_root` and `selected_input_index`;
- `ProjectParseCheckResult.pinned_root`, `selected_input_index`, and
  `trusted_source_snapshots`;
- `ProjectSemanticResult.pinned_root`, `selected_input_index`, and
  `trusted_source_snapshots`.

Defaults remain `None` or `()`. Within one project check, the same pinned-root
object flows ConfigLoad → Discovery → Parse → SemanticResult, the same index
flows Discovery → Parse → SemanticResult, and the exact snapshots tuple flows
Parse → SemanticResult. Every snapshot retains the exact index entry object.

No trust field enters `ProjectConfig`, `ProjectLogicalModule`,
`ProjectParsedInput`, or `ProjectSemanticModel`. Canonical paths, device/inode,
digests, snapshots, and trust state are not added to Project JSON v2, CLI text,
public exports, grammar, AST, IR, SQL, fixtures, or goldens.

## Exact Failure Mapping And Order

| Failure | Kind | Exact message | Path |
| --- | --- | --- | --- |
| root retarget/replacement | `PROJECT_ROOT` | `Project root identity changed during project loading.` | `None` |
| unavailable physical identity | `PROJECT_RESOURCE` | `Project filesystem identity is unavailable.` | `None` |
| config symlink | `CONFIG_READ` | `Project configuration path must not be a symbolic link.` | `pietto.toml` |
| non-regular config | `CONFIG_READ` | `Project configuration path must be a regular file.` | `pietto.toml` |
| config opened mismatch | `CONFIG_READ` | `Project configuration opened identity does not match the inspected file.` | `pietto.toml` |
| config read mutation | `CONFIG_READ` | `Project configuration file changed while being read.` | `pietto.toml` |
| outside-root source | `PROJECT_PATH` | `Project source path escapes the project root.` | logical path |
| source symlink retarget | `SOURCE_READ` | `Project source symbolic link changed after selection.` | logical path |
| regular source replacement | `SOURCE_READ` | `Project source file changed after selection.` | logical path |
| opened source mismatch | `SOURCE_READ` | `Project source opened identity does not match the selected file.` | logical path |
| physical duplicate | `PROJECT_PATH` | `Project source path duplicates an already selected file.` | later sorted logical path |
| non-regular source | `SOURCE_READ` | `Project source path must resolve to a regular file.` | logical path |
| mutation during read | `SOURCE_READ` | `Project source file changed while being read.` | logical path |

Generic source-read and UTF-8 messages remain unchanged. Root/config produce one
error. Traversal errors preserve deterministic traversal order; selected
validation errors use sorted logical order; source-load errors use index order;
parser diagnostics remain separately source ordered.

## Exact Gate 2 Allowlist

Added (`A5`):

- `docs/spec/phase54-slice3-module-identity-selected-input-index-trusted-local-loader-path-symlink-boundary-v1.md`
- `src/pietto/_project/path_trust.py`
- `src/pietto/_project/selected_input_index.py`
- `src/pietto/_project/trusted_source.py`
- `tests/test_phase54_module_identity_selected_input_index_trusted_local_loader.py`

Direct modified (`M7`):

- `docs/plan/phase-54-local-import-module-export-foundation.md`
- `src/pietto/_project/module_carrier.py`
- `src/pietto/_project/model.py`
- `src/pietto/_project/config.py`
- `src/pietto/_project/source_selection.py`
- `src/pietto/_project/check.py`
- `tests/test_phase54_schema_v2_explicit_module_carrier.py`

Mechanical readers (`M49`) are the original fixed-point list plus
`tests/test_phase50_import_module_export_readiness.py`, as frozen by immutable
corrective addendum 1. Deleted paths are `D0`. Total authority is `A5_M56_D0`;
formatter check-only input is exactly 59 Python paths after the sole original
write-mode invocation.

The primary module contains exactly 26 undecorated top-level tests, in the
frozen order from `test_module_identity_is_exact_normalized_path_only` through
`test_single_file_public_privacy_scope_and_flat_evidence_contract_remain_exact`.

## Flat Evidence Paths And Exclusive Creation

Every newly created Slice 3 evidence file is a flat filename directly under
`/home/mianliwang/.local/state/pietto/evidence`. The common directory must
already exist and is not otherwise modified. The exact paths are:

- `/home/mianliwang/.local/state/pietto/evidence/pietto-phase54-slice3-gate0-gate1-plan.txt`
- `/home/mianliwang/.local/state/pietto/evidence/pietto-phase54-slice3-gate0-gate1-plan-correction-1.txt`
- `/home/mianliwang/.local/state/pietto/evidence/pietto-phase54-slice3-gate0-gate1-plan-correction-2.txt`
- `/home/mianliwang/.local/state/pietto/evidence/pietto-phase54-slice3-gate2-evidence-and-diff.txt`
- `/home/mianliwang/.local/state/pietto/evidence/pietto-phase54-slice3-gate3-publication-evidence.txt`

Every authorized new target uses `O_CREAT | O_EXCL | O_NOFOLLOW`, `mode=0644`,
and must be a regular non-symlink. The forbidden directory
`/home/mianliwang/.local/state/pietto/evidence/phase54-slice3` is never created.
Historical Phase 54 Slice 1 and Slice 2 evidence remains immutable at its
historical paths and is never renamed, moved, copy-replaced, deleted, appended,
or chmodded.

## Gate Terminals And Lifecycle

Gate 0 / Gate 1 PASS ends with the exact flat `report=` path and `next=GATE2`.
Any corrective addendum ends with its own exact flat `report=` path. Gate 2 PASS
ends with the exact flat Gate 2 `report=` path and `next=GATE3`. Gate 3 PASS ends
with the exact flat Gate 3 `report=` path and
`next=PHASE54_SLICE4_GATE0_GATE1`. Every STOP record uses the gate's exact flat
evidence path. Gate 3 evidence-chain fields name the exact Gate 0 / Gate 1,
optional corrective-addendum, Gate 2, and Gate 3 flat paths.

Slice 3 becomes `COMPLETED` only after reviewed-tree publication,
natural exact-head PR CI attempt 1, squash-tree equality, natural exact-head `main` CI
attempt 1, ff-only reconciliation, cleanup, and immutable Gate 3 evidence.
Then Slices 4-16 remain `UNSTARTED` and the next state is
`PHASE54_SLICE4_GATE0_GATE1`.

## Retained-later Boundary

Slice 4 retains contextual import/export grammar, generated parser changes, and
immutable import/export AST. Slices 5-15 retain module catalogs, visibility,
named re-export, bindings, collision rules, graph/cycle diagnostics,
cross-module type/relation semantics, identity-safe downstream facts, assets,
inspection, canonical serialization, and compatibility hardening. Slice 16
retains completion audit and status lock.

Slice 3 adds no module resolver, import-driven discovery, excluded-file probe,
global/callback/ambient registry, package loader, remote I/O, dependency solver,
lockfile behavior, public serializer schema, runtime execution, database
behavior, Rust/native build, additional dialect, release, tag, publish, upload,
signing, attestation, or supply-chain behavior.
