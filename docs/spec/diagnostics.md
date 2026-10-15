# Pietto Diagnostic Codes

Pietto diagnostics use the canonical format:

```text
PIE-<PHASE><NUMBER>
```

`PHASE` identifies the compiler or execution stage:

| Prefix | Stage |
|---|---|
| `PIE-P` | Parser, lexer, and indentation |
| `PIE-S` | Semantic analysis |
| `PIE-I` | IR and SQL compilation |
| `PIE-B` | Backend capabilities |
| `PIE-R` | Runtime and execution |

`NUMBER` is a four-digit identifier within the phase. Diagnostic severity is
stored separately and is never encoded in the code.

## Parser Diagnostics

| Code | Meaning |
|---|---|
| `PIE-P1000` | Generic syntax error |
| `PIE-P1003` | Invalid indentation or inconsistent dedent |
| `PIE-P1004` | Tab or mixed indentation |
| `PIE-P1005` | Unsupported brace-style block |
| `PIE-P1006` | UTF-8 source byte budget exceeded |
| `PIE-P1007` | Raw non-EOF lexer token budget exceeded |

## Semantic Diagnostics

| Code | Meaning |
|---|---|
| `PIE-S2001` | Duplicate name in one semantic scope or namespace, including a schema-v2 local type/source/relation bucket and an EXPLICIT_MODULES relation let named like another let of its declaration, a module relation name (including a relation import binding that does not resolve) or a JOIN binding of its declaration (reported at the let), and a repeated query header parameter name (reported at the later parameter), and a repeated typed VALUES column name (reported at the repeated column) |
| `PIE-S2002` | Unknown local or explicit-module type reference |
| `PIE-S2003` | Local type alias cycle, including within one acyclic schema-v2 module |
| `PIE-S2004` | Invalid Decimal precision-scale type arguments |
| `PIE-S2005` | Implicit nullability; single-file severity follows `--check-mode` (else a header `mode`, else CHECKED): omitted in LOOSE, WARNING in CHECKED, ERROR in STRICT |
| `PIE-S2006` | Semantic analysis recursion limit exceeded |
| `PIE-S2102` | Unknown field, including a schema-v2 minimal direct row-fact projection and the column of an EXPLICIT_MODULES `scalar relation.column` read (reported at the read) |
| `PIE-S2103` | Unknown function |
| `PIE-S2104` | Invalid built-in function arguments |
| `PIE-S2105` | Invalid operator operands, including known comparison or `between` operands from different comparable type families, and an EXPLICIT_MODULES `in` read whose left value does not pair with the read column or whose read block has known columns that are not exactly one, reported at the test; ERROR in LOOSE/CHECKED/STRICT. `Text` against `Date`, `Timestamp` or `UUID` is not checked yet (see `operator-comparison-matrix-contract-v1.md`). |
| `PIE-S2110` | Duplicate query-local named-window declaration |
| `PIE-S2111` | Dangling query-local named-window declaration or use reference |
| `PIE-S2112` | Query-local named-window dependency cycle |
| `PIE-S2113` | Named-window monotonic component conflict |
| `PIE-S2202` | Known non-Bool expression in a predicate context |
| `PIE-S2301` | Unknown local or explicit-module relation, including the name of an EXPLICIT_MODULES `exists`, `scalar` or `in` read, reported at the read |
| `PIE-S2302` | Local relation dependency cycle, including within one acyclic schema-v2 module and through the relation lets of one EXPLICIT_MODULES declaration; the message follows one cycle of reads, starting with the member written first, where a declaration's lets count as written before it; when cycles share members, it names one of them; an EXPLICIT_MODULES `exists`, `scalar` or `in` read that would make its block read itself, directly or through its lets or a module table or query, reports it at the read |
| `PIE-S2303` | Invalid, missing, or untyped direct local/imported source shape; for a source without a shape, single-file severity follows `--check-mode` (else a header `mode`, else CHECKED): omitted in LOOSE, WARNING in CHECKED, ERROR in STRICT |
| `PIE-S2304` | Computed projection without an explicit alias; single-file severity follows `--check-mode` (else a header `mode`, else CHECKED): omitted in LOOSE, WARNING in CHECKED, ERROR in STRICT. Project checks do not follow `--check-mode` or a header `mode`; where they report it, it is an ERROR. |
| `PIE-S2305` | Duplicate projection output name |
| `PIE-S2306` | Invalid source connector or connector arguments |
| `PIE-S2307` | Static relation LIMIT operand is invalid; emits error message `Limit must be a static integer from 0 to 9223372036854775807` |
| `PIE-S2308` | Aggregate used in an invalid context |
| `PIE-S2309` | Aggregate called with the wrong arity |
| `PIE-S2310` | Aggregate composition is deferred |
| `PIE-S2311` | Nested aggregate is unsupported |
| `PIE-S2312` | Aggregate projection mixed with non-aggregate projection without `GROUP BY` |
| `PIE-S2313` | Aggregate projection without an explicit alias |
| `PIE-S2314` | Aggregate field argument has an unsupported type |
| `PIE-S2315` | Aggregate expression argument is deferred |
| `PIE-S2316` | Historical GROUP BY IR/SQL lowering gate, retired after SQL lowering |
| `PIE-S2317` | Duplicate GROUP BY key |
| `PIE-S2318` | Non-grouped projection in grouped relation |
| `PIE-S2319` | Grouped scalar projection is deferred |
| `PIE-S2320` | Pure grouped output without an aggregate is deferred |
| `PIE-S2321` | Grouped ORDER BY is deferred |
| `PIE-S2322` | Historical `satisfying` IR/SQL lowering gate, retired after source pipeline enablement |
| `PIE-S2323` | `satisfying` used without `GROUP BY` |
| `PIE-S2324` | Unknown select output name in `satisfying` |
| `PIE-S2325` | Input field referenced instead of select output in `satisfying` |
| `PIE-S2326` | Unsupported select output referenced in `satisfying` |
| `PIE-S2327` | Unsupported expression form in `satisfying` |
| `PIE-S2328` | Parsed `let:` binding uses an unsupported lowering boundary outside the current row-level inline expansion MVP |
| `PIE-S2329` | Invalid `let:` binding name, shadowing, duplicate name, or projection output conflict |
| `PIE-S2330` | Invalid `let:` binding dependency order, self-reference, or cycle |
| `PIE-S2331` | `QUALIFY` lacks both a selected window result and a hidden predicate window computation |
| `PIE-S2332` | `QUALIFY` reference is unknown or ambiguous across visible pre-window inputs and selected window results |
| `PIE-S2333` | Project relation semantic completion is unavailable, including a later tail whose required intrinsic-grain proof is explicitly UNKNOWN |
| `PIE-S2334` | A flat-relational operation or named set input remains unavailable; ERROR in LOOSE/CHECKED/STRICT, retaining existing messages and authored spans. Successful supported explicit-module INNER/LEFT/CROSS/RIGHT/FULL/SEMI/ANTI and set operations retire only their exact owner-held temporary admission diagnostics. Condition readiness alone, failed sets and other entrypoints do not remove this boundary. |
| `PIE-S2335` | JOIN pre-match input/reference/type or scalar context is unavailable, unknown, forward or ambiguous; ERROR at the exact JOIN/reference/expression span. Existing scalar-kernel and Bool-consumer diagnostics retain their codes and objects. |
| `PIE-S2336` | Unsupported authored JOIN combination: CROSS with ON/VIA, multi-hop VIA with ON, or a multi-hop new kind; ERROR at the authored JOIN span. |
| `PIE-S2337` | An explicit private single-match requirement is legal but not statically proved at its exact matching boundary; WARNING in LOOSE/CHECKED/STRICT, including successful completed project checks. Counts actual matched right BAG occurrences; downstream enforcement remains required, including when private combined IR is correctly VERIFIED. Inspection retains the obligation and diagnostic identity. No request or PROVED produces no such warning. |
| `PIE-S2338` | An explicit private single-match request has an invalid owner/use/root, direction/role, scope, unit, or matching boundary (including CROSS); ERROR in every mode, with no valid obligation or proof. Private combined IR keeps the affected owner non-concrete; existing operation diagnostics remain. |
| `PIE-S2339` | A final visible DISTINCT field lacks approved exact row-equivalence capability; ERROR in LOOSE/CHECKED/STRICT, preserving field/type/reason and selected-expression location. Includes Any/Bytes/Json, missing/invalid/unpropagated Decimal parameters, and Float (including resolved aliases and finite literals) deferred to Phase 72. No successful DISTINCT quotient or full-row uniqueness is produced. Hidden or unselected fields do not enter this check. |
| `PIE-S2340` | Relation ORDER after DISTINCT is not proved functionally determined by the complete visible row; ERROR at the offending ORDER expression. Existing exact strict FD evidence may justify a hidden input; no representative, first/last/min/max or automatic aggregate is chosen. |
| `PIE-S2341` | Set operation omits explicit ALL/DISTINCT or has fewer than two authored operands; ERROR at the operation span in every check mode. |
| `PIE-S2342` | A set operand has no concrete completed input or its visible width differs; ERROR at the operand span for unavailable inputs or the operation span for width mismatch, without partial output or first-available fallback. Existing precise missing/ambiguous input diagnostics remain. |
| `PIE-S2343` | Corresponding set fields lack exact compatible canonical types or independently validated identical Decimal precision/scale; ERROR at the operand span. Unknown types do not match themselves. |
| `PIE-S2344` | A set operation requiring row equivalence has an unsupported participating field; ERROR at the operand span for UNION DISTINCT and both INTERSECT/EXCEPT forms. Includes Float/aliases deferred to Phase 72, Any/Bytes/Json and unavailable equality evidence. UNION ALL requires exact shape/type compatibility but no row equivalence. |
| `PIE-S2345` | A relation `let NAME:` declaration is parsed but not yet available; ERROR in LOOSE/CHECKED/STRICT at the declaration span. Like PIE-S2346..PIE-S2352 (except a query header an EXPLICIT_MODULES project admits and an EXPLICIT_MODULES `exists`, `scalar` or `in` read inside a relation body), it is a temporary pre-admission diagnostic: every occurrence, including nested ones, is reported in (path, line, column, code) order before any semantic analysis, which then does not run. In an EXPLICIT_MODULES project the let declaration itself and its `capture` lines are admitted, and read errors of an admitted let are PIE-S2302, PIE-S2359 and PIE-S2360, and for a let with `capture` lines PIE-S2370, never PIE-S2345. |
| `PIE-S2346` | An entry-query header parameter is parsed but not available here; ERROR in every check mode at each parameter span. It applies in single-file analysis, in LEGACY_FLAT projects, and in EXPLICIT_MODULES projects to a header whose query has a VALUES, set-operation or table-function FROM body. An EXPLICIT_MODULES query whose own FROM reads a relation admits its header, with or without relation lets (PIE-S2353..PIE-S2356). |
| `PIE-S2347` | A typed VALUES body, including its zero-row header form, is parsed but not yet available; ERROR in every check mode at the VALUES body span. In an EXPLICIT_MODULES project a VALUES table, query or let body is available and is checked by PIE-S2001 and PIE-S2361..PIE-S2365 instead. |
| `PIE-S2348` | A `scalar relation.column` read is parsed but not yet available; ERROR in every check mode at the expression span. In an EXPLICIT_MODULES project a closed read inside a relation body is available, and PIE-S2348 is instead a semantic ERROR at the read when it is written outside WHERE and the SELECT of an ungrouped query (JOIN ON, a row `let:`, the SELECT of a grouped or aggregate query, SATISFYING, a window, QUALIFY, ORDER BY or LIMIT) or reads a relation whose columns are not known before completion (a set, an authored JOIN, a relation reading one of them or a typed VALUES body, or a relation whose own errors leave its columns unknown; a VALUES body itself is read by its header), whatever column it names; outside a relation body it stays the pre-admission diagnostic. |
| `PIE-S2349` | An `exists relation` reference is parsed but not yet available; ERROR in every check mode at the expression span. The call `exists(name)` is unchanged. In an EXPLICIT_MODULES project a closed read inside a relation body is available, and PIE-S2349 is instead a semantic ERROR at the read when it is written outside WHERE and the SELECT of an ungrouped query (JOIN ON, a row `let:`, the SELECT of a grouped or aggregate query, SATISFYING, a window, QUALIFY, ORDER BY or LIMIT); outside a relation body it stays the pre-admission diagnostic. |
| `PIE-S2350` | An `in relation` or `not in relation` reference is parsed but not yet available; ERROR in every check mode at the membership expression span. Literal lists such as `in (vip)` are unchanged. In an EXPLICIT_MODULES project a closed read inside a relation body is available, and PIE-S2350 is instead a semantic ERROR at the read when it is written outside WHERE and the SELECT of an ungrouped query (JOIN ON, a row `let:`, the SELECT of a grouped or aggregate query, SATISFYING, a window, QUALIFY, ORDER BY or LIMIT); outside a relation body it stays the pre-admission diagnostic. |
| `PIE-S2351` | A `capture` line of a relation let is parsed but not yet available; ERROR in every check mode at the line span. In an EXPLICIT_MODULES project capture lines are available (PIE-S2366..PIE-S2370); single-file and LEGACY_FLAT projects keep this pre-admission diagnostic. |
| `PIE-S2352` | A table-function FROM input such as `from generate_series(1, 31, 1) as n` is parsed but not yet available; ERROR in every check mode at the FROM clause span. |
| `PIE-S2353` | An admitted query header parameter declaration is invalid: its type is not exactly `Bool`, `Int`, `Float` or `Text` without arguments, it omits `not null`/`nullable`, or it is a parameter after the 64th; ERROR at the parameter span before semantic analysis. A repeated parameter name reports `PIE-S2001` at the later parameter. |
| `PIE-S2354` | A query header parameter name is also an input field (a typed VALUES column of a FROM or JOIN input included), a `let:` name, a relation name visible in the module, a JOIN binding, a SELECT output or a named window of that query or of one of its relation lets, or the name of one of its relation lets; ERROR at the parameter span. An unaliased SELECT item that reads a parameter, in the query or in one of its lets, would name its output after it and reports this code at the read. |
| `PIE-S2355` | A query header parameter is read outside the available positions; ERROR at the read, before semantic analysis. Reads, and `let:` bindings or outputs whose value reads one, are available beneath unary, binary, comparison, null-test, BETWEEN, conditional, literal-list IN and CAST operators and the value arguments of `lower`, `upper`, `trim`, `contains`, `starts_with`/`ends_with` (first argument), `coalesce`, `nullif` and `sign`, in `let:` bindings, `where`, JOIN `on`, the SELECT items of a query without GROUP BY, SATISFYING or aggregates (where a SELECT item that is a window call also takes a bare read as the value argument of `lag`, `lead`, `first_value`, `last_value` or `nth_value`, the `lag`/`lead` default, the `lag`/`lead` offset, the `ntile` bucket count or the `nth_value` position; emission blocks a `Text` or `Bool` value with PIE-B1003 `window_parameter_value_kind_not_realized_yet` and a non-`Int` default with PIE-B1003 `window_default_literal_kind_not_realized_yet`), SATISFYING, QUALIFY and ORDER BY keys that read a field, binding or output (a grouped ORDER BY key must be an output name; emission matches an ungrouped key to a `let:` binding or a restated selected expression as it does without parameters, PIE-B1003 otherwise). A grouped SELECT item may name a computed group key or apply `count`, `avg`, `min` or `max` to one `let:` name; a GROUP BY key may name a computed `let:` binding in a query without JOIN inputs. Any other position reports this code at each read or dependent name: LIMIT, other window positions (another window argument, PARTITION BY, ORDER BY, a frame offset, a read nested in an operator) and named windows (frame offsets included), other call arguments, a GROUP BY key naming a parameter, an alias or a JOIN query key, other grouped SELECT items and constant ORDER BY keys. An output name counts only in SATISFYING, QUALIFY, ORDER BY and LIMIT; elsewhere the same name reads the input field it shadows. The same rules apply in each relation let of the query. |
| `PIE-S2356` | A FROM, JOIN or set operand, or an EXPLICIT_MODULES `exists`, `scalar` or `in` read, names a query that declares header parameters, including one in a relation let or in the body of a declaration with lets; ERROR at the input or read. A query with parameters is only an entry query. |
| `PIE-S2357` | An EXPLICIT_MODULES table or query declares more than 64 relation lets; ERROR at each let after the 64th, reported with the pre-admission diagnostics before any semantic analysis, which then does not run. |
| `PIE-S2358` | A query header parameter read as a window structural count (`lag`/`lead` offset, `ntile` bucket count, `nth_value` position) is not declared `Int not null`; ERROR at the read, before semantic analysis. |
| `PIE-S2359` | An EXPLICIT_MODULES relation let is never read by `from`, a JOIN target, a set operand or an `exists`, `scalar` or `in` read of any block of its declaration; a let read only by itself is PIE-S2302 instead. ERROR at the let declaration. Its own body is still fully checked. |
| `PIE-S2360` | An EXPLICIT_MODULES relation let is nested deeper than 16 query blocks: the declaration body is depth 0 and a let read by a block at depth d is at depth d + 1 on its deepest read path; ERROR at each such let declaration in source order. |
| `PIE-S2361` | A typed VALUES column is not `Bool`, `Int`, `Float` or `Text` followed by `not null` or `nullable`; ERROR at the column's type. |
| `PIE-S2362` | A typed VALUES row has a different number of cells than its header has columns; ERROR at the row. |
| `PIE-S2363` | A typed VALUES cell is not a fixed literal (a signed number counts as one); a name, parameter, call or other expression is an ERROR at the cell. |
| `PIE-S2364` | A typed VALUES cell does not match its column's declared type and nullability, for example an `Int` outside the signed 64-bit range, an integer literal for a `Float` or `null` in a `not null` column; ERROR at the cell. |
| `PIE-S2365` | A typed VALUES body has more than 1,000 rows or 64 columns; ERROR at the VALUES body span. |
| `PIE-S2366` | An EXPLICIT_MODULES `capture` line names no single FROM or JOIN row input of its declaration body (an unknown name, a SEMI or ANTI JOIN target, or a body without a FROM relation); ERROR at the capture line, reported with the file's pre-admission diagnostics (PIE-S2345..PIE-S2352, PIE-S2357) in one (path, line, column, code) order and before its query header checks (PIE-S2353, PIE-S2355 and a header's PIE-S2001 and PIE-S2354); semantic analysis then does not run. |
| `PIE-S2367` | A relation let repeats a `capture` name; ERROR at each later line, reported like PIE-S2366. |
| `PIE-S2368` | A `capture` name is also an input of the let itself (self-correlation: the FROM name, a JOIN binding or a set operand of the let); ERROR at the capture line, reported like PIE-S2366. Rename the input through another let. |
| `PIE-S2369` | A captured field `name.field` is not a row field of the captured FROM or JOIN input (an outer row `let:` value, SELECT output, aggregate or window result is never one), or reads a captured input whose columns are not known before completion (a set, an authored JOIN, a typed VALUES body, a relation reading one of them, or a relation whose own errors leave its columns unknown), whatever field it names; semantic ERROR at the field read, in source order with the expression's other diagnostics. |
| `PIE-S2370` | A let with `capture` lines is used where correlation is not yet available: at the let when its body is not a FROM relation with an optional WHERE and an ungrouped, window-free SELECT (a JOIN, row `let:`, GROUP BY, an aggregate in WHERE or SELECT, window, QUALIFY, SATISFYING, ORDER BY, LIMIT, DISTINCT, set operation or VALUES body), except that a let joined LATERAL or read by `scalar`, `in` or `not in` (never by `exists`) may end in ORDER BY and LIMIT whose ORDER BY reads no captured field and no aggregate, and at each read of the let other than the first `exists`, `scalar`, `in`, `not in` or JOIN written in its declaration body in source order (a later such read or JOIN, FROM, set operand, or a read from another let, a JOIN included): unlike other lets, it is read exactly once; ERROR reported like PIE-S2366. A correlated read's position, column and width rules stay PIE-S2348, PIE-S2349, PIE-S2350, PIE-S2102 and PIE-S2105. |
| `PIE-S2371` | A `capture` line of a let joined LATERAL names a row input that is not left of that JOIN (the let's own JOIN binding or a later JOIN's binding); ERROR at the capture line, reported like PIE-S2366. |
| `PIE-S2372` | A RIGHT, FULL, SEMI or ANTI JOIN reads a let with `capture` lines; only `cross join`, `inner join` and `left join` read it LATERAL. ERROR at the JOIN, reported like PIE-S2366. |
| `PIE-S2401` | Constraint return type does not expand to `Bool` |
| `PIE-S2402` | Callable or field derive body type mismatch |
| `PIE-S2501` | Duplicate shape item name |
| `PIE-S2502` | Unknown unique or index target field |
| `PIE-S2503` | Duplicate unique or index target field |
| `PIE-S2504` | Derived field dependency cycle |
| `PIE-S2601` | Unknown relationship endpoint relation |
| `PIE-S2602` | Duplicate relationship metadata name |
| `PIE-S2603` | Duplicate endpoint local name within one relationship |
| `PIE-S2701` | Invalid, unselected, or unresolved local module import target |
| `PIE-S2702` | Duplicate or conflicting logical module identity |
| `PIE-S2703` | Explicit-module import dependency cycle. While any cycle exists, a project check reports besides it only parse, semantic analysis and source connector diagnostics of every module; the checks made while completing relations (for example WHERE typing, the checks at a `scalar` or `in` read, PIE-S2354 and PIE-S2356) appear once every cycle is fixed. |
| `PIE-S2704` | Duplicate, unknown, ineligible, or invalid export request |
| `PIE-S2705` | Unknown, private, or non-exported imported declaration |
| `PIE-S2706` | Local, import, alias, or export binding collision |
| `PIE-S2707` | Unresolved explicit-module reference or unsupported advanced module form |

## IR Diagnostics

| Code | Meaning |
|---|---|
| `PIE-I1000` | Missing or inconsistent semantic fact required for declaration or expression IR lowering |

## Backend Diagnostics

| Code | Meaning |
|---|---|
| `PIE-B1000` | Selected PostgreSQL/private MySQL SQL backend emission case is unsupported or invalid |
| `PIE-B1001` | SOURCE_REALIZATION: explicit selected source mapping, identifier, family or row-domain/read-only declaration cannot realize the scan |
| `PIE-B1002` | REPRESENTATION: selected logical/physical storage, value domain, nullability, Decimal parameters or output label do not correspond |
| `PIE-B1003` | UNSUPPORTED_RULE: target release or selected lowering shape has no current implementation; later-owned operators remain planned. Includes `zero_physical_source_not_admitted_on_target`: a MySQL statement whose only inputs are typed VALUES bodies |
| `PIE-B1004` | MISSING_EVIDENCE: required existing logical meaning, validated Decimal parameters or environmental declaration is absent |
| `PIE-B1005` | PREMISE_CONFLICT: the selected rules cannot use the supplied declarations coherently |
| `PIE-B1006` | UNFULFILLED_REQUIREMENT: applicable original negative/conflicting target evidence or mandatory enforcement remains unresolved |
| `PIE-B1007` | TARGET_RESOURCE: emitted structure, SQL bytes or public artifact exceeds a compiler or stricter declared target limit |
| `PIE-B1008` | ARTIFACT_INTEGRITY: actual SQL AST, final bytes, ranges, parameters, requirements or current input roots fail correspondence |

These additional codes are implemented by the private Phase66 Slice3 emission
pipeline and its `pietto.sql-emission.v1` serialization (`pietto.sql-emission.v2`
for a VERIFIED query with header parameters). They do not expand the
legacy emitter's `PIE-B1000` domain or implement later operator families.

## Runtime Diagnostics

These codes belong to the public execution alpha (`pietto.execution`, see
[Execution](../execution.md)). They are an alpha interface: a code may be split,
merged or retired with a note in the release notes, but is never reused for
another meaning. They appear only on that Python interface, never in a CLI or
JSON output. Each error also carries an unstable private `detail` word. Every
attempt outcome carries the alpha's two declarations:

- `Managed operator compliance: NOT_INDEPENDENTLY_VERIFIED`
- `Native all-definition lifetime exclusion: NOT_DEMONSTRATED / NOT CLAIMED`

| Code | Meaning |
|---|---|
| `PIE-R1001` | INPUT_MISSING: a required argument of `compile_query`, `export_bundle`, `load_bundle`, `execute()` or `save()` is `None`; no default is substituted |
| `PIE-R1002` | INPUT_INVALID: an input has the wrong type or an unsupported value, including SQL text instead of a compiled query, a `None` field of an access, premise or limits value, a Unix-socket or multi-host `host`, a premise that does not cover the query's sources, invalid limits or isolation, a `values` argument that is not a tuple, a `parameters` argument that is not `None` or a dict with string keys, a bundle payload that is not `bytes` or is empty or larger than 32 MiB, and a trust record that is not 64 lowercase hexadecimal characters |
| `PIE-R1003` | ROUTE_REFUSED: the route is not available in this alpha or does not fit the compiled query, including a MySQL compiled query that reads no physical relation |
| `PIE-R1004` | QUERY_NOT_EXECUTABLE: the verified query cannot be prepared for execution, including a bundle with a guard program or a refinement, values with which the query cannot be prepared, and an R2 call for a query with a typed VALUES body |
| `PIE-R1005` | CODE_IDENTITY: the installed Pietto or ANTLR runtime code changed since `compile_query` or `load_bundle`, `accepted_compatibility` names other code, or the code's identity cannot be established |
| `PIE-R1006` | VALUE_REFUSED: `execute(values=...)` does not give exactly one value per slot of `query.slots`, or a value is not of its slot's exact type and range (`Bool`: `bool`; `Int`: `int`, never `bool`, signed 64-bit; `Float`: finite `float`; `Text`: `str` that UTF-8 can encode, without NUL); `detail` is `BINDING_VALUE:<ordinal>:<tag>` with the 0-based slot ordinal for a value and `BINDING_SLOTS` for a wrong number of values, never the value. `execute(parameters=...)` with a missing or extra parameter name is `BINDING_PARAMETERS`, and a value outside its parameter's declared type or nullability is `BINDING_PARAMETER:<ordinal>:<tag>` with the 0-based declaration position, never the value; the same holds on every route and in `save`, `save_recoverable` and `relay_live` (`recover` judges restated parameters by the saved binding: `PIE-R1009`) |
| `PIE-R1007` | BUNDLE_CONTENT: the bytes given to `load_bundle` are not the bytes `expected_pin` names; Pietto never takes a pin from the bytes |
| `PIE-R1008` | BUNDLE_NOT_ACCEPTED: the bytes given to `load_bundle` are malformed, fail verification, or name a producer or compatibility other than `accepted_producer` and `accepted_compatibility` |
| `PIE-R1009` | WORKSPACE_REFUSED: a saved-result workspace is absent, invalid, unqualified or not v7, or a saved-result call restates `values` or `parameters` that differ from the saved binding (`BINDING_VECTOR`); in `recover` this includes any restatement that cannot bind at all once the query declares parameters or `parameters` names any, after the checks of its other inputs and the workspace's own |
| `PIE-R1010` | OPERATION_REFUSED: a caller operation identity is invalid or conflicts with a recorded step |
| `PIE-R1999` | REQUEST_UNCLASSIFIED: a request refusal that the alpha does not classify yet |
| `PIE-R2001` | DEPENDENCY_MISSING: a pinned dependency of the selected route (driver or PyArrow) is not installed; refused before connecting |
| `PIE-R2002` | DRIVER_PROFILE: the importable selected driver or PyArrow is not the pinned distribution, version and required implementation, is not that distribution's own files, or cannot be loaded; route-specific unsafe implementations are refused before they receive connection values |
| `PIE-R2003` | AMBIENT_ENVIRONMENT: a refused route environment variable is set; refused before connecting |
| `PIE-R2004` | CONNECTION_FAILED: the selected route's TCP connection, TLS profile or authentication failed. PostgreSQL requires TCP SCRAM-SHA-256, a password encrypted with `password_encryption='scram-sha-256'`, and a first matching `pg_hba.conf` `scram-sha-256` line; MySQL requires `caching_sha2_password`, TLS and a caller CA that verifies server identity. |
| `PIE-R2005` | TARGET_VERSION: the server is not the selected route's pinned version: PostgreSQL 18.6 or MySQL 8.4.12 |
| `PIE-R2006` | SESSION_CONTEXT: the session or its read-only transaction lacks the required settings |
| `PIE-R2007` | SOURCE_QUALIFICATION: a source relation does not qualify under the declared deployment premise |
| `PIE-R3001` | DEADLINE: the attempt's deadline expired |
| `PIE-R3002` | STATEMENT_TIMEOUT: the server canceled a statement at the 10 second statement limit |
| `PIE-R3003` | SERVER_ERROR: the server or the open connection reported an error, including a `scalar` read of more than one row (SQLSTATE 21000) |
| `PIE-R3004` | RESOURCE_LIMIT: a row or byte limit (`batch_rows`, `batch_bytes`, `max_rows` or `max_bytes`, including qualifying profile and catalog reads) would be exceeded; the whole batch is refused, never truncated; delivered batches stay valid and the attempt is never COMPLETE |
| `PIE-R3005` | RESULT_CHECK: returned metadata or values do not match the result contract |
| `PIE-R3006` | FINALIZATION: the attempt could not commit or clean up at its end. The failure keeps what the attempt recorded: for a failed `COMMIT` or `ROLLBACK`, phase `transaction` with its SQLSTATE and exception class; when the result was read to the end and `COMMIT` acknowledged but a cleanup step then failed, phase `finalization` (cause `ExecutionError`), with the failed step as the `PIE-R5001` entry |
| `PIE-R3007` | CONSUMER_ERROR: the caller's code raised inside the `with` block (outcome only) |
| `PIE-R3008` | INTERRUPTED: a `BaseException` that is not an `Exception` ended the attempt (outcome only) |
| `PIE-R3009` | CANCELLED: the caller cancelled the attempt before it completed |
| `PIE-R3999` | ATTEMPT_UNCLASSIFIED: an attempt failure that the alpha does not classify yet, including an exception that is not the driver's before a session exists |
| `PIE-R4001` | HANDLE_REUSED: a result handle was opened again; it runs one attempt once |
| `PIE-R4002` | BATCH_CLOSED: a closed result batch was exported |
| `PIE-R4003` | BATCH_TRANSFER: a result batch cannot be exported as requested |
| `PIE-R4004` | SCHEMA_EXPORT: `pa.schema(result)` cannot export the result schema because PyArrow is absent, is not the pinned `pyarrow` 26.0.0 distribution or cannot be loaded, or the schema cannot be built; the attempt is unchanged |
| `PIE-R5001` | CLEANUP_FAILED: a cleanup step failed (outcome only) |
| `PIE-R5002` | DROPPED_UNCLOSED: an open result handle was garbage-collected, or was still open at interpreter exit (a `ResourceWarning`, hidden by default) |
