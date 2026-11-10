#!/bin/bash
# Target-only entrypoint. Run only after an explicit PostgreSQL authorization.
set -eu
: "${PIETTO_PG_RUN_ROOT:?missing PIETTO_PG_RUN_ROOT}"
: "${PIETTO_PG_PYTHON:?missing PIETTO_PG_PYTHON}"
: "${PIETTO_PG_IMAGE:?missing PIETTO_PG_IMAGE}"
[ "$PIETTO_PG_IMAGE" = "sha256:f372eda99ac2ea249c3dce566dcdf468397035371284d2cf2103b4bc52b3b39e" ] || { echo "wrong PostgreSQL 18.6 image" >&2; exit 2; }
P=$PIETTO_PG_RUN_ROOT
LOCK=/tmp/claude-1000/pietto-docker-campaign-postgres.lock
NONCE=$(UV_PYTHON=3.13.13 UV_OFFLINE=1 "$PIETTO_PG_PYTHON" -I -c 'import secrets; print(secrets.token_hex(12))')
CONTAINER=pietto-p77-maint-pg-$NONCE
LABEL=pietto.phase77.pg-run=$NONCE
flock --close -w 600 "$LOCK" timeout 7200 env PIETTO_PG_CONTAINER="$CONTAINER" PIETTO_PG_CONTAINER_LABEL="$LABEL" PIETTO_PG_TARGET_NONCE="$NONCE" PIETTO_PG_TARGET_LOCK="$LOCK" bash -c '"$1" -I -c '"'"'import json, pathlib, sys; pathlib.Path(sys.argv[1]).write_text(json.dumps({"nonce":sys.argv[2],"lock":sys.argv[3],"timeout_seconds":7200,"container_name":sys.argv[4],"container_label":sys.argv[5]}, sort_keys=True))'"'"' "$2/target-invocation.json" "$3" "$4" "$5" "$6"; exec bash "$2/pg.sh"' bash "$PIETTO_PG_PYTHON" "$P" "$NONCE" "$LOCK" "$CONTAINER" "$LABEL"
