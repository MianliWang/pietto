### A Float literal product that rounds to zero is refused

Project SQL folds `+`, `-` and `*` of two `Float` literals when it is
emitted. A product of two non-zero literals that rounds to zero, such as the
square of 1e-195 written as a decimal literal, is now BLOCKED with
`PIE-B1002` `float_result_not_finite` on PostgreSQL and MySQL and under both
literal policies, as an overflowing one already was. Plain verification and
compiled replay apply the same rule, and so does a binding: the two `Float`
literal slots of a bind-safe template refuse such a pair of values, such as
1e-195 and 1e-195 or 5e-324 and 0.5, with `PIE-R1004` `BINDING_INVALID` on
both targets. On MySQL, a nested product of literals that was already
BLOCKED, such as `2.0 * (a * b)` with such an inner product, now reports the
inner product's `float_result_not_finite` instead of `PIE-B1003`
`float_literal_operands_required`, and a sign over such a product, such as
`-(a * b)`, reports it instead of `PIE-B1003`
`unary_sign_requires_int_operand`.

Before, such a statement was VERIFIED, although the targets' rules for `*`
disagree on it: PostgreSQL's float8 `*` fails it with SQLSTATE 22003
(`value out of range: underflow`), also with the factors as bound
parameters, while MySQL's DOUBLE `*` returns `0.0`. So one statement would
give a different result on each target. A subnormal product, a product with
a zero factor and a sum or difference that is exactly zero keep their value,
as neither target fails them.

Compiling a query now folds only the operands that emission folds: two
direct literals, each possibly signed. Before, it also folded a `let` that
holds a `Float` literal, which the SQL reads as a column and PostgreSQL
checks when the statement runs. So on PostgreSQL a `let x` that holds
10^300, written out as a decimal literal, with `r = x * x` was VERIFIED, but
`compile_query` refused it with `PIE-R1004` `COMPILED_PHYSICAL_DOMAIN`. It
now compiles, and every reader accepts it, as it accepts a `let` that holds
1e-195, which the underflow rule would otherwise have refused the same way.

- Breaking: a statement with such a product, which was VERIFIED, is now
  BLOCKED on both targets. On MySQL it ran and returned `0.0`, such as the
  square of 1e-195; on PostgreSQL it failed with SQLSTATE 22003 when it
  ran.
- Breaking: the two `Float` literal slots of a bind-safe template now refuse
  a pair of values whose product rounds to zero, such as 1e-195 and 1e-195,
  with `PIE-R1004` `BINDING_INVALID`, where MySQL returned `0.0` and
  PostgreSQL failed with SQLSTATE 22003.
- Breaking: on MySQL, a nested product or a sign over such a product, which
  was already BLOCKED, reports `PIE-B1002` `float_result_not_finite` in
  place of a `PIE-B1003` detail.

Compatibility: these outputs change:

| Code or output | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1002 `float_result_not_finite` | a product of two non-zero `Float` literals that rounds to zero, on PostgreSQL and MySQL | VERIFIED; MySQL returned `0.0`, PostgreSQL failed with SQLSTATE 22003 | BLOCKED |
| PIE-R1004 `BINDING_INVALID` | a bind-safe template's two `Float` literal slots bound to such a pair, such as 1e-195 and 1e-195 or 5e-324 and 0.5 | bound; MySQL returned `0.0`, PostgreSQL failed with SQLSTATE 22003 | refused |
| MySQL blocker | `2.0 * (a * b)` or `-(a * b)` over such a product `a * b` | `PIE-B1003` `float_literal_operands_required` or `unary_sign_requires_int_operand` | `PIE-B1002` `float_result_not_finite` |
| PIE-R1004 `COMPILED_PHYSICAL_DOMAIN` | `compile_query` on PostgreSQL of a `let x` that holds 10^300 with `r = x * x` | refused | compiles |

No diagnostic code or detail is added, and no CLI JSON v1, project JSON v2 or
artifact shape changes. Single-file SQL, which writes such literals as SQL
number text, is not affected.
