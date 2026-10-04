# Development

## Working rules

Use the smallest change that preserves current compiler behavior. Reuse an
existing owner before adding a helper or framework. Keep focused regression
tests for parser/AST, semantic/IR, SQL, diagnostics, CLI/JSON, package behavior,
generated artifacts, and real trust boundaries. Do not preserve historical
repository shape, completed-phase prose, path counts, or self-authored hashes.

Ponytail is an installed runtime layer: use `FULL` for ordinary work, `ULTRA`
for minimization, `ponytail-review` for candidates, and periodic
`ponytail-audit` or `ponytail-debt` only when useful. Pietto overrides its
deletion-first default only for semantic identity/completeness, ordering,
multiplicity, availability, stable diagnostics/output, generated
reproducibility, and genuine content/trust identity.

Escalate user decisions only for product behavior, durable architecture,
public compatibility, or high-risk trust/algorithm assumptions. Exact file
layout, straightforward behavior-equivalent implementation, formatting, and
derived cleanup are implementation freedom.

## Lean Gate v2

**Gate 0 — sync.** Fetch, require clean worktree/index, no active Git
operation, and a synchronized fast-forward `main`; freeze the baseline.

**Gate 1 — decisions.** Record only substantive product, durable architecture,
public compatibility, or high-risk trust/algorithm decisions. Do not make a
decision record for mechanical implementation detail.

**Gate 2 — build.** Implement the minimum solution, run focused checks, review
the complete candidate, group real findings by root cause, consolidate the
repair batch, follow the active dispatch cumulative budget, run proportionate
final validation, and seal the candidate
by its Git tree OID. Stop for unresolved material findings, trust/data-loss or
security regressions, unreproducible candidate content, validation failure, or
out-of-scope behavior.

**Gate 3 — publish.** Rebind the baseline, stage exactly the sealed tree, make
one ordinary fast-forward commit and push, then require natural exact-head CI.
If CI fails, preserve that head and repair in a child commit; never rerun the
failed head as a substitute for a repair.

Git is the publication mechanism. The conceptual states are
`DIRTY_LOCAL_CANDIDATE`, `CLEAN_PRE_PUSH`, and `SHALLOW_PUSHED_HEAD`; no
repository simulator is required. `origin/HEAD` is not publication authority.

## SHA policy v2

For ordinary work, baseline identity is the Git parent, candidate content is
the Git tree OID, and changed paths are derived from Git diff. Do not add
patch, manifest, evidence-file, historical repository, path, count, or
reader-of-reader digests. Keep hashes only when they bind a real cross-boundary
artifact: dependency/lock integrity, pinned GitHub Actions, generated artifact
or vendored-tool reproducibility, trusted opened bytes, or package/dependency
product identity. Product `sha256` semantics are unchanged.

## Validation tiers

Use the layered policy in
[Workflow Lifecycle Reader And Validation Efficiency v1](spec/workflow-lifecycle-reader-validation-efficiency-v1.md):
keep dirty-stage checks focused, run one complete review, then run the
authoritative Python 3.13 validator exactly once. Run generated, golden, and
package-smoke audits locally only when their owned risk surfaces change.
Natural CI remains the final independent Python 3.12 and 3.13 coverage owner.
The current four partitions and completion consumers are specified by
[CI governance](architecture/ci-workload-governance-v1.md); older monolithic
and no-gain records below retain their historical applicability.

Do not propose horizontal CI pytest sharding, extra shards, extra pytest workers,
a different xdist scheduler, or arbitrary heavy-file splitting as a performance
route. The [CI sharding no-gain record](spec/validation-performance-interlude-iv-slice1-ci-horizontal-sharding-and-gate-decomposition-v1.md)
measured that route and rejected it: every independent pytest invocation pays a
shared acquisition floor of roughly 470.64s, which is already above the 55%
adoption ceiling, so sharding multiplies that floor rather than dividing it. That
record also states the measured reopening boundary.


## Phase-end acquisition consolidation

Reuse observations and compatible preparation under explicit input/lifetime
boundaries; rerun independent assertions. Existing owners come first:
`tests/_pietto_repository_facts.py` for process-local immutable source observations,
and the existing differential acquisition owner for compatible run-owned process
cells. Session scope is per worker; it does not establish cross-worker sharing.

1. During a Slice, reuse an existing owner when it fits. Briefly record each new
   exceptional acquisition's actual input, assurance purpose, freshness/isolation,
   resource need and owner. Do not force a broad refactor on every Slice.
2. At Phase start/midpoint reserve consolidation effort in the existing route.
   Before the final audit-only boundary and authoritative seal, inspect new or
   changed tests/helpers relative to the actual Phase baseline, including direct
   existing consumers of changed shared owners.
3. Classify repeated acquisition, fixtures/preparation, copying/serialization and
   resource affinity. Consolidate significant compatible work; preserve fresh
   identity, mutation, process-portability and independent source/wheel witnesses.
   Keep evidence-based low-value exceptions with a reason and owner.
4. Reuse current timings and operation counts. Measure bounded before/after only
   for unanswered questions; integrate the ordinary final validation and evidence
   selection, without another mandatory full profile or database matrix.
5. Review exact equivalence/coverage, changed/add/remove/overlay detection,
   duplicate-work reduction, memory and measured total/critical-path cost. Report
   structural improvement, wall-time improvement and no-gain separately.
6. The Phase handoff summarizes migrated/shared/fresh readers, exceptions and
   remaining debt. A material new duplication burden cannot remain unexamined;
   low-value repetition does not justify a new framework. Formal end-to-end
   dispatches include implementation scope/budget before an audit-only closeout.

This routine review does not require a CI health alert. `ci_workload` and
`ci/workloads.toml` remain the execution-requirement/placement owners; sharing
notes never select tests. Scheduler/topology/resource-policy changes still need
existing evidence and separate authority. [C01](spec/validation-consolidation-c01-v1.md)
bootstraps this procedure without rewriting closed Phase67/S03 history.

## Explicit target conformance

After the Phase66 Slice2 infrastructure publication, applicable acceptance needs
both the existing compiler gates and successful PostgreSQL/MySQL conformance.
Since Slice11 the target denominator is 60 cases and 181 public documents per
target, including the admitted window families, the DISTINCT/ORDER/LIMIT result
boundaries, the six SET forms and their exact non-support boundaries.
Default pytest remains offline; it runs the fixture/observer/config/receipt unit
checks without Docker or database discovery. Real execution is explicit:

```text
UV_PYTHON=3.13 uv run python tests/_pietto_target_conformance.py run --target postgres --pins tests/phase66_target_pins.json --evidence-dir /tmp/pietto-target-postgres-new --run-id local-check --run-attempt 1
UV_PYTHON=3.13 uv run python tests/_pietto_target_conformance.py run --target mysql --pins tests/phase66_target_pins.json --evidence-dir /tmp/pietto-target-mysql-new --run-id local-check --run-attempt 1
```

Use new owned evidence directories outside the repository. The fixed pins,
local Docker endpoint, linux/amd64 platform, finite cases, deadlines and exact
resource cleanup are specified by the [facility contract](spec/phase66-isolated-target-conformance-facility-v1.md).
The same checked-in pins run on a historical or a containerd-backed Docker image
store, because the [image identity compatibility contract](spec/phase66-target-facility-docker-image-identity-compatibility-v1.md)
verifies whichever immutable identity that store actually exposes and binds the
owned container to the exact validated runtime image. No daemon reconfiguration,
image-store switch or repin is needed or permitted.
No arbitrary DSN/image/SQL input, missing-environment skip, automatic retry of a
failed target, host administration or shared-image cleanup is provided.
`verify-receipts` is data-only; CI verifies both same-run receipts, transferred
bytes and successful compiler/target prerequisites through its strict aggregate.
Local compiler, local target, CI compiler and CI target results are separate.
This facility preserves its six Slice2 legacy/control cases and also consumes
the installed Slice3 scan/projection pipeline: production public artifact bytes,
independent data-only decoding, unchanged submission and complete typed BAG
observations. Slice3 added twelve cases and thirteen public artifact variants;
the [Slice4 contract](spec/phase66-slice4-named-shared-producer-scopes-terminal-output-emission-v1.md)
extended its publication manifest to fifteen cases and twenty-six public documents per
target, including six successful named-chain variants and seven structural-only
BLOCKED variants. Compiler failures have independent no-submission evidence.
The decoder checks actual immediate CTE terminals while retaining final physical
source provenance. Environment observations include identifier limits/case; pins,
acquisition limits and workflow commands remain unchanged. R03 joint JOIN/ORDER/SET
execution remains assigned to Slices7/10/11.


The [Slice5 fixed-value/native contract](spec/phase66-slice5-fixed-values-physical-type-anchors-server-parameter-use-mapping-v1.md)
set the A–S19-case/46-public-document denominator:30 VERIFIED,
3 INPUT_REJECTED and13 BLOCKED per target. Private receipts require v2 native
prepare/execute/session/argument/terminal/close-send evidence and exact harness inputs;
historical v1 is not new transport proof. MySQL query submissions use pinned low-level
native methods, including zero parameters. Fixed BEGIN/rollback and identified manager
operations retain their ordinary purpose. A native failure never falls back to a cursor.
Part A focused prerequisite and final whole-candidate target manifests are separate.


The [Slice6 row stage contract](spec/phase66-slice6-row-scalar-let-where-on-context-emission-v1.md)
emits one generated SELECT per actual original stage block: ordered LET bodies, a
TRUE-only filter body and the final projection, with explicit pass-through columns and
`p{index}` / `s{n}` / `t{n}` / `c{i}` naming. Admitted row values are field and LET
references, existing literals and parameters, unary signs, signed-Int `+` `-` `*`,
approved same-logical-type comparisons, `is null`/`is not null` and Boolean `and`/`or`.
Scalar Bool stays three-valued and only a predicate root consumes TRUE. A finite
emission-local interval is checked at every node against the actually selected physical
type, so an overflowing intermediate is rejected even when the final result fits. The
old single-projection shapes keep byte-identical SQL. The current exact denominator is
T–V22 cases and61 public documents per target:39 VERIFIED,3 INPUT_REJECTED,19 BLOCKED.
`L_emission_blocked/where_later` and `O_named_later/producer_filter` migrate from the
not-yet-implemented WHERE blocker to independently checked successful queries, and
`T_row_direct/truth_table` witnesses all nine ordered three-valued AND/OR pairs on both
fixed targets. A focused run of one or more cases uses repeated `--case` arguments and
its receipt records `full_manifest: false`; only a complete manifest is acceptance
evidence.


The [Slice7 value-bridge/JOIN/EXISTS contract](spec/phase66-slice7-value-bridge-join-exists-outer-nulling-terminal-output-emission-v1.md)
emits one generated SELECT per JOIN occurrence with capture-free `m{n}` input aliases,
the ordered effective ON of retained relationship equalities then the authored
predicate, and EXISTS/NOT EXISTS around the complete right terminal. A published port
keeps its carrier's storage and value domain and only gains the possibility of NULL;
only a matched-pairs INNER narrows a nullable carrier, and only for a direct comparison
operand of a top-level AND conjunct. PostgreSQL admits all seven kinds inside their
approved domains including restricted FULL; MySQL FULL stays a typed non-support with
no usable SQL while its neighbouring kinds still emit. The current exact denominator is
W–V25 cases and69 public documents per target, and it splits by target for the first
time: postgres49 VERIFIED,3 INPUT_REJECTED,17 BLOCKED; mysql48 VERIFIED,3
INPUT_REJECTED,18 BLOCKED. `O_named_later/self_join` and `V_row_blocked/match_join`
migrate from the not-yet-implemented JOIN blocker to independently checked successful
queries. R03 repeated/shared JOIN joint execution is delivered here; ORDER and SET
joint execution remain with Slices10/11, and the amended R11/C09 membership differences
remain with Slices8/9/10/11. Grouping, windows, DISTINCT, ORDER/LIMIT and SET remain
BLOCKED for their own Slices.


The [Slice8 grouped/global aggregate contract](spec/phase66-slice8-grouped-global-satisfying-aggregate-emission-v1.md)
adds native GROUPED/GLOBAL aggregation, its satisfying stage and the aggregate result
representations. `GROUP BY` binds the actual input expression rather than an output
alias or an ordinal, GLOBAL emits none, and ONLY_FULL_GROUP_BY stays on with no
`ANY_VALUE` or representative-row repair. `count`, `count_distinct`, `min` and `max`
emit their own spellings; `sum`/`avg` keep one exact typed blocker everywhere,
including behind a named producer or a membership right side. The current exact
denominator is V–Z35 cases and107 public documents per target: postgres81 VERIFIED,3
INPUT_REJECTED,23 BLOCKED; mysql79 VERIFIED,3 INPUT_REJECTED,25 BLOCKED. Five fixed
aggregation relations are loaded by the same fixture manager. Only the GROUPED/GLOBAL
branch of the amended R11/C09 ledger closes here; window/QUALIFY, LIMIT and SET
membership remain with Slices9/10/11, and windows, DISTINCT, ORDER/LIMIT and SET
remain BLOCKED for their own Slices.


The [Slice12 complete-artifact contract](spec/phase66-slice12-complete-emission-artifact-dual-denominator-sql-range-queries-v1.md)
adds no emitter, no public format change and no target case. It adds one private
inspection module, `project_sql_emission_inspection`, whose factory binds a runtime
artifact to its prepared request only after the complete verifier passes and then answers
forward (subject or origin to SQL ranges with their source associations) and reverse (byte
position or half-open byte interval to every overlapping range) queries by bounded linear
scans of the retained ranges. The installed emission probe exercises that view inside the
generation child before export, so the required same-child origins include it; the target
denominator stays 60 cases and 181 public documents per target.


The [Slice13 project emit-SQL CLI contract](spec/phase66-slice13-project-emit-sql-cli-explicit-contract-atomic-output-v1.md)
adds the installed public `pietto emit-sql --project ...` command through one private
coordinator, `project_sql_emission_cli`, over the unchanged plan, emission, verification
and serialization owners. The package smoke runs the installed console as a real
subprocess over the README example project (JSON, text with `--output`, one rejection).
The target facility adds the `CLI_console_emission` case: the copied emission probe in
`console` mode runs the installed console entrypoint through `runpy` inside the isolated
installed interpreter for six frozen witnesses, and the receipt identifies each console
document by SHA-256 against the API record of the same input. The target denominator is
61 cases and 187 public documents per target (181 API-generated and 6 console documents).


The [Slice14 private emission observation contract](spec/phase66-slice14-private-emission-observation-process-integration-v1.md)
adds three private modules: `project_sql_emission_portable_schema` (the closed record table,
limits and primitive encoders, data only), `project_sql_emission_pure_boundary` (bounded raw
and parsed-mapping decoding, documented relations and the immutable range-lookup view; it
imports only the schema) and `project_sql_emission_portable` (runtime export from a verified
artifact and independent runtime correspondence). The differential process registry gains
the `phase66` matrix family, whose probe copies `_pietto_phase66_sql_emission_probe.py` and
`_pietto_phase66_sql_emission_differential_probe.py` into relocated and installed cells and
reports the three modules' same-child origins under `phase66_module_import_origins`. Six
requests are added per available interpreter and no cells; the target denominator is
unchanged and no private document enters a receipt.

The [Slice15 conformance contract](spec/phase66-slice15-expanded-target-differential-metamorphic-conformance-v1.md)
adds the target case `M_metamorphic_composition` and `cases.check_relations`, which checks
ten metamorphic law families across the VERIFIED submissions of every full-manifest run
(after the case loop, as a `case_execution` failure) and in strict receipt verification;
the laws read no case oracle and add no receipt bytes. The receipt file ceiling is 33 MiB
(34,603,008 bytes). The target denominator is 62 cases and 190 public documents per target
(184 API-generated and 6 console documents).

The unnumbered [pre-Slice16 corrective closure](spec/phase66-pre-slice16-completion-corrective-closure-v1.md)
adds the case `G_scan_row_domains` (PostgreSQL inheritance, a view and a partitioned root,
created by `cases.row_domain_setup` after every inherited relation) and the variants
`A_window_named/use_local` and `V_join_full/null_keys`; each witness declares only the
fields it reads so every document stays inside the unchanged 33 MiB ceiling. The target
denominator is 63 cases and 195 public documents per target (189 API-generated and 6
console documents). Its partitioned-root witness also executes a wide `lag` default, so each
target's own window value width is checked by the full manifest.


The post-publication residual supplement keeps that denominator and receipt format. Its
`A_window_frame/range` witness retains both original outputs and adds one literal-carrier
window output with an independent all-ones/int8-or-LONGLONG oracle. R-A expression versus
materialized-field rules, R-B independent row images and R-C multiple scoped window owners
are documented in the [current corrective disposition](spec/phase66-pre-slice16-completion-corrective-closure-v1.md#post-publication-residual-supplement).
Changed production or authenticated probe bytes require fresh full target receipts; old
successful receipts remain historical evidence, not proof of the supplement.


## Local runtime OOM protection

The [Interlude V Slice1 guard](spec/validation-performance-interlude-v-slice1-wsl-oom-emergency-guard-v1.md)
adds `--oom-guard {auto,on,off}` to the validator. Local supported Linux/WSL auto mode
supervises each gate in its own process group; CI auto mode and explicit off retain the
old execution path. Startup worker selection, the four-worker ceiling and loadfile are
unchanged. A resource-pressure abort is not a semantic/test failure. It is an incomplete
validation start and must be recorded distinctly as exit 75 / `RESOURCE_PRESSURE_ABORTED`.
There is no automatic retry or dynamic resizing; later recovery requires explicit task
authority. Missing optional PSI/events does not disable available-memory protection.
This safety guard claims no speed gain or guarantee against every OOM. Interlude IV's
NO_GAIN sharding conclusion remains historical; S2's current evidence can inform a
separately dispatched S3 decision without changing CI here.


## Phase66 G8 native window membership evidence

本节保留 G8 当时的交付边界；当前 Phase66 已完成，后续安排见下方 Interlude V three-Slice route。

[Unnumbered G8 evidence closure](spec/phase66-pre-slice16-g8-window-qualify-native-membership-evidence-closure-v1.md)
补齐 R11/C09 的 native window/QUALIFY membership witness；原 Slice16 re-audit HOLD 是
证据缺口，发现时没有证明 product defect。只加强 A_window_qualify 的两个既有 variants：
selected→SEMI、hidden→ANTI，完整 right terminal 决定 membership，最终只输出左列。
独立 BAG 分别为 [0,1] 与 [BIG,BIG]，F9 同时检查分区、disjoint supports 和独立 ranking。
63 cases/195 documents、189 API+6 console、原 status counts 和33 MiB ceiling 全部不变。

G8 is `COMPLETED / PUBLISHED` only upon successful natural exact-head CI and strict raw
receipt verification on its ordinary publication. Phase66 remains `ACTIVE`; Slice16
requires a fresh re-audit from the G8 publication; its prior HOLD remains history.
N66=16，package/CLI=0.1.0。Phase67 NOT STARTED；v4 planning accepted candidate, not activated。
G8 历史交付当时选择先完成 evidence closure；下列调度状态不替代当前 Interlude V route：
Interlude V Slice1 COMPLETED / PUBLISHED，future slices NOT AUTHORIZED / NOT STARTED。
不要自动重启 Slice16 或 Phase67，也不重新贴回旧 HOLD candidate。


## Interlude V three-Slice execution route

S2 交付时 Interlude V `ACTIVE`, total route = 3：S1 OOM guard 已发布；
[S2 current-suite measurement and runtime optimization](spec/validation-performance-interlude-v-slice2-runtime-cost-reduction-v1.md)
把测量与单一 cell-coordination 优化合并交付，`performance_outcome=MEASURED_GAIN`；
S2 `COMPLETED / PUBLISHED` 以 guarded validation、ordinary publication、自然 exact-head
五-job CI 和 fresh raw receipts strict verification 为条件。S3 `NEXT / NOT STARTED`，
将 CI gate decomposition、evidence-dependent sharding、Dependabot grouping、最终 benchmark
和 closure 合为一个另行 dispatch 的 Slice。Phase66 COMPLETED / N66=16；Phase67 NOT STARTED；
accepted v4 retained；package/CLI=0.1.0。

同四个消费者的 pytest 观察为 562.66s → 176.46s，16 cells/98 requests 在本机可用解释器集合下
逐 request 身份、cell 内顺序和原始输出不变。共享 acquisition 生产窗口为 553.711s → 168.707s，
生产 wall 之和为 568.418s → 656.885s；收益来自已有四 workers 重叠生产，未减少观察工作。
无新增 pool、持久结果 cache、阈值或 admission policy。短实验不能替代 full suite/CI 时间。

本次两次自动重建 `.venv` 是保留的执行偏差；用户只前瞻接受已重建的 CPython3.13.13/locked
环境继续同一 S2。before/after 存在 environment/cache instance discontinuity，不是 fully controlled
比较，不能把数值差异全部归因于补丁。当前依赖版本/import locations 已核对，旧环境未保留的
metadata 仍未知。任务外部 launcher 对所有 project-level uv 命令统一设置 `UV_PYTHON=3.13.13`；
廉价 Ruff 使用已核验 `.venv/bin/ruff`。仅 `--locked` 不禁止环境同步，`--no-sync` 也不证明环境正确。
解释器固定应覆盖所有工具；显式 3.12/3.13 probe children、seed/mode 和 fixture-owned 安装保持不变。
详见 S2 spec 对 Phase66 J04/J05/J06 的消费和 S3 cost/coverage handoff。


## Interlude V CI closure

[S3 decomposition and closure](spec/validation-performance-interlude-v-slice3-ci-decomposition-and-closure-v1.md)
关闭三-Slice Interlude；S1/S2/S3 COMPLETED / PUBLISHED 以最终 sealed publication、全部11个
自然 CI jobs、逐版本 coverage reconciliation 与两份 native raw receipts strict verification 为条件。
Phase66 COMPLETED / N66=16；Phase67 NEXT / NOT STARTED，accepted v4 retained，需要新的
rebind/repository freeze 授权；package/CLI0.1.0。不自动进入 Phase67，不追加 S4。

普通本地 `scripts/validate.py --timings --oom-guard on` 仍执行全部六 gates；CI 使用明确标为
partial 的 `scripts/ci_validation.py gates/run/collect/verify`。S3 当时采用两个分区；后续独立的
[CI remaining-tail maintenance](spec/ci-remaining-tail-rebalance-v1.md) 采用每版本三个 invocations：
`matrix/loadfile`、`standalone/load`、`remaining/loadfile`。仅 Phase65/66 六个独立 mode 节点
使用 native load，从单独 job 的启动即参与逐 node 分发，不再按同文件绑定。共享矩阵成员与
loadfile 不变，各分区保留 resource policy、ceiling4 和独立新鲜根，不复制 semantic observations。
检查与 runtime jobs 并行，Python3.12/3.13 完成 jobs 必须同时核对依赖 success 和完整报告，
最后 target aggregate 才接收 complete compiler status。无新的池或持久结果 cache。

`collect` 独立获取未分区 U；每个真实分区记录 full-collection identity、实际选中 IDs 及
setup/call/teardown 终态，跨 job 消费者验证 disjoint union 和全部终态。原有 test skips 仍记录，
job 的 skipped/cancelled/failed/missing 不能由报告 PASS 覆盖。JSON report 每份最多8 MiB，
只含 IDs、状态和小型既有 manifest properties，不含 SQL/semantic graphs；一日保留，current
run/attempt/checkout/runtime 绑定，使用既有 pinned raw artifact transport 和 digest-mismatch:error。
它不是来源权威、数据库 receipt 或跨运行结果缓存。

共同 lock/Ruff 由3.12 checks job 执行一次。Pyright 的 effective imports/stubs 没有被证明等价，
因此 production/test typing 均在两版本保留。generated/golden/package smoke 同样各保留一次；
pytest 中的真实 generated-guard consumer 也要求 runtime jobs 保留 Java21。
CI maintenance 的 Gate2 使用一次 Python3.13 coverage-equivalent rehearsal：全部 static gates、
独立完整 collection、三个新鲜分区串行执行并对账，随后 generated/golden/installed smoke 各一次；
所有重负载使用 guard on。
这消耗一个 full-suite-equivalent start，不能再额外跑 monolithic suite 作为“保险”。

Dependabot 保留两生态的 daily/timezone/open-PR-limit；仅将 Ruff、Pyright、pytest、pytest-cov、
pytest-xdist 的 minor/patch version updates 组成 tooling group，并将 Actions minor/patch 分组。
major 独立，driver/runtime/target pins 不入 tooling group；不忽略安全更新、不自动合并、不升级版本。
分组节省尚未观察，只能报告配置与代表性匹配检查。

S1/S2 的计数和 S2 环境事件保留在独立历史记录。S3 使用新的受限 ledger；每个 project-level uv
命令仍由任务外部 launcher 固定已核验 CPython3.13.13，CI 使用各自明确的 interpreter。
决策教训是区分 waiting/CPU、invocation-local reuse、runtime-dependent gates 和真实 node coverage；
冻结前还必须查全 script inventories 的直接 readers。具体时长分开记录 pytest、gate、job、critical
path 与 summed runner time，不从一次 hosted run 推出版本因果或稳定 p95。

CI runtime 使用 `--durations=30 --durations-min=1`，另从实际 pytest reports 输出有界的慢节点、
文件累计耗时和 worker 摘要；setup/call/teardown 与 child start/finish 分开，时序不取自 parent
收到报告的时间。计时不进入 coverage schema 或 native receipts，也不决定成员。fixture 依赖分组
与耗时平衡是不同问题：同文件封装可能串行化独立测试，完整报告正确不代表调度已最优。


## 当前 CI workload governance 与 Phase67

[CI governance v1](architecture/ci-workload-governance-v1.md) 取代R1的当前placement；旧段落保留历史。
四个当前分区是 shared-acquisition/loadfile、plan-portability/load、emission-portability/load、
general-runtime/loadfile。普通local validator仍不改变selection；pytest.ini只注册marker。
新special节点用ci_workload声明class/family/group/profile，registry负责placement；无placement即拒绝。
新ordinary自动纳入实际U。添加测试时说明扩展的assurance、预计资源影响及正负检查，不要求精确秒数。

coverage v2保存resolved descriptor table/indices与policy身份，独立于health v1；旧coverage v1只属历史。
managed canonical store的真实production与preparation被被动观察，synthetic stores与memo reads不算重复。
health通过required报告与GitHub Job Summary进入正常CI；最终aggregate只读获取current runtime summaries
和bounded main history，artifact字节按ID/size/digest/context验证。只有此job有actions:read，无写权限。
health不足历史可为INSUFFICIENT_EVIDENCE；slow正确结果不失败，不自动调参、改配置、retry或省略测试。

两compiler/package jobs各在独立环境跑真实PyArrow25.0.1 probe，completion要求完整readiness；core安装与CLI
仍无Arrow。开发机统一外部launcher固定既有project解释器，隔离实验明确指定现有解释器，禁止环境重建。
本次Gate2仅一次3.13完整equivalent：static、独立U、四分区串行、全部对账/health、auxiliary和精确输入匹配的
两解释器小probe；不能另加monolithic/full3.12/cold-matrix。本期 [brief](phases/phase-67/brief.md)、
[Slice01](phases/phase-67/slice-01.md) 与 [lessons](references/engineering-lessons.md) 供后续phase消费。

## Phase67 private result product checks

[Slice02](phases/phase-67/slice-02.md) 在普通 Arrow-free tests 中检查 retained contract/producer identity；
两 compiler/package jobs 另在 fresh isolated3.12/3.13 环境安装 locked core dependencies、candidate wheel，
然后按原 hash lock 安装 PyArrow25.0.1（Slice02历史路径；当前S13见下）。原九组 SDK probe 保持；新增 installed product consumer 使用 `-I`，
核验全部实际 Pietto import origins、当前 source input closure、14组测值/负例及 run context。
completion 必须消费独立 product artifact；coverage、health 和 SDK report schema 不变。
新增 src 文件改变 native package input fingerprint，必须取得当前 head 的 fresh native receipts。

协作约定：用户提交 terminal Slice report 后，协调 ChatGPT 在同一回复审查并给出下一份完整 English prompt；
HOLD 则给出 focused continuation 或 consolidated decision sheet。执行代理在当前授权终态停止，
不因这条协调约定自动开始下一 Slice，也不引入 scheduler/automation service。


## Slice03 private result contract 与轻量过程记录

[Slice03](phases/phase-67/slice-03.md) 增加三private owners：stdlib-only pure boundary、checked exporter、独立runtime correspondence。原两compiler/package jobs及completion沿用现有required product report；不得把pure PASS、metadata或canonical bytes当作producer binding authority。比较两runtime的完整documents，排除外部evidence envelope；native inputs随新模块改变，必须消费fresh自然CI receipts。

每个后续Slice在原外部ledger旁记录轻量JSONL步骤及中文成本摘要：meaningful step的start/end/recovered/note，workflow/step/parent、起止/monotonic elapsed、timing basis、purpose、sanitized action、outcome/reason/retry、evidence refs、budget categories。长命令启动前写start，结束后写同step end；ledger仍唯一计数权威，raw logs留外部。报告区分Slice观察窗口、命令时间、HOLD/user wait、CI wall与runner sum，parent/child不重复相加；缺失时间明确unknown。终态附evidence-linked步骤/成本摘要和下一Slice至多三条改进建议，历史缺口不否定正确执行的product gates，不自动增加benchmark、豁免或scope。

## Slice04 scalar result检查

[Slice04](phases/phase-67/slice-04.md) 沿用同一private consumer，默认Arrow保留signed producer width，显式request按完整int_range判断无损；Bool行carrier与logical batch不同，finite Float64按IEEE bits验证signed zero。原23product与9SDK案例独立保留，新案例通过同一report/damage/input-origin链；core仍Arrow-free，codec格式及batch limits保持。native普通文件准备统一预检，不重跑已绿gates改善计时。

## Slice05 Text result检查

[Slice05](phases/phase-67/slice-05.md) 沿用required product consumer：38个命名案例与36个report-damage controls，同步末端exact assertions；原9 SDK组、30product cases和6份canonical文档保留。新增4份Text/mixed文档完整bytes在local及downloaded CI报告跨runtime比较。UTF-8/offset资源和NULL槽由真实PyArrow25.0.1验证；普通pytest保持Arrow-free，fresh native receipts仍绑定当前input closure。

## Slice06 Decimal result checks

[Slice06](phases/phase-67/slice-06.md) 的shared参数域扩展与private结果层属于一个候选、一次author/Ponytail review和一次完整3.13 equivalent。required product报告扩展至47个命名案例/45个damage controls，两个local与natural-CI运行时比较原10份及新增4份canonical完整bytes。context/traps/flags、实际scaled coefficients、retained-buffer先检查与constructor/checker拒绝层均有独立见证；core保持Arrow-free。

## Slice07 private meaning与结果验证

[Slice07](phases/phase-67/slice-07.md) 先以Arrow-free acquisition/preparation/result vertical关闭Q2，再跑Timestamp/UUID矩阵；public/default缺meaning仍拒绝。new scalar owner改变package input closure，因此仍需fresh native CI，旧native manifest未扩为新高precision/temporal查询。required product消费者验证56cases/54damage controls，原14份与新增4份canonical完整bytes跨local/CI双runtime比较；默认UUID与显式binary16具有同一neutral contract。

## Slice08 finite scalar与midpoint验证

[Slice08](phases/phase-67/slice-08.md) 在原required consumer新增8组，精确64product/62damage controls，保留9SDK和原18份完整canonical documents，新增4份mixed/nullable文档。positional snapshots同时记录ordinal、label、type、values与validity；重复label不用dict列oracle。合法empty absent buffer先经full structural validation再跳过零长度值扫描，非空检查不减。actual文档scanner与current lifecycle读者在full前执行；midpoint文档进入final tested tree，费用/raw/native终态保留外部ledger。

## Slice09 bounded finite reader验证

[Slice09](phases/phase-67/slice-09.md) 复用S08 fixtures和单一scalar checker，usage由同一次validated traversal返回；verify_batch原返回None行为保持。required product精确74groups/72damage controls，9SDK组及22份neutral完整documents不变，新增reader模块由实际installed origins/input closure消费。source失败使用真实from_batches iterable；稀有close/StopIteration/控制流异常明确标为test injection。初组就覆盖unknown/short/extra、empty≠EOF、late error及cleanup；actual doc scanners/current reader/typing inventory在full前执行。四分区、自然15jobs及fresh native receipts仍必需，native package-members新增reader路径不豁免33MiB限制。

## Slice10 CPU协议验证

[S10](phases/phase-67/slice-10.md) 将required product扩为84groups/82实质damage controls，保留9SDK和22全文。真实consumer与wrapper计数/注入控制分别标明；native输入closure随interop模块刷新。自然CI观察允许foreground串行预取已上传raw，最终required inventory/context/bytes与三个data-only native strict仍完整执行，提前下载不证明成功。

## Slice11 ingress验证

[S11](phases/phase-67/slice-11.md) 沿用required consumer，严格92product/90damage及9SDK，原22documents四runtime全文一致。独立SDK native fixture与producer rows配对，不经producer mapper重建Arrow输入；接受点、原raw-reader lease、source/delivery终态与layout-specific cost分别观测。S09/S10直接manifest readers、typing/lifecycle及实际doc scanner在full前检查。

## Slice12 private IPC验证

[Slice12](phases/phase-67/slice-12.md) required product为102groups/100实质damage controls，九SDK和22份完整neutral文档保持。S01 boundary-prefix见证仅说明Arrow短流可读；产品framing与caller extent各自拒绝对应损坏。原S11 launcher/guard验证双runtime实际wheel/origins，Git/network由supervisor闭合；local candidate不宣称发布或native执行。

## Slice13 optional Arrow extra 与安装隔离

[Slice13](phases/phase-67/slice-13.md) 通过唯一 `pietto[arrow]` 选择精确
`pyarrow==25.0.1`，默认 locked setup 与既有core `.venv` 保持Arrow-free。
两compiler/package jobs由 `scripts/package_smoke.py --dist-dir ... --extra-env ...`
各构建或消费同一个wheel/sdist，先在全新core环境验证无PyArrow、lazy imports、真实缺依赖
拒绝及原CLI/SQL，再在另一个全新prefix以候选wheel的 `[arrow]` 安装。hash-pinned
requirements仅预置并校验tested dependencies，随后wheel extra完整解析，不使用 `--no-deps`
绕过selector。独立SDK9、product102/100及原22份neutral全文仍走既有required reports。

实测矩阵只覆盖Linux x86-64、CPython3.12/3.13、PyArrow25.0.1；不是环境marker或其他平台
支持承诺。安装日志记录exact wheel SHA、distribution metadata与resolved site-packages
origins；raw/native闭合分别证明CI产物与既有native设施，不宣称数据库执行安装测试。

## Slice14 fixture与captured-native replay

[S14](phases/phase-67/slice-14.md) 在原installed product consumer加入八组，固定110/108，
保留九SDK及22份neutral全文；普通pytest仍offline。新helper仅显式加载闭合test-helper集合，
小child复制该集合并移动TABLE projects，production origins必须来自同一installed wheel。

原aggregate严格验两份完整native receipts后，复用S13 `_install_extra` 安装当前wheel[arrow]
到独立3.13环境，再消费八个原执行观察；不重跑110组或SDK。sidecar≤2MiB且位于pair-only
目录外，raw artifact总数28；其自身失败、上传或identity失败均使aggregate失败。native
receipt schema/fixtures/queries及15-job图不变。自然CI后同一helper在保留的两个final local
extra环境重放当前receipt，比较semantic observations及typed BAG，不比较路径/偶然fetch顺序。
只有该closure后才清理owned环境。外层driver与child都固定已核验解释器，所有失败累计记录。

## Slice15 whole-result laws

[S15](phases/phase-67/slice-15.md) 将当前required product扩至120groups/118damage；
core-only checker保持Arrow-free，两个installedruntime运行真实七类whole-result routes和独立值oracle。
S14 helper加载/复制/input closure同步闭合新helper；原八native-replay cells、sidecar和28raw总数保持。
22neutral全文须比较当前双runtime与verified S14 expected bytes；IPC bytes不作canonical承诺。
先cheapfocused、一次完整review/repair与follow-up，再原guarded full/package/publication/current-replay。
完整support/readiness矩阵和所有预算见唯一S15合同，S16/Phase68不自动开始。

## Slice16 audit与最终回归

[完成审计](phases/phase-67/completion-audit.md)使用原owner/probes，普通新principal仅offline检查
引用、支持和边界，不以18行/PASS文字证明完成。原120/118、SDK9、22neutral全文、八replay cells、
15jobs/28raw保持；新的pytest数只取真实collection。四个clean core/extra cells消费同candidate wheel，
完整全文同时比较当前双runtime及verified S15 expected；历史结果不代替新执行。
最终closure与cleanup顺序见[唯一规则](phases/phase-67/slice-16.md#唯一闭环规则)，S16外部ledger累计所有失败。
Phase68需独立FULL gate，本次不执行该gate；不得新增skip、benchmark或性能interlude。

## Phase68 explicit local premise experiments

[S01](phases/phase-68/slice-01.md) adds an intentionally invoked test-only `scripts/phase68_executor_premise.py` and an offline data-only checker. Experimental dependencies are isolated by `ci/phase68-executor-premise-requirements.txt`; they never enter core or the four clean Phase67 regression cells. Local observed facts are not newly exercised hosted-CI driver support.
Ordinary new tests remain in independent full collection with no workload placement change. The S01 contract retains guarded3.13 final equivalence, two-runtime SDK9/120118/22documents, exact natural CI28raw/native/current replay. The one external ledger counts all failures and starts; complete unsupported and inconclusive environment have different terminals.

## Phase68 S02 historical validation and repair policy

[S02](phases/phase-68/slice-02.md) used its closed dispatch Section 8 as its sole
execution-budget authority: causal corrections/focused starts have approved
24/24 headroom. Historical S01 counts and unconditional local install matrix
remain historical. A consolidated review finding set permits later diagnosed
in-scope repairs within that cumulative authority; no unchanged luck retries.

Select auxiliary local gates by their registered input closure and actual CI
consumer, not merely by absence of production edits. Record NOT_REQUIRED_LOCAL,
CURRENT_CI or REUSED_UNCHANGED with origin; never a fabricated local PASS.
Focused behavior/direct readers, appropriate Ruff/Pyright, one authoritative
Python3.13 full regression and exact-head natural CI remain current. The normal
`scripts/validate.py --timings --oom-guard on --pytest-maxprocesses 4` path runs its six
gates once; selecting it does not additionally run an equivalent partition suite.
Natural CI retains independent collection, four partitions, managed acquisition,
all package/native/replay consumers and existing worker limits unchanged.

S02 explicit experiment entry is the isolated pinned interpreter followed by
`scripts/phase68_recovery_premise.py run --directory <new-owned-root> --ledger
<single-S02-ledger> --tree <actual-tree> --family all`. Ordinary pytest only
uses stdlib temporary storage/processes and data-only checks; no source DB or
optional-driver discovery. Source/store/sink results remain local evidence.

## Phase68 S03 execution and validation record

[S03](phases/phase-68/slice-03.md) uses its single dispatch Section 9 and external
cumulative ledger. P1/P2 qualification and the route predicate enabled its private
PostgreSQL implementation in the same dispatch. Diagnosed in-envelope corrections,
delta checks and the authorized ordinary publication proceed under that authority;
closed S02 budgets and evidence remain unchanged.

Invoke `scripts/phase68_slice3_probe.py all --directory <new-owned-root> --ledger
<single-S03-ledger> --tree <actual-tree>` with the recorded isolated Python and
pinned dependencies, after installing the current ordinary wheel there. The
worker exercises source and installed production origins; the independent data
checker consumes the report. Ordinary pytest neither discovers credentials nor
starts a DB. New execution modules remain private and driver/Arrow imports lazy.

Current focused checks, direct inventories, Ruff/Pyright and the guarded unfiltered
Python3.13 validator are local obligations. New `src` members change wheel/sdist
and native package fingerprints: exact-head natural CI owns both clean core/Arrow
cells, SDK/product complete-document comparisons, fresh native receipts and their
captured replay. Local native experiments are separately required; hosted old
native families do not certify S03. Generated/golden inputs are unchanged except
the explicit script inventories, checked locally and again by CI. No duplicate
local full partition run or untriggered CI-maintenance work is added.

## Validation Consolidation C01 current closure

C01 is separate test/development maintenance after published Phase68 S03; S04
remains unimplemented. Its dispatch Section 10 and single external ledger own
all cumulative budgets. The measured cohort keeps original nodes/assertions and
injection seams. The current unfiltered guarded Python3.13 validator remains
required, followed by natural exact-head CI and its actual consumers. Native
S01–S03 campaigns and production inputs are not changed or rerun here.

## Phase68 S05 output bridge validation

[S05](phases/phase-68/slice-05.md) uses its one external ledger and dispatch Section9.
Its explicit `scripts/phase68_slice5_probe.py campaign` consumes the selected pinned
isolated Python, current ordinary wheel and registered disposable fixtures. General
output correspondence, metadata and lossless carrier checks feed the existing scalar,
batch and Arrow consumers; source/installed PG and test-only MySQL/ADBC claims stay
separate. The finite named query/type manifest preserves original target exclusions.
Shared binder/decoder changes require current dependent native acceptance. Ordinary
pytest remains offline; focused/direct readers, full typing/Ruff, required package
smoke and the complete guarded unfiltered Python3.13 validator remain local gates.
Exact-head natural CI owns both runtimes and its unchanged mandatory package, native
and captured-replay consumers. Acquisition handoff remains S10 review, S19 integration,
S20 audit-only; this adds no scheduler or performance-maintenance authority.


## Phase68 S06 refinement validation

[S06](phases/phase-68/slice-06.md) keeps the original dispatch Section10 ledger and its
explicit four-path PostgreSQL structural-argument amendment. The original HOLD and
native 42883 observations remain immutable. Complete source/installed, three-route,
fresh-process and independent-checker evidence precedes publication; a range fix or
unverified render is not S06 completion. Internal native fields/work consume the
existing request limits, and no page bound is a source extent oracle.

Protect the accepted core before every core-targeted uv/validator invocation with
command-scoped `UV_PYTHON=3.13.13 UV_NO_SYNC=1 UV_LOCKED=1`; retain separate lock
checking and the unfiltered guarded validator. Explicit isolated installs retain
their own scope. Shared admission/verifier/reader changes require current dependent
acceptance; exact-head CI still owns all existing runtime/partition/native/package
consumers. Compatible fixtures and passive observations are reused; source/wheel,
mutation and fresh-process identities are not merged or replaced by a PASS cache.


## Phase68 S07 guarded execution validation

[S07](phases/phase-68/slice-07.md) uses one cumulative ledger across its original dispatch,
multi-hop amendment and explicit budget corrections. Preserve earlier HOLDs and failed raw.
Before the complete three-route/source-installed campaign, freeze current producing inputs
and obtain `GREEN_FOR_CURRENT_INPUTS` from bounded fixture/native/control/reader preflight.
A changed producer or checker meaning invalidates affected readiness; a full campaign or
full validator is not a diagnostic. Reuse unchanged observations only with exact input reasons.

The explicit S07 launcher owns sequential disposable databases and fresh origin workers.
Independent checks include complete main and auxiliary sessions, statements, nested writer
attempts, native terminals and actual-record damage. Driver close returning is followed by
the existing bounded server-session absence observation; timeout remains failure. Ordinary
pytest stays offline. Required focused/Ruff/typing and the unfiltered guarded Python3.13 full
validator remain local; exact-head CI retains all existing runtime/package/native/replay
consumers. Core no-sync protection and the S19/S20 acquisition boundary remain unchanged.


## Phase68 S08 private MySQL acquisition

[S08](phases/phase-68/slice-08.md) requires an explicit scoped
`MySQLDeploymentPremise` before source discovery. Every owned attempt requalifies
actual definitions, complete supported dependencies and the current native context.
The premise supplies definition/security stability only; native lifetime exclusion
is `NOT_DEMONSTRATED` and compliance is `NOT_INDEPENDENTLY_VERIFIED`.

`scripts/phase68_slice8_probe.py` owns serial source/installed workers and disposable
MySQL fixtures. Native records retain prepare/execute/binary EOF, commit/delivery,
control and cleanup separately. Its independent checker must reconcile actual
native context replies as well as copied observations before complete acceptance.
The resumed instance retains full 50/52/54 per-origin acceptance,
authoritative unfiltered Python3.13 validation and natural exact-head CI as closure obligations.
Ordinary pytest opens no database. Core/profile and cumulative-budget restrictions
continue across resumptions; no new execution profile is implied.


## Phase68 S09 private PostgreSQL ADBC acquisition

[S09](phases/phase-68/slice-09.md) adds a separate explicit PG deployment premise
and bounded source/registry qualification before evaluating reads. The retained
raw catalog replies and actual data-session context are checked independently;
operator compliance and native definition lifetime exclusion remain unproved.
`scripts/phase68_slice9_probe.py` uses the existing serial owned-worker/resource
protocol. It captures producing bytes, loaded origins and pinned runtime identity,
requires matching readiness for the complete source/installed campaign, and keeps
native EOF, transaction ACK/UNKNOWN, delivery and cleanup distinct. Checked Arrow
batches are owned independently of the closed source handles. TLS `require` retains
its encryption-only policy and cannot inherit user CA/CRL/client-key defaults.
The full denominator is derived from current S05/S06/S07 PostgreSQL owners;
small preflight, controls and same-version fresh-process refinement retain separate
histories. Core full validation stays unfiltered; natural CI owns its unchanged
auxiliary partitions. S10 must freshly accept the route-specific premise and
qualify native sources; S19 consolidation and S20 audit-only remain unchanged.


## Phase68 S10 compiled inputs and acquisition review

[S10](phases/phase-68/slice-10.md) keeps one cumulative dispatch/amendment ledger.
The complete original pure corpus and no-source corruption checks precede native
expansion. Small actual three-route representatives precede one integrated review
and exact-input readiness; the complete named live/bundle/source/installed matrix
precedes the authoritative unfiltered Python 3.13 validator and natural exact-head CI.
Source building belongs to the external reference or the new live build boundary;
the isolated bundle runtime receives explicit bytes/pins/values/access, never source
graphs or source-rebuilding helpers. Preserve failed attempts and reconsume complete
unchanged raw when only an independent checker changes.

Phase-end acquisition review: reuse S04/S05/S06/S07 cases and literal oracles,
S01 resource/runtime identities, S08 registered process ownership, original
metadata/scalar/native/page consumers, and the existing two isolated prefixes.
Fresh compiled roots, authorization, qualification, native attempts, installed
origins and fault cuts remain fresh. Passive tracing is restricted to actual
native boundaries; expensive semantic validation remains inside the owner timer.
S19 must consolidate observer assembly and repeated pure reference acquisition
without caching live qualification or collapsing occurrence/attempt histories.
S20 stays audit-only. Current code/member/package changes require current
installed and core-only source-free checks; unchanged grammar/golden producers
retain their declared independent CI responsibility.


## Phase68 S11 job store validation

[S11](phases/phase-68/slice-11.md) keeps one cumulative dispatch ledger. Ordinary
tests cover the qualified-profile positive branch on the measured local build and
the explicit refusal on any other runtime (CI's system SQLite included); they never
skip or simulate a durable PASS. Real process kill/reap, fork and contention
histories use disposable owned workspaces only. The bounded native bridge
(`scripts/phase68_slice11_probe.py`) registers in one process and executes from a
fresh source-free process; S10's original consumers recheck values/SQL/sessions and
the S11 checker reads a static backup copy against raw records and literal oracles.
Store code changes the semantic build identity, so current bundles and installed
witnesses are rebuilt on the final code closure; docs-only changes rerun nothing.
