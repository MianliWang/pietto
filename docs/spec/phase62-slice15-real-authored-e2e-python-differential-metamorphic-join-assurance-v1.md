# Phase 62 Slice 15 Real Authored E2E, Python Differential, And Metamorphic JOIN Assurance v1

## 状态与起始 authority

本合同冻结：

```text
PHASE62_SLICE15_REAL_AUTHORED_E2E_PYTHON_DIFFERENTIAL_COMPATIBILITY_METAMORPHIC_JOIN_ASSURANCE
```

Slice 15 基于已发布的 Slice-14 portability child：

```text
commit c67b2414942974988397682e4a8a776890e38b5d
tree   15200d4207f29904d970041518209872e7e5bb75
CI     33587048578
       push/main
       attempt 1
       success
```

Phase 62 Slices 1–14 已完成并发布。Slice 15 是唯一 publication candidate；
Phase 62 Slice 16 = NEXT / NOT IMPLEMENTED。

## Assurance-only scope

Slice 15 只增加 docs/tests assurance：

```text
production delta = 0
public delta = 0
SQL / CLI / JSON delta = 0
```

真实链路从 real authored Project 开始：

```text
check_project_parse_only
-> build_empty_project_semantic_result
-> keys / Value FDs
-> base Project IR / evaluation / relational properties
-> relationships / conditions / guarantees
-> authored JOIN uses / explicit paths
-> binary JOIN region
-> multi-fact analysis
-> independent Phase-62 verification
-> fresh five-product analysis bundle
-> private inspection
-> pietto.phase62-inspection.v1 canonical bytes
```

Positive E2E 只调用既有 builders，不手工制造 semantic facts、relationship uses、
JOIN nodes、aggregate facts、multi-fact results、verification results 或 portable
inspection documents。没有新增 production orchestrator。

## Real authored corpus

Probe 自持真实 `.pietto` fixture text，并由 pytest 临时写入两个 Project modules。
主 component 覆盖：

- unique direct shorthand 与 explicit one-hop VIA；
- explicit two-hop VIA 与 accumulated-left binary topology；
- INNER/LEFT、branching from an earlier binding、self/role-playing reuse；
- one-to-many fanout、nullable equality、ordered composite equality；
- parallel direct ambiguity、unknown relationship、bad endpoint role；
- concrete/non-concrete JOIN regions；
- join-free same-context aggregate facts、reused facts、comparable grain、independent
  multi-fact chasm 与 multiplicity exposure。

第二个 disconnected module 保留 independent source/query component，确保 corpus
不是单 relation fixture。JOIN-bearing deferred queries 不包含 aggregate expressions。

## Reviewed common observation

`EXPECTED_COMMON_MANIFEST` 是一次提交、不可动态更新的 human-reviewable manifest。
它显式记录 module/declaration positions、relationship/direction/condition occurrences、
JOIN-use states/path lengths、selected binary effects、key/FD/grain signatures、fact/
locality identities、alignment/chasm classifications、VERIFIED status、five analysis
products、winner-free query cardinalities 与 inspection section counts。

Probe 同时输出完整 ordered portable records 与完整 canonical bytes。所有环境直接
比较完整 observation bytes、portable records 与 canonical bytes；SHA-256 只用于大型
payload 的 review 摘要：

```text
digest != semantic identity
digest != canonical comparison substitute
```

不按名称或 serialized bytes 排序，不 bless environment-local expectation。

## Python differential matrix

复用 Phase-58 installed-wheel/interpreter helpers及 Phase-61 process-batched pattern：

```text
Python 3.12 and Python 3.13
PYTHONHASHSEED = 0, 1, 7, 4294967295
```

每个 available supported interpreter 对四个 seeds 运行 source-checkout probe；每个
interpreter 另以 seed 7 运行 relocated source 与 isolated installed wheel。当前
validator interpreter 必须在 matrix 中，最终 Python 3.12/3.13 authority 属于自然 CI。

每个 probe process 内都执行 normal and reverse authored file-creation order，以及
primary/transformed Project construction/query order。外层 pytest 控制 subprocess、
cwd、ambient environment、source relocation 与 wheel target；probe 自身不含
`subprocess.run`、environment discovery、wheel builder、cache 或 normalization。

Installed-wheel observation 必须证明 `pietto.__file__` 位于 isolated target 内，且
不在 checkout 内。

## Required authored metamorphics

### direct shorthand versus explicit VIA

同一 exact direction 的 direct shorthand 与 explicit one-hop VIA 保留相同 guarantee、
fanout、survival、null-effect facts；JOIN-use 与 Project-IR identities 仍不同。不声称
whole-query identity 或 canonical-byte equality。

### parallel relationship ambiguity

Primary corpus 的 direct shorthand 只有一个 candidate。Transformed corpus 新增第二个
parallel relationship 后，shorthand 成为 non-concrete `AMBIGUOUS`，explicit original
VIA 仍 concrete，并按 authority order 保留两个 candidates，不选择 winner。

### remove target uniqueness

只删除 exact target UNIQUE evidence，观察既有静态 transition：

```text
AT_MOST_ONE -> UNBOUNDED_BY_ONE
PRESERVES_SOURCE_MULTIPLICITY -> MAY_MULTIPLY
```

同时比较既有 candidate-key/FD/grain-transfer consequences，不在测试中推导新规则。

### INNER versus LEFT

同一 relationship/path 的 INNER 与 LEFT 显式比较 survival、outer barrier、right-side
null extension、effective nullability、`NULL_EXTENSION` property、key/FD strength 与
nulling grain-factor provenance。

### multi-hop, accumulated-left, and role reuse

N-step VIA 产生恰好 N binary JOINs；step `i > 0` 的 left input 是前一 JOIN output。
相同 relation/fact 的两次 authored use 保留不同 JOIN uses、field introduction uses、
factor uses 与 fact localities。

## BAG/NULL oracle test-side witnesses

测试直接使用已发布 Slice-13 stdlib oracle，不增加 production adapter。覆盖：

- one-to-many BAG multiplication 与 left/right multiplicity scaling；
- LEFT unmatched row、NULL equality `UNKNOWN`、INNER empty；
- multi-column composite equality 中一个 NULL component 阻止 match；
- `Customer -> 2 Orders -> independently 3 Returns` 产生 `2 * 3 = 6` bounded chasm
  witness；
- dependent `Customer -> Orders -> Items` 根据实际 Order key 产生 3 rows，而不是
  independent `2 * 3`；
- bag input order、INNER swap + exact column permutation invariance，以及 LEFT
  non-commutativity。

Oracle result 不是 Project semantic authority 或 verifier proof；bounded PASS 不是
rewrite certification。

## Negative and pure-boundary differential

每个环境保留 typed state/reason families：parallel direct ambiguity、missing explicit
relationship、bad endpoint-role direction、zero-allocation non-concrete JOIN region 与
non-concrete multi-fact subject。比较 typed states/reasons，不比较 CPython exception
text。

Selected malformed portable documents 只覆盖 unknown format、section order 与 dangling
ref 的 normalized status/coordinates，不重复 Slice 14 全 rejection suite。

Fresh scopes 必须不同且 runtime refs 不等；等价 source 的 observations、portable
records 与 canonical bytes 相同。Starting coordinates `(7, 11, 5, 5)` 的 shifted build
保留 authored semantic observation，但 runtime positions 与 canonical bytes 不同。
Scope token、cwd、absolute root、object address、`repr()` 与 hash-derived identity 不得
进入 observation。

## Execution discipline

Matrix 按 process 批量获取，不为每条 assertion 启动 subprocess；同一 immutable wheel
target 在支持的 interpreters 间复用。Tests 支持 serial fallback 与 xdist
`--dist=loadfile`。

Focused commands：

```text
UV_PYTHON=3.13 uv run pytest -q tests/test_phase62_slice15_real_authored_e2e_python_differential_metamorphic_join_assurance.py
UV_PYTHON=3.13 uv run pytest -q -n 2 --dist=loadfile tests/test_phase62_slice15_real_authored_e2e_python_differential_metamorphic_join_assurance.py
```

## Frozen boundaries

Slice 15 不改变 production、grammar/AST、semantic law、relationship/path/JOIN behavior、
key/FD/grain rule、multi-fact classification、verifier/analysis、inspection format、oracle、
joined scalar namespace、aggregate-over-JOIN、reaggregation/algebra、Script IR/SQL、CLI/
JSON/public schema、optimizer/rewrite、persistent cache、package/dependency/workflow 或
version。

任何需要 production edit 的 genuine E2E defect 均为
`ARCHITECTURE_DECISION_REQUIRED`。Slice 15 repair 最多一次，并且只能位于 frozen
docs/test closure；第二 repair、hidden winner、normalization 或 Slice-16 work 为终止。

Fresh complete review 冻结并修复一个 test-observation completeness root：

```text
SLICE15_E2E_OBSERVATION_OMITS_NEGATIVE_MULTIFACT_QUERY_AND_CROSS_LAYER_CONTINUITY_EVIDENCE
```

同一 repair batch 增加 exact cross-layer `is` assertions、non-concrete multi-fact
typed subjects/zero-allocation evidence、common/chasm/nulling winner-free query closure，
以及 earlier-binding branching 证据。Corpus、matrix、manifest policy、production 与
semantic expectations 均未改变。Slice 15 repair accounting 为 `1/1`；不允许第二
repair。

## Changed-path and publication lock

Exact closure 为 A3/M6/D0，9 paths：

```text
docs/roadmap.md
docs/spec/phase62-slice15-real-authored-e2e-python-differential-metamorphic-join-assurance-v1.md
docs/status.md
tests/_pietto_phase62_join_differential_probe.py
tests/test_active_phase_lifecycle.py
tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py
tests/test_phase62_slice15_real_authored_e2e_python_differential_metamorphic_join_assurance.py
tests/test_validation_performance_interlude_slice2_differential_probe_runtime_decomposition_optimization.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

最终只运行一次 authoritative validator：

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Publication 是一个普通 non-amend commit `Add Phase 62 JOIN end-to-end assurance`、
一次 fast-forward push 与自然 exact-head CI attempt 1；不 dispatch、rerun、cancel 或
添加 status-only follow-up commit。

真正 PASS 后：

```text
Phase 62 Slices 1–15 = COMPLETED / PUBLISHED
Phase 62 Slice 16 = NEXT / NOT IMPLEMENTED
```
