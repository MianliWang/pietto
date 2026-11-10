#!/usr/bin/env bash
set -u -o pipefail

root=$(pwd -P)
runtime="$root/.cache/phase77-recovery/runtime"
candidate="$root/.cache/phase77-recovery/candidates/maintenance"
cache="$candidate/.uv-runtime-cache"
log="$runtime/logs/prepare.log"

run() {
    printf '+ %q' "$@" | tee -a "$log"
    printf '\n' | tee -a "$log"
    "$@" 2>&1 | tee -a "$log"
    result=${PIPESTATUS[0]}
    printf '[exit %s]\n' "$result" | tee -a "$log"
    return "$result"
}

run env UV_PYTHON=3.13.13 UV_CACHE_DIR="$cache" UV_OFFLINE=1 UV_NO_SYNC=1 uv pip install --python "$runtime/venvs/core-dev/bin/python" --no-index --find-links "$runtime/wheelhouse" "$runtime/dist"/*.whl -r "$runtime/requirements/core-dev.txt" || exit $?
run env UV_PYTHON=3.13.13 UV_CACHE_DIR="$cache" UV_OFFLINE=1 UV_NO_SYNC=1 uv pip install --python "$runtime/venvs/native/bin/python" --no-index --find-links "$runtime/wheelhouse" "$runtime/dist"/*.whl -r "$runtime/requirements/native.txt" || exit $?
run env UV_PYTHON=3.13.13 UV_CACHE_DIR="$cache" UV_OFFLINE=1 UV_NO_SYNC=1 uv pip check --python "$runtime/venvs/core-dev/bin/python" || exit $?
run env UV_PYTHON=3.13.13 UV_CACHE_DIR="$cache" UV_OFFLINE=1 UV_NO_SYNC=1 uv pip check --python "$runtime/venvs/native/bin/python" || exit $?
run "$runtime/venvs/native/bin/python" -I "$runtime/build_manifest.py" || exit $?
run "$runtime/venvs/core-dev/bin/python" -I -c 'import importlib.metadata as m, platform, pietto, sys; assert platform.python_version() == "3.13.13"; assert "pyarrow" not in {x.metadata["Name"].lower() for x in m.distributions()}; print(sys.executable); print(pietto.__file__); print(m.version("psycopg"), m.version("mysql-connector-python"), m.version("pytest"))' || exit $?
run "$runtime/venvs/native/bin/python" -I -c 'import adbc_driver_manager, adbc_driver_postgresql, importlib.metadata as m, mysql.connector, platform, psycopg, pyarrow, sys, wrapt; assert platform.python_version() == "3.13.13"; print(sys.executable); print(pyarrow.__file__); print(psycopg.__file__); print(mysql.connector.__file__); print(adbc_driver_manager.__file__); print(adbc_driver_postgresql.__file__); print(wrapt.__file__); print({x:m.version(x) for x in ("pyarrow", "psycopg", "psycopg-binary", "mysql-connector-python", "adbc-driver-manager", "adbc-driver-postgresql", "opentelemetry-api", "opentelemetry-sdk", "opentelemetry-semantic-conventions", "wrapt", "pytest")})' || exit $?
run "$runtime/venvs/native/bin/python" -I .cache/phase77-recovery/native-maintenance/runnable-rebind/mysql/selfcheck.py --candidate "$candidate" --wheel "$runtime/dist"/*.whl || exit $?
run "$runtime/venvs/native/bin/python" -I "$runtime/inspect_candidate_artifacts.py" || exit $?
run sh -c 'find "$1" -maxdepth 1 -type f ! -name "*.whl" -print | grep . && exit 1 || true' sh "$runtime/wheelhouse" || exit $?
run sh -c 'sha256sum "$1"/*.whl "$2"/* > "$3"' sh "$runtime/wheelhouse" "$runtime/dist" "$runtime/reports/all-artifacts.sha256" || exit $?
