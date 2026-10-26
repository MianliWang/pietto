# Phase71 planning notes：外部参考、假设与证据缺口

本文件记录 Phase71 开局审阅的外部参考、规划假设与仍未关闭的证据缺口。它随只含文档的路线发布提交发布，只在该提交的自然 exact-head CI 成功后成立，此前是 candidate。所有者采纳的推荐见[决定记录](../../decisions.md)的 D71.01–D71.11。
外部行为只为 Pietto 的决定提供依据，永远不成为仓库权威（[phase initiation gate](../../architecture/phase-initiation-gate-v1.md#external-reference-review-record)；[product design lessons](../../references/product-design-lessons-v1.md)）。

片号指 [24 片路线](slices.md)。下文的参考编号 E1–E3 只指外部参考，与 [execution guide](../../execution.md) 中的已保存结果流程 R1（重读）、R2（同源恢复）无关。路线图中本期一行是 [Phase 71](../../roadmap.md#future-roadmap-v6)。

## 范围与新鲜度

- 审阅的参考：Malloy Nested Views、PostgreSQL 18 文档（页脚 18.6）与 Apache Arrow Columnar Format（Arrow v26.0.0 文档，format 1.5）。没有其他外部参考影响本次开局。
- 所有者计划 v2 在 2026-10-25 查阅了这三份官方资料；lead 在同日重读了其中与本期结论直接相关的段落（PostgreSQL §9.21 聚合函数与 §7.2 表表达式、Arrow 的 List 与 Struct 布局、Malloy 的 nesting 页）。页面没有存档，下文引用的文档文字是阅读记录，不是保存的副本。
- 仓库里已有的相关审阅记录：Phase63 S1 的 R06 Apache Arrow（快照 2026-09-02，release 25.0.1，ADOPT，只作交换表示）与 R09 Malloy（快照 2026-09-02，ADAPT，owner 71/73/74），以及 [Phase70 外部参考记录](../phase-70/planning-notes.md) 的 PostgreSQL 18.6 LATERAL 观察。[产品架构](../../architecture/product-architecture-v1.md)已写明 Arrow `List<Struct>` 不等于 Pietto `NestedRelation` 语义。
- 本次开局没有原生观察。PostgreSQL carrier、精度与资源边界的实测是 S02 的实验（D71.09 授权它先于 S01 在 Teach 运行），结果只作证据，不是 Slice 验收或 Pietto 语义的证明。
- 目标 pin 不变：PostgreSQL 18.6、MySQL 8.4.12，`postgres_rows` 为 `psycopg[binary]==3.3.5` 加 `pyarrow==26.0.0`。

## E1 Malloy Nested Views

1. **Snapshot/date**：Malloy 官方文档 nesting 页（docs.malloydata.dev/documentation/language/nesting），2026-10-25 读取；仓库已有 R09（2026-09-02）。没有固定 Malloy 版本，也没有运行 Malloy。
2. **Problem/constraints**：每个父行带子表，以及多层分析结果。Pietto 只借作者的理解模型，本期只做一层、只做 PostgreSQL。
3. **Semantic/identity model**：`nest:` 在外层 view 里生成一个 aggregating subquery，为所在 view 的每一行产生一个子表；示例 JSON 中每个外层行带一个数组。每一层是自己的 query 与 grain。
4. **Layering/dependency direction**：嵌套 view 嵌在外层 view 之内，层与层之间由语言定义，不由 SQL 表示定义。Pietto 对应的是语义/UX 层。
5. **Algorithms/data structures/complexity**：Malloy 用自己的分组 SQL 策略一次生成多层结果；Pietto 不复制该策略。
6. **Interface/version/capability model**：不假定 Malloy 支持的所有 dialect 都能迁移到 Pietto；Pietto 只有 PostgreSQL 的有限 lowering。
7. **Testing/operational lifecycle**：可借用的反例是“子表过滤独立于父层”与“并列子表互不相乘”；页面说过滤可以写在嵌套的任一层，示例中的 `limit: 5` 写在子表内。
8. **Pitfalls/migration costs**：页面正文没有说明聚合 locality 怎样相对外层计算，也没有说明嵌套内的排序规则（生成的 SQL 里有 `ORDER BY`，但正文没有承诺）；隐式的聚合 locality 会把聚合代数拖进本期。
9. **Disposition**：`ADAPT`，只取用户模型。
10. **WHAT_NOT_TO_COPY**：无界多层嵌套；隐式 grain 与隐式 group capture；它的完整 grouping SQL 策略；UI 与展示路径当身份。
11. **Pietto owner affected**：语义/UX——S03（写法与类型显示）、S04（Collect 绑定）、S16（并列子表与阶段组合）；聚合 locality 与隐式分组归 Phase73；多层嵌套由 S24 指定接收 owner。

## E2 PostgreSQL 18.6

1. **Snapshot/date**：PostgreSQL 18 文档（页脚 18.6），2026-10-25 读取：§9.21 Aggregate Functions 与 §7.2 Table Expressions（含 LATERAL、表函数与 `WITH ORDINALITY`）。Phase70 的 18.6 原生 LATERAL 观察（2026-10-14）仍有效；本次没有新的原生观察。
2. **Problem/constraints**：PostgreSQL 是唯一的嵌套执行目标。本期要把“每父行一个有序子表”与 CROSS/INNER/LEFT 展开 lower 到它上面，同时保持 Pietto 的空集、NULL、重数与顺序语义。性能不在范围内。
3. **Semantic/identity model**：
   - **聚合的空输入。** 除 `count` 外，聚合在没有选中行时返回 NULL；文档特别指出 `array_agg` 在没有输入行时返回 NULL 而不是空数组，需要时用 `coalesce` 替换。
   - **聚合的输入顺序。** `array_agg`、`string_agg` 等的结果取决于输入顺序，而这个顺序默认不确定，要在聚合调用里写 `ORDER BY` 才受控；从已排序子查询供值“通常”可行，但外层若还有 join 等处理就可能被打乱。
   - **LATERAL。** 前置 `LATERAL` 的 FROM 子查询可以引用前面 FROM 项的列，对提供这些列的每一行求值一次；`LEFT JOIN LATERAL … ON true` 让没有产出行的源行仍然出现在结果中。
4. **Layering/dependency direction**：只作为 dialect lowering 与执行 carrier；PostgreSQL 的默认值不进入 Pietto 语义，Pietto 的语义由 [brief](brief.md) 的语义契约独立定义。
5. **Algorithms/data structures/complexity**：相关执行与聚合可能昂贵；LATERAL 对每个提供行求值。本期不承诺执行成本，只承诺可证明的运输量上界（S02）。
6. **Interface/version/capability model**：
   - Pietto 只接受确切的 18.6 并在运行时核对。
   - `WITH ORDINALITY` 为函数结果加一个从 1 开始的 bigint 序号列；多参数 `UNNEST` 等价于对每个参数分别 `UNNEST` 再以 `ROWS FROM` 组合。
   - 使用实际锁定的数据库 profile 与 `postgres_rows` 驱动；ADBC 1.12.0 对嵌套值的映射本期不评估（D71.05 拒绝该路线）。
7. **Testing/operational lifecycle**：需要覆盖空输入、排序、NULL 补齐与真实原生执行；新发射变体进入完整 PG 目标清单，封存前按 D71.11 在本机 Docker 运行；S02 的 Teach 实验只作证据。
8. **Pitfalls/migration costs**：
   - 不处理 `array_agg` 的空输入会把 `[]` 变成 `None`。
   - 只靠上游子查询排序不能保证聚合顺序；多个聚合各自排序、遇到并列值时可能互相错位。
   - JSON 文本解码会丢 Decimal 的小数位与 Float 的 signed zero（按 JSON 解析 `-0` 得整数 `0`），重复的 JSON key 只保留最后一个。
   - 多参数 `unnest` 遇到不等长数组会补 NULL，悄悄造出元素。
   - 每个新发射变体都增加目标 conformance 回执。
9. **Disposition**：`ADOPT/ADAPT`，只取有限机制（LATERAL、聚合内 `ORDER BY`、显式空输入处理）。
10. **WHAT_NOT_TO_COPY**：
    - 原样照搬 JSON 的值语义或 driver 自动转换；
    - 聚合空输入返回 NULL 与默认不确定的顺序作为 Pietto 契约；
    - 依赖已排序子查询保证聚合顺序；
    - `ROWS FROM`、`WITH ORDINALITY` 与 select-list 中的集合返回函数作为公开写法；
    - 多参数 `unnest` 的 NULL 补齐；
    - 规划器策略与优化假设。
11. **Pietto owner affected**：
    - S02：carrier、精度与资源边界实验。
    - S06：计划中的 Collect/Unnest 表达与 carrier 需求。
    - S08：Collect source emission（空输入、顺序契约、Top-K、并列子表）。
    - S13：Unnest emission 与公开纵向。
    - S14、S15：SQL 内展开后的 scalar 语义。
    - S20、S21：组合复核与差分语料。
    - 深度适配与数据库原生 array/JSON 列：Phase76。

## E3 Apache Arrow Columnar Format

1. **Snapshot/date**：Apache Arrow v26.0.0 文档的 Columnar Format（format 版本 1.5），2026-10-25 读取；仓库已有 R06（2026-09-02，release 25.0.1）。当前 pin 是 `pyarrow==26.0.0`。
2. **Problem/constraints**：嵌套结果的类型化值布局、零拷贝互操作与 IPC 保存。Pietto 只把它用作 ResultContract 下游的交换表示。
3. **Semantic/identity model**：
   - **List。** offsets buffer 有 length + 1 个有符号整数，即使是 null slot 也要单调不减；null 由 validity bitmap 表示，一个 null list 可以对应 child array 中非空的一段，其内容任意；空 list 是两个相等的 offset。
   - **Struct。** struct array 有自己的 validity bitmap，独立于各 child 的 bitmap；一个 child 值是否有效要取两个 bitmap 对应位的逻辑与，所以有效的 child 值可能被 null 的 struct slot 遮蔽。
   - Arrow 定义物理 fields/children，不定义 Pietto 的 occurrence 或身份。
4. **Layering/dependency direction**：位于 ResultContract 之下；Arrow 的 schema 与字段名不反推 Pietto 语义（[产品架构](../../architecture/product-architecture-v1.md)）。
5. **Algorithms/data structures/complexity**：offsets/children 的有界遍历；验证复杂度与 children 总数成线性，费用计算需要计入 children 与 offset buffer。
6. **Interface/version/capability model**：沿用已锁的 Arrow owner 与 `pyarrow==26.0.0`；IPC 序列化时文档建议把 offsets 规范化为从 0 开始；Pietto 的 IPC 保持 `compression=None`、`allow_64bit=False` 与 96 MiB 上限。
7. **Testing/operational lifecycle**：0 行、切片与非零 offset、validity 遮蔽、零长 absent buffer、copy/borrow 与 close 后的归属、C data/stream 与 IPC 消费；同型换列、丢重与 offset 损坏要被独立 oracle 抓住。
8. **Pitfalls/migration costs**：
   - null list 下的 child 段内容任意，不能当作数据读取。
   - struct 的 null 会遮蔽有效的 child 值，只看 child bitmap 会出错。
   - 切片后的 offset 不从 0 开始。
   - 文档没有逐条说明切片与非零起点 offset 的规则，Pietto 以实际 SDK 行为与自己的验证为准。
   - SDK 接受一个 batch 不代表语义或完整性正确。
9. **Disposition**：`ADOPT`，只取表示。
10. **WHAT_NOT_TO_COPY**：用 List/Struct 代替关系语义；从 Arrow schema 或第一条数据推断 Pietto 类型；承诺全系统零拷贝或支持所有 Arrow 类型（LargeList、ListView、Map 等不在本期）。
11. **Pietto owner affected**：S07（递归 ResultContract 与 digest）、S10（binding、construction 与计量）、S11（ownership 与生命周期）、S17（IPC framing 与兼容拒绝）、S18/S19（保存与断源读取）；dataframe 适配归 Phase80。

## 对 Phase71 决定的影响

| 所有者决定 | 依据 | 处置 |
| --- | --- | --- |
| Collect 收集已完成的关系，保持 bag 重数；零行得 `[]`，不是 `None`；并列子表各自完成后再附属于父行（D71.04） | E1 每行一个子表的用户模型；E2 `array_agg` 空输入返回 NULL；E3 空 list 与 null list 的区分 | ADAPT（空输入显式处理，不搬 PostgreSQL 默认值） |
| 被 `collect` 读的 let 必须写 `order by`；lowering 把顺序带进收集操作本身；并列不承诺（D71.03） | E2 聚合输入顺序默认不确定，排序子查询遇到 join 可能失效 | ADAPT（顺序契约由 Pietto 定义） |
| CROSS/INNER/LEFT Unnest 先 `let o = unnest(...)` 再 JOIN，LEFT 在没有匹配时保留父行一次（D71.02、D71.04） | E2 LATERAL 与 `LEFT JOIN LATERAL … ON true` 保留源行 | ADAPT（不公开 `ROWS FROM`/`WITH ORDINALITY`） |
| 结果是严格 schema 的 `List<Struct<...>>`，层级 validity 区分空集合、`None` 容器、NULL record 与 NULL 字段；完整嵌套合同进入 digest（D71.04、D71.06） | E3 List offsets/validity 与 Struct 的独立 validity | ADOPT（只作表示） |
| carrier 用受控文本或位置化 row array，由 schema 指导的严格 decoder 还原，不从 JSON 推型（D71.07） | E2 与 JSON 解码的精度陷阱；E3 的类型化布局 | 待 S02 实证 |
| 只做一层嵌套；不做隐式 group capture 与聚合 locality（D71.04） | E1 的多层与隐式 locality 会把聚合代数拖进本期 | REJECT for Phase71（Phase73 与 S24 的接收 owner） |

## 规划假设

| 输入 | 本期假设 |
| --- | --- |
| 方向 | 延续路线图对 Phase71 的 NestedRelation/Collect/Unnest/flatten/nested Arrow 归属 |
| Stage | 描述性目标“向稳定 1.0 迈进的可组合查询与类型化结果”，不编造数字 Stage |
| 容量 | 24 片必做加 1 个未分配位置，容量 25（D71.09）；Phase70 的修复余额不继承 |
| 时间 | 没有截止日期；lead 的推论是实施约 3–6 天加收尾，`0.1.6` 整体约 2–3 周，这不是承诺 |
| 使用反馈 | 没有最新实际使用体验；不编造“能用但脆弱”的场景 |
| 开发组织 | 一个主集成者，至多 3 个隔离 worker，共享写面统一接线 |
| 公开范围 | 先保证有限域端到端完整；不同时扩大 dialect、runtime、平台与恢复协议 |
| 基线 | S01 绑定下一版合成后的候选；计划 v2 的 `6d0f6c6c` 与路线发布基线 `88c11d08` 只作规划证据 |
| 资源界限起点（D71.07，由 S02 证实或替换） | 行数上限只数父行，`batch_rows`、`max_rows` 含义不变；子行计入字节上限（默认每批 1 MiB）；每次执行最多 1,048,576 个子行；一个父行的列表放不进一批时整批拒绝，不拆行 |
| 写法 | `collect` 加关系名与 `let o = unnest(...)` 加 JOIN（D71.01、D71.02）经 S03 前的学习者探测验证；探测推翻时回到所有者 |
| Teach 与验证 | Teach 只做非权威预检与实验；权威验证在集成主机，直到 runner acceptance 落地；封存前 PG 原生检查在本机 Docker（D71.10、D71.11） |

## 证据缺口（开局时未关闭）

| 缺口 | 现状 | 关闭点 |
| --- | --- | --- |
| PostgreSQL carrier 的精度、空输入、顺序与对齐，以及真实内存/大小边界 | 只有文档与推论；没有原生实测 | S02（Teach 实验，D71.09） |
| 写法的可学性 | 推荐写法只经 0.1.5 编译器对照（新写法今天是语法错或语义拒绝），没有学习者探测 | S03 冻结前 |
| 新诊断码段与逐字消息 | 开局时 `PIE-S28xx` 未被使用；下一版会新增或退役一些码 | S01 在绑定的基线上确认，S03 Gate 1 定稿 |
| 下一版（`0.1.6`）候选 | 各项尚未合成，只在 main 之外的 worktree；身份未知 | S01 Gate 0 |
| 项目模式 FROM 别名的缺陷（`PIE-S2102` 与 `inconsistent_scope_relation` traceback）与 JOIN 诊断的多余 `PIE-S2334`、`PIE-S2333` 内部用语 | 0.1.5 上实测复现；归 `0.1.6` 修复项 | S01 核对下一版候选上的结果；Unnest 继承 JOIN 诊断 |
| runner acceptance | 没有 acceptance tool 与合格环境记录；只有集成主机合格 | S03 之前的单独派发（D71.10） |
| CI health | `INSUFFICIENT_EVIDENCE`、可比样本 0；成本记录不完整 | 中点与 S22 消费最新适用样本 |
| ADBC PostgreSQL 1.12.0、psycopg 3.3.5 对数组与 record 的 loader | 未审阅 | 不在本期（D71.05 拒绝 ADBC 嵌套路线；psycopg 的实际解码由 S02 观察） |
| 外部页面存档 | 2026-10-25 的阅读没有存档 | 不关闭；记录为阅读笔记 |
| 学习者以外的真实使用反馈 | 没有 | 不阻塞本期；S24 交接记录 |
