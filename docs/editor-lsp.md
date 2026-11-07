# Editor diagnostics: `pietto lsp` (alpha)

`pietto lsp` is a language server for editors. It runs the `pietto check`
stage on the files you edit and pushes the diagnostics to the editor. It does
nothing else: no hover, completion, go-to-definition, formatting or SQL. The
editor runs no dialect, so backend refusals (`PIE-B...`) appear only in
`pietto emit-sql`. This is an alpha contract for editors; it adds no CLI JSON
document and changes no other command.

## What the server does

- It speaks JSON-RPC 2.0 with Language Server Protocol framing on standard
  input and output. `pietto lsp --stdio` is the same command; `--stdio` is
  accepted because generic clients add it.
- The editor sends whole documents (full sync), and positions are UTF-16, as
  every LSP client expects.
- Project roots come only from the `projectRoots` initialization option: a
  list of absolute paths, each the same as `pietto check --project PATH`.
  Without the option there are no roots. Any other value, and two paths that
  name one directory (also through a symbolic link), are refused with the
  JSON-RPC error `-32602`. Pietto never guesses a root from the workspace or
  the working directory. To change the roots, restart the server.
- Every module that a root selects is checked, whether it is open or not, and
  shows the diagnostics of `pietto check --project ROOT --format json`. An
  open file is checked from its unsaved buffer. The buffer is only read for
  these diagnostics: nothing is written, and `emit-sql`, compiled builds and
  packages refuse buffer text by type.
- In a `schema_version = 2` root, a read, parse, header, def import or
  naming error, an error of the checks after naming, or an import cycle in
  one module no longer hides the other modules: that module, and every
  module that imports it directly or through other modules, is left out and
  the rest is checked again, at most five times. Each module still checked
  shows what `pietto check --project ROOT --format json` shows with the
  left-out modules in `[sources].exclude`. A root of another schema version,
  like the command line, stays all or nothing.
- Any other open file is checked like `pietto check FILE`. A module that
  imports names reports them as unknown (and the import as `PIE-S2708`) until
  its project root is in `projectRoots`.
- A diagnostic shows its `message` and then, on a new line, its JSON
  `suggestion`, unless the message already contains that text.
- Project errors show as `project error: <kind>: <message>`: at the file they
  name, else at `pietto.toml`, else in a message window.
- Each published set for an open file carries the document version it was
  computed from. A newer edit makes an older result stale, and the server
  drops it instead of publishing it.

The server adds five messages of its own, without a `PIE-` code. Each of
the first three is the only diagnostic its file gets; the server picks no
root, no buffer and no file. A file open under two URIs is checked from the
disk until one of them is closed.

| When | Message |
|---|---|
| Two configured roots select the same file | `This file belongs to two project roots: <root 1> and <root 2>. Keep one of them in projectRoots.` |
| A selected file is open under two URIs, for example `file:///r/a.pietto` and `file:///r/./a.pietto`, or `file:///r/A.pietto` on Windows | `This file is open under two URIs: <uri 1> and <uri 2>. Keep one of them open.` (URIs in code-point order) |
| Two selected files have names that differ only in letter case, which a case-sensitive directory on Windows can hold | `This file is selected under two names that differ only in letter case: <name 1> and <name 2>. Rename one of them.` (names relative to the root, in code-point order) |
| A module was not checked because a module it imports has errors | `Not checked: this module imports <file>, which has errors.` (two or more files: `<file 1>, <file 2> and <file 3>, which have errors.`, in code-point order; Information, at its import) |
| The editor sent a partial change | `Pietto needs whole-document changes; reopen this file.` |

## VS Code with a generic LSP client

These steps use a fictional project at `/home/ada/work/harbor-sales` (on
Windows, `C:\Users\ada\work\harbor-sales`) with its `pietto.toml` at that
root.

1. Install Pietto into a Python environment and note the full path of its
   `pietto` command, for example `/home/ada/.venvs/pietto/bin/pietto` (on
   Windows, `C:\Users\ada\.venvs\pietto\Scripts\pietto.exe`).
2. Give `.pietto` files a language id in your user or workspace
   `settings.json`:

   ```json
   {
     "files.associations": { "*.pietto": "pietto" }
   }
   ```

3. Install a generic LSP client extension, for example *Generic LSP Client
   (v2)* (`llllvvuu.glspc`), and point it at the server. With that extension
   the settings are (check the names in the extension's own README if they
   differ in your version):

   ```json
   {
     "glspc.server.command": "/home/ada/.venvs/pietto/bin/pietto",
     "glspc.server.commandArguments": ["lsp"],
     "glspc.server.languageId": ["pietto"],
     "glspc.initializationOptions": {
       "projectRoots": ["/home/ada/work/harbor-sales"]
     }
   }
   ```

   On Windows the root is written as a JSON string, for example
   `"C:\\Users\\ada\\work\\harbor-sales"`.
4. Reload the window. Open `harbor-sales/models.pietto`; its errors, and the
   errors of the project's other modules, appear in the Problems panel.
5. Run only one Pietto diagnostics source for a file. If another extension
   already runs `pietto check` on save, turn that off, or the two sets of
   diagnostics mix.

Any other client that can start a command over stdio works the same way:
the command is `pietto lsp`, the documents are `*.pietto` files, and the
initialization options are `{"projectRoots": [...]}`.
