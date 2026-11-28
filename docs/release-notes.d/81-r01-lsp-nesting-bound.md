### Editor messages nested more than 1000 deep

The alpha `pietto lsp` server now reads a message body only when its arrays
and objects nest at most 1000 deep, counted outside strings before the body
is decoded. A deeper body receives JSON-RPC `-32700` `Parse error` with a
null id, as invalid JSON does, and the session goes on. Until now the
Python interpreter decided: its `json` refused a body only past its own
recursion limit, so the depth that became a parse error differed between
interpreters and platforms.

Before (measured at `588d9093` on Linux with uv's CPython 3.12.13, 3.13.13
and 3.14.5, by the answer of a `pietto lsp` process to one framed body of
nested arrays, of nested objects or of both): a body was a parse error
from 9998 levels on 3.12.13, from 9999 on 3.13.13 and from 40124 on
3.14.5, while natural CI's CPython 3.14.10 on Linux read a body of
100,000 levels and answered `-32600`. After: on each of the three a body
of 1000 levels is read and one of 1001 levels is a parse error; the bound,
not the interpreter, decides. A body that any of the three refused is
still refused. The CLI commands, CLI JSON and PIE codes are unchanged. The
surface is alpha until the Phase82 freeze.
