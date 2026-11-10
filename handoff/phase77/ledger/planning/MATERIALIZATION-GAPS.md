# Literal materialization gaps

Status: `SOURCE_BASE_MISSING_NO_RECONSTRUCTION`.

All original literal patches are retained in `literal-patches/`. The following
updates are deliberately not applied because their exact pre-image is not in
the selected recovery records. The initial/add-file version remains materialized
where present. No runtime summary or inferred result has been used to bridge a
gap.

| Input | Materialized baseline | Unapplied literal update(s) | Exact missing base |
| --- | --- | --- | --- |
| S09 typed parameters | `s09_typed_parameters/{README,candidate-contract,qualification-matrix,write-set-and-checks,pure_parameter_prep_selfcheck,uuid-lowering-revision}.{md,py}` | `p77_typed_parameters.jsonl:180,194,200` | The patch hunks target intermediate README/contract/check text not present in the line-129 add-file patch. UUID native bytes remains recorded as implementation freedom, but no unproved update was synthesized. |
| S15 division | `s15_division/{s15_pure_judge.py,ATTACH_PARENT_REQUEST.md,ACTUAL_CHECKS.md}` | `p77_division.jsonl:120,126,131,161` | The pure-judge/parent-request hunks require an intermediate source state absent from the line-91 add files. Existing D76.02 zero-division difference is preserved as a referenced law, not recomputed. |
| Stats | `stats_probe/{stats_probe.py,PLAN.md,README.md}` | `editor_latency.jsonl:963,986,1020,1026,1031,1045,1141,1155,1162,1168,1180,1187,1214,1224,1231` | Several later hunk pre-images do not match the line-954/1000/1006 add-file state. The complete literal sequence remains available for a future recovery with the missing intermediate base. |

No gap remains for the nested oracle, S13 ordered-values hook, or Float hook
files; their recovered Python files pass syntax parsing. All materialized Python
files pass AST parsing as recovered, but this is syntax-only and not a probe,
test, database result, or qualification.
