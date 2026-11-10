#!/usr/bin/env bash
set -u -o pipefail

root=$(pwd -P)
runtime="$root/.cache/phase77-recovery/runtime"
log="$runtime/logs/maintenance-rebind.log"
run() {
    printf '+ %q' "$@" | tee -a "$log"
    printf '\n' | tee -a "$log"
    "$@" 2>&1 | tee -a "$log"
    result=${PIPESTATUS[0]}
    printf '[exit %s]\n' "$result" | tee -a "$log"
    return "$result"
}

run "$runtime/venvs/native/bin/python" -I "$runtime/rebind_manifest.py" || exit $?
run "$runtime/venvs/native/bin/python" -I "$runtime/rebind_wheelhouse_manifest.py" || exit $?
run "$runtime/venvs/native/bin/python" -I "$runtime/write_maintenance_mysql_binding.py" || exit $?
run stat -c '%n %s bytes' "$runtime/wheelhouse/wrapt-2.5.0-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl" || exit $?
