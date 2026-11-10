# Editor navigation continuation inventory — 2026-11-09

## Scope and method

Read-only inventory of the canonical core worktree, the owner's VS Code
extension worktree, retained recovery records, and the persisted SQL-preview
evidence. No core or extension source was changed. No Python, npm, VS Code,
database, or package command was run.

The approved scope is limited to standard LSP hover, definition and document
symbols backed by an ephemeral core snapshot. It does not include completion,
formatting, model views, a persistent facts artifact, request-time analysis,
or broader reference navigation.

## Current implementation coverage

The canonical core worktree still contains the intended implementation:

- `src/pietto/_editor_facts.py` detaches declarations and only exact semantic
  `from`/type uses. It does not select a same-spelling fallback target.
- `src/pietto/_lsp.py` advertises the three LSP providers, writes a snapshot
  only as part of the preceding diagnostic analysis, invalidates it by epoch,
  and answers requests without calling a parser, project checker, compiler, or
  disk reader. Missing, stale, omitted, conflicting, ambiguous, and unsupported
  facts yield `null` or an empty symbol list.
- `src/pietto/_project/check.py` retains project facts only after the selected
  schema-v2 semantic pass succeeds. Its ordinary project diagnostic API stays
  diagnostics-only.
- `tests/test_cli_lsp.py` covers current snapshot requests, post-change
  invalidation, request-time no-analysis, UTF-16/BOM ranges, single-file and
  project type/`from` definitions, imports/re-exports, target/root/URI
  conflicts, partial-project omissions, response-shape negotiation, and
  top-level source-ordered symbols. `tests/test_project_editor_overlays.py`
  covers the diagnostics-only separation and overlay boundary.

This is consistent with the documented alpha contract in
`docs/spec/lsp-editor-facts-v1.md`: only type and `from` navigation is
available; fields, lets, parameters, and function calls remain unsupported.
The current feature implementation therefore has no identified missing product
code within ED.01--ED.02.

## Candidate identity and evidence status

Recovery records describe a historical local candidate with tree
`a0c66256e30332d9445eed5fd2f005bc6809e633`, 27,619 passed / 41 skipped,
41 goldens, installed wheel/sdist smoke, and a VS Code 1.145.2 host result of
13 passes plus one optional old-Python skip. These are historical tool-record
claims, not fresh verification in this inventory.

The tree object is no longer in canonical Git (`git cat-file` cannot resolve
it), its `/tmp` candidate and raw Gate-2/host logs are gone, and no retained
manifest maps its exact file hashes to the present dirty worktree. The present
core paths therefore **cannot be proven equal** to that historical candidate,
even though their feature shape and scope agree with its retained description.
They require a newly sealed candidate identity before any old test result can
be reused or a new result can be claimed for them.

The retained evidence at
`/home/mianliwang/.local/state/pietto/evidence/pietto-phase71-20261026/claude-takeover-20261027/claude-closeout-017-20261103/editor-sql-preview-20261108/implementation`
is real terminal evidence for the earlier SQL-preview package only: VSIX
0.2.1, host 13 PASS / one optional SKIP, and node 27 PASS. It explicitly omits
hover, definition, and outline, so it neither establishes nor substitutes for
the newer navigation acceptance.

## VS Code extension status

The extension worktree is at published `e61444f90e3f` (version 0.3.0) with
uncommitted test/synchronization changes. Its production activation already
uses the generic `vscode-languageclient` `LanguageClient`; standard provider
capabilities advertised by `pietto lsp` need no private adapter or new
extension production code. The current host test adds an actual client check
for hover, exact cross-module definition, and ordered symbols.

The extension user documentation is still materially stale: `README.md`,
`docs/architecture.md`, and `CHANGELOG.md` say hover/definition/outline are
absent. Those claims must be updated in the extension candidate before it can
describe the approved user-visible feature. No version bump, Marketplace
upload, or extension CI is required or authorized by this inventory.

## Remaining work, in dependency order

1. Freeze the current core and extension inputs with fresh, recorded hashes;
   do not treat historical `a0c662...` as their identity.
2. Review the combined core candidate and run its focused tests, generated and
   golden checks as selected by its actual closure, then one authoritative
   Python-3.13 Gate 2 on the sealed tree. Rebuild and smoke-test the wheel and
   sdist from that same identity.
3. Update the extension's stale public documentation, retain the host test,
   and run the extension's existing Node/host acceptance against the exact
   sealed core wheel. That acceptance must observe hover, a cross-module exact
   definition, and source-ordered symbols; preserve its raw result.
4. Only after those checks may docs/status use a fresh `LOCAL GATE 2 PASSED`
   statement for the re-sealed identity. Natural CI, a commit, a push, and any
   Marketplace action remain separate and unauthorized.

No product-code expansion is recommended: the LSP client already supports the
standard protocol path, and the approved fact contract deliberately excludes
the remaining binding categories.

## Fresh offline VS Code acceptance preparation

Read-only inventory on 2026-11-09 found these reusable prerequisites in the
extension worktree:

- `node_modules` is present (147 MiB), `out/tests/runHost.js` is present, and
  `package-lock.json` is lockfile v3 with SHA-256
  `40136c2be55202fb3b444ff482612cb1b26592dd586a547066d4c7f6980e788d`.
- The real cached editor is
  `.vscode-test/vscode-linux-x64-1.145.2/code`; it is VS Code 1.145.2, so
  setting `VSCODE_EXECUTABLE` avoids the runner's stable-version download.
- The environment currently has WSLg display endpoints (`DISPLAY=:0`,
  `WAYLAND_DISPLAY=wayland-0`); `xvfb-run` and `Xvfb` are absent. The cached
  editor and its isolated profiles remain available.
- Pietto's recovered runtime has CPython 3.13.13 and an offline wheelhouse,
  but its extant 0.1.10 wheel is a maintenance artifact and the `core-dev`
  interpreter imports editable maintenance source. Neither is a substitute
  for an interpreter installed from the freshly sealed editor wheel.

After the root creates an owned, isolated interpreter containing the sealed
core wheel and its dependencies, the source-host command is:

```bash
VSCODE_EXECUTABLE=/home/mianliwang/projects/pietto-vscode-extension-claude/.vscode-test/vscode-linux-x64-1.145.2/code \
PIETTO_TEST_PYTHON=<owned-editor-venv>/bin/python \
PIETTO_TEST_PYTHON_ARGUMENTS='[]' \
npm run test:host
```

Run it from `/home/mianliwang/projects/pietto-vscode-extension-claude` with
the WSLg display environment retained. `test:host` first compiles TypeScript,
uses the cached editor through `VSCODE_EXECUTABLE`, writes fresh isolated
workspace/profile data, and exercises the development extension against that
wheel. It covers the real hover, exact cross-module definition, and
source-ordered symbol providers in addition to the existing diagnostics and
preview scenarios.

For the installed-extension path, after the extension documentation/test
candidate is sealed and its VSIX is built from that same identity:

```bash
VSCODE_EXECUTABLE=/home/mianliwang/projects/pietto-vscode-extension-claude/.vscode-test/vscode-linux-x64-1.145.2/code \
PIETTO_TEST_PYTHON=<owned-editor-venv>/bin/python \
PIETTO_TEST_PYTHON_ARGUMENTS='[]' \
npm run test:vsix
```

`test:vsix` rebuilds TypeScript, installs
`artifacts/pietto-vscode-extension-0.3.0.vsix` into a new isolated extension
profile, and delegates to the same host suite with the installed extension
path asserted. It does not build the VSIX; `npm run package` must happen
first. No `npm ci`, VS Code download, or network operation is needed when the
listed caches remain unchanged.

`PIETTO_TEST_OLD_PYTHON` is optional. No recovered 0.1.9 wheel/interpreter was
found, so the legacy-no-LSP scenario prints its designed `SKIP`; it is not a
prerequisite for the three approved navigation providers. Preserve that skip
explicitly rather than downloading an old package during the fresh acceptance.
