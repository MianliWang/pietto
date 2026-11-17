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
| 88 | Compile-time logical optimizer: memo, join-order/hypergraph search and equivalence rewrites over a closed rule set; automatic flatten |
| 89 | SQL-expressible physical strategies for the Phase88 optimizer: Yannakakis semi-join reduction and exact predicate transfer; WCOJ and Free Join need an execution engine and stay out |
| 90 | Profiling-driven Rust kernels, PyO3/maturin, parity and wheel matrix |

On 2026-11-26 the owner changed `AGENTS.md`: Pietto has a compile-time
optimizer and never a runtime one, so rows 88 and 89 work inside that
boundary (PL.102, PL.105). The editor line is a work package of its own
beside these phases (see below).

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
PL.46). `0.2.2`, which carries all the work before Phase81, the MySQL
catch-up included (PL.55), was published on 2026-11-27 (PL.96, PL.97).
Phase81's commits reach `main` only after the `0.2.2` release commit
(PL.57).
The first tiers of SQLite B2 and DuckDB B2 and the interop relief are in
`0.2.2` (PL.47, PL.55), and so are DuckDB B2's second tier and JF's
J1, and E4B, the part of C04's E4 that MC.04 left to the owner's plan,
whose lists had all qualified when `0.2.2`'s final assembly started (PL.85
(2)); SQLite B2's second tier publishes after `0.2.2` (PL.61, PL.64), and
`0.2.3` is released after Phase81's slice P16 closes and before the Phase82
freeze (PL.94, PL.98 (3)). The release ledger REL covers `0.2.3` and every
later `0.2.x` release before `0.3.0` but the freeze release (PL.98 (4)).
Phase82 and Phase83 also use `0.2.x`, and no release is called `1.0`:
every release before Phase90 is a `0.2.x`, and Phase90, the Rust rewrite,
releases as `0.3.0` (PL.51). The extension follows its own version line.

`0.2.0` requires PostgreSQL and MySQL within the MySQL cadence below, one
local analysis path (the limited DuckDB path of Phase79, not a complete third
dialect) and the Phase80 interoperability with five libraries and its Python
surface. It does not require editor facts; the editor ships on its own
extension versions.

Until the Phase82 freeze a release may carry breaking changes: it lists them
at the top of its release notes with a pin to the previous exact version and
keeps recompiling, reading saved results and running again apart, and
bundles and saved jobs, which stay bound to the exact installed code, are
not migrated (D76.13, PL.101 (1)). The VS Code extension has versions of
its own (see the editor work package). Each release is approved on its
own.

### After the Phase82 freeze

Phase82 freezes concrete semantics and compatibility rules: each public
contract states what a later `0.2.x` release may add and what stays, and an
addition that can break a working program or reader, such as a new reserved
name or a JSON field, counts as a compatibility change. After the freeze a
`0.2.x` release only adds compatibly, and a breaking change waits for
`0.3.0` (PL.51), except a correctness or fail-open repair, which its
release lists at the top of its notes, with each change of public SQL or a
carrier authorized item by item (PL.100 (iii)). Phase82 writes into
its compatibility policy the rules that the owner answered on 2026-11-26
(PL.100): an input may gain optional keys, while a new output member comes
only in a parallel schema version that a caller chooses; diagnostic codes
and locked orders freeze, while their texts may change; a reserved word or
built-in name is added only where no existing program fails; opening a
documented refusal, where every program that succeeded keeps its
diagnostics, SQL, JSON and results, and a new public name, where existing
names keep their behavior, are compatible additions; SQL bytes stay stable
except under such repairs and security repairs, and an optimizer's rewrite
comes only behind an explicitly enabled option; and a deprecation is
written in the documentation only. A target release accepted at the
freeze stays accepted within `0.2.x` (PL.101 (2)). As the lead reads the
owner's answer, which the owner may correct, `0.2.x` has no support window
after `0.3.0`, and no compatibility across versions is promised before
`1.0` (PL.100 (ix)). Phases 84–90 and the tentative owners below work
inside those rules.

### MySQL cadence

MySQL support may trail PostgreSQL by about two to three phases (D76.10). New
features reach PostgreSQL first, which finds the problems, and MySQL catches
up in later batches; until then each MySQL path fails closed with a
deterministic diagnostic. Semantics and IR stay dialect-neutral, a form opens
on MySQL only after a passing two-database run (D74.09), and the capability
page and the release notes list what MySQL refuses. Project `sum(Int)`
(J12, D76.10) is an approved exception: Phase77 opened it in the S01 and
S03 forms, and the MySQL catch-up work package MC, which closed with its
[completion audit](mysql-catchup/completion-audit.md), opened more of its
forms family by family, each only after its own two-database
qualification (D77.76, MC.03). Every MySQL project `sum(Int)` form that MC
did not open keeps the exception with no target, listed under J12 (3) in
each release, and the [Phase82 freeze ledger](#phase82-freeze-ledger)
rules on it (MC.10). E4B, the part of C04's E4 that MC.04 left to the
owner's plan (PL.58 (4), PL.75), opened E4's wider positions in
[E4B's cells](language.md#mysql-float-wider-cells), each chain after its
own raw and emitted campaigns (PL.78, PL.79). A MySQL `count` of a `Float`
`+`, `-` or `*`, and any E4B `count` under a WHERE, wait for one of two
fixes before the Phase82 freeze (PL.82); a `*` beside a header parameter
(PL.76), a `Float` operation in a JOIN `on` (PL.68) and every other
position of PostgreSQL's E4 keep their refusal with no target, listed
under J12 (3) (MC.10). MySQL R2's first page that ends `FAILED` without a
public reason stays as it is, since D19 did not extend D77.80's precheck
([MC completion audit](mysql-catchup/completion-audit.md#d19)): MC2, the
MySQL catch-up after the freeze, measures it again with D19's three
repairs and the corrected codes of MySQL's source refusals, and D19's
extension does not ship before then (PL.106). `stddev`
of an `Int` (J12, D76.10) is one with no target phase (D77.34), and MySQL
nested results (D71.05) one with the target of the separate later nested
work package (D77.32). The MySQL `UUID` header parameter stays withdrawn,
with no target (D77.79). Each release request lists the MySQL forms beyond
the cadence (D76.09).

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
audit waited for DuckDB's (PL.57, PL.58). DuckDB B2's first tier
is published, ending at `107df991` (PL.52); its midpoint was answered after
T06–T08 had run, since its dispatch had no stop there. DuckDB's second
tier is published, ending at `df8817d3`, and its
[completion audit](phases/phase-79/t2-completion-audit.md) closes Phase79
(D79.23). SQLite B2's first tier
is complete: S06–S12 are published as one batch ending at `31859bc6`
(PL.59); R1, the tier's one PostgreSQL replay (PL.47), passed on
2026-11-17 once the host reached Docker Desktop's Engine; and its closeout
S16 closes Phase78 with its
[completion audit](phases/phase-78/completion-audit.md). R1 and S16
were published as one batch ending at `300f0a93` (PL.59), whose Gate 2
and natural CI the completion audit records. SQLite B2's second tier
(D78.14), on its own ledger P78T2, is implemented and qualified in two
batches: S14's range-proved `Int` arithmetic, S15's windows over one source
read and the replay R2 in the first, and S13a's INNER and LEFT JOINs of
sources, S13b's route over them, the replay R3 and the closeout in the
second. Both replays passed on 2026-11-18, on the batches' heads before
their rebase, and count for a rebased tree only while its replay binding
tests pass; the batches publish after the `0.2.2` release commit, which
carries no commit of the tier (PL.64,
[second tier record](phases/phase-78/route.md#b2-second-tier-record)).
SQLite B2 also makes single-file SQLite SQL write `Bool`
literals as `1` and `0`, a change to the bytes that `0.2.0` and `0.2.1`
publish, which its release lists as incompatible (PL.54).

### Interop relief

The interop relief (IR) is a work package with its own ledger that widens
D80.03's admission table (PL.47). Its slices are implemented (PL.53) and
are in `0.2.2` (PL.55);
[Field admission](interop.md#field-admission) gives the widened table. `UUID`
fields reach pandas and Polars as their 16 bytes, unchanged; `decimal256`
reaches pandas only, and Polars keeps refusing it with a fix that names
`to_pandas`; one level of nesting, a list of structs of admitted flat fields,
reaches pandas and Polars, which revises PL.39 for that level, while deeper
or other shapes stay refused; `to_numpy` takes a nullable `Float` with NaN at
each null, while a nullable `Int` or `Bool` stays refused; the plots take
nullable `Int` and `Float` fields, where a null breaks the line and draws no
point; and `to_scipy_csr` takes `Float` values, stored as float64 with
`-0.0` kept, beside its `Int` coordinates. The Windows claim still leaves
out the extras (PL.40, D5).

### Phase81 scope

Phase81 follows the new route of the owner's draft plan for the later
phases, which bundles several phases for parallel scheduling and which the
lead reviewed, in its next revision, r17, which the lead drafted and the
owner reviewed and dispatched on 2026-11-17; the [Phase81
route](phases/phase-81/route.md) binds its Gate 0 and positions, and its
implementation ran beside `0.2.2` (PL.54, PL.58, PL.65, PL.66).
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
and severity within the existing codes. The assurance work uses
a bounded, seeded generator and shrinker with no new dependency and no
network. The release tools move into `scripts/`, where CI runs only their
dry run and self-tests. Phase81 keeps the sheet's ledger,
`C206/F618/D11,950/S14`, under PL.15, and PL.52's push authorization
applies to its batches since the `0.2.2` release commit was pushed, before
which no Phase81 commit was pushed (PL.57, PL.58).

Phase81 decides the CPython matrix (3.14 into CI and the verified profile;
until then 3.12 and 3.13, with no upper bound on `requires-python`), the
Windows scope and a re-verification policy that reuses a verification result
only for the same immutable input (version, configuration and identity),
with the trust evidence recorded. It holds the diagnostic review that was
planned for Phase82. Natural CI has run the platform-neutral tests on
Windows with Python 3.12 and 3.13 since the 2026-11-06 maintenance
(`e961ddb6`). Of the Windows scope, P05 landed the path-based batch
directory writer and the CLI and compile claim, with execution not claimed
and the extras left out (PL.40, D5;
[platforms and qualification](capabilities.md#platforms-and-qualification));
P06 landed the editor acceptance, the extension's `windows-latest` job on
PyPI's `0.2.2` wheel, and nothing of the scope remains. Nullability v2
changes a public type contract, as Phase81's review found, so the freeze
keeps the v1 rules and v2 waits for `0.3.0` as a breaking item (PL.69).

From the `0.2.1` lanes (PL.44), Phase81's editor work takes the rest of
the fault tolerance of `pietto lsp` and the overlap diagnostic for a
project root nested in another through a symbolic link. With
[P12](phases/phase-81/route.md#p12-record), an internal error outside the
analysis of a document or a root, while the server answers a request or
stores and publishes an analysis, no longer ends the server, and a failed
analysis no longer leaves its old diagnostics on the new text. With
[P13](phases/phase-81/route.md#p13-record), each spelling of a file that
two such roots select publishes only the overlap diagnostic, as for roots
nested as written.

Phase81 also takes three semantic extensions that the owner decided on
2026-11-15 for `let` names in aggregates and under GROUP BY (PL.48), in
place of questions that PL.44 left to its diagnostic review. Items
(1) and (4) are semantic extensions that both modes accept: (1) a `let`
name inside an aggregate's expression argument is read by its value, so
`sum`, `avg`, `count`, `count_distinct` and `string_agg` accept with a
`let` name, as in `sum(d + 1)` after `let d = qty`, the arguments that they
accept with a field, and other aggregates report what they report for the
field; and
(4) a `let` that only renames a field may be selected or projected in a
relation with GROUP BY, as `k` or `x = k` after `let k = qty` and
`group by k`. Item (3) is also a semantic extension: single files accept
`min` and `max` of a numeric `let`, which projects already accept. Each
extension takes a slice of its own with a
two-database verification, and none lands before the `0.2.2` release
commit (PL.57); until each lands,
`0.2.2`'s behavior and the [diagnostics reference](spec/diagnostics.md)
stand.

### Tests and maintenance

Batch 2 (M11–M16), one maintenance batch after the `v0.2.1` tag that
`v0.2.1` does not carry, completed the third whole-tree test pass and the
CI scheduler fix for module fixtures built in several shards (F3), under the
[CI workload governance](architecture/ci-workload-governance-v1.md)
(PL.40, D14; PL.49). The pass left three items to later owners (PL.49),
and one remains: the naming exception of
`tests/_pietto_mysql_native_prepared.py` waits until a line refreezes the
qualification packages that name it, the nested work package or a later
one, since MC refreezes none of them (MC.13). MC settled the surviving
mutants of Phase77 S12's allowlisted guards in `src/pietto/_project` with
the repeated MySQL cell derivation ([MC completion
audit](mysql-catchup/completion-audit.md#pl49s-two-items)), and the pure
verifier fidelity repair (PL.20, D77.54) settled those in the pure reader,
as the
[Slice14 contract](spec/phase66-slice14-private-emission-observation-process-integration-v1.md#coverage)
records. With [P17](phases/phase-81/route.md#p17-record),
`import pietto.execution` loads only its access, input, premise and limit
classes, and each other name imports its owner when first read (PL.40,
D15). Each completion audit records the Gate 2 duration.

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
| pandas and Polars nesting; the Arrow data-analysis example; `compile_queries(...)`; `round` of a `Float` with digits | the owner's answer of 2026-11-15 to the lead's `0.2.1` plan, and for the example the lead's ruling under the owner's later instruction that day (J25, D75.03, D76.05, D80.06, PL.39): one level of nesting to the interop relief (PL.47, which revises PL.39 for that level), and other nesting to a Gate 1 after the nested work package that took Phase77 S24 (D77.32), which admits it before the Phase82 freeze or leaves it refused by the `pietto.interop` ledger row; `compile_queries(...)` after the forged-compiled trust decision, which PL.70 took, at the latest the Phase82 freeze; `round` to its Phase82 freeze ledger row; and the example, whose inputs Phase79 B1 and Phase80 S02 deliver, is delivered by the `0.2.1` interop guidance in [An Arrow table through DuckDB](interop.md#an-arrow-table-through-duckdb) |
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
| SQLite RIGHT, FULL, CROSS and asof JOINs, a JOIN to a query or relation `let`, other `on` forms, `Float` keys, relationship matches, single-match obligations and `any` and `not any` reads; `qualify`, `lag`, `lead`, `ntile`, the value functions, `percent_rank`, `cume_dist`, a window `avg`, named windows, windows over grouped or joined rows, a window `sum` in another frame and `count()` with no partition or order key in a frame other than the default | a later SQLite Gate 1 with a use case; each untaken one a Phase82 freeze input (D78.14; [second tier record](phases/phase-78/route.md#b2-second-tier-record)) |
| SQLite run-time guarded and `Float` arithmetic, `/` and `%`, and arithmetic that reads a parameter; arithmetic in `having`, as the argument of `min` or `max` and `abs` in an aggregate's argument, which `check` refuses on every target; `Text` that holds NUL; SQLite bundles, saved results, relay, jobs and R2; other SQLite builds and platforms; the SQLite capability-facts profile | a later Gate 1 with a use case for the arithmetic; the owner for what `check` refuses, since opening it changes the `check` that every target shares (D78.15 (1), P5 of the [second tier stops](phases/phase-78/route.md#b2-second-tier-order-and-stop-points)); a later SQLite execution Gate 1 for NUL; the later execution and recovery owners; the Phase82 support matrix, where each is not qualified; the editor capability-facts Gate 1; each untaken one a Phase82 freeze input ([B2 deferred owners](phases/phase-78/route.md#b2-deferred-owners)) |
| The MySQL project `sum(Int)` forms that MC did not open | no target: an approved exception listed under J12 (3) in each release, and the Phase82 freeze ledger's MC.10 row (D77.76, MC.10; [MC completion audit](mysql-catchup/completion-audit.md#handoff)) |
| MySQL `count` of a `Float` `+`, `-` or `*` in E4B's cells, and any E4B `count` under a WHERE, kept refused since MySQL may count a row without computing an argument it types non-nullable (a `NOT NULL` column under a nullable declaration), where PostgreSQL fails: first complete fix, MySQL SQL that computes the argument whatever the column's nullability | E4B's chain C owner, with new MySQL bytes and a chain C witness, before the Phase82 freeze (D77.78, MC.04, PL.58, PL.82) |
| The same `count`: second complete fix, MySQL source admission that refuses a `NOT NULL` column under a nullable declaration for each field such a `count` reads, on every reader's route | the MySQL source admission owner with E4B's chain C owner, with a chain C witness of a nullable declaration over a `NOT NULL` column, before the Phase82 freeze (D77.78, MC.04, PL.58, PL.82) |
| Every other position of PostgreSQL's E4 on MySQL, outside E4B's positions, such as two levels of nesting, `/` or an aggregate other than `count` of an operation, a `*` beside a header parameter or `Float` arithmetic in a JOIN `on` | no target (MC.04, MC.10, PL.68, PL.76) |
| `verify_project_sql_plan` runs 38 times in one `compile_query` call on a one-relation fixture on PostgreSQL and 70 on MySQL, since that call's emission (32 checks; 64 on MySQL) and the serialization of its document in `pietto.execution` (5) run outside any call scope, beside the one check of its `prepare_live_template` scope; since [Phase81 P15](phases/phase-81/route.md#p15-record), `emit-sql --project` and `compile_sql` check each plan once per call | Phase81's P16, which keeps it in Phase81 or moves it to `0.3.0`, the Rust rewrite; reused only inside one public call (PL.40, D15; PL.50 Q6) |

## Phase82 freeze ledger

Phase82 rules on each row; it does not collect them anew. From Phase76 on,
each completion audit adds the freeze inputs of its phase here. On
2026-11-26 the owner approved as proposed the disposition of each row in
the lead's plan for Phase81–90, which Phase82's Gate 1 records (PL.99
(2)).

| Subject | Ruling Phase82 makes | Recorded by |
| --- | --- | --- |
| `pietto.compiler` (the Python compile API) | freezes (owner, 2026-11-07) | D75.02 |
| `pietto.project-relation-columns.v1`, with the kinds `type_alias` and `unknown` and the `module` field of type objects | freezes (owner, 2026-11-07) | D75.01 (owner answer B1-1, 2026-11-07) |
| The `fmt` output, its layout items (the gaps between the tokens of a line, a head comment paragraph attached to the first declaration), a line width, options and a JSON output | decided (PL.101 (3)): the output freezes after `fmt` normalizes its layout items, or as it stands if that work passes its stop point | D75.05, D75.14, PL.101 |
| `pietto lsp`, editor partial analysis and the five editor-only messages; whether `pietto.cli.main(argv)` is a documented entry point | only the diagnostic protocol freezes; the messages get a catalog without PIE codes; the entry point is decided (PL.99 (4)): `pietto.cli.main(argv)` becomes a documented entry point | D75.09–D75.12, Phase76 handoff, PL.99 |
| The E-C alpha surfaces of `pietto lsp` (formatting of the open buffer, workspace symbols, import-path document links, completion from the static vocabulary and the open buffer's identifiers, and the hover and definition facts of LSP editor facts v1); the VS Code extension's use of `pietto.cli.main(argv)` to start the server | each surface freezes with its alpha contract or changes before the freeze; the entry point is decided with the `pietto lsp` row above | ED.03, ED.09, ED.11 |
| `pietto.sql.emit_postgres_sql` | stays public and enters the API inventory | owner, 2026-11-07 |
| `pietto.interop`: its five adapters (six functions), the D80.03 admission table as the interop relief widened it ([Field admission](interop.md#field-admission): a `UUID` as its 16 bytes in pandas and Polars, `decimal256` in pandas only, one level of nesting in both, a nullable `Float` in `to_numpy` and nullable `Int` and `Float` fields in the plots as NaN, and `Float` values in `to_scipy_csr`), with nested fields beyond its one level refused, the D80.04 exception order, and the five `interop-*` extras with their pins | the surface freezes with its alpha contract or changes before the freeze; a pin refresh re-checks whether Polars reads `decimal256`, and if Polars gains a UUID dtype, which the dtype comparison then refuses, its mapping goes to the owner; other pandas and Polars nesting is admitted by a Gate 1 before then or stays refused | D80.02–D80.06, D80.08, D80.09, AD80.01, PL.47, PL.53; [Phase80 audit](phases/phase-80/completion-audit.md) |
| The header rule and its tokens retained by Phase76 | decided (PL.101 (4)): removed under the migration/hint compatibility contract, with `migrate` and the PIE-P1000 hints equal to their bytes just before the removal | D75.06, D76.12, PL.101; [Phase76 audit](phases/phase-76/completion-audit.md) |
| The nested public format; grouping extensions, automatic fan-out repair and a public aggregate state | frozen, or kept unsupported | Phase71 route, Phase74 handoff |
| `def` and `relationship` items in PACKAGE_ROOT modules; a built-in table function | for the `def` and `relationship` items, decided (PL.98 (2)): kept refused, which a later `0.2.x` may open compatibly (PL.100 (v)), and Phase90's Gate 1 reviews it again at the latest; for a built-in table function, admitted, or kept refused | D74.07, D74.12, PL.98 |
| PostgreSQL extension functions, the function/plugin SPI, user-written table functions, database-native array and JSON columns, the `postgres_adbc` nested route | the Phase82 support matrix lists each one no Gate 1 took as not supported | D76.11, D80.06, PL.51 |
| Project `matches(...)`; `Decimal` division and `avg`; `round` of a `Float` with digits | a contract, or a refusal that stays | D76.03, D76.05, D80.06 |
| The PostgreSQL TLS profile of `PostgresAccess.ca_file` | a support-matrix row | D76.07 |
| Single files and projects | `language.md` states the rule before the freeze: single files open project-only forms one at a time, DISTINCT first, with no promise that they stay a subset of projects | owner, 2026-11-07 |
| Bundles and saved jobs across versions; an upgrade-impact tool | decided (PL.101 (1)): the Phase82 compatibility and migration policy keeps them bound to the exact installed code, so that one from other code is refused with PIE-R1005 rather than misread; there is no migration and no upgrade-impact tool before the freeze, and no promise that a version's bundle or job loads on every supported installation of it | D76.13, Phase76 reminder 7, PL.51, PL.101 |
| Nullability v2 | frozen at the v1 rules; v2 is a breaking item for `0.3.0` (PL.69) | D73.13, owner, 2026-11-07, PL.50, PL.51, PL.69 |
| The CPython matrix and the Windows claim | frozen as Phase81 decides them | owner, 2026-11-07 |
| The release notes' history before the freeze, which keeps its file layout until then | archived by the Phase82 freeze | PL.40 (D10), PL.51 |
| Compiled replay and live analysis give different JOIN key and grain facts for equal SQL bytes | decided (PL.61): live semantic analysis is the only authority, and adapters read the facts only from the verified plan; JF's J2 aligns the compiled replay with the same law before Phase82's Gate 1, and Phase82 audits the closed decision | Phase74 handoff, Phase76 reminder 8, PL.61, PL.62 |
| A forged compiled aggregate whose argument reads a `let:` name in a form that `compile_query` refuses for that aggregate, such as `sum(t)` with `let t = value % 2`, loads with consistent SQL | fixed: `load_bundle` refuses such a bundle (`PIE-R1004`): the compiled replay and its semantic verifier judge a `let:` name that is a whole aggregate argument by the value it holds, except under `min` and `max`, which read it as a field, refuse a computed `let:` value inside an argument's own operation, as an aggregate `order by` key, or in the test or the summed field of a conditional count or sum and the test of `any` or `all` over a group, and read a window's value only from a field; a `let:` name that only renames a field reads as that field, so an edited bundle that reads one where `compile_query` refuses the name, such as `sum(d + 1)` with `let d = value`, loads as a known equivalence of the field form, such as `sum(value + 1)`, with equivalent SQL; Phase82 audits the closed row | Phase74 handoff, Phase76 reminder 8, PL.70 |
| The VS Code extension's sync script imports the generated lexer and parser from `pietto.generated` and two functions from `pietto.indentation`, modules that no public contract names | decided (PL.99 (4)): a limited tool contract names only what the script reads, and the other modules are internal | PL.38, PL.44, PL.99 |
| The fixed civil `Timestamp` meaning of a `now()` output; the statement time that R2 records and `recover` binds | each freezes with the result contract and the R2 workspace, or changes before the freeze | D77.42, D77.49; [Phase77 audit](phases/phase-77/completion-audit.md) |
| MySQL R2 refuses every form that `0.1.11` refused (`PUBLIC_R2_UNQUALIFIED_FORM`, by rule two) and every paired form (`PUBLIC_R2_PAIRED_FORM`) | a support-matrix row for R2 by target, or narrowed by forms that a native R2 qualification covers | D77.46, D77.67, D77.68 |
| MySQL forms that open only byte for byte as a paired form (Wave A) | the Phase82 support matrix states them as paired forms, or a structural rule replaces them | D77.36; [Phase77 audit](phases/phase-77/completion-audit.md) |
| SQLite SQL and the `sqlite_file` route: single-file `emit-sql FILE --dialect sqlite` with the successful CLI JSON v1 `dialect` value `"sqlite"`, the PIE-B1000 SQLite reasons, the declared premises and `Bool` literals written `1` or `0`; the `sqlite.table("name")` spelling with its PIE-S2306 texts; the project dialect `sqlite` with the contract target `{"family": "sqlite", "release": "3.53.1"}`, the `main` namespace, the scan `"relation_rows"` and the storage kinds, the compile refusals and their order with their details and suggestions, and the first tier's forms with their SQL spellings (`COLLATE BINARY`, the NULLS clauses, `AVG(CAST(x AS REAL))`, the one-sided `sum`) and the second tier's (range-proved `Int` arithmetic with `ABS(x)` and a negative `Int` literal written signed, windows over one source read written inline as `OVER (...)` with their frames, and INNER and LEFT equality JOINs of sources with the aliases `s0` to `sN` and `COLLATE BINARY` at each `Text` key); `compile_query(dialect="sqlite")` and `execute(route="sqlite_file")` with `SQLiteFileInput` and `premise=None`, its defences and its value and integrity check on each source table a statement reads, the bounded read of a statement that joins sources, the check of declared `unique(...)` keys before a joined aggregate, the authorizer's ranking functions, the limits of 128 MiB, 1,048,576 rows per source table and `limits.seconds`, the side files of a WAL file's read, and its detail words, `SQLITE_ERRORCODE_<n>` and `SQLITE_INTEGER_OVERFLOW` among them | frozen, kept alpha, or kept unsupported; the Phase82 support matrix lists the qualified SQLite build on Linux x86-64 under CPython 3.13.13 and 3.12.13, and every other build and platform as not qualified | D78.01–D78.04, D78.12, D78.14–D78.17, PL.47, PL.54, PL.59, PL.64; Phase78 B1 closeout; [Phase78 audit](phases/phase-78/completion-audit.md); [second tier record](phases/phase-78/route.md#b2-second-tier-record) |
| The DuckDB Arrow route: the `duckdb.arrow("key")` spelling with its PIE-S2306 texts, the project dialect `duckdb`, the contract target `{"family": "duckdb", "release": "2.0.1"}` with `scan` `"arrow_registration"`, the `arrow` namespace and the `arrow_*` storage kinds, the DuckDB compile refusals and their order with B2's details and suggestions, B2's forms (grouping with `count`, `sum`, `min` and `max`, `having`, `order by` with its NULLS clauses, the static `limit`, and predicates over literals and parameters of four types) and the second tier's (`Date`, `Timestamp` and `Decimal(p, s)` fields with `p` at most 38 and their `arrow_date32`, `arrow_timestamp_us` and `arrow_decimal128` storages, `Int` arithmetic by range proof and `Float` arithmetic with its overflow and underflow checks in the final projection, and `inner` and `left` equality JOINs, one source read twice included) with their SQL spellings and `physical_type` values, `execute(route="duckdb_arrow")` with a `DuckDBArrowInput` or a tuple of them and `premise=None`, the capture limits of 1,048,576 rows per input and 256 MiB of the selected columns over all inputs with their check order and the declared key check, the reading of every result in batches with its charge and `transaction`, the session settings with the 1 GiB `memory_limit` and the `default_collation` read-back, the detail words and the `execute-duckdb` extra | frozen, kept alpha, or kept unsupported; the Phase82 support matrix lists `duckdb` `2.0.1` with `pyarrow` `26.0.1` on the qualified platforms and every other release and platform as not qualified | D79.01–D79.15, D79.17–D79.30, D79.32, AD79.01, PL.47, PL.50, PL.92; [Phase79 B1 audit](phases/phase-79/completion-audit.md), [B2 audit](phases/phase-79/b2-completion-audit.md), [Phase79 completion audit](phases/phase-79/t2-completion-audit.md) |
| `RequestRejected` also carries the PIE-R2xxx refusals of the checks that `execute()` runs itself (`PIE-R2003` on `mysql_rows` and `postgres_adbc`, `PIE-R2001` and `PIE-R2002` of the loaded PyArrow on `duckdb_arrow`, `PIE-R2002` `SQLITE_BUILD` on `sqlite_file`), and the PIE-R1004 width refusal (`LIMIT`) covers only the PostgreSQL and MySQL routes | each freezes with the execution error classes, or changes before the freeze | D79.11; [Phase79 B1 audit](phases/phase-79/completion-audit.md) |
| The MySQL project `sum(Int)` forms that the MySQL catch-up work package MC did not open, and the E4 forms that neither E4's narrow cell nor E4B opens, `Float` arithmetic in a JOIN `on` (PL.68) and a `*` beside a header parameter (PL.76) among them | the support matrix states MySQL as unsupported for each, or gives it a target after the freeze | MC.10, PL.68, PL.76; [MC completion audit](mysql-catchup/completion-audit.md#handoff) |
| Whether PostgreSQL fails a statement over an out-of-range `Float` value that the plan may leave uncomputed, as in the shapes that E4B keeps refused because the plan fixes their computed rows (a `let` that a WHERE beside it does not read, a comparison beside another WHERE condition): the [`Float` law](language.md#float-values) does not say, while the `Int` law says that whether and when such a statement fails depends on the plan ([Aggregates and grouping](language.md#aggregates-and-grouping)) | decided (PL.101 (5)): the `Float` law's PostgreSQL side is documented as the `Int` law is written, with no change of behavior; an uncertainty of `main`, not an observed defect | PL.75 (2), PL.101; [MC completion audit](mysql-catchup/completion-audit.md#e4b) |
| A field of the PostgreSQL and MySQL deployment premises that verifies the declared keys only, off by default | decided (PL.101 (6)): added within `0.2.x`, with today's bytes while it is off; its default turns on only in `0.3.0` | PL.101 |
| Statements that the emitted SQL keeps an authored form or order, such as a correlated read never rewritten to a JOIN or decorrelated, `not in` never an ANTI JOIN, and the authored JOIN order | frozen for the default compile; an explicitly enabled compile-time optimizer option may emit a form proven equivalent to the authored one that `language.md` lists for that option, while results, diagnostics, types, nullability and the errors a statement can raise stay as promised | owner, 2026-11-26; PL.102, PL.105 |

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
