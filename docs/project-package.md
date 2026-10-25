# Projects and packages

Pietto has an explicit, compiler-only local project model. Project and package
features do not add database execution, runtime loading, a package registry,
or network access.

## Project invocation and configuration

Project commands receive an explicit root:

```bash
pietto check --project PATH
```

Pietto does not silently discover a project from the working directory.
Configuration is declarative and fail closed. The current schema and JSON
contracts are [configuration v1](spec/pietto-config-v1.md) and
[project CLI/JSON v2](spec/project-cli-json-v2.md).

A minimal source-selection configuration is:

```toml
schema_version = 1

[sources]
include = ["models/*.pietto"]
```

Selection is deterministic and project-relative. Paths use `/`, are checked
lexically, and are contained by the pinned root before trusted reads. Resource
limits bound configuration bytes, selected inputs, source bytes, and parser
work. Failures remain ordered project diagnostics rather than partial success.

The selected source files use the current [Pietto language](language.md):
source binding with `=`, explicit `from`, query names introduced by `let`, and
shape-typed relationship predicates. The optional `pietto NUMBER` header is
metadata, not a syntax selector. Project schema versions below select project
and package behavior; they do not restore retired source spelling.

## Schema compatibility

- Schema v1 preserves the legacy-flat project model.
- Schema v2 activates explicit logical modules and module-local semantic facts.
- Schema v3 selects the package-root activation branch.
- Schema v4 retains the exact package-root activation and requires one explicit
  project capability environment containing project-owned profiles and an
  ordered evaluated-target denominator.

The modes are explicit compatibility boundaries. A newer branch does not
silently fall back to an older catalog or source-selection path, and private
facts do not automatically become public CLI/JSON/IR/SQL fields.

A legacy-flat (`schema_version = 1`) project check retains its historical
scalar semantic checks over selected files, read as one file in selected
order, so a declaration can use one of another file: `Int + Text`, an invalid
cast, an unknown field, an invalid relationship declaration or a repeated enum
member gets the diagnostic that a single file gets, except inside a JOIN or an
`any(...)`, which such a project refuses (see below). These follow the
diagnostics of the legacy-flat project model, which they do not repeat.
Legacy-flat projects do not emit SQL, so the check types as an explicit-module
check does and skips the refusals that only single-file SQL needs: a field of
an alias of an enum is typed as that enum (so `lag` over it passes); a `let`
name selected unaliased in a relation with GROUP BY (`lo` for `lo = lower(t)`),
an expression past the let
inline expansion limit (PIE-S2328), a ROWS or GROUPS frame offset other than a
nonnegative Int literal up to 9223372036854775807, a window count literal
above that value, an ungrouped ORDER BY key that is a bare constant other
than an integer literal, such as `-1` or `"a"`, and a `min` or `max` whose
argument is a `let` name in a relation without GROUP BY (`m = max(w)` with
`w = amount`) all pass it (the key `1` is PIE-P1000 in every check); and a
source connector gets the diagnostics of an
explicit-module check, without the single-file table-name checks, so
`postgres.table("app.src.x")` and `postgres.table(app.src)` pass it while
`postgres.table(1)` and `postgres.table("a", "b")` are PIE-S2306. As in a
single file, an ungrouped ORDER BY key reads input fields, `let` bindings and
a SELECT output named alone, so with `x = n + 1` and a window result `w`
selected the keys `w` and `x` pass, while `w + 1`, `-w` and `x + 1` are
PIE-S2102, and so is a key `n` with `n = n + 1` selected, which names both an
input field and a SELECT output of another value. Legacy-flat retains its narrower
row-typing boundary for JOIN binding fields, computed `let` group keys and
aggregates of `let` names in grouped relations. Modern single-file JOIN/ANY
support does not widen this project mode. A missing deeper field diagnostic
inside an unavailable relation, such as one for `r.t + 1`, does not establish
that the relation is supported; its own admission/completion diagnostics remain
authoritative.
Analysis that reaches the single-file bound (PIE-S2006), such as an expression
nested past 450 levels in any selected file, leaves only the project model's
diagnostics, without PIE-S2006, as a project is not held to that bound. The
diagnostics that a check mode selects (PIE-S2303 for a source without a shape,
and PIE-S2304) are not reported, as project commands take no check mode. `emit-sql --project` and the forms that only explicit modules
admit need `schema_version = 2`.

A legacy-flat project checks no JOIN and no `any(...)` of the current syntax.
Each JOIN, of any kind and whatever its target, is one PIE-S2334: at its `on`,
a call of a relationship predicate included, or at the JOIN when it has no
`on`, with the text
``JOIN customer: a schema_version = 1 project has no JOIN in the current syntax; set schema_version = 2 to check it.``.
Each `any(...)`, before a JOIN or after it, nested or not, in any clause, is
one PIE-S2334 at the `any(...)`, with the text
``any(...): a schema_version = 1 project has no any(...) in the current syntax; set schema_version = 2 to check it.``.
They come in source order, also in a relation that reads a field of a JOIN
binding, whose other diagnostics the check omits. 0.1.4 refused this spelling
of JOIN and `any(...)` with PIE-P1000, so this refusal removes nothing that
0.1.4 accepted. The relationship JOINs that
0.1.4 checked in a `schema_version = 1` project, such as
`inner join customers as customer`, a
JOIN `via` a relationship and the other forms written with `as`, are
therefore no longer available; a legacy-flat project never emitted SQL for
them. To check such a JOIN again, rewrite it in
the current spelling, with a `let` that names its input and an `on` that calls
a relationship predicate or states the condition (`pietto migrate` reports
each old JOIN with PIE-P1011; see
[Migrating old source](language.md#migrating-old-source)), then set
`schema_version = 2`. In a project of several files, each module then imports
what it reads from another module, which exports it (see [Modules](#modules)),
and declares the relationships its JOINs call, as a relationship is not
imported.

Schema v4 has no implicit or default target or compiler profile. Package
manifest v2 capability requirements remain owned by their declaring packages;
the profile/target environment is project-owned. Bundled catalog availability
is compiler-owned and does not claim selection, installation, or live database
state.

Package manifest schema v3 retains the exact v2 semantic requirements and adds
a separate package-owned typed physical selector sidecar for
`EXTENSION_SIGNATURE` occurrences. The selector is not part of `CapabilityKey`,
does not select a catalog, and is covered by the existing whole-package content
digest. Schema-v2 extension requirements remain valid legacy unbound data.

## Trusted source identity

The project root, configuration file, and selected sources are opened through
checked descriptors. Pietto validates path containment, regular-file posture,
pre/post-read identity, byte limits, and UTF-8 before accepting source text.
Symlink and replacement races fail closed. On Windows, directory junctions and
other name-surrogate reparse points are treated as symbolic links: trusted
reads refuse to traverse them, source selection does not descend into them,
and a link whose target Windows cannot read fails closed as an inaccessible
source. Windows CPython reports a different `st_ctime` meaning for path-based
and descriptor-based stat (creation time versus change time), so Windows
trusted reads do not use ctime as an identity fact; device and inode identity,
file type, size, and modification time are still compared. The Windows
trusted-open fallback checks the parent directories before and after opening;
a concurrent writer inside the project tree that swaps an intermediate
directory and restores it within that window is not detected.

The trusted-source SHA-256 is computed over the exact accepted opened bytes.
It is product content identity, not governance hashing. Module/package layers
may derive private identity and lookup facts from it without reopening the
source or treating equal rendered text as equal authority.

## Modules

Each selected explicit-module input has a stable logical module identity and a
source-ordered local catalog. Imports, aliases, exports, and re-exports retain
exact declaration kind, owner, target, occurrence, and source order.

Module source uses Python-style lists with an explicit kind on every item.
For example, a module may import and re-export all six admitted kinds:

```pietto
from "models.pietto" import (
    type UserId,
    enum Status,
    shape User,
    source users,
    table active_users,
    query report as ImportedReport,
)

export (
    type UserId,
    enum Status,
    shape User,
    source users,
    table active_users,
    query ImportedReport,
)
```

The target module must export the requested declarations. Kinds remain exactly
`type`, `enum`, `shape`, `source`, `table` and `query`; local `def`, `constraint`,
`derive` and `relationship` declarations are not newly importable or exportable.
A relationship call uses the exact declared shapes and actual row occurrences,
including identities reached through imported shape/source aliases. It does not
create a public link object, infer a FROM input or grant a foreign-key promise.

The module graph preserves complete import evidence separately from canonical
edges. Cycles, missing targets, collisions, blocked resolution, diamonds, and
multi-hop provenance do not select an arbitrary winner. Cross-module type,
enum, shape, source, table, and query resolution preserves nominal identity,
row facts, origin, provenance, lineage, and deterministic diagnostics.

Module catalogs, binding environments, graphs, attribution, package-neutral
identity, and inspection documents are private compiler facts. Public output
changes require a separate compatibility decision.

## Package activation, manifest normalization, and root validation

Schema v3 carries one immutable package-root activation. The current private
manifest normalizer accepts caller-supplied bytes for the logical
`pietto-package.toml` input; it performs no filesystem access.

The normalizer:

- requires the exact root array-of-table structure for assets; dependencies
  are optional and normalize to an empty tuple when absent;
- enforces UTF-8, TOML, size, key, value, and lexical-path boundaries;
- preserves occurrence order and multiplicity;
- reports the complete deterministic error set;
- rejects foreign or mixed-root construction at the canonical boundary; and
- retains each nonempty declared dependency `sha256` field without yet
  verifying it against loaded package content.

A second private pure boundary runs only after successful normalization. It
defines logical package identity as the exact, case-sensitive, Unicode-exact
`(namespace, name)` pair; validates and preserves one strict SemVer 2.0.0
release string; forms the exact identity-plus-version coordinate; requires the
activation and manifest identity/version declarations to agree exactly; and
validates the root activation `sha256` as exactly 64 lowercase hexadecimal
characters. Dependency declarations remain structurally retained and otherwise
unvalidated.

A third private pure boundary types the already-normalized root assets without
tightening structural normalization. Structural manifests continue to retain
every nonempty asset kind, source order, and multiplicity. The typed boundary
accepts only the exact `module_source` kind, requires its normalized
package-relative path to end in lowercase `.pietto`, and rejects every later
occurrence of an already-declared package-local path. A successful catalog
retains the exact validated root package and one source-ordered typed value per
manifest asset. It performs no filesystem access, content read, digest work, or
module construction.

A fourth private boundary locates the explicit schema-v3 root package beneath
the exact pinned project root. It rejects symbolic-link directory traversal,
pins the canonical local directory and its filesystem identity, and retains the
exact caller root and activation authorities. Location does not read the
manifest or assets, compute package-content digests, or resolve dependencies.

A fifth private boundary trusted-reads the non-symlink regular manifest and
typed assets, verifies their inspected/opened/final identities, and rejects
physical aliases between distinct declared assets. Whole-package content uses
the frozen byte framing:

```text
b"pietto-package-content-v1\0"
|| RECORD("pietto-package.toml", exact_manifest_bytes)
|| RECORD(asset_0.path, exact_asset_0_bytes)
|| ...

RECORD(path, content) =
    U64_BE(len(path.encode("utf-8"))) || path.encode("utf-8")
    || U64_BE(len(content)) || content
```

`U64_BE` is exactly eight unsigned big-endian bytes. Assets retain typed-manifest
source order. No newline, Unicode, or TOML normalization occurs; host, project,
activation, and canonical filesystem paths never enter the digest, so
relocation does not change it. Only a digest matching the root activation pin
may produce package-owned, package-local parsed modules. Dependency declarations
remain retained manifest data and are not loaded or validated in this boundary.

A sixth private boundary validates every ordered dependency occurrence as one
exact identity, strict SemVer coordinate, whole-package digest pin, and local
directory locator. Authored `.` and `..` components normalize relative to the
declaring package directory; escape above the pinned project root fails closed.
Each dependency then uses the same contained-directory, trusted-byte, D1, pin,
and parsed-module loading as the root package.

The local load plan uses iterative declaration-order DFS and emits successful
packages in postorder, including the root as the final entry. Exact duplicate
occurrences remain separate edges. Cycles, conflicting identities/releases/
digests/physical roots, and diamonds produce private blocker evidence without
selecting a winner; Slice 9 owns their final diagnostic product. Every loaded
package remains an independent compilation island, so equal package-local
module paths are never flattened or merged.

The seventh private boundary converts existing load-plan blockers into ordered,
canonical rejection diagnostics without re-running traversal or filesystem
loading. Cycle messages retain the DFS occurrence chain; conflict facts retain
every evidenced cause; diamond messages retain both incoming authorities under
the no-winner policy. Diagnostic text uses only package coordinates, authored
and resolved logical paths, and occurrence positions—never host paths,
filesystem identities, or object ids. Exact duplicate edges accepted by the
planner remain accepted and produce no rejection.

This is a private package foundation, not a package manager. It adds no version
ranges, solver, remote or registry access, installation, lockfile, public
package graph, public diagnostic code, recovery behavior, database behavior, or
public package API. The private inspection boundary below remains internal.

The eighth private boundary derives one package inspection and one canonical
byte payload from an exact load-plan result. Successful inspections preserve
the complete declaration-order DFS postorder, the root as the final entry,
typed assets in manifest order, every dependency occurrence with multiplicity,
authored and resolved logical paths, exact coordinates, verified package
digests, dependency pins, and owner-bound target positions. Rejected and error
inspections preserve ordered project errors, parser diagnostics, and canonical
blocker diagnostics, including cycle chains, complete conflict reasons, and
both diamond incoming authorities without selecting a winner.

The retained plan-result authority derives both the structured inspection and
its `pietto.package-inspection.v1` canonical bytes, so callers cannot supply or
graft either product. Projection and serialization consume only already-loaded
private carriers: they do not read files, traverse dependencies, inspect the
host, or include canonical host paths, filesystem identities, raw manifests,
raw module sources, or ASTs. This package inspection remains distinct from the
existing private module inspection. Public exposure remains Phase 58 work.

Package inspection projects the authority-derived value into explicit immutable
tagged records and evaluates them through a total, data-only pure boundary. That
evaluator is the one production owner of the frozen canonical bytes: accepted
documents reproduce `pietto.package-inspection.v1` byte-for-byte, while
malformed documents return a closed normalized status and structural
coordinates without echoing supplied content. Python object-identity admission
remains outside the portable contract.

Frozen package differential vectors retain literal expected bytes and rejection
outcomes for successful graphs, ordered errors and diagnostics, cycles,
conflicts, diamonds, malformed scalars, and structural corruption. Cross-process
and supported-interpreter checks make the boundary ready for an independent
implementation without adding one here.

The settled Phase 55 local package foundation is one explicit compiler-only
chain: schema-v3 activation -> structural manifest -> exact identity and typed
assets -> trusted loading and D1 content identity -> exact local dependency
plan -> deterministic rejection -> private inspection -> portable pure
evaluation and differential compatibility. Later ownership remains separate:
Phase 58 owns public package inspection and explain; Phase 59 owns richer local
package graph, provenance, and lineage. The current roadmap assigns reusable
local semantic assets to Phase 74, remote assets and trust to Phase 84,
dependency solving and lockfiles to Phase 85, and profiling-driven Rust kernels
to Phase 90. Phase 67 owns result interchange and Phase 68 owns explicit execution.

## Inspection and portable boundaries

Private module inspection serializes current compiler facts canonically and
without host-path or authority leakage. The portable pure boundary and
differential vectors protect deterministic representation, exact construction,
and anti-graft behavior. They are retained current invariants even though some
test owners still have historical Phase names.

Private package inspection is a separate schema-v3 product over package loading
and rejection authority. Its package-specific pure evaluator does not merge
with or alter the module inspection format or differential corpus.

## Evidence-path compatibility

Some private capability facts intentionally carry exact retained spec, plan,
and test paths as evidence identity. Those paths remain tracked until a
separately authorized product change migrates the facts and their consumers.
Their historical-looking names do not make them lifecycle status authority;
[status](status.md) and live Git/CI own lifecycle state.

## Project SQL emission

`pietto emit-sql --project ROOT --module LOGICAL_MODULE --kind {table,query} --name NAME
--dialect {postgres,mysql} --emission-contract FILE` compiles exactly one declaration of an
explicit-module project (`schema_version = 2`) into the `pietto.sql-emission.v1` artifact
(`pietto.sql-emission.v2` for a VERIFIED query with header parameters, see
[project CLI JSON v2](spec/project-cli-json-v2.md#emit-sql-result)).
The emission contract is a normalized project-relative JSON file read once through the
same pinned-root trust rules as project sources; legacy-flat and package-root projects are
rejected as `config_schema`. See the [README example](../README.md#project-sql-emission)
and the [Slice13 contract](spec/phase66-slice13-project-emit-sql-cli-explicit-contract-atomic-output-v1.md).

The selected project path carries only contract-qualified physical values.
Timestamp requires PostgreSQL `timestamp without time zone(6)` or MySQL
`DATETIME(6)` and the fixed civil law; UUID requires PostgreSQL `uuid` or MySQL
`BINARY(16)` and standard big-endian bytes. It does not infer either law from a
declared logical type, result metadata, or a compatible-looking backend value.
The same boundary admits the closed Q1 scalar surface and the bounded Q2 numeric
results only when their retained carrier/range facts close. PostgreSQL `substr`
requires statically proved signed-`int32` start and count bounds before its
selected-project argument casts. `date_of` accepts only the exact qualified
Timestamp carrier and emits a derived Date with PostgreSQL `DATE` or MySQL
`DATE`, preserving NULL; the Date result has no independent selected-project
source, literal, parsing, arithmetic, or timezone admission. Q1 conditionals
retain SQL `CASE` order for parameter occurrences (condition, true branch,
false branch); a bind-safe artifact therefore requires its exact
`fixed_values` and `parameter_uses`, rather than SQL text alone. A computed
relation ORDER item must reuse a visible established selected expression, with
its authored direction and target NULL/collation behavior; hidden-input reuse
is rejected. Q2 accepts only independently proved numeric realizations:
signed-range Int arithmetic and direct `avg(Int)` with an input range and a
target Float carrier. `sum(Int)`, Decimal `sum`/`avg`, and Float `sum`/`avg`
remain fail-closed without their aggregate-range, exact-division, or finite
result proof; caller JSON cannot supply that proof.

The rules in the previous paragraph postdate the published `0.1.2` (GitHub
pre-release `v0.1.2` and PyPI `0.1.2`) and are not part of those
distributions; the published `0.1.3` and `0.1.4` include them. This `0.1.5`
candidate is available only when its accepted files appear on its versioned release
channels. Git publication and natural exact-head CI remain the lifecycle
authority.

These proofs belong to project SQL emission, not to `check --project`: the
check accepts, for example, `sum` over an `Int`, `Decimal` or `Float` field,
and `emit-sql --project` then reports the table or query BLOCKED with
`PIE-B1004`. Single-file `emit-sql` emits such a `SUM`.

Supported modern relationship and Boolean ANY expressions use these same
project-emission premises. ANY binders are local to their parentheses and do not
become output row inputs. Tail WHERE ANY remains a scalar value; only ordered
AND-composed filters before a later JOIN filter the rows at that JOIN prefix,
as the retired `semi join` and `anti join` did. This does not
broaden source representations, Bool aggregate emission or another project
schema's capabilities. See [Boolean existence](language.md#boolean-existence-with-any)
for the source and scope rules.

## Installing a release

Install a release from PyPI into a virtual environment, as the
[README](../README.md#install) shows: `pip install pietto`, or
`pip install "pietto[arrow]"` for an optional extra. The compiler and CLI were
verified with CPython 3.12 and 3.13 on Linux x86-64; other platforms and
Python versions are not covered by this evidence.

The `0.1.5` wheel and sdist on PyPI are the files attached to the
[v0.1.5 GitHub pre-release](https://github.com/MianliWang/pietto/releases/tag/v0.1.5),
together with `SHA256SUMS`, which lists the SHA-256 of the wheel and the sdist.
To check files downloaded from that release, keep their names and run
`sha256sum --ignore-missing -c SHA256SUMS` in the download directory. GitHub
also offers an automatic source archive under the same name as the sdist,
`pietto-0.1.5.tar.gz`; it is a snapshot of the v0.1.5 repository tag, not the
sdist, and it is not listed in `SHA256SUMS`.

Version `0.1.5` rejects bundles and saved jobs produced by `0.1.4` or earlier
by code identity; Pietto neither migrates nor rewrites those bytes, so retained
state needs its matching old environment (see
[execution](execution.md#known-limitations)). The VS Code extension `0.1.0`
accepts only the `0.1.2` wheel or its baseline fingerprint and refuses
`0.1.5`.

## Optional Arrow dependency

The core distribution depends only on `antlr4-python3-runtime==4.13.2`.
The public selector `pietto[arrow]` adds exactly `pyarrow==26.0.0`; it changes
available dependencies, not the public Python API or CLI. Phase67 result
modules remain private under `pietto._project`; Phase69 exposes the three
execution routes and saved-result APIs as public alpha under
`pietto.execution`. Package/CLI version is `0.1.5` and `requires-python`
stays `>=3.12`. Its versioned GitHub pre-release and PyPI listing determine
distribution availability once the accepted files are available.
The verified extra matrix is CPython3.12/3.13 on Linux x86-64 with PyArrow26.0.0.
See [checkout and local-wheel installation](../README.md#install-from-a-checkout).
This is not a broader platform/version support promise.

Phase68 S18 adds three route selectors, each Arrow plus one route's exact pins:
`execute-postgres` (`psycopg[binary]==3.3.5`), `execute-mysql`
(`mysql-connector-python==26.7.0`) and `execute-postgres-adbc`
(`adbc-driver-postgresql==1.12.0`, `adbc-driver-manager==1.12.0`); see the
[execution install](execution.md#install). Installation never chooses
a route, grants execution or qualifies storage; all three routes are
[public alpha interfaces](execution.md). The
[S18 contract](phases/phase-68/slice-18.md) records the verified domain.

The [Phase67 audit and handoff](phases/phase-67/completion-audit.md) identifies
the existing private bindings, ownership and finite-completion prerequisites.
Phase68 execution authority and higher-level adapters remain separately owned.
