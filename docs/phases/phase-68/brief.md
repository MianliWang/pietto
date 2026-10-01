# Phase68：显式受控只读执行、运行包与恢复

Phase67 COMPLETED，终态基线 `2f280ea02b974c0ab7e6e8e07017b960b55f850a`；其原合同和失败历史保留。
本期 ACTIVE；S01–S07 和 C01 COMPLETED / PUBLISHED；[S08](slice-08.md) CANDIDATE; completed only after closure。
S03 内部资格 gate 为 QUALIFIED_UNDER_THIS_DISPATCH；[20行路线](slices.md)为 JUSTIFIED_CANDIDATE，后续产品验收仍待完成。

## R/A/C 与使命

上期已完成七scalar/十二physical fixtures、有限reader、CPU协议、private IPC、四安装cells与真实captured-native replay。
实际value producer仍主要支持builtin field scan/projection；ORDER descriptor不是ordered query执行，旧expected_rows不是未知基数完成证明。
原16,838 local与每CI runtime16,832+6既有shallow skips、SDK9、120/118、22全文、28raw为回归基线，不是本期通过证据或计数上限。
消费 P67-L01/L04：先测真实fact producer、empty和close；L02/L03：input/oracle与source/transaction/delivery分开；L05/L06：保持精确输入、累计失败和outer/child解释器。
既有health WATCH/INSUFFICIENT_EVIDENCE、可比样本0不授权新的性能维护。

调用者通过live编译入口或无源码运行包，反复绑定参数，在PG rows、MySQL rows、PG ADBC上取得同一承诺矩阵的显式只读执行。
结果支持持久增量消费与完整成功后发布；在明确同版本source、合作sink、保留期和本地磁盘完好前提下恢复长任务，并允许有界多job并发。
默认 core 仍是 compiler；S03 增加显式调用的 private PostgreSQL 最小执行纵向，其他 adapter 与通用查询仍由后续 owners 交付。

## 已批准选择和范围

必须兑现双入口、三路线对等、类型化模板重绑定、双持久交付、真实R1/R2正例、合作reference consumer、显式recover与有限并发。
运行包可信构建来源、独立loader、受支持版本和重新授权是必要条件；不复活旧live authority或凭据。
执行创建独占连接/事务/statement；默认checks和稳定快照，Serializable是明确强profile；关闭额外SQL不免除强义务。
明确source/transaction/checkpoint/publication/sink effect/ACK/notification/cleanup各层终态；不能将UNKNOWN改为成功，不能以新attempt重写旧历史。
凭据不落盘；业务参数保护且不进入普通日志。immutable片段先耐久，metadata短事务发布引用；连续前沿不跨holes，同值重复occurrences不合并。
单job实际写端核验publisher epoch；独立job可并发；预算包含临时/最终文件、metadata/WAL和恢复控制余量；reader与retention约束GC。
同保证调优只调整batch/prefetch/提交分组/额度，不降低checks、isolation、durability；取消控制不得被数据队列饿死。

明确不做任意SQL/DML/DDL产品、业务源写入、hidden COUNT、silent fallback/换driver、整job自动重试、XA/共识/自写WAL、任意callback全局事务、
永久磁盘丢失/远程复制/多机接管、自动跨版迁移、OS scheduler、公共release或Phase69实现。时间有余才增加非必要性能取点/可视化。
不能用全部拒绝替代必需正例，不能将三路线缩到最弱交集。限20个编号Slices；当前累计执行预算沿用 S08 v2 dispatch Section 8 及已批准 view-source / managed-deployment amendments；历史 S01–S07/C01 计数保持闭合。

R2 首次 attempt 前显式选择 tie refinement；不得改变既定 ordering、peers、frames、值、NULL、类型、重数与 guards。
R2 要求合格 K-provider 的完整实际 source domain、可重开 retained version、非空单射且 reopen-stable tokens；既有 composite key 可合格。
不要求为任意无身份源合成 identity，不要求 exchangeability fallback，不新建业务列、源服务、结果表或 snapshot keeper。
provider 的持续不变性/保留责任须显式给出；普通 fresh transaction、版本标签或样本均不足以替代。
S05 接 original-output/PB，S06 接 compositional R2/refinement/peer-preserving lowering，S10 接 source-free bundle/loader 与 midpoint；每 adapter 自带 controls。

## 三层验收

每项需要真实能力、明确owner和接通的consumer，以及区分性反例；实验、类名、文档PASS和旧receipt不能单独满足产品验收。

| ID                             | 为真：能力                                                   | 存在／接通与验证                                             |
| ------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| P68-A01 双执行入口             | live编译入口和无源码、无需源语言重编译的运行包；可信构建来源、独立loader及重新授权。 | 两入口执行相同模板；换包/缺成员/错误版本/错误授权被拒。      |
| P68-A02 类型化可复用参数       | 模板、不可变的本次值绑定、attempt分离；值敏感事实失效；原slot/use映射保持。 | 同模板两组合法值及非法值；LIMIT相关证明失效；接受后修改参数容器不改变提交。 |
| P68-A03 显式执行身份与权限     | query、target、connection、statement、job/generation/attempt及role绑定；无ambient credentials。 | foreign/stale对象、错误目标/角色/句柄拒绝；实际提交与授权对应。 |
| P68-A04 三adapter对等          | PG rows、MySQL rows、PG ADBC兑现事先定义的同一产品矩阵；不取最弱交集、不silent fallback。 | 相同声明矩阵逐格走实际adapter；缺口不以UNSUPPORTED冒充已交付。 |
| P68-A05 通用结果衔接           | 已支持的平面查询族接到retained outputs/PB/AR；七scalar原域；复杂输出不能靠首行推断。 | source/projection、imports、JOIN、aggregate/window、ORDER/LIMIT、DISTINCT/SET的命名corpus及typed BAG/精确值反例。 |
| P68-A06 默认guards与运行期义务 | 默认履行适用single-match等义务；关闭额外SQL后缺强证据拒绝checked执行；不增加弱保证兜底。 | 实际成功履行和违例；相同payload的两个occurrences仍算两次；WHERE/LIMIT/去重不能抹掉义务。 |
| P68-A07 一致性profile          | 稳定快照默认；明确Serializable只读profile；guard/query的参数、predicate、role和view一致。 | 受控并发更新、不同role可见性、DDL/环境变化；强profile失败不降级。 |
| P68-A08 未知基数完成           | batch/source/transaction/delivery分别终结；不把读到N行再填回expected_rows当证明。 | normal terminal正例及late error、early close、empty与EOF的接口差别；旧RD合同回归。 |
| P68-A09 资源生命周期           | 本次独占新连接/事务与statement的接受、提交、关闭和失败责任。 | 构造中途失败、执行/读取/cleanup组合错误；不接管调用者活动事务。 |
| P68-A10 合格持久工作区         | 明确本地存储、保护/配额、SQLite实际构建与配置；文件耐久前提与状态事务分开。 | 正确profile可用；库/配置/路径不符拒绝；无修复依据不宣称耐久合格。 |
| P68-A11 检查点与进度           | immutable chunks先持久，metadata再提交引用；连续前沿与holes；观察/持久/交付/ACK分离。 | 1和3完成、2未完成不能跳过；各提交点故障、回复丢失、重新启动保持已确认进度。 |
| P68-A12 R1消费恢复             | 从同一已保存结果代恢复消费，原参数/格式/授权/保留条件复验。  | 重启、变batch大小、过期和取消任务；不丢重，不复活旧runtime对象。 |
| P68-A13 R2原提取恢复           | 在明确可重开的同源版本和正确occurrence覆盖下恢复未捕获部分；有真实正例。 | 新进程重新访问真实source并取得未捕获数据；重复键/ORDER ties/全局操作不错误拼接。 |
| P68-A14 双持久交付             | durable provisional stream及完整结果代原子发布共用内核；不将整结果塞进一个IPC frame。 | 两模式均成功且故障不发假完整；publish/cancel两种顺序；已发布后通知丢失可查询。 |
| P68-A15 合作sink               | 真实参考consumer、稳定逻辑effect身份、payload冲突、ACK/提交查询与retention。 | ACK丢失重试不重复；同键异值拒绝、等值occurrences不合并；期限/identity改变不继承旧ACK。 |
| P68-A16 取消与deadline         | 有界取消、控制资源、必要时弃用自己的连接；请求/送达/观察到终态分开。 | 阻塞execute/fetch、取消失败/晚到成功、cleanup失败；已取消job不能recover复活。 |
| P68-A17 并发与资源             | 独立execution预算、多job准入、短metadata事务、背压/控制通道；同保证调优。 | 小/大任务、慢消费者、满额度取消、源写者干扰；不降隔离/刷盘/检查，不SKIP LOCKED跳行。 |
| P68-A18 保留与安全回收         | checkpoint、published generation、active readers、sink期限共同约束GC；回收也有身份/并发协议。 | reader/GC交错、磁盘压力、孤儿片段；仍被引用的数据不删除。    |
| P68-A19 兼容与秘密边界         | 私有持久格式显式版本；恢复重新授权；凭据不落盘；敏感参数受保护；不自动跨版迁移。 | 旧runtime先拒绝而不修改；包/源/角色替换；普通日志不出现秘密。 |
| P68-A20 可查询的分层结果       | source UNKNOWN、本地已提交但回复未知、cleanup失败各自记录；保留attempt历史。 | 同一local observation的不同remote terminal不被强行合并；新attempt不篡改旧UNKNOWN。 |
| P68-A21 安装与回归             | core仍无ambient执行/Arrow依赖；执行依赖隔离，same-wheel origins；保留P67及更早能力。 | 四安装cells、SDK9、原120/118、22完整文档、原native/replay；新执行证据独立。 |
| P68-A22 联合故障与性能         | 小模型、真实组件、进程崩溃/持久模拟分层；同保证的并发与故障历史。 | 命名interleavings、故障后再次恢复、完整值/重数/终态；没有真实断电或通用exactly-once夸大。 |

## 三项风险

1. Driver parameter/result/type/control能力与文档不一致：由S01实测精确pins/options，不插值、不冒用DBAPI充当ADBC。
2. 同版本R2、FS/SQLite与sink的可恢复边界：S02必须取得未捕获suffix的真实正例，R1不能冒充R2。
3. S04/S05/S06/S07/S14尺寸及共同矩阵：S02重新核对20片可行性；冲突保留全部目标并提出明确分期决定，不增加S21。

Phase69消费真实执行矩阵与入口/error要求；public format/API归Phase82、stable1.0归Phase83、强信任/签名归Phase84，原nested/device/adapter owners保持。

当前S01前提调查：matrix6取得完整57项并通过独立checker，READY_FOR_SLICE02_EXPERIMENT仅是下一实验的前提评估。
实际driver/representation/取消边界见[planning notes](planning-notes.md#matrix6当前前提调查闭合s01仍待完整发布闭环)；S01完成仍以全部回归/发布/证据条件为准。

S02有限三路线同版本未捕获suffix、SQLite/WAL+FULL进程恢复与合作sink已观察；完整产品与路线尺寸仍未获证，详见[S02](slice-02.md)。
