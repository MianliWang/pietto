# Phase65 Slice7 Windows, Named Windows and QUALIFY Staging v1

本交付沿用 D65.01–D65.12 和 N16。输入仍是 EXPLICIT_MODULES、whole-project
completed.ok、同一快照的 VERIFIED Query Block IR，以及明确选择的 TABLE/QUERY
owner。成功 ordinary commit、fast-forward push 和自然 exact-head CI 后，Slices1–7
发布，Slice8 NEXT；Phase65 保持 ACTIVE。

## 原始证据与获准的构造步骤

发布基线为 commit `720a296a5ac7aa3181afb82ccd42453186ebba1c`、tree
`b0977930d42ddb3214021cb0a1174a1b3ef0900c`、parent
`ec0a9f3a535dc4e4284e1d064c676a217750dc43`，自然 CI `34669857637`
为 push/main/attempt1/success。中间 tree
`6af606559f94579561357b4b32490168c2b9a8fd` 仅是采纳的未封存输入。
两次前置 STOP、原始探针、失败日志及累计计数保存在仓库外，未被覆盖。

| 路径 | 正常构造和保留产品 | 规划使用的正向身份 |
| --- | --- | --- |
| 普通 selected window | 原 `_window_input_dependency` 的一次 resolve 返回值，连同原 scope、expression、definition/item、analysis、upstream symbol | 每次 WindowDependencyOccurrence 及其 computation context |
| no-JOIN hidden window | `_hidden_no_join_window` 在原 analyze_window_computation 的 prepare_inputs 接口增加一次有界准备 | 每个角色/位置的原 binding、实际 Project target，以及该 hidden expression/context |
| no-JOIN outer QUALIFY | 原 candidate/status/target 继续保留；正常构造同时提供 scope.bindings 到 Project targets 的对应 | 原 resolution 和同一 ProjectNoJoinWindowInput |
| joined selected/hidden/QUALIFY | 直接消费既有 computation sites、input namespaces、dependency occurrences 和 post-window resolutions | 原 joined field、LET occurrence、group key、aggregate result 或 selected result |
| rebound named consumer | 消费既有 IR row compatibility 的 required_fields 与当前 producer ports 的有序对应 | 原语义字段 key 连到 immediate active exports，字段名不充当匹配器 |

selected 路径没有新增 resolve。原三个探针在两版解释器中均从 0/5 保留提升为
5/5；每一个原 scope/binding/expression 都通过正常 completion/IR 可达。
RELATION_INPUT 只保留输入/计算上下文，不把函数调用伪装成字段。

hidden 路径是用户明确批准的 **NEW construction-time binding preparation**。
它对有效表达式中的直接 value/default、partition/order 引用逐次调用既有
WindowInputScope.resolve，保留返回对象；不捕获旧 kernel 的局部字段，不声称零新增
调用。literal、offset、bucket/position、frame bounds 和非法复合输入不伪造字段边。
早于 callback 的 function/modifier/arity/admission 拒绝仍可留下未准备状态；
未解析尝试不变成成功空 ledger，也不新增语言 ERROR。

原 analyzer 调用、参数、类型推断和诊断优先级保持。callback 不预填、替换或归一化
value_types。binding.value_type 与专用分析结果的 ValueType 保持各自原身份；
规划核对适用的类型/NULL 一致性，不借类型相等选取 target。模块构造把已经绑定的
target 翻译成原 Project field、LET binding 或 grouped selected item；下游只读此对应。

新引用通过 InitVar 正常构造并存于 init=False 字段，普通 dataclasses.replace
不继承成功绑定证据。历史 summary-only carrier 仍有结构用途，不能据此规划。
WindowDependencyOccurrence 的旧 equality/hash/repr、角色顺序、重复项和 first-role/
target dedup 保持；ProjectModuleWindowOutputFact 与 WindowResultProjectFact 布局不变。
Phase53 的直接 reader 只取消新增 carrier 的完整字段冻结，继续检查必要字段/相对顺序、
frozen/slots/keyword、严格 ordinal、privacy 和失败行为。Phase54/60 reader 未修改。

## 计算、输入、策略和作用域

新增私有 ProjectSQLWindow、WindowUse、WindowArgument、WindowPolicy 和
WindowProjection，沿用现有 SELECT-block、stage-port、scalar、JOIN、aggregate、
symbol 和 requirement 机制。每个计算都有原 authored/effective expression、function
identity、输入阶段/上下文、逐次输入用途、参数、结果类型和独立私有结果端口。
原 IR operator、selected result policy、effect 以及专用 partition/order bindings
一并保留；hidden computation 使用其原 WINDOW row effect，没有伪造 IR scalar。

支持既有准入的 row_number/rank/dense_rank、percent_rank/cume_dist/ntile、lag/lead、
first_value/last_value/nth_value。专用参数记录区分 value/default/offset/bucket/position，
保留省略、显式值、NULL 默认值及既有签名/空值公式。它不开放任意 scalar call。

阶段顺序为 inputs/JOIN → LET → WHERE → aggregation/satisfying（如有）→ WINDOW
→ QUALIFY → final projection。所有 selected 和 hidden sibling 只读取预窗口输入；
循环顺序不让前一个窗口结果变成后一个窗口的输入。建立的 LET/group/aggregate 值
通过端口消费，既有 effective-expression 来源仍保留，不展开成新计算。
无字段参数的 ranking 仍消费输入 BAG 和此前 JOIN/filter membership。

named namespace、declaration dependencies、composed use 和 component origins 都来自
既有语义产品。共享模板 AST 不合并 use-local binding 或 computation；未使用声明
不增加计算或 realization demand，其原诊断仍属于 whole-project completion。
规划、验证和 inspection 不解析/组合 named windows，不展开模板 DAG。

ROWS/RANGE/GROUPS、bounds、EXCLUDE、applicability/emptiness、direction、NULL posture、
NULL treatment 和 nth direction 保持原 explicit/default/inherited 状态。
NOT_APPLICABLE 不被当成适用的默认 frame。UNKNOWN effects 保持原对象，未计算 frames/
peers，也未推断 tie-breaker、唯一性、全局排序、materialization 或 physical evaluation once。

QUALIFY 读取原 post-window candidate/status/target 和 predicate type map，并保留 SQL
TRUE-only membership。selected-or-predicate-window、inline-only hidden、歧义及非法位置
规则不变。隐藏值没有 SelectItem、selected ordinal 或 canonical field；最终 exports
严格等于原 authored visible tuple。标量、group/aggregate 和 window 输出分别消费其
实际阶段值。GROUPED 的输入可见性以既有 scope 为准，私有未选键不会新增名字。

## 实源支持与保留边界

| 组合 | 当前行为 |
| --- | --- |
| ordinary/joined selected windows | 上述 11 个族的原签名/类型；INLINE、named/copy/inherited/local components |
| hidden-only / selected+hidden QUALIFY | 同一预窗口阶段，独立 hidden result，原外层 scope 与 TRUE-only filtering |
| LET/WHERE | field-backed LET 和既有行表达式端口；false WHERE 不触发 window DCE |
| GROUPED/satisfying | 原准入 selected key/aggregate 输入；保持完整 determinant、隐藏键及既有 key/FD 限制 |
| named GLOBAL → row window | 是原有合法新行上下文；不解除同体 GLOBAL+window 限制 |
| imported/reexported/repeated producer | 共享定义保留所有 uses；通过 immediate active exports，rebound consumer 使用原 IR correspondence |
| obligations/risks | 全部适用 selected-closure 记录、诊断和 single-match proof images 保留；QUALIFY 不履行或证明义务 |
| C04 | constant visible output 加 hidden row_number/QUALIFY；hidden 值不泄露 |
| C13/C14 | 真实 windowed producer 与重复阶段值使用；只证明逻辑身份，不证明物理执行次数 |
| 仍 unavailable / 原拒绝 | DISTINCT/ORDER/LIMIT、SET body、一般 scalar call、原语义不准入的 window/QUALIFY 组合 |

whole-project ERROR 阻止正向计划；不在所选闭包中的合法但未支持 body 不阻止规划。
Clause/IR 限制是 typed unavailable，缺少新增 transport 也不是语言错误或部分成功。

Slice2 的 window/QUALIFY 临时负例提升为正例。完整 Slice2–6 链保持已有 ORDER/LIMIT/
SET ancestor、graft、depth12 bindings、七类 JOIN 和 single-match 控制。Slice6 的
window/QUALIFY parent 后 rebound grouping 控制现在继续到 plan/verifier/inspection，
原 hidden/partial determinant 与可见 key/FD 断言保留。没有删除旧性质或放宽语义前提。

## 独立验证、inspection 和验证纪律

原始 input membership、argument/default、partition/order、named/frame/modifier、result、
scope crossing 和 QUALIFY predicate 都有 mandatory origins/demands。它们是要求，
不是 target support、lowerer implementation 或 runtime fulfillment 证书。

独立 verifier 对 supplied witness 核对完整清单、严格 int-versus-Bool 序号、所有用途的
角色/位置/重复项、原 binding/Project target、类型、named/policy/effect 身份、私有结果和
canonical exports。它核对 QUALIFY 原状态和同一个 aggregate context；仅有旧 IR VERIFIED
标志不能认证新 ledger。删除整个计算、用途、参数、policy、projection 或需求清单不能
空泛成功。验证不调用 plan allocators、semantic/named resolvers、frame evaluators、
FD/grain solvers 或 proof builders，也不调用会重算语义的 upstream __post_init__。

运行时 view 重新验证，提供窗口、输入用途、参数、策略、阶段上下文、QUALIFY 和要求的
exact-ref 查询，拒绝 stale/grafted positives。结构运输使用 invocation-local indexes，
保留共享定义和所有 uses；没有 persistent observation cache、evaluator 或 pass framework。

验证覆盖正常源到 completion、VERIFIED IR、plan、独立验证、inspection 的完整链，
以及原始 selected retention、NEW hidden preparation 的身份/次数/诊断和类型保持。
还覆盖缺失/partial/foreign ledger、错误 target/role/frame/type/context、重复/丢失用途、
错误 exports/origins/demands、派生状态和 no-construction monkeypatch 控制。

最大授权 A3/M22/D0、25 个指定路径，production194/test452。计数与运行失败保存在仓库外。
作者 self-review/Ponytail review 不冒充第三方审查。最终冻结输入后使用正常锁定的
Python3.12/3.13 环境；跨版本 PYTHONPATH 不作为验收。要求 focused/affected compatibility、
Ruff/format、production/test Pyright、Python3.13 authoritative validator、generated、golden
和 package-smoke 全通过，然后一次普通 commit/push，观察自然 push/main/attempt1 CI
两个 Python jobs 的四个 gates。未授权下一 Slice、SQL emission/execution、target strategy、
新语法/共享 kernel 规则、public/portable schema、依赖、workflow、version 或 golden 修改。
