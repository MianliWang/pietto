# Mechanical closure reference

Supporting material for `SKILL.md`. Deterministic helpers live in
`tests/_pietto_reader_closure.py`; every function there is read-only.

## Procedure in one diagram

```text
planned change
    -> isolated projection of the change
    -> full validation run
    -> failing set = candidate readers
    -> repeat until one pass adds nothing        (zero addition, values unchanged)
    -> substitute expected values
    -> repeat until one pass adds nothing        (zero addition, values moved)
    -> build reader graph
    -> condense into strongly connected components
    -> dependency-first expected replacement calculation
    -> reviewed dry-run patch
    -> primary applies
    -> zero-addition and zero-delta verification
    -> repeat under every publication projection
```

## Helper surface

| Function | Purpose |
| --- | --- |
| `discover_edges` | reader edges for path literals, inventory roots, and repository-wide count literals |
| `readers_of` | direct readers of a target set |
| `build_graph`, `graph_from_edges` | deterministic reader graph from adjacency or edges |
| `transitive_readers` | every node that transitively reads a seed |
| `strongly_connected_components` | Tarjan components in deterministic order |
| `condensation_order` | components in dependency-first order |
| `calculate_replacements` | dry-run plan with exact occurrence counts |
| `verify_zero_delta` | independent confirmation that no rule still matches |
| `verify_zero_addition` | readers discovered but not frozen |

There is deliberately no apply function. A tool that rewrote files during
discovery would make the closure unverifiable, because the evidence and the
thing being measured would change together.

## Why discovery must be by execution

A published slice froze its reader inventory at 64 by inspection. Execution
found a 65th during implementation. After four product edits, a full run
reported 238 failing test items across 150 paths, and the closure settled at
173 readers. The frozen allowlist grew from 72 to 182 paths while the product
surface stayed at three added files: roughly 170 of 182 paths were mechanical
closure with no product behavior attached.

The lesson is not "expect drift". It is: run the projection first, take the
failing set as the closure, and only then start editing.

## Why the second discovery pass matters

Some readers do not consume a path — they consume a *value* that appears in
another reader's source, for example an inventory tuple literal quoted inside a
different module's assertion. Those readers cannot fail until the value moves.
A discovery pass that only adds files without substituting the new expected
values will therefore report a false fixed point.

## Why the projection sweep matters

Readers that assert repository state take different branches under different
projections. A count assertion reached only on the clean-topic branch passes
while the working tree is dirty and fails after the commit. Three such readers
were invisible in the dirty projection of the current work and appeared only
under the clean-topic and squashed-main projections.

## Failure signatures and their fix

| Signature | Cause | Fix |
| --- | --- | --- |
| a reader fails only after commit | branch reached only under the clean projection | sweep every projection |
| a reader fails only in integration | merge or shallow projection differs from local | build the merge and shallow fixtures |
| a new reader appears after editing readers | reader-of-reader keyed on a moved value | second discovery pass with values substituted |
| the allowlist and the failing set disagree | closure conflated with the byte-modified set | keep the three sets distinct and recompute |
| a refresh is discarded and repeated | mechanical closure started before the semantic freeze | converge semantics first |
