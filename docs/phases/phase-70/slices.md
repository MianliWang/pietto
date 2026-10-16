# Phase70 route — 20 rows

Phase70 负责开放/组合查询与显式命名值参数（[路线图](../../roadmap.md) Future Roadmap v6 中 Phase 70 一行，以及把 open caller-rebindable query parameters 映射到 Phase70 的段落；该行中的有界去相关已由所有者移出本期，见路线图该节表格后的说明）。
路线发布时的历史记录：本路线随一次只含文档的路线发布提交发布：路线发布与 Phase70 开始都只在该普通提交的 FF push 与自然 exact-head CI 全部 job 成功后成立，此前是 candidate；尚无已合入的 Phase70 Slice。

## 实际生命周期状态

本文件的 20 行路线与其 24 节点、47 条硬依赖边是规划时的历史图，不因实际拆分或收尾而重算。原 20 行路线加 S04r、S04w、S05g、S05j 四个扩展构成 24 个规划位置；S04 拆为 S04a/S04b 后共有 25 个实际位置。其中 S01–S19 的 24 个位置已发布，最后一个位置是本候选 S20。S19 已从 `6ac82d68` 发布 `0.1.3`，其自然 exact-head CI `38809622132` 为 19/19 jobs、36 artifacts。S20 只做审计；在它的一次普通 FF 提交与自然 exact-head CI 成功前，Phase70 不宣称闭合。该条件满足后，实际总数为 25 个 Slice，且不再追加文档提交。
下表是覆盖与依赖基准；每个 Slice 在自己的 Gate 0/1 展开时绑定精确输入、写集、命令、验收与成本。三层验收 A01–A11 见 [brief](brief.md)，外部参考见[外部参考记录](planning-notes.md)，所有者决定见[决定记录](../../decisions.md)。

## 授权与依赖顺序

所有者授权 S01–S20 按依赖并行实施（D70.10）：在隔离 worktree 开发，就绪片按既有批次规则每片一个普通提交，以批次最终树的一次权威验证、一次 FF push 与自然 exact-head CI 发布。
tag、GitHub release 与 PyPI 上传只在 S19 按 D70.11 进行：S18 全绿后所有者对实际 HEAD 与已接受字节确认一次"发行"，PyPI 由所有者本人输入 token 上传。
每片开工前重新绑定 main；遇到 BLOCKER、拆片，或新的公开、信任、预算决定即停。三个后定项已按推荐定下，不再挡住任何片：scalar 多行错误沿用 `PIE-R3003`（D70.04）；命名绑定在 R1 与 R2 中与 `values=` 同规则（D70.02）；查询级函数以 `pg_catalog` 限定发射固定身份、不另做运行时目录检查（D70.05）。

检查点只约束合入顺序，不约束开始开发；草稿、早期 worktree、候选或非权威运行都不授权合入、验证、发布或开始另一个 Slice。

## 排序策略

| 策略 | 利 | 弊 |
| --- | --- | --- |
| 风险优先（先做 capture、参数） | 最大未知最早暴露 | 在块身份尚未存在时做最难的部分，返工大 |
| **先打通最细端到端链路再加厚（选定）** | 先落语法与读者闭包，再让一条闭合派生查询走到原生结果，各特性在同一身份上加厚 | 共享接缝早定，接缝错误会波及多支 |
| 价值优先（先做最常用的 IN/scalar/参数） | 用户最快受益 | 没有块身份与来源集合就无法正确实现子查询 |

## 路线发布与冻结前实验（不编号）

- 路线发布（本提交）只含文档：本路线、[brief](brief.md) 与[外部参考记录](planning-notes.md)、[决定记录](../../decisions.md)的 Phase70 节、`docs/status.md` 与 `docs/roadmap.md` 中的生命周期文字、Phase69 与 Post-Phase69 插入期的[工程教训](../../references/engineering-lessons.md)，以及非包文档中滞后文字的更正。不编号，沿用 Phase69 路线锁定的先例。
  Future Roadmap v6 表格被生命周期读者逐字锁定，不改表格行；去相关、effects 权威剩余部分与 selected-owner 政策的移交写在该节表格后的说明。`README.md` 中滞后的 `0.1.2` candidate 措辞与 Timestamp/UUID 限制是包输入，随第一批改动 `src/**` 的提交与包检查一起更正。
- 冻结前小实验：经所有者授权，2026-10-14 已在 PG 18.6 / MySQL 8.4.12 各运行 1 次（断网、一次性容器、只读 SQL）并全部清理；结果只作证据，用来定稿各片 Gate 1 的形态与错误码细节，见[外部参考记录](planning-notes.md)。

## 路线

每个特性片的"完成"都包括它**自己的首个真实消费者**：源码 → 语义 → IR → 计划 → 两方言 SQL（`emit-sql --project`）→ 本机 PG/MySQL 目标执行与独立 oracle；
该形态的 compiled 记录与至少一条公开 `execute()` 路线；三条路线逐一支持或精确拒绝；R2 逐形态处置（有坐标基础则正例，否则精确拒绝）；只在子查询/capture 中出现的来源进入 compiled sources、来源资格、R2 source inputs 与 requirement report。
被排除的形态以确定诊断拒绝，这只覆盖排除本身，不证明正例。整合与验证的三片（S16–S18）不补实现；发行片（S19）只发行已接受的最终候选；审计片（S20）只审计。

| Slice | Outcome | Hard prerequisites | Acceptance | Split risk |
| --- | --- | --- | --- | --- |
| S01 | **语法先行与前置准入门**：落地全部已批准写法（grammar 含 QUALIFY 重复语法、AST、builder，新词全为软关键字）；前置准入门位于 AST 构造之后、任何语义读者之前（现有 `syntax_diagnostics()` 在完整分析之后才收集，不能充当此门）：新建私有模块 `_syntax_admission.py`（纯函数、显式栈迭代、不缓存、按类查表），两个调用点为单文件 `analyze()`（`semantic/analyzer.py`）与项目 `_project/check.py`（同时覆盖 LEGACY_FLAT、EXPLICIT_MODULES、emit-sql 与 `compile_query`），不改 `_project/model.py`、`parser_api.py` 与 `_flat_relational_admission.py`；每个已批准家族一个新诊断码（S23xx 段当前最高为 `PIE-S2344`，新码自 `PIE-S2345` 起在该段连续分配，所有 check-mode 下都是 ERROR）；新 body/输入以显式和类型表示，每个家族是带自身 span 的独立 AST 类（查询头参数也建成节点），不冒充 `FromClause.source_name`；两种模式下每个新形态只得到该诊断、不抛异常的行为测试；`docs/language.md` 记"可解析但暂不可用"。本期门对单文件与 LEGACY_FLAT 保持拒绝，特性片只对 EXPLICIT_MODULES 解除 | — | A09, A10 | 中高 |
| S02 | **读者闭包加固**：按 AST 类分派的清单中，36 个静默跳过未知节点的函数（含 `_flat_relational_admission.syntax_diagnostics`）与 3 个复判为存在静默路径的函数（`project_sql_plan._blockers`、`build_project_sql_plan`、`project_sql_plan_verification._result_structure`），共 39 个入口改为对**新类**失败关闭；用固定的已知类集合做精确类守卫，不用动态枚举子类，现有类的回退行为逐字节不变（含无限定 `DottedNameExpr`、metadata 的 `SetRelationDef → "unknown"`、各叶子与短路路径、两份独立 ORDER 比较）；写集约 21 个源码文件与 22 个**现有**测试 owner（与 S01 无共享文件），不新增测试文件、fixture 或导出；测试以测试内定义的未知节点类驱动，不枚举内部函数名，不加计数锁。直接读字段的读者（`.from_clause` 109 处、`.source_name` 73 处真实读取、JOIN 99 处、定义循环 46 处、单输入硬约束 18 处）不在此清单内，由解除对应准入的特性片在 Gate 1 核对 | — | A10 | 中 |
| S03 | **闭合派生查询与局部关系**：局部/派生块成为一等块；把 `FromClause.source_name` 的三重身份（模块查找键、块内限定名、来源标签）拆开，局部名不进入模块符号表、元数据不按全局名任选定义；按块的来源集合（一般化三处"恰好一个来源"发射谓词与两处下游检查）；`let 名字:` 局部关系（平级、不嵌套、封闭作用域、同名报错）与派生表（let 加 `from`）；跨数据库族来源沿用失败关闭；隐藏内层来源见证；失败相关表达式留在需求/失效闭包；project check/explain JSON 是否暴露局部关系或嵌套来源在本片 Gate 1 定（暴露即换新版本标记） | S01, S02 | A01, A09 | **高** |
| S04 | **命名值参数**：头部声明与引用、单块内重复引用（PG `$n` 复用、MySQL 重复 `?`、guard/refinement 的 `server_index` 映射的首个真实生产者）、第三条状态轴与逐操作准入、绑定时重推与绑定期义务、typed NULL、`emit-sql` 与 `CompiledQuery` 的未绑定表示、一条路线的 `parameters=` | S01, S02 | A02, A09 | **高** |
| S04r | 参数进入聚合之后与结果位置：参数及依赖参数的值可用于 SATISFYING 的比较、QUALIFY、经 let/select 建立的 ORDER BY 键（DISTINCT 下参数叶子视同常量；ORDER 树中的参数出现只作匹配、不分配原生占位符）、对依赖参数的 let 列做 count/avg（可空参数绑定为 NULL 时 avg 得 NULL）；只沿用 `int_range_representable` 与 `text_result_width` 两种绑定时义务；其余位置给确定诊断 | S04 | A02, A09 | 中 |
| S04w | 窗口函数中的参数：值实参与 lag/lead 默认值；lag/lead 偏移量、ntile 分桶数、nth_value 位置用新的"结构计数区间"绑定时检查（非负、PG 不超过 int4、参数须 not null，可空性按"可能为空"）；先做两库原生实测，MySQL `NTH_VALUE(x, ?)` 实测前确定拒绝；窗口 PARTITION BY 与窗口内 ORDER BY 仍只接受直接字段 | S04 | A02, A09 | 中高 |
| S05 | 局部关系的重复使用、前向引用、无环检查、diamond、嵌套上限、内层 LIMIT 与外层 WHERE | S03 | A01, A09 | 中 |
| S05g | 计算分组键与 let 列聚合（项目模式，不带 JOIN）：let 计算出的值可作 GROUP BY 键（provenance 为 LET_DERIVED，计算键一律不贡献反向 grain 依赖），let 列可做 min/max；发射复用 let 阶段的列，GROUP BY 只引用限定列（不重复表达式，避开 MySQL 1055），补 MySQL CTE 形状的原生用例；依赖参数的分组键随之支持（与 S04 中后合入者负责组合用例）；单文件模式仍拒绝（semantic metadata v1 的 `group_keys` 不变） | S01, S02 | A12, A09 | 中高 |
| S05j | 带 JOIN 输入的计算分组键：扇出保护与 grain linkage 记录计算键依赖的 JOIN 侧；occurrence-safe 规则沿用 | S05g | A12, A09 | 中高 |
| S06 | typed VALUES 与零物理来源接缝（独立的 VALUES body 与行 schema，不进入命名关系降级，零外部输入的合法 IR 根；发射总写列别名；PG 非空洞资格（最低内容：会话上下文核验——版本 180006、`search_path=pg_catalog`、隔离级别与只读——premise 至少含 `pg_catalog`，资格记录写明"无关系根、未查目录"）、MySQL 纯零来源拒绝、VALUES 单元格只接受字面量；资源与终止规则：行数由表头与 D70.07 上限静态确定） | S03 | A03, A09 | 中 |
| S07 | 闭合 scalar 子查询（`scalar r.c`；0/1/多行、空输入聚合区分；多行错误为 `PIE-R3003` 加 SQLSTATE 21000，D70.04） | S03（+ S08 接缝包） | A04, A09 | 中 |
| S08 | 闭合 EXISTS / NOT EXISTS；**先行交付"表达式到块"共享接线包**（IR、plan、两套 verifier、compiled 各一处），合入后 S07/S09 消费其接口版本 | S03 | A05, A09 | 中 |
| S09 | 闭合单列 IN / NOT IN（三值逻辑，与字面量列表 `in` 共存；闭合关系的内层 LIMIT 只以顶层 CTE 形状发射，MySQL 不支持的直接形状永不生成；两库 `NULL IN (空子查询)` 已实测一致） | S03（+ S08 接缝包） | A05, A09 | 低 |
| S10 | 显式 capture 与首个相关 EXISTS：capture 写在 let 体开头、独立的 capture 边、外层块/use/阶段/字段身份、新增 IR 阶段检查点；只可捕获外层 FROM/JOIN 行字段，且只能以限定名访问、不参与裸名查找；capture 绑定名与内层输入同名（自相关）时报错 | S03, S08 | A06, A09 | **高** |
| S11 | 参数跨块、未绑定模板的 bundle 传输、三路线与保存流程中的命名绑定（R1/R2 按 D70.02：新建执行与保存可用新值，R1 读取与 `recover` 须重述且逐个相等） | S04, S05 | A02, A09, A10 | **高** |
| S12 | CROSS / INNER LATERAL（带 capture 的局部关系作 JOIN 右侧） | S10 | A06, A09 | 中 |
| S13 | LEFT LATERAL 与 NULL 扩展 | S12 | A06, A09 | 低 |
| S14 | 相关 scalar 与 IN 组合（外层重复行保持；带 capture 的相关关系含 LIMIT 并被 IN/NOT IN 读取时，MySQL 上确定拒绝、PG 原生执行——它放不进顶层 CTE，本期不做包装；Gate 1 可先实测一个不需要包装的相关形状，若要放开须回到所有者） | S07, S09, S10 | A04, A05, A06, A09 | 中 |
| S15 | 首个有界原生表函数加最小 effects 证据：PG `generate_series(bigint,bigint,bigint)`，发射为 `pg_catalog` 限定并显式 `CAST(… AS pg_catalog.int8)`（开工 Gate 1 先在 `search_path=pg_catalog` 会话下按确切发射形状实测）；实参只接受静态字面量、非 NULL、行数上界；新的输入变体（调用、别名/绑定、行 schema、函数与 effects 权威分开保存，来源标签用函数出现身份）；放开 6 处"只允许 UNKNOWN"闸门中表函数准入所需的部分；运行时资格按 D70.05 不另做目录检查并写入文档 | S06 | A07, A08, A09 | 中高 |
| S16 | 公共文档、诊断目录、inspection 与跨特性组合测试（不改发射核心与公开 facade 的运行时表示）；release notes 草稿 | S05, S06, S09, S11, S13, S14, S15, S04r, S04w, S05j | A01–A10, A12 | 中 |
| S17 | 执行/bundle/保存/读取在同一冻结候选上的联合验收（只验证，不实现） | S05, S06, S11, S13, S14, S15, S04r, S04w, S05j | A09, A10 | 中 |
| S18 | 获取整合、十个最慢节点 profile 复核、修复与最终候选验证 | S16, S17 | A09, A10 | 低 |
| S19 | **发行 `0.1.3`**（沿用 Phase69 S20 先例，D70.11：S18 全绿后所有者对实际 HEAD 与已接受字节确认一次"发行"，与 PyPI 上传同时进行）：按登记的版本读者一次改齐版本号、release notes 与兼容说明（`0.1.2` 的 bundle/作业按代码身份拒绝、不迁移；VS Code 扩展 0.1.0 不兼容）；受影响验证；从已提交归档做一次正式构建并接受该 wheel/sdist；GitHub 自动源码归档与 Python sdist 分开审阅；回退政策（不覆盖已发字节、yank 由所有者执行、修复走 `0.1.4`）；多环境安装、三路线/R2、信任拒绝与 owned cleanup；GitHub draft 核对后发布 pre-release `v0.1.3`；PyPI 由所有者本人输入 token 上传，上传后核对字节一致；无 TestPyPI、签名、attestation、依赖升级或新功能。**实际完成：** `6ac82d68`、CI `38809622132`（19/19 jobs、36 artifacts）、GitHub pre-release 与 PyPI byte-verified。 | S18 | A09, A10, A11 | 低 |
| S20 | 仅审计：三层验收、回归、发行字节、复盘、Phase71 交接。**闭合条件：** 本 Slice 的一笔普通 FF 提交及其自然 exact-head CI 成功；随后不得为收尾另加文档提交。 | S19 | A01–A11 | 低 |

规划结构：24 个节点、47 条硬依赖边、无环、最长路径 10（如 S02→S03→S08→S10→S12→S13→S17→S18→S19→S20）、ASAP 最大层宽 8；容量 25、余量 1（2026-10-14 所有者扩容，见[决定记录](../../decisions.md)）。S04r、S04w、S05g、S05j 不在最长路径上；S05g 只依赖 S01、S02，可与 S03、S04 并行。开局 S01 与 S02 并行；S03 完成后 S04–S09 共 6 个逻辑就绪，
但只是逻辑就绪，真实并发受共享写面限制，共享热点由单一接线 owner 串行接线。S07/S09 对 S08 的依赖是**包级**（只等接缝包），不是整片依赖。

## 超过 25 片时的停止规则

预列拆分线：S01（**按家族拆**，每片同时带 grammar、AST、门表项与行为测试；不能把 grammar/AST 与准入门拆成两片，否则中间提交会让新节点进入现有遍历器，main 历史上出现失败开放状态；两次 grammar 重生成须串行）、S03（块身份与来源集合到 emit-sql/目标执行一片，compiled 与公开路线一片）、S04（语义/计划/发射表示一片，compiled 模板/绑定/公开入口一片）、
S10（capture 身份与阶段检查点一片，相关 EXISTS 纵向一片）、S11（跨块与 bundle 一片，三路线与保存流程一片）、S15（effects 证据与运行时资格一片，表函数纵向一片；开工 Gate 1 重估）、S04w（值实参与默认值一片，结构计数实参一片）、S05g（分组键事实与 IR 一片，计划与发射一片）。
余量 1：一处拆分到 25，第二处超过容量。超过时停下，出一份只含下表取舍的小决策单交所有者；容量不自动增加；一个备用位置不能同时承接多处独立拆分（D70.09）。

| 取舍 | 腾出 | 影响与风险 | 谁来定 |
| --- | --- | --- | --- |
| 合并 S12 与 S13 | 1 | LATERAL 两种 JOIN 放进一个会话；LEFT 的 NULL 扩展反例与 CROSS/INNER 一起验收 | 所有者 |
| 合并 S08 与 S09 | 1 | 闭合 EXISTS 与 IN 同片；S09 的工作进入 S08→S10 关键路径，**会推迟 capture 片开工** | 所有者 |
| 把表函数（S15）移到 Phase74 | 1 | VALUES 的零来源接缝保留；本期没有表函数与 effects 放开 | 所有者（改变能力宽度） |
| 拆期：闭合组合与参数为 Phase70，相关/LATERAL/表函数另立后续期 | ≥5 | 改变本期终态；需新插入期，Phase71 及以后编号不变 | 所有者（改变已定范围） |
| 把容量再调高 | 无 | 改变容量；不自动增额 | 所有者 |
| 发行推迟到审计之后另行派发 | 0 | 不腾出位置（发行仍需一片）；只改变时机 | 所有者 |

不是取舍：删去 S01、S02、S18 或 S20；把未完成的特性塞进 S16/S17；用"全部拒绝"代替必需正例；为了片数合并不可审阅的大包。

## 检查点与解冻

- **接缝检查点**：S03 的块身份与按块来源集合、S04 的参数与第三条状态轴、S08 的"表达式到块"接缝包，各自合入时核对漂移；不要求它们全部完成才开始无关下游。
- **中点**：约 10 片已接受时，或 capture 片（S10）进入 Gate 1 时，以先到者为准，重跑 S/H/L/K 并做一次 Q，查看 CI health 与获取整合预留。中点**不阻塞**任何就绪片；只有共享假设被推翻时才冻结受影响的接口与包。
- **解冻条件**：公开选择被反例推翻；前置或接口漂移（含期中依赖更新合入）；无法隔离的写冲突；片尺寸或容量超出；证据输入改变；目标能力缺失；出现新的信任、支持或资源边界。
  只停受影响的包；保留已接受成果、失败记录与预算；未开工的旧展开作废并重新展开；不自动重启整个阶段。

## 验证

- 每个封存候选或批次在集成主机上做一次权威验证（Python 3.13.13，`--pytest-workers 8`，OOM guard），规则见[开发文档](../../development.md#validation-runner-acceptance)；其他 runner 的运行不计入也不替代 Gate 2。多 worker 合入的批次在权威运行前先做一次非权威全量预检（每批最多 1 次，D70.10）；Teach 只用于非权威预检。
- 改 grammar 时运行生成物可复现检查；改 SQL 输出时人工审阅 golden；`src/**` 变化时按批次运行包检查；改执行、模板、compiled 加载或 Arrow owner 时，在 Gate 2 封存前用确切候选 wheel 跑原生执行族。
- 新增或改名的入口、CI 消费者或差分文件，由集成者在同一提交更新 `.github/workflows/ci.yml` 或 `ci/workloads.toml`；新增发射变体的片在 Gate 2 封存前对候选树本机跑完整 PG/MySQL 目标清单。
- 每个 Gate 2 记录带独立收集计数和预期节点增量；聚焦集合包含被改共享模块的直接语义消费者；自然 CI 失败时保留失败头，以子提交修复，不重跑。

## 延期 owner

窄去相关与任何改写 → Phase88（逻辑优化器）/ Phase93（形式化改写认证）；NestedRelation/Collect/Unnest → Phase71；更广 equality/nullability/时间关系、Float 行等价、Timestamp 排序、
Decimal/Date/Timestamp/UUID 参数类型 → Phase72；跨层聚合代数 → Phase73；通用函数/插件 SPI、更多表函数 → Phase74；编辑器/LSP/语法版本与"项目有语义错误时只编译所选 owner"的政策 → Phase75（VS Code 扩展跟进归扩展 owner）；
PG/MySQL 深度适配（含 MySQL 受限形态的等价包装、`JSON_TABLE`、带 capture 的相关 IN 加 LIMIT）→ Phase76/77；高强度真实库、差分与性能保证 → Phase81；公开冻结 → Phase82；
优化器 memo 与改写搜索 → Phase88；持久增量缓存 → Phase91；递归 → Phase92；表函数准入以外的 effects 权威（标量函数 effects 目录 → Phase74；供改写消费的 effects → Phase88；前提是本期 S15 的最小 effects 证据，最晚在对应 Phase 的开局闸门）。
