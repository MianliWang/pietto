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

## Parallelism interlude — owner decisions and closure (2026-10-10)

所有者批准 Phase69 路线锁定前的第二个前置，即并行插段，并选择只发布按前提表述的接收规则核心 R1、R4、R10、R12
（[验证 runner 接收规则](spec/validation-runner-acceptance-v1.md)）：仓库内不加入接收工具、补集报告、环境记录格式或 runner 脚本，
也不做资格运行；接收与补集由以后的派发决定，存储正例的补集随之暂缓（派生记录，不是另一项决定），存储正例照旧在集成主机的完整
权威验证内运行。Teach 只做通道、首闭环与非权威开发循环，脚本留在仓库外，结果不算验证证据；托管 CI 按前提不执行 Gate 2 验证的
任何部分，自然 CI 的 Gate 3 角色不变。I1 使存储环境类显式（`hosted-refusal`、
`qualified`、`report`）；I2 发布规则 spec 与单次调用内的工作守恒获取认领（跨调用等待是已知残余）；I3 拆为 I3a（版本单一 owner、负向打包测试的 `match=`、CI 中
wheel 文件名的唯一匹配、只改测试的重复获取）与 I3b（phase53 整合并入按功能重组，其计划获批后才开始），关闭条文随 I3a 发布。

R2 窗口细化页的 SQL 形态与 10 s 单语句上限（U2）关闭：10 s 上限不变，本插段与 Phase69 都不改该 SQL 形态。残余是细化 SQL
的体积增长不变、refined guard 与来源准入扫描仍按服务端默认 JIT、宽 key 与大数据量下的成本不作承诺，在 Phase69 重新绑定时写入
R2 的支持说明。关闭 JIT 后单个细化页仍 ≥1 s、数据放大测量 ≥5 s、出现 57014（语句超时取消），或 Phase69 提出更宽 key 的支持
要求时，U2 重新交所有者决定。本节闭合[插段记录](spec/post-phase68-performance-interlude-v1.md)“Rejected or deferred”中生成
细化页延期项的窗口 SQL 形态与 10 s 上限部分；JIT 设置部分已由[上一节](#postgresql-refinement-page-jit--owner-decisions-2026-10-10)
闭合。同一延期项列出的并行化路线处置如下：单次调用内的工作守恒获取认领随 I2 发布；source-free 不再拆分；把不用存储的测试移出共享获取分片、
Compiler/Package 拆分、按成本发牌或第四个 general-runtime 分片都不做；托管字节码预编译不采用，只作测量，采用须另行授权；
`[[file_costs]]` 的完整四 worker 测量转入按功能重组。

关闭记录：规则已发布，目前只有集成主机满足其前提。按只发布规则核心的选择，多 runner 组合验证暂缓，留给以后提供接收工具的派发决定。所有者批准的批量合入写入
`AGENTS.md` 与[开发文档](development.md#lean-gate-v2)：每片一个提交，批次最终树一次权威验证，一次快进推送，自然 CI 只跑批次头，
批内提交没有自己的 CI 结果，以其结果为准。本插段的 `COMPLETED` 与规则的生效都以发布关闭条文的已推送 head（关闭提交本身，或在批次中推送时的批次头）
的自然 exact-head CI 为准：普通提交、FF push 与全部 job 成功后成立，此前是 candidate。下一步是另行派发的 Phase69
重新绑定。

## 0.1.1 PyPI packaging release — owner decisions (2026-10-11)

所有者授权把只改打包信息的 0.1.1 发布到 PyPI。0.1.0 不能上传：它打包的 README 写明不在 PyPI、从 GitHub wheel URL 安装，23 个链接中
16 个是仓库相对链接，METADATA 也没有 Project-URL、classifier 与 keyword；PyPI 不允许替换一个版本的文件，而改动这些内容就会改变 0.1.0
已绑定的字节，因此 0.1.0 仍只在 GitHub。0.1.1 不改变编译器与 CLI 行为；除版本号（含 `cli.py` 的回退版本字面量）外，相对 0.1.0 的
唯一源码差异是已发布的私有执行 JIT 关闭调整（dd2148b4）。README 兼作 PyPI 描述：状态写 public preview，以 `pip install pietto` 安装，
GitHub release 作为备选；仓库相对链接改为固定到 tag `v0.1.1` 的绝对地址（徽章、CI 与 release 链接本来就是绝对地址），只有 Direction 一节的 roadmap
链接指向 main；quick start 删除描述性 header 行，并把生成单个带点标识符 `"public.users"` 的 `postgres.table("public.users")` 换成普通表名；
新增只列目标、不写 phase 与日期的 Direction 一节，只列 roadmap 已有 owner 的目标（尚无 owner 的 SQL 到 Pietto 转换不列入），详细计划仍在
roadmap。`pyproject.toml` 增加 project URLs、classifiers（`Development Status :: 2 - Pre-Alpha`，不加
License classifier，PEP 639 `License-Expression` 不变）与 keywords，版本经登记的版本 owner 升到 0.1.1。tag `v0.1.1` 在 GitHub 上标为
pre-release 并附 `SHA256SUMS`；不使用 TestPyPI；所有者以自己的 token 上传。与 0.1.0 一样只构建一次，验收过的确切 wheel/sdist 即
GitHub 与 PyPI 的发布字节，0.1.1 与 tag v0.1.1 由此绑定这些字节。升版按功能支持而定的原则与 Phase69 规划都不因此改变。同一授权中，
所有者同意在 Phase69 之后插入一期，负责常用表达式、函数与 project 模式 SQL emission 骨干；roadmap 只登记这一 owner，不授权实现，
Phase70 及以后的编号不变。

## Phase69 FULL Phase Start — owner decisions (2026-10-09 and 2026-10-10)

These entries record only what the owner explicitly chose in the Phase69 FULL Phase Start: the first round of 2026-10-09 (D69.01–D69.06), the second
round of the same day (updates of D69.05 and D69.06, and D69.07–D69.10), and the owner's supplements of 2026-10-10 (to D69.03, D69.06, D69.07,
D69.09 and D69.10). Later owner decisions that calibrate them are cited in place and in the 2026-10-11 section below. Names and signatures chosen
during implementation, release operations and the 0.1.0 decisions (MIT, the ANTLR pin, 0.1.0 and `v0.1.0`; see the 0.1.0 section) are not decided
here. Slice numbers refer to the [21-Slice route](phases/phase-69/slices.md).

| ID | Chosen rule, rejected options and reason | Scope, next consumers and latest decision points |
| --- | --- | --- |
| D69.01 | Public scope: three public Python execution routes (PostgreSQL rows, MySQL rows, PostgreSQL ADBC), plus public save with source-free re-read (R1), same-source recovery (R2), complete local publication and provisional delivery to the reference cooperative sink. An ordinary query requires no persistent workspace; no CLI command executes against a database; multi-job scheduling and general garbage-collection control stay private this phase. Every public save, read, recovery and delivery flow documents and wires its own resource end, retention responsibility and permitted release path; there is no age-based automatic deletion or general directory cleanup, and the cooperative sink is never described as a side-effect guarantee for arbitrary callbacks. The public read surface also includes D69.10; retirement is D69.08. Rejected: direct queries plus the save layer with the advanced flows kept private, and direct queries only. The reason is this phase's goal and the owner's choice; the Phase82 freeze is not a compelling reason to widen public scope now. | Direct execution S02–S07, save layer S08–S11, advanced flows S12–S14, joint acceptance S18. Public multi-job scheduling and general GC: owner open; the trigger is a real caller plus separate authorization; evaluated at the latest before Phase82 fixes the public API set. CLI database execution: owner open; evaluated at the latest before Phase82 freezes the CLI. |
| D69.02 | Compatibility: all existing public contracts stay; new alpha interfaces may evolve with notes in the public documentation and release notes; no automatic migration. When the actual code-compatibility identity (every pietto `.py` file plus the installed antlr4 runtime) differs from the recorded one, the existing refusals apply (`COMPILED_COMPATIBILITY`, `JOB_COMPATIBILITY`) and the original data stays unchanged; the documentation states the matching old environment needed to keep using old state. The direction of pinning the ANTLR runtime to 4.13.2 for the first release is accepted. Rejected: compatibility across alphas, which would need a separate semantic compatibility identity and bridges. | Fact: the 0.1.0 preview commit `4b87b6a7` pinned `antlr4-python3-runtime==4.13.2` in `pyproject.toml` and `uv.lock`; S16 only re-checks it and completes the new version's readers and installation checks. Compatibility across alphas: owner open; evaluated at the latest before Phase82 freezes the public formats and APIs. |
| D69.03 | Release gate: a GitHub pre-release; no PyPI or TestPyPI upload this phase. The exact accepted wheel and sdist are frozen and published; independent verification builds are allowed, but rebuilt bytes never replace accepted artifacts; GitHub's automatic source archives are reviewed separately from the Python sdist. Rejected: PyPI as the hard gate. | Every release operation needs its own dispatch; this decision authorizes none. 0.1.0 and `v0.1.0` are bound to the 0.1.0 preview bytes and 0.1.1 and `v0.1.1` to the 0.1.1 packaging release, so a Phase69 release, if any, uses a new version and tag: `0.1.2` (2026-10-11, replacing the `0.2.0a1` direction of 2026-10-10). Whether to release and when are decided before S16, with no pre-written no-release fallback, and the owner approves the version policy before S16 (see the 2026-10-11 section below). Release mechanics default to the 0.1.0 precedent: one local build from the committed `git archive` with a pinned build backend, a draft checked before publication, upload with `gh`, no tracked release files. Latest points: who builds the release bytes and where, before S18 starts; whether tracked release files are needed, before S19 starts; credentials and write authority, in S20's own dispatch, since the 0.1.0 authorization does not extend to it. Whether the Phase69 release also goes to PyPI is decided later, at the latest before S20 (2026-10-10), and would amend this rule. |
| D69.04 | License material: the inventory, original texts and necessary notices of third-party license material must be complete. The license text is the owner's choice: MIT, chosen on 2026-10-10 (see the 0.1.0 section; `LICENSE` and PEP 639 metadata since `4b87b6a7`). Descriptions are checked against each actual distribution channel (wheel, sdist, source archive) and its exception clauses, without simplification and without claiming legal confirmation. | Completed with 0.1.0: `THIRD_PARTY_NOTICES.md` by channel; upstream texts at pinned versions with `SOURCES.md` in `LICENSES/`; package smoke compares the license files byte for byte in the wheel, the sdist and the installed distribution. S01 re-checks them on the rebound baseline and inventories new Phase69 material, if any; S16 re-checks the license metadata and updates artifact file names in the notices and README; S17 maintains texts and notices for this phase's changes and adds the remaining cross-check of the notice list against the file tree. A change of the license or of the notice set, or of D69.03, unfreezes the route. |
| D69.05 | Order: JIT predecessor, then the parallelism interlude, then the rebound baseline and the formal Phase69 route-lock publication, then implementation (reaffirmed on 2026-10-09, superseding the earlier reading of "do Phase69 first"). After both predecessors are separately authorized and fully closed, the baseline is rebound and only affected content is recalibrated; the route lock gets one complete review and no new three-round question cycle; new public, trust or budget decisions raised by predecessors are reported together, not chosen. On 2026-10-11 the owner restated this as dependency and publication order: development may run in parallel, integration goes in dependency batches, and a release is inserted only after the owner decides it by functional support. Validation location: Phase69 consumes the authorized Teach development-validation direction without implementing a migration and, once the parallelism interlude closes, adopts its qualified remote-validation and result-acceptance rules; local execution is no longer a geographic hard limit for all validation. | The JIT predecessor and the parallelism interlude are closed (sections above). The 0.1.0 preview, the 0.1.1 packaging release and the defect-fix batch are separately authorized tracks outside Phase69 and do not change this order. This decision authorizes no repository publication beyond the route-lock batch and no release, tag, upload or version change. Execution location and per-domain adoption belong to the [validation runner acceptance rules](spec/validation-runner-acceptance-v1.md); each Slice rereads the runner and acceptance rules in force at its own Gate 0, and persistent-storage positives and the native campaign run only on a runner that meets their premises. |
| D69.06 | Capacity: 21 Slices (raised from 20 on 2026-10-09). The count follows required content and independently verifiable sizes, keeps no empty Slice, need not be filled and authorizes no further automatic increase. Unfreeze counting for S19 (2026-10-10): repairs, rebuilds and affected re-verification inside the same approved target add no Slice automatically but count fully against that Slice's or a separately approved repair and verification budget; actually new independent implementation Slices count against the capacity of 21; no unlimited repair or hidden splitting; required correctness, security and trust gaps are never deferred to keep frozen bytes. Route (2026-10-10): keep 21 Slices and adopt none of the pre-listed trade-offs now; they, merging S16 and S17 included, are candidates only when the stop rule triggers. The stop rule and the pre-listed trade-offs are written in the [route](phases/phase-69/slices.md). | Derived as 21 Slices with no margin: the second-round base of 19, plus the save layer split into S08 and S09 (+1) and the read-only verified export S11 (+1); own-generation retirement sits inside S09 and the identity rule adds no Slice. Numbered S01–S21 without letter suffixes, in milestone groups (experiments S01; direct execution S02–S07; save and read S08–S11; advanced flows S12–S14; integration and release preparation S15–S17; acceptance, freeze and release S18–S20; audit only S21), with each row's dependencies in the [route](phases/phase-69/slices.md). The 0.1.0 preview shrinks S01, S16, S17 and S20, but none of them disappears. Split risk: S14 and S18 high, S08 and S12 medium; any split beyond 21 stops and goes to the owner as a small decision sheet limited to the route's pre-listed trade-offs. The midpoint (after S11) and every unfreeze re-estimate with S/H/L/K/Q. |
| D69.07 | Workspace format of the public flows: v7. A public save always creates a v7 workspace; the format is chosen once at creation, with no upgrade or migration. Capture, recovery and relay run under the private runtime's admission; public flows hold the private coordinator internally and settle crash-left allowance internally, within the narrow exception of D69.09. This is not a public multi-job scheduling API: the coordinator, `open_runtime`, the scheduling policy, the submission queue and collect appear in no supported public export, signature or return interface. One coordinator per workspace at a time; capture, recovery and relay from another process get a typed `RUNTIME_BUSY` without queueing. Coordinator sharing (2026-10-10): S08 decides sharing in an explicit context, with no global singleton by default. Accepted consequences: data operations stop at 262,144−4,096 rows, the last 4,096 rows being shared by all control writes; a window still pending after sink expiry or job termination has no release path (inferred); the public layer derives the coordinator policy from the workspace budget. Rejected: v6, the second-round recommendation; the owner gave no separate reason, and the benefits of v7 listed in that round were complete terminal states and releases within the shared 4,096 rows and a release path for the latest-checkpoint root (D69.08). | S08 and S09 (admission, crash reconcile and `RUNTIME_BUSY`); S12 and S14 (recovery and relay admission); S10, S11 and S13 (v7-specific refusals); S18 (public-surface check). Public multi-job scheduling stays deferred under D69.01. |
| D69.08 | Protection without a release path: publish only retirement of the caller's own unpublished generation. The save flow publishes this retirement by reusing the private `retire_generation`: it removes only that generation's latest-checkpoint root and then refuses new attempts, chunks, ends, retentions and publication for it. No general GC, no file deletion, no release of other flows' protections; retirement is never called space reclamation, and this phase reclaims no space. A caller's own generation is one under a job whose publisher the caller holds; the private layer has no finer caller ownership, so a later publisher of the same job can retire it too. Preconditions: unpublished, not retired, no open attempt; a code-identity mismatch refuses under D69.09. Protections that still have no public release path, stated and accepted: publication-owned retention (permanent) and a window retention still pending after sink expiry or job termination. Rejected: no root release at all, and targeted collection, which deletes files and exceeds the capacity. Reason: it gives the save flow a root-release path and a terminal state for generations without adding a Slice or crossing D69.01's rule that general GC control stays private. | S09 (retirement and its counterexamples); S15 and S17 (wording checks in the API reference and capacity notes: retirement is not space reclamation); S18 (across flows: retirement leaves other flows' protections unchanged, checked by row-set comparison). Space reclamation, meaning any collection that deletes files including a public collect: owner open; the trigger is a real caller plus separate authorization; evaluated at the latest before Phase82 fixes the public API set. |
| D69.09 | Control writes on old state whose code identity differs: always refused, with one narrow exception. When a job's recorded code-compatibility identity differs from the running code, the public layer refuses every control write on it (claiming the publisher, interrupting an attempt, releasing a retention, cancelling, retiring) before any write. Read-only access is limited to qualifying metadata queries: read-only, writing no row or file, needing no publisher, decoding no saved result or bundle, connecting to no source and returning no row data (a REFINED capture's checkpoint descriptor carries per-row coordinates, so it is not metadata). Result re-reads (R1, the read-only verified export, publication reads, delivery and recovery) still require the matching code identity and fresh trust inputs. Consequence: after a Pietto upgrade, releasing, unlocking or retiring an old job's state needs the code identity that registered the job. Narrow exception (2026-10-10), the only exception write under this rule: the legitimate current coordinator, after a real ownership takeover, settles admissions that earlier epochs left unsettled, under the original protocol, including the required coordinator ownership records (the `runtime_owner` row and the admission settlement rows). This is a persistent write and is never described as bookkeeping without writes. It does not claim the old job's publisher, interrupt or cancel an old attempt or job, release retentions, retire generations, delete files, resume execution or accept incompatible results; claimed bytes stay charged, and old attempts and UNKNOWN history stay unchanged. The read-only verified export, status queries (qualifying metadata queries) and requests the identity gate will refuse never trigger reconcile implicitly. Rejected: allowing metadata-only control writes, which would change old workspace metadata, in tension with D69.02's literal requirement that original data stays unchanged. | Counterexamples in S08–S14 (control writes refused first on a mismatch, checked by row-set and byte comparison; S11's result re-read check); S17 compatibility notes (the access layer lists only qualifying metadata queries). This entry is the narrow exception's boundary text. S08 wires it: coordinator open and close with the ownership record; reconcile loops within the boundary until it returns empty; in-process settlement tests; in-process counterexamples showing that status queries and requests the identity gate will refuse do not trigger reconcile (derived order: the identity gate runs before the coordinator opens, and a request it refuses never opens it). S09 accepts it with kill and replacement histories, including an old job with a mismatched code identity: only the `runtime_owner` and admission settlement rows change, while job, generation, attempt, retention and operation rows and file bytes stay unchanged; claimed bytes stay charged; old attempts and UNKNOWN history stay; the old job's publisher is not claimed and nothing is interrupted or cancelled. S11 shows that the export triggers no reconcile; S18 reviews the joint histories. |
| D69.10 | Public read-only retrieval after the operation quota runs out: a public read-only verified export. It reuses the private snapshot read: it reads a saved result (published ones included) at a fixed checkpoint and hands it out as bounded Arrow batches after verifying each member. It is not a degraded R1 mode: it never advances ACK, consumer progress or delivery state, writes no row and uses no budget. It keeps the fixed snapshot, integrity, qualification, trust (matching code identity and fresh trust inputs) and applicable reader protections (the v7 shared lease; members already decided for collection carry a tombstone and refuse with `CHUNK_COLLECTED`). Refusal conditions (decided by the owner on 2026-10-10): job state or an already-retired generation is not by itself a refusal; compatibility, fresh trust, fixed snapshot, member integrity and reader protections stay; members decided for collection, removed or corrupt refuse at the original gates; uncommitted files are never accepted (derived examples: staging names and orphan files outside committed metadata). It never triggers reconcile implicitly (D69.09), and exhausting the operation quota alone does not block a legitimate snapshot read. It widens D69.01's public read surface to R1 plus this export. Rejected: adding nothing this phase and listing the export as deferred. Reason: once the operation quota runs out, R1, delivery and publication refuse while the data is still on disk; the export keeps those results readable through a public path. | S11 (new, +1 Slice, including counterexamples showing that the export opens no coordinator and triggers no reconcile); S15 API reference and effect table; S17 capacity notes; S18 joint acceptance. |

D69.05–D69.10 record the choices of 2026-10-09 and their reasons; D69.02–D69.04 state as facts the parts the 0.1.0 preview completed. The owner also
decided on 2026-10-10 to reuse what 0.1.0 completed (the MIT license, the notices, the ANTLR pin and the release process) and to handle only real
increments and new-artifact acceptance (applied in S01, S16, S17 and S20; derived). Assumptions of the original decision sheets that are not listed here were not
adopted as decisions.

## Phase69 route lock — owner decisions (2026-10-11)

所有者为 Phase69 的 [21 片路线](phases/phase-69/slices.md) 定下按里程碑组的常设授权，不再逐片派发：S01 先合入；S02–S07 与 S01 同属第 1–7 片的授权组，连续进行，
遇 BLOCKER、拆片，或新的公共、信任、预算决定即停；S08–S14 在 S07 之后的现实检查后授权，S15–S19 在中点之后授权；S20 与 S21 各自单独派发。两项决定合读（派生）：
已获授权的组内，检查点只约束合入顺序，不约束开始开发，组内的 Slice 在自身前置问题已答复后即可在隔离 worktree 开发；S08–S14 与 S15–S19 两组本身分别在 S07 之后的现实检查与中点之后才获授权。
合入在路线锁定发布之后，S02–S07 在 S01 之后，按依赖与已发布的批量合入规则进行。`AGENTS.md` 的展开规则相应改为只展开当前授权组内的 Slice；这只改授权措辞，不产生发行权限。

公开 PostgreSQL 执行前提只声明 `schemas`：每次调用绑定已编译查询自己的来源，并检查每个来源的 schema 都已声明，调用方不列来源关系；`schemas` 是调用方的前提声明，不是授权或表级授予，
凭据与 provider 能力都不从环境推断（派生）。早期 PostgreSQL 部署只支持 TCP 加 SCRAM-SHA-256：socket 目录在连接前拒绝；服务器要求 trust、peer、
password、md5 或 GSS 认证时，由 `require_auth=scram-sha-256` 在认证过程中、发送密码之前拒绝；错误说明怎样经 TCP 建立 SCRAM 密码用户；md5 或本机 Unix socket
之类的显式选择，只在真实用户需要时另行决定。新的公开执行错误使用 `PIE-R` 诊断码（所有者 2026-10-10 决定）：新码是可有说明地演进的 alpha 接口，既有 `PIE-P`、
`PIE-S`、`PIE-I`、`PIE-B` 码及其顺序不变；每个新码由引入它的 Slice 写明精确合同（派生）。这些措辞由所属 Slice 写入公开文档。

Phase69 的发行号为 `0.1.2`；`0.1.0` 与 `0.1.1` 都是已发布的历史，不复用。是否发行与时机在 S16 开始前决定，不预写“不发行”的退路；
版本政策由所有者在 S16 开始前批准。本节不授权任何发行、tag、上传或版本变更。

公开 Timestamp/UUID 含义不进 Phase69，归 Phase69 之后插入的一期；Phase69 的 alpha 文档写明项目模式 SQL 生成对含 Timestamp 或 UUID 字段的 shape 报 `PIE-B1004` 的限制。
Phase53 的四个窗口函数族包装、它们的三个 builder 与 family 参数，在 S21 之后另行授权的按功能重组窗口里连同经过它们的测试一起删除，最晚在插入的一期开始之前。binding 层
verifier memo 与测量缺口（容器内数据库服务端 CPU 与内存、worker RSS、时钟差异）由单独派发的 S21 复盘定以后的 owner 与最晚点；调用方提供 CA 的服务器身份校验
与 PostgreSQL rows 的有界读取放到后续期，同样由 Phase69 结束复盘（S21）定 owner 与最晚点。S21 复盘同时写明它们的前提，不实现它们，也不分配预算（派生）。

文件头配置移出源文件：`--check-mode` 与 README、示例和[语言参考](language.md)中文件头的清理是提前步骤，排在 Phase69 的 alpha 文档之前；其余两步归 Phase75（syntax editions
and migrations），在 Phase82 冻结之前完成：先清除仓库其余文件中的文件头并对文件头行发弃用警告，至少一个带警告的版本发布之后再删除文件头语法。语言参考所说文件头行
以后退役，即指这两步；项目模式的严重度设置以后另定。

所有者 2026-10-11 的其余决定不在本节：PostgreSQL 与 MySQL 路线的其余信任设置、alpha 文档的地位与 S02 对 README 的最小更正、S15 的上手示例、按功能重组的时机，
以及本期 Teach 预算，由所属 Slice 的 Gate 1 或仓库外证据记录；Phase69 批次的见证规则写在[路线](phases/phase-69/slices.md)的验证一节。

更正（2026-10-11）：[JIT 一节](#postgresql-refinement-page-jit--owner-decisions-2026-10-10)写的“c3-full01 越线的两页”，指 c3-full01 中越线那次 attempt 的两页：只有
第 2 页越过 10 s 上限并以 57014 取消，第 1 页在上限内返回。该句的数字不变，原文不改；所有者认可在此更正。

取代说明（2026-10-11）：所有者把单文件带点表名的修正并入缺陷修复批次。单文件把连接字符串中的一个点读作 schema.table（PostgreSQL 的 schema、MySQL 的 database），两段分别
加引号；多于一个点或有空段时以确定性诊断失败关闭；单文件 PostgreSQL 与 MySQL 对带点名字的公开输出随之改变。对带点名字，这一决定取代
[Phase66 路线锁定合同](spec/phase66-dialect-sql-emission-product-phase-initiation-gate-route-lock-v1.md)中保留单文件旧解释与旧输出的各条约束：D66.03 的“do not split dotted
text, guess schema/connection or change legacy interpretation”，D66.13 的“Preserve legacy single-file CLI/SQL and existing JSON”，D66.14 的“Keep package0.1.0, legacy formats
and old behavior unchanged …”，以及请求合同（Concrete request, output and state contract）中 legacy single-file `emit-sql` 的默认 text、flags、exit/JSON/SQL“保持原状”
一句。同一批次中所有者另行授权的两项单文件公开输出变化（命名窗口的 SQL 改变；以前能编译的类型不配比较现在失败）同样偏离后三条，也由该授权取代。项目模式不变：namespace
与 name 仍取自 emission 合同，连接字符串不进入 SQL，也不猜 schema 或连接。历史合同原文不改。

## Phase69 parallel implementation extension — owner decision (2026-10-11)

所有者将按依赖并行实施的授权扩展到既定 S01–S21，允许隔离 worktree 开发、就绪片按既有批次规则每片一个普通提交，并以批次最终树的一次权威验证、一次 FF push 与自然 exact-head CI 发布。S07 三路线现实检查、S11 中点以及 S20/S21 独立检查点继续约束集成与验证；新的公开语义、信任和预算决定仍须所有者确认。这取代本日路线锁定记录中只授权 S01–S07 开发、其余组待检查点后授权的措辞。它不授权 tag、GitHub release 或 PyPI 上传。
