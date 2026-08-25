# Phase 58 Slice 15 Reachability-Aware Multi-Target End-to-End Assurance v1

## Assurance Rule

Slice 15 distinguishes a state representable by a generic lower-level model
from a state reachable through the current authored project/package runtime.
The three exact assurance classes are:

```text
PRODUCTION_REACHABLE_E2E
STRUCTURALLY_UNREACHABLE_CURRENT_RUNTIME
INVALID_INPUT_REJECTED_BEFORE_PROJECT_EXPLAIN
```

Every `PRODUCTION_REACHABLE_E2E` obligation starts with real `pietto.toml`,
`pietto-package.toml`, dependency manifests, and package source bytes and then
uses the published project loader, trusted package path, runtime builder, and
representative Slice 14 CLI surfaces. No test constructs a final matrix,
inspection, Project Explain payload, envelope, or catalog selection result.

`STRUCTURALLY_UNREACHABLE_CURRENT_RUNTIME` is not simulated at the top level.
It requires both a live production-invariant proof and direct semantic tests at
the generic lower-level owner. `INVALID_INPUT_REJECTED_BEFORE_PROJECT_EXPLAIN`
requires a real authored input and the exact earlier fail-closed boundary.

## Production Authority

The assured production chain is:

```text
_run_project_explain
-> _build_project_explain_runtime
-> load_project_config
-> _locate_root_package / _load_root_package
-> _build_package_load_plan
-> _build_package_inspection_fact_set
-> _package_capability_requirement_binding
-> _package_extension_signature_requirement_selectors
-> _build_project_capability_environment
-> select_extension_catalog / ExtensionSignatureProviderContext
-> build_package_capability_checking_matrix
-> build_capability_inspection
-> Project Explain Slice 3-7 projections
-> ProjectExplainEnvelope[ProjectExplainPayload]
-> JSON v1 or deterministic text
```

The assurance corpus supplies no caller override for requirements, selectors,
profiles, targets, availability, catalogs, providers, checking, or projection.

## Reachability Ledger

| Obligation | Highest production owner | Authored prerequisite | Classification | Assurance |
| --- | --- | --- | --- | --- |
| multiple packages | package load plan | exact pinned dependency manifests | `PRODUCTION_REACHABLE_E2E` | real dependency project |
| multiple targets | project capability environment | ordered schema-v4 target declarations | `PRODUCTION_REACHABLE_E2E` | real multi-target project |
| requirements undeclared | package binding/checking | schema-v1 package | `PRODUCTION_REACHABLE_E2E` | runtime projection |
| requirements declared empty | package binding/checking | schema-v2 empty collection | `PRODUCTION_REACHABLE_E2E` | runtime projection |
| requirements declared non-empty | package binding/checking | schema-v2/v3 entries | `PRODUCTION_REACHABLE_E2E` | runtime projection |
| compatibility `BLOCKED` | capability checking | selected profile absent or foreign in availability | `STRUCTURALLY_UNREACHABLE_CURRENT_RUNTIME` | structural identity proof plus direct checker tests |
| `SATISFIED` | capability checking | supported target and provider evidence | `PRODUCTION_REACHABLE_E2E` | real schema-v3 extension path |
| `UNSUPPORTED` | capability checking | exact `explicitly_unsupported` project fact | `PRODUCTION_REACHABLE_E2E` | real profile input |
| `ABSENT` | capability checking | supported target evidence and complete provider zero-match | `PRODUCTION_REACHABLE_E2E` | real profile input |
| `UNKNOWN` | capability checking | incomplete/missing target or catalog evidence | `PRODUCTION_REACHABLE_E2E` | real profile/catalog no-match input |
| capability `CONFLICT` | capability checking | ordered distinct same-key support conclusions | `PRODUCTION_REACHABLE_E2E` | real profile input |
| empty targets | runtime zero-context adaptation | explicit empty schema-v4 environment | `PRODUCTION_REACHABLE_E2E` | all declaration states |
| catalog `SELECTED` | exact catalog selection | PostgreSQL 18 vector 0.8.6 | `PRODUCTION_REACHABLE_E2E` | bundled pgvector path |
| catalog `UNDECLARED` | exact catalog selection | valid exact target with no bundled match | `PRODUCTION_REACHABLE_E2E` | real no-match target |
| catalog `AMBIGUOUS` | generic catalog selection | multiple distinct candidates for one target | `STRUCTURALLY_UNREACHABLE_CURRENT_RUNTIME` | bundled-ledger uniqueness plus direct selector test |
| catalog `CONFLICT` | generic catalog selection | same coordinate with different content | `STRUCTURALLY_UNREACHABLE_CURRENT_RUNTIME` | bundled-ledger uniqueness plus direct selector test |
| schema-v2 extension requirement | runtime authority gap | no typed selector sidecar | `PRODUCTION_REACHABLE_E2E` | zero-target success and targeted diagnostic |
| schema-v3 extension requirement | package selector authority | exact typed selector sidecar | `PRODUCTION_REACHABLE_E2E` | selected and no-match paths |
| `PORTABLE` | portability derivation | non-empty targets and no definite gaps | `PRODUCTION_REACHABLE_E2E` | zero requirements and selected extension |
| `NOT_PORTABLE` | portability derivation | `UNSUPPORTED` or `ABSENT` cell | `PRODUCTION_REACHABLE_E2E` | mixed multi-target states |
| `INDETERMINATE` | portability derivation | no evaluated targets | `PRODUCTION_REACHABLE_E2E` | explicit empty targets |
| `DIAGNOSTIC_ERROR` | runtime result | valid schema-v2 extension package with target | `PRODUCTION_REACHABLE_E2E` | runtime and CLI exit 1 |
| `USAGE_OR_RESOURCE_ERROR` | runtime result | missing project root | `PRODUCTION_REACHABLE_E2E` | runtime and CLI exit 2 |

## BLOCKED Boundary

For every valid schema-v4 target,
`_build_project_capability_environment` resolves the selected base and overlays
from the same materialized profile objects used to construct project profile
availability. The exact objects in the composition dependency order therefore
have matching availability buckets. Missing, duplicate, wrong-kind, or
incompatible references fail earlier with `config_schema`; they do not become
a successful Project Explain `BLOCKED` result.

The generic checker continues to support
`PackageCapabilityRequirementsBlocked`, `profile_not_declared_available`, and
`profile_authority_mismatch`. Its direct owner tests remain the authority for
those lower-level semantics. The real E2E corpus asserts that valid runtime
payloads do not fabricate `BLOCKED`.

## Catalog Boundary

Current compiler-owned availability is exactly the bundled pgvector target
`PostgreSQL/18/vector/0.8.6` and pg_trgm target
`PostgreSQL/18/pg_trgm/1.6`. These exact targets are unique. Since
`select_extension_catalog` first filters by exact target, current runtime
candidate cardinality is at most one and only `SELECTED` or `UNDECLARED` is
top-level reachable.

The generic selector retains `AMBIGUOUS` and `CONFLICT` for controlled
availability supplied directly to that owner. Direct Phase 57 tests preserve
no-winner behavior. Project and package authored inputs cannot append or
replace compiler catalog availability, and Slice 15 adds no override.
Availability is not selection, and selection is not extension installation or
live database state.
Multi-source/generated catalog expansion remains later Phase 69 readiness,
not Slice 15 implementation.

## Real Corpus Guarantees

The corpus preserves dependency-first package inspection order, package-local
requirement occurrence order, explicit target order, distinct same-key
requirements across packages, package-owned typed selectors, and exact matrix
column order. One dependency selects physical `vector` while the root package
selects physical `halfvec` for the same semantic extension requirement; neither
selector overrides or collapses the other.

Across real inputs it exercises `SATISFIED`, `UNSUPPORTED`, `ABSENT`, `UNKNOWN`,
and capability `CONFLICT`, while keeping `UNDECLARED` distinct. Definite gaps
remain `UNSUPPORTED` and `ABSENT`; they make the project `NOT_PORTABLE` even
beside uncertain or conflicting cells. Empty targets remain `INDETERMINATE`
with `no-evaluated-targets`, and non-empty targets with zero requirements are
`PORTABLE`.

Representative JSON and text CLI executions must equal the same runtime
envelope, be deterministic in one environment, preserve exits 0/1/2, and emit
no private outcome, exit field, object representation, or partial payload.

## Compatibility And Lifecycle

Slice 15 changes no production source, product semantics, public JSON shape,
text behavior, CLI behavior, catalog ledger, package schema, project schema,
or availability rule. The assurance methodology correction does not expand
the 17-slice route. Slice 16 retains pure/differential, hash-seed, relocation,
Python-version, golden, and installed-wheel assurance. Slice 17 retains Phase
58 completion and Phase 59 handoff.

`PHASE58_SLICE15_SELF_OWNED_OPEN = 0`
