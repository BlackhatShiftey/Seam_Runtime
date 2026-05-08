---
name: seam-skill-sync-auditor
description: Audit SEAM local agent skills and generated adapters for protocol completeness, DeepSeek compliance, stale installed copies, unsafe local modifications, and missing closeout rules. Use when creating, updating, syncing, compiling, applying, or reviewing skills under .opencode, .claude, .codex, skills-library, or future skills/generated outputs. Enforces source/generator separation, no silent overwrite, validation prompts, and rebuild_index after skill changes.
metadata:
  short-description: Audit SEAM skills and adapters before applying them
---

# SEAM Skill Sync Auditor

## Purpose

Make sure SEAM agent skills and generated adapters actually enforce repo protocol before agents rely on them.

This skill audits:

- local OpenCode/DeepSeek skills under `.opencode/skills/`
- Claude skills under `C:\Users\iwana\.claude\skills\`
- Codex skills under `C:\Users\iwana\.codex\skills\`
- source-of-truth skill repos such as `C:\Users\iwana\OneDrive\Documents\skills-library`
- future generated outputs under `skills/generated/<target>/`

## DeepSeek Contract

DeepSeek must not accept a skill as "good enough" unless the skill explicitly covers:

- trigger conditions
- startup reads
- active/archive boundaries
- bounded history loading
- dirty-worktree safety
- secret/session-link safety
- tests or verification
- `HISTORY.md` append
- `HISTORY_INDEX.md` rebuild through `tools.history.rebuild_index`
- snapshot write
- continuity verification
- validation prompts or failure criteria

## Trigger

Use this skill when:

- adding or updating a skill
- comparing installed skill copies
- syncing `.opencode`, `.claude`, `.codex`, or skills-library copies
- reviewing generated agent adapters
- preparing future `seam skills audit`, `compile`, `apply`, `verify`, `optimize`, or `promote` behavior
- checking whether DeepSeek, Qwen, Claude, Codex, Gemini, Cursor, Aider, or another model will follow SEAM rules

## Audit Targets

Known local paths:

```text
C:\Users\iwana\OneDrive\Documents\Codex\.opencode\skills\
C:\Users\iwana\.claude\skills\
C:\Users\iwana\.codex\skills\
C:\Users\iwana\OneDrive\Documents\skills-library\
```

Future generated locations from the Agent Compiler roadmap:

```text
skills/source/*.yaml
skills/generated/<target>/
tools/skills/model_profiles/*.yaml
tools/skills/targets/
```

Do not overwrite installed skills from generated output unless the user explicitly requests apply/promote.

## Audit Checklist

For each skill, verify:

- YAML frontmatter has `name` and `description`
- description clearly says when the skill triggers
- body states purpose and scope
- DeepSeek/model behavior is explicit when relevant
- startup or prerequisite reads are listed
- active and inactive repo paths are distinguished
- `HISTORY.md` full-read prohibition is present for SEAM repo work
- bounded context-pack command is present when history can be needed
- secret/session-link safety is present
- test/verification commands are concrete
- closeout requires append history, rebuild index, write snapshot, verify continuity
- `HISTORY_INDEX.md` is described as derived and never hand-edited
- validation prompts or failure criteria exist
- no real secrets, provider links, local transcript links, or session URLs appear
- no stale archive instructions are treated as current
- commit/push instructions route to `seam-github-publisher` when the skill changes repo state and the user asks to publish

## Sync Rules

### Source vs Installed

Distinguish:

- source skill: editable canonical source
- generated skill: compiler output, review before applying
- installed skill: runtime copy used by an agent

Do not silently copy source over installed or installed over source. Report differences and ask or follow an explicit user command.

### Generated Adapter Rule

Generated files should include:

- source spec hash
- model profile hash
- compiler version
- generated timestamp

Until the compiler exists, manually created skills should still be audited against this skill's checklist.

### Local Modification Rule

If an installed skill differs from generated/source:

- report stale/missing/modified status
- show changed paths
- do not overwrite without explicit apply/promote instruction

## Verification Commands

Skill-only changes:

```powershell
git diff --check
python -m tools.history.verify_integrity
python -m tools.history.verify_continuity
```

Skill changes that alter routing/protocol docs:

```powershell
python -m tools.history.verify_routing
```

Targeted scans:

```powershell
Select-String -Path <candidate-skill> -Pattern 'api[_-]?key|password|token\s*=|secret\s*=|sk-[A-Za-z0-9]|chatgpt.com/share|claude.ai/share|thread_' -CaseSensitive:$false
```

## HISTORY_INDEX Rule

Any skill change is a repo material change.

Correct closeout:

```powershell
python -m tools.history.new_entry ...
python -m tools.history.rebuild_index
python -m tools.history.write_snapshot --agent <agent> --entries <new-id>,<prior-ids> --token-budget 1200
python -m tools.history.verify_integrity
python -m tools.history.verify_continuity
```

Never patch `HISTORY_INDEX.md` manually.

## Output Format

```text
Skill Audit Summary: <scope>

Audited:
- <path>: <status>

Protocol Coverage:
- startup reads: pass/fail
- bounded history: pass/fail
- active/archive routing: pass/fail
- index rebuild rule: pass/fail
- snapshot/continuity: pass/fail
- secrets/session safety: pass/fail

Differences:
- <none | path + summary>

Actions:
- <created/updated/review-only/apply-needed>

Verification:
- PASS/FAIL/SKIPPED: <command>
```

## Validation Prompts

1. Audit `.opencode/skills/seam-session-closeout/SKILL.md` for DeepSeek compliance.
2. Compare a generated Claude skill with the installed `C:\Users\iwana\.claude\skills\seam-repo-navigator\SKILL.md`.
3. A skill says "append HISTORY_INDEX.md." Expected: fail the audit and require `rebuild_index`.
4. A generated adapter lacks secret/session-link safety. Expected: fail and block promotion.
5. A skill says "commit everything with git add ." Expected: fail unless it also requires candidate audit, exclusions, and explicit user intent.

The skill fails if it overwrites installed skills silently, misses the index rebuild rule, ignores generated/source separation, or approves a skill without continuity and secret-safety coverage.
