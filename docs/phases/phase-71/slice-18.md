# Phase71 Slice18：嵌套普通保存

发布状态：`COMPLETED / PUBLISHED`（main 的 B6 批次）。批次 head
`b9a50b23fc19c9ac096224b8449a1d6387dee2a8`，tree
`54bd20a86acf7ba8ecb3205649c4fa46d1718e36`；自然 CI `41420591084`
attempt 1 的 19 个 job 均成功。
以下保留实施时的候选与检查记录；其中的待验证文字属于封存前时点。

封存前记录：focused candidate。本片不封存、不发布，且不以 focused 检查替代 Gate 2 或自然 CI。

S18 只打开已经被 Phase71 私有 producer、结果合同、Arrow binding 与 IPC
reader 闭合的嵌套 `postgres_rows` 普通保存。它复用
`pietto.job-workspace.v7` 的既有 job、generation、attempt、顶层 occurrence、chunk
与 checkpoint 生命周期；一个 child row 不产生独立 checkpoint、ACK 或持久进度单位。

## 准入与边界

- `save()` 先保留既有 `_checked_request()` 的 compiled identity、route、binding、
  source、limit 与 PostgreSQL 准入，再进入既有 workspace registration 与
  `jobs.capture()` 生命周期。
- 保存的 chunk 仍经既有 result binding、`encode_ipc()` 与 capture descriptor 写入；
  S18 不新建 framing、schema、公开 JSON 或 durable trust 选择。
- 已有 publication eligibility 与 v7 completion 规则不变。S18 不承诺新 publication
  API，也不把 capture terminal 解释为 publication。
- `postgres_adbc`、MySQL、R2/recovery、sink 与 relay 对嵌套形状继续在各自既有边界
  拒绝；relay 的 `COLLECTION_ENTRY` 拒绝不属于本片的打开范围。

## 消费者闭合与候选检查

S18 的 producer 是实际 nested `postgres_rows` result binding；它的第一个 durable
consumer 是现有 capture/chunk/checkpoint 链，S19 才打开新进程读者。候选至少需要
覆盖成功保存的完整顶层 extent、空/零 batch、corrupt/foreign/path refusal、以及关闭后
资源释放；这些是现有 jobs/result owners 的行为测试，不新增 slice 命名测试文件。

S14/S15 leaf域与S16组合已由B5闭合；本片必须取得真实durable消费者证据，不能以B5的execute证据替代保存验收。

## 验收归属

B5已发布于305ab2c802258c2b3e932ccf236481dfc0e0034e（树6e335432490b8c7a64501519376c6dbfa59ec3cd，CI41390632023 attempt1 19/19）。本片使用其全8 leaf、retained/Unnest组合及empty三个实际保存代表，由既有execution-API原生campaign持有同一候选wheel和PostgreSQL获取；每次保存随后独立新进程R1与verified_export，完整schema/parent extent与child内容由独立oracle核对。

新强正例不放入core pytest后靠缺PyArrow跳过。core仅承接收据的接受与损坏拒绝；合格存储、PyArrow、真正数据库读取及断源消费者在既有installed/native owner执行。当前为候选，原生/Gate2/发布尚未完成。
