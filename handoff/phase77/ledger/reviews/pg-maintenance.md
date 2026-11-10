# M77 PostgreSQL fresh-maintenance input and lifecycle review

## Scope and evidence boundary

Static review only of `native-maintenance/runnable-rebind/{pg-tls,pg-remaining}`,
their historical source archives, the current candidate/runtime manifests, and
the existing no-DB logs. No database, Docker command, network operation,
installer, or test was run. This is M77 maintenance review only; it opens no
P77 numeric work.

## Narrow re-review after the M77 repair

The earlier RECORD, target-entry, cleanup, remaining-input, materializer, and
parent-status repairs are present in the static source. Both fresh bindings now
record integrity summaries for all six selected distributions; both current
`fresh-start.exit` and self-test exit files are `0`; and both self-test logs
report the refreshed fabricated-world pass. `target-run.sh` is source-bound,
receipt-bound, generates a 24-hex nonce, applies `timeout 7200`, and `pg.sh`
now records cleanup before removal. The remaining receipt includes
`in/timestamp-exec/pietto.toml`; the obsolete materializer exits as retired;
and `PG-RECOVERY.md` now states no-DB preparation rather than native success.

The next two entries are the interim narrow-review findings; both are resolved
in the final disposition below and are retained for review history.

1. **A real cleanup receipt will fail the ownership judge.**

   `target-run.sh` creates `LABEL=pietto.phase77.pg-run=<nonce>` and `pg.sh`
   stores that exact Docker label value in `cleanup.json`. Both lifecycle
   judges instead require `cleanup.container.label == nonce`
   (`pg-tls/judge.py:71`, `pg-remaining/judge.py:63`). The fabricated worlds
   use that impossible bare nonce, so the no-DB self-tests cannot expose the
   production mismatch. A native run with correct Docker inspection evidence
   will be rejected.

   Compare the cleanup value to the complete expected label, or consistently
   record only the label value after the equals sign. Update the fabricated
   world and add a negative mutation for the other representation.

2. **The lock is per run root, not one canonical PostgreSQL engine lock.**

   Both `target-run.sh` files set `LOCK=$PIETTO_PG_RUN_ROOT/pg-target.lock`
   and write `target-invocation.json` before acquiring it. PG-TLS and
   remaining have separate persistent roots, so their calls can acquire
   different locks and run concurrently; two callers of one root can also
   replace the invocation record before `pg.sh` reads it. This does not meet
   the canonical-PG-lock lifecycle requested for the campaign.

   Require one shared dispatch-selected PostgreSQL lock, acquire it before
   writing the invocation record, and retain its exact path in the
   receipt/judge. Keep the existing 7200-second database-execution wrapper.

## Final disposition of the narrow re-review

Both narrow-re-review defects are now resolved.

- `target-run.sh` rejects any image other than the fixed PostgreSQL 18.6
  digest, derives one shared
  `runtime/locks/pietto-postgres-maintenance.lock`, and creates
  `target-invocation.json` only inside the successful `flock` command before
  it enters `pg.sh`. Both judges require that exact lock, the 7200-second
  envelope, the nonce-derived container name, and the full ownership label.
- `pg.sh` records both the asserted full label
  `pietto.phase77.pg-run=<nonce>` and the value observed from Docker
  inspection, `<nonce>`. The two judges now require both representations, and
  their fabricated receipts use the same shape as the launcher. The cleanup
  record remains in the raw hash set and the source/receipt closure includes
  `target-run.sh`.

The refreshed fresh bindings agree with the current hashes of their bound
producer, launcher, judge, receipt, relay, client, TLS generator, and (for
remaining) raw-driver source. They include the all-distribution `RECORD`
payload integrity summaries. Both refreshed fresh-start records bind wheel
`f4c96921c4d4ceb057830f2dd21f2e634325dac2bef933532747ae4aab963a73`, and
both refreshed self-tests first report `binding ... status: exact` then their
fabricated-world success (`18/18` TLS cells; 15 remaining negative
mutations). These are static/no-DB closure records only.

One documentation-only residue remains: both `COMMANDS.md` files call the
shared lock `pg-target.lock`, while the executable and judges use
`runtime/locks/pietto-postgres-maintenance.lock`. It does not alter the
executable closure or the judge, but should be corrected before a human
dispatch uses the command notes.

## Final canonical-lock and writer correction

The prior shared-runtime-lock disposition above is superseded. Both actual
`target-run.sh` scripts, both `pg.sh` invocation checks, both judges, and both
fabricated receipts now require the existing engine-wide canonical lock
`/tmp/claude-1000/pietto-docker-campaign-postgres.lock`; no new lock or
symlink remains in the runnable closure. `ROOTSTART.md` now gives the exact
target environment, fixed PostgreSQL 18.6 image digest, canonical lock, fresh
nonce identity, and `timeout 7200` boundary.

The target writer now emits compact JSON without the former escaped trailing
text. `pg-tls/target-writer-selftest.exit` is `0` and its stdout says
`target writer json PASS`; it uses the same lock-held writer shape and
verifies a subsequent `json.load`. The two `target-run.sh` files are bytewise
identical (SHA-256
`56a174068d13d339d27ae3edfc80a16175214c3d6a38f563100d6735f6c32528`), so
this is evidence for the shared writer source; there is no separate remaining
writer-record file. Both fresh-start/self-test records were regenerated
afterward and remain successful. Shell syntax parsing of both target, PG,
fresh-start, self-test, and TLS-generator scripts also passes.

The two `COMMANDS.md` files still use the old descriptive name
`pg-target.lock`; this is a documentation wording discrepancy only. Their
linked `ROOTSTART.md` target command names the actual canonical path.

The currently bound profile is internally consistent: candidate HEAD is
`f8ccd2c44a2d9adf431a496bd9bbae037783176f`, its working-tree patch and both
copied `candidate.patch` files are
`548e72276b20c2bff3bb0613a527ef230fb9095942b562dca32a6150da12e1cc`,
`uv.lock` is
`b2cc96b25b0b9f2225c4529f0123ae869cd804af0578b4f83c931a15aa893064`, and
the candidate wheel is
`f4c96921c4d4ceb057830f2dd21f2e634325dac2bef933532747ae4aab963a73`.
The latter is also recorded by `runtime/reports/candidate-dist.sha256` and the
rebind artifact manifest.

The fresh-binding replacement is a real improvement over the archived literal
prefix model. Both `fresh_binding.py` scripts require CPython 3.13.13, check
candidate base/working patch/lock and wheel digest, require the six selected
distribution versions to share the native site-packages prefix, and compare
Pietto's `direct_url.json`, module path, and `RECORD` path with the newly
produced binding. A scan of the runnable sources (excluding the intentionally
historical diff stored in `candidate.patch`) found no old `/tmp` prefix,
historical patch digest, or old wheel direct URL. `fresh-start.exit` and the
current self-test exit files are zero; their logs show binding check plus a
fabricated-judge pass. Those are no-DB preparation facts only, not native PG
evidence: the TLS `18/18` text is expressly a fabricated world and neither
package has a new `raw/` directory.

## Original findings (historical; resolved by the narrow re-review above)

1. **The wheel binding does not verify the installed bytes named by `RECORD`.**

   `fresh_binding.py:49-56` reads `direct_url.json`, resolves
   `pietto.__file__`, and records a SHA-256 of the `RECORD` file, but never
   verifies the `RECORD` entries against the files in the native environment.
   The binding is then produced from that same environment
   (`fresh_binding.py:57-68`). A change to an installed Pietto module (or to a
   selected native driver) can leave its version, prefix, `direct_url.json`,
   module path, wheel digest, and unchanged `RECORD` file looking correct;
   both the fresh binding and the fabricated judge then accept code that did
   not come from wheel `f4c...a73`.

   Validate the recorded hashes and sizes for the installed files of every
   selected distribution before producing or accepting the binding, and fail
   closed on an unhashed/missing entry that is required by the run. Keep the
   existing exact path/direct-URL checks; they establish provenance but are
   not byte-integrity checks.

2. **There is no executable target command that establishes the PG lock, two-hour ceiling, or fresh container nonce.**

   `ROOTSTART.md` deliberately contains only the no-DB fresh-start command.
   `COMMANDS.md:7-9` and `RUNBOOK.md:8-10` delegate the real invocation to a
   future dispatch, while both `pg.sh` files merely require an arbitrary
   `PIETTO_PG_CONTAINER`, log the unverified text `pg: lock held`, and have no
   `flock`, `timeout 7200`, canonical lock path, nonce/name rule, or ownership
   label. Thus a target caller can run the scripts outside the canonical PG
   lock and two-hour envelope, and the receipt/judge cannot distinguish that
   from the intended lifecycle. `--pull=never` and `--network none` are in the
   scripts, and the observed image/network are checked, but the required
   parent lifecycle is not closed.

   Add one target-only, preregistered invocation entry which supplies the same
   fresh binding values, creates and records one nonce-derived owned container
   name/label, holds the canonical PostgreSQL lock, and wraps the complete
   run in `timeout 7200`. Make the receipt and judge require the recorded
   invocation/ownership fields. Keep `ROOTSTART.md` no-DB only.

3. **Cleanup is not proved and failure paths destroy the server evidence before it is captured.**

   In both launchers the EXIT trap only sends `kill "$RELAY"` and immediately
   removes the container (`pg.sh:40-45` / `39-44`); it neither waits for the
   child nor captures `docker logs` first. A failed readiness, setup, marker,
   or client step therefore removes the sole server log before
   `pg-server.log` is written on the normal tail path. This violates the
   required raw/server-log-before-cleanup lifecycle and makes root-cause
   adjudication incomplete.

   The normal remaining path also executes `wait "$RELAY" ... || true`, sets
   `RELAY=` and passes literal `1` as `relay_reaped` to `receipt.py`
   (`pg-remaining/pg.sh:116-125`). Its judge then accepts that field as proof
   (`judge.py:97-99`). This is a pseudo-reaped receipt. The TLS package is
   weaker: it has neither container identity/absence nor relay-reaped fields
   in `receipt.py:28-76`, and its judge never requires them.

   Use one cleanup routine for normal and error exits: preserve the first
   failure status; capture server and relay diagnostics before removal; kill
   and `wait` for the actual relay PID; record that wait outcome and the
   inspected owned container ID/name/label; then remove and independently
   inspect absence. Do not disable the EXIT trap until those facts are
   recorded. Have both judges reject missing, false, or mismatched cleanup
   evidence.

4. **The remaining-story receipt omits an actual project input.**

   `pg-remaining/client.py:280-287` calls `compile_query()` on
   `in/timestamp-exec`. Pietto project compilation reads `pietto.toml` as part
   of project configuration, but `judge.py:26-35` and `receipt.py:22-53`
   include `in/timestamp-exec/main.pietto` and `contract.json`, not
   `in/timestamp-exec/pietto.toml`. A changed timestamp-project source
   selection/schema configuration can therefore influence the native attempt
   without changing the accepted `campaign.json` inputs.

   Add that TOML file to the shared receipt/judge input set and its fabricated
   negative mutation. Remove `in/demo-exec/*` from this remaining closure if
   it is not executed; it is currently recorded even though this client uses
   only `ordered-exec` and `timestamp-exec`.

5. **The surviving PG materializer cannot reproduce the reviewed runnable closure.**

   `native-maintenance/materialize_pg_rebind.mjs:10-26` remains an executable
   parent producer. It copies the historical archives and applies only the
   early path substitutions; it does not create the current fresh-binding
   scripts, `ROOTSTART.md`, lock variable, receipt/judge identity changes, or
   cleanup fields. Re-running it now overwrites `pg.sh`, `gen-tls.sh`,
   `COMMANDS.md`, and `RUNBOOK.md` with historical behavior and leaves a
   mixed directory. The final receipt does not bind this producer, so its
   drift is otherwise invisible.

   Either update this sole producer to materialize exactly the reviewed
   closure or retire it and state that the runnable directories are the
   maintained source. Do not retain a runnable generator that recreates old
   literal-prefix semantics.

## Original documentation finding (resolved)

6. **The parent recovery status is stale and contradicts the actual local records.**

   `native-maintenance/PG-RECOVERY.md:24-33` says the fresh packages still
   have old fixed prefix checks and that no launcher has run. The runnable
   sources now use fresh bindings, and both `fresh-start.log` files plus both
   self-test logs exist. This does not make the packages native-ready or turn
   the synthetic results into a PG pass, but it misstates the current
   lifecycle boundary for the next reviewer.

   Update only that parent status to say that fresh no-DB preparation and
   fabricated self-checks occurred, while independent review, a target
   dispatch, raw receipt, compare result, and native qualification remain
   absent.

## Verdict

**Final narrow re-review verdict: the five original M77 must-fix findings,
the canonical engine-lock correction, and the target-writer correction are
resolved in the current static/no-DB closure.** The remaining `COMMANDS.md`
lock-name wording is documentation-only. This verdict authorizes no database
action by itself: target dispatch, raw receipt, independent `compare` result,
native qualification, and CI remain absent.

Not checked: no Docker/PostgreSQL execution, target image availability,
network behavior, or new runtime/CI result. No source code was changed by
this review.

## Native PG-TLS result assessment (read-only)

### Observed result and campaign integrity

The first fresh target campaign is complete but its original comparison is
`16 PASS / 2 FAIL`, exit 1. `raw/campaign.json` binds the current candidate
base, patch, lock and wheel; the fixed PostgreSQL 18.6 image; `network=none`;
the canonical engine lock and nonce-owned container; the fresh binding; every
runner/input digest; every cell record; server/relay/campaign logs; and the
cleanup receipt. All 18 client processes exited zero, and cleanup records the
owned container ID/name/label, captured server log, reaped relay, and absent
container.

Only C1 differs from the historical TLS oracle:

- `postgres_rows` records `AttemptFailed`, `PIE-R2003`, public category
  `AMBIENT_ENVIRONMENT`, `end=FAILED`.
- `postgres_adbc` records `RequestRejected`, `PIE-R2003`, private detail
  `EXECUTION_AMBIENT_CONNECTION_PROFILE`.

Both C1 segments have no relay accept and no `pietto_reader` authentication or
authorization. Thus the run still proves the intended ambient `PGSSLROOTCERT`
refusal before a client connection; its two failures are result-shape
expectation failures, not a TLS transport or cleanup failure. Preserve
`raw/compare.json` and `root-judge.log` as the original failed comparison.

### Independent contract attribution

This is a TLS oracle/judge defect, not a maintenance-candidate regression.

- The published f8 baseline and current
  `tests/test_execution_api_postgres_rows.py:1009-1034` both require an
  ambient PostgreSQL rows variable to produce
  `AttemptFailed(PIE-R2003, EXECUTION_AMBIENT_CONNECTION_PROFILE)` with the
  `FAILED`/`NOT_STARTED`/`CLOSED` terminal. `PGSSLROOTCERT` is one of the
  refused `PG*` inputs.
- The public handle contract says `execute()` returns an unopened handle and
  checks driver/environment when that attempt opens. Rows calls
  `refuse_ambient(("PG",))` in `_connect`, so its refusal necessarily occurs
  during first consumption and is classified by `attempt_failure`; its public
  category is `AMBIENT_ENVIRONMENT`.
- ADBC calls the same refusal from `prepare_postgres_adbc_attempt` before its
  private owner is imported. It is therefore classified at `execute()` as a
  `RequestRejected`; its public detail is the private owner key
  `EXECUTION_AMBIENT_CONNECTION_PROFILE`. Current ADBC tests/checkers require
  that exact key.
- The f8-to-candidate diffs for the rows and ADBC native owners only change
  Psycopg 3.3.5 to 3.3.8 and PyArrow 26.0.0 to 26.0.1. The ambient-refusal
  owner, public error classifier, handle lifecycle, and the cited tests are
  unchanged.
- The recovered historical `ORACLE.md` and copied judge instead require both
  routes to be `RequestRejected` with detail `AMBIENT_ENVIRONMENT`, conflating
  the public diagnostic category with a private detail and erasing the rows
  route's documented attempt boundary. The recovered historical
  `root-judge.log` already records the identical two C1 failures.

### Required evidence handling

Do not edit the registered historical TLS oracle or overwrite the original
failed compare result to fit this run. The smallest correct repair is a new,
versioned child adjudication specification/judge plus its fabricated-world
checks: it must retain the immutable old receipt and all its original input
identities, then accept exactly the two route-specific C1 shapes above while
still requiring no relay/client authorization for each.

On those conditions, a child re-adjudication of this complete immutable raw
campaign is sufficient; a new native PG-TLS run is not needed merely to repair
the observer. Replacing the original `ORACLE.md` or `judge.py` in place would
break the source-bound receipt and would not requalify the already captured
attempt. This assessment does not decide the independently authorized
remaining PostgreSQL campaign and does not convert its evidence into a TLS
result.
