# Phase66 Pre-Slice16 G8 Window/QUALIFY Native Membership Evidence Closure v1

## Authority and chronology

本次是 `PHASE66_UNNUMBERED_G8_WINDOW_QUALIFY_NATIVE_MEMBERSHIP_EVIDENCE_CLOSURE`，
发生在 post-guard Slice16 re-audit HOLD 之后。它不是 Slice16、Slice17 或 Phase67；
N66=16、package/CLI=0.1.0。没有 production source 或产品语义变更。

接受基线：`27a558233c7c9b2b3d1b5f4dc4d2ecc7c330bca4`，tree
`94a7ae03f5e0d408a6af07699a605b60ea50b7d5`，sole parent
`3c6f25dabc43a0df84f6221d3e82d000554b365d`；natural CI
[35974624517](https://github.com/MianliWang/pietto/actions/runs/35974624517)，push/main/attempt1/success。
六路径 Slice16 HOLD 候选已复制到新的外部 G8-preservation 目录，逐文件核对 exact bytes 和
SHA-256 后仅按授权恢复四个 tracked paths、移除两个已复制的 untracked additions。
原审计账 diagnostic4/8、correction1/6、stored verifier3/4 继续冻结；G8 使用独立账本。
旧候选不会在 G8 发布后重贴，下一次 Slice16 必须从新基线重新构造。

[原 route lock](phase66-dialect-sql-emission-product-phase-initiation-gate-route-lock-v1.md)
R11/C09 要求 SEMI/ANTI 消费完整 right window/QUALIFY terminal，而
[Slice9 contract](phase66-slice9-admitted-windows-named-windows-frames-qualify-emission-v1.md)
曾声明该成员已关闭。现有 compiler tests 确实验证了 selected/hidden composition、SQL
结构、public decoding 和 shortcut controls，但基线每目标189 API documents、178实际
case observations 中，没有同时含 `OVER` 与 `EXISTS`/`NOT EXISTS` 的提交。
发现时这是 required-evidence gap，未证明 compiler defect 或 server failure。
本 spec 补记真实 chronology，不改写原 Slice9 历史合同或 route promise。

G8 只有在本地 required gates、sealed ordinary commit/FF push、该 head 的自然
push/main/attempt1 五-job CI 及新 raw receipts strict verification 全部成功后，才
`COMPLETED / PUBLISHED`。本 spec 不嵌入未来自己的 SHA/run。
Phase66 始终 ACTIVE；Slice16 的 HOLD 需要 G8 发布后的 fresh re-audit 才能解除，
G8 自己不宣称 Phase66 completion。Phase67 NOT STARTED；已接受的 v4 planning candidate
未激活。Interlude V Slice1 已完成，其余 slices NOT AUTHORIZED / NOT STARTED。

## Two strengthened native witnesses

仅加强既有 `A_window_qualify/selected` 和 `A_window_qualify/hidden`；没有新增 case/variant。
`WINDOW_BODIES` 中原 direct selected/hidden QUALIFY 保留，`window_fixture` 将其作为
named `ranked` producer，再附加左端 membership consumer。两者只读取既有物理 rows 的
`id`，使用已经存在的单字段 declaration/contract 模式；不修改物理表、四个 rows、
其余 window families 或别的 variant。完整 emitted public documents 仍全部进入 receipt。

PostgreSQL 的两个 source 如下；MySQL 只把 source family 改为 `mysql`，其他源码相同。

```text
shape One:
    id: Int not null
source rows: One is postgres.table("opaque")
table ranked:
    from rows
    select:
        record_id = id
        numbered = row_number() window:
            order by:
                id
    qualify:
        numbered <= 2
query result:
    from rows
    semi join ranked as r:
        from rows
        on rows.id == r.record_id
    select:
        record_id = rows.id
```

```text
shape One:
    id: Int not null
source rows: One is postgres.table("opaque")
table ranked:
    from rows
    select:
        record_id = id
    qualify:
        row_number() window:
            order by:
                id
        <= 2
query result:
    from rows
    anti join ranked as r:
        from rows
        on rows.id == r.record_id
    select:
        record_id = rows.id
```

selected producer 有 visible `record_id, numbered`；hidden producer 只有 `record_id`，
其 window 仅供 QUALIFY 消费。两者都是先 `ROW_NUMBER() OVER (ORDER BY ...)`，再外层
QUALIFY filter，最后 producer projection。outer SEMI/ANTI 的相关比较读取此 complete
terminal 的 exact `record_id` port；right window result 不进入最终左 schema。
生成的一个 statement 同时含 window 和 `WHERE EXISTS (` 或 `WHERE NOT EXISTS (`，
不是分别执行两个无关 queries。

| Variant | Independent right membership | Exact final BAG | Final output / metadata |
| --- | --- | --- | --- |
| selected / SEMI | `{0,1}` | `[0,1]` | one `record_id`, logical Int, not null; PG int8/OID20, MySQL BIGINT/LONGLONG8 |
| hidden / ANTI | `{0,1}` | `[9007199254740993,9007199254740993]` | 同一个 left-only schema/type；重复数必须保留 |

这里的 not null 是 retained logical/producer contract。实际 PostgreSQL description 为
`[record_id,20,null,8,null,null,null]`，nullability 未提供，不能写成协议报告了非 NULL；
MySQL description 为 `[record_id,8,null,null,null,null,0,4097,63]`。值域、逻辑 nullability
和实际 metadata 分别记录。

oracle 从既有 source BAG `[0,1,BIG,BIG]` 和 row_number 前两行手工推得，不从 actual
observation 或 emitter mapping 得出。不能把 BAG 转成 set，也不强加未承诺的最终排序。
若跳过 right window/QUALIFY 直接扫描 base table，SEMI 变成四行、ANTI 变成零行，
两项 exact per-case oracle 都拒绝它。direct Slice9 selected/hidden compiler tests 的原语义
保持，不把最终左 schema 的变化改写成隐藏 selected producer result。

## Independent controls and F9

新增 Slice9 control 检查一个真实 artifact：window→QUALIFY→projection→membership 的
object chain、selected/hidden flag、right columns 数和 exact terminal，完整 public decode、
最终左列类型/label；将 right input 的 producer graft 到 pre-QUALIFY window body 时，
已有 runtime verifier 拒绝。没有新增 verifier 或产品规则。

F9 保留 named/inline 与 peer-ranking 两条旧关系，并将旧 direct hidden/selected row
等价关系适配为当前组合：

```text
bag(selected/SEMI) + bag(hidden/ANTI) == original left BAG
supports(selected/SEMI) intersect supports(hidden/ANTI) == empty
bag(selected/SEMI) == ids of the separately executed ranking rows with row_number <= 2
```

这些关系只读本 full run 的不同 actual observations，不读 per-case expected rows。
最后一条使用已有 `A_window_ranking/peers`，防止同时把 SEMI 改成 all-left、ANTI 改成
empty 后仍靠 partition/disjointness 蒙混通过。测试分别破坏单个结果，并验证这种
coordinated shortcut 也被拒绝。它不是 document-string assertion，F1–F10 families 不减少。

保留 denominator：63 cases、195 public documents/target，即189 API +6 console。
PostgreSQL 162 VERIFIED /4 INPUT_REJECTED /29 BLOCKED；
MySQL 158 VERIFIED /4 INPUT_REJECTED /33 BLOCKED。
既有 facility/synthetic-receipt、Slice3 manifest、Slice14/private/process、corrective
hidden-use consumers 均保留。没有新增 Python file，所以不改 sole inventory reader。

## Capacity forecast and actual evidence

硬上限不变：receipt v2，33 MiB = 34,603,008 bytes。基线 raw pair：PG artifact10797303884，
34,544,638 B；MySQL artifact10797826318，34,550,764 B。基线 exact bytes/digests 继承
post-guard audit 已下载并严格验证的 pair，不把旧 residual dependency closure 当当前基线。

DB acquisition 之前的 diagnostic1 构造并独立 decode 四个 strengthened artifacts，逐项
比较基线 public bytes、SQL、inputs inventory。只有这两个 variants 的 source/contract
inputs 变化；case/API/console 数不变。下表的 public bytes 指单份，receipt 中各有两份完整
public string；JSON escaping 的实际增长/减少单独计入总预测。

| Target / variant | Old public B | New public B | Old SQL B | New SQL B | Observation non-SQL growth allowance B |
| --- | ---: | ---: | ---: | ---: | ---: |
| PG selected | 116212 | 88559 | 602 | 597 | 4702 |
| PG hidden | 110200 | 82568 | 577 | 576 | 4936 |
| MY selected | 116143 | 88475 | 594 | 590 | 17230 |
| MY hidden | 110135 | 82492 | 569 | 569 | 16714 |

每 variant 的 non-SQL allowance 是两倍旧完整 observation、16份新 expected rows 编码，
再加1024 B；不因列数减少而扣 metadata。SQL 按所有实际 text/hex copies 单独算，只计正
增长；MySQL 当前每 observation 还有三个 SQL hex copies。whole receipt 另保留16384 B
给 identity/timing 等不确定长度；不把 forecast 当 actual observation，也不写伪造回执。

| Target | Escaped public delta B | Observation growth allowance B | Extra reserve B | Forecast raw B | Forecast headroom B |
| --- | ---: | ---: | ---: | ---: | ---: |
| postgres | -128198 | 9638 | 16384 | 34442462 | 160546 |
| mysql | -128082 | 33944 | 16384 | 34473010 | 129998 |

本地 actual records：四次 target start 均一次成功，无重试；每次 owned container/network
cleanup 均 success/absent。focused receipt 的 full_manifest=false，只证明两个 G8 variants；
full receipt 的 full_manifest=true，证明完整63-case manifest。它们记录的是 checked-out
baseline HEAD 和实际 dirty-candidate inputs()，不是旧 baseline CI receipt。

| Run / target | Raw bytes | SHA-256 | Actual headroom B |
| --- | ---: | --- | ---: |
| local-g8-focused-1 / postgres | 17470738 | 0418b99f8cdf3e3cf6f49bc7ddafa16999322d456fa37082828430b981d610d7 | 17132270 |
| local-g8-focused-1 / mysql | 16959207 | 11454f61ce54cacf76be8f0386b9b58e1f69271a215a43b9f555437a43896e0e | 17643801 |
| local-g8-full-1 / postgres | 34416326 | ed079fddab49eb548695a7876f7cbb7e06e130bfafa84973d17c5f9df8295d47 | 186682 |
| local-g8-full-1 / mysql | 34422390 | 4446955551b32e1506b0c4bb2efd7dafe6095d31e7b4fcdf2087c47ad9b6f0e9 | 180618 |

四次 actual SQL 都包含 ROW_NUMBER OVER 和各自 EXISTS/NOT EXISTS，selected/SEMI 是
精确 BAG [0,1]，hidden/ANTI 是 [BIG,BIG]；最终只有 record_id，PG OID20、MY LONGLONG8。
full PG/MySQL 的 public status counts 均与上文一致。strict local per-target 两条命令
均 PASS，检查 safe raw read、exact inputs/pins/checkout/run/attempt、完整 oracle、native
transport、diagnostics 和 cleanup；没有提供伪造 artifact ID。local aggregate 必须在
guard-enabled authoritative validator 成功后，才用真实 compiler/target success 状态运行。
它与最终 validator/CI 结果由外部 Gate2/Gate3 ledger 记录，不能预先在此声明成功。


自然 CI 在未改 workflow 中重新运行两目标全量与 aggregate；发布后必须下载实际新 raw
pair，核对真实 ID、length、digest、head/run/attempt、G8 SQL/rows/metadata 和 owned cleanup，
再 strict per-target/aggregate。CI metadata、aggregate logs、raw verification 分别归因。
本地回执没有 uploaded artifact ID，不给它伪造 upload identity。

## Scope, validation and lifecycle

冻结 A1/M8/D0 九路径：两个 probe/oracle helpers，既有 Slice9 composition 和 Slice15
metamorphic tests，新 G8 spec，status/roadmap/development 与 sole lifecycle reader。
production、grammar、historical Slice9/route lock、target facility/observer、workflow、pins、
dependencies、version、OOM implementation/spec 均不变。Slice16 additions 不在 worktree。

默认 pytest 保持 offline。先 focused tests、Ruff、relevant typing、capacity，再前台串行
focused PG→MY、full PG→MY、strict local per-target、integrated author/Ponytail
review 与需要时一次 follow-up，最后 `UV_PYTHON=3.13 uv run python scripts/validate.py
--timings --oom-guard on`，再用真实 prerequisites 执行 strict local aggregate。generated/golden/package 的 owned inputs 未变，不另跑这些本地
gates；自然 CI 保留它们。guard 不保证绝无 OOM，resource-aborted start 不是 semantic PASS。

作者 review 是自审，不是第三方认证。G8 独立 budgets、失败 starts、修正组、sealed tree、
commit/parent、CI 和 raw receipt facts 全存外部 G8 ledger；不借用或重置 Slice16 counters。
任何 production/target-rule/capacity gap 均 HOLD，不在此任务里扩大支持或增加资源阈值。

G8 成功发布后：Phase66 ACTIVE、Slices1–15 COMPLETED / PUBLISHED，G8 unnumbered evidence
closure COMPLETED / PUBLISHED；Slice16 NEXT / requires fresh re-audit，原 HOLD 保留。
Phase67 v4 planning accepted candidate, not activated；下一次 audit PASS 后再按单独任务
rebind/publish planning/lessons 并展开 Slice1。此任务不自动重启 Slice16 或 Phase67。
