# Phase65 Slice9 SET Query-Expression Bodies And Positional Ports v1

本交付沿用 D65.01–D65.12、N16、EXPLICIT_MODULES、whole-project completed.ok、
exact VERIFIED Query Block IR 和同一快照的显式 TABLE/QUERY owner selection。
SetRelationDef 是既有 TABLE/QUERY 的 body 分支，没有新增 selected-owner 类别。
成功普通 commit、fast-forward push 和自然 exact-head CI 后，Slices1–9 发布，
Slice10 NEXT；Phase65 继续 ACTIVE。

基线 commit `86bf4e6e5a525e0c099339f0ea29c4b51ab57f04`，tree
`a813b16992cb2d355aa61a8eac259c3ee715bc69`，parent
`0966ecb309f6243baf4490a423ebcb47af1f909c`；自然 CI `34686688681`
为 push/main/attempt1/success。写前实时 fetch、refs、工作区、index、Git 操作和
相关进程已核对；本 Slice 使用独立累计预算，不继承前一 Slice 的权限。

## 原始证据与实现

24 个正常构造前置案例覆盖六种形式、直接 TABLE/QUERY SET selection、Float、
重复/三 operand/nested graph、Decimal parents、window/QUALIFY/DISTINCT/ORDER/LIMIT
operand 与下游 JOIN。成功项确认为 ProjectIRCompletedSetOperationOutput，
而非仅有 VERIFIED 标志的 terminal。上游语义、IR、类型与 proof producers 全部只读。

| 既有证据 | 新计划对应与用途 |
| --- | --- |
| ProjectSetInputScope / ProjectSetOperation | ProjectSQLSetBody 保存 exact operation、kind/quantifier/multiplicity、equivalence/uniqueness posture、row domain 和 active properties |
| ProjectSetOperandUse / ProjectIRSetOperandInput | 每次独立 ProjectSQLSetOperand 保存 source、resolution/dependency 所属的 binding use、active producer 和全部字段 |
| use.fields / ProjectRowEquivalenceInput | 每个 ProjectSQLSetInput 保存确切 binding port、producer terminal port 和原 type/equivalence evidence |
| ProjectSetColumn / ProjectCompletedSetOutputField | ProjectSQLSetColumn 保存全 operand 的同位置 inputs、value sources、原 completed/IR field 和 SET-owned output |
| canonical exports | 既有 ProjectSQLResultPort / ProjectSQLResultExport 保存实际可用值及最终 canonical 映像 |

没有为 SET 构造 SelectItem、scalar projection、SELECT block 或 ProjectDistinct。
SET column 是 positional correspondence，不是逐列独立 set operation。语义 field
identity 属于 SET owner；label 采用第一个 authored operand 的既有 label。
后续 operand 不按名字对齐，不选择 first available，不推断 cast、公共类型或 Decimal
widening。输入的 aggregate/window result role 在 SET 本地仍是 ordinary_row_value，
其计算来源继续通过原 evidence 保留。

## 终端值与共享图

所有 named SELECT/SET 都有 mandatory terminal export mapping；普通无尾部 SELECT
也使用 projection result port。SOURCE 使用确切 source output。Binding 仍描述逻辑
definition/use/canonical identity，whole plan 通过完整 terminal mapping 给出值的可用性。
SET input 直接保存该 terminal 对象，SELECT/JOIN consumer 的 input_terminals 查询
同样通过映像到达最终值。缺少任何 producer terminal 不能由相同 canonical identity
补足；独立 verifier 检查全体 named mappings。

SET body 按原 dependency-first schedule 构造，读取 invocation-local terminal index。
每个 definition 只存在一次，每次 operand use 独立；输入顺序、arity 和嵌套保持。
逻辑 fold 明确为 source_order_left_fold，不 flatten 或 reassociate EXCEPT，不展开 BAG
multiplicity，也不复制所有 transitive paths。Depth12 的 p0–p12 保持 13 definitions/
24 uses，另计 source/result wrappers 的 2 definitions/2 uses；现为完整 plan/verifier/
inspection 正例，原 binding checks 保留。

Operand 内的 DISTINCT、ORDER、LIMIT 和 row/JOIN/group/window/QUALIFY 边界保持。
SET 输入只包括可见输出，不包括隐藏 window、QUALIFY、分组键、排序 helper 或 pending
hidden ORDER value。SET 本体仍 ordering=None、limit=None；外层结果条款来自真实 authored
named SELECT consumer。输入次序与逻辑 fold 不承诺物理求值次序、次数或展示排序。

## 六种语义与类型、membership 要求

保留原 multiplicity law：UNION ALL 为 m+n；UNION DISTINCT 为非空并集的一份；
INTERSECT ALL 为 min(m,n)；INTERSECT DISTINCT 为两侧均存在时的一份；EXCEPT ALL
为 max(m-n,0)；EXCEPT DISTINCT 为仅左侧存在时的一份。这里只保存结构和要求，
生产代码不计算这些 multiplicities；已有小型 test oracle 仅作为语义参考。

UNION ALL 只要求原有 concrete compatible types，允许上游准入的 Float/Any/Bytes/Json，
其 equality-unavailable reason 不变成 blocker 或 equality demand。其他五种形式要求
完整原 row-equivalence；Float 等既有 non-positive outcome 不改变。类型相同不表示
来源相同；所有 input capability、alias/nominal identity、Decimal(p,s)、TypeExpr 和
parent chains 保留原对象。外层 DISTINCT 不绕过原等价限制。

每个 output column 保存全部 operand 的 type/NULL/correspondence。EXCEPT value_inputs
仅来自左侧，所有右侧输入仍贡献 membership、comparison 和 source/type requirements。
完整行比较属于 SET body，不能删除全部字段或全部 demands 后空泛成功。Set DISTINCT
使用原 ProjectSetFullRowUniqueness，与 SELECT DISTINCT、小 key、FD、grain、cardinality
分别保留。原 operation-specific NULL、domain/origin、keys/FD/grain 及 global/subset
特例通过 exact active property witness 运输，不运行 solver 或增强保证。

## 组合支持与真实限制

六种 SET 支持 direct sources、TABLE/QUERY 直接选择、不同 label 的多列位置对应、
named/imported/reexported operands、自引用式重复 use 和嵌套。原准入的 row/LET/WHERE、
JOIN、group/GLOBAL/satisfying、window/QUALIFY 和结果条款可作为 operands。SET 输出可进入
row、JOIN、window/QUALIFY、DISTINCT/ORDER/LIMIT，以及上游准入的聚合路径。

正常源探针确认：直接 SET→GROUP/GLOBAL 目前上游返回 PIE-S2333；JOIN 或显式 SELECT
bridge 后的聚合可以完成。保持这个边界，没有暗中增加 bridge 或修改上游 admission。
Slice8 的 Decimal-parent fixture 已提升为 SET→DISTINCT 完整计划；另有真实
SET→JOIN→DISTINCT→SET 及 imported/nested controls，未合成 parent evidence。

完整 project diagnostics 保持原 tuple。全项目 ERROR 即使在空 operand 或外层 LIMIT0
下仍阻止规划；无关有效 callable-authority limitation 不污染所选闭包。原 source
realization、aggregate risks 和 single-match assessments/diagnostics/units/proofs 均在
value 与 membership closure 中保留。EXCEPT 右侧的 WARNING/enforcement 不丢失。
SET uniqueness/subset 或后续 LIMIT 不制造 single-match proof；operand 中的隐藏
STRICT-FD ORDER realization 继续 pending。混合 connector 不成为 federation 证书。

## 独立验证与 observation

每个 body、operand、input field、column、output/terminal port 都有 mandatory origins/
demands。Body 分别要求 operation/quantifier/multiplicity/membership、property/domain，
以及适用时的 whole-row equivalence。UNION ALL 没有伪造的 equivalence requirement。
Input type/NULL/representation 与 value/membership provenance 分开保留。

独立 verifier 从原 roots 核对全部 definitions/uses、scope prefix、位置、严格整数
ordinal、active producer、terminal membership、原 field/type-parent/NULL/properties 和
mandatory inventories。它不调用 plan、binding、result、SET、type/equivalence allocators，
也不调用会重构证据的 upstream validate/field_parts 或 solver。Type-parent 遍历采用
invocation-local indexes 与 iterative cycle-safe checking，保留共享结构。

inspection 重新验证输入；set_body、operands_for_set、fields_for_set_operand、
set_requirements 暴露真实非 SELECT body，terminal_exports/input_terminals 暴露当前值。
result_stages 对 SET 返回 SET body，不制造 projection。查询只接受 exact refs；
stale/grafted positives 与缺失证据不会被观察器修复。索引只属于当前 invocation/view，
没有 persistent cache、pass/plugin registry、evaluator 或机器时间阈值。

Slice2 FUTURE/combined/unrelated/ancestor/forged controls、Slice3 depth12/imported/shared/
ancestor、Slice4 replay/repeated scalar 和 Slice8 Decimal parents 完成迁移。新支持的 SET
走正例；仍需拒绝的性质使用正常 admitted trim/len call，并显式检查 completed.ok、
VERIFIED IR 和 call_authority_unavailable。Slice5–7 既有控制继续运行，历史合同不改。

## 验收与发布

既有 sole lifecycle/inventory readers 更新为 production196/test454。最终输入冻结后
要求 Python3.12/3.13 new/affected compatibility、Ruff/format、双 Pyright、Python3.13
authoritative validator 及 generated/golden/package gates。实际 tree 与外部 receipts
匹配后，普通 commit/fast-forward push 和自然 exact-head push/main/attempt1 CI 两版
Python 的四项步骤成功才建立发布终态。作者 self-review/Ponytail review 不称第三方审核。

预算累计上限 6 correction groups、4 authoritative starts、1 initial commit、余额内
至多 1 个 CI repair child；真实失败与启动保存在仓库外，未重置或借用旧 Slice 预算。
没有新语法、BY NAME、隐式 quantifier/coercion、新 type/equality/property/proof 规则、
SET-local ORDER/LIMIT、optimizer/backend strategy、literal binding、target assessment、
portable format、differential family、SQL emission/execution、公共 API/CLI/schema、依赖、
workflow、版本或 golden 变化。Phase64 COMPLETED；Phase65 ACTIVE，Slices1–9 发布后
Slice10 NEXT / NOT IMPLEMENTED，Slices11–16 NOT IMPLEMENTED，N16 不变。
