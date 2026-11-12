# Editor support: `pietto lsp` (alpha)

`pietto lsp` checks files and configured projects for diagnostics, supplies
hover, go-to-definition, document and workspace symbols, and links on import
paths from the same analysis, formats the open buffer as `pietto fmt`
formats a file, and completes Pietto keywords, builtin names and the names
the file writes. Backend
refusals (`PIE-B...`) still appear only in
`pietto emit-sql`.

The protocol, lifecycle, full-document synchronization, UTF-16 position,
project-overlay, conflict, diagnostic, resource, and trust rules are the
[LSP diagnostics v1](spec/lsp-diagnostics-v1.md) alpha contract. In
particular, it has no context-aware completion, SQL preview or execution
feature.

Hover describes resolved type and `from` references, field and `let` reads
and relationship calls. Go-to-definition follows their exact declaration,
including supported imports and re-exports inside a configured schema-v2
project. Builtin types have a hover description but no authored definition.
A field read defines the shape field when its relation reads a source; a
field of another relation, such as a relation let, has a hover but no
definition. In a single file these are the field reads of a JOIN relation and
relationship calls; in a project, the field and `let` reads of `let` values,
`select` items and `where` of a relation without JOIN, and a `from` that reads
a relation let. The outline lists named top-level declarations in source
order, including `def` functions, relationship templates and single-file
constants. Other reads, `def` calls and parameters, relationship parameters,
and a `from` that reads a table-function input have no hover or definition.

Workspace symbols list the outline's declarations of every module of the
configured roots and of every other open document: the roots in `projectRoots` order, each
root's modules in the order `pietto check --project` selects them, then the
other open documents in URI order, each in source order. A declaration is
listed when the characters of the query appear in its name in order, ignoring
the case of ASCII letters, and every declaration is listed for an empty query;
a name declared twice is listed twice. The path of each import in a schema-v2
project module is a link to the module whose project-relative path it names
exactly, as `pietto check --project` resolves it, even when that module has
errors of its own. There is no link in a single file, and none to a module
that the check left out, whose file shows a root, URI or file-name conflict
diagnostic, or whose open document had a change refused, until that document
is reopened.

These requests return no facts for stale or failed analyses, omitted modules,
modules with errors of their own, modules of a legacy-flat
(`schema_version = 1`) root, unknown types, ambiguous ranges, or a file that
shows a root, URI or file-name conflict diagnostic. A file that no root selects
is checked alone under each URI it is open under, so each such buffer keeps
its own facts. Beside a project module with an error, the other modules keep their
facts, but no use navigates into that module; only an import path links to it.
A request waits while an analysis
of its document, or of a project root that contains it, is pending, and has no
result if the document changes first or the server shuts down. A workspace
symbol request waits while any analysis is pending. Requests query
the current snapshot without rechecking or reading files. The server does not
watch external disk changes; project facts refresh when its existing document
notifications cause a new analysis. The
[editor facts contract](spec/lsp-editor-facts-v1.md) defines the exact
availability and client-capability rules.

Formatting a document formats the text in the editor, not the file on disk:
the server answers with one edit of the whole buffer that gives what
`pietto fmt` prints for that text, with no edit when the buffer is already
formatted, and with nothing when `pietto fmt` would refuse it (a parser error,
a header line, the size limit, or output that formatting would not keep), when
the document is not open, when its last change was refused, or when the editor
sent unpaired UTF-16 surrogates. It does not wait for the analyses that edits
schedule, although one that is already running ends first. It writes no file
and ignores the editor's tab and whitespace options, because `fmt` has one
layout. Its output may change before the Phase82 freeze.

Completion offers one list everywhere in a file: the keywords that current
Pietto source writes, `True`, `False` and `None` included, the builtin types,
the builtin scalar functions and aggregates, and then every name that the
open file writes outside comments and strings, such as its fields, `let`
names, relations and parameters, except the word you are typing. The editor
filters it as you type. The names
come from the file's current text alone, read as words: the server does not
check them, tell a field from a relation, or read other files, and a name that
is spelled like a keyword, such as a field named `mode`, is not among them.
The fixed part offers nothing that `pietto check` refuses, such as a retired
header word, `satisfying`, `semi join` or the PostgreSQL extension functions,
and no window function. It never waits for a pending analysis: the server
answers it as soon as it reads the request, which can be after an analysis
that is already running ends. It has no trigger characters. A word that is
both a keyword and an aggregate, such as `first`, appears once as each.

On a development host of VS Code 1.145.2 with default settings and the Pietto
extension, the keywords and builtins alone replaced the editor's word-based
suggestions in a `.pietto` file: the start of a field, `let` or relation name
of the open file had "No suggestions.", while the extension's snippets stayed.
The names of the file are in the list so that they are still suggested. Words
of other open files, which VS Code's word-based suggestions can offer, are
not.

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
