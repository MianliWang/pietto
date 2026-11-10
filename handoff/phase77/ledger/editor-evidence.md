# Phase77 editor / VS Code evidence recovery

Observed read-only on 2026-11-09. This is a recovery inventory, not a
semantic review, Gate 2 result, or new execution record. No test, `uv`, npm,
database, download, or production/extension source change was run or made.

## Current source remains present

Canonical repository observed at `main` / `f8ccd2c44a2d` with these live,
uncommitted editor-related changes:

- modified: `docs/editor-lsp.md`, `src/pietto/_lsp.py`,
  `src/pietto/_project/check.py`, `tests/test_cli_lsp.py`, and
  `tests/test_project_editor_overlays.py`;
- untracked: `src/pietto/_editor_facts.py`, `docs/phases/phase-77/`,
  `docs/release-notes.d/77-e01-editor-navigation.md`,
  `docs/spec/lsp-diagnostics-v1.md`, and `docs/spec/lsp-editor-facts-v1.md`.

The modified tracked subset has the observed numstat below. It establishes
that a current source delta exists; it does **not** establish equality with a
historical sealed candidate tree.

| Path | Added | Deleted |
| --- | ---: | ---: |
| `docs/editor-lsp.md` | 27 | 59 |
| `src/pietto/_lsp.py` | 350 | 13 |
| `src/pietto/_project/check.py` | 167 | 12 |
| `tests/test_cli_lsp.py` | 607 | 9 |
| `tests/test_project_editor_overlays.py` | 12 | 0 |

The extension repository `/home/mianliwang/projects/pietto-vscode-extension-claude`
is at `main` / `e61444f90e3f`, and retains live, uncommitted changes in exactly:

- `tests/sync_language.py` (128 added, 22 deleted);
- `tests/runHost.ts` (4 added, 3 deleted);
- `tests/host/common.ts` (2 added, 2 deleted);
- `tests/host/index.ts` (39 added, 1 deleted).

Those are current mutable working-tree witnesses only. Neither repository was
edited during this recovery.

## Indexed historical tool records

`session-index.json` retains these records and paths:

| Record | Session id | Indexed bytes | Current raw state |
| --- | --- | ---: | --- |
| root VS Code session | `01a1bc21-176a-73f1-9e3d-09ef1bb4dcb1` | 15,558,908 | readable and syntactically complete (7,058 JSON values), but now 15,850,417 bytes: 291,509 bytes larger than the index snapshot |
| `/root/editor_implementation` | `01a1bc59-33ef-70e2-bb73-95907d8be8a1` | 7,211,963 | indexed byte count matches; readable and syntactically complete (2,672 JSON values) |
| `/root/editor_protocol_review` | `01a1bc6d-ae0f-7601-a017-6ef3663ce0fa` | 5,221,228 | indexed byte count matches; readable and syntactically complete (1,151 JSON values) |

The current raw files are:

```text
/home/mianliwang/.codex/sessions/2026/11/08/rollout-2026-11-08T12-07-27-01a1bc21-176a-73f1-9e3d-09ef1bb4dcb1.jsonl
/home/mianliwang/.codex/sessions/2026/11/08/rollout-2026-11-08T13-08-45-01a1bc59-33ef-70e2-bb73-95907d8be8a1.jsonl
/home/mianliwang/.codex/sessions/2026/11/08/rollout-2026-11-08T13-31-07-01a1bc6d-ae0f-7601-a017-6ef3663ce0fa.jsonl
```

Current SHA-256 values, for later read-only correlation:

```text
4d2f2dab81cd177183661ed854ee83f513970a630abb87cc7ba4d262547ec7b0  root VS Code raw
60298c3fa22c94c5cf1bcfd34e2817d417e43ae7a94a17919ea53b17294e7633  editor_implementation raw
4d905f08df136cc02e7efab8ab45b0620bedc738ad6dced3a5002a59573d5454  editor_protocol_review raw
```

The two worker records are therefore retained as complete, re-readable raw
tool history at the indexed byte size. The root record is likewise
re-readable and parses completely. Its larger current size is expected
append-only growth of the same live thread after `session-index.json` was
written; it does not undermine the older records already in that JSONL. The
index exposes no separate agent path containing `terminal`; the root session
has source `vscode`. Treat any “root actual-terminal” evidence as material
inside that root raw session, not as an independently indexed child record.

## Not recovered

The requested evidence exists at its full persisted path (the shorter path
checked first was wrong):

```text
/home/mianliwang/.local/state/pietto/evidence/pietto-phase71-20261026/claude-takeover-20261027/claude-closeout-017-20261103/editor-sql-preview-20261108/implementation
```

It contains `RESULT.md`, candidate/final patches and SHA-256 files, candidate
and final tree identifiers, core binding identifiers, a VSIX digest, and raw
`final-validation/` logs. `RESULT.md` identifies this as the PostgreSQL SQL
preview candidate: extension baseline `7fafa7c4...`, final candidate tree
`eab60eff...`, and candidate VSIX `pietto-vscode-extension-0.2.1.vsix`.
Although the record calls it a candidate for a future `0.3.0` line, the
validated package itself is `0.2.1`.

This is not new hover/definition/document-symbol evidence. The stored patch
explicitly says it provides SQL preview while omitting hover, definition and
outline. Its `host.log` and installed-VSIX log record the earlier SQL-preview
host scenario: 13 `PASS` records and one optional old-Python `SKIP`; the node
test log records 27 pass / 0 fail / 0 skipped. Those are durable historical
terminal artifacts for the SQL-preview candidate only, not a fresh execution
and not evidence for the newer hover host work.

The following claims remain historical assertions not recovered from this
SQL-preview evidence: sealed editor tree `a0c662...`, `27,619 passed / 41
skipped`, golden `41`, and any newer hover-host result. This recovery did not
run them or upgrade their status.

The old temporary Gate 2 / VS Code artifacts are also absent:

```text
/tmp/pietto-editor-gate2-r2-gate2.log
/tmp/p76-evidence-extension-proof
/tmp/pietto-vscode-parser-api-fix-core
/tmp/pietto-vscode-parser-api-fix-release
/tmp/pietto-vscode-parser-api-fix
```

Thus the durable remainder is current mutable source, the three session JSONL
histories, and the persisted SQL-preview candidate evidence above. The listed
`/tmp` artifacts remain absent and cannot be reconstructed from this read-only
inspection.
