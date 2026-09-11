# Phase65 Slice4 Row Scalar, LET And WHERE Stage-Value Planning v1

基线 `56fe50b685692ff5ed9e58202d7116ae5a221775`，tree
`f99b74e38d81bdc61aaffeea5abf0072734238c3`，parent
`adb55b84e60f1fc1439e5b7f6e2d9fae81dba12b`；自然 CI `34562319623`
为 push/main/attempt1/success。D65.01–D65.12 与 N16 保持。

## Evidence and support

前置真实源码矩阵确认：直接、named、imported scalar 和 dependent LET 使用
historical reused IR；普通 WHERE 具有 ROW_FILTER，但原先没有保留谓词类型或
检查非 Bool、缺失名称。SET 下游的真实 replay 使用 completed Query Block IR，
其 ProjectNoJoinScalarExpression 已保留完整类型图，WHERE 已检查 Bool。
SET 及其下游仍不构成此 Slice 的 whole-plan positive。Replay 的引用 ledger 在
completed construction 中，依真实 replay schema/LET scope 调用现有 reference
collector 保留一次；其类型图直接引用已有 scalar analysis，不重新推断。

普通 SELECT 在 relation 持有的 ProjectModuleSelectExpressionFact 中保留原已计算
类型图与 exact selection/input/LET context，既有 SelectFact 布局保持；LET 保留
已有 analyzer 的类型图与诊断；
WHERE 在语义事实构造时使用既有 row expression kernel 与 Bool checker。
证据绑定 exact owner、实际输入 schema、LET scope/prefix 和 authored occurrence。
completed 边界保留新增的既有规则诊断，不在 planner 中生成语义错误。直接字段
错误继续由原 helper/semantic diagnostic 路径拥有，不能重新推断后重复追加。

| Authored domain | Planning contract |
| --- | --- |
| Literal, resolved Name/DottedName | 原 AST/value/type/nullability；不提取 binding |
| Unary `+`/`-`; binary `+`/`-`/`*`/`%`/`and`/`or` | 有序 operands、原 operator 与上下文类型证据 |
| Comparison, IS NULL, BETWEEN | 既有语义允许的操作与 NULL 证据，无新 coercion |
| Ordered LET | 每个 authored binding 一个定义，后继通过 private port 使用 |
| WHERE | 精确输入 stage、Bool/NULL 类型，SQL TRUE-only membership |
| Calls | 缺少实际 callable/argument authority 时 typed unavailable |
| JOIN, GROUP/GLOBAL/satisfying, windows/QUALIFY, DISTINCT/ORDER/LIMIT, SET | whole-plan typed unavailable，包括 reachable ancestor |

当前 grammar 不接受 unary NOT，既有除法类型为 UNKNOWN；unknown callable
如 coalesce 保留既有错误。WHERE 的部分 UNKNOWN operand evidence 可在 semantic
success 下形成 typed planning limitation，不能伪造新的语义 ERROR。

EXPLICIT_MODULES、whole-project completed.ok、exact VERIFIED Query Block IR 和
显式同 snapshot TABLE/QUERY selection 仍是入口要求。Unrelated valid unsupported
body 不阻塞 healthy selected closure；任何 whole-project ERROR 均阻塞。

## Stage transport

保留 Slice3 的 named definition/input binding seam 及其 repeated-use graph。
生成 SELECT block scope 与 named definition 分离。每个 LET 建立 stage value；
边界导出 predecessor 值，后继 scope 只引用本 scope 的输入端口。WHERE 位于 LET
之后、最终投影之前。IR 的 RELATION_INPUT 仅对应首次 block，ROW_FILTER 与
FINAL_PROJECTION 对应实际 WHERE/最终投影 block；纯生成的后继 LET block 不
复制整条 IR ledger。即使最终只选 literal，也保留 source BAG 与所有 hidden
membership dependencies。不做 DCE、CSE、pushdown 或物理 evaluation-once 推断。

Private helper ports 不伪造 canonical semantic identities，不进入 plan.exports。
最终多个输出可引用同一 LET 定义，仍保留各自 canonical output identity。
Named/imported/reexported consumers 保持 immediate producer exports 与完整 origin
paths。绑定层的 depth12 sharing/lookup 检查仍独立于 whole-plan verification。

表达式、ordered child/use edges、LET、filter、helper 和 scope correspondence 均有
origin 与 mandatory demand。Demand 声明所需 operation/type/NULL/representation/
TRUE-only 行为，不声称 target capability、lowering、purity 或 runtime fulfillment。

Verifier 独立检查 supplied witness 与真实上游事实，不调用 plan/expression builder、
binding allocator、semantic inference 或 name resolver。Runtime inspection 暴露实际
typed inventories 与 exact-ref lookup，并重验 stale positives。采用迭代遍历和每次
调用的局部索引，无 shared-DAG expansion 或持久 cache。

## Acceptance and publication

Slice2/3 的 scalar/LET/WHERE temporary negatives 迁移为正向；原 unsupported/graft/
ancestor 属性使用真正仍不支持的 ORDER/LIMIT 等有效 fixture 保留。覆盖 context/
prefix/operand/port/filter/origin/demand 篡改、空集合、foreign root、helper 泄漏，
以及语义构造和 plan allocation 的 monkeypatch 禁调用检查。
上下文 container/dependency/LET/selected-output ordinals 必须为实际 `int`；
准入、独立 verifier 与 stale inspection 均拒绝数值相等的 `Bool` 替代。

两个早期审计中的 current-source readers 随上下文扩展迁移：

- `tests/test_phase61_slice1_project_ir_architecture_source_audit_route_lock.py`
  检查唯一实际 class、既有必需字段及其相对顺序，并检查新增 WHERE/SELECT
  context 注解；不再冻结整个 semantic carrier 的字段总表。独立 RelationIR
  shape 检查保留。Slice4 的真实构造与篡改测试验证 context payload 的 exact
  selection/owner/input/LET 归属、不可变类型图和非正向拒绝。
- `tests/test_phase63_slice1_joined_query_block_product_architecture_source_audit_future_roadmap_route_lock.py`
  使用唯一顶层 AST ClassDef，检查 reference/select class 自身的 ordinals、
  candidate/field/reference 注解及实际 role type-parameter bounds。类型参数名字、
  声明换行不成为身份；注释、字符串、嵌套或近似名字的 class 不能满足检查。

这些是当前源码 reader 的兼容迁移，不修改旧 phase contract 的历史结论。

前景 author self-review；独立 verifier 不称第三方审核。独立上限为六个因果修正组、
四次 authoritative starts、一次 initial ordinary commit，至多一个普通 CI repair
child。仓库外 evidence ledger 保持累计计数。

最终验证包括 Python3.12/3.13 focused 与 affected compatibility、Ruff/format、
production/test Pyright、Python3.13 authoritative validation、generated、goldens、
installed package，然后 ordinary commit/fast-forward push 和自然 exact-head
push/main/attempt1 的两版 Python 四项步骤。没有 SQL emission、portable format、
target assessment、binding extraction 或 execution；Slice5 单独授权。

实际写入闭包为 A3/M14/D0，十七个获准路径；production191/test449，由既有 sole
inventory reader 验证。生命周期仅由既有 active-phase reader 验证。
