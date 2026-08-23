# Phase 57 Slice 9 pgvector 0.8.6 PostgreSQL 18 Catalog v1

## Purpose And Authority

Phase 57 Slice 9 establishes the first private production extension catalog:
pgvector release `0.8.6` for one exact PostgreSQL `18` target. The catalog is
static, immutable, offline, non-executable, and constructed only from the
pinned upstream evidence below through the frozen Slice 2–8 contracts.

This catalog neither proves installation nor declares itself available. It
adds no registry, package asset, runtime lookup, database probe, SQL lowering,
or public output.

## Immutable Upstream Evidence

Upstream repository:

```text
pgvector/pgvector
```

The lightweight Git tag `v0.8.6` resolves directly to peeled commit:

```text
8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c
```

The commit date and the first changelog heading are `2026-07-29`. The exact
upstream Git blobs are:

| Path | Git blob SHA |
|---|---|
| `vector.control` | `02e761f5e06ef1f951418d405bdadc78963146ae` |
| `CHANGELOG.md` | `9b955419f06891536da3c067e747951f70463bb2` |
| `README.md` | `a7d4855c4f35cc3722b0248570f5f0cbc9936ce4` |
| `sql/vector.sql` | `7fc36712b31dc3b58d6c0c5caa8fa6097f30471d` |

`vector.control` declares `default_version = '0.8.6'`. The pinned README
states Postgres 13+ support, uses `v0.8.6` installation sources, explicitly
includes PostgreSQL 18 build/image targets, and enables the extension with
`CREATE EXTENSION vector`. Only the peeled commit content was inventoried;
upstream master and post-release migration content were not retrieved or used.

## Exact Catalog Coordinate And Target

The private Pietto catalog coordinate is:

```text
namespace: pietto.postgresql
name: pgvector
catalog release: 1
```

Its exact target is:

```text
database family: PostgreSQL
database release: 18
extension identity: vector
extension release: 0.8.6
```

`pgvector` is the upstream product/catalog name. `vector` is the exact
PostgreSQL extension identity established by `vector.control` and
`CREATE EXTENSION vector`. They are not aliases. No PostgreSQL 13–17 catalog,
release range, or compatibility inference is created.

## Ordered Source Provenance

The catalog contains exactly four source occurrences. Every occurrence uses
`github.com/pgvector/pgvector` as source authority and the exact peeled commit
as source revision.

| Position | Locator | Curation |
|---:|---|---|
| 0 | `vector.control` | `extension identity and release metadata` |
| 1 | `CHANGELOG.md` | `release history` |
| 2 | `README.md` | `PostgreSQL support and user-facing surface` |
| 3 | `sql/vector.sql` | `extension SQL declarations` |

Every entry cites SQL source position 3. Native types, aggregates, and the 26
README-documented direct scalar functions additionally cite position 2 where
it materially establishes user-facing exposure. No host path, temporary path,
timestamp, or downloaded source content enters the artifact.

## Reviewed Upstream Declaration Inventory

An external statement scanner enumerated complete semicolon-terminated
declarations and retained source section boundaries. Its output was manually
reconciled against all 918 lines of pinned `sql/vector.sql`, including each
type, function, aggregate, operator, cast, access-method, and operator-class
section.

Raw supported-family inventory:

| Upstream declaration | Raw count | Semantic catalog entries |
|---|---:|---:|
| `CREATE TYPE` | 6 shell/final statements | 3 native types |
| `CREATE FUNCTION` | 114 | 114 scalar functions |
| `CREATE AGGREGATE` | 4 | 4 aggregates |
| `CREATE OPERATOR` excluding classes | 40 | 40 operators |
| `CREATE CAST` | 23 | 23 casts |
| Total | 187 syntax declarations | 184 semantic entries |

The shell and completed definitions for `vector`, `halfvec`, and `sparsevec`
collapse to one semantic native-type entry each. There is no other supported-
family declaration delta.

Intentionally excluded non-entry categories are exactly 24 operator classes,
2 access methods, 2 COMMENT statements, and the psql load guard. Access-method
and operator-class helper `CREATE FUNCTION` declarations remain included as
scalar-function `IMPLEMENTATION_SUPPORT` entries.

## Production Inventory

The production artifact contains exactly 184 entries:

| Family | Count |
|---|---:|
| `NATIVE_TYPE` | 3 |
| `SCALAR_FUNCTION` | 114 |
| `AGGREGATE` | 4 |
| `OPERATOR` | 40 |
| `CAST` | 23 |

Matchability:

```text
EXACT_MATCHABLE: 131
CATALOGED_UNMODELED: 53
```

Exposure:

```text
DIRECT_SQL_SURFACE: 96
IMPLEMENTATION_SUPPORT: 88
UNCLASSIFIED: 0
```

Unmodeled-reason incidence is:

```text
UNSUPPORTED_TYPE_FORM: 37 entries
POLYMORPHIC_OR_PSEUDO_TYPE: 19 entries
```

Three `cstring[]` typmod functions retain both reasons, so reason incidence is
not an entry partition. All 131 exact lookup groups are `UNIQUE`; there are no
`CONSISTENT_DUPLICATE` or `EVIDENCE_CONFLICT` groups.

## Native Types And Physical Spelling

The exact extension-native types are:

```text
vector
halfvec
sparsevec
```

All use exact owner `vector` and `logical_mapping = None`. Shell/final type
syntax is one semantic type. No `vector(3)`, `vector(n)`, `halfvec(n)`, or
`sparsevec(n)` atomic identity exists. Parameterized native usage is retained
as concrete Phase 64 typmod readiness, not modeled here.

Exact PostgreSQL builtin spelling is preserved as authored, including `int`
versus `integer`, `bool` versus `boolean`, and `float8` rather than a rewritten
`double precision`. Array spellings such as `integer[]`, `real[]`,
`double precision[]`, and `numeric[]` remain exact unmodeled source text.

## Exposure Curation

`DIRECT_SQL_SURFACE` is used for the three native types, the 26 functions
listed by the pinned README under vector/halfvec/bit/sparsevec functions, all
four ordinary aggregates, all 40 SQL operators, and all 23 casts.

`IMPLEMENTATION_SUPPORT` is used for type I/O/receive/send/typmod functions,
sections explicitly labeled private, aggregate transition/combine/final
helpers, cast implementation helpers, access-method handlers, and index/access
support functions. Representative exact support declaration:

```text
vector_add(vector, vector) -> vector
```

The seven access-method/support declarations without explicit null, volatility,
or parallel clauses retain `UNKNOWN` metadata rather than inferred defaults.
No declaration required `UNCLASSIFIED` after the README plus explicit SQL
section review.

## Exact Representative Surface

Representative exact entries include:

```text
native type: vector
scalar: l2_distance(vector, vector) -> float8
aggregate: avg(vector) -> vector
operator: <-> (vector, vector) -> float8
cast: vector -> halfvec, IMPLICIT, FUNCTION
```

All functions with explicit clauses retain their exact `STRICT`, `IMMUTABLE`,
and `PARALLEL SAFE` metadata. Aggregate results are established by the pinned
transition/final declarations: `avg(vector) -> vector`, `sum(vector) -> vector`,
`avg(halfvec) -> halfvec`, and `sum(halfvec) -> halfvec`.

## Cataloged-unmodeled Evidence

Array forms remain `UNMODELED` with exact source spelling and
`UNSUPPORTED_TYPE_FORM`, including:

```text
array_to_vector(integer[], integer, boolean) -> vector
vector_to_float4(vector, integer, boolean) -> real[]
integer[] -> vector cast
double precision[] aggregate state helpers
```

Pseudo/special forms retain `POLYMORPHIC_OR_PSEUDO_TYPE`, including `cstring`,
`internal`, and `index_am_handler`. `cstring[]` retains both ordered reasons:

```text
UNSUPPORTED_TYPE_FORM
POLYMORPHIC_OR_PSEUDO_TYPE
```

Source spelling is never parsed into an array or pseudo-type identity. These
declarations are retained as catalog evidence and cannot satisfy an exact
selector.

## Completeness

Production completeness claim count is exactly zero. The complete declaration
inventory proves positive and unmodeled evidence; it does not invent negative
authority for arbitrary exact scopes. Therefore an otherwise missing exact
scope resolves through Slice 8 to:

```text
Unknown(EXTENSION_CATALOG_COMPLETENESS_UNAVAILABLE)
```

not `Absent`.

## Canonical Artifact Identity

The finalized Slice 5 artifact identity is:

```text
canonical byte length: 993469
content_sha256: 686e68fe9d60c20cb276e2b26007d310ff8877a5b4a8274e5c9194116fa74654
```

Independent reconstruction from the explicit typed module data produces the
same bytes and digest. Slice 5 ordering and encoding are unchanged.

## Provider And Checker Proof

The production catalog is exercised only through explicit test availability,
exact Slice 6 selection, Slice 7 typed selectors, and the Slice 8 provider and
checker:

```text
l2_distance(vector, vector) -> Found(SUPPORTED) -> SATISFIED
vector_add(vector, vector) -> Unknown(NOT_PROVIDER_ELIGIBLE)
array_to_vector(...) -> Unknown(CATALOGED_UNMODELED)
missing exact scope -> Unknown(COMPLETENESS_UNAVAILABLE)
key.extension == pgvector -> Unknown(TARGET_MISMATCH)
PostgreSQL 17 exact selection -> UNDECLARED, never consumes this catalog
```

No production availability declaration or selector is created.

## Privacy Offline Boundary And Compatibility

The production module is private with `__all__ = ()`, contains one stable
`PGVECTOR_V086_POSTGRESQL18_CATALOG`, and is not re-exported. It performs no
filesystem, environment, network, database, Git, installation, callback,
registry, discovery, or dynamic import behavior. Built artifacts contain only
the typed Pietto module, not upstream files. `pietto-package.toml` remains
unchanged and the catalog is not a package asset.

Preserved unchanged: `CapabilityKey`, selector protocol, dialect bridge,
extension-owner validation, Slice 5 encoding, Slice 6 selection, Slice 8
provider/checker/matrix semantics, legacy unbound `EXTENSION_SIGNATURE`,
non-extension providers, profile omission, `pietto.capability-inspection.v1`,
and the Phase 56 differential corpus of 125 vectors with digest
`8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e`.

The package remains `0.1.0`. Live Git plus successful natural exact-head CI
owns Slice 9 completion. The candidate lifecycle keeps Slice 9 current and
Slice 10 unstarted; no post-CI status-flip commit is required.
