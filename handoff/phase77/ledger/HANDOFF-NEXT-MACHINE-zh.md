# 换机接手：Phase77（2026-11-10，Claude → 新电脑上的 Claude Code）

先读本文件，再读同目录 `CLAUDE-HANDOFF.md`（Codex 交接，历史背景）和 `STATUS.md`
末尾的 “Claude continuation — 2026-11-10” 一节。仓库规则以 `AGENTS.md` 为准。

## 0. 不可违反的工作规则（原机记忆的摘要）

- 与 owner 用中文交流；代码、命令、诊断、commit message 用英文。时间对 owner 用多伦多时间，文件里用 UTC。
- **任何 `uv` 调用都要 `UV_PYTHON=3.13.13`**（包括 `uv --version`）；裸 `uv run` 曾把 `.venv` 重建成 3.12。
- commit 只能用 `Mianli Wang <mianli.wang@mail.utoronto.ca>`，不加 Co-Authored-By 或任何 AI 署名；
  绝不用 mianliwang492@gmail.com。commit/push 每批都要 owner 授权；没有 tag/release/PyPI 授权。
- 从不推断 PASS；只引用真实 terminal/exit 记录；失败记录保留，不覆盖。
- Gate 2：`UV_PYTHON=3.13.13 UV_NO_SYNC=1 UV_LOCKED=1 .venv/bin/python scripts/validate.py --timings --oom-guard on --pytest-workers 8`。
  **TMPDIR、uv cache、XDG cache 放到 VS Code workspace 之外**（例如 `/tmp/claude-1000/<run>`）；
  原机 R1/R2 的内存中止实为 VS Code extension host 下约 1,900 个 `rg` 进程占约 81 GiB，不是 pytest。
- 数据库：只用固定镜像 `postgres@sha256:a10c981235b4f635e65df0cfb66a5598064628128505dbc6a3ed4ca303717521`（18.6）和
  `container-registry.oracle.com/mysql/community-server@sha256:7dcc4add9183664de3a214daf85a50c3ba6cccfd7534f700b6561bf5b41885be`（8.4.12），
  campaign 用 `--pull=never --network none`，每引擎一个自有容器、各自的锁、两小时上限、完整清理（D77.02）。
- Phase77 预算：累计 `C280/F850/D10000/S12`（D77.03）。F = 每次 pytest 启动（含失败/中断）；D = 每个外层诊断命令；
  C = 按根因计的修复；S = 范围修复。历史保守上界 D≈5,340（`costs.md`），不是实际用量。
- MySQL nested 载体已定：私有版本化 JSON envelope `mysql_json_envelope_v1`（AD77.01）。

## 1. 当前状态（原机 2026-11-10 09:50Z 停止）

- **main 没有变**，仍是 `f8ccd2c4`。待发布的 batch 是三个 commit，放在 handoff 分支上（`handoff/p77-claude-20261110~1` = `3c7a21cd`）：
  `597a41ec` M77 依赖维护（PyArrow 26.0.1 / Psycopg 3.3.8）、`e429f393` 编辑器 hover/definition/symbols、
  `3c7a21cd` Phase77 route/决定/status 文档。最终 tree `4bb7489a`。
  handoff 分支最上面那个 `handoff/phase77/` commit **绝不能进 main**。
- 最终 tree `4bb7489a` 的 Gate 2 R3 **PASS**（27,619 passed / 41 skipped，`ledger/evidence/batch-gate2-r3-20261110T090804Z/`）。
- batch 审计第 1 轮：**12 条中等问题已确认**（13 条 low），详见 `ledger/evidence/batch-audit-20261110/AUDIT-ROUND1.md`。
  因此按 Lean Gate v3 **不能 push**，要先修、重跑 Gate 2、做第 2 轮审计。
- owner 已授权：这个 batch 在 Gate 2 和审计都干净后 fast-forward push 到 main（2026-11-10）。之后的 batch 仍需各自授权。
- M77 native：MySQL 完整 campaign ACCEPTED、PG TLS 18/18、PG remaining 通过（raw 证据在 owner 的 OneDrive 私有包）。
- 本机这次会话的成本：maintenance/editor 线 F+5（3 次 Gate 2 + 2 次 focused）、C+1（damage 正则）；
  Phase77 S12 workflow D+116、F+0（设计 40、反驳 43、被停的实现 33）。

## 2. 新电脑要做的任务（按顺序）

1. 环境恢复（§3 命令）。
2. **修 batch 审计的 12 条中等问题**（按根因合并，在 batch 的对应 commit 里修，保持一个 slice 一个 commit）：
   - 文档与证据不一致：`docs/execution.md`、`docs/project-package.md` 仍说 26.0.1/3.3.8 资格待定 → 引用新的 M77 native 结果及其范围；
     `README.md`/`project-package.md` 把新 pin 说成已发布 0.1.10 的内容；`docs/development.md` 仍写 26.0.0（low）。
   - `77-m01` 片段要写上：仍装着 pyarrow 26.0.0 / psycopg 3.3.5 的环境现在会被 PIE-R2002 / PIE-R4004 拒绝（参照 `release-notes.md` 里上一次依赖维护的写法），不能说 diagnostics 不变。
   - `docs/status.md` 不能在本 batch 自己的 commit 里写 “PUBLISHED”；改为“本 batch 候选”，发布事实由下一批记录。
     status/D77.03 不应把被 Git 忽略的 `.cache/phase77-recovery` 当作读者可达的依据。
   - `docs/decisions.md` D77.02 仍写 “No commit, push or release is authorized” → 记录 owner 2026-11-10 授权 push 本 batch。
   - `docs/roadmap.md` 编辑器一节仍把 hover/definition/symbols 写成未来工作 → 按 ED.01/ED.02 更新。
   - 编辑器代码两条（`src/pietto/_project/check.py:475` 一个 schema-v2 模块的语义错误会清空整个 root 的导航；
     `src/pietto/_lsp.py:403` 分析完成前的请求得到空结果）：先判断是否属于 ED.02 允许的 fail-closed 行为；
     若保留，在 `docs/editor-lsp.md` 写成已知限制；若修，需重跑编辑器 focused 和扩展 host 验收。
3. 对新的最终 tree 跑一次 Gate 2，再做第 2 轮审计（只看修复）；都干净后 FF push 到 main，等 natural CI。
   下一批第一个 commit 记录发布事实（commit、tree、Gate 2、CI run）。
4. **S12**（`candidates/s12`，已恢复到修复前的状态）：
   - `reviews/s12.md`：BLOCKED 的 R1/R2 根因。
   - `reviews/s12-repair-design.md` + `reviews/s12-repair-design-result.json`：新设计。
   - `reviews/s12-repair-critique.json`：反驳结论 NEEDS_CHANGES（3 条 medium：设计的 Plan P 把 R1 重新归类而非解决；
     会悄悄改变 MySQL 公共诊断；MySQL 在某处返回 NULL 而 Pietto 声称非空）。先回应这三条再实现。
   - `candidates/logs/s12-implement-stopped-20261110/partial-implementation.patch`：被停的实现只改了 `project_sql_emission_ast.py` 四处，已撤销，仅供参考。
   要求：一个 canonical rendered-occurrence 表示，MySQL `lpad` 每个渲染出来的 `?` 有独立有序的 leaf/use，
   renderer、`parameter_uses`、`native_arguments()`、compiled 重建、verifier、public decoder、template 都从它消费；
   PostgreSQL 字节不变；PIE-S2355 header 参数拒绝保留。
5. 把各恢复候选（S08、S10、S11、S12、S14、S16、S25、Decimal，全部基于 `f8ccd2c4`）rebase 到新 main，
   逐个做 focused 验证，再按 route 集成；之后才是 PG/MySQL native 资格认证。S08 还需现树验证 computed named-let 拒绝。
6. 先做一次 Phase77 slice 清点：S01–S07、S09、S13、S15、S17–S24、S26–S27 在原机只有探针/规划材料或缺失
   （见 `planning/MATERIALIZATION-GAPS.md`、`numeric-report.md`、`qualification-report.md`），不要假定已实现。
7. 扩展仓库补丁（`candidate-exports/vscode-extension-claude`：README/CHANGELOG/架构/host 测试）等 owner 决定是否 push。

## 3. 恢复命令（WSL Ubuntu；路径可改）

```bash
git clone https://github.com/MianliWang/pietto.git ~/projects/pietto
cd ~/projects/pietto
git fetch origin handoff/p77-claude-20261110
git worktree add --detach ../pietto-handoff origin/handoff/p77-claude-20261110
mkdir -p .cache/phase77-recovery
cp -a ../pietto-handoff/handoff/phase77/ledger/. .cache/phase77-recovery/
bash .cache/phase77-recovery/restore-candidates.sh ../pietto-handoff/handoff/phase77/candidate-exports
UV_PYTHON=3.13.13 uv python install 3.13.13 3.12.13
UV_PYTHON=3.13.13 uv sync --locked
docker pull postgres@sha256:a10c981235b4f635e65df0cfb66a5598064628128505dbc6a3ed4ca303717521
docker pull container-registry.oracle.com/mysql/community-server@sha256:7dcc4add9183664de3a214daf85a50c3ba6cccfd7534f700b6561bf5b41885be
```

候选的 focused 测试：在候选目录里 `PYTHONPATH=src:tests ~/projects/pietto/.venv/bin/python -m pytest -p no:cacheprovider <selection> -q`
（PYTHONPATH 优先于 `.venv` 里指向 main 的 editable 安装）。完整私有包（含原始会话记录和 raw 证据）在 owner 的
OneDrive `pietto-handoff/`，只在需要追溯时解压，绝不上传到 GitHub。

批量 Gate 2 的 batch worktree：`git worktree add --detach ../p77-batch1 origin/handoff/p77-claude-20261110~1`，
修完后在这个 worktree 里改写 commit（每个 slice 仍是一个 commit），再按 AGENTS.md 的 Gate 3 push。
