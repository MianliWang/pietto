"""Deterministic local guard policy and tiny owned-process-group safety checks."""

from __future__ import annotations

from contextlib import ExitStack
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from types import SimpleNamespace
from typing import Any, cast

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate.py"
SPEC = (
    ROOT
    / "docs/spec/validation-performance-interlude-v-slice1-wsl-oom-emergency-guard-v1.md"
)


def _load():
    spec = importlib.util.spec_from_file_location("pietto_v5s1_validate", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast(Any, module)


v = _load()
GIB = 1024**3
MIB = 1024**2


@pytest.fixture(autouse=True)
def _local(monkeypatch):
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)


def sample(available=6 * GIB, *, total=8 * GIB, psi=None, events=(3, 2)):
    return v.MemorySample(total, available, psi, events)


def test_fixed_thresholds_and_retained_startup_policy():
    assert (v.OOM_SAMPLE_SECONDS, v.OOM_CRITICAL_BYTES, v.OOM_HARD_BYTES) == (
        1.0,
        768 * MIB,
        3 * GIB // 2,
    )
    assert (
        v.OOM_PRESSURE_BYTES,
        v.OOM_PSI_FULL_AVG10,
        v.OOM_CONSECUTIVE_SAMPLES,
        v.OOM_TERM_GRACE_SECONDS,
    ) == (3 * GIB, 4.0, 3, 5.0)
    assert v.RESOURCE_PRESSURE_EXIT == 75
    assert (
        v.PYTEST_WORKER_MEMORY_BYTES,
        v.PYTEST_MIN_MEMORY_RESERVE_BYTES,
        v.PYTEST_MAX_RESOURCE_WORKERS,
    ) == (512 * MIB, GIB, 4)
    assert v.PYTEST_DIST_CHOICES == ("loadfile", "loadscope")


@pytest.mark.parametrize(
    "current,reason",
    [
        (sample(768 * MIB), "critical_available"),
        (sample(0), "critical_available"),
        (sample(events=(4, 2)), "cgroup_oom_increased"),
        (sample(events=(3, 3)), "cgroup_oom_kill_increased"),
        (sample(events=(4, 3)), "cgroup_oom_kill_increased"),
    ],
)
def test_immediate_triggers_have_stable_priority(current, reason):
    assert v._pressure_trigger(current, sample(), 0)[0] == reason


@pytest.mark.parametrize(
    "current,reason",
    [
        (sample(3 * GIB // 2), "sustained_low_available"),
        (sample(3 * GIB, psi=4.0), "sustained_memory_pressure"),
        (sample((64 * GIB + 9) // 10, total=64 * GIB + 9), "sustained_low_available"),
        (
            sample((64 * GIB + 9) // 5, total=64 * GIB + 9, psi=4.0),
            "sustained_memory_pressure",
        ),
    ],
)
def test_noncritical_pressure_needs_three_consecutive_samples(current, reason):
    count = 0
    for expected in (None, None, reason):
        actual, count = v._pressure_trigger(current, sample(), count)
        assert actual == expected
    assert count == 3


def test_healthy_memory_resets_and_high_psi_alone_is_not_pressure():
    baseline = sample()
    count = 0
    for current, expected_count in [
        (sample(GIB), 1),
        (sample(GIB), 2),
        (sample(6 * GIB, psi=99), 0),
        (sample(GIB), 1),
        (sample(3 * GIB + 1, psi=4), 0),
        (sample(3 * GIB, psi=3.99), 0),
    ]:
        reason, count = v._pressure_trigger(current, baseline, count)
        assert reason is None and count == expected_count
    for _ in range(20):
        assert v._pressure_trigger(sample(events=(1, 0)), baseline, 0) == (None, 0)


def test_alternating_noncritical_causes_are_still_consecutive_pressure():
    count = 0
    for current in (sample(GIB), sample(3 * GIB, psi=4), sample(GIB)):
        reason, count = v._pressure_trigger(current, sample(), count)
    assert reason == "sustained_low_available" and count == 3


def test_optional_telemetry_and_gate_event_baseline():
    missing = sample(events=None)
    assert v._event_deltas(sample(events=(999, 999)), missing) == (None, None)
    assert v._event_deltas(missing, sample()) == (None, None)
    assert (
        v._pressure_trigger(sample(768 * MIB, events=None), missing, 0)[0]
        == "critical_available"
    )
    assert (
        v._pressure_trigger(sample(GIB, events=None), missing, 2)[0]
        == "sustained_low_available"
    )
    assert v._pressure_trigger(
        sample(events=(999, 999)), sample(events=(999, 999)), 0
    ) == (None, 0)


def test_cgroup_limits_use_existing_memory_interpretation_and_ignore_cache(monkeypatch):
    values = {
        "/proc/meminfo": f"MemTotal: {16 * GIB // 1024} kB\nMemAvailable: {8 * GIB // 1024} kB\nCached: {14 * GIB // 1024} kB\n",
        "/sys/fs/cgroup/memory.max": str(4 * GIB),
        "/sys/fs/cgroup/memory.current": str(GIB),
    }
    monkeypatch.setattr(v, "_read_text", values.get)
    current = v._memory_sample()
    assert current == sample(3 * GIB, total=4 * GIB, events=None)
    assert v._pressure_trigger(current, current, 2) == (None, 0)
    values["/sys/fs/cgroup/memory.current"] = str(4 * GIB + 1)
    assert v._memory_sample().available == 0
    values["/sys/fs/cgroup/memory.max"] = "max"
    assert v._memory_sample().total == 16 * GIB
    values["/sys/fs/cgroup/memory/memory.limit_in_bytes"] = str(2 * GIB)
    values["/sys/fs/cgroup/memory/memory.usage_in_bytes"] = str(GIB)
    assert v._memory_sample().available == GIB


@pytest.mark.parametrize(
    "text,expected",
    [
        (None, None),
        ("some avg10=99\nfull avg10=4.00 avg60=0 total=1", 4.0),
        ("full avg10=nan", None),
        ("full avg10=inf", None),
        ("full avg10=oops", None),
        ("full avg10=101", None),
    ],
)
def test_optional_psi_reader(monkeypatch, text, expected):
    monkeypatch.setattr(v, "_read_text", lambda _: text)
    assert v._memory_psi() == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        (None, None),
        ("oom 7\noom_kill 2\nhigh 123", (7, 2)),
        ("oom x\noom_kill 2", None),
        ("oom 0", None),
    ],
)
def test_optional_events_reader(monkeypatch, text, expected):
    monkeypatch.setattr(v, "_read_text", lambda _: text)
    assert v._memory_events() == expected


@pytest.mark.parametrize(
    "key,value", [("GITHUB_ACTIONS", "true"), ("CI", "1"), ("CI", "true")]
)
def test_auto_ci_never_reads_guard_telemetry(monkeypatch, capsys, key, value):
    monkeypatch.setenv(key, value)
    monkeypatch.setattr(v, "_memory_sample", lambda: pytest.fail("CI guard telemetry"))
    assert v._oom_guard_enabled("auto", v._build_parser()) is False
    assert capsys.readouterr().out == ""


def test_auto_local_and_missing_telemetry_modes(monkeypatch, capsys):
    monkeypatch.setattr(v.sys, "platform", "linux")
    monkeypatch.setattr(v, "_memory_sample", lambda: sample(events=None))
    assert v._oom_guard_enabled("auto", v._build_parser())
    monkeypatch.setattr(v, "_memory_sample", lambda: None)
    assert not v._oom_guard_enabled("auto", v._build_parser())
    assert capsys.readouterr().out.count("OOM guard unavailable") == 1
    with pytest.raises(SystemExit) as error:
        v._oom_guard_enabled("on", v._build_parser())
    assert error.value.code == 2


@pytest.mark.parametrize("unsupported", ["platform", "waitid", "reaper"])
def test_on_refuses_unsupported_setup_before_launch(monkeypatch, unsupported):
    monkeypatch.setattr(v, "_memory_sample", lambda: sample())
    monkeypatch.setattr(
        v.subprocess, "Popen", lambda *a, **kw: pytest.fail("child launched")
    )
    if unsupported == "platform":
        monkeypatch.setattr(v.sys, "platform", "darwin")
    elif unsupported == "waitid":
        monkeypatch.delattr(v.os, "waitid")
    else:
        monkeypatch.setattr(v.signal, "getsignal", lambda _: signal.SIG_IGN)
    with pytest.raises(SystemExit) as error:
        v.main(("--oom-guard", "on"))
    assert error.value.code == 2


def test_off_and_unavailable_auto_keep_the_old_run_path(monkeypatch, capsys):
    monkeypatch.setattr(v, "GATES", (("one", ("one",)), ("two", ("two",))))
    monkeypatch.setattr(v, "_memory_sample", lambda: None)
    calls = []

    def run(command, *, cwd, check):
        assert cwd == ROOT and check is False
        calls.append(command)
        return SimpleNamespace(returncode=23)

    monkeypatch.setattr(v.subprocess, "run", run)
    monkeypatch.setattr(
        v.subprocess, "Popen", lambda *a, **kw: pytest.fail("guarded path")
    )
    assert v.main(("--oom-guard", "off")) == 23
    assert "OOM guard" not in capsys.readouterr().out
    assert v.main(()) == 23
    assert "OOM guard unavailable" in capsys.readouterr().out
    assert calls == [("one",), ("one",)]


def test_exited_gate_wins_the_pressure_race_without_a_group_signal(monkeypatch):
    child = SimpleNamespace(pid=123456, returncode=None)

    def wait():
        child.returncode = 23
        return 23

    child.wait = wait
    monkeypatch.setattr(v.subprocess, "Popen", lambda *a, **kw: child)
    snapshots = iter([sample(), sample(0)])
    monkeypatch.setattr(v, "_memory_sample", lambda: next(snapshots))
    statuses = iter([None, object()])
    monkeypatch.setattr(v.os, "waitid", lambda *a: next(statuses))
    monkeypatch.setattr(
        v.os, "killpg", lambda *a: pytest.fail("already exited gate signalled")
    )
    assert v._run_guarded_gate("test", ("fake",), "on") == 23


def test_lost_wait_ownership_never_signals_a_reusable_pid(monkeypatch, capsys):
    monkeypatch.setattr(v, "_memory_sample", lambda: sample())
    monkeypatch.setattr(
        v.subprocess,
        "Popen",
        lambda *a, **kw: SimpleNamespace(pid=123456, returncode=None),
    )

    def missing(*args):
        raise ChildProcessError

    monkeypatch.setattr(v.os, "waitid", missing)
    monkeypatch.setattr(v.os, "killpg", lambda *a: pytest.fail("unowned PID signalled"))
    assert v._run_guarded_gate("test", ("fake",), "on") == 2
    assert "child wait ownership lost" in capsys.readouterr().out


def test_termination_pins_leader_until_group_kill_then_reaps(monkeypatch):
    calls = []
    child = SimpleNamespace(pid=123456, wait=lambda: calls.append("wait"))
    monkeypatch.setattr(v.os, "getpgrp", lambda: 7)
    monkeypatch.setattr(v.os, "killpg", lambda pid, sig: calls.append((pid, sig)))
    clock = iter([0.0, 0.0, 0.0, 5.0])
    monkeypatch.setattr(v.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(v.time, "sleep", lambda n: calls.append(("sleep", n)))
    assert v._terminate_gate(child) == "SIGTERM_SIGKILL"
    assert calls == [
        (123456, signal.SIGTERM),
        (123456, 0),
        ("sleep", 0.05),
        (123456, signal.SIGKILL),
        "wait",
    ]
    child.pid = 7
    with pytest.raises(RuntimeError, match="validator process group"):
        v._terminate_gate(child)


CHILD = r"""
import json,os,signal,subprocess,sys,time
from pathlib import Path
ready=Path(sys.argv[1])
grand_ready=ready.with_suffix('.grand')
def identity(pid):
    fields=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
    return [pid,int(fields[2]),fields[19]]
grand=subprocess.Popen([sys.executable,'-c',"import os,time;from pathlib import Path;Path("+repr(str(grand_ready))+").write_text(str(os.getpid()));time.sleep(20)"])
def stop(*args):
    try: grand.wait(timeout=1)
    except subprocess.TimeoutExpired: grand.kill();grand.wait()
    ready.with_suffix('.reaped').write_text(str(grand.returncode))
    raise SystemExit(0)
signal.signal(signal.SIGTERM,stop)
try:
    deadline=time.monotonic()+3
    while not grand_ready.exists():
        if time.monotonic()>deadline: raise RuntimeError('grandchild readiness')
        time.sleep(.005)
    temporary=ready.with_suffix('.tmp');temporary.write_text(json.dumps([identity(os.getpid()),identity(grand.pid)]));temporary.replace(ready)
    time.sleep(20)
finally:
    if grand.poll() is None: grand.terminate()
    grand.wait(timeout=2)
"""
STUBBORN = r"""
import json,os,signal,sys,time
from pathlib import Path
signal.signal(signal.SIGTERM,signal.SIG_IGN)
ready=Path(sys.argv[1]);fields=Path(f'/proc/{os.getpid()}/stat').read_text().rsplit(')',1)[1].split()
temporary=ready.with_suffix('.tmp');temporary.write_text(json.dumps([[os.getpid(),int(fields[2]),fields[19]]]));temporary.replace(ready)
time.sleep(20)
"""


def _same_owned_process(identity):
    pid, group, started = identity
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
    except FileNotFoundError:
        return False
    return int(fields[2]) == group and fields[19] == started


def _finish_fixture(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


@pytest.mark.skipif(
    sys.platform != "linux", reason="Linux owned-process-group integration"
)
@pytest.mark.parametrize("mode", ["pressure", "sigint", "sigterm", "pressure_kill"])
def test_tiny_owned_group_cleanup_keeps_unrelated_sibling_alive(
    tmp_path, monkeypatch, capsys, mode
):
    child_script = tmp_path / "child.py"
    child_script.write_text(STUBBORN if mode == "pressure_kill" else CHILD)
    ready = tmp_path / "ready.json"
    original_spawn = subprocess.Popen
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    children = []
    with ExitStack() as cleanup:
        sibling = original_spawn([sys.executable, "-c", "import time;time.sleep(20)"])
        cleanup.callback(_finish_fixture, sibling)

        def spawn(*args, **kwargs):
            assert kwargs == {"cwd": ROOT, "start_new_session": True}
            child = original_spawn(*args, **kwargs)
            children.append(child)
            cleanup.callback(_finish_fixture, child)
            return child

        monkeypatch.setattr(v.subprocess, "Popen", spawn)
        monkeypatch.setattr(v, "OOM_SAMPLE_SECONDS", 0.01)
        monkeypatch.setattr(v, "OOM_TERM_GRACE_SECONDS", 1.0)

        def telemetry():
            if ready.exists():
                if mode.startswith("pressure"):
                    return sample(0, events=None)
                signum = signal.SIGINT if mode == "sigint" else signal.SIGTERM
                assert (
                    callable(signal.getsignal(signum))
                    and signal.getsignal(signum) is not previous[signum]
                )
                os.kill(os.getpid(), signum)
            return sample(events=None)

        monkeypatch.setattr(v, "_memory_sample", telemetry)
        monkeypatch.setattr(
            v,
            "GATES",
            (
                ("tiny", (sys.executable, str(child_script), str(ready))),
                (
                    "later",
                    (sys.executable, "-c", "raise RuntimeError('later gate ran')"),
                ),
            ),
        )
        if mode.startswith("pressure"):
            assert v.main(("--oom-guard", "on")) == 75
        elif mode == "sigint":
            with pytest.raises(KeyboardInterrupt):
                v.main(("--oom-guard", "on"))
        else:
            with pytest.raises(SystemExit) as error:
                v.main(("--oom-guard", "on"))
            assert error.value.code == 143
        assert len(children) == 1
        identities = json.loads(ready.read_text())
        assert identities[0][0] == identities[0][1] == children[0].pid
        assert os.getpgrp() != children[0].pid and os.getpid() != children[0].pid
        assert children[0].returncode is not None and sibling.poll() is None
        assert all(not _same_owned_process(identity) for identity in identities)
        if mode != "pressure_kill":
            assert len(identities) == 2 and identities[1][1] == identities[0][1]
            assert int(ready.with_suffix(".reaped").read_text()) == -signal.SIGTERM
        else:
            assert children[0].returncode == -signal.SIGKILL
        assert {sig: signal.getsignal(sig) for sig in previous} == previous
        records = [
            json.loads(line.removeprefix("[validate] resource-pressure "))
            for line in capsys.readouterr().out.splitlines()
            if line.startswith("[validate] resource-pressure ")
        ]
        if mode.startswith("pressure"):
            assert len(records) == 1
            record = records[0]
            assert (
                record["reason"] == "RESOURCE_PRESSURE_ABORTED"
                and record["trigger"] == "critical_available"
            )
            assert record["format"] == "pietto.validation-resource-pressure.v1"
            assert record["gate"] == "tiny" and record["child_pid"] == children[0].pid
            assert (
                record["effective_total_bytes"] == 8 * GIB
                and record["effective_available_bytes"] == 0
            )
            assert (
                record["critical_threshold_bytes"] == 768 * MIB
                and record["hard_threshold_bytes"] == 3 * GIB // 2
            )
            assert (
                record["psi_full_avg10"]
                is record["memory_events_oom_delta"]
                is record["memory_events_oom_kill_delta"]
                is None
            )
            assert 0 <= record["elapsed_seconds"] < 5
            assert record["termination"] in {"SIGTERM", "SIGTERM_SIGKILL"}
            if mode == "pressure_kill":
                assert record["termination"] == "SIGTERM_SIGKILL"
        else:
            assert records == []


@pytest.mark.skipif(sys.platform != "linux", reason="Linux process groups")
@pytest.mark.parametrize("code", [0, 23])
def test_healthy_guard_preserves_exit_and_signal_handlers(monkeypatch, code):
    monkeypatch.setattr(v, "_memory_sample", lambda: sample())
    monkeypatch.setattr(v, "OOM_SAMPLE_SECONDS", 0.01)
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    assert (
        v._run_guarded_gate(
            "healthy", (sys.executable, "-c", f"raise SystemExit({code})"), "on"
        )
        == code
    )
    assert {sig: signal.getsignal(sig) for sig in previous} == previous


def test_spec_keeps_safety_and_later_work_boundaries():
    text = SPEC.read_text()
    for required in (
        "RESOURCE_PRESSURE_ABORTED",
        "75",
        "768 MiB",
        "1.5 GiB",
        "3 GiB",
        "4.0%",
        "SIGTERM",
        "SIGKILL",
        "NO_GAIN",
        "375s",
        "N66=16",
        "NOT AUTHORIZED / NOT STARTED",
    ):
        assert required in text


@pytest.mark.parametrize(
    "signum,exception,code",
    [(signal.SIGINT, KeyboardInterrupt, None), (signal.SIGTERM, SystemExit, 143)],
)
def test_cancellation_during_spawn_waits_for_owned_handle_and_restores_handlers(
    monkeypatch, signum, exception, code
):
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    child = SimpleNamespace(pid=123456, returncode=None)
    stopped = []

    def spawn(*args, **kwargs):
        assert kwargs == {"cwd": ROOT, "start_new_session": True}
        handler = signal.getsignal(signum)
        assert callable(handler)
        handler(signum, None)
        return child

    def stop(process):
        assert process is child
        stopped.append(process.pid)
        process.returncode = -signal.SIGTERM
        return "SIGTERM"

    monkeypatch.setattr(v, "_memory_sample", lambda: sample())
    monkeypatch.setattr(v.subprocess, "Popen", spawn)
    monkeypatch.setattr(v, "_terminate_gate", stop)
    with pytest.raises(exception) as raised:
        v._run_guarded_gate("tiny", ("fake",), "on")
    if code is not None:
        assert raised.value.code == code
    assert stopped == [123456]
    assert {sig: signal.getsignal(sig) for sig in previous} == previous


def test_failed_spawn_always_restores_handlers(monkeypatch):
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    monkeypatch.setattr(v, "_memory_sample", lambda: sample())

    def fail(*args, **kwargs):
        raise OSError("synthetic spawn failure")

    monkeypatch.setattr(v.subprocess, "Popen", fail)
    with pytest.raises(OSError, match="synthetic spawn failure"):
        v._run_guarded_gate("tiny", ("fake",), "on")
    assert {sig: signal.getsignal(sig) for sig in previous} == previous


def test_abort_record_retains_event_deltas_and_not_a_kernel_victim_claim(
    monkeypatch, capsys
):
    snapshots = iter([sample(events=(3, 2)), sample(events=(5, 3))])
    monkeypatch.setattr(v, "_memory_sample", lambda: next(snapshots))
    child = SimpleNamespace(pid=123456, returncode=None)
    monkeypatch.setattr(v.subprocess, "Popen", lambda *a, **kw: child)
    monkeypatch.setattr(v.os, "waitid", lambda *a: None)

    def stop(process):
        process.returncode = -signal.SIGTERM
        return "SIGTERM"

    monkeypatch.setattr(v, "_terminate_gate", stop)
    assert v._run_guarded_gate("events", ("fake",), "on") == 75
    record = json.loads(
        capsys.readouterr().out.removeprefix("[validate] resource-pressure ")
    )
    assert record["reason"] == "RESOURCE_PRESSURE_ABORTED"
    assert record["trigger"] == "cgroup_oom_kill_increased"
    assert (
        record["memory_events_oom_delta"],
        record["memory_events_oom_kill_delta"],
    ) == (2, 1)


@pytest.mark.parametrize("mode,expected", [("auto", 23), ("on", 2)])
def test_runtime_telemetry_loss_never_retries_or_invents_pressure(
    monkeypatch, capsys, mode, expected
):
    child = SimpleNamespace(pid=123456, returncode=None)

    def wait():
        child.returncode = 23
        return 23

    child.wait = wait
    spawns = []

    def spawn(*args, **kwargs):
        spawns.append(args)
        return child

    stopped = []

    def stop(process):
        stopped.append(process.pid)
        process.returncode = -signal.SIGTERM
        return "SIGTERM"

    snapshots = iter([sample(), None, None])
    statuses = iter([None, None, object()])
    monkeypatch.setattr(v, "_memory_sample", lambda: next(snapshots))
    monkeypatch.setattr(v.os, "waitid", lambda *a: next(statuses))
    monkeypatch.setattr(v.subprocess, "Popen", spawn)
    monkeypatch.setattr(v, "_terminate_gate", stop)
    monkeypatch.setattr(v.time, "sleep", lambda _: None)
    assert v._run_guarded_gate("tiny", ("fake",), mode) == expected
    output = capsys.readouterr().out
    assert (
        output.count("OOM guard unavailable") == 1
        and "RESOURCE_PRESSURE_ABORTED" not in output
    )
    assert len(spawns) == 1 and stopped == ([123456] if mode == "on" else [])


def test_group_disappearing_before_first_signal_keeps_real_gate_exit(
    monkeypatch, capsys
):
    child = SimpleNamespace(pid=123456, returncode=None)

    def wait():
        child.returncode = 23
        return 23

    child.wait = wait
    monkeypatch.setattr(v.subprocess, "Popen", lambda *a, **kw: child)
    snapshots = iter([sample(), sample(0)])
    monkeypatch.setattr(v, "_memory_sample", lambda: next(snapshots))
    monkeypatch.setattr(v.os, "waitid", lambda *a: None)

    def gone(pid, signum):
        assert pid == child.pid and signum == signal.SIGTERM
        raise ProcessLookupError

    monkeypatch.setattr(v.os, "killpg", gone)
    assert v._run_guarded_gate("tiny", ("fake",), "on") == 23
    assert "RESOURCE_PRESSURE_ABORTED" not in capsys.readouterr().out
