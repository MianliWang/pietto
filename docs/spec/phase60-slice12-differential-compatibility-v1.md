# Phase 60 Slice 12 Differential Compatibility v1

## Answer And Scope

Slice 12 proves that the published advanced-window system is invariant across
supported interpreter, hash-seed, relocation, ambient-state, command-order,
and packaging conditions. It adds assurance only: no production, grammar,
generated, golden, package metadata, dependency, workflow, public schema,
backend support, or semantic-law change.

The predecessor is commit
`a8c6accfc6c41194b346434abe313d59f41b9520`, tree
`9083ca99661fba6478f0200aee2e631cf033948f`, with successful natural
exact-head CI `33290389421` on push attempt 1 for Python 3.12 and 3.13.

The test reuses the established Phase 58 interpreter/relocation/wheel matrix,
the Phase 59 graph serializers and production package builder, and the paired
CLI helper. The Phase 60 probe owns only its bounded authored corpus and
observation projection; it contains no subprocess harness, persisted PASS
cache, sorting, final-authority constructor, or replacement general framework.

## One Common Observation

Every environment consumes one reviewed common expectation. The observation
begins from real `.pietto` files and retains ordered normalized evidence for:

```text
semantic result type
named/inline use shape and target ordinal
effective frame, exclusion, NULL treatment, and nth direction
relation strategy and exact reachable/emission declaration order
ordered relation and inline target evidence
PostgreSQL/MySQL SQL or exact backend diagnostic
Project semantic provenance and ordered dependency occurrences
private inspection canonical bytes/digest and named records/links
package version
```

The full observation bytes and each detailed target are digest-locked in
addition to the human-reviewable summaries. Runtime-only scopes, object
addresses, absolute roots, CWD, and irrelevant environment values are absent;
two independently constructed authored/project/package graphs retain unequal
runtime identities while producing equal semantic/IR/decision/SQL/canonical
observations. No `sorted()` or semantic normalization hides source order.

## Differential Matrix

The matrix uses:

```text
PYTHONHASHSEED = 0, 1, 7, 4294967295
Python 3.12 and Python 3.13 when available
repository source, relocated source, and isolated installed wheel
two unrelated project roots per observation
unrelated CWD and irrelevant ambient environment value
combined Python 3.12 + seed 1 + relocation when available
combined Python 3.13 + seed 4294967295 + relocation when available
```

All available supported interpreters and the current validator interpreter are
required. The installed-wheel case begins from an empty install cache and
proves `pietto.__file__` belongs to the isolated target rather than the
repository checkout.

Each fresh observation evaluates PostgreSQL then MySQL and MySQL then
PostgreSQL in opposite construction/paired-CLI orders. Repeated same-target
decision and emission calls must remain identical. The positive corpus reuses
Slice 11 byte-exact sources for PostgreSQL `NATIVE_REORDER`, MySQL
`NATIVE_PRESERVE`, PostgreSQL `INLINE_EXACT`, ROWS/RANGE/GROUPS, all EXCLUDE
states, effective defaults, RESPECT NULLS, FROM FIRST, Project semantic
provenance/data lineage, and private inspection.

## Backend-Negative Compatibility

Eight real named-window sources remain semantically valid and fail target
lowering identically in every environment:

```text
PostgreSQL: IGNORE NULLS, FROM LAST, RANGE offset
MySQL: GROUPS, explicit EXCLUDE, IGNORE NULLS, FROM LAST, RANGE offset
```

Each retains `NOT_LOWERABLE`, ordered typed evidence, zero SQL artifacts, and
one exact `PIE-B1000` diagnostic message/location class. The PostgreSQL IGNORE
NULLS source separately reaches a CONCRETE Project result with named semantic
provenance and data dependencies intact.

Focused validation runs the Slice 12 module in both serial and xdist
--dist=loadfile modes; the module-scoped matrix uses only pytest-owned
temporary roots and no shared fixed scratch path.

## Preserved Boundary

Slice 12 does not expand frame-value input expressions beyond the Slice 9
direct-field/scalar-literal contract. In particular,
`first_value(aggregate_output_alias)` is a Slice 13 readiness/deferred subject
for the appropriate later aggregation/grain owner. Slice 12 also adds no
QUALIFY, aggregate-as-window, Project IR, JOIN/grain, Phase 64 RANGE typing,
reusable package windows, new dialect, or public lineage/schema field.

## Reader Closure

The exact Slice 12 changed-path allowlist is:

```text
docs/roadmap.md
docs/spec/phase60-slice12-differential-compatibility-v1.md
docs/status.md
tests/_pietto_phase60_window_differential_probe.py
tests/test_active_phase_lifecycle.py
tests/test_phase60_slice12_differential_compatibility.py
tests/test_validation_performance_interlude_slice2_differential_probe_runtime_decomposition_optimization.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A3/M5/D0`, eight paths. The Slice 2 performance reader recognizes the
new probe/harness reuse while preserving its historical Phase 58/59 timing and
process-count evidence. Dynamic Phase-60 discovery requires no edit.

## Lifecycle And Publication

The candidate records Phase 60 active, Slices 1–11 completed, Slice 12
current, and Slice 13 next/unstarted. Natural exact-head CI owns completion
without a status-only follow-up commit. The exact ordinary commit subject is:

```text
Add Phase 60 differential compatibility assurance
```
