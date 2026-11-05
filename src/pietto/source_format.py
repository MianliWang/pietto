"""Lossless source formatting: only the whitespace between tokens changes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from antlr4 import InputStream
from antlr4.Token import Token

from pietto import parser_api
from pietto.errors import Diagnostic, DiagnosticErrorListener, Severity
from pietto.generated.PiettoLexer import PiettoLexer
from pietto.generated.PiettoParser import PiettoParser
from pietto.indentation import (
    IndentationResult,
    _trailing_indentation,
    find_leading_tab_diagnostics,
    inject_indentation,
    join_parenthesized_lines,
)
from pietto.source_migration import _line_ending

_LAYOUT = frozenset({PiettoLexer.NEWLINE, PiettoParser.INDENT, PiettoParser.DEDENT})
_HEADER = frozenset(
    {PiettoLexer.PIETTO, PiettoLexer.MODE, PiettoLexer.DIALECT, PiettoLexer.ENCODING}
)
_MODULE = frozenset({PiettoLexer.IMPORT, PiettoLexer.FROM, PiettoLexer.EXPORT})
_BLANKS = str.maketrans("", "", " \t\r\n")


@dataclass(frozen=True, slots=True)
class FormatResult:
    """The formatted source and the parser's diagnostics; the source is None
    when the input is refused."""

    source: str | None
    diagnostics: tuple[Diagnostic, ...]
    input_text: str = ""  # the source as read; empty when it is too large

    @property
    def changed(self) -> bool:
        return self.source is not None and self.source != self.input_text


class FormatRefusedError(ValueError):
    """The formatted source cannot be returned."""


@dataclass(frozen=True, slots=True)
class _Line:
    width: int  # the indentation as written
    code: str  # the tokens and the gaps between them, as written
    comment: str
    block: bool  # starts a logical line, unlike a line inside parentheses
    header: str | None  # a header line as written, without its line ending
    module: bool  # starts an import or export statement


def format_file(path: str | Path) -> FormatResult:
    """Read a bounded UTF-8 input and format it without changing the file."""

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
        return FormatResult(None, failure.diagnostics)
    return format_source(source.decode("utf-8"), path=path)


def format_source(source: str, *, path: str | Path | None = None) -> FormatResult:
    """Format a source that parses without errors; refuse any other.

    The result is lexed, joined and indented again and must give the input's
    tokens, blocks and logical lines without an error, every line its code
    and comment exactly as written, and the same text apart from spaces,
    tabs and line endings, so only indentation, blank lines, the spaces
    before a comment, trailing whitespace and line endings may differ, or
    FormatRefusedError is raised.
    """

    parsed = parser_api.parse_source(source, path=path)
    if _has_errors(parsed.diagnostics):
        return FormatResult(None, parsed.diagnostics, source)
    prefix = "\ufeff" if source.startswith("\ufeff") else ""
    body = source[len(prefix) :]
    raw, joined, errors = _tokens(body)
    expected = _effective_tokens(joined, errors)
    kept = {item.start for item in joined.tokens if item.type == PiettoLexer.NEWLINE}
    lines = _lines(body, raw, kept)
    formatted = prefix + _render(lines, _line_ending(body))
    if parser_api._source_exceeds_utf8_budget(formatted):
        raise FormatRefusedError(
            "the formatted source would exceed the maximum supported size of "
            f"{parser_api._MAX_SOURCE_UTF8_BYTES} UTF-8 bytes; "
            "nothing was printed or written"
        )
    output = formatted[len(prefix) :]
    output_raw, output_joined, output_errors = _tokens(output)
    if (
        expected is None
        or find_leading_tab_diagnostics(output, path=None)
        or _effective_tokens(output_joined, output_errors) != expected
        or _written(_lines(output, output_raw, set())) != _written(lines)
        or output.translate(_BLANKS) != body.translate(_BLANKS)
    ):
        raise FormatRefusedError(
            "formatting would not keep the source's tokens, comments and blocks; "
            "nothing was printed or written"
        )
    return FormatResult(formatted, parsed.diagnostics, source)


def _has_errors(diagnostics: tuple[Diagnostic, ...]) -> bool:
    return any(item.severity is Severity.ERROR for item in diagnostics)


def _tokens(
    body: str,
) -> tuple[list[Token], IndentationResult, tuple[Diagnostic, ...]]:
    """The lexer's tokens, those left once parentheses join their lines, and
    the lexer's errors."""

    listener = DiagnosticErrorListener(None)
    lexer = parser_api._PiettoLexer(InputStream(body))
    lexer.removeErrorListeners()
    lexer.addErrorListener(listener)
    raw, budget = parser_api._read_tokens(lexer, path=None)
    errors = (*listener.diagnostics, *((budget,) if budget is not None else ()))
    joined = join_parenthesized_lines(
        raw,
        newline_type=PiettoLexer.NEWLINE,
        open_type=PiettoLexer.LPAREN,
        close_type=PiettoLexer.RPAREN,
        window_type=PiettoLexer.WINDOW,
        colon_type=PiettoLexer.COLON,
        path=None,
    )
    return raw, joined, errors


def _effective_tokens(
    joined: IndentationResult, errors: tuple[Diagnostic, ...]
) -> list[tuple[int, str | None]] | None:
    """What the parser reads, where blank and comment lines add no NEWLINE;
    None when the source does not lex, join or indent cleanly. The lexer
    turns a character it does not know into an UNKNOWN token."""

    if (
        errors
        or joined.diagnostics
        or any(token.type == PiettoLexer.UNKNOWN for token in joined.tokens)
    ):
        return None
    indented = inject_indentation(
        joined.tokens,
        newline_type=PiettoLexer.NEWLINE,
        indent_type=PiettoParser.INDENT,
        dedent_type=PiettoParser.DEDENT,
        path=None,
    )
    if indented.diagnostics:
        return None
    effective: list[tuple[int, str | None]] = []
    previous: Token | None = None
    for token in indented.tokens:
        if token.type not in _LAYOUT:
            effective.append((token.type, token.text))
        elif token.type != PiettoLexer.NEWLINE or (
            previous is not None and previous.type != PiettoLexer.NEWLINE
        ):
            effective.append((token.type, None))
        previous = token
    return effective


def _lines(body: str, raw: list[Token], kept: set[int]) -> list[_Line]:
    """Split the source at its NEWLINE tokens, which ``kept`` names by start
    when they survive joining; comments are in the gaps. The header lines
    are the leading code lines that start with a header keyword."""

    lines: list[_Line] = []
    code: list[str] = []
    width, block, cursor, header, module = 0, True, 0, True, False
    for token in raw:
        gap = body[cursor : token.start]
        cursor = token.stop + 1
        if not code:
            stripped = gap.lstrip(" \t")
            width += len(gap) - len(stripped)
            gap = stripped
        if token.type in {PiettoLexer.NEWLINE, Token.EOF}:
            text = "".join(code)
            # A comment runs to the line end, so only this gap can hold one.
            written = text + gap if header and text else None
            lines.append(_Line(width, text, gap.strip(" \t"), block, written, module))
            width = len(_trailing_indentation(token.text or ""))
            block, code, module = token.start in kept, [], False
        else:
            if not code:
                header = header and token.type in _HEADER
                module = token.type in _MODULE
            code.append(gap + body[token.start : token.stop + 1])
    return lines


def _written(lines: list[_Line]) -> list[tuple[str, str]]:
    """Each line's code and comment in order; a comment without code is a
    full-line comment."""

    return [(line.code, line.comment) for line in lines if line.code or line.comment]


def _render(lines: list[_Line], newline: str) -> str:
    """The lines at their indentation, with the blank lines they keep."""

    indents = _indents(lines)
    entries = [
        (index, line, indents[index])
        for index, line in enumerate(lines)
        if line.code or line.comment
    ]
    # A top-level entry is a declaration line or a comment line at column 0.
    top = [line.block and indent == 0 for _, line, indent in entries]
    blank = [
        0 < position and index - entries[position - 1][0] > 1
        for position, (index, _, _) in enumerate(entries)
    ]
    # The header lines and the comment lines over them stay together (the
    # parser already refuses a blank line between two header lines).
    last_header = max(
        (p for p, (_, line, _) in enumerate(entries) if line.header is not None),
        default=0,
    )
    blank[1 : last_header + 1] = [False] * last_header
    # Exactly one blank line between top-level declarations, and none
    # between two consecutive imports or exports; the comment lines at
    # column 0 over a declaration belong to it, so the blank line goes above
    # them and none stays among them. Header lines are not declarations, and
    # the comment lines that no declaration follows keep their blank lines.
    module = False
    for start, (_, line, _) in enumerate(entries):
        if not top[start] or not line.code or line.header is not None:
            continue
        first = start
        while first > 0 and top[first - 1] and not entries[first - 1][1].code:
            first -= 1
        above = first > 0 and not (module and line.module)
        blank[first : start + 1] = [above] + [False] * (start - first)
        module = line.module
    text = [
        (newline if blank[position] else "")
        + (
            line.header
            if line.header is not None
            else " " * indent
            + line.code
            + ("  " if line.code and line.comment else "")
            + line.comment
        )
        for position, (_, line, indent) in enumerate(entries)
    ]
    return "".join(item + newline for item in text)


def _indents(lines: list[_Line]) -> list[int]:
    """Four spaces per block; a comment line takes the indentation of the
    line it precedes, or that of the deeper block it was written in; a line
    inside parentheses moves with the line it continues."""

    indents = [0] * len(lines)
    widths = [0]
    shift = 0
    pending: list[tuple[int, int]] = []  # comment lines and their written depth
    for index, line in enumerate(lines):
        if not line.block:
            indents[index] = max(0, line.width + shift)
        elif not line.code:
            pending.append((index, sum(w <= line.width for w in widths) - 1))
        else:
            while widths[-1] > line.width:
                widths.pop()
            if widths[-1] < line.width:
                widths.append(line.width)
            depth = len(widths) - 1
            for comment, written in pending:
                indents[comment] = 4 * max(depth, written)
            pending = []
            indents[index] = 4 * depth
            shift = indents[index] - line.width
    for comment, written in pending:
        indents[comment] = 4 * written
    return indents
