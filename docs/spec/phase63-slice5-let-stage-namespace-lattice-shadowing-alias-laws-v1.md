# Phase 63 Slice 5 LET Stage Namespace Lattice Shadowing Alias Laws v1

## Decision And Live Authority

Phase 63 Slice 5 adds one private occurrence-complete LET analysis over the
exact Slice-4 joined binding environment. It retains immutable source-ordered
namespace prefixes and delegates field discovery and scalar type composition to
their existing owners. It does not begin Slice 6.

The live starting authority was rebound before mutation:

```text
commit 095c8e27cfc23c7fe0e520628c51c1ade884d318
tree   acd03a63aa28d303baa70b7438f052718823630d
CI     33718336042
workflow CI
event push
branch main
attempt 1
conclusion success
Python 3.12 success
Python 3.13 success
```

## Existing LET Authority

The existing `semantic.let_bindings` policy remains normative. LET bindings are
source ordered; earlier references are allowed; self and forward references
fail closed; duplicate names, input shadowing, and projection collisions fail
closed; aggregate calls remain invalid in LET context. LET values are bare-only
and projection aliases remain output names.

Slice 5 reuses the existing `PIE-S2329`, `PIE-S2330`, `PIE-S2308`, and scalar
kernel diagnostics. It does not add a public diagnostic code or modify
single-file LET behavior. The existing direct-unaliased selected LET exception
is retained for private Project compatibility.

## Occurrence Identity And Name Admissibility

One Phase-63 LET occurrence is the exact root plus source ordinal plus exact
`LetBinding` AST object. Name is a lookup surface, not identity. No UUID, hash,
derived string, or second declaration domain exists.

Name admissibility is computed against the complete clause before sequential
typing. If a spelling is duplicated, all occurrences of a duplicate spelling
are inadmissible; the first occurrence is not admitted as a winner.

A name also remains inadmissible when it collides with any visible joined field
spelling, authored binding name, retained input relation name, or conflicting
projection output. Ambiguous visible field spellings still shadow. Hidden
multi-hop fields do not shadow because they are not name-visible. Relation
names remain collision evidence but never become qualified lookup aliases.

## Immutable Namespace Chain

The exact local chain is:

```text
POST_JOIN_INPUT -> LET_BINDING(i) -> POST_LET
```

Every namespace retains the exact Slice-4 root, authored relation bindings,
visible fields, hidden structural fields, and complete authored LET occurrence
tuple. `POST_JOIN_INPUT` has no LET values. `LET_BINDING(i)` has only admitted
values from exact earlier ordinals. `POST_LET` contains all authored LET values
in order and exists only on concrete success.

Namespaces and values are frozen tuples. LET values retain their exact
occurrence, expression, prefix namespace, existing-kernel `ValueType`, and
expression-keyed type evidence. A transient name-to-type dictionary may feed
the existing kernel, but it is not retained as identity authority:

```text
compiled index != normative fact
```

No joined `RowSchema`, field-name map, global symbol table, registry, or cache
is created.

## Reference Lookup And Type-Kernel Reuse

For `NameExpr`, lookup first checks the exact admitted earlier LET value. If no
LET value matches, it delegates to Slice-4 winner-free unqualified field
discovery. A LET and field candidate may not compete; that would be root
incoherence rather than precedence.

For `DottedNameExpr`, lookup always delegates to Slice 4. Qualified LET
references are not introduced, and `relation_name` remains unavailable as a
qualifier fallback.

Self, forward, or otherwise unavailable authored LET names are retained as
dependency blockers and never fall back to a field. Projection outputs never
enter any namespace: `projection alias != row/LET namespace binding`.

Exact concrete field leaves seed the existing expression-keyed type map.
Earlier LET types use the existing `bare_value_types` seam. The unchanged
`infer_row_expression` kernel remains the sole function, operator, and
nullability compositor. Function callees remain function identities rather
than scalar reference leaves.

## Closed Non-Concrete Results

Concrete success requires every occurrence to be name-admissible,
dependency-valid, field-resolved, and known through the existing kernel. It
publishes one exact final `POST_LET` namespace.

A non-concrete result publishes `post_let = None`. It retains every authored
occurrence and immutable prefix plus exact inadmissible occurrences, dependency
reference roots, non-concrete Slice-4 resolutions, unknown-type occurrences,
and existing diagnostics. Partial admitted prefixes may explain failure but do
not escape as final successful authority.

## Projection And Later-Stage Boundary

Explicit projection collisions remain fail-closed, while the existing exact
unaliased direct selected LET form remains compatible. Projection aliases are
never LET-expression leaves or members of `POST_JOIN_INPUT`, a binding prefix,
or `POST_LET`.

Slice 5 adds no post-JOIN row-property bridge, WHERE stage, grouping,
aggregate-over-JOIN behavior, window computation, QUALIFY, final projection,
Project IR unary tail, SQL, Arrow, executor, or public behavior. Those remain
with Slice 6 and later exact owners.

## Differential Compatibility

Equivalent single-input cases are compared directly with current
`semantic.let_bindings` using its Project-compatible direct-selection setting.
Duplicate names, self/forward dependencies, field and relation shadowing,
explicit projection collision, and direct unaliased selected LET decisions
remain identical. Current Phase-43 inline aggregate/grouped behavior is neither
reimplemented nor changed.

## Exact Changed-Path Closure

| Status | Path |
| --- | --- |
| `A` | `src/pietto/_project/project_scalar_namespaces.py` |
| `A` | `docs/spec/phase63-slice5-let-stage-namespace-lattice-shadowing-alias-laws-v1.md` |
| `A` | `tests/test_phase63_slice5_let_stage_namespace_lattice_shadowing_alias_laws.py` |
| `M` | `docs/roadmap.md` |
| `M` | `docs/status.md` |
| `M` | `tests/test_active_phase_lifecycle.py` |
| `M` | `tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py` |

The closure is exactly seven paths, `A3/M4/D0`. The mechanical Python
inventory transition is production `166 -> 167` and tests `409 -> 410`.

The frozen 16-Slice route, public contracts, grammar/generated output,
package/dependency/workflow/version state, SQL/Arrow/executor behavior, and all
Phase-64+ implementation remain unchanged.

## Assurance And Publication

Hermetic assurance covers immutable prefixes, exact occurrence identity,
sequential dependencies, duplicate invalidation, field/binding/relation
shadowing, projection laws, qualification, existing-kernel typing and
diagnostics, LEFT nullability, multi-hop hidden fields, and single-input LET
differential compatibility. The principal test reads no mutable lifecycle
document.

After focused tests, targeted Pyright, Ruff, format checks, and one complete
rereview, the authoritative local validator runs exactly once:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Publication is one ordinary non-amend commit named
`Add Phase 63 joined LET namespaces`, one normal fast-forward push to `main`,
and natural exact-head CI. A failed head is preserved and never rerun.

## Slice 6 Handoff

Successful natural exact-head CI completes Slice 5 without a status-only
follow-up commit. Phase 63 remains `ACTIVE`; Slices 1–5 are
`COMPLETED / PUBLISHED`; Slice 6 becomes `NEXT / NOT IMPLEMENTED`; Slices 7–16
remain `NOT IMPLEMENTED`.

The exact next owner is Phase 63 Slice 6 — Post-JOIN Row Semantics,
Nullability, Lineage And Property Bridge. Slice 6 is not begun here.
