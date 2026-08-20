# Semantic Metadata Artifact v1

## 1. Status

This document is the normative contract for Semantic Metadata Artifact v1.
`pietto explain <file> [--format text|json]` implements the artifact without
changing parser, semantic, IR, SQL, CLI JSON v1, package, runtime, or database
behavior. Text and JSON are derived from the same normalized metadata fact
boundary.

## 2. Artifact Identity And Version Domain

The public artifact identity is:

```text
Semantic Metadata Artifact v1
```

Every JSON document in this artifact family uses:

| Field | Type | Value |
|---|---|---|
| `artifact` | string | `"Semantic Metadata Artifact v1"` |
| `schema_version` | integer | `1` |
| `command` | string | `"explain"` |

`schema_version: 1` is the Semantic Metadata Artifact v1 version domain. It is
separate from existing single-file CLI JSON v1 for `check` and `emit-sql`, and
separate from future project-level JSON v2. Semantic Metadata Artifact v1 is not
a mutation of CLI JSON v1 and is not the future project JSON v2 contract.

The approved future CLI direction remains:

```text
pietto explain <file> [--format text|json]
```

Text is the default future format. JSON is the normative future
machine-readable presentation and text output must be derived from the same
normalized artifact. Slice 2 does not implement the command or define the final
text layout.

## 3. Pipeline And Fail-closed Policy

Artifact v1 is emitted only after this future pipeline succeeds:

```text
parse
-> semantic analysis
-> existing IR construction
-> normalized metadata artifact
```

The explain pipeline must not invoke SQL lowering, connector execution,
database connections, SQL execution, or runtime behavior.

On parse failure, semantic failure, or IR failure, the JSON document contains
diagnostics/error information only. It must not expose partial definitions,
partial relations, partial schemas, partial projections, partial aggregates, or
partial lineage.

## 4. Top-level Success Envelope

Producer field order is:

```text
artifact, schema_version, command, ok, path, diagnostics, metadata
```

| JSON path | Type | Required | Nullability | Meaning |
|---|---|---|---|---|
| `$.artifact` | string | yes | non-null | Constant `"Semantic Metadata Artifact v1"`. |
| `$.schema_version` | integer | yes | non-null | Constant `1`. |
| `$.command` | string | yes | non-null | Constant `"explain"`. |
| `$.ok` | boolean | yes | non-null | `true` after parse, semantic analysis, and IR construction succeed without error diagnostics. |
| `$.path` | string or null | yes | nullable | User-supplied path posture via `str(path)`; `null` only when unavailable. |
| `$.diagnostics` | array | yes | non-null | Existing CLI JSON v1 diagnostic object shape, in compiler order. |
| `$.metadata` | object | yes | non-null | Normalized metadata payload. |
| `$.error` | absent | yes | n/a | Must not appear on success. |

## 5. Top-level Failure Envelope

Producer field order is:

```text
artifact, schema_version, command, ok, path, diagnostics, error
```

| JSON path | Type | Required | Nullability | Meaning |
|---|---|---|---|---|
| `$.artifact` | string | yes | non-null | Constant `"Semantic Metadata Artifact v1"`. |
| `$.schema_version` | integer | yes | non-null | Constant `1`. |
| `$.command` | string | yes | non-null | Constant `"explain"`. |
| `$.ok` | boolean | yes | non-null | Always `false`. |
| `$.path` | string or null | yes | nullable | User-supplied path posture via `str(path)`; `null` only when unavailable. |
| `$.diagnostics` | array | yes | non-null | Existing CLI JSON v1 diagnostic object shape, in compiler order. |
| `$.error.stage` | string | yes | non-null | One of `"parse"`, `"semantic"`, or `"ir"`. |
| `$.error.message` | string | yes | non-null | Stable summary of why metadata is unavailable. |
| `$.metadata` | absent | yes | n/a | Must be absent, not `null`, on failure. |

CLI process exit-code behavior is deferred to the later CLI integration slice.

## 6. Diagnostics Reuse

Artifact v1 reuses the existing CLI JSON v1 diagnostic object shape by
reference. The normative shape is documented in `docs/spec/cli-json-v1.md` and
implemented today by `src/pietto/cli_json.py::diagnostic_to_json_dict`.

Every diagnostic object has:

| Field | Type | Required |
|---|---|---|
| `code` | string | yes |
| `severity` | string | yes |
| `message` | string | yes |
| `location` | object or null | yes |
| `suggestion` | string or null | yes |

When `location` is non-null, it has `path`, `line`, `column`, `end_line`, and
`end_column`. Artifact v1 must not mutate CLI JSON v1, add JSON v1 fields,
remove JSON v1 fields, change JSON v1 field types, change JSON v1 severity
strings, change JSON v1 diagnostic ordering, or change JSON v1 schema version.

## 7. Metadata Payload

The success payload is:

| JSON path | Type | Required | Ordering | Source |
|---|---|---|---|---|
| `$.metadata.source` | object | yes | n/a | Artifact metadata. |
| `$.metadata.definitions` | array | yes | single-file source/IR definition order | IR-derived summary. |
| `$.metadata.sources` | array | yes | source definition order | IR-derived summary. |
| `$.metadata.relations` | array | yes | table/query definition order | IR-derived summary. |
| `$.metadata.types` | array | yes | first referenced order | Semantic/IR-derived summary. |

### Source Identity Object

`$.metadata.source` contains:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `path` | string or null | yes | Same path policy as the top-level `path`. |

There is no project root, project-relative path, canonical path, absolute path,
file digest, package version, or release field in Artifact v1.

### Definition Object

`$.metadata.definitions[]` contains:

| Field | Type | Required | Allowed values |
|---|---|---|---|
| `name` | string | yes | Source definition name. |
| `kind` | string | yes | `type`, `enum`, `shape`, `source`, `table`, `query`, `constraint`, or `derive`. |
| `location` | object or null | yes | Artifact source-location object. |

Definition objects expose public names, coarse kind, and source location only.
They must not expose raw AST node identity, raw `SemanticModel` shape, raw
`SymbolId`, raw `FieldId`, or raw IR nodes.

### Source Object

`$.metadata.sources[]` contains:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `name` | string | yes | Pietto source definition name. |
| `schema` | schema object | yes | Current row schema facts. |
| `location` | object or null | yes | Source definition location. |

Source objects do not expose connector arguments, connector configuration
values, credential-like values, secrets, raw connector structures, connector
execution behavior, or database connection behavior.

### Relation Object

`$.metadata.relations[]` contains:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `name` | string | yes | Relation name. |
| `kind` | string | yes | `table` or `query`. |
| `input` | object | yes | Immediate input relation summary. |
| `input_schema` | schema object | yes | Immediate input schema. |
| `output_schema` | schema object | yes | Relation output schema. |
| `projections` | array | yes | Projection order. |
| `query` | object | yes | Where, group, satisfying, order, and limit posture. |
| `aggregates` | array | yes | Aggregate calls in projection order. |
| `lineage` | array | yes | Basic direct-field lineage only. |
| `location` | object or null | yes | Relation definition location. |

`input.kind` is one of `source`, `table`, `query`, or `unknown`. Artifact v1 is
single-file only and does not define multi-file relation ordering.

### Schema And Field Objects

Schema objects contain `fields`, an array in existing row-field order.

Field objects contain:

| Field | Type | Required |
|---|---|---|
| `name` | string | yes |
| `type` | type object | yes |
| `nullability` | string | yes |
| `location` | object or null | yes |

`nullability` is one of `non_null`, `nullable`, or `unknown`. A field location
may be `null` for synthetic or declaration-less facts.

### Type Object

Type objects contain:

| Field | Type | Required | Allowed values |
|---|---|---|---|
| `status` | string | yes | `known` or `unknown` |
| `name` | string or null | yes | Type name, or `null` when unavailable |
| `kind` | string | yes | `builtin`, `type_alias`, `enum`, `shape`, or `unknown` |
| `canonical_name` | string or null | yes | Canonical type name, or `null` when unavailable |
| `canonical_kind` | string | yes | `builtin`, `type_alias`, `enum`, `shape`, or `unknown` |
| `nullability` | string | yes | `non_null`, `nullable`, or `unknown` |
| `support_posture` | string | yes | `current`, `limited_frozen`, `deferred_builtin`, `metadata_only`, or `unknown` |

Type encoding does not add new type semantics. `ValueTypeKind.UNKNOWN` is
encoded as `status: "unknown"` and does not collapse
`EffectiveNullability.UNKNOWN`. `Any` remains a known builtin with current
semantic posture. `Bytes` and `Json` are known builtins with
`support_posture: "deferred_builtin"`. `UUID` is a known builtin with
`support_posture: "limited_frozen"`. Enum fields use `kind: "enum"` with
`support_posture: "metadata_only"`. Decimal has no precision or scale fields.
Date and Timestamp have no timezone, literal, temporal arithmetic, precision,
native database metadata, or schema-introspection fields.

### Query Object

Relation `query` objects contain:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `where.present` | boolean | yes | Whether a where clause exists. |
| `group_keys` | array | yes | Field-reference objects in GROUP BY order. |
| `satisfying.present` | boolean | yes | Whether a result predicate exists. |
| `order_by` | array | yes | Order posture objects. |
| `limit` | object or null | yes | Static limit object, otherwise `null`. |

Order posture objects contain `scope`, `direction`, `expression_kind`, and
`field_leaves`. `scope` is `input` or `grouped_result`. `direction` is `ASC` or
`DESC`.

### Projection Object

Projection objects contain:

| Field | Type | Required |
|---|---|---|
| `name` | string or null | yes |
| `expression_kind` | string | yes |
| `type` | type object or null | yes |
| `field_leaves` | array | yes |
| `location` | object or null | yes |

`expression_kind` is one of `field_ref`, `aggregate_call`,
`bounded_expression`, `literal`, `call`, `predicate`, or `unknown`. Artifact v1
does not serialize raw expression trees.

### Aggregate Object

Aggregate objects contain:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `function` | string | yes | Aggregate function name. |
| `arguments` | array | yes | Empty for `count()`, otherwise expression summaries. |
| `result_type` | type object | yes | Semantic/IR result type. |
| `projection_name` | string or null | yes | Owning projection alias if any. |
| `location` | object or null | yes | Aggregate call location. |

`function` is one of `count`, `count_distinct`, `sum`, `avg`, `min`, or `max`.
Artifact v1 covers current aggregate facts only: `count()`, `count(field)`,
`count_distinct(field)`, `sum`, `avg`, `min`, `max`, bounded numeric aggregate
expressions, group keys, satisfying result predicates, and grouped result
ordering. Artifact v1 adds no aggregate functions and makes no SQL backend
acceptance claim for documented fail-closed risks such as Enum aggregate SQL
output.

### Basic Lineage Object

Lineage objects contain:

| Field | Type | Required |
|---|---|---|
| `output` | string or null | yes |
| `field_leaves` | array | yes |

Field leaves contain:

| Field | Type | Required |
|---|---|---|
| `relation` | string | yes |
| `field` | string | yes |
| `qualifier` | array of strings | yes |
| `location` | object or null | yes |

Basic lineage is limited to direct source relation and field provenance for
direct field projections, normalized direct field leaves used by currently
supported bounded expressions, and normalized direct field leaves used by
currently supported aggregate arguments.

Artifact v1 excludes raw `SymbolId`, raw `FieldId`, AST identity, raw IR nodes,
relationship traversal, JOIN lineage, multi-file lineage, graph lineage,
physical database lineage, runtime lineage, connector secrets, and raw
connector structures.

## 8. Ordering Contract

Artifact v1 is single-file only.

| Array | Ordering |
|---|---|
| `diagnostics` | Existing compiler diagnostic order. |
| `definitions` | Single-file source/IR definition order. |
| `sources` | Source definition order. |
| `relations` | Table/query definition order. |
| `schema.fields` | Existing row-field order. |
| `projections` | Projection order. |
| `group_keys` | GROUP BY item order after current semantic normalization. |
| `aggregates` | Projection order, then encounter order inside each projection. |
| `order_by` | Source order. |
| `lineage.field_leaves` | Deterministic first-encounter order within the owning expression summary. |

Object member order is producer guidance, not a compatibility guarantee. Array
order is part of the contract where listed above.

## 9. Path And Source-location Policy

Artifact v1 uses the existing user-supplied string / `str(path)` posture. It
does not canonicalize paths by default, promise absolute paths, promise
project-relative paths, or introduce project-root semantics.

Top-level `path`, `metadata.source.path`, diagnostic `location.path`, and nested
metadata locations all follow this posture. Path values may be `null` only when
the path is unavailable. Location objects must not fabricate `0:0` coordinates.

## 10. Excluded Fields And Non-goals

Artifact v1 excludes:

- relationship metadata;
- relationship traversal, grain, fanout, optionality, cardinality, or JOIN
  facts;
- SQL dialect or backend fields;
- a global per-program `deferred` field;
- connector secrets, connector arguments, connector configuration values, and
  raw connector structures;
- runtime, database, physical database, and schema-introspection metadata;
- project, workspace, or multi-file facts;
- JSON v2 fields;
- public MySQL API expansion;
- package version, release, tag, publish, upload, signing, or attestation data.

Phase 32 MVP does not add a public Python API. Slice 2 adopts no tooling and
does not change package metadata.

## 11. Compatibility And Evolution Policy

For `schema_version: 1`, removing or renaming fields, changing JSON types,
changing nullability, changing allowed values, changing field meaning, changing
fail-closed metadata absence, or exposing excluded fields is breaking and
requires a future Artifact schema version.

Additive fields may remain in `schema_version: 1` only when the field is
documented in this contract, covered by static audit, optional for consumers,
and does not change existing field meaning or fail-closed behavior.

Existing CLI JSON v1 remains unchanged. Future project-level JSON v2 remains
separate Phase 33 work and must not inherit Artifact v1 fields implicitly.

## 12. Contract Examples

The examples in this section are contract examples only. They are not current
CLI output.

Success example:

```json
{
  "artifact": "Semantic Metadata Artifact v1",
  "schema_version": 1,
  "command": "explain",
  "ok": true,
  "path": "examples/orders.pietto",
  "diagnostics": [],
  "metadata": {
    "source": {"path": "examples/orders.pietto"},
    "definitions": [{"name": "orders", "kind": "source", "location": null}],
    "sources": [
      {
        "name": "orders",
        "schema": {
          "fields": [
            {
              "name": "amount",
              "type": {
                "status": "known",
                "name": "Decimal",
                "kind": "builtin",
                "canonical_name": "Decimal",
                "canonical_kind": "builtin",
                "nullability": "non_null",
                "support_posture": "current"
              },
              "nullability": "non_null",
              "location": null
            }
          ]
        },
        "location": null
      }
    ],
    "relations": [],
    "types": []
  }
}
```

Failure example:

```json
{
  "artifact": "Semantic Metadata Artifact v1",
  "schema_version": 1,
  "command": "explain",
  "ok": false,
  "path": "bad.pietto",
  "diagnostics": [
    {
      "code": "PIE-P1000",
      "severity": "error",
      "message": "syntax error",
      "location": {
        "path": "bad.pietto",
        "line": 1,
        "column": 1,
        "end_line": null,
        "end_column": null
      },
      "suggestion": null
    }
  ],
  "error": {
    "stage": "parse",
    "message": "Semantic Metadata Artifact v1 metadata is unavailable because parsing failed."
  }
}
```

## 13. Slice 3 Handoff

Slice 3 may plan a private metadata model and builder that consumes parse,
semantic, and existing IR facts and emits a normalized internal artifact only
after the approved pipeline succeeds. Slice 3 must preserve the public/private
fact boundary in this contract and must not widen Artifact v1 without a
separate contract update.
