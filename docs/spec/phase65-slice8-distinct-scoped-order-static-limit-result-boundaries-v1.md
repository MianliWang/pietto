# Phase65 Slice8 DISTINCT, Scoped ORDER And Static LIMIT Result Boundaries v1

本交付消费 EXPLICIT_MODULES、whole-project completed.ok、同快照的 VERIFIED
Query Block IR 和明确选择的 TABLE/QUERY。D65.01–D65.12、N16 保持。成功普通
commit、fast-forward push 和自然 exact-head push/main/attempt1 CI 后，Slices1–8
发布，Slice9 NEXT；本合同不授权 Slice9。

## 原始证据与构造入口

起点为 commit `0966ecb309f6243baf4490a423ebcb47af1f909c`，tree
`3d4d7f967680309f9ac5a9a339e510fe174903bb`，parent
`720a296a5ac7aa3181afb82ccd42453186ebba1c`；自然 CI `34682271444` 成功。
实时 fetch、refs、工作区、index、Git 操作和相关进程在写入前检查。

实源前置矩阵区分三个入口：ordinary existing-entry、rebound existing-entry、
completed joined/no-JOIN replay。普通 ORDER 使用 ProjectIRProvidedRelationOrdering，
普通 LIMIT 使用 ProjectIRProvidedCardinalityUpperBound；completed 路径使用
ProjectRelationOrdering/ProjectRelationLimit。不能把这些载体按外形强行互换。

| 路径 | 正常上游构造与保留 | 下游使用 |
| --- | --- | --- |
| existing-entry ORDER | 原来只有排序 IR，缺少 typed ORDER analysis；completed roots 在原 input/LET 环境调用既有 `_no_join_relation_ordering` 一次，保留成功或失败结果 | ProjectCompletedOrderFacts 连回 exact semantic entry；不改变旧完成诊断 |
| completed no-JOIN ORDER | `_no_join_relation_ordering` 原分析及类型 map 保留；成功 ORDER 构造时对缺失 ledger 调用共享候选收集机制 | 每个 OrderItem/operand 的 owner、ordinal、input/LET target、原类型对象 |
| joined scalar ORDER | 直接消费原 namespace analysis 的 resolutions/value_types | 原 joined field 或 LET occurrence，不做第二次名字解析 |
| grouped/window ORDER | 保留 normal resolver 已选择的 clause dependency、pre-window binding 或 selected-window result | 原 group/aggregate/window stage value，保持优先级与 fallback |
| static LIMIT | 消费原 ProjectRelationLimit 或旧 IR upper-bound witness | 原 clause/literal、strict Int、既有范围与上界 |

普通/replay 缺失引用的补建是 **NEW construction-time binding preparation**，不是
保存以前不存在的 resolver 返回值。existing-entry 的 typed ORDER 构造同样明确记为
新增上游准备。没有在 planner、verifier、inspection 中调用解析、类型推断、FD/grain
solver 或 proof builder；已存在的分析、ValueType 和诊断不被替换或预填。

ProjectRelationOrdering 的新 inputs 通过 InitVar 注入并冻结。构造失败不发布部分
ordering；summary-only 构造和 dataclasses.replace 派生对象没有 inputs，不能据此
规划。旧 carrier 摘要和诊断不变。未成功解析的 SELECT alias 不变成 backward-visible。
Phase63 直接 reader 增加 exact input/type retention 和 derived-copy 控制，没有新增
整载体字段快照。

ProjectModuleOrderReferenceFact 是独立的 ORDER occurrence sidecar，保留 exact
OrderItem；原 ProjectModuleExpressionReferenceFact 的两种泛型角色与布局不变。
两个入口共享从原 collector 提取的 `_expression_reference_candidates`，既有
qualifier、input/LET 优先级、候选完整性、顺序和失败状态只在一处处理。

## 可见投影、商集与结果端口

现有 SELECT-block 负责 row/JOIN、LET/WHERE、aggregate/satisfying、window/QUALIFY
和 authored visible projection。新 ProjectSQLResultBoundary 以该 projection 为
predecessor，逐次连接 DISTINCT、relation ORDER、LIMIT；它们形成实际结果图。
result_stages 查询把这两部分按一个 definition 的真实顺序展示。

Canonical export 是语义输出对应，不是任意阶段的可用值。ProjectSQLResultPort
为 projection、每个结果阶段的 input/output 分配不同引用；ProjectSQLResultExport
把完整 canonical tuple 连到最终阶段。绑定和 JOIN consumer 使用 immediate named
exports；独立验证要求对应 definition 的全部结果阶段及终端映像，不能绕过内层
DISTINCT、ORDER 或 LIMIT。共享定义只保留一次，重复 uses 各自存在。

ProjectSQLDistinct/ProjectSQLQuotientField 消费原 ProjectDistinct 和
ProjectIRDistinctComparison，比较 tuple 严格等于 authored visible outputs。
隐藏窗口、QUALIFY helper、row LET、未选分组键和隐藏排序值不加入商集。
每个字段保留原 equivalence、type resolution、TypeExpr、Decimal precision/scale、
NULL-equal 规则及 parent evidence。全行 uniqueness 与较小 key、普通 predicate
equality、cardinality 分开；原 origin、input domain 和 global_input 特例保持。
连续 DISTINCT 不合并，不根据 key 删除，也不选择代表行。

普通 Decimal 命名转递保留原 TypeExpr，各次 quotient 保留自身的分析对象；非空
Decimal parent evidence 的现有实源见证经过 SET，因此继续是 SET whole-plan
unavailable 控制。没有为了制造可规划 parent 示例而拓宽 SET 或类型规则。

## ORDER 的两个作用域分支

没有 DISTINCT 时，ORDER 通过 projection 的必要私有端口读取原 input/LET/group/
window 值。此类端口不进入 canonical exports；重复 keys 和表达式 uses 不去重。
原表达式树、每个 operand、原/默认 direction、类型、NULL 和未指定 ties 姿态保持。

有 DISTINCT 时只消费两种原始 determination record：

1. 三元 visible-source record：每个原 target 连到商集中的全部对应可见端口。
   computed projection 不暴露自由输入，也不提供逆变换证明。
2. 二元 STRICT-FD record：ProjectSQLHiddenOrderRequirement 保留原 item、表达式和
  类型、property/index、seed/requested classes、closure/witness，以及 visible determinant
  和原到当前 pre-quotient input images。OrderItem.value 指向这个 pending requirement；
  其 uses 不携带普通可用值端口。普通 result-port lookup 拒绝该引用。

隐藏要求没有 fulfillment 标志、代表行、MIN/MAX、join-back 或 backend 策略。
结构有效不证明数据库识别该 FD、collation 等价、SQL 可以发出或运行时已经履行。
独立 verifier 检查所给 derivation 的 rooted membership、STRICT index premise 和
每一步 witness，不调用 `_distinct_ordering`、`_validate_distinct_order_proofs` 或 solver。
LAX、相同字段名、匹配数量、quotient uniqueness 都不能替代原 STRICT 前提。

## LIMIT、性质与义务

顺序固定为 row/JOIN/group/window/QUALIFY → visible projection → DISTINCT → ORDER
→ LIMIT。LIMIT 只给当前边界至多 N 行，absent 与 0 分开；Bool 不作为 Int，不求值、
折叠负号或读取 bind slot。没有 filter pushdown、LIMIT0 DCE、隐藏 tie-breaker、
确定选中行或 blanket GLOBAL 承诺。内层排序与选行保留，consumer 不自动继承展示顺序。

原 single-match assessments、diagnostics、scope、input-pair 和 proof images 全部保留。
真实有限右侧 producer 的 RIGHT_LIMIT proof 进入可规划闭包；post-JOIN LIMIT、
DISTINCT、QUALIFY、SEMI/ANTI 的输出上界不证明 single match。LEGAL_UNPROVED 的
downstream enforcement 在 LIMIT0 下仍然存在。全项目 ERROR 阻止规划，完整诊断
tuple 保持；无关有效 SET limitation 或 warning 不成为所选结果的要求。

## 验证、观察和支持矩阵

每个结果 boundary/port、quotient field、ORDER item/expression/use、hidden requirement、
LIMIT 和 canonical image 都有 mandatory origins/demands，保留 value、membership、
type/proof、generated structure。独立 verifier 从原 roots 核对完整清单、source order、
multiplicity、严格整数 ordinal、端点、类型和作用域；删除全清单不能空泛成功。
inspection 重新验证输入，提供 result_stages/result_port/order_uses_for/
hidden_order_requirement/result_requirements 查询，拒绝 stale 或 grafted positive。

支持原语义准入的普通行、LET/WHERE、七类 JOIN、GROUPED/GLOBAL、selected/hidden
windows/QUALIFY 与 DISTINCT/ORDER/static LIMIT 组合，以及 named/imported/reexported
和 rebound consumers。保留隐藏/部分 grouping determinant、已证明的可见 key/FD、
selected/hidden window 分离、original window bindings 和 depth12 binding sharing。
支持 Bool/Int/Text/Date/Timestamp/UUID/合法精确 Decimal 的可见等价；Float（含 alias、
有限 literal）、Any/Bytes/Json、缺失 Decimal 证据保留原 non-positive outcome。
无关未选择 Float 和 non-DISTINCT ORDER/LIMIT 不受可见等价限制。

Slice2 的 FUTURE_BODIES、combined blockers、无关 limitation/error、named ancestor、
forged-concrete 控制，以及 Slice3/4/5/7 临时负例完成迁移。新正例走正常源码到
completion、VERIFIED IR、plan、independent verification、inspection；剩余拒绝使用
有效 SET body 或明确缺失证据。Slice6 当前控制保持，无需编辑。

新 transport 使用 invocation-local indexes、迭代 graph/operand/witness 遍历；引用
共享原有图，不建立持久缓存。成本按实际阶段、端口、用途、类型/proof 和 provenance
边计；原始上游 FD analysis 成本另计。没有新 evaluator、optimizer、pass framework、
数据库/reference executor、机器时间阈值或性能提升声明。

## 门禁与保留范围

作者 self-review 与 Ponytail review 不称第三方审查；独立实现的 verifier 也不是
第三方审核。修复组/validator starts/commit/push/CI 收据在仓库外持续累计；上限为
6/4/1 initial commit，以及剩余修复预算内至多 1 个自然 CI repair child。

最终内容冻结后要求 Python3.12/3.13 focused/affected compatibility、Ruff/format、
production/test Pyright、Python3.13 authoritative validator 和 generated/golden/package
门禁成功，再封存实际测试 tree 并普通发布。自然 exact-head CI 两版 Python 的四个
步骤成功才成立发布终态。唯一 lifecycle/inventory readers 继续负责当前状态和
production195/test453；无新 mutable-document reader。

没有新 syntax/public API/CLI/schema、DISTINCT ON、OFFSET/ties、SET planning、scalar-call
扩展、literal binding、target assessment、backend lowering、SQL emission/execution、
portable format、differential family、依赖、workflow、version 或 golden 变化。
Phase64 COMPLETED，Phase65 ACTIVE；Slices1–8 PUBLISHED 后，Slice9 NEXT / NOT IMPLEMENTED，
Slices10–16 NOT IMPLEMENTED，N16 不变。
