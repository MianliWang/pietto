# Phase71 S02 — PostgreSQL 嵌套 carrier 与有界来源合同（candidate）

## 状态与决定

本文是 S02 的**批次评审候选**，基于 S01 绑定的合成基线
`9511f13563d0d5ce21fc778c6a3828a8324c2222`。它不是 Gate 2 证据，不是已发布行为或公开格式，
也不允许开放嵌套执行。B1 证据目录中的早先独立评审针对本文更早的字节（S02 终审没有记录摘要），
不覆盖本修订；B1 验收前须重新独立评审。

按 D71.07，选择私有的 PostgreSQL `postgres_rows` live carrier `pg_column_arrays_v1`：一个
presence/count scalar，加上按子 schema ordinal 顺序、每个子字段 occurrence 一个 PostgreSQL 类型化
`array_agg` 结果。使用普通的 Psycopg 文本结果路径（`col_arr`），不用 `col_arr_bin`。后者在
基准会话中同样精确，并且在一父 1,048,576 子的形状上更小（DataRow 字节 103,353,923 B、decode
窗口 VmHWM 增量 859,984 KiB，`col_arr` 为 120,764,978 B、893,324 KiB；两个量的定义见下表
末行）；它还不依赖文本输出的会话设置：在下表第 2 行的六种会话变体下（含 `col_arr` 中止的
`extra_float_digits=0`），`col_arr_bin` 对 pid 1、3、6 都是 EXACT。取舍是：文本路径要求 S10、
S14、S15 固定或核实这些会话设置（下表第 2 行）；binary 路径不需要，但现有 `PostgresExecution`
只走普通 cursor/文本结果路径，改用 binary protocol 会新增 reader/ABI 面，目前没有证明需要。
这既不改变源语言，也不改变任何现有的 scalar/result/IPC 格式。

`jsonb_obj` 与 `jsonb_pos` 被拒绝：实验中 `-0.0` 变成了 `0.0`。JSON、record array 与
binary-protocol 变体都不是回退方案；它们需要各自完整的替代证据与评审。

B1 证据目录 `/home/mianliwang/.local/state/pietto/evidence/pietto-phase71-20261026/b1` 保存
source-bound 设计修订 r1–r4、carrier 选择与独立评审，并引用 native 分析。native 分析与本地
Arrow/IPC replay 本身在
`/home/mianliwang/.local/state/pietto/evidence/pietto-post70-stability-20261016/work/claude-lead-20261023/phase71-s02/codex-r2/`
（`native-analysis-final.md`、`replay/`）。

## Carrier 不变量

1. descriptor 从受检子 schema 导出：有序的子字段 occurrence、期望的 array OID、期望的 element
   OID、leaf 域、nullability 与一个 carrier 版本。标签与 JSON key 从不用于恢复子身份。
2. presence/count 精确：`None` 表示容器不存在，此时每个 array 都必须不存在；`0` 表示存在的
   空 `[]`，此时每个 `array_agg` cell 都是 SQL `NULL`；正的 count 要求每个 array 都存在且恰好
   这么长。所有 scalar 都是 `NULL` 的子行仍是一条子记录。
3. 每个字段聚合消费同一条已形成的子 occurrence 流。SQL lowering 只为对齐并行 array 创建一个
   私有 ordinal；它不公开，不决定 LIMIT 成员，也不给用户 tie 顺序保证。
4. 每个并列 collection 有独立的相关/LATERAL 聚合；任一 collection 的 carrier 形成之前，子行
   从不互相 join。
5. 未知的 OID/域/arity/nullability/字节公式、意外的 carrier 字段或畸形的 native 结果，在构造
   Arrow 之前拒绝。driver 默认 loader 在严格 decoder 之前抛出的异常（见下表第 2 行）同样必须
   映射为确定的拒绝，不能作为未捕获异常泄漏；拒绝也不回显 driver 消息，因为其中带有子值
   （brief 的“离线读取与诊断”规定不默认回显子值）。

## 前提、证据、核实时点、范围与有效期

| 前提 | 证据 | 核实时点 | 范围 / 有效期 |
| --- | --- | --- | --- |
| `col_arr` 保留所覆盖的值与容器 | Job 2549 分析：`/home/mianliwang/.local/state/pietto/evidence/pietto-post70-stability-20261016/work/claude-lead-20261023/phase71-s02/codex-r2/native-analysis-final.md`；返回的 `/home/mianliwang/.local/state/pietto/evidence/pietto-post70-stability-20261016/teach/runs/teach-post70-corpus-p71carrier-s02r2-codex/returned/out/fidelity.json.xz` | S10 在确切候选上重做严格的 native 解码 | PostgreSQL 18.6、Psycopg binary 3.3.5，仅限该 fixture 及其基准会话：`fidelity.json.xz` 的 `server` 记录为 `server_encoding` UTF8、`lc_collate` C、`TimeZone` UTC、`extra_float_digits` `1`、`DateStyle` `ISO, MDY`；会话变体与域外值见下一行；不是 Gate 2 或跨路线证明 |
| 文本输出依赖的会话设置已固定 | 产品路线固定 `client_encoding=UTF8`、`search_path=pg_catalog`、`timezone=UTC` 与 `standard_conforming_strings=on`，另设的 `statement_timeout`、`jit=off` 与 `application_name` 不影响文本输出（`src/pietto/_project/project_execution_postgres.py`）；`src/` 既不设置也不读取 `extra_float_digits` 或 `DateStyle`。Job 2549 实测（`fidelity.json.xz` 的 `session` 与 `ood`）：`extra_float_digits=0` 时 `col_arr` 没有失败关闭：float8 文本输出舍入为 15 位有效数字，该 fixture 含 `-DBL_MAX`，舍入为溢出的 `-1.79769313486232e+308`，Psycopg 默认 loader 因此抛出未捕获的 `OverflowError`，消息带出 array 的其余部分（该 lexeme 之后的 25 个子值与结尾的 `}`）；实验的平面默认 loader 对照抛出只含该 lexeme 的同一 `OverflowError`（实验对照，未在 Pietto 产品路线上复现）。异常只因这个极端值出现：同一 pid 1 array 中位于它之前的 `0.30000000000000004` 与 `0.3333333333333333`（`extra_float_digits=1` 的原始 cell）会输出为 `0.3` 与 `0.333333333333333`，解析成不同的 float 而不抛异常；没有极端值的数据因此得到静默的错误 float 值（由原始 cell 与 15 位舍入推得，未单独实测）。`extra_float_digits=3`、`DateStyle` 为 `German, DMY`、`SQL, MDY` 或 `Postgres, MDY`、`TimeZone=America/Toronto` 下，`col_arr` 对 pid 1、3、6 都是 EXACT（`rec_arr` 在三种 `DateStyle` 下对 pid 1、6 REFUSED（`CARRIER: Date lexeme`），对 pid 3 EXACT）。域外值中，date 与 timestamp 的 `infinity`/`-infinity` 以及 date `4713-01-01 BC` 在任何严格 decoder 运行前就由默认类型化 array loader 抛出 `DataError`，token 里带着 array 的结尾（如 `'-infinity}'`、`'4713-01-01 BC"}'`） | S10 在同一 owned 连接上固定或核实文本解码依赖的每项设置，并把上述 driver 异常映射为确定的拒绝；S14（Float）与 S15（Date/Timestamp）补齐各自 leaf 依赖的设置 | 只覆盖上述六种会话变体与该 fixture 的域外值；`extra_float_digits <= 0` 舍入 float8 文本输出：一般结果是静默的错误 float 值，只有舍入后溢出的值才变成未捕获的 driver 异常（本 fixture 的实测）；两者都不是拒绝，把 driver 异常映射为拒绝挡不住前者，只有固定或核实该设置才能；未核实相应设置时对应 leaf 拒绝 |
| 数据库编码是 UTF8 | 实验库的 `server_encoding` 是 UTF8（`servers.json`）；产品路线只固定 client 编码，只回读 `current_setting('client_encoding')`，`src/` 不读 `server_encoding` | S08 preflight 在同一事务读取 `current_setting('server_encoding')`，不是 `UTF8` 就在主 SQL 前拒绝 | 只有这样 `octet_length` 才等于 UTF-8 输出字节；单字节编码中 U+0800 及以上的字符（如 WIN1252、LATIN9 的 `€`：存 1 字节，UTF-8 输出 3 字节）会使下文的 Text 上界失效 |
| 普通文本结果 cell 携带类型化 array | 返回的原始记录：`/home/mianliwang/.local/state/pietto/evidence/pietto-post70-stability-20261016/teach/runs/teach-post70-corpus-p71carrier-s02r2-codex/returned/out/raw-fidelity.jsonl.xz` | S10 核对确切的 native metadata/OID 与 decoder | 82 条 `col_arr` 原始记录全为文本格式 `0`，OID 相同（`[20, 20, 1016, 1000, 1022, 1009, 1231, 1182, 1115, 2951]`：父值/count 加八个 array）；不作一般 buffer 结论 |
| 需要显式的聚合顺序与分开的并列子表 | `native-analysis-final.md` 中 job 2549 的 tie/顺序保真与 `2 x 3 -> 6` 并列反例 | S08/S16 的真实发射与组合测试 | 内部 ordinal 只保证配对；D71.03 的 tie 语义不变 |
| 根/来源身份与单个只读事务存在，preflight 与主 carrier 语句共享一个 snapshot | 现有的 `project_postgres_source_assurance.py` 与 `project_execution_postgres.py`：`isolation` 为 `stable` 时 `BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY`，否则 `SERIALIZABLE`，profile 刷新核对该隔离级别；r2 依赖这一事务语义让 preflight 与主语句读同一 snapshot（不另读 snapshot token） | 每次 S08 native 尝试：live qualification，同一 owned 连接与事务，不重连/不重绑定，并核实隔离级别仍是 REPEATABLE READ 或 SERIALIZABLE | 只限现有合格的 `postgres_rows` 路线；不推及 ADBC/MySQL；改为每条语句各取 snapshot 的隔离级别（如 READ COMMITTED）会使 preflight 读数不再界定主语句，此时拒绝 |
| 非常量来源的 carrier 数据在主 carrier SQL 之前有界 | B1 证据目录中 S02 source-bound 设计记录 r2–r4，及本文下述修正 | S08/S10 在主 SQL 前做 scalar preflight，并有独立 verifier | 只覆盖结果行的 DataRow 字段贡献（含 typed-array）；不是 executor/RSS/Arrow/网络上界 |
| 内存不由本准入模型界定 | `col_arr` 一父 1,048,576 子（`native-analysis-final.md`；返回的 `sweep.jsonl.xz`）：DataRow 字节 120,764,978 B，即 `7 + 10 × 4 + 120,764,931` 值字节，不含其他协议 framing；decode 窗口 VmHWM 增量 893,324 KiB，即 decode 前重置 VmHWM 后的峰值减基线 RSS。窗口不含 fetch，但增量含 fetch 时已加载并留到 decode 窗口的行：Psycopg 默认的类型化 array loader 在 `fetchall` 中运行，decode 窗口开始前 RSS 已比基线高 753,028 KiB（`col_arr_bin` 的 859,984 KiB 中为 717,696 KiB），所以它不是 decode 本身的成本。释放后读到的进程 VmHWM 为 1,421,744 KiB（含实验自身 decode 之后的 digest） | S10、S12 与 S20 各自的 native/Arrow 内存与超限检查 | 单一 fixture/主机/profile 的观察，不是安全运行上限；现有路线的客户端 cursor 可能在首次读取时把整个 native 结果放进客户端（brief 现状能力表），carrier 上界从不证明读取前内存 |

job 的返回经过字节核验，但 `gate2_qualified: false`；其远端环境没有 PyArrow。本地 replay
只在返回数据上使用固定版本的 PyArrow 26.0.0（Psycopg 3.3.5，见 `replay/replay.json` 的
`local`）。两者都不能单独使产品路线合格。

## D71.07 起点假设的处置

| D71.07 起点假设 | S02 处置 | 消费者 |
| --- | --- | --- |
| 行数上限只数父行；`batch_rows`、`max_rows` 含义不变 | 证实保留：一个父行是一个 DataRow，`batch_rows` 与 `max_rows` 仍只数父行 | S10、S12 |
| 子行计入字节上限（默认每批 1 MiB） | 保留并细化为两道检查：主 SQL 前的 carrier 数据准入（下文 `DataRow`、`D_batch` 对 `batch_bytes`，`D_total` 对 `max_bytes`），以及交付时照旧的计量。现有 `batch_bytes`/`max_bytes` 计的是交付字节，`max_bytes` 还计入路线的 qualification profile 与 catalog 读取（`src/pietto/execution/_access.py` 的 `ExecutionLimits`）；preflight 的数不替代也不改变这一计量 | S08、S10、S20 |
| 每次执行最多 1,048,576 个子行 | 保留为独立的准入条件：传播出的总子行上界（因而也包括每个父行的子行上界）不得超过 1,048,576。字节规则不能代替它：默认限制下 3,496 个父行，每行一个非空父 `Int`、count 与一个 300 个 Bool 子行的 array，`DataRow` 为 3,965（`7 + 46 + 7 + 3,905`），`D_batch` 为 1,015,040（不超过 1 MiB），`D_total` 为 13,861,640（不超过 64 MiB），却有 1,048,800 个子行 | S08、S10、S20 |
| 一个父行的列表放不进一批时整批拒绝，不拆行 | 保留：任一 `DataRow` 超过 `batch_bytes` 时在主 SQL 前拒绝整个执行；交付时超限的父行使其所在批整体失败；从不拆分父行，也不静默加入 `LIMIT` | S10、S12、S20 |

## 保存与离线读取可控域

S02 没有新的保存或离线读取实测：job 2549 的本地 replay 只证明该 fixture 的严格 Arrow 往返
（`to_pylist` 后逐位比较 float、以 `compare_total` 比较 Decimal、要求 naive Timestamp），以及
IPC read-back 与写入的 array 按 PyArrow `equals` 相等。`equals` 视 `-0.0` 与 `0.0` 相等（两种
JSONB 变体丢了 signed zero，`replay.json` 中它们与 oracle 的 `equals` 仍为真），所以 IPC 一项不证明
float 逐位保留。它说明解码后的嵌套 batch 可以序列化；完整顶层行的保存与既有 publication
资格由 S18 证明，S02 不声称。S02 冻结的可控域就是 brief 的现有边界加上文的上限：IPC 的
96 MiB 上限、`compression=None`、`allow_64bit=False` 不因嵌套放宽；保存以完整顶层 occurrence
为单位，子行不独立 checkpoint、ACK 或跨 chunk 拆分，优先复用 workspace v7（D71.06）；IPC、
R1 与 `verified_export` 各自先用现有 envelope/输入字节限制约束元数据解析，再核实深度为 1、
offset、子行数（不超过上文的子行上限）与声明规模，然后才构造或物化。S17–S19 在此域内证明
各自的读者，或以证据替换本条；在那之前，嵌套值在保存/IPC/R1/导出处拒绝。

## 有界来源准入模型

preflight 先在同一事务读取 `current_setting('server_encoding')`，不是 `UTF8` 就拒绝：
`client_encoding=UTF8` 只让服务器在输出时转码，`octet_length` 数的是数据库自身编码的字节。
随后，对每个受检的物理根和只在需要的 Text 来源 occurrence 上，一个固定的私有 scalar 读取
得到有上限的 `COUNT(*)` 与有上限的 `MAX(octet_length(value))`。它只指名已经合格的根/字段，
不接受调用方 SQL、估计值、回调或新来源；它在来源 qualification 之后、主 carrier 提交之前，
在同一 owned 只读事务与 binding 上运行；该事务是 REPEATABLE READ 或 SERIALIZABLE，preflight
与主 carrier 语句读同一 snapshot（见上表“根/来源身份”一行）。每个读数截止在相关上限中最小者加一：父行来源的
`COUNT(*)` 对 `max_rows`，子行来源的对 1,048,576 的子行上限（同时供两者的根取较小者），Text
的 `MAX` 对 `batch_bytes` 与 `max_bytes` 中较小者。读数到达截止值即拒绝，从不把截止值当作
上界继续传播（r1 的 `max_rows + 1` 拒绝哨兵、r2 的饱和即 `UNKNOWN`）。

固定 `VALUES` 与已准入的有限表函数（Phase70 的有界 `generate_series`）是常量来源，不做物理
preflight：行上界取确切的字面行数或已知的有限行数，字段上界取确切的字面编码或闭合的有限域
上界（r2）；它们只是小域回退，不能充当下文首个真实来源正例。受检计划的 descriptor 保守地传播
上界：过滤与排序不缩小上界；inner/cross join 相乘；LEFT 用
`left * max(1,right)`；SEMI/ANTI 保留左侧；分组聚合至多等于其输入；**全局聚合恰好一行，
即使输入为空**；LIMIT 只缩小行数，从不缩小字段宽度。唯一性不收紧 join 上界：声明的
`unique(...)` 是受信任的 Pietto 模型合同，不做运行时或 catalog 强制（见[语言文档](../../language.md)），
违反它的数据会产生超出上界的 join 行；推测的或 catalog 上的唯一性同样不用。closed let 携带
其定义处的上界；capture 对每个父行使用子上界，总数取饱和的父行乘子行。未知的操作/公式、
volatile 路径、上述有限表函数之外的 set-returning 路径、溢出或 profile/binding 变化都拒绝。

绑定参数使用其确切的受检值。对 Text，`O_param = len(value.encode("utf-8"))`；过滤中的参数不会
使来源的行数或宽度变小。其他参数/聚合/计算值需要各自闭合的 canonical PostgreSQL 输出上界，
否则拒绝。

## 有限的 DataRow/typed-array 模型

设已核实的 canonical UTF-8 scalar 输出上界为 `O_i`（Text 的 `O_i` 是上述 preflight 在 UTF8
数据库上测得的 `MAX(octet_length(value))`）：

```
E_i       = max(4, 2 * O_i + 2)
A_i(n>0) = 2 + (n - 1) + saturated_sum(E_i, n terms)
A_i(0)   = absent          # array_agg is SQL NULL
Cell(x)  = 4 + x
NullCell = 4
DataRow  = 7 + sum(field over every emitted result field), where field is
             Cell(A_i(n)), or NullCell for n = 0 / absent   # child-field array
             Cell(digits_10(n)), or NullCell for absent     # count/presence scalar
             Cell(E_i)                                      # ordinary parent scalar (conservative)
D_batch  = saturated_sum(largest batch_rows DataRow values)
D_total  = saturated_sum(all DataRow values)
```

`E_i` 覆盖 NULL 记号，或引号加最坏情况的转义。`A_i` 包含花括号与分隔符。`DataRow` 计入父行
发射的每个结果字段：carrier 的 count/presence 与各 array，以及普通父字段。固定域 leaf 的
`O_i` 用 r3 的值：`O_Int = 20`（`int8` 最长文本 `-9223372036854775808`）、`O_Bool = 5`（保守值；
PostgreSQL 的 boolean 文本输出只有 1 字节 `t`/`f`）。所有算术在所比较上限加一处饱和：
`DataRow` 与 `D_batch` 对 `batch_bytes`，`D_total` 对 `max_bytes`，父行计数对 `max_rows`，子行
计数对 1,048,576。准入要求每个 `DataRow` 与 `D_batch` 不超过 `batch_bytes`，`D_total` 不超过
`max_bytes`，传播出的父行上界 `P` 不超过 `max_rows`，且传播出的总子行上界不超过 1,048,576。

在上述前提（UTF8 数据库、preflight 与主语句共享事务 snapshot、已核实的输出公式、不用唯一性
收紧 join）成立时，这只界定结果行
（carrier 加普通父字段）的 PostgreSQL DataRow 字段贡献。RowDescription/控制 framing、
client/TLS/TCP 字节、PostgreSQL executor 内存、Psycopg 缓冲与 Arrow 分配都在本模型之外，需要
各自既有的/native 的或 S10 专门的检查。解码后的相等结果或原始 fixture cell 长度从不构成来源
上界的证明。

## 首个真实来源的 S12 域

首个非常量正例必须使用合格的物理根，不能用 VALUES：

* 数据库 `server_encoding` 为 `UTF8`；
* 父根 `P <= 64`；
* 子物理根的**全局** `N_child <= 16`（不是未测量的每父行声明）；capture 可以保守地产生
  `64 * 16 = 1024` 个子 occurrence，低于 1,048,576 的子行上限；
* 一个 collection，受检子行为 `(Int, Bool, Text)`，一个非空父 `Int`，没有并列 collection，
  实际来源/绑定表达式的 Text 至多 256 个 UTF-8 字节；并且
* 同一 descriptor/preflight 在主提交前证明全部结果字段与实际的来源/profile/binding。

在该域边界（`O_Int = 20`、`O_Bool = 5`、`O_Text = 256`）：`E_Int=42`、`E_Bool=12`、
`E_Text=514`、`A_Int(16)=689`、`A_Bool(16)=209`、`A_Text(16)=8241`，五字段结果行（父 `Int`、
count、三个 array）的 DataRow 为 `7 + 46 + 6 + 693 + 213 + 8245 = 9210`；因为 `P = 64` 不超过默认
`batch_rows = 256`，`D_batch = D_total <= 64 * 9210 = 589440 < 1048576`（`batch_bytes` 的默认
值 1 MiB；`max_bytes` 的默认值是 64 MiB）。这是一个可准入的 carrier 数据域，不是完整的协议或
内存上界。

## 消费者 owner 与现有拒绝

| Owner | 后续必须闭合 | 现状 |
| --- | --- | --- |
| S07 | 一层嵌套 ResultContract、可移植 schema 与 digest | 拒绝嵌套形状 |
| S08 | 受检的 Collect 发射、排序、来源上界 preflight | 没有嵌套 SQL 路线 |
| S10 | native descriptor/严格 decoder 与 Arrow 构造 | 只有平面 scalar reader |
| S13 | 私有的 SQL 侧 Unnest，在运算前恢复 scalar 含义 | 没有 Unnest 执行路线 |
| S17 | 嵌套 IPC framing/读取验证 | 只有平面 IPC |
| S18/S19 | 保存、R1 与 verified export | 拒绝嵌套值 |
| S20/S21 | 资源/取消/拒绝/差分闭合 | 没有组合 PASS |

`postgres_adbc`、MySQL、R2/recover、sink/relay、多层嵌套与每个尚未闭合的公开嵌套消费者都保持
早期拒绝。S02 r3 的自检只是有限的设计算术；r4 为 NOT_RUN；本修订的 UTF8 编码、子行上限、
join 收紧、preflight 截止与 `DataRow` 字段规则的修正，以及补记的 snapshot 前提、常量来源规则与
会话设置证据的重述，都没有新的运行。它们都不是 native 或产品 PASS。
