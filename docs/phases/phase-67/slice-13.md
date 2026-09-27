# Phase67 Slice13：公开 optional Arrow extra 与 wheel isolation

本 Slice 只交付 P67-A16 的依赖选择与安装隔离。用户批准唯一 selector
`pietto[arrow]` 和 `pyarrow==25.0.1`；core 仍只有
`antlr4-python3-runtime>=4.13.2`，`requires-python = ">=3.12"`、package/CLI
`0.1.0` 保持。结果接口仍私有于 `pietto._project`；Phase69 负责 public alpha。

## Q1：范围与安装矩阵冻结

基线 `8f5333fdf526c3211c98135e7a4cce660864dcc8`，tree
`4dd7c58e276e84e18faeeb2bd8368b2e2423ad79`；自然 push/main CI
`36343560204` attempt1 success。tracked/index 干净，原 `.agents/` 保留。
既有 core CPython3.13.13 Arrow-free，禁止 sync/recreate 或装 Arrow。

| fresh installed-wheel cell | 平台 | 依赖与消费者 |
| --- | --- | --- |
| core-only CPython3.12 | Linux x86-64 | 无 PyArrow；CLI/SQL/package；真实 loader 拒绝缺失依赖 |
| arrow-extra CPython3.12 | Linux x86-64 | 同 wheel `[arrow]`；PyArrow25.0.1；SDK9与product102/100 |
| core-only CPython3.13 | Linux x86-64 | 无 PyArrow；CLI/SQL/package；真实 loader 拒绝缺失依赖 |
| arrow-extra CPython3.13 | Linux x86-64 | 同 wheel `[arrow]`；PyArrow25.0.1；SDK9与product102/100 |

此表是已验证支撑集，不是 environment marker；不推断其他平台/解释器/Arrow支持。
四 cells 串行，各有干净 prefix。`-I`、去除 Python 环境注入、无关 cwd、distribution
metadata、exact wheel bytes 与 resolved module origins 共同证明隔离。wheel/sdist
独立验证完整依赖、唯一 extra、README、console entry 和当前私有 result owners。
hash-pinned requirements 是 tested-wheel integrity 来源；extra metadata 是依赖 selector。

冻结22条路径（A2/M20/D0 ceiling；总上限30、additions≤3、无删除）：

- `pyproject.toml`：exact public arrow extra; unchanged core/version/python。
- `uv.lock`：normal uv lock regeneration。
- `scripts/package_smoke.py`：artifact metadata, fresh core/extra cells, installed origin/identity/laziness。
- `.github/workflows/ci.yml`：same wheel/core/extra route in both existing compiler jobs。
- `ci/phase67-arrow-compatibility-requirements.txt`：verified-wheel prose only; hashes preserved。
- `README.md`：valid checkout and wheel extra commands and verified support。
- `docs/development.md`：current installation and validation route。
- `docs/project-package.md`：public dependency selector versus private result API。
- `docs/phases/phase-67/brief.md`：A16 S13 boundary。
- `docs/phases/phase-67/slices.md`：link S13; keep fixed N67。
- `docs/phases/phase-67/planning-notes.md`：Q1/Q2 concise record。
- `docs/decisions.md`：approved packaging decision。
- `docs/status.md`：conditional S13 closure and S14 next。
- `docs/roadmap.md`：conditional S13 closure and S14 next。
- `docs/references/engineering-lessons.md`：durable installation evidence lesson。
- `docs/phases/phase-67/slice-13.md`：new controlling S13 contract and freeze。
- `tests/test_phase67_slice13_optional_arrow_extra.py`：new principal metadata/lock/isolation negative controls。
- `tests/test_active_phase_lifecycle.py`：sole mutable lifecycle reader。
- `tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py`：new ordinary principal inventory。
- `tests/test_phase67_slice1_ci_governance_and_arrow_readiness.py`：current extra-install route assertion。
- `tests/test_phase67_slice2_result_contract_int_arrow.py`：core-free assertion with new extra/lock。
- `tests/test_phase11_packaging_smoke.py`：real sdist project metadata fixture。

普通新测试为离线 metadata/隔离小控制，自动进入独立collection；真实安装由package gate
串行执行，不新增special placement、worker、job或Arrow experiment campaign。
保护production、public API/CLI/SQL/JSON、private frame/neutral bytes、target pins/receipts。

## 预算与验收

单一外部S13 ledger累计失败启动与修正：diagnostics≤6、focused pytest≤12、causal
corrections≤12、full equivalent默认1/硬上限2、integrated author/Ponytail review1、targeted
follow-up1、Q默认2/最多3、development package starts≤3；final每runtime各1次core/extra/
SDK/product，ordinary commit/push各1、failed-CI child/push/delta最多各1，native strict≤4
（通常3）、docs-only partial continuation≤1且要求输入不变。agents、detached、local
full3.12、DB campaign、CI rerun/dispatch/cancel、release/tag/upload均为0。
保留日志、wheels、raw/native原始bytes；只清理owned临时根。

实际metadata/安装前提、focused/readers/Ruff/Pyright、完整review与唯一follow-up后，
执行Q2、depth-one和一次guarded3.13 full equivalent：static、独立U、四串行分区、
coverage/health、generated/golden/package、双runtime原SDK/product。22份neutral documents
全文跨runtime且相对S12保持，不以hash替代全文比较。core真实loader必须返回既有
`ARROW_DEPENDENCY_MISSING`，无stub/fallback/vendor；core和extra均不得eager import PyArrow。

## 发布与终态条件

reviewed/tested/sealed tree经普通sole-parent commit/FF push、自然exact-head push/main
attempt1全部15jobs、当前27个raw artifacts的ID/length/SHA/context、SDK/product消费者及
fresh普通native receipt copies的PG/MySQL/aggregate strict全部通过，Slices01–13才为
`COMPLETED / PUBLISHED`。native facility没有执行本Slice安装矩阵。
Phase67 `ACTIVE` / N67=16；Slice14 `NEXT / NOT STARTED`，Slices15–16 `NOT STARTED`；
Phase66 / Interlude V / R1保持 `COMPLETED`。不开始Slice14，不上传或改版本。

## Q2：收敛候选

唯一author/Ponytail审查与定向复核已关闭全部finding：metadata单值header按完整cardinality
核验，实际check/PostgreSQL/MySQL调用在同一installed process观察lazy import，extra环境在
acquisition前拒绝已有或symlink prefix。当前全Phase67/package/lifecycle读者、Ruff及两类
Pyright通过；3.13真实development core/extra及102/100产品通过。没有production变化或新
报告schema；最终双runtime四cell、9SDK/102product、22全文、guarded完整equivalent、
depth-one、Git/自然CI/raw/native仍全部是发布必需条件，实际结果由同tree外部证据绑定。
