# Validation Performance Interlude Slice 1 Baseline Profiling And Route Lock v1

## Answer And Scope

Interlude Slice 1 establishes the unoptimized baseline, attributes current
validation cost, and freezes the remaining evidence-backed route. It implements
no performance optimization and changes no Pietto production, parser, AST,
semantic, IR, SQL, diagnostic, CLI, JSON, generated, golden, or package
behavior. Test policy, assertions, test selection, and validation coverage are
not weakened.

Phase 59 is completed by live Git plus natural exact-head CI. The Validation/
Test Performance Optimization Interlude is active. Phase 60 remains blocked
and not activated.

## Starting Authority

The live rebound baseline is:

| Fact | Value |
| --- | --- |
| `HEAD == main == origin/main == live remote main` | `6a3d5d54ce728b60985718ed7b867721a1680f13` |
| Tree | `d9469ac3fb715e8b6e689aa7fef9384f0662b3de` |
| Subject | `Complete Phase 59 package graph provenance` |
| Natural CI | `33053099675`, `push`, attempt `1`, successful exact head |
| Package version | `0.1.0` |
| Published test count | `10326` |

The repository was clean, had divergence `0/0`, and had no active Git
operation before profiling or mutation.

## Methodology And Environment

Measurements used the repository's existing serial pytest command under
CPython 3.13.13. No xdist worker was enabled. Timing used `/usr/bin/time` around
the repository-native command, while pytest supplied its own duration report.
Static source analysis and a temporary uncommitted pytest plugin counted
`Path.read_text`, `Path.read_bytes`, `glob`, `rglob`, and `ast.parse` only for
cost attribution. The plugin and its argument inventory are not repository
artifacts.

| Environment fact | Observation |
| --- | --- |
| Platform | CPython 3.13.13 on Linux/WSL2 x86_64 |
| CPU visibility | 20 logical CPUs; process affinity allowed 20 |
| pytest | 9.1.1 |
| Installed plugins | pytest-cov 7.1.0; pytest-xdist 3.8.0 |
| Tracked files | 699 |
| Tracked Python / Markdown | 498 / 103 |
| Python test files | 344 |
| Collected tests | 10326 |
| Cache posture | existing `.pytest_cache`, repository bytecode caches, and normal user uv cache |

An initial full diagnostic using a newly empty temporary uv cache is excluded
from the baseline. It completed 10312 tests but produced 14 setup errors when
two offline installed-wheel fixtures could not acquire cached build tooling.
The valid baseline restored the normal user uv cache and passed all tests. This
distinction is part of the reproducibility contract: offline wheel assurance
requires the normal locked build-cache posture and must not be silently timed
under an empty cache.

Hardware-dependent seconds below are observations, not test assertions or
portable semantic budgets. Later comparisons must use the same host, Python,
serial worker mode, cache posture, and commands.

## Collection And Full Pytest Baseline

Collection used:

```bash
UV_PYTHON=3.13 uv run pytest --collect-only -qq
```

The valid full baseline used:

```bash
UV_PYTHON=3.13 uv run pytest --durations=100 --durations-min=0.05
```

| Measurement | Observation |
| --- | ---: |
| Collection wall | 2.78s |
| Collection user / system | 2.19s / 0.58s |
| Collection maximum RSS | 127092 KiB |
| Full pytest wall | 217.61s |
| pytest-reported session | 215.94s |
| Full pytest user / system | 207.40s / 11.33s |
| Full pytest maximum RSS | 239580 KiB |
| Result | 10326 passed |

Separate warm runs imply approximately 1.3% collection/import wall and 98.7%
post-collection execution wall. Collection is not a dominant owner.

## Slow Tests And Dominant Cost

The leading durations were:

| Test family | Measured duration | Approximate full wall share |
| --- | ---: | ---: |
| Phase 58 Slice 16 differential fixture setup | 73.53s | 33.8% |
| Phase 59 Slice 11 differential fixture setup | 25.52s | 11.7% |
| Phase 57 Slice 12 cross-interpreter fixture setup | 9.25s | 4.3% |
| Phase 54 pure-boundary differential tests visible in the slow table | at least 16s | at least 7% |
| Two lifecycle-reader scanner tests | 5.72s | 2.6% |

A focused profile of the first three families passed in 104.18s and attributed
their parent-process child commands as follows:

| Child command family | Count | Cumulative child wall |
| --- | ---: | ---: |
| Phase 58 project-explain differential probe | 8 | 65.091s |
| Phase 59 graph differential probe | 10 | 27.335s |
| Interpreter/isolated `python -c` witnesses | 15 | 9.709s |
| `uv build --offline --wheel` | 2 | 0.326s |
| `uv pip install --offline` | 2 | 0.268s |

Repeated isolated probes, not wheel construction, dominate current pytest
runtime. The Phase 54/57/58/59 cross-process differential assurance family is
the first runtime-decomposition owner. Each seed, interpreter, relocation,
installed-wheel, failure, ordering, multiplicity, and byte-exact witness is
semantic assurance and must remain independently evidenced even if acquisition
is reused.

## Validator And Auxiliary Attribution

Natural CI `33053099675` supplies complementary clean-runner evidence. Its
Python 3.13 validator used the then-existing four-worker xdist CI command; it is
not a controlled comparison with the local serial run.

| Validator stage | CI observation | Share of 222.830s validator total |
| --- | ---: | ---: |
| Lockfile | 0.011s | below 0.1% |
| Ruff format | 0.166s | below 0.1% |
| Ruff lint | 0.114s | below 0.1% |
| Production Pyright | 14.745s | 6.6% |
| Test Pyright | 22.623s | 10.2% |
| pytest with four xdist workers | 185.170s | 83.1% |

The same job then spent approximately 0.84s on generated verification, 0.12s
on golden audit, and 20.12s on package smoke. Pytest is the dominant validator
stage; the combined Pyright stages are a separate material second owner.
Package smoke is material end-to-end assurance but is outside the validator
and remains mandatory and serial.

## Repository Reader Audit

Static analysis of current test source found:

| Operation | Call sites | Distinct owners |
| --- | ---: | ---: |
| `Path.read_text` | 400 | 323 |
| `Path.read_bytes` | 44 | 31 |
| `ast.parse` | 64 | 59 |
| `Path.rglob` | 43 | 37 |
| `Path.glob` | 39 | 35 |
| `Path.iterdir` | 5 | 5 |

The union contains 76 scanner owners. Excluding 23 owners whose only scan is a
temporary-output cleanup check leaves 53 owners scanning repository-controlled
examples, source, tests, docs, scripts, generated files, or fixtures.

A focused measured set of 31 broad historical scanner owners passed in 10.12s
and established this lower bound:

| Operation | Measured count |
| --- | ---: |
| `rglob` | 56 calls yielding 20733 paths |
| Explicit `glob` | 13 calls yielding 1494 paths |
| `Path.read_text` | 8544 reads of 665 unique paths |
| Repeated `Path.read_text` | 7879 reads across 639 repeatedly read paths |
| Python / Markdown `read_text` | 7550 / 714 |
| `ast.parse` | 1762 parses of 487 unique filenames |
| Repeated `ast.parse` | 1275 parses across 460 repeatedly parsed filenames |

The temporary plugin's raw `glob` counter also observed the internal `glob`
used to implement each `rglob`; the explicit `glob` values above subtract those
56 nested calls and their 20733 results.

The two lifecycle-reader tests alone scanned the 344 test files four times,
performed 1445 text reads of 358 unique paths, and performed 1373 AST parses of
343 unique Python filenames. Of those, 1087 reads and 1030 parses were repeats.
This is duplicated fact acquisition inside one policy owner. By contrast,
scanner owners that inspect distinct diagnostics, public-export absence,
generated inventory, lifecycle ownership, or packaging boundaries retain
legitimate independent assertions even when their acquisition may be shared.

Historical repository-wide readers materially contribute measurable cost, but
they do not dominate the suite. Their measured representative wall is about
4.7% of the full serial pytest wall, while cross-process differential assurance
alone is more than half of the visible slow-test cost.

## Repository Test Index Decision

`RepositoryTestIndex = PARTIALLY_SUPPORTED`.

The counts support immutable session-scoped reuse of tracked paths, source
text, and Python AST for compatible historical readers. They do not support
building a monolithic index containing every proposed import relationship and
Markdown structure before a caller proves those fields are needed. Slice 3
therefore owns the smallest shared acquisition that removes measured duplicate
reads/parses while preserving independent assertions, exact path order, source
bytes, and lifecycle-reader privacy. It may grow only when another measured
owner needs an additional immutable field.

## Xdist And Rust Boundaries

The installed xdist dependency and historical Maintenance Phase 3 contracts
are capability evidence, not current-suite safety authority. The current suite
now includes later module-scoped caches, subprocess probes, wheel builds,
temporary projects, cwd/environment isolation, dirty-tree readers, and global
fact acquisition that the historical audit did not cover.

Slice 1 restores natural CI to the serial authoritative command:

```bash
uv run python scripts/validate.py --timings
```

No authoritative local validator or natural CI in Slice 1 uses xdist. Before a
later benchmark, Slice 5 must inventory shared mutable state, cwd/environment
mutation, fixed/shared filesystem paths, global caches, module-scoped fixtures,
package-build isolation, dirty-tree readers, and ordering assumptions. It must
then prove collision-free deterministic parity on the current suite. Installed
tooling alone does not satisfy those prerequisites.

Rewriting Python tests in Rust is not owned. Python production and cross-
environment integration remain Python-owned; the first Rust-kernel decision
remains Phase 68 ownership.

## Frozen Interlude Route

| Slice | Independent owner | Evidence and terminal metric |
| ---: | --- | --- |
| 1 | Baseline Profiling, Cost Attribution, And Route Lock | Record the measurements and freeze the route; implement no optimization |
| 2 | Differential Probe Runtime Decomposition And Optimization | Decompose child-probe runtime first, preserve every assurance witness, and reduce the same three-fixture 104.18s profile by at least 25% without reducing the witness matrix |
| 3 | Repository Reader Acquisition Reuse | Preserve all assertions and reduce the 31-owner profile's `read_text` and `ast.parse` counts by at least 60%, with at least 30% lower same-method reader wall |
| 4 | Validator Static-Analysis Stage Optimization | Preserve both Pyright projects and diagnostics; reduce their combined same-environment wall by at least 20% or close the owner as not beneficial with measured evidence |
| 5 | Current-Suite Isolation Audit And Xdist Decision | Admit no benchmark before the isolation audit; retain parallel CI only if controlled parity is exact and median wall improves by at least 15% |
| 6 | Completion Benchmark And Phase 60 Readiness Assurance | Preserve all gates and achieve at least 20% lower serial pytest wall and 15% lower serial validator wall, or close unmet owners explicitly without claiming performance PASS |

The route is evidence-driven and ends before Phase 60 activation. A Slice may
close an investigated technique as not beneficial, but may not pad results by
removing tests, skips, xfails, assertions, diagnostics, generated/golden/
package assurance, or supported Python versions.

## Success Metrics And Compatibility Locks

Later measurements track collection wall, post-collection execution wall,
serial pytest wall, validator total and stage walls, repeated repository source
reads, repeated AST parses, repository-controlled scanner-owner count, test
count, and failure/coverage semantics. The Slice 1 pre-change count of 10326 is
a floor, not a target to reduce; new interlude tests increase it. A later PASS
cannot be caused by fewer collected tests.

Relative timing targets are evaluated only on the same environment and cache
posture. Repository tests lock structure and policy, not machine-specific
seconds. Python 3.12/3.13 natural CI, generated verification, golden audit,
package smoke, reader closure, fail-fast validator behavior, public outputs,
and exact diagnostics remain mandatory.

## Changed-Path And Lifecycle Lock

The exact Slice 1 changed-path allowlist is:

```text
.github/workflows/ci.yml
docs/roadmap.md
docs/spec/validation-performance-interlude-slice1-baseline-profiling-cost-attribution-route-lock-v1.md
docs/status.md
tests/test_active_phase_lifecycle.py
tests/test_phase11_ci_workflow.py
tests/test_validation_performance_interlude_slice1_baseline_profiling_cost_attribution_route_lock.py
tests/test_phase59_slice12_completion_audit_phase60_handoff.py
tests/test_workflow_lifecycle_validation_efficiency.py
```

Production, generated, golden, package, version, dependency, and validator
script deltas are zero. `tests/test_active_phase_lifecycle.py` remains the sole
mutable lifecycle reader; this Slice's static test does not read mutable
lifecycle documents.

Successful natural exact-head CI on the single Slice 1 commit establishes
Slice 1 completion without a status-only follow-up commit and leaves:

```text
Phase 59 = COMPLETED
Validation/Test Performance Optimization Interlude = ACTIVE
Phase 60 = NOT ACTIVATED

NEXT:
VALIDATION_PERFORMANCE_INTERLUDE_SLICE2_DIFFERENTIAL_PROBE_RUNTIME_DECOMPOSITION_AND_OPTIMIZATION
```
