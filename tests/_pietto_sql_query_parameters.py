"""The published one-source emission fixture with a header-parameter query."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import _pietto_sql_emission as probe

PROTOCOL = {"postgres": "postgres_extended", "mysql": "mysql_prepared"}


def parameterized_case(
    root: Path,
    target: str,
    body: str,
    policy: str = "preserve_literals",
    *,
    protocol: bool = True,
) -> Any:
    """Build the fixture with ``body`` as its selected query ``result``.

    The contract adds exact identifier case and, unless ``protocol`` is false,
    the native parameter protocol every parameter read requires.
    """
    base = probe.fixture(target)
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
    if protocol:
        contract["environment"].append(
            {
                "key": "parameter_protocol",
                "scope": "statement",
                "value": PROTOCOL[target],
            }
        )
    source = base["source"].split("table result:", 1)[0] + body
    return probe.build_case(
        root / target / policy,
        source,
        probe.encoded(contract).decode(),
        policy,
    )
