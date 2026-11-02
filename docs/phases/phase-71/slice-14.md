# Phase71 Slice14: Float and Decimal collected leaves

发布状态：`COMPLETED / PUBLISHED`（main 的 B5 批次）。批次 head
`305ab2c802258c2b3e932ccf236481dfc0e0034e`，tree
`6e335432490b8c7a64501519376c6dbfa59ec3cd`；自然 CI `41390632023`
attempt 1 的 19 个 job 均成功。
以下保留实施时的候选与检查记录；其中的待验证文字属于封存前时点。

封存前记录：candidate，未验证、未发布。本记录在 B4 已发布 tree 上描述 B5 的私有候选；不是 Gate 2 seal、原生运行或自然 CI 结论。

S14 只扩展 PostgreSQL `postgres_rows` collection carrier 的 child-leaf 域为 `Float` 与 `Decimal`。运行时
`CHILD_KINDS`、S13 source emission、compiled verifier 与 compiled lowering 各自显式同步这一集合；它们不是仅靠
一个 runtime allowlist 间接打开。ADBC、MySQL、保存、R1、R2 与 relay 不开放。嵌套 IPC framing/offset 与兼容边界已由 Phase71 S17 交付，本片不新增 IPC 协议。

## Carrier and value law

- `pg_float8[]` 的 OID 是 `1022`；child 值必须是有限 binary64 `float`。Arrow 保留 `float64` 的原始位，含 signed zero。
- `pg_numeric[]` 的 OID 是 `1231`；child Decimal 保留 verified precision/scale，precision `<= 38` 用 `decimal128`，否则用 `decimal256`。输入和读取均按 unscaled value 与 fixed scale 验证，不读取或改变 Decimal context。
- Arrow child 没有 adaptation request：Int width、Text offset、Decimal width 与 UUID representation 都由 verified child observation 推导。计量按实际 Decimal 16/32-byte 宽度，不再按通用八字节估计。
- S12 source-bound `DataRow` 上界把 Float 固定为 24 个字符；Decimal 从 source field 的 verified precision/scale 推导为 `precision + sign + optional decimal point`。未证明的 Decimal fact 在 carrier 前拒绝。
- 按 S02 已记录的 PostgreSQL 18.6 text-carrier 基准，会话固定并在同一 owned connection 核实 `extra_float_digits=1`；它避免该基准已证实的 Float text rounding/overflow，并作为 19-cell context receipt 被核验。

## Boundaries and witnesses

`tests/test_results_nested_relations.py` 使用真实 Collect output 与独立 psycopg-shaped metadata oracle，检查 live/stored binding 与 array OID。`tests/_pietto_results_nested.py` 的 installed-product group `nested_extended_scalar_leaves` 核对 Float negative-zero 原始 bytes、Decimal unscaled `-1250` / scale 2，以及 decimal128/256 的实际宽度与 child charge。`tests/test_execution_nested_relations_admission.py` 证明扩大后的完整 child set 在连接前通过准入。

这些 focused witnesses 不代替真实 PostgreSQL、exact candidate wheel、Gate 2 或自然 exact-head CI。S15 才扩大 Date、Timestamp、UUID，并复核其 raw-buffer offset/meaning 边界。
