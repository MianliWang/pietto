# Phase66 Slice7 Value Bridge, JOIN/EXISTS, Outer Nulling and Terminal Output v1

## Scope

本 Slice 实现已发布的 R07/R08/R09/R10/R11 JOIN 与 membership 义务，使用既有 source、
scope、fixed-value、row-stage、verification 与 target-consumer 管线。真实 SQL 域是
ordered JOIN chain：每个 occurrence 一个 generated SELECT，输入为 physical source、
named/imported producer 或前一个 JOIN（accumulated left），其后接既有 row tail
（ordered LET、TRUE-only WHERE、最终标量投影）。N66=16。Phase65 语义/IR/plan
authority、legacy emitters 和产品执行边界保持不变。

本 Slice 另含一项被明确授权的上游 current-route 兼容修订，其完整规则记在
[route lock](phase66-dialect-sql-emission-product-phase-initiation-gate-route-lock-v1.md)
的 “Upstream current-route compatibility rule authorized for Slice7”。

R03 outstanding joint execution: Slice10 ordinary/rebound/completed ORDER and
ORDER/LIMIT sharing; Slice11 repeated UNION ALL and two import facades. 本 Slice
交付 R03 的 repeated/shared JOIN joint execution，不宣称 R03 整体完成。

R11/C09 outstanding membership differences: Slice8 GROUPED/GLOBAL; Slice9
window/QUALIFY; Slice10 LIMIT0/LIMIT1; Slice11 SET。

## Admitted JOIN shapes

| kind | native spelling | published ports | null-extended side |
| --- | --- | --- | --- |
| cross | ` CROSS JOIN ` | left ++ right | 无 |
| inner | ` INNER JOIN ` | left ++ right | 无 |
| left | ` LEFT JOIN ` | left ++ right | right |
| right | ` RIGHT JOIN ` | left ++ right | left（整个 accumulated left） |
| full | ` FULL JOIN ` | left ++ right | left 与 right |
| semi | ` WHERE EXISTS (` | 仅 left | 无 |
| anti | ` WHERE NOT EXISTS (` | 仅 left | 无 |

CROSS 必须没有 `on` 且没有 relationship equality；其余 kind 必须至少有一个
condition 组件。每个 JOIN input 的 ordinal 固定为 0/1，pre-match MATCH ports 按
`(*left.ports, *right.ports)` 排列，published OUTPUT ports 一一对应其自身 pre-match
carrier，绝不按名称或拼写去重。

### Restricted PostgreSQL FULL (R09) 与 MySQL 否定域 (R10)

FULL 仅在 PostgreSQL 且条件的每个 equality 两侧都是同一 physical storage 的
signed-integer（`pg_int2`/`pg_int4`/`pg_int8`）直接 cross-input 字段时准入；没有
cross-input equality 时以 `PIE-B1003 full_join_requires_cross_input_equality` 关闭。
MySQL 的 FULL 是 typed non-support：`PIE-B1003 mysql_full_join_approved_non_support`，
**没有任何可用 SQL**。这不是对该 target 的整体拒绝：同一 corpus 的
LEFT/RIGHT/INNER/CROSS/SEMI/ANTI 在 MySQL 上照常 emit。

## Port realization and outer nulling

published port 保留其 pre-match carrier 的 physical storage 与 value domain，只可能
新增 NULL 的可能性；原始声明绝不被改写。source field 声明在其自身域内验证，
JOIN 引起的 nullable 是独立推导的第二层：

- `nulled = carrier.nulled or side ∈ JOIN_NULLS[kind]`，membership wrapper 不 null-extend
  任何一侧；
- inherited nulling 经由前一个 JOIN 自己的 published columns 传递，所以 accumulated
  RIGHT 保留更早的 causes，ordered nulling causes 不被合并或丢弃；
- 每个实际 null-extended port 恰好产生一条 `null_extension` generated requirement。

### ON 自身的 NULL 拒绝（narrowing）

只有 matched-pairs 的 INNER 让每一行都经过其条件，所以只有 INNER 中的 NULL 操作数会
移除该行。据此，nullable carrier 只在以下条件下收紧为 NON NULL：

1. kind 是 INNER；
2. 该 pre-match port 是 effective ON 的某个 top-level AND conjunct 中某个
   comparison 的**直接**操作数；retained relationship equality 是 pre-match port 之间的
   comparison，同样证明其两个操作数。

OR 分支、`is null` / `is not null` 测试与计算出的操作数都不证明任何东西，preserved
side 从不被收紧。`lhs.key + 1 == r.key` 因此只收紧 `r.key`，不收紧 `lhs.key`。

builder、独立 verifier 与 public consumer 各自推导这一结论；consumer 只用公开字节里
解析出的条件结构，从不读取 published realization 来决定它是否合法。

## Generated units, naming and bytes

每个 JOIN occurrence 一个 CTE `p{index}`，列名 `c{i}`。JOIN input 别名为 capture-free
的 `m{n}`；physical input 用其自身 source definition 的 namespace/relation identifier，
与普通 scan 一致，因此每个 reach 到 physical relation 的 input 保留完整的
`qualified_scan`(R01) 与 `source_representation`(R02) 义务。named CTE reference 不是
另一个 physical scan。joined tail 以 `RowJoinUse` 读取最后一个 JOIN 的 published ports。

effective ON 的渲染顺序固定为：ordered relationship equalities（各自拥有自己的
enclosing span），然后 authored predicate。membership wrapper 渲染为
` WHERE EXISTS (` / ` WHERE NOT EXISTS (` + `SELECT ` + closed generated sentinel `1`
+ ` FROM ` + right relation + ` WHERE ` + 完整 effective condition + `)`。

## Generated requirement kinds

`join_use`、`join_input`、`join_output`、`join_terminal`、`relationship_equality`、
`match_condition`、`full_condition`、`membership`、`correlation`、`sentinel`、
`null_extension`，以及每个 physical JOIN input 自身的 `qualified_scan` /
`source_representation`。两个 denominator（original 与 generated）都被独立重建；
builder 与 verifier 产生同一张新清单本身不构成完整性证明，所以 public consumer
从公开字节重建第三份。

## Authored literals inside ON

ON 角色的 literal 与 bound parameter 现在与 select/let/where 角色同样被接受。
`preserve_literals` 内联渲染且不产生 native argument；`bind_safe_literals` 按 authored
顺序产生 native argument，`$n` / `?` 的出现次数与 slot 顺序精确对应。

## Target conformance denominator

完整 manifest 现为 **25 cases / 69 public documents per target**，且首次按 target 分裂：

| target | VERIFIED | INPUT_REJECTED | BLOCKED |
| --- | --- | --- | --- |
| postgres | 49 | 3 | 17 |
| mysql | 48 | 3 | 18 |

差额正是 `V_join_full/restricted`：PostgreSQL VERIFIED，MySQL BLOCKED。新增 case：

- `W_join_shapes`：`cross`、`inner`、`semi`、`anti` 的自连接 multiplicity 与
  complement；
- `W_join_values`：`left_marker`（未匹配 LEFT row 同时 null-extend retained source
  value、authored literal、computed value 与 ordered LET 结果）、`right_accumulated`
  （RIGHT null-extend 整个保留 left）、`via_refined`（relationship equality 加
  authored ON refinement）；
- `V_join_full`：`restricted`，per-target。

`O_named_later/self_join` 与 `V_row_blocked/match_join` 从 “JOIN 尚未实现” 的 blocker
迁移为独立检查的成功查询，并各自拥有独立列出的 typed BAG 与 positional metadata
oracle。`V_join_full/restricted` 的 FULL 见证的是 matched pairs 加 right-only
null-extension；本 corpus 没有 left-only partner，FULL 的 left-preserving 半边仍由
`left_marker` 的 LEFT 见证，本文件不宣称更多。

## Retained negatives and rejection controls

- base-table shortcut、`NOT IN` 改写、删除 right LIMIT/GLOBAL/SET、right output 漏入
  左 schema：保持拒绝；
- 协同删除一个 scan 及其 requirements、删除 right membership 依赖、丢失未投影的
  producer value：public consumer 拒绝；
- JOIN kind token 替换、EXISTS/NOT EXISTS 极性翻转、sentinel 改值、input alias 捕获、
  published port 改列、ON operator 替换：public consumer 拒绝；
- 把 `null_extension` requirement 移到 preserved side：public consumer 拒绝。

## Not added

grouping、windows、QUALIFY、DISTINCT、ORDER/LIMIT、SET、public project emit CLI、
caller rebind、general result decoder、product executor 都不在本 Slice。
`project_join_conditions.py` 未被修改，M1/M2/M4 relationship guarantee 未被发明或放宽。

## Controlling repository references

- [Route lock](phase66-dialect-sql-emission-product-phase-initiation-gate-route-lock-v1.md)
- [Slice6 row contract](phase66-slice6-row-scalar-let-where-on-context-emission-v1.md)
- [Isolated target conformance facility](phase66-isolated-target-conformance-facility-v1.md)
- [Development](../development.md) / [Status](../status.md) / [Roadmap](../roadmap.md)
