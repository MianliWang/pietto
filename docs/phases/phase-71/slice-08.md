# Phase71 Slice08：PostgreSQL 的 Collect source emission

状态：candidate（批次 B3）。P-core（节点、渲染、纯检查）与 P-wire（接线、准入、需求、公开文档、compiled 前拒绝）
都在本片；按 D71.11 在本机 Docker 上跑完整 PostgreSQL 目标清单（含 Collect 新变体与 `array` cell）移交 S12，见 §6。
决定来源：S08 Gate 1 记录（ARCHITECTURE_DECISION，D-S08-1..13；workflow `wf_f037202f-d24` 的 `s08-gate1`）与所有者
2026-10-30 对 Q1 的回答 (a)（`owner-answer-20261030-s08-q1.json`）：在现有 emit-sql v1/v2 格式内加性扩展。
本片建立在 B2（[S04](slice-04.md)–[S07](slice-07.md)）之上；批次 B3 建立在 main 的 `81f0d3b5`（`0.1.6`、B2 与 `0.1.6` 审计的项目模式小修）之上，不属于 `0.1.6`，其发布规则见[路线](slices.md)，发布之前本片是 candidate。

## 1. SQL 形状

每个 Collect 读是父关系投影体 FROM 之后的一个 `LEFT JOIN LATERAL` 单行聚合（D-S08-1）：

```sql
SELECT ..., "g<n>"."n" AS "<field>", "g<n>"."a0" AS "<child0>", ...
FROM <scan> AS "sP"
LEFT JOIN LATERAL (
  SELECT COUNT(*) AS "n", ARRAY_AGG("e<n>"."c0" ORDER BY "e<n>"."c<V>") AS "a0", ...
  FROM <被收集 let 的终端> AS "e<n>") AS "g<n>" ON TRUE
```

| 情形 | 写法 |
| --- | --- |
| closed let | 终端 CTE 在可见列之后多一个私有 ordinal 列 `c<V>` = `ROW_NUMBER() OVER (<终端 ORDER 的各项，不写 NULLS>)`；ordinal 不进 `columns`/`cte_columns`，其他读者字节不变（D-S08-2） |
| captured let | 内联链在 lateral 的 FROM 中，LIMIT 留在相关派生表内，按父行生效 |
| `select distinct` let | 在读的位置加 wrapper `d<n>`，ordinal 写在 wrapper 中，从不进 DISTINCT SELECT |
| 并列 Collect | 每个读一个 lateral，按列序；lateral 只读父行 |
| 父关系有 ORDER BY/LIMIT | 投影 CTE 头展开为 `c<i>`, `c<i>_0`…；结果体把整组带到最终标签 |

空集是 `n = 0`、每个 array 为 NULL；全 NULL 的子行是 `n = 1`。tie 内顺序与 LIMIT 末位成员不承诺（F-4）。

## 2. 准入与拒绝

- D-S08-4：PostgreSQL 准入一个 Collect 读，当且仅当它的父 definition 是本语句的 selected owner
  （`project_sql_emission_nested.collect_admitted`）。读父关系的关系（`from parent`、`exists parent`、`scalar parent.x`、
  在别的模块 import 后读取）仍报 S06 的 `PIE-B1003 collect_not_admitted_on_target`，位置与次序不变，归 S16。
  MySQL 每个 Collect 读都报这一项；与表函数同在时表函数那条在前，不出现
  `mysql_correlated_order_or_limit_read_not_admitted`（F-2）。Unnest 不变（S13）。
- 准入的读不屏蔽语句的平面拒绝：S06 的 `staged_capture` 仍报 `PIE-B1002 arithmetic_outside_physical_range`，Timestamp
  端口加 CROSS JOIN 仍报 `scalar_meaning_requires_field_projection`。
- D-S08-5：captured 被收集 let 的原生 occurrence 在 `realize_rows` 的投影块根中排在投影表达式之后、按列序，与渲染
  次序一致；`row_parameter_leaves` 与 `row_value_roots` 经 `lateral_values` 按同一顺序遍历。不做这一步时，bind-safe
  程序在 emission 中抛异常（负对照已记录）。
- D-S08-6：`emission_blockers` 原有的列数检查改为物理宽度（`physical_width`：嵌套组 1+F 列，被收集终端再加
  ordinal）；平面单元两者相等，字节与诊断不变。lateral 计入节点数，验证器独立重算。
- D-S08-8：`build_compiled` 在 `_Export` 之前（主 plan）与 `_LogicalExport` 之前（保留的 single-match owner）对有
  Collect 的 plan 抛 `CompiledError("NESTED_UNAVAILABLE")`；公开为 `compile_query` 的 `RequestRejected` PIE-R1004，在任何
  连接与 driver import 之前，`execute()` 与 `export_bundle` 因此不可达。F-3 已证实：去掉保留 owner 的判定时，带
  Collect 的保留 owner 在 build 中抛未分类的 `ValueError`（公开为 PIE-R1999）。S09 起主 plan 的判定在模板闸门，
  同一个词；保留 owner 一处为 `COMPILED_RETAINED_COLLECT`（[S09](slice-09.md) §6）。
- D-S08-9：`export_emission_observation` 报 `OUTSIDE_SCHEMA`，`verify_emission_observation` 报 `outside_schema`，
  都在 `_Export` 之前；规则表 R01–R26 不变。
- S07 的读者拒绝不变：`prepare_output` 报 `ResultError("NESTED_UNAVAILABLE")`，output 视图归 S10（D-S08-7）。

## 3. 公开文档（Q1 (a)）

`pietto.sql-emission.v1`（有 header 参数时 v2）的标签不变，平面文档逐字节不变。嵌套字段的 `columns` 条目：

- `logical_type`：`{"kind": "collection", "name": null, "parameters": null, "element": [...]}`，每个 element 是
  `{"ordinal", "label", "logical_type", "nullable"}`，与平面列同义。
- `representation`：`{"carrier": "pg_column_arrays_v1", "columns": [{"role": "count", "sql_symbol"},
  {"role": "field", "child", "storage", "sql_symbol"}…]}`；这里的 `sql_symbol` 是语句结果中的物理列（从 1 起）。
- `correspondence`：`collect`、`use`、`producer`、`children`、`export`、`sql_symbol`（逻辑位置），父关系有结果边界时
  另有 `result_origin`。
- 嵌套文档中每个 `correspondence.sql_symbol`（平面列也是）都是逻辑位置；平面列的语句列等于它加上前面每个嵌套字段的
  F（`element` 个数）。读者按 `representation.columns` 与这一偏移找语句列，不按标签（array 带子字段的标签）。
- 需求：三条原始 `collection` 需求的规则为 R27（D-S08-10）；生成需求 `collect_lateral`（subject 为 Collect 读，带
  naming premise）、`collect_count`、`collect_array`、`collect_ordinal` 的规则都是 R27；lateral 与 DISTINCT wrapper 各带
  一条 `read_only_select_bytes`（R23）。
- range role：`collect_lateral_open/close`、`collect_on_true`、`collect_count`、`collect_array`、
  `collect_array_order`、`collect_scope`、`collect_reference`、`collect_carrier_column`、`ordinal_window`、
  `ordinal_column`、`distinct_wrapper_open/close`。
- text 格式按记录行打印，不另加代码。

规格文字在 [project CLI JSON v2](../../spec/project-cli-json-v2.md#emit-sql-result)；诊断在
[diagnostics](../../spec/diagnostics.md) 的 PIE-B1003、PIE-B1007、PIE-R1004 行；语言说明在
[language](../../language.md#nested-relations-collect-and-unnest)。

## 4. 独立验证

`verify_row_query` 对每个 Collect 认领调用 `_collect_problems`（ORDER 与 LIMIT 取自 plan 的
`collect_order`/`collect_limit`，不取自节点），并核对读者 scope 的终端、列像、符号与 `block_reads`；每个体的
`laterals` 必须恰好是其 Collect 列的 lateral。`_verify_result_body` 核对 ordinal 的有无（被 Collect 读且无 DISTINCT
时才有）与逐项内容，以及整组携带（`_collect_group_problems`）。需求分母与 R27 独立重推。`verify_row_bytes` 的字节
规则来自 P-core。真实 artifact 上的损坏（去掉 lateral、交换 array、去掉 ordinal、把组降为平面列、删去生成需求、改
R27）都使公开序列化报 `PIE-B1008 artifact_correspondence`。

## 5. 测试 owner

| owner | 内容 |
| --- | --- |
| `tests/test_sql_nested_relations.py` | S06 的拒绝测试收窄为仍被拒绝的形状（PG 只余读父关系者，MySQL 全部）；P-core 节点与字节测试；真实正例（S06 形状加 `WIRED` 与跨模块来源，SQL 逐字节）、公开 JSON/text、DISTINCT wrapper、F-2、参数次序（bind-safe 与 v2）、物理宽度与节点上限、compile 拒绝、inspection 与 output、真实 artifact 损坏、literal oracle 的 Collect 程序族 |
| `tests/_pietto_sql_nested_collect.py` | 平面替身、`collect_record`、`WIRED`、`contract`、`wired_outcome`、`oracle_contract` |
| `tests/test_execution_compiled_families.py` | `_pietto_execution_binding.proof_artifact(retained="collect")`；S09 把用例改写为保留 owner 的 `COMPILED_RETAINED_COLLECT` |
| `tests/test_harness_sql_emission_portability.py` | 观察的 `OUTSIDE_SCHEMA` |
| `tests/test_harness_nested_oracles.py`、`tests/_pietto_execution_nested_oracle.py` | D-T1：literal oracle 与它的测试随本片落地；IPC oracle 的部分随 S17，flat harness 随 S21 |

## 6. 未交付与交接

- AC-F7 / D-S08-11：`L_relation_collect` 目标变体、收据 v3 的 `array` cell、`docs/development.md` 的 denominator 段，
  以及 D71.11 的本机 Docker PostgreSQL 18.6 运行。本片任务没有 Docker 授权；literal oracle 的 C1–C10 已全部 VERIFIED，
  可直接作为这些变体的独立期望。这些变体的文档要经过测试专用的公开 decoder
  `tests/_pietto_sql_emission.decode_public`（target-conformance cases、差分 harness 与执行探针都调用它），它现在拒绝每个
  嵌套 VERIFIED 文档：不认识 range subject kind `collect`（“range origin roles”），对无 JOIN 的语句要求恰好一个物理
  scan（“one physical scan without a JOIN”），也不认识嵌套列的 `collection`/`pg_column_arrays_v1` 条目与 R27 需求。
  AC-F7 先让它学会这些形状（嵌套列按上面的逻辑位置与偏移读），再加变体；在此之前它对嵌套文档 fail closed。
  lead 2026-10-30 把 AC-F7 整体移交 [S12](slices.md)（第一个公开执行 Collect 的片），记 D71.10 scope 一次。B3 的封存
  不等 AC-F7，而依赖在确切的 candidate wheel 上跑 D71.11 的权威 rows campaign：它在 PostgreSQL 18.6 真库上执行
  Collect 的嵌套形状（S10 加入、S11 扩充），并按独立字面 oracle 核对。
- D-S08-8 的判定已由 [S09](slice-09.md) §6 的模板闸门取代：主 plan 的判定在 `verify_template`，保留同一个 detail，
  保留 owner 一处为 `COMPILED_RETAINED_COLLECT`。
- slice-07.md 的 output 两行与 slice-02.md 的“S08 preflight”按 D-S08-7 改为 S10，由 S10 的提交修订（F-7、F-8）。
- 父关系被读时的发射（S16）、Unnest（S13）、Float/Date/Timestamp/UUID 子 leaf 的原生证据（S14/S15）、公开执行（S12）、
  MySQL（Phase77）。
