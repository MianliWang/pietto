# Phase66 Slice4 Named/Shared Producer Scopes And Terminal Output Emission v1

## Scope and the explicit R03 amendment

本次用户指令明确授权 R03 排期修订。原 Slice1 route 把 R03 completing Slice 记为04；
该历史不是 Slice3 PASS 自动授予的新授权。本 Slice 交付 named/imported/reexported
field-projection chains、exact definition/use/terminal layout 和 capture-free SQL。
重复 JOIN/SET uses 与三种 ORDER carriers 只有真实 upstream graph/阻断文档检查。

R03 outstanding joint execution: Slice7 repeated/shared JOIN; Slice10 ordinary/rebound/completed ORDER and ORDER/LIMIT sharing; Slice11 repeated UNION ALL and two import facades.

这些后续见证必须通过 installed 新 pipeline 联合执行；layout、BLOCKED documents、
分别执行的 queries 或手写 control 均不能抵扣。R03 及整个 Phase66 尚未完成。
N66=16 与各 operator owner 保持不变。

Gate0 基线是 `d53952e6e1763f76e0257c5e6221bd1fc414cb75`，tree
`b6f1de9795f9feb889dfbd3e5498b84ab35728d3`，parent
`cf873dda68aae99078210e0a971bb04ab6eca2a3`；已发布自然 CI35038724418
的五项必需 jobs 成功。Gate1 初次冻结漏掉已获准的 Slice3 exact manifest reader；
完整 focused 检查发现后、修改该 reader 前修订为 A3/M17/D0，共20条已授权路径。
两份 freeze、失败与累计账本保留在仓库外 `~/.local/state/pietto/evidence/phase66-slice4/`。

新文件为本合同、`project_sql_emission_scopes.py` 和 Slice4 principal；生产修改限于
既有五个 emission modules。既有 resource grants 已覆盖新 fixture，资源 helper 无需修改；
scopes 不定义新的 diagnostic code，也不引入 protected capability API consumer。
diagnostic registry/legacy exact domains、语义/IR/Phase65 production、public exports、CLI、
依赖/lock/pins/workflow/validator/typing configuration 均保留。

## Exact authority and admitted SQL

正向域保留所有 direct projections，扩展到有限无环 TABLE/QUERY 命名链，每个 body
恰有一个 relation input 和 field-only projection。各层可重复引用、重排、省略和改名。
import/reexport 的定义模块、每条 use-local binding/origin trail 保留。物理 source mapping
仍完整覆盖原 schema；忽略投影未用列不能删除原 stage-value demands。

layout 从 VERIFIED whole plan 的完整 definitions/uses 及 `terminal_exports()` /
`input_terminals()` 建立。独立 checker 从原 source ports/result exports 重建 terminal
映像，并逐项核对完整 ordered inventory 与依赖先后，拒绝缺项、foreign port、collapsed
use、反向依赖或循环。canonical producer export、actual result terminal、consumer input
port 是不同对象；每个 emitted edge 绑定立即前驱，transitive physical lineage 仅说明来源。

layout 在后续算子的真实 plans 上也有 applicability consumer，但没有 SQL body/name/scope
字段。JOIN/SET/ORDER/window/filter 等未实现 shape 返回准确 `PIE-B1003`，不为可支持的
子 scan 单独生成成功 SQL。全项目 semantic ERROR、必要 enforcement、raw negative/conflict
facts 保留；不要求 Phase65 whole-target-positive。

选定唯一 strategy：一个顶层非递归 `WITH`，每个中间 producer 恰一个 CTE，按原依赖顺序
出现。CTE 为 `p0`、`p1` 等；完整 terminal column list 使用 `c0`、`c1` 等短名；use aliases
为 `s0`、`s1` 等。字段引用绑定具体 terminal，不以名称或 SQL ordinal 替代原 identity。
每个 CTE body 只有 field SELECT；没有嵌套 WITH/derived SELECT，SELECT nesting depth 为1。
最后 SELECT 使用原最终 labels。直接查询没有新结构时保留原 SQL/public bytes。

物理表始终使用独立 namespace qualifier。PostgreSQL 的 schema qualification 可区分
同名 CTE/物理表，MySQL 的 CTE 定义/引用没有 schema prefix；因此 qualified physical scan
与 unqualified CTE reference 是不同 typed token roles。依据
[PostgreSQL18 SELECT](https://www.postgresql.org/docs/18/sql-select.html) 与
[MySQL nonrecursive WITH binding rules](https://dev.mysql.com/worklog/task/?id=883)。
没有 materialization hint、复制/内联优化、evaluation-once 或 nondeterministic coupling 承诺。

## Representations, names and limits

各边界保留真实 type/NULL evidence 与 source representation；Decimal 只复用 Slice3
preparation 的原参数校验入口，不重新 analyze、推断 p/s 或 CAST。Timestamp/UUID 缺少
原 meaning evidence 仍为 `PIE-B1004`。PRESERVE 与 genuinely empty BIND_SAFE 都覆盖整个
closure；任一非空 eligible slot/value/use 不进入本 Slice 正向域。

命名链需要 statement `identifier_case` 声明：PG 为 `quoted_exact`，MY 为
`lower_case_table_names=0`。缺失为 `PIE-B1004`，不一致为 `PIE-B1005`。facility 实际读取
PG `max_identifier_length=63` 与 MY `lower_case_table_names=0`，并用 physical `p0` 与首个
CTE `p0` 同名、logical `Key`/`key` 含不同值类型的实际 query 检验绑定。MySQL case 依据
[8.4 identifier case rules](https://dev.mysql.com/doc/refman/8.4/en/identifier-case-sensitivity.html)。
这些声明只在实际准入的 named SQL 上使用，不为被阻断的 graph 捏造 SQL scope。

中间 authored label 不按最终 SQL label 长度拒绝，因为实际输出的是短生成名；最终 label
保持 PG63 UTF-8 bytes / MY256 characters 及既有字符限制，拒绝超长而不截断。
对每个实际 SELECT/CTE header 检查 PG1664 / MY4096 columns；对实际结构检查32768 nodes、
8MiB SQL、16MiB artifact、空 parameters 和更严格的声明。JSON input depth128 不充作 SQL
nesting cap。平坦 WITH 不随链深度增加 SELECT nesting；不宣称未经观察的 target CTE 数上限
或整个 pipeline 的线性复杂度。测试记录实际 layout/SQL/artifact 尺寸与时间。

## Verification and public encoding

AST verifier 独立核对每个定义、use、立即 terminal、canonical export、input port、physical
source field、SQL symbol 和最终输出的对应。bytes verifier 消费实际 token/events，检查
真实引号、标点、作用域/列引用、全覆盖 UTF-8 half-open ranges 与 source-map origins；
不调用 construction/rendering 生成“期望 SQL”。

原 requirement denominator 来自完整原 plan，包括省略字段仍保留的所有 stage inputs。
generated denominator 来自实际 CTE definitions/header columns、每个 named use 的完整
立即 terminal、所有 bodies/projections/bytes。R03 naming requirements 引用实际声明的
premise occurrence；coordinated deletion 或空 self-certified lists 无法通过。

继续使用 `pietto.sql-emission.v1` 的原三个 branches 和顶层 keys。最终 columns 的
`source`/`field`/`source_port` 仍是物理来源；`input_port` 是最后一个立即前驱 use 的 port，
不再要求其编号等于物理 field ordinal。direct 文档保留原编号条件。
CTE header 的 `terminal_column` ranges 指向 actual result terminal；body label 指向
canonical export；column ranges 指向所读取的立即 terminal；use alias 指向 original use。
新增 generated kinds 为 `cte_definition`、`terminal_column`、`named_use`、
`immediate_terminal`、`nonrecursive_with_bytes`，仍用已有 subject/rule/premises fields。
没有 private graph dump、第二 public format 或 runtime identity restoration。

独立 data-only decoder 从实际 public SQL bytes/ranges 读取上述有限 grammar，逐个检查
backward-only definitions、complete terminal lists、alias/column bindings、physical provenance、
两个 requirement inventories 和空 parameter sets。JSON 解码后重新 UTF-8 编码；失败文档
保持 artifact:null、无 SQL、完整 blockers/cli_errors/original diagnostics。
新增 scope ranges 的 origins 还须保留相应角色、每个 origin 的 authored cause、原 source
inventory 内的路径与一致坐标；同 subject 的完整 ordered origins 必须一致，origin ordinal
不可转移给另一个 subject。CTE terminals、use/input ports、projection/exports 的 causes
需与各自 definition 相符；import/reexport 路线保留完整有序 hops。检查的是文档一致性，
不是 source bytes、坐标或 runtime identity 的真实性认证；合法 type-alias associations 保留。
所有 statement premises 按原 preparation 顺序读取，不因位于 `environment` 或某 source 的
`premises` 而改变适用性；两种 SQL grammar 都检查标识符与实际 SQL/artifact/node/column
尺寸的全部更严格声明，参数集合保持空。来源元数据不是执行或认证凭据。

## Exact additive facility denominator

原 A–L 及其13份公共 documents 保持：4 VERIFIED、3 INPUT_REJECTED、6 BLOCKED。
新增以下3个 cases、13个 variants；current manifest 恰为15 cases、26份公共 documents：
10 successful SELECTs、3 INPUT_REJECTED、13 BLOCKED。失败16项有实际 execute counter
不变证据；不计为数据库 query success。

| Case | Exact variants | Boundary |
| --- | --- | --- |
| M_named_chain | table_bag, query_bag, empty, long_intermediate | 两个 CTE、每层不同 ports，重复引用/省略/改名，6个 positional outputs |
| N_imported_chain | bag, empty | a→b reexport→main，真实 defining-module provenance；bag 使用 physical p0 collision |
| O_named_later | self_join, union_dag, two_facades, order_ordinary, order_rebound, order_completed, producer_filter | VERIFIED upstream structural layout，公共 BLOCKED，无 target submission |

成功 oracle 独立固定 typed row multisets：保留大 Int、nullable Bool、尾空格/非BMP Text、
精确 Decimal、finite Float/signed zero、duplicates、empty 和重复 Int 的位置/次数。
原 observer/diagnostics/same-session recovery/SELECT-only privileges/owned cleanup 保持。
新 schema-qualified collision fixture 由既有 manager setup 加载，没有改资源 acquisition 或 TLS。

同一个 candidate wheel 包含新 scopes module；实际 `-I` child 导入记录包含它。
单文件输入按原 bytes 标识，多模块输入用按文件名排序的完整 filename→text JSON bytes
标识，同时公共 request 保留每个 trusted module 的原 bytes hash/length。probe/config/contract
与全部源码输入进入既有 receipt transfer identity。adapter 仅提交独立 decode 的原 SQL。

## Gates and lifecycle

保持 pytest offline、xdist/serial fallback、两套 typing authority、sole lifecycle/inventory
readers。最终运行 authoritative Python3.13、两版本 focused、golden/package、两个顺序
完整 target manifests；grammar/generated 与 Git/workflow infrastructure 未改变，按 live
AGENTS.md 选择本地 generated/depth-one tiers。自然 CI 仍要求五项成功。

所有失败、修正和调用在仓库外累计；一次 ordinary commit/normal ff push，必要时最多一个
余额内 child；无 rerun/dispatch/cancel/amend/rebase/force。最终发布身份不预写候选。
成功后 Phase65 COMPLETED；Phase66 ACTIVE，Slices1–4 COMPLETED/PUBLISHED，Slice5
NEXT/NOT IMPLEMENTED，Slices6–16 NOT IMPLEMENTED，N66=16。Slice5 未开始。
本 Slice 不实现 JOIN/ORDER/SET lowering、非空 parameters、public project emit CLI、
通用 result decoder 或 product executor；不宣称 R03 完整 target conformance。
