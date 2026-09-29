# Validation Consolidation C01

C01 CANDIDATE; completed only after closure。这是published Phase68 S03之后、S04之前的独立test/development维护，不占20个产品位置。Phase68 ACTIVE，S01–S03 COMPLETED / PUBLISHED，S04 NOT IMPLEMENTED。
基线 `069a5bab80bf8fda1ca04f5a08446fb0f2940881`，tree `dcec7f5e0829b32ac0153e8581a0550bca5889aa`，自然CI36532317073/push/main/attempt1。原S03 HOLD、失败、22/24修复与2/3 full记录保持闭合。
C01派发Section10是唯一预算权威；外部root `/home/mianliwang/.local/state/pietto/evidence/validation-consolidation-c01-20260929T073556Z` 的 `pietto-validation-consolidation-c01-ledger.json` 记录全部starts与失败。当前原生实验/S03 producing closure不变，不重跑source/store/sink campaign。

## 机制、cohort与接受

现有 `RepositoryFactIndex.snapshot(root)` 是lazy first-read、process-local observation cache，不是atomic worktree snapshot。C01扩展它的text-only读取和从实际传入text得到的lowercase；PythonSourceFacts的字段、冻结值、原resolved-root限制、构造器参数顺序和失败parse后重试保持。没有共享mutable AST或policy PASS/FAIL。

Phase57完整模块与四个已有Phase52 text-only source scanners形成41-node测量cohort。Phase57仍使用实际 `_read` seam；每次policy invocation重新取得owner-local sorted rglob命名空间，传入的增改text参与lowercase派生。Base及其namespace在一次invocation内固定，新的invocation观察实际加入/移除路径。Injected strings不修改base cache，parameter case之间不泄漏。观察序列使用tuple保留重复path及其全部冲突内容，不选择last winner。

Text-only cache绑定owner显式选择的lexical路径，保留read_text的UTF8/newline/symlink行为，不将其变成Git tracked清单；父级`..`和其他root不接受。Python facts仍保留原有resolved root身份。修改、复制、relocation后的真实语料用fresh index；相同root的新内容不能凭mtime或HEAD冒充旧capture。普通repo consumers的复用前提是该run/corpus只读且无竞争writer；不声明线程安全或跨worker全局一次。

原Phase57十个substring禁词均非空且不含newline，因而在`\n`连接后的lowercase文本中匹配，等价于在各文件lowercase中匹配。保留comments/strings、lower而非casefold，以及原完整path exclusions。违规报告给出原禁词及全部实际违规paths，避免对整份拼接源码构造巨大expected-negative diff；断言每次仍独立执行。精确S03例外仍仅属于 `src/pietto/_project/project_execution_postgres.py` 的 `psycopg` / `server_version`；其他八项禁令及其他owner、同basename/相似路径反例保持。

| Considered consumer | Disposition / identity purpose |
| --- | --- |
| Phase57 catalog scope scanner及全部旧注入控制 | MIGRATED：text/lowercase共享；每次断言重新选择namespace并执行policy |
| Phase52 aggregate、expression-stage、logical inventory、scalar-signature的四个text scanners | MIGRATED：保留各自rglob、generated排除和断言，text请求不再隐式解析全src；aggregate的实际assigned-name查询仍parse |
| Phase52 lookup、private foundation、parity readiness | ALREADY_SHARED：确有identifier/import/topology用途，保留AST或显式fresh例外 |
| workflow lifecycle ownership | ALREADY_SHARED：literal/import facts；nonrecursive glob及唯一mutable reader不变 |
| 既有RepositoryFactIndex独立reference tests | INTENTIONALLY_FRESH：独立read/parse、Assign/AnnAssign、ignored/relocation验证不共享结论 |
| Phase63/66 audit及其他helper调用者 | 单/少量文件或不同表示，LOW_VALUE/ALREADY_SHARED；无理由为统一形式迁移 |
| differential process acquisition / package-generated-source-wheel witnesses | OUT_OF_SCOPE / INTENTIONALLY_FRESH：原run-owned协调、interpreter/seed/mode/assurance和独立subjects均不变 |

完整navigation及逐consumer selector/representation/scope见外部 `pietto-validation-consolidation-c01-reader-map.json`，它不是collection或placement authority。新增support tests为ordinary；不新增ci_workload类别、registry、scheduler或worker额度。

## 独立等价与变异控制

原fact suite仍独立读/parse全部需要的corpus，保持精确identifier/import/literal/assignment事实。C01增加text-only不parse、malformed Python分界、失败capture重试、changed/add/remove、glob/rglob/ignored显式输入、copy/relocation/lexical alias/symlink、outside-root、overlay组合/无泄漏和corrupt/omitted/extra fact反例。

实际Phase57控制先确认baseline，再注入actual read/path view；缓存warming后仍拒绝，撤销overlay后恢复baseline。故意破坏shared lowercase时，原negative test本身必须报告DID NOT RAISE，证明未缓存上次PASS。小型独立reference直接read_text/ast.parse/lower，不调用待验证的派生实现；有newline的跨文件needle反例说明优化的限制，不将token-membership当substring。

原semantic node IDs/参数案例不删、不改。最终还需要alone/cohort/reordered及当前resource-selected xdist的focused接受、完整collection无旧node丢失、unfiltered guarded3.13和自然CI闭环。

## 当前测量：操作数与wall分开

先恢复S03实际六gate timing：lock/format/lint各约1s，production typing57.026s、test typing49.021s、pytest821.341s，实际`pytest -n 4 --dist=loadfile` /4workers。其930.431s总命令与38tests/46.047s不能归因于磁盘读取；旧full没有单项CPU/RSS/collection/setup统计，保持unknown。

C01有限instrumentation记录本cohort：47,256次text读取/244不同文件、1,802,618,667 returned UTF8 bytes、306 AST parses；候选245次/244文件、9,209,707 bytes、78 parses。rglob requests由280到67（67,480→16,147 underlying results）。在该Python中rglob调用glob，嵌套计数不能相加。剩余read/parse包含合法独立collection/AST检查，不靠消除其目的凑零。

Profile明确显示原caught-negative assertion formatting的difflib成本，以及反复joined lowercase和四个text scanners的不必要AST派生；不能把全部收益称为文件读取收益。最终instrumented wall为121.697s→9.138s，含profiler/counter开销，不作为普通timing样本。

冻结普通fresh-process比较使用两个同基线materialized corpora，排除环境/cache/external evidence。每次包含实际collection/setup/独立消费/teardown；所有Pietto/helper origins均来自对应copy，41个nodes相同、终态全部passed。同core Python3.13.13及依赖，无环境重建。OS缓存未控制，继承hash seed未显式固定，个别随机seed未观测，不夸大为硬件不变的精密因果实验。

初始三组按reference/candidate、candidate/reference、reference/candidate交错执行；该候选中间dict的重复path冲突缺陷在审查中发现。修复后保留未变reference三次，重新执行三次最终candidate及一次instrumentation。原候选4.560s中位数及其全部raw保留为被替代结果，不当作最终接受。

| Ordinary repetition | Unchanged reference seconds | Final candidate seconds |
| --- | ---: | ---: |
| 1 | 51.116 | 4.380 |
| 2 | 50.511 | 4.430 |
| 3 | 51.160 | 4.383 |
| Median | 51.116 | 4.383 |

Reference range 50.511–51.160s；最终candidate 4.380–4.430s。Selected cohort wall disposition=MEASURED_GAIN，median降低91.42%。普通peak RSS reference173292–174428KiB，最终candidate94312–94564KiB；这是整个benchmark进程，不是单cache内存。每次CPU、collection、setup/call/teardown、公共materialization及guarded-command wall保留在外部raw/summary；序列化与公共materialization另列，不把overlapping worker/child加成wall。

这不证明整个validator或hosted CI同幅改善；未重跑instrumented full来制造指标。First Interlude的2412→483 reads /1661→484 parses仍是历史结构结果，没有旧wall gain。InterludeII调度NO_GAIN、IV sharding NO_GAIN保留历史；后来的V/R1及现行四分区治理才是当前placement。C01不恢复旧拓扑，也不增加worker。

## 外部参考处置

只消费三个primary sources的机制，不安装相应平台或缓存测试结论。访问日期2026-09-29。

| Required field | pytest-xdist | Pants | Bazel |
| --- | --- | --- | --- |
| Snapshot/date | stable docs /3.8.0目录；本机3.8.0 | stable docs显式2.33 | live Remote Caching页面，未固定release |
| Problem/constraints | worker各自执行session fixtures | 过细process拆分重复准备 | 重用需要声明真实inputs/environment |
| Semantic/identity model | pytest session不等于跨worker单例 | compatible preparation与隔离边界 | action输入身份不由old success代替 |
| Layering/dependency direction | observation先于consumer断言 | preparation共享不合并独立测试意义 | cache记录不提供授权 |
| Algorithms/data structures/complexity | per-process scope；例子另用lock | compatible groups/batching有成本权衡 | declared inputs/environment与outputs匹配 |
| Interface/version/capability model | core pytest/xdist owner保持 | 不迁移Pietto到Pants | 不建立remote/cache API |
| Testing/operational lifecycle | serial/xdist独立验证 | 比较完整setup+consumption | 当前input和dirty namespace显式绑定 |
| Pitfalls/migration costs | 单fixture不能声称全worker只做一次 | 不兼容cell不能合并 | source在run中变化会破坏reuse |
| Disposition | ADAPT process-local边界 | ADAPT兼容性/成本推理 | ADAPT输入/lifetime原则 |
| WHAT_NOT_TO_COPY | 第二套跨worker锁/存储 | result-cache/test-selection策略及scheduler | remote/persistent cache、替换fresh assertions |
| Pietto owner affected | existing RepositoryFactIndex | owner-local cohort与现有acquisition边界 | C01输入比较与phase-end程序 |

来源：[pytest-xdist how-to](https://pytest-xdist.readthedocs.io/en/stable/how-to.html#making-session-scoped-fixtures-execute-only-once)、[Pants batching](https://www.pantsbuild.org/stable/docs/python/goals/test#batching-and-parallelism)、[Bazel caching](https://bazel.build/remote/caching)。

## Phase-end程序与最终闭环

程序已接到 [development](../development.md#phase-end-acquisition-consolidation)、[phase initiation](../architecture/phase-initiation-gate-v1.md) 与 [CI governance](../architecture/ci-workload-governance-v1.md)。逐Slice优先已有owner；start/midpoint预留；相对实际phase baseline审查new/changed acquisition并在audit-only边界前实施；handoff列出shared/fresh/有据例外、等价/覆盖、操作量/时间/内存及剩余债务。常规review不需health alert；真实scheduler/topology/resource变化仍需单独授权。

封树前完成一次integrated review与实际delta follow-up，最后full313保持所有旧nodes加实际新tests。自然exact-head push/main attempt1必须保留所有当前jobs/steps、coverage、core/Arrow、SDK9、product120/118、22全文及native/replay实际consumer；本地auxiliary按真实输入闭包选择，不以tests-only推断豁免。发布为一次普通sole-parent commit/FF push；原失败保留。完成只由新head自然CI、外部final-state及owned cleanup激活，不预填未来head/run或追加status-only提交。
