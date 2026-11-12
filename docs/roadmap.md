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
[Phase76 completion audit](phases/phase-76/completion-audit.md) records its
delivered scope and Phase77 handoff; Git and natural CI own its publication.
D76.01–D76.18 and the technical reminders that reach beyond Phase76 remain in
the [decision record](decisions.md#phase76--owner-decisions-2026-11-07) and the
sections below.

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
| 82 | Public schemas/API/CLI/syntax/support-matrix freeze, ruling on the [freeze ledger](#phase82-freeze-ledger) |
| 83 | Stable 1.0 release audit and publication |
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

Phase77 follows its [route](phases/phase-77/route.md). On 2026-11-10 the owner
approved the Gate 1 of Phase78 SQLite B1, Phase79 DuckDB B1, Phase80 and the
editor core work package E-C, which run beside Phase77 under the shared rows
PL.01–PL.06 of the
[decision record](decisions.md#phase7880-and-editor-core-gate-1--owner-decisions-2026-11-10):
see the [Phase78 route](phases/phase-78/route.md), the
[Phase79 route](phases/phase-79/route.md), the
[Phase80 route](phases/phase-80/route.md) and the
[E-C route](editor/ed03-route.md).

The owner's answers of 2026-11-07 settled the rules below; the
[decision record](decisions.md#roadmap-after-0110--owner-decisions-2026-11-07)
gives each with its source.

### Versions

`0.1.10` carries Phase73, Phase74 and Phase75. Pietto core Phase76 and
Phase77 ship together as `0.1.11`. Phase78–80 ship as `0.2.0` once its gate
below is met; Phase81 uses `0.2.x`, Phase82 uses `1.0.0rc1` and Phase83 uses
`1.0`. The extension follows its own version line.

`0.2.0` requires PostgreSQL and MySQL within the MySQL cadence below, one
local analysis path (the limited DuckDB path of Phase79, not a complete third
dialect) and the Phase80 interoperability with five libraries and its Python
surface. It does not require editor facts; the editor ships on its own
extension versions.

Before 1.0 a release may carry breaking changes: it lists them at the top of
its release notes with a pin to the previous exact version and keeps
recompiling, reading saved results and running again apart, and bundles and
saved jobs are not migrated before the Phase82 compatibility decision
(D76.13). The VS Code extension has versions of its own (see the editor work
package). Each release is approved on its own.

### After 1.0

Phase82 freezes concrete semantics and compatibility rules: each public
contract states what a `1.x` release may add and what stays, and an addition
that can break a working program or reader, such as a new reserved name or a
JSON field, counts as a compatibility change. A breaking change waits for
`2.0`. Phases 84–90 and the tentative owners below work inside those rules.

### MySQL cadence

MySQL support may trail PostgreSQL by about two to three phases (D76.10). New
features reach PostgreSQL first, which finds the problems, and MySQL catches
up in later batches; until then each MySQL path fails closed with a
deterministic diagnostic. Semantics and IR stay dialect-neutral, a form opens
on MySQL only after a passing two-database run (D74.09), and the capability
page and the release notes list what MySQL refuses. Project `sum(Int)`,
`stddev` of an `Int` (J12, D76.10) and MySQL nested results (D71.05) are
approved exceptions with the target Phase77. Each release request lists the
MySQL forms beyond the cadence (D76.09).

### Editor work package

The editor line is its own work package beside Phases 76–80, tied to none of
them. The core semantic owner provides the facts and the extension consumes
them. [LSP diagnostics v1](spec/lsp-diagnostics-v1.md) describes the diagnostic
protocol of `pietto lsp`, and
[LSP editor facts v1](spec/lsp-editor-facts-v1.md) the hover, go-to-definition
and document symbols that ED.01 and ED.02 selected, from an ephemeral
in-process snapshot with the existing metadata formats unchanged; both are
alpha contracts. Each remaining step needs its own Gate 1. The owner approved
the first on 2026-11-10: the editor core work package E-C (ED.03–ED.06, the
[E-C route](editor/ed03-route.md)) first measures an editor latency budget over
a representative corpus, which decides whether the linear analysis of layered
JOIN DAGs and the FD sharing of PMS-6 (see the
[project-mode follow-up](#project-mode-follow-up)) come first, and adds
formatting, workspace symbols, document links, completion from the static
vocabulary and the open buffer's identifiers (ED.09) and wider hover and
definition to `pietto lsp`. Still ahead are the capability
facts, which get a new versioned capability document whose own Gate 1 records
the weighing against the
[semantic metadata artifact v1](spec/semantic-metadata-artifact-v1.md) (ED.06),
in four layers (check, SQL emission, execution, result reading) and three
states (unsupported, unknown, not qualified), read alike by editors and AI
tools, with each backend filling its own profile; and the extension's model
view, rebuilt on the column view.

The owner's VS Code extension (`MianliWang/pietto-vscode-extension`) takes
its diagnostics from `pietto lsp` and versions apart from Pietto, with a
minimum Pietto version that its own checks enforce: `0.2.0` stays, small
changes ship as `0.2.x`, `0.3.0` comes only with a user-visible editor
feature, and no Marketplace pre-release channel is used. PostgreSQL SQL
preview is the feature now published on the independent `0.3.0` line (see
[status](status.md)). It gets a CI in its
repository, which needs its own authorization, and its Marketplace timing is
the owner's. Each Pietto phase that changes the grammar or the built-in
catalog carries the extension sync, made by the lead, and the sync script
stops reading the private `pietto.parser_api._parse_migration_source`.

### Third dialect

The owner selected AD78.01 on 2026-11-08: small Pietto-owned target adapters,
with sqlglot only as a test oracle, and the limited DuckDB path before SQLite.
The existing PostgreSQL/MySQL emitters retain their SQL-byte and semantic
authority; sqlglot is not a runtime dependency. Phase numbers stay unchanged.
On 2026-11-10 AD78.02 revised that schedule: Phase78 SQLite B1 is implemented
in parallel with Phase77 and Phase79 and publishes after Phase79 DuckDB B1,
and AD78.03 fixes the third-dialect seam the two share. The
[Phase78 route](phases/phase-78/route.md) and the
[Phase79 route](phases/phase-79/route.md) bind each B1's supported forms,
pinned dependencies, error ownership and qualification; this architecture
decision does not open a dialect by itself.

### Phase81 scope

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
and a native Windows editor acceptance; until then the package keeps its
`Operating System :: OS Independent` classifier. Nullability v2 goes to
Phase81 if it changes a public type contract, otherwise to `2.0`.

### Tests and maintenance

The third whole-tree test pass ends before the end of Phase78. The CI scheduler fix for module fixtures built in
several shards (F3) is authorized as its own maintenance batch, with its
evidence under the
[CI workload governance](architecture/ci-workload-governance-v1.md). The
import time of `pietto.execution` may be fixed before Phase80. Each
completion audit records the Gate 2 duration.

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
| Database-native array and JSON columns; the `postgres_adbc` nested route | a later Phase80 Gate 1 (D80.06); the Phase82 freeze (D76.11) |
| MySQL nested output and `JSON_TABLE` | Phase77 (D71.05) |
| pandas and Polars nesting; the Arrow data-analysis example; `compile_queries(...)`; `round` of a `Float` with digits | a later Phase80 Gate 1 (J25, D75.03, D76.05, D80.06) |
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

## Phase82 freeze ledger

Phase82 rules on each row; it does not collect them anew. From Phase76 on,
each completion audit adds the freeze inputs of its phase here.

| Subject | Ruling Phase82 makes | Recorded by |
| --- | --- | --- |
| `pietto.compiler` (the Python compile API) | freezes (owner, 2026-11-07) | D75.02 |
| `pietto.project-relation-columns.v1`, with the kinds `type_alias` and `unknown` and the `module` field of type objects | freezes (owner, 2026-11-07) | D75.01 (owner answer B1-1, 2026-11-07) |
| The `fmt` output, its layout items (the gaps between the tokens of a line, a head comment paragraph attached to the first declaration), a line width, options and a JSON output | the output freezes after its layout items | D75.05, D75.14 |
| `pietto lsp`, editor partial analysis and the five editor-only messages; whether `pietto.cli.main(argv)` is a documented entry point | only the diagnostic protocol freezes; the messages get a catalog without PIE codes; the entry point is decided | D75.09–D75.12, Phase76 handoff |
| `pietto.sql.emit_postgres_sql` | stays public and enters the API inventory | owner, 2026-11-07 |
| The header rule and its tokens retained by Phase76 | removed under the migration/hint compatibility contract | D75.06, D76.12; [Phase76 audit](phases/phase-76/completion-audit.md) |
| The nested public format; grouping extensions, automatic fan-out repair and a public aggregate state | frozen, or kept unsupported | Phase71 route, Phase74 handoff |
| `def` and `relationship` items in PACKAGE_ROOT modules; a built-in table function | admitted, or kept refused | D74.07, D74.12 |
| PostgreSQL extension functions, the function/plugin SPI, user-written table functions, database-native array and JSON columns, the `postgres_adbc` nested route | the 1.0 support matrix lists each one no Gate 1 took as not supported | D76.11 |
| Project `matches(...)`; `Decimal` division and `avg`; `round` of a `Float` with digits | a contract, or a refusal that stays | D76.03, D76.05 |
| The PostgreSQL TLS profile of `PostgresAccess.ca_file` | a support-matrix row | D76.07 |
| Single files and projects | `language.md` states the rule before the freeze: single files open project-only forms one at a time, DISTINCT first, with no promise that they stay a subset of projects | owner, 2026-11-07 |
| Bundles and saved jobs across versions; an upgrade-impact tool | the 1.0 compatibility and migration policy, and whether the tool comes before 1.0 | D76.13, Phase76 reminder 7 |
| Nullability v2 | Phase81 if it changes a public type contract, otherwise `2.0` | D73.13, owner, 2026-11-07 |
| The CPython matrix and the Windows claim | frozen as Phase81 decides them | owner, 2026-11-07 |
| Compiled replay and live analysis give different JOIN key and grain facts for equal SQL bytes | an ARCHITECTURE_DECISION of the semantic and ProjectIR owner, with the lead integrating every reader, before any slice consumes those facts | Phase74 handoff, Phase76 reminder 8 |
| A forged compiled `median(id * 2)` loads with consistent SQL | a trust decision of the compiled and verifier owner, coordinated by the lead, before the first new consumer of compiled admission and at the latest before `compile_queries(...)` | Phase74 handoff, Phase76 reminder 8 |

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
