# SOP - Track M P0 Standard Benchmark Completion, DeepSeek Execution Pass

Issued: 2026-05-20
Owner pattern: Codex authors and verifies this SOP; DeepSeek implements the
work on its own branch with parallel workers; Codex reviews and merges only
after independent verification.

Scope: complete the P0 work surfaced by PR #31, "Add Track M - Competitive
Position & Market Entry." PR #31 adds the strategic roadmap, but the P0 work
it names is not complete until SEAM has reproducible, sealed results from the
standard memory benchmark harnesses.

PR #31 state at SOP authoring:

- PR: https://github.com/BlackhatShiftey/Seam/pull/31
- Branch: `claude/remote-control-AD6Di`
- Base: `main`
- State: open draft, mergeable status `CONFLICTING`
- P0 claims in the PR body:
  1. Wire SEAM into `mem0ai/memory-benchmarks`
  2. Run full LoCoMo: 1,540 questions, 4 categories, LLM-as-a-Judge
  3. Run LongMemEval: 500 questions, updates plus abstention
  4. Run BEAM-1M: 100 conversations, 2,000 probing questions

This SOP does not authorize marketing claims. It authorizes benchmark
engineering, methodology capture, BIL sealing, and handback for review.

## Hard Constraints

1. Start from current `main`, not the stale PR #31 branch.
2. Create a new branch named `deepseek/track-m-p0-standard-benchmarks`.
3. Use parallel workers with disjoint file ownership. One coordinator owns git,
   history closeout, benchmark artifacts, and final handback text.
4. Do not commit benchmark output bundles unless the SOP explicitly promotes a
   small fixture as a repo-owned test fixture. Real result bundles stay outside
   git and are referenced by hash/path only in HISTORY.
5. Do not edit `HISTORY.md`, `HISTORY_INDEX.md`, `.seam/`, `PROJECT_STATUS.md`,
   `REPO_LEDGER.md`, `ROADMAP.md`, `archive/`, `docs/archive/`, `build/`,
   `.venv/`, `test_seam/`, or `experimental/webui/`. If continuity closeout is
   required, stop after code/doc changes and return the exact closeout notes for
   Codex to apply.
6. Do not expose API keys, local env values, provider session URLs, private
   conversation links, or benchmark account identifiers. Use ignored local env
   files only.
7. Any benchmark statement must name command, git SHA, adapter, judge, dataset,
   fixture hash, result hash, BIL level, and skipped reason if applicable.
8. Stub judge output is smoke-only. It must never be presented as a competitive
   score.

## Required Read Order

Read these files before touching code:

1. `PROJECT_STATUS.md`
2. `REPO_LEDGER.md`
3. `HISTORY_INDEX.md`
4. `docs/CODE_LAYOUT.md`
5. `docs/DATA_ROUTING.md`
6. `docs/roadmap/COMPETITIVE_ROADMAP.md` from PR #31, or from the local branch
   if PR #31 has been merged by the time DeepSeek starts.
7. `docs/SOP_BENCHMARKABLE_STATE_ROADMAP.md`
8. `docs/SOP_CRITICAL_BENCHMARKABILITY_FIX.md`
9. `docs/ledgers/agents/deepseek.md`

Do not read all of `HISTORY.md`. Use:

```bash
python3 -m tools.history.build_context_pack --entries 217,218,219,220,221 --token-budget 5000 --no-chain
python3 -m tools.history.build_context_pack --refs "Track M|PR #31|LoCoMo|LongMemEval|BEAM|benchmarkable" --latest 12 --token-budget 5000 --no-chain
```

## Pre-flight

Run this before changing files:

```bash
git status --short --branch
git rev-parse --show-toplevel
git fetch origin main pull/31/head:pr-31-track-m || true
gh pr view 31 --json number,title,state,headRefName,baseRefName,mergeable,isDraft,url
python3 -m tools.history.verify_integrity
python3 -m tools.history.verify_routing
python3 -m tools.history.verify_continuity
python3 -m tools.streams.verify_streams
.venv/bin/python -m pytest test_seam_all/ tools/history/test_history_tools.py tools/streams/ tests/ -q
```

Expected baseline may include continuity or streams drift if another local agent
has appended history without closeout. If baseline gates fail before DeepSeek
edits anything, stop and return `SCOPE_LIMIT_HIT: pre_existing_continuity_drift`
with the exact failing lines.

## Worker Topology

### Worker A - PR #31 Rebase And Roadmap Integration

Files:

- `ROADMAP.md`
- `.seam/streams/roadmap/state.md` only if Codex later handles derived closeout
- `docs/roadmap/COMPETITIVE_ROADMAP.md`
- `docs/SOP_DEEPSEEK_PARALLEL_AUDIT_EXECUTION.md`

Tasks:

1. Inspect PR #31 diff against current `main`.
2. Determine whether the Track M roadmap content has already landed.
3. If it has not landed, reapply only the current Track M docs content needed by
   P0. Do not copy stale history entries from the PR branch.
4. If there is a conflict with newer local `PROJECT_STATUS.md`, leave status
   closeout for Codex.
5. Run:
   ```bash
   python3 -m tools.streams.roadmap_parser --emit-state
   python3 -m tools.streams.verify_streams
   ```
   Only if this worker edits `ROADMAP.md`; otherwise skip and report why.

Exit criteria:

- PR #31's Track M intent is represented on the work branch or explicitly
  marked as already present.
- No stale PR #31 history entry is copied into current `HISTORY.md`.

### Worker B - PgVector P0 Upgrade Migration

Files:

- `seam_runtime/vector_adapters.py`
- `tests/audit/test_pgvector_pk_composite.py`
- `seam_runtime/doctor.py` only if migration status needs operator reporting

Problem:

HISTORY#219 found that the #218 composite primary key change breaks existing
pgvector deployments because `CREATE TABLE IF NOT EXISTS` does not modify an
old `PRIMARY KEY (record_id)` table.

Tasks:

1. Write a regression test that creates the old schema:
   ```sql
   create table seam_vector_index (
       record_id text primary key,
       model_name text not null,
       source_hash text not null,
       embedding vector(3) not null
   );
   ```
2. Confirm the test fails before the migration.
3. Add idempotent migration in `PgVectorAdapter.ensure_table()`:
   - inspect the primary key columns from `pg_constraint` and `pg_attribute`
   - if the key is exactly `record_id`, replace it with `(record_id, model_name)`
   - preserve rows
   - do nothing when the key is already `(record_id, model_name)`
4. Add a second test that running `ensure_table()` twice is safe.
5. If `seam doctor` can report pgvector status without leaking DSNs, add a
   generic migration-ready status. Do not include connection strings.

Commands:

```bash
PGVECTOR_TEST_DSN=<ignored-env-value> .venv/bin/python -m pytest tests/audit/test_pgvector_pk_composite.py -q
.venv/bin/python -m pytest tests/audit/test_pgvector_real_adapter.py -q
```

Exit criteria:

- Existing rows survive migration.
- Fresh schema still works.
- Real-adapter tests pass when `PGVECTOR_TEST_DSN` is set.
- Tests skip cleanly without pgvector env.

### Worker C - mem0 Harness Adapter Spike

Files:

- `benchmarks/external/mem0_harness/adapter.py`
- `benchmarks/external/mem0_harness/README.md`
- `tests/audit/test_mem0_harness_adapter_contract.py`
- `pyproject.toml` only if a new optional extra is required

Problem:

Track I built SEAM's own external benchmark runner. PR #31 P0 specifically
requires wiring SEAM into the open-source `mem0ai/memory-benchmarks` harness so
numbers are comparable to the public ecosystem.

Tasks:

1. Inspect the current upstream harness interface from a local clone outside the
   repo. Do not vendor the upstream repo into SEAM.
2. Create a thin SEAM adapter module that exposes the expected harness methods
   while using SEAM's existing runtime APIs.
3. The adapter must support:
   - ingesting multi-turn conversation messages
   - searching by query string
   - returning ranked memory text plus stable IDs and scores
   - optional provenance trace attachment under a SEAM-specific metadata key
4. Add contract tests with a tiny in-repo fixture. The tests must not require
   network access, the upstream harness, or API keys.
5. Document how to run against a real local clone:
   ```bash
   git clone https://github.com/mem0ai/memory-benchmarks ../memory-benchmarks
   .venv/bin/python -m benchmarks.external.mem0_harness.adapter --harness ../memory-benchmarks --dataset locomo --dry-run
   ```

Exit criteria:

- Contract tests prove the adapter shape.
- The README names the exact upstream commit used for any manual run.
- No upstream benchmark code is copied into this repo.

### Worker D - Full LoCoMo Run Path

Files:

- `benchmarks/external/locomo/run.py`
- `benchmarks/external/locomo/README.md`
- `benchmarks/external/common/runner.py`
- `tests/audit/test_locomo_full_dataset_routing.py`

Tasks:

1. Add full-dataset routing without committing the full dataset if the license
   or size makes it inappropriate for git.
2. Add `--dataset-path` or equivalent explicit input so the operator can point
   to a locally downloaded LoCoMo release.
3. Preserve `--quickstart locomo` as the 60-second smoke path.
4. Add a fixture validator that checks the four PR #31 categories are present:
   single-hop, multi-hop, open-domain, temporal.
5. Add a dry-run mode that prints case counts, category counts, fixture hash,
   and estimated judge calls without running the judge.
6. Run one smoke command with stub judge and seal only as BIL-0 or explicit
   stub-allowed BIL-2.

Commands:

```bash
.venv/bin/python -m seam bench external --quickstart locomo --adapter seam --judge stub --format json
.venv/bin/python -m seam bench external locomo --dataset-path <local-locomo-json> --dry-run --format json
```

Exit criteria:

- Full LoCoMo path can be validated without executing a paid judge run.
- Any actual full run uses real judge only with operator-provided ignored env.
- Per-category result breakdown is emitted.

### Worker E - LongMemEval Run Path

Files:

- `benchmarks/external/longmemeval/`
- `tests/audit/test_longmemeval_routing.py`
- `benchmarks/registry/memory_benchmarks.json`
- `benchmarks/external/README.md`

Tasks:

1. Add a LongMemEval adapter scaffold that can validate a local dataset path.
2. Support the five PR #31 categories: information extraction, multi-session
   reasoning, temporal reasoning, knowledge updates, abstention.
3. Implement dry-run validation and fixture hashing.
4. Add tests for category validation and missing-dataset errors.
5. Do not claim a score until a real run is executed and sealed.

Exit criteria:

- `seam bench external --plan` shows LongMemEval with a concrete local command.
- Dry-run validation reports 500 expected questions when pointed at a complete
  local dataset, or a clear error when incomplete.

### Worker F - BEAM-1M Run Path

Files:

- `benchmarks/external/beam/`
- `tests/audit/test_beam_routing.py`
- `benchmarks/registry/memory_benchmarks.json`
- `benchmarks/external/README.md`

Tasks:

1. Add BEAM-1M adapter scaffold and dry-run validator.
2. Validate expected scale metadata: 100 conversations and 2,000 probing
   questions for the 1M track.
3. Refuse BEAM-10M unless the operator explicitly passes a separate flag.
4. Add estimated runtime and judge-call reporting.
5. Do not commit generated large fixtures or result bundles.

Exit criteria:

- BEAM-1M dry-run validates local dataset shape.
- BEAM-10M is explicitly deferred and cannot run accidentally.

### Worker G - Benchmark Publication And BIL Gate

Files:

- `seam_runtime/benchmark_integrity.py`
- `seam_runtime/benchmark_baseline_policy.py`
- `benchmarks/external/README.md`
- `tests/audit/test_track_m_publication_gate.py`

Tasks:

1. Add a publication checklist or gate that refuses competitive publication
   metadata unless the result:
   - uses a non-stub judge
   - names the dataset and fixture hash
   - includes git SHA
   - includes adapter name and retrieval mode
   - includes per-category metrics
   - has a BIL-2 verification result
2. Add tests showing stub judge results are refused for publication metadata.
3. Add docs explaining where local result bundles live and what hashes should
   be copied into HISTORY.

Exit criteria:

- Stub judge cannot accidentally become a publishable Track M result.
- BIL-2 verification remains deterministic.

## Integration Order

The coordinator integrates in this order:

1. Worker B pgvector migration
2. Worker C mem0 harness adapter contract
3. Worker D full LoCoMo dry-run path
4. Worker E LongMemEval dry-run path
5. Worker F BEAM-1M dry-run path
6. Worker G publication/BIL gate
7. Worker A PR #31 roadmap/doc rebase

Rationale: runtime correctness and benchmark command shape should stabilize
before roadmap/status files are updated.

## Required Verification

Run all commands that apply to changed files:

```bash
git diff --check
.venv/bin/python -m pytest tests/audit/test_pgvector_pk_composite.py -q
.venv/bin/python -m pytest tests/audit/test_mem0_harness_adapter_contract.py -q
.venv/bin/python -m pytest tests/audit/test_locomo_full_dataset_routing.py -q
.venv/bin/python -m pytest tests/audit/test_longmemeval_routing.py -q
.venv/bin/python -m pytest tests/audit/test_beam_routing.py -q
.venv/bin/python -m pytest tests/audit/test_track_m_publication_gate.py -q
.venv/bin/python -m pytest test_seam_all/ tools/history/test_history_tools.py tools/streams/ tests/ -q
.venv/bin/python -m py_compile seam.py
.venv/bin/python -m compileall -q seam_runtime benchmarks tools scripts installers
python3 -m tools.history.verify_integrity
python3 -m tools.history.verify_routing
python3 -m tools.history.verify_continuity
python3 -m tools.streams.verify_streams
```

Benchmark smoke commands:

```bash
.venv/bin/python -m seam bench external --plan --format json
.venv/bin/python -m seam bench external --quickstart locomo --adapter seam --judge stub --format json
.venv/bin/python -m seam bench external locomo --dataset-path <local-locomo-json> --dry-run --format json
.venv/bin/python -m seam bench external longmemeval --dataset-path <local-longmemeval-json> --dry-run --format json
.venv/bin/python -m seam bench external beam --track 1m --dataset-path <local-beam-dir> --dry-run --format json
```

If a local dataset is unavailable, report the exact skipped command and the
dataset path/env variable the operator must provide. Do not replace it with
synthetic scores.

## Stop Conditions

Stop and hand back when any of these happens:

- PR #31 conflicts require deleting current main work.
- A benchmark dataset license forbids local use or redistribution and no
  operator-approved download path exists.
- A real judge run would require an API key that is not present in ignored env.
- Full LoCoMo, LongMemEval, or BEAM would exceed the operator's compute/cost
  budget.
- A P0 fix requires editing forbidden continuity files.
- A worker finds that the current code already satisfies an item and can prove
  it with commands; mark it `STALE_ALREADY_DONE` with evidence.

## Handback Format

DeepSeek's final response must include:

```text
===== DEEPSEEK REPORT: TRACK_M_P0 =====
branch: deepseek/track-m-p0-standard-benchmarks
head: <sha>
base: main
pr31_state_seen: <open-draft-conflicting or updated state>

fixed:
- <item id>: <files>, <tests>, <result>

stale_or_already_done:
- <item id>: <evidence>

deferred:
- <item id>: <reason and required operator decision>

benchmark_results:
- quickstart_locomo_stub: <command>, <metrics>, <BIL level or smoke-only>
- full_locomo: <dry-run or real-run result>
- longmemeval: <dry-run or real-run result>
- beam_1m: <dry-run or real-run result>

publication_gate:
- stub_refused_for_publication: <yes/no>
- bil2_verification: <command/result>

verification:
- <command> -> <result>

changed_files:
- <path>

generated_or_local_artifacts_not_committed:
- <path or none>

open_questions:
- <question or none>

codex_review_prompt:
<filled prompt from docs/prompts/DEEPSEEK_TRACK_M_P0_PROMPT.md>
```
