"""Public Pietto parsing facade that keeps ANTLR objects internal."""

from __future__ import annotations

import bisect
import unicodedata
from _thread import allocate_lock, start_new_thread
from threading import Event
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from antlr4 import CommonTokenStream, InputStream, ParserRuleContext, TokenStream
from antlr4.atn.LexerATNSimulator import LexerATNSimulator
from antlr4.atn.ParserATNSimulator import ParserATNSimulator
from antlr4.error.Errors import NoViableAltException
from antlr4.IntervalSet import IntervalSet
from antlr4.ListTokenSource import ListTokenSource
from antlr4.PredictionContext import PredictionContextCache
from antlr4.Token import Token

from pietto.ast_builder import AstBuilder
from pietto._syntax_admission import modern_spelling_diagnostics
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


class _LineEndSimulator(LexerATNSimulator):
    """Count LF, CRLF and a lone CR as one line end each, as NEWLINE does.

    The ANTLR runtime counts only LF.
    """

    def consume(self, input: InputStream) -> None:
        character = input.LA(1)
        if character == 0x0A or (character == 0x0D and input.LA(2) != 0x0A):
            self.line += 1
            self.column = 0
        else:
            self.column += 1
        input.consume()


class _PiettoLexer(PiettoLexer):
    def __init__(self, input: InputStream) -> None:
        super().__init__(input)
        self._interp = _LineEndSimulator(
            self, self.atn, self.decisionsToDFA, PredictionContextCache()
        )


@dataclass(frozen=True, slots=True)
class ParseResult:
    """The AST and structured diagnostics produced by a parse attempt."""

    ast: Script | None
    diagnostics: tuple[Diagnostic, ...]


def parse_source(source: str, *, path: str | Path | None = None) -> ParseResult:
    """Parse modern source with bounded, cancellation-contained diagnostics."""

    return _parse_contained(source, path=path, modern=True)


def _parse_legacy_source(source: str, *, path: str | Path | None = None) -> ParseResult:
    """Read old spelling only for migration and precise refusal diagnostics."""

    return _parse_contained(source, path=path, modern=False)


def _parse_migration_source(
    source: str, *, path: str | Path | None = None, modern: bool = False
) -> tuple[ParseResult, ParserRuleContext | None]:
    """Retain the successful legacy tree and its original token offsets.

    With ``modern``, read modern tokens instead and admit every spelling the
    grammar parses, so that a modern source's retired spellings can migrate.
    """

    trees: list[ParserRuleContext] = []
    result = _parse_contained(
        source, path=path, modern=modern, trees=trees, admit=False
    )
    return result, trees[0] if trees and result.ast is not None else None


def _parse_contained(
    source: str,
    *,
    path: str | Path | None,
    modern: bool,
    trees: list[ParserRuleContext] | None = None,
    admit: bool = True,
) -> ParseResult:
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
    # stops within a few thousand characters of lexing, at the next token the
    # parser or its lookahead moves over, or at the next tree node, and is
    # re-raised once the parse has stopped, so no parse outlives its call.
    cancel = Event()
    finished = allocate_lock()
    finished.acquire()
    outcome: list[ParseResult | BaseException | None] = [None]

    def contained() -> None:
        result: ParseResult | BaseException
        try:
            try:
                result = _parse_source(
                    source,
                    path=path,
                    cancel=cancel,
                    modern=modern,
                    trees=trees,
                    admit=admit,
                )
            except RecursionError:
                result = ParseResult(
                    ast=None, diagnostics=(_recursion_diagnostic(path, None, ()),)
                )
        except BaseException as error:  # re-raised in the calling thread
            result = error
        # On every path ``outcome`` is filled, without allocating, before
        # ``finished`` is released.
        outcome[0] = result
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
                return _contained_parse(
                    source,
                    path=path,
                    cancel=cancel,
                    modern=modern,
                    trees=trees,
                    admit=admit,
                )
            raise
        cancel.set()
        # The wait above can have taken ``finished`` just before the exception,
        # but only once ``outcome`` was filled: while it is empty, waiting again
        # cannot wait for a release that has already been taken.
        if outcome[0] is None:
            finished.acquire()
        raise
    result = outcome[0]
    if isinstance(result, BaseException):
        raise result
    assert result is not None  # filled before ``finished`` was released
    return result


def _contained_parse(
    source: str,
    *,
    path: str | Path | None,
    cancel: Event,
    modern: bool = True,
    trees: list[ParserRuleContext] | None = None,
    admit: bool = True,
) -> ParseResult:
    """Parse inside the recursion containment boundary."""

    try:
        return _parse_source(
            source, path=path, cancel=cancel, modern=modern, trees=trees, admit=admit
        )
    except RecursionError:
        return ParseResult(
            ast=None, diagnostics=(_recursion_diagnostic(path, None, ()),)
        )


def _parse_source(
    source: str,
    *,
    path: str | Path | None,
    cancel: Event,
    modern: bool = True,
    trees: list[ParserRuleContext] | None = None,
    admit: bool = True,
) -> ParseResult:
    """Implement parsing inside the public recursion containment boundary."""

    lexer_listener = DiagnosticErrorListener(path)
    lexer = _PiettoLexer(_CancellableInputStream(source, cancel))
    lexer.removeErrorListeners()
    lexer.addErrorListener(lexer_listener)
    raw_tokens, token_budget_diagnostic = _read_tokens(lexer, path=path)
    if token_budget_diagnostic is not None:
        return ParseResult(ast=None, diagnostics=(token_budget_diagnostic,))

    if not modern:
        for token in raw_tokens:
            if token.text in {"None", "True", "False", "having", "any", "for"}:
                token.type = PiettoLexer.IDENTIFIER

    diagnostics = list(lexer_listener.diagnostics)
    diagnostics.extend(find_leading_tab_diagnostics(source, path=path))
    # Each cause gets no parser error of its declaration beside it: the parser
    # would only report what follows from it.
    causes = [*_brace_diagnostics(raw_tokens, path=path)]
    causes.extend(_indentation_character_diagnostics(raw_tokens, path=path))
    unterminated = [
        token for token in raw_tokens if token.type == PiettoLexer.UNTERMINATED_STRING
    ]
    for token in unterminated:
        causes.append(
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
                    *causes,
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
    causes.extend(indentation.diagnostics)
    diagnostics.extend(causes)

    tokens = list(indentation.tokens)
    starts = _declaration_starts(tokens)
    # Parsed inline rather than in a helper: every frame here is one less for
    # the nesting the parser accepts.  A parse that guessed a decision (see
    # _PiettoSimulator) and is not clean is parsed again with ANTLR deciding.
    guess = True
    while True:
        parser = _PiettoParser(
            _CancellableTokenStream(ListTokenSource(tokens, source_path(path)), cancel),
            tokens if guess else None,
        )
        parser.removeErrorListeners()
        reporter = SyntaxErrorReporter(path, tokens)
        parser._errHandler = reporter
        try:
            tree = parser.script()
        except RecursionError:
            if parser.simulator.guessed:
                guess = False
                continue
            return ParseResult(
                ast=None,
                diagnostics=(
                    _recursion_diagnostic(
                        path,
                        parser.getCurrentToken(),
                        [tokens[index] for index in starts],
                    ),
                ),
            )
        if not (reporter.errors and parser.simulator.guessed):
            break
        guess = False
    for token in _misplaced_steps(tree):
        reporter.report_out_of_order(token)
    if reporter.errors:
        diagnostics.extend(
            _first_error_per_declaration(tokens, starts, reporter, causes)
        )

    ordered_diagnostics = _source_ordered(diagnostics)
    if any(item.severity is Severity.ERROR for item in ordered_diagnostics):
        return ParseResult(ast=None, diagnostics=ordered_diagnostics)

    if modern and admit:
        spelling_diagnostics = modern_spelling_diagnostics(
            tree, path=path, cancel=cancel
        )
        if spelling_diagnostics:
            return ParseResult(ast=None, diagnostics=spelling_diagnostics)

    builder = AstBuilder(path, cancel=cancel, legacy=not modern)
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

    if trees is not None:
        trees.append(tree)
    return ParseResult(ast=ast, diagnostics=ordered_diagnostics)


class _PiettoParser(PiettoParser):
    """The Pietto parser, giving every caller its own expected-token set.

    For most states ANTLR returns the set its ATN caches for every parse in
    the process, and its Python error recovery adds to the set in place, so a
    message would otherwise depend on what the process parsed before.  Given
    the source's tokens, it guesses the decisions of ``_GUESSES``.
    """

    def __init__(self, input: TokenStream, tokens: Sequence[Token] | None = None):
        super().__init__(input)
        self.simulator = _PiettoSimulator(
            self, self.atn, self.decisionsToDFA, self.sharedContextCache
        )
        self.simulator.tokens = tokens
        self._interp = self.simulator

    def getExpectedTokens(self) -> IntervalSet:
        expected = IntervalSet()
        expected.addSet(super().getExpectedTokens())
        return expected


# A shape item that starts with a name is a field unless `=` follows the name
# (`key = unique(id)`).  So that `id Int` still reports the field's missing ':'
# rather than an item no alternative fits, a name followed by neither ':' nor
# '=' is predicted to be a field.
_SHAPE_ITEM_DECISION: int = (
    PiettoParser.atn.ruleToStartState[PiettoParser.RULE_shapeItem]
    .transitions[0]
    .target.decision
)
_NAME_FIRST: frozenset[int] = frozenset(
    PiettoParser.atn.nextTokens(
        PiettoParser.atn.ruleToStartState[PiettoParser.RULE_identifier]
    )
)


def _first_alternative(decision: int, token: int) -> int:
    """The first alternative of a decision that can start with ``token``."""

    state = PiettoParser.atn.decisionToState[decision]
    return next(
        alternative
        for alternative, transition in enumerate(state.transitions, start=1)
        if token in PiettoParser.atn.nextTokens(transition.target)
    )


# ANTLR settles two kinds of decision only by reading a whole expression
# ahead, and its closure at the expression's end nests three to five frames
# for each of the expression's levels, more than parsing and building it
# take: a block body's optional `return`, which is also a name, and in a
# qualify condition a call that a window follows, told from a plain call only
# after its `)`.  Given the tokens, the parser instead takes the first
# alternative that can start with the next token: for a body's `return`
# always, for a qualify call when a window's direction, null treatment or
# window follows its `)`.  No earlier alternative can start with that token,
# so a clean parse is the parse ANTLR's own decisions give; one that is not
# clean is parsed again with ANTLR deciding (see _parse_source).
_RETURN_DECISIONS: frozenset[int] = frozenset(
    state.decision
    for state in PiettoParser.atn.decisionToState
    if state.ruleIndex
    in {PiettoParser.RULE_constraintBody, PiettoParser.RULE_deriveBody}
    and set(PiettoParser.atn.nextTokens(state.transitions[0].target))
    == {PiettoParser.RETURN}
)
_QUALIFY_PRIMARY_DECISION: int = (
    PiettoParser.atn.ruleToStartState[PiettoParser.RULE_qualifyPrimaryExpression]
    .transitions[0]
    .target.decision
)
_GUESSES: dict[tuple[int, int], int] = {
    **{
        (decision, PiettoParser.RETURN): _first_alternative(
            decision, PiettoParser.RETURN
        )
        for decision in _RETURN_DECISIONS
    },
    (_QUALIFY_PRIMARY_DECISION, PiettoParser.IDENTIFIER): _first_alternative(
        _QUALIFY_PRIMARY_DECISION, PiettoParser.IDENTIFIER
    ),
}
# What may follow a window call's `)`: its direction, null treatment or window.
_WINDOW_TAIL: frozenset[int] = frozenset(
    token
    for rule in (
        PiettoParser.RULE_nthValueDirection,
        PiettoParser.RULE_nullTreatment,
        PiettoParser.RULE_qualifyInlineWindowSpec,
    )
    for token in PiettoParser.atn.nextTokens(PiettoParser.atn.ruleToStartState[rule])
)


class _PiettoSimulator(ParserATNSimulator):
    """ANTLR's prediction, except that a shape item never fails on its name
    and, given the tokens, the decisions of ``_GUESSES`` are guessed."""

    tokens: Sequence[Token] | None = None
    guessed = False

    def adaptivePredict(
        self, input: TokenStream, decision: int, outerContext: ParserRuleContext
    ) -> int:
        if self.tokens is not None:
            start: Token = cast(Any, input).LT(1)
            guess = _GUESSES.get((decision, start.type))
            if guess is not None and (
                decision != _QUALIFY_PRIMARY_DECISION
                or self._window_follows_call(cast(int, start.tokenIndex))
            ):
                self.guessed = True
                return guess
        try:
            return super().adaptivePredict(input, decision, outerContext)
        except NoViableAltException as error:
            if (
                decision == _SHAPE_ITEM_DECISION
                and error.startToken.type in _NAME_FIRST
                and error.offendingToken.tokenIndex == error.startToken.tokenIndex + 1
            ):
                return 1  # fieldDefinition
            raise

    def _window_follows_call(self, name: int) -> bool:
        """Whether the name at ``name`` opens a call that a window follows."""

        tokens = cast(Sequence[Token], self.tokens)
        if name + 1 >= len(tokens) or tokens[name + 1].type != PiettoParser.LPAREN:
            return False
        depth = 0
        for index in range(name + 1, len(tokens) - 1):
            kind = tokens[index].type
            depth += (kind == PiettoParser.LPAREN) - (kind == PiettoParser.RPAREN)
            if depth == 0:
                return tokens[index + 1].type in _WINDOW_TAIL
        return False


def _misplaced_steps(tree: ParserRuleContext) -> Iterator[Token]:
    """The first step of each relation body that stands out of its order.

    Any lets and WHEREs may precede a JOIN.  After the last JOIN, or in a body
    without one, come lets and named windows and then at most one WHERE; a
    `let:` block may follow those lets but not a WHERE.  A JOIN after a named
    window is the step out of order.  A body whose steps reach no clause after
    them is left to its syntax error, and a step that error recovery parsed
    again from the same token counts once.
    """

    pending = [tree]
    while pending:
        context = pending.pop()
        if isinstance(context, PiettoParser.TableBodyContext):
            body: Any = context  # its generated rule accessors
            if (
                body.letClause() or body.groupByClause() or body.selectClause()
            ) is None:
                continue
            steps: list[Any] = []
            for step in body.relationStep():
                if not steps or step.start.tokenIndex > steps[-1].start.tokenIndex:
                    steps.append(step)
            joined = [
                index
                for index, step in enumerate(steps)
                if step.joinClause() is not None
            ]
            window = next(
                (
                    index
                    for index, step in enumerate(steps)
                    if step.namedWindowDeclaration() is not None
                ),
                len(steps),
            )
            if joined and window < joined[-1]:
                yield next(steps[index].start for index in joined if index > window)
                continue
            where = False
            for step in steps[joined[-1] + 1 if joined else 0 :]:
                if where:
                    yield step.start
                    break
                where = step.whereClause() is not None
            else:
                if where and body.letClause() is not None:
                    yield body.letClause().start
        elif isinstance(context, _RELATION_OWNERS):
            pending.extend(
                child
                for child in context.getChildren()
                if isinstance(child, ParserRuleContext)
            )


_RELATION_OWNERS = (
    PiettoParser.ScriptContext,
    PiettoParser.DefinitionContext,
    PiettoParser.TableDefinitionContext,
    PiettoParser.QueryDefinitionContext,
    PiettoParser.LetRelationDefinitionContext,
)


class _CancellableInputStream(InputStream):
    """Source text whose lexing stops soon after its caller cancels it.

    One token, such as a long comment or string, can span the whole file, so
    the lexer's character loop checks every 4,096 characters.
    """

    __slots__ = ("_cancel",)

    def __init__(self, data: str, cancel: Event):
        super().__init__(data)
        self._cancel = cancel

    def consume(self) -> None:
        if not self._index & 0xFFF and self._cancel.is_set():
            raise ParseCancelled
        InputStream.consume(self)


class _CancellableTokenStream(CommonTokenStream):
    """A token stream whose parse stops once its caller cancels it.

    The parser and its lookahead both move over tokens with ``consume``, also
    over tokens that a long lookahead has already fetched.
    """

    def __init__(self, source: ListTokenSource, cancel: Event):
        # ANTLR accepts any token source; its runtime annotation names Lexer.
        super().__init__(cast(Any, source))
        self._cancel = cancel

    def consume(self) -> None:
        if self._cancel.is_set():
            raise ParseCancelled
        CommonTokenStream.consume(self)


def _declaration_starts(tokens: list[Token]) -> list[int]:
    """Indexes of the tokens that start a top-level declaration, in order.

    A declaration starts with the first token of a logical line at column 0,
    unless that is a space the lexer does not know, such as a form feed: it is
    the line's indentation and stays in the declaration it is in.
    """

    layout = {Token.EOF, PiettoLexer.NEWLINE, PiettoParser.INDENT, PiettoParser.DEDENT}
    return [
        index
        for index, token in enumerate(tokens)
        if token.column == 0
        and token.type not in layout
        and not _is_indentation_character(token)
        and (index == 0 or tokens[index - 1].type in layout)
    ]


def _is_indentation_character(token: Token) -> bool:
    """Whether the token is a space the lexer does not know, such as a form feed."""

    text = token.text or ""
    return token.type == PiettoLexer.UNKNOWN and (
        text in ("\v", "\f") or unicodedata.category(text) == "Zs"
    )


def _first_error_per_declaration(
    tokens: list[Token],
    starts: list[int],
    reporter: SyntaxErrorReporter,
    causes: list[Diagnostic],
) -> list[Diagnostic]:
    """Keep the first parser error of each top-level declaration.

    Later errors in the same declaration are recovery noise, and a declaration
    whose source already has a brace, indentation or string error gets none:
    that error is the cause.  Both lookups bisect the sorted starts.
    """

    start_lines = [tokens[index].line for index in starts]
    blocked = {bisect.bisect_right(start_lines, item.location.line) for item in causes}
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
) -> tuple[list[Token], Diagnostic | None]:
    """Materialize lexer tokens so indentation and token checks can share them."""

    tokens: list[Token] = []
    non_eof_count = 0
    while True:
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


def _indentation_character_diagnostics(
    tokens: list[Token],
    *,
    path: str | Path | None,
) -> list[Diagnostic]:
    """Report a space other than ' ' and tab in a line's indentation.

    A form feed, vertical tab or Unicode space such as a no-break space is no
    indentation to the lexer, so the line's indentation would end before it
    and the parser would only report what follows from that, such as the end
    of the block above.
    """

    return [
        _token_diagnostic(
            "PIE-P1000",
            f"Unexpected character U+{ord(token.text):04X} in indentation; indent "
            "with spaces.",
            path,
            token,
        )
        for index, token in enumerate(tokens)
        if _is_indentation_character(token)
        and (index == 0 or tokens[index - 1].type == PiettoLexer.NEWLINE)
    ]


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
