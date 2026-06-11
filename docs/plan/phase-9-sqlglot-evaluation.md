# Phase 9 SQLGlot Evaluation

## Status

**This evaluation is planning-only and does not approve SQLGlot as a
production dependency.**

**Decision: approved only for a future isolated Phase 10 MySQL-generation
spike; not approved as a production dependency, PostgreSQL replacement, or
implementation in Phase 9.**

The spike approval means that SQLGlot remains a candidate worth testing
against Pietto's accepted adapter boundary. It does not authorize a dependency
change, backend implementation, MySQL CLI behavior, PostgreSQL rewrite,
transpilation pipeline, optimizer, executor, database integration, or runtime
feature.

The handwritten PostgreSQL backend remains authoritative. A future MySQL
backend may use SQLGlot only if a separate Phase 10 spike satisfies every
mandatory gate in this document.

## Evidence Basis

Evidence was reviewed on June 11, 2026. The specifically reviewed release is
SQLGlot 30.9.0, published on PyPI and tagged in the official repository on
June 4, 2026.

The review used:

- the current Pietto PostgreSQL backend and SQL result model;
- the five reviewed PostgreSQL byte-exact golden fixtures;
- the Phase 9 master plan;
- `docs/spec/sql-dialect-source-contract-v1.md`;
- SQLGlot's official README and API documentation;
- SQLGlot's official dialect registry and AST primer;
- SQLGlot's official package metadata and MIT license;
- the official GitHub tag history and PyPI 30.9.0 artifact metadata.

No SQLGlot package was installed. No package artifact was downloaded or
executed. No local spike was needed to answer the architecture-level questions
in Slice 4. Import time, memory use, direct-construction API details, exact
generated SQL, and Pietto-specific failure behavior therefore remain explicit
Phase 10 evidence gaps.

## Acceptable Role

The only acceptable future role is:

```text
Pietto Semantic IR
    -> isolated Pietto SQLGlot AST adapter
    -> SQLGlot dialect generator
    -> dialect SQL text
    -> existing Pietto SqlResult
```

The adapter must consume `ScriptIR` directly. It must construct SQLGlot
expression nodes from supported IR nodes without parsing generated SQL text.
SQLGlot types must remain private to the adapter and must not enter Semantic
IR, public APIs, diagnostics, or CLI/JSON models.

The selected dialect must be explicit. A future first use should be limited to
MySQL generation while the handwritten PostgreSQL backend remains the
reference implementation.

## Rejected Roles

The following roles are rejected:

- PostgreSQL SQL to MySQL transpilation;
- parsing Pietto source or replacing the Pietto parser;
- replacing semantic analysis or Semantic IR;
- optimizer use or semantic query rewriting;
- executor or in-memory runtime use;
- SQL execution;
- database connection or destination selection;
- connector execution;
- schema introspection or type inference from a database;
- exposing SQLGlot AST nodes through Pietto public APIs;
- using SQLGlot's generic dialect as an implicit fallback.

Transpilation is especially unsuitable. It would make rendered PostgreSQL text
an intermediate representation, lose direct IR-to-diagnostic attribution, and
invite the best-effort behavior that Pietto's fail-closed contract prohibits.

## Pietto Baseline

Any future SQLGlot work must preserve:

- `emit_postgres_sql(ScriptIR) -> SqlResult`;
- the handwritten PostgreSQL backend;
- current PostgreSQL byte-exact golden output;
- ordered `SqlArtifact` and `PIE-B1000` behavior;
- current compiler-stage isolation;
- JSON v1 fields and semantics;
- existing CLI commands, flags, exit codes, and text output;
- generation-only behavior with no execution or connection path.

The Phase 9 dialect/source contract remains the authority for connector,
function, expression, identifier, literal, physical-name, and diagnostic
capabilities. SQLGlot support for a construct does not make that construct a
Pietto backend capability.

## Decision Matrix

| Criterion | Evidence | Result | Required consequence |
|---|---|---|---|
| Programmatic AST construction | Official documentation exposes expression trees, constructors, builders, traversal, and dialect generation | Conditional pass | Phase 10 must prove direct construction for every MySQL MVP IR node without parsing SQL strings |
| PostgreSQL and MySQL rendering | Both dialects are listed as officially maintained | Pass for spike | Always choose the target generator explicitly |
| Unsupported-feature behavior | Default behavior may warn and continue with best-effort output; `RAISE` and `IMMEDIATE` modes are documented | Conditional pass | Pietto capability validation remains primary and all generator unsupported cases must fail closed |
| Type isolation | SQLGlot accepts and returns its own expression objects | Pass by architecture | Keep all SQLGlot types inside one internal adapter and return Pietto `SqlResult` only |
| PostgreSQL byte-exact compatibility | SQLGlot controls quoting, formatting, aliases, parentheses, and rendering; no byte-exact Pietto evidence exists | Fail for migration | Do not migrate PostgreSQL; any later proposal requires exact equality across all PostgreSQL goldens |
| MySQL-only generation | Official MySQL generator support and direct AST construction make an isolated adapter plausible | Conditional pass | Evaluate only the accepted MySQL MVP surface first |
| API stability and pinning | Official versioning permits backwards-incompatible minor releases | High risk | Select and pin one exact version for a future spike; review every upgrade |
| License and provenance | SQLGlot 30.9.0 reports MIT, Python 3.9+, a verified PyPI maintainer, source and universal wheel artifacts | Conditional pass | Re-review the exact chosen release, hashes, maintainers, and distribution before adoption |
| Release cadence | At least ten tags from 30.3.0 through 30.9.0 were published between April 7 and June 4, 2026 | High-change signal | Do not use a floating compatible range for initial integration |
| Dependency surface | The base package is documented as no-dependency; optional `c`, `rs`, and `dev` extras and optional optimizer behavior exist | Conditional pass | Install no extras, native acceleration, optimizer dependency, or plugin dialect |
| Resource consumption | Upstream publishes parser benchmarks, but no Pietto AST-generation measurements were run | Open | Measure import, generation, depth, output size, CPU, and memory in Phase 10 |
| Failure modes | Structured parse and unsupported errors exist, but direct adapter failures were not exercised | Open | Define exception translation, warning capture, no-partial-output behavior, and resource failure policy |
| Generation-only threat boundary | AST construction and SQL generation can be used without executor, optimizer, IO, or database APIs | Pass by architecture | Restrict imports and tests to expression construction and dialect generation |
| Maintenance advantage | Shared dialect machinery may reduce MySQL quoting and rendering work, but adapter cost is unmeasured | Open | Compare a small handwritten MySQL backend with the isolated SQLGlot adapter during the spike |

The matrix supports a limited spike, not adoption. The PostgreSQL migration
criterion currently fails, and the resource, failure-mode, and maintenance
criteria still require measured evidence.

## AST Construction Assessment

SQLGlot documents programmatic SQL construction and a common expression tree
used by its dialect generators. This makes the accepted IR-to-AST adapter
architecturally feasible.

The evidence is not yet sufficient to approve implementation:

- some convenience examples accept SQL strings and therefore parse text;
- direct constructors expose SQLGlot-specific node and argument conventions;
- the stability of those constructors across minor releases is not promised;
- no Pietto expression, identifier, literal, or relation mapping was run;
- no MySQL output was compared with a reviewed Pietto contract.

A Phase 10 spike must use direct expression construction for every supported
IR node. It must not use `parse_one`, `condition` with SQL strings,
`transpile`, or rendered PostgreSQL SQL as an adapter shortcut.

## Dialect Rendering Assessment

SQLGlot 30.9.0 lists PostgreSQL and MySQL as officially supported dialects.
This is sufficient evidence that both generators exist and are maintained by
the core project. It is not proof that either generator matches Pietto's exact
surface or compatibility policy.

For a future MySQL spike, the adapter must explicitly select MySQL and test:

- backtick identifier quoting and escaping;
- one opaque physical table name;
- text, Boolean, integer, finite float, and `NULL` literals;
- fields, qualified fields, aliases, and relation references;
- comparisons, null predicates, `BETWEEN`, unary, arithmetic, and Boolean
  operators;
- `lower`, `trim`, and `len -> CHAR_LENGTH`;
- metadata no-op behavior;
- artifact and diagnostic ordering;
- deterministic rejection of `matches`.

SQLGlot's PostgreSQL generator is not needed for that spike.

## Fail-Closed Requirements

SQLGlot documents best-effort translation as the default for some unsupported
cases. That default is incompatible with Pietto.

A future adapter must use layered failure controls:

1. Validate the closed Pietto backend capability declaration before creating
   SQLGlot nodes.
2. Map only explicitly supported IR nodes, functions, operators, connectors,
   literals, and identifiers.
3. Select the target dialect explicitly.
4. Configure the selected SQLGlot generation API to raise immediately for
   unsupported behavior, and prove that configuration with focused tests.
5. Treat any SQLGlot warning, unsupported condition, unexpected node,
   rendering exception, or invalid output as a backend failure.
6. Convert expected adapter failures into deterministic Pietto backend
   diagnostics using the original IR span and ordering.
7. Emit no SQL artifact for a failed relation and never substitute another
   function, operator, connector, or dialect.

`RAISE` or `IMMEDIATE` is a secondary guard, not Pietto's capability model.
An absence of a SQLGlot error does not prove that generated SQL has the
semantics Pietto accepted.

## Isolation Requirements

A future adapter must be internal and one-directional:

```text
ScriptIR -> private SQLGlot expressions -> SQL text -> SqlResult
```

It must not:

- add SQLGlot fields or types to Semantic IR;
- change `emit_postgres_sql`;
- add a generic public emitter merely to expose SQLGlot;
- return SQLGlot exceptions or nodes;
- invoke parser, optimizer, executor, lineage, schema, or database helpers;
- mutate `ScriptIR`;
- import SQLGlot from parser, semantic, IR, CLI presentation, or JSON modules.

The adapter owns only dialect AST construction and generation. Pietto owns
capability validation, source spans, diagnostics, artifact models, and public
interfaces.

## PostgreSQL Compatibility Decision

PostgreSQL migration is not approved.

This conclusion is based on a compatibility gap, not a claim that SQLGlot
cannot generate valid PostgreSQL. SQLGlot's generator owns rendering choices,
while Pietto already has a byte-exact contract for whitespace, aliases,
identifier quoting, literal spelling, parentheses, artifact boundaries, and
dotted physical names.

No official SQLGlot document promises byte-for-byte stability against
Pietto's handwritten renderer, and Slice 4 ran no output experiment. The
reasonable inference is that migration would create formatting and
compatibility work without helping the first MySQL MVP.

Any later PostgreSQL migration proposal must be separately approved and must:

- preserve the public emitter and result models;
- pass all PostgreSQL unit tests;
- match all five reviewed SQL golden fixtures byte for byte;
- preserve diagnostics and artifact ordering;
- preserve `"public.users"` as one quoted identifier;
- demonstrate a maintenance benefit that justifies migration risk.

Phase 10 should not attempt this work.

## Dependency And Supply-Chain Assessment

SQLGlot 30.9.0 has an MIT license and requires Python 3.9 or newer, which is
compatible with Pietto's Python 3.12 baseline. The project describes the base
package as dependency-free. PyPI publishes a pure-Python universal wheel and a
source distribution.

The package also advertises optional `c`, `rs`, and `dev` extras. SQLGlot
documentation mentions optional `dateutil` behavior for optimizer
simplification. Pietto has no need for those paths. An initial spike must use
the pure-Python base package only.

The observed release cadence and versioning policy increase upgrade risk:

- minor releases may be backwards-incompatible;
- tags are frequent;
- AST construction details are adapter-critical;
- generator changes can alter golden output.

PyPI reports that the reviewed 30.9.0 artifacts were uploaded with Twine and
not with Trusted Publishing. This is a provenance consideration, not by
itself a rejection. A future dependency review must verify the selected
release, artifact hashes, lockfile resolution, maintainers, license, package
contents, and vulnerability audit.

If Phase 10 later proposes production adoption, it must:

- select one exact reviewed version rather than a floating range;
- add no extras, native extension, plugin dialect, optimizer, or executor
  dependency;
- review the complete `pyproject.toml` and `uv.lock` diff;
- run `uv lock --check` and `uv audit --locked`;
- require all PostgreSQL golden tests and reviewed MySQL golden tests;
- treat upgrades as explicit compatibility changes with the same review.

Slice 4 changes no dependency and does not select 30.9.0 for future
production. The exact candidate must be re-reviewed when the spike begins.

## Resource And Failure-Mode Gaps

No Pietto-specific performance or robustness experiment was run. Upstream
parser benchmarks do not answer direct AST-generation costs.

The Phase 10 spike must measure representative and adversarial cases for:

- import time and imported module surface;
- wheel and installed size;
- AST node count and generation time;
- deeply nested expressions and recursion behavior;
- large projections, identifiers, and string literals;
- maximum generated SQL size;
- warning and exception behavior;
- deterministic handling of unsupported nodes;
- accidental partial output;
- memory and CPU growth.

Pietto's current 1 MiB source and token limits are frontend controls. They do
not independently bound SQLGlot AST size, recursion, generated output, or
backend time. A production proposal must connect backend costs to an accepted
resource policy.

## Phase 10 Spike Contract

The future spike is approved only as an evidence-gathering activity. It must
compare:

```text
Option A: small handwritten MySQL renderer
Option B: isolated ScriptIR-to-SQLGlot-AST MySQL adapter
```

The SQLGlot option may proceed toward production only if it proves:

- direct AST construction for the full accepted MySQL MVP;
- no parsing or transpilation of SQL text;
- private type isolation;
- strict fail-closed unsupported behavior;
- deterministic Pietto diagnostics;
- reviewed MySQL byte-exact golden outputs;
- unchanged PostgreSQL output and API;
- acceptable import, CPU, memory, depth, and output-size behavior;
- an exact dependency pin and accepted supply-chain review;
- lower expected maintenance cost than the handwritten option.

Failure of any mandatory gate means Phase 10 uses the handwritten MySQL
backend or defers MySQL. The spike must not weaken the contract to justify
SQLGlot.

## Evidence Gaps

Slice 4 intentionally leaves these questions open for the Phase 10 spike:

- the exact direct-constructor mapping for each Pietto IR node;
- MySQL string escaping and SQL mode behavior;
- whether SQLGlot can preserve Pietto's opaque dotted-name contract for the
  MySQL candidate;
- exact exception and warning surfaces from direct generation;
- import and resource costs under Pietto workloads;
- exact MySQL output and parenthesization;
- adapter maintenance cost versus a handwritten MySQL renderer;
- the exact release that would be proposed for production.

These gaps block adoption but do not block the limited spike decision.

## Explicit Non-Goals

Slice 4 does not add or implement:

- SQLGlot or another dependency;
- a SQLGlot adapter;
- a MySQL backend or `mysql.table`;
- `--dialect mysql`;
- a generic public SQL emitter;
- PostgreSQL backend changes;
- SQL transpilation;
- parser, semantic, IR, CLI, JSON, grammar, or generated-file changes;
- optimizer or executor use;
- SQL execution, database access, connector execution, or schema
  introspection;
- richer SQL features;
- project or multi-file behavior;
- runtime, Web UI, watch mode, or LSP/editor integration.

## Official References

- SQLGlot 30.9.0 package metadata:
  <https://pypi.org/project/sqlglot/30.9.0/>
- SQLGlot official README:
  <https://github.com/tobymao/sqlglot#readme>
- SQLGlot API documentation:
  <https://sqlglot.com/sqlglot.html>
- SQLGlot AST primer:
  <https://github.com/tobymao/sqlglot/blob/main/posts/ast_primer.md>
- SQLGlot dialect registry:
  <https://github.com/tobymao/sqlglot/blob/main/sqlglot/dialects/__init__.py>
- SQLGlot package metadata:
  <https://github.com/tobymao/sqlglot/blob/main/pyproject.toml>
- SQLGlot MIT license:
  <https://github.com/tobymao/sqlglot/blob/main/LICENSE>
- SQLGlot tag history:
  <https://github.com/tobymao/sqlglot/tags>
