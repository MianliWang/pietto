# Pietto 决策记录

现有历史决策仍由对应 published contracts 保存；本入口不覆盖旧 authority。

| ID | 已选规则／备选与理由 | evidence／scope／next consumer／最晚决定点 |
| --- | --- | --- |
| D67.01 | target-neutral ResultContract，ProducerResultBinding 与 ArrowResultBinding 分离；拒绝转换掩盖 mismatch | 用户接受v4＋Phase66 J02/V05；Slice02 |
| D67.02 | 独立 canonical private bytes；Arrow metadata只冗余传输 | 旧 private boundary经验；Slice03；不得成为runtime身份权威 |
| D67.03 | nested-ready shape消费单一canonical scalar authority；不建第二solver/NestedRelation | 用户锁定；Slice02/04–08 |
| D67.04 | finite RecordBatch/reader；normal finalization不等于executor success | 用户锁定；Slices09/12，Phase68执行owner |
| D67.05 | 实验pin PyArrow25.0.1，仅已测Linux x86-64/CPython3.12/3.13；不推测版本范围、不装core | 官方两wheel元数据；cases types/carriers/adaptation/strings/capsules/alias/finite/ipc/device在3.12.13/3.13.13已真实通过；Slice13公开extra |
| D67.06 | 四CI shards消费独立requirements；hard coverage/locality与advisory timing/history分开 | 本次明确授权＋R1；当前CI与未来phase starts |
| D67.07 | string默认，large_string仅显式binding；UUID extension优先但须C/IPC保真，否则显式fixed binary16 | 本Slice capsules/ipc已证实UUID extension保真，选canonical extension；binary16只保留显式备选；Slices05/07/10/12 |
| D67.08 | owned/transferred/显式borrowed分开，借用须lifetime/non-mutation义务；contract独立于buffer所有权 | alias/capsules已证实：默认owned、有效protocol transfer、显式borrowed须lifetime/non-mutation；Slice10 |

Timestamp/UUID显式private meaning已由Slice07取得upstream witnesses；默认无meaning仍拒绝，Arrow roundtrip不赋予意义。
公开alpha归Phase69，stable1.0归Phase83，Rust归Phase90；91–97维持完成审计的tentative/owner-only界定。

| ID | 已选规则／备选与理由 | evidence／scope／next consumer／最晚决定点 |
| --- | --- | --- |
| D67.09 | Slice02 private scalar-leaf contract引用完整 retained fields；direct/projection Int 的 pg_int8/my_bigint 先与 supplied observations 对应，再显式 int64；不接受隐式推断/强制转换 | 本次批准；真实两target source与同根多realization；Slices03/04 |
| D67.10 | owned positional rows，64 fields/4096 rows/8MiB data+validity，允许小 configured ceiling 测拒绝；batch 不带 EOF/whole-result completion | 本次批准；owned mutation/typed empty/NULL/limit negatives；Slices09–10扩完整有限记账 |
| D67.11 | `pietto.result-contract.v1` 是有界中立描述；UTF-8规范JSON+单LF；pure view不复活runtime，独立checker消费显式原合同/verification | Slice03；4MiB/depth48/65536 values/8192 records/16384 references/单text128KiB/total text2MiB/1024 fields；只约束codec |
| D67.12 | descriptive coordinate equality与live对象身份分开；alias/import path分组及ORDER的完整retained inputs分别核对；coherent substitute pure可通过但runtime必须拒绝 | Slice03；two-runtime installed cases与exporter-defect injection；后续scalar扩展显式更新三检查，不承诺public format兼容 |

| D67.13 | Slice04 Arrow整数默认保留已验证producer宽度；显式per-field request绑定exact field，完整int_range必须包含于目标signed16/32/64，允许domain-total lossless narrowing/widening；先核对producer，样本不决定合法性 | 已批准Slice04；private binding实例化，不改变DSL coercion或public格式 |
| D67.14 | pg_bool的exact bool与my_bool01的exact int0/1载体显式区分；Arrow checker验证logical bool；finite_float/binary64仅exact finite float，signed-zero由独立值快照/IEEE bits核对 | Slice04；不扩MySQL Bool value-window或payload authenticity保证 |

| D67.15 | Text保留exact str/Unicode scalar序列，max_characters按码点；pg_text拒绝NUL，my_varchar保留合法supplied-row NUL；encoding/collation/padding逐项核对，不成为Arrow比较语义 | 已批准Slice05；官方字符存储依据与result-boundary正负例，不冒充native DB输入认证 |
| D67.16 | 默认string、仅exact field显式32/64 offset请求选择large_string；实际UTF-8+offset+validity计费，numeric旧计费保持；retained buffers先于full validation | Slice05；中立codec bytes不受选择影响；S09/S10/S11继续拥有reader/协议/一般ingress |

| D67.17 | 经S06前提HOLD后明确批准shared Decimal parameter precision1..65、scale0..p；旧38位合同有效，当前producer仍scale≤min(p,30) | 用户addendum及Phase31 reader补充授权；同一rule/site/alias，非算术或nominal结果扩展 |
| D67.18 | fixed-scale有限数值按sign/digits/exponent精确转为≤p位tuple；Decimal正负零统一；默认p≤38 decimal128、p39..65 decimal256，低p显式256允许 | S06；exact Decimal、无context舍入/flags污染、16/32byte计费；不改变Float signed-zero或中立codec |

| D67.19 | 显式private target-neutral source-occurrence meaning bundle；独立验证完整源集合/closed law，result与emission共同保留；默认/CLI/native旧caller不自动opt-in | S07四项选择已明确批准；仅builtin field-only scan/projection，不开第二solver或其他lowering |
| D67.20 | Civil Timestamp/microsecond/no timezone，inclusive1000-01-01 00:00:00.000000至9999-12-31 23:59:59.499999；拒绝aware/fold1，int ticks编码 | 用户批准的精确共同transport域，细化V05年级outline；MySQL8.4文档依据，不称pinned server实测 |
| D67.21 | UUID全部128bits标准big-endian；PG exact UUID与MySQL exact16bytes分离；默认canonical pa.uuid，显式binary16；fake extension不授予意义 | 沿用原canonical选择并由S07私有binding实现；无generation/version限制/registry mutation |

| D67.22 | 显式完整positional field-label请求只改变Arrow presentation；exact ResultField/ordinal绑定，None保留默认；每项1024及总65536 UTF-8 bytes，不改旧payload计费 | S08 dispatch；producer标签、source identity、PIE-S2305、neutral bytes保持；schema不认证同type同名值历史 |
| D67.23 | S08 midpoint保留N67=16，owned scalar integration不宣称reader/completion/protocol/IPC/extra已完成 | 见S08三层A01–A18与S/H/L/K/Q；S09/S10/S12/S13必要决定在各自首次接口前关闭 |

| D67.24 | 显式caller extent绑定exact fresh/exclusive source、binding和session；normal EOF、exact rows、successful close共同允许completion | S09三项选择已明确批准；不认证调用方/原值/DB完整性，不要求未来executor预先COUNT |
| D67.25 | 同步checked pull保留每个batch/empty，count equality不是EOF，early close incomplete，late/read/cleanup失败终态无receipt | S09；返回supplied carrier不升级ownership；S10/S11/S12及Phase68各留原职责 |
| D67.26 | 保留batch/codec/label上限；新增1024批/1048576行/64MiB sum(max(logical,referenced))，重复引用/empty计费，max_batches+1次source pull | S09；caller-only tightening，不能限定单次upstream分配/阻塞，无timeout或backpressure承诺 |

| D67.27 | buffer copy/borrow与C handle transfer是独立维度；默认真实buffer copy，显式BorrowLease经Python buffer exporter pin原owner至所有consumer释放 | S10 ACTIVE dispatch；holding owner不阻止alias mutation，实际机制/边界见[S10](phases/phase-67/slice-10.md) |
| D67.28 | C schema请求仅None/exact equivalent，无cast；fresh S09 reader授予一个managed stream consumer，显式interop session负责确定性cleanup | S10两runtime premise证实SDK close不执行generator finally；source completion与downstream error分列 |

| D67.29 | rows/batch/raw reader显式入口复用原S08–S10机制；raw-reader lease绑定原source，接受前caller保留责任、接受后composition失败清理session | S11 ACTIVE已委派private接口；[合同](phases/phase-67/slice-11.md)，无新envelope或状态机 |

## Phase67 Slice12 private transport

[Slice12](phases/phase-67/slice-12.md) 将既有有限结果封装为standard Arrow IPC与固定100-byte header、无trailer、96MiB frame。payload/canonical-contract SHA-256、length及rows/batches只检查transport correspondence；message metadata不授予authority；live binding及原值correspondence仍独立，stronger trust/signing归Phase84。此为已批准private实现选择，不冻结公共wire格式。

## Phase67 Slice13 optional dependency

D67.30：用户批准唯一公开selector `pietto[arrow]`，精确 `pyarrow==25.0.1`；core依赖、
`requires-python >=3.12`、package/CLI0.1.0保持。已验证支撑集仅CPython3.12/3.13、Linux
x86-64，不将支持表变为marker；独立hash lock保留tested-wheel integrity。此为依赖公开可安装，
result API仍private、Phase69负责public alpha，不构成release。实测与隔离见[S13](phases/phase-67/slice-13.md)。

## Phase67 Slice14 real consumer

D67.31：用户批准两条有限证据链：真实编译/result/SDK搭配supplied fixtures，以及已由原strict
接受的同次Phase66原生执行观察重放。后者实际输入只取observations.rows，先核对原recipe、
artifact、protocol facts和lifecycle；声明domain仍为声明。预先复用receipt行数作extent是replay
调用方声明，不是独立DB completeness证据。原strict留core，额外Arrow环境不引入driver依赖。
只新增一个test-only sidecar/纯数据checker，不新增公共schema、executor或native查询。

## Phase67 Slice15：whole-result joint assurance

`IMPLEMENTATION_FREEDOM`：沿用现有fixture、independent snapshots与required product artifact，
一个test-only law helper连接十组finite结果关系；无新production facade/协议/cache。
`DERIVED_MECHANICAL`：当前120/118和helper闭包/typing/lifecycle直接读者随实际新增集合更新。
[Slice15](phases/phase-67/slice-15.md) 区分transport顺序与typed BAG、pure equivalent文档与live bound
authority、条件input完成与delivery成功；Phase68 readiness只交付现有API及其明确前提。

## Phase67 Slice16：scope-qualified completion audit

本Slice只核对已批准要求与实际证据，不扩大support或重新决策executor。
[A01–A18三层矩阵、retrospective与handoff](phases/phase-67/completion-audit.md)保留descriptor、fixture、
captured-native replay及future execution层。[唯一闭环规则](phases/phase-67/slice-16.md#唯一闭环规则)
在实际证据全部满足后才激活完成；当前S16为candidate。Phase68另行FULL initiation，先消费audit与适用lessons。

## Phase68 approved optional execution decisions

[Phase68 brief](phases/phase-68/brief.md) preserves the user's dual live/bundle entries, typed rebinding, three-route parity, default checks/stable view, explicit Serializable profile, exclusive owned resources, dual durable delivery, real R1/R2, cooperative sink and bounded concurrency. Core has no ambient execution.
S01 is a test-only FULL initiation candidate; P01/P02/P03 facts gate production boundaries and S02 revalidates the20-row route. No public format, production loader, durable job schema or Phase69 release is frozen here. Unknowns remain blocking for their dependent owner; complete negative experiments never waive product goals.

S02调查保留上述目标，实证边界与剩余route见[S02](phases/phase-68/slice-02.md)。`ARCHITECTURE_DECISION / USER_DECISION_REQUIRED`：先解决全查询重复求值稳定性及输出occurrence恢复，再冻结S03/S11接口；现有scan witness不能授权全族R2。当前PRODUCT_GATE_BLOCKED_REPLAN，未决定新source服务或削减功能。

## Phase68 S03 — approved source and tie decisions

R2 的 caller 在首次 attempt 前显式固定未指定 ties；不能重写原 ordering/peers/frames/exclusions、类型、NULL、重数、producer uses 或 guards。恢复不能看过 prefix 后另选 policy。普通 non-R2 emission 不变。
R2 要求 external provider 对完整实际 source domain 给出可重开 retained version 与稳定非空单射 tokens；既有 composite keys 可合格。无需为任意 identity-free sources 合成身份，不强制 exchangeability fallback，不创建业务列或 source infrastructure。
S03 的 component-view/native peer-frame 资格支持 JUSTIFIED_CANDIDATE，不是全族产品认证。S05 负责 original-output/PB；S06 负责组合 R2 facts/refinement/lowering/独立 correspondence；S10 负责无源码 bundle/loader 与 midpoint；S03/S08/S09 各自带 controls。S19 联合验收、20位置与 A01–A22 不变。细节及 conditional gate 见 [S03](phases/phase-68/slice-03.md)。

## Phase68 S09 — approved PostgreSQL ADBC source assurance

用户明确批准 S09 private `postgres_adbc` 的闭合 native source-admission domain，及独立、显式的
PG managed-deployment definition/security-lifetime premise。它绑定原 access/source roots 和
有界行政 scope；operator 从发现前直到最后远端 source use 保持相关定义/权限稳定，正常行更新
仍允许。compliance 未独立验证，native all-definition exclusion 未证明；source structure、
data snapshot、retained provider 与 guards/outputs 分别核查。旧 PG rows/MySQL 和旧声明含义不变。
具体域、实际原始反例与 S10 fresh acceptance 边界见 [S09](phases/phase-68/slice-09.md)。

## Phase68 S18 — selected execution extras

S18 派发选定三个路线 extra：`execute-postgres`（`pyarrow==25.0.1`、`psycopg[binary]==3.3.5`）、`execute-mysql`
（`pyarrow==25.0.1`、`mysql-connector-python==26.7.0`）与 `execute-postgres-adbc`（`pyarrow==25.0.1`、
`adbc-driver-postgresql==1.12.0`、`adbc-driver-manager==1.12.0`）。D67.30 的 `arrow` 选择不变并承担无驱动的已保存结果使用；
不增加 recovery 别名、全驱动 extra 或平台 marker。core 依赖、版本与入口不变；extra 不选择路线、不授予执行、不证明存储资格，
执行 API 仍为私有；不冻结 Phase69 公共 API 或发布工程。精确依赖边界与已验证域见 [S18](phases/phase-68/slice-18.md)。

## 0.1.0 public preview release — owner decisions (2026-10-10)

所有者在 Phase69 之外批准一次公开预览发行，让外部用户可以下载并试用现有能力。发布范围只限已验证的公开面：单文件与项目的
`check`、`explain`、`emit-sql`，以及现有的公开 Python 导出；执行与结果 API 仍为私有，由 Phase69 负责公开。所有者选择 MIT
许可证（`LICENSE`）；第三方材料按 wheel、sdist 与源码归档分列于 `THIRD_PARTY_NOTICES.md`，上游原文按固定 commit（abego 许可页为固定 Wayback 快照，Python3 模板头取自已跟踪的 ANTLR jar）存于
`LICENSES/`，不作法律结论。core 依赖固定为 `antlr4-python3-runtime==4.13.2`。包与 CLI 版本保持 0.1.0，tag `v0.1.0`，在
GitHub 上标为 pre-release；不上传 PyPI/TestPyPI。只构建一次，验收过的确切 wheel/sdist 即发布字节，独立验证构建不替换它们。0.1.0 与 tag v0.1.0 由此绑定本次验收字节；Phase69 的发行须使用新的版本号与 tag，不得以不同字节复用 0.1.0。
Phase69 规划的顺序、范围与所有者已作出的决定不因此改变；Phase69 重新绑定时扣除已完成的许可与元数据工作。

## PostgreSQL refinement-page JIT — owner decisions (2026-10-10)

所有者批准 Phase69 路线锁定前的第一个前置：私有 `postgres_rows` 与 `postgres_adbc` 在每个生成的细化页提交前，于来源资格认证之后、
同一只读事务内单独发出事务局部的 `SELECT pg_catalog.set_config('jit','off',true)` 并读回 `off`，读回不符即以该路线既有的
context 错误码失败关闭；设置持续到该 attempt 的事务结束，不持久化，`CONTEXT_SQL` 的 17 列不变。范围是两条路线上的全部细化页
（REFINED 捕获、R2 捕获与恢复、普通 refined/guarded 执行）；refined guard 语句与来源准入扫描仍按服务端默认 JIT，legacy `''`
路线、MySQL、细化生成器与独立验证器不变。这不是全局 JIT 策略：不用 ALTER SYSTEM/DATABASE/ROLE，不加连接启动参数，不改测试
容器命令；10 s 单语句上限与 20 s 默认 attempt 期限不变。仓库外对基线代码手动关闭 JIT 的机制测量（固定 18.6 镜像、1 CPU 容器、
矩阵 fixtures）中，234 个不同页面逐页回放最慢 0.017 s，结果与默认 JIT 逐行相同；c3-full01 越线的两页在 1/6/8 路负载下最慢
0.027 s；关闭 JIT 不改变细化 SQL 的体积增长，宽 key 与大数据量下的成本不作承诺；依 PostgreSQL 18.6 源码，没有 LLVM provider
的服务端仍接受该设置，只是空操作（未实测）。候选在目标负载下的原生证据在本次派发的外部证据实例。本节闭合
[插段记录](spec/post-phase68-performance-interlude-v1.md)“Rejected or deferred”中生成细化页 JIT 设置的延期项；R2 窗口 SQL
形态与 10 s 上限仍由下一个并行插段决定。
