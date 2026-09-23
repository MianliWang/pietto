"""Real-source private emission observations through the existing process matrix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import _pietto_phase66_sql_emission_probe as emission

__all__ = ("observation", "render")
SEED_ENVIRONMENT = "PIETTO_PHASE66_SLICE14_AMBIENT"
FORMAT = "pietto.phase66-sql-emission-observation-differential.v1"
# The per-request envelope of this family's product bytes.
MAX_OBSERVATION_BYTES = 8 * 1024 * 1024
TARGETS = ("postgres", "mysql")
# Both dialects over: an imported direct chain; typed bound fixed values; a
# nested EXCEPT fold; a SEMI membership; hidden-window QUALIFY stages; hidden
# grouping; the three ORDER carriers; and one INPUT_REJECTED and one BLOCKED
# outcome that keep only their existing public failure bytes.
CORPUS = (
    ("N_imported_chain", "bag"),
    ("R_fixed_direct", "table_bind"),
    ("S_set_nesting", "left_fold_except"),
    ("W_join_shapes", "semi"),
    ("A_window_qualify", "hidden"),
    ("X_aggregate_grouped", "hidden"),
    ("O_named_later", "order_ordinary"),
    ("O_named_later", "order_rebound"),
    ("O_named_later", "order_completed"),
    ("K_emission_rejected", "duplicate_selector"),
    ("L_emission_blocked", "missing_source"),
)


def _summary(view) -> dict[str, object]:
    """Bounded lookups over the decoded view; every value is data."""
    kinds: dict[str, int] = {}
    for ref in view.order:
        kinds[ref.kind] = kinds.get(ref.kind, 0) + 1
    parameters = [r for r in view.ranges if r.kind == "parameter"]
    return {
        "records": kinds,
        "sql_bytes": len(view.sql),
        "ranges": len(view.ranges),
        "at_end": len(view.at(len(view.sql))),
        "first": [r.position for r in view.at(0)],
        "parameters": [
            [r.start, r.end, [hit.position for hit in view.at(r.start)]]
            for r in parameters
        ],
    }


def observation(workspace: Path) -> dict[str, object]:
    from pietto._project import project_sql_emission_portable as portable
    from pietto._project import project_sql_emission_pure_boundary as pure
    from pietto._project.project_sql_emission import serialize_project_sql_emission

    cases = []
    for target in TARGETS:
        for case, variant in CORPUS:
            item = emission.fixture(target, case, variant)
            _, outcome = emission.build_case(
                workspace / target / case / variant,
                item["source"],
                item["contract"],
                item["policy"],
            )
            record: dict[str, object] = {
                "target": target,
                "case": case,
                "variant": variant,
                "status": outcome.status,
            }
            artifact = outcome.artifact
            if artifact is None:
                # A non-positive outcome has no artifact and so no private document.
                refused = portable.export_emission_observation(outcome, None)
                assert refused.status is portable.ObservationStatus.INVALID_ROOT
                assert refused.canonical_bytes is None
                record["public"] = serialize_project_sql_emission(outcome).decode()
                cases.append(record)
                continue
            observed = portable.export_emission_observation(artifact, artifact.request)
            assert observed.status is portable.ObservationStatus.OK
            data = observed.canonical_bytes
            assert data is not None
            checked = portable.verify_emission_observation(
                data, artifact, artifact.request
            )
            assert checked.corresponds, checked.issues
            decoded = pure.parse_emission_observation(data)
            assert decoded.status is pure.Status.OK and decoded.view is not None
            assert decoded.canonical_bytes == data
            record["document"] = data.decode("utf-8")
            record["summary"] = _summary(decoded.view)
            record["truncated"] = pure.parse_emission_observation(data[:-2]).status
            cases.append(record)
    duplicate = pure.parse_emission_observation(b'{"format":"x","format":"x"}')
    return {
        "format": FORMAT,
        "cases": cases,
        "duplicate_key": duplicate.status,
    }


def render(value: object, workspace: Path) -> bytes:
    assert isinstance(workspace, Path)
    data = (
        json.dumps(
            value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        ).encode("utf-8")
        + b"\n"
    )
    assert len(data) <= MAX_OBSERVATION_BYTES
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    arguments = parser.parse_args(argv)
    try:
        output = render(observation(arguments.workspace), arguments.workspace)
    except Exception:
        sys.stderr.write("Phase66 private observation probe failed.\n")
        return 1
    sys.stdout.buffer.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
