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

Every root or dependency `sha256` declaration durably means an expected
whole-package-content SHA-256. The complete trusted manifest-plus-asset byte
set and its framing do not yet exist, so this boundary does not compute or
verify package content and does not hash manifest bytes as a substitute.
Whole-package framing, computation, and verification belong to trusted loading;
dependency-pin validation belongs to dependency loading and planning.

This is a private package foundation, not a package manager. Package loading,
package-content digest verification, module integration, dependency planning,
registry access, remote fetch, installation, lock resolution, database
behavior, and public package APIs remain separately authorized work.

## Inspection and portable boundaries

Private module inspection serializes current compiler facts canonically and
without host-path or authority leakage. The portable pure boundary and
differential vectors protect deterministic representation, exact construction,
and anti-graft behavior. They are retained current invariants even though some
test owners still have historical Phase names.

## Evidence-path compatibility

Some private capability facts intentionally carry exact retained spec, plan,
and test paths as evidence identity. Those paths remain tracked until a
separately authorized product change migrates the facts and their consumers.
Their historical-looking names do not make them lifecycle status authority;
[status](status.md) and live Git/CI own lifecycle state.
