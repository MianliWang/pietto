# Phase71 S05 — CROSS/INNER/LEFT Unnest 绑定（candidate）

## 状态与决定

本文是批次 B2 中 S05 的**批次候选**记录，建立在 [S04](slice-04.md) 之上；B2 建立在 `0.1.6` 的发行提交
`bdb3f567` 之上，不属于 `0.1.6`，其发布规则见[路线](slices.md)。本文不声称 B2 已验证或已发布。

决定来源是 S05 Gate 1 记录
`/home/mianliwang/.local/state/pietto/evidence/pietto-phase71-20261026/claude-takeover-20261027/b2-records/S05-GATE1.md`
及其 Amendment A1（lead 2026-10-28 应用，取代 §5.1 的 `PIE-S2806` B1 消息与 §8 AC-03 的程序清单）；
ARCHITECTURE_DECISION，所有者 2026-10-27T15:18Z 接受 B2 Gate-1 决策包的推荐（D-S05 = U1）。

| 决定 | 内容 |
| --- | --- |
| D-S05-1 表示 U1 | 每个合格的 Unnest let 是一个块内 catalog occurrence，按身份绑定，绝不按作用域名字查找（镜像表函数先例）：`ProjectDeclarationOccurrence.unnest`、`ProjectModuleCatalog.unnests`、视图节点 `UnnestRelationDef`（parser 从不构造）、身份判别字段 `unnest_position`（kw-only，非 None 时 `let_position` 为 None 且不是表函数）。所有身份构造点走同一个共享函数，避免 Unnest occurrence 拿到所在声明的身份。Unnest JOIN 按 authored span 对应到 occurrence。私有 QB-IR 检查编码器在缺省时省略 `unnest_position`（平面字节不变），非 None 时失败关闭 |
| D-S05-2 参数可见性 | `unnest(b.f)` 的 `b` 必须恰好是写在该 let 之前的 FROM binding 或更早的 CROSS/INNER/LEFT 具名 JOIN binding；SEMI/ANTI target 与 RIGHT JOIN target 不是。共享谓词放在 `_syntax_admission.py` 的 `unnest_lets` 旁边，规范化与事实构造共用。它是 LATERAL“JOIN 左侧”规则的严格子集，以后放宽是兼容变化 |
| D-S05-3 字段、nullability、presence、grain | 源 binding 被更早的 LEFT JOIN 补空时容器字段 NULLABLE（只取自既有 current-join 行）；元素字段按被收集 let 的输出顺序，身份 owner 是 Unnest occurrence，provenance 指向子字段身份；CROSS/INNER 保留子字段 nullability（只能经既有 null-rejection 收窄），LEFT 时全部 NULLABLE、nulling cause 是这个 JOIN；LEFT 占位只由 nulling cause 识别；occurrence 没有唯一键、FD 或行数上界，父关系的键在输出中不再唯一；输出没有顺序（D71.03） |
| D-S05-4 片内拒绝 | 同一体中 Unnest 与 GROUP BY、聚合、HAVING、窗口、QUALIFY、SELECT DISTINCT、`any(...)`、Collect 读、另一个 Unnest 并存，relation let 体中的 Unnest，都报 `PIE-S2807`（留给 S16 放宽）；写在 Unnest JOIN 之前、可能补空源 binding 的 RIGHT/FULL JOIN 在本期永久拒绝。WHERE、行值 let、外层 ORDER BY 与 LIMIT、写在 Unnest JOIN 之后的 RIGHT/FULL JOIN 不拒绝 |
| D-S05-5 诊断阶段 | `PIE-S2807` 全部在规范化阶段，与 `PIE-S2604` 同阶段同顺序，报出后不做语义分析；`PIE-S2806` 的 binding 类在规范化阶段，字段类型类在语义阶段（在 `PIE-S2802` 之后）；未知字段保持 `PIE-S2102` |
| D-S05-6 闸门 G2 不变 | 每个 Unnest let 仍各一条 `PIE-S2802`；有效 Unnest 程序 `check --project` 只得到 `PIE-S2802` 集合，`emit-sql --project` 仍 BLOCKED |
| D-S05-7 唯一权威 | `ProjectModuleUnnestOccurrenceFact`（owner 与 occurrence 身份、authored let、被准入的 JOIN、源 binding 位置、源字段身份与链接的 Collect 读事实、`nested_type`、元素输出身份、`diagnostic`；typed ⇔ 无诊断）；S03 sidecar 的 Unnest 输入改为这个事实（不再自己解析 binding），completion 的输出来源直接是这个事实对象 |

## 交付

- `let o = unnest(p.field)` 加恰好一个 `cross join o`、`inner join o on ...` 或 `left join o on True`：`o` 有被收集
  let 的字段，它的 JOIN 报任何 JOIN 都会报的内容，规范的合法 Unnest 程序不再显示继承的 `PIE-S2334`/`PIE-S2335`。
- 三种 JOIN 的语义：`[]`、未匹配外连接的 None、子行都不满足 ON 时，CROSS/INNER 不产生行，LEFT 保留一行占位；
  k 个子行满足 ON 时都产生 k 行。ON 与 WHERE 的区别由既有的 ON/joined filter 放置事实承载。
- 删除 S03 按位置识别 Unnest JOIN 的 `is_unnest_join` 与 sidecar 自己解析 binding 的 `ProjectUnnestInputFact`。
- 文档：`docs/language.md` 新增 Unnest 小节（写法、三种 JOIN 的对照表、ON 与 WHERE、无顺序与键、参数规则、拒绝
  清单）；`docs/spec/diagnostics.md` 新增 `PIE-S2806`、`PIE-S2807` 两行并修改 `PIE-S2802` 行；`docs/release-notes.md`
  的 “Unnest binding in explicit-module projects” 条目。

## 诊断

逐字文本以 `docs/spec/diagnostics.md` 为准；都是 ERROR，只在 EXPLICIT_MODULES 项目出现。

| 码 | 规则 |
| --- | --- |
| `PIE-S2806`（新，位置是参数） | B1：不是写在 let 之前的 FROM 或 CROSS、INNER、LEFT JOIN binding（含 RIGHT JOIN target；A1）；B2：FROM 别名的原名，消息给出 `unnest(alias.field)`；B3：表函数 binding；F1：字段不是嵌套关系；F2：字段类型未知且上游无 ERROR 解释。每个 Unnest let 至多一条，顺序 B1、B2、B3、`PIE-S2102`、F1、F2 |
| `PIE-S2807`（新） | K：RIGHT/FULL Unnest；M：第二个及以后的 JOIN；R：其他读取（封闭的 `{use}` 集合）；S：同体中的不准入构造（封闭的 `{construct}` 集合，每个 let 至多一条）；L：relation let 体中。FULL JOIN target 写在 Unnest JOIN 之前时报 S（可能补空），不报 `PIE-S2806` |
| `PIE-S2802`（行修改） | Unnest let 的 JOIN 在其书写位置读参数嵌套字段的行，与任何 JOIN 报同样的诊断；不被准入的 Unnest 改报 `PIE-S2806` 或 `PIE-S2807` |

## 不交付与 owner

| 内容 | owner |
| --- | --- |
| IR/plan 中的 Unnest 表达与 source closure；G2 的移动 | S06 |
| Unnest 的 PostgreSQL 发射；最终平面输出的 Unnest | S08、S13 |
| D-S05-4 中留给放宽的组合（分组、聚合、窗口、DISTINCT、`any(...)`、Collect、多个 Unnest、let 体） | S16 |
| 一般化的 nullability 收窄 | Phase72 |

## 集成、检查与交接

- 开发树 `5bb98d01`（基于 S04 r1 `b3826607`），经评审与修复轮次（证据在
  `/home/mianliwang/.local/state/pietto/evidence/pietto-phase71-20261026/claude-takeover-20261027/wf10/` 与 `wf11/`）；
  B2 阶段树 `22553b74`（`wf14-b2/s05-*`，评审 r0 无可复现缺陷，Teach 非权威全量与 main 基线逐节点对比无新失败）。
  之后阶段 delta 以 `git apply --3way` 接到 MySQL parity 树上的 S04 树，全部干净应用，得到 `a8106928`。
- `0.1.6` 发行后，本提交把同一 delta（`1e0534a0..a8106928`）以 `git apply --3way` 重放到发行提交上的 S04 树。
  冲突与处理：`nested_relation_facts.py` 按 S05 删去 `_visible_bindings`、`is_unnest_join` 与 S04 重放时为 Unnest
  JOIN 加的 `unnest_join_lets`，`project_completed_semantics.py` 的 `_blocked_inputs` 回到项目模式的原样：S05 的
  Unnest occurrence 是 JOIN 的目标，项目模式的“输入失败已报告”直接作用于它；完成诊断与 JOIN 条件诊断同时经过
  项目模式的 `unavailable_ids`、LEGACY_FLAT 准入过滤与 S05 的 `unnest_join_noise`；
  `project_relationship_predicates.py` 合并两边的 import；`tests/test_project_nested_relation_facts.py` 取 S05 的
  Unnest 期望；发布说明的 S05 条目接在 “Unreleased changes following 0.1.6” 节的 S04 条目之后。无冲突的新 owner
  `tests/test_project_nested_relation_unnest.py` 的期望同样随项目模式改变（与 S04 记录同一原则）：不再报 LEGACY_FLAT
  准入文字（`PIE-S2334`，含 LEFT JOIN ON、集合操作与 Unnest 后的 RIGHT JOIN）；JOIN ON 的未知引用与歧义字段取
  0.1.6 的消息（`JOIN ON reference is unknown: o.missing`、`Ambiguous field: id; write parent.id or o.id`）；
  producer 未完成的用例期望 `[]`；alias 控制组中 JOIN 跟随已报告的失败，不再报自己的 `PIE-S2335`。发布说明不再
  声称正确的 Unnest “不再显示继承的 `PIE-S2334`、`PIE-S2335`”，因为 `0.1.6` 在该处只报 `PIE-S2802`。
- 测试 owner：`tests/test_project_nested_relation_unnest.py`（新 owner，measured aspect split：`test_project_nested_relation_facts.py`
  在 S04 后已超过 2,000 行，S05 再加约 1,800 行；AC-01..13 与 test-local 的 Unnest oracle）；
  `tests/test_project_nested_relation_facts.py`（只更新被 S05 合法改变的 Unnest 期望）；
  `tests/test_project_module_qualified_nominal_declaration_catalogs.py`（catalog 的 `unnests` 与 occurrence 的
  `unnest`、`unnest_position` 字段表）；
  `tests/test_project_cross_module_table_query_relation_resolution_row_facts_legacy_compatibility.py`（resolution
  环境的 `unnest_symbols` slot）；`tests/test_harness_sql_emission_portability.py`（编码器不编码 `unnest_position`）；
  `tests/test_project_parse_only_check.py`（schema 2 中与 Collect 同体的 Unnest 在语义前报 `PIE-S2807`）。
- focused 检查（Python 3.13.13，`PYTHONPATH=src`，`-p no:cacheprovider -n 4`）：上述 owner、S04 的 owner 与
  `test_semantic_syntax_admission`、`test_repo_docs_examples`、`test_diagnostics`，以及 import 被改共享模块的
  owner（IR 查询块与集合、plan JOIN 作用域、let 作用域、JOIN 语义、窗口计算等）。
- 交接：S06 让 Unnest 进入 IR/plan 并退休 `PIE-S2802`；`ProjectModuleUnnestOccurrenceFact` 是 S06 计划记录的语义来源。
