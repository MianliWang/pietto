# Phase71 S01 — 合成基线绑定与消费者 owner（candidate）

S01 绑定 D71.09 要求的下一版合成候选。该内容已发布为
`9511f13563d0d5ce21fc778c6a3828a8324c2222`，tree
`50e3488948e1d80c5f76fd844f6305a4715ea010`，source tree
`46e7421af2d3f771f6d35547ad422941d3015e36`。这是内容绑定，不是浮动的 `main`
引用。包版本仍是 `0.1.5`：B1 不改已发行字节，也不发行 `0.1.6`（尚未发行，其版本与发行另行授权）。
这一绑定就是 B1 的基线：S01、S02、S03 都建立在 main `9511f135` 之上。所有者 2026-10-27 批准的
post70 修正与新增的 MySQL 单文件 parity 是落在 S03 之后的 `0.1.6` 提交，不改变这一绑定（见下文
“开放项与 owner”一节）。

基线的自然 [CI 40379937842](https://github.com/MianliWang/pietto/actions/runs/40379937842)
是 `push/main` attempt 1，19 个 job 全部成功。Gate 0 fetch 了 main，确认这一确切提交、
tracked 内容与 index 干净且没有进行中的 Git 操作，并建立了干净隔离的 B1 worktree。
canonical checkout 中已有的无关未跟踪文件保持不动。

本准备记录不声称 B1 已验证或已发布，也不声称有独立评审覆盖本文的字节：B1 证据目录中的
S01 评审针对更早的字节（它记录的 `slice-01.md` 摘要是 `85bfd98049af…`），本修订在 B1
验收前须重新独立评审。S01、S02、S03 各保留一笔提交，随后在集成主机上对批次最终树做一次权威
验证、一次 fast-forward push，并以批次头的自然 CI 为准。

## 写者、worktree、写集与检查

- 活动 writer：B1 只有一个主集成 writer（派发记录
  `/home/mianliwang/.local/state/pietto/evidence/pietto-phase71-20261026/b1/dispatch.json`
  的 `integration_writer`；2026-10-27 的 lead 交接见
  `/home/mianliwang/.local/state/pietto/evidence/pietto-phase71-20261026/claude-takeover-20261027/TAKEOVER-zh.md`）。
  隔离开发 worker 的上限见 D71.09 及其 2026-10-28 修订（先提高到至多 6 个，随后允许按需至多 12 个），
  同一共享文件同一时刻只有一个 writer。
- 集成 worktree：`/home/mianliwang/projects/pietto-wt/phase71-b1-integrated-codex`（S01/S02 文档）；B1 批次树在
  `/home/mianliwang/projects/pietto-wt/phase71-b1-batch-claude` 合成（记录
  `/home/mianliwang/.local/state/pietto/evidence/pietto-phase71-20261026/claude-takeover-20261027/wf5/b1-batch-integrate/integration-record.json`）。
  S03 的开发 worktree 与冻结 tree 记在同一 B1 证据目录。
- S01 写集（只含文档）：`docs/phases/phase-71/slice-01.md`（新增）、
  `docs/phases/phase-71/brief.md`（当前绑定指引、路线发布事实与回看 5 的核对结果）、
  `docs/phases/phase-71/planning-notes.md`（路线发布事实与开局缺口表的当前指引、核对结果）、
  `docs/decisions.md`（D71.09 的 2026-10-28 worker 上限修订）与 `docs/roadmap.md`（所有者 2026-10-28
  的 MySQL 节奏说明）。S02 写集是
  `docs/phases/phase-71/slice-02.md`（新增），加上两份描述整个批次并链接 `slice-02.md` 的文件；
  它们随 S02 的提交进入，不更早，否则 S01 提交会留下断链：
  `docs/phases/phase-71/slices.md`（路线发布事实与 B1 绑定句、决定范围由 D71.01–D71.11 改为
  D71.01–D71.12、授权条目中 worker 上限的 D71.09 修订、路线发布条目的提交号、路线表 S01/S02 两格的链接）与 `docs/status.md`（“Repository package and CLI”行、Phase71 行、新增的
  “Phase71 runner acceptance bootstrap”行、Next 行，以及以 `Phase66/Interlude V/R1 保持 COMPLETED`
  开头的长段）。
- 检查命令（在集成 worktree 中，Python 3.13.13）：
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -p no:cacheprovider tests/test_active_phase_lifecycle.py tests/test_workflow_lifecycle_validation_efficiency.py tests/test_repo_static_hardening.py`；
  S01 与 S02 写集中每个文件的相对链接解析到存在的文件；`git rev-parse` 核对上文 commit、tree 与
  source tree，`gh run view 40379937842 --json headSha,event,attempt,conclusion,jobs` 核对 CI 事实。

## 取代规划假设的现行事实

- 已批准的 Post70 修复与 C1–C8 已合入，但本基线与已批准的决定仍有出入（见下文“开放项与 owner”
  一节）。其中一项是发布说明缺条目：所有者决定 B13（与 C1–C8 同属 Post70
  决定导出的第 7 节，2026-10-25 批准）把 S1 后续的诊断码与条数变化作为纠错接受，并要求写进发布说明。行为已在本基线：单文件
  `from orders`、`let c = custmers`、`inner join c on c.id == orders.customer_id`（复现程序
  `/home/mianliwang/.local/state/pietto/evidence/pietto-phase71-20261026/claude-takeover-20261027/wf3/verify-docs-rereview-s01-r1-minors/b13/main.pietto`）
  在 9511 报 `13:13 PIE-S2301 error: Unknown relation: custmers`，在 0.1.5 报 `13:5 PIE-S2604`；
  `docs/release-notes.md` 的 “Unreleased changes following 0.1.5” 一节却没有对应条目，已准备的
  草稿（`/home/mianliwang/.local/state/pietto/evidence/pietto-post70-stability-20261016/work/claude-lead-20261023/v016-release-notes-draft/B13-s1-followup-r3.md`）
  未合入。B1 写集不含发布说明，本片不补（开放项 O1）。
- 手写 ON 可以使用源声明的键；项目推导的唯一键在 9511 只有一部分能证明 ON 匹配，容器内的键不能
  升级为全局键。实测（复现
  `/home/mianliwang/.local/state/pietto/evidence/pietto-phase71-20261026/claude-takeover-20261027/wf4/docs-fix-r3/run2/b8all`，
  9511 输出在同目录的 `b8all-9511.log`）：键经只带 `where` 过滤、或只带 `order by`/`limit` 的不分组查询
  保留下来时可以匹配；键来自分组查询的 GROUP BY、带 `any(...)` 过滤的查询、带窗口列的查询或
  `select distinct` 查询时，对这样的生产者写键上的 ON 等式，`check --project` 仍报 `PIE-S2333`
  （`models/shop.pietto:69:1`、`:76:1`、`:83:1`、`:90:1`），补救文字却要求
  “match a unique key of t in `on`”，即程序已经写的等式（审计 a1:F2、A2-08；修正第 1 轮评审
  SEM-R1-03）。其他生产者形状未逐一实测。所有者 2026-10-27 对 B8 的决定：`0.1.6` 写真实的
  文档并给出不循环的补救文字，不扩大键；键扩大以后作为单独评审的项。由修正计划组 G13 承接（开放项
  O2）。已有的有限 D11/D12 改进不授权其保留的后续范围。
- 项目模式 FROM 别名：0.1.5 的 traceback 与 `PIE-S2102` 在本基线已修复。以下复现程序都在
  `/home/mianliwang/.local/state/pietto/evidence/pietto-phase71-20261026/claude-takeover-20261027/wf3/docs-rereview-s01-r2`（下称复现根）中：
  `fromalias/from_alias_relname`（`let c = customers`、`from c`、`id = customers.id`）在 0.1.5 抛出
  `ValueError: Canonical inspection payload must evaluate exactly: inconsistent_scope_relation at record 26 field None.`，
  在 9511 得 `Project check OK`。但原来源名限定字段的兼容超出了 0.1.5 接受的范围：同一别名之后写
  `where any(o.customer_id == customers.id for o in orders)`（复现根下的 `a203`），9511 通过，
  0.1.5 退出 1，先报旧的 FROM 别名缺陷 `17:14 PIE-S2102 error: Unknown field: c.id`，再报
  `15:32 PIE-S2334 error: ANY predicate reference is unavailable.`（后者专属该 `any` 引用）。所有者只批准保留以前
  接受的写法，9511 的发布说明也写明 `any`、capture 与 JOIN 作用域不适用这一兼容；这一出入属于
  开放项 O2（审计 A2-03，也包括 JOIN 中的同类扩大）。
- 下面两种 JOIN 写法（开放项 O3）的诊断在 9511 与 0.1.5 逐字相同，没有下一版修正可供继承。`schema_version = 2` 项目中
  `let o = their_orders` 之后写 `cross join o on True`（复现根下的 `joindiag/crosson`），9511 与
  0.1.5 都报两条多余的 `PIE-S2334`
  （`20:5` 的 `CROSS JOIN is available only when an EXPLICIT_MODULES project (schema version 2) completes it.`
  与 `20:18` 的 JOIN-local ON 同句）以及 `20:5 PIE-S2336 error: CROSS JOIN cannot have ON or VIA.`；
  同一 capture let 写 `left join o` 而不写 `on`（`joindiag/lefton`），两版都报内部用语
  ``20:5 PIE-S2333 error: Project relation semantic completion is unavailable: q (JOIN o: write `on` with the condition that matches customers to their_orders)``。
  这不是说 JOIN 诊断整体未变：所有者 2026-10-25 批准的 B13 修正已在本基线，其中包括 JOIN 诊断，
  例如上文 B13 复现里 JOIN 别名 let 的 `PIE-S2301`（0.1.5 为 `PIE-S2604`），以及项目 JOIN `on`
  以 JOIN 输入为实参调用未知函数时只报一条 `PIE-S2103`（0.1.5 报 `PIE-S2334` 加一到两条
  `PIE-S2335`；复现
  `/home/mianliwang/.local/state/pietto/evidence/pietto-phase71-20261026/claude-takeover-20261027/wf4/verify-docs-rereview-s01-r3-minors/r3b/jf4`
  与同级的 `jf5`，输出在同级的 `joinfn.log`；B13 草稿列有这些变化）。
  S03 以 9511 的现行输出（含这些 B13 修正）作为 JOIN 诊断基线；以后对 JOIN 诊断的任何修正由 Unnest 按 D71.02
  自动继承（开放项 O3，已处置）。
- 本基线的源码与测试都没有使用 `PIE-S28xx`。S03 按需连续分配新码并记录逐字消息；这一观察不经
  新注册表预留码段。
- D71.02 记录 0.1.5 在 JOIN 前别名 let 右边写 `unnest(...)` 时报 `PIE-S2604`、下一版可能改码。
  本基线未改：EXPLICIT_MODULES 项目中 `from lhs` 之后写 `let o = unnest(lhs.id)` 再
  `cross join o`，9511 与 0.1.5（`6d0f6c6c` 的 `src`）的 `check --project` 都报
  `main.pietto:8:5 PIE-S2604 error: A row-value let must follow FROM and every JOIN and precede WHERE`。
  S03 以它为现行诊断基线。
- 相关的锁定 pin 仍是 PostgreSQL 18.6、`psycopg[binary]==3.3.5` 与 `pyarrow==26.0.0`。S02 的
  native 实验在远端没有 PyArrow；单独的本地 Arrow/IPC replay 使用 26.0.0。两者是互相独立的
  非权威实验证据。
- Runner acceptance bootstrap `ad7baf65280b957691cb0a70a01b6e27e17ade0f` 已发布且自然 CI 成功，
  但记录的 bootstrap 绑定 `ad7baf65` 的 acceptance rule 字节，而 `9511f135` 改了其中的
  `scripts/ci_validation.py`（collection 命令加 `-c pytest.ini`）。因此它拒绝 `9511f135` 的每个后继，
  包括 B1 的候选（审计 A6-3：`candidate changes adopted acceptance rule bytes`）。所有者 2026-10-27
  决定暂不改 runner acceptance 机制（不补 `ci_workload` 标记，也不重新 bootstrap），所以 B1 的权威
  验证只在集成主机运行，不使用 Teach 拆分；Teach 仍只做非权威预检与实验。bootstrap 本身也不是
  Teach 回执。
- S02 的实验与本地 replay 已完成。七种实测 carrier 保留了 fixture 的值；两种 JSONB 变体丢失
  signed zero。S02 必须选定编码并写明来源/资源前提。实验通过不代表产品已有嵌套路线。

## 开放项与 owner

S01 不把 O1、O2、O4 报告为已闭合；O3 已由 lead 处置。开放项来自对 9511 的独立审计
`/home/mianliwang/.local/state/pietto/evidence/pietto-phase71-20261026/claude-takeover-20261027/post70-audit-confirmed.json`
（39 条经对抗验证的发现：1 BLOCKER、11 MAJOR、21 MINOR、6 NIT）与修正计划
`/home/mianliwang/.local/state/pietto/evidence/pietto-phase71-20261026/claude-takeover-20261027/wf3/post70-plan/plan.json`
（G01–G24 共 24 组），但两者不是完整清单：修正候选的第 1 轮评审
`/home/mianliwang/.local/state/pietto/evidence/pietto-phase71-20261026/claude-takeover-20261027/wf3/post70-r1-reviews.json`
之后又确认了 9511 已有的缺陷，其中两条 BLOCKER 级缺陷审计与计划都没有（见 O2 一行）；修正记录
`/home/mianliwang/.local/state/pietto/evidence/pietto-phase71-20261026/claude-takeover-20261027/post70-correction-ledger.jsonl`
在 2026-10-27T15:26Z 记下这两条均继承自 9511。它们同样由已批准的 post70 修正承接。修正候选在 main 之外准备（集成 worktree
`/home/mianliwang/projects/pietto-wt/post70-fix-integ-claude`）。D71.09 不覆盖它的发布；所有者
2026-10-27 单独批准了发布，并新增一项 MySQL 单文件 parity：在单文件 JOIN 及同类单文件族上，MySQL
先与 PostgreSQL 齐平，只用确切的 MySQL 8.4 lowering，非确切形状继续失败关闭（记录：
`/home/mianliwang/.local/state/pietto/evidence/pietto-phase71-20261026/claude-takeover-20261027/owner-answer-20261027T1518Z.json`）。
两者各自是普通提交，落在 S03 之后，但不在 B1 中：lead 2026-10-28 在 D71.09 范围内决定 B1 只含 S01、S02、
S03 并先发布；post70 修正收敛后作为 B1 之后单独的一批发布，MySQL parity 也在 B1 之后的批次发布。`0.1.6` 的版本、tag 与
发行仍未授权。

| 项 | 现状（9511） | owner / 最晚点 |
| --- | --- | --- |
| O1 B13 发布说明条目 | 见上文；审计 a1:F1、A2-07 | 修正计划组 G10，随已批准的 post70 修正提交；最晚点：`0.1.6` 发行之前（B13） |
| O2 与已批准决定相悖的基线缺陷 | 例如单文件 QUALIFY 外层的 `any` 读同文件的表时只按裸名读取，不定义依赖 CTE（审计 a3:F1，BLOCKER）：复现根下的 `qany/q.pietto` 在 9511 的 `emit-sql --dialect postgres` 退出 0，语句读 `FROM "bulk_lines"` 且没有 `WITH`，0.1.5 报 `24:5 PIE-I1000`；这与 Post70 决定 B1（同文件读取内联为依赖 CTE，被读关系拒绝时读它的语句也拒绝）相悖，也是相对 0.1.5 的回归。`check --project` 接受没有内部 ORDER BY 的 `string_agg(name, ",")`（审计 A2-02；复现根下的 `a202` 项目，同一源码作单文件 `a202/single.pietto` 报 `13:17 PIE-S2104`），与 C5 相悖。还有上文的 FROM 别名扩大（A2-03）、B8 的 ON 键说明与循环的补救文字（a1:F2、A2-08）与 C1 警告覆盖不全（A2-04）。审计之后，修正第 1 轮评审又确认了两条 9511 已有的 BLOCKER 级缺陷（复现在 `/home/mianliwang/.local/state/pietto/evidence/pietto-phase71-20261026/claude-takeover-20261027/wf4/verify-docs-rereview-s01-r3-minors/r3b`）：同文件 1,000 个表的链（`chain/c1000.pietto`，每个表读前一个）在 9511 的 `emit-sql --dialect postgres` 退出 1，抛出 `RecursionError: maximum recursion depth exceeded`，不输出 SQL，0.1.5 退出 0 并输出 34,889 字节 SQL（SQL-R1-02，相对 0.1.5 的回归）；单文件 QUALIFY 外层的 `any` 读一个输出名为 `__pietto_qualify_0` 的同文件表（`cap/cap.pietto`），9511 的 `check` 与 `emit-sql` 都退出 0，`EXISTS` 里的未限定端口名被内层同名列捕获（`"_pietto_value_1"."__pietto_qualify_0" = "__pietto_qualify_0"`），结果行错误，0.1.5 的 `emit-sql` 报 `PIE-I1000`（SQL-R1-01、SEM-R1-02） | 修正计划组 G01、G06、G07、G13，随已批准的 post70 修正提交；审计之后发现的两条 BLOCKER 不在计划中，同样由该修正承接（第 1 轮评审因它们拒绝了候选）。A2-04（G14）所有者 2026-10-27 选择计划的选项 (a)：在该修正中逐项补全 C1 的 `PIE-S2385` 覆盖（enumerated completion）。审计其余各项的 owner 见计划，但所有者 2026-10-27 的回答改变了计划中的两组：所有者要求暂不改 Teach/runner acceptance 机制，lead 据此把 G18（receiver 失败关闭加固，A6-4、A6-6、A6-8；计划为 FIX）从该修正撤回，与该机制一起暂不改，仍是没有排期的开放项；G21（A6-1，计划为 REPORT_ONLY 并列出选项）按所有者决定不补标记、不重新 bootstrap（见上文 runner acceptance 一条）。最晚点：`0.1.6` 发行之前（G18 除外） |
| O3 JOIN 诊断的多余 `PIE-S2334` 与 `PIE-S2333` 内部用语 | 见上文：这两种写法的输出与 0.1.5 相同。它只是开局规划观察（brief 回看 5、planning-notes 缺口表），不是所有者批准的 Post70 项，修正计划也没有覆盖 | 已处置（lead，2026-10-27）：这两种写法没有可继承的下一版修正（已批准的 B13 JOIN 诊断修正不改变它们的输出，且已在 9511）；S03 以 9511 的输出为 JOIN 诊断基线，以后若有修正，Unnest 按 D71.02 自动继承 |
| O4 `docs/roadmap.md` 的生命周期孪生文字 | :32 与 :92 仍是路线发布前的条件句（自然 CI 成功前是 candidate），没有记录已发布的 `6e9d7be6`，与本批次改过的 status、brief、slices 不一致；:2912–2914 仍写 D71.01–D71.11。S01 写集只在该文件加入所有者 2026-10-28 的 MySQL 节奏说明，不改这些孪生文字 | 由已批准的 post70 修正提交（修正计划组 G20）更正；B1 文档只指向该提交 |

这些提交不改变 S01 的绑定：B1 的基线保持 main `9511f135`，S01–S03 都建立在它之上；post70 修正与
MySQL parity 是 B1 之后批次中的 `0.1.6` 提交；B1 的批次最终树不含它们，它们所在批次的最终树各自得到
一次权威验证。S03 消费的 FROM 别名、JOIN 诊断与 `PIE-S2604` 基线仍取自 9511；修正改变其中的事实时，
由修正提交更新受影响的检查与文档，JOIN 诊断的修正由 Unnest 按 D71.02 继承。main 在 B1 推送前若出现
其他提交，仍按[解冻条件](slices.md#检查点与解冻)处理。

## Owner 与依赖方向

一个主集成者拥有合成后的 tree。隔离开发 worker 按 D71.09 及其 2026-10-28 修订的上限参与；共享文件同一时刻只有一个
writer。S02 的证据/设计与 S03 的私有实现可以并行；两者都在 S01 之后完成验收，S03 不依赖
S02 的验收。[既有批次路线](slices.md#分批发布)仍是 B1–B9，不新增 Slice。

| 现有 owner | 后续必须接收的消费者与边界 |
| --- | --- |
| `grammar/Pietto.g4`、`ast_nodes.py`、`ast_builder.py`、生成的 parser | S03 拥有书写语法、位置、上下文词与完整 AST 读者集合。生成文件只来自固定版本的生成器。 |
| 对未知表达式节点以 `Unsupported expression` 抛异常的 13 处闭合分派遍历（9511 行号）：`semantic/aggregates.py:299`、`semantic/analyzer.py:1197`、`semantic/expressions.py:2162` 与 `:2325`、`semantic/let_bindings.py:724`、`semantic/field_derive_cycles.py:166`、`ir/lowering.py:1339`、`_project/model.py:3314`、`_project/module_semantic_fact_preservation.py:4261`、`_project/aggregate_grouped_clause_facts.py:1449`、`_project/row_dependency_graph.py:618`、`_project/row_expression_schema.py:505` 与 `:519` | S03 让每个新 variant 在每一处都得到确定结果（遍历其子节点或确定拒绝），可达输入不得出现 traceback。S03 第一个类型化候选就在 `aggregates.py:299` 抛出 `AssertionError: Unsupported expression: CollectRelationExpr`（`/home/mianliwang/.local/state/pietto/evidence/pietto-phase71-20261026/b1/s03-typed-c1-focused.log`）。这份按消息文本得到的清单只是下限；不抛异常、静默跳过未知节点的读者仍由 S03 在完整 AST 读者集合中逐个核对。 |
| `semantic/modern_inputs.py`、semantic 类型/作用域 owner、`_project/project_relationship_predicates.py` | S03–S05 区分关系别名、scalar let 与 Unnest 输入；保留确切的 binding/字段 occurrence 与完整解析证据。 |
| 项目 IR、SQL plan、verification、portable 与 source-map owner | S06 投影受检的 Collect/Unnest 权威。未知 variant 拒绝；名字与运输列不能替代操作身份。 |
| `project_result_contract*`、`project_result_output.py`、`project_result_binding.py` | S07 定义递归逻辑形状、occurrence 与 nullability。S08/S10 绑定实际发射的 producer。这些消费者闭合前，现有只接受 scalar 的拒绝保留。 |
| `project_sql_emission_*` 与 PostgreSQL lowering | S08 独立收集每个已完成的子关系，保留实际的排序需求。S13 在 scalar 运算前为 Unnest 恢复类型化 scalar 值。 |
| `project_compiled_*`、`project_execution_template.py` | S09 闭合 encode/decode、verification、加载与 source-free 使用。live 准备已经要求 compiled 构造，不能绕开这一依赖。S13 开放可执行的 Unnest。 |
| `project_arrow_result.py`、`project_arrow_interop.py`、result ingress/reader | S10/S11 拥有递归构造、child/offset 验证、计量与 copy/borrow/lease 清理。现有只支持平面的 copy 路径不够。 |
| `project_execution_reader.py`（`check_native_column` 只接受 scalar 存储类型码，`postgres_rows` 经 `ExecutionPayloads`/`bind_native_output` 使用它；ADBC、MySQL 与 refinement 经 `decode_native_rows` 逐个 producer 字段做 scalar 解码；`bind_stored_output`）与 `project_execution_postgres.py`（`postgres_rows` 尝试与 owned 会话设置） | S10 拥有 native descriptor 与严格 decoder 的嵌套扩展，并固定或核实文本解码依赖的会话设置（见 S02 记录 `slice-02.md` 的前提表）。S12 的 `postgres_rows` 中点纵向经过这一 reader。其余导入者沿用本表的 owner：job capture 归 S18/S19，公开执行、guard 与 refinement 归 S12/S13，MySQL/ADBC 的早期拒绝由 S20 核实；`project_execution_source.py` 的 `verify_source_observations` 也调用 `check_native_column`，但只核对 source 字段的原生列、不读取结果列，不在嵌套结果的路径上，保持只接受 scalar。所属片闭合前保留只接受 scalar 的拒绝。 |
| `project_result_ipc.py` | S17 绑定完整嵌套合同，物化前验证 framing/限制，覆盖截断、offset 与重分批。 |
| Job workspace、chunk、publication、replay 与公开 saved/export owner | S18/S19 保留完整顶层 occurrence，并分别验证 R1 与 export。除非实际语义需要，复用 workspace v7。 |
| 执行/公开路线守卫、refinement、R2 与 effect codec | S12/S13 只暴露已完成的路线。S20 核实 MySQL、ADBC、R2 与 sink/relay 的早期拒绝，包括最终投影为平面的 Collect/Unnest。 |
| `_project_explain/`（`json_v1.py` 的 JSON 与 `text.py` 的文本渲染）、`cli_json.py` | 终态 1 要求 `explain --project` 对新程序给出确定结果。S03 拥有新 variant 在这些读者中的确定行为（拒绝或沿用既有形状）与嵌套类型显示这一 UX 候选（D71.01、brief 的“时间够才做”）；未获批准前公开 explain/CLI JSON 形状不变；S21 串联核对。 |
| `pyproject.toml`、`uv.lock`、安装与 bundle 消费者 | 每个改动它们的片闭合实际的包读者；S23 核实完整的已安装产品并准备发行材料。 |

测试放在所观察的最深产品 owner。现有 parser、项目 let、IR/plan、compiled、result/Arrow/IPC、
执行与 jobs owner 仍是获取 owner。只有真正的新功能才新增按功能命名的 owner；不引入 phase
快照、路径/计数锁或完成审计测试。

## 供下游验收的独立反例

这些期望来自选定的语义模型，不来自 carrier decoder。后续正例必须经由所属的真实产品 producer 进入。

| 字面输入或变异 | 必须观察到 | Owner |
| --- | --- | --- |
| 三个父 occurrence，值为 A、A、B；每个 A 有子行 [7, 7]，B 为 [] | Collect 保留 3 个父行与 4 个子行；值相等从不合并 occurrence。CROSS（不写 ON）或 INNER ON True 得 4 行；LEFT ON True 得 5 行。 | S04–S06、S12–S13 |
| 同一输入，LEFT Unnest ON 子值 > 10 | 恰好 3 个占位行，每个父 occurrence 一个。把该谓词移到 WHERE 可能删掉它们。 | S05、S13 |
| `[]`、不存在的容器 `None` 与 `[{v: None}]` | 三种不同状态；最后一个有一个真实子行。从不从全 NULL 字段推断存在与否。 | S03、S07、S10、S13 |
| 相互独立的 orders [1, 2] 与 payments [3, 4, 5] | 子行数保持 2 与 3；不预先做 2×3 的子行 join。 | S04、S08、S16 |
| 并列排序键、隐藏排序字段、书写的 Top-K、同类型字段换序 | 保留每个实际行、重数与书写的排序需求；不承诺 tie 顺序，不出现隐藏的公开字段，不按名字重建字段。 | S04、S06、S08、S13–S16 |
| 损坏的子 offset/count、未知 variant，或新操作投影为平面输出 | 在所属边界确定拒绝；平面输出从不解除操作级的路线/R2 限制。 | S03、S07–S11、S17–S20 |
| 一个完整父行列表超过已准入的批或来源上界 | 整个父行/批失败；从不拆分其持久 occurrence，也不静默加入来源 LIMIT。 | S02、S10、S18、S20 |

## Phase initiation review

[phase initiation gate](../../architecture/phase-initiation-gate-v1.md) 的三十个字段在下表重新绑定。
[brief](brief.md) 仍是语义与支持合同；本记录更新证据与 owner，而不是重放历史批准。

| 字段 | 当前处置 |
| --- | --- |
| 1 live authority；6 proof posture | 上文的确切合成基线/CI。实验、候选、Gate 2 与已发布证据彼此分开。 |
| 2 outcome；3 semantic model；22 UX | 类型化的父行带子行结果与显式 Unnest，一个 collection 层，D71.01–D71.05。S03 的真实学习者探测先于写法/诊断冻结；不使用合成的参与者结果。 |
| 4 identity；5 construction states | 父/子/字段/输出 occurrence 各自独立。只发布闭合的受检状态；现有 scalar 消费者在所属片完成前拒绝新 variant。 |
| 7 layers；8 dependencies；17 invalidation | 上文 owner 表按 AST → semantic authority → IR/plan → backend → execution/result 排列。改动使实际下游事实失效；下游不重新决定语义。 |
| 9 migration；25 packaging；27 release | D71.06 保留历史产物，不自动迁移。只升级受影响的兼容维度。S23 准备 0.1.6；版本/tag/release/PyPI 需要各自的授权。 |
| 10 requirements/capabilities；26 support | D71.05 明确选择 v2 模块/PostgreSQL/postgres_rows 与有界的 Arrow/保存/R1/export。requirement 从不成为 provider 或执行证据。 |
| 11 interchange；12 execution；13 lifecycle | 逻辑嵌套 schema 与 SQL 运输、Arrow 分开。S07–S19 拥有受检的递归交换、显式执行与父行级的所有权/清理。 |
| 14 trust；19 concurrency | 既有的 trusted-opened-byte 与 runner 边界不变。Teach 上没有模型 token、GitHub 写凭据或私钥；不写 canonical。开发隔离不增加产品并发。 |
| 15 algorithms；16 complexity | 一层、有限的子记录；S02 依据实测选择 carrier/资源前提。交付上限不是读取前的内存保证。S08/S10 必须在大规模物化前执行已批准的来源前提。 |
| 18 cache；21 inspection | 既有的调用期验证与来源身份不变；缓存的观察不能使来源合格或产生权威。既有 explain/JSON 保持只读、形状兼容；其 owner 见上表。 |
| 20 diagnostics | 此处核实 S28xx 可用、`PIE-S2604` 基线与 Unnest 继承的现行 JOIN 诊断（9511 输出；开放项 O3 已处置）；S03 冻结实际的模式/上下文消息。诊断顺序、位置与无关的码仍受既有合同约束。 |
| 23 conformance；24 differential | 上文的原值/occurrence 反例供真实 producer 与独立消费者测试使用。既有平面 PostgreSQL/MySQL 行为仍是回归覆盖。 |
| 28 readiness/deferred owners；29 route | Post70 输入未闭合：合成基线 `9511f135` 已绑定并保持为 B1 基线；O1、O2、O4 由所有者 2026-10-27 批准的 post70 修正承接（S03 之后的普通提交；O2 中 lead 按所有者“暂不改 Teach 机制”的回答暂缓的 G18 除外），O3 已处置，各自的 owner 与最晚点见“开放项与 owner”一节。owner 表与 B1–B9 路线为每个尚未实现的消费者命名。没有把任何延期消费者报告为可用。 |
| 30 repair/stops | C200/F180/D250/S12；开局重建的 S02 账为 C4/F2/D1/S0，含两次保守计入的报告更正。Teach 开局为 2 jobs / 13,520 core-seconds，上限 500 jobs / 2,000 core-hours / 并发 16。原失败运行与记录保留。 |

## Health、检查与交接

实际基线 health 产物报告 `WATCH` 与 `INSUFFICIENT_EVIDENCE`，可比历史样本为零。每个 Python
运行时收集/选中/执行 22,728 个节点：22,709 通过、19 跳过。有 18 个长节点信号、4 个结构性
fewer-units 信号与 2 个 imbalance-watch 信号。成本数据不完整。这些观察不授权调度器、拓扑或
worker 策略变更。

适用的工程教训要求直接消费者闭合、确切 pin 读者、独立收集与合成 tree 的验证。获取整合预留在
既有的 S12 复查与 S22，位于 S24 的仅审计边界之前。复用合适的新鲜见证；本准备片不额外增加
强制的数据库/全量运行。

S01 本身只改文档：检查其链接与确切的源码/CI 引用；B1 的最终验证在集成主机上运行，按批次实际改动闭包选定。S02
消费绑定的 pin/读者及其保留的 native/replay 证据。S03 消费空闲诊断码段、`PIE-S2604` 基线、
现行 JOIN 诊断基线、反例与读者清单（含上表的 13 处闭合分派遍历）。一次所有者回答区分了空/不存在/全 NULL 容器，但误读了 Collect 与调用的区别，
也没有预测 JOIN 行数。S03 保留 D71.01/D71.02，并增加一个最小示例与诊断说明；这是有限的所有者
反馈，不是群体理解性结论。
