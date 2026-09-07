# Phase 64 Flat Relational Algebra Product/Phase Initiation Gate v3, Source Audit, Architecture And Route Lock v1

## Decision

Phase 64 **Flat Relational Algebra** 的 phase-start audit 与 design closure 均已完成。
Gate 0 baseline、live source audit、三张 ledger、65–97 pull-forward 分类、新增
external reference records、独立复现的 counterexample evidence，以及用户裁决的
决策集 D01–D08 都已固定，据此锁定 **11 条 numbered Slice** 的 Phase-64 route。

本地 publication candidate 阶段：

```text
Phase 63 = COMPLETED
Validation/Test Performance Optimization Interlude II = COMPLETED
Phase 64 = ACTIVE / SLICE 1 CANDIDATE
Phase 64 Slice 1 = CURRENT / ROUTE LOCK CANDIDATE
Phase 64 Slices 2–11 = NOT IMPLEMENTED
```

本 Slice 的 natural exact-head CI 成功后，无需 status-only follow-up commit：

```text
Phase 64 = ACTIVE
Phase 64 Slice 1 = COMPLETED / PUBLISHED
Phase 64 Slice 2 = NEXT / NOT IMPLEMENTED
Phase 64 Slices 3–11 = NOT IMPLEMENTED
```

Slice 1 只做文档与 static assurance：不新增 production 行为、不新增 grammar
production、不实现任何 Phase-64 语言特性。前一份 Phase-64 提案预先固定的
authored syntax 与 16-slice route 记为 proposal，不是 approved design authority；
本文件的 route 长度为 **11**，由 §Route Selection 的比较得出。

## Starting Authority

Gate 0 重新绑定的唯一 live baseline：

```text
commit = bb52135038973b40638ff86367ba478846f898c6
tree   = 8244d6ecf9c98af0895992a39cac93dd9352481d
parent = 461e5ef59b689b61a1815f039b93331bed3ac576
subject = Complete validation performance interlude II
natural CI = 34002966434
event / branch / attempt / conclusion = push / main / 1 / success
Python 3.12 job = 101405014835 / success
Python 3.13 job = 101405014976 / success
```

`HEAD == main == origin/main == live remote main`，divergence `0/0`，tracked /
index / untracked inventory 均为空，无 active Git operation，`NUL` absent。

起始 lifecycle 与 inventory（经现有 reader 重新绑定，非新建 reader）：

```text
Phase 63 = COMPLETED
Validation/Test Performance Optimization Interlude II = COMPLETED
Phase 64 = NEXT / NOT IMPLEMENTED
Phase-64 numbered route = absent
production Python = 179
test Python = 428
collected tests = 11526
```

`production Python = 179` 与 `test Python = 428` 由既有专属 inventory reader
`tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py`
拥有；本 audit 未新增 whole-repository inventory scan。

## Product/Phase Initiation Gate v3 Coverage

使用现行 [Phase Initiation Gate v1](../architecture/phase-initiation-gate-v1.md)
的 30 个 field。答案为 Phase-64 独立重绑定，不复用 Phase-63 答案。依赖产品裁决的
field 在 decision checkpoint 前曾记为 `OPEN` 并按 Gate 规则阻断 design closure；
D01–D08 落定后全部作答。

| # | Field | Phase-64 answer | Evidence / owner |
| ---: | --- | --- | --- |
| 1 | Live authority | 上节 baseline；authority 为 live Git + natural exact-head CI，而非本文档 | Gate 0；`AGENTS.md` |
| 2 | User/product outcome | 用户可在一个 relation body 中书写 generic `ON` JOIN 与 `CROSS/RIGHT/FULL/SEMI/ANTI`，对既有命名关系做 DISTINCT 与显式 `ALL`/`DISTINCT` 的 `UNION`/`INTERSECT`/`EXCEPT`，并让这些输出继续经既有 LET/WHERE/GROUP/satisfying/WINDOW/QUALIFY/projection/ORDER/LIMIT 尾部完成。成功**不包含** SQL 生成、执行、优化、嵌套关系与 inline path-group/outer-capture 语法 | D01–D08；§Product Exits |
| 3 | Semantic reference model | 有限 BAG + SQL NULL；predicate 三值逻辑与 row-equivalence 分离；已由 `project_bag_null_oracle.py` 与 SQLite 独立复现 | F13; C01–C10 |
| 4 | Identity model | 复用 `ProjectJoinUseIdentity`(owner+join_position)、`ProjectTraversalStepUseIdentity`、`ProjectModuleRowFieldIdentity` 的 `RELATION_OUTPUT` 域；新算子 occurrence identity 待 D06 | F02, F05, F06 |
| 5 | Construction states | 复用现有 closed concrete / typed non-concrete terminal 模式（`ProjectQueryBlockNonConcreteReason`、`ProjectEffectiveOutputTerminalReason`、`ProjectIRQueryBlockTerminalReason`） | F07, F08, F09 |
| 6 | Proof posture | asserted / derived / verified / observed / unknown / disproven 分离；本文件的 counterexample 为 disproven-by-example，finite case 不证明全称等式。single-match 另立第三态「合法但未证明」，见 #20 | C01–C10；D05 |
| 7 | Layer ownership | 每个新 fact 归属 semantic stage、Project IR 或 inspection 之一；不新建第二套 property engine | F10, F11 |
| 8 | Dependency direction | semantic → IR → verification → inspection 单向；下游不得重新决定语义 | `layering-and-coupling-laws-v1.md` |
| 9 | Versioning and migration | Project JSON v2、CLI text/JSON、`AUTHORED_JOIN_DEFERRED`、既有 inspection format 保持不变；新增只允许 additive private | Phase-63 public exit |
| 10 | Requirements vs capabilities | Phase 64 保持 target-neutral；backend legality 与 capability 仍属 Phase 65+ | Handoff Q11 |
| 11 | Interchange | 无新的 process/serialization/device 边界；private canonical bytes 仅用于 observation | Phase-63 Slice 15 |
| 12 | Execution | 无 execution；Phase 64 不引入 evaluator、optimizer 或 backend selection | `AGENTS.md` 产品边界 |
| 13 | Resource lifecycle | `NOT_APPLICABLE` — Phase 64 不获取进程外资源；reason=纯内存语义构造；owner=Phase 68 | Roadmap v6 |
| 14 | Security and trust | 无新 trust boundary；trusted opened bytes / package identity 不变 | `path_trust.py`, `trusted_source.py` |
| 15 | Algorithms and data structures | 复用既有 FD/key/grain closure index（`ProjectValueFDIndex`、`ProjectIROutputFDIndex`、`ProjectGrainDependencyIndex`）；新算子只增加 transfer rule，不新增 search | F10 |
| 16 | Complexity posture | 每 hop O(left fields + right fields) 的 field 传播；set operation 为 O(操作数 × 字段数) 的 schema 对齐；无 join-order search（Phase 88） | F10, F11 |
| 17 | Invalidation | 每个新 fact 必须声明 producer / retaining root / consumer / invalidation trigger；复用 Slice-14 verifier 与 invalidation | F09 |
| 18 | Cache | `NOT_APPLICABLE` — 无持久 observation cache，重算即可；reason=snapshot-local；owner=Tentative Phase 91 | Roadmap v6 |
| 19 | Concurrency | `NOT_APPLICABLE` — 构造为确定性单线程纯函数；reason=无共享可变状态；owner=Phase 68 | 现有 pure boundary tests |
| 20 | Diagnostics | 现有 78 个 `PIE-` code、消息与顺序不变；新增码全部为 additive `PIE-S2xxx`。未被静态证明但**合法**的 single-match requirement 在 `LOOSE`/`CHECKED`/`STRICT` **三种模式下一律为 `WARNING`**，不随 mode 升级为 `ERROR`；非法组合仍为 `ERROR` 且属不同码 | D05；`errors.py:12-16`；`cli_json.py:64` |
| 21 | Inspection | read-only inspection 与构造分离；复用 VERIFIED-only、winner-free query 与 additive private format | Phase-63 Slice 15 |
| 22 | UX | authored surface 沿用现有 `<kind> join x as b:` 缩进块，body 内 `FROM` 之后允许 `ON` 交替（与既有 `VIA` 并列）；kind 关键字扩展；set operation 为顶层子句且 `ALL`/`DISTINCT` 必须显式书写；组合边界复用**既有命名关系**，不新增 inline path-group 语法 | D01, D02, D03, D04 |
| 23 | Conformance | 无新的 normative public contract；conformance vector 的可移植性属 Phase 76–80 | Roadmap v6 |
| 24 | Differential and fuzz assurance | Slice 1 使用既有 `project_bag_null_oracle` 与 stdlib SQLite 复现 counterexample；不新建 differential subprocess family | C01–C10; F13 |
| 25 | Packaging | zero delta：无 dependency、lockfile、workflow、generated、golden、version 变更 | §Zero-Delta |
| 26 | Support matrix | Python 3.12/3.13 不变；无新 dialect/edition | 既有 CI matrix |
| 27 | Release / deprecation / EOL | `NOT_APPLICABLE` — 无 release surface 变更；reason=private-only；owner=Phase 69/82/83 | Roadmap v6 |
| 28 | Readiness and deferred owners | 三张 ledger + 65–97 atomic 分类见下 | §Ledgers, §Pull-Forward |
| 29 | Slice route | 11 条 numbered Slice，逐条记录 prerequisites、production/test owner、contract、non-goals、acceptance 与 handoff | §Route Selection |
| 30 | Repair and stop conditions | budgets：doc/static repair 12、mechanical 12、validator starts 4、production repairs 0；stop 条件含未决 product decision | 本任务授权 |

所有 30 个 field 均已作答；没有 `UNKNOWN`。四处 `NOT_APPLICABLE`（#13、#18、#19、#27）
各自给出确切理由与后续 owner，且都不掩盖缺失的语义定义。

## Reusable Question-Set Coverage

用户累积的 12 组 phase-start 问题在本文件的覆盖位置：

| Group | 覆盖位置 |
| --- | --- |
| A 产品/范围 | §Decision、Gate #2、D01/D02/D04 |
| B 现状/历史 | §Live Source Audit F01–F13、§Ledgers |
| C 全 roadmap pull-forward | §Pull-Forward 65–97 |
| D 决策/自由度 | §Decision Packet；`IMPLEMENTATION_FREEDOM` 未进入 packet |
| E 语义/身份 | Gate #3/#4、§Semantic Laws、C01–C10 |
| F 层次/组合 | Gate #7/#8/#17、F07–F11 |
| G 算法/成本 | Gate #15/#16、F10 |
| H 状态/资源/信任 | Gate #5/#12/#13/#14、D05 |
| I UX/诊断/观察 | Gate #20/#21/#22、D04 |
| J 兼容/生态/发布 | Gate #9/#25/#26/#27、§Zero-Delta |
| K 参考/保证 | §External Review R17–R25、§Counterexamples |
| L 路线/验收/变更 | Gate #29/#30（decision 后进行） |

八项 cross-cutting 附加要求的覆盖：observable equivalence/algebra 见 §Semantic
Laws；minimal counterexample 与组合闭合见 C01–C10；unknown 与 obligation 的分离
见 D05；error/evaluation effect 见 Gate #6 与 L07；safety/liveness 与 atomic
publication 见 Gate #5；evolution/reversibility 见 Gate #9；evidence strength 与
independent validation 见 §Counterexamples 的复现方法说明；total workflow/resource
cost 见 Gate #15/#16 与 §Pull-Forward。

## Live Pietto Source Audit

每条 finding 给出 exact seam，而非仅文件名。

| ID | Exact root | Finding | Phase-64 consequence |
| --- | --- | --- | --- |
| F01 | `grammar/Pietto.g4:271`, `src/pietto/ast_nodes.py:528,545`, `src/pietto/ast_builder.py:540` | authored JOIN kind 仅 `INNER`/`LEFT`；`joinClause` 的 body 只有 `FROM` + 零个或多个 `VIA`；无 ON、无 generic right input | generic JOIN 与新 kind 均需新 grammar；D01 已定为扩展现有 `joinBody` |
| F02 | `src/pietto/_project/project_relationship_uses.py:171,183` | `ProjectJoinUseIdentity = owner + join_position`；`ProjectTraversalStepUseIdentity = join + step_position` 已存在 | 不需要另铸 parallel JOIN identity；VIA hop 已有从属 identity |
| F03 | `src/pietto/_project/project_ir_joins.py:1618-1665` | JOIN region 以 `accumulated` 为左输入逐 hop 展开；`kind = ProjectIRBinaryJoinKind(use.kind.value)`（`:1448`）对 **每一个** hop 复制 authored kind | 旧 VIA 语义确认；新 kind 不得照抄该循环（见 L03/L04） |
| F04 | `src/pietto/_project/project_ir_joins.py:1236-1266,1448-1470` | INNER 的 `NON_NULL` 强化只在字段位置出现在 `condition.correspondences` 且此前未被 null 化时施加 | 该证明根是 null-rejecting 等值对应，不是「这是 JOIN」；generic ON 不继承（C04） |
| F05 | `src/pietto/_project/project_relationship_conditions.py:58-64` | `ProjectRelationshipConditionScope` 已保留 `RELATIONSHIP_BASE_MATCH` / `JOIN_LOCAL_ON_REFINEMENT` / `POST_JOIN_FILTER` | refinement 与 generic ON 的 scope 座位已存在，无需第三套 scope 模型 |
| F06 | `src/pietto/_project/module_attribution.py:239-265,1717-1723` | `ProjectModuleRowFieldIdentity` 的 `RELATION_OUTPUT` 域仅需 `(owner, kind, field_position, name)`，且已有不依赖 `SelectItem` 的铸造点 | set/DISTINCT output 可直接使用该域，无需伪造 SELECT AST |
| F07 | `src/pietto/_project/project_final_outputs.py:632-690` | 但 `ProjectCompletedOutputField` 强制绑定 `select_fact`、`item: SelectItem` 与 `definition.select_items[ordinal]` | set-operation 输出无法复用该 constructor；需要同域、非 SELECT 的第二个 output-field 构造者（D06） |
| F08 | `src/pietto/_project/project_query_block.py:195-197` | row-source sum 当前恰为 `ProjectExistingRelationRowSource \| ProjectVerifiedJoinedRowSource` | Handoff Q1 的扩展点确定；新 variant 不得把所有 output 提升为 relationship endpoint |
| F09 | `src/pietto/_project/project_completion.py:145-152,575-585`；`src/pietto/_project/project_query_block_ir.py:963-969,2582-2598` | `EFFECTIVE_UPSTREAM_JOIN_UNSUPPORTED` 由「JOIN 声明的上游仍为 recoverable-pending」触发；`EFFECTIVE_JOIN_INPUT_REBIND_UNSUPPORTED` 由 stale active join input 触发 | 两者是 Phase-64 必须解除的确切边界，且都是真实 typed diagnosis，不可当作可丢弃的错误 |
| F10 | `project_row_keys.py:60-72`, `project_value_fds.py:222,662`, `project_grain.py:39-62`, `project_ir_relational_properties.py:107-160` | key（`STRICT`/`LAX`、`NULLS_DISTINCT`/`NULLS_NOT_DISTINCT`）、value-FD closure index、grain factor/closure、IR 侧 value class/key/FD 均已存在 | 复用既有 kernel；Phase 64 只加 transfer rule，不建第二个 property engine |
| F11 | `src/pietto/_project/project_grain.py:48-61` | `ProjectGrainOriginKind` 仅 `SOURCE_ROW_DOMAIN` / `GROUPED_RESULT` / `GLOBAL_AGGREGATE`；`ProjectGrainFactorKind` 仅 `SOURCE_DOMAIN` / `GROUP_DOMAIN` | DISTINCT 商域与 set-operation 备选域没有既有 origin；不得伪造 `GROUPED_RESULT`（D07） |
| F12 | `src/pietto/semantic/model.py:71-86`；`project_relationship_conditions.py:45,720-755` | **历史基线事实**：`ValueType` 分别携带 `resolved_type` 与 `nullability`；等值类型身份按 kind/name/symbol 精确比较，且 relationship 比较把 `Any/Bytes/Decimal/Json` 显式推迟 | 该推迟表是 relationship 比较的历史边界，**不是** Phase-64 row-equivalence 规范；后者由 D07 独立划定，且不因此顺带放宽 relationship 比较 |
| F13 | `src/pietto/_project/project_bag_null_oracle.py:1-267` | 已存在纯有界 BAG/NULL oracle，但仅支持 `INNER`/`LEFT` 与等值对应 | Slice 1 复用它做 INNER/LEFT 证据；其余 kind 由 stdlib SQLite 独立复现，不扩展 production |

历史断言与真实语义缺陷的分离：F09 的两个 terminal 是**当前真实**的 typed
diagnosis（不是 stale 断言）；`AUTHORED_JOIN_DEFERRED`（`row_lineage.py:57`、
`model.py:645`）是**历史事实**，Phase 63 已在其上叠加完成语义，Phase 64 不得整体
移除或改写它。

## Ledgers

### CURRENT_PRODUCTION

| Item | Owner root | State |
| --- | --- | --- |
| authored INNER/LEFT relationship JOIN + VIA | `ast_nodes.JoinClause`, `project_relationship_uses` | existing |
| accumulated-left binary JOIN region | `project_ir_joins.build_project_ir_join_region` | existing |
| relationship base condition（等值合取、TRUE-only、null-rejecting） | `project_relationship_conditions` | existing |
| 出现完整的 joined row shape 与有效 nullability | `project_ir_properties`, Phase-63 Slice 6 | existing |
| key / value-FD / grain / fanout / multifact 证据 | `project_row_keys`, `project_value_fds`, `project_grain`, `project_multifact` | existing |
| WHERE / GROUP / satisfying / WINDOW / QUALIFY / projection / ORDER / LIMIT | Phase-63 Slices 8–12 | existing |
| 项目级 effective-output ledger 与 completed semantics | `project_completion`, `project_final_outputs`, `project_completed_semantics` | existing |
| Query-block Project IR、verification、invalidation、inspection、pure boundary | Phase-63 Slices 14–15 | existing |

### CURRENT_READINESS

| Item | Retained root | Readiness ≠ acceptance |
| --- | --- | --- |
| `JOIN_LOCAL_ON_REFINEMENT` / `POST_JOIN_FILTER` condition scope | `project_relationship_conditions:58-64` | 枚举存在；无 producer/consumer |
| `ProjectTraversalStepUseIdentity` | `project_relationship_uses:183` | identity 存在；未被新 kind 使用 |
| `RELATION_OUTPUT` 身份域的非 SELECT 铸造点 | `module_attribution:1717` | 可用；未被 set output 使用 |
| 有界 BAG/NULL oracle | `project_bag_null_oracle` | 仅 INNER/LEFT 等值 |
| `ProjectOptionalGrainFactorReadiness.NOT_CONSTRUCTIBLE_BEFORE_LOGICAL_JOIN` | `project_grain:63-67` | 明确标注为未来 JOIN/nulling authority |

Readiness 不等于 compiler acceptance、backend support、runtime behavior 或
release authority。

### RETAINED_LATER

保留给 Future Roadmap v6 既有 owner，不在 Phase 64 转移：见 §Pull-Forward。
未发生任何 public/backend/execution/release ownership 的静默重指派。

## Whole-Roadmap Pull-Forward Audit

每个已知 owner 65–90 与 tentative 91–97 都被单独覆盖。分类互斥。

| Owner | Atomic item | Class | Reason |
| ---: | --- | --- | --- |
| 64 core | Phase-64 IR **实际保留** 每个 condition 与其 scope、field mapping、source span、显式输出与 single-match obligation | `IMPLEMENT_NOW` | 这是本阶段自身的实现职责，不是对 Phase 65 的前移；Slices 3、7、9、10 拥有 |
| 64 core | verification/inspection **证明** 上述保留是精确的 | `IMPLEMENT_NOW` | Slice 10 的独立验证与 VERIFIED-only 观察 |
| 65 | Phase-65 对上述事实的**消费契约**（lowering 无需重新决定语义） | `CONTRACT_ONLY_NOW` | 只记录消费方需要什么，不冻结承载形状（D08） |
| 65 | 构造 `ProjectSQLPlan` 及其 SQL 分解、参数、alias 与 legality 机制 | `DEFER_BY_NECESSITY` | 缺的是 SQL planning/legality 接口本身：无 plan 节点代数、无参数/占位符模型、无 alias 作用域与生成规则、无 legality/capability 判定面。这与「尚未选定后端」无关 |
| 66 | PostgreSQL/MySQL 多关系 SQL 与 Project emit-SQL | `DEFER_BY_NECESSITY` | 先决条件为 Phase 65 plan |
| 67 | 结果形状、hidden field、nullable/provenance 与 check-vs-executable 区分 | `CONTRACT_ONLY_NOW` | 新算子必须声明哪些 field 对用户可见；Arrow contract 本身属 67 |
| 68 | executor SPI、ADBC/DBAPI、streaming、cancellation、backpressure | `OUT_OF_SCOPE` | 与 Phase-64 语义无共享不变量 |
| 69 | public alpha release engineering、unified safe entrypoints | `OUT_OF_SCOPE` | release authority 独立 |
| 70 | relation value/use/scope 与 named composition、path witness 的可复用性 | `CONTRACT_ONLY_NOW` | Phase 64 的 named operand 决定（D04）会约束 70；capture/LATERAL/nesting 不实现 |
| 70 | outer capture、EXISTS/IN、LATERAL、bounded decorrelation、effect authority | `DEFER_BY_NECESSITY` | 需要 open/composite plan 模型 |
| 71 | NestedRelation、Collect、Unnest、flatten、nested Arrow | `OUT_OF_SCOPE` | 平坦代数不产生嵌套域 |
| 71 | outer/inner grain 的区分不被本阶段意外冻结 | `CONTRACT_ONLY_NOW` | grain origin 扩展（D07）必须为嵌套留出空间 |
| 72 | 基础 positional 类型兼容 + nullable 传递 + 精确 row-equivalence 支持域 | `IMPLEMENT_NOW` | set operation 无此则无法定义；支持域按 D07 划定（含精确同参 `Decimal(p,s)`），不沿用历史 relationship 比较推迟表 |
| 72 | advanced equality/coercion、temporal/range/ASOF relationship | `DEFER_BY_NECESSITY` | 需要 advanced type work |
| 73 | 现有 fanout/chasm/`AGGREGATE_ALGEBRA_REQUIRED` 证据在新算子上继续成立 | `CONTRACT_ONLY_NOW` | 不得因新算子而伪造 aggregate repair |
| 73 | aggregate algebra/state、grouping extension、reaggregation | `OUT_OF_SCOPE` | Phase-63 已明确不转移 |
| 74 | identity/dependency 事实可被资产消费而不重解析名字 | `CONTRACT_ONLY_NOW` | 新算子的 occurrence identity 必须可寻址 |
| 74 | reusable local semantic assets、derived relationship、function/plugin SPI | `OUT_OF_SCOPE` | 需要 asset 模型 |
| 75 | 每个新 authored construct 保留 exact span 与 typed diagnostic | `CONTRACT_ONLY_NOW` | `ast_builder` 已对所有节点写 span（F01），新产生式必须延续 |
| 75 | formatter、LSP、editor、syntax edition/migration | `OUT_OF_SCOPE` | 工具层独立 |
| 76–79 | PostgreSQL/MySQL/SQLite/DuckDB 深度适配 | `DEFER_BY_NECESSITY` | 需要 Phase 65/66 plan 与 backend 能力模型 |
| 76–79 | 哪些 conformance vector 是可移植的（`INTERSECT ALL`/`EXCEPT ALL` 在 SQLite 缺失即为反例） | `CONTRACT_ONLY_NOW` | 本文件已记录该可移植性证据（C09） |
| 80 | pandas/Polars/NumPy/SciPy/Matplotlib 互操作 | `OUT_OF_SCOPE` | 需要 Arrow/result contract |
| 81 | 独立 oracle、counterexample、observation 边界 | `IMPLEMENT_NOW` | 本 Slice 已建立并复用（C01–C10、F13） |
| 81 | 高强度 real-DB/differential/metamorphic/fuzz/performance 战役 | `DEFER_BY_NECESSITY` | 需要 execution |
| 82 | public schema/API/CLI/syntax/support-matrix 冻结 | `OUT_OF_SCOPE` | Phase 64 无 public delta |
| 83 | 1.0 release audit | `OUT_OF_SCOPE` | release authority 独立 |
| 84 | 远程资产/registry/transport/signing/trust | `OUT_OF_SCOPE` | Pietto 明确不做远程加载 |
| 85 | dependency solver、canonical lockfile | `OUT_OF_SCOPE` | 无 solver |
| 86 | RDKit/geospatial/sparse/DLPack/device 适配 | `OUT_OF_SCOPE` | 无 domain value 模型 |
| 87 | asserted / proved / observed constraint 的分离在新算子上继续成立 | `CONTRACT_ONLY_NOW` | `ProjectConstraintEvidenceOrigin`/`Trust`/`EnforcementPosture` 已存在（F10） |
| 87 | catalog/statistics/runtime data quality/chase | `OUT_OF_SCOPE` | 需要 catalog |
| 88 | rewrite premise 必须显式（每条 law 记 LHS/RHS、观察域、前提、证据强度） | `CONTRACT_ONLY_NOW` | 见 §Semantic Laws；无 memo、无 join-order search |
| 88 | logical optimizer memo、join-order/hypergraph search | `OUT_OF_SCOPE` | 需要 cost 模型 |
| 89 | Yannakakis/WCOJ/Free Join/predicate transfer | `OUT_OF_SCOPE` | physical layer |
| 90 | Rust kernel、PyO3/maturin、parity、wheel matrix | `OUT_OF_SCOPE` | 无 profiling 驱动的需求 |
| 91 | invalidation 与身份不被意外冻结为持久 cache 身份 | `CONTRACT_ONLY_NOW` | Gate #18 记为 `NOT_APPLICABLE` 并指向 91 |
| 92 | recursion/fixpoint 假设不被冻结（平坦代数不隐含非递归性为语言约束） | `CONTRACT_ONLY_NOW` | 只冻结当前 DAG 现实，不冻结未来 |
| 93 | 形式化 rewrite certification | `DEFER_BY_NECESSITY` | 本 Slice 只记 premise 与反例，不做证明 |
| 94 | cloud/federation 语义与传输 | `OUT_OF_SCOPE` | 无分布模型 |
| 95 | DML/DDL/migration | `OUT_OF_SCOPE` | Pietto 为编译器 |
| 96 | governance/security policy 语义 | `OUT_OF_SCOPE` | 无 policy 模型 |
| 97 | continuous/streaming 语义 | `OUT_OF_SCOPE` | 有限 BAG 语义不隐含流式假设 |

表中 `64 core` 两行是**本阶段自身的实现职责**，不计入跨阶段 pull-forward；跨阶段的
`IMPLEMENT_NOW` 恰为 Phase-72 与 Phase-81 两项。没有 placeholder abstraction 被提出；
每个 `CONTRACT_ONLY_NOW` 都有当前不变量或指名的未来 consumer。资产计数未被照抄：`production Python = 179` 与
`test Python = 428` 由 §Starting Authority 的既有 reader 实测。

## External Reference Review

Phase-63 的 R01–R16（`2026-09-02` snapshot）继续由那份 immutable contract 拥有，
其耐久综合见 [product design lessons](../references/product-design-lessons-v1.md)；
本节只新增 Phase-64 特有关切的记录，审计日期 `2026-09-06`。每条使用现行 11 字段。
`ADOPT`/`ADAPT`/`REJECT`/`DEFER` 是 Pietto 设计处置，不是产品对等声明。

### R17 PostgreSQL set operations and outer-join reordering legality

1. Snapshot/date：`postgres/postgres@798bdcae89debabc59fa8afc6d690fec584db32f`（`2026-09-05T00:12:40Z`）；stable docs `18`（页面标注 `2026-08-13`）；审计 `2026-09-06`。[table expressions](https://www.postgresql.org/docs/18/queries-table-expressions.html)、[SELECT](https://www.postgresql.org/docs/18/sql-select.html)、[optimizer README](https://github.com/postgres/postgres/blob/master/src/backend/optimizer/README)。
2. Problem/constraints：在允许外连接的情况下，仍需正确枚举合法的连接顺序。
3. Semantics/identity：`INTERSECT ALL` 为 `min(m,n)`，`EXCEPT ALL` 为 `max(m-n,0)`，`UNION` 默认去重且 `DISTINCT` 可显式书写；`ON` 在连接前处理、`WHERE` 在连接后处理，对外连接结果不同。
4. Layering：optimizer README 用 `SpecialJoinInfo` + `join_is_legal` 把合法性检查与搜索分离。
5. Algorithms/complexity：identity 1/2/3 为可枚举的重写前提，而非无条件代数律。
6. Interface/version/capabilities：set-operation 操作数不得直接携带 `ORDER BY`/`LIMIT`，加括号后可以；`INTERSECT` 比 `UNION` 结合更紧。
7. Testing/lifecycle：不适用（文档与规划器源码）。
8. Pitfalls：identity 3 仅在 `Pbc` 对 B 的某列 strict（拒空）时成立；把 inner join 移入/移出外连接的可空侧是明确非法的。
9. Disposition：`ADAPT`。
10. WHAT_NOT_TO_COPY：`SpecialJoinInfo`/planner 数据结构、join 搜索、cost 模型、`DISTINCT ON`、以及把无条件 `is_associative` 标志加到 JOIN 上。
11. Pietto owner affected：D02、D03、L01–L06；Phase 88 拥有搜索。

### R18 Substrait JoinRel / SetRel / CrossRel

1. Snapshot/date：`substrait-io/substrait@8ca7db0e8e0969b78fc54c65d8587796fa0363ab`（`2026-09-03T19:10:08Z`）；审计 `2026-09-06`。[logical relations](https://substrait.io/relations/logical_relations/)。
2. Problem/constraints：为跨引擎交换定义与目标无关的逻辑关系。
3. Semantics/identity：`JoinRel` 枚举 12 个 join type（含 `LEFT_SEMI`/`LEFT_ANTI`/`LEFT_SINGLE`/`RIGHT_*`/`LEFT_MARK`/`RIGHT_MARK`），并把 `expression` 与 `post_join_filter` 分成两个字段；`SetRel` 的 `MINUS_PRIMARY_ALL` 为 `max(0, m - sum(n1..n))`，`INTERSECTION_MULTISET_ALL` 为 `min(m, n1..n)`，`UNION_ALL` 为 `m + n1 + … + n`；`CrossRel` 输出顺序为「左输入字段后接右输入字段」。
4. Layering：逻辑关系与 emit/remap 分离。
5. Algorithms/complexity：不适用（无算法规定）。
6. Interface/version/capabilities：`SINGLE` 变体即「右侧至多一个匹配」的一等公民表达；`MARK` 变体产出可空布尔列。
7. Testing/lifecycle：不适用。
8. Pitfalls：positional-only 的字段引用不适合作为用户可见身份。
9. Disposition：`ADAPT`。
10. WHAT_NOT_TO_COPY：protobuf 公开暴露、positional-only 用户身份、physical relation、fallback extension，以及「12 个 join type 全部支持」这一范围假设。
11. Pietto owner affected：D02、D03、D05、D06。

### R19 Apache Calcite RelMdUniqueKeys

1. Snapshot/date：`apache/calcite@ec283fb583ec08b3ceb984bdbf359589ec9384bb`（`2026-09-05T17:17:31Z`）；审计 `2026-09-06`。[`RelMdUniqueKeys.java`](https://github.com/apache/calcite/blob/main/core/src/main/java/org/apache/calcite/rel/metadata/RelMdUniqueKeys.java)。
2. Problem/constraints：从计划结构派生唯一键元数据。
3. Semantics/identity：`Union` 仅在 `!all` 时以全部列为唯一键；`Intersect` 采「任一输入的任一唯一键即为结果唯一键」；`Minus` 的唯一键恰为第一个输入的唯一键；`Join` 仅当一侧在等值列上唯一 **且** 另一侧不产生 null 时才传递另一侧的键。
4. Layering：元数据 provider 与算子分离。
5. Algorithms/complexity：带 `limit` 的有界枚举。
6. Interface/version/capabilities：`ignoreNulls` 参数在 SetOp 分支未被使用。
7. Testing/lifecycle：不适用。
8. Pitfalls：把 key 传递与 FD 传递混为一谈；Calcite 未对 `Union` 主张 FD 继承。
9. Disposition：`ADAPT`。
10. WHAT_NOT_TO_COPY：通用规则规划器、ambient metadata 单例、Java 元数据 handler 机制，以及把 `ignoreNulls` 的默认行为当作 Pietto 的 NULL 策略。
11. Pietto owner affected：D07、L08–L10。

### R20 DuckDB SEMI/ANTI joins and set operations

1. Snapshot/date：`duckdb/duckdb@e3946f2327a3cc622e1ec7fe71d51de49f93e61d`（`2026-09-04T13:50:35Z`）；stable 文档页审计 `2026-09-06`。[FROM/JOIN](https://duckdb.org/docs/stable/sql/query_syntax/from.html)、[set operations](https://duckdb.org/docs/stable/sql/query_syntax/setops.html)。
2. Problem/constraints：把 SEMI/ANTI 与 `BY NAME` 等提升为 authored 语法。
3. Semantics/identity：`SEMI JOIN` 返回「左表中至少有一个匹配」的行且**只含左表列**；`ANTI JOIN` 返回无匹配的左行、同样只含左列；vanilla set operation 用集合语义，`ALL` 变体用袋语义；传统三个 set operation 按**列位置**对齐并要求列数相同，`UNION BY NAME` 按名字对齐且缺列补 NULL。
4. Layering：authored 语法直接映射到逻辑算子。
5. Algorithms/complexity：不适用。
6. Interface/version/capabilities：`ASOF`/`POSITIONAL`/`LATERAL` 为独立 authored 形式。
7. Testing/lifecycle：不适用。
8. Pitfalls：SEMI/ANTI 不发布右侧字段，因此**不能**用同一个循环连续遍历下一跳。
9. Disposition：`ADAPT`。
10. WHAT_NOT_TO_COPY：`NATURAL JOIN` 的名字启发式、`POSITIONAL JOIN`、隐式类型转换规则，以及 `ASOF`（属 Phase 72）。
11. Pietto owner affected：D02、D03、D04、L05。

### R21 Moerkotte, Fender, Eich 2013 — core search space enumeration

1. Snapshot/date：ACM SIGMOD 2013，DOI [`10.1145/2463676.2465314`](https://doi.org/10.1145/2463676.2465314)；ACM 页面在 `2026-09-06` 返回 HTTP 403，元数据经公开检索确认（Semantic Scholar、CMU 15-721 课程副本）。
2. Problem/constraints：重排超出普通 join 的算子（外连接、反连接）时并非所有顺序都有效。
3. Semantics/identity：提出三个 conflict detector；指出既有 NEL/EEL 与 SES/TES 方案仍会生成非法计划。
4. Layering：conflict detection 与枚举分离。
5. Algorithms/complexity：最后一个检测器在 core search space 内是完备的。
6. Interface/version/capabilities：明确不要求所有谓词拒空（比前人更宽松）。
7. Testing/lifecycle：不适用。
8. Pitfalls：其结论属于**优化器搜索空间**，不是用户可见语义；Pietto 当前无 join 重排。
9. Disposition：`DEFER`。
10. WHAT_NOT_TO_COPY：把 conflict detector 当作 Phase-64 的语义定义，或据此在无 cost 模型时引入重排。
11. Pietto owner affected：L01–L06 的前提记录；实现属 Phase 88。

### R22 Graph OPTIONAL patterns — Neo4j Cypher and SPARQL 1.1

1. Snapshot/date：Neo4j Cypher manual `current`、W3C SPARQL 1.1 Recommendation；均审计 `2026-09-06`。[OPTIONAL MATCH](https://neo4j.com/docs/cypher-manual/current/clauses/optional-match/)、[SPARQL 1.1](https://www.w3.org/TR/sparql11-query/)。
2. Problem/constraints：图查询中「整段模式可选」与「逐跳可选」的区别。
3. Semantics/identity：Cypher 明确「either the whole pattern is matched, or nothing is matched」，未匹配时对模式缺失部分给 `null`；其 `WHERE` 是模式描述的一部分，「will be considered while looking for matches, not after」。SPARQL 的 `OPTIONAL` 为左结合，`P OPTIONAL{A} OPTIONAL{B}` 等价于 `{P OPTIONAL{A}} OPTIONAL{B}`。
4. Layering：模式匹配与后续过滤分层。
5. Algorithms/complexity：不适用。
6. Interface/version/capabilities：整段可选是**显式书写**的结构，不是优化器改写。
7. Testing/lifecycle：不适用。
8. Pitfalls：把 `WHERE` 放到错误的 `OPTIONAL MATCH` 上会改变结果。
9. Disposition：`ADAPT`。
10. WHAT_NOT_TO_COPY：图数据模型、变量长度路径、`MINUS` 的图语义，以及把「整段可选」当作可由编译器自动选择的等价改写。
11. Pietto owner affected：D03（whole-path optionality 必须是 authored 的 hop/group 边界，见 C01）。

### R23 SQL equivalence reasoning — U-semiring and Cosette

1. Snapshot/date：U-semiring 论文 [`arXiv:1802.02229`](https://arxiv.org/abs/1802.02229)（2018，最终修订 2018-05-24），审计 `2026-09-06`；Cosette 指南 `https://cosette.cs.washington.edu/guide` 在 `2026-09-06` DNS 解析失败（`ENOTFOUND`），未取得内容。
2. Problem/constraints：判定 SQL 查询语义等价。
3. Semantics/identity：摘要声明其扩展 semiring 语义以支持无界求和与去重，覆盖「bags and sets 上求值的 SQL 查询以及各种完整性约束」，并据此形式化验证了 39 条改写规则。
4. Layering：形式化与实现（Coq）分离。
5. Algorithms/complexity：摘要未给出复杂度界。
6. Interface/version/capabilities：**摘要页未确立**其对 SQL NULL、三值逻辑或外连接的覆盖；本审计不作该主张。Cosette 的支持范围因站点不可达而**未确立**。
7. Testing/lifecycle：不适用。
8. Pitfalls：把「验证过 39 条改写」误读为「覆盖任意外连接与 NULL」。
9. Disposition：`DEFER`。
10. WHAT_NOT_TO_COPY：把外部等价判定器的结论当作 Pietto 语义授权；在未确立覆盖域时引用其为 NULL/外连接的 oracle。
11. Pietto owner affected：Phase 93；本 Slice 仅记录前提与反例。

### R24 DBSP

1. Snapshot/date：[`arXiv:2203.16684`](https://arxiv.org/abs/2203.16684)（2022-03-30 提交），审计 `2026-09-06`。
2. Problem/constraints：任意程序的增量视图维护。
3. Semantics/identity：以流计算语言建模，声称可表达完整关系查询、分组聚合、单调与非单调递归及流式聚合。
4. Layering：语言 + 通用增量化算法。
5. Algorithms/complexity：摘要未给出适用于本阶段的界。
6. Interface/version/capabilities：摘要**未说明** SQL NULL 与外连接的处理；不作该主张。
7. Testing/lifecycle：不适用。
8. Pitfalls：把增量化模型误当作基础语义定义。
9. Disposition：`DEFER`。
10. WHAT_NOT_TO_COPY：Z-set/流式表示作为 Phase-64 的 BAG 语义授权。
11. Pietto owner affected：Tentative Phase 91/92。

### R25 egg (equality saturation)

1. Snapshot/date：[`arXiv:2004.03082`](https://arxiv.org/abs/2004.03082)，POPL 2021；API 参考 `egg 0.11.0` 的 [`Condition`](https://docs.rs/egg/0.11.0/egg/trait.Condition.html) 与 [`ConditionalApplier`](https://docs.rs/egg/0.11.0/egg/struct.ConditionalApplier.html)；审计 `2026-09-06`。
2. Problem/constraints：以 e-graph 高效表示同余关系并做改写驱动优化。
3. Semantics/identity：e-class analysis 为领域知识提供接入点。
4. Layering：改写引擎与规则集分离。
5. Algorithms/complexity：饱和过程的成本由规则集决定。
6. Interface/version/capabilities：引擎提供 `Condition` 与 `ConditionalApplier`，可在改写时**运行期检查**使用者提供的条件；但运行期检查一个被提供的条件，不等于**证明**该改写及其前提是可靠的——可靠性仍由使用者负责。
7. Testing/lifecycle：不适用。
8. Pitfalls：把律登记为**无条件**重写规则时，带 NULL/外连接前提的等价类会不正确；`ConditionalApplier` 能表达前提，却不代表前提本身已被证明。
9. Disposition：`REJECT`（对 Phase 64）。这是**范围**决定——Phase 64 没有 memo、cost 模型或改写引擎——不是「egg 无法表达条件」的能力主张。
10. WHAT_NOT_TO_COPY：把 JOIN 律登记为无条件重写规则；本阶段每条律必须携带前提与观察域。
11. Pietto owner affected：L01–L10 的记录形状；引擎实现属 Phase 88/93。

### R26 Authoring surfaces — PRQL and Ibis

1. Snapshot/date：`ibis-project/ibis@05d2b293344e86cb41c1a426071734f7e270335a`（`2026-08-29T15:46:34Z`）与 `PRQL/prql@374d769c4177a5d374c3ed8f5b3a6678e9237e0d`（`2026-09-06T23:26:19Z`）；均审计 `2026-09-06`。[PRQL join](https://prql-lang.org/book/reference/stdlib/transforms/join.html)、[PRQL append](https://prql-lang.org/book/reference/stdlib/transforms/append.html)、[Ibis tables](https://ibis-project.org/reference/expression-tables)、`ibis/expr/types/relations.py`。
2. Problem/constraints：可读的管道式 join / set operation 书写。
3. Semantics/identity：PRQL 用 `join side:{inner|left|right|full} rel (condition)`，默认 `inner`，并提供 `(==col)` 自等值简写；其 set operation 为 **bag 语义**——`append` 等价于 `UNION ALL`，`remove` 等价于 `EXCEPT ALL`（逐条抵消重复行），`intersect` 等价于 `INTERSECT ALL`，去重需另行 `distinct`。Ibis 的默认**逐方法不同**：`ibis/expr/types/relations.py` 中 `union(self, table, /, *rest, distinct: bool = False)`、`intersect(self, table, /, *rest, distinct: bool = True)`、`difference(self, table, /, *rest, distinct: bool = True)`；`join(..., how="inner")`。
4. Layering：authored 表面与后端编译分离。
5. Algorithms/complexity：不适用。
6. Interface/version/capabilities：两者都把 kind 作为**具名参数**而非新关键字家族。两者的 set operation 默认**并不统一去重**：PRQL 全部为 bag 语义，Ibis 只有 `union` 默认保留重复，`intersect`/`difference` 默认去重。因此「生态一律默认 `DISTINCT`」不成立，不能作为任何 Pietto 默认值的依据。
7. Testing/lifecycle：不适用。
8. Pitfalls：PRQL 无 semi/anti；Ibis 的 `distinct(keep=...)` 会引入顺序依赖的赢家选择；同一生态内 `union` 与 `intersect` 的默认相反，正是隐式默认易错的证据。
9. Disposition：`ADAPT`。
10. WHAT_NOT_TO_COPY：`keep='first'/'last'` 这类顺序依赖的行选择（Pietto 禁止任意赢家）；Python 层的隐式类型强制。
11. Pietto owner affected：D01、D04。Pietto 要求显式书写 `ALL`/`DISTINCT` 是一项**产品决定**，其依据是本记录显示的默认值不一致与隐式去重的陷阱；它不是 fail-closed / no-winner 规则的推论。

### R27 Interface/conformance references — reasoned disposition

1. Snapshot/date：沿用 Phase-63 R01（MLIR）、R11（Android stable AIDL/VINTF/CTS）、R12（OpenHarmony/XTS）的 `2026-09-02` snapshot；Linux VFS 于 `2026-09-06` 评估但未取快照。
2. Problem/constraints：phase-start 是否需要新的接口/身份/一致性区分。
3. Semantics/identity：MLIR 的 typed IR + verifier 区分、AIDL/VINTF 的「接口 / 提供者清单 / 需求矩阵 / 一致性证据」四分，已分别由 R01 与 R11 吸收进现行架构文档与 Gate。
4. Layering：同上。
5. Algorithms/complexity：不适用。
6. Interface/version/capabilities：Phase 64 不新增跨进程接口、provider manifest 或 conformance suite。
7. Testing/lifecycle：现有 Ponytail review + natural CI 已覆盖。
8. Pitfalls：为对称而做仪式性长篇复核。
9. Disposition：`DEFER`（不新增记录）。Linux VFS 判为 `NOT_RELEVANT`：其贡献是内核对象生命周期与挂载命名空间，Phase 64 无资源生命周期（Gate #13 为 `NOT_APPLICABLE`）。
10. WHAT_NOT_TO_COPY：为凑数而引入的抽象。
11. Pietto owner affected：无；Phase 69/82/83 保留既有归属。

Apache DataFusion 的处置沿用 Phase-63 R04（`2026-09-02` snapshot），本次未刷新；
本文件不对 DataFusion 的当前实现行为作任何新主张。
所有测试保持 network-free；外部内容不授予 shell 或仓库写入权限。

## Semantic Laws And Rewriting Premises

不使用无条件的 `is_associative` / `is_commutative` 标志。每条律记录 LHS/RHS、
观察域（BAG 多重性 / 值 / 顺序 / 错误 / provenance）、字段映射、谓词自由输入、
拒空前提、类型与等价前提、约束与 effect 前提、证据强度、反例与 consumer。

| ID | LHS = RHS | Observation domain | Required premises | Evidence | Counterexample when premises drop |
| --- | --- | --- | --- | --- | --- |
| L01 | `A CROSS B` = `A INNER B ON TRUE` | BAG 多重性、字段映射（左后接右） | 无 | R17 明文；R18 `CrossRel` 顺序 | 无 |
| L02 | `A INNER B` = `B INNER A`（配合字段重映射） | BAG 多重性；**不含**输出字段顺序 | 谓词对两侧自由；无 effect | R17 | 若把字段顺序纳入观察域则不成立 |
| L03 | `(A LEFT B) INNER C on Pac` = `(A INNER C on Pac) LEFT B` | BAG 多重性、值 | `Pac` 只引用 A 与 C | R17 identity 1 | `Pac` 引用 B 时不成立 |
| L04 | `(A LEFT B on Pab) LEFT C on Pbc` = `A LEFT (B LEFT C on Pbc) on Pab` | BAG 多重性、值 | `Pbc` 对 B 的至少一列拒空 | R17 identity 3；C02 复现 | C02：`Pbc = (B.k IS NULL OR B.k=C.k)` 时两侧不同 |
| L05 | `A LEFT (B INNER C)` ≠ `(A LEFT B) INNER C` | BAG 多重性 | —（这是**否定**律） | R17 明文；C01 复现 | C01：1 行 vs 0 行 |
| L06 | `A RIGHT B` = `B LEFT A`（配合字段重映射） | BAG 多重性、值 | 字段映射显式 | R17 定义为「converse of a left join」 | 若左输入是累积行且映射被省略则不成立 |
| L07 | `SEMI(A,B)` 保留 A 的出现与多重性、**不发布** B 的字段 | BAG 多重性、字段可见性 | 存在性判定用 TRUE-only | R20；C05 复现 | 连续 SEMI 后无法再遍历下一跳（C05） |
| L08 | `DISTINCT(R)` 在其等价域上证明全行唯一 | 值等价类 | 等价关系在**已批准支持域**上是全域的且 NULL≡NULL；`Decimal(p,s)` 需两侧精确同参 | R17/R19/R20；C07 复现；D07 | 支持域外不成立：`Any`/`Bytes`/`Json`，以及参数缺失或不一致的 `Decimal` |
| L09 | `UNION` 不继承分支局部 FD | 值 | — | R19 未主张；C07 复现 | C07：`(1,Alice)` ∪ `(1,Bob)` 破坏 `id → name` |
| L10 | `EXCEPT` 非结合 | BAG 多重性 | — | R17 左结合规定；C07 复现 | C07：`{3}` vs `{2,3}` |

已排序的构造、源语法、语义分组与物理执行顺序是四件不同的事。契约定义序列中
被论证过的最后一个元素不自动是非法的赢家；判定依据是 root authority，而不是对
`[-1]` 之类语法的全面禁令。

## Reference Cases And Counterexamples

证据由两个独立来源复现：既有纯 oracle `project_bag_null_oracle`（INNER/LEFT、
等值对应）与标准库 SQLite `3.53.1`。有限用例只能**反驳**全称主张，不能证明它们。
Python/hash-seed 层面的字节相等只证明确定性，不证明 SQL 语义正确性。

| ID | Case | Reproduced result | Refutes |
| --- | --- | --- | --- |
| C01 | A(1 行)、B(2 匹配行)、C 空：逐跳 LEFT / 整段可选 / 末跳必需 | `2` / `1` / `0` 行；隐藏 B 后仍为 `2` 行 | 「三者等价」；「隐藏中间字段可去除多重性」 |
| C02 | B 空且 `B.key IS NULL OR B.key=C.key` | 左结合得 `(1,NULL,7)`，右结合得 `(1,NULL,NULL)`；改用普通等值后两者相同 | L04 的无条件形式 |
| C03 | base relationship 匹配被 refinement 排除 | TRUE-match 集合是 base 的子集；`AT_MOST_ONE` 可留存，`AT_LEAST_ONE` 不可；LEFT 侧变为可空 | 「refinement 不改变 match guarantee」 |
| C04 | `L.key = R.key OR L.allow_any`，`L.key` 为 NULL | INNER JOIN 输出 `(NULL, 1, 5)` | 「INNER JOIN 使被引用字段 NON_NULL」「JOIN 自动给出双向 value FD」 |
| C05 | SEMI 于首跳 vs 于完整路径 | `{1,2}` vs `{1}` | 「路径存在性等于首跳存在性」；谓词局部字段可外泄 |
| C06 | 两个右侧出现具有相同 payload；右输入全局 `LIMIT 1` | 出现数 `2`、distinct payload `1`；右输入 `LIMIT 1` 后每左行至多一匹配 | 「按 payload 去重可满足单匹配要求」；「右输入 LIMIT 1 等同 JOIN 后 LIMIT 1」 |
| C07 | 重复 set 操作数、FD 冲突、EXCEPT 括号、NULL 与空操作数 | `UNION ALL(P,P)` 多重性翻倍；`(P∖Q)∖S={3}` 而 `P∖(Q∖S)={2,3}`；set operation 中 `NULL≡NULL`（INTERSECT 得 `NULL`，EXCEPT 得空），而谓词 `NULL=NULL` 仍为 UNKNOWN；`(1,Alice) ∪ (1,Bob)` 破坏 `id→name` | 「操作数去重」「EXCEPT 可任意重括号」「set 等价与谓词等价同一」「FD 逐分支继承」 |
| C08 | DISTINCT 与隐藏字段 | `DISTINCT vis` 得单行，隐藏列不参与相等键 | 「隐藏 IR 字段影响 DISTINCT 键」；「DISTINCT 使任意顺序确定」 |
| C09 | `INTERSECT ALL` / `EXCEPT ALL` 的可移植性 | SQLite `3.53.1` 语法错误，PostgreSQL 与 Substrait 有明确多重性定义 | 「集合算子在各后端一致可用」；为 Phase 76–79 提供可移植性证据 |
| C10 | RIGHT/FULL 作用于累积左输入 | `(A INNER B) FULL C` 产生 `(NULL, NULL, 900)` | 「RIGHT/FULL 只对某个具名子集补空」 |

组合路径（grouped → generic LEFT → window/QUALIFY；`UNION ALL` → JOIN → DISTINCT；
FULL → WHERE → GROUP → 下游关系）的精确 adapter 见 §Route Selection 的 cross-feature
审计；它们的合法输入由 D03 的命名关系边界与 D04 的 authored 组合决定。

本 Slice **不**添加 parser production，也不主张任何示例可被当前 HEAD 解析；
D01 确定的语法在 Slice 1 仍然只是文档，由 Slice 2 实现。

## Resolved Decision Set

以下八项均为用户在本 Slice 的 decision checkpoint 上明确裁决，状态 `CONFIRMED`。
前一位 assistant 的确切关键字、隐式默认、「所有 path/kind 组合全支持」、强制
`ALL`/`DISTINCT` 与固定 16-slice route 记为 **proposal**，未被采纳为 authority。

### D01 Generic JOIN 的 authored 语法 — `CONFIRMED`

- 决定：扩展现有 `joinBody`。保留 `<kind> join <relation> as <binding>:` 缩进块；body 内 `FROM` 之后允许 `ON` 交替，与既有 `VIA` 并列；`AuthoredJoinKind` 扩展为 `INNER|LEFT|CROSS|RIGHT|FULL|SEMI|ANTI`。
- 未采纳的备选：kind 作为具名参数（R26 的 PRQL/Ibis 形状）；generic 与 relationship 使用两套独立 authored 形式。
- 理由：复用既有 kind 位置与全部 span 机制（F01），不向语言引入 Pietto 目前没有的具名参数构造。
- 最小示例：`left join orders as o:` / `  from customers` / `  on customers.id == o.customer_id`。
- 兼容性：纯新增；现有 `VIA` 形式与既有程序不变。
- 实现 owner：**syntax owner** = Slice 2（`grammar/Pietto.g4`、`ast_nodes.py`、`ast_builder.py`）；**semantic owner** = Slice 3（`project_relationship_uses.py` 的授权 AST 消费）。

### D02 新 kind 的支持范围 — `CONFIRMED`

- 决定：`CROSS/RIGHT/FULL/SEMI/ANTI` 只作用于**直接二元**右输入，其右输入可以是既有命名关系或已完成的 effective output。多跳 `VIA` 路径仍然只支持既有 `INNER`/`LEFT`。
- 未采纳的备选：全部 kind 支持逐跳多跳；分级支持 inline path group。
- 理由：C05 证明连续 `SEMI` 会丢失遍历下一跳所需的中间字段；C10 证明 `RIGHT/FULL` 对**整个累积左输入**补空，逐跳复制既有循环（F03）语义上不成立。
- 必要的不支持组合的替代写法：见 D03——把该路径先声明为命名关系，再对其做直接二元的新 kind JOIN。每个被拒组合发出精确 typed diagnostic，不静默改写。
- 实现 owner：**syntax owner** = Slice 2（kind 关键字）；**semantic owner** = Slice 3（`project_relationship_uses.py` 的 kind 中性 use 准入与被拒组合诊断）；**输出形状与属性** = Slice 5（`CROSS`/`RIGHT`/`FULL`）与 Slice 6（`SEMI`/`ANTI`），均在 `project_ir_joins.py`。

### D03 组合边界与整段路径可选性 — `CONFIRMED`

- 决定：**以既有命名关系作为唯一显式组合边界**。新 kind 允许消费完整的命名关系结果；本阶段**不新增** inline path-group 语法，也不新增 outer capture。
- 未采纳的备选：新增 inline group 语法；由编译器自动选择整段可选性；完全不支持整段可选。
- 理由：C01 证明逐跳可选 / 整段可选 / 末跳必需给出 2/1/0 行，属用户可见语义，不能是静默的优化器改写（R17 明确 `A leftjoin (B join C)` ≠ `(A leftjoin B) join C`；R22 表明显式书写是成熟先例）。命名关系已经是 Pietto 的既有边界，复用它使整段可选性**无需任何新语法**：把 `B INNER C` 声明为一个关系，再 `left join` 它。
- 架构收敛：该决定与 F08/F09 汇合为同一个机制——它要求的正是「JOIN 消费已完成的 effective output」，也就是解除 `EFFECTIVE_UPSTREAM_JOIN_UNSUPPORTED` 与 `EFFECTIVE_JOIN_INPUT_REBIND_UNSUPPORTED` 的那条边界。
- 实现 owner：**semantic owner** = Slice 4（`project_query_block.py` 的 row-source sum 与 `project_completion.py` 的 effective-output 边界解除）；**IR consumer** = Slice 10。

### D04 Set operation 的组合与 `ALL`/`DISTINCT` — `CONFIRMED`

- 决定：set operation 为 relation body 的顶层子句，操作数为具名 relation 引用；`ALL` 或 `DISTINCT` **必须显式书写**，省略即 fail closed；操作数按**位置**对齐。
- 未采纳的备选：默认 `DISTINCT`（R17 的 SQL 惯例）；默认 `ALL`；`UNION BY NAME` 式的名字对齐。
- 理由：这是一项**产品决定**，不是 fail-closed / no-winner 规则的推论——那些规则并不推出「必须显式书写」。支持该决定的证据是：SQL 的隐式去重是已知的语义与性能陷阱，而生态默认值**并不一致**（R26：PRQL 的 `append`/`remove`/`intersect` 全为 bag 语义；Ibis 的 `union` 默认 `distinct=False` 而 `intersect`/`difference` 默认 `True`）。在默认值本身有分歧时，要求作者写明比继承任一惯例更不易错。name-aligned 对应是一个可单独设计的查找选项，不是被永久禁止的身份模型，留待后续阶段。
- 兼容性：纯新增；每个操作数出现保持独立（C07），declaration scheduling 可以去重依赖边，但操作数多重性不可。
- 实现 owner：**syntax owner** = Slice 2（set-operation 子句的 grammar/AST/span）；**semantic owner** = Slice 9（操作数对齐、六条多重性律、显式 `ALL`/`DISTINCT` 的 fail-closed 判定）；**IR consumer** = Slice 10。

### D05 Single-match 契约 — `CONFIRMED`（含用户补正）

- 决定：完整的 obligation 对象**私有保留**在 semantic/IR fact 上；公开面只经**既有** diagnostics 通道发出一个新增 `PIE-S2xxx`。
- 用户补正：未被静态证明但**合法**的 requirement 在 `LOOSE`、`CHECKED`、`STRICT` **三种模式下一律为 `WARNING`**，不随 mode 升级为 `ERROR`。因此 check-success 的含义在所有模式下保持一致：静态合法的查询始终 check 成功并携带一条 warning。非法组合仍为 `ERROR`，且使用不同的码。
- 与既有机制的关系：`Severity.WARNING` 已存在（`errors.py:12-16`）；CLI text 渲染 severity（`cli.py:1112`）、CLI JSON 输出 `"severity"`（`cli_json.py:64`）；成功判定只看 `ERROR`（`cli.py:1152`、`json_v2.py:114`）。因此 **wire schema 与 Project JSON v2 零变更**。注意本决定与 `PIE-S2005` 的 mode-sensitive 政策（`analyzer.py:881`）**不同**：本码不随 mode 变化。
- 单位与作用域：计数**实际匹配的 BAG 出现**，不是 distinct payload、端点身份或合成的未匹配行；per-hop、完整路径与 distinct target 计数互不相同，需分别指明。
- 合法的作用域内基数证明：若确切的**已完成右输入本身**具有全局至多一行的上界，则每个左出现至多一个右匹配；该证明**不**推出原始 source 上的键或 max-one 关系，也不同于 JOIN 之后的 `LIMIT`。必须记录确切的 proof root。
- 禁止：为满足要求而选行、截断或去重；后置 `WHERE`/`LIMIT` 不能追溯掩盖指定匹配边界上的违规。
- 最小反例：C06。
- 实现 owner：**semantic owner** = Slice 7（`project_relationship_match_guarantees.py` + check 边界与 warning 诊断）；**IR consumer** = Slice 10（obligation 的精确保留证明）；下游兑现方为 Phase 65/68。

### D06 共享 semantic→IR 集成缝 — `CONFIRMED`

- 决定：扩展 `ProjectQueryBlockRowSource` sum；并**授权对 `project_final_outputs.py` 做窄重构**，把 output-field 构造拆为 SELECT 来源与非-SELECT 来源两个入口，共用同一 `ProjectModuleRowFieldIdentity` 的 `RELATION_OUTPUT` 身份域。
- 未采纳的备选：伪造 `SelectItem`（违反「不伪造 AST」）；新建平行输出身份域（会造出第二个身份域）；新建平行模块（两套输出构造逻辑）。
- 源证据：F06（身份域仅需 `(owner, kind, position, name)`，且 `module_attribution.py:1717` 已有非-SELECT 铸造点）；F07（`ProjectCompletedOutputField` 硬绑 `select_fact`/`SelectItem`/`definition.select_items[ordinal]`）。
- 兼容性：private-only；不改变既有 SELECT 路径的行为或身份。
- 实现 owner：**row-source sum 扩展** = Slice 4（`project_query_block.py`）；**非-SELECT output-field 入口与 `project_final_outputs.py` 窄重构** = Slice 9；**IR consumer** = Slice 10。

### D07 等价/类型支持域与 property/grain 转换 — `CONFIRMED`

- 决定：row-equivalence 支持域 = 精确类型身份相等，NULL≡NULL 且在支持域上全域；**`Decimal` 进入支持域，要求精度与标度完全相同**，不做隐式拓宽；`Any`、`Bytes`、`Json` 仍显式不支持并 fail closed。DISTINCT 商域与 set-operation 备选域使用**新增的** `ProjectGrainOriginKind`，不复用 `GROUPED_RESULT`。
- 未采纳的备选：沿用既有推迟集（会拒绝常见的 Decimal 去重工作流）；允许同标度下的受控精度拓宽（类型提升规则属 Phase 72）。
- 精确边界（对所有当前决策陈述统一适用）：
  - 有限 `Decimal(p,s)` 在**两侧都带经验证的同参证据**时，由 Phase-64 row-equivalence owner 支持；
  - nullability 是**独立证据**，不参与类型身份判定；
  - 参数缺失或未传播时**不猜测**，该列 fail closed；
  - 不做隐式拓宽、不做舍入、不从聚合结果反推 `p`/`s`；
  - `Any`、`Bytes`、`Json` 仍在已批准 row-equivalence 支持域之外；
  - `UNION ALL` 只要求形状与类型兼容，**不要求**重复比较能力，因此不受本支持域约束；
  - 历史 relationship 比较的支持范围不因本决定顺带放宽（见 F12）。
- 源证据：F11（无既有 origin 可用）、F12（推迟集与 `ValueType` 的分离先例）；R19（Union DISTINCT 全列键 / Intersect 任一输入键 / Minus 第一输入键）；C07（FD 不逐分支继承）。
- 属性转换：DISTINCT 在其等价关系下证明全行唯一（L08）；键结论仍需既有键模型的 NULL、相等、作用域与最小性前提，既不无条件提升也不一概禁止；`UNION` 的 nullability 为跨输入的保守 OR，`INTERSECT` 在某输入证明非空时可排除 NULL，`EXCEPT` 沿其保留的左域。
- 兼容性：private-only。
- 实现 owner：**semantic owner** = Slice 8（row-equivalence 支持域、`DISTINCT`、新商域 `ProjectGrainOriginKind`，位于 `project_grain.py`）；**set-operation 属性传递** = Slice 9（`project_ir_relational_properties.py` 的键/FD/nullability 转换）；**IR consumer** = Slice 10。

### D08 Pull-forward 范围 — `CONFIRMED`

- 决定：**拆分「当前 IR 产物」与「未来 SQLPlan 契约」**，两者占据不同的原子行：
  - Phase 64 自身**实现**其算子的 Project IR 产物，并实际保留每个 condition 与 scope、field mapping、source span、显式输出与 single-match obligation（`IMPLEMENT_NOW`）；
  - verification/inspection **证明**这些保留是精确的（`IMPLEMENT_NOW`）；
  - Phase-65 对这些事实的**消费契约**为 `CONTRACT_ONLY_NOW`，不在无 target 模型时冻结承载形状；
  - 构造 `ProjectSQLPlan` 及其 SQL 分解、参数、alias、legality 机制为 `DEFER_BY_NECESSITY`，理由是缺少 SQL planning/legality 接口本身（plan 节点代数、参数/占位符模型、alias 作用域与生成规则、legality/capability 判定面），**不是**「尚未选定后端」。
- 未采纳的备选：把 Phase-65 承载结构一并前移（在无 target 模型时容易冻结错误形状）。
- 其余分类沿用 §Pull-Forward 表。区分两类计数：**Phase-64 核心实现职责**（上面两条 `64 core` 行）不是跨阶段前移；真正的**跨阶段 pull-forward** `IMPLEMENT_NOW` 仍为两项——Phase-72 的基础类型兼容/等价支持域与 Phase-81 的独立 oracle/反例边界。不得为了保住「两项」这个数字而把本阶段必需的产物错分为 `CONTRACT_ONLY_NOW`。
- 保留 owner 边界不变：没有 public、backend、execution 或 release ownership 被重指派。

## Authored Mode Source Map

本表由既有已批准决策（D01–D04）导出，不引入新的产品选择。它固定了五种 authored
形态、各自的 condition scope 与谓词作用点。
表中的 `ON` 语法在当前 baseline **不可解析**；
示例只描述 Slice 2 之后的形态。除被描述的未来 `ON` 子句外，示例沿用现有语言拼写：
相等为 `==`（`grammar/Pietto.g4:660`，`=` 是 select 别名赋值），限定引用使用已声明的
绑定名（`from` 的源名或 `as` 的目标绑定名），字符串为双引号字面量。

| # | Authored 形态 | 关系发现 | 谓词的 condition scope | 谓词作用点 | Slice owner |
| ---: | --- | --- | --- | --- | --- |
| M1 | 直接关系简写（不变）：`inner join orders as o:` / `  from customers` | 由既有 relationship 声明发现 | `RELATIONSHIP_BASE_MATCH` | 该单跳的匹配 | 既有行为，无变更 |
| M2 | 显式 `VIA`（不变）：`  via ships: customer -> order` | 由具名 relationship 与端点角色发现 | `RELATIONSHIP_BASE_MATCH`（逐跳各一） | 每一跳自身的匹配 | 既有行为，无变更 |
| M3 | Generic `ON`（无关系遍历）：`inner join orders as o:` / `  from customers` / `  on customers.id == o.customer_id` | **无**关系发现 | generic 匹配条件（既有 supported row-scalar Bool，TRUE-only） | 该二元 JOIN 的匹配 | Slice 2 语法 / Slice 3 语义 |
| M4 | 关系 refinement（单跳 + `ON`）：`left join orders as o:` / `  from customers` / `  via ships: customer -> order` / `  on o.status == "open"` | 由 relationship 发现，**base condition 保留** | `JOIN_LOCAL_ON_REFINEMENT`，与保留的 base 合取 | 同一跳的匹配，`base AND refinement` | Slice 2 语法 / Slice 3 语义 |
| M5 | `CROSS`（无匹配条件）：`cross join calendar as k:` / `  from customers` | 无 | 无 condition | 无匹配判定，笛卡尔积 | Slice 2 语法 / Slice 5 语义 |

区分三者的 authored 证据是**结构性**的，不靠命名或启发式：

- **M3 与 M4 的区别**：JOIN body 内是否存在关系遍历。有遍历 + `ON` = M4 refinement，
  base condition 继续存在且不被替换；无遍历 + `ON` = M3 generic 匹配条件。
- **M4 与 `WHERE` 的区别**：refinement 参与**匹配判定**，因此影响 LEFT 侧是否补空
  （C03：`AT_MOST_ONE` 可留存，`AT_LEAST_ONE` 不可，LEFT 侧变为可空）；`WHERE` 在
  JOIN **之后**过滤，会移除已补空的行。两者 scope 不同（`JOIN_LOCAL_ON_REFINEMENT`
  对 `POST_JOIN_FILTER`），authority 互不替代（E04）。
- **M3 不继承关系证据**：generic `ON` 没有 base condition，也不因此获得等值对应证明；
  非空与 FD 强化需要各自的 conjunct 级拒空证据（C04、F04）。

已批准表面**不包含**多跳 `VIA` 加 `ON` refinement：其 refinement 作用于哪一跳、
哪一组或整条路径未被任何已批准决策选定，因此该组合 fail closed 并给出精确诊断。
其替代写法由 D03 提供：把该路径声明为命名关系，再对该关系书写 M3 或 M4。若日后需要
多跳 refinement，那是一项**独立的产品决定**，本文件不代为选择、也不声称已闭合。

## Route Selection

按 §9 的比较维度筛选 8–16：semantic completeness、avoided redesign、later ownership、
cohesion/testability、dependency/safe parallelism、implementation/diagnostic risk、
reader burden、CI/evidence efficiency、public/release/trust containment。

评估方式是**定性**的：这些维度用于说明每个候选被接受或拒绝的确切理由，
**没有**计算加权总分，也没有回溯打分矩阵。本文件不声称任何数值比较结果。
硬性的兼容性、authority 与可验证性门槛先于任何偏好；在没有决定性差异时取较少的
Slice 数，除非较大方案解除了已证明的过载。

| Route | 结构 | 结果 |
| ---: | --- | --- |
| 8 | 必须把「五个新 kind + 属性传递」与「等价域 + DISTINCT + 三个 set operation」各压成一条 | 拒绝：两条都是已证明的过载（两种互斥的输出形状规则；六条多重性律 + 新 grain origin + 非-SELECT 输出构造者） |
| 9 | 同上再加 IR/verification 与 completion 分开 | 拒绝：同一过载未解除 |
| 10 | 把 IR composition/verification/inspection 折进 completion | 拒绝：违反 completion 与 assurance 分离；Phase-63 的 Slice 16 为纯文档先例 |
| **11** | 见下表 | **选定** |
| 12 | 把选定 route 的 Slice 4 拆成「row-source sum 扩展与 effective-output 边界解除」与「首个 generic 垂直闭合」两条 | 拒绝：拆出的前半条没有可独立演示的产品结果——扩展在垂直闭合使用它之前没有 consumer，其验收只能断言内部结构。这是与选定 route 结构上确有差异的候选，但差异不利 |
| 13–16 | 每个 JOIN kind 或每个 set operation 各占一条 | 拒绝：五个 kind 共享 `project_ir_joins` 的 transfer rule，三个 set operation 共享同一多重性与身份机制；无独立 production/test ownership，属 Slice 膨胀 |

选定 11 的理由是逐候选的定性判定，而不是分数：8/9/10 都保留了上表中两处已证明的
过载（五个新 kind 的两种互斥输出形状规则挤在一条；等价域 + `DISTINCT` + 三个 set
operation + 新 grain origin + 非-SELECT 输出构造者挤在一条），或把 assurance 折进
completion；12 的拆分产生一条没有独立产品结果的 Slice；13–16 缺少独立的
production/test ownership。11 相对 8–10 的额外两条不是膨胀，而是解除那两处过载。

先前版本曾把「额外把 grammar/AST 与 ON 语义拆开」列为 12 的结构，并据此声称
11 与 12「同分」而由平局规则胜出。那是**错误**的：选定的 11 条 route 本身已把
grammar/AST（Slice 2）与 ON 条件语义（Slice 3）分开，因此那不是一个不同的候选，
也从未存在过一次同分或一次数值比较。此处已改为真实的替代分组与定性理由。

### 选定 route — 11 条 numbered Slice

| Slice | Owner |
| ---: | --- |
| 1 | Product Gate v3、source audit、architecture 与 route lock |
| 2 | Generic `ON`、新 JOIN kind 与 set-operation 子句的 grammar、AST、contextual keyword 与 span |
| 3 | Generic ON 条件语义、refinement 与 base/WHERE/satisfying/QUALIFY 的 authority 分离 |
| 4 | Row-source sum 扩展、effective-output JOIN 边界解除与首个 generic 垂直闭合 |
| 5 | `CROSS`/`RIGHT`/`FULL` 输出形状、null-extension 与属性传递 |
| 6 | `SEMI`/`ANTI` 左出现保留与存在性语义 |
| 7 | Single-match 方向、单位、作用域证明、obligation 与 warning 诊断 |
| 8 | Row-equivalence 支持域、`DISTINCT` 与商域 grain origin |
| 9 | `UNION`/`INTERSECT`/`EXCEPT`、显式 `ALL`/`DISTINCT` 与输出身份 |
| 10 | 新算子的 Project IR composition、verification、invalidation、inspection 与 pure boundary |
| 11 | Completion audit 与 Phase-65 handoff |

### 逐 Slice 契约

| Slice | Prerequisites | Production / focused-test owner | Input → output contract | Non-goals | Representative acceptance | Handoff |
| ---: | --- | --- | --- | --- | --- | --- |
| 2 | Slice 1 | `grammar/Pietto.g4`、`ast_nodes.py`、`ast_builder.py` / 新 focused test | 源文本 → 保留 span 的 `JoinClause`（含可选 `ON` 表达式与扩展 kind）与 set-operation 子句 AST | 无语义解析、无类型检查、无 lowering | `ON` 可单独出现，也可与关系遍历**共存**（后者是 refinement，见 §Authored Mode Source Map）；两种形态的 AST 可区分且都带 span；缺失 `ALL`/`DISTINCT` 在解析层保留为可被 Slice 9 fail closed 的形状 | AST 形状交 Slice 3（JOIN）与 Slice 9（set operation） |
| 3 | Slice 2 | `project_relationship_conditions.py`、`project_relationship_uses.py` | 授权 AST → generic ON 的 Bool 类型证据、conjunct 分解与拒空证据；refinement 落入 `JOIN_LOCAL_ON_REFINEMENT` | 不构建 IR、不推导键/FD、不改写 base relationship | C04：析取 ON 不产生 `NON_NULL`；C03：refinement 保 `AT_MOST_ONE`、失 `AT_LEAST_ONE` | 条件事实交 Slice 4/5/6 |
| 4 | Slice 3 | `project_query_block.py`、`project_completion.py`、`project_ir_joins.py` | 扩展后的 row-source sum + 已完成 effective output → 首个 generic `INNER`/`LEFT` `ON` 端到端穿过既有一元尾部至 completed output 与 check | 不引入新 kind、不引入 set operation | `EFFECTIVE_UPSTREAM_JOIN_UNSUPPORTED` 在合法输入上不再触发；一条真实 authored 查询完成 check | **早期垂直闭合**；集成缝交 Slice 5–9 |
| 5 | Slice 4 | `project_ir_joins.py`、`project_ir_relational_properties.py` | 直接二元右输入 → `CROSS`/`RIGHT`/`FULL` 行形状、对**整个累积左输入**的 null-extension 与属性传递 | 不做 `SEMI`/`ANTI`、不做多跳新 kind | C10：`(A INNER B) FULL C` 保留真实左或右见证 | 属性传递交 Slice 10 |
| 6 | Slice 5 | `project_ir_joins.py` | 直接二元右输入 → 保留左出现与 BAG 多重性、**不发布**右字段 | 不发布右字段、不支持逐跳 `SEMI` | C05：完整路径存在性 ≠ 首跳存在性；谓词局部字段不外泄 | 同上 |
| 7 | Slices 3、5、6 | `project_relationship_match_guarantees.py`、check 边界 | 匹配证据 → 已证明 / 合法但未证明（obligation + 三模式一律 warning）/ 非法（error） | 不选行、不截断、不去重 | C06：等 payload 的两个右出现仍违规；右输入全局 `LIMIT 1` 是合法作用域内证明 | obligation 交 Slice 10 与 Phase 65 |
| 8 | Slice 4 | `project_grain.py`、`project_ir_relational_properties.py` | 精确类型身份（含精度标度相同的 `Decimal`）→ 全域 row-equivalence、`DISTINCT` 与新商域 grain origin | 不做隐式拓宽、不做 `Any`/`Bytes`/`Json` | C08：隐藏字段不入相等键；`Any` 列 fail closed | 等价域交 Slice 9 |
| 9 | Slice 8 | 新 set-operation stage、`project_final_outputs.py`（窄重构） | 具名操作数 + 显式 `ALL`/`DISTINCT` → 六条多重性律、位置对齐、经非-SELECT 入口铸造的输出身份 | 无 name-aligned 对应、无隐式默认 | C07：操作数重复、`EXCEPT` 非结合、NULL 单一等价类、FD 不继承 | 输出交 Slice 10 |
| 10 | Slices 4–9 | `project_query_block_ir.py`、`project_query_block_ir_verification.py`、inspection/pure boundary | 全部新算子 → active root、IR 组合、独立验证、invalidation 与 VERIFIED-only 观察 | 无 optimizer、无 SQL、无 execution | `EFFECTIVE_JOIN_INPUT_REBIND_UNSUPPORTED` 在合法输入上不再触发；观察为 winner-free | 交 Slice 11 |
| 11 | Slices 1–10 | 文档 + static assurance | 完成审计 → 物质出口关闭与 Phase-65 handoff | 无 production delta | 全部物质出口有真实产品与 principal 支撑 | 交 Phase 65 |

repair authority：每条 Slice 只对自身 owner 做 root-cause 修复；跨 Slice 的真实
production defect 停止该 Slice 并单独处置，不在完成审计中掩盖。

### 物质出口（按产品结果定义，非每 Slice 一个）

```text
E01 generic ON JOIN（INNER/LEFT）端到端可用并完成 check
E02 CROSS/RIGHT/FULL 直接二元可用，null-extension 覆盖整个累积左输入
E03 SEMI/ANTI 直接二元可用，保留左出现且不发布右字段
E04 relationship refinement 与 base/WHERE/satisfying/QUALIFY 的 authority 保持分离
E05 JOIN 可消费已完成的 effective output；两个 UNSUPPORTED 边界在合法输入上解除
E06 single-match 的三态契约（已证明 / 合法未证明 warning / 非法 error）成立
E07 DISTINCT 在精确等价域上可用，含精度标度相同的 Decimal
E08 UNION/INTERSECT/EXCEPT 六条多重性律成立且 ALL/DISTINCT 必须显式
E09 新算子输出继续穿过既有 LET/WHERE/GROUP/satisfying/WINDOW/QUALIFY/projection/ORDER/LIMIT
E10 新算子进入 active-output ledger、IR、verification、invalidation 与 inspection
E11 Project JSON v2 的 top-level schema/keys 零 delta；新增的 authored 语法与诊断码是 additive public
E12 Phase-65 handoff 记录完整，且不需要从名字、末端输出或字节重建语义
```

### Cross-feature 与 reverse-consumer 审计

| 组合路径 | 覆盖 Slice | 适配缝 |
| --- | --- | --- |
| grouped output → generic LEFT → window/QUALIFY | 4、10 | grouped 输出经命名关系成为右输入；既有 `POST_LET` 命名空间不变 |
| `UNION ALL` → JOIN → `DISTINCT` | 9、4、8 | set 输出经 D06 的非-SELECT 入口取得 `RELATION_OUTPUT` 身份，再作为 row source |
| `FULL` → WHERE → GROUP → 下游关系 | 5、10 | FULL 输出的 null-extension provenance 进入既有 Slice-6 属性桥 |
| self-join / 重名 / 外部 snapshot / stale active producer / 循环终端 | 4、10 | 既有 occurrence 身份与依赖图不变；不新增赢家选择 |

| 反向 consumer | 需要什么 | 由谁提供 |
| --- | --- | --- |
| Phase 65 | 每个 condition 与 scope、field mapping、source span 与 enforcement/equality requirement | Slices 3、7、9 实际产生并保留；Slice 10 证明保留；消费契约本身为 `CONTRACT_ONLY_NOW`（D08） |
| Phase 67 | 结果形状、隐藏字段、nullable/provenance 与 check-vs-executable 区分 | Slices 5、6、9、10 |
| Phase 68 | single-match obligation 的**基数错误含义**：Phase 64 不执行，但该 obligation 表达「运行期可能违反至多一匹配」，须经后续 lowering/execution 兑现或拒绝 | Slice 7 的 obligation 记录 + Slice 10 的保留证明；资源与 effect 的缺席不等于没有下游 consumer |
| Phase 73 | fanout/chasm/`AGGREGATE_ALGEBRA_REQUIRED` 证据在新算子上继续成立 | Slices 5、8、9 |
| Phase 88 | 每条改写律的 LHS/RHS、观察域、前提与证据强度 | §Semantic Laws（L01–L10） |

以上任何一方都不需要从名字、最后输出或规范化字节重建缺失语义。

未来实现测试使用已完成的 Interlude 基础设施：批量精确环境获取、不变的 witness
区分、resource-aware loadfile、serial fallback、双 Python 版本，以及独立的
foreign-snapshot 测试。不为每条断言新建子进程，也不施加机器特定的运行时断言。

## Public And Compatibility Exit

| Boundary | Phase-64 finding | Result |
| --- | --- | --- |
| Package/CLI version | `0.1.0` | UNCHANGED |
| Authored language | 新增 generic `ON`、五个 JOIN kind、`DISTINCT` 与三个 set operation | ADDITIVE（Slices 2–9） |
| Diagnostic codes | 既有 78 个码、消息与顺序不变；新增均为 additive `PIE-S2xxx` | ADDITIVE |
| Diagnostic severity | 复用既有 `Severity`；single-match warning 不改变 check 成功判定 | COMPATIBLE |
| CLI text / CLI JSON | 形状不变 | COMPATIBLE |
| Project JSON v2 | top-level schema/keys 不变 | COMPATIBLE |
| `AUTHORED_JOIN_DEFERRED` | 历史事实保留，不整体移除或改写 | UNCHANGED |
| `_project` exports | `__all__ == ()` | PRIVATE |
| Inspection formats | Phase-61/62/63 格式不变；新观察为 additive private | ADDITIVE / PRIVATE |
| SQL / Arrow / executor / optimizer | 未启用 | NOT IMPLEMENTED |
| Release surface | 无 package/dependency/lockfile/workflow/tag/Release/signing/attestation 变更 | ZERO DELTA |

三个层次必须分开陈述，不得合并为「全部只是 additive private」：

| 层次 | 内容 | 公开性 |
| --- | --- | --- |
| Slice 1 | 本 Slice 对上述每一项的实际 delta 均为零 | 零公开行为变更 |
| Phase 64（Slices 2–9） | **用户可见**的新 authored 语法与新增诊断码，且 single-match 在三种 check 模式下一律发 `WARNING` | **additive public**，Project JSON v2 的 top-level schema/keys 不变 |
| Phase 64 运行期 | 无 execution、无 executor、无 effect system | 不存在运行期行为 |

因此 Phase-64 的语法与诊断是**公开的 additive 变更**，只是它们不改变 JSON schema；
把整个 Phase 64 称作「additive private only」是不准确的。JSON schema 未变与
「无公开行为变更」是两件事。private 的部分是 `_project` 内部载体与 inspection 格式。

## Slice 1 Zero-Delta Boundary

```text
production delta = 0
grammar / generated delta = 0
public API / CLI / JSON / SQL delta = 0
package / dependency / lockfile / workflow / version delta = 0
Arrow / executor / optimizer delta = 0
Phase-64 implementation delta = 0
```

任何真实 production correctness defect 都会停止本 Slice，不在此修复或用 prose 掩盖。

## Reader And Inventory Ownership

唯一 mutable lifecycle-document reader 仍是 `tests/test_active_phase_lifecycle.py`。
本 Slice 的 principal 只消费本 immutable contract、explicit source 与 Git objects；
它不读取、不命名、也不伪装引用 mutable lifecycle 文档路径。完整的 changed-path
表保留在本契约与该 lifecycle owner 中。

专属 inventory reader 继续独占 current whole-repository Python inventory；principal
只保留不可变的转移 `179 -> 179` 与 `428 -> 429`，不做动态 inventory scan。

Phase-64 的 pre-implementation 缺席断言是**历史性**的：它绑定到 baseline
`bb52135038973b40638ff86367ba478846f898c6` 的 immutable source/Git 对象，
不创建任何永久禁止未来 Phase-64 语法出现在 current HEAD 的断言。历史 delta 使用两个 immutable
commit，绝不使用 old-start..future-HEAD。shallow CI 下只跳过不可用的 Git-object 检查，
decision/route/static assurance 仍然执行。测试不访问网络，也不从 pytest 内部拉取历史。

每条被冻结的事实必须归入且仅归入以下两类之一。`HISTORICAL` 读 baseline 不可变来源
并做**精确**比对（用安全静态解析，不执行历史源码）；`DURABLE` 读 live source 但只做
**保留性**（子集/成员存在）检查，因此不会在下一次合法扩展时误报。

| Frozen fact | 分类 | 检查方式 |
| --- | --- | --- |
| `AuthoredJoinKind` 成员集合 | `HISTORICAL` | baseline 静态解析，精确集合 |
| `ProjectIRBinaryJoinKind` 成员集合 | `HISTORICAL` | baseline 静态解析，精确集合 |
| `ProjectGrainOriginKind` 成员集合 | `HISTORICAL` | baseline 静态解析，精确集合 |
| `ProjectEffectiveOutputTerminalReason.EFFECTIVE_UPSTREAM_JOIN_UNSUPPORTED` 存在 | `HISTORICAL` | baseline 静态解析，成员存在 |
| `ProjectIRQueryBlockTerminalReason.EFFECTIVE_JOIN_INPUT_REBIND_UNSUPPORTED` 存在 | `HISTORICAL` | baseline 静态解析，成员存在 |
| `_DEFERRED_EQUALITY_BUILTINS` 字面量 | `HISTORICAL` | baseline 源文本 |
| authored grammar 只有 `(INNER \| LEFT) JOIN` 且无 set-operation 关键字 | `HISTORICAL` | baseline 源文本 |
| 三个 `ProjectRelationshipConditionScope` 保留 | `DURABLE` | live，子集 |
| `ProjectModuleRowFieldKind.RELATION_OUTPUT` 保留 | `DURABLE` | live，成员存在 |
| `AuthoredJoinKind` 保留 `INNER`/`LEFT` | `DURABLE` | live，子集 |
| `ProjectIRBinaryJoinKind` 保留 `INNER`/`LEFT` | `DURABLE` | live，子集 |
| `ProjectGrainOriginKind` 保留三个 baseline origin | `DURABLE` | live，子集 |
| `Severity` 保留 `ERROR`/`WARNING` | `DURABLE` | live，子集 |
| `ProjectBagNullJoinKind` 保留 `INNER`/`LEFT` | `DURABLE` | live，子集 |

同一个枚举可以同时出现在两类中：其**精确集合**是历史事实，其**既有成员的保留**是
durable 法则。principal 不得对 live 枚举做精确集合比对——那会在 Slice 2、5、6、8
合法扩展枚举时把正确的实现判为失败。

## Exact Changed-Path Closure

| Status | Path |
| --- | --- |
| A | docs/spec/phase64-flat-relational-algebra-product-phase-initiation-gate-v3-source-audit-architecture-route-lock-v1.md |
| A | tests/test_phase64_slice1_flat_relational_algebra_product_phase_initiation_gate_v3_source_audit_architecture_route_lock.py |
| M | docs/roadmap.md |
| M | docs/status.md |
| M | tests/test_active_phase_lifecycle.py |
| M | tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py |

```text
A2/M4/D0
6 paths
production Python: 179 -> 179
tests: 428 -> 429
```

没有 `src/`、`grammar/`、`scripts/`、`.github/`、pyproject/lockfile/generated/golden/
package/version 路径。

## Phase-65 Handoff Boundary

Phase 64 交给 Phase 65 的是：target-neutral 的完整平坦代数语义、每个算子的
condition 与 field mapping、精确 source span、single-match 的 enforcement
requirement，以及 §Semantic Laws 中每条改写律的前提与观察域。Phase 65 拥有
`ProjectSQLPlan`、参数化、source map 与 backend legality/capability；Phase 64
不冻结其承载形状（D08）。

## Slice 1 Reconciliation Lineage

原始 Slice-1 publication 是**不可变证据**，其数字保持为原始发布事实：

```text
original publication commit = f483d2d3a73edbfd6b203fb3014758095e398e23
original publication tree   = 008c88eb2a6aadb63172bb2ee3b326971dfe058d
original publication parent = bb52135038973b40638ff86367ba478846f898c6
original publication CI     = 34049044651 / push / main / attempt 1 / success
original publication closure = A2/M4/D0, 6 paths
```

该提交的 CI 成功是历史事实，**不是** failed head，也不被本次更正重新标记。

本次为其后的一个 **documentation/static-test correction child**，不是 Slice 2、
不是新的 numbered Slice、也不是新的 phase-start audit。它更正已发布契约与 principal
中的六类证据缺陷（R1–R6），不改变任何已确认的产品选择、N=11 或 E01–E12：

```text
correction closure = A0/M5/D0
correction paths   = 本契约、Slice-1 principal、roadmap、status、active lifecycle reader
production delta   = 0
production Python  = 179 (unchanged)
test-file inventory = 429 (unchanged)
```

三个 alignment 路径之所以必需：Slice-2 的 authored surface 标签在 roadmap 的
Phase-64 route 表、status 的 `Next` 行与 active lifecycle reader 的期望常量中各有
一份，更正必须同时覆盖这三处，否则 sole-reader guard 会与契约不一致。

## Slice 1 Accounting

```text
documentation/static-test root-cause repairs = 0/12
additional mechanical historical doc/test-reader paths = 0/12
authoritative validator process starts = 0/4
production mutations = 0
```

decision checkpoint 上返回的 `USER_DECISION_REQUIRED` packet 是一次诚实的
pre-publication 停止，不消耗 repair batch；用户裁决 D01–D08 后本 Slice 在保留
上述账目的前提下继续，未重启审计。

## Validation And Publication

完成 focused suites、reader/inventory guards、public/private 兼容性、targeted
Pyright、Ruff、format、`git diff --check` 与一次合并的 finding review 后，唯一
authoritative validator 是：

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

预算为 4 starts；unchanged failed candidate 不得重跑。最终 PASS 后封存 exact
tree，只创建一个 ordinary non-amend commit：

```text
Establish Phase 64 flat relational algebra route
```

只允许一次 normal fast-forward push，随后只观察 natural exact-head CI。必须为
`push/main/attempt 1/success` 且 Python 3.12/3.13 成功。禁止 amend、rebase、
force push、manual rerun、dispatch、tag、Release、signing、attestation 或
status-only follow-up commit。

成功标题：

```text
PASS — PHASE64_SLICE1_PRODUCT_PHASE_INITIATION_EXPANSION_READINESS_DESIGN_ROUTE_LOCK_END_TO_END
```
