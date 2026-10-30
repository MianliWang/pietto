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

A minimal configuration, `pietto.toml` at the root, selects the files of an
explicit-module project:

```toml
schema_version = 2

[sources]
include = ["models/*.pietto"]
```

`exclude` is optional and defaults to `[]`. This is the mode that the README
examples, JOINs and `any(...)` in `check --project`, and `emit-sql --project`
need. `schema_version = 1` selects the older legacy-flat mode, which checks no
JOIN and no `any(...)` and emits no SQL; keep it only for an existing
legacy-flat project (see [Schema compatibility](#schema-compatibility)).

Selection is deterministic and project-relative. Paths use `/`, are checked
lexically, and are contained by the pinned root before trusted reads. A
`[sources]` pattern follows these rules:

- It is relative to the project root and uses `/`. It may not be empty,
  absolute, a drive or UNC path, end with `/`, contain a backslash, `$`, a
  backtick, or an empty, `.` or `..` segment, or have a segment that starts
  with `~` or `!`.
- `*` matches any characters inside one path segment, and `?` matches exactly
  one character. A segment that is exactly `**` matches any number of whole
  path segments, including none. Brackets, braces, extended globs such as `@(...)`, and `**`
  inside a longer segment, such as `a**b`, are rejected.
- Only files whose names end in `.pietto` are selected, so `models/*`
  selects the `.pietto` files in `models/`.
- A file or directory whose name starts with `.` matches only a pattern segment
  that also starts with `.`. `*`, `?` and `**` never match it, so `**` does
  not enter hidden directories.
- A path that any `exclude` pattern matches is not selected, even when an
  `include` pattern matches it.
- Selection does not enter symbolic-link directories. A selected symbolic-link
  file must resolve to a regular file inside the root. Selecting the same
  physical file through two paths is an error.
- Selected files are read in code-point order of their project-relative paths.
  A selection that matches no `.pietto` file is an error that names the
  `include` and `exclude` patterns.
- Selection does not list a directory that no `include` pattern can reach, or
  one that an `exclude` pattern covers completely, such as `dir/**`, so an
  unreadable directory there is no error. An unreadable directory that could
  hold a selected file is a `project_glob` error.

The only resource limits are per file: a selected source may hold at most
1 MiB (1,048,576 bytes) of UTF-8, or it is `PIE-P1006`, and at most 200,000
tokens, or it is `PIE-P1007`. Pietto does not limit the number of selected
files, their total size, or the size of `pietto.toml`, so the time and memory
a project command uses grow with the project. Failures remain ordered project
diagnostics rather than partial success.

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

Each project command reads only some schema versions:

| `schema_version` | Top-level tables | `check --project` | `emit-sql --project` | `explain --project` |
|---|---|---|---|---|
| `1` legacy-flat | `[sources]` | yes | no | no |
| `2` explicit modules | `[sources]` | yes | yes | no |
| `3` package root | `[package]` | no | no | no; convert it to `4` |
| `4` package root | `[package]`, `[capability_environment]` | no | no | yes |

A command given another version fails with `config_schema`.
Schema 3 and 4 select no source files, so `[sources]` is rejected there; they
name one package instead (see
[Explaining a package-root project](#explaining-a-package-root-project)).

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
An always-null numeric expression keeps the stricter typed-twin diagnostic in
this mode, as it does in an EXPLICIT_MODULES project.
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

## Explaining a package-root project

`pietto explain --project ROOT [--format json]` reads only a
`schema_version = 4` project. It writes the Project Explain Artifact v1
(`pietto.project-explain.v1`), not a project JSON v2 envelope; see the
[JSON contract](spec/phase58-slice8-project-explain-json-v1.md) and the
[CLI contract](spec/phase58-slice14-project-explain-cli-text-json-v1.md).
For a schema 1 or 2 project it fails with `config_schema` at `pietto.toml`,
whose message names the commands that read that project (`check --project`,
and for schema 2 also `emit-sql --project`); explain for explicit-module
projects is a
[roadmap](roadmap.md#project-mode-follow-up) item. A schema 3 project converts
in one step: set `schema_version = 4` and add an empty
`[capability_environment]` table.

Explain reports the package graph, each package's content digest, the declared
capability requirements, and their portability across the targets of
`[capability_environment]`. It parses the package modules and reports their
syntax errors, but it does not check their semantics: an unknown import, a
duplicate declaration or an unknown type still gives `ok: true`. Check the
same files with `check --project` through a schema 2 configuration next to the
package, as in this layout, where the package is the README quick-start file:

```text
shop/
├── pietto.toml            schema 4: pietto explain --project shop
└── pkg/
    ├── pietto.toml        schema 2: pietto check --project shop/pkg
    ├── pietto-package.toml
    └── shop.pietto
```

`shop/pkg/pietto-package.toml` lists every module of the package as an asset,
with a normalized package-relative path:

```toml
schema_version = 1
namespace = "example"
name = "shop"
version = "1.0.0"

[[assets]]
kind = "module_source"
path = "shop.pietto"
```

`shop/pkg/pietto.toml`:

```toml
schema_version = 2

[sources]
include = ["*.pietto"]
```

`shop/pietto.toml` names the package directory and repeats its namespace, name
and version, which must equal the manifest's. `version` is a strict SemVer
release:

```toml
schema_version = 4

[package]
path = "pkg"
namespace = "example"
name = "shop"
version = "1.0.0"
sha256 = "<the digest that package_digest.py prints>"

[capability_environment]
```

`sha256` pins the exact bytes of the manifest and every asset, framed as
described in [Package activation](#package-activation-manifest-normalization-and-root-validation).
No Pietto command computes it. This standard-library script prints it for one
package directory:

```python
# package_digest.py: python package_digest.py shop/pkg
import hashlib
import sys
import tomllib
from pathlib import Path

package = Path(sys.argv[1])
manifest = (package / "pietto-package.toml").read_bytes()
records = [("pietto-package.toml", manifest)]
for asset in tomllib.loads(manifest.decode("utf-8"))["assets"]:
    records.append((asset["path"], (package / asset["path"]).read_bytes()))
digest = hashlib.sha256(b"pietto-package-content-v1\0")
for path, content in records:
    name = path.encode("utf-8")
    digest.update(len(name).to_bytes(8, "big") + name)
    digest.update(len(content).to_bytes(8, "big") + content)
print(digest.hexdigest())
```

Run it again after every edit of the manifest or a module: a stale pin is
`project_resource` ("Package content digest does not match the declared root
sha256."). After a successful explain, the text output shows the digest as
`content_sha256`.

With an empty `[capability_environment]`, portability is `indeterminate`
(`no-evaluated-targets`). A target makes it evaluate, for example:

```toml
[[capability_environment.profiles]]
namespace = "profiles"
name = "base"
release = "r1"
kind = "base"
database_family = "PostgreSQL"
database_release = "18"

[[capability_environment.targets]]
database_family = "PostgreSQL"
database_release = "18"
base_profile_namespace = "profiles"
base_profile_name = "base"
base_profile_release = "r1"
```

The [capability environment contract](spec/phase58-slice11-project-capability-environment-authority-v1.md)
defines profile facts, overlays and the other keys. A package may also declare
`[[dependencies]]` (`namespace`, `name`, `version`, `sha256`, and a `path` to
the dependency's directory relative to the declaring package), each pinned by
its own digest. When the root package fails to load, for example because of a
syntax error or a stale pin, explain reports only the root's diagnostics and
loads no dependency, so a dependency's errors appear once the root loads.

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

An import target is the path of another selected source of the project,
relative to the project root and written with `/` separators, exactly as
`inputs[].path` reports it: no `./`, no leading `/`, no `..` and no `\`.
So with `include = ["models/*.pietto"]`, `models/orders.pietto` imports from
`"models/types.pietto"`, not from `"types.pietto"`, and a source that
`[sources]` excludes cannot be imported. An unresolved target is PIE-S2701,
which names the selected paths it may have meant. Import and export
statements are read only in a `schema_version = 2` project: a LEGACY_FLAT
project check refuses each one, and a single-file command warns at each one
(PIE-S2708).

The target module must export the requested declarations, with the kind they
are exported as; a module may re-export an imported declaration, and such
re-exports chain through any number of modules. Kinds remain exactly
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
`--module` is the module's project-relative path with `/` separators, such as
`models/queries.pietto`; when nothing matches, the error lists the project's
modules, or the declarations of that kind in the module.
The emission contract is a normalized project-relative JSON file read once through the
same pinned-root trust rules as project sources; legacy-flat and package-root projects are
rejected as `config_schema`. See the [README example](../README.md#project-sql-emission)
and the [Slice13 contract](spec/phase66-slice13-project-emit-sql-cli-explicit-contract-atomic-output-v1.md).

`--output FILE` writes the JSON artifact in either `--format`: with
`--format text`, the readable presentation goes to stdout and the file still
holds the JSON document. Only a VERIFIED artifact is written.

### Emission contract values

The contract `target` is `{"family": "postgres", "release": "18.6"}` or
`{"family": "mysql", "release": "8.4.12"}`. Its family must equal `--dialect`,
or the command fails with `emission_contract_schema`; another release is
BLOCKED with `PIE-B1003`. Each source field's `representation` gives its
`storage`, its `nullable` (`false` for a non-null field, `true` for an optional
one) and its `domain`:

| Logical type | PostgreSQL `storage` | MySQL `storage` | `domain` |
|---|---|---|---|
| `Int` | `pg_int2`, `pg_int4`, `pg_int8` | `my_smallint`, `my_int`, `my_bigint` | `int_range`, with string `min` and `max` inside the storage range |
| `Bool` | `pg_bool` | `my_bool01` | `bool01` |
| `Text` | `pg_text` | `my_varchar`, with a `length` from `max_characters` to 16383 | `text`, with `max_characters`, `encoding` `UTF8` (MySQL `utf8mb4`), `collation` `C` (MySQL `utf8mb4_0900_bin`) and `padding` `NO PAD` |
| `Decimal(p, s)` | `pg_numeric` | `my_decimal` | `decimal`; the storage and domain `precision` and `scale` are `p` and `s` |
| `Float` | `pg_float8` | `my_double` | `finite_float`, with `format` `binary64` |
| `Timestamp` | `pg_timestamp` | `my_datetime` | `timestamp`; the storage has `fractional_seconds` 6 |
| `UUID` | `pg_uuid` | `my_uuid_bytes` | `uuid`, with `encoding` `standard_bytes` |

Premises declare facts about the database that the compiler cannot see. A
source premise goes in that source's `premises` with `"scope": "source"`; a
statement premise goes in `environment` with `"scope": "statement"`:

| Key | Scope | PostgreSQL value | MySQL value | Needed |
|---|---|---|---|---|
| `row_domain_matches` | source | `true` | `true` | on every source the statement reads; otherwise `PIE-B1001` |
| `read_only_object` | source | `true` | `true` | on every source the statement reads; otherwise `PIE-B1001` |
| `client_encoding` | statement | `"UTF8"` | `"utf8mb4"` | whenever the statement reads a source |
| `operator_environment` | statement | `"builtin_only"` | `"builtin_only"` | when the SQL computes more than the selected columns, for example a value, a filter, an ordering or a limit |
| `identifier_case` | statement | `"quoted_exact"` | `"lower_case_table_names=0"` | when the SQL needs named stages (a `WITH` clause), for example for `where`, `group by`, `order by`, `limit`, a window, a JOIN, a relation `let`, a set operation, or a read of another table |
| `parameter_protocol` | statement | `"postgres_extended"` | `"mysql_prepared"` | when the artifact has a placeholder: a literal under `--literal-policy bind-safe`, or a read of a header parameter |

A needed statement premise that is missing is BLOCKED with `PIE-B1004`, and
one with another value with `PIE-B1005`. A plain projection of source columns
needs only the source premises and `client_encoding`. The statement premise
`resource_limits` (an object that lowers `sql_bytes`, `artifact_bytes`,
`nodes`, `parameters` or `columns`), `session_sql_mode` and
`session_time_zone` are optional. The field premises `value_domain`,
`encoding`, `collation`, `padding` and `comparison_prefix_bytes` are optional
and must agree with the field's `domain`.

The README example on MySQL declares
`source items: Item = mysql.table("fixture.items")` and uses this contract:

```json
{
  "format": "pietto.emission-contract.v1",
  "target": {"family": "mysql", "release": "8.4.12"},
  "sources": [{
    "selector": {"module": "main.pietto", "kind": "source", "name": "items"},
    "relation": {"namespace": "fixture", "name": "items"},
    "scan": "relation_rows",
    "fields": [
      {"ordinal": 0, "name": "id", "column": "item_id",
       "representation": {"storage": {"kind": "my_bigint"}, "nullable": false,
                          "domain": {"kind": "int_range", "min": "0", "max": "100"}}},
      {"ordinal": 1, "name": "label", "column": "item_label",
       "representation": {"storage": {"kind": "my_varchar", "length": 64}, "nullable": false,
                          "domain": {"kind": "text", "max_characters": 64,
                                     "encoding": "utf8mb4", "collation": "utf8mb4_0900_bin",
                                     "padding": "NO PAD"}}}
    ],
    "premises": [
      {"key": "row_domain_matches", "scope": "source", "value": true},
      {"key": "read_only_object", "scope": "source", "value": true}
    ]
  }],
  "environment": [
    {"key": "client_encoding", "scope": "statement", "value": "utf8mb4"},
    {"key": "operator_environment", "scope": "statement", "value": "builtin_only"},
    {"key": "identifier_case", "scope": "statement", "value": "lower_case_table_names=0"}
  ]
}
```

### Emission rules

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
distributions; the published `0.1.3`, `0.1.4` and `0.1.5` include them. This
`0.1.6` candidate is available only when its accepted files appear on its
versioned release channels. Git publication and natural exact-head CI remain
the lifecycle authority.

These proofs belong to project SQL emission, not to `check --project`: the
check accepts, for example, `sum` over an `Int`, `Decimal` or `Float` field,
and `emit-sql --project` then reports the table or query BLOCKED with
`PIE-B1004`. Single-file `emit-sql` emits such a `SUM`.

`check --project` also accepts the following forms, which
`emit-sql --project` reports BLOCKED on both dialects whatever the contract
declares:

- `count`, `count_distinct`, `min` and `max` of a `Text`, `Float` or `Decimal`
  argument; of an `Int` argument they are admitted, and so is `count()`;
- a comparison of a `Float` value (`price > 1.5`, `price > 1`,
  `price > other_price`) or of a `Decimal` value with a literal
  (`amount > 1.5`);
- `order by` or `group by` a `Float` value;
- arithmetic on a `Float` field (`price * 2.0`, `price + price`);
- `/` and `%`, whatever their operand types, `Float(x) / y` included;
- `matches(...)`;
- a `Text` default of `lag` or `lead` (`lead(label, 1, "none")`);
- `Int` arithmetic whose result is not proved to fit the column's storage
  type. The proof uses the storage type, not the declared `int_range`:
  `id + 1` over `pg_int4` or `my_int` is admitted, while `qty + 1` over
  `pg_int8` or `my_bigint` is BLOCKED with `PIE-B1002`, and so are `-id` and
  `abs(id)` over `pg_int4`.

Admitting these forms needs reviewed SQL and a real-database differential on
PostgreSQL and MySQL, which the PostgreSQL/MySQL parity batch plans (see the
[roadmap](roadmap.md#project-mode-follow-up)).

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

The `0.1.6` wheel and sdist on PyPI are the files attached to the
[v0.1.6 GitHub pre-release](https://github.com/MianliWang/pietto/releases/tag/v0.1.6),
together with `SHA256SUMS`, which lists the SHA-256 of the wheel and the sdist.
To check files downloaded from that release, keep their names and run
`sha256sum --ignore-missing -c SHA256SUMS` in the download directory. GitHub
also offers an automatic source archive under the same name as the sdist,
`pietto-0.1.6.tar.gz`; it is a snapshot of the v0.1.6 repository tag, not the
sdist, and it is not listed in `SHA256SUMS`.

Version `0.1.6` rejects bundles and saved jobs produced by `0.1.5` or earlier
by code identity; Pietto neither migrates nor rewrites those bytes, so retained
state needs its matching old environment (see
[execution](execution.md#known-limitations)). The VS Code extension `0.1.0`
accepts only the `0.1.2` wheel or its baseline fingerprint and refuses
`0.1.6`.

## Optional Arrow dependency

The core distribution depends only on `antlr4-python3-runtime==4.13.2`.
The public selector `pietto[arrow]` adds exactly `pyarrow==26.0.0`; it changes
available dependencies, not the public Python API or CLI. Phase67 result
modules remain private under `pietto._project`; Phase69 exposes the three
execution routes and saved-result APIs as public alpha under
`pietto.execution`. Package/CLI version is `0.1.6` and `requires-python`
stays `>=3.12`. Its versioned GitHub pre-release and PyPI listing determine
distribution availability once the accepted files are available.
The verified extra matrix is CPython3.12/3.13 on Linux x86-64 with PyArrow26.0.0.
See [checkout and local-wheel installation](../README.md#install-from-a-checkout).
This is not a broader platform/version support promise.

Phase68 S18 adds three route selectors, each Arrow plus one route's exact pins:
`execute-postgres` (`psycopg[binary]==3.3.5`), `execute-mysql`
(`mysql-connector-python==26.10.0`; the published `0.1.5` selects `26.7.0`) and `execute-postgres-adbc`
(`adbc-driver-postgresql==1.13.0`, `adbc-driver-manager==1.13.0`; the published `0.1.5` selects `1.12.0`); see the
[execution install](execution.md#install). Installation never chooses
a route, grants execution or qualifies storage; all three routes are
[public alpha interfaces](execution.md). The
[S18 contract](phases/phase-68/slice-18.md) records the verified domain.

The [Phase67 audit and handoff](phases/phase-67/completion-audit.md) identifies
the existing private bindings, ownership and finite-completion prerequisites.
Phase68 execution authority and higher-level adapters remain separately owned.
