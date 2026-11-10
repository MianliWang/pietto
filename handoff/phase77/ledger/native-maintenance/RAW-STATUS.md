# Runtime raw-status boundary

The historical `/tmp/pietto-p77-maint-*` directories are no longer present in
the current workspace. No raw report, resource journal, relay journal,
`verdict.json`, or `compare.json` was regenerated.

MySQL R8 has a recorded launcher request only: the session ends immediately
after `call_d9557f7ad9534b8e8ed8ba110d478165`, before a tool result. Therefore
the following facts are `UNKNOWN`: actual start, full native check, external
judge, verdict creation, cleanup, and pass/fail. The R8 run must not be
described as a passing database qualification.

PostgreSQL has tool-preserved worker reports of TLS R2 pass (18/18) and
remaining R4 pass. Their original raw files are currently unavailable, so this
recovery preserves the evidence layer and transcript locations rather than
reconstructing synthetic raw files.
