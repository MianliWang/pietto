# Phase 53 Window IR, Dual-backend Lowering, And Window-function Facts Contract v1

## Status And Ownership

This contract is the sole behavior authority for Phase 53 Slice 15. It closes
the bounded compiler seam from the completed window semantic model to private
Window IR and independently evidenced PostgreSQL and private-MySQL SQL. It also
adds one private descriptive `WINDOW_FUNCTION` capability domain.

The published lifecycle after Slice 15 is:

```text
Phase 53 = ACTIVE
Slices 1 through 15 = COMPLETED
Slice 16 = UNSTARTED
```

Slice 16 exclusively owns the Phase 53 completion audit and status lock. Phase
60 retains frames and advanced window behavior, Phase 63 retains `QUALIFY`,
Phase 69 retains extension-specific and additional-dialect lowering, and Phase
70 retains broader public schema, lineage, and attribution expansion.

## Stage And Authority Contract

The established stage order remains:

```text
ROW / let / where
    -> GROUP / aggregate / satisfying
    -> WINDOW
    -> final order
    -> limit
```

Slice 15 consumes facts already published by semantic analysis. In particular,
`SemanticModel.expression_value_types` already contains the result type for
every validated `WindowExpr` and the required operand types. Lowering replaces
only the prior explicit fail-closed `WindowExpr` guard. It does not rerun
semantic analysis, reconstruct a signature or nullability formula, infer
legality from a capability fact, or add a semantic-model persistence map.

An absent result or operand type, an unrecognized identity, or any malformed
validated-to-IR boundary continues to fail closed with the existing
`PIE-I1000` missing-semantic-fact behavior. Generic `CallIR` is not widened.

## Identity, Result, And Argument Contract

The exact builtin identity order is:

1. `row_number`;
2. `rank`;
3. `dense_rank`;
4. `percent_rank`;
5. `cume_dist`;
6. `ntile`;
7. `lag`;
8. `lead`.

Every builtin identity reaches IR with `namespace=()`, its exact
source-preserved lowercase name, and role
`WindowFunctionRoleIR.WINDOW_FUNCTION`. No normalization, case folding,
aliasing, or namespace synthesis is permitted. Any other identity, including a
future extension identity, remains non-lowerable.

Slice 15 copies, rather than recomputes, the completed result facts:

- `row_number`, `rank`, `dense_rank`, and `ntile` are non-null `Int`;
- `percent_rank` and `cume_dist` are non-null `Float`;
- `lag` and `lead` preserve the exact bound generic type and completed
  nullability formula result.

The exact argument shapes remain zero arguments for `row_number`, `rank`,
`dense_rank`, `percent_rank`, and `cume_dist`; one positive exact `Int`
literal for `ntile`; and one through three completed navigation arguments for
`lag` and `lead`. Source order is preserved. Omitted offset and default
arguments remain omitted: lowering synthesizes neither literal `1` nor
`NULL`.

Partition keys remain a source-ordered, duplicate-preserving tuple of zero or
more expressions. Window-local order remains a source-ordered,
duplicate-preserving, non-empty tuple. Omitted, `asc`, and `desc` source
directions remain distinguishable even though omitted direction has effective
`ASC` lowering.

## Private Window IR Contract

`src/pietto/ir/model.py` owns exactly one private expression node, three
private sibling carriers, and one role enum:

```python
class WindowFunctionRoleIR(StrEnum):
    WINDOW_FUNCTION = "window_function"

@dataclass(frozen=True, slots=True)
class WindowFunctionIdentityIR:
    namespace: tuple[str, ...]
    name: str
    role: WindowFunctionRoleIR

@dataclass(frozen=True, slots=True)
class WindowOrderItemIR:
    expression: ExpressionIR
    direction: OrderDirectionIR
    direction_is_explicit: bool
    span: SourceSpan

@dataclass(frozen=True, slots=True)
class WindowSpecIR:
    partition_by: tuple[ExpressionIR, ...]
    order_by: tuple[WindowOrderItemIR, ...]
    span: SourceSpan

@dataclass(frozen=True, slots=True)
class WindowCallIR(ExpressionIR):
    identity: WindowFunctionIdentityIR
    arguments: tuple[ExpressionIR, ...]
    spec: WindowSpecIR
```

`WindowCallIR` inherits `span` and `value_type` as its first two fields,
matching existing expression-node field order. `WindowOrderItemIR` is not
relation-level `OrderItemIR`: it additionally preserves whether direction
was explicit. Partition items are ordinary `ExpressionIR` values; no extra
partition wrapper is introduced.

All five types are frozen, slotted, value-based, hashable, and deterministically
ordered. Their constructors fail closed:

- namespace is an exact tuple whose members, when present, are nonblank exact
  strings;
- name is a nonblank exact string and role is exactly
  `WindowFunctionRoleIR.WINDOW_FUNCTION`;
- argument, partition, and order collections are exact tuples;
- order is non-empty and every order item uses exact
  `OrderDirectionIR.ASC` or `OrderDirectionIR.DESC`;
- `direction_is_explicit` is an exact `bool`; `False` requires effective
  `ASC`;
- builtin arity is validated without synthesizing omitted arguments;
- every nested expression and span has the exact expected carrier type.

The carriers use no Python object identity, callback registry, ambient
discovery, or unordered set/mapping traversal. They are intentionally suitable
for deterministic differential testing and a later separately authorized Rust
boundary.

The carriers are deliberately absent from `src/pietto/ir/__init__.py`.
There is no new IR serializer, public Python export, CLI or JSON projection, or
metadata schema.

## Lowering And Grouped-result Contract

The lowering path is exact `WindowExpr` to `WindowCallIR`. Identity,
arguments, partition keys, local-order expressions, direction,
omitted-versus-explicit direction, spans, and the published result type are
preserved. Multiple window outputs lower independently in selected source
order.

Ungrouped direct fields, bounded lets, and immediate-upstream window fields use
the established ordinary row-expression lowering rules. A bare unique window
output used by final relation ordering lowers as the selected output alias, not
as a repeated window expression.

For a grouped relation, admitted `GROUP_KEY` and `AGGREGATE_RESULT` window
operands lower to their underlying selected expressions. The compiler must not
render a SELECT alias inside `OVER (...)`, rerun aggregate semantics, invent
aggregate-as-window behavior, or add a subquery or CTE. The legal same-level
shape is:

```sql
SELECT
    "k" AS "k",
    SUM("amount") AS "total",
    RANK() OVER (ORDER BY SUM("amount") DESC) AS "r"
FROM "t"
GROUP BY
    "k"
```

Grouped relation validation admits `WindowCallIR` as a selected shape while
still requiring at least one aggregate and rejecting every other unsupported
shape. Grouped final order admits a selected window-output alias alongside the
already supported selected group-key and aggregate-result outputs.

## PostgreSQL Rendering Contract

PostgreSQL renders the bounded form:

```text
FUNCTION(arguments) OVER (PARTITION BY keys ORDER BY items)
```

The exact SQL function spellings are `ROW_NUMBER`, `RANK`, `DENSE_RANK`,
`PERCENT_RANK`, `CUME_DIST`, `NTILE`, `LAG`, and `LEAD`. Zero-argument
calls retain `()`. Arguments, partition keys, and local-order items preserve
source order and duplicates and use `, ` as the separator. `PARTITION BY`
is omitted when its tuple is empty. `ORDER BY` is always present. Every
effective direction renders explicitly as `ASC` or `DESC`.

The complete window expression is one line. Existing PostgreSQL identifier
quoting, escaping, projection indentation, alias rendering, and relation-level
layout remain authoritative. Final relation order over a window result renders
the quoted output alias.

Malformed or unsupported Window IR raises `ValueError` within the renderer
and becomes the existing `PIE-B1000` diagnostic at the definition span
through `emit_postgres_sql`. No new diagnostic is introduced.

## Private-MySQL Rendering Contract

Private MySQL independently renders the same bounded function, `OVER`,
`PARTITION BY`, `ORDER BY`, argument, omission, direction, and source-order
semantics. Its bytes are independently evidenced and are not inferred from the
PostgreSQL result.

MySQL identifiers use the established backtick quoting, backtick doubling,
NUL rejection, UTF-8 validation, 64-character identifier limit, and
256-character select-alias limit. Malformed or unsupported Window IR raises
`MySqlRenderError` and becomes existing `PIE-B1000` through
`emit_mysql_sql`.

The private entrypoint remains private. `emit_mysql_sql` is not added to
`pietto.sql.__all__`, and `src/pietto/sql/__init__.py` remains unchanged.

## Descriptive WINDOW_FUNCTION Capability Facts

`CapabilityDomain` gains exactly
`WINDOW_FUNCTION = "window_function"`. The new private module
`src/pietto/semantic/capability_windows.py` has `__all__ = ()`, owns the
complete ordered fact tuple, and provides one private
`window_lookup_inputs(key)` entrypoint matching the established
domain-local lookup pattern.

The inventory contains exactly 24 supported facts in deterministic identity
order:

- eight signature facts, one for each exact builtin identity;
- eight PostgreSQL lowering facts, one for each identity;
- eight private-MySQL lowering facts, one for each identity.

Every key uses `CapabilityDomain.WINDOW_FUNCTION`, the exact lowercase
identity name, operation `signature` or `lowering`, an ordered exact
operand tuple, and context `window_signature` or `window_lowering`.
Signature keys use `dialect=None`; lowering keys use `postgresql` or
`mysql`. Extension is always `None`. Backend is evidence-level only and is
`postgresql` or `private-mysql`.

Signature evidence keeps identity/catalog existence and semantic procedure
legality distinct. Lowering evidence separately establishes IR, PostgreSQL, and
private-MySQL support. The lookup preserves exact-key `Found`, complete-domain
`Absent`, incomplete-domain `Unknown`, and contradictory same-key
`Conflict`. Unsupported subjects in the complete builtin domain are absent;
extension-specific or otherwise incomplete claims remain unknown.

Facts are immutable, descriptive evidence only. `Found` plus `SUPPORTED`
does not authorize parsing, semantic acceptance, IR construction, SQL
rendering, extension installation, or public exposure.

## Diagnostics, Compatibility, And Public Boundaries

Slice 15 changes no diagnostic code or message. Renderer-shape failure is
`PIE-B1000`; unrelated missing semantic facts stay `PIE-I1000`. Established
semantic diagnostics and their first-error order remain unchanged.

There is no grammar, generated, AST, parser, semantic-acceptance, semantic
row-schema, private-project persistence, graph, lineage, CLI, CLI JSON v1,
Project JSON v2, Semantic Metadata Artifact v1, public Python API, runtime,
database, schema-introspection, fixture, golden, example, script, workflow,
package metadata, dependency, lockfile, version, tag, Release, publish, upload,
signing, attestation, provenance, or SBOM change.

Package and installed CLI version remain `0.1.0`. Generated inventory remains
8 and golden inventory remains 37: 32 SQL and 5 JSON. Exact backend SQL evidence
is inline test evidence and does not create or regenerate a golden.

## Unsupported And Future-owned Boundaries

Frames, `ROWS`, `RANGE`, `GROUPS`, named windows, window inheritance,
aggregate-as-window behavior, `first_value`, `last_value`, `nth_value`,
nested windows, same-select window dependencies, `QUALIFY`, extension-specific
lowering, third or additional dialects, runtime/database execution, project
IR/SQL, relationship, JOIN, grain/fanout behavior, public window metadata,
implicit coercion, promotion, LUB/common-supertype search, temporal conversion,
Decimal precision fusion, and native mapping remain unsupported.

Windows remain forbidden in `where`, group keys, aggregate arguments,
`satisfying`, and every other previously forbidden context. A namespace-ready
IR identity does not imply an extension catalog or extension lowering. A
frame-free `WindowSpecIR` does not implement a frame. Dual-backend evidence
does not authorize another backend.

## Lifecycle And Gate Boundary

Gate 2 entered with frozen `A3/M71/D0` authority. Mechanical repair rounds 4
and 6 proved two additional tracked inventory/topology readers, making final
scope exactly `A3/M73/D0`. It performs exactly one write-mode Ruff invocation over
the frozen 72-path handwritten Python manifest; the post-formatter reader
repair is formatting-neutral and receives read-only Ruff checks only. Gate 2
keeps the index empty and does not stage,
commit, push, mutate CI, tag, release, publish a package, upload, sign, or
attest.

The authorized publication path uses the exact branch
`phase53/slice15-window-ir-dual-backend-lowering`, exact commit and PR title
`Add Phase 53 window IR and dual-backend lowering`, unique natural exact-head
PR CI, squash merge, and unique natural exact-head main CI. No direct-main
push, amend, rebase, force-push, or manual CI mutation is permitted.

After that publication succeeds, Slice 15 is `COMPLETED`, Phase 53 remains
`ACTIVE`, and Slice 16 remains `UNSTARTED`. The sole next authorization is
`SLICE16_GATE0_GATE1`; no Slice 16 implementation is started here.
