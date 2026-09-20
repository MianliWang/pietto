# Phase66 Slice8 GROUPED/GLOBAL, satisfying and Aggregate Emission v1

## Scope

本 Slice 实现已发布的 R12/R13 与 T06：GROUPED/GLOBAL 原生分组、satisfying 的后聚合
谓词阶段，以及 aggregate 结果的精确 physical representation。它消费既有 source、
scope、fixed-value、row-stage、JOIN、verification 与 target-consumer 管线，不新增
optimizer、grouping sets、ROLLUP/CUBE、fanout-safe reaggregation、SQL function/plugin
registry、public project emit CLI、caller rebind、general result decoder 或 product
executor。N66=16。Phase65 语义/IR/plan authority、legacy emitters 与产品执行边界不变。

基线 commit `0a84a483828659e328f81f8d6d13702417c007d9`，tree
`145ea8323afbcfccf331d83b54b893cbcc83819d`，parent
`c029eefe591d481efc3cb23949987f8a587bbec8`；自然 CI `35494822267` 为
push/main/attempt1/success。

R03 outstanding joint execution: Slice10 ordinary/rebound/completed ORDER and
ORDER/LIMIT sharing; Slice11 repeated UNION ALL and two import facades。本 Slice
不推进 R03。

R11/C09 outstanding membership differences: Slice9 window/QUALIFY; Slice10
LIMIT0/LIMIT1; Slice11 SET。本 Slice 只交付 GROUPED/GLOBAL right-terminal 这一项
sub-obligation，不宣称 R11/C09 或 R03 整体完成。

## 阶段调度

一个 definition 的准入阶段顺序恰为

    complete input terminal -> let* -> where? -> aggregate -> satisfying? -> projection

每个阶段是它自己的 generated SELECT。joined definition 的第一个阶段读取自身 JOIN
tail，因此只有 ordinary 的第一个阶段声明 `relation_input` operator。aggregate 阶段的
exports 恰为该 aggregation 的 `results`（先 ordered determinants，再 ordered
occurrences），satisfying 阶段整列 carry 并追加一个谓词，最终 projection 只输出
`aggregate_projections` 指定的 canonical 可见输出。

GROUPED 的 `GROUP BY` 绑定实际输入表达式/列；GLOBAL 完全不发出 `GROUP BY`。输出
alias 与数字 ordinal 都不参与绑定：一个常量值分组键按其已建立的 producer port 分组，
而不是 `GROUP BY 1`。ONLY_FULL_GROUP_BY 保持开启；不发出 `ANY_VALUE`、代表行、
把未分组字段包进 MIN/MAX、额外分组键或任何 session 规则改动。

## 函数、类型与结果域（R13）

| authored | native | result tag | result storage | nullable | result domain |
| --- | --- | --- | --- | --- | --- |
| `count()` | `COUNT(*)` | Int | `pg_int8` / `my_bigint` | 否 | `int_range 0 .. 2^63-1` |
| `count(field)` | `COUNT(col)` | Int | `pg_int8` / `my_bigint` | 否 | `int_range 0 .. 2^63-1` |
| `count_distinct(field)` | `COUNT(DISTINCT col)` | Int | `pg_int8` / `my_bigint` | 否 | `int_range 0 .. 2^63-1` |
| `min(field)` | `MIN(col)` | 参数 tag | 参数 storage | 是 | 参数 domain |
| `max(field)` | `MAX(col)` | 参数 tag | 参数 storage | 是 | 参数 domain |
| `sum` / `avg` | 无 | — | — | — | APPROVED_NON_SUPPORT |

`COUNT` 的结果域来自 R13 已声明的 signed64 前提，不从参数的数值范围推断，也不制造
physical uniqueness；它不是一条通用 input-cardinality 证明义务，既有 aggregate/error
契约保持不变。`MIN`/`MAX` 保留参数的 representation，但因为空输入与全 NULL 输入没有
极值，结果一律 nullable，即使参数列本身 non-null。

aggregate 参数只准入一个 direct established field reference（含既有 LET-fed field
reference）。argument 内的 scalar call、算术与 literal 仍为 non-support。
`sum`/`avg` 在任何位置——直接选中、隐藏在 named producer 里、或只作为 membership
右侧——都保持同一条 typed blocker
`PIE-B1003 sum_avg_result_realization_rule_not_reviewed_in_phase66`，不做 final
CAST、rounding 规则或空输入捷径。

`count_distinct` 只是该 aggregate 自己的 `DISTINCT` 修饰，不是整行 DISTINCT，也不
授予通用 inline modifier、aggregate `FILTER` 或 aggregate 内部 ordering。

## 分组比较域（R12）

group determinant 停留在已 review 的 V01–V04 域：Int（须有 `int_range` 证据）、
Bool（须为精确 `bool01` 域）、Text（须有精确 encoding/collation/padding）、
Decimal（须有精确 precision/scale）。V05 保持其既有意义限制，V06 的 transport
不授予 Float 分组或相等比较：Float 分组键得到
`PIE-B1003 group_key_type_outside_reviewed_comparison_domain`。被违反的 source 域
（例如 Bool 声明成 `int_range 0..2`，或 Decimal storage scale 与 logical 参数不符）
仍是 `PIE-B1002` representation 失败。

## 空输入、NULL 与重复

GROUPED 空输入产生零个 group；GLOBAL 空输入仍产生恰好一行，且其下方的 false WHERE
不会抹掉那一行。全 NULL 行与没有行不同：`COUNT(*)` 计行，`COUNT(field)` 与
`COUNT(DISTINCT field)` 不计 NULL，极值为 NULL。分组比较把 NULL 键视作同一组。
重复声明的相同 aggregate 各有自己的 occurrence 与 result port，不做 CSE；两个不同
group 可以投影出完全相同的可见行，其 multiplicity 必须保留。

## satisfying

satisfying 实现为一个确定性的外层 SELECT + WHERE，读取 aggregation 阶段已建立的
result 列。这是所要求的 HAVING 行为的一个有效实现；验收标准不是出现 `HAVING` 字样。
只有 predicate 根为 TRUE 的 group 被保留；内部 Bool 值保留 TRUE/FALSE/NULL 与既有
AND/OR/比较/NULL-test 树，不对标量操作数施加 COALESCE/IS TRUE。satisfying 的别名、
重复引用与已解析的 unique aggregate-LET 引用都解析到同一个既有 result port，是
use 而不是新的 computation。satisfying 不会下推到 pre-aggregation WHERE，也不能通过
同名捕获 raw input、旧 JOIN 或 row-LET 值。

源码层面的 `GLOBAL + satisfying` 仍然被上游拒绝。已支持的替代 composition 是：一个
named GLOBAL producer，后跟一个普通 consumer filter——包括移除空输入 `count=0` 那一
行的 filter。这不是新语法。

## 上游 aggregate-producer completion 路线

被明确授权的窄扩展只作用于 completion 的路线选择：`_promoted_scalar_producer`
现在除既有 ordinary scalar body 外，还接纳 mode 为 GROUPED/GLOBAL、
`aggregate_readiness` 为 CONCRETE、每个 selected output 都是该 stage 自己的
`ProjectNoJoinGroupedOutput`、没有 relation ORDER/LIMIT barrier，且**确有一个
authored JOIN 直接消费该 producer** 的 no-JOIN body。没有 JOIN 消费者的 grouped
producer（例如只被 SET operand 消费的 GLOBAL producer）保持其原有 base route 与
自身 `historical_properties`，其 GLOBAL grain 证据不被这条路线改动。
window/QUALIFY（selected 或 hidden）排除保持不变，旧 scalar 路线及其排除保持不变，
不删除任何 aggregate guard，也不把每个 replay 归类成 scalar。

被提升的是 grouped/global 结果本身，不是其原始来源行：GLOBAL 结果不是它的 raw
source row，带隐藏键的 GROUPED 结果既不是 GLOBAL 也不是唯一可见 tuple。可传输性
不产生 relationship-endpoint 或 M1/M2/M4 guarantee；joined field aggregate 仍需要
其既有 grain/uniqueness 前提，缺少时保持 `PIE-S2333`。

Slice7 的 later-owner 排除只迁移其 aggregate 分支；window 分支保留为真实负例。该排除
的两个 fixture 此前都在 parse 阶段失败，现已改写为真实可接受的源码表面。

## Composition 与 R11/C09

两个方向都交付：JOIN -> aggregation（在 joined grain 上，`COUNT` 计 joined
occurrence 而不是唯一 base entity，不插入 DISTINCT 掩盖 multiplicity），以及
aggregation -> JOIN/SEMI/ANTI（经完整 terminal）。已算出的 aggregate 值在 outer
join 上被 null-extend：右侧 GROUPED producer 的 non-null count 在其 GROUPED 行缺席时
变为 NULL，不重算 COUNT，也不用 0 替代 NULL；nulled port 仍保留 count 自己的非负
signed64 域。

SEMI/ANTI 消费完整的 GROUPED/GLOBAL/satisfying 结果：不简化成 `EXISTS(raw source)`，
不用 sentinel 替换 producer SELECT，不丢弃 grouping 或 satisfying，不丢右侧依赖。
生成的 wrapper sentinel `1` 是结构常量，左侧 multiplicity、TRUE-only matching 与
`NOT EXISTS`（而非 `NOT IN`）保持不变，左 schema 不含 right output。

既有 group protection、STRICT-FD、grain/pair/fanout/chasm 风险记录、single-match
请求/证明/警告与其 enforcement 按原单位保留；不新增 proof solver 或 fanout-repair
reaggregation。

## 公共 artifact

公共格式仍是 `pietto.sql-emission.v1`，测试 receipt 仍是 v2。本 Slice 在既有
correspondence 内新增两个封闭的 provenance 备选：canonical 可见 aggregate 输出用
`aggregate_origin`，经 row stage、named chain 或 JOIN port 传输的 aggregate 值用
`aggregate_transport`。两者字段相同：`role`（`group_key` / `aggregate_result`）、
`mode`、`empty_input`、`aggregation`、`stage`、`function`、`determinant`、
`aggregate`、`arguments`、`inputs`、`result`。row count 的 `arguments` 为空而
`inputs` 是该 stage 的完整输入终端——空的 scalar argument 集合不是空依赖集合。常量值
determinant 保留它自己的 `literal_origin`。

新增的 generated requirement kinds 为 `aggregation`、`group_key`、`aggregate`、
`result_projection` 与 `satisfying_root`；新增的 range roles 为 `group_by`、
`group_separator`、`grouping_scope`/`grouping_qualifier`/`grouping_column`、
`group_key_scope`/`group_key_qualifier`/`group_key_column`、
`result_scope`/`result_qualifier`/`result_column`、
`aggregate_open`/`aggregate_close`/`aggregate_distinct`/`aggregate_row_count`、
`satisfying`，以及 `grouping` 与 `aggregate` 两个 expression range。保留的
aggregation demand 家族按 subject 归属规则：`aggregate` 归 R13，其余归 R12。

## 验证

plan→AST verifier 独立重建完整 aggregation inventory、argument 与 result 角色分离、
隐藏 determinant、阶段调度、canonical 输出映射、satisfying uses 与原风险/义务覆盖，
不调用 builder、renderer、semantic resolver 或 type/grain solver。events→bytes
verifier 独立复核函数拼写、`COUNT(*)` 与 `COUNT(column)` 与 `COUNT(DISTINCT column)`
的区别、GROUP BY 绑定、阶段边界、匹配作用域、后聚合谓词、native parameter token 与
完整 UTF-8 range。独立的 data-only 公共 consumer 以窄的可复用 scope/qualifier/column
语法原语扩展，仍对每个源的 type/storage/domain/NULL/premise 做自己的检查。

fixed-value 管线保持 default PRESERVE 与显式 BIND_SAFE：satisfying 位置由既有抽取
规则判定为 specialized，因此在 BIND_SAFE 下仍保留字面量，而同一 body 的 pre-group
WHERE 字面量仍然绑定为一个 native argument。verifier 独立重推这条 eligibility，
而不是接受 builder 的结论。

本 Slice 新增的 graph-bearing 类型（`AggregateOrigin`、三个 column 类型、
`AggregateStage`）都有常数工作量的 bounded repr，不递归展开共享 provenance，也不改动
equality/identity 或 public serialization；一个有意的失败断言保留为回归。

## 目标一致性 denominator

manifest 从 25 cases / 69 public documents per target 扩到
35 cases / 107 public documents per target：
postgres 81 VERIFIED、3 INPUT_REJECTED、23 BLOCKED；
mysql 79 VERIFIED、3 INPUT_REJECTED、25 BLOCKED。差异仍只来自 R09/R10 的 FULL 域。
五个固定聚合关系（`phase66 agg é`、`phase66 agg empty é`、`phase66 agg trio é`、
`phase66 agg nulls é`、`phase66 agg keys é`）的每一行都在测试内独立声明，绝不从
observation 反读。

## 不在本 Slice

window/QUALIFY emission 属 Slice9，result DISTINCT/ORDER/LIMIT 属 Slice10，SET 属
Slice11。本 Slice 不新增 grammar、public API/CLI/JSON top-level key、portable format、
依赖、workflow、golden、版本或 product execution。
