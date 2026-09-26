# Phase67 Slice06：精确有限 Decimal128/256

基线 `8a97e089c130775e327cdbbebbbfee179fe8be80`，tree `48be1901a103f910faa7e883dead2068adde0876`，sole parent `76fef176a9c85eb907146866b3d2c60801a1dce1`；自然CI `36228301379`/push/main/attempt1 success已重新绑定。core既有CPython3.13.13无Arrow，`.agents/`保留，无已有S06候选。

本文件在production编辑前冻结。S06落实 [P67-A02/A03/A04/A06](brief.md#三层完成验收与回归)，保留A01/A05/A08/A11/A15/A16/A18。S07 meaning、S08 midpoint、S09 readers、S10 protocols、S11 ingress、S12 IPC、S13 extra、S14 integration保持各自owner。

## 私有接口与精确意义

在现有producer owner新增 `DecimalObservation(precision, scale)`，在 `ProducerObservation` 末尾追加 `decimal=None`，保持旧位置调用。Decimal必须domain=`decimal`、carrier=`decimal`，Int lower/upper与Text metadata均None；非Decimal的decimal metadata也必须None。不新增模块、generic registry或scalar solver。

| target | exact storage | exact domain | retained范围 |
| --- | --- | --- | --- |
| PostgreSQL | kind=pg_numeric,precision=p,scale=s | kind=decimal,precision=p,scale=s | 1≤p≤65；0≤s≤min(p,30) |
| MySQL | kind=my_decimal,precision=p,scale=s | kind=decimal,precision=p,scale=s | 同上 |

直接读取已验证 `SQLColumn.source_field.decimal` 的保留fact；storage/domain/observation各自与该fact核对，precision/scale必须exact int。完整root/source/export/column、顺序/label/provenance/nullability先验证，Arrow加宽不能修复producer谎报。只允许builtin参数化Decimal direct/projection，不增加nominal/arithmetic/window成功域。

`DecimalWidthRequest(field, bits)` 与 `bind_arrow(..., decimal_widths=None)` 使用完整positional tuple，None或绑定exact retained Decimal ResultField的128/256请求。默认p≤38选decimal128，39≤p≤65选decimal256；显式256低precision允许；p>38请求128拒绝，包括empty/all-null/small data。p/s不随适配变化，metadata不授予权威。现有Int/Text请求可并存。

D(p,s)为系数k满足abs(k)≤10**p−1的固定尺度数值。仅exact decimal.Decimal/合法None；拒绝非finite、subclass、coercion和其他scalar。不保留输入内部exponent/significance；正负Decimal零统一系数0、exponent=-s，Float signed-zero仍保持。

转换使用finite检查及as_tuple的sign/digits/exponent：去掉尾部零后计算固定尺度所需零数，先判断负shift或有效位数>p再构造至多p位tuple。零先单独处理。无ambient Decimal arithmetic、quantize、normalize、float中间值或大指数幂；上下文/flags不变。`1.2300`可精确成为1.23，`1.234`在s=2拒绝；极端±1000000 exponent早拒绝，零不展开幂。既有caller对象大小不由Arrow8MiB政策担保。

## 数据、资源与独立见证

真实 `.pietto` fixture采用 `amount: Decimal(p,s) not null` 与 nullable companion，select `renamed = amount`；mixed加入Int/Bool/Float/Text，并同时请求integer16/Text64/Decimal256。代表参数 `(1,0),(3,3),(9,2),(38,0),(39,4),(65,30)`，两目标各见证，不做全精度/尺度笛卡尔积。

Decimal每列charge=`ceil(r/8)+r*(bits/8)`，显式256按32bytes；numeric旧8byte、Text旧offset/UTF8政策和64fields/4096rows/8MiB上限不变。先dimensions/charge，再精确scalar preflight，再Arrow构造。supplied CPU carrier先schema/dimensions及所有引用buffer总和，再full validation和非NULL实际domain；尊重offset和validity bit offsets，不解释NULL槽payload。无borrowed/reader/C/IPC新接口。

冻结9个新增product案例，原38cases/9SDK/36damage controls全保留：

- `decimal_values`：有限p/s边界、两宽度、正负max系数、越界一单位、固定scale、trailing zeros与mixed/owned精确值。
- `decimal_bindings`：全部producer fact、field/root/label/nullability及协调schema损坏；upstream缺参数/unsupported记录真实拒绝层。
- `decimal_requests`：默认/显式选择、foreign/reordered/duplicate/wrong-kind/Bool/128-at39/arity以及precision/scale/schema/metadata拒绝。
- `decimal_context`：两种小precision、不同rounding/traps/已置flags，测量before/after完整context和>28位值；exact与refusal不变。
- `decimal_empty_null`：每宽度typed zero/all-null、nonnullable NULL拒绝、零统一及carrier/nonfinite/extreme-exponent拒绝。
- `decimal_resources`：16/32byte实际宽度、mixed精确小上限与少一byte；small slice retained过大，combined invalid value先LIMIT。
- `decimal_supplied`：真实小buffer、非零array/validity offsets、NULL任意payload、正负precision overflow、constructor和checker层明确。
- `decimal_substitution`：domain-valid值/sign/排列/duplicate/NULL/prefix与injected builder被独立oracle拒绝，不声称batch完成语义。
- `decimal_codec`：两target Decimal与mixed共4份新文档完整declared参数/provenance，原10份完整bytes保持、width不改变中立bytes。

报告期望从fixture coefficients、固定p/s/schema和独立整数/tuple构造取得，实际值从Arrow固定宽度coefficients读取，不调用product转换来算期望。新增9种实质report损坏（missing case/coefficient/scale/width/refusal/context/resource/supplied/codec），main末端精确controls改45；product总47。verify_report与跨runtime完整文档compare同步，现有ci_validation.check_product继续强制消费；不得改subset/>=。

## 精确路径与预算

21条冻结路径含reader reserves；新增仅本plan与principal，删除0，production仍228个Python，tests501→502。codec既有declared参数及correspondence可直接消费，无必要reserve。旧S02–05 tests和CI consumer/readers仅为真实接口影响reserve。

```text
src/pietto/_project/project_result_binding.py
src/pietto/_project/project_arrow_result.py
tests/_pietto_phase67_result_product_probe.py
tests/test_phase67_slice6_decimal_arrow.py
tests/test_phase67_slice2_result_contract_int_arrow.py
tests/test_phase67_slice3_result_contract_portable_boundary.py
tests/test_phase67_slice4_numeric_bool_float_arrow.py
tests/test_phase67_slice5_text_unicode_arrow.py
tests/test_active_phase_lifecycle.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
tests/test_phase11_ci_workflow.py
scripts/ci_validation.py
docs/phases/phase-67/slice-06.md
docs/phases/phase-67/brief.md
docs/phases/phase-67/slices.md
docs/phases/phase-67/planning-notes.md
docs/decisions.md
docs/references/engineering-lessons.md
docs/development.md
docs/status.md
docs/roadmap.md
```

lifecycle变更包含roadmap开头owner/next句、active段落、status表和test_active_phase_lifecycle的expected表/owner句/current方法；保留历史S05条件记录。最终状态在publication/raw证据完成前明确candidate。

预算：diagnostics6、focused12、corrections8、full默认1最多2、review/followup各1、Q2、env2、product每runtime3、SDK每runtime1、commit/push各1、failed-CI child/push/delta各1、native4通常3。local DB/full3.12/extra matrix/agents/detached/manual CI全0；唯一计数权威为新S06外部ledger。重任务guard on、top-level串行、≤4workers，core环境不重建不sync，所有project uv绑定既有解释器。

## Q1与执行顺序

Q1确认当前上游保留参数边界、API、精确数值/零意义、bounded tuple转换、当前typing/report/lifecycle读者完整；均属本次批准范围。先focused legal source/38–39/context/typing，首次installed直接含buffer检查顺序与malformed控制；一次主作者/Ponytail review、单批因果修复、一次targeted followup、depth-one affected reader；一次完整3.13 equivalent含五static/独立U/四分区及managed/health/auxiliary/两installed consumers。随后exact-tree seal/普通commit/FF push、自然15jobs、raw-byte GET/current context和三个fresh native strict checks。每一步及累计失败保存在durable ledger/JSONL，不把本结果矩阵称为native SQL新输入认证。

官方范围依据：[Arrow Decimal128](https://arrow.apache.org/docs/python/generated/pyarrow.decimal128.html)、[Decimal256](https://arrow.apache.org/docs/python/generated/pyarrow.decimal256.html)固定尺度与容量；[Python Decimal](https://docs.python.org/3.13/library/decimal.html)的tuple表示和构造精度独立性。产品范围仍以上游65/30为准；真实API行为由精确25.0.1 installed witnesses确认。

## HOLD：真实 retained Decimal 证据上限冲突

首次focused发现本文件Q1对上游可达范围的假设不成立。`semantic/analyzer.py:84`的 `_DECIMAL_PRECISION_MAX=38` 与742–792行共享参数规则保留38位上限；emission preparation调用该规则，超过38只保留None。下游 `representation_problem` 的65是依赖有效fact后的额外上限，不能证明39–65实际入域。两target的(38,0)均VERIFIED；(39,4)/(65,30)均BLOCKED，两个字段均 `PIE-B1004/validated_decimal_parameters_missing`；直接共享规则诊断 `PIE-S2004: Decimal precision must be an integer from 1 to 38`。

此行为已有Phase41 semantic与Phase66 emission回归覆盖。不能仅在result层绕过共享规则、伪造fact或用低precision显式256代替要求的39–65成功。保护owner未改；保留未完成候选与累计ledger，未启动installed/full/review/publication。最小后续决定是批准受控上游前提变更，明确合法precision范围及semantic owner/相关当前回归和文档的写入范围；收到续行前不继续产品改写，不开始S07。当前计划47cases/45controls尚未完成接入或验证，不称为已实现。

## 已批准续行：共享参数域扩展与Q-refreeze

用户明确激活addendum并额外批准Phase31 direct reader仅同步上限断言。W0为上文21条，加以下8条成为29条；全Slice ceiling32/additions≤3/deletions0；Q ceiling2→3，其余预算不变。原Q1的可达性假设错误、旧38位有效合同与正确HOLD保留历史。新增Q-refreeze通过，最终converged Q仍待执行。

```text
src/pietto/semantic/analyzer.py
tests/test_phase41_decimal_precision_scale_semantic_validation.py
tests/test_phase41_decimal_precision_scale_type_carrier.py
tests/test_phase66_slice3_minimal_source_realization_scan_projection_emission.py
docs/language.md
docs/spec/phase66-slice3-minimal-source-realization-scan-projection-emission-v1.md
docs/spec/aggregate-function-typeclasses-and-decimal-arithmetic-scope-lock-v1.md
tests/test_phase31_numeric_promotion_decimal_boundary.py
```

新批准语言接受范围precision1..65、scale0..p；规则、argument syntax、site、alias传播及diagnostic code/location/order不变。producer仍要求scale≤min(p,30)；(38,38)/(65,65)可有shared fact但无当前emission/result成功。Decimal128阈值38及deferred算术策略不改。直接消费者为legacy semantic analyzer、emission preparation和project_row_equivalence；后两production owner保持只读，新增真实高precision与不同参数/missing-fact回归。Phase31仅同步exact ceiling reader。

草案引用的原markdown hash与实际上传txt hash不同；上传txt与原保存副本一致，未改写二者。此provenance差异、refreeze失败及累计计数归外部ledger；当前用户明确批准的范围是续行权威。

## Slice06 Q3：收敛候选与最终验证边界

新增scope Q与原final Q均已消费，累计Q3/3。approved premise组228 passed，综合follow-up621 passed，真实3.13 installed47cases/45damage controls/162origins通过；旧38cases/36controls保留。一次主作者/Ponytail审查R1的preallocation与mixed cross-kind见证已闭合。ModuleType哨兵typing问题改用setattr，最新typing结论仍由随后一次完整rehearsal静态门给出；不把早先失败改写为PASS。

共享参数precision38→65是明确批准的语言接受扩展，算术/nominal/SQL/API/codec格式政策不改。原10份文档的完整保持及新增4份跨runtime一致性由最终两local/两CI报告核对。候选只有在depth-one、guarded完整3.13 equivalent、精确wheel消费者、seal/publication及自然15jobs/raw/native全部完成后才称published；不开始S07。
