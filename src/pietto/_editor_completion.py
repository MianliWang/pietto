"""What `pietto lsp` offers as completion (alpha): a static vocabulary, then
the identifiers of the request's open buffer. The vocabulary is the keywords
that accepted source writes, then the builtin types, scalar functions and
aggregates of the core catalog; it is built once, at import, from the
generated lexer's literal names and the core catalog, which it only reads.
The identifiers come from one regular-expression scan of the buffer text that
finds the lexer's IDENTIFIER tokens; it parses and analyses nothing and runs
no generated lexer. The position only leaves out the word being typed. The
contract is docs/spec/lsp-editor-facts-v1.md."""

from __future__ import annotations

import re

from pietto.generated.PiettoLexer import PiettoLexer
from pietto.semantic.aggregates import (
    GROUP_TEST_AGGREGATE_NAMES,
    SEMANTIC_AGGREGATE_NAMES,
)
from pietto.semantic.catalog import (
    BUILTIN_FUNCTIONS,
    BUILTIN_TYPE_NAMES,
    SPECIAL_BUILTIN_FUNCTION_NAMES,
)

__all__ = ("buffer_identifiers", "completion_items")

# CompletionItemKind values of the first protocol version, which every client
# supports without declaring a value set.
_TEXT = 1
_FUNCTION = 3
_CLASS = 7
_KEYWORD = 14

# Lexer words that no accepted source writes as a keyword: the retired header
# lines (a header word is still a name, and `encoding` a type argument name),
# and the retired spellings `satisfying`, `semi` and `anti` JOINs, `cast`,
# `null`, `nullable`, and the relationship `endpoint` and `via` forms.
_REFUSED = frozenset(
    {
        "anti",
        "cast",
        "checked",
        "dialect",
        "encoding",
        "endpoint",
        "loose",
        "mode",
        "null",
        "nullable",
        "pietto",
        "satisfying",
        "semi",
        "strict",
        "via",
    }
)
# The TRUE and FALSE rules each lex two spellings, so the lexer has no literal
# name for them; accepted source writes these.
_BOOLEANS = frozenset({"True", "False"})
_LITERAL_WORDS = frozenset(
    name[1:-1]
    for name in PiettoLexer.literalNames
    if name.startswith("'") and name[1:-1].isidentifier()
)
# Every word that the lexer reads as a keyword token, not an IDENTIFIER.
_LEXER_WORDS = _LITERAL_WORDS | {"true", "True", "false", "False"}

_KEYWORDS = sorted((_LITERAL_WORDS - _REFUSED) | _BOOLEANS)
_VOCABULARY: tuple[tuple[str, int], ...] = (
    *((word, _KEYWORD) for word in _KEYWORDS),
    *((name, _CLASS) for name in sorted(BUILTIN_TYPE_NAMES)),
    *(
        (name, _FUNCTION)
        for name in sorted({*BUILTIN_FUNCTIONS, *SPECIAL_BUILTIN_FUNCTION_NAMES})
    ),
    *(
        (name, _FUNCTION)
        for name in sorted({*SEMANTIC_AGGREGATE_NAMES, *GROUP_TEST_AGGREGATE_NAMES})
    ),
)
_LABELS = frozenset(label for label, _ in _VOCABULARY)

# The grammar's COMMENT, STRING and UNTERMINATED_STRING (whose escape takes any
# character, a line break too), NUMBER and IDENTIFIER rules. Matching from the
# left skips comments, strings and numbers whole, as the lexer's longest match
# does, so group 1 holds exactly the text of each IDENTIFIER token.
_TOKENS = re.compile(
    r"#[^\r\n]*"
    r"|\"(?:\\.|[^\"\\\r\n])*\"?"
    r"|'(?:\\.|[^'\\\r\n])*'?"
    r"|[0-9](?:_?[0-9])*(?:\.[0-9](?:_?[0-9])*)?"
    r"|([a-zA-Z_][a-zA-Z_0-9]*)",
    re.DOTALL,
)


_LINE_BREAK = re.compile(r"\r\n|\r|\n")


def buffer_identifiers(text: str, offset: int | None = None) -> list[str]:
    """The distinct IDENTIFIER token texts of a buffer, in code-point order,
    without the spelling of the one that touches `offset`: the word being
    typed, which VS Code's word-based suggestions leave out too."""

    words: set[str] = set()
    typed = None
    for match in _TOKENS.finditer(text):
        word = match.group(1)
        if word is not None and word not in _LEXER_WORDS:
            words.add(word)
            if offset is not None and match.start() <= offset <= match.end():
                typed = word
    words.discard(typed)
    return sorted(words)


def _offset(text: str, line: int, character: int) -> int | None:
    """The string offset of an LSP position (UTF-16 units; a character past
    the end of its line is the line's end), or None past the last line."""

    starts = [0, *(match.end() for match in _LINE_BREAK.finditer(text))]
    if line >= len(starts):
        return None
    offset = starts[line]
    while character > 0 and offset < len(text) and text[offset] not in "\r\n":
        character -= 2 if ord(text[offset]) > 0xFFFF else 1
        offset += 1
    return offset


def completion_items(
    text: str | None = None, line: int = 0, character: int = 0
) -> list[dict[str, object]]:
    """The `textDocument/completion` result: one complete `CompletionItem`
    list, keywords, types, scalar functions and aggregates in that order and
    each in code-point order, then the identifiers of `text`, the open buffer,
    that are not already a label, with kind Text, except the one at the
    request's position. A word that is both a keyword and an aggregate, such
    as `first`, is one item of each."""

    words = (
        [] if text is None else buffer_identifiers(text, _offset(text, line, character))
    )
    return [
        *({"label": label, "kind": kind} for label, kind in _VOCABULARY),
        *({"label": word, "kind": _TEXT} for word in words if word not in _LABELS),
    ]
