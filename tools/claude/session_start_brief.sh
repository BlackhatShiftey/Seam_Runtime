#!/usr/bin/env bash
# SessionStart brief for Claude Code in the SEAM repo.
#
# Prints the AGENTS.md-mandated startup read order plus the latest continuity
# handoff and verify-gate status so the model orients on protocol without
# waiting to be reminded.

set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT" || exit 0

PY=python3
command -v "$PY" >/dev/null 2>&1 || PY=python

LATEST=$(sed -n '14p' HISTORY_INDEX.md 2>/dev/null | awk -F'|' '{gsub(/ /,"",$2); print $2}')

cat <<EOF
[SEAM protocol brief]
  Repo: $(basename "$REPO_ROOT")
  Latest HISTORY entry: #${LATEST:-unknown}

  AGENTS.md Session Start read order (do this before any repo state change):
    1. PROJECT_STATUS.md
    2. REPO_LEDGER.md
    3. HISTORY_INDEX.md
    4. docs/CODE_LAYOUT.md
    5. docs/DATA_ROUTING.md  (when task touches history/ledgers/routing/audit)
  Then: tools.history.build_context_pack for bounded history reads.

  AGENTS.md Session End (after any repo state change):
    1. Append HISTORY.md entry (no in-place edits to committed entries).
    2. Rebuild HISTORY_INDEX.md.
    3. Write snapshot.
    4. Run verify_integrity + verify_routing + verify_continuity.

  Git commit/push commands are gated by tools/claude/preflight_protocol.sh.
EOF
