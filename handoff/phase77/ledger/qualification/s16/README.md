# Phase77 S16 Text-window qualification

Status: `PREPARED_NOT_STARTED`. This package only invokes the candidate's
public project compiler. It owns no connection, container, credential, native
result, or qualification claim.

`build_s16_plan.py` writes the shared strict v2 plan envelope: candidate
identity, public/compiled reader identities, a closure digest, then the exact
source, config, contract, public artifact, SQL, fixed values, parameter uses,
columns, DDL and typed seed. The parent campaign executes exactly that material
with its existing prepared runner and retains raw metadata, values, warnings,
EOF and cleanup outcomes in the matching receipt envelope.

The seed orders four rows by `id`, which is the authored window order. Result
comparison is an unordered bag keyed by `id`; it preserves all four rows and
does not invent a final SELECT ordering. The expected rows distinguish an
empty Text default, a Unicode default, a source NULL and an omitted default
for both `lag` and `lead` boundaries.

MySQL is accepted only if every window output has Text metadata that maps to
`my_utf8mb4_text`: type code 253, charset 309, no binary flag and decoded
Python `str`. A bytes value, BLOB/BINARY/VARBINARY metadata or a binary flag is
a failed qualification cell, even if displayed characters look correct.

```text
UV_PYTHON=3.13.13 CANDIDATE_PYTHON -I -B build_s16_plan.py \
  --candidate-root /tmp/pietto-p77-s16-tZYZTX/repo --output .
UV_PYTHON=3.13.13 CANDIDATE_PYTHON -I -B build_s16_plan.py --output . --self-check
UV_PYTHON=3.13.13 CANDIDATE_PYTHON -I -B build_s16_plan.py --output . \
  --judge-self-check /tmp/pietto-p77-flat-qualification/judge.py
```

The last command is a no-database schema self-check. It proves the shared judge
rejects false Text metadata, a binary flag, altered values/NULL, reordered
metadata, extra receipt fields and a grafted case. Result row order itself is
not rejected because this selected query has no final `ORDER BY`; its oracle is
a bag keyed by `id`.

The later two-database campaign must additionally prove that a field default
remains refused and that PostgreSQL retains `E'...'` while MySQL emits `X'...'`.
No plan output is database evidence.
