# Phase68 Slice07 — Default runtime guards and same-context checked execution

S07 CANDIDATE; completed only after closure。S01–S06/C01 已发布；S08 NEXT / NOT IMPLEMENTED / separate dispatch required。
基线 `196c3108b887dc2b6ab2417d9ad478ae76b8e818`，tree `f5927814a2b62c88a06bf9c542f14183d4e03a80`，
自然 CI36677611835/push/main/attempt1。当前实例 `phase68-slice07-20260930T081300Z` 沿用同一账本；
原 dispatch Section10、多跳准入 amendment 和明确预算修正共同约束续作。原 HOLD 与失败记录保留。

## 原义务与准备边界

`prepare_guarded` 消费原已验证 semantic/plan roots；`PendingGuardScope` 保留完整且有序的原始
single-match 与 enforcement inventory。`GuardedArtifact` 是独立私有类型，结构验证不授予执行权限。
旧普通/public emitter 和 execution verifier 仍拒绝未履行义务；没有隐式给所有 JOIN 添加请求。

多跳 amendment 只允许已验证 shape 进入闭合的私有 guarded route。无 authored binding-use 的
producer input 保留 `None`，沿原 producer/export/port 对应构造，独立 verifier 重建全部输入。
两种 no-request 多跳控制在旧入口保留原 PIE-B1003 details；其余 operator/type/target exclusions、
原 assessments/proof kinds/warnings、S06 PG structural-argument 域保持不变。

| 原义务或边界 | 当前行为 | 区分性检查 |
| --- | --- | --- |
| direct / exact hop / whole path | 按每个原 request、全部有序 hop/input pair 建立 subject | 重复请求、imports/re-export、首跳/后跳、错序/遗漏/外来根 |
| `ACTUAL_MATCHED_BAG_OCCURRENCE` | 每个 left occurrence 的完整原谓词 TRUE 匹配计数 | 相等 right payload 仍算两次；NULL/UNKNOWN、outer unmatched、SEMI/ANTI |
| 原 right LIMIT0/1 / GLOBAL | 独立验证原静态界，可不提交 match guard SQL | 原 proof/root/hop 与实际 binding；后置 LIMIT 不替代 |
| 依赖 source/relationship 的事实 | 当前保守执行完整 runtime match check，不按 constraint 名称免除 | 声明关系事实与实际重复源不符仍违反 |
| WHERE / QUALIFY / DISTINCT / LIMIT0 | guard 仍针对原匹配边界和完整 input terminal | 后置消除不能隐藏违反；refined 第一页外违反也拒绝 |
| no obligation / forbidden guard SQL | 无义务和适用静态证明直接走原 data；有 pending 且禁止额外 SQL 则提交前拒绝 | 不把关闭 guard SQL 当作关闭 source/context admission |

## Guard 与 data 的同一性

普通 guarded execution 不要求 R2 K-provider。它将原 source/producer、完整 guard 和 data 放入
同一条已独立验证的原生 statement：PostgreSQL 使用 materialized CTE；MySQL 使用保留 BAG 的
window barrier。guard 检测第二个实际匹配，不以输出唯一性、payload DISTINCT 或隐藏 data LIMIT
代替。状态 channel 先于 data；违反时仍可有服务端计算，但不授权公共输出。

显式 S06 refinement 才允许单独 guard statement。它复用完整 source vector、原 producer choice、
pre-attempt tie policy 和原 S06 CTE，随后在同一事务中分页；guard 不受 page frontier/size 限制。
`Enumeration` 在请求页和推进 progress 前核对本次仍存活的 fulfillment。新 attempt 重新履行，
不导入旧 receipt。普通 tied subject 与两个合法 tie 次序的 test-only contrast 分开记录。

`project_guard_verification` 从原 roots 重建完整 subject/condition/input/parameter 对应，逐项检查
SQL 字节和 typed uses，不调用新的 guard renderer/lowerer 作为 oracle。S04 binding 的 A/B/A、
四种值叶与 caller-container mutation、S05 七 scalar/真正 empty schema 均由原 owners 消费。

MySQL shared materialization 的计算列或 source Text 投影可报告 native type252/BLOB flag；
私有 guarded output 仅在原 column/root/source-field identity、已认可的 Text storage、collation309
和完整 scalar requirements 同时匹配时消费该真实 metadata。源表 admission 与旧入口不扩域，
不把252伪写成253。普通/refined 四叶及较宽 source VARCHAR 分别覆盖原生结果路径；
相同逻辑 Text 不代表两条路径的原生 type code 相同。

## 实际执行与终态

`GuardedExecutionRequest` 连接私有 PostgreSQL executor；默认执行 pending guards。
`GuardContext` 绑定本次独占连接、原请求、role、只读 stable/显式 Serializable、source schema、
本地 transaction identity 与服务器 xid。昂贵检查后和下一次 native/public/page 接受前再检查
context、取消和 deadline。同连接 COMMIT/BEGIN 或 SET ROLE 也不能继承旧 fulfillment。

`GuardRun` 保留 PENDING/STATIC/RUNNING/FULFILLED/VIOLATED/UNKNOWN；状态、native uses、
值和 receipt roots 不能被同形对象替换。guard SQL、参数、metadata、结果和内部 buffers 计入原
request limits。原生错误、缺失 header、不完整读取、取消或 deadline 均不证明成功。
source EOF、delivery、COMMIT/ROLLBACK ACK/UNKNOWN 和 cleanup failure 保持分层。

MySQL-native / PG-ADBC 当前通过明确 test transports 接相同 planner、独立 verifier、guard
consumer 和 S05 binder；`ObservedGuardRequest`/data-only replay 不能生成 PG 执行权限。
这些 native 观察不宣称 S08/S09 product executor 或其完整 controls 已实现。

## 当前验收与后续接口

完整 campaign 前必须取得精确输入的 `GREEN_FOR_CURRENT_INPUTS`：全部 fixture 构造、旧入口
控制、native 参数与内部命名、三路线生命周期/metadata drain、ordinary/refined、多跳、取消/
deadline、source/installed、完整 statement/session/worker 与直接 reader/typing 预检。
改变受影响 production/helper/fixture/checker meaning 会使对应 readiness 失效。预检不是完整矩阵。

显式 `scripts/phase68_slice7_probe.py` 串行运行 pinned disposable DB、source 和 installed workers。
literal expectations 来自 fixture 和原 match laws；实际 raw SQL/参数/metadata/完整结果、origins、
全部控制、tie auxiliary session 和 writer 新版本 attempt 由独立 checker 重消费。损坏原始记录副本
必须拒绝，遗漏 denominator 不补 PASS。真实 native fault 与 test injection 分开标记。

S08/S09 接 pending preparation、verified native statement/uses 与仍存活的 guard/result consumer，
实现各自独占连接及 controls；不能把 observed transport 当产品 adapter。S10 独立重建结构 authority，
复核累计 preparation 成本；S14 重新 admission 全部 source/choice，并在新 attempt 重跑所需 guards。
live receipt 不序列化成 durable proof，本 Slice 不冻结未来 bundle/checkpoint 格式。

复用原 compiler fixtures、S01 native/resource owner、S05 scalar/binder、S06 admission/page/终止观察，
保留 fresh semantic roots、source/installed 与 native/mutation 身份。S19 完成必要 acquisition 整合，
S20 维持 audit-only。二十个产品位置、A01–A22 和后续 owners 保留。

完成仅由精确 reviewed/validated tree 的普通提交、FF push、自然 exact-head attempt1 CI 全部
必要 consumers 与 owned cleanup 激活，并写入新外部 terminal。此前仍是 candidate；不预填未来
commit/run，不用 status-only commit 回填，不开始 S08。
