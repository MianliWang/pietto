# Phase67 Slice15：whole-result laws 与 Phase68 readiness

基线 `31156eaf22341e0b16b400d496982c7ff51d610c` / tree
`994f85f4cae08f9e399a663d6dce617be80afc81`，自然 push/main CI36356999376 attempt1、15jobs成功。
本 Slice 对 P67-A01/A03/A05/A09/A13/A14/A17 提供有限 joint assurance；Phase67仍ACTIVE、N67=16。
S16承担最终A01–A18三层审计及完成决定；本文件不启动S16或Phase68。

## Q1：有限 corpus 与观察边界

复用现有混合13列、七类scalar/12种physical choices、nullable和descriptor/imported fixtures。
每结果最多5行、每route最多5批；重复值、BIG=9007199254740993、NULL、Float signed zero、
Decimal coefficient/scale、Unicode、civil microseconds及UUID原始bytes均按位置核对。
Text trailing spaces另外保留原S14五类scalar的真实八cell路线。
expected 来自独立literal fixture；input decoding、SDK观察和law checker分开。bool/int/null显式tag，
Float用IEEE754 bits、Decimal用signed coefficient+scale（正负零系数均0）、Text用UTF-8、
Timestamp用civil microseconds、UUID用标准bytes。BAG用typed Counter保重；它不是Pietto collation规则。
C协议要求的UUID field metadata按真实边界精确核对，不把不同schema先cast成相同推断dtype。

| law | source/target | original | transformation | relation | route | refusal | counterexample |
| --- | --- | --- | --- | --- | --- | --- | --- |
| W01 | finite mixed PG/My | 4 rows with BIG/repeat/NULL/-0/Decimal/civil/UUID | rows/native/IPC | exact positional schema/null/value and complete | C-array/C-stream/IPC | schema/domain/delivery | same-domain scalar |
| W02 | same mixed PG; descriptor/imported | 4 rows; 4-field ordered contract | [4],[1,3],[0,1,0,3,0]; BAG permutation; desc->asc | sequence per input; typed Counter across BAG; ORDER correspondence | fresh C-stream + pure/live | CORRESPONDENCE | duplicate loss or legal changed ORDER |
| W03 | mixed PG/My and recompiled projection | same-type duplicate labels; empty/allNULL/small | Int16->32, string->large, Decimal128->256, UUID->binary; projection permutation | values same; exact requested fields and distinct new mapping | C-array + IPC | ARROW_ADAPTATION/PRODUCER_OBSERVATION | moved/foreign/repeated request; old-mapping swap |
| W04 | mixed PG and imported descriptors | live contract/export and fresh equivalent source | pure decode, fresh compilation, tail/owner/field/provenance graft | pure may correspond; bound/runtime cannot migrate | independent correspondence + finite C/IPC | ROOT/FIELD/CORRESPONDENCE/meaning | writer defect and coordinated producer/schema |
| W05 | mixed PG + current existing terminal cases | fixed extent4/session | early/prefix/trailing-empty/late/decoder/export/writer/cleanup | input,delivery,IPC terminal separate | managed C-stream + IPC | extent/source/cleanup/bridge | completed input with failed delivery; non-source StopIteration |
| W06 | mixed PG + current SDK ownership cases | mutable whole result and explicit lease | close, alias mutation, copy/spend/graft grants | owned independent; borrowed retains owner but aliases mutable | C-array/C-stream | INTEROP_BINDING/SPENT/LEASE | retention without nonmutation |
| W07 | mixed PG current100-byte frame | 4 rows in2batches | corrupt; coherent same-count value replacement; prefix; batch-count | integrity separate from original-value correspondence | complete incremental IPC | IPC_FRAME/INTEGRITY/COMPLETION | valid mutated result with successful conditional completion |
| W08 | mixed PG | small retained buffers and two layouts | exact/one-under limits; same values/repeated backing | independent A/R; sum(max(A,R)); separate frame length | managed C-stream + IPC | LIMIT before copy/value/frame decode | simultaneously over-limit and invalid value |
| W09 | current existing corpus + historical S14 expected22 | all22 current canonical docs | current runtime comparison and S14 full bytes | all complete bytes; original domains/meaning/extra remain | current complete product and package cells | existing semantic/producer/package regressions | obsolete p39/80MiB expectations |
| W10 | mixed PG | independent retained original4 rows | value/-0/swap/reorder/duplicate loss/replacement/NULL; patched copy | sequence/BAG discriminate appropriate changes | C-array + IPC with restored patch | original oracle | real valid-but-corrupt builder output |

原110 groups/108 controls逐项保留；十组新law接原required product，最终120/118。
原组的complete checker先执行，whole checker再联合引用本次执行的terminal/authority/ownership证据；
不把旧PASS当成新执行，也不为每个law复制原完整graphs和22份文档。现有22中立文档仍在唯一原字段中
生成，由最终orchestrator作当前3.12/3.13全文比较及对应S14 verified文档全文比较。
S14旧文档只作expected bytes，native/current replay由本次自然CI新产物驱动。

无新增sidecar、job、依赖、fuzzer、production facade或cache。新helper import/checker在core无Arrow可用；
product与S14 relocated/replay的显式helper加载、复制、input closure包含传递依赖。installed origins按真实观察记录。
S14原G/H BAG、I/J empty两target八cells保持五类logical scalar，不宣称native Timestamp/UUID或全七类覆盖。
测试重分批、行置换、合成变值均为test input transformation，不是新DB执行或cursor布局观察。

## Phase68 support/evidence matrix

| owner/API | supplied authority / preconditions | current domain | completion / ownership | evidence layer | non-support / next owner |
| --- | --- | --- | --- | --- | --- |
| `project_result_contract.build_result_contract`；portable/pure/correspondence | completed verified plan、exact selected root、field occurrences；explicit scalar meaning | 七类scalar的logical shape；nominal/refinement及ORDER只在已有descriptor层 | pure document可对应fresh equivalent contract；bound export必须原live authority | S03与W04本次checker；22完整neutral bytes | 不从bytes复活authority；未知nested→Phase71，stronger trust→84 |
| `project_result_binding.bind_producer` | exact emitted artifact、ordered observations、完整declared domain/carrier/nullability/provenance | Int16/32/64；PG Bool / MySQL0或1；finite Float64；Text；Decimal；显式Timestamp/UUID | conversion前核对；empty/allNULL不证明domain-total adaptation | 双target installed fixtures、S14五类captured-native replay、W03/W04 | 不是driver adapter或SQL执行正确性证明；Phase68负责连接实际producer事实 |
| `project_arrow_result.bind_arrow` / verify | producer binding、exact field-bound representation/labels | Int16/32/64；bool；finite double/signed zero；string/large_string；Decimal128/256；timestamp(us)；canonical UUID/binary16 | 重复carrier label保留不同field occurrence；schema精确；无sample inference | W01/W03全七类fixture、S04–S08原域反例 | 无隐式widen修复producer lie；无新ORDER producer成功域 |
| Decimal shared domain / result producer | precision1..65、shared scale0..p；producer scale≤min(p,30) | Decimal128/256 fixed signed coefficient；零统一0 | context-free exactness与NULL按原合同 | S06本次完整regressions、W01/W03/W09 | 不恢复p39旧拒绝，不新增算术/nominal Arrow支持 |
| scalar meaning / civil time / UUID | builtin source occurrence的显式meaning；默认缺失拒绝 | civil1000-01-01至9999-12-31 23:59:59.499999；无timezone转换；UUID128bit标准序 | source/field/provenance绑定先于Arrow | S07本次端点/meaning负例；W01/W04 | 五类native replay未覆盖两类；Phase68 adapter须供应可信meaning |
| `project_result_ingress.ingest_rows/ingest_batch/ingest_reader` | positional rows或explicit typed carrier；fresh raw reader | flat finite CPU批；empty/allNULL显式schema；13列mixed | 原checker；默认owned，borrow需真实lease/nonmutation | W01三route、W02重分批、W10实际copy缺陷注入 | 不推断首行dtype、不compact掩盖invalid carrier |
| `project_result_reader.open_finite_reader` / verify | exact binding、fresh exclusive source、caller expected_rows；原resource limits | batch≤64fields/4096rows/8MiB；≤1024batches/1048576rows/64MiB累计 | normalEOF+exactextent+successfulclose；session-bound completion；empty非EOF | W02/W05/W08；原S09/S10完整terminal controls | 非执行成功、非可信DB总行数；Phase68设计extent/finalization来源 |
| `project_arrow_interop` managed batch/stream、BorrowLease、transfer | original live binding、fresh grant；explicit realowner和nonmutation承诺 | CPU C Data/C Stream/PyCapsule | ownedcopy独立；borrow持owner至consumer释放；alias仍可mutation；transfer非exclusive buffer | W06真实SDK/weakref/alias、W10；S10原9SDK和grants反例 | 非独立C实现认证或exact native callback计数；devices→86，Rust/PyO3→90 |
| `project_result_ipc.encode_ipc/open_ipc/verify_ipc_completion` | original binding、expected_rows、boundedframe；exactschema | 100-byteheader、uncompressedstream、总96MiB；当前格式 | extent/batches/integrity、source completion、delivery cleanup分开；metadata不授权 | W01/W05/W07/W08实际incremental consumers，prefix及coherent altered result | 非source认证、非跨runtime canonical IPC；public format另有owner |
| S13 `scripts/package_smoke.py` / `pietto[arrow]` | same candidate wheel；core/extra不同cleanprefix；pin25.0.1 | 当前实测Linuxx86-64 CPython3.12/3.13；package/CLI0.1.0 | core Arrow-free；private lazy API保持 | 四final安装cells、SDK9、required120/118、实际origins | 无额外平台/range/release/publicalpha承诺；Phase69 public alpha |
| S14 native receipt replay helper | 当前run exact PG/MySQL原始receipts先strict验证；原source/contract/publicartifact及五列事实 | 两target×G/H BAG与I/J empty八cells；五类scalar | 三route typed BAG/field/terminal；各进程重建liveauthority | 本次CI3.13、local3.12/3.13 captured-native replay | 旧DB观察重放不是新query；path和偶然独立BAG顺序非值等价条件 |

Phase68可消费以上live bindings、owned/leased batches、checked finite readers、CPU C protocols、private IPC、
optional extra与真实receipt replay；仍须设计connection/statement/execution authority、实际driver adapters、
transaction lifecycle、errors/cancellation/backpressure，以及可信extent/finalization证据。
`expected_rows`不授权hidden COUNT query、不发明exact cursor rowcount，也不解决unknown-cardinality执行。
尚未开始Phase68；publicalpha→69、nested→71、strongertrust→84、devices→86、Rust/PyO3→90。
任何已承诺Phase67义务的实证缺口需具体记录，不能换名future-owned以宣布PASS。

## 精确路径与预算

Q1共27可写路径，初始expected19变化、另8个private owner为有因repair reserve；至多32tracked变化、A3/D0。
reserve只有发现已批准域内的具体缺陷并附独立regression时才可使用，不是新支持授权。

- `tests/_pietto_phase67_whole_result_probe.py`：new ten whole-result laws, positional typed oracle and data-only checker。
- `tests/test_phase67_slice15_whole_result_conformance.py`：new bounded core laws/checker independence tests。
- `docs/phases/phase-67/slice-15.md`：new frozen corpus and Phase68 support/readiness contract。
- `tests/_pietto_phase67_result_product_probe.py`：append ten groups/controls and exact helper/input closure。
- `tests/_pietto_phase67_real_consumer_probe.py`：transitive helper loading/copy/input closure only。
- `tests/test_phase67_slice9_finite_reader_completion.py`：direct current product denominator。
- `tests/test_phase67_slice10_arrow_ownership_interop.py`：direct current product denominator。
- `tests/test_phase67_slice11_result_ingress.py`：direct current product denominator。
- `tests/test_phase67_slice12_bounded_ipc.py`：direct current product denominator。
- `tests/test_active_phase_lifecycle.py`：sole mutable lifecycle reader。
- `tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py`：two new Python test files inventory。
- `docs/phases/phase-67/brief.md`：current Slice15 link, support boundary or conditional lifecycle。
- `docs/phases/phase-67/slices.md`：current Slice15 link, support boundary or conditional lifecycle。
- `docs/phases/phase-67/planning-notes.md`：current Slice15 link, support boundary or conditional lifecycle。
- `docs/decisions.md`：current Slice15 link, support boundary or conditional lifecycle。
- `docs/development.md`：current Slice15 link, support boundary or conditional lifecycle。
- `docs/status.md`：current Slice15 link, support boundary or conditional lifecycle。
- `docs/roadmap.md`：current Slice15 link, support boundary or conditional lifecycle。
- `docs/references/engineering-lessons.md`：current Slice15 link, support boundary or conditional lifecycle。
- `src/pietto/_project/project_result_contract.py`：RESERVE only: W04 live identity check if concrete graft defect。
- `src/pietto/_project/project_result_contract_correspondence.py`：RESERVE only: W04 independent pure/live correspondence if concrete defect。
- `src/pietto/_project/project_result_binding.py`：RESERVE only: W03 producer/field preconversion identity if concrete defect。
- `src/pietto/_project/project_arrow_result.py`：RESERVE only: W03 explicit adaptation and W08 pre-copy admission if concrete defect。
- `src/pietto/_project/project_result_reader.py`：RESERVE only: W05 exact extent/EOF/cleanup and W08 sum accounting if concrete defect。
- `src/pietto/_project/project_arrow_interop.py`：RESERVE only: W05/W06 grant/lease/delivery failure if concrete defect。
- `src/pietto/_project/project_result_ingress.py`：RESERVE only: W01 independent native carrier acceptance if concrete defect。
- `src/pietto/_project/project_result_ipc.py`：RESERVE only: W07 frame/completion separation if concrete defect。

保护pyproject/lock/pin/version、publicCLI/SQL/JSON、compiler/semantics/IR/plan/emission、Phase66全部设施、
CI拓扑/workloads、core和.agents。一个S15累计ledger；diagnostics6/focused12/corrections12，review1/follow-up1，
Q通常2最多3、full通常1最多2；开发package3、每runtime installedproduct≤4（通常≤3）、finalSDK通常1，
每runtime bounded replay≤3且historical总≤1；native strict≤4通常3。普通commit/FFpush各1；实际failedCI
child/push/deltareview各≤1；orchestration/docs-only continuation各≤1且共享两full上限。agents、detached、
并发download、localDB、localfull3.12、manualCI、release均0。固定core/isolated解释器、guard和≤4workers。

完成条件：一次完整finding集审查及一批root-cause repair、一次follow-up、Q2/depth-one；同tree完整3.13
static/collection/四serialpartitions/coverage+health/generated/golden/package、final双runtime120/118+SDK9
及22文档全文；exactstage普通soleparentcommit/FFpush；新head自然push/main attempt1全部15jobs及requiredsteps；
28raw逐份identity/size/SHA/context与真实consumer；fresh ordinary nativepair预检及PG/MySQL/aggregate三strict；
当前CI3.13/local3.12/local3.13八cell replay闭合。之后仅清理registeredownedroots并保留原失败/轮子/全部raw证据。
宽阶段start/end/basis及原events保留；parent/child/full/CIwall/runnersum/prefetchoverlap不重复相加。

成功后Slices01–15 COMPLETED/PUBLISHED，Slice16 NEXT/NOT STARTED；Phase67 ACTIVE/N67=16，
Phase66/InterludeV/R1仍COMPLETED、package/CLI0.1.0。此前均为candidate；在S15终态停止。

## 已复现的 IPC owner 修复

W01的[0,1,0,3,0]布局捕获实际缺陷：pinned SDK 经 C-array import 的零行、非零offset批次
直接写IPC会产生错误bodyLength/continuation；source已完成仍无法正常decode。纯SDK每列/组合
对照定位到C-import条件，26组合独立复现/修复观察归外部证据。
在已冻结`project_result_ipc` owner中，仅在原批次完成validation与retained/admission计费后、
交给SDKwriter前，对非零offset的零行批次作SDK empty take，得到offset0；原批次仍写出一次。
原source descriptors、累计charge、extent、batchcount、frame格式/96MiB和资源check-order不变。
W01两runtime真实consumer的完整fields/values/NULL/terminal是必需回归；不把空批当EOF或drop掉，
不对有值carrier复制/compact来掩盖validation failure。

## Slice15 Q2：收敛候选

唯一author/Ponytail finding集R1–R3已完成单批修复与一次follow-up：mixed retained bytes与managed
delivery descriptors由独立算式核对；畸形law报告保持原ValueError边界；当前lifecycle使用明确
CANDIDATE-until-closure条件转换，不以文档自证发布。853项focused、Ruff及两类typing通过。
更新wheel的3.12开发product为120/118、实际167origins；后续最终两个installedruntime仍须各自
新执行，开发报告不代替final。旧13列/七类、原110/108与S14八cell/28raw路线保持。
当前20changed paths/A3/M17/D0，仅使用IPC一个production reserve；其已复现空offset缺陷及
修复边界见本合同。depth-one、完整3.13及双runtimefinal、普通publication、自然15jobs/raw/native/
currentreplay仍是完成条件。S16/Phase68不开始。
