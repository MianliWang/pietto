"""The published one-source emission fixture with a header-parameter query."""

from __future__ import annotations

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
    item = probe.parameterized_fixture(target, body, policy, protocol=protocol)
    return probe.build_case(
        root / target / policy, item["source"], item["contract"], policy
    )
