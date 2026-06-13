# Relationship Metadata Semantic Validation Version 1

## Status

Phase 15 Slice 1 is complete as a semantic-validation-only implementation.

Phase 14 introduced relationship metadata as parse-only AST storage. Phase 15
Slice 1 makes semantic analysis validate that metadata without adding it to
semantic definitions, Semantic IR, SQL, CLI formats, JSON schema, runtime, or
database behavior.

## Validation Rules

Semantic analysis applies these rules after collecting all current relation
symbols, so endpoint references may target relations declared later in the
same file:

1. Every endpoint `relation_name` must name an existing source, table, or
   query relation symbol.
2. Every relationship declaration name must be unique among relationship
   metadata declarations in the same script.
3. The two endpoint `local_name` values within one relationship must be
   distinct.

Relationship declarations remain outside `Script.definitions`. Their names
are not added to the type, callable, or relation namespace, and a relationship
name cannot be used as a relation input.

## Diagnostics

All implemented relationship metadata diagnostics have error severity and use
the existing semantic diagnostic construction and deterministic source-order
sorting:

| Code | Condition | Location |
|---|---|---|
| `PIE-S2601` | An endpoint references an unknown relation. | The complete relationship endpoint span. |
| `PIE-S2602` | A relationship name repeats an earlier relationship name. | The complete later relationship declaration span. |
| `PIE-S2603` | An endpoint local name repeats within one relationship. | The complete later endpoint span. |

No additional diagnostic code is reserved by this slice.

## Allowed Cases

The following remain valid:

- a self-relationship whose two endpoints reference the same relation and use
  distinct local names;
- an endpoint local name matching an existing relation, type, or callable
  name;
- a relationship name matching an existing relation, type, or callable name;
- multiple valid relationships referencing the same relations;
- forward references to existing relation declarations later in the file.

This slice does not introduce broader name ownership or ambiguity rules.

## Stage Boundary

| Stage or surface | Phase 15 Slice 1 behavior |
|---|---|
| Grammar, generated ANTLR, parser, and AST | Unchanged from Phase 14. |
| Semantic analysis | Validates relationship metadata using existing relation symbols. |
| Semantic model | Relationship metadata is not stored as a symbol or new semantic fact. |
| Semantic IR | Unchanged; relationship metadata is not lowered. |
| PostgreSQL and MySQL SQL | Unchanged; no relationship SQL is emitted. |
| CLI text and JSON | Formatting and schema are unchanged; JSON version 1 remains authoritative. |
| Runtime and database | No connection, execution, introspection, or authorization behavior is added. |

Existing programs without relationship metadata retain their semantic model
and diagnostic behavior.

## Non-Goals

Phase 15 Slice 1 does not implement or authorize:

- JOIN, relation composition, multiple relation inputs, or SQL lowering;
- relation-role semantics or endpoint-role enforcement beyond duplicate local
  endpoint names;
- cardinality, fanout, measures, dimensions, or aggregates;
- permission gates, runtime authorization, runtime security, or a threat
  model;
- database or connector execution, database connections, or schema
  introspection;
- JSON version 2, project mode, multi-file compilation, watch mode, LSP, Web
  UI, or a playground;
- SQLGlot or another dependency;
- a public MySQL emitter or generic public `emit_sql(...)`;
- release, publication, signing, upload, deployment, or attestation behavior.
