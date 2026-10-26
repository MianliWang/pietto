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
| D69.03 | Release gate: a GitHub pre-release and PyPI, as approved by the owner on 2026-10-12; no TestPyPI upload. The owner selected `0.1.2` / `v0.1.2`, superseding the temporary source-`0.1.1` retention and S20/S21 deferral. PyPI credentials remain owner-only hidden local input. The exact accepted wheel and sdist are frozen and published; independent verification builds are allowed, but rebuilt bytes never replace accepted artifacts; GitHub's automatic source archives are reviewed separately from the Python sdist. Rejected: replacing the GitHub pre-release gate with PyPI alone. | Every release operation needs its own dispatch; this decision authorizes none. 0.1.0 and `v0.1.0` are bound to the 0.1.0 preview bytes and 0.1.1 and `v0.1.1` to the 0.1.1 packaging release, the owner has now selected `0.1.2` / `v0.1.2` for Phase69. Earlier on 2026-10-12 the owner temporarily retained source `0.1.1` and deferred S20/S21; the later release authorization supersedes that temporary policy. Existing published `0.1.1` bytes and `v0.1.1` are not replaced. Whether to release and when are decided before S16, with no pre-written no-release fallback, and the owner approves the version policy before S16 (see the 2026-10-11 section below). Release mechanics default to the 0.1.0 precedent: one local build from the committed `git archive` with a pinned build backend, a draft checked before publication, upload with `gh`, no tracked release files. Latest points: who builds the release bytes and where, before S18 starts; whether tracked release files are needed, before S19 starts; credentials and write authority, in S20's own dispatch, since the 0.1.0 authorization does not extend to it. The owner resolved the previously open PyPI choice before S20: the exact accepted distributions also go to PyPI through owner-operated hidden local credential input. |
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

## Phase69 source version retained — owner decision (2026-10-12)

The owner keeps the current source package and CLI at `0.1.1` and will choose
an upgrade after more work. This supersedes the earlier S16 `0.1.2` upgrade
policy. Current source changes and locally built candidate bytes are distinct
from the published PyPI `0.1.1` and `v0.1.1` assets; neither is overwritten.
S15–S19 implementation and qualification continue under the existing scope.
S20 release and S21 post-release completion await the later version and release
decision. No new release or tag is authorized, and Phase69 is not declared
complete from source qualification alone.

## Phase69 release and completion — owner decisions (2026-10-12)

After S01–S19 closed at `9e74aa681133a359ee825b31a9b8573c29932d7c` with natural CI38326554421/push/main/attempt1 and all 19 jobs/36 required consumers accepted, the owner authorized the upgrade and release, then selected **0.1.2** and **GitHub pre-release plus PyPI**. This supersedes the temporary 0.1.1 retention and S20/S21 deferral; the existing 0.1.1 distribution and v0.1.1 assets remain historical bytes.

S20 updates active version and release readers, performs affected validation, accepts one release build from the committed archive, verifies the exact wheel/sdist and their installed/native input closure, and publishes those bytes through a checked GitHub draft and owner-operated PyPI upload. The token is not sent to chat or read/stored by an agent. No signing, attestation, TestPyPI, dependency upgrade, support expansion or product feature is included. S21 follows the actual release with completion, retrospective and handoff only; it assigns future owners and latest decision points without implementing that work or allocating its budget. The route remains 21 Slices.

## Phase69 S21 retrospective — deferred owners (2026-10-12)

S21 closes the earlier delegation of future owners and latest points without implementing or funding them. The [completion audit](phases/phase-69/completion-audit.md#deferred-owner-terminal-ledger) names each current code owner: binding-verifier memo and resource/clock measurement gaps go to Phase81 planning, before any memo, scheduler or worker-policy change; PostgreSQL rows CA identity and bounded reads go to Phase76, at latest before the Phase82 support freeze; the external nullability v2 proposal goes to Phase72 design review before adoption. Public Timestamp/UUID and common expression/function/emission meaning belong to the inserted post-Phase69 phase. Phase53 wrapper/test reorganization remains separately authorized after S21 and before that inserted phase. Native Windows proof is required before any future Windows support claim. These are ownership transfers and retained limits, not new public semantics, implementation grants, costs or automatic phase starts.

## Phase70 Phase Start — owner decisions (2026-10-14)

所有者 2026-10-14 以「按推荐。不过我还是希望你能够用teach 提高效率，并帮我提交PyPI或者把相关命令给我。我来输入token」答复 Phase70 开局闸门 v3，采纳全部推荐（含三个后定项）与许可，并要求本期使用 Teach、由所有者本人输入 PyPI token。
闸门 v4 在这次答复之后修正了 v3 的四处实质内容（D70.02 的 R1/R2 规则、D70.05 的 MySQL IN 加 LIMIT 范围、D70.03 的自相关换名、D70.11 的发行确认方式），并补上 D70.10 的 Teach 额度与清理；所有者以「确认 v4；Teach 12/480，清理同意。」确认了 v4。
下表只记录所有者的选择、放弃的备选与理由；本节的 D70.01–D70.11 是仓库中首次定义的 D70 编号。实现中的名称、诊断码与逐形态行在所属 Slice 的 Gate 1 定稿，并在该片首个公开提交前写入公开文档。
片号指 [20 片路线](phases/phase-70/slices.md)；lead 的可逆内部架构决定记在 [brief](phases/phase-70/brief.md)，外部参考记在[外部参考记录](phases/phase-70/planning-notes.md)，都不是所有者决定。

| ID | 已选规则／放弃的备选与理由 | 范围、下一消费者与最晚决定点 |
| --- | --- | --- |
| D70.01 | 命名值参数在被执行的入口查询头部声明，例如 `query orders_since(cutoff: Int not null, label: Text nullable):`，正文直接用名字；调用新增 `parameters={...}`，按名字给全。名字同时是字段、let 或关系时编译报错，不选赢家；代价是以后上游表新增同名字段时旧查询报错，而不是悄悄改义。只有入口查询能有参数，其局部关系可以引用；带参数的查询不能作为其他查询的输入。首批类型为 Bool、Int、Float、Text（可声明 nullable）。参数不得出现在 LIMIT、窗口范围、要求固定值的函数实参（如 `substr` 的位置、表函数实参）与 VALUES 单元格：这些位置靠固定值做安全证明。依赖参数值的安全检查（如整数溢出）记为绑定时义务写入产物，每次绑定时重推，不合格的值在执行前拒绝。命名参数在 `preserve` 与 `bind-safe` 下都是占位符；产物分别列出命名参数（名字、类型、每次出现的占位位置）与字面量槽；占位符按渲染顺序编号，PostgreSQL 同一参数复用同一个 `$n`，MySQL 每次出现一个 `?`。原 `values=` 含义不变，可以省略（用编译时的字面量），给出时按槽序给全，两份清单可以同时使用。放弃：正文写 `$cutoff`（永不撞名，但多一个符号）；查询体首行的 `param` 声明；查询之间传参（需要关系函数，留给以后）；编译时拒绝需要值才能证明安全的表达式（更保守，但 `cutoff + 1` 这类写法编不过）；本期一并做更多参数类型（需先扩充绑定与线上格式）。 | S01 语法；S04 单块语义、计划、发射、`CompiledQuery` 的未绑定表示与一条路线的 `parameters=`；S11 跨块、bundle 传输以及三条路线与保存流程中的命名绑定。Decimal、Date、Timestamp、UUID 参数类型归 Phase72。 |
| D70.02 | 未绑定模板是封闭的类型化状态，逐操作准入：`check`、`compile_query`（记录绑定时义务）、`emit-sql --project`（以新版本标记输出参数清单与绑定时义务）、inspect/explain、`export_bundle`/`load_bundle` 允许；`execute`、`save`、`relay_live` 必须给全参数，缺值、错型、非法 NULL 在连接数据库之前拒绝。命名绑定在已保存结果中与 `values=` 的现行规则一致（后定项，按推荐）：新建执行或保存（`execute`、`save`、`save_recoverable`）按名字给全，可以用新值；R1 的 `open_saved_read`、`release_saved_read`、`publish_saved_generation`、`verified_export` 与 R2 的 `recover` 每次都重新写出 `parameters=`，且必须与该代次保存的值逐个相等、类型相同（如 `True` 不等于 `1`），否则按现有 `BINDING_VECTOR` 拒绝；保存的绑定含命名参数时此项必填，不含命名参数的现有调用不变。参数的名字、类型与占位位置进绑定描述的新接口版本，参数值与字面量槽的值一起进绑定向量的新版本，NULL 带类型；`save_recoverable` 与 `recover` 只对有坐标基础的形态开放。放弃：本期 R1/R2 拒绝含命名参数的查询。 | S04、S11；S17 联合验收。 |
| D70.03 | 写法 A：命名局部关系加按名引用。局部关系写在查询体开头，只用 `query` 关键字（`table` 与 `query` 今天的子句相同，局部只留一种拼写）；`from x:` 内联派生表是唯一的内联块。表达式中按名引用局部或模块级关系：`customer_id in vip`、`exists recent`；scalar 子查询写成 `scalar grand_total.amount`，用关键字是为了 `grand_total` 将来成为输入时意思不会悄悄改变。VALUES 用类型化表头 `values(id: Int not null, label: Text nullable):` 加每行一条，零行只写表头。表函数写成 `from generate_series(1, 100, 1) as n`，`n` 同时是关系名与唯一列名。相关查询在局部关系里写 `capture customers`，每个外层输入各写一行；capture 进来的外层输入只能用限定名（`customers.id`），不参与裸名查找；把带 capture 的局部关系 JOIN 进来即 LATERAL（`cross join`，或 `inner/left join … on <条件>`，纯 LATERAL 写 `on true`），不加新关键字。同名一律编译报错，局部关系不遮蔽外层或模块级名字：身份法则不允许按"最近"选赢家；代价是以后在模块里新增同名关系时旧查询报错而不是改义。自相关（capture 的绑定名与本块某个输入同名，如 `capture orders` 又 `from orders`）同样报错，须先用一个局部 `query` 给内层换名。新词都是软关键字，现有同名字段与关系照常可用；单段 `scalar r`、`capture a, b`、空参数表 `query q():` 等未列出的写法本期确定拒绝。随之批准的公开诊断变化：新增约 9 个"暂不可用"诊断码，自 `PIE-S2345` 起在 S23xx 段内连续分配，在单文件与旧式平铺项目中长期保留；语法错误消息中"expecting …"的候选词增加，码、顺序与位置不变；现有负例 `query …(parameter: Text):` 变为合法写法。S01 只允许 token 级调整，任何用户可见的拼写变化回到所有者。放弃：写法 B 内联块（更像 SQL，但要改六条子句的换行规则与 QUALIFY 语法，select 与 order by 中的续写行会静默成为新的一项）；局部关系遮蔽模块级名字（需要明确的产品合同）；外层字段参与裸名查找、重名即报错；本期加 `capture orders as outer_orders` 别名写法。 | S01 一次落地全部写法，并以前置准入门挡住未实现的形态；S03/S05 局部与派生关系，S06 VALUES，S07–S10 子查询与 capture，S12/S13 LATERAL，S14 相关组合，S15 表函数。 |
| D70.04 | 结果规则与位置：scalar 子查询只有一列，0 行得 NULL、1 行得值、多行由数据库在执行时报错，不加 LIMIT 1；多行错误沿用 `PIE-R3003`，带数据库给出的 SQLSTATE 21000，不新增错误码（后定项，按推荐）。`exists` 的结果永不为 NULL；`in`/`not in` 子查询沿用字面量列表 `in` 的三值逻辑，`not in` 不改写成 ANTI JOIN。子查询只在 WHERE 与非分组查询的 SELECT 中可用；分组查询的 SELECT（分组后的 SELECT 只接受分组键与聚合输出）与其他子句位置本期确定拒绝。`capture` 只取外层 FROM/JOIN 行上的字段（LEFT JOIN 之后的 NULL 扩展身份保留），不取外层 let、SELECT 输出、聚合或窗口结果，跨两层以上的捕获每层显式写；外层同值的重复行各自得到结果。写出的每个表达式都做完整静态检查（包括未选取的列与 EXISTS 内层的投影），但不承诺数据库是否求值它们；运行时错误之间的先后不作承诺，编译期诊断的码、顺序与位置照旧确定。放弃：编译期要求证明 scalar 至多一行（更保守，可写的形态更少）；允许分组 SELECT 中的非相关子查询（要先定义分组之后的作用域）；新增 scalar 多行专用错误码。 | S07–S10、S12–S14。 |
| D70.05 | 能力宽度：每个新形态都做到公开执行，三条路线逐一支持或明确拒绝；保存后同源恢复（R2）对新形态默认明确拒绝，只有具备坐标基础的形态逐个开放。只有 VALUES 或表函数、没有物理表的查询：PostgreSQL 必须给出非空洞的来源资格（至少核验会话上下文与 `pg_catalog` 前提，资格记录写明没有关系根、函数身份由限定发射固定、未查目录），MySQL 本期拒绝。表函数只做 PostgreSQL `generate_series`：实参是固定的非 NULL 整数，行数有上界；MySQL 不支持。查询级函数的运行时资格（后定项，按推荐）：调用发射为带 schema 的 `pg_catalog.generate_series`，实参显式转成 bigint，函数身份由此固定，不另做运行时目录检查并写入文档；表函数片开工时先在本机按确切发射形状实测一次。IN 读取带 LIMIT 的局部关系：不带 capture 的闭合关系两库都允许，只以顶层 CTE 形状发射，直接的 `IN (… LIMIT …)` 形状永不生成；带 capture 的相关关系含 LIMIT 并被 IN/NOT IN 读取时，MySQL 上确定拒绝，PostgreSQL 允许。放弃：MySQL 用单行哑表承载 VALUES（违反"不用包装绕过限制"）；表函数整个移到 Phase74；按 `pg_catalog` 函数身份逐次做运行时检查；MySQL 上一律拒绝 IN 读取带 LIMIT 的关系。 | 各特性片自带首个真实消费者；S06 零来源接缝；S09；S14；S15；S17 联合验收。 |
| D70.06 | 路线图范围变化：两类窄去相关改写移出本期，归 Phase88（逻辑优化器），形式化改写认证归暂定的 Phase93；Phase70 不做任何改写，effects 证据只放开有界表函数准入所需的部分，UNKNOWN effects 不升格；表函数准入以外的 effects 权威，标量函数的 effects 目录归 Phase74，供改写消费的 effects 归 Phase88。理由：现有 `semi`/`anti join` 已覆盖这类语义，而且本来就发射为相关 `EXISTS`；改写不增加任何可写的查询；两库的小型探针显示相关 EXISTS/NOT EXISTS 已被原生规划为 semi/anti join，改写的执行收益没有测过，本决定不以性能为依据；按[产品架构](architecture/product-architecture-v1.md)，改写搜索与代价属于优化器侧平面，拓扑归 Phase88–89。路线图把"项目有语义错误时只编译所选 owner"列为 Phase69/70 的政策决定，Phase69 未处理：本期保持现行的整项目结果政策不变，移交 Phase75（编辑器部分分析）再定。Future Roadmap v6 中 Phase 70 一行由生命周期读者逐字锁定，保持原文，移交写在该节表格后的说明。放弃：保留窄去相关（22 片、容量 22 时零余量，须同时选一项取舍）。 | 路线 20 片；Phase74、Phase75、Phase88 与 Phase93 开局消费；[路线图](roadmap.md#future-roadmap-v6)。 |
| D70.07 | 数值上限（以后放宽不会破坏已写的程序）：查询块嵌套深度（局部、派生、子查询与 capture 层级合计）16；每个查询的局部关系声明 64；每个入口查询的命名参数 64；单条语句的占位符总数 65,535（两种数据库的协议上限）；每个 VALUES 关系 1,000 行、64 列；`generate_series` 由固定实参算出的行数不超过 1,048,576（与默认 `max_rows` 一致），step 不为 0。 | S03、S04、S05、S06、S15 各自的确定诊断。 |
| D70.08 | 公开产物与已存格式：bundle 可以携带未绑定模板（编译一次、绑定多次）；只新增取值的产物沿用现格式，需要新字段的产物（如含命名参数者）换新版本标记，旧读者明确拒绝；这也适用于项目 check/explain 的 JSON（project JSON v2）：如需暴露局部关系或嵌套来源须换新版本标记，否则保持现有结构。compiled 记录加新种类时提升版本号；保存作业的绑定描述换新接口版本；旧 bundle 与工作区不迁移、不改义。新构造只在显式模块项目（EXPLICIT_MODULES）中提供；单文件、旧式平铺项目（LEGACY_FLAT）与单文件 metadata v1 不变，继续明确拒绝（沿用 Phase64 先例）。包根模式（PACKAGE_ROOT）的 `explain --project` 不分析关系体，沿用 Phase64 先例不加拦截：含新写法的包模块从今天的解析错误变为 explain 成功，这不代表这些关系可用。放弃：bundle 只携带已绑定的查询（更简单，但失去复用模板的主要价值）；在包加载处也加拦截（影响所有包加载的读者，并新增一处公开诊断变化）。 | S03（project JSON 是否暴露嵌套来源）、S04、S11、S16、S17；跨 alpha 兼容仍按 D69.02 在 Phase82 冻结前评估。 |
| D70.09 | 路线与容量：20 片（含发行片 S19 与审计片 S20），容量 22。22 是一次真实扩容：Phase69 的 21 片已含发行与审计，本期新增发行范围，且四个高风险片与两个中高风险片可能需要两处拆分；这不是尺寸证明。余量 2：两处拆分仍在容量内；超过 22 片时停下，出一份只含路线所列取舍的小决策单交所有者，容量不自动增加，一个备用位置不同时承接多处独立拆分。放弃：保持容量 21（余量 1，只容得下一处拆分）。 | [路线](phases/phase-70/slices.md)；中点与每次解冻按 S/H/L/K/Q 重估。 |
| D70.10 | 许可与实施授权：(1) 路线发布为一次只含文档的普通提交、FF push 与自然 exact-head CI；(2) Python 3.13.13 权威验证环境已于 2026-10-14 经授权重建并核验，规范 `.venv` 前后无差异；(3) 本机数据库容器（PostgreSQL 18.6 / MySQL 8.4.12 固定镜像，断网，全部自有清理）：冻结前小实验已于 2026-10-14 经授权完成，此后每个封存候选或批次在 Gate 2 封存前各跑一次仓库规定的检查（新增发射变体的跑两库目标清单；改动执行、模板、compiled 加载或 Arrow 的用确切候选 wheel 跑原生执行族），输入变化后的重跑、S17 联合验收、S18 最终候选与 S19 对正式 wheel 的安装后核验也包括在内，同一时间只跑一个 campaign、单次不超过 2 小时；(4) S01–S20 按依赖并行实施（隔离 worktree），含每片或每批的普通提交、FF push 与自然 exact-head CI，tag 与发行动作只按 D70.11；每片开工前重新绑定 main，遇到新的公开、信任或预算决定即停；(5) 预算，超出任一上限即停：全期累计修复 causal 54、focused 60、diagnostic 30、scope 6（causal 沿用 Phase68 的最终上限，另两项因共享面更多而上调）；权威全量验证与本机数据库检查按每个封存候选或批次一次计，因失败而重跑每次计 1 个 causal，产品代码不变、只因数据库或容器抖动的重跑计 1 个 diagnostic；多 worker 合入的批次在权威运行前先做一次非权威全量预检（每批最多 1 次）；每片 1 个提交、每批 1 次 FF push，自然 CI 失败后的修复子提交每个计 1 个 causal，不重跑 CI。Teach（所有者要求本期使用）：只做非权威预检，不计入也不替代 Gate 2；额度 12 个作业 / 480 核时（每个作业最多 40 核 × 1 小时，同时最多 2 个），优先用于多 worker 批次的全量预检与高风险片合入前的全量回归；存储清理已于 2026-10-14 经所有者同意完成：`pietto-teach/jobs/` 中 2026-10-12 及以前的 59 个作业输出（1,701,526,912 B）先打包到本机并逐文件校验，再从 Teach 删除。放弃：只先授权前十片；本期不使用 Teach。 | 全部 Slice。 |
| D70.11 | 阶段末发行 `0.1.3`（所有者 2026-10-14 提出）：本决定只批准发行方案，沿用 Phase69 先例：S18 的最终候选通过权威验证且自然 CI 全绿后，集成者把实际 HEAD、已接受的 wheel/sdist 字节哈希与发行清单交给所有者，所有者回一句"发行"即授权 tag、GitHub pre-release 与 PyPI 上传，这一步与所有者输入 PyPI token 在同一时刻。内容：版本号与版本读者一次改齐；release notes 写明 `0.1.2` 的 bundle 与保存作业会被拒绝、不迁移；从已提交归档做一次正式构建并接受该 wheel/sdist；GitHub 自动生成的源码归档与 Python sdist 分开审阅；安装后核验按 D70.10 的 (3)；tag `v0.1.3`；GitHub pre-release 先建 draft 核对再发布。PyPI 由所有者本人用自己的 token 上传：集成者准备确切命令与核对清单，所有者在自己的终端运行上传并输入 token；token 不进入对话，不被代理读取或保存。回退：发行后发现缺陷时不覆盖已发字节，PyPI 的 yank 由所有者执行，GitHub pre-release 加说明，修复走 `0.1.4` 并另行授权；版本号用掉后不复用（同一字节上传失败可以重试，字节变了就换号）。不做 TestPyPI、签名、attestation，不顺带升级依赖或加功能。VS Code 扩展 0.1.0 只接受 `0.1.2` wheel 或基线 `9e74aa68` 的指纹，会拒绝 `0.1.3`：扩展跟进归扩展 owner，本期不提供稳定的编辑器 API，release notes 写明这一点。放弃：现在预先授权全部发行动作（到时不再确认）；版本号 `0.2.0`。 | S19 发行，S20 审计核对发行字节；最终字节或版本号变化、内容超出本条或出现新的信任或公开决定时回到所有者。 |

本节不授权 S19 条件成立之前的任何 tag、GitHub release、PyPI 上传或版本变更，也不授权任何改写，不改变 Phase69 与 Phase69 之后插入的一期已发布的决定。

## Phase70 local relations — owner decision (2026-10-14)

所有者以「let 方案，用 let vip: 你的建议很不错」采纳局部关系的新写法，修订 D70.03 中的局部 `query` 声明与内联派生块 `from x:`：
局部关系写作 `let 名字:`，只能写在 table 或 query 体的开头、`from` 之前；多个 let 平级排列，可以互相引用但不成环，不嵌套；
let 的体是一段 FROM 关系体、类型化 VALUES 体或集合运算体；`capture` 只写在 let 体开头，一行一个。派生表一律先用 let 命名再 `from` 它，
不再有内联块。行级 `let:` 子句（写在 `from` 之后、无名字、给出表达式）不变。所有者同日以「允许」同意 table 体中的 let、let 体为 VALUES 或集合运算、
参数头与 VALUES 表头的末尾逗号。代价：本期无法写嵌套相关（一个 let 捕获另一个 let 的行），以后放开不破坏已写的程序。
准入门的临时诊断码相应为 8 个：PIE-S2345 let 关系声明、PIE-S2346 查询头参数、PIE-S2347 VALUES 体、PIE-S2348 scalar 读取、PIE-S2349 EXISTS 引用、
PIE-S2350 IN 引用、PIE-S2351 capture 行、PIE-S2352 表函数 FROM 输入。D70.07 的嵌套深度上限继续约束子查询与 capture 的层级。

## Phase70 repair budget — owner decision (2026-10-14)

所有者以「批准diagnostic额度翻倍，请继续」把 D70.10 的全期累计 diagnostic 上限从 30 提到 60；各片的 diagnostic 片上限相应翻倍。causal、focused 与 scope 上限不变。

## Phase70 scope extension — owner decision (2026-10-14)

所有者核对后续 Phase 没有明确 owner，以「如果没有的话就把slice数目调整为25一口气做了吧。依旧尽可能高并发一步步吧phase70做完」把容量从 22 调到 25，
并把以下能力纳入本期（核查依据：表达式分组键在 Phase43 范围锁中"继续拒绝"、Phase52 写明"需另行授权"，Phase73 的 grouping extensions 不含计算键；
let 列 min/max 与参数在聚合、窗口与结果位置的使用没有 owner）：
- S04r：参数及依赖参数的值可用于 SATISFYING、QUALIFY、经 let/select 建立的 ORDER BY 键，以及对依赖参数的 let 列做 count/avg；
- S04w：窗口函数中的参数，含 lag/lead 偏移量、ntile 分桶数与 nth_value 位置的"结构计数区间"绑定时检查；
- S05g、S05j：let 计算分组键与 let 列 min/max（项目模式；S05j 含 JOIN 输入）。

D70.01 的参数位置相应细化（U1）：LIMIT、窗口范围、要求固定值的函数实参与 VALUES 单元格仍不接受参数；参数头必须写明 `not null` 或 `nullable`（U2）；
撞名集合包括入口查询的 SELECT 输出名与命名窗口名（U3）；参数类型只接受 Bool、Int、Float、Text 四个内建名（U4）。
单文件模式不提供计算分组键，semantic metadata artifact v1 的 `group_keys` 不变。路线为 24 片、容量 25、余量 1（D70.09 修订）。

## Phase70 addendum — owner decisions (2026-10-15)

所有者确认：capture let 的外层 captured input 字段已知时，可从 own FROM 的完成后定型 relation 读取；若 captured outer input 自身的列在 completion 前未知，每个 captured-field read 仍为 `PIE-S2369`。capture let 直接 FROM table function 仍为 `PIE-S2370`，须先经另一 let。

接手时确认的全期累计修复上限为 causal 150、focused 180、diagnostic 180、scope 9。该预算只恢复已授权工作并保留历史超限与 UNKNOWN 的核账；不自动批准新的公开语义，也不授权 S19 或发行。

## Phase70 S19/S20 lifecycle reconciliation (2026-10-15, America/Toronto)

S19 已实际完成并发布：源 head `6ac82d682ea70056ffbecd64a9f53f72491a51c6`、tree `550c1fa0765cb209f3f8438e4b49d5f6329dd24a` 的自然 exact-head CI `38809622132` attempt 1 接受 19 jobs、36 artifacts。GitHub pre-release `v0.1.3`（release `414443229`）和 PyPI `0.1.3` 均已公开核验；正式 wheel SHA-256 为 `15f2a73da34dbf332ae19eebb32aa7e10830ddf46de79169be0bdad5a3e2e06b`，sdist SHA-256 为 `31c06e0b7ab3fe48b4a17ec28ae9b17ec957a4dd433ff5d50385d68f56da449f`。这些是已发生的渠道事实，不改变 D70.11 的发行授权边界，也不重写此前决定。

截至 S19，实际已完成 24 个 Slice；S20 是唯一剩余的审计 Slice。Phase70 仅在 S20 的一笔普通 FF 提交及其自然 exact-head CI 成功后，以 25 个实际 Slice 闭合；该 CI 成功后不再追加收尾文档提交。历史规划图仍为原 20 行路线、24 节点、47 条边；S04r、S04w、S05g、S05j 是授权扩展，S04a/S04b 是原 S04 的实际拆分，不据此改造历史 DAG 指标。

截至 S19 的保守修复核账为 causal 121、focused 107、diagnostic 156、scope 6；当前上限为 causal 225、focused 180、diagnostic 270、scope 9。上限来自接近上限时所有者一次性增加 50%，并保留历史 UNKNOWN 与此前计数，不把本段当作追溯性授权重写。Phase71 仍未开始，须自行通过 phase-initiation gate；本段不授予其实现、预算或产品语义。

## Single-file JOIN MVP — approved scope (2026-10-20)

所有者批准先交付 PostgreSQL 优先的单文件 JOIN MVP。MVP-1 包含七种 JOIN、显式或推断的单步关系匹配、ON、绑定字段与外连接 NULL 语义；MVP-2 增加 GROUP BY、聚合、SATISFYING 和分组排序。当前集成同时包含两组能力；这项范围决定不代表验证、golden 审核或发布已经完成。

每个输入位置有独立身份，自连接不按关系名合并；裸字段须唯一，关系与来源推断保留全部候选，不按最近位置挑选。SEMI/ANTI 的目标只供自己的 ON 读取。LEFT/RIGHT/FULL 引入的 NULL 扩展身份保留，后续 INNER 或 WHERE 不清除它；INNER 自身的有效匹配证据可以收紧此前未被外连接扩展的字段。

聚合采用保守的源键闭包：聚合实参读取的输入与按源声明的非空唯一键分组的输入共同覆盖全部产行因子；INNER/LEFT 关系匹配提供前向键依赖，只有不带 ON 的 INNER 提供反向依赖。RIGHT/FULL、CROSS 与纯 ON 不提供依赖，派生关系不传播键。`count()` 豁免，`min`、`max` 与 `count_distinct` 不豁免。未覆盖时在调用处报 PIE-S2381，并只给出能闭合证明的修复建议；不能用外连接的 NULL 部分证明唯一目标。

PostgreSQL 使用现有单一 SELECT 尾部。SEMI/ANTI 变为 EXISTS/NOT EXISTS，下一次 RIGHT 把待处理过滤放入自己的 ON；仍有过滤待处理的 FULL 拒绝。原生 FULL 只接受两侧 Int 字段相等的 AND 条件。MySQL 按关系报 PIE-B1000 并保留其他产物；单文件 EXPLAIN 继续使用一个输入的 Semantic Metadata Artifact v1，在每个 JOIN 关系报 PIE-I1000，不扩充 JSON。

暂不开放 JOIN 上的窗口、多步 VIA、未知字段集合输入、通过 table/query 的关系匹配、非分组聚合后的 ORDER BY、MySQL JOIN 发射与 JOIN EXPLAIN v2。QUALIFY、DISTINCT、集合、关系 let、LATERAL capture、VALUES、表函数及头参数保持各自既有边界。LEGACY_FLAT、PACKAGE_ROOT、EXPLICIT_MODULES、无 JOIN 输出与显式执行/resource 契约不因本次实现放宽；共享内核提取和项目行为变更需要后续独立授权。

## Phase71 Phase Start — owner decisions (2026-10-25)

所有者 2026-10-25 以「然后这几项批准都全部按照你的推荐来上限 C200/F180/D250/S12，封存前 PG 原生检查允许本机 Docker」答复 Phase71 开局的 P 组详解：P1–P6 与所有者计划 v2 第 12 节的决定 1–3 都按推荐采纳；修复上限由所有者改为 causal 200 / focused 180 / diagnostic 250 / scope 12（推荐值为 185 / 165 / 235 / 9）；封存前的 PostgreSQL 原生检查开出本机 Docker 例外。
计划 v2（24 片）取代 lead 旧的 14 片草案，旧草案中仍有用的内容按 lead 的校准并入，不另立决定。
下表只记录所有者的选择、放弃的备选与理由；本节的 D71.01–D71.11 是仓库中首次定义的 D71 编号。实现中的名称、诊断码、逐字消息与逐形态行在所属 Slice 的 Gate 1 定稿，并在该片首个公开提交前写入公开文档。
片号指 [24 片路线](phases/phase-71/slices.md)；语义契约、支持域与可逆实现选择记在 [brief](phases/phase-71/brief.md)，外部参考、假设与证据缺口记在[规划记录](phases/phase-71/planning-notes.md)，都不是另外的所有者决定。

| ID | 已选规则／放弃的备选与理由 | 范围、下一消费者与最晚决定点 |
| --- | --- | --- |
| D71.01 | Collect 的写法（P1，A）：在 SELECT 中写 `recent_orders = collect last_orders`，与 `exists recent`、`scalar r.latest`、`x in big` 同一类“词加关系名”的读关系写法；`collect` 是上下文词，已有叫 collect 的字段、函数与关系照常解析；括号永远表示调用。0.1.5 中这样写是语法错（`PIE-P1000`），加入它不改变任何已有程序的意思。随写法批准的公开诊断变化：项目中 `collect <let>` 从语法错变为接受；单文件、LEGACY_FLAT 与 PACKAGE_ROOT 中的 `collect`/`unnest` 得到一个说明怎样建 `schema_version = 2` 项目的新诊断；语法错误消息中 expected 候选词可能增加，码、顺序与位置不变；被 `collect` 读的 let 写 ORDER BY/LIMIT 不再报 `PIE-S2370`；`PIE-S2103`、`PIE-P1000`、`PIE-S2370` 的部分消息增加指向新写法的提示。新码自 S01 在绑定基线上确认的空闲码段连续分配。放弃：`list(last_orders)`（像 Python，但 `名字(...)` 要看括号里是字段还是关系才分得清，而且与今天合法的同名用户 `def` 程序冲突，实测）；`collect(last_orders)`（计划 v2 示例；冲突相同，又没有像 Python 的好处）。 | S03 冻结逐字拼写与诊断，冻结前做一次学习者探测（只读，不用 Teach），探测推翻时回到所有者；S04 绑定；`explain` 嵌套类型显示（如 `recent_orders: list[{order_id: Int, total: Decimal}]`）是 S03 的 UX 候选。 |
| D71.02 | Unnest 的写法（P2，A）：先写 `let o = unnest(customers_with_orders.recent_orders)`，再写 `cross join o`、`inner join o on o.total > 10` 或 `left join o on True`，与现行 JOIN 别名 `let buyer = customers` 和 LATERAL 的 `let o = last_orders` 同一个样子；JOIN 必须写种类；`unnest(...)` 的参数必须是前面某个可见 binding 的嵌套字段；语义完全照计划 v2 §6.6。语法上只新增一处：JOIN 前的别名 let 右边可以是 `unnest(...)`，只改语义准入、不改 grammar（推断）；0.1.5 在该位置报 `PIE-S2604`（下一版可能改报别的码）；项目中变为接受，其他模式得到 D71.01 的新诊断。用户自定义了同名 `def unnest` 时怎样区分由 S03 写明（候选规则：右边是 `unnest(<输入>.<字段>)`、没有同名用户 `def`、并且这个 let 恰好是同一段里一个 JOIN 的目标）。放弃：`left join unnest(...) as o on True`（表函数式，读起来像 PostgreSQL，但重新引入 0.1.5 刚退役的 JOIN `as`，与所有者 2026-10-20 “把 as 和 join 分开”的决定相反，还要改 grammar）。 | S03 写法与准入；S05 绑定；S13 公开纵向。Unnest 继承 JOIN 诊断，包括下一版对它们的修正。 |
| D71.03 | 子表顺序（P3）：被 `collect` 读的 let 必须写 `order by`，closed let 也一样；缺少时报确定诊断并给出加法。排序键并列不构成全序：tie 内的顺序与 LIMIT 末位取哪一行都不承诺，文档照计划 v2 写明，并教用户把唯一列放进排序键。父行顺序只由外层 `order by` 决定；Unnest 展开后的行没有顺序。理由：Python 用户会把 list 当成有序；先严后松是兼容的变化，先松后严会让已上线的程序编译失败。放弃：照计划 v2 不强制、没写 `order by` 就是 bag；不强制但给警告。 | S04 诊断；S08 把顺序契约带进收集操作并经 compiled/bundle 保留非输出排序键；S16 组合；以后放宽是兼容变化。 |
| D71.04 | 嵌套结果的含义（计划 v2 决定 1，A）：显式 Collect 收集已完成的关系；保留 bag 重复；零行是 `[]`，不是 `None`；CROSS/INNER/LEFT Unnest 分开；一个 collection 层，允许多个并列子表；计划 v2 第 6 节的作用域、grain、空集/None/NULL 字段、算子准入与一层深度定义随之采纳（含 D71.03 对 §6.5 的收紧）。放弃：B 直接做任意多层、隐式 group capture 与自动 flatten（类型、作用域、优化与聚合代数一起进入，25 片容量没有证据可承诺）。 | S03–S06 语义与计划；执行器不得暗中改变本条含义；多层与嵌套相关的接收 owner 由 S24 指定。 |
| D71.05 | 消费者与支持域（计划 v2 决定 2，A；P4）：只在 EXPLICIT_MODULES（`schema_version = 2`）项目与 PostgreSQL 上开放；`execute()` 经 `postgres_rows`，Arrow/IPC，普通保存，断源 R1 与 `verified_export`，bundle 导出与加载；`postgres_adbc`、MySQL、R2（`save_recoverable`/`recover`）与 sink/relay 对新嵌套形状在任何连接、workspace 访问或外部作用之前确定拒绝，不回退到别的路线；单文件、LEGACY_FLAT 与 PACKAGE_ROOT 中的新写法确定拒绝。现在不切 S17–S19；`0.1.6` 时间更紧时，把 S17–S19 移到 `0.1.7` 是最自然的切口，须由所有者另行决定。放弃：lead 旧草案（两条 PG 路线都开放 `execute()`，保存类一律拒绝）；只做到编译器与 SQL（不达成“真实类型化结果”的使命）；三路线与全部恢复/交付能力一起开放（运输、内存与 effects 的不确定性明显扩大）。 | S12 中点纵向；S17–S19 保存与读取；S20 拒绝复核；ADBC 嵌套归 Phase76、MySQL 嵌套归 Phase77 的开局；拒绝用哪个码与 detail 在各片 Gate 1 定。 |
| D71.06 | 兼容与存储（计划 v2 决定 3，A）：只升级真实受影响的 schema/兼容维度；保留旧平面读者与旧产物；不自动迁移旧 bundle/job；保持顶层行为持久进度单位，优先复用 `pietto.job-workspace.v7`；旧读者遇到新嵌套产物由版本/合同边界拒绝，不误读成 Text、不忽略未知子行；新运行时对历史 bundle/job/IPC 按各自版本、代码身份与 trust 规则逐项接受或拒绝；IPC 外层 framing 是否换版本由字段含义是否变化决定；零行、零 batch 与空子表也携带完整合同。放弃：B 在平面 v1 里塞入开放 JSON/Any（含义与验证边界失真）；C 直接引入子行 checkpoint、独立 ACK 与 workspace v8（扩大持久协议，没有必要性证据）。 | S07、S09、S17、S18、S19；跨 alpha 兼容仍按 D69.02 在 Phase82 冻结前评估。 |
| D71.07 | 实验先行与资源界限：S02 实测 PostgreSQL carrier（优先受控文本 carrier 加 schema 指导的严格 decoder，位置化 row array 是候选）、精度、内存与大小边界及保存可行性，并以“前提—证据来源—核实时点—适用范围/有效期”表锁定可证明的准入域；JSON 可以出现在 SQL 内部，但不得从第一行推型、不得经 driver 转成 Python float、不得以 key 代替 field occurrence、不得丢失 signed zero、Decimal scale 或 Timestamp 微秒。资源界限的起点假设：行数上限只数父行，`batch_rows`、`max_rows` 含义不变；子行计入字节上限（默认每批 1 MiB）；每次执行最多 1,048,576 个子行；一个父行的列表放不进一批时整批拒绝，不拆行。保护性 LIMIT 不得静默加入源程序。只有常量输入可行时回到所有者做范围决定，不以玩具正例宣告终态完成。 | S02 结束前冻结 carrier 编码；S10、S12、S20 消费；改变这些假设的 S02 结论在 S02 记录中替换本条起点，不另立所有者决定，除非改变终态。 |
| D71.08 | `pietto fmt`（P5）：维持所有者 2026-10-17 的决定，作为 Phase71 之后、Phase72 之前的一个独立步骤，不占 Phase71 容量；Future Roadmap v6 中 Phase 75 一行不改（LSP、编辑器接入、syntax editions 与迁移仍在 Phase75 与扩展 owner），这一步写在路线图表格后的说明里。它只新增命令，不改已有语法、SQL 与诊断；解析失败的文件、注释保留（词法器今天丢弃注释）与等价写法是否统一，在这一步自己的开局定。放弃：并入 Phase75（用户多等三期，72–74 的新写法没有统一样子）。 | Phase71 的 S24 交接；这一步开工仍需自己的派发与开局闸门。 |
| D71.09 | 路线、容量与实施授权（P6）：计划 v2 的 24 片加 1 个未分配位置，容量 25；超过时按路线的停止规则回到所有者，容量不自动增加。现在授权 S02 的 PostgreSQL carrier 实验在 Teach 上运行、先于 S01：只读、在仓库之外、一次性 PostgreSQL 18.6、确切的 `psycopg[binary]==3.3.5` 与 `pyarrow==26.0.0`、自己清理、不写仓库、不提交，结果只作证据，S02 整片验收仍依赖 S01。S01 在下一版（`0.1.6`）各项合成为一个候选之后开始，并绑定该候选而不是 main。路线发布后 S01–S24 按依赖并行实施（一个主集成者、至多 3 个隔离 worker）：每片一个普通提交，按批次规则一次权威验证、一次 FF push 与自然 exact-head CI；自然 CI 失败的头保留，以子提交修复，不重跑。不在本授权内：本路线发布提交本身（先给所有者看过再提交）；`0.1.6` 的版本、tag、GitHub release 与 PyPI 上传（所有者 2026-10-25 的打包决定：`0.1.6` = 下一版各项 + 外部评审缺口 + Phase71）。 | 全部 Slice；中点与每次解冻按 S/H/L/K/Q 重估；S23 准备发行决策材料。 |
| D71.10 | 预算与验证主机（P6）：(1) 全期累计修复上限 causal 200 / focused 180 / diagnostic 250 / scope 12，超出任一项即停；计法沿用 D70.10 (5) 与 Phase70 预算账本的口径，不继承 Phase70 的余额。(2) Teach 本期单独记账 500 jobs / 2,000 core-h，同时最多 16 个作业，S02 实验计入；只做非权威预检与实验，温和流量。(3) S03 之前单独派发一次 runner acceptance，让 Teach 可以承担权威验证的静态检查与大部分 pytest；集成主机每次仍跑独立收集、约 464 个需要本机前提的补跑与 accept 核验，生成文件、golden、打包、Docker/原生与安装后检查照旧在本机；设计稿的 Q1、Q2 到派发时由所有者回答；新规则在该改动的自然 CI 成功后才生效，此前只有集成主机合格。放弃：推荐的 C185/F165/D235/S9（所有者改为更宽的上限）；lead 早先的 C215/F190/D275/S10（基数不一致）。 | 全部 Slice；接近上限时停下请所有者决定；runner acceptance 是单独派发，不是编号 Slice。 |
| D71.11 | 封存前 PostgreSQL 原生检查的本机 Docker 例外：仓库要求新增发射变体的片在 Gate 2 封存前对候选树跑完整 PG 目标清单、改动执行、模板、compiled 加载或 Arrow 的片用确切候选 wheel 跑原生执行族；这些检查与当前“本机不跑数据库”的工作规则冲突，所有者按 D70.10 (3) 的方式开例外：固定镜像、断网、自有清理，同一时间只跑一个，每次不超过 2 小时；输入变化后的重跑、S21 联合核对与 S23 的安装后核验也包括在内。放弃：改规则让这些检查在 Teach 上跑（需要另一次尚未设计的规则改动）。 | S08、S10–S21、S23；runner acceptance 不改变本条。 |

本节不授权 tag、GitHub release、PyPI 上传或版本变更，不授权任何改写，也不改变 Phase70 与此前已发布的决定。
