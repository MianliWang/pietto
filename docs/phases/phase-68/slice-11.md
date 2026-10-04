# Phase68 Slice11：Durable job store、兼容性与独占 job publisher

S11 CANDIDATE; completed only after closure。基线为 S10 published head
`e8fbc5ed60eebb0bf9ad772f08a1b50b48d1c17c`，自然 CI37181864937/push/main/attempt1。
本文只描述候选合同；当前存储/原生/安装验收、精确 Git tree、普通 FF 发布、自然 exact-head CI 的全部消费者和
owned cleanup 共同激活完成。证据属于独立 S11 实例，不合并任何已闭合计数。S12 NEXT / NOT STARTED / separate dispatch required。

## 合格工作区与保护边界

`project_job_workspace` 只接受调用者显式给出的、规范绝对路径的私有工作区；父目录须属于当前用户且无 group/other 写权限。
没有 cwd/home fallback。`create_workspace` 独占 mkdir（0700）并写 `CREATING` 标记，同一 SQLite 事务初始化封闭 schema
与 workspace 行，再以 O_EXCL 写入不可变 canonical 信封 `workspace.json`、fsync 目录，最后删除标记。
标记存在或信封/数据库缺失即 `WORKSPACE_INCOMPLETE`，不会被当成空 store；创建失败只删除本次调用按 inode 记录的资源。

`open_workspace` 先检查对象类型、属主、私有权限、单链接与符号链接替换，再解析有界信封；未知 format/feature、非 canonical、
重复成员或身份不符在任何 SQLite open 之前拒绝，文件字节与时间戳不变。实测只读 WAL open 也会创建 `-wal/-shm`，
因此未知格式绝不进入 SQLite。已知信封之后，SQLite 管理的恢复/共享内存记账被允许并单独说明；随后核对
`journal_mode=wal`（只读不转换）、application_id、user_version、精确 `sqlite_schema` 行与 workspace 行，失败为
`WORKSPACE_SCHEMA`，不迁移、不修复、不改 job 状态。

合格 profile 由产品自己观察：Linux；SQLite 版本、`sqlite_source_id()` 与完整 compile options 属于唯一测量构建
3.53.1 / `2026-05-05 10:34:17 c88b2201…7e9`（含 WAL-reset 修复）；工作区所在挂载为 rw ext4 且无 nobarrier。
不声称其他版本、系统库或文件系统合格；tmpfs、网络与跨 OS 挂载拒绝。OS/虚拟磁盘诚实 fsync 是外部前提
`EXTERNAL_PREMISE_NOT_VERIFIED`。每个连接设置并回读 DEFENSIVE、关闭 trusted schema/trigger/view/扩展/可写 schema/DQS、
外键、`synchronous=FULL`、内存 temp_store、有界 busy、预算页数、journal 上限与 cell 检查，ATTACH 上限为 0。

保护边界是私有 OS 用户目录与合作产品 owner；不防 root、同用户直接改写 SQLite/锁文件、被攻陷 SQLite、凭据被盗、
永久磁盘丢失、回滚旧磁盘镜像或多机共享存储，也不声称加密、tamper-proof 或安全删除。

## 身份、规格与转换

身份域互不替代：workspace `ws-`、job `job-`、binding record `bind-`、generation `gen-`、attempt `att-`、publisher instance `pub-`
加持久整数 epoch、调用者给出的 operation `op-`。rowid 不是身份；operation sequence 只表示历史顺序。
job 保存 S10 精确 pinned bundle 字节及 pin/producer/compatibility 描述；这些副本只是一致性数据，不是信任锚。
binding record 保存 slot 描述与 S10 scalar wire 的 typed vector（Bool、Int、±0 Float bits、Text 保持区别），相等值仍是不同记录。
generation 是不可变逻辑结果命名空间：binding record、route、isolation 以及去掉进程内引用的
`describe_compiled_binding` 描述（query/target/profile/接口版本/slots/outputs/sources/refinement/provider 要求）。
注册 generation 不是完成；没有 COMPLETE/PUBLISHED、结果行、chunk 或 frontier。

只有 job 行会被更新，其余行只插入。每个 job 变更在同一写事务中先做 operation 重放/冲突检查，再以
`UPDATE job … WHERE identity, publisher_epoch, publisher_instance, revision, state` 条件更新并要求 rowcount=1，
然后插入效果与 operation 记录。转换表：

| 操作 | 前提 | 效果 |
| --- | --- | --- |
| register_job | 已开 workspace、预算 | ACTIVE、epoch0、revision1 |
| claim | 持有 job OS 锁；ACTIVE 或 CANCELLED | epoch+1、新 instance |
| register_binding / register_generation / open_attempt | 当前 publisher；ACTIVE；open_attempt 要求无未终结 attempt | 插入 |
| record_attempt / record_not_executed | 当前 publisher 即 attempt 的 publisher；尚无终态 | 插入终态 |
| interrupt_attempt | 当前 epoch 大于 attempt epoch；尚无终态 | INTERRUPTED，远端各层 UNKNOWN |
| cancel_job | 当前 publisher；ACTIVE | CANCELLED；不声称 source 已停止 |

## 独占 publisher 与丢失回复

每个 job 一个稳定 inode 的锁文件，非阻塞 `flock`，O_CLOEXEC/O_NOFOLLOW，取得后复核路径仍指向同一 inode，再以短事务分配更高 epoch。
没有 TTL、mtime lease、自动接管或隐藏重试；失败不改变 ownership。句柄绑定 pid，fork/外进程使用拒绝；关闭只关闭本描述符一次，
继承的 open file description 仍可能持锁，因此关闭不等于已证明释放。fork 出的子进程不得终结继承的 SQLite/锁句柄（应以 `os._exit` 结束）；产品拒绝其使用，但无法阻止解释器终结继承对象。直接删除锁文件可绕过 OS 排他，但旧 epoch 在数据库写端仍被拒绝。

operation 身份由调用者在调用前持有。同 id 同请求返回 `PREVIOUSLY_COMMITTED`（查询已提交事实，不是原始 ACK），不同请求
`OPERATION_CONFLICT`。COMMIT 抛错一律 `STORE_COMMIT_UNKNOWN`，连接退役，不自动重复；调用者用新句柄查询。
真实进程在提交前被杀则无部分效果，提交后、回复前被杀则新查询恰好看到一个效果，原调用者回复仍未观察。

## S10 接入与下游

`register_job` 接受 live 或 loaded 模板根的精确字节；`load_job` 必须由调用者重新提供 pin/producer/compatibility，
先核对当前代码 compatibility，再核对信任输入，最后仍由 S10 `load_compiled` 对实际字节验 pin。`bind_record` 经 S10
`bind_values` 产生新的 binding 引用。`open_attempt` 重新推导描述与向量并记录这一新 binding；`record_attempt` 要求
owner 的 request.binding 正是该对象、owner 已关闭，并保存 `compiled_attempt_outcome` 的完整分层字段。存储的 outcome 是历史，
不是下一次执行的授权；每次执行仍需新的凭据、managed premise、来源资格与 guard。`local_durable_result` 保持 `NOT_IMPLEMENTED`。

| 后续 | S11 提供 | S11 不实现 |
| --- | --- | --- |
| S12 | workspace/job/generation 身份、publisher 写端围栏与封闭事务模式 | chunk、文件提交、frontier、retention |
| S13 | 受保护 bundle/vector、job 状态/兼容与新鲜信任加载接缝 | 已保存结果读取/重分批 |
| S14 | query/binding/target/route/profile/refinement/provider 要求描述 | 恢复 frontier 与 occurrence coverage |
| S15/S16 | generation 命名空间与可查询 operation 身份 | effect、ACK、完整代发布 |
| S17 | per-job publisher、短写事务、本地/远端终态区分 | 调度、reader lease、GC、全局 RSS 上限 |

## 上限与错误

bundle ≤ S10 32 MiB；vector 与 description 各 ≤ 4 MiB；outcome ≤ 64 KiB；job/binding/generation/attempt/operation
记录数上限，单 generation attempt 序号 ≤ 1024；工作区预算 8 MiB–4 GiB 写入信封。数据操作要求
db+wal+shm+信封+锁文件 + 3×载荷 + 4 MiB 控制余量不超预算且文件系统有余量，控制操作可用余量。
这是保守准入，不是所有瞬时分配的硬上限；ENOSPC/IOERR 仍可能阻止失败记录，此时调用者保留 UNKNOWN。
所有错误为无值类别；repr、错误、计时标签与普通报告不含参数值、密码或 bundle 正文。

## 验收与证据

普通测试覆盖 profile 接受与拒绝、创建/打开/损坏、连接设置回读、预算、忙等待、注入提交歧义、主错误与清理错误、
A/B/A 与 ±0、信任维度、publisher 排他、写端围栏、句柄生命周期、幂等/冲突、分层历史、取消、三路线 owner、协调损坏与保密；
真实进程覆盖两进程争用、提交前后 SIGKILL、创建中崩溃、fork 继承锁与 source-free 新进程重载。非合格运行时（例如 CI
使用的系统 SQLite）上这些测试断言显式拒绝，不跳过、不模拟耐久 PASS；正例见证属于本地合格 profile。

`scripts/phase68_slice11_probe.py` 是显式有界原生桥接：注册进程退出后，source-free 新进程从 store 重载并经三条 S10 route
各执行 A/B/A/empty，记录分层结果；S10 原独立消费者复核值/SQL/会话，S11 检查器从静态备份副本比对 attempt、终态与字面量 oracle，
并拒绝协调损坏。installed origin 使用当前 wheel，core-only 前缀证明 store 不导入 Arrow/驱动。进程 kill 不是断电证明。
