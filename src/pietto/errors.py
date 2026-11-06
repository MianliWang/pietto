"""Structured parser diagnostics and internal AST construction errors."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum
from functools import cached_property
from pathlib import Path
from typing import Any

from antlr4.Token import Token
from antlr4.error.ErrorListener import ErrorListener
from antlr4.error.ErrorStrategy import DefaultErrorStrategy

from pietto.generated.PiettoParser import PiettoParser


class Severity(StrEnum):
    """Severity levels exposed by parser diagnostics."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """A one-based source location with optional half-open end coordinates."""

    path: str | None
    line: int
    column: int
    end_line: int | None = None
    end_column: int | None = None


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """A structured, user-facing parser diagnostic."""

    code: str
    severity: Severity
    message: str
    location: SourceLocation
    suggestion: str | None = None


UNEXPECTED_INDENTATION = "Unexpected indentation."


class ParseCancelled(Exception):
    """A parse stopped because its caller was interrupted while waiting."""


class AstBuildError(Exception):
    """An ordinary source error discovered while constructing the AST."""

    def __init__(self, message: str, *, line: int, column: int) -> None:
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column


def source_path(path: str | Path | None) -> str | None:
    """Normalize an optional path for public diagnostic and AST values."""

    return str(path) if path is not None else None


class DiagnosticErrorListener(ErrorListener):
    """Convert ANTLR lexer and parser errors into Pietto diagnostics."""

    def __init__(self, path: str | Path | None) -> None:
        self.path = source_path(path)
        self.diagnostics: list[Diagnostic] = []

    def syntaxError(
        self,
        recognizer: object,
        offendingSymbol: object,
        line: int,
        column: int,
        msg: str,
        e: Exception | None,
    ) -> None:
        """Record an ANTLR syntax callback as a generic Phase 1 error."""

        del recognizer, offendingSymbol, e
        self.diagnostics.append(
            Diagnostic(
                code="PIE-P1000",
                severity=Severity.ERROR,
                message=msg,
                location=SourceLocation(
                    path=self.path,
                    line=line,
                    column=column + 1,
                ),
            )
        )


_LAYOUT_TOKEN_TYPES = frozenset(
    {Token.EOF, PiettoParser.NEWLINE, PiettoParser.INDENT, PiettoParser.DEDENT}
)
_TOKEN_DISPLAY = {
    Token.EOF: "end of file",
    PiettoParser.NEWLINE: "end of line",
    PiettoParser.INDENT: "indentation",
    PiettoParser.DEDENT: "end of block",
}
_EXPECTED_DISPLAY = {
    Token.EOF: "end of file",
    PiettoParser.NEWLINE: "end of line",
    PiettoParser.INDENT: "an indented block",
    PiettoParser.DEDENT: "end of block",
    PiettoParser.IDENTIFIER: "a name",
    PiettoParser.NUMBER: "a number",
    PiettoParser.STRING: "a string",
}
# Characters echoed from source that a terminal could act on or hide.
_INVISIBLE = frozenset(
    "\u061c\u200e\u200f\u2028\u2029\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\ufeff"
)
# Relation clause words, and how a clause-order message names them.
_CLAUSE_WORDS = {
    PiettoParser.FROM: "from",
    PiettoParser.LET: "let",
    PiettoParser.WHERE: "where",
    PiettoParser.GROUP: "group by",
    PiettoParser.SELECT: "select",
    PiettoParser.WINDOW: "window",
    PiettoParser.SATISFYING: "satisfying",
    PiettoParser.HAVING: "having",
    PiettoParser.QUALIFY: "qualify",
    PiettoParser.ORDER: "order by",
    PiettoParser.LIMIT: "limit",
    **dict.fromkeys(
        (
            PiettoParser.INNER,
            PiettoParser.LEFT,
            PiettoParser.CROSS,
            PiettoParser.RIGHT,
            PiettoParser.FULL,
            PiettoParser.SEMI,
            PiettoParser.ANTI,
            PiettoParser.ASOF,
        ),
        "join",
    ),
}
_JOIN_KINDS = frozenset(
    (
        PiettoParser.INNER,
        PiettoParser.LEFT,
        PiettoParser.CROSS,
        PiettoParser.RIGHT,
        PiettoParser.FULL,
        PiettoParser.SEMI,
        PiettoParser.ANTI,
    )
)
_ASOF_KIND_HINT = "Write `asof left join` or `asof inner join`."
# The kinds an asof JOIN line admits where a parse error stands in their place.
_ASOF_KIND_TYPES = frozenset((PiettoParser.INNER, PiettoParser.LEFT))
_ASOF_LINE_HINT = "Write the asof `on` on one line."
_RELATION_BODY_CONTEXTS = (
    PiettoParser.TableBodyContext,
    PiettoParser.TableDefinitionContext,
    PiettoParser.QueryDefinitionContext,
    PiettoParser.LetRelationDefinitionContext,
)
_CLAUSE_ORDER = (
    "a relation body lists from, joins, let, where, group by, select, having, "
    "qualify, order by and limit in that order."
)
# Habits from SQL and other languages, recognized from the offending token.
_WORD_HINTS = {
    "over": "Write a window function as `rank() window(order by ...)` or "
    "`rank() window name`, not OVER (...).",
    "case": "Write `a if condition else b` instead of CASE.",
    "with": "Write a relation let `let x:` at the start of the body instead of "
    "WITH (EXPLICIT_MODULES projects).",
}
# Keywords that modern source spells another way, or not at all (`via`), so
# capitals such as NULL or BETWEEN are not answered with their lowercase.
_RETIRED_WORDS: dict[str, str | None] = {
    "null": "None",
    "true": "True",
    "false": "False",
    "between": "lower <= value <= upper",
    "cast": "Float(value)",
    "nullable": "T | None",
    "satisfying": "having",
    "via": None,
}
_SUBQUERY_HINT = (
    "A subquery is not written in parentheses: declare it as a relation let "
    "`let x:` at the start of the body and read it with `in x`, `exists x` or "
    "`scalar x.c` (EXPLICIT_MODULES projects)."
)
_FROM_HINT = (
    "A FROM reads a named relation: declare a subquery as a relation let "
    "`let x:` at the start of the body and write `from x` (EXPLICIT_MODULES "
    "projects)."
)
# The `||` hint, and the 0.1.7 one where `concat` names a callable of the
# program's own (`declares_concat`), not the builtin.
PIPE_HINT = "Write `concat(a, b)` to join Text, or `or` for a condition."
UNJOINED_PIPE_HINT = "String concatenation with `||` is not supported yet."
_CALLABLE_KEYWORDS = frozenset(
    {
        PiettoParser.DEF,
        PiettoParser.CONSTRAINT,
        PiettoParser.DERIVE,
        PiettoParser.RELATIONSHIP,
    }
)
# Words that an expression follows, so a '(' after them is not a call's;
# `exists` and `scalar` read a relation, as a subquery would.
_EXPRESSION_WORDS = frozenset(
    {
        "else",
        "ensure",
        "exists",
        "if",
        "in",
        "is",
        "limit",
        "on",
        "return",
        "scalar",
        "when",
        "where",
    }
)
# Clause headers whose block needs ':' at the end of the header line.
_BLOCK_HEADERS = frozenset(
    {
        PiettoParser.SELECT,
        PiettoParser.DISTINCT,
        PiettoParser.BY,
        PiettoParser.LET,
        PiettoParser.SATISFYING,
        # Not QUALIFY: its condition never follows `qualify:` on that line.
    }
)


def _first_sets() -> tuple[
    frozenset[int], frozenset[int], frozenset[int], frozenset[int], frozenset[int]
]:
    """FIRST sets of an expression, an operand, a name, a declaration and a
    header."""

    atn = PiettoParser.atn

    def first(*rules: int) -> frozenset[int]:
        return frozenset(
            token
            for rule in rules
            for token in atn.nextTokens(atn.ruleToStartState[rule])
        )

    return (
        first(PiettoParser.RULE_expression),
        first(PiettoParser.RULE_additiveExpression),
        first(PiettoParser.RULE_namePart),
        first(
            PiettoParser.RULE_definition,
            PiettoParser.RULE_relationshipDefinition,
            PiettoParser.RULE_moduleStatement,
        ),
        first(PiettoParser.RULE_header),
    )


(
    _EXPRESSION_FIRST,
    _OPERAND_FIRST,
    _NAME_FIRST,
    _DECLARATION_FIRST,
    _HEADER_FIRST,
) = _first_sets()


def quoted_source_text(text: str) -> str:
    """Quote source text on one line, escaping controls and invisible marks."""

    escaped: list[str] = []
    for character in text:
        code = ord(character)
        if character in "\n\r\t":
            escaped.append({"\n": "\\n", "\r": "\\r", "\t": "\\t"}[character])
        elif code < 0x20 or code == 0x7F:
            # The CLI escapes C0 controls and DEL the same way.
            escaped.append(f"\\x{code:02x}")
        elif 0x80 <= code <= 0x9F or character in _INVISIBLE:
            escaped.append(f"\\u{code:04x}")
        else:
            escaped.append(character)
    return "'" + "".join(escaped) + "'"


def declares_concat(tokens: Sequence[Token]) -> bool:
    """Whether ``tokens`` declare a callable `concat`: a `def`, `constraint`,
    `derive` or relationship template of that name (`shadowed_builtin_names`),
    read from the tokens, so also in source that does not parse."""

    return any(
        keyword.type in _CALLABLE_KEYWORDS
        and name.text == "concat"
        and parenthesis.type == PiettoParser.LPAREN
        for keyword, name, parenthesis in zip(tokens, tokens[1:], tokens[2:])
    )


def with_unjoined_pipe_hints(
    diagnostics: Iterable[Diagnostic],
) -> tuple[Diagnostic, ...]:
    """``diagnostics`` with the 0.1.7 `||` hint, for the files of a
    schema_version = 1 project, one namespace, one of which declares a
    callable `concat` (`declares_concat`)."""

    return tuple(
        replace(
            item,
            message=item.message.removesuffix(PIPE_HINT) + UNJOINED_PIPE_HINT,
        )
        if item.code == "PIE-P1000" and item.message.endswith(PIPE_HINT)
        else item
        for item in diagnostics
    )


def _index(token: Token) -> int:
    """A token's stream index; a token the recovery invented has none."""

    return -1 if token.tokenIndex is None else token.tokenIndex


def token_display(token: Token) -> str:
    display = _TOKEN_DISPLAY.get(token.type)
    return display if display is not None else quoted_source_text(token.text or "")


def _out_of_order(clause: str) -> str:
    return f"Clause `{clause}` is out of order or repeated; {_CLAUSE_ORDER}"


def _expected_display(expected: Iterable[int]) -> str:
    """Name an expected-token set briefly: categories first, then tokens."""

    rest = set(expected)
    parts: list[str] = []
    if _OPERAND_FIRST <= rest:
        parts.append("an expression")
        rest -= _EXPRESSION_FIRST
    elif PiettoParser.IDENTIFIER in rest:
        parts.append("a name")
        rest -= _NAME_FIRST
    if _DECLARATION_FIRST <= rest:
        parts.append("a declaration")
        rest -= _DECLARATION_FIRST | _HEADER_FIRST
    literal_names = PiettoParser.literalNames
    for token_type in sorted(
        rest, key=lambda item: (item in _LAYOUT_TOKEN_TYPES, item)
    ):
        display = _EXPECTED_DISPLAY.get(token_type)
        if display is None and 0 < token_type < len(literal_names):
            display = literal_names[token_type]
        parts.append(display or PiettoParser.symbolicNames[token_type])
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " or " + parts[-1]


class SyntaxErrorReporter(DefaultErrorStrategy):
    """ANTLR's recovery, with messages phrased for a Pietto author.

    Errors are collected with their offending token index, so the parser API
    keeps one per declaration; a message names the offending token, an
    expected-token set by category, and a hint for common habits. An error
    at a synthetic end-of-block or end-of-file token is located just after
    the last source token before it.
    """

    def __init__(self, path: str | Path | None, tokens: list[Token]) -> None:
        super().__init__()
        self.path = source_path(path)
        # The parsed token list; a stream token's index is its position here.
        self.tokens = tokens
        self.errors: list[tuple[int, Diagnostic]] = []

    def reportNoViableAlternative(self, recognizer: Any, e: Any) -> None:
        token = e.offendingToken
        # The decision's expected set describes its first token, so it also
        # fits an offending token that only blank lines precede.
        between = self.tokens[_index(e.startToken) : _index(token)]
        layout_only = all(item.type in _LAYOUT_TOKEN_TYPES for item in between)
        expected = recognizer.getExpectedTokens() if layout_only else None
        self._record(recognizer, token, expected)

    def reportInputMismatch(self, recognizer: Any, e: Any) -> None:
        self._record(recognizer, e.offendingToken, e.getExpectedTokens())

    def reportFailedPredicate(self, recognizer: Any, e: Any) -> None:
        self._record(recognizer, e.offendingToken, None)

    def reportUnwantedToken(self, recognizer: Any) -> None:
        if self.inErrorRecoveryMode(recognizer):
            return
        self.beginErrorCondition(recognizer)
        token = recognizer.getCurrentToken()
        self._record(recognizer, token, self.getExpectedTokens(recognizer))

    def reportMissingToken(self, recognizer: Any) -> None:
        if self.inErrorRecoveryMode(recognizer):
            return
        self.beginErrorCondition(recognizer)
        token = recognizer.getCurrentToken()
        expected = frozenset(self.getExpectedTokens(recognizer))
        if expected & _LAYOUT_TOKEN_TYPES:
            # A missing line or block end is an unexpected token to an author.
            self._record(recognizer, token, expected)
            return
        if self._asof_kind_slot(token):
            expected = _ASOF_KIND_TYPES
        asof = self._asof_hint(token)
        message = (
            f"Missing {_expected_display(expected)} before {token_display(token)}."
        )
        if self._from_parenthesis(recognizer, token):
            message += " " + _FROM_HINT
        if asof is not None:
            message += " " + asof
        self._append(token, message)

    def report_out_of_order(self, token: Token) -> None:
        """Report a relation step that parses but stands out of its order.

        The steps after FROM parse as one list; the parser API reports a step
        that the list's order does not admit as the parser reports a clause.
        """

        self._append(token, _out_of_order(_CLAUSE_WORDS[token.type]))

    def _token(self, index: int) -> Token | None:
        return self.tokens[index] if 0 <= index < len(self.tokens) else None

    def _line_start(self, index: int) -> int:
        """The index of the first token of the logical line holding ``index``."""

        return self._line_starts[index] if 0 <= index < len(self.tokens) else index

    @cached_property
    def _line_starts(self) -> list[int]:
        """The first token of each token's logical line, in one pass, so a
        message costs the same however long its line is."""

        starts: list[int] = []
        start = 0
        for index, token in enumerate(self.tokens):
            starts.append(start)
            if token.type in _LAYOUT_TOKEN_TYPES:
                start = index + 1
        return starts

    def _asof_hint(self, token: Token) -> str | None:
        """A hint for an asof JOIN line written in another form."""

        index = _index(token)
        start = self._line_start(index)
        first = self._token(start)
        previous = self._token(index - 1)
        if (
            token.type == PiettoParser.ASOF
            and previous is not None
            and previous.type in _JOIN_KINDS
            and start == index - 1
        ):
            if previous.type in {PiettoParser.INNER, PiettoParser.LEFT}:
                return (
                    f"Write `asof {previous.text} join NAME on ...`; `asof` "
                    "comes before the kind."
                )
            return _ASOF_KIND_HINT
        if first is None or first.type != PiettoParser.ASOF or start == index:
            return None
        if token.type == PiettoParser.JOIN and index == start + 1:
            return _ASOF_KIND_HINT
        if not self._asof_join_line(start):
            # `asof` stays a name: a line that only starts with it keeps its
            # own message.
            return None
        kind = self._token(start + 1)
        target = self._token(start + 3)
        if token.type == PiettoParser.AS and kind is not None and target is not None:
            alias = self._token(index + 1)
            name = "p" if alias is None or not alias.text else alias.text
            return (
                f"First `let {name} = {target.text}`, then "
                f"`asof {kind.text} join {name} on ...`."
            )
        if token.type == PiettoParser.BY and target is not None:
            earlier = self._from_binding(start)
            return (
                f"Match keys in `on`: `on {earlier}.k == {target.text}.k and "
                f"{earlier}.t >= {target.text}.t`."
            )
        if token.type == PiettoParser.NEWLINE:
            return _ASOF_LINE_HINT
        return None

    def _asof_kind_slot(self, token: Token) -> bool:
        """Whether ``token`` stands where a line-initial `asof ... join` has
        its kind, which only `inner` or `left` fills."""

        index = _index(token)
        asof, following = self._token(index - 1), self._token(index + 1)
        return (
            asof is not None
            and asof.type == PiettoParser.ASOF
            and self._line_start(index) == index - 1
            and (
                token.type == PiettoParser.JOIN
                or (following is not None and following.type == PiettoParser.JOIN)
            )
        )

    def _asof_join_line(self, start: int) -> bool:
        """Whether the logical line at ``start`` begins `asof <kind> join`."""

        kind, join = self._token(start + 1), self._token(start + 2)
        return (
            self.tokens[start].type == PiettoParser.ASOF
            and kind is not None
            and kind.type in _JOIN_KINDS
            and join is not None
            and join.type == PiettoParser.JOIN
        )

    def _asof_name_step(self, recognizer: Any, token: Token) -> Token | None:
        """The line-initial `asof` of a relation step that is no JOIN, such as
        `asof = 1`: the grammar reads it as an asof JOIN missing its kind, but
        the author wrote a name, as before `asof` was a word."""

        index = _index(token)
        asof, before = self._token(index - 1), self._token(index - 2)
        following = self._token(index + 1)
        if (
            isinstance(recognizer._ctx, PiettoParser.JoinKindContext)
            and asof is not None
            and asof.type == PiettoParser.ASOF
            and (before is None or before.type in _LAYOUT_TOKEN_TYPES)
            and token.type != PiettoParser.JOIN
            and (following is None or following.type != PiettoParser.JOIN)
        ):
            return asof
        return None

    def _from_binding(self, index: int) -> str:
        """The FROM input named on the nearest `from` line before ``index``."""

        while index > 0:
            index -= 1
            token = self.tokens[index]
            if token.type == PiettoParser.FROM and self._line_start(index) == index:
                following = self._token(index + 1)
                if following is not None and following.text:
                    return following.text
        return "earlier"

    def _from_parenthesis(self, recognizer: Any, token: Token) -> bool:
        """Whether ``token`` is a '(' where a FROM clause expects its relation.

        ANTLR reports it as missing or unexpected depending on the token after
        it, so both reports ask here.
        """

        previous = self._token(_index(token) - 1)
        return (
            token.type == PiettoParser.LPAREN
            and previous is not None
            and previous.type == PiettoParser.FROM
            # The name is a rule of its own inside the FROM clause.
            and isinstance(recognizer._ctx.parentCtx, PiettoParser.FromClauseContext)
        )

    @cached_property
    def _declares_concat(self) -> bool:
        """Whether the file declares a callable `concat`; as for
        `_parenthesized`, the first message that asks makes the one pass."""

        return declares_concat(self.tokens)

    @cached_property
    def _parenthesized(self) -> list[bool]:
        """Whether a '(' still open on its logical line precedes each token.

        Line breaks inside parentheses are not tokens, so every layout token
        starts the count again.  The first message that asks makes the one
        pass, so a message costs the same however long its line is.
        """

        inside: list[bool] = []
        depth = 0
        for token in self.tokens:
            inside.append(depth > 0)
            if token.type in _LAYOUT_TOKEN_TYPES:
                depth = 0
            elif token.type == PiettoParser.LPAREN:
                depth += 1
            elif token.type == PiettoParser.RPAREN and depth:
                depth -= 1
        return inside

    def _subquery(self, token: Token) -> bool:
        """Whether ``token`` is where a query written in parentheses fails.

        A field may be named select, from or with, so only these count, read
        up to ``token`` and the token after it: `(select` and an operand or
        ':', `(select * from` and a name, `(with` and a name before `as`, or
        `(from` and a name before `as` or a relation clause, in parentheses
        that do not hold a call's or a cast's arguments.  Reading these few
        tokens keeps the cost of a message the same however long its line is.
        """

        index = _index(token)
        words = tuple(
            (item.text or "").lower()
            for item in self.tokens[max(index - 4, 0) : max(index, 0)]
        )
        after = self._token(index + 1)
        name = token.type in _NAME_FIRST
        if words[-4:] == ("(", "select", "*", "from"):
            parenthesis, query = index - 4, name
        elif words[-2:] == ("(", "select"):
            parenthesis = index - 2
            query = token.type in _OPERAND_FIRST or token.type == PiettoParser.COLON
        elif words[-2:] == ("(", "with"):
            parenthesis = index - 2
            query = name and after is not None and (after.text or "").lower() == "as"
        elif words[-2:] == ("(", "from"):
            parenthesis = index - 2
            query = (
                name
                and after is not None
                and (after.type in _CLAUSE_WORDS or after.type == PiettoParser.AS)
            )
        else:
            return False
        before = self._token(parenthesis - 1)
        return query and not (
            before is not None
            and before.type in _NAME_FIRST
            and (before.text or "").lower() not in _EXPRESSION_WORDS
        )

    def _record(self, recognizer: Any, token: Token, expected: Any) -> None:
        previous = self._token(_index(token) - 1)
        line_start = previous is None or previous.type in _LAYOUT_TOKEN_TYPES
        expected_types = frozenset(expected) if expected is not None else frozenset()
        if {PiettoParser.RPAREN, PiettoParser.COMMA} <= expected_types:
            # A generator's `for` may follow the first argument of a call; the
            # message names a call's ordinary continuations only.
            expected_types -= {PiettoParser.FOR}
        clause = _CLAUSE_WORDS.get(token.type)
        if token.type == PiettoParser.ASOF and not self._asof_join_line(_index(token)):
            # `asof` stays a name: only `asof <kind> join` is a JOIN line.
            clause = None
        body_line = line_start and isinstance(recognizer._ctx, _RELATION_BODY_CONTEXTS)
        name = self._asof_name_step(recognizer, token)
        if name is not None:
            token, message = (
                name,
                f"Unknown clause {token_display(name)}; {_CLAUSE_ORDER}",
            )
        elif body_line and clause is not None:
            message = _out_of_order(clause)
        elif body_line and token.type not in _LAYOUT_TOKEN_TYPES:
            message = f"Unknown clause {token_display(token)}; {_CLAUSE_ORDER}"
            hint = self._hint(recognizer, token, previous, expected_types, line_start)
            if hint is not None:
                message += " " + hint
        elif token.type == PiettoParser.INDENT:
            message = UNEXPECTED_INDENTATION
            if self._asof_join_line(self._line_start(max(_index(token) - 1, 0))):
                message += " " + _ASOF_LINE_HINT
        elif PiettoParser.INDENT in expected_types and expected_types <= {
            PiettoParser.INDENT,
            PiettoParser.NEWLINE,
        }:
            message = "Expected an indented block after ':'."
        elif PiettoParser.SELECT in expected_types and token.type in {
            PiettoParser.DEDENT,
            Token.EOF,
        }:
            message = "Missing `select:` clause; " + _CLAUSE_ORDER
        else:
            if self._asof_kind_slot(token):
                expected_types = _ASOF_KIND_TYPES
            message = f"Unexpected {token_display(token)}"
            if expected_types:
                message += f"; expected {_expected_display(expected_types)}"
            message += "."
            hint = self._hint(recognizer, token, previous, expected_types, line_start)
            if hint is not None:
                message += " " + hint
        self._append(token, message)

    def _hint(
        self,
        recognizer: Any,
        token: Token,
        previous: Token | None,
        expected: frozenset[int],
        line_start: bool,
    ) -> str | None:
        """A hint for a habit from SQL or another language, if one applies."""

        text = token.text or ""
        following = self._token(_index(token) + 1)
        asof = self._asof_hint(token)
        if asof is not None:
            return asof
        if token.type == PiettoParser.WINDOW and isinstance(
            recognizer._ctx, PiettoParser.SelectLineContext
        ):
            return "A window call is a whole `select:` item on a line of its own."
        let = self._token(_index(token) - 3)
        if (
            token.type == PiettoParser.WINDOW
            and previous is not None
            and previous.type == PiettoParser.ASSIGN
            and let is not None
            and let.type == PiettoParser.LET
        ):
            return (
                "A named window is a `let` among the lets after FROM and every "
                "JOIN, before `where`, `group by` and `select`."
            )
        if token.type == PiettoParser.ASSIGN and (
            PiettoParser.NEWLINE in expected or PiettoParser.EQ in expected
        ):
            return (
                "Compare with `==`; `=` only names a select output, a let "
                "binding or a type argument."
            )
        if token.type == PiettoParser.NEWLINE and _OPERAND_FIRST <= expected:
            return "A line break ends the clause unless it is inside parentheses."
        if token.type == PiettoParser.AS:
            return "Name a select output with `name = expression`."
        if token.type == PiettoParser.JOIN:
            return (
                "A JOIN starts with its kind: `inner`, `left`, `cross`, "
                "`right` or `full`."
            )
        # D71.02: a table-function Unnest in a JOIN points to the Unnest let.
        joined = self._token(_index(token) - 2)
        if (
            token.type == PiettoParser.LPAREN
            and previous is not None
            and previous.text == "unnest"
            and joined is not None
            and joined.type == PiettoParser.JOIN
        ):
            return (
                "Write `let o = unnest(binding.field)` before the JOIN, then join `o`."
            )
        if token.type == PiettoParser.UNKNOWN and not text.isascii():
            return "Names use ASCII letters, digits and `_`."
        if token.type == PiettoParser.STAR and (
            not expected or _OPERAND_FIRST <= expected
        ):
            return "`*` is not supported; write `count()` or list the fields."
        if (
            token.type == PiettoParser.GT
            and previous is not None
            and previous.type == PiettoParser.LT
        ):
            return "Write `!=` for not-equal."
        if (
            token.type == PiettoParser.MINUS
            and line_start
            and following is not None
            and following.type == PiettoParser.MINUS
        ):
            return "Comments start with `#`."
        if token.type == PiettoParser.UNKNOWN and text == ";":
            return "Lines do not end with `;`."
        if (
            token.type == PiettoParser.PIPE
            and following is not None
            and following.type == PiettoParser.PIPE
        ):
            return UNJOINED_PIPE_HINT if self._declares_concat else PIPE_HINT
        before = self._token(_index(token) - 2)
        if (
            previous is not None
            and previous.type == PiettoParser.DISTINCT
            and before is not None
            and before.type == PiettoParser.LPAREN
        ):
            return "Write `count_distinct(x)` for COUNT(DISTINCT x)."
        if self._from_parenthesis(recognizer, token):
            return _FROM_HINT
        if self._subquery(token):
            return _SUBQUERY_HINT
        if (
            previous is not None
            and previous.type == PiettoParser.LPAREN
            and before is not None
            and before.type == PiettoParser.VALUES
        ):
            return (
                "A VALUES body has a typed header, `values(id: Int, "
                "label: Text | None):`, and one row per line below it "
                "(EXPLICIT_MODULES projects)."
            )
        if (
            isinstance(recognizer._ctx, PiettoParser.QualifyClauseContext)
            and previous is not None
            and previous.type in {PiettoParser.QUALIFY, PiettoParser.COLON}
        ):
            # Unlike the other clause headers, `qualify:` takes only a block.
            return (
                "Write the `qualify:` condition in an indented block on the next line."
            )
        if (
            previous is not None
            and previous.type in _BLOCK_HEADERS
            and not self._parenthesized[_index(token)]
        ):
            # A header word (the `select`, `group`, `order` or `partition`
            # before `distinct` or `by`) heads a clause only where it starts a
            # line, not inside an expression, as in `(select ...)`.
            header = (
                before
                if previous.type in {PiettoParser.BY, PiettoParser.DISTINCT}
                else previous
            )
            ahead = None if header is None else self._token(_index(header) - 1)
            if header is not None and (
                ahead is None or ahead.type in _LAYOUT_TOKEN_TYPES
            ):
                return (
                    "A clause lists its items on its header line, or in an "
                    "indented block after ':'."
                )
        if previous is not None and (previous.text or "").lower() == "case":
            return _WORD_HINTS["case"]
        if token.type == PiettoParser.IDENTIFIER:
            lowered = text.lower()
            # `collect` is a word only in a Collect item (D71.01), so `Collect`
            # keeps the message it had before that word existed.
            if (
                lowered != text
                and lowered != "collect"
                and f"'{lowered}'" in PiettoParser.literalNames
            ):
                if lowered in _RETIRED_WORDS:
                    modern = _RETIRED_WORDS[lowered]
                    return None if modern is None else f"Write `{modern}`."
                return f"Keywords are lowercase: write `{lowered}`."
            if lowered == "with" and not line_start:
                # A common table expression starts a line; a WITH later in a
                # line, as in `with time zone`, is other SQL.
                return None
            if lowered in _WORD_HINTS:
                return _WORD_HINTS[lowered]
        # D71.01: a select line that goes wrong right after the word `collect`
        # points to the Collect item, unless a hint above explains the token.
        if (
            previous is not None
            and previous.type == PiettoParser.COLLECT
            and isinstance(recognizer._ctx, PiettoParser.SelectLineContext)
        ):
            return "A Collect read is a whole select item: `name = collect relation`."
        if self._asof_kind_slot(token):
            return _ASOF_KIND_HINT
        return None

    def _append(self, token: Token, message: str) -> None:
        line, column = token.line, token.column + 1
        if token.type in {PiettoParser.DEDENT, Token.EOF}:
            # Synthetic block ends sit at the next line's token or past the
            # last line; point just after the last source token instead.
            index = _index(token) - 1
            while index >= 0 and self.tokens[index].type in _LAYOUT_TOKEN_TYPES:
                index -= 1
            if index >= 0:
                last = self.tokens[index]
                line, column = last.line, last.column + len(last.text or "") + 1
        self.errors.append(
            (
                _index(token),
                Diagnostic(
                    code="PIE-P1000",
                    severity=Severity.ERROR,
                    message=message,
                    location=SourceLocation(path=self.path, line=line, column=column),
                ),
            )
        )
