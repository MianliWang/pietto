#!/bin/sh
# Run only after the parent review accepts this package and an empty run path.
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: mysql.sh RUN_DIRECTORY" >&2
    exit 2
fi

RUN_DIRECTORY=$1
WHEELHOUSE=/tmp/pietto-maintenance-runtime-wheelhouse
OTEL_WHEELHOUSE=/tmp/pietto-maintenance-otel-wheelhouse
EXPECTED_BINDING=/tmp/pietto-p77-maint-mysql-prereg/expected-binding.json
EXPECTED_BINDING_SHA256=4a037f713fe1a13bcbfd9dcade138b1bb0d024cab5eb42788d7367de82e99a42
CANDIDATE=/tmp/pietto-maintenance-2601-338
WHEEL=/tmp/pietto-maintenance-2601-338-package-dist-r2/pietto-0.1.10-py3-none-any.whl
PACKAGE=/tmp/pietto-p77-maint-mysql-none-campaign
WHEEL_SHA256=f4c96921c4d4ceb057830f2dd21f2e634325dac2bef933532747ae4aab963a73

case "$RUN_DIRECTORY" in
    /tmp/pietto-p77-maint-mysql-run-*) ;;
    *) echo "run directory must be owned /tmp/pietto-p77-maint-mysql-run-*" >&2; exit 2 ;;
esac
[ ! -e "$RUN_DIRECTORY" ] || { echo "run directory exists" >&2; exit 2; }
[ "$(sha256sum "$EXPECTED_BINDING" | awk '{print $1}')" = "$EXPECTED_BINDING_SHA256" ] || { echo "expected binding drift" >&2; exit 2; }

exec nice -n 19 flock --close -w 600 /tmp/claude-1000/pietto-docker-campaign-mysql.lock \
    timeout 7200 env UV_PYTHON=3.13.13 UV_OFFLINE=1 UV_LINK_MODE=copy \
    /tmp/pietto-maintenance-2601-338/.venv/bin/python -I "$PACKAGE/campaign.py" \
    --candidate "$CANDIDATE" --wheel "$WHEEL" --wheel-sha256 "$WHEEL_SHA256" \
    --house "$WHEELHOUSE" --otel-house "$OTEL_WHEELHOUSE" \
    --expected-binding "$EXPECTED_BINDING" --run-dir "$RUN_DIRECTORY"
