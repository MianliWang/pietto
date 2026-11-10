# Editor combined candidate Gate 2 preparation

Status: `PREPARED_NO_START`.

This is one future authoritative Python 3.13 validation for the frozen editor
combined candidate. It is independent from maintenance Gate 2 and will not
reuse any maintenance validation result. It binds baseline
`f8ccd2c44a2d9adf431a496bd9bbae037783176f` / tree
`460e3e135d1dcb0b926928bc2632a889410f258a`, candidate temporary-index tree
`a5d300bb1e6a0216ee95b62552466f407cdc40cb`, complete binary patch
`a1a867ec37151a58c38db75902c4f14b32bbbaf1967fa85c0cb17293f3aa6799`, and
lock SHA-256 `b2cc96b25b0b9f2225c4529f0123ae869cd804af0578b4f83c931a15aa893064`.

The candidate deliberately retains four untracked editor inputs. The launcher
uses a temporary Git index with `add -A`, records their paths, includes them in
the source-closure digest, and compares the full temporary-index tree and
closure before/after. It never stages the canonical worktree.

It uses the already fresh, independently smoke-tested exact editor artifacts:

- wheel `9d2b31b0fa72ee40b1f671b5aa50f5eb0fedc83fdc19fe3d20bf2378e2921dd2`;
- sdist `3639469b78ba7ca78cb42d590ebd7c608767707e5f4cee98b3537229674bc7bf`;
- package-smoke terminal
  `evidence/editor-package-r1-20261110T044000Z/run/terminal.json`, exit 0.

The preflight also binds that package run's retained-dist SHA-256 receipt to
both artifact digests; a terminal success without those same artifacts is
rejected.

Generated checks are not selected because grammar and generated parser inputs
are unchanged. The project golden check was separately selected and passed in
`editor-focused-r2-20261110T043000Z`; the full validator keeps its six
authoritative gates rather than narrowing its collection.

The prepared command is:

```bash
cd /home/mianliwang/projects/pietto
PIETTO_EDITOR_GATE2_START=YES \
  .cache/phase77-recovery/evidence/editor-gate2-prepared-20261110T053000Z/run-editor-gate2.sh
```

It uses the existing isolated CPython 3.13.13 Arrow-free core runtime and
offline cache; all `uv` environment selection is fixed in the launcher. The
single validator call has `--pytest-workers 1 --pytest-maxprocesses 1` and
`--oom-guard on`, preserving full selection while avoiding prior process-fanout
pressure. The preflight requires a writable ext4 temporary root without
disabled barriers, records CPU/load/memory/cgroup environment facts, and
compares complete source/cache inventories before use. A launcher-owned monitor records only timestamped memory/PSI/cgroup
facts and top PID/PPID/RSS/command names every ten seconds, and its EXIT trap
reaps it before writing a terminal record.

No tests, build, package installation, database operation, commit, push,
release or external CI was run to prepare this packet.
