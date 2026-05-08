---
name: seam-implementation-planner
description: Turns SEAM architecture output from seam-architect into an exact, sliced build plan with concrete file paths, function signatures, test commands, history closeout steps, rollback points, and derived-index rules. Use this skill after seam-architect produces a design, when the user asks to implement, build, or execute an architecture. Optimized for DeepSeek/OpenCode and any capable agent model executing inside the SEAM repo.
metadata:
  short-description: Convert SEAM architecture into executable build slices
---

# SEAM Implementation Planner

## Purpose

Turn an architecture design (typically from `seam-architect`) into a concrete, ordered build plan that an implementation agent can execute without guessing.

You are a planner, not an architect. You take a validated architecture and break it into verifiable slices. You do not redesign. If the architecture is missing facts or interfaces, flag the gap and stop — do not fill it with guesses.

## Model Target

This skill is model-agnostic for execution models. Use whichever capable model is running the implementation session (DeepSeek V4 Pro, Claude, etc.). The output must be clear enough for any implementation agent to follow.

Recommended settings:
- temperature: low
- thinking: enabled if available (helps with sequencing dependencies)
- purpose: precise planning, dependency ordering, test wiring

## Skill Chain

This skill sits in the local DeepSeek/OpenCode chain:

```text
seam-repo-navigator -> seam-architect -> seam-implementation-planner -> seam-implementation-executor -> seam-test-hardener -> seam-session-closeout -> seam-github-publisher when commit/push is requested
```

Do not use this planner as a substitute for repo orientation or session closeout.

## When To Use

Use this skill when:
- `seam-architect` has produced a design and the user says "build it", "implement this", "execute the plan", or "let's start"
- the user gives you architecture output directly and asks for a build plan
- the task is breaking down a multi-file change into ordered slices
- the user asks for a step-by-step implementation sequence

Do NOT use this skill when:
- the architecture hasn't been validated yet (defer to `seam-architect` first)
- the task is a single-file, single-function change (just do it)
- the user is only asking a question about the architecture

## Startup Context

Before planning, confirm `seam-repo-navigator` orientation has run. If not, do it first.

Read or verify the active repo sources required by `AGENTS.md`:

1. `PROJECT_STATUS.md`
2. `REPO_LEDGER.md`
3. `HISTORY_INDEX.md`
4. `docs/CODE_LAYOUT.md`
5. `docs/DATA_ROUTING.md` when the task touches history, ledgers, maintenance records, routing, context budget, auditability, snapshots, or protocol

Never bulk-read all of `HISTORY.md`. Use bounded history only when needed:

```powershell
python -m tools.history.build_context_pack --topics <tags> --latest 3 --token-budget 1200
python -m tools.history.build_context_pack --route <route> --token-budget 1200
```

## Prerequisites

Before planning, verify you have or gather:

1. The architecture output (from `seam-architect` or equivalent) including:
   - Goal statement
   - Current repo facts
   - Hard invariants
   - Proposed design with interfaces
   - Implementation slices (high-level)
   - Verification plan

2. Live repo state:
   ```powershell
   git status --short --branch
   git log --oneline -5
   ```

3. Any referenced files actually exist at the claimed paths.

If the architecture is missing interfaces, data flow, or verification, **stop and flag the gap**. Do not invent missing pieces.

## Planning Workflow

### 1. Validate The Architecture Input

Quick consistency check:

- Are all referenced modules in active paths (not archive)?
- Do the interfaces name real file paths?
- Are the invariants consistent with current `REPO_LEDGER.md`?
- Does the verification plan reference real test files?

Flag any discrepancy before planning.

### 2. Expand Slices Into Build Steps

For each architecture slice, produce an exact build step. A build step must include:

```
Step N: <slice name>
Goal: <what this step achieves, verifiable>
Files:
  - create: <path>  (new file)
  - modify: <path>:<line-range>  (existing file, what changes)
  - verify: <path>  (test file)
  - docs: <path>    (if docs change)
Dependencies: <steps that must complete first>
Implementation:
  <concrete what-to-write, function signatures, class outlines, imports>
Test:
  <exact test command to run after this step>
  Expected: <pass / specific output>
Rollback:
  <how to undo this step if it fails>
Done when:
  <verifiable condition>
History:
  <whether this step requires a HISTORY.md entry, and what topics>
```

### 3. Order By Dependency

Sort slices so that:
- No step references code created in a later step.
- Shared interfaces/modules come before consumers.
- Storage schema comes before storage access code.
- Tests can be written alongside or immediately after their target code.
- History/snapshot closeout is the final step.

Mark any parallelizable steps.

### 4. Wire Verification

Every step that produces code must include a test command.

After all steps, include the full verification suite:

```powershell
python -m pytest test_seam_all/test_seam.py -q
python -m tools.history.verify_integrity
python -m tools.history.verify_continuity
```

If the change touches routing:

```powershell
python -m tools.history.verify_routing
```

### 5. Plan Closeout

The final steps must cover:

```powershell
# Append HISTORY.md entry with tools.history.new_entry
python -m tools.history.new_entry ...
python -m tools.history.rebuild_index
python -m tools.history.write_snapshot --agent <agent> --entries <new-entry-id>,<relevant-prior-ids> --token-budget 1200
python -m tools.history.verify_integrity
python -m tools.history.verify_continuity
```

Plus any ledger/status updates the architecture specified.

`HISTORY_INDEX.md` is derived state. Never plan a manual edit or append to `HISTORY_INDEX.md`; the only valid update is `python -m tools.history.rebuild_index` after the `HISTORY.md` append.

### 6. Identify Checkpoints

Mark 2-4 natural checkpoints where the user can:
- Verify progress so far
- Decide to continue or pause
- Commit partial work safely through `seam-github-publisher`

## Output Format

Use this exact structure:

```
Build Plan: <short name>

Architecture Reference: <link to architecture output or summary>

Prerequisites Check:
- Architecture completeness: <ok / gaps>
- Repo state: <clean / dirty>, branch <name>
- Active paths verified: <yes / no>

Build Steps:
1. <step name>
   Goal: ...
   Files:
     - create: ...
     - modify: ...
     - verify: ...
   Dependencies: none / step N
   Implementation: ...
   Test: ...
   Rollback: ...
   Done when: ...
   History: ...

2. <step name>
   ...

(... all steps ...)

Checkpoints:
- After step N: <what should work, how to verify>
- After step M: <what should work, how to verify>

Full Verification:
python -m pytest test_seam_all/test_seam.py -q
python -m tools.history.verify_integrity
python -m tools.history.verify_continuity
python -m tools.history.verify_routing  (if routes changed)

Closeout:
- HISTORY.md: <entry topics>
- HISTORY_INDEX.md: rebuild with python -m tools.history.rebuild_index; no manual edits
- Snapshot: write
- REPO_LEDGER.md: <update needed? yes/no, what>
- PROJECT_STATUS.md: <update needed? yes/no, what>
- GitHub: <not requested / use seam-github-publisher, commit scope>

Risks:
- <risk>: <mitigation>

Estimated Steps: N
Parallelizable: steps X, Y
Total files touched: N
```

## Behavior Rules

Do not:
- redesign the architecture (flag gaps, don't fill them)
- skip test wiring for any code-producing step
- propose steps that depend on code from a later step
- create steps without rollback instructions
- plan archive-path changes unless the architecture explicitly retires/revives archive material
- forget history closeout
- manually edit or append `HISTORY_INDEX.md`

Do:
- flag missing interfaces immediately
- use exact file paths from the repo, not guesses
- match existing test layout (`test_seam_all/test_seam.py` or modular test files)
- keep steps small and independently verifiable
- note which steps can run in parallel
- include the full verification suite as the final validation gate
- require `python -m tools.history.rebuild_index` after every material history append

## Example

Given a simple architecture for adding a new CLI command `seam.py status`, the output would look like:

```
Build Plan: seam-status-command

Architecture Reference: Architecture: CLI Status Command (from seam-architect session)

Prerequisites Check:
- Architecture completeness: ok
- Repo state: clean, branch main
- Active paths verified: yes

Build Steps:
1. Add status command handler
   Goal: Create seam_runtime/status.py with a get_status() function
   Files:
     - create: seam_runtime/status.py
   Dependencies: none
   Implementation: Write get_status() returning dict with branch, remote, cleanliness, last-commit
   Test: python -c "from seam_runtime.status import get_status; print(get_status())"
   Rollback: delete seam_runtime/status.py
   Done when: function imports and returns non-empty dict
   History: no (internal step, covered by final entry)

2. Wire into seam.py CLI
   Goal: Add "status" subcommand to seam.py argparse
   Files:
     - modify: seam.py: add subparser and handler call
   Dependencies: step 1
   Implementation: Add "status" to subparsers, call get_status() and format output
   Test: python seam.py status
   Rollback: remove the subparser block from seam.py
   Done when: python seam.py status prints formatted status output
   History: no

3. Closeout
   Goal: Record change in history and verify integrity
   Files:
     - modify: HISTORY.md (append)
     - regenerate: HISTORY_INDEX.md with python -m tools.history.rebuild_index
     - create: .seam/snapshots/<timestamp>.json
   Dependencies: step 2
   Implementation: Append history entry with tools.history.new_entry, rebuild index with tools.history.rebuild_index, write snapshot, run verify
   Test: python -m tools.history.verify_continuity
   Rollback: revert HISTORY.md to prior HEAD state
   Done when: all verify commands pass
   History: entry covering steps 1-2
```

## Validation Prompts

1. Given the architecture for a new compression codec, produce a build plan.
2. Take the model-routing architecture from seam-architect and plan implementation.
3. The architecture has a gap — the storage interface is undefined. What do you do? (Expected: stop, flag the gap, don't guess.)

4. The user says "append the index." What do you do? (Expected: refuse manual index edit; append `HISTORY.md` then run `rebuild_index`.)

The skill fails if it:
- invents missing architecture rather than flagging gaps
- produces steps that can't be executed independently
- skips test commands
- forgets history closeout
- creates circular dependencies between steps
- hand-edits `HISTORY_INDEX.md` instead of planning `rebuild_index`
