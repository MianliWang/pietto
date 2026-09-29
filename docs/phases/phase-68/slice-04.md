# Phase68 Slice04 — Typed reusable execution templates and bindings

S04 CANDIDATE; completed only after closure。Phase68 ACTIVE；S01–S03/C01 已发布。
基线 `6d32ece0328d4760645faf2423d38dd2a2ef0c96`，tree `9fc857ac4446c6d07a4ea350e0532ff21510c804`，
parent `069a5bab80bf8fda1ca04f5a08446fb0f2940881`，CI36544619465/push/main/attempt1。
本文不宣称未来 commit/CI 已发生；闭合历史不重写。

## 选择与实际接通

`prepare_template` 消费完整验证后的 live emission 和其 retained compilation context。
`bind_values` 接收完整有序 `(exact slot, exact builtin value)`，复制为不可变 tuple；
`prepare_bound_execution` 接入原 private PG executor，每次执行取得新 request/attempt/连接。
同模板可以保留 A/B，B 之后再次执行 A 不改变 A。参数不进入普通 repr、日志或错误文本。

采用保守全量重建：只复制原 AST，并替换被原 slot 精确拥有的 LiteralExpr.value；
新 syntax image 交给现有 semantic、completed、IR、plan、emission owners。
原 opened source snapshots 是出处证据，不宣称新值曾出现在这些字节中。
不修改原 AST/envelope/artifact，不改 SQL 文本或重新解析 SQL，不加第二套语义解析器。
另一模块独立比较原/新 syntax、完整 slot/native use、owner、结构、值、context 与保留请求；
它不调用 specialization builder 作为 oracle。旧 fixed-original path、public bytes/CLI/JSON 保持原合同。

| 能力 | 当前 owner / 精确输入 | 独立检查与消费者 | 区分性证据 |
| --- | --- | --- | --- |
| 复用模板与值 | `project_execution_template.py`；原 verified artifact、实际 slot、值 tuple | `project_execution_binding_verification.py`；bound request | A/B/A、容器修改、失败后仍可用、foreign/reordered/duplicate |
| 值敏感事实 | 原 semantic/IR/plan/emission；私有 syntax image | 原独立 verifiers + 新 syntax/site correspondence | Int arithmetic/sign overflow、Text length、signed zero、旧 proof/new values |
| 保留义务 | 原 completed single-match requests/conditions/path/hops | 原 proof owners 重新证明，新 correspondence 检查完整 occurrence | RIGHT_LIMIT proof 新 root、未履行 guard 拒绝、path/hop 与 repeated request alias |
| 实际参数 | 接受的值 + verified NativeUse | 精确 slot/anchor/index；原 PG RawCursor | 独立捕获实际 submit；PG reuse/MySQL per-occurrence 纯映射 |
| 窄输出桥 | `project_execution_projection.py`；完整实际 SQLRowQuery | 原 emission verifier + unchanged direct-source correspondence；原 producer/Arrow chain | WHERE/ORDER/LIMIT 保留，computed/foreign/hidden-output/graft 拒绝 |

新生产边界仅上述三个 private modules 和必要 request/native/reader/producer integration。
现有 literal/plan/emission producers、grammar、旧 scalar/operator semantics 无改动。
每个绑定重建其值相关证据；无优化计划 cache、global registry、source-free bundle 或共享资源。

## 实际 eligible sites 与域

| 原 literal tag | 接受的值与 native 表示 | 当前检查 |
| --- | --- | --- |
| Bool | exact `bool`，非 NULL；PG Bool / MySQL 显式 signed 0/1 | Bool 与 Int 分离 |
| Int | exact `int`，Int64；保留超过 binary64 exact integer 范围的整数 | leaf、每级 unary sign、实际 arithmetic interval 与 type anchor |
| Float | exact finite `float` / binary64 | hex identity 区分 `+0.0`/`-0.0`；拒绝 nonfinite、Int coercion |
| Text | exact `str`，Unicode、UTF8；PG 不含 NUL | 实际长度重建，目标 encoding/collation/padding；不 trim/normalize；MySQL NUL 保留原规则 |

这些是现有 SELECT/LET/WHERE/ON 中 classifier 已准许的 builtin leaves；
原 operator/ancestry/domain 限制仍适用。Text literal 本身没有臆造的 VARCHAR 长度上限；
有界源字段域与 bind literal 的实际长度不是同一事实。
七 scalar result contract 不定义七种 literal syntax；Decimal/Timestamp/UUID 不新增参数位。
Untyped NULL 不成为 nullable slot；`None` 不代表缺省值。
LIMIT、frame、window offset/default、type/connector 等 preserved sites 不可通过 slot map 覆盖。
结构变化拒绝旧模板；不变 LIMIT 只保留上界，空结果仍须实际 EOF，不补造 expected_rows。

完整 source/module syntax 对应保留 definition/use 区分；equal-valued distinct slots 不合并。
重复 native use 按实际原 slot 分配：PG 同 slot 同 server index，MySQL 每 occurrence 一个参数。
后者仅是纯 compiler/readiness 证据，未交付 MySQL executor 或 ADBC typed binding。

## 命名验收与证据层次

`tests/_pietto_phase68_slice4_probe.py` 的固定 `VALUES`/`ROWS`/`SQL` 是小型 native manifest/oracle，
`scripts/phase68_slice4_probe.py` 仅显式调用。7 行 owned fixture，查询 role 只读；
source 与 installed wheel 各执行 A、B、A_again、empty、mutated、cancel、consumer_error。
A/B 的 `id > value` 结果不同；完整 typed bag 检查重复、NULL 和 `2**53+1`。
实际 native submit 通过有界观察 seam 捕获，独立比较值/SQL/use/metadata/schema/终态。
空结果保留 checked Arrow schema。值/use/SQL/metadata/rows/schema/context/origin/terminal damage 必须拒绝。
这些 installed-code witnesses 不是 S10 的无源码入口。

纯测试覆盖全部四种 eligible tag、旧 fixed/imported/named sites、表达式域、结构参数和完整义务；
native 产品输出只接 unchanged direct Int source fields。纯 mapping/codec 不标为数据库实测。
S03 原 controls/unknown cardinality/cleanup/explicit profile 和有限 reader 合同保留。

| 检查 | 本 Slice 的证据选择 |
| --- | --- |
| 新 binding/producer/execution、旧 fixed transport、Phase57/C01/lifecycle readers | CURRENT_LOCAL focused + 完整 unfiltered Python3.13 validator |
| 新 PG source/wheel bindings | CURRENT_LOCAL；独立新 campaign 与 producing tree；CI 旧 native 不冒充新 campaign |
| 包内新 private members / installed imports | CURRENT_LOCAL 新 wheel origins + policy-required package smoke；CURRENT_CI 两 runtime installation/SDK/product/canonical |
| generated / golden | 本地 NOT_REQUIRED_LOCAL：实际 producing closure 未变；CURRENT_CI 保留独立 gates |
| legacy native strict/replay | CURRENT_CI exact-head 两目标/两runtime consumer；旧完整 corpus 未改，本地不重复整个旧 campaign |
| C01 observation owner、S01 resource/pump、pins | REUSED_UNCHANGED；新身份/源/安装观察仍 fresh |
| depth-one publication infrastructure | NOT_REQUIRED_LOCAL：没有修改 Git/publication machinery；自然 CI 浅克隆保留原验证 |

## Acquisition handoff 与后续 owner

普通新测试用 core，无新 placement/profile，不增加 worker/scheduler/cache。
兼容 fixture 建造复用现有 helpers；predicate 原始模板用 module fixture；
corruption、fresh identity、relocation/native source/wheel 必须使用各自作用域。
没有新性能 campaign。S10 midpoint 消费准备成本；S19 在联合验收前实施必要整合，S20 audit-only。

S05 仍拥有通用 computed/JOIN/aggregate/window/DISTINCT/SET PB 和七 scalar native outputs；
S06 拥有 compositional R2/tie refinement/peer-preserving lowering；S07 履行 runtime guards。
S04 不提供可变 tie-policy 或 R2 执行；原 target/context/policy 换根不能继承旧绑定。
S08/S09 交付 MySQL/ADBC adapters；S10 交付 source-free bundle/loader；后续持久/恢复/并发职责保持。
20 个产品位置、A01–A22、双入口、三路线、双交付模式不变；S05 必须另行派发。

## 唯一闭环规则

原 session/单写入者，S04 dispatch Section 9 的一个累计账本；不重开 S01–S03/C01。
外部根 `/home/mianliwang/.local/state/pietto/evidence/phase68-slice04-20260929T165647Z`，
所有新 evidence 使用 `pietto-phase68-slice04-` 前缀；失败、原 producing revisions 和所有 starts 保留。
只有 connected acceptance、独立 review/follow-up、当前完整验证、exact sealed tree 的普通 commit/FF push、
自然 exact-head push/main attempt1 CI 全部 job/step/consumer 和资源清理同时闭合，
外部 `pietto-phase68-slice04-final-report-zh.md` 才能激活 `COMPLETED / PUBLISHED`。
本文保持 candidate-era 状态，不追加 status-only commit。`.agents/` 与零字节 `NUL` 保留。
