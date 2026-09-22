# Phase66 Slice12: Complete Emission Artifact, Dual-Denominator Closure And SQL-Range Queries v1

Slice12 delivers T12 of the Phase66 route. It adds no emitter, no operator, no
public format change and no target case. It completes and independently
re-verifies the existing emission artifact across the admitted Slice3–11 shapes,
closes original/generated requirement correspondence with grounded justification,
and exposes one private, immutable, artifact-bound inspection view with forward
and reverse SQL-range queries over the exact verified artifact. Every check is a
finite structural comparison over retained runtime objects; there is no proof
graph, SAT engine, callback registry or cache.

## Reused verification, not a second representation

| Obligation | Owner (unchanged) | What Slice12 adds |
| --- | --- | --- |
| Complete artifact (C23) | `EmissionArtifact`/`EmissionOutcome`, `prepared_current`, `verify_project_sql_emission`, `serialize_project_sql_emission` | the inspection factory runs the complete verifier and refuses malformed, stale, foreign and decoded-document roots; witnesses for fresh explicit target preparation over an unchanged neutral plan and for every graft class |
| Denominator A (C20, C31) | `verify_requirements` / `verify_row_requirements` bind every `plan.demands` entry by identity and rule | witnesses for single and coordinated removal, duplication, reordering and foreign subjects on the direct, multi-stage, row, JOIN, result and SET routes |
| Denominator B (C20) | the same verifiers rebuild the expected generated inventory from the actual CTEs, scans, columns, nodes, JOIN units, result bodies and SET units | witnesses that removal from the artifact list or from both lists is refused while the structure remains |
| Grounding (C21, C22) | `prepare_project_sql_emission` (same-scope declaration conflict `PIE-B1005 inconsistent_declared_scope`), `emission_blockers`, `text_comparison_domain_conflict`, `set_column_physical_representation_mismatch`, premise identity in the verifiers | witnesses that source-local valid differences (`max_characters`) are not a global conflict, that a cross-source operation must satisfy its own rule, and that the closed representation admits only direct accepted roots |
| Final bytes (C24) | `verify_sql_bytes` / `verify_row_bytes` re-derive the complete token partition and the overlay spans | witnesses for operator, identifier, SET quantifier, grouping, separator, parameter and comment-forming mutations with correct sidecars |
| Coordinates (C25) | rendering captures zero-based half-open UTF-8 byte offsets; the byte verifiers decode every token | independent prefix-byte oracle over quote/newline/non-BMP identifiers, JSON and parser coordinates kept separate, mid-codepoint endpoints refused |
| Parameters/results (E05) | `verify_parameters` / `verify_row_parameters`, positional public columns | the view exposes the retained positional final columns and the `(NativeUse, token range)` chain |

The closed requirement representation has only direct accepted roots: an
`OriginalRequirement` binds one retained report entry, a `GeneratedRequirement`
binds one actual AST/plan subject and a tuple of retained `Premise` objects from
the prepared request. It cannot express a requirement-to-requirement reference,
so no cycle is representable; substituting a copied premise, another
requirement, or an emptied tuple is refused by identity. This boundary is
verified directly rather than by inventing a general proof graph.

## Private inspection entrypoint

`pietto._project.project_sql_emission_inspection.inspect_project_sql_emission(artifact, request)`
returns an `EmissionInspection` or raises `ValueError`. It requires the exact
`EmissionArtifact` and the exact `PreparedEmission` it was produced from, runs
`verify_project_sql_emission`, and never calls emit, prepare, build, render,
serialize or any source/contract reopening. A decoded public document, a
foreign request, a stale artifact or any grafted component is refused.

The view is a frozen dataclass over retained objects:

| Field | Content |
| --- | --- |
| `artifact`, `request`, `verification` | the bound runtime objects and the `EmissionVerification` that admitted them |
| `sql` | the exact final UTF-8 bytes |
| `ranges` | `SQLRange(position, kind, role, subject, start, end, event, origins)`; every token event in byte order, then every expression overlay in its retained order; `origins` pairs each retained source-map entry with that entry's retained associations (import route, hop, site and parser location); scaffolding keeps an empty tuple |
| `original_requirements`, `generated_requirements` | the retained ordered denominators |
| `columns` | the retained positional columns of the final unit (the public visible tuple) |
| `parameter_uses` | `(NativeUse, SQLRange)` pairs in token order |

Query semantics:

| Query | Rule |
| --- | --- |
| `ranges_of(subject)` | `subject` must be the retained object itself: a key of the source map's subject index or the subject of an emitted range; returns every range whose subject is that object, in retained order; a valid subject with no emitted range returns `()`; a forged reference with equal kind and ordinal is `ValueError` |
| `ranges_of(origin)` | a retained `ProjectSQLSourceMapEntry` or an ORIGIN-kind plan reference; returns every range whose retained origins contain that entry |
| `at(p)` | `type(p) is int` and `0 <= p <= len(sql)`; hits satisfy `start <= p < end`; `p == len(sql)` has no hit; an interior byte of a multi-byte character hits its containing ranges |
| `overlapping(start, end)` | ints with `0 <= start <= end <= len(sql)`; `start == end` returns `()`; otherwise every range with `range.start < end and start < range.end` |
| invalid input | Bool, non-int, negative, beyond the buffer or a reversed interval is `ValueError`; parser coordinates and JSON offsets are never accepted as byte addresses |

Results are deterministic in retained rendering order: tokens before overlays,
each group in its retained order, all distinct occurrences preserved, nested and
repeated hits all returned. Construction is one pass over events, overlays and
their associations; every query is a bounded linear scan of `ranges` (no index
tree, no cache, no reconstruction per query).

## Installed consumer

The installed emission probe binds and checks the view inside the generation
child for every VERIFIED document before that record is exported: ranges,
columns, parameter uses and origin counts must correspond to the data-only
decoding, the parameter tokens and the first/last range must be found by forward
and reverse lookup, and end-of-buffer must have no hit. Any drift fails the
whole generation. The required same-child installed origins therefore include
`pietto._project.project_sql_emission_inspection`; the independent public decoder
remains data-only and imports no production construction or verification.

## Manifest denominator

Unchanged: 60 cases and 181 public documents per target.

| Target | VERIFIED | INPUT_REJECTED | BLOCKED |
| --- | ---: | ---: | ---: |
| PostgreSQL | 150 | 3 | 28 |
| MySQL | 147 | 3 | 31 |

## Changed-path and lifecycle lock

The grammar, generated parser, public legacy SQL emitter, the seven emission
modules and six operator emission modules, `pyproject.toml`, `uv.lock`, target
pins, Docker configuration, `.github/workflows/ci.yml`, `scripts/validate.py`,
upstream plan/report/source-map/assessment owners and the package version are
untouched. No skip, xfail or marker filter was added and no target case was
removed. Slice12 completion is not Phase66 completion.

```
Phase65 = COMPLETED
Phase66 = ACTIVE
Phase66 Slices1-12 = COMPLETED/PUBLISHED
Phase66 Slice13 = NEXT / NOT IMPLEMENTED
N66 = 16
```
