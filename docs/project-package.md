# Projects and packages

Pietto has an explicit, compiler-only local project model. Project and package
features do not add database execution, runtime loading, a package registry,
or network access.

## Project invocation and configuration

Project commands receive an explicit root:

```bash
pietto check --project PATH
```

Pietto does not silently discover a project from the working directory.
Configuration is declarative and fail closed. The current schema and JSON
contracts are [configuration v1](spec/pietto-config-v1.md) and
[project CLI/JSON v2](spec/project-cli-json-v2.md).

A minimal source-selection configuration is:

```toml
schema_version = 1

[sources]
include = ["models/*.pietto"]
```

Selection is deterministic and project-relative. Paths use `/`, are checked
lexically, and are contained by the pinned root before trusted reads. Resource
limits bound configuration bytes, selected inputs, source bytes, and parser
work. Failures remain ordered project diagnostics rather than partial success.

## Schema compatibility

- Schema v1 preserves the legacy-flat project model.
- Schema v2 activates explicit logical modules and module-local semantic facts.
- Schema v3 selects the package-root activation branch.

The modes are explicit compatibility boundaries. A newer branch does not
silently fall back to an older catalog or source-selection path, and private
facts do not automatically become public CLI/JSON/IR/SQL fields.

## Trusted source identity

The project root, configuration file, and selected sources are opened through
checked descriptors. Pietto validates path containment, regular-file posture,
pre/post-read identity, byte limits, and UTF-8 before accepting source text.
Symlink and replacement races fail closed.

The trusted-source SHA-256 is computed over the exact accepted opened bytes.
It is product content identity, not governance hashing. Module/package layers
may derive private identity and lookup facts from it without reopening the
source or treating equal rendered text as equal authority.

## Modules

Each selected explicit-module input has a stable logical module identity and a
source-ordered local catalog. Imports, aliases, exports, and re-exports retain
exact declaration kind, owner, target, occurrence, and source order.

The module graph preserves complete import evidence separately from canonical
edges. Cycles, missing targets, collisions, blocked resolution, diamonds, and
multi-hop provenance do not select an arbitrary winner. Cross-module type,
enum, shape, source, table, and query resolution preserves nominal identity,
row facts, origin, provenance, lineage, and deterministic diagnostics.

Module catalogs, binding environments, graphs, attribution, package-neutral
identity, and inspection documents are private compiler facts. Public output
changes require a separate compatibility decision.

## Package activation, manifest normalization, and root validation

Schema v3 carries one immutable package-root activation. The current private
manifest normalizer accepts caller-supplied bytes for the logical
`pietto-package.toml` input; it performs no filesystem access.

The normalizer:

- requires the exact root array-of-table structure for assets; dependencies
  are optional and normalize to an empty tuple when absent;
- enforces UTF-8, TOML, size, key, value, and lexical-path boundaries;
- preserves occurrence order and multiplicity;
- reports the complete deterministic error set;
- rejects foreign or mixed-root construction at the canonical boundary; and
- retains each nonempty declared dependency `sha256` field without yet
  verifying it against loaded package content.

A second private pure boundary runs only after successful normalization. It
defines logical package identity as the exact, case-sensitive, Unicode-exact
`(namespace, name)` pair; validates and preserves one strict SemVer 2.0.0
release string; forms the exact identity-plus-version coordinate; requires the
activation and manifest identity/version declarations to agree exactly; and
validates the root activation `sha256` as exactly 64 lowercase hexadecimal
characters. Dependency declarations remain structurally retained and otherwise
unvalidated.

A third private pure boundary types the already-normalized root assets without
tightening structural normalization. Structural manifests continue to retain
every nonempty asset kind, source order, and multiplicity. The typed boundary
accepts only the exact `module_source` kind, requires its normalized
package-relative path to end in lowercase `.pietto`, and rejects every later
occurrence of an already-declared package-local path. A successful catalog
retains the exact validated root package and one source-ordered typed value per
manifest asset. It performs no filesystem access, content read, digest work, or
module construction.

A fourth private boundary locates the explicit schema-v3 root package beneath
the exact pinned project root. It rejects symbolic-link directory traversal,
pins the canonical local directory and its filesystem identity, and retains the
exact caller root and activation authorities. Location does not read the
manifest or assets, compute package-content digests, or resolve dependencies.

A fifth private boundary trusted-reads the non-symlink regular manifest and
typed assets, verifies their inspected/opened/final identities, and rejects
physical aliases between distinct declared assets. Whole-package content uses
the frozen byte framing:

```text
b"pietto-package-content-v1\0"
|| RECORD("pietto-package.toml", exact_manifest_bytes)
|| RECORD(asset_0.path, exact_asset_0_bytes)
|| ...

RECORD(path, content) =
    U64_BE(len(path.encode("utf-8"))) || path.encode("utf-8")
    || U64_BE(len(content)) || content
```

`U64_BE` is exactly eight unsigned big-endian bytes. Assets retain typed-manifest
source order. No newline, Unicode, or TOML normalization occurs; host, project,
activation, and canonical filesystem paths never enter the digest, so
relocation does not change it. Only a digest matching the root activation pin
may produce package-owned, package-local parsed modules. Dependency declarations
remain retained manifest data and are not loaded or validated in this boundary.

A sixth private boundary validates every ordered dependency occurrence as one
exact identity, strict SemVer coordinate, whole-package digest pin, and local
directory locator. Authored `.` and `..` components normalize relative to the
declaring package directory; escape above the pinned project root fails closed.
Each dependency then uses the same contained-directory, trusted-byte, D1, pin,
and parsed-module loading as the root package.

The local load plan uses iterative declaration-order DFS and emits successful
packages in postorder, including the root as the final entry. Exact duplicate
occurrences remain separate edges. Cycles, conflicting identities/releases/
digests/physical roots, and diamonds produce private blocker evidence without
selecting a winner; Slice 9 owns their final diagnostic product. Every loaded
package remains an independent compilation island, so equal package-local
module paths are never flattened or merged.

The seventh private boundary converts existing load-plan blockers into ordered,
canonical rejection diagnostics without re-running traversal or filesystem
loading. Cycle messages retain the DFS occurrence chain; conflict facts retain
every evidenced cause; diamond messages retain both incoming authorities under
the no-winner policy. Diagnostic text uses only package coordinates, authored
and resolved logical paths, and occurrence positions—never host paths,
filesystem identities, or object ids. Exact duplicate edges accepted by the
planner remain accepted and produce no rejection.

This is a private package foundation, not a package manager. It adds no version
ranges, solver, remote or registry access, installation, lockfile, public
package graph, public diagnostic code, recovery behavior, database behavior, or
public package API. The private inspection boundary below remains internal.

The eighth private boundary derives one package inspection and one canonical
byte payload from an exact load-plan result. Successful inspections preserve
the complete declaration-order DFS postorder, the root as the final entry,
typed assets in manifest order, every dependency occurrence with multiplicity,
authored and resolved logical paths, exact coordinates, verified package
digests, dependency pins, and owner-bound target positions. Rejected and error
inspections preserve ordered project errors, parser diagnostics, and canonical
blocker diagnostics, including cycle chains, complete conflict reasons, and
both diamond incoming authorities without selecting a winner.

The retained plan-result authority derives both the structured inspection and
its `pietto.package-inspection.v1` canonical bytes, so callers cannot supply or
graft either product. Projection and serialization consume only already-loaded
private carriers: they do not read files, traverse dependencies, inspect the
host, or include canonical host paths, filesystem identities, raw manifests,
raw module sources, or ASTs. This package inspection remains distinct from the
existing private module inspection. Public exposure remains Phase 58 work.

Package inspection projects the authority-derived value into explicit immutable
tagged records and evaluates them through a total, data-only pure boundary. That
evaluator is the one production owner of the frozen canonical bytes: accepted
documents reproduce `pietto.package-inspection.v1` byte-for-byte, while
malformed documents return a closed normalized status and structural
coordinates without echoing supplied content. Python object-identity admission
remains outside the portable contract.

Frozen package differential vectors retain literal expected bytes and rejection
outcomes for successful graphs, ordered errors and diagnostics, cycles,
conflicts, diamonds, malformed scalars, and structural corruption. Cross-process
and supported-interpreter checks make the boundary ready for an independent
implementation without adding one here.

The settled Phase 55 local package foundation is one explicit compiler-only
chain: schema-v3 activation -> structural manifest -> exact identity and typed
assets -> trusted loading and D1 content identity -> exact local dependency
plan -> deterministic rejection -> private inspection -> portable pure
evaluation and differential compatibility. Later ownership remains separate:
Phase 58 owns public package inspection and explain; Phase 59 owns richer local
package graph, provenance, and lineage; Phase 66 owns additional package asset
kinds; Phase 67 owns remote package management and trust; and Phase 68 owns a
solver, lockfile, and the first Rust-kernel decision.

## Inspection and portable boundaries

Private module inspection serializes current compiler facts canonically and
without host-path or authority leakage. The portable pure boundary and
differential vectors protect deterministic representation, exact construction,
and anti-graft behavior. They are retained current invariants even though some
test owners still have historical Phase names.

Private package inspection is a separate schema-v3 product over package loading
and rejection authority. Its package-specific pure evaluator does not merge
with or alter the module inspection format or differential corpus.

## Evidence-path compatibility

Some private capability facts intentionally carry exact retained spec, plan,
and test paths as evidence identity. Those paths remain tracked until a
separately authorized product change migrates the facts and their consumers.
Their historical-looking names do not make them lifecycle status authority;
[status](status.md) and live Git/CI own lifecycle state.
