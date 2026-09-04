# Phase 63 Slice 14 Query-Block Project IR Composition, Verification, And Invalidation v1

## Live Authority And Lifecycle

Slice 14 从已发布 commit
`8b56db95ab45933d05db2123b3e89fb81b8ac2fa`、tree
`c07493ab11dcf308a0cde01f9ef33a567096eb3c` 开始。其 parent 是
`0d1d66badc2cf901d35876b360a25a9c36a829b3`，subject 是
`Add Phase 63 completed project semantics`。自然 exact-head CI run
`33855263140` 是 `push / main / attempt 1 / success`；Python 3.12 与
Python 3.13 均为 success。

Gate 0 重新 fetch 并核验：`HEAD == origin/main == live remote main`，divergence
是 `0/0`，worktree、index 与 untracked inventory 均为空，无 active Git
operation。Phase 63 保持 `ACTIVE`；Slices 1–13 是
`COMPLETED / PUBLISHED`；Slice 14 是唯一当前 implementation owner；Slices
15–16 未实现。本 Slice 不开始 Slice 15 或 Phase 64。

Gate 0 前仅删除了根目录 exact untracked regular file `./NUL`。它是 mode
`0644`、size `0`、SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`；它
不是 Slice-14 changed path、repair、closure 或 publication evidence。

## Decision

`ARCHITECTURE_DECISION`：Slice 14 构造一个 private、target-neutral、additive
query-block Project IR overlay：

```text
exact Phase-61 ProjectIRProjectPlan
-> exact Phase-62 binary JOIN snapshot
-> Phase-63 query-block unary IR overlay
```

overlay 消费 exact Slice-13 `ProjectConcreteCompletedSemanticResult` 与 Slice-12
effective-output ledger，不重写历史语义、Phase-61 fragments、Phase-62 JOINs 或
它们的 verification。每个 effective owner 恰有一个 closed result：

1. exact historical IR reuse；
2. historical no-JOIN IR rebound to the exact active upstream output；
3. fresh completed joined/replay query-block IR；
4. typed IR terminal。

构造按既有 dependency-first schedule 执行，结果按 canonical owner order
返回。explicit active-output mapping 是后续依赖的唯一 IR authority；不得按
name、latest、last、maximum coordinate 或 structural equality 选 output。

## Identity, Allocation, And Historical Retention

Slice 14 复用 exact `ProjectIRSnapshotScope`。`starting_allocation` 是 exact
Phase-62 `ending_allocation`；plan-node、output、input-slot 与 use 四个现有域都
继续 dense global positions。没有第二套 coordinate 或新的 relation、final
field、plan-node、output、use、slot identity。

FINAL_PROJECTION 对 completed output 使用 exact Slice-12
`ProjectCompletedOutputField.identity` 作为 `ProjectIRFieldAnchor.identity`。
中间 query-block field 只有 plan-local position，不获得 module-final identity。
历史 rebound 继续使用 existing canonical historical field identities。

`ProjectIRLogicalOperatorKind` 的八个历史值保持不变。只有 private
`ProjectIRQueryBlockOperatorExtensionKind.QUALIFY` 是 additive extension；没有
第二份八值 enum，也不修改 Phase-61/62 inspection、pure 或 canonical output。

## Reuse, Rebind, And JOIN Boundary

`ProjectExistingEffectiveOutput` 仅在 owner、semantic fact、historical fragment、
active upstream output、historical cross edge 与 required/provided row shape 都
保持 exact 时零分配复用。相同 local semantic facts 不等于相同 active IR
dependency root。

历史 no-JOIN local semantics 仍有效但 upstream active output 已替换时，Slice
14 重建其 existing unary fragment、复用 existing resolution/dependency authority，
并让 RELATION_INPUT 的 exact `ProjectIRUseOccurrence` 消费 active upstream。
它不重跑 semantic analysis 或创建另一 relation resolver。无法证明 exact row
compatibility 时返回 typed terminal，且该 owner 分配零 refs。

completed joined tail 只可附着到 exact published
`ProjectIRConcreteJoinRegion`。每个 external JOIN input 必须仍是其 effective
owner 的 exact active IR output；region-local accumulated-left output 不重绑。
stale external input 返回 `EFFECTIVE_JOIN_INPUT_REBIND_UNSUPPORTED` terminal，
不改写或补建 JOIN。generic JOIN over effective outputs 仍属于 Phase 64。

## Query-Block Operators And Evidence

joined tail 不新增 RELATION_INPUT；no-JOIN replay 从一个 consuming active
upstream 的 RELATION_INPUT 开始。两者都只分配实际 authored stages：

```text
RELATION_INPUT? -> ROW_FILTER? -> GROUP_AGGREGATE? -> RESULT_FILTER?
-> WINDOW_EVALUATION? -> QUALIFY? -> FINAL_PROJECTION
-> RELATION_ORDERING? -> LIMIT?
```

LET、named-window declaration 与 JOIN 不产生 unary operator。one semantic
window stage 只产生 one WINDOW_EVALUATION operator；所有 selected 与 hidden
QUALIFY computations 共享 exact pre-window semantic authority。selected window
可以产生 stage-local scalar output；hidden window 不产生 scalar output、field
identity、selected occurrence 或 automatic final field。

query-block operator carrier 保留 exact existing `ProjectIRPlanNodeOccurrence`、
历史 kind 或 additive QUALIFY kind、exact owner anchor，以及 closed typed Slice
8–12/no-JOIN replay evidence。evidence 必须是 retained root member；name、shape、
value equality 或 foreign-but-compatible carrier 不构成 authority。

## Row Shape And Relational Properties

query-block row shape 保留 relation anchor、producer、ordered field positions、
exact `ProjectRowField`、effective nullability，以及适用时的 exact JOIN
introduction/nulling provenance。它不通过 `ProjectRowSchema.fields` flatten joined
rows，因此 duplicate names 与 occurrence multiplicity 保持完整。

Slice 14 不创建第二个 value-class、key、FD、FD-closure 或 grain kernel。新的
relational products 使用现有 `ProjectIROutputFieldOccurrence`、
`ProjectIROutputValueClass`、`ProjectIROutputCandidateKey`、
`ProjectIROutputValueFD`、`ProjectIROutputFDIndex`、STRICT closure、
`ProjectIRProvidedIntrinsicGrain` 与 existing grain dependency carriers。一个
最小 nominal row-output extension seam 让同一 existing algebra 接受 query-block
row outputs；historical behavior 不变。

WHERE、SATISFYING、QUALIFY、ORDER 与 LIMIT 只 image surviving-row BAG、value
classes、keys、FDs 与 intrinsic grain，不加强事实。WINDOW image incoming
properties；每个 selected result 是 fresh singleton class，hidden results append
nothing，且没有新 key/FD。FINAL_PROJECTION 只以 exact Slice-12 source evidence
image direct inputs；computed outputs 是 fresh singleton。determinant 未完整投影的
key/FD 被丢弃，现有 frontier、key-FD 与 FD-index helpers 是唯一计算内核。

GROUPED 在 real new GROUP_AGGREGATE node 使用 existing
`ProjectGroupedGrainFactorIdentity`：owner 是 canonical declaration，operator 是
new node ref，context 保留 exact Slice-9/Slice-12 group authority。incoming active
factors 决定 grouped factor；只有 existing STRICT key/group evidence 才允许 reverse
dependency。group-key classes 构成 grouped key。GLOBAL 没有 active grouped
factor、empty fake key、LIMIT-1 等价或 pre-aggregation JOIN grain。

一个 immutable query-block grain-origin extension 以 exact historical
`ProjectGrainOriginSet` 为 root，按 operator/allocation order 覆盖每个 new
GROUPED/GLOBAL origin 恰好一次。每个新 relational grain product 指向同一个 exact
extension；历史 factors 不迁移。

只有 exact Slice-12 `ProjectRelationOrdering` 建立 relation-result ordering；window
ordering 不泄漏。exact `ProjectRelationLimit` 仅建立 `cardinality <= N`，不建立
key、uniqueness、max-one、GLOBAL 或 grain。所有 output/scalar effects 保持 current
unknown posture；window policy 只适配 exact retained computation authority。

## Independent Verification And Derived Analyses

`project_query_block_ir_verification.py` 不调用 Slice-14 constructor 生成 expected
answers。它以固定 issue order 独立检查：

- Slice-13、Phase-62 VERIFIED result、Slice-12 overlay 与 snapshot scope continuity；
- exact starting/ending allocation 与四域 dense coordinates；
- one canonical entry per owner、exact dependencies/schedule/active mapping；
- historical reuse/rebind 与 external JOIN-input exactness；
- authored operator sequence、QUALIFY placement、absence rules 与 evidence membership；
- output/slot/use endpoints、producer/consumer、anchor、acyclic actual uses；
- occurrence-complete row shapes、nullability/provenance 与 final identity reuse；
- BAG、value classes、keys、FDs、FD index、group/global grain、window output/non-output、
  relation ORDER、LIMIT 与 unknown effects；
- foreign completed/verification/overlay/stage/upstream/final-field/group/window grafts。

`VERIFIED` 要求 issues 为空。只有 VERIFIED output 可以 fresh derive combined
reverse-use index、combined topological order 与 combined reachability。三个分析使用
同一个 generic combined actual-use topology kernel；它们不是 semantic authority，
也不持久缓存。

invalidation 复用 exact `ProjectIRChangeDomain` 与
`ProjectIRVerificationRequirement.RERUN_REQUIRED`。TOPOLOGY invalidates all three
combined topology analyses；相关 semantic/property/effect/context/provenance change
要求 overlay rebuild，但不把纯 topology observation 升级成 semantic authority。
changed Slice-13 completed-semantic root invalidates the complete overlay and all
derived analyses。Slice 14 不实现 incremental cross-snapshot reuse。

## Frozen Core Closure

首次 production mutation 前冻结以下 exact 11-path core closure：

```text
A src/pietto/_project/project_query_block_ir.py
A src/pietto/_project/project_query_block_ir_verification.py
M src/pietto/_project/project_ir_relational_properties.py
M src/pietto/_project/project_ir_evaluation_context.py
M src/pietto/_project/project_grain.py
A docs/spec/phase63-slice14-query-block-project-ir-composition-verification-invalidation-v1.md
A tests/test_phase63_slice14_query_block_project_ir_composition_verification_invalidation.py
M docs/roadmap.md
M docs/status.md
M tests/test_active_phase_lifecycle.py
M tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

expected core accounting 是 `A4/M7/D0`。production Python inventory 是
`175 -> 177`；test inventory 是 `418 -> 419`。任何额外 historical test/static
reader 只能使用 separate mechanical allowance，且不得扩大 production closure。

## Production Repair Ledger

首次 STOP 时 production repairs 是 `8/8`。续授权将总预算扩展为 12；batch 9
完成后继续完成一次最小化 repair，当前 production repairs 是 `10/12`：

1. `project_query_block_ir.py` 的首次 Ruff check 暴露两个 unused imports；删除
   exact imports，只修改该新 production path。
2. 首次 Ruff format check 显示同一新模块未按 repository formatter 排版；只对
   `project_query_block_ir.py` 执行限定格式化，无语义修改。
3. targeted Pyright 暴露 grouped-context mutable attribute override 与 additive
   row-output nullability 无法封闭窄化；在
   `project_ir_evaluation_context.py`、`project_grain.py`、
   `project_ir_relational_properties.py` 和新构造 owner 中改成只读
   `grouped_keys` 与 exact extension branch。
4. 同一 Pyright pass 随后暴露宽 union/类名字符串无法证明 exact carrier；
   `project_query_block_ir.py` 改用真实 retained carrier types 和逐分支 exact
   narrowing，移除字符串类型判断与宽泛 group-key alias。
5. 剩余 Pyright evidence 是跨字段 union 与 optional provenance 相关性；只在已有
   runtime exact type gate 后加局部 cast/optional gate，并保持原接受域。
6. real authored Slice-13 smoke 暴露 projection-only joined tail 的
   FINAL_PROJECTION 直接消费 Phase-62 JOIN row，而 projection image helper 只接受
   先前 Slice-14 row；扩展该 exact input branch，未增加 synthetic operator。
7. verifier 首次静态 gate 暴露 ROW_SHAPE final branch 被补丁上下文置于文件尾而
   形成 syntax failure；只把该 block 移回 `_verify_row_shapes`。
8. verifier integration 暴露 exact root closure 不完整：rebound aggregate context
   未保留、pending upstream terminal 未重绑 final terminal，且 projection helper
   二次构造了 output-field occurrences，使 value classes 未引用 property field
   inventory。`project_query_block_ir.py` 保留 exact contexts/terminal root，并让
   projection classes 与 properties 共享一次 field-occurrence tuple；
   `project_query_block_ir_verification.py` 完成 exact typed narrowing。targeted
   Ruff、Pyright、普通/rebind/stale/downstream-terminal runtime verification 随后
   全部通过。
9. fresh adversarial rereview 暴露
   `IMPLICIT_LAST_RESULT_ACTIVE_IR_ROOT_SELECTION`：completed、pending 与 rebound
   active authority 仍通过 `row_outputs[-1]` / `row_properties[-1]` 选择。
   `project_query_block_ir.py` 现在让 reused、rebound 与 completed concrete ledger
   entry 直接保留 exact `active_output` 和 `active_properties`；builder 在 exact
   final authored operator 构造时捕获 row root，并按 output identity 捕获 property
   root。pending 与 downstream 只消费这些 explicit roots。
   `project_query_block_ir_verification.py` 独立从 exact semantic stage presence
   推导 final operator，验证 root 的唯一 membership、producer、owner、property
   linkage、downstream uses 与 foreign-graft rejection。principal 的 behavior 与
   AST regressions 从 `2 failed` 变为 `2 passed`，完整 principal 是 `12 passed`；
   Slice-14 production 不再含 active-root `[-1]`。
10. batch-9 后的 `ponytail-review` 暴露 `_PendingReuse`、`_PendingRebound`
    与 `_PendingCompleted` 上三个 caller-free `output` compatibility accessor；
    explicit `active_output` 已是唯一 internal consumer seam。只在
    `project_query_block_ir.py` 删除这 12 行 dead flexibility；targeted Ruff、
    Pyright 与完整 principal `12 passed`。

mechanical closure 是 `0/12`；没有新增 historical test/static-reader path。

## Budgets, Validation, And Publication

fresh Slice-14 初始 accounting 是 production repairs `0/8`；续授权把总预算扩展为
`12`，当前是 `10/12`。mechanical closure paths 是 `0/12`，authoritative
validator starts 是 `0/4`。focused compatibility 覆盖 Phase
61/62 IR、Slice 7–13 semantics、lifecycle 与 inventory；所有 changed handwritten
Python 运行 targeted Pyright，另运行 Ruff、format、`git diff --check` 与 fresh
adversarial rereview。authoritative command 是：

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Gate 2 PASS 后只允许 ordinary non-amend commit
`Add Phase 63 query-block Project IR`、one normal fast-forward push，以及 natural
exact-head `push / main / attempt 1` CI。禁止 amend、rebase、force push、manual
rerun、dispatch、tag、Release、signing 或 attestation。

## Explicit Non-goals And Handoff

Slice 14 不修改 public API、CLI、JSON、Project Explain、inspection、pure boundary、
canonical serialization、SQL、Arrow、executor、optimizer、parser/AST、package、
dependency、workflow 或 version behavior。Slice 15 单独拥有 observation/pure/E2E/
differential/metamorphic assurance；Phase 64 单独拥有 generic JOIN semantics。

成功 natural exact-head CI 后，Phase 63 保持 `ACTIVE`；Slices 1–14 是
`COMPLETED / PUBLISHED`；Slice 15 是 `NEXT / NOT IMPLEMENTED`；Slice 16 未实现。
