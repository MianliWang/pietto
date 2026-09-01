# Phase 62 Slice 7 Existing-Operator Key/FD/Grain Transfer And Grain Comparison v1

## Exact owner and authority

Slice 7 adds one private post-verification
`src/pietto/_project/project_ir_relational_properties.py` stage. Starting
authority is commit `88dbfb51a35504b0b753e299c6c90b6303a8e450`, tree
`724f2b8ce113bf01072e83f7cd4792cae4a9d8be`, natural CI `33491899112`.

```text
verified Project IR + fresh analyses + Slice-4 keys + Slice-5 FDs + Slice-6 grain
-> output-occurrence relational properties
```

## Frozen closure

The fixed closure is `A3/M5/D0`: roadmap, this contract, status, the private
owner, active lifecycle, Slice-1 live-source reader, Slice-7 focused test, and
validator inventory. A ninth path is `READER_CLOSURE_DRIFT`.

## Construction and occurrence identity

Construction follows `ProjectIRAnalysisBundle.topological_order` and exact
output refs. `origins.evaluation is analyses.stage` is mandatory. Each output
field occurrence retains its exact `ProjectIRRelationRowOutput`, output ref,
position, and row-shape evidence. Semantic field, output occurrence, derived
value class, and bit position remain distinct.

Source RELATION_INPUT seeds exact Slice-4/5 keys and FDs plus its Slice-6
FACTORIZED origin. Derived RELATION_INPUT uses its sole exact cross edge.
Unary flows preserve intrinsic factors and map keys/FDs only through exact
field images. Direct/renamed projection images are admitted; arbitrary
computed expressions are not determinant aliases.

## Keys, FDs, and nullability

Output keys are occurrence-owned determinant-class facts with complete ordered
supports and direct non-dominated frontier semantics. Surviving keys derive
direct FDs to all remaining output classes. Only STRICT direct FDs participate
in targeted closure; LAX facts remain direct. Exact NON_NULL output evidence
may upgrade LAX; raw predicate text never does.

## Operator and grain laws

ROW_FILTER, RESULT_FILTER, WINDOW_EVALUATION, FINAL_PROJECTION,
RELATION_ORDERING, and LIMIT preserve intrinsic grain and create no factor.
LIMIT 1 does not create GLOBAL grain, empty key, or empty-determinant FD.

GROUP_AGGREGATE uses the exact aggregate context and Slice-6 origin. Grouped
output activates its grouped factor and retains the forward incoming-factor
dependency. Visible group classes form a STRICT output key. Global aggregate
uses GLOBAL with zero active factors and creates no empty key/FD.

`ProjectIRProvidedLocalGrainEvidence remains unchanged` and is not the new
occurrence-owned intrinsic property.

## Comparison and boundaries

On-demand comparison freezes EQUAL, LEFT_FINER, RIGHT_FINER, INCOMPARABLE,
UNKNOWN, CONFLICT. GLOBAL is coarsest. Comparison creates no all-pairs table,
path enumeration, cache, or semantic identity.

There is no grammar/AST/generated, public schema, SQL, JOIN, relationship
cardinality, fanout, path, optional factor, multi-fact, CLI/JSON, package,
workflow, dependency, or version delta.

## Review, publication, and handoff

Slice 7 allows one bounded repair batch (`1/1` after review), one authoritative
validator, one ordinary commit, one fast-forward push, and natural exact-head
attempt-1 CI.

The single repair root is
`OUTPUT_GRAIN_DEPENDENCY_AND_COMPARISON_KERNEL_DOES_NOT_YET_USE_NORMATIVE_DIRECTIONAL_CLOSURE`.
The repair adds exact STRICT-key-backed reverse grain dependency and on-demand
directional dependency closure.

The authorized recurrence continuation consumes the second and final repair
batch for
`OUTPUT_LOCAL_KEY_FD_TRANSFER_WAS_IMPLEMENTED_AS_A_LOSSY_IMAGE_PROJECTION_INSTEAD_OF_A_COMPLETE_OUTPUT_LOCAL_VALUE_CLASS_AND_FD_KERNEL`.
It replaces member selection with complete ordered alias classes, keeps
composite determinants factorized, and adds an output-local STRICT/LAX FD
basis, dense arbitrary-width index, LHS-incident worklist, deterministic
witness, and epistemic PROVEN/NOT_PROVEN query.

```text
Slice 7 repairs: 2/2
authoritative validator starts before validation: 0/1
```

The grain-comparison recurrence continuation consumes the third and final
repair for
`GRAIN_COMPARISON_DIRECTIONAL_CLOSURE_REMAINS_NON_REPLAYABLE_AND_NON_INDEXED`.
Comparison now compiles one comparison-local factor/index domain, retains both
PROVEN or NOT_PROVEN directions, uses LHS incidents plus normative ready-rule
order, and independently replays each retained witness.

```text
Slice 7 repairs: 3/3
authoritative validator starts before validation: 0/1
```

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
Add Phase 62 key FD grain transfer and comparison
PASS — PHASE62_SLICE7_EXISTING_OPERATOR_KEY_FD_GRAIN_TRANSFER_GRAIN_COMPARISON_END_TO_END
```

After PASS, `Phase 62 Slice 8 = NEXT / NOT IMPLEMENTED`. Do not begin Slice 8.
