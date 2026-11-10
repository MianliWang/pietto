#!/usr/bin/env bash
# Recreate the Phase77 candidate trees from candidate-exports (HEAD + binary
# patch + untracked tarball). Pietto candidates become detached worktrees of
# this clone; extension candidates are cloned from GitHub. Fails closed if a
# patch does not apply exactly.
set -Eeuo pipefail
EXPORTS="$(cd -- "${1:?usage: restore-candidates.sh <candidate-exports dir>}" && pwd -P)"
REC="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO="$(git -C "$REC" rev-parse --show-toplevel)"
EXT_URL=https://github.com/MianliWang/pietto-vscode-extension.git
mkdir -p "$REC/candidates"
for dest in "$EXPORTS"/*/; do
    name=$(basename "$dest")
    [[ -f "$dest/HEAD" ]] || continue
    head=$(<"$dest/HEAD")
    case "$name" in
        decimal-repo) target="$REC/candidates/decimal/repo" ;;
        vscode-extension-claude) target="$REC/../../../pietto-vscode-extension-claude" ;;
        *) target="$REC/candidates/$name" ;;
    esac
    if [[ -e "$target" ]]; then
        echo "skip existing $target"
        continue
    fi
    mkdir -p "$(dirname "$target")"
    if [[ "$name" == vscode-extension-claude || "$name" == editor-extension-vsix ]]; then
        git clone -q "$EXT_URL" "$target"
        git -C "$target" checkout -q --detach "$head"
    else
        git -C "$REPO" worktree add -q --detach "$target" "$head"
    fi
    if [[ -s "$dest/tracked.patch" ]]; then
        git -C "$target" apply --binary --whitespace=nowarn "$dest/tracked.patch"
    fi
    if [[ -f "$dest/untracked.tar.gz" ]]; then
        tar -C "$target" -xzf "$dest/untracked.tar.gz"
    fi
    git -C "$target" status --porcelain=v1 > /tmp/restore-status-$$
    if cmp -s /tmp/restore-status-$$ "$dest/status.txt"; then
        echo "restored $name at $head"
    else
        echo "STATUS MISMATCH for $name (compare git status with $dest/status.txt)" >&2
    fi
    rm -f /tmp/restore-status-$$
done
[[ -d "$EXPORTS/logs" ]] && cp -a "$EXPORTS/logs" "$REC/candidates/logs"
[[ -f "$EXPORTS/decimal.patch" ]] && cp -a "$EXPORTS/decimal.patch" "$REC/candidates/decimal/decimal.patch"
echo done
