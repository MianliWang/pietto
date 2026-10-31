# Phase71 route — 24 rows

Phase71 负责嵌套关系与有界嵌套结果（[路线图](../../roadmap.md#future-roadmap-v6) Future Roadmap v6 中 Phase 71 一行：NestedRelation、Collect、Unnest、flatten、outer/inner grain、nested Arrow），只在 EXPLICIT_MODULES 项目与 PostgreSQL 上提供。
本路线已由只含文档的路线发布提交 `6e9d7be6` 发布，其自然 exact-head CI `40250919248` attempt 1 的 19 个 job 全部成功：路线锁定，Phase71 开始。
批次 B1（S01、S02、S03）已发布：S01 `be385507`、S02 `fc5e685c`、S03 `8e0a77d8` 一起 FF push，批次头的自然 exact-head CI `40770576938` 全部 19 个 job 成功；[S01](slice-01.md) 与 [S02](slice-02.md) 记录绑定下一版合成候选 `9511f13563d0`。之后的批次照此规则：只有 FF push 且批次头自然 CI 全部成功才 `COMPLETED / PUBLISHED`，此前都是 candidate。
`0.1.6` 已从发行提交 `bdb3f567` 发行（tag `v0.1.6`），只含 Phase71 的 B1。批次 B2（S04、S05、S06、S07）建立在该发行提交之上，不属于 `0.1.6`，各片记录见下表的链接；B2 已发布：S04 `0dc5d5c1`、S05 `0da7e40a`、S06 `fb3bc264`、S07 `ee19ee01` 与 `0.1.6` 审计的项目模式小修 `81f0d3b5` 一起 FF push，批次头 `81f0d3b5` 的自然 exact-head CI `41128410841` 全部 19 个 job 成功。当前批次 B3（S08、S09、S10、S11）建立在 main 的 `81f0d3b5` 之上，同样不属于 `0.1.6`，按同一规则发布，此前都是 candidate。
下表是覆盖与依赖基准；每个 Slice 在自己的 Gate 0/1 展开时绑定精确输入、写集、命令、验收与成本。三层验收 A01–A12、语义契约与支持域见 [brief](brief.md)，外部参考见[外部参考记录](planning-notes.md)，所有者决定见[决定记录](../../decisions.md)的 D71.01–D71.12。

## 授权与依赖顺序

所有者授权（D71.09）：
- **S02 的 PostgreSQL carrier 实验现在就可以在 Teach 上运行，先于 S01**：只读 SQL、一次性 PostgreSQL 18.6、确切的 `psycopg[binary]==3.3.5` 与 `pyarrow==26.0.0`，在仓库之外运行、自己清理，不写仓库、不提交，结果只作证据；计入本期 Teach 账。它不依赖下一版基线，可以和下一版整合并行。S02 的整片验收仍依赖 S01：S01 在绑定的基线上核对 pin 与读者未变后，才把实验结论接为 S02 的验收输入。
- **S01 在下一版（`0.1.6`）各项合成为一个候选之后开始**，绑定该候选，不绑定 main；该候选的身份在 S01 的 Gate 0 记录。
- 路线发布后 S01–S24 按依赖并行实施：一个主集成者，至多 3 个隔离开发 worker（2026-10-28 的 D71.09 修订先提高到至多 6 个，随后允许按需至多 12 个；实际数按执行器能力与资源核对，不是给数据库或产品 runtime 授权同样数量的并发任务）；每片一个普通提交，就绪片可按批次规则合成一批，以批次最终树的一次权威验证、一次 FF push 与自然 exact-head CI 发布；自然 CI 失败的头保留，以子提交修复，不重跑。
- S03 之前单独派发一次 runner acceptance（D71.10），不是编号 Slice；设计稿的 Q1（这次改动本身怎样封存）与 Q2（同一 Teach 账户里调度器的剩余信任风险）到派发时由所有者回答。落地并通过自然 CI 之前，每次权威验证都只在集成主机运行。
- 版本号、tag、GitHub release 与 PyPI 上传不在本授权内：S23 准备发行决策材料，Phase71 完成版 `0.1.7` 的发行另行授权（D71.09）。所有者 2026-10-30 把 Phase71 的完成版从 `0.1.6` 改为 `0.1.7`：`0.1.6` 只含 Phase71 已发布的 B1（S01–S03），之后的批次在 `0.1.6` 的发行提交进入 main 之后再推送（见[决定记录](../../decisions.md)）。
- 每片开工前重新绑定基线；遇到 BLOCKER、拆片，或新的公开、信任、预算决定即停。

检查点只约束合入顺序，不约束开始开发；草稿、早期 worktree、候选或非权威运行都不授权合入、验证、发布或开始另一个 Slice。

## 排序策略

| 策略 | 利 | 弊 |
| --- | --- | --- |
| 纯风险优先（先做格式与内存） | 尽早发现 carrier 与资源障碍 | 长期没有用户可见成果 |
| 纯价值优先（先写漂亮的嵌套示例） | 最快有演示 | 把 compiled、IPC、资源与所有权成本拖到最后 |
| **先验证两个风险，再打通最小纵向，随后加厚组合与生命周期（选定）** | S02 消除 carrier 未知，S03–S11 按真实 producer 接通，S12 交付公开最小纵向；S13–S20 扩到承诺的完整域，S21–S24 做完整消费者与交付闭合 | 到中点要串行经过语义、计划、结果三层；共享写面需要单一接线 owner |

## 路线发布与冻结前工作（不编号）

- 路线发布（`6e9d7be6`）只含文档：本路线、[brief](brief.md) 与[外部参考记录](planning-notes.md)、[决定记录](../../decisions.md)的 Phase71 节、`docs/status.md` 与 `docs/roadmap.md` 中的生命周期文字（Phase70 的闭合状态、Phase71 的路线候选、表格后的延期 owner 与 `pietto fmt` 步骤）。不编号，沿用 Phase69/70 路线锁定的先例。Future Roadmap v6 表格被生命周期读者逐字锁定，不改表格行。
- S02 实验：见上节，经所有者授权先于 S01 运行；结论最晚在 S02 结束时冻结 carrier 编码。
- 学习者探测：S03 冻结写法之前做一次小型探测（只读，不用 Teach），对象是只会一点 SQL 的 Python 用户，题目覆盖 `collect last_orders`、`let o = unnest(...)` 加三种 JOIN、空列表与 `None` 的区别；探测推翻 D71.01 或 D71.02 的写法时回到所有者。
- runner acceptance 派发：见上节。

## 路线

“依赖”是该 Slice **完整验收**所需的输入，不要求所有私有开发都等这些 Slice 结束（并行方式见下文）。每片只列目标，不预写会过时的文件修改步骤。

| Slice | 目标 | 覆盖验收 | 完整验收依赖 | 类型 |
| --- | --- | --- | --- | --- |
| [S01](slice-01.md) | 绑定实际基线（下一版合成后的候选）、活动 writer、worktree 与授权；消化最新决定（含下一版对诊断码与条数的修正、D-11/D-12 的恢复结果与项目模式 FROM 别名缺陷的修复）；在该基线上确认新诊断码段（开局时 `PIE-S28xx` 未被使用）；建立独立的嵌套反例与实际消费者闭包（遍历、序列化、验证、安装、IPC 读者） | A01, A11, A12 | — | 准备 |
| [S02](slice-02.md) | 实测 PostgreSQL carrier、精度、实际内存与大小边界及保存可行性，锁定可证明的准入域（D71.07 的起点假设逐条证实或替换），输出“前提—证据来源—核实时点—适用范围/有效期”表；只有常量输入可行时回到所有者做范围决定 | A06, A08, A09, A10 | S01 | 实验（实验部分已授权先于 S01） |
| S03 | 最小现代源语法：`name = collect let_name`（`collect` 为上下文词；预计要改 grammar，并按规定重新生成 parser、跑复现检查）与 `let o = unnest(binding.field)` 作 JOIN 输入（只改语义准入）；同名用户 `def` 的区分规则；嵌套类型与 occurrence/nullability 契约；未知 variant 先失败关闭；单文件、LEGACY_FLAT、PACKAGE_ROOT 的确定诊断（说明怎样建 `schema_version = 2` 项目）；D71.01/D71.02 批准的公开诊断变化与逐字消息；`explain` 嵌套类型显示为 UX 候选 | A01 | S01 | 必做 |
| [S04](slice-04.md) | Collect 对已完成关系的绑定：closed/captured、显式 capture 与参数、空集与 bag、限定准入（一次使用、Top-K、未分组 SELECT）；被 collect 读的 let 未写 `order by` 的确定诊断（D71.03） | A01, A02, A03 | S03 | 必做 |
| [S05](slice-05.md) | CROSS/INNER/LEFT Unnest 的绑定、presence、输出字段/nullability/grain 与拒绝（JOIN 必须写种类，参数必须是可见 binding 的嵌套字段） | A01, A04 | S03, S04 | 必做 |
| [S06](slice-06.md) | IR/ProjectSQLPlan 中的 Collect/Unnest 表达、source closure、需求与独立 correspondence | A02, A03, A04, A06 | S04, S05 | 必做 |
| [S07](slice-07.md) | 递归 ResultContract、可移植闭合 schema、层级意义与完整 digest 规则 | A07, A08 | S02, S06 | 必做 |
| [S08](slice-08.md) | PostgreSQL 的 Collect source emission：closed/captured、空集、顺序契约与 Top-K、并列子表的独立运输与真实 artifact | A02, A03, A05, A06 | S02, S06, S07 | 必做 |
| [S09](slice-09.md) | Collect 的 compiled build/verify/lowering 与 source-free 契约；为 Unnest 保留最小闭合表示，未接通时确定拒绝 | A07, A11 | S06, S07, S08 | 必做 |
| S10 | 真实 emission 的 producer/Arrow binding、owned construction、递归验证与 children/bytes 计量 | A08, A09 | S07, S08 | 必做 |
| S11 | 嵌套 copy/borrow/lease、C data/stream 相关通路、非零 offset、零行与 close 生命周期 | A08, A09 | S10 | 必做 |
| S12 | **中点**：Int/Bool/有限 Text 的公开最小真实纵向；曝光前完成准入、未闭合消费者的预拒绝与基础失败/cleanup；接收 S08 的 AC-F7（`L_relation_collect` 目标变体、收据 v3 的 `array` cell、`docs/development.md` 的 denominator 段与 D71.11 的 PostgreSQL 运行；D71.10 scope 一次） | A02, A06, A07, A08, A09 | S08, S09, S10, S11 | 必做 / 中点 |
| S13 | Unnest 的真实 source emission → compiled → 公开 native/bundle；最小纵向只交付最终平面输出，含 presence 与早期拒绝 | A04, A06, A07, A09 | S05, S06, S08, S09 | 必做 |
| S14 | Float/Decimal 嵌套 leaf 的无损 carrier、bit/scale、SQL 内 Unnest 后的 scalar 语义与独立原值证明 | A04, A06, A08, A09 | S12, S13 | 必做 |
| S15 | Date/Timestamp/UUID 的有限域、意义、SQL 内 Unnest 后的 scalar 语义与原值证明 | A04, A06, A08, A09 | S12, S13 | 必做 |
| S16 | 多个并列子表、命名/分组阶段、参数/排序/过滤及 Collect–Unnest 组合，含展开一项后仍保留另一嵌套字段、普通 JOIN 透传与跨模块传递 | A03, A04, A05, A08 | S12, S13 | 必做 |
| S17 | 完整嵌套合同的 IPC framing、截断/错 schema、rebatch/offset 与兼容拒绝 | A07, A08, A10 | S07, S09, S10, S11 | 必做 |
| S18 | 普通保存、完整顶层 occurrence/chunk/checkpoint 与既有 publication 资格；优先复用 v7 工作区 | A08, A10 | S12, S14, S15, S17 | 必做 |
| S19 | 新进程断源 R1 与独立 `verified_export`，含 trust/schema、重分批与只读导出无控制写入 | A08, A10 | S18 | 必做 |
| S20 | 全类型与组合的资源、错误、关闭/取消和拒绝复核，覆盖 live/saved、R1/export 及未支持的路线/R2/sink/relay | A09, A10, A11 | S12, S13, S14, S15, S16, S18, S19 | 必做 |
| S21 | 独立差分/metamorphic/损坏语料、旧平面全回归与所有必做公开消费者的串联核对 | A01–A11 | S14, S15, S16, S18, S19, S20 | 必做 |
| S22 | 阶段末获取成本与直接读者复核、覆盖保持与适用 CI health（十个最慢节点的有界 profile 复核）；只修复已确认且属于本期的缺陷 | A11, A12 | S21 | 必做 |
| S23 | 干净安装、候选 package/示例/help/支持矩阵与准确版本策略；准备 `0.1.7` 发行决策材料（不发行） | A06, A07, A08, A10, A11, A12 | S22 | 必做 |
| S24 | 仅审计：三层验收对账、最终审计、实际计划偏差、延期 owner 的接收与最晚点、Phase72 可消费的交接 | A01–A12 | S23 | 审计 / 收尾 |

规划结构：24 个节点、57 条列出的硬依赖边（其中 25 条可由传递推出，按计划 v2 原样保留）、无环、编号即拓扑序；最长路径 18 个节点（S01→S03→S04→S05→S06→S07→S08→S10→S11→S12→S14→S18→S19→S20→S21→S22→S23→S24）；ASAP 最大层宽 3（S14、S15、S16）。容量 25、余量 1，余量不设伪编号、不建账、不自动开始。

- S08–S11 按“PG source emission → Collect compiled → Arrow binding/construction → ownership”排列：S07 的 ResultContract 可以消费真实 checked plan，所以先于 emission；compiled 与 Arrow 的完整验收不能先于 emission。
- Unnest 的 source emission 与 compiled 接通都归 S13，避免 S09↔S13 循环或接受假 artifact。S09 声明了 Unnest records 也不报告该操作可执行，未接通的加载/准备路径确定拒绝，S13 以真实 producer 闭合后才开放。
- S12 只交付 Int/Bool/有限 Text；S14/S15 加厚其余 leaf；不能把局部层完成写成八类 leaf 全部公开可用。S13 的最小公开验收只交付最终平面结果，因此不等 S12；展开 orders 后仍选择 payments 等嵌套字段的组合须等 S16 依赖的 S12/S13 全部就绪。
- 保存与断源读取分成 S18/S19：写入/publication 与新进程的 trust/读取是两个可独立验收的边界。
- S20 是完整组合复核，不是首次补上早期拒绝、资源与 cleanup 边界的位置；flat-output Unnest 也不能绕过新 operation 的路线/R2 准入。

## 分批发布

按所有者要求分批并行推进；以下分组不改变 24 个 Slice 的目标、完整验收依赖或容量。每片仍是一笔普通提交，每批只在最终树上做一次权威验证、一次 FF push 和一次自然 exact-head CI。共享文件在同一时刻只有一个 writer；下一批可以提前准备，冻结与合入仍须满足本路线的依赖和检查点。

| 批次 | Slice（提交顺序） | 批次边界 |
| --- | --- | --- |
| B1 | S01、S02、S03 | 绑定前置合成候选，接入 carrier 实验证据，再封存语法与嵌套类型；runner acceptance 在 S03 前完成 |
| B2 | S04、S05、S06、S07 | Collect/Unnest 绑定、计划与递归 ResultContract；共享语义文件由集成者顺序接入 |
| B3 | S08、S09、S10、S11 | 真实 PostgreSQL emission、compiled、Arrow 与 ownership，未闭合的公开消费者继续拒绝 |
| B4 | S12、S13、S17 | 最小公开纵向、最终平面输出的 Unnest 与 IPC；本批自然 CI 通过后做中点复查 |
| B5 | S14、S15、S16 | 中点复查通过后，封存其余 leaf 与组合能力 |
| B6 | S18、S19 | 普通保存、断源 R1 与 verified_export |
| B7 | S20、S21 | 资源、取消、拒绝与完整回归闭合 |
| B8 | S22、S23 | 获取成本、安装与发行决策材料；发行仍需单独授权 |
| B9 | S24 | B8 自然 CI 通过后的独立审计；不与 S23 同批 |

路线文档提交不占编号批次。前置的 `0.1.6` 修复项在 main 之外合成，S01 绑定经过检查的确切候选；本表不新增前置候选的提交或发布授权。所有者 2026-10-30 决定：`0.1.6` 是下一版各项、post70 修正、MySQL 单文件对齐、依赖维护与项目模式修正，Phase71 只含已发布的 B1；B2 及以后的批次进入 Phase71 的完成版 `0.1.7`。

S01 消费已确认的项目兼容决定：手写 ON 可使用普通项目推导出的唯一键，但容器内或 element-factor 的键不得升级为全局唯一键；项目 FROM 别名修复保留原输入名限定字段的既有合法用法。`explain` 的嵌套类型显示仍只是 S03 的 UX 候选，未获批准前不改变公开 JSON。封存前本机 Docker 的授权仅覆盖 D71.11 的 PostgreSQL，不能据此启动 MySQL 原生检查。

## 并行方式与共享写面

| 私有工作包方向 | 可以提前做的内容 | 集成前必须具备 |
| --- | --- | --- |
| 语义与语言 | 独立 fixture、scope/capture/Unnest 规则、parser 候选 | 主集成者公布的最小 schema/identity 契约 |
| PG lowering 与 carrier | 官方机制实验、carrier 精度反例、SQL 节点私有实现 | 已冻结的 Collect/Unnest 计划事实与输出需求 |
| 结果与消费者 | Arrow children/offset/ownership、IPC 损坏 oracle、保存读者评估 | 真实 ResultContract、emission/producer；正式正例必须来自对应上游 owner |
| 独立验证 | typed literal oracle、旧回归选择、安装/文档审阅 | 对应功能的完整集成候选 |

S02 与 S03 的私有工作可在 S01 后并行，但不先冻结未证实的 durable carrier。S05 的语法/拒绝设计可与 S04 重叠，其真实正例验收仍需真实 producer。S06 的 Collect 工作包在 S04 的真实接口稳定后即可推进；S05 只阻塞 S06 的 Unnest 工作包与整片验收。S07 的结构研究可早于 S06 完成。S08 完成后，S09 与 S10 可按隔离写集并行验收。S11/S17 可重叠私有准备，S17 的完整验收仍等 S11。S14/S15/S16 在 S12/S13 前提具备后可并行。S18、S19、S20 可提前分工准备，整片验收依赖不变。

grammar 与生成的 parser、公共 AST/model 枚举、统一遍历、compiled schema、result shape 定义、公开 API 接线、lockfile/packaging 是集中写面：同一时间只有指定 owner 修改同一共享文件；worker 提供不重叠的模块、fixture 或精确 patch 交主集成者接线；“不同函数”不等于同一共享文件没有集成冲突；真实依赖、验收组合、文件冲突与数据库/端口/profile 资源互斥分别记录；worker 的通过结果不能相加成为合成后的 PASS；不把开发并行变成产品内的多 compiler worker 或通用调度内核。

## 中点退出条件（S12）

S12 完成后的复核必须看到：
- 一个真实的、由当前 schema/语义 owner 产生的嵌套程序；
- live 路径实际经过 compiled graph；
- PostgreSQL 原生结果通过严格 decoder，抵达公开 Arrow 消费者；
- 空集、重复、nullable 字段与至少一组大小拒绝真实发生；
- 新功能曝光前，按 compiled operation 与结果形态联合检查运行准入，基础失败/取消/cleanup 已成立；
- 尚未闭合的嵌套 IPC、保存、断源读取与其他公开入口明确拒绝，只有 S17/S18/S19 的相应验收完成才逐项开放，原平面入口继续可用；
- 现有平面回归未破坏；
- S02 的内存与 carrier 假设仍成立。

只返回 JSON、只构建一个手写 Arrow ListArray、只让 checker 接受，都不算中点纵向完成。中点重跑 S/H/L/K/Q，查看适用的 CI health 与获取整合预留；私有准备可以继续，但 B5 及后续批次必须等 B4 自然 CI 通过且中点复查通过后才能封存或发布；共享假设被推翻时，另行冻结受影响的接口与包并修正计划。

## 修复、资源与验证预算

- **修复上限（D71.10）**：全期累计 causal 200 / focused 180 / diagnostic 250 / scope 12，超出任一项即停，由所有者决定是否加额度；不继承 Phase70 的余额，历史 UNKNOWN 照实保留。计法沿用 Phase70：causal 是评审、验证或 CI 发现问题后的一次根因修复（同一根因多处只算 1；权威验证失败后修好重跑计 1；自然 CI 失败后的修复子提交每个计 1，不重跑 CI）；focused 是修复后重新启动一次相关测试（中途中断也计 1）；diagnostic 是为查原因而跑的测试，或产品代码不变、只因数据库或容器抖动的重跑；scope 是一片在进行中改变范围。worker 首轮实施时的常规测试不计。权威全量验证与本机数据库检查按每个封存候选或批次一次计；多 worker 合入的批次在权威运行前先做一次非权威全量预检（每批最多 1 次，在 Teach 上）。
- **Teach（D71.10）**：本期单独记账 500 jobs / 2,000 core-h，同时最多 16 个作业；温和流量，不重交同一 request id；结果只是非权威开发证据，不计入也不替代 Gate 2，直到 runner acceptance 落地并有合格的环境记录。
- **本机 Docker（D71.11）**：封存前的 PostgreSQL 原生检查（新增发射变体的片跑完整 PG 目标清单；改动执行、模板、compiled 加载或 Arrow 的片用确切候选 wheel 跑原生执行族）在本机 Docker 运行：固定镜像、断网、自有清理，同一时间只跑一个，每次不超过 2 小时。MySQL 的预拒绝与旧平面行为仍由适用的现有测试、golden 和 CI 覆盖；新增 MySQL 容器检查须另行授权。
- **验证**：每个封存候选或批次在合格 runner 上做一次权威验证（现在只有集成主机：Python 3.13.13，`--pytest-workers 8`，OOM guard，规则见[开发文档](../../development.md#validation-runner-acceptance)）。改 grammar 时运行生成物可复现检查；改 SQL 输出时人工审阅 golden；`src/**` 变化时按批次运行包检查。新增或改名的入口、CI 消费者或差分文件，由集成者在同一提交更新 `.github/workflows/ci.yml` 或 `ci/workloads.toml`。每个 Gate 2 记录带独立收集计数与预期节点增量；聚焦集合包含被改共享模块的直接语义消费者。封存前做一次只读的对抗审查。

## 超过 25 片时的停止规则

预列拆分线：S13（Unnest 的 emission 一片、compiled 与公开纵向一片）是唯一余量的首选用途；其他片展开时若明显无法在一个可审阅会话闭合，同样先报告。余量 1：一处拆分到 25，第二处超过容量。超过时停下，出一份只含下表取舍的小决策单交所有者；容量不自动增加；一个备用位置不同时承接多处独立拆分；不把一个巨大 Slice 改名为“小补丁”规避容量。

| 取舍 | 腾出 | 影响与风险 | 谁来定 |
| --- | --- | --- | --- |
| 先收窄尚未批准的能力（只读展示、额外示例等“时间够才做”项） | 0–1 | 已选主流程不变 | 主集成者报告，所有者确认 |
| 把 S17–S19（IPC、保存、R1、`verified_export`）移到 `0.1.8` | 3 | `0.1.7` 只交付嵌套 `execute()`，保存类入口一律在连接前拒绝；S20、S21 中与保存有关的部分和 S23 的支持矩阵相应缩小；以后开放是纯放宽 | 所有者（改变 D71.05 已采纳的终态） |
| 收窄到静态有界 VALUES 或已有受约束来源（S02 证明不了来源约束时） | 0 | 丢失真实来源上的用户场景；不能以玩具正例宣告终态完成 | 所有者（范围决定） |
| 删减已采纳的某个必做 leaf 或 Unnest 语义 | 1 | 改变终态与支持矩阵 | 所有者（范围决定） |
| 把容量再调高 | 无 | 改变容量；不自动增额 | 所有者 |

不是取舍：删去 S01、S02、S22 或 S24；把未完成的特性塞进 S20/S21；用“全部拒绝”代替必需正例；为了片数合并不可审阅的大包。

## 检查点与解冻

- **接缝检查点**：S03 的写法与嵌套类型契约、S06 的计划事实、S07 的 ResultContract、S08 的真实 emission，各自合入时核对漂移；不要求全部完成才开始无关下游。
- **解冻条件**：S02 无法证明选定 carrier 的精度或必要运输资源边界；公开 API 无法在现有 compiled/Arrow/lifecycle owner 中组合、需要新的 durable 协议；必做范围预计超 25 片，或某片明显无法在一个可审阅会话完成；需要超过一层嵌套、宽 equality、隐式 group capture 或 MySQL/ADBC/R2/sink 扩范围才能达成已承诺终态；下一版基线、main 或所有者的新决定改变了已绑定的语法/接口/授权；真实 source closure、安全/身份或原值正例被推翻；并行写集产生无法在现有 owner 内隔离的冲突。
  触发后只重跑受影响的 S/H/L/K/Q；保留已接受成果、累计失败与预算；未开工的旧展开作废并重新展开；不 reset 账本，不自动重启整个阶段。

## 延期 owner

| 内容 | owner / 最晚决定点 | 回收前提 |
| --- | --- | --- |
| 多层 collection | 后续嵌套扩展候选；S24 决定具体挂靠，不占用既有他期编号 | 一层闭环，深度/大小/身份/codec 成本有证据；另行预算 |
| UNION ALL、普通 RIGHT/FULL 携带嵌套、嵌套窗口值/读取 | 对应核心语义/SQL plan owner 的后续候选；S24 保留 unsupported 或指定接收 owner | 相应类型/来源/lowering 前提成立，单独范围与预算 |
| 一个 capture let 读另一个 capture let（嵌套相关） | S24 按同一规则指定接收 owner 与最晚点 | 本期一层的事实与拒绝边界 |
| MySQL 嵌套输出 / `JSON_TABLE` | Phase77，该 Phase 开局 | 精确版本能力、空/NULL/顺序与 carrier 保真研究 |
| PG ADBC 嵌套路线 | Phase76 的 adapter/target 扩展候选，该 Phase 开局确认 | driver 实际 carrier、batch ownership、资源域与值保真 |
| 数据库原生 array 与 JSON 列 | Phase76（类型部分配合 Phase72），该 Phase 开局 | 本期 carrier 编码与解码证据 |
| 嵌套值的 equality/hash/grouping/DISTINCT | Phase72，类型/equality 设计前 | bag/sequence equality、NULL、Float 含义有独立合同 |
| 隐式 group capture、自动安全再聚合；对列表做聚合（`len`、`sum(o.total for o in c.recent_orders)`、对列表用 `any(...)`） | Phase73，该 Phase 开局 | 聚合阶段/grain 与 fanout 证明先成立 |
| 通用函数/插件 SPI；用户可写的数组表函数 | Phase74 | 明确的插件 contract/effects/版本/trust |
| 编辑器与扩展深度支持 | 扩展 owner / Phase75；独立派发 | 核心接口已定，原扩展任务状态明确 |
| `pietto fmt` | Phase71 之后、Phase72 之前的独立步骤（D71.08），其开工仍需自己的派发 | 本期写法定稿 |
| pandas/Polars 嵌套适配 | Phase80 | 本期嵌套 Arrow |
| 嵌套 fuzz 与高强度差分 | Phase81 | 本期语料与 oracle |
| 嵌套公开格式冻结 | Phase82 | 本期版本标记 |
| 自动 flatten、去相关、CSE、求值次数 | Phase88/93 | 明确可证明的等价前提与 effects |
| 子行级恢复、R2、嵌套 sink 效果 | 后续执行/恢复专门契约；S24 给出接收 owner 与最晚点 | 稳定坐标、effect identity 与完整 checkpoint/ACK 模型 |
| D-11/D-12 整体恢复 | 现行路线图中 Pietto lead 的后续项 | 不为本期偷偷扩大；挡住必做时只定点提出前置 |
| 公开发行（`0.1.7`） | 本期候选之外的明确发行续行 | 所有者对确切版本、构建与渠道的授权；不沿用旧发布权限 |

未分配编号的延期必须在 S24 明确接收 owner；当前不虚构一个已经获批的未来 Phase。
