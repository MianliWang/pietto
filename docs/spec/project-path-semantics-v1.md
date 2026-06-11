# Pietto Project Root And Path Semantics Version 1

## Status

This document defines the planned root, path, glob, file-identity, display-path,
and ordering contract for a future Pietto project mode.

**The contract is not implemented.** Pietto does not currently discover
project roots, read `pietto.toml`, expand source globs, traverse project files,
or compile multiple files. The current CLI and JSON schema version 1 remain
single-file interfaces.

This specification supports future project/configuration and multi-file
planning. It does not authorize filesystem or CLI implementation.

## Goals

The path model must provide:

- explicit and reproducible project identity;
- containment of configuration, source selection, and output paths;
- stable project-relative paths for diagnostics and tools;
- deterministic source and SQL artifact ordering;
- consistent behavior across Linux, macOS, Windows, and WSL;
- clear symbolic-link, hard-link, duplicate-file, and traversal rules;
- bounded path and glob work before compiler stages begin.

The current single-file path behavior remains the compatibility baseline.

## Project Root Model

The first project implementation should require an explicit project root. The
accepted future CLI direction is `--project ROOT`, mutually exclusive with
the existing positional single-file path, as documented in
`docs/spec/project-cli-json-v2.md`.

The intended root rules are:

- project mode begins only through an explicit project invocation;
- the selected root must identify an existing directory;
- the future configuration file is exactly `pietto.toml` directly within that
  root;
- configuration paths, source patterns, project diagnostic paths, and source
  artifact identity are interpreted relative to that root;
- the root is converted to an absolute lexical path and a canonical physical
  directory identity before source selection;
- failure to resolve or access the explicit root is a project usage or
  configuration failure, not an invitation to search another directory;
- current positional single-file paths never activate project mode.

The first implementation must not search parent directories for
`pietto.toml`. Implicit upward search risks:

- selecting an unexpected configuration file;
- changing behavior according to the current working directory;
- crossing trust boundaries in shared or untrusted directories;
- confusing nested projects and monorepositories;
- producing different CI and local results;
- making a single-file command silently become a project command.

Any later proposal for discovery requires a separate compatibility and
security review.

## Path Concepts

A future implementation should keep these concepts distinct:

| Concept | Meaning |
|---|---|
| Invocation path | The path spelling supplied by the user for the explicit project root |
| Filesystem path | The platform-native path used for filesystem operations |
| Canonical path | The physically resolved path used for containment and file identity |
| Project-relative path | A normalized `/`-separated path relative to the project root |
| Display path | Stable project-relative text shown to users in project mode |
| Diagnostic path | The display path attached to a source or configuration diagnostic |
| JSON path | A future structured project path using the same normalized project-relative spelling |
| Artifact source identity | The project-relative source path plus future file/module identity needed to attribute an artifact |

One string must not be reused for every role. In particular, a convenient
display path is not sufficient proof of filesystem containment.

## Configured Path Representation

Paths and patterns in `pietto.toml` use normalized project-relative text:

- `/` is the only separator;
- paths are relative to the explicit project root;
- absolute POSIX paths are rejected;
- Windows drive paths and UNC paths are rejected;
- `.` and `..` path segments are rejected;
- empty path segments from repeated `/` are rejected;
- a leading or trailing `/` is rejected;
- NUL and platform path separators other than `/` are rejected;
- strings are treated literally, without environment expansion, tilde
  expansion, URL decoding, or shell interpretation.

Normalized project-relative paths retain their Unicode spelling. Pietto should
not apply locale-sensitive comparison or silently rewrite Unicode
normalization forms. Filesystem identity checks must still reject two
different spellings that resolve to the same physical file.

## Canonicalization And Containment

Containment requires both lexical validation and physical resolution:

1. validate the configured project-relative path or pattern;
2. join it to the canonical project root using platform path APIs;
3. resolve selected filesystem entries before reading source bytes;
4. verify that every resolved source remains within the canonical root;
5. establish file identity and reject duplicate aliases;
6. only then read the file and enter the parser pipeline.

Lexical removal of `..` is not sufficient. A path that looks contained may
escape through a symbolic link or another filesystem alias.

Containment should use path-component relationships, not string-prefix
comparisons. For example, `/work/app2` is not inside `/work/app`.

## Cross-Platform Semantics

The configuration and display model is platform-neutral even though
filesystem operations are platform-specific:

- configured and project-relative paths always use `/`;
- deterministic sorting uses normalized project-relative strings;
- sorting compares Unicode code points, is case-sensitive, and is not
  locale-aware;
- sorting never depends on filesystem enumeration order;
- display paths preserve the accepted project-relative spelling;
- drive-qualified and UNC paths are not allowed in source patterns;
- platform-native absolute paths remain internal filesystem values;
- canonical identity follows the host filesystem's actual case and aliasing
  behavior.

On case-insensitive filesystems, names that differ only by case may identify
the same file and must be rejected as duplicate identities. On
case-sensitive filesystems they may be distinct, but their deterministic
ordering still uses the normalized case-preserving strings.

Windows paths, WSL paths, and host paths must not be implicitly translated
between namespaces. A future invocation receives a root meaningful to the
process that runs Pietto.

Filesystem Unicode normalization may differ by platform. Pietto should
preserve configured text for display but use physical file identity to prevent
duplicate compilation. Cross-platform repositories should avoid names that
differ only by case or Unicode normalization.

## Include And Exclude Patterns

The planned `[sources]` selection pipeline is:

1. validate every include and exclude pattern;
2. expand all include patterns within the root;
3. retain only regular files whose normalized path ends in `.pietto`;
4. form the union of include matches;
5. remove every path matched by an exclude pattern;
6. resolve containment and physical file identity;
7. reject duplicate identities or unsafe entries;
8. sort the final set by normalized project-relative path.

Exclude patterns always win over include patterns. Pattern array order does
not affect the selected set or final ordering.

The version 1 pattern subset should be:

- literal path segments;
- `*` for zero or more characters within one segment;
- `?` for exactly one character within one segment;
- `**` only as a complete segment, matching zero or more complete path
  segments.

The following are unsupported and should be rejected rather than ignored:

- character classes such as `[a-z]`;
- brace expansion such as `{src,test}`;
- extglob or shell-specific forms;
- backslash escaping;
- absolute patterns;
- `.` or `..` segments;
- malformed uses of `**` inside another segment.

An include may name an individual `.pietto` file or use a pattern. A bare
directory name has no implicit recursive meaning; recursive selection requires
an explicit pattern such as `models/**/*.pietto`.

Only `.pietto` regular files are accepted. Matching directories, sockets,
devices, FIFOs, or unrelated file extensions does not create source inputs.

An include list that produces no final source files is a project
configuration/input error. There are no implicit default include patterns.

## Hidden And Conventional Directories

A path segment beginning with `.` is hidden. Wildcards do not match a leading
`.` unless the corresponding pattern segment also begins with `.`. Thus,
`**/*.pietto` does not silently select `.cache/hidden.pietto`, while
`.generated/**/*.pietto` may select an explicitly named hidden tree.

Pietto does not implicitly exclude `vendor`, `generated`, `build`, or similar
directory names. Hidden defaults and tool-specific conventions reduce
reproducibility. Projects must express such exclusions explicitly.

## Symlink Policy

The conservative first implementation should:

- never follow a symbolic link to a directory during glob traversal;
- allow an explicitly selected symbolic link to a source file only when its
  fully resolved target is a regular file inside the canonical project root;
- reject links whose target is outside the root;
- reject dangling links;
- reject or contain symbolic-link loops before unbounded traversal;
- apply project containment and duplicate-identity checks after resolution.

Not following symlinked directories keeps traversal finite and avoids silently
importing a second tree. A future relaxation requires separate planning.

## Hard Links And Duplicate File Identity

Hard links and in-root symbolic links may give one physical source multiple
project-relative names. The first implementation should reject a project when
two selected paths identify the same physical file.

Rejection is preferable to choosing one alias because it:

- avoids platform- or traversal-dependent winners;
- prevents duplicate definitions and diagnostics;
- preserves one stable source identity per file;
- supports output-path protection against source aliases.

The error should identify the conflicting project-relative paths. File
identity must use platform filesystem identity or an equivalent same-file
check, not only canonical path text.

## Output Path Boundary

This document does not define project output layout. Before project output is
implemented, its design must ensure:

- output cannot overwrite `pietto.toml`;
- output cannot overwrite any source path;
- output cannot target a symbolic or hard-linked alias of a source;
- directory and final-component symlink behavior is explicit;
- validation and atomic replacement preserve existing output on failure;
- partial project failures do not create nondeterministic artifacts.

Current single-file `emit-sql --output` behavior remains unchanged.

## Diagnostic And Display Paths

Project-mode diagnostics should use stable normalized project-relative paths:

- configuration diagnostics use `pietto.toml`;
- source diagnostics use the selected source's project-relative path;
- paths use `/` on every platform;
- paths do not depend on the process working directory;
- canonical absolute paths are not exposed by default.

An error that prevents the project root from being established may need the
original invocation path because no project-relative path exists yet. The
planned JSON v2 contract represents that path on a `project_root` CLI error
while leaving the logical project root null.

Avoiding absolute paths improves reproducibility and reduces accidental
filesystem information leakage. Diagnostic messages must still use the
existing terminal-control escaping rules in text mode.

## JSON Compatibility

JSON schema version 1 remains a single-file contract. Its `path` field and
diagnostic fallback behavior must not be reinterpreted for projects.

The accepted future project JSON schema version 2 design includes:

- project root and configuration path;
- ordered normalized input paths;
- configuration and source-read errors;
- project-relative diagnostic paths;
- artifact source-file and source-definition identity;
- path normalization and ordering guarantees;
- output status and partial-failure semantics.

The project object uses logical root `"."` after root establishment to avoid
absolute-path leakage; a root failure uses `null` and attributes the invocation
spelling to its CLI error. The complete unimplemented design is documented in
`docs/spec/project-cli-json-v2.md`. This slice implements no JSON changes.

## Deterministic Traversal And Artifact Ordering

The baseline deterministic order is:

1. sort selected source files by normalized project-relative path;
2. preserve definition order within each file;
3. traverse files and definitions using that order unless dependency semantics
   require a stable graph order;
4. preserve backend artifact order for each deterministically traversed
   definition.

The project-wide ordering and stage-gating contract is documented in
`docs/spec/project-multifile-semantics-v1.md`. Any future graph order must use
normalized project-relative paths and file-internal definition positions as
deterministic tie-breakers.

Filesystem enumeration order, hash-map order, inode order, modification time,
and locale must never determine diagnostics or artifacts.

Project errors should not produce or write a nondeterministic partial artifact
set. Exact partial-result behavior remains for the multi-file and CLI/JSON
slices.

## Resource Budget Interaction

The current implemented parser/frontend budgets remain per file:

- maximum 1,048,576 UTF-8 source bytes;
- maximum 200,000 raw non-EOF lexer tokens.

A future project path layer also needs fixed limits for:

- number and total length of configured patterns;
- directory entries and path components examined;
- recursion depth for directory traversal;
- symbolic links followed and identities visited;
- selected source-file count;
- aggregate UTF-8 source bytes and tokens;
- diagnostics and SQL artifacts;
- JSON output size.

Budget checks must stop work at the first defined excess and produce
deterministic failure behavior. Configuration must not override safety
ceilings. Planning values, CLI-error versus diagnostic classification, and
deferred counter definitions are documented in
`docs/spec/project-resource-model-v1.md`.

## Security Risks

The future implementation must address:

- lexical and encoded path traversal;
- symbolic-link escape and loops;
- hard-link source/output aliasing;
- glob and directory-entry explosion;
- accidental configuration pickup through implicit discovery;
- nested-project and monorepo root confusion;
- case, separator, drive, UNC, and Unicode mismatches;
- nondeterministic filesystem traversal;
- absolute-path leakage in diagnostics or JSON;
- time-of-check/time-of-use filesystem races;
- unsafe output inside or aliased to the source tree.

Explicit roots, strict relative patterns, physical containment, duplicate
identity rejection, deterministic sorting, and bounded traversal are required
controls.

## Non-Goals

Phase 8 Slice 3 adds no:

- project-root discovery or root canonicalization code;
- configuration loading or TOML parsing;
- `pietto.toml` file or fixture;
- filesystem walking or glob expansion;
- runtime path-normalization API;
- project mode or multi-file compilation;
- module, import, or include syntax;
- CLI command, flag, or behavior change;
- JSON v2 implementation or JSON v1 change;
- SQLGlot integration, MySQL support, or SQL feature expansion;
- SQL execution, database connection, connector execution, or schema
  introspection;
- runtime server, Web UI, watch mode, or LSP/editor integration;
- `compile_to_ir()` or `compile_to_sql()`;
- grammar, generated parser, test, fixture, dependency, or lockfile change.

## Implementation Prerequisites

Before path or project discovery code is approved, an implementation plan must
cover tests for:

- acceptance and rejection of explicit project roots;
- absence of implicit upward root discovery;
- missing, non-directory, inaccessible, and aliased roots;
- configured separator, absolute, drive, UNC, `.`, `..`, empty-segment, and
  malformed-pattern rejection;
- `*`, `?`, and whole-segment `**` matching;
- individual-file selection and `.pietto` filtering;
- include union, exclude precedence, and empty final sets;
- explicit hidden-path behavior and absence of implicit vendor exclusions;
- root escape and symbolic-link escape rejection;
- symbolic-link directory non-traversal and loop containment;
- hard-link and other duplicate file identities;
- deterministic normalized sorting independent of directory order and locale;
- case-sensitive and case-insensitive filesystem cases;
- Unicode spelling and duplicate-identity cases;
- stable project-relative text and future JSON paths;
- output-path protection against source and configuration aliases;
- path, glob, symlink, file-count, and aggregate resource-budget failures;
- unchanged single-file CLI and JSON v1 path behavior.

No path, glob, or project discovery code should be written until the Phase 8
completion audit is complete and a separately approved implementation phase
addresses the documented prerequisites.
