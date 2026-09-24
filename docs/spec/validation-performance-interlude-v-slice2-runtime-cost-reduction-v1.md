# Validation Performance Interlude V Slice2: Runtime Cost Reduction v1

## Decision and boundary

`IMPLEMENTATION_FREEDOM`：只错开已有 xdist workers 对各自所需 process cells 的访问起点。
`DifferentialAcquisition` 原已提供 run-local store、资源锁、cell 锁和 per-worker memo；
本次复用它们。无新 pool、worker、持久 cache、compiler 优化、oracle 变更或 CI 修改。
结果为 `performance_outcome=MEASURED_GAIN`，带下述环境实例差异限定。

基线为 `e3cbd80e7db9f994f45c03770cc7ed92aae1fdf6`，tree
`e8ceba6fabf19b5d16cc594999afde5283a75e81`，sole parent
`d3ba2e7a7da710dbd4736670b6257d96e885e71d`。修改前已确认 natural push/main
[36052583300](https://github.com/MianliWang/pietto/actions/runs/36052583300)、attempt1、五 jobs success。
Phase66 completion 和 Dependabot maintenance 是继承历史，不计入本 S2 ledger。

首次仓库编辑前冻结以下八路径；A2/D0，不扩大原 envelope：

- `tests/_pietto_differential_process_acquisition.py`
- `docs/development.md`
- `docs/status.md`
- `docs/roadmap.md`
- `tests/test_active_phase_lifecycle.py`
- `tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py`
- 本 spec
- `tests/test_validation_performance_interlude_v_slice2_runtime_cost_reduction.py`

六个 target helpers 的递归本地 import closure 与本次 execution owner 无交集；
235 个 protected source/helper/pin/manifest/lock 文件的字节在本次修改前后保持相同。
`src/**`、target inputs、workflow、lock、版本、validator worker/loadfile/OOM policy 不变。

## Current measurement and limits

唯一前后实验各执行四个原有消费者，CPython3.13.13、四 workers、loadfile、同一外部
instrumentation 和既有 owned-gate guard on。它们分别拥有 Phase65 process matrix、
Phase65 independent field/identity/role oracle、Phase64 flat-IR process equality、
Phase63 full records/metamorphics。该四-node workload 会生产整个共享矩阵，不是廉价 unit benchmark。

| Scope | Before | After |
| --- | ---: | ---: |
| pytest summary, four tests passed | 562.66s | 176.46s |
| External guarded invocation wall | 563.640593s | 177.628776s |
| First producer start to last producer end | 553.710963s | 168.706787s |
| Sum of cell producer wall, includes child waiting and resource preparation | 568.418031s | 656.884609s |
| Per-worker nonproduction time, includes lock waiting and payload reads | 309.398–552.902s | 1.141–6.077s |
| Per-worker parent CPU inside payload acquisition | 2.691–3.024s | 1.436–1.525s |
| Per-worker selected-node collection | 1.129–1.229s | 1.098–1.203s |
| Relocation / wheel-build-and-install preparation | 0.152s / 0.284s | 0.033s / 0.310s |
| Peak summed owned-process RSS | 3.218 GiB | 2.929 GiB |
| Minimum effective available memory | 9.814 GiB | 10.067 GiB |
| Maximum memory PSI full avg10 | 0.00% | 0.01% |
| Peak owned processes, including existing CLI children | 10 | 12 |

Before 的四消费者基本等待同一 cell，短暂小-cell 重叠不改变主要串行瓶颈。
After 同时生产四个独立 cell，producer-wall sum / production-span 从约1.03变为3.89；
没有减少 observation 工作，producer-wall sum 还增加了。较短关键路径和显著减少的非生产时间
证明协调机制有用；它们不是 child CPU 或总 runner cost。未单独计量每个 child 的 CPU。

慢 testcase 时间不能直接当作语义计算：Phase65 independent field oracle 的 setup 为
554.01s → 167.79s，call 为6.89s → 7.04s；Phase63 对应 setup 为553.61s → 166.01s，
call 约0.02s。已有 sweep/独立断言都保留，没有为了 node 数量拆分它们。

两次实验均 fresh acquisition roots，重新生产 installed/relocated fixtures，不复用跨 run
semantic results。它们并非 fully controlled comparison：首次实现的 Ruff 命令漏设解释器，
uv 自动把项目 `.venv` 重建为3.12；随后已启动的 focused launcher 固定3.13，又触发重建为3.13。
这两次重建违反原任务约束并触发 HOLD；
用户随后前瞻接受已重建 CPython3.13.13/locked 环境继续同一 S2，没有追溯授权或重置计数。
当前全部18个 installed distributions 的版本与 lock 相符，相关 import locations 已核对；
未装的 colorama/tzdata 是 Windows-only。旧环境完整 metadata 未记录，仍未知。
uv/bytecode/OS cache 与背景负载未清空或宣称相等。因此表中差异是 observed difference，
不能当成全部由补丁造成的隔离因果百分比或稳定方差改善。

RSS 是1s采样的 owned-process RSS 之和，含共享页重复计数，可能遗漏瞬时峰值；PSI 为系统观测。
两轮无 guard abort，未见实质内存风险增加，after 的 `.venv/pyvenv.cfg` identity 保持不变。
无需新增 pressure admission check。普通四 worker 上限及全部 S1 cleanup/exit75 规则继续有效。

## Assurance conservation

改动只在 `documents(family)` 内对所需 cell 去重并旋转访问顺序，再按原 request 顺序返回
字节。每个 cell 仍由原锁和原 `_run_cell` 生产，保持 interpreter/hash seed/mode/ambient/
workspace 及 cell 内完整 request 顺序。每个逻辑 request 仍单独调用原 observation/render。
失败保持传播，不做 fallback/retry；没有替换独立 checker 或跨 root/mutation 缓存检查结果。

本机支持集合为3.12/3.13，前后16 cells、98 requests。逐 cell manifest 的 request identity、
ambient 和相对 workspace/cwd 顺序、interpreter、seed、executable 完全对应；所有原始 result
bytes 直接相等，并保存逐 request digest inventory。checkout/relocated/installed origins 分别
绑定各次 invocation 的自身 roots；Phase65/66 modules 的 same-child origins 同样检查。
不可把16/98硬编码成所有环境保证：现有 manifest 对支持集合大小 I=1/2 给出
`24 + 37*I` requests，cell 数由完整 request-cell union 决定；单/双解释器断言仍在。

原十个 acquisition consumer 文件及所有旧 test entrypoint、独立 oracle、负例、relational
checks 保持不变。新 principal 检查单/双 interpreter manifests、不同 worker 起点、原序返回、
仅所需 cell、同 invocation 完成复用、不同 roots 重做、serial 顺序及失败只发布一次且不重试。
原 standalone/forward/reverse batch、atomic failure、relocation/wheel assertions 保持启用。
最终 full suite 使用新的 pytest invocation，不能复用此处 before/after 结果。

## Validation and publication

外部证据根为 `/tmp/pietto-v5s2-20260924/`：`ledger.json` 保留全部 starts 和两次环境偏差；
`comparison.json` 保留时间线分析、全部 request/output inventory 与 origins 比对；raw profiling
不写入 semantic documents 或 target receipts。单作者 self-review 加 installed Ponytail review，
不宣称独立审稿人或多代理审查。全量与 CI 终态绑定外部 seal/publication records、Git 和自然 CI，
不另做 status-only commit。尚未通过的 gate 不由本 spec 代替。

外部 launcher 对每个 project-level uv command 统一固定 `UV_PYTHON=3.13.13`，所有 nested
validator commands 继承；不覆盖显式 child interpreter 选择。最终权威入口为：

```bash
UV_PYTHON=3.13.13 uv run --locked python scripts/validate.py --timings --oom-guard on
```

保留最多两次 full starts 的原预算，默认只用一次；不重复 unaffected generated/golden/package
检查，不启动本地 DB。普通 sole-parent commit/FF push 后，必须等待新的自然 push/main attempt1
Python3.12、Python3.13、Target postgres、Target mysql、aggregate 五 jobs 成功，并通过现有
data-only verifier 核验新的两份 raw receipts 的 artifact IDs/digests 和 strict per-target/aggregate。

历史全量观测独立列示：Phase66 local validator 1060.565s（pytest959.93s）；当前维护基线
CI3.12/3.13 validator1355.828s/1919.931s（pytest1266.42s/1811.02s，16117 passed/6旧 skips）。
不同 head、环境、hosted runner 的这些数据不是本短实验对照，也不证明某 Python 版本更慢。
最终 full validator 子 gates、pytest、job elapsed 和端到端 CI 分别在发布证据/终端报告给出。

## S3 cost and coverage handoff

- 必需观察总量未下降。一次 invocation 的共享生产包含所有需求 cell；本机该 workload 的
  elapsed acquisition 窗口约168.7s，生产 wall 之和约656.9s，不能再把旧470s当当前固定 floor。
  小于375s不是自动批准 sharding；Interlude IV 的旧 NO_GAIN 在其环境仍成立。
- 测量中的大节点主要等待共享生产，独立 oracle call 仍约7s；其余 standalone/batch 正反序
  全 probe 重做、语义负例和普通 suite 成本未优化。完整 suite 的剩余尾部应结合最终时间判断，
  不把四-node wall 直接外推为 full-suite wall。
- coverage-preserving 首选候选分区：同一 pytest invocation 保留 Phase58–66 全部共享
  acquisition consumers（含 Phase65 Slice14/15），其余不依赖该 store 的 tests 才考虑另分区。
  任何实际分区须证明完整 node union/disjointness、全部 cross-node assertions，以及独立运行
  会触发的新 acquisition 成本；这里不修改 CI 或发布一个未测的分区方案。
- 最多使用既有四 workers，不能每个 worker 再开 pool。每个 shard 都重新生产矩阵会增加总
  runner work，但并行 K jobs 的 wall 不是自动等于 K*P；critical path 是最长 required dependency
  path，total runner cost 是各 job elapsed 之和。aggregate 仍等待两 Python 与两 target jobs。
- 可在 S3 核对并共享的具体候选：`uv lock --check`、Ruff format/check 的相同 checkout、lock、
  native Ruff0.16.8 和配置输入。Pyright base/tests 虽同设 pythonVersion3.12，仍须证明有效配置、
  dependency/import paths 和工具版本一致后才去重。ANTLR generation 的工具链和生成字节须另证。
  pytest 两 Python runtime domains、golden serialization、各解释器 installed package 行为不能
  凭“静态外观”去重；两 native targets 和 strict receipt aggregate 保留。
- S3 合并 gate decomposition、证据支持的 sharding 决定、Dependabot grouping、最终 benchmark
  与 closure；需要自己的 dispatch，不拆成新的 profiling/sharding/grouping/closure Slices。

## Lessons and lifecycle

消费 [Phase66 J04/J05/J06](phase66-completion-audit-phase67-handoff-v1.md#phase66-retrospective-and-engineering-lessons)：
J04 要沿完整消费链核对逐 request/origin/bytes 与独立 oracle，不能靠 pass count 证明保真；
J05 把等待、生产 sum、关键路径和内存分开，先利用已有资源协调，再决定 CI 分区；
J06 保留失败/偏差与累计 starts，明确 environment acceptance 不抹去旧事件。
解释器选择必须覆盖所有 uv-launched tools；`--locked` 不阻止环境同步，`--no-sync` 不证明依赖正确。

Phase66 remains COMPLETED，N66=16；Interlude V ACTIVE、total route=3；S1 COMPLETED/PUBLISHED。
S2 COMPLETED/PUBLISHED 仅在上述完整发布/CI链成功后生效，performance_outcome=MEASURED_GAIN
带环境差异限定；此前为候选。S3 NEXT / NOT STARTED / execution requires its own dispatch。
Phase67 NEXT / NOT STARTED，accepted v4 retained；package/CLI0.1.0。无自动第四 Slice。
