### Editor workspace symbols and import links — editor core work package

The alpha `pietto lsp` server now advertises `workspaceSymbolProvider` and
`documentLinkProvider`. A `workspace/symbol` request lists the declarations
that document symbols list, for every module of the configured roots and
every other open document: the roots in `projectRoots` order, each root's
modules in the order `pietto check --project` selects them, then the other
open documents in URI order, each in source order. Every occurrence is kept,
so a name declared in two modules is listed twice. A declaration is listed
when the characters of the query appear in its name in order, ignoring the
case of ASCII letters, and every one is listed for an empty query. The
request waits while any analysis is pending, and a module or document without
facts lists nothing.

A `textDocument/documentLink` request returns one link for each import of a
schema-v2 project module, on the import path's string, to the module whose
project-relative path the string names exactly, as `pietto check --project`
resolves it. The target may have errors of its own, but there is no link in
a single file or in a module without facts, and none to a module that the
check left out, whose file shows a root, URI or file-name conflict, or whose
open document had a change refused, until that document is reopened.
Neither request resolves items later.

Both answer from the analysis that the diagnostics come from, with no new
check and no file read. Diagnostics, hover, definition, document symbols and
formatting are unchanged, and so are the CLI commands, CLI JSON, PIE codes,
semantic metadata and relation-column formats. The surface is alpha until the
Phase82 freeze.
