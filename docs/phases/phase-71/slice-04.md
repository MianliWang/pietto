# Phase71 S04 — Collect 对已完成关系的绑定（candidate）

## 状态与决定

本文是批次 B2（S04、S05、S06、S07）中 S04 的**批次候选**记录。B2 建立在 `0.1.6` 的发行提交 `bdb3f567`
之上：`0.1.6` 已发行，含 B1、post70 修正批次、依赖维护、MySQL 单文件 parity `06d18554` 与项目模式修正
`60adc230`，B2 不属于 `0.1.6`。B2 只在四片提交一起 FF push、批次头的自然 exact-head CI 全部 job 成功后才
`COMPLETED / PUBLISHED`，此前都是 candidate。
本文不声称 B2 已验证或已发布。

决定来源是 S04 Gate 1 记录
`/home/mianliwang/.local/state/pietto/evidence/pietto-phase71-20261026/claude-takeover-20261027/b2-records/S04-GATE1.md`
（ARCHITECTURE_DECISION；所有者 2026-10-27T15:18Z 接受 B2 Gate-1 决策包的推荐，
`owner-answer-20261027T1518Z.json` 的 `b2_gate1`）。Gate 1 中的行号指当时的基线，不是本提交的树。

| 决定 | 内容 |
| --- | --- |
| D-S04-1 类型承载 | 新增 `ProjectResolvedTypeKind.NESTED_RELATION`；`ProjectResolvedType` 带 kw-only 的 `nested` 描述符，kind 与描述符必须一致。嵌套类型的内部名 `<nested relation>` 不出现在任何公开输出中。描述符删除 `container_nullability`：容器 nullability 只看所属行字段，直接 Collect 的容器恒为 NON_NULL。类型相等是元素关系 occurrence 身份加有序子字段身份，与值相等无关（值相等属 Phase72）。adapter 把嵌套类型显式映射为 kernel UNKNOWN，不抛异常。S04 由此在两处重开 S03 的嵌套类型契约（类型从 sidecar 移到父字段上；删除容器 nullability） |
| D-S04-2 引用闸门 | `PIE-S2805` 在既有的逐引用权威处判定（无 JOIN 的引用候选、无 JOIN 的 ORDER BY、JOIN 路径字段查找、JOIN ON、ANY、capture 环境、relation read 的列、整行消费者）；不改 kernel，不从 schema 中去掉嵌套字段。被判定的引用照常解析，不报 `PIE-S2102`；带它的 carrier 变为非具体。`unnest(binding.field)` 的参数不是标量引用，不在此判定 |
| D-S04-3 白名单 | 只拒 UNKNOWN 的读者改为只接纳标量 kind；这些点只负责失败关闭，不各自报码。集合列复制 `resolved_type`，不再按名字重建 |
| D-S04-4 唯一权威 | `ProjectModuleCollectReadFact` 与 scalar read 事实并列，是 Collect 读的唯一权威（typed ⇔ 无诊断；常量 BAG、`[]`、NON_NULL 容器、深度 1 不可配置）；S03 sidecar 的 Collect occurrence 改为从它派生。completed output 的来源就是这个事实对象，completion 能从它走到被收集 let 已完成的排序（含非输出键） |
| D-S04-5 闸门 G2 | `PIE-S2802` 的码、文本、位置与顺序不变；含 Collect 的关系真实完成，精确诊断与 `PIE-S2802` 并存；有效嵌套程序的 `check --project` 只得到 `PIE-S2802` 集合，`emit-sql --project` 仍 BLOCKED、`artifact: null`。删除 S03 的 Collect owner 特例 |
| D-S04-6 冻结词表 | 私有 `pietto.module-inspection.v1` 的 `resolved_type_kind` 词表与格式不变：词表锁把它列为五个成员的精确子集，`ProjectInspectionTypeResolution` 拒绝 NESTED_RELATION |
| D-S04-7 透传边界 | 读含 Collect 输出的关系（FROM、JOIN、`exists`、标量列的 `scalar`/`in`）可行；再选出嵌套字段报 `PIE-S2805`（透传归 S16）；集合运算元与 SELECT DISTINCT 报 `PIE-S2805`；Collect 一个含嵌套字段或列在 completion 前未知的 let 报 `PIE-S2803` |

## 交付

- 删除 S03 的两处隔离（model 中的 DEFERRED 行状态与 joined aggregation 的 Collect 投影特例）：含 Collect
  的关系真实完成，无 JOIN 与有 JOIN 的父关系一样；Collect 输出是 completed output field。
- Collect 准入：只在未分组声明体的 SELECT 中；目标必须是同一体中声明的 relation let；列在 completion 前已知；
  叶类型是八类之一（Bool、Date、Decimal、Float、Int、Text、Timestamp、UUID），nullability 已知；深度 1。
  alias 叶按其 canonical builtin 定型，逐类执行准入归 S12/S14/S15（brief 的“不自动支持所有 alias”）。
- 被 collect 读的 let 未写 `order by` 报 `PIE-S2804`（D71.03），closed 与 captured let 都适用。
- captured let 的单次使用族加入 `collect`（`PIE-S2370`）；Top-K 已由 S03 实现，S04 只验证。
- 嵌套字段在任何其他位置的读报 `PIE-S2805`；整行消费者（DISTINCT、集合运算）失败关闭。
- 文档：`docs/language.md` 的 Collect 节（有序 let、closed 与 captured、`[]`、`None` 与 `[{v: None}]` 的区别、
  只在未分组 SELECT 中、其他位置的 `PIE-S2805`）；`docs/spec/diagnostics.md` 新增 `PIE-S2803`、`PIE-S2804`、
  `PIE-S2805` 三行，修改 `PIE-S2302`、`PIE-S2333`、`PIE-S2370`、`PIE-S2802` 行；`docs/release-notes.md` 的
  “Collect reads in explicit-module projects” 条目。

## 诊断

逐字文本以 `docs/spec/diagnostics.md` 为准；全部是 ERROR，只在 EXPLICIT_MODULES 项目出现（其他模式已在
`PIE-S2801` 停止）。

| 码 | 规则 |
| --- | --- |
| `PIE-S2803`（新） | Collect 读不被准入：分组 SELECT 或 relation let 中（模块 relation-resolution 诊断，排在 `PIE-S2802` 之前）；目标不是同一体的 relation let；列在 completion 前未知（读集合运算、VALUES、authored JOIN 或表函数的 let 及读它们的 let，同 `PIE-S2348` 先例）；叶类型、未知 nullability 或深度（Collect 读事实诊断，在 `PIE-S2802` 之后）。每个读最多一条 `PIE-S2803` 或 `PIE-S2804` |
| `PIE-S2804`（新） | 被收集的 let 没有 ORDER BY；修法写进 message（text 输出只打印 message），不填 related location，公开 JSON 形状不变 |
| `PIE-S2805`（新） | 嵌套值用在不准入的位置：值用法（位置是封闭集合）、再选出（透传）、SELECT DISTINCT、集合运算元；与同一表达式的 `PIE-S2102`/`PIE-S2105` 同位，每个叶一条 |
| `PIE-S2370`（消息变化） | read-once 消息由 ``... by exists, scalar, in or a join ...`` 改为 ``... by exists, scalar, in, collect or a join ...``；平面程序同样受影响，发布说明已写明（D71.01 批准的消息提示） |
| `PIE-S2802`（不变） | 每个 Collect 读与 Unnest let 各一条；行内补充：不被准入的 Collect 读另报 `PIE-S2803` 或 `PIE-S2804`，读其嵌套字段报 `PIE-S2805`，含 Collect 读的关系像其他关系一样完成 |
| `PIE-S2333`（补充） | 收集一个 ORDER BY 键只是一个指向非窗口 SELECT 输出的名字的 let 时，completion 尚不能按该键给 Collect 值排序，报 `PIE-S2333` |

## 不交付与 owner

| 内容 | owner | 在 S04 中的行为 |
| --- | --- | --- |
| Unnest 绑定、参数与 JOIN 规则、presence、grain，`PIE-S2806`/`PIE-S2807` | S05 | 维持 S03：`PIE-S2802` 加继承的 JOIN 诊断 |
| IR/plan 中的 Collect/Unnest、source closure、plan 级 kind 词表 | S06 | G2 关闭，不可达 |
| 递归 ResultContract 与其黑名单 | S07 | G2 关闭 |
| 发射；MySQL 拒绝 | S08、S13 | — |
| 嵌套字段透传（再选出，经命名关系、别名、模块、普通 JOIN 输出） | S16（建议的接收 owner；S24 不得在未指派时收尾） | `PIE-S2805` |
| let 体中的 Collect；分组 SELECT 中的直接 Collect；读集合运算、VALUES、authored JOIN、表函数的 let 的 Collect | S16 | `PIE-S2803` |
| 嵌套值的 equality、hash、DISTINCT、分组、排序、集合运算 | Phase72 | `PIE-S2805` |
| 含 Collect 读的关系中读 shape 字段的 SELECT 项、绑定 shape 字段的 let（与 `select distinct` 一样走无 JOIN 重放） | S16（建议的接收 owner，待 lead 处置） | 无原因的 `PIE-S2333`，已写入文档 |

## 集成、检查与交接

- 开发树 `e1efdfdf`（基于 S03 c3 `38e17b7b`），经 Gate 2 评审与修复轮次（证据在
  `/home/mianliwang/.local/state/pietto/evidence/pietto-phase71-20261026/claude-takeover-20261027/wf10/` 与 `wf11/`）；
  B2 阶段树 `bb906006` 在 B1 main 树 `484cced8` 上（`wf14-b2/s04-*`，评审 r0/r1 没有发现 rebase 缺陷）。之后同一
  delta 以 `git apply --3way` 接到 `938f2e17`（MySQL parity 提交的树）上，得到 `1e0534a0`：`project_scalar_namespaces.py`、
  `existence_values.py`、`module_semantic_fact_preservation.py` 与 post70 修正的 shape 定型二次推导同处冲突，
  合并后两者并存（先算本 carrier 的 `PIE-S2805`，再做 shape 二次推导，最后按源顺序并入嵌套诊断）；
  `docs/release-notes.md` 保留 B1 条目并在其后加 S04 条目；`docs/spec/diagnostics.md` 的 `PIE-S2333` 行取 main
  的新文字，再接 S04 的补充句。
- `0.1.6` 发行后，本提交把同一 delta（`938f2e17..1e0534a0`）以 `git apply --3way` 重放到发行提交的树
  `3f4c6a06` 上。项目模式修正的代码与诊断在重叠处优先，S04 的嵌套逻辑叠加其上：
  `project_join_conditions.py` 的 ON 读先判嵌套字段（`PIE-S2805`），其余无目标的读用项目模式的
  `_reference_diagnostic` 并记入 `unavailable_diagnostics`；`project_joined_aggregation.py` 的
  `_direct_read_diagnostic` 与 `_nested_field_reads` 并存；`project_joined_windows.py` 先按单文件改写歧义读
  （`PIE-S2335`），再处理嵌套读；`project_completed_semantics.py` 保留项目模式的 `follows`、`unavailable_ids`
  与 `_selected_unknown_group_keys`，Collect owner 的例外改为 S04 的 `refused_collect_owners`，结果再经
  `_one_report_per_nested_read`；`project_final_outputs.py` 中无 JOIN 的 ORDER BY 先给 SELECT 输出名报项目模式的
  `PIE-S2102`，再并入嵌套读（同位时 `PIE-S2805` 取代它），LIMIT 错误按项目模式先于 ORDER BY 报告，并带
  ORDER BY 中嵌套读的 `PIE-S2805`。合并暴露两处交互，各作最小修正：项目模式新增的单文件分组检查
  （`with_single_file_grouping_diagnostics`）跳过读嵌套字段的关系，与读 let 名或 relation 的关系相同（否则在同一
  读处多报 `PIE-S2318`、`PIE-S2321`，并多出 `PIE-S2312`、`PIE-S2308`）；Unnest JOIN 的输入在其 let 自己报错
  （`PIE-S2802`）时按项目模式的“输入失败已报告”处理，不再多报 `JOIN pre-match input or relationship authority is
  unavailable.`，与 alias let 控制组一致（D71.02）。测试期望随项目模式改变：EXPLICIT_MODULES 项目不再报
  LEGACY_FLAT 的临时准入文字（`PIE-S2334`）；关系内已有自身错误（包括 Collect 读的 `PIE-S2802`）时不补无原因的
  `PIE-S2333`；失败关系的读者不再报 `PIE-S2333` 或 `PIE-S2348`。按同一规则，读失败 let（其自身错误或所读关系
  失败）的 Collect 读也不报 `PIE-S2803` 的 “columns … are not known before completion”，与 scalar 读在同一处并入
  `unavailable_ids`（等价评审 R1）。`docs/spec/diagnostics.md` 取 main 的文字再接
  S04 的补充（`PIE-S2302` 的 `collect`、`PIE-S2333` 的 Collect 句），并在单文件分组检查一段写明读嵌套字段的
  关系只报 `PIE-S2805`；B1 条目留在发布说明的 `0.1.6` 节，S04 条目放在其上新的
  “Unreleased changes following 0.1.6” 节。
- 测试 owner：`tests/test_project_nested_relation_facts.py`（AC-01..05、07..10、12..14、17）、
  `tests/test_project_let_relations.py`（capture 与 `PIE-S2370` 消息）、
  `tests/test_semantic_rust_ready_pure_boundaries_differential_vectors.py`（词表 `narrowed` 子集）、
  `tests/test_project_private_module_inspection_canonical_serialization.py`（carrier 拒绝）。
- focused 检查（Python 3.13.13，`PYTHONPATH=src`，`-p no:cacheprovider -n 4`）：上述 owner、
  `test_repo_docs_examples`、`test_semantic_syntax_admission`、`test_diagnostics`，以及 import 被改共享模块的
  owner（IR 行等价与集合、JOIN 语义、分组 schema、shape 解析等）。批次权威验证在集成主机上对 B2 最终树做一次。
- 文档项（发布评审复现并修正，行为不变，都失败关闭）：`PIE-S2803` 行曾把 `between` 列为自带 nullability 的
  写法，而现代语法只接受 `lower <= value <= upper`，kernel 把它与比较一样定为 nullability 未知的 Bool，被收集时报
  “nullability 未知”，现列入比较一类（S04-R1-01，MINOR）；`docs/language.md` 与发布说明曾说 Collect 任何非
  relation let 都报 `PIE-S2803`，实际只有 source、table、query（含导入的）报 `PIE-S2803`，alias、值或窗口 let
  报 `PIE-S2301`（S04-R1-02，NIT）；含 Collect 读的关系中读 shape 字段的 SELECT 项或绑定 shape 字段的 let
  使关系报无原因的 `PIE-S2333`，与 `select distinct` 关系相同，现写入 `docs/language.md`、`PIE-S2333` 行与
  发布说明（B2-SHAPE-COLLECT-1，MINOR；放宽见上表）。
- 交接：S05 复用 S03 冻结的 `unnest_lets` 谓词与“写在该 let 之前的 FROM/JOIN binding”可见性；S06 在移动 G2
  之前重跑引用位置矩阵与代理；result contract 的黑名单交给 S07。
