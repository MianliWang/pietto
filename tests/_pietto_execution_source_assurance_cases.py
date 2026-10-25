"""Named S06 source inputs; independent result expectations live in the checker."""

import json

import _pietto_sql_emission as emission
from _pietto_execution_rows_cases import (
    BLOCK_READS,
    CASES as ORIGINAL_CASES,
    build,
    seven_artifact,
)

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
# The admitted R2 families: R2 refines no expression block read yet.
REFINED = tuple(case for case in CASES if case not in BLOCK_READS)

R2_BOUND_RELATION = "phase66 r2 bound"
R2_BOUND_MAX = 2147483645

MIXED = """query result:
    from rows
    select:
        record_id = id
        rn = row_number() window(order by flag)
        previous = lag(id, 1, 9007199254740995) window(order by flag)
        peer_rank = rank() window(order by flag)
        fraction = percent_rank() window(order by flag)
        cumulative = cume_dist() window(order by flag)
        bucket = ntile(3) window(order by flag)
        rows_first = first_value(id) window(
            order by flag rows between 1 preceding and current row
        )
        peer_last = last_value(id) window(order by flag)
    qualify lead(id) window(order by flag) is not None or rn == 4
    order by:
        rn
    limit 4
"""

REPEATED = """table ranked:
    from rows
    select:
        record_id = id
        rn = row_number() window(order by flag)
        previous = lag(id, 1, 9007199254740995) window(order by flag)
    order by:
        flag
    limit 2
query result:
    union all ranked, ranked
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


def r2_bound_setup(target):
    if target == "postgres":
        relation = '"public"."' + R2_BOUND_RELATION + '"'
        columns = (
            '"order.id" INTEGER NOT NULL, "flag value" BOOLEAN, '
            '"text `""é" TEXT COLLATE "C" NOT NULL, '
            '"amount value" NUMERIC(9,2) NOT NULL, '
            '"ratio value" DOUBLE PRECISION NOT NULL'
        )
    elif target == "mysql":
        relation = "`phase66`.`" + R2_BOUND_RELATION + "`"
        columns = (
            "`order.id` INT NOT NULL, `flag value` TINYINT, "
            '`text ``"é` VARCHAR(64) CHARACTER SET utf8mb4 '
            "COLLATE utf8mb4_0900_bin NOT NULL, "
            "`amount value` DECIMAL(9,2) NOT NULL, `ratio value` DOUBLE NOT NULL"
        )
    else:
        raise ValueError("R2_BOUND_TARGET")
    rows = ",".join(
        f"({identifier},NULL,'r2',0.00,0.0)"
        for identifier in (1, R2_BOUND_MAX, R2_BOUND_MAX)
    )
    return (
        (f"CREATE TABLE {relation} ({columns})", ()),
        (
            "INSERT INTO "
            + relation
            + ' ("order.id","flag value","text `""é","amount value","ratio value") '
            + "VALUES "
            + rows,
            (),
        )
        if target == "postgres"
        else (
            "INSERT INTO "
            + relation
            + ' (`order.id`,`flag value`,`text ``"é`,`amount value`,`ratio value`) '
            + "VALUES "
            + rows,
            (),
        ),
    )


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
        source = contract["sources"][0]
        source["relation"]["name"] = R2_BOUND_RELATION
        source["fields"][0]["representation"] = {
            "storage": {"kind": "pg_int4" if target == "postgres" else "my_int"},
            "nullable": False,
            "domain": {
                "kind": "int_range",
                "min": "1",
                "max": str(R2_BOUND_MAX),
            },
        }
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
