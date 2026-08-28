# Validation Performance Interlude Slice 3 Repository Reader Acquisition Reuse v1

## Answer And Scope

Slice 3 separates repository fact acquisition from historical policy
assertions and shares only the former across nine measured high-reuse scanner
owners. It adds one test-only session-local cache of immutable Python-source
facts and changes no production, public, validator, CI, xdist, generated,
golden, package, Rust, or Phase 60 behavior.

## Starting Authority

| Fact | Value |
| --- | --- |
| Published Slice 2 commit | `b6191d790040233a5ad62de7549c36bc0a555d9c` |
| Published Slice 2 tree | `874511592c4eee2b6ef024146b0017c335cd4ab4` |
| Natural CI | `33121173872`, `push`, attempt `1`, successful exact head |
| Published test count | `10335` |
| Package version | `0.1.0` |

Phase 59 is completed, the Validation/Test Performance Optimization Interlude
is active, Slices 1–2 are published complete, Slice 3 is the current
publication candidate, and Phase 60 remains blocked and not activated.

## Reader Decomposition

Slice 1 measured 31 broad historical scanner owners. Slice 3 refreshed the
live denominator and selected nine high-reuse owner tests rather than
mechanically migrating all 31:

- two workflow lifecycle-reader ownership tests repeatedly reconstruct the
  same test-file literals and imports;
- seven Phase 52 privacy/import/source-boundary owners repeatedly enumerate
  `src/pietto/**/*.py` and read identical source text;
- two of those Phase 52 owners also independently parse the same source corpus
  to derive identifier facts.

The remaining 22 scanner owners retain direct acquisition because their
measured reuse is lower, their surfaces differ, or migration would serve
architectural uniformity rather than current performance.

The fixed nine-test benchmark passed with deterministic operation counts:

| Before measurement | Run 1 | Run 2 |
| --- | ---: | ---: |
| Wall | 6.78s | 5.98s |
| Repository text reads | 2412 | 2412 |
| Distinct text files | 482 | 482 |
| Duplicate text reads | 1930 | 1930 |
| Repository AST parses | 1661 | 1661 |
| Distinct parsed files | 460 | 460 |
| Duplicate AST parses | 1201 | 1201 |
| `rglob` calls/results | 9 / 1051 | 9 / 1051 |
| Explicit `glob` calls/results | 8 / 1436 | 8 / 1436 |

The highest-value duplicated acquisition is exact Python text plus derived
literal/import/identifier facts, not any shared policy decision.

## Shared Acquisition Surface

`tests/_pietto_repository_facts.py` provides one explicit-root
`RepositoryFactIndex.snapshot(root)` cache with:

- owner-supplied Python paths validated against that root;
- exact `read_text(encoding="utf-8")` text;
- immutable string-literal and direct-import sets;
- immutable name/attribute/import-alias identifier sets;
- immutable top-level assignment target names for the existing owner whose
  historical universe includes both `ast.Assign` and `ast.AnnAssign`.

The helper does not enumerate, filter, glob, or apply Git-ignore policy to
paths. Each explicitly requested Python source is read and parsed at most once
per cache scope. The mutable AST is discarded; consumers receive only frozen
derived facts. No Markdown fact, heading index, arbitrary AST, result cache,
or general repository database is implemented.

## Policy And Freshness Boundary

Policy assertions remain in the nine existing owners. They still decide:

- the sole mutable lifecycle reader;
- product-test membership and historical phase boundaries;
- non-recursive `glob`, recursive `rglob`, and explicit path inventories;
- the exact AST node classes inspected, including `ast.Assign` without
  `ast.AnnAssign` where that was the historical rule;
- allowed and forbidden source consumers/imports/identifiers;
- exact exclusions, expected symbols, and public/private policy.

The shared helper contains none of those decisions.

The migrated owners were audited as read-only over repository Python files for
the whole pytest session. Their first explicit request captures a frozen fact,
and later requests reuse it. A copied, relocated, or intentionally rewritten
corpus obtains a fresh explicit snapshot/cache scope after materialization; no
timestamp heuristic or silent invalidation is used. Access order changes no
observations, ignored paths selected by an owner remain eligible, and no
PASS/failure state is stored.

## Performance Proof

The invalid first implementation scanned ignored `.venv` files, producing
1111 reads/parses and an 8.53s wall regression. It was rejected before review
and is not part of the after evidence. Candidate-owned Git inventory corrected
that acquisition root.

The first reviewed candidate measured 502 reads, 502 parses, and a 4.75s
two-run median, but its shared derived facts widened one `ast.Assign` policy to
`ast.Assign` plus `ast.AnnAssign`, and recursive discovery replaced an owner's
non-recursive glob. The continuation rejected those numbers as final authority,
restored the exact owner-local selectors, and remeasured the repaired candidate.

| Comparable measurement | Before | Repaired after |
| --- | ---: | ---: |
| Run 1 wall | 6.78s | 6.31s |
| Run 2 wall | 5.98s | 5.89s |
| Run 3 wall | not required | 8.85s |
| Median | 6.38s | 6.31s |
| Run range | 0.80s | 2.96s |
| Text reads | 2412 | 483 |
| Distinct text files | 482 | 483 |
| Duplicate text reads | 1930 | 0 |
| AST parses | 1661 | 484 |
| Distinct parsed files | 460 | 483 |
| Duplicate AST parses | 1201 | 1 |
| Repository glob/rglob calls | 17 | 17 |
| Scanner-owner tests/assertions | 9 | 9 |

Text reads decrease by 80.0%, AST parses decrease by 70.9%, duplicate text
acquisition falls to zero, and duplicate AST acquisition falls from 1201 to
one exact owner-local reparse. A third repaired run was required because the
first two ranges overlap the baseline and wall-time conclusions were noisy.
The repaired median is 0.07s, or 1.1%, below the two-run baseline median, far
smaller than either observed run range. No wall-time improvement is claimed,
and there is no material wall-time regression; the material gain is the
deterministic operation-count reduction with exact policy semantics.

## Assurance Locks

Focused assurance must prove:

- shared text/literal/import/identifier facts equal independent legacy reads
  and parses over the migrated corpus;
- returned facts are frozen and contain no policy or test-result state;
- mutation requires a fresh explicit snapshot;
- relocated snapshots preserve content-derived facts;
- access order does not affect observations;
- mixed `Assign`/`AnnAssign` input remains `Assign`-only for the historical
  owner, preserving assignment targets, calls, and source order;
- non-recursive, recursive, and explicit owner path sequences remain exact,
  including nested-test exclusion for the non-recursive owner;
- ignored Python paths explicitly selected by an owner are not filtered by the
  shared acquisition layer;
- nine migrated owner tests and their assertions remain intact;
- lifecycle ownership remains centralized;
- Slice 2 differential batching, source/wheel behavior, and production/public
  semantics remain unchanged.

Machine-specific seconds above are observational evidence, not repository
pass/fail budgets. Operation counts and owner-local policy invariants are the
structural regression surface.

## Changed-Path And Lifecycle Lock

The exact Slice 3 changed-path allowlist is:

```text
docs/roadmap.md
docs/spec/validation-performance-interlude-slice3-repository-reader-acquisition-reuse-v1.md
docs/status.md
tests/_pietto_repository_facts.py
tests/test_active_phase_lifecycle.py
tests/test_phase52_aggregate_signature_algebra_facts.py
tests/test_phase52_expression_stage_clause_capability_facts.py
tests/test_phase52_fail_closed_capability_lookup.py
tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py
tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py
tests/test_phase52_private_capability_fact_foundation.py
tests/test_phase52_scalar_function_operator_signature_facts.py
tests/test_validation_performance_interlude_slice3_repository_reader_acquisition_reuse.py
tests/test_workflow_lifecycle_validation_efficiency.py
```

`tests/test_active_phase_lifecycle.py` remains the sole mutable lifecycle
document reader. Historical completion tests remain immutable-contract readers
and do not consume lifecycle state through the shared snapshot.

Successful natural exact-head CI on the single Slice 3 commit establishes
Slice 3 completion without a status-only follow-up commit and leaves:

```text
Phase 59 = COMPLETED
Validation/Test Performance Optimization Interlude = ACTIVE
Phase 60 = NOT ACTIVATED

NEXT:
VALIDATION_PERFORMANCE_INTERLUDE_SLICE4_VALIDATOR_STATIC_ANALYSIS_STAGE_OPTIMIZATION
```
