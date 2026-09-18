# Phase66 Slice3 Minimal Source Realization And Scan/Projection Emission v1

## Gate1 and ownership

本 Slice 消费已发布 Phase66 route lock 的 R01、R02 source/projection、首次 R23 和
R25。唯一正向关系形状是一个 selected TABLE/QUERY、一个 direct source、field-only
final projection，允许字段重排和改名。BAG、NULL、source/input/export occurrence 与
SQL symbol 各自保留。没有 named/shared producer、CTE、scalar、LET、filter、JOIN、
group、window、DISTINCT、ORDER、LIMIT、SET 或 parameter lowering；这些 later-owned
形状返回当前 implementation blocker，不改变其既定规划状态。Slice4 未开始。

Gate0 接受 `cf873dda68aae99078210e0a971bb04ab6eca2a3`，tree
`de5e7738975cc98e80f87b928f4f7e858a8e2a6f`，parent
`49caec122a1d1242e7ce7178c8507aa3f7dbfacb`。自然 CI35018753152 的两个 compiler、
两个 target 和 aggregate 均成功。此处只记录已发生的基线，不预写本 Slice 的发布身份。
原 diagnostic-registry Gate1 STOP、追加审计、冻结边界及累计运行记录保留在仓库外
`~/.local/state/pietto/evidence/phase66-slice3/`；该 STOP 不消耗 code correction。

冻结实际边界 A8/M13/D0：新增本合同、五个 `project_sql_emission*.py`、独立 probe 和
本 Slice principal；修改 development/status/roadmap、facility contract、diagnostics、
三个 facility helpers（runner/cases/observation）、facility principal、legacy diagnostic
union reader、sole lifecycle/inventory readers 和 capability parity privacy reader。
resource helper、另外三个 permitted privacy guards 无新 consumer，不修改。

已审计入口是 `build_project_sql_plan` → exact `verify_project_sql_plan` → inspection 的
source/input/export、requirements、source-map、raw target assessment。下游不要求 Phase65
whole-target-positive；保留 genuine negative/conflicting facts 和 mandatory enforcement。
语义/IR/Phase65 authorities、legacy emitters、public exports、CLI、旧 JSON、dependencies、
target pins、workflow、validator、typing configuration 均保持各自现有边界。

## Preparation and representation

`prepare_project_sql_emission` 只接显式 UTF-8 contract bytes 和当前 runtime verification。
结构遵循 `pietto.emission-contract.v1`；先完整校验，再按 selected evidence closure 判断
applicability。selector 只在输入准备时绑定；ordinal 不接受 bool，name 仅校验 ordinal 的
原 occurrence。namespace/relation/column 是独立 component，locator 不作为 SQL。
accepted bytes 与 normalized bytes 留在 invocation；没有文件读取、数据库发现或凭证。

V01/V02/V03/V06 消费原 builtin type、NULL posture 及相符的 declared storage/domain。
V04 的 explicit-module root 保留 original TypeExpr/canonical resolution，但没有 legacy
SemanticModel 的 Decimal parameter map。因此只在 preparation 中对当前唯一 resolution
所绑定的 exact original TypeExpr/retained alias terminal 调用既有
`semantic.analyzer._decimal_precision_scale_fact`；消费成功的原校验结果，不复制 p/s 规则、
重跑 analyze、构造 DISTINCT/SET evidence 或修改原 diagnostics。缺参数或校验失败为
MISSING_EVIDENCE，声明与已验证参数不符为 REPRESENTATION。上游有效 precision 上限仍为38；
physical V04 的65不创造额外 logical evidence。verifier/serializer 不调用此校验器。

当前 Timestamp/UUID 只有 builtin name/nullability，没有 V05 所需 calendar/timezone/
precision/standard-byte-order meaning evidence，返回 PIE-B1004。声明不能补造 logical facts。
Float 只传递 declared finite binary64 域，不授予 row equality。没有最终 CAST 修补。

局部 encoding details：timestamp domain 为 `{kind:"timestamp"}`，表示 route-lock 固定
V05 域；uuid 为 `{kind:"uuid",encoding:"standard_bytes"}`；finite_float 为
`{kind:"finite_float",format:"binary64"}`。expression scope 的 site/context 各为
`{kind,position}`，分别引用当前 expression site 和其 block，另保留 exact source selector。
resource_limits 是非空 closed object，可含 sql_bytes/artifact_bytes/nodes/parameters/columns；
值为非负整数，只能降低现有上限，parameters=0 与本 Slice 的空参数集相容。其它 premise 是其既定 scope 下的 typed 声明，不能表示 SQL、
predicate 或 rule_correct。未使用的 setting 不成为运行时履行声明。

保留 input 1MiB/4096 sources/32768 fields/128 nesting，SQL8MiB、public artifact16MiB、
32768 generated nodes/parameters，以及 PostgreSQL1664/MySQL4096 output columns 的上限。
标识符保留 PostgreSQL UTF-8 byte 长度和 MySQL character/BMP 边界；超长 label 拒绝，
不截断。参考 [PostgreSQL lexical rules](https://www.postgresql.org/docs/18/sql-syntax-lexical.html)、
[MySQL names](https://dev.mysql.com/doc/refman/8.4/en/identifiers.html) 与
[identifier limits](https://dev.mysql.com/doc/refman/8.4/en/identifier-length.html)。

## SQL, independent verification and public bytes

闭合 AST 只有 SELECT、qualified scan、field projection 和局部 SQL symbols。
内部关系名为 s0；physical reference 始终有独立 namespace qualifier，字段始终有 relation
qualifier。最终 label 是原输出 label。无 SELECT *、ORDER、DISTINCT、filter、cast、
raw SQL、DML/DDL、locking、OUTFILE 或 assignment。

plan/AST verifier 检查 exact current roots、source/input/export/projection 身份及完整顺序。
独立 bytes verifier 按实际 AST 检查 event grammar、真实 identifier 解码、separator、
punctuation 和每段 SQL bytes；不调用 builder/renderer 重建答案。
事件的 zero-based half-open UTF-8 ranges 由 renderer 当场记录，完整覆盖最终 SQL；
origin references 保留 source-map entries 及其原 source positions，parser character
坐标与 SQL byte offsets 分开。摘要或 metadata 不能认证错误 SQL。

原始 requirement denominator 来自原 plan demands 和独立验证的 report；generated
denominator 从真实 scan、全部 source fields、每个 projection 和 SELECT bytes 结构重建。
两列表协调删除仍失败。无 emitted parameters 由实际 field-only AST 和 captured
envelope/slots/uses 联合证明；PRESERVE 与 eligible set 为空的 BIND_SAFE 都保留。

生产 `serialize_project_sql_emission` 实现 `pietto.sql-emission.v1` 的三个 closed branches。
INPUT_REJECTED 含非空 cli_errors；BLOCKED 含 blockers 或原 ERROR；两者 artifact:null，
没有 SQL/columns/ranges 等成功 payload。VERIFIED 恰有 route-lock 规定的成功 keys。
PIE-B1001–PIE-B1008 通过独立行为/序列化测试登记；legacy implementation 仍恰为 PIE-B1000，
registry 的完整集合等于两个 disjoint implemented domains 的并集。

request 包含 logical owner、原 trusted source module/sha256/byte_count、normalized input
和 literal_policy。columns 按 ordinal 保留 label、logical kind/name/parameters、nullable、
physical representation，及 source selector/field/source_port/input_port/export/projection/
sql_symbol 的 positional correspondence。ranges 包含 start/end/kind/role/subject/origins；
requirements 包含 denominator/ordinal/kind/subject/rule/disposition/premises/evidence。
这些是有限公共投影，不序列化 private graph 或捏造 observed server build。

独立 test-only `decode_public` 从实际 serialized bytes 检查三个 branch、字段/类型、
code/reason、positions、requirements、SQL grammar/UTF-8 ranges 及空 slot/use 对应。
JSON escaping 解码后恢复 SQL，再以 UTF-8 提交。decoded data 不恢复 runtime authority，
也不是数据库 result decoder。公共 CLI/file loading/atomic user output 留给 Slice13；
private AST portable observation 留给 Slice14。

## Exact current target manifest

每个 target 的 current manifest 恰为下列12个 case；前六项保留 Slice2 的原独立断言。

| Case | Exact variants and required evidence |
| --- | --- |
| A_legacy | 原 installed legacy consumer，duplicate Int BAG |
| B_result | 原 ordered result/metadata control |
| C_parameters | 原 driver protocol/ordered fixed-input control |
| D_diagnostics | 原 notices/warnings 和 expected incomplete-observer negative |
| E_recovery | 原 same-session success/error/recovery/success |
| F_privilege_cleanup | 原 SELECT-only role 与 owned cleanup |
| G_emission_table_bag | bag；TABLE，五字段重排/改名，四行含一个重复 pair |
| H_emission_query_bag | bag；QUERY，同一 typed BAG，BIND_SAFE 的空 eligible set |
| I_emission_table_empty | empty；TABLE，零行且完整五列 metadata |
| J_emission_query_empty | empty；QUERY，同一空输入边界 |
| K_emission_rejected | duplicate_selector、ordinal_bool、stale_selector；三份 INPUT_REJECTED，无提交 |
| L_emission_blocked | missing_source、bool_domain、decimal_mismatch、timestamp_meaning、uuid_meaning、where_later；六份 BLOCKED，无提交 |

新 pipeline 每 target 恰13份公共 document、四次成功 SELECT；拒绝/阻断不计数据库查询成功。
有效 rows 的独立 oracle 覆盖9007199254740993、nullable Bool、trailing spaces/non-BMP Text、
Decimal(9,2)、finite Float/signed zero。比较完整 typed row multisets，保留重复数与位置。
physical names 含点、空格、反引号、双引号和多字节 é。PostgreSQL Bool 与 MySQL signed
integer Bool 的实际 driver tags 分开；Decimal 观察保留精确十进制及 scale，不做产品转换。

现有 wheel/build/install 复用；新 probe 和 source/contract/config inputs 纳入真实 transfer
identity，`-I` child 从 installed wheel 调用新生产路径并记录同 child origins/member bytes。
adapter 只接独立 public decode 产出的 SQL/ordered empty parameters，逐字节核对；没有 private
shortcut、checkout imports 或手写成功 envelope。失败 variants 记录实际 execute boundary 的
submission counter 不变。aggregate 同时要求完整旧/新 manifest、input identity、原环境、
terminal observation 和独立 cleanup absence。默认 pytest 不发现数据库或 Docker。

## Validation and publication

先 focused/Ruff/两套 Pyright，完整审查后运行 authoritative Python3.13、golden 和 installed
package 检查，再顺序运行两个 target 的完整 current manifest；本次未改 parser generation
或 Git/CI infrastructure，不无故增加 generated/depth-one workload。自然 CI 仍独立要求
Python3.12、Python3.13、PostgreSQL、MySQL 和 strict aggregate 五项成功。累计预算沿用
原 Slice3，失败证据不覆盖，不 rerun CI。seal/ordinary commit/normal ff push 的实际身份
留在 Git 和仓库外收据中。

成功发布后 Phase65 COMPLETED；Phase66 ACTIVE，Slices1–3 COMPLETED/PUBLISHED，Slice4
NEXT/NOT IMPLEMENTED，Slices5–16 NOT IMPLEMENTED，N66=16。未交付公共 project emit CLI、
parameter lowering、通用 result decoder 或 product executor，不宣称整个 Phase66 完成。
