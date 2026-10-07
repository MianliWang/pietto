# Phase68 baseline route — 20 rows

Phase68 ACTIVE；S01–S17 与 C01 COMPLETED / PUBLISHED；[S18](slice-18.md) CANDIDATE; completed only after closure；S19–S20 NOT STARTED。
S03 内部 gate QUALIFIED_UNDER_THIS_DISPATCH；路线 JUSTIFIED_CANDIDATE，后续验收不由本表自证。
上限20；下表是覆盖与依赖基准，不是20片总尺寸或工期已经实验确认。coding单写入者、严格按派发范围串行。

| Slice | Outcome | Dependencies | Acceptance |
| --- | --- | --- | --- |
| S01                                                          | Full initiation and three-adapter premise evidence           | none                    | A03, A04, A05, A07, A08, A09, A16, A21                       |
| S02                                                          | Source-version, durable-store and sink recovery spike; route revalidation | S01                     | A10, A11, A12, A13, A15, A17, A18, A19, A20, A22             |
| S03 | Source/native qualification and common authority; minimal PG execution and controls | S01, S02 | A03, A07, A08, A09, A13, A16, A20, A21 |
| S04                                                          | Typed reusable templates, parameter binding and invalidation | S03                     | A02, A03, A20                                                |
| S05 | General original-output / producer-binding bridge | S03, S04 | A04, A05 |
| S06 | Compositional R2 facts, coherent refinement and peer-preserving lowering | S03, S04, S05 | A05, A06, A13, A20 |
| S07 | Default guards, view/role correspondence and single-match fulfillment | S04, S05, S06 | A06, A07 |
| S08 | MySQL common execution adapter and owned controls | S03, S04, S05, S07 | A04, A05, A07, A08, A09, A16 |
| S09 | PostgreSQL ADBC common execution adapter and owned controls | S03, S04, S05, S07 | A04, A05, A07, A08, A09, A16 |
| S10 | Source-free executable bundle, independent loader and common-contract midpoint | S04, S05, S06, S07, S08, S09 | A01, A02, A03, A07, A08, A09, A16, A19, A20 |
| S11                                                          | Durable job store, compatibility and exclusive job publisher | S02, S10           | A03, A10, A19                                                |
| S12                                                          | Immutable chunks, committed checkpoints and retention foundations | S11                     | A11, A18, A20                                                |
| S13                                                          | R1 saved-result recovery and reauthorization                 | S12                     | A12, A19, A20                                                |
| S14                                                          | R2 same-version extraction recovery and occurrence coverage  | S06, S07, S10, S12, S13 | A13, A06, A07, A20                                           |
| S15                                                          | Durable streaming delivery and cooperative sink commitment   | S10, S12, S13, S14      | A14, A15, A11                                                |
| S16                                                          | Atomic complete-generation publication and lost-reply recovery | S15                     | A14, A20                                                     |
| S17                                                          | Multi-job admission, backpressure, resource tuning and concurrent GC | S10, S12, S15, S16      | A17, A18, A16                                                |
| S18                                                          | Execution extras, recovery-runtime installation and compatibility | S10, S11, S17           | A21, A19                                                     |
| S19                                                          | Whole-matrix differential, crash histories and equal-guarantee concurrency | S14, S15, S16, S17, S18 | A01, A02, A04, A06, A07, A08, A10, A11, A12, A13, A14, A15, A16, A17, A18, A19, A20, A21, A22 |
| S20                                                          | Three-layer completion audit, cost retrospective and Phase69 handoff | S19                     | A01, A02, A03, A04, A05, A06, A07, A08, A09, A10, A11, A12, A13, A14, A15, A16, A17, A18, A19, A20, A21, A22 |

P1/P2 当前资格、20位置完整机制与成本评估见 [S03](slice-03.md)。S02 的 PRODUCT_GATE_BLOCKED_REPLAN / sizing NOT_VALIDATED 是闭合历史；S03 新批准的 source/tie 决定与实测解开其特定前提。
S04/S05/S06/S07/S10/S14 仍为尺寸 watchpoints。S10 重查共同合同与 S/H/L/K/Q，S19 保留联合故障验收。
保留 A01–A22、全部已承诺查询族与目标特定 exclusions；不增加 S21，也不把未交付功能隐移 Phase69。S04 已完成类型化绑定；S05 已接通原 outputs、general producer binding 与七 scalar native results；S06 已接通 compositional refinement / independent verification / bounded pages；S07 已闭合 pending guards / same-context fulfillment；S08 已发布显式 managed-deployment 前提下的 private MySQL execution；S09 已发布有限来源资格与独立 PG managed-deployment 前提下的 private PostgreSQL ADBC execution。S10 已发布 compiled bundle/独立 loader/source-free binding 与两个新 PG route 的共同有限 profile。S11 已发布合格私有工作区、durable job/generation/attempt 身份与独占 publisher epoch 写端围栏。S12 已发布显式 v2 工作区、受检捕获的不可变 chunk、文件先于元数据、围栏下的 committed checkpoint/连续 frontier 与 retention 引用基础。S13 已发布显式 v3 工作区、进程内新鲜已保存结果读取授权、绑定精确 checkpoint 与固定 extent 的 consumer、有界重分批与围栏下的显式本地确认进度；R1 不访问源。S14 已发布显式 v4 工作区、首次捕获前登记的 R2 规格与初始资格描述、新进程显式恢复（新鲜资格与 guard）、从位置 0 的有序重新枚举与 occurrence 对账、全部旧岛屿匹配前的候选屏障、围栏下补洞与后缀续写及多 attempt 成员。S15 已发布显式 v5 工作区、独立持久的参考合作 sink（自身事务内物化精确 typed 行、主键即稳定效果身份、同键异值冲突、查询与同身份重提、有限保留合同）、已采纳不可变 checkpoint 窗口与固定 S13 交付的临时流式交付、发送前提交的本地意图与围栏下的 sink 观察及派生确认前沿。S16 已发布显式 v6 工作区、与不可变 attempt 终态同事务记录的 closing observation、从原始事实重算的完整结果真值表（原始捕获或已对账重新枚举 `[0, N)` 的 S14 continuation 为 closing 基础）、新鲜发布授权、写事务外逐 chunk 复核全部成员、一个围栏事务内的不可变 publication 与发布自有保护、两种 publish/cancel 顺序与丢失回复后查询。S17 已发布显式 v7 工作区、每工作区一个显式有界协调实例、内存与持久资源向量的原子准入与恰好一次结算、文件出现前的 chunk claim、持久下游背压下的固定高水位、独立于数据额度的控制通道与 worker 自记的持久取消、显式未发布代退役、按代共享/独占生命周期租约、持久精确删除决定与目录同步后的移除观察（C16 验证并发越界一次性接受，历史保留）。S18 candidate 接入三个路线 extra（各自 Arrow 加该路线精确驱动）与 `arrow` 的无驱动已保存结果安装、同一 wheel 的干净解析安装来源、所选路线 pinned 驱动在 admission/worker/连接前的命名拒绝与无回退，以及未知信封/已识别 schema/编译代码/新鲜接受四层兼容；完成须当前验收、发布与自然 CI 激活。S19 须另行派发；每次新执行仍须 fresh acceptance/qualification。

S04 acquisition handoff：复用现有 source/compiler fixture、S01 resource/pump 和 C01 text observation；保留 fresh AST identity、source/installed native witnesses。S10 midpoint 检查累积准备成本，S19 在联合验收前完成必要整合实现，S20 保持 audit-only；不删除产品位置或 A01–A22。
