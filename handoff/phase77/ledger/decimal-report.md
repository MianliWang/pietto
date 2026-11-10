# Phase77 Decimal candidate recovery

Recovered candidate base: local `f8ccd2c44a2d9adf431a496bd9bbae037783176f`.

The candidate is `candidates/decimal/decimal.patch`. It contains the final
eight Python paths recovered from the historical tool-call inputs and file-change
events. It admits MySQL project Decimal `+`/`-` with `Int`, `+`/`-` between
different-scale Decimal sources, Decimal `*` Int, and unary Decimal sign. The
same carrier law is reconstructed by emission verification, the pure boundary,
compiled semantics, and the public-artifact decoder.

Actual isolated candidate repository:
`/home/mianliwang/projects/pietto/.cache/phase77-recovery/candidates/decimal/repo`.
It was cloned locally from the `f8ccd2c44a2d9adf431a496bd9bbae037783176f`
HEAD, then received this patch. Its dirty tree contains exactly the eight paths
listed below; it is the candidate to inspect or integrate, while
`decimal.patch` remains the provenance-preserving transfer artifact.

## Recovered edits

| Path | Historical call IDs and recovered location |
| --- | --- |
| `src/pietto/_project/project_sql_emission_rows.py` | `arrow_update.jsonl:116`, `call_798f95813b5e4b1585a634784f578074`; historical code lines 1190, 1742, 1753 |
| `src/pietto/_project/project_sql_emission_verification.py` | `arrow_update.jsonl:116`, `call_798f95813b5e4b1585a634784f578074`; historical code lines 1573, 1584, 1617 |
| `src/pietto/_project/project_sql_emission_pure_boundary.py` | `arrow_update.jsonl:121`, `call_af5dc2aba09b4600bbe9207912e3fbf8`; historical code lines 1028, 1676, 1687, 1719, 1730 |
| `src/pietto/_project/project_completed_semantics.py` | `arrow_update.jsonl:141,144`, `call_e9c050f170584e24b39cf6a58df1ebcb`, corrected by `call_24870cf64d2f43d4b07452c66d02ed69`; historical code line 3822 |
| `tests/_pietto_sql_emission.py` | `arrow_update.jsonl:135,139`, `call_a12b81e8c6ab4fe28b2793adb2818991` and `call_d63e81aa25904cb3a3177cd1c0188c6e`; historical code lines 9509, 9595, 9602, 9608 |
| `tests/test_execution_compiled_families.py` | `arrow_update.jsonl:128`, `call_54114128a19040afa30f406281147c06`; historical code line 4110 |
| `tests/test_project_numeric_carriers.py` | `p77_decimal_closure.jsonl:13,15,17`, `call_1733c722914e40458759650c9c27b6b4`, corrected by `call_986c13cc5c82423d939bdee98dd77994` and `call_743af51e1d4a4457b353cfde9f89f762`; historical code lines 621, 672, 695, 717 |
| `tests/test_sql_project_scalar_expressions.py` | `arrow_update.jsonl:122` and `p77_decimal_closure.jsonl:8,24`, `call_3095b2ef5c794126858c7e653ed876ad`, `call_acd0abc3-9387-4943-9903-bb0eb5df09cd`, `call_dafb9fa29b3240cdbd1cd4a41249dad1`, and `call_6dad4121c37d42a186196ccede0372b7`; historical code lines 25, 202, 214, 2443 |

## Retained boundaries

- MySQL Decimal `SUM` remains refused.
- A non-direct `Int` producer remains refused with `PIE-B1002` and
  `arithmetic_outside_physical_range`.
- Carrier validation remains closed for precision above 65 or scale above 30.
- Float, division, and aggregate expansion are absent from this candidate.

## Evidence and limits

The candidate patch SHA256 is
`f0c86a3d77a333ccd88432d147c34299a7f1c138086b4a9c0a9d6e2b44d44650`.
It passed `git apply --check` against the local `f8` checkout during recovery.
The isolated candidate repository also passed `git diff --check` and Python
3.13 `py_compile` over all eight changed Python paths after the patch applied.

The original closure session recorded 31 focused cases, `py_compile`, and Ruff
over these eight files. Those are historical observations only; no pytest,
database run, Gate 2, commit, or publication was run during this recovery.

The historical raw candidate directory no longer exists. The patch was rebuilt
from the actual `apply_patch` inputs plus the final full-diff tool output. The
only correction inferred from the event sequence is the indentation repair in
`project_completed_semantics.py`; its final form is explicitly confirmed by
`call_24870cf64d2f43d4b07452c66d02ed69`. No other missing edit is asserted.
