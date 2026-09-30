"""Named S06 source inputs; independent result expectations live in the checker."""

import json

import _pietto_phase66_sql_emission_probe as emission
from _pietto_phase68_slice5_cases import CASES as ORIGINAL_CASES, build, seven_artifact

CASES = (
    ORIGINAL_CASES
    + (
        ("R2_mixed", "joint"),
        ("R2_repeated", "tied_limit"),
    )
    + tuple(
        ("R2_seven", f"{precision}_{state}")
        for precision in (39, 65)
        for state in ("values", "empty", "null")
    )
)

MIXED = """query result:
    from rows
    select:
        record_id = id
        rn = row_number() window:
            order by:
                flag
        previous = lag(id, 1, 9007199254740995) window:
            order by:
                flag
        peer_rank = rank() window:
            order by:
                flag
        fraction = percent_rank() window:
            order by:
                flag
        cumulative = cume_dist() window:
            order by:
                flag
        bucket = ntile(3) window:
            order by:
                flag
        rows_first = first_value(id) window:
            order by:
                flag
            rows between 1 preceding and current row
        peer_last = last_value(id) window:
            order by:
                flag
    qualify:
        lead(id) window:
            order by:
                flag
        is not null or rn == 4
    order by:
        rn
    limit 4
"""

REPEATED = """table ranked:
    from rows
    select:
        record_id = id
        rn = row_number() window:
            order by:
                flag
        previous = lag(id, 1, 9007199254740995) window:
            order by:
                flag
    order by:
        flag
    limit 2
query result:
    union all:
        from ranked
        from ranked
"""


BOUND = """query result:
    from rows
    where id > 0
    select:
        record_id = id
        shifted = id + 1
    order by:
        id
    limit 4
"""


def fixture(target, case, variant):
    if case not in ("R2_mixed", "R2_repeated", "R2_bound"):
        return emission.fixture(target, case, variant)
    base = emission.fixture(target)
    header = base["source"].split("table result:", 1)[0]
    contract = json.loads(base["contract"])
    contract["environment"].append(
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": "quoted_exact"
            if target == "postgres"
            else "lower_case_table_names=0",
        }
    )
    if case == "R2_bound":
        contract["environment"].append(
            dict(
                key="parameter_protocol",
                scope="statement",
                value="postgres_extended" if target == "postgres" else "mysql_prepared",
            )
        )
    return {
        "source": header
        + (MIXED if case == "R2_mixed" else BOUND if case == "R2_bound" else REPEATED),
        "contract": emission.encoded(contract).decode(),
        "policy": "bind_safe_literals" if case == "R2_bound" else "preserve_literals",
    }


def original(directory, target, case, variant):
    if case == "R2_seven":
        precision, state = variant.split("_", 1)
        return seven_artifact(directory, target, precision=int(precision), state=state)
    if case in ("R2_mixed", "R2_repeated", "R2_bound"):
        item = fixture(target, case, variant)
        checked, result = emission.build_case(
            directory, item["source"], item["contract"], item["policy"]
        )
        if not checked.verified or result.status != "VERIFIED":
            raise ValueError(
                (
                    case,
                    result.status,
                    tuple((b.code, b.detail) for b in result.blockers),
                    tuple((d.code, d.message) for d in result.diagnostics),
                )
            )
        return result.artifact
    result = build(directory, target, case, variant)
    if result.status == "BLOCKED":
        return None
    return result.artifact


def source_requirements(artifact, providers, role):
    from pietto._project.project_execution_source import RetainedSourceRequirement

    requirements = []
    for source in artifact.request.sources:
        matching = tuple(
            p
            for p in providers
            if (p["namespace"], p["name"]) == (source.namespace, source.name)
        )
        if len(matching) != 1:
            raise ValueError("provider fixture correspondence")
        p = matching[0]
        requirements.append(
            RetainedSourceRequirement(
                source,
                p["provider"],
                p["version"],
                p["revision"],
                p["namespace"],
                p["registry"],
                p["definition"],
                tuple(p["tokens"]),
                role,
                "Owned fixture: immutable token/payload and complete visible domain; version retained until explicit target cleanup.",
            )
        )
    return tuple(requirements)
