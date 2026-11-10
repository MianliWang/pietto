# Editor navigation extension acceptance

Classification: `FRESH_LOCAL_EXTENSION_ACCEPTANCE_PASS`; this is not core Gate
2, a commit, a push, Marketplace publication, or natural CI.

## Bound inputs

- Core candidate temporary-index tree:
  `a5d300bb1e6a0216ee95b62552466f407cdc40cb`.
- Core wheel:
  `pietto-0.1.10-py3-none-any.whl`, SHA-256
  `9d2b31b0fa72ee40b1f671b5aa50f5eb0fedc83fdc19fe3d20bf2378e2921dd2`.
- The host interpreter is the isolated installed-wheel CPython 3.13.13
  environment. Its `direct_url.json` points to exactly that wheel; see
  `python-origin.txt`.
- Extension base: `e61444f90e3f426557fd805b66e3d75e20b55e5a`. The exact
  candidate diff SHA-256 is
  `6257331fa73ff477405897fb4b229fb298418f70364a34a304b4baebb5688d6a`.
  `extension-candidate.patch` and the matching isolated-clone receipt retain
  the source identity. The diff contains all seven tracked candidate inputs:
  `CHANGELOG.md`, `README.md`, `docs/architecture.md`, and
  `tests/host/common.ts`, `tests/host/index.ts`, `tests/runHost.ts`, and
  `tests/sync_language.py`. It contains no untracked host-test input; the
  isolated clone's `node_modules` entry is an untracked symlink only.
- VS Code: cached 1.145.2 executable, SHA-256
  `d1c6fe7cec1e285f1210cd3c0472099c25bb56e94f0c8ef7384ee3229ed0b518`.

## Passed fresh checks

- Node R2: 27 of 27 extension checks passed against the bound interpreter;
  `node-test.log` and `node-test.exit` record the command and zero exit.
- Development host R4: 13 acceptance scenarios passed and the optional
  legacy-Python scenario explicitly skipped. It observed a `shape User` hover,
  two exact cross-module definition locations, and source-ordered `Audit` /
  `audit_users` symbols. The raw terminal record is
  `../editor-host-r4-20261110T053700Z/host-dev.log`, with zero exit in its
  sibling `host-dev.exit`; the structured scenario result is the original
  extension's `artifacts/host-results.json`, SHA-256
  `2ef64b8d5ad697a1a731eee432dcf0b81cb58fd2a2ebcbcfc6dd1f82856f75e0`.
- The isolated clone was packaged offline as a 0.3.0 VSIX, SHA-256
  `8c293c8690f81c5760d8c58a98729ae30dc4c0a97d2e65db13ef342729256622`.
  Its installed-VSIX host R2 also passed 13 scenarios with the same explicit
  legacy skip. The raw terminal record is this packet's `host-vsix.log` and
  zero `host-vsix.exit`; the structured scenario result is the isolated
  clone's `artifacts/vsix-host-results.json`, SHA-256
  `41cce134d66d2ec903b8dca18be46206b5f207f7cdb86c0c32ed1d3917291c0c`.

The installed host runs only the packaged extension in its isolated profile;
the small development test driver contains no Pietto implementation.

## Preserved non-product runner failures

- `editor-host-20261110T051900Z/node-test.exit=1`: no
  `PIETTO_TEST_PYTHON` was passed, so two environment-dependent checks refused
  before invoking Pietto. Node R2 corrected only that invocation and passed.
- This packet's `host-dev.exit=1` inherited an unavailable `/run/user/1000`
  socket directory. `../editor-host-r3-20261110T053000Z/host-dev.exit=1`
  used an evidence runtime path too long for a Unix socket. Both failed before
  extension activation. R4 uses a short, owned `/tmp/p77editorxdg.*` runtime
  directory and is the accepted development-host attempt.

No network download, dependency installation, Marketplace action, core source
edit, extension version change, commit, or publication occurred.
