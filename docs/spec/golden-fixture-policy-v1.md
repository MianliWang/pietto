# Golden Fixture Policy v1

## Status

This policy is implemented by Phase 11 Slice 4. It governs the reviewed
fixtures under `tests/fixtures/golden/` without changing their contents or the
Pietto language, compiler, SQL output, CLI, JSON schema, or runtime behavior.

The authoritative non-mutating audit command is:

```bash
uv run python scripts/check_goldens.py
```

## Comparison Contracts

SQL golden fixtures are byte-exact contracts. Artifact separators,
indentation, identifier and string quotes, commas, spaces, line endings, and
the final newline are all part of the reviewed output. Tests must compare SQL
as bytes and must not normalize text before comparison.

JSON golden fixtures are structural contracts. Tests decode both actual output
and the reviewed fixture with the Python standard library `json` module before
comparison. JSON object member order and insignificant whitespace are not
semantic contracts.

## Review Policy

Every golden change requires explicit human review of both:

- the Pietto input that produces or motivates the result;
- the complete expected SQL or JSON output.

Golden files must not be refreshed by an automatic bulk command. This
repository intentionally provides no golden update, approval, rewrite, or
snapshot workflow. A fixture change is an ordinary reviewed source change,
and reviewers must understand why every changed output byte or JSON value is
correct.

Dynamic behavior, error paths, output-file safety, filesystem races, and other
stateful behavior are often clearer in focused behavioral tests than in
goldens. A golden fixture should be used only when a stable complete output is
the contract under review.

## Inventory And Ownership

`scripts/check_goldens.py` owns the explicit SQL and JSON classification for
the current fixture inventory. Each classified fixture is paired with at
least one Pietto input and referenced by an owning test:

| Fixture group | Pietto input | Owning test |
| --- | --- | --- |
| `check_types.json` | `examples/basic/types.pietto` | `tests/test_cli_golden_outputs.py` |
| `check_sources_users_warning.json` | `examples/sources/users.pietto` | `tests/test_cli_golden_outputs.py` |
| `emit_sql_active_users.sql` and `.json` | `examples/tables/active_users.pietto` | `tests/test_cli_golden_outputs.py` |
| `emit_sql_active_user_emails.sql` | `examples/queries/active_user_emails.pietto` | `tests/test_cli_golden_outputs.py` |
| PostgreSQL compatibility SQL | matching `tests/fixtures/postgres/*.pietto` | `tests/test_cli_golden_outputs.py` and `tests/test_phase10_mysql_golden_corpus.py` |
| MySQL compatibility SQL | matching `tests/fixtures/mysql/*.pietto` | `tests/test_phase10_mysql_golden_corpus.py` |
| MySQL ordering metadata JSON | `tests/fixtures/mysql/compatibility_ordering_metadata.pietto` | `tests/test_phase10_mysql_cli_enablement.py` |
| Phase 12 PostgreSQL composition SQL | `tests/fixtures/phase12/postgres_order_limit_composition.pietto` | `tests/test_phase12_composition_cli_json_goldens.py` |
| Phase 12 MySQL composition SQL and JSON v1 | `tests/fixtures/phase12/mysql_order_limit_composition.pietto` | `tests/test_phase12_composition_cli_json_goldens.py` |

The audit reports:

- classified fixtures that are missing;
- files in the golden directory that are unclassified or orphaned;
- owning tests that reference missing fixtures;
- missing paired Pietto inputs;
- JSON fixtures that cannot be decoded by `json.loads`.

Inventory and orphan checks exist to expose ownership mistakes. They do not
rewrite, regenerate, normalize, or otherwise modify fixtures, and the audit
does not invoke the compiler.

## Phase Boundary

This policy adds no SQL feature. In particular, it does not add ordering,
limits, joins, grouping, aggregates, windows, CTEs, subqueries, DDL, DML, or
migrations. PostgreSQL remains byte-exact, MySQL generation remains within its
existing MVP, JSON v1 remains unchanged, and `emit_mysql_sql` remains private.

CI and packaging smoke integration remain future Phase 11 slices.
