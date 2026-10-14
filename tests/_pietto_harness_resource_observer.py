"""Bounded passive observations of a current, explicitly owned test container."""

from __future__ import annotations

import json
import math
import re
import time
from typing import Any, Callable


_CPU = re.compile(r"([0-9]+(?:\.[0-9]+)?)%")
_BYTES = re.compile(r"([0-9]+(?:\.[0-9]+)?)(B|kB|MB|GB|KiB|MiB|GiB)")
_FACTORS = {
    "B": 1,
    "kB": 1000,
    "MB": 1000**2,
    "GB": 1000**3,
    "KiB": 1024,
    "MiB": 1024**2,
    "GiB": 1024**3,
}
_CONTAINER_IDENTITY = ("id", "name", "image", "labels", "running", "pid", "started_at")
_MAX_RAW_FIELD_CHARS = 128


def _number(
    value: object, pattern: re.Pattern[str], factors: dict[str, int] | None = None
) -> int | float | None:
    if not isinstance(value, str):
        return None
    match = pattern.fullmatch(value.strip())
    if match is None:
        return None
    numeric = float(match.group(1))
    if not math.isfinite(numeric) or numeric < 0:
        return None
    return int(numeric * factors[match.group(2)]) if factors is not None else numeric


def _raw_field(value: object) -> str | None:
    return (
        value if isinstance(value, str) and len(value) <= _MAX_RAW_FIELD_CHARS else None
    )


def _owned(resource: Any, observation: dict[str, Any]) -> None:
    if resource.container_id is None or observation.get("id") != resource.container_id:
        raise ValueError("container id mismatch")
    if resource.owned("container", observation) is not True:
        raise ValueError("foreign container")
    if (
        observation.get("running") is not True
        or type(observation.get("pid")) is not int
        or not isinstance(observation.get("started_at"), str)
        or not observation["started_at"]
    ):
        raise ValueError("container start identity unavailable")


def _stats(resource: Any, before: dict[str, Any]) -> dict[str, object]:
    raw = json.loads(
        resource.docker(
            "stats",
            "--no-stream",
            "--format",
            "{{json .}}",
            resource.container_id,
            timeout=10,
        )
    )
    if not isinstance(raw, dict):
        raise ValueError("malformed Docker stats")
    identifier, name = raw.get("ID"), raw.get("Name")
    if (
        not isinstance(identifier, str)
        or not identifier
        or not before["id"].startswith(identifier)
        or name != before["name"].lstrip("/")
    ):
        raise ValueError("Docker stats identity mismatch")
    usage = raw.get("MemUsage")
    used, limit = (
        (usage.split(" / ", 1) + [None])[:2] if isinstance(usage, str) else (None, None)
    )
    return {
        "container_cpu_percent": _number(raw.get("CPUPerc"), _CPU),
        "container_memory_used_bytes": _number(used, _BYTES, _FACTORS),
        "container_memory_limit_bytes": _number(limit, _BYTES, _FACTORS),
        "docker_stats_raw": {
            key: _raw_field(raw.get(key))
            for key in ("ID", "Name", "CPUPerc", "MemUsage", "PIDs")
        },
    }


def _database_clock(resource: Any) -> dict[str, object]:
    try:
        with resource.manager.cursor() as cursor:
            if resource.target == "postgres":
                cursor.execute(
                    "SELECT (extract(epoch FROM clock_timestamp()) * 1000000000)::bigint"
                )
                value, unit = cursor.fetchone()[0], "ns"
            else:
                cursor.execute(
                    "SELECT CAST(UNIX_TIMESTAMP(CURRENT_TIMESTAMP(6)) * 1000000 AS UNSIGNED)"
                )
                value, unit = cursor.fetchone()[0], "us"
    except Exception as error:
        return {
            "database_clock": None,
            "database_clock_unit": None,
            "database_clock_unobserved": type(error).__name__,
        }
    if type(value) is not int or value < 0:
        return {
            "database_clock": None,
            "database_clock_unit": None,
            "database_clock_unobserved": "malformed_value",
        }
    return {
        "database_clock": value,
        "database_clock_unit": unit,
        "database_clock_unobserved": None,
    }


def observe(
    resource: Any,
    *,
    wall_ns: Callable[[], int] = time.time_ns,
    monotonic_ns: Callable[[], int] = time.monotonic_ns,
) -> dict[str, object]:
    """Take one passive sample; callers own the bounded sample schedule."""
    before = resource.measurement_container_observation(timeout=10)
    _owned(resource, before)
    client_before, monotonic_before = wall_ns(), monotonic_ns()
    clock = _database_clock(resource)
    client_after, monotonic_after = wall_ns(), monotonic_ns()
    stats = _stats(resource, before)
    after = resource.measurement_container_observation(timeout=10)
    _owned(resource, after)
    if any(after[key] != before[key] for key in _CONTAINER_IDENTITY):
        raise ValueError("container identity changed during observation")
    ordered = client_after >= client_before and monotonic_after >= monotonic_before
    value, unit = clock["database_clock"], clock["database_clock_unit"]
    scale = 1 if unit == "ns" else 1000 if unit == "us" else None
    bounds = (
        None
        if not ordered or type(value) is not int or scale is None
        else {
            "lower_ns": value * scale - client_after,
            "upper_ns": value * scale - client_before,
        }
    )
    return {
        "container": {key: before[key] for key in _CONTAINER_IDENTITY},
        "container_pid_namespace": "NOT_OBSERVED",
        "client_realtime_before_ns": client_before,
        "client_realtime_after_ns": client_after,
        "client_monotonic_before_ns": monotonic_before,
        "client_monotonic_after_ns": monotonic_after,
        "database_client_realtime_offset_bounds_ns": bounds,
        "client_clock_unobserved": None if ordered else "client_clock_jump",
        **clock,
        **stats,
    }
