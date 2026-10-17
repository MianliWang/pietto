"""Handwritten Python-style INDENT/DEDENT support for Pietto tokens."""

from __future__ import annotations

import re

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from antlr4.Token import CommonToken, Token

from pietto.errors import (
    UNEXPECTED_INDENTATION,
    Diagnostic,
    Severity,
    SourceLocation,
    source_path,
)


@dataclass(frozen=True, slots=True)
class IndentationResult:
    """The transformed token stream and indentation diagnostics."""

    tokens: tuple[Token, ...]
    diagnostics: tuple[Diagnostic, ...]


def find_leading_tab_diagnostics(
    source: str,
    *,
    path: str | Path | None,
) -> tuple[Diagnostic, ...]:
    """Report tabs appearing in the leading indentation of source lines."""

    diagnostics: list[Diagnostic] = []
    path_text = source_path(path)

    # LF, CRLF and a lone CR each end one line, as for every other position.
    for line_number, line in enumerate(re.split(r"\r\n|\r|\n", source), start=1):
        leading = line[: len(line) - len(line.lstrip(" \t"))]
        tab_column = leading.find("\t")
        if tab_column >= 0:
            diagnostics.append(
                Diagnostic(
                    code="PIE-P1004",
                    severity=Severity.ERROR,
                    message="Tabs are not allowed in leading indentation.",
                    location=SourceLocation(
                        path=path_text,
                        line=line_number,
                        column=tab_column + 1,
                    ),
                    suggestion="Use spaces for indentation.",
                )
            )

    return tuple(diagnostics)


def join_parenthesized_lines(
    tokens: Sequence[Token],
    *,
    newline_type: int,
    open_type: int,
    close_type: int,
    window_type: int,
    colon_type: int,
    path: str | Path | None,
) -> IndentationResult:
    """Drop the line breaks inside parentheses, like Python implicit joining.

    Continuation lines inside ``(`` ... ``)`` carry no NEWLINE, so their
    indentation, blank lines and comments never reach the block logic; every
    token keeps its source position. An unmatched ``)`` is left to the parser.

    A window block (``window:`` or ``window name:`` ending a line) opened
    inside parentheses keeps its line breaks, as every parenthesized line
    break did before joining existed: joining resumes once those parentheses
    close, so such a QUALIFY operand parses exactly as it always did. A ``(``
    still open at EOF is reported; it makes the parser input meaningless.
    """

    output: list[Token] = []
    diagnostics: list[Diagnostic] = []
    open_parens: list[Token] = []
    # The depth of the parentheses whose window block keeps line breaks.
    kept_depth: int | None = None
    path_text = source_path(path)
    for token in tokens:
        if token.type == newline_type and open_parens:
            # ``window:`` or ``window name:`` ending a line opens a block.
            recent = [item.type for item in output[-3:]]
            if kept_depth is None and (
                recent[-2:] == [window_type, colon_type]
                or (recent[:1] == [window_type] and recent[-1:] == [colon_type])
            ):
                kept_depth = len(open_parens)
            if kept_depth is not None:
                output.append(token)
            continue
        if token.type == open_type:
            open_parens.append(token)
        elif token.type == close_type and open_parens:
            open_parens.pop()
            if kept_depth is not None and len(open_parens) < kept_depth:
                kept_depth = None
        elif token.type == Token.EOF and open_parens:
            diagnostics.append(
                _diagnostic(
                    "PIE-P1008", "'(' is never closed.", path_text, open_parens[-1]
                )
            )
        output.append(token)
    return IndentationResult(tokens=tuple(output), diagnostics=tuple(diagnostics))


def inject_indentation(
    tokens: Sequence[Token],
    *,
    newline_type: int,
    indent_type: int,
    dedent_type: int,
    path: str | Path | None,
) -> IndentationResult:
    """Insert synthetic block tokens using indentation captured by NEWLINE tokens."""

    # This ordered buffer acts as the pending-token queue later consumed by
    # ListTokenSource. Synthetic tokens are appended exactly where they belong.
    output: list[Token] = []
    diagnostics: list[Diagnostic] = []
    # Zero is the permanent baseline; nested block widths are pushed and popped.
    indentation_stack = [0]
    path_text = source_path(path)
    # An indented first code line is reported here, after any blank or comment
    # lines.  Its width opens no block: the rest of the file is measured as if
    # the line started at column 0, so a file indented as a whole can also get
    # a PIE-P1003 at a later line.
    code_seen = False
    first = tokens[0] if tokens else None
    if first is not None and first.type not in {newline_type, Token.EOF}:
        code_seen = True
        if first.column > 0:
            diagnostics.append(
                _diagnostic("PIE-P1000", UNEXPECTED_INDENTATION, path_text, first)
            )

    for index, token in enumerate(tokens):
        if token.type == Token.EOF:
            # A final logical newline lets the parser finish the last statement,
            # then every open indentation level is closed before EOF.
            if output and output[-1].type != newline_type:
                output.append(_synthetic_token(token, newline_type, "\n"))
            while len(indentation_stack) > 1:
                indentation_stack.pop()
                output.append(_synthetic_token(token, dedent_type, ""))
            output.append(token)
            continue

        output.append(token)
        if token.type != newline_type:
            continue

        next_token = tokens[index + 1] if index + 1 < len(tokens) else None
        # Comments are skipped by the lexer. Consecutive NEWLINE tokens therefore
        # represent blank or comment-only lines and must not change block depth.
        if next_token is None or next_token.type in {newline_type, Token.EOF}:
            continue

        indentation = _trailing_indentation(token.text or "")
        width = len(indentation.replace("\t", " "))
        previous = indentation_stack[-1]
        if not code_seen:
            code_seen = True
            if width > 0:
                diagnostics.append(
                    _diagnostic(
                        "PIE-P1000", UNEXPECTED_INDENTATION, path_text, next_token
                    )
                )
            continue

        if width > previous:
            indentation_stack.append(width)
            output.append(_synthetic_token(next_token, indent_type, indentation))
            continue

        if width == previous:
            continue

        while len(indentation_stack) > 1 and indentation_stack[-1] > width:
            indentation_stack.pop()
            output.append(_synthetic_token(next_token, dedent_type, ""))

        if indentation_stack[-1] != width:
            diagnostics.append(
                Diagnostic(
                    code="PIE-P1003",
                    severity=Severity.ERROR,
                    message="Indentation does not match an outer block.",
                    location=SourceLocation(
                        path=path_text,
                        line=next_token.line,
                        column=next_token.column + 1,
                    ),
                )
            )

    return IndentationResult(
        tokens=tuple(output),
        diagnostics=tuple(diagnostics),
    )


def _diagnostic(code: str, message: str, path: str | None, token: Token) -> Diagnostic:
    """Build one error diagnostic located at a source token."""

    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        location=SourceLocation(path=path, line=token.line, column=token.column + 1),
    )


def _trailing_indentation(text: str) -> str:
    """Extract indentation following the final line break in a NEWLINE token."""

    newline_index = max(text.rfind("\n"), text.rfind("\r"))
    return text[newline_index + 1 :] if newline_index >= 0 else ""


def _synthetic_token(anchor: Token, token_type: int, text: str) -> CommonToken:
    """Create a zero-width synthetic token anchored to a real source token."""

    token = CommonToken(type=token_type)
    token.text = text
    token.line = anchor.line
    token.column = anchor.column
    token.start = anchor.start
    token.stop = anchor.start - 1
    return token
