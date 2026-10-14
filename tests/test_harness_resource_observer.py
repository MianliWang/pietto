"""The bounded, identity-bound resource-observer harness contract."""

from __future__ import annotations

from contextlib import nullcontext
import json

import pytest

import _pietto_harness_resource_observer as observer
import _pietto_execution_public_journey_runner as runner


class _Cursor:
    def execute(self, text: str) -> None:
        assert "clock_timestamp" in text

    def fetchone(self) -> tuple[object, ...]:
        return (1_800_000_000_000_000_000,)

    def __enter__(self):
        return self

    def __exit__(self, *_: object) -> bool:
        return False


class _Manager:
    def cursor(self):
        return _Cursor()


class _Resource:
    container_id = "a" * 64
    name = "pietto-owned"
    nonce = "nonce"
    target = "postgres"
    manager = _Manager()

    @staticmethod
    def measurement_container_observation(*, timeout):
        assert timeout == 10
        return {
            "id": "a" * 64,
            "name": "/pietto-owned",
            "image": "sha256:" + "b" * 64,
            "labels": {"pietto.phase66.invocation": "nonce"},
            "running": True,
            "pid": 77,
            "started_at": "2026-10-13T00:00:00Z",
        }

    @staticmethod
    def owned(kind, value):
        return kind == "container" and value["labels"] == {
            "pietto.phase66.invocation": "nonce"
        }

    @staticmethod
    def docker(*args, timeout):
        assert args[:3] == ("stats", "--no-stream", "--format") and timeout == 10
        return json.dumps(
            {
                "ID": "a" * 12,
                "Name": "pietto-owned",
                "CPUPerc": "1.25%",
                "MemUsage": "4.00MiB / 1.00GiB",
                "PIDs": "3",
            }
        )


def test_observation_keeps_container_and_database_clock_domains_explicit():
    result = observer.observe(_Resource())
    assert result["container_cpu_percent"] == 1.25
    assert result["container_memory_used_bytes"] == 4 * 1024**2
    assert result["database_clock_unit"] == "ns"
    assert result["container_pid_namespace"] == "NOT_OBSERVED"


def test_stats_identity_mismatch_is_refused():
    class Wrong(_Resource):
        @staticmethod
        def docker(*args, timeout):
            return json.dumps(
                {
                    "ID": "f" * 12,
                    "Name": "pietto-owned",
                    "CPUPerc": "0.00%",
                    "MemUsage": "0B / 1.00GiB",
                }
            )

    with pytest.raises(ValueError, match="identity"):
        observer.observe(Wrong())


def test_unknown_stats_fields_are_null_and_a_client_clock_jump_has_no_offset():
    class Unknown(_Resource):
        @staticmethod
        def docker(*args, timeout):
            return json.dumps(
                {
                    "ID": "a" * 12,
                    "Name": "pietto-owned",
                    "CPUPerc": "NaN%",
                    "MemUsage": "unknown",
                    "unexpected": "not retained",
                }
            )

    values = iter((200, 201, 199, 202))
    result = observer.observe(
        Unknown(),
        wall_ns=lambda: next(values),
        monotonic_ns=lambda: next(values),
    )
    assert result["container_cpu_percent"] is None
    assert result["container_memory_used_bytes"] is None
    assert result["database_client_realtime_offset_bounds_ns"] is None
    assert result["client_clock_unobserved"] == "client_clock_jump"
    docker_stats = result["docker_stats_raw"]
    assert isinstance(docker_stats, dict)
    assert "unexpected" not in docker_stats


def test_malformed_database_clock_is_unknown_not_zero():
    class BadCursor(_Cursor):
        def fetchone(self) -> tuple[object, ...]:
            return (True,)

    class BadManager:
        def cursor(self):
            return BadCursor()

    class BadClock(_Resource):
        manager = BadManager()

    result = observer.observe(BadClock())
    assert result["database_clock"] is None
    assert result["database_clock_unobserved"] == "malformed_value"


def _calibration_modules(events, cleanup_status="success"):
    class Resource:
        def __init__(self, target, pin, directory):
            self.target = target
            assert directory.is_dir()
            events.append(("init", target))

        def acquire(self):
            events.append(("acquire", self.target))

        def cleanup(self):
            events.append(("cleanup", self.target))
            return {
                "status": cleanup_status if self.target == "postgres" else "success"
            }

    class Resources:
        Resources = Resource

        @staticmethod
        def deadline(seconds):
            assert seconds == 20 * 60
            return nullcontext()

    class Observer:
        @staticmethod
        def observe(resource):
            events.append(("observe", resource.target))
            return {
                "container_cpu_percent": 1.0,
                "container_memory_used_bytes": 1,
                "container_memory_limit_bytes": 2,
                "database_clock": 3,
                "database_client_realtime_offset_bounds_ns": {"lower_ns": 0},
            }

    return Resources, Observer


def test_calibration_closes_one_target_before_acquiring_the_next(tmp_path):
    events = []
    resources, calibration_observer = _calibration_modules(events)
    rows, interrupted = runner._measure_targets(
        {"targets": {"postgres": {}, "mysql": {}}},
        tmp_path,
        resources,
        calibration_observer,
    )
    assert interrupted is None
    assert [row["status"] for row in rows] == ["OBSERVED", "OBSERVED"]
    assert events == [
        ("init", "postgres"),
        ("acquire", "postgres"),
        ("observe", "postgres"),
        ("cleanup", "postgres"),
        ("init", "mysql"),
        ("acquire", "mysql"),
        ("observe", "mysql"),
        ("cleanup", "mysql"),
    ]


def test_calibration_cleanup_failure_blocks_the_second_target(tmp_path):
    events = []
    resources, calibration_observer = _calibration_modules(events, "failed")
    rows, _interrupted = runner._measure_targets(
        {"targets": {"postgres": {}, "mysql": {}}},
        tmp_path,
        resources,
        calibration_observer,
    )
    assert len(rows) == 1
    assert rows[0]["status"] == "CLEANUP_FAILED"
    assert events == [
        ("init", "postgres"),
        ("acquire", "postgres"),
        ("observe", "postgres"),
        ("cleanup", "postgres"),
    ]
