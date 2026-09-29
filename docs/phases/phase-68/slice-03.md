# Phase68 Slice03 — source qualification and minimal PostgreSQL execution

S03 CANDIDATE; completed only after closure。Phase67 COMPLETED，Phase68 ACTIVE；S01–S02 COMPLETED / PUBLISHED。S04 NEXT / NOT IMPLEMENTED / separate dispatch required。
基线 `86ed839878b877f9ea363c146b939cacf23c43ff`，tree `bda78b078699b8c1978cd65a2f5b65b32f8e56ff`，S02 自然 CI36508766895/push/main/attempt1。
本派发 Section 9 是唯一累计预算权威；独立 evidence root 为 `/home/mianliwang/.local/state/pietto/evidence/phase68-slice03-20260929T035616Z`，其中 `pietto-phase68-slice03-ledger.json` 保留所有 starts、失败与校正。闭合 S02/design records 不改写。

## 资格与内部 gate

`S03_IMPLEMENTATION_GATE = QUALIFIED_UNDER_THIS_DISPATCH`。`pietto-phase68-slice03-internal-gate.json` 记录当前 native/source 证据、构造性推理与未来验收的区别。Q 资格通过后本派发直接进入 P，不另开 interlude。

P1 在 PG18.6 / MySQL8.4.12 的实际 component UNION ALL view 上检验 K=`(part,lid)`：两个组件各有自己的 PK，单独 lid 在完整 view 中全部冲突。完整域非空/单射检查不是 sample，也不把 projected value 当 occurrence。显式 alternate ORDER 与 fresh process/session 保持相同 K→payload；同值重复、未投影 hidden 值、重复 source uses、精确大 Int 与 Float signed zero 分开观察。Expiry、replacement、view visibility、role 与 token collision 各自拒绝，manager 对自己的 disposable inputs 封存 DML。

Production `RetainedSourceRequirement` 持有 exact BoundSource、provider/version/revision、显式 registry/view context、token columns、role 及 provider guarantee。实际 admission 在本 attempt 的只读 snapshot 中核查 metadata、view definition、token physical type 与完整域唯一性；同 connection/session 绑定继续接受检查。Registry 与定义并不能认证恶意 provider；持续 immutable token/payload correspondence、完整可见域、跨 reopen 保留与 expiry 责任仍由外部 provider 保证。普通 non-R2 执行不要求 K；本模块也不提供 R2 模式。当前 signed-integer composite admission 是一种方法，不是将所有未来合法 token 限定为整数。

P2 分离原 peer order 与 choice order。ROW_NUMBER/NTILE/navigation 共用一种 choice；RANK/DENSE_RANK/distribution 保留原 peers。原 frame membership 先决定，再在其中调用 native FIRST/LAST/NTH，保留原宽度、NULL/empty 与 native computation；没有 Python frame evaluator。ROWS、RANGE/default、原 admissible offset RANGE 正反向、大 offset、PG GROUPS/exclusion、隐藏 LEAD/post-window filter、原 LIMIT 与 outer page 分别检验。PG rows、PG ADBC 实际 typed binding 和 MySQL native prepared 都运行 nonempty/prefix/empty outer pages；MySQL 已排除的 GROUPS/exclusion 不扩张。

独立 literal oracle 检查实际 SQL/API arguments、metadata、值、Float bits、联合选择、重数和 native terminals。损坏控制涉及 indiscriminate order extension、frame SQL/value、joint values、hidden metadata、physical type、role/domain；仅 populated keys 或 PASS flag 不足。实验 SQL 仍属 test-only，未成为 S06 编译器 lowering。

## 坐标与容量的构造性边界

小 fixture 的 8 行不是产品上限。Provider K 需 lawful total order；结构性 continuation 比较完整 key，逐分量显式 NULL placement 与 ASC/DESC，不能以单个新 ROW_NUMBER 或 hidden source COUNT 假设完整坐标总可装入 native Int。

需要 native ordinal 的原函数保留其原合法范围前提；新增 lowering 必须独立证明适用范围或用结构性锚点。ROWS/GROUPS endpoint 可在 anchor 前后按完整 K/原 peer key 寻找原有有界 offset 的 predecessor/successor，RANGE endpoint 使用原 admissible key arithmetic；peer membership 不添加 K。实体组合从 scan K、带 side tags 的 joins/outer absence、branch tags 的 UNION ALL 及原 group/set equivalence keys 推导。等价类 copy progress 仅在原完整输出 payload 已证明等价时计数，并服从原资源/native continuation 范围；不能按 projected hash 消除不同 occurrences。

这是 S06 的构造方向与 proof obligations，不能当作已实现任意基数算法。每一类须有原语义独立 correspondence、容量适用性、完整 producer-use/guard inventory 与 empty/overlap/方向反例；若新的支持族需要另一个通用 query/frame engine，应重新核对受影响 route fit，不能藏进 helper。

## 生产链与交付范围

`project_execution.py` → `project_execution_source.py` / `project_execution_postgres.py` → `project_execution_reader.py` → 原 ResultContract / producer binding / Arrow payload validators。
真实 source 经现有 compile/selected verification/emission 后进入 `prepare_execution`，再显式调用 `PostgresExecution`。执行器不接受任意 SQL、caller transaction、ambient credential discovery 或 generic callback authority。请求固定原 artifact、ResultContract、target/access/isolation、limits 与可选 source requirement；driver/Arrow 仅在调用边界 lazy import。该 profile 拒绝 ambient PG* connection 配置及 SSLKEYLOGFILE，禁用自动 client certificate 选择，显式 password/passfile；平台无法表示的 timer duration 在连接前拒绝。

S03 交付当前 PB 能证明的 builtin Int direct-field scan/projection，含 non-null/nullable、重复值、±(2**53+1)、empty。现有 PB 的 SQLSelect/SQLColumn 路径不接受 SQLRowQuery predicate 或 literal output；因此非空 fixed/native uses 在本 Slice 拒绝，S04 保留 binding 接点、S05 负责一般 producer bridge。原 emission/native-use facts 保持，不插值、不改 compiler SQL，不因 resource limit 增加 LIMIT。

真实 mandatory single-match 负例由原 emitter 以 PIE-B1006/original_enforcement_not_fulfilled 拒绝；执行入口同时扫描完整 single_matches inventory。尚未履行的强义务不能进入 native submission，原 proof applicability 验证保持，S07 负责 guards 实际执行。

每 attempt 新建独占 PG connection/transaction/statement；验证 exact release、role、read-only、stable Repeatable Read 或显式 Serializable、UTF8/search_path。实际 metadata 对应原 ordinal/label/storage/domain；empty 同样完成 metadata binding，不从第一行推断。每批经现有 value/domain/NULL 检查和 managed Arrow batch 后由真实 Arrow consumer 读取。

未知基数只由 native empty fetch 取得 EOF，不回填旧 finite reader expected_rows。恰好 4 个 batch 的 8 行、empty、early close、row budget、late checker/consumer failure、真实 source error、commit-response loss 与 cleanup failure 保留 source/transaction/delivery/cleanup 分层；lost commit response 为 UNKNOWN。配置预算不是结果基数事实。

Psycopg RawCursor 在 execute 时缓冲结果，`fetchmany` 不是 server streaming 或硬 RSS 保证。statement_timeout、owned deadline/cancel_safe 与 connect timeout 提供该 profile 的有界控制；不宣称任意网络故障的硬实时中断。真实 held-lock execute 的 requested/sent/observed 分开记录；native timeout 与 timer 可能竞争。Read failure、commit/cleanup 丢失采用明确标注的注入，不冒充真实 blocking-fetch 取消。所有 controller threads join，own session 关闭由 manager 再观察；primary failure 不被 cleanup 改写。

普通 wheel 包含四个新 private owners，isolated env 中实际 source/installed positive 均消费原生产代码。Core 环境、依赖 metadata/lock、三路线 pins、旧有限 reader 与 public interfaces 不变。S03 没有 template cache、R2 lowering、durable job/store/sink 或 S04 实现。

## 后续路线与 A01–A22

[20位置表](slices.md)给出依赖和完整 A 映射；本次判定 JUSTIFIED_CANDIDATE，不是全期 product proof。S01/S02 成本与本次 P1/P2 成本都计入原位置，不设 S21。

| Owner | 构造/边界与独立证明 | 直接读者和验证成本 |
| --- | --- | --- |
| S04 | typed template/value binding，值敏感 proof invalidation，原 slot/use/native transport；复用现有 emission/value owners | 新 binding→request/PB，合法二组值、非法值/修改容器；不重造 parser；A02/A03/A20 |
| S05 | original output/PB bridge，scan/joins/aggregate/window/ORDER/LIMIT/DISTINCT/SET 与七 scalar 的原逻辑/表示 | 现有 output shape、PB/Arrow/native adapters；每类独立 typed BAG/metadata oracle，超出 field-only 的实质新增成本；A04/A05 |
| S06 | compositional source/output occurrence，coherent tie refinement，original peers/frame membership/native extraction，容量适用性 | plan/verification/selected-hidden-use closure、PB 与 R2；各 recipe family 独立 correspondence/损坏，不能只靠 lab SQL；A05/A06/A13/A20 |
| S07 | 实际 guards 与 proof applicability；相同参数/role/view/snapshot，完整义务与重数 | compiler obligation→execution/submission；违例、hidden/pre-filter uses，默认 fail closed；A06/A07 |
| S08/S09 | MySQL native / PG ADBC，精确 bindings/metadata/terminals，分别带 controls | S03 common request、S05 PB、S07 guards；完整声明矩阵与 native representation/control，不只复用服务端；A04/A05/A07/A08/A09/A16 |
| S10 | source-free executable bundle、independent loader，fresh authority 与版本/member/value checks；共同合同 midpoint | packaging/loader 与三 adapter；原源码 absent、foreign/graft、全部终态；A01/A02/A03/A07/A08/A09/A16/A19/A20 |
| S11/S12 | S02 已测 SQLite/FS profile→durable job publisher、immutable chunks/continuous checkpoint/retention | ledger/store/opened bytes→readers；atomic引用与holes/cut faults；A03/A10/A11/A18/A19/A20 |
| S13/S14 | R1 同代保存结果消费；R2 由 S06 facts+qualified reopen+S07 guards 恢复未捕获部分 | fresh authorization、source/store/frontier；重复/全局/组合原查询与完整历史，不能由两个成功 page 推断；A06/A07/A12/A13/A19/A20 |
| S15/S16 | durable stream/reference cooperative sink；atomic complete-generation publication/lost reply | effect/ACK/conflict、完整generation与notification分开；A11/A14/A15/A20 |
| S17/S18 | admission/backpressure/multi-job/GC；execution extras/recovery installation/compatibility | retention/active readers/磁盘预算与same-wheel四cells；A16/A17/A18/A19/A21 |
| S19/S20 | joint crash/concurrency/equal-guarantee performance，三层 completion/cost audit | 全部 A01–A22；不把局部 feasibility 当最终保证，不转移未完成内容到 Phase69 |

实际 held-lock 观察使用 `pg_stat_clear_snapshot()` 清除本 manager 事务的统计缓存，依据 [PostgreSQL statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)；不是重置统计计数。

## Current-input validation 与 closure

| Check / actual closure | Local action | CI / reuse boundary |
| --- | --- | --- |
| 新四 production owners、helper/cases、实际 fixture/options/control schedule | 当前 focused、typing/lint，当前 Q/P native campaign，独立 checker damages | S01/S02 helpers/pins unchanged 仅复用实现；旧运行不是当前 PASS |
| script inventory / source-test typing inventory / sole mutable lifecycle reader | 当前直接测试 | 原完整 CI collection 无过滤/placement 变更 |
| authoritative Python3.13 | 原 guarded unfiltered validator 的全部六 gates | 两 runtime CI 与 independent collection/coverage 保留；不重复本地等价 partition suite |
| grammar/golden fixtures | NOT_REQUIRED_LOCAL 单独重跑，inputs 未改；inventory 测试当前 | 当前 CI generated/golden 原 gate |
| 新 src package members / build metadata / installed origins | CURRENT_LOCAL 普通 wheel 的实际 S03 installed positive | CURRENT_CI clean core/Arrow cells、SDK9、product120/118、22完整 canonical documents |
| native declared package inputs / current captured replay | NOT_REQUIRED_LOCAL legacy native strict，独立 gate 由现有 CI 执行 | CURRENT_CI fresh PG/MySQL receipts 与实际 installed captured replay；不冒充新 S03 实验 |
| publication/Git implementation | 未改 infrastructure，不需新增 depth-one 命令；真实 shallow CI 原检查仍保持 | CURRENT_CI，原 shallow policy 未豁免 |

Full producing revisions/tree 与最终 reviewed tree 分开记录，documentation-only edits 不改称实验 tree。Shared producer/helper 变化重跑其 dependent cases，纯 checker 纠错仅在观察语义不变时重读 raw。review 按一次完整 findings、累计根因修复和一次 bounded follow-up 执行。

Gate2 exact baseline/tree/checks、Gate3 sole-parent commit/FF/natural push/main attempt1、全部 required jobs/steps/raw-consumers 与 cleanup 均在同一外部记录闭合后，才激活 S03 COMPLETED / PUBLISHED。`.agents/`、`NUL` 是保留例外，不宣称全目录 untracked-clean。不作 status-only 追加提交；不自动启动 S04。
