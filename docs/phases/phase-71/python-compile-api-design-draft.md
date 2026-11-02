# Compile-only Python API 设计草案（Phase75，未实现）

这是所有者要求的设计材料，不是现有 API 或已批准的兼容合同。函数、导出位置与
结果类型仍须由 Phase75 的公开 API 决定确认；本周期只交付设计。

## 推荐入口与替代方案

推荐两个窄入口，暂定如下；模块名尚未决定：

```python
compile_sql(project_root, *, module, kind, name, dialect,
            emission_contract, literal_policy="preserve") -> SqlEmissionResult
compile_all_sql(project_root, *, dialect, emission_contract,
                module=None, kind=None, name=None,
                literal_policy="preserve") -> SqlEmissionResult
```

前者对应一个精确 owner；后者对应已有 `--all`，三个可选 selector 是精确 AND
过滤，不支持通配符，也不改变 project authority order。首次只设计项目输入；
`dialect`、contract 采用 CLI 已有域，不引入默认 target；literal policy 仅采用已有
`preserve` 与 `bind-safe`，不是单值占位或新增扩展接口。
`project_root` 与 contract 首先采用现有路径输入和可信加载器，不额外接受可变的
已解析模型或调用者自制的 private context。

另一选择是一个 `compile_sql(..., all=False)` 入口；它少一个名称，但不同模式下
selector 的必填条件不如两个入口明确。直接扩展 `execution.compile_query` 则会
混合 SQL authoring 与执行资格，本草案不推荐。两者都留给 Phase75 确认。

## 最小结果与错误合同

暂定 `SqlEmissionResult` 是 frozen value，只含：

- `status`：沿用 `VERIFIED`、`BLOCKED`、`INPUT_REJECTED`。
- `document_bytes: bytes`：完整公开 JSON，包括既有结尾换行。单项使用已有 v1/v2；
  批量使用 `pietto.sql-emission.batch.v1`。
- `item_documents: tuple[bytes, ...]`：单项时是一项，批量时按公开顺序保留每个原始
  单项 document，顺序与 batch 的 items 相同。单项调用有 item 时，
  `item_documents[0] == document_bytes`。
  全局准备、selector 或累计输出限制错误时该 tuple 为空，但 `document_bytes`
  仍保留完整失败文档。

不再建立第二套 Diagnostic、SQL plan、owner identity 或 item schema。调用者可
解码公开 document；selector、位置、完整 diagnostics/blockers 及 suggestion
都从既有文档取得。返回 bytes 与 tuple 不暴露可变编译状态；内部产物只能在调用内
存活。是否需要便捷属性，应以 Phase75 的实际调用者为依据，而非先扩充返回类型。

Python 参数类型错误采用普通参数异常；类型正确但取值不合法的 dialect、policy
或 selector 走现有 CLI 对应的 INPUT_REJECTED 文档。有效参数所指的项目、contract、语义与
backend 拒绝使用既有失败文档。意外内部异常不得被伪装成成功或普通 BLOCKED；
其公开异常类型仍待 Phase75 决定。API 不调用 `sys.exit`。

批量逐项结果必须保留。状态优先级沿用 CLI：任一 INPUT_REJECTED 则整体为它，
否则任一 BLOCKED 则整体 BLOCKED，否则 VERIFIED；分别对应 CLI 的 2、1、0。
**逐项 INPUT_REJECTED 不自动清空其余 items**；只有已有全局失败边界才清空。
空匹配沿用 `emission_selector` / INPUT_REJECTED，不返回成功的空 batch。
不选第一个失败者，也不跳过 blocked 项。诊断顺序、位置、重复项与 authority
顺序全部采用现有公开文档，不另作排序或去重。

## 共同准备、可信输入与资源

内部复用现有一次准备 owner：parse、completed semantics、IR、bundle 后，逐 owner
执行 plan → verify → prepare → realize。CLI 与新 API 应消费同一产物，而非新建
编译管线。准备上下文仍是 private，不成为公共 cache 或可跨调用保留的对象。

同一选择与受信 opened bytes 必须产生相同单项 JSON bytes。批量 item 中嵌入原单项
JSON，嵌入时仅按现有 envelope 去除该 document 的最终换行；`item_documents` 保留
单项完整 bytes，不从外层 JSON 重新序列化来猜测原字节。整体批量 document 必须与
对应 CLI JSON stdout 相同，单项调用的行为和 bytes 不变。

每次调用重新取得当前 project/package/config/contract 的可信输入；不承诺多文件
文件系统的全局原子快照。已有 opened-bytes、路径、包身份、大小和读取失败边界
继续生效。不要接受 private plan 来绕过这些验证。

完整 canonical batch JSON（UTF-8 envelope 与最终换行也计入）的上限仍为
64 MiB。超限整体 INPUT_REJECTED，`batch_output_limit`，两个 item 集合均为空；
既有每项限制保留。这是输出字节上限，**不是进程峰值内存上限**。实现时应共享已有
bytes 引用，避免为便捷结果再建立一套大型对象图。

API 不提供 output 路径、目录写入、数据库、网络或任意 Python 执行，不增加 compiler
worker、异步任务或跨调用缓存。CLI 的 Linux 目录输出限制不适用于这个只返回 bytes
的入口；调用者自行写文件时也不能把 CLI 的原子目录保证当作 API 保证。

## 与 execution API 的关系及验收

现有 `pietto.execution.compile_query(...) -> CompiledQuery` 保持原有 import、参数、
结果与执行资格。新结果不是 CompiledQuery，不可直接传给 execution；不得凭能发射
SQL 推断某个 route 已开放。内部共同准备不改变 bundle 的信任或兼容维度。

Phase75 应在现有 CLI/项目发射 owners 中验证：单项/批量逐字节对应，混合状态与
全局错误、空匹配、selector 过滤与顺序、header parameters、两 target、literal
policy、64 MiB 边界、输入变更与失败后下一次调用的独立性。保留无数据库连接、
不写文件和不泄露 mutable context 的见证；自然 CI 与包导出检查仍须按当时闸门完成。

Phase75 的 owner 须确认最终名字/模块/参数类型、两个入口或一个入口、结果与内部
异常合同、兼容和版本策略，以及实测内存是否需要新的产品资源决定。本草案不承诺
`schema --json`、单文件入口、`now()` 或其他尚未批准的能力，也不改变阶段排期。
