# Phase71 Slice22：获取整合与十个最慢节点复核

状态：获取与 profile 复核已完成，作为 B8 候选进入 S23；B8 的 Gate 2、提交和
自然 CI 另行封存。本片没有新增产品代码、缓存、调度或测试选择规则。

## 实际基线与覆盖

Phase 基线为 `9511f13563d0d5ce21fc778c6a3828a8324c2222`。最终实现与工具链输入为
`6ee4b2b0f35a7eff392755bdaccfff949775cf06`，tree
`45f11ad0a7ffef413c84b57a7c77ab528e765b22`；自然 push/main CI
`41502915403` attempt 1 的 19 个 job 全部成功。

逐路径清单覆盖相对此基线的 230 个变更 tests 路径（176 个 test owner、48 个
shared helper、6 个 fixture/pin）。48 个 helper 的直接读者清单区分 import、显式
字面量/manifest 引用与注释：511 条依赖/引用关系中，452 条读者路径在 Phase 基线
已存在；61 条仅文字上下文不计作执行消费者。另核对 result-product/helper registry、
differential cell manifest、native API manifest 和整树 collection/typing/CI 读者。
这些是有边界的引用清单，不是动态执行图的形式证明。

两套 CI runtime 各有 24,850 个 collected/selected/terminal nodes；596 个文件组的
收集数量与 B7 完全一致。pytest 9.2 自动缩短长参数 ID，历史 node-id 集合因此不同；
health 为 `INSUFFICIENT_EVIDENCE / WATCH`、可比样本 0。当前完整覆盖独立验收，
不把历史不可比解释成性能改善，也不据此改变 topology、worker ceiling 或排序政策。

## 获取处置

- 继续使用既有 process-local repository facts 与 run-owned differential acquisition。
  Python、seed、origin、family/request 身份保持独立；session 只表示本 worker。
- nested execution/admission/matrix、result contracts 和 public Unnest document 的
  module fixtures 已共享只读 compile/bind 准备；socket、workspace、monkeypatch、
  flat control 与实际 attempt 各自新建。
- literal oracle 与 metamorphic laws 共享 authored input，保持独立计算实现。
  corpus/datasets/realizations/instances 已按 canonical leaf tuple 缓存；损坏行采用
  replacement values 或 deepcopy，不修改共享 rows。
- plan/IR graft、foreign root、源码变体、source/wheel/relocation、Arrow offset/
  ownership、IPC serialization，以及 save→fresh R1→fresh export 继续保留独立获取。
- S20 sibling Arrow accounting 已归入既有 managed `nested_accounting`，没有新增 core
  Arrow 依赖。CLI 目录竞态与逐操作文件读取不能替换成不变源码缓存。
- 小规模 golden/config 读取、stdlib cleanup 和低 self-time 编码保留原 owner；未证明
  显著且相容的额外重复，不新增统一获取框架。每个路径的输入、lifetime、worker 与
  保留理由均在外部 acquisition inventory 中登记。

## 十个独立 profile

严格读取 artifact `13169844147` 的完整 health，并核对其 712,283 字节与 SHA-256
`a92be464b77f85a97e6f51efa6fb92b47289bfc2afc8f8ab49f9e19763fbde82`。
取两个 runtime 中 setup/call/teardown 合计时间的最大值，按其降序选择十个不同
node ID，同分按名称排序；不滤除等待子进程的节点。每个节点单独在合格集成主机的
CPython 3.13.13 / pytest 9.2.0 下运行一次 cProfile，CPU 0–7，其他自有工作限于
8–11，每项开始前 load < 8。十项均为一个测试通过，监控无错误。

下表是本机受 instrumentation 影响的归因，不能与 CI shard 时间相减宣称提速。
进程列是 `subprocess.run` 的已完成调用数 / 其中符合测试预期的非零退出数；
`poll` 次数不等于进程数。

| # | node | 本机秒 | parent poll 占比 | 进程 / 预期非零 |
|---|---|---:|---:|---:|
| 1 | `tests/test_harness_ir_differential.py::test_real_flat_ir_records_bytes_and_rejections_match_every_process_cell` | 580.28 | 97.32% | 16 / 0 |
| 2 | `tests/test_harness_plan_conformance.py::test_registered_corpus_has_independent_field_identity_and_role_expectations` | 583.63 | 94.95% | 15 / 0 |
| 3 | `tests/test_harness_plan_portability.py::test_registered_process_matrix_and_same_child_origins` | 583.73 | 97.07% | 19 / 0 |
| 4 | `tests/test_harness_sql_emission_portability.py::test_standalone_forward_reverse_batches_beside_older_families[checkout]` | 111.46 | 98.65% | 6 / 1 |
| 5 | `tests/test_harness_sql_emission_portability.py::test_standalone_forward_reverse_batches_beside_older_families[installed]` | 116.69 | 98.76% | 8 / 1 |
| 6 | `tests/test_harness_sql_emission_portability.py::test_standalone_forward_reverse_batches_beside_older_families[relocated]` | 116.82 | 98.75% | 6 / 1 |
| 7 | `tests/test_harness_plan_portability.py::test_standalone_forward_reverse_batch_and_atomic_failure[checkout]` | 111.69 | 98.95% | 8 / 2 |
| 8 | `tests/test_harness_plan_portability.py::test_standalone_forward_reverse_batch_and_atomic_failure[relocated]` | 119.30 | 98.96% | 8 / 2 |
| 9 | `tests/test_harness_sql_emission_portability.py::test_acquired_phase66_cells_same_child_origins_and_identical_bytes` | 562.68 | 99.12% | 15 / 0 |
| 10 | `tests/test_harness_plan_portability.py::test_standalone_forward_reverse_batch_and_atomic_failure[installed]` | 120.24 | 99.00% | 10 / 2 |

十项 parent profile 均由等待子进程主导。九个既有完整 memoized verifier body
均纳入监控，但这些 parent 中没有 top-level scope 调用，分母为 0/N/A；不推断
child 的 verifier 次数或 CPU 来源。独立的 pure-document decoder 另有可见分母：
35 个 plan document 对应 35 次 `_input_tree`（3,258,740 个 JSON tree occurrences、
73,379 records），18 个 VERIFIED emission document 对应 18 次（398,256 / 11,804）。
边界检查各执行一次；bytes prescan 与 parsed-object bound 是不同输入面的保护，保留。

高频 `_require` 是大量输入字段的类型/深度/边数/字节界限检查。pytest 的一次编号
临时目录 cleanup 解释了部分高频文件调用；没有记录删除路径的独立 identity，因此
不把调用数说成唯一路径数。低 self-time 的 AST/import/catalog 编码也没有重复输入的
证据。standalone、forward/reverse、malformed batch 与独立 malformed probe 保留各自
fresh execution，预期拒绝不记为意外失败。所有 finding 均明确 `KEEP`，无开放修复项。

结构结论是保留本期已形成的共享与独立见证；本片没有新的结构优化，也没有 wall-time
改善声明。完整 pstats、逐 top-level 计数、输入分母和处置在接管证据目录
`codex-takeover-20261031/parallel-20261101/b8_root_integration/` 的
`profile-summary.json`、`profiles-maintenance/01..10/`、`acquisition-review.json` 与
`acquisition-readers-final.json`。observer registry 的导入发生在 cProfile 计时前；
这不影响给定节点的完成结果，但属于本机归因方法的限制。后续代码/测试/工具链输入
改变时重新评估适用性；未变节点沿用这次 review。
