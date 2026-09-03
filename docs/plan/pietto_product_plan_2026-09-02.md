# Pietto 产品规划历史快照
**快照日期：2026-09-02**

> 本文记录 `2026-09-02` 当日的 product/roadmap 视图；在 repository
> architecture authority extraction 后，它仅是 historical planning evidence，
> 不是 current implementation authorization，也不是 competing roadmap。
> Durable architecture authority 位于 [`docs/architecture/`](../architecture/)，
> current phase-level ownership 位于 [`docs/roadmap.md`](../roadmap.md)，exact
> phase/slice authority 位于 current published [`docs/spec/`](../spec/) contracts。
> [`docs/status.md`](../status.md) 仅是 lifecycle summary；publication/lifecycle
> authority 是 live Git + natural exact-head CI；[`AGENTS.md`](../../AGENTS.md)
> 仍是 repository working authority。下文的“当前”均表示该快照日期的状态。

## 1. 产品定位

Pietto 是 gradual / semantic SQL authoring DSL 与编译器：

```text
.pietto
-> ANTLR
-> AST
-> semantic facts
-> Project logical authority / Project IR
-> Query Block IR
-> ProjectSQLPlan
-> dialect SQL AST
-> SQL
```

数据生态方向：

```text
completed query authority
-> PiettoResultContract
-> Arrow schema / RecordBatch / stream
-> pandas / Polars / NumPy / SciPy / Matplotlib
-> RDKit / geospatial / DLPack / device adapters
```

1.0 核心建议定义为：

```text
read/query/analytics semantic compiler
+ optional explicit execution
```

它不是 DBMS、transaction manager、job scheduler、general Python runtime、DML/DDL/migration framework、cross-database federation runtime 或 full physical execution engine。

## 2. 长期架构原则

### Identity / authority

```text
name != identity
alias != identity
binding != declaration
use occurrence != declaration
semantic field != output occurrence
semantic field != SQL alias
semantic field != Arrow field name

relationship declaration
!= relationship direction
!= traversal path
!= authored JOIN use
!= binary JOIN node

candidate key != row uniqueness != Value FD != grain

canonical bytes != semantic identity
cache key != occurrence identity
runtime handle != semantic identity
```

禁止 hidden winner：first/latest/shortest/nearest/best。

Lookup 保留完整 candidate bucket：

```text
0 -> ABSENT/UNKNOWN
1 -> CONCRETE
>1 -> AMBIGUOUS
```

`not proven != false`，`unknown != zero`。

### 分层

```text
AST
Semantic Authority
Project IR / Query Block IR
ProjectSQLPlan
Dialect SQL AST
Execution Plane
ResultContract / Arrow
Ecosystem Adapter Plane
Optimizer / Physical Plane
```

任何下游层都不能重新决定上游已确定的 semantic authority。

还应持续保持：

```text
normative fact != compiled index
interface != capability
semantic requirement != optimization hint
semantic construction state != runtime resource state
cache != authority
inspection != resolver
optimizer != path/name resolver
```

Compiler core 默认无 network/database/credential/transaction/ambient plugin authority。

## 3. Product/Phase Initiation Gate v3

Phase 63 Slice 1 已正式冻结 30 项 Phase 启动 Gate：

1. live authority
2. user/product outcome
3. semantic reference model
4. identity model
5. construction states
6. proof posture
7. layer ownership
8. dependency direction
9. versioning/migration
10. target requirements vs capabilities
11. interchange
12. execution
13. resource lifecycle
14. security/trust
15. algorithms/data structures
16. complexity
17. invalidation
18. cache
19. concurrency
20. diagnostics
21. inspection
22. UX
23. conformance
24. differential/fuzz
25. packaging
26. support matrix
27. release/deprecation/EOL
28. readiness/exact deferred owners
29. Slice route
30. repair/stop conditions

任何 `NOT_APPLICABLE` 必须给 exact reason + exact owner。

## 4. External Product Reference Review

每个 Phase Slice 1 应选择真正相关的成熟系统做 subsystem-specific review，并记录：

```text
Snapshot/date
Problem/constraints
Semantic/identity model
Layering/dependency direction
Algorithms/data structures/complexity
Interface/version/capability model
Testing/operational lifecycle
Pitfalls/migration costs
Disposition = ADOPT / ADAPT / REJECT / DEFER
WHAT_NOT_TO_COPY
Pietto owner affected
```

Phase 63 Slice 1 已审计：
LLVM/MLIR、PostgreSQL、Calcite、DataFusion、Substrait、Arrow、ADBC、SQLAlchemy、Malloy、Cube、Android stable AIDL/VINTF/CTS、OpenHarmony/XTS、MLIRSmith、SynthFuzz、Differential Query Plans、SQLancer++。

长期经验：
- MLIR：multi-level IR、legality conversion、interfaces、analysis invalidation。
- modern DB：query block、logical/physical separation、typed metadata。
- Substrait：semantic requirement vs optimization hint。
- Arrow：typed interchange + explicit lifecycle。
- SQLAlchemy：compiler/dialect/executor/connection 分层。
- Malloy/Cube：nested relation、explicit path、multi-fact alignment。
- Linux VFS：name/object/handle/cache separation。
- Android/OpenHarmony：versioned interface、required/provided capabilities、component evolution、conformance、least privilege。

## 5. Arrow 的正式产品位置

Arrow 已正式进入 roadmap，但：

```text
Arrow compatibility != automatic compatibility with every Python package
```

Arrow 主要解决：
- typed tabular/columnar data
- NULL bitmap
- nested List/Struct
- RecordBatch / stream
- cross-language ABI
- some zero-copy

Arrow 不自动解决：
- RDKit Mol semantics
- arbitrary SciPy function lowering
- Matplotlib semantics
- GPU tensor interchange
- database execution

因此未来有三条边界：

```text
Arrow -> tabular/nested
DLPack / Array API -> dense tensor/device
Domain adapters / Arrow Extension Types -> RDKit/geospatial/sparse/etc.
```

关键 law：
`Arrow field name != Pietto field occurrence`；
`Arrow List<Struct> != NestedRelation semantics`；
Arrow metadata 不能成为 key/grain/lineage authority。

## 6. 发布路线

```text
Phase 66 -> internal/TestPyPI developer preview
Phase 69 -> public PyPI alpha
Phase 76–80 -> practical beta
Phase 81 -> release-candidate evidence
Phase 82 -> 1.0-rc freeze
Phase 83 -> stable 1.0.0
```

1.0 不等待 optimizer、incremental、Rust 或 Phase 90。

## 7. Future Roadmap v6

### Phase 63
Joined Query Block semantic completion and QUALIFY。

### Phase 64
Flat relational algebra：
generic `JOIN ... ON` / refinement、CROSS/RIGHT/FULL/SEMI/ANTI、DISTINCT、UNION/INTERSECT/EXCEPT、single-match enforcement。

### Phase 65
Target-neutral ProjectSQLPlan、parameters、source maps、legality/capability requirements。

### Phase 66
PostgreSQL/MySQL baseline multi-relation SQL + Project emit-SQL。

### Phase 67
Arrow interchange foundation + PiettoResultContract：
schema/type mapping、RecordBatch/stream、PyCapsule、copy/lifetime/device boundary。

### Phase 68
Explicit executor SPI：
ADBC/DBAPI、connection/statement、parameters、streaming、cancellation、backpressure、credential boundary。

### Phase 69
Public alpha release engineering：
TestPyPI/PyPI、metadata/license、support matrix、SBOM/signing/attestation、safe entrypoints。

### Phase 70
Open/composite plans：
nonrecursive CTE/subqueries、VALUES/table functions、outer captures、EXISTS/IN、LATERAL、bounded decorrelation、effect/volatility authority。

### Phase 71
NestedRelation / Collect / Unnest / flatten：
outer/inner grain、relative inner grain、NULL vs empty、cardinality、BAG、ordering、nested Arrow。

### Phase 72
Advanced equality/types/nullability + temporal/range/ASOF relationships。

### Phase 73
Aggregate algebra/state、grouping extensions、fanout-safe/symmetric aggregate、reaggregation、automatic grain repair。

### Phase 74
Reusable local semantic assets、derived relationships、function/plugin SPI、adapter conformance。

### Phase 75
Formatter、LSP、editor、diagnostics UX、syntax editions/migrations。

### Phase 76–79
深度数据库适配：
- 76 PostgreSQL
- 77 MySQL
- 78 SQLite
- 79 DuckDB

### Phase 80
pandas / Polars / NumPy / SciPy / Matplotlib interoperability。

### Phase 81
高强度 assurance：
real DB、SQLLogicTest-style differential、TPC-derived corpus、metamorphic、mutation、fuzz、constraint-guided data、plan-diversity、TLP/NoREC/DQP/CODD-style oracle、performance budgets。

### Phase 82
Public schemas/API/CLI/syntax/support-matrix freeze，1.0 RC。

### Phase 83
Stable 1.0 audit + publication。

### Phase 84
Remote assets / registry / transport / signing / trust。

### Phase 85
Dependency solver / canonical lockfile / reproducible resolution。

### Phase 86
RDKit / geospatial / sparse / DLPack / PyTorch / JAX / CuPy adapters。

### Phase 87
Catalog / constraints / statistics / runtime data-quality / chase。

### Phase 88
Logical optimizer memo + join-order/hypergraph search。

### Phase 89
Physical strategies：
Yannakakis、WCOJ/Generic Join、Free Join、Predicate Transfer、Diamond Hardened joins 等。

### Phase 90
Profiling-driven Rust kernels：
profile real corpus、pure hot kernels、typed FFI contract、Python reference、PyO3/maturin、differential parity、panic isolation、cross-platform wheels。

不进行 whole-project Rust rewrite。

## 8. Tentative post-90

```text
91 persistent incremental-cache identity + incremental/differential Project IR
92 recursive relations/fixpoints/iterative planning
93 formal rewrite certification
94 cloud/federation
95 DML/DDL/migrations
96 governance/security policy semantics
97 continuous/streaming query semantics
```

## 9. 算法方向

现在/Phase 63+：
- immutable stage environments
- hash/trie lookup
- complete 0/1/N candidate buckets
- arbitrary-width bitsets
- antichain/frontier
- incident-indexed worklists
- union-find + proof forest for unconditional equivalence
- Kahn scheduling
- Tarjan/Kosaraju SCC
- typed arena/refs
- provenance/source-map DAG

SQL lowering：
- legality-driven conversion
- capability-set matching
- deterministic alias allocation
- strict literal/parameter/identifier separation

Arrow/execution：
- bounded producer/consumer queue
- backpressure
- explicit resource state machine
- immutable/ref-counted buffers
- selection/dictionary vectors
- cancellation graph

Future optimizer：
- Cascades/Volcano
- DPccp/hypergraph DP
- Yannakakis
- WCOJ
- Free Join
- Predicate Transfer
- Diamond Hardened joins

Incremental future：
- rustc/Salsa-style dependency graph
- DBSP-style differential propagation
- equality saturation/egglog only after rewrite preconditions are formally checkable

## 10. 当前正式状态

Phase 62 final：

```text
commit d9a423fe6822ed549e3063299a4781cd7ed4b480
tree   d0c40f2a644b5cb8cff2fb5390e991ab1ec1ef31
CI     33598904937
success
```

Phase 63 Slice 1 initial publication：

```text
commit e5b790b0b1c516bbeb2aac0833d209afe1b83811
tree   5134d48db2e86d1e09740d6c97937c280c6e3ae6
CI     33690102213
failure
```

失败原因：principal test 在 GitHub Actions depth-one checkout 错误要求 parent commit 可见。

Terminal child：

```text
commit e90e8eb5c3fcee12fb932773959e9b862968776e
tree   d8b54927e1a36840c39f6c693b2aa0cf4d1ce3fc
CI     33693963322
push/main
attempt 1
success
```

Final CI：
- Python 3.12：11188 passed；generated 8/8；goldens 39/39；package smoke PASS
- Python 3.13：11188 passed；generated 8/8；goldens 39/39；package smoke PASS

Lifecycle：

```text
Phase 62 = COMPLETED
Phase 63 = ACTIVE
Slice 1 = COMPLETED / PUBLISHED
Slice 2 = NEXT / NOT IMPLEMENTED
```

`docs/status.md` 仍保留 pre-publication `Slice 1 = CURRENT / PUBLICATION CANDIDATE` wording；live Git + natural exact-head CI 才是 publication authority，不应单独做 status-only commit。

## 11. Phase 63 frozen 16 slices

1. Product Gate v3 / external audit / Future Roadmap / route lock — COMPLETE
2. Query-block owner bridge / row-source sum / states / mode boundary — NEXT
3. Scalar-reference environment / resolution facts / type-kernel adapter
4. Bindings / visible joined fields / qualified-unqualified lookup
5. LET / stage namespace lattice / shadowing / alias laws
6. Post-JOIN row semantics / nullability / lineage / property bridge
7. Completion scheduling / effective-output ledger / module propagation
8. Joined row filtering
9. Joined grouping / aggregate / GLOBAL / satisfying / risk linkage
10. Generic window-computation sites / named-window reuse
11. QUALIFY grammar/AST/semantics/property transfer
12. Projection/order/limit/final output/ledger completion
13. Completed project semantic result / public check boundaries
14. Query-block Project IR composition / verification / invalidation
15. Inspection/pure boundary / E2E / differential / metamorphic
16. Completion audit / Phase 64 handoff

## 12. Phase 63 关键 law

- `ProjectDeclarationOccurrence` = project owner identity。
- existing `QueryBlockOccurrence` = source/named-window scope identity。
- 只允许 typed bridge，不创建第三套 query-block identity。
- row source = closed semantic sum。
- correlation 是 future orthogonal capture context，不是 row-source variant。
- NestedRelation 是 relation-valued value；Unnest 后才成为 row source。
- scalar resolution 与 type composition 分离。
- 不创建第二套 JOIN expression typer。
- LET 是 first post-JOIN scalar scope，并保留 sequential/no-forward/no-self/shadowing。
- multi-hop intermediate fields 可参与 structural/property authority，但不自动 name-visible。
- `AUTHORED_JOIN_DEFERRED` 保留 historical evidence，不删除/改写。
- project-wide effective relation-output ledger：每个 owner 恰好一个 concrete effective output 或一个 non-concrete terminal。
- 不创建第三套 normative dependency graph。
- completed joined output 可被 downstream no-new-JOIN FROM 消费，但不自动成为 relationship endpoint。
- generic `JOIN ... ON` 属于 Phase 64。
- joined aggregate 保留 fanout/chasm risk，但 Phase 63 不做 aggregate algebra repair。
- QUALIFY 位于 WINDOW 后、FINAL PROJECTION 前，TRUE-only。
- selected/hidden QUALIFY window computation 使用 generic computation-site bridge，不迁移 existing selected `WindowOccurrenceIdentity`。
- final fields 复用 existing owner/select/output occurrence identity。
- 不发布 partial completed output。
- positive completion 仅 EXPLICIT_MODULES。
- LEGACY_FLAT / PACKAGE_ROOT / single-file JOIN 继续 typed fail-closed。
- JOIN 保持 binary；unary tail 接在 binary region 后。
- Phase 63 不实现 SQL/Arrow/executor/correlation/nested/extra joins/aggregate algebra/optimizer。

## 13. Repository documentation 状态

当前：
- `docs/roadmap.md` 是 current roadmap，但非常大且混合历史与未来。
- `docs/status.md` 允许保留非循环历史 wording，live Git/CI 优先。
- `docs/plan/` 已明显陈旧，独立 phase planning 目前大约只到 Phase 52；不是 Phase 63–90 产品规划 authority。
- 当前最完整的长期产品/roadmap authority 是 Phase 63 Slice 1 route-lock spec + live roadmap。

推荐但尚未发布的 documentation prerequisite：

```text
repository-level architecture authority extraction
```

建议建立：

```text
docs/architecture/product-architecture-v1.md
docs/architecture/phase-initiation-gate-v1.md
docs/architecture/identity-and-authority-laws-v1.md
docs/architecture/layering-and-coupling-laws-v1.md
docs/references/product-design-lessons-v1.md
```

并由 `AGENTS.md` 加简短 pointers。

这必须是已发布 Slice-1 authority 的 documentation-only projection，不能顺便发明新 semantics。

## 14. 工作治理

- 中文讨论；English code/identifiers/paths/commands/diagnostics/commit subjects。
- 正式 Codex prompt 尽量 lean。
- 默认按 live `AGENTS.md` 的 Lean Gate v2。
- bounded self-repair，严格 accounting。
- frozen changed-path closure；no silent scope expansion。
- authoritative Python 3.13 validator before Gate 3。
- natural CI owns final Python 3.12/3.13。
- failed publication head preserve，普通 child repair；不 rerun failed head。
- tests xdist-compatible 或显式 isolate。
- shared repository fact acquisition。
- 避免重复 CLI subprocess / repo scans。
- serial fallback + Python 3.12 compatibility。
