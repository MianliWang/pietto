# Phase65 Slice14 Portable Plan Boundary And Minimal Process Integration v1

本交付沿用 D65.03/.05/.07–.12、N16 与 Slice10–13 的原产品边界。基线 commit
`079ed2ecfbcf71e9adc11dec898a1a61120ae7f5`，tree
`d227daf60175a6100be6dca2d07023b75b53b240`，parent
`a0e235f9c858187a7b5f25e47c1413e61a8899fe`；自然 CI `34750296114`
为 push/main/attempt1/success。写前已核对 clean worktree/index、同步 refs、Git 操作
和进程。Slice14 账本独立保存于 `~/.local/state/pietto/evidence/phase65-slice14/`。

## 三种不同的保证

Runtime encoder 消费 exact current ProjectSQLPlanVerification，保留 completed、IR、
selected owner、literal policy 和 fixed envelope。报告与 source map 通过已有只读产品
取得并在边界核验；显式 supplied assessment 必须属于相同 request。编码不选择 target、
不 compose profile、不取得 provider，不重新证明语义或运行 renderer。

Runtime correspondence 独立核对每个编码字段、原对象关联和完整 collection。
Pure consistency 只检查新 schema 内的记录与关系；它不调用 runtime encoder，也不重建
AST/semantic/IR/ProjectSQLPlan 对象。调用者可以构造另一个内部一致的文档；pure OK
不证明原 source/proof authenticity、database conformance、安装或运行时履行。

## 实现前的有限字段矩阵

前置 `runtime-field-audit.json` 使用十二个已通过的真实 source/completed/VERIFIED IR/
plan fixtures 和两种 literal policies，记录 110 类实际运行时记录的完整字段。静态
variant 定义补足窗口、ORDER/proof/type 等可选分支。以下矩阵指定字段的 transport
含义；新 schema 中的闭合 per-kind field definitions 是精确字段顺序和类型的 authority。
不是 dataclasses.asdict/repr dump，也不复制整个 compiler semantic root graph。

| 原对象/字段 | 文档记录与必要关系 | 缺失、顺序与检查 |
| --- | --- | --- |
| plan.scope、selected owner、policy、envelope | 一个 observation root；selected definition、显式 policy、slot/value inventories | root 唯一；旧 runtime request、bindings-only/unavailable 拒绝；文档不携带 opaque scope/address |
| bindings.definitions / source descriptors | definition 与 source；原 declaration/source identity、connector AST、ordered exports | declaration 与使用分开；source spelling/locator 保持为数据；source family 不代表 connection |
| input_uses / boundaries / symbols | 每个 ordered use、producer/consumer、port map、boundary 和 scope-local symbol | external producer 必需；内部 predecessor 需要正面的同 scope/order 关系；重复 uses 不合并 |
| source/input/canonical/stage/result ports | 独立 ref domains 与 ordered original/terminal correspondences；原 type/nullability/source links | 不能靠同名、同类型或总数替代 port 对应；helper 不能进入 visible exports |
| blocks / expression sites / expressions / operands | SELECT stage 与真实 SET body 分开；原作用域、AST、ValueType、ordered operand links | unary/binary/comparison/NULL/between/call/result-reference 的闭合字段；不折叠负号或重新推断类型 |
| LET / filter / JOIN / matching | 原值与 predicate、SQL TRUE-only、orientation、input role/nulling、relationship equalities | 完整 pre-match 与 post-match boundaries；SEMI/ANTI 右侧 membership 保持 |
| aggregation / keys / calls / projections | GROUPED/GLOBAL、empty input、argument/result maps、原 type 与 effect evidence | 不把 COUNT(*) 与 nullable-field count 合并；保持原 group/NULL/comparison 条件 |
| aggregate risk / single-match / proof | 原 risk variant、scope/unit/state、diagnostic、premises、root/child branches | PROVED/LEGAL_UNPROVED 与 enforcement 分开；没有 fulfilled tag；不能删除必要 proof branch |
| windows / uses / arguments / policy / projection | selected/hidden、authored/effective、partition/order、frame/modifier/named links、原 IR policy/effect | QUALIFY 使用的 hidden computation 必需；scope/backreference 不能冒充 executable edge |
| DISTINCT / quotient / ORDER / hidden requirement / LIMIT | visible-only quotient、exact type/equivalence、两种 ORDER 分支、STRICT-FD 原 premises、静态 bound | pending hidden value 不是 visible port；LIMIT0 不消除 membership 或义务 |
| SET body / operand / input / column | operation/quantifier/multiplicity、source-order fold、positional type/value/member inputs、canonical outputs | EXCEPT 右侧只是不贡献 value，仍必须保留 membership；重复 producer 的 uses 各自声明 |
| logical type / field equivalence / Decimal sources | 原类型种类、nominal declaration、type parents、precision/scale 和 provenance links | 不把 alias 重新猜成 builtin；若上游已解析则保留该结果与原 declaration/parameters；父关系必需 |
| literal site / slot / value / bind use | policy、disposition/reason、original decoded tagged value、source span、expression occurrence | absent/empty/zero 不互换；Bool/Int/Float 不混用；绑定叶必须拥有 slot/use/value |
| report entries / links / summary | 全部 demand occurrence、family/subkind、subject/context/origin、composite subrequirements、原 proof/risk links | 每个原 demand 恰一条；不能缩小分母或删除未映射 family 来得到 positive |
| source map sources/sites/entries/associations/legacy positions/links | logical source、原 AST membership/container/declaration、authored/effective roles、generated reason、typed endpoints | 一基半开 parser 字符坐标；legacy partial/unavailable 显式；合法 explanatory backreferences 保留 |
| optional assessment / request/profile/query/results/aspects | 显式 presence、原 target/profile releases、facts/occurrences、query uses、raw lookup、applicability 与 residuals | omission 与 negative/unresolved 分开；profile partial；target mismatch/conflict 不能变成 complete support |

Record declarations 用文档内 typed refs；运行时 exact object membership 只用于 encoder/
correspondence 的 invocation-local index，不进入文档。原序列和 multiplicity 是顺序
authority，不按 label/value/span 排序去重。标准化字段顺序由 schema 决定；不同原对象
即使内容相同仍保留其 occurrence，不同运行时构造可以得到相同 observable bytes。

## 新格式、输入与资源边界

独立 marker 为 `pietto.phase65-sql-plan-observation.v1`。旧 Phase61–64 markers、records
和未变输入 bytes 不改动。文档采用一个固定字段顺序的 root 与闭合 typed record table；
references、字段类型、required/optional、枚举值和跨记录角色均由新 schema 定义。

外层只允许 `format`、`records`。每条记录只允许 `kind`、`ref`、`fields`；
`ref` 为 `[domain, position]`，`fields` 为按 schema 顺序排列的 `[name, value]`
数组。记录标签采用独立 snake_case 词汇，如 `project_sql_plan`、
`project_sql_plan_ref`、`capability_fact`，不会据标签查找或构造运行时类。
运行时 adapter 只按闭合类型表与显式字段规则取值；没有 dataclass 自动展开。
IR/semantic 根在必要的 owner、source occurrence、operator 与证据处截断，
不复制 analysis roots、mutable indexes、解析输入文件或整个 compiler object graph。

首条 `observation` 记录关联 plan、report、source_map 与可选 assessment。
各 domain 的声明位置从零连续分配，完整记录序列遵守从该 root 出发、按字段与
原集合顺序的广度优先分配。不同对象不按相同值合并，重复引用保持重复；
report 与显式 assessment 可持有同一请求的两个独立 report 实例。

值统一为 `[tag, data]`。`absent` 使用 null，`boolean` 使用 JSON Boolean，
`integer` 使用十进制字符串，`float_hex` 使用规范有限十六进制字符串，
`text`/`enum` 使用字符串，`ref` 使用文档引用，`sequence` 使用值数组。
`mapping` 使用有序的二成员 `sequence` 键值对数组，不将字段或类型化键转成字符串。
例如 Int 1 是 `["integer","1"]`，Bool true 是 `["boolean",true]`，
Float 负零是 `["float_hex","-0x0.0p+0"]`。原表达式中的一元负号另行保留。

Bytes/text parser 严格使用 UTF-8 和一个 JSON value。每层 duplicate object key（包括
相同值）在构造 mapping 前拒绝；trailing tokens、invalid UTF-8、NaN/Infinity 和无穷
数值拒绝。Already-parsed input 有独立入口，不能证明调用者此前没有丢失 duplicate keys。
未知 marker/kind/field、缺失字段、错误 tag/ref/ordinal 和 parsed-container cycle 均受控拒绝。

整数字面量使用显式 Int tag 和规范十进制文本，避免 JSON/host 浮点转换。Float 使用
显式 tag 和有限 float.hex 表示，保留 signed zero；Bool 和原 decoded Text 各有自己的
tag。Unary negative 保留原 operator/operand 与 span，不折入 payload。原 Int/Float 超出
transport 数值/lexical 范围时返回 typed rejection，不修改上游规划/字面量 admission。

上限固定为 UTF-8 输入 8 MiB、32,768 records、131,072 reference edges、64 层 parsed
container nesting、单一 Text 262,144 个字符、整数十进制 magnitude 4,096 digits。
已解析输入仅接受 JSON 的内建 dict/list/scalar 容器；单个集合至多 131,072
成员，检查节点预算至多为 reference-edge 上限的八倍。Ref 的原始 JSON 整数
只允许非负规范十进制形式，`-0` 也拒绝。输出同样受 8 MiB 限额约束。
在昂贵转换前先检查廉价字节/长度/深度限额；不关闭解释器的 integer safety limit。
Recursion/resource errors 在支持域内转为闭合 outcome，无 truncated accepted document；
不承诺抵抗 OS kill 或任意 host memory exhaustion。

Canonical bytes 使用 schema field/record order、UTF-8、JSON ensure_ascii=False /
allow_nan=False / compact separators，尾部恰一个 LF。无 sort-by-value、hash/id、CWD、
seed、interpreter/import path 或临时路径 identity。合法 authored Text、connector locator
或显式 provenance 即使含路径、URL、0x 仍为数据，不按文本外观删除或 redaction。
Rejected outcome 不提供 canonical bytes，也不泄露 payload/exception chains。

Pure evaluator 建立 immutable record/ref/query indexes，检查完整 mandatory links、role/
owner/order/type/value、feature demands 和 optional assessment presence。只在 executable
producer/stage dependency 上检查所需 acyclicity，不把 source-map/result backreferences
统一套进 DAG。Decoded view 返回 portable records，不能作为 executable import。

运行时入口为 `build_project_sql_plan_portable` 与
`verify_project_sql_plan_portable`，原有四类 inspection 提供 `portable()`。
纯入口为 `evaluate_project_sql_plan_document`、
`decode_project_sql_plan_mapping`、`parse_project_sql_plan_document`；
`Inspection.record(ref)` 与 `Inspection.for_kind(kind)` 只查询本次文档的数据记录。
文档内引用是局部数据地址，不能充当跨文档、跨请求的运行时身份凭证。

## 首个真实 process family 与 reader 闭合

新增 family `phase65`，probe 为 `_pietto_phase65_sql_plan_differential_probe.py`，ambient
marker 为 `PIETTO_PHASE65_SLICE14_AMBIENT`。沿用 existing matrix request shape：两个
available supported interpreters 的 checkout seeds 0/1/7/4294967295，以及每个解释器
seed7 的 relocated/installed cells。不加入 CLI_SESSION_FAMILIES，不修改环境/调度策略。

最小固定 corpus 由五种正常源码组成：minimal/default policy、typed bound literals、
重复具名 SET/positional terminal、aggregate/window/QUALIFY/result staging、hidden
STRICT-FD ORDER。包含原 source/report maps 与一个显式 partial target assessment。
每种 observation 由独立原 pipeline 构造，不手造最终 AST/IR/plan，不为组合改写上游限制。
昂贵 process corpus 保持有限；全部 production record branches 和 malformed-input handling
在本交付完成，Slice15 只扩大 conformance。

Probe 提供 observation(workspace)、唯一 render(value, workspace)、真实 main(argv)。
Standalone 通过实际文件 entrypoint 执行；与 forward/reverse batch 的 envelope bytes
逐字节一致，成功 stderr 为空且 stdout 恰一条 LF framing。失败 cell 不发布部分结果。
Seed 仅在启动子进程时设置；沿用 invocation-local acquisition、原 atomic publication、
xdist coordination 和 cleanup。

复制清单只添加新 probe 的精确文件。Probe 仅依赖生产模块与已有 support manifest 中
的支持模块。Relocated/installed child 在 checkout 外运行实际复制的 probe；同一个
产出 observation 的 child 记录 portable/pure/schema 模块 import origins，在 acquisition
receipt 中核实其位于实际 relocated/installed root 并排除 checkout。Origins 不进入产品。
Installed wheel 从最终冻结候选构建，不沿用更早候选的 wheel。

两个 Interlude II readers 分别保留 phase58–63 的历史 62-request/16-cell 文档事实与
原 phase58–64 的 74-request compatibility 子域。当前 request 总量、largest cell 和
support manifest 对应从独立 expected manifest 验证，不将旧数字永久改写成新的 magic
number，也不让同一错误 registry 自证正确。旧 probe/render/standalone 字节行为不变。

若 runtime portable adapter 消费 capability carriers，仅在三份既有 Phase52 隐私测试的
全部适用集合登记 `src/pietto/_project/project_sql_plan_portable.py`。Pure/schema 不登记、
不 import capability/runtime/AST/IR；原 producer inventories、扫描器和公开边界保留。

Phase57 的现有 scope guard 对 `project_sql_plan_portable.py` 与
`project_sql_plan_portable_schema.py` 仅放行 `extension_catalog` 元数据词汇。
两者仍受 create-extension、`pg_extension`、server-version discovery、driver
以及原 named-extension 词汇禁令约束，不整体加入旧 catalog owners。
对这两个精确路径，直接标识符、属性和 import alias 还会检查 catalog construction/
selection 与 provider acquisition API，元数据许可不放行这些操作引用。
Pure owner 没有使用该词汇，不增加例外。原 catalog module/provider inventories、
catalog-source、package-manifest 与 public-export 检查保留；此迁移不授权
catalog discovery、provider acquisition、installation 或 database access。

## Gate 与完成边界

精确范围上限 A6/M16/D0、22 paths；inventory 上限 production204/test460。Probe 计入
既有 test Python inventory，仍由唯一 reader 维护。已有 report/map/assessment 改动仅限
可选 portable entrypoints/read accessors，不迁移语义或修改原 carrier 以适应编码。
新增可修改路径仅为既有
`tests/test_phase57_slice1_postgresql_extension_signature_catalog_scope_lock.py`。

累计预算 6 causal correction groups、4 local authoritative starts、1 initial ordinary
commit、余额内至多 1 natural-CI repair child。第 4 组后复核完整剩余 findings 与收敛；
原失败和计数不重置。作者 self-review/Ponytail review 不称第三方 review。

Final-input freeze 前完成全部合同与 lifecycle/inventory。最终要求两个 locked Python
环境的 focused/pure/runtime/reader/privacy/compatibility，真实 phase65 seed/relocation/
installed cells、standalone/batch parity、Ruff/format、production/test Pyright，以及
Python3.13 authoritative/generated/golden/package gates。封存实际测试树后一次普通
commit/fast-forward push，自然 exact-head push/main/attempt1 的两个 Python jobs 四项
步骤成功才建立 publication authority；后续源码更改需更新适用验证与安装 artifact。

成功后 Phase64 COMPLETED，Phase65 ACTIVE，Slices1–14 PUBLISHED，Slice15 NEXT /
NOT IMPLEMENTED，Slice16 NOT IMPLEMENTED，N16 不变。没有开始 Phase66、执行、
caller rebind、driver integration、redaction 或 Slice15 的全量 conformance catch-up。
