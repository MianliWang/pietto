# Claude Code 接手：Phase77–80 与独立编辑器工作

状态：**CHECKPOINT STOPPED / READY FOR CLAUDE CODE HANDOFF**。
用户于 2026-11-09（America/Toronto）要求：达到一个 checkpoint 后停止，由
Claude Code 接手。Codex 已正常中断 R3 长验证，保留全部证据并停止；不启动下一轮验证或产品工作。
编辑器 Gate 2 的条件 START 已撤销，明确 **NOT STARTED**。

## 先读与执行边界

工作区 `/home/mianliwang/projects/pietto`；本文件所在目录下的相对路径均以
`.cache/phase77-recovery/` 为根。先读仓库 `AGENTS.md`、当前
`docs/decisions.md`、`docs/status.md`、`docs/phases/phase-77/route.md`。
正常工作遵循 Ponytail FULL；非平凡语义工作沿用仓库 semantic-convergence skill。

- 已授权：完整 Phase77 S01–S27，累计 `C280/F850/D4000/S12`；PyArrow
  `26.0.1` + psycopg/psycopg-binary `3.3.8` 的独立 M77 维护候选；相应本地 Gate 2。
- 数据库：仅固定缓存 PostgreSQL 18.6 / MySQL 8.4.12，`--pull=never --network none`，
  每引擎最多一个自有容器、每 campaign 最多两小时，使用既有各引擎锁，完整自有清理。
  PostgreSQL 锁是 `/tmp/claude-1000/pietto-docker-campaign-postgres.lock`；
  MySQL 锁是 `/tmp/claude-1000/pietto-docker-campaign-mysql.lock`。不能另建仅供某两个脚本共享的锁。
- 已授权宿主机从官方 PyPI 准备固定测试 wheels；不等于新增产品依赖或容器联网。
- **任何 `uv` 调用，包括 `uv --version`，必须设置 `UV_PYTHON=3.13.13`。**
  尽量离线使用已有缓存。不要从 sandbox PID namespace 的 `ps` 推断宿主机任务不存在。
- 没有 commit、push、tag、release、签名、发布或主动外部 CI 授权。本次均未执行。
- 编辑器已批准标准 LSP hover/definition/documentSymbol，以及按文档版本失效的临时核心快照；
  精确绑定才可跳转，未知/冲突为空，请求时不重新解析、检查、编译或读盘。
  metadata 与 relation-column 格式不变；model view 在后。
- 新后端已选小型自有 adapter、sqlglot 仅测试对照、DuckDB 先。阶段标签不变：
  有限 Phase79 DuckDB 路径排在 Phase78 SQLite 之前。Phase78/79/80 的具体合同、依赖与预算未获批准。

## 两项尚未回答的 Phase77 决定

1. 将 D 上限从 4000 调到 10000，保留 C280/F850/S12 和所有历史成本；不能把“继续”当作同意。
   `costs.md/json` 保留重建过程。旧 `D<=2773` 因按 agent 名错误排除混合工作而撤回。
   当前保守上界 5340 不是实际超支证明，也不是剩余额度；C/F/S 不能默认为零。
   新 Phase77 产品/诊断 campaign 已暂缓；独立维护、编辑器与未来阶段规划继续。
2. MySQL nested carrier：私有版本化 JSON envelope，或 count + 每 child 的 JSON arrays。
   原 async 问题尚无答案。S21–S23 的首个 consumer 不能先选方案再实施。

用户此前已经批准完整 27 片、依赖候选、固定数据库范围与编辑器快照；不要再次询问这些已决事项。

## Git 与工作树

- 核心 canonical HEAD：`f8ccd2c44a2d9adf431a496bd9bbae037783176f`；发布基树：
  `460e3e135d1dcb0b926928bc2632a889410f258a`。此前自然 CI `42489408515` attempt 1 为 21/21；
  这是既有 Phase76 发布记录，不是本次脏树的 CI。Phase76 完成；包版本仍为 `0.1.10`。
- canonical 当前保留编辑器源代码/测试、决策与状态/路线文档，**没有把全部 M77/Phase77 候选合入**。
  主要代码是 `src/pietto/_editor_facts.py`、`_lsp.py`、`_project/check.py`；另有 LSP tests、specs、
  `scripts/package_smoke.py` 的能力声明和 editor release fragment。
- 原用户未跟踪文件 `.agents/`、`NUL`、品牌 ZIP、`out_proj2_semi_pg.txt` 不属于清理范围。
  不要 prune 原 S25 的 stale worktree administration。
- 扩展仓库 `/home/mianliwang/projects/pietto-vscode-extension-claude`：HEAD
  `e61444f90e3f426557fd805b66e3d75e20b55e5a`，版本 0.3.0；当前 7 个 tracked dirty 文件：
  README、CHANGELOG、docs/architecture、tests/host/common.ts、tests/host/index.ts、tests/runHost.ts、
  tests/sync_language.py。没有新增私有 LSP adapter。没有改版本或 Marketplace 发布。

## 恢复事故与证据规则

旧 `/tmp` 候选、wheels、raw logs/receipts 全部丢失，宿主与 sandbox 均确认。
旧 B1/B2/B3 和 editor `a0c662...` seal 对象也不在 canonical Git。
源码通过 retained tool inputs 恢复；`records/` 保留原 session/source/line/call_id/output，
`session-index.json`、`records/gaps.json` 标明来源和损坏尾记录。
恢复的源码、tool summary、synthetic self-check 均不能替代真实 target receipt。
新候选、环境和 raw evidence 统一保留在这个工作区的 ignored `.cache` 下，不能仅留 `/tmp`。

旧 editor 的 27619/41、41 goldens、13 PASS/1 SKIP 只是历史工具记录；本次已另做新验证。
旧 SQL-preview 外部证据不是 hover/definition/symbol 验收。旧 Phase77 B3
`e1155f...` 与其 wheel 不可直接使用；没有新的 Phase77 产品 native qualification。

## M77 独立维护候选

位置 `candidates/maintenance`，仍为隔离的实际 Git clone。

| 绑定 | 值 |
| --- | --- |
| dirty tree | `2af0e2e47a062eb747ed5d2cd664c2dab5da4aed` |
| tracked patch SHA-256 | `548e72276b20c2bff3bb0613a527ef230fb9095942b562dca32a6150da12e1cc` |
| uv.lock SHA-256 | `b2cc96b25b0b9f2225c4529f0123ae869cd804af0578b4f83c931a15aa893064` |
| wheel SHA-256 | `f4c96921c4d4ceb057830f2dd21f2e634325dac2bef933532747ae4aab963a73` |
| sdist SHA-256 | `15b43b884064e0837bbfa891b8eea44996acc2592bd169b5a6ea96e29d29cfff` |

产物 `runtime/dist/`；隔离环境 `runtime/venvs/{core-dev,native}`；固定 wheels 在 `runtime/wheelhouse/`。
`runtime/candidate-artifacts-rebind-manifest.json` 绑定修正后的文档与 lock；保留原 manifest。
静态复审 `reviews/maintenance.md`。

新通过的证据：

- focused：`evidence/maintenance-focused-20261110T014824Z-oz1bSc/`，408 passed，exit 0。
- MySQL：`evidence/mysql-maintenance-r2-20261109T030000-0500/`，`verdict.json` ACCEPTED，
  完整 native/public/bundle/context/IPC/cancel/deadline 与 owned cleanup。
- PG remaining：`native-maintenance/runnable-rebind/pg-remaining/`，compare exit 0，
  rows/ADBC 生命周期、取消、相关保留边界；清理已确认。
- PG TLS：`native-maintenance/runnable-rebind/pg-tls-r2/`，18/18，compare exit 0，清理已确认。
  原 `pg-tls/` 的 16/18 失败保持不动：旧 oracle 把公共 AMBIENT_ENVIRONMENT category
  与 EXECUTION_AMBIENT_CONNECTION_PROFILE detail 混淆，并抹平 rows/ADBC 边界。
  独立复审对照 f8 代码和已有测试确认是 oracle 缺陷。R2 只改 C1 oracle/judge 与机械绑定，未改产品。
- package：`evidence/maintenance-package-r2-20261110T043000Z/RESULT.md`，独立 retained-artifact smoke PASS，
  前后候选与产物相同；core/Arrow 安装边界与 CLI/LSP/project/emission 检查通过。

全量验证记录：

- `evidence/maintenance-gate2-20261110T020611Z/`：8 workers，pytest 约 93% 后 resource abort，exit 75。
- `evidence/maintenance-gate2-r2-20261110T041227Z/`：4 workers，pytest 255 秒后 resource abort，exit 75。
  两次五项前置 gate 均通过，未完成 pytest；无产品失败结论；输入绑定未变。
- **R3 已中断，不再运行**：`evidence/maintenance-gate2-r3-20261110T042408Z/`，
  `--pytest-workers 1 --pytest-maxprocesses 1 --oom-guard on`，完整六项 gate，10 秒 RSS/内存监控。
  包 smoke 使用上面的独立同产物 PASS，不重复运行。实际 terminal 为 exit 130：按用户交接要求中断，
  不是 PASS、资源保护事件或产品失败。完整数据见末尾。
  此前两个失败的运行期无每 PID RSS，不能断言约 33 GB 压力来自某个进程；R3 监控补上了这一缺口。

## 新维护／编辑器组合候选

位置 `candidates/editor-combined`；先叠加精确 M77 patch，再加 canonical editor 10 个输入。
`scripts/package_smoke.py` 保留 Arrow pin 和 LSP capabilities 两个独立 hunk。

| 绑定 | 值 |
| --- | --- |
| dirty tree | `a5d300bb1e6a0216ee95b62552466f407cdc40cb` |
| tracked binary diff SHA-256 | `a1a867ec37151a58c38db75902c4f14b32bbbaf1967fa85c0cb17293f3aa6799` |
| wheel SHA-256 | `9d2b31b0fa72ee40b1f671b5aa50f5eb0fedc83fdc19fe3d20bf2378e2921dd2` |
| sdist SHA-256 | `3639469b78ba7ca78cb42d590ebd7c608767707e5f4cee98b3537229674bc7bf` |

四个 intended untracked editor 输入由临时索引树与 manifest 完整绑定，不能仅靠 tracked diff 判断闭包。
`reviews/editor-combined-candidate-manifest.json` 和 `reviews/editor-candidate-preparation.md` 是输入明细。
独立复审 `reviews/editor-combined-review.md` 没有具体 finding，但不替代运行验证。

- focused R2：`evidence/editor-focused-r2-20261110T043000Z/run/`，88 passed（12.23s），41 goldens
  （34 SQL byte-exact + 7 JSON structural），exit 0。R1 缺临时目录、collection 前 exit 3 的记录保留。
  `project/check.py` 是 golden 的输入闭包；“未改 fixture 所以不跑 golden”的旧判断已经撤回。
- package：`evidence/editor-package-r1-20261110T044000Z/run/`，独立精确产物 smoke PASS。
  wheel/sdist 在 `evidence/editor-focused-20261110T051000Z/run/dist/`。
- installed-wheel Python：`runtime/editor-runtime/installed-wheel/bin/python`；editable core 环境是
  `runtime/editor-runtime/core-dev`。不要拿 M77 wheel/环境冒充 editor。
- 扩展综合报告：`evidence/editor-host-r2-20261110T052200Z/RESULT.md`。
  Node 27/27；开发 host 与安装 VSIX host 各 13 PASS + 1 旧 Python 未配置的明确 SKIP。
  开发 host 的成功 raw 在相邻 `editor-host-r4-20261110T053700Z/host-dev.{log,exit}`；
  综合报告目录的 `host-dev.exit=1` 是必须保留的旧启动失败，不能引用为成功。
  安装 host 的成功 raw 是报告目录的 `host-vsix.{log,exit}`。
- 扩展 diff：`6257331fa73ff477405897fb4b229fb298418f70364a34a304b4baebb5688d6a`；
  VSIX：`8c293c8690f81c5760d8c58a98729ae30dc4c0a97d2e65db13ef342729256622`。
  原扩展证据未被覆盖；安装测试在恢复目录的隔离扩展副本中运行。
- **组合 editor Gate 2 从未启动**。预备包是
  `evidence/editor-gate2-prepared-20261110T053000Z/{PLAN.md,run-editor-gate2.sh}`，
  launcher SHA `70a3ffd71312450ed696eaf73b05e5c4f8236126d41e7d140beba0a569d6b28a`。
  用户要求 checkpoint 后停，已经撤销其条件 START；不要把现成脚本当作当前运行授权。
  未来用户续作后应先重绑输入/宿主、确认没有现存全量任务，再启动一次；M77 Gate 2 不替代这个组合树的 Gate 2。

VS Code 缓存是扩展 `.vscode-test/vscode-linux-x64-1.145.2/code`，node_modules 也在。
设置 `VSCODE_EXECUTABLE`、精确 `PIETTO_TEST_PYTHON`、`PIETTO_TEST_PYTHON_ARGUMENTS='[]'`；
Node tests 也需要这个 Python 环境。WSLg 缺 `/run/user/1000`，使用短的自有 `/tmp` XDG runtime，
不能用很长的证据路径作为 Unix socket 路径。原环境启动失败已保留；不要为补 optional skip 下载旧 Python。

## Phase77 恢复候选：尚未获得新的产品 native / Gate 2

`candidates/{s08,s10,s11,s12,s14,s16,s25}` 与 `candidates/decimal/repo` 是分别恢复的候选，
并非一个已接受的集成树。详见 `scalar-report.md`、`decimal-report.md`、`windows-report.md`、
`tuple-asof-report.md`。旧 B3 不能从这些名字直接推定重建成功。

- **S12 BLOCKED**：MySQL LPAD 重复使用实参，SQLParameter/use 仍按源叶创建一次。
  `rendered_constant_chains`、`value_requirements`、独立 `node_expectations`、row binding obligations
  等尚未全量按 dialect/rendered occurrences 闭合。见 `reviews/s12.md`。11 focused tests 不能证明 native args 顺序/数量。
  现有 header parameter 的 PIE-S2355 拒绝保留，不可为让测试通过而扩大语义。
- S08 已恢复 computed named-let construction refusal 的最终编辑，仍需独立现树验证。
- S11 保留重复 port 拒绝而非去重；不同 alias 必须保留。
- S16 最终只允 PG E / MySQL X 字面量路径、有效空 X'' width 0、NUL 拒绝。
  最终 diff SHA `37a0f165df2194c809899eeea0b905cbc255286eaa08f85060924325c5de71b0`。
- `numeric/` 的 probe/parent 源码已恢复；safe_unary 的每条 literal/physical/prepared 路线都是 +,-,+。
  旧 PG119 record raw 不在，不能重建假结果。
- `qualification/` 中有 common flat/Decimal/S16 builders/judges；PG flat parent 仍有缺失输入。
- `planning/materialized/` 是原始准备物；`planning/MATERIALIZATION-GAPS.md` 明确未应用的后续 hunks。
  不是完成的产品候选或已批准的 native campaign。

## 未来阶段准备

`planning/duckdb-gate1-ready-proposal.md` 与 `planning/phase80-gate1-ready-proposal.md` 是新整理的
**未批准建议**；`planning/continuation-decision-sheet.md` 汇总真实未决边界。
DuckDB first vertical、输入捕获上限/API、五库 dtype/null/CSR/plot 精度、版本 pin/平台和预算仍需 Gate 1。
这两份提议不能替代 Phase77 预算或 nested 决定，也不能宣称 Phase78–80 已实现。
没有 SQLite 实现候选。不要自动启动未来阶段。

## Claude 接手后的最短顺序（需要用户恢复工作的指令）

1. 先读本文件末尾真实 checkpoint，并核对 Git、候选输入、已有进程和证据路径；不复跑已通过且输入未变的检查。
2. M77 R3 因交接中断，完整 Gate 2 仍未完成。依据保留的 raw/RSS 选择适当的既有运行参数，
   用户恢复工作后再安排完整验证；不得拼接未完成片段为 PASS，也不要复跑已通过的独立 package/native 检查。
3. 编辑器已有 focused/golden/package/两个 host 通过；完整组合 Gate 2 仍待执行。不要把它报为已通过。
4. 在用户回答 Phase77 两个问题后，先修 S12 occurrence 根因，再按现路线集成/资格；保留历史预算、失败和未知。
5. 发布、发行与后续阶段启动仍由各自授权和真实 Gate 决定。本次 checkpoint 不附带任何 publication authority。

## 最终 checkpoint

Checkpoint 已完成：维护 native/package 与编辑器 focused/golden/package/真实 host 验收均有新证据；
两套完整核心 Gate 2 都没有 PASS，保留给 Claude 后续处理。

R3 从 `2026-11-10T04:29:43Z` 到 `2026-11-10T04:57:54.593690Z`，约 28m11s。
五项前置 gate 通过；pytest 使用一个 worker、收集 27,634 项，约到 2%。
为按用户要求交接，向重新确认身份的 validator PID 573773 发 SIGINT；
`run/terminal.json` 实际 exit 130，通用 status 为 `FAILED_OR_ABORTED`，
本次具体原因是 **USER_REQUESTED_CHECKPOINT_INTERRUPTION**，不是 OOM 或产品失败。
`run/resource-monitor.status` 为 `stopped`，所有候选 before/after 绑定相同。

宿主检查确认本轮 launcher 572904、monitor 573771、validator 573773、tee 573774、
uv 576153、pytest 576156、worker 576157 与自有 probe 均已退出；PGID 572904/576153 无残留。
这些 PID 是终止记录，不是未来可以直接 kill 的授权；接手时任何进程动作都必须重新确认身份。
所有子代理已结束工作，编辑器 Gate 2 从未启动，没有任何排队的自动 START。

R3 监控中 `MemAvailable` 为 29,566,516–36,791,736 kB；cgroup current 最高
16,997,687,296 bytes，pytest direct child RSS 最高 1,059,732 kB。
一 worker 的本轮片段未触发资源保护，但速度不足以作为快速交接前的完整验证。
不要因此推断四/八 worker 的先前内存压力原因已被证明。

最终 canonical HEAD 仍为 f8ccd2c44a2d9adf431a496bd9bbae037783176f，staging 为空，
`git diff --check` 通过。所有本地改动、恢复候选、失败记录与 raw evidence 留在原处。
没有提交、推送、tag、发行、Marketplace 操作或外部 CI。
