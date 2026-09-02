# Phase 62 Slice 14 Private Inspection, Winner-Free Query, And Pure Canonical Boundary v1

## 状态与基线

本合同冻结 `PHASE62_SLICE14_PRIVATE_INSPECTION_WINNER_FREE_QUERY_PURE_CANONICAL_BOUNDARY`。
它基于已发布的 Slice 13：

```text
commit c7d0e957affd346e976307863e0d0624c8e227ad
tree   e620535ecb20c33da11a6e2defc3edb6b0d65ac7
CI     33580406830
       push/main
       attempt 1
       success
```

Slice 14 是唯一当前 publication candidate。自然 exact-head CI 成功即完成
Phase 62 Slices 1–14，不需要 status-only commit。Phase 62 Slice 15 = NEXT /
NOT IMPLEMENTED。

## 精确范围

Slice 14 只增加两个 private owner：

```text
src/pietto/_project/project_phase62_inspection.py
src/pietto/_project/project_phase62_pure_boundary.py
```

两者均保持：

```python
__all__: tuple[str, ...] = ()
```

完整路径是：

```text
fresh VERIFIED ProjectPhase62AnalysisBundle
-> exact runtime Phase-62 inspection
-> typed winner-free queries
-> portable immutable Phase-62 document
-> one pure total evaluator
-> one canonical private byte payload
```

`ProjectPhase62AnalysisBundle` 是唯一 admission。inspection 按 identity 保留
`verification`、`root`、fresh base Project IR verification，以及 Slice 13 的五个
analysis products。bare `ProjectMultiFactAnalysis`、旧 verifier result、同 scope
替代物或非 VERIFIED 输入均不是 admission authority。

Inspection 不重新运行 parsing、semantic analysis、relationship/key/FD/grain
构造、path/JOIN 构造、multi-fact analysis、verification、Phase-62 analyses 或
BAG/NULL oracle。

## Runtime inspection

`ProjectPhase62Inspection` 是 frozen、只读、snapshot-local 的 observation。
它按现有 authority/source/ref 顺序保留：

- relationship subjects、两个 endpoint directions、concrete conditions、ordered
  equality correspondences、directional match guarantees 及完整 direct-candidate
  buckets；
- relation-binding occurrences、JOIN uses、VIA step uses、direct/explicit paths 与
  path analyses；
- concrete/non-concrete JOIN regions、binary JOIN occurrences、两个 slots/uses、
  joined outputs/fields、match pairs、fanout、survival、null-extension、outer
  barrier 与 `NULL_EXTENSION` property；
- base/JOIN relational outputs、fields、value classes、candidate keys、value FDs、
  FD indexes、intrinsic grains、active factor identities 与 grain dependencies；
- aggregate fact occurrences、home/JOIN localities、contextual grains、multiplicity
  exposures、actual candidates、common-grain buckets、alignments、chasms 与
  non-concrete multi-fact subjects；
- Phase-62 verification、base verification、combined reverse-use/topological order、
  nulling provenance、fact-locality index 与 multi-fact alignment index。

每一 section 必须 object-for-object 对应 exact bundle/root。name matching、value
equality substitute、ref-position-only substitute、sorting、deduplication、hash 或
重构对象都不能满足 runtime closure。直接 authority 顺序与派生 topological
顺序分开保留。

Summary counts 只是 observation，不是 identity 或 semantic authority。

## Winner-free typed queries

Private query 仅接收 exact typed runtime identity/ref，并返回完整 canonical tuple。
范围包括 relationship declaration/direction、`ProjectJoinUseIdentity`、
`ProjectIRBinaryJoinIdentity`、四种 Project IR ref、field nulling provenance、
aggregate fact/localities、locality-related alignments、exact pair bucket、alignment
common-grain bucket、locality chasms，以及 non-concrete JOIN-use/JOIN-region/
multi-fact why-not subjects。

Project IR/fact refs 必须属于 inspected snapshot scope；跨 snapshot ref fail closed。
Query 不是 resolution，query result 不是 semantic authority。不得加入 free-form
query language、name resolver、`get_best_path`、`get_join`、`get_alignment` 或任何
以 first item 充当 winner 的 API。

## Portable document

Portable owner 只导入 Python standard library，format marker 固定为：

```text
pietto.phase62-inspection.v1
```

Runtime scope token 永不序列化。`ProjectPhase62PortableRef(domain, position)` 使用
closed document-local domains。`plan_node`、`output_value`、`input_slot`、`use`
保留显式 Project IR positions；其余 positions 只是 canonical section coordinates。
所有 occurrence-owning records 仍显式携带 module/declaration/JOIN/path/fact/locality
identity facts。bare integer 不是 typed ref。

Document 采用一个 closed section order：header/summary 与 Project topology，随后
relationship、traversal、relational properties、JOIN、multi-fact、analysis，最后
`end`。Direct semantic sections 保持 authority order；只有 analysis topological
section 使用派生顺序。

Pure values 只有 text、bounded non-negative integer、boolean、closed enumeration、
typed ref、ordered tuples 与 explicit absence。文本编码显式处理 separator、escape、
control characters 与 surrogate code points。

## Pure total evaluator

`evaluate_project_phase62_document(...)` 对 exact portable document 总是返回：

```text
OK + canonical bytes
```

或 closed normalized rejection 加 numeric record/field coordinates。Rejected outcome
不回显 supplied text，也不暴露 bytes。

Evaluator 校验 header/end、marker、record/field/value closure、section order、counts、
portable ref domain/density/dangling、relationship correspondence/directions、JOIN
path/two-input topology/matches/joined-field nulling、key/FD/grain local refs、fact
ownership/locality/exposure、complete common candidates、alignment/chasm participants，
以及五类 Slice-13 analysis equality。

这些是 portable structural consistency checks，不是另一套 relationship、key、FD、
grain、fanout、chasm 或 alignment semantic compiler。

## Canonical bytes 边界

Pure owner 只有一个 canonical document encoder。Runtime inspection owner 仅投影并
委托 pure evaluator，不含 byte encoder、JSON serializer、deserializer、parser 或
schema export。

Freeze：canonical bytes are not identity。具体而言：

```text
canonical-byte equality
!= Project IR identity
!= relationship identity
!= JOIN identity
!= fact identity
!= semantic equivalence
!= alignment proof
!= persistent/cache/content identity
```

不同 snapshot 在 explicit coordinates/facts 相同的情况下可以生成相同 bytes；其
runtime refs 仍不相等。显式 coordinates 改变则 bytes 改变。不得加入 digest、hash
identity、registry 或 persistent cache。

## Determinism 与 isolation

Inspection、query、projection 与 serialization 不修改任何输入对象，不分配新的
Project IR/relationship/JOIN/fact runtime identity。结果不依赖 environment、cwd、
locale、clock、randomness、hash seed、global registry、filesystem、network 或 mutable
cache。

Slice 13 `project_bag_null_oracle.py` 保持完全在 inspection root/document 之外；
oracle cases、output bags 与 hard assurance bounds 都不被 inspection 或序列化。

## 非目标

Slice 14 不增加 semantic derivation、verification/invalidation 行为、path resolution、
JOIN/grain/multi-fact classification、grammar/AST、joined scalar namespace、
aggregate-over-JOIN、reaggregation/algebra、Script IR/SQL、CLI/JSON/Project Explain、
public schema、persistent storage、optimizer/rewrite、recursion、package/dependency/
workflow 或 version 行为。

Slice 15 独占 real authored E2E、Python differential compatibility 与 metamorphic
JOIN assurance；本 Slice 不开始 Slice 15。

## Changed-path 与验证封口

Fixed-point reader closure 为 A4/M5/D0，共 9 paths：

```text
docs/roadmap.md
docs/spec/phase62-slice14-private-inspection-winner-free-query-pure-canonical-boundary-v1.md
docs/status.md
src/pietto/_project/project_phase62_inspection.py
src/pietto/_project/project_phase62_pure_boundary.py
tests/test_active_phase_lifecycle.py
tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py
tests/test_phase62_slice14_private_inspection_winner_free_query_pure_canonical_boundary.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

最终 authority validator 只有一次：

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Publication 使用一个普通 non-amend commit `Add Phase 62 private inspection`、一个
fast-forward push，以及自然 exact-head CI；不 dispatch、rerun 或 cancel。

## Failed-head CI interpreter portability continuation

原始 Slice-14 review repair root 保持原样：“portable projection 对少量既有
authority 仍不够完整（endpoint/binding identity facts、why-not reasons、
verification header），且 pure JOIN topology 可再封闭两个遗漏关系。”该 repair
已在 failed parent 中完成，不在本 continuation 中重开或修改。

Failed publication authority 为：

```text
commit f688a84972696c009994849688cf9348f7398983
tree   87ed4473c6071cfd520051c58a03adb93f26cd58
CI     33585654081
       push/main
       attempt 1
       failure
```

Python 3.12 与 Python 3.13 都只在 Slice-14 hash-seed/cwd subprocess assurance
失败；CI 的 uv project environment 位于 runner temp，因此仓库内没有
`.venv/bin/python`。Additional root 精确冻结为：

```text
SLICE14_HASH_SEED_CWD_ASSURANCE_HARDCODES_REPOSITORY_DOT_VENV_INSTEAD_OF_ACTIVE_INTERPRETER
```

Repair child 只把 focused determinism test 的 subprocess interpreter authority
从 repository-local `.venv/bin/python` 改为执行当前 test process 的
`sys.executable`。Hash seeds、unrelated cwd、`PYTHONPATH`、environment isolation 与
canonical-byte assertions 全部不变；不创建、查找或推断第二个 interpreter。

该 child 不改变任何 production semantics。Phase-62 inspection runtime authority、
winner-free query、portable document、canonical bytes、pure stdlib-only boundary 与
BAG/NULL oracle isolation 均保持 byte/behavior zero-delta；Slice 15 未开始。

Continuation child changed-path closure 为：

```text
docs/spec/phase62-slice14-private-inspection-winner-free-query-pure-canonical-boundary-v1.md
tests/test_phase62_slice14_private_inspection_winner_free_query_pure_canonical_boundary.py

A0/M2/D0
```

Operation ledger 不重置：

```text
original repairs:                         1/1
additional CI-portability repair:         1/1
cumulative repairs:                       2/2

original local authoritative validators:  1/1
continuation child validator allocation:  1/1
cumulative local authoritative validators after child validation: 2/2
```

失败 parent 与 CI `33585654081` 保持不变，不 amend、force-push、rerun、dispatch、
cancel 或改写历史。Continuation validation 成功后只允许一个普通 child commit、
一次 fast-forward push，以及该 child 自然产生的 exact-head `push/main` attempt 1。
