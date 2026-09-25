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
