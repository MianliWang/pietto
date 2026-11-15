### Editor sessions that outlive an internal error

The alpha `pietto lsp` server no longer stops when an error inside Pietto
stops the analysis of an open document or of a project root. That analysis
publishes no diagnostics and keeps no editor facts, the requests that waited
for it are answered, the server writes `pietto lsp: internal error; continuing`
and the traceback to standard error, and the next change of the document
analyses it again. A failed root analysis publishes no diagnostics, so the
root's diagnostics from an earlier analysis stay in place.

Before (measured at `22046a4f` on Linux with CPython 3.13.13, with the
analyzer made to raise `ValueError`): opening a document that no root selects
ended the server with exit code 1 and the traceback on standard error, and
later requests got no reply. An internal `ValueError` in a project root's
check already published `project error: project_root: Project root could not
be pinned.` and kept the session; that is unchanged, and any other internal
error there no longer ends the server. After: the session goes on as above.
The CLI commands, CLI JSON and PIE codes are unchanged. The surface is alpha
until the Phase82 freeze.
