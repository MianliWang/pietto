# Phase66 Slice13: Project emit-SQL CLI, Explicit Contract Input And Atomic Output v1

Slice13 delivers T13 of the Phase66 route (R24, E08, C03, C29). It adds the
installed public Project emit-SQL command over the existing verified emission
pipeline: one explicit TABLE/QUERY owner, one explicit dialect, one safely read
emission-contract file, and the existing complete versioned artifact or a
complete typed failure, as JSON, readable text or an atomically replaced
artifact file. It adds no emitter, no operator, no public Python API, no
database executor and no private observation format. Legacy single-file
`emit-sql`, CLI JSON v1 and project check JSON v2 are unchanged.

## Command

```text
pietto emit-sql --project PATH --module LOGICAL_MODULE --kind {table,query}
    --name NAME --dialect {postgres,mysql} --emission-contract FILE
    [--literal-policy {preserve,bind-safe}] [--format {text,json}] [--output FILE]
```

Project mode defaults to `--format json` and `--literal-policy preserve`
(`preserve_literals`); `bind-safe` selects the existing `bind_safe_literals`
eligibility and never caller rebind or structural-constant binding. `--dialect`
and `--emission-contract` are always explicit.

| Rule | Behavior |
| --- | --- |
| Mode detection | An `emit-sql` argv selects project mode when a token equal to `--project` or starting with `--project=` appears before the first `--`. Detection runs before the legacy JSON pre-dispatch. Tokens after `--` are positional, so `pietto emit-sql --dialect postgres -- --project` is a legacy request for a file named `--project`. |
| Exclusivity | A positional path together with `--project` is a `usage` error. Project-only options without `--project` are legacy `unrecognized arguments` (stderr, exit 2); they never activate project discovery. |
| Strict options | The project parser has no abbreviations; every singleton option (`--project`, `--module`, `--kind`, `--name`, `--dialect`, `--emission-contract`, `--literal-policy`, `--format`, `--output`) rejects repetition as `usage` instead of last-wins; unknown options, missing values and invalid choices are `usage` errors. Nothing is opened or written before argv is accepted. |
| Help | `--help` is ordinary argparse help on stdout with exit 0; it opens no project or contract. The legacy `emit-sql --help` gains only an epilog line naming the project form. |
| Usage-error channel | `usage` errors are the `pietto.sql-emission.v1` `INPUT_REJECTED` document on stdout with empty stderr and exit 2. Only an argv carrying exactly one `--format text`/`--format=text` renders the usage banner and `pietto emit-sql: error: …` on stderr instead. |

## Explicit project and contract input

The project is loaded by the existing explicit loader (`pietto.toml`, no
ancestor or environment discovery, no configless entry). Discovery failures map
one-to-one to the approved kinds `project_root`, `config_read`, `config_parse`,
`config_schema`, `project_path`, `project_glob`, `project_resource` and
`source_read` with their logical paths; a project that is not in the
`EXPLICIT_MODULES` mode is `config_schema` at `pietto.toml`. Every such failure
is `INPUT_REJECTED` with exit 2 and carries every project diagnostic already
known.

`--emission-contract FILE` is a normalized project-relative path: not absolute,
nonempty, no `.` or `..` components, no doubled or trailing separators. The
logical path (`/`-joined components) is the only path echoed. The file is opened
once through the pinned-root open contract (`path_trust._open_pinned_file`:
per-component `O_NOFOLLOW`, `O_NONBLOCK`, descriptor identity), must be a
regular file, is read with the existing 1 MiB ceiling enforced while reading
(`MAX_INPUT_BYTES + 1` bytes at most), must present the same descriptor state
after the read as before it, and the pinned root is re-verified afterwards. The
descriptor is closed on every path. Symbolic links (leaf or directory
component), FIFOs, directories, absent files, escaping paths, oversize files,
root-identity changes and unavailable filesystem identity are
`emission_contract_read` with fixed messages; OS error text, absolute roots and
raw contract bytes are never echoed. The accepted bytes are passed unchanged to
`prepare_project_sql_emission`; nothing reopens the file.

The contract keeps its strict schema (UTF-8, duplicate keys, BOM, trailing data,
unknown fields, nesting and count limits, Bool-as-ordinal, malformed selectors
and releases all `INPUT_REJECTED`; an unsupported well-formed release
`BLOCKED`/`PIE-B1003`). The contract family and `--dialect` must agree; a
conflict is `INPUT_REJECTED` `emission_contract_schema` at `target/family`, and
neither side wins.

## Owner selection and compilation

The selected owner is the unique current declaration occurrence whose logical
module path, nominal declaration kind (`table`/`query`, including a
TABLE/QUERY SET body) and declared name equal `--module`, `--kind` and
`--name`; these are the three coordinates the public `request.owner` already
publishes. Zero or several candidates are `INPUT_REJECTED` `emission_selector`.
Import facades are never owners; the same spelling in another module is a
different owner with its own outcome.

Compilation reuses the production owners in their established order: parse-only
project check, completed semantics, query-block IR with verification and the
analysis bundle, `build_project_sql_plan` and `verify_project_sql_plan` with the
selected policy, `prepare_project_sql_emission` over the accepted contract bytes,
`realize_project_sql`, and `serialize_project_sql_emission` with its final
verifier. A whole-project parse or semantic ERROR is `BLOCKED` with exit 1, all
original diagnostics in order, no `cli_errors` and no candidate SQL. The command
never constructs a VERIFIED document itself: every document, including a usage
error, is the serializer's bytes.

## Output channels and atomic file

| Outcome | JSON (default) | Text | `--output FILE` | Exit |
| --- | --- | --- | --- | --- |
| VERIFIED | the serializer bytes, one document with its final newline, on stdout; stderr empty | labeled presentation on stdout: format/status, target and environment, owner, literal policy, sources, the accepted contract (canonical JSON), the complete verbatim SQL between `sql:` and `end sql`, then every `fixed_values`, `parameter_uses`, `columns`, `requirements` and `ranges` record as one canonical JSON line, and diagnostics | the same complete JSON artifact bytes as JSON stdout, in either format | 0 only when every requested channel succeeded |
| BLOCKED | document on stdout, stderr empty | document rendered on stderr, stdout empty | nothing written | 1 |
| INPUT_REJECTED | document on stdout, stderr empty | document rendered on stderr, stdout empty (usage: banner form) | nothing written | 2 |

`--output` keeps the ordinary CLI pathname interpretation (relative to the
working directory, not project-contained). Before compilation a symbolic link, a
non-regular existing destination or a missing parent directory is `output_path`.
Immediately before publication the destination is checked again and rejected as
`output_path` when its resolved path, or its `(device, inode)` identity when it
exists, equals the project configuration, any selected project source (selected
or not for this owner) or the emission contract; hard links, normalized aliases
and symlinked directory aliases are therefore refused, and a different file that
merely shares a name is not. Only VERIFIED publishes: the bytes are written to a
same-directory temporary file and installed with one `os.replace` after
compilation, verification and serialization are complete. A creation, write,
close, replacement or cleanup failure leaves an existing destination unchanged
and an absent destination absent, removes only this invocation's temporary file,
and reports `output_write` (cleanup failure as a second `output_write`) as an
`INPUT_REJECTED` document with no success payload and exit 2.

The file is replaced before the presentation is written. If stdout then fails
(write or flush), the exit code is 2, stderr receives
`pietto emit-sql: error: standard output could not be written` (with
`; the replaced artifact file is kept` when a file was replaced), and the file is
neither rolled back nor claimed absent. Without a file, a stdout failure is
likewise not success and no second document is appended. No crash-atomic stdout,
cross-channel transaction or power-loss durability is claimed.

Failure documents never echo the absolute root, the user's raw path arguments,
source or contract text, OS exception text or environment values. Successful
artifacts remain source/value-bearing as before.

## Independent consumption and installed evidence

The data-only public decoder now accepts the complete approved CLI error kinds
(`usage`, `unsupported_dialect`, `project_root`, `config_read`, `config_parse`,
`config_schema`, `project_path`, `project_glob`, `project_resource`,
`source_read`, `output_path`, `output_write`, `emission_contract_read`,
`emission_contract_schema`, `emission_selector`) and nothing else; the record
shape stays `kind,message,path`.

Every public document the command produces is byte-identical to the installed
API artifact for the same source, contract and policy. The principal test proves
this byte equality directly for representative direct, imported, SET,
multi-stage, C03 fixed-value, BLOCKED and INPUT_REJECTED inputs on both dialects,
and covers dispatch, containment, strict input, real-filesystem output, protected
aliases, stubbed I/O and stdout faults, decoder refusal and legacy compatibility.

The package smoke runs the installed console as a real subprocess over the README
example project (JSON, text with `--output`, and a selector rejection). The
target facility adds one case, `CLI_console_emission`, driven by the same copied
probe in `console` mode: the isolated installed interpreter runs the console
entrypoint through `runpy` with real argv over real project and contract files
from an unrelated working directory for six frozen witnesses:

| Witness | Input | Form | Expected |
| --- | --- | --- | --- |
| W1_table_text_output | G_emission_table_bag/bag | table, text, `--output` | VERIFIED, submitted |
| W2_fixed_bind_json_output | R_fixed_direct/table_bind | table, bind-safe, json, `--output` | VERIFIED, submitted (C03) |
| W3_imported_json | N_imported_chain/bag | query, json | VERIFIED, submitted |
| W4_set_json | S_set_forms/union_all | query, json | VERIFIED, submitted |
| W5_rejected_json | K_emission_rejected/duplicate_selector | query, json | INPUT_REJECTED, exit 2, zero submissions |
| W6_blocked_json | L_emission_blocked/missing_source | query, json | BLOCKED, exit 1, zero submissions |

The receipt stays within its 32 MiB ceiling: each console record carries the
witness input identity, exit code, stderr, the SHA-256 of stdout, of the artifact
file and of the consumed document, and the verbatim stdout only for the text
witness. The console document is identified against the API record of the same
input, whose complete bytes the receipt already carries, by SHA-256 (the
facility's transfer identity); the harness requires equal digests, the expected
status and exit code, empty stderr, `stdout == artifact file` for JSON with
`--output`, no file without `--output`, and the text presentation containing the
complete SQL. Submissions use the decoded API bytes of that identity and the
existing per-variant row/metadata oracle. Required same-child origins add
`pietto.cli` and `pietto._project.project_sql_emission_cli` to the emission
owners the CLI loads; the private inspection module remains a probe-child origin
only. The denominator becomes 61 cases/187 public documents per target
(181 API-generated and 6 console): postgres 154 VERIFIED, 4 INPUT_REJECTED,
29 BLOCKED; mysql 151 VERIFIED, 4 INPUT_REJECTED, 32 BLOCKED. Receipt v2 fields,
pins, the 120 s probe deadline and the 30 s legacy child deadline are unchanged;
the console child uses the same 30 s deadline.

## Consuming BIND output

A `bind-safe` artifact is a complete SQL/value/use/contract unit. The SQL carries
server parameter forms (`$n` on PostgreSQL, `?` on MySQL); `fixed_values` are the
exact tagged logical values (Int as decimal text, Float as binary64 hex with the
authored sign kept as unary SQL structure, Bool, Text); `parameter_uses` map each
SQL occurrence to its slot, server index, physical type and UTF-8 byte range.
The physical relation and column names come from the emission contract's source
descriptions, which the user writes for the actual database. Executing the bare
SQL without the value/use map, or rebinding values, is outside the contract.

## Retained non-support

No configless project, ancestor discovery, `pietto.toml` default dialect, SQL-only
BIND export, caller rebind, partial-error policy, multi-owner emission, second
JSON parser or renderer, product executor or private observation format is
added. Slice14 owns private emission observation, Slice15 expanded conformance,
Slice16 audit-only closure.
