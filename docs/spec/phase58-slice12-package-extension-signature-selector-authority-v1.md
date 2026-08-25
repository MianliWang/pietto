# Phase 58 Slice 12 Package Extension-Signature Selector Authority v1

## Evidence And Ownership

Package manifest v2 requirements preserve only semantic `CapabilityKey`
identity. The existing extension provider requires one exact typed
`ExtensionCatalogLookupScope`, and Phase 57 forbids reconstructing physical
catalog identity from semantic subject, operation, operands, or context.
Therefore the declaring package owns a separate typed selector sidecar. It is
not an eighth key field and is not installation, catalog selection, or runtime
state.

## Package Schema v3

Schemas 1 and 2 remain exact compatibility branches. Schema 1 has no
requirements or selectors. Schema 2 requirements, including unbound
`EXTENSION_SIGNATURE` requirements, remain valid and always have an empty
selector tuple. Schema 3 retains all v2 syntax and additionally permits exact
root AOT `[[extension_signature_selectors]]`.

Each selector names an exact `requirement_position` and one closed family:
`native_type`, `scalar_function`, `aggregate`, `operator`, or `cast`. Selector
positions must exactly equal every `EXTENSION_SIGNATURE` requirement position
in requirement order. Missing, extra, duplicate, reordered, out-of-range, or
non-extension bindings fail closed.

The bound key must have domain `extension_signature`, dialect `postgresql`, and
an exact nonblank extension identity. Schema 3 with no extension requirement
requires and accepts no selector entries.

## Typed Physical Syntax

Physical type references use only `postgres_builtin` or `extension_native`
plus exact nonblank `physical_name`. `pietto_logical` is forbidden. Every
extension-native reference receives its owner directly from the bound
requirement's exact extension identity; no owner is separately authored.

- `native_type` requires one extension-native `physical_name`.
- `scalar_function` and `aggregate` require `sql_name` and ordered exact nested
  `[[extension_signature_selectors.input_types]]`; zero inputs are valid.
- `operator` requires `operator_name`, explicit `unary` or `binary` arity, and
  ordered exact nested `[[extension_signature_selectors.operand_types]]` with
  matching cardinality.
- `cast` requires exact nested source and target tables and preserves direction.

All root/nested AOT and table authorities are source-proven by parsed-value
probes. Inline arrays, ordinary tables where AOT is required, AOT where a table
is required, quoted/dotted aliases, and attachment outside the current selector
are rejected.

## Loaded-Package Adapter

`_package_extension_signature_requirement_selectors(package, binding)` reads
only the already-loaded canonical manifest. Schema 1 or an unbound package
returns `None`; schema 2 with a binding remains legacy unbound and returns
`None`; schema 3 with a binding returns exact
`ExtensionSignatureRequirementSelectors`, including an empty occurrence tuple
when no extension requirement exists.

Package object, binding collection, requirement keys, selector positions, and
extension owners retain exact authority. The adapter performs no filesystem or
TOML work, target/profile lookup, availability lookup, catalog selection,
provider construction, checking, inspection, Project Explain, or CLI work.

## Content Identity And Separation

Selector bytes are part of `pietto-package.toml` and therefore already covered
by the existing whole-package digest. No selector-specific digest exists.
Package inspection v1 remains unchanged.

Phase 67 may transport manifest v3 semantic requirements and typed selectors
without rewriting either. A selector remains package contract data, not
installation evidence.

## Current Route

After published Slice 11 the proven selector gap expands the current Phase 58
route from 16 to exactly 17 slices. Published Slices 1–11 remain unchanged;
Slice 12 owns selector authority, Slice 13 owns runtime orchestration and
zero-context adaptation, Slices 14–17 retain CLI, E2E, assurance, and completion
ownership respectively. Further expansion candidate: `NONE`.

`PHASE58_SLICE12_SELF_OWNED_OPEN = 0`
