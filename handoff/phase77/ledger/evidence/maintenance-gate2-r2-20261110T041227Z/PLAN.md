# M77 maintenance Gate 2 R2 prepared command

This packet is preparation only. It follows R1's preserved
`RESOURCE_PRESSURE_ABORTED` / exit-75 terminal and does not claim Gate 2,
native database, publication, or natural-CI success.

The launcher first records and fail-closes on the candidate binding:

- `HEAD=f8ccd2c44a2d9adf431a496bd9bbae037783176f`;
- baseline `HEAD^{tree}` `460e3e135d1dcb0b926928bc2632a889410f258a` and
  dirty temporary-index tree `2af0e2e47a062eb747ed5d2cd664c2dab5da4aed`;
- `uv.lock` SHA-256 `b2cc96b25b0b9f2225c4529f0123ae869cd804af0578b4f83c931a15aa893064`;
- dirty patch SHA-256 `548e72276b20c2bff3bb0613a527ef230fb9095942b562dca32a6150da12e1cc`;
- retained wheel SHA-256 `f4c96921c4d4ceb057830f2dd21f2e634325dac2bef933532747ae4aab963a73`;
- retained sdist SHA-256 `15b43b884064e0837bbfa891b8eea44996acc2592bd169b5a6ea96e29d29cfff`.

It requires the editable, Arrow-free `runtime/venvs/core-dev` CPython 3.13.13
runtime; CPython 3.12.13, Java 21, Node, non-shallow Git, an actual IPv4
loopback bind, and a writable qualified ext4 temporary root. It records only a
resource snapshot; it intentionally does not inspect host processes, so it
does not claim host-process exclusivity.

The single owner-authorized START command is:

```bash
cd /home/mianliwang/projects/pietto
PIETTO_M77_GATE2_START=YES \
  .cache/phase77-recovery/evidence/maintenance-gate2-r2-20261110T041227Z/run-gate2-r2.sh
```

The authoritative command is exactly the documented host invocation through
the recovered core runtime. `UV_PROJECT_ENVIRONMENT` is the absolute recovered
`core-dev` venv and the Gate-owned cache is seeded from the verified
`candidates/maintenance/.uv-runtime-cache` before the first `uv` call:

```text
UV_PYTHON=3.13.13 UV_OFFLINE=1 UV_NO_SYNC=1 UV_LOCKED=1 UV_PYTHON_DOWNLOADS=never \
  UV_CACHE_DIR=<evidence>/run/uv-cache UV_PROJECT_ENVIRONMENT=<core-dev-absolute-path> \
  <core-dev-python> -B scripts/validate.py \
  --timings --oom-guard on --pytest-workers 8 --pytest-maxprocesses 4 --pytest-dist loadfile
```

It is followed only if that command exits zero by `scripts/package_smoke.py`
against the already-bound retained `runtime/dist` wheel and sdist. Passing
`--dist-dir` prevents a rebuild; the Arrow installed cell receives a new
evidence-owned venv. The launcher records every command, raw combined log, exit
code, preflight, environment facts, temporary-index before/after bindings, and
the trap's actual terminal exit in `run/`.

Auxiliary selection follows the actual candidate input closure:

- `package-smoke`: required (`pyproject.toml`, `uv.lock`, package reader and
  installation contracts changed), using the existing bound artifacts only.
- `generated`: not selected (no grammar, ANTLR provenance, or generated-file
  path changed).
- `golden`: not selected (no parser, semantic/IR/SQL emitter, golden fixture,
  or golden owner changed).
- fresh MySQL full execution: not launched here; the separately accepted
  `mysql-maintenance-r2-20261109T030000-0500` evidence remains separate.
- PostgreSQL execution: not launched here; its fresh rebind remains pending.
- Teach/bootstrap: prohibited. The only `scripts/ci_workloads.py` delta is the
  Arrow version literal and preflight rejects bootstrap/split terms.
