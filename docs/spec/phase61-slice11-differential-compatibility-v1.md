# Phase 61 Slice 11 Differential Compatibility v1

## Answer And Scope

Slice 11 proves that the published real-authored Phase 61 Project IR pipeline
has one invariant semantic and canonical observation across supported
interpreters, hash seeds, relocation, file-creation order, cwd/ambient state,
operation order, and isolated installed-wheel execution.

It is assurance-only:

```text
production delta = 0
public delta = 0
SQL / CLI / JSON delta = 0
```

The two test owners are:

```text
tests/_pietto_phase61_project_ir_differential_probe.py
tests/test_phase61_slice11_differential_compatibility.py
```

The probe owns only the bounded authored corpus and observation projection. It
creates no production carrier, subprocess framework, cache, persistent
identity, comparator normalization, or environment-specific expectation.

## Starting Authority

| Fact | Value |
| --- | --- |
| Branch | `main` |
| HEAD | `6607e7a7b127562e5f24490a0135bd7e14134744` |
| Tree | `700df2d796a30852e2076c75af5b60411e8feeea` |
| Parent | `edf68678b2a766302e654202f3fe0798c3386ffd` |
| Subject | `Add Phase 61 Project IR end-to-end pipeline` |
| Natural exact-head CI | `33355551275`, `push`, attempt `1`, successful |
| CI interpreters | Python 3.12 and Python 3.13, both successful |
| Divergence | `0/0` |
| Version | `0.1.0` |

That unique successful natural CI establishes:

```text
Phase 61 = ACTIVE
Slices 1-10 = COMPLETED
both Slice 5 prerequisites = COMPLETED
Slice 11 = NEXT / UNSTARTED
```

The clean pre-write Phase 60 differential/lifecycle/reader baseline was
`61 passed` under Python 3.13. Both trusted local supported interpreters were
available as Python 3.12.13 and Python 3.13.13.

## Frozen Reader And Changed-path Closure

Fixed-point closure covers all published Phase 61 Slice 1-10 contracts and
both Slice 5 prerequisites; the Slice 10 pipeline and real-authored fixture;
the Phase 58-60 interpreter, relocation, wheel, common-manifest, and probe
owners; differential performance-batching assurance; product-test discovery;
mutable lifecycle; exact Python source/test counts; and readers of those
readers.

The exact changed-path allowlist is:

```text
docs/roadmap.md
docs/spec/phase61-slice11-differential-compatibility-v1.md
docs/status.md
tests/_pietto_phase61_project_ir_differential_probe.py
tests/test_active_phase_lifecycle.py
tests/test_phase61_slice11_differential_compatibility.py
tests/test_validation_performance_interlude_slice2_differential_probe_runtime_decomposition_optimization.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A3/M5/D0`; there is no production path. Dynamic Phase 61 workflow and
reader discovery requires no additional edit. `tests/test_active_phase_lifecycle.py`
remains the sole direct reader of mutable status/roadmap. A ninth changed path
is `READER_CLOSURE_DRIFT`.

## Reused Differential Infrastructure

Slice 11 reuses unchanged established owners:

| Concern | Existing owner |
| --- | --- |
| Supported interpreter discovery | Phase 58 Slice 16 `_available_supported_interpreters` |
| Isolated environment construction | Phase 58 Slice 16 `_environment` pattern |
| Relocated source copy | Phase 58-60 `_relocate_source` pattern |
| Offline fresh-cache wheel build/install/origin | Phase 58 Slice 16 `_installed_python` |
| Batched one-process observation | Phase 59/60 differential probe pattern |
| Xdist isolation | resource-aware `loadfile` policy and serial fallback |
| Authoritative validation | `scripts/validate.py` |
| Installed package closure | `scripts/package_smoke.py` |

The Phase 61 probe contains no `subprocess.run`; the pytest matrix owns one
process per required environment. Each probe process batches positive Project
construction, opposite construction/query order, shifted allocation, semantic
negative Projects, verifier corruption, and pure-boundary rejections. There is
no per-assertion process startup.

## One Reviewed Common Observation

Slice 11 freezes one reviewed common observation.

Every environment is checked against one committed
`EXPECTED_COMMON_MANIFEST`. It contains human-reviewable exact relation/field
identities, states, operator sequences, direct cross edges, aggregate/window
contexts, verification, topology, queries, semantic terminals, typed negative
outcomes, package version, and explicit counts. Digests bind the complete
ordered coordinates, properties/effects, reachability, equivalence,
rewrite-readiness, each canonical inspection payload, and the complete
observation document.

The probe itself retains the complete canonical
`pietto.project-ir-inspection.v1` bytes as exact decoded UTF-8 text. Tests
compare those bytes directly across every matrix member in addition to the
fixed manifest. Test-local SHA-256 is review evidence only:

```text
test digest != Project IR identity
test digest != production content identity
```

No environment run updates or blesses the expectation dynamically. Lists and
JSON keys retain supplied order; the probe uses neither `sorted()` nor a
sorting encoder.

## Positive Authored Corpus And Compatibility Invariants

The probe faithfully retains the Slice 10 real multi-module corpus and adds one
current global aggregate solely to exercise the published `group_keys=()`
boundary. Real authored files pass through:

```text
check_project_parse_only
-> build_empty_project_semantic_result
-> build_project_ir_pipeline
```

It retains the source/table/import/re-export/downstream chain, two-hop imported
origin, shared producer with distinct uses, disconnected component, full
eight-stage relation, grouped aggregate, named window, and mixed concrete plus
non-concrete Project. It constructs no semantic root, Project IR fragment,
portable document, or accepted inspection record by hand.

The complete observation preserves:

```text
authored/module/declaration/field occurrence identity and order
separate node/output/input-slot/use coordinate domains
BAG multiplicity
current logical operator order
cross-relation direct-use authority and owner-local source_order=0
SATISFIED exact row compatibility
global aggregate group_keys=() with no synthetic local grain
window dependency roles, exact policy, and unknown effects
closed bindings
ordinary DAG acyclicity
fresh VERIFIED result and detachable analyses
winner-free typed inspection queries
canonical direct-record and derived-analysis order
```

No comparator infers a stronger equivalence or hides an authority-order defect.

## Differential Matrix

The exact fixed hash-seed set is:

```text
PYTHONHASHSEED = 0, 1, 7, 4294967295
```

All locally available supported interpreters run the same probe and common
manifest. The current validator interpreter is mandatory. Natural CI runs the
complete committed suite under Python 3.12 and Python 3.13.

Every probe constructs byte-identical Projects under unrelated roots using
normal and reverse file-creation order. Two complete construction passes also
execute Project A then Project B and Project B then Project A, while independent
typed inspection queries run in opposite orders. Results remain equal without
sorting, proving that filesystem enumeration, current-project state, query
order, and a hidden mutable cache are not authority.

Source-checkout runs use distinct cwd values and distinct irrelevant
`PIETTO_SLICE11_IRRELEVANT` values. Project relocation, copied-source
relocation, and combined interpreter/seed/relocation cases retain exact bytes.
No absolute root, cwd, ambient value, runtime scope, or object address appears.

The installed-wheel case reuses the offline fresh-cache helper, copies the
probe outside the checkout, and runs against a temporary wheel target.
`pietto.__file__` must be below that target and outside this repository. The
complete observation and canonical bytes equal source-tree execution.

The compared origins are exactly: source checkout, relocated source, and
isolated installed wheel.

## Runtime Identity And Portable Equality

Each probe builds equivalent Projects with equal explicit zero starting
coordinates under distinct runtime snapshot scopes. Their runtime node refs are
unequal while their complete semantic observations and canonical bytes are
equal.

A separate build reuses the exact semantic result with explicit starting
coordinates `(7, 11, 5, 5)`. Its first node position is `7` and its canonical
bytes differ from the zero-start payload exactly where the portable format
records coordinates.

```text
portable equality != occurrence identity
equal semantics != shared runtime scope
different explicit coordinates remain observable
```

## Negative-state Differential Assurance

The Slice 10 missing-field query remains a real semantic `UNKNOWN` terminal in
the primary mixed Project. It has no node or edge and remains visible through
the exact typed why-not query.

A second real authored Project contains a two-relation cycle plus an independent
`rows -> okay` component. The cycle relations remain typed `BLOCKED` terminals
with zero nodes/uses and exact semantic-fact evidence; the independent concrete
component survives, the complete representable Project verifies, and canonical
inspection remains stable.

One copied test-only Slice 7 stage omits an aggregate context. The independent
verifier returns typed `INVALID` with the same ordered `EVALUATION_CONTEXT`
issue family and optional plan-node coordinate in every environment. Exception
class or text is not compared.

This is the fixed typed INVALID issue family and coordinate contract.

The pure-boundary subset checks exact normalized status and coordinates for:

```text
wrong format marker
non-dense node ref coordinate
wrong-domain ref
dangling ref
section-order violation
invalid use endpoint
```

These malformed documents are test-only derivatives of the real positive
inspection document. They do not duplicate Slice 9's complete rejection suite.
They preserve normalized pure-boundary rejection status and coordinates.

## Optimized Execution And Zero Delta

The matrix retains the established outer-variant independence and batches all
same-environment observation work in one probe. It uses module-scoped
pytest-owned temporary roots, has no fixed shared scratch path, no test-order
dependency, no result/PASS cache, and remains safe under serial and xdist
`--dist=loadfile` execution.

The performance interlude reader verifies that the four seeds, supported
interpreters, relocation/source/wheel branches, two construction orders, and
absence of subprocess/cache/sorting code remain explicit. Slice 11 claims no
new performance gain and changes no performance infrastructure, so
`PERFORMANCE_GAIN_NOT_PROVEN` is not applicable.

Slice 11 adds no semantic admission, operator/property, optimizer, rewrite,
recursion/fixpoint, JOIN/grain/fanout, public Project IR schema, deserializer,
cache, persistent identity, SQL/backend/dialect, package metadata, dependency,
workflow, version, tag, Release, signing, or attestation behavior.

## Focused Assurance

The focused Slice 11 module must pass unchanged in both modes:

```text
UV_PYTHON=3.13 uv run pytest -q tests/test_phase61_slice11_differential_compatibility.py
UV_PYTHON=3.13 uv run pytest -q -n 2 --dist=loadfile tests/test_phase61_slice11_differential_compatibility.py
```

This is the required serial and xdist --dist=loadfile assurance pair.

Ruff plus production/test Pyright, the differential performance reader,
lifecycle/static-reader closure, and adjacent Slice 10 E2E also remain green.

## Slice 12 Handoff

After successful natural exact-head CI:

```text
Phase 61 remains exactly 12 slices
Slices 1-11 = COMPLETED
Slice 12 = NEXT / UNSTARTED
```

The only next owner is:

```text
Phase 61 Slice 12 — Completion Audit And Phase 62 Handoff
```

Slice 11 performs no completion audit and makes no Phase 62 readiness claim.

## Gate Lifecycle And Publication

Gate 2 runs focused serial and xdist matrices, Ruff, production/test Pyright,
one complete review, at most one same-root repair batch, fresh rereview, and
exactly one authoritative validator:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Central package smoke follows because installed-wheel behavior is in scope.
Generated and golden inputs do not change; natural CI still checks them.

Gate 3 rebinds the predecessor, stages exactly the sealed eight-path tree,
makes one ordinary commit, performs one fast-forward push, and observes the
unique natural exact-head CI without dispatch, cancel, or rerun.

The exact commit subject is:

```text
Add Phase 61 differential compatibility assurance
```

The published PASS title is:

```text
PASS — PHASE61_SLICE11_DIFFERENTIAL_COMPATIBILITY_END_TO_END
```

Successful natural exact-head CI completes Slice 11 without a status-only
follow-up commit. Slice 12 remains next / unstarted.
