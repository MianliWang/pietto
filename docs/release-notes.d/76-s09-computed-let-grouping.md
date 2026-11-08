### Computed let keys in single-file grouping

Single-file queries can group by and select a concrete computed `let`, using
its binding identity and inferred type as in projects. PostgreSQL and MySQL
lower the key expression in place; nullable keys retain their nullability.
The two-query form remains supported. The previous PIE-S2102 computed-key
refusal and PIE-S2329 self-selection refusal disappear for admitted keys;
non-key reads and invalid bindings remain refused. Scalar expressions around
aggregate results are covered by the aggregate-composition notes.

Semantic metadata keeps its v1 field-reference shape: computed GROUP BY keys
report all real field dependency leaves in per-key encounter order, including
repeats. A literal-only key has no field leaf; an empty `group_keys` summary
is not proof that GROUP BY is absent. Existing direct-field JSON/text bytes
are unchanged.
