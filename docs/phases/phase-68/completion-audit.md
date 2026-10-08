# Phase68 完成审计：三层证据、证据域对账、成本复盘与交接输入

S01–S19 与 C01 已发布；S20 **ACTIVE / CANDIDATE**，Phase68 **ACTIVE — completion candidate pending S20 closure**；
性能插段与 Phase69 均 NOT STARTED。本审计的实质判断是：现有证据支持 A01–A22 在已记录、经独立检查的域内满足；
S20 自己的回归、普通发布、自然 CI 消费者与清理仍待完成，不能以本矩阵文字替代。生效只依
[唯一闭环规则](slice-20.md#唯一闭环规则)，最终身份由该规则指定的外部记录在观察后绑定。

## 权威与证据索引

规范采用 [brief 的二十二项原义](brief.md#三层验收)（P68-A01–A22；下表首列逐字保留其编号与名称，并概括“为真”“验证”两栏，全文以 brief 为准）；
路线采用[固定二十行](slices.md)；各 Slice 合同只作导航，S19 交接表只作输入，不替代本审计。

| 简称 | 实际 owner / authoritative entry |
| --- | --- |
| CB / CL | [project_compiled_build](../../../src/pietto/_project/project_compiled_build.py) `build_compiled`；[project_compiled_loading](../../../src/pietto/_project/project_compiled_loading.py) `load_compiled`、`semantic_build_identity`、`supported_compatibility` |
| TPL | [project_execution_template](../../../src/pietto/_project/project_execution_template.py) `prepare_live_template`、`prepare_compiled_template`、`bind_values`、`describe_compiled_binding` |
| EX | [project_execution](../../../src/pietto/_project/project_execution.py) `prepare_compiled_execution`、`compiled_attempt_outcome`、`compiled_closing_facts`、`compiled_source_description`、`pinned_modules` |
| OUT / RDR | [project_result_output](../../../src/pietto/_project/project_result_output.py) `prepare_output`、`verify_output`；[project_execution_reader](../../../src/pietto/_project/project_execution_reader.py) `bind_native_output`、`decode_native_rows` |
| 路线 | [PostgresExecution](../../../src/pietto/_project/project_execution_postgres.py)、[PostgresADBCExecution](../../../src/pietto/_project/project_execution_postgres_adbc.py)、[MySQLExecution](../../../src/pietto/_project/project_execution_mysql.py)；来源资格 [qualify_sources](../../../src/pietto/_project/project_postgres_source_assurance.py)、[recognize_view](../../../src/pietto/_project/project_mysql_view_source.py) |
| GRD | [project_guard_program](../../../src/pietto/_project/project_guard_program.py) `prepare_program`；[project_guard_runtime](../../../src/pietto/_project/project_guard_runtime.py) `prepare_guarded_execution`、`verify_guarded_execution` |
| WS / ST | [project_job_workspace](../../../src/pietto/_project/project_job_workspace.py) `create_workspace`、`open_workspace`、`storage_profile`、`supports`；[project_job_store](../../../src/pietto/_project/project_job_store.py) `claim_publisher`、`open_attempt`、`record_attempt`、`interrupt_attempt`、`cancel_job`、`query_operation`、`load_job` |
| CAP / VER | [project_job_capture](../../../src/pietto/_project/project_job_capture.py) `begin_capture`、`checkpoint_snapshot`、`retain_checkpoint`、`release_retention`、`classify_files`；[project_job_store_verification](../../../src/pietto/_project/project_job_store_verification.py) `verify_store` |
| RP / XR | [project_job_replay](../../../src/pietto/_project/project_job_replay.py) `accept_saved_read`、`register_consumer`、`open_replay`；[project_job_extraction](../../../src/pietto/_project/project_job_extraction.py) `begin_extraction`、`accept_recovery`、`begin_continuation` |
| DLV / SNK | [project_job_delivery](../../../src/pietto/_project/project_job_delivery.py) `accept_window`、`accept_sink`、`register_stream`、`relay`、`retire_stream`；[project_job_sink](../../../src/pietto/_project/project_job_sink.py) `create_sink`、`open_sink` |
| PUB | [project_job_publication](../../../src/pietto/_project/project_job_publication.py) `accept_publication`、`prepare_publication`、`publish_generation`、`publication` |
| RT / GC | [project_job_runtime](../../../src/pietto/_project/project_job_runtime.py) `open_runtime`、`reconcile`；[project_job_collection](../../../src/pietto/_project/project_job_collection.py) `retire_generation`、`protection`、`collect`、`availability` |

独立消费者与检查器：[S10 check](../../../tests/_pietto_phase68_slice10_check.py) `check_matrix_record`、`check_matrix_origin`；
[S14 check](../../../tests/_pietto_phase68_slice14_check.py) `check_capture`、`check_recovery`、`check_r1`、`check_history`；
[S17 check](../../../tests/_pietto_phase68_slice17_check.py) `check_all`；[S18 check](../../../tests/_pietto_phase68_slice18_check.py) `check_install`；
[S19 check](../../../tests/_pietto_phase68_slice19_check.py) `required`、`cross_check`、`check_matrix`、`check_j01`、`check_j02`、
`check_storage`、`check_tuning`、`check_compat`、`check_evidence`、`joint_model`；入口 [S19 probe](../../../scripts/phase68_slice19_probe.py)。

| 证据锚 | 实际身份 | 类别 |
| --- | --- | --- |
| E19 campaign04 | 生产者候选 tree `794858a8e90552adaf6ad7da56e204f4d9a25806`（readiness4，产品/打包闭包与 B19 字节相同），六个组件 exit 0 | NATIVE；原生合格生产 profile |
| reuse-bridge4 | compat、consumer、S03 来自 campaign02（readiness2 `fab78e0e`）；S09、S08 与 postgres_rows 对比对来自 campaign03（readiness3 `899a10af`）；可执行单元 digest 相同，tuning() 只差路线选择 | 有界复用，未拼接失败 attempt |
| check02 | 检查器输入 tree `6160561d39c1640d2b8193ebd8ebc73dc1a1554e`（含 C25 修复）、campaign04 目录与 reuse-bridge4；exit 0、584.45 s | 最终独立验收 |
| S19 发布 | `ec8a03775ab1f52b72bfd72429a744252e94bcf8` / tree `1273371325f042030879f4305973d9b24cab3aa3`；full01 18,588 passed；CI37705001971 attempt1、15 jobs、`PASS_EXACT_HEAD_ALL_CONSUMERS` | CURRENT_LOCAL / CURRENT_CI（S19 时点） |
| B20 维护 | `b4cb9845fa59cec6a3303e2dd21a3ce070f21d72` / tree `66fd816eb92d1c22ed3bee72cbe65277f4aaa61d`；full 18,588 passed；CI37711770935 attempt1、15 jobs、集合相对 S19 不变 | 当前锁定 profile |
| 产品身份 | wheel `pietto-0.1.0-py3-none-any.whl` SHA-256 `cf81718b12dfcc9161719063b7f171d65299eb662507cdf37467d64a75543979`；sdist `5537168badc910b20eb6176bb2423b436d355b0f5a84ac868d0aa2dd90cfa538`；代码身份 `133d424d7f85c44d176326818b882ad6c838e4f2b4349feb2cec03fbfaaeafe0` | 打包输入（PKG-INFO、`pyproject.toml`、`README.md`、`src/**`）自 B19 至 B20 未变 |
| S20 只读重算 | aud01 矩阵清点与已记录 raw digest 复核、aud02 计时复算、aud03 发布链对账、aud04 成本表核对、aud05 R1 尾段计时读出 | CURRENT_LOCAL 审计；不是新的原生执行 |

“ACQUIRED” 或生产者 `checked` 字样不是验收：check02 在 worker 之外对每个 cell 的 raw 重跑 S10/S14 原定律与 R1 尾段，
并在真实 raw 的副本上施加全部损坏族。S20 不把 S19 证据改称 CURRENT_LOCAL，只在其原始生产/检查身份下审计。

## A01–A22 三层矩阵

每行“判定”是已批准域内的实质审计判断；最终 PASS 统一受 S20 闭环条件约束。类别：NATIVE（campaign04/check02）、
SIGKILL（真实子进程 kill）、REAL_COMPONENT（SQLite/文件系统）、INJECTED、MODEL，以及当前 pytest/CI 回归。

| ID / 原义 | 能力与适用域 | owner / 权威输入 | 接通的消费者与观察 | 判别负例 → 拒绝定律 | 证据与限制 | 判定 |
| --- | --- | --- | --- | --- | --- | --- |
| P68-A01 双执行入口：live 编译入口与无源码、无需源语言重编译的运行包；可信构建来源、独立 loader、重新授权；两入口同模板，换包/缺成员/错误版本/错误授权被拒 | live 与 source-free bundle 两入口进入同一私有 template/binding；3 路线 × live/bundle × source/installed；`pietto.compiled-execution.v1`、版本向量 (1,1,1,1) | CB `build_compiled`（已验证 artifact、guard、refinement）；CL `load_compiled(raw, expected_pin, accepted_producer, accepted_compatibility)`，信任输入全部由调用方给出；每次加载新语义根 | check02 对 PG 1,328 与 MySQL 636 个 cell 逐一重跑 `check_matrix_origin`（禁止的源语言调用、成员字节、安装来源）与 `check_matrix_record`；live/bundle 各占一半 | origin_swap → `S10_MATRIX_INSTALLED_ORIGIN`；bundle worker 源语言细化 → `S10_MATRIX_SOURCE_FREE`；[S10 test](../../../tests/test_phase68_slice10_compiled_bundle.py) `test_closed_envelope_corruption`（格式、头、成员缺失/重排/重复）；[S11 test](../../../tests/test_phase68_slice11_job_store.py) `test_fresh_trust_inputs_and_separate_compatibility_dimensions`（错误 pin/producer/compatibility → `JOB_TRUST_INPUT`/`JOB_COMPATIBILITY`，改写字节 → `COMPILED_CONTENT_PIN`）；S17 bundle 在当前代码 `COMPILED_COMPATIBILITY` | NATIVE + pytest；pin 与 producer 是调用方提供的内容身份，不是签名或认证；receipt/hash 不授予权限 | SATISFIED_IN_RECORDED_DOMAIN |
| P68-A02 类型化可复用参数：模板、不可变值绑定、attempt 分离；值敏感事实失效；slot/use 保持；两组合法值与非法值，LIMIT 证明失效，接受后改容器不改提交 | `bind_values(template, supplied)`；四种可绑定叶值 Bool/Int64/有限 binary64 Float/Text，与七个结果 scalar 分开；LIMIT/frame/offset 结构性 | TPL、[binding verification](../../../src/pietto/_project/project_execution_binding_verification.py)；S11 binding record 的 typed wire（True≠1、±0 位） | R2_bound A/B/A_again 与 guarded binding_A/B/A_again cell 由 `check_matrix_record` 判值；S13/S16 的 accept_* 逐值相等 | 非法向量、接受后修改调用方容器、A/B/A 不变性：[S04 test](../../../tests/test_phase68_slice4_binding.py) `test_reusable_immutable_a_b_a_and_failed_bind`；Int 溢出/符号、Text 长度、±0 由原 verifiers 重建 | NATIVE + pytest；不为 Decimal/Timestamp/UUID 增加参数位；LIMIT/frame 不可绑定 | SATISFIED_IN_RECORDED_DOMAIN |
| P68-A03 显式执行身份与权限：query、target、connection、statement、job/generation/attempt 与 role 绑定；无 ambient credentials；foreign/stale/错误目标/角色/句柄拒绝 | 分层身份 declaration/use/slot/output、binding、attempt；`ws-`/`job-`/`bind-`/`gen-`/`att-`/`pub-`+epoch/`op-`；进程内不可复制的 SavedRead/Recovery/Window/Sink/Publication acceptance | EX access 与 premise；ST `claim_publisher` 与条件写端围栏（rowcount=1）；RP/XR/DLV/PUB 的 accept_* | check02：`MATRIX_FRESH_ATTEMPTS`（PG 1,816、MySQL 872 个 attempt 全部唯一）；J01 谱系；J09；S08/S09 控制族的 role/transaction 替换 | reused_attempt → `MATRIX_FRESH_ATTEMPTS`；foreign_predecessor/laundered_attempts → `J01_LINEAGE`；过期接受、外来兼容；[S03 test](../../../tests/test_phase68_slice3_execution.py) `test_explicit_access_refuses_ambient_libpq_redirect`；[S09 test](../../../tests/test_phase68_slice9_execution.py) `test_premise_is_exact_not_ambient` | NATIVE + SIGKILL（S11 进程历史）+ pytest；身份字符串不认证任何人，私有合作用户边界是前提 | SATISFIED_IN_RECORDED_DOMAIN |
| P68-A04 三adapter对等：PG rows、MySQL rows、PG ADBC 兑现同一声明矩阵；不取最弱交集、不 silent fallback；缺口不以 UNSUPPORTED 冒充 | PG 166 个声明 case × 2 路线、MySQL 164 个声明（5 个原 owner 排除）× 1 路线，各 × live/bundle × source/installed | 三条路线 owner；S19 `required()` 从下层 case owner 与字面 TOTALS 独立推导，`cross_check` 与生产者 `native_manifest`/`r2_families` 互核 | check02 `check_matrix` 与逐 cell 重检；S20 aud01：观察集合与必需集合相等，缺失 0、外来 0、重复 0 | omitted/duplicated/foreign/relabeled/recast → `INVENTORY_*`；排除换 owner → `INVENTORY_EXCLUSION`；缩短的清单 → `INVENTORY_MANIFEST`/`INVENTORY_R2`；S18 并集无回退控制 | NATIVE；排除只来自原 owner 的拒绝，不转用于 PostgreSQL；三路线各有自己的 premise，不是同一安全域 | SATISFIED_IN_RECORDED_DOMAIN |
| P68-A05 通用结果衔接：已支持平面查询族接 retained outputs/PB/AR；七 scalar 原域；不靠首行推断；命名 corpus 与 typed BAG/精确值反例 | OUT 从完整 terminal 取有序输出；RDR 绑定原生 metadata；Int、Bool、Float、Text、Decimal、Timestamp、UUID；source/projection、imports、JOIN、aggregate/window、ORDER/LIMIT、DISTINCT/SET | OUT、RDR 与 Phase67 RC/PB/AR | `check_matrix_record` 以 S06/S07 字面 oracle 判完整值（BAG 与有序 case 顺序、NULL、类型）；R2_seven 39/65 values/empty/null；tuning 与 J02 值对照 S06 字面 | changed_value/collapsed_duplicate/swapped_ordinal/reversed_order → `S10_MATRIX_ORIGINAL_FULL_VALUES`（C25 后协调全部副本且留在声明域内）；J02 值损坏 → `J02_EFFECT`；dropped_value/equal_but_wrong → `TUNING_VALUES` | NATIVE；七 scalar 与四叶分开；无新精度域、嵌套、pandas 或算子；原 exclusions 保留 | SATISFIED_IN_RECORDED_DOMAIN |
| P68-A06 默认guards与运行期义务：默认履行 single-match 等义务；关闭额外 SQL 后缺强证据拒绝；相同 payload 两次仍算两次；WHERE/LIMIT/去重不能抹掉义务 | guard 与 data 同一已验证语句（PG materialized CTE、MySQL window barrier）；refined 单独 guard 同事务、不受页限；pending 义务且禁止 guard SQL 时提交前拒绝 | GRD；[project_single_match](../../../src/pietto/_project/project_single_match.py) | guarded case（PG 55；MySQL 54，另 1 个原 owner 排除）的全部 cell 由 `check_representative` 比对 guard_states 与行；`refined_violation_outside_page` 的 12 个 R2 cell 在任何 basis 前以 `SINGLE_MATCH_VIOLATED` 拒绝；漂移项在恢复前拒绝且 checkpoint 不变 | refusal_moved_checkpoint/missing_drift → `MATRIX_DRIFT`；`bag_two_equal_null`、hidden where/limit/distinct case；[S03 test](../../../tests/test_phase68_slice3_execution.py) `test_real_unfulfilled_obligation_is_refused_before_connect` | NATIVE；S20 数据回读确认 12 个 NO_R2_BASIS 均为 guard 阶段违例（见全矩阵对账）；有限 managed premise | SATISFIED_IN_RECORDED_DOMAIN |
| P68-A07 一致性profile：稳定快照默认、显式 Serializable 只读；guard/query 的参数、predicate、role、view 一致；并发更新、role 可见性、DDL/环境变化；强 profile 失败不降级 | stable Repeatable Read 默认，显式 Serializable；guard context 绑定同一连接/role/事务；PG 有限来源资格与 MySQL view-source 各自配 managed premise | EX `ExecutionLimits` 与 premise；[guard context](../../../src/pietto/_project/project_guard_context.py)；来源资格 owner | 每路线每 cell 的 guarded `serializable`；visibility_full/visibility_subset；J01 G_source_drift、H_version_replaced；S09 stable_update/serializable/role_replace 与 S08 role_change 控制 | 源漂移 → `RECONCILIATION_MISMATCH`；版本替换与过期保留在拥有层拒绝；强 profile 不降级 | NATIVE；`Managed operator compliance: NOT_INDEPENDENTLY_VERIFIED`；`Native all-definition lifetime exclusion: NOT_DEMONSTRATED / NOT CLAIMED`；不是通用 PG 程序分析 | SATISFIED_IN_RECORDED_DOMAIN |
| P68-A08 未知基数完成：batch/source/transaction/delivery 分别终结；不回填 expected_rows；late error、early close、empty 与 EOF 的接口差别；旧 RD 合同回归 | `CompiledAttemptOutcome` 分层（source EOF、transaction COMMIT_ACK/UNKNOWN、delivery、cleanup、cancel 三元组、remote use end）；空结果为 schema-only `[0,0)` EOF chunk | EX `compiled_attempt_outcome`、`compiled_closing_facts`；CAP capture_end | `check_matrix_record` 分层终态；S16 真值表在 J10 上从原始行重算；[S03 test](../../../tests/test_phase68_slice3_execution.py) `test_unknown_cardinality_exact_boundary_and_empty`、`test_failures_are_not_eof_success` | unknown_published → `J10_ELIGIBILITY`；eof → `S14_CHECK_COMPLETE_COVERAGE`；位置 0 的空洞不是空结果成功 | NATIVE + SIGKILL + pytest；无隐藏 COUNT、无可信 cursor rowcount | SATISFIED_IN_RECORDED_DOMAIN |
| P68-A09 资源生命周期：本次独占新连接/事务/statement 的接受、提交、关闭与失败责任；构造中途失败、执行/读取/cleanup 组合错误；不接管调用者事务 | 每个 attempt 新建独占连接/事务/statement；不接受调用者事务；primary 失败不被 cleanup 改写；本地关闭不推断远端静止 | 三条路线 owner | check02 在控制族原始数据上重跑原检查器：S03 17 个 case product MATCH、S09 24 个控制、S08 12 个控制 | commit/rollback 丢失、prepare/read/close-send 错误、清理失败分层；[S03 test](../../../tests/test_phase68_slice3_execution.py) `test_grafted_resource_rejection_closes_only_owned_handles`；[S09 test](../../../tests/test_phase68_slice9_execution.py) `test_unknown_transaction_is_not_rolled_back_as_original` | NATIVE 控制（S03 来自 campaign02、S09/S08 来自 campaign03，经 reuse-bridge4；三者都在 union 前提环境运行，S09 worker 的 native-env 与 S08 自 C24 最终修复起）；INJECTED 与真实阻塞由原族标注；cleanup 词：PG rows `CLOSED`，ADBC/MySQL `LOCAL_CLOSED_REMOTE_UNOBSERVED`（不是远端静止证明） | SATISFIED_IN_RECORDED_DOMAIN |
| P68-A10 合格持久工作区：本地存储、保护/配额、SQLite 实际构建与配置；文件耐久前提与状态事务分开；错误 profile 拒绝，无依据不宣称耐久 | 显式私有路径；Linux、SQLite 3.53.1（固定 source id）、rw ext4 无 nobarrier；WAL + `synchronous=FULL`；预算与控制余量 | WS `storage_profile`、`create_workspace`、`open_workspace` | 每个 S19 存储在 CPython 3.13.13 + SQLite 3.53.1 + ext4 上打开；[S11 test](../../../tests/test_phase68_slice11_job_workspace.py) `test_profile_binds_the_actual_measured_build_and_filesystem` | `test_unsupported_profile_refuses_before_any_file`、`test_foreign_or_future_envelope_refuses_with_no_sqlite_open`、`test_path_object_and_permission_substitutions_refuse_without_repair`；compat unknown_feature → `FORMAT_FEATURES` | REAL_COMPONENT + NATIVE；诚实 fsync 是外部前提；托管合格存储正例 NOT_OBSERVED（CI 只走拒绝分支） | SATISFIED_IN_RECORDED_DOMAIN |
| P68-A11 检查点与进度：immutable chunks 先持久、metadata 再引用；连续前沿与空洞；观察/持久/交付/ACK 分离；1 与 3 完成而 2 未完成不能跳过 | chunk staging O_EXCL、fsync、link、目录 fsync，再单事务发布 chunk 与新 checkpoint；frontier 为自 0 起最大连续前缀 | [chunks](../../../src/pietto/_project/project_job_chunks.py)、CAP、VER | 每个 R2 cell 的 `check_capture`/`check_recovery`；J01 B_holes、C_reply_lost、D_second_crash；S12 K1–K7 进程历史 | 每个 target 9/9：producing_attempt → `S14_CHECK_OLD_MEMBERS_PRESERVED`、hole → `S14_CHECK_NEW_EXACT_COMPLEMENT`、frontier → `S14_CHECK_FROZEN_BOUNDS`、barrier → `S14_CHECK_BARRIER`、capture_plan → `S14_CHECK_CAPTURE_PLAN`、history 两类 → `S14_CHECK_HISTORY_*`；另两类 prior_unknown、eof 见 A20、A08 | NATIVE + SIGKILL；进程 kill 不是断电；设备 sync 诚实是前提 | SATISFIED_IN_RECORDED_DOMAIN |
| P68-A12 R1消费恢复：同一已保存代、原参数/格式/授权/保留复验；重启、变 batch、过期、取消；不丢重，不复活旧 runtime 对象 | `accept_saved_read` 新鲜信任与 typed 值、精确 checkpoint/extent；显式确认链从 0 无缝；未确认的 `(generation, position)` 可同身份重投；R1 不访问源 | RP | check02 R1 尾段：PG 488（244 source + 244 installed）、MySQL 236（118 + 118），无驱动、零连接；J03 固定前缀；S13 批 1/2/3/整体 | invented_ack/enlarged_scope/relabeled_redelivery → `J03_R1`；driver_in_saved_tail → `R1_SOURCE_OFFLINE`；过期、取消、释放在发出前拒绝 | NATIVE（Arrow-only 进程）+ SIGKILL；本地 ACK 不是任意外部副作用保证；旧 consumer 不跟随新 checkpoint | SATISFIED_IN_RECORDED_DOMAIN |
| P68-A13 R2原提取恢复：可重开同源版本与正确 occurrence 覆盖下恢复未捕获部分；新进程访问真实 source 取得未捕获数据；重复键/ties/全局操作不错误拼接 | 首次捕获前登记规格与资格描述；新进程新鲜资格与 guard；从位置 0 有序重新枚举、对账全部旧成员、屏障后补洞与续写；每个 chunk 记录真实 producing attempt | XR、CAP、EX `compiled_source_description` | PG 488、MySQL 236 个准入 R2 cell 由新进程恢复，check02 同时以 `check_matrix_record` 与 `check_recovery` 判定；J01 每路线 7 段历史 × 3 路线 | B_damage_value/B_damage_coordinate → `RECONCILIATION_MISMATCH`（成员与 checkpoint 不变）；J01 损坏 5 类 → `J01_LINEAGE`；NO_R2_BASIS 12、漂移 3 | NATIVE + SIGKILL；provider token/payload/version 保留由外部负责；可能重读完整前缀；无 COUNT oracle、snapshot keeper 或自动整 job 重试 | SATISFIED_IN_RECORDED_DOMAIN |
| P68-A14 双持久交付：durable provisional stream 与完整结果代原子发布共用内核；故障不发假完整；publish/cancel 两种顺序；发布后通知丢失可查询 | DLV 窗口、issuance、sink 观察与派生前沿；PUB closing observation、精确 `[0, N)` 成员与发布自有保护；共用 S12 chunk/checkpoint | DLV、PUB | J02（每路线 12 个效果）；J04 发布切点与通知丢失；J05 两种顺序；J10 资格；S18 联合历史中的发布与查询 | notification_as_commit → `J04_PUBLICATION`；reversed_order/released_protection → `J05_ORDER`；unknown_published → `J10_ELIGIBILITY` | NATIVE + SIGKILL；无跨库原子事务或任意 callback exactly-once；发布不撤回 | SATISFIED_IN_RECORDED_DOMAIN |
| P68-A15 合作sink：真实参考 consumer、稳定逻辑 effect 身份、payload 冲突、ACK/提交查询与 retention；ACK 丢失重试不重复，同键异值拒绝，等值 occurrence 不合并 | reference sink v1：主键 `(workspace, generation, position)`，DUPLICATE/CONFLICT，五类 query 结果，不可变保留合同 | SNK、DLV `accept_sink` | J02：sink COMMIT 后、本地确认前切断，新进程恢复并同身份重发 → `PRESENT_MATCHING`，每个 occurrence 恰好一个效果，等值 occurrence 两个效果 | 每路线 8/8：六类效果损坏 → `J02_EFFECT`；driver_in_adopter → `SAVED_SOURCE_ACCESS`；injected_as_kill → `EVIDENCE_CLASS` | NATIVE（3 路线）；sink 保留与工作区保留独立；空的替换 sink 不证明旧效果不存在 | SATISFIED_IN_RECORDED_DOMAIN |
| P68-A16 取消与deadline：有界取消、控制资源、必要时弃用自己的连接；请求/送达/观察分开；阻塞 execute/fetch、取消失败/晚到成功、cleanup 失败；已取消 job 不能 recover 复活 | owner 原生 cancel/deadline；RT 控制通道独立于数据额度与满队列；持久 `cancel_job`；cancel requested/sent/observed 分开 | 路线 owner；RT `Runtime.cancel`；ST `cancel_job`（`open_attempt` 要求 ACTIVE） | 控制族 blocked_cancel/blocked_deadline/late_cancel；J05、J08（满队列取消、协调器死亡后恰好一次对账、不启动新 attempt）；tuning 的 CANCELLED_QUEUED | cancel_as_success → `J08_RECONCILE`；cancel_completed → `TUNING_TERMINALS`；顺序与保护损坏 → `J05_ORDER` | NATIVE + SIGKILL + 标注的 INJECTED；无任意网络故障的硬实时中断承诺 | SATISFIED_IN_RECORDED_DOMAIN |
| P68-A17 并发与资源：独立预算、多 job 准入、短事务、背压/控制通道；同保证调优；不降隔离/刷盘/检查，不 SKIP LOCKED | RT 资源向量原子准入与恰好一次结算、FIFO 有界超车、固定高水位背压、控制通道 | RT `open_runtime`、`reconcile` | J08；S17 `check_events`；`check_tuning`：每路线一对 serial/concurrent，终态、精确值与工作量相同，背压实际发生（物理连接峰值 1/2、worker 峰值 1/3） | double_settlement → `J08_RECONCILE`；serialized_concurrent/one_connection → `TUNING_OVERLAP`；never_blocked → `TUNING_BACKPRESSURE`；less_work → `TUNING_EQUAL_WORK` | NATIVE；结果 NO_MEASURED_SPEEDUP；每路线一对，无显著性或伸缩声明；不要求加速 | SATISFIED_IN_RECORDED_DOMAIN |
| P68-A18 保留与安全回收：checkpoint、已发布代、active readers、sink 期限共同约束 GC；回收有身份/并发协议；reader/GC 交错、磁盘压力、孤儿片段；被引用数据不删 | 保护根（最新 checkpoint、S12/S13/S15/S16 retention、共享租约）；显式退役；独占租约下持久删除决定 → unlink → 目录同步 → removal 观察 → credit | GC、CAP `classify_files` | J06 读者/回收两种顺序与全部根；J07 五个回收切点；S17 检查器在联合历史中 | stale_read → `J06_LIFETIME`；protected_tombstone → `PROTECTED_COLLECTED`；observed_absence/credit_before_removal → `J07_COLLECTION` | SIGKILL + REAL_COMPONENT + NATIVE；不删除数据库、WAL/SHM、信封或历史行；无断电声明 | SATISFIED_IN_RECORDED_DOMAIN |
| P68-A19 兼容与秘密边界：私有持久格式显式版本；恢复重新授权；凭据不落盘；敏感参数受保护；不自动迁移；旧 runtime 先拒绝而不修改 | v1–v7 信封与 schema 精确，`supports()` 按 feature；未知信封在 SQLite 打开前拒绝；schema 损坏 `WORKSPACE_SCHEMA`；代码身份 `COMPILED_COMPATIBILITY`/`JOB_COMPATIBILITY` | WS、CL `semantic_build_identity`、ST `load_job` | `check_compat`：B19 与当前代码身份同为 `133d424d…`，存档 S16 运行时拒绝 v7；[S11 test](../../../tests/test_phase68_slice11_job_store.py) `test_protected_values_and_credentials_stay_confined` | unknown_feature → `FORMAT_FEATURES`；laundered_identity → `CODE_IDENTITY`；envelope_accepted → `ENVELOPE_BEFORE_SQLITE`；archived_accepts_v7 → `ARCHIVED_REFUSAL` | compat 族（campaign02，经 reuse-bridge4）+ pytest；无 v8、无迁移、无公共格式冻结；不防 root 或同用户改写 | SATISFIED_IN_RECORDED_DOMAIN |
| P68-A20 可查询的分层结果：source UNKNOWN、本地已提交而回复未知、cleanup 失败各自记录；保留 attempt 历史；新 attempt 不篡改旧 UNKNOWN | 终态与 closing observation 同事务；`interrupt_attempt` 保持远端 UNKNOWN；operation 查询（`PREVIOUSLY_COMMITTED`、`STORE_COMMIT_UNKNOWN`）；只读状态视图 | ST、PUB、XR、DLV | S16 真值表在 J10（相同持久前缀、不同远端结果）；S14 `check_history`；S17 D13（联合历史） | prior_unknown → `S14_CHECK_PRIOR_UNKNOWN_PRESERVED`；unknown_published → `J10_ELIGIBILITY` | NATIVE + SIGKILL；本地 COMMIT 不确定时保持 UNKNOWN | SATISFIED_IN_RECORDED_DOMAIN |
| P68-A21 安装与回归：core 无 ambient 执行/Arrow 依赖；执行依赖隔离、same-wheel origins；保留 P67 及更早能力（四安装 cell、SDK9、120/118、22 文档、native/replay） | `pietto`、`pietto[arrow]`、三个 `execute-*` 与并集；同一 wheel 六个干净解析前缀；所选路线 pinned 驱动在 admission/worker/连接前拒绝，无回退 | `pyproject.toml` extras；EX `pinned_modules`；各路线 `drivers()`；[package smoke](../../../scripts/package_smoke.py) | S19 install02（S18 `install()` 作用于当前 wheel `cf81718b…`）；consumer 族 8 步（LOCAL `local-s19-campaign02`，两次新构建 wheel 字节相同）；S19 与 B20 自然 CI 的 SDK/product/canonical/target/replay/health 消费者已观察，S20 的同一组消费者待闭环规则观察 | 安装损坏 D1–D4 与解析负例；S18 检查器八类协调损坏各由指定定律拒绝 | install02/compat/consumer（LOCAL）+ CI；依赖两域见下节；托管 wheel 自检不是独立下载的本地字节 | SATISFIED_IN_RECORDED_DOMAIN |
| P68-A22 联合故障与性能：小模型、真实组件、进程崩溃/持久模拟分层；同保证并发与故障历史；故障后再次恢复，完整值/重数/终态；不夸大断电或通用 exactly-once | 五层证据分开记录；`joint_model` 有界穷举；J01–J10 连接历史；同保证对比 | S19 `check_evidence`、`joint_model` 与各层原检查器 | check02 全部族；存储两套各 34 步、9 个真实 SIGKILL 切点、7 个决定、19 次结算、8 组值 | injected_as_kill → `EVIDENCE_CLASS`；values 损坏 → `VALUES`；模型或注入改称 SIGKILL → `EVIDENCE_CLASS` | 全部层；有界模型不是证明；进程 SIGKILL 不是断电；性能只报告记录范围 | SATISFIED_IN_RECORDED_DOMAIN |

## 全矩阵对账

必需集合由 S19 检查器 `required()` 从下层 case owner 推导（字面 TOTALS PG 166/0/62、MySQL 164/5/62 防止目录被缩短），
cell 身份为 `(target, route, group, case, variant, entry, origin, obligation)`。观察列来自 check02，S20 aud01 从
campaign04 矩阵报告只读重算（不打开任何 SQLite），并复核报告已记录的 2,694 个 raw digest：0 个不符。

| target | 路线 | 声明 case | 排除 | 必需 cell | MATRIX 义务 | R2 义务 | MATRIX 观察 | R2 恢复 | NO_R2_BASIS | 漂移 | R1 读出 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| postgres | postgres_rows, postgres_adbc | 166 | 0 | 1328 | 832 | 496 | 832 | 488 | 8 | 2 | 488 |
| mysql | mysql_rows | 164 | 5 | 636 | 396 | 240 | 396 | 236 | 4 | 1 | 236 |

- 两侧都满足 MATRIX + R2 + NO_R2_BASIS = 必需 cell，R1 读出 = R2 恢复（source 与 installed 各半：244/244、118/118），
  漂移项每条路线一个，单独计数，不进入分母。
- NO_R2_BASIS 恰好是 `refined_violation_outside_page`（S07 guarded-refined，`states=("VIOLATED",)`、`rows=()`）的全部 R2 cell：
  每个都在登记任何 R2 basis 之前失败，`capture.s14` 为空、没有 recover。S20 回读 12 个原始记录：均为 `category=SINGLE_MATCH_VIOLATED`、
  `guard_states=["VIOLATED"]`、primary phase `guard`、transaction `ROLLBACK_ACK`、0 行、cleanup `CLOSED`。这是被观察到的指定负义务，
  不是被豁免的正例。检查器强度说明：S14 `check_capture` 的无 basis 分支只要求该 case、失败非 `S14Abandoned` 且无行，并未绑定违例类别；
  本次原始数据满足更严条件，没有 false PASS。加固该分支属于未来另行授权的检查器工作，S20 不改原检查器。
- MySQL 的 5 个排除都是 case 级（不是 cell 级）原 owner 拒绝：普通与细化的 `V_join_full/null_keys`、`A_window_groups/exclude`
  （owner `original`，观察 `NONE`），guarded `full_unmatched`（owner `case_preparation`，观察 `GuardPreparationError`，S07 postgres_only）。
  每个排除 case 少 4 个 cell（1 路线 × 2 entry × 2 origin）；PostgreSQL 没有排除。
- attempt：check02 计入 cell 自身的 attempt（PG 1,816、MySQL 872）；含漂移项各自的 capture/recover attempt 为 1,820 与 874，全部唯一。
  这是计数口径差异，不是额外的成功 cell。
- R2 读出绑定：check02 为每个恢复的工作区记录行数、generation、producing attempts 与 checkpoint，并以 S14 `check_r1` 对照 Arrow-only 尾段。

## 联合历史与检查器来源

| ID | 位置与切点 | 判据与结果 |
| --- | --- | --- |
| 12-cell 下限 | `joint` 族即原 S18 `native()`：每路线 × live/bundle × source/installed，在各自路线安装中运行 S17 联合历史、并集路由与无回退、删源、丢失回复与无驱动尾部 | S6/S7 字面 oracle、S17 `check_all`、S18 检查器；PG 8 段历史 + 2 次丢失回复，MySQL 4 段 + 1 次 |
| J01 / J09 | 矩阵分区 0 删库前，每路线 installed bundle：B_holes、B_damage_value、B_damage_coordinate、C_reply_lost、D_second_crash、G_source_drift、H_version_replaced | S14 `check_history` 与其损坏族在 S19 raw 上重跑 + `J01_LINEAGE`；7 段 × 3 路线 |
| J02 | 同上：S15 原生 relay 在 sink COMMIT 后、本地确认前切断；新进程 S14 恢复；无驱动进程同身份重发并只交付其余；同键异值 CONFLICT | `J02_EFFECT`：每路线 12 个效果，重发 `PRESENT_MATCHING` |
| J03–J10 | `storage` 族（source、installed 各一套）：一个 v7 工作区内真实 Arrow chunk 与真实子进程 SIGKILL | `check_storage` 与 16 类协调损坏，每套 16/16 命中指定定律 |

进程 SIGKILL 不是物理断电；合成 owner、注入调用与 SIMULATED_NATIVE_IO 均保持标注。四个清单维度（12-cell 下限、J01 历史、J02 效果、
两套存储历史）彼此独立，不合并成一个测试计数，也不要求每个故障覆盖每个 SQL cell。

- **C25（仅检查器）**：check01 在 `MATRIX_DAMAGES` 停止，诊断显示全部损坏被拒绝，但 5 个由更早的原定律拦下（PG swapped_ordinal →
  VALUE_DOMAIN；MySQL 四类 → S08 完整重消费）。修复让损坏与原检查器重新解码的每个副本（MySQL 二进制 get_rows 行与 int01 Bool 载体）
  一致并留在声明域内；diag16 在 campaign04 raw 上 12/12 命中指定定律，check02 在不变的 campaign04 raw 上通过。没有新的原生运行。
- **C24（环境闭包）**：第一次修复只把 S09 父进程移入 union 前提环境（campaign02 随即在 worker 处失败）；最终修复把 S09（进程与
  native-env）和 S08 也整体放入原 S01 执行前提环境（S03 自 readiness2 起已在 union 中运行）；check02 消费的控制族结果来自 campaign02/03 中可执行内容相同的单元。

## 产品与依赖两个证据域

S19 → B20 只改六个路径：`ci/phase68-executor-premise-requirements.txt`、PINS、`uv.lock`（仅这两个包的 version/sdist/wheel 共 12 行）、
S18 检查器 SELECTIONS、S18 探针 wheel 文件名与 S18 安装测试字面量。`src/`、grammar、`pyproject.toml`（extras）与 `README.md`
未变，因此产品 wheel/sdist 输入与代码身份不变；依赖 profile 与之分开记录。

| profile | 实际内容 | 证据 |
| --- | --- | --- |
| S19 原生合格生产 profile | CPython 3.13.13、SQLite 3.53.1、本地 ext4；ADBC 与 union 配方前缀含 importlib_resources 6.5.2、typing_extensions 4.15.0、adbc-driver-postgresql/manager 1.12.0、pyarrow 25.0.1，union 另含 psycopg/psycopg-binary 3.3.5 与 mysql-connector-python 26.7.0；PG rows 前缀无 typing_extensions | install02 前缀在删除前的快照；campaign04/check02 |
| B20 当前锁定 profile | 新 lock 与 PINS：importlib-resources 7.1.0、typing-extensions 4.16.0；其余锁定条目不变；开发 core 只更换 typing_extensions 分发 | #82/#83 维护检查、隔离前缀快照与当前回归 |

| 变更依赖 | 实际运行时调用者 | 路线/平台条件 | 不变的输入 | 已有观察 | 剩余未知 |
| --- | --- | --- | --- | --- | --- |
| importlib-resources 6.5.2 → 7.1.0 | 仅 `adbc_driver_postgresql._driver_path()`：`importlib_resources.files(driver)` 后 `joinpath("libadbc_driver_postgresql.so").is_file()`，返回字符串路径 | 只在 `execute-postgres-adbc` 与并集安装中存在；Pietto `src/` 不导入 | 驱动 wheel 与随附 `.so`（10,451,184 B）不变；产品代码不变 | 维护在 CPython 3.13.13 隔离前缀中观察到 7.1.0 的 `files()` 返回 PosixPath 并定位到该 `.so` | 新依赖对下真实 PG ADBC 查询：NOT_OBSERVED |
| typing-extensions 4.15.0 → 4.16.0 | 路线闭包在 CPython 3.13 上没有运行时调用者：adbc-driver-manager 只在 `TYPE_CHECKING` 下导入，psycopg 只在 Python < 3.11/3.13 时导入，pyarrow 只在 < 3.8 时导入；编译模块中无引用 | ADBC/union 安装；开发 core 经 pyright | 产品代码不变 | lock、PINS、读者一致性由维护检查与当前回归覆盖 | 无已知运行时路径 |

| 主张 | 证据基础 |
| --- | --- |
| S19 全矩阵、R2 与联合历史 | S19 原生合格生产 profile，campaign04/check02 |
| 更新后的 lock/前提/PINS/读者一致 | #82/#83 维护检查与当前回归 |
| 新 importlib-resources 能定位随附的 ADBC 库 | 维护的隔离前缀观察 |
| 更新后的传递依赖对下真实 PostgreSQL ADBC 查询 | NOT_OBSERVED（维护记录中没有） |
| B20/S20 托管的旧 target-conformance 成功 | 只在其回执/驱动/消费者域内成立；不是 Phase68 ADBC 路线或新依赖 profile 的覆盖 |

处置：A01–A22 的必需正例都有其原始证据，产品与输入的不变关系成立，依赖影响审计没有发现具体矛盾，也没有原始必需义务依赖于
缺失的新 profile 观察。因此按本次派发的规则，S20 以“新 profile 下的真实 ADBC 查询 NOT_OBSERVED”明示关闭：这不是对任何必需正例的豁免，
也不声称新 profile 通过了全矩阵。完成主张仅是**已批准的 Phase68 功能在其已记录、经独立检查的域内**成立，不认证每个平台、
包元数据允许的每个版本或每个新可解析的传递依赖组合。

## 支持域与不扩大的含义

- compiler core 仍无 ambient 执行；可选安装只提供依赖，不授予调用方信任、不选择路线、不创建 job、不认证存储。
- 七个结果 scalar 与现有查询/算子排除保留；四个可绑定叶值是另一个域；Phase68 完成不带来新的 SQL/后端/嵌套/pandas/算子支持。
- ALT-COMPILED 避免执行时的源语言重新细化，但仍要求可信构建、内容 pin、代码兼容与新鲜接受；存储的回执或 hash 不是凭证。
- R1 只命名一个已保存 checkpoint/extent 与显式确认链；R2 是完整有序重新枚举加全部旧成员对账，可能重读完整前缀。
- 完整发布需要成功的 closing owner 证据与精确持久成员；原中断/UNKNOWN attempt 保留；source EOF、COMMIT_ACK、受检交付与各路线
  cleanup 词各自独立。`LOCAL_CLOSED_REMOTE_UNOBSERVED` 既不是 cleanup 错误，也不是远端已静止的证明。
- sink COMMIT、回复、本地 sink 确认、R1 ACK、完整本地发布、通知、当前可用性与远端静止是不同事实；没有跨库原子事务。
- workspace v1–v7、reference sink v1 与既有 bundle/IPC/发布格式不变；识别、schema、代码兼容与新鲜接受是四个门；无迁移或公共格式冻结。
- 发布保护不因普通取消、读者关闭或 sink 退役而释放；GC 只回收合格的自有未发布已退役数据或已放弃的 claim。
- `Managed operator compliance: NOT_INDEPENDENTLY_VERIFIED`；`Native all-definition lifetime exclusion: NOT_DEMONSTRATED / NOT CLAIMED`。
- provider token/payload/version 保留与 sink 实例/保留是独立责任；本地 sync 诚实与私有合作用户边界是显式前提；
  没有断电、恶意 root、永久磁盘丢失或多机接管保证。托管存储/运行时正例只在原始数据实际暴露时才声明，其余 NOT_OBSERVED。

## 二十个位置与发布链

aud03 只读对账 Phase67 终点 `2f280ea02b974c0ab7e6e8e07017b960b55f850a` 到 B20 的 first-parent：23 个普通、未签名、唯一父提交，0 个 merge；
每个 head 恰有一次 push/main 自然 CI。二十个产品位置是 S01–S20；C01、PR #81 与 #82/#83 维护是独立维护，不是额外 Slice。

| 角色 | head | tree | 自然 CI | 处置 |
| --- | --- | --- | --- | --- |
| S01 | `5d9645e796a3408e60a4a93ba0b263b8a40b1ef4` | `dcb0263270657b03b27d9238869c21f024f09dd2` | 36499401981 attempt1 success | COMPLETED / PUBLISHED |
| S02 | `86ed839878b877f9ea363c146b939cacf23c43ff` | `bda78b078699b8c1978cd65a2f5b65b32f8e56ff` | 36508766895 attempt1 success | COMPLETED / PUBLISHED；PRODUCT_GATE_BLOCKED_REPLAN 保留为历史 |
| S03 | `069a5bab80bf8fda1ca04f5a08446fb0f2940881` | `dcec7f5e0829b32ac0153e8581a0550bca5889aa` | 36532317073 attempt1 success | COMPLETED / PUBLISHED |
| C01 | `6d32ece0328d4760645faf2423d38dd2a2ef0c96` | `9fc857ac4446c6d07a4ea350e0532ff21510c804` | 36544619465 attempt1 success | 独立维护 COMPLETED / PUBLISHED |
| S04 | `15c64d5ad8d5680abd1d08a5ff4d43e94d0a8aab` | `c4655d313c72803d3ced108f68e3c5342c0b38d0` | 36613787353 attempt1 success | COMPLETED / PUBLISHED |
| S05 | `01e509bf2cb2b83f1e699e089f3b1e5f7b3ea0b1` | `968c7370ad94231ea580403c7e776cff61713a52` | 36641150728 attempt1 success | COMPLETED / PUBLISHED |
| S06 | `196c3108b887dc2b6ab2417d9ad478ae76b8e818` | `f5927814a2b62c88a06bf9c542f14183d4e03a80` | 36677611835 attempt1 success | COMPLETED / PUBLISHED |
| S07 | `58b93255d66dca7b9b8b3a750be3e3d6abd03492` | `39f966d1772d9e4c0e8b4f6191a3b79fc7fa50d6` | 36820279356 attempt1 success | COMPLETED / PUBLISHED |
| S08 | `e6719209bd935f0f4063959ffa64b47d548dcdfd` | `14ce58e6b3a66323dc212e42726265578be55c94` | 36926813328 attempt1 success | COMPLETED / PUBLISHED |
| S09 | `bd92c2c9f29d3b47aa94ea7dfcb5a6fe2e564b68` | `3924d1774c4f261ab38cf6a1e2f2abac6be01178` | 36977540827 attempt1 success | COMPLETED / PUBLISHED |
| S10 | `e8fbc5ed60eebb0bf9ad772f08a1b50b48d1c17c` | `a31854f36a09ee23f3e79858e06d2fafcf4e619c` | 37181864937 attempt1 success | COMPLETED / PUBLISHED |
| S11 | `383747bbf5c4fe3142a01a15cef3fa34543015bf` | `d5c4304684d97194bb83347b2bdd9ecfc2c76f8b` | 37188868480 attempt1 success | COMPLETED / PUBLISHED |
| S12 | `d4d5f157df739a92e310ad23ac156ba4f66cb4cc` | `03ee7b53914695a3f7bac67b73bf9c223e1003c5` | 37229699158 attempt1 success | COMPLETED / PUBLISHED |
| S13 | `a223d2e469fb941f7206b85467b66349d3075678` | `3b7963d9a1a3ccff02a076342bdb969d2b5de6d3` | 37275267364 attempt1 success | COMPLETED / PUBLISHED |
| S14 | `d9646b574509aff9d0dbfab98a29a25ab97ff6bf` | `36fe7bb6db2aa02c4a6fa55d30bef72fdaa7842b` | 37364275901 attempt2 success | COMPLETED / PUBLISHED；attempt1 托管运行器分配失败，一次用户授权的完整重跑是历史，不是常设许可 |
| S15 | `ccda584ca93ad92b54154f958c8405a23efc8ae3` | `0aa49b1c2fd0524268c738ae3a7a19169a2e252c` | 37401687496 attempt1 success | COMPLETED / PUBLISHED |
| S16 | `cd6dbea4d5b9d2f10265be8eea3a64afa0e3f286` | `48d8dec61fc6fbff14aac8d6a3376aba372f366d` | 37427084705 attempt1 success | COMPLETED / PUBLISHED |
| S17 | `12f0f8adfc2a3873ee31b0bab86e565aa8ab96f3` | `babbd7626deffa9d68106a12c2fe88263c772a89` | 37459792622 attempt1 success | COMPLETED_WITH_DISCLOSED_PROCESS_EXCEPTION；C16 一次性接受，campaign03 为合规验收，历史不合规保留 |
| PR #81 | `9d0866871a45ef17a352b2dc0218942356eb4c21` | `0e3d8899b60086f15d83e299fc73cd36ed900322` | 37495792058 attempt1 success | 独立维护（Ruff 0.16.10、托管补丁 3.12.14/3.13.15） |
| S18 初始 | `52551f4aa3a95fd2e5e2d430f1bb572291d22b12` | `0f66e31e18e2b9ad9a7f032e4e09d859c96795dc` | 37560515473 attempt1 failure | 保留的失败 head（C10：CI 才运行的已安装读者） |
| S18 修复子提交 | `35fb67afa3d12088de7571bfe313c296a68a2f0d` | `d00981dc0d76a021094a4107977eecb7255c8450` | 37566435211 attempt1 success | S18 COMPLETED / PUBLISHED（普通子提交，无手动重跑） |
| S19 | `ec8a03775ab1f52b72bfd72429a744252e94bcf8` | `1273371325f042030879f4305973d9b24cab3aa3` | 37705001971 attempt1 success | COMPLETED / PUBLISHED |
| #82/#83 维护 | `b4cb9845fa59cec6a3303e2dd21a3ce070f21d72` | `66fd816eb92d1c22ed3bee72cbe65277f4aaa61d` | 37711770935 attempt1 success | 独立维护；两个 PR 由 Dependabot 自动关闭、未合并 |
| S20 | 包含本审计的未来普通提交 | 待外部记录 | 待自然运行 | ACTIVE / CANDIDATE |

## 获取合并处置

S19 已按 [phase-end 程序](../../development.md#phase-end-acquisition-consolidation)对 Phase67 终点到 B19 的增量完成必要合并：
每个矩阵分区一个数据库生命周期同时承载普通、guarded 与 R2 夹具（替代 S10/S14 各自的生命周期）；每个声明 case 一个父进程参考构建与
bundle 供四个 cell 与各路线使用；细化 R2 只执行一次，恢复即该 cell 的矩阵观察；worker 程序文本每分区组装一次；已校验 wheelhouse
与六个配方前缀供全部族使用；每分区每来源一个 Arrow-only 读出进程。保持新鲜：资格认证、guard、publisher、SQLite 连接、接受、attempt、
来源与故障切点——check02 用 `MATRIX_FRESH_ATTEMPTS` 证明 attempt 未被合并成缓存成功。C01 的 RepositoryFactIndex 与托管获取不变，
没有第二个缓存、共享可变 AST 或测试选择权威。结构计数：S10、S14 历史上各用 21、24 个数据库生命周期，campaign04 用 4 个矩阵分区
生命周期承载全矩阵、R2、J01、J02 与漂移项（观察，不是加速声明）。

剩余重复的处置：pytest 中重复的源码编译判为 INTENTIONALLY_FRESH——每个断言拥有自己的新鲜 live 编译根，共享需要跨测试的可变产物图，
且在 loadfile 下依赖调度；757 s 单节点关键路径与重文件长尾是性能插段的优化假设，不是未履行的 S19 合并义务。CI 才运行的已安装读者
（S18 C10）有显式本地入口 `consumer`：S19 的 LOCAL `local-s19-campaign02` 实际走到已安装来源/元数据与读者检查，重放的是 S18 已核验回执的
原始身份（`35fb67af`/37566435211/1），不是 S20 的新原生观察。之后包或消费者输入变化的切片须运行这些直接读者；输入不变时不要求。

## 成本复盘

数值来自保存的计时 JSONL、ledger 与 CI 审计；aud02 只做复算，不新测。单调时钟与 UTC 跨度是两个时钟，分别列出；重叠的命令不相加为墙钟；
预留槽位不是实测 CPU。CPU 为计时 wrapper 的 `RUSAGE_CHILDREN`（已回收的后代进程），不含容器内数据库服务端。

| 范围 | 单调时长 s | UTC 跨度 s | 子进程 CPU user+sys s | 说明 |
| --- | ---: | ---: | ---: | --- |
| campaign04（簿记父进程） | 30956.57 | 31659.02 | 94535.21 | 报告中的“8.6 h”是单调时长；平均约 3.05 核 |
| 阶段 0 tuning | 1778.88 | 1828.20 | 1786.73 | 独占窗口 |
| 阶段 1 矩阵与存储 | — | 26963.68 | — | 阶段跨度；“7.3 h”/“7.31 h”是 mysql-0 组件单调时长，不是阶段跨度 |
| matrix pg-0 / pg-1 / pg-2 | 20801.85 / 22146.76 / 16901.86 | 21276.65 / 22654.55 / 17296.29 | 21173.85 / 22563.33 / 16986.71 | 每分区 CPU/墙钟约 1.0 核，cell 串行 |
| matrix mysql-0 | 26307.85 | 26901.83 | 26687.74 | 组件超时 28800 s |
| storage | 1043.65 | 1065.12 | 1021.98 | |
| 阶段 2 joint-pg / joint-mysql | 2809.24 / 1438.13 | 2866.54（阶段跨度） | 2857.23 / 1456.55 | 预留 4+4 槽，实测各约 1.0 核 |
| check01（失败）/ check02 | 571.79 / 584.45 | 582.51 / 597.08 | 2055.21 / 2096.94 | 4 个 spawn worker |
| S19 full01 | 1373.75 | 1408.06 | 4359.76 | pytest 1237.6 s；4 worker |

- 长命令的 UTC 跨度一致比单调时长多约 2.2–2.5%（campaign04 +702.45 s）；同一实例总差 1440.99 s。未观察到挂起或重置边界，原因 UNKNOWN，
  不以一方修正另一方。S19 报告中的“1,440.5 s”与“225 个事件”是转录差异；计时摘要记录为 1440.99 s 与 226 个事件，以记录为准，两者都保留。
- 失败与中断分开记录：campaign01（281.41 s）与 campaign02（286.53 s）因 C24 在阶段 0 失败；campaign03 在阶段 1 因外部内存耗尽失败
  （无关的 12.2 GB python 进程于 14:00:04Z 被内核 OOM 结束，ledger 记为 ENVIRONMENT_MEMORY_EXHAUSTION；遗留的自有 PG 容器在会话删除被
  拒后由用户手动删除并经观察确认）。不推断超出日志的因果确定性。
- 同保证对比（serial/concurrent，独占窗口）：PG rows 232.5/258.8 s（campaign03，经复用桥）、PG ADBC 366.1/372.4 s、MySQL 293.1/301.5 s，
  均为 NO_MEASURED_SPEEDUP，值与保证正确；没有需要修复的性能目标。tuning 组件 CPU/墙钟约 1.0，与 GIL 受限的假设相容，但不构成证明。
- 托管 CI：S19 运行 workflow 1845 s、job 合计 6354 s（最长 Runtime 3.12 / general-runtime 1733 s）、本地传输 244 s；维护运行 workflow
  1893 s、job 合计 6802 s、传输 298 s。CPU/RSS 为 UNKNOWN。S17/S18 的成本属于不同工作量，不是受控比较基线。
- S19 预算实用（ledger）：campaign 4/6、数据库生命周期 18/27、对比对 6/9、家族启动 30/36、修正组 25/54（24 E、1 M）、聚焦 14/48、
  诊断 18/24、全量 1/4；其中前四个上限由两次用户授权提高（授权 01：campaign 4→6、数据库生命周期 18→27、对比对 6→9；授权 02：家族启动 30→36），原文保存在 S19 证据中。这些是历史，不是 S20 的预算池。

## 结论

现有证据支持 A01–A22 在已记录、经独立检查的域内满足，二十个产品位置的发布链完整；保留的失败与例外（S02 原 HOLD、S14 attempt2、
S17 C16、S18 失败 head 与修复子提交、S19 campaign01–03 与 check01）均保持历史原样。仍为 NOT_OBSERVED 的事项：更新后传递依赖对下的
真实 PostgreSQL ADBC 查询、托管合格存储/运行时正例；`Managed operator compliance: NOT_INDEPENDENTLY_VERIFIED`；
`Native all-definition lifetime exclusion: NOT_DEMONSTRATED / NOT CLAIMED`。Phase68 的完成只由
[唯一闭环规则](slice-20.md#唯一闭环规则)在实际观察后激活；交接见 [Phase69 交接](phase69-handoff.md)。
