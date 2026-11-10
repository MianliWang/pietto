# Candidate contract — not an enabled MySQL capability

## Fixed retained contract

`plan.parameters` is declaration ordered.  A MySQL authored read consumes one
native use and one `?`, in rendered SQL order, even when two reads name the
same parameter.  Binding validates every declared name and value before native
statement allocation.  Compiled verification re-derives the physical carrier;
the pure reader and compiled reader must accept exactly the same carrier and
realization facts.  Values never enter emitted SQL bytes.

The current MySQL `Bool`, `Int`, `Float`, and `Text` SQL bytes and behavior;
the PostgreSQL SQL bytes and behavior; and all already-refused header positions
remain unchanged.  This candidate does not widen aliases, GROUP BY, aggregate,
window, or structural-call positions.

## Finite proposed probe surface

The probe family is only a prepared `SELECT` with a source field comparison or
selected typed expression.  For each type it records the raw prepared SQL
bytes, ordered typed values, prepare parameter metadata, execution warnings,
result metadata/rows, and the independent oracle result.

| Header tag | Candidate physical identity | Candidate prepared anchor | Accepted API value | Required boundary |
| --- | --- | --- | --- |
| `Decimal(p,s)` | `my_decimal` | `CAST(? AS DECIMAL(p,s))` | finite `decimal.Decimal` | `1 <= p <= 65`, `0 <= s <= min(p,30)`; exact scale and precision, no rounding or clamping |
| `Date` | `my_date` | `CAST(? AS DATE)` | exact `datetime.date`, not `datetime` | civil `1000-01-01` through `9999-12-31` |
| `Timestamp` | `my_datetime6` | `CAST(? AS DATETIME(6))` | naive `datetime.datetime` | civil range, exact six fractional digits, data and control sessions at `+00:00` |
| `UUID` | **unselected** | hypothesis only: `CAST(? AS BINARY(16))` | exact `uuid.UUID` | a reviewed, observed canonical UUID to 16-byte argument conversion; standard byte order, high-bit inputs, and NULL |

The first three SQL spellings are qualification hypotheses, not current output

The existing `parameter_text()` path is intentionally not reused as a MySQL
Likewise, the current renderer calls `anchor_suffix(physical_type)` without a
Decimal storage argument, so `DECIMAL(p,s)` cannot be enabled just by filling
`HEADER_PHYSICAL["mysql"]`.

## Required negative behavior

- `None` is accepted only for a nullable declaration and is sent as one bound
  NULL per authored MySQL occurrence; it never becomes SQL text `NULL` or an
  omitted argument.
- A Decimal with excess scale or precision, non-finite Decimal, a `datetime`
  passed to `Date`, aware/out-of-civil-range `Timestamp`, and a non-`UUID`
  UUID input fail binding before prepare/execute.
- One declaration read twice produces two `?` bytes, two metadata positions,
  and two native argument positions in SQL order.  It is not deduplicated as
  PostgreSQL `$n` is.
- A malicious string that is not the declared typed value is rejected before
  prepare.  A valid bound Text control containing SQL punctuation is data only:
  raw SQL bytes, placeholder count, and prepare metadata remain invariant.
- Any prepare or execute warning is evidence to diagnose, not a successful
  qualification; warnings cannot be suppressed or converted into a result.

## Pre-gate decision

UUID encoding is `USER_DECISION_REQUIRED`: choose an observed driver argument
