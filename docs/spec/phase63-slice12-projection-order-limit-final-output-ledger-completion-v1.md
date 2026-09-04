# Phase 63 Slice 12 Projection, Order, Limit, Final Output, And Ledger Completion v1

## Decision And Live Authority

Slice 12 从已发布 commit
`3f0a5435aa14d7b6ca23348b28c5b966f745c04f`、tree
`be7f7c7dc1f36ed0a7aed1a4561d33eb17fd21ec` 开始。其父 commit 是
`4b984f8c8578bcd7abd42db80fa8ead294d49f8f`，subject 是
`Add Phase 63 QUALIFY semantics`。自然 exact-head push run `33831892060`
的 Python 3.12 与 Python 3.13 jobs 均为 success。

Phase 63 保持 `ACTIVE`。Slices 1–12 是 `COMPLETED / PUBLISHED`；Slice 13
是唯一 `NEXT / NOT IMPLEMENTED` owner；Slices 14–16 未实现。本 Slice 不开始
Slice 13。

## Immutable Slice-7 Completion Overlay

`ProjectEffectiveOutputCompletion` 是精确 `ProjectCompletion` 上的不可变
completion overlay。它保留同一个 base、`ProjectJoinedQualifySet`、owner tuple、
dependency tuple 与 `ProjectCompletion.schedule`，并按既有 dependency-first
schedule 构造。它不重算拓扑，不创建第三张依赖图，也不修改或重建任何 Slice-7
entry。

每个 canonical owner 恰有一个 overlay entry。已完整的历史
`ProjectExistingEffectiveOutput` 与不可恢复的
`ProjectEffectiveOutputTerminal` 在语义未变化时按 object identity 复用。新完成
entry 保留精确 base entry；新 typed terminal 保留精确 base entry、dependency、
causal blocker，以及需要时更早 schedule 中的 upstream overlay entry。

历史 concrete no-JOIN definition 若含 authored QUALIFY，旧输出并不完整，必须
重放而不能复用。`JOINED_TAIL_PENDING` 必须找到唯一 Slice-11 result；concrete
result 才能完成，non-concrete result 形成 terminal。
`UPSTREAM_EFFECTIVE_OUTPUT_PENDING` 只沿精确 single dependency 使用更早的
effective output；upstream terminal 不得产生 placeholder schema。
`EFFECTIVE_UPSTREAM_JOIN_UNSUPPORTED` 与其他不可恢复 terminal 保持原对象，
不会重新进入 JOIN construction。

### Authority Root Integrity

same Slice-7 base 不等于 same Slice-11 authority root。
`ProjectEffectiveOutputCompletion` 保留一个精确 `ProjectJoinedQualifySet`；每个
joined completed entry 的 root，以及每个 joined terminal 保留的 Slice-11 result，
都必须以 object identity 属于该 set 的完整 result tuple。相同 owner、ordinal、
name、type 或等价内容都不能替代该成员关系。

每个 completed field 与 relation ORDER source 必须回闭到其 completed entry 的
精确 root：joined source 只来自该 root 的 Slice-9 stage outputs、Slice-10 window
inputs/results 或精确 scalar namespace；no-JOIN source 只来自该 replay root 的
input/LET、grouped readiness、clause dependency 与 window-output tuple。alternate
Slice-11/replay authority 的等形 evidence 必须拒绝。

joined non-concrete terminal 的 blocker 必须就是 retained set 中的精确 result。
每次实际进入 no-JOIN replay 时创建一个 owner-local
`ProjectNoJoinReplayRoot`。overlay 按既有 schedule 保留完整 replay-root tuple；
concrete replay 与本地 failure terminal 都必须指回该 tuple 中的精确 root，terminal
blocker 必须就是该 root 保留的 blocker。root 同时绑定精确 base entry、历史
semantic fact 与同一 overlay 中的 concrete upstream entry。仅传播 upstream
failure 的 terminal 尚未进入本地 replay，因此不得伪造 replay root。

这些检查只使用 retained root 与完整 tuple membership，不按 owner/name/type
选择等形替代品，也不创建 registry、全局 canonicalizer 或第二张 replay graph。

## Canonical Final Field Identity

最终字段不定义新 identity domain。每个完成字段使用现有
`ProjectModuleRowFieldIdentity`：owner 来自现有 `_declaration_identity`，kind 是
`RELATION_OUTPUT`，`field_position` 等于 selected ordinal，name 等于稳定 output
name。

完成字段同时保留精确历史 `ProjectModuleSelectFact`、同一个 `SelectItem`、ordinal、
name、完成的 `ProjectRowField`、`ProjectRowResultRole` 与 source-stage evidence。
select occurrence 与 final field identity 是相互关联但不同的 authority。

joined owner 的历史 semantic fact 仍是 `AUTHORED_JOIN_DEFERRED`，因此 Slice 12
不会伪造 `ProjectModuleRelationOutputFieldAttribution`。合法 source evidence 的
封闭 union 是：joined scalar/input analysis、Slice-9 GROUP_KEY 或
AGGREGATE_RESULT occurrence、Slice-10 selected window binding，以及 no-JOIN replay
scalar/grouped/window authority。不存在 SQL alias identity。

## Projection And Project Types

稳定命名规则保持：显式 alias；否则 bare `NameExpr` name；否则最后一个
`DottedNameExpr` component；其余无名。无名 computed projection 保留
`PIE-S2304`，duplicate name 保留 `PIE-S2305`。任一失败都会禁止整个完成输出，
不会留下 partial schema。

joined `ABSENT` aggregation 的 selected window 逐 ordinal 复用精确
`ProjectSelectedWindowResultBinding`；其他 select item 在同一个 post-LET joined
scalar authority 上调用现有 expression adapter。select items 相互平行，不能读取
selected window alias、ordinary projection alias 或 hidden QUALIFY result。

`GROUPED` 的每个 non-window item 必须映射同一个 Slice-9
`ProjectJoinedStageOutputOccurrence`，window item 映射 Slice-10 selected result。
`GLOBAL` 的每个 item 映射 Slice-9 aggregate result，selected window 仍不支持。

ValueType 到 Project type 的转换只调用现有 project conversion seam。direct
projection 尽可能保留精确 `ProjectResolvedType`；builtin 通过现有 builtin
authority；nominal type 必须携带精确现有 `ProjectSymbol`，不能按 spelling 解析。
无法建立精确 Project type 时 fail closed。

只有全部 select item concrete、全部有稳定 name 且 name 唯一后，才构造一个
`ProjectRowSchema`。有序 completed-field tuple 是 occurrence/identity authority；
schema mapping 只是 interface projection。

## Result Roles And Row Domain

最终 `ProjectRowField.result_role` 保持现有四类：ordinary scalar/direct 是
`ORDINARY_ROW_VALUE`，selected grouped key 是 `GROUP_KEY`，aggregate 是
`AGGREGATE_RESULT`，selected window 是 `WINDOW_RESULT`。角色不从 name 推断。

`ProjectCompletedRowDomain` 明确区分三种 result posture：

- `ABSENT` 精确保留 joined preservation 的 intrinsic-grain authority；普通下游
  no-JOIN 按 reference 保留 upstream completed row-domain authority。
- `GROUPED` 只保留精确 group-key occurrence tuple 作为 semantic basis；它不声称
  pre-aggregation JOIN grain，也不创建 `ProjectGroupedGrainFactorIdentity`。
- `GLOBAL` 是显式 global posture，没有 authored group-key factor set。

Slice 12 不创建新的 normative grain graph。它也不创建
`ProjectIROutputRelationalProperties`，不推导 key、uniqueness、FD、value/equality
class、nullability strengthening、grain dependency 或 relationship cardinality。

## Relation ORDER

relation ORDER 是第一个 final relation-order authority。window-local ORDER、
QUALIFY evaluation 与 relation ORDER 是不同 stage。没有 authored relation
`order by` 时，即使 window 内有排序，完成输出的 ordering 仍明确 absent。

一个 concrete ordering 保留精确 `OrderByClause`、source-ordered `OrderItem`、
source ordinal、authored expression、type/resolution evidence 与 effective
direction。omitted 和显式 `asc` 都是 `ASC`，`desc` 是 `DESC`。items 不去重、不
重排，order key 不要求出现在 final projection。

`ABSENT` scope 使用精确 input/joined post-LET 与 admitted LET authority；ordinary
projection alias 不可见。bare selected-window alias 仅在普通 lookup 为 ABSENT 且
恰有一个同名 selected result 时 fallback。普通 lookup 为 ambiguous 或
non-concrete 时不得 fallback；非 name scalar expression 也不能隐藏改写 alias。

`GROUPED` ORDER 只接受 bare `NameExpr`，并且只可指向精确 selected GROUP_KEY、
AGGREGATE_RESULT、group-key-backed LET 或 selected window result。raw input 与
任意 grouped scalar expression 保持 `PIE-S2321` fail-closed；不按 spelling 猜测
group-key 等价。`GLOBAL + relation ORDER` 保持 non-concrete，不把 aggregate alias
扩展成新语言语义。

## LIMIT

LIMIT 继续调用现有 exact static checker。唯一合法 operand 是非 Boolean integer
literal，范围是 `0 <= limit <= 9223372036854775807`。完成的 limit fact 保留同一个
`LimitClause`、同一个 `LiteralExpr` 与 canonical integer value。invalid LIMIT
只保留 `PIE-S2307`，不运行 expression evaluator，也不产生字段、函数或类型
cascade。

LIMIT 只提供 output row-count upper bound；LIMIT 0 是 at-most-zero。LIMIT 1
不是 candidate key、unique identity、relationship max-one、GLOBAL aggregate 或
grain factor，且不产生 key、FD、uniqueness、cardinality 或 grain facts。

## No-JOIN Replay And Shared QUALIFY Kernel

recoverable no-JOIN owner 对精确 upstream completed `ProjectRowSchema` 重放现有
LET、row expression、WHERE Bool、aggregate/grouped finalization、satisfying、
window、QUALIFY、projection、relation ORDER 与 LIMIT helpers。原
`ProjectModuleRelationSemanticFacts` 只作为历史 occurrence authority 保留，永不
修改或替换。

WHERE 使用现有 `infer_row_expression` 与 Bool consumer，保留 LET/input scope、
aggregate-invalid-context、known Bool、`PIE-S2202` 与 SQL TRUE/FALSE/UNKNOWN
filtering law，不做 predicate-derived property strengthening。GROUPED/GLOBAL
调用现有 aggregate/grouped finalization 与 clause-readiness；不重写 aggregate。
selected no-JOIN windows 调用现有 project/window helper；hidden inline windows
调用 occurrence-neutral window computation kernel，且没有 fake
`WindowOccurrenceIdentity`。

`project_joined_qualify.py` 只抽出一个最小私有 shared QUALIFY predicate kernel。
joined API 与 no-JOIN replay 都委托它；scope lookup 仍由各自 caller 拥有。共同
kernel 负责 `PIE-S2331` window requirement、hidden-before-reference blocker
precedence、精确 ValueType seeds、现有 `infer_row_expression`、aggregate invalid
context、Bool consumer、`PIE-S2202`、SQL truth retention 与 no property
strengthening。

no-JOIN QUALIFY 的 bare lookup 合并 exact pre-window input 与 exact selected
window result，保留 0/1/N 与 `PIE-S2332`；dotted lookup 仅使用 input scope。
ordinary projection aliases 不可见，hidden results 不进入 name domain，hidden
windows 也不能读取 selected output。

## Final Output Atomicity And Boundaries

`ProjectCompletedEffectiveOutput` 保留 exact owner、Slice-11 或 downstream replay
root、ordered completed fields、`ProjectRowSchema`、row-domain posture、relation
ordering 或 explicit absence、LIMIT 或 explicit absence，以及 exact dependency
evidence。任一 select/order/limit/tail component 失败都会生成 typed terminal，
不会产生 concrete completed output。

Slice 12 只创建 semantic completion authority，不分配 FINAL_PROJECTION、
RELATION_ORDERING 或 LIMIT Project IR node，不创建 Project IR output/property。
Slice 13 才拥有包装原 `ProjectSemanticResult`、completion products、effective
outputs、diagnostics 与 public project-check success boundary 的 completed result。
本 Slice 不修改 SQL、CLI、JSON、package、dependency、workflow、Arrow 或 executor。

## Exact Changed-Path Closure

冻结的 changed-path closure 恰为八个路径：

| State | Path |
| --- | --- |
| A | `src/pietto/_project/project_final_outputs.py` |
| A | `docs/spec/phase63-slice12-projection-order-limit-final-output-ledger-completion-v1.md` |
| A | `tests/test_phase63_slice12_projection_order_limit_final_output_ledger_completion.py` |
| M | `src/pietto/_project/project_joined_qualify.py` |
| M | `docs/roadmap.md` |
| M | `docs/status.md` |
| M | `tests/test_active_phase_lifecycle.py` |
| M | `tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py` |

闭包是 `A3/M5/D0`。production Python inventory 是 `173 -> 174`；test inventory
是 `416 -> 417`。只有既有 dedicated current-inventory reader 动态扫描并断言
`174/417`；本 principal 只记录 immutable transition。

## Assurance And Publication

focused assurance 覆盖 canonical final identity、全部 projection source family、
stable naming/duplicate/unknown atomicity、三种 row-domain、ABSENT/GROUPED/GLOBAL
ORDER scope、direction/source order、LIMIT `0/1/max` 与 invalid matrix、历史
object reuse、joined completion/failure、no-JOIN selected/hidden QUALIFY、A→B→C
module propagation、upstream terminal 与 unsupported effective JOIN preservation。

静态 assurance 证明没有 final-field identity fork、历史 attribution forgery、
partial final output、projection-alias ORDER leak、GLOBAL ORDER expansion、LIMIT
max-one leak、grouped pre-aggregation grain leak、base mutation、JOIN re-entry、第二
QUALIFY/scalar/window kernel、Project IR 或 Slice-13 wrapper。

候选在 focused tests、targeted Pyright、Ruff、format、`git diff --check` 与完整
八路径 rereview 后，恰好一次运行
`UV_PYTHON=3.13 uv run python scripts/validate.py --timings`。随后只允许一个普通
commit `Complete Phase 63 final relation outputs`、一个 normal fast-forward push，
并观察自然 exact-head CI attempt 1；不 amend、rebase、force-push、dispatch、rerun
或 cancel。

## Slice 13 Handoff

成功的自然 exact-head CI 使 Phase 63 Slices 1–12 成为
`COMPLETED / PUBLISHED`。Phase 63 仍是 `ACTIVE`；Slice 13 是
`NEXT / NOT IMPLEMENTED`，Slices 14–16 仍未实现。Slice 13 单独拥有 completed
project semantic result 与 public check boundaries；本 Slice 不开始它。
