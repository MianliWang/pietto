#!/usr/bin/env bash
# Run only after the root explicitly authorizes the sealed editor candidate.
set -Eeuo pipefail

readonly EVIDENCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly RECOVERY_ROOT="$(cd -- "$EVIDENCE_DIR/../.." && pwd -P)"
readonly CANDIDATE="$RECOVERY_ROOT/candidates/editor-combined"
readonly RUNTIME="$RECOVERY_ROOT/runtime/editor-runtime"
readonly CORE_PYTHON="$RUNTIME/core-dev/bin/python"
readonly WHEELHOUSE="$RECOVERY_ROOT/runtime/wheelhouse"
readonly CACHE_SEED="$RECOVERY_ROOT/evidence/editor-focused-20261110T051000Z/run/uv-cache"
readonly PACKAGE_RECEIPT="$RECOVERY_ROOT/evidence/editor-package-r1-20261110T044000Z/run/terminal.json"
readonly PACKAGE_DIST_RECEIPT="$RECOVERY_ROOT/evidence/editor-package-r1-20261110T044000Z/run/commands/reused-dist.sha256"
readonly WHEEL="$RECOVERY_ROOT/evidence/editor-focused-20261110T051000Z/run/dist/pietto-0.1.10-py3-none-any.whl"
readonly SDIST="$RECOVERY_ROOT/evidence/editor-focused-20261110T051000Z/run/dist/pietto-0.1.10.tar.gz"
readonly EXPECTED_HEAD="f8ccd2c44a2d9adf431a496bd9bbae037783176f"
readonly EXPECTED_BASELINE_TREE="460e3e135d1dcb0b926928bc2632a889410f258a"
readonly EXPECTED_DIRTY_TREE="d927402bda7c77d44d74f2903b0a41ca9d1b8256"
readonly EXPECTED_PATCH="76bbac7a9f23809840c456f42cecd7251ad5305dc3cdbeff44addc9625aeba6b"
readonly EXPECTED_LOCK="b2cc96b25b0b9f2225c4529f0123ae869cd804af0578b4f83c931a15aa893064"
readonly EXPECTED_WHEEL="9d2b31b0fa72ee40b1f671b5aa50f5eb0fedc83fdc19fe3d20bf2378e2921dd2"
readonly EXPECTED_SDIST="3639469b78ba7ca78cb42d590ebd7c608767707e5f4cee98b3537229674bc7bf"
readonly RUN_DIR="$EVIDENCE_DIR/run"
readonly SCRATCH="/tmp/claude-1000/pietto-editor-gate2-r2-20261110T084923Z"
readonly TMP_ROOT="$SCRATCH/tmp"
readonly BINDINGS="$RUN_DIR/bindings"
readonly COMMANDS="$RUN_DIR/commands"
MONITOR_PID=""

if [[ "${PIETTO_EDITOR_GATE2_START:-}" != YES ]]; then
    printf '%s\n' 'Refusing to start: set PIETTO_EDITOR_GATE2_START=YES after root START.' >&2
    exit 64
fi
if [[ -e "$RUN_DIR/STARTED" || -e "$RUN_DIR/terminal.json" ]]; then
    printf '%s\n' "Refusing to overwrite existing Gate 2 evidence: $RUN_DIR" >&2
    exit 65
fi

mkdir -p "$RUN_DIR" "$TMP_ROOT/pytest" "$BINDINGS" "$COMMANDS" "$SCRATCH/uv-cache" "$SCRATCH/xdg-cache"
touch "$RUN_DIR/STARTED"

export UV_PYTHON=3.13.13
export UV_OFFLINE=1
export UV_NO_SYNC=1
export UV_LOCKED=1
export UV_PYTHON_DOWNLOADS=never
export UV_CACHE_DIR="$SCRATCH/uv-cache"
export UV_FIND_LINKS="$WHEELHOUSE"
export VIRTUAL_ENV="$RUNTIME/core-dev"
export UV_PROJECT_ENVIRONMENT="$VIRTUAL_ENV"
export PATH="$VIRTUAL_ENV/bin:$PATH"
export TMPDIR="$TMP_ROOT"
export PYTEST_DEBUG_TEMPROOT="$TMP_ROOT/pytest"
export XDG_CACHE_HOME="$SCRATCH/xdg-cache"
export PYTHONDONTWRITEBYTECODE=1

fail() {
    printf '[preflight] %s\n' "$*" | tee -a "$RUN_DIR/preflight.log" >&2
    printf '%s\n' 2 > "$RUN_DIR/preflight.exit"
    exit 2
}

capture_state() {
    local label=$1
    local index="$BINDINGS/$label.index"
    git -C "$CANDIDATE" status --porcelain=v1 > "$BINDINGS/$label.status"
    git -C "$CANDIDATE" diff --binary HEAD > "$BINDINGS/$label.patch"
    git -C "$CANDIDATE" diff --cached --binary > "$BINDINGS/$label.index.patch"
    git -C "$CANDIDATE" ls-files --others --exclude-standard > "$BINDINGS/$label.untracked"
    GIT_INDEX_FILE="$index" git -C "$CANDIDATE" read-tree HEAD
    GIT_INDEX_FILE="$index" git -C "$CANDIDATE" add -A
    GIT_INDEX_FILE="$index" git -C "$CANDIDATE" write-tree > "$BINDINGS/$label.tree"
    rm -f "$index"
    (
        cd "$CANDIDATE"
        git ls-files -co --exclude-standard -z -- src pyproject.toml uv.lock docs/spec docs/editor-lsp.md scripts/package_smoke.py |
            xargs -0 sha256sum
    ) > "$BINDINGS/$label.source-closure.sha256"
}

require_equal() {
    cmp -s "$1" "$2" || fail "changed during Gate 2: ${1##*/} != ${2##*/}"
}

cache_inventory() {
    (
        cd "$1"
        find . -type f -print0 | sort -z | xargs -0 sha256sum
    )
}

record_command() {
    local name=$1
    shift
    printf '%q ' "$@" > "$COMMANDS/$name.command"
    printf '\n' >> "$COMMANDS/$name.command"
}

run_step() {
    local name=$1
    shift
    record_command "$name" "$@"
    set +e
    "$@" 2>&1 | tee "$COMMANDS/$name.log"
    local code=${PIPESTATUS[0]}
    set -e
    printf '%s\n' "$code" > "$COMMANDS/$name.exit"
    return "$code"
}

monitor_snapshot() {
    {
        printf 'timestamp_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        rg '^(MemTotal|MemAvailable):' /proc/meminfo
        sed 's/^/psi_memory_/' /proc/pressure/memory
        for path in /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.current /sys/fs/cgroup/memory.events; do
            printf '%s=' "$path"
            tr '\n' ' ' < "$path"
            printf '\n'
        done
        printf '%s\n' 'top_processes_pid_ppid_rss_comm:'
        ps -eo pid=,ppid=,rss=,comm= --sort=-rss | awk 'NR <= 32 { print }'
        printf '%s\n' 'rss_kib_by_comm_top12:'
        ps -eo rss=,comm= | awk '{ n[$2]++; s[$2] += $1 } END { for (c in s) printf "%d %d %s\n", s[c], n[c], c }' | sort -rn | awk 'NR <= 12 { print }'
        printf 'process_count=%s rg_count=%s\n' "$(ps -e --no-headers | wc -l)" "$(ps -C rg --no-headers | wc -l)"
        printf '%s\n' '--'
    } >> "$RUN_DIR/resource-monitor.log"
}

start_monitor() {
    (while :; do monitor_snapshot; sleep 10; done) &
    MONITOR_PID=$!
    printf '%s\n' "$MONITOR_PID" > "$RUN_DIR/resource-monitor.pid"
}

stop_monitor() {
    if [[ -n "$MONITOR_PID" ]] && kill -0 "$MONITOR_PID" 2>/dev/null; then
        kill -TERM "$MONITOR_PID"
        wait "$MONITOR_PID" || true
    fi
}

record_terminal() {
    "$CORE_PYTHON" - "$RUN_DIR/terminal.json" "$1" <<'PY'
import json
import sys
from datetime import datetime, timezone

path, code = sys.argv[1], int(sys.argv[2])
with open(path, "x", encoding="utf-8") as output:
    json.dump(
        {
            "actual_exit": code,
            "format": "pietto.editor-gate2-terminal.v1",
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "PASS" if code == 0 else "FAILED_OR_ABORTED",
        },
        output,
        sort_keys=True,
    )
    output.write("\n")
PY
}

on_exit() {
    local code=$?
    set +e
    stop_monitor
    capture_state after
    record_terminal "$code"
    trap - EXIT
    exit "$code"
}

preflight() {
    : > "$RUN_DIR/preflight.log"
    [[ -x "$CORE_PYTHON" && -d "$WHEELHOUSE" && -d "$CACHE_SEED" ]] || fail "missing editor runtime inputs"
    [[ "$(git -C "$CANDIDATE" rev-parse HEAD)" == "$EXPECTED_HEAD" ]] || fail "candidate HEAD changed"
    [[ "$(git -C "$CANDIDATE" rev-parse HEAD^{tree})" == "$EXPECTED_BASELINE_TREE" ]] || fail "candidate baseline changed"
    [[ "$(git -C "$CANDIDATE" rev-parse --is-shallow-repository)" == false ]] || fail "candidate Git history is shallow"
    [[ "$(sha256sum "$CANDIDATE/uv.lock" | cut -d' ' -f1)" == "$EXPECTED_LOCK" ]] || fail "uv.lock binding changed"
    [[ "$(git -C "$CANDIDATE" diff --binary HEAD | sha256sum | cut -d' ' -f1)" == "$EXPECTED_PATCH" ]] || fail "candidate patch binding changed"
    [[ "$(sha256sum "$WHEEL" | cut -d' ' -f1)" == "$EXPECTED_WHEEL" ]] || fail "wheel binding changed"
    [[ "$(sha256sum "$SDIST" | cut -d' ' -f1)" == "$EXPECTED_SDIST" ]] || fail "sdist binding changed"
    "$CORE_PYTHON" - "$PACKAGE_RECEIPT" <<'PY' || fail "editor package receipt is not accepted"
import json
import pathlib
import sys

value = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
assert value == {
    "actual_exit": 0,
    "format": "pietto.editor-package-smoke-terminal.v1",
    "status": "PASS",
    **{key: value[key] for key in ("finished_at_utc",)},
}
PY
    [[ -f "$PACKAGE_DIST_RECEIPT" ]] || fail "editor package artifact receipt is missing"
    rg -Fq "$EXPECTED_WHEEL" "$PACKAGE_DIST_RECEIPT" || fail "editor package wheel binding changed"
    rg -Fq "$EXPECTED_SDIST" "$PACKAGE_DIST_RECEIPT" || fail "editor package sdist binding changed"
    sha256sum "$PACKAGE_RECEIPT" > "$RUN_DIR/package-smoke-receipt.sha256"
    sha256sum "$PACKAGE_DIST_RECEIPT" > "$RUN_DIR/package-smoke-artifacts.sha256"
    local temp_profile
    temp_profile=$(findmnt -T "$TMP_ROOT" -no FSTYPE,OPTIONS) || fail "cannot inspect temp storage"
    [[ "$temp_profile" == ext4\ * && "$temp_profile" == *rw* && "$temp_profile" != *nobarrier* && "$temp_profile" != *barrier=0* ]] || fail "temporary root is not qualified ext4"
    printf '%s\n' "$temp_profile" > "$RUN_DIR/temp-storage.txt"
    "$CORE_PYTHON" -I -B - "$CANDIDATE" "$RUN_DIR/runtime-source-import.json" <<'PY' || fail "source import profile failed"
import importlib.util
import json
import pathlib
import platform
import sys

candidate = pathlib.Path(sys.argv[1]).resolve()
import pietto
assert platform.python_implementation() == "CPython"
assert platform.python_version() == "3.13.13"
assert pathlib.Path(pietto.__file__).resolve().is_relative_to(candidate / "src")
assert importlib.util.find_spec("pyarrow") is None
pathlib.Path(sys.argv[2]).write_text(json.dumps({"python": sys.executable, "pietto": str(pathlib.Path(pietto.__file__).resolve())}, sort_keys=True) + "\n")
PY
    command -v python3.12 >/dev/null || fail "CPython 3.12 unavailable"
    [[ "$(python3.12 -c 'import platform; print(platform.python_version())')" == 3.12.13 ]] || fail "CPython 3.12.13 unavailable"
    java -version 2> "$RUN_DIR/java-version.txt"
    rg -q 'version "21\.' "$RUN_DIR/java-version.txt" || fail "Java 21 unavailable"
    node --version > "$RUN_DIR/node-version.txt"
    git --version > "$RUN_DIR/git-version.txt"
    "$CORE_PYTHON" - "$RUN_DIR/loopback-bind.json" <<'PY' || fail "cannot bind loopback"
import json
import socket
import sys
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    host, port = sock.getsockname()
open(sys.argv[1], "x", encoding="utf-8").write(json.dumps({"address": host, "port": port}) + "\n")
PY
    {
        printf 'nproc=%s\n' "$(nproc)"
        getconf _NPROCESSORS_ONLN | sed 's/^/online_cpus=/'
        sed -n '1,3p' /proc/loadavg | sed 's/^/loadavg=/'
        rg '^(MemTotal|MemAvailable):' /proc/meminfo
        for path in /sys/fs/cgroup/cpu.max /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.current /sys/fs/cgroup/memory.events; do
            [[ -r "$path" ]] && printf '%s=' "$path" && tr '\n' ' ' < "$path" && printf '\n'
        done
    } > "$RUN_DIR/resources.txt"
    cache_inventory "$CACHE_SEED" > "$RUN_DIR/uv-cache-seed.sha256"
    cp -a "$CACHE_SEED/." "$UV_CACHE_DIR/"
    cache_inventory "$UV_CACHE_DIR" > "$RUN_DIR/uv-cache-copy.sha256"
    require_equal "$RUN_DIR/uv-cache-seed.sha256" "$RUN_DIR/uv-cache-copy.sha256"
    capture_state before
    [[ "$(<"$BINDINGS/before.tree")" == "$EXPECTED_DIRTY_TREE" ]] || fail "temporary-index tree changed"
    [[ ! -s "$BINDINGS/before.index.patch" ]] || fail "candidate has staged inputs"
    printf '%s\n' PASS > "$RUN_DIR/preflight.exit"
}

cd "$CANDIDATE"
trap on_exit EXIT
trap 'exit 143' TERM
trap 'exit 130' INT
preflight
start_monitor
run_step authoritative-validation env \
    UV_PYTHON="$UV_PYTHON" UV_OFFLINE="$UV_OFFLINE" UV_NO_SYNC="$UV_NO_SYNC" \
    UV_LOCKED="$UV_LOCKED" UV_PYTHON_DOWNLOADS="$UV_PYTHON_DOWNLOADS" \
    UV_CACHE_DIR="$UV_CACHE_DIR" UV_FIND_LINKS="$UV_FIND_LINKS" VIRTUAL_ENV="$VIRTUAL_ENV" \
    UV_PROJECT_ENVIRONMENT="$UV_PROJECT_ENVIRONMENT" PATH="$PATH" TMPDIR="$TMPDIR" \
    PYTEST_DEBUG_TEMPROOT="$PYTEST_DEBUG_TEMPROOT" XDG_CACHE_HOME="$XDG_CACHE_HOME" \
    PYTHONDONTWRITEBYTECODE=1 "$CORE_PYTHON" -B scripts/validate.py --timings \
    --oom-guard on --pytest-workers 8 --pytest-dist loadfile
capture_state after
require_equal "$BINDINGS/before.status" "$BINDINGS/after.status"
require_equal "$BINDINGS/before.patch" "$BINDINGS/after.patch"
require_equal "$BINDINGS/before.index.patch" "$BINDINGS/after.index.patch"
require_equal "$BINDINGS/before.untracked" "$BINDINGS/after.untracked"
require_equal "$BINDINGS/before.tree" "$BINDINGS/after.tree"
require_equal "$BINDINGS/before.source-closure.sha256" "$BINDINGS/after.source-closure.sha256"
printf '%s\n' PASS > "$RUN_DIR/post-run-integrity.txt"
