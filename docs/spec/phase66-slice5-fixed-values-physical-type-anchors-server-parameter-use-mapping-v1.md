# Phase66 Slice5 Fixed Values, Physical Anchors and Native Parameter Uses v1

## Scope and ordered prerequisite

本 Slice 分两部分、共用预算、一次最终发布。A 先修复 test-only MySQL native prepared
transport，并用 installed 既有 emitter、独立 protocol controls 和真实隔离目标验证；
B 才扩展原 literal/envelope 的 leaf/sign projection。A 通过不是 Slice5 完成。
N66=16。Phase65 语义/IR/plan authority、legacy emitters 和产品执行边界保持。

R03 outstanding joint execution: Slice7 repeated/shared JOIN; Slice10 ordinary/rebound/completed ORDER and ORDER/LIMIT sharing; Slice11 repeated UNION ALL and two import facades.

## Approved native adapter amendment

固定 Connector/Python26.7.0 pure implementation、原 server image/pin/TLS 和配置。
原 MySQLCursorPrepared.execute 会把合法物理列名中的 percent-s 加双引号误改为问号
加双引号。原离线真实方法见证保留为 counterexample，绝不算 server execution。
此前 A–O 的有限成功记录保持历史含义，不能外推为所有输入的 SQL byte guarantee。

所有 MySQL query 用途的提交统一使用 test-only
tests/_pietto_mysql_native_prepared.py。用途覆盖 legacy、新 public artifact、参数、
recovery、privilege、session observation；选择不依赖 SQL 内容或参数数量。
既有固定 BEGIN/rollback 属于 transaction management，保留普通 command；
BEGIN 仅由明确 begin() 用途调用，不能作为 native failure 的 fallback。
第一次 native BEGIN 的1295/HY000失败记录保留，不把协议不支持改称成功。
固定 manager setup/environment/diagnostics 保留原 cursor 路由；只有显式 native
warning/no-rowset control 使用 manager 的新路由。PostgreSQL 继续使用 RawCursor。
生产代码不导入 adapter/driver，没有 DSN、用户 SQL runner、产品 executor 或 fallback。

API 是固定版本的 implementation dependency：

1. cmd_stmt_prepare 接收独立 public decode 恢复的 exact UTF-8 bytes。
2. 立即登记返回的 statement_id，核对 num_params/parameters 与参数个数，包括零。
3. cmd_stmt_execute 使用同一 connection、ID、返回 metadata 和独立解码的 ordered data。
4. rowset tuple 到来时只设置公开 unread_result=True；get_rows(binary=True,
   columns=实际 result metadata, count=1000) 消费真正 rowset EOF 后由驱动清除此状态。
   metadata EOF 单独保留，不以空 batch 或预期行数替代结果终止。
5. 完整 drain 后先 SHOW COUNT(*) WARNINGS、再 SHOW WARNINGS，保留 total/details。
   error、未完成 fetch、诊断丢失或 cleanup 失败都保留，不能覆盖 primary failure。
6. finally 对每个返回的 owned ID 调用 cmd_stmt_close。COM_STMT_CLOSE 无响应；
   complete_no_ack 仅表示调用/send 完成。connection teardown 是独立 resource 事实。

一次 prepare/一次 execute/close 不需要 cmd_stmt_reset；reset 不代表 transaction rollback。
沿用10秒query、20秒read及30秒resource cleanup边界；没有改 socket、packet、
authentication、TLS、regex 或其它 driver state。

## Independent call observation

限定当前 connection、固定 driver source paths 和本次调用的 sys.setprofile hook
观察真实 cmd_stmt_prepare、cmd_stmt_execute、get_rows、cmd_stmt_close 和 command-send。
get_rows 只观察 binary=True 的 statement 结果，普通 SHOW diagnostics 的文本结果
由既有 diagnostics observer 单独保存，不能混入 native rowset 的 EOF/row denominator。
另外只读观察该 connection 的 driver encoder make_stmt_execute 输入/返回，
把实际 ordered data/metadata 与传入 command-send 的 execute payload 连接起来；
adapter 自己不调用或复制 packet helper。原 hook 在 finally 恢复。
不记录 authentication/credentials/TLS keys 或其它 connection 的数据。

exact public SQL bytes = 独立 decoder SQL bytes = prepare statement bytes
= STMT_PREPARE command-send payload。这不是 packet capture 或 server acknowledgement。
真实 prepare response、binary rows、metadata、terminal 与独立 oracle 是另外的证据。

## Private receipt v2

当前 private receipt 格式为 pietto.target-conformance-receipt.v2；
原 v1 bytes/历史解释保持，当前 verifier 不把它们当作新路由证据。
artifact filename/run/attempt/head/native digest/received bytes 规则不变。
public pietto.sql-emission.v1 的既有顶层字段不变。

每个 observation 在原字段之外必须有 api、native。cursor 路由 api 等于实际
cursor_type，native=null；新路由 api=mysql.native-prepared.v1，cursor_type=null。
native 是以下 closed object：

    adapter, driver_version, driver_sources, session_id, statement_id, prepare,
    parameter_count, parameter_metadata, result_metadata, metadata_eof, terminal,
    unread_final, close_send, events

events 按实际调用顺序保存 event/session_id/value；prepare/execute/encoder/fetch/close
都有 call/return，command-send 记录 command/payload/expect_response。
参数 records 保持有限 scalar tags；driver metadata 与 public logical map 各自保留。
verifier 检查 exact event denominator/order、SQL bytes、ID/session/argument/metadata、
encoder-return/send payload、完整 terminal/rows 和 close-send。
resource journal 另记录 query/manager 的实际 session_id 与 connection close 返回。
删 event、换 ID/session/payload/values、缺 terminal/close、替换 v1 都拒绝。
没有 driver 操作或数据库连接的 data-only receipt verification 不恢复源码权威。

## Part A finite corpus

A–O 原 case IDs/variants/逻辑结果全部保留；其历史26份公共文档为10 VERIFIED、
3 INPUT_REJECTED、13 BLOCKED。当前 adapter/receipt assertions 显式迁移到 v2。

新增 P_native_identifiers：
preserve、bind、plain_preserve、plain_bind、named_preserve、named_bind、
empty_preserve、empty_bind。完整 source schema 映射四个物理字段：
percent-s 加双引号=11、问号加双引号=99、percent-s=7、nullable neighbor=NULL。
owned table 有两份重复行，另有同 schema 空表。投影目标字段必须返回11，不能返回99；
plain control 返回7；empty 保留 positional metadata；named 读 immediate terminal。
上述 BIND envelope 为空，不冒充非空 parameter 产品见证。

Q_native_lifecycle 是独立 protocol control：success、allocated execute-time error、
同 session rollback/recovery/success、native warning/no-rowset、空 binary rowset；
MySQL 另有零参数向量对一个 server marker 的 count mismatch，必须阻止 execute。
独立 JSON/integer-cast control 不授予产品相应表达式 lowering。

Part A focused prerequisite 固定选择 A_legacy、C_parameters、E_recovery、
P_native_identifiers、Q_native_lifecycle；它不是完整 manifest。
当前完整 A–Q 共17 cases/34公共文档，18 VERIFIED、3 INPUT_REJECTED、13 BLOCKED；
A–F 与 Q 的独立 controls 不混入公共文档计数。
Part B 的实现前冻结记录保留于外部 Slice5 evidence；下面记录对应的当前合同。
Part A receipts 不认证后续发生变化的 wheel/harness，final acceptance 必须重新绑定。

## Reviewed interfaces

[MySQL identifiers](https://dev.mysql.com/doc/refman/8.4/en/identifiers.html)、
[prepared cursor API](https://dev.mysql.com/doc/connector-python/en/connector-python-api-mysqlcursorprepared.html)
和已安装26.7.0 connection.py/protocol.py/abstracts.py 的实际源码共同限定本实现。
网页不替代实际版本/source identity、server response 或独立 oracle。

## Part B literal and sign domain

只允许原 builtin Bool/Int/Text/finite Float 叶及其已经验证的 unary +/- 链；
field reference 仍可直接传递，field operand 的新 unary lowering 不在本域。
不增加 binary/call/LET/WHERE/ON/JOIN/group/window/DISTINCT/ORDER/LIMIT/SET。
NULL 保留原 PIE-S2333/unavailable root，未扩大原语法；nonfinite 数据始终拒绝。
每个 Int leaf、anchor intermediate、unary result 都须落入 signed64；
-9223372036854775808 的正数叶9223372036854775808不在该域，不能靠最终负值修复。
这是 literal anchor 域，不是一般 Int->BIGINT 映射。SQL 保留每个 sign，不折叠原节点。
Float 使用原 binary64 值和 sign-sensitive hex；-0.0 的原 envelope 仍可为正零叶。

| Tag | PostgreSQL PRESERVE / BIND | MySQL PRESERVE / BIND | Wire and result |
| --- | --- | --- | --- |
| Bool | CAST(TRUE/FALSE or $n AS pg_catalog.bool) | CAST(TRUE/FALSE or ? AS SIGNED) | PG bool；MY显式0/1整数；MY结果是signed BIGINT expression，不是TINYINT source |
| Int | canonical decimal or $n, CAST AS pg_catalog.int8 | canonical decimal or ?, CAST AS SIGNED | Python int保持精确；检查每层signed64 |
| Float | quoted shortest-roundtrip decimal or $n, CAST AS pg_catalog.float8 | 带exponent的approximate numeric token或?, CAST AS DOUBLE | finite binary64；PG无numeric中间层，MY无decimal/default/narrow Float中间层 |
| Text | E-string逐UTF8 byte octal或$n, CAST AS pg_catalog.text COLLATE C | UTF8 X-hex或?, CAST AS CHAR CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin | 精确Unicode、原长度/trailing spaces；PG拒绝NUL；不指定截断长度，不复制source字段metadata |

Text result 的 public domain max_characters 来自该固定值自身；physical kind 分别为
pg_text/my_utf8mb4_text，MySQL character-expression family 不冒称source VARCHAR(n)。
空/nonempty的实际metadata另由有限target oracle检查；raw nullable/protocol字段保留，
不把parameter metadata的nullable估计当原logical NULL事实。显式COLLATE限定语义；
仅有charset不算collation证明。SQL/artifact/node/parameter原ceilings保持。

existing operator_environment=builtin_only、client_encoding 原声明均检查；
非空 BIND 另检查现有 parameter_protocol 的 postgres_extended/mysql_prepared 声明。
这不增设session设置，不改变server SQL mode。规则依据已固定版本及
[PG lexical rules](https://www.postgresql.org/docs/18/sql-syntax-lexical.html)、
[PG numeric types](https://www.postgresql.org/docs/18/datatype-numeric.html)、
[MySQL casts](https://dev.mysql.com/doc/refman/8.4/en/cast-functions.html)和
[MySQL hex literals](https://dev.mysql.com/doc/refman/8.4/en/hexadecimal-literals.html)。

## Runtime and public correspondence

runtime SQLColumn field branch不变；SQLLiteralColumn/LiteralOrigin保存exact原expression、
literal site、原slot/value、canonical export、actual terminal。constant没有BoundField/source
port。后续named读取只有immediate producer/input port，复用origin而不重提取值。
所有CTE列和中间值仍在SQL和双denominator中，即使final output未引用。

fixed_values按原logical slot顺序，每项恰为slot/reference/site/tag/value：
slot为zero-based wire ordinal，reference/site为原literal_slot/literal_site reference。
Bool用JSON bool；Int为canonical decimal string；Float为finite canonical binary64 hex；
Text用exact Unicode。映射来自原对象身份，不把序号相等当runtime identity。

parameter_uses恰为use/slot/server_index/physical_type/range；range恰为start/end。
use/slot从零开始，native server_index从一开始且按first-emitted order分配。
PG只对same slot兼容context复用；MY每个occurrence一个argument；equal distinct slots不合并。
public decode后的值/map是提交参数唯一来源，PRESERVE为零slots/uses/arguments。

literal correspondence恰为literal_origin/expression/input_port/producer/export/projection/sql_symbol。
literal_origin恰为expression/leaf/site/slot/export/terminal；
producer为null或export/terminal对象。current computed projection的input_port/producer为null；
named read保留实际immediate边。原source-origin correspondence的keys和含义不变。

lexical ranges仍完整连续覆盖UTF8 SQL；其后追加postorder expression_range，
role为anchor/unary。placeholder独立range不扩大为CAST/sign范围。
new generated requirements是value_projection/literal/parameter/type_anchor/unary。
literal evidence恰为单项tag/value；unary evidence恰为单项operator(+/-)；
其余新generated evidence为空。它们覆盖未最终可见的literal，允许decoder独立拒绝
PRESERVE token/value/sign改动。runtime verifier不调用builder/renderer/semantic resolver。
coherent alternate public data不是源码认证，也不恢复可继续编译的runtime root。

## Final finite manifest and boundaries

完整当前manifest恰为A–S19 cases、46 public documents/target：
30 VERIFIED SELECT、3 INPUT_REJECTED、13 BLOCKED。A–O的15 cases/26 documents与原逻辑
outcomes保留；A–F、Q independent controls与公共文档计数分开。

R_fixed_direct的6 variants为table_preserve/table_bind/query_preserve/query_bind/
empty_preserve/empty_bind。20输出列；非空BIND18 slots/uses/arguments，PRESERVE均为零。
覆盖true/false、Int1/Float1、zero/signs/-0.0/-1.5、9007199254740993、equal17的distinct slots，
空/trailing/Unicode/nonBMP/quote/backslash/newline/marker Text，11-vs99 physical regression，
duplicates、neighbor NULL和完整empty-input metadata。

S_fixed_named的6 variants为named_preserve/named_bind/imported_preserve/imported_bind/
empty_preserve/empty_bind。7输出列；BIND5 slots/uses/arguments，PRESERVE均为零。
producer的unused true仍有原值、SQL、requirements和binding；base17多次terminal读取只有
一个original slot/marker。不同producer层新增literal，import/reexport路径保留原cause。

Q current MySQL8 observations分别覆盖success、DO JSON的execute3141/22032、同session恢复、
native warning/no-rowset、empty rowset、zero-vector arity rejection、SELECT JSON的fetch3141/22032、
再恢复success。PG保持5 observations。原误判阶段的失败收据全部保留。
component allocator的zero/one/many及incompatible-context测试不冒充whole-query重复marker证据。
R03 joint witnesses仍归Slices7/10/11，Slice6和产品执行/结果解码/CLI/caller rebind均未实施。
