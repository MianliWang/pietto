# Editor focused R1 terminal

Status: `FAILED_BEFORE_COLLECTION`.

The isolated editor candidate build and local environments completed on the
qualified host with more than 8 GiB available memory. Both offline `uv pip
check` calls passed. The artifacts are:

- wheel `pietto-0.1.10-py3-none-any.whl`, SHA-256
  `9d2b31b0fa72ee40b1f671b5aa50f5eb0fedc83fdc19fe3d20bf2378e2921dd2`;
- sdist `pietto-0.1.10.tar.gz`, SHA-256
  `3639469b78ba7ca78cb42d590ebd7c608767707e5f4cee98b3537229674bc7bf`;
- installed-wheel Python
  `runtime/editor-runtime/installed-wheel/bin/python`.

The one focused pytest launch exited 3 before collecting any test. Its runner
set `PYTEST_DEBUG_TEMPROOT` to a child path but did not create that child's
parent directory. Pytest therefore raised `FileNotFoundError` while creating
its base temporary directory. Golden checking did not start. This is a runner
defect, not a product test failure.

Candidate binding remained exact: temporary-index tree
`a5d300bb1e6a0216ee95b62552466f407cdc40cb` and tracked patch
`a1a867ec37151a58c38db75902c4f14b32bbbaf1967fa85c0cb17293f3aa6799` agree
before and after. The raw terminal and logs are retained under
`evidence/editor-focused-20261110T051000Z/run/`.

The minimal repair is to create `$RUN/tmp/pytest` before launching pytest, then
prepare a new R2 evidence directory and rerun the complete focused packet once.
R1 must not be overwritten or resumed. No candidate source change is needed.
