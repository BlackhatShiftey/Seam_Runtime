---
name: seam-session-closeout
description: Close out repo-changing SEAM sessions by inspecting changed files, appending HISTORY.md, rebuilding HISTORY_INDEX.md, writing a snapshot, running continuity/integrity/routing verification, and reporting the exact final state. Use after implementation, documentation, roadmap, ledger, protocol, skill, or generated-adapter work changes repo state.
metadata:
  short-description: Finish SEAM sessions with verified history and snapshot continuity
---

# SEAM Session Closeout

## Purpose

Finish a SEAM repo-changing session without leaving stale status, broken history continuity, missing snapshots, unverified routing, or unreported failures.

This skill is the closeout partner for `seam-repo-navigator`, `seam-architect`, and `seam-implementation-planner`. It does not design or implement the feature. It records what changed, verifies the temporal chain, and leaves the next agent with a truthful resume point.

## Model Target

Use any capable implementation or maintenance model. For DeepSeek/Qwen-style agents, prefer:

- temperature: low
- thinking/reasoning: enabled
- purpose: exact repo bookkeeping, verification, and risk reporting

## When To Use

Use this skill after any material repo state change, including:

- code changes
- tests or fixtures
- docs, roadmap, ledger, or status updates
- protocol, routing, classification, snapshot, or history-tool changes
- local agent skills or generated adapter changes
- branch merge/sync work

Do not use this skill for read-only questions unless the user asks for a repo-health or continuity audit.

## Non-Negotiable Index Rule

`HISTORY_INDEX.md` is derived state. DeepSeek must never append, patch, or hand-edit it.

The only valid sequence is:

```powershell
python -m tools.history.new_entry ...
python -m tools.history.rebuild_index
python -m tools.history.write_snapshot --agent <agent> --entries <new-entry-id>,<relevant-prior-ids> --token-budget 1200
python -m tools.history.verify_integrity
python -m tools.history.verify_continuity
```

If the user asks to "append the index", interpret that as "append history and rebuild the derived index." Do not manually edit `HISTORY_INDEX.md`.

## Startup Check

Before writing closeout records, inspect live state:

```powershell
git status --short --branch
git log --oneline -5
```

If the session involves history, routing, ledgers, auditability, snapshots, or multi-agent continuity, verify orientation files are current enough for the task:

1. `AGENTS.md`
2. `PROJECT_STATUS.md`
3. `REPO_LEDGER.md`
4. `HISTORY_INDEX.md`
5. `docs/CODE_LAYOUT.md`
6. `docs/DATA_ROUTING.md`

Never bulk-read all of `HISTORY.md`. If previous entries are needed, use bounded context:

```powershell
python -m tools.history.build_context_pack --topics <topic> --latest 3 --token-budget 1200
python -m tools.history.build_context_pack --route <route> --token-budget 1200
```

## Safety Rules

- Do not revert, delete, reset, or overwrite unrelated work.
- Treat a dirty worktree as shared multi-agent state until proven otherwise.
- Record skipped tests as skipped, failed commands as failed, and assumptions as assumptions.
- Do not put secrets, API keys, session URLs, private links, local agent transcript links, or credential-bearing DSNs into `HISTORY.md`, snapshots, docs, commit messages, or the final answer.
- If a secret or private session URL is found in candidate files, stop and ask for rotation/history handling instead of copying it into another artifact.
- Keep generated operator/user artifacts out of git unless the user explicitly promotes them as repo-owned fixtures or docs assets.

## Closeout Workflow

### 1. Classify The Change

Identify what changed and which stable files need updates:

- `HISTORY.md`: required for every material change.
- `HISTORY_INDEX.md`: always rebuild with `python -m tools.history.rebuild_index` after appending history; never edit by hand.
- `.seam/snapshots/`: always write one snapshot after the history entry.
- `PROJECT_STATUS.md`: update when current operating state or active focus changed.
- `REPO_LEDGER.md`: update when stable policy, architecture, routing, runtime safety, or cross-agent protocol changed.
- `tools/history/routing_manifest.json` and `docs/ledgers/`: update only when classification/routing facts changed.

Use only valid history topics from `AGENTS.md`.

### 2. Inspect Candidate Files

Review the changed file list before writing history:

```powershell
git status --short
git diff --name-only
git diff --cached --name-only
```

For untracked files, inspect only files relevant to this session. Do not stage or describe unrelated files as your work.

### 3. Run The Right Verification

Choose the smallest adequate test first, then broader gates when risk warrants it.

Common gates:

```powershell
python -m pytest test_seam_all/test_seam.py -q
python -m tools.history.verify_integrity
python -m tools.history.verify_continuity
```

Add this when routes, classifications, route ledgers, or route-aware context behavior changed:

```powershell
python -m tools.history.verify_routing
```

Add `git diff --check` before final reporting when files changed.

### 4. Scan For Secrets And Session Links

Before appending history or staging, scan candidate changed files for secret-shaped strings and private session links. Keep the scan targeted to candidate files, not generated/cache-heavy directories.

If anything credential-like is found, redact/remove it locally and rerun the scan. If it was already committed, stop and ask for history-rewrite and credential-rotation handling.

### 5. Append HISTORY.md

Use the history tool, not manual editing:

```powershell
python -m tools.history.new_entry --agent <agent> --status done --topics <comma-topics> --commits <commit-or-none> --refs <comma-refs> --supersedes <latest-related-id> --body "<body>"
```

The body must state:

- previous state
- new state
- changed files
- why the change was made
- verification run and results
- failures or skipped verification
- unresolved next step, if any

Use `supersedes` for follow-up work tied to the latest relevant entry. Do not edit old entries.

### 6. Rebuild, Snapshot, Verify

After the new entry is appended, immediately rebuild the derived index:

```powershell
python -m tools.history.rebuild_index
python -m tools.history.write_snapshot --agent <agent> --entries <new-entry-id>,<relevant-prior-ids> --token-budget 1200
python -m tools.history.verify_integrity
python -m tools.history.verify_continuity
```

If routing changed:

```powershell
python -m tools.history.verify_routing
```

### 7. Final State Read

Finish with:

```powershell
git status --short --branch
git diff --stat
```

If the user asked to push, commit, publish, save to GitHub, or make the tree clean, hand off to `seam-github-publisher` after closeout. Otherwise, report the exact local state and leave unrequested git actions alone.

Do not decide commit scope casually. The publisher must include relevant source/docs/tests/protocol/skill files plus `HISTORY.md` and rebuilt `HISTORY_INDEX.md`, while excluding secrets, local env files, caches, generated artifacts, local DBs, ignored snapshot JSON, and unrelated work.

## Output Format

Use this structure:

```text
Closeout Summary: <short name>

Changed:
- <file>: <what changed>

History:
- HISTORY.md: entry #<id>, topics <topics>
- HISTORY_INDEX.md: rebuilt
- HISTORY_INDEX.md update method: rebuild_index only; no manual edits
- Snapshot: <path>

Verification:
- PASS/FAIL/SKIPPED: <command>

Final State:
- Branch: <branch and upstream state>
- Worktree: <clean / dirty, with remaining untracked or modified files>
- Push: <pushed / not requested / blocked>
- Commit handoff: <not requested | seam-github-publisher needed>

Next:
- <one concrete next step, or "none">
```

## Validation Prompts

1. A code slice changed `seam_runtime/cli.py` and tests passed. Close out the session.
2. A routing-manifest change added a new route ledger. What extra verification is required?
3. The worktree has unrelated untracked files before closeout. What do you do?

The skill fails if it:

- edits old `HISTORY.md` entries
- skips `HISTORY_INDEX.md` rebuild after appending history
- hand-edits or appends `HISTORY_INDEX.md`
- forgets to write a snapshot
- claims verification passed without command evidence
- reads all of `HISTORY.md`
- stages or reverts unrelated work
- copies secrets or private session links into repo artifacts
