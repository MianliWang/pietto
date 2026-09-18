# Phase66 Slice6 Row Scalars, LET Stages, WHERE and ON Context v1

## Scope

本 Slice 实现已发布的 R05/R06 行表达式与 TRUE-only consumer 义务，使用既有 source、
scope、fixed-value、verification 与 target-consumer 管线。真实 SQL 域是单输入的
direct/named/imported/reexported TABLE/QUERY body，带既有有序 LET stage、WHERE 和
最终标量投影。保留实际验证过的 stage schedule，不按表面标签推断。N66=16。
Phase65 语义/IR/plan authority、legacy emitters 和产品执行边界保持不变。

R03 outstanding joint execution: Slice7 repeated/shared JOIN; Slice10
ordinary/rebound/completed ORDER and ORDER/LIMIT sharing; Slice11 repeated UNION ALL
and two import facades. 本 Slice 不宣称 R03 完成。

## Admitted typed expression trees

准入节点：exact field/LET reference、既有 literal/parameter、unary sign、signed-Int
`+` `-` `*`、同一 logical type 的 approved comparison、`is null` / `is not null`、
Boolean `and` / `or`。保留括号、操作数顺序与原始 identity。

| node | admitted operands | result | PostgreSQL storage | MySQL storage |
| --- | --- | --- | --- | --- |
| reference | 任一准入 stage/source 值 | 操作数的 | 操作数的 | 操作数的 |
| literal/parameter + anchor + unary | Slice5 域不变 | tag | pg_bool/int8/float8/text | my_signed_bool/int/double/utf8mb4_text |
| unary `+` `-` over 非 literal | 仅 Int | Int | 操作数中最宽的 int2/int4/int8 | my_signed_int |
| binary `+` `-` `*` | Int × Int | Int | max(width) in int2/int4/int8 | my_signed_int |
| binary `and` `or` | Bool × Bool | Bool（三值） | pg_bool | my_signed_bool |
| comparison `==` `!=` `<` `<=` `>` `>=` | 同一 logical type ∈ {Int, Text, Decimal} | Bool | pg_bool | my_signed_bool |
| `is null` / `is not null` | 任一准入值 | Bool NON_NULL | pg_bool | my_signed_bool |

不准入并以 `PIE-B1003` 关闭：`/`、`%`、`between`、任意调用、Float 或 Bool comparison、
Float/Decimal 算术、混合类型算术、Float/Decimal 字段的 unary、行值里的
joined/match/window/aggregate reference。上游接受某个 operator 本身不等于目标支持。
既有 finite-Float transport/sign 行为保持，但不授予一般 Float 算术、比较或行等价。
Decimal comparison 需要其原始精确参数；不新增 Decimal 算术或 aggregate promotion。

## Stage value construction

消费精确验证过的 expression/site、原始 operator/type 证据、operand link、LET prefix、
stage input/export 与直接 relation terminal。LET 名称不是身份；stage port 不是
source field 或 canonical output。每个 LET 只读其原始输入与既定 prefix：没有
name-based lookup、first-match binding、same-SELECT alias 依赖或对后续 LET/最终标签的引用。

沿用既有 closed CTE/SELECT 策略：每个实际原始 stage block 一个 body，显式 pass-through
列。生成 scope 绑定实际 stage occurrence，不发明 Pietto 定义。后续 stage 读取既定
stage 列；不把 LET 表达式拼接进每个 consumer、不重复抽取其 literal、不递归复制共享定义。
必需的中间计算/export/demand 即使最终不可见也保留。

命名：非最终 body 为 CTE `p{index}`；消费 input use 的 block 别名 `s{use.position}`，
消费上一 stage 的 block 别名 `t{block.position}`；CTE 列为 `c{i}`。WHERE 渲染在其
自己的 stage body 上。旧的单 PROJECTION 定义形状不变，其 SQL bytes 与 public document
逐字节保持。

WHERE 消费恰当的既定值并保持存活行的 BAG multiplicity。最终投影使用正确的 post-filter
port。命名 consumer 读取完整的直接 terminal，绝不绕过 producer 的 filter 或直接从其
祖先 source 取值。不做 predicate pushdown、constant folding、reassociation、CSE，
也不因 filter 而移除强制义务。生成的 CTE 不是强制物化、时间求值屏障或 exactly-once 保证。
准入算术必须在其声明的求值域上有效，不依赖 Boolean 左右短路或 WHERE 来阻止本可发生的错误。

## Truth semantics

标量 Bool 保持三值 TRUE/FALSE/NULL。SELECT/LET 内的 `and` / `or` 保持该结果，普通
comparison 对 NULL 仍为 unknown。只有 predicate ROOT 消费 TRUE：不对内部 Boolean
操作数或所有标量输出施加 `IS TRUE` / `CASE` / `COALESCE`。`is null` / `is not null`
是各自独立的 NON_NULL 操作。不以 null-safe equality 替代普通 equality，没有数值真值性，
也没有含2的 MySQL Bool 域。保留上游 NULL 证据：不用 WHERE 条件发明更强的语义 nullability。

逻辑 Bool、物理 source Bool0/1 与实际生成的 comparison/logical 结果元数据彼此区分，
并按目标冻结与观测，不把 source-column 元数据复制到每个表达式上。

## Finite range checking

V01 算术允许一个 emission-local 有限区间计算，来源限于已接受的 source `int_range`、
精确 fixed Int literal 与既定 stage interval，且只沿原始 unary `+` `-` 与 binary
`+` `-` `*` 传播。这是目标实现检查，不是语义求解器、可调用 evaluator 或一般约束证明器；
不从 WHERE/ON 推导更紧的域、不检视数据、不推断 FD/key、不提升上游证明状态。

每个 leaf、必要转换、中间运算与结果都对照**实际选定的** SQL 物理类型检查，包括 unary
最小整数边界与乘法端点，且不产生宿主溢出。最终结果落在范围内不能免除溢出的中间结果，
更宽的最终 CAST 也不能修复它。任何必要的无损物理 anchor 都需要显式的、已检查的规则，
不存在通用 Int->BIGINT 映射；没有无符号重解释或隐式数值/Float 提升。即使分析得到单点
区间，SQL 中仍保留原始表达式树。

缺失证据与不兼容表示是两类分别冻结的 blocker：`PIE-B1004` 对 missing evidence，
`PIE-B1002` 对 representation/range，`PIE-B1003` 对未准入规则，`PIE-B1005` 对 premise 冲突。
最小真实算术域包含常量与有界字段表达式，含依赖的 LET 链。

## Public encoding

public `pietto.sql-emission.v1` 与私有 receipt v2 的顶层字段不变。
`columns[].correspondence` 新增第三个封闭分支 `computed_origin`
{kind, expression, site, role, stage, export, terminal, operands[], source, field,
source_port}，与既有 `source` 与 `literal_origin` 分支并列，其余
expression/input_port/producer/export/projection/sql_symbol 保持。一般表达式既不是
虚构的 source field 也不是 literal；既有分支及其含义不变。没有私有上游图 dump、
额外 public format 或对既有字段的不兼容重解释。

新 range role：value_scope/value_qualifier/value_column、carry_scope/carry_qualifier/
carry_column、binary_open/close、arithmetic_operator、logical_operator、
comparison_open/close、comparison_operator、is_null_open/is_null_test/is_null_close、
where、stage_reference/stage_scope、cte_name/cte_columns_open/cte_body_open/close；
expression_range role 增加 reference/binary/comparison/is_null，与 anchor/unary 并列。

新 generated requirement kind：stage_use 与 stage_terminal（R03）、carry_projection 与
computed_projection（R05）、reference（R05，evidence `[{site, context}]`）、arithmetic、
comparison、null_test（R05）、logical 与 predicate_root（R06）。原始 demand 规则映射
增加：filter family -> R06；expression family 且 plan 节点为 logical Binary -> R06，
为 arithmetic Binary / Comparison / IsNull -> R05。Reference -> R01，literal/unary -> R04，
stage_value -> R02 保持不变。

计算值元数据保留已检查的 logical type/NULL、实际物理结果域，以及经命名使用的直接 stage
链。Boolean consumer 角色与标量值生产分开记录。fixed value/use 与 adapter 参数仍来自
实际生产文档与独立 decoder，不来自并行私有信封。

## Independent verification and consumption

plan-to-AST/stage 对应与 events-to-final-bytes 验证同时扩展。两个 verifier 都不通过重跑
builder/renderer 或语义 resolver 获得期望：独立重建实际 operand（依据保留的 operand
link，而非节点字段）、stage schedule/列/引用、全部原始 demand，以及由 operator/转换/
filter/生成 scope 引入的 requirement。同时删除两张清单，或同时删除一个未使用的 LET 与其
附属记录，都必须失败。

渲染期以最终 SQL UTF-8 字节坐标记录词法范围与外层表达式范围；原始 parser 字符 span 单独
保留。检查 operator 拼写/优先级、Boolean root 角色、括号/分隔符、capture、source cause、
每个 marker 与重叠表达式归属。正确的范围/元数据不能为被改动的 operator 或不同的 stage
引用背书。

test-only 独立 public consumer 扩展同一个既有 decoder，而不是新增第三个各自分叉的 decoder：
共享的 contract/field/premise/constant-leaf/parameter 机制全部复用，仅新增 carried port、
准入 operator 节点、stage scope 与 filter root 的语法。named-definition CTE 与
stage-select-block CTE 是显式区分的绑定情形。consumer 自行重导出 realization 与两个
requirement 分母，不从产品模块导入规则函数。

## Manifest

Slice5 的 A–S19 cases/46 public documents 是历史事实，不是 Slice6 的状态总量。
`L_emission_blocked/where_later` 与 `O_named_later/producer_filter` 的原 blocker 是尚未实现
的 WHERE family，其既有前提已满足新规则，因此迁移为独立检查过的成功查询；原始 source 目的
与历史结果保持，变体名不是状态权威。只有 `where_later` 需要补充 identifier_case 输入前提，
并记录为变更过的输入身份。

新增 `T_row_direct`（table_preserve、query_bind、empty_preserve、truth_table）、
`U_row_named`（named_preserve、imported_bind、empty_preserve）与 `V_row_blocked`
（float_arithmetic、float_comparison、bool_comparison、int_overflow、unary_overflow、
modulo、between、match_join）。T–V22 cases/61 public documents per target include
39 VERIFIED,3 INPUT_REJECTED,19 BLOCKED；A–F 与 Q protocol control 不计入 document 数。
`truth_table` 在两个真实目标上见证 AND 与 OR 的全部九组有序三值配对。

## ON/MATCH

本 Slice 的 ON/MATCH 指针对真实验证过的 pre-match 输入做实际类型化表达式/上下文检查，
以及共享的标量实现接缝。整个 JOIN 的构造与执行属于 Slice7。JOIN plan 可以触发该
applicability consumer，但仍然 BLOCKED，且没有任何可用的部分 SQL 或 public 成功。
不把 ON 改写成 WHERE、不发明单输入替代、不把片段检查算作已执行的 JOIN。
Satisfying/QUALIFY 集成同样保留在其既有 operator owner。

## Not in this Slice

无 JOIN/EXISTS、grouping、window、DISTINCT、ORDER/LIMIT、SET、新增 authored syntax、
public project CLI、caller rebind、private portable product、general result decoder 或
product executor。不重开 phase initiation，不改变已发布的 slice 排程。
