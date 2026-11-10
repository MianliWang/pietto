### Editor formatting — editor core work package

The alpha `pietto lsp` server now formats an open document: it advertises
`documentFormattingProvider` and answers `textDocument/formatting` with one
edit of the whole buffer that gives what `pietto fmt` prints for the same
text: it keeps a leading byte order mark and writes every line break as the
buffer's first one (LF when it has none). A buffer that is already formatted
gets no edit. The request has no result when
`pietto fmt` would refuse the buffer (a parser error, a retired header line,
the size limit, or output that formatting would not keep), when the document
is not open, when its last change was refused, or when the editor sent
unpaired UTF-16 surrogates.

Formatting reads only the open buffer: it neither waits for the analyses that
edits schedule nor starts one, although an analysis already running when it
arrives ends first; it reads and writes no file and publishes no
diagnostic. The editor's formatting options are ignored, because `fmt` has one
layout, and `fmt` output may still change before the Phase82 freeze. Range and
on-type formatting are not provided. Diagnostics, hover, definition and
document symbols are unchanged, and so are the CLI commands, CLI JSON, PIE
codes, semantic metadata and relation-column formats. The surface is alpha
until the Phase82 freeze.
