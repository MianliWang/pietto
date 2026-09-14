# Phase65 Slice15 Whole Selected-Plan Real-Source Differential Conformance v1

本交付继续同一个 Slice15，沿用 D65.01–D65.12、P01–P09 与 N16。发布基线为
`b6278c94b74f60fb32b4314e992c22974d4519a0`，tree
`20460df34ed65dc07dfb5a536f7fcf7b511ea17c`，parent
`a4db6382dd9d01867529605b14c902aef135bfd2`；基线自然 CI `34793858855`
为 push/main/attempt1/success。既有失败发布及普通 CI child 的历史保持。

续行采纳原未封存红测试和 sole inventory reader 的 461 文件更新。账本位于
`~/.local/state/pietto/evidence/phase65-slice15/`，原 STOP、类型检查失败、红测试、
原观察和累计消耗不覆盖、不重置。本文定义候选交付与验收要求；实际通过、封存、
commit/push 和 CI 结论以仓库外收据及 live Git/CI 为准。

## 有界生产修复 F65S15-01

真实 `value = id + 1`、BIND_SAFE_LITERALS 原产品全部有效。删除 literal demand
的全部 contexts 或仅二元祖先、保留原 ancestry 和 report links，原纯检查错误地
返回 OK/canonical bytes；runtime correspondence 正确拒绝。原两个红测试保留。

F01 的生产改动位于 `project_sql_plan_pure_boundary.py` 的既有记录关系检查：

- 沿 use → slot → site → position 核对 exact bound expression、definition、owner、
  expression context、role、evidence/type。以实际 site occurrence 的 expression 为根，
  迭代核对每个 parent/operand ordinal，最终到达同一 literal leaf。截断 ancestry
  不能改换根；零祖先仍要求 leaf 自己的 demand。
- 使用 context ref 和 exact AST ref 从本 plan 的 expression demands 独立定位每个
  ancestor/leaf。contexts 必须完整、有序、唯一且同 context；两份供给清单互相删空
  不能认证自己。LET/stage/producer references 不展开为新的 defining literals。
- 每份 report 独立使用自己的 entry identities，重建完整 link 顺序和原位置。
  literal_ancestor_context 不与 proof-root/proof-child 混用；assessment 的第二份
  report 不能借用另一份 report 的 entries。非 literal proof links 保持原义。

F01 不改变 schema、encoder、runtime verifier 或 report producers。检查器仍
只依赖标准库和 closed schema，无语义重建、source parsing、runtime helper、provider
或 encoder 调用。索引限定单次调用，遍历成本计入实际 records、ancestry 与 links。
正确文档格式和 bytes 不变；内部矛盾文档改为 INVALID_RELATION/no canonical bytes。
Coherent symbol rewrite 仍可 pure OK、但不能对应原 runtime；没有文档来源真实性承诺。

## 有界生产修复 F65S15-02

原正常 `rows → ordered SELECT with ORDER BY id → result SELECT` 在 completed
semantics、IR、plan、report 和 source map 均有效；encoder 遇到原始
`ProjectIRProvidedRelationOrdering` 时 fail closed，尚未到达 pure checking。
保留两个 literal policies 的无 data-literal 红例，不制造 bound slots。

`project_sql_plan_portable.py` 为该 exact class 增加 closed adapter；
`project_sql_plan_portable_schema.py` 增加专用
`project_ir_provided_relation_ordering` record，依序为 typed output、evidence、items。
它分别关联原 `ProjectIRRelationRowOutput`、`ProjectModuleRelationSemanticFacts`
和有序 `OrderItem` occurrences，纳入实际 property-stage/QBRP unions 和 ref domains。
`ProjectRelationOrdering` 仍是不同记录；既有逐字段独立 correspondence machinery
核对原 runtime 对象和三个字段，不重编码或重新构造 properties。

Pure boundary 从现有记录独立关联 output/evidence owner、authored ORDER clause、
完整 item 顺序和 prepared ORDER items。普通 property stage 以完整 fragment 的
ordered row-shape/operator pairs 核对建立或保留 ordering 的原 output/evidence；
rebound route 使用实际 result boundary、operator 和 query-block result properties。
未被 consumer 使用的独立 carrier 不能代替所需关系闭包。检查不引入名字解析、
ORDER 分析或外层 presentation-order 继承。

直接控制覆盖多 item/direction/default、projection 与真实 rebound、LIMIT-only、
distinct completed carrier、原 ORDER/LIMIT/filter barriers，以及 missing/wrong-kind
fields、foreign/equal-looking evidence/output、item omission/duplication/reordering、
无关 clause 和错误 property-stage membership。内部矛盾在 pure 层拒绝；对原对象的
graft 在 runtime correspondence 层拒绝。两项修复均有 no-runtime-helper 控制。

格式仍为 `pietto.phase65-sql-plan-observation.v1`。这是已承诺 transport domain 的
缺失 record 补全；旧字段顺序、含义、numeric encoding 和资源限制保持。
不含新 carrier 的原有效文档保持原 canonical bytes；旧 checker 会拒绝未知新 kind，
没有对旧实现的 forward-compatibility 承诺。其他生产 owners 保持只读。

## 扩展前的有限覆盖矩阵

下表在扩大既有 CORPUS 前列出。P 表示 PRESERVE_LITERALS，B 表示 BIND_SAFE_LITERALS。
每个正例都经正常 authored project、completed.ok、原 VERIFIED IR、显式 owner、
plan verification、runtime report/map、portable correspondence、decode/pure checking。
每项运行两次独立构造，拒绝跨快照 graft；实际进程覆盖统一使用既有 checkout 四 seeds
及 relocated/installed seed7、每个确实可用的 Python3.12/3.13，不逐 case 新增请求。

| Case | source/project、selected owner、policy | 独立语义/身份/字段期待 | 对应变异与拒绝边界 |
| --- | --- | --- | --- |
| minimal | 原 CONTROL；main.result QUERY；P | source rows、单 canonical id、terminal export；原文档不变 | terminal omission → pure |
| bound | 原 BOUND_SOURCE；QUERY；B；原 partial assessment | LET→WHERE、Bool/Int/Float/Text、unary negative zero、Unicode/大 Int、完整 slots/uses；原文档不变 | 值/tag/slot、ancestry/contexts/links → pure；旧 envelope → runtime |
| shared_set | 原 SET_SOURCE；QUERY；P | visible DISTINCT/ORDER、repeated UNION ALL、EXCEPT right membership、Decimal parents；原文档不变 | positional input/member/parent loss → pure |
| staged | 原 STAGED_SOURCE；QUERY；P | GROUPED、selected rank、satisfying/QUALIFY/ORDER/LIMIT2 的真实顺序；原文档不变 | referenced window omission → pure |
| hidden_order | 原 FD_SOURCE；QUERY；P | hidden Float 不进入 visible quotient，STRICT-FD 原 proof 与 pending posture；原文档不变 | proof branch omission → pure |
| row_shared | Slice10 BODY 的实源；QUERY；B；两个独立 report instances | 相同 Int1 三个独立 slots；LET a 两次引用不重复定义；各 primitive tags、escaped/non-BMP 字符范围 | cross-report literal target → pure |
| table_mysql | CONTROL 的 mysql TABLE 选择；P | 显式 TABLE owner、mysql.table descriptor 和原 id export | changed selected owner/foreign scope → runtime |
| imported_reexport | 两份同字节 producer、facade reexport、main mysql source；QUERY；B | 两个 shared owners 不合并；reexport defining/use sites、重复 a uses、完整 canonical exports | lost repeated use/foreign source owner → pure 或 runtime correspondence |
| join_cross | Slice5 generic fixture；QUERY；P | cartesian pairs、无 ON、两个原输入/六个输出 ports | omitted external input → pure |
| join_right | 同 fixture RIGHT；QUERY；B；direct request | left 三个输出具有当前 nulling root；right 保持；原 LEGAL_UNPROVED/WARNING | wrong match/output nulling role → pure |
| join_semi | 同 fixture SEMI；QUERY；B；direct request | right matching fields/dependency 留存、仅 left 三个输出；不能推导 single-match | wrong right-output role → pure/correspondence |
| join_anti | 同 fixture ANTI；QUERY；P；direct request | left_not_exists、right membership 留存；原 enforcement required | lost right membership → pure/correspondence |
| join_refinement | strict unique relationship + ON refinement + post-WHERE；QUERY；B | 原 relationship equality/REFINEMENT proof；ON 和 WHERE 的角色、scope 不混合 | pre/post field graft → runtime/correspondence |
| join_accumulated | LEFT 后 FULL；QUERY；P | 后者 accumulated-left predecessor；先前右侧 nulling 再累积，原输入次序保持 | removed prior nulling root → pure/correspondence |
| proof_right_limit | 具名 right_named LIMIT1 后 JOIN；QUERY；B | RIGHT_LIMIT 依赖原 producer LIMIT1，不依赖最终输出 bound | missing premise node → pure |
| proof_right_global | Slice64 已准入的 joined GLOBAL right producer 后 SEMI；QUERY；P | 仅 outer request；RIGHT_GLOBAL、one_global_row、原 producer/use/proof roots | missing original proof scope → pure |
| path_complete | Slice5 all-unique 双 hop path；QUERY；P | 两 PATH_HOP 加 WHOLE_PATH 均 PROVED；全部 children/input pairs | missing proof child → pure |
| path_partial | 原 non-unique 起点双 hop path；QUERY；B | PROVED、LEGAL_UNPROVED、LEGAL_UNPROVED；whole 无伪造 proof | removed obligation → pure/correspondence |
| global_empty | false WHERE 后 COUNT()/COUNT(value)/SUM(value)；QUERY；P | GLOBAL one_global_row；COUNT 非 NULL、SUM nullable，两个 COUNT argument lists 不同 | altered empty-input field → pure |
| group_hidden | Slice6 joined group fixture、两个 hidden keys；QUERY；P | 两个有序 keys 留在 private results，visible 仅 total，NO_GROUPS | hidden key leaked to canonical output → pure/correspondence |
| group_partial | 同 fixture 只选 lhs key；QUERY；B | 保留两个 keys、只公开 left_id/total，不补全 active key/FD | group-key/visible image corruption → pure/correspondence |
| grouped_satisfying | Slice6 LET/WHERE/GROUP/satisfying；QUERY；B | 两 LET→WHERE→aggregate→satisfying→projection；三 uses 指同 aggregate port | wrong context/source port → runtime/correspondence |
| aggregate_risks | Slice6 joined eight-aggregate fixture；QUERY；P | COUNT/COUNT_DISTINCT/SUM/AVG/MIN/MAX、重复 SUM distinct occurrences、原全部 risks/pair evidence | removed retained risk → pure |
| window_rank_navigation | eight admitted ranking/navigation calls；QUERY；B | row_number/rank/dense_rank/percent_rank/cume_dist/ntile/lag/lead；原有序 argument/input roles | missing argument/window reference → pure |
| window_value_named | first/last/nth_value，shared/inherited names、ROWS/RANGE/GROUPS、modifiers；QUERY；P | effective components 回到 authored template；共享模板不合并 computations | effective labelled authored → pure/correspondence |
| mixed_qualify | Slice7 selected_and_hidden；QUERY；B | selected 和 hidden row_number 两次 computation，QUALIFY 真实 post-window scope | hidden result leaked to visible output → pure/correspondence |
| hidden_distinct | hidden navigation QUALIFY + visible DISTINCT/LIMIT0；QUERY；B | 仅 constant 为 comparison tuple；四个 input roles 和 bound literal 留存 | wrong quotient/window dependency → pure/correspondence |
| set_forms | Decimal alias parents、五个依赖相连的 SET bodies；QUERY；P | 与 shared_set 合计六种 forms；ordered positional labels、嵌套/left-fold、EXCEPT right membership | swapped columns/operands/Decimal parent → pure |
| set_float | Float UNION ALL；QUERY；B | typed Float input/output，requires_equivalence false，无 whole-row comparison demand | wrong equivalence claim → pure/correspondence |
| sharing_depth12 | 原 p0…p12 named DAG，p0 literal17；QUERY；B | named 13 definitions/24 uses；另列 source/result wrappers，总15/26；一个 slot/use | repeated-use omission → pure |
| limit_before_filter | named bounded ORDER/LIMIT1 后 consumer WHERE；QUERY；B | producer projection/order/limit；consumer where/projection，无 outer ordering承诺 | barrier association graft → runtime/correspondence |
| filter_before_limit | 原合法对照，把 WHERE authored 在 producer；QUERY；B | producer where/projection/order/limit；consumer projection；仅比较指定结构差异 | 与前例作 scoped metamorphic comparison |
| target_omitted | CONTROL + 显式 omitted request；QUERY；P | 全 denominator NOT_ASSESSED、无 lookups；neutral plan 不变 | false complete summary → pure |
| target_applicable | CONTROL + partial profile 的真实 Int fact；QUERY；P | 原 compiler subproposition positive，剩余 realization 未解决 | removed aspect/residual → pure |
| target_mismatch | 同 source、不同 profile release；QUERY；P | raw fact 留存、applicability false、无 whole-plan support | false applicability → pure |
| target_conflict | 同 source、显式冲突 Int declarations；QUERY；P | Conflict 两份 facts 都保留，仍有原 residuals | false support/removed conflict member → pure |
| target_residual | 同 source + supplied extension selector/undeclared selection；QUERY；P | selector 是未映射 residual，不准入新 plan call 或安装承诺 | removed catalog residual → pure |

Fixture sources 来自 Slice3/5/6/7/8/9/10 的正常行为用例，report/map/assessment expectations
来自 Slice11–14 的实际消费者。Probe 内只保留所需源码和生产 imports，不能 import
任意 `test_phase65_*`。新测试的有限 expected manifest 独立于 CORPUS registry；角色、
原对象身份、有序 links、required members 和 pending posture 分别断言，不能只看总数。

## P01–P09 与反例对应

| Exit | 实际断言域和反例 |
| --- | --- |
| P01 | 正常显式 QUERY/TABLE；whole-project ERROR、invalid connector、mandatory-evidence unavailability：C01/C02/C20/C23/C38 |
| P02 | imported/reexported/same-looking owners、seven joins、repeated SET/depth12：C08/C09/C17/C23/C24 |
| P03 | JOIN/ON/WHERE、GROUPED/GLOBAL/windows/QUALIFY、visible DISTINCT、ORDER、LIMIT barrier、six SET：C03/C04/C10/C11/C12/C13/C14/C15/C16/C19/C30/C34/C36/C39/C41 |
| P04 | row_shared/bound/sharing_depth12、两 literal policies 与 F65S15-01：C05/C06/C07/C27/C28/C29/C30/C40 |
| P05 | imported_reexport、row_shared Unicode、named windows、membership/proof sources：C22/C24/C35/C36/C37 |
| P06 | complete report、direct/hop/whole-path pending/proofs、risks、hidden ORDER 和 target cases：C18/C21/C27/C31/C32/C33 |
| P07 | 每项 fresh verification/runtime products；cross-snapshot、policy/envelope/target 的有别失效：C23/C24/C25/C26 |
| P08 | 正向 typed records、named field/link corruption、raw input 和 coherent alternative：C23/C24/C25/C31/C40/C41/C43 |
| P09 | 同一 acquisition store 的实际解释器/seeds/standalone/batch/relocation/frozen wheel 与旧 family bytes：C09/C22/C42/C43 |

负源域单列 actual failing layer/code：invalid connector、unrelated semantic ERROR、
general scalar call 的 planning unavailable、Float DISTINCT/equality-requiring SET、
direct SET→GROUP/GLOBAL PIE-S2333，以及 illegal window/QUALIFY/satisfying。它们不进入
concrete encoder 以制造 portable rejection。Malformed runtime、correspondence、pure
document 和 raw parser rejections 分开记录；返回 rejection 时没有 canonical bytes。

每个 process request 只序列化正常 case documents、实际 role/multiplicity summaries
和 compact named rejection outcomes；不复制每份坏文档、不增加 generic mutation engine。
保留 whole-document deletion、raw duplicate keys、invalid UTF-8/numeric/unknown tags 和
既定 resource boundaries。Rejection coordinates 只采用接口实际返回的值。

Metamorphic checks 只比较保持不变的 facet：无关合法 definitions 不产生 selected uses/
demands；无关 ERROR 仍阻止规划；增加 repeated use 不增加 defining slots；SET operand
重排改变 positional evidence；LIMIT/filter 顺序不同；target-only reassessment 不改 neutral
plan；PRESERVE/BIND 不改 authored AST/visible exports；hidden/selected windows 仅按规则
改变 visible tuple。不据较窄关系要求完整文档相等，不插入未授权 bridge 或代数 rewrite。

## 进程、门禁与发布边界

使用既有 family/version/seed/mode keys 和唯一 acquisition store。保留 ambient marker、
renderer/main contract、same-child import-origin receipts、退出码/stderr/LF framing、
forward/reverse batch 与失败原子性。Relocated/installed 只用已声明 support manifest；
安装观察必须来自冻结候选 wheel 的实际子进程，不借 checkout fallback。

支持 Python3.12/3.13；每次运行独立验证 available interpreters。本地两者均执行，CI
至少执行其配置版本及其他确实发现可用的版本。当前 dual-version registry 的86 requests/
16 cells 是独立 manifest 的结果；历史62/74子域保留。清单不是执行证据。

写范围上限 A2/M9/D0、十一条精确路径；production204/test461。累计上限6 correction groups、
4 authoritative starts、1 initial commit、余额内至多1 ordinary CI repair child。Group1
是原 witness 类型修正；Group2 是完整 F65S15-01 关系修复及直接后果；Group3 修正
RIGHT_GLOBAL 实源 admission/outer request；Group4 是完整 F65S15-02；Group5 修正
probe/oracle 对原 API 层次及 closed tags 的读取；Group6 使现有 reader 的独立 matrix
期待保留 supplied available-interpreter 顺序，同时检查两种顺序，历史固定模板保持。
实际消耗以持续账本为准，所有失败保留。
作者/Ponytail/内部只读复核不称第三方 review。

全部内容先完成再 final-input freeze；要求双版本 focused/完整 Slice14 reader、扩展
真实 process matrix、代表性原 plan/report/map/assessment tests、Ruff/format、production/
test Pyright，以及 Python3.13 authoritative/generated/golden/package gates。封存实际
tested tree 后一次普通 commit/fast-forward push；natural exact-head push/main/attempt1
两个 Python jobs 的四项步骤成功才建立 publication。后续输入更改须更新适用验证和 wheel。

成功生命周期为 Phase64 COMPLETED，Phase65 ACTIVE，Slices1–15 COMPLETED/PUBLISHED，
Slice16 NEXT/NOT IMPLEMENTED；N16 不变。没有 database execution、bytes-only source
authenticity、redaction、target realization 或 runtime fulfillment，completion audit 留在16。
