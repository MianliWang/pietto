# Pietto Python Compile API v1

## Status

This is an **alpha** interface. Before the support-matrix freeze, its names,
signatures and `SqlEmission` fields may change in any `0.1.x` release; each
change gets a release-note line, with no deprecation period. The documents it
returns are the existing [project CLI JSON v2](project-cli-json-v2.md#emit-sql-result)
emission documents, whose own contract is unchanged.

## Entry Points

```python
from pietto.compiler import SqlEmission, compile_all_sql, compile_sql

compile_sql(project, *, module, kind, name, dialect, emission_contract,
            literal_policy="preserve") -> SqlEmission
compile_all_sql(project, *, dialect, emission_contract, module=None,
                kind=None, name=None, literal_policy="preserve") -> SqlEmission
```

`SqlEmission` is a frozen value with two fields: `status`, one of
`VERIFIED`, `BLOCKED` and `INPUT_REJECTED`, and `document`, the complete JSON
document as `bytes`, final newline included.

## Equality Law

For arguments of the right Python types, `compile_sql` returns as `document`
exactly the stdout bytes of

```text
pietto emit-sql --project PROJECT --module MODULE --kind KIND --name NAME
  --dialect DIALECT --emission-contract CONTRACT --literal-policy POLICY --format json
```

and `compile_all_sql` those of the same command with `--all`, where only the
selectors that are not `None` are given. The command runs on the same files
with the same interpreter. `status` is the document's top-level `status`, and
the command's exit code is 0, 1 or 2 for `VERIFIED`, `BLOCKED` and
`INPUT_REJECTED`. `compile_sql` gives `pietto.sql-emission.v1`, or
`pietto.sql-emission.v2` for a VERIFIED query with header parameters, and
`compile_all_sql` gives `pietto.sql-emission.batch.v1`.

Each value is passed as its string value (a `str` subclass included) in one
`--option=value` argument, so a value that looks like an option, such as
`-h`, `--` or `--all`, stays a value; the command reads such a value only in
that spelling. Usage messages come from the running interpreter's `argparse`,
so their text can differ between Python versions, as the command's does.

## Returned Outcomes

Every outcome that the command prints as a JSON document is returned, never
raised. This includes an out-of-domain dialect, kind or literal policy and an
empty project root (`usage`), project, configuration and contract rejections,
an absent or ambiguous selector (`emission_selector`), BLOCKED documents, and
a batch over 64 MiB (`batch_output_limit`).

## Raised Exceptions

- `TypeError` when `project` is not a `str` or `os.PathLike[str]` (a `bytes`
  path included), or another argument is not a `str`; `compile_all_sql` also
  accepts `None` for `module`, `kind` and `name`. A missing keyword argument
  is Python's own `TypeError`. Nothing is read first.
- `UnicodeEncodeError` when the document cannot be encoded. The command then
  prints `pietto: error: terminal output could not be encoded` on stderr and
  no document, with exit 2, so this case is outside the equality law.
- Any other exception is an internal error. It propagates unchanged and is
  never reported as a status.

## Resources And Scope

Each call reads `pietto.toml`, the sources and the emission contract afresh,
with the same pinned reads and identity checks as the command. It keeps
nothing between calls, writes no file (there is no `--output`), produces no
text format, and opens no database or network connection. The 64 MiB batch
limit bounds the returned bytes, not peak memory. This alpha makes no
thread-safety claim.

## Related Entries

- `pietto.execution.compile_query` compiles one query into a `CompiledQuery`
  for [execution](../execution.md). It raises `RequestRejected` for invalid
  arguments (PIE-R1001/R1002) and for a VERIFIED query that cannot become an
  execution (PIE-R1004/R1005), and `CompileRejected` for the other statuses.
  `compile_sql` prepares no execution and returns those documents instead.
- A single file is compiled with the CLI, `pietto emit-sql FILE --dialect ...`.
- `pietto.sql.emit_postgres_sql` remains, but it takes IR input and has no
  MySQL counterpart, so it is not recommended.
