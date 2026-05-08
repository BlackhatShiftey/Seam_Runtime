---
name: seam-test-hardener
description: Diagnose and harden SEAM tests after implementation or CI failures. Use when tests fail, coverage must be added, CI paths drift, benchmark gates need verification, or DeepSeek must prove a change works. Enforces targeted reproduction, minimal fixes, active test layout, artifact routing, no stale archive assumptions, honest failure reporting, and closeout through HISTORY.md append plus HISTORY_INDEX.md rebuild.
metadata:
  short-description: Fix and strengthen SEAM tests without hiding failures
---

# SEAM Test Hardener

## Purpose

Turn failing, missing, or weak verification into reliable SEAM test evidence.

This skill is not a general refactor tool. It changes tests and test-adjacent code only to prove behavior, repair real regressions, or preserve CI/release gates.

## DeepSeek Contract

DeepSeek must reproduce before fixing whenever possible.

If a failure cannot be reproduced locally, say so and record the exact command, environment limit, or missing dependency. Do not invent a pass.

## Trigger

Use this skill when:

- a test fails locally or in CI
- implementation needs focused coverage
- CI path/test command is stale
- a benchmark gate or release check must be validated
- a refactor changes shared behavior
- a user asks whether the change is actually safe

## Active Test Baseline

Primary regression suite:

```text
test_seam_all/test_seam.py
```

History tool tests:

```text
tools/history/test_history_tools.py
```

Generated per-test SQLite files should route into:

```text
test_seam/
```

Root-level `test_seam_*.db` files are not desired.

## Workflow

### 1. Reproduce Or Establish Baseline

Start with the smallest failing or relevant command.

Examples:

```powershell
python -m pytest test_seam_all/test_seam.py -q -k "<keyword>"
python -m pytest test_seam_all/test_seam.py tools/history/test_history_tools.py -q
python -m py_compile seam_runtime\<module>.py test_seam_all\test_seam.py
python -m tools.history.verify_integrity
python -m tools.history.verify_routing
python -m tools.history.verify_continuity
```

For CI failures, inspect the exact CI command/path before changing code. Stale path failures should fix CI/docs/test layout together.

### 2. Classify The Failure

Classify as one of:

- implementation bug
- test expectation drift
- stale path or moved file
- environment/dependency issue
- flaky timing/resource issue
- benchmark or fixture mismatch
- protocol/history/routing failure

Do not weaken a test until you know which class applies.

### 3. Fix The Smallest Real Cause

Preferred order:

1. fix implementation if behavior is wrong
2. update test expectation if behavior intentionally changed and docs/plan support it
3. repair test setup or artifact path if infrastructure is stale
4. isolate flaky/resource-heavy checks behind existing guarded scripts

Do not add sleeps, broad skips, or loose assertions unless the reason is explicit and documented.

### 4. Add Coverage Where Risk Exists

Add or update tests when:

- a public CLI/API behavior changed
- storage schema or persistence changed
- retrieval/ranking/benchmark behavior changed
- history/routing/protocol code changed
- a regression was fixed

Keep tests targeted. Broaden only when shared behavior changed.

### 5. Route Artifacts Correctly

Keep generated artifacts out of root and out of git unless deliberately promoted.

Expected local sinks:

- `test_seam/` for per-test SQLite artifacts
- ignored benchmark run folders for generated benchmark outputs
- operator Documents folders for local benchmark archives when using store scripts

### 6. Verify The Repair

Run the focused command first, then broader gates as needed.

For runtime changes:

```powershell
python -m pytest test_seam_all/test_seam.py -q
```

For history/routing changes:

```powershell
python -m tools.history.verify_integrity
python -m tools.history.verify_routing
python -m tools.history.verify_continuity
```

For benchmark claims:

```powershell
python seam.py benchmark diff <run-a> <run-b>
python seam.py benchmark gate <bundle>
```

Do not claim benchmark improvement without benchmark evidence.

## HISTORY_INDEX Rule

Test hardening that changes repo files requires normal closeout:

```powershell
python -m tools.history.new_entry ...
python -m tools.history.rebuild_index
python -m tools.history.write_snapshot --agent <agent> --entries <new-id>,<prior-ids> --token-budget 1200
python -m tools.history.verify_continuity
```

`HISTORY_INDEX.md` is derived. Never add entries to it by hand.

## Output Format

```text
Test Hardening Summary: <short name>

Failure/Baseline:
- <command>: <result>

Cause:
- <classification and evidence>

Changed:
- <file>: <change>

Verification:
- PASS/FAIL/SKIPPED: <command>

Residual Risk:
- <none | remaining issue>

Closeout:
- history append/rebuild snapshot required: <yes/no>
```

## Validation Prompts

1. A CI job fails because it still runs `Test-Seam-All/test_seam.py`. What should change?
2. A runtime patch changes MCP dispatch validation. What tests should be added?
3. A benchmark claim improves query exactness. What proof is required?
4. A model says it "updated the index" by editing `HISTORY_INDEX.md`. Expected: reject, rebuild from `HISTORY.md`.

The skill fails if it hides failing tests, weakens assertions without evidence, leaves root test DB sprawl, makes benchmark claims without gates, or hand-edits `HISTORY_INDEX.md`.
