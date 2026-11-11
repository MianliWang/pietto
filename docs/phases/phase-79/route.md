# Phase79 route — B1 limited DuckDB path, Gate 1 approved, Gate 0 bound (health and overlap pending)

Phase79 owns the Phase 79 row of the [roadmap](../../roadmap.md#future-roadmap-v6):
DuckDB deep adaptation, with the limited local analysis path that `0.2.0`
requires. Under AD78.01, as AD78.02 revises its schedule (sheet Q7 A′), that
limited path publishes before Phase78 SQLite B1, which is implemented in
parallel ([third dialect](../../roadmap.md#third-dialect)). On 2026-11-10
(America/Toronto) the owner approved the Gate 1 of its first vertical, B1,
with the recommended answers of the lead's decision sheet. These are
D79.01–D79.08 and AD79.01, the third-dialect seam AD78.03, and the rows
PL.01–PL.06 shared with Phase78, Phase80 and the editor core, in the
[decision record](../../decisions.md). The approval covers local lane work
from Gate 0, its offline probe cells and its validation (PL.01, PL.02). It
grants no commit, push, tag, release, package upload, extension-repository
push or Marketplace action. B1 publishes only under its own later push
authorization (PL.04). B1 is one vertical; it does not complete Phase79.

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

This route was drafted on the maintenance/editor batch candidate
`569c365dbb66d48d87da4dfca0982e09d21d0061` (tree
`5561238f181887274dbadbdd5fa848998cfa1872`), which is not Phase79's baseline.
The batch was published under D77.04 instead as `befa5de8`, `6a1eb9c9` and
`ab972f36`.

Gate 0 of every Phase79 lane is bound to the head that published the D77.04
batch (PL.02): `main` at `ab972f362c433b234a74f542c5d274d22c8cdeae` (tree
`821be1ccf7bb6f3e14b8d00d80f1f30d3cc087fe`), whose natural exact-head CI
`42831340276`, push/main attempt 1, passed all 21 jobs. At that head it
rebinds the branch, tree, remote, CI, the qualified health and alerts of that
CI, the source, the tests and the controlling contracts. A lane that starts
later binds the newest published head and names that base tree in its brief.
Health is advisory: it changes no scheduler, topology or placement, and too
little history does not prove green. The midpoint and the closeout read the
health again.

What the drafting tree holds, unchanged on `ab972f36`:

- `src/`, `tests/`, `pyproject.toml` and `uv.lock` contain no DuckDB code or
  pin.
- sqlglot is absent, and existing tests lock that absence: the core-dependency
  check in `tests/test_sql_mysql_connector_semantic_surface.py`, and the
  PostgreSQL and MySQL relation-module checks.
- The Arrow identity is `pyarrow==26.0.1` (M77.01).
- `execute()` knows three routes and two dialects, and requires a premise
  on every route.
- The sheet counts 403 comparisons of a `family` value in 39 files (the
  drafting tree has 410 matching lines in 39 files). Some take a binary
  default (`project_sql_emission_rendering.py:80,265`,
  `project_execution.py:387`); others fail closed
  (`project_refinement_order.py:50-53`). Where a binary default lies on its
  path, an unexpected third family would silently fall into a PostgreSQL or
  MySQL branch; the AD78.03 firewall keeps `duckdb` off those paths.

Phase77 write sets have been measured for only 8 of its 27 slices, all on the
scratch base `bd18a4c3`, which descends from neither `569c365d` nor
`ab972f36`. Gate 0 measures the overlap again on the published head.

**Previous completion audit: NOT_APPLICABLE.** The gate asks each phase to
consume the previous phase's completion audit. Phase77 is still open and has
none. Gate 1 consumes instead:

- the [Phase76 completion audit](../phase-76/completion-audit.md) and its
  Phase77 handoff;
- the facts of Phase77's published batches;
- the lessons listed below.

The owner of this item is Phase77 S27. The first Phase79 replay after the
Phase77 audit is published consumes that audit (PL.01).

The applicable [engineering lessons](../../references/engineering-lessons.md):

| Lesson | What it means for Phase79 |
| --- | --- |
| 75-1 and Phase74 lesson 2 | Start from the publishing head, or name the base the replay carries, and carry the base delta, not its resolutions. |
| Phase72 lesson 2 | Repository-wide locks fail only on the integrated tree. The family firewall is such a lock. |
| Phase72 lessons 1, 3 and 4 | Run `pyright` on touched tests. A relayed owner message is for the lead. A verdict comes only from real outputs and has a self-test against fabricated ones. |
| Phase68 audit lesson 4 and Phase69 lesson 2 | Find every literal pin reader before a pin lands, and change them all in one commit. |
| Phase69 lesson 5 | A version string is not build identity. Native evidence binds the installed artifact. |
| 75-3 | A test that can skip can pass without running. |
| 75-4 | A lane writes only under its own name. |
| 76-1, 76-4 and 76-6 | Bind the executed input. Keep claims bounded. Reuse evidence only for the same input closure. |
| Phase74 lesson 3 | A witness named live calls `compile_query`. |

## Outcome

B1 is one local, read-only query over one Arrow table that the caller
supplies. It returns through the existing `ResultHandle` and `ResultBatch`
(D79.01):

| Admission | Exact limit |
| --- | --- |
| Project and source | An explicit-module project with exactly one `source x: Shape = duckdb.arrow("key")`. The key is a non-empty string, used exactly, with no normalization or case folding. |
| Relational shape | A direct projection, optionally with one direct comparison `IntField <op> param`, where `<op>` is `==`, `!=`, `<`, `<=`, `>` or `>=`. No relation `let` or derived source. |
| Parameter | None for a projection, or exactly one declared non-null `Int` used once in the comparison, through the existing exact binding. A projection needs no dummy parameter. |
| Columns | `Int`, `Text`, `Bool` and finite `Float` for source and result. Each keeps its compiled nullability and source order. `Text`, `Bool` and `Float` are projected only. |
| Literal policy | `preserve` only. |
| Entry points | `check --project`, `emit-sql --project --dialect duckdb`, `compile_sql`, `compile_query` and `execute(route="duckdb_arrow")`. |

Results are compared as bags, because B1 has no ORDER BY.

Not in B1:

- arbitrary SQL, file, database or connection URIs, caller settings, catalog
  access, extension loading, SQL functions and UDFs;
- more than one input, JOINs, aggregation, windows, ORDER BY and LIMIT, set
  operations;
- `Decimal`, temporal, `UUID` and nested types, and the `bind-safe` literal
  policy;
- single-file mode and `emit-sql FILE --dialect duckdb`;
- bundles, saved results, relay, jobs and installation automation;
- sqlglot;
- any change to PostgreSQL or MySQL SQL bytes or contracts, and any claim of
  parity across databases.

Phase80 consumes only a separately qualified `ResultBatch` conversion
boundary.

Whether `0.2.0` also needs a B2 (group by with `count`, `sum`, `min` and
`max`, then ORDER BY and LIMIT) is still the owner's decision; see the
deferrals table.

## Decisions adopted

| ID | Rule | Sheet source |
| --- | --- | --- |
| PL.01–PL.06 | **Shared answers.** Parallel start, own ledger, lane rules and the previous-audit item (PL.01); Gate 0 and the work before it (PL.02); host pytest workers (PL.03); integration and version line (PL.04); dependencies, the PK lane, platforms and CI (PL.05); the planning ledger (PL.06). | Q1 A, Q2 A, Q3 A |
| D79.01 | **B1 scope.** The outcome above. Refusals reuse existing codes with new details; a new PIE code needs the owner. The mapping of each refusal to an existing code is the lead's derivation from DuckDB draft G2, stated to the owner as inform before S01 binds. | Q8 A; draft G2 (lead, inform) |
| D79.02 | **DuckDB pin.** `execute-duckdb = ["pyarrow==26.0.1", "duckdb==2.0.0"]`, pinned literally under PL.05. `2.0.0` is the release the authorized probe resolved and installed; no LTS status is claimed. Another release needs a new install probe and the owner. | Q3 A; the 2026-11-10 probe |
| D79.03 | **Execute API.** `DuckDBArrowInput(name, table)` is frozen, refuses copy and pickle, and does no I/O. `premise=None` is accepted only for `duckdb_arrow`, which changes the PIE-R1001 rule text. `isolation` accepts only `"stable"`, which means the owned capture snapshot. The input name must equal the contract `relation.name` and the connector argument (D76.06). There is no premise type, no `execute_local`, and no change to `ExecutionLimits`. | Q8 A |
| D79.04 | **Capture.** At most 65,536 rows and 16 MiB measured by `Table.nbytes` before the copy; this is a fixed private policy. The Arrow types are int64, string, bool and float64 only. A non-null compiled field requires `null_count == 0`. NaN and ±Inf are refused. `-0.0` is admitted under the `Float` value contract; sheet Q8 asks only that its handling be stated, so this is the lead's derivation, stated to the owner as inform before S01 binds. Text must be valid UTF-8. The capture is an owned copy without unselected backing. Refusals are PIE-R1002 `DUCKDB_ARROW_CAPTURE_LIMIT` and `DUCKDB_ARROW_SCHEMA`. | Q8 A; draft G8; `-0.0` lead, inform |
| D79.05 | **Emission contract.** The target is `{"family": "duckdb", "release": "2.0.0"}` (D79.02), each source has `scan: "arrow_registration"`, and `MAX_PARAMETERS` has DuckDB's own limit (pending S00). This is a public compatibility change. | Q8 A |
| D79.06 | **Session hardening.** Extensions are never installed or loaded automatically. External access is off. Replacement scans are off. `threads` and `memory_limit` are explicit. Nothing spills to a temporary directory. The configuration is locked and read back. If any item cannot be proven on the pin, the route is refused. | Q8 A |
| D79.07 | **Qualification.** An in-process native matrix runs on the integration host, with no Docker and no engine lock, under a new runner-acceptance domain row. Natural CI installs the pinned duckdb into `arrow-ready`. | Q3 A; draft G7 A |
| D79.08, D79.09 | **Budget.** `C120/F360/D4100/S4` from sheet §3.2, plus a half share of PK `C40/F120/D1200/S4` (PL.05). The owner chose it on 2026-11-11 (D79.09), which ends the D1800 stop point that the lead had taken as the lower plausible reading of the option selected at Gate 1. | §3.2; the owner's answer of 2026-11-11 |
| D79.10 | **Outcome values.** The S04 candidate's provisional `duckdb_arrow` outcome values, the details `DUCKDB_RESULT_CHECK` and `DUCKDB_ARROW_CAPTURE_COPY`, the failure phase names `driver`, `session`, `query`, `result`, `delivery`, `finalization` and `consumer`, and the PIE-R5001 cleanup entry names `unregister` and `close` are accepted; a name outside these lists, or a later change, goes back to the owner. | the owner's answer of 2026-11-11 |
| D79.11 | **PyArrow missing or another release.** PIE-R2001 or PIE-R2002, raised as `RequestRejected`, as on the other Arrow routes; `execution.md` changes its category sentence. | the owner's answer of 2026-11-11 |
| D79.12 | **Informs.** The D79.01 refusal mapping, the D79.04 `-0.0` admission and the spec's derived items (namespace `"arrow"`, `arrow_*` storage kinds, `Text` ordering `"C"`, parameter limit 65,535) stand. The lead also stated AD79.01 to the owner on 2026-11-11, as inform: it stays the lead's decision, and an objection from the owner before S04 seals reopens it. | the owner's answer of 2026-11-11; the lead's statement of 2026-11-11 |
| AD78.03 | **Third-dialect seam (ARCHITECTURE_DECISION).** DuckDB gets an independent adapter with its own SQL AST, renderer and artifact verifier. It consumes `ProjectSQLPlan`, with dispatch at the CLI, `compiler._emit` and `compile_query`. The PostgreSQL/MySQL pipeline never receives `"duckdb"` or `"sqlite"`. A family firewall test reruns on the integration tree at every replay. S02 lands the shared connector and dialect-set hunks first; Phase78 S02 adds its SQLite entries only after that, serially, so those lines have one writer at a time. Assumption: `ProjectSQLPlan` is target-neutral. Not taken: threading a third family through the existing pipeline (B), or a general dialect registry (C). | Q9 A |
| AD79.01 | **Failure ownership (lead ARCHITECTURE_DECISION, inform).** DuckDB runtime errors become the existing `AttemptFailed`/`Failure` with phase, type name, `sqlstate=None` and `vendor=None`, as `MySQLFailure` does. An interrupt counts as cancellation. An overflow is a native target failure, with no new PIE promise. | draft G5 |

E-C is the editor-core package (ED.03–ED.06). Its batches reach `main` and
widen the `0.1.11` alpha surface (PL.04). Phase79 replays only at Phase77
published-batch boundaries (PL.04), and a replay takes in the E-C batches
published before that boundary.

## Dependencies and pins

| Input | State at Gate 1 | Bound by |
| --- | --- | --- |
| PyArrow | `26.0.1`, observed in every Arrow extra (M77.01); the probe's wheels `pyarrow-26.0.1-cp312-cp312-manylinux_2_28_x86_64.whl` (sha256 `c718bf97a92a6dea97fd1062c3b9f9e2e83cb9cc926e752289fa4ffff41738f9`) and `pyarrow-26.0.1-cp313-cp313-manylinux_2_28_x86_64.whl` (sha256 `f71221bbc7707e3fad920d0478db9350791d4714ec445299ee0d56559fbc156c`) carry the hashes in `ci/phase67-arrow-compatibility-requirements.txt` | Gate 0 rebind |
| DuckDB distribution and exact release | **Observed:** `duckdb` `2.0.0`, the latest stable release on PyPI at 2026-11-10T11:32:46Z (first uploaded 2026-10-21T12:50:38Z, `requires_python >=3.11.0`). No LTS status is claimed (D79.02). | Probe; D79.02 |
| Wheel and hash; cp312/cp313 manylinux x86-64 | **Observed:** one wheel serves CPython 3.12 and 3.13, `duckdb-2.0.0-cp312-abi3-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`, sha256 `ab51ec57d329d6f3df37c0287b55d71c3fc07bb54b61d1afed09104f953b1431`, not yanked; it needs glibc ≥ 2.28 at most. The hashed requirement files list every file of the pinned version. | Probe |
| Install | **Observed on CPython 3.13.13 only:** a fresh venv installed the 17-pin closure with `--require-hashes --no-deps`, and `uv pip check` passed. CPython 3.12 was resolved (same pins and hashes) but not installed; its install comes from PK's package smoke and natural CI. | Probe; S05 (PK) |
| Installed `METADATA`/`RECORD` and module origin | **Pending S00** (offline, in the probe's environment, after Gate 0). At run time, a missing, mismatched, shadowed or non-owned import is refused through the existing driver refusal family. | S00, then S04 |
| DuckDB parameter limit for `MAX_PARAMETERS` | **Pending S00** | S01 |
| Session settings | **Observed defaults on 2.0.0:** `python_enable_replacements=true`, `enable_external_access=true`, `autoinstall_known_extensions=true`, `autoload_known_extensions=true`, `lock_configuration=false`, `temp_directory=.tmp` (a relative path), `max_temp_directory_size` 90% of available disk, and `threads=32` and `memory_limit=24.9 GiB` from this host. Replacement scans find a table in a local of the frame that calls `con.sql`, not of an outer frame; after `SET python_enable_replacements = false` that lookup fails with CatalogException, while `register` and `from_arrow` still work. **Pending S00:** setting and locking every D79.06 value, its read-back, and proof that extensions, external access and temporary spill stay off. | Probe; S00, then S01 |
| Arrow round trip | **Observed on 2.0.0:** `from_arrow`, `register` and same-frame replacement scans read all four probe tables, both empty shapes included; nulls, NaN, 2^63-1 and 9999-12-31 are kept. `to_arrow_table()` returns the original types but drops non-null flags; `fetch_arrow_table()` is deprecated and warns; `.arrow()` returns a `RecordBatchReader`. | Probe; S04 |
| `Table.nbytes` and the measure of the owned copy | **Pending S00 and S04** | S04 |
| Extra | `execute-duckdb = ["pyarrow==26.0.1", "duckdb==2.0.0"]` | S05 (PK) |
| sqlglot | Not introduced in B1 | — |
| CPython | 3.13.13 and 3.12.13 on the integration host (runner-acceptance rows 0b and 2) | Gate 0 |

The network step is that of PL.05: the one PyPI metadata/hash fetch and
isolated install probe, shared with Phase80 (pandas, polars with
polars-runtime-32, numpy, scipy and matplotlib), which ran outside every
repository at 2026-11-10T11:32:46Z before Gate 0. PK resolves offline from the
probe's uv cache for the `uv.lock` regeneration and package smoke on each
integration tree; any new networked package or metadata fetch needs a separate
owner approval. The probe facts this route relies on are stated inline in the
table above: the versions, the wheel tags and the duckdb and PyArrow wheel
sha256 values. The raw probe outputs are owner-held working records outside
Git. Until PK seals, when PL.05 removes them, the probe's uv cache and venv
are the offline package source for lane environments on CPython 3.13. Version
numbers seen in earlier drafts without network authority are not facts.

## Slices

The column "Sheet" names the lane in the decision sheet. Budgets are
`C/F/D/S` planning allocations inside the ledger, not separate caps.

| Slice | Sheet | Content | Write set | Checks | Depends on | Budget |
| --- | --- | --- | --- | --- | --- | --- |
| S00 | D0 | Package evidence: the completed 2026-11-10 fetch and install probe (PL.05), plus the remaining offline cells in the probe's environment: the parameter limit, setting and locking each D79.06 value with its read-back, extension, external-access and spill absence, installed `METADATA`/`RECORD` and origin, `Table.nbytes`; the 11-item external-reference record | None in the repository: the probe's environment (outside Git, removed after PK seals, PL.05) and the lane's own evidence folder | The wheel sha256 values stated under "Dependencies and pins" bind the exact wheels; an independent read-only review | Fetch and install: done before Gate 0 under PL.05 (a) (sheet Q3 A, owner 2026-11-10); remaining cells: Gate 0 | 5/10/150/0 |
| S01 | D1 | Alpha spec: admission, API, capture, contract values, session settings and their values, the check order, the refusal catalogue with exact detail strings, the usability row, and the shared-page hunks | New `docs/spec/duckdb-arrow-route-v1.md`; new `docs/release-notes.d/79-s01-duckdb-arrow-route.md` | `scripts/release_notes.py check`; `tests/test_repo_docs_links.py`; `tests/test_repo_release_notes_fragments.py` | S00 | 5/10/100/0 |
| S02 | D2 | Target identity and the shared connector and dialect sets; the family firewall (AD78.03), which keeps `duckdb` and `sqlite` out of the PostgreSQL/MySQL pipeline, so no binary-default comparison there changes. Any binary-default edit that proves necessary is a measured exception the owner sees before it lands. | The connector set in `semantic/source_connectors.py` and its admission in `ir/lowering.py`; the plan's target admission (`project_sql_plan.py`, `project_sql_plan_target_assessment.py`); `FAMILIES` in `project_sql_emission_portable_schema.py` (`:831`); `RELEASES`, `MAX_PARAMETERS` and the scan value in `project_sql_emission_contract.py` (`:39-40`); the dialect choices of `cli.py` and `project_sql_emission_cli.py`; `execution/_query.py` (`_CHOICES`). Not written: `project_sql_plan_verification.py`, `project_sql_plan_pure_boundary.py` and the other Phase77 emission hot files. Tests in `tests/test_semantic_source_connectors.py`, `tests/test_project_capability_target_matrix.py` and `tests/test_sql_emission_closure.py`; the firewall, listing `duckdb` and `sqlite`, goes into a repository owner. | Focused tests; Ruff; `pyright` on `src` and on `pyrightconfig.tests.json`; the repository-wide owners and the firewall on the merged tree; goldens unchanged; `pietto fmt` keeps the spelling; single-file bytes unchanged; the lead decides whether D76.12 applies | S01 | 15/45/400/1 |
| S03 | D3 | Independent adapter (AD78.03) | New `src/pietto/_project/project_duckdb_*.py`; dispatch hunks in the CLI, `compiler._emit` and `compile_query`; new `tests/test_sql_duckdb_emission.py`; `tests/test_sql_compile_api.py`; `tests/test_cli_project_emit_sql.py` | `compile_sql` returns the bytes of `emit-sql --project --dialect duckdb --format json`; a live query is built only from a VERIFIED document; a forged artifact is refused; PostgreSQL/MySQL goldens are unchanged; the adapter imports no duckdb, pyarrow or sqlglot | S02 | 35/105/900/1 |
| S04 | D4 | Execution route, capture and lifecycle (D79.03, D79.04, D79.06, AD79.01). Results are fetched with `to_arrow_table()` at the pin, never the deprecated `fetch_arrow_table()` or `.arrow()`, which returns a `RecordBatchReader`; because `to_arrow_table()` drops non-null flags, S04 restores and verifies the compiled nullability before it binds a `ResultBatch`. | New `execution/_duckdb.py`; `_access.py`, `_handle.py`, `execution/__init__.py`; refusals in `_query.py` (`export_bundle`), `project_job_store.py` and `project_execution.py`. The DuckDB storage kind lives in its own module and is wired into `project_result_binding.py` and `project_execution_reader.py` only after Phase77 S23. Tests in `tests/test_execution_api_queries.py`, `tests/test_execution_api_errors.py`, `tests/test_execution_api_results.py` and `tests/test_results_optional_arrow.py`; new `tests/test_execution_api_duckdb_arrow.py` and `tests/_pietto_execution_duckdb.py` | Every request check runs before any DuckDB or PyArrow import; controls with forged tables; caller mutation after the call; close, cancel, deadline and setup failure; the existing routes' refusals unchanged | S02; the end-to-end tests need S03 | 30/90/800/1 |
| S05 | PK | `execute-duckdb` packaging (D79.02) | `pyproject.toml`; `uv.lock`, regenerated on the integration tree offline from the probe's uv cache (PL.05); `tests/test_release_installation.py`; `scripts/package_smoke.py`; `ci/phase67-arrow-compatibility-requirements.txt`, the arrow-ready hash allowlist that package smoke installs; every literal pin reader | Package smoke with `--extra-env`, including the CPython 3.12 install, whose PyArrow wheel the probe's uv cache lacks (its fetch needs the owner, PL.05); installed wheel and sdist cells; pin-reader search | The PK schedule of PL.05: after Phase77's next published batch, integrating after Phase77 S26 | PK |
| S06 | D6 | Native qualification (D79.07) | Native cells in `tests/test_execution_api_duckdb_arrow.py` and `tests/test_harness_execution_api.py`; the domain row in `docs/spec/validation-runner-acceptance-v1.md` and `docs/development.md` | The matrix below. Both documents are VR2 acceptance rule paths, so the batch that carries S06 runs its whole Gate 2 on the integration host, and no new bootstrap is recorded (PL.05; owner, 2026-10-27) | S03, S04, S05; the midpoint | 15/45/500/0 |
| S07 | D7 | CI wiring | The extra-env contents in `scripts/package_smoke.py` and `ci/phase67-arrow-compatibility-requirements.txt`, and `.github/workflows/ci.yml` only if needed; `ci_workload` declarations | Depth-one validation; the registry stays core-only | S06 | 5/15/150/0 |
| S08 | D8 | Closeout: the B1 acquisition consolidation; the shared pages; freeze-ledger rows; the audit with its Phase78 and Phase79-B2 handoff | `docs/capabilities.md` (its own "DuckDB local path" subsection), `docs/spec/diagnostics.md`, `docs/execution.md`, `docs/project-package.md`, `docs/language.md`, `docs/roadmap.md`, `docs/status.md`, the fragment, `docs/phases/phase-79/completion-audit.md` | Docs and fragment tests; the bounded ten-slowest profile after publication; the Gate 2 duration is recorded | S06, S07; Phase77 S26 for the shared pages, unless the subsection stands alone | 10/40/300/1 |

The replay reserve is D800.

The order of development is S00, S01, S02, then S03 and S04 in parallel,
then S05, S06, S07 and S08. Each slice is one commit.

S02 lands the shared connector and dialect-set hunks first (AD78.03), and no
other lane edits those lines until S02 has integrated. It writes the DuckDB
entries in a shape that the SQLite entries extend, and its firewall lists
`sqlite` beside `duckdb`. Only after that does Phase78 S02 add the SQLite
entries, serially on S02's integrated lines and on Phase78's ledger, so the
lines have one writer at a time. Under AD78.02 (sheet Q7 A′), SQLite B1
publishes after Phase79 B1.

A ruling from the lead that `duckdb.arrow` changes the built-in catalog makes
the extension sync of D76.12 part of the closeout. That sync is only prepared:
sheet Q4 is not approved, and nothing here pushes to the extension
repository.

## Qualification method

**Emission:**

- Pietto owns the expected SQL bytes of each admitted shape.
- `compile_sql` returns exactly the CLI JSON bytes.
- `compile_query` accepts only a VERIFIED document.
- The adapter's own verifier refuses forged artifacts.
- PostgreSQL and MySQL goldens and byte outputs stay unchanged.

**Native runs:**

- The matrix runs in process, on the integration host, against `duckdb`
  `2.0.0` (D79.02).
  It needs no Docker and no engine lock; D76.16 does not apply.
- The oracle is Pietto-owned Python, computed from the Arrow input and
  written before the run.
- The verdict comes only from saved outputs. A self-test feeds fabricated
  outputs and must fail every fail-open shape. An independent integrity audit
  reads the verdict (lessons 72-4 and 74-1).

The matrix covers:

- dependency identity: a missing, mismatched or shadowed driver is refused
  before any session;
- the caps: 65,536 rows against 65,537, and 16 MiB at and above the limit;
- refused Arrow types and values: dictionary, large_string, string_view,
  extension and null types, NaN, ±Inf, invalid UTF-8 and NUL;
- admitted values: `Int` extremes, the bits of `-0.0`, NULL only in nullable
  fields;
- each comparison operator;
- caller mutation after the call;
- the read-back of every session setting;
- close, cancellation, deadline and setup failure;
- the absence of any extension load, file or network effect;
- result labels, order and multiplicity.

Combinations are tested with real queries (reminder 10). A test that needs the
extra fails in the run meant to provide it and prints a skip line anywhere
else, and acceptance counts skips beside passes. A failed cell keeps its
refusal, and no fallback is invented.

**Runners and CI:**

- S06 adds a runner-acceptance domain row. Rows 3 and 4 are not borrowed.
- S07 puts the pinned duckdb into `arrow-ready`, so natural CI holds the
  DuckDB native evidence.
- S06 edits `docs/development.md` and
  `docs/spec/validation-runner-acceptance-v1.md`, and S07 may edit
  `.github/workflows/ci.yml`; all three are among the eight VR2 acceptance
  rule paths. The batch that carries any of them runs its Gate 2 wholly on the
  integration host. Under the owner's 2026-10-27 decision its natural CI is
  not recorded as a new bootstrap, and the Teach split stays void (PL.05,
  [runner acceptance](../../development.md#validation-runner-acceptance)).

**Gate 2 and natural CI:**

- Gate 2 runs one authoritative Python 3.13 validation of the batch tree.
- It reruns the golden and package checks; their inputs change.
- It reruns no generated check: B1 changes no grammar.
- Natural CI owns the final Python 3.12 and 3.13 coverage.

## Lanes and integration

- Each lane starts from the latest integration head and rebases onto it again
  before delivery. Its brief names the base tree. A replay carries the base
  delta with plumbing and compares the changed lines.
- The repository-wide owners and the firewall run on the integration tree at
  every replay.
- Lanes follow the lane rules of PL.01 and the pytest worker rule of PL.03;
  Gate 2 shares the integration host under PL.01, with the authoritative
  worker cap of PL.03. No Phase79 rule raises it.
- `uv.lock` is only ever regenerated, never merged as text, and all readers
  of a pin change in one commit (PL.05). Shared pages are edited serially at
  integration, and each slice keeps its own fragment.
- Under PL.04, B1 publishes after the `0.1.11` cut as one batch with its own
  push authorization: one commit per slice, one authoritative validation, one
  fast-forward push and natural CI on the batch head. A failed head is kept
  and repaired by a child, never rerun.

Route and decision records (documentation only, with no code and no
release-note fragment) may reach `main` before the `0.1.11` cut, in a Phase77
batch under D77.06 or in a documentation and tool batch under D77.14;
Phase78–80 code and fragments may not. By the lead's ruling (PL.04, lead,
inform), this route reaches `main` in a Phase77 batch under D77.06, because
the batch also carries a Phase77 repair, counted on Phase77's ledger, that
returns PIE-B1003 refusals of project `/` and `%` instead of crashing. D77.14,
a rule for a whole documentation and tool batch, does not cover it.

## Budget, midpoint and stops

The cumulative ceiling is `C120/F360/D4100/S4`, recorded from sheet §3.2,
which includes the D800 replay reserve (D79.08). The option the owner selected
at Gate 1 named no figure, and the lower plausible reading of it, the DuckDB
proposal's `D1800`, was the stop point until 2026-11-11, when the owner chose
`D4100` (D79.09). It is Phase79's ledger, not Phase77's,
and no handoff or lane resets it. The shared PK ledger, `C40/F120/D1200/S4`, is
borne half by Phase79 and half by Phase80 (PL.05). D counts one per
diagnostic command, and a loop inside one command counts once (D76.17). The
planning entry charged here is the DuckDB draft's 33 and this route's
drafting 20 shell commands, plus any later fix of this route and Phase79's
share of the shared passes after the approval. The 19 commands of the shared
PyPI/install probe open the PK ledger, and PL.06 records the shared sheet,
critique, review, consolidation and fix-pass commands once and keeps those
before the approval on Phase77.

**Midpoint (after S03's candidate, before S06 opens).** The midpoint passes
when all of these hold:

- S00 has recorded its remaining offline cells (the parameter limit, the
  setting lock and read-back, `Table.nbytes`) on top of the probe's pin,
  hashes and defaults, and S01 is bound;
- S02 and S03 pass their focused checks;
- PostgreSQL/MySQL goldens are unchanged and the firewall is green on the
  integration tree;
- spend projects within the ceiling and leaves the replay reserve intact;
- the replay count and the CI health of the newest head are recorded;
- new helpers and owners are listed for the acquisition reserve;
- the sheet Q2 option-C check of PL.04 is done.

**Unfreeze conditions.** Each of these needs the owner:

- a form beyond D79.01;
- a new PIE code, or a changed text outside S01's rows;
- any change to PostgreSQL/MySQL bytes or contracts;
- a compiled-record or `VERSIONS` change;
- a public value beyond `DuckDBArrowInput`, or a change to the meaning of
  `ExecutionLimits`;
- a runtime sqlglot dependency;
- a package or metadata fetch other than the completed probe fetch of PL.05
  (PK resolves offline from the probe's uv cache), a duckdb release other
  than `2.0.0`, or a platform beyond PL.05;
- any Docker use;
- an extension-repository push;
- a ledger change.

**Stops.** The lead stops at:

- any cap;
- unproved package or input identity;
- a hardening item that cannot be proven on the pin; the route is then
  refused and reported;
- a trust regression;
- a failed native cell, which is first a question about its judge;
- a needed change of product law;
- a Phase77 change that a replay cannot carry without changing meaning.

Failed candidates, probes and runs stay in the ledger.

## Risks

1. **Moving base.** Phase77 S09 plans to change the portable schema and reader
   that S02 also edits. S21–S23 change the readers that S04 wires. S26 closes
   packaging. The third whole-tree test pass falls before the end of Phase78.
   Each of these forces replays, and every replay can add a binary family
   default. Mitigations: the D800 reserve, replays only at Phase77
   published-batch boundaries, the firewall on the integration tree, and the
   option-C check.
2. **Trust.** Extension auto-loading can reach the network, replacement scans
   can read caller frames, and the engine can spill to disk; the probe found
   each of these on by default on `2.0.0`. Any of them may be impossible to
   switch off provably on the pin. Mitigations: S00 proves that each D79.06
   value can be set and locked, S06 reads each back, and the route is
   refused if one cannot be proven.
3. **Packaging hotspot.** `uv.lock`, the literal pin readers, the installed
   matrix, Phase77 S26 and the VR2 rule paths all meet in S05 and S07.
   Mitigations: PK is one serial lane, the lock is regenerated, every reader
   changes in the same commit, and S07 gets a depth-one validation.

## External reference — DuckDB (probe of 2026-11-10; the rest pending S00)

| # | Item | Record |
| ---: | --- | --- |
| 1 | Snapshot/date | PyPI JSON at 2026-11-10T11:32:46Z: `duckdb` `2.0.0`, wheel sha256 `ab51ec57d329d6f3df37c0287b55d71c3fc07bb54b61d1afed09104f953b1431`; installed and exercised on CPython 3.13.13 only. The raw probe outputs are owner-held working records outside Git. Upstream documentation pages were not re-read. |
| 2 | Problem/constraints | An in-process engine reading one registered Arrow table, with no network, no files and no extension, bounded resources and a pinned identity. |
| 3 | Semantic/identity model | DuckDB's own types, NULL, ordering and floating-point rules, and a registration name. Observed on `2.0.0`: replacement scans resolve a name from a local of the frame that calls `con.sql` (not of an outer frame), and `SET python_enable_replacements = false` stops them. Pietto's laws stay the authority; a difference becomes a refusal. |
| 4 | Layering/dependency direction | A provider behind the execution route. Pietto emits every statement; DuckDB never decides Pietto meaning. |
| 5 | Algorithms/data structures/complexity | Observed defaults on `2.0.0`: `threads` and `memory_limit` follow the host (32 and 24.9 GiB here), `temp_directory` is the relative `.tmp`, and `max_temp_directory_size` is 90% of available disk. Pietto fixes each value (D79.06). |
| 6 | Interface/version/capability model | `:memory:` connection, Arrow registration (`register`, `from_arrow`), parameterized execution, settings and their lock. Arrow fetch at the pin is `to_arrow_table()`, which drops non-null flags; `fetch_arrow_table()` is deprecated and `.arrow()` returns a `RecordBatchReader`. The parameter limit and the lock behaviour are pending S00. No LTS status is claimed. |
| 7 | Testing/operational lifecycle | No server. Close and interrupt semantics are verified on the pin. |
| 8 | Pitfalls/migration costs | Automatic extension install and load; caller-frame scans; spilling; default resource settings. Each pin change re-qualifies the route and changes `target.release`. |
| 9 | Disposition | Adopt as an optional, pinned, hardened provider for B1 only. |
| 10 | WHAT_NOT_TO_COPY | DuckDB defaults, SQL extensions, implicit casts and coercions, source auto-discovery, and error texts as Pietto diagnostics. |
| 11 | Pietto owner affected | `execution/_duckdb.py`, the DuckDB adapter, PK, the support matrix. |

## Usability row — `duckdb.arrow("key")`

| Spelling | Canonical form | Works with | Errors | Discoverability |
| --- | --- | --- | --- | --- |
| `source orders: Order = duckdb.arrow("orders")` in an explicit-module module | As written; `pietto fmt` keeps it byte-identical (S02 witness) | `check --project`, `emit-sql --project --dialect duckdb`, `compile_sql`, `compile_query`, and `execute(route="duckdb_arrow", access=DuckDBArrowInput(name="orders", table=t), premise=None)` | An argument other than one non-empty string literal: PIE-S2306. In a single file: today's PIE-S2306, unchanged. Another dialect: PIE-B1001. An unsupported shape: PIE-B1003 with a detail and a hint. An input mismatch: PIE-R1002 `DUCKDB_ARROW_SCHEMA`. S01 names the exact details. | `language.md` source connectors, the spec, the capability subsection, the release notes |

## Deferrals

| Item | Owner | Latest point |
| --- | --- | --- |
| Whether `0.2.0` needs B2 | The owner | The B1 audit (S08), before any `0.2.0` request |
| NUL in `Text` input: refused until decided, as PIE-R1006 does for bound values | The owner | Before the B1 batch Gate 2 |
| Wiring the result reader | S04 | After Phase77 S23 is integrated, before S06 |
| Extension sync for `duckdb.arrow` (D76.12) | The lead rules at S02; a push needs a separate extension authorization | Before the B1 batch push |
| Whether SQLite B2 reuses a generalized firewall or builds its own pipeline | The Phase78 B2 Gate 1 | Before any B2 code |
| sqlglot as a test oracle (IMPLEMENTATION_FREEDOM under AD78.01) | The first Phase79 slice beyond projection and filter | Its Gate 1 |
| Other Phase79 work: multi-source, JOIN, aggregation, windows, ORDER BY and LIMIT, more parameters, `Decimal`, temporal, `UUID` and nested types, bundles, saved, relay and job routes, an install workflow, engine cancellation beyond B1 | Later Phase79 Gate 1s | The Phase82 freeze lists each one no Gate 1 takes as unsupported |
| Platforms other than PL.05 | Phase81 | Its Gate 1 |
| Reminder 8 (JOIN facts, forged compiled `median`) | Satisfied by exclusion: B1 has no JOIN and no new consumer of compiled admission, since bundles are refused | The first Phase79 slice that admits either |
| Stating AD79.01 to the owner (inform) | The lead; stated on 2026-11-11 (D79.12) | Before S04 seals |
| Stating the D79.01 refusal-code mapping and the D79.04 `-0.0` admission to the owner (inform) | The lead; stated on 2026-11-11, and both stand (D79.12) | Before S01 binds |

## Initiation-gate checklist

| # | Field | Phase79 B1 answer |
| ---: | --- | --- |
| 1 | Live authority | Gate 0 is bound to the published D77.04 head `ab972f36` and its natural CI `42831340276` (PL.02). The drafting tree is not authority. The previous-audit item is NOT_APPLICABLE (reason above; owner Phase77 S27; PL.01). |
| 2 | User/product outcome | One bounded local Arrow-table query (D79.01). It excludes every listed non-outcome and does not by itself meet the `0.2.0` gate. |
| 3 | Semantic reference model | The existing typed relation, NULL, finite `Float` value, bag, order, parameter, result and diagnostic laws, with a target-neutral `ProjectSQLPlan`. No DuckDB law is added. |
| 4 | Identity model | Identities kept apart: the source declaration occurrence (canonical); the connector key, which equals `relation.name` and the input name (D76.06) and is never an alias; field ordinal and order; target family and release; parameter occurrence (76-2); the capture of each attempt; the attempt itself. Forbidden: a winner picked among same-spelling sources or columns, Arrow labels used as occurrence identity, provenance inferred from the route, case folding. |
| 5 | Construction states | PLANNED, IMPLEMENTED, QUALIFIED, GATE2 and PUBLISHED stay distinct. An emission document is VERIFIED or BLOCKED; a live query comes only from VERIFIED. A capture is admitted or refused before any session. |
| 6 | Proof posture | Asserted: the drafts. Observed: the 2026-11-10 probe's metadata, hashes, CPython 3.13.13 install, defaults and Arrow round trip; later the S00 cells and the S06 cells. Verified: setting read-back, schema and capture checks, the adapter verifier. Derived: emission from the plan. Unknown: the parameter limit, the setting lock and read-back, `Table.nbytes` and the CPython 3.12 install, which S00 and PK close before the claims that need them. Disproven: a hardening item that fails, which refuses the route. |
| 7 | Layer ownership | Semantic and IR own the connector. `ProjectSQLPlan` owns the target assessment. The adapter owns lowering, rendering and verification. `_duckdb.py` owns driver identity, capture, session and attempt. The result owner owns output checks and the storage kind. PK owns the extra. |
| 8 | Dependency direction | Compiler, then adapter, then private execution, then result binding. `_duckdb.py` depends only downward: it never reads source syntax, reselects a target, infers a schema or feeds driver observations back. The PostgreSQL/MySQL modules never import the adapter. |
| 9 | Versioning and migration | The spec is alpha until the Phase82 freeze. The contract gains a family. After a pin upgrade an old contract is BLOCKED with PIE-B1003. No compiled record or `VERSIONS` change, and no bundle or saved-result migration. S08 adds the freeze-ledger rows. |
| 10 | Target requirements versus provider capabilities | The contract demands the source and the exact target. Installed-driver evidence shows only route availability. The capability page stays a hand-kept snapshot (D75.08). |
| 11 | Interchange | Inbound: a bounded owned Arrow snapshot. Outbound: `ResultBatch`, and the emission JSON for the CLI and API. No SQL, URI, setting or configuration crosses. |
| 12 | Execution | Explicit `execute(route="duckdb_arrow")`, owned by execution: one in-memory, read-only session per attempt, running compiler SQL only. |
| 13 | Resource lifecycle | The copy is made before `execute()` returns. The session opens at the first handle entry. Close and unregistration run on success, early close, cancellation, deadline, result failure and setup failure. The caller owns the table and the batches. |
| 14 | Security and trust | Package identity and origin; validated table shape, caps, UTF-8 and finite floats; key and target; D79.06. No network, file, socket, extension, credential or ambient configuration. The PL.05 fetches are outside the product runtime. No new digest. |
| 15 | Algorithms and data structures | One schema comparison, one bounded copy, one registration and one statement. No planner, registry, generic adapter or discovery. |
| 16 | Complexity posture | Validation is O(columns); the copy is O(rows × columns) under the caps. `threads` and `memory_limit` are explicit. There is no physical or peak-memory guarantee. |
| 17 | Invalidation | Each compile rereads the source, contract and code. Each execution captures afresh. A pin change invalidates every DuckDB contract through its target. |
| 18 | Cache | None: no session reuse, registry or memo. |
| 19 | Concurrency | One handle per thread. Attempts share nothing. Engine threads are fixed by `threads`. Results are a bag. |
| 20 | Diagnostics | S01 freezes the order. Every request check runs before any import, and capture runs before the session. Codes: PIE-B1003 details, PIE-S2306, PIE-B1001, PIE-R1003, PIE-R1004, PIE-R1002 details; failures follow AD79.01; the PIE-R1001 text changes. Existing diagnostics stay byte-identical. |
| 21 | Inspection | `check`, `compile` and `explain` stay non-executing. No DuckDB catalog inspection. |
| 22 | UX | The usability row above. One canonical spelling. Single files are unchanged, and unsupported shapes get hints. |
| 23 | Conformance | The new spec, the project CLI JSON v2 dialect value, the contract values in `project-package.md`, `diagnostics.md` and `execution.md`. One DuckDB native matrix; PostgreSQL/MySQL goldens are checked independently. |
| 24 | Differential and fuzz assurance | A Pietto oracle written before the run, bag comparison, an input-row permutation that must give the same bag, and repeated runs that must agree. No fuzzing, reducer or sqlglot in B1; Phase81 owns high-intensity work. |
| 25 | Packaging | The optional `execute-duckdb` only. Core dependencies are unchanged (tested). Imports are lazy. No grammar or generated change. The lock is regenerated, and installed cells come from package smoke. |
| 26 | Support matrix | CPython 3.12 and 3.13 on Linux x86-64 (glibc ≥ 2.28) with duckdb 2.0.0 and PyArrow 26.0.1 (PL.05, D79.02). Other platforms are unqualified (Phase81). DuckDB works in project mode only. |
| 27 | Release, deprecation and EOL | No Phase79 code, test, golden, extra, lock change or release-note fragment reaches `main` before the `0.1.11` cut; route and decision records (documentation only, with no code and no release-note fragment) may reach it earlier, in a Phase77 batch under D77.06 or a documentation batch under D77.14 (PL.04). B1 counts toward `0.2.0`, whose gate and release are approved separately. Nothing is deprecated. A failed head is kept and repaired by a child. |
| 28 | Readiness and exact deferred owners | Ready: Gate 0 is bound to `ab972f36`; S00's remaining cells come before S01. Every deferral is in the table above with its owner and latest point. |
| 29 | Slice route | S00–S08 as above, with their write sets, checks, dependencies and non-goals. |
| 30 | Repair and stop conditions | `C120/F360/D4100/S4` plus half of PK (D79.08, D79.09), the midpoint, the unfreeze conditions and the stops above. Each publication is authorized on its own, and failures are preserved. |
