# Phase 58 Slice 10 Package Capability Requirement Declaration v1

## Scope

Slice 10 adds package-owned capability requirement declaration authority. It
extends `pietto-package.toml` and constructs one private binding from an
already-loaded root or dependency package. It does not select targets,
profiles, providers, or catalogs; check requirements; build Project Explain;
or add CLI/public behavior.

## Manifest Schema

`PackageManifest.schema_version` accepts exact non-Boolean integers `1` and
`2`. Schema 1 retains its existing package identity, ordered assets, ordered
dependencies, validation, loading, and content-digest behavior, and rejects
`capability_requirements` as unsupported. Schema 2 retains those surfaces and
adds one optional exact root table:

```toml
[capability_requirements]
namespace = "example.capabilities"
name = "runtime"
```

Both declaration identity fields are required exact nonblank strings. The
table permits only `namespace`, `name`, and the decoded `entries` collection.
The table must be source-proven as exact bare root
`[capability_requirements]`; inline, quoted, dotted, or unrelated nested
equivalents are rejected.

Requirement entries use only exact nested array-of-table headers:

```toml
[[capability_requirements.entries]]
domain = "logical_type"
subject = "Int"
operands = []
```

An authored `entries` assignment, inline-table array, ordinary table, quoted
header, or dotted alternate is invalid. Entries require `domain` and an exact
array of nonblank string `operands`. They optionally accept exact nonblank
string `subject`, `operation`, `context`, `dialect`, and `extension`. At least
one of `subject` or `operation` is required, and `extension` requires
`dialect`. Strings and operand order are preserved without trimming, case
folding, aliasing, sorting, grouping, or deduplication.

The closed schema-v2 domain vocabulary is:

```text
logical_type
literal
parameter
scalar_function
unary_operator
binary_operator
comparison
null_test
clause
aggregate
window_function
expression_stage
conversion
dialect_lowering
extension_signature
```

Future `CapabilityDomain` additions require an explicit manifest-v2
compatibility review. Every syntax or semantic rejection uses
`ProjectDiscoveryErrorKind.CONFIG_SCHEMA` and the logical manifest path.

## Normalized Model

`PackageManifestCapabilityRequirements` is a frozen, slotted private carrier
with exact fields `identity` and `keys`. It reuses
`CapabilityRequirementCollectionIdentity` and an authored-order tuple of the
existing `CapabilityKey`; no duplicate key carrier exists. Exact duplicate
keys in one declaration are invalid.

`PackageManifest` has exact fields, in order:

```text
schema_version
namespace
name
version
assets
dependencies
capability_requirements
```

The final field defaults to `None`, preserving valid internal schema-v1
constructors and equality/hash behavior with the same trailing value.

## Declaration States

| Input | Binding |
| --- | --- |
| Schema 1 | `None` |
| Schema 2, table absent | `None` |
| Schema 2, declared table with no entries | non-`None`, zero occurrences |
| Schema 2, declared entries | non-`None`, all occurrences in authored order |

Undeclared and declared-empty are distinct states.

## Package Binding

`_package_capability_requirement_binding(package)` accepts exact
`LoadedRootPackage` or `LoadedDependencyPackage` values. It reads only the
already-loaded package's canonical manifest. For a declaration, it reuses the
exact declaration identity and keys, assigns zero-based source-order
positions, builds one `CapabilityRequirementCollection`, and binds it to the
caller's exact package object.

The adapter performs no filesystem access, TOML parsing, package reload,
dependency traversal, project override, target/profile lookup, capability
checking, provider work, or catalog work. Root and dependency packages retain
only their own declarations.

## Content Identity And Separation

The existing package-content digest already covers exact
`pietto-package.toml` bytes. A requirement-only byte change therefore changes
that digest; Slice 10 adds no second digest and makes no signing or attestation
claim.

`PackageInspection`, its package carrier, and its canonical serialization do
not gain capability requirement fields. Slice 10 constructs no capability
inspection, checking matrix, target context, profile availability, extension
catalog availability, Project Explain payload, CLI route, public export,
generated artifact, or golden.

## Lifecycle

Phase 58 remains active. Slices 1-9 are completed, Slice 10 is the current
owner, and Slice 11 remains next, unstarted, and unauthorized. Natural
exact-head CI owns Slice 10 completion without a status-flip commit.

`PHASE58_SLICE10_SELF_OWNED_OPEN = 0`
