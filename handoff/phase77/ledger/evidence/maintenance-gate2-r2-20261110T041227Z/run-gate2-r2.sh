#!/usr/bin/env bash
# Run only after the owner explicitly authorizes M77 Gate 2 R2 START.
set -Eeuo pipefail

readonly EVIDENCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly RECOVERY_ROOT="$(cd -- "$EVIDENCE_DIR/../.." && pwd -P)"
readonly CANDIDATE="$RECOVERY_ROOT/candidates/maintenance"
readonly RUNTIME="$RECOVERY_ROOT/runtime"
readonly CORE_PYTHON="$RUNTIME/venvs/core-dev/bin/python"
readonly WHEELHOUSE="$RUNTIME/wheelhouse"
readonly DIST_DIR="$RUNTIME/dist"
readonly ARTIFACT_MANIFEST="$RUNTIME/candidate-artifacts-rebind-manifest.json"
readonly CACHE_SEED="$CANDIDATE/.uv-runtime-cache"
readonly EXPECTED_HEAD="f8ccd2c44a2d9adf431a496bd9bbae037783176f"
readonly EXPECTED_BASELINE_TREE="460e3e135d1dcb0b926928bc2632a889410f258a"
readonly EXPECTED_DIRTY_TREE="2af0e2e47a062eb747ed5d2cd664c2dab5da4aed"
readonly EXPECTED_LOCK="b2cc96b25b0b9f2225c4529f0123ae869cd804af0578b4f83c931a15aa893064"
readonly EXPECTED_PATCH="548e72276b20c2bff3bb0613a527ef230fb9095942b562dca32a6150da12e1cc"
readonly EXPECTED_WHEEL="f4c96921c4d4ceb057830f2dd21f2e634325dac2bef933532747ae4aab963a73"
readonly EXPECTED_SDIST="15b43b884064e0837bbfa891b8eea44996acc2592bd169b5a6ea96e29d29cfff"
readonly RUN_DIR="$EVIDENCE_DIR/run"
readonly TMP_ROOT="$RUN_DIR/tmp"
readonly BINDINGS="$RUN_DIR/bindings"
readonly COMMANDS="$RUN_DIR/commands"

if [[ "${PIETTO_M77_GATE2_START:-}" != "YES" ]]; then
    printf '%s\n' 'Refusing to start: set PIETTO_M77_GATE2_START=YES after owner START.' >&2
    exit 64
fi
if [[ -e "$RUN_DIR/terminal.json" || -e "$RUN_DIR/STARTED" ]]; then
    printf '%s\n' "Refusing to overwrite existing Gate 2 evidence: $RUN_DIR" >&2
    exit 65
fi

mkdir -p "$TMP_ROOT" "$BINDINGS" "$COMMANDS" "$RUN_DIR/uv-cache" "$RUN_DIR/xdg-cache"
touch "$RUN_DIR/STARTED"

export UV_PYTHON=3.13.13
export UV_OFFLINE=1
export UV_NO_SYNC=1
export UV_LOCKED=1
export UV_PYTHON_DOWNLOADS=never
export UV_CACHE_DIR="$RUN_DIR/uv-cache"
export UV_FIND_LINKS="$WHEELHOUSE"
export VIRTUAL_ENV="$RUNTIME/venvs/core-dev"
export UV_PROJECT_ENVIRONMENT="$VIRTUAL_ENV"
export PATH="$VIRTUAL_ENV/bin:$PATH"
export TMPDIR="$TMP_ROOT"
export PYTEST_DEBUG_TEMPROOT="$TMP_ROOT/pytest"
export XDG_CACHE_HOME="$RUN_DIR/xdg-cache"
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$PYTEST_DEBUG_TEMPROOT"

fail() {
    printf '[preflight] %s\n' "$*" | tee -a "$RUN_DIR/preflight.log" >&2
    printf '%s\n' 2 > "$RUN_DIR/preflight.exit"
    exit 2
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

candidate_tree() {
    local label=$1
    local index="$BINDINGS/$label.index"
    GIT_INDEX_FILE="$index" git -C "$CANDIDATE" read-tree HEAD
    GIT_INDEX_FILE="$index" git -C "$CANDIDATE" add -u
    GIT_INDEX_FILE="$index" git -C "$CANDIDATE" write-tree
}

capture_state() {
    local label=$1
    [[ -d "$CANDIDATE" ]] || return 0
    git -C "$CANDIDATE" status --porcelain=v1 > "$BINDINGS/$label.status" || return 0
    git -C "$CANDIDATE" diff --binary HEAD > "$BINDINGS/$label.patch" || return 0
    git -C "$CANDIDATE" diff --cached --binary > "$BINDINGS/$label.index.patch" || return 0
    git -C "$CANDIDATE" ls-files --others --exclude-standard > "$BINDINGS/$label.untracked" || return 0
    candidate_tree "$label" > "$BINDINGS/$label.tree" || return 0
    (
        cd "$CANDIDATE"
        git ls-files -z -- src pyproject.toml uv.lock | xargs -0 sha256sum
    ) > "$BINDINGS/$label.source-closure.sha256" || return 0
}

require_equal() {
    local left=$1
    local right=$2
    cmp -s "$left" "$right" || fail "changed during Gate 2: ${left##*/} != ${right##*/}"
}

cache_inventory() {
    (
        cd "$1"
        find . -type f -print0 | sort -z | xargs -0 sha256sum
    )
}

record_terminal() {
    local code=$1
    "$CORE_PYTHON" - "$RUN_DIR/terminal.json" "$code" <<'PY'
import json
import sys
from datetime import datetime, timezone

path, code = sys.argv[1], int(sys.argv[2])
with open(path, "x", encoding="utf-8") as output:
    json.dump(
        {
            "format": "pietto.phase77.maintenance-gate2-terminal.v1",
            "actual_exit": code,
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "PASS" if code == 0 else "FAILED_OR_ABORTED",
        },
        output,
        sort_keys=True,
    )
    output.write("\n")
PY
    "$CORE_PYTHON" - "$RUN_DIR/terminal.json" <<'PY'
import json
import pathlib
import sys

value = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
assert value["format"] == "pietto.phase77.maintenance-gate2-terminal.v1"
assert type(value["actual_exit"]) is int
PY
}

on_exit() {
    local code=$?
    set +e
    capture_state after
    record_terminal "$code"
    trap - EXIT
    exit "$code"
}

preflight() {
    : > "$RUN_DIR/preflight.log"
    [[ -d "$CANDIDATE/.git" || -f "$CANDIDATE/.git" ]] || fail "candidate is not a Git checkout"
    [[ -x "$CORE_PYTHON" ]] || fail "missing core-dev CPython runtime"
    [[ -d "$WHEELHOUSE" && -d "$DIST_DIR" && -d "$CACHE_SEED" ]] || fail "missing retained runtime inputs"
    [[ "$(git -C "$CANDIDATE" rev-parse HEAD)" == "$EXPECTED_HEAD" ]] || fail "candidate HEAD changed"
    [[ "$(git -C "$CANDIDATE" rev-parse HEAD^{tree})" == "$EXPECTED_BASELINE_TREE" ]] || fail "candidate baseline tree changed"
    [[ "$(git -C "$CANDIDATE" rev-parse --is-shallow-repository)" == false ]] || fail "candidate Git history is shallow"
    [[ "$(sha256sum "$CANDIDATE/uv.lock" | cut -d' ' -f1)" == "$EXPECTED_LOCK" ]] || fail "uv.lock binding changed"
    [[ "$(git -C "$CANDIDATE" diff --binary HEAD | sha256sum | cut -d' ' -f1)" == "$EXPECTED_PATCH" ]] || fail "candidate patch binding changed"
    [[ "$(sha256sum "$DIST_DIR/pietto-0.1.10-py3-none-any.whl" | cut -d' ' -f1)" == "$EXPECTED_WHEEL" ]] || fail "retained wheel binding changed"
    [[ "$(sha256sum "$DIST_DIR/pietto-0.1.10.tar.gz" | cut -d' ' -f1)" == "$EXPECTED_SDIST" ]] || fail "retained sdist binding changed"
    [[ "$(git -C "$CANDIDATE" diff -- scripts/ci_workloads.py)" == *'26.0.1'* ]] || fail "ci_workloads change is not the selected Arrow pin"
    if git -C "$CANDIDATE" diff -- scripts/ci_workloads.py | rg -q 'ci_validation|validation_runner_receiver|Teach'; then
        fail "ci_workloads change attempts a Teach bootstrap or split"
    fi

    local temp_profile
    temp_profile=$(findmnt -T "$TMP_ROOT" -no FSTYPE,OPTIONS) || fail "cannot inspect temporary-root storage"
    [[ "$temp_profile" == ext4\ * && "$temp_profile" == *rw* && "$temp_profile" != *nobarrier* && "$temp_profile" != *barrier=0* ]] || fail "temporary root is not qualified ext4"
    printf '%s\n' "$temp_profile" > "$RUN_DIR/temp-storage.txt"

    "$CORE_PYTHON" -I -B - "$CANDIDATE" "$RUN_DIR/runtime-source-import.json" <<'PY' || fail "core-dev source import or Arrow-free check failed"
import importlib.util
import json
import pathlib
import platform
import sys

candidate = pathlib.Path(sys.argv[1]).resolve()
import pietto

origin = pathlib.Path(pietto.__file__).resolve()
assert platform.python_implementation() == "CPython"
assert platform.python_version() == "3.13.13"
assert origin.is_relative_to(candidate / "src")
assert importlib.util.find_spec("pyarrow") is None
with open(sys.argv[2], "x", encoding="utf-8") as output:
    json.dump(
        {
            "implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "pietto_origin": str(origin),
            "pyarrow_spec": None,
            "sys_executable": sys.executable,
        },
        output,
        sort_keys=True,
    )
    output.write("\n")
PY

    command -v python3.12 >/dev/null || fail "CPython 3.12 is unavailable on PATH"
    [[ "$(python3.12 -c 'import platform; print(platform.python_version())')" == 3.12.13 ]] || fail "CPython 3.12.13 is unavailable on PATH"
    command -v java >/dev/null || fail "Java is unavailable"
    java -version 2> "$RUN_DIR/java-version.txt"
    rg -q 'version "21\.' "$RUN_DIR/java-version.txt" || fail "Java 21 is unavailable"
    command -v node >/dev/null || fail "Node is unavailable"
    node --version > "$RUN_DIR/node-version.txt"
    command -v git >/dev/null || fail "Git is unavailable"
    git --version > "$RUN_DIR/git-version.txt"

    "$CORE_PYTHON" - "$RUN_DIR/loopback-bind.json" <<'PY' || fail "cannot bind a loopback socket"
import json
import socket
import sys

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    host, port = sock.getsockname()
with open(sys.argv[1], "x", encoding="utf-8") as output:
    json.dump({"address": host, "port": port, "family": "AF_INET"}, output, sort_keys=True)
    output.write("\n")
PY

    {
        printf 'nproc=%s\n' "$(nproc)"
        getconf _NPROCESSORS_ONLN | sed 's/^/online_cpus=/'
        sed -n '1,3p' /proc/loadavg | sed 's/^/loadavg=/'
        rg '^(MemTotal|MemAvailable):' /proc/meminfo
        for path in /sys/fs/cgroup/cpu.max /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.current /sys/fs/cgroup/memory.events; do
            [[ -r "$path" ]] && printf '%s=' "$path" && tr '\n' ' ' < "$path" && printf '\n'
        done
        printf '%s\n' 'process inventory intentionally not inspected; this sandbox cannot judge host process ownership.'
    } > "$RUN_DIR/resources.txt"

    sha256sum "$ARTIFACT_MANIFEST" > "$RUN_DIR/runtime-artifact-manifest.sha256"
    cache_inventory "$CACHE_SEED" > "$RUN_DIR/uv-cache-seed.sha256"
    cp -a "$CACHE_SEED/." "$UV_CACHE_DIR/"
    cache_inventory "$UV_CACHE_DIR" > "$RUN_DIR/uv-cache-copy.sha256"
    require_equal "$RUN_DIR/uv-cache-seed.sha256" "$RUN_DIR/uv-cache-copy.sha256"
    capture_state before
    [[ "$(<"$BINDINGS/before.tree")" == "$EXPECTED_DIRTY_TREE" ]] || fail "temporary-index dirty candidate tree changed"
    [[ ! -s "$BINDINGS/before.index.patch" && ! -s "$BINDINGS/before.untracked" ]] || fail "candidate has staged or untracked inputs"
    printf '%s\n' 'PASS' > "$RUN_DIR/preflight.exit"
}

cd "$CANDIDATE"
trap on_exit EXIT
trap 'exit 143' TERM
trap 'exit 130' INT
preflight
run_step authoritative-validation env \
    UV_PYTHON="$UV_PYTHON" UV_OFFLINE="$UV_OFFLINE" UV_NO_SYNC="$UV_NO_SYNC" \
    UV_LOCKED="$UV_LOCKED" UV_PYTHON_DOWNLOADS="$UV_PYTHON_DOWNLOADS" \
    UV_CACHE_DIR="$UV_CACHE_DIR" UV_FIND_LINKS="$UV_FIND_LINKS" VIRTUAL_ENV="$VIRTUAL_ENV" UV_PROJECT_ENVIRONMENT="$UV_PROJECT_ENVIRONMENT" \
    PATH="$PATH" TMPDIR="$TMPDIR" PYTEST_DEBUG_TEMPROOT="$PYTEST_DEBUG_TEMPROOT" \
    XDG_CACHE_HOME="$XDG_CACHE_HOME" PYTHONDONTWRITEBYTECODE=1 \
    "$CORE_PYTHON" -B "$CANDIDATE/scripts/validate.py" --timings --oom-guard on --pytest-workers 8 --pytest-maxprocesses 4 --pytest-dist loadfile

run_step package-smoke env \
    UV_PYTHON="$UV_PYTHON" UV_OFFLINE="$UV_OFFLINE" UV_NO_SYNC="$UV_NO_SYNC" \
    UV_LOCKED="$UV_LOCKED" UV_PYTHON_DOWNLOADS="$UV_PYTHON_DOWNLOADS" \
    UV_CACHE_DIR="$UV_CACHE_DIR" UV_FIND_LINKS="$UV_FIND_LINKS" VIRTUAL_ENV="$VIRTUAL_ENV" UV_PROJECT_ENVIRONMENT="$UV_PROJECT_ENVIRONMENT" \
    PATH="$PATH" TMPDIR="$TMPDIR" XDG_CACHE_HOME="$XDG_CACHE_HOME" PYTHONDONTWRITEBYTECODE=1 \
    "$CORE_PYTHON" -B "$CANDIDATE/scripts/package_smoke.py" --dist-dir "$DIST_DIR" --extra-env "$RUN_DIR/package-arrow-venv"

capture_state after
require_equal "$BINDINGS/before.status" "$BINDINGS/after.status"
require_equal "$BINDINGS/before.patch" "$BINDINGS/after.patch"
require_equal "$BINDINGS/before.index.patch" "$BINDINGS/after.index.patch"
require_equal "$BINDINGS/before.untracked" "$BINDINGS/after.untracked"
require_equal "$BINDINGS/before.tree" "$BINDINGS/after.tree"
require_equal "$BINDINGS/before.source-closure.sha256" "$BINDINGS/after.source-closure.sha256"
printf '%s\n' 'PASS' > "$RUN_DIR/post-run-integrity.txt"
