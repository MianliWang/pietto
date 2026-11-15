### Loaded bundles keep the limits of the sites in a statement with a JOIN

`load_bundle` now refuses, on PostgreSQL and on MySQL, a bundle whose records
put an inclusive comparison chain (`1 <= x <= 3`), a conditional, a
membership test, a cast or a scalar call (such as `abs`) at a site where
`compile_query` refuses these forms in a statement with a JOIN, with
PIE-R1004 `COMPILED_OPERATOR`:

- a `let` or `where` of a definition with its own JOIN;
- a JOIN `on`, the test of a `where any(...)` before a JOIN included;
- a `qualify` of any definition of the statement;
- on MySQL, any `let`, `where`, `having` or SELECT item of a definition
  with no JOIN of its own, except in the four paired forms
  ([0.1.12](../release-notes.md#conditionals-beside-a-join-and-calls-in-aggregate-arguments-in-four-mysql-project-forms));
  `0.2.0` refused only a conditional there.

A `same_value` call in a JOIN `on` is still judged by the null-safe JOIN cell
rules, and one outside every cell is still refused with
`COMPILED_PHYSICAL_DOMAIN`. `compile_query` refuses these forms at these
sites, as the [project docs](../project-package.md) say (other JOIN
expression sites "retain their existing limits"), so no bundle it writes
holds one; only bytes made some other way could. `0.2.0` loaded such a
bundle and rendered its SQL, although the [execution docs](../execution.md)
say only queries `compile_query` can produce are loaded. Every check
`load_bundle` makes before this one keeps its code and detail. On MySQL the
check of a scalar call in an aggregate argument reads the records in the
same pass, so a bundle with such a call and such a form in a row of a
definition with no JOIN of its own reports the first of the two in its
record order.

Changed diagnostics (bundles `0.2.0` refused; no accepted program changes):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-R1004 | `load_bundle` of a bundle described above that `0.2.0` refused at a replay check that runs after this one, such as a JOIN `on` with such a form and a `same_value` outside every cell | that check's detail, such as `COMPILED_PHYSICAL_DOMAIN` | `COMPILED_OPERATOR` |
| PIE-R1004 | on MySQL, `load_bundle` of a bundle outside the paired forms that `0.2.0` refused with `COMPILED_AGGREGATE_ARGUMENT` and that also holds a comparison chain, membership test, cast or scalar call in a row of a definition with no JOIN of its own | `COMPILED_AGGREGATE_ARGUMENT` | the detail of the first of the two in the bundle's record order |

New refusals (bundles `0.2.0` loaded, which none of its emissions wrote):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-R1004 | `load_bundle` of a bundle described above | loaded | `COMPILED_OPERATOR` |

No PIE code or detail name is added. What `compile_query`, `export_bundle`
and `emit-sql` produce, its SQL bytes included, is unchanged, and so are CLI
JSON v1, project JSON v2 and the Python API shapes. A forged compiled
`median(id * 2)` still loads; that trust decision stays on the
[roadmap](../roadmap.md).
