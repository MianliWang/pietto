### MySQL refuses a typed parameter that a plain projection never reads

MySQL project emission reported VERIFIED, with SQL that has no placeholder
for the parameter, for a query that declares a `Decimal(p, s)`, `Date`,
`Timestamp` or `UUID` header parameter and never reads it, when its SELECT
items are only fields and literals, signed or not, over its source or over
upstream queries or tables that select the same way, such as:

```pietto
query result(day: Date):
    from words
    select:
        id
        k = 1
```

The [language page](../language.md#query-header-parameters-in-explicit-module-projects)
and the notes of [`0.1.10`](../release-notes.md#typed-project-query-parameters)
and [`0.1.12`](../release-notes.md#mysql-project-decimal-date-and-timestamp-parameters)
state that MySQL emission refuses such a declaration, read or not, and
compiled replay did refuse it, so `pietto.execution.compile_query` never
returned such a query and no execution entry ran its SQL. Emission now
refuses it too: PIE-B1003 `query_parameter_type_not_admitted_on_target` at
each such declaration in header order, the same document that the same
header over a body with a WHERE reports. Like that body's, its document
then reaches no stage after emission that only a `VERIFIED` document
reaches (the list below the table), so it reports none of their refusals
and writes nothing, though, as that body's, it is still refused with
`project_path` where one of its own blockers or diagnostics is located in a
project file whose name is not UTF-8 (the fifth row). In
`emit-sql --project --all` and `pietto.compiler.compile_all_sql`, only that
query's own document changes, and every other item's document is as before
where the batch listed items, but the batch is no longer `VERIFIED`, so
`--output DIR` writes nothing, not even another query's artifact, and its
64 MiB output limit counts the new document (the last row).

Changed diagnostics (programs no execution entry ran; every other program,
PostgreSQL's included, is unchanged):

| Entry | Before (`0.2.1`, measured at `f82bb79e`) | After |
| --- | --- | --- |
| `pietto emit-sql --project`, with or without `--all` | `VERIFIED` with that SQL, exit 0, and `--output` written | `BLOCKED` with the blockers above, exit 1, and nothing written |
| `pietto.compiler.compile_sql` | a `VERIFIED` document with that SQL | a `BLOCKED` document with the blockers above |
| `pietto.execution.compile_query` | `RequestRejected` with PIE-R1004 `QUERY_NOT_EXECUTABLE` (detail `COMPILED_PHYSICAL_DOMAIN`, or `COMPILED_PARAMETER` for a query that declares a `UUID`) | `CompileRejected` with the blockers above |
| any of these for such a query that another rule refuses, such as one whose contract names an unreviewed MySQL release, other than at a stage of the next row | that rule's blockers | the same blockers with the ones above where a body with a WHERE reports them: after a premise conflict (`inconsistent_declared_scope`) and `target_release_not_reviewed`, and before every other blocker, the query's own literal-sign refusals included, such as `literal_leaf_representation` for an item `k = 9223372036854775808` |
| any of these for such a query refused only at a stage after emission that only a `VERIFIED` document reaches, each listed below | that stage's refusal: PIE-B1007 `sql_byte_limit` or `public_artifact_byte_limit` alone; `INPUT_REJECTED` with `project_path`, `output_path`, `output_write` or `batch_output_platform` (exit 2; a batch refused this way lists no item); or exit 2 with the error of a standard output that could not be written or encoded, which ends `; the replaced artifact file is kept` once an `--output` file or directory was written | the blockers above alone, as a body with a WHERE reports them, exit 1 (in JSON, a standard output that cannot be written is still exit 2, with the error alone), and nothing written, unless one of them or a diagnostic of the document is located in a project file whose name is not UTF-8: then, as for that body, `INPUT_REJECTED` with `project_path` naming that file (exit 2) and the blockers located elsewhere, so that a query in such a module names its own module where `0.2.1` named the project's first such file, and a query beside a warning located in such a file lists the blockers above beside `project_path` |
| `pietto emit-sql --project --all` and `pietto.compiler.compile_all_sql`, whose batch has a 64 MiB output limit | the batch with those documents, or `INPUT_REJECTED` with `batch_output_limit` (exit 2) where they took it past the limit | the batch with the documents above, which can fit the limit where those did not (then `BLOCKED`, exit 1, unless another item is `INPUT_REJECTED`), or pass it where they fit (`INPUT_REJECTED` with `batch_output_limit`, exit 2) for a list longer than the document it replaces, as for a query that declares many of these parameters or that another rule refuses |

The stages after emission that only a `VERIFIED` document reaches, which
such a query no longer reaches, are, in the order the entries run them:

- realization's byte limits, 8 MiB of SQL or a 16 MiB document, or less
  under the contract's `resource_limits` (PIE-B1007 `sql_byte_limit` or
  `public_artifact_byte_limit`);
- the encoding of the document, which names the project's source files:
  another project file whose name is not UTF-8 is refused with
  `project_path` (a refused document is checked instead for its own
  locations, as the fifth row says: a blocker or diagnostic located in such
  a file refuses it with `project_path` naming that file);
- the write of `emit-sql --output FILE`, refused with `output_path` for a
  project file or the contract, or for a destination that, since it was
  checked before emission, has become one that `--output` refuses, such as
  a symbolic link, and with `output_write` for a read-only file, a file of
  another user, a failed write or a temporary file that cannot be removed;
  otherwise the file is written;
- the write of `emit-sql --project --all --output DIR`, made only for a
  `VERIFIED` batch, refused with `output_write` for project inputs that
  change before it is written or for a failed write, such as under a parent
  directory this user may not write, and with `batch_output_platform` on a
  file system without safe directory output; otherwise the directory is
  written;
- in `--format text`, standard output, which gets only the rendering of a
  `VERIFIED` document, a refused one going to standard error, and is
  written only when it is not empty: a closed or full standard output or a
  closed pipe gives `pietto emit-sql: error: standard output could not be
  written`, and a stream installed without a binary buffer that cannot
  encode the text gives `pietto: error: terminal output could not be
  encoded`, each with exit 2 (under `--all`, standard output is still
  written for another `VERIFIED` item);
- in either format, the ending `; the replaced artifact file is kept` of
  the error of a standard output that could not be written, once an
  `--output` file or directory was written;
- `compile_query`'s execution template, whose refusal is the PIE-R1004 of
  the third row, and everything that follows it.

Emission reports these blockers only for a query whose body it comes to
write, as a projection, as rows or as a JOIN. A MySQL query that declares
such a parameter and that emission refuses before that keeps exactly the
blockers it had, without these: one with a plan-stage refusal, such as
`order` for `order by None is None` or `expression_evidence_unavailable` for
an output `z = None`; one refused with PIE-B1007 `generated_structure_limit`
before it is assessed; one whose statement has a table-function input (such
as a read of a `generate_series` query), a Collect read, an Unnest or an
outer aggregate composition (`aggregate_composition_not_admitted_on_target`);
one refused with `scalar_meaning_requires_field_projection`; and one whose
shape emission does not write, as for a JOIN whose `on` calls `coalesce`.
Since `0.1.10` the language page and the PIE-B1003 row of the
[diagnostics specification](../spec/diagnostics.md#backend-diagnostics) have
stated the refusal for these queries too; both now state this rule and name
these queries.
No PIE code or detail is added, and no SQL text, CLI JSON v1, project JSON
v2, artifact or bundle shape changes.
