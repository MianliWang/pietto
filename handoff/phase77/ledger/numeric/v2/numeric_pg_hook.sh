#!/bin/sh
# Invoke only while the parent-owned PostgreSQL literal-none relay is live.
set -eu

HERE=/tmp/pietto-p77-numeric-prereg-r4
MANIFEST=$HERE/manifest.json
MATERIALIZER=$HERE/materialize_endpoint.py
PROBE=$HERE/p77_mysql_numeric_probe.py
RELAY=/tmp/pietto-p77-maint-pg-run-r2/relay.py

if [ "${1-}" = "--self-check" ]; then
    test -r "$MANIFEST" && test -r "$MATERIALIZER" && test -r "$PROBE" && test -r "$RELAY"
    grep -q 'pietto_numeric_probe' "$PROBE"
    echo "numeric PostgreSQL hook self-check passed"
    exit 0
fi

if [ "$#" -ne 11 ] || [ "$1" != "--start" ] || [ "$2" != "--container" ] || [ "$4" != "--port" ] || [ "$6" != "--ca-file" ] || [ "$8" != "--run-dir" ] || [ "$10" != "--candidate-python" ]; then
    echo "usage: numeric_pg_hook.sh --start --container ID --port PORT --ca-file PATH --run-dir DIR --candidate-python PYTHON" >&2
    exit 2
fi

CONTAINER=$3
PORT=$5
CA=$7
RUN=$9
PY=$11
case "$CONTAINER" in pietto-p77-maint-pg-*) ;; *) echo "unexpected owned container" >&2; exit 2 ;; esac
case "$RUN" in /tmp/pietto-p77-numeric-pg-run-*) ;; *) echo "unexpected run directory" >&2; exit 2 ;; esac
test ! -e "$RUN" || { echo "run directory exists" >&2; exit 2; }
test -r "$CA" || { echo "caller CA unavailable" >&2; exit 2; }
case "$PORT" in *[!0-9]*|'') exit 2 ;; esac
test "$PORT" -gt 0 && test "$PORT" -le 65535 || exit 2

mkdir -m 700 "$RUN"
PASSWORD=$(python3 -I -c 'import secrets; print(secrets.token_hex(24))')
bootstrap() {
    printf "CREATE ROLE pietto_numeric_probe LOGIN PASSWORD '%s';\n" "$PASSWORD"
    printf "CREATE DATABASE pietto_numeric_probe OWNER pietto_numeric_probe;\n"
}
bootstrap | docker exec -i "$CONTAINER" psql -X -q -v ON_ERROR_STOP=1 -U postgres -d postgres >/dev/null
HBA=$(docker exec "$CONTAINER" psql -X -q -A -t -U postgres -d postgres -c 'SHOW hba_file')
test -n "$HBA" || { echo "missing hba path" >&2; exit 1; }
printf '%s\n' 'hostssl pietto_numeric_probe pietto_numeric_probe 127.0.0.1/32 scram-sha-256' \
    | docker exec -i -u postgres "$CONTAINER" sh -c "cat >> '$HBA'"
docker exec "$CONTAINER" psql -X -q -v ON_ERROR_STOP=1 -U postgres -d postgres -c 'SELECT pg_reload_conf()' >/dev/null
"$PY" -I -B "$MATERIALIZER" --engine postgres --port "$PORT" --ca-file "$CA" --out "$RUN/endpoint.json"
python3 -I - <<PY
import hashlib, json
from pathlib import Path
run = Path("$RUN")
endpoint = json.loads((run / "endpoint.json").read_text())
(run / "bootstrap.json").write_text(json.dumps({
    "container": "$CONTAINER", "role": "pietto_numeric_probe", "database": "pietto_numeric_probe",
    "relay_sha256": hashlib.sha256(Path("$RELAY").read_bytes()).hexdigest(),
    "endpoint": {key: value for key, value in endpoint.items() if key != "password_env"},
}, indent=2, sort_keys=True) + "\n")
PY
env -i PATH=/usr/bin:/bin UV_PYTHON=3.13.13 UV_OFFLINE=1 UV_LINK_MODE=copy \
    PIETTO_NUMERIC_PROBE_PASSWORD="$PASSWORD" \
    "$PY" -I -B "$PROBE" --run-plan "$MANIFEST" --endpoint-json "$RUN/endpoint.json" --write-receipt "$RUN/numeric-receipt.json"
