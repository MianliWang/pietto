# Phase71 Slice23：候选安装、文档与 0.1.7 发行决策材料

状态：`COMPLETED / PUBLISHED`，B8 head `28dc36fdd54b90d406e07a4e82d3c10c2bad5e35`，
tree `b0b8b21e036356afd82e77a8bf90e13f555aa0ef`，自然CI `41518702589` attempt1、19/19。
本片交付安装与发行决策材料；发行状态仍为PENDING_RELEASE_DECISION。
B8 Gate2为24809passed/41skipped、独立收集24850；fresh core/Arrow/CLI、Arrow readiness
及reader、installed result-product136cases/211origins及reader全部成功。
候选wheel SHA-256为`0174e6e76fbf646f50cb4bb59476df27ac39e87ef1aa3e342539706d662b79c7`，
sdist为`0ac1567ab418b8fc3bca801120b06d3e3f21bfc133e841ca365ceccde6b522ee`。

基线是 `6ee4b2b0f35a7eff392755bdaccfff949775cf06`，tree
`45f11ad0a7ffef413c84b57a7c77ab528e765b22`，自然 main CI `41502915403`
attempt 1 为 19/19 成功。本片的产品 source、tests、lock、public exports 和 runtime
contracts 与该基线相同；改动限于 README、当前状态与设计/审阅材料。

## 已实现与仍拒绝的边界

| 表面 | 当前 main 的有界能力 | 保留边界 |
|---|---|---|
| 源码/计划 | EXPLICIT_MODULES 项目中的一层 Collect；closed/captured let、并列集合、分组后显式阶段组合、命名/模块与普通 JOIN 透传 | 单文件、LEGACY_FLAT、PACKAGE_ROOT、多层嵌套与 collection scalar/group/order 运算仍拒绝 |
| 顺序与展开 | Collect 必须有 order by，可含隐藏 nullable 排序键与 Top-K；每个查询最多一个 CROSS/INNER/LEFT Unnest，可保留 sibling collection | 不把 bag、ties 或外连接 placeholder 简化成唯一行或代表行 |
| 目标与执行 | PostgreSQL 18.6、显式 postgres_rows；Int/Bool/finite Text/finite Float/Decimal/Date/Timestamp/UUID child leaves | MySQL/ADBC 与 guarded/refined nested execution 保留连接前拒绝；不改变旧平面路线 |
| source/bundle/results | source-free compiled、typed Arrow ownership/C-data/internal IPC、按真实 parent/child/cell/byte charge 拒绝超限 | 不把 emitted SQL 等同于执行许可；不开放任意 IPC import |
| durable consumers | ordinary save、固定快照的新进程 R1、独立只读 verified_export；parent occurrence 是 checkpoint/ACK 单位 | nested R2/recovery、relay 与 sink effects 保持拒绝；无迁移或新的 workspace 协议 |
| emission interludes | 受检 Int 算术/SUM、JOIN scalar projection、Timestamp UNION、逐 blocker suggestion、批量 --all | error timing 按已有 owner 决定；64 MiB 是完整 batch 输出界限，不是峰值内存保证；目录输出仍限已验证 Linux 路径 |

详细准入以 [execution](../../execution.md#bounded-collect-and-unnest)、
[project/package](../../project-package.md#project-sql-emission)、当前 JSON contracts
及 [unreleased notes](../../release-notes.md#unreleased-changes-following-016) 为准。
S21 的 96 个 native law observations、73 个 PG target families 与有限 S09 controls
各有独立分母；它们不会因这个表格扩大成未执行的 campaign 或新支持承诺。

## 候选核验与证据层

B8 已在自身隔离 worktree、Python 3.13.13 上完成以下核验并封存；实际结果在
Gate 2 收据，随后自然 CI 独立覆盖 Python 3.12/3.13：

- 从最终候选构建 wheel/sdist，检查 artifact inventory、metadata、console/CLI、
  README quick start、项目发射与 fresh core install。另建 fresh `[arrow]` 环境，
  核对 dependency pins、lazy import、installed origin 与确切 wheel bytes。
- 通过既有 installed result-product owner 验证真实 Arrow/nested/IPC 消费及损坏拒绝；
  独立 checker 重读其收据。安装消费者不是原生数据库执行或 PyPI served bytes。
- 对 unchanged runtime closure 明确列出与已接受 B7/native wheel 的成员差异；不把
  新 README metadata 的 wheel hash 冒充旧 native artifact 的 hash，也不声称重跑了数据库。
- 检查 examples/help、支持与拒绝矩阵、完整 collected nodes，运行一次合格主机的
  权威全量 validator。generated/golden 等辅助检查按实际输入闭包和既定 CI 分工执行。
- 完整审阅本批 finding set，修复后封存 exact tree；S22/S23 各一个普通提交、一次
  fast-forward push，只有批次头的自然 CI 成功后才记为 published。S24 在此之后独立审计。

本片核对的是当前候选及其使用说明，不把文档评审当执行证明。README 保留 Python
用户易上手的主线，另说明手写/AI 生成 Pietto 的 fail-closed guardrail；不承诺
证明业务意图或真实数据库内容。README 也区分 published 0.1.6 与 main 的未发行功能。
S08–S19 原候选记录保留，并在头部补齐实际已发布批次身份；S20/S21 状态同步。

## 版本与发行决定

package/CLI version 仍为 `0.1.6`。2026-11-02 13:28（多伦多）的 PyPI JSON 观察为
latest 0.1.6，未占用 0.1.7；GitHub 最近 release 也为 v0.1.6 pre-release。
这只是该时点的可用性观察，不能保证未来版本名仍空闲。0.1.7 version/tag、GitHub
release 与 PyPI 上传均不在本片授权中，没有上传或改写历史产物。

发行前 owner 仍须单独决定版本与渠道、时间、签名/attestation 和失败处理；届时
重新绑定发布分支、候选 artifacts 与版本占用，并核验渠道实际提供的 bytes。
S23 交付的是决策材料，发行状态保持 `PENDING_RELEASE_DECISION`。

## 仅设计的附件

- [Compile-only Python API](python-compile-api-design-draft.md)：Phase75 接收后续实施，
  具体入口/结果/错误与资源合同仍待确认。既有
  `pietto.execution.compile_query(...) -> CompiledQuery` 不变，不新增 public exports。
- [`now()`](now-function-design-draft.md)：UTC statement-snapshot 是待决定提案，
  未实现、不是本版 capability。`concat`、`stddev` 留给后续函数工作。
- `schema --json`、measure/metric、Cube/dbt export 与 Windows CI 已作为未来 phase
  候选写入 [roadmap](../../roadmap.md#future-roadmap-v6)，没有重排阶段或提前实施。
