### Computed let keys in single-file grouping

Single-file queries can group by and select a concrete computed `let`, using
its binding identity and inferred type as in projects. PostgreSQL and MySQL
lower the key expression in place; nullable keys retain their nullability.
The two-query form remains supported. The previous PIE-S2102 computed-key
refusal and PIE-S2329 self-selection refusal disappear for admitted keys;
non-key reads, invalid bindings and scalar expressions around aggregates
remain refused.
