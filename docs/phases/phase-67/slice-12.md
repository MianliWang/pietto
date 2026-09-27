# Phase67 Slice12：有界 private IPC

当前合同及续行授权为唯一产品边界。保留原ledger与旧候选 `c1bb0f895b4c76c3772443617a38972790ce3173`、旧full16674 passes及review的历史身份；它们只验证旧32+56/80MiB合同，不构成本次验收。published baseline `1d19c64c88b4e01074ade5985e556780c848b91e`，tree `08395a6d0d7c1a281bef64c0de844a36cc273776`，S11 natural CI36312935619/push/main/attempt1/success。

## Q3 接口与固定frame

`project_result_ipc.py`保持lazy Arrow和空`__all__`。`IPCLimits(max_bytes=96*1024*1024)`为exact非负int且只可收紧；`encode_ipc(binding, source, *, expected_rows, reader_limits=FiniteReaderLimits(), ipc_limits=IPCLimits()) -> bytes`；`open_ipc(binding, frame, *, expected_rows, reader_limits=FiniteReaderLimits(), ipc_limits=IPCLimits()) -> IPCStream`；`verify_ipc_completion(session) -> FiniteCompletion`返回原S09对象。

header为`struct.Struct(">12sQQQ32s32s")`，恰100bytes：`b"PIETTO-IPC1\x00"`、uint64 rows、uint64 batches、uint64 payload bytes、32raw canonical-contract SHA-256、32raw payload SHA-256，随后仅一个Arrow stream payload。无trailer/flags/padding/JSON/nested envelope/trailing bytes。合同digest来自caller live contract及verification经原S03 exporter的`pietto.result-contract.v1`完整canonical bytes；不从digest恢复runtime authority，不改变22份neutral文档。

encode先verify live binding，再由S11接受fresh raw reader，S10独占checked pull与owned delivery保留每个chunk（含empty），实际C consumer逐批写IPC；不经Table/read_all/cast/reblocking。writer明确V5、use_legacy_format=False、allow_64bit=False、compression=None、exact binding schema、custom_metadata=None。bounded BytesIO在每次write增长前检查剩余payload预算。源normal EOF+exact rows+successful source close并验证原receipt，writer/managed cleanup全成功后才返回frame；partial sink不发布。

open先exact bytes及IPCLimits、100-byte最小长度、magic/total length、总ceiling、exact caller rows、batch上限、payload digest，再live binding/current canonical digest；之后才`pa.ipc.open_stream`。SDK IPC reader是RecordBatchStreamReader子类，沿用已实测的SDK C-stream handoff成为S09接受的exact RecordBatchReader，再经S11 owned acceptance seam。该seam仅为内部opened handle在接受前失败时清理，不放宽原raw-reader domain。

IPCStream只保留原frame bytes/claims/live binding/managed session与实例身份，无第二套一般状态机。既有S09正常EOF/close与原declared extent仍是输入完成的条件；`verify_ipc_completion`额外要求frame rows/batches相等、原binding/frame关系保持、managed CLOSED且无primary/cleanup错误，返回同一个原receipt。EXHAUSTED尚未完成delivery cleanup；early close/late error/cleanup failure不产生IPC完成。foreign release不足以完成；copied/grafted wrapper不能克隆authority。frame owner在session生命周期内保持，返回owned arrays可在wrapper关闭后继续使用。

message custom metadata允许安全SDK构造的bounded变体，但owner/meaning/extent/completion/trust/ownership键一律不赋权；payload digest相应改变仍可得到相同合法values。schema metadata依原exact binding规则检查。raw Arrow complete-message prefix可能当短stream接受；截断原Pietto frame由length/digest拒绝。重封装并采用较小caller extent可以是不同conditional result，不能认证原结果。hash只提供bytes correspondence，不是authentication/native-memory sandbox/SQL或DB成功。

## 原十组与资源

保留既有十组名，在组内完成当前合同，不建立平行taxonomy：ipc_roundtrip、ipc_boundary_truncation、ipc_mid_message_truncation、ipc_completion、ipc_metadata、ipc_corruption、ipc_limits、ipc_lifecycle、ipc_uuid_representation、ipc_correspondence。严格102product/100实质controls，原92/90与9SDK保持。双target13字段复用独立ordinal/NULL、Float bits、Decimal coefficient/scale、UTF8、timestamp ticks、UUID bytes；完整schema和empty/firstNULL/uneven/trailing-empty/batch order/duplicates分别观察。独立struct/hash算术验证100-byte frame，contract digest比对既有完整neutral文档；IPC bytes不成为跨runtime canonical承诺。

96MiB包含100-byte header，独立于64fields/4096rows/8MiB及1024batches/1048576rows/64MiB finite limits。所有旧label/contract ceilings保持。小fixture exact/one-under、digest先于decoder、真实metadata变体、source/decoder/writer/cleanup failure及原值替换oracle按不同层记录。source/copy/writer/final bytes/decoder allocations可重叠，frame ceiling不是RSS；单次SDK调用内部allocation/阻塞不受sandbox或backpressure保证。

## 同18路径与累计预算

Q3原位冻结18路径，A3/M15/D0，无额外路径；旧principal名称沿用。

```text
src/pietto/_project/project_result_ipc.py
tests/test_phase67_slice12_bounded_ipc.py
docs/phases/phase-67/slice-12.md
src/pietto/_project/project_result_ingress.py
tests/_pietto_phase67_result_product_probe.py
tests/test_phase67_slice9_finite_reader_completion.py
tests/test_phase67_slice10_arrow_ownership_interop.py
tests/test_phase67_slice11_result_ingress.py
tests/test_active_phase_lifecycle.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
docs/phases/phase-67/brief.md
docs/phases/phase-67/slices.md
docs/phases/phase-67/planning-notes.md
docs/decisions.md
docs/references/engineering-lessons.md
docs/development.md
docs/status.md
docs/roadmap.md
```

已批准累计上限：product每runtime5、SDKfinal每runtime2、review2、followup2、Q4；full上限仍2，旧full为历史，full2为新合同唯一最终验证。其余保持diagnostics6/focused12/corrections12/env2/ordinarycommit1/FFpush1/failed-CI child-push-delta各1/native最多4/docs-onlypartial1。复用两既有env，agents/detached/simultaneous downloads/localDB/full3.12/extra cold matrix/manualCI均0。保留所有失败、旧wheel/report与计数，不重新开账。

按授权Q3→current implementation/focused→Review2冻结完整finding集→剩余budget单批repair→followup2→Q4→depth-one→full2。新full包含五static、独立collection、四fresh serial partitions、coverage/managed/health、generated/golden/package、exact新wheel、双runtime product/SDK和22全文比较；不复用旧full作为当前结果。然后exact stage/普通sole-parent commit/FF push、自然attempt1全部15jobs、current raw与三native strict、owned cleanup和中文报告。旧环境/metadata-role HOLD保持历史，本次授权由本执行代理完成闭环。

完成须绑定新tree与fresh Git/CI/raw/native证据。Phase67 ACTIVE/N67=16、Slices01–12完成后S13 NEXT/NOT STARTED，14–16未开始；Phase66/InterludeV/R1完成，package/CLI0.1.0不变。在S12终态停止。

Review2冻结R3接受后sink/session构造失败的确定性cleanup、R4外层ABI与原cause/等大小替换/current claim controls分列，在原owner与十组内单批修复。原cause OSError与外层ArrowInvalid分别记录；这不是新增支持域。实际followup2/Q4/full2/自然CI结果归外部同一ledger。

用户在C8准备错误HOLD后明确将累计corrections上限从8调整为12，其余上限不变。C9仅将两处E731 lambda赋值改为直接分支调用；失败与旧候选73daf92a保留。followup2依据当前focused/两typing及3.12实际102/100通过关闭R3/R4；Q4确认同18路径、原22全文保持。full2、同tree publication与fresh CI/raw/native仍是完成的必要条件。
