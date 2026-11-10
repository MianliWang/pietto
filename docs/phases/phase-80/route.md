# Phase80 route — Gate 1 approved, Gate 0 bound (health and overlap pending)

Phase80 owns the Phase 80 row of the
[roadmap](../../roadmap.md#future-roadmap-v6): pandas, Polars, NumPy, SciPy
and Matplotlib interoperability and the Python user surface. On 2026-11-10
(America/Toronto) the owner approved its Gate 1 with the recommended answers
of the lead's decision sheet; D80.01–D80.07 and AD80.01, with the rows
PL.01–PL.06 shared with Phase78, Phase79 and the editor core, in the
[decision record](../../decisions.md) record them. Phase80 runs beside Phase77
on its own ledger (PL.01, D80.07). No Phase80 code reaches `main` before the
`0.1.11` cut (PL.04), and this route authorizes no commit, push, tag,
release or package upload.

Gate 0 binds the head and its natural CI; the read of that CI's eligible health and alerts and the re-measured Phase77 overlap are pending until the package's first implementation batch records them.

Before Gate 0, these runs happened besides paper records (PL.02). The PyPI
metadata and hash fetch and isolated install probe of PL.05 (a), which sheet
Q3 A authorizes, read PyPI JSON at 2026-11-10T11:32:46Z; the lead's record of
the owner's approval of Q3 A that day carries the earlier `modified` time
11:32:37Z. Earlier, during the read-only Gate 1 drafting and before that
approval, the SQLite draft ran an in-memory `sqlite3` probe that its critique
repeated, and the Phase80 draft took a PyPI reading. No authorization is
recorded for these two: they were unauthorized preparation, and their results
are not evidence. Phase78 Q0 measures the SQLite build and its listed cells in
the Gate 0 environment, and the PL.05 probe replaces the PyPI reading. Every
implementation slice starts from the published head that Gate 0 binds (PL.02).

## Gate 0 and live authority

This route was drafted on `569c365d` (tree
`5561238f181887274dbadbdd5fa848998cfa1872`), an unpublished candidate of the
maintenance/editor batch, which was published under D77.04 instead as
`befa5de8`, `6a1eb9c9` and `ab972f36`. Gate 0 of every Phase80 lane is bound
to that published head (PL.02): `main` at
`ab972f362c433b234a74f542c5d274d22c8cdeae` (tree
`821be1ccf7bb6f3e14b8d00d80f1f30d3cc087fe`), whose natural exact-head CI
`42831340276`, push/main attempt 1, passed all 21 jobs. It rebinds there:

- branch, tree, remote state, natural CI and its eligible
  [CI health](../../architecture/ci-workload-governance-v1.md) samples and
  alerts;
- the PyArrow identity: `PYARROW` in
  `src/pietto/_project/project_arrow_result.py`, the four extras, `uv.lock`
  and `ci/phase67-arrow-compatibility-requirements.txt` (`26.0.1` on `main`
  since `befa5de8` under M77.01);
- the `ResultBatch` boundary of `src/pietto/execution/_handle.py`: no public
  constructor, export through `pyarrow.record_batch(batch)`, `HandleMisuse`
  PIE-R4002 once closed, and the private `_batch` factory of real producers;
- the Arrow result types of `project_arrow_result.py`: Int as int16/32/64,
  Text as `string` (or requested `large_string`), Decimal as decimal128/256,
  Date as date32, Timestamp as zone-less timestamp[us], UUID as the
  `arrow.uuid` extension or binary16, Bool, Float as float64 after the finite
  check, nested as `list<struct>`;
- CI: the arrow-ready environment that `scripts/package_smoke.py --extra-env`
  builds in `.github/workflows/ci.yml`, and the core-only profile and
  six-shard ceiling of `scripts/ci_workloads.py`;
- which Phase77 batches are published, above all S21–S24 and S26.

The initiation gate's item "consume the previous completion audit" is
`NOT_APPLICABLE`: Phase77 has no completion audit while Phase80 runs beside it
(PL.01). Gate 1 consumes instead the
[Phase76 completion audit](../phase-76/completion-audit.md), the facts of
Phase77's published batches and the
[engineering lessons](../../references/engineering-lessons.md) cited below
(Phase68 4, Phase68 S19, Phase69 2, Phase72 2, Phase75 1, 3 and 4, Phase76
reminder 10). Phase77 S27 owns the
missing audit; the first Phase80 replay after its publication consumes its
handoff, and S06 at the latest.

## Outcome and scope

A Python user who holds an open `ResultBatch` from any existing route, saved
read or verified export gets, in one call, a pandas or Polars DataFrame, a
NumPy array, a SciPy CSR array or a Matplotlib artist on their own Axes, with
field order, row order, multiplicity, null positions and exact types kept as
D80.03 states. The batch stays open and the result outlives it.

The Python user surface of this phase (D80.02) is the existing alpha
`pietto.compiler` and `pietto.execution` entry points, unchanged, plus the new
`pietto.interop` package, its five extras and one guide page
`docs/interop.md` that walks from a project to each library.

Not included: compiling, executing, iterating, saving or reopening a query;
whole-result accumulation; zero-copy, allocator, mutability or thread-safety
promises; a combined extra; Windows, macOS or CPython 3.14 claims (Phase81);
any Pietto syntax, CLI or diagnostic code; and the deferred candidates of
D80.06 (`compile_queries(...)`, native array and JSON columns, the
`postgres_adbc` nested route, `round` of a `Float` with digits, pandas and
Polars nesting, the Arrow data-analysis example). Phase80 changes no grammar
or built-in catalog, so no extension sync (D76.12) and no extension-repository
push follow from it.

## Adapter contract

```python
from pietto.interop import (
    plot_line, plot_scatter, to_numpy, to_pandas, to_polars, to_scipy_csr,
)

def to_pandas(batch: ResultBatch) -> "pandas.DataFrame": ...
def to_polars(batch: ResultBatch) -> "polars.DataFrame": ...
def to_numpy(batch: ResultBatch, column: int) -> "numpy.ndarray": ...
def to_scipy_csr(
    batch: ResultBatch, row: int, column: int, value: int,
    shape: tuple[int, int],
) -> "scipy.sparse.csr_array": ...
def plot_line(
    batch: ResultBatch, x: int, y: int, *, ax: "matplotlib.axes.Axes",
) -> "matplotlib.lines.Line2D": ...
def plot_scatter(
    batch: ResultBatch, x: int, y: int, *, ax: "matplotlib.axes.Axes",
) -> "matplotlib.collections.PathCollection": ...
```

Arguments are positional field ordinals (an `int`, never a `bool`, within
`0 <= ordinal < field count`); a label is never looked up. No function takes
`**kwargs`. Each adapter reads the batch once through
`pyarrow.record_batch(batch)`.

| Arrow field | pandas | Polars | NumPy | SciPy | Matplotlib |
| --- | --- | --- | --- | --- | --- |
| int16/32/64 | `ArrowDtype` of the type | Int16/32/64 | same width, non-nullable | row, column or value, non-nullable | float64, non-nullable, every value within ±2**53 |
| bool | `ArrowDtype(bool)` | Boolean | `bool_`, non-nullable | refused | refused |
| float64 | `ArrowDtype(double)` | Float64 | float64, non-nullable | refused | float64, non-nullable |
| string, large_string | `ArrowDtype` of the type | String | refused | refused | refused |
| decimal128 (p ≤ 38) | `ArrowDtype` of the type | Decimal(p, s) | refused | refused | refused |
| date32 | `ArrowDtype(date32)` | Date | refused | refused | refused |
| timestamp[us], no zone | `ArrowDtype` of the type | Datetime("us") | refused | refused | refused |
| decimal256, UUID, nested | refused | refused | refused | refused | refused |

- pandas and Polars admit nullable fields and keep null positions; pandas uses
  a RangeIndex, never the pandas default string dtype. Any Polars output dtype
  other than its mapping cell is a refusal, never a cast.
- NumPy, SciPy and Matplotlib judge "non-nullable" by the schema field, not by
  the values of one batch, so two batches of one query cannot differ (users
  `coalesce` in Pietto first). NumPy returns an owned writable copy (D67.27)
  of shape `(n,)`, or `(0,)` with the dtype for a typed empty batch, and
  keeps the sign of zero.
- SciPy takes three distinct Int fields and a `shape` of two non-negative
  `int` values, each at most 4096: CSR allocates `shape[0] + 1` index
  pointers whatever the stored entries, so the caller-supplied shape needs its
  own bound, kept at the per-batch row ceiling of D67.10. It returns a
  canonical `csr_array` (sorted indices, int32 index dtype, data dtype of the
  value field) that stores every record, explicit zeros included; duplicate,
  negative or out-of-shape coordinates are refused, and the result does not
  depend on record order.
- Matplotlib draws only on the caller's Axes, never imports `pyplot`, selects
  no backend, never shows or saves, and checks every value before it creates
  the artist. The artist's data (`get_xydata()`, `get_offsets()`) equals the
  source values bit for bit in input order; no rendering precision is
  promised.
- Float finiteness is the result contract's guarantee upstream, not an
  adapter refusal. A typed empty batch returns the target's typed empty
  object.

## Errors and lifecycle

Errors are standard Python exceptions (D80.04), checked in one fixed order,
an implementation choice that tests and `docs/interop.md` share: `TypeError`
for a wrong argument type; then the existing `HandleMisuse` PIE-R4002 for a
closed batch; then `ValueError` for ordinal, admission, shape, coordinate or
envelope failures, schema checks before value checks; then
`ModuleNotFoundError` for a missing extra; then the target conversion, whose
failures are not wrapped. No PIE family is added. A refused call leaves the
batch open and the Axes without a new artist.

A call converts one batch. The caller owns the batch, the Axes and the
returned object; the adapter never closes the batch, and the returned object
stays usable after `batch.close()` because the imported Arrow batch keeps its
buffers. Space is one batch (at most 4,096 rows and 8 MiB, D67.10, D76.08)
plus the target object. There is no Pietto cache, thread, executor, file,
network, credential or database authority, and no cancellation, since no
Pietto operation is asynchronous. Target libraries keep their own effects:
PyArrow and Polars thread pools and Matplotlib's configuration directory and
font cache. `docs/interop.md` states them as `docs/execution.md` states
PyArrow's import effects.

## Dependencies and pins

The one PyPI metadata/hash fetch and isolated install probe of PL.05 (P0b's
package part) ran outside every repository at 2026-11-10T11:32:46Z,
hash-verified, in the D71.09 manner; the same fetch serves the Phase79 DuckDB
evidence. The probe facts this route relies on, the versions, wheel tags and
PyArrow wheel sha256 values, are stated inline in the table below. The raw
probe outputs are owner-held working records outside Git. The probe also keeps
its uv cache and CPython 3.13.13 venv until PK seals, when PL.05 removes them;
until then they serve the offline cells below and the lane environments. Lanes
install on CPython 3.13 offline from that cache with `--require-hashes`, and
PK resolves offline from it for the `uv.lock` regeneration and package smoke
on each integration tree; any new networked package or metadata fetch needs a
separate owner approval. The cache holds no CPython 3.12 wheels of pandas,
numpy, SciPy, Matplotlib or PyArrow, nor of Matplotlib's dependencies
`contourpy`, `fonttools`, `kiwisolver` and `pillow`, so the CPython 3.12
cells come from natural CI, and from PK's package smoke once the owner
approves fetching those wheels. The Phase80 draft's 2026-11-10 PyPI reading
was taken without network authorization and is not evidence; the probe
replaces it.

| Distribution | Role | Pin | Status |
| --- | --- | --- | --- |
| pyarrow | existing `arrow` extra, `PYARROW` identity | `26.0.1` on `main` since `befa5de8` | bound at Gate 0 on `ab972f36` (M77.01, D77.04); the probe's wheels `pyarrow-26.0.1-cp312-cp312-manylinux_2_28_x86_64.whl` (sha256 `c718bf97a92a6dea97fd1062c3b9f9e2e83cb9cc926e752289fa4ffff41738f9`) and `pyarrow-26.0.1-cp313-cp313-manylinux_2_28_x86_64.whl` (sha256 `f71221bbc7707e3fad920d0478db9350791d4714ec445299ee0d56559fbc156c`) carry the hashes in `ci/phase67-arrow-compatibility-requirements.txt`; only a manylinux_2_28 wheel exists, so PyArrow sets the glibc 2.28 floor |
| pandas | `interop-pandas` | `pandas==3.1.1` | observed: latest stable, first uploaded 2026-11-04, `requires_python >=3.11`; cp312 and cp313 manylinux_2_24/2_28 wheels |
| polars, and its runtime distribution | `interop-polars` | `polars==2.1.0` | observed: `polars` pins `polars-runtime-32==2.1.0` exactly itself, so the extra pins `polars` only; pure-Python `polars` wheel and one `cp311-abi3` manylinux_2_17 runtime wheel |
| numpy | `interop-numpy`; transitive for pandas, SciPy and Matplotlib | `numpy==2.5.4` in `interop-numpy` only, no co-pin | observed: `requires_python >=3.12`; cp312 and cp313 manylinux_2_27/2_28 wheels |
| scipy | `interop-scipy` | `scipy==1.18.1` | observed: cp312 and cp313 manylinux_2_27/2_28 wheels |
| matplotlib | `interop-matplotlib` | `matplotlib==3.11.2` | observed: cp312 and cp313 manylinux_2_17 wheels |
| every closure wheel | hash allowlist | SHA-256 per file | observed: 17 pins, identical for cp312 and cp313 (the two hashed requirement files differ only in the header), 683 hashes covering every file of each pinned version; transitive pins contourpy 1.4.0, cycler 0.12.1, fonttools 4.68.0, kiwisolver 1.5.1, packaging 26.3, pillow 13.0.0, pyparsing 3.3.3, python-dateutil 4.0.0, tzdata 2026.6; installed with `--require-hashes --no-deps` and checked with `uv pip check` on CPython 3.13.13 only |

Each extra pins only its target library (D80.05); `uv.lock` locks the
closures, and the installation tests own them. The observed closure keeps
the `PYARROW` identity and has a wheel for every supported cell. A pin change
that requires a PyArrow other than the `PYARROW` identity, or misses a wheel
for a supported cell, stops for the owner. Qualified cells are
`pietto[arrow,interop-X]` for each X on CPython 3.12 and 3.13, Linux x86-64,
glibc ≥ 2.28. A route extra beside an interop extra is claimed only under the
stated assumption that it carries the same PyArrow identity; it gets no cell
of its own. No target version is checked at run time; `docs/interop.md` says
that only the pins are qualified.

## Qualification

Real witnesses run in installed environments, because the core test environment
has no PyArrow. The script consumer `tests/_pietto_results_interop.py` runs
with `-I` in each `pietto[arrow,interop-X]` environment, writes a report, and
fails when its target is missing there (Phase75 lesson 3). The core-only owner
`tests/test_results_interop.py` holds the import, signature and argument
checks, the core-only negative and the report checker, which refuses every
fabricated fail-open report (a missing cell or case, a skipped target, a wrong
version, an empty case list). The existing arrow-ready environment is the
missing-extra negative of all five adapters.

Every adapter has a core-only import negative, an installed-wheel witness of
its extra, a missing-extra negative, a closed-batch negative, a control that
it executes nothing and touches no handle, typed empty, nullable and refusal
cases, order and multiplicity, and post-close use. pandas and Polars add
logical type, value and null oracles and the exact dtype matrix; NumPy adds
signed-zero bits, the owned copy and the nullable-schema refusal; SciPy adds
coordinate permutations, duplicates, stored zeros and canonical form;
Matplotlib adds caller-Axes identity, bit equality and no `pyplot` import.
Oracles come from the producer's input values, never from the target's output.
Batches come from real producers through `_batch`, never a duck-typed
stand-in (D67.31 precedent), and from real queries rather than every
permutation (Phase76 reminder 10). No database campaign follows: a batch
already exists. A lane runs the CI-shaped consumer locally before delivery
(Phase68 S19 lesson). The five extras on two CPython versions form ten
installed cells.

## Slices

| Slice | Delivers | Depends on | Draft C/F/D/S |
| --- | --- | --- | --- |
| P0b | Probe. Done on 2026-11-10 (PL.05): exact versions, hashes and closures; on CPython 3.13.13, the int64, bool, float64, string, decimal128(10,2), date32 and timestamp[us] matrices with nulls, NaN, ±0 and both typed-empty shapes for pandas, Polars, NumPy and dense SciPy input, and Matplotlib's import effects. Remaining after Gate 0, offline in the probe's venv: int16 and int32, large_string, decimal128 at p = 38, the refusals of decimal256, UUID and nested fields, the pyplot-free `Figure()` path, and `csr_array` built from coordinate triplets with explicit zeros kept and int32 indices. Evidence only; the integrator copies the results into this route | Fetch and install: done before Gate 0 under PL.05 (a) (sheet Q3 A, owner 2026-11-10); remaining cells: Gate 0, before PK seals | 5/15/300/1 |
| S01 | `pietto.interop` seam: lazy package, argument and closed-batch checks, error order, report checker, guide skeleton | Gate 0, D80.02, D80.04, AD80.01; the lead states the D80.02 Python-user-surface wording to the owner (inform) before S01 seals | 10/30/300/1 |
| S02 | pandas and Polars | S01; P0b before its qualification | 35/105/1000/2 |
| S03 | NumPy | S01; P0b before its qualification | 15/45/400/1 |
| S04 | SciPy | S01; P0b before its qualification | 20/60/500/2 |
| S05 | Matplotlib | S01; P0b before its qualification | 20/60/500/2 |
| PK-80 | Phase80 share of the shared packaging lane PK: five extras, lock, hash allowlist, ten installed CI cells | P0b, S01; the PK schedule of PL.05 (after Phase77's next published batch, integrating after Phase77 S26) | PK ledger |
| S06 | Shared pages, acquisition consolidation, completion audit with handoff, lessons | S01–S05, PK-80, IB1 natural CI | 15/45/400/1 |

| Slice | Write set | Checks and acceptance |
| --- | --- | --- |
| P0b | none in the repository; the probe's uv cache and CPython 3.13.13 venv (outside Git, removed after PK seals, PL.05) and the lane's own evidence folder | each D80.03 cell observed at the pin or reported failed; a failed row stops for the owner |
| S01 | new `src/pietto/interop/__init__.py`, one private common module, `tests/test_results_interop.py`, `tests/_pietto_results_interop.py`, `docs/interop.md`; fragment `80-s01-interop-package.md` | Ruff and static gates; a fresh `-I` import of `pietto.interop` loads no `pyarrow`, target or `pietto.execution`; names and signatures; each `TypeError` before any target import; report-checker refusals; in an arrow-ready environment PIE-R4002 for a closed real batch and `ModuleNotFoundError` with the batch open; `tests/test_repo_*` on the lane tree |
| S02 | new `src/pietto/interop/_pandas.py` and `_polars.py`; their consumer cases, core-only cases and guide sections; fragment `80-s02-pandas-polars.md` | every D80.03 pandas and Polars row in both installed environments, on CPython 3.13 in the lane and on 3.12 and 3.13 through PK's package smoke and natural CI: dtypes, null positions, typed empty, order, duplicates, post-close use, refusals |
| S03 | new `src/pietto/interop/_numpy.py`; cases, guide section; fragment `80-s03-numpy.md` | dtype per type, `(n,)` and `(0,)`, `signbit` of ±0, a writable copy that shares no buffer with the batch, nullable-schema refusal without nulls, ordinal refusals |
| S04 | new `src/pietto/interop/_scipy.py`; cases, guide section; fragment `80-s04-scipy.md` | canonical output equal under record permutations, stored zeros, int32 indices, data width, duplicate/negative/out-of-shape and shape-bound refusals |
| S05 | new `src/pietto/interop/_matplotlib.py`; cases, guide section; fragment `80-s05-matplotlib.md` | with `MPLCONFIGDIR` in the lane's scratch and an Axes from `matplotlib.figure.Figure()`: artist type and Axes, bit-equal data in order, `pyplot` absent from `sys.modules`, no artist after a refusal, the ±2**53 bound and one beyond |
| PK-80 | `pyproject.toml`, `uv.lock` (regenerated on the integration tree only), `tests/test_release_installation.py`, `tests/test_results_optional_arrow.py`, `scripts/package_smoke.py` (wheel file list, interop environments), one hash allowlist under `ci/`, `.github/workflows/ci.yml`, and every other literal reader the inventory finds; fragment `80-p01-interop-extras.md` | literal-pin reader inventory first (Phase68 lesson 4, Phase69 lesson 2); installation tests; package smoke with all five interop environments in the CI shape; depth-one validation of the CI change |
| S06 | `docs/roadmap.md` (deferred row, freeze-ledger rows), `docs/status.md`, `docs/capabilities.md` (pointer), `README.md` (install line), `docs/execution.md` (pointer), `AGENTS.md` (alpha list) only if the owner decides it, as for D76.18 (pending: no D80 row authorizes it), new `docs/phases/phase-80/completion-audit.md`, `docs/references/engineering-lessons.md` | docs owners and `scripts/release_notes.py check`; the [acquisition consolidation](../../development.md#phase-end-acquisition-consolidation) of new and changed tests against the Phase80 baseline; the ten-slowest profile of IB1's natural CI health; three-layer acceptance in the audit |

S02–S05 develop in parallel after S01 and integrate in that order, since they
share the S01 consumer and guide page. `ci.yml` and `scripts/ci_validation.py`
are VR2 acceptance rule paths: the batch that carries PK-80 runs its Gate 2
wholly on the integration host, and under the owner's 2026-10-27 decision its
natural CI is not recorded as a new bootstrap, so the Teach split stays void
(PL.05, [validation runner
acceptance](../../development.md#validation-runner-acceptance)). PK also
carries Phase79's `execute-duckdb` extra; it regenerates `uv.lock` once per
integration and orders the two shares itself.

## Lanes and integration

- Every lane starts from the latest integration head, names its base in its
  brief and rebases before delivery (Phase75 lesson 1, Lean Gate v3). The
  repository-wide owners run on the merged tree at each replay (Phase72
  lesson 2), and the real-producer cases rerun too, because Phase77 S21–S23
  change producers and readers.
- Lanes write only under their own names (Phase75 lesson 4) and follow the
  lane rules of PL.01 and the pytest worker rule of PL.03; Gate 2 shares the
  integration host under PL.01, with the authoritative worker cap of PL.03.
- New files first, shared hunks last; replays only at Phase77
  published-batch boundaries; shared pages serialized at integration
  (PL.04); `uv.lock` regenerated, never text-merged (PL.05).
- Under PL.04, Phase80 code, tests, extras, lock changes and fragments stay
  off `main` until the `0.1.11` cut, since the release assembly takes every
  fragment present.
- Batches after the cut: IB1 is S01, PK-80, S02, S03, S04 and S05, one commit
  each, one authoritative Python 3.13 Gate 2 on its final tree, one
  fast-forward push under its own authorization, natural exact-head CI; IB2 is
  S06 after IB1's CI. A failed head is kept and repaired by a child, never
  rerun. Phase80 ships in `0.2.0` once its gate is met (D76.14).

Route and decision records (documentation only, with no code and no
release-note fragment) may reach `main` before the `0.1.11` cut, in a Phase77
batch under D77.06 or in a documentation and tool batch under D77.14;
Phase78–80 code and fragments may not. By the lead's ruling (PL.04, lead,
inform), this route reaches `main` in a Phase77 batch under D77.06, because
the batch also carries a Phase77 repair, counted on Phase77's ledger, that
returns PIE-B1003 refusals of project `/` and `%` instead of crashing. D77.14,
a rule for a whole documentation and tool batch, does not cover it.

## Budget

The cumulative Phase80 ceiling is `C120/F360/D4200/S10`, of which D800 is the
replay reserve (D80.07); the per-slice drafts above sum to D3400 and are
planning, not allowances. PK keeps its own `C40/F120/D1200/S4`, reported half
to Phase79 and half to Phase80 (PL.05). D counts one per diagnostic command,
and the probe and design lines count (D76.17). The planning entry charged here
is the Phase80 draft's 34 and this route's drafting 26 shell commands
(read-only except the one that made this file's directory), plus any later fix
of this route and Phase80's share of the shared passes after the approval.
The 19 commands of the shared PyPI/install probe open the PK ledger, and
PL.06 records the shared sheet, critique, review, consolidation and fix-pass
commands once and keeps those before the approval on Phase77. From the
approval on Phase80 spends nothing of Phase77's ledger and resets nothing
there, and no lane or handoff resets this one. At any cap the lead stops and
asks.

## Risks

1. Long life off `main`: replays across Phase77 S21–S27 move the Arrow types
   and producers the cases read. The replay reserve, published-boundary
   replays and the sheet Q2 option-C check at the Phase77 midpoint (PL.04)
   bound it.
2. The packaging hot spot that Phase77 S26 and Phase79 share, with CI-only
   literal readers and the VR2 acceptance rule paths. One PK lane, a reader
   inventory, lock regeneration and a host-only Gate 2 for that batch bound
   it.
3. Target behavior at the pin is only partly observed, and only on CPython
   3.13.13. The probe confirmed the closures against PyArrow `26.0.1`, the
   Polars decimal and temporal mappings of the probed types, pandas 3's lossy
   defaults (which is why D80.03 requires `ArrowDtype`) and Matplotlib's
   import effects. The remaining P0b cells and the CPython 3.12 installs are
   unproven. P0b precedes every qualification claim, and a failed row stops
   for the owner; no fallback conversion is written.

## Midpoint, unfreeze and closure

**Midpoint (local, before IB1 seals).** P0b's remaining cells, S01 and S02
are integration-ready; the pin table carries every result; each D80.03 row is
proven or stopped; the measured rate projects within the ceiling; the latest
`main` natural CI health and alerts are read; the acquisition reserve has
reviewed the new consumer and fixtures; and the Phase77 S21–S24 state is
reported for the PL.04 option-C check.

**Unfreeze conditions.** The owner decides any change of a D80.03 row or a
signature, a new function, extra or combined extra, a platform, a pin change
after qualification, a package or metadata fetch other than the completed
probe fetch of PL.05 (PK resolves offline from the probe's uv cache), a
deferred candidate, a
new PIE code or public text beyond the listed pages, and any
extension-repository change.

**Closure.** Phase80 closes when the five adapters pass all ten installed
cells, IB1 and IB2 are on `main` with green natural exact-head CI, and the
completion audit records the freeze-ledger inputs (`pietto.interop`, the
extras and each deferred candidate's latest point), the Gate 2 duration and
the handoff. `0.2.0` also needs Phase79 and its own release approval.

## External references

Each record follows the gate's eleven items. The snapshot of each library is
the 2026-11-10 probe (PL.05): PyPI JSON at 2026-11-10T11:32:46Z and the
installed wheels at the selected pin, exercised on CPython 3.13.13 only.
Upstream documentation pages were not re-read; the 2026-11-09 proposal's
reading of the pandas PyArrow guide and the Polars `from_arrow` page is an
input, not the snapshot. Claims still marked "to verify" are remaining P0b
cells.

| Item | pandas | Polars | NumPy | SciPy sparse | Matplotlib |
| --- | --- | --- | --- | --- | --- |
| 1 Snapshot/date | `3.1.1`, probe of 2026-11-10 | `2.1.0` with `polars-runtime-32` `2.1.0`, probe of 2026-11-10 | `2.5.4`, probe of 2026-11-10 | `1.18.1`, probe of 2026-11-10 | `3.11.2`, probe of 2026-11-10 (`MPLBACKEND=Agg`, empty isolated `HOME`) |
| 2 Problem/constraints | one batch to a DataFrame without losing nulls or exact types | the same without a silent cast | one column to an owned array with its exact dtype | records to a matrix without dropping zeros or summing duplicates | values onto the caller's Axes without global state |
| 3 Semantic/identity | dtypes carry values, never Pietto identity; labels are presentation (D67.22) | same | position is row order; no label | coordinates are the relation; record order is not kept | input order is point order |
| 4 Layering | consumes the checked Arrow batch only | same | same, through PyArrow's `to_numpy` | same | same |
| 5 Algorithms | `RecordBatch.to_pandas(types_mapper=pandas.ArrowDtype)` | `from_arrow`, then a schema comparison | `to_numpy(zero_copy_only=False)`, then an owned copy | validate, then build canonical CSR | `Axes.plot` or `Axes.scatter` on float64 arrays |
| 6 Interface/version | observed: the default `to_pandas()` gives `str` for strings, object for decimal and date, and float64 for a nullable Int, losing 2^63-1; `ArrowDtype` keeps all seven probed types and keeps NaN apart from null | observed: the probed types load as Int64, Boolean, Float64, String, Decimal(10,2), Date and Datetime(us) with nulls and NaN apart; `polars` pins its runtime distribution exactly; other widths and refusals to verify | observed: a nullable Int becomes float64 with NaN and loses 2^63-1; null and NaN merge in float64; zero copy is impossible for `ChunkedArray` and for any column with a null | observed on dense input: object and datetime dtypes are refused, NaN is stored, -0.0 and False are not stored; `csr_array` from triplets, kept explicit zeros and int32 indices to verify | observed: `import matplotlib` writes no file; the first `import matplotlib.pyplot` writes `$HOME/.cache/matplotlib/fontlist-v3.11.0.json`; environment, threads, signal handlers, logging, `sys.path` and the working directory stay unchanged; the pyplot-free `Figure()` path to verify |
| 7 Testing/lifecycle | selected-pin matrix | selected-pin schema matrix | dtype, ±0 signbit and copy controls | permutation and zero controls | `Figure()` without `pyplot`; `MPLCONFIGDIR` in scratch |
| 8 Pitfalls/migration | a pin can change dtypes | a pin can change casts | nulls change the dtype | `csr_matrix` and `csr_array` operators differ | `pyplot` selects a backend and writes a font cache |
| 9 Disposition | require `ArrowDtype` | refuse any off-table dtype | non-nullable schema fields only, owned copy | canonical `csr_array` | caller Axes only |
| 10 WHAT_NOT_TO_COPY | inference, default string dtype, NaN as missing | inference and fallback casts | NaN as missing, object arrays, zero-copy views | `sum_duplicates`, `eliminate_zeros` | current Axes, unit and date converters |
| 11 Pietto owner | S02 | S02 | S03 | S04 | S05 |

## Initiation-gate fields

| # | Field | Binding |
| ---: | --- | --- |
| 1 | Live authority | Gate 0 is bound to the published D77.04 head `ab972f36` with natural CI `42831340276` and rebinds the inputs listed above; the draft base `569c365d` is not authority. |
| 2 | Outcome | Five one-batch adapters and the D80.02 user surface; the non-goals above. |
| 3 | Semantic model | The result contract and Arrow binding of `project_arrow_result.py`, the `Float` contract of `language.md` and the `ResultBatch` contract of `execution.md` stay authority; adapters re-decide nothing. |
| 4 | Identity | Field ordinal (argument authority), field label (presentation), row position and multiplicity, null position, the caller's batch and Axes, the new target object, and target package identity (name, pin, wheel hash). Forbidden: label lookup, sorting, deduplication, a duplicate-coordinate winner, an inferred shape, nullability from one batch's values. |
| 5 | Construction states | A call is refused with the batch open and nothing published, or returns one complete target object; Matplotlib validates before the artist exists. Claims move from planned to probed (P0b), qualified at the pin, Gate 2, CI and release. |
| 6 | Proof posture | Asserted: D80 rows. Derived: the type table from the Arrow owner. Observed: the 2026-11-10 probe at the pins (versions, hashes, closures, the CPython 3.13.13 matrices). Verified: installed reports, Gate 2, natural CI. Unknown: the remaining P0b cells and the CPython 3.12 installs, which block the S02–S05 qualification claims that need them. Disproven: a failed row stops. |
| 7 | Layer ownership | `pietto.interop`, the explicit adapter plane (AD80.01), owns argument checks and conversion; the Arrow owner keeps types and finiteness; the execution owner keeps `ResultBatch` and PIE-R4002; PK owns extras, lock and hashes. |
| 8 | Dependency direction | `pietto.interop` reads the public `ResultBatch`, PyArrow and its target, lazily; it imports no `_project` owner, and nothing upstream imports it. S01 checks the imports. |
| 9 | Versioning | A new alpha surface until the Phase82 freeze; no serialized artifact, compiled record or `VERSIONS` change; no migration. A pin change reruns the matrices and is a compatibility decision. |
| 10 | Requirements vs capabilities | The D80.03 table is the requirement; a library's behavior counts only as observed at its pin; no run-time capability or version inference. |
| 11 | Interchange | One in-process Arrow C Data import of one batch into one target object. No process, serialization, file, device or network crossing; DLPack stays Phase86. |
| 12 | Execution | None: adapters compile, execute, connect and read handles not at all, and Matplotlib never renders, shows or saves. |
| 13 | Resource lifecycle | As in "Errors and lifecycle": caller-owned batch, Axes and result; one batch of space; a failure leaves the batch open; no cancellation. |
| 14 | Security and trust | Package identity is the boundary: exact pins, hash-allowlisted closures, installed-wheel witnesses, the PL.05 fetches only; no network, credential, file or database authority; target effects documented; no run-time version check. |
| 15 | Algorithms | One C Data import; the pandas `types_mapper` path; Polars `from_arrow` plus a schema comparison; a NumPy copy; SciPy validation, duplicate detection and canonical CSR; a Matplotlib envelope check. No cache. |
| 16 | Complexity | Per call O(rows × fields) time, SciPy O(n log n + shape[0]); space O(batch + result); rows ≤ 4,096 and 8 MiB per batch; shape dimensions ≤ 4,096. |
| 17 | Invalidation | No persisted fact. An Arrow type or producer change (Phase77 replays), a `PYARROW` change or a target pin change reruns the admission table and the installed cells. |
| 18 | Cache | None in Pietto; target caches such as the Matplotlib font cache are environment effects, not authority. |
| 19 | Concurrency | Synchronous in the caller's thread; no Pietto shared state; no thread-safety promise for one batch or Axes; target thread pools documented. Lanes as in "Lanes and integration". |
| 20 | Diagnostics | No new code; PIE-R4002 kept; the fixed exception order of "Errors and lifecycle"; S01 fixes and tests each message. |
| 21 | Inspection | `num_rows`, `closed` and `pyarrow.schema(batch)` stay the read-only inspection; adapters add none, and reading the schema neither opens nor closes anything. |
| 22 | UX | Python names, ordinals and messages that name the field and the Pietto-side fix (such as `coalesce`); `docs/interop.md` lists every refusal. The fmt and usability-row item is `NOT_APPLICABLE`: Phase80 adds no Pietto spelling; owner: the Phase80 Gate 1 that admits a source candidate such as `round` of a `Float` with digits. |
| 23 | Conformance | The D80.03 table, `docs/interop.md` and the `ResultBatch` contract; ten installed cells; oracles from producer inputs. |
| 24 | Differential and fuzz | No database differential (no SQL changes); metamorphic permutations, ±0 bits, typed empty, null and boundary controls, two-run determinism. A fuzz framework is `NOT_APPLICABLE`: the admission table is finite and closed; owner: Phase81 high-intensity assurance. |
| 25 | Packaging | New `src/pietto/interop/` in the wheel file list; five extras; `uv.lock` regenerated on the integration tree; one hash allowlist; no generated file; the core dependency unchanged. |
| 26 | Support matrix | CPython 3.12 and 3.13, Linux x86-64, glibc ≥ 2.28, `pietto[arrow,interop-X]`; other route extras under the same-PyArrow assumption; no Windows, macOS or 3.14 claim. |
| 27 | Release | `0.2.0`, never before the `0.1.11` cut; alpha until Phase82; a failed row stays refused; breaking changes before 1.0 follow D76.13; release, tag and upload need their own approval. |
| 28 | Readiness and deferrals | Prerequisites: D77.04 publication with natural CI, bound as `ab972f36` (PL.02); P0b's remaining cells; PK. Inform: the lead states the D80.02 Python-user-surface wording to the owner before S01 seals. Deferrals: the completion-audit item (Phase77 S27; PL.01) and D80.06's candidates with their roadmap and freeze-ledger points. |
| 29 | Slice route | P0b → S01 → S02–S05 → S06, with PK-80 beside them; batches IB1 and IB2. |
| 30 | Repair and stop | The budget above; stop for a cap, an unproved row, a package or platform mismatch, a trust or compatibility change, or a repair that widens the table; failed candidates and evidence are kept; pushes need per-batch authorization. |
