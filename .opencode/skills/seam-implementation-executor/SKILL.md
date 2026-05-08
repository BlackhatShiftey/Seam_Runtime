---
name: seam-implementation-executor
description: Execute a validated SEAM implementation plan without redesigning it. Use after seam-repo-navigator, seam-architect, and seam-implementation-planner have produced an oriented build plan. Enforces active-path edits, dirty-worktree safety, exact file ownership, targeted tests, no destructive git behavior, and mandatory handoff to seam-session-closeout for HISTORY.md append, HISTORY_INDEX.md rebuild, snapshot write, and continuity verification.
metadata:
  short-description: Execute SEAM build plans with tests and protocol discipline
---

# SEAM Implementation Executor

## Purpose

Implement a validated SEAM build plan exactly, in small verifiable slices, without redesigning architecture or breaking repo protocol.

This skill is the execution partner for:

```text
seam-repo-navigator -> seam-architect -> seam-implementation-planner -> seam-implementation-executor -> seam-test-hardener -> seam-session-closeout -> seam-github-publisher when commit/push is requested
```

## DeepSeek Contract

DeepSeek must not improvise around missing plan details.

If the plan lacks a file path, interface, verification command, dependency order, or rollback point, stop and ask for `seam-implementation-planner` to repair the plan. Do not fill structural gaps with guesses.

## Trigger

Use this skill when:

- the user says to implement, execute, build, apply, or start a validated plan
- `seam-implementation-planner` output exists
- a multi-file SEAM change has already been designed
- a code/doc/test slice needs direct file edits

Do not use this skill for:

- pure architecture work
- open-ended design
- one-line/simple fixes that can be safely done directly after repo orientation
- session-end bookkeeping only

## Required Inputs

Before editing, confirm:

- repo orientation is complete
- build plan exists
- target files are in active paths unless archive work was explicitly requested
- tests are named
- rollback instructions exist
- user did not prohibit edits, commits, or pushes

Run:

```powershell
git status --short --branch
git diff --name-only
git diff --cached --name-only
```

If unrelated changes exist, leave them alone. If they touch the same files, inspect carefully and adapt without reverting user or other-agent work.

## File Ownership Rules

Only edit files named by the plan or files directly required by the implementation after inspection.

Active paths:

- `seam_runtime/`
- `seam.py`
- `experimental/`
- `tools/`
- `scripts/`
- `installers/`
- `docs/` except `docs/archive/`
- tests
- root status files
- `.opencode/skills/` for local skill work

Inactive paths require explicit user or architecture approval:

- `archive/code/`
- `docs/archive/`
- `build/`
- `.venv/`
- generated/cache paths

## Execution Workflow

### 1. Restate The Slice

Before editing each slice, state:

```text
Executing slice <N>: <name>
- Goal: <verifiable outcome>
- Files I will touch: <paths>
- Tests after slice: <commands>
- Rollback: <plan-provided rollback>
```

### 2. Inspect Existing Patterns

Read nearby code/tests/docs first. Prefer existing project helpers and style.

Use targeted reads. Do not scan archive/generated/cache paths unless the plan explicitly requires them.

### 3. Edit With Minimal Scope

Use focused edits:

- do not refactor unrelated code
- do not rename public commands unless the plan requires it
- do not change packaging metadata unless the plan requires it
- do not alter runtime behavior from a docs-only plan
- do not create new abstractions unless the plan calls for them or existing patterns require them

### 4. Run Slice Verification

After each code-producing slice, run the plan's test command.

Examples:

```powershell
python -m py_compile seam_runtime\<module>.py test_seam_all\test_seam.py
python -m pytest test_seam_all/test_seam.py -q -k "<keyword>"
python seam.py <command> --help
```

Record pass, fail, or skipped. If a test fails, do not hide it. Either fix within the slice or hand off to `seam-test-hardener`.

### 5. Update Required Docs Only

Update:

- `PROJECT_STATUS.md` when current operating state or active focus changed
- `REPO_LEDGER.md` when stable policy, architecture, routing, safety, or cross-agent protocol changed
- `ROADMAP.md` or `docs/roadmap/*` when planned direction changed
- docs/setup/readme files when user/operator behavior changed

Do not duplicate long history. Use pointer cards such as `see HISTORY#NNN` when appropriate.

### 6. Pre-Closeout Checks

Before handoff to `seam-session-closeout`, run:

```powershell
git diff --name-only
git diff --check
git status --short --branch
```

If runtime code changed, run at least targeted tests. If broad behavior changed, run:

```powershell
python -m pytest test_seam_all/test_seam.py -q
```

## HISTORY_INDEX Rule

Never append, patch, or manually synchronize `HISTORY_INDEX.md` while implementing.

At session end:

1. append `HISTORY.md` with `python -m tools.history.new_entry`
2. regenerate `HISTORY_INDEX.md` with `python -m tools.history.rebuild_index`
3. write a snapshot with `python -m tools.history.write_snapshot`
4. verify continuity

This is handled by `seam-session-closeout`.

## Commit/Push Rule

Do not stage or commit from this skill unless the user explicitly asked for commit/push and `seam-session-closeout` has completed. Use `seam-github-publisher` for commit scope, candidate scans, explicit staging, commit messages, push, and remote alignment checks.

## Forbidden Behavior

- Do not redesign architecture during execution.
- Do not skip repo orientation.
- Do not edit files outside the slice without saying why.
- Do not revert unrelated dirty work.
- Do not use destructive git commands.
- Do not hand-edit `HISTORY_INDEX.md`.
- Do not commit secrets, local `.env` values, private keys, provider links, or chat/session links.
- Do not claim tests passed unless command evidence exists.

## Output Format

```text
Execution Summary: <slice or plan name>

Implemented:
- <path>: <change>

Verification:
- PASS/FAIL/SKIPPED: <command>

Open Issues:
- <none | issue + next action>

Closeout Needed:
- HISTORY.md append: yes/no
- HISTORY_INDEX.md rebuild through rebuild_index: yes/no
- Snapshot: yes/no
- verify_continuity: yes/no
- GitHub publisher needed: yes/no
```

## Validation Prompts

1. Execute a planner slice that adds a CLI command and test.
2. The plan references `archive/code/old_cli.py` as active code. What do you do?
3. Tests fail after a slice. What do you report and what skill handles hardening?
4. The user says "append the index too." Expected: explain index is derived and run `rebuild_index` only after appending history.

The skill fails if it redesigns, edits unrelated files, skips tests, hides failures, reverts other work, or manually edits `HISTORY_INDEX.md`.
