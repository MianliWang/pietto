# Phase77 scalar candidate recovery

Base for every recovered candidate is local commit
`f8ccd2c44a2d9adf431a496bd9bbae037783176f`. Canonical worktree files were
not used as a source or edited.

## S10 — `candidates/s10`

Recovered from `editor_implementation.jsonl`:

- `call_b10b50a7ee1948ef897ba33bcdf7a3e0`: pure-boundary admission for MySQL
  `filtered_count`, `group_any`, and `group_all`; `filtered_sum` remains
  PostgreSQL-only.
- `call_4ddb8117a1f54a4284cce744c205949b` and
  `call_d906264ca1c64e859635a5b10aae9e9d`: portable-observation closure and
  retained conditional-sum rejection.
- `call_5c14934fa2474cfc9957573b89a9d216`,
  `call_dd1ad06b5eb642cba2b91fb5e2c1a0bd`, and
  `call_b2848e367cc045a5bc56a0b82fcdb67b`: compiled replay, forged-function,
  and unknown-family refusal coverage.

The candidate contains no `sum(Int)` MySQL admission.

## S12 — `candidates/s12`

Recovered production rows/rendering portions from `p77_text_date.jsonl`,
`call_1864b580579b44b494327b0763933f92`: MySQL `concat`, non-truncating
`lpad`, `add_months`, and `now` rendering/row admission.

The production readers are recovered from the recorded patch chain:
`project_sql_emission_rows.py`, `project_sql_emission_rendering.py`,
`project_sql_emission_verification.py`, and
`project_sql_emission_pure_boundary.py`.

**NEW_RECONSTRUCTION — test closure:** the overlapping historical test edits
were replaced with a new closure in the existing scalar/public-decoder owners.
It covers MySQL `now`, `concat`, Unicode fill/non-truncating `lpad`,
plain `add_months`, signed-32-bit width refusal, public decoder/pure reader,
compiled replay, and bind-slot order for conditional Text/width inputs.
Conditional Date/month inputs remain refused. This is a fresh reconstruction,
not a byte-exact claim for the lost historical test tree.

## S14 — `candidates/s14`

Recovered from `arrow_update.jsonl`:

- `call_478c5371b9274953905938c1a657d23a`: MySQL admits only an inlined
  conditional in a non-joined definition and an aggregate-argument scalar
  call.
- `call_702` (`call_cba1e5df9e9e450ca737bc52699b51ae`): documents the same
  narrow E2/E3 boundary.
- `call_478c5371b9274953905938c1a657d23a`: compiled replay parametrized for
  MySQL and PostgreSQL.

The existing SQL owner now covers the admitted MySQL E2/E3 cases and the
retained MySQL `JOIN ON` conditional refusal. Candidate-local `PREREG.md` and
`REPORT.md` remain outside the clone tree. Joined `WHERE`, `ON`, `let`, and
unrelated scalar forms were not opened.

## Checks performed now

`py_compile`, Ruff, and `git diff --check` passed in `s10`, `s12`, and `s14`.
Only the explicitly new S12 focused pytest run below was executed; no database,
full Gate 2, network, publication, or historical test result was treated as
current proof.

For S12, the candidate-import record is `logs/s12-candidate-import.log`; the
final guarded focused test record is `logs/s12-focused-pytest-r11.log` with
exit `logs/s12-focused-pytest-r11.exit` (`11 passed, 291 deselected`), and the
final Ruff record is `logs/s12-ruff-r2.log` with exit
`logs/s12-ruff-r2.exit`. They used candidate `src:tests`, CPython 3.13.13,
`UV_PYTHON=3.13.13`, and `UV_OFFLINE=1`.

**Occurrence repair, NEW_RECONSTRUCTION.** The MySQL `lpad` renderer revisits
the text and width expressions. The shared tree/value occurrence walkers now
repeat those leaves in renderer order, so any admitted native placeholder
stream allocates one use per rendered `?`, rather than one use per authored
argument. This is an internal occurrence inventory repair: it does not alter
the compiled wire shape or PostgreSQL output. Current S12 semantics rejects
header parameters inside `lpad` before lowering (`PIE-S2355`), so no compatible
header-parameter native witness exists without separately widening that public
semantic boundary; that widening was not made here.
