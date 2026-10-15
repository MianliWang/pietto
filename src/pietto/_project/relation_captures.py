"""Capture lines of relation lets: authored structure and its refusals.

Phase70 S10 admits, in EXPLICIT_MODULES projects only, a relation let whose
body starts with ``capture NAME`` lines (D70.03, owner rule of 2026-10-14). Each
line names one FROM or JOIN row input of the declaration body, whose current
row the let reads through qualified names ``NAME.field`` only. The let is
read once, by ``exists``, ``scalar``, ``in`` or ``not in`` written in that
declaration body (D70.04; Phase70 S10, S14) or, LATERAL
(Phase70 S12, S13), as the target of a CROSS, INNER or LEFT JOIN of that body
whose capture lines name inputs left of it (D70.03); its body is a FROM
relation with an optional WHERE and an ungrouped, window-free SELECT; a let
read LATERAL or by ``scalar``, ``in`` or ``not in`` may end in an ungrouped
ORDER BY that reads no captured field, and LIMIT (MySQL emission refuses the
latter readers, D70.05).

Everything here reads authored syntax only and runs before semantic analysis,
like the query-header refusals: a refused capture stops that run's semantic
readers, so they never see an invalid capture structure. The one semantic
refusal, a captured field that its outer input does not have, is reported by
the semantic layer with the code kept here.
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import cast

from pietto import _syntax_admission as gate
from pietto.ast_nodes import (
    AuthoredJoinKind,
    BlockRelationDef,
    CapturedFieldExpr,
    FromClause,
    JoinClause,
    LetRelationDef,
    Node,
    RelationExistsExpr,
    RelationMembershipExpr,
    RelationScalarExpr,
    Script,
    SelectBody,
    SetOperand,
    SetOperationBody,
    Span,
    TableFunctionFromClause,
    ValuesBody,
    WindowExpr,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import contains_semantic_aggregate

__all__: tuple[str, ...] = ()

# Phase70 S10 codes.
CAPTURE_DIAGNOSTICS: dict[str, str] = {
    "outer_input": "PIE-S2366",
    "duplicate": "PIE-S2367",
    "self_correlation": "PIE-S2368",
    "field": "PIE-S2369",
    "unsupported": "PIE-S2370",
}
# Phase70 S12/S13 codes (LATERAL JOIN of a let with capture lines).
LATERAL_DIAGNOSTICS: dict[str, str] = {
    "prefix": "PIE-S2371",
    "kind": "PIE-S2372",
}
# JOIN kinds whose target fields never reach the joined row.
_FILTERING_JOINS = frozenset({AuthoredJoinKind.SEMI, AuthoredJoinKind.ANTI})
# JOIN kinds that may join a let with capture lines (LATERAL, D70.03).
LATERAL_JOINS = frozenset(
    {AuthoredJoinKind.CROSS, AuthoredJoinKind.INNER, AuthoredJoinKind.LEFT}
)
_READS = (RelationExistsExpr, RelationScalarExpr, RelationMembershipExpr)


def _diagnostic(key: str, message: str, span: Span) -> Diagnostic:
    return Diagnostic(
        code=CAPTURE_DIAGNOSTICS.get(key) or LATERAL_DIAGNOSTICS[key],
        severity=Severity.ERROR,
        message=message,
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def captured_field_diagnostic(
    capture: str, field: str, span: Span, *, known: bool = True
) -> Diagnostic:
    """The semantic refusal of a field its captured outer input does not have,
    or of any field of an input whose columns are not known before completion."""

    return _diagnostic(
        "field",
        f"Captured input {capture} has no row field {field}."
        if known
        else f"Captured field {capture}.{field} is not yet available: the columns "
        f"of {capture} are not known before completion.",
        span,
    )


def outer_row_bindings(block: BlockRelationDef) -> tuple[tuple[str, int], ...]:
    """Row binding names of a declaration body with their binding positions.

    Position 0 is the FROM input and ``k + 1`` the target of JOIN ``k``; a SEMI
    or ANTI target never reaches the row and a body without a FROM relation
    has no row binding.
    """

    body = block.body
    if type(body) is not SelectBody or type(body.from_clause) is not FromClause:
        return ()
    return (
        (body.from_clause.source_name, 0),
        *(
            (join.target_binding_name, position + 1)
            for position, join in enumerate(body.join_clauses)
            if join.kind not in _FILTERING_JOINS
        ),
    )


def lateral_join(block: BlockRelationDef, let: LetRelationDef) -> int | None:
    """The position of the JOIN of ``block``'s body that reads ``let``, if any.

    A let with capture lines joined by its declaration body is read LATERAL:
    its capture lines read the row of the bindings to the left of that JOIN.
    """

    body = block.body
    if type(body) is not SelectBody:
        return None
    positions = tuple(
        position
        for position, join in enumerate(body.join_clauses)
        if join.target_relation_name == let.name
    )
    return positions[0] if len(positions) == 1 else None


def null_extended_bindings(
    block: BlockRelationDef, let: LetRelationDef | None = None
) -> frozenset[int]:
    """Binding positions an outer JOIN of the body may null-extend.

    A LEFT or FULL JOIN null-extends its target; a RIGHT or FULL JOIN
    null-extends the FROM input and every earlier JOIN target. For a let read
    LATERAL by JOIN ``k`` only the JOINs left of it count: they built its row.
    """

    body = block.body
    if type(body) is not SelectBody:
        return frozenset()
    lateral = None if let is None else lateral_join(block, let)
    nulled: set[int] = set()
    for position, join in enumerate(body.join_clauses[:lateral]):
        if join.kind in {AuthoredJoinKind.LEFT, AuthoredJoinKind.FULL}:
            nulled.add(position + 1)
        if join.kind in {AuthoredJoinKind.RIGHT, AuthoredJoinKind.FULL}:
            nulled.update(range(position + 1))
    return frozenset(nulled)


def captured_field_reads(let: LetRelationDef) -> tuple[CapturedFieldExpr, ...]:
    """Every captured field read written in one let body, in source order."""

    return _captured_reads(let.body)


def _captured_reads(root: object) -> tuple[CapturedFieldExpr, ...]:
    found: list[CapturedFieldExpr] = []
    pending: list[object] = [root]
    while pending:
        value = pending.pop()
        kind = type(value)
        if kind is tuple:
            pending.extend(reversed(cast(tuple[object, ...], value)))
            continue
        if (
            kind is Span
            or kind.__module__ != "pietto.ast_nodes"
            or not is_dataclass(value)
        ):
            continue
        if kind is CapturedFieldExpr:
            found.append(cast(CapturedFieldExpr, value))
            continue
        pending.extend(
            reversed(tuple(getattr(value, item.name) for item in fields(value)))
        )
    return tuple(sorted(found, key=lambda item: (item.span.line, item.span.column)))


def _inner_bindings(let: LetRelationDef) -> frozenset[str]:
    body = let.body
    if type(body) is SetOperationBody:
        return frozenset(operand.relation_name for operand in body.operands)
    if type(body) is not SelectBody:
        return frozenset()
    source = body.from_clause
    names = {
        source.source_name
        if type(source) is FromClause
        else cast(TableFunctionFromClause, source).binding_name
    }
    for join in body.join_clauses:
        names.update((join.target_binding_name, join.source_binding_name))
    return frozenset(names)


def takes_order_and_limit(block: BlockRelationDef, let: LetRelationDef) -> bool:
    """Whether the reads of ``let`` may take its ORDER BY and LIMIT.

    The one reader gate for a let with capture lines ending in ORDER BY and
    LIMIT (a top-k per outer row): a let the declaration body joins (LATERAL)
    or reads by ``scalar``, ``in`` or ``not in`` takes them, even when it is
    read more than once, which is refused at each later read (PIE-S2370); an
    ``exists`` read does not. Every later layer realizes and verifies those
    bodies inside whatever read renders the let; MySQL emission refuses them
    inside a ``scalar`` or ``in`` read (D70.05).
    """

    body = block.body
    if type(body) is SelectBody and any(
        join.target_relation_name == let.name for join in body.join_clauses
    ):
        return True
    nodes: list[Node] = []
    _walk(body, nodes)
    return any(
        type(node) in (RelationScalarExpr, RelationMembershipExpr)
        and _read_name(node) == let.name
        for node in nodes
    )


def admitted_capture_body(let: LetRelationDef, ordered: bool = False) -> bool:
    """FROM a relation, an optional WHERE and an ungrouped, window-free SELECT;
    when ``ordered`` (``takes_order_and_limit``) it may end in ORDER BY and
    LIMIT (a per-row top-k) whose ORDER BY reads no captured field and no
    aggregate."""

    body = let.body
    return (
        type(body) is SelectBody
        and type(body.from_clause) is FromClause
        and not body.join_clauses
        and body.let_clause is None
        and body.group_by_clause is None
        and (
            body.order_by_clause is None
            or (
                ordered
                and not _captured_reads(body.order_by_clause)
                and not any(
                    contains_semantic_aggregate(item.expression)
                    for item in body.order_by_clause.items
                )
            )
        )
        and (ordered or body.limit_clause is None)
        and body.satisfying_clause is None
        and body.qualify_clause is None
        and not body.named_windows
        and body.distinct_clause is None
        and not any(
            type(item.expression) is WindowExpr
            or contains_semantic_aggregate(item.expression)
            for item in body.select_items
        )
        and (
            body.where_clause is None
            or not contains_semantic_aggregate(body.where_clause.expression)
        )
    )


def _walk(root: object, found: list[Node]) -> None:
    """Collect relation names read by FROM, JOIN, set operands and expressions."""

    pending: list[object] = [root]
    while pending:
        value = pending.pop()
        kind = type(value)
        if kind is tuple:
            pending.extend(reversed(cast(tuple[object, ...], value)))
            continue
        if (
            kind is Span
            or kind.__module__ != "pietto.ast_nodes"
            or not is_dataclass(value)
        ):
            continue
        if kind in {FromClause, JoinClause, SetOperand, *_READS}:
            found.append(cast(Node, value))
        pending.extend(
            reversed(tuple(getattr(value, item.name) for item in fields(value)))
        )


def _read_name(node: Node) -> str:
    if type(node) is FromClause:
        return node.source_name
    if type(node) is JoinClause:
        return node.target_relation_name
    if type(node) is SetOperand:
        return node.relation_name
    return cast(RelationExistsExpr, node).relation_name


def _block_diagnostics(block: BlockRelationDef) -> list[Diagnostic]:
    found: list[Diagnostic] = []
    outer = outer_row_bindings(block)
    captured = [let for let in block.let_relations if let.captures]
    for let in captured:
        seen: set[str] = set()
        inner = _inner_bindings(let)
        for clause in let.captures:
            name = clause.name
            if name in seen:
                found.append(
                    _diagnostic(
                        "duplicate",
                        f"Capture {name} is written more than once in let {let.name}.",
                        clause.span,
                    )
                )
                continue
            seen.add(name)
            if name in inner:
                found.append(
                    _diagnostic(
                        "self_correlation",
                        f"Capture {name} is also an input of let {let.name}; "
                        "rename that input through another let.",
                        clause.span,
                    )
                )
            elif sum(binding == name for binding, _ in outer) != 1:
                found.append(
                    _diagnostic(
                        "outer_input",
                        f"Capture {name} does not name one FROM or JOIN row "
                        f"input of {block.name}.",
                        clause.span,
                    )
                )
        body = let.body
        gated = (
            type(body) is ValuesBody and not gate.explicit_modules_admits(ValuesBody)
        ) or (
            type(body) is SelectBody
            and type(body.from_clause) is TableFunctionFromClause
            and not gate.explicit_modules_admits(TableFunctionFromClause)
        )
        ordered = takes_order_and_limit(block, let)
        if not gated and not admitted_capture_body(let, ordered):
            found.append(
                _diagnostic(
                    "unsupported",
                    f"Let {let.name} with capture lines may use only FROM, "
                    + (
                        "WHERE, an ungrouped SELECT, an ungrouped ORDER BY "
                        "without captured fields and LIMIT."
                        if ordered
                        else "WHERE and an ungrouped SELECT."
                    ),
                    let.span,
                )
            )
    if not captured:
        return found
    names = {let.name: let for let in captured}
    reads: list[tuple[Node, bool]] = []
    for scope, in_body in (
        *((let.body, False) for let in block.let_relations),
        (block.body, True),
    ):
        nodes: list[Node] = []
        _walk(scope, nodes)
        reads.extend((node, in_body) for node in nodes)
    # Unlike other lets (Phase70 S05), a let with capture lines is read
    # exactly once: by its one admitted read; every later one in source order
    # and every other read is refused.
    admitted: set[str] = set()
    for node, in_body in sorted(
        reads, key=lambda item: (item[0].span.line, item[0].span.column)
    ):
        let = names.get(_read_name(node))
        if let is None:
            continue
        if type(node) in (*_READS, JoinClause) and in_body and let.name not in admitted:
            admitted.add(let.name)
            if type(node) is JoinClause:
                found.extend(_lateral_diagnostics(block, let, node, outer))
            continue
        found.append(
            _diagnostic(
                "unsupported",
                f"Let {let.name} with capture lines can be read only once, by "
                f"exists, scalar, in or a join in the body of {block.name}.",
                node.span,
            )
        )
    return found


def _lateral_diagnostics(
    block: BlockRelationDef,
    let: LetRelationDef,
    join: JoinClause,
    outer: tuple[tuple[str, int], ...],
) -> list[Diagnostic]:
    """A JOIN of the declaration body reads a let with capture lines LATERAL.

    The JOIN kind must keep every left row it pairs with the let's rows, and
    each capture line must name a row input to the left of that JOIN.
    """

    if join.kind not in LATERAL_JOINS:
        return [
            _diagnostic(
                "kind",
                f"Let {let.name} with capture lines can be joined only by "
                "cross, inner or left join.",
                join.span,
            )
        ]
    position = cast(SelectBody, block.body).join_clauses.index(join) + 1
    inner = _inner_bindings(let)
    found: list[Diagnostic] = []
    seen: set[str] = set()
    for clause in let.captures:
        bindings = tuple(index for name, index in outer if name == clause.name)
        if (
            clause.name in seen
            or clause.name in inner
            or len(bindings) != 1
            or bindings[0] < position
        ):
            seen.add(clause.name)
            continue
        seen.add(clause.name)
        found.append(
            _diagnostic(
                "prefix",
                f"Capture {clause.name} of let {let.name} is not a row input to "
                f"the left of its join in {block.name}.",
                clause.span,
            )
        )
    return found


def capture_diagnostics(script: Script) -> tuple[Diagnostic, ...]:
    """Structural capture refusals of one EXPLICIT_MODULES file.

    They belong to the file's pre-admission diagnostics, which the caller
    merges in ``gate.source_order``.
    """

    found: list[Diagnostic] = []
    for definition in script.definitions:
        if type(definition) is BlockRelationDef:
            found.extend(_block_diagnostics(definition))
    return tuple(found)
