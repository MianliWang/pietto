#!/usr/bin/env bash
set -u -o pipefail

root=$(pwd -P)
runtime="$root/.cache/phase77-recovery/runtime"
candidate="$root/.cache/phase77-recovery/candidates/maintenance"
cache="$candidate/.uv-runtime-cache"
downloader=/tmp/pietto-phase77-wheel-downloader
log="$runtime/logs/maintenance-rebind.log"
cp312=wrapt-2.5.0-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl

touch "$log"
run() {
    printf '+ %q' "$@" | tee -a "$log"
    printf '\n' | tee -a "$log"
    "$@" 2>&1 | tee -a "$log"
    result=${PIPESTATUS[0]}
    printf '[exit %s]\n' "$result" | tee -a "$log"
    return "$result"
}

stage=$(mktemp -d /tmp/pietto-phase77-cp312-wrapt.XXXXXX) || exit $?
printf '+ mktemp -d /tmp/pietto-phase77-cp312-wrapt.XXXXXX\n%s\n[exit 0]\n' "$stage" | tee -a "$log"
run env PIP_CACHE_DIR="$stage/pip-cache" "$downloader/bin/python" -m pip install --dry-run --ignore-installed --no-deps --only-binary=:all: --platform manylinux_2_28_x86_64 --implementation cp --python-version 3.12 --abi cp312 --report "$runtime/reports/wrapt-cp312-resolve.json" wrapt==2.5.0 || exit $?
run env PIP_CACHE_DIR="$stage/pip-cache" "$downloader/bin/python" -m pip download --no-deps --only-binary=:all: --platform manylinux_2_28_x86_64 --implementation cp --python-version 3.12 --abi cp312 --dest "$stage" wrapt==2.5.0 || exit $?
run test -f "$stage/$cp312" || exit $?
if test -f "$runtime/wheelhouse/$cp312"; then
    run cmp "$stage/$cp312" "$runtime/wheelhouse/$cp312" || exit $?
else
    run cp "$stage/$cp312" "$runtime/wheelhouse/$cp312" || exit $?
fi
run sha256sum "$runtime/wheelhouse/$cp312" || exit $?
run env PIP_CACHE_DIR="$stage/pip-cache" "$downloader/bin/python" -m pip install --dry-run --ignore-installed --no-deps --only-binary=:all: --report "$runtime/reports/uv-build-resolve.json" uv-build==0.13.7 || exit $?
run env PIP_CACHE_DIR="$stage/pip-cache" "$downloader/bin/python" -m pip download --no-deps --only-binary=:all: --dest "$stage" uv-build==0.13.7 || exit $?
uvbuild=$(find "$stage" -maxdepth 1 -type f -name 'uv_build-0.13.7-*.whl' -print -quit)
test -n "$uvbuild" || exit 1
if test -f "$runtime/wheelhouse/$(basename "$uvbuild")"; then
    run cmp "$uvbuild" "$runtime/wheelhouse/$(basename "$uvbuild")" || exit $?
else
    run cp "$uvbuild" "$runtime/wheelhouse/" || exit $?
fi
run sha256sum "$runtime/wheelhouse/$(basename "$uvbuild")" || exit $?
run env UV_PYTHON=3.13.13 UV_CACHE_DIR="$cache" UV_OFFLINE=1 UV_NO_SYNC=1 uv pip install --python "$runtime/venvs/core-dev/bin/python" --no-index --find-links "$runtime/wheelhouse" --editable "$candidate" -r "$runtime/requirements/core-dev.txt" || exit $?
run env UV_PYTHON=3.13.13 UV_CACHE_DIR="$cache" UV_OFFLINE=1 UV_NO_SYNC=1 uv pip check --python "$runtime/venvs/core-dev/bin/python" || exit $?
run env PYTHONDONTWRITEBYTECODE=1 "$runtime/venvs/core-dev/bin/python" -I -c 'import importlib.metadata as m, pathlib, pietto, platform; root=pathlib.Path("'"$candidate"'") / "src" / "pietto"; assert platform.python_version() == "3.13.13"; assert pathlib.Path(pietto.__file__).resolve().parent == root.resolve(); assert "pyarrow" not in {x.metadata["Name"].lower() for x in m.distributions()}; print(pietto.__file__)' || exit $?
run "$runtime/venvs/native/bin/python" -I "$runtime/rebind_manifest.py" || exit $?
run "$runtime/venvs/native/bin/python" -I "$runtime/rebind_wheelhouse_manifest.py" || exit $?
run "$runtime/venvs/native/bin/python" -I "$runtime/write_maintenance_mysql_binding.py" || exit $?
