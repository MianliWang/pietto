#!/bin/sh
# NEW_RECONSTRUCTION: fresh identities are mandatory; do not invoke historical paths.
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: mysql.sh RUN_DIRECTORY" >&2
    exit 2
fi

RUN_DIRECTORY=$1
EVIDENCE_ROOT=/home/mianliwang/projects/pietto/.cache/phase77-recovery/evidence
for name in PIETTO_MAINT_PYTHON PIETTO_MAINT_CANDIDATE PIETTO_MAINT_WHEEL PIETTO_MAINT_WHEEL_SHA256 PIETTO_MAINT_HOUSE PIETTO_MAINT_OTEL_HOUSE PIETTO_MAINT_EXPECTED_BINDING PIETTO_MAINT_LOCK; do
    eval "value=\${$name-}"
    [ -n "$value" ] || { echo "missing $name" >&2; exit 2; }
done
case "$RUN_DIRECTORY" in
    "$EVIDENCE_ROOT"/mysql-maintenance-*) ;;
    *) echo "run directory must be in the persistent maintenance evidence root" >&2; exit 2 ;;
esac
[ "$(dirname "$RUN_DIRECTORY")" = "$EVIDENCE_ROOT" ] || { echo "nested run directory refused" >&2; exit 2; }
[ ! -e "$RUN_DIRECTORY" ] || { echo "run directory exists" >&2; exit 2; }
[ -f "$PIETTO_MAINT_EXPECTED_BINDING" ] || { echo "missing expected binding" >&2; exit 2; }
[ -f "$PIETTO_MAINT_WHEEL" ] || { echo "missing wheel" >&2; exit 2; }
[ -x "$PIETTO_MAINT_PYTHON" ] || { echo "missing python" >&2; exit 2; }

exec nice -n 19 flock --close -w 600 "$PIETTO_MAINT_LOCK" \
    timeout 7200 env UV_PYTHON=3.13.13 UV_OFFLINE=1 UV_LINK_MODE=copy \
    "$PIETTO_MAINT_PYTHON" -I "$(dirname "$0")/campaign.py" \
    --candidate "$PIETTO_MAINT_CANDIDATE" --wheel "$PIETTO_MAINT_WHEEL" --wheel-sha256 "$PIETTO_MAINT_WHEEL_SHA256" \
    --house "$PIETTO_MAINT_HOUSE" --otel-house "$PIETTO_MAINT_OTEL_HOUSE" \
    --expected-binding "$PIETTO_MAINT_EXPECTED_BINDING" --run-dir "$RUN_DIRECTORY"
