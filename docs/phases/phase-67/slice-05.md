# Phase67 Slice05：Text、Unicode 与显式 Arrow offset 宽度

基线 `76fef176a9c85eb907146866b3d2c60801a1dce1`，tree `e3688dde9a283a450b4b19f2000790c8d177c03a`，sole parent `be51fef66655e68d7fb450649a5b2061115016d1`；已重新读取自然 push/main CI `36224628578` attempt1 success。`.agents/` 保留；core CPython3.13.13 无 Arrow。

本文件在 production 编辑前冻结。只展开 P67-A02/A03/A04/A06/A07，保留 A01/A05/A08/A11/A15/A16/A18；验收定义见 [brief](brief.md)。S06 Decimal、S07 meaning、S08 finite integration、S09 reader、S10 protocols、S11 ingress、S12 IPC、S13 extra、S14 producer integration 保持后续 owner。

## 私有接口与生产者边界

沿用两个 result owners，不加文件、registry 或 scalar solver。`TextObservation(max_characters, encoding, collation, padding, storage_length=None)` 加在 producer owner，`ProducerObservation` 末尾追加 `text=None`，保持全部既有位置参数；Text 的 domain=`text`、carrier=`str`、lower/upper=None。字段身份、position/label、target、exact storage keys/parameters、logical nullability 和整个 emission/export correspondence 先于 Arrow 核验。

| target/storage | 域与长度 | carrier/default |
| --- | --- | --- |
| PostgreSQL `pg_text`，仅 kind | UTF8/C/NO PAD；exact int max_characters≥0；无 storage_length | exact str / string |
| MySQL `my_varchar`，kind+length | utf8mb4/utf8mb4_0900_bin/NO PAD；exact int 0≤max_characters≤length≤16383 | exact str / string |

`TextOffsetWidthRequest(field, bits)` 与 `bind_arrow(..., text_offset_widths=None)`：完整 positional tuple，每项 None 或 exact retained ResultField 的32/64请求；None默认32。与现有 integer_widths 独立并存。错误kind/foreign/reordered/duplicate/arity/Bool/width均拒绝；schema不能选择宽度。offset选择不改变 neutral canonical bytes。

合法 fixture 为 builtin `shape Row`，`text: Text not null`、`maybe_text: Text nullable`，direct source 到 select `renamed = text`、`maybe_text`；mixed 追加 Int/Bool/Float。上游结构及 exact descriptors 经首轮 focused group 确认；不为错误fixture放宽语义。

值保留空串、ASCII/CJK/补充平面、组合序列、空白、重复、NULL与顺序；max_characters按有效Python str码点计，不规范化。拒绝非exact str、surrogates、超domain、nonnullable NULL。pg_text拒绝U+0000；my_varchar保留supplied-row NUL。collation/padding只是核对的producer事实，不提供Arrow比较语义。独立值oracle才能识别domain-valid替换。

## 资源与 supplied carrier

保留64fields/4096rows/8MiB及caller-only tightening；numeric/Bool/Float仍收每列 `8*r+ceil(r/8)`。Text每列 `ceil(r/8)+(bits/8)*(r+1)+strict_utf8_bytes`；包含zero/all-null offsets，mixed求和，另核对signed offset范围。先核对尺寸/type/domain，再有界逐码点计UTF-8，无不受限encode或大fixture；这些是准入计费，不是Python RSS保证。

supplied CPU RecordBatch先检查type/schema/dimensions和所有引用buffers的保守总和，再 `validate(full=True)` 与logical value/domain。非零slice offset交给Arrow受支持的scalar访问；NULL槽内容不解释为字符串，但占用计入retained bytes。不做memory去重、重建、cast或借用输出API。畸形offset/UTF8仅以实际分配的小buffers构造，记录constructor或checker真实拒绝层。

## 有限manifest与独立验收

保留原30product案例、9SDK组和28damage controls；新增8个命名案例：

- `text_values`：两target default/large、mixed整数请求、精确schema/值/NULL/UTF8/码点数与owned不受caller替换影响。
- `text_binding`：完整观察及root/field/label/domain/storage漂移、协调schema伪造、上游unsupported与同根合法不同表示。
- `text_requests`：32/64显式请求及foreign/reordered/duplicate/missing/extra/wrong-kind/Bool/unsupported negatives。
- `text_empty_null`：两宽度zero/all-null；max=0空串、max边界/多字节、nullable与NUL target差异。
- `text_resources`：精确小计费/一字节超限、mixed、offset开销、retained大buffer小slice。
- `text_supplied`：非零offset、NULL未指定payload、schema/metadata/type拒绝、畸形offset及invalid UTF8的checker见证。
- `text_value_substitution`：有效替换、trim/casefold/normalization/NULL/order/multiplicity由独立oracle拒绝；注入builder也不能伪造PASS。
- `text_codec`：两target Text与mixed共4份新canonical文档、pure与live核验；原S03四份与S04两份完整bytes保持。

报告checker检查实际schema/value/UTF8/domain/resource observations，完整case equality；damage suite追加8个不同损坏，末端exact assertion更新为36。full canonical comparison添加text_codec。`scripts/ci_validation.py:check_product`现有required consumer自动调用同一checker；保留必要reader reserve，不新增workflow步骤。

## 精确write freeze与预算

20条冻结路径（含5个reader reserves），新增仅plan与principal共2条，删除0；不加private helper。typing direct scan仍228个production Python，tests 500→501；owner为现有static-analysis-stage test。lifecycle direct reader为 `test_active_phase_lifecycle.py` 当前Slice04方法，更新为Slice05/next06；status/roadmap最终条件闭合保留15jobs/N67=16/package0.1.0。

```text
src/pietto/_project/project_result_binding.py
src/pietto/_project/project_arrow_result.py
tests/_pietto_phase67_result_product_probe.py
tests/test_phase67_slice5_text_unicode_arrow.py
tests/test_phase67_slice2_result_contract_int_arrow.py
tests/test_phase67_slice3_result_contract_portable_boundary.py
tests/test_phase67_slice4_numeric_bool_float_arrow.py
tests/test_active_phase_lifecycle.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
tests/test_phase11_ci_workflow.py
scripts/ci_validation.py
docs/phases/phase-67/slice-05.md
docs/phases/phase-67/brief.md
docs/phases/phase-67/slices.md
docs/phases/phase-67/planning-notes.md
docs/decisions.md
docs/references/engineering-lessons.md
docs/development.md
docs/status.md
docs/roadmap.md
```

reader reserves为旧S02/S03/S04 principal、test_phase11_ci_workflow.py、scripts/ci_validation.py；其余是实现/证据/文档路径。codec owners无当前需要，不冻结不编辑。预算：diagnostics6、focused12、corrections8、full2（默认1）、review/followup各1、Q2、外部env2、product每runtime3、SDK每runtime1、commit/push各1、failed-CI child/push/delta各1、native4（通常3）；agents/detached/local DB/full3.12/manual CI全0。唯一计数权威是外部S05 ledger，失败starts累积。

## Q1 与执行顺序

Q1：已绑定当前upstream Text admission及现有owner/readers，API/字节/identity/source/value独立oracle覆盖上述acceptance；无新产品或架构待决。先focused syntax/domain/typing，再installed真实小buffer与value witnesses；一次主作者/Ponytail review与完整finding set修复，targeted followup和depth-one affected readers；一次最终guarded3.13 equivalent含五static gates、独立全collection、四分区串行≤4workers、reconciliation/health、generated/golden/package、两isolated pinned consumers。seal、ordinary commit/FF push、自然15jobs exact-head CI、raw GET字节证据、fresh receipt普通文件preflight及三个strict data-only checks。绝不把历史receipt当新head证据。

## 官方依据与证据分层

[Arrow layout](https://arrow.apache.org/docs/format/Columnar.html)、[StringArray](https://arrow.apache.org/docs/python/generated/pyarrow.StringArray.html)、[large_string](https://arrow.apache.org/docs/python/generated/pyarrow.large_string.html)：offset、NULL槽和slice规则；保守逐buffer引用计费保持本项目既有政策。
[PostgreSQL18 character](https://www.postgresql.org/docs/18/datatype-character.html) 明确字符存储不含code zero；[MySQL8.4 literals](https://dev.mysql.com/doc/refman/8.4/en/string-literals.html) 明确NUL字符表示。这里是result-boundary witnesses，无新native DB输入或执行认证。
[Astra task context/decision boundaries](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra) 用于明确任务上下文、裁决边界和完成条件；执行权限/预算以本次dispatch为准。

## Slice05 Q2 / 最终候选

一次主作者/Ponytail审查与targeted followup闭合；真实3.13 installed38cases/36damage controls通过，包含先retained-limit后UTF8验证、NULL任意payload、nonzero offsets、extension/schema拒绝、逐字段宽度、domain-valid截尾与注入builder拒绝。首次typing与旧numeric helper、当前lifecycle表reader失败均保留在本Sliceledger；修正没有放宽任何旧拒绝或集合相等断言。最终只余guarded完整3.13 equivalent、两runtime最终wheel/readiness、depth-one读者、exact-tree publication与fresh natural-CI raw/native闭合；完成声明以这些证据为条件。
