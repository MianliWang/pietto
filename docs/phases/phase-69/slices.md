# Phase69 route — 21 rows

Phase69 负责公开 alpha 发行工程与统一安全入口（[路线图](../../roadmap.md) Future Roadmap v6 中 Phase 69 一行）。
本路线随路线锁定批发布：路线锁定 COMPLETED / PUBLISHED，head `f93dfc23d9c372146fb48e791e7c9c13f7c53531`，CI38140918564/push/main/attempt1，Phase69 已开始。
下表是覆盖与依赖基准，不授权任何 Slice 开工、合入、验证或发布；每个 Slice 在自己的 Gate 0/1 展开时绑定精确输入、写集、命令、验收与成本。所有者决定见[决定记录](../../decisions.md)。

## 授权组与依赖顺序

所有者已把实施授权扩展为 S01–S21，允许按依赖在隔离 worktree 并行开发，就绪片按既有批次规则合入。S07 之后的三路线现实检查、S11 之后的中点与 S20/S21 的独立检查点继续约束集成和验证；新的公共、信任、预算决定仍须确认。此授权不包含 tag、GitHub release 或 PyPI 上传（所有者 2026-10-11 补充决定）。

- S01 COMPLETED / PUBLISHED，与 S02 同批，head `a7bcb2d7ed4a4c688ce84a68182e70d166a60f4a`，CI38144178777/push/main/attempt1：把 S19 consumer 与 check 的回执目录、审计记录与身份三元组改为显式参数。
- S02 COMPLETED / PUBLISHED，与 S01 同批，head `a7bcb2d7ed4a4c688ce84a68182e70d166a60f4a`，CI38144178777/push/main/attempt1：公开 PostgreSQL rows 执行 alpha（`pietto.execution`）。
- S03 在 S02 之后合入，提供调用方自有信任记录下的查询 bundle（`export_bundle`、`load_bundle`）、显式值与重复调用；它已 COMPLETED / PUBLISHED，head `d5e75e211fbd0d88251306cf206e8604ae50d709`，CI38173790890/push/main/attempt1。S04 public results 与 Arrow batches 已 COMPLETED / PUBLISHED，head `2b8239ab60848dbe7e100344f6bdaf86d2b64a5b`，CI38176914040/push/main/attempt1。S05–S07 已 COMPLETED / PUBLISHED，批次头 `2156ff02c5abdb28747920f0d2cfada38426042b`，自然 CI38221525566/push/main/attempt1；19 个 jobs 与 36 份 required artifacts 的 exact-head 消费检查全部通过。S08–S14 已 COMPLETED / PUBLISHED，批次头 `bf8c13445483158b42e8a8eaea848c07d7025c4a`，自然 CI38276213065/push/main/attempt1；19 个 jobs 与 36 份 required artifacts 的严格消费检查全部通过。S11 后的中点已按 S/H/L/K/Q 复核，S15–S19 按既有依赖继续；S15–S18 已 COMPLETED / PUBLISHED，批次头 `825435eff733db15fc839f1aada57d0d4bbe9c73`，自然 CI38308888475/push/main/attempt1；19 个 jobs 与 36 份 required artifacts 的全部严格消费检查通过。S19 整理与冻结的 `COMPLETED / PUBLISHED` 仅在必要测量和权威验证通过、其普通提交与 FF push 完成、自然 exact-head CI 的 19 个 jobs 与 36 份 required artifacts 消费检查全部通过后成立；此前仍为 candidate。届时本轮 S01–S19 闭合，S20/S21 按所有者决定延期，整个 Phase69 继续 ACTIVE。已批准的 C1/T1 保留手动取消的 first-winner 语义：取消只有先获胜才成为 `CANCELLED`，其后请求不改变已结算终态。S06 的显式连接输入、单一 TCP host、CA 身份校验、关闭连接属性与 OpenTelemetry 已获所有者确认；S07 保留清理超时后的显式重试。S07 三路线现实检查已按本派发闭合：Linux 集成主机的 PG rows、MySQL rows 和 PG ADBC 资格通过，operator compliance 与 native source lifetime 的原有未证明边界保留；本轮以 S19 的上述条件闭合为终点。
- S01–S21 均有按依赖并行实施的常设授权；遇到 BLOCKER、拆片，或新的公共、信任、预算决定即停。
- S07 之后的三路线现实检查已闭合，S08–S14 按既有依赖集成与验证；其候选及开发证据仍不能替代批次最终 Gate。
- S11 中点已闭合；当时 CI health 为 `INSUFFICIENT_EVIDENCE / WATCH`，可比样本为 0，成本记录不完整，alerts 仅作复核线索。S15–S19 继续既有依赖；S19 的 profile 与冻结仍须使用 S18 最终自然 CI，调度与资源政策不因此改变。
- S20 与 S21 各自单独派发。所有者 2026-10-12 明确本轮完成 S01–S19，源码保持 `0.1.1`，S20/S21 留待后续；现有 PyPI `0.1.1` 与 `v0.1.1` 字节不替换。S19 的整理、冻结与验收继续，S20 新发行及 S21 发行后审计等待后续版本与发行决定，当前不据此宣称整个 Phase69 完成。

已获授权的组内，检查点只约束合入顺序，不约束开始开发：组内的 Slice 在自身前置问题已答复后即可在隔离 worktree 提前开发；合入在路线锁定发布之后，按各行依赖成批进行，每个 Slice 仍是一个提交。本次补充授权允许 S01–S21 按依赖并行实施，但不跳过现实检查、中点、每片验收或发行检查点。草稿、早期 worktree、候选或非权威运行本身不构成合入、验证或发布的证据。

| Slice | Outcome | Dependencies |
| --- | --- | --- |
| S01 | Experiments and inventory: public inputs and effects, per-route environment inputs, storage-qualification availability, third-party and release-path review; explicit S19 consumer/check harness inputs | none; integrates after the route lock |
| S02 | PostgreSQL rows minimal safe direct vertical on a clean install: no persistent workspace, first public error surface, caller-declared `schemas`, TCP with SCRAM-SHA-256 | S01 |
| S03 | Trusted live/compiled query bundle entry, exact template/value binding, repeated calls and invalidation | S02 |
| S04 | Public results and Arrow batches: ownership and explicit bounded consumption | S02, S03 |
| S05 | Complete terminal states: early stop, cancellation, deadline, primary/cleanup layering, dropped handles and the complete public error projection | S02, S03, S04 |
| S06 | Public MySQL route with its own profile and no fallback | S01, S03, S04, S05 |
| S07 | Public PostgreSQL ADBC route and the three-route support profile table | S01, S03, S04, S05 |
| S08 | Save I: ordinary save on a v7 workspace under private admission on all three routes | S03, S04, S05, S06, S07 |
| S09 | Save II: crash end, cross-process busy refusal and retirement of the caller's own unpublished generation | S08 |
| S10 | R1 saved-result read without the source | S08 |
| S11 | Read-only verified export; the midpoint follows this Slice | S08 |
| S12 | Same-source R2 recovery; its R2 support notes carry the refinement-page residuals recorded in the parallelism-interlude decisions: refined SQL volume growth is unchanged, refined guard and source-admission scans still use the server-default JIT, and no cost promise is made for wide keys or large data; a request for wider key support returns the window SQL shape and the 10 s limit to the owner | S08, S09, S10 |
| S13 | Complete local publication of ordinary and recovered generations | S08, S09, S10, S12 |
| S14 | Reference cooperative sink: window delivery and relay | S08, S09, S10 |
| S15 | Unified entry: API reference, CLI and documentation consistency, effect table and runnable walkthrough | S02–S14 |
| S16 | Current metadata and version readers with source version retained at `0.1.1` | S06, S07, S14, S15 |
| S17 | Third-party materials and public notes: support table, README execution part and alpha release notes | S16 |
| S18 | Whole public journey joint acceptance and the native campaign on one candidate build | S01–S17 |
| S19 | Phase-end consolidation and freeze after S18's natural CI | S18 |
| S20 | Release of the frozen bytes; separately dispatched | S19 |
| S21 | Audit only: completion, retrospective and handoff; separately dispatched | S20 |

## 超过 21 片时的停止规则

最可能拆分的是 S14（高：窗口交付与 relay 各一片）、S18（高：构建、联合历史与公开面检查一片，同一份字节上的原生 campaign 一片）、S08（中：先 PG rows，再 MySQL 与 ADBC）和 S12（中：参数与只读接受一片，恢复续写与杀进程历史一片）。任何一片拆分都会使总数到 22，超过容量 21：此时停下，出一份只含下表取舍的小决策单交所有者选择；容量不自动增加（[D69.06](../../decisions.md)）。2026-10-10 所有者决定保持 21 片，暂不采用任何取舍。

| 取舍 | 腾出 | 影响与风险 | 谁来定 |
| --- | --- | --- | --- |
| 合并 S03 与 S04 | 1 | 两片在第二轮都是小片 | 所有者在停止决策单中选择 |
| 合并 S06 与 S07 | 1 | 两套真实数据库见证放进一个会话；S07 之后的现实检查随之后移 | 所有者在停止决策单中选择 |
| 合并 S10 与 S11 | 1 | 导出仍是独立入口，但可能被误读为 R1 的一种模式 | 所有者在停止决策单中选择 |
| 合并 S16 与 S17 | 1 | 0.1.0 已完成第三方原文与附注，S17 缩小，合并现在更便宜；2026-10-10 暂不采用 | 所有者在停止决策单中选择 |
| 把 S18 的部分交叉反例前移到 S13、S14 | 0，只为避免拆分 | S13、S14 变重；联合验收仍归 S18 | 所有者在停止决策单中选择 |
| relay 移出本期 | 避免 S14 拆分 | 改变公开范围（D69.01） | 改变已定决定，须所有者另行决定 |
| 撤回只读验证导出 | 1 | 删除 S11，推翻 D69.10 | 改变已定决定，须所有者另行决定 |
| 拆期 | 至少 3 | 改变本期终态（D69.01） | 改变已定决定，须所有者另行决定 |
| 把容量调到 22 | 无 | 改变 D69.06；所有者已说明不自动增额 | 改变已定决定，须所有者另行决定 |

不是取舍：撤回退役自己未发布代的公开路径（它本身不加片）；删去 S01 或 S21（门规则要求它们）；把 S19 并入 S18 或 S20（冻结必须在 S18 的自然 CI 之后，发行必须单独派发）。

## Alpha 范围与已知限制

Phase69 不加公开 Timestamp/UUID 含义（所有者 2026-10-11 决定）。项目源的 shape 里只要有 Timestamp 或 UUID 字段，项目模式 SQL 生成就报 `PIE-B1004`（`logical_temporal_or_uuid_meaning_missing`），即使查询不用该字段。
S15 的 API 参考、效果表与 walkthrough，以及 S17 的支持表与 alpha 发布说明都写明这一限制；公开含义归 Phase69 之后插入的一期。

## 公开前提与支持边界

以下措辞由所属 Slice 写入公开文档与架构文档；路线锁定本身不改这些文档。

- 调用方只声明 `schemas`：每次调用绑定已编译查询自己的来源，并检查每个来源的 schema 都已声明；调用方不列来源关系。`schemas` 是调用方的前提声明，不是授权或表级授予；凭据与 provider 能力不从环境推断。
- 早期 PostgreSQL 部署只支持 TCP 加 SCRAM-SHA-256：socket 目录在连接前拒绝；服务器要求 trust、peer、password、md5 或 GSS 认证时，由 `require_auth=scram-sha-256` 在认证过程中、发送密码之前拒绝；错误与公开文档说明怎样经 TCP 建立 SCRAM 密码用户。
- S02 首次写入（PG rows 公开入口，以及[产品架构](../../architecture/product-architecture-v1.md)层表中的公开入口层），S07 的 PG ADBC 公开路线沿用，S15 的 API 参考与 S17 的支持表汇总。

## 诊断

- 既有 `PIE-P`、`PIE-S`、`PIE-I`、`PIE-B` 诊断的码、消息、顺序与位置不变；路线锁定不新增诊断码。
- 新的公开执行错误使用 `PIE-R` 码（所有者 2026-10-10 决定）。它们属于可有说明地演进的 alpha 接口；每个新码由引入它的 Slice 在[诊断合同](../../spec/diagnostics.md)里写明精确合同：S02 引入首批，S05 补全公开错误投影，S15 核对文档与 CLI 诊断一致。
- 三项文档分类仍未决，路线锁定不改变相关行为、诊断或顺序：单文件 `== null` 比较（如 `ok == null`）、改名或计算的输出列上的 ORDER BY、Decimal 诊断的归属。

## 验证

每个 Slice 或批次的权威验证遵循[开发文档](../../development.md#validation-runner-acceptance)与[验证 runner 接收规则](../../spec/validation-runner-acceptance-v1.md)：规则已发布，目前只有集成主机满足其前提；其他 runner 上的运行是非权威的，不计入也不替代任何 Gate 2 验证。
批次内各片的已安装见证与原生见证，在满足其前提的 runner（目前只有集成主机）上对封存的批次头树运行一次，排在权威验证之前（所有者 2026-10-11 决定）。
接收工具与合格环境记录归另行提出的验证 runner 派发：它可与 Phase69 并行，计划须所有者批准，目前没有获批的派发、范围或预算，不属于本路线。

## 延期 owner

- 公开 Timestamp/UUID 含义：Phase69 之后插入的一期。
- Phase53 的四个窗口函数族包装、它们的三个 builder 与 family 参数：S21 之后另行授权的按功能重组窗口，连同经过它们的测试一起删除，最晚在插入的一期开始之前；不是 Phase69 的 Slice。
- binding 层 verifier memo，以及测量缺口（容器内数据库服务端 CPU 与内存、worker RSS、时钟差异）：单独派发的 S21 复盘为它们定以后的 owner、前提与最晚点；S21 不实现它们，也不分配预算。
- 调用方提供 CA 的服务器身份校验与 PostgreSQL rows 的有界读取：放到后续期，Phase69 结束复盘（S21）定以后的 owner 与最晚点（所有者 2026-10-11 决定）。
