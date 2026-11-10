#!/usr/bin/env bash
set -u -o pipefail

root=$(pwd -P)
runtime="$root/.cache/phase77-recovery/runtime"
candidate="$root/.cache/phase77-recovery/candidates/maintenance"
log="$runtime/logs/prepare.log"
cache="$candidate/.uv-runtime-cache"
downloader=/tmp/pietto-phase77-wheel-downloader

mkdir -p "$runtime/logs" "$runtime/dist" "$runtime/wheelhouse" "$runtime/reports" "$runtime/venvs" "$cache"
touch "$log"

run() {
    printf '+ %q' "$@" | tee -a "$log"
    printf '\n' | tee -a "$log"
    "$@" 2>&1 | tee -a "$log"
    result=${PIPESTATUS[0]}
    printf '[exit %s]\n' "$result" | tee -a "$log"
    return "$result"
}

run git -C "$candidate" rev-parse HEAD || exit $?
run git -C "$candidate" status --short || exit $?
run sh -c 'cd "$1" && { find src -type f -print0 | sort -z | xargs -0 sha256sum; sha256sum pyproject.toml uv.lock; } > "$2"' sh "$candidate" "$runtime/reports/source-before.sha256" || exit $?
if ! run env UV_PYTHON=3.13.13 UV_CACHE_DIR="$cache" UV_OFFLINE=1 UV_NO_SYNC=1 uv build "$candidate" --out-dir "$runtime/dist" --clear --no-create-gitignore; then
    run env UV_PYTHON=3.13.13 UV_CACHE_DIR="$cache" UV_NO_SYNC=1 UV_DEFAULT_INDEX=https://pypi.org/simple uv build "$candidate" --out-dir "$runtime/dist" --clear --no-create-gitignore || exit $?
fi
run sh -c 'cd "$1" && { find src -type f -print0 | sort -z | xargs -0 sha256sum; sha256sum pyproject.toml uv.lock; } > "$2"' sh "$candidate" "$runtime/reports/source-after.sha256" || exit $?
run cmp "$runtime/reports/source-before.sha256" "$runtime/reports/source-after.sha256" || exit $?
run sh -c 'sha256sum "$1"/* > "$2"' sh "$runtime/dist" "$runtime/reports/candidate-dist.sha256" || exit $?
run python3.13 -m venv "$downloader" || exit $?
run "$downloader/bin/python" -I -c 'import platform, sys; assert platform.python_implementation() == "CPython"; assert platform.python_version() == "3.13.13"; print(sys.executable); print(sys.version)' || exit $?
stage=$(mktemp -d /tmp/pietto-phase77-runtime-wheelhouse.XXXXXX) || exit $?
printf '+ mktemp -d /tmp/pietto-phase77-runtime-wheelhouse.XXXXXX\n%s\n[exit 0]\n' "$stage" | tee -a "$log"
run env PIP_CACHE_DIR="$stage/pip-cache" "$downloader/bin/python" -m pip install --dry-run --ignore-installed --only-binary=:all: --report "$runtime/reports/core-dev-resolve.json" -r "$runtime/requirements/core-dev.txt" || exit $?
run env PIP_CACHE_DIR="$stage/pip-cache" "$downloader/bin/python" -m pip install --dry-run --ignore-installed --only-binary=:all: --report "$runtime/reports/native-resolve.json" -r "$runtime/requirements/native.txt" || exit $?
run env PIP_CACHE_DIR="$stage/pip-cache" "$downloader/bin/python" -m pip download --only-binary=:all: --dest "$stage" -r "$runtime/requirements/core-dev.txt" || exit $?
run env PIP_CACHE_DIR="$stage/pip-cache" "$downloader/bin/python" -m pip download --only-binary=:all: --dest "$stage" -r "$runtime/requirements/native.txt" || exit $?
run find "$stage" -maxdepth 1 -type f -name '*.whl' -printf '%f\n' || exit $?
run find "$stage" -maxdepth 1 -type f ! -name '*.whl' -print || exit $?
run cp -a "$stage"/. "$runtime/wheelhouse"/ || exit $?
run "$downloader/bin/python" -I "$runtime/build_manifest.py" || exit $?
run env UV_PYTHON=3.13.13 UV_CACHE_DIR="$cache" UV_OFFLINE=1 UV_NO_SYNC=1 uv venv --python 3.13.13 "$runtime/venvs/core-dev" || exit $?
run env UV_PYTHON=3.13.13 UV_CACHE_DIR="$cache" UV_OFFLINE=1 UV_NO_SYNC=1 uv pip install --python "$runtime/venvs/core-dev/bin/python" --no-index --find-links "$runtime/wheelhouse" "$runtime/dist"/*.whl -r "$runtime/requirements/core-dev.txt" || exit $?
run env UV_PYTHON=3.13.13 UV_CACHE_DIR="$cache" UV_OFFLINE=1 UV_NO_SYNC=1 uv venv --python 3.13.13 "$runtime/venvs/native" || exit $?
run env UV_PYTHON=3.13.13 UV_CACHE_DIR="$cache" UV_OFFLINE=1 UV_NO_SYNC=1 uv pip install --python "$runtime/venvs/native/bin/python" --no-index --find-links "$runtime/wheelhouse" "$runtime/dist"/*.whl -r "$runtime/requirements/native.txt" || exit $?
run "$runtime/venvs/core-dev/bin/python" -I -c 'import importlib.metadata as m, platform, pietto, sys; assert platform.python_version() == "3.13.13"; assert "pyarrow" not in {x.metadata["Name"].lower() for x in m.distributions()}; print(sys.executable); print(pietto.__file__); print(m.version("psycopg"), m.version("mysql-connector-python"), m.version("pytest"))' || exit $?
run "$runtime/venvs/native/bin/python" -I -c 'import adbc_driver_manager, adbc_driver_postgresql, importlib.metadata as m, mysql.connector, platform, psycopg, pyarrow, sys, wrapt; assert platform.python_version() == "3.13.13"; print(sys.executable); print(pyarrow.__file__); print(psycopg.__file__); print(mysql.connector.__file__); print(adbc_driver_manager.__file__); print(adbc_driver_postgresql.__file__); print(wrapt.__file__); print({x:m.version(x) for x in ("pyarrow", "psycopg", "psycopg-binary", "mysql-connector-python", "adbc-driver-manager", "adbc-driver-postgresql", "opentelemetry-api", "opentelemetry-sdk", "opentelemetry-semantic-conventions", "wrapt")})' || exit $?
run "$runtime/venvs/native/bin/python" -I .cache/phase77-recovery/native-maintenance/runnable-rebind/mysql/selfcheck.py --candidate "$candidate" --wheel "$runtime/dist"/*.whl || exit $?
run sh -c 'sha256sum "$1"/*.whl "$2"/* > "$3"' sh "$runtime/wheelhouse" "$runtime/dist" "$runtime/reports/all-artifacts.sha256" || exit $?
