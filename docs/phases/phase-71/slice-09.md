# Phase71 Slice09：Collect 的 compiled 表示、source-free 契约与 Unnest 保留表示

状态：candidate（批次 B3），定稿。S09-A（闭合描述层：schema 词表、`verify_description` 的 collect、
collection 与 unnest 规则、`output` 记录交叉核对、`layout` 的显式拒绝）与 S09-B（build 导出、`verify_export`
与 compiled emission 的对应核对、lowering、compiled 语义/IR/plan、compiled 授权下的嵌套合同、模板闸门、真实
source-free 闭环）同在本片的一笔提交中，建立在 [S08](slice-08.md) 之上；批次 B3 建立在 main 的 `81f0d3b5` 之上，
其发布规则见[路线](slices.md)，发布之前本片是 candidate。
决定来源：S09 Gate 1 记录（ARCHITECTURE_DECISION，D-S09-1..9）与 S08 Gate 1 的 D-S08-8（闸门的移交）。
本文件是 S10–S19 读取的私有表示与交接规则；私有格式不进 `docs/spec/`，没有公开 JSON、CLI 或 SQL 变化。

## 1. compiled 记录

版本：`VERSIONS = (6, 1, 6, 1)`。升的是 schema（collect operator、collection 标签、`unnest` 键）与
occurrence（新的块读 occurrence）；semantic 与 profile 不变。旧 bundle 本来就因代码身份被拒（`PIE-R1005`
或 `COMPILED_COMPATIBILITY`），版本是维度标签，不是安全机制。

| 元素 | 记录 | 规则 |
| --- | --- | --- |
| Collect 读 | `expression_block_use (operation, consumer, producer, column)` | `column` 为 null；`producer` 是被收集 let 的 `result` unit，`ordering` 非空（D71.03）；closed let 有位置（CTE），captured let 无位置（inline）；`consumer` 是该 let 的父（声明它的 table 或 query，是否 entry 都可以）的 projection `row`：同一坐标、`let` 为 null、不拥有 table function；沿用 `e<n>` 别名、`capture_use`、`inline_units` 与 `captured_reads` |
| 值 | `operation (operator, operands, logical, site)` | `COLLECT_OPERATOR = ("collect", "collect")`，不在 `BLOCK_READ_OPERATORS` 中；`operands = ()`；`logical = ("collection", "non_null")`；`site` 为 null（与所有 operation 相同） |
| 端口 | `port` | `("collection", n)`：source 是 Collect（端口属于该 projection row，`n` 等于 Collect 的 non_null），或 source 是父 `result` unit 对这种端口的 value read（端口属于该 result，logical 相同）。读者（`from` 或 JOIN）的 `use` 可以列出父的 collection 端口，但不读、不携带它 |
| output | `output` | `logical` 等于端口的 logical，`meaning` 为 null（D-S09-9） |
| 子字段 | 不新增 | producer result unit 的端口，按顺序；都是标量。被收集终端的端口 `label` 是 let 的字段名（Collect 的子 label），不是 CTE 的 `c<i>`；它的体照常渲染为 `c<i>`（D-S09-10） |
| 顺序 | 不新增 | producer `result.ordering`，隐藏键由 projection 的 helper port 承载 |
| LIMIT | 不新增 | producer `result.limit`/`limit_literal`（恒为 `preserved_with_reason`，在 pin 中） |
| ordinal、count、arrays、laterals、carrier | 不持久化 | lowering 从已验证 emission 与 ResultContract 推导，live 与 compiled 各自重算（D-S09-7） |

`unnest`（保留，S13 接通前拒绝）：`(owner, position, source, fields, outputs, layout)`。`owner` 是所在声明，
`position` 是 U1 的 `unnest_position`（同一声明内两个 Unnest 不会碰撞），`source` 是 JOIN 左输入上被展开的
嵌套端口，`fields` 是按子顺序的 `field` 记录，`outputs` 是端口。它不在 `RELATIONS` 中，不进入任何执行闭包。

## 2. 描述层拒绝（`verify_description`）

| 情形 | 类别 |
| --- | --- |
| 任何成员中出现 `unnest` 记录，与位置和个数无关 | `COMPILED_UNNEST_UNAVAILABLE`（逐记录检查之前） |
| `unnest` 记录字段数不符 | `COMPILED_FIELDS`（decode） |
| MySQL 描述中出现 Collect 读 | `COMPILED_COLLECT_TARGET` |
| Collect 读的 column 不为 null；producer 不是 result 或 ordering 为空或不属于 let；consumer 不是该 let 的父的 projection row；captured let 的 inline unit 被第二个读者读 | `COMPILED_EXPRESSION_BLOCK_USE` |
| 一个 Collect 没有或有两条块读 | `COMPILED_EXPRESSION_BLOCK_USE_INVENTORY` |
| Collect 带 operand | `COMPILED_OPERATOR_ARITY` |
| 任何 operation（Collect 或平面值）的 `site` 不为 null：build 从不写它，literal、slot 与谓词调用各自记录 site | `COMPILED_OPERATION_SITE` |
| Collect 的 logical 不是 `("collection", "non_null")`；其他 operation 带 collection logical | `COMPILED_COLLECT_LOGICAL` |
| Collect 不止是一个 row 的直接值、其端口的 source 与其块读的 operation（例如在谓词、JOIN 谓词或另一个 operation 中） | `COMPILED_COLLECT_PLACEMENT` |
| JOIN、聚合或窗口值引用 operation（与 Collect 无关，种类本来不准入） | `COMPILED_REFERENCE` |
| field 带 collection logical | `COMPILED_FIELD_LOGICAL` |
| 其他带 logical 的记录（join/set/aggregate/window 值）带 collection logical，与描述中有没有 Collect 无关 | `COMPILED_COLLECTION_LOGICAL` |
| 端口的 collection logical 与其 source 不符（扫描端口、普通 read、可空容器、Collect 端口改成标量、读者再次选择它，同 `PIE-S2805`） | `COMPILED_COLLECTION_PORT` |
| collection 端口被父 result projection 之外读取（如作父 ORDER 键、作 capture、作读者 JOIN 或窗口值的输入），或被一条不读其 owner 的 use 列出，或读它的 result 是 `distinct`（collection 没有相等，同 S04 的 `PIE-S2805`） | `COMPILED_COLLECTION_READ` |
| `output` 的 logical 与端口不同，或 meaning 不为 null | `COMPILED_OUTPUT_PORT` |
| 描述的版本标签不是当前 `VERSIONS` | `COMPILED_COMPATIBILITY` |

requirement 记录的 `anchors` 只锚定 occurrence，不放置值，放置规则不计它们。公开 `load_bundle` 对这些拒绝报
`PIE-R1008`，detail 是上表类别；不连接、不 import driver、不读 workspace。真实 bundle 的公开结果不变；公开差别只在
伪造 bundle 上：伪造 `unnest` 的 detail 从 `COMPILED_ADDRESS` 变为 `COMPILED_UNNEST_UNAVAILABLE`；`output` 的
logical/meaning 与端口不符的 bundle 原先被接受，现报 `PIE-R1008` `COMPILED_OUTPUT_PORT`；只改导出端口的标量 logical（nullability 或类型）而不改 `output` 副本的 bundle，原先在准备时报 `PIE-R1004` `COMPILED_PORT_TYPE`，现在加载时报 `PIE-R1008` `COMPILED_OUTPUT_PORT`（两者都在连接之前；`output` 副本一起改时仍是 `PIE-R1004` `COMPILED_PORT_TYPE`）；operation 上伪造的 `site` 原先被接受，现报 `PIE-R1008` `COMPILED_OPERATION_SITE`；端口、output 或值记录上
伪造的 collection logical 原先在 emission 报 `PIE-R1004` `COMPILED_LOGICAL_TYPE`，现在描述层报 `PIE-R1008` 与上表类别。

S09-A 的中间态（只有词表与描述层）只在私有开发中出现，不入库。

## 3. build、lowering 与独立核对（S09-B）

**build（`project_compiled_build`）**
- `_Export` 在父 projection row 的 `CollectColumn` 处写 Collect 的 operation、它的 `expression_block_use`（column 为
  null，producer 为被收集 let 的终端 result unit，`e<n>` 与 live 相同）与 `("collection", "non_null")` 端口；captured
  let 的 unit 与 `capture_use` 在这个读处导出（与 block read 共用 `inline_let`）。父 result unit 的
  `ResultGroupColumn` 是对该端口的 value read。ordinal、lateral、carriers、DISTINCT wrapper 都不持久化（D-S09-7）。
- requirement 锚点：Collect 的 COLLECT/COLLECT_ORDER 需求锚定 Collect operation，COLLECT_EXPORT 锚定它的端口与父 result
  的携带端口；`verify_compiled_requirement_inputs` 接受 subject `collect` 与 COLLECTION 家族的 `export`，compiled
  规则为 R27（与 live 相同）。
- D-S09-10（本片新增，F-S09-11）：被收集终端是 CTE 时，它的端口 label 原是 `c<i>`，let 的字段名不在任何记录中；
  这些端口改存字段名。lowering 照常把它们渲染为 `c<i>`（所有非 final 的 result 列都如此），平面 bundle 不变。
- D-S09-8：保留（未选中）owner 的 plan 有 Collect 时，`_LogicalExport` 报 `COMPILED_RETAINED_COLLECT`，取代 S08 在
  `build_compiled` 中的两处 `NESTED_UNAVAILABLE`；选中 owner 的 Collect 现在导出。
- OBS-1（早于 S09，S09 收尾时修复）：保留 owner 的 ORDER BY 不带 DISTINCT 时，排序键是 projection 旁的隐藏端口，
  `_LogicalExport` 没有它的形式；`logical_results` 原来在 `zip(strict=True)` 抛未类型化的 `ValueError`，现在报
  `COMPILED_RETAINED_ORDER`。生产只重绑已有的 single-match 请求，没有公开路径到达这里。
- `verify_export` 独立核对每个 Collect 列（`EXPORT_COLLECT`）、被收集终端端口的字段名（`EXPORT_COLUMN_LABEL`）与
  COLLECTION 需求锚点（`EXPORT_REQUIREMENT_COLLECT_ANCHOR`）。

**compiled 语义、IR 与 plan**
- `derive_compiled_semantics`：Collect 依赖其终端的全部端口；它与携带它的端口、read 得到嵌套事实
  （`CompiledScalarFact.nested` 为 S04 的 `NESTED_RELATION` 类型，只由记录重建，I-S04-C1；value type 名为
  `<nested relation>`、不是 builtin；没有 realization）。`declared()` 仍只认标量；任何标量读者对嵌套事实调用
  `require_realization()` 报 `COMPILED_LOGICAL_ONLY_FACT`，Collect 落进标量值位置时 lowering 报
  `COMPILED_COLLECT_PLACEMENT`。`verify_compiled_semantics` 独立重推这些事实（`SEMANTIC_COLLECT`）。
- `build_compiled_query_block_ir`：嵌套端口的证据类型就是该描述符，值与 live 描述符相等；嵌套字段不在任何 value
  class 中（D-S04-3），compiled property law 同样排除它。
- `CompiledSQLPlan.collects`：每个 Collect operation 一条 `CompiledSQLCollect`（ref、block、export、use、producer、
  children、captures）；`verify_compiled_sql_plan` 对照记录独立核对，删除、复制、换序、嫁接都报
  `COMPILED_PLAN_COLLECT_INVENTORY` 或 `COMPILED_PLAN_COLLECT`。

**lowering（`emit_compiled`）与发射核对**
- 父 projection row 的 Collect 端口经 S08 的 `realize_collect` 建 `CollectColumn` 与 lateral；captured let 在 lateral
  内按既有 inline 链构建；被收集终端（无 DISTINCT）带 S08 的 ordinal；父 result 把嵌套组整体带到终端
  （`ResultGroupColumn`）。同一套 AST 类与 renderer，SQL 与 live 逐字节相同。lowering 的漂移类别是 S08 的
  detail，例如 `COMPILED_COLLECT_CHILDREN_DRIFT`。
- `_verify_compiled_emission` 只对照记录核对 Collect 列（`EMISSION_COLLECT`、`EMISSION_COLLECT_TERMINAL`、
  `EMISSION_COLLECT_ORDINAL`、`EMISSION_COLLECT_CARRIERS`、`EMISSION_COLLECT_INLINE`）、每个体的 `laterals`
  （`EMISSION_LATERALS`）、result 的嵌套组（`RESULT_GROUP`）与 ordinal 的有无（`RESULT_ORDINAL`）。生成需求的独立
  核对对 DISTINCT wrapper 读终端自己的 ORDER（与无 DISTINCT 时的 ordinal 相同），不再读 live plan 的 ORDER 记录。
- compiled 授权下的 `build_result_contract`/`verify_result_contract` 接受嵌套字段（`_compiled_element`：经父 result
  的 read 找到 Collect、它的终端与子端口，子 label 与 nullability 必须等于描述符），取代 S07 留下的
  `SCALAR_UNAVAILABLE`；子 Timestamp 带它的意义 round trip。

## 4. compiled digest v2（slice-07 §4.2 的实现）

`contract_digest` 的 compiled 分支：先 `verify_result_contract`；平面合同写 `pietto.compiled-result-contract.v1`，
字节不变；至少一个嵌套字段时写 `...v2`，嵌套 entry 为 `[ordinal, label, "collection", 容器 nullability,
[子标量 entry…]]`，子 entry 与 v1 标量 entry 相同；子 shape 不是 `ScalarShape` 时报 `ResultError("FIELD")`。
`project_result_ipc.py` 是 B3 共享写面：这段改动由集成者在 S09 的提交中接线，S10 的 IPC guard 在 S10 的提交中接线。
它的测试（AC-05、AC-12）与下面 `layout` 的嵌套拒绝测试（AC-04）属于 S07 owner `tests/test_results_nested_relations.py`，
同样以精确 patch 交集成者，S07-B 封存后（必要时 rebase）在 S09 的同一提交中写入。

`project_job_delivery.layout` 改经 `scalar_fields(contract)`：平面返回同一个 tuple，字节不变；嵌套报
`NESTED_UNAVAILABLE`。S20 复核 R2/sink。

## 5. source-free 契约（A07 私有层；公开执行归 S12）

只用 bundle 字节与调用者的三条记录，不读项目文件。已证明（`tests/test_execution_nested_relations.py`，SF6 在
`tests/test_execution_compiled_source_free.py`）：

1. `load_compiled` → `emit_compiled` 的 SQL 与 live S08 artifact 逐字节相同：S08 的 14 种形状、literal oracle 的
   C1–C10 Collect 程序（preserve 与 bind-safe）、bind-safe 与 header 参数的原生次序，以及 Decimal、Timestamp 子 leaf。
2. 每个 lateral 的 carriers、arrays、ordinal 与 wrapper 与 live 相同。PG carrier descriptor（`pg_column_arrays_v1`）
   随 D-S08-7 归 S10，其 live/compiled 相等由 S10（或 S12）验收（S08 F-12）。
3. compiled `build_result_contract` 得到 `NestedShape`，子字段个数、顺序、label、canonical、nullability 与意义与
   live 相同；v2 digest 在 live 构建的 root 与 loaded root 上相等，并等于 v2 文档的字面重算。
4. 隐藏 ORDER 键在 bundle 中保留，ordinal 的 ORDER 项与 live 相同。
5. 没有源 I/O；新进程中没有项目也没有测试 helper、driver 或 pyarrow。

pin 覆盖：只改第一个字段的子排序方向或键、只换被收集的 let（子 schema 相同）、只改子 LIMIT，都改变 pin 与
v2 digest；同一源码独立构建两次，payload、pin 与 digest 都相同。三项都已在 pinned records 中，没有新增记录。

真实嵌套 bundle 的拒绝（重新 pin 后在 load 或 lowering 报 `CompiledError`，不 import driver，不连接）：producer 改为
let 的 projection row、column 不为 null 或去掉 ordering（`COMPILED_EXPRESSION_BLOCK_USE`；closed let 去掉 ordering
先报 `COMPILED_RESULT_BOUNDARIES`）、Collect 的 logical 改为标量（`COMPILED_COLLECT_LOGICAL`）、Collect 带
operand（`COMPILED_OPERATOR_ARITY`）、端口可空（`COMPILED_OUTPUT_PORT` 或 `COMPILED_COLLECTION_PORT`）、`output`
改为标量（`COMPILED_OUTPUT_PORT`）、第二个 Collect 读第一个的 let（`COMPILED_RELATION_INVENTORY_CLOSURE`）、去掉
`capture_use`（`COMPILED_INLINE_INVENTORY`）、captured 终端的子端口换序（`COMPILED_COLLECT_CHILDREN_DRIFT`）。
翻转排序方向、交换两个 closed let 的读或 closed 终端的列序都是另一个自洽的程序，由 pin 区分，不是拒绝。

## 6. 公开面

S09 没有公开 JSON、CLI、SQL 或诊断码变化，`pietto` 没有新名字。D-S08-8 的判定从 `build_compiled` 移到模板闸门：
`project_execution_binding_verification.verify_template`（每个执行模板都经过它，`prepare_template`、
`prepare_guarded_template` 与 `bind_values`）对有 Collect 的 plan 抛 `CompiledError("NESTED_UNAVAILABLE")`，与 S08
同一个词：`compile_query` 仍报 `RequestRejected` `PIE-R1004`；私有构建的嵌套 bundle 经 `load_bundle` 也报
`PIE-R1004` `NESTED_UNAVAILABLE`，都在连接、workspace 与 driver import 之前。该文件不在原生执行族输入闭包所列
文件中（development.md 的列表）；B3 的 D71.11 原生族运行由 S10 的 rows campaign 在含本片代码的批次候选 wheel
上进行（S08 的目标变体运行移交 S12）。

## 7. 交接规则

- S08：D-S08-8 的判定已由 §6 的模板闸门取代（同一个词）；保留 owner 一处改为 `COMPILED_RETAINED_COLLECT`。
  `tests/test_execution_compiled_families.py` 的 S08 用例相应改写为保留 owner 的拒绝。
- S10：`project_result_ipc.py` 中只改 `encode_ipc`/`open_ipc`，不改 `contract_digest`。S10 的 carrier descriptor
  在 compiled artifact 上重算并与 live 相等（S08 F-12）。
- S12：删除 `verify_template` 的闸门（S13 前它也要挡 Unnest）；公开 live→compiled 纵向；`docs/execution.md` 的
  bundle 文字。
- S13：用真实 producer 替换 `COMPILED_UNNEST_UNAVAILABLE`；形状不符时再升 `VERSIONS`。Unnest 的 JOIN 经 `join_value`
  携带左输入的 collection 端口，今天按 `COMPILED_COLLECTION_LOGICAL` 拒绝；S13 放宽这条规则并为它加测试。
- S08/S12：父不是 entry 的 Collect 在描述层已被接受。读父的关系不选嵌套列时，`from parent select ...` 与
  `from parent ... order by ...` 已被接受；但读者的行 stage（`where`；`let`、`satisfying`、`qualify` 等其他携带输入
  端口的行 stage 同理）携带父的全部输入端口，其中的 collection 端口由 row 拥有，按 `COMPILED_COLLECTION_PORT`
  拒绝；JOIN、集合运算或窗口读者对父的携带也仍被拒绝（`COMPILED_COLLECTION_LOGICAL`/`COMPILED_COLLECTION_READ`）。
  这些都失败关闭。读父关系的读者在 PostgreSQL 上的发射归 S16（D-S08-4），S16 打开它们时一并放宽这些描述层规则
  并加测试；在那之前，这类读者在发射时仍报 `PIE-B1003`（D-S08-4），不会产生到达描述层的真实 bundle。
- S15：Timestamp/UUID 子 leaf 的执行开放；S09 已证明 Timestamp 子 leaf 带意义 round trip。
- S20：复核 `layout` 与 R2/sink 的拒绝；保留 owner 的 Collect 仍是 `COMPILED_RETAINED_COLLECT`。
- S17–S19：v2 digest 进入 IPC 帧、job 记录与断源读取。

## 8. 测试 owner

| owner | 内容 |
| --- | --- |
| `tests/test_execution_nested_relations.py` | 描述层（S09-A）；S08 全部形状的 build、load、lowering、SF1–SF4、描述符；literal oracle 的 Collect 程序；参数次序；Decimal/Timestamp 子 leaf；pin 覆盖；真实 bundle 的拒绝矩阵；compiled 事实、IR 与 plan Collect 记录；公开 PIE-R1004；SF5 |
| `tests/test_execution_compiled_source_free.py` | SF6：新进程中的嵌套 bundle |
| `tests/test_execution_compiled_families.py` | 保留 owner 的 `COMPILED_RETAINED_COLLECT`（取代 S08 的 build 拒绝用例）；隐藏排序键的 `COMPILED_RETAINED_ORDER`（OBS-1） |
| `tests/test_results_nested_relations.py` | v2 digest 的字面见证（伪造合同与真实 compiled root）、`layout` 的嵌套拒绝 |
| `tests/test_execution_api_queries.py` | 只删 `(5, 1, 5, 1)` 字面锁 |
