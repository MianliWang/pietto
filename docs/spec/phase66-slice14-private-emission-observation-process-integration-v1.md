# Phase66 Slice14 Private Emission Observation And Process Integration v1

## Authority and scope

This contract delivers Phase66 route row 14 (R26, C29/C32, contributing E06/E08/E09)
under the [Phase66 route lock](phase66-dialect-sql-emission-product-phase-initiation-gate-route-lock-v1.md).
It adds a distinct private, versioned observation of the already-verified emission
artifact and the first real `phase66` differential process family. It adds no emitter,
lowering rule, renderer, verifier rule, public format, CLI flag, public Python export,
database case or receipt field. The public artifact (`pietto.sql-emission.v1`), the public
CLI, the complete verifier, the Slice12 inspection view, the Phase65 portable format and
the database target facility are read-only inputs.

## Marker and wire format

The private marker is `pietto.sql-emission-observation.v1`. A document is compact UTF-8
JSON with one final LF:

```text
{"format": MARKER, "root": ["artifact", 0], "records": [{"ref": [kind, index], "fields": {...}}, ...]}
```

`src/pietto/_project/project_sql_emission_portable_schema.py` owns the closed record
table: 73 record kinds, each with its exact ordered fields and a closed value type
(`nat`, `text`, `sql`, `bool`, `none`, `nullable`, `data`, `fixed`, `plan`, `subject`,
`scope`, typed local references `@kind|kind`, optional `?T`, list `*T`). A local reference
is `[kind, index]`; a retained plan reference is `{"kind", "position"}` over the closed
Phase65 plan reference kinds, and the plan scope is `{"kind": "selected_plan",
"position": 0}` as in the public artifact. Fixed values are `{"tag", "value"}` with Int as
decimal text, Float as finite binary64 hex (signed zero kept) and Bool/Text exact. Objects
inside `data` values have sorted keys and natural integers only.

Records are exactly the first-visit preorder from the root following reference fields in
schema order; each kind's index is its running count. One runtime object is one record;
equal content at distinct objects is distinct records. Object identity is used only by the
exporter's invocation-local index and never serialized. Product bytes carry no cwd, host
path, address, hash, random value, time, process id, hash seed or interpreter.

## Field ledger and cutoffs

Every emission-owned runtime dataclass maps to one record kind whose fields are its own
dataclass fields plus named derived upstream evidence, minus named cutoffs; a test checks
this against the live classes. Derived evidence: diagnostics; request owner, literal
policy, trusted module snapshots, target request target/issues, layout definitions/uses,
input blockers; owner module/kind/name; field logical type, effective nullability and
Decimal parameters; unary/operation operators (`is null` / `is not null` for NULL tests);
anchor tag; literal and fixed values; block kind; JOIN kind, ON reference and nulling JOIN
node positions; named-window policy; window binding policy/role/position; SET equivalence
requirement and fold; source-map entry role and associations; association source path,
site, location with availability, import path and access hop; original demand family,
subkind, subject and assessment outcomes. Cutoffs: the request's verification, report,
source-map, assessment and layout runtime roots and its private accepted-values cache are
represented by the records above; a bound field's upstream field, type resolution and
Decimal type-expression identities are represented by the facts the emission consumed.
Upstream plan records are retained plan references; association evidence objects and
AST node identities are not transported. Fields the admitted domain always leaves empty
(window origin definition, specification parent, ORDER/window NULL posture, result/SET
unit predicate/aggregation/window) are the closed type `none`.

## Runtime export and correspondence

`project_sql_emission_portable.export_emission_observation(artifact, request)` returns
`EmissionObservation(status, canonical_bytes)` with status `ok`, `invalid_root` (not the
exact runtime artifact and its own request, including decoded data), `unverified` (the
existing complete verifier rejects), `outside_schema` or `resource_limit`; only `ok`
carries bytes. It reads the artifact and invokes only the existing read-only verifier. A
non-VERIFIED emission outcome has no artifact and so no private document; its public
failure bytes stay the existing serialized failure.

`verify_emission_observation(document, artifact, request)` returns the ordered issues
(empty means corresponds). It parses through the pure boundary, reruns the existing
verifier, then walks the decoded document (never the exporter) binding each record to
exactly one runtime object and back, recomputing each derived field through the retained
plan, source map, report and assessment rather than the export path, and finally compares
the document with the existing public artifact projection (SQL, target, request, fixed
values, parameter uses, columns, range kinds/roles/subjects/offsets/origins, both
denominators and diagnostics) and with the Slice12 inspection view.

The existing complete verifier re-derives row blockers through its own realization step;
that inherited internal step is not an export or correspondence entrypoint. Preparation,
emission, AST building, rendering, parsing, plan building and export are never reached by
correspondence or pure decoding.

## Pure consistency

`project_sql_emission_pure_boundary` imports only the schema module.
`parse_emission_observation(bytes | str)` and `evaluate_emission_observation(mapping)`
return `Outcome(status, view, canonical_bytes, detail)` with statuses `ok`,
`invalid_input`, `invalid_utf8`, `invalid_json`, `duplicate_key`, `unknown_format`,
`invalid_document`, `invalid_record`, `invalid_field`, `invalid_value`, `invalid_ref`,
`invalid_relation`, `resource_limit`; a rejection has no view and no bytes and a bounded
constant detail. The raw route rejects duplicate keys at every depth (equal values
included), trailing data, invalid UTF-8, non-natural or oversized integer lexemes, JSON
floats and NaN before building containers beyond the limits. The parsed-mapping route
accepts only exact builtin containers, never calls user methods, rejects cycles, and is not
evidence that duplicate keys were absent before parsing.

Documented relations: target family/release, contract target, target request, literal
policy, empty input blockers and module snapshots; premise positions and JSON values;
source order, field ordinals and column collisions; query/request/rendered roots; unit
order, finality, `p{n}` unit symbols, `c{i}` terminal columns bound to terminals, and
producers before consumers; column ordinals and symbol positions; operation kinds,
operators and arity; anchor physical types per family and tag; acyclic value trees;
parameter claims, fixed-value slots, PostgreSQL slot-consistent `$n` reuse and MySQL
ordinal `?` indexes; tokens partitioning the SQL on UTF-8 boundaries; per-kind lexical
forms; closed syntax spellings; no comment-forming adjacency; balanced parentheses;
WITH-preamble structure and preamble-only roles; per-unit output label sequences; scope
aliases, column names, relation names and unit references bound to the document; bound
operator, quantifier, direction, frame, limit, sentinel, literal and parameter texts;
overlays aligned to token boundaries, opened and closed by their own subject, nested, and
reference/grouping/ORDER overlays bound to their port and read terminal; origins identical
per subject; SET positional alignment by reference identity, left fold and at least two
operands; outer null images nullable; C32 ORDER carrier consistency between an ORDER and
its items; one original entry per demand position in order with expression and filter
demands present for every serialized expression and predicate; and the generated
inventory re-enumerated independently from the serialized AST (kind, subject, rule,
multiplicity and order) with exact statement premise sets and scoped field premises.

The view is immutable and offers records by reference or kind, `at(offset)` (end of SQL
has no hit), `overlapping(start, end)` (an empty interval has none; an interior byte hits
its containing ranges) and `ranges_of(plan reference | origin reference)` returning every
token then overlay occurrence in retained order and rejecting a foreign reference.

Pure consistency is not authenticity: it cannot authenticate source history, recreate live
verification or certify a database, and a coherent alternative document (another real
observation, or a consistently rewritten ORDER carrier) passes it while failing
correspondence to the runtime roots it is offered for.

## Limits

Private codec limits only: document 32 MiB (at most the authorized 64 MiB; the public
artifact ceiling is 16 MiB and the private document adds the complete AST and token
sidecar); 1,048,576 raw JSON values counted before conversion; 131,072 records; 524,288
reference edges; nesting depth 32; 1 MiB per non-SQL text; SQL text 8 MiB (the emission
ceiling); natural integers up to 2^31−1 (10 digits); tagged Int text within signed 64 bits
(20 characters). A private limit yields a typed `resource_limit` without bytes and never
changes public emission. The measured corpus maximum is about 0.36 MB per document. The
process family's product is bounded to 8 MiB per request.

## Coverage

All 297 VERIFIED generation inputs (postgres150, mysql147) export, correspond and decode
with byte-identical canonical re-encoding, and together exercise every record kind. Outside
that corpus, real sources witness SET operands reading physical sources directly and an
expression-scoped premise; multi-hop path JOINs (the only source of predecessor JOIN inputs)
remain BLOCKED at admission and have no private document.

## Process family

The `phase66` family runs `tests/_pietto_phase66_sql_emission_differential_probe.py`
with ambient marker `PIETTO_PHASE66_SLICE14_AMBIENT` through the existing matrix route and
is not a CLI session family. Its `observation(workspace)` builds both dialects over eleven
real fixtures (imported direct chain, typed bound fixed values, nested EXCEPT, SEMI
membership, hidden QUALIFY windows, hidden grouping, the three ORDER carriers, one
INPUT_REJECTED and one BLOCKED outcome), exports, corresponds and decodes each VERIFIED
artifact and keeps each non-positive outcome only as its existing public failure bytes.
The support manifest adds `_pietto_phase66_sql_emission_probe.py` and
`_pietto_phase66_sql_emission_differential_probe.py`. A cell containing the family reports
`phase66_module_import_origins` for exactly the three new modules from the same child;
the Phase65 origin key keeps its meaning.

Per available supported interpreter the family adds six requests (checkout seeds
0/1/7/4294967295, relocated seed 7, installed seed 7) and no new cells: with both
interpreters 98 requests over 16 cells, with one 61 over 9; the historical 62/74/86
subsets are unchanged.

## Database domain

The target corpus stays 61 cases and 187 public documents per target (postgres154/4/29,
mysql151/4/32). No private document enters a receipt; receipt v2, the 32 MiB ceiling and
the console SHA-256 linkage are unchanged. The three new modules enter the package member
closure, so fresh target receipts are required for the candidate.

## Lifecycle

Phase66 remains `ACTIVE`; Slice14 completes only upon successful natural exact-head CI;
Slice15 (expanded target/differential/metamorphic conformance and historical
compatibility) is next and not implemented; Slice16 is audit-only. N66 remains 16 and the
package version remains 0.1.0.
