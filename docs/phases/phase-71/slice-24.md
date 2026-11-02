# Phase71 Slice24：最终审计与交接候选

这是 B9 的 audit-only 候选。Phase71 只有在本片一个普通提交 fast-forward push 后，
其自然 exact-head CI 接受全部 required consumers，才为 `COMPLETED / PUBLISHED`。
本记录不授权发行、下一阶段实施、数据库 campaign 或只为补写自身提交/CI 而追加提交。

## 绑定与证据层

审计基线是 B8 head `28dc36fdd54b90d406e07a4e82d3c10c2bad5e35`，tree
`b0b8b21e036356afd82e77a8bf90e13f555aa0ef`；自然 push/main CI `41518702589`
attempt 1 的 19 个 job 全部成功。S22 commit
`8fd880701c9b87b3978bf77577a980d855bc1e37`（tree
`05129d1365a5cd543876c3010612221f1278e0bf`）采用批次头结果，没有自己的 CI 结论。

B8 的合格 Python 3.13.13 Gate 2 为 24,809 passed / 41 skipped，独立收集 24,850。
另有 fresh core/Arrow 安装、已安装 CLI、Arrow readiness 和独立 reader；installed
result-product 为 136 cases / 211 verified origins，严格 reader 复核成功。
本机 core skips、managed Arrow positives、真实数据库观察、Gate 2 和自然 CI 不相加
冒充同一个证据分母。

| 层 | 已接受事实及其边界 |
|---|---|
| B7 runtime/native | head `1440878114b5b5a61709ad170202bbf5939634f1`，tree `7eaf46704d925d1852c55e0b23f6d6ccaea3f17a`，CI `41485998460` attempt 1、19/19。原生原始获取绑定 tree `1122c5e5a1b4ce4e41aa78686d09eb8efdcff634`；其后 test-reader-only 修正经独立重读闭合，原始失败保留。 |
| Native wheel | `4def34258a419219cfad9a192531112e9749535ed4399706e3c42dd3b8f58317`；PG18.6、psycopg3.3.5、PyArrow26.0.0，固定镜像、internal network/exec-stdio、flock、单个自有 container、四份隔离/清理 journal。 |
| B8 candidate wheel | `0174e6e76fbf646f50cb4bb59476df27ac39e87ef1aa3e342539706d662b79c7`；352 个 runtime members 与 native wheel 逐字节相同，仅 README 对应的 METADATA 正文与 RECORD 不同，metadata headers 相同。新安装证据绑定新 wheel；旧 native 收据保留原身份，不声称在新 wheel 上重跑数据库。 |
| B8 candidate sdist | `0ac1567ab418b8fc3bca801120b06d3e3f21bfc133e841ca365ceccde6b522ee`，仍名为 `pietto-0.1.6.tar.gz`；不是 PyPI 已发行 bytes。B9 只改未进入 wheel/sdist 的 docs，README、package、src、lock 与 build inputs 不变。 |
| Channels | 已发行 0.1.6 只含 Phase71 B1；后续批次及 interludes 在 main 上、尚无 0.1.7 发行。S24 不修改历史 distributions 或 channels。 |

## A01–A12 三层验收对账

[brief](brief.md) 保持规范地位。下列“存在”与“接通”相互区分，拒绝范围不会因相邻
正例而自动开放。具体支持域见 [S23](slice-23.md#已实现与仍拒绝的边界)。

| ID / 用户事实 | 存在的 owner 与区分性反例 | 已接通消费者 |
|---|---|---|
| A01 确定的语法、scope/type 与模式拒绝 | S03–S05；`test_project_nested_relation_facts.py`、`test_project_nested_relation_unnest.py` 的同名/forward/cycle、错误来源和模式反例 | 现代源码到 checker；单文件/LEGACY_FLAT/PACKAGE_ROOT 保持确定拒绝；完整收集和自然 CI |
| A02 Collect 保父 occurrence、重复、空与真实全NULL子行 | S04/S08；独立 literal/occurrence oracle、真实 plan/result owners | S12–S16 public postgres_rows，B7 literal/native/law consumers；不靠JSON外观判断正确 |
| A03 capture/参数与分组后显式阶段组合 | captured let、exact use/producer、nullable outer JOIN carry；禁止直接 group representative capture | source/compiled、参数切换和实际 native；匹配[]、未匹配None与重复parent各保留 |
| A04 CROSS/INNER/LEFT Unnest 与 presence/grain | S05/S13；三parent的4/5行、ON拒绝全部child、UNKNOWN与后置WHERE反例 | 实际 flat/retained-sibling输出、source-free compiled、typed rows；INNER ON的null-rejection不误用到LEFT WHERE |
| A05 并列集合与子关系排序/Top-K | S04/S08/S16；2×3独立children、隐藏nullable排序键、ties、跨模块身份；无order by拒绝 | SQL/native/literal与20类laws；C7父ORDER/LIMIT最终count-port修复同时覆盖source、compiled及strict verifier |
| A06 真实目标行为 | PostgreSQL完整73case families、installed/native SQL与独立typed consumer；MySQL nested拒绝 | 当前CI两目标完整既有conformance；MySQL只保旧flat正例，不假报nested支持 |
| A07 live/source-free bundle | S09及`test_execution_nested_relations.py`；foreign root、删child、错version/occurrence及source禁用反例 | 真实export/load/bind/execute；native的fresh live/bundle workers分别核对 |
| A08 Arrow八类leaf与ownership/IPC | S10/S11/S14/S15/S17；Float signed-zero、Decimal scale/width、temporal/UUID、offset/validity、C/IPC损坏与close后归属 | B8真实installed product、B7 PG到rows/Arrow；core缺Arrow的skip不算positive；IPC仍为internal读取边界 |
| A09 有界资源与真实终态 | S02/S12/S20；parent/child/cell/total charges、超限、失败、取消、脱敏；shared-window连接不虚构归属 | API native、rows三worker回收与分层strict readers；target fixture清理与attempt cleanup是不同事实 |
| A10 save → R1 → verified_export | S18/S19；v7固定snapshot、parent extent/ACK、每member一次读取/验证、每slice再查acceptance/PID/close | 源项目移除后新进程、无driver的R1与独立export；全部8leaf及保留组合/empty；export无持久control writes，R2/relay/sink仍拒绝 |
| A11 旧flat/现代语法与兼容 | S01/S21；阶段baseline两树比较、逐条owner许可、现有三路线回归与源码迁移 | 全量/独立collection、naturalCI及原生旧消费者；unknown drift不豁免 |
| A12 按文档安装且状态诚实 | S22/S23；同一候选core/Arrow install、CLI/examples/help、support与refusal矩阵 | exact wheel origins、独立安装reader、自然CI；发行材料不是发行授权或served-byte证据 |

B7 native law matrix 的分母为 96：22 个 nested programs × 两组 MINIMAL/FULL seeds ×
fresh live/bundle = 88，加 U1/M1 LATERAL twins 的 8 个观察。nested 组覆盖八类 leaf；
LATERAL twins 只用 Int/Bool/Text，flat CROSS LATERAL 的 Timestamp/UUID 原拒绝未开放。
20 个 law families 都要有 HOLDS；NOT_APPLICABLE 不充数。另有 all-leaf C1 的实际
save、新进程 R1 和新进程 export，保留各自的 native/reader 身份。

有限 S09 controls + seven/39-values 的 source/installed 四 worker 与 data-only重读，
只关闭受影响的 checker 路径，不能写成完整 S09 campaign。statement-timeout 控制的
UNKNOWN/attempt-cleanup FAILED 是预期观察；fixture/container/network最终清理另验。

阶段 flat 对比绑定 S01 baseline `9511f13563d0d5ce21fc778c6a3828a8324c2222` 与实际
候选，报告分母为 1,352 command entries 和 90 frozen-file entries：IDENTICAL 1,335、
ALLOWED 105、ADDED 2、DRIFT 0、STALE 0。105 项按精确 command/path 绑定已有 owner
决定，没有按整个诊断码或目录豁免。原 raw exit1/differences 保留；data-only许可对账
不是重新执行。B6→B7的单批比较另记，不能替代整个Phase的对比。

## 获取、实际偏差与保留限制

- 计划24片、容量25；实际仍是S01–S24，未使用第25个位置。S17随B4提前到最小纵向，
  符合已批准依赖；AC-F7按owner决定并入S12，scope账仅该项既有变化。
- [S22](slice-22.md)完成230路径/48helper及直接读者复核。维护main的十项profile
  已处置；B8最终health前十名重用其中九项，再补一次source-free PostgreSQL corpus
  profile。该项1passed/130.96s，631个声明entry/boundary段及762个direct fallback段；
  实际出现的verify_description/scope/preparation为497/338/232次，在各观测段内同一
  参数组最多一次。六个其他registry body未在parent出现，child不外推。165个bundle
  由独立registered child在删除source后验证，source calls/AST constructions均0。
- 两次health均INSUFFICIENT_EVIDENCE/WATCH、comparable0；没有调度/拓扑授权、没有
  性能提升声明。parent等待、纯document边界检查、fresh process/ownership及标准cleanup
  分别解释；所有已观察finding均KEEP，无借此增加cache/framework或弱化检查。
- 最初learner记录仅一名human response，资格细节未提供，不可推广。owner于2026-10-27
  选择Option A，保留D71.01/D71.02并补Collect/call、三JOIN、[]/None/真实NULLchild与
  earlier binding四项教学说明。没有虚构更多参与者或将后续解释替代原回答。
- 项目emission、batch emit、第二emission和single-file checkedSUM按owner决定独立
  发布；batch64MiB是输出限制，Linux目录首版限制保留。README第二卖点不保证业务逻辑。
- 错worktree writer、主环境重建、只读agent落盘、local NAT隔离以及漏设uv pin事件均
  保留失败/原头/恢复决定。当前全部工具与落盘root独占，reviewer只收冻结文本。每条uv
  固定3.13.13；不声称口头只读已经建立技术隔离，也不把错误环境/网络收据当有效native。
- B3仅有owner明确批准的attempt2例外；之后失败头均按既有规则保留、子提交修复，不
  推得后续rerun权限。Teach split仍按2026-10-27决定HOLD，没有新标记/rebootstrap。
- 独立续行账在B9开工为C167/F423/D155，上限C300/F500/D300；后续操作逐次追加。
  原Phase账的历史UNKNOWN仍保留，不冒充已知总量或零；本片不增加scope或预算。

## 延期接收与 Phase72

未编号延期的主责与决定点在[路线延期表](slices.md#延期-owner)更新；每项只有一个
accountable owner，其他层会审。当前acting lead接收协调/升级与backlog交接责任，
不是替代未来语义决定。Phase88/93保留原路由；93在roadmap的Tentative later ownership
表中，不是可擅删的悬空编号，也不授权实施。详见[Phase72交接](phase72-handoff.md)。

## Closure rule and write boundary

本审计与phase72-handoff是最终Phase71生命周期记录，同一S24普通提交更新受影响
status/route/roadmap读者。只有该提交FF push且自然exact-head CI成功才闭合Phase71；
在此之前是候选，之后以Git和该CI为发布事实，不追加仅重述自身hash/run的文档提交。
S24不改src、tests、package、lock、README、grammar/generated、CI或公开形态，不重建
已接受分发物或重跑旧native。它在自己的docs树上执行普通权威验证与自然CI。
`pietto fmt`、Phase72开局与0.1.7发行都需要各自派发，不由S24自动启动。
