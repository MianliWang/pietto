# Phase67 完成审计：三层证据、复盘与 Phase68 输入

S01–15已发布；S16 **ACTIVE / CANDIDATE**，Phase67 **ACTIVE — completion candidate pending S16 closure**，
Phase68 **NOT STARTED**。本审计的实质判断是：现有证据支持A01–A18在已授权范围内满足；
S16新回归、ordinary publication与fresh evidence仍待完成，不能以本矩阵文字替代。
生效只依[唯一闭环规则](slice-16.md#唯一闭环规则)，精确最终identity由该规则指定的外部record在观察后绑定。

## 权威与证据索引

规范采用[brief的18项原义](brief.md#三层完成验收与回归)。逐字对照`ff6b1b02`中的18行与S15基线相同；
S01-era `cffb59b2`还要求顺序/BAG/multiplicity、真实consumer、CPU边界、finite与executor分开，未被后来叙述免除。
S02补全Phase级要求是当时用户Appendix A授权，并修复S01局部src禁令与Phase目标的混写；不声称读取不存在的独立v4/v5文件。
实际收窄/扩展依据为[决策D67.01–31](../../decisions.md)及各已发布Slice合同的明确选择/续行；
S06共享参数扩展、S07meaning、S09caller extent、S12当前格式分别保留批准来源，不能由下游能力推定。

| 简称 | 实际owner / authoritative entry |
| --- | --- |
| RC | [project_result_contract](../../../src/pietto/_project/project_result_contract.py)：`build_result_contract`、`verify_result_contract`；selected verified root和完整exports |
| PB | [project_result_binding](../../../src/pietto/_project/project_result_binding.py)：`bind_producer`、`verify_producer_binding`；真实emission source-field realization |
| AR | [project_arrow_result](../../../src/pietto/_project/project_arrow_result.py)：`bind_arrow`、`verify_arrow_binding`、`build_owned_batch`、`verify_batch`；explicit field-bound policy |
| portable / pure / correspondence | [writer](../../../src/pietto/_project/project_result_contract_portable.py)、[pure](../../../src/pietto/_project/project_result_contract_pure_boundary.py)、[checker](../../../src/pietto/_project/project_result_contract_correspondence.py)；三种独立职责 |
| MEAN | [project_scalar_meaning](../../../src/pietto/_project/project_scalar_meaning.py)：`acquire_scalar_meaning`、`verify_scalar_meaning`；原source occurrence/closed law |
| RD | [project_result_reader](../../../src/pietto/_project/project_result_reader.py)：`open_finite_reader`、`verify_finite_completion`；原source/expectation/session与terminal |
| IX | [project_arrow_interop](../../../src/pietto/_project/project_arrow_interop.py)：`manage_batch`、`BorrowLease`、`BatchTransfer`、`manage_stream`、`import_batch`、`import_stream` |
| ING | [project_result_ingress](../../../src/pietto/_project/project_result_ingress.py)：`ingest_rows`、`ingest_batch`直接别名，`ingest_reader`组合原owner |
| IPC | [project_result_ipc](../../../src/pietto/_project/project_result_ipc.py)：`encode_ipc`、`open_ipc`、`verify_ipc_completion`；不另建一般completion体系 |
| 安装 | [package_smoke](../../../scripts/package_smoke.py)：wheel/sdist完整metadata、clean core/extra、真正extra解析和resolved origins |

行为证据来自[原product probe](../../../tests/_pietto_phase67_result_product_probe.py)、
[whole-result helper](../../../tests/_pietto_phase67_whole_result_probe.py)、
[real consumer/replay helper](../../../tests/_pietto_phase67_real_consumer_probe.py)与各Slice principal。
其中fixture执行、captured-native replay、descriptor-only和future execution是不同层，不能相互升级。
[新audit principal](../../../tests/test_phase67_slice16_completion_audit.py)只帮助发现引用/支持说明缺口，不生成完成证明。

最新既有执行锚 E15：head `437916ecf59d8873ef154a1e09f1e48e76884edf`、[CI36366896863](https://github.com/MianliWang/pietto/actions/runs/36366896863) push/main attempt1 success；
raw product `pietto-phase67-slice15-raw-result-product-36366896863-1-3.13.json`，artifact `10947881759`，SHA-256 `ecf08eb0b83289349782d5266c3afc01bf6a5ed6c181cddf6f1b18e3578dd336`。
当前metadata/长度/SHA已重绑定；local完整22文档与该raw全文相等。E15为历史执行和本次expected baseline，**不是S16运行证据**。
原S15 120/118、SDK9、local16832/0、CI每runtime16826+6既有shallow-history skips、product167/replay166origins、28raw均为实测，不固定未来pytest/origin数。
S16最终新执行、current receipts和effective verdict只归唯一闭环record；不得把历史绿灯搬过去。

## A01–A18 三层矩阵

每行的“支持”是已批准域的实质审计判断。最终PASS统一受S16闭环条件约束，未满足条件时Phase仍ACTIVE。
“原范围”逐项保留brief原义；正例与counterexample须能区分错误，存在类型/class或roundtrip相等单独不够。

| ID / 原范围 | 可观察：positive + discriminating negative | 已存在：owner / authoritative inputs | 已连接：caller → checks → consumer / terminal | 具体证据 / 授权与层 | 判定与精确限制 |
| --- | --- | --- | --- | --- | --- |
| P67-A01：target-neutral contract 保留 selected owner/root、全部按序 field occurrences、名称/位置和语义引用；不得由 target/driver/Arrow 推断身份 | 双target重命名/nullable输出仍按ordinal保留全部field；equal-looking foreign root、drop/swap/duplicate与port/provenance graft拒绝 | RC.build_result_contract / verify_result_contract；真实 ProjectSQLPlanVerification、selected_owner、active_output、全部 exports | 真实source→completed/IR/verified plan→RC→PB→AR→rows/C消费者；每层复验同一root和完整字段 | `postgres`, `mysql`, `ordered_fields`, `foreign_root`, `contract_live_grafts`, `whole_live_authority`；S02/S03、W04；所有按序occurrence而非label赢家；未从driver或Arrow推断身份 | 支持批准域；已验证有限结果边界；不认证外部producer诚实性。 |
| P67-A02：保留 declared/canonical scalar、value domain、nullability、nominal/refinement 身份；ResultShape 单一 scalar authority，结构可扩展但不引入 Struct/List/NestedRelation 成功域 | S03 descriptors/imported保留Money共享alias、Label refinement、全部grouped origin paths；missing member/foreign reference/coherent tail拒绝；S07 nominal meaning申请明确拒绝 | RC.ScalarShape / PB.verify_producer_binding；retained declared TypeExpr、canonical kind、effective NULL、type resolution | retained type/source facts→RC→独立portable/pure/correspondence；builtin scalar才继续PB/AR | `contract_documents`, `contract_live_grafts`, `meaning_premise`, `finite_codec`；S02/S03/S07；描述层正例不冒充nominal Arrow-value正例；S03批准descriptor域大于adapter域 | 支持批准域；七builtin scalar进入当前value链；nominal/refinement及其他描述不能自行开启新的producer成功域。 |
| P67-A03：producer binding 分开核对 exact representation/domain/nullability/provenance；同一语义根可有多个合法 binding，失配在转换前拒绝 | neutral_reuse在同一root连接两个合法realization；width/family/domain/protocol/label失配、producer+Arrow协调篡改在conversion前拒绝 | PB.bind_producer / verify_producer_binding；exact RC、emission artifact/request、source_field realization及ordered observations | inspect_project_sql_emission→verify_result_contract→每个column/export/field→PB→AR→实际consumer | `neutral_reuse`, `producer_mismatch`, `coordinated_mutation`, `text_binding`, `decimal_bindings`, `integration_producer_correspondence`；D67.01/09/13–21；S02–07、S14真实protocol事实与supplied声明分开 | 支持批准域；同根多binding由不同合法realization证明；分别编译PG/MySQL不伪装同一对象；不含driver/execution authority。 |
| P67-A04：Arrow binding/schema 显式、可独立核验；仅有声明且 lossless 的 adaptation，不能让 widening 修复 producer lie | domain-total Int narrowing/widening、string/large_string、低p Decimal128/256、UUID/binary16保值而schema有别；moved/foreign/repeated及全域不fit请求拒绝 | AR.bind_arrow / verify_arrow_binding；PB与exact field-bound Integer/Text/Decimal/UUID/label requests | PB先复验→显式requests→schema→owned/native校验→C-array与IPC两边界 | `integer_adaptation`, `text_requests`, `decimal_requests`, `uuid_policy`, `whole_fields_adaptation`；D67.13/16/18/21/22；W03另比较合法重新编译投影与原mapping下同名同type换值 | 支持批准域；不以empty/allNULL/小样本证明适配合法；无隐式cast或修复producer lie。 |
| P67-A05：独立 canonical private bytes 与 bounded pure decoder；pure consistency 不等于 live runtime correspondence；拒绝 resurrection、stale/graft 与 missing tail | 22完整canonical文档；pure-valid coherent tail/order/NULL替换被原runtime拒绝；禁用writer时独立checker仍工作，coherent writer缺陷被检出 | portable.export_result_contract；pure.decode_contract；correspondence.verify_contract_correspondence / verify_bound_export | live contract→bounded export→纯view；显式supplied fresh equivalent root可correspond；原bound export/producer/session不能迁移 | `contract_documents`, `contract_pure`, `contract_substitutions`, `contract_identity`, `contract_independence`, `whole_live_authority`；D67.02/11/12；S03 test_independent_checker_detects_coherent_writer_defect；W04 | 支持批准域；pure一致性、fresh supplied correspondence与原live身份三种主张分开；不序列化/复活runtime。 |
| P67-A06：有限类型 ledger：Int16/32/64、Bool、finite Float/signed zero、Unicode、Decimal128/256、timestamp(us，无时区转换)、UUID；只宣称实际支持域 | 七logical/十二physical、13列mixed；BIG、Float±0 bits、Unicode、Decimalcoeff/scale、civil ticks、UUIDbytes；越域/nonfinite/coercion与域内替值分别拒绝 | PB/AR scalar mapping；shared semantic Decimal参数fact；MEAN civil_ticks与closed laws | 真实builtin source/projection→已验证参数/meaning→PB→explicit AR→行/独立SDK/C/IPC消费者 | `integer_widths`, `scalar_mixed`, `text_values`, `decimal_values`, `decimal_context`, `timestamp_values`, `uuid_values`, `finite_mixed_values`；D67.13–21；S04–08完整value/refusal组、W01/W10；S06明确批准38→65 | 支持批准域；shared p1..65/s0..p；producer s≤min(p,30)；Decimal±0统一系数0，Float±0保留；不扩算术/nested。 |
| P67-A07：默认 string、显式 large_string；collation/padding 不成为 Arrow equality authority；canonical UUID extension 与显式 binary16 备选；时间/UUID meaning 先在上游闭合 | 默认string及显式large_string、默认canonical UUID及显式binary16经C/IPC保真；缺meaning、fake extension、unit/tz/request移位均拒绝 | MEAN.acquire_scalar_meaning / verify_scalar_meaning；AR.TextOffsetWidthRequest / UUIDRepresentationRequest | source-port完整inventory→explicit同一个meaning bundle给emission/RC→PB→AR→C/IPC；不由metadata赋权 | `text_binding`, `text_requests`, `uuid_policy`, `meaning_premise`, `ipc_uuid_representation`；D67.07/15/16/19–21；S07批准civil区间；text/uuid policy及ipc_uuid_representation | 支持批准域；collation/padding非Arrow equality；civil无timezone转换，1000-01-01至9999-12-31 23:59:59.499999；PG UUID与MY bytes严格分离。 |
| P67-A08：empty/all-null 仍有 explicit types；实际 NULL 遵守合同；carrier duplicate labels 按 ordinal 保留，不取消语言 PIE-S2305 | typed zero/allNULL/firstNULL、同type同label异value完整保留；实际nonnullable NULL拒绝；原mapping列交换仅由独立值oracle识别；语言重复export仍PIE-S2305 | AR.ArrowFieldLabelRequest / build_owned_batch / verify_batch；logical与producer label保持原层 | real mixed/allnullable roots→explicit schema/labels→rows及native→C/IPC；按ordinal消费 | `finite_empty`, `finite_all_null`, `carrier_labels`, `carrier_label_refusals`, `whole_fields_adaptation`；D67.22/23；finite_*、carrier_*、W01/W03/W10；两target12physical choices | 支持批准域；carrier重复名只改presentation，不扩语言成功域；empty/null不能授权额外类型或意义。 |
| P67-A09：RecordBatch/finite reader 保值、NULL、multiplicity、已有 order；覆盖 rechunk/empty batches，不强制 Table/read_all/combine_chunks 或整结果复制 | whole/uneven/empty-interleaved保留同一输入sequence/NULL/重数；BAG置换保typed Counter、丢重复行不保；desc→合法asc文档不correspond原ORDER | RD.CheckedFiniteReader；RC.ordering；correspondence._Correspondence.ordering；IX.ManagedStream | 每个输入batch→原checker→checked pull→managed/IPC incremental；retained ORDER独立导出/核对 | `reader_rechunk`, `reader_correspondence`, `whole_rechunk_bag_order`, `contract_order_substitution`；S01原“顺序/BAG”、S02 per-input sequence、S09批准conditional reader、S15 W02明确descriptor-only ORDER层 | 支持批准域；PASS仅为transport保序及已有ORDER描述保留；八native cells均BAG/empty，不宣称ordered native/ordered result-producer执行，亦不增加SQL排序成功域。 |
| P67-A10：batch、finite completion、executor success 分开；empty 不是 EOF、prefix 未闭合、IPC EOF 不证明查询完成；attester/denominator 明确 | count相等但未EOF、prefix、empty、early/late/cleanup/control错误不能完成；source已完成但consumer/writer失败仍无delivery/IPC成功；foreign/copied receipt拒绝 | RD.open_finite_reader / verify_finite_completion；IX.ManagedStream；IPC.verify_ipc_completion | 原expected_rows/session→逐批观察→normalEOF+exactrows+成功source close→原receipt；下游cleanup和frame claims另核验 | `reader_extent`, `reader_terminal`, `reader_identity`, `c_stream_terminal`, `ipc_completion`, `whole_finite_completion`；D67.04/24/25；reader_*、c_stream_terminal、integration_terminal_failures、W05/W07 | 支持批准域；caller extent是条件性分母；无COUNT/可信cursor rowcount/unknown-cardinality/executor成功证明。Phase68设计这些义务。 |
| P67-A11：owned/borrowed/transferred 的 lifetime、non-mutation、release 和 memory domain 明确；CPU 成功、unsupported devices 拒绝 | owned隔离真实mutable backing且关闭后值存活；borrow实际pin owner至释放但alias mutation可改值；spent/copied/grafted grants与非CPU/device-only hooks拒绝 | IX.ManagedBatch / BorrowLease / BatchTransfer / ManagedStream；exact source/binding/owner和non_mutation=True | source先验证→独立buffers copy或明确lease→实际C handle→foreign consumer→显式session close/consumer release | `ownership_copy`, `ownership_borrow`, `ownership_transfer`, `c_protocol_lifetime`, `cpu_protocol_resources`, `whole_lifetime_delivery`；D67.08/27/28；S10 SDK-backed机制、ownership_*、c_protocol_lifetime、W06 | 支持批准域；transfer不等于buffer独占；holding owner不保证nonmutation；foreign close不等于source完成；无unsafe pointer/sandbox或精确native callback次数承诺。 |
| P67-A12：positional rows 与 Arrow-native ingress 共享 checker；不从首行猜类型、不重建 candidate 掩盖 validation failure | rows与独立typed SDK carrier保值；错误schema/authority/device/extent在接受前拒绝且不pull/close；接受后claim失败保留primary并清理一次 | ING.ingest_rows=IX.build_managed_batch；ingest_batch=IX.manage_batch；ingest_reader直接组合RD/IX | 明确入口→原scalar/schema/resources checker→owned/leased batch或fresh raw reader接受→managed delivery | `ingress_rows`, `ingress_batch`, `ingress_reader`, `ingress_refusals`, `ingress_ownership`, `ingress_independence`；D67.29；S11 ingress_*及test_accepted_composition_preserves_primary_and_closes_once；W01/W05 | 支持批准域；无dict/name合列、dtype推断、重建candidate、Table/read_all或一般generator入口；raw reader须fresh/exclusive且caller履行接受前责任。 |
| P67-A13：CPU C Data/PyCapsule/C Stream 有真实 consumer/lifetime checks；PyArrow-backed 通过不等于独立 C 实现认证 | 真实pa.schema/record_batch/RecordBatchReader.from_stream消费者及close后retained数组；requested-schema失配在spent/pull前拒绝；handle不可重放 | IX.__arrow_c_schema__/__arrow_c_array__/__arrow_c_stream__；import_batch/import_stream | live binding→single grant→CPU C Data/C Stream→真实SDK consumer→显式lifetime/terminal核验 | `c_schema_array`, `c_schema_requests`, `c_stream_values`, `c_protocol_lifetime`, `integration_rows_consumer`, `integration_arrow_consumer`；S10十组、S14三route、W01/W06；SDK9仍独立必需 | 支持批准域；仅PyArrow-backed CPU成功域，不是独立C实现认证；Phase86设备、Phase90 Rust/PyO3。 |
| P67-A14：bounded private IPC 验证有效/畸形/truncation/completeness/metadata forgery；IPC bytes 不是语义身份 | 100-byte/96MiB frame正常增量消费；length/digest/truncation/metadata/schema拒绝；complete-message prefix与wrong batches不能完成；coherent同count变值可transport通过却不保原值 | IPC.encode_ipc / open_ipc / verify_ipc_completion；live binding+caller extent+原RD receipt | S11接受→S10实际C批→bounded writer→成功源及writer/delivery cleanup→frame；open先cheap frame再SDK→原managed reader→同一receipt | `ipc_roundtrip`, `ipc_boundary_truncation`, `ipc_completion`, `ipc_metadata`, `ipc_corruption`, `whole_ipc_integrity`, `whole_routes_values`；S12当前合同、S15 W01/W05/W07；empty nonzero-offset修复在原validation/admission后且批数/charge/descriptors保持 | 支持批准域；hash和message metadata不认证source/executor；无public/cross-runtime canonical IPC承诺；旧80MiB候选不验证当前格式。 |
| P67-A15：field count、batch rows/bytes、batch count/total bytes、contract bytes、IPC bytes 有明确 ceiling，超限以小 fixtures 拒绝 | 小exact/one-over与同时invalid的check-order见证；retained先于copy/validate；重分批同值但sum(max(A,R))成本可增；codec1024 fields不混成batch64 | AR.BatchLimits与_field_labels；RD.FiniteReaderLimits；pure.DocumentLimits；IPC.IPCLimits | 原carrier dimensions/schema/R→full/domain→每批max(A,R)→managed delivery charge→独立IPC长度；各limit只收紧 | `contract_limits`, `finite_resources`, `reader_limits`, `cpu_protocol_resources`, `ipc_limits`, `whole_resource_boundaries`；D67.10/11/16/22/26；contract_limits、finite_resources、reader_limits、cpu_protocol_resources、ipc_limits、W08 | 支持批准域；所有当前上限见资源表；临时source/copy/writer/decoder可重叠，非RSS上限；upstream单次分配/阻塞不受此sandbox保证。 |
| P67-A16：compiler core Arrow-free；optional install path 与 private API 隔离实测，无额外 release/range promise 或公共泄漏 | same-wheel四fresh core/extra cells；core无Arrow且真实missing-dependency拒绝；extra解析精确25.0.1；错误metadata/version/path/symlink前缀被拒绝 | scripts/package_smoke.py；pyproject arrow selector；lazy private owners与installed origins | build/inspect wheel+sdist→clean core/extra解析安装→CLI/lazy origin检查→SDK9/product→CI required reports | `no_reconstruction`, `integration_relocated_process`, `integration_report_integrity`；D67.05/30；S13 metadata/隔离回归；S14 relocated consumer；S15实际四cell记录 | 支持批准域；Linux x86-64/CPython3.12/3.13；requires-python>=3.12不是更广Arrow证书；private result API，package0.1.0，无release。 |
| P67-A17：real producer/result consumers、independent negatives、whole-result metamorphics；data correspondence 不等于 SQL 正确性或 runtime obligations 完成 | 真实source/bindings→三route与relocated child；原native receipt rows重放；域内替值/±0/换列/重排/丢重复/NULL、实际copy/writer缺陷与report damage均可区分 | product/whole-result/real-consumer probes及原CI required consumers；独立input、observation、literal oracle | preserved positive及negative→required120/118；完整native strict→当前eight-cell replay→sidecar与local两runtime checker | `integration_producer_correspondence`, `integration_rows_consumer`, `integration_arrow_consumer`, `integration_ipc_consumer`, `integration_report_integrity`, `whole_routes_values`, `whole_rechunk_bag_order`, `whole_fields_adaptation`, `whole_live_authority`, `whole_finite_completion`, `whole_lifetime_delivery`, `whole_ipc_integrity`, `whole_resource_boundaries`, `whole_historical_contracts`, `whole_oracle_discrimination`；D67.31；S14五类×两target×G/H BAG/I/J empty；S15 W01–W10七类installed fixtures | 支持批准域；fixture、captured-native replay、descriptor、future execution分层；不把五类replay扩大成七类native证据，不以expected表作输入。 |
| P67-A18：保留原 semantic/compiler/package assurance、真实 skips 与解释器域；closeout 对账 numbered/unnumbered 工作、成本/readiness/incidents，提炼3–7条教训供下一 Phase 消费 | S15 full16832/0与CI每runtime16826+既有6skip；15个发布链及范围逐项对账；S16须新full/四cells/120118/22文档/28raw/native/replay，任何缺项不得激活完成 | 原compiler/semantic/package gates、唯一lifecycle reader；本审计/实际Git历史/每Slice ledger | 固定N67=16→S08 midpoint→S01–15实际闭环→本三层audit/六lesson/handoff→唯一条件规则→未来观察到的S16终态 | 完整regression与本审计记录；S01原phase流程与本S16 dispatch；历史表/成本表/incident记录；S16执行事实只写外部closure record | 支持批准域；实质审计支持在批准域内完成，S16回归/发布/清理仍PENDING；不推断性能提升或Phase68完成。 |

PB中的`protocol_nullable=None`保留protocol未知，不覆盖原logical nullability；不能由non-NULL样本推断non-null。
RD checked reader本身不升级ownership，它返回经过检查的supplied batch；owned/leased delivery由IX/ING承担。

## 支持域与不能替代的证据

七个logical families：Int、Bool、Float、Text、Decimal、Timestamp、UUID。十二physical choices为
int16/int32/int64、bool、float64、string/large_string、decimal128/decimal256、timestamp(us)、canonical UUID/binary16。
13列mixed额外保留第二个同type同label异value的Int16 occurrence，不把列数当类型数。

| 边界 | 当前已验证域与前提 | 明确不支持 / 证据限制 |
| --- | --- | --- |
| Scalar/producer | builtin direct field-only scan/projection、PG/MY各自exact carrier；确定logical NULL与原realization | nominal/refinement/alias/import描述完整保留，但不据此宣称新的nominal Arrow或SQL stage成功；具体Enum程序拒绝不推广为全Enum结论 |
| Int / Bool / Float | signed16/32/64；PG exact bool、MY exact int0/1；finite binary64保留±0 bits | whole domain不fit不能凭empty/小sample适配；非finite/coercion拒绝 |
| Text | exact Unicode scalar/UTF-8、default string、field-bound large_string；pg_text拒绝NUL，MY supplied row可含合法NUL | collation/padding只作producer事实核验，无新Arrow比较/排序语义，无新native NUL认证 |
| Decimal | shared p1..65、s0..p；producer s≤min(p,30)；默认p≤38的128、p39..65的256，低p显式256；exact coefficient，无context rounding | 不恢复旧p39拒绝，也不把language scale许可当producer支持；正负Decimal零同系数0，不同于Float signed-zero |
| Timestamp / UUID | 显式同root meaning；civil1000-01-01至9999-12-31 23:59:59.499999、早期999999us合法；UUID标准128bits | 默认missing meaning仍拒绝；无timezone转换；PG exact UUID/MY immutable16bytes；fake extension/name metadata不授权；端点不是pinned server最大值实测 |
| ORDER / BAG | 每次consumer保留其supplied序列；BAG跨独立结果以typed Counter保重；descriptor方向/表达式/uses与原authority对应 | W02 ORDER标明descriptor-only；desc→asc可pure-valid但不correspond原root。原八native cells没有ordered SQL claim；遵守S15不得扩producer成功域的授权边界 |
| Finite / lifetime | 原expected_rows先于消费；normalEOF+exactextent+successfulclose；source、managed delivery与IPC分别完成；默认owned、显式lease | exactcount不是EOF；empty不是EOF；foreign close不等于source完成；borrow保活不阻止alias mutation；不能防任意host-memory改写 |
| IPC | current100-byte header / 96MiB、V5/uncompressed、原22neutral文档digest与payload digest；message metadata不赋权 | frame/EOF/hash不证明source/SQL/DB完整性或执行成功；无public/canonical跨runtime IPC保证 |
| Installation / integration | Linux x86-64、CPython3.12/3.13、PyArrow25.0.1；unique`pietto[arrow]`、四clean同wheelcells | requires-python>=3.12不是更宽Arrow支持证书；private API、version0.1.0、无release；七类fixture不冒充五类captured-native proof |

### S15 empty-offset修复的独立复核

原失败是pinned SDK经C-import的零行非零offset批次写出损坏IPC。S15真实复现并在批准的IPC reserve中修复；
本S16不重做SDK campaign。源码显示归零empty offset发生在S11接受和S09/S10原carrier验证/计费之后、SDK writer之前，
仍写一个batch，不compact有值carrier、不绕过retained-limit。E15 W01 PG values的source receipt实际为：
layout `[0,1,0,3,0]`，5 batches/4 rows/6 pulls，五批R各528，A分别12/175/12/480/12，
`sum(max(A,R))=2640`；原descriptors的ordinal/row_start/rows完整，source COMPLETE后IPC consumer正常完成。
W08用独立算式以及同时超retained/值invalid的反例检查顺序；S16 final会重新执行原W01–W10。

## 独立资源界面

| owner | hard ceiling | 算法 / 边界 |
| --- | --- | --- |
| AR.BatchLimits | 64 fields / 4096 rows / 8MiB | 每batch A含numeric保守8byte、validity、Textoffset/UTF8、Decimal16/32、UUID16；另计每次referenced buffer R，不dedup |
| AR field labels | 每项1024 UTF-8 bytes / 总65536 | explicit完整field-bound请求；默认源标签不追溯引入新限制；独立于payload计费 |
| RD.FiniteReaderLimits | 1024 batches / 1,048,576 rows / 64MiB | 累计sum(max(A,R))，empty/repeated backing也计；最多max_batches+1次source pull判EOF |
| IX managed delivery | 原batch/session ceilings | 每chunk max(Csource,Cdelivery)，再累计；source+copy临时referenced bytes另记，不以nbytes/RSS代替 |
| pure.DocumentLimits | 4MiB bytes（含LF）、depth48、65536 values、8192 records、16384 references、text131072bytes/项、total_text2MiB、1024 fields | 当前owner原值；export/decode独立bounded preflight；caller不能提升hard cap；codec1024≠batch64 |
| IPC.IPCLimits | 全frame96MiB，header100bytes包含在内 | cheap framing/length/extent/digest先于SDK；writer增长前检查；不代表decoder/upstream一次分配或阻塞的sandbox |

## 实际 Phase 工作与发布链

以下由S16外部`history-reconciliation.json`一次生成：当前Git first-parent完整15条，逐条head/tree/sole-parent
与保存的terminal run/jobs相同，均push/main/attempt1、15jobs成功；实际Git delta均为最终批准freeze/amendment的子集。
15个已发布numbered Slices对应15个ordinary commits，未发现额外已发布repair commit；未发布candidate/full/continuation另计，不能冒作Slice或commit。
S16本行只记录角色与待观察状态，不编造未来SHA/run。

| Slice / role | 实际head / tree / sole parent | natural CI | actual A/M/D / approved paths | disposition |
| --- | --- | --- | --- | --- |
| 01 CI governance + SDK readiness | `cffb59b29961b4a75552979093d0a18f369cf7df` / `dbf77f6ed1097a728134059544e0aad6e497bc09` / `e0d02247f1f6410c1715ef22eb3c6e254726a962` | [36099028120](https://github.com/MianliWang/pietto/actions/runs/36099028120) | 13/14/0 / 27；无scope escape | COMPLETED / PUBLISHED |
| 02 Int vertical | `ff6b1b0233f11aab400905a5952bcf8ca0e60e82` / `eb77c04176da6f3bb15979026b22d7defe0dbbb2` / `cffb59b29961b4a75552979093d0a18f369cf7df` | [36176037555](https://github.com/MianliWang/pietto/actions/runs/36176037555) | 6/13/0 / 19；无scope escape | COMPLETED / PUBLISHED |
| 03 neutral portable/live boundary | `be51fef66655e68d7fb450649a5b2061115016d1` / `12b7a4e64346d35c3b158ca9bd82b64c46562fd6` / `ff6b1b0233f11aab400905a5952bcf8ca0e60e82` | [36197167166](https://github.com/MianliWang/pietto/actions/runs/36197167166) | 5/11/0 / 17；无scope escape | COMPLETED / PUBLISHED |
| 04 numeric Bool Float | `76fef176a9c85eb907146866b3d2c60801a1dce1` / `e3688dde9a283a450b4b19f2000790c8d177c03a` / `be51fef66655e68d7fb450649a5b2061115016d1` | [36224628578](https://github.com/MianliWang/pietto/actions/runs/36224628578) | 2/13/0 / 15；无scope escape | COMPLETED / PUBLISHED |
| 05 Text Unicode | `8a97e089c130775e327cdbbebbbfee179fe8be80` / `48be1901a103f910faa7e883dead2068adde0876` / `76fef176a9c85eb907146866b3d2c60801a1dce1` | [36228301379](https://github.com/MianliWang/pietto/actions/runs/36228301379) | 2/14/0 / 20；无scope escape | COMPLETED / PUBLISHED |
| 06 Decimal approved premise expansion | `7c1a944d94d6b21d5031679b2497ef58da5f9115` / `76dc1c6bca53513d6c070b578844a0e241d2003d` / `8a97e089c130775e327cdbbebbbfee179fe8be80` | [36259274452](https://github.com/MianliWang/pietto/actions/runs/36259274452) | 2/21/0 / 29；无scope escape | COMPLETED / PUBLISHED |
| 07 explicit meaning Timestamp UUID | `4b28725829251a10c43a3e597322bf4684a3ea9b` / `faf378685e8345b73c287762f1e684c7bcae0b00` / `7c1a944d94d6b21d5031679b2497ef58da5f9115` | [36267007145](https://github.com/MianliWang/pietto/actions/runs/36267007145) | 3/24/0 / 36；无scope escape | COMPLETED / PUBLISHED |
| 08 finite integration + midpoint | `f2a7d75f38e7770db7af3d0b3375f8d9954256a5` / `ea4466801bff9847c3b688ddaafa9875d8336eac` / `4b28725829251a10c43a3e597322bf4684a3ea9b` | [36279999513](https://github.com/MianliWang/pietto/actions/runs/36279999513) | 2/12/0 / 14；无scope escape | COMPLETED / PUBLISHED |
| 09 finite reader | `eb7fbcc94ea872210380b64bd1e445f799aed7d0` / `6e2f4b7ec5e603a0ea395ba39a2263e4541b4da7` / `f2a7d75f38e7770db7af3d0b3375f8d9954256a5` | [36299384053](https://github.com/MianliWang/pietto/actions/runs/36299384053) | 3/12/0 / 16；无scope escape | COMPLETED / PUBLISHED |
| 10 ownership/C protocols | `f7a4ed89ef628da4da9fb309a23e40d0b67aa282` / `3fe9cc4bb2394db0ccf6b337adf4cd8dc4b056d3` / `eb7fbcc94ea872210380b64bd1e445f799aed7d0` | [36306958433](https://github.com/MianliWang/pietto/actions/runs/36306958433) | 3/14/0 / 17；无scope escape | COMPLETED / PUBLISHED |
| 11 rows/native ingress | `1d19c64c88b4e01074ade5985e556780c848b91e` / `08395a6d0d7c1a281bef64c0de844a36cc273776` / `f7a4ed89ef628da4da9fb309a23e40d0b67aa282` | [36312935619](https://github.com/MianliWang/pietto/actions/runs/36312935619) | 3/14/0 / 19；无scope escape | COMPLETED / PUBLISHED |
| 12 current bounded IPC | `8f5333fdf526c3211c98135e7a4cce660864dcc8` / `4dd7c58e276e84e18faeeb2bd8368b2e2423ad79` / `1d19c64c88b4e01074ade5985e556780c848b91e` | [36343560204](https://github.com/MianliWang/pietto/actions/runs/36343560204) | 3/15/0 / 18；无scope escape | COMPLETED / PUBLISHED |
| 13 optional extra/isolation | `8bf641902f9adff429912a72c4b948dc6219869c` / `e5396d6271614d818581d1696a2a823cb0aa62be` / `8f5333fdf526c3211c98135e7a4cce660864dcc8` | [36348807929](https://github.com/MianliWang/pietto/actions/runs/36348807929) | 2/20/0 / 22；无scope escape | COMPLETED / PUBLISHED |
| 14 real consumer/replay | `31156eaf22341e0b16b400d496982c7ff51d610c` / `994f85f4cae08f9e399a663d6dce617be80afc81` / `8bf641902f9adff429912a72c4b948dc6219869c` | [36356999376](https://github.com/MianliWang/pietto/actions/runs/36356999376) | 3/16/0 / 19；无scope escape | COMPLETED / PUBLISHED |
| 15 whole-result laws/readiness | `437916ecf59d8873ef154a1e09f1e48e76884edf` / `6992f1e25abddb9f4bfdddd72e9120596df2da01` / `31156eaf22341e0b16b400d496982c7ff51d610c` | [36366896863](https://github.com/MianliWang/pietto/actions/runs/36366896863) | 3/17/0 / 27；无scope escape | COMPLETED / PUBLISHED |
| 16 completion audit/regression/retrospective/handoff | 包含本audit的未来ordinary commit；exact identity待外部record | 待自然运行 | Q1为15条，A≤3/D0；最终actual待seal | ACTIVE / CANDIDATE |

### 非编号工作、amendment与已解决事件

- S01是同一Slice内联合CI governance/SDK readiness，不拆成额外编号；Phase66、恰三Slice的Interlude V和单独R1均是先前已完成工作。
- S03原reader遗漏触发HOLD，明确增加一个typing reader；非必要workflow接线撤回。后来native普通文件准备在同一已发布head上续行，corrections6→7明确只增一组，native总4含一次旧失败与三次成功；最终v2/后续v3报告闭合，不重新开启其已解决历史。
- S06旧shared precision≤38是当时合法规则；外层65不证明可达。真实38/39失败后明确批准同一shared rule扩到65及八个额外owner/readers，language scale与producer scale仍分开；原HOLD保留。
- S07明确meaning、civil端点及field-only opt-in，portable CUTOFF仅隔离既有wire不传输的runtime identity。初始full的文档diagnostic spelling失败后批准corrections8→12及一次严格docs continuation；10/12为实际累计，不追认早期8上限已允许所有修正。
- S08合法empty absent buffer缺陷被真实consumer发现并在原seam修复；midpoint明确后半段completion/lifetime/IPC/installation义务不能提前置绿。
- S09 caller extent与同步pull、limits经明确决定后落地；不以未来COUNT或cursorrowcount假设隐藏分母。S10每runtime product最大4含small premise，来自其原dispatch，不擅自沿用其他Slice的3上限；scope-amendment只改已预留reader用途。
- S12经历实际只读Git/network环境HOLD、local-only候选及depth-one前提，再收到实质不同current contract。旧`c1bb0f895b4c76c3772443617a38972790ce3173`是计算但未写入Git objects的候选tree标识（原ledger明确记录），不是一个发布commit；旧32+56-byte/80MiB full只验证旧合同。明确续行后使用current100-byte/96MiB，review/follow-up各2、Q4、full2、每runtime product5/SDK2均按该次授权累计，correction上限再明确8→12；最终9/12。当前对象库无旧tree不被误报为发布链断裂，原inventory/diff/full保留。
- S13全部已通过stage之后，错误外层解释器因缺pytest中断；保持同tree/unchanged inputs，只补未执行步骤。原full driver失败1057.769s和恢复214.449s分列，两个orchestration starts不等于重复执行全部heavy gates。
- S14原八cell fixture与captured-native replay、required sidecar是同一Slice；一次historical开发replay仍归旧head。末尾timing recovery把修正累计更新为9/12，原8快照保留但不再作最终值。
- S15在已批准IPC reserve修复真实empty-offset问题；required120/118、原七类fixture与五类replay保持。1次失败installed启动、captured目录前提错误、未执行的premature-status审批拒绝及安全conditional替代均保留；三个review原因在一批修复中分别计费，最终6/12。

未发现授权范围逃逸；这来自实际delta对照各次批准清单及上述用途核对，不是仅看changed-path总数。
无额外已发布编号；S16不创建Slice17，也不把这些准备/续行改写为“全部第一次成功”。

## 成本、计费与可比性

下表数字为保存的各Slice记录，非记忆估计。窗口可能含HOLD、协调或未分类时间；命令parent/stages、CI wall/runner sum、
观察/transfer是重叠视角，**不相加为Phase总耗时**。UNKNOWN不填0；测试增长不是生产率指标，不推断CPU/model time或speedup。
详细逐命令、installed starts/durations与source哈希保存在同目录history-reconciliation，原记录只读。

| Slice | recorded window / basis | full/continuation parent seconds | CI wall / runner sum seconds | transfer seconds | correction / 当时批准ceiling |
| --- | --- | --- | --- | --- | --- |
| 01 | UNKNOWN（未覆盖完整Slice窗口） | 826.439 | 687.000 / 3842.000 | UNKNOWN | 3/6 |
| 02 | UNKNOWN（未覆盖完整Slice窗口） | 818.341 | 566.000 / 3704.000 | UNKNOWN | 2/6 |
| 03 | 2026-09-25T21:28:16.167009+00:00 → 2026-09-26T05:28:13.770270+00:00；28797.603260993958s recorded；最终native续行另8.389s，完整Slice elapsed UNKNOWN | 792.215 | 709.000 / 3839.000 | 287.838 | 7/7（明确6→7） |
| 04 | 2026-09-26T06:00:57.098620+00:00 → 2026-09-26T06:59:04.310223+00:00；3487.211603164673s recorded | 826.882 | 604.000 / 3721.000 | 206.713 | 2/8 |
| 05 | 2026-09-26T07:23:34.905274+00:00 → 2026-09-26T08:14:25.582700+00:00；3050.677426099777s recorded | 848.205 | 759.000 / 3903.000 | 188.253 | 4/8 |
| 06 | 2026-09-26T08:28:28.349848+00:00 → 2026-09-26T17:48:14.496948+00:00；33586.14709997177s recorded | 867.022 | 699.000 / 4130.000 | 188.807 | 7/8 |
| 07 | 2026-09-26T18:09:49.032073+00:00 → 2026-09-26T19:59:36.557982+00:00；6587.525908946991s recorded | 817.687 + docs 174.037（不同窗口） | 662.000 / 4207.000 | 214.167 | 10/12 |
| 08 | 2026-09-26T22:59:13.120432+00:00 → 2026-09-26T23:51:11.573916+00:00；3118.453484s recorded | 831.854 | 522.000 / 3933.000 | 194.435 | 6/8 |
| 09 | 2026-09-27T05:35:59.238445+00:00 → 2026-09-27T06:28:18.763000+00:00；3139.524555s recorded | 898.955 | 610.000 / 3811.000 | 178.044 | 5/8 |
| 10 | 2026-09-27T07:28:20.077392+00:00 → 2026-09-27T08:57:04.447519+00:00；5324.370127s recorded | 952.954 | 705.000 / 3701.000 | 192.735 | 8/8 |
| 11 | 2026-09-27T09:46:29.820249+00:00 → 2026-09-27T10:45:47.543959+00:00；3557.72371s recorded | 1033.045 | 565.000 / 4022.000 | 181.939 | 6/8 |
| 12 | 原local 2026-09-27T11:47:15.564511+00:00→2026-09-27T12:31:41.043002+00:00；current/holds分段记录，非一个执行窗口 | 旧1066.976 + current1250.209（不同合同） | 711.000 / 4520.000 | 216.704 | 9/12（明确8→12） |
| 13 | 2026-09-27T19:46:52.921402+00:00 → 2026-09-27T20:54:26.643035+00:00；ledger window 4053.722s | 1057.769（中断） + 214.449（仅补缺项） | 740.000 / 4411.000 | 197.184 | 9/12 |
| 14 | 2026-09-27T21:27:51.643613+00:00 → 2026-09-27T23:12:07.951256+00:00；ledger window 6256.308s | 1348.538 | 690.000 / 3942.000 | 204.504 | 9/12 |
| 15 | 2026-09-28T00:39:37.741413+00:00 → 2026-09-28T01:58:58.610623+00:00；ledger window 4760.869s | 1392.291 | 699.000 / 4339.000 | 205.343 | 6/12 |
| 16 | 本次recorded起点2026-09-28T02:16:50.873963+00:00；结束待观察 | 待新final | 待新natural CI | 待当前raw | ≤12，累计ledger |

S01还单列CI-governance、Arrow-readiness与joint-validation command wall；其每runtime SDK计数3包含两local和一hosted，
不能与后来仅local product口径直接相加。S03 cost v2仍标workflow_open，native续行delta另存；不伪造终态全窗口。
S07 ledger full1与另一个docs continuation窗口分开；S12两full验证不同合同；S13两driver starts只有缺项继续。
S14该ledger window止于原终态，随后timing-recovery补记不在此窗口内；其reporting duration未单独测量，仍为UNKNOWN，9/12计数不回退。
S14/S15 prefetch分别与hosted CI重叠，当前记录保留该交集；任何同层总计须明确覆盖哪些窗口，本文不提供无完整覆盖的总Phase elapsed。

基线closeout health只读取S15当前workflow报告一次：`INSUFFICIENT_EVIDENCE`、`current_screen=WATCH`、comparable_samples=0。
实际signals含SHARD_IMBALANCE_WATCH（3.12）、SHARD_IMBALANCE_REVIEW（3.13）、LONG_INDIVISIBLE_NODE、
FEWER_UNITS_THAN_WORKERS；repeat_confirmations和repeated_cost_codes为空。test-set/runtime/runner不同的历史不作同域性能证明。
这些是advisory，不是本Phase完整性失败，也不授权新performance interlude/repartition/benchmark；当前hard checks成功。
S16自己的health随必需自然CI在外部终态记录实际signals及可比性，不能提前写green或推断加速。

## Retrospective 与下一次必需动作

计划的16行角色完整保持：启动joint readiness→private thin vertical→codec→有限scalar→midpoint→reader→ownership→ingress→IPC→extra→real integration→whole laws→本closeout。
实际必要变化均有准确owner和授权：S06可达参数前提、S07明确meaning、S12实质contract替换、S13外层driver恢复、S15既有域修复。
没有以少测试/少字段/报告PASS旗标代替承诺，没有因history不足启动维护，也没有将五类native replay写成七类native认证。
六条耐久行动集中在[工程教训P67-L01–L06](../../references/engineering-lessons.md#phase67-完成审计的六条耐久教训)；
后续FULL phase-initiation必须先筛选适用项，说明消费方式与仍然存在的限制。

## Phase68 及后续 handoff

| 可消费边界 / actual API | supplied authority / 域 | ownership / terminal义务 | evidence层 / 剩余限制 / next owner |
| --- | --- | --- | --- |
| RC `build_result_contract` / `verify_result_contract` | verified plan、selected owner、完整fields，单一scalar authority | 不从portable bytes重建live root；保留所有ordered occurrences | S02/S03/W04；可供Phase68规划，execution authority仍需独立设计 |
| PB `bind_producer` / AR `bind_arrow` | 原emission artifact及exact observations、explicit requests、必要MEAN bundle；七类当前scalar | producer事实先于适配、schema严格、原值oracle独立 | installed fixtures；native replay只覆盖五类；实际driver adapter属于Phase68 |
| ING `ingest_rows` / `ingest_batch` / `ingest_reader` | positional rows或explicit CPU batch；fresh exclusive raw reader | 接受前caller责任，接受后一次cleanup；默认owned或完整lease承诺 | S11/W01；无named/dtype inference或通用dataframe adapter，Phase80负责更高层适配 |
| IX `BorrowLease` / `manage_batch` / `manage_stream` / C protocols | exact source/binding/owner/nonmutation、single-use grants | 实际owner pin到consumer释放；alias mutation仍caller负责；explicit session close | S10/S14/W06，PyArrow-backed CPU；Phase86设备/DLPack，Phase90 Rust/PyO3 |
| RD `open_finite_reader` / `verify_finite_completion` | 可信度由caller提供的exact extent、original session/limits | normalEOF+exactrows+source close；input与delivery分开 | S09/W05；unknown cardinality、可信extent/finalization与backpressure由Phase68设计 |
| IPC `encode_ipc` / `open_ipc` / `verify_ipc_completion` | 原live binding、caller extent、100-byte/96MiB frame | framing先验、成功writer/decoder/delivery cleanup、返回原RD receipt | S12/W07；不是执行/来源认证；Phase82 public format/API freeze、Phase84 stronger trust/signing |
| `pietto[arrow]` / package smoke | same candidate wheel、clean prefixes；Linuxx86-64/CPython3.12/3.13/25.0.1 | core Arrow-free，版本/metadata/origins共同验证 | S13安装+S14relocation/replay；Phase69 public entrypoint/alpha/release选择，Phase83 stable1.0 |
| strict native receipts→real-consumer replay | current head/run/attempt、exact originalbytes、原recipe/artifact/protocol/lifecycle | strict先于replay；相同八cell三route、typed BAG/fields/terminals；不比较路径或偶然独立BAG顺序 | S14；重放既有观察不是新DB查询，不能代替Phase68连接/statement/execution authority |

Phase68必须另行设计execution/connection/statement authority、实际driver adapters、transactions、runtime errors、
cancellation/backpressure、可信extent/finalization与unknown cardinality。不得hidden COUNT、假定可靠cursor rowcount、
由首批推分母或把IPC hash当executor证据。Ready for Phase68 planning不等于这些义务已完成。

精确后续owner保持：Phase69 public alpha/entrypoint/release；Phase71 nested semantics；Phase80 higher-level Python/dataframe adapters；
Phase82 public format/API freeze；Phase83 stable1.0；Phase84 stronger trust/signing；Phase86 non-CPU/device/DLPack；Phase90 Rust/PyO3；
Phase91–97仅tentative/owner-only，不增加承诺。Phase68独立FULL phase-initiation须先消费本audit与适用lessons，再由自己的dispatch激活实现。
本S16不执行该规划gate、不建Phase68文件、不启动Slice1；所有后续阶段均保持未开始。
