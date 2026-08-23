# Phase 57 Slice 10 pg_trgm, ltree, And PostGIS Representability v1

## Purpose And Authority

Phase 57 Slice 10 adds the second private production extension catalog,
`pg_trgm` 1.6 for PostgreSQL 18, and records two non-production audits:
`ltree` 1.3 representability and a bounded PostGIS 3.6.4 core stress corpus.

The generic Slice 2–9 schema remains unchanged. Unsupported-but-retainable
declarations use existing cataloged-unmodeled authority. No ltree or PostGIS
catalog, support claim, availability, runtime behavior, or public output is
created.

# A. pg_trgm Production Catalog

## PostgreSQL REL_18_6 Authority

Upstream repository and tag:

```text
postgres/postgres
REL_18_6
```

The lightweight tag resolves directly to commit:

```text
724edf9bde9d356724ad384a2e196edc3c9f80f7
```

Commit tree:

```text
69f81c582d01133710c1eeb9c12fadf7f47633e4
```

The pinned release notes identify `Release 18.6` with release date
`2026-08-13`. Only exact commit content was used; later PostgreSQL branches
and master were excluded.

## pg_trgm Pinned Sources

| Source | Git blob SHA |
|---|---|
| `contrib/pg_trgm/pg_trgm.control` | `1d6a9ddf259944cff08191edad2f2b44d399352f` |
| `doc/src/sgml/pgtrgm.sgml` | `07bfcac93191ed91822e24e7a746e87ac3e9d0df` |
| `contrib/pg_trgm/pg_trgm--1.3.sql` | `4c6edf8c245143ef6412fecddd14f8a9e497444a` |
| `contrib/pg_trgm/pg_trgm--1.3--1.4.sql` | `64a0c219b5cbbd9ee01c53a254769c2744ddb9b0` |
| `contrib/pg_trgm/pg_trgm--1.4--1.5.sql` | `db122fce0ffcc32f4c34c15d6f37b5343d7e8cae` |
| `contrib/pg_trgm/pg_trgm--1.5--1.6.sql` | `9e74684eaddbebecb937350d86676a8d57671f0b` |

The control declares `default_version = '1.6'`.

## Effective 1.6 Reconstruction

The final surface was reconstructed as:

```text
base: 1.3
upgrade: 1.3 -> 1.4
upgrade: 1.4 -> 1.5
upgrade: 1.5 -> 1.6
```

Statement-aware inventory reviewed all four files and applied current-state
semantics:

- 1.3 creates one native type, 25 functions, six operators, and two operator
  classes;
- 1.4 adds five functions and four operators;
- 1.5 adds `gtrgm_options(internal) -> void` and changes only unmodeled
  operator-family/selectivity metadata;
- 1.6 changes only operator-family membership;
- there are no owned `DROP`, `CREATE OR REPLACE`, aggregate, or cast effects.

The 11 `ALTER OPERATOR FAMILY` and five `ALTER OPERATOR` statements are
retained as effective-history evidence but do not alter modeled five-family
identity or result fields. Two operator classes remain out of scope.

## Catalog Coordinate And Provenance

```text
catalog namespace: pietto.postgresql
catalog name: pg_trgm
catalog release: 1

database family: PostgreSQL
database release: 18
extension identity: pg_trgm
extension release: 1.6
```

The six ordered source occurrences all use
`github.com/postgres/postgres` and exact revision
`724edf9bde9d356724ad384a2e196edc3c9f80f7`:

| Position | Locator | Curation |
|---:|---|---|
| 0 | `contrib/pg_trgm/pg_trgm.control` | extension identity and release metadata |
| 1 | `doc/src/sgml/pgtrgm.sgml` | documented user-facing functions and operators |
| 2 | `contrib/pg_trgm/pg_trgm--1.3.sql` | base install declarations |
| 3 | `contrib/pg_trgm/pg_trgm--1.3--1.4.sql` | 1.4 effective-surface additions and modifications |
| 4 | `contrib/pg_trgm/pg_trgm--1.4--1.5.sql` | 1.5 effective-surface additions and modifications |
| 5 | `contrib/pg_trgm/pg_trgm--1.5--1.6.sql` | 1.6 effective-surface additions and modifications |

## Effective Production Counts

| Family | Effective inventory | Production entries |
|---|---:|---:|
| `NATIVE_TYPE` | 1 | 1 |
| `SCALAR_FUNCTION` | 31 | 31 |
| `AGGREGATE` | 0 | 0 |
| `OPERATOR` | 10 | 10 |
| `CAST` | 0 | 0 |
| **Total** | **42** | **42** |

| Dimension | State or reason | Count |
|---|---|---:|
| Matchability | `EXACT_MATCHABLE` | 26 |
| Matchability | `CATALOGED_UNMODELED` | 16 |
| Exposure | `DIRECT_SQL_SURFACE` | 16 |
| Exposure | `IMPLEMENTATION_SUPPORT` | 26 |
| Exposure | `UNCLASSIFIED` | 0 |
| Exact group | `UNIQUE` | 26 |
| Exact group | `CONSISTENT_DUPLICATE` | 0 |
| Exact group | `EVIDENCE_CONFLICT` | 0 |
| Unmodeled reason incidence | `UNSUPPORTED_TYPE_FORM` | 1 |
| Unmodeled reason incidence | `POLYMORPHIC_OR_PSEUDO_TYPE` | 15 |

Inventory and production counts are identical.

## pg_trgm Curation

The documentation exposes exactly six direct functions:

```text
similarity(text, text) -> float4
show_trgm(text) -> _text
word_similarity(text, text) -> float4
strict_word_similarity(text, text) -> float4
show_limit() -> float4
set_limit(float4) -> float4
```

`show_limit` and `set_limit` remain direct despite documented deprecation.
All ten documented text/text operators are direct SQL surface.

SQL source spelling, not documentation aliases, owns physical identity:

```text
float4 remains float4, not real
smallint remains smallint, not int2
int2 remains int2, not smallint
int4 remains int4, not integer
"char" remains quoted "char"
show_trgm result remains _text, not text[]
```

`_text` is retained as `UNMODELED` with `UNSUPPORTED_TYPE_FORM`, while its
documentation evidence establishes `DIRECT_SQL_SURFACE`. This is the concrete
`DIRECT_SQL_SURFACE + CATALOGED_UNMODELED` case.

The extension-native `gtrgm` type is exact, owner `pg_trgm`, has no logical
mapping, and is `IMPLEMENTATION_SUPPORT`. Type I/O, operator implementation,
GiST/GIN, and options functions are implementation support. `cstring`,
`internal`, and `void` retain `POLYMORPHIC_OR_PSEUDO_TYPE`. The absence of a
`STRICT` clause on `gtrgm_options` remains `UNKNOWN` null-call posture rather
than an inferred default.

## Completeness And Canonical Identity

Production completeness claims and groups are both zero. Missing exact scopes
remain `Unknown(EXTENSION_CATALOG_COMPLETENESS_UNAVAILABLE)`.

Final artifact identity:

```text
canonical byte length: 216386
content_sha256: 09eb10a0660a05ca180d43a23f1eda7aaf4b6198f5de249591317194cc9576b7
```

Independent reconstruction produces identical bytes and digest. Slice 5
encoding is unchanged.

## Provider And Checker Proof

The real catalog is selected only through test-only Slice 6–8 authority:

```text
similarity(text, text)
-> Found(SUPPORTED)
-> checker SATISFIED

show_trgm exact-name selector
-> Unknown(EXTENSION_CATALOGED_UNMODELED)

exact GiST/GIN support function
-> Unknown(EXTENSION_CATALOG_NOT_PROVIDER_ELIGIBLE)

missing exact scope
-> Unknown(EXTENSION_CATALOG_COMPLETENESS_UNAVAILABLE)

wrong extension or PostgreSQL target
-> fail-closed target/selection Unknown
```

# B. ltree 1.3 Representability Probe

## ltree Pinned Authority

| Authority | Value |
|---|---|
| Repository | `postgres/postgres` |
| Source tag | `REL_18_6` |
| Resolved commit | `724edf9bde9d356724ad384a2e196edc3c9f80f7` |
| Extension release | `1.3` |

The probe uses these exact blobs from that commit:

| Source | Git blob SHA |
|---|---|
| `contrib/ltree/ltree.control` | `c2cbeda96c73439b3033bcb00547fcd9bca8cd5f` |
| `doc/src/sgml/ltree.sgml` | `1c3543303f0ab96d2bdb1832f9ad6d43699cae75` |
| `contrib/ltree/ltree--1.1.sql` | `d46f5fcd02eb6a4ecec6d07fb8356c3f29c6b7b7` |
| `contrib/ltree/ltree--1.1--1.2.sql` | `e38e76b31e2defa6a26ca588c7043745d31cd574` |
| `contrib/ltree/ltree--1.2--1.3.sql` | `bc9a34dd591d1e4aba702cf8d0259dbb02c6b6be` |

The control declares `default_version = '1.3'`. Effective reconstruction starts
from 1.1, adds six recv/send functions, two options functions and type/operator
metadata in 1.2, then adds two hash functions and out-of-scope hash operator
class metadata in 1.3.

## ltree Probe Results

Effective five-family surface:

| Family | Effective declarations |
|---|---:|
| `NATIVE_TYPE` | 4 |
| `SCALAR_FUNCTION` | 80 |
| `AGGREGATE` | 0 |
| `OPERATOR` | 49 |
| `CAST` | 0 |
| **Five-family total** | **133** |

| Classification | Count |
|---|---:|
| `REPRESENTABLE_EXACT` | 61 |
| `REPRESENTABLE_UNMODELED` | 72 |
| `OUT_OF_SCOPE_BY_PHASE57` | 50 |
| `SCHEMA_GAP` | 0 |

The exact extension-native types are `ltree`, `lquery`, `ltxtquery`, and the
internal GiST storage type `ltree_gist`. Array aliases `_ltree` and `_lquery`
retain exact source spelling as unsupported forms. `cstring`, `internal`, and
`void` remain pseudo/special forms.

Reason incidence inside representable-unmodeled declarations is:

| Reason | Incidence |
|---|---:|
| Array/unsupported form | 53 |
| Pseudo/special type | 27 |

The official docs and SQL confirm native/native operators, `ltree` with
`lquery`/`ltxtquery`, `ltree[]` with scalar native types, `lquery[]`, and
native-array/native-array combinations. All can be faithfully retained as
exact or cataloged-unmodeled entries. There is no schema gap.

The 50 out-of-scope statements are four operator classes, three operator-family
changes, three type changes, and 40 operator metadata changes. No production
ltree module or catalog is created.

# C. PostGIS 3.6.4 Bounded Stress Audit

## PostGIS Pinned Authority

```text
repository: postgis/postgis
annotated tag: 3.6.4
tag object: e174f9c3c7576f6a4eba6f98f5f7cf0f13cfeb3a
peeled commit: 94d984bd083635c1d253db0f87cf80b32548e406
release date: 2026-06-08
```

Required blobs:

| Source | Git blob SHA |
|---|---|
| `NEWS` | `554b990454bcf7f30016b3ee70c41c6adc4d82f6` |
| `extensions/postgis/postgis.control.in` | `3e679906b409d0fc99c2981026f83c2ecafb59c0` |
| `extensions/postgis/Makefile.in` | `88ef35afdf61d1889b4a9be5d247271871902985` |

Bounded core declaration sources:

| Source | Git blob SHA |
|---|---|
| `postgis/postgis.sql.in` | `710c24e4254ca090b653404a0b76507fd44f85c2` |
| `postgis/geography.sql.in` | `ced61b8c74e6345a956d8b6f730a62c80adb6761` |
| `postgis/postgis_brin.sql.in` | `9009a74202c481d4101efb709656f93cdfc90bdf` |
| `postgis/sqldefines.h.in` | `d8bbfa312c796746b648da289fa7c79638a78553` |

No stable-3.6/master or prerelease evidence was used.

## Core SQL Assembly Boundary

`extensions/postgis/Makefile.in` proves that the core extension install SQL is
assembled in order from generated `postgis_for_extension.sql`, spatial
reference configuration/data SQL, and `spatial_ref_sys.sql`.

`postgis_for_extension.sql` is SQLPP output from `postgis/postgis.sql.in`; that
source includes `geography.sql.in` and `postgis_brin.sql.in` and uses
configuration definitions from `sqldefines.h`. Spatial reference SQL is
table/configuration/data infrastructure, not a five-family declaration source.

The audit inspected source templates only. It did not run SQLPP, Perl, Make,
PostgreSQL, extension installation, or generated SQL.

## Bounded Corpus

The three declaration templates contain this raw source-template corpus:

| Family | Raw declarations |
|---|---:|
| `NATIVE_TYPE` (including composite types) | 9 |
| `SCALAR_FUNCTION` | 722 |
| `AGGREGATE` | 22 |
| `OPERATOR` | 45 |
| `CAST` | 26 |
| **Raw five-family declarations** | **824** |

Because preprocessor branches and generated assembly prevent this source count
from being a final installed catalog claim, a reviewed bounded corpus of 36
items was selected across all stress categories:

| Family | `REPRESENTABLE_EXACT` | `REPRESENTABLE_UNMODELED` | Total |
|---|---:|---:|---:|
| `NATIVE_TYPE` | 7 | 2 | 9 |
| `SCALAR_FUNCTION` | 4 | 8 | 12 |
| `AGGREGATE` | 2 | 2 | 4 |
| `OPERATOR` | 4 | 0 | 4 |
| `CAST` | 3 | 0 | 3 |
| **Five-family subtotal** | **20** | **12** | **32** |

| Out-of-scope bounded case | Count |
|---|---:|
| GiST operator-class/index integration | 1 |
| BRIN operator-class/index integration | 1 |
| `spatial_ref_sys` table/configuration | 1 |
| Generated multi-source assembly | 1 |
| **`OUT_OF_SCOPE_BY_PHASE57` subtotal** | **4** |
| **Bounded corpus total** | **36** |

`SCHEMA_GAP` is zero.

## Representative Stress Cases

Exact cases include named extension types (`geometry`, `geography`, `box2d`,
`box2df`, `box3d`, `spheroid`, `gidx`), ordinary overloaded functions,
geometry/geography operators, named-type casts, and ordinary aggregates with
named exact inputs and results.

Cataloged-unmodeled cases include:

```text
geometry_dump and valid_detail composite types
geometry[] inputs/results
default arguments on geography/geometry functions
ST_Dump(geometry) RETURNS SETOF geometry_dump
postgis_srs(...) RETURNS TABLE(...)
ST_HexagonGrid(...) OUT arguments + RETURNS SETOF record
geometry_in(cstring)
geography_recv(internal, oid, integer)
ST_AsMVT(anyelement) aggregate
ST_ClusterIntersecting aggregate returning geometry[]
```

No `VARIADIC` declaration occurs in the bounded source set. Overloads,
defaults, arrays, pseudo-types, set-returning, table/composite returns,
operators, casts, aggregates, schema placeholders, and multi-source generation
are all observable without requiring a generic schema change.

The intentional stress-category search also found `geometry`/`geography`
typmod hooks, `SUPPORT postgis_index_supportfn` planner metadata, operator
classes, configuration/table DDL, runtime library bindings, and extension
assembly dependencies. Exact type/function identity or existing
cataloged-unmodeled evidence retains the five-family declarations; the other
metadata stays outside the frozen families. Typmod semantics remain deferred
to Phase 64.

The audit is not a PostGIS catalog, completeness claim, provider claim, or
full-support statement. Separate raster, topology, SFCGAL, tiger geocoder,
address standardizer, and other bundled extensions remain excluded.

## Generic-schema Result And Later Readiness

```text
pg_trgm: no gap
ltree: deferred representability only, no gap
PostGIS bounded core corpus: deferred representability only, no gap
```

The existing exact and cataloged-unmodeled carriers can faithfully retain all
audited five-family cases. No generic production schema changed.

The audits reinforce Phase 64 ownership for arrays, typmods, composite and
advanced type semantics. They also expose a distinct later requirement: any
future PostGIS production catalog needs an explicit
generated/multi-source SQL assembly authority before population. This Slice
does not assign or implement that owner.

The release-aware PostgreSQL core builtin signature catalog still requires an
explicit later owner.

## Privacy Compatibility And Lifecycle

Only `pg_trgm` has a production module. There is no
`extension_catalog_ltree.py` or `extension_catalog_postgis.py`. No catalog is
automatically available or selected. Upstream files are absent from source and
built artifacts.

Preserved unchanged: `CapabilityKey`, selector protocol, dialect bridge,
Slice 5 canonical encoding, Slice 6 selection, Slice 8 provider/checker/matrix,
pgvector artifact identity, `pietto.capability-inspection.v1`, Phase 56's 125
vector corpus and digest
`8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e`,
and package version `0.1.0`.

Live Git plus successful natural exact-head CI owns Slice 10 completion. The
candidate lifecycle keeps Slice 10 current and Slice 11 unstarted; no post-CI
status-flip commit is required.
