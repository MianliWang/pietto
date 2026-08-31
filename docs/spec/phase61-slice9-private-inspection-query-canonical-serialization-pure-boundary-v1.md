# Phase 61 Slice 9 Private Project IR Inspection v1

## Answer And Exact Owners

Slice 9 adds the private read-only observation pipeline:

```text
fresh VERIFIED ProjectIRAnalysisBundle
-> exact runtime inspection
-> typed winner-free queries
-> portable immutable document
-> one canonical private byte payload
```

The two exact owners are:

```text
src/pietto/_project/project_ir_inspection.py
src/pietto/_project/project_ir_pure_boundary.py
```

The first retains exact runtime authority for inspection and queries, then
projects portable records. The second contains no Project IR runtime object and
owns total validation plus the only canonical encoder.

```text
Project IR authority != inspection != query result != canonical bytes != persistent identity
```

## Starting Authority

| Fact | Value |
| --- | --- |
| Branch | `main` |
| HEAD | `577511b9dd6dbf14dbd5dc3710bee0a3d86b92be` |
| Tree | `c4bc106f54d31939c4681d4d1dd6bb10d519f78c` |
| Parent | `455629a9edc93622180788ff4cba8b76776c4e9f` |
| Subject | `Add Phase 61 Project IR verifier` |
| Natural exact-head CI | `33349469530`, `push`, attempt `1`, successful |
| Divergence | `0/0` |
| Version | `0.1.0` |

That publication establishes Slices 1-8 as completed and Slice 9 as the only
next owner. The clean pre-write inspection/pure/Project-IR/lifecycle focused
baseline was `150 passed`.

The live architecture audit selected the Phase 55 pattern:

```text
authority-derived inspection
-> portable document
-> pure evaluator
-> canonical bytes
```

Phase 59 supplied typed-coordinate and winner-free-query laws, but its
single-module direct encoder was not reused because Slice 9 requires a stronger
two-owner portable boundary. Historical Phase 54/55/59 formats remain
unchanged.

## Frozen Reader And Changed-path Closure

Fixed-point closure covers all published Phase 61 Slice 1-8 contracts; the
Slice 8 verified bundle; Phase 54/55/59 inspection and pure-boundary
conventions; package/product-test discovery; lifecycle readers; exact Python
source/test counters; and readers of those readers.

The frozen allowlist is exactly:

```text
docs/roadmap.md
docs/spec/phase61-slice9-private-inspection-query-canonical-serialization-pure-boundary-v1.md
docs/status.md
src/pietto/_project/project_ir_inspection.py
src/pietto/_project/project_ir_pure_boundary.py
tests/test_active_phase_lifecycle.py
tests/test_phase61_slice9_private_inspection_query_canonical_serialization_pure_boundary.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A4/M4/D0`. Package and Phase 61 product-test discovery are dynamic.
`tests/test_active_phase_lifecycle.py` remains the sole direct mutable
status/roadmap reader. A ninth changed path is `READER_CLOSURE_DRIFT`.

## VERIFIED Analysis Admission

`build_project_ir_inspection` accepts exactly one `ProjectIRAnalysisBundle`.
Its retained verification must be `VERIFIED` with no issues. `INVALID`, a Slice
7 stage, a Project plan, or a same-scope substitute cannot enter inspection.

The exact bundle stage and every fresh analysis object are retained by identity.
Inspection does not rerun parsing, semantic analysis, name/type resolution,
Project IR construction, policy/effect derivation, verification, or analysis.
There is no alternate unverified entry point.

## Complete Private Inspection Projection

`ProjectIRInspection` retains canonical exact tuples for:

```text
snapshot summary
concrete and non-concrete relation fragments
nodes and logical operators
typed current outputs
input slots and direct uses
cross-relation edges
provided and required properties
row-shape compatibilities
effects
aggregate, window-operator, and window-result contexts
verification result
reverse-use index
topological order
transitive reachability
semantic-equivalence assessments
rewrite-readiness assessments
```

Section formation validates object-for-object identity against the exact Slice
8 bundle and Slice 7 plan. It preserves relation order, ref order, operator
order, use order/source order, context order, pair order, multiplicity, shared
producers, disconnected components, and non-concrete terminals. It performs no
sorting or deduplication.

`ProjectIRInspectionProduct` derives the portable document and canonical bytes
as init-only products. Building it allocates no Project IR ref and mutates no
stage, plan, structure, bundle, allocation, ref, property, or analysis.

## Typed Winner-free Query Surface

Private query functions accept exact typed runtime refs or exact
`ProjectDeclarationOccurrenceIdentity` values and return complete canonical
tuples for:

```text
relation occurrence
node/output/input-slot/use ref
incoming and outgoing direct uses
cross edge and its compatibility
properties and effects for one output
aggregate/window evaluation contexts
non-concrete why-not fragment
reachability entry
equivalence assessment
rewrite readiness
```

Queries scan the canonical tuples. No stored mutable index, name resolver,
free-form query language, first/latest/nearest/best result, or name-oriented
winner exists.

```text
query != resolution authority
query result != semantic authority
```

## Portable Identity And Record Order

The private format marker is exactly:

```text
pietto.project-ir-inspection.v1
```

Runtime snapshot scope is implicit and absent from portable data. Every Project
IR coordinate is `ProjectIRPortableRef(domain, position)` with one of four
closed domains:

```text
plan_node
output_value
input_slot
use
```

A bare integer is never a ref. Relation semantic identity is represented by
module path, module/declaration positions, declaration kind, and declared name.
Final semantic fields retain positions/names and stable type/nullability/role
facts. Stage-local scalar fields retain only stage position/name facts; no
module row-field identity is fabricated.

The closed record order is:

```text
header
fragment
node
output
input_slot
use
cross_edge
property
compatibility
effect
evaluation_context
reverse_use
topological
reachability
equivalence
rewrite_readiness
end
```

Direct Project records follow canonical relation/ref order. Only the
`topological` section follows derived topological order. Serialization never
reorders direct topology through an analysis.

## Pure Total Boundary And Rejections

`project_ir_pure_boundary.py` contains only explicit immutable portable values:

```text
text
bounded non-negative integer
boolean
closed enumeration
typed portable ref/ref tuple
ordered text/enumeration tuple
explicit absence
ordered field/record/document tuples
```

`evaluate_project_ir_document` is total for exact portable documents. It
returns `OK` plus bytes or one closed normalized status with deterministic
record/field coordinates. Rejections never echo supplied text.

Validation covers:

```text
empty/missing/duplicate header or end
unknown marker, record, or enumeration
field arity/key/tag and missing/extra payload
negative/out-of-range integer
section order and trailing records
duplicate/non-dense typed ref coordinates
dangling or wrong-domain refs
fragment concrete/non-concrete state and root/count consistency
producer/output/slot/use endpoint relations and one-use-per-slot
semantic-use/cross-edge correspondence
provided/required property and compatibility completeness
one exact effect per output
aggregate/window/result context completeness
reverse-use equality
topological validity
transitive reachability equality
canonical concrete-fragment pair order and dimension status
rewrite-readiness blockers/status
```

The pure owner imports no Project IR runtime carrier and uses no filesystem,
cwd, environment, locale, clock, randomness, network, database, process/thread
state, registry, or cache.

## Single Canonical Serializer

`serialize_project_ir_inspection` follows exactly:

```text
inspection
-> _project_ir_pure_document
-> evaluate_project_ir_document
-> canonical bytes
```

The pure module contains exactly one `_encode_document`. The inspection module
contains no byte encoder. There is no reference serializer, comparison
serializer, parser, deserializer, JSON schema, or public format.

Text escaping is explicit for separators, slash escapes, control characters,
and surrogate code points. Record/field/tag order is closed and deterministic.

## Canonical Bytes Are Not Identity

Freeze:

```text
canonical-byte equality != Project occurrence identity
canonical-byte equality != semantic equivalence
canonical-byte equality != rewrite readiness
canonical-byte equality != persistent cache identity
canonical-byte equality != content identity
```

Two independent scopes with the same explicit coordinates and facts serialize
identically while their runtime refs remain unequal. Different explicit start
coordinates remain visible and change the payload. No SHA, digest, `hash()`,
object address, `repr()`, or scope token is created or encoded.

## Determinism Immutability And Zero Mutation

All summary, inspection, product, portable value/ref/field/record/document, and
outcome carriers are frozen and slotted. Runtime sections are exact tuples;
portable sections are explicit tuples.

Building, querying, projecting, and serializing leave object-for-object
unchanged:

```text
ProjectIREvaluationContextStage
ProjectIRProjectPlan
ProjectIRStructuralStage
ProjectIRAnalysisBundle
starting/ending allocation
all Project IR refs
```

Hash seed and unrelated cwd do not alter records or bytes. There is no ambient
state, mutation, serialization cache, or bytes-derived lookup.

## Focused Assurance

Positive tests use real authored parsed/analyzed multi-module Projects through
the complete Slice 5-8 path. They cover source/query chains, a cross-module
re-exported edge, a shared producer, a disconnected component,
aggregate/window contexts, and one non-concrete terminal.

Focused checks prove:

```text
VERIFIED-only admission
complete exact inspection section identity/order
typed relation/node/output/slot/use queries
complete incoming/outgoing buckets
cross-edge/compatibility and property/effect queries
evaluation-context and non-concrete why-not queries
reachability/equivalence/rewrite-readiness queries
no name winner; equal authored occurrences remain distinct
direct order remains distinct from topological analysis order
accepted portable reference document
all targeted normalized malformed-document terminals
one pure canonical encoder and inspection delegation
fresh scope with equal coordinates -> identical bytes and unequal refs
shifted coordinates -> different observable bytes
hash-seed/cwd independence
no address/repr/digest/deserializer
zero Project IR allocation/mutation
public/CLI/JSON/SQL/script RelationIR zero-delta
```

The complete Slice 9 file passed as `7 passed` after the bounded review repair.
Tests use pytest-owned paths and isolated subprocesses and remain xdist/serial
compatible.

## Integration Boundaries And Non-goals

Slice 9 changes no Slice 2-8 carrier, constructor, verifier, analysis, semantic
law, identity, or allocation. It adds no expression serializer, public Project
IR schema, CLI/JSON/API exposure, deserializer, persistent cache/storage,
content-addressed identity, optimizer/rewrite, recursion/fixpoint, JOIN/grain,
fanout, parser/AST/grammar, diagnostic, SQL/backend behavior, Project Explain
field, version change, tag, Release, signing, or attestation.

Historical module/package/package-graph inspection and pure formats remain
unchanged. Their helpers are not coupled into the new Project IR format.

## Slice 10 Handoff

After successful natural exact-head CI:

```text
Phase 61 remains exactly 12 slices
Slices 1-9 = COMPLETED
Slice 10 = NEXT / UNSTARTED
```

The only next owner is:

```text
Phase 61 Slice 10 — Real Authored Multi-Module Project IR E2E
```

Slice 9 implements none of that broader E2E owner.

## Gate Lifecycle And Publication

Gate 2 uses focused tests, Ruff, and Pyright; freezes the complete finding set;
permits at most one same-root repair batch; performs a fresh rereview; and
starts exactly one authoritative validator:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Local package smoke is required because two packaged private modules are added.
Generated and public golden inputs do not change; natural CI still checks them.

Gate 3 rebinds the predecessor, stages exactly the sealed eight-path tree,
makes one ordinary commit, performs one fast-forward push, and observes the
unique natural exact-head CI without dispatch, cancel, or rerun.

The exact commit subject is:

```text
Add Phase 61 Project IR inspection
```

The published PASS title is:

```text
PASS — PHASE61_SLICE9_PRIVATE_INSPECTION_QUERY_CANONICAL_SERIALIZATION_PURE_BOUNDARY_END_TO_END
```

Successful natural exact-head CI completes Slice 9 without a status-only
follow-up commit. Slice 10 remains next / unstarted.
