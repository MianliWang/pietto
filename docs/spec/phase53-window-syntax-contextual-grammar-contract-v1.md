# Phase 53 Slice 2 Pietto-native Window Syntax And Contextual Grammar Contract v1

## Status And Slice Identity

Phase 52 is `COMPLETED`. Phase 53 is `ACTIVE`. Slice 1 is `COMPLETED`, while Slice 2 remains `UNSTARTED` throughout Gate 2. This contract is the bounded grammar and parser-recognition authority for Phase 53 Slice 2. A separately authorized Gate 3, exact publication, and successful natural CI are required before Slice 2 becomes `COMPLETED`.

The slice title is **Pietto-native Window Syntax And Contextual Grammar Contract**. Gate 2 leaves its exact `A2/M67/D0` result unstaged and uncommitted. It does not authorize Slice 3 or any later compiler behavior.

## Approved Product Authority

Slice 2 owns:

- grammar and lexer recognition;
- exact lowercase global `window` reservation;
- contextual `partition` compatibility;
- inline unnamed window syntax;
- generated ANTLR output;
- raw CST, identifier-compatibility, and deterministic parser-diagnostic tests;
- a minimal fail-closed `AstBuilder` bridge;
- plan/spec and compatibility-reader persistence.

Slice 2 does not own a `WindowSpec` AST carrier, `WindowFunctionIdentity`, semantic catalogs, generic binding, symbolic nullability, WINDOW-stage facts, project result roles, dependency or lineage, IR, SQL, public schema, runtime, database behavior, package metadata, workflow, release, or Rust behavior.

## Exact Canonical Syntax

Candidate B is canonical:

```pietto
query ranked:
    from rows
    select:
        rn = row_number() window:
            partition by:
                account_id
                region
            order by:
                observed_at desc
                sequence_id
```

The exact grammar shape is:

```antlr
selectItem
    : identifier ASSIGN windowExpression
    | identifier ASSIGN expression NEWLINE
    | expression NEWLINE
    ;

windowExpression
    : dottedName callSuffix windowSpec
    ;

windowSpec
    : WINDOW COLON NEWLINE NEWLINE* INDENT windowSpecBody DEDENT
    ;

windowSpecBody
    : NEWLINE* partitionByClause NEWLINE* orderByClause? NEWLINE*
    | NEWLINE* orderByClause NEWLINE*
    ;

partitionByClause
    : PARTITION BY COLON NEWLINE NEWLINE* INDENT windowPartitionBody DEDENT
    ;

windowPartitionBody
    : NEWLINE* windowPartitionItem (windowPartitionItem | NEWLINE)*
    ;

windowPartitionItem
    : expression NEWLINE
    ;
```

## Introducer And Case Policy

The exact introducer is lowercase `window:`. Add `WINDOW: 'window';` before `IDENTIFIER`; do not return `WINDOW` through `identifier` or `namePart`. Lowercase `window` is therefore globally reserved in all identifier positions.

The lexer remains case-sensitive. `Window` and `WINDOW` continue to tokenize as `IDENTIFIER` and remain accepted identifiers. This contract adds no case-folding, alias spelling, alternate introducer, or contextual text predicate.

## Clause Shape And Ordering

A window spec contains either:

- one optional nonempty `partition by:` block followed by an optional nonempty `order by:` block; or
- one nonempty `order by:` block.

Partition-only syntax is recognized at grammar level because per-function order requirements belong to later semantic slices. If both subclauses occur, partition must precede order. Each subclause occurs at most once. Blank lines are accepted only where the existing block grammar permits them. Empty specs, empty subclauses, duplicate clauses, and order-before-partition reject deterministically.

Partition items are generic expressions, one per line. Window-local order items reuse the existing `orderItem` rule: one generic expression followed by optional `asc` or `desc` and a newline.

## Function Call Alias And Suffix Binding

The suffix binds exactly one direct top-level `dottedName callSuffix`. A selected window expression must use the existing explicit alias form:

```pietto
alias = function(arguments) window:
    order by:
        key
```

The suffix does not bind an unaliased call, literal, parenthesized expression, binary expression, nested call result, or another window suffix. Qualified direct calls and ordinary argument lists, including the existing trailing-comma form, remain syntactically available. Function identity and argument legality are not grammar decisions.

## Grammar And Semantic Ownership

Grammar owns tokenization, colon/indentation structure, nonempty blocks, fixed subclause order, direct-call suffix binding, one suffix, and explicit aliasing.

Later semantic slices own the eight-function catalog, arity and optional-argument rules, function-specific order requirements, partition/order operand binding, visibility and nesting, result type, nullability, WINDOW-stage legality, grouped-result inputs, project facts, IR, SQL lowering, and diagnostics beyond parser recognition. Grammar acceptance is not semantic or backend support.

## AST Fail-closed Bridge

Slice 2 adds no AST carrier. Before ordinary expression handling, `AstBuilder.visitSelectItem` detects `ctx.windowExpression()`, obtains the exact token from `ctx.windowExpression().windowSpec().WINDOW().getSymbol()`, and raises existing `AstBuildError` with this exact message:

```text
Window syntax is recognized, but WindowSpec AST preservation starts in Phase 53 Slice 3.
```

The error uses the token line and user-facing `column + 1`. The public parser returns `ast=None` and exactly one `PIE-P1000` ERROR for a grammar-valid window expression. No recognized spec may be silently discarded or represented as an ordinary `CallExpr`. `src/pietto/parser_api.py` and `src/pietto/ast_nodes.py` remain byte-identical.

## Global Identifier Compatibility

Lowercase `window` is rejected in every audited identifier position: query, source, and table names; `from` relation; shape field; selected alias; let binding; derive parameter; dotted-name part; function name; relationship name; and endpoint local name.

The repository contains no tracked positive Pietto fixture or golden that requires lowercase `window` as an identifier. The historical `window recent` parser-negative sample remains negative and selected. `Window` and `WINDOW` remain accepted identifiers.

## Contextual Keyword Compatibility

Add `PARTITION: 'partition';` before `IDENTIFIER`, and add `PARTITION` to `identifier`. Do not add it separately to `namePart`, because `namePart` already accepts `identifier`. Lowercase `partition` therefore remains usable in all ordinary identifier paths while also introducing `partition by:` inside a window spec.

`over` remains an ordinary `IDENTIFIER`. Existing `BY`, `ASC`, and `DESC` token-and-identifier compatibility remains unchanged. The eight approved names—`row_number`, `rank`, `dense_rank`, `percent_rank`, `cume_dist`, `ntile`, `lag`, and `lead`—remain ordinary identifiers. Frame vocabulary such as `rows`, `range`, `groups`, `preceding`, `following`, `unbounded`, and `current` remains contextual and unreserved.

## Positive Grammar Matrix

The exact nine raw-parser/CST cases are:

1. order-only with omitted direction;
2. one partition item and one ascending order item;
3. multiple partition items and mixed order directions;
4. permitted blank lines within nested blocks;
5. a qualified direct call;
6. call arguments with a trailing comma;
7. an unrelated ordinary function name;
8. two independent window outputs;
9. surrounding ordinary select items with stable window-token locations.

Separate parameter matrices cover four generic partition/order expression shapes, both case variants, both contextual identifier spellings, and all eight approved function identities. These cases prove grammar/CST or ordinary identifier behavior only.

## Negative Grammar Matrix

The exact twenty malformed or deferred raw-parser cases are:

1. missing `window` colon;
2. missing outer window indentation;
3. inconsistent nested indentation;
4. empty window spec;
5. empty partition block;
6. empty order block;
7. duplicate partition blocks;
8. duplicate order blocks;
9. partition after order;
10. unknown window subclause;
11. named-window reference;
12. named-window declaration;
13. frame syntax;
14. `nulls first`;
15. `nulls last`;
16. `qualify`;
17. multiple window suffixes;
18. suffix on a forbidden non-call shape;
19. malformed order expression;
20. malformed partition expression.

The compatibility matrix separately rejects lowercase `window` in twelve identifier positions. Four public-parser cases prove fail-closed AST behavior rather than grammar rejection.

## Diagnostic And Location Contract

For canonical path `slice2-window.pietto`, the first `window` token is at line `4`, column `27`. The parser API returns `ast=None` and exactly one diagnostic:

```text
code=PIE-P1000
severity=ERROR
message=Window syntax is recognized, but WindowSpec AST preservation starts in Phase 53 Slice 3.
path=slice2-window.pietto
line=4
column=27
```

Malformed grammar and indentation cases remain deterministic source errors with stable offending locations. Slice 2 adds no diagnostic code and changes no public diagnostic schema.

## Generated Source Contract

The tracked generated inventory remains exactly eight files. One invocation of the tracked ANTLR 4.13.2 jar through `make generate-parser` may mutate exactly:

1. `src/pietto/generated/Pietto.interp`
2. `src/pietto/generated/Pietto.tokens`
3. `src/pietto/generated/PiettoLexer.interp`
4. `src/pietto/generated/PiettoLexer.py`
5. `src/pietto/generated/PiettoLexer.tokens`
6. `src/pietto/generated/PiettoParser.py`
7. `src/pietto/generated/PiettoVisitor.py`

`src/pietto/generated/__init__.py` remains empty and byte-identical. Generated files are never edited or formatted manually. A second generator invocation requires separate recovery authority.

## Reader Hash And Repository State Closure

The exact Gate 2 repository scope is `A2/M67/D0`. Every grammar SHA reader, generated aggregate reader, individual generated SHA map, final `AstBuilder` SHA reader, compiler boundary digest reader, nested raw-SHA edge, inventory reader, and modified repository-state reader terminates inside M67. Equality checks remain exact; historical hashes remain historical only where explicitly intended.

Gate 2 requires 67 tracked modified paths, exactly two authorized nonignored untracked paths, no deletion or rename, and an empty index at base `d52a4a80aee1a1708d8fd480f63aa450a1c25eff`. Modified state readers also accept a future clean synchronized `main` or clean detached depth-one checkout with optional refs, require every existing ref to equal HEAD, and do not require `HEAD^`, network, or external evidence.

## Validation CI And Publication Boundary

Gate 2 validation is fixed and ordered: lock check; repository Ruff format check; Ruff lint; production Pyright; test Pyright; the exact 77-operand focused selector with `146 passed`; the exact 185-node broad overlay with `6121 passed, 185 deselected` from 6306 collected items; generated check; and empty `git diff --check`.

Future committed inventory is 841 tracked files, 516 Python files, 229 Markdown files, 435 test modules, 4194 top-level test functions, 6306 collected items, 8 generated files, and 37 goldens. Natural clean CI must return all deselected readers and project `6306 passed` on Python 3.12 and 3.13.

Gate 2 does not stage or publish. A separately authorized Gate 3 stages exactly 69 paths, creates one commit with subject `Add Phase 53 Pietto-native window syntax contract`, performs one normal push to `main`, and observes the unique natural `CI / push / main`, attempt 1, at the exact new `headSha`. Gate 3 creates no tag, Release, or PR.

## Public Behavior And Deferred Scope

The public parser recognizes the grammar and then fails closed before AST preservation. This is intentional Slice 2 behavior and is not a semantic, IR, SQL, CLI-output, or runtime implementation claim.

No AST carrier, semantic catalog, generic binder, nullability evaluator, WINDOW stage, project result role, dependency/lineage, IR, PostgreSQL/private-MySQL lowering, public schema, package, workflow, release, or Rust surface changes. Named windows, frames, aggregate-as-window, same-select dependencies, nested window calls, window use in filters/grouping/aggregate arguments/`satisfying`, and `QUALIFY` remain deferred to their explicit owners.

## Stop Conditions

STOP if the exact syntax cannot be recognized without silent AST loss; a `WindowSpec` carrier or later-slice behavior becomes necessary; lowercase `window` cannot remain globally reserved; contextual compatibility fails; generated output differs from the seven-path set; generated `__init__.py`, parser API, or AST nodes change; a hash or inventory edge escapes M67; exact `A2/M67/D0`, 16 functions/70 items, selector identities, validation counts, or clean depth-one behavior drift; a second generator or formatter is needed; the index becomes nonempty; or any semantic/project/IR/SQL/public/package/workflow/runtime/release/Rust surface must change.
