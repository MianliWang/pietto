# Phase68 Slice13：R1 已保存结果恢复与新鲜读取授权

S13 CANDIDATE; completed only after closure。基线为 S12 published head
`d4d5f157df739a92e310ad23ac156ba4f66cb4cc`，自然 CI37229699158/push/main/attempt1。
本文只描述候选合同；当前存储/原生/安装验收、精确 Git tree、普通 FF 发布、自然 exact-head CI 的全部消费者和
owned cleanup 共同激活完成。证据属于独立 S13 实例，不合并任何已闭合计数。S14 NEXT / NOT STARTED / separate dispatch required。

## 范围

R1 只恢复对已捕获 occurrence 的消费：从一个不可变 S12 checkpoint 读取已保存 chunk，绝不重新执行、查询、
重新资格化或重新求值 source/guard。S14 才恢复 source 提取；S15 拥有合作 sink 效果与 ACK 对账；S16 拥有整代原子发布；
S17 拥有调度与并发 GC。

## 显式 v3 工作区

v1（默认）与 v2（`result-chunks`）的创建、打开、schema 与语义不变。S13 只在显式
`create_workspace(..., format=FORMAT_V3)` 时创建 `pietto.job-workspace.v3`：信封 `(format, features)` 必须正好是
`(v3, ["result-chunks", "saved-replay"])`，user_version 3，精确 schema = S11 表 + S12 表（不变）+ 封闭 S13 表，
私有目录同 v2。能力按封闭版本表的精确 feature 判断（`supports(workspace, feature)`），从不使用 `version >= n`：
capture/读取/retention 需要 `result-chunks`（v2、v3），全部 S13 调用需要 `saved-replay`（仅 v3，否则
`WORKSPACE_REPLAY_FORMAT`，v1/v2 文件与 schema 不变）。没有迁移、ALTER、导入存档 job 或绕过信封的 sidecar；
已发布 S12 运行时（存档 wheel01 模块字节）打开 v3 以 `WORKSPACE_FORMAT` 在 SQLite open 前拒绝且目录不变。

## S13 表（v3，STRICT、只插入）

| 表 | 内容 |
| --- | --- |
| `consumer` | `csm-` 身份、job、generation、精确 checkpoint、binding record、唯一 retention、scope（`complete_capture`/`committed_prefix`）、固定 extent、purpose、可选 `not_after`、publisher epoch/instance |
| `replay_session` | `rps-` 身份、consumer、ordinal（逐个递增，较新会话取代旧会话）、打开时的 position、非秘密 acceptance 描述（accepted_at、seconds、batch_rows）、publisher epoch/instance |
| `issuance` | `dlv-` 身份、consumer、session、session 内 ordinal、`[start, stop)`、publisher epoch；`(identity, session, consumer, start, stop)` 唯一 |
| `acknowledgement` | issuance、consumer、session、`[start, stop)`、`previous`（start 为 0 时 NULL，否则等于 start）、publisher epoch |

acknowledgement 的范围以外键等于其 issuance 范围；`(consumer, previous) → acknowledgement(consumer, stop)` 自引用外键加
`(consumer, start)`、`(consumer, stop)` 唯一，使已确认区间构成从 0 开始的单一无缝链：无空洞、无重叠。进度是派生值
（最大 stop），没有缓存列；打开会话与独立校验器都重算整条链。consumer 的撤销/释放就是对其 retention 的显式 S12
`release_retention`（原 owner、控制围栏）；本地 close 不写任何持久记录。新 operation kind：`register_consumer`、
`open_replay`、`issue_delivery`、`acknowledge_delivery`（均为 ACTIVE 围栏）。

## 新鲜读取授权

`new_consumer()` 先分配 `csm-`。`accept_saved_read(workspace, job, generation, *, checkpoint, consumer, scope, extent,
purpose, route, values, expected_pin, accepted_producer, accepted_compatibility, seconds, batch_rows)` 在不导入
Arrow 的情况下：用新鲜调用方信任输入经 S11 `load_job` 与 S12 `stored_binding` 从存储向量重派 binding 并核对 generation
描述；调用方 route 必须等于 generation route；调用方 `values` 经 S10 `bind_values` 与 S11 typed wire 必须逐值等于存储向量
（True≠1、-0.0≠0.0、精确 Text）；`compiled_output` 的合约身份与坐标方案必须等于 capture 行；命名 checkpoint 必须存在，
其按 checkpoint 规则重算的 frontier 必须等于 extent。结果是进程内、按 pid 绑定、按对象身份登记的
`SavedReadAcceptance`：不可复制、不可 pickle；任何存储布尔、同址 pin、旧 receipt、复制对象或恢复的会话记录都不能铸造它；
持有身份字符串不认证任何人。这是私有合作用户边界内调用方接受的读取能力，不是组织策略合规证明，也不是 source 权限；
它不授权 R2 attempt。

有效期 1–86400 秒：仅当可信主机墙钟 `time.time()` 小于 accepted_at+seconds 且 `time.monotonic()` 小于会话内
截止时间时有效，墙钟回拨不能延长；跨进程只用当前时间加新鲜 acceptance，不声称防回滚时钟或磁盘镜像重放。
`batch_rows`（1–4096）是读取上限。持久化的只有非秘密描述：consumer 的 purpose/scope/extent/not_after 与 session 的
accepted_at/seconds/batch_rows。过期、外部或复制的 acceptance、已取消 job、已释放 retention、过期 consumer、
purpose/scope/extent/consumer/checkpoint/generation/route/value/pin/producer/代码兼容性不符，均在任何 replay 行之前拒绝。
已交给调用方内存的数据无法被撤回（明确限制）。

## 状态机与固定范围

- `register_consumer(publisher, acceptance, *, operation, not_after=None)`：一个 ACTIVE 围栏事务内，consumer 不存在；
  事务内 `_retain`（S12 retain_checkpoint 共用）保护**精确** checkpoint；extent 由 S12 `_snapshot` 重算并等于 acceptance；
  `complete_capture` 要求 capture_end 已记录 source EOF、观察终点 N = extent、无空洞且至少一个成员（空结果即 schema chunk），
  这是行覆盖，不是远端事务成功；`committed_prefix` 是调用方接受的固定临时前缀（可为 0）。position 0 隐含。
- `open_replay(publisher, acceptance, *, operation)`：consumer 事实等于 acceptance、retention 未释放、未过期、checkpoint
  快照与覆盖事实重算、确认链从 0 连续且不超过 extent → position P；新会话 ordinal 为最大值加一，较旧会话此后永远不能
  issue/ack；重放的 operation → `REPLAY_REPLAYED`。从不跟随可变的“最新 checkpoint”，也不扩大范围。
- `ReplaySession.next(rows, *, operation)`：存在待确认交付 → `DELIVERY_PENDING`（不丢弃）；position 等于 extent →
  `SavedScopeEnd`；否则读取所需成员（每个成员先整块解码并按值校验，块内后缀损坏阻止任何前缀），切片、拼接
  （`pyarrow.concat_batches`）并经 S10 `manage_batch` 重新校验与拷贝，然后在一个 ACTIVE 围栏事务中复核最新会话/
  publisher/retention/过期、会话内无未确认 issuance、start 等于已确认 frontier、stop 不超过 extent，再插入 issuance。
  只有 COMMIT 已知后才把 `Delivery` 交给调用方；`STORE_COMMIT_UNKNOWN` 退役工作区且不暴露数据。
- `ReplaySession.acknowledge(delivery, *, operation)`：只接受本会话发出的那个对象；同一短事务复核围栏、最新会话、
  retention、过期、issuance 未确认且范围相同、start 等于 frontier，插入 acknowledgement 与 operation 结果——这是进度的
  线性化点。同 operation 同请求只返回已提交事实，请求不同为 `OPERATION_CONFLICT`。事务内没有 IO、解码或回调。
- `close()` 只释放读取描述符与缓存成员，不确认、不完成、不写持久记录。`consumer_state(workspace, consumer)` 是只读观察
  （取消、过期后仍可用），不重新打开读取。

`Delivery` 携带 `[start, stop)`、generation、checkpoint、consumer、新的 delivery/session/operation 身份、受检
`ManagedBatch`、refined 坐标原子与 `held_bytes`；occurrence 标签为 `(generation, position)`，物理 chunk 身份从不暴露。
`SavedScopeEnd` 的 `SAVED_SCOPE_EXHAUSTED` 只表示这个固定本地范围没有更多行：同时给出 scope、extent、派生确认位置、
本会话校验过的区间、实际校验的 schema（空 complete 才有；位置 0 的空洞为 None）、观察终点、空洞与 S12 原始 attempt 分层
（UNKNOWN 保持 UNKNOWN）。它不是 source EOF、整查询成功、sink 效果或整代发布。

## 不丢失与可重投

持久进度只是连续的已确认前缀。已发出未确认的区间保留为历史，可由后续会话以相同逻辑位置重新发出（新的 dlv-/rps-/op-
身份）。本地确认是调用方声明加本地 COMMIT，不验证外部 sink 效果，不声称任意外部效果 exactly-once。必需示例：
`[0,7)`，会话 A 批 2 确认 `[0,2)`、收到 `[2,4)` 后死亡；新会话 B 批 3 从 2 开始确认 `[2,5)`、`[5,7)`，持久链恰为 `[0,7)`，
A 的 `[2,4)` 仍是未确认历史；确认 COMMIT 后、回复前被杀时，新句柄查询原 operation 得到 position 4 并从 4 恢复。

## 内存与资源

每次 `next` 只持有所需成员加一个输出批，缓存一个已解码成员；切片可能保留整个父 buffer，`held_bytes` 如实计入
（不承诺零拷贝或进程 RSS 上限）。从不使用整代 `read_all`、全部解码 chunk 列表或完整 oracle 副本；`SnapshotReader.verify`
逐成员校验，不再累积全部表，也不缓存整代 PASS。重分批输出的 Arrow 类型只由 canonical kind 决定，家族载体只影响原生输入。

## 失败切点

| 切点 | 证据 | 持久结果 |
| --- | --- | --- |
| 注册 COMMIT 前 / COMMIT 后回复前 | 真实 SIGKILL | 无 consumer 与 retention / 查询得到注册、position 0 |
| 会话已注册未发出数据 | 真实 SIGKILL | 一个会话、无 issuance |
| issuance 已提交、调用方未见 / 已交付未开始确认 | 真实 SIGKILL | 未确认历史，新会话从原位置重投 |
| 确认行已插入未 COMMIT / COMMIT 后回复前 | 真实 SIGKILL | 无确认 / 查询得到确认，从其 stop 恢复 |
| 全部已确认、终态回复丢失 | 真实 SIGKILL | position 等于 extent，新会话立即终态 |
| 解码失败、读取与发出之间或发出与确认之间取消/过期/释放、陈旧 publisher/会话、COMMIT 未知、busy、预算、回滚失败、关闭失败 | 注入 | 拒绝新读取与进度，已提交状态真实，无删除 |

缺失、截断、交换、语义损坏或外部 chunk 从不导致跳过、源重取、重新捕获、截断确认历史或收养孤儿文件。真实 SIGKILL 与注入
错误是不同证据，都不是断电证明；设备/OS sync 诚实是外部前提。

## 验证

核心环境没有 Arrow：纯区间法则在所有主机运行；v1/v2/v3 边界、acceptance、注册原子性、会话取代、issue/ack、过期时钟、
取消/释放/过期的晚到交错、陈旧 publisher、COMMIT 歧义、busy/预算/回滚/关闭错误、独立历史重放损坏以及真实 SIGKILL 切点、
必需示例和双进程争用在合格本地 profile 上运行（其他主机断言显式拒绝），saved input 用 S12 标注的 Arrow-free 存储步，
replay 数据步为标注的 ARROW_FREE_REPLAY_STEP。真实 Arrow 由 `scripts/phase68_slice13_probe.py` 运行：`suite` 在原生捕获
profile 中用真实 ExecutionPayloads/Arrow/IPC 捕获七标量（39/65）、重复值、空 schema、迟到前缀与位置 0 空洞，并在新的
Arrow-only 进程中以批 1/2/3/整体、块内恢复、跨块拼接、pinned 空洞、损坏副本、晚到授权变化以及真实 SIGKILL 的必需示例与
丢失回复重放；`bridge` 在 PG/MySQL 三条路线、live/bundle、source/installed 上捕获后停止并删除源库，再由新的 Arrow-only 进程
（未安装驱动、零 socket 连接、零源语言入口）恢复，S10 原字面消费者读取 R1 恢复的行；`representatives` 以 v3 锚定补丁捕获 refined
代表并恢复坐标原子。独立检查器读取静态备份与 chunk 字节、直接用 pyarrow 解码并对照 S12 字面 oracle。

| 后续 | S13 提供 | S13 不实现 |
| --- | --- | --- |
| S14 | 不可变 consumer/checkpoint 绑定、scope 模式、`SavedScopeEnd` 分层与 R1 绝不访问源的边界 | R2 提取恢复、新 Enumeration 导入 frontier |
| S15 | `Delivery`（`[start, stop)`、occurrence 标签、dlv-/rps-/op- 身份）、`acknowledge` 的可查询 operation、`consumer_state` | sink 效果、ACK 对账、效果身份 |
| S16 | 固定 extent 与确认链 | 整代原子发布、通知丢失 |
| S17 | consumer retention 引用、`protected_chunks` 中的 consumer 保护、`held_bytes` | 调度、并发 GC、reader/GC 交错 |
