# Editor support: `pietto lsp` (alpha)

`pietto lsp` checks files and configured projects for diagnostics and supplies
hover, go-to-definition and document symbols from the same analysis. Backend
refusals (`PIE-B...`) still appear only in
`pietto emit-sql`.

The protocol, lifecycle, full-document synchronization, UTF-16 position,
project-overlay, conflict, diagnostic, resource, and trust rules are the
[LSP diagnostics v1](spec/lsp-diagnostics-v1.md) alpha contract. In
particular, it has no completion, formatting, SQL preview or execution feature.

Hover describes resolved type and `from` references. Go-to-definition follows
their exact declaration, including supported imports and re-exports inside a
configured schema-v2 project. Builtin types have a hover description but no
authored definition. The outline lists named top-level declarations in source
order, including single-file constants and relationship templates. Field,
let, parameter and function-call bindings are not yet navigation facts.

These requests return no facts for stale or failed analyses, omitted modules,
ambiguous ranges or root/URI conflicts. They query the current snapshot without
rechecking or reading files. The server does not watch external disk changes;
project facts refresh when its existing document notifications cause a new
analysis. The [editor facts contract](spec/lsp-editor-facts-v1.md) defines the
exact availability and client-capability rules.

## The Pietto extension for VS Code

The Phase75 acceptance used the Pietto extension for VS Code `0.2.0`, commit
`5484ebdb` of the repository `MianliWang/pietto-vscode-extension`. It starts
`pietto lsp` through `vscode-languageclient` 9.0.1 and sends its setting
`pietto.projectRoots` as the `projectRoots` initialization option. Its
acceptance, which the [Phase75 route](phases/phase-75/route.md) requires, ran
in VS Code 1.145.2 on the batch-1 head `ff1aa713`. The independent extension
has since published its `0.3.0` SQL-preview code; [status](status.md) records
that repository state separately from the owner's Marketplace upload. Follow
its repository's installation instructions or use a generic LSP client as
the next section shows. The extension `0.1.0` accepted only Pietto `0.1.2`.

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
