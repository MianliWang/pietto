# Phase71 Slice19：嵌套断源读取与只读导出

状态：focused candidate。本片依赖 S18 的真实已保存候选；没有 Gate 2 与自然 CI
闭合前，不宣称 R1 或 `verified_export` 可发布。

S19 打开新进程的 `open_saved_read()` 与独立 `verified_export()`，只读取一个固定
checkpoint。两者继续从既有 `stored_binding()`、fresh trust、fixed-snapshot、
`SnapshotReader` 与 nested `open_ipc()` 路径取得 authority；不从 caller 参数、cache
或 IPC bytes 重建 authority。

## 读取和持久边界

- R1 的 consumer registration、replay session 与 ACK 语义不变；嵌套 child rows 不
  具有独立 consumer、ACK 或 cursor。
- `verified_export()` 不打开 coordinator、不做 control write、不推进 consumer state；
  它只持有读者和 v7 shared lease，并在 close 时释放它们。
- 每次交出 slice 都重新检查 acceptance 与 `SnapshotReader` 的进程/关闭状态。每个
  member 在首次交出任一 slice 前仍由 `SnapshotReader` 完整检查。重分批时仅在当前
  进程缓存该已验证 member，直到 member 耗尽或 close；cache 不持久、不跨进程，也不
  绕过 expiry、foreign-process、missing/corrupt path、descriptor/digest、schema 或
  IPC admission refusal。
- 未提交 staging 文件、已收集 member、错误 trust、错误 schema/contract 和非 fixed
  checkpoint 继续由原有边界拒绝。S19 不新增公开格式、CLI 或 trust policy。

## 候选检查

现有 `test_execution_api_saved_read.py`、
`test_execution_api_verified_export.py` 与 results/job owners 承担产品行为检查；新增
rebatch witness 必须证明一个 member 即使交出多个 batch 也只读验一次。真实 nested
producer/consumer、foreign/corrupt/path 与无控制写入证据仍须在可用的隔离环境中运行。

`root-held-cache-validation-03` 在同一候选上运行完整
`test_execution_api_verified_export.py`，结果为 19 passed、exit 0，包含 cache 填充后
acceptance expiry、foreign PID 与 reader closed 三个拒绝反例。该记录仍不是 B5 集成域、
native、Gate 2 或自然 CI 证据。

## 当前集成验收

新正例复用execution-API installed/native campaign；保存后移除源项目，再分别启动R1与verified_export新进程，不传入源连接参数。检查全8 leaf、retained组合、empty capture、逐parent ACK、原始child顺序与export前后持久控制状态/文件字节。SQLite SHM的临时读锁不作为持久内容。zero-row export不返回slice/schema，不把scope exhaustion升级为额外payload验证。

原生证据、Gate2和自然CI仍待完成；旧flat focused结果不作为nested正证。
