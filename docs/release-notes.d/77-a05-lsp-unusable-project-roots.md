### Editor project roots that no file can have

The alpha `pietto lsp` server no longer stops when the `projectRoots`
initialization option holds a path that no POSIX file can have: one with a
NUL character, or with an unpaired UTF-16 surrogate that the file system
encoding cannot write. It refuses such a list as it refuses any other invalid
value, with the JSON-RPC error `-32602` and the message `projectRoots must be
a list of distinct absolute paths`, and then waits for the next message.

Before (measured at `864411cb` on Linux with CPython 3.13.13):
`"projectRoots": ["/tmp/a\u0000b"]` ended the server with exit code 1 and a
`ValueError` traceback on standard error, and `"projectRoots":
["/tmp/r\ud800"]` ended it with exit code 2 and `pietto: error: terminal
output could not be encoded`; neither request got a reply. After: both get the
`-32602` error above. On Windows, whose `realpath` accepts both paths, nothing
changes. Valid roots, diagnostics, the CLI commands, CLI JSON and PIE codes
are unchanged. The surface is alpha until the Phase82 freeze.
