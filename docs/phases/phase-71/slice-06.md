# Phase71 S06 — IR/ProjectSQLPlan 中的 Collect 与 Unnest（candidate）

## 状态与决定

本文是批次 B2 中 S06 的**批次候选**记录，建立在 [S04](slice-04.md) 与 [S05](slice-05.md) 之上；B2 建立在 `0.1.6`
的发行提交 `bdb3f567` 之上，不属于 `0.1.6`，其发布规则见[路线](slices.md)。本文不声称 B2 已验证或已发布。

决定来源是 S06 Gate 1 记录（workflow `wf_f037202f-d24` 的 `s06-gate1`；修订后的副本
`/home/mianliwang/.local/state/pietto/evidence/pietto-phase71-20261026/claude-takeover-20261027/wf24-next/b2-close/s06-gate1.amended.txt`）。
ARCHITECTURE_DECISION，所有者 2026-10-27T15:18Z 接受 B2 Gate-1 决策包与设计准备的推荐；S04 的 D-S04-5 与 S07 的
D-S07-8 把闸门 G2 的移动交给本片。S06 是一笔提交，含两个私有工作包：S06-C（Collect）与 S06-U（Unnest，等 S05
冻结后实现）。

| 决定 | 内容 |
| --- | --- |
| D-S06-1 G2 移到发射边界 | 退休 `PIE-S2802`（码不复用）。合法嵌套程序 `check --project` 通过（rc=0，JSON `ok: true`）；`emit-sql --project` 在每个 Collect 读报 `PIE-B1003 collect_not_admitted_on_target`、在每个 Unnest let 报 `PIE-B1003 unnest_not_admitted_on_target`，所有目标都报，位置与原 `PIE-S2802` 相同。S08 让 PostgreSQL 不再报 Collect 的这一项，S13 对 Unnest 做同样的事，MySQL 保留到 Phase77；detail 拼写在本片一次定下 |
| D-S06-2 Collect 的投影 | Collect SELECT 项不建 `ProjectSQLProjection`、expression site 或行表达式；`ProjectSQLCollect` 自己是其导出端口的投影（窗口与聚合投影的先例），避免按位置读 `plan.expressions` 的读者读到错误记录 |
| D-S06-3 order 与 limit | 不存进记录，由 `collect_order(plan, c)` 与 `collect_limit(plan, c)` 从 producer 派生 |
| D-S06-4 导出需求 | 嵌套导出端口不建 `ExportRepresentationDemand`，由 COLLECTION 族的 `COLLECT_EXPORT` 代替；每个非 source 导出端口恰好有二者之一 |
| D-S06-5 需求族 | `ProjectSQLDemandFamily.COLLECTION = "collection"` 与 `MappingGap.COLLECTION`，在 PostgreSQL 与 MySQL 上都是残余需求，没有 capability key；新枚举值都不用 `nested_relation` 拼写（S04 的公开输出哨兵） |
| D-S06-6 不新增 blocker kind | 嵌套值的误用由语义层 `PIE-S2803`、`PIE-S2805`、`PIE-S2806`、`PIE-S2807` 拒绝；plan 遇到不可能的状态按结构不变式失败，验证器报 `STRUCTURE` |
| D-S06-7 Phase65 观察 | `_check_context` 对含 `collects` 或 `unnests` 的 plan 抛 `UNSUPPORTED_VALUE`（Phase70 LATERAL 先例），规则表不变 |
| D-S06-8 私有 QB-IR 检查文档 | 不改；只加见证：嵌套程序确定地序列化，字节中没有哨兵字符串；Unnest 身份仍由 S05 编码器拒绝 |
| D-S06-9 source map | `CollectRelationExpr` 进入已知节点，`SYNTAX_ROLES` 加 `COLLECT`（cause 是 SelectItem）与 `UNNEST`（cause 是 JoinClause） |
| D-S06-10 端口血缘 | `collect_of(plan, port_ref)` 沿 EXPORT、INPUT_PORT、JOIN_PORT 的封闭边集找唯一的 COLLECT，找不到或不唯一时失败，不选赢家；S06-U 与 S07 是调用者，透传一支留给 S16 |
| D-S06-11 发射拒绝位置 | 在 D70.05 表函数拒绝之后、标量端口检查之前收集嵌套拒绝，按 (path, line, column) 排序；只要有嵌套拒绝就返回。Gate 2 修复 S06U-PLAN-R1-1 之后，scalar-meaning 准入的提前返回不再吞掉嵌套拒绝 |
| D-S06-12 Unnest 的 plan 形状 | Unnest occurrence 是一个 `ProjectSQLDefinition`（exports 是元素端口，没有 select block 与 input use，results 不为它建 VALUES 体），JOIN 的右输入以它为 producer；`ProjectSQLUnnest` 是挂在 JOIN 上的旁挂事实；所有由 occurrence 位置构成的坐标键都含 `unnest_position` |

## Plan 记录契约（供 S08、S09、S13 读取）

- `ProjectSQLPlan.collects` 与 `ProjectSQLPlan.unnests`（JOIN 顺序）；RefKind 与 OriginRole 各加 `COLLECT`、`UNNEST`；
  helper 在 `src/pietto/_project/project_sql_plan_nested.py`。记录都是 frozen、slots、kw-only、`eq=False`。
- COLLECTION 需求族：每个 Collect 有 `COLLECT`（每个父行的完整 bag）、`COLLECT_ORDER`（producer 的 ORDER 键序，不加
  tie-breaker）与 `COLLECT_EXPORT`（容器 nullability 与子字段），每个 Unnest 有 `UNNEST_ROWS` 与 `UNNEST_SOURCE`；嵌套族的
  origins 与 demands 位于 values 族与 literals 族之间，平面程序贡献 0 条。
- Unnest 的独立结构核对 U1–U6（`project_sql_plan_verification.py` 的 `_unnest_structure`）：
  - U1：Unnest JOIN 与 Unnest occurrence 一一对应。
  - U2：`collect` 对应的 COLLECT 的 `fact is semantic.collect_read`，独立核对，不依赖 helper。
  - U3：`outputs` 与 `semantic.nested_type.element_fields` 同序同证据。
  - U4：LEFT 时每个元素字段都 NULLABLE，`nulling` 含本 JOIN；CROSS/INNER 时保留子字段的 nullability，但 INNER JOIN
    自己的 `on` 证明不为 NULL 的可空元素字段收窄为 NON_NULL（`resolved_join_field_nullability`，与 IR builder 及任何
    JOIN 输入同一规则；S06U-COMPAT-R2-1 的 r3 修复）。本条取代 Gate 1 记录中只写“CROSS/INNER 时保留子字段的
    nullability”的原文（S06U-COMPAT-R3-1）。
  - U5：definition 的 phase-62 性质为 BAG，无唯一键、无 FD、无上界；JOIN 输出不新增键或顺序。
  - U6：一个 body 至多一个 Unnest（`PIE-S2807` 保证），否则报结构错误。
- plan 验证从 IR 与语义权威独立重算，不调用 builder；QB-IR 验证器认识 Collect 读边，与 S04 的 D-S04-3 一致地把
  嵌套字段排除在值类之外。

## 平面程序不变（硬约束）

COLLECT/UNNEST 用自己的计数器，平面程序每个既有 kind 的位置不变；平面 plan、公开 `pietto.sql-emission.v1` 字节、
Phase65 plan 观察字节、v1 合同与其他私有文档都不变（新增的空 `collects`/`unnests` 字段之外）。Gate 2 用 plan 测试语料
与平面程序在 PostgreSQL 和 MySQL 上实测：plan 坐标、Phase65 观察哈希与 sql-emission.v1 JSON 和 text 字节相同。集合列
复制输入的 `resolved_type`（`dataclasses.replace`），使按身份去重的 Phase65 编码器写出与 main 相同的记录（S06U-COMPAT-1）。

## 文档与诊断

- `docs/spec/diagnostics.md`：`PIE-S2802` 行改为退休行；仍有效的句子按含义迁入 `PIE-S2803` 与 `PIE-S2807` 行；
  `PIE-B1003` 行加 `collect_not_admitted_on_target` 与 `unnest_not_admitted_on_target`；`PIE-S2370` 与 `PIE-S2807`
  行删去“所以没有 `PIE-S2802`”的说法。
- `docs/language.md`：项目检查 Collect 读与 Unnest let，`emit-sql --project` 在所选目标准入其 lowering 之前报
  `PIE-B1003`。
- `docs/release-notes.md`：Collect 与 Unnest 条目改写为“项目检查通过、`emit-sql --project` 报 `PIE-B1003`”；
  “Unreleased changes following 0.1.6” 节新增一条，说明 `0.1.6` 报的 `PIE-S2802` 已退休（`0.1.6` 节的 B1 条目不改）。

## 不交付与 owner

| 内容 | owner |
| --- | --- |
| Collect 的 PostgreSQL 发射（替换 PG 上的 `PIE-B1003`）、发射观察、compiled 前的显式拒绝 | S08 |
| compiled 中的 COLLECT 与 COLLECTION 事实 | S09 |
| Unnest 的发射与 compiled | S13 |
| ResultContract 的嵌套分支 | S07 |
| 嵌套字段透传（端口血缘中的投影接续） | S16 |
| `emit-sql --project` JSON 中嵌套列的公开形状 | S08 Gate 1 的所有者问题 |
| 读嵌套父关系的平面读者现在被 `PIE-B1003` 拒绝，是否让它们可发射 | S08 Gate 1 |
| 嵌套值的 equality、分组、排序 | Phase72 |

## 集成、检查与交接

- S06-C 开发树 `7bbf5278`（基线 `770be124`）接入 B2 阶段树 `d931d3f7`；集成时修复 QB-IR 验证器与 S04 定稿的
  值类规则不一致（新增 `_nested_positions`），补齐测试类型收窄，并按 D-S06-1 删去 S04/S05 测试中 Collect 的
  `PIE-S2802` 期望（评审 r0 无可复现缺陷）。
- S06-U 在 `wf19-continue` 中完成三轮修复，阶段树 `8ba91793`：r2 修 S06U-PLAN-R1-1（Timestamp/UUID 端口加 CROSS JOIN
  时嵌套拒绝被 scalar-meaning 的提前返回吞掉）与集合列重建导致的 Phase65 平面漂移；r3 修 S06U-COMPAT-R2-1（U4 的
  验证器规则与 IR builder 不一致，使正确的 INNER Unnest plan 被拒为 INPUT_REJECTED）。r3 评审无可复现缺陷；
  记录缺口 S06U-COMPAT-R3-1 由上文的 U4 条闭合。
- 之后阶段 delta 22553b74..8ba91793 以 `git apply --3way` 接到 MySQL parity 树上的 S05 树，并把 B1 发布说明条目中的
  `PIE-S2802` 说法改为已退休，得到 `e1ec73f2`。
- `0.1.6` 发行后，本提交把同一 delta（`a8106928..e1ec73f2`）以 `git apply --3way` 重放到发行提交上的 S05 树；代码全部
  干净应用。冲突与处理：`PIE-B1003` 行取 main 的文字（含 `order` 的位置与 plan 阶段拒绝的位置），再加入
  `collect_not_admitted_on_target` 与 `unnest_not_admitted_on_target`；B1 条目已在发布说明的 `0.1.6` 节，不再改写，
  改在 “Unreleased changes following 0.1.6” 节加一条“`PIE-S2802` 已退休”；测试期望在删去 `PIE-S2802` 之后按项目模式
  的规则重算：没有 `PIE-S2802` 之后，关系内没有其他错误的 Collect 关系重新报无原因的 `PIE-S2333`（`output-name-key`、
  `producer-not-completed`），失败关系的读者、失败输入或更早失败 JOIN 之后的 JOIN 仍不报跟随诊断，LEGACY_FLAT 的临时
  准入文字不出现；main 新增的“块体中的 Unnest JOIN 不是未知关系”测试按 S05/S06 改为在语义之前的 `PIE-S2806`、
  `PIE-S2807` 与一个合法程序（原程序读 `parent.id`，而 `parent` 只输出嵌套字段）。
- 测试 owner：`tests/test_plan_nested_relations.py`、`tests/test_ir_nested_relations.py`、`tests/test_sql_nested_relations.py`
  （新，`ci_workload("general-runtime")`）；扁平 helper `tests/_pietto_plan_nested.py`；`tests/test_project_nested_relation_facts.py`、
  `tests/test_project_nested_relation_unnest.py`、`tests/test_project_let_relations.py`（减法更新）；`tests/test_plan_source_maps.py`、
  `tests/test_plan_demands.py`。
- focused 检查（Python 3.13.13，`PYTHONPATH=src`，`-p no:cacheprovider -n 4`）：上述 owner、`test_plan_*`、`test_ir_*`、
  `test_sql_relation_*`、`test_sql_join_lateral`、`test_harness_plan_*`、`test_repo_docs_examples` 与 golden 检查。
- 交接：S07 用 `collect_of` 取 `NestedShape.collect`，用 helper 取 order 与 limit；S08 按本节契约实现 Collect 发射。
