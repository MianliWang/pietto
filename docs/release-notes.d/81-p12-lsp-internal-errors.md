### Editor sessions that outlive any internal error

The alpha `pietto lsp` server no longer stops when an error inside Pietto
occurs outside the analysis of a document or a project root: while it
stores or publishes an analysis's result, answers a request or handles a
notification. As for an error in the analysis itself, it writes
`pietto lsp: internal error; continuing` and the traceback to standard
error, and the session goes on. A request that the error stopped receives
JSON-RPC `-32603` `Internal error`, and a notification that it stopped is
handled no further. When an error stops an analysis, or the storing or
publishing of its result, the document or root clears every diagnostic set
it had published and keeps no editor facts, so the diagnostics of an older
text no longer stay on the new one; the next change analyses it again.
Closed standard output still ends the session with exit code 1, and an
interrupt is not caught. A standard error that cannot be written changes
none of this.

Before (measured at `6fa66291` on Linux with CPython 3.13.13, in a
`pietto lsp` process whose analysis, publishing and completion were made
to raise `RuntimeError` for marked texts): after version 1 of a document
published its diagnostics, an error in the analysis of version 2 left them
on version 2's text, and an error while publishing version 3's result ended
the server with exit code 1 and the traceback, so later messages got no
reply. After: version 2's set is cleared, the completion request whose
answer fails receives `-32603`, the later versions publish their
diagnostics, and `shutdown` and `exit` end the session with exit code 0.
The CLI commands, CLI JSON and PIE codes are unchanged. The surface is
alpha until the Phase82 freeze.
