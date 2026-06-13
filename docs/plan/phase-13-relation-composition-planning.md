# Phase 13: Relation Composition And Relationship Planning

## Status

**Phase 13 relation composition and relationship planning has started.**

**Slice 1: Master Plan And Baseline Audit is complete.**

**Slice 2: Relationship / Relation Role Contract is complete.**

Slices 3 through 6 are planned only and are not authorized for production
implementation. Phase 12 SQL Feature Expansion I is complete. Slices 1 and 2
add only planning documents, focused static audits, and scope-aware status
documentation. They change no grammar, generated ANTLR content, production
compiler code, SQL output, CLI behavior, JSON schema, public API, dependency,
package metadata, version, or golden fixture.

Phase 13 is planning-only unless a later slice receives separate explicit
authorization that changes that boundary. The current phase does not
implement JOIN, relationship declarations, relation roles, permission gates,
or runtime security behavior.

## Phase 13 Goal

Define cautious contracts for future relation composition and relationship
planning before any syntax or compiler implementation is considered.

The design must:

- preserve Pietto as a readable semantic SQL authoring language rather than a
  generic SQL builder;
- preserve explicit, selected-dialect SQL lowering and fail-closed compiler
  behavior;
- distinguish input relations, output relations, declared relationships, and
  any future relation role or authority model;
- study relation-as-gateway or relation-as-checkpoint semantics without
  claiming runtime enforcement;
- define how query context could eventually match relationship authority or
  purpose without confusing compiler checks with database authorization;
- settle name resolution, row-schema, cardinality, diagnostics, backend, and
  security boundaries before implementation.

Relationship declarations, relationship endpoints, endpoint roles, relation
roles, relation-as-gateway semantics, authority, purpose, and query context
are conceptual planning vocabulary only. They are not current Pietto syntax,
keywords, reserved words, runtime capabilities, or security guarantees.

## Non-goals And Hard Boundaries

Phase 13 Slice 1 must not:

- change `grammar/Pietto.g4` or generated ANTLR files;
- change parser, AST, semantic, IR, SQL backend, CLI, JSON, scripts, CI, or
  any other production code;
- implement JOIN, relationship declarations, relation roles, relationship
  gates, relation gates, or permission matching;
- implement GROUP BY, aggregate functions, HAVING, CTEs, subqueries, unions,
  windows, or other SQL feature expansion;
- implement runtime database permissions, database roles, row-level security,
  masking, security barriers, or capability tokens;
- execute SQL, connect to a database or connector, or introspect schemas;
- implement project mode, multi-file compilation, or `pietto.toml`;
- implement JSON v2 or change JSON v1;
- add SQLGlot or any other dependency;
- expose the MySQL emitter publicly or add a generic public `emit_sql(...)`;
- turn Pietto into a generic SQL builder;
- change golden fixtures, package metadata, package version, or public APIs.

Future Phase 13 slices remain planning and contract slices unless a separate
explicit decision authorizes production work. A slice title that discusses a
relationship, JOIN, security boundary, or SQL shape does not itself authorize
that capability.

## Current Baseline

The preserved Phase 12 baseline is:

- single-file `.pietto` parsing, semantic analysis, immutable Semantic IR, and
  explicitly selected PostgreSQL or MySQL SQL generation;
- static `postgres.table(Text)` and `mysql.table(Text)` sources;
- `table` and `query` relation definitions;
- one relation input through `from`;
- optional row filtering through `where`;
- projection through `select`;
- input-scope `order by:` after `select`, where projection aliases are not
  visible;
- optional static integer `limit <integer>`;
- supported-feature parity between the PostgreSQL and MySQL backends;
- CLI text and JSON schema version 1 presentation through `pietto check` and
  `pietto emit-sql`;
- public `pietto.sql.emit_postgres_sql` and private
  `pietto.sql.mysql.emit_mysql_sql`;
- no generic public `emit_sql(...)`;
- 15 reviewed golden files under `tests/fixtures/golden`, with historical
  golden bytes preserved and audited by the existing golden policy.

This baseline does not include multiple relation inputs, JOIN, relationship
metadata, output-schema ordering, runtime authorization, SQL execution, or
database enforcement.

## Why Phase 13 Must Be Planning-First

Relation composition crosses compiler and security-sensitive boundaries that
cannot be safely inferred from surface syntax alone:

- name resolution must distinguish relations, relationship names, input
  fields, projected fields, and any future role names;
- row schemas must remain deterministic before and after composition;
- cardinality affects result shape and whether composition can multiply rows;
- join fanout can silently change counts, uniqueness, and downstream meaning;
- SQL lowering must preserve the same semantics in PostgreSQL and MySQL;
- diagnostics must identify the owning declaration and source span without
  cascades or backend-dependent ambiguity;
- future policy checks must remain distinct from runtime database enforcement;
- a relation-as-gateway model could accidentally imply authority that the
  compiler cannot enforce;
- unsafe or unsupported composition must fail closed instead of emitting
  approximate SQL.

Phase 13 therefore contracts concepts, scope, lowering, diagnostics, and
security boundaries before any grammar or production implementation.

## Conceptual Design Areas

The following are planning concepts only:

- **Relation composition**: how a future query could combine more than one
  relation while keeping data flow explicit.
- **Relationship declaration**: whether and how named relationships could
  describe allowed composition independently from physical SQL syntax.
- **Relation role, authority, and purpose**: whether a relation could declare
  an intended use or access context without becoming a runtime permission
  system.
- **Relation as gateway or checkpoint**: whether composition could be required
  to pass through reviewed semantic relations, while recognizing that this is
  not database enforcement.
- **Composition risk controls**: how future contracts could reject ambiguous,
  fanout-prone, or unsupported combinations and fail closed.
- **Query context matching**: how a future query's context could be checked
  against relationship authority or purpose at compile time.
- **Input relation versus output relation**: how field visibility and schema
  ownership change across a composition boundary.
- **Cardinality**: how one, many, one-to-many, and many-to-one concepts affect
  schema and fanout analysis.
- **Semantic versus runtime permission**: which guarantees belong to the
  compiler and which require database or deployment enforcement.
- **SQL-lowerable invariant**: how every executable core semantic operation
  remains representable as explicit selected-dialect SQL.
- **Fail-closed backend behavior**: how unsupported or unsafe lowering
  eventually produces diagnostics rather than partial or approximate SQL.

No names in this section define accepted Pietto syntax, final grammar terms,
keywords, reserved words, or a public interface.

## Proposed Phase 13 Slices

1. **Master Plan And Baseline Audit**: complete. Record the Phase 12 baseline,
   planning-only boundary, six-slice sequence, and static compatibility locks.
2. **Relationship / Relation Role Contract**: complete. The normative
   planning-only contract is
   `docs/spec/relationship-relation-role-contract-v1.md`. It defines
   conceptual terminology, cardinality, authority, SQL-lowering, and explicit
   non-enforcement boundaries. It defines no currently accepted Pietto syntax
   and adds no implementation.
3. **Composition Scope And Name Resolution Contract**: planned only. Define
   future input/output schemas, qualification, ambiguity handling, and
   deterministic scope rules without implementation.
4. **Join / Composition SQL Shape Contract**: planned only. Define possible
   explicit SQL-lowering shapes, dialect parity, fanout treatment, and
   fail-closed cases without implementing JOIN.
5. **Security Boundary And Diagnostics Contract**: planned only. Define the
   separation between compiler semantics and runtime enforcement plus future
   diagnostic ownership without security implementation.
6. **Completion Audit And Documentation**: planned only. Audit the planning
   contracts, status documents, compatibility boundaries, and continued
   absence of production implementation.

These are planning and contract slices. A future explicit decision must
authorize any grammar, compiler, backend, CLI, JSON, dependency, public API,
runtime, or database change.

## SQL-Lowerable Invariant

Every future executable Pietto query must lower to explicit SQL artifacts for
the explicitly selected and supported dialect. Core query semantics must not
depend on hidden runtime post-processing, connector execution, in-memory row
combination, or an implicit authorization service.

If a future feature cannot be represented safely and consistently for a
selected dialect, the compiler should fail closed with ordered diagnostics.
It must not silently omit semantics, approximate cardinality, or emit SQL for
only the supported subset of a relation.

## Security Boundary Notes

A relationship gate, relation gate, or relation-as-checkpoint model is a
future design possibility only. Compiler planning is not database
enforcement, and runtime authorization is not implemented. Pietto currently
does not provide access control, privacy enforcement, authorization,
row-level security, masking, policy isolation, or safe data sharing.

Database roles, row-level security, safe views, masking, security barriers,
capability tokens, deployment policy, and runtime identity are future areas.
Phase 13 must not claim financial-grade safety or treat syntax as an access
control boundary. Any future safety claim would require a reviewed protocol,
CI/CD controls, database-level enforcement, deployment assumptions, and a
separate threat model in addition to compiler syntax and semantic checks.

## Diagnostic Planning

Future diagnostics must remain structured and use the existing canonical
families:

- `PIE-Pxxxx` for parser, lexer, and indentation diagnostics;
- `PIE-Sxxxx` for semantic diagnostics;
- `PIE-Ixxxx` for IR construction diagnostics;
- `PIE-Bxxxx` for backend capability diagnostics.

Phase 13 Slices 1 and 2 introduce no diagnostic codes. Later contracts may
reserve or describe future diagnostics only after assigning responsibility to
the correct compiler stage, defining source-span ownership, avoiding cascades,
and preserving deterministic order.

## Backend Planning

Any future supported composition feature must preserve PostgreSQL/MySQL
supported-feature parity within an explicitly authorized implementation
slice. Both backends must consume `ScriptIR`, remain isolated from parsing and
semantic analysis, and fail closed for unsupported capability.

PostgreSQL remains the public reference backend. The MySQL emitter remains
private to `pietto.sql.mysql` and explicit CLI dispatch. Phase 13 does not add
a public generic `emit_sql(...)`, a backend registry, SQLGlot, or any new
dependency.

## Audit Checklist

Each future Phase 13 slice must verify:

- no grammar or generated-file change unless explicitly authorized;
- no production implementation unless explicitly authorized;
- no dependency, lockfile, package metadata, or version change;
- no public API or MySQL emitter export expansion;
- focused tests are added before or with the authorized artifact;
- status, plan, and contract documentation are updated;
- the authoritative validation commands are run;
- targeted searches cover prohibited syntax, runtime, security, and API
  markers;
- the complete diff, including untracked files, is inspected before commit;
- PostgreSQL/MySQL parity and fail-closed behavior remain explicit;
- JSON v1, CLI, golden, and compiler-stage boundaries remain unchanged unless
  separately authorized.

Slice 2 validation includes:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pytest tests/test_phase13_planning_audit.py tests/test_phase13_relationship_role_contract.py
uv run pytest
uv run python scripts/validate.py
uv run python scripts/check_generated.py
uv run python scripts/check_goldens.py
uv run python scripts/package_smoke.py
uv run pyright
uv run pyright --project pyrightconfig.tests.json
uv lock --check
git diff --check
```
