# Phase68 Slice16：原子完整代发布与丢失回复后查询

S16 CANDIDATE; completed only after closure。基线为 S15 published head
`ccda584ca93ad92b54154f958c8405a23efc8ae3`，自然 CI37401687496/push/main/attempt1。本文只描述候选合同；当前存储/原生/安装
验收、精确 Git tree、普通 FF 发布、自然 exact-head CI 的全部消费者和 owned cleanup 共同激活完成。证据属于独立 S16 实例，
不合并任何已闭合计数。S17 NEXT / NOT STARTED / separate dispatch required。产品“发布”（完整本地代）与本实现的 Git 发布是两件事。

## 范围与选定机制

S16 把已经持久、已检查的 S12/S14 chunk 组成的一个完整本地代，以一个原子元数据事务发布为不可变引用：引用精确 checkpoint、
`[0, N)` 范围、合约/坐标方案、closing attempt 与其 closing observation、发布自有保护和原 operation，而不重写数据文件或另存
整份结果。私有 owner `project_job_publication` 位于现有 job store 之上；v6 `record_attempt` 在终态事务内记录 closing
observation，S11/S12/S14 写端在 v6 上拒绝已发布代的新 attempt 与数据写入。没有 sink 策略、任意 callback、通知服务/outbox、
可变 latest 注册、跨库事务/XA、源服务、迁移、调度、GC 或公共 release；S17 负责调度/背压/GC。

## 显式 v6 工作区

v1–v5 的创建、打开、schema 与语义不变。只有显式 `create_workspace(..., format=FORMAT_V6)` 创建 `pietto.job-workspace.v6`：
features 为 v5 的四项加 `complete-publication`，user_version 6，schema = S11–S15 表（不变）+ 封闭 S16 关系。能力只按
`supports(workspace, "complete-publication")` 判断（否则 `WORKSPACE_PUBLICATION_FORMAT`）；没有升级、ALTER、导入或 sidecar。
已发布 S15 运行时（存档 wheel 字节）打开 v6 以 `WORKSPACE_FORMAT` 在 SQLite open 前拒绝且目录不变。没有新身份类别：一个代至多一个
发布，以 generation 为键；原 operation 是丢失回复后的查询句柄。

| 关系（v6，STRICT、只插入） | 内容 |
| --- | --- |
| `attempt_subject`、`retention_subject` | 唯一索引，仅作为复合外键目标 |
| `closing_observation` | 一个 OUTCOME attempt 的 closed=1、受检交付行数、primary 失败 `[phase, kind]` 或空、cleanup 失败类别列表；外键指向 attempt 终态与 `(attempt, generation, job)`；只由 v6 `record_attempt` 与终态同事务写入 |
| `publication` | generation 主键；job、binding、checkpoint、范围 N、成员数、合约、坐标方案、closing、retention（唯一）、描述符、operation（唯一，延迟外键）、发布者 epoch/instance；外键防止跨 job/代/checkpoint 嫁接 |

描述符是有界规范 JSON：`pietto.publication.v1`、basis（CAPTURE/CONTINUATION）、kind、chunk 与坐标格式、工作区格式；成员仍由
不可变 checkpoint 承载，摘要不证明覆盖或认证结果。

## closing observation 与完整性真值表

S10 新增 `compiled_closing_facts(owner)`，与 `compiled_attempt_outcome` 共享同一 owner/请求状态校验，只读取 owner 自身的
closed、`outcome.rows`、primary 与 cleanup 失败的 `(phase, kind)`；原 outcome 不变。NOT_EXECUTED、INTERRUPTED 与缺失终态没有
observation；进程在终态事务提交前死亡则证据缺失，不从文件、时间或之后的成功推断。

可发布当且仅当以下事实同时成立（括号为拒绝码，按此顺序给出第一项）：终态为 OUTCOME 且有 observation
（`PUBLICATION_CLOSING_UNOBSERVED`）；source=EOF（`PUBLICATION_SOURCE`）；transaction=COMMIT_ACK 且 remote_source_use_end=TRANSACTION_ACK
（`PUBLICATION_TRANSACTION`）；delivery=COMPLETE（`PUBLICATION_DELIVERY`）；cleanup 为该路线自身的正常词且无 cleanup 失败
（`PUBLICATION_CLEANUP`）；无 primary 失败（`PUBLICATION_PRIMARY`）；QUALIFIED 且有事务上下文（`PUBLICATION_QUALIFICATION`）；每个 guard
状态为 STATIC/FULFILLED（`PUBLICATION_GUARDS`）；结构/部署/路线/绑定引用一致（`PUBLICATION_OUTCOME`）；closing 基础（`PUBLICATION_BASIS`）；
已知范围 N 等于 observation 行数（`PUBLICATION_EXTENT`）；指名 checkpoint 为最新且恰好覆盖 `[0, N)`（`PUBLICATION_COVERAGE`）；无开放
attempt（`PUBLICATION_ATTEMPT_OPEN`）；尚未发布（`GENERATION_PUBLISHED`）；发布事务内 job 仍为 ACTIVE（S11 围栏 `JOB_STATE`）。

| 路线 | 正常 cleanup | 失败 cleanup |
| --- | --- | --- |
| postgres_rows | `CLOSED` | `FAILED` |
| postgres_adbc | `LOCAL_CLOSED_REMOTE_UNOBSERVED` | `FAILED_REMOTE_UNOBSERVED` |
| mysql_rows | `LOCAL_CLOSED_REMOTE_UNOBSERVED` | `FAILED` |

`LOCAL_CLOSED_REMOTE_UNOBSERVED` 只是本地关闭、未观察远端，不证明远端静止；事务保证只来自 COMMIT_ACK。迟到的取消请求在已完成
工作之后只被记录（cancel 三元组），不是失败。closing 基础：普通代与“无 continuation 的 R2 代”用原始捕获 attempt（capture_end
EOF=N，全部成员由它产生）；发生过恢复时用一个已对账（屏障）、自身 continuation_end 为 EOF=N 且覆盖 checkpoint 即指名 checkpoint 的
S14 continuation，其前驱成员保留、新成员均由它产生。旧 attempt 可以保持 UNKNOWN/INTERRUPTED；新成功不是旧事务的 ACK，任意之后的
无关成功、未完整重新枚举、缺屏障、规格变化或来历不明的成员都拒绝。

## 授权、准备与原子发布

`accept_publication` 给出进程内、不可复制、purpose 限定的 `PublicationAcceptance`：新鲜 pin/producer/compatibility、精确 typed 值、
route/isolation、输出合约与坐标方案、指名 checkpoint 与 closing attempt，R2 代还核对提取规格；墙钟与单调钟双截止。它不连接源、
不重跑 guard、不需要数据库凭据；记录与身份不认证任何人。

`prepare_publication` 先用现有 S12 `retain_checkpoint` 取得准备保护（不是发布，不出现在任何发布列表），再在任何写事务之外读取
原始事实、计算真值表，并用 S12 `SnapshotReader.read` 一次一个 chunk 复核全部成员（有界字节、摘要、描述符、完整 IPC 值、schema、
坐标），只保留文件对象 `(dev, ino, ctime, size)`；昂贵工作后再查授权与 job 状态。已知拒绝只释放本次准备保护，释放本身不确定时
保守保留并注记。准备对象进程内、单主体、不可复制，不能由摘要重建。

`publish_generation` 是唯一可见点：一个短的 S11 `_operate` 写事务，ACTIVE 围栏、授权有效、真值表从原始行重算、成员与范围
等于准备时、准备保护未释放且属于该 checkpoint、无既有发布、无开放 attempt、成员文件对象逐个重查（不读内容），然后插入不可变
publication，把准备保护经引用转为发布自有保护，并与 operation 结果同时提交。仅在观察到 COMMIT 后返回 COMMITTED_THIS_CALL；
COMMIT 结果不明为 `STORE_COMMIT_UNKNOWN`，工作区句柄退役、一切保留，按原 operation 查询；同 operation 重放返回历史事实，内容不同
为 `OPERATION_CONFLICT`，其他 operation 不能覆盖已发布代。

## 取消顺序、查询与通知

发布与取消共用 S11 的串行围栏：取消在先则发布拒绝（`JOB_STATE`），准备不是发布；发布在先则之后的取消照常记录，但不撤回发布、
不删除 operation、不释放其保护。陈旧 publisher/revision（`PUBLISHER_STALE`/`PUBLISHER_REVISION`）不同于取消。
`publication(workspace, job, generation)` 精确返回 RECORDED 发布、已知未发布（None）或报错（IO/损坏/未知代不是“不存在”）；
`publications(workspace, job)` 在一个读快照内按提交顺序列出。持有旧快照的读者可以看到旧视图。返回值与之后的通知都在提交原子性
之外：提交后回复前的进程死亡与成功返回后的通知写失败都不回滚发布，新进程按原 operation 与代找到唯一的原发布。发布后的数据
损坏只让当前读取失败，历史发布保留；不删除、不缩小、不回源、不换 checkpoint。

## 读取交接、保护与 sink 分离

发布引用只指向其完整 checkpoint 与范围；新读者仍须 S13 新鲜已保存读取授权（complete_capture、固定 checkpoint/范围），发布记录
不是凭证。既有 S13 consumer 范围不变；取消后新读取按原有取消规则。发布自有保护出现在 `protected_chunks` 中；通用
`release_retention` 对发布的 retention 拒绝（`RETENTION_PUBLISHED`），读者关闭、stream 退役、超时、publisher 更替与取消都不会释放它；
v6 下已发布代拒绝新 attempt、新 chunk/checkpoint 与 capture/continuation 终点写入（`GENERATION_PUBLISHED`）。S15 临时效果与本地
确认保持独立：本地发布可与未完成的 sink 交付共存，sink 中全部效果存在也不能使失败/不完整的 source 合格，发布不调用 submit/
reconcile/retire，也不自动 R1 确认。

## 失败切点与验证

真实 SIGKILL 切点：准备保护已提交、校验完成未发布、publication 已插入未 COMMIT、COMMIT 后未回复；另有成功返回后的通知写失败、
两个进程的新旧读快照、跨进程的取消在先与发布在先、以及第二个写者的真实 `PUBLISHER_BUSY`。新进程查询结果总是零或一个完整发布。

核心环境没有 Arrow 与数据库：纯真值表、三路线 cleanup 词与覆盖模型在所有主机运行；v1–v6 边界、closing observation、普通/空/R2
发布、拒绝矩阵、空洞与开放 attempt、成员损坏、取消顺序、陈旧 publisher、授权与时钟、注入故障、历史保留、保护、S13/S15 邻接与
独立历史损坏在合格本地 profile 上运行，closing owner 为标注的 SYNTHETIC_CLOSED_OWNER、成员检查为 ARROW_FREE_MEMBER_CHECK。
真实证据由 `scripts/phase68_slice16_probe.py` 运行：`suite` 在 Arrow-only profile 中以 SIMULATED_NATIVE_IO 捕获七标量（39/65）、重复值、
空 schema 与迟到失败并发布/拒绝，新进程以 S13 读取发布引用，成员损坏（迟到摘要、互换成员、越界取值、错查询复制、空 schema）
在可见前全部拒绝，存档 S15 wheel 拒绝 v6；`native` 在每条路线、两种入口与两种来源上运行 R2_seven 联合历史（S15 前缀效果、SIGKILL、
R2 前发布被拒、新进程 S14 恢复由真实 owner 记录 closing observation、删除源库后在无驱动 Arrow-only 进程中发布、查询与 S13 读取），
并在每条路线与来源上发布普通七标量、普通空、精炼空与 guarded 结果；独立检查器从原始关系重算资格、成员、血统与对应关系，真实
记录上的每项协调损坏都重写其触及的全部冗余副本，并须由其指定控制拒绝（如伪造成功的旧 attempt 由血统 BASIS、删除成员并重算
总和由 closing 行数、抹去的历史 UNKNOWN 由 INTERRUPTED 定律）；同时改写结果事实本身的全部副本属于威胁模型之外的恶意私有数据。

| 后续 | S16 提供 | S16 不实现 |
| --- | --- | --- |
| S17 | 发布自有 retention（`protected_chunks` 可见、不可通用释放）、准备保护与发布保护可区分、`GENERATION_PUBLISHED` 写端准入点 | 调度、背压、并发 GC、删除 |
| S18 | v6 能力集与 `pietto.publication.v1` 描述符、closing observation 字段、S10 bundle/代码兼容仍需新鲜 | 安装与跨版本兼容 |
