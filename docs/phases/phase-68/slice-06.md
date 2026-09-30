# Phase68 Slice06 — Compositional R2 refinement and checked enumeration

S06 CANDIDATE; completed only after closure。S01–S05/C01 已发布；S07 NEXT / NOT IMPLEMENTED / separate dispatch required。
基线 `01e509bf2cb2b83f1e699e089f3b1e5f7b3ea0b1`，tree `968c7370ad94231ea580403c7e776cff61713a52`，
parent `15c64d5ad8d5680abd1d08a5ff4d43e94d0a8aab`，自然 CI36641150728/push/main/attempt1。
本文件不预告未来 commit/CI。外部实例 `phase68-slice06-20260929T233906Z` 沿用同一 ledger；
原 dispatch Section10 是唯一数值预算。原 HOLD、原始失败与随后窄 amendment 分开保留。

## 显式修正与旧边界

本次获准纠正原 PostgreSQL project-emission 的结构参数范围：NTILE bucket 与 NTH_VALUE
position 为 1..2147483647；显式 LAG/LEAD offset 为 0..2147483647。原已验证超界调用的真实
42883/rollback/无EOF历史保持；当前在提交前以 PIE-B1002 /
`postgres_window_structural_argument_out_of_int32_range` 拒绝，无可用 executable artifact。
运行时 verifier 从原事实独立检查；pure observation consumer 仅按 target/function/role 检查数据，
也会拒绝以前超界的 serialized observations。没有自动格式迁移。

这不是 Pietto Int 的全局缩域。合法旧 SQL/public/portable bytes、省略参数、原错误类型/负数规则、
Int64 value/default、rank/result widths、R15 signed64 frame offsets、MySQL 域与原 exclusions 保持。
不 clamp、wrap、窄 cast，也不以小 fixture 返回 default/NULL。四种 bindable leaves 与结构参数仍分开。

## 当前连接的私有链

`prepare_refinement` 显式接受 pre-attempt `TieRefinement`、完整 source capability vector 与原
`GeneralOutput`。新 typed statement 独立于原 EmissionArtifact；原 AST、SQL 和原输出根不改写。
`project_refinement_verification` 按原完整 units/uses/ports 重建规则、逐项消费 native CTEs，
并独立识别实际 SQL 字节和每个参数 occurrence，不调用 lowerer/renderer 自证。

`RefinedExecutionRequest` 包裹原已检查 execution request；`PostgresExecution` 在同一独占只读
stable/Serializable transaction 内重新 admission 全部 source、提交外层有界页，经原 S05 producer/
scalar/managed Arrow 链消费。MySQL-native/PG-ADBC 只通过显式 test transports 接相同 verifier/
page consumer；其 product executors/完整 controls 仍属 S08/S09。

| 原族 | occurrence / choice / capacity 规则 | 独立检查及命名见证 |
| --- | --- | --- |
| scan/projection/LET/filter | qualified signed composite K；只投影原实际读取列，保持 value computation/TRUE-only filter | 完整 source/use vector、无额外列权限、原 S05 family fixtures |
| named/imported/repeated | producer 在自身 scope 决定 choice，consumer 后加 use/branch tag | repeated tied LIMIT producer；fresh graph structural addresses，live roots 不互借 |
| INNER/CROSS/outer JOIN | 有序 pairs，明确 presence/absence，matched NULL 不当 unmatched | 全部原 ports/conditions、outer/membership fixture、NULL/方向控制 |
| SEMI/ANTI/guard subjects | left occurrences，完整 right terminal 与原义务 | complete original inventory；未履行 mandatory obligations 在执行前拒绝 |
| GROUPED/GLOBAL | 原 typed determinant class；GLOBAL unit；原 native COUNT/MIN/MAX | hidden groups、empty/all-null；K 不进入原 grouping |
| windows/QUALIFY | RN/NTILE/navigation 共享 O+K；rank/distribution 保留 O peers；先 frame membership 再 exclusion | joint mixed、hidden LEAD、原 frames/GROUPS/exclusion；R2 不重算 native 分布值 |
| ROWS/GROUPS endpoints | 原有限 offset 寻找结构性 predecessor/successor；missing endpoint 按 before/after 处理 | 不新增全局 ordinal/COUNT；范围与零/大 offset 各自保留 |
| RANGE/default/frame value | 原键/方向/peers/合法阈值；正确 member set 上做 native FIRST/LAST/NTH | 原 R15 arithmetic 前提；coherent window 和 peer-changing damage |
| ORDER/LIMIT | 原 terminal 和静态 LIMIT 留在 outer page 下面，仅细化 ties | 原 ordering + typed K；不对 input chunks 分别求全局结果 |
| DISTINCT | 原 visible tuple quotient 先形成，再取 class key | hidden-group quotient；内部 K 不泄露到 DISTINCT |
| 六 SET forms | 原 positional fold；UNION ALL branch+K；DISTINCT native quotient；ALL 等值类内结构性后继配对 | 完整两侧/copies，无 arbitrary payload winner、无新 dense copy ordinal |

MySQL nullable JOIN 输入以包含完整 injective K 的内部 DISTINCT 保持每个 occurrence：
K 唯一使该操作一一对应，不是公共 payload 去重。它固定派生输入边界，避免 nullable constant
在 merged derived relation 与下一页 predicate 中被不一致折叠。独立 verifier 要求该完整键和边界。
MySQL 内部 CTE 列名及保留前缀按大小写不敏感规则避让；必要时使用位置列名，最外层仍输出原始
`Key`/`key` 等标签、类型和顺序。原普通 emitter 及公共输出格式不改变。

ALL 配对沿双方严格有序且唯一的 K 同时推进，每个等值类恰有 min(L,R) pairs；INTERSECT ALL
保留配对，EXCEPT ALL 保留剩余 left labels。公共 payload 来自原完整 tuple quotient，原 equality/
representation 保证其可互换，原 SET 输出不被伪装成 source field。该闭合 native 规则不引入
Python query/frame evaluator。完整依赖与 guard subjects 始终保留。

结构性 keys/NULL/direction 比较采用逐分量规则，避免裸 tuple `>`、字符串拼接或 hash 身份。
内部 columns/nodes/SQL/parameters 与原显式 native limits 一起计费，row/key/buffer 另按 execution
limits 检查。资源拒绝不冒充 unsupported family、EOF 或 source 总行数；不截公共列腾位置。
MySQL recursive selection 的实际 depth limit 作为资源环境记录；正常 terminal 是接受条件，
不把实验最多64行当产品界限。嵌套 scalar endpoint 与 successor matching 可能昂贵，原 deadlines
保留；本次不做优化器或性能维护。

## 四条法律与进展

1. Erasure 精确一对一对应全部原 S05 fields，输出是一种联合合法的原查询求值。
2. 在同 Q/b/V/A/E/tau 下，构造性 choice/transfer 决定稳定 K→payload；prefix 相等只是防御检查。
3. 每页在完整 refined terminal 外，按固定 total order 取连续段；正常 short/empty 页才完成，full 页继续。
4. foreign/changed roots、policy/binding/context、无效 coordinate/metadata、异常 terminal 不能推进。

`Enumeration` 从零开始并拥有唯一 pending page。不存在任意 frontier 导入或 durable cursor API。
页数据、原 scalar 及内部坐标先检查；在最后控制检查之后才推进。source/page/transaction/delivery/
cleanup 各自记录，UNKNOWN 不由后续 attempt 改成成功。PG execute 缓冲的是有界输出页；fetch hints
不是 server streaming 或硬 RSS 保证，完整 native Q 仍可能执行大量 server work。

Source vector 对齐全部原 dependencies，包括 hidden/right/重复 uses；每个 source 保留自己的
provider/version/revision/view/role 与完整 key 资格。复用同 source 不造新版本；schema/carrier/文本
collation 等实际可观察项与 configured value bounds 分开。完整可见域、持续 token/payload 不变性、
可信 provider 和跨 reopen retention 仍是明确外部前提；不 hash-read payload、写业务源或保留 extractor。

## 验收与后续 owner

完整命名分母沿用原 S05 46 cases，另有 mixed/repeated 与六个 seven-scalar states；
不是 family-by-seven-type Cartesian product。七 scalar、wide Int/Decimal、signed zero、empty/all-null
与旧 exclusions 保持。显式 launcher 为 `scripts/phase68_slice6_probe.py`，普通 pytest 不开 DB。
父级独立 literal oracle 与 fresh-root record reconsumption 检查实际 SQL/args/metadata/keys/schema/
origins/terminals；workers 不接收完整 oracle。各 route 的初次 worker 只取 bounded prefix，关闭/reap/
session-gone 后新 worker 用不同 page size 重验前缀并取未请求 suffix。这不认证 S11–S16 durability。

当前范围要求 source+installed PG、真实 MySQL native prepared、typed ADBC、A/B/A、source replacement/
expiry/visibility/role/token collision、late control/value failure 与 actual-record damages。只有这些当前
证据、完整 review/follow-up、guarded unfiltered Python3.13、exact sealed tree 普通 commit/FF push、
自然 exact-head attempt1 CI 的所有 mandatory jobs/consumers 与 cleanup 同时闭合，外部新 completion
report 才能激活完成。原 HOLD 报告不得覆盖；不发布单独范围修正或 status-only commit。

Core 固定 CPython3.13.13；core-targeted uv/validator 命令使用 `UV_PYTHON=3.13.13 UV_NO_SYNC=1
UV_LOCKED=1`，仍执行独立 `uv lock --check` 与全部 gate/resource guard。隔离 profile 必要安装不套用
core no-sync。没有 core refresh、pins/CI topology/validator 覆盖变更。

S07 仍负责 guards；S08/S09 负责 adapters；S10 负责 source-free bundle/loader 与累计准备成本复核；
S11/S12 负责存储；S14 消费这里的完整 choice/occurrence/page laws；S19 实施必要 acquisition整合，
S20 audit-only。复用 compatible fixture/observation owners，fresh mutation/root/process/source-wheel
见证仍独立，不缓存 PASS/selection/coverage。20位置与 A01–A22 不变，路线保持 JUSTIFIED_CANDIDATE。
