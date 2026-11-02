# Phase71 Slice15: Date, Timestamp and UUID collected leaves

状态：candidate，未验证、未发布。本记录建立于本 lane 的 S14 candidate；不是 Gate 2 seal、原生运行或自然 CI 结论。

S15 将 PostgreSQL `postgres_rows` collection carrier 的 child-leaf 域扩展为 `Date`、`Timestamp` 与 `UUID`。运行时
`CHILD_KINDS`、S13 source emission、compiled verifier 与 compiled lowering 都显式扩展为完整八类 leaf；source-free
loader 重新核对该 typed record。ADBC、MySQL、保存、R1、R2 与 relay 仍关闭。嵌套 IPC framing/offset 与兼容边界已由 Phase71 S17 交付，本片不新增 IPC 协议。

## Carrier and value law

- array OID 固定为 `pg_date[]`/`1182`、`pg_timestamp[]`/`1115`、`pg_uuid[]`/`2951`。
- Arrow child 类型固定为 `date32`、timezone-free `timestamp[us]` 与 `arrow.uuid`。Date 仅接受 1000-01-01 到 9999-12-31；Timestamp 仅接受 civil microseconds、无 timezone、`fold == 0` 的既有边界；UUID 是精确 16 bytes。
- Timestamp 和 UUID batch verification 从 raw buffer 读取，并以每个 array 的实际 offset 定位；它不经 Python conversion 读取相邻 poison slot。Date conversion 的 overflow 归为 `ARROW_BATCH`。
- S12 source preflight DataRow 上界分别是 Date 12、Timestamp 28、UUID 38；它们是受控 PostgreSQL text-carrier 上界，而不是新的标量语义。
- 按 S02 已记录的同一 PostgreSQL text-carrier 基准，会话固定并核实 `DateStyle=ISO,MDY`（服务端回读 `ISO, MDY`）；它与 `extra_float_digits=1` 同在 19-cell context receipt 中核验，且不开放 ADBC nested 路线。

## Witnesses and remaining validation

`tests/test_results_nested_relations.py` 保留真实 Collect output、live/stored binding 与 OID metadata 的边界检查。`tests/_pietto_results_nested.py` 的 installed-product group `nested_extended_scalar_leaves` 使用非零 list/struct/leaf offsets 核验 Date、Timestamp、UUID 的原值与 raw buffer，前后 poison Timestamp slot 不可被读取；它与 Float/Decimal 共用安装包检查。

这些 focused witnesses 不代替 PostgreSQL 原生、exact candidate wheel、Gate 2 或自然 CI 证据。
