### Editor completion — editor core work package

The alpha `pietto lsp` server now advertises `completionProvider` and answers
`textDocument/completion` with one list: the keywords that current source
writes (`True`, `False` and `None` included), the builtin types, the scalar
functions and aggregates of the core catalog, and then the identifiers that
the open buffer writes outside comments and strings, such as its field, `let`,
relation and parameter names, except the word being typed. Nothing else in
the list depends on the position, so the editor filters it as you type. The
server answers when it reads the request: it neither waits for nor starts an
analysis. It reads the buffer's words with one scan and does not parse, check
or classify them; a name spelled like a keyword, such as a field named `mode`,
is not among them, and other files are not read.

Words that `pietto check` refuses are not part of the fixed list: the retired
header words, `satisfying`, `semi` and `anti` JOINs, `cast`, `null`,
`nullable`, `endpoint` and `via`, and the PostgreSQL extension functions,
which are not callable. Window functions are not part of it either. A word
that is both a keyword and an aggregate, such as `first`, is one item of each.
There are no trigger characters, no resolve request, no context-aware
completion and no signature help.

On a development host of VS Code 1.145.2 with default settings and the Pietto
extension, the fixed list alone replaced the editor's word-based suggestions
in a `.pietto` file: the start of a field, `let` or relation name of the open
file had no suggestion, while the extension's snippets stayed. The buffer's
names are in the list so that they are still suggested; words of other open
files are not.

Diagnostics and document symbols are unchanged, and so are the CLI commands,
CLI JSON, PIE codes, semantic metadata and relation-column formats. The surface
is alpha until the Phase82 freeze.
