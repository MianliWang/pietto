# Phase65 Slice12 Forward And Reverse Source-Map Queries v1

沿用 D65.03/.09/.10/.11、N16、whole-project completed.ok、exact VERIFIED Query
Block IR 和显式 TABLE/QUERY selection。基线 commit
`a7a48a1e3c7b288e051213fdb163dd7226d0cd60`，tree
`c9472766324a40c543c97c2f17bce897a7dfdd27`，parent
`0c025b1060a93b9ab0999f71575830b7c25757ed`；自然 CI `34739921800`
为 push/main/attempt1/success。写前同步并检查 refs、工作区、index、Git 操作和进程。
Slice11 的历史 observation loss 保持原记录，本交付不重开其恢复或预算。

## 产品与精确入口

`project_sql_plan_source_maps.py` 提供独立只读 ProjectSQLSourceMap。
`build_project_sql_source_map` 消费 exact current ProjectSQLPlanVerification，
保留原 plan、verification、literal policy、fixed envelope 和 diagnostic tuple；
completed/IR/selected-owner roots 通过原 verification 与 plan.scope 保持原身份。
构造、独立 verification 和 inspection 边界均使用原 captured request fresh verify。
bindings-only、unavailable、failed/foreign/stale roots 和旧 envelope request 均拒绝。

真实入口为 `ProjectSQLPlanInspection.source_map()`，连接 build → independent
verify → runtime view。报告和 source map 是独立的 optional consumers，计划不依赖
其中任一个。Requirement entry 通过原 demand ref 和 origin ref 查询地图，不创建
report-specific plan identity，不要求先构造 report 才能解释 literal/output。

## 映射域与来源归属

Flat entries 严格对应原 `plan.origins`，每个 origin occurrence 恰好一个 entry，
保留原 subject、role、provenance、owner、cause、evidence 和 ordered antecedents。
多个 origin 可以拥有同一 subject，不能选第一个或按值、span、名字合并。

Subject 域来自全部 original-origin subjects，包括 definitions、ports、expressions、
scopes、symbols、boundaries、demands 和 plan-scope selected-owner case。Origin refs
是另一种 endpoint。这里不复用 Slice11 较窄的 report subject-query 域。

Source 域是同一 plan authority 已保留的 logical modules/parsed inputs。只遍历其
原 AST 和 closed frame containers 来建立 invocation-local membership index；
不读取文件、重解析、realpath/case-fold 路径或调用 resolver。未关联的已拥有 AST
仍可用于合法空查询；没有因此添加未选择 declaration 的 plan origins 或 demands。

一个 SourceSite 由实际 module/parsed authority、原 AST occurrence 和实际 container/
declaration membership 识别。共享 named template 的原节点只分配一次 site；不同
节点即使 span/text 相等也不同。来源的 declaration/container、消费它的 plan definition、
display path 和原 coordinates 分开保存。Relationship metadata 的 container 保持原
relationship declaration，不改成消费它的 query。

| 原保留证据 | 直接 source association |
| --- | --- |
| 每个 origin.cause | 原 cause 的 AST membership；即使 cause 很宽也保留它 |
| SelectItem/LET/predicate/order item | 原 expression body；不从 label 猜位置 |
| ProjectIROutputFieldOccurrence / ProjectRowField | 原 FieldDef 与 TypeExpr；保留外部 shape/type declaration |
| 原 reference_provenance / origin_path | 原 nominal target、type terminal、ordered import/reexport items |
| Source descriptor | 原 connector AST，locator 不重新解释 |
| Window / WindowPolicy | 原 authored expression；实际 effective-to-authored correspondence；已有 named target/reference 与实际 local/inherited components |
| Literal site/slot/value/use | 原 LiteralExpr、原 type owner 与实际 consuming definition；不重新提取 literal |

Attribution 中的 occurrence identity 是它原有的结构 locator，用于查找同一 rooted
attribution 表中的确切 request/facade/target；随后仍须验证原 AST 对象 membership。
保留原 path/hop/attribution 对象和原顺序，不进行新的名字解析或 path-string 认证。
只消费已有 concrete provenance；没有的 finer semantic lineage 不被下游推断。

## Authored correspondence 与 generated explanation

当前 role taxonomy 闭合地区分 syntax correspondence 和 generated structure。
Syntax correspondence 表示计划节点有实际 AST 对应，不表示该 plan ref 本身就是 AST。
Generated scopes/ports/symbols/definitions/uses/demands 等以其原 closed origin role、
原 witness 和 ordered antecedents 作为生成理由，不从“有 span”推出 authored subject。
这些 entry 没有自造 source span；它们的 authored cause 是解释上下文。

SELECTED_OWNER、DEFINITION、SOURCE_DESCRIPTOR 等已有 root reasons 可以没有 antecedents。
不为满足非空规则制造边。BOUND expression 仍指向原 literal AST，slot/fixed value/
bind-use 运输记录分别保留其生成理由和原来源；没有 AST rewrite 或 caller rebind。

Named-window effective WindowExpr 通常不是 authored tree 的新 occurrence。
EFFECTIVE_WINDOW association 保存 observed effective object、原 authored site 和实际
window witness。不能凭 copied span 把 effective node 放进 authored reverse index。
组件直接使用已有 effective component 所引用的原 AST，因此 inherited component 能回到
原 named declaration；defaults 和非 AST frame scalars 不制造新 source sites。

## 坐标与 unavailable compatibility

Mapped AST sites 保存原 Span 对象及其原字段快照：one-based、half-open parser character
coordinates。Escaped/non-BMP Text 的 decoded value/length 不替代源码范围；没有 UTF-8、
UTF-16、LSP 或 SQL offset 转换。display_path 来自原 logical module，不覆盖原 position.path。

原 ProjectRowField.provenance.location 作为独立 legacy-position evidence 保留：
None 是 UNAVAILABLE；原 end coordinate 缺失是 PARTIAL；其余为 COMPLETE。
这些记录不冒充 AST sites，也不认证任意同 span 对象。原 FieldDef/cause 的有效来源
关联仍然独立存在，不用 owner span/line1/零宽位置填补 legacy absence。

坐标必须为 exact positive int，Bool 拒绝；已知 end line 早于 start line 即使另一
end coordinate 缺失也拒绝。完整范围不能倒置。当前真实 authored AST Span 必须完整，
把 end fields 删除的伪造 Span 是错误，不标为 legacy unavailable。Partial SourceLocation
compatibility 单独测试，不把合成历史位置宣称为新 authored-map 功能。

## 查询语义与有序关系

Runtime view 提供：

- `subject(ref)` 返回该 owned subject 的全部原 origin entries；`origin(ref)` 只接受
  exact origin ref。`associations(ref)` 返回该 subject/origin 的全部直接 source associations。
- `reverse(source, occurrence)` 验证 exact authored membership，返回全部直接关联的
  plan/origin occurrences。位置相等不能使 foreign/effective AST 通过此入口。
- `at(source, line, column)` 使用 start ≤ point < end；`overlapping(source, start, end)`
  使用半开区间相交。返回全部匹配 associations，不选 nearest/first。相等 endpoints 是
  合法空范围，反向范围拒绝。正整数但无匹配的坐标返回空；不读取源文件推导行长边界。
- `antecedents(ref)` / `dependents(ref)` 是精确直接 link occurrences，endpoint 明确为
  ORIGIN 或 SUBJECT。前者解析到确切 entry，后者解析到确切 subject 及其全部 origins。
- `explain(ref, transitive=False)` 只含直接 origin/source associations；显式 transitive
  模式迭代遍历保留的 antecedent relationships。`visited` 是完整 reached entries，
  `origins` 可按 provenance 过滤；过滤不剪断 traversal intermediates。Links 保留每次
  原 occurrence，结果 entries 按原 inventory order 各返回一次。

原 VALUE、MEMBERSHIP、TYPE_PROOF、GENERATED_STRUCTURE 从不合并成 guessed path role。
例如 demand TYPE_PROOF → input MEMBERSHIP 两条事实都可见。EXCEPT right、SEMI/ANTI
matching、WHERE/satisfying/QUALIFY、hidden group/window/order 和 single-match premises
仍可解释，但不变成可见 result fields，不履行风险或 enforcement。

原结果容器/port ledger 可以包含结构性回指。Source map 保留这份已经 Layer1 验证的
关系；它不是新的 database-value causal DAG。Visited traversal 能处理这些原回指，
reverse indexes 不增加 causal edges。任何新增/丢失/错位/foreign endpoint 都会拒绝。
不展开所有 transitive paths，不把 producer origins 为每个 consumer 再复制一份。

## 独立验证与覆盖

Layer1 调用现有 whole-plan verifier。Layer2 独立检查 original-origin coverage、
role/nature/reason、consumer 与 authored ownership、各 finer evidence route、原 AST
membership、坐标、endpoint kinds、所有 forward/reverse index members。
它不调用 map builder、origin classifier 或 position/site allocator；共享的部分仅为
closed representations、纯 retained-witness/AST traversal、membership 和 index utilities。

删除 plan.origins 由 Layer1 拒绝；删除 map entries/sites/role/associations、import hop、
reverse bucket，或调整其他库存掩盖缺失，仍由 Layer2 拒绝。检查原对象、严格序号、
顺序和 multiplicity，不以总数代替对应。旧 policy/envelope/map verification 不能被
inspection 重用为新 product 认证；未知 mapping role fail closed。

真实测试覆盖直接/重命名/重复投影、同 subject 多 origins、外部类型、import/reexport、
shared/inherited named windows、隐藏阶段、EXCEPT/SEMI/ANTI、direct/hop/whole-path proofs、
两种 literal policies、Unicode/escapes、多行与半开坐标、同 span 不同 AST、legacy absence、
depth12 sharing、双向 direct-index round trips 和原 ledger 上的独立 reachability oracle。
Report integration 仅使用原 demand/origin refs。No-reconstruction controls 禁止 inference、
names/proofs/providers、文件读取、source parsing 和 map-builder invocation。
Source-map construction 被禁用时，plan verification 和 requirements reporting 仍成立。

## 范围与门禁

本交付新增 source-map owner，修改既有 inspection 的可选入口和 Slice11 的直接互操作
测试；原 plan/origin/demand/requirements 构造与检查器均保持，没有必要的 origin-link 修复。
实际闭包 A3/M6/D0，九个获准路径；sole lifecycle/inventory readers 更新为 production199/
test457。历史合同、Slice2–10 tests、grammar、upstream kernels、public/portable APIs、
emitters、providers、dependencies、workflow/version/golden 均不改动。

作者 self-review/Ponytail review 不称第三方审核。计数与真实启动/失败/结果持续写入
`~/.local/state/pietto/evidence/phase65-slice12/`。上限为 6 causal correction groups、
4 authoritative starts、1 initial ordinary commit，以及余额内至多 1 ordinary CI child。
无 budget reset、amend/rebase/force、manual CI rerun/dispatch 或 status-only follow-up。

最终内容冻结后要求正常 locked Python3.12/3.13 focused/compatibility、Ruff/format、
production/test Pyright、Python3.13 authoritative、generated、golden、package 全部通过。
实际 tested tree 封存后普通 commit/fast-forward push，自然 exact-head push/main/attempt1
两个 Python jobs 的四项步骤成功才成立发布终态。

成功时 Phase64 COMPLETED；Phase65 ACTIVE，Slices1–12 PUBLISHED，Slice13 NEXT /
NOT IMPLEMENTED，Slices14–16 NOT IMPLEMENTED，N16 不变。没有开启 Slice13、推断额外
database value lineage、redaction、SQL offsets、target support 或 execution/fulfillment。
