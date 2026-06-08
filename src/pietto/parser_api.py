from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from antlr4 import CommonTokenStream, InputStream
from antlr4.ListTokenSource import ListTokenSource
from antlr4.Token import Token

from pietto.ast_builder import AstBuilder
from pietto.ast_nodes import Script
from pietto.errors import (
    Diagnostic,
    DiagnosticErrorListener,
    Severity,
    SourceLocation,
    source_path,
)
from pietto.generated.PiettoLexer import PiettoLexer
from pietto.generated.PiettoParser import PiettoParser
from pietto.indentation import (
    find_leading_tab_diagnostics,
    inject_indentation,
)


@dataclass(frozen=True, slots=True)
class ParseResult:
    ast: Script | None
    diagnostics: tuple[Diagnostic, ...]


def parse_source(
    source: str,
    *,
    path: str | Path | None = None,
) -> ParseResult:
    lexer_listener = DiagnosticErrorListener(path)
    lexer = PiettoLexer(InputStream(source))
    lexer.removeErrorListeners()
    lexer.addErrorListener(lexer_listener)
    raw_tokens = _read_tokens(lexer)

    diagnostics = list(lexer_listener.diagnostics)
    diagnostics.extend(find_leading_tab_diagnostics(source, path=path))
    diagnostics.extend(_brace_diagnostics(raw_tokens, path=path))

    indentation = inject_indentation(
        raw_tokens,
        newline_type=PiettoLexer.NEWLINE,
        indent_type=PiettoParser.INDENT,
        dedent_type=PiettoParser.DEDENT,
        path=path,
    )
    diagnostics.extend(indentation.diagnostics)

    parser_listener = DiagnosticErrorListener(path)
    token_stream = CommonTokenStream(
        ListTokenSource(list(indentation.tokens), source_path(path))
    )
    parser = PiettoParser(token_stream)
    parser.removeErrorListeners()
    parser.addErrorListener(parser_listener)
    tree = parser.script()
    diagnostics.extend(parser_listener.diagnostics)

    ordered_diagnostics = tuple(
        sorted(
            diagnostics,
            key=lambda item: (
                item.location.line,
                item.location.column,
                item.code,
            ),
        )
    )
    if any(item.severity is Severity.ERROR for item in ordered_diagnostics):
        return ParseResult(ast=None, diagnostics=ordered_diagnostics)

    return ParseResult(
        ast=AstBuilder(path).visit(tree),
        diagnostics=ordered_diagnostics,
    )


def parse_file(path: str | Path) -> ParseResult:
    source_path_value = Path(path)
    return parse_source(
        source_path_value.read_text(encoding="utf-8"),
        path=source_path_value,
    )


def _read_tokens(lexer: PiettoLexer) -> list[Token]:
    tokens: list[Token] = []
    while True:
        token = lexer.nextToken()
        tokens.append(token)
        if token.type == Token.EOF:
            return tokens


def _brace_diagnostics(
    tokens: list[Token],
    *,
    path: str | Path | None,
) -> tuple[Diagnostic, ...]:
    path_text = source_path(path)
    return tuple(
        Diagnostic(
            code="P1005",
            severity=Severity.ERROR,
            message="Braces are not supported as Pietto block delimiters.",
            location=SourceLocation(
                path=path_text,
                line=token.line,
                column=token.column + 1,
            ),
            suggestion="Use a colon followed by an indented block.",
        )
        for token in tokens
        if token.type in {PiettoLexer.LBRACE, PiettoLexer.RBRACE}
    )
