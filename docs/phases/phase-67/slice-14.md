# Phase67 Slice14：真实 producer/result consumer integration

基线 `8bf641902f9adff429912a72c4b948dc6219869c` / tree
`e5396d6271614d818581d1696a2a823cb0aa62be`；自然push/main CI36348807929 attempt1成功。
P67-A03/A13/A16/A17只在本Slice冻结corpus闭合；S15 broader whole-result、S16审计仍未开始。

## Q1：corpus、责任与范围

两个target各自恰为G_emission_table_bag/bag、H_emission_query_bag/bag、
I_emission_table_empty/empty、J_emission_query_empty/empty，共八cells。消费现存recipe原source、
contract、TABLE/QUERY和literal policy，五列按display_text/record_id/active/amount/ratio。
保留Unicode/trailing spaces、BIG=9007199254740993、duplicate BAG、Bool/NULL、Decimal9,2
及finite Float bits；empty仍有五列。不得添加native查询或声称native Timestamp/UUID/Decimal65。

fixture路径从真实source重建live verification及ResultContract/Producer/Arrow bindings；
receipt路径只使用既有strict verifier已接受的同一原始receipt字节与真实observations.rows。
原source/contract hashes、artifact全文、request、column/protocol facts、context和lifecycle先核对。
明确声明的domain保持声明；protocol unknown nullability保持unknown，不由sample推断。
strict receipt verifier独占完整native manifest/inputs/lifecycle验收，新消费者不替代它。

每cell执行rows→ingest_rows→C-array；独立SDK typed input→S11→managed C-stream；
fresh finite input→encode_ipc→exact frame→open_ipc→incremental consumer→verify_ipc_completion。
owned为默认，所有grant/source/session独立且显式close；原extent/EOF/cleanup和delivery分开。
[0,1,0,3]等chunk布局是测试选择，不是live cursor观察；单一观察跨route保序保重，独立运行只比typed BAG。
四个TABLE cells在同一已安装环境的一个受限child中从实际移动后的project重建authority；
不传递或复活live handles，不增全历史process matrix。helper复制/加载范围闭合，production只来自wheel。

八新product groups与八实质report controls同步冻结为110/108；原102/100、SDK9和22份neutral全文保留。
fixture consumer不读数据库或future receipts。原15-job图中只在aggregate strict成功之后新增3.13
Arrow-extra replay环境及required sidecar：`phase67-consumer-integration-<run_id>-<attempt>.json`，
上限2MiB、位于pair-only native目录外，原27artifact均保留、总数28。单一test-only格式保留完整小观察、
原receipt引用、实际context/input closure/installed origins；无公开API/协议或live数据库适配器。
自然CI后本地两个最终extra环境各重放当前receipts一次，之后才清理；历史开发replay最多一次，独立标记。

冻结路径及用途（19路径，A3/M16/D0；总上限30、additions3、无删除）：

- `tests/_pietto_phase67_real_consumer_probe.py`：新增闭合fixture/replay消费者、单一sidecar checker、受限relocation child与S13安装复用。
- `tests/test_phase67_slice14_real_consumer_integration.py`：新增离线decoder/report/身份与负例主测试。
- `docs/phases/phase-67/slice-14.md`：新增八cell合同、Q与范围预算。
- `tests/_pietto_phase67_result_product_probe.py`：八组集成与八项损坏控制；110/108及实际helper input closure。
- `tests/test_phase67_slice9_finite_reader_completion.py`：current product denominator reader。
- `tests/test_phase67_slice10_arrow_ownership_interop.py`：current product denominator reader。
- `tests/test_phase67_slice11_result_ingress.py`：current product denominator reader。
- `tests/test_phase67_slice12_bounded_ipc.py`：current product denominator reader。
- `tests/test_active_phase_lifecycle.py`：唯一mutable lifecycle reader。
- `tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py`：两新增test helper/principal inventory。
- `.github/workflows/ci.yml`：existing aggregate严格receipt后额外隔离extra/replay/upload/identity；原15-job图保持。
- `docs/phases/phase-67/brief.md`：S14有限A03/A13/A16/A17边界。
- `docs/phases/phase-67/slices.md`：S14链接；S15 next。
- `docs/phases/phase-67/planning-notes.md`：Q1/Q2与独立验收。
- `docs/decisions.md`：用户批准的fixture与captured-native replay区分。
- `docs/development.md`：当前110/108及required sidecar28份闭合顺序。
- `docs/status.md`：conditional S14 terminal/S15 next。
- `docs/roadmap.md`：conditional S14 terminal/S15 next。
- `docs/references/engineering-lessons.md`：输入观察与独立oracle/receipt权威/完成边界。

production reserves为零：目前未发现需修的生产缺陷；不添加便利层。保护production与Phase66 helpers/
fixtures/oracles/observer/pins/receipt schema、S03/S12格式、S13依赖/lock/version、CLI/API/SQL/JSON、
workloads/topology及.agents。必需support缺口必须具体HOLD，不能换成更容易的case。

## 预算与完成条件

独立S14 ledger累计所有启动/失败/修正与宽阶段wall spans。diagnostics6、focused12、修正12、
review1/follow-up1、Q通常2最多3、full driver通常1最多2、开发package/acquisition3；每Python
installed product最多3（留final）、final SDK1、final core/extra各1同wheel；每Python bounded replay最多3，
其中历史开发最多1且current final必需。ordinary commit/push各1；实际failed CI child/push/delta各最多1；
native strict最多4通常3；orchestration-only及docs-only continuation各最多1，均在两次full上限内。
agents/detached/simultaneous downloads/localDB/full3.12/manualCI/release为0。外层driver与child均固定
已核验解释器。普通新pytest仅离线小decoder/report/authority checks，自动进入现有collection；不新增placement。

先验populated及empty真实binder/consumer，再扩八cells；一次完整review与单批causal repairs/一次follow-up、
Q2、depth-one后执行guarded3.13 full equivalent及final两runtime安装/SDK/product/22全文。
只有同tree普通sole-parent commit/FF push、自然exact-head push/main attempt1的15jobs/全部required
steps、28raw身份/消费者、fresh ordinary native三strict及CI3.13/local3.12/local3.13当前receipt replay
全部通过才为published。fixture执行、旧native查询、captured-native replay分开，不冒充新的查询或独立C认证。
最终Phase67 ACTIVE/N67=16，Slices01–14 COMPLETED/PUBLISHED，Slice15 NEXT/NOT STARTED、Slice16未开始；
Phase66/InterludeV/R1仍COMPLETED，package/CLI0.1.0。不开始S15或Phase68。

## Slice14 Q2：收敛候选

唯一author/Ponytail审查的完整finding集已关闭：receipt format/submission types与实际replay
解释器标签精确核对，删除独立SDK builder和relocated child的unused authority参数。
一次targeted follow-up通过全部当前Phase67/lifecycle/package/CI/doc readers、Ruff及两类Pyright。
3.13开发消费者110/108与唯一旧S13 receipt replay均通过；旧replay只归旧head/context。
当前19路径/A3/M16/D0，无production/native-helper/依赖/lock变化。最终depth-one、一次完整
coverage-equivalent、final同wheel双runtime4安装cells/SDK/product/22全文、ordinary publication、
自然15jobs及28raw/native/current-replay闭合仍为必需。精确tree与实测归外部ledger，不启动S15。
