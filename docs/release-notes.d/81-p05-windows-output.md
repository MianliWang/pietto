### Windows support for the CLI and `pietto.compiler`

On Windows x86-64 the CLI (`check`, `emit-sql`, `fmt`, `explain` and `lsp`)
and `pietto.compiler` are now supported with CPython 3.12 and 3.13. CI runs
their tests there on CPython 3.12.10 and 3.13.15 and smoke-tests the
installed wheel without any extra. Execution is not claimed on Windows: no
route, saved result, job or extra is qualified there. The `sqlite_file`
route refuses there (PIE-R2002), the workspace and saved-result names need
`fcntl`, which Windows CPython lacks, and the other routes are not refused,
so nothing that worked there is newly refused. The package's classifiers now
name `Operating System :: POSIX :: Linux` and
`Operating System :: Microsoft :: Windows` in place of
`Operating System :: OS Independent`; macOS is not claimed. See
[platforms and qualification](../capabilities.md#platforms-and-qualification).

`emit-sql --project ROOT --all --output DIR` now writes its directory on
Windows with CPython 3.12.4 or later, where it returned
`batch_output_platform` before. It writes by path: it creates DIR and
`DIR/artifacts` with access for only their owner, SYSTEM and Administrators,
holds both open without delete sharing while it writes, refuses either one
when it is a reparse point such as a junction, checks both against their
paths before each step, creates each file exclusively under a temporary
`.pietto-*.tmp` name, checks it again and renames it into place without
replacing an existing name, checks the installed name, and writes
`manifest.json` last. DIR's ancestors, and DIR until the command holds it,
are resolved by path, so someone who can delete entries in DIR's parent can
move the output elsewhere, though no existing file is replaced; the owner's
other processes and Administrators can still change files in DIR, and so
can every local user on a volume that keeps no access lists, such as FAT32
or exFAT. Its
failures use the existing `output_path` and `output_write` kinds. See
[project CLI JSON v2](../spec/project-cli-json-v2.md).

On Windows, the line ends that the CLI itself writes to stdout are now LF,
in text and JSON format alike, as `--output` files already did; the output
that the CLI wrote there through its text stream ended its lines with CRLF
before. `fmt` and `migrate` still keep the source's line endings, and stderr
keeps the platform's newline, CRLF on Windows. See
[CLI JSON v1](../spec/cli-json-v1.md).

Compatibility: on Windows, a reader that expected CRLF on stdout now gets
LF; the bytes of every `--output` file, batch artifact and manifest are
unchanged, and so is stdout outside Windows. On other platforms, macOS among
them, `--output DIR` still returns `batch_output_platform`, as does Windows
with an earlier CPython; its message now reads `Safe batch directory output
requires Windows with CPython 3.12.4 or later or a supported Linux
filesystem; use stdout instead.`
