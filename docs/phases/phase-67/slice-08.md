# Phase67 Slice08：有限 scalar 集成、typed empty/all-NULL 与 carrier labels

基线 `4b28725829251a10c43a3e597322bf4684a3ea9b`，tree `faf378685e8345b73c287762f1e684c7bcae0b00`，sole parent `7c1a944d94d6b21d5031679b2497ef58da5f9115`；自然 CI36267007145/push/main/attempt1 success。core 为既有 Arrow-free CPython3.13.13。独立 S08 ledger 不借用 S07 starts；保留未跟踪 `.agents/`。

## Q1、接口与身份

完整读取 Arrow owner 和 producer 精确标签检查、真实 source/renamed projection fixture、meaning acquisition、报告末端及 typing/lifecycle 读者。沿用真实 builtin field-only scan/projection，取得同根显式 meaning；不修改 upstream fields 构造可达域。现有 private Arrow records 不进入 neutral codec/CUTOFF；新增测试使 typing inventory 从229/503变为229/504。

新增 frozen/slots/eq=False `ArrowFieldLabelRequest(field: ResultField, label: str)`；在 `ArrowResultBinding` 末尾追加 `field_labels`，`bind_arrow` 新增同名 keyword-only argument，默认 `None`。显式 tuple 必须完整覆盖 ordinal，None entry 保留 logical label；每项绑定 exact retained field。重复 label text 合法，foreign/reordered/wrong-kind identity 不合法。显式标签 exact nonempty str、Unicode scalar、无 NUL；每项≤1024 UTF-8 bytes、总计≤65536 bytes，先廉价检查再编码，无截断/normalization；默认源标签不追溯新增限制。private拒绝使用 ARROW_LABELS；删除存储字段不冒充API omission。

semantic label、producer observation label、Arrow carrier label分属原有身份/观测/显式presentation；producer精确label检查及语言 PIE-S2305 不变。build/check共享policy核验，candidate/schema metadata不能倒推政策。相同schema无法识别同类型同名column交换；独立原始输入positional oracle负责拒绝，无name lookup。

## 有限支持与 witness matrix

仅 Int exact signed16/32/64，Bool PG bool/MY int01，finite float64/IEEE signed-zero，Text string/explicit large_string，Decimal128/256，civil timestamp(us,tz=None)，canonical UUID/explicit binary16。Decimal参数1≤p≤65、0≤s≤p，producer s≤min(p,30)，固定scale无rounding。Timestamp inclusive1000-01-01至9999-12-31 23:59:59.499999，较早microsecond999999合法。UUID全部标准big-endian128bits。

每target一个13列混合source和一个all-nullable source：12种physical choices加一个独立Int16 field；全部为真实renamed projection。第0/5/12列显式同名，覆盖异type和同type异value、非相邻重复及nullable companions。原56product/54damage/9SDK保留，新增以下8组，总64/62；旧18份完整canonical documents保持，新增两个target mixed及nullable根共4份，总22。

| group | 真实观察与独立拒绝 |
| --- | --- |
| finite_mixed_values | 双target、13列完整types/labels/nullability/values；整数、IEEE bits、UTF8、Decimal coefficients、ticks、UUID bytes、validity独立预期 |
| finite_empty | complete zero rows，nonnullable合法；schema/meaning/request仍检查，zero fields拒绝 |
| finite_all_null | 13列all-NULL、one row、first-row-NULL/later-values；actual nonnullable NULL/coercion拒绝 |
| carrier_labels | default保留、显式重复名的populated/empty/all-NULL，ordinal身份与values不丢失 |
| carrier_label_refusals | exact identity/arity/type/Unicode/byte bounds/deletion，no-policy/changed schema、producer forged label、metadata及PIE-S2305 |
| finite_resources | exact与少1byte的mixed总计费、explicit宽Text/Decimal、empty offsets、NULL retained charge、非零value/validity offsets、retained-limit先于invalid value |
| finite_correspondence | 同type同名swap、domain-valid替换、NULL变更、lost duplicate/prefix及injected builder拒绝；batch PASS不等于finite completion |
| finite_codec | 22份完整documents，label/width/rows不改同一neutral bytes；pure不复活runtime identity，meaning/field graft仍拒绝 |

每新组一个实质report corruption，覆盖非首列value、ordinal、label、NULL、mixed成本；真实verify_report和CI required check_product消费。没有只靠PASS flags或name-keyed oracle。

## 资源与检查顺序

同时保留64fields/4096rows/8MiB、caller只能收紧及S03独立codec limits。每列ceil(r/8)+8r用于Int/Bool/Float/Timestamp；UUID与Decimal128用16r，Decimal256用32r；Text用ceil(r/8)+offset_bytes*(r+1)+non-NULL UTF8。按实际显式width相加，不dedup，label metadata另计。零行Text仍有offset allowance，NULL固定列不免计费。

row ingress先dimensions/base及exact value/UTF8 preflight再allocation；supplied先schema/dimensions、referenced-buffer总和、full validation、logical/domain。实际SDK接受的empty/absent buffer在既有seam处理；不建立通用import层。Timestamp先读ticks判域，不先溢出datetime。

## 精确路径与预算

以下14路径为write set，新增principal/本计划2条、无删除；只有实际受影响的reader才修改。额外路径先做具体scope amendment，28path/3addition上限不授权任意路径。

```text
src/pietto/_project/project_arrow_result.py
tests/_pietto_phase67_result_product_probe.py
tests/test_phase67_slice8_finite_scalar_carriers.py
docs/phases/phase-67/slice-08.md
tests/test_active_phase_lifecycle.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
docs/phases/phase-67/brief.md
docs/phases/phase-67/slices.md
docs/phases/phase-67/planning-notes.md
docs/decisions.md
docs/references/engineering-lessons.md
docs/development.md
docs/status.md
docs/roadmap.md
```

producer/neutral/meaning/codec production owners保持read-only。protected语法/semantics/IR/SQL/public API、workflow/CI拓扑、native fixtures/pins、dependencies/version/host/agents不修改。fixture/consumer继续单一现有probe，不新增helper。

预算：targetless diagnostics6，focused pytest12，causal corrections8，full默认1最多2，author/Ponytail review1及targeted followup1，Q≤3通常2，external env2，product每runtime≤3，final SDK每runtime1，initial commit/push各1，failed-CI child/push/delta各1，native strict≤4通常3，严格条件下docs-only partial≤1。agents/detached/manual CI/local DB/full3.12/extra matrix均0。guard on、重任务top-level串行≤4workers。所有uv绑定已核验core；解释器域不缩小。

## Midpoint 初始 S/H/L/K/Q

S：A02/A06/A08在owned batch集成，现有identity/meaning仍上游owned。H：已接受S06参数和S07意义不重开；S09 attester/denominator及batch/total budgets、S10 lifetime/non-mutation/release、S12 metadata/completion、S13 packaging均在其首次接口前决定。L：固定16行和依赖不变，S09 reader、S10 protocols、S11 ingress、S12 IPC、S13 extra、S14 real producer、S15 whole-result/Phase68 readiness、S16 closeout必需。K：S07 incomplete full与174.037s docs continuation分开，只作历史成本，不作regression百分比；当前health advisory不授权维护。Q：当前无新产品决定；最终三层A01–A18状态及converged成本在Q2补齐。

先运行real fixture/label与actual doc scanners/current lifecycle，再进行author/Ponytail完整finding集、单批因果修复和targeted followup。final full包含最终midpoint/lifecycle文本：5静态gate、独立U、4 fresh serial partitions与coverage/health、generated/golden/package、双runtime exact-wheel product/SDK/完整bytes。depth-one reader/import检查计focused。只有附件严格docs-only条件可复用未变完整footprint；不泛化。

完整本地closure后seal、sole-parent ordinary commit/FF push、natural exact-head15jobs、byte-preserving raw inventory及current consumers、fresh native普通文件预检与PG/MY/aggregate data-only strict串行闭合。成功后Phase67 ACTIVE/N67=16，Slices01–08 COMPLETED/PUBLISHED，Slice09 NEXT/NOT STARTED、10–16 NOT STARTED。Phase66/Interlude V/R1仍完成、package/CLI0.1.0；Phase68执行、69alpha、83stable、90Rust各归原owner，不启动S09。

## Midpoint 三层状态与最终评估

下表“可观察／存在／连接”只描述S08收敛候选；publication仍需同tree完整local、自然CI与raw闭合。跨Slice义务不提前标整项完成。

| 验收 | 可观察 | 已存在 | 已连接／剩余准确owner |
| --- | --- | --- | --- |
| P67-A01 | 完整有序字段、foreign/graft负例 | neutral runtime contract | source→contract→batch已连接；S15–16最终闭合 |
| P67-A02 | 七类scalar的declared/canonical/domain/nullability | 单一ScalarShape及identity | 当前owned有限范围完整；nested归Phase71 |
| P67-A03 | exact storage/domain/protocol/label拒绝 | 独立producer verifier | 私有双target supplied-row已连接；真实producer ingress与联合保证S14–15 |
| P67-A04 | 默认与显式physical/label schema检查 | private Arrow binding | owned builder与supplied checker已连接；非自动修复producer |
| P67-A05 | 旧18+新4完整文档、pure/live替换拒绝 | bounded codec与runtime correspondence | 两runtime/CI消费者必需；whole-result S15 |
| P67-A06 | 12physical choices、signed-zero/Unicode/coefficients/ticks/bytes | 全部七类finite ledger | 当前合法owned范围完整；未扩大builtins/nominals |
| P67-A07 | string/large_string、UUID/binary16 | field-bound policies、S07意义 | batch完整；协议S10与IPC S12尚欠 |
| P67-A08 | typed empty/all-NULL、first-null、非相邻同名异值 | explicit schema/label与NULL检查 | 当前owned batch完整；语言重复export仍PIE-S2305 |
| P67-A09 | 单batch顺序与duplicates、prefix oracle | bounded owned batch | finite reader/rechunk S09，ingress S11，whole-result S15未完成 |
| P67-A10 | legal prefix仍可batch PASS | 尚无completion attester | S09决定denominator/finalization；S12绑定IPC；Phase68 execution success |
| P67-A11 | owned mutation/CPU、NULL storage | owned materialization | borrowed/transferred/non-mutation/release S10，设备Phase86 |
| P67-A12 | positional row与supplied batch同checker | private checked seam | general Arrow-native ingress S11未完成 |
| P67-A13 | 原SDK capsule/lifetime探针 | SDK实验基础 | product CPU C Data/C Stream S10，真实consumer S14–15未完成 |
| P67-A14 | 原SDK IPC实验不等于产品完成 | 无产品IPC层 | S12 bounded metadata/completion，S15 assurance |
| P67-A15 | fields/rows/bytes及codec小上限拒绝 | batch/codec独立资源界面 | batch count/total与protocol/IPC S09–12仍必需 |
| P67-A16 | core Arrow-free和隔离wheel consumers | private optional import seam | public optional extra S13、安装集成S14未完成 |
| P67-A17 | supplied-row原输入oracle与保留native manifest | 局部negative/metamorphic | real producer S14、whole-result S15；SQL/executor不由Arrow证明 |
| P67-A18 | 现有compiler/package与精确report集合 | required CI/readers/成本ledger | 每Slice保持；S16 closeout/retrospective仍必需 |

S：目标保持accepted owned finite domain，label只为presentation，不以all-NULL开放Date/Bytes/Json/Any/nested或无meaning。H：S06参数/S07意义已接受；S09启动前明确谁attest有限完成、完整denominator、batch/total bounds；S10接口前明确lifetime/non-mutation/release责任；S12设计前明确metadata与completion绑定；S13安装面前明确extra包装。均无需为完成S08提前决定。

L：保留16行和依赖，S09→S10→S11→S12→S13→S14→S15→S16顺序/义务不缩减，无S17。Phase68接连接/凭据/执行/事务/runtime failure/cancel/backpressure；69alpha、83stable1.0、90Rust保持原owner。

K：S07实测initial INCOMPLETE full817.687s、docs continuation174.037s为两个窗口；自然CI execution662s、runner sum4207s、observation671.342s、raw transfer214.167s分列，不相加为一个执行耗时。S08当前real source focused35项1.92s，首次3.13产品19.039s失败于合法empty buffer，修复后3.12完整产品27.054s通过64/62；两次typing失败7.038/7.034s，修正后8.038s通过。当前有限病例和guarded单次full预算可容纳S08；后半段completion/lifetime/IPC仍高风险，应沿原owner前置决策与真实consumer。历史health不足/提示仅advisory，不开维护。final full、双runtime、CI和transfer实测归本Slice外部报告，不在预执行文本声称已通过。

Q：路线保留；当前没有阻碍S08的新product/trust选择。S06可达域教训由真实13字段source先验证；S07完整字段/optional-slot删除、field-only opt-in保持，文档scanner提前运行。typed empty采用SDK实际接受布局，same-type同名值历史由独立oracle检测。后续未完成项和最晚决定点均已列明，无隐含免除。Q2与主作者review/followup/final验证的实际事实绑定外部ledger，所有历史失败保留。
