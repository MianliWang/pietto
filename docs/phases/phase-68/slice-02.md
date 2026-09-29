# Phase68 Slice02 — source, store and cooperative sink recovery premises

S02 CANDIDATE; completed only after closure。基线 `5d9645e796a3408e60a4a93ba0b263b8a40b1ef4`，tree `dcb0263270657b03b27d9238869c21f024f09dd2`；S01 自然 CI `36499401981/push/main/attempt1/success` 已由外部 final-state 激活，不重开旧候选历史。

调查结论：`COMPLETE`（须完成下述候选验证/发布闭环）；下一阶段：`PRODUCT_GATE_BLOCKED_REPLAN`。
三路线有限 R2、磁盘进程恢复及合作 sink 前提已取得正例；通用全局查询 R2 的 occurrence/重复执行稳定性仍缺机制决定。S03 NOT STARTED；实现须另行派发。

## Frozen scope and budget authority

首次编辑前冻结 A5/M14/D0 共19路径，详见外部 `scope.json`。新增仅 `scripts/phase68_recovery_premise.py`、两个 `tests/_pietto_phase68_recovery_{cases,store}.py`、principal及本文；修改仅当前政策/Phase68/lifecycle和四个直接inventory readers。
源产品代码、现有 S01/helpers、pins/locks、CI、core和 `.agents/` 未授权修改。没有生产格式、executor、source service、scheduler、public API。
唯一数值预算为本次 ACTIVE dispatch Section 8，原文和累计 `ledger.json` 留在外部根。S01 原12等历史限制不迁移；当前 causal/focused headroom24/24 见该唯一 authority，不重写旧账本。
代理、detached job、并行顶层重任务均未使用。case 内有界子进程和两连接历史不等于后台服务。

## Mechanisms and observations

`tests/_pietto_phase68_recovery_cases.py::MANIFEST` 在首次完整campaign前固定16个命名cases，不做无意义笛卡尔积。普通pytest不导入实验drivers、不发现或启动DB。
fixture manager 用独立字面 SQL 创建6行 v1 输入关系；数据库 trigger 拒绝其 INSERT/UPDATE/DELETE（含manager实际UPDATE负例），query role只有SELECT。DDL和retention仍由隔离manager契约保证，label自身不证明immutable。
fixture的 `(version_id, occurrence_id)` 是源提供的测试身份，不是按值推断的产品隐藏字段。三个相同可见payload、重复key、NULL、`2**53+1`和Unicode/引号均有独立literal oracle。

三条路线均实际执行 `WHERE version_id = parameter AND occurrence_id > parameter ORDER BY occurrence_id LIMIT parameter`：首进程只请求2行，提交immutable片段/SQLite检查点并确认后SIGKILL、reap；manager查询证明原native session消失。
新进程重新建立只读身份，核对同一retained token，读取3、1、0行；最后0是有限扫描EOF。即便driver预取整个页面，也没有请求后4行。恢复前manager另建v2，恢复仍固定v1；expiry/replacement在source reads前拒绝。
实际SQL、native arguments/API、session、driver-specific metadata/EOF、文件提交顺序、原值和终态均由data-only checker核对，不按key数量或PASS字段认证。
三个joined histories分别从自己的source→store→sink上下文闭合，没有拼接不同job。它们不证明恢复旧cursor、任意mutable snapshot或所有SQL族。

真实PG exported snapshot在exporter结束且session消失后，由新进程import得到 `42704 / snapshot ... does not exist`；不用假定的通用异常。两target普通新事务在manager把10改20后读到20，不能自称旧版本。
独立算法反例：严格visible-key `>`漏掉第二个key7 occurrence；按source occurrence推进保留它。`SUM([2,3,5])=[10]`与分块SUM拼接`[5,5]`不同；这只反证朴素拼接。

## Storage and sink applicability

实际 CPython3.13.13 / python-build-standalone BUILD20260602，`_sqlite3`为built-in，没有 `__file__`；SQLite3.53.1 source_id `2026-05-05 10:34:17 c88b22011a54b4f6fbd149e9f8e4de77658ce58143a1af0e3785e4e6475127e9`，与[官方release source identity](https://www.sqlite.org/releaselog/3_53_1.html)对应。[WAL-reset修复依据](https://www.sqlite.org/wal.html#walreset)覆盖3.51.3及以后和注明backports；这里选择实际已安装固定build，不以未复现race作为证明。
workspace实测为 `/dev/sdd` 上的Linux `ext4`，mount含 `data=ordered`；每个参与连接实际WAL/FULL (`synchronous=2`)。所有observed profile与实际compile options保留在raw。OS、虚拟磁盘与device诚实兑现sync仍是外部前提，见[atomic commit假设](https://www.sqlite.org/atomiccommit.html)和[FULL语义](https://www.sqlite.org/pragma.html#pragma_synchronous)。没有物理断电或硬件认证。

实验片段为有限test-only JSON bytes，每片≤1MiB；写完整checked chunk→file fsync→不可覆盖的namespace安装及directory fsync→短metadata transaction→commit→ACK。这是lab实现，不冻结产品durable format。
partial、显式注入fsync失败、已持久orphan、未提交metadata被杀均不提前推进；commit后ACK丢失通过新进程重开找回。missing/corrupt/binding/version/canceled拒绝，1和3的持久chunk/ACK不能跨过2。
两job分离；一个worker在write transaction外等待时，另一job writer可提交；独立reader的旧transaction仍见active，结束后新读见complete。仅机制观测，不声称吞吐改善。
后续必须补exclusive publisher epoch、reader retention、GC引用与配额/控制余量；此处没有通用scheduler/collector。

sink是另一个持久SQLite owner，effect/payload同事务提交。首effect提交后kill丢ACK，job仍无ACK；独立进程查到effect，fresh consumer用同identity重试，最终6个effects且只对首项reconciled。两等值occurrences仍各有效果。
同key异payload、namespace/epoch改变、显式时钟now=100到期拒绝；gap不推进ACK frontier，canceled job不能复活。source EOF、本地commit、generation publication、sink effect、ACK、notification分别归属；UNKNOWN模型保留未观察remote commit，不冒充真实网络故障、XA或任意callback exactly-once。

## Remaining route: preserve all goals, block the unresolved decision

保留原20个编号（含S01/S02），不增加S21、不把多个大功能重命名成一片。S03–S20依赖DAG及原验收归属保留，但整体尺寸 `NOT_VALIDATED`。

| Query family | Candidate R2 mechanism | Exact unresolved boundary / required evidence |
| --- | --- | --- |
| source/projection, imported scan | source-provided retained version + occurrence frontier | S02直接有限scan已证；imports/derived projection仍由S06/S14证对应 |
| JOIN / repeated uses | immutable inputs with complete joined occurrence tuples; evaluate original query | outer/null-extension/multiplicity and guard view need S06/S07/S14 proof |
| grouped/global aggregate | recompute original whole query on same immutable inputs, recover final output occurrences | cannot aggregate chunks independently; group/final output identity and exact arithmetic pending |
| window / QUALIFY | reevaluate original global window on same version | ORDER ties may change LAG/ROW_NUMBER membership; version immutability alone does not fix tie evaluation |
| ORDER / LIMIT | stable total result order and verified replay prefix, then fresh uncaptured reads | compiler ORDER descriptor alone neither guarantees total order nor reproducible LIMIT ties |
| DISTINCT / SET | reevaluate complete operators with their declared equality and multiplicity | UNION/INTERSECT/EXCEPT ALL duplicate occurrence matching pending; no value-based winner |
| typed general outputs / guards | retained compiler facts, actual driver metadata and same-role/view guard reexecution | no first-row inference, no persisted live authority or reduced three-route matrix |

具体待决方案：在现有条件源契约内，先设计“全查询重求值 + 可验证重复执行稳定性 + 输出occurrence/连续前沿”的共用恢复证明，再决定哪些现有语义事实足够、哪些需要额外明确条件。
S02尚无证据表明该方案能对全部已承诺族（尤其tie-sensitive window/ORDER/LIMIT）保持原语义。不能默认添加snapshot keeper、result table、CDC/backup服务；也不能退为只支持scan或R1。
该 `USER_DECISION_REQUIRED / ARCHITECTURE_DECISION` 阻断S03和S11/S12格式冻结；下一dispatch应只解决这一个source/算法边界及其尺寸分配。不是重做Phase-start interview。
S04的值敏感事实、S05独立无源loader、S06通用输出、S07 guards与S14全局恢复均仍是独立watchpoints：S06/S07必须在S14前提供真实identity/view事实，S11不得先猜恢复格式。18个剩余位置仍有明确owner，但未量化的新算法工作不能靠“表有20行”算作容纳成功。

| Requirement | Remaining owners / dependencies | Mechanism / exact boundary | Still needed |
| --- | --- | --- | --- |
| A01 | S05, S18, S19; S04 typed template | trusted source-free bundle; independent loader then fresh authorization; no serialized live roots; both entries remain required | installed source-free execution, tamper/version/role failures |
| A02 | S04, S05, S07; S03 authority | immutable typed values + slot/use map; invalidate value-sensitive facts; seven scalar domains; no generic string binding or retained old LIMIT proof | two bindings and invalid values; container mutation and guard correspondence |
| A03 | S03, S11; S01/S02 gates | explicit query/target/role/attempt identity; exclusive publisher epoch; experimental token is source evidence, not product authority | foreign/stale/grafted objects and epoch race |
| A04 | S08, S09, S10, S19; S04/S06/S07 | same declared matrix with actual native APIs; PG rows, native MySQL, PG ADBC all retained; no intersection retreat | full three-route query/type/isolation/terminal matrix |
| A05 | S06, S08, S09; S03/S04 | upstream output/representation facts to PB/AR; seven scalars, imports/JOIN/aggregate/window/ORDER/LIMIT/DISTINCT/SET | general output derivation and empty schema without first-row inference |
| A06 | S07, S14, S19; S04/S06 | default guards use same values/predicates/role/view; equal occurrences count twice; no weak checked fallback | single-match success/violation; hidden/filtered obligations retained |
| A07 | S07, S10, S14; source/guard binding | stable snapshot default; explicit Serializable; rerun guards on recovery; no downgrade; saved version is not a live exported snapshot | DDL/role changes and controlled conflicts across each route |
| A08 | S03, S10, S19; native query terminals | separate page EOF, source EOF, transaction and delivery; finite S02 page limits prove only unrequested suffix; no fabricated total | late failure, empty batch/EOF, early close, unknown cardinality |
| A09 | S03, S10; fresh exclusive connection | owned statement/transaction cleanup with layered errors; S02 killed process/session witness is finite | construction/read/cleanup combinations, caller-owned transaction refusal |
| A10 | S11, S18; S02 fixed runtime/FS profile | qualified workspace, effective SQLite WAL/FULL and sync protocol; ext4 + OS/device sync assumptions; no power-loss certification | profile admission, quota/control reserve and actual deployment build evidence |
| A11 | S12, S15; S11 store owner | checked bounded immutable chunks then short metadata commit; job checkpoint differs from WAL maintenance; holes never advance | production crash cuts, concurrent epoch protection and orphan handling |
| A12 | S13, S15; S12 | R1 reads saved chunks after reauthorization; only same generation/binding/retention; no source claims | different batch size, canceled/expired/missing/corrupt cases |
| A13 | S06, S07, S14, S19; full-family deterministic recovery decision BEFORE S03/S11 freeze | reopen version; replay/evaluate whole query then verified occurrence frontier; S02 proves only ordered fixture scan; global/tie-sensitive mapping unresolved | approved full-family occurrence/ordering mechanism and genuine uncaptured suffix witnesses |
| A14 | S15, S16; S10/S12/S13/S14 | durable provisional stream then atomic complete generation publication; both modes required; completion never assumes sink ACK | publish/cancel races, lost notification query, incomplete stream |
| A15 | S15, S19; S12/S13/S14 | separate cooperative transactional effects and query/retry; stable namespace/epoch/job/occurrence + payload; finite retention promise | production reference consumer and ACK loss/conflict/expiry histories |
| A16 | S10, S17; route-specific driver control | bounded cancel/deadline, discard owned connection when required; S01 SLEEP and S02 SIGKILL are not universal driver cancellation | blocking execute/fetch, late success, failed cleanup and canceled recovery |
| A17 | S17, S19; S10/S12/S15/S16 | bounded admission/backpressure with short metadata transactions; S02 two-job reader/writer mechanism is not performance result | slow consumer/full quota/control progress with equal guarantees |
| A18 | S12, S17; S11 identity and S15 promises | reader leases/epochs, generation and sink retention constrain GC; S02 retains all lab files; no general collector | reader/GC/orphan/disk-pressure interleavings |
| A19 | S05, S11, S13, S18; trusted input/version policy | private explicit versions, protected bindings and fresh authorization; no credentials/live authority persisted; no automatic migration | old runtime rejection without writes, package/source/role substitution |
| A20 | S03, S10, S12–16; per-layer terminals | attempt history records source/commit/ACK/cleanup separately; saved EOF cannot resolve unobserved remote commit | UNKNOWN preserved across retry and queried local commit |
| A21 | S18, S19, S20; S05/S11/S17 | isolated execution extras, same wheel and installed origins; core remains compiler/Arrow-free; old SDK/product/native contracts retained | four installation cells, SDK9/product120/118/canonical22, current native/replay |
| A22 | S19, S20; S14–S18 | models + real component/process histories + bounded write-loss injection; each joined run consistent; no physical power/XA/exactly-once claim | full promised matrix with independent value/multiplicity and failure oracles |

## Input-sensitive evidence selection

| Check | Actual input closure / change | Current local action / reused origin |
| --- | --- | --- |
| focused behavior, control/store, data-only damages | new probe/helpers/principal plus direct inventories/lifecycle changed | CURRENT_LOCAL, actual child/pump and disk checks |
| Ruff and relevant Pyright | new/changed code | CURRENT_LOCAL; full typing also in authoritative validator |
| authoritative Python3.13 | full repository collection; no changed-test filter | CURRENT_LOCAL, normal six-gate `validate.py`, guard on, resource workers capped4; no second partitioned suite |
| depth-one/import and lifecycle | new explicit script and current owners | CURRENT_LOCAL, core import remains optional-driver-free; actual depth-one candidate export |
| generated / golden | grammar/generated/vendor/golden-producing inputs unchanged; only inventory reader changes | NOT_REQUIRED_LOCAL auxiliary; current full behavior consumers and CURRENT_CI audits remain |
| extra package/core/Arrow installation cells | `pyproject.toml`, lock, `src/pietto`, package_smoke and fixed probes unchanged | NOT_REQUIRED_LOCAL; CURRENT_CI actual fresh cells; S01 old cells REUSED_UNCHANGED context only |
| SDK9, product120/118, canonical22 | SDK two-path closure; product `input_closure()` explicit sources/helpers/package script unchanged | NOT_REQUIRED_LOCAL; CURRENT_CI exact-head consumers and complete report checks |
| legacy native strict / captured replay | native `inputs()` explicit HELPERS, emission probe, pins, metadata/lock, all source members; replay explicit helpers unchanged | NOT_REQUIRED_LOCAL; CURRENT_CI native/aggregate/replay consumers, never S02 experiment certification |
| new source/store/sink histories | producer/store/fixture/runtime/options/fault schedule/checker meaning | CURRENT_LOCAL complete manifest; each joined history one run; docs-only changes do not rerun |

Closure selection is recorded from real declared sets in external `validation-selection.json`; added S02 scripts/tests are not silently assumed independent. CI keeps all current jobs/steps and full collection/four partitions. Current-run artifacts are acquired once only as required by their consumers; old run IDs cannot certify publication.

## Conditional completion

Only the final external record may activate S02 COMPLETED/PUBLISHED after: complete independently checked experiment manifest; consolidated author/Ponytail review and targeted closure; scope/depth-one checks; authoritative full regression; sealed exact tree, ordinary sole-parent commit and FF push; natural exact-head push/main attempt1 all required jobs/steps and current evidence; registered cleanup.
A complete scope-limited investigation with this blocked product gate can publish. Missing facts/harness failures are HOLD, not an adverse-result PASS. Source DBs, credentials and experiment environment are cleaned only after closed receipts; minimal closed stores/chunks, failures, raw observations and wheel/cache references remain. No S03 work follows this terminal.

## Current local evidence binding

独立原始证据根：`/home/mianliwang/.local/state/pietto/evidence/phase68-slice02/20260929T004727Z`。当前完整manifest使用 `campaign-03/report.json`，实际执行tree `2f2b351f5dce30febfb586dcbe315f16b80613f5`；`current-experiments.json`记录独立checker与七个实质report/actual-operation损坏控制。此前thin-postgres、campaign01/02及所有失败保留原tree，未重标为最终执行。
后续仅文档/测试验证记录的变更由最终tree差异核对；全量回归、publication和自然CI事实只写入外部终态，本文不预言其head/run。
