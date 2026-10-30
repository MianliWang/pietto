# Phase71 Slice07：递归 ResultContract、可移植闭合 schema、层级意义与 digest 规则

状态：定稿。S07-A（类型、白名单、v2 闭合 schema、读者拒绝）与 S07-B（真实嵌套 plan 上的 build/verify
嵌套分支、writer 的 v2 投影、correspondence 的嵌套比较、真实合同上的源码根 digest）都在本片。
决定来源：S07 Gate 1 记录（ARCHITECTURE_DECISION，所有者 2026-10-27 接受 B2 推荐；
`/home/mianliwang/.local/state/pietto/evidence/pietto-phase71-20261026/claude-takeover-20261027/b2-records/S07-GATE1.md`）。
本片属于批次 B2，建立在 [S06](slice-06.md) 之上；B2 建立在 `0.1.6` 的发行提交 `bdb3f567` 之上，不属于 `0.1.6`，
其发布规则见[路线](slices.md)，发布之前本片是 candidate。
本文件是 S08–S19 读取的私有格式与交接规则；私有格式不进 `docs/spec/`，没有公开输出变化。

## 1. 层级意义

| 层 | 值 | 含义 |
| --- | --- | --- |
| 顶层行 | 一个父 occurrence | multiplicity 为 bag；顺序只由外层 `order by` 决定（`contract.ordering`） |
| 容器 | `None` | 容器不存在。只在容器 nullability 不是 NON_NULL 时可能出现（S16 透传，例如普通 LEFT JOIN 未匹配）；直接 Collect 的容器恒为 NON_NULL |
| 容器 | `[]` | 子关系完成后零行；不是 `None` |
| 容器 | `[r1, r2, …]` | 子关系完成后的全部行，保留 bag 重复。序列顺序 = 被收集 let 的 ORDER 键序；键上并列的行不承诺顺序，LIMIT 末位取哪一行也不承诺（D71.03）。隐藏排序键只出现在 `element.ordering`，不进子字段 |
| 元素 | 一条记录 | 一个真实子 occurrence，永不为 None；`{v: None}` 是一条真实记录 |
| 子 leaf | 标量 | 自身的 nullability 与意义（Timestamp/UUID 按 scalar meaning）。字段名是展示，不是身份；身份是 ordinal、port 与 identity |

合同与数据无关：零行、零 batch、空子表都携带完整合同（D71.06）。

## 2. 运行时类型

```text
ScalarShape(declared, canonical)                       # 不变
NestedShape(frozen, slots, eq=False)
  collect       S06 的 Collect 记录（经端口血缘得到的唯一来源）
  owner         被 collect 的 let 的 entry.owner（带 let_position）
  output        该 entry 的 active_output
  multiplicity  该 entry 的 active_properties.multiplicity，必须是 BAG
  ordering      该 entry 的 active_properties.ordering，必须非 None（D71.03）
  fields        tuple[ResultField, ...]，每个子字段的 shape 都是 ScalarShape（深度 1）
ResultField.shape: ScalarShape | NestedShape
```

嵌套字段：`ordinal`、`label`、`port` 与顶层标量字段相同；`nullability` 是
`port.field.effective_nullability`（容器 nullability）；`provenance` 是 `evidence.provenance`；`meaning` 为 None。
子字段：`ordinal` 是子位置，`label` 是子端口 `identity.name`，`port` 是子导出端口，
shape 是 `ScalarShape(field_def.type_expr 或 None, resolved_type)`，nullability、provenance 取子端口自己的，
meaning 取 `_output_entry(scalar_meaning, 子端口)`。

标量判定是白名单 `_SCALAR_KINDS = {BUILTIN, TYPE_ALIAS, ENUM}`：

- build：白名单内是标量 leaf；`NESTED_RELATION` 且授权是 `ProjectSQLPlanVerification` 走嵌套分支（S07-B）；
  其他一律 `SCALAR_UNAVAILABLE`。compiled 授权下的嵌套端口在 S09 之前因此得到 `SCALAR_UNAVAILABLE`。
- verify：同样划分；标量端口配 `NestedShape`、嵌套端口配 `ScalarShape` 都报 `FIELD`。
- 子字段：白名单是标量；嵌套报 `NESTED_DEPTH`（build）/ `FIELD`（verify）；其他报 `SCALAR_UNAVAILABLE` / `FIELD`。

嵌套分支只读一条来源：S06 的 `collect_of(plan, port.ref)` 给出唯一的 Collect 记录，它的 `producer` 给出唯一的
plan definition（entry 与 exports）。build 要求：

- `collect.children` 与 `definition.exports` 同序同对象；S04 描述符的 `element_fields` 与这些子端口字段数相同，
  逐个 `identity` 与 effective nullability 相同；
- 元素 owner 的 `let_position` 是 int，且不是表函数输入或 Unnest occurrence；multiplicity 是 BAG。

以上任一不成立报 `NESTED_ELEMENT`；被收集 let 的 ordering 为 None 是不变式违反，报 `NESTED_ORDER`；
子 Timestamp/UUID 找不到 meaning 报 `MEANING_UNAVAILABLE`，不产出缺意义的合同。verify 用同一来源逐个
`is` 比较，任一不符（含上述类别）都报 `FIELD`。

## 3. `pietto.result-contract.v2`

v2 只在合同至少含一个嵌套字段时使用；全平面合同继续写 `pietto.result-contract.v1`，字节与 digest 不变。
解码器按 format 分派：v2 文档没有嵌套字段报 `VERSION`；v1 文档出现嵌套 leaf 时键集合不符，报 `DOCUMENT`；
只认 v1 的旧读者遇到 v2 报 `VERSION`。

**顶层**：键集合与 v1 相同（`format owner output field_count fields types multiplicity ordering`，可选
`scalar_meaning`），按 v1 规则校验。`fields` 的每个元素恰好是一个 v1 标量 leaf，或一个嵌套 leaf。
leaf 带 `element` 键时按嵌套 leaf 校验。

**嵌套 leaf**：键集合 `ordinal label identity port output position kind element nullability
declared_nullability role provenance`。

- `ordinal`、`label`、`identity`、`port`、`output`、`position` 同 v1 顶层 leaf；
- `kind == "collection"`；`nullability`、`declared_nullability` ∈ {non_null, nullable, unknown}；
  `role == "ordinary_row_value"`；`provenance` 按 v1 规则；
- 不允许 `declared`、`canonical`、`type_resolution`、`meaning`。

**let_owner**：`identity module_position declaration_position let_position`；identity 是 namespace
`relation`、kind `query` 的 nominal，三个位置都是 index。只在 `element` 内使用：`element.owner`、
`element.output.owner`、`element.ordering.owner` 与每个子 leaf 的 `identity.owner`。顶层、types、provenance
与 origin 中的 owner 保持 v1 形状。let_owner 不要求与顶层 owner 同一声明，所以 S16 透传不需要换版本。

let occurrence 的身份是 `ProjectDeclarationOccurrenceIdentity` 的六个部分：identity、module_position、
declaration_position、let_position、`table_function` 与 `unnest_position`（S05）。表函数输入 occurrence 与它所在的
let 有相同的三个位置，只差 `table_function` 与展示名；Unnest occurrence 的 `let_position` 为 null，由
`unnest_position` 定位。元素 owner 永远不是表函数输入或 Unnest：S03 的 `_is_local_let` 要求 `let_position`
非 null 且不是 `table_function` 目标，所以 let_owner 不写这两个对 let 恒为空的部分。S07-B build 读元素 owner 的
occurrence（`entry.owner`，`ProjectDeclarationOccurrence`），要求 `table_function is None` 且
`unnest_position is None`，否则按不变式违反报 `NESTED_ELEMENT`；放开表函数输入或 Unnest 元素的那一片必须同时给
let_owner 加对应部分并换版本。

**element**：键集合 `owner output multiplicity nullability ordering field_count fields`。

- `owner` 是 let_owner；`output` 是 `relation_output`，其 owner 等于 `element.owner`；
- `multiplicity == "bag"`、`nullability == "non_null"` 是由版本固定的常量，放宽必须换版本；
- `ordering` 非 null，键与 v1 顶层 ordering 相同，`owner == element.owner`；
- `field_count ≥ 1`，且 `field_count == len(fields) == output.field_count`；
- `fields` 的每个元素恰好是一个 v1 标量 leaf：`identity.owner == element.owner`，
  `identity.position == ordinal == position`，`output == element.output`；`port.owner` 在全部子 leaf 中相同；
  Timestamp/UUID 子 leaf 的 `meaning` 规则同 v1。子 leaf 再嵌套时键集合不符。

**全局**：

- 一个 let 只有一个 element。同一 let（按 let_owner 的三个位置识别）被收集多次时，每个嵌套 leaf 都带同一个
  element 记录，规范 JSON 逐字节相同；只校验第一次，之后的只比较。依据：一个 let 只有一个 plan definition、一个
  active output 和一个 plan order（Gate 1 的 I-S06-1、I-S06-4），所以第二次 Collect 的子 export 端口就是第一次的。
  S04 接受同一个 let 被收集两次；S06 若偏离 I-S06-1/I-S06-4，先修订本条。
- 关系自己的坐标只属于一个关系 owner（顶层 owner 或某个 let_owner）：leaf 的 `port.owner`（definition）、
  关系 output 的 `position`（relation_output）与 ordering 的 `prepared.order`（relation_order）。所以子 leaf 的
  definition 不能是顶层的，两个不同 let 也不能共用 definition、output 或 order。
- export 坐标在整个文档中互不相同；同一 let 的重复 element 只比较，它的子 export 不再计入。
- 其余跨关系一致性（order item、表达式、use 与端口 producer 坐标）不由闭合 schema 核对，由 S07-B 的
  correspondence 对照 plan 核对。
- 顶层加子 leaf 的总数不超过 `DocumentLimits.fields`（1024），重复 element 的子 leaf 也计入；
  writer 端按同一总数检查；
- `types` 按文档遍历序的首次出现编号：顶层字段按序（嵌套字段内先子字段，再 `element.ordering`），
  最后是顶层 ordering；
- `DocumentLimits` 的数值、规范 JSON 编码与 `decode_contract`/`reencode_contract` 的接口都不变。

**私有类别**：

| 类别 | 情形 |
| --- | --- |
| `VERSION` | 未知 format；v2 文档没有嵌套 leaf |
| `DOCUMENT` | 键集合不符（含 v1 中的嵌套 leaf、子 leaf 再嵌套、嵌套 leaf 带 canonical/declared/meaning）；element 常量、ordering 为 null、role、let identity 的 namespace/kind；element 字段数不一致或为 0；关系的 output owner 或 ordering owner 不等于该关系 owner（顶层与 element 同一规则，同 v1） |
| `TAG` | 嵌套 leaf 的 `kind` 不是 `collection` |
| `REFERENCE` | leaf 的 identity owner、output 或 position 不对应其关系（顶层与子 leaf 同一规则，同 v1）；export 坐标重复；子 port owner 不一致；关系自己的坐标属于两个关系；同一 let 的 element 不同；meaning 配对；types 不可达或乱序 |
| `INDEX` | ordinal 不等于其位置；ordinal、position 或 let_position 不是 index（null、字符串或 bool） |
| `NUMBER` | 负整数或非整数的数（字节预检，先于任何 schema 规则；直接编码 dict 时非整数的数报 `DOCUMENT`） |
| `LIMIT` | 顶层加子 leaf 的总数超过预算 |

相对 Gate 1 §6：Gate 1 把 owner、output、坐标的对应错误都归 `REFERENCE`，把位置错归 `INDEX`。S07 改为在每个
结构位置沿用 v1 在同一位置的类别，平面文档的类别因此一个不变：关系头部的 owner 对应（output owner、ordering
owner）是 `DOCUMENT`，leaf 对其关系的对应是 `REFERENCE`；负整数在共享的字节预检中报 `NUMBER`，所以负的
let_position 报 `NUMBER`，不报 `INDEX`。lead 在 Gate 2 记录中登记这一偏离。

v2 文档不写 `<nested relation>`，也不写 `nested_relation`。

## 4. digest

### 4.1 源码根（S07）

`contract_digest(c) = SHA-256(export_result_contract(c, c.authority).canonical_bytes)`，代码路径不变。
平面合同写 v1 字节，digest 不变；嵌套合同写 v2 字节。v2 字节覆盖：

- 元素 owner（含 let_position）与元素 output；
- 子字段的顺序、identity、port 坐标与 label；declared type 及其参数、canonical 与 type_resolution/origins；
  nullability、declared_nullability、provenance；子 meaning 索引及其 `scalar_meaning` 法则；
- 元素 ordering：表达式、方向与 prepared uses，含隐藏键的表达式与端口；
- 容器 nullability 与容器 provenance；由版本固定的常量 bag、non_null。

按设计不覆盖：carrier、物理列、LIMIT/WHERE/查询文本（同 v1 顶层）、数据。

### 4.2 compiled 根（S07 写定，S09 实现）

平面继续用 `pietto.compiled-result-contract.v1`，原文不变。含嵌套时：

```text
{"fields": [entry, ...],
 "format": "pietto.compiled-result-contract.v2",
 "multiplicity": contract.multiplicity.value,
 "pin": root.expected_pin,
 "query": _wire(root.description.query)}
标量 entry = [ordinal, label, kind, name, nullability, meaning]      # 与 v1 相同
嵌套 entry = [ordinal, label, "collection", container_nullability, [子标量 entry, ...]]
编码：json.dumps(ensure_ascii=True, sort_keys=True, separators=(",", ":"))，ASCII 字节
```

只在至少有一个嵌套 entry 时用 v2。元素 owner、元素 ordering（含隐藏键）、子字段到来源的绑定与 LIMIT，
都由 `pin` 与 `query` 绑定，与 v1 顶层 ordering 的处理一致。S09 验收必须证明：只改子排序键、只换被收集的 let、
只改子 LIMIT，都会改变 pin，从而改变 digest；某项不在 pinned records 中时，S09 把它加进 compiled records，
不加进 digest JSON。

### 4.3 持久化、IPC 与跨版本

- 保存的 job 记录只存 digest 的十六进制字符串；嵌套 digest 只是另一个字符串，继续复用
  `pietto.job-workspace.v7`（D71.06）。
- IPC 头的 100 字节布局不变，合同槽仍是 32 字节原始 digest；嵌套帧归 S17。`layout` 不是 digest，本期对嵌套拒绝。
- compiled bundle 绑定代码身份，新代码本来就拒绝旧 bundle（`PIE-R1005`），所以 digest 的跨版本稳定性不是要求。
  旧运行时遇到嵌套产物：源码文档在 format 处得到 `VERSION`；compiled 在代码身份或版本处被拒（S09/S18）。
- digest 表达完整性与合同身份，不是认证。

## 5. Arrow 映射（S10 实现）

```text
pa.field(label,
         pa.list_(pa.field("item", pa.struct([子字段...]), nullable=False)),
         nullable=<容器 nullability 不是 NON_NULL>)
```

- 32 位 offset：用 `pa.list_`，不用 `large_list`（与 IPC 的 `allow_64bit=False` 一致；S02 每次执行最多
  1,048,576 个子行）。
- item 恒有效，因为元素永不为 None。
- 子字段：名字是子 label，只作展示；顺序按子 ordinal；类型、宽度请求与 nullable 沿用现有八类标量规则，
  宽度请求的具体形状由 S10 定。

## 6. 仍是平面的读者与交接规则

`scalar_fields(contract)`（`project_result_contract.py`）：每个字段的 shape 都是精确的 `ScalarShape` 时返回
`contract.shape.fields`（同一个 tuple），否则报 `ResultError("NESTED_UNAVAILABLE")`。它在三个汇合点替换
对 `contract.shape.fields` 的读取，或在读取之前先拒绝，都位于该读者已有的权威核对之后：

| 汇合点 | 位置 | 由谁打开 |
| --- | --- | --- |
| output | `_prepare_output`；`verify_output` | S08 |
| binding | `_columns`（共享检查）；`bind_producer`；`verify_producer_binding` | S10 |
| compiled digest | `contract_digest` 的 compiled 分支 | S09 |

其余读者都先经过其中之一：`bind_arrow` 等经 binding；`describe_compiled_binding` 经 `_prepare_output`；
`layout` 经 `_prepare_output` 与 compiled digest；`decode_native_rows`/`_bind_output` 经 `verify_output`；
`ExecutionPayloads` 经 binding。S07 不改原生执行族输入闭包中的文件。

`prepare_execution` 的 `postgres_rows` 路径没有 output 时直接调用 `build_result_contract`，不经
`_prepare_output`（`project_execution.py`）。它在连接前经 `verify_execution_request` 调 binding 的共享检查
`_columns`；`bind_native_projection` 也调 `_columns`。所以 binding 汇合点包括 `_columns`：它在
`verify_result_contract` 与 scalar meaning 核对之后调 `scalar_fields`。S07-B 为源码授权打开
`verify_result_contract` 之后，这条路径仍在连接前显式报 `NESTED_UNAVAILABLE`，不依赖非 `SQLColumn` 的
`PRODUCER_UNSUPPORTED` 或全 Int 实现规则这类偶然拒绝。

`verify_contract_correspondence` 先显式比较 `format`：plan exports 中有嵌套端口时期望 v2，否则期望 v1；
不符报 `CORRESPONDENCE`，不靠缺失的键。嵌套 leaf 的 element 不读合同的 `NestedShape`：它从 S06 的 Collect
记录与 S04 描述符独立枚举子端口，再按 let_owner 比较子 leaf，最后比较 element ordering 与该 let 的 plan order。
合同只提供子 leaf 的 meaning，与顶层 leaf 相同。

**交接规则**：谁打开一个汇合点，谁就在同一片中把显式拒绝下移到仍未打开的下游读者。

- S08 打开 `_prepare_output` 时，给 `describe_compiled_binding` 与 `layout` 加判定，或保证它们拿不到嵌套 output；
- S10 打开 binding（`_columns`、`bind_producer`、`verify_producer_binding`）时，同一片中打开或显式拒绝
  `prepare_execution` 的 `postgres_rows` 无 output 路径与 `bind_native_projection`（Gate 1 §12）；
- S09 打开 compiled digest 时，保证 `layout` 显式拒绝。compiled 分支的 `scalar_fields` 已由
  `tests/test_results_nested_relations.py` 在放行的授权下驱动；S09 打开时改写这个见证，不删除；
- S20 复核 R2/sink 的 `layout` 对嵌套的拒绝。

## 7. 合同不包含的内容

- carrier（S02 的 `pg_column_arrays_v1` 属于 producer/binding，归 S08/S10）；
- 物理列（一个嵌套字段对应 1+F 个物理列）；
- 元素 nullability 字段：本期由 v2 的封闭常量 `"non_null"` 表达；
- LIMIT、WHERE 与查询文本：compiled 根由 `pin` 与 `query` 绑定；S06 的 Collect 记录保留 `limit`；
- Arrow 类型。

子 schema 已提供 S02 carrier descriptor 所需的全部输入：有序子 occurrence（ordinal/port）、leaf 域
（declared type 及其参数、canonical）、每层 nullability。

## 8. 上游接口（S07-B 的前提）

| 编号 | 接口 |
| --- | --- |
| I-S04-1 | `ProjectResolvedTypeKind.NESTED_RELATION`；`ProjectResolvedType.nested` 是精确的 `ProjectNestedRelationType(element_relation, element_fields, collection_depth == 1)` |
| I-S04-2 | Collect 输出 `ProjectRowField`：NON_NULL，`field_def=None`，provenance 为 `DERIVED_EXPRESSION @ collect span`，role 为 `ORDINARY_ROW_VALUE` |
| I-S04-3 | PIE-S2804 已落地；S07 只把 ordering 为 None 当作不变式违反（`NESTED_ORDER`） |
| I-S04-4 | 子 leaf 只有八类 builtin；alias 叶的 canonical 是 builtin，`field_def` 保留 |
| I-S04-5 | `element_relation is` 被收集 let 的 IR `entry.owner`；子端口的 `field.evidence is element_fields[i]`（实现时核实） |
| I-S06-1 | plan 上的 Collect 记录：精确的父导出端口、producer definition、`children` 与 `producer.exports` 同序同对象、非 None 的 order ref、limit 与 capture ref |
| I-S06-2 | 端口血缘 helper：从嵌套端口找到唯一的 Collect，没有或不唯一时报错，不选赢家 |
| I-S06-3 | 嵌套导出端口在 `plan.exports` 中，并通过独立 plan 验证 |
| I-S06-4 | producer entry：`find_owner(entry.owner) == (entry,)`；ordering 非 None；multiplicity 为 BAG；`plan.orders` 中恰有 1 个 `source.owner is entry.owner` |
| I-S06-5 | 子端口：`field.output is entry.active_output`；`identity.owner.let_position` 是 int |
| I-S06-6 | `_output_entry(bundle, 子端口)` 能找到子 Timestamp/UUID 的来源；做不到时 build 报 `MEANING_UNAVAILABLE`（实现时核实） |
| I-S06-7 | producer let 及其来源在 plan closure 内 |

G2 的位置由 S06 Gate 1 决定，最晚在 S08 公开发射之前；S07 的读者拒绝在 G2 的任何位置下都成立。

实现时核实（S07-B）：

- I-S04-5 前半不成立：`element_relation` 是值相等的 `ProjectDeclarationOccurrenceIdentity`，被收集 let 的
  `entry.owner` 是 `ProjectDeclarationOccurrence`，不是同一对象。后半也只对直接投影的 producer 成立：
  DISTINCT 与 QUALIFY 的 producer 在完成时重建行，子端口的 field evidence 不是描述符中的对象，窗口结果字段的
  provenance symbol 也不同。按 Gate 1 的备选，build、verify 与 correspondence 都以 Collect 记录的 `children`
  （`is`）为准，再用描述符的字段数、`identity` 与 effective nullability 交叉核对；合同的子 provenance 取 plan
  子端口自己的。
- I-S06-1 的形状：Collect 记录的 `export`、`producer`、`children` 是 plan ref；order 与 limit 由
  `collect_order`、`collect_limit` 提供（S06 Gate 1 D-S06-3）。合同不读 LIMIT；元素 ordering 是 entry 的
  `active_properties.ordering`，writer 与 correspondence 都在 `plan.orders` 中找 `source.owner is entry.owner`
  的唯一 order，与 `collect_order` 同一规则。
- I-S06-2 即 `collect_of`；I-S06-6 只对直接投影的子 Timestamp/UUID 成立：它们经 `_output_entry` 找到唯一来源。
  派生的子 Timestamp/UUID（如 `coalesce`、聚合或窗口结果）在 `_output_entry` 报 `MEANING_OUTPUT`，build 报
  `MEANING_UNAVAILABLE`，与顶层同类表达式在 HEAD 上的 `MEANING_OUTPUT` 是同一限制，不是回归；按 Gate 1，
  修 `_output_entry` 仍归 S15。

## 9. 附带修复（F-S07-1）

pure 校验接受 writer 一直在写的 `conditional`（`when_true condition when_false location`）、`membership`
（`value options negated location`）与 `cast`（`value target location`，target 按 `declared` 规则且非 null）
三个表达式标签，各按 writer 的键集合闭合校验。此前用条件、`in` 或 `Float(...)` 作排序键，或在类型 `ensure`
中使用它们的程序在导出时得到 `DOCUMENT_TAG`；v2 元素 ordering 复用同一 codec，所以被收集的 let 也受影响。
所有原本可导出的 v1 文档字节不变。

这是 Gate 1 §14 待办 1 推荐的处置（AC-18），在 S07 修复账中计 1 个 causal；lead 在 Gate 2 记录中登记采纳。

同一根因的另一处（S07B-CONTRACT-R2-1）：writer 不写入口查询头部参数的读取（`ParameterRefExpr`），所以排序键读参数的
程序（如 `query result(p: Int)` 中 `order by orders.total * p, id`，顶层或被收集的 let）能 build 与 verify，导出与源码根
digest 却得到 `DOCUMENT_TAG`。现在 writer 与 pure 校验都有闭合的 `parameter` 标签（`name ordinal type_name nullability
location`；`ordinal` 按 index 规则，`type_name` 只能是 `Bool`、`Int`、`Float`、`Text`，`nullability` 只能是 `nullable`
或 `not_null`，与语义对头部参数的准入相同），correspondence 对照 AST 逐项比较这五项。至此 codec 覆盖排序键能写的全部
表达式：排序键中的 ANY（PIE-S2334）、`scalar`/`exists`/`in` 关系读（PIE-S2348、PIE-S2349、PIE-S2350）、被捕获字段
（PIE-S2370）、窗口（解析错误）与 Collect 输出（PIE-S2805）都已在语义或解析时拒绝。lead 在 Gate 2 记录中一并登记。

兼容性：同一个 format 名 `pietto.result-contract.v1` 下的文法变宽了，只增加了 writer 一直在写的三个标签与
新写的 `parameter`。S07 之前的 pure 解码器读到这些新可导出的 v1 文档时报 `TAG`，不是 `VERSION`，仍然失败关闭。这些文档是私有的、不持久化：
job 记录只存 digest 的十六进制字符串；公开执行走 compiled digest 分支，不经 pure 解码器。所以没有公开变化。

## 10. 在 `0.1.6` 上重放

本片的 delta 先接在 MySQL parity 树上的 S06 树上，得到 `76ba8c3f`。`0.1.6` 发行后，本提交把同一 delta
（`e1ec73f2..76ba8c3f`）以 `git apply --3way` 重放到发行提交上的 S06 树：代码、测试与本文件全部干净应用，唯一冲突是
`docs/status.md` 的 Phase71 行，S07 的链接加在 `0.1.6` 已发行、B2 为其上候选批次的文字中。
