---
name: seam-github-publisher
description: Stage, commit, push, and verify SEAM repo changes on GitHub without staging unrelated work, secrets, generated artifacts, or stale local files. Use when the user asks to commit, push, publish, save local updates, get the repo clean, verify everything is on main, merge, or prepare for reset. Enforces explicit path staging, candidate-file scans, safe commit messages, remote alignment checks, and no manual HISTORY_INDEX.md edits.
metadata:
  short-description: Commit and push SEAM changes safely to GitHub
---

# SEAM GitHub Publisher

## Purpose

Publish SEAM repo changes to GitHub safely and verifiably.

This skill answers:

- what to commit
- what not to commit
- how to stage without grabbing unrelated work
- how to write safe commit messages
- when to push
- how to prove local `main` and `origin/main` are aligned

## DeepSeek Contract

DeepSeek must not use `git add .` in a dirty shared worktree unless the user explicitly asked to commit every repo-relevant file and the candidate list has been audited.

Default behavior is explicit path staging.

If the user asks "commit everything" or "save all project files before reset", interpret that as all repo-relevant source/docs/test/protocol files after audit, not secrets, caches, ignored generated artifacts, local databases, user outputs, or private environment files.

## Trigger

Use this skill when the user asks to:

- commit
- push
- publish
- merge
- save repo work before reset
- get the worktree clean
- verify everything is pushed to `main`
- verify local and GitHub are aligned
- prepare a branch or PR

Also use this after `seam-session-closeout` when the user explicitly wants the change committed or pushed.

## Required Pre-Publish State

Before staging, repo-changing work must already be closed out:

```powershell
python -m tools.history.new_entry ...
python -m tools.history.rebuild_index
python -m tools.history.write_snapshot --agent <agent> --entries <new-entry-id>,<relevant-prior-ids> --token-budget 1200
python -m tools.history.verify_integrity
python -m tools.history.verify_continuity
```

If routing/classification/ledger routes changed:

```powershell
python -m tools.history.verify_routing
```

`HISTORY_INDEX.md` is derived. Never hand-edit it to make a commit look current.

## Inspect State

Run:

```powershell
git status --short --branch
git diff --name-only
git diff --cached --name-only
git ls-files --others --exclude-standard
```

For remote alignment or push claims, fetch:

```powershell
git fetch origin
git rev-list --left-right --count origin/main...main
git rev-parse HEAD
git rev-parse origin/main
```

Interpret `git rev-list --left-right --count origin/main...main`:

- `0 0`: local `main` and `origin/main` point to the same history
- `0 N`: local is ahead by `N`
- `N 0`: local is behind by `N`
- `N M`: histories diverged; fetch/merge/rebase decision needed before push

## What To Commit

Commit files that are part of the requested repo change:

- active runtime code under `seam_runtime/`
- `seam.py`
- active prototypes under `experimental/`
- active tooling under `tools/`
- active scripts under `scripts/`
- installers under `installers/`
- tests, especially `test_seam_all/test_seam.py` and `tools/history/test_history_tools.py`
- active docs under `docs/` excluding `docs/archive/`
- root status/protocol docs such as `PROJECT_STATUS.md`, `REPO_LEDGER.md`, `ROADMAP.md`, `AGENTS.md`
- `HISTORY.md` after material changes
- `HISTORY_INDEX.md` only after it was regenerated with `python -m tools.history.rebuild_index`
- `.opencode/skills/*/SKILL.md` when local DeepSeek/OpenCode skill behavior changed
- tracked config/metadata files when the requested change actually requires them

For SEAM skill work, the expected commit set usually includes:

```text
.opencode/skills/<changed-skill>/SKILL.md
HISTORY.md
HISTORY_INDEX.md
```

Snapshot JSON files are written for continuity but are local derived artifacts in this repo unless Git shows them as tracked or the user explicitly asks to promote them. Do not force-add ignored `.seam/snapshots/*.json` by default.

## What Not To Commit

Never commit:

- API keys
- passwords
- tokens
- private keys
- local `.env` values
- provider session links
- Claude/Codex/ChatGPT/OpenCode local transcript or share links
- local database artifacts such as root-level `test_seam_*.db`
- `.venv/`
- `__pycache__/`
- `.pytest_cache/`
- build outputs
- generated/cache-heavy folders
- ignored benchmark run outputs
- generated operator/user `.seam.png` surfaces unless deliberately promoted as repo-owned fixtures/docs assets
- unrelated files from another agent/user
- files in `archive/code/` or `docs/archive/` unless the requested change explicitly touches archived material

If a secret or private session URL appears in candidate files, stop. Redact/remove locally and ask for rotation/history handling if it was already committed.

## Candidate Scan

Before staging candidate paths, run a targeted scan over those files.

Example pattern:

```powershell
Select-String -Path <candidate-files> -Pattern 'api[_-]?key|password|token\s*=|secret\s*=|sk-[A-Za-z0-9]|chatgpt.com/share|claude.ai/share|thread_' -CaseSensitive:$false
```

False positives from instruction examples are allowed only when they are clearly placeholder scan patterns, not real credentials.

Also run:

```powershell
git diff --check
```

Windows LF/CRLF warnings alone are not commit blockers when `git status` and diffs are otherwise expected.

## Stage Explicitly

Stage exact paths:

```powershell
git add -- <path1> <path2> <path3>
```

Use `git add -u -- <path>` for tracked modifications only when appropriate.

Avoid `git add .` in a dirty worktree. Use it only when:

1. user explicitly asked to commit all repo-relevant updates,
2. untracked files were audited,
3. ignored/generated/secrets are excluded,
4. the final staged list is reviewed.

After staging:

```powershell
git diff --cached --name-status
git diff --cached --stat
git status --short --branch
```

If unrelated files are staged, unstage only those files:

```powershell
git restore --staged -- <path>
```

Do not use destructive reset commands.

## Commit

Use a concise commit message that states the repo change, not the chat session.

Good examples:

```powershell
git commit -m "Add DeepSeek SEAM skill chain"
git commit -m "Harden SEAM history closeout protocol"
git commit -m "Document agent compiler roadmap"
```

Never put secrets, private links, chat/share URLs, transcript links, local thread IDs, or provider session links in commit messages.

If `HISTORY.md` was appended before the commit and says `commits: none`, do not rewrite old history after committing. The next material history entry can reference the commit if needed. SEAM history is append-only.

## Push

Push only when the user asked to push, publish, sync, save to GitHub, or make remote current.

For `main`:

```powershell
git push origin main
git fetch origin
git rev-list --left-right --count origin/main...main
git rev-parse HEAD
git rev-parse origin/main
git status --short --branch
```

A successful pushed-and-aligned finish requires:

```text
git rev-list --left-right --count origin/main...main
0 0
```

and matching `HEAD` / `origin/main` SHAs.

If branch protection or remote rejection occurs, report the exact error and stop for merge/PR handling. Do not force-push unless the user explicitly requests it and understands the risk.

## Merge Or Divergence

If `origin/main...main` returns `N M`:

1. fetch has already run
2. inspect recent commits
3. explain the divergence
4. merge or rebase only according to repo policy/user instruction
5. rerun tests/continuity if merge changes files
6. push after verification

Default for this repo when preserving shared history is a normal merge unless the user requested rebase.

## Final Report

Use:

```text
GitHub Publish Summary: <short name>

Committed:
- <commit sha>: <message>

Staged/Committed Files:
- <path>

Excluded:
- <path or class>: <reason>

Verification:
- PASS/FAIL/SKIPPED: <command>

Remote:
- Branch: <branch>
- origin/main alignment: <0 0 | ahead/behind/diverged>
- HEAD: <sha>
- origin/main: <sha>

Final Worktree:
- <clean | remaining files and why>
```

## Validation Prompts

1. The worktree has `.opencode/`, `HISTORY.md`, `HISTORY_INDEX.md`, and ignored snapshot JSON after skill work. What gets committed?
2. The user asks "push all local updates before reset." What do you inspect and exclude?
3. `git rev-list --left-right --count origin/main...main` returns `1 2`. What do you do?
4. A candidate file contains a real provider key. Expected: stop, redact/remove, ask for rotation/history handling if committed.

The skill fails if it uses `git add .` blindly, stages unrelated work, commits generated/local artifacts by default, skips candidate secret scans, writes unsafe commit messages, skips remote alignment checks, force-pushes without explicit instruction, or hand-edits `HISTORY_INDEX.md`.
