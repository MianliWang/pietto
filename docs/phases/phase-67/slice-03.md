# Phase67 Slice03：canonical private result contract、pure decoding 与 runtime correspondence

基线 `ff6b1b0233f11aab400905a5952bcf8ca0e60e82`，tree `eb77c04176da6f3bb15979026b22d7defe0dbbb2`，
sole parent `cffb59b29961b4a75552979093d0a18f369cf7df`；natural push/main36176037555 attempt1，15 jobs success。
本文件在产品实现前创建。只有本地 seal、普通发布、自然 CI 和原始证据核验全部完成才发布终态。
Slice02 文档延迟同步的已披露偏差保留为历史，不回写修正。只执行 S03，不开始 S04。

## 接受与字段覆盖

P67-A01/A05/A15：真实 source 的 verified neutral output → live contract → 独立保存的 private bytes →
有界 pure view；显式原合同及 verification 提供独立 runtime correspondence。原 producer→Arrow→owned Int64 batch 链继续使用原运行时对象。
P67-A02–A04/A08/A11–A12/A16 和 A18 回归义务保留；不是全 Phase 最终审计。

| retained component | wire projection / pure invariant | runtime check | witness |
| --- | --- | --- | --- |
| authority / selected owner | document-local scoped declaration coordinates、module path/namespace/kind/name，非 opaque root token | supplied verification 精确对象及现有 verifier | W01/W07 foreign equal-looking root |
| active output | output/node occurrence coordinates、owner、role、field denominator | 对 retained active output 完整核对 | W01/W06 missing tail |
| ordered fields / ports | fields 保留 ordinal、label、field identity、output、typed port coordinates 与来源位置；不同 occurrence 不按名字合并 | independently enumerate all plan exports | W01/W05 drop/duplicate/reorder |
| declared/canonical scalar | declared TypeExpr 与参数/NULL syntax；canonical kind/name、可用 nominal/refinement 描述；保留既有 alias/import 描述，不重解类型 | retained field/type facts and exact type-reference authority | W02 non-Int/Decimal/imports |
| nullability | `non_null` / `nullable` / `unknown`；declared absence 单独用 null | effective upstream nullability | W06 legal substitution |
| provenance | 既有 kind、symbol/module identity、authored location 与相关已有引用；共享 declaration 以明确 local reference 表达 | independently compare full provenance and its denominator | W02/W07 graft |
| multiplicity / ordering | retained BAG posture；null 表示无 order；有 order 保留按序 key expression、position、direction、引用；NULL treatment 未提供则显式 unspecified | actual retained ordering authority；不从 rows 推断 | W02/W06 direction substitution |
| reference closure | local reference 精确 kind/index/scope，完整可达，禁止 dangling/foreign-kind/duplicate/cycle；描述性坐标不成为 live capability | compare all referenced members, no prefix-only match | W05/W08 |

不把未知当缺席、不把 adapter unavailable 当 scalar descriptor unavailable。描述符支持域大于当前 Int 数据适配器。
不递归导出 compiler session，不含 target release、physical storage/range、Arrow metadata/buffers/rows、SQL、
绝对宿主路径、PID/time/Git/CI。两合法 producer bindings 不改变同一个 neutral contract 的 bytes。

## 冻结格式、资源界面与实现边界

private marker `pietto.result-contract.v1`。UTF-8 JSON，`ensure_ascii=False`、`sort_keys=True`、
`separators=(",", ":")`、`allow_nan=False`，末尾恰好一个 LF；不做 Unicode normalization。
语义数组保持原顺序。JSON 数字只用于有界非负整数坐标/计数，Bool 不算 index；literal Int 用规范十进制字符串，
Float 用有限 `float.hex()` 字符串（保留 signed zero），Bool/Text/NULL 使用独立 tags。closed field sets，无 unknown-field fallback。
字节输入先检查长度及结构 nesting，再交标准库 JSON；duplicate keys、非法 UTF-8/escape、nonfinite/nonnormal number、
非规范字节、额外尾部均确定性拒绝。accepted bytes 必须逐字节 decode/re-encode 相同。

hard limits：4 MiB（包含 LF）、depth48、65536 values、8192 records、16384 references、每 text131072 UTF-8 bytes、
累计 text2 MiB、1024 fields。小 caller limits 只能收紧。export 同样先限 traversal/value/text、再限制完整编码；拒绝不返回 partial bytes。
这些限制仅约束 private document，不回溯限制 live factory；64 fields/4096 rows/8 MiB 的原 batch ceilings 保持。

pure view 防御性持有 canonical bytes，提供 owned data/fields，显式 pure validate/re-encode；只依赖 stdlib。
export 使用 verify_result_contract 及其现有上游 verifier；不 parse/build/prepare/emit replacement authority。
independent correspondence 单独实现 retained-field comparison，不调用 exporter 或其 semantic projection。
runtime-bound export 仅保存 supplied contract/context 与 bytes，绝非 decoded-data resurrection。
coherent smaller/altered document 可以 pure-valid，但必须在原大合同的 runtime check 拒绝。
另一次编译不会全局废除原 immutable context；equal descriptive bytes 可以在 B 自己的 authority 下对应 B，不能证明源自 A。

## 有限 witness manifest

| ID | required checks |
| --- | --- |
| W01 | PG/MY renamed + nullable 全字段、canonical bytes、pure view、correspondence；原14个 product 与9个 SDK cases 独立必需 |
| W02 | Text、parameterized Decimal、既有 nominal/alias/import/refinement 描述、共享 provenance，ordered/unordered；不扩 Arrow-value 支持 |
| W03 | 重复 export、等价构造顺序、relocation、固定 hash seeds 7/19；两 primary runtime 比较完整 document bytes |
| W04 | fresh process block compiler/runtime/Arrow imports，pure decode/owned fields/re-encode；独立手写小 oracle/字段枚举 |
| W05 | closed fields/version/kind、UTF-8/escapes/numeric tags、Bool index、refs/sharing/cycles、字段 omissions/duplicates/reorder、truncation/trailing/limits |
| W06 | coordinated tail/count/ref removal、合法 field/order 属性更改：pure-valid/runtime-invalid |
| W07 | foreign roots、owner/output/port/type/provenance graft、stale bound export、协调 live-leaf/document damage；原 context 保持有效；bytes/dict/view 不可作 live inputs |
| W08 | 禁用 exporter 后独立 checker 正常；注入 coherent exporter omission 由 downstream checker 检出，真实上游 verifier 保持 |
| W09 | no unauthorized reconstruction；fresh pure subprocess；core install Arrow-free；installed module origins 与当前输入闭包 |
| W10 | 小 configured document limits；原64/4096/8MiB、exact large Int、duplicates、empty/all-null、pre-conversion mismatch、owned buffers 回归 |

固定小 corpus：postgres、mysql、descriptors、imported；child seeds 不新增 global differential family/process cells。
installed probe report 延用 `pietto.result-product.v1` 并精确扩展 case manifest；保存少量完整 canonical documents，
data-only verifier 独立核对内容及 refusal observations；damage controls 包含 missing docs、changed bytes、bogus correspondence、origins/context/version。
两个 compiler/package jobs 和 required runtime completion 都消费扩展 probe；本地及下载自然 CI raw reports 后比较完整 canonical payload；不增加 workflow steps。
不新增 jobs/placements、artifact retention、native cases 或 coverage schema。

## 路径、预算和验证

冻结 A5/M11/D0，共16路径：

- A `src/pietto/_project/project_result_contract_pure_boundary.py`
- A `src/pietto/_project/project_result_contract_portable.py`
- A `src/pietto/_project/project_result_contract_correspondence.py`
- A `tests/test_phase67_slice3_result_contract_portable_boundary.py`
- A `docs/phases/phase-67/slice-03.md`
- M `tests/_pietto_phase67_result_product_probe.py`
- M `tests/test_active_phase_lifecycle.py`
- M `.github/workflows/ci.yml`
- M `docs/phases/phase-67/brief.md`
- M `docs/phases/phase-67/slices.md`
- M `docs/phases/phase-67/planning-notes.md`
- M `docs/decisions.md`
- M `docs/references/engineering-lessons.md`
- M `docs/development.md`
- M `docs/status.md`
- M `docs/roadmap.md`

Q1：只扩 approved S03，三检查独立、当前 descriptor 支持与 adapter 分开；以上路径足够接入现有 required consumers。
无新 architecture/user decision。所有上游 production、旧 portable boundaries、public API、grammar、locks、pins、CI topology、
项目环境和 .agents 受保护。必要 post-freeze extra path 或 protected behavior 需求立即 HOLD。

预算：diagnostic6、focused12、causal correction6、full-equivalent2（默认1）、integrated author/Ponytail review1/followup1、
Q2、external env2、每 local primary complete product launch3、seed2、initial commit/push1/1、conditional child1/1、native strict verifier4。
无额外 agents、detached heavy jobs、local DB/Docker 或 manual CI。guard on、重 parent 串行、workers≤4；abort也计一次 full。
项目级 uv 固定现有 CPython3.13.13；两 fresh external env 安装 locked core/candidate wheel/原 hash-checked Arrow25.0.1。

最终一次3.13 equivalent：五 static gates、independent full collection、四 fresh partitions 串行及 exact reconciliation/health，
generated/golden/installed package 各一次、两个 runtime SDK+extended product+pure children/full-byte compare；无需额外 monolithic/full3.12。
一次 integrated primary-author/Ponytail review、一批 material repairs、一次 targeted follow-up；不宣称独立第三方认证。
外部 ledger/seal 保留 reviewed dirty candidate tree、实际 origins/context/raw bytes、所有失败及累计计数。
提交前重绑 baseline/remote、stage exactly sealed tree，ordinary sole-parent commit/FF push；自然15 jobs attempt1成功后，
raw-byte route 核对实际 artifact IDs/size/SHA256/context、两 runtime coverage/product/SDK/health 和 fresh PG/MY/aggregate native receipts。
WATCH/INSUFFICIENT_EVIDENCE 仅 advisory。无 source historical execution/DB execution、finite completion、IPC 或 public compatibility promise。
后续 scalar additions 必须显式扩此 private grammar与三组检查，不可静默推断。

外部证据目录：`~/.local/state/pietto/evidence/phase67-slice03/20260925T210052Z/`。
冻结时未 seal / 未发布；累计计数和 incidents 以该目录的 `pietto-phase67-slice03-ledger.json` 为准。

## 执行 HOLD（未 seal、未发布）

冻结前的 reader inventory 漏掉现有 exact typing-inventory reader：
`tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py:93`
要求 production/test 文件数225/498，而本候选实际为228/499。该文件不在冻结16路径中，dispatch §7
要求 post-freeze expansion 显式批准；因此停止，没有修改冻结外文件，没有运行 full gate 或发布。

另一个已确认 reader 是 `tests/test_phase11_ci_workflow.py:222`：候选新增两个 aggregate downloads 后，
其 raw-download 计数由2变4。推荐 continuation 删除本候选新增的非必需 workflow steps（已冻结路径内），
仍在本地 rehearsal 和下载 natural-CI raw reports 后运行完整 bytes 比较；因此无需扩展此 workflow reader。
最小新增批准只涉及前述 typing-inventory reader；候选当前原样保留，未先行执行 continuation。

当前实际改动 A5/M2/D0；其余已冻结路径尚未修改。初步codec和probe尚未完成 integrated review/installed evidence，
本文前面的内容是验收设计，不能视为已验证完成。首次focused46 passed；第二次focused92 passed/1 failed：
探索性Enum投影在既有上游得到ProjectSQLPlanUnavailable/expression_evidence_unavailable，并非已有可用neutral合同。
修正组1将它保留为拒绝见证，采用已支持的直接Decimal参数正例，同时修复两处故意错误类型输入的test annotations；修正后尚未复验。
不改变上游semantics，不宣称Enum新增成功。targeted Ruff通过，targeted typing的原两项失败保留。

累计：targetless diagnostics4/6、focused2/12、correction1/6、Q1/2、review0/1、followup0/1、
full0/2、external Arrow env0/2、两local product starts均0/3、native strict0/4、commit0/1、push0/1；
agents/detached jobs/DB/Docker/manual CI均0。项目解释器仍3.13.13且Arrow-free；.agents保留。
还有实现完整性审查、全部installed证据、local gate、文档终态和Git/CI链待执行，不把HOLD称为Slice完成。

## 续行修订与实际 wire 覆盖

用户明确批准17路径allowlist：原16路径外仅增加`tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py`。变更225/498→228/499已逐项对应三个codec owners和一个principal；旧freeze/HOLD及workflow删除前diff存于外部。workflow现与baseline相同，属于未使用路径，不stage；实际A5/M11/D0共16路径。

closed top-level fields：`format, owner, output, field_count, fields, types, multiplicity, ordering`。owner以module/namespace/kind/name及module/declaration位置描述；output保留output/node位置、owner与field_count。field完整保留ordinal/label、field identity、export/definition/producer坐标、output与position、declared TypeExpr/arguments、canonical kind/name/symbol、effective及原evidence nullability、result role、provenance kind/symbol/location、原type resolution。

`types`按首次语义引用顺序保留唯一nominal declaration，其base/parameters、ensures表达式或Enum成员为closed结构。type resolution保留direct/canonical状态、全部alias refs和terminal target；`origins`按reference分组，保留全部paths、逐hop的reference/target/import/facade路线与builtin或nominal terminal，不能flatten丢掉路径关系。相同Money声明由两个字段共用一个local type ref；Python container interning不进入格式。

ORDER保留provided/final类别、owner与每个key的expression、authored/effective direction、`nulls=unspecified`；从既有retained plan附上完整prepared item/value/type及按序uses、scope/ports/pending requirement。plan/IR坐标是当前描述范围中的typed occurrence coordinates，不能用于反序列化runtime；`type_declaration`是必须闭合、可达、kind正确的document-local索引。pure只验证文档声称的结构/关系，不解决未存储的compiler semantics。

编码前后均有resource preflight：大text在UTF-8分配前检查字符上界，raw JSON在stdlib分配前统计depth/value/record界限；所有closed-schema畸形容器返回private错误。65字段中立合同可export，而原Arrow batch仍限64；小document限制不污染原live factory。

四个determinism documents为PG、MY、Text/refinement/Decimal/shared alias、imported aliases+computed ORDER；合法Unicode literal `café é`保持原码点。一个额外直接Decimal参数正例与一个具体Enum程序的`expression_evidence_unavailable`拒绝分别记录；不推广为所有Enum支持判断。

installed manifest精确23 cases（原14保持），含27个有界malformed类别、coherent tail/unknown-nullability/ORDER变更、equal-looking owner/output/port/type/provenance graft、saved bytes与damaged live chain、exporter禁用与coherent writer缺陷注入。保存四份主document和三份coherent alternatives；21种report-damage控制要求全部拒绝，实际import origins及current input closure独立核验，无固定159模块数。

一次integrated primary-author/Ponytail review冻结R1–R3：projection completeness、pure totality/resources、installed evidence/docs；合并修正记为causal groups3–5。修正后targeted follow-up、Q2、本地full-equivalent、两runtime完整consumer及最终raw-CI证据由外部ledger/seal给出实际结果，不在本文件预言尚未发生的HEAD或CI成功。

原计数、失败及scope amendment保持累计。轻量日志与中文成本复核只做一次有界S01/S02/S03历史提取，后续只追加当前步骤。最终report必须贴出可读成本摘要，不能只给本地路径。发布链全部成功后Phase67 ACTIVE/N67=16，Slices01–03 COMPLETED/PUBLISHED；Slice04 NEXT/NOT STARTED，05–16 NOT STARTED；Phase66/Interlude V/R1及package/CLI0.1.0保持。
