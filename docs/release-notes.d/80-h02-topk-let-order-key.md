### A relation that a JOIN reads reports its own ORDER BY key

In an EXPLICIT_MODULES project, a relation `let` (a let with `capture` lines
joined LATERAL, a top-k per left row, included), and a table or query that
selects a value other than a field, such as a literal, a computation or a
window result, is read by a JOIN, or with FROM by a relation with JOIN
inputs, only once the project has completed it. An error that this
completion finds in the relation's own body is now reported at that error,
in place of a bare PIE-S2333 `Project relation semantic completion is
unavailable: <name>` at the declaration that reads the relation. Most
visibly, an ORDER BY key that names a SELECT output of that relation other
than a window result, as `order by: out desc` after `out = id`, is now
PIE-S2102 ``Unknown field: out; this project relation cannot order by a
SELECT output yet (restate its expression, or bind it with `let` and order
by that name)`` at the key, the rule and message of any relation that a
project completes.

A key that names a field of the relation's input is accepted as before when
the relation has no window, GROUP BY or aggregate, and so is a let that
orders by its own output when another let reads it and the JOIN reads that
let. A window relation that a JOIN reads still gets only the bare PIE-S2333
at the reader, as in `0.2.0`, when it is ordered by an input field or by its
window result or has a LIMIT, and so does a grouped relation ordered by its
output or with a LIMIT.

Changed diagnostics (programs refused in `0.2.0`; no accepted program
changes):

| Case | Before (`0.2.0`) | After |
| --- | --- | --- |
| Such a let, table or query without GROUP BY or aggregate, ORDER BY key naming its own SELECT output other than a window result | PIE-S2333 at the declaration that reads it | the PIE-S2102 above, at the key |
| Such a table or query, ORDER BY key calling an aggregate (`count()`) | PIE-S2333 at the declaration that reads it | PIE-S2308 at the key, as in a single file |
| Such a let, table or query with another error of its own, such as an unknown or ambiguous ORDER BY key (PIE-S2102), an invalid operand in its WHERE (PIE-S2105) or a captured field not yet available (PIE-S2369) | that error and PIE-S2333 at the declaration that reads it | that error alone |
| The relation of the first row, read by a JOIN with an error in its `on` (PIE-S2335) | the reader's error alone | the PIE-S2102 above and the reader's error |
| The relation of the first row, read by an `inner join` without `on` | PIE-S2333 ``... (JOIN r: write `on` with the condition ...)`` at the JOIN | the PIE-S2102 above and that PIE-S2333 |
| The relation of the first or third row, also read with FROM by a table or query without JOIN inputs that has an error of its own | PIE-S2333 at the declaration with the JOIN and the other query's error, beside the third row's error if any | the relation's error and the other query's error |

`check --project` and `emit-sql --project` report the same list. A reader
with JOIN inputs keeps the errors of its JOIN conditions, such as PIE-S2335
in its `on`; its other checks are reported once the relation's error is
fixed, as for any failed input (PIE-S2333). A relation without JOIN inputs
that reads the failed relation with FROM reads it as before. A single
file has no relation lets and accepts the table or query of the first row.
No diagnostic code is new and the JSON shapes are unchanged.
