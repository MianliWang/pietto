# Phase65 Slice13 Explicit Target/Profile Requirement Assessment v1

沿用 D65.05–.10、N16 和 Slice11/12 的原对象身份边界。基线 commit
`a0e235f9c858187a7b5f25e47c1413e61a8899fe`，tree
`eb0bcb33e2291a7114ab9c464959fdc8488ee551`，parent
`a7a48a1e3c7b288e051213fdb163dd7226d0cd60`；自然 CI `34744544990`
为 push/main/attempt1/success。写前已核对实时 refs、clean worktree/index、Git
操作和进程。累计账本位于仓库外 `~/.local/state/pietto/evidence/phase65-slice13/`。

本交付在未封存候选 `38b306eb37bc633d61a10f31f2eb0f231f68918f` 处因既有
consumer registration 路径不足停止。续行授权保留同一候选与累计预算，将精确范围
扩展为 A4/M10/D0、十四条路径。原 privacy 3 failed/133 passed 收据保留。
第 3 个修正组只在三份 Phase52 隐私测试的四个适用 exception sets 登记
`project_sql_plan_target_assessment.py` 和 `project_sql_plan_target_mapping.py`
两个完整私有路径。没有 directory/prefix/glob 例外，没有更改 AST/alias/relative-import/
lookup-token 检测、公开导出检查、动态 import 和原控制测试，也没有将 consumer
加入 MODULE_RELS 或 capability producer inventory。production201/test458 不变。

## 实现前的真实命题矩阵

使用 Slice11 的十二个真实 source/completed/VERIFIED IR/plan fixtures：minimal、
row、literal_tags、join、path、partial_path、aggregate、hidden_group、hidden_window、
window_arguments、hidden_order、set_membership。前置 probe 覆盖全部现有 demand
variant/subkind，原始结果保存在 `prerequisite-matrix.json`。以下是本交付的闭合映射，
没有通过搜索 positive facts 选择 key。所有 key 均保持 release-free。

| 原 demand / witness | 精确子命题与 key schema | 原 provider owner | 必须保留的剩余命题 |
| --- | --- | --- | --- |
| Source / 原 connector AST | postgres.table → postgresql；mysql.table → mysql 的精确 family bridge，无 capability key | 原已验证 source descriptor | locator、同一 connection、catalog availability、source realization |
| Export；StageValue INPUT/EXPORT / 原 ProjectResolvedType、ProjectRowField 或 ValueType | LOGICAL_TYPE，builtin name / catalog_membership / builtin_registry；alias、enum、shape 仅 declaration_kind / semantic_model | capability_inventory | 原 nominal identity、alias/provenance、Decimal 参数、NULL、数据库表示和跨 stage 值保持 |
| Expression MATCH/LET/WHERE/SELECT/AGGREGATE_ARGUMENT/SATISFYING/QUALIFY / 原 AST、operand_types、result ValueType | LITERAL result；UNARY_OPERATOR、BINARY_OPERATOR、COMPARISON、NULL_TEST；已准入 aggregate argument 的 Text lower/trim/len/matches 为 SCALAR_FUNCTION。context=expression，operands 严格使用原 provider 的有序结果/NULL posture schema | capability_inventory / capability_signatures | 原具体 operand 类型、nominal/Decimal identity、比较/NULL/collation、evaluation effect、数据库 release 和 lowering |
| Aggregate AGGREGATE_OPERATION / 原 ProjectSQLAggregate、source call、argument refs/result type | AGGREGATE signature / aggregate_signature；零参数 count 或直接字段 count/count_distinct/sum/avg/min/max；operands=(arity, argument shape, argument type, result type, nullability, GROUP, aggregate_result) | capability_aggregates | composite/LET argument 的 schema 对应未建模；group/empty-input、modifier、risk、完整 lowering |
| Window INPUT_BAG_AND_RESULT / 原 function identity、policy、input/result | WINDOW_FUNCTION signature / window_signature；row_number/rank/dense_rank、percent_rank/cume_dist、ntile、lag/lead、first_value/last_value/nth_value 的原 arity/argument/result/NULL/stage/role/order schema | capability_windows | 原 argument/default/offset、NULL、frame、collation、named scope、QUALIFY、effect、完整新计划 lowering；不查询 legacy WindowCallIR lowering |
| Window ARGUMENT / 原 value_type（存在时） | 与 Export 相同的 compiler type 子命题；specialized input 无 ValueType 则显式未映射 | capability_inventory | 原特殊 argument role、值域和输入政策 |
| Literal Bool/Int/Text/Float / 原 fixed value/use/slot 和 ancestor contexts | compiler LITERAL result / expression 与 LOGICAL_TYPE catalog_membership | capability_inventory | 原五项 DATA_TYPE、NULLABILITY、RANGE_PRECISION、OPERATOR_OPERAND、COLLATION_OVERLOAD 各自保持未解决；PARAMETER 声明事实不能证明 SQL bind/driver 类型 |

每个其余 variant/subkind 都保留独立的原 witness 和精确未映射原因：

- Filter WHERE/SATISFYING/QUALIFY：SQL TRUE-only row retention。
- Scope LET/WHERE/PROJECTION/AGGREGATE/SATISFYING/WINDOW/QUALIFY：原 predecessor、ordered inputs/exports 和作用域。
- JOIN JOIN_ROWS/MATCH_INPUT/MATCH_FIELD/OUTPUT_FIELD/RELATIONSHIP_EQUALITY/POST_MATCH_SCOPE/SINGLE_MATCH/PROOF_CONTEXT：原 rows/null extension、match inputs/fields、输出表示、relationship equality、scope、obligation/proof。
- Aggregate GROUPING_AND_EMPTY_INPUT/GROUP_COMPARISON/RESULT_PROJECTION/RETAINED_RISK：原 bag/group/NULL comparison、projection 和风险。
- Window INPUT_USE/POLICY/PROJECTION：原 input-use、frame/modifier/named policy 和 projection。
- Result BOUNDARY/PORT/DISTINCT/COMPARISON/ORDER/ORDER_ITEM/EXPRESSION/USE/HIDDEN/LIMIT/EXPORT：原 boundary、port、row equivalence、排序、隐藏 STRICT-FD 实现和原静态 limit/terminal。
- SET OPERATION/PROPERTIES/COMPARISON/OPERAND/INPUT/COLUMN：原 quantifier/bag/row-domain、等价、membership 和 positional type/value inputs。

精确 compiler 子命题支持不会覆盖上述剩余需求。未知 future variant/subkind 拒绝，
不能自动归入完整 inventory。alias/nominal operands 不冒充 builtin signature；原
Decimal 参数和 provenance 留在原 witness，目录成员身份不能证明具体值的精度表示。
若上游已把 alias 解析为 builtin（真实 Money = Decimal(12, 2) fixture 即如此），
读取其原 resolved type 查询目录，同时保留原 alias declaration、参数和来源；assessment
不重新展开 alias，也不反向伪造一个 TYPE_ALIAS result。

## 输入与证据

使用 detached private request，显式 DATABASE CapabilityProfileTarget、原 base/ordered
overlays 和既有 compose_capability_profiles 的一次结果。它不声称 PACKAGE_ROOT
配置 membership，不更改 EXPLICIT_MODULES。精确 target/profile wrappers 与独立的
profile/database/extension releases 全部保留；family/database release 不同、blocked
composition、缺 profile 都是显式输入未解决。omitted target 为 NOT_ASSESSED，零 provider。

当前没有能从真实 plan demand 推导 exact extension selector 的规则。若显式提供原
ExtensionSignatureProviderContext，逐个保留 selector/selection 为未映射输入，检查
target release agreement；不调用 extension provider，不推断选择、安装或新增准入。

Canonical dispatch 仅在构造时按共享 query 调用。核验从原静态 inventories 检查完整
fact membership/order 和 owner 的纯 schema completeness predicates，不再次 acquisition。
Profile composition 的原输入/顺序/结果绑定保留，核验不重新 compose。Profile facts
始终 partial；原 profile lookup 和 canonical provider lookup 分开，按既有 lookup
代数保留 Found/Absent/Unknown/Conflict。Found 的 support 与 roadmap 分开。
Profile 是 explicit declaration，不能升级为数据库 release conformance。
成功 composition 的全部原 occurrences 也在 target mismatch 时保留并作 raw lookup；
`profile_applicable` 单独报告声明适用性。错误 release 不把原 Found/Conflict 改写成
Unknown，也不能产生 satisfied aspect。缺 profile 或 blocked composition 没有 effective
occurrences，但原输入和 blockers 保持。核验独立检查该布尔值及原事实，不调用构造侧
适用性函数。结果类别保留原 lookup 的 negative/conflict 与 inapplicable/input-unresolved
同时出现；它们不是当前数据库 release 的 conformance verdict。

## 完整产品、核验与查询

独立 assessment 复用 exact verified Slice11 report。每个原 entry 恰有一个有序 demand
assessment，所有 mandatory aspects 保留；原 plan/report/map 不变。查询共享限定同一
assessment request 的 key、proposition kind、provider、target/profile/catalog 与 applicability
context；occurrence-to-query edges 完整，跨 request 不复用。共享 producer 不沿路径复制。

独立 verifier 核对原请求与 report、闭合 aspect 覆盖、key/witness/context、原 facts、
lookup reductions、全部结果类别、immutable indexes 和原义务。它不调用 assessment
builder、mapping classifier、status aggregator、composer 或 providers，也不调用语义/
证明重建、renderer、网络或文件发现。入口为 build → verify → inspection，以及既有
private plan inspection 的可选 target assessment 入口。

Summary 同时返回所有 satisfied subpropositions、negative、Absent/Unknown、Conflict、
unmapped/inapplicable 和 pending realization members；不选择单一失败覆盖其余。原
PROVED、LEGAL_UNPROVED enforcement/WARNING、aggregate risk、hidden ORDER 保持原
report summary 与 links。LIMIT0、DISTINCT、EXCEPT 右侧 membership 不履行这些义务。
当前真实证据只能产生 positive subset；每个完整 demand 仍有原实现缺口，不能称
whole-plan supported，更没有 executable/installed/ready certificate。

Exact demand/aspect/query 和 target/summary 查询保持原 demand/origin refs，可继续用于
report/source-map。foreign/wrong-role refs、Bool ordinal、stale wrappers 拒绝；owned no-hit
可返回空。边界 fresh validate 后复用 invocation-local immutable indexes。

## 验证与发布

真实 pipeline 覆盖正子命题、两种 literal policies、source mismatch/mixed families、
profile partial/conflict/negative、全分母、保留义务与 depth12。Synthetic declarations
只测试 lookup/aggregation mechanics，不代表 backend conformance。Mutation tests 删除
demand/aspect/query/unresolved/proof links，伪造状态、facts、completeness、counts、roots；
monkeypatch controls 确认 independent verification 不依赖 builder/provider 或重建。

作者 self-review/Ponytail review；不称第三方审核。限额 6 correction groups、4 本地
authoritative starts、1 initial ordinary commit，余额内至多 1 natural-CI repair child。
全部内容在 final-input freeze 前完成，要求 locked Python3.12/3.13 focused/compatibility、
Ruff/format、production/test Pyright、Python3.13 authoritative/generated/golden/package。
精确 tested tree 封存后普通 commit/fast-forward push，natural exact-head push/main/attempt1
两个 Python jobs 四项步骤成功建立 publication authority。

成功时 Phase64 COMPLETED，Phase65 ACTIVE，Slices1–13 PUBLISHED，Slice14 NEXT /
NOT IMPLEMENTED，Slices15–16 NOT IMPLEMENTED。N16 不变，没有开始 portable integration、
SQL lowering、安装发现或运行时履行。
