# Phase68 Slice12：不可变结果 chunk、committed checkpoint 与 retention 基础

S12 CANDIDATE; completed only after closure。基线为 S11 published head
`383747bbf5c4fe3142a01a15cef3fa34543015bf`，自然 CI37188868480/push/main/attempt1。
本文只描述候选合同；当前存储/原生/安装验收、精确 Git tree、普通 FF 发布、自然 exact-head CI 的全部消费者和
owned cleanup 共同激活完成。证据属于独立 S12 实例，不合并任何已闭合计数。S13 NEXT / NOT STARTED / separate dispatch required。

## 显式 v2 工作区

S11 v1（`pietto.job-workspace.v1`、user_version 1、无 S12 表与目录）仍是 `create_workspace` 默认值，其创建、打开、
元数据语义与未知格式拒绝不变。S12 只在显式 `create_workspace(..., format=FORMAT_V2)` 时创建
`pietto.job-workspace.v2`：信封 `(format, features)` 必须正好是 `(v2, ["result-chunks"])`，user_version 2，
精确 schema = S11 表 + 封闭 S12 表，另有私有目录 `chunks/` 与 `staging/`（0700）。打开时先按已知版本表核对信封，
未知/未来/不匹配的 format-features 组合在任何 SQLite open 前拒绝；已知版本再做版本专属对象与 schema 检查。
v1 永不因打开或调用 chunk API 而升级；所有 S12 capture/引用变更要求 v2（否则 `WORKSPACE_CAPTURE_FORMAT`）。
没有自动迁移、ALTER、复制历史 job 或修改 S11 存档。已发布 S11 运行时打开 v2 以 `WORKSPACE_FORMAT` 拒绝且目录不变。

## 生产者到读取者

| 步骤 | 拥有者/数据 | 检查 |
| --- | --- | --- |
| 生产 | 真实 S10 owner（PG rows、PG ADBC、MySQL）的 `next(owner)`，即 `ExecutionPayloads.accept` 产出的 ManagedBatch | 类型、batch 绑定即 `owner._payloads.binding`，owner 行/批计数恰好前进本批 |
| refined 谱系 | `Enumeration.last_committed`（commit_page 内一行桥接） | 同一 enumeration 的 CheckedPage，行数一致，progress 行数等于已观察位置 |
| 位置 | 会话按受检流分配 `[observed, observed+rows)` | 调用者不能提供 first/last/count/max(key) |
| 空结果 | owner 已关闭、编译 outcome source 为 EOF、未观察任何行 | 单独的 `[0,0)` schema chunk（terminal EOF、0 批），不制造数据行 |
| 迟到非法值 | owner 在 payload 检查处抛错，不返回该批 | 该批不暂存；先前 chunk 不变；end 记录已观察位置与 owner 自身终态 |
| 文件 | 规范描述符 + 未改动的 S10 `encode_ipc` 帧（expected_rows = 本 chunk 受检行数） | 有界、O_EXCL staging、fsync、link 不覆盖、只删本次 staging、inode/ctime/nlink 复核、目录 fsync |
| SQLite | `publish_chunk`：S11 围栏（ACTIVE）、attempt 未终结、capture attempt/publisher 一致、不重叠、上限、提交边界 stat 复核；插入 chunk、新不可变 checkpoint、完整成员与 frontier | 单事务；COMMIT 歧义为 `STORE_COMMIT_UNKNOWN`，连接退役，之后用新句柄查询 |
| 读取 | 新鲜信任 → load_job/bind_record → `compiled_output` → `bind_stored_output`（stored-chunk 用途，protocol nullability 未知）→ bind_arrow | 合约身份 = capture = 描述符 = IPC 头；文件 fstat/大小/sha256/描述符逐字段；`open_ipc` 全值校验；坐标数量与方案 |

仅存在文件从不等于已捕获：只有与文件一致的已提交 chunk 行才是。会话只能由 `begin_capture` 针对一个 publisher、
一个未终结 attempt、其新鲜 binding、route/isolation 与一个尚未交付任何批的 owner 建立；一个 generation 只绑定一次原始
capture attempt，后续 attempt 只是历史，不能追加重新求值的结果（跨 attempt 续接由 S14 授权）。

compiled 根没有源语言可移植合约文档，因此原 IPC owner 对 `CompiledSQLPlanVerification` 合约使用
`pietto.compiled-result-contract.v1` 身份：pinned root、查询地址、乘性与完整公共形状（序号、标签、规范类型、可空性、
Timestamp/UUID 含义）的规范 JSON 的 sha256。源语言合约仍用原可移植导出，帧格式与检查不变。

## chunk 文件 v1

`>16sQQ32s` 头：魔数 `PIETTO-CHUNK1`、描述符长度、帧长度、sha256(描述符‖帧)；随后是 ASCII 规范 JSON 描述符与原
`PIETTO-IPC1` 帧。描述符字段固定：format `pietto.result-chunk.v1`、workspace、job、generation、attempt、binding record、
chunk、kind、contract、start、stop、rows、batches、terminal（仅 schema chunk 为 EOF）、coordinates（refined 为逐行
`pietto.coordinate-atoms.v1` 原子：float 位、Decimal 元组、datetime fold、UUID 字节；ordinary 为 null）、frame_bytes、
frame_sha256。名称为 `chunks/<chk-id>.chunk`，staging 为 `staging/<chk-id>.staging`。上限：文件 16 MiB、描述符 2 MiB、
每 chunk ≤ 4096 行与 64 字段、每 generation chunk/checkpoint ≤ 256、每会话未发布暂存 ≤ 8、工作区 chunk ≤ 65536、
retention ≤ 16384；读取先 fstat 定界再分配。内容 digest 只保护文件边界，私有且从不作公共身份；同字节可属于两个合法 chunk。

## 失败切点

| 切点 | 结果 |
| --- | --- |
| K1 staging 部分写入 / K2 完整写入未 fsync / K3 fsync 后未 link | 无 committed 引用；先前 checkpoint 完好；残留 staging 仅被分类 |
| K4 最终名已持久、元数据前 | 孤儿最终文件，不是进度；打开不收养 |
| K5 行已插入、COMMIT 前 | 无部分成员/checkpoint；孤儿文件 |
| K6 COMMIT 后、回复前 / K7 回复已送达 | 新查询恰好一个效果；同 id 不同请求为冲突 |
| 注入 EIO（文件 fsync、link、目录 fsync）、短写、预算拒绝 | `CHUNK_IO` / `CHUNK_ORPHANED_IO` / `WORKSPACE_BUDGET`；不产生引用 |

真实 SIGKILL/回收与注入 IO 错误是不同证据，二者都不是断电证明；设备/OS sync 诚实是外部前提。
已提交引用指向缺失/截断/替换/损坏文件时读取显式拒绝（`CHUNK_MISSING/SIZE/DIGEST/OBJECT/DESCRIPTOR`），历史不缩减、不重建 frontier。
陈旧写者至多留下自己的未引用文件，不能发布元数据、覆盖已提交文件或删除他人文件。

## committed 覆盖与分层终态

区间约定唯一：零起点半开 `[start, stop)`。每次发布生成不可变 checkpoint：完整成员集 = 上一 checkpoint 成员 + 新 chunk，
frontier 是自 0 起的最大连续前缀（不是 max(stop)），缓存列由读取与独立校验器重算核对。必需历史：受检流产生
`[0,2)`、`[2,4)`、`[4,6)`，先发布第一与第三个，committed 为 `[0,2)`、`[4,6)`、frontier 2；新进程读取者仍见 2；
同一未崩溃会话发布缺失区间后，只有原子成员/checkpoint 更新产生 6。

快照分别投影 committed 区间、frontier、空洞、观察终点（`capture_end` 或 UNKNOWN）、会话所见 owner 终态、attempt 终态及
其 source/transaction/delivery/cancel/cleanup/remote_source_use_end（无终态时 UNKNOWN），完整性 RECORDED，只有逐一读取并校验
全部成员后才为 VERIFIED；publication 与 consumer ACK 为 `NOT_IMPLEMENTED_BY_S12`。没有新的成功标志；source EOF 加空洞不是完整捕获；
本地 checkpoint 不声称远端 COMMIT。S10 存储 outcome 的 `local_durable_result` 仍为 `NOT_IMPLEMENTED`，S12 不改写它。

## 读取与 retention 基础

`checkpoint_snapshot` 是一次读事务的不可变成员快照（不保护、不读文件）；`retain_checkpoint` 在一次 S11 围栏写事务中
插入 `ret-` 引用并返回该 checkpoint 的精确成员快照；`release_retention` 只写元数据，可由同 job 的后续 publisher 调和，
外部 job 拒绝，无 TTL/时钟释放。受保护集合 = 每个 generation 最新 checkpoint 成员 + 未释放 retention 的成员；
`classify_files` 只报告 referenced/missing/orphans/staging/foreign。S12 不删除 committed chunk、不跑 GC。
`SnapshotReader` 只持有成员快照与自己打开的只读目录描述符，不持有 publisher 或 SQLite 连接；返回的受检 chunk 是低层存储读取，
不是 R1 交付。读取关闭、publisher 变化或本地 owner 关闭都不推断远端静止。

## 资源、进程与保密

预算计入 SQLite/WAL/SHM、信封、锁与 chunk/staging 文件（硬链接按 inode 计一次），数据准入保留控制余量；
free-space、journal_size_limit、max_page_count 都不是物理硬上限，ENOSPC 可能阻止失败记录，此时保留 UNKNOWN。
只有登记的 spawn 子进程打开自己的工作区并 claim 自己的 publisher；会话、publisher、工作区与读取句柄绑定 pid，fork 继承使用拒绝。
保护边界仍是私有 OS 用户与合作产品 owner；不防 root、同用户直接改写、磁盘镜像回滚、任意 VFS 或被盗凭据，不声称 tamper-proof。

## 验证

核心环境没有 Arrow：普通测试覆盖纯帧/坐标/frontier 法则（任何主机都运行）、v1/v2 边界、文件协议与注入故障、
fence/取消/陈旧 publisher/外部句柄/替换 inode、空洞与不可变 checkpoint、幂等与提交歧义、retention、独立历史重放损坏，
以及真实 SIGKILL 切点、新进程读取与 fork 拒绝；存储机制使用标明的无 Arrow 存储步（合成帧，位置按受检规则分配）。
非合格运行时上这些存储测试断言显式拒绝。执行 profile（`scripts/phase68_slice12_probe.py suite`）在真实 ExecutionPayloads/Arrow/IPC 上
覆盖七标量（39/65 精度）、空 schema、迟到非法值、满尾批与 VERIFIED 读回；原生桥（`bridge`）在 PG/MySQL 三条路线 × live/bundle ×
source/installed 上捕获 A（乱序空洞）、B、A_again、empty、A_late（首个 chunk 后取消），由新鲜 source-free 进程读取后交给 S10
原字面 oracle 与 S12 独立检查器（静态备份 + chunk 字节 + 直接 pyarrow 解码 + 协调损坏）；`representatives` 以锚定替换让 S10 case worker
捕获并读回 guarded/refined/七标量/空结果代表。

| 后续 | S12 提供 | S12 不实现 |
| --- | --- | --- |
| S13 | `checkpoint_snapshot`、`retain_checkpoint`、`SnapshotReader.read/verify`、`stored_output`；chunk/checkpoint/checkpoint_member 行与描述符 | 消费者 offset、重分批、R1 交付恢复 |
| S14 | capture（kind/contract/scheme）、refined 坐标原子与 frontier/空洞、capture_end | 新 Enumeration 导入 frontier、抓取未捕获后缀 |
| S15/S16 | 不可变 checkpoint 身份与可查询 operation | sink effect、ACK、整代发布 |
| S17 | retention/retention_release、`protected_chunks`、`classify_files` 与 publisher 来源 | 调度、并发 GC、reader/GC 原子交错 |
