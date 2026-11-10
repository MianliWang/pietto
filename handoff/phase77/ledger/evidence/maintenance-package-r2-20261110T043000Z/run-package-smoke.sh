#!/usr/bin/env bash
# Independent retained-artifact package smoke; this is not a Gate 2 launcher.
set -Eeuo pipefail

readonly EVIDENCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly RECOVERY_ROOT="$(cd -- "$EVIDENCE_DIR/../.." && pwd -P)"
readonly CANDIDATE="$RECOVERY_ROOT/candidates/maintenance"
readonly RUNTIME="$RECOVERY_ROOT/runtime"
readonly CORE_PYTHON="$RUNTIME/venvs/core-dev/bin/python"
readonly WHEELHOUSE="$RUNTIME/wheelhouse"
readonly DIST_DIR="$RUNTIME/dist"
readonly CACHE_SEED="$CANDIDATE/.uv-runtime-cache"
readonly RUN_DIR="$EVIDENCE_DIR/run"
readonly BINDINGS="$RUN_DIR/bindings"
readonly COMMANDS="$RUN_DIR/commands"
readonly EXPECTED_HEAD=f8ccd2c44a2d9adf431a496bd9bbae037783176f
readonly EXPECTED_TREE=2af0e2e47a062eb747ed5d2cd664c2dab5da4aed
readonly EXPECTED_PATCH=548e72276b20c2bff3bb0613a527ef230fb9095942b562dca32a6150da12e1cc
readonly EXPECTED_LOCK=b2cc96b25b0b9f2225c4529f0123ae869cd804af0578b4f83c931a15aa893064
readonly EXPECTED_WHEEL=f4c96921c4d4ceb057830f2dd21f2e634325dac2bef933532747ae4aab963a73
readonly EXPECTED_SDIST=15b43b884064e0837bbfa891b8eea44996acc2592bd169b5a6ea96e29d29cfff

if [[ "${PIETTO_M77_PACKAGE_SMOKE_START:-}" != YES ]]; then
    printf '%s\n' 'Refusing to start without PIETTO_M77_PACKAGE_SMOKE_START=YES.' >&2
    exit 64
fi
if [[ -e "$RUN_DIR" ]]; then
    printf '%s\n' "Refusing to overwrite evidence: $RUN_DIR" >&2
    exit 65
fi

candidate_tree() {
    local index="$BINDINGS/$1.index"
    GIT_INDEX_FILE="$index" git -C "$CANDIDATE" read-tree HEAD
    GIT_INDEX_FILE="$index" git -C "$CANDIDATE" add -u
    GIT_INDEX_FILE="$index" git -C "$CANDIDATE" write-tree
}

capture() {
    git -C "$CANDIDATE" status --porcelain=v1 > "$BINDINGS/$1.status"
    git -C "$CANDIDATE" diff --binary HEAD > "$BINDINGS/$1.patch"
    git -C "$CANDIDATE" diff --cached --binary > "$BINDINGS/$1.index.patch"
    git -C "$CANDIDATE" ls-files --others --exclude-standard > "$BINDINGS/$1.untracked"
    candidate_tree "$1" > "$BINDINGS/$1.tree"
    (cd "$CANDIDATE" && git ls-files -z -- src pyproject.toml uv.lock | xargs -0 sha256sum) > "$BINDINGS/$1.source-closure.sha256"
}

terminal() {
    "$CORE_PYTHON" - "$RUN_DIR/terminal.json" "$1" <<'PY'
import json
import sys
from datetime import datetime, timezone
path, code = sys.argv[1], int(sys.argv[2])
with open(path, "x", encoding="utf-8") as output:
    json.dump({"actual_exit": code, "format": "pietto.m77.package-smoke-terminal.v1", "finished_at_utc": datetime.now(timezone.utc).isoformat(), "status": "PASS" if code == 0 else "FAILED"}, output, sort_keys=True)
    output.write("\n")
PY
}

on_exit() {
    local code=$?
    set +e
    capture after
    terminal "$code"
    trap - EXIT
    exit "$code"
}

mkdir -p "$RUN_DIR/tmp" "$RUN_DIR/uv-cache" "$RUN_DIR/xdg-cache" "$BINDINGS" "$COMMANDS"
touch "$RUN_DIR/STARTED"
trap on_exit EXIT
trap 'exit 143' TERM
trap 'exit 130' INT

[[ -x "$CORE_PYTHON" && -d "$WHEELHOUSE" && -d "$CACHE_SEED" ]] || { printf '%s\n' 'missing recovered runtime input' >&2; exit 2; }
[[ "$(git -C "$CANDIDATE" rev-parse HEAD)" == "$EXPECTED_HEAD" ]] || { printf '%s\n' 'candidate head changed' >&2; exit 2; }
[[ "$(git -C "$CANDIDATE" diff --binary HEAD | sha256sum | cut -d' ' -f1)" == "$EXPECTED_PATCH" ]] || { printf '%s\n' 'candidate patch changed' >&2; exit 2; }
[[ "$(sha256sum "$CANDIDATE/uv.lock" | cut -d' ' -f1)" == "$EXPECTED_LOCK" ]] || { printf '%s\n' 'candidate lock changed' >&2; exit 2; }
[[ "$(sha256sum "$DIST_DIR/pietto-0.1.10-py3-none-any.whl" | cut -d' ' -f1)" == "$EXPECTED_WHEEL" ]] || { printf '%s\n' 'wheel changed' >&2; exit 2; }
[[ "$(sha256sum "$DIST_DIR/pietto-0.1.10.tar.gz" | cut -d' ' -f1)" == "$EXPECTED_SDIST" ]] || { printf '%s\n' 'sdist changed' >&2; exit 2; }
available_kib=$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)
[[ "$available_kib" -ge 8388608 ]] || { printf 'MemAvailable=%s KiB below 8 GiB start floor\n' "$available_kib" >&2; exit 75; }
findmnt -T "$RUN_DIR/tmp" -no FSTYPE,OPTIONS > "$RUN_DIR/storage.txt"
grep -E '^(MemTotal|MemAvailable):' /proc/meminfo > "$RUN_DIR/resources-before.txt"
awk '/^full / {print}' /proc/pressure/memory >> "$RUN_DIR/resources-before.txt"
printf 'core_python=%s\n' "$CORE_PYTHON" > "$RUN_DIR/runtime.txt"
"$CORE_PYTHON" -I -c 'import platform; assert platform.python_version() == "3.13.13"; print(platform.python_implementation(), platform.python_version())' >> "$RUN_DIR/runtime.txt"

export UV_PYTHON=3.13.13 UV_OFFLINE=1 UV_NO_SYNC=1 UV_LOCKED=1 UV_PYTHON_DOWNLOADS=never
export UV_CACHE_DIR="$RUN_DIR/uv-cache" UV_FIND_LINKS="$WHEELHOUSE"
export UV_PROJECT_ENVIRONMENT="$RUNTIME/venvs/core-dev"
export VIRTUAL_ENV="$UV_PROJECT_ENVIRONMENT"
export PATH="$VIRTUAL_ENV/bin:$PATH" TMPDIR="$RUN_DIR/tmp" XDG_CACHE_HOME="$RUN_DIR/xdg-cache" PYTHONDONTWRITEBYTECODE=1
cp -a "$CACHE_SEED/." "$UV_CACHE_DIR/"
capture before
[[ "$(<"$BINDINGS/before.tree")" == "$EXPECTED_TREE" ]] || { printf '%s\n' 'candidate temporary-index tree changed' >&2; exit 2; }
[[ ! -s "$BINDINGS/before.index.patch" && ! -s "$BINDINGS/before.untracked" ]] || { printf '%s\n' 'candidate staged or untracked inputs' >&2; exit 2; }
sha256sum "$RUNTIME/candidate-artifacts-rebind-manifest.json" > "$RUN_DIR/artifact-manifest.sha256"
printf '%q ' env UV_PYTHON="$UV_PYTHON" UV_OFFLINE="$UV_OFFLINE" UV_NO_SYNC="$UV_NO_SYNC" UV_LOCKED="$UV_LOCKED" UV_PYTHON_DOWNLOADS="$UV_PYTHON_DOWNLOADS" UV_CACHE_DIR="$UV_CACHE_DIR" UV_FIND_LINKS="$UV_FIND_LINKS" VIRTUAL_ENV="$VIRTUAL_ENV" UV_PROJECT_ENVIRONMENT="$UV_PROJECT_ENVIRONMENT" PATH="$PATH" TMPDIR="$TMPDIR" XDG_CACHE_HOME="$XDG_CACHE_HOME" "$CORE_PYTHON" -B "$CANDIDATE/scripts/package_smoke.py" --dist-dir "$DIST_DIR" --extra-env "$RUN_DIR/package-arrow-venv" > "$COMMANDS/package-smoke.command"
printf '\n' >> "$COMMANDS/package-smoke.command"
set +e
env UV_PYTHON="$UV_PYTHON" UV_OFFLINE="$UV_OFFLINE" UV_NO_SYNC="$UV_NO_SYNC" UV_LOCKED="$UV_LOCKED" UV_PYTHON_DOWNLOADS="$UV_PYTHON_DOWNLOADS" UV_CACHE_DIR="$UV_CACHE_DIR" UV_FIND_LINKS="$UV_FIND_LINKS" VIRTUAL_ENV="$VIRTUAL_ENV" UV_PROJECT_ENVIRONMENT="$UV_PROJECT_ENVIRONMENT" PATH="$PATH" TMPDIR="$TMPDIR" XDG_CACHE_HOME="$XDG_CACHE_HOME" PYTHONDONTWRITEBYTECODE=1 "$CORE_PYTHON" -B "$CANDIDATE/scripts/package_smoke.py" --dist-dir "$DIST_DIR" --extra-env "$RUN_DIR/package-arrow-venv" 2>&1 | tee "$COMMANDS/package-smoke.log"
code=${PIPESTATUS[0]}
set -e
printf '%s\n' "$code" > "$COMMANDS/package-smoke.exit"
[[ "$code" == 0 ]]
capture after
cmp -s "$BINDINGS/before.status" "$BINDINGS/after.status"
cmp -s "$BINDINGS/before.patch" "$BINDINGS/after.patch"
cmp -s "$BINDINGS/before.index.patch" "$BINDINGS/after.index.patch"
cmp -s "$BINDINGS/before.untracked" "$BINDINGS/after.untracked"
cmp -s "$BINDINGS/before.tree" "$BINDINGS/after.tree"
cmp -s "$BINDINGS/before.source-closure.sha256" "$BINDINGS/after.source-closure.sha256"
printf '%s\n' PASS > "$RUN_DIR/post-run-integrity.txt"
