# Phase 44 Project Config Schema Contract v1

## Status

Phase 44 Slice 2 is Project Config Schema Contract. It is
docs/spec/static-audit work only and implements no behavior change.

This contract locks the narrow active `pietto.toml` schema needed before the
future private config loader and deterministic source-selection slices. Slice 2
does not implement config loading, source selection, glob expansion, source
reading, parser aggregation, Project JSON v2 input reporting, CLI behavior,
project semantic analysis, project IR, project SQL, runtime behavior, database
behavior, or release behavior.

Phase 44 Slice 3 implements only a private config loader and schema validator
for this contract under `src/pietto/_project/**`. Slice 3 does not wire the
loader into CLI behavior, Project JSON v2 output, source selection, glob
expansion, source reading, parser aggregation, public diagnostics, semantic
analysis, IR, SQL, runtime behavior, database behavior, or release behavior.

Phase 44 Slice 4 implements only private deterministic source selection over
the loaded config contract. It expands configured include patterns, applies
configured exclude patterns, reports deterministic project-relative selected
inputs through the existing private project model, verifies physical
containment, and rejects duplicate physical file identity when detectable.
Slice 4 does not wire source selection into CLI behavior, Project JSON v2
output, source reading, `.pietto` parsing, parser aggregation, public
diagnostics, semantic analysis, IR, SQL, runtime behavior, database behavior, or
release behavior.

Package version remains `0.1.0`.

## Active Schema

The active Phase 44 project config schema is:

```toml
schema_version = 1

[sources]
include = ["models/**/*.pietto"]
exclude = []
```

This is a contract example, not a repository fixture and not an implemented
input.

The accepted top-level keys in this Slice 2 contract are exactly:

- `schema_version`;
- `sources`.

The private loader must reject unknown top-level keys, unknown tables, unknown
keys inside `[sources]`, duplicate keys or tables prohibited by TOML, and known
keys with the wrong TOML type.

## Schema Version

`schema_version = 1` is required.

The rules are:

- `schema_version` is a top-level key;
- its value must be an integer, not a string or floating-point number;
- the only accepted value in this contract is `1`;
- a missing, wrong-typed, or unsupported schema version is a private loader
  `config_schema` error;
- no implementation may silently migrate or reinterpret an older file.

There is no implicit minor version or feature negotiation.

## Sources Table

`[sources]` is required.

The table contains exactly:

| Key | Type | Rule |
|---|---|---|
| `include` | array of strings | Required and non-empty |
| `exclude` | array of strings | Optional; missing means `[]` |

There is no implicit include default. A missing `sources.include` is a future
`config_schema` error. A missing `sources.exclude` means no configured
exclusions.

The private loader must reject non-string elements. Slice 2 does not implement
TOML parsing, schema validation, source selection, or pattern expansion. Slice 3
implements only private TOML parsing and schema validation. Slice 4 implements
only private source selection and pattern expansion over the already loaded
private config model.

## Path Contract

Configured source patterns use normalized project-relative text:

- `/` is the only separator;
- paths and patterns are relative to the explicit project root;
- absolute POSIX paths are rejected;
- Windows drive paths and UNC paths are rejected;
- `.` and `..` path segments are rejected;
- empty path segments from repeated `/` are rejected;
- leading `/` and trailing `/` are rejected;
- backslashes and NUL are rejected;
- strings are literal data, with no environment-variable expansion, tilde
  expansion, command substitution, shell interpretation, URL decoding, or
  platform path separator rewriting.

Lexical validation is not enough for future source selection. Later source
selection must still verify physical containment, symlink behavior, hard-link
identity, and duplicate physical file identity before reading source bytes.

## Wildcard Subset

The Phase 44 wildcard subset is intentionally small:

- `**` may appear only as a complete path segment;
- `*` may appear inside a normal path segment and matches within that segment;
- `?` may appear inside a normal path segment and matches within that segment.

Valid examples include:

```text
*.pietto
models/*.pietto
models/**/*.pietto
```

Unsupported forms must be rejected by future config/source-selection behavior
rather than ignored:

- character classes such as `[a-z]`;
- brace expansion such as `{src,test}`;
- extglob or shell-specific forms;
- negated glob syntax;
- backslash escaping;
- malformed uses of `**` inside another segment.

Phase 44 does not include default hidden-directory exclusions, default vendor or
generated-directory exclusions, or implicit recursive meaning for a bare
directory name. Projects must express exclusions explicitly through
`sources.exclude`.

## Future Reporting Boundary

Future runtime config, path, glob, resource, and source-read failures are project
`cli_errors`, not fabricated compiler diagnostics and not new `PIE-*` codes.
Slice 3 reports config and configured-pattern failures only through the private
project error model; it does not expose them through CLI output or Project JSON
v2 output.

Expected future Project JSON v2 error ownership:

| Failure | Future `cli_errors.kind` |
|---|---|
| unreadable config | `config_read` |
| invalid TOML syntax | `config_parse` |
| schema-invalid config | `config_schema` |
| invalid configured path | `project_path` |
| invalid or failing pattern expansion | `project_glob` |
| project discovery budget exceeded | `project_resource` |
| selected source cannot be read | `source_read` |

Slice 2 does not change current root/config-only Project JSON v2 output. It does
not add `inputs[]`, file counters beyond the current zero counters, new JSON
fields, new CLI error kinds in runtime output, or any text-output behavior.

## Relationship To Earlier Specs

`docs/spec/pietto-config-v1.md` is a historical broader configuration reference.
This Slice 2 contract narrows the active Phase 44 config surface to
`schema_version` and `[sources]` only.

The following remain deferred:

- `[project]`;
- `project.name`;
- `project.default_dialect`;
- output configuration;
- resource-budget configuration;
- tooling configuration;
- hooks, plugins, or executable configuration;
- secrets, credentials, runtime settings, database settings, network settings,
  and connector settings.

Future implementation slices may use the existing project root/path, Project
JSON v2, and multi-file semantics contracts as evidence, but those older specs
do not authorize behavior outside the approved Phase 44 slice.

## Explicit Non-goals

Slice 2 does not authorize:

- config loader implementation;
- source selection implementation;
- glob expansion implementation;
- source file reading;
- parser aggregation implementation;
- CLI behavior changes;
- `src/pietto/**` changes;
- Project JSON v2 serializer changes;
- CLI JSON v1 mutation;
- Semantic Metadata Artifact v1 mutation;
- semantic model changes;
- Semantic IR changes;
- SQL backend changes;
- grammar or generated parser changes;
- fixtures or goldens;
- package, dependency, workflow, or lockfile changes;
- full project semantic analysis;
- project IR or SQL;
- `emit-sql --project`;
- `explain --project`;
- imports, includes, modules, export, package semantics, or visibility rules;
- JOIN or relationship behavior;
- `RelationLayerIR`;
- `LetBindingIR`;
- runtime or database execution;
- schema introspection, db pull, connector execution, credentials, or network
  behavior;
- Arrow, PyArrow, dataframe, materialization, or new dependency behavior;
- LSP, editor server, playground, or UI behavior;
- tag, release, publish, upload, signing, or attestation.

## Slice Responsibilities

Slice 3 implements a private config loader only. It owns TOML reading, TOML parse
classification, schema validation, configured pattern lexical validation, and
normalization of missing `sources.exclude` to an empty list. It does not own
source selection, glob expansion, source reading, parser aggregation, CLI
behavior, or Project JSON v2 output.

Slice 4 implements private deterministic source selection only. It owns
include/exclude expansion, exclude precedence, empty final source-set handling,
deterministic ordering, containment, symlink/hard-link duplicate identity
rejection, and source-selection resource limits. It does not own source reading,
parser aggregation, CLI behavior, or Project JSON v2 output.

Slice 5 may implement source read plus parse-only project check only after a
separate Gate 1 and Gate 2 approval.

Slice 6 may implement Project JSON v2 `inputs[]` and project check counters only
after a separate Gate 1 and Gate 2 approval.
