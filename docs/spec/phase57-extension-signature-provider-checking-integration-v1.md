# Phase 57 Slice 8 Extension-signature Provider And Checking Integration v1

## Purpose And Authority

Phase 57 Slice 8 connects exact typed extension-signature requirement selectors
and precomputed extension-catalog selections to the existing private capability
lookup, requirement checker, and target matrix. It adds no catalog discovery,
selection, installation evidence, runtime inspection, SQL lowering, or public
output.

The semantic `canonical_capability_provider_inputs(key)` remains unchanged.
Without Slice 8 target authority, `EXTENSION_SIGNATURE` still resolves to
`Unknown(NOT_EVIDENCED)`.

## Provider Context Authority

`ExtensionSignatureProviderContext` retains one exact
`ExtensionSignatureRequirementSelectors` sidecar and an ordered tuple of
`ExtensionSignatureProviderSelectionOccurrence` values. Each selection
occurrence binds one exact requirement position to one already-computed
`ExtensionCatalogSelectionResult`.

The selection positions must equal the selector positions exactly and in source
order. Missing, duplicate, extra, non-selector, and out-of-order bindings fail
construction. The checker additionally requires the selector sidecar's exact
requirement collection to be the binding's requirement collection; a separately
constructed equal collection is foreign authority.

One context may bind multiple extension-signature requirements to independent
selection results. The provider, checker, and matrix never call
`select_extension_catalog`.

## Target Affinity

The exact closed bridge is:

```text
CapabilityKey.dialect == "postgresql"
-> database_family == "PostgreSQL"
```

The bridged database family must equal
`selection.requested_target.database_family`, and `CapabilityKey.extension`
must directly equal `selection.requested_target.extension_identity`. Every
candidate and selected catalog must retain the selection's exact requested
target. An internally inconsistent selection is malformed context; a valid
selection whose target does not match the key produces
`Unknown(EXTENSION_CATALOG_TARGET_MISMATCH)`.

Database, extension, and catalog releases remain outside `CapabilityKey`.
There is no release fallback, aliasing, normalization, or compatibility
inference.

## Selection And Lookup Algebra

Selection outcomes project before entry lookup:

| Slice 6 outcome | Provider result |
|---|---|
| `UNDECLARED` | `Unknown(EXTENSION_CATALOG_UNDECLARED)` |
| `AMBIGUOUS` | `Unknown(EXTENSION_CATALOG_SELECTION_AMBIGUOUS)` |
| `CONFLICT` | `Unknown(EXTENSION_CATALOG_SELECTION_CONFLICT)` |
| `SELECTED` | exact selector-scoped catalog lookup |

Only `SELECTED` consumes `selection.selected_catalog`. Catalog coordinate or
content conflict is selection uncertainty, not capability `Conflict`.

Lookup compares only:

```text
group.scope == selector.scope
```

for the exact five families `NATIVE_TYPE`, `SCALAR_FUNCTION`, `AGGREGATE`,
`OPERATOR`, and `CAST`. It never parses `CapabilityKey.subject`, `operation`,
`operands`, or `context`, never crosses families, and performs no alias,
coercion, overload, default, variadic, polymorphic, or cast-assisted matching.

An exact declaration is provider-eligible only when it is both
`EXACT_MATCHABLE` and `DIRECT_SQL_SURFACE`. `IMPLEMENTATION_SUPPORT` and
`UNCLASSIFIED` produce
`Unknown(EXTENSION_CATALOG_NOT_PROVIDER_ELIGIBLE)`.

## Exact Groups And Evidence Projection

An eligible `UNIQUE` exact group projects one `CapabilityFact` using the exact
requested key, `SUPPORTED`, and neutral `NONE` disposition.

An eligible `CONSISTENT_DUPLICATE` projects one semantic fact. Its private
provider authority retains the complete group and selected catalog, so all
corroborating declarations and source provenance remain available.

`EVIDENCE_CONFLICT` projects one distinct same-key supported fact per group
member and therefore produces the existing capability `Conflict`. Group member
order is the deterministic Slice 5 order. Existing `CapabilityEvidence` with
`SEMANTIC_CATALOG` source is used; each reference contains catalog coordinate,
content SHA-256, group-member position, evidence-occurrence position, and source
position. Member plus evidence-occurrence positions keep facts distinct even
when upstream source positions overlap or repeat. Logical source locators are
used as paths; host paths, cwd, timestamps, and object identities are absent.

The constructor-closed `ExtensionSignatureProviderAuthority` separately
retains the exact requirement, selector occurrence, selection occurrence,
selected catalog, scope, exact group, relevant unmodeled blockers, consulted
completeness group, and projected `CanonicalCapabilityProviderInputs`. Its
retained authority is sufficient for check construction to recompute and
reject grafted provider inputs.

## Cataloged-unmodeled Relevance

`CATALOGED_UNMODELED` is not omission. Before completeness is consulted,
potential relevance is decided from already-structured family-local fields:

- native type: exact `type_identity` equality;
- scalar or aggregate: exact callable identity equality when present,
  otherwise exact `declaration.sql_name` equality within the same family;
- operator: exact operator identity equality when present, otherwise exact
  `operator_name` plus arity equality within the same family;
- cast: every structurally exact endpoint must equal its corresponding
  selector endpoint; one or two unmodeled endpoints with no exact mismatch are
  potentially relevant.

No unmodeled spelling is parsed. A relevant declaration produces
`Unknown(EXTENSION_CATALOGED_UNMODELED)` and is retained in the provider
authority. A declaration proven unrelated by this rule does not affect the
requested scope.

## Scoped Completeness

Completeness is consulted only when there is no exact group and no relevant
unmodeled blocker, using only an exactly equal lookup scope:

| Exact completeness state | Provider result |
|---|---|
| `COMPLETE` | existing `Absent(NO_CATALOG_ENTRY)` |
| `INCOMPLETE` | `Unknown(EXTENSION_CATALOG_COMPLETENESS_INCOMPLETE)` |
| `CONFLICT` | `Unknown(EXTENSION_CATALOG_COMPLETENESS_CONFLICT)` |
| no group | `Unknown(EXTENSION_CATALOG_COMPLETENESS_UNAVAILABLE)` |

No whole-catalog or whole-family completeness is inferred. Entry conflict,
unmodeled evidence, and completeness at another scope remain lookup-local and
cannot poison or complete the requested scope.

## Checker And Matrix Integration

`check_package_capability_requirements` accepts one optional
`ExtensionSignatureProviderContext`. Its existing four-argument call retains
predecessor behavior. Context-backed extension checks retain their exact
`ExtensionSignatureProviderAuthority`; non-extension and unbound extension
checks continue reconstructing the semantic canonical provider.

The existing status algebra and order are unchanged:

1. any target/provider capability conflict -> `CONFLICT`;
2. otherwise any found explicitly unsupported fact -> `UNSUPPORTED`;
3. otherwise provider absence -> `ABSENT`;
4. otherwise any unknown -> `UNKNOWN`;
5. otherwise two supported facts -> `SATISFIED`.

Target-profile omission remains incomplete `Unknown(NOT_EVIDENCED)` and catalog
success does not create target support.

`CapabilityCheckingTargetContext` retains an optional provider context beside
composition and profile availability. Provider-context object authority is part
of duplicate-context identity, so equal composition/availability with different
provider contexts may form distinct columns. Caller column order remains exact.
The matrix calls the canonical checker once per column and performs no catalog
lookup, status aggregation, best/worst target choice, or portability
classification.

## Compatibility And Non-scope

The existing `CanonicalCapabilityProviderInputs`, `Found`, `Absent`, `Unknown`,
`Conflict`, `CapabilityFact`, `CapabilityKey`, requirement collection, profile,
and target lookup schemas remain unchanged. The semantic canonical provider is
zero-delta for every old caller and non-extension domain.

`CapabilityInspectionFormat.CAPABILITY_INSPECTION_V1` remains exactly
`pietto.capability-inspection.v1`. Inspection continues projecting only its
existing provider completeness, reason, lookup, facts, and status fields. It
adds no catalog coordinate, selector, selection, digest, completeness, or
catalog-provenance field. The Phase 56 differential corpus and its accepted
bytes remain unchanged. Slice 5 canonical catalog bytes and SHA-256 identity
remain unchanged.

Slice 8 adds no concrete extension fact or catalog, PostgreSQL core catalog,
installation or database introspection, `CREATE EXTENSION`, registry, remote
transport, package asset, solver, lockfile, parser, AST, IR, diagnostic, CLI,
JSON, SQL lowering, emitter behavior, dependency, version bump, tag, Release,
package publication, signing, or attestation.

The package remains `0.1.0`. Live Git plus successful natural exact-head CI
owns Slice 8 completion. The candidate lifecycle keeps Slice 8 current and
Slice 9 unstarted; no post-CI status-flip commit is required.
