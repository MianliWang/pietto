# Phase68 initiation notes

当前 owner 为 [S05](slice-05.md)：general original-output / producer binding 与七 scalar native result 候选；S01–S04/C01 已发布。S03 P1/P2 与 private PG 资格闭合；内部 gate QUALIFIED_UNDER_THIS_DISPATCH，20位置 JUSTIFIED_CANDIDATE。下列历史调查与失败文字不代表当前 gate。

S04 使用原 compiler fixture 与 S01 resource/pump；新身份/篡改测试独立重建必要 roots，native source/wheel 保持独立。没有新 repository observation cache、CI placement 或 profiling。S10 检视复用机会，S19 完成必要 acquisition consolidation，S20 只审计。

宏观选择已批准。比较三种顺序：格式/抽象先行会固定未知前提；单driver到底再复制易继承偶然实现；采用两片风险实验→PG最薄纵向→共同内核三路线→持久恢复→并发联合验收。
UNKNOWN阻止依赖它的生产冻结，不阻止本轮旨在解决前提的实验。

## 当前实测与边界

首次最小P02：三路线nonempty/empty/NULL准确返回，含2**53+1、重复use、引号/placeholder-like文本；ADBC1.12.0 use_copy=True/False均返回。
这是开发观察，不是最终candidate矩阵、跨runtime认证或产品三路线对等。第二次矩阵启动在SQLite内建模块无__file__处失败，数据库尚未启动；原失败与累计starts保留。
CPython3.13.13实际SQLite3.53.1，source_id=`c88b22011a54b4f6fbd149e9f8e4de77658ce58143a1af0e3785e4e6475127e9`（2026-05-05）；这里只观察身份，不认证durability。
后续P01–P07完整实际结果及收敛状态写入唯一外部ledger/report；未执行项保持待证。

## 外部参考 G

三组均ADAPT，不继承外部产品为Pietto全链证明。Snapshot/date为2026-09-28本期pin读取与明确引用；未实测内容仅属接口/设计前提。

| Reference | Problem / semantic identity | Layering / algorithm / interface | Testing / pitfalls | Disposition / WHAT_NOT_TO_COPY / owner |
| --- | --- | --- | --- | --- |
| [PG/Psycopg/ADBC](https://arrow.apache.org/adbc/current/python/recipe/postgresql.html) | native parameters、结果类型、transaction view；statement/session身份分开 | 显式driver消费已编译SQL；真实prepare/bind、pull、cancel；pins1.12.0/3.3.5 | 文档仍限制bind-result，已发布wheel必须实测；NUMERIC/UUID表示单列 | ADAPT；不复制fallback/写入样例或将batch作为语义；S01、S03/S09 |
| [MySQL consistent read](https://dev.mysql.com/doc/refman/8.4/en/innodb-consistent-read.html) / pinned Connector26.7.0源码 | 原生参数、consistent read与session差异 | 复用现有native prepared test owner，不将private driver实现复制进产品 | 原generic cursor曾改写有效identifier；actual protocol、query-role、EOF各自观察 | ADAPT；不继承DBMS调度器、DML或自动降级；S01/S08 |
| [SQLite WAL](https://www.sqlite.org/wal.html) | metadata事务不等于结果文件耐久；实际build/source与fix provenance | S02限定SQLite/FS profile，短事务引用immutable片段 | 版本号/WAL+FULL/未复现不是修复证明；ACK和source terminal独立 | ADAPT；不自写WAL，不宣称断电实测；S02/S11/S12 |

P02/S02输入：哪种真实可重新打开的同源版本能在原进程死亡后提供未捕获suffix；重复键/ORDER ties/全局操作如何证明occurrence覆盖；
片段fsync与metadata提交失败如何恢复；实际SQLite构建及FS前提是否合格；合作sink逻辑effect身份、ACK查询/丢失和retention如何闭合。
这些在S02结束、S03或任何持久格式冻结前决定；S02还需对全部20行重新做机制/尺寸核对，不实现生产loader。

## 30-field technical gate

下表逐项对应[当前启动gate](../../architecture/phase-initiation-gate-v1.md)。未解决生产前提有精确后续owner，不假称本Slice证明。

| # | Current disposition / owner |
| --- | --- |
| 1 | live baseline/CI/S16 external closure |
| 2 | dual entries and22acceptance |
| 3 | retained compiled semantic authority |
| 4 | occurrence/query/connection/attempt domains |
| 5 | observed statuses and conditional publication |
| 6 | asserted vs observed vs UNKNOWN |
| 7 | test-only S01; explicit future executor owner |
| 8 | upstream compiler to execution to result |
| 9 | private versions/reauthorization; S02 before formats |
| 10 | requirements independent from measured capabilities |
| 11 | source-free bundle vs live roots; later S05 |
| 12 | explicit owned test reads only |
| 13 | registered bounded connect/read/cancel/cleanup |
| 14 | loopback/owned roles/no persisted credentials |
| 15 | finite fixtures and independent typed BAG |
| 16 | 16rows/1MiB; original resource guard |
| 17 | S04 value-sensitive invalidation |
| 18 | no persistent observation authority |
| 19 | one DB; joined case-local manager/control only |
| 20 | four experiment statuses; no public diagnostic changes |
| 21 | offline checker separated from explicit run |
| 22 | no source syntax/API changes inS01 |
| 23 | three routes/exact pins/local-only observations |
| 24 | literal oracle and report damages |
| 25 | external experimental environment; core protected |
| 26 | new observations CPython3.13; old two-runtime regression |
| 27 | ordinary commit/FF/natural attempt1; no release |
| 28 | P01/P02/P03 blockers remain assigned |
| 29 | 20baseline; pendingS02 sizing |
| 30 | cumulative12; one review/followup; bounded starts |

## IPC continuation 历史：控制读取修复后的HOLD

原matrix3的14/57与HOLD候选保留。C12改为单owner raw/nonblocking控制读取；真实pipe/child回归直接消费实际pump，旧buffered策略作为区分性负例。
matrix4已取得PG rows19/19，随后遇到ADBC DataType元数据JSON计费错误；C13显式编码真实type_code，未知metadata仍None，pins/options未变。
matrix5在实际tree`bb4091acfb1ba7b97a9ba0d2bcd21615755b5388`取得全部57个keys及两target成功cleanup，但这不是57项通过。
C14仅修data-only verifier：MySQL helper.execute与实际cmd_stmt_execute分开核对，原始trace不改写，所有producer/query/fixture/driver输入经AST和完整footprint核对未变。
修正checker仍拒绝MySQL P06：execution_observed=False，parent未发送KILL QUERY，worker却写了无条件signal成功文字。该项应为INCONCLUSIVE_ENVIRONMENT（harness同步缺证据），不是driver unsupported或有效能力mismatch。
当前matrix预算5/5；取消观察与truthful signal记录需要修复及新执行，现有授权不足以再开完整矩阵。原57记录、真实执行tree与后来data-only checker/tree保持区分，不拼接旧新观察，不启动full或publication。
三路线P02原值/实际API参数对应已重验，ADBC1.12.0仍仅有本有限参数读取正例；不据此认定streaming/cancellation/recovery或产品parity。
S02未开始；后续source/store/sink与20行尺寸闸门保持。准确终态及累计账本见同一外部evidence root的ipc-continuation记录。

C15随后在原写集内准备了取消前提修正：native prepared使用Execute命令，并记录actual thread信息、manager signal_sent；standalone SLEEP中断返回1与正常0分开，未同步仍HOLD。
依据[MySQL8.4 thread commands](https://dev.mysql.com/doc/refman/8.4/en/thread-commands.html)及[SLEEP文档](https://dev.mysql.com/doc/refman/8.4/en/miscellaneous-functions.html#function_sleep)修正的是有限harness前提，不是产品语义变更；旧轮询具体线程状态未保存，文档/静态推理不代替新实测。
C15实际predicate/terminal无DB反例与完整principal38passed、测试Pyright通过；当前producer已改变，因此matrix5不能认证该候选，需要另行授权新完整矩阵。当前HOLD及原失败不清零。

## Matrix6：当前前提调查闭合，S01仍待完整发布闭环

matrix6在实际Git tree `d7dbfccd70a8e007032635c3ab634c8ea9118521`从头取得57个独立route/case keys，全部有限观察符合各自正/负试验目的；独立checker通过。
当前next-stage assessment为READY_FOR_SLICE02_EXPERIMENT；这不是adapter产品parity、全域取消、streaming、R2或20片尺寸证书，也不是S02派发。
旧matrix1–5、两个HOLD、C14历史data-only消费及其各自execution trees保留，未用旧14/56项拼接。此处docs-only结果记录后的最终tree与实际执行tree分开，完整可执行footprint须在Q4核对。

| Group | PG rows | MySQL rows | PG ADBC |
| --- | --- | --- | --- |
| P01 | 1/1 | 1/1 | 1/1 |
| P02 | 3/3 | 3/3 | 3/3 |
| P03 | 3/3 | 3/3 | 3/3 |
| P04 | 2/2 | 2/2 | 2/2 |
| P05 | 5/5 | 5/5 | 5/5 |
| P06 | 1/1 | 1/1 | 1/1 |
| P07 | 4/4 | 4/4 | 4/4 |

MySQL P06直接记录owned session10、Command=Execute、State=User sleep、Query=SELECT SLEEP(5)；manager KILL QUERY调用返回后才记录signal_sent=True。
同一query返回Int1、native_rowset_eof、statement close返回且control线程joined；耗时0.052073s。固定server max_execution_time10000ms大于SLEEP5，deadline/profile未放松；本结果限定该受控fixture。
PG rows记录QueryCanceled/57014；PG ADBC记录取消请求导致的libpq OSError，二者均在观察到PgSleep后由各自driver取消、statement关闭与control join。PG的request.signal_sent=False只表示manager没有代发，它们的实际driver signal结果单独记录。
三路线P02实际参数/结果已重验，ADBC原use_copy=True/False均成立；P03保留真实metadata和NUMERIC文本/UUID carriers适配义务。P04仅有限稳定view/Serializable正常只读历史。
P05保留错误发生的实际阶段，不把execute-time error写成首批交付后late error，不由fetchmany推server streaming。P07真实直接output正例与复杂族桥接owner分开。
C12–C15修正未改生产、pins、profiles、SQL/fixture目标或Phase67协议。matrix6两target均cleanup成功；完整full/四安装cells/SDK9/120118/22全文、publication/natural CI/28raw/native/current replay仍是S01完成的硬条件。

## S02 observations and remaining decision

真实前缀2行→原进程终止/session消失→新进程原版本3/1/0行；三driver分别闭合独立sink lost-ACK。SQLite固定build/实际ext4/WAL FULL和五切点见S02及raw，不扩为物理断电证明。全局查询不能按chunks拼接；immutable输入仍不足以保证tie-sensitive window/ORDER/LIMIT重复执行稳定性。全部22项保留；阻断依赖生产/格式冻结，待明确恢复算法及20片尺寸分配。

## S03 当前资格与后续责任

P1 的 component view 以 `(part,lid)` 覆盖完整实际域；仅 `lid` 的反例跨组件冲突。不同 fresh session/明确访问顺序保持 token→payload，对 expiry/replacement/visibility/role/token 损坏拒绝。
P2 的 choice order 与 original peer order 分离，frame membership 按原 frame 决定，再用 native FIRST/LAST/NTH 提取。PG GROUPS/exclusion 与 MySQL 已排除族保持分开；三路线均观察原生宽度、NULL、Float bits、empty/nonempty outer pages。
这些是有限 native/source 证据。构造性容量说明、全部未来 owners 与 proof 成本见 S03；不宣称实验 SQL 已成为 S06 lowering，也不把 composite integer 试验变成所有 provider token 的唯一类型。
S05 接通原 outputs 到 PB；S06 证明组合、peers/frames、完整 producer uses 和 occurrence 覆盖；S07 执行 guards；S10 source-free loader 独立重建 authority；S14 将这些事实接入真实 R2。没有第二个通用 frame evaluator。


## S06 current candidate and target-domain correction

[S06](slice-06.md) implements the explicit private refinement route and bounded
complete-query pages; current acceptance/publication remains its closure condition.
The approved PG int4 function-argument correction is separate from Int64 values,
defaults/results and R15 frames. Old VERIFIED/native-failure observations remain
historical; current excessive-argument documents are rejected. S06 supplies exact
source/use, choice/peer/frame, erasure and progress laws; S07/S08/S09/S10/S14 retain
their original ownership. Native observations remain finite and provider guarantees
remain explicit; none imply source-free loading or durable recovery completion.


## S07 private guarded route

[S07](slice-07.md) preserves the original request unit and complete direct/hop/path inventory.
The explicit multi-hop amendment opens only the private guarded shape gate; old no-request
PIE-B1003 controls and all other original exclusions remain. Ordinary execution shares actual
producer evaluation between guard and data without requiring R2; explicit refinement uses
the existing source vector and tie policy. Pending structure and live fulfillment have separate
owners. Current source/installed acceptance, exact-input readiness and complete auxiliary
session accounting precede publication. S08 remains separately dispatched.
