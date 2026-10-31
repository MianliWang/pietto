# Phase71 Slice10：嵌套结果的 producer/Arrow binding、owned 构造、递归验证与 children/bytes 计量

状态：candidate（批次 B3），S10 定稿（S10-A 与 S10-B，同一笔提交）。D71.11 的 native 运行由封存阶段在确切的 candidate wheel 上进行
（第 10 节）。
决定来源：S10 Gate 1 记录（ARCHITECTURE_DECISION，D-S10-1 至 D-S10-12），以及 S08 Gate 1 的 D-S08-7（output 视图与
carrier descriptor 归 S10）。
本片建立在 [S09](slice-09.md) 之上；批次 B3 建立在 main 的 `81f0d3b5` 之上，其发布规则见[路线](slices.md)，发布之前本片是 candidate。
本文件是私有格式与交接规则；不进 `docs/spec/`，没有公开 JSON、CLI、SQL 或诊断变化，`pietto` 没有新名字。

## 1. 交付

S10-A（result/Arrow owner）：

| 文件 | 内容 |
| --- | --- |
| `project_result_binding.py` | `ProducerNestedBinding`；`ProducerResultBinding.fields` 的注解；逐 leaf 定律抽成 `_verify_leaf`（平面行为等价），存储表抽成 `_storages` |
| `project_arrow_result.py` | `MAX_CHILD_ROWS`；子 leaf 白名单；嵌套 Arrow 类型与字段级相等；请求拒绝；owned 列式构造；递归验证；A/R/C 计量 |
| `project_result_reader.py` | `_roots` 递归；reader 的 `NESTED_UNAVAILABLE` guard |
| `project_arrow_interop.py` | `_copy_batch` 的 `NESTED_UNAVAILABLE` guard |
| `project_execution_reader.py` | 只在 `decode_native_rows`（ADBC/MySQL 行）对非 `ProducerFieldBinding` 报 `NESTED_UNAVAILABLE`：`fields` 注解变宽后的类型收窄，平面行为不变；其余改动归 S10-B |

相对 Gate 1 §6 写集（lead 在 Gate 2 记录中登记）：
- `project_execution_reader.py` 在 Gate 1 中只属于 S10-B；上表这处收窄是 `fields` 注解变宽后 pyright 的必需改动。
- 同一注解变宽使 tests 的 pyright 在读 `.observation` 的既有平面用例上失败；`tests/test_execution_adbc.py`、
  `test_execution_outputs.py`、`test_execution_refinement.py` 只加类型收窄，运行时行为不变。
- AC-01 的数据模型测试放在 binding owner `tests/test_results_contract.py`，不放 `test_results_reader.py`（它不观察
  reader）。
- `scripts/phase68_executor_premise.py` 的 `HELPERS` 加入 `_pietto_results_nested`：product helper 在导入时加载它，
  premise 的 `input_identity()` 必须绑定它的字节。

S10-B（在 S08、S09 冻结树上）：

| 文件 | 内容 |
| --- | --- |
| `project_result_output.py` | D-S08-7：`NestedOutputColumn`（carrier descriptor）；`_prepare_output`/`verify_output` 对嵌套字段打开（第 7 节）；guarded output 与 `source_read_columns` 显式拒绝 |
| `project_result_binding.py` | `_columns` 的分派（第 7 节）；`bind_producer` 的嵌套分支（observation 为 `(count, children)`）；`verify_producer_binding` 的嵌套分支 `_verify_nested`；`MAX_CHILD_ROWS` 与子 leaf 白名单 `CHILD_KINDS` 移到这里（binding 验证要用；`project_arrow_result` 重新导出） |
| `project_execution_reader.py` | `_bind_output` 展开 1+F 物理列并检查 route；`_nested_observation`（OID 表）；共用的 `_observation`；严格 decoder `decode_carrier_rows`；`ExecutionPayloads` 先解码、再计子行；`bind_stored_output` 共用同一分支 |
| `project_execution_postgres.py` | `_read`：嵌套尝试的 loader 异常映射（第 9 节） |

`project_execution_template.py`、`project_execution.py`、`project_result_ipc.py`、`project_refinement*.py` 与
`project_guard_*.py` 不改：它们读到的嵌套 output 都先经过上面的显式拒绝（第 7 节）。

**测试缝（AC-11）**：installed product consumer 的 S10 七组（`tests/_pietto_results_nested.py`）全部改用真实
producer：真实 VERIFIED 的 PostgreSQL Collect（S08）、它的 output 与 descriptor（本片），以及 rows reader 按
psycopg 形状的 description 做的真实 binding（`collected`、`metadata`、`real`）。只有可空容器的部分保留唯一的测试缝
`project_arrow_result.verify_producer_binding`，到 S16 为止：直接 Collect 的容器恒为 NON_NULL，S16 之前没有真实上游
能产生可空容器；保留这个缝的三组（`nested_arrow_type`、`nested_owned_values`、`nested_verification`）在
`authority` 中记录不替换时入口的类别 `FIELD`。S11 的组仍用 S10-A 的合成 producer（`nested`、`admitted`），由 S11-B
改写。

## 2. 数据模型

```text
ProducerNestedBinding(frozen, slots, eq=False)
  field      顶层嵌套 ResultField（shape 是 NestedShape）
  column     S08 的嵌套 output column（S10-B 起由真实 output 提供）
  count      ProducerObservation(storage="pg_int8", domain="child_count",
                                 lower=0, upper=MAX_CHILD_ROWS, carrier="int")
  children   tuple[ProducerFieldBinding, ...]   # 每个子字段一个，与 NestedShape.fields 逐一同一
  nullable   容器 nullability 不是 NON_NULL
ProducerResultBinding.fields: tuple[ProducerFieldBinding | ProducerNestedBinding, ...]
MAX_CHILD_ROWS = 1 << 20     # project_result_binding 的模块常量（project_arrow_result 重新导出）；D71.07/S02，不是调用方参数
```

carrier descriptor 是 output 的 `NestedOutputColumn`（D-S08-7 起归 S10），binding 的 `column` 以身份引用它：

```text
NestedOutputColumn(frozen, slots, eq=False)
  original   语句的 CollectColumn，或父关系结果体携带它的 ResultGroupColumn
  field      顶层嵌套 ResultField；export 是它的端口
  ordinal, label
  terminal   语句的最终单元
  carrier    "pg_column_arrays_v1"
  aliases    1+F 个物理列名：count，然后每个子字段一个 array（语句自己的别名，按位置）
  children   被收集终端的输出（OutputColumn），每个子 leaf 一个；realization 与 source_field 是终端列自己的
```

`verify_output` 从语句的 Collect 列与被收集终端独立重推：Collect 记录 `is` `NestedShape.collect`；carrier 的
subject 依次 `is` 端口与 `collect.children`；aliases 等于 carrier 标签；每个子项的原列是 `ResultColumn`，`export`
`is` 子 leaf 的端口，realization `is` 终端列的 realization。违反分别报 `OUTPUT_COLUMNS`、`OUTPUT_CARRIER`、
`OUTPUT_REALIZATION`。目标族不是 PostgreSQL 时报 `OUTPUT_CARRIER`。compiled artifact 上重算的 descriptor 与 live 相同
（S08 F-12，见 `test_the_compiled_descriptor_equals_the_live_one`）。

nested binding 的验证（`_verify_nested`）：`bound.column is` 该 descriptor；子 leaf 不在 `CHILD_KINDS`（Int、Bool、
Text）内报 `PRODUCER_UNSUPPORTED`；count observation 必须恰为
`(ordinal, label, family, "pg_int8", 0, MAX_CHILD_ROWS, "child_count", "int")`，类型逐项精确，其余可选项为 None，
`protocol_nullable` 只能是 None 或 bool；容器 nullability 不是 NON_NULL 时 `nullable` 为 True。以上违反报
`PRODUCER_OBSERVATION`。每个子项按顶层标量同一个逐 leaf 定律 `_verify_leaf` 检查（general 规则，ordinal 是子
ordinal）；子项的身份或对应不符报 `PRODUCER_FIELDS`。

Arrow owner 的结构判定 `_children(bound)`：标量字段必须是 `ProducerFieldBinding` 且 shape 是 `ScalarShape`，
否则 `PRODUCER_FIELDS`；嵌套字段要求 `NestedShape`、非空 children tuple、`child.field is shape.fields[k]`、子 shape
是 `ScalarShape`、nullable 是 bool、子 label 唯一（struct 值按 label 成键，重复会丢值），否则 `PRODUCER_FIELDS`；
子 leaf 不在白名单 `Int`、`Bool`、`Text` 内时报 `PRODUCER_UNSUPPORTED`。S14、S15 只扩大白名单。

## 3. Arrow 映射

```text
pa.field(label,
         pa.list_(pa.field("item", pa.struct([pa.field(child.label, child_type, nullable=child.nullable), ...]),
                           nullable=False)),
         nullable=<容器 nullability 不是 NON_NULL>)
```

- 任何一层都不带元数据；item 恒名 `item` 且不可空；32 位 offset（`pa.list_`）。
- 子字段按子 ordinal；Int 宽度按 `INT_WIDTHS[storage]`（int16/int32/int64），Text 是 `pa.string()`。
- 字面例：`pyarrow.Field<c: list<item: struct<i: int64 not null, b: bool, t: string> not null> not null>`。
- 嵌套字段上没有宽度或表示请求：`integer_widths`、`text_offset_widths`、`decimal_widths`、`uuid_representations`
  的非 None 项报 `ARROW_ADAPTATION`，`field_labels` 的非 None 项报 `ARROW_LABELS`。以后增加是兼容变化。
- `verify_arrow_binding` 对嵌套字段用 `Field.equals(expected, check_metadata=True)`：PyArrow 26 的 `DataType ==`
  看不见 item 名（`element`）、item 元数据与子字段元数据；它的元数据比较又把 `{}` 当作没有元数据，所以字段、item
  与每个子字段还要求 `metadata is None`，与平面字段一致。平面字段的比较不变。

## 4. 逻辑嵌套值与 owned 构造

owned 构造的输入与 carrier 无关：

- `None`：容器不存在；只在容器可空时允许，否则 `NULL`；
- 否则是长度为 F 的 `tuple`，第 k 项是第 k 个子字段的值序列（`tuple` 或 `list`），各序列等长，长度就是子行数；
  `[]` 写作 F 个空序列。

拒绝（全部在任何 Arrow 分配之前）：容器不是 tuple、子序列不是 tuple/list 报 `VALUE_DOMAIN`；序列数不等于 F、
子序列不等长报 `ROW_ARITY`；子元素按平面 `_value` 规则检查（Int 越界、bool 冒充 Int、Text 超长或含 NUL、Bool
不是 bool、嵌套 list 元素报 `VALUE_DOMAIN`，非空子字段上的 None 报 `NULL`）。

构造顺序：先计入每个嵌套字段零子行时的固定部分（struct 与子字段 validity、Text 子字段的首个 offset），使构造前
的计量恰等于验证器的 A；每行再做全部值检查与计量（子行数先计入上限与固定 allowance，再逐元素检查值并累计 Text
字节，余量用尽即停）；之后每个子字段一次 `pa.array(..., from_pandas=False)`，`pa.StructArray.from_arrays`（不带
mask），`pa.ListArray.from_arrays(int32 offsets, struct, type=..., mask=...)`。offset 从 0 起；null 容器拥有空
segment；只有存在 null 容器时才传 mask；从不 `pa.array(nested_python)`。构造好的 batch 交给同一个
`_checked_batch_usage` 得到 usage，不信任构造过程。

`pg_column_arrays_v1` 的 count 与 array-NULL 规则只在 S10-B 的 decoder 中，由 decoder 转成上面的逻辑值。

## 5. 递归验证的顺序

1. `_dimensions(batch.num_columns, …)`、`_verify_schema`：身份只取自 `batch.schema`
   （`Schema.equals(check_metadata=True)`），不从列自己的类型推身份或 nullability。PyArrow 26 的
   `RecordBatch.from_arrays(schema=S)` 接受列类型只在 item 名或子元数据上不同的数组，并让 `batch.schema` 等于 S；
   这样的 batch 按 S 判定，值检查照常。
2. `_dimensions(N_fields, …)`：N_fields 是顶层字段加全部子字段。
3. 基础计费（平面字段，加嵌套字段的 list validity 与 offset）；递归 `buffers()` 求和得 R；`validate(full=True)`。
4. 长度为 0 的嵌套列：`C_j = 0`，不调用任何 list accessor。PyArrow 26 上 offsets buffer 不存在的零长度 list，
   `offsets.to_pylist()` 与 `flatten()` 会 segfault；product consumer 在子解释器中见证缺失与零大小两种 buffer。
5. 读 `o_0..o_P`；null 容器：字段不可空报 `NULL`，`o_{i+1} != o_i` 报 `ARROW_BATCH`（非规范形式）。
6. `values.slice(o_0, C_j)` 上 `null_count != 0` 报 `NULL`：`validate(full=True)` 不执行 item 的非空标志。
7. 子行上限与固定 allowance（struct validity、每个子 leaf 的 validity 与数据或 offset）。
8. 每个子 leaf `referenced.field(k)` 一次 `to_pylist()`，按平面逐值规则（`logical=True`）检查并累计 `T_k`；
   子字段的 nullability 由 `_value` 判定，Text 字节余量用尽即停。

引用区间外的子元素不做逐值检查，但计入 R。

相对 Gate 1 D-S10-5：第 7 步（上限与固定 allowance）放在逐值检查之前，与平面“先基础计费、再逐值”的顺序一致，
并让 Text 字节的提前停止用上完整余量；一个同时违反两类规则的 batch 因此先报 `LIMIT`。lead 在 Gate 2 记录中登记。

## 6. 计量

```text
A_nest(j) = ceil(P/8) + 4*(P+1) + ceil(C_j/8) + sum_k leaf(C_j, k)
leaf(n,k) = ceil(n/8) + 8n                 # Int/Bool
          | ceil(n/8) + 4(n+1) + T_k       # Text，32 位 offset
A = sum_flat + sum_j A_nest(j)
R = 每列递归 buffers() 中非 null buffer 的大小之和
C = sum_j C_j
```

| 层次 | 规则 |
| --- | --- |
| 每批 | `N_fields ≤ min(fields, 64)`；`A ≤ L`；`R ≤ L`；`C ≤ MAX_CHILD_ROWS`；每个 Text leaf `T_k < 2^31` |
| 每次执行（`ExecutionPayloads`，第 8 节） | 父行之和 ≤ `max_rows`（含义不变）；子行之和 ≤ `MAX_CHILD_ROWS`（分配前）；`max(A,R)` 之和加 guard/profile 字节 ≤ `max_bytes`（规则不变） |
| 平面 | 计费与错误逐字节不变 |

每批子行上限是真实约束，不被字节上限覆盖：一个父行、只有一个 Text 子字段且值为空串时，1,048,577 个子行的
A = 4,456,467 ≤ 8 MiB，仍报 `LIMIT`。一个父行放不进一批时整批失败，从不拆分，也不静默截断。

见证值（product consumer，期望值手算）：S12 边界（P = 64，C = 1,024，`(Int, Bool, Text 256 B)`，父 Int 非空）
A = 283,928、R = 275,336；64 个 `[]` A = 792、R = 776；恰好 1,048,576 个空串子行 A = 4,456,461、R = 4,194,316。

## 7. binding 汇合点与显式拒绝

`_columns` 的分派（D-S10-7）：

| 分支 | 处理 |
| --- | --- |
| 非 guarded 的 `output is not None` | 打开：返回 `verify_output` 的列，嵌套字段是 `NestedOutputColumn` |
| `output is None`（`prepare_execution` 的 `postgres_rows` 无 output 路径、SQLSelect 路径、`bind_native_projection`） | 保留 `scalar_fields`，报 `NESTED_UNAVAILABLE`，在任何连接之前 |
| guarded output | `verify_output` 在 guard 视图之前调 `scalar_fields`，报 `NESTED_UNAVAILABLE`（F-S10-2）；`_prepare_output(guarded=…)` 同样 |

output 打开后仍是平面的读者（S07 的交接规则：谁打开汇合点，谁就把拒绝下移）：

| 读者 | 拒绝 | 由谁打开 |
| --- | --- | --- |
| `source_read_columns`（R2 refinement 的 lowering 与验证、guard 验证） | `scalar_fields`，`NESTED_UNAVAILABLE` | S12/S20 |
| `describe_compiled_binding`、`compiled_output` | 不可达：每个 compiled binding 先经 S09 的模板闸门 `verify_template`（`NESTED_UNAVAILABLE`） | S12 |
| `project_job_delivery.layout`（保存与 R2/sink 的行布局） | S09 的 `scalar_fields`，`NESTED_UNAVAILABLE` | S18–S20 |
| `_bind_output` 的 route 不是 `postgres_rows` | `NESTED_UNAVAILABLE`（`postgres_adbc`；`mysql_rows` 在族核对处报 `EXECUTION_METADATA_ROUTE`），`decode_native_rows` 因此也拒绝 | 连接前拒绝归 S12/S20 |

私有的 `postgres_adbc` 嵌套请求（`prepare_execution(..., route="postgres_adbc")`）会先连接，再在 `_bind_output`
确定拒绝；不解码，也不分配 Arrow。公开路径在 S12 之前由 S09 的模板闸门挡住（`compile_query`/`load_bundle` 报
`PIE-R1004`）。D71.05 要求的连接前拒绝归 S12。

## 8. native descriptor 与严格 decoder（`pg_column_arrays_v1`）

每个嵌套字段占 1+F 个物理列，按逻辑字段顺序展开：count，然后每个子字段一个 array（子 ordinal 序）。每列只按位置
核对它在 descriptor 中的别名与 OID，从不用标签恢复子身份（S02 不变量 1）：

| 物理列 | OID | 打开 |
| --- | --- | --- |
| count（`int8`） | 20 | S10 |
| `pg_int2` / `pg_int4` / `pg_int8` 子字段 | 1005 / 1007 / 1016 | S10 |
| `pg_bool` 子字段 | 1000 | S10 |
| `pg_text` 子字段 | 1009 | S10 |
| 其余子存储 | — | S14、S15；在此之前 binding 报 `PRODUCER_UNSUPPORTED`：description 宽度与该字段之前的列先核对，该字段自身的 count 与 array 列不再核对 |

别名或 OID 不符、物理列缺少或多出报 `EXECUTION_METADATA`；`null_ok` 只作 protocol 证据。保存的 chunk
（`bind_stored_output`）没有 metadata，protocol nullability 为 None，schema 与 live binding 相同。

`decode_carrier_rows(producer, rows, children)`，每行、在任何 Arrow 分配之前：

1. 行是 tuple 或 list，长度等于物理列数，否则 `EXECUTION_METADATA`。
2. 标量字段原样传递（由 owned 构造检查）。
3. 嵌套字段：
   - count 为 None：容器不可空报 `NULL`；可空（S16）时每个 array 也必须是 None，否则 `EXECUTION_CARRIER`；
   - 否则 `type(count) is int` 且 `0 ≤ count ≤ MAX_CHILD_ROWS`（bool 不算 int），否则 `EXECUTION_CARRIER`；
   - count 为 0：每个 array 必须是 None（空集合是 0 与 NULL arrays，不是 `{}`），否则 `EXECUTION_CARRIER`；
   - count > 0：每个 array 的 `type is list` 且长度等于 count，否则 `EXECUTION_CARRIER`；
   - 子行累计超过本次执行余下的预算报 `EXECUTION_RESOURCE_LIMIT`（逐行检查，先于元素检查）；
   - 每个元素经平面标量规则 `_value` 检查：2 维元素、超出 observation 范围（含超出 int64）、bool 冒充 Int、
     Text 超过 `max_characters` 或含 NUL 报 `VALUE_DOMAIN`，非空子字段上的 None 报 `NULL`；
   - 输出第 4 节的逻辑嵌套值（count 为 0 时是 F 个空序列）。

owned 构造照常重新检查全部值（不信任 decoder）。psycopg 的 `bool[]` loader 把 `t` 以外的 token 读成 False，
`int8[]` 接受超出 int64 的值（Gate 1 q4）：Bool 的正确性依赖 OID 核对与服务器的规范输出，Int 依赖范围检查。

`ExecutionPayloads`：producer 有嵌套字段时 `nested` 为真，`accept` 先解码，传入执行级余量
`MAX_CHILD_ROWS - children`；父行仍只计入 `max_rows`；`children` 在批次交付后累加。超过时在该批的 Arrow 分配之前报
`EXECUTION_RESOURCE_LIMIT`。

## 9. driver loader 异常

`PostgresExecution._read`：只对 `_payloads.nested` 为真的尝试，捕获 `fetchmany` 的 `Exception`；带 `sqlstate` 的
异常（服务器状态）原样重抛；其余在 `except` 块之外抛 `ResultError("EXECUTION_CARRIER")`，所以 `__cause__` 与
`__context__` 都为 None，记录的失败只有 phase 与类名（`ExecutionFailure("read", "ResultError")`），不带 driver
文本（S02 不变量 5）。平面尝试不变（原异常与 `PIE-R3003` 分类照旧）。可达性：OID 在 fetch 之前已绑定，所以对规范的
服务器输出不可达；`server_encoding` 是 SQL_ASCII 时非 UTF-8 的 Text 字节可达，直到 S12 的 preflight 核对
`server_encoding`。

会话设置：S10 的叶子（Int、Bool、Text）依赖的文本输出设置只有 `client_encoding`，它已在连接 options 中固定并在打开
时回读核对，所以 S10 不新增固定。`standard_conforming_strings` 不影响 array 输出的转义（推断），由 D71.11 的 Text
引号用例核实。`extra_float_digits` 归 S14，`DateStyle` 归 S15。

## 10. guard、native 验收与交接

S10 自己的 guard（S11-A 的同批改动移除前两项）：

| guard | 位置 | 由谁移除 |
| --- | --- | --- |
| 嵌套 batch 到达 `_copy_batch`（`manage_batch`、`import_batch`、stream 交付） | `project_arrow_interop._copy_batch`，在 `from_buffers` 之前 | S11 |
| 嵌套 binding 打开 finite reader（同时挡住 `ingest_reader`、`import_stream`、`manage_stream`、`encode_ipc`、`open_ipc`；`open_ipc` 的 owned ingress 会关闭 source） | `CheckedFiniteReader.__init__`，在 binding 复核之后、source 类型检查之前 | S11 |
| route 不是 `postgres_rows` 的嵌套 output | `_bind_output` | 连接前拒绝归 S12/S20 |

`build_managed_batch` 不经 `_copy_batch`，所以 S10 不依赖 S11 就能交付 owned 嵌套 batch；它的 C 导出可以
`pa.record_batch` 往返且值相等。`project_result_ipc.py` 不改（S09 在那里实现 compiled digest v2）。在 S10 的提交中，
真实 producer 让 `encode_ipc` 经过 v2 digest 到达 reader guard，见证为 `NESTED_UNAVAILABLE`；`open_ipc` 的见证 envelope
带全零 contract digest，在 reader guard 之前报 `IPC_CONTRACT`。S11 移除 reader guard 时在 `_contract_digest` 中加的拒绝
让两者都报 `NESTED_UNAVAILABLE`。

**交接规则**：S11 移除 reader guard 时，必须在同一片中给 `encode_ipc`/`open_ipc` 的入口加显式拒绝，直到 S17。

**D71.11 native（封存阶段运行，本片没有运行）**：`docs/development.md` 要求在确切的 candidate wheel 上重跑
`tests/_pietto_execution_api_probe.py` 的 `consumer` 与 `postgres` 两族，以及依赖的 general-output rows campaign
（`tests/_pietto_execution_rows_probe.py campaign`）。本片在 rows campaign 中加了嵌套族：PostgreSQL 目标建
`"kids"` 表（`KIDS_TABLE`、`KIDS`，见 `tests/_pietto_execution_rows_cases.py`），`postgres_rows` 的 source 与 installed
两个 worker 都跑 `nested_cases`：captured、closed、父关系带 ORDER BY/LIMIT、Int4/Int2 子字段（OID 1007/1005），
每个按独立字面 oracle（`nested_expected`：父行为多重集，子行按 seq 的并列组，并列内顺序不承诺）核对提交的 SQL、
物理 description（OID 20、1016、1000、1009 等）、Arrow schema 与值；数据覆盖空集、全 NULL 子行、重复、并列、
Int64/Int32/Int16 极值、Text `,{}"\`、空串、字符串 `NULL` 与多字节字符；`batch_bytes=64` 的用例证明首批整批拒绝
（`LIMIT`，不拆分）。每批后记录 VmHWM，只作证据。执行级子行上限只做离线测试（native 需要上百万子行）。

同一 campaign 的平面 `bound_cases`（模板 `renamed = id + 1`）夹具已陈旧，由 B3 封存的 D71.11 运行发现，随本片
修复（只改探针，不改产品）：`8dcc610c` 起 `Int` 算术的证明用 storage 类型而不用声明的 `int_range`
（[project-package](../../project-package.md)），夹具把 `id` 声明为 `pg_int8`，`id + 1` 因此报 PIE-B1002
`arithmetic_outside_physical_range`；rows campaign 只在 native 运行，离线测试没有覆盖。模板现在读自己的
`"rows_pg_int4"` 表（`id INTEGER`，同样 5 行），`id` 声明为 `pg_int4`（`template(..., storage=)`，默认不变），
期望域改为 int4 范围加偏移；参数、行、5 个用例与两个控制终态不变，SQL 只换表名。平面与嵌套族仍读
`id BIGINT` 的 `"rows"`，嵌套族核对 OID 20，其发射与修复前逐字节相同。

| 片 | 从 S10 接手 |
| --- | --- |
| S11 | 移除 `_copy_batch` 与 reader 的 guard；同一片中给 IPC 入口加显式拒绝；reader 的每会话子行计数复用 `MAX_CHILD_ROWS`；`_pull` 的 `_dimensions(batch.num_columns, …)` 与 reader 打开时的 `_dimensions(len(source.schema), …)` 改用 N_fields；用于 copy 的规范零行；S11-B 把它的组改用本片的真实 producer（`real`） |
| S12 | 连接前拒绝 ADBC/MySQL/guarded/保存/R2/sink（D71.05）；来源上界 preflight（语句、`DataRow`/`D_batch`/`D_total` 算术与独立 verifier）并在同一只读事务中、主 SQL 之前运行，核对 `server_encoding`（D-S08-7 把语句与算术交给 S10，D-S10-10 交给 S08/S12；两片都没有交付，本文件按 S12 记，见 slice-02）；公开码与 detail；`pa.schema(handle)`；带子行的限制的公开文档；`source_read_columns` 与 guarded output 的嵌套打开 |
| S14、S15 | 扩大子 leaf 白名单 `CHILD_KINDS` 与 `PG_ARRAYS`；`extra_float_digits`、`DateStyle`；`_verify_schema` 的递归 UUID 扩展类检查；driver 异常的 native 见证 |
| S16 | 可空容器的真实正例（替换第 1 节保留的缝；decoder 的 count/array 同为 NULL 规则已就绪） |
| S17 | 移除 S11 加的 IPC 拒绝 |
| S18–S20 | 保存、R1、`verified_export` 与 R2/sink 的 `layout` 拒绝 |

## 11. 测试 owner

| owner | 内容 |
| --- | --- |
| `tests/_pietto_results_nested.py`（installed product consumer，Arrow） | 七组：类型（含 closed/ordered 同 schema、stored schema，AC-03/15）、binding 相等与请求、未打开子 leaf 在 binding 时拒绝（AC-04）、owned 值与按 psycopg 形状的 carrier 行解码后的真实值（`carrier`，AC-05/16）、构造前拒绝（AC-06）、计量（AC-07）、递归验证（AC-08）、guard（AC-10）；期望值都是手写字面值 |
| `tests/test_results_nested_relations.py` | 真实 descriptor 与 binding（captured、closed、父关系带结果边界）、description 损坏、route、未打开子 leaf、协调损坏、descriptor 损坏、仍是平面的读者的拒绝、compiled 与 live 的 descriptor 相同（AC-12、AC-15，Arrow-free）；S07 的 admitting-authority 见证改写为 output 打开后的 `OUTPUT_COLUMNS` |
| `tests/test_execution_outputs.py` | 严格 decoder 的接受与拒绝矩阵、可空容器规则、执行级子行计数在分配前（AC-13，Arrow-free） |
| `tests/test_execution_api_postgres_rows.py` | stub cursor 的 loader 异常：嵌套尝试不带 sentinel，平面不变，服务器状态原样（AC-14） |
| `tests/_pietto_execution_rows_cases.py`、`tests/_pietto_execution_rows_probe.py` | D71.11 的嵌套 native 族与独立字面 oracle（第 10 节） |

## 12. 相对 Gate 1 的偏离（lead 在 Gate 2 记录中登记）

- 写集：D-S08-7 把 output 视图与 descriptor 交给 S10，所以 S10 改了 Gate 1 §6 列为“不改”的
  `project_result_output.py`；descriptor 就是 output 的 `NestedOutputColumn`，没有另设 descriptor 类型。
- F-S10-2 的拒绝放在 `verify_output`（guarded output 的根），而不是只放在 `_columns` 的 guarded 分支：一处同时覆盖
  `_columns`、guard 验证与 `_prepare_output(guarded=…)`。
- `source_read_columns` 加 `scalar_fields`：output 打开后，R2 与 guard 的来源闭包是剩下的平面读者。
- decoder 也逐元素调用平面标量规则（Gate 1 把元素检查只放在构造中）：AC-13 因此不需要 Arrow，畸形 carrier 不会到达
  构造；构造仍然重查。执行级预算传进 decoder，逐行在元素检查之前截止。count 为 None 时先判容器 nullability。
- `MAX_CHILD_ROWS` 与白名单移到 `project_result_binding`（binding 验证需要；`project_arrow_result` 重新导出同名常量）。
- 未打开的 Date 子字段由 `date_of(<label>_at)` 派生：emission contract 不接受 Date 来源列。
- 产品 consumer 不加新组：AC-16 的真实值放进 `nested_owned_values.carrier`，AC-15 放进 `nested_arrow_type`，
  使 S11 的组在 `CASES` 中的位置不变；没有缝的组不再有 `authority` 项。
- `tests/test_execution_adbc.py` 的 `Payload` 替身加 `nested = False`（`ExecutionPayloads` 的新属性）。
- `tests/_pietto_execution_postgres.py` 的共享 `CheckedRows` 替身同样加 `nested = False`（`PostgresExecution._read`
  读 `payloads.nested`）。
- `tests/test_sql_nested_relations.py` 中 S08 的 output 见证改写为
  `test_a_verified_collect_artifact_is_inspected_and_has_its_output`（原 `..._but_has_no_output_yet`）：按
  slice-07.md 第 6 节的交接规则，打开 output 汇合点的 S10 改写这个见证，不删除。
- preflight 没有 owner 交付（见第 10 节 S12 行）；slice-02.md 的“S08 preflight”改为 S12，并在消费者表中加 S12 行；
  slice-07.md 的 output 两行按 D-S08-7 改为 S10（F-7、F-8）。
