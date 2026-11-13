### MySQL `Float` membership in a let with `capture` lines

- Fixed: MySQL project SQL (`emit-sql --project`, `compile_query`) emitted
  a `Float` `v in m` or `v not in m` written in a WHERE whose `m` is a let
  with `capture` lines, a correlated `IN` subquery. MySQL may flatten it
  into a semijoin, and its `Float` equality then gave wrong rows: in the
  Phase77 R01 qualification cells on MySQL 8.4.12, with the semijoin
  materialized beside a `VARCHAR(1000)` key (`where kw == o.kw` in the
  let), the outer rows whose `v` is `-0.0` or `0.0` came back twice in a
  fixture whose matching inner rows held both `-0.0` and `0.0`.
  PostgreSQL returned each row once. Every such read is now BLOCKED with
  PIE-B1003 `membership_type_pair_not_admitted` at the read, whatever its
  key, for `in` and `not in`, a nullable or non-null value, a literal or
  `None`.
- The same read as a SELECT item (`select: f = v in m`) emits as before,
  and so does a read of a let without `capture` lines or of a source
  (`where v in m` over `let m: from i`, `where v in iv`) and a correlated
  read of another type. PostgreSQL emits every form as before.
- A statement that emission refuses for another reason, such as an
  unreviewed MySQL release, reports the blockers it has without this one.
  A compiled MySQL artifact that holds such a read is refused when it is
  replayed. No PIE code is added and no JSON shape changes.

New refusals (programs accepted before):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | MySQL project `where v in m` or `where v not in m`, `v` a `Float` field and `m` a let of `capture o`, `from i`, `where kw == o.kw` (or `kn == o.kn`), `select: v` | VERIFIED: ``WHERE (`s1`.`v` IN (SELECT `e0`.`c0` FROM (SELECT `t1`.`c1` AS `c0` FROM (SELECT ... WHERE (`s0`.`kw` = `s1`.`kw`)) AS `t1`) AS `e0`))`` | BLOCKED PIE-B1003 `membership_type_pair_not_admitted` at `v in m` |
