# Pietto Project Resource Model Version 1

## Status

This document defines the planned resource-budget contract for a future
Pietto project mode.

**The contract is not implemented.** Pietto does not currently load
`pietto.toml`, discover project roots, expand globs, traverse project files,
compile multiple files, emit JSON schema version 2, or enforce project-level
resource budgets.

The implemented CLI and JSON schema version 1 remain single-file interfaces.
The only implemented resource limits are the existing per-file parser/frontend
source and token budgets.

## Goals

The future project resource model must:

- reject disproportionately large project work at deterministic stage
  boundaries;
- preserve the current per-file parser budget contract;
- bound project discovery, loading, compiler, artifact, and presentation work;
- classify resource failures consistently as CLI errors or compiler
  diagnostics;
- preserve stable project-relative ordering and path attribution;
- prevent partial project SQL from being written after any project error;
- keep safety ceilings independent from project configuration;
- support focused boundary tests before implementation.

These budgets are containment controls. They do not provide complete
denial-of-service protection.

## Implemented Single-file Baseline

Phase 7 implemented exactly two parser/frontend limits:

| Budget | Implemented limit | Failure |
|---|---:|---|
| UTF-8 source bytes | `1,048,576` bytes per file or `parse_source()` input | `PIE-P1006` |
| Raw non-EOF lexer tokens | `200,000` tokens per file | `PIE-P1007` |

The current contract is:

- the source budget measures encoded UTF-8 bytes, not Unicode code points;
- the token budget counts raw non-EOF lexer tokens before indentation
  injection;
- source-size failure takes precedence because tokenization does not begin;
- both failures are parser diagnostics with severity `error`;
- both failures return exit code `1` through the CLI;
- JSON schema version 1 places them in `diagnostics`, leaves `cli_errors`
  empty, and changes no key set;
- `emit-sql --output` does not create, truncate, or replace output after either
  parser budget failure;
- semantic analysis, IR construction, and SQL emission do not run after a
  parser budget failure.

These limits provide deterministic parser/frontend containment for one input
file. They do not currently bound:

- AST node count or language-structural depth;
- type-alias expansion or relation dependency depth;
- semantic graph size or traversal work;
- total diagnostics;
- SQL artifact count or bytes;
- JSON output bytes;
- wall-clock time, CPU, or process memory.

Project mode must preserve this single-file behavior exactly.

## Budget Layers

The future project model has four resource layers.

### Discovery And Identity

This layer covers work before source contents are compiled:

- configured pattern count and total pattern bytes;
- directory entries and glob candidates examined;
- path components normalized or resolved;
- symbolic links resolved;
- filesystem identities established;
- selected source-file count.

Discovery accounting must not depend on filesystem enumeration order. A
candidate-limit failure should identify the project or configured pattern, not
an arbitrary operating-system "first" path.

### Loading And Frontend

This layer covers:

- total selected and parsed files;
- per-file UTF-8 source bytes;
- total project UTF-8 source bytes;
- per-file raw non-EOF tokens;
- total project raw non-EOF tokens;
- top-level definition count;
- AST node count;
- expression depth.

The existing per-file source and token limits remain active inside the
project-level aggregate limits.

### Compiler Graph And Artifacts

This layer covers:

- type-alias expansion depth;
- relation dependency vertices, edges, and maximum depth;
- semantic namespace and graph size;
- deterministic semantic traversal work;
- diagnostic and related-location count;
- SQL artifact count;
- total generated SQL artifact bytes.

Cycle diagnostics do not replace graph-size, graph-depth, or traversal-work
budgets. A large acyclic graph can still exceed safe work.

### Presentation And Output

This layer covers:

- combined SQL bytes presented or written;
- JSON schema version 2 encoded bytes;
- bounded error documents after a presentation budget failure;
- output alias validation and atomic replacement work.

Presentation budgets must preserve syntactically complete output. Pietto must
not truncate raw SQL or encoded JSON and report it as success.

## Planning Values For A First Implementation

The following values are conservative planning defaults. They are not active
limits and do not authorize implementation.

### Decision-ready Limits

| Budget | Planning value | Rationale |
|---|---:|---|
| Selected project source files | `256` | Supports moderately split projects while bounding per-file setup and aggregation |
| Parsed file attempts | `256` | Matches the selected-file ceiling; no hidden extra project inputs |
| Total UTF-8 source bytes | `8,388,608` bytes (8 MiB) | Eight times one per-file limit, preventing 256 individually maximal files |
| Total raw non-EOF tokens | `1,000,000` | Five times the per-file ceiling and bounded below the 256-file theoretical maximum |
| Configured include patterns | `256` | Bounds pattern validation and repeated traversal setup |
| Configured exclude patterns | `256` | Matches the include ceiling |
| Total configured pattern bytes | `65,536` bytes | Bounds path parsing while allowing descriptive project layouts |
| Glob candidate paths examined | `10,000` | Bounds traversal fan-out before source selection |
| Symbolic-link resolutions | `1,000` | Provides a hard fallback while symlinked directories remain non-traversable |
| Top-level definitions | `20,000` | Bounds namespace and initial graph construction within the source-byte ceiling |
| Diagnostics emitted | `1,000` | Prevents unbounded reporting while retaining useful project context |
| Related locations emitted | `2,000` | Bounds cross-file attribution independently from primary diagnostics |
| SQL artifacts | `5,000` | Bounds backend result cardinality before presentation |
| Total generated SQL bytes | `16,777,216` bytes (16 MiB) | Bounds generated data and combined text output |
| Encoded JSON v2 bytes | `33,554,432` bytes (32 MiB) | Allows structured metadata and JSON escaping around bounded SQL payloads |

The JSON ceiling is larger than the raw SQL ceiling because JSON quoting and
escaping add bytes. It is still an independent encoded-output limit; valid SQL
generation does not guarantee that a JSON result fits.

### Required Counters With Values Deferred

The following budgets are required before project implementation, but their
exact limits remain TBD until Pietto defines stable, testable counters:

| Budget | Required counting decision |
|---|---|
| AST nodes | Enumerate every counted AST dataclass and decide whether shared or synthetic nodes count |
| Expression depth | Define depth for unary, binary, call, grouping, predicate, and type-expression nesting |
| Type-alias expansion depth | Count acyclic expansion edges independently from cycle detection |
| Relation graph vertices and edges | Define which source, table, and query relationships enter the graph |
| Relation dependency depth | Define longest-path accounting and require iterative traversal where practical |
| Semantic graph work | Define deterministic work units rather than elapsed time |
| Path-normalization work | Define component, canonicalization, and identity-operation counters |

Implementation must not substitute Python recursion limits, wall-clock timing,
filesystem timing, or memory observations for these structural counters.

Candidate values may be proposed in the later implementation plan only after
the counters are specified. Boundary tests must be able to construct exactly
at-limit and one-over-limit inputs without depending on machine speed.

## Counting Rules

Future implementation should use these general rules:

- limits are inclusive; a value equal to the limit is accepted;
- the first counted unit beyond a limit fails the applicable stage;
- UTF-8 and SQL/JSON sizes are encoded byte counts, not character counts;
- EOF is excluded from lexer token totals, matching the current per-file rule;
- selected and parsed files use normalized project-relative identity;
- a physical source selected through aliases counts once only after aliases
  have been rejected as an invalid project;
- diagnostic and related-location caps count serialized records;
- artifact bytes count each artifact's encoded SQL exactly once;
- combined output separators count toward combined SQL bytes;
- JSON bytes count the final `ensure_ascii=True` encoding plus its trailing
  newline.

Counters must use bounded integer arithmetic and stop as soon as the next unit
would exceed the limit. They must not materialize an unbounded collection and
only then measure it.

## Failure Classification

Resource ownership determines whether a future failure is a CLI error or a
compiler diagnostic.

| Failure class | Planned representation | Exit |
|---|---|---:|
| Config pattern count/bytes | `project_resource` CLI error attributed to `pietto.toml` | `2` |
| Glob candidate or discovery work | `project_resource` CLI error | `2` |
| Path, symlink, or identity work | `project_resource` CLI error | `2` |
| Selected file count | `project_resource` CLI error | `2` |
| Aggregate source bytes before parsing | `project_resource` CLI error | `2` |
| Per-file source or token budget | Existing parser diagnostic | `1` |
| Aggregate token budget during project parsing | Future parser/frontend diagnostic | `1` |
| AST, expression, definition, graph, or semantic work budget | Future owning-stage diagnostic | `1` |
| Diagnostic or related-location cap | Future compiler diagnostic with truncation indication | `1` |
| Artifact-count budget | Future backend diagnostic | `1` |
| SQL or JSON presentation-size budget | `project_resource` CLI error | `2` |
| Output path or write failure | Existing planned `output_path` or `output_write` CLI error | `2` |

This distinction preserves the current rule: failures caused by compiler
content at parser, semantic, IR, or backend stages are diagnostics, while
project setup, filesystem, and presentation failures are CLI errors.

## Future Error Names

JSON schema version 2 should add this v2-only CLI error kind:

| Kind | Meaning |
|---|---|
| `project_resource` | A project discovery, loading, or presentation budget was exceeded |

Existing planned kinds remain more specific where applicable:

- `project_glob` for invalid glob syntax or non-resource source-selection
  failure;
- `project_path` for path containment, symlink, or identity policy failure
  that is not a budget excess;
- `output_path` for destination safety failure;
- `output_write` for atomic write or replacement failure.

The accepted JSON v2 design does not use a generic `project_output` kind.
Output size may use `project_resource`; destination validation and write
failures retain their specific existing kinds.

Compiler-stage budget failures require future full `PIE-...` diagnostic codes
owned by the relevant stage family. Exact codes and stable messages must be
assigned only when implementation begins. Documentation, code, and tests must
never introduce or display a bare diagnostic code.

## Stage Gates And Precedence

Future project processing should apply resource checks in this order:

1. parse and validate the explicit root and configuration;
2. validate pattern count, pattern bytes, and path syntax;
3. traverse in deterministic project order while enforcing candidate,
   path-work, symlink, and identity budgets;
4. reject an empty source set or selected-file count excess;
5. read selected files in normalized path order while enforcing per-file and
   aggregate source-byte budgets;
6. parse readable files in normalized path order while enforcing per-file and
   aggregate token, AST, expression-depth, and definition budgets;
7. run semantic analysis only after the complete project frontend succeeds;
8. enforce graph-size, graph-depth, and semantic-work budgets before or during
   deterministic traversal;
9. build IR and generate artifacts only after earlier stages succeed;
10. enforce artifact count and generated SQL byte budgets before presentation;
11. validate combined output and JSON encoded size before any output write;
12. write one complete output atomically only after every project stage
    succeeds.

Within one stage, normalized project-relative path and source position define
processing order. Resource failure messages should report the limit and
measured category without depending on arbitrary hash-map or filesystem
enumeration order.

A fixed precedence avoids different failures winning on different machines.
For example, an aggregate source-byte failure prevents tokenization, and a
compiler-stage failure prevents artifact or output-size checks.

## Diagnostic Cap And Truncation

The diagnostic ceiling includes its truncation indication. With a planning
limit of `1,000`, a future implementation should emit at most:

- the first `999` diagnostics in deterministic producer order; and
- one final error diagnostic stating that additional diagnostics were omitted
  because the project diagnostic budget was reached.

The truncation diagnostic requires a future canonical `PIE-...` code and
causes exit `1`, even if all preceding diagnostics were warnings. It should
have no fabricated source location unless the owning compiler stage can
attribute one deterministically.

Related locations have their own cap. Exhausting it must not silently remove
attribution while reporting success. The implementation plan must define
whether the final truncation diagnostic also reports omitted related
locations.

## JSON Version 2 Interaction

JSON schema version 1 remains unchanged.

Future JSON v2 should represent:

- setup, discovery, aggregate source, SQL-size, and JSON-size failures in
  `cli_errors`;
- parser and compiler-stage budget failures in `diagnostics`;
- existing per-file `PIE-P1006` and `PIE-P1007` diagnostics without changing
  their meanings;
- normalized project-relative paths where a file can be attributed;
- deterministic input, diagnostic, related-location, CLI-error, and artifact
  ordering.

No new success-only resource metadata is required for the first v2
implementation. Counts may be added only through an explicit schema review.
The existing `inputs` objects remain `parsed` or `error`; the resource model
does not introduce an ambiguous `skipped` status.

If a JSON result would exceed its encoded byte ceiling, Pietto should emit one
small, valid JSON v2 failure document:

- `ok` is `false`;
- `cli_errors` contains one `project_resource` error;
- `diagnostics` is empty rather than a truncated oversized collection;
- `artifacts` is empty for `emit-sql`;
- requested output metadata reports `"written": false`;
- no oversized SQL or diagnostic payload is included;
- stderr remains empty for a handled JSON request;
- the process exits `2`.

The implementation must reserve enough bounded space for this failure
document. It must never byte-truncate JSON or emit a second document after a
partial first document.

Optional considered/loaded/skipped counters are deferred. If added later,
their definitions and schema compatibility must be explicit.

## Output Write Interaction

Project output remains all-or-nothing:

- any project CLI error or compiler error prevents an output write;
- exceeding artifact, SQL, or JSON budgets prevents an output write;
- output validation covers `pietto.toml`, every selected source, symbolic
  links, hard links, and physical identity aliases;
- an existing output file remains byte-for-byte unchanged after failure;
- atomic same-directory replacement occurs only after complete rendering and
  validation;
- temporary files are cleaned after write or replacement failure.

The first project design supports one optional combined SQL output file.
Artifact-directory output, directory replacement, naming, collision, and
rollback rules require a separate design before implementation.

## Configuration Interaction

The initial `pietto.toml` schema must not contain resource-budget keys.

In particular, configuration must not:

- raise, disable, or bypass a safety limit;
- derive limits from environment variables;
- evaluate expressions or commands to compute limits;
- select a "trusted" mode with unbounded work;
- change failure classification or diagnostic ordering.

Any future configurable budget proposal requires a separate compatibility and
security review. User values must remain below fixed non-configurable hard
ceilings, and invalid values must fail configuration validation rather than be
silently clamped.

## Watch And LSP Considerations

Watch mode and LSP/editor integration need different operational contracts:

- watch mode needs cumulative and per-rebuild budgets, invalidation bounds,
  and protection from repeated filesystem churn;
- LSP needs cancellation, per-request budgets, document-version attribution,
  and bounded partial-result behavior;
- editor best-effort analysis may intentionally differ from the CLI's
  all-or-nothing project result;
- latency and memory policies may depend on the host process.

Phase 8 implements none of these capabilities. Project CLI budgets do not
pre-authorize watch, LSP, incremental compilation, or partial analysis.

## Runtime And Database Boundary

Project compiler budgets do not make runtime or database behavior safe.

SQL execution, database connections, connector execution, schema
introspection, credentials, network access, retries, cancellation, transaction
control, and runtime services require a separate threat model. Their
connection pools, query timeouts, row limits, network bytes, credential use,
and server memory are outside this project resource contract.

## Security Limitations

The planned structural budgets reduce exposure to:

- unexpectedly broad globs;
- excessive source aggregation;
- large acyclic compiler graphs;
- diagnostic amplification;
- oversized SQL and JSON results;
- partial output writes after project failure.

They do not:

- guarantee a bound on CPU time for every accepted input;
- guarantee a fixed process-memory maximum;
- replace algorithmic-complexity review;
- eliminate filesystem time-of-check/time-of-use races;
- sandbox ANTLR, Python, or dependencies;
- protect a future network service by themselves;
- provide complete denial-of-service protection.

## Non-Goals

Phase 8 Slice 6 adds no:

- project resource-budget implementation or new active limit;
- diagnostic code, message, severity, or behavior change;
- change to `PIE-P1006` or `PIE-P1007`;
- configuration budget key or environment override;
- project CLI, `--project`, or exit-code behavior;
- JSON v2 serializer, resource metadata, or JSON v1 change;
- configuration loading or `pietto.toml` file;
- root discovery, path traversal, glob expansion, or file loading;
- multi-file compiler, module, import, or include syntax;
- parser, semantic, IR, or SQL backend behavior change;
- SQLGlot integration, MySQL support, or SQL feature expansion;
- SQL execution, database connection, connector execution, or schema
  introspection;
- runtime server, Web UI, watch mode, or LSP/editor behavior;
- wall-clock timeout, CPU sandbox, or memory sandbox;
- complete denial-of-service protection claim;
- `compile_to_ir()` or `compile_to_sql()`;
- test, fixture, dependency, grammar, generated parser, `pyproject.toml`, or
  lockfile change.

## Implementation Prerequisites

Before project resource enforcement is approved, an implementation plan must
define the deferred counters and include tests for:

- exactly-at-limit and one-over-limit selected file counts;
- total project UTF-8 source bytes;
- total project raw non-EOF tokens;
- configured pattern count and bytes;
- glob candidate count;
- symlink and path-identity work;
- top-level definitions and future AST node count;
- expression and type-alias depth;
- relation graph vertices, edges, and depth;
- deterministic semantic work accounting;
- diagnostic and related-location caps with one truncation indication;
- artifact count and generated SQL bytes;
- encoded JSON v2 bytes and compact valid failure output;
- configuration inability to raise or disable limits;
- deterministic precedence and ordering across filesystems;
- no partial output writes and preservation of an existing output;
- JSON v2 CLI-error versus diagnostic classification;
- unchanged single-file limits, diagnostics, JSON v1, CLI behavior, and output
  safety.

No project loading, multi-file compiler, JSON v2, or project budget code should
be written until Phase 8 completion audit is complete and a separately
approved implementation phase defines the deferred counters and exact future
diagnostic codes.

## Related Documents

- [Phase 7 resource/depth budget design](../plan/phase-7-resource-depth-budget-design.md)
- [Pietto project configuration schema version 1](pietto-config-v1.md)
- [Project root and path semantics version 1](project-path-semantics-v1.md)
- [Project multi-file semantics version 1](project-multifile-semantics-v1.md)
- [Project CLI and JSON schema version 2 design](project-cli-json-v2.md)
- [Phase 8 Project Model & Configuration Planning](../plan/phase-8-project-model-configuration-planning.md)
