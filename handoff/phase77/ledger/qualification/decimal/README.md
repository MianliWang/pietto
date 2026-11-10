# Phase77 Decimal target-qualification preregistration

Status: `PREPARED_NOT_STARTED`.  This package has no database client,
container, resource wrapper, credentials or target result.  The builder uses
the candidate's public project-compile fixture to materialize per-target JSON
for the existing Decimal closure; the later flat runner alone executes SQL.

`postgres.json` and `mysql.json` use the agreed target envelope:

```json
{"target":"...","cases":{"name":{"candidate":{},"expected":{},"terminal_policy":"..."}}}
```

The positive cases carry public source/contract provenance, actual emitted SQL,
fixed values, parameter uses, output columns, target DDL/seed/ordering rule and
an independent Decimal oracle.  The result representation is exactly the
public carrier (`false` for unary source reads, otherwise `"unknown"`); the
source carriers are non-null, so no fixture invents a NULL Decimal outside the
contract.  The negative cases carry no SQL and must stay compiler
terminals.  Precision 65/scale 30 is a successful exact Decimal case; 66/30
is a compiler terminal, not a target-overflow query.

Build without a database:

```sh
python -I -B build_decimal_plan.py --candidate-root /tmp/pietto-p77-s17s19-4jbLrY/repo --output .
python -I -B build_decimal_plan.py --output . --self-check
```
