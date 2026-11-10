#!/usr/bin/env bash
# R2 preserves the R1 launcher and changes only its shell assignment order.
set -Eeuo pipefail

readonly EVIDENCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly SOURCE="$EVIDENCE_DIR/../maintenance-package-r1-20261110T042500Z/run-package-smoke.sh"
readonly GENERATED="$EVIDENCE_DIR/run-package-smoke.sh"

if [[ "${PIETTO_M77_PACKAGE_SMOKE_START:-}" != YES ]]; then
    printf '%s\n' 'Refusing to start without PIETTO_M77_PACKAGE_SMOKE_START=YES.' >&2
    exit 64
fi
[[ -f "$SOURCE" && ! -e "$GENERATED" ]] || { printf '%s\n' 'R2 launcher source missing or generated runner already exists.' >&2; exit 65; }
sha256sum "$SOURCE" > "$EVIDENCE_DIR/r1-launcher.sha256"
sed \
    -e 's/maintenance-package-r1-20261110T042500Z/maintenance-package-r2-20261110T043000Z/g' \
    -e 's/export UV_PROJECT_ENVIRONMENT="\$RUNTIME\/venvs\/core-dev" VIRTUAL_ENV="\$UV_PROJECT_ENVIRONMENT"/export UV_PROJECT_ENVIRONMENT="\$RUNTIME\/venvs\/core-dev"\nexport VIRTUAL_ENV="\$UV_PROJECT_ENVIRONMENT"/' \
    "$SOURCE" > "$GENERATED"
bash "$GENERATED"
