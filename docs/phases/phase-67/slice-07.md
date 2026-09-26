# Phase67 Slice07：显式上游 meaning、Timestamp 与 UUID

用户已明确批准并dispatch四项选择，并额外批准 `project_sql_emission_portable_schema.py` 仅新增upstream identity CUTOFF声明。基线HEAD `7c1a944d94d6b21d5031679b2497ef58da5f9115`，tree `76dc1c6bca53513d6c070b578844a0e241d2003d`，parent `8a97e089c130775e327cdbbebbbfee179fe8be80`，自然CI36259274452/push/main/attempt1 success；core3.13.13 Arrow-free。S07新ledger，未重置或重跑S06。

## 意义与边界

S07落实 [P67-A02/A03/A04/A06/A07](brief.md#三层完成验收与回归)，保留A01/A05/A08/A11/A15/A16/A18。沿用N67=16；S08 integration/midpoint、S09 finite completion、S10 C/lifetime、S11 ingress、S12 IPC、S13 extra、S14 broader integration不启动。

Timestamp是proleptic Gregorian civil date/time，精确microsecond、无timezone转换；inclusive `[1000-01-01 00:00:00.000000, 9999-12-31 23:59:59.499999]`。此前V05只到year-level，精确末端是本次批准的保守共同transport域，非pinned server实测最大值。499999只约束最后端点；早期时刻仍允许microsecond999999。UUID保留标准big-endian16bytes的全部128bits，不限制version/variant，不生成/parse/比较。

## 上游owner与显式接口

新增唯一private owner `project_scalar_meaning.py`，Arrow-free/target-neutral，闭合 `TimestampMeaning`、`UUIDMeaning` law records，`ScalarMeaningEntry` 与 `ScalarMeaningBundle`。`acquire_scalar_meaning(verification)`只读取真实已验证plan/completed/type-resolution source-port inventory，为actual builtin Timestamp/UUID按源顺序派生entries。保留exact verification、source-port/field、declared TypeExpr、canonical type与resolution occurrence。无registry/cache/trusted flag/自由解释字符串/第二solver。

`verify_scalar_meaning(bundle, verification)`独立逐项核对root、完整source denominator、精确object identity、closed law和顺序，不调用acquisition重建。result输出通过已验证source/projection links找到同一source entry，重命名/重排/重复投影保持不同ordered输出occurrences；不能按label挑winner。

`prepare_project_sql_emission(..., scalar_meaning=None)`和`emit_project_sql(..., scalar_meaning=None)`显式private输入；`build_result_contract(checked, *, scalar_meaning=None)`也显式接收同一bundle。旧callers/CLI/native fixtures不自动获取意义，absence维持PIE-B1004。PreparedEmission与BoundField追加可选引用并在applicability完整验证；所有artifact验证既有路径调用emission_blockers，因此无需修改protected verifier owner。新CUTOFF仅标识旧emission observation不传输的runtime identity引用；完整meaning描述归neutral result codec，旧wire字段不改。异常/foreign bundle产生typed input/correspondence失败，不当成absence。

ResultContract保留bundle，ResultField追加meaning entry；producer核对contract与emission使用同一bundle、完整column/export对应及source entry。ProducerObservation末尾追加 `meaning` law与 `fractional_seconds`，旧位置调用及Int/Text/Decimal metadata兼容。

| logical / source storage | exact domain / observed carrier | Arrow |
| --- | --- | --- |
| Timestamp / pg_timestamp或my_datetime，fractional_seconds=6 | timestamp，已核验civil law；exact naive datetime，fold=0 | timestamp(us,tz=None) |
| UUID / pg_uuid | uuid/standard_bytes；exact uuid.UUID，使用.bytes | pa.uuid()默认 |
| UUID / my_uuid_bytes | uuid/standard_bytes；exact immutable bytes，len16 | pa.uuid()默认 |

`UUIDRepresentationRequest(field, representation)`与`bind_arrow(..., uuid_representations=None)`采用完整positional tuple；representation仅`uuid`或`binary16`。默认canonical pa.uuid；显式binary16为pa.binary(16)，不fallback、不改变logical UUID及中立bytes；旧Int/Text/Decimal请求可并存。schema检查exact UuidType且storage16，拒绝伪extension类/name metadata；不改global registry。无Timestamp unit请求。

## 数值与资源

Timestamp只用naive epoch加减的integer days/seconds/microseconds，不调用timestamp()/total_seconds()/mktime。supplied批次直接读取signed int64 ticks先判已批准范围，NULL payload不解释，越界不as_py溢出。UUID先独立检查PG object/MySQL bytes载体，再标准16byte构造canonical extension或显式binary16；比较实际bytes的oracle才能识别domain-valid byte swap。

保留64fields/4096rows/8MiB及S03独立codec limits；Timestamp charge=ceil(r/8)+8r，UUID两表示均ceil(r/8)+16r；Int/Bool/Float、Text offsets/UTF8、Decimal16/32byte不变。row preflight先于buffer构造，supplied保留先type/schema/dimensions/retained buffers，再full validation、非NULL域的顺序；无新dedup/reader/borrowed/C/IPC。

## Neutral描述与旧文档

无meaning的旧document保持原exact keys/bytes。显式bundle启用可选top-level `scalar_meaning` closed record，包含format与完整source entry描述；相关Timestamp/UUID leaf有整数`meaning`索引。source描述包含source port coordinate、source output/position、declared/canonical、resolution及closed law。pure checker按完整record keys、law、reference/type一致性检查；标记存在却缺meaning字段拒绝。删除整个可选分支可以形成旧描述，但与带meaning的live contract必须CORRESPONDENCE失败，不能复活authority。独立runtime checker直接核对supplied live bundle/source/outputs，不重新export。

原14份canonical documents保持；新增两target temporal与mixed共4份。Arrow UUID representation不改neutral bytes，两个final local及两个downloaded CI报告完整比较18份文档。

## 紧凑manifest与读者

原47product/45damage controls/9SDK保留；新增9组，product总56；追加9种实质report damage，末端总54。planned分母须真实required consumer验证：

- meaning_premise：两type/target真实source，private success，absence/foreign/altered/nominal、完整source/output identity。
- timestamp_values：显式ticks -1/0/+1、pre-epoch、leap、端点/外一微秒、普通999999与far future，components独立。
- timestamp_policy：aware/fold/subclass/date/coercion、unit/tz/schema及安全越界ticks。
- uuid_values：PG UUID/MySQL bytes、canonical/binary16，nonsymmetric/nil/all-one/zero/NULL/重复。
- uuid_policy：exact requests、wrong carrier/length/order declaration、fake extension/metadata及不fallback。
- temporal_empty_mixed：typed zero/all-null、Int/Text/Decimal/UUID同时请求、owned isolation。
- temporal_resources：精确小allowance/少1byte、nonzero/validity offset/NULLpayload、retained-before-invalid及allocation sentinel。
- temporal_correspondence：in-domain time/UUID替换、swap、NULL、permutation、lost duplicate/prefix及injected builder；不声称S09完成语义。
- temporal_codec：18份完整描述、pure/live独立、source/output graft、meaning缺失/变更、width-neutral bytes。

所有预期从固定calendar components、显式整数ticks、UUID hex bytes和资源算术独立编写，不调用product转换生成期望。main CASES、verify_report、damage suite、main终端计数、compare_product_reports及现有ci_validation.check_product一并闭合。typing inventory229production/503tests；required origins新增meaning owner。lifecycle开头句、status表、current段与sole reader同步，历史V05/S06保留。

## 精确write freeze、Q与预算

冻结36路径，新增仅meaning owner/S07 principal/S07 plan共3，删除0；第四helper不使用。旧结果principals、emission principals、CI consumer路径仅为直接reader兼容reserve，不因列入而编辑。

```text
src/pietto/_project/project_scalar_meaning.py
src/pietto/_project/project_sql_emission_contract.py
src/pietto/_project/project_sql_emission_ast.py
src/pietto/_project/project_sql_emission.py
src/pietto/_project/project_sql_emission_portable_schema.py
src/pietto/_project/project_result_contract.py
src/pietto/_project/project_result_binding.py
src/pietto/_project/project_arrow_result.py
src/pietto/_project/project_result_contract_portable.py
src/pietto/_project/project_result_contract_pure_boundary.py
src/pietto/_project/project_result_contract_correspondence.py
tests/_pietto_phase67_result_product_probe.py
tests/test_phase67_slice7_timestamp_uuid_arrow.py
tests/test_phase67_slice2_result_contract_int_arrow.py
tests/test_phase67_slice3_result_contract_portable_boundary.py
tests/test_phase67_slice4_numeric_bool_float_arrow.py
tests/test_phase67_slice5_text_unicode_arrow.py
tests/test_phase67_slice6_decimal_arrow.py
tests/test_active_phase_lifecycle.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
tests/test_phase66_slice3_minimal_source_realization_scan_projection_emission.py
tests/test_phase66_slice14_private_emission_observation_process_integration.py
tests/test_phase11_ci_workflow.py
scripts/ci_validation.py
docs/phases/phase-67/slice-07.md
docs/phases/phase-67/brief.md
docs/phases/phase-67/slices.md
docs/phases/phase-67/planning-notes.md
docs/decisions.md
docs/language.md
docs/development.md
docs/status.md
docs/roadmap.md
docs/references/engineering-lessons.md
docs/spec/phase66-dialect-sql-emission-product-phase-initiation-gate-route-lock-v1.md
docs/spec/phase66-slice3-minimal-source-realization-scan-projection-emission-v1.md
```

Q1确认实际authority producer、独立verifier、source/output mapping和default absence路径；先实现/执行Arrow-free premise vertical，Q2确认可达后才跑Arrow矩阵。全候选一次author/Ponytail review、单批因果修复、一次targeted followup，depth-one与Q3后一次完整guarded3.13 equivalent；exact-tree普通commit/FF push、自然15jobs及fresh raw/native闭合。没有分开的前提publication。

预算diagnostics6/focused12/corrections8/full默认1最多2/review1/followup1/Q3/env2/product每runtime3/SDK各1/commit1/push1/failed-CI child与push/delta各1/native4通常3。agents/detached/manual CI/local DB/full3.12/extra matrix全部0。guard on，top-level串行≤4workers；所有project uv绑定core解释器，保持core Arrow-free。新ledger及meaningful-step JSONL记录全部失败与owned roots。

## 官方依据与明确限制

[MySQL8.4 datetime](https://dev.mysql.com/doc/refman/8.4/en/datetime.html) 的原文字面范围为 `'1000-01-01 00:00:00.000000' to '9999-12-31 23:59:59.499999'`；本次取其保守共同域，不称pinned server实测。
[Arrow UUID](https://arrow.apache.org/docs/format/CanonicalExtensions.html#uuid)规定canonical extension使用标准big-endian fixed-size16bytes且无特定version保证；[Python UUID](https://docs.python.org/3.13/library/uuid.html)区分.bytes/.bytes_le；[Timestamp API](https://arrow.apache.org/docs/python/generated/pyarrow.timestamp.html)与[datetime](https://docs.python.org/3.13/library/datetime.html)提供编码机制，不能代替Pietto的意义授权。
新native receipts仅认证未扩展的既有manifest和当前输入closure；不认证S07 supplied-row矩阵为新native SQL执行或准确端点实测。public exposure与后续native接线仍归后续明确授权工作。

## Slice07 Q3 / 最终候选

Q1 scope、Q2 reached premise与Q3 final candidate均已消费。前提30项通过，result/codec原组253项通过加2个拒绝层修正项通过；综合review follow-up603 passed，重新构建的3.13 wheel消费者实测56cases/54controls/163origins通过。R1删除meaning引用返回typed PIE-B1008、R2显式meaning限field-only scan/projection已关闭；未扩public/default/native输入。

诊断6/6的历史失败均保留：负例键类型、已有declared非None条件、日期/Bool负例类型标注及review变量复用。最后变量仅重命名，最新typing由随后正式full静态门确认，不改写旧失败。后续只有depth-one、一次guarded完整3.13 equivalent、最终双runtime wheel/SDK/18文档完整比较，以及同tree seal/普通commit/FF push/自然15jobs/raw/native闭合。完成声明仍以这些证据为条件，不开始S08。
