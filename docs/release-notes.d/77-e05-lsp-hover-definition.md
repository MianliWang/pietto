### Editor hover and definition for fields, lets and calls — editor core work package

The alpha `pietto lsp` server now answers hover and definition on more uses,
each from a binding that the analysis already keeps, one fact per written
occurrence. In a single file, a field read of a JOIN relation shows
`field NAME` and, when it reads a source, defines the field of the source's
shape; a relationship call shows `relationship NAME` and defines its
template. In a schema-v2 project, a name that a `let` value, `select` item or
`where` of a relation without JOIN reads shows `field NAME` or `let NAME`
when the analysis bound it to exactly one input field or `let`: the field
defines its shape field when the relation reads a source, and the `let` its
binding. A `from` that reads a relation let now shows `let NAME` and defines
that let.

Every other use still has no hover or definition. In a single file, that is
any other read, such as one of a relation without JOIN, and a `let` use. In a
project, it is any other read, such as a JOIN relation's reads or a
`group by`, `order by` or window read, and a relationship call. In both, it
is a `def` call or parameter, a relationship parameter, a relationship call's
argument and a `from` that reads a table-function input. The facts come
from the analysis that the diagnostics come from, with no new check and no
file read. Diagnostics, document and workspace symbols, links and formatting
are unchanged, and so are the CLI commands, CLI JSON, PIE codes, semantic
metadata and relation-column formats. The surface is alpha until the Phase82
freeze.
