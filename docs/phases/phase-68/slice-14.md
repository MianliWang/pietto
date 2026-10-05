# Phase68 Slice14：R2 同版本提取恢复与持久 occurrence 覆盖

S14 CANDIDATE; completed only after closure。基线为 S13 published head
`a223d2e469fb941f7206b85467b66349d3075678`，自然 CI37275267364/push/main/attempt1。
本文只描述候选合同；当前存储/原生/安装验收、精确 Git tree、普通 FF 发布、自然 exact-head CI 的全部消费者和
owned cleanup 共同激活完成。证据属于独立 S14 实例，不合并任何已闭合计数。S15 NEXT / NOT STARTED / separate dispatch required。

## 范围与选定机制

S14 只恢复 source 提取：调用方显式请求、新进程、同一编译查询与 binding、重新取得真实保留源资格认证与 guard，
从位置 0 重新枚举完整 refined 查询，与冻结的已提交成员逐 occurrence 对账，补齐已提交空洞并抓取此前未请求的后缀，
再经现有 S12 文件持久化与 S11 围栏提交新 chunk/checkpoint。选定机制是 **verified ordered re-enumeration + occurrence
reconciliation**，不是任意持久 frontier 赋值：可能重读整个已保存前缀并对每页重新求值完整原生查询，不声称后缀复杂度或加速。
它不是自动整 job 重试/回退；没有 seek、未证明的 OFFSET、隐藏 COUNT、合成 ROW_NUMBER、哈希去重、Python 查询求值器、
CDC、快照保持器、远程租约或源端结果表。R1 仍不访问源；S15 拥有 sink 效果/ACK，S16 整代发布，S17 调度/GC。

## 显式 v4 工作区

v1/v2/v3 的创建、打开、schema 与语义不变。只有显式 `create_workspace(..., format=FORMAT_V4)` 创建
`pietto.job-workspace.v4`：信封 features 精确为 `["result-chunks", "saved-replay", "extraction-resume"]`，user_version 4，
schema = S11 + S12 + S13 表（不变）+ 封闭 S14 表，私有目录同 v2。能力只按封闭版本表的精确 feature 判断
（`supports(workspace, "extraction-resume")`，否则 `WORKSPACE_EXTRACTION_FORMAT`）。没有迁移、ALTER、sidecar 或存档转换；
已发布 S13 运行时（存档 wheel 模块字节）打开 v4 以 `WORKSPACE_FORMAT` 在 SQLite open 前拒绝且目录不变。

| 表（v4，STRICT、只插入） | 内容 |
| --- | --- |
| `extraction` | generation 主键、job、原始 attempt（唯一）、不可变 specification、初始资格描述、publisher epoch/instance；与 capture 行**同一事务**插入 |
| `continuation` | attempt 主键、job、generation、冻结前驱 checkpoint（可 NULL）、F、H、成员数、行数、publisher epoch/instance |
| `reconciliation` | attempt 主键、屏障时的新鲜位置 P、已匹配行数、publisher epoch |
| `continuation_end` | attempt 主键、generation、观察位置、source 终态、未发布 staged 数、覆盖 checkpoint（仅 EOF 且无缝时非 NULL）、epoch |

新 operation kind：`begin_extraction`、`begin_continuation`、`reconcile_extraction`（ACTIVE 围栏）与 `end_continuation`
（控制围栏）；续写 chunk 复用 `publish_chunk`。每个效果与其 operation 行在同一短事务中（S11 重放/冲突/查询律不变）。

## 初始 R2 基础（不追认）

`begin_extraction(publisher, attempt, owner, *, operation)` 需要 v4、已打开且已资格认证的 refined 编译 owner（与 attempt 同一
binding 对象、route、isolation；无已交付 payload；Enumeration 在位置 0）。它在同一 ACTIVE 围栏事务中插入 capture 行
（REFINED、合约、坐标方案）与 extraction 行，之后的 chunk 走不变的 S12 CaptureSession。

- specification（规范 JSON，恢复时重算并逐字节比较）：`pietto.extraction-spec.v1`、chunk 格式、坐标原子版本、kind、
  输出合约 digest、坐标方案（choice/order/keys/directions/erasure/prefix/rule）、route、isolation，以及 refinement 的**有序**
  完整 source-use 需求向量（namespace、name、provider、version、revision、registry、definition、token 列、role、provider guarantee）。
- 资格描述：S10 只读桥 `compiled_source_description(owner)` 在 `verify_compiled_owner`、owner 自己的资格对象 `.verify(owner)`
  与 admissions `.verify` 之后，只投影 owner 已检查的稳定事实：route、isolation、role、environment、初始原生 context 去掉新鲜字段
  （PG/ADBC 的 backend pid、事务 id、server 地址/端口、postmaster 启动时间；MySQL 的 CONNECTION_ID）、有限闭包（PG：roots 与
  每个 catalog 回复的 kind/arguments/rows，含 OID；MySQL：对象 key/kind/engine/列/原生定义、edges、security）以及每个 source
  观察（registry 行、definition、token 类型、碰撞行、schema 元数据、collation、终态；route 与 role 只在顶层出现一次）。会话 id、连接、receipt、回调与 admission
  对象从不序列化；超过 4 MiB 拒绝。

普通 `begin_capture` 在 v4 上仍是单 attempt，从不获得续写权；v2/v3 或没有 extraction 行的 capture 请求 R2 以
`EXTRACTION_UNKNOWN` 拒绝，普通捕获与 R1 照常。初始基础提交前崩溃则没有 capture，也就没有 R2 权利（后续 attempt 是新的初始捕获）。

## 新鲜恢复授权

`accept_recovery(workspace, job, generation, *, checkpoint, purpose, values, expected_pin, accepted_producer,
accepted_compatibility, seconds)`：以新鲜调用方信任输入重派 S10 template/binding，typed 值逐值相等，要求 refinement 与
extraction 行，重算 specification 并逐字节比较；`checkpoint` 必须等于该 generation **当前最新** checkpoint（无 checkpoint 时为
None），否则 `CONTINUATION_PREDECESSOR`；在打开任何源之前读取并校验每个已提交成员的字节、描述符、producing attempt 与完整
IPC 值（损坏即拒绝，从不重取修复）。结果是进程内、purpose 限定、pid 绑定、按对象身份登记且不可复制的
`RecoveryAcceptance`（1–86400 秒，墙钟与 monotonic 双重截止，成本前后与写入时复核）；它持有新鲜 binding 供调用方
`open_attempt` 与 `prepare_compiled_execution` 使用，自身不是源权限。

调用方（S11 规则不变）在新进程打开自己的工作区、声明自己的 publisher、以 `interrupt_attempt` 中断旧的未终结 attempt
（远端层保持 UNKNOWN）、用 acceptance 的 binding 开新 attempt，并以新鲜访问、route 专属托管前提与新 limits/页大小准备并打开
真实 owner——它在新连接/新事务上重新资格认证完整 source 向量与全键域 NULL/碰撞、definition/provider/version/revision/role/
schema/collation，并重新执行 guard。`begin_continuation(publisher, acceptance, attempt, owner, *, operation)` 复核 acceptance、
subject、attempt/binding/route/isolation 对应、位置 0 的新 owner，以新 owner 重算 specification 与资格描述并要求与持久文本逐字节
相等（`EXTRACTION_QUALIFICATION_CHANGED`）；事务内复核 attempt 打开且属于本 publisher、不是原始 attempt、最新 checkpoint 仍等于
前驱，再插入 continuation。持久文本本身从不授权；产品代码从不使用测试传输 `admit_observed_sources`。

## 对账与屏障

冻结 C：F = 重算的最大连续已提交前缀，H = 任一成员最高 stop（只作对账界，不是进度），P = 新枚举位置（从 0）。已知完整
范围 K = 已记录的正常 EOF 观察（所有 EOF 观察必须一致），或 C 含 schema-only 成员时为 0。

- `ContinuationSession.stage()` 每次只消费 owner 的一个受检页（S12 血缘：payload 计数、`enumeration.last_committed`、坐标），
  位置只来自受检流。纯函数 `segments(members, P, P+r)` 把页切成成员内的 old 段与补集 new 段。
- old 段：经 `SnapshotReader.read`（有界、描述符/attempt/IPC 值检查，一次只持有一个成员）读取已保存成员，逐位置比较精确坐标
  原子、Arrow schema（含元数据）与每个公开值的 `atom()`（True≠1、-0.0≠0.0、NULL、Decimal 元组、UUID 字节、datetime iso+fold）；
  任何差异 → `RECONCILIATION_MISMATCH`，会话失败，不发布任何内容。可见值相同但 occurrence 不同同样是不匹配。
- new 段：S12 `_encode` + `_materialize` 只写这一页的精确切片与坐标切片，描述符 attempt 为续写 attempt，得到持久但未引用的
  文件。屏障前它只是候选：不是成员、不可经 R1 交付、不推进 F；上限 `MAX_CANDIDATES = 64` 加 generation chunk 上限、文件上限与
  工作区预算/控制保留（资源拒绝是诚实拒绝，不是不支持族或 EOF）。
- 越过 K 的行 → `RECONCILIATION_EXTENT`；正常 EOF 时 P < H → `RECONCILIATION_PREMATURE_END`，K 已知且 P≠K →
  `RECONCILIATION_EXTENT`；空结果且无 schema 成员时物化 schema-only `[0,0)` EOF chunk；C 的 schema 成员只由新鲜空结果的 schema
  相等匹配。
- `ready` 当且仅当 P ≥ H、已匹配行数等于 C 的行数且会话/owner 未失败（只匹配 [0,F)、计数或最后一个键都不能打开屏障）。
  ready 后未对账则 `stage()` → `RECONCILIATION_PENDING`。
- `reconcile(operation)`：acceptance 有效、owner 未失败/未取消，ACTIVE 围栏事务复核本 publisher 的 continuation、attempt 未终结、
  最新 checkpoint 仍等于前驱、尚无 reconciliation，插入屏障记录（P 与已匹配行数）。之后本 attempt 才能发布。
- `publish(staged, operation)`：S12 发布路径经版本化写入者检查：原始 capture attempt（S12 规则与 capture_end 界）或（v4）
  本 generation 已对账、本 publisher、未终结的续写 attempt，且前驱成员仍全部在最新 checkpoint 中、此后新增成员全部由本 attempt
  产生；与 generation 任何 chunk 不重叠、K 已知时 stop ≤ K、文件身份复核，然后 chunk + 新 checkpoint（ordinal+1、完整成员集、
  重算 frontier）+ operation 同一事务。frontier 从不跳过空洞；新完整覆盖获得新的不可变身份，C 保持原样。
- `end(operation)`（owner 已关闭，控制围栏）：EOF 需要已对账、最新 checkpoint 恰好覆盖 [0,P)（P=0 时为 schema 成员）且 P 等于
  所有已记录 EOF 范围，记录覆盖 checkpoint；非 EOF 只记录观察位置与终态（临时前缀）。
- 再次崩溃：下一个进程冻结其实际最新 checkpoint 并以新 attempt 重做资格认证与对账；不收养屏障对象、持久 VERIFIED 标志或
  其他进程的候选文件（它们保持为未引用文件，`classify_files` 可见）。

## 多 attempt 成员与 R1 交接

`Member` 携带真实 producing attempt；`SnapshotReader.read` 以成员自己的 attempt 核对描述符（v1–v3 由不变的 SQL 谓词保证等于
capture attempt）。v4 `_snapshot` 只接纳 capture attempt 与同 generation 已对账的续写 attempt；任何其他嫁接都会改变成员数 →
`CHECKPOINT_MEMBERS`。v4 终点投影：任一 EOF 观察（全部一致）给出 (N, EOF)，否则取最新观察；分层保留原始 capture attempt
的条目（原 UNKNOWN 不变）并追加 `continuations`（每个续写 attempt 的终态种类与分层）。S13 代码不变：新 consumer 可选择恢复后的
checkpoint（complete_capture 仍是 EOF 范围、无空洞、含 schema 成员），R2 之前注册的 consumer 保持其 checkpoint、extent 与确认
位置；(generation, position) 标签在 attempt 之间与 R1 重分批中不变。恢复结果的 R1 在源已停止后，在仅含 Arrow 的新进程中无 DB
凭据、无源连接、无 guard 重执行地读取。`extraction_state` 是只读观察：原始 attempt、各续写的前驱/F/H/成员/行、屏障、终点、
最新 checkpoint 的重算覆盖与 K；完整覆盖只是行覆盖，不是事务 ACK、交付、consumer/sink 确认或整代发布。

## 独立校验

`verify_store` 从原始行重放：begin_extraction 等于 capture + extraction 行与请求，specification 与 capture 合约/方案/route/
isolation 一致；begin_continuation 的前驱等于重放的最新 checkpoint，F/H/成员/行由重放成员重算，资格描述等于 extraction 行；
reconcile 只在最新 checkpoint 未变、position ≥ H、matched = rows 时；续写 chunk 只在其 reconciliation 之后、由同一 publisher、
前驱成员保留且新增成员属于该 attempt；EOF 终点要求无缝覆盖等于观察位置且所有 EOF 范围一致；complete_capture consumer 注册
使用此前任一 EOF 终点。每个 v4 行都必须由其 operation 产生。

## 失败切点

| 切点 | 证据 | 持久结果 |
| --- | --- | --- |
| 初始基础提交后 / 候选文件持久后（屏障前）/ 屏障提交后 | 真实 SIGKILL | 没有新 checkpoint；下一进程从实际成员重新对账，候选不被收养 |
| 续写 chunk COMMIT 后回复前 / continuation_end COMMIT 后回复前 | 真实 SIGKILL | 新调用方查询**同一** operation 看到一次效果，原回复保持 UNKNOWN，再从实际成员显式恢复 |
| 扩展前缀后再次崩溃 | 真实 SIGKILL | 第三个进程以另一页大小完成，三个 producing attempt 可重建 |
| 晚期岛屿协调损坏、源漂移、版本替换、取消 | 真实原生 | 在任何新 checkpoint 之前拒绝；旧 checkpoint 字节/身份/frontier 不变 |
| 陈旧 publisher、外部 attempt、COMMIT 歧义、预算 | 注入 | 拒绝进度；已提交状态真实；歧义退役工作区并以新句柄查询 |

真实 SIGKILL 与注入错误是不同证据，都不是断电证明；设备/OS sync 诚实与私有合作用户边界是显式前提。

## 验证

核心环境没有 Arrow 与数据库：纯段划分法则穷举小模型；v4 边界、初始基础、屏障/前驱/范围前提、权限新鲜性、COMMIT 歧义、
覆盖规则、独立历史损坏、R1 交接与真实 SIGKILL 切点在合格本地 profile 上运行，使用标注的 SYNTHETIC_OPEN_OWNER、
ARROW_FREE_MEMBER_CHECK 与 ARROW_FREE_PAGE_STEP（真实 `_step`、围栏、屏障、发布与校验器照常运行）；每个 R2 家族的 live 与
loaded 根逐字节重建同一 specification。真实证据由 `scripts/phase68_slice14_probe.py` 运行：`matrix` 在原生 profile 中对每个
准入 R2 家族、三条路线与 live/bundle、source/installed，由隔离 S10 主体以页大小 2 捕获至多三页并放弃 attempt，再由新的隔离
主体以页大小 3 恢复；S10 原始检查器与 S06/S07 字面 oracle 在 worker 外判断完整新鲜枚举，S14 检查器判断冻结前驱、屏障、旧成员
不变、新成员恰为补集与无缝覆盖，并在源库删除后由 Arrow-only 新进程做 R1；`histories` 在每条路线上运行真实 SIGKILL 的
A–I 与 L 历史（前缀+后缀、空洞、晚期岛屿值/坐标协调损坏、回复丢失、二次崩溃、终点回复丢失、屏障后崩溃、源漂移、版本替换、第一页后取消、资格认证前取消）；`matrix` 的 guarded 组另含一个新鲜 guard 漂移项（保存前缀后 guard 源被改为页外违规数据，恢复由自身 guard 在任何续写前拒绝）。

| 后续 | S14 提供 | S14 不实现 |
| --- | --- | --- |
| S15 | 跨 attempt 稳定的 (generation, position) occurrence、每个 chunk 的 producing attempt、可查询的 begin/reconcile/publish/end operation、`extraction_state` | sink 效果、外部 ACK 对账、效果身份 |
| S16 | 完整覆盖 checkpoint 与 K、各 attempt 终态分层 | 整代策略与原子发布 |
| S17 | 未引用候选/孤儿文件的 `classify_files` 可见性、新旧 checkpoint 与 consumer 保护 | 调度、并发 GC、读取/GC 交错 |
