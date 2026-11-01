# Phase71 Slice17：嵌套 IPC framing、解码前的 payload 准入、截断与错 schema、rebatch/offset 与兼容拒绝

状态：B4 S17 本地候选，parent `e169cb88`（IPE 已发布且自然 CI 通过）。本树重放早期 S17 包，并以当前
S10/S11 的 nested interop、字段顺序 oracle 与 IPC 入口关闭点作语义合并。候选移除了私有嵌套 IPC 拒绝，
并接入 source-root 的 nested `encode_ipc`/`open_ipc` 往返、compiled v2 digest 和 payload admission；但尚未运行
focused pytest、Gate 2 或发布。S12/S13 合树后仍须按第 8 节重新验证保存边界和完整 product consumer。
决定来源：S17 Gate 1 记录（ARCHITECTURE_DECISION，D-S17-1 至 D-S17-8）。
本文件是私有格式与交接规则；不进 `docs/spec/`，没有公开输出变化。

## 1. S17-A 交付

| 文件 | 内容 |
| --- | --- |
| `project_result_ipc.py` | `_admit_payload`、`_compressed`；`_open_reader` 在 `pa.ipc.open_stream` 之前调用一次 `_admit_payload`，并交给它调用方的 `reader_limits.max_batches` |
| `tests/test_results_ipc.py` | Arrow-free：检查顺序、消息规则、控制流、flatbuffer slot 与边界 |
| `tests/_pietto_results_nested_ipc.py` | installed product consumer 的两组：`nested_ipc_admission`、`nested_ipc_oracle` |
| `tests/_pietto_execution_nested_oracle.py`、`tests/_pietto_results_nested_ipc_oracle.py`、`tests/test_harness_nested_oracles.py` | tools 冻结版本的逐字节副本（不由 S17 编写） |

payload admission 与 binding 无关，作用于所有 binding。候选以真实 default-leaf source binding 覆盖 nested
round-trip、rebatch、empty 和 offset；目录仍保留 Arrow-free catalog/self-check 作为完整损坏语料的独立来源。

## 2. framing 不换版本（D-S17-1，依据 D71.06）

100 B header `>12sQQQ32s32s` 与 magic `PIETTO-IPC1\0` 不变，字段含义也不变：rows 是父行数；batches 是
RecordBatch 数；size 是 payload 长度；contract 是 32 字节的 `contract_digest(binding.producer.contract)`（源码根为
v1 或 v2 导出的 SHA-256，compiled 根为 compiled-result-contract v1/v2，S09）；最后一项是 payload 的 SHA-256。

- 嵌套帧与平面帧由合同槽区分：平面 binding 永远配不上嵌套帧，反之亦然，结果是 `IPC_CONTRACT`。
- 旧运行时造不出嵌套 binding，会更早被拒（S03 语法、源码文档在 format 处的 `VERSION`、bundle 的 `PIE-R1005`）。
- 子行数不进 header，由 reader 计数（S10 每批，S11 每会话）。writer 选项与 96 MiB 上限不变。

## 3. 解码前的 payload 准入（D-S17-2、D-S17-3、D-S17-4）

`_open_reader(payload, max_batches)` 先遍历 `pa.ipc.MessageReader.open_stream(pa.py_buffer(payload))`，再调用
`pa.ipc.open_stream`：

- DictionaryBatch → `IPC_ENCODING`；
- RecordBatch 的 `Message.header`（slot 2）指向的 `RecordBatch.compression`（slot 3）存在 → `IPC_ENCODING`；
- V4 消息（`Message.version`，slot 0）的 `Message.custom_metadata`（slot 4）中有键 `ARROW:experimental_compression`
  → `IPC_ENCODING`，不论它写的是哪个 codec。这是 Arrow 0.17 的实验格式：没有 compression slot 时，Arrow 对 V4
  消息按这个键解压 body；V5 不读这个键。
- `read_next_message` 抛出 `StopIteration`（流结束，含缺 EOS）或其他 `Exception`（framing 损坏）→ 检查结束，
  损坏留给既有 reader：在 `open_stream` 处报 `IPC_READ`，或在之后的 pull 中报 `READER_SOURCE`；
- `BaseException` 原样传播；
- slot 读取对每个推导出的位置做显式边界检查，越界报 `IPC_READ`。V4 `custom_metadata` 先检查完整 vector
  byte span，且最多扫描 1024 项；超过上限报 `IPC_READ`。Arrow 在交出 metadata 之前已校验 flatbuffer，
  这是纵深防御：`struct.unpack_from` 接受负 offset，会从末尾读。

检查与 reader 共用 Arrow 的 message framing，停在同一条消息；reader 只能解码检查已完整读过的消息，所以从不解压
未被检查的 body。平面 `ipc_lifecycle.late_decode` 的见证不变（交出 [2] 后 `READER_SOURCE`）。

检查最多读 `max_batches + 2` 条消息（`open_ipc` 的 `reader_limits`，默认 1024）：schema、`max_batches` 个 batch，
以及 reader 在报 `LIMIT` 之前多解码的那一个。reader 不会读得更远，所以这个上限不放过任何会被解码的消息；预算之外
的压缩或字典消息由 reader 先报 `LIMIT`，从不被解码。检查的时间与内存都受 reader 的 batch 预算及每消息 1024 个
metadata 项限制。历史预检（不是当前候选的 Gate 2）曾在
`wf19-continue/s17-review-ipc-r2c/probe/` 记录平面 postgres schema 之后跟 1,383,517 条 72 B 零列 RecordBatch 的
95 MiB 帧，经真实 `open_ipc` 与读取都报 `READER_SOURCE`：基线 1.24 s，无界的检查 15.72 s，有界的检查 1.58 s。

检查无条件生效（D-S17-3 选 A，tools F-T1 的根因修复）：产品 writer 从不压缩、从不写字典；保存的 chunk 在
`open_ipc` 之前已按 digest 核对，所以只有不是 Pietto 写出的字节会改变结果；没有公开 IPC 入口。

政策点：

| 输入 | 结果 |
| --- | --- |
| zstd、lz4 压缩的 body（含只由 V4 `ARROW:experimental_compression` 键声明 codec 的） | 解压之前 `IPC_ENCODING` |
| DictionaryBatch（含嵌套 struct 中字典类型的子字段） | `IPC_ENCODING`，先于 reader 的 `ARROW_SCHEMA` |
| legacy 前缀、metadata V4、缺 EOS | 放行，值与规范帧相同 |
| V4 的 `Message.custom_metadata` 不含该键 | 放行；Arrow 自己在该 batch 报 `ArrowInvalid`（那里只允许 LZ4_FRAME 或 ZSTD），即 pull 时 `READER_SOURCE`，没有 body 被解码 |
| 零长度 list、offsets buffer 长度为 0、0 行 | 放行 0 行（S10 长度 0 规则，S11 规范 copy） |
| EOS 之后的尾随字节、big-endian schema | 刻意不查：reader 在 EOS 停止，frame digest 覆盖这些字节；换字节序的分配受 96 MiB 限制 |

历史预检（不是当前候选的 Gate 2）：一个 10,852 B 的 zstd 平面帧，内含一个 256 MiB 的 Text 值。经真实 `open_ipc`，
基线先使峰值 RSS 增加约 260 MiB，再报 `LIMIT`；S17-A 报 `IPC_ENCODING`，峰值 RSS 增加 576 KiB。一个 12,268 B 的 V4
帧只用 `ARROW:experimental_compression` 键声明 zstd，内含同样的 256 MiB Text 值：只查 slot 3 的检查会放行它，
峰值 RSS 增加约 268 MiB 后才报 `LIMIT`；现在报 `IPC_ENCODING`，峰值 RSS 增加 4,884 KiB。它们不证明当前候选。

## 4. oracle 类别到私有类别的映射（D-S17-5）

| oracle 类别 | 私有类别 | 位置 | 交出的行 |
| --- | --- | --- | --- |
| ACCEPT | 无；`verify_ipc_completion` 通过 | — | 全部，值等于 oracle |
| REFUSE_FRAME | `IPC_FRAME`（超上限时为 `LIMIT`） | `_frame` | 无；没有 SDK 调用 |
| REFUSE_CONTRACT | `IPC_CONTRACT` | `open_ipc` | 无；没有 SDK 调用 |
| REFUSE_ENCODING | `IPC_ENCODING` | `_open_reader` 的检查 | 无；`open_stream` 未被调用 |
| REFUSE_READ | schema 消息损坏或不是 stream 时打开即 `IPC_READ`；之后的消息损坏时在该消息处 `READER_SOURCE` | `_open_reader` / reader `_pull` | 只有损坏点之前的消息；永不 complete |
| REFUSE_SCHEMA | `ARROW_SCHEMA`；`child_dictionary` 例外，带字典 batch，报 `IPC_ENCODING` | reader `__init__`；字典在 `_open_reader` | 无 |
| REFUSE_BATCH | `ARROW_BATCH` 或 `NULL` | reader `_pull` | 损坏之前的 batch；永不 complete |
| REFUSE_EXTENT | header rows ≠ expected 为 `IPC_EXTENT`；行数不足或超出为 `READER_EXTENT`；batch 数 ≠ header 为 `IPC_COMPLETION` | `_frame` / reader / `verify_ipc_completion` | 可能交出全部行，但永不 complete |
| REFUSE_LIMIT | `LIMIT` | `_frame`；reader 每批（S10）与每会话子行（S11） | 永不 complete |

只有 `verify_ipc_completion` 通过才算 complete。错误文本只含类别词；`IPC_ENCODING` 不带 `__cause__` 与
`__context__`，所以 sentinel 不会出现在错误链中。新词只以 detail 的形式经 `category_word` 到达公开面，而且只对
非 Pietto 写出的 chunk。

## 5. 不打开保存入口（D-S17-7）

S17-B 只对嵌套 binding 打开私有的 `encode_ipc`/`open_ipc`。公开面只能经保存、R1、导出到达，它们由 S12 的连接前
准入保持拒绝，到 S18/S19 为止。S17-B 的 Gate 0 必须确认：移除 S11 的拒绝后，嵌套 capture 仍在连接前被拒。

## 6. 测试 owner

- `tests/test_results_ipc.py`：Arrow-free 检查，未标记的 ordinary 测试。
- `tests/_pietto_results_nested_ipc.py`：S17 IPC 产品 owner，由 `_pietto_results_product.py` 加载，组追加在
  `CASES` 末尾；S14、S15、S16 往里加 IPC 正例与类型错配。
  - `nested_ipc_admission`：目录中每个 payload case 的准入结论（`compression_zstd`、`compression_lz4`、
    `child_dictionary` 为 `IPC_ENCODING`，其余放行）；字典流与空 payload；只由 V4 `ARROW:experimental_compression`
    键声明 zstd、lz4 的嵌套 canonical payload；压缩 case 在 `open_stream` 与 `read_record_batch` 都被替换成失败时
    仍报 `IPC_ENCODING`；postgres 与 mysql 的 finite fixture 经真实 `open_ipc` 的重编码帧（含只由该键声明 codec
    的 V4 帧，以及不含该键、由 reader 报 `READER_SOURCE` 的 V4 custom_metadata 帧），以及去掉检查后的对照（zstd
    被解压放行，字典到达 `ARROW_SCHEMA`，只由该键声明的帧被解压成与规范帧相同的值）。
    default-leaf 的 non-null nested cases 另由真实 C6 source binding 经 `open_ipc` 覆盖全部 oracle 类别；
    `nested_nullable` 保持 S16 的明确测试缝，flat binding 继续由既有 finite product owner 覆盖。
  - `nested_ipc_oracle`：tools IPC oracle 在 pinned PyArrow 26.0.0 下的 `self_check`，逐 case 记录结论。
- `tests/test_harness_nested_oracles.py`：随 oracle 一起落地，`ci_workload("general-runtime")`。
- consumer 的 `HELPERS` 按依赖顺序列出 observation helper、两个 oracle 与新 helper：在 `-I` 下 tests 目录不在
  `sys.path`，literal oracle 对 observation helper 的 import 只能命中已加载的模块。

## 7. 交接

| 片 | 与 S17 的关系 |
| --- | --- |
| S07-B | `export_result_contract` 写出 `pietto.result-contract.v2`：嵌套 header 的合同槽 |
| S09 | `contract_digest` 的 compiled 分支写 `pietto.compiled-result-contract.v2`（集成者 patch） |
| S08、S10-B | 真实嵌套 `ArrowResultBinding`，与 oracle 的 `canonical_schema` 完全相等 |
| S11 | reader 接受嵌套、每会话子行上限、`_copy_batch` 结构 copy；嵌套 IPC 的显式拒绝放在 `encode_ipc`/`open_ipc` 的入口（不放进 `_open_reader`），S17-B 移除它 |
| S12、S13 | 嵌套 save/R1/export 的连接前拒绝保持；S17-B 重新见证 |
| S14、S15 | 在 S17 owner 中加子 leaf 的 IPC 逐位正例与类型错配 |
| S16 | 在 S17 owner 中加可空容器与两个嵌套字段的 IPC 正例 |
| S18、S19 | 经 `open_ipc` 读 chunk，自动继承准入检查 |
| tools | oracle 冻结后重新同步副本；合入时 literal oracle 必须等于 S08 或 S12 落地的版本。目录应补只由 V4 `ARROW:experimental_compression` 键声明 zstd、lz4 的 REFUSE_ENCODING case；同步时把它们加入 helper 的 `REFUSED` |

## 8. B4 合树后的验收清单

- 候选已移除 S11 的入口拒绝，并以 default-leaf source binding 见证 canonical schema、round-trip、rebatch、empty、
  offset、全部 non-null catalog 类别与 compiled v2 digest；当前尚未执行这些 product checks。`nested_nullable` 到 S16
  为止仍只走测试缝。
- 目录每个 case 按自己的 framing 经真实 `open_ipc`，类别符合第 4 节；ACCEPT 的值经 oracle 比较器相等。
- encode 往返：单 batch、每父行一 batch、夹空 batch、零行 batch、零 batch、list 级切片、struct offset、非零首 offset。
- 兼容：v1/v2 digest 互换为 `IPC_CONTRACT`；compiled 根的嵌套帧；`child_rows_over_cap` 为 `LIMIT`；
  `large_list` 与 `element` 等变体为 `ARROW_SCHEMA` 且 0 行。
- D71.11：S17-A 只改 `project_result_ipc.py`，不在登记的原生族输入闭包内，记 `NOT_REQUIRED_LOCAL`；S17-B 在 Gate 0 重判。
