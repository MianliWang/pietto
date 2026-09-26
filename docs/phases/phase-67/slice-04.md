# Phase67 Slice04：Int/Bool/finite Float 与显式无损 Arrow 适配

基线 `be51fef66655e68d7fb450649a5b2061115016d1`，tree `12b7a4e64346d35c3b158ca9bd82b64c46562fd6`，sole parent `ff6b1b0233f11aab400905a5952bcf8ca0e60e82`；natural push/main36197167166 attempt1，15 jobs及S03最终三个native checks通过。本文件在production编辑前创建。

只展开P67-A02/A03/A04/A06；保留A01/A05/A08/A11/A15/A16/A18。供给rows与source contracts是结果边界观察，不是cursor/DB执行证明。S05–07的Text/Decimal/Timestamp/UUID、S09有限reader、S10协议所有权、S11一般Arrow ingress、S13extra、S14producer integration保持后续所有权。

## 接受的private API与表示

沿用ResultContract、ProducerResultBinding、ArrowResultBinding三个authority。producer完整核对retained emission、字段身份/order/domain后才考虑Arrow类型。没有第二solver、cast registry、跨kind转换或新SQL存储。

| logical / producer storage | physical positional carrier / domain | default Arrow |
| --- | --- | --- |
| Int / pg_int2、my_smallint | exact int；完整int_range位于signed16 | int16 |
| Int / pg_int4、my_int | exact int；完整int_range位于signed32 | int32 |
| Int / pg_int8、my_bigint | exact int；完整int_range位于signed64 | int64 |
| Bool / pg_bool | exact bool；bool01 | bool |
| Bool / my_bool01 | exact int 0/1；bool01，显式转换False/True | bool |
| Float / pg_float8、my_double | exact finite float；finite_float/binary64 | float64 |

ProducerObservation保留旧位置参数及protocol_nullable；lower/upper扩为可选，non-Int必须None；追加domain（默认int_range）与carrier（默认int）。Bool明确domain=bool01、carrier=bool或int01；Float明确domain=finite_float、carrier=float。metadata不覆盖logical nullability，不从样本猜载体。

`IntegerWidthRequest(field: ResultField, bits: int)`位于现有Arrow owner；`bind_arrow(producer, *, integer_widths=None)`接受完整按字段顺序的tuple，每项为绑定该exact field的request或None。整个None/字段None保留producer宽度。只接受exact int16/32/64，foreign/moved/duplicate/missing requests拒绝；非Int字段只能None。显式窄化或加宽仅当完整producer区间被target signed range包含，empty/小样本不能影响判定。规则先于Arrow依赖加载/转换检查，旧int8/bigint无参数调用保持int64。

行输入检查physical scalar，Arrow batch检查logical scalar；MySQL正确转换的bool不能再套int01输入谓词。Float拒绝NaN/±inf/int/bool/Decimal/text；使用IEEE754 big-endian bytes独立比较±0.0、重复值、fraction、small/large finite。contract-only checker可以接受另一个in-domain值，值真伪必须由独立输入快照oracle判断。

保留ordered labels/ports、完整列数、logical NULL、typed empty/all-null、owned buffers。64fields/4096rows/8MiB及caller tightening不变；8byte/cell加validity的保守预估覆盖bool bitmap，实际retained buffers另查；小限额与slice-retained buffer见证不分配巨量数据。

原pietto.result-contract.v1格式及四份S03 canonical documents保持；新增Bool/Float通过既有export/pure/re-encode/独立correspondence。codec所有者经premise确认无需编辑。MySQL Bool value-window既有B1阻断保留，不扩大operator admission。

## 有限见证与独立oracle

W01：两target×16/32/64真实source/projection、默认schema、加宽、signed端点、duplicates、9007199254740993与负数；wrong producer width/domain在conversion前拒绝。
W02：同一neutral root以contained int_range产生合法narrow/default/wider bindings；全域不fit在binding时拒绝，即使预期empty/all-small；foreign/malformed请求拒绝。
W03：两target混合Int/Bool/Float、renamed和nullable/non-nullable字段；物理carrier独立正反例，bool逻辑batch与MySQLint01输入分开。
W04：Float bits oracle保留±0.0和finite极值；拒绝nonfinite与exact类型冒充；协调sign-flip可过domain却不通过值oracle。
W05：typed empty、all-null、实际NULL违反NON_NULL、missing/swapped/duplicate/foreign records、coordinated producer+Arrow graft。
W06：caller mutation、configured fields/rows/bytes、retained slice buffers、optional Arrow缺失；不实现borrowed/多batch/EOF/IPC。
W07：Bool/Float codec与旧documents完整bytes回归、pure/live distinction；原9SDK/23product各自独立必需，新案例扩现有report并有damage controls、真实installed origins/input closure。

六个基础representation组合已由diagnostic1在原upstream得到VERIFIED，均含Int/Bool/Float，codec同样通过。fixture builders复用现有source/build_neutral/emission_input；不以不合法源推断adapter失败。普通core测试保持Arrow-free，真实Arrow正例在两隔离installed consumers必需执行。

## 精确冻结与验证

冻结15路径（A2/M13/D0；无reserved路径）：
- `src/pietto/_project/project_result_binding.py`
- `src/pietto/_project/project_arrow_result.py`
- `tests/_pietto_phase67_result_product_probe.py`
- `tests/test_phase67_slice4_numeric_bool_float_arrow.py`
- `tests/test_active_phase_lifecycle.py`
- `tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py`
- `docs/phases/phase-67/slice-04.md`
- `docs/phases/phase-67/brief.md`
- `docs/phases/phase-67/slices.md`
- `docs/phases/phase-67/planning-notes.md`
- `docs/decisions.md`
- `docs/references/engineering-lessons.md`
- `docs/development.md`
- `docs/status.md`
- `docs/roadmap.md`

production仍228个非generated文件；test新增principal一份，499→500，保持完整discovery/exact equality。当前lifecycle table/owner/node同步；既有workflow与ci_validation product路径直接消费新manifest，无需修改。其他路径一律受保护。

一次author/Ponytail integrated review、完整finding set、一批必要修正、一次targeted follow-up；一次浅depth候选检查；一次final3.13 full-equivalent：五static、独立U、四分区串行fresh roots、完整reconciliation/health、generated/golden/package一次、两runtime最终installedSDK/product/damage/full-byte comparison。所有heavy guard on、workers≤4，项目uv固定Arrow-free3.13.13，明确children不变。

预算：diagnostic6、focused12、correction8、full2默认1、review/followup各1、Q2、external env2、local product每runtime3、initial commit/push各1、conditional failed-CI child/push/delta review各1、native strict4默认3；agents/detached/manualCI/DB0。保留所有failed starts；需要超额动作才HOLD。

本地seal后ordinary sole-parent commit与FFpush各一次，自然exact-head push/main attempt1所有15jobs成功；github_bytes取得新raw artifacts并核对ID/name/length/SHA/context，完整reports核验与fresh PG/MY/aggregate native strict。receipt普通exclusive binary copies，先统一lstat/完整bytes/33MiB/精确pair-only manifest/三argv预检。无symlink、重编码、旧head receipt或status-only发布。

外部ledger/JSONL保留meaningful steps、wall/monotonic、review实际区间、parent/children与未知间隔；不重扫历史成本。当前尚未review/seal/发布，不把本设计当验证PASS。全部门槛完成后Phase67 ACTIVE/N67=16，Slices01–04 COMPLETED/PUBLISHED，Slice05 NEXT/NOT STARTED，06–16 NOT STARTED；Phase66/Interlude V/R1及package0.1.0不变。

## Integrated review 与收敛

主作者correctness/Ponytail review冻结完整R1/R2：probe末尾旧damage计数21遗漏新增7项，精确更新为28；domain-total适配增加Int16两端点及越界一位、重复/换位/畸形请求与禁止调用coercion方法的独立见证。两cause合并一批，production未因review改动。原23case加7组，现required product manifest30；原9SDK不变。首次3.13 installed launch在旧计数断言失败，保留为消耗的start；复验及最终gate结果由外部ledger/seal绑定，不冒称失败已PASS。

## 最终验证前的实际状态

R1/R2 targeted follow-up通过：普通focused、typing及depth-one候选的direct readers全部闭合；第二次3.13 installed consumer完整30cases/28damage controls通过。production wheel自初版未变，review只补测试/probe与记录。首次installed失败、两次patch sandbox初始化失败均保留。Q2确认无新upstream/product决策、15路径范围及two-runtime/fresh-native义务保持。随后一次最终equivalent及实际reviewed/tested tree、Git/CI链以外部seal/ledger记录；不额外发布文档状态。
