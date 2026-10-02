# Phase68 Slice09 — Private PostgreSQL ADBC owned execution

S09 CANDIDATE; completed only after closure。基线 `e6719209bd935f0f4063959ffa64b47d548dcdfd`，
tree `14ce58e6b3a66323dc212e42726265578be55c94`；S08 自然 CI36926813328/push/main/attempt1。
原 S09 dispatch 与已批准 PostgreSQL source-assurance amendment 共同约束本实例；唯一累计账本位于
`/home/mianliwang/.local/state/pietto/evidence/phase68-slice09-20261001T220643Z`。
原 HOLD、原始观察、失败与预算均保留；用户明确将 causal correction ceiling 从24调整为36、readiness ceiling 从8调整为12，其他上限不变。S10 NOT STARTED；本文不预言发布或全矩阵通过。

## 已批准的来源与信任边界

`postgres_adbc` 是显式 private route。`PostgresADBCDeploymentPremise` 默认缺失，绑定 exact
PostgresAccess、原 source roots 和有界 schema scope；不是 MySQL premise。ordinary、bound、
guarded、refined、guarded-refined 都在任何 source/registry/schema/key/guard/data 求值前取得
当前资格；Serializable 和 `allow_guard_sql=False` 不免除这些要求。

operator 从 discovery 前直到最后远端 source use，负责协调完整相关 definitions/security
及 inheritance/partition membership 的变更。正常行更新仍允许；本前提不代替实际只读
Repeatable Read/Serializable、R2 version/key/retention、tie choice、guard 或结果检查。
无法排除仍在远端运行的工作时，local close/cancel 不结束 operator 的保护责任。

| 责任 | 准确边界 |
| --- | --- |
| source/dependency 与可达机制资格 | 当次 ADBC 数据连接的 native replies，经独立 checker 核对完整集合和位置 |
| native context / data snapshot | 当次实际 role、database、settings、session、xid 和事务状态；不以副本自洽代替 |
| definition/security lifetime | `EXPLICIT_MANAGED_DEPLOYMENT_PREMISE` |
| operator compliance | `NOT_INDEPENDENTLY_VERIFIED` |
| native all-definition exclusion | `NOT_DEMONSTRATED / NOT CLAIMED` |
| provider retention / token-to-payload | 保留 S03/S06 原外部责任，不新增认证 |

旧 `read_only_object` 和 `row_domain_matches` 的含义不变。普通 PostgreSQL rows 维持既有
准入；其更广 source-assurance applicability 没有因 S09 自动获证。MySQL 保留独立的
managed-deployment 条件。三个 route 不是相同的通用安全域。

## 有限 native source 机制

安全 catalog 查询与小型 PG18 native-node reader 只读取结构，不执行未知 source、函数体、
EXPLAIN 或 LIMIT0 来试探安全性。已资格化后才运行原有有界 schema/version/key reads。
registry 是实际来源；其 wrapper、依赖与 security context 先于 registry value query 检查。

当前 profile 消费 local heap relations、所需 inheritance/partition domain、projection/filter、
scalar registry subquery、UNION ALL 与嵌套 invoker/definer view 的 native rewrite facts。
同一对象的 immutable metadata 可在当次复用，每条 reference/security path 仍保留位置和重数；
PG security_invoker 每一层使用原始查询用户；不继承外层 definer 的 base-row 权限。
原 ONLY 边界不会扩成 inherited scan。外层 Pietto query-family 分母不因此缩减。

有限 core implementation/signature/type links 逐项检查，不按函数名、namespace、volatility
或 OID 阈值授予权限。opaque user routines、未资格化 custom operators/casts、foreign/extension
reads、RLS 路径及未知 native node 会拒绝。virtual generated expressions 仅能使用已资格化
结构与机制；write-time defaults/triggers 和 stored generated values 不作为 read-time calls。
准入上限为128个 relation、有限 catalog/role/edge inventory、64层、32768个 node 和8MiB
catalog bytes，并同时受 execution limits 约束；超限是资源失败，不是空闭包。

原 HOLD 的 PG18.6 catalog 观察证明：字符串函数体的表依赖不必出现在 `pg_depend`，修改函数
不必改变根 view definition。**没有执行该可疑函数，也没有 PG 1→2 result/MVCC 反例。**
原始最小记录与新回归由 `test_phase68_slice9_postgres_source_assurance.py`、S09 native probe
和独立 checker 维护；不把 MySQL 历史结果转写成 PG 观察。

## ADBC 生命周期与结果

固定 PG18.6、ADBC driver/manager1.12.0、Arrow25.0.1；optional imports 只发生在显式执行。
直接持有 database/connection/statement/C stream/Arrow reader，显式 host/port/database/user/
password/TLS；无 driver-manifest、CWD、service/password-file 或 pool fallback。
Linux pinned profile 对 CA/CRL/client-cert/key 使用 `/dev/null` character device 的不可达 child
path，禁止空选项触发 home-directory defaults；`require` 仍只要求加密，未新增 peer identity 认证。
默认 PostgreSQL rows constructor 不变，也不把 ADBC 对象标为 Psycopg owner。

参数来自原 verified use/binding/control domain，单个 typed Arrow parameter row；原 SQL 与
`$n` correspondence 不变。data/guard/page 预先选择 `use_copy=True`，metadata/context/control
预先选择 False；不会在错误后重试另一模式或版本。

原生 Arrow schema、opaque NUMERIC/UUID carrier、完整 positional output 与原 S05 scalar/
managed consumer 分开。先以实际 raw referenced buffers 检查预算，保留有界 Arrow batches，
关闭 reader 后核查事务再逐批交付；不积累无界 Python row list 或 Table。
`BATCH_SIZE_HINT_BYTES` 是 hint，不能约束单次 native allocation、prefetch 或 server work；
无 hard RSS/零复制承诺。交付的 owned/copied batch 与 source handle 关闭分别验证。

COPY reader 的正常终态还须与其 native 协议匹配：当 pinned reader 已核查 CommandComplete、
完成 Arrow EOF 并关闭后，允许一次固定 non-COPY context checkpoint 完成 ReadyForQuery drain；
随后必须回到 `intrans` 且实际 xid/role/settings 不变。错误或部分 stream 不获此例外。
这不是把任意 `active` 状态当成有效事务；下一次检查也不能重用该许可。

原 guard/data materialization、完整匹配边界、refined source vector 和 outer page law 由 S06/S07
原 owners 验证。native EOF、checked-source completion、transaction ACK/UNKNOWN、delivery 和
cleanup 各自保留。cancel requested/returned/observed 分列；native protocol error 退役连接，
不重连、重试整个 query 或以关闭证明远端 quiescence。primary failure 不被 cleanup 覆盖。

## 验收与后续交接

完整 current source/installed 分母来自 S05/S06/S07 owners：每 origin 52 ordinary、54 refined、
55 guarded entries，另含来源/身份/控制与 fresh same-version witnesses。旧 driver/transport
观察仅保留原 narrow meaning；不能代替本次 product acceptance。raw consumer 复核实际 SQL/
bind/Arrow/native context、完整 values、所有 auxiliary/origin 及终态，损坏真实记录须拒绝。

只有 integrated review、bounded follow-up、当前 acceptance、authoritative unfiltered core3.13
六门、实际选择的 auxiliaries、exact sealed tree、ordinary commit/FF push、自然 exact-head
push/main attempt1 及全部 mandatory consumers/cleanup 闭合，外部新 terminal 才激活完成。
core、pins、public SQL/CLI/JSON、package0.1.0、三路线原边界与20位置/A01–A22 保持。

S10 须取得 fresh operator acceptance/native qualification，并明确映射三个 route profiles；
bundle 可携带描述与要求，不能携带已复活的 live permission 或 operator-compliance proof。
S19 完成必要 acquisition consolidation，S20 保持 audit-only；本 Slice 不实现 durable recovery、
source-free bundle、多 job scheduler、store/sink/GC 或 execution extra。


事务终结还须重新比对当次初始 native context：即使 request/context 校验、cancel 或 consumer
已提前失败，COMMIT/ROLLBACK 前仍核对真实 handle、status 与完整 typed context；失配则保留
UNKNOWN 并关闭自有连接，不把另一事务的 ACK 归给原尝试。该检查不依赖可变的 context 副本。
普通 native family 验收显式请求120秒，覆盖 instrumentation 与完整语义验证；产品默认20秒、
原生 statement timeout 上限10秒以及独立取消/deadline控制保持。原60秒失败完整保留，不计PASS。
