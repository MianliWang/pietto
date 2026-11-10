# Phase77 S10/S12/S14 flat qualification pack

Status: `PREPARED_NOT_STARTED`. This pack is a parent hook for one existing
single-engine, `--network none` campaign. It neither opens a socket nor starts
a container.

## Reach

`flat_qualification.py` builds real public artifacts through the supplied
candidate compiler. Each plan closes the verified public artifact's source,
config, contract, SQL, fixed values, parameter uses, column representation,
target DDL and typed seed under that candidate's Git-tree identity and its two
actual artifact-reader identities. The required path is:

`source + contract -> check/plan -> emit_project_sql -> byte verification -> public artifact -> parent native prepared runner -> raw metadata/rows/warnings -> independent expected judge`.

Compiled and reader closure is retained by the S10/S12/S14 owner tests; this
pack consumes the same public artifact rather than reconstructing SQL.

| Case | Candidate reach | Independent expectation |
| --- | --- | --- |
| `s10_group` | conditional count, group `all`/`any` | duplicate, NULL and zero-match groups; bag `(2,false,true),(0,false,false),(0,false,false)` |
| `s12_text` / `s12_temporal` | concat/lpad and add_months/now | Unicode and NULL Text with `lpad(..., 3, "0")`; month clipping and observed UTC timestamp6 |
| `s14_join` | LEFT JOIN then `count(lower(r.label))` | `(1,1),(2,0)` bag; Int/Int non-null; unmatched right contributes zero |

`s12_temporal` Date overflow is deliberately absent: the campaign separately
records the native terminal and warnings before any portable promise is made.

## Parent hook

After the parent has created its owned endpoint, relay and native observer, it
runs the candidate environment only:

```text
UV_PYTHON=3.13.13 UV_OFFLINE=1 CANDIDATE_PYTHON -I -B flat_qualification.py \
  --repo CANDIDATE_REPOSITORY --target mysql --write-plan RUN/mysql-plan.json
```

The parent executes only each plan case's `fixture.ddl` and
`fixture.typed_seed`, then submits `candidate.sql` with exactly
`candidate.fixed_values` and `candidate.parameter_uses`. It writes a closed
`*-receipt.v2` envelope and invokes `judge.py`; extra or missing cases/fields,
substituted fixture/SQL/parameters/metadata, wrong values, warnings, terminal,
cleanup, candidate identity or reader identity all fail closed. A plan is one
candidate's preparation only, never evidence borrowed from another candidate.
