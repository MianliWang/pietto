# S16 B2 runtime rebind

This directory is a fresh input rebind, not a new oracle or database result.
It is built from the B2 candidate tree
`9e688596fdb52667531b120d10ace4d836c426f2` and the exact wheel
`pietto-0.1.10-py3-none-any.whl` with SHA-256
`b7f62d1174361257fe065b8718ef1741555b078367405aa425d3c6d452e115b3`.

The parent plan's source shape, DDL, typed seed and mathematical window oracle
are unchanged. The B2 plans independently recompile the source and bind the
public artifact, fixed values, parameter uses, columns, compiled payload and
compiled replay SQL to the B2 tree and wheel identity. They remain
`PREPARED_NOT_STARTED`: no container, database, native reader, qualification
or Gate 2 result is present.
