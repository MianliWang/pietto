# Roadmap

Pietto is a readable, typed, modular SQL authoring compiler. Future work must
be selected by current user/product need, not by an inherited phase number.
Every substantive slice begins by identifying its authority roots, current
invariants, compatibility boundary, and the smallest behavior that is actually
needed.

This roadmap holds only what lies ahead: the phase owners, the decisions that
shape later phases, the open follow-ups and the inputs of the Phase82 freeze.
What is published, at which commit and with which natural CI, is in
[status](status.md). Each phase's route, completion audit and handoff are
under `docs/phases/`, the [release notes](release-notes.md) describe every
release, and Git history keeps the earlier text of this roadmap. The
[Phase77 completion audit](phases/phase-77/completion-audit.md) records its
delivered scope and next-phase handoff; Git and natural CI own its
publication. D77.01–D77.83 and AD77.01–AD77.03 remain in the
[decision record](decisions.md), and the open items that reach beyond
Phase77 are written into the sections below.

Durable cross-phase product and architecture laws enter through [product
architecture](architecture/product-architecture-v1.md), the [phase initiation
gate](architecture/phase-initiation-gate-v1.md), [identity and authority
laws](architecture/identity-and-authority-laws-v1.md), and [layering and
coupling laws](architecture/layering-and-coupling-laws-v1.md). This roadmap
owns phase-level future ownership and release milestones. Published phase
specs own exact phase and slice contracts, while [`docs/plan/`](https://github.com/MianliWang/pietto/blob/8e7c43f1852b2c26318b3217268a1f7416f44965/docs/plan/README.md)
is historical planning evidence rather than current authority.

The compiler core has no ambient database execution, credentials, remote
loading, registry, dependency solving, runtime evaluation or installation
discovery; execution is the separate, explicit, read-only plane that Phase68
introduced. Numerical operations require compiler-owned or qualified
physical evidence; caller-declared ranges alone do not prove arithmetic
safety. Future work must preserve established identity, complete
collection, provenance, ordering, trust, and diagnostic boundaries unless a
new explicit product decision changes them.

## Future Roadmap v6

These rows assign one phase-level owner to every retained subject. A row
authorizes no slice route or implementation; each phase's Gate 1 sets its
scope. The
[Phase 63 Slice 1 contract](spec/phase63-joined-query-block-product-architecture-source-audit-future-roadmap-route-lock-v1.md)
keeps the complete old-owner to new-owner ledger of the former Phase63–70
map.

| Phase | Owner |
| ---: | --- |
| 63 | Joined Query Block semantic completion and QUALIFY |
| 64 | Flat relational algebra: generic ON/refinement; CROSS/RIGHT/FULL/SEMI/ANTI; DISTINCT; UNION/INTERSECT/EXCEPT; private single-match request/proof/obligation |
| 65 | Target-neutral ProjectSQLPlan, parameters, source maps, legality and capability requirements |
| 66 | PostgreSQL/MySQL baseline multi-relation SQL and Project emit-SQL |
| 67 | Arrow interchange foundation and Pietto result contract |
| 68 | Explicit executor SPI, ADBC/DBAPI, streaming/cancellation/backpressure |
| 69 | Public alpha release engineering and unified safe entrypoints |
| 70 | Open/composite plans, nonrecursive CTE/subqueries, VALUES/table functions, outer captures, EXISTS/IN, LATERAL, bounded decorrelation, effect authority |
| 71 | NestedRelation, Collect, Unnest, flatten, outer/inner grain, nested Arrow |
| 72 | Advanced equality/types/nullability and temporal/range/ASOF relationships |
| 73 | Explicit two-level aggregation, conditional and list aggregates, per-group detail lists, nested GROUP/DISTINCT keys, project aggregate windows and parity, `median`/`quantile` and small scalar features |
| 74 | Cross-module reuse of `def` and relationships, relationship parameters that take table/query rows, MySQL catch-up, `variance`/`pvariance`/`pstdev`, group `all`/`any`, `first`/`last` and multi-column `count_distinct` |
| 75 | Formatter follow-ups, `pietto lsp` editor diagnostics with partial analysis, diagnostic hints, compile API, relation column view and header-line retirement |
| 76 | PostgreSQL deep adaptation: project SQL for more forms that `check --project` accepts, `%` of `Float` operands, `Decimal` times `Int`, computed `let` keys in single files, scalars over aggregates, and a caller CA for PostgreSQL connections |
| 77 | MySQL deep adaptation |
| 78 | SQLite deep adaptation |
| 79 | DuckDB deep adaptation, with the limited local analysis path that `0.2.0` requires |
| 80 | pandas/Polars/NumPy/SciPy/Matplotlib interoperability and the Python user surface |
| 81 | High-intensity real-DB/differential/metamorphic/fuzz/performance assurance, the diagnostic review, and the CPython, Windows and re-verification decisions |
| 82 | Public schemas/API/CLI/syntax/support-matrix freeze within `0.2.x`, ruling on the [freeze ledger](#phase82-freeze-ledger) |
| 83 | Release audit and publication after the freeze, of the then `0.2.x` release |
| 84 | Remote assets/registry/transport/signing/trust |
| 85 | Dependency solver/canonical lockfile/reproducible resolution |
| 86 | RDKit/geospatial/sparse/DLPack/device-framework adapters |
| 87 | Catalog/constraints/statistics/runtime-data-quality/chase |
| 88 | Logical optimizer memo and join-order/hypergraph search |
| 89 | Physical strategies including Yannakakis/WCOJ/Free Join/predicate transfer |
| 90 | Profiling-driven Rust kernels, PyO3/maturin, parity and wheel matrix |

Rows 88 and 89 stand in tension with `AGENTS.md`, which says Pietto is not a
query optimizer; their Gate 1 resolves it, by narrowing the row or by an
owner change of `AGENTS.md`, before any work starts. The editor line is a
work package of its own beside these phases (see below).

Phase77's implementation is complete under its
[completion audit](phases/phase-77/completion-audit.md), whose handoff
names Phase78 next. On 2026-11-10 the owner
approved the Gate 1 of Phase78 SQLite B1, Phase79 DuckDB B1, Phase80 and the
editor core work package E-C, which run beside Phase77 under the shared rows
PL.01–PL.06 of the
[decision record](decisions.md#phase7880-and-editor-core-gate-1--owner-decisions-2026-11-10):
see the [Phase78 route](phases/phase-78/route.md), the
[Phase79 route](phases/phase-79/route.md), the
[Phase80 route](phases/phase-80/route.md) and the
[E-C route](editor/ed03-route.md).

The owner's answers of 2026-11-07 settled the rules below, and on
2026-11-16 the owner changed their release numbers (PL.51); the
[decision record](decisions.md#roadmap-after-0110--owner-decisions-2026-11-07)
gives each with its source.

### Versions

`0.1.10` carries Phase73, Phase74 and Phase75. Pietto core `0.1.11` carries
Phase76 and the repairs ready at its cut, and Phase77's remaining slices
continue into `0.1.12` (PL.21) with two new slices, `now()` as an output
column (D77.42) and `now()` in `relay_live` and R2 (D77.43, D77.49); `0.1.11` was published on 2026-11-13
(PL.26), and `0.1.12` was published on 2026-11-14 (PL.29). Phase78–80 ship as
`0.2.0`, which was published on 2026-11-15 (PL.36, PL.37), and `0.2.1`,
which carries the leftovers of Phase80 and earlier with the MySQL `Float`
`same_value` in a JOIN `on` (PL.43), was published the same day (PL.45,
PL.46). `0.2.2` carries all the work before Phase81, the MySQL catch-up
included, and the owner has authorized its publication (PL.55, PL.56);
Phase81's commits reach `main` only after the `0.2.2` release commit
(PL.57).
The first tiers of SQLite B2 and DuckDB B2 and the interop relief enter
`0.2.2` (PL.47, PL.55), and so do DuckDB B2's second tier, JF's J1 and
the batches of E4B, the part of C04's E4 that MC.04 left to the owner's
plan, that are pushed before `0.2.2`'s final assembly starts; SQLite B2's
second tier publishes after `0.2.2` (PL.61, PL.64). Phase82
and Phase83 also use `0.2.x`, and no release is called `1.0`: every release
before Phase90 is a `0.2.x`, and Phase90, the Rust rewrite, releases as
`0.3.0` (PL.51). The extension follows its own version line.

`0.2.0` requires PostgreSQL and MySQL within the MySQL cadence below, one
local analysis path (the limited DuckDB path of Phase79, not a complete third
dialect) and the Phase80 interoperability with five libraries and its Python
surface. It does not require editor facts; the editor ships on its own
extension versions.

Until the Phase82 freeze a release may carry breaking changes: it lists them
at the top of its release notes with a pin to the previous exact version and
keeps recompiling, reading saved results and running again apart, and
bundles and saved jobs are not migrated before the Phase82 compatibility
decision (D76.13). The VS Code extension has versions of its own (see the
editor work package). Each release is approved on its own.

### After the Phase82 freeze

Phase82 freezes concrete semantics and compatibility rules: each public
contract states what a later `0.2.x` release may add and what stays, and an
addition that can break a working program or reader, such as a new reserved
name or a JSON field, counts as a compatibility change. After the freeze a
`0.2.x` release only adds compatibly, and a breaking change waits for
`0.3.0` (PL.51). Phases 84–90 and the tentative owners below work inside
those rules.

### MySQL cadence

MySQL support may trail PostgreSQL by about two to three phases (D76.10). New
features reach PostgreSQL first, which finds the problems, and MySQL catches
up in later batches; until then each MySQL path fails closed with a
deterministic diagnostic. Semantics and IR stay dialect-neutral, a form opens
on MySQL only after a passing two-database run (D74.09), and the capability
page and the release notes list what MySQL refuses. Project `sum(Int)`
(J12, D76.10) is an approved exception with the target Phase77, which
opened it only in the S01 and S03 forms. Its other forms stay refused, and
each release lists them under J12 (3) as not yet met, until the MySQL
catch-up work package MC opens them form by form, extending S01's guarded
SUM, each with its own two-database qualification (D77.76). MC also takes
C04's E4, MySQL `Float` `+`, `-`, `*` and sign on fields, opening a form
only where its finite results match and its overflow fails on both
databases (D77.78), and MySQL R2's first page that ends `FAILED` without a
public reason, which it measures on a real MySQL before it extends D77.80's
precheck (PL.40, D19). MC is the catch-up phase that those rows name, a
work package with no phase number (MC.01); it comes before Phase81 and
ships in `0.2.2`. Its Gate 1 is recorded (MC.01–MC.18) and MC is active:
all eight `sum(Int)` families G1–G8 (MC.02), E4's narrow cell with a
guarded `*` (MC.04, MC.05), D19 and PL.49's two items, on its own ledger
(MC.07); see the [MC route](mysql-catchup/route.md). The G1 and G2 slices
widen S02's [`sum(Int)` cell](language.md#aggregates-and-grouping), and
E4's slice opens its [narrow cell](language.md#mysql-float-arithmetic-cell);
E4's wider positions, a `let` carry, WHERE comparisons and ORDER BY keys,
stay refused under J12 (3) for the owner's later plan, before the Phase82
freeze (MC.04, PL.58).
`stddev` of an `Int` (J12, D76.10) is one with no target phase (D77.34), and
MySQL nested results (D71.05) one with the target of the separate later
nested work package (D77.32). The MySQL `UUID` header parameter stays
withdrawn, with no target (D77.79). Each release request lists the MySQL forms
beyond the cadence (D76.09).

### Editor work package

The editor line is its own work package beside Phases 76–80, tied to none of
them. The core semantic owner provides the facts and the extension consumes
them. [LSP diagnostics v1](spec/lsp-diagnostics-v1.md) describes the diagnostic
protocol of `pietto lsp`, and
[LSP editor facts v1](spec/lsp-editor-facts-v1.md) the hover, go-to-definition
and document symbols that ED.01 and ED.02 selected, from an ephemeral
in-process snapshot with the existing metadata formats unchanged; both are
alpha contracts. The editor core work package E-C added formatting,
workspace symbols, import-path links, completion and the hover and
definition facts that the analysis retains, all alpha, and closed on
2026-11-16; its
[completion audit](editor/ed03-completion-audit.md#handoff-to-the-next-editor-step)
hands off what the next editor steps take. Each remaining step needs its own
Gate 1. Still ahead are the
capability facts, which get a new versioned capability document whose own
Gate 1 records the weighing against the
[semantic metadata artifact v1](spec/semantic-metadata-artifact-v1.md) (ED.06),
in four layers (check, SQL emission, execution, result reading) and three
states (unsupported, unknown, not qualified), read alike by editors and AI
tools, with each backend filling its own profile.

The owner's VS Code extension (`MianliWang/pietto-vscode-extension`) takes
its diagnostics from `pietto lsp` and versions apart from Pietto, with a
minimum Pietto version that its own checks enforce: small changes ship as
patch versions, a minor version comes only with a user-visible editor
feature, and no Marketplace pre-release channel is used. Its current version
is in [status](status.md), and its Marketplace timing is the owner's. Each
Pietto phase that changes the grammar or the built-in
catalog carries the extension sync, made by the lead. The extension
repository's small fixes join the extension changes that Phase81 decides,
under one authorization (PL.40, D11).

### Third dialect

The owner selected AD78.01 on 2026-11-08: small Pietto-owned target adapters,
with sqlglot only as a test oracle, and the limited DuckDB path before SQLite.
The existing PostgreSQL/MySQL emitters retain their SQL-byte and semantic
authority; sqlglot is not a runtime dependency. Phase numbers stay unchanged.
On 2026-11-10 AD78.02 revised that schedule: Phase78 SQLite B1 is implemented
in parallel with Phase77 and Phase79 and publishes after Phase79 DuckDB B1,
and AD78.03 fixes the third-dialect seam the two share. On 2026-11-14 both
B1 batches were published together in one fast-forward push, ending at
`94b4097a`, which meets that order (PL.32). The
[Phase78 route](phases/phase-78/route.md) and the
[Phase79 route](phases/phase-79/route.md) bind each B1's supported forms,
pinned dependencies, error ownership and qualification; this architecture
decision does not open a dialect by itself. `0.2.0` carries DuckDB B1
only: the owner answered on 2026-11-14 that it needs no B2 (`group by` with
`count`, `sum`, `min` and `max`, then `order by` and `limit`), after the
owner's `0.2.0` request of that day (PL.31, PL.33). The
[Phase79 B1 audit](phases/phase-79/completion-audit.md#phase79-b2-handoff)
hands B2 over.

On 2026-11-15 the owner answered the Gate 1 sheets of both B2 parts
(PL.47). Each starts at its own Gate 0 on the head where `v0.2.1` is
published and the natural CI of its post-release documentation commit has
passed. SQLite B2, Phase78's project mode, is a separate SQLite project
adapter. Its first tier opens project mode with `having`, `count_distinct`
and `avg` of an `Int`, which single files also gain, and a project `sum` of
an `Int` only where the contract's `int_range` lies on one side of zero.
Project SQL writes `COLLATE BINARY` at each `Text` comparison, ordering,
grouping, deduplication and `min` or `max`,
in place of D78.02's premise, which single files keep, and one PostgreSQL
replay joins its in-process qualification. The tier also opens read-only
execution of a caller's SQLite file of `STRICT` tables on the one qualified
SQLite build, on Linux x86-64 with CPython 3.12.13 and 3.13.13: eleven
defences, at most 128 MiB, 1,048,576 rows per source table and a run's
default 20 seconds, and before each run a bounded check of the file's values
and integrity that refuses text holding NUL. SQLite B2 integrates after
batch 2, and
Phase78 closes with its closeout slice S16. DuckDB B2 is Phase79's second
slice, replayed onto batch 2's head and implemented in T01–T08, which enter
`0.2.2` (PL.55,
[B2 audit](phases/phase-79/b2-completion-audit.md)): grouped `count`, `sum`, `min` and
`max`, `having`, `order by` and `limit`, comparisons with literals, `and`,
`or` and `not`, and filters with several parameters, with capture limits of
1,048,576 rows and 256 MiB of the selected columns and a fixed
`memory_limit` of 1 GiB in place of D79.04's, and refusal texts rewritten
without "yet", in the version that the owner approved (PL.50). Both B2
parts write NULLS clauses that place NULL as PostgreSQL does. At their
midpoints the owner sent JOINs and the other forms of each second tier to
the owner's plan for the later phases (PL.54), where they come before
the Phase82 freeze, each with its own Gate 1, and Phase79's completion
audit waits for DuckDB's (PL.57, PL.58). DuckDB B2's first tier
is published, ending at `107df991` (PL.52); its midpoint was answered after
T06–T08 had run, since its dispatch had no stop there. SQLite B2's first tier
is complete: S06–S12 are published as one batch ending at `31859bc6`
(PL.59); R1, the tier's one PostgreSQL replay (PL.47), passed on
2026-11-17 once the host reached Docker Desktop's Engine; and its closeout
S16 closes Phase78 with its
[completion audit](phases/phase-78/completion-audit.md). R1 and S16
were published as one batch ending at `300f0a93` (PL.59), whose Gate 2
and natural CI the completion audit records.
SQLite B2 also makes single-file SQLite SQL write `Bool`
literals as `1` and `0`, a change to the bytes that `0.2.0` and `0.2.1`
publish, which its release lists as incompatible (PL.54).

### Interop relief

The interop relief (IR) is a work package with its own ledger that widens
D80.03's admission table (PL.47). Its slices are implemented (PL.53) and
enter `0.2.2` (PL.55);
[Field admission](interop.md#field-admission) gives the widened table. `UUID`
fields reach pandas and Polars as their 16 bytes, unchanged; `decimal256`
reaches pandas only, and Polars keeps refusing it with a fix that names
`to_pandas`; one level of nesting, a list of structs of admitted flat fields,
reaches pandas and Polars, which revises PL.39 for that level, while deeper
or other shapes stay refused; `to_numpy` takes a nullable `Float` with NaN at
each null, while a nullable `Int` or `Bool` stays refused; the plots take
nullable `Int` and `Float` fields, where a null breaks the line and draws no
point; and `to_scipy_csr` takes `Float` values, stored as float64 with
`-0.0` kept, beside its `Int` coordinates. Until that release, `0.2.1`'s
refusals stand, and the Windows claim still leaves out the extras (PL.40,
D5).

### Phase81 scope

Phase81 follows the new route of the owner's draft plan for the later
phases, which bundles several phases for parallel scheduling and which the
lead reviewed, in its next revision, r17, which the lead drafted and the
owner reviewed and dispatched on 2026-11-17; Phase81's Gate 0 may start,
and its implementation runs beside `0.2.2` (PL.54, PL.58, PL.65, PL.66).
On 2026-11-16 the owner answered the lead's
Phase81 Gate 1 sheet (PL.50), taking every recommendation except that the
release tools move into the repository, and later adopted every answer
again in that route (PL.58). In them CPython 3.14 gets full CI parity
(30 jobs) and joins the
verified profile. On Windows
x86-64 the CLI and `pietto.compiler` are declared supported with execution
NOTRUN, batch directory output gets a writer that holds the new directory's
handle, the extension repository's CI gains a native Windows job and, in
the same push, the extension's preview drops the `None:1:1` prefix of a
diagnostic without a path (PL.44 (c), PL.66), and the
classifiers name Linux and Windows. A verification result is reused only
inside one public call, and a stored or cross-process result is verified
again when loaded. The diagnostic review fixes texts, hints, positions, order
and severity within the existing codes. Nullability v2 gets a read-only
review first, reported to the owner at the midpoint. The assurance work uses
a bounded, seeded generator and shrinker with no new dependency and no
network. The release tools move into `scripts/`, where CI runs only their
dry run and self-tests. Phase81 keeps the sheet's ledger,
`C206/F618/D11,950/S14`, under PL.15, and PL.52's push authorization
applies to its batches once the `0.2.2` release commit is pushed, before
which no Phase81 commit is pushed (PL.57, PL.58).

Phase81 decides the CPython matrix (3.14 into CI and the verified profile;
until then 3.12 and 3.13, with no upper bound on `requires-python`), the
Windows scope and a re-verification policy that reuses a verification result
only for the same immutable input (version, configuration and identity),
with the trust evidence recorded. It holds the diagnostic review that was
planned for Phase82. Natural CI has run the platform-neutral tests on
Windows with Python 3.12 and 3.13 since the 2026-11-06 maintenance
(`e961ddb6`). Batch `emit-sql --project ROOT --all --output DIR` writes only
on supported Linux filesystems and is not supported on Windows or macOS, as
the README and the project guide state; those platforms use batch stdout, a
single `--output FILE`, or `pietto.compiler.compile_all_sql(...)` with their
own code writing the files. The Windows scope covers a path-based batch
directory writer, a claim of CLI and compile support with execution NOTRUN,
and a native Windows editor acceptance, and that claim leaves out the extras
(PL.40, D5); until then the package keeps its
`Operating System :: OS Independent` classifier. Nullability v2 goes to
Phase81 if it changes a public type contract, otherwise to `0.3.0`.

From the `0.2.1` lanes (PL.44), Phase81's diagnostic review also drops,
by Q7 (d) (a) of PL.50, the PIE-B1004 `identifier_case_declaration_missing`
that a statement refused during realization still reports when its only
`let` is an inline capturing one that reads another query, while the code
stays. It also takes the
MySQL one of the two comments on diagnostic texts from the external audit
of `0.2.0` (PL.40, D6); the DuckDB one goes to DuckDB B2 (PL.47). Two
items found while `0.2.1` was prepared, both as in `0.2.0`, join that
review and its documentation check: the PIE-S2333 entry of the
[diagnostics reference](spec/diagnostics.md) says that a relation's own
checks are reported once the error of a relation it reads is fixed, but an
order proof's PIE-S2104 and PIE-S2334 are reported before that; and a
null-safe JOIN `on` statement whose contract has no `identifier_case` or
another value is refused before its stages are built and reports that its
shape is not admitted, not that premise. Its editor work takes the rest of
the fault
tolerance of `pietto lsp` (an internal error outside the analysis of a
document or a root, such as
while the server answers a request or stores and publishes an analysis,
still ends the server, and a failed analysis leaves its old diagnostics on
the new text) and the overlap diagnostic for a project
root nested in another through a symbolic link.

Phase81 also takes four items that the owner decided on 2026-11-15 for
`let` names in aggregates and under GROUP BY (PL.48), in place of the
three questions about them that PL.44 left to its diagnostic review. Items
(1) and (4) are semantic extensions that both modes accept: (1) a `let`
name inside an aggregate's expression argument is read by its value, so
`sum`, `avg`, `count`, `count_distinct` and `string_agg` accept with a
`let` name, as in `sum(d + 1)` after `let d = qty`, the arguments that they
accept with a field, and other aggregates report what they report for the
field; and
(4) a `let` that only renames a field may be selected or projected in a
relation with GROUP BY, as `k` or `x = k` after `let k = qty` and
`group by k`. Item (3) is also a semantic extension: single files accept
`min` and `max` of a numeric `let`, which projects already accept. Item
(2) changes a diagnostic only: projects report the single-file PIE-S2314,
not the bare PIE-S2333, for `min` or `max` of a `Text` or `Bool` `let`,
and accept nothing more. Each extension takes a slice of its own with a
two-database verification, and none lands before the `0.2.2` release
commit (PL.57); until each lands,
`0.2.1`'s behavior and the [diagnostics reference](spec/diagnostics.md)
stand.

### Tests and maintenance

Batch 2 (M11–M16), one maintenance batch after the `v0.2.1` tag that
`v0.2.1` does not carry, completed the third whole-tree test pass and the
CI scheduler fix for module fixtures built in several shards (F3), under the
[CI workload governance](architecture/ci-workload-governance-v1.md)
(PL.40, D14; PL.49). The pass left three items to later owners (PL.49),
and two remain: the naming exception of
`tests/_pietto_mysql_native_prepared.py` waits until a line refreezes the
qualification packages that name it, the nested work package or a later
one, since MC refreezes none of them (MC.13); and the surviving mutants of
Phase77 S12's allowlisted guards in `src/pietto/_project` go with the
repeated MySQL cell derivation to the MySQL catch-up work package MC
(MC.01). The pure verifier fidelity repair (PL.20, D77.54) settled those
in the pure reader, as the
[Slice14 contract](spec/phase66-slice14-private-emission-observation-process-integration-v1.md#coverage)
records. Phase81 takes the import time of
`pietto.execution` (PL.40, D15). Each completion audit records the Gate 2
duration.

### Deferred subjects

Each subject has an owner and a latest decision point; none is scheduled
before its owner's Gate 1 takes it.

| Subject | Owner and latest point |
| --- | --- |
| Measure and metric definitions | unscheduled |
| Grouping extensions (ROLLUP, CUBE, GROUPING SETS) | the aggregation semantic owner, at a named use case (J8); Phase82 freeze input |
| Automatic fan-out repair or reaggregation; a public aggregate state | the joined-aggregation and aggregation semantic owners, at the first Gate 1 that admits one or at a consumer; Phase82 freeze input |
| PostgreSQL extension functions; the function/plugin SPI and user-written table functions | a Gate 1 with a named use case; Phase82 freeze input (D76.11) |
| A new built-in table function | the first Gate 1 that names a case; Phase82 freeze input (D74.12) |
| Database-native array and JSON columns; the `postgres_adbc` nested route | the Phase82 freeze, by its ledger row (D76.11, D80.06, PL.39) |
| MySQL nested output and `JSON_TABLE` | the separate nested work package, at its own Gate 1 (D71.05, D77.32) |
| pandas and Polars nesting; the Arrow data-analysis example; `compile_queries(...)`; `round` of a `Float` with digits | the owner's answer of 2026-11-15 to the lead's `0.2.1` plan, and for the example the lead's ruling under the owner's later instruction that day (J25, D75.03, D76.05, D80.06, PL.39): one level of nesting to the interop relief (PL.47, which revises PL.39 for that level), and other nesting to a Gate 1 after the nested work package that took Phase77 S24 (D77.32), which admits it before the Phase82 freeze or leaves it refused by the `pietto.interop` ledger row; `compile_queries(...)` after the forged-compiled trust decision below, at the latest the Phase82 freeze; `round` to its Phase82 freeze ledger row; and the example, whose inputs Phase79 B1 and Phase80 S02 deliver, is delivered by the `0.2.1` interop guidance in [An Arrow table through DuckDB](interop.md#an-arrow-table-through-duckdb) |
| Nested fuzz and high-intensity differential work; a readability and compile-time benchmark | Phase81 (J25) |
| The nested public format | the Phase82 freeze |
| Multi-level collections and the refused nested combinations; a capture let that reads another capture let | the NestedRelation semantic owner and the ProjectSQLPlan owner; the scope and capture semantic owner; each at its first admission Gate 1 |
| Nested `==`, ORDER BY and set-operation dedup, kept refused (D73.06) | the nested-value semantic owner, at the first Gate 1 that admits one |
| Child-level recovery, R2 and nested sink effects | a later execution and recovery owner, after a durable coordinate, effect and ACK contract |
| Decorrelation, automatic flatten, CSE and every other rewrite; the scalar-function effect catalog (D70.06) | Phase88; formal rewrite certification is the tentative Phase93 |
| Cube and dbt export | Phase84 |
| Wildcard imports, `constraint` and `derive` exports, qualified calls | the module owner, until a Gate 1 admits one (D74.12) |
| Conversions other than `Float(value)` and `Text(value)` of an `Int` | their later owner; unscheduled |
| The header rule and its tokens in the grammar | Phase76 retained them under the `migrate` and per-line PIE-P1000 byte-compatibility fallback; removal belongs to the Phase82 freeze (D76.12) |
| SQL-to-Pietto conversion | the tentative candidate 105 below |
| SQLite's second tier: JOINs, range-proved `Int` arithmetic and windows (S13–S15) | the owner's plan, before the Phase82 freeze, with its own Gate 1 and ledger; the cutoff for admitting it is Phase82's Gate 1 (PL.58 (4)); the decision on the freeze ledger's JOIN key and grain row comes before any slice that opens a JOIN (PL.54, PL.58; [Phase78 audit](phases/phase-78/completion-audit.md#handoff)) |
| SQLite run-time guarded and `Float` arithmetic, `/` and `%`; `Text` that holds NUL; SQLite bundles, saved results, relay, jobs and R2; other SQLite builds and platforms; the SQLite capability-facts profile | a later Gate 1 with a use case for the arithmetic; a later SQLite execution Gate 1 for NUL; the later execution and recovery owners; the Phase82 support matrix, where each is not qualified; the editor capability-facts Gate 1; each untaken one a Phase82 freeze input ([B2 deferred owners](phases/phase-78/route.md#b2-deferred-owners)) |
| The other MySQL project `sum(Int)` forms | the MySQL catch-up work package MC before Phase81, form by form with its own qualification (D77.76, MC.01, MC.02; see [MySQL cadence](#mysql-cadence) and the [MC route](mysql-catchup/route.md)) |
| E4's wider MySQL positions outside its narrow cell: a `let` carry, a WHERE comparison and an ORDER BY key of a `Float` `+`, `-`, `*` or sign on a field (C04 E4) | the owner's later plan, before the Phase82 freeze (D77.78, MC.04, PL.58) |
| Every other position of PostgreSQL's E4 on MySQL, such as `x + y`, a nested operation or a parameter operand | no target (MC.04, MC.10) |
| `verify_project_sql_plan` runs without a memo, 4 to 29 times per case | `_project/project_sql_plan_verification.py` and its emission callers, in Phase81 (PL.40, D15); a memo needs the owner ([Phase77 S26](phases/phase-77/route.md#s26-closure-record)) |

## Phase82 freeze ledger

Phase82 rules on each row; it does not collect them anew. From Phase76 on,
each completion audit adds the freeze inputs of its phase here.

| Subject | Ruling Phase82 makes | Recorded by |
| --- | --- | --- |
| `pietto.compiler` (the Python compile API) | freezes (owner, 2026-11-07) | D75.02 |
| `pietto.project-relation-columns.v1`, with the kinds `type_alias` and `unknown` and the `module` field of type objects | freezes (owner, 2026-11-07) | D75.01 (owner answer B1-1, 2026-11-07) |
| The `fmt` output, its layout items (the gaps between the tokens of a line, a head comment paragraph attached to the first declaration), a line width, options and a JSON output | the output freezes after its layout items | D75.05, D75.14 |
| `pietto lsp`, editor partial analysis and the five editor-only messages; whether `pietto.cli.main(argv)` is a documented entry point | only the diagnostic protocol freezes; the messages get a catalog without PIE codes; the entry point is decided | D75.09–D75.12, Phase76 handoff |
| The E-C alpha surfaces of `pietto lsp` (formatting of the open buffer, workspace symbols, import-path document links, completion from the static vocabulary and the open buffer's identifiers, and the hover and definition facts of LSP editor facts v1); the VS Code extension's use of `pietto.cli.main(argv)` to start the server | each surface freezes with its alpha contract or changes before the freeze; the entry point is decided with the `pietto lsp` row above | ED.03, ED.09, ED.11 |
| `pietto.sql.emit_postgres_sql` | stays public and enters the API inventory | owner, 2026-11-07 |
| `pietto.interop`: its five adapters (six functions), the D80.03 admission table as the interop relief widened it ([Field admission](interop.md#field-admission): a `UUID` as its 16 bytes in pandas and Polars, `decimal256` in pandas only, one level of nesting in both, a nullable `Float` in `to_numpy` and nullable `Int` and `Float` fields in the plots as NaN, and `Float` values in `to_scipy_csr`), with nested fields beyond its one level refused, the D80.04 exception order, and the five `interop-*` extras with their pins | the surface freezes with its alpha contract or changes before the freeze; a pin refresh re-checks whether Polars reads `decimal256`, and if Polars gains a UUID dtype, which the dtype comparison then refuses, its mapping goes to the owner; other pandas and Polars nesting is admitted by a Gate 1 before then or stays refused | D80.02–D80.06, D80.08, D80.09, AD80.01, PL.47, PL.53; [Phase80 audit](phases/phase-80/completion-audit.md) |
| The header rule and its tokens retained by Phase76 | removed under the migration/hint compatibility contract | D75.06, D76.12; [Phase76 audit](phases/phase-76/completion-audit.md) |
| The nested public format; grouping extensions, automatic fan-out repair and a public aggregate state | frozen, or kept unsupported | Phase71 route, Phase74 handoff |
| `def` and `relationship` items in PACKAGE_ROOT modules; a built-in table function | admitted, or kept refused | D74.07, D74.12 |
| PostgreSQL extension functions, the function/plugin SPI, user-written table functions, database-native array and JSON columns, the `postgres_adbc` nested route | the Phase82 support matrix lists each one no Gate 1 took as not supported | D76.11, D80.06, PL.51 |
| Project `matches(...)`; `Decimal` division and `avg`; `round` of a `Float` with digits | a contract, or a refusal that stays | D76.03, D76.05, D80.06 |
| The PostgreSQL TLS profile of `PostgresAccess.ca_file` | a support-matrix row | D76.07 |
| Single files and projects | `language.md` states the rule before the freeze: single files open project-only forms one at a time, DISTINCT first, with no promise that they stay a subset of projects | owner, 2026-11-07 |
| Bundles and saved jobs across versions; an upgrade-impact tool | the Phase82 compatibility and migration policy, and whether the tool comes before the freeze | D76.13, Phase76 reminder 7, PL.51 |
| Nullability v2 | Phase81 if it changes a public type contract, otherwise `0.3.0` | D73.13, owner, 2026-11-07, PL.50, PL.51 |
| The CPython matrix and the Windows claim | frozen as Phase81 decides them | owner, 2026-11-07 |
| The release notes' history before the freeze, which keeps its file layout until then | archived by the Phase82 freeze | PL.40 (D10), PL.51 |
| Compiled replay and live analysis give different JOIN key and grain facts for equal SQL bytes | decided (PL.61): live semantic analysis is the only authority, and adapters read the facts only from the verified plan; JF's J2 aligns the compiled replay with the same law before Phase82's Gate 1, and Phase82 audits the closed decision | Phase74 handoff, Phase76 reminder 8, PL.61, PL.62 |
| A forged compiled `median(id * 2)` loads with consistent SQL | a trust decision of the compiled and verifier owner, coordinated by the lead, before the first new consumer of compiled admission and at the latest before `compile_queries(...)` | Phase74 handoff, Phase76 reminder 8 |
| The VS Code extension's sync script imports the generated lexer and parser from `pietto.generated` and two functions from `pietto.indentation`, modules that no public contract names | whether the script must stop importing them, and which public entry point replaces them if so | PL.38, PL.44 |
| The fixed civil `Timestamp` meaning of a `now()` output; the statement time that R2 records and `recover` binds | each freezes with the result contract and the R2 workspace, or changes before the freeze | D77.42, D77.49; [Phase77 audit](phases/phase-77/completion-audit.md) |
| MySQL R2 refuses every form that `0.1.11` refused (`PUBLIC_R2_UNQUALIFIED_FORM`, by rule two) and every paired form (`PUBLIC_R2_PAIRED_FORM`) | a support-matrix row for R2 by target, or narrowed by forms that a native R2 qualification covers | D77.46, D77.67, D77.68 |
| MySQL forms that open only byte for byte as a paired form (Wave A) | the Phase82 support matrix states them as paired forms, or a structural rule replaces them | D77.36; [Phase77 audit](phases/phase-77/completion-audit.md) |
| SQLite SQL and the `sqlite_file` route: single-file `emit-sql FILE --dialect sqlite` with the successful CLI JSON v1 `dialect` value `"sqlite"`, the PIE-B1000 SQLite reasons, the declared premises and `Bool` literals written `1` or `0`; the `sqlite.table("name")` spelling with its PIE-S2306 texts; the project dialect `sqlite` with the contract target `{"family": "sqlite", "release": "3.53.1"}`, the `main` namespace, the scan `"relation_rows"` and the storage kinds, the compile refusals and their order with their details and suggestions, and the first tier's forms with their SQL spellings (`COLLATE BINARY`, the NULLS clauses, `AVG(CAST(x AS REAL))`, the one-sided `sum`); `compile_query(dialect="sqlite")` and `execute(route="sqlite_file")` with `SQLiteFileInput` and `premise=None`, its defences and its value and integrity check, the limits of 128 MiB, 1,048,576 rows per source table and `limits.seconds`, the side files of a WAL file's read, and its detail words, `SQLITE_ERRORCODE_<n>` and `SQLITE_INTEGER_OVERFLOW` among them | frozen, kept alpha, or kept unsupported; the Phase82 support matrix lists the qualified SQLite build on Linux x86-64 under CPython 3.13.13 and 3.12.13, and every other build and platform as not qualified | D78.01–D78.04, D78.12, PL.47, PL.54, PL.59; Phase78 B1 closeout; [Phase78 audit](phases/phase-78/completion-audit.md) |
| The DuckDB Arrow route: the `duckdb.arrow("key")` spelling with its PIE-S2306 texts, the project dialect `duckdb`, the contract target `{"family": "duckdb", "release": "2.0.0"}` with `scan` `"arrow_registration"`, the `arrow` namespace and the `arrow_*` storage kinds, the DuckDB compile refusals and their order with B2's details and suggestions, B2's forms (grouping with `count`, `sum`, `min` and `max`, `having`, `order by` with its NULLS clauses, the static `limit`, and predicates over literals and parameters of four types) and the second tier's (`Date`, `Timestamp` and `Decimal(p, s)` fields with `p` at most 38 and their `arrow_date32`, `arrow_timestamp_us` and `arrow_decimal128` storages, `Int` arithmetic by range proof and `Float` arithmetic with its overflow and underflow checks in the final projection, and `inner` and `left` equality JOINs, one source read twice included) with their SQL spellings and `physical_type` values, `execute(route="duckdb_arrow")` with a `DuckDBArrowInput` or a tuple of them and `premise=None`, the capture limits of 1,048,576 rows per input and 256 MiB of the selected columns over all inputs with their check order and the declared key check, the reading of every result in batches with its charge and `transaction`, the session settings with the 1 GiB `memory_limit` and the `default_collation` read-back, the detail words and the `execute-duckdb` extra | frozen, kept alpha, or kept unsupported; the Phase82 support matrix lists `duckdb` `2.0.0` with `pyarrow` `26.0.1` on the qualified platforms and every other release and platform as not qualified | D79.01–D79.15, D79.17–D79.30, AD79.01, PL.47, PL.50; [Phase79 B1 audit](phases/phase-79/completion-audit.md), [B2 audit](phases/phase-79/b2-completion-audit.md), [Phase79 completion audit](phases/phase-79/t2-completion-audit.md) |
| `RequestRejected` also carries the PIE-R2xxx refusals of the checks that `execute()` runs itself (`PIE-R2003` on `mysql_rows` and `postgres_adbc`, `PIE-R2001` and `PIE-R2002` of the loaded PyArrow on `duckdb_arrow`, `PIE-R2002` `SQLITE_BUILD` on `sqlite_file`), and the PIE-R1004 width refusal (`LIMIT`) covers only the PostgreSQL and MySQL routes | each freezes with the execution error classes, or changes before the freeze | D79.11; [Phase79 B1 audit](phases/phase-79/completion-audit.md) |

## Project-mode follow-up

The owner decided in October 2026 to document these project-mode limits first
and implement them later:

- Explain for explicit-module (`schema_version = 2`) projects. Phase75 added
  their relation columns (alpha; see
  [Listing relation columns](project-package.md#listing-relation-columns)).
  Source columns, `schema_version = 4` columns, canonical type names,
  `Decimal` precision and scale, and single-file relations with a JOIN, let,
  capture or Collect stay with this follow-up (D75.14). The Project Explain
  artifact still reads only `schema_version = 4` package-root projects and
  only parses their modules; see
  [Explaining a package-root project](project-package.md#explaining-a-package-root-project).
- Wider project SQL emission. Of the forms that `check --project` accepts
  but `emit-sql --project` refuses, listed in
  [Project SQL emission](project-package.md#project-sql-emission), Phase76
  takes those of D76.02 on PostgreSQL and the Phase77 Gate 1 takes MySQL,
  each form with reviewed SQL and a real-database run. The forms of D76.03
  stay refused, and MySQL FULL JOIN stays an approved non-support.

These ARCHITECTURE_DECISIONs have no phase yet; the first two are inputs of
the editor latency budget:

- Linear project analysis of layered JOIN DAGs. When each relation JOINs the
  relation before it and the one before that, a project's check time still
  grows exponentially with the layers, because the grain kept for each JOIN
  copies the grain factors of every path to its inputs (single files are not
  affected, and no SQL or diagnostic is wrong). Sharing those factors is an
  ARCHITECTURE_DECISION on the semantic identity of grain facts; the release
  notes list it under the project-mode known limitations.
- Sharing functional-dependency structure across JOIN steps (PMS-6). Every
  JOIN step still images every FD of its inputs, so the cost grows faster than
  the JOIN count; on 2026-11-04 the owner did not adopt the proposed sharing.
- The F5 and F7 residuals: project joined aggregation analysis beside a
  refused WHERE or `let:` binding, and the SELECT and ORDER BY diagnostics
  after a failing JOIN `where` or `let:`; the
  [0.1.8 release notes](release-notes.md#project-mode-quality-public-alpha-release-notes--018)
  list them. The other differences listed there, such as the order of some
  diagnostics, the severity of PIE-S2304 and ORDER BY keys after a SELECT
  error, have no scheduled home.

The other [known limitations of 0.1.7](release-notes.md#known-limitations)
have no scheduled home yet.

## Follow-up after the single-file JOIN demo

The post-0.1.4 stability repair kept two conservative refusal classes: D-11,
the documented sound outer-JOIN aggregate cases, and D-12, the documented
NULL-arithmetic cases that PostgreSQL or MySQL execute correctly. Phase72
restored the cases that its Gate 1 case list accepted (see the
[0.1.9 release notes](release-notes.md)); real fan-out and the cases that list
did not accept stay refused. The remaining relaxation stays with the Pietto
lead, with a full review before any further one. It is not permission to
restore incorrect SQL.

## Tentative later ownership

These separately numbered owners are `TENTATIVE / OWNER ONLY` and authorize no
implementation. Of 98–106 (owner, 2026-11-07), only 98 and 99 are open as
limited directions, for check and compile only and with no database
credentials; 95 (writes), 97 (streams) and 106 (a web UI) stay out unless
`AGENTS.md` changes.

| Tentative phase | Owner |
| ---: | --- |
| 91 | Persistent incremental-cache identity and incremental/differential Project IR |
| 92 | Recursive relations, fixpoints, iterative planning, and bounded recursive provenance |
| 93 | Formal rewrite certification |
| 94 | Cloud/federation semantics, planning, and transport |
| 95 | DML, DDL, and migrations |
| 96 | Governance and security policy semantics |
| 97 | Continuous/streaming query semantics distinct from finite-result streaming |
| 98 | MCP compile and context (check and compile only) |
| 99 | Official user skills (check and compile only) |
| 100 | Controlled AI actions |
| 101 | Metrics and analysis models |
| 102 | Nested extensions |
| 103 | Remaining function and semantic gaps |
| 104 | User model tests and drift |
| 105 | Bounded SQL-to-Pietto import of existing SQL (the owner's wish) |
| 106 | Result browsing and multi-host presentation |

Compiler acceptance, private capability facts, backend support, database
installation, public exposure, local graph behavior, remote I/O, solving, and
release operations remain separate authorities. No phase or roadmap row
implicitly grants a tag, release, package publication, signing, or attestation.

Use the current source, tests, retained normative contracts, Git state, and
natural CI as authority. Git history contains completed planning and delivery
history; it is not duplicated as a second current roadmap.
