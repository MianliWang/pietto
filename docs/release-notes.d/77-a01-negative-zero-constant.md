### A negated `-0.0` constant

- A `Float` constant or `--set` value of `-0.0` now reads as `-0.0` written
  in the file, a minus sign before `0.0`, as every other negative constant
  does. Negating it emitted `--0.0` on both targets, which PostgreSQL reads
  as the start of a comment: the rest of the line was lost, so the statement
  failed or silently dropped the output. A sign before a negative literal is
  now parenthesised.

| Case | Before | After |
| --- | --- | --- |
| `flipped = -flip` with `flip: Float = -0.0` or `--set flip=-0.0` | `--0.0 AS "flipped"` | `-(-0.0) AS "flipped"` |
| `scaled = amount * flip`, the same constant | `"amount" * -0.0 AS "scaled"` | `"amount" * (-0.0) AS "scaled"` |
