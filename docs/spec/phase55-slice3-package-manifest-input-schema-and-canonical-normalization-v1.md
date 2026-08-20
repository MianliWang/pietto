# Phase 55 Slice 3 Package Manifest Input Schema And Canonical Normalization v1

## Purpose And Lifecycle

Phase 55 is **Semantic Package Asset Schema And Deterministic Local Loading**.
Slice 3 is **Package Manifest Input Schema And Canonical Normalization**. This
specification is the exact product and architecture contract for the Slice 3
Gate 2 candidate.

The frozen baseline is commit
`019f7355c1556d918f180209736fec2b75a9e964`, tree
`ba285171d8d9b4a1cf34556990fff0b7b6181a69`, with natural `push` CI attempt 1
run `32078392127` successful. Phase 54 is `COMPLETED`, Phase 55 is `ACTIVE`,
Slices 1 and 2 are `COMPLETED`, Slice 3 is `IMPLEMENTED_UNPUBLISHED`, Slices 4
through 12 are `UNSTARTED`, and `next=PHASE55_SLICE3_GATE3`.

The controlling immutable authorities are:

- `/home/mianliwang/.local/state/pietto/evidence/pietto-phase55-slice3-gate0-gate1-package-manifest-schema-normalization-plan.txt`, SHA-256 `b4bd0256fbc27859b3b749861e6e0bb8d6d359c8e4f50398b9ecaa2e173defe6`;
- `/home/mianliwang/.local/state/pietto/evidence/pietto-phase55-slice3-gate0-gate1-package-manifest-schema-normalization-plan-correction-1.txt`, SHA-256 `86fa69d5196d1053bcaa39e33a8f07741bd1dc9799a890765bae369b5f7b8cb6`.

Correction 1 changes only the reader-universe/tool contract. It changes no
manifest product behavior recorded below.

## Product Boundary

Slice 3 adds one private, standard-library-only normalization seam:

```text
_normalize_package_manifest(
    root_package: ProjectRootPackageActivation,
    manifest_bytes: bytes,
) -> PackageManifestNormalizationResult
```

The function accepts caller-supplied bytes, not a filesystem path or decoded
mapping. `ProjectRootPackageActivation.path` determines only the logical
project-relative manifest path:

```text
"."   -> "pietto-package.toml"
"a/b" -> "a/b/pietto-package.toml"
```

This is lexical composition only. Slice 3 performs no filesystem operation and
claims no existence, regular-file, symlink, containment, handle, inode, or
TOCTOU fact.

## Exact Manifest v1 Schema

The fixed file name is `pietto-package.toml`. The input is strict UTF-8 TOML
and the byte limit is exactly `1048576`; the limit is inclusive and applies
before decoding. There is no additional item-count limit.

The exact top-level keys are:

```text
schema_version
namespace
name
version
assets
dependencies
```

`schema_version` is required and is exact non-boolean integer `1`.
`namespace`, `name`, and `version` are required exact non-empty strings.

`assets` is required and consists of one or more exact bare root
`[[assets]]` array-of-table occurrences. Each entry contains exactly the
required non-empty string fields `kind` and `path`.

`dependencies` is optional. Absence normalizes to `()`. Presence requires one
or more exact bare root `[[dependencies]]` array-of-table occurrences. Each
entry contains exactly the required non-empty string fields `namespace`,
`name`, `version`, `sha256`, and `path`.

Ordinary tables, quoted/dotted/nested substitutes, inline arrays or tables,
ordinary arrays, explicit empty arrays, unknown keys or tables, missing
fields, empty strings, wrong value kinds, duplicate TOML keys/tables, and
unsupported schema versions fail closed. A sentinel reparse proves the raw
root array-of-table source form because decoded TOML list shape alone cannot
distinguish it from inline input.

Repeated asset or dependency occurrences are retained. Slice 3 does not sort,
deduplicate, bucket, or select a winner. Later Slice 5 and Slices 8-9 own
semantic duplicate rejection.

## Canonical Immutable Values

The exact private carrier field order is:

```text
PackageManifestAsset(kind, path)
PackageManifestDependency(namespace, name, version, sha256, path)
PackageManifest(schema_version, namespace, name, version, assets, dependencies)
PackageManifestNormalizationResult(manifest_path, manifest, errors)
```

All four carriers are frozen, slotted, and hashable. Authority collections are
exact tuples containing exact carrier types. The normalization entrypoint
requires exact `ProjectRootPackageActivation` and exact `bytes`; strings,
mutable byte containers, predecoded mappings/lists, subclasses, and prebuilt
foreign collection inputs are rejected.

TOML key order, item field order, comments, and whitespace do not affect
`PackageManifest` equality or hash. Asset and dependency occurrence order and
multiplicity do. Independently parsed equal documents are value-equal and have
equal hashes; that does not establish shared provenance for later derived
products.

Normalization is limited to UTF-8/TOML decoding, schema validation, fixed field
order, and list-to-tuple conversion. It does not strip, casefold, normalize
Unicode or paths, sort, deduplicate, build an authoritative map, parse SemVer,
validate slugs/SHA-256/kinds, compare root pins, construct identity, or compute
a digest.

## Structural Path Rules

Asset `path` rejects empty text, NUL, backslash, POSIX/UNC/drive/URI absolute
forms, empty segments, `.` or `..` segments, repeated slash, and trailing
slash. Accepted text is retained exactly. No suffix or filesystem fact is
required.

Dependency `path` has the same common rejections but permits and preserves `.`
and `..` segments. Slice 6 alone determines whether its future normalized
locator remains inside the pinned project root.

No environment/tilde expansion, `normpath`, realpath, symlink handling, or
filesystem interpretation occurs.

## Error Posture And Complete Scan

Failures use ordered tuples of the existing private `ProjectDiscoveryError`
carrier:

| Failure | Existing kind |
| --- | --- |
| bytes over limit | `PROJECT_RESOURCE` |
| invalid UTF-8 or TOML, including TOML duplicates | `CONFIG_PARSE` |
| schema, source form, field, or value kind | `CONFIG_SCHEMA` |
| structural path | `PROJECT_PATH` |

No new `PIE-*` range, public enum, JSON field, CLI option, or public export is
created. Byte-limit, UTF-8, and TOML failures may return one error because no
decoded structure exists. Successful TOML parsing performs a complete scan:
canonical top-level field order, deterministic unknown-key order, then asset
occurrence order, then dependency occurrence order. Any error yields
`manifest=None`; no partial normalized value exists.

## Compatibility And Later Owners

Schema v1 legacy-flat behavior, package-absent schema v2 behavior, and Slice 2
schema-v3 activation remain exact. Existing schema-v3 source selection still
fails closed before manifest I/O. A manifest under schema v1/v2 remains
ignored even when malformed, oversized, unreadable, or a symlink.

Slice 4 owns package identity, slug/exact SemVer, pin matching, and content
digest. Slice 5 owns `MODULE_SOURCE`, typed asset catalog, unknown-kind and
normalized-path duplicate rejection. Slice 6 owns trusted locators and
filesystem trust. Slice 7 owns loading and package/module integration. Slices
8-9 own dependency validation, closure, planning, conflicts, cycles, and
rejection algebra. Slices 10-12 own inspection, hardening, and completion.

Slice 3 adds no public API, CLI, JSON, Artifact, IR, SQL, dependency, workflow,
version, fixture, golden, remote, solver, lockfile, Rust, tag, Release,
publication, signing, or attestation behavior.

## Corrected Reader Contract And Gate Boundary

`TRACKED_TARGET_UNIVERSE` is every tracked regular file.
`TEXT_READER_SOURCE_UNIVERSE` is the strict-UTF8-decodable subset. Static
reader discovery uses the latter as sources and the former as targets. Every
binary exclusion is rediscovered and bound by path, Git mode, blob OID,
content SHA-256, and byte count. Gate 2 requires `reader_additions=0`,
`digest_delta=0`, and `binary_inventory_unexplained_delta=0`.

Gate 2 keeps the real index empty and creates no branch, commit, push, PR, CI
action, tag, Release, publication, signature, or attestation. Only Gate 3 may
publish the exact externally sealed candidate through the frozen direct-main
contract.
