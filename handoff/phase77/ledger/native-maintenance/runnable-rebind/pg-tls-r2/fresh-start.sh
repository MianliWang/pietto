#!/bin/bash
# Local preparation only: bind the installed wheel, generate new TLS, then self-test.
set -eu
: "${PIETTO_PG_RUN_ROOT:?missing PIETTO_PG_RUN_ROOT}"
: "${PIETTO_PG_PYTHON:?missing PIETTO_PG_PYTHON}"
: "${PIETTO_PG_CANDIDATE:?missing PIETTO_PG_CANDIDATE}"
: "${PIETTO_PG_WHEEL:?missing PIETTO_PG_WHEEL}"
: "${PIETTO_PG_WHEEL_SHA256:?missing PIETTO_PG_WHEEL_SHA256}"
: "${PIETTO_PG_BASE:?missing PIETTO_PG_BASE}"
: "${PIETTO_PG_PATCH_SHA256:?missing PIETTO_PG_PATCH_SHA256}"
: "${PIETTO_PG_LOCK_SHA256:?missing PIETTO_PG_LOCK_SHA256}"
P=$PIETTO_PG_RUN_ROOT
LOG=$P/fresh-start.log
EXIT=$P/fresh-start.exit
rm -f "$LOG" "$EXIT"
if UV_PYTHON=3.13.13 UV_OFFLINE=1 "$PIETTO_PG_PYTHON" -I "$P/fresh_binding.py" produce --output "$P/fresh-binding.json" --wheel "$PIETTO_PG_WHEEL" --wheel-sha256 "$PIETTO_PG_WHEEL_SHA256" --candidate "$PIETTO_PG_CANDIDATE" --base "$PIETTO_PG_BASE" --patch-sha256 "$PIETTO_PG_PATCH_SHA256" --lock-sha256 "$PIETTO_PG_LOCK_SHA256" >"$LOG" 2>&1 && PIETTO_PG_RUN_ROOT="$P" UV_PYTHON=3.13.13 UV_OFFLINE=1 bash "$P/gen-tls.sh" >>"$LOG" 2>&1 && PIETTO_PG_RUN_ROOT="$P" PIETTO_PG_PYTHON="$PIETTO_PG_PYTHON" PIETTO_PG_CANDIDATE="$PIETTO_PG_CANDIDATE" PIETTO_PG_WHEEL="$PIETTO_PG_WHEEL" PIETTO_PG_WHEEL_SHA256="$PIETTO_PG_WHEEL_SHA256" PIETTO_PG_BASE="$PIETTO_PG_BASE" PIETTO_PG_PATCH_SHA256="$PIETTO_PG_PATCH_SHA256" PIETTO_PG_LOCK_SHA256="$PIETTO_PG_LOCK_SHA256" bash "$P/selftest.sh" >>"$LOG" 2>&1; then
  printf '0\n' >"$EXIT"
else
  status=$?
  printf '%s\n' "$status" >"$EXIT"
  exit "$status"
fi
