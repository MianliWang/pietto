# M77 R2 preparation binding

Prepared at `2026-11-10T04:12:27Z`, after confirming no live M77 launcher,
validator, pytest, package-smoke, or differential-probe descendant.

- Candidate: `HEAD=f8ccd2c44a2d9adf431a496bd9bbae037783176f`;
  baseline tree `460e3e135d1dcb0b926928bc2632a889410f258a`; frozen dirty tree
  `2af0e2e47a062eb747ed5d2cd664c2dab5da4aed`; dirty patch SHA-256
  `548e72276b20c2bff3bb0613a527ef230fb9095942b562dca32a6150da12e1cc`;
  35 dirty paths.
- R1 terminal: exit `75`, `RESOURCE_PRESSURE_ABORTED` at pytest 93%; its
  before/after status, patch, index patch, untracked, tree and source closure
  are all identical. R1 is retained untouched.
- Host snapshot: `MemAvailable=36993360 kB`; PSI `full avg10=0.01`; cgroup
  events `oom=0`, `oom_kill=6`. This is an observation, not a future-run
  resource guarantee.

R2 preserves the authoritative six validator gates and retained-dist package
smoke. It changes only the approved execution ceiling: `--pytest-workers 8`
with `--pytest-maxprocesses 4`, plus `--oom-guard on`. The launcher keeps the
same fail-closed candidate/cache/storage/loopback/runtime bindings, creates a
new Gate-owned cache seeded from the verified runtime cache, and records all
raw logs, exits, resource observations, and before/after bindings. It cannot
be started without `PIETTO_M77_GATE2_START=YES`.
