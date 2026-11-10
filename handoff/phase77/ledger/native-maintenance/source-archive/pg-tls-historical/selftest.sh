#!/bin/bash
set -eu
P=/tmp/pietto-p77-maint-pg-run
OUT=$P/selftest-current.stdout
EXIT=$P/selftest-current.exit
rm -f "$OUT" "$EXIT"
if UV_PYTHON=3.13.13 nice -n 19 python3 -I "$P/judge.py" selftest >"$OUT" 2>&1; then
  printf '0\n' >"$EXIT"
else
  status=$?
  printf '%s\n' "$status" >"$EXIT"
  exit "$status"
fi
