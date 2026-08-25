# Phase 58 Slice 13 Project Explain Runtime Builder v1

## Scope And First Missing Edge

Slice 13 closes the first production edge from one explicit project root to the
already-published `ProjectExplainEnvelope[ProjectExplainPayload]`. The private
builder is `_build_project_explain_runtime(project_root)` in
`pietto._project_explain.runtime_builder`. It accepts no caller overrides for
package requirements, package selectors, project targets/profiles, or compiler
catalog availability.

The builder orchestrates, without replacing, these existing authorities:

```text
load_project_config
-> trusted root-package location/loading and package load plan
-> PackageInspectionFactSet
-> package requirement bindings and typed selector sidecars
-> ProjectCapabilityEnvironmentAuthority
-> exact catalog selection and extension provider contexts
-> package capability matrices and capability inspections
-> Project Explain Slice 3-7 projections and composition
-> ProjectExplainEnvelope[ProjectExplainPayload]
```

Package and dependency order, requirement occurrence order, explicit target
order, supplied-overlay order, catalog selection outcomes, and projection order
remain those of the existing owners. The runtime builder does not sort,
deduplicate, reload, reparse, or reconstruct their facts.

## Project And Package Authority

Only project schema v4 supplies the required capability environment. Schemas
1-3 remain valid existing configuration contracts but are not reinterpreted as
an explicitly empty environment. A non-v4 root therefore produces a private
usage/resource failure rather than an implicit target.

Package manifests retain their published semantics:

- schema v1 has no requirement binding;
- schema v2 preserves undeclared, declared-empty, and ordered declared
  requirements, including legal unbound `EXTENSION_SIGNATURE` requirements;
- schema v3 retains the same requirements and supplies the exact package-owned
  typed selector sidecar.

The builder obtains both values only from the already-loaded package adapters.
It never derives a selector from `CapabilityKey` strings and never permits the
project to override a dependency package selector.

## Target, Catalog, And Provider Authority

Each package matrix receives package-specific target-context objects that share
the exact project-owned composition and profile-availability objects for each
target. The context's extension provider authority may differ by package
because selectors are package-owned. Project Explain target agreement therefore
requires exact shared composition and availability identity, not identity of
the whole package-specific context carrier.

For every schema-v3 selector and target, the exact extension release comes from
the target's one matching selected overlay. The builder combines that release
with the explicit database family/release and requirement extension identity to
form the exact existing `ExtensionCatalogTarget`, calls
`select_extension_catalog`, and passes the resulting selection with the
unchanged typed selector to `ExtensionSignatureProviderContext`.

No matching overlay is a deterministic
`extension_catalog_target_mismatch` diagnostic. The builder does not choose an
extension release, target, catalog, or profile by fallback. Availability is not
selection, and selection is not installation or runtime presence.

With non-empty targets, a schema-v2 `EXTENSION_SIGNATURE` requirement lacks the
typed authority required for complete checked-extension evidence. The package
remains valid, but Project Explain construction fails with an existing
`not_evidenced` diagnostic rather than inventing a selector or returning a
partial payload.

## Zero-Target Compatibility

The canonical capability matrix, capability inspection, and capability pure
boundary accept `contexts = ()`.

```text
undeclared binding:
    contexts = columns = rows = ()

declared-empty binding:
    contexts = columns = rows = ()
    declaration identity remains present in inspection/projection authority

declared non-empty binding:
    contexts = columns = ()
    one row per requirement occurrence in exact order
    every row.cells = ()
```

No provider is invoked for zero targets. No target, UNKNOWN, BLOCKED, checked
cell, or catalog fact slot is synthesized. Existing non-empty matrix/checking
semantics are unchanged. The published empty Slice 4 matrix, empty Slice 5
evidence, and `INDETERMINATE / no-evaluated-targets` portability derivation are
used unchanged.

## Runtime Result And Failure Boundary

`ProjectExplainRuntimeBuildResult` contains only:

```text
outcome
envelope
```

The exact private outcomes are `success`, `diagnostic_error`, and
`usage_or_resource_error`. They are not serialized into Project Explain JSON
v1 and add no public exit-code field.

Success carries the complete existing payload and may retain ordered non-error
package diagnostics. Failure carries no payload and at least one detached error
diagnostic. Existing parser/semantic diagnostic codes and ordering are retained;
existing `ProjectDiscoveryErrorKind` values identify project/package
usage-resource failures; the two runtime authority gaps above use existing
capability reason values. Invalid or host-identifying paths are not inserted
into detached locations.

## Compatibility And Non-goals

Slice 13 adds no public Python export, JSON field, text renderer, CLI route,
exit-code implementation, package resolver, package loader, catalog selector,
provider algorithm, checker, portability algorithm, filesystem traversal,
network access, database connection, installed-extension inference, registry,
timestamp, random identity, tag, or Release.

`pietto explain <file>` remains unchanged. `pietto explain --project` belongs
to Slice 14. Broad multi-target E2E, differential/golden assurance, and Phase
59+ provenance or package-transport work remain Slices 15-17 and later phases.

## Lifecycle

Phase 58 remains on its published 17-slice route. Slice 13 is the current
runtime-builder owner; Slice 14 remains next and unstarted. Natural exact-head
CI owns Slice 13 completion without a status-only follow-up commit.

`PHASE58_SLICE13_SELF_OWNED_OPEN = 0`
