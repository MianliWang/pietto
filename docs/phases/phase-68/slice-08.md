# Phase68 Slice08 — Private MySQL owned execution and view-source admission

S08 CANDIDATE; completed only after closure。沿用 `phase68-slice08-20261001T062937Z`
及唯一累计账本；原 v2 dispatch、native view-source amendment 与已批准 managed-deployment decision 共同约束本次续作。
原 HOLD、两个稳定事务1→2反例及 UNKNOWN producing-tree 的早期调试观察保留。
S01–S07/C01 的已发布历史不重写；S09 NOT STARTED。

## 已批准的 source 边界

新增 private checked MySQL source admission，不改变 compiler/SQL 的合法性。
合法编译输入仍可能因运行时 source 无法限定而拒绝；原 PIE-B1003 / PIE-B1006、
S07 guarded multi-hop 与 S06 PG window-argument 域不变。
普通执行不要求 R2 K-provider；retention、完整 token 注入性和 choice 仍由原 owners 负责。

SHOW CREATE VIEW 的实际完整定义、schema/name、ALGORITHM、DEFINER、SQL SECURITY、
character-set/collation，以及 server/account/role/database/session/transaction 必须对应。
结构边界覆盖当前 S03/P1 component UNION ALL、S06 retained-key wrappers、
S07 INVOKER/registry predicates、必需 DEFINER 和嵌套 view、旧 native parent/family views。
S01 的 `p68_view` 实际为基表；名字不决定对象种类。

闭合片段为 SELECT 全部投影、单个 named/derived FROM、scalar subquery、WHERE、
UNION ALL、literal/reference、算术/比较/AND/OR/IS NULL、CAST AS SIGNED 和 CURRENT_USER。
CURRENT_USER 按每条 DEFINER/INVOKER 路径保存上下文，不当全局常量。
原生 query 的其他 JOIN/aggregate/window/order/limit 支持仍由原 compiler 决定；
这里描述的是底层 native view 定义片段，不是缩减 Pietto query family。

未知结构、schema-qualified callable、stored routine、loadable function、变量、
volatility/外部或锁副作用、executable comments/hints、未解析/歧义引用、cycles 和
不完整定义/leaf metadata 均拒绝。完整输入与每条 arm/表达式必须验证，不裁剪 false
分支、未使用输出或 LIMIT0。quoted identifier、点号、空格、Unicode、转义和 literal
必须按原生 lexical context 区分；不做关键词黑名单或裸 FROM 扫描。

识别器提出带 token span 的结构，独立 verifier 按每条 production 的终结符及完整
partition、call 分类和有序依赖闭合检查；可共享有独立损坏控制的有限 lexer。
纯记录通过不能创建 live product owner。重复依赖保留位置，immutable object acquisition
只在同一有效 lifetime 内共享。没有跨运行 PASS cache。

总定义 bytes、每定义 tokens、object/edge/depth 都有明确资源边界，并计入现有执行预算。
基表必须是实际 persistent InnoDB；reachable virtual generated expression 要单独闭合，
write-time defaults/triggers 不当 read dependency，也不作为 source 不变证明。

## 已接受的 managed-deployment premise

定义/security lifetime 现在显式依赖 operator 的外部责任声明。默认缺失；声明绑定精确
MySQL access、原 source identities 与发现前接受的 schema 范围。该范围须覆盖所有行政
修改路径、transitive views、base fields/engine、registry 和安全配置；范围外依赖拒绝。
每个 attempt 重新接受声明、取得 native definitions、独立检查闭包并绑定当前 context。
声明不提供定义、依赖、InnoDB、权限、R2 或结果证据，也不是管理员未来行为的证明。

普通 InnoDB 行数据可以修改，仍由实际 RR/Serializable 决定可见性及锁行为。
CURRENT_USER 在 DEFINER 下取该 definer，INVOKER 继承调用者（可能是上一层 definer）；
各调用路径及原生权限检查保持，definition visibility 不授予直接 base-row SELECT。

assurance 分别记录当前结构检查、native context、EXPLICIT_MANAGED_DEPLOYMENT_PREMISE、
NOT_DEMONSTRATED native lifetime protection 和 NOT_INDEPENDENTLY_VERIFIED compliance。
外部责任从 acquisition 前持续到最后一个远端 source use 结束，包含 guards、所有 pages、
取消及 remote quiescence 未确认的情况。local close/cancel request 不是远端终止证明。
迁移流程可暂停新 attempt，等待已有 use 确认结束，再迁移并开始 fresh qualification。
本 Slice 不实现迁移 scheduler；不承诺阻止或在调用前发现非协调/恶意 DDL。
所有实际观测到的不一致仍拒绝后续接受或进度。

object-scoped SHOW VIEW 与必要 metadata visibility 是明确 prerequisite；不会为了验收
增加 blanket base-table SELECT。结构通过后才允许原 source 的 schema/read 查询。
原 catalog 可作旁证，其过滤后空集不作证明。后续 S10/S14 必须 fresh opt-in/revalidate，
不能把序列化 assurance 或旧 live acceptance 重放成授权。

## 完整 Slice 验收

ordinary、guarded、refined、guarded-refined 共用该 source 边界；禁用额外 guard SQL 和
选择 Serializable 都不跳过。保留每个 source/installed origin 的 ordinary50、unguarded
refinement52、guarded54，以及控制与有限 source-law 见证。原 native EOF、close-send、
COMMIT/ROLLBACK、delivery、cancellation、cleanup 分层保持；view proof 不制造成功终态。

当前 focused/native、完整独立 record/denominator/damage、review/followup、全量 guarded
core3.13 validation、exact seal、普通 sole-parent commit/FF push、自然 exact-head attempt1
CI 全部消费者和 owned cleanup 闭合之后，才激活原 S08 PASS terminal。当前未发布。
S10 后续须重新授权/验证该边界，不能持久化 live receipt 充当 trust；S19 保持必要
acquisition consolidation，S20 audit-only。本次不开始这些后续工作。


## 保留的失败及当前 disposition

原两个 hidden-routine/MyISAM 1→2 反例仍为 failed admission。精确8.4.12/26.7.0的
10-case/two-isolation metadata 实验仍为 NO_DEMONSTRATED_NATIVE_DEFINITION_LIFETIME：
SHOW CREATE 后无目标 MDL、并发 DDL 成功；Information Schema FOR SHARE 返回3550。
该 verdict 与两份外部 HOLD 不重写。新的用户决定仅替代 native DDL exclusion 发布前提，
结束本 Slice 的 lock 调查。缺少显式 premise 仍拒绝；有效 premise 接入实际结构检查，
不接受 fail-all 作为交付，也不把本次边界变更记成第四次 planning。


## 已保留的证据预算 HOLD 与续行

此前独立审查复现：协调修改记录的 server UUID、epoch 与 source context 副本时，
checker 未把它们对应到实际 driver 回复。24/24额度处的HOLD及反例保留。用户随后追加8组
修复额度；同一实例上限为32，旧计数不重置，planning仍3/3。

C25已独立核对data/control session、context/epoch实际SQL回复与normal EOF；协调修改、
缺失回复和错绑session均拒绝。data-only记录不创建live authority。当前继续完整source/installed
验收已闭合，保留同一review follow-up及当前full validation/发布条件；S09保持NOT STARTED。

MySQL SHOW CREATE VIEW需要该view的SELECT及SHOW VIEW。嵌套view的metadata权限按对象授予，
底层base table只需本准入查询所需的metadata可见性；不由此授予或执行base-row SELECT。


## 当前原生验收与发布条件

source/installed 各 ordinary50、unguarded refinement52、guarded54，合计312个独立
attempt，经完整重新消费核对484条native statement、278个page及94项实际记录损坏拒绝。
24项控制、10项source-delta、两origin的同版本fresh refinement与4项受影响PG原生用例
均按各自分母闭合。旧RR见证证明并发业务数据提交后旧snapshot不变、fresh attempt读到42；
缺少premise及fresh MyISAM engine仍拒绝。旧记录保留原producing identity，回读只从
同一attempt的实际native回复补足历史副本字段，不产生live authority。

取消/截止见证确实到达native lock wait并送出KILL，但未观察到native取消终态；
transaction保持UNKNOWN。测试observer另行确认session消失，不把它改写成transaction ACK。
reply-loss/cleanup故障注入与实际native事件分别保留；没有新增真实网络黑洞保证。

首轮campaign的ordinary100完整记录可复用；后续fixture切换漏选database的1046失败
保持FAILED，修复后只重采余下212项。外部审计配置/类型/旧格式适配失败也全部保留。
唯一累计账本计数不重置。此合同仅在当前全量验证、精确tree普通提交/FF push、
自然exact-head attempt1 CI全消费者与owned cleanup完成后激活S08完成状态。
S10重查source-free边界，S19保留必要acquisition consolidation；S09仍需独立派发。
