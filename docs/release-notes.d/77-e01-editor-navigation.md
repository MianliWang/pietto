### Editor navigation — independent editor work package

The alpha `pietto lsp` server now provides hover and go-to-definition for
resolved type and `from` references, plus document symbols for named top-level
declarations. Configured schema-v2 projects retain exact import and re-export
targets; `def` functions, relationship templates and single-file constants
appear in source order.

The server answers from facts attached to its current analysis; a request sent
while an analysis of its document or project root is pending waits for it.
Beside a project module with an error, the other modules keep their facts, but
no use navigates into that module. Unknown, conflicting, omitted or stale
facts, and a legacy-flat root, produce no navigation result; a request does
not reparse, compile or read disk. Builtin types have hover text and no
authored definition. Field, let, parameter and function-call navigation,
including a `from` that reads a relation let or a table-function input,
workspace symbols and filesystem watching remain outside this first version.

Standard LSP capability negotiation handles hover and symbol response formats.
A `file:` URI whose host does not parse, such as `file://[::1/x.pietto`, no
longer stops the server: it is checked as a standalone document. Existing
diagnostic codes, CLI JSON, semantic metadata and relation-column formats are
unchanged. This is the independently authorized editor line,
not an additional MySQL slice or a Marketplace release.
