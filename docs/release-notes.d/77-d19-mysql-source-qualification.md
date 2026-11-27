### MySQL source refusals of Pietto's reader are `PIE-R2007` or `PIE-R3004`

On the `mysql_rows` route, when Pietto's own MySQL source reader refuses
a source as the attempt opens, entering the handle that `execute()` returns
now raises `AttemptFailed` with the refusal's word as the detail:
`PIE-R3004` (`RESOURCE_LIMIT`) with one of the six words of the reader's
fixed bounds below, as PostgreSQL's and SQLite's source limits are, and
`PIE-R2007` (`SOURCE_QUALIFICATION`) for every other refusal with the
cause `ViewSourceError`. Among the latter are:

- a source view, or a view that such a view reads, that MySQL records under
  another `character_set_client` or `collation_connection` than `utf8mb4`
  and `utf8mb4_0900_bin` (`MYSQL_VIEW_LEXICAL_CONTEXT`), or whose text lies
  outside the profile the reader admits (another `MYSQL_VIEW_` word, such as
  `MYSQL_VIEW_UNQUALIFIED_CALL` for a call of a function other than
  `current_user()`);
- a base table among the sources, or read by such a view, with a `VIRTUAL`
  generated column (`MYSQL_SOURCE_READ_TIME_GENERATED`);
- parentheses or expressions in a view's text nested deeper than the reader
  parses, such as more than 48 nested parentheses
  (`MYSQL_VIEW_NESTING`, which also names an unbalanced parenthesis).

The fixed bounds are more than 128 tables and views among the sources and
the objects that their views read (`MYSQL_VIEW_OBJECT_LIMIT`), more than
262,144 bytes of their `SHOW CREATE` text (`MYSQL_VIEW_DEFINITION_SIZE`), a
view text of more than 32,768 tokens (`MYSQL_VIEW_TOKEN_LIMIT`), more than
1,024 relation references in one view or in all of them
(`MYSQL_VIEW_EDGE_LIMIT`), a view's syntax tree beyond the reader's depth or
size bound (`MYSQL_VIEW_RESOURCE_LIMIT`), and invocation paths through the
views beyond its depth or count bound (`MYSQL_VIEW_SECURITY_LIMIT`). Two
other bounds of depth take the code of another refusal that their word also
names: nesting deeper than the reader parses is `PIE-R2007` with
`MYSQL_VIEW_NESTING`, as above, and a table or view that the reader
reaches more than 48 levels below a source is `PIE-R3999` with
`MYSQL_VIEW_DEPENDENCY_CYCLE`, the word of a cycle among views. The reader
reads each view once, on the first path that reaches it, so a table or view
that only a later path puts that deep, under a view already read on a
shorter path, is bounded only by `MYSQL_VIEW_SECURITY_LIMIT`, `PIE-R3004`.

- Breaking: `0.2.2` reported each refusal with the cause `ViewSourceError`
  as `PIE-R3003` (`SERVER_ERROR`, the server or the open connection
  reported an error) with no detail, although the server reported none; it
  is now `PIE-R2007` with its word, or `PIE-R3004` with one of the six
  words of a fixed bound.
- Breaking: `0.2.2` reported the bounds on the number of tables and views
  and on the size of their `SHOW CREATE` text, which the attempt checks as
  it reads the definitions, with the cause `ExecutionError`, as `PIE-R3999`
  (`ATTEMPT_UNCLASSIFIED`) with the words `MYSQL_VIEW_OBJECT_LIMIT` and
  `MYSQL_VIEW_DEFINITION_SIZE`; they are now `PIE-R3004` with the same
  words.
- Unchanged: the attempt fails at the same point, with the phase
  `admission` and the same cause; only the code, its category and the
  detail change. When the attempt's deadline has passed, `PIE-R3001` still
  wins, now with the reader's word as its detail. A source refused with
  another cause or word keeps its code, such as a MyISAM table, `PIE-R3999`
  with the detail `MYSQL_SOURCE_ENGINE`, or a table or view that the
  reader reaches more than 48 levels below a source, `PIE-R3999` with
  `MYSQL_VIEW_DEPENDENCY_CYCLE`. `save` and `save_recoverable` still end
  such an attempt with `terminal` `FAILED` and no public code.

Compatibility: these outputs of `execute()` on `mysql_rows` change:

| Code or output | Case | Before | After |
| --- | --- | --- | --- |
| PIE-R2007 `SOURCE_QUALIFICATION` | a refusal of the reader with the cause `ViewSourceError` and a word other than the six of the fixed bounds, such as `MYSQL_VIEW_LEXICAL_CONTEXT`, `MYSQL_VIEW_UNQUALIFIED_CALL`, `MYSQL_SOURCE_READ_TIME_GENERATED` or `MYSQL_VIEW_NESTING` for nesting deeper than the reader parses | `PIE-R3003`, no detail | `PIE-R2007` with the word |
| PIE-R3004 `RESOURCE_LIMIT` | a view beyond a fixed bound of the reader, with the cause `ViewSourceError` (`MYSQL_VIEW_TOKEN_LIMIT`, `MYSQL_VIEW_EDGE_LIMIT`, `MYSQL_VIEW_RESOURCE_LIMIT`, `MYSQL_VIEW_SECURITY_LIMIT`) | `PIE-R3003`, no detail | `PIE-R3004` with the word |
| PIE-R3004 `RESOURCE_LIMIT` | more than 128 tables and views, or more than 262,144 bytes of their `SHOW CREATE` text, with the cause `ExecutionError` (`MYSQL_VIEW_OBJECT_LIMIT`, `MYSQL_VIEW_DEFINITION_SIZE`) | `PIE-R3999` with the word | `PIE-R3004` with the word |
| PIE-R3001 `DEADLINE` | such a refusal with the cause `ViewSourceError` after the attempt's deadline has passed | no detail | the word as the detail |

No diagnostic code is added and no JSON shape changes.

[MySQL rows](../execution.md#mysql-rows) now states the requirements that
the reader checks and its fixed bounds. A view among a query's sources, or
read by one, must be created or replaced after
`SET NAMES utf8mb4 COLLATE utf8mb4_0900_bin`, since MySQL keeps the
creating session's values with the view; the `mysql` client started with
`--default-character-set=utf8mb4` creates views under
`utf8mb4_0900_ai_ci`, also on a server started with
`--collation-server=utf8mb4_0900_bin`. A table among a query's sources, or
read by such a view, must not have a `VIRTUAL` generated column; a `STORED`
one is admitted.
