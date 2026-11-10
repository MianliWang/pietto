# M77 R1/R2 resource diagnosis

This is a read-only diagnosis; it changes neither candidate selection nor test
selection, CI workload governance, guard thresholds, or product code.

R1 began with `MemAvailable=35626556 kB`, created eight pytest workers, and
aborted after 844.164 seconds with `effective_available_bytes=2908954624`.
R2 began with `MemAvailable=36714536 kB`, created four pytest workers, and
aborted after 255.024 seconds with `effective_available_bytes=3792248832` and
PSI full `avg10=3.49`. In both terminals, the guard's effective total was
`42058223616` bytes and its hard threshold was 10 percent,
`4205822361` bytes; both had zero cgroup OOM and OOM-kill deltas.

The cgroup `memory.max` is `max`, so the guard uses global available memory;
neither R1 nor R2 records per-process RSS, peak RSS, or a peak descendant
count. Their retained host snapshots cannot prove whether the approximate
33-GB available-memory loss was owned entirely by Gate 2 or shared with other
workloads. The post-run host snapshot is not historical attribution.

The candidate does have real test subprocess fanout. R1 retained eight
`popen-gw*` roots and R2 retained four. At R2 runtime, each worker had an owned
differential probe descendant. The differential process acquisition owner uses
`subprocess.run` for offline wheel build/install and child-interpreter probes.
This supports reducing pytest-worker concurrency; it does not prove the memory
cost of any individual child.

The smallest documented next execution change is `--pytest-workers 1
--pytest-maxprocesses 1 --oom-guard on`. It preserves the full selection and
six validator gates while changing the numeric worker branch to `-n 1`; it
does not bound test-owned child processes or guarantee success. R3's monitor
fills the missing attribution layer without exposing command arguments.
