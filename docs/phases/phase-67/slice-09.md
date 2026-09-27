# Phase67 Slice09：有界 finite reader、声明 extent 与正常 finalization

三项产品选择已由用户明确一并批准并dispatch。基线 `f2a7d75f38e7770db7af3d0b3375f8d9954256a5`，tree `ea4466801bff9847c3b688ddaafa9875d8336eac`，sole parent `4b28725829251a10c43a3e597322bf4684a3ea9b`；natural CI36279999513/push/main/attempt1 success。core沿用Arrow-free CPython3.13.13，未同步/重建。S08 health WATCH/INSUFFICIENT_EVIDENCE、comparable0只作advisory。

## 已批准选择与完成主张

P67-A09/A10及A15 stream部分：显式调用方在消费前声明完整exact expected_rows，接受fresh/exclusive real CPU RecordBatchReader，逐批同步pull、保留batch边界（包括empty）及全部positional序列。完成必须随后观察normal EOF、exact extent且source close成功；不从EOF或已消费prefix反推分母。不是认证调用方/原值/数据库完整性/SQL执行，也不要求未来executor预先COUNT。外部推进reader、并发读/close及消费期间外部buffer mutation属未验证的调用前提。

采用一个private owner `project_result_reader.py`。接口为 `open_finite_reader(binding, source, *, expected_rows=None, limits=FiniteReaderLimits())`，返回 `CheckedFiniteReader`，有schema/read_next_batch/iteration/close/context-manager及不drain的completion inspection；不提供read_all、Table、cast、raw-reader或protocol bypass。source类型精确RecordBatchReader，schema/type/labels/metadata、meaning/binding和limits在接受前检查。构造失败由caller保留handle；成功构造后由session负责一次close。

`FiniteResultExpectation` frozen/slots/eq=False，保留exact binding、exact source弱引用、unique session对象、声明和limits。SDK25.0.1实测支持weakref、schema无预读、EOF和close后已返回owned batch可用。弱引用仅为内部身份记录，公开接口不暴露raw reader；terminal释放active source强引用。原expectation对象及primitive声明/limits、producer/schema/request tuple与request field/value的独立捕获用于拒绝同会话coherent改写，不能仅重建自身receipt比较。

## 状态、错误和receipt

| state | 行为 |
| --- | --- |
| OPEN | 已接受schema/声明，逐批验证；completion=None，inspection不pull |
| COMPLETE | 观察normal EOF、exact rows、close成功后终态；重复read StopIteration，无新pull/close |
| CLOSED_INCOMPLETE | 显式提前close（即使已达到声明或声明0）；不drain、不发receipt；再读READER_CLOSED |
| FAILED | source/validation/extent/resource/identity/cleanup失败；保留primary和cleanup异常；再读READER_FAILED，无retry |

StopIteration只在source.read_next_batch的try范围解释为EOF；validator、descriptor/finalization或close中的StopIteration是失败。普通source异常为READER_SOURCE并保留cause；existing scalar/binding ResultError保持原category；unexpected validation/finalization为READER_VALIDATION；不吞KeyboardInterrupt/SystemExit。combined primary/cleanup均保留，控制流BaseException需要时以BaseExceptionGroup传播。close幂等且失败也不重试。context manager不压制body异常。

稳定private categories：READER_DECLARATION（absent/unknown/非exact-int/negative/超总rows声明）、READER_SOURCE（非真实reader及read失败）、READER_EXTENT（short/extra）、READER_IDENTITY（expectation/session/receipt/policy失配）、READER_VALIDATION（非source嵌套异常）、READER_CLEANUP、READER_CLOSED、READER_FAILED；沿用LIMIT与scalar/schema层category，不新增compiler diagnostics。先检查原authority，source取回后先cheap header、prospective count/rows，再buffer/base与scalar；offending batch不yield。

`BatchDescriptor`仅ordinal/row_start/rows/logical_bytes/retained_bytes；原始observations为独立primitive tuple，最多1024，不保存旧batches。`FiniteCompletion`绑定原expectation/session/source identity/binding、实际descriptor tuple和计数及terminal observation。`verify_finite_completion(reader, expectation, completion)`独立核对actual completed session与issued record identity、完整descriptor cardinality/ordinals/contiguity/sums/limits、原声明及live binding；不调用receipt builder、不读source。改count、tail、foreign/grafted/copy-other-session/deleted fields与coordinated counter改写相对未变originals必须拒绝。仅普通in-process identity保证，不承诺抵抗任意恶意Python内存改写。

## 资源与共用checker

保留batch1..64fields/4096rows/8MiB及label1024bytes/项、65536total、S03独立codec limits。`FiniteReaderLimits`包含batch limits和max_batches=1024、max_total_rows=1048576、max_total_bytes=64MiB；所有值exact nonnegative int，Bool/超hard ceiling拒绝，0可用于小fixture。

每批 A 为S08 logical allowance（含actual UTF8），R为所有referenced buffers保守总和，无dedup；C=max(A,R)，累计sum(C)，重复引用/empty也计费。不能A+R或batch.nbytes。共用Arrow `_verify_schema`，`_checked_batch_usage`只做原来一次full/scalar遍历并返回(A,R)，`verify_batch`保持返回None。remaining bytes收紧BatchLimits以在full/scalar前拒绝base/R超限，Text按剩余量增量检查。计数只在整批成功后更新。达到max_batches允许额外一次pull判EOF；返回任何batch均LIMIT，因此pull≤max_batches+1。

该界面不能限制单次upstream pull内部的分配/阻塞；不增加timeout、async、executor或backpressure。不同合法rechunk保值但charge/批数可变，不承诺不同layout在相同tight limits下都被接受。保留BAG/order事实但不把source提供序列升级为SQL排序保证。

## 有界manifest与独立证据

复用S08真实双target13字段mixed/nullable roots、七类scalar/12physical choices、重复label和显式widths；原64groups/62controls/9SDK/22完整documents保持，新增以下10组形成74/72。22份neutral bytes不加入extent/session；最终两local及两CI报告完整比较。

- `reader_values`：真实reader值/labels/NULL/ticks/bytes全链
- `reader_empty_null`：zero batches/typed empty/absent buffers/all-NULL/first-null
- `reader_extent`：frozen denominator、short/extra/invalid totals
- `reader_terminal`：exact-count后late read error、trailing empty与EOF
- `reader_lifecycle`：close once、early close、cleanup与combined failure、retained owned values
- `reader_limits`：小界限、累计max(A,R)、empty pull cap、retained-before-invalid
- `reader_rechunk`：unsplit/uneven/empty-interleaved同原值与layout costs
- `reader_identity`：foreign/deleted/grafted expectation/receipt/session/policy与counter损坏
- `reader_correspondence`：等count替换/swap/permute/duplicate replacement与injected builder独立oracle
- `reader_incremental`：无预读、无drain/whole materialization，bounded descriptor transcript

每新组一个实质report-damage control，改变实际值/计数/状态/close/read/identity/resource记录，不仅删除case或改PASS。source read失败由真实from_batches cooperative iterable引发；无法自然构造的close/validator异常用围绕实际production操作的明确test injection，单独标明。原始expected总数先于候选读取且从固定原值独立给定。

## Q1 write freeze、直接读者与预算

以下16路径，3新增、无删除；S08 principal为明确shared-checker reserve，其余均实际owner。新增reader不被旧emission/neutral schema图遍历，CUTOFF无修改理由；PRODUCTS加入reader使实际installed origin检查生效，input_closure已覆盖全部src；required ci_validation.check_product调用扩展verify_report，无需新CI步骤。typing inventory230/505，actual doc scanners为test_phase12_order_by/test_phase12_limit的canonical diagnostic检查，sole lifecycle reader保持test_active_phase_lifecycle。

```text
src/pietto/_project/project_result_reader.py
tests/test_phase67_slice9_finite_reader_completion.py
docs/phases/phase-67/slice-09.md
src/pietto/_project/project_arrow_result.py
tests/_pietto_phase67_result_product_probe.py
tests/test_phase67_slice8_finite_scalar_carriers.py
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

预算diagnostics6/focused12/corrections8/full默认1最多2/review1/followup1/Q≤3通常2/env2/product每runtime3且预留final/SDK final各1/commit1/push1/failed-CI child与push/delta各1/native≤4通常3/docs-only partial≤1严格附带条件。agents/detached/concurrent downloads/manual CI/local DB/full3.12/extra matrix均0。重任务guard on、top-level串行≤4workers，uv明确绑定core；无core sync或Arrow安装。一个S09 ledger跨中断保留累计starts，所有failure/preparation mistake记录。

Q1成立：批准的caller extent、pull/lifecycle与limits可在既有seam实现；SDK前提诊断1通过。S08教训直接成为首批empty/positional/reader-tail witnesses。Q2用于收敛候选，不重做midpoint。一次author/Ponytail完整finding集及单批repair、一次targeted followup后，depth-one、一次3.13 full-equivalent（5 static、独立U、4 fresh serial partitions、coverage/managed/health、generated/golden/package、双runtime exact-wheel产品/SDK）绑定同tree。文档scanner/current readers在full前执行。批准的机械docs-only continuation严格按dispatch，绝不泛化复用。

成功后一次ordinary sole-parent commit/FF push、自然exact-head attempt1全15jobs、当前raw inventory字节/ID/digest/context与实际consumers、fresh ordinary native pair预检和PG/MY/aggregate data-only strict全部闭合。当前receipt33MiB上限不变，新增source通过真实input closure认证；不称新DB reader/SQL执行证据。保留证据后仅清理owned roots。

S10 ownership/non-mutation/C protocols、S11一般ingress、S12 IPC completion envelope、S13extra、S14real producer、S15whole-result、S16closeout仍必需；Phase68执行/事务/取消/backpressure，69alpha、83stable、90Rust不改变。最终Phase67 ACTIVE/N67=16，Slices01–09 COMPLETED/PUBLISHED，Slice10 NEXT/NOT STARTED、11–16未开始；package/CLI0.1.0。在此停止。

参考：[RecordBatchReader](https://arrow.apache.org/docs/python/generated/pyarrow.RecordBatchReader.html)提供固定schema、pull/EOF/close；[C Stream](https://arrow.apache.org/docs/format/CStreamInterface.html)区分stream与returned-array lifetime。只作SDK机制依据，不替代本次实际Pietto证据；不开放C协议。

## 实现前提与成本校准

真实SDK前提诊断通过；初次focused58 passed/2.42s，typing准备错误修正后通过，installed3.13首轮74groups/72controls/164origins，命令44.081s。complete canonical corpus仍22份。S08保留历史full831.854s、CI execution522s/runner sum3933s/raw transfer194.435s，不作为本Slice速度比较。

新增reader只增加native package-members/wheel-members各一个path+digest entry（单entry JSON112bytes，旧Arrow path每receipt两处；原digest宽度不变），不加native fixture/SQL document。S08 PG/MY分别34418132/34424193 bytes，至33MiB仍余184876/178815 bytes；这是发布前结构headroom核对，实际新head仍必须取得并核验fresh receipts，不能用估计代替闭合。

## Q2 收敛与最终验收边界

一次完整主作者correctness/Ponytail审查冻结R1 cleanup控制异常去重、R2 session内producer observation/protocol-nullability捕获、R3小界限与coherent新声明证据；同一批修复后只作一次targeted follow-up。三项批准选择与16行路线保持，无新产品决定；reader记录仍不进入neutral codec。unknown-source真实性、外部并发/先前消费、buffer mutation及upstream阻塞的限制不减。完整final候选验证、普通publication及current raw/native闭合的实际事实归外部ledger；完成前均为candidate，不启动S10。
