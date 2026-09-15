# Phase66 Isolated Target Conformance Facility v1

## Gate1: accepted scope and current owners

本Slice仅交付test-only real conformance facility，不实施Slice3或产品executor。
接受基线commit `49caec122a1d1242e7ce7178c8507aa3f7dbfacb`、tree
`824836de0c1fbaf69490aaaa45200d2083cda1f0`、parent
`71c1fa13c152d7be317c4bffee48615a39f1c2e4`；重新fetch/readback确认clean main、无active
Git操作或相关竞争进程，基线自然CI34934157115为push/main/attempt1/success。
当前本地Docker29.6.2明确endpoint为`unix:///var/run/docker.sock`、linux/amd64；未安装/
重新配置Docker、sudo、切换remote context或使用host DB。Slice1预算已关闭。

复用现有legacy CLI→parser/semantic/ScriptIR→PostgreSQL/MySQL renderer；源投影和独立SQL
都是真实consumer。`scripts/package_smoke.py`的isolated wheel/venv/external scratch模式
保持原样，新facility在生成SQL的同一child内核验实际installed origins及wheel member bytes。
legacy JSON v1仍为原schema，fixture receipt不冒充未来emission artifact。

当前无`tests/conftest.py`或额外pytest配置。默认pytest只运行unit/config/injected faults；
真实DB只由explicit runner运行。`scripts/validate.py`、两份Pyright配置、四项legacy gates、
package/runtime依赖、0.1.0、goldens和historical八family process registry均保持。
production204；五个新test Python文件使inventory463→468，仍由原sole inventory reader核对。
mutable status/roadmap仅由原sole lifecycle reader核对。

精确闭包A7/M9/D0（16路径）：

- A 本合同、`tests/_pietto_target_conformance.py`、
  `tests/_pietto_target_conformance_resources.py`、
  `tests/_pietto_target_conformance_observation.py`、
  `tests/_pietto_target_conformance_cases.py`、`tests/phase66_target_pins.json`、
  `tests/test_phase66_slice2_isolated_target_conformance_facility.py`。
- M `.github/workflows/ci.yml`、`pyproject.toml`、`uv.lock`、`docs/development.md`、
  `docs/status.md`、`docs/roadmap.md`、`tests/test_phase11_ci_workflow.py`、
  `tests/test_active_phase_lifecycle.py`、
  `tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py`。

CI guard只把原command/environment/action-count断言限于原validation job；全局read-only
permissions、无secret/PAT/elevated PR/publication/repository rewrite规则保留；artifact例外仅限
下述两目标的有界收据。原`test_phase11_validation_entrypoint.py`和runtime dependency/privacy/
packaging guards仍运行，不作宽泛allowlist或skip/xfail。

## Pins and actual distribution relationship

2026-09-15只读核实[PyPI Psycopg3.3.5](https://pypi.org/project/psycopg/3.3.5/)、
[binary3.3.5](https://pypi.org/project/psycopg-binary/3.3.5/)及
[Connector/Python26.7.0](https://pypi.org/project/mysql-connector-python/26.7.0/)的stable、
non-yanked分发元数据和3.12/3.13 wheels。新增`target-conformance`group，dev只include一次；
runtime仍仅antlr。uv.lock保留已有版本并冻结新增transitives/hashes。
PG实际要求binary implementation及RawCursor；MY固定use_pure=True和prepared cursor。
执行收据记录实际driver/Python/libpq/library版本，不拿development-doc banner当pin。

`phase66_target_pins.json`是唯一target pin输入；不接受其它image/DSN/SQL-file/callback/command。
执行使用repository@platform-digest，并核对image config ID/architecture及实际server build。

| Target | Reviewed distribution | Index / platform / config |
| --- | --- | --- |
| postgres | docker.io/library/postgres:18.6-bookworm；PG_VERSION=18.6-1.pgdg12+2 | index `sha256:1c59e2c3c818eaa0f0628f695b36e7c9e362d6b219b36a54a32df645cbd7e1af`；amd64 `sha256:a10c981235b4f635e65df0cfb66a5598064628128505dbc6a3ed4ca303717521`；config `sha256:f372eda99ac2ea249c3dce566dcdf468397035371284d2cf2103b4bc52b3b39e` |
| mysql | container-registry.oracle.com/mysql/community-server:8.4.12；官方config history安装mysql-community-server-minimal-8.4.12 | 单platform manifest、无index；amd64 `sha256:7dcc4add9183664de3a214daf85a50c3ba6cccfd7534f700b6561bf5b41885be`；config `sha256:c9570e7b94230d3717b88a334acaea49a4fe6b162f68a8f2927eaaf866b7f867` |

Docker Hub的mysql:8.4.12返回404，其当前目录列8.4.11；不以它替代批准target。
实际选用[MySQL官方文档指定的OCR Community渠道](https://dev.mysql.com/doc/refman/8.4/en/docker-mysql-getting-started.html)，
标准anonymous bearer读取确认8.4.12存在，且config为linux/amd64。公开构建history仍须由真实
server VERSION()/build及包信息核对，不等同跨channel interchangeable server。未解决identity
矛盾阻止执行验收；没有latest、预发行adapter、降级或架构emulation。

## Closed invocation and receipt boundary

```text
UV_PYTHON=3.13 uv run python tests/_pietto_target_conformance.py run
  --target postgres --pins tests/phase66_target_pins.json
  --evidence-dir ABSOLUTE_NEW_OWNED_DIRECTORY --run-id ID --run-attempt 1
UV_PYTHON=3.13 uv run python tests/_pietto_target_conformance.py verify-receipts
  --pins tests/phase66_target_pins.json --evidence-dir RECEIVED_DIRECTORY
  --expected-commit SHA --run-id ID --run-attempt 1
  --compiler-status COMPILER_STATUS --target-status TARGET_STATUS
```

status参数必须来自实际完成的对应检查；CI分别传入`needs.validation.result`和
`needs.target_conformance.result`，只有两者均为`success`才可接受完整收据。
MY只替换target。`--case`只接受下列固定case ID；省略为完整manifest，选择全部case也计完整
run。receipt verification是data-only；单target post-upload校验还要求artifact-id/digest，
aggregate校验两目标完整收据及compiler/target prerequisite outcomes。receipt文件上限32MiB，
为最大16MiB失败结果前缀及完整诊断/cleanup证据预留空间。没有数据库或Docker
连接、镜像获取、driver操作或重跑。未知/重复JSON keys、extra/missing字段、过期identity、
变更SQL/parameters、空/重复/缺失case、错误pins/build或cleanup未知均拒绝。

receipt独立格式`pietto.target-conformance-receipt.v1`。candidate包含实际Git HEAD及实际
build/harness/pins输入内容身份；dirty-local输入不冒称已发布HEAD，最终seal另在仓库外绑定。
hash只用于source→wheel→installed bytes、SQL/parameters及receipt transfer这些真实边界。
生成child运行真实installed console文件，记录同一child已加载module的wheel-relative origin
和bytes；另开import probe不能替代。默认argv无用户SQL与可重绑定parameter API。

## Independent finite manifest and observations

每个target都有恰好六个case；expected fixtures/results在cases owner中独立固定，不从compiler
mapping或observed输出生成，不以set/排序/epsilon隐藏BAG/type/order差异。

| ID / family | Frozen source or control | Independent expected outcome |
| --- | --- | --- |
| A_legacy | installed console编译一source Int not-null projection，加载两行(1),(1) | legacy v1成功且一个relation artifact，exact生成SQL原样提交；BAG恰为两行1；真实column metadata |
| B_result | 独立fixture及SQL按seq排序选id,note | [(7,NULL),(7,NULL),(9007199254740993,`雪?%s é 😀`)]，精确值/type及positional columns |
| C_parameters | PG原生$n复用large Int；MY原生?三次occurrences及显式独立SQL CAST | [large Int,Unicode text,large Int]，参数输入/顺序/类型保持；不是Phase66 slot/type-anchor builder |
| D_diagnostics | PG manager重复CREATE TABLE IF NOT EXISTS；MY manager INSERT IGNORE超长VARCHAR(5) | PG NOTICE/42P07复制于callback内，server total unavailable；MY warning1265，非clearing SHOW COUNT(*) WARNINGS和SHOW WARNINGS完整；max_error_count=0为明确expected incomplete-observer control |
| E_recovery | 同一connection success→PG除零或MY未知column→rollback→success | PG22012；MY1054/42S22；exact server-execute failure，实际rollback且session identity不变；不能reconnect代替 |
| F_privilege_cleanup | query identity成功SELECT、实际grants/role属性、denied管理操作和owned teardown | PG无schema CREATE，CREATE TABLE拒绝42501；MY无database CREATE，CREATE DATABASE拒绝1044/42000；无额外管理授权，所有取得live IDs最终不存在 |

管理操作与query操作分开；credential-bearing管理SQL不记录秘密内容。query SQL/ordered
parameters、driver call、rows/value tags、protocol-specific metadata/diagnostics、execute/fetch/
close/recovery各有观察。PG RawCursor先完整client-buffered，不声称真实late streaming；MY
prepared结果完整drain后才进行诊断查询，diagnostics在close或下一普通statement前捕获。
PG notice的Diagnostic对象仅callback内有效，立即复制scalar fields；无可用server total则null。
MY warning total与stored details独立，不能用会清除诊断的SELECT @@warning_count代替SHOW。
nullable metadata unavailable保持null，不推断false/non-null。prefix rows后error或overflow
只保留失败观察；expected observer-negative不能成为完整查询成功。

unit tests在零DB环境注入late fetch、missing metadata、diagnostic loss/truncation、timeout、
setup/recovery/cleanup及primary+cleanup failures，并检查pins、receipt/manifests、SQL/parameter
substitution、wrong installed origin、required job非success。injected证据与real server证据分别报告。

## Resource acquisition and close

resource helper先确认explicit本地Unix Docker endpoint及linux/amd64，忽略ambient Docker/DB
context、DSN、PG/service/credential files。需要时使用owned空client-config目录隔离registry
credentials；不修改用户或daemon配置、不login、不sudo、不触及其它服务。
MY使用owned container生成的public CA，显式证书链验证；不复制private key，自动生成证书的
名字不作为localhost hostname证明，endpoint身份由该CA加exact container/loopback port绑定。
固定`tls_versions=["TLSv1.2","TLSv1.3"]`与`ssl_verify_cert=True`；所选Connector使用原生
SSLContext和CA chain policy。MySQL自动证书缺少AKI，不能宣称通过Python3.13
`create_default_context()`附加的strict X.509 extension checks；不关闭证书链验证或使用明文fallback。
忽略ambient `SSLKEYLOGFILE`，失败保留脱敏native error及实际server running/exit/OOM状态。
PG使用明确的本地plaintext测试连接。两种transport姿态分别记录，不套用生产连接默认。
MY receipt记录从exact owned container复制的CA bytes SHA-256及image/container身份，并观察
manager/query两条实际session的`Ssl_cipher`与`Ssl_version`；空cipher/version为失败。
证书链验证配置、实际TLS及hostname未验证分别记录。参见[官方TLS状态定义](https://dev.mysql.com/doc/refman/8.4/en/server-status-variables.html)
和[Connector/Python连接参数](https://dev.mysql.com/doc/connector-python/en/connector-python-connectargs.html)。
每invocation新nonce、独占user-defined bridge（明确IPv4 NAT）、一个container，loopback-only ephemeral publish；data为
owned tmpfs，无host/network/socket mounts或privileged模式。1CPU/1GiB/pids128上限，两个local
target顺序执行。下载的immutable image cache可保留，非独占资源不删除。
Docker internal网络不提供所需host port publishing；使用独占bridge并检查实际唯一loopback
binding，记录network/port观察值，缺失或额外binding失败。此设施不提供通用出站网络sandbox，
container只运行指定server与固定fixture操作，不访问其它数据库或服务；参见[Docker端口发布](https://docs.docker.com/engine/network/port-publishing/)。

metadata30s、image pull600s、dependency sync300s、wheel build120s/install180s、generation30s。
startup/readiness总计≤120s，manager在10/60s两个检查点内尝试，预留query身份的初次连接，manager与query初次连接合计
最多3次；budget不足时不再连接，不以新身份隐藏第4次尝试。无内部retry层。
query≤10s、read≤20s、cleanup总计≤30s；每relation≤1000fixture rows，结果
≤100000rows/16MiB。PG server statement_timeout与本地deadline，MY原生read/write timeout及
本地deadline共同限时；不宣称Psycopg有不存在的read_timeout接口。

先持久记录creation intent/nonce，取得ID立即记录并登记cleanup；ambiguous creation按exact
intent/name/nonce/image关系核对，不以宽prefix删除，也不把暂未观察到当作确定不存在。
每个连接close、container stop/remove、network remove和最终absence分别记录；一个失败不
覆盖其它失败。PG实际rollback，MY fixture DDL不依赖rollback撤销。取消/timeout仍做bounded
owned cleanup；runner/process loss不保证清理，unknown永远不PASS。

## Required CI and transfer

保留validation的Python3.12/3.13、resource-aware/serial fallback、interpreter proof及四commands。
新target-conformance为Python3.13×{postgres,mysql}，fail-fast:false；每cell使用相同closed
runner。run/attempt/target专属单个secret-free JSON artifact，upload以if:always()保留失败
receipt，if-no-files-found:error、archive:false、overwrite:false、retention1day；禁止上传venv/
cache/原始process日志。每cell核对非空native artifact-id和其digest等于上传JSON bytes。
固定upload v7的`archive:false`使用该文件basename作为artifact name，忽略`name`参数。

aggregate needs validation和target-conformance，if:always()；只下载本run两个exact names，
逐artifact `digest-mismatch: error`，再data-only核对两个完整manifest及所有prerequisites。
missing/failed/cancelled/skipped/empty job、缺receipt、错误digest、incomplete observation或
unresolved cleanup都不能PASS。取消导致aggregate无法运行同样不是成功。
aggregate必须显式提供两种prerequisite status，无默认success。receipt/pins只读取identity
在打开前、opened descriptor和读后仍对应的regular file；符号链接、替换及读取期间变化失败。

新official actions经实际tag/source核对：

- upload-artifact v7.0.1：`043fb46d1a93c77aae656e7c1c64a875d1fc6a0a`。
- download-artifact v8.0.1：`3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c`；实际源码向client传
  expectedHash并在digestMismatch/error时throw，不能降为warning。

全局contents:read、persist-credentials:false及现有pull_request/push安全triggers保留，
无secrets/PAT/elevated events、dispatch/rerun、branch-protection或CI publication。
infrastructure逻辑位于四个tested helpers；YAML只组合固定步骤。

## Review, validation and publication

独立上限6 root-cause correction groups、4 authoritative starts、每target4 full local
manifest executions、一次ordinary initial commit及余额内最多一个natural-CI repair child。
第4组复评完整remaining findings/convergence；focused选例及startup尝试也记录，不重命名full
run绕预算，不自动重放不变的failed target。分类保持COMPILER_DEFECT、FIXTURE_OBSERVER_DEFECT、
INFRASTRUCTURE_FAILURE、TARGET_IMPLEMENTATION_DEFECT、UNRESOLVED_ATTRIBUTION。
production缺陷或第17路径需求为STOP。没有xfail/skip、optimizer/downgrade/scope-shrink绕路。

final applicable输入须通过两个Python的focused及unchanged authoritative/Ruff/Pyright、
generated/golden/package、两个完整真实target与独立receipt/cleanup验证；publication/Git
infrastructure另按development契约做depth-one验证。重叠authoritative可供应focused覆盖，
不为summary数字重复等价matrix。全部receipts/failed evidence置于
`~/.local/state/pietto/evidence/phase66-slice2/`，不写入Git或自引用未来commit/tree/CI。
seal→exact stage→ordinary commit→normal ff push→natural exact-head attempt1；两compiler jobs、
两target cells及strict aggregate全部成功才完成。

内部只读审查不是third-party review；真实legacy/control SQL不证明新ProjectSQLPlan lowering。
成功后Phase65 COMPLETED、Phase66 ACTIVE、Slice2 COMPLETED/PUBLISHED、Slice3 NEXT/NOT
IMPLEMENTED、Slices4–16 NOT IMPLEMENTED、N66=16。不开始Slice3，不宣称全部Phase66 exits。
