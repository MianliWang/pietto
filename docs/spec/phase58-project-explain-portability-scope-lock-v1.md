# Phase 58 Project Explain And Portability Scope Lock v1

## Answer And Authority

Phase 58 owns the public `Project Explain Artifact v1` direction. Its public
machine format marker is:

```text
pietto.project-explain.v1
```

The future invocation is additive to the existing `explain` command:

```text
pietto explain --project <root>
pietto explain --project <root> --format json
```

Slice 1 freezes architecture, public semantics, compatibility boundaries,
readiness, and the exact 12-Slice route. It adds no production model, marker
constant, CLI option, serializer, JSON schema, or portability calculation.

Candidate lifecycle state is:

```text
Phase 55: COMPLETED
Phase 56: COMPLETED
Phase 57: COMPLETED
Phase 58: ACTIVE
Slice 1: CURRENT
Slice 2: NEXT / UNSTARTED
```

Live Git plus successful natural exact-head CI owns Slice 1 completion. This
document does not authorize Slice 2, and no post-CI status-flip commit is
required.

## Artifact Identity And Existing Explain Compatibility

The two explain surfaces remain distinct:

| Surface | Human name | Machine identity | Command |
| --- | --- | --- | --- |
| Existing single-file | `Semantic Metadata Artifact v1` | `artifact = "Semantic Metadata Artifact v1"`, `schema_version = 1`, `command = "explain"` | `pietto explain <file> [--format text\|json]` |
| Future project mode | `Project Explain Artifact v1` | `pietto.project-explain.v1` | `pietto explain --project <root> [--format text\|json]` |

The existing single-file surface is exact zero-delta. Text remains its default
human-readable output. JSON remains its versioned machine output. A successful
single-file run returns exit `0`; parse, semantic, or IR diagnostic failure
returns exit `1`; input read or decode failure returns exit `2`. Its success
JSON contains `metadata`, while its failure JSON contains `error` and no
fabricated `metadata`. Existing serializers, ordering, paths, diagnostics,
streams, and tests remain authoritative.

Project mode is not `pietto explain-project`, `pietto explain-projects`, or a
new top-level command. Project Explain Artifact v1 does not modify, reinterpret,
or version-bump Semantic Metadata Artifact v1.

## Deterministic Snapshot Boundary

Project Explain Artifact v1 represents one deterministic compiler-analysis
snapshot. It is not live database, installation, server, filesystem discovery,
registry, network-resolution, or runtime state.

The snapshot may retain exact selected private authority including package,
target profile, catalog coordinate, catalog target, catalog content SHA-256,
source revision, and source locator. Those facts do not claim that a target or
extension is installed, available on a running server, or currently reachable.

## Independent Private Authority Composition

Phase 58 composes bounded public projections from three independent private
authorities:

```text
PackageInspectionFactSet
/ pietto.package-inspection.v1

CapabilityInspectionFactSet
/ pietto.capability-inspection.v1
+ PackageCapabilityCheckingMatrix

ExtensionCatalogInspectionFactSet
/ pietto.extension-catalog-inspection.v1
```

The architecture is:

```text
independent private authorities
-> explicit public projections
-> artifact-local cross-references
-> deterministic portability derivation
```

The public artifact does not merge or replace private fact ownership. Phase 58
must not create another package resolver, capability checker, catalog selector,
provider, or provenance graph.

## Public Requirement Model

The public conceptual model is exactly:

```text
REQUEST
-> RESOLUTION
-> RESULT
```

| Layer | Retained public meaning |
| --- | --- |
| `REQUEST` | Exact requirement occurrence, semantic `CapabilityKey`, exact declaring package, bounded requested-by/root context, and source order |
| `RESOLUTION` | Exact evaluated target, target/profile authority, selected catalog authority, catalog coordinate/target/content digest, selection outcome, and exact evidence references consulted where available |
| `RESULT` | Evaluation state, checked status when applicable, reason, and artifact-local evidence references |

Declaration, resolution, and installed/runtime state remain separate. Phase 58
does not add version solving, registry lookup, lockfiles, installation, or
environment mutation.

## Bounded Requirement Provenance

The v1 public projection supports this bounded explanation:

```text
root/project package
-> declaring package
-> requirement occurrence
```

It distinguishes `declared_by`, `requested_by`, package role, and exact
requirement position. Exact source occurrence order and multiplicity are
retained. It does not construct a transitive provenance graph or global
provenance node IDs.
Deterministic artifact-local positions and references are sufficient. Full
package graph, attribution, provenance, and lineage remain Phase 59 ownership.

## Explicit Evaluated Target Denominator

Every portability statement is qualified by one explicit ordered evaluated
target set retained in the artifact. The complete meaning is:

```text
portable over this exact ordered target set
with respect to these exact declared requirements
```

The artifact preserves target order, exact target identity, and how the
resolved set was obtained. The lower-level artifact builder consumes an
explicit resolved target set. A future CLI may derive a default from explicit
project declarations, but it must materialize the resolved set in the
artifact.

There is no implicit universal target set and no target range, `latest`,
nearest-target, compatibility expansion, ranking, or recommendation. An
unqualified `portable: true` is invalid.

## Normative Requirement By Target Matrix

The raw ordered requirement-by-target matrix is normative. Matrix order is
requirement source order by explicit target order.

Evaluation states are exactly:

| Evaluation state | Meaning |
| --- | --- |
| `UNDECLARED` | The requirement collection is not declared for checking |
| `BLOCKED` | Declared checking is blocked before a checked result exists |
| `CHECKED` | A canonical checked result exists |

A `CHECKED` cell has exactly one status:

| Checked status | Portability evidence |
| --- | --- |
| `SATISFIED` | Positive checked evidence |
| `UNSUPPORTED` | Definite compatibility gap |
| `ABSENT` | Definite compatibility gap |
| `UNKNOWN` | Indeterminate evidence |
| `CONFLICT` | Indeterminate evidence |

`UNDECLARED` and `BLOCKED` never become a fabricated checked `UNKNOWN`. The raw
state, checked status when present, exact reason, and evidence remain
inspectable. Portability is only a deterministic summary over that matrix.

## Portability Derivation

The public classification vocabulary is exactly:

```text
PORTABLE
NOT_PORTABLE
INDETERMINATE
```

Requirement-level rules over the explicit evaluated target set are:

| Condition | Classification |
| --- | --- |
| Non-empty target set and every cell is `CHECKED / SATISFIED` | `PORTABLE` |
| At least one cell is `CHECKED / UNSUPPORTED` or `CHECKED / ABSENT` | `NOT_PORTABLE` |
| Otherwise | `INDETERMINATE` |

A definite gap is sufficient for `NOT_PORTABLE` even when another cell is
`UNKNOWN`, `CONFLICT`, `UNDECLARED`, or `BLOCKED`. Those four forms do not erase
the gap and are otherwise indeterminate evidence.

An empty evaluated target set is `INDETERMINATE` with a bounded
no-evaluated-targets reason. Zero declared requirements over a non-empty
evaluated target set is `PORTABLE` with `requirements_evaluated == 0`.

Project-level rules are:

| Condition | Classification |
| --- | --- |
| Any requirement is `NOT_PORTABLE` | `NOT_PORTABLE` |
| Otherwise, any requirement is `INDETERMINATE` | `INDETERMINATE` |
| Otherwise | `PORTABLE` |

There is no `PARTIALLY_PORTABLE`, `MOSTLY_PORTABLE`, `BEST_TARGET`,
`WORST_TARGET`, target ranking, or recommendation.

## Public Evidence Posture

The v1 public evidence vocabulary is exactly:

| Evidence kind | Meaning |
| --- | --- |
| `SOURCE_FACT` | Retained upstream or authored source fact |
| `DETERMINISTIC_DERIVATION` | Provider result, matrix projection, or portability classification derived from exact authority |
| `UNAVAILABLE` | Required authority is undeclared or unavailable |
| `CONFLICTING` | Same-scope evidence conflicts without an arbitrary winner |

`REVIEWED_INTERPRETATION` is not a v1 evidence-kind member because Phase 58 has
no independent human-reviewed interpretation producer. A future schema may add
such a kind only with real authority and an explicit compatibility decision.

## Bounded Public Provenance

Public provenance is sufficient to answer:

- why the requirement exists;
- which target was evaluated;
- which exact private authority was selected;
- which evidence produced the result; and
- why a result is unknown, absent, unsupported, or conflicting.

It may retain package coordinate, requirement position, target position,
catalog coordinate, catalog target, catalog content digest, entry
matchability/exposure, source authority, source revision, source locator, and
provider reason/result through deterministic artifact-local references.

It does not expose Python object identity, inode/device identity, host absolute
paths, temporary paths, `cwd`, virtual-environment paths, or private
`source_reference` text as the sole provenance authority. It does not build the
Phase 59 graph, and artifact-local positions are not global IDs.

## Logical Paths And Privacy

Public project/package paths are logical only. Permitted domains are:

- project-relative paths;
- package-relative paths; and
- upstream source locators.

Forbidden public path identity includes host absolute paths, symlink-resolved
host paths, home directories, `cwd`, temporary directories, virtual-environment
paths, and device/inode identity. The artifact is relocation-stable.

## Success And Failure Envelope

Project Explain Artifact v1 uses one versioned top-level envelope for success
and failure. It distinguishes the exact format marker, a success Boolean,
ordered diagnostics, and an optional project-explain payload.

A parse, project, package, or semantic failure does not produce fabricated
partial success facts. Exact field names and the final nested shape belong to
later model and JSON slices; the single-envelope product decision is fixed.

## JSON Text And Schema Evolution

JSON is the stable public machine contract. It will require the exact format
marker, bounded enum vocabularies, deterministic ordering, stable field
semantics, deterministic UTF-8 serialization, compatible success/failure
envelopes, and golden plus differential tests.

Human-readable text is not a machine compatibility contract. It remains
semantically accurate and useful, but wording, spacing, headings, and wrapping
may evolve without a public schema-version change.

Within Project Explain Artifact v1, field removal, field rename, field type
change, required-field addition, existing enum semantic change, or existing
ordering semantic change is breaking and requires a new explicit marker or
version. Existing meanings are not silently widened or repurposed. The precise
optional-field policy belongs to the public JSON schema slice and must remain
conservative.

## Deterministic Ordering

Existing private semantic order remains authoritative:

| Public collection | Ordering |
| --- | --- |
| Packages | Existing private package-inspection authority order |
| Requirements | Exact source occurrence order |
| Targets | Explicit resolved target order |
| Matrix | Requirement order by target order |
| Catalog and evidence tables | Deterministic private/content-derived order |
| Source evidence | Retained source-occurrence order |

Semantic source order is not cosmetically sorted. Output does not depend on
dictionary, set, or object-allocation order.

## Later Readiness

| Phase | Retained readiness, not authorization |
| ---: | --- |
| 59 | Stable artifact-local package, requirement, target, catalog-evidence, and source positions can later become graph nodes and edges without being global IDs now |
| 60 | The request/resolution/result, status, reason, provenance, and portability model remains capability-domain agnostic, including future `WINDOW_FUNCTION` evidence |
| 64 | Type evidence retains exact structured type, unmodeled source spelling, and unmodeled reason without speculative array elements, typmods, vector dimensions, composite fields, coercion results, or promotion ranks |
| 69 | Database family/release, extension identity/release, catalog identity/release/content digest, and source revision/locator remain separately inspectable; there is no installed-extension field |

Phase 69 owns release-aware PostgreSQL core builtin signature catalogs,
backend-specific core catalog foundations, generated/multi-source extension
catalog assembly, extension-specific lowering, and additional dialect
foundations.

## Package Manager Lessons And Non-goals

Phase 58 adopts four mature package-manager lessons:

- request is distinct from resolution and installation;
- exact selected source, version, and content identity remains inspectable;
- users need a bounded explanation of why a requirement or result exists; and
- target/environment context affects resolution.

It does not add version ranges, compatible-release operators, `latest`, a
solver, lockfile, package or catalog registry, remote fetching, optional
requirement semantics, peer-dependency semantics, installation state, or
environment mutation.

## Exact 12-Slice Route

| Slice | Owner |
| ---: | --- |
| 1 | Architecture/scope/route lock; artifact identity; target denominator; single-file explain compatibility |
| 2 | Public common model and success/failure envelope; logical paths; evidence posture; request/resolution/result vocabulary |
| 3 | Package and requirement provenance projection; `declared_by`/`requested_by` |
| 4 | Public requirement/target compatibility matrix; evaluation states; five checked statuses and reasons |
| 5 | Public extension-catalog evidence projection; catalog coordinate/target/digest; selection; matchability/exposure; bounded provenance |
| 6 | Conservative requirement/project portability derivation |
| 7 | Cross-section composition; artifact-local references; integrity; deterministic ordering; authority separation |
| 8 | Public JSON v1 schema; deterministic serialization; success/failure envelopes; privacy and schema-evolution locks |
| 9 | `pietto explain --project` text/JSON integration; existing single-file explain zero-delta |
| 10 | Real multi-target E2E scenarios spanning package, capability, catalog, all evaluation states, and all checked result classes |
| 11 | Public pure/differential compatibility boundary; goldens; Python 3.12/3.13; hash seed; relocation; installed wheel |
| 12 | Completion audit; Phase 59 handoff; Phase 60/64/69 readiness reconciliation |

The phase may expand only through an explicit evidence-backed route update for
a genuine independent lifecycle, public compatibility boundary, or similarly
independent owner. Do not add padding, compress independent ownership, or
silently reorder the route. Current expansion candidate: `NONE`.

## Explicit Non-goals

Phase 58 does not authorize:

- universal portability, target recommendation/ranking, or best/worst target;
- database connections, live installation detection, `CREATE EXTENSION`,
  runtime catalog discovery, server OIDs, or runtime verification;
- package/catalog registries, remote loading, solvers, lockfiles, ranges, or
  dependency installation;
- public provenance or lineage graphs;
- array, typmod, vector-dimension, composite, coercion, or promotion semantics;
- SQL lowering or emitter changes;
- PostGIS, ltree, or TimescaleDB production support or package catalog assets;
- version bump, tag, GitHub Release, package publication, signing, or
  attestation.

## Slice 1 Change And Release Boundary

Slice 1 changes documentation and static tests only. Production source, CLI,
serializers, JSON contracts, public exports, package behavior, generated
artifacts, golden fixtures, dependencies, lockfile, and workflows remain
unchanged. The package and CLI version remains `0.1.0`.

Slice 2 remains `UNSTARTED / NOT AUTHORIZED`.
