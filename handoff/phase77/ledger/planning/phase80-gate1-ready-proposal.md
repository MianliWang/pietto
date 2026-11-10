# Phase80 interoperability and Python surface — Gate 1 ready proposal

Status: PROPOSAL_NOT_APPROVED (2026-11-09). This is planning only. It adds no dependency, public API, test, database execution, release or publication authority.

## Recommended outcome

Deliver five real one-batch adapters above the existing public ResultBatch boundary: pandas, Polars, NumPy, SciPy and Matplotlib. They make a completed caller-owned batch useful in each library. They do not compile, execute, stream, save, reopen or inspect a query.

The first surface is one lazy public package:

~~~python
from pietto.interop import (
    plot_line, plot_scatter, to_numpy, to_pandas, to_polars, to_scipy_csr,
)

def to_pandas(batch: ResultBatch) -> "pandas.DataFrame": ...
def to_polars(batch: ResultBatch) -> "polars.DataFrame": ...
def to_numpy(batch: ResultBatch, column: int) -> "numpy.ndarray": ...
def to_scipy_csr(
    batch: ResultBatch, row: int, column: int, value: int,
    shape: tuple[int, int],
) -> "scipy.sparse.csr_matrix": ...
def plot_line(
    batch: ResultBatch, x: int, y: int, *, ax: "matplotlib.axes.Axes",
) -> "matplotlib.lines.Line2D": ...
def plot_scatter(
    batch: ResultBatch, x: int, y: int, *, ax: "matplotlib.axes.Axes",
) -> "matplotlib.collections.PathCollection": ...
~~~

The pietto.interop root imports neither PyArrow nor a target library. Each
function imports its own target only after accepting one open ResultBatch, then
uses the existing public C Data seam, pyarrow.record_batch(batch). It cannot
take a ResultHandle, query, SQL, iterator, connection, Arrow object or whole
result, and never closes its argument. The returned target object remains
usable after batch.close(). This is a lifetime guarantee, not a zero-copy,
allocator, RSS, device, mutability or thread-safety promise.

Use five independent extras: interop-pandas, interop-polars, interop-numpy,
interop-scipy and interop-matplotlib. Each pins the selected PyArrow version
and exactly one target package. There is no combined interop extra in v1, so
one adapter cannot silently install the other four. The M77 candidate selected
PyArrow 26.0.1; its package identity must be rebound at Gate 0. This proposal
does not claim that the checked-out 26.0.0 metadata has changed.

## v1 conversion contract

The flat adapters preserve selected-field order, row order, multiplicity and
the existing unique Arrow field labels. They never infer semantic identity from
a label or fill, drop, rename, reorder, flatten, stringify or JSON-encode
values. SciPy is expressly different: it projects coordinate records into a
matrix and therefore does not preserve original coordinate-record order.
A source Float is finite binary64 and preserves signed zero wherever the target
can observe it. A typed zero-row batch returns the target's typed zero-row
object rather than an untyped empty container.

| Adapter | Admit | Required output and null rule | Refuse |
| --- | --- | --- | --- |
| pandas | Flat Int, Bool, finite Float and Text, including nullable columns | DataFrame is built with PyArrow-backed pandas ArrowDtype columns: each dtype is the input Arrow field dtype, null is pandas missing data, and typed empty retains that dtype. Field/row order, multiplicity and null positions remain. | Decimal, Date, Timestamp, UUID, nested fields, NaN/infinity, or lost null/value. |
| Polars | Same as pandas | DataFrame comes from the RecordBatch with no schema override or target fallback cast. Acceptance requires the selected-pin native schema matrix: matching integer width, Boolean, Float64 and String, with source null positions and typed empty schema retained. | Same exclusions as pandas, plus any target fallback cast. |
| NumPy | One non-null Int, Bool or finite Float column by ordinal | One-dimensional native-dtype ndarray with input row count; typed empty is shape (0,) with that dtype; signed zero survives. | Nullable, Text, Decimal, temporal, UUID, nested values, object/mask/stringification conventions or bad ordinal. |
| SciPy | Three distinct non-null Int columns by ordinal: row, column, value; every shape dimension is at most 4096 | csr_matrix of explicit non-negative shape; zero-based coordinates; each distinct coordinate/value record becomes one stored entry, including explicit zero. It preserves the coordinate relation, not input-record order. | Inferred or oversized shape, duplicate coordinates, negative/out-of-range coordinates, null/non-Int fields or implicit zero dropping/reduction. |
| Matplotlib | Two distinct non-null finite Float columns, or Int values in the exact Float64 envelope -2**53 through 2**53, and caller-owned Axes | plot_line returns Line2D, plot_scatter returns PathCollection; input order becomes artist order. All values are checked before the artist is created. | Null/non-numeric/nested values, out-of-envelope Int, sorting, aggregation, pyplot/current-Axes, figure/backend selection, show, save or ownership of caller axes. |

Pandas uses Table.to_pandas(types_mapper=pandas.ArrowDtype), the documented
Arrow-backed dtype path. Polars uses from_arrow with its RecordBatch input and
no schema override; because Polars documents that unsupported Arrow types may
be cast to a closest type, every v1 accepted field has a selected-pin native
schema assertion and a fallback cast is a refusal. A target-pin change reruns
both matrices and is a compatibility decision.

### External-reference review

Snapshot/date: pandas and Polars official documentation reviewed 2026-11-09:
[pandas PyArrow guide](https://pandas.pydata.org/pandas-docs/stable/user_guide/pyarrow.html)
and [Polars from_arrow](https://docs.pola.rs/py-polars/html/reference/api/polars.from_arrow.html).
Problem/constraints: make one Arrow batch useful without losing nulls or
silently casting. Semantic/identity model: library dtypes carry values; they
do not establish Pietto identity. Layering/dependency direction: adapters only
consume the checked Arrow batch. Algorithms/data structures/complexity: one
batch conversion, no aggregate state. Interface/version/capability model:
pandas documents ArrowDtype through Table.to_pandas; Polars accepts
RecordBatch but may cast unsupported Arrow types. Testing/operational
lifecycle: selected-pin matrices prove the admitted rows. Pitfalls/migration
costs: a target pin can change dtype/cast behavior. Disposition: require
ArrowDtype for pandas and reject a Polars fallback cast. WHAT_NOT_TO_COPY:
neither library's type inference or fallback casting becomes Pietto behavior.
Pietto owner affected: the Phase80 adapter plane only.

## Errors, lifecycle and limits

ResultBatch keeps its existing closed-input error: HandleMisuse / PIE-R4002.
The adapter owns only input validation: wrong public type is TypeError; a bad
or duplicate ordinal, prohibited coordinate or source shape is ValueError. A
missing selected extra raises ordinary ModuleNotFoundError; a target-library
failure is not wrapped. No new PIE family is added.

A call converts exactly one batch. It may allocate its returned target object,
but has no whole-result accumulation, cache, executor, thread, filesystem,
network, credential, database or device authority. Target conversion failures
leave the input batch open. No Pietto cancellation exists because conversion
has no Pietto-owned asynchronous operation.

## Exact first implementation ownership

| Slice | Product owner and test owner | Completion boundary |
| --- | --- | --- |
| S01 common seam/package | New src/pietto/interop/__init__.py and one private common owner; tests/test_results_interop.py, extending tests/test_results_arrow_ownership.py, tests/test_results_optional_arrow.py and tests/test_release_installation.py | Lazy core import, one-batch/lifetime/error rules, extras and installed-artifact witnesses. |
| S02 tabular | src/pietto/interop/_pandas.py and _polars.py; tests/test_results_interop_pandas_polars.py | Flat matrix, nulls, typed empties, post-close use and dtype receipts. |
| S03 NumPy | src/pietto/interop/_numpy.py; tests/test_results_interop_numpy.py | Ordinal/non-null numeric shape/dtype and signed-zero rules. |
| S04 SciPy | src/pietto/interop/_scipy.py; tests/test_results_interop_scipy.py | Coordinate/shape/duplicate/zero rules. |
| S05 Matplotlib | src/pietto/interop/_matplotlib.py; tests/test_results_interop_matplotlib.py | Caller-Axes and artist/order rules, no backend ownership. |
| S06 audit | Existing package, result and release-note owners; no phase-named test | Cross-adapter package matrix, acquisition consolidation, docs, completion audit and handoff. |

A shared tests/_pietto_results_interop.py is justified only if batch/fixture
construction is duplicated across two target owners. It contains no test cases
and imports no test module.

compile_queries(...), native array/JSON columns, postgres_adbc nested results,
round(Float, digits), and the Arrow data-analysis example are explicitly outside
S01--S06. They remain named Phase80 candidates and cannot enter as an adapter
convenience.

## Qualification and proposed ceiling

Each adapter requires a core-only import negative, selected-extra
installed-wheel witness, missing-extra negative, closed-batch negative,
no-execution/no-handle side-effect control, typed empty, nullable/refusal,
order/multiplicity and post-close witness. Tabular adapters additionally need
logical type/value/null oracles; NumPy needs binary signed-zero checks; SciPy
needs coordinate permutations, duplicate and stored-zero controls; Matplotlib
needs a noninteractive caller-Axes identity/control. A pre-existing
ResultBatch means no database campaign follows from one-batch conversion.

Proposed Phase80 cumulative ceiling is C140/F420/D3000/S12, with the current
units: causal roots, every pytest launch, outer diagnostic commands and scope
repairs. It is new-phase authority only if adopted at Gate 1; it never resets
or spends the Phase77/M77 ledger. Stop before another slice for an
unproved target dtype/null behavior, package/platform mismatch, trust or
compatibility change, budget cap, or a repair requiring a broader table.
Preserve failed candidates and installed-target evidence; never create a
fallback conversion.

## Gate 1 field disposition

| Fields | Proposed binding |
| --- | --- |
| 1--2 | Rebind main, Phase77/M77 closure and natural CI. Outcome is five adapters, not query execution or a general data-science runtime. |
| 3--6 | Existing ResultBatch/Arrow meaning remains authoritative. Ordinal, label, order, multiplicity and null position are separate identities. Only selected-pin installed witnesses make concrete target claims. |
| 7--8 | pietto.interop is downstream adapter ownership. Semantic, project, SQL, execution and Arrow owners keep authority; adapters cannot re-decide meaning. |
| 9--11 | New alpha Python surface; no migration or serialized adapter artifact. One live batch crosses to one in-process target object only. |
| 12--14 | No Pietto execution, I/O, network, credential or database authority. Caller owns batch and axes. Exact wheel/pin/RECORD is the package trust boundary. |
| 15--16 | One C Data import and bounded per-batch conversion. Space may be proportional to the returned target object; cache and whole-result accumulation are forbidden. |
| 17--19 | No Pietto cache. Batch close does not invalidate returned object. Calls use caller-thread target calls and no shared Pietto state. |
| 20--22 | Keep PIE-R4002; otherwise use the stated standard Python errors. No syntax or CLI. Docs list every refusal and caller-Axes rule. |
| 23--24 | Pin-specific installed matrices and independent Arrow/oracle controls; no database differential/fuzz obligation for one in-memory batch, but permutation/zero/null controls apply. |
| 25--27 | Five extras, exact pins, lock and installed-wheel smoke; supported Python/platform matrix is bound at Gate 1. Release follows its separate delivery decision. |
| 28--30 | Exact pins/platforms and target matrices are prerequisites. S01--S06 is the route; C140/F420/D3000/S12 is proposed. Stop/failure preservation applies; commit, push and natural CI require separate authority. |

## Decisions required to activate

1. Approve or amend the six signatures, five adapter rows, standard-error
   policy and five-extra package shape as one compatibility decision.
2. Select exact target pins and supported Python/platform matrix after official
   metadata and installed-wheel inspection.
3. Approve or amend C140/F420/D3000/S12 and S01--S06. The deferred Phase80
   candidates remain deferred until a later Gate explicitly opens them.

No library was installed, no external version was queried, and no test,
database action or product change was performed for this proposal.
