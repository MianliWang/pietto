# Maintenance recovery candidate review

## Scope and method

- Target: `.cache/phase77-recovery/candidates/maintenance` working tree against
  `f8ccd2c44a2d9adf431a496bd9bbae037783176f`.
- Static review only. I ran `git diff --check`, inspected the complete 35-path
  diff and current readers, and compared the Arrow allowlist with `uv.lock`.
  I did not run pytest, an installer, a database/container, or network access.
- The prior `/tmp/pietto-maintenance-2601-338` patch and its `7345ddec...`
  hash are historical checkpoints only. The recovery status records that its
  raw candidate artifacts and native receipts are absent; this review neither
  recreated nor treated them as current PASS evidence.

## Initial finding — resolved by narrow re-review

1. **RESOLVED — documentation had relabeled prior qualification as qualification of
   the new pins.**

   `docs/project-package.md:1184` changes the verified matrix from
   PyArrow 26.0.0 to 26.0.1 without retaining the old evidence boundary.
   `docs/execution.md:105-107` still says that “These extras were verified …
   with the lock's exact artifacts”, while its immediately preceding extra
   table and text now name the maintenance candidate (3.3.8/26.0.1). This
   contradicts the correctly retained pending statement at
   `docs/execution.md:14-16` and the per-route pending declarations at
   `docs/execution.md:68-70`. The header in
   `ci/phase67-arrow-compatibility-requirements.txt:1` also calls the 26.0.1
   selection “Verified”, although static wheel identity is not native runtime
   qualification.

   The repair now retains the published 3.3.5/26.0.0 qualification at
   `docs/project-package.md:1184-1186` and `docs/execution.md:105-107`, labels
   3.3.8/26.0.1 as selected and pending at `docs/execution.md:14-16,68-70`,
   and limits the CI requirements header to selected official-wheel hashes,
   explicitly excluding runtime qualification. This removes the incorrect path
   by which a reader could skip fresh qualification.

## Verified static closure

- The candidate contains exactly 35 modified paths. `git diff --check` found
  no whitespace errors. The only production changes are literal pins in the
  Arrow owner, PostgreSQL driver owner, and ADBC native owner; the public
  refusal paths remain unchanged.
- `pyproject.toml`, the lock's Pietto metadata, runtime owners, CI workload
  reader, premise files, package smoke reader, target-conformance pins, install
  probe/checker, product/consumer/nested readers, and their tests all select
  PyArrow 26.0.1 and Psycopg/Psycopg-binary 3.3.8 where applicable.
- `uv.lock` is now `b2cc96b25b0b9f2225c4529f0123ae869cd804af0578b4f83c931a15aa893064`.
  Its `revision` remains 5 and its top-level metadata is unchanged. Structured
  comparison finds only four changed package records: `pietto`, `pyarrow`,
  `psycopg`, and `psycopg-binary`; there are no added/removed packages and no
  unrelated package or dependency-edge drift.
- The Arrow CPython 3.12 and 3.13 Linux x86-64 allowlist hashes match the
  current lock's `files.pythonhosted.org` metadata exactly:
  `c718bf97...41738f9` for CP312 and `f71221bb...bc156c` for CP313
  (`uv.lock:388,395`; requirements file lines 3-5). This is static source
  metadata evidence only; no wheel was downloaded or executed.
- Negative contracts remain negative: the package/installer tests retain
  missing-Arrow, wrong-version, conflicting-constraint, missing-artifact and
  foreign/shadow-origin refusals. They update the selected good pin, rather
  than converting the former bad case into success. PostgreSQL still maps a
  wrong/shadow driver to `EXECUTION_DRIVER_VERSION` / `PIE-R2002` before a
  connection.
- Historical version facts were not wholesale rewritten: `docs/execution.md`
  preserves published 26.0.0 and its 3.3.5/26.0.0 native-evidence rows; the
  explicitly legacy recovery-case reader still expects 3.3.5/26.0.0. That
  preservation makes finding 1 a documentation-boundary defect, not a reason
  to relabel those old witnesses.

## Narrow re-review verdict

`READY_FOR_FOCUSED_VALIDATION / READY_FOR_NATIVE_INPUT_REVIEW` — the sole
static finding is resolved, the 35-path candidate is clean under
`git diff --check`, and current package metadata is limited to the intended
pins. This is readiness for the next evidence-producing stages, not their
result: no historical hash or absent raw `/tmp` artifact supplies focused or
native PASS evidence.

Not checked: executable focused tests, lock regeneration, wheel build/install,
native PostgreSQL/MySQL qualification, CI, and any network metadata lookup.
