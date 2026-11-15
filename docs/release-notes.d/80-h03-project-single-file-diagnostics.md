### Project aggregate diagnostics as in a single file

In an EXPLICIT_MODULES (`schema_version = 2`) project, a table or query with
aggregates and no JOIN input that reads a `let` name now reports the errors
that a single file reports of its aggregates, grouping, grouped ORDER BY,
`having` and LIMIT, in place of the bare PIE-S2333 `Project relation semantic
completion is unavailable: <name>` at the declaration, where a single file
reads the `let` name as its value; beside a generator test's error it no
longer drops them. Such a relation, with or without a
`let` read, lists these errors in source order, as a single file does,
where `0.2.0` listed an aggregate's own error first. A project relation's
`first` or `last` order proof error, which `0.2.0` listed after them, now
comes after the errors of its relation that precede it in source, just
before the first error of the relation listed after all of those, and so
before any error of another relation that `0.2.0` listed between them; with
none listed after them it still comes after the errors of the other checks.
Errors of
different relations otherwise keep the project's stage order, so another
relation's projection error can still come first, as in `0.2.0`. Beside a
`let` and projection name conflict (PIE-S2329), a read of the refused
binding is no longer reported again, a binding with an error of its own that
an aggregate reads as its direct argument is reported only at the binding,
and the other bindings keep their types, as in a single file.

Changed diagnostics (programs refused in `0.2.0`; no accepted program
changes), each over a relation that reads `let q2 = qty * 2` in
`m = sum(q2)` unless the row says otherwise:

| Case | Before (`0.2.0`) | After |
| --- | --- | --- |
| `count(nope)` or `sum(nope)` | PIE-S2333 at the declaration | PIE-S2102 `Unknown field: nope` at the argument |
| `sum(label)` of a `Text` field | PIE-S2333 at the declaration | PIE-S2314 at the call |
| `limit -1` without GROUP BY | PIE-S2333 at the declaration | PIE-S2307 at the LIMIT |
| An unknown GROUP BY key, grouped ORDER BY key or `having` output | PIE-S2333 at the declaration | PIE-S2102, PIE-S2321 or PIE-S2324 at it |
| Such an error under a computed or aliased `let` GROUP BY key (`let big = qty > 1` then `group by big`, or `let k = label` then `group by k`) | PIE-S2333 at the declaration, or beside a generator test's error the test's PIE-S2105 alone | the single file's error at it |
| A computed `let` GROUP BY key's own refusal (`let bucket = amount * 2`): a `let` alias of it as the key (`let alias = bucket`, then `group by alias`), the key listed twice, or a `having` reference to its selected output (`b = bucket`, then `having b > 0`) | PIE-S2333 at the declaration | the single file's PIE-S2102 ``Unknown field: alias; a query cannot group by a computed `let` value here yet: ...``, PIE-S2317 or PIE-S2326 at it |
| `sum(nope)` or `limit -1` beside a generator test's error (`sum(1 for o in group if o.label > 1)`) | the test's PIE-S2105 alone | the PIE-S2102 or PIE-S2307 too, in source order |
| `sum(o.nope for o in group if o.label > 1)` | the test's PIE-S2105 alone | PIE-S2102 `Unknown field: nope`, then the PIE-S2105 |
| `stddev`, `variance`, `pvariance`, `pstdev`, `median` or `quantile` of a `let` that PIE-S2329 refused | the PIE-S2329, then PIE-S2315 and PIE-S2102 `Unknown field: <let>` at the call | the PIE-S2329 alone |
| Such a call of a `let` with an error of its own (`let v = nosuch`) | that error, then PIE-S2102 `Unknown field: v` at the call | that error alone |
| `count_distinct(w, id)` of a refused `let w = qty + 1` | the PIE-S2329, then PIE-S2315 at the argument | the PIE-S2329 alone |
| An `order by` key of `first` or `last` that reads a refused `let` | the PIE-S2329 alone, or with PIE-S2104 `The order of first does not end in a unique key, ...` at the call | the PIE-S2329, then PIE-S2104 `Order key of first must be a direct field` at the key |
| `sum(k)` of `let k = label` beside a refused `let` | the PIE-S2329 alone | the PIE-S2329, then PIE-S2314 at the call |
| Grouped `t = sum(nope)` before `u = sum(label)`, with or without a `let` read | PIE-S2314 of `u`, then PIE-S2102 of `t` | in source order: PIE-S2102 of `t`, then PIE-S2314 of `u` |
| A `first` or `last` order proof's PIE-S2104, or its PIE-S2334 over JOIN rows, before another error of the relation (`c = sum(nope)` after `v = first(plant, order by sold_at)`) | after the relation's other errors | after the relation's errors that precede it in source, before the next of its errors listed after them |

`check --project` and `explain --project` report the same list. A relation
is checked as in `0.2.0` when it reads a `let` name in the argument of `min`
or `max` (which a project admits and a single file refuses with PIE-S2315;
a `Text` or `Bool` one both refuse, a single file with PIE-S2314) or inside an
aggregate's expression argument (`sum(d + 1)`, where a single file reports
PIE-S2102 `Unknown field: d`); when it selects under GROUP BY a `let` name
that a single file refuses there (`k` after `let k = label`, its PIE-S2329,
or `x = k`, its PIE-S2102, with a GROUP BY hint unless the `let` has an error
of its own, which a project then reports alone); or when it reads a query
parameter, `any(...)`, a nested relation field, a relation or a captured
field. A `let` read is checked as the value it names, so as for a field, an
ORDER BY key error without GROUP BY (PIE-S2380, or PIE-S2102 for an unknown
field) and an invalid operand beside an aggregate in a projection
(PIE-S2105) are not reported beside the relation's other errors. No
diagnostic code is new and the JSON shapes are unchanged.
