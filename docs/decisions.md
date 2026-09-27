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
