---
name: seam-roadmap-ledger-updater
description: Decide and apply the correct SEAM documentation update across ROADMAP.md, PROJECT_STATUS.md, REPO_LEDGER.md, docs/roadmap, docs/ledgers, and HISTORY.md. Use when work changes project direction, current operating state, stable policy, architecture, routing, safety rules, durable workflows, or agent protocol. Enforces pointer-card discipline, no duplicated chronology, valid history topics, and rebuild_index after history append.
metadata:
  short-description: Update SEAM roadmap/status/ledger docs in the right place
---

# SEAM Roadmap Ledger Updater

## Purpose

Keep SEAM's durable docs truthful without duplicating history or mixing current instructions with stale archive content.

This skill decides where a fact belongs:

- direction
- current state
- stable architecture/policy
- route/audit facts
- chronological history

## DeepSeek Contract

DeepSeek must not scatter the same prose across multiple docs.

Use one canonical home for each fact, then pointer cards where useful. If unsure whether a fact is stable policy or session chronology, put detailed chronology in `HISTORY.md` and only add a concise pointer to durable docs.

## Trigger

Use this skill when:

- a feature changes project direction
- the active focus or operating state changes
- stable architecture or policy changes
- route classifications or audit behavior changes
- roadmap items are added, completed, deferred, or reprioritized
- agent protocol or local skill policy changes
- a user asks "is this in the roadmap", "add this to the ledger", or "where does this direction live"

## Documentation Map

Use these homes:

- `ROADMAP.md`: planned direction, tracks, future work, priorities
- `docs/roadmap/*`: detailed roadmap workstream files
- `PROJECT_STATUS.md`: current operating state, stable surfaces, active focus, resume point
- `REPO_LEDGER.md`: stable repo-wide policy, architecture decisions, routing policy, runtime safety, benchmark publication policy, cross-agent protocol
- `docs/ledgers/*`: stable route/topic facts useful for search
- `HISTORY.md`: append-only chronology of material changes
- `HISTORY_INDEX.md`: derived compact index, rebuilt by tool only
- `.seam/snapshots/*`: bounded handoff packs, written by tool only

Do not use archived docs as current instructions unless the task explicitly revives and rewrites them.

## Decision Rules

### Update PROJECT_STATUS.md When

- current operating state changed
- active focus changed
- resume point changed
- stable user-facing surface changed
- next agent should believe something new on startup

### Update REPO_LEDGER.md When

- stable policy changed
- architecture invariant changed
- storage/source-of-truth decision changed
- active/archive routing policy changed
- runtime service safety rule changed
- benchmark publication rule changed
- cross-agent protocol changed
- repo licensing/protection/contribution boundary changed

### Update ROADMAP.md Or docs/roadmap When

- planned workstream is added
- scope/track/priority changes
- feature moves from idea to planned work
- completed planned work should be marked or linked

### Update docs/ledgers When

- route facts need durable search
- classification lifecycle changes
- topic-level audit facts should be found without reading session chronology

### Update HISTORY.md Always When State Changed

Every material repo change needs one append-only history entry, followed by index rebuild and snapshot.

## Pointer Discipline

Use concise pointers:

```text
see HISTORY#141
```

Do not copy long history bodies into status, roadmap, or ledger docs.

Do not rewrite old history to make the timeline cleaner. Add a new entry with `supersedes`.

## Routing Changes

If changing `tools/history/routing_manifest.json` or route ledgers:

1. preserve lifecycle fields
2. mark moved/retired routes instead of erasing the only explanation
3. update the relevant `docs/ledgers/*` file when stable route facts changed
4. append history
5. rebuild index
6. write snapshot
7. run:

```powershell
python -m tools.history.verify_routing
python -m tools.history.verify_continuity
```

## HISTORY_INDEX Rule

Never manually update `HISTORY_INDEX.md`.

Correct order:

```powershell
python -m tools.history.new_entry --agent <agent> --status done --topics <valid-topics> --refs <refs> --supersedes <id> --body "<body>"
python -m tools.history.rebuild_index
python -m tools.history.write_snapshot --agent <agent> --entries <new-id>,<prior-ids> --token-budget 1200
python -m tools.history.verify_integrity
python -m tools.history.verify_continuity
```

Use only valid topics from `AGENTS.md`.

## Verification

For doc-only changes:

```powershell
git diff --check
python -m tools.history.verify_integrity
python -m tools.history.verify_continuity
```

For routing/ledger/classification changes:

```powershell
python -m tools.history.verify_routing
```

For docs that mention commands or test paths, verify the paths exist.

## Output Format

```text
Documentation Routing Summary: <short name>

Fact Placement:
- ROADMAP.md: <yes/no, reason>
- PROJECT_STATUS.md: <yes/no, reason>
- REPO_LEDGER.md: <yes/no, reason>
- docs/ledgers: <yes/no, reason>
- HISTORY.md: <yes, entry required>

Changed:
- <file>: <change>

Verification:
- PASS/FAIL/SKIPPED: <command>

Index/Snapshot:
- HISTORY_INDEX.md rebuilt with rebuild_index: <yes/no>
- Snapshot written: <path>
```

## Validation Prompts

1. "Add agent compiler to the roadmap." Expected: roadmap workstream, status if active focus changes, history closeout.
2. "Add temporal chaining of facts to the ledger." Expected: ledger if stable protocol, history for chronology, verify continuity.
3. "Mark a route retired." Expected: manifest lifecycle, route ledger if stable facts changed, verify_routing, rebuild index.
4. "Update HISTORY_INDEX.md with the new entry." Expected: refuse manual edit; use `rebuild_index`.

The skill fails if it duplicates long chronology, leaves status stale, changes route facts without `verify_routing`, uses invalid history topics, or hand-edits `HISTORY_INDEX.md`.
