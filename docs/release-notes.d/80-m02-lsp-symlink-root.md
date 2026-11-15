### Editor project roots through a symbolic link

The alpha `pietto lsp` server now checks a file that the editor opens under
the real path of a project root as that root's module when `projectRoots`
names the root through a symbolic link. At initialization the server records
each root's real path, and an opened document under that real path, but under
no root as written, takes the root's spelling: the project check uses its
buffer and publishes the project's diagnostics at the document's own URI.
Only the root is resolved, never the file's own links, and a document under
the real paths of two or more roots keeps its spelling. On Windows the real
path is compared ignoring letter case, as for VS Code's `file:///c%3A/...`
URIs. A module that is not open still publishes under the root's spelling.

Before (measured at `22046a4f` on Linux with CPython 3.13.13): with
`"projectRoots": ["/work/link"]`, where `/work/link` is a symbolic link to
`/work/harbor`, opening `file:///work/harbor/a.pietto`, a module without
errors that imports `models.pietto`, checked it alone as a single file and
published a PIE-S2708 warning and a false PIE-S2301 `Unknown relation:
users`. After: no diagnostic, as `pietto check --project /work/link`
reports.

A root nested in another root through a symbolic link still publishes the
modules that both select under both spellings without the overlap
diagnostic; that known limitation of `0.1.11` holds. Roots as written,
the conflict diagnostics, the CLI commands, CLI JSON and PIE codes are
unchanged. The surface is alpha until the Phase82 freeze.
