# Phase68 Slice10：Compiled executable bundle、独立 loader 与共同 PG 来源合同

S10 CANDIDATE; completed only after closure。基线为 S09 published head
`bd92c2c9f29d3b47aa94ea7dfcb5a6fe2e564b68`，自然 CI36977540827/push/main/attempt1。
本文只描述候选合同；当前完整验收、精确 Git tree、普通 FF 发布、自然 exact-head CI 的全部消费者和 owned cleanup
共同激活完成。证据属于独立 S10 实例，不合并任何已闭合计数。S11 NEXT / NOT STARTED / separate dispatch required。

## 编译输入与原始规则

`build_compiled` 只从实际已验证的 source artifact、guard preparation 与显式 refinement 导出有限图。
图保存完整 declaration/use/port/field/output/slot 身份、源和参数对应、被保留但未选中的义务，以及所选 target 的完整要求。
`project_compiled_schema` 定义数据；`project_compiled_build` 负责可信导出；
`project_compiled_loading` 负责显式输入和外部 pin；`project_compiled_verification` 独立检查完整关系；
`project_compiled_lowering` 经原 semantic/IR/plan/emission owners 建立新的根。

这是明确的 compiled 输入分支。类型、NULL、范围、行等价、key/FD/grain、JOIN、aggregate/window、SET、
requirement/origin/proof、guard 与 refinement 继续消费原始规则。不存在第二个语义解释器。
运行时不恢复 `Script`、source AST、`ProjectParseCheckResult`、trusted source snapshot，
不重新执行 project/config/package discovery、module/import/name/type/source-connector elaboration。
未选中源可以只保留逻辑事实；所选执行闭包仍必须具有真实 physical source/field mapping。

`prepare_live_template` 与 `prepare_compiled_template` 接入同一私有 template/binding 接口。
live 调用不必写入再读取 JSON。每次加载产生新的语义根，每次 binding 有独立 instance reference；
相同值的兼容描述不能充当同一对象或同一 attempt 的证据。不同值重新推导值敏感事实。
Bool、signed Int64、有限 binary64 Float、Text 是四种可绑定叶值；七类结果 scalar 保留各自原域。
`True` 与 `1`、正负零、NULL、重复 occurrence、重复 use、结构性 LIMIT/frame/offset 角色保持区别。

## 有界格式与信任

格式为 `pietto.compiled-execution.v1`；显式 schema/semantic/occurrence/profile 版本向量为 `(1, 1, 1, 1)`。
固定成员为 `structure`、`parameters`、`targets`、`obligations`、`outputs`。
输入使用 canonical JSON；未知或重复成员、未知 tag/version、错误顺序、引用或值编码均拒绝。
上限包括 32 MiB envelope、1,048,576 JSON values、131,072 records、524,288 edges、
32 层 JSON、256 层 expression、512 fields、1 MiB Text。超限不是自动扩展格式的依据。

调用者必须另外提供整个 envelope 的 expected content pin、accepted producer 和 accepted compatibility。
loader 不从 payload 自选信任根，不读取 CWD 项目作为 fallback。producer 绑定可信构建输入；
compatibility 绑定实际 Pietto/ANTLR 代码和显式版本，不依赖未来 commit、HEAD、文档或安装目录。
whole-envelope pin 是跨边界内容身份，不是签名、registry 或凭据。没有自动迁移和自动信任升级。
含业务字面量的 bundle 和绑定输入必须由调用者保护；不生成参数 hash oracle，不把凭据、连接、事务、
source/guard receipt 或 live handle 写入包。

## 三个原生 route 与来源资格

`prepare_compiled_execution` 显式选择 `postgres_rows`、`postgres_adbc` 或 `mysql_rows`，并要求相应 fresh premise。
两个新 PG 入口共用有限 PG 来源资格；真实 Psycopg catalog reply 与真实 ADBC reply 保持不同 native 类型。
资格检查先于 source/schema、registry 和 key 扫描；保留完整 repeated/transitive paths、角色与 invoker/definer 规则。
local heap、inheritance、partition、ONLY、有限 nested/component view、合格 registry 和 retained-key wrapper
属于承诺域。已有 opaque routine、custom operator/cast、foreign/extension、RLS、不合格 virtual-generated
机制仍在求值前拒绝。没有通用 PG 程序分析或 native DDL lock-exclusion 承诺。

PG 与 MySQL 的 managed premise 分别绑定本次 route/access/root/schema，不能相互替代。
有限来源资格是实际观察；operator compliance 为 `NOT_INDEPENDENTLY_VERIFIED`；
native all-definition lifetime exclusion 为 `NOT_DEMONSTRATED`。operator 责任从 discovery 前覆盖至最后可能的 remote use。
provider 的 version/key/payload/retention 责任另行满足；稳定快照不冻结定义或创造 R2 retention。

旧 PG rows 入口和 public compiler/emitter/CLI/JSON 合同保持原状，不能作为新输入拒绝后的降级通道。
MySQL native prepared/per-use occurrences、PG 参数复用和 ADBC typed binding/COPY 边界保持原有语义。
复杂验证仍在实际 owner 的计时/取消边界内；错误后 COMMIT/ROLLBACK 前仍检查原始 native transaction。
Psycopg RawCursor 不据此变成 server streaming，ADBC batch hint 不是 RSS 上限，MySQL statement close-send 没有 ACK。

## 分层结果与验收

私有 `CompiledAttemptOutcome` 区分结构接受、部署前提、实际 source qualification、事务建立、guard 状态、
source terminal、transaction ACK/UNKNOWN、delivery、cancel requested/sent/observed、cleanup 和 remote use end。
EOF 后交付失败可以保留真实 ACK；cancel sent 不等于观察到取消终态；本地关闭不等于 remote quiescence。
新成功 attempt 不改写旧 UNKNOWN。local durable result 为 `NOT_IMPLEMENTED`。

纯验收覆盖当前 S04/S05/S06/S07 命名语料、原 target exclusions、retained-unselected、独立深层 corruption
和新进程 source-free binding。外部 observer 可以建立原 source reference；隔离 bundle worker 不得收到 source graph
或 source-rebuilding helper。source-library 与 same-wheel installed origin 分别记录真实执行。

原生分母取自当前原始 case owners 和 S10 profile/control laws，分别列 entry、route、origin、family/mode 与 oracle。
记录实际 SQL、每个 typed use、native metadata、完整值、guard/page、context、session/worker/cleanup terminal；
独立消费者重消费原始记录。故障后的完整无关记录可以按真实输入闭包保留，不拼接失败 attempt。
最高成本代表决定有界测试 request deadline；产品默认 20 秒不因此改变。测试采集成本不冒充产品加速。

## A01–A22 midpoint 与后续 owners

| 义务 | S10 边界及后续责任 |
| --- | --- |
| A01 | 双新入口、可信 build 与独立 source-free loader；后续仍需重新授权。 |
| A02 | 同一 template 的 typed A/B/A 与非法值拒绝；不序列化本次 binding authority。 |
| A03 | declaration/use/slot/output、binding、attempt 分层身份；job/generation/publisher epoch 由 S11。 |
| A04 | 三个实际原生 route 的声明域；原 target exclusions 保留。 |
| A05 | 原通用结果与七 scalar、NULL、空 schema、完整值/重数；不以参数域缩减结果域。 |
| A06 | 全部 pending/retained guards 与 fresh 同事务履行；S14 恢复仍不得丢失义务。 |
| A07 | 新共同 PG finite profile、独立 MySQL profile 与各自 managed premise；不降低隔离。 |
| A08 | source EOF、transaction ACK、delivery 分离；不是 durable completion。 |
| A09 | 原 native connection/statement/transaction 生命周期；不复活 serialized handles。 |
| A10 | 合格工作区、SQLite 与独占 publisher 属于 S11；S10 未实现。 |
| A11 | immutable chunk/checkpoint/frontier 属于 S12；descriptor 不创建 durable progress。 |
| A12 | 保存结果的 R1 恢复与重授权属于 S13。 |
| A13 | R2 静态 source requirement/occurrence 描述保留；跨进程续取与 coverage 闭合属于 S14。 |
| A14 | durable provisional stream 和 generation publication 属于 S15/S16。 |
| A15 | effect 身份、payload conflict、ACK 查询与保留协议属于 S15。 |
| A16 | 当前 owner 的取消/deadline/cleanup；job cancel/recover 状态由后续 store owners。 |
| A17 | 每次执行的资源事实保留；多 job admission、backpressure、control reserve 属于 S17。 |
| A18 | 引用、reader、sink retention 与并发 GC 属于 S12/S17。 |
| A19 | 显式格式/build compatibility、外部 pin、敏感输入保护；S11/S18 消费，不自动迁移。 |
| A20 | 当前 attempt 的分层描述；持久查询及历史存储由 S11–S16，UNKNOWN 不被覆盖。 |
| A21 | core 保持惰性、隔离 same-wheel 验收；正式 execution/recovery extras 属于 S18。 |
| A22 | 当前纯损坏与 native 控制；持久崩溃/并发联合历史属于 S19，S20 仅审计。 |

S11 使用独立 job/generation/attempt/publisher epoch，不能用 code/content/相等参数代替它们。
S12 使用稳定 node/use/field/output/occurrence 坐标，但 committed frontier 只能由真实存储协议发布。
S14 重新接受源/角色/版本并消费保留的 occurrence 描述；S15 不把 delivery 当 sink effect/ACK。
S17 消费有界资源事实与未确认 remote use，不能以本地关闭授权安全 GC。
二十个位置、S/H/L/K/Q 和全部 A01–A22 保留；后续路线为 JUSTIFIED_CANDIDATE，未提前认证。

## 获取整合与闭合

当前复用原 case/fixture/resource/process/metadata/scalar/native/page checker owners，保留必要的 fresh query-root、
source-free process、native attempt、安装 origin 和故障切点。S19 须进一步统一跨 adapter 的观察器装配及
fixture/reference 获取，消除重复纯准备成本；不能合并 live qualification、guard receipt、transaction 或历史终态。
S20 保持 audit-only。

正常闭合要求当前 focused/direct-reader、Ruff/生产与测试 typing、完整原生分母、包成员/installed/source-free 验收、
权威 Python 3.13 validator、精确 sealed tree、普通 sole-parent commit/FF push、自然 exact-head CI 的所有 required
jobs/steps/consumers，以及 protected-core/owned-resource 最终 readback。不手动 rerun/dispatch/cancel CI，不追加状态专用 commit。
