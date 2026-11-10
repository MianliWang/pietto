# Actual checks

No target, network, Docker command, database connection, product source edit,
manifest edit, PostgreSQL parent edit, test suite, Git mutation, commit or
publication was run for this preparation.

| Check | Command | Result |
| --- | --- | --- |
| Pure positive/negative receipt checks | `UV_PYTHON=3.13.13 UV_OFFLINE=1 UV_NO_SYNC=1 uv run python /tmp/pietto-p77-s15-prep/s15_pure_judge.py --self-check` | passed |
| Syntax compilation | `UV_PYTHON=3.13.13 UV_OFFLINE=1 UV_NO_SYNC=1 uv run python -m py_compile /tmp/pietto-p77-s15-prep/s15_pure_judge.py` | passed |

The first sandboxed attempt to run the first command could not create uv's
cache lock; the recorded passing run used the same offline command after the
normal sandbox escalation.  It did not run a target experiment.
