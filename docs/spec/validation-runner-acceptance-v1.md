# Validation Runner Acceptance v1

It takes effect once the parallelism interlude closure publication passes
natural CI. Until an acceptance tool and a qualified environment record exist
for another runner, only the integration host qualifies.

## Scope

This version publishes the premise-based core of the validation runner rules
approved for the parallelism interlude: R1, R4, R10 and R12, numbered as in the
interlude dispatch. The dispatch's other numbers (R2, R3, R5–R9 and R11) are
not rules of this version; they stay reserved for a later dispatch that
provides an acceptance tool. These numbers follow the interlude dispatch only;
they are unrelated to the Phase68 recovery modes R1 and R2, including the R2
window refinement, and to CI remaining-tail maintenance R1. When this version
is published, no acceptance tool and no qualified environment record exist for
any runner other than the integration host.

This version adds no acceptance tool, report or environment-record format,
runner script, job template or qualification run. It changes no validator, CI
workflow, coverage or health schema, worker ceiling, product source, package
input or version, and it moves no domain away from the integration host.
Validation keeps the layered policy of
[Workflow Lifecycle Reader And Validation Efficiency v1](workflow-lifecycle-reader-validation-efficiency-v1.md)
and the current rules in [Development](../development.md).

## Terms

- **Integration host**: the one machine that holds the canonical worktree,
  seals Gate 2 candidates and publishes them. It is a role, not a place.
- **Runner**: any environment that executes validation work, such as the
  integration host, a compute node allocated by a batch scheduler, a hosted CI
  runner or any other. Each kind is a **runner category**.
- **Gate 2 validation**: the final validation that a Gate 2 seal relies on:
  the authoritative validation and the auxiliary audits, native campaigns and
  installed consumers that the candidate requires. Dirty-stage focused checks
  and reviews are not part of it.
- **Domain**: a part of a Gate 2 validation with its own premises (R4 rows
  1–8).
- **Premise**: a checkable property of a runner and its environment. R4 rows 0
  and 0b are the **Gate 2 premises**; rows 1–8 are **domain premises**.
- **Environment record**: the facts of one runner environment that the
  premises are judged against. This version defines no record format; the
  integration host is judged by the observed facts of its accepted core and
  host, while another runner's record counts only after an acceptance tool on
  the integration host has accepted it. The premises stay the same; only the
  evidence path differs.
- **Acceptance tool**: a checker that the integration host runs to decide
  whether another runner's environment record and reports count toward a
  Gate 2 validation. This version provides none.
- **Qualified environment record**: an environment record that an acceptance
  tool has accepted for named domains.
- **Provenance**: the producer of a report. [Development](../development.md)
  already calls the reports of the integration host's local consumer entry
  `LOCAL` provenance; this specification uses `LOCAL` for every report that
  the integration host produces.
- **Accepted core**: the integration host's canonical `.venv`, protected as
  Development requires (no environment rebuild, and command-scoped
  `UV_PYTHON=3.13.13 UV_NO_SYNC=1 UV_LOCKED=1`). A disposable environment that
  another runner builds for one job is not the accepted core. Building it is
  never a rebuild of the accepted core, and it does not breach Development's
  no-rebuild rule when that runner's environment record binds its identity
  (uv version, interpreter build, `uv.lock`, offline cache manifest) and the
  job's preflight checks that identity. This version defines neither the
  record format nor the preflight.

## R1 Premises, not places

- Every runner category, the integration host included, is judged by the same
  premises.
- A runner executes a domain as part of a Gate 2 validation only when its
  environment record satisfies that domain's premises. Where a domain runs
  follows from qualification. A non-authoritative run, such as a development
  loop, never counts toward or stands in for any part of a Gate 2 validation;
  on another runner R10 still applies to it.
- No host name, site name or local/remote distinction is a permission or
  exclusion condition. Provenance is a record field, not a permission
  condition, and the status columns of R4 are dated facts, not rules.
- Under these premises hosted CI currently executes no part of a Gate 2
  validation. Gate 2 validates the candidate tree before it is sealed and
  committed, while hosted CI runs only on commits already pushed (to `main` or
  in a pull request); running it on a candidate earlier would publish the
  candidate and trigger external CI, which needs explicit authorization. Its
  interpreter patches also differ from the one the integration host's report
  checker runs (row 0b). Hosted CI keeps its Gate 3 role as natural exact-head
  CI.
- Qualification is not a support claim.

## R4 Domains and premises

A runner must satisfy rows 0 and 0b before any domain row lets it execute part
of a Gate 2 validation. The three status columns record facts as of 2026-10-10;
they are not rules. The compute-node observations come from the preflight and
the reports of non-authoritative jobs that ran a published head on 2026-10-10,
unless a cell gives another date. A dash means that the row does not apply
because rows 0 and 0b are not satisfied.

| Row | Domain or premise | Premise | Integration host (WSL2 laptop) | Allocated compute node (SciNet Teach cluster) | Hosted CI runner |
| --- | --- | --- | --- | --- | --- |
| 0 | Gate 2 candidate reach | Runs the exact candidate tree before the seal, without publishing it or triggering external CI, and returns every result with its digest to the integration host | Satisfied | Not established: no acceptance tool exists; development-loop candidate runs are non-authoritative | Not satisfied: runs only on pushed commits |
| 0b | Same interpreter patch | Runs the same interpreter patch as the integration host's report checker; report contexts are compared by strict equality, full `python_version` included | Satisfied: CPython 3.13.13 | Satisfied: CPython 3.13.13 in the preflight and the report contexts | Not satisfied: CPython 3.12.14 and 3.13.15 |
| 1 | Static gates | Locked environment, CPython 3.13.13, Node availability recorded (Pyright needs it), the same candidate tree | Satisfied | Not verified; not planned | — |
| 2 | General pytest | CPython 3.13.13 with CPython 3.12.13 on `PATH` (domain `[[3,12],[3,13]]`), Java 21, complete Git history, basetemp and acquisition roots on runner-local storage, a worker plan within the runner's resource limit (a job's allocation, or the validator worker count approved for the integration host) | Satisfied | Not qualified: no acceptance tool or qualified environment record; the preflight found CPython 3.12.13 on `PATH`, Java 21 and complete Git history | — |
| 3 | Storage positives | Linux, the exact qualified SQLite build, ext4 mounted read-write without `nobarrier` or `barrier=0` | Satisfied | Not satisfied: the jobs' temporary root is tmpfs, so their storage positives were counted as `PIETTO_NOT_RUN` skips | — |
| 4 | Docker and native campaigns | `/var/run/docker.sock`, linux/amd64, pinned images, qualified storage | Satisfied | Not satisfied: needs row 3 | — |
| 5 | Generated audit | Java 21, `tools/antlr-4.13.2-complete.jar` matching its recorded SHA-256, the generator input closure | Satisfied | Not verified; not planned | — |
| 6 | Golden audit | Locked environment, the compiler and fixture input closure | Satisfied | Not verified; not planned | — |
| 7 | Package, Arrow and installed consumers | The build backend and the locked dependency wheels, pyarrow 25.0.1 included, from the package index or, on a runner without network, from an offline cache or wheelhouse | Satisfied | Not planned | — |
| 8 | Steps that need GitHub credentials or network | Authorized GitHub credentials and network access | Satisfied | Not satisfied: holds no credentials (R10); compute nodes have no network (observed 2026-10-09T03:29Z) | — |

The observed storage profile decides row 3; a declared storage environment
class never satisfies it. The authoritative validator declares the `qualified`
class for its pytest gate and, before its first gate, checks row 3 with that
gate's interpreter on pytest's temporary root. A runner that fails the check
is refused with exit 2 before any gate runs, which is not a validation start.
In any other run a storage positive that row 3 prevents is the asserted
refusal under `hosted-refusal` (the hosted CI default), a counted
`PIETTO_NOT_RUN storage-positive <category>` skip under `report` (the default
elsewhere) or a `PIETTO_STORAGE_REQUIRED <category>` failure under
`qualified`, and hosted `verify` refuses any `PIETTO_NOT_RUN` skip. An early
return or a skip is never a positive witness
([CI workload governance](../architecture/ci-workload-governance-v1.md));
[Development](../development.md#phase68-s11-job-store-validation) owns the
classes and their declaration, and its
[validation tiers](../development.md#validation-tiers) own the validator's
storage pre-check.

Within a Gate 2 validation, native campaigns and installed consumers (rows 4
and 7) are produced and adopted only where their premises hold; as of
2026-10-10 that is only the integration host, and their reports are `LOCAL`
provenance. This specification does not define how such results from any
other runner would be accepted; that needs separate authority. Natural CI
keeps running its own hosted consumers.

## R10 Credentials and trust

Here an *other runner* is any runner other than the integration host that
executes validation work outside natural CI, authoritative or not; hosted CI
runners executing natural CI keep the permissions their workflow declares.

- Validation jobs on other runners are explicit external execution under the
  active dispatch.
- No other runner holds a GitHub write credential or a model-service token
  anywhere, and its work directories and job environments hold no SSH private
  key. Every job environment on another runner is built from an allow-list
  that names no credential or token variable. A key that a site generates for
  its own internal SSH is reported by name only, and the repository owner
  decides what happens to it.
- Other runners never push and never write the canonical worktree.
- Their reports are never uploaded as CI artifacts, never enter health
  history, never use a numeric run id and never stand in for natural CI. The
  existing history filter already excludes them: trusted history reads only
  this repository's push/main, completed-success, attempt-1 runs (see
  [CI workload governance](../architecture/ci-workload-governance-v1.md)).

## R12 Effect and precedence

- This specification takes effect once natural exact-head CI passes on the
  pushed head that publishes the parallelism interlude closure: the closure
  commit itself or, when the closure is pushed inside a batch of commits, the
  batch head. Until then it grants nothing: each session follows the
  `AGENTS.md` it loads and the current validation rules, under which the
  authoritative validation runs on the integration host, and the interlude
  seals its own publications under those rules.
- Only the closure publication writes the clauses that apply this
  specification into [`AGENTS.md`](../../AGENTS.md), the current sections of
  [Development](../development.md),
  [CI workload governance](../architecture/ci-workload-governance-v1.md) and
  the [workflow lifecycle policy](workflow-lifecycle-reader-validation-efficiency-v1.md).
- No candidate whose Gate 2 validation starts before this specification takes
  effect selects runners under it; the earliest candidate that may is the
  Phase69 route-lock commit.
- Until an acceptance tool and a qualified environment record exist for
  another runner, only the integration host qualifies. Providing both needs a
  later dispatch, which also decides the reserved rules.
- Apart from replacing places with premises (R1), this specification relaxes
  no validation rule. The authoritative validation still runs exactly once per
  candidate, and independent full collection, complete coverage, auxiliary
  audits selected by their input closure, protection of the accepted core and
  natural CI as the final Python 3.12 and 3.13 owner are unchanged.
