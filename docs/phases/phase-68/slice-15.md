# Phase68 Slice15：持久临时流式交付与合作 sink 提交

S15 CANDIDATE; completed only after closure。基线为 S14 published head
`d9646b574509aff9d0dbfab98a29a25ab97ff6bf`，自然 CI37364275901/push/main/attempt2（attempt1 在托管运行器分配阶段失败；
经用户授权一次完整重跑，两次 attempt 均不改标签）。本文只描述候选合同；当前存储/sink/原生/安装验收、精确 Git tree、
普通 FF 发布、自然 exact-head CI 的全部消费者和 owned cleanup 共同激活完成。证据属于独立 S15 实例，不合并任何已闭合计数。
S16 NEXT / NOT STARTED / separate dispatch required。

## 范围与选定机制

S15 把已提交的已保存 occurrence 增量交付给一个独立持久的参考合作 sink：只披露 S12/S14 已提交、连续、受检的不可变
checkpoint 窗口（或固定 S13 consumer 的实际 `Delivery`），每个 occurrence 在 sink 自己的 SQLite 事务中物化为一行精确
typed 行，效果身份稳定、同键异值显式冲突，回复丢失后显式查询与同身份重提，本地按 S11 围栏记录 sink 观察并派生连续
确认前沿。一个私有协调器（`project_job_delivery`）位于现有 job store 之上，参考 sink（`project_job_sink`）是另一个私有
目录与数据库。效果是临时的：之后的 source/transaction 失败不撤销它们，不是完整查询成功。没有 XA/共识、任意 callback
exactly-once、网络服务、connector 平台、source 写入、任意 SQL、复制/故障转移、迁移、S16 整代发布或 S17 调度/GC；
普通交付不需要 R2 K-provider。

## 显式 v5 工作区

v1–v4 的创建、打开、schema 与语义不变。只有显式 `create_workspace(..., format=FORMAT_V5)` 创建
`pietto.job-workspace.v5`：features 精确为 `["result-chunks", "saved-replay", "extraction-resume", "cooperative-delivery"]`，
user_version 5，schema = S11–S14 表（不变）+ 封闭 S15 表。能力只按 `supports(workspace, "cooperative-delivery")` 判断
（否则 `WORKSPACE_DELIVERY_FORMAT`）；S12/S13/S14 帮助函数本已按 feature 判断，在 v5 上不变。没有升级、ALTER、导入或
sidecar；已发布 S14 运行时（存档 wheel02 模块字节）打开 v5 以 `WORKSPACE_FORMAT` 在 SQLite open 前拒绝且目录不变。
身份类别新增 `stm-`（stream）、`sts-`（stream session）、`sti-`（stream issuance）、`snk-`（sink 实例）、`skc-`（sink 提交）。

| 表（v5，STRICT、只插入） | 内容 |
| --- | --- |
| `stream` | 一个 generation 对一个 sink 命名空间实例的唯一交付登记：job、generation、binding、route、输出合约、坐标方案、行布局 layout、sink、namespace、epoch、保留合同、purpose、publisher；`(generation, sink, namespace, epoch)` 唯一 |
| `stream_window` | 窗口链：ordinal、previous（首个为 NULL，否则 ordinal−1）、精确 checkpoint、该 checkpoint 的 S12 retention（唯一）、`[start, stop)`；`(stream, previous, start)` 外键指向前一窗口的 `(stream, ordinal, stop)`，首窗口 start=0，stop=checkpoint 连续 frontier |
| `stream_session` | 会话 ordinal（最新者取代旧者）、打开时派生前沿 position、非秘密 sink 接受描述（accepted_at、seconds、purpose）与读取 batch_rows |
| `stream_issuance` | 在任何 sink 接触之前提交的本地意图：session 内 ordinal、窗口 ordinal 或 S13 `dlv-`（二选一，`delivery` 唯一）、`[start, stop)`、按序效果 digest 的 sha256（载荷对应，不是成功） |
| `sink_observation` | 每个 occurrence 至多一个精确确认：position、issuance、session、basis（REPLY/QUERY）、status（COMMITTED/DUPLICATE/PRESENT_MATCHING）、sink 提交身份与序号、行 digest；`(stream, commit)` 唯一 |
| `stream_retirement` | 显式退役：退役时的前沿；同一事务对每个窗口 retention 插入 S12 `retention_release` |

新 operation kind：`register_stream`、`adopt_window`、`open_stream`、`issue_stream`、`confirm_sink`（ACTIVE 围栏）与
`retire_stream`（控制围栏）。本地 sink 确认前沿只由观察派生：位置 0 与 2 已确认、1 缺失时为 1。

## 独立参考 sink

私有目录含 `sink.json` 信封与 `sink.sqlite`；显式 `create_sink(root, *, namespace, epoch, retention_seconds)` 与
`open_sink(root, *, expected_identity)`、`describe`、`submit`、`query`、`close`。复用工作区的规范路径、私有对象检查、
存储 profile 资格（同一合格 Linux/ext4/SQLite 构建，WAL/FULL）与连接设置，但拥有自己的连接、APPLICATION_ID 与封闭 schema，
从不与 job store 共享事务或 ATTACH。未知格式/身份在 SQLite 之前拒绝；没有完整信封的既有目录从不被初始化。

一个实例就是一个命名空间实例 `(namespace, epoch)` 加一个不可变有限保留合同
`{"format":"pietto.sink-retention.v1","retained_until":T,"seconds":N}`，创建时固定，写入信封与单例行并在每次打开时比较。
物化效果表 `effect(workspace, generation, position, layout, payload, digest, commit_identity, sequence, committed_at)`
以 `(workspace, generation, position)` 为主键，只插入：

- `submit`：先检查规范 JSON、上界、精确 typed 形状（字段数、规范标量名↔S06 atom 种类、非空性；坐标宽度），以及实例/命名空间/
  epoch/保留合同；`BEGIN IMMEDIATE` 后在事务内再查保留期限，然后直接 INSERT（主键裁决，没有 INSERT OR IGNORE，没有 Python
  先查后写）。主键冲突时读取已存行：layout 与 payload 逐字节相等 → `DUPLICATE`（返回原提交记录，不插入），否则 `CONFLICT`
  （不覆盖）。只有 COMMIT 返回后才回复 `COMMITTED`；COMMIT 不确定则退役句柄（`SINK_COMMIT_UNKNOWN`）。每个 occurrence 一个事务。
- `query`：`PRESENT_MATCHING`、`PRESENT_CONFLICT`、`ACTIVE_NOT_FOUND`、`RETENTION_EXPIRED`、`UNAVAILABLE_OR_UNKNOWN`（实例、命名空间、
  epoch 或保留合同不同）；过期或被替换的数据库从不报告为未找到。

所有者是持久的 sink 数据库及其库代码，任何合作进程以新鲜访问打开；生产代码没有进程适配器、RPC、守护进程、CLI 或插件注册表。

## 效果身份与精确载荷

效果键为 `(sink 实例, namespace, epoch, 源 workspace, generation, position)`；position 只来自受检读取。attempt、checkpoint、
chunk、batch、session、consumer、operation、大小、pid、路径或载荷哈希都不是 occurrence 身份；等值的两个位置是两个效果，
重试同一位置是一个。sink epoch 标识目的地实例，job publisher epoch 只围栏本地元数据，两者不混用。

layout（每个 stream 一次，Arrow-free）：`pietto.sink-layout.v1`、输出合约 digest、有序字段 `[ordinal, label, kind, 规范名,
nullability, meaning law]`、multiplicity 与坐标方案。payload（每个 occurrence）：`{"coordinates": [...]|null, "values": [...]}`，
每个值是受检 batch `to_pylist()` 的 S12 `coordinate_wire`（S06 atom：float 位、Decimal 元组、datetime iso+fold、UUID 字节、
True≠1、NULL），没有第二个标量解释器；与 batch 布局、偏移、原生载体和 IPC batch 数无关，producing attempt 只是出处。
digest = 规范 `[layout, payload]` 的 sha256，只作对应校验；sink 与客户端比较完整文本。效果 ≤ 8 MiB，一次发出 ≤ 16 MiB，
在任何效果之前检查。

## 新鲜授权

`accept_window(workspace, job, generation, *, checkpoint, purpose, route, values, trust…, seconds, batch_rows)` 是读取授权：
以新鲜调用方信任输入经 S12 `stored_binding` 重派 binding，typed 值逐值相等，`compiled_output` 的合约与方案等于 capture 行，
checkpoint frontier 由 checkpoint 规则重算（`checkpoint=None` 只用于登记）。`accept_sink(sink, *, instance, namespace, epoch,
retention, purpose, seconds)` 是提交/查询授权：从打开的 sink 所有者重新读取描述，与调用方独立期望比较；截止同时受保留合同
`retained_until` 约束（续期会话不续期合同）。两者都是进程内、按对象登记、pid 绑定、不可复制、墙钟+单调双重截止，
读取前、解码后、每次发送前与每次本地写入时复核；只持久化非秘密描述。同址声明、不透明身份、旧回复或 source 资格都不能铸造它们。

## 窗口、发出与临时交付

- `register_stream(publisher, window, sink, *, operation)`：每个目的地实例与 generation 唯一一次（`STREAM_EXISTS`）；恢复以
  `find_stream` 重新打开，从不以替换登记规避冲突。`open_stream(publisher, stream, sink, *, window=None, operation)` 在派生前沿处
  新建会话，较旧会话此后不能发出、确认或采纳。
- `session.adopt(window, *, operation)`：首窗口从 0 开始；之后只接受同 generation 的已验证扩展（最新窗口成员保持、ordinal 更大、
  frontier 不变小），且仅当本地确认前沿已连续到上一窗口 stop；保护（S12 `_retain`）与窗口行原子写入。重放同一 operation 只
  返回历史事实，不是新授权；空洞之后的岛屿不进入窗口。
- `session.next(rows, *, operation)`：从派生前沿（不是最后发出位置）读取，经 S13 `_rebatch` 的同一有界受检成员切片，派生 payload，
  然后在一个 ACTIVE 围栏事务中复核最新会话、最新窗口与其保护、start 等于派生前沿、本会话上一发出已全部确认，再插入
  issuance——之后才接触 sink。一个待确认批次；已确认位置标为完成，此前发出但未确认的位置标为 prior。窗口耗尽返回
  `WAITING_FOR_COMMITTED_CHECKPOINT`（带窗口、前沿、观察终点、空洞、完整行覆盖与空结果的已验证 schema），不是 source EOF 或发布；
  位置 0 的空洞不是空结果成功。
- `session.bridge(delivery, *, operation)`：实际 S13 `Delivery`（本进程、待确认、同 generation、读取授权有效）走同一载荷函数并
  发出引用该 `dlv-` 的 issuance；`session.acknowledge(issued, *, operation)` 只在该 Delivery 每个 occurrence 都已持久确认后调用原
  S13 显式确认。崩溃于两者之间时重投的相同 occurrence 已确认，不再发送。无关的 R1 游标不证明任何 sink 效果。
- `relay(session, capture, *, rows, **window)`：一个所有者/publisher 的一步同步编排。存在未决批次 → `BLOCKED`，不再拉取 source；
  先交付已采纳窗口；只有窗口耗尽时才拉取一个受检 source 批次（S12 stage+publish），并以新鲜读取授权采纳为下一窗口。
  source 与 sink IO 都在 job store 写事务之外。

## 提交、回复、查询与本地确认

`session.send(issued)` 对每个未确认 occurrence 只做一次动作，每次之前复核授权、ACTIVE、当前 publisher/会话与保护：原始提交；
或对此前发出且结果未知的 occurrence 做一次查询，只有精确实例报告 `ACTIVE_NOT_FOUND` 时才以同一键与载荷重提一次。
`session.reconcile(issued)` 对本进程中结果仍未知的 occurrence 做一次查询与至多一次同身份重提；仍未知则保持未解决，等待下一次
显式调用。回复是合作所有者给出的数据：目的地、键、行 digest、提交记录与保留主体逐项校验，不是可重开访问的授权。丢失的回复
保持 UNKNOWN，之后的查询只是新的观察（basis QUERY），从不把旧回复改写为已收到。

`session.confirm(issued, *, operation)` 复核围栏、最新会话、授权与保护，在一个事务中追加观察与 operation 结果；重复的匹配观察不
重复计数，冲突或外来观察拒绝。本地 COMMIT 不确定则退役工作区，以新句柄查询原 operation，不因本地确认丢失而重发。sink COMMIT、
收到回复、本地观察 COMMIT、S13 确认、source EOF、完整 capture 与 S16 发布彼此分离。取消或过期后可能已有外部效果而无本地进度：
外部事实与本地不确定分开保留，没有补偿删除或跨库回滚。命名空间/epoch/保留合同改变或过期时，原恢复合同不可用；空的替换 sink
不证明旧效果不存在，不自动在新 epoch 重建效果，不重置本地前沿；历史观察以其原上下文可查。

## 保留、取消与资源

每个采纳窗口以 S12 retention 保护其精确 checkpoint；ACK、过期或本地 close 都不释放任何东西。`retire_stream(publisher, stream, *,
operation)`（控制围栏）只在没有任何已发出未确认 occurrence 时插入退役行并释放全部窗口 retention（仅元数据，不删文件）；否则
`STREAM_OBLIGATION_UNRESOLVED` 并保持保护。两个数据库不能原子退役，S15 不删除 sink 记录。`stream_state` 只读给出前沿、已观察
区间、未解决区间、窗口及其释放状态、会话与 issuance，供 S16/S17 使用。读取前、解码后、发送前与本地写入时检查取消/截止/保护；
sink 在效果 COMMIT 时检查自己的保留期限；进行中的效果可能在取消期间提交，如实报告。有界：一个持有的已解码成员、一个待确认批次、
效果与批次上界、sink 预算/WAL/控制余量与 job store 的现有准入；SQLite 等待有界。

## 失败切点

| 切点 | 证据 | 持久结果 |
| --- | --- | --- |
| issuance COMMIT 前 / 后（回复前）/ 已发出未发送 | 真实 SIGKILL | 无 issuance / 有 issuance、无效果；新会话查询后以同一键提交 |
| sink 效果已插入未 COMMIT / COMMIT 后回复前 / 回复后本地确认前 | 真实 SIGKILL | 无效果 / 恰一个效果；新会话查询得到 PRESENT_MATCHING，缺失者同身份重提 |
| 本地确认 COMMIT 前 / 后（回复前） | 真实 SIGKILL | 无观察 / 观察存在，查询原 operation，从派生前沿继续 |
| sink 确认后 S13 确认前 | 真实 SIGKILL | 重投的 occurrence 已确认，不再发送，随后原 S13 确认 |
| 两进程并发提交同一键 | 真实进程 | 恰一个效果；另一方 DUPLICATE（同提交记录）或 CONFLICT |
| 回复丢失、busy、IO、ENOSPC、close、预算、COMMIT 歧义、过期、取消、释放 | 注入 | 拒绝新进度；已提交的外部效果不回滚；无无界重试 |

真实 SIGKILL 与注入错误是不同证据，都不是断电证明；设备/OS sync 诚实与私有合作用户边界是显式前提。

## 验证

核心环境没有 Arrow 与数据库：纯键/区间/前沿法则在所有主机运行；v1–v5 与 sink 边界、typed 效果、窗口链、发出、前沿空洞、
部分批次与换批量、丢失回复与有界对账、冲突、授权与时钟、注入故障、保护/退役、S13 桥、relay 背压与独立历史损坏在合格本地
profile 上运行，读取步为标注的 ARROW_FREE_REPLAY_STEP、行步为 ARROW_FREE_PAYLOAD_STEP（sink 自身事务、窗口、发出、确认、围栏与
校验器照常运行）；真实 SIGKILL 切点与两进程争用在注册的子进程中运行。真实 Arrow 由 `scripts/phase68_slice15_probe.py` 运行：
`suite` 在 Arrow-only profile 中以 SIMULATED_NATIVE_IO 捕获七标量（39/65）、重复值、空 schema 与迟到失败，并在 source 结束前把
已提交 chunk 中继到 sink，再由新进程以批 1/2/3/整体、S13 桥写入独立 sink，独立检查器直接用 pyarrow 解码 chunk 字节、以自己的
解码器读取 sink 行并对照 S12 字面 oracle，协调损坏（载荷、回执、epoch、保留、前沿、遗漏效果、身份）全部拒绝，存档 S14 wheel 拒绝
v5；`native` 在每条路线上以 R2_seven 39_values 运行联合历史：R2 捕获在 source 结束前中继进 sink A、SIGKILL、新进程 S14 恢复、
Arrow-only 新进程采纳下一窗口进同一 sink（旧效果不重复）、删除源库、无驱动 Arrow-only R1 桥进新 sink B 与再次进 sink A（已全部
确认，不发送）。

| 后续 | S15 提供 | S15 不实现 |
| --- | --- | --- |
| S16 | 每 stream 的派生确认前沿、窗口 checkpoint 链、未解决区间、完整行覆盖事实与 sink 提交记录 | 整代原子发布、通知丢失恢复 |
| S17 | 窗口 retention 引用、退役释放、`stream_state` 义务、sink 预算与有界资源 | 调度、并发 GC、多 job 准入 |
