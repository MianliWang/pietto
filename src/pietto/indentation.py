from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from antlr4.Token import CommonToken, Token

from pietto.errors import Diagnostic, Severity, SourceLocation, source_path


@dataclass(frozen=True, slots=True)
class IndentationResult:
    tokens: tuple[Token, ...]
    diagnostics: tuple[Diagnostic, ...]


def find_leading_tab_diagnostics(
    source: str,
    *,
    path: str | Path | None,
) -> tuple[Diagnostic, ...]:
    diagnostics: list[Diagnostic] = []
    path_text = source_path(path)

    for line_number, line in enumerate(source.splitlines(), start=1):
        leading = line[: len(line) - len(line.lstrip(" \t"))]
        tab_column = leading.find("\t")
        if tab_column >= 0:
            diagnostics.append(
                Diagnostic(
                    code="P1004",
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


def inject_indentation(
    tokens: Sequence[Token],
    *,
    newline_type: int,
    indent_type: int,
    dedent_type: int,
    path: str | Path | None,
) -> IndentationResult:
    output: list[Token] = []
    diagnostics: list[Diagnostic] = []
    indentation_stack = [0]
    path_text = source_path(path)

    for index, token in enumerate(tokens):
        if token.type == Token.EOF:
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
        if next_token is None or next_token.type in {newline_type, Token.EOF}:
            continue

        indentation = _trailing_indentation(token.text or "")
        width = len(indentation.replace("\t", " "))
        previous = indentation_stack[-1]

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
                    code="P1003",
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


def _trailing_indentation(text: str) -> str:
    newline_index = max(text.rfind("\n"), text.rfind("\r"))
    return text[newline_index + 1 :] if newline_index >= 0 else ""


def _synthetic_token(anchor: Token, token_type: int, text: str) -> CommonToken:
    token = CommonToken(type=token_type)
    token.text = text
    token.line = anchor.line
    token.column = anchor.column
    token.start = anchor.start
    token.stop = anchor.start - 1
    return token
