# Phase71 Slice12：Int/Bool/有限 Text 的公开最小真实纵向（连接前准入、未闭合消费者的预拒绝）

发布状态：`COMPLETED / PUBLISHED`（main 的 B4 批次）。批次 head
`9df0003f020c0d5e61fb32e4528cfd20d9125142`，tree
`fa5e45c8c794207a360b3a195474e738ac2f49e9`；自然 CI `41272976489`
attempt 1 的 19 个 job 均成功。
以下保留实施时的候选与检查记录；其中的待验证文字属于封存前时点。

封存前记录：S12-B candidate。S12-A 的连接前准入与未闭合消费者门保留；S12-B 加入来源 preflight。
决定来源：S12 Gate 1 记录（ARCHITECTURE_DECISION，D-S12-1 至 D-S12-9）。
本 B4 integration candidate 绑定 parent `e169cb88f17d54234a96fc275766cb0995a2be37`
（tree `43efe9fd355213b74b3061a51c3356abd9004303`），并纳入 AC-F7。这里没有 focused、原生、Gate 2
或发布验证结论；这些仍由 B4 的后续冻结流程记录。

本文件是私有准入规则与交接；不进 `docs/spec/`。S12-A 没有公开输出变化：编译与模板闸门移除之前，下面的拒绝在
公开面不可达。

## 1. S12-A 交付

| 文件 | 内容 |
| --- | --- |
| `project_execution_nested.py`（新） | `collection_operations`、`admit_collection_route`、`admit_nested_shape`；`__all__ = ()`；只被调用者 lazy import |
| `project_execution.py` | `_verify_compiled_premise` 第一条语句调路线准入；`_verify_execution_structure` 在 `verify_result_contract` 之后调子 leaf 准入 |
| `execution/_errors.py` | `_REQUEST` 加 `COLLECTION_ROUTE`、`COLLECTION_LEAF` |
| `execution/_saved.py`、`execution/_relay.py` | 私有 helper `_collection_entry`；`save()` 与 `relay_live` 在 `_checked_request` 之后调用 |
| `project_refinement.py` | `_live_shape` 的第一个检查 |
| `project_job_replay.py` | `accept_saved_read`：`verified_stored_output` 之后、`checkpoint_snapshot` 之前 |
| `project_execution_postgres.py` | qualification 后、carrier 前，在同一 owned transaction 读取并绑定 preflight receipt |

## 2. 运算谓词

```text
collection_operations(records) -> frozenset[str]
  "unnest"  ∈ 结果 ⇔ 存在 address.kind == "unnest"
  "collect" ∈ 结果 ⇔ 存在 address.kind == "operation" 且 operator == ("collect", "collect")
```

- 所有拒绝门都按编译根的完整运算闭包判定，不只看最终输出形态：最终输出平面的 Unnest 同样被拦住。只有子 leaf
  域按结果形态判定（第 3 节）。
- 字面值取自 S09-A 已冻结的词表（`project_compiled_schema.COLLECT_OPERATOR`、`FIELDS["unnest"]`）。S12-B 改为
  import，属机械改动。
- 平面根恒为空集：本 tree 没有 S09 的 collect 词表，S12-A 不改变生产可达性。

## 3. 连接前准入

| 检查 | 位置 | 拒绝 |
| --- | --- | --- |
| 路线 | `_verify_compiled_premise` 第一条语句；覆盖 execute、save、R2、relay 的 `_checked_request`，recover 的 `verify_unbound_request`，guarded 与 refined 请求，各 owner 打开时的复核 | 运算非空，且路线不是 `postgres_rows`，或 policy 为 guarded 或 refined → `COLLECTION_ROUTE`（PIE-R1003） |
| 子 leaf | `_verify_execution_structure`，`verify_result_contract` 之后 | 任一 `NestedShape` 子字段的 canonical 名不在 S12 的 `{Int, Bool, Text}` 固定域中 → `COLLECTION_LEAF`（PIE-R1004） |

- 路线准入先于该路线自己的 premise 校验，因而先于任何 driver import、连接、workspace 或 sink。premise 本身也错时，
  结果仍是 `COLLECTION_ROUTE`。MySQL：公开入口的 dialect 检查（`PUBLIC_ROUTE_UNAVAILABLE`）先发生；私有路径得到
  `COLLECTION_ROUTE`。先例是 `MYSQL_TABLE_FUNCTION_ROUTE`。
- 没有子 leaf 检查时，Float 子字段的 Collect 会先连接、qualification 并提交 carrier SQL，到 Arrow binding 才被拒
  （`PRODUCER_UNSUPPORTED`）。S12 的子 leaf 准入固定为 Int、Bool 和有限 Text；S14/S15 明确扩大这一个域。平面合同不 import
  Arrow owner。

## 4. 未闭合消费者的预拒绝

| 门 | 位置 | 拒绝 | 由谁移除 |
| --- | --- | --- | --- |
| G-save | `save()`：`_checked_request` 之后、`open_workspace` 之前 | PIE-R1004 `COLLECTION_ENTRY` | S18（只删 `save()` 中这一处调用） |
| G-relay | `relay_live`：`_checked_request` 之后、`_sink_target` 与 workspace 之前 | PIE-R1004 `COLLECTION_ENTRY` | Phase71 内不移除（S20 复核） |
| G-R2 | `_live_shape` 第一个检查；覆盖 `save_recoverable` 与 `recover`（含 restated 而未绑定） | `ValueError("PUBLIC_R2_COLLECTION")` → PIE-R1004 | 不移除 |
| G-read | `accept_saved_read`：trust、restated 与 stored output 核对之后，checkpoint 之前；覆盖 `open_saved_read`、`release_saved_read`（都在 `claim_publisher` 之前）、`verified_export` 与 runtime REPLAY | `JobStoreError("SAVED_READ_COLLECTION")` → PIE-R1009 | S19 |
| IPC | S11 的 `_contract_digest` hunk | 私有 `NESTED_UNAVAILABLE` | S17 |

- 不放 G-publish：S18 之前不可能存在嵌套 generation（G-save 加上 `describe_compiled_binding` 的拒绝），而 S18 在
  同一笔提交中同时打开 save 与 publication。
- `save` 走 adbc 时先报路线（`COLLECTION_ROUTE`），再轮到入口门。
- `SAVED_READ_COLLECTION` 借用 PIE-R1009（WORKSPACE_REFUSED），语义偏窄；它只在 S18 到 S19 这个未发布窗口中可达。
- 精确 patch P-GREAD：`project_job_replay.py` 与 `test_execution_api_saved_read.py` 的 hunk 同时导出。S18/S19 lane
  不改 `accept_saved_read` 的函数体，也不改追加的测试函数；集成顺序 S12（B4）→ S19（B6），由集成者单一写入。

## 5. 公开码

| 私有词 | 公开码 | 来源 |
| --- | --- | --- |
| `COLLECTION_ROUTE` | PIE-R1003 | `_REQUEST` |
| `COLLECTION_LEAF` | PIE-R1004 | `_REQUEST` |
| `COLLECTION_ENTRY` | PIE-R1004 | 直接构造 |
| `PUBLIC_R2_COLLECTION` | PIE-R1004 | `ValueError` 的既有映射 |
| `SAVED_READ_COLLECTION` | PIE-R1009 | `workspace_failure` |

不新增 PIE-R 码，文档中的码集合不变。没有加入公开映射的新 `ExecutionError` 词会公开为 PIE-R1999。所有词都避开
`nested_relation`（S04 的 sentinel）。S12-B 再加 `POSTGRES_SOURCE_ENCODING`，经既有前缀映射为 PIE-R2007。

## 6. 测试缝与 owner

- 唯一的缝：`project_execution_nested.collection_operations` 换成返回 `{"collect"}`，代表尚未进入本 tree 的 S09
  collect records。每个缝用例都配一个不加缝的对照，记录今天的平面结果。“被调用即失败”的观察者
  （`open_workspace`、`_sink_target`、`claim_publisher`、`register_consumer`）不是第二个缝。
- `tests/test_execution_nested_relations_admission.py`（新 owner，Arrow-free，`ci_workload("general-runtime")`）：
  平面根恒为空集（postgres、mysql、table function、guarded、refined）、谓词、公开 execute 与私有路线准入、
  子 leaf（S10 的真实子 leaf：ibt 接受，Float/Decimal/Date/Timestamp/UUID 拒绝）、save/relay/R2 门。
- `tests/test_execution_api_errors.py`：分类表加三行。
- `tests/test_execution_api_saved_read.py`：G-read 见证，用 `unstarted_saved_generation`，需要合格的 v7 存储；
  对照得到该夹具 checkpoint 处的 `CAPTURE_UNKNOWN`，证明门在 snapshot 之前；存储不合格时以 skip 报出。
- 这些是机制测试，不是验收正例；正式正例只在 S12-B，来自真实上游 owner。

## 7. S12-B 来源 preflight

只对有 Collect operation 的 `postgres_rows` request 执行。它把唯一 active Collect 同 `NestedOutputColumn` 的
`CollectColumn`、nested type、child terminal 与 `BoundSource` field occurrence 逐一绑定；同名物理 relation 的不同声明
不能合并。S13 只对同一 Collect 的唯一 Unnest JOIN 单独重建此绑定，允许最终只选择 child 字段的子集。child 只能属于
`project_result_binding.CHILD_KINDS`。普通完成 relation closure 只接受 source、row、result：JOIN、SET、VALUES、
aggregate、window、table function、额外 source 或未知路径在 carrier 前拒绝，不能把物理根的 `COUNT(*)` 误作它们的结果行数。

qualification 后、carrier 前，固定 SQL 在同一 owned REPEATABLE READ/SERIALIZABLE snapshot 读取
`current_setting('server_encoding')`、有 sentinel 的 parent/child `COUNT(*)` 与每个 Text child 的
`COALESCE(MAX(LEAST(COALESCE(octet_length(...), 0), 257)), 0)`。每项原生 receipt 保留固定 SQL/arguments、列 OID、单行结果、SELECT status 与
connection；总 receipt 再绑定 request/output/source identity、qualification 与 profile。carrier 提交前独立重推 closure、
固定读取和 DataRow/batch/total 算术；Text width reply 是 PostgreSQL `integer` OID。普通 Collect 计 carrier 行；S13
Unnest 按 `P*C`（LEFT 为 `P*max(1,C)`）及实际最终 flat fields 计行。UTF8、64/16 source bound、child total、Text 256
或任一身份/算术不符都拒绝。

## 8. 交接

| 片 | 从 S12 接手 |
| --- | --- |
| S13 | 同一谓词；只扩展 admit 侧（`postgres_rows` 上最终平面的 Unnest）；所有门不变 |
| S14、S15 | 扩大 `project_result_binding.CHILD_KINDS` 即同时打开准入 |
| S16 | 可空容器的 count 单元格与多个 collection 字段的真实正例 |
| S17 | 移除 S11 的 IPC hunk 之后，重新见证 G-save 仍成立 |
| S18 | 删除 `save()` 中的 `_collection_entry` 调用；打开 `describe_compiled_binding`；没有 G-publish 需要移除 |
| S19 | 移除 `accept_saved_read` 中的 G-read（P-GREAD） |
| S20 | 复核 G-relay、G-R2 与路线准入；全组合下的资源与取消 |

## 9. B4 验收边界

S12 已移除保留到本片的 template gate；公开 live 和 loaded bundle 的准备不连接数据库。
保存、断源读取和 relay 的入口门继续属于各自后续片，template 可构造不意味着它们已开放。
最终 B4 必须核对真实 nested/flat-Unnest 运行、preflight 拒绝、取消/cleanup、exact-wheel
D71.11、installed product consumer、权威 Gate 2 与自然 CI；开发 focused 结果不替代这些证据。


## Current bounded execution closure

The retained pre-S12 template refusal is removed; execution still checks the
complete collection operation inventory before route/workspace/sink effects.
The source-bound preflight uses exact lowered Collect/Unnest occurrences and
BoundField identities, a fixed UTF8/count/Text-byte query set, and a receipt
bound to the request, output, connection, qualification and read-only snapshot.
Before the carrier executes, it rederives the domain and arithmetic. For a
final-flat Unnest, each final field must trace to that exact JOIN output; its
rows limit applies to expanded top-level rows, including LEFT placeholders.
Source and compiled paths share these checks, with no runtime source reload.

Local focused and source SDK checks remain development evidence. The batch's
exact-wheel PostgreSQL checks, authoritative validation and natural exact-head
CI must complete before this candidate is published. Save/R1/export and R2/relay
remain closed at their existing entry gates; S17 opens only private IPC.
