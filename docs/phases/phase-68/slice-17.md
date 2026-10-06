# Phase68 Slice17：有界多作业执行、背压与并发安全回收

S17 CANDIDATE; completed only after closure。基线为 S16 published head
`cd6dbea4d5b9d2f10265be8eea3a64afa0e3f286`，自然 CI37427084705/push/main/attempt1。本文只描述候选合同；当前存储/原生/安装
验收、精确 Git tree、普通 FF 发布、自然 exact-head CI 的全部消费者和 owned cleanup 共同激活完成。证据属于独立 S17 实例，
不合并任何已闭合计数。S18 NEXT / NOT STARTED / separate dispatch required。产品作业并发、编码写入者数量与验证槽位上限是三件事。

## 范围与选定机制

S17 承担 A17（多作业准入与资源调优）、A18（安全并发回收）与 A16 的“负载下控制”连接。它消费 S12 的受保护/分类文件、S13 consumer
保留、S14 旧成员与候选血统、S15 窗口与 sink 保留义务、S16 发布与准备保护，不重写其判定，也不重新定义成功完成。两个新的私有
owner：`project_job_runtime`（运行时所有权、准入/结算、单元、控制通道）与 `project_job_collection`（显式退役、保护根、可用性、
回收与续删）。没有守护进程、分布式调度、服务账户、持久凭据队列、任意代码作业服务、公共 CLI/API、XA、共识或新 WAL 引擎。

## 显式 v7 工作区

v1–v6 的创建、打开、schema 与语义不变。只有显式 `create_workspace(..., format=FORMAT_V7)` 创建 `pietto.job-workspace.v7`：
features 为 v6 的五项加 `bounded-job-runtime` 与 `concurrent-gc`，user_version 7，schema = v6 原样 + 封闭 S17 关系。能力只按
`supports(...)` 精确判断；旧格式上的 S17 调用在任何改动前以 `WORKSPACE_RUNTIME_FORMAT`/`WORKSPACE_COLLECTION_FORMAT` 拒绝。
没有升级、ALTER、导入、sidecar 或 `version >= 7` 推断。新身份类别仅 `run`（运行时实例）、`adm`（准入）、`gcd`（回收决定）。

| 关系（v7，STRICT、只插入） | 内容 |
| --- | --- |
| `runtime_owner` | 一个协调实例：epoch（最新者为当前）、instance、冻结的聚合策略 |
| `admission` / `admission_settlement` | 一个单元的持久资源向量与字节/操作行额度（所属 epoch）；恰好一次结算：同 epoch `RELEASED`，后继 epoch `RECONCILED`，记录已 claim 字节 |
| `chunk_claim` | 文件名出现之前登记的确切未来 chunk 文件（名字 = chunk 身份）、其 attempt、准入与字节数；v7 的每个 chunk 都先有 claim |
| `generation_retirement` | 显式退役一个未发布代，只移除其隐式最新 checkpoint 根 |
| `collection` / `tombstone` / `removal` | 一次有界、固定成员的删除决定；每个成员的确切文件对象；目录同步后的观察（`UNLINKED` 本次执行、`ABSENT` 仅观察） |

## 协调器、准入与资源向量

每个工作区每进程一个调用方创建、显式关闭的 `Runtime`：非阻塞 `flock` 锁定稳定的 `locks/runtime.lock`，并在其下写入新 epoch；
第二个协调器（任何进程）`RUNTIME_BUSY`；锁在所有 worker 线程汇合后才释放，未汇合则保留至进程退出。worker 是有界线程：三条
原生 owner 已有自身计时/控制线程与线程安全 `cancel()`；每个线程自开工作区句柄（SQLite 不跨线程）、自取 per-job publisher、
从显式类型化主机输入自建原生 owner，不跨进程传递连接、publisher、owner 或授权，不 fork，无执行器队列。

单元类型：CAPTURE、RELAY、RECOVER、REPLAY、PUBLISH，均为原 API 的薄驱动。资源向量（连接、worker、内存字节、持久字节、操作行）
在协调器互斥量下内存全有或全无预留，再在一个 BEGIN IMMEDIATE 事务内对“已提交核算 + 所有未结预留”原子检查并插入 `admission`；
v7 每个数据操作也在写锁下重新检查。硬逻辑上限：连接、worker、队列、MAX_STAGED/候选、待交付 1、待确认 issuance 1、每准入的
claim 字节；保守预留：内存、持久额度、操作行；测量观察：Arrow 持有字节、DB/WAL、statvfs、RSS。超界单元提交即拒绝
（`RUNTIME_UNIT_BOUND`），超额 chunk 在 claim 时拒绝（`RUNTIME_ALLOWANCE`），交付持有字节超内存预留拒绝（`RUNTIME_MEMORY`），
从不截断、溢出或当作 EOF。准入 COMMIT 不明：不开始工作，用新句柄按身份查询再决定；结算恰好一次，重放返回原事实；内存容量
在线程结束时恰好释放一次。后继实例 `reconcile()` 结算早先 epoch 的未结准入，claim 字节保留计费直至回收；开放 attempt 保留，
等待 publisher 按 S11 规则中断；不重启源、R1 或 R2。数据操作永远保留 `CONTROL_OPERATIONS` 行给取消、终态、结束、释放、退役。

## 调度、背压与控制通道

准入为 FIFO、工作守恒、有界超车：能放下的后来者至多超过最老的受阻单元 `overtakes` 次，之后在其放下前无人通过；限制资源
可查询。已准入单元各自一个线程，互不垄断。下一个受检批次只在上一个已持久（RELAY 还须已交付并确认）后才拉取：被阻塞的 sink 或
consumer 使源停在固定高水位（1 批、≤MAX_STAGED、1 个 issuance/交付），其他作业继续；恢复时同一 owner/attempt 继续，occurrence
身份不变，不发明 ACK 或本地确认。REPLAY 交付只经显式 `ack()` 由 worker 执行原 S13 确认；读取/取走/关闭都不是确认。

`cancel(handle)` 在互斥量下 O(1) 接受（按单元合并），立即调用该 owner 自己的原生取消（requested/sent/observed 保留），并唤醒
worker；持有 Publisher/SQLite 的 worker 记录持久 `cancel_job`，再经原 owner 关闭、结束捕获并记录 attempt 真实结果。排队单元由
控制线程自取 publisher 记录持久取消。单元期限由控制线程执行（停止，不是持久取消）。持久取消 COMMIT 不明报告 UNKNOWN，
从不由标志推断 CANCELLED。轮询与状态查询不写库。锁序（无环）：job publisher（非阻塞）→ 代租约（共享有界等待/独占不等）→
SQLite 写事务；协调器互斥量为叶子，不跨 IO、原生调用、SQLite 或 join 持有。

## 保护根与显式退役

保护 = 每个未退役代的最新 checkpoint 成员 ∪ 每个未释放 retention 指名 checkpoint 的成员（S12 显式、S13 consumer、S15 窗口、
S16 准备、S16 发布）∪ 持有共享租约的活跃文件使用者；`protection()` 在一个读快照内给出每个代的根与原因。
`retire_generation` 为 v7 专有、`_FENCE_CONTROL` 围栏、operation 幂等：已发布 `GENERATION_PUBLISHED`、已退役
`GENERATION_RETIRED`、有开放 attempt `ATTEMPT_OPEN` 拒绝；之后 open_attempt、claim、chunk 发布、capture/continuation 结束、
任何新 retention（consumer、窗口、准备、显式）与发布均以 `GENERATION_RETIRED` 拒绝，既有 consumer 的固定范围读取、已采纳窗口
的交付与读者照常。发布在先使退役拒绝；退役在先使发布拒绝；之后的取消不移除已发布保护。v7 通用 `release_retention` 对仍有
未决 issuance 的窗口 retention 或其交付被桥接且未决的 consumer retention 拒绝 `RETENTION_OBLIGATION`；发布 retention 保持
`RETENTION_PUBLISHED`。sink 数据与保留不属于工作区回收。

## 生命周期排他与并发回收

每代一个稳定锁文件 `locks/<gen>.life`。`SnapshotReader` 整个生命期持共享租约，并在取得后重新检查成员是否已有墓碑
（`CHUNK_COLLECTED`）；捕获的 claim+写文件与 chunk 发布、发布事务的文件对象复核都在共享租约内。收集器非阻塞地取独占租约，忙则
跳过并报告。候选只有两类：已退役未发布代中不在任何未释放 retention 内的已提交 chunk（RETIRED），以及无 chunk 行、其 attempt
已有终态或 publisher epoch 已被取代的 claim（ABANDONED）。未登记名字、外来对象、符号链接、已发布或受保护成员都不是候选；
已提交文件在决定前已缺失属于损坏（`CHUNK_MISSING`），不会被“回收”掉。线性化点：删除 = 独占租约下的决定 COMMIT（运行时围栏、
重算根、固定确切对象）；使用 = 取得共享租约后的新检查。之后按固定对象经受检目录描述符 unlink，目录 fsync 后记录 removal；
只有 removal 让字节退出核算。各切点：COMMIT 前无授权；COMMIT 后按原决定续删；unlink 或同步后、观察前由后继记录 ABSENT；
观察 COMMIT 后查询原决定，不重复。对象变化 `COLLECTION_OBJECT` 拒绝并保留。不删除数据库、WAL/SHM、信封、锁文件或报告，
不 VACUUM；历史行（chunk、checkpoint、attempt、operation）永不删除或改写；当前使用明确拒绝。

## 验证

核心环境没有 Arrow 与数据库：纯准入与生命周期状态模型穷举运行；v1–v7 边界、claim/租约/准入/结算、退役、各保护根单独与组合、
强制正例（已退役已提交代被实际回收且历史完整）、S13/S15/S14/S16 邻接、别名与外来/替换/缺失对象、注入切点与查询、竞态、独立
检查器与 13 种协调损坏（各由指定定律拒绝），以及协调器的重叠、冲突、竞争、回滚、歧义、背压高水位、显式 ACK、饱和下取消、
期限、公平与关闭/替换，均在合格本地 profile 上以标注的 ARROW_FREE_STORAGE_STEP、SIMULATED_NATIVE_IO、SYNTHETIC_CLOSED_OWNER、
ARROW_FREE_MEMBER_CHECK 与 ARROW_FREE_READER 运行；跨进程的读者/收集器两种顺序、五个真实 SIGKILL 切点、协调器死亡后替换与
继承描述符在注册子进程中运行。真实证据由 `scripts/phase68_slice17_probe.py` 产生：`suite` 在 Arrow-only profile 中经协调器以真实
Arrow/IPC 运行；`native` 在三条路线、两种入口与两种来源上经协调器运行，独立检查器从原始关系与事件重算。

| 后续 | S17 提供 | S17 不实现 |
| --- | --- | --- |
| S18 | v7 能力集与关系、`Unit`/`Policy`/`Runtime` 私有签名、退役/回收/拒绝观察码、懒导入边界不变 | 安装与跨版本兼容 |
| S19 | 准入/租约/墓碑定律、检查器与损坏目录、证据类别划分 | 全矩阵联合验收 |
