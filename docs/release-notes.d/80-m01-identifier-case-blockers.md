### Refused project statements report their identifier_case premise

Project SQL emission now checks the `identifier_case` statement premise of
a statement that it refuses while it builds the statement's stages. Such a
statement builds no SQL, so its plan says whether it needs named stages (a
`WITH` clause), as the premise table of the project contract lists, for
example for `where`, `group by`, `order by`, `limit`, a window, a JOIN, a
relation `let`, a set operation or a read of another table. When it does, a
missing `identifier_case` adds PIE-B1004
`identifier_case_declaration_missing` and another value adds PIE-B1005
`identifier_case_declaration_mismatch`, after the statement's other
blockers, as a statement whose stages are built already reports them.
Before, such a statement reported the premise only when it read another
table or query; one whose named stages all sit in its own definition, such
as an aggregate or a `where` over one table, reported only its other
refusals, so a contract with a wrong `identifier_case` was still refused
after they were fixed.

On MySQL this includes the conditional, JOIN and two-level `sum(Int)` forms
and the `sum(Int)` cells. One of them with a missing or wrong
`identifier_case` is refused and reports the blockers it has without those
forms (D77.37): PIE-B1004 `sum_int_aggregate_range_proof_missing`, which
said nothing of the premise, now followed by the premise's own blocker,
the one change that makes it verify.

Changed diagnostics (programs refused before; no accepted program changes):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1004, PIE-B1005 | a project statement on either family whose named stages all sit in its own definition, that emission refuses while it builds its stages, and whose contract has no `identifier_case` or another value, such as a MySQL `sum(Int)` form or a grouped `median` of a `Float` | only the other blockers, such as PIE-B1004 `sum_int_aggregate_range_proof_missing`, PIE-B1004 `float_aggregate_finite_result_proof_missing` or PIE-B1003 `quantile_not_admitted_on_target` | the same blockers, then PIE-B1004 `identifier_case_declaration_missing` or PIE-B1005 `identifier_case_declaration_mismatch` |

A refused statement that reads another table or query already reported the
premise and is unchanged. No PIE code or detail name is added. The status
stays `BLOCKED` and the exit code 1; a statement with one stage that reads
no other table or query, such as a plain projection, reports no
`identifier_case`. Emitted SQL, CLI JSON v1, project JSON v2 and the Python
API shapes are unchanged.
