# Phase 58 Slice 11 Project Capability Environment Authority v1

## Scope And Ownership

Slice 11 adds project configuration schema v4 and one detached private project
capability-environment authority. Packages continue to own capability
requirements. The project owns authored static profiles, exact target-to-profile
selection, ordered supplied overlays, and the ordered evaluated-target
denominator. The compiler owns exact availability declarations for bundled
catalogs. Availability is not selection, installation, preference, or live
database state.

Slice 11 performs no package loading, requirement binding, capability checking,
matrix or inspection construction, catalog selection, provider construction,
Project Explain projection, JSON/text serialization, or CLI work.

## Project Schema v4

Schemas 1–3 remain exact compatibility branches. Schema 4 retains
`ProjectCompilationMode.PACKAGE_ROOT`, requires the existing exact `[package]`
table, forbids `[sources]`, and requires exact bare root:

```toml
[capability_environment]
```

The allowed schema-v4 top-level keys are exactly `schema_version`, `package`,
and `capability_environment`. Inline, quoted, dotted, or unrelated nested
environment construction is rejected. An explicit environment with no profile
or target AOT entries is valid and represents exactly zero evaluated targets;
a missing environment is invalid.

`ProjectConfig` has exact fields `schema_version`, `sources`,
`compilation_mode`, `root_package`, and trailing optional
`capability_environment`. Schemas 1–3 retain `None`; schema 4 requires an exact
`ProjectCapabilityEnvironmentConfig`.

## Authored Profiles And Facts

Profiles are authored only through exact
`[[capability_environment.profiles]]`. Their exact identity/release, kind, and
database target reuse `CapabilityProfileReference`, `CapabilityProfileKind`,
and `CapabilityProfileTarget` without normalization or fallback.

A BASE profile has a database target and no base or extension fields. An
OVERLAY has an extension target and one exact base reference. Profile facts are
authored only through exact
`[[capability_environment.profiles.facts]]`. Each fact reuses the existing
closed `CapabilityKey` vocabulary and accepts only `supported` or
`explicitly_unsupported`. Exact duplicate `(support, CapabilityKey)` pairs in
one profile are invalid; opposite supports for one key remain representable.

Every authored fact becomes one existing `CapabilityFact` with disposition
`NONE` and exactly one evidence entry:

```text
source = PROJECT
source_path = pietto.toml
source_reference = capability_environment.profiles[P].facts[F]
```

Dialect and extension are copied from the exact key. Backend and reason remain
`None`; compiler-provider evidence is not copied.

## Evaluated Targets And Composition

Targets are authored only through exact
`[[capability_environment.targets]]`. Each has explicit database family/release
and one exact BASE profile reference. Supplied overlays are authored only
through exact `[[capability_environment.targets.overlays]]` and retain authored
order.

References resolve only against the exact project-defined profile authority.
Unresolved references, kind mismatch, family/release mismatch, duplicate
overlay references, duplicate extension identities, composition blockers, and
exact duplicate selected targets fail closed with `CONFIG_SCHEMA` at
`pietto.toml`. Targets sharing a database identity remain distinct when their
explicit profile selections differ.

Composition calls only the existing `compose_capability_profiles`. Its
dependency order and effective fact order remain authoritative; Slice 11 adds
no second graph algorithm.

## Availability

The compiler profile availability ledger is exactly empty. The project ledger
contains one occurrence per project profile in declaration order and must
produce exact `DeclaredCapabilityProfileAvailabilityReady` through the existing
availability builder.

Compiler extension-catalog availability is exactly:

```text
0 -> PGVECTOR_V086_POSTGRESQL18_CATALOG
1 -> PG_TRGM_V16_POSTGRESQL18_CATALOG
```

Both declarations have owner `COMPILER` and project `None`. Their exact target,
catalog reference, canonical bytes, and content digest are retained. No ltree,
PostGIS, dynamic discovery, selection result, or provider context is created.

## Compatibility And Lifecycle

Schema-v3 source selection retains its exact message. Schema v4 exits before
candidate discovery with:

```text
Schema-v4 capability environment does not use project source selection.
```

Phase 58 remains active. Slices 1–10 are completed, Slice 11 is current, and
Slice 12 remains next, unstarted, and unauthorized. Natural exact-head CI owns
Slice 11 completion without a status-flip commit.

`PHASE58_SLICE11_SELF_OWNED_OPEN = 0`
