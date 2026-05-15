#!/usr/bin/env bash
# Install the SEAM canonical pre-commit hook into .git/hooks/pre-commit.
#
# Tries a symlink first (so updates to tools/git-hooks/pre-commit are picked
# up automatically). Falls back to a copy on filesystems that do not support
# symlinks (exFAT, FAT32, some Windows configurations). The copy embeds a
# CANONICAL_SHA marker so subsequent commits can detect drift and warn that
# `bash tools/git-hooks/install.sh` should be re-run.
#
# Pass --force to overwrite an existing .git/hooks/pre-commit (backed up to
# .git/hooks/pre-commit.bak.<timestamp>).

set -u

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1

SRC_REL="tools/git-hooks/pre-commit"
SRC="$REPO_ROOT/$SRC_REL"
DEST="$REPO_ROOT/.git/hooks/pre-commit"

if [ ! -f "$SRC" ]; then
  echo "Missing $SRC" >&2
  exit 1
fi

chmod +x "$SRC"

FORCE=0
for arg in "$@"; do
  case "$arg" in
    --force|-f) FORCE=1 ;;
  esac
done

SRC_SHA="$(sha256sum "$SRC" | awk '{print $1}')"

# Already a symlink pointing at the canonical hook?
if [ -L "$DEST" ] && [ "$(readlink "$DEST")" = "../../$SRC_REL" ]; then
  echo "[SEAM hooks] Already installed (symlink): $DEST"
  exit 0
fi

# Already a copy with matching marker?
if [ -f "$DEST" ] && grep -q "^# CANONICAL_SHA: $SRC_SHA\$" "$DEST" 2>/dev/null; then
  echo "[SEAM hooks] Already installed (copy, sha matches): $DEST"
  exit 0
fi

# Need to overwrite — back up if anything exists.
if [ -e "$DEST" ] || [ -L "$DEST" ]; then
  if [ "$FORCE" -ne 1 ]; then
    echo "[SEAM hooks] $DEST already exists and does not match canonical." >&2
    echo "[SEAM hooks] Rerun with --force to replace (the existing file will be backed up)." >&2
    exit 1
  fi
  STAMP="$(date +%Y%m%d-%H%M%S)"
  mv "$DEST" "$DEST.bak.$STAMP"
  echo "[SEAM hooks] Backed up existing hook to $DEST.bak.$STAMP"
fi

# Try symlink first.
if ln -s "../../$SRC_REL" "$DEST" 2>/dev/null; then
  echo "[SEAM hooks] Installed (symlink): $DEST -> ../../$SRC_REL"
  exit 0
fi

# Fall back to copy with embedded canonical sha marker.
{
  head -n 1 "$SRC"
  echo "# CANONICAL_SHA: $SRC_SHA"
  echo "# Installed by tools/git-hooks/install.sh (copy mode; symlink unsupported by filesystem)."
  echo "# Re-run that installer after pulling updates if the source hash changes."
  tail -n +2 "$SRC"
} > "$DEST"
chmod +x "$DEST"
echo "[SEAM hooks] Installed (copy): $DEST"
echo "[SEAM hooks] Source: $SRC_REL  sha256=$SRC_SHA"
