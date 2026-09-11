# Phase65 Slice5 Seven JOIN Kinds, Match Scopes And Obligations v1

基线 `d87070d9ab0a261dd0f55f7ef1aceeee966b03dc`，tree
`d001229f4ab6815d76ab27eb7963e472cb86d983`，parent
`56fe50b685692ff5ed9e58202d7116ae5a221775`；自然 CI `34574113991`
为 push/main/attempt1/success。D65.01–D65.12 与 N16 保持。

## Evidence and scope

真实源码前置矩阵覆盖七种 kind、generic ON、relationship/refinement、self-JOIN、
多跳 INNER 路径、累积 LEFT 后的 RIGHT、joined LET/WHERE 和 named consumer。
新式 JOIN 的当前映像位于 Query Block IR `join_prefix`；稳定的旧 relationship
JOIN 位于同一 snapshot 的 `retained_joins`。两者都提供 ProjectIRComposedJoin、
原/当前 input correspondence、output 与 property authority，无需重建 JOIN IR。
多跳路径的中间 producer 属于 evidence closure，不能只遍历 authored FROM/JOIN
dependencies。Authored bindings 与实际二元输入分别保留；中间输入不伪造 binding。

唯一上游生产变化是 ProjectJoinedLetValue 保留 analyzer 已计算的有序 resolutions。
保存点仍是原构造点；完整叶覆盖、实际 namespace/prefix、target 与 value_types
必须一致。无引用的表达式才允许空 resolutions，不添加 inference/resolution pass。

EXPLICIT_MODULES、whole-project completed.ok、exact VERIFIED Query Block IR 和
显式同 snapshot TABLE/QUERY selection 保持。只规划上游已接受的 kind/mode/path
组合；没有新 grammar、语义规则、proof、public API/CLI/schema 或 IR producer。

## JOIN and row-tail transport

每个 reached JOIN 有真正的左右输入、pre-match ports、匹配条件及完整 output
images。External input 指向 exact active producer exports；internal input 必须是
同一 owner 中已建立的先前 JOIN output。缺失 producer 或较小 ordinal 不构成证明。
原/当前 introduction-use 和全部 nulling images 保持，不按名字或等值字段合并。

Relationship equality 使用既有 typed endpoint/correspondence witness；每个 path
hop 只消费自身的 base predicate。Authored ON/refinement 使用原 condition 的
references/value_types，保留与 base predicate 不同的角色；它不是 post-WHERE。
ON 看到当前 JOIN null extension 之前的左右输入，同时保留先前 JOIN 的 nulling。
CROSS 是显式 unrestricted Cartesian matching，不制造 `ON TRUE` AST。

INNER 保留匹配 BAG pairs；LEFT/RIGHT/FULL 保留既有 unmatched-side 语义与完整
null extension，RIGHT 包括整个累积 left。SEMI/ANTI 保留 left-occurrence existence
语义，right 仅贡献 matching/membership，不能进入不可见的输出或后继 namespace。
ANTI 不改写成 NOT IN，不从 grain/keys/FD 或后置过滤推导匹配数。

Joined field keys 保持 use-qualified occurrence；LET keys 保持 namespace-bound
occurrence。Joined SELECT/WHERE/LET 复用 Slice4 的 closed expression 和 stage-value
transport，新增 matching/joined context variants，不压平成单输入 schema。
Helper ports、canonical named outputs、selected visible exports 保持分离。
Named/imported/reexported consumers 使用 immediate exports，不绕过 JOIN/filter。

## Obligations, verification and observation

保留 selected dependency/evidence closure 中全部适用 ProjectIRSingleMatchRetention，
原 request/assessment、DIRECT_BINARY/PATH_HOP/WHOLE_PATH、实际 BAG unit、ordered
boundaries、原/当前 input pairs、proof images/premises 和原 Diagnostic 对象。
PROVED 是有 scope 的静态证据；LEGAL_UNPROVED 保留 PIE-S2337 WARNING 与未履行的
downstream enforcement requirement；INVALID 阻止 positive plan。Whole-path 不拆成
互相替代的 hop 要求，重复请求不按文本合并。全项目 diagnostics 保留，但无关合法
warning 不生成 selected-result demand。
同一 request 对象的重复输入保留多个 retention slots，并按上游保留共享的 assessment/
Diagnostic；不同 request 对象不会因为字段或消息等值而合并。

Matching/input/output/condition/context/obligation/proof 都有完整 role-tagged origins
和 mandatory demands，区分 value、membership、type/proof、generated structure。
Demand 不表示 target support 或 runtime fulfillment。Verifier 独立检查所给 witness
与上游对象、完整库存、顺序、scope、nulling、端点和所有必需站点，不调用 allocators、
semantic/proof builders。Inspection 暴露实际对象及 exact-ref queries，重验 stale
positives。使用迭代遍历与 invocation-local indexes，保留 sharing，无持久 cache。

## Acceptance and limits

覆盖两种 source family、TABLE/QUERY、ON true/false、relationship/refinement/path、
self/chained/outer/SEMI/ANTI、隐藏 membership、joined LET/WHERE/scalar、named/imported
consumers、PROVED/LEGAL_UNPROVED/INVALID 与 field-level graft/omission/ordering tests。
保留 strict int-versus-Bool ordinals 和禁止 construction/inference/proof 的 monkeypatch
控制。两项 Phase63 readers 增加精确 LET retention 检查，Slice2–4 JOIN negatives 迁移
为 positives；原 durable rejection 用仍不支持的有效 GROUP/window/SET/ORDER/LIMIT
fixtures 保留。Depth12 binding sharing 与 SET whole-plan rejection 继续有效。

缺失 call/type evidence、不可用输入、未支持组合及 reachable GROUP/GLOBAL/satisfying、
window/QUALIFY、DISTINCT/ORDER/LIMIT、SET 仍 typed unavailable。Right LIMIT/GLOBAL 的
既有 single-match proof 不让尚未规划的 producer body 变成 positive。没有 SQL
emission/execution、target strategy、federation、literal binding、portable format、
新 differential family、优化或物理 evaluation-once/materialization 保证。

## Closure and publication

实际闭包为 A3/M14/D0，十七个获准路径；production192/test450，由既有 sole inventory
reader 检查，生命周期由既有 active-phase reader 检查。独立预算为六个因果修正组、
四次 authoritative starts、一个 initial ordinary commit、至多一个剩余预算内 CI child。
记录位于仓库外 `~/.local/state/pietto/evidence/phase65-slice5/`；author self-review 与
Ponytail review 不称第三方审核。

最终 gates 包括 Python3.12/3.13 focused/direct compatibility、Ruff/format、双 Pyright、
Python3.13 authoritative、generated/golden/package，然后 ordinary commit/ff push 和
自然 exact-head push/main/attempt1 的两版 Python 四项步骤。成功时 Phase65 ACTIVE、
Slices1–5 PUBLISHED、Slice6 NEXT、Slices7–16 NOT IMPLEMENTED；不启动 Slice6。
