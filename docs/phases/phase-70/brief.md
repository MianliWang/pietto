# Phase70：开放/组合查询与显式命名值参数

所属 Stage：Phase82 公开冻结之前的 alpha 语言面扩展——让常见分析查询能在 Pietto 中完整表达，并经受检的编译与执行链得到正确结果（仓库没有数字 Stage，这里用描述性目标）。本期服务这一目标，Stage 不收尾。

Phase69 `COMPLETED / PUBLISHED`：S21 普通提交 `177c2e18906f22c3d42a9b0c9d65944d9af5a21d`，自然 CI38342155897/push/main/attempt1。
Phase69 之后插入的一期（下称插入期）连同同批维护 `COMPLETED / PUBLISHED`：首个发布头 `8dcc610c246ed5938e6b6b3789582bddec0bc385` 的自然 CI 失败并保留，
修复子提交 `de887b6219b0359b1b4ba0d225dbf66b3d01688b` 的自然 CI38489278446/push/main/attempt1 接受全部 required consumers。
本期规划基线为依赖升级批 head `8cc6d5cbdc89a90293f802397184403012703c91`（tree `95b25ff4c047e3f0465fdf87165801f07ccb7918`，自然 CI38501677796/push/main/attempt1）。
插入期的预算、证据与收尾不并入本期；Phase71 及以后编号不变。
本 brief、[20 片路线](slices.md)与[外部参考记录](planning-notes.md)随一次只含文档的路线发布提交发布：路线发布与 Phase70 开始都只在该普通提交的 FF push 与自然 exact-head CI 全部 job 成功后成立，此前是 candidate；尚无已合入的 Phase70 Slice。该句是路线发布时的历史状态；所有者决定见[决定记录](../../decisions.md)的 D70.01–D70.11。

## 实际收尾状态

本 brief 的路线、验收与 `PLANNED` 矩阵保留为 Phase70 的历史授权输入。原 20 行路线加 S04r/S04w/S05g/S05j 四个扩展构成 24 个规划位置；S04 拆为 S04a/S04b 后共有 25 个实际位置。其中 S01–S19 的 24 个位置已发布，最后一个位置是本候选 S20。S19 从 `6ac82d68` 发布 `0.1.3`；自然 exact-head CI `38809622132` 接受 19/19 jobs、36 artifacts，GitHub pre-release 和 PyPI 的公开字节已核验。S20 仍是审计 Slice，且只有它的一笔普通 FF 提交与自然 exact-head CI 成功后，Phase70 才以 25 个实际 Slice 闭合；成功后不再补交文档。Phase71 仍未开始，等待自己的 phase-initiation gate。

## R/A/C 与使命

**回看（事实）。**
1. Phase69 计划 21 片、实际 21 片，没有拆分；拆分风险按位置逐一评估，预列的拆分都未触发。
2. Phase69 有两个失败的已发布头（`bf252faf`、`8d7877d8`），都只在 hosted 环境的消费者上失败，由 `bf8c1344` 修复；封存前有两次本机权威验证失败（`271c751f`、`41f2cece`）；S02 候选的聚焦检查漏掉了既有执行 owner，非权威全量预检发现 9 个回归。
3. 插入期首个发布头因只在 CI 运行的读者失败（`ci.yml` 中改名 helper 的字面入口、未同步的目标 oracle），由子提交修复；一次权威验证中依赖当前工作目录的 `scripts` 导入使 46 个节点静默缺席，被独立收集计数发现。
4. Dependabot #84/#85/#87 因字面 pin 读者未同步而 PR CI 失败，同步后合批合入（CI38501677796）。
5. 插入期的新节点需要完整读者闭包，用了 5 次非权威全量预检才收敛。以上教训写入[工程教训](../../references/engineering-lessons.md)。

**教训与本期调整。**
- 只在 CI、hosted 或目标库运行的消费者与字面 pin 读者是失败头的主要来源 → 每个工作包列出它触及的共享模块的直接语义消费者；新增发射变体的片在 Gate 2 封存前对候选树本机跑完整 PG/MySQL 目标清单，改执行、模板、compiled 加载或 Arrow 的片同时用确切候选 wheel 跑原生执行族；新增或改名的入口在同一提交更新 `.github/workflows/ci.yml`。
- 新节点的读者闭包是头号返工源 → 设读者闭包加固片 S02（开局清单中按 AST 类分派的 468 个函数里 36 个静默跳过未知节点、3 个未分类且复判为存在静默路径，共 39 个入口），并由 S01 的前置准入门保证未解除的新节点不进入任何现有遍历器；
  直接读字段的读者（开局清单：`.from_clause` 109 处、`.source_name` 73 处真实读取、JOIN 99 处、定义循环 46 处、单输入硬约束 18 处）由解除准入的特性片在 Gate 1 各自核对；其中 `FromClause.source_name` 同时充当模块查找键、块内限定名与来源标签，派生查询片必须把三者拆开。
- 独立计数能抓住静默遗漏 → 每个 Gate 2 记录带独立收集计数与预期节点增量。

**现状能力（只列本期触及的部分）。**

| 档 | 能力 | 证据 |
|---|---|---|
| 可靠可用 | 项目模式平面查询：INNER/LEFT/CROSS/RIGHT/FULL/SEMI/ANTI JOIN（MySQL FULL 为已批准的不支持，PG FULL 只支持 Int 等值）、集合、DISTINCT、聚合、窗口、QUALIFY、ORDER/LIMIT，发射 PG 18.6 / MySQL 8.4.12 SQL | 自然 CI 目标 conformance、golden、`tests/test_sql_*` |
| 可靠可用 | 每个命名 producer 一个生成的非递归 CTE；SEMI/ANTI 发射为相关 `WHERE [NOT] EXISTS` | `tests/test_sql_joins.py` 两目标 VERIFIED |
| 可靠可用 | 插入期表达式面：字面量列表 `in`、条件式、函数、合格来源上的 Timestamp/UUID、派生 Date 结果 | CI38489278446，原生验收 |
| 可靠可用 | bind-safe 字面量槽：给值时必须给全，不给就用编译时字面量；按绑定重推值敏感事实；`PIE-R1004`/`PIE-R1006` 拒绝 | `tests/test_execution_binding.py` 等 |
| 可靠可用 | 公开执行 alpha：三条路线、bundle 导出/加载（代码身份兼容）、R1/R2 保存结果、`pyarrow==26.0.0` | CI38501677796 |
| 可靠可用 | Lean Gate v2：独立收集与严格覆盖、生成物/golden/包检查 | 自然 CI 19 jobs / 36 份 required artifacts |
| 能用但脆弱 | 只在 CI/hosted 运行的消费者与本机封存的一致性；字面 pin 读者；目标回执距 34 MiB 读者上限不足 1 MiB；生命周期文字在 CI 之后滞后到下一个生命周期提交；权威 3.13 环境随重启丢失，2026-10-14 经所有者授权重建；Teach 存储余量 | 上文回看；[开发文档](../../development.md)的回执记录 |
| 能用但脆弱 | 新节点种类的遍历器闭包（36 个静默跳过未知节点的函数） | 开局遍历器清单 |
| 只是代码存在 | `ProjectIRQueryBlockEffectEvidence`（全 UNKNOWN、无消费 rewrite）；readiness 框架硬编码 BLOCKED；compiled 允许一个 literal 多个 native use 但无真实生产者；`_specialize`（只在测试可达）；`ci_workload` 标记；CI health（可比样本不足） | 开局重绑 |
| 缺失 | 子查询、局部关系、FROM 派生表、VALUES、表函数、capture/LATERAL、命名参数与未绑定模板、零物理来源执行准入、查询级函数的运行时资格 | 开局重绑 |

**开局 CI health。** 基线自然 CI38501677796/push/main/attempt1 的 health 摘要（artifact `ci-health-38501677796-1-summary.json`，596,214 B，
sha256 `ff9d2d819a6644988150e3325dabcfe9bf81269522cb008de7b9be347c7fba25`，`pietto.ci-workload-health.v1`，policy sha256
`f252532dab16f38675833d36e14f353d7b85b8be92ba9d9e017de8933568a189`，topology 2）判定为 `INSUFFICIENT_EVIDENCE`、current screen `WATCH`：
只有 1 个可比样本（数值结论需 3 个中 2 个）；26 个信号为 FEWER_UNITS_THAN_WORKERS 4 个（结构性）、LONG_INDIVISIBLE_NODE 21 个（暂定）、
SHARD_IMBALANCE_WATCH 1 个（3.13 runtime，约 1.39 > 1.25）；成本记录不完整。这不是 green 或 HEALTHY 结论，也不授权任何调度、拓扑或资源政策改动。
3.13 最慢的十个节点都是 harness 差分/可移植节点（约 205–392 s）；3.12 前十中九个是 harness 节点，另一个是 `test_execution_compiled_source_free.py` 的 MySQL 节点（约 151 s）。
它们是阶段末获取整合与十个最慢节点 profile 复核（S18）的基线；任何改变收集节点集合的发布都会使历史不可比，本期大部分时间预计仍是 `INSUFFICIENT_EVIDENCE`，中点复查。

**路线图约束。** Phase71（NestedRelation）消费本期的组合计划；更广类型/nullability 在 Phase72、聚合代数在 Phase73、函数 SPI 在 Phase74、编辑器部分分析在 Phase75、优化器在 Phase88/89、递归在 Phase92、形式化改写认证在 Phase93。
按[产品架构](../../architecture/product-architecture-v1.md)，改写搜索与代价属于优化器侧平面，其内部拓扑由 Phase88–89 定；路线图 Phase 70 一行中的有界去相关已由所有者移出本期（D70.06），移交写在[路线图](../../roadmap.md#future-roadmap-v6)该节表格后的说明。

**使命。** 用户能把复杂查询拆成局部关系，按名字显式传入值，在过滤和投影里使用 scalar、EXISTS、IN 子查询，
在需要时显式引用外层行（相关子查询、LATERAL），并通过既有的受检编译与执行链得到正确的**平面**结果。
本期不建设数据库、优化器、关系值语言、嵌套结果或新的执行调度。

**终态（用户视角）。**
1. 一个查询可以在内部声明局部关系并多次使用，派生表先用 let 命名再作为 `from` 输入；名字、作用域和重复使用都有确定的规则和诊断。
2. 入口查询可以声明类型化的命名值参数；同一份编译结果（live 或 bundle）可以用不同的值反复执行，缺值、错型、不合法的 NULL 在执行前被拒绝。
3. scalar 子查询、EXISTS/NOT EXISTS、单列 IN/NOT IN 在 WHERE 和非分组查询的 SELECT 中按约定的 NULL/基数规则工作（分组查询的 SELECT 与其他子句位置确定拒绝）；需要外层行时必须显式捕获，LATERAL 支持左到右依赖与 LEFT 的 NULL 扩展。
4. VALUES 和一个有界的 PostgreSQL 表函数可以作为无物理来源的关系使用，并经明确的目标/执行准入运行。
5. 每种新形态在 PostgreSQL/MySQL 上要么生成经验证的 SQL 并原生执行通过，要么在编译期以确定诊断拒绝；旧的可靠能力不退化。
6. 用户能 `pip install pietto==0.1.3`（GitHub pre-release `v0.1.3` 与 PyPI 字节一致）使用以上能力；`0.1.2` 的 bundle 与保存作业按代码身份明确拒绝，不迁移。

**预算。** 历史规划为 24 个位置（含所有者 2026-10-14 要求的发行片 S19，以及同日扩容加入的 S04r、S04w、S05g、S05j），容量 25，余量 1（D70.09 及其 2026-10-14 修订）。22 是所有者批准的真实扩容，不是尺寸证明：Phase69 的 21 片已含发行与审计，本期新增发行范围，
且四个高风险片（S03、S04、S10、S11）与两个中高风险片（S01、S15）预列了拆分线，可能需要两处拆分；超过容量时按[路线](slices.md)的停止规则回到所有者。拆分后的 25 个实际位置包含本候选 S20；它们须在 S20 闭合条件成立后才全部发布，不重写历史 24 节点图。
截至 S19，保守修复核账为 causal 121 / focused 107 / diagnostic 156 / scope 6；当前上限为 causal 225 / focused 180 / diagnostic 270 / scope 9。它们保留 UNKNOWN 历史，且上限来自接近上限时所有者的一次性 50% 增加，不追溯改写早期授权。Teach 只做非权威预检，不计入也不替代 Gate 2；
不承诺墙钟时间；发行已按 D70.11 的所有者实际字节确认完成。

## 已锁定的输入

- 插入期与 Phase70 分开；Phase71 及以后编号不变；已闭合的 Phase69、性能/并行插段与扩展发布历史不重开。
- 一个规范集成者；隔离 worktree 中的 worker 按依赖并行开发；单一 writer、FF-only、自然 CI、一次权威验证、失败头保留、提交不加 AI 署名行。
- 语言规则（`AGENTS.md`）：冒号加空格缩进，不用花括号，不加多余关键字；新增词按既有软关键字机制引入，不使现有标识符失效。
- 公开 CLI/JSON 形状、诊断码与顺序、稳定 SQL、PostgreSQL emitter 不在未授权时改变；本期已批准的公开变化逐项列在 D70.03 与 D70.08。
- 已发行 `0.1.2` 字节不变；S19 已按 D70.11 完成 `0.1.3` 的所有者确认、GitHub pre-release 与 owner-operated PyPI 上传；这不开始 Phase71。

## 所有者决定

所有者采纳开局闸门的全部推荐，三个后定项也按推荐定下（[决定记录](../../decisions.md) D70.01–D70.11）：
- 命名值参数在入口查询头部声明、正文用裸名，调用用 `parameters={...}`；撞名报错；首批 Bool/Int/Float/Text；参数不进入 LIMIT、窗口范围、要求固定值的函数实参与 VALUES 单元格；值敏感检查记为绑定时义务、每次绑定重推（D70.01）。
- 未绑定模板可以检查、编译、发射、inspect/explain、导出与加载 bundle；执行与保存必须给全参数；R1 读取与 `recover` 须重述 `parameters=` 且与保存时逐个相等，否则 `BINDING_VECTOR` 拒绝（D70.02）。
- 写法 A：命名局部关系加按名引用。局部关系按 2026-10-14 所有者决定写作 `let 名字:`，只写在 table 或 query 体开头、`from` 之前，平级、不嵌套，体可以是 FROM 关系体、类型化 VALUES 或集合运算；派生表先用 let 命名再 `from`，没有内联块；`x in r`、`exists r`、`scalar r.c`、类型化 VALUES、`from generate_series(...) as n`；在局部关系里写 `capture`，外层字段只用限定名，把它 JOIN 进来即 LATERAL；同名一律报错，自相关须先用 let 给内层换名；新词全为软关键字；新增 8 个"暂不可用"诊断码（D70.03 及其 2026-10-14 修订）。
- 结果规则：scalar 0 行得 NULL、多行由数据库执行时报错并沿用 `PIE-R3003`（SQLSTATE 21000）；EXISTS 不为 NULL；IN 沿用三值逻辑；子查询只在 WHERE 与非分组查询的 SELECT 中；`capture` 只取外层 FROM/JOIN 行字段（D70.04）。
- 能力宽度：每个新形态做到公开执行并逐路线支持或拒绝，R2 默认拒绝；零物理来源在 PG 要求非空洞资格、MySQL 拒绝；表函数只做 PG `generate_series`，以 `pg_catalog` 限定并显式 bigint 发射、不另做运行时目录检查；IN 读取带 LIMIT 的闭合关系两库允许（只发射 CTE 形状），带 capture 的相关关系含 LIMIT 被 IN/NOT IN 读取时 MySQL 拒绝、PG 允许（D70.05）。
- 窄去相关移出本期（Phase88/93），表函数准入以外的 effects 权威归 Phase74/Phase88，"项目有语义错误时只编译所选 owner"的政策保持现行并移交 Phase75（D70.06）；数值上限（D70.07）；产物与已存格式的演进，新构造只在显式模块项目中提供（D70.08）；20 片 / 容量 22（D70.09）；许可、按依赖并行的实施授权、预算与 Teach 额度（D70.10）；阶段末发行 `0.1.3`（D70.11）。

## 内部架构决定（ARCHITECTURE_DECISION，可逆）

- AD1 语法先行加前置准入门：S01 一次落地全部已批准写法；准入门是新私有模块 `_syntax_admission.py` 中的纯函数（显式栈迭代、不缓存、按类查表），在两种模式最早的共同 AST 检查点调用：单文件 `semantic/analyzer.py` 的 `analyze()`（`_analyze` 之前）与项目 `_project/check.py`（覆盖 LEGACY_FLAT、EXPLICIT_MODULES、emit-sql 与 `compile_query`），给出确定的临时诊断并短路。
  备选是逐片增量改 grammar（每片都要重新生成不可合并的 parser 字节）、只事后追加诊断（新表达式类会先在现有遍历器里触发 `AssertionError`）、把门放在 `_project/model.py`（触及大量文本锁与诊断恒等不变量）或 `parser_api`（把"可解析但暂不可用"变成解析失败，违反公开 `ParseResult` 合同与分层）。
- AD2 局部与派生查询块是一等块，不合成隐藏的模块级声明或临时源文件；后者会让身份法则中声明与使用的区分失效。
- AD3 子查询用新的"表达式到块"依赖边（S08 先行交付的共享接线包）；capture 用独立的边种类与新增的 IR 阶段检查点；"恰好一个来源"的发射谓词一般化为按块的来源集合。把 capture 做成普通 use 会违反生产者先于消费者，把子查询塞进 JOIN 会失去 SELECT 位置。
- AD4 每个特性片交付该形态的 compiled 记录、至少一条公开路线、三路线逐一支持或拒绝与 R2 处置；compiled 记录族由集成者串行接线。
- AD5 读者闭包加固单独成片（S02），现有节点行为不变；测试是各层 owner 中"未知节点 → 确定失败"的单元测试，不枚举内部函数名、不加计数锁。
- AD6 运行时可见的公开表示变化（未绑定参数的 emit-sql/`CompiledQuery` 表示、scalar 多行错误的公开表现）放在引入它的特性片；S16 只做文档、诊断目录、inspection 与组合测试，因此 S16 与 S17 可以并行。

## 范围账本

- **必做**：语法先行与前置准入门（S01）；读者闭包加固（S02）；闭合派生查询与局部关系（S03、S05）；命名值参数与跨块传输（S04、S11）；VALUES 与零物理来源（S06）；
  闭合 scalar / EXISTS / IN（S07–S09）；显式捕获与相关 EXISTS（S10）；LATERAL（S12、S13）；相关 scalar/IN（S14）；有界表函数与最小 effects 证据（S15）；
  参数进入聚合之后与结果位置（S04r）；窗口函数中的参数（S04w）；计算分组键与 let 列聚合（S05g、S05j）；
  公共文档、诊断目录与组合整合（S16）；联合验收（S17）；获取整合与最终验证（S18）；发行 `0.1.3`（S19）；仅审计（S20）。
- **时间够才做**：只限同域补充示例与区分性反例；不开新的公开特性。
- **明确不做**：窄去相关与任何改写（Phase88/93）；MySQL 受限形态的等价包装与 `JSON_TABLE`（Phase77）；Decimal/Date/Timestamp/UUID 参数类型（Phase72）；参数进入 LIMIT、窗口 frame、要求静态值的函数实参、VALUES 单元格或表函数实参；
  表名/列名参数；关系函数或高阶查询参数；内层遮蔽外层；子查询出现在 WHERE 与非分组查询的 SELECT 以外的位置（含分组查询的 SELECT 项）；捕获外层 SELECT/聚合/窗口输出；MySQL 上带 capture 的相关关系含 LIMIT 并被 IN/NOT IN 读取（PG 允许）；
  NestedRelation（Phase71）；跨层聚合代数（Phase73）；更多表函数、函数 SPI、UDF（Phase74）；数据库深度适配（Phase76/77）；高强度真实库、差分与性能保证（Phase81）；公开冻结（Phase82）；
  表函数准入以外的 effects 权威（标量函数 effects 目录 → Phase74；供改写消费的 effects → Phase88）；优化器、memo、CSE、物化与求值次数承诺（Phase88/89）；持久增量缓存（Phase91）；递归（Phase92）；形式化改写认证（Phase93）；
  单文件模式与旧式平铺项目（LEGACY_FLAT）中的新构造（新构造只在 EXPLICIT_MODULES 提供；PACKAGE_ROOT 的 explain 沿用 Phase64 先例）；旧 bundle/workspace 自动迁移；Windows 支持声明；
  VS Code 扩展的修改或重新发布（发行 `0.1.3` 后扩展 0.1.0 会拒绝它，扩展跟进归扩展 owner）；TestPyPI、签名与 attestation；
  "项目有语义错误时只编译所选 owner"的政策（保持现行整项目结果政策，移交 Phase75 编辑器部分分析，D70.06）。

## 三层验收

每项都要有真实能力、明确 owner、接通的消费者和区分性反例；被排除形态的正确拒绝只覆盖排除本身，不证明正例；类名、文档 PASS 和旧回执不能单独满足验收。

| ID | 为真：用户能观察到 | 存在：必须有的身份/产物 | 接通与验证 |
|---|---|---|---|
| A01 局部/派生关系 | 局部关系与 FROM 派生表在作用域内正确工作，重复使用保持意义；同名、成环、越界引用、跨数据库族来源确定拒绝 | 块/声明/use/输出身份与列序、词法依赖、按块的来源集合 | 源码→语义→IR→计划→两方言 SQL→原生执行与独立 oracle；diamond 复用、内层 LIMIT 与外层 WHERE；compiled 导出与一条公开路线；**隐藏内层来源**：只在局部关系里读到的表与列出现在 compiled sources、PG source assurance roots、MySQL 闭包对象、R2 source inputs 与 requirement report，缺失即确定拒绝 |
| A02 命名参数 | 一次编译多次绑定；缺值、错型、非法 NULL 在执行前拒绝；值敏感事实按绑定重推 | 参数声明/引用/占位符映射；未绑定模板状态（第三条状态轴）与逐操作准入；bundle 记录与绑定描述 | emit-sql 未绑定表示、compiled 模板、bundle 导出/加载、三路线 execute/save 的命名绑定；单块与跨块重复使用（PG `$n` 复用、MySQL 重复 `?`）及 guard/refinement 重渲染；反例：溢出在绑定时拒绝、NULL 与缺值区分、旧或外来 bundle 被拒、参数进入 LIMIT/VALUES/表函数实参被拒（S06/S15 先实现"只接受字面量"；含真实命名参数的反例由 S04 与 S06/S15 中较后合入者负责） |
| A03 VALUES | 空、全 NULL、重复行正确；显式列与类型；错宽错型拒绝 | 类型化 shape；零物理来源合同；两方言拼写与显式别名 | 纯 VALUES（PG 非空洞资格、MySQL 明确拒绝）；与物理表 JOIN/集合两目标原生执行；R2 精确拒绝或坐标基础 |
| A04 scalar | 0/1/多行行为正确；空输入聚合的一行与零行子查询区分 | 单列、基数与 nullable 事实、错误投射 | 两目标原生强制求值的正反例；多行错误为 `PIE-R3003` 加 SQLSTATE 21000；隐藏内层来源见证；**失败相关表达式**：外层未选取的列、子查询内层投影中的 scalar 或除法仍在静态检查与需求/失效闭包中，既不删除也不强制求值；cleanup |
| A05 EXISTS/IN | WHERE 与非分组查询的 SELECT 位置结果正确；NULL、空、重复、LIMIT 正确；`NOT IN` 不当 ANTI；分组查询的 SELECT 与其他子句位置确定拒绝 | existence/membership 事实、三值规则、目标形态 blocker | 三值真值表 oracle；两目标原生；IN 读取带 LIMIT 的**闭合**局部关系在两目标原生执行（MySQL 只出现 CTE 形状，直接形状永不生成）；隐藏内层来源见证；EXISTS 内层投影的完整静态检查（同 A04 失败相关表达式）；分组查询 SELECT 与 let/JOIN ON/GROUP BY/SATISFYING/QUALIFY/ORDER BY 位置的拒绝反例 |
| A06 capture/LATERAL | 显式相关与 LEFT LATERAL 保留正确的外层出现；同值外层重复行各自独立 | capture 边（外层块/use/阶段/字段）、新阶段检查点、NULL 扩展事实 | 外层重复、右侧 0/1/多行、ON 与 WHERE、Top-K 总序；捕获外层 SELECT/聚合/窗口输出、未声明捕获与分组查询 SELECT 中捕获的拒绝反例；外层字段只能以限定名访问（与内层同名字段不冲突、外层加字段不改变内层裸名）；capture 绑定名与内层输入同名（自相关）的拒绝反例，以及用局部 `query` 换名后的正例；MySQL 上带 capture 的相关 IN 读取含 LIMIT 的关系确定拒绝、PG 原生执行；capture 读到的外层来源进入依赖与失效闭包 |
| A07 表函数 | 一个有界表函数真正运行 | 函数意义、选定 native overload、域/行数上界、运行时资格或明确 NOT CLAIMED | PG 原生正反例（step 0、NULL、超上界、参数实参被拒；发射为 `pg_catalog` 限定并显式 `pg_catalog.int8`，在 `search_path=pg_catalog` 会话下按确切发射形状实测，避免选中 integer 重载）；零物理来源的 PG 资格记录写明"无关系根、函数身份由限定发射固定、未查目录"；不另做运行时目录检查（D70.05）；MySQL 明确不支持 |
| A08 effects 权威 | UNKNOWN effects 从不升格为 pure/确定/全函数；本期没有任何改写 | 非 UNKNOWN effects 证据及其来源、compiled 承载 | 表函数准入消费显式 effects 事实；**反例**：effects 为 UNKNOWN 的函数不能通过表函数准入（现有标量函数调用不受影响）；没有任何变换因缺证据而发生 |
| A09 公开产物与消费者 | emit-sql JSON、诊断码/顺序/位置、源映射、bundle 与安装后的消费者可用 | 新旧格式与 feature 标记、完整事实集合 | 各特性片首次接通，尾部整合；解码器拒绝未知键；包检查；自然 CI 19 jobs / 36 份 required artifacts |
| A10 回归与生命周期 | 旧可靠能力不退化；旧 bundle/作业按代码身份明确拒绝、不迁移；所有现有合法源码在新语法下解析不变 | 完整义务映射、版本/存储/权限边界、生命周期记录 | S01 的语法回归（现有语料零新错误、零新精确歧义；token 文本与位置不变，token 类型只允许新软关键字从标识符变化，把新词归一为标识符后解析树全同）；S02 的行为不变；权威全量（17,553 加预期增量）；原生执行族；阶段末获取整合与 profile 复核；自然 CI |
| A11 发行 `0.1.3` | `pip install pietto==0.1.3` 可用并包含本期能力；GitHub pre-release `v0.1.3` 与 PyPI 字节一致 | 版本读者、release notes 与兼容说明；接受的 wheel/sdist 字节；GitHub draft 核对记录 | 一次正式构建（从已提交归档）；GitHub 自动源码归档与 Python sdist 分开审阅；多环境安装、三路线/R2、信任拒绝与 owned cleanup；上传后字节比对；回退政策（不覆盖已发字节、yank 由所有者执行、修复走 `0.1.4`）写入 release notes；旧 `0.1.2` bundle/作业按代码身份拒绝；自然 CI 在发行提交上全绿 |
| A12 计算分组键与 let 列聚合 | 项目模式下按 let 计算值分组、对 let 列做 min/max 结果正确（含 JOIN 输入与依赖参数的键）；单文件仍拒绝 | 计算分组键事实（LET_DERIVED）、保守 grain、扇出保护 | 两库原生（含 MySQL CTE 形状）、独立 BAG oracle、参数为 0 等取值的分组塌缩见证；GROUP BY 只引用限定列 |

## 需求矩阵（状态均为 PLANNED）

需求 → 首个 owner → 输入/档位 → 可观察行为 → 独立证据 → 状态。档位：PG 18.6 / MySQL 8.4.12，三条路线（PG 行、MySQL 行、PG ADBC），项目显式模块模式。

| 需求 | 首个 owner | 输入/档位 | 可观察行为 | 独立证据 | 状态 |
|---|---|---|---|---|---|
| A01 局部/派生关系 | S03（复用 S05） | 两库、三路线 | 作用域内正确，重复使用保持意义 | BAG oracle、两库原生、隐藏内层来源见证 | PLANNED |
| A02 命名参数 | S04（传输 S11） | 两库、三路线、bundle | 一次编译多次绑定，缺值/错型/非法 NULL 在执行前拒绝 | 绑定时义务复核、重渲染比对、原生执行 | PLANNED |
| A03 VALUES | S06 | PG 资格、MySQL 拒绝 | 空/全 NULL/重复行正确 | 两库原生、零来源资格记录 | PLANNED |
| A04 scalar | S07（相关 S14） | 两库 | 0/1/多行规则 | 原生强制求值正反例、SQLSTATE 21000 | PLANNED |
| A05 EXISTS/IN | S08、S09（相关 S14） | 两库 | 三值逻辑、位置规则 | 真值表 oracle、两库原生 | PLANNED |
| A06 capture/LATERAL | S10（LATERAL S12/S13） | 两库 | 外层出现与 NULL 扩展正确 | 外层重复与 Top-K 反例、原生执行 | PLANNED |
| A07 表函数 | S15 | PG；MySQL 拒绝 | 有界运行 | 原生正反例、确切发射形状实测 | PLANNED |
| A08 effects 权威 | S15 | — | UNKNOWN 不升格 | 表函数准入反例 | PLANNED |
| A09 公开产物与消费者 | S01 起各特性片（S16 汇总） | 公开 JSON/诊断/bundle/安装 | 形状与码稳定、新标记可用 | 解码器拒绝未知键、包检查、自然 CI | PLANNED |
| A10 回归与生命周期 | S01、S02（S17/S18 汇总） | 全量、原生执行族 | 旧能力不退化 | 权威全量与独立收集计数、自然 CI | PLANNED |
| A11 发行 `0.1.3` | S19 | wheel/sdist、GitHub、PyPI | 可安装且字节一致 | 正式构建、安装核验、上传后比对 | PLANNED |
| A12 计算分组键与 let 列聚合 | S05g（JOIN：S05j） | 两库、项目模式 | 分组与 min/max 正确 | 原生执行、独立 oracle | PLANNED |

## 逐形态分级骨架

值为负责的片；"拒"表示本期确定拒绝；细行在各片 Gate 1 填写。

| 形态 | 语言有效 | 计划完整 | 可发射（PG / MySQL） | 路线可消费 | 保存与 R2 |
|---|---|---|---|---|---|
| 派生表（let 命名后 from） | S01 | S03 | S03 / S03 | S03 | S03 定（有坐标基础则开放，否则拒） |
| 局部关系（含复用、前向引用） | S01 | S03、S05 | S03 / S03 | S03 | S03/S05 定 |
| 命名参数（单块 / 跨块） | S01 | S04 / S11 | S04 / S04 | S04 / S11 | S11 按 D70.02 |
| VALUES | S01 | S06 | S06 / 拒（纯零来源） | S06 | 普通保存 S06 定；R2 拒（无坐标基础） |
| 闭合 scalar | S01 | S07 | S07 / S07 | S07 | S07 定 |
| 闭合 EXISTS | S01 | S08 | S08 / S08 | S08 | S08 定 |
| 闭合 IN（含内层 LIMIT） | S01 | S09 | S09 / S09（只 CTE 形状） | S09 | S09 定 |
| capture 与相关 EXISTS | S01 | S10 | S10 / S10 | S10 | S10 定 |
| CROSS/INNER LATERAL | S01 | S12 | S12 / S12 | S12 | S12 定 |
| LEFT LATERAL | S01 | S13 | S13 / S13 | S13 | S13 定 |
| 相关 scalar / IN | S01 | S14 | S14 / S14（相关 IN 加 LIMIT 拒） | S14 | S14 定 |
| `generate_series` | S01 | S15 | S15 / 拒 | S15（PG 路线） | 普通保存 S15 定；R2 拒（无坐标基础） |
| 参数用于 SATISFYING/QUALIFY/ORDER BY/count-avg | S01 | S04r | S04r / S04r | S04r | 按 D70.02 |
| 参数用于窗口函数 | S01 | S04w | S04w / S04w（`NTH_VALUE(x, ?)` 实测前拒） | S04w | 按 D70.02 |
| 计算分组键与 let 列 min/max（项目模式） | 现有语法 | S05g、S05j | S05g / S05g | S05g | S05g 定 |

## 回归（必须仍然正常）

现状能力表中"可靠可用"的六行；以及现有诊断码、顺序与位置，CLI JSON v1 / project JSON v2 / metadata v1 的形状，golden SQL 字节，三条执行路线与保存/恢复流程的既有支持域。
回归按真实功能义务定位，不锁定 17,553 这个节点数或任何文件名。

## 17 节结论与 30 项映射（紧凑）

| 节 | 结论 | 30 项 |
|---|---|---|
| R/A/C | 见上文事实、能力表与路线图约束 | 1、6、17、18、28 |
| B/J0 | 使命与终态如上；24 片 / 容量 25 | 2、7、8、12、29 |
| D 预埋 | 只预埋前置准入门与读者闭包加固（不做的代价：每个特性片都可能把新节点送进静默遍历器，得到没有诊断的错误结果）；compiled 的未绑定模板表示随参数片做（不做的代价：bundle 不能携带模板） | 3、4、5、15、16 |
| E 推迟 | 见"明确不做"，每项有 owner 与回收条件（对应 Phase 的开局闸门） | 28 |
| F 扩展 | 不收新特性；只收同域示例与反例 | 2 |
| G 外部借鉴 | PostgreSQL 18.6、MySQL 8.4.12：ADAPT，作为目标行为与反例来源，不搬隐式 LATERAL、`ROWS FROM`、`column_0` 列名、VALUES 混型；不为绕过 MySQL 错误 1235 包装直接形状——闭合的命名关系本来就发射为 CTE，带 capture 的相关形状在 MySQL 上拒绝；DuckDB 与 Neumann–Kemper：ADAPT，只用于"去重绑定、不去重外层行"的论证，不采用一般去相关。每个参考的 11 字段记录见[外部参考记录](planning-notes.md) | 10、11、22、23、24 |
| H/I/S | 见所有者决定与三项风险 | 9、13、14、19、25、26、27、30 |
| J/V/K/L/Q | 三层验收与回归如上；V：不改 `AGENTS.md`，本期不变量写在本 brief，各片 Gate 0/1 必读；K：路线图表格被生命周期读者逐字锁定，不改表格行，去相关的移交写在表格后的说明与决定记录；L：见[路线](slices.md)；Q：三轮独立检查，发现按根因处置 | 20、21、29 |

路线发布时 30 项都已闭合，或已定阶段级规则、只把实现级名称、诊断码与逐形态行留给指定片的 Gate 1；三个后定项已按推荐定下，不是 UNKNOWN。

## 三项风险

1. **前置与接缝漂移**：参数（第三条状态轴）、局部块身份、capture 与"表达式到块"接缝比预期大；compiled 记录族几乎被每片触及。应对：语法先行与前置准入门、接缝检查点、各片 Gate 1 定稿接口；超出单片尺寸按预列拆分处理。
2. **语义与目标正确性**：错误时机、三值逻辑、外层阶段、零来源关系、R2 组合、MySQL 形态限制、隐藏内层来源和新节点读者闭包容易被单层测试漏掉。应对：每片首个真实消费者、区分性反例、逐形态目标矩阵与读者闭包加固；未知不升格为通过。
3. **并行与集成成本**：grammar、AST、中央分派、compiled 记录与目标回执是共享写面，重测试与数据库争用会吃掉并行收益。应对：单一共享接线 owner、私有写面工作包、就绪调度、固定候选上的分层验收、输入敏感失效。
