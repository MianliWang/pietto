# Phase 65 ProjectSQLPlan Product Initiation Gate, Source Audit And Route Lock v1

## 0. Authority, status, and use

本合同是 Phase65 Slice1 的首次 repository publication version `v1`，设计来源是
2026-09-10 的完整替代 DESIGN_PACKET **v2**，不是旧 planning v1。用户委托的
Slice1 prompt 采纳 D65.01–D65.12 与 N=16，限定本次为 documentation/static-only。
这些是本任务的新决定，不回填 Phase64 的历史批准；配套 REVIEW_REPORT v2
仅解释修订，不扩大写权限。此前缺附件的 STOP 未产生候选、验证或发布。

本次 foreground primary agent 重新读取本地实际源码、现行 architecture、AGENTS、
development、language、project-package、diagnostics 及 Phase64 completion handoff。
`git fetch origin main` 后 HEAD/main/cached/live main 同步、分歧0/0、index/worktree/
untracked 全净，无 merge/rebase/cherry-pick/revert/bisect/lock。基线为：

```text
commit = d7af544dd4ce48891d5fe2596ab23e494f48d4ab
tree = 39725359e10660ef425eb831164e100cbf649e0b
parent = ceccba408d042c3bfe08c90a9c67b57cd690541a
subject = Complete Phase 64 audit and Phase 65 handoff
natural CI = 34460962668 / push / main / attempt 1 / success
Python 3.12 job = 102818430316
Python 3.13 job = 102818430536
```

本次 GitHub API readback 确认上述两个 job 的 authoritative validation、generated、
golden、installed-package 四项步骤均 success：[基线 CI](https://github.com/MianliWang/pietto/actions/runs/34460962668)。
这是基线证据，不是本候选的运行结果。Packet 所报 local12586 / CI12581+5 skips
属于继承记录，本候选最终 receipts 只在仓库外保存，不靠反复追加文档重跑验证。

在基线，Phase64 = COMPLETED（D07-FLOAT-DEFERRED、S9-NAME-1 保持），
Phase65 = NEXT / NOT STARTED / no approved numbered route。本合同的成功
ordinary commit + ff push + natural exact-head push/main/attempt1/success 才建立：

```text
Phase64 = COMPLETED
Phase65 = ACTIVE
Phase65 Slice1 = COMPLETED / PUBLISHED
Phase65 Slice2 = NEXT / NOT IMPLEMENTED
Phase65 Slices3–16 = NOT IMPLEMENTED
N = 16
```

所有未来 plan file/class/API spelling 均为 **PLANNED**；下文只把明确的现存
source/test 路径当当前实现。Slices2–16 仍须各自授权。没有 Phase65 production PASS。

## 1. Product outcome and architectural boundary

Phase 65 produces a **private, target-neutral SQL-oriented plan for one explicitly selected completed TABLE/QUERY result**, with a referenced query-block graph, scope-safe field references, typed fixed-literal/bind transport, role-tagged planning origins, complete requirements, and separate target assessment. It consumes the actual Phase-64 VERIFIED query-block IR and its retained semantic roots.

It is not merely another wrapper around Project IR: its new responsibility is to decide and record the SQL query-block boundaries and ports needed to preserve existing stages, assign scope-local symbols, expose parameter uses, and state exact lowering demands. It is also not a dialect SQL AST, emitted SQL, executable statement, result transport, optimizer, or second semantic resolver.

```text
completed semantics + exact VERIFIED Project/Query-Block IR
    -> selected-result ProjectSQLPlan + input/output correspondence
    -> independent plan verification + runtime inspection
    -> optional explicit target-requirement assessment
    -> later Phase-66 dialect SQL AST / rendering / emission binding map
    -> later Phase-68 execution and requirement fulfillment
```

The neutral plan remains meaningful when a backend cannot implement it. Structural plan validity, target requirement satisfaction, actual lowerer implementation, and runtime fulfillment are different claims.

## 2. Corrected decisions D65.01–D65.12

These decisions are adopted by the delegated v2 Slice1 task, subject to this fresh source-backed gate; they are not retroactive Phase64 approvals. Exact private class and enum spellings are implementation freedom; the meanings and limits are not.

### D65.01 — Selected result, root eligibility, and three independent outcomes

A private request selects exactly one TABLE/QUERY **owner occurrence from the supplied snapshot**. A string, alias, last output, largest ordinal, or equal-looking reconstructed owner is not selection authority. Source declarations remain dependencies, not additional selected result kinds.

Require a concrete completed-semantic result with its existing `.ok` true, the exact current query-block VERIFIED/analysis bundle, and their full Phase61/62/64 root continuity. Then require the selected entry and every consumed predecessor to have the exact active output/properties. `completed.ok` alone is insufficient; VERIFIED alone is insufficient because a graph can contain typed terminals. Do not rerun semantic constructors inside the planner or verifier.

Keep the existing whole-project semantic-error policy. A healthy owner in a project with another ERROR does not become plannable by cropping diagnostics. Once the whole semantic prerequisite succeeds, restrict *planning* to the selected dependency/evidence closure; an unrelated operator not yet supported by the incremental planner must not block that closure. Distinguish an unrelated planner limitation from an upstream semantic ERROR.

Retain the complete original diagnostic tuple as **project diagnostics**, unchanged. Attach only exact reachable obligations to the selected plan's **requirement inventory**. An unrelated LEGAL_UNPROVED warning can remain visible in the project diagnostics without becoming a demand on this selected result. Do not filter original diagnostics by matching names/messages/paths or invent a global diagnostic-attribution engine.

The public meanings of existing `ok` do not change. The new private boundary distinguishes:

| Product | Positive meaning | Negative/unfinished meaning |
| --- | --- | --- |
| Construction | exact complete plan within the current supported operation domain, including every required demand/origin | typed unavailable result with complete blockers; no partial plan passed as concrete |
| Independent plan verification | the supplied plan agrees with exact upstream roots and all mandatory inventories | invalid; cannot inspect/target-assess as verified |
| Target assessment | per-demand evidence for one explicit target, with scoped aggregate reporting | NOT_ASSESSED, missing/unknown, unsupported, conflict, or pending realization/fulfillment as appropriate |

No universal success bit spans all three products. Later support for selected-owner compilation amid semantic errors is a **proposed** Phase69/70 policy extension, not an existing approved capability.

### D65.02 — Closed SQL-planning structure, use graph, and stage boundaries

Use a referenced, acyclic SQL-oriented graph, not opaque payloads containing an old IR node and a new label. The smallest logical categories are **source bindings**, **SELECT-block definitions**, **SET query-expression definitions**, and **uses of their exported ports**. SELECT-block formation records which expressions/clauses belong to which scope and which preceding boundary they consume. SET bodies retain operation, explicit quantifier, left-fold/nested structure, ordered operand uses and positional output ports; they are not SELECT blocks with fabricated projections.

Each definition owns a scope, its exact source/IR mapping, visible exports, private helper ports where legitimate, and semantic-stage obligations. Each input use owns its ordered port mapping and exact producer. Definitions can be shared; uses cannot be deduplicated. Final selected exports map back to canonical semantic field identities; generated ports never replace those identities. Names are optional presentation, not graph edges.

Initial construction is deterministic and **non-fusing**: introduce a boundary whenever carrying a value into the next clause would otherwise violate the retained stage/visibility rules. The implementation must record a reason (named input, aggregate result, window result/QUALIFY, DISTINCT quotient, or order/limit nesting). It must not promise one SQL SELECT per IR node or one SQL statement per block. A target lowerer later realizes the structured boundary, or rejects it; it must not reconstruct a lost boundary from source text.

The same block-context adapter must serve SELECT, ON, WHERE, GROUP, satisfying, WINDOW, QUALIFY and relation ORDER. A scope crossing uses an explicit exported port, never an old base qualifier. Adding a helper does not expand the visible output schema or the DISTINCT comparison tuple. Private post-quotient requirements that cannot be expressed as a visible port use an explicit evidence-backed requirement, not a dangling ordinary field reference (D65.04).

Generated scopes do not authorize authored subqueries, LATERAL, outer capture, recursion or decorrelation. Named producer reuse does not imply materialization or evaluation once. No CTE spelling, copy expansion, predicate pushdown, JOIN reordering, aggregate repair, CSE, or cost search is selected in Phase65. A graph cycle is invalid, not an implicit fixed point.

From Slice2 onward, an encountered but not-yet-supported reachable stage returns a typed planner terminal. It must never disappear or be treated as a pass-through. A plan is concrete only when every reached stage is covered by the current builder, verifier, runtime observation, origin and demand rules.

### D65.03 — Context-sensitive identity and positive scope membership

Reuse exact semantic/IR identities. Mint only necessary plan-local nominal domains: snapshot scope, block/query expression, input use, output/stage port, expression site and bind slot. Every retained reference has an owning domain and exact upstream correspondence; a matching name/type/position is not enough.

An expression site's identity includes its **source occurrence and evaluation/instantiation context**. Reuse of a callable body, LET source or named relation can expose the same AST object in different consumers. AST object identity alone is therefore not a sufficient key for a plan expression, parameter use, field replacement or origin. Conversely, multiple uses of one already-established stage value reference that value; they do not rebuild its expression and fresh literals. This is essential for grouped-expression reuse and repeated input roles.

| Reference role | Admissible source | Never sufficient |
| --- | --- | --- |
| External input | exact active producer + ordered input use + port map | missing producer, same schema, source name |
| Internal stage predecessor | explicit same-owner/scope preceding stage relation and its actual output | producer absence, ordinal0, smaller node number |
| Match predicate | exact accumulated-left and right pre-match input uses | post-outer-null-extended fields or later SELECT aliases |
| Post-SEMI/ANTI value | left output ports only | right predicate-local fields |
| Aggregate/window result | actual grouped/window stage port exported to that scope | pre-stage source qualifier or recomputed expression |
| Final result | exact ordered visible canonical field map | helper port or arbitrary final-looking node |

Allocate deterministic scope-local logical symbols in retained structural order. The symbol key includes its namespace (relation-use, field port, generated helper); display labels are independent. Later backend spelling must be injective in its actual namespace under quoting/case/length rules. Never truncate into collisions or silently rename a user-visible result label. Repeated producers in self-JOIN retain separate use symbols. No cross-snapshot stability promise is made; no Python id/hash/CWD/clock is serialized as identity.

### D65.04 — No invented semantics; explicit comparison, ordering and evaluation demands

Preserve BAG multiplicity, SQL TRUE-only predicate matching/filtering, outer nulling of the complete required side, SEMI/ANTI right membership dependencies, explicit set ALL/DISTINCT, authored EXCEPT nesting, visible-only DISTINCT and all existing key/FD/grain premises. Do not coalesce outer keys, rewrite ANTI as NULL-sensitive NOT IN, infer full ordering from window order, or turn subset/quotient grain into total cardinality.

The scope matrix includes the empty-input and zero-result cases. A GLOBAL aggregate can produce a row on empty input; GROUPED can produce none. COUNT(*) and COUNT(nullable-field) are different. LIMIT0 cannot license dropping a semantic error or an unfulfilled matching requirement, and a right input's own LIMIT1 proof cannot be substituted by a post-JOIN LIMIT1.

**DISTINCT + hidden ORDER:** a strict-FD proof that a hidden key is determined by a visible row is not a syntax-level ability to reference that key after projection/quotient, nor proof a database recognizes the FD. The neutral plan retains a dedicated determination demand linked to the original item, visible tuple, source/property/FD witness and stage. It does not expose the hidden key as a normal result port, add it to DISTINCT, or compute first/min/max. Phase66 must certify an exact realization or reject; the original Phase64 semantic success is not rewritten as failure.

**GROUPED dependencies:** an upstream semantic FD remains a fact with its scope/NULL policy; it is not automatically permission to emit a non-grouped column in a backend GROUP BY. Preserve existing valid group/aggregate outputs and record any target realization requirement.

**Order/effects:** distinguish window order, row-selection order, and final presentation order. Preserve authored order items and unspecified ties/NULL-order posture as such; do not add a tie-break key, collation or determinism promise. Non-fusing blocks preserve logical boundaries, not physical evaluation timing. Unknown purity/error/evaluation-count facts are retained and block any *transformation requiring them*, not ordinary neutral construction. No eager Python evaluation/constant folding is allowed. Runtime single evaluation, materialization and backend exception timing cannot be claimed solely from a subquery/CTE boundary.

### D65.05 — Typed fixed-literal transport with an explicit eligibility contract

Existing `Parameter`/`parameterList` belong to constraint/derive declarations, not query placeholders. This phase's proposed parameter deliverable is deliberately **fixed-value transport**, not a caller-rebindable query API. No source grammar, CLI flag, environment callback, secret provider or hidden substitution of semantic inputs is added. General semantic query parameters are a proposed later open-plan/API decision for Phase70 and Phase69/82, not a feature silently declared implemented here.

Two private policies are supported: `PRESERVE_LITERALS` (default) and `BIND_SAFE_LITERALS`. The second means 'extract the exactly admitted occurrences below'; it does not mean all literals or all values are safe on all databases.

**Eligibility v1 — all conditions required:**

1. A real retained `LiteralExpr` has exact literal-level semantic type evidence in its actual expression environment. Reading that evidence is allowed; calling `infer_row_expression`, name resolution or the semantic compiler from planning is not. Never infer literal type from its parent result type or host value alone.
2. Its semantic type is builtin Bool, Int, Text, or finite Float. Alias/enum/domain/Decimal/date/time/bytes/JSON values are not guessed into this set. Untyped NULL stays a NULL expression. Float equality deferral remains unchanged.
3. Its use is an ordinary selected scalar, row LET, WHERE or ON expression, following only already-supported unary/binary/comparison/Boolean/NULL-test expression edges. **Function-call, aggregate and window argument subtrees are initially not extracted**, even when an argument looks like data. New function-position support needs an exact argument-role rule, not a 'not on a blacklist' heuristic.
4. It is not within GROUP/window partition/order, relation ORDER, LIMIT/frame/type/source-connector/profile/alias syntax or another structural site. Bound uses already present in an earlier stage value may pass through these stages without re-extracting its expression.
5. Its exact contextual occurrence, source, type, original decoded value and all new uses are retained. No computed folding, subtree rewrite, or changed overload/collation/equality claim follows from extraction.

Each encountered literal receives an explicit `BOUND` or `PRESERVED_WITH_REASON` disposition under this policy. Unknown context/type means preserve with the reason, not invent a bind and not silently claim extraction of everything. This deterministic eligibility decision is not an execution fallback. Missing mandatory *plan* evidence still blocks the plan.

A slot is rooted in (planning snapshot, retained literal occurrence, actual definition/instantiation context); each use has its own identity. Distinct equal literals remain distinct, including Bool true versus Int1. Existing references to one group/stage value retain that value rather than rebuilding identical-looking expressions into different slots.

The binding envelope is complete and immutable: no missing, extra, duplicate, reordered-by-value, wrong-type, or foreign-root slot/value associations. The validator compares against the original typed source value, not generic Python `==`: true must not match1, Int1 must not match Float1.0, and signed floating zero cannot be silently normalized. The original semantic Float value, not reparsed source text or a host-inferred new type, is transported. Negative literals represented as unary syntax retain that syntax; no new folding rule is introduced.

**Value preservation is not target type preservation.** Every extracted slot carries a target demand for exact data representation, nullability, range/precision, argument/operator context and, where relevant, collation. A server/driver can infer different parameter types in different positions; a literal replaced by a bare placeholder is not certified equivalent just because the bound value is equal. Phase66 owns real SQL type anchors/casts/parameter metadata and driver mapping, and must prove the original typed operation/result is preserved or reject. No source rebind or silent literal fallback may bypass this demand.

Logical slot order is deterministic in the selected plan, but it is not SQL placeholder order. Phase66 emits an explicit occurrence-to-slot map in actual statement order; one slot may need several positional values and one source occurrence may occur in several generated blocks. Repeated slot use is not duplicated parameter identity.

Private runtime plan verification binds the envelope to exact roots. Portable consistency cannot authenticate source values. No writable query template, prepared statement, execution-value validation or driver integration is claimed by P04.

### D65.06 — Physical sources without inferred locator or execution authority

Retain each reached source's exact existing connector identity, static argument evidence, source owner and span. Initial positive descriptors consume available validated static text; do not evaluate an expression merely because its root type is Text. Insufficient static locator evidence yields a typed source-planning blocker. The simple Slice2 scan must already retain its actual source descriptor; Slice3 generalizes sharing/imports/multiple uses, not the first capture of physical origin.

A locator string is neither an alias nor arbitrary SQL. Preserve its existing connector interpretation and spelling without guessing component boundaries. Existing backend consumers remain the authority for their accepted quoting/qualification; do not invent a new split-on-dot or parse-as-SQL convention in Phase65. Phase66 validates the actual target interpretation and quotes it through its own safe identifier representation.

Neutral planning retains mixed source demands without pretending they execute together. A known incompatible source dialect yields an explicit negative single-target assessment; two same-dialect sources do not prove a common database/connection or catalog availability. Phase68 later binds one explicit compatible execution context; federation/data movement remains tentative Phase94. No connection, search-path discovery, catalog lookup, credential or network is obtained in the compiler. Source identifiers are never data binds.

### D65.07 — Complete demand inventory and proposition-preserving assessment

Every admitted plan feature contributes its own requirement sites **from its first implementing Slice**, including source/type, operand context, stage/evaluation constraints, equality/ORDER and pending obligations. Slice11 completes cross-feature reporting/dedup-by-exact-use bookkeeping; it is not permission to omit requirements until then.

A requirement identifies the exact proposition, occurrence, operand/type/NULL/equality or function shape, source/proof roots, and applicable target dimensions. Keep ordered use occurrences even if one provider lookup can service several equal keys. The independent verifier enumerates mandatory sites from upstream facts/recognized plan shapes, not just the supplied demand list: deleting the list must not make `all([])` certify a plan. If a newly admitted shape has no demand rule, it is not yet a complete plan shape.

Assess only an exact VERIFIED plan plus an explicitly supplied target/profile/catalog and evidence. Reuse existing key/lookup/completeness contracts. `Found` means a fact was found; it is not necessarily supported. `Absent` means complete-domain no fact; `Unknown` means incomplete knowledge; `Conflict` preserves all conflicting facts. None is silently mapped to support. An omitted target gives NOT_ASSESSED.

**Preserve the question answered by evidence.** Current capability facts are descriptive and key/context scoped; a syntax-membership fact, legacy lowering fact, extension catalog entry, or support for one inline window call cannot answer 'this entire new plan is realizable'. Inspect key, context, operands, provenance and version/target scope. Missing schemas or a missing exact mapping produce typed unresolved demands, not a new catch-all capability boolean. Existing release-free keys do not prove every release: keep the profile/catalog release applicability separately or leave that claim unresolved.

For one plan, retain per-demand results and all blockers. Aggregation reports whether every required mapped proposition is satisfied and separately retains unsupported, absent/unknown, conflict, missing realization, and pending runtime obligations. Mixed failures are not reduced to an arbitrary first winner. A successful assessed subset must be labelled a subset, never whole-plan support. A positive **complete requirement assessment** requires the independently verified inventory to be complete, every demand to have an applicable mapping and satisfying evidence, and no unsupported/absent/unknown/conflicting result; unrepresented or unmapped demands cannot be removed before aggregation. Pending realization/fulfillment remains a separate non-executable posture even when the relevant capability questions are satisfied. A partially explicit profile is evidence, not a complete backend catalogue by assumption.

Real positive tests must use exact *existing* evidence for propositions it actually supports; synthetic provider facts can test state mechanics but cannot establish database conformance. No speculative wide backend catalog is required. Factor a genuinely needed lowerer-local pure decision into a neutral owner only in the implementing Slice with explicit path/migration review; do not make planning depend on a SQL renderer.

The assessment is not an executable certification: backend demand satisfaction, implementation of a Phase66 strategy, actual installation and Phase68 fulfillment remain distinct. Unsupported syntax can be emitted only through a separately approved exact strategy later; never silently guess one here.

### D65.08 — Obligations and comparison promises survive planning

At the first JOIN/stage adapter, retain every applicable original private single-match assessment in the selected closure. Preserve direct/hop/whole-path scope, actual matched BAG occurrence unit, ordered boundaries/input pairs, exact proof and Diagnostic object. Whole-path requirements remain whole-path; do not cut them at the selected output or lose right-only membership dependencies. If an obligation's required evidence cannot be retained, block construction rather than retain only its message.

PROVED remains scoped static evidence; LEGAL_UNPROVED remains `enforcement_required` with the same PIE-S2337 WARNING in all check modes; INVALID does not become a positive plan. A nullable match yielding UNKNOWN is not a match. SEMI/ANTI left0/1, post-JOIN LIMIT1, LIMIT0 or DISTINCT do not fulfill a matching obligation.

A complete neutral plan may have an unresolved target realization or unfulfilled runtime obligation. Phase65 reports it explicitly; Phase66 must retain a separately authorized fulfillment path or refuse executable emission; Phase68 owns actual enforcement. This packet adds no runtime SPI, scalar-subquery/COUNT emulation or policy for silently dropping unmet obligations. It does not upgrade an upstream warning into a semantic error. Scope-relative target blockage and original check diagnostics are different outputs.

### D65.09 — Source identity, mapping roles, and disclosure policy

Capture origins from Slice2, not just in Slice12. An authored origin retains exact logical source/module and AST occurrence/span. A generated origin carries a closed reason and ordered immediate antecedent plan/evidence refs; no fake authored location is invented for a synthetic scope, alias or type anchor. A single chosen display location, if required by a diagnostic UI, is separate from the complete origin relation.

Distinguish at least **value**, **predicate/membership**, **type/proof**, and **generated-structure** provenance roles. EXCEPT's right input may contribute no output values while still controlling membership; source-map pruning must not erase it. Re-export retains the original defining source and explicit use-site trail; it does not rewrite the source to the consumer module. Reverse queries return all matching occurrences in deterministic order, not one first span.

Runtime identities require exact source ownership. Portable source locators declare their document-local role and logical path/owner; equal spans or equal source text do not authenticate runtime identity. Preserve an explicitly unavailable legacy source position as unavailable; never replace it with line1 to pretend it is authored. New generated sites must have real antecedents. Do not read the filesystem to fill a missing source during plan inspection. Where existing module/package identity distinguishes two equal logical paths, retain that exact identity as well; a basename or path string alone is not the source key. Host-derived CWD/temporary paths are not identity. Authored string values that happen to look like paths remain ordinary source data, not forbidden host-state leakage by spelling alone.

Current `Span` is one-based, half-open. `AstBuilder._end_position` counts Python text characters/newlines; retain that established parser coordinate domain. Do not reinterpret it as UTF-8 bytes, UTF-16 units or decoded-literal indexes. Include non-BMP and escaped-text cases in the source-map tests. Phase66 owns actual emitted-SQL ranges and its unit; Phase75 owns LSP/editor conversions. Plan nodes without SQL text have no SQL offset.

Diagnostics do not dump value payloads or arbitrary source snippets. Compiler core acquires no credentials/runtime binding values. **Private full plan observation may contain authored constant values and source locators, just as source evidence can; it is not automatically redacted or safe to publish.** This explicit disclosure avoids v1's ambiguous 'values absent' reading. Do not add a hash-based fake redaction guarantee. A future redacted export is a different product, not a substitute for full evidence conformance. Fixed transport payloads remain internal immutable data, never ambient callbacks.

### D65.10 — Independent verification, invalidation and total observation

Every implementing Slice adds its own closed variant support, verifier rule, runtime inspection and positive plus field-level deletion/wrong-role/foreign-root tests before it can claim a concrete plan. Shared type definitions are allowed; the verifier must not call builder/semantic resolver to create the expected answer. Witness verification checks the supplied witness and scope rather than running a second FD/type solver.

Whole-record count checks are insufficient: check mandatory link presence, role, owner, order, multiplicity and exact endpoints. In particular external producers cannot be absent, while internal predecessors require positive structural proof. Empty lists/tuples are only legal under their exact variant; zero is not absent and missing is not 'unknown support'. The verifier checks complete reachable operations, demand sites, origins and binding-use inventories against the authoritative input.

Invalidation follows explicit roots. Change of selected owner, source/semantic/IR proof root, literal policy or binding envelope requires construction and fresh plan verification as applicable. Change only of target/profile/evidence requires a new target assessment, not mutation of the neutral plan or reuse of an assessment attached to another root. A malformed/foreign/stale plan is rejected rather than repaired by inspection. No persistent identity or cross-snapshot proof cache is introduced.

Runtime observation starts with Slice2's first real plan. Slice14 introduces a distinct private portable version plus its **minimum real process-family integration**; its encoder, decoder, standalone entrypoint, schema/record inventories, relocation/install origin checks and direct historical readers must agree in that same Slice. Slice15 expands the already-working corpus and full conformance matrix, not missing infrastructure. All earlier runtime observers remain complete for their supported shapes.

Portable input is not executable plan import. Specify closed records/refs, all role-sensitive mandatory and optional fields, finite data, exact numeric tagging where required, version, and no duplicate declarations or foreign references. Ordered repeated **uses** remain legal and preserved; do not mistake them for duplicate declarations. If the boundary accepts raw JSON, duplicate object keys must reject before conversion into a mapping; exact Boolean/integer tags, unknown/extra fields and malformed numeric values must not be normalized into acceptance. A bytes/text parser and an already-parsed-document checker must have distinct input contracts. Unknown tags and malformed input yield normalized rejection/no canonical bytes; recursion/cycle/resource failure cannot become an uncaught parser exception or a truncated accepted graph. Pure consistency cannot prove the caller supplied the authentic source/IR or that the database satisfies an assumption. Runtime verification, not document bytes, owns that link. Historical Phase61–64 formats stay unchanged for unchanged inputs; lifted fixtures are explicitly classified, not blindly reblessed.

### D65.11 — Bounded graph work, no new framework

Use deterministic graph traversal/allocation over the selected reachable definitions and all uses; stable iteration comes from retained order. Do not expand shared graphs recursively, enumerate all equivalent expressions, or eagerly copy every transitive source path.

Let V/E/F/X/P/M denote reachable plan definitions, uses, field images, expression occurrences, bind uses and explicitly retained provenance edges. New construction/checking should be linear or near-linear in the data it actually materializes, with output-size accounting; existing upstream analyses and potentially quadratic reachability are measured separately, not claimed linear. No cost model, join-order search, persistent cache, generic pass framework, remote registry, new execution scheduler, or proof search.

Use existing resource-aware validation infrastructure. The in-memory plan adds no invented timeout or machine-specific resource quota. Its supported graph is finite and acyclic. The later untrusted portable input boundary must explicitly bound or iteratively handle bytes/records/reference depth using existing mechanisms; a declared limit gives a typed resource rejection, never truncation. Exact numeric limits are implementation choices reviewed with that consumer, not claims that all unbounded host inputs terminate safely. Prefer iterative traversal to avoid an accidental Python recursion ceiling. Do not set arbitrary machine-time assertions or invent benchmark improvements.

### D65.12 — Sixteen real deliveries and bounded cause-level repair

Select the 16-delivery route in section 8. Every implementation Slice has a principal invariant and a real first consumer; representation, local verification, and runtime inspection grow together. Portable interchange and whole-corpus process conformance are separate products, not one giant last integration Slice.

For each future implementation prompt, audit the full changed producer/consumer and temporary-negative reader chain before freezing exact paths. Review the complete finding set; correct a whole causal invariant rather than one failing line. Initial implementation and predictable migration are planned work, not retrospectively invented defect counts. Group mechanical fallout with its approved causal correction; preserve real failures and do not reclaim old budgets by relabeling them.

No phase-wide license for arbitrary repairs. Smaller per-Slice, explicit correction-group ceilings (normally 4–6 complete causal groups, set by that Slice) trigger a convergence review if exhausted; they do not silently trigger more budget. Live AGENTS/Git trust rules still apply. Phase 65 Slice 1 uses the narrow budget and paths in its prompt. Phase-64 47 entries are closed history.

## 3. Three exclusive planning ledgers

### 3A. INHERITED_CLOSED — reuse, do not reimplement

| Asset | Existing authority | Phase-65 consumer |
| --- | --- | --- |
| Typed completed outputs and diagnostics | project_completed_semantics / project_final_outputs | admission and explicit selected result |
| Canonical source/field/owner/use identities | module attribution, Project IR structural domains | source-to-plan correspondence and symbol binding |
| Exact completed dependency order | completion + VERIFIED analysis graph | reachable named producer graph |
| JOIN conditions, scopes, orientations | project_join_conditions/current_joins/algebra correspondence | matching blocks and requirements |
| DISTINCT/set semantics and exact types | project_row_equivalence/project_set_operations/final outputs | query-body formation and equality requirements |
| Row/property/grain/ORDER/Decimal facts | Phase-64 carriers and verification | reference-preserving plan evidence; no re-derivation |
| Single-match private assessments | project_single_match and IR retention | pending obligation collection and target assessment |
| Existing source connectors | semantic/source_connectors; existing source facts | physical source descriptors |
| Capability fact/provider/profile model | semantic capability owners + project environment | explicitly scoped target adapter |
| Diagnostic objects and source spans | errors / AST / actual logical module roots | private plan diagnostics and source maps |
| Runtime/pure historical inspection | Phase61–64 inspection contracts | compatibility controls and generic encoding reuse only |
| Optimized test acquisition | repository facts, differential acquisition/batch, lifecycle/inventory owners | reuse without new duplicate subprocess systems |

### 3B. TRANSFERRED_TO_PHASE65 — actual current deliverables

| Deliverable | Principal outcome | Non-goal | Completing slices |
| --- | --- | --- | --- |
| Selected-result plan and source descriptors | explicit owner -> concrete minimal plan or exact blocker | no partial-project bypass/public selector | 2–3 |
| Query blocks, symbols, typed stage references | scoped neutral structure retaining existing relational meaning | no general optimizer/authored subqueries | 3–9 |
| Literal parameter transport and logical bind layout | eligible data literals -> exact fixed payload/slot/use mapping | no arbitrary rebind or query parameter grammar | 10 |
| Demand and obligation report | complete requirements with original proof/diagnostic refs | no evaluator/enforcer | 11 |
| Full source maps | exact source-to-plan/reverse queries and generated-origin reasons | no real SQL character offsets | 12 |
| Explicit target assessment | supplied demands × exact provider evidence -> closed outcomes | no emitter/install/discovery/federation | 13 |
| Portable plan observation | real typed records + total role-aware consistency check | no executable deserialization | 14 |
| E2E/differential and handoff | actual corpus through all current consumers, completion evidence | no new production caught-up at audit | 15–16 |

### 3C. RETAINED_LATER — exact remaining owners

See section 6 for every Phase 66–97 atom. Future open query syntax/parameters, backend SQL, executor, Arrow, optimizer, remote loading, and advanced equality are outside this proposed Phase-65 support domain. They are not claimed to exist now. The new open-parameter/partial-error owner refinements must be recorded as proposals adopted with this task, not earlier roadmap facts. A new Phase-65-owned defect cannot be reclassified into that ledger to obtain PASS.

### 3D. New decisions, derivations, and actual implementation freedom

This is a decision index, not a fourth asset-accounting ledger. The three asset ledgers above remain mutually exclusive.

| Subject | Status in this packet | Consequence/cost |
| --- | --- | --- |
| 16 delivery units | user's preference + this task's adopted concrete route | extra publication cost; no published N16 until this Slice succeeds |
| whole-semantic-success prerequisite | retained conservative v1 proposal, not a new public policy | no selected healthy branch planning amid an unrelated semantic ERROR |
| fixed-value literal transport only | retained explicit scope proposal | no arbitrary query rebind/template; general query params still not delivered |
| typed transport demands / closed eligible roles | v2 correction | fewer bind sites initially, but no false claim that same host value ensures SQL parity |
| field/demand/source inventories from first consumer | v2 architecture correction | implementation Slice cannot defer missing links until11/12/14 |
| later-owner mapping for open parameters/partial-error policy | proposed ownership refinement | not retroactively inserted into the Phase64 handoff |
| private names/file factoring/static thresholds | implementation freedom within these laws | all future symbols remain PLANNED; no product question for a spelling choice |

A rejected representation shortcut is not a new product feature. AST-based identity, provider semantics and stage rules remain those of current authority. Actual field/schema names for new private types are settled by their first producer and consumer, not guessed into existence by the static principal.

## 4. Full mandatory Gate: thirty answers

The following are decision answers, not a claim that the future implementation already exists. `UNKNOWN` provider evidence is an intentional typed state; an unanswered product/architecture choice is still blocking.

| # | Field | Phase-65 answer / exact boundary |
| ---: | --- | --- |
| 1 | Live authority | `d7af544…` baseline/CI above, Phase64 complete; WSL/remote/CI rebind in Slice1; no old candidate authority. |
| 2 | Product outcome | D65.01–.10; a real selected-result SQL-oriented plan with parameters/origins/demands, not emitted SQL. |
| 3 | Semantic model | Supplied finite BAG/SQL-NULL/stage semantics; preserve all Phase64 support restrictions and error/evaluation premises. |
| 4 | Identity | Upstream roots reused; plan scopes/blocks/ports/uses/binds are distinct nominal roles with exact correspondence; alias/name/byte equality is not authority. |
| 5 | Construction states | Concrete plan or typed blocked result; `.ok` prerequisite; exact selected root; no partial object passed off as complete. Target assessment separate. |
| 6 | Proof posture | Supplied assertion, derivation, IR verification, plan verification, document consistency, target evidence and actual runtime fulfillment remain separate. |
| 7 | Layer ownership | Semantic/IR meaning inherited; planning owns block/symbol/bind/origin/demand structure; target adapter owns demand matching; Phase66 owns SQL AST/text. |
| 8 | Dependency | Forward semantic -> IR -> plan; pure target adapters must not import emitters backwards; no semantic reconstruction from observation. |
| 9 | Compatibility | No new authored syntax/public command/JSON top-level shape; old SQL unchanged; separate additive private plan format; historical/live test scopes separated. |
| 10 | Requirements/capabilities | D65.07; exact demand != provider support != implementation != installation; missing/conflicting evidence never wins. |
| 11 | Interchange | In-memory private plan first; one private observation document later, not executable transport; no Arrow/Rust/API freeze. |
| 12 | Execution | None; resource execution and fulfillment remain Phase68. Binding literal values is construction, not running a statement. |
| 13 | Resource lifecycle | Compiler is invocation-local memory only; no DB/network handles/transactions. Test children use existing explicit acquisition and termination. Runtime resource API is N/A here: Phase68. |
| 14 | Security/trust | Trusted opened sources unchanged; no raw SQL/credential inputs; physical identifiers not value binds; malformed refs fail closed; observer not authority. |
| 15 | Algorithms | Deterministic selected-closure traversal, explicit graph edges, scope-local maps, syntax-role literal selection, supplied-witness checking. No rewrite search. |
| 16 | Complexity | Account V/E/F/X/P/M and output growth; retain DAGs; no eager all-path duplication; no unmeasured speed claims or hidden recursion/row execution. |
| 17 | Invalidation | Exact semantic/IR root change rebuilds plan and reverifies; target changes only reassess target-dependent products; policy/bind/source changes invalidate corresponding plan/origin claims. |
| 18 | Cache | No cross-run/persistent cache; only invocation-local indexes. Persistent identity/cache remains tentative Phase91. |
| 19 | Concurrency | Deterministic construction, no shared global mutable counters; no compiler task scheduler. Tests xdist-safe; workflow one writer. Runtime concurrency remains Phase68. |
| 20 | Diagnostics | Private typed blocking reasons and exact inherited diagnostics; no reclassification of PIE-S2337; deterministic locations/order. No public new code without its later explicit surface. |
| 21 | Inspection | Exact verified-plan runtime view from first feature; total closed portable view in14; no resolver/rebuilder, role-sensitive required/optional links. |
| 22 | UX | Private compilation API for explicit selected owner and policy/target; no new language/CLI; source-backed explanations; no accidental success claims. |
| 23 | Conformance | Inherited invariants + per-feature valid/corruption pairs + explicit target evidence; PG18/MySQL8.4 are reviewed references, not automatic target-version promises. |
| 24 | Differential/fuzz | Existing real-source probe infrastructure, whole records/bytes/rejections, real Python/seeds/relocation/wheel; bounded mutations, not new fuzz platform. |
| 25 | Packaging | stdlib and existing dependencies, 0.1.0 unchanged; private modules; no SQLAlchemy/Calcite/SQLGlot runtime dependency; generated/golden reproducibility preserved. |
| 26 | Support matrix | Python3.12/3.13; EXPLICIT_MODULES only; exact inherited types/operations; Float data transport != Float equality; target analysis only for explicit evidence. |
| 27 | Release/deprecation/EOL | Ordinary per-Slice publication only; no tag/release/version/EOL change. Private additive format is not public compatibility freeze (69/82/83). |
| 28 | Readiness | Three ledgers, H01–H08 input mapping and every66–97 atom below. No future-only framework without a current caller. Proposed later-owner refinements are labelled new proposals, not old roadmap facts. |
| 29 | Route | Sixteen deliveries; explicit 14/15 alternatives below; no production in1/16; independent verification grows with each implementation. |
| 30 | Repair/STOP | Cause-level bounded corrections with exact paths and complete finding-set review; no per-line approval treadmill; material semantic/trust/root drift remains STOP. |

### Twelve question groups and eight cross-cutting checks

| Group | Actual answer |
| --- | --- |
| A product/scope | One private selected TABLE/QUERY plan, concrete or typed blocked; SQL, execution, public syntax and arbitrary rebind are excluded. |
| B current state/history | The exact d7af544 baseline completed Phase64. Its Q65 questions and N16 preference were unresolved history; this task adopts and verifies D65/N16 anew. |
| C whole-roadmap pull-forward | Every66–97 atom is classified in §6; plan ports/origins/demands have current consumers, while buffers, resources, optimizer search and remote loading remain later. |
| D decisions/freedom | D65.01–.12 settle selection, structures, eligibility, sources, target evidence, obligations and delivery. Future private names/factoring and portable numeric limits are implementation freedom within those laws. |
| E semantics/identity | Finite BAG/SQL NULL and actual stage/field/proof roots are inherited; use and declaration identities remain distinct, contextual expressions cannot be merged by value or name. |
| F layers/composition | Semantic facts -> VERIFIED IR -> plan block/port/use/demand structure -> explicit target assessment -> Phase66 SQL AST. Planning and inspection never call semantic inference to fill a gap. |
| G algorithms/cost | Deterministic selected-DAG traversal and invocation-local maps, output-size V/E/F/X/P/M accounting; no shared-DAG expansion, all-path cache or unmeasured speed claim. |
| H state/resources/trust | Whole-project semantic success precedes selected closure. No DB/network handles are acquired; fixed immutable data and document-local refs do not authenticate runtime roots. |
| I UX/diagnostics/inspection | Retain original diagnostics; selected demands are a separate collection. Full private observation may expose authored values. All origin queries preserve roles and parser coordinates. |
| J compatibility/ecosystem/release | EXPLICIT_MODULES, Python3.12/3.13, package0.1.0 and old public SQL/CLI/JSON stay fixed; additive private portable format in14, no release/tag or dependency adoption. |
| K external evidence/assurance | Eleven primary records inform boundaries; exact blobs and current page reads are distinguished from inherited review. C01–C43 are finite acceptance obligations, not future implementation proof. |
| L route/exits/change control | Sixteen real deliveries with immediate local verifier/view/origins/demands, portable acquisition in14, full conformance15, audit-only16; P01–P10 and bounded causal STOP policy govern closure. |

| Cross-cutting check | Actual rule / owner |
| --- | --- |
| X1 observable equivalence/algebra | D65.02/.04/.05, C03–C21: values/BAG/NULL/order/type/errors/evaluation promises, not schema-only parity |
| X2 minimal counterexample/composition | section7 and R65 reference cases; real compound producers in every adapter |
| X3 uncertainty and obligations | D65.01/.07/.08: missing evidence, incomplete inventory and pending runtime requirements are distinct |
| X4 errors/evaluation/effects | no constant folding/pushdown/CSE; retain unknown without inventing evaluation count |
| X5 safety/liveness/atomicity | typed whole-result failure, finite DAG, iterative/bounded pure checks; no truncated accepted graph |
| X6 evolution/reversibility | private versioned observations, no current-registry-to-historical-epoch assertions; source/runtime unchanged on rejection |
| X7 evidence strength/independence | verifier does not call builder; pure consistency is not authenticity; examples are finite reference evidence |
| X8 total cost | output-sized provenance, no all-path expansion; merge validation invocations where exact evidence permits; no measured speed claim |

## 5. Live source audit: observed facts and consequences

F01–F19 are the packet finding identifiers, reconciled here against local source at `d7af544dd4ce48891d5fe2596ab23e494f48d4ab`. This is source inspection, not execution of a Phase65 planner. The exact source/consumer/test trace below records this session's audit; prior planning-assistant review is separate evidence.

| ID | Exact source seam | Observed fact | Design consequence |
| --- | --- | --- | --- |
| F01 | `docs/architecture/phase-initiation-gate-v1.md` | 30 fields plus11-field external record; UNKNOWN decisions block | A five-question sketch is insufficient. |
| F02 | `docs/spec/phase64-completion-audit-phase65-handoff-v1.md` H01–H08 | exact completed/IR/verification/inspection prerequisites; no Phase65 shape frozen | Consume actual objects; don't reopen Phase64 or infer readiness from final names. |
| F03 | `project_completed_semantics.py::ProjectConcreteCompletedSemanticResult.__post_init__` | ok requires all effective entries concrete and no ERROR | Selected healthy owner does not change global check semantics by itself; D65.01 is explicit. |
| F04 | `ast_nodes.py::Parameter`, `grammar/Pietto.g4::parameterList`, Phase52 parameter inventory | callable declaration parameters, not runtime query placeholders | D65.05 supplies real limited typed transport; callable parameters cannot be repurposed, and no new value/type is inferred downstream. |
| F05 | `ast_nodes.py::Span` | 1-based half-open coordinate range | Do not silently adopt SQL byte offsets or ECMA426 units. |
| F06 | `semantic/source_connectors.py::check_source_connectors` | exact postgres.table/mysql.table signatures, no DB introspection | Keep static physical-source identity; no inferred connections/federation. |
| F07 | `sql/window_strategy.py::NamedWindowLoweringStrategy` and target evidence | explicit native-preserve/reorder/exact-inline/not-lowerable decisions already exist | Reuse actual demand/evidence patterns, no simplistic dialect boolean or backwards emitter dependency. |
| F08 | `project_ir_properties.py` row/stage fields and exact checkpoint roots | field roles and source membership are separate from plan occurrences | Preserve role-sensitive field maps and stages; don't use alias strings. |
| F09 | Phase64 completion contract + current IR/inspection owners | current formats, source/active-input/ORDER/Decimal obligations with actual corruption witnesses | Runtime and document evidence must be connected from first consumer. |
| F10 | Phase52 guard + `_pietto_repository_facts.py` as recorded by Slice10 CCG01 | actual dependency protection, no generic capability-name ban | Audit new true target consumer's direct guard in its implementing Slice; no silent allowlist expansion. |
| F11 | Interlude-II acquisition/readers, HR01/HR02 | historical six-family epoch differs from current seven-family registry | Never test an immutable epoch against a growing current registry. |
| F12 | `AGENTS.md`/development + sole lifecycle/inventory owners | small changes, no duplicate readers; independent actual CI publication | S1 exact A2/M4 document/static closure; no new governance runtime. |

Additional v2 findings, checked against this session's local bytes at the same commit:

| ID | Exact seam | Source fact | Consequence |
| --- | --- | --- | --- |
| F13 | `semantic/capability_facts.py::CapabilityFact/CapabilityKey` | fact is descriptive; domain/operation/operands/context and provenance define its proposition; key has no release member | no promotion from catalog membership/legacy lowering to whole new plan/release support |
| F14 | `semantic/capability_lookup.py::lookup_capability`, Found/Absent/Unknown/Conflict | Found retains support fact; Absent and Unknown have different completeness meanings; conflicts retain multiple facts | preserve each case and do not create a universal 'supported' flag |
| F15 | `ast_builder.py::visitLiteral/_parameters/_decode_numeric_literal` | typed AST variants distinguish Bool/Int/Float; callable params separate; only parsed numeric literals are finite-checked | no whole source Float finiteness proof; exact literal transport only |
| F16 | `ast_builder.py::_end_position` | line breaks and Python text length determine end coordinate | retain parser positions; decoded strings/UTF byte offsets are not source coordinates |
| F17 | `row_expression_type_facts.py::build_project_row_expression_value_types` | helper calls inference, not merely a read-only map adapter | planner may read existing semantic maps, not call this helper to repair missing evidence |
| F18 | `project_scalar_namespaces.py::ProjectJoinedLetOccurrence/ProjectJoinedScalarNamespace`, `sql/relations.py::render_relation_sql/_render_input` | LET binding retains exact namespace/source; old SQL rendering is already dialect-specific | contextual plan sites; preserve root/stage values; don't import old emitter as neutral plan builder |
| F19 | `project_scalar_namespaces.py::ProjectConcreteJoinedNamespaceExpression` | retains an expression root, exact namespace/resolutions and a `value_types: Mapping[Expression, ValueType]` | a stored literal-level type evidence seam exists for admitted joined scalar contexts; do not claim every other producer already exposes an equivalent map |

The first-party PostgreSQL PREPARE and MySQL8.4 PREPARE sections also show context-sensitive parameter typing. These are external constraints for D65.05, not Pietto implementation facts.

Sources: see section11's repository links. A finding that a mandatory current fact is absent cannot be patched during Slice1 or mislabeled a future-owner issue.


### Current source reconciliation and decision trace

F06 is narrower than a generic Text-signature summary: PostgreSQL semantic admission can
accept a Text expression; MySQL additionally requires a nonempty string LiteralExpr.
The old PostgreSQL renderer consumes a static nonempty locator and quotes it as one
identifier; Phase65 must retain exact spelling, not add split-on-dot semantics.
F19 is a real retained map, not a promise that every semantic carrier has one.
`ProjectNoJoinScalarExpression.value_types` and `ProjectJoinCondition.value_types` also
exist in their exact contexts; `build_project_row_expression_value_types` calls inference
and is prohibited as a planning repair. Callable parameters remain declaration-only.
The exact ORDER proof carrier is `ProjectDistinct.order_proofs`, reached through
`ProjectCompletedEffectiveOutput.row_domain.distinct`; there is no direct
`ProjectCompletedEffectiveOutput.order_proofs` member. This corrects the handoff's
shorthand pointer, not its existing semantic guarantee.

Construction checks actual `.ok` plus VERIFIED bundle/root/selected membership.
`ProjectIRQueryBlockSnapshot.find_owner` uses `is` and returns all matches;
`_verify_root_continuity` binds the Phase61 plan, Phase62 verification/join stage,
effective overlay and allocation. Typed terminals remain valid IR observations.
Final canonical fields, stage-local anchors and active outputs have distinct roles.
`_expected_operator_specs` orders WHERE/GROUP/satisfying/windows/QUALIFY/projection/
DISTINCT/ORDER/LIMIT from actual carriers; LET is namespace/stage-value authority,
not necessarily a separate IR node. GLOBAL plus windows/ORDER and aggregate risk
retain their existing negative domain. Do not infer an operation from a keyword.

Each following witness is an existing upstream behavior test, **not a Phase65
implementation test**. C identifiers are future acceptance duties. Source/consumer
pointers are exact current definitions; future private seams in the route are PLANNED.
The table names actual retained-data consumers: completed result -> IR builder,
snapshot -> verifier, LET occurrence -> LET value, typed namespace expression ->
completed selected field, source AST -> connector checker, capability key -> lookup,
assessment -> IR retention, Span -> authored observation, verification -> analysis,
set output -> set verification, inspection -> serialization. Invalidation is a
separate change-domain interface, not a consumer of a verification return value;
JOIN condition and joined namespace analyses are sibling type-map producers.
Static pointer existence checks do not independently prove these dataflow claims
or any future planner behavior; the actual bodies were read in this source audit.

| Decision | Classification | Current producer | Current consumer | Existing witness | Future counterexamples | First/completing Slice | Cost and rule |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D65.01 | USER_DECISION_REQUIRED | `src/pietto/_project/project_completed_semantics.py::ProjectConcreteCompletedSemanticResult` | `src/pietto/_project/project_query_block_ir.py::build_project_query_block_ir` | `tests/test_phase63_slice13_completed_project_semantic_result_public_check_boundaries.py::test_concrete_result_closes_exact_existing_chain_and_all_positive_families` | C01 C02 C33 | 2 | Whole-project ERROR blocks even a healthy selection; project diagnostics stay complete. |
| D65.02 | ARCHITECTURE_DECISION | `src/pietto/_project/project_query_block_ir.py::ProjectIRQueryBlockSnapshot` | `src/pietto/_project/project_query_block_ir_verification.py::verify_project_query_block_ir` | `tests/test_phase64_slice10_ir_corruption_and_invalidation.py::test_set_operand_occurrences_cannot_be_dropped_duplicated_or_grafted` | C08 C09 C10 C38 C41 | 2–9 | Material SELECT/SET/use/port structure costs explicit boundaries; no opaque IR wrapper. |
| D65.03 | ARCHITECTURE_DECISION | `src/pietto/_project/project_scalar_namespaces.py::ProjectJoinedLetOccurrence` | `src/pietto/_project/project_scalar_namespaces.py::ProjectJoinedLetValue` | `tests/test_phase63_slice5_let_stage_namespace_lattice_shadowing_alias_laws.py::test_namespace_chain_retains_exact_root_occurrences_and_prefixes` | C14 C17 C29 C30 | 3–4 | Context-qualified sites and stage-value reuse; names never substitute for exact membership. |
| D65.04 | USER_DECISION_REQUIRED | `src/pietto/_project/project_final_outputs.py::ProjectDistinct` | `src/pietto/_project/project_query_block_ir_verification.py::_verify_semantic_evidence` | `tests/test_phase64_slice8_row_equivalence_distinct_quotient_grain_origin.py::test_order_counterexample_and_nullable_key_do_not_choose_winner` | C03 C04 C11 C15 C16 C19 C34 C39 | 5–9 | Hidden ORDER is an explicit realization demand; no extra quotient column or representative. |
| D65.05 | USER_DECISION_REQUIRED | `src/pietto/_project/project_scalar_namespaces.py::ProjectConcreteJoinedNamespaceExpression` | `src/pietto/_project/project_final_outputs.py::ProjectCompletedOutputField` | `tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py::test_runtime_sql_parameter_substitution_is_explicitly_out_of_scope` | C05 C06 C07 C27 C28 C40 | 10 | Closed Bool/Int/Text/finite Float literal roles; fixed original values, exact tags; function/structural/unknown sites preserved. |
| D65.06 | USER_DECISION_REQUIRED | `src/pietto/ast_nodes.py::SourceDef` | `src/pietto/semantic/source_connectors.py::check_source_connectors` | `tests/test_phase64_slice10_ir_observation_and_differential.py::test_capability_locator_and_canonical_final_roles_are_bound` | C20 | 2–3 | Static validated locator only; keep connector spelling and reject insufficient evidence without evaluation. |
| D65.07 | ARCHITECTURE_DECISION | `src/pietto/semantic/capability_facts.py::CapabilityKey` | `src/pietto/semantic/capability_lookup.py::lookup_capability` | `tests/test_phase52_fail_closed_capability_lookup.py::test_incomplete_domains_preserve_actual_found_and_conflict_evidence` | C18 C31 C32 | 2–13 | Every demand retained from first operator; exact proposition and separate release applicability; no all-of-empty certificate. |
| D65.08 | USER_DECISION_REQUIRED | `src/pietto/_project/project_single_match.py::ProjectSingleMatchAssessment` | `src/pietto/_project/project_query_block_ir.py::ProjectIRSingleMatchRetention` | `tests/test_phase64_slice7_single_match_direction_unit_scoped_proof_obligation_warning_diagnostics.py::test_hop_and_whole_path_keep_their_exact_units_and_complete_authority` | C12 C21 | 5,11 | Keep full scoped proof/Diagnostic and right membership; WARNING is not fulfillment. |
| D65.09 | ARCHITECTURE_DECISION | `src/pietto/ast_nodes.py::Span` | `src/pietto/_project/project_query_block_ir_inspection.py::_authored_data` | `tests/test_phase64_slice10_ir_observation_and_differential.py::test_convergence_rereview_order_source_uses_its_actual_module` | C22 C35 C36 C37 | 2–12 | Value/membership/type/generated roles; parser character coordinates; full private view is source-bearing. |
| D65.10 | ARCHITECTURE_DECISION | `src/pietto/_project/project_query_block_ir_verification.py::verify_project_query_block_ir` | `src/pietto/_project/project_query_block_ir_verification.py::build_project_query_block_ir_analysis_bundle` | `tests/test_phase64_slice10_ir_corruption_and_invalidation.py::test_semantic_evidence_changes_require_rebuild_and_fresh_verification` | C23 C24 C25 C26 C43 | 2–14 | Independent checks, total private document rejection, no executable import or identity-by-bytes. |
| D65.11 | ARCHITECTURE_DECISION | `src/pietto/_project/project_query_block_ir.py::ProjectIRCompletedSetOperationOutput` | `src/pietto/_project/project_query_block_ir_verification.py::_verify_set_operations` | `tests/test_phase64_slice10_ir_corruption_and_invalidation.py::test_all_except_membership_and_repeated_uses_reach_the_consumer` | C09 C36 | 3,14 | Retain definitions and all uses, account materialized output and upstream analysis separately. |
| D65.12 | USER_DECISION_REQUIRED | `src/pietto/_project/project_query_block_ir_inspection.py::ProjectIRQueryBlockInspection` | `src/pietto/_project/project_query_block_ir_inspection.py::serialize_project_query_block_ir_inspection` | `tests/test_phase64_slice10_ir_observation_and_differential.py::test_phase64_standalone_probe_matches_its_single_renderer` | C42 | 14–16 | N16 costs two publication cycles over14; minimum process/acquisition/readers in14, broadening15, no production16. |

### H01–H08 actual input handoff

These are existing inputs checked at the baseline, not new planning carriers.
Their tests are the fixed Phase64 H01–H08/E01–E12 map plus the decision trace above.

| Input | Actual retained source and root condition | New consumer duty / first Slice | Blocker or loss witness |
| --- | --- | --- | --- |
| H01 | Snapshot.completed/base_plan/join_stage/owners/dependencies/schedule and each entry.active_output/active_properties; exact verified analysis bundle | 2 selected result, 3 named uses: preserve exact active endpoints and canonical owner order | C01/C02/C23/C24; no last-output or missing external producer |
| H02 | ProjectIRComposedJoin.source/condition/inputs retain current binary or historical path boundary and pre-match roles | 5 matching blocks: accumulated-left/right and actual M1–M5 condition scope | C11/C12; no WHERE/ON movement or post-null field substitution |
| H03 | ProjectIRCompletedSetOperationOutput.operands, ProjectIRSetOperandInput, ProjectSetOperation.uses and canonical set output fields | 9 SET-body positional ports, ordered repeated uses and full membership graph | C08/C09/C10/C36; preserve right EXCEPT membership and nesting |
| H04 | Original AST Span and exact logical module/declaration/use; package identity where present remains distinct | 2 local authored/generated origins; 12 complete bidirectional queries | C22/C35; unavailable legacy location stays unavailable; no guessed SQL offsets |
| H05 | ProjectIRRowField versus ProjectIRStageRowField/checkpoint and joined/final fields; exact NULL/key/FD/grain witnesses | 2 ports, 5 outer/subset fields, 6 aggregation, 8 quotient; no new property solver | C12/C19/C24/C39; UNKNOWN is not GLOBAL and grain is not total cardinality |
| H06 | ProjectDistinct.equivalence and set column capabilities retain exact type identity, validated Decimal(p,s), TypeExpr sources and parents | 8/9 equality demands, 10 exact fixed transport | C19/C27/C40; Float equality remains deferred despite finite literal transport |
| H07 | ProjectRelationOrdering.items and ProjectDistinct.order_proofs via output.row_domain.distinct; supplied visible/STRICT FD property/index/witness | 8 scoped hidden ORDER realization demand, separate from window order and visible ports | C15/C16/C30/C34; do not re-solve FD or choose a representative |
| H08 | ProjectSingleMatchAssessment and ProjectIRSingleMatchRetention retain exact request/scope/unit/boundaries/input_pairs/proofs/original Diagnostic | 5 capture, 11 report, 13 assess; Phase68 fulfills | C21/C31/C33; LEGAL_UNPROVED warning survives LIMIT/DISTINCT/SEMI/ANTI |

## 6. Whole-roadmap readiness: every Phase66–97

Classifications: **CORE_NOW** is Phase65's planned implementation responsibility (not cross-phase pull-forward); **MINIMUM_NOW** has a concrete consumer in this phase route; **CONTRACT_ONLY_NOW** retains an exact boundary with a later consumer; **DEFER_BY_NECESSITY** lacks its owning layer/runtime; **NO_CURRENT_USE** creates no placeholder code. Multiple concerns under one Phase are separate atoms.

| Phase / owner | Atom and classification | Planned Phase65 contribution / witness (not implemented in Slice1) | Work staying with later owner |
| --- | --- | --- | --- |
| 66 SQL/emit | plan/block/port/bind/source/requirement handoff: CORE_NOW | P65 plan + layout + source relations; stage-order and repeated-use witnesses | dialect SQL AST/text, actual placeholder tokens/order/SQL ranges, per-target emulations and public emit |
| 67 result/Arrow | result-shape projection: MINIMUM_NOW; buffers: DEFER_BY_NECESSITY | selected output identity/order/type/nullability and explicit presentation-order posture | PiettoResultContract API, Arrow types/batches/ownership |
| 68 executor | fulfillment and fixed bind demands: CONTRACT_ONLY_NOW; resources: DEFER_BY_NECESSITY | pending cardinality requirement + immutable value payload + no execution claim | connection/statement/session/transaction/stream/cancel/backpressure/assertion implementation |
| 69 alpha/entrypoints | status/privacy policy: CONTRACT_ONLY_NOW | check/plan/target/lowerer/fulfillment matrix and source-backed errors | public plan/bind options, integrated commands/distribution |
| 70 open plans | generated scope/use seams: MINIMUM_NOW; authored features: DEFER_BY_NECESSITY | closed graph preserves scope boundaries; no accidental capture | authored subqueries/CTEs/LATERAL/correlation/table functions, open/rebindable query parameters, general effect authority |
| 71 nested | flat result/grain provenance: CONTRACT_ONLY_NOW; nested: DEFER_BY_NECESSITY | explicit flat ports, no field/row identity from labels | Collect/Unnest/outer-inner grain/nested transport |
| 72 types/equality | exact requirement projection: CORE_NOW; advanced domain: DEFER_BY_NECESSITY | Float transport vs equality counterexample; Decimal exact source and NULL/collation requirements | NaN/equality widening/collation/temporal-ASOF rules |
| 73 aggregate algebra | existing proof preservation: MINIMUM_NOW; new algebra: DEFER_BY_NECESSITY | group/global and strict-FD evidence through block boundaries | state/merge/reaggregation/grouping extensions |
| 74 assets/SPI | dependency and callable identity: CONTRACT_ONLY_NOW; plugins: NO_CURRENT_USE | references retain exact asset/function/provider identity | reusable derived relationships and plugin registration/execution |
| 75 language tools | source-map query and logical source units: CORE_NOW; editor: DEFER_BY_NECESSITY | Unicode/import/generated-origin localization | LSP position conversions, formatting/editions/migration UI |
| 76 PostgreSQL depth | evidence-backed requirement seam: MINIMUM_NOW; deep lowering: DEFER_BY_NECESSITY | explicit profile/result without broad parity claim | target-specific optimization/extensions/catalog coverage |
| 77 MySQL depth | same explicit seam: MINIMUM_NOW | collation/identifier/source/native-feature negative cases | deeper MySQL lowerings/releases/session semantics |
| 78 SQLite depth | common plan/requirements: CONTRACT_ONLY_NOW | no dialect-name-as-support shortcut | actual SQLite backend, capability facts, tests |
| 79 DuckDB depth | common plan/requirements: CONTRACT_ONLY_NOW | no accidental BY NAME/ASOF semantics | actual DuckDB backend and deep features |
| 80 data science | exact result ports: CONTRACT_ONLY_NOW | BAG/order/null result boundary not DataFrame defaults | adapters and value materialization |
| 81 assurance | bounded independent witnesses/corpus: MINIMUM_NOW; platform: DEFER_BY_NECESSITY | loss/mutation/role/ref corpus, reference counterexamples | real-DB/fuzz/benchmark farms and performance commitments |
| 82 freeze | version/visibility ledger: CONTRACT_ONLY_NOW | private result/format stated explicitly | public syntax/API/schema/support matrix freeze |
| 83 release | evidence/migration handoff: CONTRACT_ONLY_NOW | exact delivered exits and limitations | stable1.0 publication/audit |
| 84 remote/trust | trust-preserving locators: CONTRACT_ONLY_NOW; transport: NO_CURRENT_USE | no ambient registry lookup/credentials | remote loading/signing/authentication/trust policy |
| 85 solver/lock | existing dependency identity: CONTRACT_ONLY_NOW; solving: NO_CURRENT_USE | no new nearest-version or cache identity | solver/canonical lock/resolution |
| 86 devices/domain | preserve opaque typed requirement: CONTRACT_ONLY_NOW | no device or RDKit objects in compiler | scientific/device adapters and transport |
| 87 catalog/statistics | exact evidence scope: MINIMUM_NOW; runtime data facts: DEFER_BY_NECESSITY | static proof vs observed constraint distinction | introspection/statistics/chase/data-quality evidence |
| 88 logical optimizer | rewrite premises and stable ports: CONTRACT_ONLY_NOW | no LIMIT/filter move, no set reassociation, no effect assumptions | memo/cost/join search and equivalence transformations |
| 89 physical strategies | logical demand vs realization: CONTRACT_ONLY_NOW | materialization/evaluation policy not guessed by block builder | physical strategy and dataflow choices |
| 90 Rust | small pure checker/corpus: CONTRACT_ONLY_NOW; port: NO_CURRENT_USE | total boundary and parity tests with current Python consumer | profiling-driven PyO3/maturin kernels/wheels |
| 91 tentative cache | explicit invalidation inputs: CONTRACT_ONLY_NOW | no same-bytes proof reuse | persistent/incremental identity and cache |
| 92 tentative recursion | explicit acyclicity and closure: CONTRACT_ONLY_NOW | cycles are typed invalid, not implicit fixed points | recursion/fixpoint/evaluation/provenance |
| 93 tentative proof | local preservation laws/witnesses: CONTRACT_ONLY_NOW | named assumptions, not proof-by-roundtrip | formal certification/tooling |
| 94 tentative federation | source-domain requirement: CONTRACT_ONLY_NOW | mixed connector evidence cannot imply executable federation | distributed query/data movement/network plans |
| 95 tentative DML/DDL | read-only product boundary: NO_CURRENT_USE | explicit rejection/no statements of side effects | writes/DDL/migrations |
| 96 tentative governance | no policy-by-name inference: NO_CURRENT_USE | preserve ordinary source/target identity only | access/security policy semantics |
| 97 tentative continuous | finite-plan boundary: NO_CURRENT_USE | finite BAG planning not continuous query | streaming-time/window/state semantics |

No row means 'implement the future feature now'. The target-neutral plan/source-map/fixed-literal transport work is Phase65 core, not artificially counted as cross-phase acceleration. Data execution and full backend coverage remain absent, not silently promised.

## 7. Semantic witnesses and counterexamples

These constrain planning and its representation contracts, not new source-language semantics. The original six elementary examples are retained in the v2 optional `check_counterexamples.py`, together with targeted new checks; its JSON is **not Pietto validation**. Remaining cases are design/implementation acceptance requirements to become real source-driven tests in their owner Slice.

| ID | Counterexample / law | Required outcome |
| --- | --- | --- |
| C01 | Healthy selected owner, independent project error | no positive plan under D65.01; retain diagnostics, don't crop them away |
| C02 | VERIFIED graph with selected typed terminal | no concrete selected plan from the verification flag alone |
| C03 | `[1,2]`, LIMIT1 then filter>1 vs filter>1 then LIMIT1 | `[]` vs `[2]`: preserve barrier, no pushdown |
| C04 | `(x=1, hidden_row_number=1/2)` then visible DISTINCT | one x row, not two; hidden window field not comparison key |
| C05 | `WHERE ... literal1` versus right producer's static LIMIT1 | data literal may be fixed-bind transport; structural LIMIT must remain fixed |
| C06 | changing right LIMIT1 to runtime2 after max-one proof | proof invalid; no arbitrary post-verification rebind |
| C07 | two literal1 occurrences; True versus Int1 | no value-based merge or host-type guess |
| C08 | same producer used twice under different roles/aliases | same definition, two uses and scoped references |
| C09 | repeated UNION ALL DAG depth12 | 13 producer nodes/24 use edges; don't inline4096 leaf copies or dedup uses |
| C10 | `(A EXCEPT B) EXCEPT C` vs `A EXCEPT (B EXCEPT C)` with all={1} | empty vs {1}; retain authored left fold/nesting |
| C11 | LEFT ON matching+refinement versus post-WHERE | unmatched rows differ; condition scope must not move |
| C12 | SEMI/ANTI two matching right occurrences | left0/1 result is not single-match proof; retain right dependency |
| C13 | generated CTE used twice around unknown/effectful computation | preserve requirements, don't assume materialize-once or safe duplication |
| C14 | GROUP/window result across a generated block boundary | reference output port in new scope, not old source qualifier/name |
| C15 | ORDER on hidden field justified by exact strict-FD evidence | retain proof and requirement; no arbitrary representative/min/max |
| C16 | inner ORDER/LIMIT used in later JOIN | preserve selected rows; don't invent outer presentation order |
| C17 | aliases colliding after case-fold/truncation | neutral symbols remain distinct; final target spelling must remain injective or reject |
| C18 | target omitted, provider UNKNOWN or CONFLICT | no supported/executable certificate or fallback |
| C19 | Text/NULL/Decimal exact semantic capability vs target defaults | require exact target parity; no automatic collation/coercion assumption |
| C20 | source connectors for different backend families | keep descriptors and negative/unresolved target demand; no implicit federation |
| C21 | unproved cardinality requirement plus later LIMIT1 | pending obligation remains; check WARNING unchanged |
| C22 | Unicode/imported alias/multiple generated uses | exact authored origin/coordinate unit; no guessed SQL offsets/foreign module |
| C23 | external input producer omitted; internal predecessor missing | required role endpoint rejected; absence cannot identify a role |
| C24 | equal-looking foreign IR/plan/source/type/proof roots | refuse graft; same canonical bytes never restore runtime authority |
| C25 | serialized docs altered coherently but no original root | pure consistency is not authenticity/executability; runtime uses exact roots |
| C26 | change target only / change IR / change literal policy | target reassessment only / rebuild+verify / rebuild binding+source associations as appropriate |


### v2 supplemental review obligations (not merely additional test counts)

| ID | Specific omission/contradiction | Required corrected behavior |
| --- | --- | --- |
| C27 | same value placeholder gets different inferred SQL type/overload | retain exact type/context demand; no backend readiness without realization evidence |
| C28 | a call argument is data-looking but shape-sensitive | all such subtrees preserved unless a precise supported argument-role rule exists |
| C29 | one AST/body occurs in two use environments | context-qualified sites/slot maps, not AST pointer/name/value alone |
| C30 | grouped value used in SELECT/ORDER is re-expanded with new binds | refer to the existing grouped output; no accidental structural mismatch |
| C31 | all requirements deleted, empty all() yields success | verify demand-site completeness against source/IR and complete plan shape |
| C32 | legacy type-membership/inline-window support used for whole plan | retain proposition scope; unmapped demands unresolved, not supported |
| C33 | healthy selected owner with unrelated unproved warning | all project diagnostics preserved; only reachable obligations become selected-plan demands |
| C34 | hidden strict-FD ORDER key referenced after quotient | explicit determination/realization demand, no dangling field or extra DISTINCT key |
| C35 | same decoded string, escaped spelling or non-BMP source differs | exact source occurrence/parser coordinates, not decoded-value position |
| C36 | right EXCEPT or ANTI source excluded from value-only map | retain membership/predicate origin and dependency separately |
| C37 | private report assumed redacted because fixed payload is not 'runtime value' | full private observation explicitly source-bearing; no public-safety promise |
| C38 | a new operator is reached before its builder/demand/verifier support exists | typed planner terminal; never omit/identity-pass-through it |
| C39 | GLOBAL aggregate on empty input / grouped empty input | exact stage row-count/null rules; no false disappearance of aggregate row |
| C40 | same primitive value object with wrong tag or signed zero | reject wrong typed envelope without value-based de-duplication |
| C41 | Phase65 handoff acceptance becomes post-IR blank labels | material block/port/clause/demand relation must be readable by actual verifier/view |
| C42 | process family added only in final assurance | minimum registration/standalone/render/origin/static-reader closure with Slice14 first portable consumer |
| C43 | raw JSON duplicate keys disappear during ordinary decoding | reject before mapping conversion; distinguish duplicate declarations from legitimate repeated use references |

These do not add SQL execution to Phase65. The accompanying script has labelled SQLite/reference-policy checks; no result is called Pietto or PostgreSQL/MySQL validation. Design invariants involving current roots remain mandatory source-driven implementation tests in their owning Slices.

## 8. Selected sixteen-Slice route

N=16 is selected by this task and locked only by successful Slice1 publication;
later rows are not implementation authorization. Each implementing delivery owns
its focused behavior tests and extends the builder, independent verifier, runtime
view and mandatory local origins/demands together. Any unsupported reached stage
is a typed terminal, never omitted or passed through. All new private module/API
names remain PLANNED; use the nearest real private owner, not one module per row.

| Slice | Exact input | Output / principal and owner seam | Real first consumer | Required verification | Non-goals |
| --- | --- | --- | --- | --- | --- |
| 1 | published Phase64 + v2 decisions | this document and static principal; Fresh phase gate, source/external audit, decisions, three ledgers, route lock; owner: this contract/static principal and sole lifecycle/inventory readers | immutable contract + static principal verifies complete coverage | static coverage, source/test references, historical Git and live separation | production/grammar/API changes |
| 2 | 1; exact completed.ok + VERIFIED bundle + selected owner | scan/source descriptor, SELECT export correspondence, minimal view; First selected-result scan/projection ProjectSQLPlan; owner: private plan entry/result/core builder, minimal independent verifier and runtime view | exact checked/VERIFIED root, minimal physical source, scoped exports and local origins/demands -> complete plan or blocker; independent verifier/runtime view | C01/C02/C23/C24/C31/C38/C41; wrong root, omission, terminal and unsupported reached stage; C26 selected/source/IR root change requires rebuild and fresh verification | broad operators, partial-project policy |
| 3 | 2; exact dependencies/uses/active ports/logical modules | shared definitions and scoped repeated/imported input uses; Named producer graph, physical sources, use-scoped symbols; owner: plan source/input-use/scopes owner; reuse existing completion/dependency authority | repeated/shared/imported producer consumed twice with distinct input ports; block-scope lookup | C08/C09/C17/C20; no winner, foreign producer, cycle and repeated-use loss | federation, recursive inline expansion |
| 4 | 3; actual row/LET/WHERE namespace and type maps | contextual expressions and explicit preceding-stage ports; Row scalar/LET/WHERE stage-value plan; owner: plan scalar/stage-block adapter; consume existing row/LET/filter typed facts | existing typed expression refs and exact stage barriers consumed by simple filtered result | C03/C14/C29/C30; unknown evidence, swapped stage, forbidden backward alias | evaluator, arbitrary CSE/pushdown |
| 5 | 4; current seven-kind JOIN/condition/input/obligation roots | matching clauses, all input images and local demands; Existing seven JOIN kinds and matching scopes in SQL-oriented structure; owner: plan binary matching/port adapter; consume current JOIN and composed-input authority | actual left/right/prefix ports, predicate-local right for SEMI/ANTI, applicable obligation capture; role/omission mutations | C11/C12/C21/C36; outer side, SEMI/ANTI right scope, missing obligation or condition | new JOIN semantics, native backend emulations |
| 6 | 5; GROUPED/GLOBAL/satisfying and aggregate-risk facts | aggregate boundary and exact selected stage exports; GROUPED/GLOBAL/satisfying query-block boundaries; owner: plan aggregate-block adapter; consume existing group/global/satisfying facts | aggregate input/group result/HAVING-equivalent stage ports consumed by outer result | C14/C19/C30/C39; empty/global/grouped, COUNT difference, missing risk/FD premise | reaggregation or new aggregate algebra |
| 7 | 6; named/selected/hidden window and QUALIFY authority | pre/post-window scopes and exact filtered output; Window, named-window and QUALIFY staging; owner: plan window/QUALIFY block adapter; consume existing named/hidden window authority | hidden/selected windows and post-window filters scoped correctly before outer projection | C04/C13/C14; hidden computation loss, alias capture, no physical-evaluation claim | backend native-window choice, new window semantics |
| 8 | 7; visible DISTINCT/equality/ORDER proof/static LIMIT | quotient, scoped hidden determination and order/limit boundaries; DISTINCT, relation ORDER and LIMIT result boundary; owner: plan final-row/DISTINCT/order/limit adapter; consume existing quotient/ORDER evidence | visible quotient ports; hidden strict-FD key remains explicit realization demand, not ordinary quotient column; static limits | C04/C05/C06/C15/C16/C34; wrong visible key, proof deletion, representative, zero/one | winner selection, implicit sort/tie policy |
| 9 | 8; named set bodies/all operands/canonical field images | SET query-expression definition and positional ports; Set-body query expressions and positional ports; owner: plan non-SELECT/set-body adapter and positional output port verification | all six forms + nesting/repeated operands -> reusable non-SELECT plan output | C08/C09/C10/C19/C36; all six laws, nesting, repeated operand, membership deletion | name alignment, set flattening, backend rewrites |
| 10 | 9; exact literal-level facts and contextual site inventory | policy, dispositions, typed fixed envelope and bind uses; Safe literal bind transport and logical parameter/use layout; owner: plan literal-bind policy, slot/use inventory and fixed binding-envelope validator | actual typed literals -> typed fixed-value payload/schema/uses plus target-type demands; closed literal-role inventory rejects shape extraction and rebind | C05/C06/C07/C27/C28/C29/C30/C40; missing/extra/wrong type/value/root/use/role; C26 policy/envelope change invalidates binding/source associations | public parameter syntax, execution, actual SQL placeholder order |
| 11 | 10; already-retained demands and original obligations | complete selected requirement report, project diagnostics separate; Cross-feature demand/obligation closure and report; owner: plan demand/obligation projection and its current target-neutral report consumer | checks the already-captured inventories from2–10 for exact completeness, scope and repeated-use retention; emits real requirement report | C18/C21/C31/C32/C33; delete inventory, unmapped demand, repeated-use loss | delayed first capture, provider matching, runtime enforcement |
| 12 | 11; already-retained role-tagged source/generated origins | forward/reverse source queries and diagnostic origin composition; Full source-map queries and diagnostic origin composition; owner: plan-origin forward/reverse query and diagnostic composition owner | forward/reverse maps for imports, derived nodes, binds and Unicode; minimum origins already captured in2–11 | C22/C24/C35/C36/C37; Unicode/escape/import, missing type or membership origin | real emitted SQL coordinates/LSP protocol |
| 13 | 11,12; VERIFIED plan + explicit target/profile/catalog | per-demand assessment and complete aggregate/remaining blockers; Explicit target/profile requirement assessment; owner: plan-target assessment adapter over existing capability/profile providers; audit true-consumer guards here | proposition-preserving provider mapping; per-demand results and truthful aggregate/remaining blockers, not all-of-empty success | C18/C19/C20/C27/C31/C32; actual evidence scope, unknown/absent/conflict/unsupported; C26 target/profile-only change reassesses target without mutating plan | emitter/executor/install discovery and speculative capability catalog |
| 14 | 13; complete runtime view and explicit document input contract | encoder/evaluator + minimum registered process and installed consumer; Private portable ProjectSQLPlan observation and total evaluator; owner: private plan encoder/evaluator, one minimal probe plus existing acquisition/reader adapters; runtime observer already exists | real view -> typed closed document; field-level corruption + small real process family, standalone/batch/relocation/wheel and direct-reader integration | C23/C24/C25/C40/C42/C43; corrupt each mandatory link/role, duplicate JSON keys, limits | executable deserialization or full corpus catch-up |
| 15 | 14; already-working family and all per-feature tests | full real-source Python/seed/relocation/wheel/mutation matrix; Whole selected-plan real-source E2E and differential conformance; owner: broaden already registered plan corpus and full matrix conformance; no first-consumer/registration catch-up | expand existing14 family to complete authorized real-source/type/source-map/target/mutation matrix and historical controls | P01–P09; records/bytes/rejections, old-format controls, no production catch-up | first registration or catching up missing production |
| 16 | 1–15; exact publications and behavior evidence | P01–P10 completion/limitation/Phase66 handoff ledger; Completion audit and Phase66 handoff; owner: completion contract/static principal and sole lifecycle/inventory readers; no production | exit/retention/limitations ledger verified by existing behavior evidence | P01–P10 and all retained owners; audit only, any Phase65-owned gap blocks | production work or Phase66 route approval |

Slice8 keeps the visible quotient and immediately following ORDER/LIMIT with one
consumer; Slice5 adapts already-complete JOIN meanings through one scope rule.
If later orientation finds either delivery too large, revise the route before
implementation. N16 does not permit hidden integration or audit-time production.

### Actual 14/15/16 alternatives

- **15:** combine16-route Slice11 demand/obligation collection and Slice13 target assessment, scheduling source maps before the merged delivery. Same overall scope, but semantic demand and provider interpretation change together, making unknown/unsupported/enforcement faults harder to isolate.
- **14:** additionally combine16-route Slice14 portable boundary and Slice15 whole-process conformance. Feasible in principle, but schema/type-role integration and costly consumer migration again meet at a single publication exit, reproducing a concrete Phase64 risk.
- **16 (selected):** keeps those two distinctions visible and separately verifiable. It costs two publication cycles; there is no measured speed claim. The user explicitly values smaller causal units after Phase64. No filler enum-only or wrapper-only Slice is added.

## 9. Phase-65 completion exits

| Exit | Material success condition |
| --- | --- |
| P01 | One explicit eligible result/root produces a valid plan; incompatible/unverified/error/terminal inputs cannot masquerade as concrete. |
| P02 | Source descriptors, reachable producer definitions and all uses/ports/symbol scopes are complete, exact and deterministic. |
| P03 | Existing row/JOIN/group/window/QUALIFY/DISTINCT/set/order/limit meaning survives query-block planning without invented rewrites. |
| P04 | Typed fixed data-literal slots/payload/uses are complete, exact and immutable; structural and unknown-context literals remain classified; target representation/overload demands and rendered placeholders stay separate. |
| P05 | Exact source-to-plan and reverse origin queries cover authored and generated sites without fabricated coordinates. |
| P06 | Mandatory requirement sites cannot be omitted; original pending obligations and proposition-scoped target evidence have closed distinct states and all blocker evidence; no check/lowering/execution equivalence. |
| P07 | Independent verification/invalidation and runtime inspection accompany all supplied plan features. |
| P08 | Closed portable plan evidence includes context identity, typed values, role-tagged origins and required links; actual positive/field-level-corruption/process/old-format compatibility coverage exists. |
| P09 | The reviewed corpus is stable across actual supported Python/seeds/relocation/installed wheels using the existing invocation-local acquisition; totals are derived from the new exact registry, not copied as16/74 forever. |
| P10 | Private/public/package boundaries and complete Phase66 consumer handoff are documented; no Phase65-owned open item is concealed. |

No single-file/public SQL command is a completion exit. No test-count target substitutes for these products.

## 10. External design review (eleven required fields per reference)

These eleven 11-field records retain the packet's dated interpretation. This execution separately fetched the official pages and exact source blobs listed in the current-read receipt below. A dated rolling page is not an immutable release certificate. No external framework was installed, no external repository test suite or database ran, and optional reference scripts/results were not used as Pietto test evidence.

### R01 PostgreSQL18 SELECT / WITH
1. Snapshot/date: PostgreSQL18 SELECT/WITH and PREPARE documentation, freshly reread for v2 on2026-09-10; links in11.
2. Problem/constraints: stage order, scope/FD limitations, context-inferred parameter types, and materialization/evaluation.
3. Semantic/identity model: SQL scopes and explicitly referenced CTE names; CTE folding depends on conditions.
4. Layering/dependency: backend SQL semantics and optimizer behavior, not Pietto semantic identity.
5. Algorithms/complexity: no PostgreSQL planner algorithm or performance claim adopted.
6. Interface/version/capability:18 docs are reference evidence, not a universal provider certificate.
7. Testing/operational lifecycle: read documentation; no DB run.
8. Pitfalls/migration: CTE spelling alone is not a cross-backend evaluation promise; ordering scope matters.
9. Disposition: ADAPT stage/materialization counterexamples.
10. WHAT_NOT_TO_COPY: executor, planner search, implicit CTE defaults, DML/recursion.
11. Pietto owner affected:65 block/requirements;66 dialect realization;68 fulfillment.

### R02 MySQL8.4 PREPARE / derived tables
1. Snapshot/date:MySQL8.4 PREPARE and derived-table docs, freshly reread for v2 on2026-09-10.
2. Problem/constraints: parameter markers, identifier positions, derived merging and ordering.
3. Semantic/identity model: markers are data values, not identifiers; inferred parameter types depend on expression position/context; derived relations may merge/materialize.
4. Layering/dependency: prepared-session/execution ownership is outside compiler core.
5. Algorithms/complexity: no optimizer heuristic imported or benchmark inferred.
6. Interface/version/capability: explicit8.4 reference, not unversioned MySQL support.
7. Testing/operational lifecycle: docs only, no connection/preparation.
8. Pitfalls/migration: source labels cannot become binds; inherited ordering/materialization defaults differ.
9. Disposition: ADAPT negative requirements and transport boundaries.
10. WHAT_NOT_TO_COPY: server session resources, optimizer hints, implicit reprepare behavior.
11. Pietto owner affected:65 parameters/sources;66 backend;68 session.

### R03 Apache Calcite SqlImplementor
1. Snapshot/date: official rolling Javadoc,2026-09-10.
2. Problem/constraints: relational-to-SQL context, input clauses, subquery decisions.
3. Semantic/identity model: explicit expression context, AliasContext and per-input results.
4. Layering/dependency: conversion consumes logical nodes; not upstream semantic re-resolution.
5. Algorithms/complexity: inspect context interface only; no performance claim.
6. Interface/version/capability: dialect-bound API is a reference, not a dependency.
7. Testing/operational lifecycle: API inspection only.
8. Pitfalls/migration: copying one alias set or name-based maps would not preserve Pietto occurrence roles.
9. Disposition: ADAPT context/block separation.
10. WHAT_NOT_TO_COPY: full rule planner, Java object graph, unconditional conversion defaults.
11. Pietto owner affected:65 scopes/blocks;66 converter.

### R04 Apache DataFusion SQL unparser
1. Snapshot/date: `datafusion/sql/src/unparser/plan.rs`, source blob `18af08fc18361322015080ef838803f79f880b8e`, retrieved2026-09-10.
2. Problem/constraints: logical plan -> SQL AST and clauses crossing derived-projection boundaries.
3. Semantic/identity model: one aggregate-scope helper prepares SELECT/GROUP/HAVING/QUALIFY/ORDER consistently.
4. Layering/dependency: logical plan consumed by unparser, SQL text follows AST.
5. Algorithms/complexity: no unparser throughput claim or algorithm adopted wholesale.
6. Interface/version/capability: explicit conversion can fail; source sample is not full compatibility audit.
7. Testing/operational lifecycle: source read only.
8. Pitfalls/migration: shared clause-scope logic prevents fixing SELECT while leaving ORDER stale.
9. Disposition: ADAPT common scope consumer boundary.
10. WHAT_NOT_TO_COPY: name stripping/unprojection as a substitute for Pietto exact port images, Arrow identity, SessionContext.
11. Pietto owner affected:65 query blocks/projection scope;66 AST.

### R05 SQLGlot scope model
1. Snapshot/date: `sqlglot/optimizer/scope.py`, blob `9965be0cc893c0f5f80a8c271d587c29f6c0aff0`, retrieved2026-09-10.
2. Problem/constraints: root/derived/set scopes and local/external column visibility.
3. Semantic/identity model: explicit scope variants and parent/source collections.
4. Layering/dependency: SQL AST name-scope analysis, not Pietto semantic authority.
5. Algorithms/complexity: sample inspected; no generic optimizer adopted.
6. Interface/version/capability: rolling source, pinned blob evidence.
7. Testing/operational lifecycle: no package installed or external tests run.
8. Pitfalls/migration: convenient name-keyed maps cannot replace occurrence-complete Pietto maps.
9. Disposition: ADAPT scope taxonomy and visibility questions.
10. WHAT_NOT_TO_COPY: inferred winner resolution, its optimizer/AST as our IR, broad dialect defaults.
11. Pietto owner affected:65 hygienic symbols/verification;70 later captures.

### R06 SQLAlchemy2.0 bind expressions
1. Snapshot/date:2.0 official Column Elements docs,2026-09-10.
2. Problem/constraints: separate binding expressions/keys/types/values and compiler names.
3. Semantic/identity model: BindParameter can retain type/value and unique naming behavior.
4. Layering/dependency: bind expressions are distinct from execution/session machinery.
5. Algorithms/complexity: no implementation or caching algorithm copied.
6. Interface/version/capability: examples inform roles, not a dependency/API choice.
7. Testing/operational lifecycle: docs only.
8. Pitfalls/migration: automatic literal conversion, expanding parameters and callables exceed our closed source proof boundary.
9. Disposition: ADAPT logical slot/use/rendered-position separation.
10. WHAT_NOT_TO_COPY: runtime callbacks, execution APIs, value-based inferred type or anonymous-name defaults.
11. Pietto owner affected:65 bind transport;66 emitted placeholders;68 execution.

### R07 MLIR Language Reference
1. Snapshot/date: official LangRef, rolling2026-09-10.
2. Problem/constraints: values, uses, region visibility, verification.
3. Semantic/identity model: operation results and block arguments are values; textual names are not preserved IR identity.
4. Layering/dependency: explicit scopes/regions constrain legal references.
5. Algorithms/complexity: no pass manager/dialect framework imported.
6. Interface/version/capability: reference rules adapted to private plan roles, not wire/API compatibility.
7. Testing/operational lifecycle: documentation review only.
8. Pitfalls/migration: unknown scope/type must not become ambient access.
9. Disposition: ADAPT nominal role and verification discipline.
10. WHAT_NOT_TO_COPY: mutable global context, full SSA/CFG infrastructure, universal operation interface.
11. Pietto owner affected:65 ports/symbols/verifier;later88–90.

### R08 Substrait serialization basics
1. Snapshot/date: official basics, rolling2026-09-10.
2. Problem/constraints: explicit roots and shared plan collections.
3. Semantic/identity model: root plan references other trees; collection interpretation belongs to the consuming library.
4. Layering/dependency: serialization does not define the user's selected-result policy.
5. Algorithms/complexity: reference-sharing avoids treating a graph as mandatory duplicated trees; no runtime cost claim.
6. Interface/version/capability: no protobuf dependency or exact Substrait compatibility promised.
7. Testing/operational lifecycle: documentation only.
8. Pitfalls/migration: root semantics must be specified, not inferred from collection order.
9. Disposition: ADAPT explicit selection and references.
10. WHAT_NOT_TO_COPY: public protobuf as internal authority, implicit root/evaluation policy.
11. Pietto owner affected:65 result selection/portable structure.

### R09 Malloy StageWriter
1. Snapshot/date: commit `431278999ad463c0a2d70e6aff06cd9cdd4f5303`, `packages/malloy/src/model/stage_writer.ts`.
2. Problem/constraints: composing generated SQL stages and stage names.
3. Semantic/identity model: named stages and parent writer; supports CTE or derived SQL forms.
4. Layering/dependency: practical SQL assembly, not a reusable Pietto semantic root.
5. Algorithms/complexity: code inspected, no performance measurement.
6. Interface/version/capability: private TypeScript implementation at pinned commit.
7. Testing/operational lifecycle: source-only review, no Malloy runtime.
8. Pitfalls/migration: last-stage selection, SQL-string storage, hash-derived persistent table names have different authority.
9. Disposition: ADAPT explicit stage boundary concept.
10. WHAT_NOT_TO_COPY: mutable global counter as identity, UDF/PDT execution, last-output winner.
11. Pietto owner affected:65 stage organization;66 SQL assembly.

### R10 Cube SQL API query format
1. Snapshot/date: current official query-format docs,2026-09-10.
2. Problem/constraints: distinguishing semantic query support, post-processing and pushdown.
3. Semantic/identity model: SQL fragments can map to semantic queries; other shapes depend on separate pushdown paths.
4. Layering/dependency: service/execution route is distinct from expression meaning.
5. Algorithms/complexity: no Cube rewrite/cost engine studied or adopted here.
6. Interface/version/capability: public service docs, not Pietto API parity.
7. Testing/operational lifecycle: no Cube service invoked.
8. Pitfalls/migration: availability of fallback execution can conceal backend inability in a compiler-only design.
9. Disposition: ADAPT explicit support-path distinction; REJECT fallback runtime adoption.
10. WHAT_NOT_TO_COPY: cache availability, pushdown env flags, service/connection/runtime as semantic authority.
11. Pietto owner affected:65 requirement outcomes;68/69 later adapters.

### R11 ECMA-426 source maps
1. Snapshot/date: official source-map spec,2026-09-10.
2. Problem/constraints: generated/original coordinate domains.
3. Semantic/identity model: JS/CSS columns use UTF-16, Wasm uses byte positions; content types may differ.
4. Layering/dependency: mapping transport must not redefine Pietto parser coordinates.
5. Algorithms/complexity: do not adopt VLQ codec or mapping machinery without a consumer.
6. Interface/version/capability: no claim of ECMA source-map conformance.
7. Testing/operational lifecycle: spec read; Unicode counterexample required in our tests.
8. Pitfalls/migration: codepoint/UTF-16/UTF-8 byte offsets are not interchangeable.
9. Disposition: ADAPT coordinate-unit discipline.
10. WHAT_NOT_TO_COPY: browser-specific schema, optional-error defaults, byte offsets guessed before rendering.
11. Pietto owner affected:65 origin maps;66 SQL ranges;75 editor conversion.

### Current primary-source read receipt — 2026-09-10

R01 SELECT/Functional Dependencies、PREPARE/Description、WITH/Materialization；
R02 PREPARE parameter-context rules、derived-table ORDER/merge conditions；
R03 SqlImplementor Context/AliasContext/Result/Clause interfaces；R06 bindparam
key/type/value/unique/expanding/callable roles；R07 LangRef identifiers and regions；
R08 plan collections/root references；R10 regular/post-processing/pushdown distinction；
R11 source-map coordinate definitions：本session分别成功打开§11对应official URLs。
它们是dated/version-labelled rolling reads，不是immutable release certificates。

R04通过GitHub Git blob API读取并验证 `18af08fc18361322015080ef838803f79f880b8e`
（124097 bytes），重点读 `UnparserAggScope::prepare/normalize/prepare_sort_expr`
及相关clause调用；R05同样读取并验证blob
`9965be0cc893c0f5f80a8c271d587c29f6c0aff0`（39512 bytes），重点读ScopeType、
Scope、selected_sources、references、external_columns。blob身份不是commit SHA，
下列API URL精确定位内容，不把rolling main链接当该blob的永久证据：

- [DataFusion exact blob](https://api.github.com/repos/apache/datafusion/git/blobs/18af08fc18361322015080ef838803f79f880b8e)
- [SQLGlot exact blob](https://api.github.com/repos/tobymao/sqlglot/git/blobs/9965be0cc893c0f5f80a8c271d587c29f6c0aff0)

R09 GitHub HTML打开失败；用同一primary仓库contents API在已指定commit
`431278999ad463c0a2d70e6aff06cd9cdd4f5303`成功读取完整StageWriter，
验证blob `ae510dd88595ba1818e6af8ee3fa58e53bff4812`（4057 bytes）。
实读涵盖nextName/addStage/combineStages/generateSQLStages与UDF/PDT，
这些执行/末端winner/计数器行为明确不复制。三个blob只作外部source读取，未执行。

## 11. Source links and reproducibility

Primary Pietto source root:
`https://github.com/MianliWang/pietto/tree/d7af544dd4ce48891d5fe2596ab23e494f48d4ab`

Key contract paths:
- `AGENTS.md`
- `docs/architecture/phase-initiation-gate-v1.md`
- `docs/architecture/product-architecture-v1.md`
- `docs/architecture/identity-and-authority-laws-v1.md`
- `docs/architecture/layering-and-coupling-laws-v1.md`
- `docs/spec/phase64-completion-audit-phase65-handoff-v1.md`
- `docs/spec/phase64-flat-relational-algebra-product-phase-initiation-gate-v3-source-audit-architecture-route-lock-v1.md`
- `docs/spec/phase52-logical-type-literal-parameter-nullability-inventory-v1.md`
- `docs/roadmap.md` (Future Roadmap v6,66–97)

External URLs reviewed:
- https://www.postgresql.org/docs/18/sql-select.html
- https://www.postgresql.org/docs/18/sql-prepare.html
- https://www.postgresql.org/docs/18/queries-with.html
- https://dev.mysql.com/doc/refman/8.4/en/prepare.html
- https://dev.mysql.com/doc/refman/8.4/en/derived-table-optimization.html
- https://calcite.apache.org/javadocAggregate/org/apache/calcite/rel/rel2sql/SqlImplementor.html
- https://github.com/apache/datafusion/blob/main/datafusion/sql/src/unparser/plan.rs (exact read blob above)
- https://github.com/tobymao/sqlglot/blob/main/sqlglot/optimizer/scope.py (exact read blob above)
- https://docs.sqlalchemy.org/en/20/core/sqlelement.html
- https://mlir.llvm.org/docs/LangRef/
- https://substrait.io/serialization/basics/
- https://github.com/malloydata/malloy/blob/431278999ad463c0a2d70e6aff06cd9cdd4f5303/packages/malloy/src/model/stage_writer.ts
- https://docs.cube.dev/reference/core-data-apis/sql-api/query-format
- https://tc39.es/ecma426/

The inherited packet reported unavailable rolling SQLGlot/Malloy endpoints and a DataFusion blog. Those failures are not new reads in this execution. This session's successful official-page and exact-blob reads, including the Malloy HTML-to-contents-API substitution, are identified above. No external code or database was executed.

## 12. Review, write closure and publication

本次 review interface 是 installed `ponytail` FULL 与 `ponytail-review` SKILL.md，
由同一 foreground primary writer 完整审阅 decision/contract/principal/reader unit；
这属于 self-review，不声称第三方独立审核。packet 的三轮和17个参考检查是
继承记录；未执行其 optional scripts，未把它们注册为 Pietto oracle。

首次编辑前完整读取三个 mutable-reader functions：
`test_active_status_table_and_authority_prose_are_exact`、
`test_active_roadmap_current_owner_sentence_and_routes_are_exact`、
`test_phase64_route_section_is_exact`，连同 `_read/_section/_table_rows`、
EXPECTED_STATUS、EXPECTED_CURRENT_OWNER_SENTENCE、所有被它们消费的
current/historical route/state/path constants。只对现行Phase65状态、对应route及
前次handoff的历史时点作计划迁移；旧期望不误作当前状态。

完整 inventory owner `test_no_gain_closure_restores_exact_two_stage_typing_authority`
继续独占动态文件计数；新 principal 不复制 inventory、不读 mutable lifecycle docs。
`test_active_lifecycle_reader_is_the_only_mutable_document_reader` 和其
`_document_readers` 使用 REPOSITORY_FACTS.string_literals；新 principal 连
mutable path string 都不直接引用。其source acquisition复用既有REPOSITORY_FACTS。

历史/临时negative reader audit：Phase64 Slice11 principal只读取immutable
handoff/route并将历史Git checks绑定fixed objects；Interlude II Slice4的
`test_phase64_transferred_subjects_remain_unimplemented`读取其immutable readiness，
live只保留INNER/LEFT子集。Phase52 lookup/inventory consumer guards完整保留当前
SOURCE/FACTS/INVENTORY/SIGNATURE/CONTEXT/AGGREGATE/WINDOW/WINDOW_STRATEGY/
PROFILE/SELECTOR/EXTENSION_PROVIDER/EXTENSION_INSPECTION/PROVIDER/COMPOSITION/
CHECKING/INSPECTION路径集合；新source consumer迁移由未来Slice13首次实施时
闭合，Slice1没有新增production消费者。当前七family registry与历史六family
记录分开；Slice14需同步probe/batch/acquisition/relocation/standalone/installed及
其直接历史reader，Slice15不得补第一次注册。没有本Slice所需outside-path修复。

六路径用途冻结如下；ordinary mechanical counts不是新增authority：

```text
A docs/spec/phase65-project-sql-plan-product-phase-initiation-gate-source-audit-architecture-route-lock-v1.md
A tests/test_phase65_slice1_project_sql_plan_phase_initiation_gate_route_lock.py
M docs/status.md
M docs/roadmap.md
M tests/test_active_phase_lifecycle.py
M tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

依次用途：immutable决策和证据；small static trace principal；当前生命周期；
N16路线及新later-owner映射；sole lifecycle reader同步；sole inventory owner
`production Python187 ->187; test Python445 ->446`。本候选预期A2/M4/D0。
production/grammar/generated/dependencies/lock/workflow/version/goldens/public schemas
对exact baseline零变化；这个零delta属于本候选seal，不是对future HEAD的永久断言。
历史集合/absence只绑定固定Git objects，live法律不冻结未来enum/filename总集合。
仅确切missing Git-object checks允许shallow skip，core static checks永远运行，
pytest不fetch网络或执行历史source。

初始draft和计划reader迁移不是correction。production corrections=0；document/static
corrective groups<=4；authoritative validator starts<=4；initial ordinary commit=1；
natural-CI repair child<=1且同六路径/剩余budget。完整finding set一次按因果修正，
保留失败。新product/trust/长期架构选择、production缺陷、baseline drift、越界路径
或预算耗尽均STOP，不将本期gap转给后期以取得PASS。

内容完成并review后，双Python运行new principal、sole lifecycle/inventory及reader
guard，early test Pyright/Ruff/format；最终执行正常完整命令：

```bash
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
UV_PYTHON=3.13 uv run python scripts/check_generated.py
UV_PYTHON=3.13 uv run python scripts/check_goldens.py
UV_PYTHON=3.13 uv run python scripts/package_smoke.py
```

使用正常locked/populated cache和现行acquisition/resource/xdist policy，无reduced
selection或新增skip/xfail；39 goldens、native generated、final-input sdist/wheel/
installed CLI、diff与forbidden delta检查必须通过。大Phase64 broad/matrix不额外
重复。结果绑定exact tested tree；中断先恢复，不对未变失败候选lucky rerun。
最终receipts在仓库外；seal后rebind/stage exact tree，ordinary commit
`Lock Phase 65 ProjectSQLPlan architecture and route`，ff push main，自然
exact-head `push/main/attempt 1/success`双Python四步骤建立终态。
不amend/rebase/force/rerun/dispatch/tag/release/sign/attest/status-only commit。

Slice2输入为本合同加exact completed.ok / VERIFIED bundle / selected TABLE/QUERY
owner及最小static source；出口是scan/projection真实block/export map、local
origins/demands、独立verifier/runtime view及root/omission/unsupported-stage反例。
Slice2不实现本期其他operator、参数抽取或公开入口。
