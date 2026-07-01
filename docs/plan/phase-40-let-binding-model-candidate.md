# Phase 40 Let Binding Model Candidate Decision

## Status And Trusted Handoff

Phase 40 Slice 1 is Let Binding Model Candidate Decision. Slice 1 is
docs/plan/static-audit/tests-only and implements no behavior change.

Phase 40 theme: `let:` binding model.

Trusted Phase 39 handoff:

- baseline HEAD: `2144b4912c7d75d138e6c3d838551b4ccf762bff`;
- baseline branch: `main`;
- baseline commit: `Complete Phase 39 count expression implementation audit`;
- latest completed phase: Phase 39 Count Family Implementation Candidate;
- package version remains `0.1.0`;
- no tag/release/publish/upload/signing/attestation is authorized by Slice 1.

Phase 39 completed the count-family implementation audit with
`count(expression)` support complete inside its approved boundary. Phase 40
starts from that trusted handoff and decides the next binding model direction
before any `let:` syntax, parser, AST, semantic, IR, SQL, CLI, JSON, fixture,
golden, package, workflow, or release behavior is authorized.

Slice 1 does not update `README.md`, `AGENTS.md`, or
`docs/spec/pietto-v0.9.md`; public status housekeeping remains future dedicated
work unless separately approved.

## Candidate Decision

The selected Phase 40 Slice 1 candidate is:

**Let binding model candidate and row-level expression reuse readiness**

Slice 1 chooses a behavior-preserving readiness boundary:

- record current relation body, scope, semantic, IR, and SQL facts relevant to
  reusable scalar expressions;
- choose explicit `let:`-style binding as the preferred direction;
- reject projection aliases as automatic reusable expression references;
- keep the first MVP row-level only;
- defer aggregate-level binding, post-aggregate expressions, `RelationLayerIR`,
  relationship/JOIN behavior, runtime/database execution, project/multi-file
  behavior, and public MySQL API expansion;
- define a ten-slice Phase 40 roadmap.

Slice 1 authorizes no source/compiler behavior change, source implementation,
grammar change, generated ANTLR change, parser or AST behavior change,
semantic behavior change, IR behavior change, SQL behavior change, CLI behavior
change, JSON v1 change, Project JSON v2 change, Semantic Metadata Artifact v1
schema or output change, diagnostic envelope change, SQL golden byte change,
fixture or golden change, example change, script change, workflow change,
package metadata change, lockfile change, package version change, tag, release,
publish/upload, signing, or attestation.

## Repo-Derived Let Binding Readiness

The current repository has enough expression and relation plumbing to plan a
future explicit row-level binding model, but not enough to implement it safely
in Slice 1.

| Area | Current repo-derived fact |
|---|---|
| Relation syntax | `grammar/Pietto.g4` uses one shared `tableBody` for both `table` and `query` definitions. The current order is `from`, optional `where`, optional `group by`, required `select`, optional `satisfying`, optional `order by`, optional `limit`. |
| Select aliases | `selectItem` confines `alias = expression` to projection output naming. Assignment is not a general expression form and Pietto source has no SQL-style expression `AS alias` syntax. |
| Source connector syntax | Source definitions retain the current `source users: User is postgres.table("public.users")` shape; Slice 1 does not introduce top-level `relation ...:` syntax or source `=` syntax. |
| AST shape | `TableDef` and `QueryDef` currently store `from_clause`, `where_clause`, `group_by_clause`, `select_items`, `order_by_clause`, `limit_clause`, and `satisfying_clause`. There is no `LetClause` or `LetBinding` AST node. |
| Row-level semantic scope | Current relation `where`, no-GROUP `select`, and input-scope `order by` expressions are typed against the input `RowSchema`, with the single-input qualifier available through the relation input name. |
| Projection alias scope | Projection aliases become output field names after projection. Projection aliases do not enter same-relation `where` or input-scope `order by` lookup, and must not become expression leaves by accident. |
| Result predicate scope | `satisfying:` has a separate selected-output-name scope, is GROUP BY-only, and is lowered as SQL `HAVING`. This is not the row-level expression environment. |
| Grouped order scope | Grouped `order by:` is result-scope selected-output-name ordering for selected group-key or aggregate outputs. It is not input-scope row-level ordering. |
| Semantic diagnostics | Current fail-closed behavior already includes `PIE-S2102` for unknown fields, `PIE-S2304` for unaliased computed projections, `PIE-S2305` for duplicate projection names, `PIE-S2308` for aggregate use in invalid contexts, `PIE-S2310` for aggregate projection composition, `PIE-S2311` for nested aggregates, `PIE-S2315` for deferred aggregate expression leaves, and `PIE-S2321` for unsupported grouped ordering. |
| IR shape | `RelationIR` currently has one relation layer with `filter`, `projections`, `row_schema`, `order_by`, `limit`, `group_keys`, and `result_predicate`. There is no `RelationLayerIR`, approved post-aggregate layer, hidden CTE model, or hidden subquery model. |
| SQL rendering | PostgreSQL and private MySQL renderers emit one relation SELECT with optional `WHERE`, `GROUP BY`, `HAVING`, `ORDER BY`, and `LIMIT`; they do not insert a post-aggregate subquery or CTE layer. |
| Relationship metadata | Relationship metadata remains metadata/readiness only and must not drive lookup, JOIN, IR, SQL, permissions, or runtime behavior in this phase. |

## Explicit Let Binding Rationale

Explicit `let:` binding is preferred over projection-alias reuse because it
preserves the current boundary between row-level expressions and output naming.

Projection aliases are public output field names. Reusing them as hidden input
variables would retroactively change existing same-relation `where`, no-GROUP
`order by`, aggregate argument, and output-schema contracts. It would also blur
two different scopes: row-level input expressions and result-level selected
outputs used by `satisfying:` and grouped result ordering.

An explicit `let:` section gives reusable row-level scalar expressions a
reviewed owner, source span, deterministic ordering, duplicate-name policy,
forward-reference policy, cycle policy, and lowering contract. It also keeps
projection syntax stable as `alias = expression` and avoids importing
SQL-style source `AS` aliases.

The recommended future syntax direction is a relation-body section shared by
`table` and `query` definitions:

```pietto
table order_totals:
    from orders
    let:
        gross = amount + tax
        normalized_status = lower(status)
    select:
        total_gross = sum(gross)
```

This example remains illustrative only. Slice 1 does not make it parse, does
not type it, does not lower it, and does not define final aggregate-argument
visibility.

## MVP Candidate Boundary

If a later slice separately approves `let:` implementation, the recommended
first MVP should start with these constraints:

- `let:` is row-level only;
- `let:` bindings are reusable scalar expressions;
- `let:` bindings are immutable within one relation body;
- `let:` bindings are source-ordered and deterministic;
- `let:` may appear only in the approved relation-body position selected by
  the Slice 2 contract;
- `let:` bindings may reference input fields and approved earlier row-level
  bindings only if Slice 2 explicitly approves that visibility;
- `let:` bindings must not reference later bindings;
- duplicate `let:` names fail closed;
- unresolved `let:` references fail closed;
- projection aliases must not become expression leaves;
- Projection alias syntax remains `alias = expression`;
- SQL-style expression `AS alias` source syntax remains unaccepted;
- top-level `relation ...:` source syntax remains unaccepted;
- `satisfying:` remains the result predicate surface; Pietto does not expose
  SQL `HAVING` as user syntax.

The MVP explicitly excludes:

- projection alias expression reuse;
- aggregate-level `let` binding;
- aggregate binding in `satisfying:`;
- post-aggregate expression composition;
- `RelationLayerIR`;
- hidden CTE insertion;
- hidden subquery insertion;
- nested aggregate composition;
- aggregate filters or SQL `FILTER (WHERE ...)`;
- `count_if(predicate)`;
- public MySQL API expansion;
- relationship-driven lookup or JOIN behavior;
- endpoint-qualified field lookup;
- relation composition;
- runtime/database execution;
- project/multi-file behavior;
- schema introspection or db pull behavior;
- policy/security DSL behavior;
- package version changes or release operations.

## Future Slice 2 Contract Questions

Slice 2 should answer these questions before any parser or behavior change:

- Does `let:` appear only after `from` and before `where`, or can later
  contracts allow additional positions?
- Are `let:` bindings allowed in both `table` and `query` definitions?
- Which clauses may see `let:` names: `where`, no-GROUP `select`, `group by`,
  aggregate arguments, `satisfying`, no-GROUP `order by`, grouped `order by`,
  and `limit`?
- May one `let:` binding reference earlier `let:` bindings?
- Are later references and cycles diagnosed with a new code or an existing
  fail-closed diagnostic family?
- May `let:` names shadow input fields, projection aliases, relation names, or
  other `let:` names?
- Are `let:` names bare-only, or can qualified references exist?
- Are source-qualified field leaves such as `orders.amount` accepted inside
  `let:` expressions under the current single-input qualifier rules?
- Are aggregate calls prohibited in all `let:` bindings for the MVP?
- Does SQL lowering inline `let:` expressions, introduce a private binding IR,
  or require an approved subquery/CTE model?
- How are expression type/nullability facts and metadata/explain output
  preserved without changing public schemas prematurely?

Recommended defaults for Slice 2 are conservative: one `let:` block after
`from`, row-level visibility only, no shadowing, no later references, no
aggregate calls, bare `let:` references only, current source-qualified field
leaves allowed, and stable SQL inlining unless a separate lowering contract
approves another shape.

## Phase 40 Slice Sequence

| Slice | Name | Slice posture |
|---:|---|---|
| 1 | Let Binding Model Candidate Decision | docs/plan/static-audit/tests-only; no behavior change |
| 2 | Let Binding Syntax And Scope Contract | docs/spec/static-audit first; no behavior change unless separately approved |
| 3 | Let Binding Parser And AST Surface | grammar/generated/parser/AST only for the approved syntax |
| 4 | Row-level Let Semantic Validation | semantic validation for names, ordering, duplicates, cycles, and row-level typing |
| 5 | Let Binding Semantic Model Storage | immutable semantic facts for approved bindings without public output widening |
| 6 | Let Binding IR Lowering MVP | IR lowering for approved row-level binding references and expression facts |
| 7 | Let Binding SQL Lowering MVP | PostgreSQL/private MySQL lowering for the approved IR subset with stable SQL output |
| 8 | CLI / JSON / Metadata Compatibility Hardening | preserve CLI JSON v1, Project JSON v2, and Semantic Metadata Artifact v1 compatibility |
| 9 | Let Binding Boundary Regression Matrix | regression matrix for projection aliases, aggregates, post-aggregate exclusions, and relationship/JOIN non-interaction |
| 10 | Completion Audit And Status Lock | audit/status; no new behavior unless a prior slice separately approved implementation |

Later phases or separately approved slices must handle aggregate-level binding,
post-aggregate expression layers, `RelationLayerIR`, subquery/CTE insertion,
relationship/JOIN-aware binding, project/multi-file binding, schema
introspection, and public API expansion.

## Slice 1 Public Surface Constraints

Slice 1 keeps public surfaces unchanged:

- source/compiler behavior unchanged;
- grammar and generated parser inventory unchanged;
- parser and AST behavior unchanged;
- semantic behavior unchanged;
- IR behavior unchanged;
- SQL behavior unchanged;
- CLI text output unchanged;
- CLI JSON v1 unchanged;
- Project JSON v2 unchanged;
- Semantic Metadata Artifact v1 unchanged;
- diagnostic envelope unchanged;
- SQL golden bytes unchanged;
- fixtures/goldens unchanged;
- examples unchanged;
- scripts/workflows unchanged;
- package metadata unchanged;
- package version remains `0.1.0`;
- no tag/release/publish/upload/signing/attestation.

Forbidden surfaces for Slice 1 are:

- `src/pietto/**`;
- `grammar/**`;
- generated parser files;
- `examples/**`;
- `fixtures/**`;
- golden files;
- `scripts/**`;
- `.github/workflows/**`;
- package metadata such as `pyproject.toml`, `uv.lock`, and version files;
- `README.md`;
- `AGENTS.md`;
- `docs/spec/pietto-v0.9.md`;
- release/tag/publish/upload/signing/attestation surfaces.

## Validation Plan And Gate 2 Allowlist

Approved Slice 1 Gate 2 file allowlist:

- `docs/plan/phase-40-let-binding-model-candidate.md`;
- `tests/test_phase40_let_binding_model_candidate.py`.

Validation should run exactly:

```bash
uv run pytest tests/test_phase40_let_binding_model_candidate.py
uv run pyright --project pyrightconfig.tests.json
uv run ruff format --check .
uv run ruff check .
git diff --check
```

If formatting fails only because of the approved Python test file, run:

```bash
uv run ruff format tests/test_phase40_let_binding_model_candidate.py
```

Then rerun the full validation list. Do not pass this Markdown plan file to
`ruff format`; Markdown formatting remains manual and evidence must record any
manual Markdown edits.

Gate 2 evidence should be written to
`/tmp/phase40-slice1-gate2-evidence.txt` and include baseline raw output,
changed file set, tracked diff stat/name-status where applicable, no-index
diff stat/name-status for the two new files, full tracked diff, full no-index
diffs, raw validation output, and final confirmations.

Gate 2 must not stage, commit, push, start or poll CI, tag, release,
publish/upload, sign, or attest.
