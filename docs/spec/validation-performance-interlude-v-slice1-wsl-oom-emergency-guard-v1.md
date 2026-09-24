# Validation Performance Interlude V Slice1: Local Runtime OOM Emergency Guard v1

The user has experienced real WSL OOM interruption risk. Startup resource-aware worker
selection already existed; this Slice adds runtime emergency protection, not performance
acceleration, and does not claim that future kernel OOM is impossible.

## Authority and lifecycle

Accepted baseline: `3c6f25dabc43a0df84f6221d3e82d000554b365d`, tree
`5ba6286ba57440b969892c92c86e4e08f26fc266`, sole parent
`84cf4371e3856b1eb3ac1129b252f5a076777610`, natural push/main CI `35962169430`, attempt 1,
success. The accepted dependency updates remain unchanged; psycopg stays at its pinned
3.3.5 boundary. This Slice changes no target-conformance semantics or authenticated input.

Interlude V is ACTIVE. Slice1 is COMPLETED / PUBLISHED only after its ordinary sealed
publication and successful natural exact-head CI. Future Interlude V slices are
NOT AUTHORIZED / NOT STARTED; no total Slice count is approved. Phase66 remains ACTIVE,
Slice16 pending a fresh completion audit, Phase67 NOT STARTED, N66=16, package/CLI 0.1.0.
The next user decision is further Interlude V work or returning to the Phase66 Slice16
audit. Neither starts automatically.

## Retained startup and CI behavior

`scripts/validate.py` retains its exact GATES, startup effective-memory interpretation,
512 MiB per-worker estimate, max(1 GiB, 20% effective total) reserve, CPU/affinity/cgroup
limits, four-worker ceiling, `loadfile` default, serial fallback and explicit worker options.
There is no dynamic worker resizing, automatic worker restart or retry, CI sharding,
acquisition redesign, new dependency, cgroup creation or host configuration change.
The Interlude IV NO_GAIN decision and its reopening boundary remain: fresh evidence of
P_local <= ~375s and largest indivisible semantic sweep <= ~375s, or stronger evidence
that the latency goal is achievable. This Slice does not reopen it or claim a speed gain.

## Runtime policy and modes

`--oom-guard {auto,on,off}` defaults to `auto`.

- `auto` enables supervision on local Linux/WSL with readable effective memory and the
  process-group/non-reaping-wait capabilities. It silently retains the old execution path
  under `GITHUB_ACTIONS` or ordinary `CI` (nonempty values except false/0/no/off).
  Unsupported local setup prints one concise unavailable reason and keeps the old path.
- `on` requires that setup before launching a gate; unavailable setup exits 2. Signal
  supervision requires the main thread and default SIGCHLD handling, so another reaper
  cannot invalidate the owned leader identity silently.
- `off` uses the previous `subprocess.run(..., cwd=REPO_ROOT, check=False)` path.

Effective total/available bytes reuse the existing `/proc/meminfo` and finite cgroup
limit/current interpretation. PSI `/proc/pressure/memory` full avg10 and cgroup v2
`memory.events` oom/oom_kill are optional. Missing or malformed optional values do not
turn off available-memory protection. Page-cache size is not a trigger when effective
available memory/headroom is healthy. Missing event baselines are unknown, not zero.

| Rule | Fixed policy |
|---|---|
| Sampling | 1.0 second |
| Immediate critical | available <= 768 MiB |
| Immediate events | oom or oom_kill increased from this gate's baseline |
| Hard available | available <= max(1.5 GiB, effective_total // 10) |
| Pressure-aware | full avg10 >= 4.0% and available <= max(3 GiB, effective_total // 5) |
| Non-critical persistence | 3 consecutive hard or pressure-aware samples; healthy resets |
| TERM grace | at most 5.0 seconds before KILL of a remaining owned group |

All byte thresholds use integer arithmetic. Classification priority is oom_kill increase,
oom increase, critical available, then sustained hard/pressure-aware availability.
Counters identify cgroup events, not which process a kernel may have killed.
If required memory telemetry disappears during a guarded gate, auto reports this once,
resets the consecutive count and keeps the same child while trying later samples; on
terminates its owned group and exits 2. Neither path invents a resource-pressure observation.

## Owned process lifetime and cancellation

Each guarded gate starts with `Popen(start_new_session=True)`: child PID is its process
group ID, and the supervising validator remains outside that group. No arbitrary PID,
unrelated process, Docker resource or host service is a cleanup target. Normal differential
acquisition descendants inherit this group; this is not a general manager for descendants
that intentionally detach into other sessions.

The supervisor observes leader completion with `waitid(WNOWAIT)` so it does not release
that PID before deciding whether a signal is required. On a trigger it sends SIGTERM to
only the owned group, waits up to five seconds, sends SIGKILL if that group remains, then
waits/reaps its direct leader. Keeping the leader unreaped during grace prevents signaling
a recycled group ID when a leader exits before its grandchild. Lost wait ownership is an
unavailable outcome, never permission to signal a potentially reused numeric PID.

Temporary SIGINT/SIGTERM handlers queue cancellation until the owned child handle exists.
They do not interrupt child creation or cleanup. Cancellation terminates the owned group,
then propagates KeyboardInterrupt or SIGTERM's conventional exit 143; it never proceeds to
a later gate. Handlers are restored after every gate, including failures. A normal gate's
exact exit code wins a normal-exit/pressure race and remains unchanged. Abrupt growth
between samples, unavailable telemetry, kernel behavior and deliberate session escape mean
this protection cannot guarantee OOM is impossible.

## Auditable incomplete outcome

A resource abort returns validator exit **75** and prints one JSON line prefixed
`[validate] resource-pressure `, with private marker
`pietto.validation-resource-pressure.v1`. It contains `gate`, `reason` equal to
`RESOURCE_PRESSURE_ABORTED`, deterministic `trigger`, `elapsed_seconds`,
`effective_total_bytes`, `effective_available_bytes`, `hard_threshold_bytes`,
`critical_threshold_bytes`, `psi_full_avg10` (null if unavailable),
`memory_events_oom_delta`, `memory_events_oom_kill_delta` (null without comparable samples),
`child_pid` and `termination`. It is not a language/public package format.

A resource-pressure abort is not a semantic/test failure. It is an incomplete validation
start and must be recorded distinctly. There is no automatic retry. For this Slice only,
a first authoritative resource abort permits one manually initiated recovery run after
confirmed cleanup and actual memory recovery, using `--pytest-maxprocesses 2`. Both starts
count; a second resource abort is HOLD. A healthy first run needs no recovery run.

## Validation and scope

Deterministic synthetic tests cover exact thresholds, reset, events, missing optional
telemetry, mode selection, unchanged startup policy, ordinary exits, ownership races and
machine-readable classification. Tiny real Linux child/grandchild tests demonstrate
owned-group termination/reaping, SIGINT/SIGTERM cancellation and unrelated fixture sibling
survival; no real OOM or large allocation is induced. Test cleanup uses an ExitStack of held direct-child handles, and the fixture leader
reaps its grandchild; an additional TERM-ignoring child proves real SIGKILL escalation.
No test scans or kills unrelated host processes.

The frozen delta is A2/M7/D0 across nine paths: the existing validator, the new spec and
principal test, development/status/roadmap, the phase11 entrypoint test, the existing static
inventory test and the sole active lifecycle reader. Older worker/scheduler/history readers
keep their existing assertions; only the retained entrypoint tests explicitly exercise the
unchanged CI path. Production Python stays 222 files and test Python becomes 492.

No local PostgreSQL/MySQL conformance, focused target, Docker acquisition or standalone
differential campaign runs in this Slice. Target helpers/probe/pins, pyproject/lockfile,
all src/pietto Python and their enumerated emission/console inputs remain unchanged.
One full candidate author/Ponytail self-review and one focused follow-up precede the
final `UV_PYTHON=3.13 uv run python scripts/validate.py --timings` in local auto mode.
Generated/golden/package local commands are not added without an owned risk. Natural CI
retains both Python jobs and both targets plus aggregate, with its existing four required
compiler/package steps. Publication uses one ordinary sealed commit and normal FF push;
no manual rerun/dispatch/cancel, amend, rebase, force, PR detour, signing, tag or release.
