# Phase68 Slice18：执行 extras、安装后的恢复运行时与精确兼容边界

S18 CANDIDATE; completed only after closure。基线 B18 为 PR #81 维护的 published head
`9d0866871a45ef17a352b2dc0218942356eb4c21`（唯一父 S17 head `12f0f8adfc2a3873ee31b0bab86e565aa8ab96f3`），自然
CI37495792058/push/main/attempt1；S17 以 COMPLETED_WITH_DISCLOSED_PROCESS_EXCEPTION 闭合，C16 一次性接受、历史保留。本文只描述
候选合同；当前安装/兼容/原生验收、精确 Git tree、普通 FF 发布、自然 exact-head CI 的全部消费者和 owned cleanup 共同激活完成。
S19 NEXT / NOT STARTED / separate dispatch required。extra 名称是本切片实际交付的打包面，不是稳定公共执行 API 承诺。

## 范围与选定打包

S18 承担 A21（安装与回归）与 A19（兼容与秘密边界）。应用可以有意安装三条既有路线之一的依赖闭包，或只安装已保存结果运行时的依赖，
再经原显式私有 owner 与其原授权/资格检查使用。安装从不创建 job、打开 source、授予权限或证明存储保证。基础依赖（ANTLR）、
`requires-python >=3.12`、版本 0.1.0、`pietto` 控制台入口与 `arrow` extra 不变；extra 名称与组合由 S18 派发选定：

| 选择 | 直接可选依赖 | 含义 |
| --- | --- | --- |
| `pietto` | 无 | compiler/CLI 与既有 core；不拉入 Arrow 或驱动 |
| `pietto[arrow]` | `pyarrow==25.0.1` | 既有 Arrow 能力；合格主机上无驱动的已保存结果操作（R1、S16 发布/查询、S17 REPLAY/PUBLISH 与回收、S15 参考 sink 交付） |
| `pietto[execute-postgres]` | `pyarrow==25.0.1`、`psycopg[binary]==3.3.5` | 既有 PG rows 路线与其持久结果路径 |
| `pietto[execute-mysql]` | `pyarrow==25.0.1`、`mysql-connector-python==26.7.0` | 既有 MySQL rows 路线与其持久结果路径 |
| `pietto[execute-postgres-adbc]` | `pyarrow==25.0.1`、`adbc-driver-postgresql==1.12.0`、`adbc-driver-manager==1.12.0` | 既有 PG ADBC 路线与其持久结果路径 |
| 三个执行 extra 的并集 | 上述之并 | 有意组合的原生环境；不是自动首选路线 |

没有 `recovery` 别名、默认全驱动 extra、平台 marker 或第二套结果实现。三个执行 extra 包含 Arrow，因为既有受检捕获/结果路径使用它。
lock 只为三个 extra 增加 adbc-driver-manager 1.12.0、adbc-driver-postgresql 1.12.0 与 importlib-resources 6.5.2（以一次性
`uv lock --upgrade-package importlib-resources==6.5.2` 保留已测版本，lock 记录它，无持久约束）；`pietto` 条目之外的既有包、
Ruff 0.16.10、typing-extensions 4.15.0 与解析 marker 不变；两只 ADBC Linux wheel 保持 S01 的 URL/hash 来源。
`ci/phase68-executor-premise-requirements.txt` 仍是 S01 历史测试资格，不重解释为通用产品支持。

## 选定路线的依赖边界

`project_execution.pinned_modules(pins, version_error)` 是唯一共享的窄桥（不含驱动名）：逐项先查分发版本，再无 I/O 导入模块。
缺失分发或该模块本身（或其父包）缺失为 `EXECUTION_DEPENDENCY_MISSING`；装了别的版本为该路线既有版本码（MySQL 与现在的
PG rows 为 `EXECUTION_DRIVER_VERSION`，ADBC 为 `POSTGRES_ADBC_DRIVER_PROFILE`）；其他导入失败（损坏的传递依赖或原生库）原样传播，
从不冒充“未安装”。每条路线自己的原生模块持有 `DRIVERS` 与 `drivers()`：PG rows 校验 psycopg 与 psycopg-binary 3.3.5，并要求
`psycopg.pq.__impl__ == "binary"`（否则 `POSTGRES_DRIVER_LIBRARY`：损坏的 binary 或 `PSYCOPG_IMPL` 会静默改用系统 libpq）；
ADBC 校验 driver/manager/pyarrow 与驱动自带 `.so`（`POSTGRES_ADBC_DRIVER_LIBRARY`）；MySQL 校验 connector 26.7.0。

实际使用边界：各 owner 的 `connect`/`_connect` 在原 ambient profile 检查之后、任何连接之前调用 `drivers()`。预检：`Runtime.submit()`
对 CAPTURE/RELAY/RECOVER 在入队、admission 行与 worker 之前加载该单元所选路线的驱动；未知路线以既有 `RUNTIME_ROUTE` 提前拒绝；
REPLAY/PUBLISH 与回收从不加载驱动。Arrow 仍由既有 Arrow owner 边界（`ARROW_DEPENDENCY_MISSING`）负责；受支持的路线选择都含 Arrow。
owner 构造器、`prepare_*execution` 与 `open_attempt` 不检查依赖（它们是无 I/O 的元数据/记录操作）；直接主机自己先打开的 attempt
属于该主机的显式变更。预检信息从不替代使用边界检查，也不能复活已关闭或过期的接受。组合环境中路线缺失或错误时从不改用另一个
已装驱动，也没有自动安装或重试。

## 兼容：精确格式、旧运行时与编译代码

v1–v7 信封、schema、目录与操作语义不变，S18 不增加 v8；能力只按 `supports()` 精确判断。当前安装运行时与安装的存档 S17 运行时
对 v1–v7 的特性集、user_version、schema digest 与能力门完全相同；新格式能力在旧格式上于任何应用变更前拒绝。四层分开：(a) 未知/未来/
多余特性/重排的信封在 SQLite 打开前 `WORKSPACE_FORMAT`，目录不变（安装的存档 S16 运行时对 S18 v7 同样拒绝）；(b) 已识别格式的
schema 损坏 `WORKSPACE_SCHEMA`；(c) `semantic_build_identity()` 覆盖全部 pietto/ANTLR `.py` 字节，S18 改动生产代码，故 S17 bundle
在 S18 加载为 `COMPILED_COMPATIBILITY`、S17 存储的 job/binding 为 `JOB_COMPATIBILITY`，而 S17 工作区本身仍可打开；(d) S18 自己的
bundle 与工作区在新鲜调用方输入下接受。包版本同为 0.1.0 既不推出兼容也不推出拒绝；身份由独立检查器从实际 wheel 字节重算。

## 验证

核心环境（无 Arrow、无数据库）：精确 extras/lock/逐选择闭包、制品 METADATA 的 requirement extras 解析与协调损坏、受控依赖决策表、
路线 pins 等于所声明 extra、运行时预检在 admission/worker 前拒绝且无应用变更、直接 owner 在连接前拒绝、懒导入，以及 v1–v7 能力矩阵、
信封与 schema 程序在合格本地 profile 的新进程中运行；独立检查器（`tests/_pietto_phase68_slice18_check.py`）以自身字面期望判断，
八类协调损坏各由指定定律拒绝。真实证据由 `scripts/phase68_slice18_probe.py` 产生：`install` 以经校验的 lock 制品 wheelhouse 对同一
wheel 做六个全新前缀的正常解析安装（无 `--no-deps`、无预装驱动）、`uv pip check`、安装后来源逐字节核对与路线/懒导入观察、
解析负例与损坏安装负例；`compat` 运行格式矩阵、信封/schema 与存档 S16/S17 运行时；`native` 在三路线 × live/bundle ×
source/installed 上经各自所选 extra 前缀运行原 S17 联合历史、并集路由与无回退控制、删源后 Arrow-only 无驱动尾部（发布查询、
S13 重启窗口、保留 consumer、回收、真实 sink 丢失回复与新提取/R2 拒绝）。

| 后续 | S18 提供 | S18 不实现 |
| --- | --- | --- |
| S19 | 六个依赖闭包、安装/来源/拒绝码、格式与代码兼容层、损坏目录与证据类别 | 全矩阵联合验收与阶段末获取合并 |
| Phase69 | extra 名称作为实际打包面、支持域表与错误类别 | 公共执行 API、发布工程、更广平台承诺 |
