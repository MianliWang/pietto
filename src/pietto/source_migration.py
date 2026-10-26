"""Lossless spelling migration using the compiler's bounded concrete parse tree."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from pathlib import Path
from collections.abc import Mapping
from typing import Any

from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto import ast_nodes as ast
from pietto import parser_api
from pietto.ast_nodes import (
    ConstraintDef,
    DeriveDef,
    FunctionDef,
    ImportStatement,
    Script,
    ShapeDef,
    SourceDef,
)
from pietto.errors import Diagnostic, Severity, SourceLocation, source_path
from pietto.generated.PiettoParser import PiettoParser


type _Context = Any
type _Edit = tuple[int, int, str]

_BARE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_LITERAL_WORDS = frozenset({"True", "False", "None", "true", "false", "null"})


@dataclass(frozen=True, slots=True)
class MigrationResult:
    """Complete migrated source, or diagnostics without partial output."""

    source: str | None
    diagnostics: tuple[Diagnostic, ...]


def migrate_file(path: str | Path) -> MigrationResult:
    """Read a bounded UTF-8 input without changing it."""

    with Path(path).open("rb") as stream:
        source = stream.read(parser_api._MAX_SOURCE_UTF8_BYTES + 1)
    if len(source) > parser_api._MAX_SOURCE_UTF8_BYTES:
        failure = parser_api._budget_failure(
            code="PIE-P1006",
            message="Source exceeds the maximum supported size of "
            f"{parser_api._MAX_SOURCE_UTF8_BYTES} UTF-8 bytes.",
            path=path,
            line=1,
            column=1,
        )
        return MigrationResult(None, failure.diagnostics)
    return migrate_source(source.decode("utf-8"), path=path)


def migrate_source(source: str, *, path: str | Path | None = None) -> MigrationResult:
    """Rewrite admitted legacy spellings while retaining all untouched bytes."""

    modern = _modern_parse(source, path)
    legacy, tree = parser_api._parse_migration_source(source, path=path)
    script, legacy_tokens = legacy.ast, True
    if script is None or tree is None:
        if modern.ast is not None:
            return MigrationResult(source, modern.diagnostics)
        # Modern tokens the old reader cannot read, such as `T | None`, beside
        # spellings the modern syntax retired: read it as modern to migrate.
        read, tree = parser_api._parse_migration_source(source, path=path, modern=True)
        if read.ast is None or tree is None:
            return MigrationResult(None, legacy.diagnostics)
        script, legacy_tokens = read.ast, False
    # A bare type is unknown in 0.1.4 and never None in modern syntax, so its
    # meaning is ambiguous whenever the source also has a modern reading: the
    # whole source parses as modern, or the tree was read with modern tokens.
    ambiguous = modern.ast is not None or script is not legacy.ast

    prefix = "\ufeff" if source.startswith("\ufeff") else ""
    body = source[len(prefix) :]
    diagnostics: list[Diagnostic] = []
    float_is_callable = any(
        definition.name == "Float"
        for definition in script.definitions
        if isinstance(definition, (FunctionDef, ConstraintDef, DeriveDef))
    ) or any(template.name == "Float" for template in script.relationship_templates)
    relationships = frozenset(
        template.name for template in script.relationship_templates
    )
    window_clashes = _window_input_clashes(script)
    # Only a source that the modern parser refuses and the old reader reads
    # migrates its ORDER BY keys; one that also uses modern spelling has no
    # old reading to keep, and `check` reports a key of it that is ambiguous.
    source_rows = _source_rows(script) if modern.ast is None and legacy_tokens else None
    edits: dict[int, list[_Edit]] = {}
    pending = [(tree, False)]
    while pending:
        context, visited = pending.pop()
        children = [
            child
            for child in context.getChildren()
            if isinstance(child, ParserRuleContext)
        ]
        if not visited:
            if modern.ast is not None and _modern_only_context(context):
                return MigrationResult(source, modern.diagnostics)
            pending.append((context, True))
            pending.extend((child, False) for child in reversed(children))
            continue
        changes = [change for child in children for change in edits.pop(id(child))]
        edits[id(context)] = _rewrite(
            context,
            body,
            changes,
            diagnostics,
            path,
            float_is_callable,
            legacy_tokens=legacy_tokens,
            window_clashes=window_clashes,
            source_rows=source_rows,
            ambiguous=ambiguous,
            relationships=relationships,
        )
    if diagnostics:
        diagnostics.sort(key=lambda item: (item.location.line, item.location.column))
        return MigrationResult(None, tuple(diagnostics))
    if modern.ast is not None:
        return MigrationResult(source, modern.diagnostics)

    changes = edits[id(tree)]
    if not changes:
        return MigrationResult(None, modern.diagnostics)
    migrated = prefix + _render(body, 0, len(body), changes)
    checked = _modern_parse(migrated, path)
    if checked.ast is None:
        first = min(changes, key=lambda edit: edit[0])[0]
        token = _first_token(tree, first)
        return MigrationResult(
            None,
            (
                _manual(
                    token,
                    path,
                    "This source needs manual migration; the complete rewrite is not "
                    "accepted by the modern grammar. No migrated source was emitted.",
                ),
            ),
        )
    return MigrationResult(migrated, checked.diagnostics)


def _modern_parse(source: str, path: str | Path | None) -> parser_api.ParseResult:
    """The modern parse without its warnings, such as PIE-P1009, which
    `check` reports: `migrate` reports only what stops it."""

    result = parser_api.parse_source(source, path=path)
    return replace(
        result,
        diagnostics=tuple(
            item for item in result.diagnostics if item.severity is Severity.ERROR
        ),
    )


def _token(context: _Context, name: str) -> Token | None:
    terminal = context.getToken(getattr(PiettoParser, name), 0)
    return None if terminal is None else terminal.symbol


def _modern_only_context(context: _Context) -> bool:
    """Identify source forms excluded by the legacy grammar, before AST normalization."""

    rule = PiettoParser.ruleNames[context.getRuleIndex()]
    if (number := _token(context, "NUMBER")) is not None and "_" in (number.text or ""):
        return True
    if rule in {"relationshipTemplate", "queryLetDeclaration", "anyExpression"}:
        return True
    if rule in {"constraintDefinition", "deriveDefinition"}:
        return _token(context, "RETURN") is not None  # a one-line body
    if rule == "qualifyBody":
        return len(context.qualifyLine()) > 1
    if rule in {
        "exportStatement",
        "groupByClause",
        "selectClause",
        "partitionByClause",
        "orderByClause",
        "setOperationBody",
        "qualifyClause",
    }:
        return _token(context, "COLON") is None
    if rule in {
        "sourceDefinition",
        "checkDefinition",
        "uniqueDefinition",
        "indexDefinition",
    }:
        return _token(context, "ASSIGN") is not None
    if rule == "importStatement":
        return _token(context, "FROM") is not None
    if rule == "joinClause":
        return _token(context, "AS") is None
    if rule == "tableBody":
        # A WHERE before a JOIN; the legacy body has its one WHERE after them.
        steps = context.relationStep()
        joined = [
            index for index, step in enumerate(steps) if step.joinClause() is not None
        ]
        return any(
            step.whereClause() is not None
            for step in steps[: joined[-1] if joined else 0]
        )
    if rule in {"windowSpec", "qualifyInlineWindowSpec"}:
        return _token(context, "LPAREN") is not None
    if rule == "namedWindowDeclaration":
        return _token(context, "LET") is not None
    if rule == "satisfyingClause":
        return _token(context, "HAVING") is not None
    if rule == "nullabilityModifier":
        return _token(context, "PIPE") is not None
    if rule in {"comparisonExpression", "qualifyComparisonExpression"}:
        return (
            len(context.comparisonOperator()) > 1 or _token(context, "NONE") is not None
        )
    if (
        rule in {"constraintBody", "deriveBody"}
        and _token(context, "RETURN") is not None
    ):
        return not _legacy_return_expression(context.expression())
    return False


def _legacy_return_expression(expression: _Context) -> bool:
    """Whether a preceding `return` identifier forms a legacy expression."""

    first = expression.start
    if first.type in {PiettoParser.LPAREN, PiettoParser.PLUS, PiettoParser.MINUS}:
        return True
    if first.type == PiettoParser.NOT:
        first = _first_token(expression, first.stop + 1)
    if first.type != PiettoParser.IN:
        return False
    opening = _first_token(expression, first.stop + 1)
    if opening.type != PiettoParser.LPAREN:
        return False
    pending = [expression]
    while pending:
        context = pending.pop()
        if (
            PiettoParser.ruleNames[context.getRuleIndex()] == "callSuffix"
            and context.start.start == opening.start
        ):
            # A legacy membership cannot be the left operand of arithmetic/comparison.
            return context.stop.stop == expression.stop.stop or _first_token(
                expression, context.stop.stop + 1
            ).type in {PiettoParser.AND, PiettoParser.OR, PiettoParser.IF}
        pending.extend(
            child
            for child in context.getChildren()
            if isinstance(child, ParserRuleContext)
        )
    raise AssertionError(
        "an admitted direct in(...) expression must have a call suffix"
    )


def _replace(token: Token, text: str) -> _Edit:
    return token.start, token.stop + 1, text


def _render(source: str, start: int, end: int, edits: list[_Edit]) -> str:
    pieces: list[str] = []
    cursor = start
    for begin, stop, replacement in sorted(edits, key=lambda item: (item[0], item[1])):
        if begin < start or stop > end:
            continue
        assert begin >= cursor, "migration edits must not overlap"
        pieces.extend((source[cursor:begin], replacement))
        cursor = stop
    pieces.append(source[cursor:end])
    return "".join(pieces)


def _last_token(context: _Context) -> Token:
    pending = [context]
    while pending:
        current = pending.pop()
        if isinstance(current, ParserRuleContext):
            pending.extend(current.getChildren())
        elif current.symbol.type not in {
            Token.EOF,
            PiettoParser.NEWLINE,
            PiettoParser.INDENT,
            PiettoParser.DEDENT,
        }:
            return current.symbol
    raise AssertionError("successful migration context has no source token")


def _first_token(context: _Context, offset: int) -> Token:
    pending = [context]
    while pending:
        current = pending.pop()
        if isinstance(current, ParserRuleContext):
            pending.extend(reversed(list(current.getChildren())))
        elif current.symbol.start >= offset:
            return current.symbol
    return context.start


def _manual(
    token: Token,
    path: str | Path | None,
    message: str,
    *,
    end: Token | None = None,
) -> Diagnostic:
    return Diagnostic(
        code="PIE-P1011",
        severity=Severity.ERROR,
        message=message,
        location=SourceLocation(
            path=source_path(path),
            line=token.line,
            column=token.column + 1,
            end_line=None if end is None else end.line,
            end_column=None if end is None else end.column + len(end.text or "") + 1,
        ),
        suggestion="Rewrite this declaration explicitly, preserving its identities and metadata.",
    )


def _rewrite(
    context: _Context,
    source: str,
    edits: list[_Edit],
    diagnostics: list[Diagnostic],
    path: str | Path | None,
    float_is_callable: bool,
    *,
    legacy_tokens: bool,
    window_clashes: dict[tuple[int, int], str],
    source_rows: Mapping[str, frozenset[str] | None] | None,
    ambiguous: bool,
    relationships: frozenset[str],
) -> list[_Edit]:
    """Collect one context's edits; ``ambiguous`` marks a source that also has
    a modern reading, where a bare type cannot be migrated, and
    ``relationships`` names the relationship templates of the file."""

    rule = PiettoParser.ruleNames[context.getRuleIndex()]
    colon = _token(context, "COLON")
    if rule == "tableBody":
        # A relation body's own rewrites, in order: its ORDER BY keys first,
        # then the windows move: a moved line carries the edits inside it
        # along.
        if source_rows is not None:
            edits.extend(_input_order_keys(context, source_rows, path, diagnostics))
        return _move_windows_before_select(
            context, source, edits, diagnostics, path, window_clashes=window_clashes
        )
    elif rule == "identifier" and context.start.text in {"True", "False", "None"}:
        diagnostics.append(
            _manual(
                context.start,
                path,
                f"Legacy identifier '{context.start.text}' needs manual migration "
                "because it is a literal keyword in modern syntax. Confirm the "
                "intended meaning and rename any legacy identifier and its references "
                "explicitly; no migrated source was emitted.",
                end=context.stop,
            )
        )
    elif rule == "literal":
        if context.start.text in {"null", "true", "false"}:
            edits.append(
                _replace(
                    context.start,
                    {"null": "None", "true": "True", "false": "False"}[
                        context.start.text
                    ],
                )
            )
    elif rule == "nullabilityModifier":
        if (token := _token(context, "NULLABLE")) is not None:
            edits.append(_replace(token, "| None"))
    elif rule == "typeExpression":
        _rewrite_nullability(context, edits, diagnostics, path, ambiguous=ambiguous)
    elif rule == "sourceDefinition":
        if (token := _token(context, "IS")) is not None:
            edits.append(_replace(token, "="))
    elif rule in {"constraintBody", "deriveBody"}:
        expression = context.expression()
        if (token := _token(context, "RETURN")) is None:
            edits.append((expression.start.start, expression.start.start, "return "))
        elif legacy_tokens and _legacy_return_expression(expression):
            diagnostics.append(
                _manual(
                    token,
                    path,
                    "This return body also admits a legacy expression using the "
                    "identifier 'return'. Confirm its intended meaning explicitly; "
                    "no migrated source was emitted.",
                    end=expression.stop,
                )
            )
    elif rule in {"comparisonExpression", "qualifyComparisonExpression"}:
        if (
            _token(context, "IS") is not None
            and (token := _token(context, "NULL")) is not None
        ):
            edits.append(_replace(token, "None"))
        if (between := _token(context, "BETWEEN")) is not None:
            operands = (
                context.additiveExpression()
                if rule == "comparisonExpression"
                else context.qualifyAdditiveExpression()
            )
            value, lower, upper = operands
            conjunction = _token(context, "AND")
            assert conjunction is not None
            start, end = context.start.start, context.stop.stop + 1
            value_text = _render(source, value.start.start, value.stop.stop + 1, edits)
            lower_text = _render(source, lower.start.start, lower.stop.stop + 1, edits)
            upper_text = _render(source, upper.start.start, upper.stop.stop + 1, edits)
            text = (
                lower_text
                + source[value.stop.stop + 1 : between.start]
                + "<="
                + source[between.stop + 1 : lower.start.start]
                + value_text
                + source[lower.stop.stop + 1 : conjunction.start]
                + "<="
                + source[conjunction.stop + 1 : upper.start.start]
                + upper_text
            )
            return [(start, end, text)]
    elif rule in {"primaryExpression", "qualifyPrimaryExpression"}:
        if (token := _token(context, "CAST")) is not None:
            target = context.typeExpression()
            if target.getText() != "Float":
                diagnostics.append(
                    _manual(
                        token,
                        path,
                        "Only the existing unqualified Float cast has an automatic migration.",
                    )
                )
            elif float_is_callable:
                diagnostics.append(
                    _manual(
                        token,
                        path,
                        "Legacy cast to Float needs manual migration because Float is "
                        "also declared as a callable; rewriting it would change call resolution.",
                        end=context.stop,
                    )
                )
            else:
                as_token = _token(context, "AS")
                assert as_token is not None
                edits.extend(
                    (
                        _replace(token, "Float"),
                        _replace(as_token, ""),
                        (target.start.start, target.stop.stop + 1, ""),
                    )
                )
    elif rule in {"uniqueDefinition", "indexDefinition"}:
        keyword = _token(context, "UNIQUE" if rule == "uniqueDefinition" else "INDEX")
        on = _token(context, "ON")
        if keyword is not None and on is not None:
            name = context.identifier().getText()
            spelling = "unique" if rule == "uniqueDefinition" else "index"
            edits.append((keyword.start, on.stop + 1, f"{name} = {spelling}("))
            end = context.fieldName()[-1].stop.stop + 1
            edits.append((end, end, ")"))
    elif rule == "checkDefinition" and colon is not None:
        name = context.identifier().getText()
        edits.append((context.start.start, colon.stop + 1, f"{name} = check("))
        suite = context.predicateSuite()
        lines = (
            [suite.predicateLine()]
            if suite.predicateLine() is not None
            else suite.predicateBody().predicateLine()
        )
        if len(lines) > 1:
            for index, line in enumerate(lines):
                expression = line.expression()
                start, end = expression.start.start, expression.stop.stop + 1
                edits.append((start, start, "("))
                edits.append((end, end, ") and" if index < len(lines) - 1 else ")"))
        end = lines[-1].expression().stop.stop + 1
        edits.append((end, end, ")"))
    elif rule in {"importStatement", "exportStatement"} and colon is not None:
        if rule == "importStatement":
            edits.append(_replace(context.start, "from"))
            edits.append(_replace(colon, " import ("))
            items = context.importBody().importItem()
        else:
            edits.append(_replace(colon, " ("))
            items = context.exportBody().exportItem()
        for item in items[:-1]:
            end = _last_token(item).stop + 1
            edits.append((end, end, ","))
        end = _last_token(items[-1]).stop + 1
        edits.append((end, end, ")"))
    elif rule == "relationshipDefinition" and _token(context, "LPAREN") is None:
        diagnostics.append(
            _manual(
                context.start,
                path,
                "Legacy source-bound relationship metadata needs manual migration: "
                "shape roles, actual source identities, and proof provenance cannot be inferred safely.",
            )
        )
    elif rule == "joinClause" and _token(context, "AS") is not None:
        kind = context.start.text
        if kind in {"semi", "anti"}:
            rewrite = (
                f"rewriting it as `where {'not ' if kind == 'anti' else ''}any("
                f"predicate for {context.identifier(1).getText()} in "
                f"{context.identifier(0).getText()})`"
            )
        else:
            rewrite = "introducing let" if kind == "cross" else "introducing let and on"
        diagnostics.append(
            _manual(
                context.start,
                path,
                "Legacy JOIN bindings need manual migration: preserve the exact input occurrence, "
                f"roles, inferred source, and relationship metadata when {rewrite}.",
            )
        )
    elif rule == "joinClause" and context.start.text in {"semi", "anti"}:
        return _existence_filter(
            context, source, edits, diagnostics, path, relationships
        )
    elif rule == "enumDefinition" and colon is None:
        end = context.identifier().stop.stop + 1
        edits.append((end, end, ":"))
    elif rule == "letClause" and colon is not None:
        lines = (
            [context.letLine()]
            if context.letLine() is not None
            else context.letBody().letLine()
        )
        inline = lines[0].start.line == context.start.line
        edits.append(_replace(colon, _colon_spacing(source, colon) if inline else ""))
        if not inline:
            edits.append(_replace(context.start, ""))
        for number, line in enumerate(lines):
            bindings = line.letBinding()
            if not inline:
                start = line.start.start - line.start.column
                edits.append((start, line.start.start, " " * context.start.column))
            for position, binding in enumerate(bindings):
                if not inline or number or position:
                    if position:
                        comma = line.getToken(PiettoParser.COMMA, position - 1).symbol
                        edits.append(
                            (
                                comma.start,
                                binding.start.start,
                                _line_ending(source) + " " * context.start.column,
                            )
                        )
                    edits.append((binding.start.start, binding.start.start, "let "))
    elif rule in {"windowSpec", "qualifyInlineWindowSpec", "namedWindowDeclaration"}:
        if rule == "namedWindowDeclaration" and context.start.text == "window":
            names = context.identifier()
            if not isinstance(names, list):
                names = [names]
            edits.append(_replace(context.start, "let"))
            if (assignment := _token(context, "ASSIGN")) is not None:
                edits.append(_replace(assignment, "= window"))
            else:
                end = names[0].stop.stop + 1
                edits.append((end, end, " = window"))
        if colon is not None:
            edits.append(_replace(colon, "("))
            end = _last_token(context).stop + 1
            edits.append((end, end, ")"))
    elif rule == "satisfyingClause":
        if (token := _token(context, "SATISFYING")) is not None:
            edits.append(_replace(token, "having"))

    if (
        rule
        in {
            "whereClause",
            "groupByClause",
            "selectClause",
            "satisfyingClause",
            "orderByClause",
            "partitionByClause",
        }
        and colon is not None
    ):
        following = _first_token(context, colon.stop + 1)
        if following.line == colon.line and following.type != PiettoParser.NEWLINE:
            edits.append(_replace(colon, _colon_spacing(source, colon)))
        elif rule in {"partitionByClause", "orderByClause"} and _inside_window(context):
            edits.append(_replace(colon, ""))
            body_name = (
                "windowPartitionBody" if rule == "partitionByClause" else "orderByBody"
            )
            line_name = (
                "windowPartitionLine" if rule == "partitionByClause" else "orderByLine"
            )
            lines = getattr(getattr(context, body_name)(), line_name)()
            for line in lines[:-1]:
                end = _last_token(line).stop + 1
                edits.append((end, end, ","))
    return edits


def _existence_filter(
    context: _Context,
    source: str,
    edits: list[_Edit],
    diagnostics: list[Diagnostic],
    path: str | Path | None,
    relationships: frozenset[str],
) -> list[_Edit]:
    """Rewrite `semi join x on p` in place as `where any(p for x in x)`.

    The JOIN's name binds each row of its input in the predicate, as the JOIN
    target did, so the predicate keeps its text.  Before a later JOIN the
    WHERE filters at the same JOIN prefix; as the last JOIN it becomes the
    relation's WHERE, unless lets, a WHERE or a `let:` block follow it there.
    The new binder `x` must hide nothing else the predicate reads as `x`.
    """

    kind = context.start.text
    predicate = context.expression()
    body = context.parentCtx.parentCtx
    steps = body.relationStep()
    later = steps[steps.index(context.parentCtx) + 1 :]
    name = context.identifier(0).getText()
    if predicate is None:
        reason = "it has no `on` predicate to test"
    elif not any(step.joinClause() is not None for step in later) and (
        later or body.letClause() is not None
    ):
        reason = "lets or a WHERE follow it after the last JOIN"
    elif (hidden := _hidden_by_binder(body, context, name, relationships)) is not None:
        reason = f"its new binder {name} would hide {hidden}"
    else:
        test = _render(source, predicate.start.start, predicate.stop.stop + 1, edits)
        negation = "not " if kind == "anti" else ""
        return [
            (
                context.start.start,
                predicate.stop.stop + 1,
                f"where {negation}any({test} for {name} in {name})",
            )
        ]
    diagnostics.append(
        _manual(
            context.start,
            path,
            f"This {kind} JOIN needs manual migration to `where "
            f"{'not ' if kind == 'anti' else ''}any(...)` because {reason}; "
            "no migrated source was emitted.",
            end=_last_token(context),
        )
    )
    return []


def _hidden_by_binder(
    body: _Context, join: _Context, name: str, relationships: frozenset[str]
) -> str | None:
    """What else named ``name`` the ON predicate of ``join`` reads, which the
    binder of `any(... for name in name)` would hide, in source order.

    Inside the predicate the binder takes the JOIN binding's place: a row read
    `name.field`, or `name` as a relationship row argument, keeps its meaning.
    It also hides the relation of that name from an `any(...)` iterable, the
    name read alone (an input field), and another input binding of the name.
    An inner `any(... for name in r)` hides the name from its own predicate.
    """

    others = [body.fromClause().identifier()[-1]] + [
        step.joinClause().identifier()[-1]
        for step in body.relationStep()
        if step.joinClause() is not None and step.joinClause() is not join
    ]
    if any(other.getText() == name for other in others):
        return f"the FROM input or another JOIN of this query named {name}"
    pending = [join.expression()]
    while pending:
        context = pending.pop()
        rule = PiettoParser.ruleNames[context.getRuleIndex()]
        children: list[_Context] = [
            child
            for child in context.getChildren()
            if isinstance(child, ParserRuleContext)
        ]
        if rule == "anyExpression":
            if context.identifier().getText() == name:
                return (
                    f"the relation {name} that its `on` predicate reads in `any(...)`"
                )
            children = (
                [] if context.fieldName().getText() == name else [context.expression()]
            )
        elif rule == "primaryExpression" and context.dottedName() is not None:
            callee, call = context.dottedName(), context.callSuffix()
            if call is None:
                if callee.getText() == name:
                    return f"the bare name {name} that its `on` predicate reads"
                children = []
            else:
                children = [
                    argument
                    for argument in call.expression()
                    if callee.getText() not in relationships
                    or argument.getText() != name
                ]
        pending.extend(reversed(children))
    return None


def _move_windows_before_select(
    body: _Context,
    source: str,
    edits: list[_Edit],
    diagnostics: list[Diagnostic],
    path: str | Path | None,
    *,
    window_clashes: dict[tuple[int, int], str],
) -> list[_Edit]:
    """Move the whole lines of each named window declared after select to the
    end of the lets, before where, group by or select.

    Windows now share the let namespace, so a window named like a let of its
    query, or like one of its input fields or relations, which a let cannot
    take, needs manual migration.
    """

    select = body.selectClause()
    late = [
        window
        for window in body.namedWindowDeclaration()
        if window.start.tokenIndex > select.start.tokenIndex
    ]
    names = _let_names(body) if late else set()
    refused = False
    for window in late:
        name = window.identifier(0)
        clash = window_clashes.get((window.start.line, window.start.column + 1))
        if name.getText() in names:
            message = (
                f"The named window {name.getText()} has the name of a let of its "
                "query, and windows now share the let namespace; rename one of "
                "them explicitly. No migrated source was emitted."
            )
        elif clash is not None:
            message = (
                f"The named window {name.getText()} has the name of {clash} of its "
                "query, which a window, like a let, cannot take now; rename the "
                "window explicitly. No migrated source was emitted."
            )
        else:
            continue
        refused = True
        diagnostics.append(_manual(window.start, path, message, end=name.stop))
    if not late or refused:
        return edits
    steps = body.relationStep()
    joined = [
        index for index, step in enumerate(steps) if step.joinClause() is not None
    ]
    # The relation's own WHERE: the step after the last JOIN, or after `let:`,
    # or the last JOIN itself when it is a semi/anti JOIN that becomes it.
    where = next(
        (
            step.whereClause()
            for step in steps[joined[-1] + 1 if joined else 0 :]
            if step.whereClause() is not None
        ),
        body.whereClause(),
    )
    if where is None and joined and steps[joined[-1]].start.text in {"semi", "anti"}:
        where = steps[joined[-1]]
    target = next(
        clause for clause in (where, body.groupByClause(), select) if clause is not None
    )
    moved: list[str] = []
    removed: list[list[int]] = []
    for window in late:
        start = window.start.start - window.start.column
        last = _last_token(window).stop + 1
        end = _line_end(source, last)
        inside = [edit for edit in edits if start <= edit[0] <= last]
        edits = [edit for edit in edits if edit not in inside]
        text = _render(source, start, end, inside)
        moved.append(
            text if text.endswith(("\n", "\r")) else text + _line_ending(source)
        )
        if removed and removed[-1][1] == start:
            removed[-1][1] = end
        else:
            removed.append([start, end])
    if removed[-1][1] == len(source) and not source.endswith(("\n", "\r")):
        # The file ends without a line end, so the removed last lines take
        # the line end before them.
        removed[-1][0] -= 2 if source.startswith("\r\n", removed[-1][0] - 2) else 1
    insert = target.start.start - target.start.column
    return [
        *edits,
        *((start, end, "") for start, end in removed),
        (insert, insert, "".join(moved)),
    ]


def _window_input_clashes(script: ast.Script) -> dict[tuple[int, int], str]:
    """The named windows, by position, named like an input field or relation
    of their body, as far as this file declares the inputs."""

    shapes: dict[str, set[str]] = {}
    relations: dict[tuple[str | None, str], list[ast.Node]] = {}
    bodies: list[tuple[str | None, ast.TableDef | ast.QueryDef | ast.SelectBody]] = []
    for definition in script.definitions:
        if isinstance(definition, ast.ShapeDef):
            shapes.setdefault(definition.name, set()).update(
                field.name for field in definition.fields
            )
        elif isinstance(definition, ast.BlockRelationDef):
            relations.setdefault((None, definition.name), []).append(definition.body)
            for let in definition.let_relations:
                relations.setdefault((definition.name, let.name), []).append(let.body)
            bodies.extend(
                (definition.name, body)
                for body in (
                    definition.body,
                    *(let.body for let in definition.let_relations),
                )
                if isinstance(body, ast.SelectBody)
            )
        elif isinstance(definition, ast.SetRelationDef):
            relations.setdefault((None, definition.name), []).append(definition.body)
        elif isinstance(definition, (ast.SourceDef, ast.TableDef, ast.QueryDef)):
            relations.setdefault((None, definition.name), []).append(definition)
            if not isinstance(definition, ast.SourceDef):
                bodies.append((None, definition))

    def fields(name: str, owner: str | None, seen: frozenset[str]) -> set[str]:
        found: set[str] = set()
        for relation in (
            relation
            for key in dict.fromkeys(((owner, name), (None, name)))
            for relation in relations.get(key, ())
        ):
            if isinstance(relation, ast.SourceDef):
                found |= shapes.get(relation.shape_name or "", set())
            elif isinstance(relation, (ast.TableDef, ast.QueryDef, ast.SelectBody)):
                found.update(
                    item.alias
                    or (
                        item.expression.name
                        if isinstance(item.expression, ast.NameExpr)
                        else item.expression.parts[-1]
                        if isinstance(item.expression, ast.DottedNameExpr)
                        else ""
                    )
                    for item in relation.select_items
                )
            elif isinstance(relation, ast.ValuesBody):
                found.update(column.name for column in relation.columns)
            elif isinstance(relation, ast.SetOperationBody) and name not in seen:
                found |= fields(
                    relation.operands[0].relation_name, owner, seen | {name}
                )
        return found

    clashes: dict[tuple[int, int], str] = {}
    for owner, body in bodies:
        source = body.from_clause
        if isinstance(source, ast.TableFunctionFromClause):
            input_fields = {source.binding_name}
            input_relations = {source.binding_name}
        else:
            input_fields = fields(source.source_name, owner, frozenset())
            input_relations = {source.binding_name or source.source_name}
            if body.join_clauses:
                input_relations.add(source.source_name)
        for join in body.join_clauses:
            input_relations.update(
                (join.target_binding_name, join.target_relation_name)
            )
            if join.kind not in (ast.AuthoredJoinKind.SEMI, ast.AuthoredJoinKind.ANTI):
                input_fields |= fields(join.target_relation_name, owner, frozenset())
        for window in body.named_windows:
            position = (window.span.line, window.span.column)
            if window.name in input_fields:
                clashes[position] = "an input field"
            elif window.name in input_relations:
                clashes[position] = "an input relation"
    return clashes


def _let_names(body: _Context) -> set[str]:
    """The names the lets of one relation body declare, relation lets included."""

    lets = [
        *body.queryLetDeclaration(),
        *(
            step.queryLetDeclaration()
            for step in body.relationStep()
            if step.queryLetDeclaration() is not None
        ),
    ]
    names = {let.fieldName().getText() for let in lets}
    clause = body.letClause()
    if clause is not None:
        lines = [] if clause.letLine() is None else [clause.letLine()]
        if clause.letBody() is not None:
            lines.extend(clause.letBody().letLine())
        names.update(
            binding.fieldName().getText()
            for line in lines
            for binding in line.letBinding()
        )
    owner = body.parentCtx
    while owner is not None and PiettoParser.ruleNames[owner.getRuleIndex()] not in {
        "tableDefinition",
        "queryDefinition",
    }:
        owner = owner.parentCtx
    if owner is not None:
        names.update(
            let.identifier().getText() for let in owner.letRelationDefinition()
        )
    return names


def _line_end(source: str, offset: int) -> int:
    """The offset just past the line end that follows ``offset``, if any."""

    for position in range(offset, len(source)):
        if source[position] == "\n":
            return position + 1
        if source[position] == "\r":
            return position + (2 if source.startswith("\r\n", position) else 1)
    return len(source)


def _source_rows(script: Script) -> dict[str, frozenset[str] | None]:
    """The input row of each source that this file alone declares.

    A source without a shape has an unknown row (None); one with a shape
    this file declares once has that shape's field names. A name that this
    file declares more than once or imports, or a source whose shape is
    not declared here once, is absent: its row is not syntactic.
    """

    declared: dict[str, list[object]] = {}
    for definition in script.definitions:
        declared.setdefault(getattr(definition, "name", ""), []).append(definition)
    for statement in script.module_statements:
        if isinstance(statement, ImportStatement):
            for item in statement.items:
                declared.setdefault(item.local_name or item.exported_name, []).append(
                    item
                )
    rows: dict[str, frozenset[str] | None] = {}
    for name, definitions in declared.items():
        source = definitions[0] if len(definitions) == 1 else None
        if not isinstance(source, SourceDef):
            continue
        if source.shape_name is None:
            rows[name] = None
            continue
        shapes = declared.get(source.shape_name, [])
        shape = shapes[0] if len(shapes) == 1 else None
        if isinstance(shape, ShapeDef):
            rows[name] = frozenset(field.name for field in shape.fields)
    return rows


def _input_order_keys(
    body: _Context,
    source_rows: Mapping[str, frozenset[str] | None],
    path: str | Path | None,
    diagnostics: list[Diagnostic],
) -> list[_Edit]:
    """Keep each ungrouped ORDER BY key, named alone, reading what it read.

    Over a known row such a key read the input field of its name even where
    a SELECT output of another value had that name too, and over an unknown
    row its SQL named it alone, which the database reads as that output. A
    modern key named alone reads the output, and is ambiguous where a known
    input row has a field of its name. So the key is qualified with the FROM
    binding where its FROM input is a source of this file whose shape, also
    of this file, has that field, and kept where that source has no shape
    or no such field. Which value it read is not syntactic over JOIN inputs
    or another FROM input (PIE-P1011).
    """

    order = body.orderByClause()
    if order is None or body.groupByClause() is not None:
        return []
    from_clause = body.fromClause()
    qualifier = from_clause.identifier()[-1].getText()
    select = body.selectClause()
    select_lines = [select.selectLine()] if select.selectLine() is not None else []
    if select.selectBody() is not None:
        select_lines.extend(select.selectBody().selectLine())
    # Whether every output of a name is that same input field; a window
    # result never is.
    same_field: dict[str, bool] = {}
    for line in select_lines:
        window = line.selectWindowItem()
        if window is not None:
            same_field[window.fieldName().getText()] = False
            continue
        for item in line.selectItem():
            value = item.expression().getText()
            parts = value.split(".")
            if item.fieldName() is not None:
                name = item.fieldName().getText()
            elif len(parts) <= 2 and all(_BARE_NAME.fullmatch(part) for part in parts):
                name = parts[-1]
            else:
                continue
            same_field[name] = same_field.get(name, True) and value in {
                name,
                f"{qualifier}.{name}",
            }
    steps = body.relationStep()
    joined = any(step.joinClause() is not None for step in steps)
    let_bindings = list(body.queryLetDeclaration())
    let_bindings.extend(
        step.queryLetDeclaration()
        for step in steps
        if step.queryLetDeclaration() is not None
    )
    let_clause = body.letClause()
    if let_clause is not None:
        let_lines = [let_clause.letLine()] if let_clause.letLine() is not None else []
        if let_clause.letBody() is not None:
            let_lines.extend(let_clause.letBody().letLine())
        let_bindings.extend(
            binding for line in let_lines for binding in line.letBinding()
        )
    let_names = {binding.fieldName().getText() for binding in let_bindings}
    input_name = from_clause.identifier()[0].getText()
    syntactic = (
        not joined
        and from_clause.callSuffix() is None
        and input_name not in let_names
        and input_name in source_rows
    )
    order_lines = [order.orderByLine()] if order.orderByLine() is not None else []
    if order.orderByBody() is not None:
        order_lines.extend(order.orderByBody().orderByLine())
    edits: list[_Edit] = []
    for line in order_lines:
        for item in line.orderItem():
            key = item.expression()
            name = key.getText()
            if (
                name in _LITERAL_WORDS
                or not _BARE_NAME.fullmatch(name)
                or same_field.get(name, True)
                or name in let_names
            ):
                continue
            if not syntactic:
                where = (
                    "over JOIN inputs"
                    if joined
                    else f"over the input '{input_name}', which is no source "
                    "with a shape declared in this file,"
                )
                diagnostics.append(
                    _manual(
                        key.start,
                        path,
                        f"ORDER BY key '{name}' names a SELECT output of another "
                        "value, which a modern key written alone reads; whether "
                        f"it read an input field {where} needs manual migration: "
                        "write the key with its input binding or rename the "
                        "output. No migrated source was emitted.",
                        end=key.stop,
                    )
                )
                continue
            fields = source_rows[input_name]
            if fields is not None and name in fields:
                edits.append((key.start.start, key.start.start, f"{qualifier}."))
    return edits


def _rewrite_nullability(
    context: _Context,
    edits: list[_Edit],
    diagnostics: list[Diagnostic],
    path: str | Path | None,
    *,
    ambiguous: bool,
) -> None:
    """Rewrite one declared type to the modern two nullability states.

    0.1.4 reads a bare type as unknown nullability, which becomes `T | None`,
    and `T not null` as never None, which becomes `T`. A cast target is the
    cast rule's. A `type` alias base keeps a bare type, as 0.1.4 never gave an
    alias's nullability to a value, and a modern alias cannot include None.
    """

    role = PiettoParser.ruleNames[context.parentCtx.getRuleIndex()]
    if role in {"primaryExpression", "qualifyPrimaryExpression"}:
        return
    modifier = context.nullabilityModifier()
    if modifier is None:
        if role == "typeDefinition":
            return
        if ambiguous:
            name = context.typeReference().identifier().getText()
            diagnostics.append(
                _manual(
                    context.start,
                    path,
                    f"Bare type '{name}' needs manual migration because 0.1.4 "
                    "reads it as unknown nullability and modern syntax as never "
                    f"None. Write '{name} | None' where a value may be None; a "
                    "source already written in modern syntax needs no migration. "
                    "No migrated source was emitted.",
                    end=context.stop,
                )
            )
            return
        end = context.stop.stop + 1
        edits.append((end, end, " | None"))
    elif _token(modifier, "NOT") is not None:
        edits.append(
            (context.typeReference().stop.stop + 1, modifier.stop.stop + 1, "")
        )
    elif role == "typeDefinition":
        diagnostics.append(
            _manual(
                modifier.start,
                path,
                "A nullable type alias needs manual migration because a modern "
                "alias names a type that is never None. Declare the alias with a "
                "bare type and write '| None' on each value of this type that may "
                "be None; no migrated source was emitted.",
            )
        )


def _inside_window(context: _Context) -> bool:
    parent = context.parentCtx
    while parent is not None:
        rule = PiettoParser.ruleNames[parent.getRuleIndex()]
        if rule in {"windowSpecBody", "windowInlineClause"}:
            return True
        if rule == "tableBody":
            return False
        parent = parent.parentCtx
    return False


def _line_ending(source: str) -> str:
    for position, character in enumerate(source):
        if character in "\r\n":
            return "\r\n" if source.startswith("\r\n", position) else character
    return "\n"


def _colon_spacing(source: str, colon: Token) -> str:
    return "" if source[colon.stop + 1 : colon.stop + 2].isspace() else " "
