# Phase71：嵌套关系（Collect / Unnest）与有界嵌套结果

所属 Stage：Phase82 公开冻结之前，向稳定 1.0 迈进的可组合查询与类型化结果（仓库没有数字 Stage，这里用描述性目标）。本期服务这一目标，Stage 不收尾；S24 只记录本期贡献与仍未满足的已知条件。

Phase70 `COMPLETED / PUBLISHED`：25 个实际 Slice，S20 审计普通提交 `51cac2ab32adf26040dff57aff66f524f1a1fb0d` 的自然 CI38844191993/push/main/attempt1 接受全部 required consumers。
Phase70 之后的稳定批构成 `0.1.4` 公开 alpha（`4e043a0b`），现代源语法、单文件 JOIN MVP 与 fix batch 7 构成 `0.1.5` 公开 alpha（`6d0f6c6c`，自然 CI `40156617674`），两版都已在 GitHub pre-release 与 PyPI 发布并核验字节。
所有者计划 v2 的规划证据固定在 `6d0f6c6c`（tree `e0c6c5b4e5f8bbf75e33ba67a537de2887ec4618`）；本路线发布文档的基线是 main `88c11d0839d9f12fee53bd46d777b55b11356a42`（tree `9de164058b5d9cd85c821e443117743fcf468ba2`，`src/` 与 `v0.1.5` 相同，自然 CI40180988546/push/main/attempt1）。
S01 不绑定 main，而是绑定下一版（`0.1.6`）各项已合成的候选（D71.09）：下一版各项与本期改同一批热文件（fan-out 证明、发射、let 规范化）。
本 brief、[24 片路线](slices.md)与[外部参考记录](planning-notes.md)已由只含文档的路线发布提交 `6e9d7be6` 发布，其自然 exact-head CI `40250919248` attempt 1 的 19 个 job 全部成功：路线锁定，Phase71 开始。所有者决定见[决定记录](../../decisions.md)的 D71.01–D71.12。

当前开工绑定见 [S01](slice-01.md)：下一版合成候选已发布为 `9511f13563d0`，B1 按既定批次实施；以下规划观察保留其原始基线，实际状态由 S01 的逐项接收记录承接。

## R/A/C 与使命

**回看（事实）。**
1. Phase70 原 20 行路线加 S04r/S04w/S05g/S05j 构成 24 个规划位置，S04 拆为 S04a/S04b 后为 25 个实际位置；最终修复核账 causal 123 / focused 108 / diagnostic 156 / scope 6，上限经所有者几次上调到 225 / 180 / 270 / 9。原 20 行不约束已完成的历史。
2. Phase70 交付了关系 let、命名参数、VALUES、关系读取、显式 capture/LATERAL、有界 `generate_series` 与计算分组键，是本期的组合基础；它保留 no-rewrite 边界，没有交付去相关，本期不能把它当作可用的优化器。
3. Phase70 之后源码已有现代语法（`None / True / False`、`T | None`、`source name: Shape = ...`、单行 clause 不加冒号、`let name = expression`、JOIN 别名先写 `let buyer = customers` 再 `left join buyer on …`，JOIN 里的 `as` 已退役）、单文件 JOIN 与多批稳定性修正；Arrow pin 是 `pyarrow==26.0.0`。规划与例子一律用现代语法，不搬 0.1.3 的测试数、依赖或例子。
4. 接口单独通过不等于完整公开消费者通过：Phase69/70 的失败头主要来自只在 CI、hosted 或目标库运行的消费者与字面 pin 读者（[工程教训](../../references/engineering-lessons.md)）。
5. 开局实测（0.1.5 编译器）：项目模式里 FROM 别名读字段报 `PIE-S2102`，改写法会让 `check --project` 打出 traceback；项目里 `cross join o on True` 多报两条 `PIE-S2334`。开局把这些归为 `0.1.6` 修复项，但只有 FROM 别名的修复有所有者决定；在绑定的 `9511f135` 上 FROM 别名的两项已修复，`cross join o on True` 的诊断与 0.1.5 相同（见 [S01](slice-01.md) 的开放项 O2、O3）。它们不是本期决定；本期例子读另一个查询的字段时用全名（如 `customers_with_orders.recent_orders`）。

**教训与本期调整。**

| 教训 | 本期调整 |
|---|---|
| 语法先铺开、关键运输问题后发现，会增加切片与返工 | S02 先做精确 carrier 与资源实验（所有者授权先于 S01 在 Teach 运行，D71.09）；S12 前形成真实公开执行纵向，不等到尾部才发现 bundle/Arrow 不通 |
| 共享 owner 的直接消费者、安装读者和独立 oracle 容易遗漏 | 新 variant 先列遍历、序列化、验证、安装、IPC 的消费者闭包；未知 variant 默认失败关闭 |
| 同一版本字样、SDK 支持、缓存或 worker 小结不能替代证据 | 固定源码与安装来源；新类型逐个证明值保真；主集成者验证合成后的 tree，独立检查结果与覆盖 |

**现状能力（只列本期触及的部分；“可靠可用”限于已有合同与证据域，本期开局没有重跑产品测试）。**

| 档 | 能力 | 本期处理 |
|---|---|---|
| 可靠可用 | 显式模块项目、名字/类型/来源、关系 let、已准入的 capture/LATERAL、参数与 SQL 发射 | 作为语义和编译回归，不重写 resolver |
| 可靠可用 | 显式 Python 执行、compiled bundle、平面 ResultContract、Arrow、保存/R1/R2 流程 | 旧平面输入行为不变；新嵌套形态逐层准入 |
| 能用但有明确限制 | 单文件 PostgreSQL JOIN；单文件 explain/MySQL JOIN 与其他项目模式仍拒绝；项目模式 FROM 别名读字段的缺陷（见回看 5） | 不从“单文件 JOIN 已有”推出“所有嵌套模式都该开放” |
| 能用但有明确限制 | `postgres_rows` 首次读取可能把整个 native result 放进客户端；`max_rows`/`max_bytes` 限制交付，不是读取前的内存上界 | 嵌套准入单独分析父行、子行数与 carrier 字节（S02） |
| 能用但有明确限制 | D-11/D-12 的保守拒绝（sound outer-JOIN aggregate、NULL 算术） | 保留既有承诺与 owner；只在本期必做场景被挡住时局部提出前置 |
| 没有运行证据 | 最新原生平台/路线的所有组合；真正的 Remote WSL GUI | 不标为可靠可用，不借 SDK probe 填 PASS |
| 缺失 | NestedRelation、Collect/Unnest 的语义与真实嵌套输出 | 本期新增；不能称为“只差启用” |
| 只是代码存在 | 命名 `SHAPE` 类型分类；Arrow SDK 自带 List/Struct | 放开现有 `SHAPE` guard 不等于完成新功能 |

**已核对的硬障碍（计划 v2 在 `6d0f6c6c` 上定点核对，lead 逐条复核成立）。**

| 实际 owner | 现状与影响 |
|---|---|
| `src/pietto/_project/project_result_contract.py` | `ResultShape` 只有 scalar leaf，构造拒绝 SHAPE/UNKNOWN；需要真正的嵌套 shape 与验证法则 |
| `project_result_output.py` / `project_result_binding.py` | 逻辑列与 producer carrier 按标量匹配；要区分嵌套逻辑类型与 JSON/Text 运输列 |
| `project_compiled_build.py`、result binding、Arrow binding | compiled 构建只接收真实 emission/guarded artifact，Arrow binding 复核真实 emission；完整验收必须在对应 source emission 之后，手写 fixture 不能替代 |
| `project_execution_template.py` | `prepare_live_template` 无条件进入 `build_compiled(...).root`：compiled graph 不是可延期的附加功能 |
| `project_compiled_schema.py` | 闭合 records 与 `VERSIONS = (5, 1, 5, 1)` 不认识嵌套；只调整真实受影响的兼容维度 |
| `project_arrow_result.py` | 只支持八类 scalar；需要递归 shape、children、offset、validity 与费用计算 |
| `project_arrow_interop.py` | `_copy_batch` 明写 flat-only，不递归复制或租借 children；公开结果交付前必须修复 |
| `project_result_ipc.py` | compiled contract digest 只覆盖平面字段；上限 96 MiB，`compression=None`，`allow_64bit=False`；digest 必须纳入完整嵌套结构与意义 |
| job workspace / chunks / replay | 以顶层 occurrence、chunk 与 extent 为基础（`pietto.job-workspace.v7`）；优先复用，不先验升级工作区 |
| refinement 与 reference sink | 没有嵌套 R2 坐标与递归 effect codec，必须单独拒绝 |

**开局 CI health。** 路线发布基线的自然 CI40180988546/push/main/attempt1 的 health 摘要（artifact `ci-health-40180988546-1-summary.json`，694,645 B，
sha256 `fcf852b94c27c254f97e6b512bc2b8b6e044c09b6c280e5564226eccf56d4bf1`，`pietto.ci-workload-health.v1`，policy sha256
`f252532dab16f38675833d36e14f353d7b85b8be92ba9d9e017de8933568a189`，topology 2）判定为 `INSUFFICIENT_EVIDENCE`、current screen `WATCH`，可比样本 0（runner 与 test-set 变化使三个历史样本不可比）。
两个 runtime 各 collected/selected/executed 22,306，passed 22,287，skipped 19；24 个信号为 LONG_INDIVISIBLE_NODE 18 个、FEWER_UNITS_THAN_WORKERS 4 个（结构性）、SHARD_IMBALANCE_REVIEW 1 个（3.12）、SHARD_IMBALANCE_WATCH 1 个（3.13）；成本记录不完整。
所有者计划 v2 读过的 `0.1.5` 发行 CI `40156617674` 的摘要（sha256 `deed8e0da8c31774c3d510253104efb8d623102b5d70092a04dec1e7a25755d1`）为 22,305 / 22,286 / 19，结论同样是 WATCH 与 INSUFFICIENT_EVIDENCE。
这是 runtime 覆盖，不是全产品验收总数，也不授权任何调度、拓扑、worker 上限或资源政策改动。中点与 S22 消费最新的适用 health；S01 在自己的基线上重读。

**路线图约束。** Phase71 拥有 [Future Roadmap v6](../../roadmap.md#future-roadmap-v6) 中 Phase 71 一行（NestedRelation、Collect、Unnest、flatten、outer/inner grain、nested Arrow）。
广义 equality/nullability、Float 行等价与时间/range/ASOF 在 Phase72（嵌套容器必需的最低 nullability 属本期）；聚合代数、state 与安全再聚合在 Phase73（Collect 只收集已完成的关系，不发明隐式父层分组）；通用 function/plugin SPI 在 Phase74（collect/unnest 由编译器显式拥有，不搭插件框架）；LSP、编辑器、syntax editions 与迁移在 Phase75 与扩展 owner；PG/MySQL 深度适配在 Phase76/77；dataframe 适配在 Phase80；自动 flatten、去相关、求值次数与形式化改写认证在 Phase88/93；递归在 Phase92；连续查询在 Phase97。
`pietto fmt` 按所有者 2026-10-17 的决定作为 Phase71 之后、Phase72 之前的一个独立步骤（D71.08），不占本期容量；Phase 75 一行不改。

**使命。** 让 Pietto 查询返回“每个父行带子表”的有类型结果，并明确保留父/子粒度、重复、空集、排序与来源；用户可以显式把一个子表展开回行，不靠手写 JSON 解码，也不会误以为展开天然保留所有父行与统计量。
本期不建设数据库、优化器、通用嵌套框架、多层嵌套或新的执行调度。

**终态（用户视角）。**
1. 在 `schema_version = 2` 项目里定义父查询与一个有界子关系（`let` 加 `capture`，或闭合 let），用 `recent_orders = collect last_orders` 把它放进父行的一个字段；`check`、`explain --project` 与 `emit-sql --project` 给出确定结果。
2. 同一父行可以放两个独立子表（如 orders 与 payments）；加一个子表不改变另一个子表或父行数量。
3. 另一个查询写 `let o = unnest(customers_with_orders.recent_orders)`，再用 `cross join o`、`inner join o on …` 或 `left join o on True`，明确选择只展开实际子行，还是保留没有子行的父行。
4. 经真实公开 Python API（`execute()`，`postgres_rows`）取得 schema 明确的 Arrow 嵌套批次，`to_pylist()` 得到 list of dict（空子表是 `[]`），并正确关闭与释放。
5. 保存完整顶层结果行，在断开源数据库后按既有 trust/acceptance 规则经 R1 重读，或经独立的 `verified_export` 只读导出同一快照，保留嵌套值与 schema。

**预算。** 24 片必做加 1 个未分配位置，容量 25（D71.09）；该位置不编号、不建账、不自动开始，不是多层嵌套、MySQL、ADBC 或 GUI 的预算。
全期累计修复上限 causal 200 / focused 180 / diagnostic 250 / scope 12（D71.10，所有者覆盖了推荐的 185/165/235/9），超出任一项即停；不继承 Phase70 的余额。
Teach 本期单独记账 500 jobs / 2,000 core-h、同时最多 16 个作业（D71.10），只做非权威预检与实验，直到 runner acceptance 落地并另有合格环境记录。封存前的 PostgreSQL 原生检查按 D71.11 在本机 Docker 运行。
不承诺墙钟时间；发行（版本号、tag、GitHub、PyPI）另行授权（D71.09）。

## 已锁定的输入

- Phase70、Phase69、各插段与已发行的 `0.1.0`–`0.1.5` 字节不重开、不替换；Phase72 及以后编号与范围不变。
- 一个规范集成者；隔离 worktree 中的 worker 按依赖并行开发；单一 writer、FF-only、自然 CI、每个封存候选或批次一次权威验证、失败头保留、提交只用 Mianli Wang 身份且不加 AI 署名行。
- 语言规则（`AGENTS.md`）：冒号加空格缩进，不用花括号，不加多余关键字；`collect` 是上下文词，现有同名字段、函数与关系照常解析；一件事一种写法。
- 公开 CLI/JSON 形状、诊断码与顺序、稳定 SQL 与 PostgreSQL emitter 不在未授权时改变；本期已批准的公开诊断变化逐项列在 D71.01 与 D71.02，逐字文本在 S03 的 Gate 1 定稿。
- 新能力只在 EXPLICIT_MODULES（`schema_version = 2`）项目与 PostgreSQL 提供；单文件、LEGACY_FLAT 与 PACKAGE_ROOT 不自动开放（D71.05）。
- 所有者 2026-10-25 的 `0.1.6` 决定：`0.1.6` = 下一版各项 + 外部评审缺口 + Phase71；S01 绑定下一版合成后的候选；发行本身另行授权。

## 所有者决定

所有者以「然后这几项批准都全部按照你的推荐来上限 C200/F180/D250/S12，封存前 PG 原生检查允许本机 Docker」（2026-10-25）采纳 P1–P6 与计划 v2 第 12 节决定 1–3 的推荐，并覆盖修复上限、开出本机 Docker 例外（[决定记录](../../decisions.md) D71.01–D71.11）：
- Collect 写成 `name = collect let_name`，与 `exists r`、`scalar r.c`、`x in r` 同一类“词加关系名”的读法；括号永远表示调用（D71.01）。
- Unnest 先用一行 `let o = unnest(binding.field)` 起名，再 `cross join o`、`inner join o on …` 或 `left join o on True`；参数必须是前面某个可见 binding 的嵌套字段，JOIN 必须写种类（D71.02）。
- 被 `collect` 读的 let 必须写 `order by`，closed let 也一样；排序键并列时顺序与 LIMIT 末位取哪一行都不承诺（D71.03）。
- 嵌套结果的含义按计划 v2 决定 1 的 A（D71.04）；消费者与支持域按决定 2 的 A，不现在切 S17–S19（D71.05）；兼容与存储按决定 3 的 A（D71.06）；单文件与其他模式的确定拒绝诊断（D71.05）。
- 实验先行与资源界限的起点假设由 S02 证实或替换（D71.07）；`pietto fmt` 放在 Phase71 之后、Phase72 之前（D71.08）。
- 24 片加 1 个余量、容量 25；S02 的 Teach 实验先于 S01；S01 绑定下一版候选；按依赖并行实施与批次发布（D71.09）；Teach 额度、修复上限与 S03 前的 runner acceptance 派发（D71.10）；封存前 PostgreSQL 原生检查的本机 Docker 例外（D71.11）。

## 语义契约（D71.04 采纳的计划 v2 第 6 节）

**三层分开。** 关系意义是 `NestedRelation<T>`：某个父行 occurrence 拥有的、带 schema、multiplicity、ordering 与来源的子关系；物化结果是子记录序列；Arrow 表示是有严格字段 schema 的 `List<Struct<...>>` 与层级 validity/offset。`NestedRelation<T>` 是设计概念名，不是源语言 generic 语法；Arrow 字段名、JSON key 与子行下标都不自动成为语义身份。

**Collect。** 收集被读关系完成自身过滤、分组、投影、排序与 LIMIT 之后的结果，保持 bag multiplicity；不隐式给父层分组，不重新解释父层聚合。
- closed let 可以被每个父行读取，不承诺数据库只求值一次；captured let 只消费显式捕获的、当前可见的外层 FROM/JOIN occurrence。
- 一个父行得到一个集合值；值相同的两个父行仍是两个 occurrence。子关系的过滤只改变这个集合；要删父行，须在父层写过滤。
- 子关系已分组时 Collect 读取完成后的行；父查询需先分组时，先形成独立命名关系，再从它的输出行捕获；不从父 group 任选原始行作 capture 代表。
- captured let 的一次使用、作用域与已准入 body 限制照实继承。`collect` 读取是新的明确消费者分类，只把一次 Collect 接入既有的受限 ORDER/LIMIT（Top-K）准入；captured body 仍不能直接 GROUP BY、聚合或用窗口。同一 captured let 被两个 Collect 读取仍拒绝；并列子表用两个各自 capture 的 let。
- 直接 Collect 初期只在未分组 SELECT 的准入位置开放；分组父层用上面的显式阶段组合；其他位置确定拒绝。

**空集、None 与 NULL 字段。** 零行得 `[]`，不是 `None`；`[{v: None}]` 是一条实际子行，不能变成 `[]`；初版集合元素是实际 record，不准入 `None` 元素。既有外连接使整个嵌套字段缺失时得到 `None` 容器，它与 `[]` 不同。不用“所有子字段都是 None”猜子行是否存在。这些是本期容器必需的 nullability 规则，不开放全语言的 nullability 计划。

**粒度与 fanout。** Collect 不合并父行；父层 grain 与 occurrence 不随子行数改变，子关系的 grain 由它自己的完成关系决定，未知就保持未知。两个并列子表必须各自完成再附属于父行，禁止为方便发射先把 2 条 orders 与 3 条 payments JOIN 成 6 行再分别收集。Unnest 改变 grain：输出基于父 occurrence 与真实子 occurrence 的组合，LEFT 占位不是真实子行；新 grain 不自动升格为 unique key 或 FD。

**排序与 LIMIT（D71.03 收紧计划 v2 §6.5）。** 被 `collect` 读的 let 必须写 `order by`，否则确定诊断并给出修法；lowering 必须把顺序契约带到实际收集操作（只靠上游子查询排序不够，PostgreSQL 文档也写明 join 可能打乱它）。排序键不在最终子投影时，semantic/plan 保留编译器拥有的排序依据或内部序位穿过 compiled/bundle，不按名字猜字段，也不把隐藏排序字段塞进公开子 schema；不暗加 tie-breaker。排序键并列不构成全序，tie 内顺序与 LIMIT 末位的取舍不承诺；文档教用户把唯一列放进排序键。authored LIMIT 改变的是被读关系自身的结果；运行时上限不是 authored LIMIT，超限失败、不截断。父行顺序只由外层 `order by` 决定；Unnest 输出没有自动全局顺序。不开放嵌套值的整体 equality、hash、DISTINCT/分组键、数组下标或隐式排序键。

**Unnest。** CROSS Unnest 产生实际子行，INNER Unnest 只保留 ON 为 True 的真实子行，空或缺失集合不产生行；LEFT Unnest 在没有满足 ON 的子行时保留父行一次并补空，包括集合为空、缺失以及非空但全部不匹配；None/UNKNOWN 不匹配。ON 沿用既有已准入的 JOIN 谓词家族。`left join o on o.v > 10` 与 `left join o on True` 加 `where o.v > 10` 不同，后者可以删除补空父行。“flatten”由这些明确操作承担，不另设自动 flatten 语法。`Unnest(Collect(R))` 与 `Collect(Unnest(N))` 不是无条件的改写法则，只在父 occurrence、投影、空集、重复、排序、presence 与作用域前提都满足时写有限的 metamorphic 断言。LEFT 占位经平面投影 `{v: None}` 后再 Collect 得 `[{v: None}]`；同一空输入经 CROSS 再 Collect 得 `[]`。

**最小反例。**

| 输入/操作 | 正确结果 |
|---|---|
| 父 occurrence A、A、B；每个 A 的子行 [7, 7]，B 为 [] | 嵌套结果 3 个父行，子行共 4 个 |
| 上例 CROSS 或 INNER（ON True）Unnest | 4 行，B 消失 |
| 上例 LEFT Unnest（ON True） | 5 行，B 保留一条占位 |
| 上例 LEFT Unnest，ON 为 `o.v > 10` | 3 行：两个 A 与 B 各保留一次占位 |
| 一个父行的 orders 2 行、payments 3 行，分别 Collect | 两个集合大小仍是 2 与 3，不是各 6 |
| 一个子行是 `{v: None}`，另一个父行的子表为空 | 一条真实全 NULL 记录与空集保持不同 |

**嵌套值经过既有关系算子。**

| 操作 | 本期规则 |
|---|---|
| 命名派生关系、模块输出读取、别名与投影 | 传递已准入的嵌套字段、身份、来源与 schema，随后可 Unnest；覆盖跨模块正例 |
| 普通 CROSS/INNER/LEFT JOIN 透传嵌套字段 | 只在既有 scalar ON 准入域内透传；LEFT 匹配到的空集合保留 `[]`，未匹配得 `None` 容器；普通 JOIN 按自身匹配数复制行与集合 |
| 普通 RIGHT/FULL JOIN 携带嵌套字段，或嵌套值参与 JOIN 比较 | 拒绝；旧平面 JOIN 不受影响 |
| 只用父层 scalar 的过滤、排序、LIMIT | 在既有准入域内保留嵌套值；carrier 不当普通 Text 解释 |
| 嵌套值用于 equality/hash/分组键/ORDER 键 | 拒绝（Phase72） |
| 含嵌套字段的整行 DISTINCT、UNION DISTINCT、INTERSECT/EXCEPT（含 ALL）与 UNION ALL | 拒绝 |
| lag/lead 等窗口值或 scalar 关系读取返回嵌套值 | 拒绝；closed 关系先完成既有 scalar 窗口再被 Collect 不因此禁止 |
| 先投影掉嵌套字段再执行旧 scalar 操作 | 按剩余真实 schema 与既有规则判断；执行路线仍检查完整 operation closure |

**一层嵌套。** collection depth 按递归值类型计算：scalar 为 0，record 取各字段最大值，NestedRelation(record) 为 1 加子深度，nullable 不增加深度；每个实际中间类型都必须在准入域内。命名、导入与别名保留深度；Unnest 消去对应层，所以“Collect → 显式 Unnest 成平面关系 → 再 Collect”仍是一层。Collect 的子关系仍含 collection 时拒绝，即使随后会被展开。这个类型深度独立于 D70.07 的块嵌套深度、关系读取深度与 compiled graph 大小限制；最终平面输出不清除完整 operation closure 的路线/R2 限制。

## 支持域与资源边界（D71.05、D71.07）

| 维度 | 本期必做 | 明确限制 |
|---|---|---|
| 项目模式 | EXPLICIT_MODULES，`schema_version = 2` | 单文件、LEGACY_FLAT、PACKAGE_ROOT 中的 `collect`/`unnest` 给出确定诊断，说明怎样建 `schema_version = 2` 项目 |
| 嵌套深度 | 一个 collection 层，子行是平面 scalar record；允许多个并列子表 | 子行里再放 collection 拒绝 |
| 子行类型 | 现有八类 leaf 逐类证明：Int/Bool/有限 Text（S12）、Float/Decimal（S14）、Date/Timestamp/UUID（S15） | 继承各自已准入域；不自动支持 Any/Bytes/Json 或所有 alias |
| Collect 来源 | 已完成的 closed 或已准入 captured relation | 不增加隐式 relationship traversal 或 group capture |
| SQL 目标 | PostgreSQL 的有限 lowering | MySQL 的新嵌套形状确定拒绝；旧平面 MySQL 回归 |
| 原生执行 | `postgres_rows` 的有界准入形状 | `postgres_adbc` 与 `mysql_rows` 的新嵌套形状在连接前拒绝，不回退到其他路线 |
| 编译产物 | live 路径及其必经 compiled graph；source-free bundle 闭环 | 公开 live API 不绕开 bundle |
| Arrow | 受检嵌套 batch、owned/borrowed/interop/IPC 所需闭包 | 不承诺全系统零拷贝或所有 Arrow 类型 |
| 保存与断源读取 | 顶层行完整保存；R1 与 `verified_export` 分别验证 | 子行不独立 checkpoint、ACK 或跨 chunk 拆分；只读导出不新增控制写入 |
| R2 | 新嵌套/Collect/Unnest 形状早期拒绝 | 普通执行成功不证明恢复坐标基础 |
| sink/relay | 新嵌套 effect 在 live 与 saved 入口早期拒绝 | 既有 scalar atom codec 不自动递归化 |
| UI/扩展 | 核心诊断、文档与真实示例 | 不新增 Run、grid、formatter 等；扩展任务独立 |

准入不能只看最终结果是否含 List/Struct：Collect/Unnest 即使最终输出平面列，也按真实 compiled operation 识别未支持的目标、路线或恢复方式。

**PostgreSQL carrier。** 优先实验相关子查询/LATERAL 加明确收集操作，输出一个受控的文本 carrier，再由 schema 指导的严格 decoder 建立 Arrow children；位置化 row array 是减少 key/identity 混淆的候选，最终取舍在 S02。JSON/JSONB 可以出现在 SQL 内部，但不得把逻辑类型写成 Text/Json 绕开嵌套 ResultContract，不得从第一行推断 schema，不得让 driver 先转成 Python float 再声称 Decimal 保真，不得用 JSON key 替代 field occurrence，不得丢失 Float 的 signed zero、Decimal scale 或 Timestamp 微秒与时区含义。PostgreSQL 的 `array_agg` 在零行时返回 NULL 而不是空数组、聚合输入顺序默认不确定，lowering 必须显式适配。SQL 内部 Unnest 的输出进入谓词、算术、排序或 LIMIT 之前，必须恢复原逻辑 scalar 类型与意义（例如 Decimal 不按文本排序）。

**内存与规模。** 执行正例分别说明：顶层完成关系的真实上界 P、每个子关系的上界 C_i、并列子表数 S、字段数 F、深度 D、scalar carrier 的可证明编码大小上界与来源前提是否真被履行，以及单 cell 字节、总子行、总运输字节与受检 Arrow 字节；`P × Σ_i(C_i × record_bytes_i + framing_i)` 一类数是运输量上界，不是数据库中间态、排序成本或 RSS 的证明。只声明了 `max_characters` 的 Text 不是真实长度保证。三层处理：语义与发射只决定可表达、可发射；运行准入在连接前拒绝静态不支持的路线/操作/形状，确需来源事实时在已授权连接后、提交大 carrier 查询或首次物化前核实，证据绑定本次 source/profile 与适用 snapshot；交付检查仍做 cell/children/bytes 检查并保留真实超限失败。保护性 LIMIT 不得静默加入源程序。
S02 的起点假设（D71.07，由 S02 证实或替换）：行数上限只数父行，`batch_rows`、`max_rows` 的含义不变；子行计入字节上限（默认每批 1 MiB）；每次执行最多 1,048,576 个子行；一个父行的列表放不进一批时整批拒绝，不拆行。S02 若无法经现有 qualification owner 证明来源约束，收窄到静态有界 VALUES 或已有受约束来源，并把丢失的用户场景交回所有者；最终核心正例仍须包含合格真实来源上的 closed/captured 子关系。

**离线读取与诊断。** IPC、R1、`verified_export` 各自验证读取边界，不沿用 PG 执行的内存资格：先以现有 envelope/输入字节限制约束元数据解析，再验证可核实的长度、深度、offset 与声明规模，才进入构造、解压或递归物化；交付后的 `max_bytes` 不充当分配前保护。IPC 的 96 MiB 上限、`compression=None`、`allow_64bit=False` 照旧，不因嵌套放宽；frame/contract digest 表达完整性与合同身份，不提供 authentication，新进程仍须经过既有 trust/binding 路径。坏 carrier、坏 IPC、source-free 与断源读取错误沿用既有诊断与脱敏规则，不默认回显 carrier、子值、运行时参数或私有对象 repr；用独立 sentinel 检查错误文本、诊断 JSON、explain、日志与证据摘要。

## 预埋边界与可逆实现选择

| 现在做 | 为什么以后补贵 | 本期最小动作 |
|---|---|---|
| 嵌套类型与子 occurrence 的独立身份 | 以后从 Json/Text 追回身份会破坏 API、序列化与下游解释 | 在现有语义/IR owner 加明确 variant，不造全局注册表 |
| 结构化结果 schema 与层级 nullability | 持久快照、IPC 与外部消费者会保存它 | 闭合、有版本的 shape，先只准入一层 |
| 完整 compiled records 与 digest | 错误共用旧 schema 会把历史包误当新含义 | 只调整真实受影响的版本维度；新旧失败边界有可运行证据 |
| 顶层 occurrence 仍是持久进度单位 | 改成子行 ACK 会牵涉 workspace、恢复与 sink 效果 | 完整保存一个顶层行，不建新进度协议 |
| 独立嵌套值/重数/NULL oracle | 同一个 decoder 兼任 expected 容易共同犯错 | 从原始 fixture 值独立生成预期，注入同型换列、丢重、offset 损坏 |

不预埋通用递归查询引擎、多方言嵌套框架、持续缓存、自动优化器或跨设备 schema registry。具体 helper 分布、私有类名、fixture 组织、SQL alias 与局部算法是执行器的实现自由，须复用既有 owner。

**最晚实证决定点。** carrier 编码、来源资格、运输量与离线读取可控域：S02 结束；拼写的逐字形态、同名识别、操作准入与捕获 body：S03/S04 的语义验收前；嵌套 schema/nullability、排序依据与 compiled 兼容维度：S07/S09 验收前；IPC framing、表示限制与保存读者资格：S17/S18 验收前；精确候选版本、安装 profile 与渠道：S23 展开时检查版本占用，发行另行授权。未闭合时对应新入口保持拒绝，不冻结 durable 表示。S02 的手写 carrier/Arrow 小实验只证明机制可行，不能替代 S12、S18、S19 的真实验收。

## 范围账本

- **必做**：第 6 节的语义、作用域、grain、ordering 与拒绝；现代语法下的 Collect 与 CROSS/INNER/LEFT Unnest；一个 collection 层、多个并列子表；八类已准入 leaf 逐类保真；PostgreSQL 发射与 `postgres_rows` 的真实公开纵向；live→compiled、bundle、ResultContract、Arrow/ownership/IPC 闭包；有界准入、超限失败、取消/cleanup，未支持路线与 R2/sink 的预拒绝；完整顶层行的保存、既有 publication 资格、断源 R1 与独立 `verified_export`；旧平面三路线、现代语法/迁移、错误与现有产物的回归；可安装候选、支持矩阵、示例、阶段末获取整合与 Phase72 交接。
- **时间够才做**：只在必做范围已满足、预计仍能在 25 片内完成 S23/S24、且没有新的不可逆边界时考虑，并须在最终包装与审计前集成：更完整的只读嵌套 schema 展示与教学例子（`explain` 显示 `recent_orders: list[{order_id: Int, total: Decimal}]` 是 S03 的 UX 候选）；改进既有拒绝消息的修复建议；一个额外的、明确有界的真实数据形状示例。S24 之后再增加产品工作须单列续行并重新验证受影响的包装与审计。
- **明确不做**：多层 collection；嵌套值的 equality/hash/DISTINCT/分组/排序/集合运算与 IN（Phase72）；隐式 group capture、自动安全再聚合，以及对列表做聚合（`len`、`sum(o.total for o in c.recent_orders)`、对列表用 `any(...)`，Phase73）；通用函数/插件 SPI 与用户可写的数组表函数（Phase74）；编辑器与扩展深度支持（扩展 owner / Phase75）；PG ADBC 嵌套路线与数据库原生 array/JSON 列（Phase76）；MySQL 嵌套输出与 `JSON_TABLE`（Phase77）；dataframe 嵌套适配（Phase80）；嵌套 fuzz 与高强度差分（Phase81）；嵌套公开格式冻结（Phase82）；自动 flatten/去相关/CSE（Phase88/93）；递归（Phase92）；子行级恢复、R2 与嵌套 sink 效果；UNION ALL、普通 RIGHT/FULL 携带嵌套与嵌套窗口值/读取；一个 capture let 读另一个 capture let（嵌套相关）；用户手写的嵌套 shape literal、嵌套参数、JSON 推型与外部 Arrow 表作为编译源；单文件与其他项目模式中的新构造；旧 bundle/job 自动迁移；D-11/D-12 整体恢复（现行路线图中 Pietto lead 的后续项）；发行动作。各项的接收 owner 与最晚点见[路线](slices.md#延期-owner)与[路线图](../../roadmap.md#future-roadmap-v6)。

## 三层验收

每项都要有真实能力、明确 owner、接通的消费者和区分性反例；路线表中的“覆盖 Axx”表示对终态的贡献，不表示整条已关闭。S03–S11 验收本层真实输入、正常构造/往返与确定拒绝，尚未接通的公开入口保持拒绝，并保留受影响旧平面直接消费者的可运行证据（例如 S09 关闭 Collect 的 compiled 层，A07 的公开执行部分要到 S12/S13 与最终串联验证才成立）。

| ID | 为真：用户/消费者行为 | 存在：必要 owner/数据 | 接通与验证 |
|---|---|---|---|
| A01 | `check` 对新类型、作用域与拒绝给出确定结果 | AST、semantic fact、嵌套身份与 nullability | 现代源码→真实 checker；同名不同 owner、forward/cycle、模式错误的正负例；单文件与其他模式的确定诊断 |
| A02 | Collect 保父行、重复、空集合与子行过滤 | 完成关系读取与 Collect fact | 独立 literal/occurrence oracle 对比真实 PG；空外层、空子表、全 NULL 子行 |
| A03 | capture/参数读取精确，group 不取代表行 | 既有 capture/parameter owner、新 use 与普通 JOIN 的嵌套字段透传 | 同名 sibling、外连接后捕获、参数切换、grouped-stage；LEFT 匹配 `[]`/未匹配 `None`/重复匹配正例；直接 group capture 拒绝 |
| A04 | CROSS/INNER/LEFT Unnest 正确改变行数与 nullability | Unnest 节点、presence 与 grain | 3 父行反例得 4/5 行；非空但 ON 全不匹配、UNKNOWN 与后置 WHERE；未知或损坏的嵌套输入确定拒绝 |
| A05 | 并列子表独立，子关系的 ORDER/LIMIT/过滤位置正确，未写 `order by` 的 collect 读取确定拒绝 | 各子关系的完成边界、含隐藏排序依据的 ordering demand | 2×3 fanout、nullable 非输出排序键、ties、LIMIT/ON/WHERE 位置与跨模块阶段组合；不声明一般等价 |
| A06 | PG SQL 真实执行正确，其他目标不假支持 | Plan、dialect AST、carrier demand、完整 source closure | 已安装编译器→真实提交→typed 值 oracle；MySQL 提交前拒绝；旧目标完整回归 |
| A07 | live 与 source-free bundle 保持同一语义 | 闭合 compiled records/build/verify/lowering | export/load/bind/execute；foreign root、删子行、错版本、错 occurrence 拒绝 |
| A08 | Arrow 嵌套值、schema、八类 leaf 与 ownership 正确 | 递归 ResultContract/binding/Arrow/IPC | exact values、signed zero、Decimal scale、时间/UUID、offset/validity 损坏、C/IPC 消费、close 后的归属 |
| A09 | 有界域正常执行，超限/失败/取消不伪装完成 | 实际公开 API、分层资格与预算准入、终态/cleanup | 在线与离线的 parent/child/cell/total 边界；来源事实过期、payload 错、超限、取消、primary/cleanup 与诊断脱敏 |
| A10 | 保存后断源 R1 与 `verified_export` 分别读出同一固定快照 | 现有 v7 chunk/checkpoint/contract/IPC/replay 与独立只读导出入口 | 新进程、无 driver、重分批与空结果；导出不新增 consumer/delivery/ACK/retention 写入；R2 与嵌套 sink/relay 的 live/saved 入口在外部作用前拒绝 |
| A11 | 旧平面能力与现代语法保持 | 现有函数 owner 测试与历史兼容读者 | 三路线旧正例、迁移/诊断、项目模式、逐项兼容矩阵、诊断脱敏与无 ambient I/O |
| A12 | 干净安装可按文档使用，状态诚实 | 候选 wheel/sdist、示例、支持矩阵、验收记录 | 安装后公开链路；本机/CI/渠道分层；没有发行授权不报 PUBLISHED |

## 需求矩阵（状态均为 PLANNED）

档位：PostgreSQL 18.6、`postgres_rows`（`psycopg[binary]==3.3.5`、`pyarrow==26.0.0`），EXPLICIT_MODULES 项目；MySQL 8.4.12 与 `postgres_adbc` 只作拒绝与旧平面回归。

| 需求 | 首个 owner | 输入/档位 | 可观察行为 | 独立证据 | 状态 |
|---|---|---|---|---|---|
| A01 check | S03（S04、S05 加厚） | 项目与各模式 | 确定结果与诊断 | 正负例、模式拒绝 | PLANNED |
| A02 Collect | S04（发射 S08，公开 S12） | PG、`postgres_rows` | 父行、重复、空集合 | occurrence oracle、原生执行 | PLANNED |
| A03 capture/参数 | S04（S16） | PG | 精确读取、无代表行 | 外连接后捕获、参数切换 | PLANNED |
| A04 Unnest | S05（公开 S13，leaf 语义 S14/S15） | PG | 4/5 行与 presence | 反例表、原生执行 | PLANNED |
| A05 并列与排序 | S04、S08（S16） | PG | 独立子表、顺序契约 | 2×3 fanout、ties、非输出排序键 | PLANNED |
| A06 目标 | S06、S08（S13） | PG；MySQL 拒绝 | 真实 SQL 正确 | 已安装编译器→原生提交、MySQL 拒绝 | PLANNED |
| A07 live/bundle | S09（公开 S12/S13，IPC S17） | live 与 source-free | 同一语义 | 篡改与错版本拒绝 | PLANNED |
| A08 Arrow | S10、S11（S12、S14、S15、S17） | `pyarrow==26.0.0` | 值、schema、ownership | 独立原值 oracle、offset/validity 损坏 | PLANNED |
| A09 有界执行 | S02（S12、S20） | `postgres_rows`、离线读取 | 有界、超限失败、cleanup | 边界与取消反例、sentinel 脱敏 | PLANNED |
| A10 保存/R1/export | S18、S19（S20） | v7 工作区 | 同一快照 | 新进程无 driver 读取、无控制写入 | PLANNED |
| A11 回归 | S01（S21） | 全量、三路线 | 旧能力不退化 | 权威全量与独立收集计数、自然 CI | PLANNED |
| A12 安装与状态 | S23（S24） | wheel/sdist | 按文档可用 | 干净安装、支持矩阵 | PLANNED |

## 逐形态分级骨架

值为负责的片；“拒”表示本期确定拒绝；细行在各片 Gate 1 填写。

| 形态 | 语言有效 | 计划完整 | 可发射（PG / MySQL） | 路线（`postgres_rows` / ADBC、MySQL） | 保存·R1·export / R2·sink |
|---|---|---|---|---|---|
| closed let 的 Collect | S03 | S04、S06 | S08 / 拒 | S12 / 拒 | S18、S19 / 拒 |
| captured let 的 Collect（含 Top-K） | S03 | S04、S06 | S08 / 拒 | S12 / 拒 | S18、S19 / 拒 |
| 多个并列 Collect 与阶段组合 | S03 | S04、S16 | S08、S16 / 拒 | S16 / 拒 | S18、S19 / 拒 |
| CROSS/INNER/LEFT Unnest（最终平面输出） | S03 | S05、S06 | S13 / 拒 | S13 / 拒 | S18、S19 / 拒 |
| 展开一项后仍保留另一嵌套字段 | S03 | S05、S16 | S16 / 拒 | S16 / 拒 | S18、S19 / 拒 |
| 经命名关系、别名与模块传递嵌套字段 | 现有语法 | S06、S16 | S08、S16 / 拒 | S16 / 拒 | S18、S19 / 拒 |
| 普通 JOIN 透传嵌套字段 | 现有语法 | S06、S16 | S16 / 拒 | S16 / 拒 | S18、S19 / 拒 |
| 单文件、LEGACY_FLAT、PACKAGE_ROOT 中的 collect/unnest | S03（拒） | — | — | — | — |

## 回归（必须仍然正常）

1. 0.1.5 现代词法/语法与源迁移语义，包括 BOM/CRLF/CR 与诊断位置。
2. 已准入的 scalar、命名参数、关系 let、capture/LATERAL、VALUES 与表函数。
3. 原平面 PG/MySQL SQL 与其既有拒绝；无授权不改变稳定 SQL 或 JSON 形状。
4. 平面 Arrow 类型/所有权、compiled/bundle/trust、来源资格与参数绑定。
5. 既有普通 execute、保存、R1、`verified_export`、R2、sink/publication 的平面合同；`release_saved_read`、`operation_result` 等元数据入口保持原行为。
6. 完整测试收集与选择、已安装消费者、可选依赖的惰性导入。
7. 编译与 CLI 不自动连接数据库；未支持路线没有 fallback；UNKNOWN 不变成成功。

回归按真实功能义务定位，不锁定 22,306 这个节点数或任何文件名。

## 本期不变量（V）

`AGENTS.md` 不改；下列不变量写在本 brief，各片 Gate 0/1 必读：
1. NestedRelation 的语义来自 semantic owner；Json/Text/List/Struct 不反推意义。
2. Collect 收集已完成的关系，保持父/子 multiplicity 与本层 filter/order/limit。
3. 不隐式 group capture、不任选代表行、不把并列子表先 JOIN 再收集。
4. 完整嵌套 schema、意义与身份进入 compiled records、ResultContract 与 digest。
5. 所有 children/offset/validity/buffer ownership 都要验证，不能只看顶层 schema。
6. 未准入的目标、路线、R2、sink 失败关闭；运行正例写明资源前提。
7. 一个顶层嵌套行是一个持久 occurrence；子行不独立 ACK 或恢复。
8. 原平面能力与现代语法必须回归；没有代码修改、执行或发行授权不自动跨界。

## 17 节结论与 30 项映射（紧凑）

| 节 | 结论 | 30 项 |
|---|---|---|
| R/A/C | 见上文事实、能力表、硬障碍与路线图约束；最新使用反馈未提供，不编造 | 1、6、17、18、28 |
| B/J0 | 使命与五项终态如上；24 片 / 容量 25；`0.1.6` 打包；时间不承诺 | 2、7、8、12、29 |
| D 预埋 | 只预埋嵌套身份、闭合 shape、compiled/digest 维度、顶层 occurrence 进度与独立 oracle | 3、4、5、15、16 |
| E 推迟 | 见“明确不做”，每项有 owner 与回收条件（[路线](slices.md#延期-owner)） | 28 |
| F 扩展 | 不收新特性；只收同域示例、修复建议与一个有界真实形状示例 | 2 |
| G 外部借鉴 | Malloy：ADAPT 用户模型；PostgreSQL 18.6：ADOPT/ADAPT 有限机制；Apache Arrow 26.0.0：ADOPT 表示。11 字段记录见[外部参考记录](planning-notes.md) | 10、11、22、23、24 |
| H/I/S | 见所有者决定、语义契约、支持域与三项风险 | 9、13、14、19、25、26、27、30 |
| J/V/K/L/Q | 三层验收与回归如上；V：不改 `AGENTS.md`，不变量如上；K：路线图表格行被生命周期读者逐字锁定，不改表格行，延期 owner 与 `pietto fmt` 步骤写在表格后的说明；L：见[路线](slices.md)；Q：计划 v2 的两轮与追加 24 遍复查、lead 的校准 r2 与补遗、P 组决策的独立核验，发现按根因处置 | 20、21、29 |

路线发布时 30 项都已闭合，或已定阶段级规则、只把实现级名称、诊断码与逐形态行留给指定片的 Gate 1：第 1 项由 S01 在下一版候选上重绑（main、本地 writer、worktree 与活动合同），第 20 项的新诊断码段与逐字消息由 S01/S03 在绑定的基线上确认，第 26 项的 runner、platform 与 driver patch 在执行前重新绑定，第 30 项的上限与停止规则已由 D71.10 写明。没有 UNKNOWN 留到开工。

## 三项风险

| 风险 | 早期信号 | 应对与停止条件 |
|---|---|---|
| 语义/粒度错误被“能返回 JSON”掩盖 | 重复父行被合并、并列子表相乘、全 NULL 子行消失、group capture 取代表行 | 独立 occurrence/typed BAG oracle；S04–S06 先验证反例，失败不进入具体结果 |
| compiled/Arrow/IPC/所有权有隐藏的平面假设 | live 通过但 source-free 失败、切片 offset 错、close 后数据失效、digest 漏子行 | 按真实 producer 依赖推进 S07–S11；S17 可提前研究但整片等待输入闭合；缺真实消费者不得 COMPLETE |
| native cell 物化与 carrier 精度突破预算 | `max_rows` 很小但 payload 巨大；Decimal/Float 失真；声明长度未被证明 | S02 实证 carrier 与前提；只准入有证明的有限域；不靠偷偷 LIMIT 或宽松解码“修复” |

旧债只偿还直接阻断本期的平面假设；D-11/D-12、CI 调度、通用 renderer 重构与全仓测试重组不作为顺带工程。
