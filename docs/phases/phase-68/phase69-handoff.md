# Phase68 交接：性能插段与 Phase69 的输入

本文是输入交接，不是 Phase69 initiation，也不是公共 API 设计决定。后续顺序固定为
**post-Phase68 CI/validation performance interlude → Phase69**：性能插段 APPROVED / QUEUED / NOT STARTED，Phase69 NOT STARTED，
二者各需自己的端到端 dispatch。本文的事实在 S20 [唯一闭环规则](slice-20.md#唯一闭环规则)激活后成为 Phase68 的交接基线；
最终 Phase68 head/tree 与 CI 只记录在 S20 外部 final-state 中，插段自己的 Gate0 必须重新核对 live 状态与 core 快照。

## 起点身份

| 项 | 值 |
| --- | --- |
| 当前基线（S20 之前） | B20 `b4cb9845fa59cec6a3303e2dd21a3ce070f21d72` / tree `66fd816eb92d1c22ed3bee72cbe65277f4aaa61d`，CI37711770935 |
| 产品身份 | wheel `cf81718b12dfcc9161719063b7f171d65299eb662507cdf37467d64a75543979`、代码身份 `133d424d7f85c44d176326818b882ad6c838e4f2b4349feb2cec03fbfaaeafe0`；package/CLI 0.1.0，无 public release |
| 开发 core | CPython 3.13.13、uv 0.11.19、Ruff 0.16.10、可编辑 Pietto、dev group 驱动 psycopg/psycopg-binary 3.3.5 与 mysql-connector-python 26.7.0、typing_extensions 4.16.0；无 PyArrow/ADBC |
| 原生合格 profile | S19 campaign04 的实际前缀（importlib_resources 6.5.2、typing_extensions 4.15.0）；与当前锁定 profile（7.1.0 / 4.16.0）分开 |
| 托管补丁 | Python 3.12.14 与 3.13.15（PR #81）；15-job 拓扑 |

## 已交付的私有接口

全部 owner 都是 `__all__ = ()` 的私有模块；签名取自真实代码，不在此冻结为公共 API。

| 边界 | 实际入口 | 调用方必须提供的权威 | 终态与义务 | 已测域 |
| --- | --- | --- | --- | --- |
| 编译运行包 | `build_compiled(artifact, *, guarded, refinement)`；`load_compiled(raw, *, expected_pin, accepted_producer, accepted_compatibility)`；`semantic_build_identity()` | 整包内容 pin、可信 producer、代码 compatibility | 每次加载新语义根；pin 不是签名 | 三路线 × live/bundle × source/installed |
| 模板与绑定 | `prepare_live_template`、`prepare_compiled_template(root)`、`bind_values(template, supplied)`、`describe_compiled_binding(binding, *, route)` | 精确有序 slot 值：Bool/Int64/有限 Float/Text | 值敏感事实重建；结构性 LIMIT/frame 不可绑定 | S04–S19 命名语料 |
| 执行 | `prepare_compiled_execution(binding, access, *, route, limits, isolation, postgres_deployment, mysql_deployment, allow_guard_sql)`；`PostgresExecution`、`PostgresADBCExecution`、`MySQLExecution` | 显式 access、路线专属 managed premise、isolation 与 limits | `compiled_attempt_outcome` 分层终态；`compiled_closing_facts` | PG 18.6 / MySQL 8.4.12，S19 全矩阵 |
| 工作区与 job store | `create_workspace(root, *, budget_bytes, busy_seconds, format)`、`open_workspace`、`supports(workspace, feature)`；`register_job`、`claim_publisher`、`open_attempt`、`record_attempt`、`interrupt_attempt`、`cancel_job`、`query_operation`、`load_job` | 私有规范绝对路径、合格存储 profile、调用方持有的 operation 身份 | publisher epoch 写端围栏；COMMIT 歧义为 `STORE_COMMIT_UNKNOWN` | v1–v7；SQLite 3.53.1 + ext4 |
| 捕获与检查点 | `begin_capture`、`checkpoint_snapshot`、`retain_checkpoint`、`release_retention`、`classify_files`、`stored_output` | 当前 publisher、未终结 attempt、未交付的 owner | 文件先于元数据；frontier 不跨空洞 | S12–S19 |
| R1 已保存读取 | `accept_saved_read(…, checkpoint, consumer, scope, extent, purpose, route, values, …, seconds, batch_rows)`、`register_consumer`、`open_replay`、`consumer_state` | 新鲜信任输入与 typed 值；固定 checkpoint/extent | 显式确认链；`SAVED_SCOPE_EXHAUSTED` 不是 source EOF | 无驱动 Arrow-only |
| R2 提取恢复 | `begin_extraction`、`accept_recovery(…, checkpoint, purpose, values, …, seconds)`、`begin_continuation`、`extraction_state` | 新鲜信任、访问、premise、资格与 guard | 完整有序重新枚举与全部旧成员对账；`EXTRACTION_QUALIFICATION_CHANGED`、`RECONCILIATION_MISMATCH` | 62 个准入族/target |
| 临时交付与参考 sink | `accept_window`、`accept_sink`、`register_stream`、`open_stream`、`relay`、`retire_stream`、`stream_state`；`create_sink`、`open_sink` | 读取与 sink 两个授权；sink 实例/命名空间/epoch/保留合同 | 效果身份 `(workspace, generation, position)`；`PRESENT_MATCHING`、`ACTIVE_NOT_FOUND`；`WAITING_FOR_COMMITTED_CHECKPOINT` | reference sink v1 |
| 完整本地发布 | `accept_publication`、`prepare_publication`、`publish_generation`、`publication`、`publications` | 新鲜发布授权、指名 checkpoint 与 closing attempt | 真值表从原始行重算；`PUBLICATION_CLOSING_UNOBSERVED` 等拒绝码；发布不撤回 | v6/v7 |
| 有界运行时与回收 | `open_runtime(root, *, expected_identity, policy, busy_seconds)`、`Runtime.submit/cancel/close`、`reconcile`；`retire_generation`、`protection`、`collect`、`availability` | 显式 policy；每工作区一个协调器 | 准入/结算/取消/删除决定/移除/credit 分开；`RUNTIME_BUSY`、`RUNTIME_ROUTE`、`RUNTIME_UNIT_BOUND` | v7 |

## 安装选择与依赖边界

`pietto`（core，无 Arrow/驱动）、`pietto[arrow]`（`pyarrow==25.0.1`，无驱动的已保存结果操作）、`pietto[execute-postgres]`、
`pietto[execute-mysql]`、`pietto[execute-postgres-adbc]` 与三者并集。安装从不选择路线、创建 job、授予权限或认证存储。
所选路线的 pinned 驱动在 admission/worker/连接之前检查：缺失为 `EXECUTION_DEPENDENCY_MISSING`；版本不符为
`EXECUTION_DRIVER_VERSION`（PG rows、MySQL）或 `POSTGRES_ADBC_DRIVER_PROFILE`；实现或原生库错误为 `POSTGRES_DRIVER_LIBRARY`、
`POSTGRES_ADBC_DRIVER_LIBRARY`；组合环境不回退到其他驱动。已测域：Linux x86-64；原生验收在 CPython 3.13.13，托管回归在 3.12.14/3.13.15；
更新后传递依赖对下的真实 PostgreSQL ADBC 查询 NOT_OBSERVED。

兼容四层分开：未知/未来信封在 SQLite 打开前 `WORKSPACE_FORMAT`；已识别格式的 schema 损坏 `WORKSPACE_SCHEMA`；
代码身份变化为 `COMPILED_COMPATIBILITY` 或 `JOB_COMPATIBILITY`；新鲜接受另行判定。operation 重放返回 `PREVIOUSLY_COMMITTED`，
内容不同为 `OPERATION_CONFLICT`，陈旧写者为 `PUBLISHER_STALE`，第二个写者为 `PUBLISHER_BUSY`；已发布代 `GENERATION_PUBLISHED`、
已退役代 `GENERATION_RETIRED`，发布保护 `RETENTION_PUBLISHED`，未决义务 `RETENTION_OBLIGATION`，回收后的读取 `CHUNK_COLLECTED`。
cleanup 词各路线自有：PG rows `CLOSED`；ADBC `LOCAL_CLOSED_REMOTE_UNOBSERVED`/`FAILED_REMOTE_UNOBSERVED`；MySQL
`LOCAL_CLOSED_REMOTE_UNOBSERVED`/`FAILED`。guard 违例为 `SINGLE_MATCH_VIOLATED`。

## Phase69 需要另行做出的决定

Phase69 消费真实执行矩阵与入口/错误要求，但以下事项本文都不决定：哪些私有 owner 成为公共入口及其形状、错误分类的公开方式、
发布工程与版本、支持平台与文档承诺、是否把某条路线列为 alpha。公共格式/API 冻结仍归 Phase82，stable 1.0 归 Phase83，
更强信任/签名归 Phase84；本文不把它们移入 Phase69，也不选择新的认证机制、启用 release 工具或改变包版本。
`Managed operator compliance: NOT_INDEPENDENTLY_VERIFIED` 与 `Native all-definition lifetime exclusion: NOT_DEMONSTRATED / NOT CLAIMED`
是任何公共说明都必须保留的前提。

## 性能插段输入

插段的 dispatch 须分开两个目标：**日常本地/托管回归**（本地 validator 约 1374 s、pytest 约 1235 s；托管 workflow 1845 s（S19）与 1893 s（B20），
S19 运行中最长的 job 为 Runtime 3.12 / general-runtime 1733 s；重复源码编译、重文件与 757 s 单节点长尾、既有获取与 CI 放置），以及
**大型原生验收 campaign**（S19 campaign04 单调 30956.57 s；分区不均、R1 读出串行、R2 CPU 重）。改善后者不会自动加速托管回归。
横向 CI 分片已实测无收益（每个独立 pytest 调用约 470.64 s 共享获取底），重新打开须满足其记录的边界。

| 候选（未实施） | 影响的 owner | 相关实测 | 未决的隔离/新鲜度/资源问题 | 建议的有界比较 |
| --- | --- | --- | --- | --- |
| 每个数据库一个 case 队列、worker 动态领取、长任务优先 | S19 matrix 分区与族控制器 | 每分区 CPU/墙钟约 1.0 核；pg 16902–22147 s，mysql-0 26308 s（距 28800 s 超时约 41 min） | guarded 夹具每库串行、每 cell 新鲜资格与 attempt、数据库并发与内存容量未测 | 同一 case 子集、同保证，serial 与并行各一次，记录墙钟/CPU/内存/数据库负载 |
| 在独立工作单元之间替换已空闲的目标容器 | target-conformance 资源 owner | MySQL 单分区约 1 h 长尾 | 容器生命周期、数据库所有权与清理身份；不能在工作单元中途切换 | 两种调度在同一清单上的阶段跨度 |
| 并行 R1 读出（保持实际生命周期与来源规则） | S14 `r1_offline` 尾段 | 每个工作区 8.62–11.61 s；每分区两个来源合计 1392.78–2203.00 s（约 23–37 min） | Arrow-only 进程、无驱动、零连接的不变量；保留期与读取授权 | 同一已保存工作区集合的串行与并行读出 |
| 降低 R2 CPU 成本 | S14/S06 恢复路径 | R2_seven 每页约 15 s（S19 报告的记录，S20 未从原始数据复算）；tuning 组件 CPU/墙钟约 1.0（aud02） | “受 GIL 限制”仍是假设；不能改变对账、屏障与精确值 | 固定 R2 族的 profile 与修改前后对比 |
| 降低重复源码编译与单节点长尾 | pytest 获取 owner、CI placement | 四个最重 Phase68 文件约占 general-runtime 工时 43%；757 s 单节点 | 每个断言自己的新鲜编译根；loadfile 下调度依赖 | 托管健康数据与一次本地受控对比 |

“2–3 倍”只是估计：实测平均 2.5 或 3.05 核不授权把最坏情况的槽位预留降到这个数，也不授权增加 worker；CPU 余量不证明内存或
数据库容量。现有规则保持：经批准的 campaign 至多 8 个全局重负载槽，非 campaign 至多 4 个，权威全量独占且至多 4 个 worker；
新的上限需要用户另行批准。每次新执行仍须新鲜接受、资格、guard、attempt 与来源身份。已有数据位于 S19 证据实例
`pietto-phase68-slice19-20261007T055304Z`（计时 JSONL、campaign04、check02、CI 37705001971 的 artifact）、维护实例
`pietto-dependabot-82-83-20261008T004224Z`（CI 37711770935）与 S20 实例 `pietto-phase68-slice20-20261008T024859Z`（aud01–aud05）。
测量缺口：容器内数据库服务端 CPU 与内存、每个 worker 的 RSS 峰值、两个时钟域约 2.2–2.5% 差异的原因。

SciNet 仍是用户独立副本上的 HPC 课程练习；当前正式验证所需的本地 ext4 与 Docker 容器域在那里未获资格，本文不迁移正式验证，
也不对 SciNet 的其他用途下全局结论。
