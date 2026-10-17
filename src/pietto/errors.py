"""Structured parser diagnostics and internal AST construction errors."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
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
        ),
        "join",
    ),
}
_RELATION_BODY_CONTEXTS = (
    PiettoParser.TableBodyContext,
    PiettoParser.TableDefinitionContext,
    PiettoParser.QueryDefinitionContext,
    PiettoParser.LetRelationDefinitionContext,
)
_CLAUSE_ORDER = (
    "a relation body lists from, joins, let:, where, group by:, select:, "
    "windows, satisfying:, qualify:, order by: and limit in that order."
)
# Habits from SQL and other languages, recognized from the offending token.
_WORD_HINTS = {
    "having": "Filter groups with `satisfying:` after `select:`.",
    "over": "A window function takes `window:` with an indented block or "
    "`window name`, not OVER (...).",
    "case": "Write `a if condition else b` instead of CASE.",
}
# Clause headers whose block needs ':' at the end of the header line.
_BLOCK_HEADERS = frozenset(
    {
        PiettoParser.SELECT,
        PiettoParser.DISTINCT,
        PiettoParser.BY,
        PiettoParser.LET,
        PiettoParser.SATISFYING,
        PiettoParser.QUALIFY,
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


def _index(token: Token) -> int:
    """A token's stream index; a token the recovery invented has none."""

    return -1 if token.tokenIndex is None else token.tokenIndex


def token_display(token: Token) -> str:
    display = _TOKEN_DISPLAY.get(token.type)
    return display if display is not None else quoted_source_text(token.text or "")


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
        self._append(
            token,
            f"Missing {_expected_display(expected)} before {token_display(token)}.",
        )

    def _token(self, index: int) -> Token | None:
        return self.tokens[index] if 0 <= index < len(self.tokens) else None

    def _record(self, recognizer: Any, token: Token, expected: Any) -> None:
        previous = self._token(_index(token) - 1)
        line_start = previous is None or previous.type in _LAYOUT_TOKEN_TYPES
        expected_types = frozenset(expected) if expected is not None else frozenset()
        clause = _CLAUSE_WORDS.get(token.type)
        body_line = line_start and isinstance(recognizer._ctx, _RELATION_BODY_CONTEXTS)
        if body_line and clause is not None:
            message = f"Clause `{clause}` is out of order or repeated; {_CLAUSE_ORDER}"
        elif body_line and token.type not in _LAYOUT_TOKEN_TYPES:
            message = f"Unknown clause {token_display(token)}; {_CLAUSE_ORDER}"
            hint = self._hint(recognizer, token, previous, expected_types, line_start)
            if hint is not None:
                message += " " + hint
        elif token.type == PiettoParser.INDENT:
            message = UNEXPECTED_INDENTATION
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
        if token.type == PiettoParser.WINDOW and isinstance(
            recognizer._ctx, PiettoParser.SelectLineContext
        ):
            return "A window call is a whole `select:` item on a line of its own."
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
                "`right`, `full`, `semi` or `anti`."
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
        before = self._token(_index(token) - 2)
        if (
            previous is not None
            and previous.type == PiettoParser.DISTINCT
            and before is not None
            and before.type == PiettoParser.LPAREN
        ):
            return "Write `count_distinct(x)` for COUNT(DISTINCT x)."
        if previous is not None and previous.type in _BLOCK_HEADERS:
            return (
                "A clause header ends with ':'; its items follow on the same "
                "line or in an indented block."
            )
        if previous is not None and (previous.text or "").lower() == "case":
            return _WORD_HINTS["case"]
        if token.type == PiettoParser.IDENTIFIER:
            lowered = text.lower()
            if lowered != text and f"'{lowered}'" in PiettoParser.literalNames:
                return f"Keywords are lowercase: write `{lowered}`."
            return _WORD_HINTS.get(lowered)
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
