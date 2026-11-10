#!/bin/bash
set -eu
P=/tmp/pietto-p77-maint-pg-remaining-run-r4
OUT=$P/selftest.stdout
EXIT=$P/selftest.exit
rm -f "$OUT" "$EXIT"
if UV_PYTHON=3.13.13 nice -n 19 /tmp/pietto-p77-maint-pg-run/venv-wheel-fresh/bin/python -I "$P/judge.py" selftest >"$OUT" 2>&1; then
  printf '0\n' >"$EXIT"
else
  status=$?
  printf '%s\n' "$status" >"$EXIT"
  exit "$status"
fi
