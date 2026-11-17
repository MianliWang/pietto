### Editor project roots nested through a symbolic link

The alpha `pietto lsp` server now reports the overlap of a project root
nested in another root through a symbolic link. Two roots select one file
when its path under one root, with that root replaced by its real path, is
the real-path form of a path that the other root selects, so each root's
spelling of that file receives only `This file belongs to two project
roots: <root 1> and <root 2>. Keep one of them in projectRoots.`, as for
roots nested as written. Either root may be the link. The file's own links
are still never resolved.

Before (measured at `6fa66291` on Linux with CPython 3.13.13): with
`"projectRoots": ["/work/port", "/work/link"]`, where `/work/port` selects
`**/*.pietto` and `/work/link` is a symbolic link to the project
`/work/port/sub`, the server published the ordinary diagnostics of
`sub/inner.pietto`, an unresolved import, at both
`file:///work/port/sub/inner.pietto` and `file:///work/link/inner.pietto`,
without the overlap diagnostic. After: both URIs show only the overlap
diagnostic.

This removes the known limitation of `0.2.2` and earlier for such roots. A
document that the editor opens under a spelling that no root selects as
written is still checked alone, as before: under a third spelling, under
the real paths of both roots but under neither as written, or under the
outer root's spelling of a file that only the inner root selects. A root
reached through a link checks its own spelling's open buffer while the
other root reads the file from disk. Roots as written, the other
conflict diagnostics, the CLI commands, CLI JSON and PIE codes are
unchanged. The surface is alpha until the Phase82 freeze.
