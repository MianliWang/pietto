"""Public Pietto parsing facade that keeps ANTLR objects internal."""

from __future__ import annotations

import bisect
from _thread import allocate_lock, start_new_thread
from threading import Event
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from antlr4 import CommonTokenStream, InputStream
from antlr4.ListTokenSource import ListTokenSource
from antlr4.Token import Token

from pietto.ast_builder import AstBuilder
from pietto.ast_nodes import Script
from pietto.errors import (
    AstBuildError,
    Diagnostic,
    DiagnosticErrorListener,
    ParseCancelled,
    Severity,
    SourceLocation,
    SyntaxErrorReporter,
    source_path,
)
from pietto.generated.PiettoLexer import PiettoLexer
from pietto.generated.PiettoParser import PiettoParser
from pietto.indentation import (
    find_leading_tab_diagnostics,
    inject_indentation,
    join_parenthesized_lines,
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

    if source.startswith("\ufeff"):
        source = source[1:]

    # The parse runs on a fresh low-level thread whose first frame is
    # ``contained``, so it reaches the parser two frames deep whoever calls,
    # and never deeper than a caller's own stack would.  The caller always
    # waits for it: an exception raised in the caller while it waits, such as
    # KeyboardInterrupt or a signal-based timeout, cancels the parse, which
    # stops at its next token or tree node, and is re-raised once the parse
    # has stopped, so no parse outlives its call.
    cancel = Event()
    finished = allocate_lock()
    finished.acquire()
    outcome: list[ParseResult | BaseException] = []

    def contained() -> None:
        try:
            outcome.append(_parse_source(source, path=path, cancel=cancel))
        except RecursionError:
            outcome.append(
                ParseResult(
                    ast=None, diagnostics=(_recursion_diagnostic(path, None, ()),)
                )
            )
        except BaseException as error:  # re-raised in the calling thread
            outcome.append(error)
        finally:
            finished.release()

    # ``extend`` stores the started thread's ident without running bytecode in
    # between, so ``started`` is empty exactly when no parse is running, even
    # when a signal handler raises as the start returns.
    started: list[int] = []
    try:
        started.extend(map(start_new_thread, (contained,), ((),)))
        finished.acquire()
    except BaseException as error:
        if not started:
            if isinstance(error, RuntimeError):
                # No thread is available: parse on the caller's own stack.
                return _contained_parse(source, path=path, cancel=cancel)
            raise
        cancel.set()
        finished.acquire()
        raise
    (result,) = outcome
    if isinstance(result, BaseException):
        raise result
    return result


def _contained_parse(
    source: str, *, path: str | Path | None, cancel: Event
) -> ParseResult:
    """Parse inside the recursion containment boundary."""

    try:
        return _parse_source(source, path=path, cancel=cancel)
    except RecursionError:
        return ParseResult(
            ast=None, diagnostics=(_recursion_diagnostic(path, None, ()),)
        )


def _parse_source(
    source: str,
    *,
    path: str | Path | None,
    cancel: Event,
) -> ParseResult:
    """Implement parsing inside the public recursion containment boundary.

    A lone CR ends a line for the lexer but, as before this rule existed, not
    for ANTLR's line counter, so a CR-only file keeps its positions on line 1.
    """

    lexer_listener = DiagnosticErrorListener(path)
    lexer = PiettoLexer(InputStream(source))
    lexer.removeErrorListeners()
    lexer.addErrorListener(lexer_listener)
    raw_tokens, token_budget_diagnostic = _read_tokens(lexer, path=path, cancel=cancel)
    if token_budget_diagnostic is not None:
        return ParseResult(ast=None, diagnostics=(token_budget_diagnostic,))

    diagnostics = list(lexer_listener.diagnostics)
    diagnostics.extend(find_leading_tab_diagnostics(source, path=path))
    diagnostics.extend(_brace_diagnostics(raw_tokens, path=path))
    unterminated = [
        token for token in raw_tokens if token.type == PiettoLexer.UNTERMINATED_STRING
    ]
    for token in unterminated:
        diagnostics.append(
            _token_diagnostic(
                "PIE-P1000",
                "Unterminated string literal; close it with a matching quote on "
                "the same line.",
                path,
                token,
            )
        )
        # Parsed as a string, the rest of its line raises no follow-on errors.
        token.type = PiettoLexer.STRING

    joined = join_parenthesized_lines(
        raw_tokens,
        newline_type=PiettoLexer.NEWLINE,
        open_type=PiettoLexer.LPAREN,
        close_type=PiettoLexer.RPAREN,
        window_type=PiettoLexer.WINDOW,
        colon_type=PiettoLexer.COLON,
        path=path,
    )
    if joined.diagnostics:
        # Parsing the rest of the file as one expression only adds noise; a
        # parenthesis whose close an unterminated string swallowed is not news.
        return ParseResult(
            ast=None,
            diagnostics=_source_ordered(
                (
                    *diagnostics,
                    *(
                        item
                        for item in joined.diagnostics
                        if not any(
                            (string.line, string.column + 1)
                            > (item.location.line, item.location.column)
                            and string.line == item.location.line
                            for string in unterminated
                        )
                    ),
                )
            ),
        )
    indentation = inject_indentation(
        joined.tokens,
        newline_type=PiettoLexer.NEWLINE,
        indent_type=PiettoParser.INDENT,
        dedent_type=PiettoParser.DEDENT,
        path=path,
    )
    diagnostics.extend(indentation.diagnostics)

    tokens = list(indentation.tokens)
    starts = _declaration_starts(tokens)
    # Parsed inline rather than in a helper: every frame here is one less for
    # the nesting the parser accepts.
    token_source = _CancellableTokenSource(tokens, source_path(path), cancel)
    # ANTLR accepts any token source here, but its runtime annotation names Lexer.
    parser = PiettoParser(CommonTokenStream(cast(Any, token_source)))
    parser.removeErrorListeners()
    reporter = SyntaxErrorReporter(path, tokens)
    parser._errHandler = reporter
    try:
        tree = parser.script()
    except RecursionError:
        return ParseResult(
            ast=None,
            diagnostics=(
                _recursion_diagnostic(
                    path, parser.getCurrentToken(), [tokens[index] for index in starts]
                ),
            ),
        )
    if reporter.errors:
        diagnostics.extend(
            _first_error_per_declaration(tokens, starts, reporter, diagnostics)
        )

    ordered_diagnostics = _source_ordered(diagnostics)
    if any(item.severity is Severity.ERROR for item in ordered_diagnostics):
        return ParseResult(ast=None, diagnostics=ordered_diagnostics)

    builder = AstBuilder(path, cancel=cancel)
    try:
        ast = builder.visit(tree)
    except RecursionError:
        return ParseResult(
            ast=None,
            diagnostics=(
                _recursion_diagnostic(
                    path, builder.deepest, [tokens[index] for index in starts]
                ),
            ),
        )
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
            diagnostics=_source_ordered((*ordered_diagnostics, build_diagnostic)),
        )

    return ParseResult(ast=ast, diagnostics=ordered_diagnostics)


class _CancellableTokenSource(ListTokenSource):
    """A token list whose parse stops once its caller cancels it."""

    def __init__(self, tokens: list[Token], name: str | None, cancel: Event):
        super().__init__(tokens, name)
        self._cancel = cancel

    def nextToken(self) -> Token:
        if self._cancel.is_set():
            raise ParseCancelled
        return super().nextToken()


def _declaration_starts(tokens: list[Token]) -> list[int]:
    """Indexes of the tokens that start a top-level declaration, in order.

    A declaration starts with the first token of a logical line at column 0.
    """

    layout = {Token.EOF, PiettoLexer.NEWLINE, PiettoParser.INDENT, PiettoParser.DEDENT}
    return [
        index
        for index, token in enumerate(tokens)
        if token.column == 0
        and token.type not in layout
        and (index == 0 or tokens[index - 1].type in layout)
    ]


def _first_error_per_declaration(
    tokens: list[Token],
    starts: list[int],
    reporter: SyntaxErrorReporter,
    source_errors: list[Diagnostic],
) -> list[Diagnostic]:
    """Keep the first parser error of each top-level declaration.

    Later errors in the same declaration are recovery noise, and a declaration
    whose source already has a brace, indentation or string error gets none:
    that error is the cause.  Both lookups bisect the sorted starts.
    """

    start_lines = [tokens[index].line for index in starts]
    blocked = {
        bisect.bisect_right(start_lines, item.location.line)
        for item in source_errors
        if item.code in {"PIE-P1003", "PIE-P1005"}
        or item.message.startswith("Unterminated string literal")
    }
    kept: list[Diagnostic] = []
    seen: set[int] = set()
    for token_index, item in sorted(reporter.errors, key=lambda pair: pair[0]):
        owner = bisect.bisect_right(starts, token_index)
        if owner in seen or owner in blocked:
            continue
        seen.add(owner)
        kept.append(item)
    return kept


def _recursion_diagnostic(
    path: str | Path | None, deepest: Token | None, starts: Sequence[Token]
) -> Diagnostic:
    """Report recursion exhaustion at the declaration that ran out of depth.

    The deepest token reached moves with the host's recursion limit; the start
    of its top-level declaration does not.
    """

    start: Token | None = None
    if deepest is not None:
        for candidate in starts:
            if (candidate.line, candidate.column) > (deepest.line, deepest.column):
                break
            start = candidate
    return Diagnostic(
        code="PIE-P1000",
        severity=Severity.ERROR,
        message="Parser recursion limit exceeded while processing source.",
        location=SourceLocation(
            path=source_path(path),
            line=1 if start is None else start.line,
            column=1 if start is None else start.column + 1,
        ),
    )


def _token_diagnostic(
    code: str, message: str, path: str | Path | None, token: Token
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        location=SourceLocation(
            path=source_path(path), line=token.line, column=token.column + 1
        ),
    )


def _source_ordered(diagnostics: Iterable[Diagnostic]) -> tuple[Diagnostic, ...]:
    """Order parser diagnostics by line, column and code."""

    return tuple(
        sorted(
            diagnostics,
            key=lambda item: (item.location.line, item.location.column, item.code),
        )
    )


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
    cancel: Event,
) -> tuple[list[Token], Diagnostic | None]:
    """Materialize lexer tokens so indentation and token checks can share them."""

    tokens: list[Token] = []
    non_eof_count = 0
    while True:
        if cancel.is_set():
            raise ParseCancelled
        token = lexer.nextToken()
        assert token is not None
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
