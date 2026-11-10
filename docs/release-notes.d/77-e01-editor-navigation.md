### Editor navigation — independent editor work package

The alpha `pietto lsp` server now provides hover and go-to-definition for
resolved type and `from` references, plus document symbols for named top-level
declarations. Configured schema-v2 projects retain exact import and re-export
targets; single-file constants and relationship templates appear in source order.

The server answers from facts attached to its current analysis. Unknown,
conflicting, omitted or stale facts produce no navigation result; a request
does not reparse, compile or read disk. Builtin types have hover text and no
authored definition. Field, let, parameter and function-call navigation,
workspace symbols and filesystem watching remain outside this first version.

Standard LSP capability negotiation handles hover and symbol response formats.
Existing diagnostic codes, CLI JSON, semantic metadata and relation-column
formats are unchanged. This is the independently authorized editor line,
not an additional MySQL slice or a Marketplace release.
