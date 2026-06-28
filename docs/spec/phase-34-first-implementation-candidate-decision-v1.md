# Phase 34 First Implementation Candidate Decision v1

## Purpose

This specification records the Phase 34 Slice 6 first implementation candidate
decision for the future narrow JOIN parser/AST surface.

Slice 6 is docs/spec/static-audit/status-only work. It decides whether Phase 34
is ready for actual narrow JOIN parser/AST implementation, documents why
implementation is deferred, records current grammar/generated and AST/builder
baselines, locks implementation entry criteria, describes the smallest possible
future implementation surface as non-binding, and preserves forbidden compiler
surfaces.

This document does not implement JOIN, does not implement JOIN syntax, does not
implement grain syntax, does not change grammar, does not update generated
files, does not change parser behavior, does not add AST nodes, does not change
the semantic model, does not add semantic validation, does not add diagnostics,
and does not change IR, SQL, CLI, JSON, project, runtime, or database behavior.

## Relationship To Earlier Phase 34 Slices

Slice 1 established the Phase 34 boundary: relationship grain and narrow JOIN
are future work, narrow JOIN is later-slice only, and no JOIN implementation is
approved.

Slice 2 established relationship grain as a compile-time metadata contract
around endpoint row identity and cardinality expectations. Relationship grain
prerequisites remain required future inputs before any narrow JOIN acceptance.

Slice 3 established the future narrow JOIN source-shape and semantic contract:
one explicit relationship metadata edge, explicit query opt-in, one base
relation plus one joined endpoint, deterministic endpoint qualification,
required grain facts, PostgreSQL/MySQL parity, and fail-closed behavior. Final
JOIN syntax is deferred and requires a later approved slice.

Slice 4 established parser and AST readiness boundaries. Final token spelling,
grammar productions, AST class names/fields, parser behavior, and accepted
syntax remain deferred.

Slice 5 established semantic readiness boundaries. Future semantic work must
define relationship selection, endpoint ownership, field ownership, grain
requirements, unsupported fanout/cardinality behavior, backend capability
handling, and deterministic fail-closed diagnostics before implementation.

Slice 6 preserves those boundaries. It is a candidate decision and contract
lock, not an implementation slice.

## Candidate Decision

Phase 34 is not ready for actual narrow JOIN parser/AST implementation in
Slice 6. Implementation is deferred.

Current unsupported join-like syntax must remain unsupported unless a later
approved implementation slice changes it. Parser/AST acceptance without
semantic fail-closed behavior is unsafe.

Actual parser/AST implementation is not approved by Slice 6. Slice 6 only
locks the entry criteria and future implementation boundary.

## Current Grammar / Generated Baseline

The current grammar baseline is:

```antlr
relationshipDefinition
    : RELATIONSHIP identifier COLON NEWLINE NEWLINE* INDENT relationshipBody DEDENT
    ;

relationshipBody
    : NEWLINE* relationshipEndpoint NEWLINE* relationshipEndpoint NEWLINE*
    ;

relationshipEndpoint
    : ENDPOINT identifier COLON identifier NEWLINE
    ;

tableBody
    : NEWLINE* fromClause NEWLINE* whereClause? NEWLINE* groupByClause? NEWLINE* selectClause NEWLINE* satisfyingClause? NEWLINE* orderByClause? NEWLINE* limitClause? NEWLINE*
    ;

fromClause
    : FROM identifier NEWLINE
    ;
```

There is no accepted join production. There is no accepted grain syntax.

Any `grammar/Pietto.g4` change requires regenerating the tracked ANTLR outputs
under `src/pietto/generated/`. The tracked generated inventory includes
`Pietto.interp`, `Pietto.tokens`, `PiettoLexer.interp`, `PiettoLexer.py`,
`PiettoLexer.tokens`, `PiettoParser.py`, `PiettoVisitor.py`, and `__init__.py`.

`scripts/check_generated.py` must verify the generated inventory
byte-for-byte by regenerating into a temporary directory and comparing the
tracked files.

## Current AST / Builder Baseline

The current AST and builder baseline is:

- `TableDef`;
- `QueryDef`;
- `FromClause(source_name)`;
- `RelationshipMetadata`;
- `RelationshipEndpoint`;
- there is no join list;
- there is no endpoint scope;
- there is no relationship edge selection;
- there is no grain carrier;
- there is no multi-input field owner.

Current builder touchpoints for any future parser/AST implementation would
likely include `visitTableDefinition`, `visitQueryDefinition`, `_relation_body`,
and possibly `visitFromClause` or new visitor methods for a later approved
source-shape production. Slice 6 changes none of them.

## Implementation Entry Criteria

Actual parser/AST implementation may be considered only after all of these are
true:

- syntax shape is explicitly bounded;
- grammar diff is small;
- generated-file regeneration path is clear;
- AST carrier is minimal and private/internal enough;
- semantic behavior remains fail-closed;
- no IR/SQL/CLI/JSON/project behavior changes are needed;
- no fixtures/goldens are needed;
- no diagnostic code additions are needed, unless separately approved;
- existing Phase 33 and Phase 34 tests remain untouched.

If any criterion is not met, implementation must remain deferred.

## Smallest Possible Future Implementation Surface

A future minimal parser/AST implementation surface could involve:

- `grammar/Pietto.g4`;
- tracked generated ANTLR files under `src/pietto/generated/`;
- `src/pietto/ast_nodes.py`;
- `src/pietto/ast_builder.py`;
- new Phase 34 parser/AST tests.

This future surface is non-binding and not approved by Slice 6.

That future implementation surface must not include semantic source, IR, SQL,
CLI, JSON, fixtures, goldens, scripts, package metadata, dependency, workflow,
release, tag, publish, upload, signing, or attestation surfaces unless a later
approved slice explicitly changes the boundary.

## Parser / AST Implementation Risks

Parser/AST implementation remains risky because:

- final token spelling is still deferred;
- final grammar productions are still deferred;
- final AST class names/fields are still deferred;
- parser acceptance can change failure mode from `PIE-P1000` parse failure to
  semantic rejection;
- semantic rejection would require approved diagnostics and fail-closed
  validation;
- generated-file hash/status locks may churn;
- parser span/order diagnostics can affect CLI outputs.

Slice 6 therefore does not approve parser acceptance for any JOIN-like syntax.

## Semantic Fail-closed Requirements Before Implementation

Before a later parser/AST implementation slice accepts any narrow JOIN source
shape, separately approved semantic work must define:

- relationship selection validation;
- endpoint ownership validation;
- endpoint qualification validation;
- grain prerequisites;
- unsupported fanout/cardinality behavior;
- self-relationship disambiguation;
- duplicate field owner behavior;
- backend capability handling;
- deterministic diagnostics before IR or SQL.

Parser/AST acceptance without these fail-closed requirements is unsafe.

## Current Behavior Preservation

Unsupported join-like syntax remains unsupported. Relationship metadata remains
metadata-only. Relationship metadata is not lowered to IR/SQL.

Current single-input relation behavior remains unchanged. `RelationIR` remains
single-source. PostgreSQL/MySQL render one `FROM` input.

CLI JSON v1 is unchanged. Project JSON v2 is unchanged. Semantic Metadata
Artifact v1 is unchanged.

## Phase 33 Project / JSON Preservation

Slice 6 preserves Phase 33 project/JSON boundaries:

- `pietto check --project ROOT` remains root/config-only;
- project source selection remains deferred;
- TOML schema parsing remains deferred;
- glob expansion remains deferred;
- project source parsing remains deferred;
- multi-file semantic analysis remains deferred;
- project JSON v2 remains check root/config-only;
- project emit-sql remains rejected;
- project explain remains rejected;
- project metadata aggregation remains deferred;
- single-file `pietto check --format json` remains JSON v1;
- single-file `pietto emit-sql --format json` remains JSON v1;
- single-file `pietto explain --format json` remains Semantic Metadata
  Artifact v1.

## Explicit Non-goals

Slice 6 does not implement or authorize:

- grammar changes;
- generated parser changes;
- AST changes;
- parser behavior changes;
- semantic model changes;
- semantic validation;
- diagnostic code additions;
- IR changes;
- SQL backend changes;
- CLI behavior changes;
- JSON v1 or JSON v2 behavior changes;
- Semantic Metadata Artifact v1 changes;
- fixtures/goldens changes;
- scripts changes;
- package metadata, package version, dependency, or workflow changes;
- JOIN implementation;
- JOIN syntax implementation;
- grain syntax implementation;
- grain semantic storage;
- relationship graph traversal;
- relationship chaining;
- automatic join inference;
- SQL execution;
- runtime security;
- runtime behavior;
- database/schema introspection or db pull;
- project source selection;
- TOML schema parsing;
- glob expansion;
- multi-file semantic analysis;
- project emit-sql;
- project explain;
- project metadata aggregation;
- graph/ERD/AI metadata export;
- release/tag/publish/upload/signing/attestation behavior.

No package version change is made by Slice 6. Package version remains `0.1.0`.
No tag/release/publish/upload/signing/attestation is performed by Slice 6.

## Implementation Boundary

This spec does not change grammar, generated files, AST, parser behavior,
semantic model, semantic validation, diagnostics, IR, SQL, CLI, JSON, fixtures,
goldens, scripts, package metadata, dependencies, workflows, public API,
project behavior, runtime behavior, or database behavior.

This spec does not define final JOIN syntax, final grain syntax, final AST
fields/classes, diagnostic codes, IR shape, SQL join kind, SQL alias
generation, or SQL lowering.
