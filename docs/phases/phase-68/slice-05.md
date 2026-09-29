# Phase68 Slice05 — General original-output and native result bridge

S05 CANDIDATE; completed only after closure。基线 `15c64d5ad8d5680abd1d08a5ff4d43e94d0a8aab`，
tree `c4655d313c72803d3ced108f68e3c5342c0b38d0`，sole parent
`6d32ece0328d4760645faf2423d38dd2a2ef0c96`，自然 CI36613787353/push/main/attempt1。
S01–S04/C01 已发布；旧合同的 candidate-era 文字与失败记录保持。

## 原始输出到真实消费者

`prepare_output` 从已验证 emission 的完整 terminal 取得有序 `GeneralOutput`。
每列保留原 column、原 ResultField/export、ordinal/label、实际 terminal 和 target realization；
source、literal、expression、aggregate、window、SET 与立即 use 的证据仍在这些原节点中。
完整 units 保留隐藏计算、两侧 JOIN terminal、SET operands 和全部原义务。
独立检查先重跑原 plan/emission/result verifiers，再核对每个原对象和完整有序集合，
不调用 facts constructor 自证，也不把 computed/SET 输出伪装成 source field。

调用者显式把 `output` 交给原 `prepare_execution` / `prepare_bound_execution`；
PG executor 提交实际 compiler SQL 和 verified NativeUse 参数，metadata binding 后进入原
scalar、batch、managed Arrow 和真实 Arrow consumer。旧默认 source-only binder 与 S04
窄 projection 路径保留其原拒绝行为。新分支不增加任意 SQL 或 public API。
绑定 specialization 拥有自己的 output root、值相关域及原语义检查；A/B/A 不借用 seed 的范围。
新的 metadata/payload 检查之后仍检查 cancel/deadline；EOF、事务、delivery、cleanup 分开。

| 原准入族 | 输出规则与区别 | 当前命名见证 |
| --- | --- | --- |
| scan/projection/import/repeated | 原 source 与立即 use、独立 exports/位置 | direct、imported、self-use、two facades、empty |
| literal/scalar/LET/filter | 原 expression/stage 及 accepted values；不假造字段 | signed range、Bool/Int、Text、computed A/B/A、empty |
| JOIN | side/use、matched BAG、outer NULL extension、完整 membership right | CROSS/INNER/SEMI/ANTI、LEFT/RIGHT、PG restricted FULL |
| GROUPED/GLOBAL | key/result 各自 domain/nullability；COUNT 不是输入范围 | empty/all-null extrema、COUNT、hidden keys、重复组结果 |
| windows/QUALIFY | 原 call/default/peer/frame 的 native result law | ranking、bucket、distribution、navigation、frames、hidden QUALIFY |
| ORDER/LIMIT/DISTINCT | 完整 terminal、原 order 与上界、仅 visible tuple quotient | ordering、zero/inner LIMIT、hidden-group DISTINCT、mixed window chain |
| SET | 每个 positional operand、原 ordered fold、operation nullability | 六个 ALL/DISTINCT forms、empty、local ORDER/LIMIT、grouped producer |

完整有限 manifest 由 `tests/_pietto_phase68_slice5_cases.py` 的 named cases 和七 scalar fixtures
定义，不以测试计数取代支持域。窄 SMALLINT / 宽 navigation default、Int32 与大于 binary64
精确整数范围的 Int64 都有区分性输入。

## 三层表示与原有 exclusions

原 logical requirements、verified realization 和 actual protocol observations 分开。
`ProducerObservation` 的 range、Text 域、Decimal(p,s) 与 meaning 是 checked requirements，
不是从数据 min/max 或未知 metadata 猜出的测量值。Raw metadata 独立保留，缺失仍未知；
NUMERIC typmod 缺失时仍逐值检查原 precision/scale，不能任意放宽。
原 logical UNKNOWN 保留；consumer 不据它宣称 non-null。

七 result scalars 是 Int、Bool、Float、Text、Decimal、Timestamp、UUID；
四种 bindable leaves 仍只是 Bool/Int64/finite Float/Text。Decimal39/65、精确 Text、signed zero、
原 microsecond/timezone/range 与 UUID byte order/width 通过原 consumer 检查。
PG rows 使用实际 OID；MySQL source signedness 保持精确，computed unsigned BIGINT 只在已验证
非负 signed64 域内无损衔接，不扩大范围。MySQL null_ok 仅解码协议 0/1/unknown。
ADBC1.12 的 NUMERIC/UUID 仅按精确 PostgreSQL opaque type/storage/vendor 与 typname metadata
解码 string/binary；普通字符串或任意 bytes 不能自行建立 Decimal/UUID meaning。

原排除边界保持：MySQL FULL/GROUPS/EXCLUDE、MySQL Bool-window；SUM/AVG 与 non-Int
aggregate arguments；SET equality 仅 Int/Bool/Text/Decimal，UNION ALL 额外运输 Float。
Timestamp/UUID 的 explicit meaning 仍限 field-projection chains；非该 shape 保留
`PIE-B1003 / scalar_meaning_requires_field_projection`，其 empty/all-null 由真实空表与 NULL 表验证。
其余旧 operator/target/domain blockers 和 mandatory runtime obligations 不放宽。
shape binding 不授予执行权限；普通 non-R2 不要求 K-provider。

## 验收、复用与闭环

显式 `scripts/phase68_slice5_probe.py campaign` 使用已登记的 pinned isolated interpreter，
同轮串行取得 source/wheel PG production execution，以及 MySQL native prepared / PG ADBC
的 production-binder acceptance。后两者只是 test-only transport，product executors 仍属 S08/S09。
普通 pytest import/collection 不启动 DB、不找凭据、不安装依赖。

完整原值/重数/order oracle 来自原 fixture 输入和独立既有 reference；与新 descriptor、renderer、
decoder 分开。原根/列/meaning/terminal、stale binding、outer nullability、aggregate range、
SET operand、width/scale/bit/carrier 和 late value 的负控保留。
实际 submitted SQL/arguments、raw metadata、结果、consumer schema、origin 与各终态由 data-only
checker 重读；PASS flag 不作为证据。父进程核对完整 manifest、child exit/reap 和实际 import bytes。

| 输入闭包 | 当前验证 owner |
| --- | --- |
| 新 output/binding/native decoding/control 与直接 readers | CURRENT_LOCAL focused、Ruff/Pyright、完整 unfiltered guarded Python3.13 |
| S05 source/wheel PG 和 MySQL/ADBC bridge | CURRENT_LOCAL 新 native campaign；shared reader 变化使旧 acceptance 失效 |
| 新 src member / wheel 与安装 | CURRENT_LOCAL current wheel origins、policy-required package smoke；CURRENT_CI clean core/Arrow |
| 两 runtime、full collection/partitions、SDK9、product120/118、22完整 neutral documents | CURRENT_CI exact-head 原 mandatory consumers |
| legacy native receipts/captured replay、generated/golden | CURRENT_CI；不以旧 S04 或本地 driver demo 代替 |
| unchanged S01 resource/pump、fixture/oracle、C01 observation | REUSED_UNCHANGED 实现；新 runtime、mutation、source/wheel 身份各自 fresh |
| Git/publication infrastructure | 未改，NOT_REQUIRED_LOCAL 新 depth-one campaign |

复用兼容 compiler fixtures、typed inputs 和原资源/driver owners；source/wheel、corruption 与 actual
native routes 保持独立新鲜见证。不缓存 PASS、coverage 或 test selection，不改 CI placement/resource
policy。S10 检视累计 preparation，S19 实施必要 consolidation，S20 保持 audit-only。

只有当前完整验收、一次完整 review 与累计 causal repairs/follow-up、最终 required validation、
exact sealed tree 的普通 sole-parent commit/FF push、自然 push/main attempt1 的全部 mandatory
jobs/steps/raw consumers 及 owned resource cleanup 全部闭合，外部 S05 final report 才能激活完成。
唯一外部根与累计预算由本次 dispatch Section9 和 ledger 记录；失败与 producing revisions 不改写。
不追加 status-only commit。保留 `.agents/`、零字节 `NUL` 和所有未知文件。

S06 NEXT / NOT IMPLEMENTED / separate dispatch required。compositional R2/tie refinement/peers、
S07 guard fulfillment、S08/S09 executors、S10 source-free bundle、后续 durable/recovery/delivery
职责不移动；二十个产品位置、A01–A22、双入口与三路线目标保持，package/CLI0.1.0。
