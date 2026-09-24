# Phase66 Dialect SQL Emission Product Initiation Gate And Route Lock v1

## Authority and evidence posture

本合同完成 Phase66 Slice1 的 fresh initiation/source audit/decision/route 工作。
2026-09-15 的完整替代任务采纳 D66.01–D66.16 和独立的 N66=16；不依赖旧草稿。
本次仅 documentation/static tests，A2/M4/D0 六路径；production204 不变，
test Python files462→463。数据库、driver/image、workflow、lowerer 和 Slice2 均未实施。
phase-level design 不授予未来文件、资源或执行权限。

Gate0 重新 fetch/readback，确认 clean main/index/worktree/untracked、无 active Git
operation 或相关竞争 writer/validator。接受基线：

```text
commit = 71c1fa13c152d7be317c4bffee48615a39f1c2e4
tree = 57f26514eb3db18213d369851a6b7975916cea92
parent = 128388bc258d6ee861c0128c42324fca712c0dcc
natural CI = 34902493866 / push / main / attempt1 / success
```

[基线自然 CI](https://github.com/MianliWang/pietto/actions/runs/34902493866) 的 Python3.12/3.13
jobs 均完成 authoritative/generated/golden/package。Phase65 COMPLETED、Slices1–16
COMPLETED/PUBLISHED 是已发布输入；其 F65S15-01/F65S15-02、失败 head、approval、N16
及关闭预算保持历史。Phase66 在此基线 NEXT/NOT STARTED。

本文所有 Phase66 runtime/API/schema 名称及支持规则均为 **PLANNED**，不是已经实现。
Slice1 只有经过完整审查、本地 final gates、sealed tree、ordinary commit/ff push 与自然
exact-head CI 后才 COMPLETED/PUBLISHED；届时 Phase66 ACTIVE、Slice2 NEXT/NOT IMPLEMENTED、
Slices3–16 NOT IMPLEMENTED。E01–E10 并不因此满足。
本合同不嵌入未来自身 commit/tree/CI；实际收据和累计计数只存
`~/.local/state/pietto/evidence/phase66-slice1/`。

## Thirty mandatory answers

| # | Field | Phase66 answer |
| --- | --- | --- |
| 1 | Live authority | 上述 live baseline、自然 CI 与当前源码/断言重新绑定；旧 handoff 只作输入，外部网页只作研究证据。 |
| 2 | User/product outcome | 一个 explicit selected verified plan + emission contract 产生完整只读 query artifact，或 complete typed blockers；生产编译不连接 DB。 |
| 3 | Semantic reference model | 保持 completed semantics/VERIFIED IR/ProjectSQLPlan 的 BAG、TRUE-only filter、NULL、stage、FD/proof scope 与 authored nesting；不添加 evaluator。 |
| 4 | Identity model | source declaration、binding/use、immediate terminal、canonical field、SQL symbol、logical slot、SQL occurrence/server index 各自独立；selectors 只在边界解析一次。 |
| 5 | Construction states | INPUT_REJECTED、BLOCKED、VERIFIED 三类公开结果；未验证 SQL AST/text 是内部候选，只有 VERIFIED artifact 可成功输出。 |
| 6 | Proof posture | 原 PROVED、declared environment、implemented rule、independent verification、target observation、runtime fulfillment 分开；target 不适用不改 upstream proof。 |
| 7 | Layer ownership | Phase65 拥有 neutral plan；66 拥有 source realization、SQL AST/text、params/ranges、emit contract；67 result/Arrow；68 execution。 |
| 8 | Dependency direction | semantic → IR → plan → dialect AST → render/artifact；verifier 检查对应关系；inspection/portable 不返向 resolve/type/construct。 |
| 9 | Versioning and migration | 新 input/public artifact/private observation 分别版本化；package0.1.0、legacy JSON v1、project check JSON v2、metadata v1 不改。 |
| 10 | Requirements/capabilities | 独立枚举原 mandatory demands 和 generated requirements；一个 coherent scoped environment 下匹配事实及实现规则，无循环自证。 |
| 11 | Interchange | minimal public SQL/value/use/result/range artifact 从首次 emission 可消费；full private AST observation 在14；decoded bytes 不能恢复 runtime authority。 |
| 12 | Execution | 编译零连接/凭证/网络；Slice2 单独授权 test-only isolated execution；产品 executor/fulfillment 属68。 |
| 13 | Resource lifecycle | 编译 invocation-local；future harness acquired→ready→observed→recovered→closed，bounded retries/timeouts、owned cleanup、双重失败保留，见 prerequisite ledger。 |
| 14 | Security/trust | 显式 contained trusted-read contract、closed structured names/types、拒绝 raw SQL/callback/secret；generated nodes 无 DML/DDL/locking/OUTFILE；外部 view 不因此 effect-free。 |
| 15 | Algorithms/data structures | ordered DAG traversal、局部 occurrence indexes、closed strategy dispatch、token buffer、独立范围/绑定及需求检查；无 optimizer/pass framework。 |
| 16 | Complexity | 以 definitions/uses/fields/expressions/demands/generated tokens/bytes 计实际成本；共享 DAG 不展开路径；检查 target 及 compiler ceilings，不宣称全链线性。 |
| 17 | Invalidation | plan/root/policy/envelope 改变使对应所有产物失效；target/source realization/environment 改变使66 target products失效，neutral plan可保留。 |
| 18 | Cache | 只有 invocation-local indexes/buffers，无 persistent cache、跨 snapshot authority 或自动环境缓存；91仍 tentative。 |
| 19 | Concurrency | 编译请求无共享 mutable SQL state；一个 implementation writer；test resources逐 invocation隔离，compiler/process 与 DB matrix分开。 |
| 20 | Diagnostics | 完整原 project diagnostics + selected blockers；固定 typed failure classes 和源序，不合并同名根、不靠message匹配；不得返回可用 partial SQL。 |
| 21 | Inspection | verified runtime artifact上查询 ranges/uses/requirements；只读，无重建/resolution/DB introspection；missing source position保持缺失。 |
| 22 | UX | 显式 project/root/owner/dialect/contract，固定原值 policy；新 mode 独立 versioned result，legacy invocation不变；先验证再 atomic file replace。 |
| 23 | Conformance | 两目标 finite promised rules均有真实最低正例和 violated-premise反例；Slice2先 legacy+独立SQL，Slice3起 installed new pipeline。 |
| 24 | Differential/fuzz | 独立 finite fixtures/oracles、mutation、metamorphic、BAG/order/error joint outcomes；复用process acquisition，不建fuzz平台，不重复全matrix只取数字。 |
| 25 | Packaging | runtime依赖维持stdlib/已有依赖；driver仅test dependency，Slice2精确锁定；installed wheel→artifact→submitted SQL须连贯。 |
| 26 | Support matrix | compiler Python3.12/3.13；semantic targets PostgreSQL18/MySQL8.4；规则级physical domains；server/channel/platform/adapter/environment另记，不能由family推断。 |
| 27 | Release/deprecation/EOL | 本Slice一次普通发布及限额内一个CI child；不tag/release/EOL/改旧格式；失败head保留，改策略/环境须显式批准。 |
| 28 | Readiness/deferred owners | 三类互斥asset ledger和逐67–97 atom处置；test infrastructure未获取但 acquisition/lifecycle/acceptance owner已明确。 |
| 29 | Slice route | N12/N14/N16工作量比较后锁定16；02基础设施、03首个emission、每个operator即时consumer/verification、16仅audit。 |
| 30 | Repair/STOP | 六完整 correction groups、四 local validator starts、一次首发及至多一个CI repair child；第4组复评；material contradiction/extra path/changed trust decision停止并保留证据。 |

### A–L coverage

| Group | Actual answer |
| --- | --- |
| A product | 交付完整 ProjectSQLPlan→selected dialect SQL artifact，compiler不持有执行资源。 |
| B current state | 基线完成65；legacy SQL存在；新pipeline尚无SQL AST/text，F01/F02已关闭但载体差异必须继续消费。 |
| C roadmap pull-forward | 66 core不是跨phase加速；67 result correspondence、68 test resource纪律、81最低conformance有本期consumer；未来-only atoms不建code。 |
| D decisions/freedom | D66.01–16为当前采纳决定；结构化input与closed AST/双verifier的取舍已回答；private names和等价factoring自由。 |
| E semantics/identity | exact roots/occurrences、完整bags/nulling/terminal stages与typed literals；未知effect只阻止依赖该证据的转换。 |
| F layers | 66直接消费65 runtime verification、report、map和raw assessment，新增SQL binding检查不成为Pietto resolver。 |
| G algorithms/cost | 逐实际DAG和emitted structure计成本；完整输入校验、两个需求denominators及整段结果观察均有成本，不能省略。 |
| H state/resources/trust | request声明不证明现实环境；DB测试可获取独立环境观察，production emission只记录前提；scope冲突必须拒绝。 |
| I UX/inspection | explicit selectors与contract；exact tagged Int/Float输出、position数组、UTF-8 ranges；stdout失败不能宣称原子回滚。 |
| J compatibility/release | legacy SQL/CLI/JSON/private observations及package0.1.0保留；新versioned公共产物不等于82 freeze或83 release。 |
| K external assurance | 官方18/8.4/driver/protocol/pytest/Actions资料按11字段记录；本次未执行target，不用网页证明Pietto正确。 |
| L route/control | 每Slice即时正负域/requirements/parameter/range验证；12/14/15负责汇总扩展；缺当前义务不能丢给16或later。 |

### X1–X8 cross-cutting checks

| Check | Actual obligation |
| --- | --- |
| X1 observable equivalence | 值/type/null/重复数、规定order、参数identity、diagnostics/error及complete terminal observation逐规则比较；不以set/sort/epsilon代替。 |
| X2 counterexamples/composition | C01–C32覆盖nullable Bool、outer markers、completed EXISTS、窗口/quotient/SET/LIMIT、输入冲突和错误artifact；与R规则及Slice联接。 |
| X3 unknown/obligation | missing observation、approved non-support、planned implementation、promised-domain defect分列；原LEGAL_UNPROVED enforcement阻止可用SQL，普通risk记录不自动等同未履行。 |
| X4 errors/effects | 不折叠/复制需要未知effects的表达式；CTE不保证once；完整warnings、late error、recovery/cleanup失败不得变成功。 |
| X5 safety/liveness/atomicity | closed AST、bounded input/SQL/resource、无循环自证、startup有限重试、查询终态和owned cleanup；file单次replace，stdout无rollback承诺。 |
| X6 evolution | input/artifact/private版本各自迁移；更换root/physical schema/环境使target产物失效；不修改SQL后假装relocation parity。 |
| X7 evidence independence | plan→AST与events→bytes分别验证；expected fixture不用生产mapper；declared facts不许宣告rule正确，空manifest和相互success引用拒绝。 |
| X8 total workflow/resource cost | 编译完整closure、上下游verifiers、wheel构建、两target启动/装载/观察/恢复/清理与CI收据分别测量；避免Python×seed×driver×server笛卡尔积。 |

## Adopted decisions

D66.01–D66.16 是本任务的新批准输入，不追认为Phase65决定。以下保留完整语义；
后文把它们落实为request/rule/witness/owner。USER_DECISION_REQUIRED表示决定性质，
不表示还待重复批准：.01–.05、.07–.10、.13、.15–.16 属产品/支持/信任决定；
.06、.11–.12、.14 属 ARCHITECTURE_DECISION。所有private names、等价局部分解为
IMPLEMENTATION_FREEDOM；四个current readers更新为DERIVED_MECHANICAL。

### D66.01 — Product, authority and construction states

One exact VERIFIED selected ProjectSQLPlan, its captured policy/envelope, and
an explicit target/source-realization request produce either:
- a complete verified emission artifact; or
- complete typed blockers, without usable partial SQL success.

The artifact contains one read-only query statement, dialect SQL AST, final SQL
bytes, parameter-use/fixed-value mapping, result correspondence, SQL ranges and
realization evidence. Generated nonrecursive CTEs/subqueries are implementation
forms, not new authored query syntax.

Preserve EXPLICIT_MODULES, exact selected-owner/IR roots and whole-project semantic
success. Unrelated valid planning limitations differ from project ERROR.

Do not lower a decoded observation as runtime authority. Existing legacy SQL
generation remains real and unchanged; it is not proof the new pipeline works.
Production compilation has no connection, transaction, credential or network
authority and promises no actual runtime fulfillment.

### D66.02 — Finite target domain and accurate version identity

Use PostgreSQL18 and MySQL8.4 as the two baseline families, with nonempty real
positive domains. Freeze exact rule-level support, not “all valid Phase65 plans.”

PostgreSQL18.6 is a reviewed maintenance-release candidate. MySQL8.4.12 is a
reviewed Docker-image-specific security-update candidate, not an assumed
identical server package across distribution channels.

Separate semantic target family/release, distribution artifact/channel,
multi-platform index versus platform image, actual server build/platform and
relevant library/environment versions. Verify official records; actual image
digests and stable adapter versions are acquired and frozen in Slice2.
No invented pins, rolling latest fallback or automatic downgrade.

Initial functional direction:
- both targets: admitted scan/row/JOIN/group/window/result/SET subsets;
- PostgreSQL FULL: only an explicitly reviewed supported condition/type subset,
  initially appropriate cross-input builtin equality cases; not arbitrary ON;
- MySQL FULL: explicit first-version rejection, no general emulation;
- SEMI/ANTI: exact reviewed EXISTS/NOT EXISTS;
- hidden STRICT-FD ORDER: explicit first-version rejection;
- unsupported window/frame/modifier or representation combinations: exact blockers.

A SQL keyword's existence or parser acceptance does not prove realization.
Each promised family needs a minimum positive rule and negative boundary.
Do not turn all combinations into UNKNOWN or shrink promised success silently.

### D66.03 — Explicit emission-contract input and coherent environments

Define an explicit versioned emission-contract input for project emission,
rather than leaving source realization as an unreachable private carrier.
The planned CLI supplies it explicitly, for example through --emission-contract;
freeze the exact interface in this contract without implementing it here.

At the input boundary resolve logical selectors against current project authority
to exact source/field occurrences. No first-match, ambient project discovery,
raw SQL, arbitrary expressions/callbacks or credentials.

Describe physical relation/column components, representation/value domains,
scan domain and necessary target/environment premises. A locator is not SQL;
do not split dotted text, guess schema/connection or change legacy interpretation.

Check full input structure, duplicates and ambiguity. Then assess target
applicability for the selected dependency/evidence closure: unrelated unused
source descriptions must not poison it. Conflicting duplicate target declarations
across CLI/file reject instead of using hidden override precedence.

Premises carry statement, source or expression scope. All selected rules must
hold under one coherent request; individually satisfied rules under contradictory
session assumptions cannot produce success. Different source-local properties
are not automatically a global conflict.

External declarations express only permitted facts, never “this lowering is
correct.” Compare declared requirements with separately observed test environments.
Record only environmental dimensions actually needed by each rule.

### D66.04 — Logical/physical representation and proof applicability

For each rule retain logical input/result, physical input/result, conversions,
NULL/value domains and relevant range/precision/rounding/comparison premises.

No unconditional Int->BIGINT map, guessed Decimal parameters, generic final CAST
or backend-inferred common type substitutes for this chain. Check aggregate
result representation and every SET column boundary before downstream use.

MySQL Bool's initial physical domain is explicitly0/1, plus NULL where allowed;
truthiness over arbitrary integers is insufficient. Preserve distinctions before
JOIN/GROUP/DISTINCT/SET, not merely when decoding final rows.

Text rules include applicable encoding, collation, padding and any setting that
changes comparison, such as relevant prefix-sort limits. Timestamp/UUID/Decimal
need specific representations; missing premises block the affected combination.
Finite Float binding does not enable deferred Float row equivalence.

Original keys/FD/single-match proofs remain scoped upstream evidence. Verify that
the chosen physical comparison/null/cast rules preserve the premises actually
used. Keep an original PROVED result unchanged if target applicability fails;
block realization rather than rewriting semantic proof status.

Physical row domains matter, including ordinary inheritance versus partition/view
behavior. Do not infer physical uniqueness from a same-named constraint, add ONLY
blindly, or introspect production data. No new type/FD/range solver.

### D66.05 — Scalar values, predicates and supported expressions

Preserve actual admitted expression trees and literal-level evidence. Do not
enable division/general calls or reinterpret UNKNOWN typing through lowering.

Nullable Bool scalar results are distinct from TRUE-only predicate consumption.
WHERE/ON/satisfying/QUALIFY may consume true; SELECT/LET must not replace NULL
with FALSE through IS TRUE or CASE normalization. Do not move such normalization
inside Boolean subexpressions.

Predicate equality, NULL-equal row equivalence, ordering and window peers retain
their separate rules. Generated type anchors and comparisons must not change
overloads or collations without an applicable exact rule.

Unknown effects block transformations requiring those effects to be known;
they do not license a blanket claim that all SQL is error-free. Preserve the
error/evaluation behavior actually specified, without inventing a total evaluator.

### D66.06 — Capture-free SQL scopes and result identities

Keep source/SELECT/SET, declaration/use, canonical export/stage port and SQL symbol
domains distinct. Consume exact immediate terminal outputs at every boundary.

Use deterministic, target-safe internal relation/column names and explicit
column lists. Validate actual namespace binding, not just uniqueness among
generated names: CTE/derived names must not capture physical-source references.
Quoting alone does not prevent name capture.

Check target character, case and length rules. Intermediate addressing names
may differ from user labels through explicit mappings; final labels cannot be
silently truncated, replaced or renamed. Do not depend on output aliases or
numeric ordinals for GROUP/ORDER binding. COUNT(*) is not SELECT *.

A closed SQL-scope binding check is required and is not prohibited upstream
name re-resolution. It checks new SQL structure without guessing Pietto meaning.

### D66.07 — JOIN, grouping, windows and complete terminal consumption

SEMI/ANTI consume the completed right terminal inside EXISTS/NOT EXISTS.
Never replace that producer's own SELECT, SET, GLOBAL aggregation, window or
LIMIT with a simplified base-table scan; never substitute NULL-sensitive NOT IN.

Outer-null-extended stage values remain port references. A right producer's
constant marker becomes NULL when unmatched; do not recompute the constant
above the outer join. Preserve accumulated-left nulling and matching-only inputs.

Keep GROUPED/GLOBAL empty-input differences and COUNT(*) versus COUNT(field).
A semantic FD is not target GROUP BY permission. No ANY_VALUE, MIN/MAX,
extra grouping fields or ONLY_FULL_GROUP_BY disablement as implicit repair.

Selected and hidden windows read their exact pre-window inputs; QUALIFY filters
the established results afterward. Keep named/direct/copied/inherited policies.
Allow only reviewed identity omission of target-default-equivalent modifiers;
unsupported modifiers cannot simply disappear.

### D66.08 — DISTINCT, SET, ordering and result barriers

DISTINCT and SET compare only their exact visible positional tuples; retain
types, Decimal parents, NULL equivalence, operation/quantifier and authored nesting.
EXCEPT right inputs remain membership dependencies.

Keep inner ORDER/LIMIT selection and outer presentation responsibilities separate.
Final promised order must be realized by the final returning query; an inner
CTE's order alone does not establish it.

Distinguish unspecified behavior, explicitly permitted target-defined behavior
and missing required evidence. Do not choose a NULL/collation/tie default merely
because source syntax omits a clause.

Any NULL-order emulation is separately checked for relation ORDER and relevant
window families. Adding discriminator keys must not invalidate or change
offset-RANGE semantics.

Use explicit relation boundaries where needed; do not flatten nested LIMIT or
trust an untested parenthesized spelling. Preserve constant expressions rather
than accidentally emitting ordinal ORDER/GROUP syntax.

Hidden STRICT-FD realization remains blocked initially. No hidden quotient column,
representative row, join-back or unsolicited rewrite. LIMIT0 removes neither
mandatory requirements nor original project errors.

### D66.09 — Sharing, effects and deterministic strategy choice

Shared definition identity does not imply materialization or evaluation once.
CTEs are not universal timing/error/choice-coupling barriers. Preserve only
coupling/evaluation requirements actually supplied by the semantic contract.

Do not duplicate nondeterministic/partial computations where a rule needs an
unavailable premise. Conversely, do not impose blanket mandatory materialization
on every named producer.

Use reviewed closed realization rules, not cost search or speculative rewrites.
Multiple proven-equivalent implementations of the same contract may have an
explicit deterministic internal selection policy. This is different from choosing
a winner among conflicting semantic identities or provider facts.

No runtime “try SQL, then fall back to another strategy,” constant folding,
generic CSE, automatic bridges or new authored correlation semantics.

### D66.10 — Exact fixed parameters and protocol forms

Retain PRESERVE_LITERALS by default and explicit BIND_SAFE_LITERALS eligibility.
No arbitrary caller rebind, value-based slot merging, structural-constant binding
or stage-expression re-expansion.

Separate logical slots, SQL use occurrences and server parameter indices.
PostgreSQL $n reuse requires compatible physical contexts; MySQL ? occurrences
retain their ordered slot mapping. Do not count tokens by searching SQL strings.

Fixed Bool/Int/finite Float/Text values remain exact, including tags and signed
zero. Preserve unary sign structure. Type anchors need semantic evidence and
must not repair errors by coercing values.

Current Slice5 test adapters retain Psycopg RawCursor for $n and use pinned pure
Connector/Python26.7.0 cmd_stmt_prepare/cmd_stmt_execute/get_rows/cmd_stmt_close for ?.
Every MySQL query-purpose submission follows this native route, including zero
parameters. Exact bytes reach prepare and the actual command-send payload unchanged;
statement/session/arguments, actual binary terminals and close-send are observed.
No general placeholder rewriting, cursor fallback or production executor is added.
The former prepared-cursor API remains the historical Slice2–4 choice; its actual
identifier rewrite is an offline counterexample, not a claim that every historical
query failed. The Slice5 contract amends D66.10, R04/R25 and prerequisite P02/P09 only
at this test-adapter/observation boundary; product semantics and R03 timing remain.

### D66.11 — Two complete denominators and noncircular justification

Phase65 whole-target-positive is not an input prerequisite: its residuals include
work Phase66 must implement. Consume raw evidence without upgrading its scope.

Check both:
A. every original mandatory plan demand;
B. every necessary requirement introduced by actual generated SQL structures.

Each generated CAST, correlation, parameter form, ordering/helper or target
strategy links to its rule, original cause and necessary premises. Independently
enumerate completeness from real structures, not a supplied success list.

Keep static evidence, declared external facts, realized strategy and runtime
enforcement separate. LEGAL_UNPROVED enforcement and necessary unrealized
requirements block usable SQL success. Ordinary risk/evidence records are not
automatically unfulfilled obligations.

All justification must terminate in independent accepted roots; mutually
asserting rules cannot certify each other. This finite check is not a new SAT/
proof engine, nor a change to Phase65's demand/report schema.

### D66.12 — Verify through final SQL bytes and source ranges

Verify plan-to-SQL-AST correspondence independently, then verify typed rendering
events/token structure against the final SQL bytes. Correct sidecars cannot
certify wrong text.

Check actual identifiers/operators/parentheses/separators/parameters and complete
coverage; token concatenation must not create comments or different literals.
Neither checker obtains its expected answer by rerunning the same builder/
renderer. Shared primitive encoders and closed schemas may be reused narrowly.

SQL ranges are zero-based half-open UTF-8 byte offsets into the exact final SQL
bytes. Keep original parser character spans separate. Capture ranges while
rendering, not by text search.

Database error positions have protocol-specific units and may refer to internal
queries. Convert only authenticated positions for the actual submitted SQL;
never guess from error-message snippets. JSON escaping, newline conversion,
BOM insertion or adapter rewriting cannot silently reuse old offsets.

### D66.13 — Public artifact, input UX and atomic output

Design an explicit project emit-SQL mode with unique owner selection and explicit
emission-contract input. Preserve legacy single-file CLI/SQL and existing JSON.

Separate the minimal versioned public artifact from full private debug/portable
SQL-AST observation. Public consumption must not wait for the private-format
Slice, nor expose the entire internal object graph by default.

Public fixed values require exact typed encodings, such as decimal text for Int
rather than relying on arbitrary JSON-number precision. Keep output columns
positional; never use name-keyed dictionaries as canonical result identity.

BIND output is a complete SQL/value/use/contract artifact, not a misleading bare
placeholder string. Construct and validate before publishing; prefer one atomic
file replacement over independently written SQL/parameter/map files.
An stdout I/O failure is failure, not an atomic rollback guarantee.

Decoded content does not regain exact runtime identities or authenticate its
source. Checksums identify bytes, not correctness. Artifacts remain source/value
bearing and are not automatically redacted.

Closed generated nodes forbid DML/DDL, data-modifying CTEs, INTO/OUTFILE, locking,
session assignments and arbitrary callable/raw SQL. SELECT spelling alone does
not certify arbitrary external objects as effect-free.

### D66.14 — Bounded construction, invalidation and compatibility

Use ordered DAG traversal, invocation-local indexes and token buffers.
Account for actual definitions/uses/fields/expressions/requirements and SQL size;
do not expand shared paths or claim the entire upstream pipeline is linear.

Check target limits on generated parameter occurrences, columns, windows, nesting
and bytes, not only logical-plan counts. Overflow is typed target-resource failure,
not truncation, implicit multi-statement splitting or new parameter deduplication.

No persistent cache, generic pass/plugin framework, optimizer search or
production SQLAlchemy/SQLGlot/Calcite/DataFusion dependency.

Exact plan/source/policy/envelope changes invalidate the appropriate artifacts.
Target, source realization and semantic-environment changes invalidate target
products even when display names match. Different physical schemas are changed
inputs; do not normalize their SQL afterward to fake byte parity.

Keep package0.1.0, legacy formats and old behavior unchanged unless a later exact
implementing task explicitly authorizes a necessary additive surface.

### D66.15 — Real, independent and complete target observations

Database conformance is a separate required domain, not default pytest discovery
with missing-environment skips. Preserve all existing authoritative tests.
Harness/unit/config tests remain in normal validation; real DB cases use an
explicit collection command and finite independently asserted manifest.

Fixtures and expected results must be independent of the production mapping
being tested. Distinguish exact fixed-value identity, physical-to-logical result
mapping, SQL three-valued predicates, BAG and row-equivalence rules.

Deterministic results use exact required values/types/order. Non-total or tied
results use allowed joint-result constraints, not only marginal sets. No blanket
floating epsilon, set conversion or arbitrary sorting that hides row changes.

Observe complete results and terminal status, parameter transport, column
metadata, warnings/notices and cleanup. Metadata absence is not false/non-null.
Rows returned before a later error do not constitute success.

Capture diagnostics before another statement destroys them; warning total and
stored detail count may differ. Truncated diagnostic/result observation cannot
be reported as empty/complete success. Check fixture-loading diagnostics too.

Use bounded exact errors, not “any exception” as a valid negative.
Preserve an independent success -> expected failure -> success recovery control.

### D66.16 — Test resources, CI and defect attribution

Slice2 owns the first actual isolated target-test facility. It must have a real
consumer: bounded legacy-generated examples plus independently specified SQL.
From Slice3 onward it must consume the new installed emission pipeline, not
continue certifying hand-written SQL alone.

Freeze target artifacts/platforms, stable test-only adapters, environment,
timeouts, bounded startup retries and cleanup ownership before execution.
Separate fixture-management credentials from a least-privilege query role.
No production secrets, ambient DATABASE_URL/PGHOST discovery, unrelated database,
privileged host mounts or global prune.

Model transaction/statement recovery per target. PostgreSQL expected errors
require recovery; MySQL fixture DDL cannot rely on rollback for universal cleanup.
Clean only acquired resources; preserve both query and cleanup failures.

Keep compiler/process and DB execution matrices separate to avoid a gratuitous
Python × seed × driver × server Cartesian product. Supported interpreters differ
from executables actually available in a runner; retain exact observed coverage.

Bind evidence:
candidate -> installed wheel -> generated artifact -> submitted SQL/parameters
-> actual server/environment/query role -> complete observation -> independent oracle.

From the infrastructure publication onward, future applicable Slice acceptance
requires existing compiler gates AND both exact-target conformance outcomes.
Missing/skipped/cancelled/empty required jobs cannot yield aggregate PASS.
Use explicit manifests and artifact receipts, not large job-output payloads.
Keep repository permissions read-only and never combine privileged PR events
with execution of untrusted checked-out code.

Classify failures as compiler defect, fixture/observer defect, infrastructure
failure, target implementation defect or unresolved attribution. A server bug
needs minimized version/environment evidence; do not require a vendor response
before preserving/blocking the case. Hand-written SQL also failing is not by
itself proof the server is wrong.

No silent optimizer-switch workaround, downgrade, xfail or scope shrink. A changed
environment/strategy must be explicitly approved and verified. Preserve failures;
infrastructure interruption does not require fake code edits or an empty commit.
No new manual CI-rerun authority is granted here.

## Concrete request, output and state contract

### Interface and authority

冻结新增 project mode（Slice13 实现）的调用形式：

```text
pietto emit-sql --project PATH --module LOGICAL_MODULE --kind {table,query}
    --name NAME --dialect {postgres,mysql} --emission-contract FILE
    [--literal-policy {preserve,bind-safe}] [--format {text,json}] [--output FILE]
```

参数在同一次调用中提供；positional source 与 `--project` 互斥；owner 三项必须齐全且唯一。
`--module` 使用当前 EXPLICIT_MODULES 的 logical module path，`--kind/--name`查完整候选桶，
零个或多个均拒绝；解析出的 exact owner 交下游，不由lowerer重复按名查找。
新 project mode 默认 `--format json`、`--literal-policy preserve`。
`--format json`只选择新的emission artifact family；一次stdout document、final newline、
handled结果stderr为空。text成功在stdout、失败在stderr；source或contract原文不进入错误回显。
显式project仍要求已有 `pietto.toml` 和 EXPLICIT_MODULES activation，不提供configless入口。
legacy single-file `emit-sql PATH --dialect ...` 的默认text、flags、exit/JSON/SQL保持原状。
project `--output` 写同一个完整 versioned JSON artifact；text stdout是可读呈现，包含完整
SQL、fixed values/uses、contract/results/requirements与diagnostics，不宣称bare BIND SQL可独立消费。
不提供仅SQL的BIND导出。stdout与文件各自的成功/失败如实报告。

选择独立 strict JSON emission input，不修改 `pietto.toml` 的历史default-dialect提案，
不复用可执行 Python 配置；其当前loader没有已实现的 default SQL target。
D66.13仅替代旧 `project-cli-json-v2.md` 中尚未实现的future project emit设计
（postgres-only、无module的whole-project artifact）；已实现check JSON v2保持原契约。
本期selected lowering仍要求whole-project semantic success，不授予partial-error政策。
Semantic Metadata Artifact v1仍single-file且不含dialect/connector arguments；新产物不回填它。
选择closed typed SQL AST加独立verifiers，放弃直接字符串拼接为唯一表示；其成本是一次
显式结构及event遍历，换取绑定/参数/range的可核验性。复用legacy输出安全原语，只在
新mode边界扩展保护对象；不把ScriptIR emitter拉回neutral plan。

### Emission input v1

`FILE` 为相对explicit project root的normalized project-relative路径，拒绝absolute/escaping路径；
通过现有contained regular-file/trusted opened bytes模式读UTF-8，
禁止symlink/非regular/越界、duplicate JSON keys、BOM、trailing data和未知字段。
输出不得覆盖configuration、source、contract或其hard/symbolic alias。读取一次后保留
原accepted bytes及其已有内容身份规则，不在verifier重新打开文件。
JSON对象顺序不赋予权威，数组顺序保留；所有整数ordinal禁止Bool冒充。

顶层恰为 `format,target,sources,environment`；`format="pietto.emission-contract.v1"`。

| Field | Closed input shape / meaning |
| --- | --- |
| target | `{family, release}`；family恰为postgres/mysql，release是显式reviewed target release；初始allowlist恰为(postgres,18.6)、(mysql,8.4.12)。结构合法但allowlist外的release为BLOCKED / PIE-B1003 / exit1，cli_errors为空；malformed release为INPUT_REJECTED / emission_contract_schema / exit2，不自动沿用规则。CLI/file family重复仅可相同，否则INPUT_REJECTED；无隐藏优先级。distribution不是此semantic target字段。 |
| sources[] | `{selector, relation, scan, fields, premises}`；描述当前项目的source occurrence，全部先做structure/duplicate/selector校验；只对selected dependency/evidence closure评估target applicability。 |
| selector | `{module, kind, name}`；kind恰为source，当前logical module、declaration kind/name的唯一exact occurrence。不能以locator或physical name选语义源。 |
| relation | `{namespace, name}`；两个非空identifier components，PG namespace是schema、MySQL namespace是database。内部quoted identifier节点分别编码；文本中的点不拆分，不接connection或SQL。 |
| scan | `"relation_rows"`；声明该relation实际暴露的整个row domain正是逻辑源，包括inheritance/partition/view的实际范围；首版不添加ONLY或过滤来猜测另一domain。 |
| fields[] | `{ordinal, name, column, representation}`；ordinal为source schema的zero-based field occurrence，name作logical一致性校验，column为独立physical identifier component；完整selected source schema按原序映射，重复ordinal或physical column冲突拒绝；name不是canonical field identity。 |
| representation | `{storage, nullable, domain}`；storage是下文V01–V06的closed physical type，不是SQL类型字符串；nullable取true/false/unknown，必须与上游实际NULL/evidence相容；domain为对应tag的exact值域前提，不解释表达式。 |
| premises[] / environment[] | `{key, scope, value}`；scope恰为statement、source(selector)、expression(现有source occurrence及context reference)。每个key有closed typed value与允许scope，不接受自定predicate、`rule_correct`、任意SQL/settings对象。 |

input v1 的初始premise keys只有：`row_domain_matches`、`read_only_object`、
`value_domain`、`encoding`、`collation`、`padding`、`comparison_prefix_bytes`、
`session_sql_mode`、`session_time_zone`、`client_encoding`、`identifier_case`、
`parameter_protocol`、`operator_environment`、`resource_limits`。前两项仅source scope；
value/encoding/collation/padding/prefix可source/field-expression scope；session/client/protocol/
operator/resource为statement scope。expression selector只能指当前plan已有site/context，
无法唯一绑定则拒绝。初始协议closed为PG extended `$n`或MySQL prepared `?`。
`read_only_object` 只声明物理对象访问前提，不认证任意view/function的效果或lowering正确性。
不存在可声明或覆盖upstream key/FD/proof的input字段。

例如，以下是未来一字段source的完整最小input（不是本次已执行的fixture）：

```json
{
  "format": "pietto.emission-contract.v1",
  "target": {"family": "postgres", "release": "18.6"},
  "sources": [{
    "selector": {"module": "models/main.pietto", "kind": "source", "name": "items"},
    "relation": {"namespace": "fixture", "name": "items"},
    "scan": "relation_rows",
    "fields": [{
      "ordinal": 0, "name": "id", "column": "item_id",
      "representation": {
        "storage": {"kind": "pg_int8"}, "nullable": false,
        "domain": {"kind": "int_range", "min": "0", "max": "100"}
      }
    }],
    "premises": [
      {"key": "row_domain_matches", "scope": "source", "value": true},
      {"key": "read_only_object", "scope": "source", "value": true}
    ]
  }],
  "environment": [
    {"key": "client_encoding", "scope": "statement", "value": "UTF8"},
    {"key": "operator_environment", "scope": "statement", "value": "builtin_only"}
  ]
}
```

source内`scope="source"`绑定其唯一enclosing selector；顶层source scope须为
`{kind:"source",selector:...}`，expression scope为`{kind:"expression",source:...,site:...,context:...}`，
site/context是当前plan inspection的局部references，不能来自另一snapshot。
storage是closed对象：`kind`取pg_int2/pg_int4/pg_int8/pg_bool/pg_text/pg_numeric/
pg_timestamp/pg_uuid/pg_float8或my_smallint/my_int/my_bigint/my_bool01/my_varchar/
my_decimal/my_datetime/my_uuid_bytes/my_double。仅numeric/decimal另要求precision/scale，
varchar另要求length，timestamp/datetime另要求fractional_seconds=6；未知key拒绝。
domain仅允许int_range(min/max十进制文本)、bool01、text(max_characters整数、encoding/
collation/padding明确值)、decimal(precision/scale)、timestamp(固定V05域)、uuid(standard_bytes)、
finite_float(binary64)；每个tag只接自身列出的字段，NULL由独立nullable控制。
没有任意SQL type或任意JSON predicate逃生口。结构全量验证后，仅被实际规则使用的environment
维度成为必需；未使用dimension不强行提升为runtime要求。

同一scope/key所有声明须一致；statement要求与所用source/expression需求按key的适用关系
统一检查。source A、B有不同合法collation不自动全局冲突，但若某比较要求同一collation，
必须有独立适用规则；两条规则要求同一session setting为不同值则BLOCKED。
选中源缺描述BLOCKED；未选源的合法不适用target描述不污染选中结果。所有重复、歧义、
非法结构即使在unused源上也INPUT_REJECTED。声明与Slice2+实际observation分列，编译器不验证
数据库实例，不把文件中`true`当执行证明。

input hard ceilings：1 MiB accepted UTF-8 contract、4096 source descriptions、32768 field
mappings、128 JSON nesting；超限为完整typed input failure。emission hard ceilings：8 MiB SQL、
16 MiB公共artifact、32768 generated nodes和32768 parameter occurrences；同时服从actual
selected target更低的columns/windows/nesting/protocol限制。`resource_limits`只能声明更低
环境能力，不能提高compiler hard ceilings；不能截断或拆多statement绕过。数值为本期有限
资源设计，第一implementing Slice必须测试边界；不是已测性能承诺。

### Finite physical domains

这些是规则的共同前提，不是全语言强制存储映射。logical type/原TypeExpr/Decimal parents、
physical input/result以及每次conversion都留下独立链；派生结果还须通过相同规则，不能只查扫描。

| Domain | Logical and physical contract | Positive minimum / rejected boundary |
| --- | --- | --- |
| V01 | builtin Int；PG int2/int4/int8或MySQL signed SMALLINT/INT/BIGINT，declared range必须落在实际storage与所用operation的精确范围。无默认Int→BIGINT。 | 0、1、9007199254740993在已声明int8域可投影/绑定；超范围或unsigned混合缺适用rule拒绝。 |
| V02 | builtin Bool；PG boolean；MySQL signed TINYINT只允许0/1，必要时另含NULL；logical Bool必须在比较/分组/quotient前保持该域。 | NULL/0/1 scalar与TRUE-only filter；domain含2不获Bool realization。 |
| V03 | builtin Text；PG text+UTF8+exact C comparison，MySQL VARCHAR(n)+utf8mb4+utf8mb4_0900_bin+NO PAD；n明确，原文value含U+0000的跨target域不承诺。字节/字符长度与scope显式。 | 空串、尾空格、非BMP及`a`/`A`不同值保持；PAD SPACE、其他collation、失配encoding/prefix缺exact rule阻止相应比较，不能事后decode修正。 |
| V04 | 已验证Decimal(p,s)，首版共同域1≤p≤65、0≤s≤min(p,30)，PG numeric(p,s)/MySQL DECIMAL(p,s)，原logical parameters必须吻合；每个aggregate/SET输出重新检查实际p/s/rounding，不推导或补猜。 | Decimal(9,2)原值scan/比较；跨parents/错误scale拒绝。SUM/AVG并非因此普遍开启，R13给独立边界。 |
| V05 | 有完整既有逻辑证据的Timestamp/UUID只允许representation-preserving scan/projection：PG timestamp without time zone(6)/uuid；MySQL DATETIME(6)/BINARY(16)，UUID为标准16字节顺序，无byte-swap。Timestamp共同域有效Gregorian 1000–9999、microsecond、无时区转换。 | matching声明下原值及NULL传递；timezone/precision/byte-order不明或需要未批准比较转换BLOCKED。不能从名称自行推导logical时间/UUID语义。 |
| V06 | builtin finite Float：PG double precision/MySQL DOUBLE，仅IEEE binary64 exact fixed transport/projection，保留tag、signed zero和unary structure；非finite值或需未批准row equivalence的操作不支持。 | 1.5和正负零transport；DISTINCT/equality-required SET的Float仍由上游既定边界拒绝。 |

Any/Bytes/Json/Date及nominal alias/enum或其他representation组合没有本版promise，明确
APPROVED_NON_SUPPORT；不能悄悄归入某builtin。V05不新增logical solver：输入缺实际上游意义
属于MISSING_EVIDENCE，不以自定timezone/UUID comparator消除缺口。
上述条件约束支持域；在满足已承诺条件的真实case失败则是待归因defect，不能临时缩域。

### Closed outcomes, public artifact and invalidation

内部路径为 validate input → bind current selectors → check VERIFIED plan/policy/envelope
→ match original demands and rules → build SQL AST → independently verify correspondence
→ render events/bytes → independently verify bytes/ranges/uses → publish VERIFIED artifact。
检查能继续时收集全部错误；结构错误使某子项不可解释时保留该root错误及其它可检查项，
不编造子项语义。顺序为原project diagnostics、input occurrence、selected plan需求顺序、
generated structural order；相同文字的不同occurrence不去重。

| Outcome | Payload | Public behavior |
| --- | --- | --- |
| INPUT_REJECTED | 完整结构/selector/root/policy/contract错误，logical paths，无host秘密 | 无artifact；usage/config/read/write错误exit2；不伪造PIE diagnostic。 |
| BLOCKED | exact target/representation/non-support/missing/conflict/enforcement/resource blocker及原diagnostics | 无SQL成功字段/文件；编译拒绝exit1；保留原semantic code，使用下述新增emission诊断，不重定义legacy PIE-B1000或原诊断对象。 |
| VERIFIED | exact runtime root + SQL AST + final bytes + fixed mapping + result/ranges + realized requirements | compiler成功exit0，WARNING可存在；I/O失败仍非成功，无partial artifact冒充VERIFIED。 |

### Public envelope schema

新公共格式 `pietto.sql-emission.v1` 是按status选择唯一branch的closed tagged union。
以下每行只约束自己的branch，未知、额外、缺失字段均拒绝，不把success字段强加给failure。

| Branch | Exact top-level keys | Required values and absent payload |
| --- | --- | --- |
| VERIFIED | format,status,target,request,sql,fixed_values,parameter_uses,columns,ranges,requirements,diagnostics | format固定；status为VERIFIED；target/request为objects，sql为string，其余payload与diagnostics为arrays；artifact/blockers/cli_errors不存在。 |
| INPUT_REJECTED | format,status,artifact,blockers,diagnostics,cli_errors | format固定；status为INPUT_REJECTED，artifact:null；后三项为完整arrays，cli_errors非空；sql/target/request及成功payload字段不存在。 |
| BLOCKED | format,status,artifact,blockers,diagnostics,cli_errors | format固定；status为BLOCKED，artifact:null，cli_errors为空；blockers或原ERROR diagnostics至少一项非空；sql/target/request及成功payload字段不存在。 |

只有VERIFIED branch可写artifact文件；failure没有候选AST/SQL/values/ranges/realization payload。
blocker record恰为`code,reason,subject,location,related`，code/reason对应下面PIE-B1001–PIE-B1008；
subject是可用的logical source/input/plan occurrence说明或null，location用已有public坐标形状，
related保留完整有序related locations。原runtime blocker roots保持在runtime product，public
投影不把名字当重新获取该root的凭证。diagnostics复用既有对象/顺序/public shape。
CLI error record恰为`kind,message,path`；kind/message为string，path为normalized logical path
或null，绝对root与用户原input值不回显。新family允许的kind为usage、unsupported_dialect、
project_root、config_read、config_parse、config_schema、project_path、project_glob、
project_resource、source_read、output_path、output_write、emission_contract_read、
emission_contract_schema、emission_selector，沿input/processing顺序保留所有可检查错误。
INPUT_REJECTED exit2，BLOCKED exit1，VERIFIED且I/O成功exit0；I/O错误按INPUT_REJECTED输出，
已有目的文件按atomic-write契约保留。stdout写失败不能保证还可输出完整error document。
这不是扩充legacy `{kind,name,sql}`或project check JSON v2对象。

Slice3首次公共artifact序列化即有独立data-only decoder/consumer，检查三个branch、SQL UTF-8
ranges与slot/use mapping，并将解码的exact SQL/params交给test adapter；不能把decoded数据
当runtime plan继续lower。Slice13 installed CLI/text/file复用此consumer核对真实序列化输出、
原file bytes及no-candidate-SQL失败。公共消费不等待Slice14的private AST decoder。

冻结未来新增emission codes：PIE-B1001 SOURCE_REALIZATION、PIE-B1002 REPRESENTATION、
PIE-B1003 UNSUPPORTED_RULE、PIE-B1004 MISSING_EVIDENCE、PIE-B1005 PREMISE_CONFLICT、
PIE-B1006 UNFULFILLED_REQUIREMENT、PIE-B1007 TARGET_RESOURCE、PIE-B1008 ARTIFACT_INTEGRITY。
各 implementing Slice首次公开对应code前须在当次allowlist中包含diagnostic registry/测试；
Slice1只记录planned codes，不修改现有registry。内部malformed API root抛原typed错误；public
boundary转成完整失败，不泄露traceback。contract input/read/path结构错误仍是CLI error，
`emission_contract_read`/`emission_contract_schema`/`emission_selector`为新family独有kind。

`request`保留logical owner、已接受source content identities、normalized emission input及policy；
`target`保留family/release与已声明semantic environment，不捏造server build。
`sql`是exact UTF-8 bytes的无BOM文本映射；公共序列化的JSON escaping在解码后恢复该文本，
不能按JSON文件字节偏移解释SQL ranges。`fixed_values`按logical slot序为tagged records：
Bool用JSON boolean；Int用canonical十进制字符串；Float用有限binary64 hex字符串（含signed
zero）；Text用精确Unicode字符串。不是调用者可写的rebind template。
`parameter_uses`按SQL token发生序保留`use,slot,server_index,physical_type,range`，PG兼容context
才共享index；MySQL每个`?`独立index。`columns`是positional数组，保留ordinal/label/logical type/
nullability/physical representation与canonical result correspondence，不按name建字典。
`ranges`为zero-based half-open UTF-8 byte intervals，保留source-role/occurrence与generated cause；
完整AST、索引及内部对象图只在private `pietto.sql-emission-observation.v1`中暴露（Slice14）。
公共`requirements`只记录两denominators的有序条目、rule、premise引用及realization disposition，
不把全private upstream graph序列化。两格式都source/value-bearing，不自动redacted或authenticated。

SQL AST与text错配、range不在UTF-8边界、wrong slot/server index、过期contract/root、重复或缺失
requirement、无独立根的justification cycle均不能产生VERIFIED。source、owner、policy、envelope、
contract、target或semantic environment任何相关变化都要求新target artifact/fresh verification；
无persistent cache。本文不把checksum等同正确性或source真实性。

## Three exclusive asset ledgers

这里分类的是asset责任，不是三个可叠加的成功标志。I是已完成的输入，T是66新增交付，
L是后来owner尚未交付的asset。L内MINIMUM_NOW/CONTRACT_ONLY_NOW只描述与T的当前接缝，
不把同一个future asset再登记为已实现。CORE_NOW只用于66自身工作；分类不授予未来写权限。

### INHERITED_CLOSED

| Asset | Existing authority | Reuse boundary |
| --- | --- | --- |
| I01 | completed semantics/whole-project diagnostics/EXPLICIT_MODULES | 只接受当前exact成功root，保留全部诊断。 |
| I02 | Project/Query-block IR及独立verification | active output、dependency/use schedule不按名字重建。 |
| I03 | ProjectSQLPlan source/SELECT/SET/use/terminal graph | 所有reused/rebound/completed/SET concrete variants及typed terminals。 |
| I04 | row/JOIN/nulling/group/window/QUALIFY/result/SET semantics | 不修改legality/FD/grain/type/effect；F01–F06来源链。 |
| I05 | typed fixed literals/envelope/eligibility | default PRESERVE与explicit BIND原值，slot不是SQL位置。 |
| I06 | complete plan demand/obligation report | 原denominator和LEGAL_UNPROVED，不要求整个65 assessment已positive。 |
| I07 | forward/reverse source maps | 保留parser字符坐标、所有roles与ancestry，尚无SQL offsets。 |
| I08 | capability/provider/target assessment | 原始Found/Absent/Unknown/Conflict、适用范围，不认证lowerer或实例。 |
| I09 | portable/pure correspondence及F65S15-01/F65S15-02修复 | 数据一致性不恢复runtime roots，不重开65 audit。 |
| I10 | legacy ScriptIR SQL/CLI/public JSON/package0.1.0 | 保持当前行为；新mode不能偷换既有artifact或infer dialect。 |
| I11 | repository facts、sole lifecycle/inventory readers | 新principal只读自身/immutable引用及真实source entrypoints。 |
| I12 | compiler/process acquisition/installed/golden gates | 保持八family当前denominator及旧域；现有process设施不是DB harness。 |

### TRANSFERRED_TO_PHASE66

| Asset | Classification | New delivery / owner |
| --- | --- | --- |
| T01 | CORE_NOW | source realization input和exact logical→physical binding，03首次，13 CLI。 |
| T02 | CORE_NOW | closed dialect AST、capture-free SQL scopes/names/terminals，03–04。 |
| T03 | CORE_NOW | fixed values/type anchors/server parameter-use map，05；后续每条规则扩展。 |
| T04 | CORE_NOW | row scalar/LET/WHERE/ON finite lowering，06。 |
| T05 | CORE_NOW | JOIN/EXISTS及restricted PG FULL/MySQL negative，07。 |
| T06 | CORE_NOW | GROUPED/GLOBAL/satisfying及aggregate physical results，08。 |
| T07 | CORE_NOW | admitted windows/named uses/QUALIFY，09。 |
| T08 | CORE_NOW | DISTINCT/ORDER/LIMIT与六SET形式、operand boundaries，10–11。 |
| T09 | CORE_NOW | 完整artifact、result correspondence、双denominator、bytes/ranges验证；03即时，12整合。 |
| T10 | CORE_NOW | usable installed Project emit-SQL/public versioned output与legacy compatibility，13。 |
| T11 | CORE_NOW | private observation/process/relocation/wheel消费者，14；expanded differential，15。 |
| T12 | CORE_NOW | isolated target facility与minimum real observations，02首次；03起new pipeline；16仅audit/handoff。 |

### RETAINED_LATER: every Phase67–97 atom

每个分号项都是独立atom，带自己的classification和理由；Owner列是其确切后续owner。
MINIMUM_NOW不代表此后续phase已实施；本期只做括号中有即时consumer的最小接缝。
91–97全部 **TENTATIVE / OWNER ONLY**。

| Asset | Exact later owner | Atoms: classification and reason |
| --- | --- | --- |
| L67 | Phase67 result/interchange | Arrow interchange foundation: DEFER_BY_NECESSITY，缺Arrow result/buffer层；Pietto result contract: MINIMUM_NOW，T09先给positional type/null/result correspondence，正式API/batches/lifetime归67。 |
| L68 | Phase68 execution | executor SPI: CONTRACT_ONLY_NOW，接收已验证artifact；ADBC: NO_CURRENT_USE，无driver consumer；DBAPI: MINIMUM_NOW，仅T12隔离测试adapter，产品接口仍68；connection/session/transaction: DEFER_BY_NECESSITY，编译零资源；streaming: DEFER_BY_NECESSITY，无产品result stream；cancellation: MINIMUM_NOW，仅test-owned timeout/close；backpressure: DEFER_BY_NECESSITY，有限测试观察不等于产品流控；runtime enforcement: CONTRACT_ONLY_NOW，LEGAL_UNPROVED不可waive。 |
| L69 | Phase69 alpha/entrypoints | public alpha release engineering: CONTRACT_ONLY_NOW，交付证据不等于release；unified safe entrypoints: MINIMUM_NOW，T10显式emit是本期真实入口，统一其它命令归69；partial-error policy: DEFER_BY_NECESSITY，whole-project ERROR政策保持。 |
| L70 | Phase70 open/composite plans | open/composite plans: CONTRACT_ONLY_NOW，closed artifact可交接；authored nonrecursive CTE: DEFER_BY_NECESSITY，generated CTE仅T02形式；authored subqueries: DEFER_BY_NECESSITY，同上；VALUES: NO_CURRENT_USE，无新syntax；table functions: NO_CURRENT_USE，无函数执行；outer captures: DEFER_BY_NECESSITY，无新resolution；authored EXISTS: DEFER_BY_NECESSITY，T05 generated EXISTS消费既有SEMI/ANTI；IN: NO_CURRENT_USE，不替代ANTI；LATERAL: NO_CURRENT_USE，无open captures；bounded decorrelation: DEFER_BY_NECESSITY，无rewrite搜索；effect authority: CONTRACT_ONLY_NOW，未知effects阻止需要它的转换；caller rebind: DEFER_BY_NECESSITY，本期fixed原值。 |
| L71 | Phase71 nested relation | NestedRelation: CONTRACT_ONLY_NOW，flat结果不推导nested语义；Collect: NO_CURRENT_USE，无collect算子；Unnest: NO_CURRENT_USE，无nested输入；flatten: NO_CURRENT_USE，无shape改写；outer/inner grain: CONTRACT_ONLY_NOW，保留现有grain而不新增；nested Arrow: DEFER_BY_NECESSITY，需67和nested语义。 |
| L72 | Phase72 types/equality | advanced equality: CONTRACT_ONLY_NOW，predicate/row/peer比较分开；advanced types: MINIMUM_NOW，T03/T09保留精确representation链，不新增solver；nullability: MINIMUM_NOW，T05实际outer nulling及V02；temporal relationships: DEFER_BY_NECESSITY，缺语义；range relationships: DEFER_BY_NECESSITY，窗口RANGE不授予relationship；ASOF: NO_CURRENT_USE，无ASOF节点；Float row equivalence: DEFER_BY_NECESSITY，finite transport不能解除原延后。 |
| L73 | Phase73 aggregate algebra | aggregate algebra: CONTRACT_ONLY_NOW，T06不发明equations；aggregate state: DEFER_BY_NECESSITY，无state API；grouping extensions: DEFER_BY_NECESSITY，只有既有GROUPED/GLOBAL；fanout-safe reaggregation: DEFER_BY_NECESSITY，不通过MIN/MAX/ANY_VALUE修复风险。 |
| L74 | Phase74 local assets/SPI | reusable local semantic assets: CONTRACT_ONLY_NOW，保留原dependency身份；derived relationships: NO_CURRENT_USE，不猜路径；function SPI: NO_CURRENT_USE，不增call语义；plugin SPI: NO_CURRENT_USE，无dynamic registration。 |
| L75 | Phase75 language tools | formatter: NO_CURRENT_USE，不改authored文本；LSP: CONTRACT_ONLY_NOW，消费T09 ranges；editor: CONTRACT_ONLY_NOW，SQL bytes与parser/editor单位有别；diagnostics tooling: MINIMUM_NOW，T09/T10提供原source对应；syntax editions: NO_CURRENT_USE，无新syntax；migrations: CONTRACT_ONLY_NOW，新format独立不隐式迁移旧CLI。 |
| L76 | Phase76 PostgreSQL depth | PostgreSQL deep adaptation: MINIMUM_NOW，本期18 finite baseline含restricted FULL，extensions、复杂类型与优化深度不由baseline承诺。 |
| L77 | Phase77 MySQL depth | MySQL deep adaptation: MINIMUM_NOW，本期8.4 finite baseline及FULL negative，更广session/feature/representation组合归77。 |
| L78 | Phase78 SQLite | SQLite deep adaptation: NO_CURRENT_USE，无本期target或driver，neutral portability不证明支持。 |
| L79 | Phase79 DuckDB | DuckDB deep adaptation: NO_CURRENT_USE，无本期target，BY NAME/ASOF不进入本期。 |
| L80 | Phase80 data science | pandas: CONTRACT_ONLY_NOW，先保留BAG/NULL/types；Polars: CONTRACT_ONLY_NOW，同一result接缝；NumPy: CONTRACT_ONLY_NOW，不用array dtype作语义；SciPy: NO_CURRENT_USE，无数值执行；Matplotlib: NO_CURRENT_USE，无绘图consumer。 |
| L81 | Phase81 assurance | high-intensity real-DB: MINIMUM_NOW，T12两target最低真测，本owner负责扩大规模；differential: MINIMUM_NOW，T11独立corpus；metamorphic: MINIMUM_NOW，T11限定变形关系；fuzz: DEFER_BY_NECESSITY，不建随机平台；performance assurance: CONTRACT_ONLY_NOW，记录耗时/上限不作未测SLA。 |
| L82 | Phase82 public freeze | public schemas: CONTRACT_ONLY_NOW，本期独立version；API: CONTRACT_ONLY_NOW，私有root不公开；CLI: CONTRACT_ONLY_NOW，新增mode有限承诺；syntax: NO_CURRENT_USE，无authored变化；support-matrix freeze: CONTRACT_ONLY_NOW，本期finite规则不等于1.0全集。 |
| L83 | Phase83 stable release | stable1.0 audit: CONTRACT_ONLY_NOW，E01–E10向后交接；publication: NO_CURRENT_USE，本期无tag/release/package publish。 |
| L84 | Phase84 remote/trust | remote assets: NO_CURRENT_USE，本地trusted inputs；registry: NO_CURRENT_USE，无lookup；transport: NO_CURRENT_USE，无remote load；signing: NO_CURRENT_USE，无attestation；trust: CONTRACT_ONLY_NOW，byte identity不等于semantic correctness。 |
| L85 | Phase85 dependency resolution | dependency solver: NO_CURRENT_USE，不选版本；canonical lockfile: CONTRACT_ONLY_NOW，现有uv.lock是开发依赖lock，非产品solver；reproducible resolution: CONTRACT_ONLY_NOW，沿用现有package identity。 |
| L86 | Phase86 domain/device | RDKit: NO_CURRENT_USE，无domain runtime；geospatial: NO_CURRENT_USE，无spatial规则；sparse: NO_CURRENT_USE，无sparse输出；DLPack: DEFER_BY_NECESSITY，需result/device层；device-framework adapters: DEFER_BY_NECESSITY，编译无设备资源。 |
| L87 | Phase87 catalog/data quality | catalog: CONTRACT_ONLY_NOW，显式声明不进行production introspection；constraints: MINIMUM_NOW，只检查T01/T05实际所用原proof的physical applicability；statistics: NO_CURRENT_USE，无cost search；runtime data quality: DEFER_BY_NECESSITY，不扫描生产数据验证声明；chase: NO_CURRENT_USE，不建solver。 |
| L88 | Phase88 logical optimizer | logical optimizer memo: NO_CURRENT_USE，closed dispatch已足够；join-order search: NO_CURRENT_USE，保留authored order；hypergraph search: NO_CURRENT_USE，无新优化问题。 |
| L89 | Phase89 physical strategies | Yannakakis: NO_CURRENT_USE，无physical算法；WCOJ: NO_CURRENT_USE，同上；Free Join: NO_CURRENT_USE，同上；predicate transfer: NO_CURRENT_USE，不推predicate越过barrier；materialization strategy: CONTRACT_ONLY_NOW，T02共享identity不承诺once。 |
| L90 | Phase90 profiling-driven native work | Rust kernels: NO_CURRENT_USE，无profiling依据；PyO3: NO_CURRENT_USE，无native模块；maturin: NO_CURRENT_USE，保留当前build；parity: CONTRACT_ONLY_NOW，T11可供未来独立实现；wheel matrix: CONTRACT_ONLY_NOW，本期Python wheel证据不等于native wheel支持。 |
| L91 | Phase91 TENTATIVE / OWNER ONLY | persistent incremental-cache identity: CONTRACT_ONLY_NOW，仅T09 invalidation边界；incremental Project IR: NO_CURRENT_USE，无persistent更新；differential Project IR: NO_CURRENT_USE，无增量算法。 |
| L92 | Phase92 TENTATIVE / OWNER ONLY | recursive relations: NO_CURRENT_USE，graph必须acyclic；fixpoints: NO_CURRENT_USE，无迭代语义；iterative planning: NO_CURRENT_USE，无循环构造；bounded recursive provenance: CONTRACT_ONLY_NOW，不丢失当前finite lineage。 |
| L93 | Phase93 TENTATIVE / OWNER ONLY | formal rewrite certification: CONTRACT_ONLY_NOW，独立有限verifier不自称formal proof。 |
| L94 | Phase94 TENTATIVE / OWNER ONLY | cloud semantics: NO_CURRENT_USE，无cloud资源；federation semantics: CONTRACT_ONLY_NOW，同family不证明同connection；federation planning: NO_CURRENT_USE，无跨源搬运；transport: NO_CURRENT_USE，无网络执行。 |
| L95 | Phase95 TENTATIVE / OWNER ONLY | DML: NO_CURRENT_USE，closed AST拒绝；DDL: NO_CURRENT_USE，只有test fixture管理可另获授权；migrations: NO_CURRENT_USE，无产品写执行。 |
| L96 | Phase96 TENTATIVE / OWNER ONLY | governance: NO_CURRENT_USE，无policy产品；security policy semantics: CONTRACT_ONLY_NOW，普通输入安全/least privilege不创造语言策略。 |
| L97 | Phase97 TENTATIVE / OWNER ONLY | continuous query semantics: NO_CURRENT_USE，有限BAG；streaming query semantics: NO_CURRENT_USE，不能与68 finite-result streaming混同。 |

## Handoff reconciliation

H/Q来自65 completion handoff，本文独立回答，不沿用其UNAPPROVED状态作新phase答案。

| Input | Actual entrypoint or carrier | Phase66 consumption / first owner |
| --- | --- | --- |
| H01 | `src/pietto/_project/project_sql_plan.py::build_project_sql_plan` | exact completed/bundle/owner/policy/envelope→03；不以bindings-only或IR VERIFIED代替whole plan。 |
| H02 | `src/pietto/_project/project_sql_plan_inspection.py::ProjectSQLPlanInspection.input_terminals` | source/SELECT/SET immediate terminal/use→03/04/11，不split locator。 |
| H03 | `src/pietto/_project/project_sql_plan_inspection.py::ProjectSQLPlanInspection.stage_context` | scalar/JOIN/group/window/result原stage→06–11，保持所有载体。 |
| H04 | `src/pietto/_project/project_sql_plan_verification.py::verify_fixed_literal_envelope` | logical slots、contexts及fixed原值→05，SQL occurrence另建。 |
| H05 | `src/pietto/_project/project_sql_plan_requirements.py::build_project_sql_requirement_report` | 每项原需求→03起即时，12合并两个独立denominators。 |
| H06 | `src/pietto/_project/project_sql_plan_source_maps.py::build_project_sql_source_map` | source角色/字符坐标→03起generated events/ranges，12查询。 |
| H07 | `src/pietto/_project/project_sql_plan_target_assessment.py::build_project_sql_target_assessment` | raw scoped evidence→03；complete positive不是前置，因为66负责实现残余项。 |
| H08 | `src/pietto/_project/project_sql_plan_portable.py::verify_project_sql_plan_portable` | 保持原runtime correspondence；14新增private observation与实际process消费者。 |

| Question | Adopted answer | Deciding rules |
| --- | --- | --- |
| Q01 | 18/8.4 family下仅18.6/8.4.12初始reviewed release pairs；channel/build/pins分开 | D66.02 R01–R26 |
| Q02 | explicit component input、exact source selectors、无ambient connection | D66.03–.04 R01 R02 |
| Q03 | capture-free scope checker、exact physical anchors/use maps | D66.06 .10 R03 R04 |
| Q04 | hidden STRICT-FD ORDER首版明确拒绝 | D66.08 R20 |
| Q05 | 原facts、declared环境、implemented strategy、observed结果各自保留 | D66.11 .15 R23 R25 |
| Q06 | 未履行必要enforcement/realization阻止SQL成功，普通risk不能被误判为义务 | D66.01 .11 R23 |
| Q07 | 显式project emit mode/input/public artifact，legacy不改 | D66.13 R24 |
| Q08 | UTF-8 ranges对最终bytes、独立完整target oracle | D66.12 .15–.16 R23 R25 R26 |

## Finite rule and support ledger

`PLANNED`是本phase须实施和验证的promise；`APPROVED_NON_SUPPORT`是本文明确首版边界；
`MISSING_OBSERVATION`表示规则承诺尚无target执行收据，不能当PASS或改成non-support；
`PROMISED_DOMAIN_DEFECT`表示满足promise前提的case失败，需保留并归因。
当前所有PLANNED行的target执行状态均MISSING_OBSERVATION。每行最低positive和negative都须
由其completing Slice的真实新pipeline/独立oracle完成；R25在02先用legacy/独立SQL。
negative源若本来已被semantic/plan拒绝，应保留原boundary，不伪造lowerer运行。

PG=PostgreSQL18 family的reviewed release18.6，MY=MySQL8.4 family的reviewed Docker security release8.4.12；V域与coherent request是下列所有规则的前提。
这两个release label不声称跨channel相同server package或实际build已经观察到；Slice2须证明
所获distribution/index/platform与actual server build属于相应reviewed target，不能静默接受
另一个reported version。扩大release allowlist需要新的明确review/rule/target证据。
首版环境固定test session，不以optimizer_switch调参绕过红例。新实现每个CAST、helper、
correlation、parameter、order/window结构必须登记generated requirement与原cause。

| Rule | Target/environment | Plan shape and type premises | Strategy / disposition | Generated requirements | Minimum positive witness | Violated-premise negative witness | Completing Slice |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R01 | PG/MY，explicit同family source | exact VERIFIED selected closure、完整source mappings、relation_rows实际domain | PLANNED：结构化qualified scan、显式projection | namespace/scan domain/read-only object/field representation | 单source Int字段两行含重复，投影保留两行 | missing source、stale root、other-family或错误inheritance domain阻止；unused合法target差异不影响 | 03 |
| R02 | PG/MY，V01–V06 | 每个source/result边界的logical/physical/type/null完整链 | PLANNED：有限representation-preserving mapping；conversion只有对应exact rule | encoding/range/p/s/null/collation，used proof applicability | signed Int、Bool0/1/NULL、Text尾空格、Decimal(9,2)扫描；有意义证据的V05/V06传递 | Bool2、unsigned mismatch、Decimal参数猜测、timezone/UUID顺序不明；Float row-equivalence拒绝 | 03/05 |
| R03 | PG/MY，identifier length/case已声明 | named/shared DAG，各use exact immediate terminal，三类ORDER载体 | PLANNED：nonrecursive CTE/derived blocks、显式column lists、ordered internal names和binding check；按下述明确修订分期交付 | CTE可见域、physical namespace不被capture、case/length、effect/coupling适用性 | 04实际named chains与physical同名绑定；重复/shared JOIN见证07、三ORDER载体及ORDER/LIMIT sharing见证10、重复SET及双facade见证11 | CTE capture、长final label、foreign port、循环；未知effects且rule要求复制时阻止 | 04 named-chain；07/10/11 joint execution |
| R04 | PG extended `$n`；MY26.7 native prepared `?` | 原eligible Bool/Int/finite Float/Text literals，exact envelope/policy/context | PLANNED：每SQL use映射logical slot；精确type anchor；PG context兼容才复用index | 参数physical representation、token order、type/overload、use/range完整性 | 两个相等literal两个slot；一个slot多use；大Int、Float零和含问号/`%s`文本保持 | 错tag/value/sign/index、structural LIMIT绑定、coercion修复或SQL string计token拒绝 | 05 |
| R05 | PG/MY，适用V域 | 既有field/LET reference，typed literal、unary sign、+/-/*、comparison/NULL-test/and/or已准入树；算术需要原证据足以保证精确范围 | PLANNED：逐原树/precedence表达，stage值跨boundary用port；无constant folding | operator/type/range、literal anchor和阶段scope | Int 1+2、原LET后用两次、括号混合布尔表达式 | division/general calls、UNKNOWN type、无overflow/effect前提的变换阻止；不新增solver | 06 |
| R06 | PG/MY，V02 | scalar nullable Bool与WHERE/ON/satisfying/QUALIFY消费域分开 | PLANNED：scalar三值保留；仅predicate根消费TRUE | 三值operator真值、physical Bool域 | SELECT NULL Bool仍NULL，filter NULL不保留row | 内部IS TRUE/CASE把NULL变FALSE，physical2冒充Bool拒绝 | 06 |
| R07 | PG/MY，predicate适用 | exact CROSS或INNER pre-match scopes，R05/R06条件；保留base/refinement/ON | PLANNED：native CROSS/INNER ON，显式所有ports | matching comparisons、scope、multiplicity、原mandatory proofs | 2×2 CROSS四行；含duplicate/NULL的equality INNER | 用WHERE代替ON边界、post-null field或缺condition evidence拒绝 | 07 |
| R08 | PG/MY，predicate适用 | LEFT/RIGHT与accumulated-left完整nulling，原stage constants已形成ports | PLANNED：native LEFT/RIGHT，引用完整terminal输出 | per-port outer-nullability、match domain、typed conditions | LEFT未匹配right marker变NULL；多JOIN后RIGHT累计nulling | 把marker常量重算为1、漏前一次nulling或coalesced输出拒绝 | 07 |
| R09 | PG，builtin比较环境 | FULL条件仅非空有序AND，叶均为两输入直接V01同physical signed-integer type字段的builtin equality；无额外ON项 | PLANNED：native FULL，完整两侧terminal | equality hash/merge适用、NULL/multiplicity、两侧nulling、原single-match要求 | left[1,2,NULL] right[2,3,NULL]，五行及两个不同NULL未匹配行 | inequality/OR/同侧比较/任意ON/不适用type明确non-support | 07 |
| R10 | MY | 任意FULL | APPROVED_NON_SUPPORT：typed blocker，无通用emulation | blocker关联exact FULL cause | 相邻INNER/LEFT/RIGHT R07/R08真实positive，证明不是target全拒绝 | FULL equality也拒绝，无UNION/ANTI猜测替代 | 07 |
| R11 | PG/MY | SEMI/ANTI左output与right完整completed SELECT/SET/GLOBAL/window/LIMIT terminal；condition typed | PLANNED：EXISTS/NOT EXISTS包裹完整right terminal，不重写producer SELECT list | generated correlation/scope、right dependency、NULL TRUE matching、effect适用 | right LIMIT0；right GLOBAL空输入仍一row；right SET结果和LIMIT1影响membership | base-table shortcut、NOT IN、删right LIMIT/GLOBAL/SET、right output漏到左schema拒绝 | 07 |
| R12 | PG/MY，MY保留ONLY_FULL_GROUP_BY | 原GROUPED/GLOBAL/group keys、satisfying及exact result ports | PLANNED：native grouping，先计算已建立stage；post-group predicate消费result | GROUP BY expression/column binding、NULL-equal keys、合法selected outputs | empty GROUPED零组，empty GLOBAL count为0；satisfying筛选已成aggregate值 | 仅semantic FD不满足backend grouping、额外key/ANY_VALUE/MIN/MAX修复拒绝 | 08 |
| R13 | PG/MY | count()/count(V01 nullable field)/count_distinct(V01)、min/max(V01 direct field)；count结果在signed64域 | PLANNED：COUNT(*)/COUNT(column)/COUNT(DISTINCT column)/MIN/MAX，逐实际结果representation；SUM/AVG及未reviewed promotion组合为APPROVED_NON_SUPPORT | aggregate result physical type/nullability、empty-input、count bound与distinct equality | [1,NULL,1]分别count*=3/countfield=2/countdistinct=1，empty MIN为NULL | countfield误当*；SUM/AVG产生numeric/DECIMAL而被当输入Int继续用必须typed blocker，无generic final CAST | 08 |
| R14 | PG/MY，V01 order/arguments；ranking Float结果仅V06传递 | 既有row_number/rank/dense_rank/ntile/percent_rank/cume_dist/lag/lead的准入签名、named/direct/copy/inherit政策 | PLANNED：对应native OVER和exact input，frame-insensitive policy仍保留evidence | order/peers/offset/default types、named binding、result representation | unique Int keys上的row_number与lag；重复keys的rank/dense_rank；单row分布值；ntile(2) | 错pre-window input、改变default/offset、invalid namespace或missing role拒绝 | 09 |
| R15 | PG/MY；MY不支持GROUPS/EXCLUDE | first_value/last_value/nth_value的既有effective frame；ROWS有限static bounds、RANGE current/unbounded；offset RANGE仅单non-null V01 key与非负Int static offset及精确算术前提；PG另允许原GROUPS/EXCLUDE | PLANNED：native exact frame；无语义证据时block affected combination | frame membership、peer比较、key/offset type/arithmetic、range keys数量；MY resource≤127 windows/SELECT | id=[1,2,3] ROWS1 preceding；单Int key RANGE1 preceding；PG GROUPS+EXCLUDE原membership | offset RANGE额外NULL discriminator key、负offset、MY GROUPS/EXCLUDE、缺arith evidence拒绝 | 09 |
| R16 | PG/MY | concrete window-use modifiers，与named template分开 | PLANNED：只允许RESPECT NULLS/FROM FIRST的已reviewed identity omission（PG无拼写）；MY可原生默认 | omission与effective semantics相同、modifier所属use | nullable lag/first_value与default一致 | IGNORE NULLS/FROM LAST明确APPROVED_NON_SUPPORT，不能反转ORDER伪装同一policy | 09 |
| R17 | PG/MY | 既有selected/hidden windows与QUALIFY exact post-window predicate | PLANNED：外层filter消费已建立window ports | hidden/value role、outer TRUE consumption、result columns映射 | hidden row_number<=1只导出id；selected window复用其结果 | 移到WHERE、重新compute或hidden进入visible schema拒绝 | 09 |
| R18 | PG/MY，V01–V04的适用row equivalence | DISTINCT恰为visible positional tuple，无Float比较或hidden quotient要求 | PLANNED：native DISTINCT位于原barrier | logical/physical row equivalence、NULL-equal/collation/Decimal parents | [1,1,NULL,NULL]→[1,NULL]（BAG两行） | 加hidden window/order/group值到tuple、忽略padding/prefix或Float强行比较拒绝 | 10 |
| R19 | PG/MY；NULL/order/collation posture明确可适用 | relation ORDER original typed items，三种carrier各保留input image；不靠aliases/ordinals | PLANNED：final returning SELECT实际ORDER；PG native NULLS；MY必要时仅relation/non-offset-window使用已验证NULL discriminator | ordering relation、NULL policy、scope、final bytes和tie允许集合 | final order显式实现；constant key先形成port不变成ORDER BY 1；nullable key两种policy分别观测 | inner CTE order当outer promise、猜omitted posture、alias capture、offset-RANGE追加key拒绝 | 10 |
| R20 | PG/MY | hidden STRICT-FD ORDER requirement | APPROVED_NON_SUPPORT：保留upstream PROVED并block realization | 原visible quotient/FD scope/root与blocker | visible-key ORDER R19为邻接正域 | hidden key不导出、不加DISTINCT、不representative/min/max/join-back | 10 |
| R21 | PG/MY | 原static LIMIT及operand-local/outer scope | PLANNED：明确relation boundary保留LIMIT；不flatten nested LIMIT | boundary/selection/order/effect、static constant与resource | ordered[1,2] LIMIT1后filter>1得空；filter先于LIMIT可得2 | LIMIT0删mandatory demand/error、误绑定structural literal或丢inner boundary拒绝 | 10 |
| R22 | PG/MY | 六SET forms；每列exact positional type/equivalence与operand完整terminal；V01–V04相同physical type及Decimal parameters；UNION ALL另可V06 | PLANNED：UNION/INTERSECT/EXCEPT ALL/DISTINCT，explicit nested derived boundaries，不依赖backend common-type猜测 | 逐SET column result type/NULL/collation、right membership、operand ORDER/LIMIT、nesting | A=[1,1,NULL],B=[1,NULL,NULL]六个独立BAG oracle，另测(left EXCEPT middle) EXCEPT right vs nested | names对齐、类型promotion被省略、Float equality、删EXCEPT right、嵌套LIMIT扁平化拒绝 | 11 |
| R23 | PG/MY | 完整AST/原report/生成需求/renderer events/exact bytes | PLANNED：独立plan→AST和events→bytes检查、闭合scopes/双denominator、range查询 | 每实际generated structure的premise及original cause，独立根无cycle；全部token/range覆盖 | multi-stage artifact每项都可追根，Unicode SQL bytes/ranges正确 | wrong SQL bytes/parentheses/params、两张清单互删、无root自证、range错单位拒绝 | 03起/12整合 |
| R24 | PG/MY，explicit contract/project/owner | 新公共artifact与唯一selected query | PLANNED：installed project emit、独立versioned output、atomic replace | source/input/output身份、public exact value encoding与完整diagnostics | installed console经独立public decoder生成完整可提交artifact，legacy byte/JSON回归保持 | conflicting target、ambiguous owner、unsafe output、BIND裸SQL、partial output成功拒绝 | 13 |
| R25 | 两exact targets，test-only隔离环境 | real fixture和independent oracle，先legacy/独立SQL，03起installed new pipeline | PLANNED：v2 native prepare/execute/binary terminal/close-send、complete results/metadata/diagnostics、same-session recovery、owned cleanup | actual server/build/adapter/pins/env/role及完整manifest/receipt | 每target真实至少一positive、exact error/recovery/cleanup控制 | missing/cancelled/empty job、prefix rows/丢warning、observer或cleanup failure不准PASS | 02起/15扩展 |
| R26 | Python3.12/3.13中actually available、checkout/relocated/wheel | private artifact observation及真实same-child imports/bytes/rejections | PLANNED：既有invocation-local acquisition扩展，独立manifest，单独DB matrix | candidate→wheel→artifact→submission身份链、历史streams原域 | standalone/正反batch/relocation/installed消费同产物；旧流保持 | installed来源错、submission变字节、仅manifest声称运行、空结果拒绝 | 14/15 |

R13 的count/min/max是首版aggregate承诺，SUM/AVG等没有本版reviewed physical-result转换规则，
在此明确冻结non-support；后续Phase76/77可单独扩展，不能在本phase中先承诺再静默删去。
R02的Timestamp/UUID只承诺有完整原逻辑证据的传递，不开启advanced comparison/ASOF。
R19的省略NULL/tie条款不自动赋予target default：先读原policy的unspecified/target-defined或
required-evidence状态；前两者用其允许结果约束，后者缺失必须BLOCKED。

## R03 scheduling amendment authorized for Slice4

原 Slice1 route 将 R03 completing Slice 记为04；C19 记为04/10，C32 记为04/10/14。
这些是保留的原排期历史。新的 Slice4 用户执行指令现在明确授权下述窄修订；Slice3 PASS
本身未授予该修订。N66=16、所有 operator owners、最终 Phase66 obligations 均不改变。

| Owner | Required R03 delivery |
| --- | --- |
| Slice4 | 完整 production definition/use/terminal correspondence、capture-free scopes、installed 两target named/imported/reexported field-projection chains；重复 graph 与 ORDER carriers 仅结构检查/准确 BLOCKED |
| Slice7 | repeated/shared producers inside admitted JOINs 的 installed joint execution |
| Slice10 | ordinary/rebound/completed ORDER realization，以及相关 ORDER/LIMIT sharing joint execution |
| Slice11 | repeated/shared producers inside SET，包括 repeated UNION ALL 与 two import facades 的 installed joint execution |

R03 outstanding joint execution: Slice7 repeated/shared JOIN; Slice10 ordinary/rebound/completed ORDER and ORDER/LIMIT sharing; Slice11 repeated UNION ALL and two import facades.

Slice4 的结构检查、blocked documents、分别执行的 queries 和手写 controls 不能抵扣这些
joint witnesses；其发布不代表完整 R03 target conformance。sole lifecycle reader 保持该
未完成清单可见，Slice16 completion audit 必须核对各 owner 的实际 joint receipts。
本修订不将 JOIN、ORDER/LIMIT 或 SET lowering 提前到04。

## R03 Slice10 delivery

Slice10 按 [Slice10 contract](phase66-slice10-distinct-order-limit-result-boundaries-emission-v1.md)
交付了 ordinary/rebound/completed 三类 ORDER carrier 的 installed real-target joint
execution（`O_named_later` 三个 ORDER variants 迁移为 VERIFIED，各自保留不同的
carrier authority），以及 ORDER/LIMIT sharing（一个 ordered+limited producer 被
INNER self join 的两个 use 各自绑定同一 post-LIMIT terminal）。未修改上游 completion。
其余保持未完成：

R03 outstanding joint execution: Slice11 repeated UNION ALL and two import facades.

## R03 Slice11 delivery

Slice11 按 [Slice11 contract](phase66-slice11-six-set-forms-positional-types-operand-local-boundaries-v1.md)
交付了 repeated/shared UNION ALL（`O_named_later/union_dag`）与 two import facades
（`O_named_later/two_facades`）的 installed real-target joint execution：共享 definition 只
生成一次 CTE，每个 use 是独立 operand，facade 经真实 module 解析到同一 definition。自然
exact-head CI 成功后：

R03 outstanding joint execution: none.

## R23 Slice12 delivery

Slice12 按 [Slice12 contract](phase66-slice12-complete-emission-artifact-dual-denominator-sql-range-queries-v1.md)
整合 R23：不新增表示，而是把 Slice3–11 已发布的独立 plan→AST、events→bytes、双 denominator 与
parameter/result verifiers 汇总为一个 artifact-bound 的私有 inspection 视图
（`project_sql_emission_inspection`），并补齐 C20–C25/C31 的集成见证与 forward/reverse SQL-range
查询。C20：两清单各自从实际结构独立枚举，单删、互删、重复、重排、foreign subject 均拒绝。C21：同
statement scope 的不同声明为 PIE-B1005 `inconsistent_declared_scope`，source-local 合法差异
（`max_characters`）不构成 global conflict，跨源操作各自的 compatibility rule
（`text_comparison_domain_conflict`、`set_column_physical_representation_mismatch`）保留。C22：closed
representation 只有直接 accepted roots（retained `Premise`、report entry、AST subject），不能表达
rule→rule 引用，复制、替换或 rule 引用即拒绝，不引入 proof graph。C23：fresh explicit target
preparation 可复用不变的 neutral plan，old artifact 不因此重获 validity，foreign/stale/decoded root
拒绝。C24/C25：sidecar 正确而 SQL bytes 被改、mid-codepoint endpoint、JSON 或 parser 坐标冒充 SQL
byte offsets 均拒绝；byte 地址查询可命中 interior byte 所在 range，但 emitted endpoints 保持字符边界。
C31：LEGAL_UNPROVED 为 PIE-B1006 `original_enforcement_not_fulfilled` 且原 warning 保留，EXCEPT-right
`complete_right_terminal` 与 LIMIT0 operand 的原 demands 不可删，ordinary aggregate risk 不升级为义务。
installed probe 在 generation child 内于导出前消费该视图；denominator 保持 60/181。

## R24 Slice13 delivery

Slice13 按 [Slice13 contract](phase66-slice13-project-emit-sql-cli-explicit-contract-atomic-output-v1.md)
交付 R24/E08：installed public `pietto emit-sql --project PATH --module LOGICAL_MODULE --kind
{table,query} --name NAME --dialect {postgres,mysql} --emission-contract FILE`（私有协调器
`src/pietto/_project/project_sql_emission_cli.py` 加 `cli.py` 的 project-mode 分派）在既有 verified
pipeline 之上提供 explicit owner/dialect/contract 输入、closed public union 输出（JSON stdout、text
presentation、atomic `--output` 文件）与 legacy 兼容；默认 `--format json`、`--literal-policy preserve`；
owner 按 logical module、declaration kind、name 唯一选择；contract 为 normalized project-relative
路径，经 pinned-root open contract 读取一次并在读取时执行 1 MiB 上限；每个公共文档与同输入的
installed API artifact 逐字节相同。C03：large Int decimal 文本、Bool/Int/Float tags、signed zero 以
unary 结构保留经公共 CLI 见证。C29：target facility 新增 `CLI_console_emission` case，isolated
installed interpreter 通过 runpy 运行真实 console entrypoint，同 child origins 必含 `pietto.cli` 与
`project_sql_emission_cli`，console 文档以 SHA-256 对照同输入 API 记录（收据全文携带）。denominator
61 cases/187 public documents per target（postgres 154/4/29；mysql 151/4/32）。public decoder 的
cli_errors allowlist 扩为本文 15 种 kind。不新增 emitter、public Python API、executor 或 private
observation format。

## R26 Slice14 delivery

Slice14 按 [Slice14 contract](phase66-slice14-private-emission-observation-process-integration-v1.md)
交付 R26 与 C29/C32：私有 `pietto.sql-emission-observation.v1` 覆盖完整 admitted emission 表示
（73 个闭合 record kind，typed local refs，plan refs 为 Phase65 plan 身份），runtime 导出
（`project_sql_emission_portable`，只读既有 verifier）、独立 runtime correspondence（文档驱动双向
绑定 + 公共 artifact 与 Slice12 inspection 投影）与 data-only pure consistency
（`project_sql_emission_pure_boundary`，只导入 `project_sql_emission_portable_schema`）三者分离；
coherent alternative 通过 pure 而 correspondence 失败，pure consistency 不是 authenticity。
C32：ordinary/rebound/completed ORDER carriers 与其 items 的 carrier 一致、port/read 经 order_item
overlay token 绑定，协调改写只能被 correspondence 拒绝。C29：首个 `phase66` 差分进程 family 在
checkout/relocated/installed-wheel cells 中 standalone 与正反 batch 字节一致，同 child origins 为三个
新模块。297 个 VERIFIED generation inputs 全部导出、对应、解码；DB denominator 不变（61/187），私有
文档不进入 receipt。

## R25 Slice15 delivery

Slice15 按 [Slice15 contract](phase66-slice15-expanded-target-differential-metamorphic-conformance-v1.md)
扩大 C01–C32 组合并交付 C30 路由：新 target case `M_metamorphic_composition`（执行的 JOIN chain，
其 RIGHT JOIN unit 读取前一 LEFT JOIN unit；两种 UNION ALL filter 位置），以及 `check_relations`
在每个完整 target run 内对全部 VERIFIED 提交检查十族 metamorphic 定律（F1–F10），不读取 case
oracle、不增加 receipt 字节，违反即 `case_execution` 的 `UNRESOLVED_ATTRIBUTION`。independence：
row verifier 仅以 `emission_blockers`/`realize_rows` 共享 applicability gate，协调漂移只被
`plan_ast_correspondence` 拒绝，注入的 constructor fault 为 BLOCKED PIE-B1008。Slice14 关于
predecessor JOIN inputs 只来自 multi-hop path 的表述更正为 in-definition chain 可达；two-hop `via`
仍在 Slice7 finite JOIN input domain 之外（BLOCKED PIE-B1003）。receipt 上限经用户决定为 33 MiB，
receipt v2 其余不变；denominator 62 cases/190 public documents per target（postgres 157/4/29；
mysql 154/4/32）。无 production 变更、无新 process family；Slice16 为 audit-only。

## R15-INT-OFFSET-V1 and pre-Slice16 corrective disposition

首次 Slice16 completion audit 以 HOLD 结束：发现 R14/D66.07 的 named window 首用塌缩缺陷（G1）、
R15 精确算术前提未实现（G3），以及 R09/C14、R16、C06、R21/R04 的承诺见证缺失（G2、G4–G6）。
用户随后授权一个不编号的 corrective closure（不是 Slice16/17，N66=16 不变），按
[corrective closure contract](phase66-pre-slice16-completion-corrective-closure-v1.md) 修复 G1、G3
并以证据关闭 G2、G4–G6；上文原承诺全部保持，本节不声称 G3 曾在更早 Slice 实现。

R15-INT-OFFSET-V1 是用户对 R15 “精确算术前提”的具体决定：每个 finite frame offset 为精确非负
signed64 整数（ROWS/PG GROUPS 为计数，不受 ORDER key storage 约束）；offset RANGE 的 key domain
须在其 reviewed storage 内，且每个实际 endpoint 按方向平移的整个 domain 区间在 signed64 内，
threshold 可宽于 key storage。越界 offset 为 `PIE-B1002 window_frame_offset_out_of_signed64_range`，
缺可用 domain 为 `PIE-B1004 window_range_arithmetic_evidence_missing`，domain 越出 storage 为
`PIE-B1002 window_range_key_domain_out_of_storage_range`，平移越界为
`PIE-B1002 window_range_boundary_out_of_signed64_range`；每个 use 在其 `window_specification`
之后新增 `window_frame_offset_domain` 与（RANGE 时）`window_range_arithmetic` 两个 R15 generated
requirements。G1 修复后，named declaration 只在完整 use-local specification 相同时共享生成定义。

同一 closure 的首次 MySQL 全量运行发现 G7：window value 结果（lag/lead/first/last/nth_value）照抄输入的
storage 与区间。用户随后决定三项同源处置。第一，R14-PG-NAVIGATION-RESULT-V1：PostgreSQL 三参数
lag/lead 为 `anycompatible`，未 cast 的整数 default 以其自身 literal 类型（signed32 内 int4，否则 int8）
与 value 的 `pg_int2 < pg_int4 < pg_int8` 取较宽者；offset 不参与，其他窗口/聚合/SET 宽度不变。第二，
R15-MYSQL-WINDOW-RESULT-V1：MySQL 物化的整数 window value 在显示长度 < 10 时为 INT、≥ 10 时为
BIGINT，其中 SMALLINT/INT/BIGINT 列分别为 6/11/20，d 位 default 为 d+1；只审阅 source field 与既有
window result 两类 carrier，其余 MySQL Int carrier 为
`PIE-B1002 mysql_window_integer_result_origin_not_supported_in_phase66`。两目标上的非 NULL default 都把
区间扩为最小包络 [min(L,d), max(U,d)]；超出 signed64 的 default 为
`PIE-B1002 window_default_integer_out_of_signed64_range`，包络越出所选 storage 为
`PIE-B1002 window_value_domain_out_of_storage_range`。第三，B1 是新的显式支持决定（B 原是已存在的错误
成功，并非一直是边界）：MySQL 上 Bool 值的五种 value window 为
`PIE-B1002 mysql_bool_window_result_representation_not_supported_in_phase66`，不新增 storage 词汇、
CAST 或 Int 重解释；准确的 MySQL Bool window 表示留待今后的 MySQL-depth 决定。
denominator 变为 63 cases/195 public documents per target（postgres 162/4/29；mysql 158/4/33）。
Phase66 仍 `ACTIVE`，Slice16 仍 `NEXT / NOT IMPLEMENTED`，须对新基线重新审计。

## R11/C09 scheduling amendment authorized for Slice7

原 Slice1 route 将 R11 的完整 SEMI/ANTI right terminal 义务与 C09 的 right
LIMIT0/LIMIT1/SET/GLOBAL-empty/window-producer membership 差异一并记在07。新的
Slice7 用户执行指令明确授权下述窄修订；Slice6 PASS 本身未授予该修订。N66=16、
所有 operator owners、最终 Phase66 obligations 均不改变。

| Owner | Required R11/C09 delivery |
| --- | --- |
| Slice7 | EXISTS/NOT EXISTS 包裹当前已可构造的完整 right terminal：right scan、retained producer filter、ordered LET 与 JOIN terminal；generated correlation/scope/sentinel、right dependency 完整保留、左 schema 不含 right output |
| Slice8 | right GROUPED/GLOBAL producer 的 membership 差异，含 GLOBAL empty 输入仍产生一 row |
| Slice9 | right window/QUALIFY producer 的 membership 差异 |
| Slice10 | right LIMIT0 与 LIMIT1 的 membership 差异 |
| Slice11 | right SET 结果的 membership 差异 |

C09 的 LIMIT/SET/GLOBAL/window 分支需要各自 owner 先交付该 producer 形状；在那之前
它们既不是 Slice7 的可构造输入，也不能由 Slice7 以手写 SQL 或 dummy producer 代替。
Slice7 交付的是 marker/LET/filter/JOIN terminal 分支，以及 base-table shortcut、
NOT IN、删除 right 依赖与 right output 漏入左 schema 的拒绝控制。

Slice8 交付了其中的 GROUPED/GLOBAL right-terminal 分支，其余保持未完成：

R11/C09 outstanding membership differences: Slice9 window/QUALIFY; Slice10
LIMIT0/LIMIT1; Slice11 SET.

Slice9 交付了其中的 window/QUALIFY right-terminal 分支，其余保持未完成：

R11/C09 outstanding membership differences: Slice10 LIMIT0/LIMIT1; Slice11 SET.

Slice10 交付了其中的 right LIMIT0/LIMIT1 分支：SEMI/ANTI 包裹完整的 right result body
（post-LIMIT terminal），right `LIMIT 0` 使 SEMI 为空、ANTI 为完整左 BAG，right
`ORDER BY … LIMIT 1` 只选出一个 membership key；其余保持未完成：

R11/C09 outstanding membership differences: Slice11 SET.

Slice11 交付了最后的 right SET 分支：SEMI/ANTI 包裹完整的 right SET terminal（其自身的
EXCEPT/INTERSECT DISTINCT 语义与 NULL 等价保留），不用 NOT IN、不漏 right 列、不短路到
operand 或 base scan。自然 exact-head CI 成功后：

R11/C09 outstanding membership differences: none.

## Upstream current-route compatibility rule authorized for Slice7

Slice7 之前，JOIN input producer 里任何非 field 输出（authored literal、computed
value、ordered LET）都会使该 producer 的整行 lineage 变为 non-concrete，joined tail
随之 non-concrete，emission 根本收不到这种输入。R08/C07 承诺的 “right-side literal
marker 在未匹配 LEFT row 上变 NULL” 因此无法构造。

授权的窄修订只作用于 completion 的路线选择，不改变任何 lineage status、不抑制
PIE-S2333、不伪造 source field/root/proof：

1. `optional_current`：仅承载 relationship-only `via` 的 INNER/LEFT JOIN-use owner
   （无 ON clause，且不是 CROSS/RIGHT/FULL/SEMI/ANTI）与其传递依赖闭包，可以尝试
   current route。已经强制 current 的既有成员优先，重叠时按 required 处理。
2. 采纳条件：current 结果必须是完整有效的 `ProjectCompletedEffectiveOutput`。否则
   保留原有 base route 及其自身 diagnostics，不混合两条路线的部分结果。
3. `_promoted_scalar_producer`：只有 existing no-JOIN TableDef/QueryDef entry，且其
   retained relation lineage 是唯一且已证据化的 non-CONCRETE 事实，才走既有
   `_complete_no_join_output` replay；仅当 replay 的 root 是 mode ABSENT、无 aggregate
   readiness、无 window outputs、QUALIFY ABSENT 且无 hidden attempts 的
   `ProjectConcreteNoJoinReplay`，且每个 selected output source 都是
   `ProjectNoJoinScalarExpression` 时才采纳。

两条 composition 义务必须分开理解，不可互相抵扣：

- 合法的 relationship-endpoint `via`-only INNER/LEFT control 仍是正面见证，其
  retained equality 必须原样出现在 emission 中；
- 新提升的 scalar/literal/LET producer 必须经由其 admitted generic ON route 成功
  composition。**一个值变得可传输并不因此获得 relationship-endpoint 或 M1/M2/M4
  guarantee。**

保留的上游边界：relationship `via` 的相关 endpoint producer 被提升时，
`project_join_conditions.py` 仍要求 `item.authority.historical_properties is not
None`，该输入依旧不可用，并保留其 `joined_completion_non_concrete` 原因。这是精确的
上游负例，其 before/after 失败边界被保留，它不是成功的 promoted-`via` 见证，也不抵扣
任何正面义务。`project_join_conditions.py` 未被修改。

## Upstream aggregate-producer completion route authorized for Slice8

Slice7 的 `_promoted_scalar_producer` 只接纳 ordinary scalar body，因此一个
GROUPED/GLOBAL no-JOIN producer 的 joined tail 仍然 non-concrete，R12/R13 承诺的
aggregate right terminal 与 outer-nulled aggregate value 都无法构造。新的 Slice8
用户执行指令明确授权下述窄修订；Slice7 PASS 本身未授予该修订。N66=16、所有
operator owners、最终 Phase66 obligations 均不改变。

授权的修订只作用于 completion 的路线选择，不改变任何 lineage status、不抑制
PIE-S2333、不伪造 source field/root/proof：

1. `_promoted_scalar_producer` 复用既有 `_complete_no_join_output` replay。除既有
   ordinary scalar body 外，另接纳 mode 为 GROUPED 或 GLOBAL、
   `aggregate_readiness.status` 为 CONCRETE、`replay.ordering` 与 `replay.limit`
   均为 None、每个 selected output source 都是 `ProjectNoJoinGroupedOutput`，
   且确有一个 authored JOIN 直接消费该 producer 的 replay root。只被 SET operand
   或其他非 JOIN 消费者使用的 grouped producer 保持原 base route 与自身
   `historical_properties`，其 GLOBAL/FACTORIZED grain 证据不受影响。
2. window/QUALIFY 排除不变：`window_outputs`、非 ABSENT 的 QUALIFY、
   `selected_windows` 与 `hidden_attempts` 任一存在即保留原有 base route。
3. 旧 scalar 路线及其排除原样保留；没有删除任何 aggregate guard，也没有把 replay
   一律归类为 scalar。

被提升的是 grouped/global 结果本身：GLOBAL 结果不是其 raw source row，带隐藏键的
GROUPED 结果既不是 GLOBAL 也不是唯一可见 tuple。可传输性不产生
relationship-endpoint 或 M1/M2/M4 guarantee，joined field aggregate 仍需其既有
grain/uniqueness 前提，缺少时保持原有 `PIE-S2333` 负例。

## Upstream window-producer completion route authorized for Slice9

Slice8 的 `_promoted_scalar_producer` 明确保留了 window/QUALIFY 排除，因此一个完成的
window 或 QUALIFY no-JOIN producer 的 joined tail 仍然 non-concrete，R14/R17 承诺的
window right terminal 与 outer-nulled window value 都无法构造。新的 Slice9 用户执行指令
明确授权下述窄修订；Slice8 PASS 本身未授予该修订。N66=16、所有 operator owners、最终
Phase66 obligations 均不改变。

授权的修订只作用于 completion 的路线选择，不改变任何 lineage status、不抑制 PIE-S2333、
不伪造 source field/root/proof：

1. `_promoted_scalar_producer` 另接纳一个 body：`root.window_outputs` 存在或
   `root.qualify.kind` 为 `AUTHORED_QUALIFY`，且 `qualify.concrete`、每个
   `qualify.hidden_attempts` 的 analysis 均为 `WindowComputationAnalysis`、
   `replay.ordering` 与 `replay.limit` 均为 None、确有一个 authored JOIN 直接消费该
   producer，且每个 selected output source 为 `ProjectNoJoinScalarExpression` 或
   `ProjectModuleWindowOutputFact`。
2. 其余排除原样保留：relation ORDER/LIMIT barrier、ABSENT-qualify body 仍带
   `selected_windows`/`hidden_attempts`、旧 scalar 与 Slice8 grouped 分支及其全部条件。
3. 被提升的是完成的 window 结果本身。可传输性不产生 relationship-endpoint 或
   M1/M2/M4 guarantee。

Slice7 的 later-owner 排除现已迁移其 window 分支为正面行为；保留的真实负例改为一个
带 Slice10 relation ORDER barrier 的 window producer。

Slice7 的 later-owner 排除只迁移其 aggregate 分支为正面行为；window 分支保留为真实
负例。该排除原有的两个 fixture 都在 parse 阶段失败（`PIE-P1000`），因此两者都已按真实
可接受的源码表面重写；这是被记录的既有缺陷修复，不改变任何已发布义务。

## Counterexample obligations

这些是独立规格例，不是本次Pietto/DB执行结果。不新增evaluator/fuzz平台。
每个C要求同时检查正例域和违反前提时的准确边界；“拒绝”不指任意exception。

| Case | Minimal input / independent expected boundary | Rules | Completing Slice |
| --- | --- | --- | --- |
| C01 | nullable Bool=[TRUE,FALSE,NULL]投影三值；WHERE只一行；NULL不能在子表达式被归一为FALSE | R05 R06 | 06 |
| C02 | MY physical Bool=[1,2]不得以truthiness合并为true；声明0/1域的[0,1,NULL]为正例 | R02 R06 R18 | 03/06 |
| C03 | Int9007199254740993公共decimal文本；Bool1/Int1/Float1 tags与Float正负零区分，unary minus不折叠 | R02 R04 R24 | 05/13 |
| C04 | count*/count nullable及empty GLOBAL/GROUPED差异；SUM/AVG physical promotion触发明确首版边界，不在downstream错用 | R12 R13 R22 | 08/11 |
| C05 | Text `a`/`A`、`x`/`x `、prefix后不同值；原PROVED不被不同collation/padding/prefix扩大适用 | R02 R18 R19 | 05/10 |
| C06 | PG parent与child出现同key，relation_rows与physical uniqueness不能由same-named constraint认证；partition/view分别声明 | R01 R02 | 03 |
| C07 | LEFT右producer先SELECT marker=1，未match时marker必须NULL | R08 | 07 |
| C08 | (A LEFT B) RIGHT C，A/B的已累计nulling与新nulling均保留 | R08 | 07 |
| C09 | SEMI/ANTI right LIMIT0、LIMIT1、SET、GLOBAL empty、window producer各自completed terminal；base scan shortcut得到不同membership | R11 | 07 |
| C10 | constant GROUP/ORDER key=1不能解释成ordinal；用户label等于column不得改变绑定；04只完成named field labels/scopes，constant GROUP/ORDER仍由08/10真实执行 | R03 R12 R19 | 04 scopes /08 GROUP /10 ORDER |
| C11 | physical table名恰等于generated CTE名，quoted也可能capture；04 named-chain namespace checker与真实target证明绑定，不代表R03全部joint cases完成 | R03 | 04 |
| C12 | hidden window/group/order值不在visible DISTINCT/SET tuple内，SELECT label重复仍positional | R17 R18 R20 R22 | 09/10/11 |
| C13 | [1,2]先LIMIT1再filter>1为空；先filter后LIMIT为[2]；outer presentation须final ORDER | R19 R21 | 10 |
| C14 | PG FULL builtin cross-input Int equality正例含两个NULL未match行；inequality/OR/额外ON为准确non-support；MY FULL总negative | R09 R10 | 07 |
| C15 | RESPECT NULLS/FROM FIRST identity omission可保持；IGNORE NULLS/FROM LAST不可消失 | R16 | 09 |
| C16 | offset RANGE单non-null Int key正例；为NULL order加key导致offset-RANGE不合法/变义；多key/负offset准确拒绝 | R15 R19 | 09/10 |
| C17 | A=[1,1,NULL],B=[1,NULL,NULL]：UNION ALL six rows，UNION DISTINCT two；INTERSECT ALL two，DISTINCT two；EXCEPT ALL one1，DISTINCT zero | R22 | 11 |
| C18 | SET不同Decimal parents/p/s或Int/Float promotion不得靠backend common type；Float UNION ALL与其它五式不同 | R02 R22 | 11 |
| C19 | 两个use共享definition并不证明materialize/evaluate once；04保留结构/阻断，07/10/11分别实际验证JOIN、ORDER/LIMIT、SET sharing；不捏造重复LIMIT选择独立性或coupling | R03 R21 | 04 structural /07/10/11 joint |
| C20 | 原demands完整但generated CAST/correlation/parameter/order helper需求缺失仍失败；两清单互删不能空成功 | R04 R11 R23 | 05/07/12 |
| C21 | 两rule要求同一statement时区/SQL mode不同→conflict；两个source局部合法不同collation不自动global conflict | R01 R02 R23 | 03/12 |
| C22 | justification A→B→A无独立root拒绝；一root被两个rule引用允许但各use保留 | R23 | 12 |
| C23 | old plan/new contract、foreign owner/policy/envelope、target-only改动旧artifact失效；neutral root可不变 | R01 R04 R23 | 03/05/12 |
| C24 | sidecar正确但SQL operator/identifier/parentheses/separator被改，或拼接产生comment，independent byte checker拒绝 | R23 | 03起/12 |
| C25 | 非BMP/escape/newline的parser字符坐标与UTF-8 SQL range不同；JSON escaping后不得移用JSON byte offsets；wrong parameter index拒绝 | R04 R23 | 05/12 |
| C26 | warning total大于存储details，next statement清空诊断，或fixture-load warning丢失，不能报empty success | R25 | 02 |
| C27 | prefix rows后error、metadata absent、rollback/cleanup失败分别保留；success→expected failure→success必须真实恢复 | R25 | 02 |
| C28 | CI manifest为空、missing/skipped/cancelled target job、receipt缺项均不能aggregate PASS | R25 | 02 |
| C29 | candidate wheel正确但实际import来自checkout，或submitted SQL/parameters与artifact不同，证据链失败 | R24 R25 R26 | 03/13/14 |
| C30 | promised-domain红例不能以手写SQL也失败就认定server bug；保持version/environment/minimized fixture与unresolved attribution | R25 | 02/15 |
| C31 | original LEGAL_UNPROVED与LIMIT0/EXCEPT right membership完整保留；ordinary aggregate risk与未履行义务分别处理 | R11 R13 R21 R23 | 07/08/10/12 |
| C32 | ordinary与rebound provided ORDER的items可共享但outputs不同；completed relation ORDER有不同carrier；04只验证结构并BLOCKED，10真实ORDER执行，14独立观察/反向map | R03 R19 R26 | 04 structural /10 execution /14 observation |

## Source findings and consumer consequences

本次author与两个内部只读审计读取实际源码、test bodies及所调用assertion helpers；不是只按
名字找entrypoint，也不是third-party review。已读Phase65 initiation、completion及Slice5–15
各合同；历史临时unsupported fixtures不升级成永久语言限制。下面的箭头是实际data消费链，
future renderer一栏明确未实现；verifier/inspection的调用关系不伪称保留数据字段。

| Finding | Actual producer | Actual consumer / verifier | Source assertion read | Future renderer / parameter / range consequence | Public / portable / test-reader consequence |
| --- | --- | --- | --- | --- | --- |
| F01 | `src/pietto/_project/project_sql_plan.py::build_project_sql_plan` | `src/pietto/_project/project_sql_plan_verification.py::verify_project_sql_plan` → `src/pietto/_project/project_sql_plan_inspection.py::inspect_project_sql_plan` | `tests/test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan.py::test_selected_closure_distinguishes_unrelated_limitation_and_error`、`tests/test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan.py::test_verifier_and_inspection_never_call_construction` | R01只lower exact VERIFIED selection；全project ERROR不裁剪，无关valid planning limitation不poison | public success不可升级IR flag；decoded portable不是入口。 |
| F02 | `src/pietto/_project/project_query_block_ir.py::ProjectIRReusedEffectiveOutput` / `src/pietto/_project/project_query_block_ir.py::ProjectIRReboundExistingOutput` | `src/pietto/_project/project_sql_plan.py::_root_inventory` → `src/pietto/_project/project_sql_plan.py::build_project_sql_bindings`；plan verifier检查exact active producer/edge | `tests/test_phase65_slice8_distinct_scoped_order_static_limit_result_boundaries.py::test_rebound_order_and_limit_use_original_to_active_input_correspondence` | reused cross-relation edge与rebound relation-input edge分别映射；每use消费immediate exports，参数不re-expand | repeated uses保留multiplicity；input_terminals不能按last/name选。 |
| F03 | `src/pietto/_project/project_ir_properties.py::ProjectIRProvidedRelationOrdering` 与 `src/pietto/_project/project_final_outputs.py::ProjectRelationOrdering` | `src/pietto/_project/project_sql_plan_portable.py::build_project_sql_plan_portable` / `src/pietto/_project/project_sql_plan_pure_boundary.py::_provided_ordering_relationships`；runtime correspondence另验 | `tests/test_phase65_slice15_whole_selected_plan_real_source_differential_conformance.py::test_provided_ordering_rebound_and_completed_ordering_keep_distinct_routes`、`tests/test_phase65_slice15_whole_selected_plan_real_source_differential_conformance.py::test_provided_ordering_fields_preserve_exact_output_evidence_and_items` | ordinary/rebound provided carrier为exact output/evidence/items；completed为owner/clause/prepared inputs/items；两种都传至R19，不能用同一个ORDER元组猜绑定或outer order | F65S15-02的两个record及property/ORDER links继续覆盖；items可同tuple但output不同。 |
| F04 | `src/pietto/_project/project_final_outputs.py::ProjectCompletedEffectiveOutput` → `src/pietto/_project/project_query_block_ir.py::ProjectIRCompletedQueryBlockOutput` / `src/pietto/_project/project_query_block_ir.py::ProjectIRCompletedSetOperationOutput`；negative为 `src/pietto/_project/project_query_block_ir.py::ProjectIRQueryBlockTerminal` | `src/pietto/_project/project_sql_plan.py::_root_inventory` / whole plan verification | `tests/test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan.py::test_concrete_looking_terminal_cannot_bypass_supported_shape` | completed query及SET是实际IR concrete carriers；terminal在project-to-plan construction成为typed unavailable，不能作为VERIFIED plan lower输入，无usable partial SQL/ranges | complete selected closure必须处理四类concrete（含SET）与所有terminal。 |
| F05 | `src/pietto/_project/project_query_block_ir_algebra.py::ProjectIRComposedJoin` | `src/pietto/_project/project_sql_plan.py::build_project_sql_plan` / `src/pietto/_project/project_sql_plan_verification.py::verify_project_sql_plan` | `tests/test_phase65_slice5_seven_join_kinds_match_scopes_obligation_retention.py::test_accumulated_left_has_all_previous_and_current_nulling`、`tests/test_phase65_slice15_whole_selected_plan_real_source_differential_conformance.py::test_registered_portable_join_group_window_set_and_profile_relationships` | pre-match、post-null ports、matching-only right分开；R08 marker保持port，R11 EXISTS读completed terminal；source range保留right membership | public columns不含SEMI/ANTI right；portable原nulling counts/roles不被丢弃。 |
| F06 | `src/pietto/_project/project_sql_plan_windows.py::authority` / `src/pietto/_project/project_sql_plan_sets.py::build_body` | plan builder/verifier及 `src/pietto/_project/project_sql_plan_inspection.py::ProjectSQLPlanInspection.terminal_exports` | `tests/test_phase65_slice7_windows_named_window_qualify_staging.py::test_windowed_producer_rebound_consumers_keep_immediate_exports`、`tests/test_phase65_slice9_set_query_expression_bodies_positional_ports.py::test_operand_stages_and_output_roles_survive_set` | windows exact pre-window inputs，QUALIFY后筛；SET每operand完整terminal包括LIMIT/GLOBAL，显式type/NULL/范围links | hidden值不能进入public quotient；EXCEPT right仍membership provenance。 |
| F07 | `src/pietto/_project/project_sql_plan_literals.py::ProjectSQLFixedEnvelope` | `src/pietto/_project/project_sql_plan_verification.py::verify_fixed_literal_envelope` / whole plan verifier | `tests/test_phase65_slice10_typed_fixed_literal_envelope_bind_use_layout.py::test_equal_values_remain_separate_and_let_references_do_not_reextract`、`tests/test_phase65_slice10_typed_fixed_literal_envelope_bind_use_layout.py::test_signed_zero_payload_corruption_does_not_fold_unary_minus` | R04保留contextual slot/actual SQL occurrence/server index三层；literal policy改变使old artifact失效 | public Int decimal/Float hex；BIND不是rebind API；原private envelope不得直接改成public graph。 |
| F08 | `src/pietto/_project/project_sql_plan_requirements.py::build_project_sql_requirement_report` | `src/pietto/_project/project_sql_plan_requirements.py::verify_project_sql_requirement_report` / inspection | `tests/test_phase65_slice11_complete_demand_obligation_report.py::test_layer1_rejects_missing_demands_and_literal_constituents`、`tests/test_phase65_slice11_complete_demand_obligation_report.py::test_repeated_original_requests_and_unrelated_project_warnings` | R23从原结构枚举A，新SQL AST独立枚举B；未fulfilled requirement阻止artifact，不能all(empty) | 原diagnostics和selected demands各自有序；risk/evidence不自动等同execution obligation。 |
| F09 | `src/pietto/_project/project_sql_plan_source_maps.py::build_project_sql_source_map` | `src/pietto/_project/project_sql_plan_source_maps.py::verify_project_sql_source_map` / `src/pietto/_project/project_sql_plan_source_maps.py::ProjectSQLSourceMapInspection.reverse` | `tests/test_phase65_slice12_forward_reverse_source_map_queries.py::test_literal_transport_reverse_identity_and_exact_coordinates` | source coords是parser characters；R23新SQL offsets为UTF-8，render时捕获并独立检最终bytes | public ranges映射logical source roles；不猜DB error snippet或伪造缺位置。 |
| F10 | `src/pietto/_project/project_sql_plan_target_assessment.py::prepare_project_sql_target_request` | `src/pietto/_project/project_sql_plan_target_assessment.py::build_project_sql_target_assessment` / `src/pietto/_project/project_sql_plan_target_assessment.py::verify_project_sql_target_assessment` | `tests/test_phase65_slice13_explicit_target_profile_requirement_assessment.py::test_real_compiler_positive_subpropositions_do_not_certify_composites`、`tests/test_phase65_slice15_whole_selected_plan_real_source_differential_conformance.py::test_target_only_reassessment_keeps_the_original_neutral_request` | 原SATISFIED只针对proposition；R23不要求whole-target-positive，也不跳过原negative/conflict | new request/source/environment单独绑定；原assessment raw channels和neutral bytes保留。 |
| F11 | `src/pietto/_project/project_sql_plan_portable.py::build_project_sql_plan_portable` | `src/pietto/_project/project_sql_plan_portable.py::verify_project_sql_plan_portable` / `src/pietto/_project/project_sql_plan_pure_boundary.py::evaluate_project_sql_plan_document` | `tests/test_phase65_slice14_portable_boundary_minimal_process_integration.py::test_coherent_document_is_not_runtime_authentication`、`tests/test_phase65_slice15_whole_selected_plan_real_source_differential_conformance.py::test_removing_contexts_and_all_their_links_still_contradicts_ancestry` | pure consistency不能作为runtime lower输入；source report-local ancestry不能通过两清单互删证明完整 | F65S15-01保持；R26新observation不污染旧format或假装redacted。 |
| F12 | `src/pietto/sql/relations.py::render_relation_sql` / `src/pietto/sql/mysql.py::emit_mysql_sql` | `src/pietto/cli.py::main` / `src/pietto/cli_json.py::emit_sql_result_to_json_dict` | `tests/test_phase10_mysql_cli_enablement.py::test_closed_dispatch_passes_only_script_ir_to_selected_backend`、`tests/test_phase10_mysql_cli_enablement.py::test_mysql_remains_private_and_check_is_unchanged` | legacy是ScriptIR→SQL而非ProjectSQLPlan→SQL；新AST/range verifier不能以旧emitter自证 | legacy v1/public Postgres API unchanged；project mode采用独立artifact，旧goldens仍byte-exact。 |
| F13 | `tests/_pietto_repository_facts.py::RepositoryFactIndex` / `tests/_pietto_differential_process_acquisition.py::available_supported_interpreters` | static principals / `tests/_pietto_differential_process_acquisition.py::DifferentialAcquisition` | `tests/test_phase65_slice14_portable_boundary_minimal_process_integration.py::test_process_request_manifest_covers_single_and_both_interpreters` | R26复用实际current registry：phase58–65八family，supported与available不同；不重建process framework | lifecycle/inventory各现有唯一reader；当前双解释器86 requests不是永久quota，旧62/74域不丢。 |
| F14 | existing pyproject/uv.lock、`scripts/validate.py::main`、`scripts/package_smoke.py::main` | `.github/workflows/ci.yml` 两Python jobs / existing static stage and package tests | `tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py::test_no_gain_closure_restores_exact_two_stage_typing_authority` | 现有环境无DB adapter/job；R25必须新获资源授权，先有真实legacy consumer；03起用new installed pipeline | 当前四required steps保持；不是DB执行证据，新增DB acceptance不可missing/empty PASS。 |

Public/privacy边界的直接readers还包括
`tests/test_phase49_compatibility_privacy_hash_lock_readiness.py::test_project_json_v2_public_envelope_and_privacy_remain_stable`、
`tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py::test_current_aggregate_grouped_private_facts_remain_unserialized_and_unexported`、
`tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py::test_private_inventory_has_no_compiler_public_or_serializer_consumer`、
`tests/test_phase65_slice13_explicit_target_profile_requirement_assessment.py::test_new_consumers_remain_private_without_dynamic_or_renderer_access`、
`tests/test_phase58_slice14_project_explain_cli_text_json.py::test_cli_dependency_direction_is_narrow_and_does_not_duplicate_runtime`。
任何未来consumer迁移须先完整查这些guard实际保护的依赖和数据，而不是将名字加入宽泛allowlist。
新artifact只投影所需字段，不能直接暴露上述private aggregate/type/module载体。

## Future infrastructure prerequisites

这张表是设计/接收门，不是本Slice执行许可。未来Slice2 prompt必须先重新列举真实依赖、
lockfile、collection、harness、workflow、直接guards与每项resource operation，然后冻结精确
allowlist；本合同不预造contingency文件、不安装driver/image、不触碰宿主已有DB。

| Prerequisite | Exact acquisition / implementation owner and gate | Lifecycle and acceptance |
| --- | --- | --- |
| P01 target artifacts | Slice2 Gate0/1读取PG18.6/MySQL8.4.12官方distribution记录，区分image tag、multi-platform index digest、platform manifest digest、server build/platform、libraries；实际pins尚MISSING_OBSERVATION | 只在精确resource授权后pull/create；无latest/自动downgrade；运行前核对server/OS/architecture/libraries与receipt，错配不测假target。 |
| P02 stable test adapters | Slice2在实际 `pyproject.toml` / `uv.lock` 冻结Psycopg RawCursor与历史Connector/Python prepared cursor及依赖版本；当前Slice5使用同一26.7 pure driver的native methods；当前dev docs不是stable pin | 独立test dependency group/locked env，无production import；当前v2核对actual prepare/command-send byte identity、statement/session/value和terminal/close-send；无cursor fallback。 |
| P03 explicit collection | Slice2检查 `tests/conftest.py`、`pyproject.toml`、`scripts/validate.py` 和现有pytest acquisition；新DB collection exact命令/paths由该Slice先enumerate再获批 | 常规pytest继续所有既有tests和新harness unit/config tests；DB cases单独显式collection及独立有限manifest；没有环境skip当PASS。 |
| P04 isolated resources | Slice2 resource owner持有显式container/network/volume IDs及creation receipt；仅本次资源，无ambient DATABASE_URL/PGHOST、host mounts、global prune | planned bounds：startup≤120s，最多3次startup/connect尝试且在总时限内；query≤10s、read≤20s、cleanup≤30s；Slice2执行前冻结实际参数，失败不无限重试。 |
| P05 fixtures and query role | Slice2分别管理fixture-admin与least-privilege SELECT-only角色，credentials只传test资源通道；不进compiler/artifact/log | 独立人工有限fixture及oracle，首版每case每relation≤1000rows，结果≤100000rows/16MiB；bounded overflow归observer failure，无prefix成功。 |
| P06 recovery/close | Slice2每项成功acquire即登记finalizer，setup/yield之前失败也清理；观测diag必须早于下一语句 | PG expected error后rollback/savepoint recovery；MY DDL不能靠rollback cleanup；success→expected failure→success、close及owned drop/stop结果都记录。 |
| P07 diagnostics/observation | Slice2先观测legacy-generated与independent SQL；Slice3开始必须用installed new emission artifact，后续每operator首个consumer同时接入 | 完整rows/types/column metadata/terminal status/notices/warning total/details及fixture loading diag；detail截断或缺metadata保持明确unavailable，不能判false/non-null。 |
| P08 CI aggregate | Slice2检查 `.github/workflows/ci.yml`、现有四required steps、workflow tests，再获精确workflow/resource权限；当前workflow未改变 | 两exact-target jobs独立compiler3.12/3.13 matrix；read-only repo permissions、pinned actions，不运行privileged PR untrusted checkout；missing/skipped/cancelled/empty required job使aggregate非PASS。 |
| P09 receipts and linkage | Slice2建立finite manifest/real receipts，03开始candidate→installed wheel→artifact→submitted SQL/params→server/env/query role→complete observation→independent oracle | 当前v2增加native API/session/statement/actual-command/terminal/cleanup；历史v1不认证新路由。artifact传递而非大job outputs；identity hash只用于跨boundary真实bytes；下载digest warning必须变验证失败，不能以checksum认证语义。 |
| P10 guard and installed closure | Slice2重新枚举 `.github/workflows/ci.yml`、`scripts/package_smoke.py`、`scripts/check_goldens.py`、`tests/_pietto_differential_process_acquisition.py`、`tests/_pietto_differential_probe_batch.py` 及上节direct guards | 既有compiler/process acquisition不冒充DB harness；14做首次private observation实际注册/relocation/wheel消费，15扩大；SUPPORTED与AVAILABLE分别记录。 |

状态：NOT_ACQUIRED→ACQUIRED→READY→RUNNING→OBSERVED/FAILED→RECOVERED/RECOVERY_FAILED→
CLOSED/CLEANUP_FAILED。取消、超时、连接中断都进入failure和owned cleanup；query failure与cleanup
failure可同时存在。fixtures无并发写竞争；不同target隔离执行并有独立receipts。由本次实际创建
IDs界定清理权限，失败收据不自动授予重新运行或删除其它资源权限。

失败分类为 COMPILER_DEFECT、FIXTURE_OBSERVER_DEFECT、INFRASTRUCTURE_FAILURE、
TARGET_IMPLEMENTATION_DEFECT、UNRESOLVED_ATTRIBUTION。server bug需minimized exact query、
fixture、SQL/params、版本/环境与独立预期；手写SQL也失败只说明同现象，不能单独证实server错误。
不等待vendor回应才保留/阻断；不加xfail、不改optimizer_switch/降级/缩promise掩盖红例。
基础设施中断只保留实际状态，不制造empty commit；无manual CI rerun授权。

## Sixteen-Slice delivery route

每个implementing Slice在首次引入行为时交付producer→verifier→actual consumer及local demands、
参数/range links、positive/negative evidence。12/14/15只能整合/扩展，不能补忘掉的first capture。
基础设施发布起，所有适用Slice acceptance必须同时拥有原compiler gates与两target conformance，
这不是本Slice提前创建target jobs。

| Slice | Delivery | First consumer and independent check | Counterexamples | Exit coverage |
| --- | --- | --- | --- | --- |
| 01 | Initiation/source audit/decisions/route | 本合同与static principal，no production | C01–C32作为未来义务 | E01–E10设计，不宣称满足 |
| 02 | Isolated target conformance facility, real minimal consumers and required CI | legacy-generated + independently specified SQL、真实recovery/cleanup、manifest/required aggregate | C26 C27 C28 C30 | E09设施 |
| 03 | Minimal source realization and both-dialect scan/projection emission vertical | installed minimal emission及public decoder被target facility消费；独立AST/byte/requirement/source/output map验证立即存在 | C02 C06 C21 C23 C24 C29 | E01 E02 E03 E04 E06 E07 |
| 04 | Named/shared producers, scopes, terminal outputs and capture-free names | exact scopes/terminal consumer、SQL binding check、两target真实named chains；repeated/ORDER graph仅结构/阻断，joint witnesses留07/10/11 | C10 C11 C19 C32 | E02 E03 E06 |
| 05 | Fixed values, physical type anchors and server parameter-use mapping | RawCursor/prepared实际transport与原envelope核对、use/ranges/source links | C02 C03 C05 C20 C23 C25 | E05 E06 E07 |
| 06 | Supported row scalar/LET/WHERE/ON | 原树/nullable Bool的独立truth oracle与真实target scalar/filter | C01 C02 | E03 E04 E06 E07 |
| 07 | JOIN/EXISTS, restricted PostgreSQL FULL and MySQL FULL negative domain | completed right terminals、outer-null ports与two-target BAG oracle；R03 repeated/shared JOIN joint execution | C07 C08 C09 C14 C19 C20 C31 | E02 E03 E04 E07 |
| 08 | GROUPED/GLOBAL/satisfying and aggregate representations | empty input、count/null、promoted representation negative与post-group consumer | C04 C10 C31 | E03 E04 E07 |
| 09 | Admitted windows/named uses/QUALIFY | selected/hidden pre-window roots、frame/peers/modifiers和QUALIFY真实consumer | C12 C15 C16 | E02 E03 E04 E07 |
| 10 | DISTINCT/ORDER/LIMIT and exact result barriers | final ORDER、visible tuple、inner LIMIT与hidden STRICT-FD blocker；R03三类ORDER及ORDER/LIMIT sharing joint execution | C05 C10 C12 C13 C16 C19 C31 C32 | E02 E03 E04 E07 |
| 11 | Six SET forms, positional types and operand-local boundaries | independent六式BAG/type oracle，保留nested/operand terminal消费者；R03 repeated UNION ALL及two import facades joint execution | C04 C12 C17 C18 C19 | E02 E03 E04 E07 |
| 12 | Complete emission artifact, dual-denominator closure and SQL-range queries | 汇总已有verifiers、独立完整性/无cycle/actual-byte range queries | C20 C21 C22 C23 C24 C25 C31 | E01 E05 E06 E07 |
| 13 | Project emit-SQL, explicit contract input, public output and legacy compatibility | installed console exact selection/input/output/error/atomic tests、独立public decoder与target submission | C03 C29 | E08 |
| 14 | Private emission observation and first real process/relocation/wheel integration | private schema/parser/correspondence+standalone/正反batch/同child origin，保留历史 | C29 C32 | E06 E08 E09 |
| 15 | Expanded target/differential conformance and historical compatibility | 扩corpus/mutations/joint outcome、完整两target与历史process streams | C01–C32扩大组合；C30 | E03 E04 E09 |
| 16 | Completion audit and exact Phase67/68/later handoff | audit only，逐E/ledger/rule消账，核对R03的07/10/11 joint receipts，无implementation catch-up | C01–C32处置，不能补实现 | E01–E10最终审核 |

“first”在Slice14标题中只修饰private emission observation这一个新产品的
standalone/batch/relocation/wheel消费。Slice3已经拥有target facility内真实installed-wheel→
public artifact decode→submission证据；Slice13交付installed public CLI，14不重置或推迟它们。

### Workload alternatives

**12:** 把02基础设施与03扫描合并、04共享与05参数合并、12完整artifact与13公共CLI合并、
14 process与15扩展conformance合并。四个独立failure surfaces重叠：资源/target与lowerer归因、
身份与wire values、proof completeness与I/O、首次portable消费者与大corpus。少四次发布但每步
定位/回退面更大，且容易把设施或first consumer拖后；不选。

**14:** 只合并04/05及14/15，仍让scope/capture与typed wire mapping同批、first portable
integration与扩展矩阵同批。少两次发布，但均跨独立根因；不选。

**16 (selected):** 02仅设施，03才首个new emission；后续stage、完整artifact、CLI、portable、
扩展assurance各有真实交付和独立失败面。额外publication成本明确，不声称测得提速。
Phase65 N16是已关闭历史，本N66=16为独立新route。不得回到overloaded Slice2。

## E01–E10 phase exits

| Exit | Required product outcome | Required independent acceptance |
| --- | --- | --- |
| E01 | Exact roots, explicit selected request/source/target and invalidation. | root/owner/contract/policy/envelope/target变动与graft negative，原project ERROR完整。 |
| E02 | Physical names/scopes/ports/terminal and result correspondence. | reused/rebound/completed/SET路径、capture/outer nulling、visible positional outputs。 |
| E03 | Nonempty real positives in both finite promised dialect domains. | R01–R22 promised正域两target真实收据；PG FULL restricted、MY FULL明确negative。 |
| E04 | Complete non-positive results without misleading successful SQL leakage. | all blockers、缺证据/冲突/unsupported/error/overflow、无partial SQL成功。 |
| E05 | Exact fixed values, physical type anchors and emitted parameter uses. | tags/large Int/signed zero、original literal→SQL use→server index及实际transport。 |
| E06 | SQL AST/text/ranges/original-origin correspondence through final bytes. | 独立结构与bytes checks、Unicode/range查询、actual submitted bytes一致。 |
| E07 | Independent completeness of original and introduced requirements. | 两denominator独立枚举，全部roots/premises、无循环自证；必要未fulfilled阻止。 |
| E08 | Usable installed Project emit-SQL with explicit input and legacy compatibility. | console实际argv/stdout/stderr/atomic file/contract读取、独立public decoder及旧API/JSON/SQL regression。 |
| E09 | Real target and deterministic process conformance in separate measured domains. | 实際target/env/driver与complete oracle；另记interpreters/seeds/relocation/wheel，缺required job无PASS。 |
| E10 | No concealed Phase66-owned gap; accurate later-owner/limitation handoff. | 逐rule/C/asset对照promise和证据；67/68/later准确接收，无catch-up/xfail/scope shrink。 |

发布Slice1只批准这十项exit及路线；**Phase66 exits are NOT SATISFIED by Slice1**。

## Primary-source review records

以下按2026-09-15实际读取的官方资料记录；页内容/发布版本和实际安装观察不同。
没有执行数据库、安装driver/image，未使用Calcite/DataFusion/SQLAlchemy/SQLGlot/Malloy/Cube
作语义替代；本任务无需额外框架比较。每条记录恰含11项。

### XREF01 Release and distribution identity

1. Snapshot/date: 2026-09-15；[PostgreSQL18.6 release](https://www.postgresql.org/docs/release/18.6/)、[MySQL8.4.12 release](https://dev.mysql.com/doc/relnotes/mysql/8.4/en/news-8-4-12.html)、[Docker image inspection](https://docs.docker.com/reference/cli/docker/buildx/imagetools/inspect/)。
2. Problem/constraints: 精确测试target，不能把family、release、distribution与实际server混同。
3. Semantic/identity model: PG18.6发布日期2026-08-13；18.5未发布。MY8.4.12发布日期2026-08-18，说明限定Server Docker image security update；不推导所有分发渠道存在同一package。
4. Layering/dependency direction: release说明描述vendor产物；image index/platform manifest和实际server identity由test acquisition验证，不进入semantic resolver。
5. Algorithms/data structures/complexity: manifest显式列各platform；只选已授权平台及digest，不展开所有平台matrix。
6. Interface/version/capability model: freeze family/release、channel、index/platform digest、build/platform及library版本；本次实际pins未获取。
7. Testing/operational lifecycle: Slice2获取并检查image/server/adapter；release-note修复不是本期Pietto执行证据。
8. Pitfalls/migration costs: PG release涉及outer-null constants、group comparison、window等修复；MY记录optimizer错误，故需要最小失败case和环境保留。
9. Disposition: ADAPT；采纳候选版本与身份分层，actual acquisition到Slice2。
10. WHAT_NOT_TO_COPY: rolling latest、自动降级、默认optimizer workaround或以发布说明替代conformance。
11. Pietto owner affected: D66.02/.16、P01、Slice2/15。

### XREF02 PostgreSQL relational, type and frame boundaries

1. Snapshot/date: 2026-09-15；[table expressions](https://www.postgresql.org/docs/18/queries-table-expressions.html)、[aggregates](https://www.postgresql.org/docs/18/functions-aggregate.html)、[SET type resolution](https://www.postgresql.org/docs/18/typeconv-union-case.html)、[SELECT/window frames](https://www.postgresql.org/docs/18/sql-select.html)、[window modifiers](https://www.postgresql.org/docs/18/functions-window.html)；官方[REL_18_6 joinrels.c](https://github.com/postgres/postgres/blob/REL_18_6/src/backend/optimizer/path/joinrels.c)经GitHub API实读，blob `aad41b940091db693e2b570199c3db3ca3d9d3ea`。
2. Problem/constraints: 保持完整terminal、NULL、empty aggregation、类型与frame，不从keyword存在推导全域实现。
3. Semantic/identity model: table引用可能含inheritance descendants；COUNT忽略NULL与COUNT(*)不同；SUM(int8)/AVG可返回numeric；SET逐列、嵌套逐次决定类型。
4. Layering/dependency direction: vendor parser/planner/executor规则是target约束；Pietto原proof/identity由上游拥有。
5. Algorithms/data structures/complexity: FULL无可用join path时源码报feature-not-supported；R09因此选择更窄builtin equality域，不承诺任意ON。
6. Interface/version/capability model: PG18 offset RANGE要求一个ORDER key与适用offset类型；RESPECT NULLS/FROM FIRST只具默认行为，未实现其modifier拼写。
7. Testing/operational lifecycle: C06/C07/C14/C16及aggregate/SET类型逐target执行，不能只靠SQL parser。
8. Pitfalls/migration costs: 盲目ONLY、最终CAST、SET common type或FROM LAST反转ORDER都会改变契约。
9. Disposition: ADAPT；R01/R09/R13/R15/R16/R22设精确前提和首版negative。
10. WHAT_NOT_TO_COPY: backend FD自动识别、planner重排、materialization时机、隐式type coercion作为Pietto语义。
11. Pietto owner affected: Slice3/7–11、D66.04/.07/.08。

### XREF03 MySQL value, comparison and operator domain

1. Snapshot/date: 2026-09-15；[numeric types](https://dev.mysql.com/doc/refman/8.4/en/numeric-type-syntax.html)、[GROUP BY](https://dev.mysql.com/doc/refman/8.4/en/group-by-handling.html)、[aggregate results](https://dev.mysql.com/doc/refman/8.4/en/aggregate-functions.html)、[SET operations](https://dev.mysql.com/doc/refman/8.4/en/set-operations.html)、[window restrictions](https://dev.mysql.com/doc/refman/8.4/en/window-function-restrictions.html)、[padding](https://dev.mysql.com/doc/refman/8.4/en/char.html)、[collations](https://dev.mysql.com/doc/refman/8.4/en/charset-mysql.html)、[max_sort_length](https://dev.mysql.com/doc/refman/8.4/en/server-system-variables.html#sysvar_max_sort_length)、[JOIN syntax](https://dev.mysql.com/doc/refman/8.4/en/join.html)。
2. Problem/constraints: MySQL语法/物理types与logical Bool、比较、分组及窗口不能一一按名字替换。
3. Semantic/identity model: BOOL是TINYINT别名，nonzero truth不等于仅0/1；NO PAD保留尾空格，PAD SPACE忽略；prefix limit可影响PAD SPACE排序/分组/DISTINCT。
4. Layering/dependency direction: exact session/source comparison属性供lowerer applicability检查，不能重写原key/FD/proof。
5. Algorithms/data structures/complexity: 按实际SELECT计windows（文档上限127），按每列检查SET result类型，不按logical window定义数估计。
6. Interface/version/capability model: 8.4支持三SET×ALL/DISTINCT；GROUPS/EXCLUDE/IGNORE NULLS/FROM LAST虽可parse仍不支持；原生JOIN语法无FULL。
7. Testing/operational lifecycle: R10明确FULL negative，R14–R22实测finite positives；ONLY_FULL_GROUP_BY保持启用。
8. Pitfalls/migration costs: SUM/AVG exact输入输出DECIMAL，不能直接当输入Int；R13首版明确拒绝未reviewed promotion。不能ANY_VALUE或关闭strict grouping修复。
9. Disposition: ADAPT；V02/V03及rule-level前提，使用utf8mb4_0900_bin的NO PAD域。
10. WHAT_NOT_TO_COPY: arbitrary truthiness、隐式coercion、collation默认、FULL emulation、optimizer_switch掩盖红例。
11. Pietto owner affected: Slice3/5–11/15，D66.02/.04/.05/.07/.08。

### XREF04 Names, CTE visibility and sharing

1. Snapshot/date: 2026-09-15；[PG lexical identifiers](https://www.postgresql.org/docs/18/sql-syntax-lexical.html)、[PG WITH](https://www.postgresql.org/docs/18/queries-with.html)、[MY WITH](https://dev.mysql.com/doc/refman/8.4/en/with.html)、[MY identifier limits](https://dev.mysql.com/doc/refman/8.4/en/identifier-length.html)。
2. Problem/constraints: 生成名可唯一但仍capture physical source，CTE共享不等于所需evaluation semantics。
3. Semantic/identity model: PostgreSQL通常identifier上限63bytes；MySQL表/列64characters、alias256characters并有使用场景例外；namespace lookup而非quotes决定绑定。
4. Layering/dependency direction: lowerer检查新SQL绑定，保留Pietto ports；不返向解析用户meaning。
5. Algorithms/data structures/complexity: deterministic bounded internal names、显式column lists及closed scope traversal；按目标单位检查最终label。
6. Interface/version/capability model: MySQL derived tables可遮CTE，CTE可遮base tables；PG CTE可有folding/materialization选择。
7. Testing/operational lifecycle: C10/C11/C19/C32使用同名physical源与不同carrier/use；真实执行检验绑定和allowed joint outcomes。按 Slice4 新授权修订，04仅named chains真实执行，JOIN/ORDER/SET joint outcomes分别由07/10/11交付。
8. Pitfalls/migration costs: quoting不能消除capture；长label截断、numeric ordinal或output alias依赖导致错绑。
9. Disposition: ADAPT；R03/R19显式namespace和terminal检查，case/length为target premise。
10. WHAT_NOT_TO_COPY: mandatory全局materialization、随意CTE inline/copy、optimizer成本搜索或backend别名winner。
11. Pietto owner affected: 原排期 Slice4/10、D66.06/.09/.14；R03修订后的joint execution owners另含Slice7/11，决策边界不变。

### XREF05 Server parameter forms and byte positions

1. Snapshot/date: 2026-09-15；[Psycopg cursor types](https://www.psycopg.org/psycopg3/docs/advanced/cursors.html)当前页面为3.3.6.dev1文档；[Connector/Python prepared cursor](https://dev.mysql.com/doc/connector-python/en/connector-python-api-mysqlcursorprepared.html)、[PG protocol error fields](https://www.postgresql.org/docs/18/protocol-error-fields.html)。
2. Problem/constraints: 提交SQL必须绑定最终bytes与精确参数，不能未经验证改placeholder/ranges。
3. Semantic/identity model: logical slot、SQL use、server index不同；PG error position是1-based characters，internal query position另有字段，不等于UTF-8 bytes。
4. Layering/dependency direction: compiler产生server form；test adapter消费固定artifact，不获得rebind或semantic修复权。
5. Algorithms/data structures/complexity: renderer events记录use order和range；authenticated original-query位置可线性按UTF-8 prefix换算，无text-search猜测。
6. Interface/version/capability model: RawCursor自3.2提供原生$n且只接受positional参数；MY prepared cursor接受?或%s，每marker一个值。选择?不证明cursor避免rewrite；该历史snapshot的stable adapter pins由Slice2获取。当前Slice5使用相同26.7 pure driver的native methods，并观察actual command payload。
7. Testing/operational lifecycle: 对实际adapter版本检查submitted SQL与params、type metadata、large Int/signed zero/Unicode及complete result。
8. Pitfalls/migration costs: 普通Psycopg Cursor的%s接口不同；不能拿开发文档版本当安装pin或假定所有driver都保留SQL。
9. Disposition: ADAPT；D66.10/.12的直接server-form策略和独立mapping验证。
10. WHAT_NOT_TO_COPY: generic placeholder重写framework、caller重绑、引用error snippet猜位置、internal query位置当原SQL。
11. Pietto owner affected: Slice2/5/12/15。

### XREF06 Recovery and complete diagnostics

1. Snapshot/date: 2026-09-15；[Psycopg transactions](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)、[MY implicit commits](https://dev.mysql.com/doc/refman/8.4/en/implicit-commit.html)、[MY SHOW WARNINGS](https://dev.mysql.com/doc/refman/8.4/en/show-warnings.html)。
2. Problem/constraints: 预期错误之后还能正确查询，且观察/cleanup失败不可丢失。
3. Semantic/identity model: returned rows、query completion、diagnostic total/details、transaction recovery是不同状态。
4. Layering/dependency direction: test harness owns session/fixture生命周期，production compiler仍零连接。
5. Algorithms/data structures/complexity: bounded完整结果与diagnostic buffer、原query后立即capture、逐acquired resource close；overflow typed failure。
6. Interface/version/capability model: PG failed transaction需要rollback；MY DDL可能implicit commit，即使部分temporary DDL不commit也不能依赖rollback撤销。
7. Testing/operational lifecycle: success→expected exact failure→success；query及cleanup双失败均保存；fixture loading也观察warnings。
8. Pitfalls/migration costs: MY warning计数可超过max_error_count存储条数，下一语句可影响诊断；读取不到details不是零warning。
9. Disposition: ADAPT；P04–P07与C26/C27作为Slice2最低实际consumer。
10. WHAT_NOT_TO_COPY: connection默认事务当所有target一致、任意exception算expected、prefix-result成功或finally覆盖原failure。
11. Pietto owner affected: Slice2/15，未来产品resources归68。

### XREF07 pytest collection and cleanup

1. Snapshot/date: 2026-09-15；[fixture lifecycle](https://docs.pytest.org/en/stable/how-to/fixtures.html)、[exit codes](https://docs.pytest.org/en/stable/reference/exit-codes.html)。
2. Problem/constraints: no-test、fixture setup失败及teardown failure都不能伪装成target PASS。
3. Semantic/identity model: collected case identity、executed outcome、fixture instance和cleanup ownership分别记录。
4. Layering/dependency direction: DB collection是单独test入口，常规authoritative保留旧tests，harness/unit在默认validation。
5. Algorithms/data structures/complexity: 有限独立manifest对比实际collection/outcomes；不扩Python×driver×server×seed组合。
6. Interface/version/capability model: 无tests collected为exit5；exit0也必须与非空required manifest对照。
7. Testing/operational lifecycle: 每项acquire成功即注册cleanup；不能仅在尚未到达的yield之后布置清理。
8. Pitfalls/migration costs: marker+缺环境skip不足以成为独立DB成功域；同一fixture并发重用会污染结果。
9. Disposition: ADAPT；P03/P06/P08明确collection/cleanup和serial fallback。
10. WHAT_NOT_TO_COPY: 测试框架承担production资源管理、online默认discovery或skip/xfail解除承诺。
11. Pietto owner affected: Slice2/15，当前static principal仅普通offline测试。

### XREF08 Natural CI, artifacts and permissions

1. Snapshot/date: 2026-09-15；[GitHub secure use](https://docs.github.com/en/actions/reference/security/secure-use)、[workflow artifacts](https://docs.github.com/en/actions/tutorials/store-and-share-data)。
2. Problem/constraints: natural exact-head结果、执行代码身份、跨job artifact及aggregate acceptance必须闭合。
3. Semantic/identity model: commit、installed wheel、artifact bytes、submitted query、actual server与oracle各有独立证据，hash只识别相应bytes。
4. Layering/dependency direction: CI观察candidate；CI/provider成功不是language authority，外部artifact不能赋予源码权限。
5. Algorithms/data structures/complexity: 有限job manifest与receipt逐项核对，artifact传输不塞大job outputs。
6. Interface/version/capability model: upload/download artifact有digest检查，但文档描述mismatch可仅warning；本设施须显式使不匹配验收失败。
7. Testing/operational lifecycle: 两target必需job不允许missing/skipped/cancelled/empty取得aggregate PASS；compiler两Python jobs保留原四required步骤。
8. Pitfalls/migration costs: privileged pull_request_target/workflow_run结合untrusted checkout有风险；只读repo permissions和精确action pin随Slice2重新审查。
9. Disposition: ADAPT；future natural CI消费完整artifact receipts，保持failed head/run。
10. WHAT_NOT_TO_COPY: privileged PR自动执行、admin bypass、manual rerun、digest即correctness、空aggregate成功。
11. Pietto owner affected: Slice2/14/15；本Slice publication仅现有CI。

## Slice1 validation, repair and publication

新static principal只检查finite gate/decision/ledger/rule/C/route/exit结构、真实cited entrypoints及
material兼容/信任区别，复用 `REPOSITORY_FACTS`，不作prose theorem prover或运行时证明。
不加在线依赖、historical Git-object skip、carrier-layout snapshot、全repo哈希或第二lifecycle/
inventory reader。现有 `tests/test_active_phase_lifecycle.py`独占mutable status/roadmap；
现有validation static-stage test独占本次production/test file inventory更新。

初始写作和可预见reader迁移是planned work。genuine corrections按完整cause计组，最多6；
第4组后检查收敛。local authoritative starts最多4；首发ordinary commit1次，remaining scope/
budget内至多1个普通natural-CI repair child。实际start/failure/outcome在指定仓库外目录持久记录，
中断不重置；不借Phase65已关闭预算。cap到达但全部完成不自动FAIL。
material新矛盾、需要第七路径、改变产品/信任决定、持续competing writer或未知published进展
必须保留candidate/evidence并STOP；本任务不许可production修复。

先完成所有内容及完整finding-set审查，按cause修正文档/static test，运行两个locked Python
3.12/3.13的focused initiation/lifecycle/inventory compatibility，Ruff/format和production/test
Pyright。然后final-input freeze并运行：

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
UV_PYTHON=3.13 uv run python scripts/check_generated.py
UV_PYTHON=3.13 uv run python scripts/check_goldens.py
UV_PYTHON=3.13 uv run python scripts/package_smoke.py
```

authoritative保留优化repository acquisition、xdist兼容与serial fallback、既有process覆盖；
不重复相同full matrix只为多一个数字，不推断skip reasons。后续candidate edits需要renewed
applicable evidence。Gate2 seal是实际tested Git tree；Gate3 rebind HEAD/index/worktree/remote/
fast-forward与publication progress，stage六路径且staged tree等于seal，ordinary commit parent
必须是接受baseline，再normal push origin/main。用户已明确授权，不因routine mechanics重复问。
若正常approval机制要求tree-specific直接确认，则保留seal，只请求那一次精确publication批准。

成功必须是自然exact-head push/main/attempt1、Python3.12/3.13 jobs及authoritative/generated/
golden/package四步骤全部成功。失败首发不得amend/rebase/force/rerun/cancel/dispatch；只可在
剩余预算六路径内普通child修复。无PR绕路、tag/release/package publish、status-only后续commit。

Author/Ponytail/internal read-only review is not third-party review。
Documentation/source research is not target execution or implementation proof。
不宣称implemented lowerer、installed database facility、universal support、runtime fulfillment或
Phase66 completed；发布成功后也不自动开始Slice2。

## Controlling repository references

- [AGENTS](../../AGENTS.md) / [development](../development.md)
- [Product architecture](../architecture/product-architecture-v1.md)
- [Identity laws](../architecture/identity-and-authority-laws-v1.md)
- [Layering laws](../architecture/layering-and-coupling-laws-v1.md)
- [Initiation gate](../architecture/phase-initiation-gate-v1.md)
- [Product design lessons](../references/product-design-lessons-v1.md)
- [Phase65 initiation](phase65-project-sql-plan-product-phase-initiation-gate-source-audit-architecture-route-lock-v1.md)
- [Phase65 completion/handoff](phase65-completion-audit-phase66-handoff-v1.md)
- [Language](../language.md) / [Project/package](../project-package.md)
- [CLI JSON v1](cli-json-v1.md) / [Project JSON v2](project-cli-json-v2.md)
- [Configuration](pietto-config-v1.md) / [Diagnostics](diagnostics.md)
- [Metadata artifact](semantic-metadata-artifact-v1.md) / [Golden policy](golden-fixture-policy-v1.md)


## Post-publication R14/R15/R23/R24/R26 residual disposition

The [post-publication supplement](phase66-pre-slice16-completion-corrective-closure-v1.md#post-publication-residual-supplement)
corrects the earlier agent's interpretation of the MySQL origin restriction: admitted
literal and materialized aggregate carriers remain inside R14/R15's finite promise.
Retained expression metadata and the actual generated materialization boundary determine
the window result; storage tags alone do not prove an expression's server metadata.
R23 independently binds each row result image to its verified expression/input. R24/R26
consume all supported window-owning definitions in their own scopes, with complete
statement inventories and independent corruption controls. B1, G1, R15-INT-OFFSET-V1,
P/default enclosure, G2/G4/G5/G6 and all other approved boundaries remain unchanged.
The successful predecessor `fa44de88` and its raw receipts are retained; this supplement
needs a separate ordinary successor and fresh exact-head compiler/package/target evidence.
It changes no macro phase decision, numbered Slice, public format or package version.
