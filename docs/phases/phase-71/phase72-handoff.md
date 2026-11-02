# Phase71 S24 handoff — Phase72 readiness

本交接只在[S24 closure rule](slice-24.md#closure-rule-and-write-boundary)满足后生效。
它不开始Phase72，不授权formatter或0.1.7发行。新lead先核对live main、其树与自然CI，
不要只凭这份文档的历史hash行动。

## 可消费的基线

产品与安装基线B8：`28dc36fdd54b90d406e07a4e82d3c10c2bad5e35` / tree
`b0b8b21e036356afd82e77a8bf90e13f555aa0ef`，自然CI `41518702589` attempt1、19/19。
S24只加audit/lifecycle docs；当前public package version仍0.1.6，后续main能力未发行。
B8 wheel0174e6e76fbf646f50cb4bb59476df27ac39e87ef1aa3e342539706d662b79c7与native
wheel4def34258a419219cfad9a192531112e9749535ed4399706e3c42dd3b8f58317的352个runtime
members完全相同，README metadata不同；保留两者的原证据身份。

一层NestedRelation已贯穿显式模块、semantic/IR/plan、PostgreSQL source与compiled
emission、postgres_rows、八类leaf Arrow/内部IPC、ordinary save、新进程R1与独立
verified_export。parent occurrence与child occurrence、count carrier与child ports、
[]与None与真实全NULLchild必须继续分开；collection不是scalar key或可自动flatten的值。
MySQL/ADBC nested、guarded/refined nested、R2/relay/sink、多层nested均继续拒绝。

## 开局顺序与边界

1. 先重新绑定当前Git/CI、writer/worktree、批准范围和预算；沿用
   [phase initiation gate](../../architecture/phase-initiation-gate-v1.md)，消费本审计、
   当前health与工程教训。不要重启已闭合Phase71或把累计失败清零。
2. `pietto fmt`是D71.08规定的71后72前独立步骤，仍需自己的派发；本交接未实施它。
3. Phase72主要接收advanced equality/types/nullability与temporal/range/ASOF关系。
   在其设计冻结前明确bag/sequence equality、NULL/Float意义，不能把现有顺序编码
   或renderer bytes自动当作新的用户语义。每个新公开合同先问owner。
4. owner2026-10-30把concat/stddev放到next phase，并要求now()先设计；将此决定带入
   下一次scope/Gate1，先决定精确语义与范围；本次S24不实现它们。
   [now草案](now-function-design-draft.md)仍未获语义批准。
5. [compile-only API草案](python-compile-api-design-draft.md)只设计，Phase75接收后续
   实施；既有execution.compile_query不迁移。schema --json、measure/metric、Cube/dbt、
   Windows CI保持roadmap已有候选归属，不改排期。

## 未编号延期的主责接收

| 事项 | 主责 / 会审 | 最晚决定点；当前处置 |
|---|---|---|
| 多层collection | NestedRelation semantic owner；type/result/compiled owners会审 | 首个依赖多层的扩展Gate1或设计冻结前，取先发生者；Phase72开局明确仍unsupported，不新增phase号/预算 |
| nested UNION、ordinary RIGHT/FULL carry、nested windows | ProjectSQLPlan owner；semantic/target/result会审 | 对应形状首次准入Gate1前，闭合类型、grain、lineage与lowering；现有拒绝保留 |
| capture let读取另一个capture let | scope/capture semantic owner；SQLPlan会审 | nested correlation首次准入Gate1前；不得从普通capture能力推得支持 |
| child级恢复、nested R2、relay/sink | execution/recovery owner；jobs/result/relay会审 | 对应入口开放的Gate1/实施前先定durable coordinates、effect identity与ACK合同；保留拒绝，无虚构未来phase |
| D-11/D-12整体恢复 | Pietto lead协调既有semantic owners | 未排期恢复责任；在提出相应放宽之前完整审阅。已有定点修复不等于整体完成 |
| G18 / Teach mechanism | Pietto lead；所有者作信任决定 | 当前HOLD；任何机制/marker/rebootstrap变化前重新派发，保持host-only Gate2 |
| 0.1.7渠道发行 | 所有者 / release owner | 版本、tag、渠道、签名/attestation、失败处理及最终bytes逐项授权后；现在仅有决策材料 |

已编号延期保持路线：equality→72，implicit group/list aggregates→73，function/plugin→74，
editor/API→75，PG ADBC/原生array/JSON→76，MySQLnested→77，pandas/Polars→80，
fuzz/high-intensity assurance→81，公开格式冻结→82，optimizer/rewrite→88/93（后者tentative）。
所有这些是owner与回收前提，不是提前准入或预算。恢复后的Claude接收lead协调与交接，
具体layer owner在各自Gate1接受实施任务。

## 必须带走的三条教训

- 用显式cwd、git顶层、Python版本与import origin断言隔离环境。当前事故恢复限制是root
  独占全部工具/落盘，其他reviewer只收冻结文本；没有技术只读证明就不恢复工具型委派。
- public兼容增量要同时关闭所有严格读者；source/compiled/native/installed/data-only
  reconsume是不同证据。新收据不能替换旧失败，也不能把重复执行编成“重读”。
- parent/child/grain与carrier identity必须由所属层提供；current-node profile的parent
  等待和0scope不证明child成本。共享准备保留exact input/lifetime，fresh identity、
  process、ownership与变异反例不能为了速度合并。

## 本机交接入口

证据根为`~/.local/state/pietto/evidence/pietto-phase71-20261026/claude-takeover-20261027/`。
先读TAKEOVER-zh.md和PHASE71-QUEUE-zh.md的最新Codex段，再核对原handoff与所有者回答。
`codex-takeover-20261031/`保留原失败、预算历史UNKNOWN、隔离事故与批准的恢复记录。
B7 native/flat记录在parallel-20261101/b7_root_integration；B8 package、11项profile与
最终health适用性在b8_root_integration；B9自身Git/Gate/CI另有最终收据。
不自动重连Teach SSH，不碰main的.agents/NUL/out_proj2_semi_pg.txt，不触及其他容器。
