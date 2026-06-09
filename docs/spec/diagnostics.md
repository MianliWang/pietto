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

## Semantic Diagnostics

| Code | Meaning |
|---|---|
| `PIE-S2001` | Duplicate name in one semantic scope or namespace |
| `PIE-S2002` | Unknown type |
| `PIE-S2003` | Type alias cycle |
| `PIE-S2005` | Implicit nullability |
| `PIE-S2102` | Unknown field |
| `PIE-S2103` | Unknown function |
| `PIE-S2104` | Invalid built-in function arguments |
| `PIE-S2202` | Known non-Bool expression in a predicate context |
| `PIE-S2301` | Unknown relation |
| `PIE-S2302` | Relation dependency cycle |
| `PIE-S2303` | Invalid, missing, or untyped source shape |
| `PIE-S2304` | Computed projection without an explicit alias |
| `PIE-S2305` | Duplicate projection output name |
| `PIE-S2306` | Invalid source connector or connector arguments |
| `PIE-S2401` | Constraint return type does not expand to `Bool` |
| `PIE-S2402` | Callable or field derive body type mismatch |
| `PIE-S2501` | Duplicate shape item name |
| `PIE-S2502` | Unknown unique or index target field |
| `PIE-S2503` | Duplicate unique or index target field |
| `PIE-S2504` | Derived field dependency cycle |

## IR Diagnostics

| Code | Meaning |
|---|---|
| `PIE-I1000` | Missing or inconsistent semantic fact required for declaration or expression IR lowering |

No backend or runtime diagnostic codes are currently defined.
