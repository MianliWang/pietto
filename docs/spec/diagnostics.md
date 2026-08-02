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
| `PIE-S2005` | Implicit nullability |
| `PIE-S2006` | Semantic analysis recursion limit exceeded |
| `PIE-S2102` | Unknown field, including a schema-v2 minimal direct row-fact projection |
| `PIE-S2103` | Unknown function |
| `PIE-S2104` | Invalid built-in function arguments |
| `PIE-S2105` | Invalid operator operands |
| `PIE-S2202` | Known non-Bool expression in a predicate context |
| `PIE-S2301` | Unknown local or explicit-module relation |
| `PIE-S2302` | Local relation dependency cycle, including within one acyclic schema-v2 module |
| `PIE-S2303` | Invalid, missing, or untyped direct local/imported source shape |
| `PIE-S2304` | Computed projection without an explicit alias |
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

No runtime diagnostic codes are currently defined.
