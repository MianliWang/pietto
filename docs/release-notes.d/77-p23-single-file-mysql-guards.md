### Single-file MySQL Text literals and table names

- Single-file MySQL SQL wrote a backslash in a Text literal as `\\` and a
  line feed, carriage return, tab, backspace or Ctrl-Z as a backslash
  escape, which MySQL reads as another value under the `sql_mode`
  `NO_BACKSLASH_ESCAPES`: a WHERE test then compared the column with
  another value. A Text literal that holds a backslash or a control
  character is now written as its UTF-8 bytes in hexadecimal with the
  `_utf8mb4` introducer, as project MySQL SQL writes its Text literals in
  hexadecimal. MySQL reads it the same in every `sql_mode` and compares it
  under the column's collation, as any other literal. Another Text literal
  is unchanged, and no PostgreSQL or project Text literal changes.
- A single-file `mysql.table` string with a part that ends with a space or
  holds `/`, `\` or a character outside the Basic Multilingual Plane now
  fails `check` with PIE-S2306 at the string, as project SQL emission
  refuses such a name; MySQL `emit-sql` wrote it before. `check` knows no
  dialect, so a file that declares such a source no longer emits
  PostgreSQL SQL either, even when no statement reads that source. As for
  any `check` error, `emit-sql` of such a file reports only the `check`
  diagnostics, also for a statement that emission refused before. A string
  with a part that holds NUL or has more than 64 characters still passes
  `check`, even when its other part would fail it, and keeps its PIE-B1000
  from MySQL `emit-sql`. No PIE code is added and no JSON shape changes.

Changed single-file MySQL SQL (measured at `a015afcf`):

| Pietto | Before | After |
| --- | --- | --- |
| `where name == "a\\b\nc"` | ``WHERE `name` = 'a\\b\nc'`` | ``WHERE `name` = _utf8mb4 X'615c620a63'`` |
| `tag = "it's \\ ok"` | `` 'it''s \\ ok' AS `tag` `` | `` _utf8mb4 X'69742773205c206f6b' AS `tag` `` |
| `"\b\n\r\t"` | `'\b\n\r\t'` | `_utf8mb4 X'080a0d09'` |
| `"O'Reilly"`, `"你好"` | unchanged | unchanged |

New refusals (programs accepted before):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-S2306 | `mysql.table("𠀀.users")`, `mysql.table("app.users ")`, `mysql.table("   ")`, `mysql.table("app/users")` | `check` passes; MySQL `emit-sql` writes ``FROM `𠀀`.`users` `` and the like | `Invalid source connector arguments for mysql.table: a table or database name must not end with a space or hold /, \ or a character outside the Basic Multilingual Plane` |
| PIE-S2306 | a file whose `table q` reads `postgres.table("app.users")` and that declares an unread `mysql.table("app/users")` source | `check` passes; PostgreSQL `emit-sql` writes `FROM "app"."users"` | the same PIE-S2306 at the `mysql.table` string |

Changed diagnostics (programs refused before):

| Program | Before | After |
| --- | --- | --- |
| PostgreSQL `emit-sql` of a `table q` that reads `mysql.table("app/users")` | PIE-B1000 `PostgreSQL SQL emission is not implemented for RelationIR: q. PostgreSQL relation emission requires postgres.table(Text)` | PIE-S2306 at the `mysql.table` string |
| `emit-sql` for either dialect of another statement that emission refused, in a file that declares such a `mysql.table` source, such as a MySQL `table q` that reads `postgres.table("app.users")` | that statement's own refusal, here PIE-B1000 `MySQL SQL emission is not implemented for RelationIR: q. MySQL relation emission requires mysql.table(Text)` | only the file's PIE-S2306 |
