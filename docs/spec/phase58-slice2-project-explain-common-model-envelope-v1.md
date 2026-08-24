# Phase 58 Slice 2 Project Explain Common Model And Envelope v1

## Answer And Authority

Slice 2 implements the private immutable common-model foundation for the
future public `Project Explain Artifact v1`. The machine marker remains:

```text
pietto.project-explain.v1
```

The controlling Phase contract is
`phase58-project-explain-portability-scope-lock-v1.md`. Slice 2 implements only
artifact identity, common vocabularies, relocation-stable logical paths,
detached locations and diagnostics, and a type-safe success/failure envelope.

The Python package is private. “Public model” describes the future artifact's
model, not a public Python import surface. JSON remains Slice 8 ownership, and
the future CLI remains Slice 9 ownership.

## Private Python Surface

Production ownership is exactly:

```text
src/pietto/_project_explain/__init__.py
src/pietto/_project_explain/model.py
```

Both modules remain private with empty `__all__`. Nothing is re-exported from
`pietto`, `pietto._project`, `pietto._metadata`, or another package root.

The Slice 2 model inventory is exactly:

- `PROJECT_EXPLAIN_ARTIFACT_NAME`;
- `ProjectExplainFormat`;
- `ProjectExplainEvidencePosture`;
- `ProjectExplainRequirementStage`;
- `ProjectExplainLogicalPathKind`;
- `ProjectExplainLogicalPath`;
- `ProjectExplainLocation`;
- `ProjectExplainDiagnostic`; and
- `ProjectExplainEnvelope[PayloadT]`.

No production payload placeholder is introduced.

## Artifact Identity

The human-readable identity and machine marker are separate:

| Identity | Exact value |
| --- | --- |
| `PROJECT_EXPLAIN_ARTIFACT_NAME` | `Project Explain Artifact v1` |
| `ProjectExplainFormat.PROJECT_EXPLAIN_V1` | `pietto.project-explain.v1` |

`ProjectExplainFormat` has exactly one member. Slice 2 adds no schema-version
integer, command value, JSON field contract, serializer, or CLI route.

## Closed Vocabularies

`ProjectExplainEvidencePosture` is exactly:

| Member | Value |
| --- | --- |
| `SOURCE_FACT` | `source_fact` |
| `DETERMINISTIC_DERIVATION` | `deterministic_derivation` |
| `UNAVAILABLE` | `unavailable` |
| `CONFLICTING` | `conflicting` |

The enum describes evidence posture only. It proves neither private authority
nor installation/runtime presence. There is no reviewed-interpretation,
hypothesis, inferred, partial, stale, trusted, verified, or fifth unknown
posture.

`ProjectExplainRequirementStage` is exactly:

| Member | Value |
| --- | --- |
| `REQUEST` | `request` |
| `RESOLUTION` | `resolution` |
| `RESULT` | `result` |

These stages remain distinct. Their package, requirement, target, catalog,
matrix, status, and evidence-reference payloads remain later ownership.
Installation is not a fourth stage.

`ProjectExplainLogicalPathKind` is exactly:

| Member | Value |
| --- | --- |
| `PROJECT_RELATIVE` | `project_relative` |
| `PACKAGE_RELATIVE` | `package_relative` |
| `UPSTREAM_SOURCE_LOCATOR` | `upstream_source_locator` |

No kind implies a host filesystem identity.

## Immutable Model Shapes

Every model carrier is a frozen, slotted, keyword-only dataclass.

| Carrier | Exact field order |
| --- | --- |
| `ProjectExplainLogicalPath` | `kind`, `value` |
| `ProjectExplainLocation` | `path`, `line`, `column`, `end_line`, `end_column` |
| `ProjectExplainDiagnostic` | `code`, `severity`, `message`, `location`, `suggestion` |
| `ProjectExplainEnvelope[PayloadT]` | `format`, `ok`, `diagnostics`, `payload` |

Equality and hashing are ordinary immutable value semantics when every field is
hashable. No carrier retains an AST node, filesystem `Path`, file descriptor,
inode/device identity, exception, original `Diagnostic`, private inspection,
or another authority object.

## Logical Path Contract

`ProjectExplainLogicalPath` retains exact input spelling. It rejects malformed
values rather than normalizing them and performs no filesystem or network I/O.

### Project-relative And Package-relative Values

The exact value must be a non-empty `str`, use forward-slash logical
separators, and be either `.` or a normalized relative logical path.

The whole value `.` is the logical root. Other values reject:

- a leading or trailing slash;
- UNC forms;
- an ASCII Windows drive prefix;
- every backslash;
- NUL or another Unicode control character;
- empty or repeated components;
- `.` or `..` components; and
- implicit normalization.

The values do not call `Path.resolve`, `os.path.realpath`, filesystem stat,
symlink resolution, or cwd-dependent normalization.

### Upstream Source Locators

An upstream locator is one exact non-empty opaque `str`. It preserves spelling
and rejects:

- NUL or another Unicode control character;
- POSIX absolute path identity;
- Windows drive or rooted/UNC identity;
- home-relative host identity; and
- `file:` local-file URI identity, case-insensitively.

Stable repository, revision, documentation, URL, or upstream content locators
remain opaque. The model performs no URL parsing, canonicalization, case
folding, network access, or universal URI validation.

## Location Contract

`ProjectExplainLocation` is detached data with:

- `path` equal to an exact `ProjectExplainLogicalPath` or `None`;
- start `line` and `column` both absent or both present;
- present coordinates exact positive integers, with bool rejected;
- end `end_line` and `end_column` both absent or both present;
- an end requiring a start; and
- the end coordinate not preceding the start coordinate.

Coordinates are one-based. The carrier supports no location, path-only
location, and complete coordinates without inferring a path or consulting cwd.

## Diagnostic Contract

`ProjectExplainDiagnostic` has exact fields:

```text
code
severity
message
location
suggestion
```

`code` and `message` are exact non-empty strings. `severity` is an exact
existing `pietto.errors.Severity` member. `location` is an exact detached
`ProjectExplainLocation` or `None`. A present `suggestion` is an exact non-empty
string.

Values are not stripped, normalized, case-folded, sorted, or rewritten. The
carrier retains no original `Diagnostic`, error object, exception, AST, package
error, inspection, or authority object. Slice 2 adds no diagnostic code and
changes no diagnostic producer, documentation, stream, or exit status.

## Type-safe Success And Failure Envelope

`ProjectExplainEnvelope[PayloadT]` is generic in its future Slice-owned payload.
It has exact Python field order:

```text
format
ok
diagnostics
payload
```

Common invariants:

- `format` is exactly `ProjectExplainFormat.PROJECT_EXPLAIN_V1`;
- `ok` is an exact bool;
- `diagnostics` is an exact tuple of exact `ProjectExplainDiagnostic` values;
- order and multiplicity are preserved; and
- `payload` is the generic payload value or `None`.

Success is exactly:

```text
ok is True
payload is not None
no diagnostic has Severity.ERROR
```

A success may retain ordered warnings.

Failure is exactly:

```text
ok is False
payload is None
at least one diagnostic has Severity.ERROR
```

A failure may retain warnings before or after errors. The envelope rejects a
missing success payload, erroneous success, failure payload, error-free
failure, list diagnostics, diagnostic subclasses, non-bool `ok`, and a foreign
marker. It never drops, sorts, deduplicates, synthesizes, or rewrites facts.

## Ordering And Multiplicity

Diagnostic tuple order and multiplicity are semantic data. Repeated equal or
identical diagnostic values remain repeated. Slice 2 performs no sorting,
deduplication, winner selection, or diagnostic-code allocation.

## Privacy And Relocation

The common model contains only explicit immutable values. It exposes no host
absolute path, cwd, home directory, temporary directory, virtual-environment
directory, inode/device identity, Python object identity, symlink-resolved
path, open file, network client, or private authority object.

Logical paths and opaque upstream locators are relocation-stable. Malformed
host identity fails closed rather than being rewritten.

## Compatibility And Retained Ownership

Slice 2 leaves exact zero delta in:

- `pietto explain <file>` and Semantic Metadata Artifact v1;
- `_metadata` model, builder, serializer, and text renderer;
- Project JSON v2 and project check;
- package, capability, and extension-catalog inspections;
- package/capability/catalog pure boundaries;
- public Python exports;
- grammar, generated parser, AST, semantics, IR, SQL, package loading,
  capability checking, and catalog selection.

Retained ownership remains:

| Slice | Retained owner |
| ---: | --- |
| 3 | Package/requirement projection, coordinates, assets, direct dependencies, `declared_by`, `requested_by`, occurrences, and bounded why chain |
| 4 | Evaluated targets, matrix, evaluation states, checked statuses, reasons, and evidence |
| 5 | Catalog coordinate/target/digest, selection, physical selector, matchability, exposure, and source provenance |
| 6 | `PORTABLE`, `NOT_PORTABLE`, `INDETERMINATE`, and requirement/project derivation |
| 7 | Cross-section composition, artifact-local references, integrity, ordering, deduplication, and why links |
| 8 | Public JSON schema, serializer, UTF-8 bytes, canonical representation, envelopes, and compatibility goldens |
| 9 | Text rendering, future project explain CLI routes, exit codes, and stream routing |

## Non-goals

Slice 2 adds no:

- production `ProjectExplainPayload`;
- package, requirement, target, matrix, catalog, or portability model;
- artifact-local reference table;
- public JSON field contract, dictionary, serializer, or canonical bytes;
- text renderer or CLI routing;
- golden, fixture, grammar, generated, dependency, lockfile, workflow, version,
  tag, Release, publication, signing, or attestation behavior;
- filesystem, database, runtime, installation, or network behavior.

## Lifecycle And Slice 3 Handoff

Candidate lifecycle is:

```text
Phase 55: COMPLETED
Phase 56: COMPLETED
Phase 57: COMPLETED
Phase 58: ACTIVE
Slice 1: COMPLETED
Slice 2: CURRENT
Slice 3: NEXT / UNSTARTED
```

Git plus successful natural exact-head CI owns Slice 2 completion. No later
status-only commit is required.

```text
PHASE58_SLICE2_SELF_OWNED_OPEN = 0
```

Slice 3 owner is package and requirement provenance projection, including
package coordinates/assets/direct dependencies, `declared_by`, `requested_by`,
requirement occurrences, and the bounded why chain.

Slice 3 remains `UNSTARTED / NOT AUTHORIZED`.
