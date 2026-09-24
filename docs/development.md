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
the complete candidate, group real findings by root cause, make one repair
batch when needed, run proportionate final validation, and seal the candidate
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
Natural CI remains the final independent Python 3.12 and 3.13 full-validation
owner, and keeps its existing monolithic per-interpreter validation step.

Do not propose horizontal CI pytest sharding, extra shards, extra pytest workers,
a different xdist scheduler, or arbitrary heavy-file splitting as a performance
route. The [CI sharding no-gain record](spec/validation-performance-interlude-iv-slice1-ci-horizontal-sharding-and-gate-decomposition-v1.md)
measured that route and rejected it: every independent pytest invocation pays a
shared acquisition floor of roughly 470.64s, which is already above the 55%
adoption ceiling, so sharding multiplies that floor rather than dividing it. That
record also states the measured reopening boundary.


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

当前 Interlude V `ACTIVE`, total route = 3：S1 OOM guard 已发布；
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
