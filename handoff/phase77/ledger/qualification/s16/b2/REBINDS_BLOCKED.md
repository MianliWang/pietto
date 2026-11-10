# S16 B2 input rebind — blocked

The requested B2 tree is
`9e688596fdb52667531b120d10ace4d836c426f2`; the supplied wheel is
`pietto-0.1.10-py3-none-any.whl` with SHA-256
`b7f62d1174361257fe065b8718ef1741555b078367405aa425d3c6d452e115b3`.
The shared judge file has SHA-256
`6641e9180c6d54b903b2140f46a89453999fb3d69820ea0ab9ac36eaa4960bf1`.

Using the B2 tree's public project compiler on the frozen S16 source and
contract produced PostgreSQL `VERIFIED`, but MySQL remained `BLOCKED` with:

```text
PIE-B1003 window_default_literal_kind_not_realized_yet
```

The B2 source contains part of the later S16 work (`X'hex'` rendering), but
does not contain the finalized empty-Text and target-token/pure-boundary
admission patch. Therefore it cannot produce the required MySQL public
artifact, reader or compiled-replay identity. No B2 MySQL plan JSON is written
from a blocked artifact.

This is a mechanical input-rebind observation, not a database run or a
qualification result. Rebuild this directory only after a B2 candidate tree
containing the reviewed S16 patch is named and frozen.
