# Phase68 Slice19：全矩阵差分保证、联合崩溃历史、同保证并发与阶段末获取合并

S19 CANDIDATE; completed only after closure。基线 B19 为 S18 published head
`35fb67afa3d12088de7571bfe313c296a68a2f0d`（C10 修复子提交，唯一父为保留的失败 head `52551f4aa3a95fd2e5e2d430f1bb572291d22b12`），
自然 CI37566435211/push/main/attempt1；S17 以 COMPLETED_WITH_DISCLOSED_PROCESS_EXCEPTION 闭合，C16 一次性接受、历史保留。本文只描述
候选合同；当前矩阵/联合历史/同保证对比、精确 Git tree、普通 FF 发布、自然 exact-head CI 的全部消费者和 owned cleanup 共同激活完成。
S20 NEXT / NOT STARTED / separate audit-only dispatch required；S19 不自证 Phase68 完成，A01–A22 的三层完成审计属于 S20。

## 范围与选定方式

S19 是审计边界之前的集成与保证 owner：在当前候选上让 S04–S18 已交付的能力在声明的查询矩阵、三条显式路线、两种入口与两种库来源上
组合运行，暴露真实组合缺陷，并完成必要的阶段末获取合并。没有新的语言/查询族、后端、公共执行 API/CLI、来源授权、v8、sink v2、
迁移、调度器、GC 算法、序列化器、缓存或 CI 拓扑。产品代码、`pyproject.toml`、`README.md` 与 `uv.lock` 计划不变，因此当前产品 wheel
就是 B19 自己的 wheel（S18 dist-final `cf81718b…3979`，同一语义构建身份）；若诊断出需要的产品修正，则按原定律窄修并重建当前 wheel
与全部 installed 见证。新增的只有测试侧组合与检查：`tests/_pietto_phase68_slice19_probe.py`、独立检查器
`tests/_pietto_phase68_slice19_check.py` 与薄入口 `scripts/phase68_slice19_probe.py`；S14 `r2_histories` 只增加可选 `routes`。

## 必需矩阵与独立成员

独立检查器从下层 case owner（S05 CASES、S06 追加、S10 的 R2_bound 与 PG 行域补充、S07 manifest）加字面目标限制与总数推导必需集合，
并与生产者的 `native_manifest(target)` / `r2_families(target)` 交叉核对；缩短的生产者清单无法通过。cell 身份为
`(target, route, group, case, variant, entry, origin, obligation)`：

| target | 路线 | 声明（普通/细化/guarded） | 命名排除（原 owner） | 准入 R2 | cells |
| --- | --- | --- | --- | --- | --- |
| postgres | postgres_rows、postgres_adbc | 166（54/57/55） | 无 | 62 | 1,328（R2 496） |
| mysql | mysql_rows | 164（52/57/55） | 5：普通与细化的 V_join_full/null_keys、A_window_groups/exclude（`original()` 拒绝），guarded full_unmatched（postgres_only） | 62（含 2 个排除） | 636（R2 240） |

普通与 guarded cell 是一次受检原生 attempt；准入 R2 cell 是一次 R2 捕获（page 2、至多 3 页、发布 [0,2]：非空时留下洞与晚到岛）、
不带终态地放弃，再由新进程以新鲜信任/访问/premise/guard、page 3 从位置 0 完整重新枚举、对账全部旧成员并补洞续写——这次恢复
同时是该 cell 的矩阵值/guard/终态观察（S10 `check_matrix_record` 与 S14 `check_recovery` 同时判它），之后删源，由新的无驱动
Arrow-only 进程读出每个恢复后的工作区。guarded refined_pages 的新鲜 guard 违例（drift）在每条路线 installed:bundle 上被恢复前拒绝且
checkpoint 不变。排除只由原 owner 的拒绝记录（`original()`/`case_preparation`），不以缺工具、预算或新失败冒充。

## 获取合并（阶段末）

审查基线为 Phase67 终态 `2f280ea02b974c0ab7e6e8e07017b960b55f850a` 到 B19 的全部 Phase68 测试/脚本增量。实现的共享：每个矩阵分区一个
数据库生命周期同时承载普通、guarded 与 R2 夹具（S06 `setup` + S16 `guard_sources`，替代 S10/S14 各自的 general/guarded 生命周期）；
每个声明 case 一次父进程参考构建与一个 bundle 供四个 cell、各路线与两种角色使用；细化 R2 只执行一次（历史上 S10 矩阵与 S14 R2 各
执行一次）；worker 程序文本每分区组装一次；S18 已校验 wheelhouse 的副本与一次安装的六个配方前缀供全部 S19 族使用；每分区每来源
一个 Arrow-only 读出进程。保持新鲜：资格认证、guard、publisher、SQLite 连接、接受、attempt、来源与故障切点。pytest 中重复的源码
编译（四个最重 Phase68 文件按 S18 托管健康数据约占 general-runtime 工时的 43%）判为 INTENTIONALLY_FRESH：每个断言拥有自己的新鲜
live 编译根，共享需要跨测试的可变产物图且在 loadfile 下依赖调度；757 s 单节点的关键路径属于已排队的性能插段。CI 才运行的已安装
消费者（C10）现在有显式本地入口 `consumer` 族：与 CI 同形的 package smoke、Arrow readiness 与 result product 加原检查器、以及
真实消费者 prepare/replay/verify——后者重放 S18 已核验的两份 phase66 回执，按其原始身份（35fb67af/37566435211/1，在 S19 提交前
等于本地 HEAD），不改写任何回执，报告标为 LOCAL。

## 联合历史与证据层

| ID | 位置 | 判据 |
| --- | --- | --- |
| 12 cell 下限 | `joint` 族 = 原 S18 `native()`：每路线 × live/bundle × source/installed 在各自路线安装中运行 S17 联合历史、union 路由与无回退、删源、丢失回复与无驱动尾部 | S6/S7 字面 oracle、S17 `check_all` 与 damages17、S18 检查器 |
| J01/J09 | 矩阵分区的数据库移除前：每路线 installed bundle 的 S14 B_holes、B_damage_value/B_damage_coordinate（协调损坏的旧成员在对账处拒绝且不被采纳）、C_reply_lost（洞+岛、补洞提交后回复丢失、再崩溃、第三次完成）、D_second_crash、G_source_drift、H_version_replaced | S14 `check_history` 与其 `checker_damage` 损坏族在 S19 raw 上重跑 + S19 谱系定律 |
| J02 | 同上：S15 原生 relay 在第二次本地确认前（sink 已提交）切断、新进程 S14 恢复、新的无驱动进程按同一身份重发、采纳恢复后的 checkpoint 并只交付其余；同键异值 CONFLICT | S19 效果定律（每个 occurrence 恰好一个效果、等值 occurrence 两个效果） |
| J03–J10 | `storage` 族：一个 v7 工作区内真实 Arrow chunk、真实子进程 SIGKILL（固定前缀 R1 的确认/未确认重发、发布提交前后切点与通知丢失、两种 cancel/publish 顺序、五个回收切点、读者/回收两种顺序与全部保护根、协调器死亡后恰好一次对账、过期与外来兼容拒绝、相同持久前缀的不同远端结果） | S19 `check_storage` 与 16 种协调损坏 |

模型（有界穷举）、受控注入、真实组件（SQLite/文件系统）、进程 SIGKILL 与原生证据分层记录，没有物理断电声明。每路线还运行原
控制族：S03 PG rows 产品用例、S09 PG ADBC 控制、S08 MySQL 控制（阻塞执行/取消/期限、早关、晚到失败、事务歧义、清理失败）。

## 同保证并发、安装与兼容

`tuning` 族：每条路线一对（serial workers=1 与 concurrent workers=3），相同查询/绑定/来源版本/隔离/guard/值/持久与回收保证，各自新
工作区与 sink namespace；小作业、多页大作业、慢 sink 背压与被取消作业；比较终态、精确值、等量工作与 S17 运行时定律，耗时只报告，
不要求加速（NO_MEASURED_SPEEDUP 合法）。`install` 族为 S18 `install()`（六配方、两个解析负例、损坏安装）；`compat` 族以原始存档字节
物化两个角色：S16（v7 拒绝）与 B19（直接前序，期望由从 wheel 字节重算的代码身份推出）。v1–v7、reference sink v1 不变，无迁移。

## 验证与交接

普通测试无数据库、无 Arrow：独立必需集合与生产者清单相等、清单五类损坏、证据类别、联合模型，以及 J01/J02/存储/矩阵/同保证
定律在受控数据上的接受与指定定律拒绝。真实证据只由显式族产生，原检查器与 S19 检查器在 worker 之外判定：`check` 族不读生产者的 checked 标记，在每个 cell 的 raw 上重跑 S10/S14 原定律与 R1 尾段，并在真实 raw 的副本上施加全部损坏族（含 S14 原 `checker_damage`），每个损坏须被指定定律拒绝。A01–A22 交接表、
完整成员、排除、联合历史、损坏、共享/新鲜/例外处置与剩余性能候选写入外部 S19 证据与最终报告，交给 S20 审计。

| 后续 | S19 提供 | S19 不实现 |
| --- | --- | --- |
| S20 | 当前全矩阵/R2/联合历史/同保证证据、A01–A22 映射、获取合并处置与剩余候选 | 三层完成审计与 Phase69 交接 |
| 性能插段 | 测量缺口与候选（关键路径单节点、源码编译成本） | CI 调度、分片或 worker 变更 |
