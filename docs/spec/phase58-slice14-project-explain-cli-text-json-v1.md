# Phase 58 Slice 14 Project Explain CLI Text And JSON v1

## Scope And Route

Slice 14 extends the existing `pietto explain` command with one explicit
project mode:

```text
pietto explain --project <root> [--format text|json]
```

The parser accepts positional `path` XOR `--project`. Neither or both is a
usage error. Project mode never infers the current directory, an environment
variable, or another default root. `text` is the default and the exact format
vocabulary remains `text` and `json`.

The existing `pietto explain <file> [--format text|json]` route continues to
call its unchanged Semantic Metadata Artifact v1 implementation.

## Runtime And Exit Authority

Project mode calls `_build_project_explain_runtime(root)` exactly once and
consumes only its `ProjectExplainRuntimeBuildResult`. The CLI owns the fixed
translation:

```text
SUCCESS                 -> 0
DIAGNOSTIC_ERROR        -> 1
USAGE_OR_RESOURCE_ERROR -> 2
```

The integer exit status is not inserted into Project Explain JSON or its
runtime envelope. Slice 14 adds no project loader, package resolver, selector,
catalog selection, provider, checker, matrix, inspection, projection,
portability, or payload-composition logic.

## JSON Output

Project JSON calls only `serialize_project_explain_json_document` with the
Slice 13 envelope. Both success and runtime failure write exactly that one
document to stdout. The existing serializer retains the four-field order
`format`, `ok`, `diagnostics`, `payload`; marker
`pietto.project-explain.v1`; compact separators; UTF-8 without BOM; and exactly
one final LF. The CLI adds no prose, second newline, `outcome`, or `exit_code`.

Parser usage errors occur before a runtime envelope exists and retain the
existing argparse-style stderr behavior.

## Human Text Output

`pietto._project_explain.text.render_project_explain_text` is the one private
human renderer. It consumes an exact existing envelope and does not construct a
parallel semantic model. Success is written to stdout; runtime diagnostic and
usage/resource failures are written to stderr.

Success renders deterministic sections in this order:

```text
artifact identity and status
diagnostics
packages and direct dependencies
capability requirement collections and requests
targets, package evaluations, and matrix rows
extension catalog evidence
project and requirement portability
bounded requirement explanations
```

Empty sections render explicit `none`. Zero targets remain visibly
`indeterminate / no-evaluated-targets`; no target, UNKNOWN, or BLOCKED state is
fabricated. Failure renders ordered diagnostics and an explicit unavailable
payload. Text escapes control characters, adds no object representations,
timestamps, random IDs, terminal-width decisions, or private fields, and owns
exactly one final LF.

## Output Channels

| Condition | stdout | stderr | Exit |
| --- | --- | --- | ---: |
| Parser usage failure | empty | usage | 2 |
| Project JSON success | exact envelope | empty | 0 |
| Project JSON diagnostic failure | exact envelope | empty | 1 |
| Project JSON usage/resource failure | exact envelope | empty | 2 |
| Project text success | exact human document | empty | 0 |
| Project text diagnostic failure | empty | exact human failure | 1 |
| Project text usage/resource failure | empty | exact human failure | 2 |

No failure path creates a partial payload or converts an error into a warning.

## Compatibility And Boundaries

Project Explain JSON v1 and Semantic Metadata Artifact v1 are distinct and
unchanged machine contracts. Slice 14 adds no YAML/TOML/debug format, public
Python export, JSON schema field, database/network/registry access, package
installation, extension-installation inference, hidden target, or new command
family.

Slice 15 retains broad real multi-package/multi-target E2E assurance. Slice 16
retains differential, hash-seed, relocation, Python-version, and installed-
wheel parity. Slice 17 retains completion and Phase 59 handoff.

## Lifecycle

Phase 58 remains on the published 17-slice route. Slice 14 is the current CLI
owner; Slice 15 remains next and unstarted. Natural exact-head CI owns Slice 14
completion without a status-only follow-up commit.

`PHASE58_SLICE14_SELF_OWNED_OPEN = 0`
