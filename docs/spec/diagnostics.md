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
| `PIE-S2001` | Duplicate name in one semantic scope or namespace, including a schema-v2 local type/source/relation bucket |
| `PIE-S2002` | Unknown local or explicit-module type reference |
| `PIE-S2003` | Local type alias cycle, including within one acyclic schema-v2 module |
| `PIE-S2004` | Invalid Decimal precision-scale type arguments |
| `PIE-S2005` | Implicit nullability; single-file severity follows `--check-mode` (else a header `mode`, else CHECKED): omitted in LOOSE, WARNING in CHECKED, ERROR in STRICT |
| `PIE-S2006` | Semantic analysis recursion limit exceeded |
| `PIE-S2102` | Unknown field, including a schema-v2 minimal direct row-fact projection |
| `PIE-S2103` | Unknown function |
| `PIE-S2104` | Invalid built-in function arguments |
| `PIE-S2105` | Invalid operator operands, including known comparison or `between` operands from different comparable type families; ERROR in LOOSE/CHECKED/STRICT. `Text` against `Date`, `Timestamp` or `UUID` is not checked yet (see `operator-comparison-matrix-contract-v1.md`). |
| `PIE-S2110` | Duplicate query-local named-window declaration |
| `PIE-S2111` | Dangling query-local named-window declaration or use reference |
| `PIE-S2112` | Query-local named-window dependency cycle |
| `PIE-S2113` | Named-window monotonic component conflict |
| `PIE-S2202` | Known non-Bool expression in a predicate context |
| `PIE-S2301` | Unknown local or explicit-module relation |
| `PIE-S2302` | Local relation dependency cycle, including within one acyclic schema-v2 module |
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
| `PIE-S2703` | Explicit-module import dependency cycle |
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
| `PIE-B1003` | UNSUPPORTED_RULE: target release or selected lowering shape has no current implementation; later-owned operators remain planned |
| `PIE-B1004` | MISSING_EVIDENCE: required existing logical meaning, validated Decimal parameters or environmental declaration is absent |
| `PIE-B1005` | PREMISE_CONFLICT: the selected rules cannot use the supplied declarations coherently |
| `PIE-B1006` | UNFULFILLED_REQUIREMENT: applicable original negative/conflicting target evidence or mandatory enforcement remains unresolved |
| `PIE-B1007` | TARGET_RESOURCE: emitted structure, SQL bytes or public artifact exceeds a compiler or stricter declared target limit |
| `PIE-B1008` | ARTIFACT_INTEGRITY: actual SQL AST, final bytes, ranges, parameters, requirements or current input roots fail correspondence |

These additional codes are implemented by the private Phase66 Slice3 emission
pipeline and its `pietto.sql-emission.v1` serialization. They do not expand the
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
| `PIE-R1001` | INPUT_MISSING: a required argument of `compile_query`, `export_bundle`, `load_bundle` or `execute()` is `None`; no default is substituted |
| `PIE-R1002` | INPUT_INVALID: an input has the wrong type or an unsupported value, including SQL text instead of a compiled query, a `None` field of an access, premise or limits value, a Unix-socket or multi-host `host`, a premise that does not cover the query's sources or omits `pg_catalog`, invalid limits or isolation, a `values` argument that is not a tuple, a bundle payload that is not `bytes` or is empty or larger than 32 MiB, and a trust record that is not 64 lowercase hexadecimal characters |
| `PIE-R1003` | ROUTE_REFUSED: the route is not available in this alpha or does not fit the compiled query |
| `PIE-R1004` | QUERY_NOT_EXECUTABLE: the verified query cannot be prepared for execution, including a bundle with a guard program or a refinement and values with which the query cannot be prepared |
| `PIE-R1005` | CODE_IDENTITY: the installed Pietto or ANTLR runtime code changed since `compile_query` or `load_bundle`, `accepted_compatibility` names other code, or the code's identity cannot be established |
| `PIE-R1006` | VALUE_REFUSED: `execute(values=...)` does not give exactly one value per slot of `query.slots`, or a value is not of its slot's exact type and range (`Bool`: `bool`; `Int`: `int`, never `bool`, signed 64-bit; `Float`: finite `float`; `Text`: `str` that UTF-8 can encode, without NUL); `detail` is `BINDING_VALUE:<ordinal>:<tag>` with the 0-based slot ordinal for a value and `BINDING_SLOTS` for a wrong number of values, never the value |
| `PIE-R1007` | BUNDLE_CONTENT: the bytes given to `load_bundle` are not the bytes `expected_pin` names; Pietto never takes a pin from the bytes |
| `PIE-R1008` | BUNDLE_NOT_ACCEPTED: the bytes given to `load_bundle` are malformed, fail verification, or name a producer or compatibility other than `accepted_producer` and `accepted_compatibility` |
| `PIE-R1999` | REQUEST_UNCLASSIFIED: a request refusal that the alpha does not classify yet |
| `PIE-R2001` | DEPENDENCY_MISSING: a pinned dependency of the route (driver or PyArrow) is not installed; refused before connecting |
| `PIE-R2002` | DRIVER_PROFILE: the importable driver is not the pinned distribution, version or binary implementation (`PSYCOPG_IMPL` other than `binary` is refused before the import), or the driver or PyArrow cannot be loaded |
| `PIE-R2003` | AMBIENT_ENVIRONMENT: a refused environment variable (`PG*`, `SSLKEYLOGFILE`, `OPENSSL_CONF`, `OPENSSL_MODULES`) is set; refused before connecting |
| `PIE-R2004` | CONNECTION_FAILED: the driver reported that the TCP connection or its SCRAM-SHA-256 authentication failed, with channel binding over TLS; other authentication methods are refused before the password is sent. `sslmode` `require` needs a server with TLS, reached directly, whose certificate is signed with RSA or ECDSA, and the first `pg_hba.conf` line that matches must be a `scram-sha-256` line: `hostssl` for remote clients, `host` only for 127.0.0.1 and ::1; see the server setup in [Execution](../execution.md) |
| `PIE-R2005` | TARGET_VERSION: the server is not PostgreSQL 18.6 |
| `PIE-R2006` | SESSION_CONTEXT: the session or its read-only transaction lacks the required settings |
| `PIE-R2007` | SOURCE_QUALIFICATION: a source relation does not qualify under the declared deployment premise |
| `PIE-R3001` | DEADLINE: the attempt's deadline expired |
| `PIE-R3002` | STATEMENT_TIMEOUT: the server canceled a statement at the 10 second statement limit |
| `PIE-R3003` | SERVER_ERROR: the server or the open connection reported an error |
| `PIE-R3004` | RESOURCE_LIMIT: a row or byte limit would be exceeded; the whole batch is refused, never truncated |
| `PIE-R3005` | RESULT_CHECK: returned metadata or values do not match the result contract |
| `PIE-R3006` | FINALIZATION: the attempt could not commit or clean up at its end. The failure keeps what the attempt recorded: for a failed `COMMIT` or `ROLLBACK`, phase `transaction` with its SQLSTATE and exception class; when the result was read to the end and `COMMIT` acknowledged but a cleanup step then failed, phase `finalization` (cause `ExecutionError`), with the failed step as the `PIE-R5001` entry |
| `PIE-R3007` | CONSUMER_ERROR: the caller's code raised inside the `with` block (outcome only) |
| `PIE-R3008` | INTERRUPTED: a `BaseException` that is not an `Exception` ended the attempt (outcome only) |
| `PIE-R3999` | ATTEMPT_UNCLASSIFIED: an attempt failure that the alpha does not classify yet, including an exception that is not the driver's before a session exists |
| `PIE-R4001` | HANDLE_REUSED: a result handle was opened again; it runs one attempt once |
| `PIE-R4002` | BATCH_CLOSED: a closed result batch was exported |
| `PIE-R4003` | BATCH_TRANSFER: a result batch cannot be exported as requested |
| `PIE-R5001` | CLEANUP_FAILED: a cleanup step failed (outcome only) |
| `PIE-R5002` | DROPPED_UNCLOSED: an open result handle was garbage-collected, or was still open at interpreter exit (a `ResourceWarning`, hidden by default) |
