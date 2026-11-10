# Editor and maintenance combined candidate review

What this change does: candidate `a5d300bb1e6a0216ee95b62552466f407cdc40cb`
combines the recovered M77 dependency update with standard-LSP hover,
definition and document symbols. The editor path creates detached facts only
from the analysis that produces diagnostics and serves requests from the
current in-process epoch snapshot.

Looks good. Ship.

The review traced the changed LSP request dispatch through `_Server._analyse`,
`_set_root_snapshot`, `_editor_request`, exact-use lookup and target
availability; it also traced the project-specific fact projection through
`check_project_editor_diagnostics` and the legacy diagnostics-only caller.
The snapshot is removed before every affected document/root epoch is marked
dirty, root failures and omitted modules do not enter its facts map, ambiguous
ranges return no result, and a definition target must remain inside the same
current snapshot. The type/from facts derive from semantic resolution rather
than spelling lookup. The existing diagnostics-only project caller passes
`editor_facts=False`, so it does not acquire the new projection. The composed
`package_smoke.py` retains both independent hunks, and `git diff --check` is
clean.

Not checked: no focused Python tests, full Gate 2, package build/smoke, or
VS Code host run was executed; the missing historical editor tree and receipts
cannot validate this new candidate.
