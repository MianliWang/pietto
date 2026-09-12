# Phase65 Slice10 Typed Fixed-Literal Envelope And Bind-Use Layout v1

沿用 D65.01–D65.12、N16、EXPLICIT_MODULES、whole-project completed.ok、
同快照 VERIFIED Query Block IR 和明确选择的 TABLE/QUERY。发布基线 commit
`9de7991498e2258bf41557bae95f91152c9670f3`，tree
`27dfeff90478e366eb3589544f1b9e07108d0c99`，parent
`86bf4e6e5a525e0c099339f0ea29c4b51ab57f04`；自然 CI `34715387544`
为 push/main/attempt1/success。写前已同步 refs 并检查干净 index/worktree、Git
操作和相关进程。上游 semantic/type/proof/IR producers 全部只读。

## 实源证据与清单边界

前置矩阵区分正常 completion、VERIFIED IR 与实际 concrete plan。普通和 joined
SELECT/LET/WHERE/ON 的 literal-level ValueType 来自原 expression evidence map，
没有从 schema、父表达式或 Python 值推断类型。`-3` 与 `-0.0` 的原 AST 是
UnaryExpr 包住正 LiteralExpr，负号不属于解码 payload。

| 实际消费者 | 清单与证据 |
| --- | --- |
| 普通／joined scalar sites | 保留 exact site、owner、stage、LiteralExpr、原 ValueType、root-first parent/operand ancestry 和 expression ref |
| Aggregate arguments、satisfying、QUALIFY | 保留原专用角色；已有结果引用不展开成新的 binding computation；隐藏窗口由实际 window consumer 单独枚举 |
| Window arguments | 保留每个实际 argument/default/offset/bucket/position 的 AST 与专用证据；offset/bucket 可能没有 ValueType，不能据数值发明类型 |
| Window partition/order/frame | 从每个实际 computation 的 effective components 读取原 AST；named template 的共享 AST 在不同 computation context 下分别保留 |
| Relation ORDER、static LIMIT | 原 ORDER type map、原 LIMIT literal；LIMIT0 仍是一个真实结构位置 |
| Source connector | 仅 reached source 的原 connector arguments；Text locator 不成为 data bind |
| Consumed type arguments | reached source fields 的 FieldDef.type_expr，以及已有 resolved alias edge 指向的 TypeDef.base；TypeArgument.value 的 LiteralExpr 标为结构位置，保留实际 type declaration owner 和 source-port context |

顺序为 dependency-first definitions；每个 source 的 connector、字段类型按原顺序，
SELECT 内按实际 scalar stages、window arguments/components、ORDER、LIMIT 顺序。
同一个 named definition 只枚举一次，不沿重复 input/SET uses 展开；LET 和 stage
ports 保持现有引用。Inherited frame literal 可共享 AST，但不会合并 use-local
policy contexts。来源身份是原对象和 owning context，路径仅用于既有索引查找，
候选仍须 exact TypeExpr membership。

不遍历无关 module/declaration 的表达式，也不把类型/proof metadata 中反复出现
的同一值当成新求值。GROUP 当前只接受 NameExpr/DottedNameExpr；enum members、
profile/config scalars、alias labels、effective default numbers 不是 LiteralExpr。
未使用 named window declarations、shape ensure/index/check predicates 不是当前
表达式消费者，不额外变成 literal evaluation 或 realization demand。

源码探针确认：普通 NULL 投影保留原 PIE-S2333；普通 trim 等 scalar calls
仍可能是合法语义、但缺少 planner callable authority 的 typed unavailable。
常量聚合和计算 LET 直接／命名进入部分窗口路径也有原有准入限制，分别记录为
前置负例，不声称成功 preservation。已准入的 computed LET→aggregate port、
window offset/default/NULL、aggregate transform、satisfying/QUALIFY、ORDER/LIMIT
和 named/imported/SET 组合使用真实正例。

## 策略与正向提取

私有 `ProjectSQLLiteralPolicy.PRESERVE_LITERALS` 是默认；显式选择
`BIND_SAFE_LITERALS` 才提取。两个策略都没有 replacement-value 参数，不改变
原语义或 planning admission。ProjectSQLBindings 仍仅表示 relation graph。

每个 inventoried site 是 BOUND 或 PRESERVED_WITH_REASON。判定顺序固定：

1. 默认策略统一保留为 preserve_policy，并保留原角色／证据。
2. 专用和结构角色优先保留为 specialized_or_structural_context，即使没有类型。
3. 只有 SELECT、row LET、WHERE、authored ON 有资格；未知角色、缺少实际
   expression consumer 或未知边为 unknown_extraction_context。Call subtree
   有独立 call_argument_subtree 原因。
4. Untyped NULL 保留；缺少 exact known literal ValueType 为 literal_type_unavailable。
   只有 TypeKind.BUILTIN、无 nominal definition 的 Bool/Int/Text/Float 准入。
5. 原 decoded payload 必须有精确 Bool/Int/Text/Float tag，Float 必须 finite；
   非准入 builtin、错误 representation 和 nonfinite 分别有保留原因。

正向 ancestry 仅沿当前 unary/binary/comparison/Boolean/IS NULL/BETWEEN scalar
edges。GROUP、aggregate/call/window arguments/defaults、satisfying、QUALIFY、
window policy、relation ORDER、LIMIT、connector 和 type arguments 不提取。
缺少 extraction evidence 意味着保留；底层计划本身的 mandatory evidence 缺失
仍然拒绝。已经 BOUND 的站点不得在 envelope 失效时回退到源字面量。

## Slot、真实 use 和固定 envelope

每个 slot 属于 exact planning scope、原 literal 和实际 definition/context。
相同值的不同 source sites 各有 slot。当前 non-fusing graph 中每个被提取的
表达式叶有一个真实 use；LET/producer reuse 不制造额外 uses。Depth12 重复 SET
的单个定义 literal 仍只有一个 slot/use；这不是 physical evaluation-once 保证。

`ProjectSQLBoundLiteral` 与 `ProjectSQLLiteral` 是 expression union 中不同的
closed leaf。Bound leaf 保存原 AST/site/ValueType 和确切 ProjectSQLBindUse。
既有 `inspection.expression(ref)` 返回这个实际叶；`literal_value(ref)` 沿其
use/slot 读取固定 payload，preserved leaf 则保持原 literal transport。
没有 AST rewrite、LET expansion、folding、CSE、optimizer 或 SQL placeholder。

不可变 schema/envelope 保存有序 slot/value associations；payload 直接取原已解码
值，禁止 caller rebind。独立 checker 核对 exact schema、scope、policy、ref kinds、
strict int ordinals、完整顺序与原 source value。缺失、多余、重复、错序、foreign、
错误 tag、mutable/malformed payload 均拒绝。空值表只适用于实际零 bound sites。

Bool、Int、Float 不依赖 Python 的宽松数值相等；Float 使用 finite 检查和
`float.hex()` 精确比较，区分正负零。负零源码仍保留 unary minus 包住正零的结构。
Text 不重解码或规范化 Unicode，Int 不增加 backend range 限制；传输值正确不等于
目标参数的 type/overload/collation 正确。

独立 `verify_fixed_literal_envelope` 是实际 whole-plan verifier 的调用路径。
它核对 literal schema/source transport；原 semantic/IR、relation/stage invariants
仍由 whole-plan verification 负责。验证记录捕获 policy 与 envelope 对象；换
policy/root/context/envelope 后必须重新构造适用产品并 fresh verify。内容相同的
envelope wrapper 也不能沿用旧 positive。缺失字段和 stale/grafted inspection
归一化拒绝，不修补、不切换 policy、不恢复 payload。

## Origins、demands 与验证

每个 literal site、slot、fixed value、bind use 都有 mandatory role-tagged origin。
原 authored Span 保持 one-based half-open parser character coordinates；escaped
和 non-BMP Text 的 decoded length 不代替源码范围。Type 参数保留原类型声明 owner，
与消费它的 source definition/port 分开。Use 的 generated-transport origin 保留
ordered slot/expression antecedents，value/membership/type/generated 角色不混用。

每个 actual bind use 都有 ProjectSQLLiteralDemand，链接 slot/fixed value、原
literal 和全部 ancestor expression demands，保留原 operator/ordered operand types。
必需要求为 exact data representation、nullability、range/precision、typed operand
context，以及适用的 collation/overload；没有 target support 或 fulfillment 标志。
之前的 source/JOIN/aggregate/window/quotient/ORDER/LIMIT/SET 要求均保留。
LIMIT0 与 EXCEPT right-only membership 不删除定义 literals 或 single-match warnings。
Float binding 不解除五种 equality-requiring SET 的限制；直接 SET→GROUP/GLOBAL
仍保留 PIE-S2333，已有显式 bridge 规则不变。

独立 verifier 通过共享的纯 retained-shape traversal 重建完整 expected positions，
自行实现 eligibility/reason 检查，不调用 builder classifier、slot allocator、
semantic inference、name resolution 或 type solver。检查每次 context、AST/span、
literal-level type、slot/use、真实 expression transport、envelope、origin 与 demand。
同时删除全部新清单不能空泛通过。实际消费者和 stale-positive 测试包含 producer/
classifier 禁调用控制。只在调用内使用索引；迭代 ancestry links 在真实 literal
处展开路径，成本计入实际 materialized ancestry，不复制中间表达式的全部前缀。

Private full inspection 可读取 authored values，是 source-bearing view，不是 redacted
export。错误只返回封闭 issue/固定消息，不转储 payload。逻辑 slot 顺序不是 Phase66
statement/driver placeholder 顺序；SQL type anchors、emitted occurrence mapping、
target assessment、driver integration 和 execution 均未交付。

## 门禁与生命周期

最大 A3/M21/D0；本交付的源代码只增加 literal owner，并修改 plan、expression、
verification、inspection 四个既有模块。旧 Slice2–9 默认策略断言保持。
sole inventory reader 更新为 production197/test455，sole lifecycle reader 更新当前
状态。历史合同、public/portable APIs、grammar、SQL、dependencies 和 golden 不变。

作者 self-review/Ponytail review 不称第三方审查。累计 correction groups、validator
starts、失败、sealed tree、commit/push 和 CI 收据位于仓库外；预算为 6/4/1 initial
commit，余额内至多一个普通 natural-CI repair child，禁止 reset/rerun/amend/force。
第 4 组后已复查完整剩余 finding set 和收敛情况。

最终内容冻结后要求正常 locked Python3.12/3.13 focused/default/bound matrices、
Ruff/format、production/test Pyright、Python3.13 authoritative validator、generated、
goldens、package-smoke 全部通过。一次普通 commit/fast-forward push 后，自然
exact-head push/main/attempt1 的两个 Python jobs 四项步骤成功才建立发布终态。
成功时 Phase64 COMPLETED，Phase65 ACTIVE，Slices1–10 PUBLISHED；Slice11 NEXT /
NOT IMPLEMENTED，Slices12–16 NOT IMPLEMENTED，N16 不变；没有启动 Slice11。
