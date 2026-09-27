# Phase67 Slice10：Ownership 与 CPU Arrow C interoperability

ACTIVE dispatch已授权完整实现/验证/ordinary publication/raw闭合。基线 `eb7fbcc94ea872210380b64bd1e445f799aed7d0`，tree `6e2f4b7ec5e603a0ea395ba39a2263e4541b4da7`，parent `f2a7d75f38e7770db7af3d0b3375f8d9954256a5`，natural CI36299384053/attempt1 success。core仍Arrow-free3.13.13；两owned环境使用hash-verified PyArrow25.0.1 wheels，无下载/升级。

## Q1 接口和责任

一个private `project_arrow_interop.py` owner。`manage_batch(binding, batch, *, lease=None, limits=BatchLimits())`默认owned copy；`BorrowLease(source, binding, owner, non_mutation)`显式exact source/binding、非None owner和exact True承诺才允许借用。`build_managed_batch(binding, rows, ...)`仅复用实际row builder的新鲜owned结果；无caller owned=True/trusted flag。`ManagedBatch`提供schema/C schema/C array/transfer/close/context；`BatchTransfer`一次grant，未调用的request拒绝不消耗data，实际handoff开始即spent，成功/失败/不确定均不重放。live batch可显式发出新的capsules。

| 责任 | 接受点／保持／终点 |
| --- | --- |
| caller | 提供真实binding、稳定CPU carrier；接受前失败保留caller责任 |
| owned batch | 先核验source再逐buffer复制bytes；保留原offset/null布局/UUID storage，再核验delivery；与外部mutable backing独立 |
| borrowed batch | no-copy重包原buffers；Python `__buffer__` exporter强持原buffer、lease及原owner，native consumer持ArrowBuffer从而真实pin owner；commitment延伸至所有消费者释放 |
| data transfer | C handle释放义务单次交SDK；不等于exclusive buffer ownership，SDK destructor负责release，无手工native回调 |
| managed stream | 接受fresh OPEN/pulls0 S09 session后独占pull token；显式context/finally负责bridge及原reader关闭一次；SDK consumer必须在session生存期内消费 |

owned复制所有finite validity/value/offset/data buffers，保留slice offset，不通过Python scalar/float roundtrip或cast修复输入。borrow用Python3.12+ buffer protocol，不调用integer-pointer或foreign-buffer地址构造API；观察地址仅用于测试共享判定。lease冻结source/binding/owner/commitment，删字段、foreign lease或改策略拒绝。已经发出的native handles独立持有buffers/原owner，exporter close不使数组失效；holding owner不能阻止alias mutation，负例明确展示限制。

`import_batch(binding, provider, ...)`只接受明确CPU array protocol provider，经SDK `pa.record_batch`消费并核对真实CPU/schema/domain/resources，默认再owned copy。`import_stream(binding, provider, *, expected_rows, limits, lease=None)`只接受CPU stream provider，经SDK导入后建立新的S09 expectation/session，再交managed owner；不能继承外部completion。device-only hooks在调用前拒绝；cooperative Python/native pointers不是sandbox，坏例只用SDK合法capsules或Python wrong-shape returns。

## Schema requests、stream与资源

真实 `__arrow_c_schema__`、`__arrow_c_array__`、`__arrow_c_stream__`，消费者使用pa.schema/pa.record_batch/RecordBatchReader.from_stream。request None或exact equivalent frozen schema才接受；借助已实测pinned `Schema._import_from_c_capsule`检查request，无best-effort cast。Int/Text/Decimal p/s/TS unit/tz/UUID extension/labels/nullability/metadata任何不等在data handoff或pull前拒绝。top-level C struct只是RecordBatch传输容器，不开放Pietto nested/Struct。

reader新增private单consumer grant/pull入口，公开direct read在grant后返回READER_CLAIMED，原S09调用保持不变；共用原binding snapshot检查。managed bridge每一chunk都通过S09，保持batch/empty/NULL/positional顺序，不导出unchecked source、不Table/read_all/coalesce。bridge iterator只弱引用session，不假定foreign close传播；session必须活到foreign消费结束。normal EOF、early close、primary/cleanup失败与source-complete/downstream-failed分别记录。输入completion沿用S09独立checker，不另建completion体系；nested StopIteration/bridge错误不变成EOF。GC只作best-effort后备，确定性错误由显式close/context报告。

两runtime小premise均通过：真实schema/array/stream capsule、消费后ArrowInvalid拒绝replay、grant无预读、buffer exporter对owner的保活与最终释放。foreign reader.close和source.close都未执行generator finally；只有显式generator.close执行。因此桥使用受控iterator与显式session cleanup，不依赖generator close传播。PyArrow到PyArrow不是独立C实现认证。

batch64fields/4096rows/8MiB、label/codec limits及S09 1024批/1048576行/64MiB保留。source先按C=max(A,R)验证/计费；delivery独立约束，每chunk interop charge=max(Csource,Cdelivery)后累计，不能先compact规避sourceR。source usage直接消费S09实际validated descriptor，不重复full scan取同一usage；owned新结果独立check。临时source+copy referenced bytes另记，不作为RSS。只持current数据及bounded primitive descriptors；单次provider/pull内部阻塞分配不受这些保证。

## Witness、读者与write freeze

复用S08/S09双target13字段mixed/nullable与独立bits/coefficients/ticks/UTF8/UUID oracle。保留74/72/9SDK/22完整documents，新增下面10组和10个实质damage controls，最终84/82。实际origins测量；22份全文跨final local/CI两runtime比较，不新增ownership wire字段。

- `ownership_copy`
- `ownership_borrow`
- `ownership_transfer`
- `c_schema_array`
- `c_schema_requests`
- `c_stream_values`
- `c_stream_terminal`
- `c_protocol_lifetime`
- `cpu_protocol_resources`
- `interop_correspondence`

每组包含实际schema/values、buffer独立或共享、lease弱引用/lifetime、read/close/transfer状态和计费，不以PASS flag替代。正常/失败/early/abandoned handles分别见证；late read为真实SDK iterable，稀有copy/cleanup/control错误明确标test injection。request mismatch先于spent/pull，replay保持spent；same-count/same-label替换由原值oracle识别。

冻结17路径，新增3，无删除。S09 principal仅为grant兼容reserve；未使用第四helper。新runtime records不进入neutral/emission图，无CUTOFF修改。PRODUCTS/actual report checker及末端84/82同步；ci_validation既有required消费无需改接线。typing231/506。actual文档scanner仍是test_phase12_order_by/test_phase12_limit；sole lifecycle reader同步opening/表/active段。

```text
src/pietto/_project/project_arrow_interop.py
tests/test_phase67_slice10_arrow_ownership_interop.py
docs/phases/phase-67/slice-10.md
src/pietto/_project/project_arrow_result.py
src/pietto/_project/project_result_reader.py
tests/_pietto_phase67_result_product_probe.py
tests/test_phase67_slice9_finite_reader_completion.py
tests/test_active_phase_lifecycle.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
docs/phases/phase-67/brief.md
docs/phases/phase-67/slices.md
docs/phases/phase-67/planning-notes.md
docs/decisions.md
docs/development.md
docs/status.md
docs/roadmap.md
docs/references/engineering-lessons.md
```

## 执行与预算

diagnostics6/focused12/corrections8/full默认1最多2/review1+followup1/Q≤3通常2/env2/product每runtime最大4含premise并预留final/SDK final各1/ordinary commit与FF push各1/failed-CI child-push-delta各1/native≤4通常3/docs-only partial≤1严格dispatch条件。agents/detached/concurrent downloads/local DB/full3.12/extra matrix/manual CI均0。所有重命令guard on、top-level串行、≤4workers，uv绑定core。

一次author/Ponytail review冻结finding集、单批repair及targeted followup，先actual doc/lifecycle/typing/report读者，再depth-one和一次完整3.13 equivalent（5static、独立U、4 fresh serial partitions、coverage/managed/health、generated/golden/package、双runtime最终wheel/SDK/product）。同tree seal/ordinary publication/natural15jobs；可在foreground观察中串行提早下载已上传raw，最终仍核对完整required inventory。current raw字节/IDs/context、实际consumers/22全文与fresh普通native pair三strict闭合才完成。

四个broad wall spans保留于ledger；初始read start未计时则unknown，其余从Q1起前瞻计时，mixed/full/CI/transfer嵌套不相加。只清理当前owned disposable roots。S11 general ingress、S12IPC、S13extra、S14producer、S15assurance、S16closeout未开始；Phase68执行/事务/取消/backpressure，69alpha、83stable、90Rust保留。最终Phase67 ACTIVE/N67=16、S01–10 published、S11 NEXT、12–16 NOT STARTED，0.1.0不变。

冻结用途补充：S09 principal还直接读取当前CASES数量及reader groups位置；首次focused揭示旧74断言，已在同一冻结路径内机械更新为84及精确保留reader十组区间。未扩路径/预算，原失败保留。

SDK表示细化：C importer对canonical UUID消费extension metadata后保留空map `{}`，原schema为None；新protocol oracle记录真实空map，不抹去观测。既有schema.equals(check_metadata=True)的空metadata等价规则及非空metadata拒绝保持；owned source/copy内部原schema仍不变。该差异不属于value复制失败。

Q2/review：完整主作者审查冻结原primary/control跨C ABI保留、fresh-owned mutable buffer再验证、stream lease释放及delivery主导累计费用三项，单批修复后做一次targeted follow-up。C consumer的SDK异常表示与session原始原因分别记录；context保留原原因。临时source+copy引用量不冒充RSS。后续保持同tree full/publication/raw义务。

Targeted follow-up补充：Python copy不能克隆同一data grant或stream session授权；绑定原wrapper身份，复制体的析构/close也不能关闭原reader。该C8修复在原owner/冻结路径内，保留累计预算；可变buffer注入见证使用unsigned-byte view，避免测试自身signed/unsigned结构不匹配。
