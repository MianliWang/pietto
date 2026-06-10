"""Public Pietto parsing facade that keeps ANTLR objects internal."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from antlr4 import CommonTokenStream, InputStream
from antlr4.ListTokenSource import ListTokenSource
from antlr4.Token import Token

from pietto.ast_builder import AstBuilder
from pietto.ast_nodes import Script
from pietto.errors import (
    AstBuildError,
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

_MAX_SOURCE_UTF8_BYTES = 1_048_576
_MAX_NON_EOF_TOKENS = 200_000
_SOURCE_SIZE_CHUNK_CHARACTERS = 65_536


@dataclass(frozen=True, slots=True)
class ParseResult:
    """The AST and structured diagnostics produced by a parse attempt."""

    ast: Script | None
    diagnostics: tuple[Diagnostic, ...]


def parse_source(
    source: str,
    *,
    path: str | Path | None = None,
) -> ParseResult:
    """Parse source text into a Pietto AST without exposing ANTLR objects.

    Source errors, budget failures, and parser recursion exhaustion produce
    structured diagnostics.
    """

    if _source_exceeds_utf8_budget(source):
        return _budget_failure(
            code="PIE-P1006",
            message=(
                "Source exceeds the maximum supported size of "
                f"{_MAX_SOURCE_UTF8_BYTES} UTF-8 bytes."
            ),
            path=path,
            line=1,
            column=1,
        )

    try:
        return _parse_source(source, path=path)
    except RecursionError:
        return ParseResult(
            ast=None,
            diagnostics=(
                Diagnostic(
                    code="PIE-P1000",
                    severity=Severity.ERROR,
                    message="Parser recursion limit exceeded while processing source.",
                    location=SourceLocation(
                        path=source_path(path),
                        line=1,
                        column=1,
                    ),
                ),
            ),
        )


def _parse_source(
    source: str,
    *,
    path: str | Path | None,
) -> ParseResult:
    """Implement parsing inside the public recursion containment boundary."""

    lexer_listener = DiagnosticErrorListener(path)
    lexer = PiettoLexer(InputStream(source))
    lexer.removeErrorListeners()
    lexer.addErrorListener(lexer_listener)
    raw_tokens, token_budget_diagnostic = _read_tokens(lexer, path=path)
    if token_budget_diagnostic is not None:
        return ParseResult(ast=None, diagnostics=(token_budget_diagnostic,))

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

    try:
        ast = AstBuilder(path).visit(tree)
    except AstBuildError as error:
        build_diagnostic = Diagnostic(
            code="PIE-P1000",
            severity=Severity.ERROR,
            message=error.message,
            location=SourceLocation(
                path=source_path(path),
                line=error.line,
                column=error.column,
            ),
        )
        return ParseResult(
            ast=None,
            diagnostics=tuple(
                sorted(
                    (*ordered_diagnostics, build_diagnostic),
                    key=lambda item: (
                        item.location.line,
                        item.location.column,
                        item.code,
                    ),
                )
            ),
        )

    return ParseResult(ast=ast, diagnostics=ordered_diagnostics)


def parse_file(path: str | Path) -> ParseResult:
    """Read and parse a UTF-8 Pietto source file."""

    source_path_value = Path(path)
    with source_path_value.open("rb") as source_file:
        source_bytes = source_file.read(_MAX_SOURCE_UTF8_BYTES + 1)
    if len(source_bytes) > _MAX_SOURCE_UTF8_BYTES:
        return _budget_failure(
            code="PIE-P1006",
            message=(
                "Source exceeds the maximum supported size of "
                f"{_MAX_SOURCE_UTF8_BYTES} UTF-8 bytes."
            ),
            path=source_path_value,
            line=1,
            column=1,
        )
    return parse_source(source_bytes.decode("utf-8"), path=source_path_value)


def _read_tokens(
    lexer: PiettoLexer,
    *,
    path: str | Path | None,
) -> tuple[list[Token], Diagnostic | None]:
    """Materialize lexer tokens so indentation and token checks can share them."""

    tokens: list[Token] = []
    non_eof_count = 0
    while True:
        token = lexer.nextToken()
        if token.type == Token.EOF:
            tokens.append(token)
            return tokens, None
        non_eof_count += 1
        if non_eof_count > _MAX_NON_EOF_TOKENS:
            return [], Diagnostic(
                code="PIE-P1007",
                severity=Severity.ERROR,
                message=(
                    "Token count exceeds the maximum supported limit of "
                    f"{_MAX_NON_EOF_TOKENS} non-EOF tokens."
                ),
                location=SourceLocation(
                    path=source_path(path),
                    line=token.line,
                    column=token.column + 1,
                ),
            )
        tokens.append(token)


def _source_exceeds_utf8_budget(source: str) -> bool:
    """Count UTF-8 bytes in bounded chunks and stop at the configured limit."""

    if len(source) > _MAX_SOURCE_UTF8_BYTES:
        return True

    encoded_size = 0
    for offset in range(0, len(source), _SOURCE_SIZE_CHUNK_CHARACTERS):
        chunk = source[offset : offset + _SOURCE_SIZE_CHUNK_CHARACTERS]
        encoded_size += len(chunk.encode("utf-8", errors="surrogatepass"))
        if encoded_size > _MAX_SOURCE_UTF8_BYTES:
            return True
    return False


def _budget_failure(
    *,
    code: str,
    message: str,
    path: str | Path | None,
    line: int,
    column: int,
) -> ParseResult:
    """Build one deterministic parser budget failure."""

    return ParseResult(
        ast=None,
        diagnostics=(
            Diagnostic(
                code=code,
                severity=Severity.ERROR,
                message=message,
                location=SourceLocation(
                    path=source_path(path),
                    line=line,
                    column=column,
                ),
            ),
        ),
    )


def _brace_diagnostics(
    tokens: list[Token],
    *,
    path: str | Path | None,
) -> tuple[Diagnostic, ...]:
    """Report brace tokens while ignoring braces lexed inside strings or comments."""

    path_text = source_path(path)
    return tuple(
        Diagnostic(
            code="PIE-P1005",
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
