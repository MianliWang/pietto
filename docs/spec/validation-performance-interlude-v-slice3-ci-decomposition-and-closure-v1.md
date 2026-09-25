# Validation Performance Interlude V Slice3: CI Decomposition and Closure v1

## Decision and authority

S3 完成三-Slice Interlude，不新增 S4，也不启动 Phase67。基线为
`16b90aec4b3601947f69553da1f7da5a290b1a31`，tree
`be14e22fea8602b74e459662f5d197aef2c15576`，sole parent
`e3cbd80e7db9f994f45c03770cc7ed92aae1fdf6`；natural push/main
[36064902345](https://github.com/MianliWang/pietto/actions/runs/36064902345)、attempt1、success 已核对。
Phase66 COMPLETED / N66=16、accepted Phase67 v4 retained、package/CLI0.1.0 保持不变。

选择每个 primary Python runtime 两个 pytest invocations；不增加第三分区，也不共享跨运行的
semantic observations。默认 local validator 不变。S3 的新报告和工作流是 CI execution machinery，
不是 compiler/public API、target receipt 或来源权威。

最终 reader 等量替换已获精确授权；候选仍需完成 review、guarded rehearsal、普通发布和
全部自然 CI 才能关闭。current docs 中的 COMPLETED / PUBLISHED 是此完整链的条件性状态，不代替 live Git/CI。

## Gate ownership

| Command / effective inputs | Version dependence | Owner and sharing decision |
| --- | --- | --- |
| `uv lock --check`; same checkout, pyproject, uv.lock, uv0.11.19, Linux | static project metadata and whole requires-python resolution | `checks_twelve` once; original command and input set retained |
| Ruff format/check; same source/config, native Ruff0.16.8, Linux | unchanged Ruff target/config, not the invoking Python VM | `checks_twelve` once; no new hosted job solely for these sub-second checks |
| production/test Pyright; target3.12 plus stubs/dependency/import environment | environment equivalence not established | both `checks_twelve` and `checks_thirteen` |
| generated, golden, installed smoke | generator/serialization/installed-runtime dependent | both check jobs retain the original three commands |
| pytest, all actual primary-runtime U | both primary runtimes remain required | `runtime_twelve` and `runtime_thirteen`, each matrix/remaining |
| full coverage + successful prerequisite jobs | per-version | genuine `Python 3.12` / `Python 3.13` completion jobs |
| native PostgreSQL/MySQL and raw receipts | target-specific | existing target jobs and unchanged verifier; final aggregate requires both Python completions |

Checks, runtime partitions and targets start independently. Each Python completion depends on its own
checks/runtime jobs, uses `if: always()` and explicitly requires both results to be `success` before
accepting the data reports. The target aggregate derives COMPILER_STATUS from both complete Python
results. Skipped, cancelled, failed, timed-out, missing or empty required work cannot green the final gate.
There are eight job definitions / **eleven realized jobs**: two checks, four runtime partitions, two Python
completions, two targets, one final aggregate. All matrix strategies retain `fail-fast: false`.

Java21 remains in checks and runtime jobs: pytest itself includes a real generated-guard subprocess.
PR and push/main triggers, contents-read permissions, credential isolation, reviewed action SHAs,
uv0.11.19 and the unchanged dependency lock are retained. No manual dispatch/retry/cancellation,
new secret, cross-run artifact fetch, branch-protection change or unconditional echo-success summary.

## Partition and actual coverage

`matrix` contains the ten current Phase58–66 shared-acquisition consumer files, except six exact nodes:
Phase65 Slice14 `test_standalone_forward_reverse_batch_and_atomic_failure` and Phase66 Slice14
`test_standalone_forward_reverse_batches_beside_older_families`, each checkout/relocated/installed.
Their dependencies are preparation resources through `_cell_child`, not `documents`; their standalone,
forward/reverse and failure checks remain intact in `remaining`. Every other ordinary node also goes to
`remaining`. There is no weight database, timing-adaptive membership, randomized hash or scheduler change.

The pre-edit actual collection had16,129 unique IDs:315 matrix /15,814 remaining. Actual fixture closure
identified module-scoped matrix fixtures in seven of the ten files and direct consumers in the others;
there was no outside-file fixture consumer. These are baseline observations, not a permanent denominator.
New ordinary tests remain in the complete remainder. Stale special files or changed mode selectors fail.
Both partitions use the original resource-aware policy, four-worker ceiling and loadfile, without pools
inside workers. The entire supported-interpreter/seed/mode/request/origin assurance remains in each
primary runtime's matrix invocation. Wheel/relocation preparation is fresh; no cross-job results transfer.

Each version's checks job independently runs ordinary full `--collect-only` without the classifier and
records U. Each runtime invocation observes its own full collection before selection and records its
count/digest, actual selected node IDs and actual setup/call/teardown outcomes. xdist worker collections
must agree. The data consumer requires the exact current-run/attempt/checkout/runtime, matching full U,
nonempty partitions, disjoint union, no missing/duplicate/foreign terminal ID, complete phases and genuine
pytest success. Existing test skips stay visible. Report PASS never overrides non-successful job status.

The private JSON reports are bounded at8 MiB each; node names are stored once with indexed phase outcomes.
Only small existing request/cell manifest properties are retained, not raw SQL or semantic graphs.
Names bind run/attempt/runtime/partition, transfers use existing pinned raw upload/download actions,
no overwrite, missing-file error, one-day retention and `digest-mismatch: error`. Upload bytes are checked
against the returned artifact ID/digest; completion consumes exact names from this run, not a broad glob.
Checkout binding uses actual Git HEAD and GITHUB_SHA: a PR's actual merge checkout is not its source-head
SHA, while the publication benchmark must be push/main at the new exact head.

## Dependabot configuration

Both ecosystems retain their daily schedules, America/Toronto timezone and open-PR limit5.
`python-tooling` explicitly matches ruff, pyright, pytest, pytest-cov and pytest-xdist; `routine-actions`
matches Actions. Both use `applies-to: version-updates` and minor/patch update types. Major updates remain
separate. psycopg/psycopg-binary, mysql-connector-python and compiler runtime dependencies are outside the
tooling group. No ignore/security suppression, auto-merge, pin weakening, dependency upgrade or PR mutation.
This is configuration/matching assurance, not observed future savings. The relevant primary behavior is
specified by [GitHub jobs/needs](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-jobs)
and [Dependabot groups](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference#groups).

## Evidence, cost model and bounded validation

S2 evidence is retained selectively under the new S3 evidence root, without moving/deleting its originals.
The preserved S2 targeted result was562.66s →176.46s, production span553.711s →168.707s; summed producer
wall increased. Its environment/cache discontinuity and two unauthorized automatic venv recreations remain
recorded. It proves a useful coordination mechanism, not an isolated causal percentage or stable variance.
S2 full validator833.506s / pytest gate735.404s and full acquisition span about301.960s have different scopes.
S2 CI validators1588.883/1642.488s, runtime gates1486.104/1535.072s, jobs1638/1691s, run1724s and
summed jobs3516s are the observational comparison baseline. Native jobs69/93s and aggregate25s were not
its dominant waiting path. No repeat S2 campaign or cold full baseline is needed.

Before hosted observation, the engineering model is `max(checks, matrix, remaining, targets)`, then the
small required summary/aggregate paths. Matrix work no longer carries both independent standalone families;
those two files can use distinct existing loadfile workers in the remainder. S2's full acquisition and
post-acquisition tail support testing a roughly300–550s local-equivalent runtime critical path, plus setup
and summaries; this is an estimate, not an adopted speedup threshold. Collection and fresh resource
preparation repeat per invocation; ordinary semantic observations do not. Runner sum may increase even when
critical path falls. K parallel jobs are not automatically K*P wall time. A third partition is not retained.

Synthetic tests cover identity/membership omissions, duplicates and foreign IDs, wrong runtime/run/attempt/
checkout, missing shards, incomplete setup/call/teardown and masked skipped/cancelled jobs. A small real
pytest suite additionally checks the actual plugin/xdist path. A depth-one candidate collection/router/
workflow check must precede seal, using copied-checkout source imports rather than the original source.

The authorized Gate2 rehearsal runs all five static gates, then both Python3.13 partitions serially with
fresh roots and the original OOM guard on, independently reconciles full U, then runs generated/golden/
installed smoke once. It consumes one full-suite-equivalent start; the original two-start ceiling includes
any abort/repair reserve. Do not add a monolithic full run. Normal `scripts/validate.py` retains all six
local gates, and partial CI output is explicitly labelled partial. All project-level uv commands inherit
verified CPython3.13.13 from the external local launcher; explicit differential children and CI primary
versions are not overridden. No project venv recreation, cache clearing or interpreter acquisition.

S1 recorded3 diagnostics,9 focused starts,2 correction groups,1 validator/commit/push and no CI child;
its successful validator was1063.628s. S2 recorded6 diagnostics,5 focused,2 cold matrices,2 repair groups,
1 full validator/commit/push and no CI child. Their authoritative validator total is1897.134s before S3.
Categories overlap (S2 cold runs also count as diagnostics/focused); they must not be added as independent
experiments. S3 has a separate cumulative ledger, including failed small starts, and records its final
rehearsal, hosted critical path, summed job time, report transfer and raw target verification. Missing old
stage timings remain unknown. No target starts or Docker acquisitions run locally.

## Scope, review and closure

The only execution addition is `scripts/ci_validation.py`; report regressions live in the existing
`tests/test_phase11_ci_workflow.py`. The spec is the other addition. The approved final set is
19 paths / A2/M17/D0. An exact two-for-two amendment replaces the optional new principal and its pure
file-count reader with `tests/test_phase11_generated_guard.py` and `tests/test_phase11_golden_policy.py`.
Each receives only one ordered inventory insertion of `scripts/ci_validation.py`; exact equality and all
surrounding assertions remain. The original freeze/HOLD and reader-audit omission remain recorded; neither
reader was edited before approval. The removed inventory owner stays byte-identical to baseline.
Historical specs, src/grammar/generated outputs, lock/Python/Pyright configuration, S1/S2 execution owners,
target helpers/probe/pins/input closure, AGENTS and user `.agents/` are read-only. Native receipt v2, full
manifests, raw transport and33 MiB ceiling are unchanged.

One author self-review with installed Ponytail, one bounded repair batch and targeted follow-up own the
integrated candidate; no independent reviewer or extra agent is claimed. Exact final tree, operation ledger,
per-runtime U/selected/terminal counts, all eleven job outcomes, report/raw receipt IDs and digests, and
performance limitations belong to the seal/publication evidence. A genuine in-scope natural failure may
use only the original bounded child permission; a performance target miss cannot trigger a rerun or child.

The lessons that changed decisions are waiting versus computation, invocation-local reuse, runtime-specific
tool inputs, independent actual node coverage, complete inventory-reader closure before freeze, and
command-wide interpreter pinning. S1/S2 and Interlude IV remain historical. A successful S3 closes Interlude V
with measured observations; hosted gain may remain `CI_GAIN_NOT_ESTABLISHED` without weakening correctness.
Phase66 remains COMPLETED/N66=16. Phase67 NEXT / NOT STARTED, accepted v4 retained for separately authorized
rebind/repository freeze. Package/CLI0.1.0. No automatic S4, planning publication or Phase67 Slice1.
