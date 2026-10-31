# Phase71 Slice11：嵌套 copy/borrow/lease、C data/stream、非零 offset、零行与 close 生命周期

状态：candidate（批次 B3），S11 定稿（S11-A 与 S11-B，同一笔提交，在 B3 中排在 S08、S09、S10 之后）。D71.11 的 native 运行与
installed product 的权威运行由封存阶段在确切的 candidate wheel 上进行（第 9 节）。
决定来源：S11 Gate 1 记录（ARCHITECTURE_DECISION，D-S11-1 至 D-S11-8）。
本片建立在 [S10](slice-10.md) 之上；批次 B3 建立在 main 的 `81f0d3b5` 之上，其发布规则见[路线](slices.md)，发布之前本片是 candidate。
本文件是私有格式与交接规则；不进 `docs/spec/`，没有公开 JSON、CLI、SQL 或诊断变化，`pietto` 没有新名字。

## 1. 交付与测试缝

| 文件 | 内容 |
| --- | --- |
| `project_arrow_interop.py` | `_copy_batch` 去掉 S10 guard，嵌套列走结构 copy（`_nested`、`_empty`；平面与嵌套共用 `_buffer`）；`ManagedBatch.__init__`、`import_batch` 经 `_delivered` 核对子行对应；`ManagedStream._next` 读 observation 的 `[3:6]` 并核对子行对应 |
| `project_result_reader.py` | 去掉 reader guard；接受前检查 N_fields；`BatchDescriptor.child_rows`；每会话子行上限；completion 复核子行 |
| `project_arrow_result.py` | 只把 `_checked_batch_usage` 拆成 `_checked_batch_counts`（返回 `(A, R, C)`）加 2 元组 wrapper |
| `project_result_ipc.py` | 只在 `_contract_digest` 中对嵌套 binding 报 `NESTED_UNAVAILABLE`（第 6 节） |

`build_managed_batch` 不经 copy，生产中的嵌套交付（`ExecutionPayloads`）不经 S11 的 copy；consumer 拿到 C 导出后
再交回 `import_batch`/`import_stream` 时才经过它（第 9 节的 native 步骤）。

测试：installed product consumer 的扁平 helper `tests/_pietto_results_nested_interop.py` 六组
（`nested_copy`、`nested_copy_refusals`、`nested_c_array`、`nested_streams`、`nested_zero_rows`、
`nested_ipc_closed`），每组一个 damage control，没有新的 pytest 节点（每个行为都要 Arrow，core profile 不装）。
嵌套 producer 全部是真实的（S11-B，第 9 节）：S10 的 `real` 用 rows reader 绑定真实 VERIFIED 的 PostgreSQL
Collect（S08）output。只有可空容器（S16 之前没有真实上游能产生）保留 S10 登记的唯一测试缝 `admitted()`（代替
`project_arrow_result.verify_producer_binding`），只用在 `nested_copy_refusals` 的 `null_container_segment` 一项，
该组的 `authority` 记录不加缝时入口的类别（`FIELD`）；其余组没有缝，也就没有 `authority` 项。“禁止调用”类见证用
观察者（被调用即失败），每个观察者都有正向控制，它们不是第二个权威缝。期望值都是手写字面值，从 S10 的
`ROWS` 与 carrier 行按 slice 推出（S11 自己重写一遍，不取自 S10 helper 或被测代码）。

接线（P-WIRE，已在集成树中，与 S11 的 src 改动同一笔）：`_pietto_results_product.py` 加载、`CASES`、`run`、
`verify`、damage 各加一处；两个平面组替换的共享检查器（`reader_lifecycle` 的 `validation_stop` 与 ingress 的
“五条路径都调用共享检查器”）改为替换 `_checked_batch_counts`，期望值不变（`_checked_batch_usage` 只是它的
wrapper，`build_managed_batch` 也经由它）；`_pietto_results_consumer.py` 与 `scripts/phase68_executor_premise.py`
的 HELPERS；`_pietto_results_nested.py` 的 `nested_guards` 期望机械翻转（五个入口改为 `ACCEPTED`，
`owned_ingress` 为 `READER_SOURCE` 且 source 已关闭，两个 IPC 入口改为 `NESTED_UNAVAILABLE`）。

P-WIRE 与 S11 的 src 改动不可分，必须落在同一笔提交里，规则同第 6 节的 IPC hunk。copy 与 reader 路径改调
`_checked_batch_counts` 之后，两个平面组若仍替换 `_checked_batch_usage`，注入的失败就到不了这些路径，组会报
`AssertionError`；`nested_guards` 的 S10 期望也不再成立。只落 src 的树会让 CI 的 arrow-ready product 步骤失败。

## 2. 结构 copy

```text
_copy_batch(batch, lease):                    # 签名不变；batch.schema 已由 _verify_schema 判定与 bound 相等
  每列 kind = batch.schema.field(i).type
    非 list：平面主体（输出逐字节不变）
    list：_nested(column, kind, lease)；只有这一支把 (ValueError, ArrowException) 映射为 ARROW_BATCH，
          在 except 块之外抛出，__cause__ 与 __context__ 都是 None
_nested(a, kind):
  len(a) == 0 → _empty(kind)                  # 只读 len()
  struct → from_buffers(kind, len, [None], null_count=0, children=[_nested(a.field(k), …)])
  list   → from_buffers(kind, len, a.buffers()[:2] 的 copy, offset=a.offset, children=[_nested(a.values, …)])
  leaf   → from_buffers(kind, len, a.buffers() 的 copy, offset=a.offset)
_empty: list [None, 00000000] 加子 empty；struct [None]；string [None, 00000000, b""]；其他 [None, b""]
copy(b): None → None；owned → py_buffer(bytes(b))；leased → py_buffer(_LeasedBuffer(b, lease))
```

- 类型戳记：每一层都用已验证 schema 的类型（B9）。PyArrow 26 的 `RecordBatch.from_arrays(schema=S)` 接受
  列类型只在 item 名或子元数据上不同的数组；copy 不把列自己的类型传下去。
- list 保留自己的 offset 与整块 offsets；struct 改到 offset 0 且不带 validity，子 leaf 带上 struct 的 offset。
  丢弃 struct validity 只在 S10 的引用区间 null 检查之后才安全（B7）。
- 规范空数组：嵌套列内任意深度的零长度数组都换成全新的 owned 空数组，从不 lease。平面零长度列保持原样。
  B6：全 `[]` 而子 buffer 缺失的 batch 能过 `validate(full=True)`，其 C 导入报 `ArrowInvalid`；交付后的
  C 导入成功。B10：零长度 list 在 offsets 缺失时，`offsets`/`flatten()` 会让 PyArrow 26 崩溃，所以只读 `len()`；
  product consumer 在子解释器中见证缺失与零大小两种 offsets（owned 与 leased）。
- 结构 copy 保留整块父 buffer，所以 slice 的 R 与整批相同（平面同理）。交付后的 R 只在丢弃 struct validity
  或换成规范空数组时变化，可能变小，也可能变大：
  - 变小：零行 slice 的嵌套列换成规范空数组，不再保留整块父 buffer（171 → 48）；丢弃 1 字节的 struct
    validity（48 → 47）。
  - 变大：规范空数组补上 source 缺失的 buffer，多出几个字节（B6：28 → 32）。这时 stream 在 `remaining`
    边界上失败关闭（`LIMIT`），不会误放行。
- 只有 Int/Bool/Text 子 leaf 能到达 copy（S10 白名单，`_verify_schema` 在 copy 之前）。

## 3. 计数与对应

`_checked_batch_counts(batch, binding, producer, *, limits) -> (A, R, C)` 是原 `_checked_batch_usage` 的主体，
末尾多返回已在算的引用子行数；`_checked_batch_usage` 是取前两项的 wrapper，其余调用者不变。
`ManagedBatch.source_usage`/`usage` 仍是 2 元组（`ExecutionPayloads.accept` 按 `max(managed.usage)` 计费），
`ManagedStream.descriptors` 仍是 6 元组。

三个 copy 入口（`manage_batch`、`import_batch`、`ManagedStream._next`）都核对交付子行数等于 source 子行数，
否则 `ARROW_BATCH`。这条只是计数定律：移位后子行数相同的 copy 缺陷抓不到，值的正确性由结构 copy 本身与
copy 矩阵见证。

## 4. reader 计量

- observation 与 `BatchDescriptor` 末位加 `child_rows`；平面恒为 0；父行仍是唯一的行单位（D71.07）。
- 接受前：`_verify_schema` 之后检查 `_dimensions(N_fields, 0, limits.batch)`，N_fields 是顶层加全部子字段；
  不满足时报 `LIMIT`，source 留在调用方（owned ingress 会关闭它）。原来的 `_dimensions(len(source.schema), …)`
  与 `_pull` 的 `_dimensions(batch.num_columns, …)` 保持不变：直接改用 N_fields 会把过宽平面 source 的类别从
  `LIMIT` 变成 `ARROW_SCHEMA`（相对 slice-10 第 7 节的措辞）。`_pull` 的 N_fields 已由 counts 内部检查。
- `_pull`：会话子行合计超过 `MAX_CHILD_ROWS`（1,048,576，S02）时，在记录 observation 之前报 `LIMIT`，reader
  进入 `FAILED`，source 恰好关闭一次。字节规则不能代替它：空串 Text 子行每行只计约 4.25 B。
- completion：每个 `child_rows` 是 int、非负、不超过上限且等于 observation；合计等于 `reader._children` 且
  不超过上限；否则 `READER_IDENTITY`。
- `CheckedFiniteReader.read_next_batch` 原样交回调用方的 source batch，只核对不规范化（与平面相同）；规范零行
  只保证经 copy 交付的 batch。

## 5. 拒绝表（私有类别；公开码由 S12 映射）

| 入口 | 条件 | 类别 |
| --- | --- | --- |
| 任一 copy 入口 | source 未通过 S10 嵌套检查 | `ARROW_SCHEMA` / `ARROW_BATCH` / `NULL` / `LIMIT`，copy 不被调用 |
| `_copy_batch` 嵌套分支 | PyArrow 意外失败 | `ARROW_BATCH`，不串联 PyArrow 文本 |
| 任一 copy 入口 | 交付子行数 ≠ source 子行数 | `ARROW_BATCH` |
| `__arrow_c_array__` / `__arrow_c_stream__` | requested 为 `element` item、`large_list`、`list_view`、可空 item 或子字段元数据 | `INTEROP_REQUEST`；精确 schema 被接受 |
| 导出 | close 之后；第二次 spend；`copy(grant)` | `INTEROP_CLOSED`；`INTEROP_SPENT`；`INTEROP_BINDING` |
| leased 导出 | owner 被替换、`non_mutation` 被删 | `INTEROP_LEASE` |
| leased 导出 | owner 改动 offsets（不单调）、子 Text 字节（非 UTF-8） | `ARROW_BATCH` |
| leased 导出 | owner 清掉非空子字段的 validity 位 | `NULL` |
| reader `_pull` | 会话子行 > 1,048,576；字节超预算 | `LIMIT` |
| reader 打开 | N_fields > `min(limits.fields, 64)` | `LIMIT`，在接受之前 |
| completion | `child_rows` 被改、为负、不是 int，或与 reader 合计不符 | `READER_IDENTITY` |
| `encode_ipc` / `open_ipc` | binding 含嵌套字段 | `NESTED_UNAVAILABLE`，到 S17 为止 |

不新增类别。close 之前做的外部导入在 close 加 GC 之后仍然有效；leased owner 在外部导入存活期间被 pin 住，
导入释放后随之释放。`ManagedStream` 的终态 `CLOSED`、`CLOSED_INCOMPLETE`、`FAILED` 与 `__del__` 兜底与平面相同。

## 6. IPC 拒绝与 S17 的移除规则

去掉 reader guard 时如果不同时关闭 IPC，S07-B 一落地，嵌套 IPC 就会在 S17 之前开放（Gate 1 探针：替身
digest 下帧 1,052 B、往返值相等），并连带打开经 `encode_ipc`/`open_ipc` 的 capture 与 `SnapshotReader`。
所以拒绝放在 `project_result_ipc._contract_digest` 中、`interop._capture(binding)` 之后、`contract_digest` 之前：

- `encode_ipc` 在 `ingest_reader` 之前拒绝；`open_ipc` 在 `_frame` 之后、`_open_reader` 与 ingress 之前拒绝，
  即在任何 Arrow IPC 导入之前；`IPCStream` 复核同一个函数。
- 先于 `contract_digest`，所以无论 S07-B 或 S09 的 digest 何时落地，见证都稳定。
- canonical 文件由集成者单一写入：这个 hunk 同时导出为精确 patch（P-IPC），接在 S09 的 `contract_digest`
  patch 之后。
- replay `_rebatch`、`verified_export`、R1 的嵌套输入只能来自已保存的嵌套结果，保存与读取都经过这两个入口，
  所以 S11 之后仍不可达。
- **S17 移除的就是这一个 hunk**；S10-B 若改写 `nested_guards` 中 IPC 的两行，只能改成 `NESTED_UNAVAILABLE`。

## 7. 偏差

相对 S11 DESIGN：

- 不写嵌套层的扩展类 re-wrap、UUID 规范空数组与 `nested_leaf_layouts` 组：其他 leaf 到不了 copy，这些由
  S14/S15 与 binder 放宽一起交付并测试。通用 leaf 分支对其他非扩展定宽或 binary 布局本来成立。
- 不加 DESIGN 10.2 的 Arrow-free stub 测试：平面 stream 组本来就是 observation 变长的回归见证，IPC 拒绝与
  completion 损坏在 product 组中用真实 reader 见证。
- 测试 owner 是新扁平 helper，不追加进 S10 的 `_pietto_results_nested.py`（单一写者；按 aspect 划分）。

相对 S11 Gate 1（S11-B）：
- `delivered` 只 copy 后缀 slice；全部 slice 的矩阵（AC-02）在 `nested_copy` 中对真实 captured binding 跑一次，
  closed binding 的 copy 由 `carrier` 的后缀 slice 覆盖。
- 零父行与全 `[]` 的真实结果需要新语句：S10 helper 的 `collected` 加 `where`、`kid_where` 两个选项（S11 的改动）。
- native 步骤放在 S11 helper 的 `delivered`，rows probe 调用它（rows probe 已经这样加载 S10 helper）。

相对 S10 交接（slice-10 第 7 节）：N_fields 是追加检查，不替换原有 `_dimensions` 调用（第 4 节）。

## 8. 交接

| 片 | 从 S11 接手 |
| --- | --- |
| S12 | 公开嵌套 `ResultBatch` 的承诺与公开码（`INTEROP_CLOSED` → PIE-R4002，其他 → PIE-R4003，尝试中 → R3005）；连接前拒绝；saved-read gate |
| S14、S15 | 新 leaf 走通用 leaf 分支并由它们测试；嵌套层 UUID 扩展类 re-wrap 与规范空数组归 S15；放宽 `_checked_batch_counts` 时基于 S11 的拆分 |
| S16 | 可空容器的真实正例，同样经过 copy |
| S17 | 移除 `_contract_digest` 的那一个 hunk；嵌套 IPC 读入后经 S11 的 copy 交付；IPC 零长度 offsets 由 S11 规范化 |
| S18、S19 | `_rebatch` 与 export 的 slice copy；结构 copy 的成本定律（slice 保留整块父 buffer）；S19-3 复核 |
| S20 | 全组合下的资源、取消与 close 复核；producer binding 的每次复核成本（第 9 节实测） |

## 9. S11-B：真实 producer、native 步骤与 installed 权威

真实 producer（`run` 按 `SHAPES` 各建一次，S10 的 `real`）：captured 与 closed 的 `(i Int, b Bool | None,
t Text | None)` Collect、父行过滤后没有父行的 `no_parents`（`where rows.id > 100`）、每个父行都收集到 `[]` 的
`all_empty`（`kid_where`：`kids.seq > 9`）、单独一个 Text 子字段（会话子行上限）、63 与 64 个子字段（接受时的
N_fields）。为此 S10 helper 的 `collected` 加了 `where`（父行过滤）与 `kid_where`（与捕获条件 `and` 连接）两个
选项，默认不变。

| 组 | 改用真实 producer 后 |
| --- | --- |
| `nested_copy` | P = 5 的全部 21 个 slice 乘 owned/leased（captured）；`carrier`：captured 与 closed 各把 S10 的 psycopg 形状 carrier 行（重复、`[]`、全 NULL 子行、Int64 极值、引号字符与多字节）经 rows reader 的严格 decoder 与 `build_managed_batch` 按 4 行一批交付，C 导出后关闭 handle、GC，再读值（字面 oracle），然后跑 `delivered` |
| `nested_copy_refusals` | 真实 binding 的拒绝在缝外；可空容器一项保留缝 |
| `nested_c_array`、`nested_streams` | 真实 binding；会话上限与接受宽度用真实的 Text 与宽 Collect |
| `nested_zero_rows` | `carrier`：`no_parents` 没有批次，`all_empty` 五个父行（0、2、5、5、-1）都是 count 0 与 NULL arrays，两批 |
| `nested_ipc_closed` | 真实源码根 digest（S07-B）接受嵌套合同（32 B），所以 S11 的拒绝是唯一的关闭点：去掉它，真实嵌套 IPC 往返成功（帧 1,052 B，值相等）；S11-A 的替身 digest 因此删去 |

`delivered(binding, batches)`（S11 helper）是一个真实结果的 S11 步骤，参数是 handle 已关闭的 C 导出：每个导出
交回 `import_batch`；每批的每个后缀 slice（整批、每个非零 offset、零长度尾部）owned 与 leased 各 copy 一次；全部
批次经 `import_stream` 与 `manage_stream` 读回。每次 copy 核对值等于导出自己的值、子行数相等、每层类型戳记；
stream 核对终态 `CLOSED`、值相等、descriptor 的子行合计。全部 (start, length) slice 已由 `nested_copy` 的矩阵覆盖，
所以这里只取后缀。product 组与 native 用例调用同一个函数。

**native（D71.11，追加在 S10 的嵌套 rows 用例上）**：
- `collect_pg(nested=True)` 在 `with batch:` 中只做 C 导出，handle 关闭后 `gc.collect()` 再读值，所以记录的值
  都是 close 加 GC 之后的值；没有失败时对全部导出跑 `delivered`，写入记录的 `interop`。
- `NESTED_SHAPES` 加 `no_parents` 与 `all_empty`（description 与 Arrow 字段同 captured）；`nested_expected` 对两者
  按同一过滤从 `KIDS` 推出（没有父行；每个父行的子行为空）。
- `check_nested_record` 追加：每批父行数为 1 到 4（`batch_rows=4`，空 fetch 结束 stream，不交付空批）且批数等于
  schema 数，合计等于 oracle 的父行数，`interop` 等于 `nested_interop_expected`（子行合计取自 oracle，后缀 slice
  数取自每批父行数）；`small_batch` 的 `interop` 必须是 None。
- 本片没有运行 native；离线模拟（不用数据库，把 oracle 推出的 carrier 行经真实 binding 交付）对六个形状与
  `small_batch` 通过，五种记录损坏都被拒。

**installed 权威**：六组在 installed product consumer 中运行（D71.12）：封存时在 candidate wheel 的全新
`pietto[arrow]` prefix 中运行，报告由 `scripts/ci_validation.py check-product` 核验；`PRODUCTS` 要求的来源已包含
S11 改动的四个模块。开发循环（`PYTHONPATH` 指向工作树）只是非权威见证。

**成本（实测，非权威；耗时随主机负载变化，次数与比例不变）**：真实 producer 让六组明显变慢；首次测量时主机
负载较高，六组从约 23 s（缝下）增到约 3 分钟，空闲主机（12 CPU，load average 0.9）重测真实 producer 的六组约
55 s。原因不在 S11：每次 capture 与每次 `_checked_batch_*` 都完整复核 producer binding，真实嵌套 producer 的
一次复核约为平面的 7 到 8 倍（output 视图重新检查 emission；空闲时约 30 ms 对约 3.7 ms）。生产中每个交付批次
复核 8 次（`build_managed_batch` 3 次，导出 5 次）；一次 copy（`manage_batch`）加导出复核 7 次（3 次加 4 次）。
