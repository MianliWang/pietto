# Phase 62 Slice 11 Binary Project IR JOIN Region v1

## Starting Authority

Slice 11 starts from commit
`b26e394e5f8238f2c69d86844fb15f7bcb52362b`, tree
`fcbd2b5cf661ae9b8793371c9ae750768fe164e3`, and natural exact-head
`push/main` CI `33559281666`, attempt 1, success. Slices 1–10 are completed and
published. Slice 11 is the sole current publication candidate.

## Architecture

Slice 11 is one post-base extension:

```text
base ProjectIRProjectPlan
+ base ProjectIRRelationalPropertyStage
+ exact ProjectRelationshipUseSet
+ base plan ending allocation
-> same-snapshot binary JOIN-region stage
```

The extension reuses the base `ProjectIRSnapshotScope` and continues plan-node,
output, slot, and use coordinates. `project_ir_pipeline.py` and
`project_ir_composition.py` remain unchanged. The original JOIN-bearing
semantic fact and single-relation fragment remain
`DEFERRED / AUTHORED_JOIN_DEFERRED` and non-concrete.
The sole new production owner is private `project_ir_joins.py`.

## Identity And Structural Topology

`ProjectIRBinaryJoinIdentity` is exact `ProjectJoinUseIdentity` plus authored
path-step position. JOIN kinds are the separate binary `INNER` and `LEFT`; no
ninth unary `ProjectIRLogicalOperatorKind` exists.

Every binary JOIN owns two input slots with ordinals 0/1, two
`ProjectIRJoinInputUseOccurrence` values, one plan node, and one joined-row
output. Multi-hop uses emit one binary node per exact path step. The first step
uses the source binding's standalone output on the left; later path steps use
the previous JOIN output. Every later authored JOIN clause also uses the
current accumulated row structurally, even when its condition maps through an
earlier binding slice.

One ledger is all-or-none. Any non-concrete authored use produces a typed
zero-allocation region and no concrete prefix. Independent ledgers remain
independent.

## Joined Row Fields And Match Mapping

`ProjectIRJoinedRowShape` is plan-local and fabricates no concrete module
semantic state. Fields are ordered accumulated-left then exact right input,
without name deduplication. Each `ProjectIRJoinedRowField` retains original
`ProjectRowField` evidence, its exact JOIN-input introduction use, current
position, ordered nulling JOIN refs, and effective output-local nullability.

```text
semantic field identity != joined field instance != value class != bit position
```

Every base-match correspondence is recovered from its exact
`ProjectConcreteRelationshipCondition` and mapped through exact binding/path
field instances. No names, key facts, JOIN-local refinement, or winner search
replace that authority. Intermediate multi-hop slices remain internal.

## Actual Effects And NULL_EXTENSION

Forward `AT_MOST_ONE` preserves source multiplicity; otherwise the hop may
multiply. LEFT always guarantees structural-left survival. INNER guarantees
survival only when its exact source slice has no prior null-generation and the
hop minimum is `AT_LEAST_ONE`.

INNER adds no nulling. LEFT may null-extend its right side when the hop permits
zero matches or the source slice was already null-generated. Newly introduced
right fields receive the current JOIN ref; carried left fields retain all
earlier refs. LEFT remains an outer-join barrier even when null extension is
proven impossible.

`ProjectIRProvidedNullExtension` is the positive `NULL_EXTENSION` property and
contains the complete joined-field provenance. Outputs with no nulling retain
exact `NOT_APPLICABLE`. Ordering remains `UNKNOWN`.

Nulling provenance makes a field `NULLABLE`. Otherwise an exact matched INNER
field is `NON_NULL`; a LEFT right match is `NON_NULL` only when actual nulling
is impossible. Original semantic-field nullability is never mutated.

## Key And FD Transfer

Left candidate keys survive only under forward at-most-one evidence. A
right-only key also requires reverse at-most-one plus an exact current
source-binding determinant image that is a left key. LEFT nulling downgrades
right-only keys to LAX. Composite candidates are formed only from left-key ×
right-key pairs and pass through the existing non-dominated frontier.

Left-local FDs remain. Right-local FDs remain, with determinant-sensitive
STRICT-to-LAX handling under LEFT nulling. Exact forward/reverse cross-side
rules use directional maximum evidence. Equality adds bidirectional STRICT
rules only for INNER or LEFT with impossible actual nulling. Surviving keys
derive key-to-all-output rules. The existing arbitrary-width output FD index
and STRICT closure remain the sole algorithm.

## Grain Factor Uses And Dependencies

`ProjectJoinGrainFactorIdentity` is exact base factor identity plus
introduction-use ref plus ordered nulling JOIN refs. Repeated/self/grouped
uses remain occurrence-distinct without new base origins. Carried factors keep
their identity; right factors receive the exact current use and optional
nulling ref. Active factors are the ordered union; two evidenced GLOBAL inputs
remain GLOBAL without fake factors.

Forward at-most-one derives source-binding factor uses -> right factor uses.
Reverse at-most-one derives the reverse only when right factors are not
null-generated. Value FDs are never reused as grain dependencies.

## Frozen Boundaries And Closure

The complete changed-path closure is `A3/M9/D0`, 12 paths: five exact
production paths plus the three documentation and four test/core paths. No
historical reader required modification.

Slice 11 adds no joined scalar namespace, unary tail, Script IR, SQL JOIN
lowering, pipeline/composition/verifier mutation, join reordering, path search,
global cache, or Slice-12 multi-fact/chasm behavior.

Assurance covers one-hop/multi-hop topology, accumulated-left use, all-or-none
allocation, branching/self-role identity, actual effects, transitive nulling,
positive/NOT_APPLICABLE null properties, key/FD transfer, directional grain
dependencies, and 144-class Python-int FD masks.

One repair batch is permitted after the complete finding set is frozen. The
complete review froze and repaired the single root
`JOIN_REGION_CARRIERS_AND_TRANSFER_DO_NOT_CLOSE_EXACT_SOURCE_SLICE_AND_OUTPUT_STATE`
in repair batch 1/1. Effects and region topology are now derived or replayed
from exact retained evidence; cumulative null provenance owns property
availability; reverse FDs cover the complete source-binding slice; empty GLOBAL
source factors remain exact empty evidence; and no-nulling keys recompute
strength from output-local nullability.

The authoritative validator is:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Publication uses one ordinary commit and one fast-forward push followed by
unique natural exact-head Python 3.12/3.13 CI.

```text
Add Phase 62 binary Project IR joins
PASS — PHASE62_SLICE11_PROJECT_IR_BINARY_JOIN_REGION_MULTI_INPUT_TOPOLOGY_NULL_EXTENSION_PROPERTY_TRANSFER_END_TO_END
```

After PASS, `Phase 62 Slice 12 = NEXT / NOT IMPLEMENTED`. Do not begin Slice
12.
