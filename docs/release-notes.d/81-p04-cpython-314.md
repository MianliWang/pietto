### CPython 3.14

The compiler and CLI are now verified with CPython 3.14 on Linux x86-64,
beside 3.12 and 3.13. On 3.14, as on each of them, CI runs a compiler and
package job, six runtime partitions, a completion job and a Windows job:
30 jobs in all with the three target jobs, which stay on 3.13. The package
declares the `Programming Language :: Python :: 3.14` classifier, and
`requires-python` stays `>=3.12`.

- On CPython 3.14 the extras, the SQLite build, `save` and R2 are stated
  only as measured, not claimed: uv's CPython 3.14.5 links the qualified
  SQLite 3.53.1 build, while a CPython 3.14 that links another SQLite, as
  Ubuntu's does, is refused by `save`, the saved-result calls, R2 and the
  `sqlite_file` route, as on any other build
  ([platforms and qualification](../capabilities.md#platforms-and-qualification)).
