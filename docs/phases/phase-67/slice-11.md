# Phase67 Slice11：Positional rows 与 Arrow-native ingress

ACTIVE dispatch授权完整实现、验证、普通commit/FF push和自然CI闭合。基线 `f7a4ed89ef628da4da9fb309a23e40d0b67aa282`，tree `3fe9cc4bb2394db0ccf6b337adf4cd8dc4b056d3`，parent `eb7fbcc94ea872210380b64bd1e445f799aed7d0`；natural CI36306958433/attempt1 success。core Arrow-free3.13.13，SDK限原hash-verified25.0.1，两owned运行时。

## Q1：三个入口与接受责任

`project_result_ingress.py`是inert private owner，`__all__=()`。`ingest_rows(binding, rows, *, limits=BatchLimits()) -> ManagedBatch`直接别名现有`build_managed_batch`，`ingest_batch(binding, batch, *, lease=None, limits=BatchLimits()) -> ManagedBatch`直接别名`manage_batch`。`ingest_reader(binding, source, *, expected_rows, limits=FiniteReaderLimits(), lease=None) -> ManagedStream`先capture真实binding和指向原raw reader的lease，再直接建立S09 session并由S10初始化/claim；不经capsule导出再导入。

rows只接受原exact list/tuple与full positional arity，producer carrier严格检查，实际fresh-owned builder不再复制。batch只接受真实CPU RecordBatch，原source先schema/dimensions/retained/full/domain检查，再默认独立buffer copy及delivery检查，或exact source/binding/owner/True lease共享；不从Arrow logical values绕回producer rows。reader只接受fresh/exclusive real RecordBatchReader，所有拒绝在接受前不pull/close，caller保留handle；S09接受后的composition/claim失败关闭accepted session一次并保留primary/cleanup。原lease不改指向hidden session，共用S10 capture及最小accepted-session helper，显式provider仍走原import_batch/import_stream。

不存在Table、ChunkedArray、duck conversion、dict/name匹配、generator、IPC、raw pointer fallback或scalar coercion。binding/meaning/policy authority不能由schema/labels/value推断。单batch没有finite completion。schema inspection/construction无预读；每个chunk（含empty）保留并通过原checker，正常EOF+exact原extent+successful source close才完成。input completion与delivery/cleanup终态独立，context/finally负责确定性清理，foreign release不足以完成；copied/competing grants不能制造authority。保留原primary/control与ABI representation区分。

## 有限证据与资源

落实[brief](brief.md) A09/A12及A15 ingress部分，继承[S09](slice-09.md)与[S10](slice-10.md)。两target混合13字段覆盖七kind/12physical choices、重复carrier labels按ordinal、NULL/empty/firstNULL、signed zero、exact UTF8/Decimal coefficient/timestamp ticks/UUID bytes。MySQL rows Bool是int0/1而native是bool；Timestamp rows为naive civil datetime、native ticks；PG UUID rows为UUID，MySQL为bytes；Decimal保留declared scale/precision且无float/context rounding。

| 新组 | 独立观测与拒绝 |
| --- | --- |
| ingress_rows | real source→binding→rows→actual consumer，四种state、actual fresh storage及arity/type拒绝 |
| ingress_batch | 独立SDK原生构造，mixed/NULL/absent/sliced，default copy及原carrier失败先于copy |
| ingress_reader | 直接raw reader无预读、normal/empty/trailing-empty/uneven、extent与边界 |
| ingress_parity | rows/batch/raw reader/原CPU array与stream各fresh source，比对同一独立ordinal原值 |
| ingress_refusals | foreign authority、extent、wrong route/schema/metadata/nullability、fake/device hooks零调用 |
| ingress_ownership | exact lease、actual pin、接受前caller与接受后cleanup、early/late/control/error、copied/competing grants |
| ingress_resources | 每layout exact/under、retained先于invalid/copy、delivery累计、empty cap与不同合法cost |
| ingress_independence | common-checker注入确实到达，domain-valid substitution/swap/lostduplicate/changed delegate被原值oracle拒绝，22全文保持 |

原84groups/82damage及9SDK全保留，新增八组/八实质damage，末端严格92/90；actual required report consumer、PRODUCTS、S09/S10 direct principals与typing/lifecycle同步。expectations不调用product builder/copier/mapper。完整22中立documents跨最终local3.12/3.13及downloadedCI3.12/3.13比较，route/ownership/extent不入neutral格式。原值oracle是correspondence而非provenance认证。

资源保持64fields/4096rows/8MiB每batch，1024batches/1048576rows/64MiB每session及既有label/codec ceiling，只可收紧。Csource=max(A,R)，delivery累计sum(max(Csource,Cdelivery))，reuse实际validated usage；source+copy temporary references另记，均非RSS保证。合法slice/null布局和chunking的bytes可不同，不以nbytes替代R、不compact掩盖invalid source、不unbounded materialize。

## 路径、预算与终态

Q1冻结19路径，最多28、新增3、删除0；两个既有scalar/reader owner仅reserve窄integration，共用现有机制足够则不改。

```text
src/pietto/_project/project_result_ingress.py
tests/test_phase67_slice11_result_ingress.py
docs/phases/phase-67/slice-11.md
src/pietto/_project/project_arrow_interop.py
src/pietto/_project/project_result_reader.py
src/pietto/_project/project_arrow_result.py
tests/_pietto_phase67_result_product_probe.py
tests/test_phase67_slice9_finite_reader_completion.py
tests/test_phase67_slice10_arrow_ownership_interop.py
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

diagnostics6/focused12/corrections8/full默认1最多2/review1+followup1/Q最多3通常2/env2/product每runtime3且预留final/SDKfinal各1/commit与FFpush各1/failed-CI child-push-delta各1/native最多4通常3/docs-only partial最多1严格原dispatch条件。agents/detached/simultaneous downloads/local DB/full3.12/extra matrix/manualCI均0。heavy guard on/串行/最多4workers，uv显式绑定core；不增加S10 premise allowance。

一次完整author/Ponytail审查冻结finding集，bounded一批repair，一次targeted followup；actual读者、depth-one先于一次full3.13 equivalent。五static、独立U、四serial fresh partitions、exact coverage/managed/health、generated/golden/package和两runtime最终wheel/SDK/product。seal同tree，ordinary sole-parent commit/FF push，自然push/main/attempt1当前15jobs及requiredsteps成功。foreground串行raw prefetch复用仍须最终inventory/head/run/attempt/digest/length/context闭合；fresh独立inode普通native pair、33MiB上限、三条预检argv及三strict sequential。

外部唯一ledger/meaningfulJSONL/中文报告保存failures/logs/wheels/raw/native/scripts，只清理登记disposable roots。read/freeze首次读前未记录起点，如实unknown；其余三broad spans前瞻记录，full独立interval但可能nested，monotonic command union/CI execution/runner sum/observation/prefetch分列。S10混合window不作为速度基线。

同tree local/CI/raw/native闭环后：Phase67 ACTIVE/N67=16，Slices01–11 COMPLETED/PUBLISHED，Slice12 NEXT/NOT STARTED，13–16 NOT STARTED；Phase66/InterludeV/R1完成，package/CLI0.1.0不变。S12 IPC、S13 extra、S14 producer、S15 assurance、S16 closeout不提前实现；provider/nativepointer/prior unseen consumption/concurrency/aliasmutation仍属cooperative前提。

Q2审查冻结一个新入口见证补强组：raw reader实际copy isolation、接受后claim失败、原lease变更先于pull、control跨ABI原身份、五route实际坏值、retained-first raw reader与device-only零fallback。单批修复只扩现有八组及独立exact oracle；production保持两个别名和最小组合，无第二轮一般审查。
