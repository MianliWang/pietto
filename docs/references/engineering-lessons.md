# 工程教训：下一阶段可执行的输入

条目是已有审计与实际观察的行动摘要，不是新审批系统。phase start消费适用条目，midpoint/closeout更新限制与状态。

| 来源／根因 | 适用条件／行动 | 回归／限制／状态 |
| --- | --- | --- |
| Phase66 J01：共享声明曾抹掉use-local差异 | 共享模板仍按完整use specification核对两顺序、共享与隔离 | Q07及native named window witnesses；不禁止完整相同规格共享；有效 |
| J02：逻辑域、producer storage、结果表示混同 | Result binding先核对type/null/protocol/origin，再作显式lossless adaptation | width矩阵、R-A、V05；missing meaning不由Arrow补足；有效 |
| J03：构造与image共同犯错、丢尾 | 从retained authority独立重推完整集合；加coordinated mutation、多owner、missing-tail | R-B/R-C；bytes一致非runtime认证；有效 |
| J04：分别通过不代表串联消费者通过 | 每项required positive绑定完整同次consumer链及区分性negative | G8/F9与Slice01真实probe/CI链；不扩任意笛卡尔积；有效 |
| J05：receipt/时间/WSL成本逼近边界 | 预估真实分母与headroom；分CPU/等待/关键路径/sum；保留owned cleanup | 33MiB receipt、S1 guard；不删mandatory断言换快；有效 |
| J06：support缩减与计数漂移 | 精确owner与supersession，累计失败starts，不把unknown改PASS | B1及14/14 ledger；不重建无必要旧repro；有效 |
| Interlude V S1/S2：安全与加速、环境同步被混同 | guard不是优化；共享store仅run-local；所有工具固定已核验解释器 | 原环境/cache事件保留；--locked不禁止sync；有效 |
| S3：节点计数与artifact摘要不足 | 独立U、真实worker集合/终态、exact raw artifact identity；冻结前查全readers | script inventories与raw-transfer incident；历史v1不迁移成新证据；有效 |
| R1：文件依赖分组不等于耗时平衡 | 独立mode可native逐node安排；先审计fixture；依据实际reports观察 | 六mode完整保留；finish spread非最优性/idle CPU证明；有效 |
| Slice01：required observations与advisory建议分离 | collection/locality错误hard fail；不足历史明确INSUFFICIENT_EVIDENCE；配置只经reviewed commit变更 | 正负policy/health/probe tests；当前实际结果由Slice01 seal绑定；候选至完整验收 |

Slice02 消费 J02–J06：contract/producer/Arrow 三层分别保留权威；同根多 realization 与 foreign-root negative
分开；installed consumer 读取当前 wheel，独立报告验证实际 Int 值/类型/NULL 和全部负例。新模块即使不改 emitter，
也改变 native input closure，旧 receipt 不能证明当前候选。SDK readiness 与产品消费证据必须各自保留。

Slice03：freeze前必须按真实新增production/test文件逐项检查直接inventory readers；本次漏项触发有效HOLD，续行仅批准一个reader。中立description应保留provenance路径分组及ORDER引用，不能flatten后以共同遗漏的roundtrip自证。既有required product路径足够时不增加重复workflow下载。具体一个Enum程序的上游拒绝不能推广为全类型结论。

Slice04消费S03教训：freeze前逐项核对inventory/lifecycle/probe readers，使用既有required product链；Float signed-zero需要独立bits/value witness，schema/domain不能认证payload历史。native证据先准备普通独立文件及精确pair-only布局再计数运行strict checker。

Slice05：variable-width费用按实际UTF-8、offset与validity计算，供给slice必须先检查retained buffers再full validate；NULL槽任意payload不等于有效字符串。测试同时区分constructor拒绝、checker拒绝与独立value correspondence，不把domain PASS当原始行认证。

Slice06：下游representation的65位上限未证明上游能产生相应fact；共享semantic rule当时仍限38。先追踪fact生产规则并实测可达38/39边界；本次正确HOLD后由用户明确扩至65，旧合同不追认错误。语言scale≤p、producer scale≤min(p,30)和Arrow width是三个独立判断。

Slice07：先验证实际meaning producer与explicit consumption，再建立Arrow矩阵；补齐新runtime field对应的旧observation CUTOFF inventory，保持完整字段断言。处理新增optional authority时应同时测试字段删除的typed failure，并防止显式opt-in顺带开放本Slice未授权的旧lowering。SQL/数据结果观察、pure描述和source-value真实性仍是不同证据。

Slice08：完整schema与原始输入positional values是两种证据；同type同名column交换可能通过batch schema/domain，必须由独立原输入oracle拒绝。零行数组可合法没有data buffer，先遵守pinned SDK full validation再处理零长度，不能把owned constructor的分配细节当输入约束。S06/S07的先证可达域、字段删除typed failure、完整reader inventory及文档diagnostic scanner已纳入本Slice前置检查。

Slice09：声明extent先于候选消费，正常source EOF只在read操作边界解释；达到行数、empty批或cleanup成功单独都不够。累计处理费用使用每批max(logical,referenced)再求和，切片/重分批可改变成本；原值正确性仍由独立positional oracle验证。真实SDK无预读/weakref/close后返回值前提先测，罕见cleanup异常注明注入，不能把测试sentinel描述为自然SDK行为。

Slice10：先测真实capsule/close/owner保活；C handle release不代表独占buffer，也不保证关闭原checked source。协议消费后的SDK空metadata表示与跨C ABI异常表示应如实记录，保留原binding规则和原primary cause；不要将表示差异误判为值复制损坏或用归一化隐藏它。

### Phase67 Slice11：入口组合的验收责任

显式入口可直接别名已有owned builder/managed batch；raw reader应直接组合接受与delivery，不用C导出再导入绕行。source-specific lease在接受前capture，接受后claim失败由原session一次cleanup。logical Arrow与producer carriers分别建fixture；layout成本不强求相等，原值oracle与domain checker各司其职。细节与限制见[唯一S11合同](../phases/phase-67/slice-11.md)。

### Phase67 Slice12：transport与完成的责任

Arrow接受complete-message prefix不证明原有限结果完成。固定framing检测普通截断，caller extent仍交原session检查；源完成之后writer finalization仍可能失败。内部创建reader的接受前cleanup归transport，接受后的close归原reader owner，不能重复关闭或覆盖primary错误。

### Phase67 Slice13：依赖选择与安装证据

先测真实artifact metadata和local-wheel extra语法，再接CI。core/extra必须从两个干净prefix
安装同一个wheel；hash预置不能替代extra解析。metadata、wheel bytes和resolved origins共同
约束安装身份，SDK/version字符串本身不够；依赖公开可安装不等于private API已公开。

### Phase67 Slice14：真实观察与独立消费者

receipt replay的输入是原execution rows，预期答案只能用来核验；decoder与原值oracle不共用
同一个转换入口。先证明populated/empty可达，再扩固定corpus。原strict receipt证明与额外
consumer证明分开；frame/extent通过仍不能认证原值、重复行或DB未遗漏。解释器固定覆盖外层driver。

## Phase67 Slice15：whole-result law 约束

- 跨route只共享独立literal预期与positional观察格式；真实缺陷注入须改变实际消费者看到的值，不能仅损坏报告。
- 同值重分批可改变referenced-buffer与sum(max(A,R))成本；分别证明值关系和admission，不用RSS解释上限。
- handoff按fixture/native replay/descriptor/future execution分层；expected_rows与EOF不足以替Phase68提供执行authority。

## Phase67 完成审计的六条耐久教训

以下为Phase级行动入口；上方逐Slice记录保留其历史状态，不重写原授权或失败。S03 settled closure、
S06旧38合同与明确扩展、S12旧/当前格式、S14 timing addendum按[完成审计](../phases/phase-67/completion-audit.md)
的准确supersession理解。条目有效；Phase67完成状态仍由S16唯一闭环规则决定。

| ID / origin-root cause | applicability trigger | required future action | witness / regression | limitation | evidence / next consumer | status |
| --- | --- | --- | --- | --- | --- | --- |
| P67-L01 / S06外层65不代表shared fact可达；S07必须先取得meaning | 新类型、driver事实、能力或representation桥接 | 从实际fact生产owner追到consumer，先证边界正/负；missing前提明确HOLD，仅经授权改上游；完整type/field/CUTOFF读者同时闭合 | S06真实38/39拒绝后批准1..65；S07meaning_premise/default missing及optional-slot删除 | 不以schema或SDK roundtrip赋予语义，不追认旧38规则为bug | [S06](../phases/phase-67/slice-06.md)、[S07](../phases/phase-67/slice-07.md)、`pietto-phase67-slice06-approval-refreeze.json`；Phase68 adapters/authority规划 | 有效；Phase68 FULL gate必需筛选 |
| P67-L02 / S14输入decoder若兼作expected会共同解释错误；S08/S15同type同名换值可过schema | 输入adapter、codec或多route差分 | 分开输入解码、实际观察与独立literal/original oracle；保ordinal、NULL、bits、coefficients及typed BAG重数；注入真实builder/bridge缺陷 | S14 test_original_value_oracle_does_not_reuse_the_input_decoder；S15 W10 copy注入、±0/换列/丢重反例 | data correspondence不等于来源认证或新的Pietto equality/collation | [S14](../phases/phase-67/slice-14.md)、[W10 helper](../../tests/_pietto_phase67_whole_result_probe.py)；Phase68 driver result integration | 有效 |
| P67-L03 / S01/S12完整message prefix可被SDK接受；S09 count相等不等于EOF | 有限结果、cursor终结、IPC或取消/cleanup设计 | 固定原extent/session，分别记录source、delivery、IPC、executor结论；每层有自己的normal/failed terminal；未知基数另行设计 | reader_terminal/identity、ipc_completion、integration_terminal_failures、W05/W07 | expected_rows不授权COUNT或可靠cursorrowcount假设；hash/EOF不认证DB完整性 | [D67.24–26](../decisions.md)、[S09](../phases/phase-67/slice-09.md)、[S12](../phases/phase-67/slice-12.md)；Phase68 extent/finalization与runtime errors | 有效 |
| P67-L04 / S08合法empty absent buffers、S10 foreign close不传播generator finally、S15 C-import empty offset损坏IPC | SDK/pin、ownership/protocol交界或异常路径变化 | 以小真实消费者验证零行/offset、copy/borrow/alias、close/控制异常；原carrier先validation/admission，再作必要已批准delivery处理 | SDK9、ownership_*、S15 W01实际失败及修复；W08 retained-before-copy | PyArrow-backed不等于独立C认证；owner retention不是nonmutation；wrapper close次数不是native callback计数 | [S08](../phases/phase-67/slice-08.md)、[S10](../phases/phase-67/slice-10.md)、[S15](../phases/phase-67/slice-15.md)及原失败；Phase68 lifecycle，Phase86/90后续桥接 | 有效 |
| P67-L05 / S03 receipt文件准备与S12 materially changed contract需要精确证据身份 | scope/format修订、HOLD/resume、CI/raw闭环 | 保留旧candidate/失败/累计计数，区分实际Git commit与计算tree；新合同重验受影响链，current receipts先普通独立副本/完整digest/argv预检再strict | S03明确7/7与4native终态；S12旧1066.976s/current1250.209s各归原合同；当前28raw规则 | 旧PASS不迁移；纯orchestration/docs续行仅在完整input footprint未变时复用；不把观察丢失改成PASS/FAIL | [历史对账](../phases/phase-67/completion-audit.md)、`pietto-phase67-slice03-native-continuation-authority-v1.txt`、`pietto-phase67-slice12-continuation-authority.txt`；Phase68及后续publication | 有效；保留旧记录 |
| P67-L06 / S13外层解释器缺pytest；S14时间汇总需恢复；CI可比样本不足 | 长验证、installed/acquisition、成本或健康判断 | 同时固定outer/child解释器与安装来源；先小focused/reader检查，保留一次完整finding集；从结构记录生成费用并区分parent/stages、CIwall/runner sum/transfer overlap | S13仅补缺项恢复；S14 timing-recovery；S15 full1392.291s与CI699s分列 | 不把UNKNOWN填0，不将test-count增长当生产率，不由WATCH/INSUFFICIENT_EVIDENCE启动性能interlude | [package_smoke](../../scripts/package_smoke.py)、[S13](../phases/phase-67/slice-13.md)、`pietto-phase67-slice14-timing-recovery.json`；Phase68 FULL gate消费真实health与预算 | 有效 |

## Phase68 Slice01 consumption of P67 lessons

S01先测真实parameterized SELECT，不以ADBC文档或API名称判支持（L01/L04）；独立literal oracle保原值/位模式/重数，schema与value correspondence分开（L02）。
source/statement/transaction/delivery/cleanup分别记录，unknown cardinality不借COUNT或旧extent补证（L03）；本地实测与旧native replay保持不同证据层（L05）。
outer/child固定解释器，SQLite builtin module不能假定有独立__file__；原失败计入单一累计ledger，已完成case及时保存，时间未知不填0（L05/L06）。
当前S01仍candidate；准确支持/缺口只由最终绑定报告与唯一闭环规则确定，不因preliminary P02成功宣称三路线产品对等。

S01续行实测：selector只反映kernel readiness，buffered readline可能藏住已读控制帧；单owner raw framing和真实coalesced/fragmented/EOF/ACK反例关闭该缺陷。
MySQL helper调用不等于第二次native提交；prepared Execute、实际signal outcome与standalone SLEEP返回值须按真实接口分开记录。matrix6已重验完整57项；旧失败不抹去，不从局部成功推全域产品保证。

## Phase68 S02 bounded lessons

- 同版本标识需与源的实际不可变/保留契约相连；原提取者死亡后新session取得未捕获suffix才是R2，scan正例不迁移到全局算子。
- 文件namespace durability、metadata commit与job ACK分别观测；进程崩溃不是断电，WAL maintenance不是应用checkpoint。
- sink commit与本地ACK分离；稳定effect身份、payload/epoch/retention检查和可查询历史共同支持有限重试。

## Phase68 S03

- Provider definition evidence 必须与执行端使用同一 role/schema/deparse context；`pg_get_viewdef` 在不同 search_path 下文本不同。S03 在明确 pg_catalog context 捕获并验收，避免把表示差别误判成 domain 改变。
- 持锁事务观察 blocked query 时显式清除自己的统计 snapshot，再检查实际 session、SQL、active/Lock；缓存 activity 不能当成新控制观察。参见 [S03 合同](../phases/phase-68/slice-03.md)。
- Oracle 的物理宽度须从既有表示规则独立推导：MySQL UNION 常量 part 是 BIGINT，Arrow 有界 SMALLINT 是 int16。保留失败 raw，修正 checker 后只重读语义未变的记录。
