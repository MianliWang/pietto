### Decimal multiplication by Int and unary signs

`Decimal * Int` and `Int * Decimal`, and unary `+` and `-` of Decimal,
now pass semantic checking. Single-file PostgreSQL and MySQL emission
renders these forms, including `sum(amount * n)` for an Int field `n`.
PostgreSQL projects retain an exact `Decimal(p+19,s)` product carrier while
`p+19 <= 65`; unary signs preserve `(p,s)`. Qualified Decimal/Int header
parameters use the same rule. MySQL project forms remain refused.

This removes the former `PIE-S2105` messages and JSON suggestions
`a Decimal multiplies only by a Decimal; Decimal times Int is not supported yet`
and `a Decimal has no sign operator yet; write ...` for these forms, and the
single-file product aggregate's `PIE-B1000`. Decimal/Float arithmetic still
reports `PIE-S2105`; same-scale Decimal parameter addition and parameter
Decimal/Decimal multiplication keep their refusal, as do project Decimal
division and `avg`. Products wider than 65 digits remain `PIE-B1002`.
