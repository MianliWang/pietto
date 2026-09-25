# Phase67：有限结果契约与 Arrow 互操作基础

规划层级 FULL；N67=16。描述性 Stage 目标是建立有限结果交换边界；现有资料没有数字 Stage，故不另造编号。
本次明确联合授权只展开 Slice01：可运行的 CI workload governance、真实隔离 Arrow 实验和耐久规划。
Slice02 产品薄纵向及后续实现尚未开始。包/CLI 保持0.1.0。

## 当前能力与边界

| 能力 | 证据等级／当前状态 | 本期消费 |
| --- | --- | --- |
| 编译、显式 PostgreSQL/MySQL emission 与有限 native result correspondence | Phase66 完成审计／自然 CI 与 native receipts 已观察 | 消费现有 positional identity、类型、NULL、producer representation；不重解语义 |
| private document／完整性／invalidation | Phase65/66 可执行 contracts | 独立 canonical ResultContract bytes；Arrow metadata 只作冗余传输 |
| Arrow ResultContract／batch／产品 reader／生命周期 | 缺失；不是“已有代码即可用” | Slice02–15 建立真实消费者链 |
| Timestamp/UUID meaning | V05 条件性且缺必要 upstream witnesses | Slice07 在首次映射前补足；不能用 Arrow roundtrip 替代 |
| 产品 executor、连接、事务、取消、backpressure | 缺失，Phase68 owner | 本期仅交付结果/绑定/batch 合同与有限完成边界 |
| CI 全量分区覆盖 | R1 已观察，健康历史治理缺失 | Slice01 连接分类、placement、实际执行、覆盖、health 与维护判断 |

使命：将完成的查询语义投影为 target-neutral PiettoResultContract，分别建立 ProducerResultBinding
和 ArrowResultBinding；不通过转换隐藏 producer mismatch。ResultShape nested-ready，但不新增
NestedRelation 语义或第二 scalar solver。优先 RecordBatch／有限 reader，不强制整结果 Table。

## 三层完成验收与回归

- 可观察：声明的有限类型、NULL、顺序/BAG/multiplicity、绑定、生命周期与完成语义均有正反消费者；不能只看 EOF 或 wrapper immutable。
- 已存在：private contract bytes、pure decoder、runtime correspondence、明确依赖/资源界面及安装隔离。
- 已连接：upstream authority → contract → producer binding → Arrow binding/batches → 有限消费与 close；下游不成为语义权威。

保留 parser/AST/source locations、semantic identity、SQL/diagnostics/CLI/JSON、native target assurance、
原全量测试及解释器域。duplicate SELECT labels 仍由 PIE-S2305 拒绝；carrier 的重复 label 不扩语言。
CPU 是当前成功域；device/GPU/DLPack 不在本 Slice。finite finalization 不等于 executor success。

## 范围、成本与风险

必需：固定16-Slice路线、Slice08 checkpoint、每 phase retrospective/lessons；本 Slice 的四分区工作治理、
规范覆盖与 advisory health、真实 hash-locked Arrow 小实验。可选：可获得的 CPU/内存观测；缺失写 unavailable。
排除：src 改动、公开 arrow extra、Slice02 产品实现、数据库采集、调参循环、新 worker pool。

本联合 dispatch 上限：27条实际冻结路径（授权天花板32），A13/M14/D0；诊断6、focused12、
修正6、full2默认1、review/follow-up1/1、两隔离实验环境、每解释器完整 probe≤3、下载≤512MiB、
commit/push1/1、必要 failed-CI child/push/delta-review1/1/1、native verifier≤4。所有成本在同一外部
ledger 分 CI、Arrow、joint-validation 记录；agents、detached heavy jobs、手动 CI mutation、本地 DB 均0。

最多三项风险：报告/历史完整性与信任漂移；借用缓冲区/EOF 被错当语义或完成权威；额外执行与环境同步
超预算。具体 hard/advisory 边界见 [CI governance](../../architecture/ci-workload-governance-v1.md)。
[路线](slices.md)、[Slice01](slice-01.md)、[两轮规划与 Q](planning-notes.md) 是本期 durable owner。
