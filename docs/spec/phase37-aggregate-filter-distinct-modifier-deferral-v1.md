# Phase 37 Aggregate Filter Distinct Modifier Deferral v1

## Status

Phase 37 Slice 7 is `Aggregate Filter / DISTINCT / Modifier Syntax
Deferral`. Slice 7 is docs/spec/static-audit plus parser/semantic
behavior-audit tests only.

Slice 7 authorizes no behavior change. It does not change source/compiler
behavior, grammar, generated ANTLR files, parser behavior, AST behavior,
semantic behavior, IR behavior, SQL lowering, CLI behavior, JSON v1, Project
JSON v2, Semantic Metadata Artifact v1, diagnostic envelope shape, SQL golden
bytes, fixtures/goldens, public status docs, scripts, workflows, package
metadata, lockfiles, package version, release operations, tags,
publish/upload, signing, or attestation.

Package version remains `0.1.0`.

## Current Accepted Distinct Aggregate Spelling

The current accepted distinct aggregate spelling is `count_distinct(...)`.
Generic SQL-style `count(distinct field)` is not Pietto source syntax and
remains deferred/prohibited.

Current accepted `count_distinct(...)` behavior remains the existing direct
field and lower/trim Text-chain surface:

- `count_distinct(field)`;
- `count_distinct(source.field)`;
- `count_distinct(lower/trim Text chain)` over exactly one `Text` field leaf.

Slice 7 does not change current PostgreSQL or private MySQL SQL rendering for
accepted `count_distinct(...)` forms.

## Current Row And Result Predicate Surfaces

Current row-level `where:` is not aggregate `FILTER`. It remains input row
filtering before grouping and is distinct from SQL `FILTER (WHERE ...)` inside
an aggregate call.

Current `satisfying:` is the only result-predicate user surface. It is not
generic SQL `HAVING` user syntax and is not aggregate filter syntax. Direct
aggregate calls inside `satisfying:` remain invalid and reuse existing
semantic diagnostics such as `PIE-S2308`.

Current grouped `order by:` is result-level selected-output-name ordering. It
is not aggregate internal ordering. Grouped result ordering remains
selected-output-name based and unsupported grouped order expressions continue
to fail closed through existing diagnostics such as `PIE-S2321`.

## Deferred And Prohibited Syntax

Slice 7 explicitly keeps these forms deferred/prohibited:

- aggregate filters / SQL `FILTER (WHERE ...)`;
- generic `DISTINCT` syntax such as `count(distinct field)`;
- aggregate internal ordering / `WITHIN GROUP`;
- window functions / `OVER (...)`;
- generic aggregate modifiers;
- `count(*)` source syntax;
- modifier-like aggregate arguments.

These forms require separate syntax, parser, semantic, IR, SQL portability,
diagnostic, public output, fixture/golden, and validation decisions before any
future implementation may be considered.

## Existing Failure Posture

Existing failure posture remains unchanged:

- parser syntax failures use existing parser diagnostics such as `PIE-P1000`;
- invalid aggregate contexts reuse existing semantic diagnostics such as
  `PIE-S2308`;
- grouped order expression misuse uses existing `PIE-S2321`;
- arity errors use existing `PIE-S2309`;
- aggregate projection composition remains `PIE-S2310`;
- nested aggregates remain `PIE-S2311`;
- aggregate projections requiring aliases remain `PIE-S2313`;
- deferred aggregate expression argument shapes remain `PIE-S2315`.

Slice 7 adds no diagnostic codes, changes no diagnostic wording, and changes no
diagnostic envelope shape.

## Public Surface Stability

Slice 7 keeps public surfaces unchanged:

- CLI JSON v1 unchanged;
- Project JSON v2 unchanged;
- Semantic Metadata Artifact v1 unchanged;
- diagnostic envelope unchanged;
- SQL golden bytes unchanged;
- fixtures/goldens unchanged;
- package version remains `0.1.0`;
- no tag/release/publish/upload/signing/attestation.

No grammar change, generated artifact change, SQL byte change, JSON schema
change, public API change, runtime/database behavior, release operation, or
package version change is authorized.
