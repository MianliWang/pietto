# Phase 62 Slice 2 Relationship Declaration Identity, Endpoint Roles, Module-Local Resolution, And Construction States v1

## Answer And Exact Owner

Slice 2 adds the smallest private Project relationship foundation:

```text
authored relationship declaration
-> exact Project relationship declaration occurrence
-> exactly two source-ordered endpoint occurrences
-> exact Project relation targets when resolvable
-> typed concrete/non-concrete subject
```

The owner is limited to declaration/endpoint occurrence identity, module-local
ownership, existing relation resolution, existing semantic provenance,
construction state, completeness, and deterministic authority ordering.

```text
existing public RelationshipSemanticInfo
!= private Project relationship occurrence
```

## Starting Authority

| Fact | Value |
| --- | --- |
| Branch | `main` |
| HEAD / `main` / `origin/main` | `998eaa5655bbe64d4ae13b8ac03f413ce84343ff` |
| Tree | `d3a698a3a4916cac39a0852bb43ef4243876b18e` |
| Parent | `5fe550481b5de34977a59078e1f5ba9b5c90d0b0` |
| Subject | `Fix Phase 61 completion test portability` |
| Natural exact-head CI | `33463294917`, `push`, `main`, attempt `1`, successful |
| CI jobs | Python 3.12 successful; Python 3.13 successful |
| Downstream CI | generated, golden, and package smoke successful on both jobs |
| Divergence | `0/0` |
| Worktree/index/untracked | clean / clean / empty |
| Active Git operation | none |

The predecessor is the successful child of preserved failed Slice-1 commit
`5fe550481b5de34977a59078e1f5ba9b5c90d0b0` and establishes:

```text
Phase 61 = COMPLETED

Phase 62 = ACTIVE
Slice 1 = COMPLETED / PUBLISHED
Slice 2 = NEXT / NOT IMPLEMENTED
```

## Frozen Reader And Changed-path Closure

The fixed-point changed-path set is exactly:

```text
docs/roadmap.md
docs/spec/phase62-slice2-relationship-declaration-identity-endpoint-roles-module-local-resolution-construction-states-v1.md
docs/status.md
src/pietto/_project/project_relationships.py
tests/test_active_phase_lifecycle.py
tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py
tests/test_phase62_slice2_relationship_declaration_identity_endpoint_roles_module_local_resolution_construction_states.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A3/M5/D0`. The lifecycle owner remains the sole direct mutable
roadmap/status reader. The Slice-1 assurance stops treating the now-delivered
private source path as permanently absent. The validator inventory accounts
for one production file and one test file. A ninth path is
`READER_CLOSURE_DRIFT`.

## Existing Semantic And Project Authority

Slice 2 reuses without modifying:

```text
RelationshipMetadata
RelationshipEndpoint
RelationshipSemanticInfo
RelationshipSemanticEndpointInfo
ProjectLogicalModule
ProjectModuleIdentity
ProjectModuleRelationResolutionEnvironment
ProjectResolvedModuleRelationSymbol
ProjectSemanticResult
```

`build_project_relationships(...)` accepts one exact existing
`ProjectSemanticResult`. For each declaring module it obtains the one existing
relation-resolution environment and forms the semantic checker input only from
that environment's exact local/imported symbol facts.

It invokes the existing `check_relationship_metadata(...)` semantic owner once
over the exact retained module `Script`. The resulting readonly
`RelationshipSemanticInfo` and endpoint objects are retained object-for-object
by concrete Project occurrences. Their meaning is neither copied from text nor
reconstructed into a second semantic model.

Imported endpoint spelling therefore resolves only through the declaring
module's already-authorized imported relation symbol. There is no all-module
string search, alternate import resolver, re-typecheck, or ambient lookup.

## Private Carriers And Identity Laws

The dedicated private owner is
`src/pietto/_project/project_relationships.py` with empty `__all__`.

| Carrier | Exact responsibility |
| --- | --- |
| `ProjectRelationshipDeclarationIdentity` | exact module identity, module occurrence position, relationship source position |
| `ProjectRelationshipEndpointIdentity` | exact declaration identity plus endpoint position `0` or `1` |
| `ProjectRelationshipEndpointOccurrence` | exact authored endpoint, optional exact Project target, optional exact semantic endpoint |
| `ProjectRelationshipDeclarationOccurrence` | exact declaring module, authored declaration, two endpoints, optional exact semantic relationship |
| `ProjectConcreteRelationshipSubject` | complete semantic relationship and two resolved endpoint targets |
| `ProjectNonConcreteRelationshipSubject` | one typed terminal plus exact diagnostics/resolution issues, no fake concrete fact |
| `ProjectModuleRelationshipEnvironment` | complete source-ordered relationship collection for one module |
| `ProjectRelationshipSet` | complete selected-module-ordered Project result and exact semantic root |

Identity is nominal and occurrence-safe:

```text
relationship declaration occurrence != endpoint occurrence
endpoint local role/name != endpoint identity
deterministic order != semantic identity
```

Name strings, endpoint pairs, field contents, canonical bytes, hashes, object
addresses, and lexicographic order are not relationship identity. Source/module
positions locate authored occurrences; they do not select a semantic winner.

## Module Ownership Endpoint Roles And Resolution

Every declaration occurrence retains exactly one `ProjectLogicalModule` owner.
Its identity's `ProjectModuleIdentity`, module position, and source relationship
position must agree with that exact module and AST object.

Each declaration has exactly two endpoint occurrences in authored order. Each
endpoint exposes, without interpretation:

```text
authored local role
authored relation spelling
exact RelationshipEndpoint object and Span
exact ProjectResolvedModuleRelationSymbol when available
exact RelationshipSemanticEndpointInfo when admitted
```

Endpoint order and spelling do not infer left/right, parent/child, one/many,
foreign/primary, source/target, or fact/dimension. Self-relationship endpoint
identities remain distinct even when their exact target symbol is the same.
Separate relationship identities remain distinct when both target pairs and
endpoint roles are equal.

Relationship declarations remain module-local. Slice 2 adds no relationship
import, export, re-export, package asset, library, or ambient module authority.

## Construction States Completeness And Ordering

The closed state vocabulary is:

```text
CONCRETE
UNKNOWN
DEFERRED
BLOCKED
AMBIGUOUS
```

`CONCRETE` requires the existing semantic relationship object and two exact
Project relation targets. `UNKNOWN` retains unresolved endpoint evidence.
`BLOCKED` retains duplicate endpoint-role or existing module-resolution blocker
evidence. `AMBIGUOUS` retains duplicate relationship declaration or ambiguous
relation-resolution evidence. `DEFERRED` is reserved by the carrier but is not
constructible without future exact evidence and is not fabricated by the
reachable Slice-2 builder.

Every parsed relationship appears exactly once as a concrete or non-concrete
subject. A failed declaration never removes an earlier/later independent
concrete declaration. Duplicate names and same-target pairs are not
deduplicated. Non-concrete state is not a concrete relationship with unknown
fields.

Environments follow exact selected-module order. Subjects follow exact authored
relationship order. Semantic facts and diagnostics retain existing semantic
order. No sorting, global registry, interning, cache, hash identity, or winner
is introduced.

## Implementation Boundary And Non-goals

Slice 2 adds no field-match or query semantics:

```text
field correspondences                 # Slice 3
ON/WHERE equality/null analysis       # Slice 3
UNIQUE/key semantics                  # Slice 4
value FD engine                       # Slice 5
grain                                 # Slice 6
grain transfer/comparison             # Slice 7
referential coverage/cardinality      # Slice 8
relationship paths/fanout             # Slice 9
authored JOIN syntax/use              # Slice 10
Project IR JOIN region                # Slice 11
multi-fact alignment                  # Slice 12
relationship import/export            # Phase 66
SQL lowering                          # Phase 63
public relationship schema            # Phase 70
```

`SemanticModel`, `ProjectSemanticModel`, `ProjectSemanticResult`, `RelationIR`,
and existing Project IR nodes/operators remain unchanged. The new sidecar is
built explicitly from those existing roots; it is not injected into a public or
god object.

## Focused Assurance

The principal test proves:

```text
one admitted declaration -> one Project occurrence
exact module owner and source position
exactly two endpoint identities and roles
self endpoints distinct / same target retained
same-target-pair declarations distinct
same endpoint roles across declarations do not collide
local and imported target resolution through existing module authority
exact RelationshipSemanticInfo object provenance
UNKNOWN / BLOCKED / AMBIGUOUS terminals remain distinct
failed subjects do not erase independent concrete subjects
selected-module and authored relationship ordering
cwd/environment independence
frozen private carriers and winner-free exact resolution
exact upstream semantic/resolution object identity and detached-evidence rejection
```

Focused closure also retains existing relationship semantic, script IR/SQL,
Project relation-resolution, lifecycle, and reader tests. Tests remain serial,
xdist, order, cwd/environment, and Python 3.12/3.13 compatible.

## Compatibility And Production Delta

The only production addition is the private standalone relationship module.
There is no change to:

```text
grammar/generated parser
AST
public SemanticModel fields
existing relationship diagnostics/admission
script RelationIR / ScriptIR
PostgreSQL or MySQL SQL
ProjectSemanticModel / ProjectSemanticResult
Project IR eight-operator algebra
CLI / JSON / Project Explain
package/dependency/workflow/version
```

The public package and `pietto._project` re-export surfaces remain unchanged.

## Later-owner Boundaries

The exact frozen 16-Slice route remains unchanged. Slice 3 owns exact field
correspondences, condition-scope separation, and equality/null analysis. Slices
4-12 retain key/FD/grain/coverage/cardinality/path/fanout/JOIN/multi-fact
ownership. Phase 63 owns SQL and additional logical JOIN forms; Phase 66 owns
relationship assets/import/export; Phase 70 owns public exposure.

No later carrier or behavior is scaffolded here.

## Slice 3 Handoff

Slice 2 leaves Slice 3 exact private readiness for:

```text
module-owned relationship declaration identity
two exact endpoint occurrences and roles
exact authored endpoint spans/spellings
exact local/imported Project relation targets
exact existing semantic relationship/endpoint objects
complete typed concrete/non-concrete subjects
deterministic complete Project ordering
```

The only next owner after successful publication is **Phase 62 Slice 3 — Exact
Field Correspondences, ON/WHERE Separation, Equality/Null Behavior, And
Constraint-Scope Boundary**. Slice 3 is not implemented here.

## Review And Repair Accounting

Slice-1 cumulative repair accounting is terminal at `3/3` and is not reused.
Slice 2 allows at most one bounded repair batch after the complete finding set
is frozen, only for the same root, owner, and eight-path closure.

```text
Slice 2 repair batches allowed: 1
Slice 2 repair batches used before review: 0
```

Any second path set, later owner, grammar/public change, or route change is
`ARCHITECTURE_DECISION_REQUIRED`. Recurrence after a repair is
`REVIEW_RECURRENCE`.

## Gate Lifecycle And Publication

The publication candidate state is:

```text
Phase 61 = COMPLETED

Phase 62 = ACTIVE
Slice 1 = COMPLETED / PUBLISHED
Slice 2 = CURRENT / PUBLICATION CANDIDATE
Slices 3-16 = NOT STARTED
```

After focused checks and fresh rereview, start exactly one authoritative
validator:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Gate 3 requires the exact reviewed seal, one ordinary commit, one fast-forward
push, and one natural exact-head `push/main` CI attempt without rerun, dispatch,
or cancellation. Both Python 3.12/3.13 jobs and generated/golden/package smoke
must succeed.

The commit subject is:

```text
Add Phase 62 relationship identity foundation
```

The PASS title is:

```text
PASS — PHASE62_SLICE2_RELATIONSHIP_DECLARATION_IDENTITY_ENDPOINT_ROLES_MODULE_LOCAL_RESOLUTION_CONSTRUCTION_STATES_END_TO_END
```

Successful natural exact-head CI establishes without a status-only commit:

```text
Phase 61 = COMPLETED

Phase 62 = ACTIVE
Slice 1 = COMPLETED / PUBLISHED
Slice 2 = COMPLETED / PUBLISHED
Slices 3-16 = NOT STARTED

Phase 62 Slice 3
= NEXT / NOT IMPLEMENTED
```
