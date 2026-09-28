# Phase68 Slice01 — FULL initiation and measured driver premises

S01 CANDIDATE; completed only after closure。只实施test-only premise harness与FULL启动产物，禁止S02/后续生产实现。
基线HEAD `2f280ea02b974c0ab7e6e8e07017b960b55f850a`，tree `82c4ee8ecb4718d5110630d8759eaad2102163e1`，sole parent `437916ecf59d8873ef154a1e09f1e48e76884edf`；自然CI36373861089/push/main/attempt1。
S16外部终态激活Phase67完成；core/package/CLI0.1.0与既有能力不变。

## Q1 exact write set

18路径，A8/M10/D0；ceiling28/A8/D0。下表在首次tracked edit前冻结。数值余量不授权其他路径。

| Path | Purpose |
| --- | --- |
| `docs/phases/phase-68/brief.md` | approved mission, full A01-A22 scope, regression inventory and risks |
| `docs/phases/phase-68/slices.md` | 20-row baseline DAG, premise gates, S02 sizing and S10 midpoint |
| `docs/phases/phase-68/planning-notes.md` | measured dispositions, technical30 mapping and three reference families |
| `docs/phases/phase-68/slice-01.md` | precise experiment contract and conditional closure |
| `scripts/phase68_executor_premise.py` | explicit test-only driver observation and data-only report checker |
| `tests/test_phase68_slice1_executor_premises.py` | offline full-denominator and discriminating report-damage controls |
| `ci/phase68-executor-premise-requirements.txt` | isolated experimental dependency identities |
| `tests/_pietto_phase68_executor_cases.py` | separate finite fixture/oracle definitions from driver observations |
| `docs/decisions.md` | approved optional execution choices |
| `docs/status.md` | Phase67 external closure and Phase68 candidate lifecycle |
| `docs/roadmap.md` | authorized20-row baseline and unchanged future owners |
| `docs/development.md` | explicit local premise invocation and regression distinction |
| `docs/references/engineering-lessons.md` | P67-L01-L06 consumption and measured caveats |
| `tests/test_active_phase_lifecycle.py` | sole current lifecycle reader |
| `tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py` | exact ordinary test inventory additions |
| `tests/test_phase11_generated_guard.py` | new explicit test-only script inventory |
| `tests/test_phase11_golden_policy.py` | new explicit test-only script inventory |
| `tests/test_phase11_validation_entrypoint.py` | new explicit test-only script inventory |

全部src/、grammar/generated、public API/CLI/SQL/JSON、pyproject/uv.lock、原Arrow/target pins、原native receipt、CI workflow/workload/health、core环境、.agents、host与credentials受保护。
输入为本轮独立ACTIVE请求、v8规划索引、liveAGENTS/架构gate、P67审计/lessons及精确现有helper；附件排版差异不产生新授权。

## Exact experiment / resource contract

`tests/_pietto_phase68_executor_cases.py`固定3routes×19named cases=57，分组P01依赖/route identity、P02三个参数向量、P03typed populated/empty/allNULL七族、
P04稳定view/Serializable正常只读、P05多pull/emptyEOF/earlyclose/真实表达式error/标注cleanup injection、P06实际阻塞后取消、P07编译非空/空/旧fixed emission/命名族owner。
精确SQL/输入/oracle分别保留在cases、probe和复用的Phase66/67fixture。解码、实际值记录和独立literal oracle分离；typed BAG保重数，metadata不由首行推断。
ADBC primary use_copy=True，唯一显式alternative=False；typed Arrow参数和batch-size hint1均明确记录。新driver observations只在owned CPython3.13.13、requirements精确pins环境。
PG18.6/MySQL8.4.12使用原target image digests、原owner身份/TLS/checks；endpoint unix:///var/run/docker.sock，loopback，新query只读role与manager分离。
单DB、1CPU/1GiB/512MiBtmpfs（原facility更严格值）；startup120/connect10/query10/read20/cleanup30秒；16rows/1MiB每case、16MiB每target报告、4KiB每diagnostic。
case内有界control线程和child必须join/reap；没有agents、disowned jobs或并行顶层heavy。原guard固定outer/children解释器；依赖仅进owned外部环境。

报告每个case只能为OBSERVED_SUPPORTED、OBSERVED_UNSUPPORTED、OBSERVED_MISMATCH、INCONCLUSIVE_ENVIRONMENT；失败前已取得观察及时保留。
完整unsupported可完成实验，但PRODUCT_GATE_BLOCKED，不能冒充adapter parity；环境未结论HOLD。report checker拒绝missing route/case、dependency/source漂移、换输入/实际值/target、缺terminal、unsupported升格与虚假next readiness。

## Budget / execution

唯一累计ledger：`~/.local/state/pietto/evidence/phase68-slice01/20260928T203400Z/pietto-phase68-slice01-ledger.json`。
所有新耐久证据使用pietto-phase68-slice01-前缀；旧原始证据不改。失败/HOLD/resume不清零。
诊断≤6/focused≤12/causal corrections≤12/review1/followup1/Q通常2≤3/full通常1≤2/driver matrix≤3且保留final；
新driver环境≤2/ADBC released selections≤2/每route alternative≤1/DBstarts≤8。历史native rehearsal0；四clean安装cells同wheel；每runtime原SDK/product通常1≤3；
native strict≤4，local captured replay每runtime≤2；ordinary commit/FFpush各1，实际failed-natural-CI child/push/delta各≤1；manual CI actions/release/tag/upload0。

显式入口：owned3.13/bin/python scripts/phase68_executor_premise.py run --directory <new-owned-evidence> --ledger <single-ledger>。
普通pytest仅验证data-only report，不连接DB或导入Arrow。开发矩阵与最终同候选矩阵分开；纯报告格式变更不重跑无变化实验，probe/fixture变更使受影响观察失效。

## Sole conditional closure

仅当同一reviewed/tested/sealed tree完成以下事实，外部终态才能激活S01 COMPLETED/PUBLISHED；本文不预言未来commit或CI：

1. 完整P01–P07观察、真实状态、依赖/资源身份、独立值/终态和57分母checker通过；明确唯一READY_FOR_SLICE02_EXPERIMENT或PRODUCT_GATE_BLOCKED_REPLAN。
2. 一次完整author/Ponytail finding集、因果修正、一次targeted followup、Q2/depth-one完成，未解决的必需问题为HOLD。
3. 一次authoritative guarded3.13 full equivalent：static、独立collection、四串行partitions、coverage/managed/health、generated/golden/package；同candidate wheel四clean core/Arrow cells，双runtimeSDK9、原120/118、22完整文档比较。
4. 精确stage，一个ordinary sole-parent commit与FFpush；新head自然push/main/attempt1全部requiredjobs/steps成功。保留failedhead，仅授权child可修复；不amend/rebase/force/rerun/dispatch/cancel。
5. 当前28raw的完整ID/name/size/SHA/head/run/attempt/input及真实consumers；fresh普通native副本、exactpair预检、PG/MySQL/aggregate strict；当前CI/local3.12/local3.13captured replay闭合。它们是P66/67回归，不是新driver实测。
6. owned资源close/reap，精确清理owneddisposable根；保留wheel、premise/raw/native/replay、失败、core与.agents。最终HEAD/remote相等且index/tracked干净。

成功或具体HOLD后停止S01；S02 NEXT/NOT STARTED，S03–S20不释放实施，完整路线尺寸PENDING S02实证重验。

## S01 IPC continuation amendment

原HOLD候选`c63bf591c1029adde52220716f7a4026b28dfa30`是实际Git tree对象，不是commit；matrix3的14/57及全部失败原样保留。
用户后续ACTIVE请求仅修test-harness control pipe，写集仍18路径/A8/M10/D0。Q3绑定恢复；Q4绑定最终收敛。
本S01累计ceiling修订为：driver matrices5、DBstarts9、causal corrections16、integrated review2、targeted followup2、Q4；USED不清零。
其他初次dispatch上限不变，后续Slices默认仍12组。matrix4为完整修正运行；matrix5只供明确原因和对应修正后的恢复，不是必需重复。
修复采用parent raw/nonblocking读取与显式有界JSON-line缓冲，先消费已累积完整帧；严格UTF-8整帧解码、control EOF与result EOF分开，stderr有界排空，原ACK/manager操作与180秒watchdog不变。
真实无DB管道回归直接调用实际pump，覆盖coalesced请求/ACK、UTF-8分片、EOF、timeout/brokenpeer及旧buffered策略区分；不触碰Phase67 Arrow IPC。
新完整57项必须来自同一次当前输入运行，不把原14与新43拼接。记录实际execution tree；仅文档结果记录变更时，明确diff并核对完整可执行footprint不变后可复用该矩阵。
原full/四安装cells/SDK9/120118/22全文/natural CI/28raw/native/current replay与条件发布规则全部保持。

## Matrix6-only completion addendum

最新用户授权仅实际使用matrix6一次、Follow-up2与Q4；文本表格有更高数值，但明确正文禁止matrix7/第三轮完整review，本轮遵循较窄行动边界。
操作账本只将driver matrix累计ceiling5→6，其他既有上限不放大；amendment bookkeeping不另收费Q/C15。
matrix6已完成57项有限观察及独立checker，实际execution tree/最终docs tree关系见planning-notes和外部matrix6-binding。
后续必须依原唯一规则执行首次完整回归、四cells/双runtime消费者、普通发布与自然CI/raw/native/replay；本文件仍为CANDIDATE; completed only after closure。
