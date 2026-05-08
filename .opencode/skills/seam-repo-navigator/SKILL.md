---
name: seam-repo-navigator
description: Mandatory SEAM repository orientation protocol for DeepSeek, OpenCode, Codex, Claude, and other agents. Use this before any SEAM repo inspection, edit, test, documentation, roadmap, ledger, history, snapshot, commit, push, merge, or repo-health claim. Enforces startup reads, active/archive routing, bounded history loading, live Git verification, secret hygiene, and the rule that HISTORY_INDEX.md is derived by rebuild_index and must never be hand-edited.
metadata:
  short-description: Orient agents safely before SEAM repo work
---

# SEAM Repo Navigator

## Purpose

SEAM has a mandatory repo protocol. Follow it before making claims or edits.

This skill prevents the common model failures that break SEAM continuity:

- editing before reading current repo state
- reading all of `HISTORY.md`
- treating archive or generated code as active source
- confusing one local SEAM clone for another
- making GitHub sync claims from memory
- skipping history, index, snapshot, routing, or secret-hygiene closeout
- manually editing `HISTORY_INDEX.md` instead of rebuilding it

## DeepSeek Contract

When this skill triggers, DeepSeek must obey these rules exactly:

1. Do the orientation commands before file edits.
2. Read the startup sources in order.
3. Use bounded history packs when history is needed.
4. Produce the orientation summary before changing files.
5. Stop and report a blocker if a required protocol step cannot be performed.
6. Never substitute memory, guesses, or "probably current" for live repo evidence.

## Trigger

Use this skill automatically when the working directory is the SEAM repo or a SEAM worktree and the user asks to:

- inspect, explain, review, modify, refactor, test, commit, push, or merge repo files
- update docs, roadmap, ledgers, history, snapshots, skills, or agent instructions
- work on runtime, CLI, dashboard, REST, MCP, installer, benchmark, retrieval, compression, HS/1, MIRL, storage, or model routing
- answer whether something is current, pushed, merged, in the roadmap, stable, archived, safe, or compatible with SEAM architecture
- diagnose repo health, GitHub state, CI state, branch state, or worktree cleanliness

If the user says "fix this", "add this", "harden this", "look at the repo", "commit this", "push this", "is this up to date", or "is this in the roadmap" while in SEAM, this skill is mandatory.

## Non-Repo Boundary

If the user explicitly says the problem is outside SEAM, inspect that named surface directly. Do not edit SEAM as a detour.

Examples outside SEAM:

- Codex Desktop provider state
- Windows taskbar or icon repair
- global Claude/Codex/OpenCode config repair
- unrelated local tooling outside the repo

## Step 1: Confirm Workspace

Run live checks:

```powershell
git rev-parse --show-toplevel
git remote -v
git branch --show-current
git status --short --branch
```

Expected active root:

```text
C:\Users\iwana\OneDrive\Documents\Codex
```

If the root is not the intended SEAM checkout, stop and switch or ask. Do not write in the wrong clone.

For push, merge, or "is everything current" claims, fetch first:

```powershell
git fetch origin
git status --short --branch
git rev-list --left-right --count origin/main...main
git rev-parse HEAD
git rev-parse origin/main
```

## Step 2: Read Startup Sources

Read in this order:

1. `PROJECT_STATUS.md`
2. `REPO_LEDGER.md`
3. `HISTORY_INDEX.md`
4. `docs/CODE_LAYOUT.md`
5. `docs/DATA_ROUTING.md` when the task touches history, ledgers, maintenance records, routing, context budget, auditability, snapshots, or protocol

Also read `AGENTS.md` when:

- this is a new agent session
- the task may change repo files
- the task touches history, routing, protocol, security, commits, pushes, snapshots, or multi-agent coordination
- the user provides new `AGENTS.md` instructions in the prompt

Read model-specific shims only after canonical files:

- `CLAUDE.md` for Claude-compatible tools
- OpenCode/DeepSeek skill files under `.opencode/skills/` when the task touches local skills

## Step 3: Stay In Active Paths

Prefer active paths:

- `seam_runtime/`
- `seam.py`
- `experimental/`
- `tools/`
- `scripts/`
- `installers/`
- `docs/` except `docs/archive/`
- tests
- root status files
- `.opencode/skills/` when the task is local agent skill work

Treat these as inactive unless the user explicitly asks for historical or retired material:

- `archive/code/`
- `docs/archive/`
- `build/`
- `.venv/`
- generated/cache paths
- `__pycache__/`
- `.pytest_cache/`

If an active doc points to archived material, read only the specific referenced file and label it historical.

## Step 4: Load Bounded History

Never bulk-read all of `HISTORY.md`.

Use `HISTORY_INDEX.md` as the map. When chronology or prior work matters, use context packs:

```powershell
python -m tools.history.build_context_pack --topics <tags> --latest 3 --token-budget 1200
python -m tools.history.build_context_pack --route <route> --token-budget 1200
```

Before selecting a route, inspect the manifest when route behavior matters:

```powershell
Get-Content tools\history\routing_manifest.json
```

If no route fits, say so in the orientation summary and use `HISTORY_INDEX.md` plus targeted indexed reads.

## Step 5: Produce Orientation Summary

Before editing, output:

```text
SEAM orientation complete.
- Repo root: <path>
- Remote/branch: <origin url>, <branch>
- Repo state: <clean | dirty | ahead/behind details>
- Startup sources read: <files>
- Relevant route/context: <none | route/topics + budget>
- Active paths likely involved: <paths>
- First safe action: <what you will do first and why>
```

Only after this summary should edits begin.

## Hard Rules

- Never bulk-read `HISTORY.md`.
- Never edit before startup orientation.
- Never treat archive paths as active.
- Never infer current GitHub sync from memory.
- Never commit or record secrets, API keys, provider session links, local chat links, `.env` values, passwords, tokens, private keys, or private URLs.
- Never put local Claude/Codex/ChatGPT/OpenCode session links in history, snapshots, docs, comments, commits, or handoffs.
- Never overwrite old history entries. Append new entries and use `supersedes`.
- Never manually edit `HISTORY_INDEX.md` to add an entry. Append `HISTORY.md`, then run `python -m tools.history.rebuild_index`.
- Never duplicate long protocol prose across docs. Use pointer cards such as `see HISTORY#NNN`.
- Never move generated user/operator artifacts into git unless the user explicitly promotes them as fixtures or docs assets.
- Never change stable architecture, policy, or routing facts without updating the right durable file.

## GitHub Commit And Push Handoff

If the user asks to commit, push, publish, save to GitHub, make the worktree clean, or prepare for reset, hand off to `seam-github-publisher` after session closeout.

The publisher must decide what to commit from live evidence:

- include requested source/docs/test/protocol/skill files
- include `HISTORY.md`
- include `HISTORY_INDEX.md` only after `python -m tools.history.rebuild_index`
- exclude secrets, `.env`, caches, generated artifacts, local databases, and unrelated user/agent work
- do not force-add ignored snapshot JSON unless explicitly promoted

Use explicit path staging by default, not blind `git add .`.

## Session-End Handoff

If any repo state changed, hand off to `seam-session-closeout` or perform the same required sequence:

```powershell
python -m tools.history.new_entry ...
python -m tools.history.rebuild_index
python -m tools.history.write_snapshot --agent <agent> --entries <new-entry-id>,<relevant-prior-ids> --token-budget 1200
python -m tools.history.verify_integrity
python -m tools.history.verify_continuity
```

If routing, classifications, route ledgers, or route-aware context behavior changed, also run:

```powershell
python -m tools.history.verify_routing
```

## SEAM Invariants

Preserve unless the user explicitly revisits the architecture:

- SQLite is canonical truth.
- Vector stores are derived retrieval layers.
- PACK is derived prompt-time context, not canonical storage.
- `HISTORY.md` is append-only.
- `HISTORY_INDEX.md` is derived state from `tools.history.rebuild_index`.
- Snapshots are bounded handoff artifacts.
- `tools/history/routing_manifest.json` is the mutable route map.
- `REPO_LEDGER.md` stores stable repo-wide policy and architecture facts.
- `PROJECT_STATUS.md` stores current operating state and active focus.
- SEAM-HS/1 surfaces are queryable visual containers, not replacements for SQLite.
- Direct-read AI-native machine language is the primary compression/query artifact; opaque payloads are only backing layers for exact rebuild/integrity.

## Conditional Guidance

### Git, Push, Merge, Repo Health

Fetch before remote-alignment claims:

```powershell
git fetch origin
git status --short --branch
git rev-list --left-right --count origin/main...main
git rev-parse HEAD
git rev-parse origin/main
```

For commit/push execution, use `seam-github-publisher`.

### Architecture Or Roadmap

Read:

- `ROADMAP.md`
- `PROJECT_STATUS.md`
- `REPO_LEDGER.md`
- `HISTORY_INDEX.md`
- relevant `docs/roadmap/*` file when named or clearly applicable

For Agent Compiler work:

```text
docs/roadmap/AGENT_COMPILER.md
```

### History, Ledger, Routing, Auditability

Read `docs/DATA_ROUTING.md` and inspect `tools/history/routing_manifest.json`.

Run after route/ledger/classification changes:

```powershell
python -m tools.history.verify_routing
```

### Tests

Before adding or moving tests, inspect current test layout and CI paths.

Primary suite:

```text
test_seam_all/test_seam.py
```

Root-level `test_seam_*.db` sprawl is not desired. Per-test SQLite artifacts should route into `test_seam/`.

## Validation Prompts

1. "Is everything pushed to main?" Expected: fetch, compare `main` and `origin/main`, report exact SHAs/counts.
2. "Add a new adapter under `seam_runtime`." Expected: orient first, stay in active paths, inspect tests, then edit.
3. "Document the latest route change." Expected: read routing docs/manifest, use bounded history, update durable files, then close out.
4. "Append the index." Expected: refuse manual index append; append `HISTORY.md` then run `rebuild_index`.

The skill fails if it edits before orientation, reads all history, hand-edits `HISTORY_INDEX.md`, treats archive code as active, or makes current-state claims without live evidence.
