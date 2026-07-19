# Phase 53 Slice 3 WindowSpec, Extension-compatible WindowFunctionIdentity, And AST Contract v1

## Status And Slice Identity

Phase 53 is `ACTIVE`; Slices 1 and 2 are `COMPLETED`; Slice 3 remains `UNSTARTED` throughout Gate 2. This slice is a bounded AST-preservation and fail-closed compiler foundation. It becomes `COMPLETED` only after a separately authorized Gate 3 publishes the exact Gate 2 result and observes the unique natural `CI / push / main`, attempt 1, succeed at the published `headSha`.

## Slice 2 Syntax And Lifecycle Authority

Slice 2 is the sole authority for the already accepted contextual grammar. The canonical syntax is an explicitly aliased direct call followed by an inline `window:` block containing nonempty `partition by:` and/or `order by:` clauses. Slice 3 consumes that CST without changing `grammar/Pietto.g4`, generated ANTLR files, `parser_api.ParseResult`, diagnostic inventory, or the Slice 2 malformed/deferred grammar boundary.

## Selected WindowExpr Architecture

The selected architecture is a dedicated immutable `WindowExpr(Expression)` with payload fields declared in the exact order `call`, `spec`, and `identity`. It keeps an ordinary `CallExpr` intact, keeps the alias on `SelectItem`, and makes the call/spec/identity invariant indivisible. Ordinary `CallExpr`, `SelectItem`, and `OrderItem` shapes remain unchanged; no select-item side channel or optional call fields are added.

## Exact WindowSpec Shape And Invariants

`WindowSpec(Node)` is `dataclass(frozen=True, slots=True, kw_only=True)` and carries its own `span`, `partition_by: tuple[Expression, ...]`, and `order_by: tuple[OrderItem, ...]`. Both collections must be exact tuples with correctly typed members, and they cannot both be empty. An absent clause is represented by an empty tuple. Source order, duplicates, and original expression objects are preserved without sorting, normalization, registry lookup, or semantic legality inference.

## Window-order Item Reuse And Ordinal Boundary

Window-local ordering reuses the existing pure-data `OrderItem`. Its direction remains the exact three-state value `None`, `"asc"`, or `"desc"`. `AstBuilder` owns the policy split: final relation `order by:` continues to reject integer ordinals, while an integer literal inside window-local `order by:` is preserved as an ordinary expression. `OrderItem` itself gains no owner, legality, or backend state.

## Private WindowFunctionIdentity Shape

`src/pietto/_window_identity.py` defines the private frozen/slots value object `WindowFunctionIdentity(namespace, name, role)` and the single `WindowFunctionRole.WINDOW_FUNCTION` member. `__all__` is the empty tuple, the module name is private, and neither the package root nor `ast_nodes` re-exports the identity class under a public-looking binding.

Construction requires an exact tuple namespace, nonempty exact-string namespace components, a nonempty exact-string name, and an exact `WindowFunctionRole` member. Invalid shapes fail deterministically. Construction never strips, lowercases, casefolds, sorts, or otherwise normalizes source text.

## Namespace Name Role And Case Semantics

An unqualified call such as `rank` produces `namespace=()` and `name="rank"`. A qualified call such as `analytics.rank` produces `namespace=("analytics",)` and `name="rank"`. A multi-part call such as `Org.Analytics.Rank` produces `namespace=("Org", "Analytics")` and `name="Rank"`. The final dotted part is always the name, preceding parts remain an ordered namespace tuple, and case is byte-preserved.

The role says only that the identity came from the syntactic `windowExpression` position. It does not claim builtin membership, extension installation, semantic existence, signature legality, result typing, nullability, mandatory ordering, portability, backend support, or public availability. Approved candidate names, unrelated names, `Window`, and `WINDOW` all use the same extraction.

## CST-to-AST Construction

`AstBuilder.visitSelectItem` routes a CST `windowExpression` to an ordinary expression slot while preserving the explicit alias on `SelectItem`. `visitWindowExpression` constructs the dotted callee, call arguments, call-only span, private identity, `WindowSpec`, and full `WindowExpr`. `visitWindowSpec` constructs source-ordered partition expressions and window-local order items, and `visitWindowPartitionItem` returns the contained expression.

Ordinary primary-expression calls share the call-construction helper and retain their existing AST behavior. Final-order and window-order items share the order-item helper with an explicit ordinal policy. No grammar, generated visitor, parser API, semantic catalog, project model, IR, SQL renderer, or public serializer participates in CST construction.

## Source-span And Location Preservation

All spans are 1-based and half-open. `WindowExpr.span` begins at the first callee token and ends after the final significant partition/order item. `CallExpr.span` ends after the closing parenthesis and excludes `window`. The callee covers only its dotted name, and argument spans remain ordinary expression spans.

`WindowSpec.span` begins at lowercase `window` and ends after its final significant item. A partition expression retains its exact expression span. An order item begins at its expression and ends after `asc`/`desc` when present; its nested expression excludes the direction. `SelectItem.span` begins at the alias and ends with the full window expression. Layout-only `NEWLINE`, `INDENT`, `DEDENT`, and blank lines do not expand logical ends.

## Parser Success And Compatibility

Every canonical Slice 2 window source now returns a non-`None` AST with no parser diagnostics and preserves alias, call, arguments, identity, window specification, order directions, item order, and spans. The temporary Slice 2 bridge message is retired from valid parse results. The existing malformed/deferred 12-case matrix remains rejected through existing parser diagnostics, and ordinary calls and final-order ordinal rejection remain unchanged.

Parser success establishes syntax preservation only. It does not establish that any window function is semantically supported or lowerable.

## Semantic Fail-closed Boundary

The only semantic change is an early `WindowExpr` branch in `semantic/expressions.py::_infer`, after the existing-fact cache and before ordinary expression dispatch. It emits existing `PIE-S2103` with the ordinary message `Unknown function: <full dotted name>` at the call-only span, returns the existing unknown value internally, and deliberately does not publish an expression value-type fact for the `WindowExpr`, its call, or its arguments.

Ordinary `check` therefore fails closed. If a caller bypasses semantic errors and invokes expression lowering, the existing missing-fact gate returns `PIE-I1000` with `Missing semantic fact required for IR lowering: expression value type`. No exception, Window IR, or SQL lowering is created.

## Project Parse-only Deferred Boundary

Private project readers treat `WindowExpr` as an unknown non-direct, non-aggregate expression without a semantic value-type fact. The existing row-expression adapter therefore returns a non-concrete missing-value result with empty dependency and lineage placeholders. Existing aggregate/grouped recognizers continue to accept only `CallExpr`, so no `WINDOW_RESULT`, window dependency, window lineage, or project semantic fact is created.

## IR SQL And Public Serialization Boundary

Slice 3 adds no Window IR node, builder/lowering branch beyond the existing missing-fact diagnostic, PostgreSQL rendering, private-MySQL rendering, fixture, golden, CLI behavior, CLI JSON v1 field, Semantic Metadata Artifact v1 field, Project JSON v2 field, or public SQL API. IR, SQL, CLI, serializer, package-root, parser API, package metadata, lockfile, and workflow surfaces remain byte-identical.

## Expression Walker And Exhaustiveness Closure

The semantic expression inferencer is the only consumer requiring a production edit. Existing aggregate recognizers, child walkers, let binding readers, satisfying readers, and project row/dependency walkers either see an opaque unsupported expression or return an existing unknown/deferred result. The derive-only assertion path is unreachable because grammar confines a window expression to an aliased select item. IR lowering stops at the missing semantic fact before exhaustive node lowering, and metadata walkers consume IR only.

This closure cannot be widened to add permissive fallback facts, `assert_never` escape hatches, generic call treatment, or silent successful drops.

## Positive AST Matrix

The focused contract covers order-only, partition-only, combined specs, multiple partition/order items, omitted/ascending/descending directions, zero and multiple arguments, a trailing comma, unqualified/qualified/multi-part identities, unrelated names, all eight planned candidate names, `Window`, `WINDOW`, multiple independent window outputs, surrounding ordinary projections, exact aliases, stable source order, exact spans, equality/hash/repr, constructor invariants, and window-local integer literals.

## Negative And No-behavior Matrix

The Slice 2 malformed/deferred 12-case subset remains rejected. Valid window syntax no longer produces the temporary bridge diagnostic. Three identity variants fail semantic analysis with exact `PIE-S2103`; no `WindowExpr` value-type fact is published; direct IR lowering yields existing `PIE-I1000`; and the project adapter remains non-concrete with no dependency or lineage placeholders.

Tests also lock the absence of a window catalog, generic compatibility binding, nullability formula, mandatory-order policy, WINDOW-stage fact, `WINDOW_RESULT`, Window IR, SQL, public serialization, new diagnostic code, dependency, version, workflow, fixture, or golden behavior.

## Grammar Generated And Parser API Immutability

`grammar/Pietto.g4`, all eight files in `src/pietto/generated`, `src/pietto/parser_api.py`, and `src/pietto/__init__.py` remain byte-identical to the Slice 2 publication baseline. Gate 2 does not run ANTLR or any generator. The generated inventory remains exactly eight.

## Reader Hash Inventory And Repository-state Closure

Gate 2 is restricted to exact `A3/M51/D0`: this specification, the private identity module, and the focused test are added; the Phase 53 plan, three existing production modules, and 47 exact compatibility readers are modified. The future committed inventory is 844 tracked files, 518 Python files, 230 Markdown files, 436 test modules, 4219 top-level test functions, 6376 collected items, 8 generated files, and 37 goldens.

Compiler, semantic, Phase 15 subset, frontend, parser-AST, raw-file, nested raw-SHA, inventory, selector, and repository-state readers terminate inside the exact allowlist. Gate 2 dirty state is exact and unstaged; clean synchronized `main` and clean detached/depth-one CI are also valid without fixed-base history requirements.

## Validation Depth-one CI And Gate 3 Publication

Gate 2 uses one write-mode Ruff format invocation over the exact 52 handwritten Python paths. Validation then runs lock check, repository-wide Ruff format check, Ruff lint, production Pyright, test Pyright, the exact 202-item focused selector, the exact dirty broad suite with `6193 passed, 183 deselected`, generated check, and `git diff --check`. The focused LF payload SHA-256 is `9d7668d9edbfb111f080e0ea99438df33266736bb98a3283f6c1a01bc27f6eb0`; the 183-node overlay LF payload SHA-256 is `15714b4cd20d2b0c17c9aa9a648bb1efefc311dbfb06dd33f3f1c2a1f9d11132`. The clean-CI projection is 6376 passes per Python job, generated inventory 8, goldens 37, package smoke PASS, and installed CLI `pietto 0.1.0`.

Gate 2 leaves `A3/M51/D0` unstaged and uncommitted. Only a separately authorized Gate 3 may stage the exact 54 paths, create one commit, perform one normal push to `main`, and observe the unique natural CI run. Gate 3 does not imply a tag, Release, PR, package upload, signing, attestation, or Slice 4 authorization.

## Deferred Ownership And Stop Conditions

Slice 4 owns generic compatibility foundations; Slice 5 owns symbolic nullability formulas; Slice 6 owns the private window semantic carrier, WINDOW stage, dependency, lineage, and result roles; Slices 7–14 own bounded function behavior; Slice 15 owns Window IR and independent backend lowering; Slice 16 owns completion audit and status lock. Phase 60 retains advanced windows and Phase 63 retains `QUALIFY` lowering.

STOP if AST preservation requires grammar/generated changes, a second formatter, semantic acceptance, project/IR/SQL/public-schema implementation, an allowlist escape, weakened hash/state equality, changed collection arithmetic, staging/publication, or any unresolved product decision. Parser AST success never authorizes later-slice behavior.
