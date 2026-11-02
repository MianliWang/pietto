# `now()` 函数设计草稿（仅设计，未批准实现）

状态：供 owner 审阅。本草稿不授权语法、semantic/IR/SQL、CLI/JSON、execution API、
测试、版本或发行变更；也不声称 `now()` 已被 Pietto 接受。

## 已有边界

Pietto 的 `Timestamp` 是 civil、微秒精度、无 timezone 的值；现有意义契约拒绝
aware 值与 `fold=1`。因此不能把 PostgreSQL `timestamptz` 或 MySQL session-local
`DATETIME` 不经选择地当作同一 Timestamp，也不能在编译时读取本机时钟、把值写入
bundle、或把动态时钟当成可重放常量。

现有 execution 结果在一次已启动执行中可保存为事实。R1 与 `verified_export` 只读
已保存的 rows，必须保留原执行写入的 Timestamp，绝不重新求值 `now()`。只有实际重
执行 source/compiled SQL、或实际 retry 的新 statement 才取得新 snapshot。R2 的新
attempt/resume 如何处理动态时钟尚无批准语义，首次范围应继续拒绝或明确 defer。

## 目标数据库事实（只作设计输入）

- PostgreSQL 的 `now()`/`transaction_timestamp()` 是 transaction 开始时刻；
  `statement_timestamp()` 是当前语句开始时刻；`clock_timestamp()` 在同一语句内也
  会变化。它们返回 `timestamp with time zone`。见
  [PostgreSQL current date/time functions](https://www.postgresql.org/docs/current/functions-datetime.html)。
- MySQL 的 current-time 函数在一次 query 开始时只求值一次；`NOW()` 是该语句开始
  的常量，而 `SYSDATE()` 是调用时刻，且 `SET TIMESTAMP` 影响前者、不影响后者。
  `UTC_TIMESTAMP([fsp])` 返回 UTC date-time，且同属每 query 一次的 current-time
  函数。见 [MySQL 8.4 date and time functions](https://dev.mysql.com/doc/refman/8.4/en/date-and-time-functions.html)。

这些事实表明，裸 `now()` 在两目标间没有 transaction 级共同含义；wall-clock 也不
满足同一语句内的稳定性要求。

## 选择

| 选择 | 意义 | 跨目标/复现后果 | 结论 |
| --- | --- | --- | --- |
| A transaction snapshot | PostgreSQL transaction 起点 | MySQL `NOW()` 是 query/statement 起点；Pietto 不拥有用户 SQL 的 transaction 边界 | 不选 |
| B statement snapshot in UTC | 一次 target statement 开始时刻，转换为 UTC civil Timestamp，微秒精度 | PostgreSQL 形态为 `statement_timestamp() AT TIME ZONE 'UTC'`；MySQL 形态为 `UTC_TIMESTAMP(6)`；每次新 SQL 执行取得新值 | **推荐，待 owner 批准** |
| C wall clock | 每次函数调用的物理时刻 | 同一 statement 的行/表达式可不同，优化与重试都不能给稳定结果 | 拒绝/不设计 |

推荐 B 的核心是：`now()` 不表示“编译时间”、不表示调用 Python API 的本机时间、也
不表示一段 transaction 的时间；它只表示**该 target statement 的一次 UTC civil
snapshot**。这使 PostgreSQL/MySQL 的 transaction ownership 差异不进入 Pietto 的
公开语义，并与无 timezone 的 `Timestamp` 保持一致。

## 拟议下阶段范围（尚未实现）

若 owner 采纳 B，最小实现可只包括：

1. 零参数 `now()`，结果类型 `Timestamp`，只在 PostgreSQL/MySQL 已明确的 selected
   SQL target 上发射；未选 target 或未能证明 UTC civil 转换时确定拒绝。
2. 每个 emitted statement 内所有 `now()` occurrence 必须表示同一 snapshot；不得
   映射到 PostgreSQL `clock_timestamp()` 或 MySQL `SYSDATE()`。
3. 编译、check、explain、bundle serialisation 与 source-free loading 不读取时钟；
   artifact bytes 不含 snapshot。一次实际执行的交付结果可包含该次值；仅新 SQL
   执行或 actual retry 产生新 snapshot。R1 与 `verified_export` 读取原保存 rows，
   保留其中的原值，不重新求值。
4. 目标表达式自身给出 UTC civil 值，因此不为 `now()` 增加 session-time-zone option
   或新的连接前提；手动 `emit-sql` 与 execution API 都发射同一精确 target form。
   仍须在实施阶段验证 decoder 与既有 civil Timestamp 范围/微秒约束的对应。
5. 先只准入普通 scalar projection。谓词、join、group/order key、default/DDL、保存
   资格、R2 resume/refinement、constant folding 与任何 cache key 的规则均保持拒绝或
   deferred，直到各自 owner 明确接收。

本草案的实现属于下一阶段的函数/时间语义工作；S23 只附设计供审阅，
不将它列为本版功能。实施需要现有
Timestamp contract、semantic catalog/signature、target emitter、execution/session
owner 与 source/compiled/installed consumers 的联合设计和验证。

## 仍需 owner 决定

是否采纳选择 B 的 UTC statement-snapshot 意义，还是继续拒绝 `now()`？若采纳，
后续阶段再按其自己的公开语言闸门决定拼写和首次准入 contexts；本草稿不预选这些
公开细节，也不把 R2 动态时钟语义带入首次范围。

## 相关函数的范围

`concat` 与 `stddev` 保持 owner 已定的下一阶段函数工作：它们不因本草稿获得实现、
类型、target 或 release 授权。`now()` 只先完成本设计；三者不应为了共享一次改动而
合并，也不应借 Phase71/B8 自动进入公开面。
