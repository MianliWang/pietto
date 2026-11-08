### Header compatibility and project formatting

The semantic API ignores a hand-built Header's retired mode field:
`analyze(script)` defaults to CHECKED, and `mode_override` is the caller's
mode selection. Source headers still produce the same per-line `PIE-P1000`
diagnostics, and `migrate` keeps its deletion and manual-migration behavior.
The legacy header grammar and tokens remain until the Phase82 freeze to
preserve those readers and their output bytes. No grammar, generated parser
or built-in catalog input changed, so this change requires no extension sync.

On platforms with directory-relative file operations, `fmt --project` holds
each source parent directory from its trusted read through atomic replacement,
checks the opened file identity and original bytes, and uses that directory
for temporary files, replacement and cleanup. A detected directory or symlink
replacement refuses the write; a move at the final operation cannot redirect
the write to another directory. Formatting bytes and file order are unchanged.

The held-directory guarantee starts at the trusted read, not initial directory
discovery. The path-based fallback, including Windows, adds an opened-source
identity check but does not eliminate every directory race. Writes remain
atomic per file; a project is not one transaction.

These are B2 source-candidate changes, pending final validation and publication.
They do not declare Phase76 complete or publish a package release.
