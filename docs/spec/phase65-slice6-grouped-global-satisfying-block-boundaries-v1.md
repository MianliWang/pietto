# Phase 65 Slice 6 GROUPED/GLOBAL/satisfying Block Boundaries v1

本交付沿用 D65.01–D65.12、N16 和 Phase65 ACTIVE 状态。它消费明确选择的
TABLE/QUERY、EXPLICIT_MODULES、whole-project completed.ok 和同一快照的
VERIFIED Query Block IR。自然 exact-head CI 成功后 Slices1–6 发布，Slice7
NEXT；本合同不宣称 Phase65 完成、目标支持、风险履行或数据库执行。

## 基线与前置修复

基线 commit `ec0a9f3a535dc4e4284e1d064c676a217750dc43`，tree
`4ef49bbce9019699c2c3875249b51e1c52b08182`，parent
`d87070d9ab0a261dd0f55f7ef1aceeee966b03dc`；自然 CI `34651949568`
为 push/main/attempt1/success。

初次实源检查发现：LEFT JOIN 后 `group by: lhs.id`、仅选择
`total = count()`，正常语义完成成功，但 IR 抛出
`GROUPED output must expose every exact group key.`。两个解释器、两种
连接器和 TABLE/QUERY 共八个隐藏键案例复现；八个选出键的对照通过。
当时的 expected-error harness 成功不是功能通过；源码、堆栈和账本保存在
仓库外的 Slice6 evidence 目录。续授权将两个 IR 文件纳入同一 Slice6，
没有重置预算，也没有单独发布修复。

完整分组 determinant 属于原始 aggregate context/input，允许其成员不出现在
可见输出。IR 只在每个 determinant 分量都有精确输出映射时保留分组派生的
STRICT key 和 FD；隐藏、部分投影、同一键的重复投影不能代替缺少的另一键。
重命名和重排保留原有完整覆盖行为。无可见 key 时仍是 GROUPED、FACTORIZED
grain 和原 grouped origin/factor，保留输入依赖，不变成 GLOBAL 或一行承诺。

同源 JOIN 的两个 use 共享底层字段，分组输入通过原 joined-field occurrence
及既有 input correspondence 区分。独立 IR verifier 核对原始 determinant、
可见映射、factor 和完整 grain 依赖；它不调用 builder 的覆盖结果或 FD/grain
solver。普通 reused、rebound、no-JOIN replay 和 joined 路径均有实源控制。
窗口父体引出的 rebound 用于 IR 回归，其 SQL-plan 闭包仍保留窗口限制。

## 原始证据保留与 reader 迁移

| 路径 | 正常构造点与保留产品 | 首个消费者 |
| --- | --- | --- |
| 普通 aggregate | `aggregate_grouped_schema` 保存原 call/item、input schema、LET scope、upstream symbol、argument/effective-expression、原 ValueType map 和 result type | aggregate argument/result ports |
| 普通 GROUP | group helper 保存原 selected-item 到 exact group-key 的映射；candidate attempt/finalization 保留全部键及映射 | IR determinant 覆盖与私有分组端口 |
| 普通 satisfying | clause helper 保留 `SatisfyingResultPredicateInfo` 和完整 `occurrence_facts` | 后聚合 predicate 与每次结果引用 |
| module/replay references | module/completed 构造在实际 input/LET 环境调用既有引用 collector，保留每个 group key 的引用 | pre-aggregate scope membership |
| joined aggregate | 直接消费已有 group keys、argument analyses、stage outputs、satisfying resolutions、protection/grain/pair linkages | 相同的聚合阶段与需求清单 |

`dependency_facts` 继续是 target-deduplicated summary；新 occurrence ledger
保留源码顺序和重复引用。失败 finalization/readiness 不发布部分新证据。
映射和序列不可变，ValueType 与诊断对象保持原身份。规划不重新推断类型、
展开 LET、恢复名字或建立第二条语义流水线。

新证据集中在 attempts/finalization，原 `ProjectGroupKeyFact`、
`ProjectAggregateSelectedResult`、`ProjectGroupedSelectedResult` 及三个 schema
carrier 的布局保持。两个已授权 Phase51 reader 从完整字段快照迁移为必要
结构、真实保留、immutable maps、失败原子性、重复项、身份与 privacy 检查。
其他历史 schema reader 不改动。新 payload 由正常构造的原始产品通过
InitVar 提供，并保存在 init=False 字段中；dataclasses.replace 派生 UNKNOWN/
BLOCKED 状态时不继承这些构造期证据。原成功对象不变，派生对象不重新推断或
默认获得成功映射，Phase54 的原有派生状态消费者保持兼容。

## 实源支持与限制矩阵

| 组合 | 本交付行为 |
| --- | --- |
| 普通 GROUPED/GLOBAL | 原有 count()、count(field)、count_distinct、sum、avg、min、max；TABLE/QUERY 与 PostgreSQL/MySQL 描述符 |
| 类型与参数 | 原规则允许的 Bool/Int/Float/Decimal/Text/Date/Timestamp/UUID comparison/count 类型、numeric/temporal extrema、numeric expressions；不把这些类型统一授权给所有函数 |
| 参数中的既有变换 | count 的 len/lower/trim 等已准入表达式及 count_distinct 的 lower/trim 链，只在原 aggregate argument authority 下形成专用 call 节点 |
| LET/WHERE | 已支持的有序 row LET、直接字段 LET 分组别名、LET-fed 参数和 pre-aggregate WHERE；保持 established LET port，不展开成新 AST |
| joined GROUPED | 现有语义准入的六类聚合、未选键、nullable outer-JOIN 参数及全部风险关联 |
| joined GLOBAL | count() 及具有既有 grain/relationship 前提的准入字段聚合；不将未满足风险要求的组合改判成功 |
| satisfying | 普通与 joined 的 GROUPED 输出别名、重复引用、既有唯一 aggregate-LET 引用；TRUE-only retention 和原 UNKNOWN nullability |
| named/imported | 隐藏键 grouped/GLOBAL 的 immediate exports 进入 row/WHERE、JOIN、准入 aggregate 消费者；保留 re-export trail 与 repeated uses |
| single-match | 既有 RIGHT_GLOBAL 正例随可规划 GLOBAL 生产者保留；不转移到 GROUPED、另一个输入或后续 filter；LIMIT 生产者仍不可规划 |
| 仍拒绝或 unavailable | GLOBAL+satisfying、计算分组键、pure grouping、嵌套/组合 aggregate、混合 GLOBAL 行投影、歧义 aggregate 引用及其他上游拒绝形状 |

重复声明的相同聚合各有结果端口和 canonical export，不做 CSE。joined
satisfying 的 aggregate-call 引用要求已有规则认可的唯一目标；重复声明导致
歧义时保留原诊断。普通 scalar call 和含此类调用的 row-stage body 仍受既有
callable-authority 边界约束；aggregate 参数节点不开放通用函数规划。

## 阶段、作用域和要求

沿现有 SELECT-block/port machinery，顺序为必要的 LET、WHERE、AGGREGATE、
SATISFYING、PROJECTION。分组键和 aggregate result 是新的私有阶段值；最终
映射消费这些端口，并精确对应原 canonical exports。未选键、helper 不进入
selected visible outputs。satisfying 不能通过同名捕获 raw input、旧 JOIN alias
或 row LET；其 aggregate-call 引用是已有结果的一次 use，不是新 computation。

count() 虽无 scalar arguments，仍消费整个输入 BAG 及 JOIN/WHERE membership。
GLOBAL aggregate stage 在空输入上保留一行语义，GROUPED 空输入无 group；
false WHERE 不被折叠成空 GLOBAL 输出。后续消费者仍可过滤 GLOBAL 结果。
count(nullable right field) 与 count() 分开保留，count_distinct 不替换成整行
DISTINCT，不增加 NULL/equality 规则。

每个 key、aggregate、argument expression/operand、result port、projection、
satisfying use、block 和 risk 都有强制 origins/demands。分组比较、原函数操作、
类型/NULL、空输入、表示与保留风险是要求，非 capability 或 execution 证书。
group protection、STRICT-FD、grain/pair/chasm/fanout 记录保持原单位和对象；
没有 solver、代表行选择、common-grain winner、DISTINCT 修复或重聚合重写。
规划不以 pending requirement 为由新增语义 ERROR，也不将其标为 fulfilled；
当现有上游因风险而 non-concrete 时仍保留该边界。

独立 plan verifier 消费给定 witness 与原 roots，核对完整清单、严格 int 序号、
scope membership、argument/result 分离、canonical map 和风险/obligation 关联。
删除整个清单不能空泛通过。原 satisfying target 必须是同一输出对象；同形
对象拼接不能代替 membership。禁止调用 plan allocators、semantic/proof/FD/grain
构造器或具有重算行为的 upstream `__post_init__`。

运行时 inspection 重验输入，暴露 aggregation、group keys、ordered aggregates、
argument/result/projection links、satisfying uses、stage contexts 和要求；查询只接受
本 plan 的 exact refs。IR inspection 继续保留可见形状，观察内容不代替运行时身份。

## 验证、范围与发布

实源回归覆盖普通/joined/replay、rebound IR、隐藏/部分/完整键、同源 JOIN、
rename/reorder/repeated projections、NULL、类型、LET、WHERE、satisfying、命名与
导入组合；负例覆盖字段/上下文/清单/来源/需求/原始证据拼接及禁止重建控制。
Slice2 的 GROUP/GLOBAL 与 Slice5 的 RIGHT_GLOBAL 临时负例提升为正例；
Slice3/4、depth12 bindings、七种 JOIN、SET whole-plan 和窗口/ORDER/LIMIT 控制保留。

最大授权 A3/M21/D0、24 个指定路径；本候选实际 A3/M18/D0、21 路径。
未改 `project_sql_plan_joins.py` 与 Slice3/4 测试，因为既有实现和控制足够。
唯一 inventory reader 更新为 production193/test451。唯一 lifecycle reader 保持。

累计上限为 6 个因果修复组、4 次本地 authoritative starts、1 个初始普通 commit，
以及余额内至多 1 个自然 CI repair child。源码/运行失败、计数、最终 tree 和门禁
收据保留在仓库外；不把独立 verifier 当作第三方审查。

最终输入冻结后要求两版 Python focused/affected compatibility、Ruff/format、
production/test Pyright、Python3.13 authoritative validator、generated、golden、
package-smoke 全部通过。一次普通 commit/fast-forward push 后观察自然
push/main/attempt1 CI 及两个 Python 作业的四个门禁步骤。不 amend/rebase/force、
rerun/dispatch、tag/release 或另发状态提交。没有新 grammar、公共 API/CLI/JSON、
portable format、依赖、workflow、golden、版本、SQL emission 或 execution。
