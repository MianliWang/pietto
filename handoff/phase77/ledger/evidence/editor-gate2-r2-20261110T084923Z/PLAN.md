# Editor combined Gate 2 R2

R1 (`editor-gate2-r1-20261110T083050Z`) completed without resource pressure
(min MemAvailable 26.7 GB, no `rg` process) and exited 1: 27,618 passed,
41 skipped, 1 failed. The failure,
`tests/test_execution_compatibility.py::test_artifact_law_accepts_exact_declarations_and_rejects_coordinated_damage`,
is a defect of the M77 maintenance patch shared by both candidates: the
D1 damage regex in `tests/_pietto_execution_installation_check.py` still
matched `pyarrow==26.0.0`, so after the 26.0.1 pin the damage was a no-op.
Causal repair (one C, maintenance): the regex now derives the version from
the checker's own `ARROW["pyarrow"]`, applied identically to
`candidates/maintenance` and `candidates/editor-combined`; the owner file
passes in both (`m77-damage-regex-fix-20261110T084901Z/`). Test-only change:
wheel and sdist (no tests in the sdist) and the package receipt are unchanged.

New bindings: editor-combined tree `d927402b`, patch `76bbac7a`;
maintenance tree `fd63dc9c`, patch `3900846a`. The launcher differs from
R1 only in those two expectations and the scratch path
(`launcher-delta-from-r1.diff`). Same 8 workers, same six gates.
