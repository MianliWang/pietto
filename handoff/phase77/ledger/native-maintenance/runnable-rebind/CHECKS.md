# New-reconstruction checks

Completed without database, Docker, network, installation, or launcher
execution:

- `campaign.py`, `relay.py`, `judge.py`, `preflight.py`, and `selfcheck.py`
  parse with CPython 3.13.13.
- `mysql.sh` passes `sh -n`.
- `campaign.py` SHA-256 is
  `c2c38ce086a19e56ccbb45c9d46b74763e915d242bc914398735725e8ef56fbd`.

The full no-DB `selfcheck.py` was attempted only against the isolated recovery
candidate and a non-package hash placeholder. It reached the finite IPC check,
then failed because the local CPython 3.13.13 environment cannot import
`pyarrow`; the captured child terminal says `ModuleNotFoundError: No module
named 'pyarrow'`. The local uv archive contains PyArrow 26.0.0 and older copies,
not the required 26.0.1 artifact. No dependency was installed or downloaded.

This is a fresh-reconstruction dependency-closure blocker. It does not reuse
the historical no-DB self-check PASS, and it does not imply a native pass.
