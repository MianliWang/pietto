# Phase77 S13 ordered first/last raw qualification preparation

Status: `PREPARED_NOT_STARTED`. This is a parent-owned, database-free request
builder. It opens no endpoint, creates no container, and does not claim a
Pietto compiler result or target admission.

## Scope

The candidate is limited to direct value fields and the already-proven total
internal order:

- the source's `unique(row_id)` finishes the order;
- every order key is direct and filtered non-NULL before the primitive sees it;
- `first` is the first row in `order_a ASC, order_b DESC, row_id ASC`;
- `last` is the first row after every one of those directions is reversed;
- a grouped empty input yields no row, while a global empty input yields one
  row whose ordered values are all NULL.

The seed deliberately has duplicate `(order_a, order_b)` values, NULL values,
two NULL-key rows, mixed UTF-8 text, and `-0.0`/`+0.0` Float values. NULL-key
rows are excluded by the valid candidate filter. An unfiltered rank query is
an observation-only probe: its target-specific NULL ordering must never become
a Pietto promise.

## Candidate choice

PostgreSQL's raw baseline is its existing `ARRAY_AGG(value ORDER BY ...)[1]`
shape. The MySQL raw primitive is the smallest candidate that does not encode
a value into a string or select an arbitrary representative:

```sql
SELECT
    MAX(CASE WHEN first_rank = 1 THEN value_column END)
FROM (
    SELECT
        value_column,
        ROW_NUMBER() OVER (ORDER BY order_a ASC, order_b DESC, row_id ASC)
            AS first_rank
    FROM ordered_value_rows
    WHERE order_a IS NOT NULL AND order_b IS NOT NULL
) AS ranked
```

One ranked row can contribute a non-NULL value to each conditional `MAX`; a
selected NULL stays NULL. The campaign must prove that this preserves each
direct carrier's native metadata and Float bits. It must not silently turn a
carrier into JSON or text.

`JSON_ARRAYAGG`/`JSON_EXTRACT` are not selected: JSON is not the direct typed
carrier. `GROUP_CONCAT`, formatted composite keys, hashes, and `ANY_VALUE` are
out: they either stringify/collapse values or choose a representative. No raw
SQL below is Pietto-emitted SQL.

## Parent hook

After the existing one-engine lock, endpoint, relay, and prepared native
observer are active, the parent may write and inspect the finite request:

```text
UV_PYTHON=3.13.13 CANDIDATE_PYTHON -I -B raw_hook.py --selfcheck
UV_PYTHON=3.13.13 CANDIDATE_PYTHON -I -B raw_hook.py --request
```

For each target the parent must execute the listed DDL, seed using the listed
typed parameter rows, perform the direct seed readback, then submit only the
listed raw primitives through its existing prepared runner. It records SQL,
typed binds, positional metadata, rows, warning list and terminal separately.
The independent oracle derives expected selected `row_id`s from the literal
fixture, not from candidate SQL; it compares selected values to the direct
readback of those rows (including Float bits). Failures, raw statements and
readbacks are retained by the parent.

This preparation adds no product files, test owner, resource framework,
database run, Gate 2, commit, or decision. A product change still needs a
qualified public compiler artifact and the normal project/reader closure.
