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

Timestamp/UUID meaning仍由Slice07在映射入域前取得upstream witnesses；Arrow roundtrip不补足V05。
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
