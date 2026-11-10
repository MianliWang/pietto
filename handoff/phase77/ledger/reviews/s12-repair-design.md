# S12 repair design — MySQL `lpad` rendered occurrences (R1/R2) + R3

日期：2026-11-10。对象：`candidates/s12`（base `f8ccd2c4`，未提交 S12 diff）。
本文件只给设计，没有修改任何 source/test。权威输入：`reviews/s12.md`（BLOCKED，
R1/R2）与 `scalar-report.md` S12 节。

证据（只读诊断，均在 candidate 或 `git archive f8ccd2c4` 导出的 base 树上运行，
`nice -n 10`，无 pytest、无 DB、无网络）：

| log | 内容 |
| --- | --- |
| `candidates/logs/s12-repair-design-1.log` | 首轮：let/literal/def/inline 形状在两族的 status/SQL/uses |
| `candidates/logs/s12-repair-design-2.log` | candidate as-is：两源 labelled witness，含 inline、`starts_with`、header 变体 |
| `candidates/logs/s12-repair-design-3.log` | candidate + walker 去掉 family 重复（模拟推荐方案） |
| `candidates/logs/s12-repair-design-4.log` | base `f8ccd2c4`，同 2 的输入 |
| `candidates/logs/s12-repair-design-5.log` | 单源 bind-safe witness 可行性 + MySQL pure boundary 拒绝细节 |
| `candidates/logs/s12-repair-design-6.log` / `-7.log` | 最终 witness 源在 candidate / base 上的完整事实 |

每个 log 都有同名 `.exit`（全部为 `0`）。诊断脚本在 scratchpad，未进入 clone。

## 0. 结论

推荐 **方案 P（沿用既有 precedent，fail closed）**：

1. 删掉 candidate 在 walker 层加的 family 重复（`rows._tree_nodes` /
   `rows._value_nodes` 的 `family` 参数与 lpad `(0, 1, 0, 0, 1, 2)` 重排，以及
   `ast.realize_rows` / `spliced_value_nodes` / `row_parameter_leaves` 的 family
   传递），回到 base 的唯一 authored-node walker。
2. canonical occurrence authority 定义为：**一个 realized native leaf ↔ 恰好一个
   `NativeUse` ↔ 恰好一个渲染出的 parameter token**。renderer 多次访问同一
   operand 时，若该 operand 子树含 native leaf，则 token 数多于 leaf/use，由
   独立的 normal verifier 与 pure boundary 拒绝（`PIE-B1008
   fixed_value_or_parameter_correspondence`）。这正是 PostgreSQL `lpad`、
   PostgreSQL `round(Float)`、以及两族 `starts_with`/`ends_with` 现有的机制。
3. MySQL `lpad` 的 admission 边界因此与 PostgreSQL `lpad` 完全一致；PG 输出
   byte-identical（已对 base 实测）。
4. 另修一个设计调查中新发现、阻挡 witness 的 candidate 缺陷 **R3**：MySQL pure
   boundary 拒绝首参为 Text literal 的 `lpad`（`lpad realization`）。
5. 修正 docs/release-note 中 "preserves every repeated occurrence" 的不实表述。

方案 P 下 R1 不再存在（没有任何 VERIFIED artifact 含"同一 leaf 的重复 marker"，
因此不需要也不允许第二条 use），R2 不再存在（所有 consumer 共用一个 walker，
渲染重复由独立的 token 流核对）。"每个实际渲染的 MySQL marker 有自己的 ordered
leaf/use" 对所有 admitted artifact 成立，且被独立验证。

若 owner 坚持 MySQL 承认"重复位置内含 native marker"（R1 字面要求的成功
witness），那是 MySQL 领先 PG 的产品语义扩展，见 §11 方案 O，分类
`USER_DECISION_REQUIRED`。

## 1. 事实：PostgreSQL 如何处理被渲染多次的 bound operand

- 构造：PG `lpad` 渲染 `(CASE WHEN length(s) >= w THEN s ELSE lpad(s, CAST(w AS
  pg_catalog.int4), fill) END)`，`s`/`w` 分别渲染 3/2 次；PG `round(Float)` 单参渲染
  5 次（`project_sql_emission_rendering.py` round 分支）。
- AST：`build_row_value` 每个 authored operand 只建一个 value；`build_value` 从
  `uses[original.ref]` 取一条 `NativeUse` 冻结在一个 `SQLParameter` 上。renderer 每次
  访问都 emit `"$" + str(leaf.use.server_index)`（同一 `$k`），subject 都是
  `leaf.site.ref`。
- walker：`rows.rendered_value_nodes` / `rendered_tree_nodes` 只对 conditional 重排
  （`rendered_operand_order`），对 lpad/round/starts_with 不重复；
  `row_parameter_leaves` 每个 leaf 一次。
- verifier：`verify_row_parameters` 要求 `len(parameter_uses) == len(leaves) ==
  len(parameter tokens)`，逐位置 `use is leaf.use`、`use.ordinal == ordinal`、
  `token.subject is leaf.site.ref`。重复渲染使 token 多于 leaf → 失败 →
  `verify_project_sql_emission` issue `fixed_value_or_parameter_correspondence` →
  `_realize_row_query` 返回 BLOCKED `PIE-B1008`。
- 实测（base `f8ccd2c4`，log 4）：PG `lpad` 的 width 或 text 位置含 capturing-let
  scalar read（其 WHERE 有 bind-safe `"x"`/`7`，或 header 参数 `lo`）→ BLOCKED
  `[("PIE-B1008", "fixed_value_or_parameter_correspondence")]`。candidate 上 PG 完全
  相同（log 2 vs 4 中 PG 段无 diff）。

结论：PG 的处理是"同一 leaf 重复 emit `$k`，由 verifier 的 token 计数律 fail
closed"。要求的 "保持 PG byte-identical" 即保持这一行为。

## 2. 事实：MySQL 已承认的重复渲染构造（precedent）

- `starts_with`/`ends_with`：两族都渲染 `(LEFT(a, CHAR_LENGTH(b) ) = b)` /
  `(left(a, length(b) ) = b)`，第二参 `b` 渲染两次；base 起即为 MySQL admitted。
- 机制（三层，全部是既有的）：
  1. semantic：header 参数只在 `starts_with`/`ends_with` 的**第一**参可用（`docs/spec/diagnostics.md`
     PIE-S2355 行："starts_with/ends_with (first argument)"），其它 call argument 都是
     PIE-S2355（lpad 全部参数亦然，包括读 header 的 `let`）。
  2. literal policy：`project_sql_plan_literals.classify` 对任何祖先含 `CallExpr` 的
     literal 返回 `CALL_ARGUMENT`，因此 bind-safe literal 永不进入 call argument 子树
     （`def` 内联同理，log 1 `def_width` 两族 0 个 marker）。
  3. 唯一可达路径：capturing let（inline body）经 scalar/exists/IN read 放在重复位置；
     其 body 中的 bind-safe literal 或 header 参数随 read 被重复渲染 → verifier token
     计数律 → BLOCKED `PIE-B1008`。
- 实测：`starts_with(lhs.label, scalar matched.label)` 在 base 与 candidate 的 MySQL、
  PG 均 BLOCKED `PIE-B1008 fixed_value_or_parameter_correspondence`；对照
  `starts_with(scalar matched.label, lhs.label)`（不重复的位置）两族 VERIFIED，
  uses `[(0, 1), (1, 2)]`，`native_arguments == ("x", 7)`（log 2/4）。

结论：MySQL 存在 precedent，且与 PG 机制相同。按 task 要求复用它。

## 3. 可达性：什么能落进 lpad 的重复 `s`/`w`

| 输入形状 | bind-safe 结果（两族） |
| --- | --- |
| `lpad(chosen, width, "雪")`，`chosen`/`width` 为含 bind-safe literal 的 `let` | VERIFIED；marker 在 let 的 CTE 中各渲染一次，lpad 内只重复 stage reference |
| `lpad("ab", 5 if x > 0 else 3, "雪")`（literal 直接作 call argument） | VERIFIED；0 marker（`CALL_ARGUMENT`） |
| `lpad(label, band(id), "雪")`（def 内联条件） | VERIFIED；0 marker |
| header 参数直接或经 `let` 进入 lpad | PIE-S2355（保持，不放宽） |
| width 条件里 `scalar matched.id`，`matched` 为 capturing let，WHERE 含 `"x"`、`7` | BLOCKED PIE-B1008（PG base 同） |
| `lpad(scalar matched.label, 4, "雪")` | BLOCKED PIE-B1008（PG base 同） |
| 同上但 WHERE 读 header `lo`（不触发 PIE-S2355） | BLOCKED PIE-B1008（PG base 同） |

因此 R1 所说"重复位置上的可绑定 Text/Int"只有两类：经 `let` 的 stage reference
（marker 不重复，正常 VERIFIED），和经 capturing-let read 的 inline body（marker
重复，两族 fail closed）。

## 4. candidate walker 修改的实际效果

- log 2（as-is）与 log 3（walker 去掉 family 重复）**逐字节相同**：所有 direct 形状
  结果一致，所有 inline 形状都 BLOCKED `PIE-B1008`。
- as-is 下 MySQL inline 的失败路径是：`collect` 按重复后的 `rendered` 为 inline body
  的 literal 分配 2–3 条 use，`build_value` 只取第一条，`parameter_uses` 由
  `tuple(leaf.use for leaf in row_parameter_leaves(query))`（family-aware，重复同一
  leaf）得到 `(u0, u1, u0, u1)`，ordinal 不连续 → verifier 拒绝。去掉重复后：分配 1 条，
  leaf 1 个，token 2–3 个 → verifier 拒绝。结果相同，但前者留下无 leaf 的残留 use，
  且使 `value_requirements` / `node_expectations`（"one requirement per actual node"）
  与 `row_parameter_leaves` 采用两种不同的 order 概念（R2 的根）。
- 结论：candidate 的 family walker 修改对可达输入是惰性的，对 canonicality 是有害的。
  按 "prefer deletion" 删除。

## 5. 设计（方案 P）：canonical rendered-occurrence authority

### 5.1 定义（唯一）

`ast.row_parameter_leaves(query)`（base 实现：`spliced_value_nodes((value,))`，
family-free，authored node 顺序 + conditional 渲染重排 + inline body 拼接）是 native
leaf 序列的唯一定义。不变量：

> 每个 VERIFIED row/join artifact 中，`row_parameter_leaves(query)[i].use is
> artifact.parameter_uses[i]`，且第 i 个 `parameter` rendering event 的 subject 是
> 该 leaf 的 site（或 parameter read 的 original ref）。因此每个渲染出的 marker
> 恰有一个自己的 ordered leaf/use；一个 leaf 被渲染多次的 artifact 不存在
> （fail closed）。

MySQL 与 PostgreSQL 共用此定义；族差异只在 `allocate_uses` 的 server index（MySQL
`ordinal + 1`，PG 按 owner 复用）——这是既有逻辑，不变。

### 5.2 builder 路径（全部回到 base 代码）

- `realize_rows.collect`：`rows.rendered_constant_chains(plan, reference)` +
  `rows.rendered_tree_nodes(plan, reference)`（无 family），inline read 处递归收集
  inline body roots 一次 / 每个 read 节点出现一次；`allocate_uses(family, ...)`；
  `occurrence_uses`。
- `build_row_value` / `parameters.build_value`：每个 realized leaf `take_use` 一次。
  不需要 "per rendered marker 的 SQLParameter"：admitted artifact 中 leaf 与 marker
  一一对应；重复渲染的 leaf 由 §5.4 拒绝。
- `rendered_constant_chains` 保持无 family（R2 第 1 点因 walker 不再有 family 而消失；
  bind-safe literal 不可能出现在 call argument 子树，见 §2）。

### 5.3 各 consumer 如何从同一 authority 派生（全部不改代码）

| consumer | 派生方式 |
| --- | --- |
| renderer（row/join） | 每次访问 emit 一个 token；MySQL `?`，PG `$server_index`；不读 walker |
| `artifact.parameter_uses` | `project_sql_emission.py:260` `tuple(leaf.use for leaf in row_parameter_leaves(query))`；guard 版本 `project_guard_preparation.py:237` 同式 |
| `native_arguments()` | `project_execution_binding_verification.py:196` 逐 `parameter_uses`：MySQL 每 use 一个参数，PG 每 owner 一个 |
| compiled rebuild/load/re-emit | `emit_compiled` 在 compiled plan 上重跑同一 `realize_rows`；`project_compiled_verification.py:6207` 核对 `row_parameter_leaves` 与 `plan.parameter_uses` 及 `used_parameters` |
| normal verifier | `verify_row_parameters`（leaf/use/token 三者等长逐位对应）、`verify_row_bytes`（独立重算全部字节与事件，lpad 用其自身的 positions 表） |
| public canonical decoder / pure boundary | `portable.export_emission_observation` → `pure.parse_emission_observation`：`_Check` 要求 `claimed == {use: 1}`，`_Tokens` 要求 `len(parameter events) == len(uses)` 且每个 token 的 `sql_parameter.use` 依序等于 use；`portable.verify_emission_observation` 再核对 public JSON `parameter_uses` |
| live template | `bind_values` → `_specialize` / `emit_compiled` 重派生；`verify_binding` 逐 use 比较 ordinal/server_index/physical 与 `native_arguments`；header 模板的 `_discharged` 两侧都用无 family 的 `spliced_value_nodes`，配对一致 |
| requirement inventory | `value_requirements` 与独立的 `node_expectations` 都是 "one requirement per actual node"，无 family；MySQL 与 PG 同形（若按渲染重复会把 lpad 内的 stage reference 计 3 次，改变 MySQL public `requirements`） |
| binding obligations | `row_binding_obligations` 每个 operation 一次；lpad 的重复序列 `(0,1,0,0,1,2)` 的首现顺序就是 `(0,1,2)`，按对象去重后与 authored 顺序相同，无 family 即正确 |

### 5.4 独立 verifier 如何复核（不与 builder 共享盲点）

builder 的 walker 看不见渲染重复，这是有意的。verifier 不靠 walker 发现重复，而是
把 walker 的 leaf 序列与**从实际字节/事件独立得到的 token 流**逐位对比：

1. `verify_row_bytes` 不调用 renderer，按自己的 lpad/round/starts_with 文本与 positions
   表重算每个事件和字节，证明事件流就是字节流；
2. `verify_row_parameters` 以该事件流中的 `parameter` token 对比 `row_parameter_leaves`
   与 `parameter_uses`：任何 leaf 被渲染两次都使 token 数多于 leaf 数；
3. pure boundary 从 canonical observation bytes 独立重建 token 序列并要求每个 use
   被恰好一个 `sql_parameter` claim、每个 token 依序对应。

三者都由"实际渲染"驱动，因此 builder 与 verifier 不可能在"重复渲染"上同错。

### 5.5 源码变更清单（实现时）

| 文件 | 动作 |
| --- | --- |
| `src/pietto/_project/project_sql_emission_rows.py` | `rendered_tree_nodes`、`_tree_nodes`、`rendered_value_nodes`、`_value_nodes` 恢复 base（删 `family` 参数与 MySQL lpad 重排）；`rendered_constant_chains` 不变 |
| `src/pietto/_project/project_sql_emission_ast.py` | `realize_rows` 两处 `rendered_tree_nodes(..., family)`、`spliced_value_nodes(values, family=None)` 及其递归、`row_parameter_leaves` 的 `query.request.family` 恢复 base；该文件对 base 的净 diff 为零 |
| `src/pietto/_project/project_sql_emission_pure_boundary.py` | lpad `_Check`：PG 分支恢复 base 原文（`_is_pg_text_value(doc, operands[0])` 与 `_is_pg_text_input(result)`）；MySQL 分支见 §6 |
| `docs/language.md`、`docs/release-notes.d/77-s12-mysql-scalar-text-date.md` | 见 §7 |
| `project_sql_emission_rendering.py`、`project_sql_emission_verification.py` 等 | 只做 §8 的机械 format 修复；lpad/add_months/now/concat 的 MySQL 渲染与字节重算保留 |

不新增抽象、不新增 dataclass、不改 `SQLParameter`/`NativeUse`/observation schema/
compiled wire shape/public JSON。

## 6. R3（新发现）：MySQL pure boundary 拒绝 literal Text 首参的 `lpad`

- 复现（log 5/6）：单源 bind-safe `fixed = lpad("ab", width, "雪")` 在 MySQL 上
  VERIFIED、normal verifier 通过、compiled/template 通过，但
  `pure.parse_emission_observation(...)` → `INVALID_RELATION`，`detail ==
  "lpad realization"`，`verify_emission_observation(...).corresponds is False`。
  首参为 source field 或 stage reference 时 OK；PG 全部 OK。
- 根因：candidate 把 lpad 检查改为 `_is_key_value(_value_realization(doc,
  operands[0]), family)`。`_value_realization` 对 anchor 只有 PG Text/Bool/Float 与
  signed Int 的像，没有 `my_utf8mb4_text` anchor 的像 → 返回 `None` → MySQL 拒绝。
  base 的 PG 谓词 `_is_pg_text_value` 带 anchor 回退，candidate 丢了它。
- 修复（最小、lpad 局部）：
  - PG：逐字恢复 base 谓词（不碰任何 PG 验证语义）。
  - MySQL：首参接受 `_is_key_value(_value_realization(doc, operands[0]), "mysql")`
    **或** anchored MySQL Text literal/parameter（anchor `tag == "Text"`、
    `physical_type == "my_utf8mb4_text"`、fixed value tag `Text`，镜像
    `_is_pg_text_value` 的 anchor 分支）；结果 `_is_key_value(result, "mysql")` 保持。
  - 不扩展 `_value_realization` 的 MySQL Text anchor 像：那会改变其它 MySQL 检查的
    observation 接受面（不在本修复授权内）。记为后续观察项。

## 7. 文档与 release note

- `docs/language.md` lpad 段（candidate 新句 "including every repeated `s` and `width`
  occurrence"）改为与 PG 同边界的表述，例如："MySQL project SQL has the same
  non-truncating candidate shape and the same refusals as PostgreSQL project SQL;
  native qualification remains pending."
- release-note fragment 删去 "The candidate preserves every repeated `lpad` argument
  occurrence in native placeholder order."，可改为 "MySQL `lpad` admits exactly what
  PostgreSQL project `lpad` admits."
- 表格行保持 candidate 文本（"candidate emitted for the same proven width; native
  qualification pending"）即可。

## 8. 机械项（`DERIVED_MECHANICAL`）

- `project_sql_emission_rendering.py` 约 715 行：注释被拼到 `if name in {"lpad",
  "add_months"}:` 行尾；拆回独立注释行。
- `project_sql_emission_verification.py` 约 7428–7437 行：PG/MySQL spelling dict 中
  `"coalesce"`、`"concat"` 缩进错位。
- 超长行（rendering `now` 三元式、verification `now`、pure `add_months` `date`
  tuple、rows `now`/`add_months`）：交给 `ruff format`。
- `tests/test_sql_project_scalar_expressions.py`：
  `test_mysql_s12_conditional_text_is_replayed_and_conditional_date_stays_refused`
  去掉 slice 名（如 `test_mysql_conditional_text_and_width_feed_lpad_and_conditional_date_stays_refused`），
  docstring 去掉 "preserve each repeated SQL occurrence"；函数内 import 上移到模块头。
- `tests/test_execution_compiled_families.py` `SCALAR_FAMILIES` 上方注释 "MySQL
  project SQL refuses `concat`" 已过时（见 W4）。

## 9. Focused witness tests

全部扩展现有 owner，不新增文件。

**W1 — `tests/test_sql_project_scalar_expressions.py`**
`test_bind_safe_lpad_reads_each_bound_marker_once`，`@pytest.mark.parametrize("target", TARGETS)`，
`emit(tmp_path, target, BODY, policy="bind_safe_literals")`：

```
table result:
    from rows
    let chosen = text if flag else "雪"
    let width = 5 if id > 0 else 3
    select:
        padded = lpad(chosen, width, "雪")
        fixed = lpad("ab", width, "雪")
```

断言（数值均已在 log 6/7 实测）：

- 两族 `VERIFIED`；`artifact.rendered.sql` 等于固定字符串：PG 为 log 7 base 的字节
  （与 candidate log 6 相同，即 PG byte-identity witness），MySQL 为 log 6 字节。
- MySQL：`sql.count("?") == 4`；最后一个 ` SELECT CASE WHEN CHAR_LENGTH(` 之后 `?` 数为 0
  （两个 lpad 内没有 marker）；PG：`$1..$4` 各出现一次。
- `[(u.ordinal, u.server_index, u.physical_type, slot index) for u in parameter_uses]`：
  MySQL `[(0, 1, "my_utf8mb4_text", 0), (1, 2, "my_signed_int", 2), (2, 3, "my_signed_int", 1), (3, 4, "my_signed_int", 3)]`；
  PG `[(0, 1, "pg_text", 0), (1, 2, "pg_int8", 2), (2, 3, "pg_int8", 1), (3, 4, "pg_int8", 3)]`。
- `fixed_values` 值 `("雪", 5, 0, 3)`（slot 顺序）；`native_arguments(artifact, values) ==
  ("雪", 0, 5, 3)`（渲染顺序）。
- `len(parameter events) == len(parameter_uses) == len(ast.row_parameter_leaves(artifact.ast)) == 4`，
  且逐位 `use is leaf.use`、event subject 是 leaf site。
- `verify_project_sql_emission(...).verified`。
- `export_emission_observation` OK；`pure.parse_emission_observation(...).status is
  pure.Status.OK`；`verify_emission_observation(...).corresponds`（MySQL 在修 R3 前失败，
  是 R3 的回归 witness）。
- compiled：`build_compiled` → `load_compiled` → `emit_compiled(loaded, values)` 的 SQL 字节
  相等，`[(ordinal, server_index, physical_type)]` 相等。
- live template：`prepare_live_template` slot tags `["Text", "Int", "Int", "Int"]`；
  `bind_values` 同值 → `arguments == ("雪", 0, 5, 3)`；换值 `("雪雪", 6, 1, 4)` →
  `arguments == ("雪雪", 1, 6, 4)` 且 SQL 字节不变。

**W2 — 同一 owner**
`test_a_native_marker_in_a_repeated_call_operand_fails_closed_as_on_postgres`，
`parametrize(target × case)`，用 `probe.labelled_join_witness(target, body,
policy="bind_safe_literals")` + `probe.build_case`。capturing let：

```
    let matched:
        capture lhs
        from rhs
        where rhs.id == lhs.id and rhs.label == "x" and rhs.id > 7
        select:
            id
            label
```

- 拒绝 case：`lpad(lhs.label, 5 if (scalar matched.id) == 1 else 3, "雪")`、
  `lpad(scalar matched.label, 4, "雪")`、`starts_with(lhs.label, scalar matched.label)`（precedent）、
  header 变体 `query result(lo: Int):`，WHERE 用 `rhs.id > lo`，lpad width 同第一例。
  断言两族 `BLOCKED`、`artifact is None`、
  `probe.decode_public(serialize_project_sql_emission(outcome))` 的
  `(code, subject.detail)` 为 `[("PIE-B1008", "fixed_value_or_parameter_correspondence")]`、
  `diagnostics == []`（两族、base 均实测）。
- 对照 case：`starts_with(scalar matched.label, lhs.label)`、`len(scalar matched.label)`：
  两族 `VERIFIED`，uses `[(0, 1), (1, 2)]`，`native_arguments == ("x", 7)`，observation
  OK/corresponds，compiled SQL 相等，template 换值 `("x雪", 8)`。不要对这两个
  VERIFIED 两源文档调用 `probe.decode_public`（base 起即 `invalid public artifact`）。

**W3 — `tests/test_execution_compiled_bundle.py`**
`test_lpad_and_add_months_templates_render_the_emitted_sql` 参数化到
`("postgres", "mysql")`：MySQL 的 `form` 为 `b"CASE WHEN CHAR_LENGTH("` 与
`b"DATE_ADD("`；compiled template 与 live template 的 `bound.arguments == values`、SQL 相等
（lpad 在 WHERE header 参数旁，不在 lpad 内）。

**W4 — `tests/test_execution_compiled_families.py`**
`SCALAR_FAMILIES["concat"]` 增加 `"mysql": "CONCAT("`，更新过时注释：MySQL concat 的
compiled replay 与 live template 绑定 WHERE literal。

未纳入：`probe.decode_public` 作为 lpad 成功 oracle。它在 base 起对 PG lpad 就报
`closed scalar call spelling`（log 2/4），扩展 test decoder 是独立的 harness 变更。本
设计以 pure boundary + `verify_emission_observation`（交叉核对 public JSON
`parameter_uses`）作为 "public canonical decoder/pure boundary" 的成功 witness。

## 10. Focused 验证计划（实现阶段）

每次只跑一个 pytest，`nice -n 10`、`-p no:cacheprovider`、无 `-n`，tee 到
`candidates/logs/s12-repair-<stage>-<n>.log` 与 `.exit`：

1. `tests/test_sql_project_scalar_expressions.py`（整个 owner）；
2. `tests/test_sql_relation_scalar.py tests/test_sql_relation_exists.py
   tests/test_sql_relation_membership.py tests/test_sql_join_lateral.py
   tests/test_sql_query_parameters.py`（walker 回退触及的 inline/参数 inventory owner；
   回退后代码与 base 相同）；
3. `tests/test_execution_compiled_bundle.py -k lpad`、`tests/test_execution_compiled_families.py
   -k scalar_families`、`tests/test_execution_binding.py`。

再加 touched files 的 `ruff check`、`ruff format --check` 和 `git diff --check`。PG
byte-identity 已有 base 证据（log 4/7）；若源码在 PG 路径上与本设计不同，按 log 7 的
做法在 base 导出树上重跑 W1/W2 源。

## 11. 被拒绝的替代：方案 O（让 MySQL 承认重复 marker）

R1 字面要求"每个重复 MySQL marker 有自己的 leaf/use 并成功"。唯一可达的重复 marker
来自 capturing-let inline body（§3），其代价：

- inline body 由 `_inline_target` 在 `realize_stages` 中每个 block_use 只 realize
  **一次**（single-read 不变量），`SQLBlockRead.target.producer` 共享同一 body。
  即使 `_scalar_call` 按 `(0, 1, 0, 0, 1, 2)` 为 MySQL lpad 建 6 个 operand value，
  inline body 中的 `SQLParameter` 仍是同一组对象。
- 两条出路都很重：(a) 每个渲染出现 realize 一次 inline let（破坏 single-read，
  `readable[block_use.ref]` 改为多 target）；(b) 把 leaf→use 改为 leaf→有序 uses，
  牵动 renderer、`verify_row_parameters`/`verify_parameters`、compiled
  `EMISSION_PARAMETER*`、guard preparation、portable observation schema
  （`sql_parameter.use`）、pure boundary（`claimed == {use: 1}`、`self.one(parameters, site)`）、
  binding verification。
- 还会让 MySQL `lpad` 领先 PG `lpad`（PG 必须保持 BLOCKED），并与 MySQL 自身的
  `starts_with`/`ends_with` 规则分裂；违背 "MySQL lags PG; PG scouts" 的 owner 方针。

分类：`USER_DECISION_REQUIRED`（公开语义与跨目标一致性）。不在本修复内执行。

## 12. 风险

1. 方案 P 不满足 R1 的字面成功 witness；"成功"只对 marker 不重复的形状成立，重复
   marker 形状以 PIE-B1008 fail closed。需由 owner/reviewer 接受 §2 precedent 为依据。
2. 拒绝以 `PIE-B1008 fixed_value_or_parameter_correspondence`（内部对应性 detail）
   呈现，而非 PIE-B1003 规则 refusal；这是 PG 与 MySQL `starts_with` 的既有行为。改成
   显式 builder refusal 会改变 PG public blockers，需另行授权（可记入 roadmap）。
3. R3 是 R1/R2 之外的新缺陷；不修则 W1 的 MySQL pure/public 断言失败。修复必须保持
   PG 谓词逐字不变。
4. `probe.decode_public` 不能解码任何 lpad 文档（PG 亦然），也不接受两源 VERIFIED
   capturing-let 文档；witness 不依赖它做成功 oracle。
5. 两源 labelled witness + let 链在 compiled export 上 `COMPILED_EXPORT_SOURCE_BINDING`
   （PG base 同，log 2/4）；W1 用单源 fixture 规避，属既有限制。
6. candidate 的 format 损伤会让 `ruff format --check` 失败，需机械修复。
7. MySQL native qualification（DB campaign）仍待做；本设计不作任何 DB 结论。
