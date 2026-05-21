# SOP - Track M P1 Real Benchmark Runs

Issued: 2026-05-20
Owner pattern: the implementation agent runs real datasets and real judges on a
fresh branch; Codex reviews artifacts, hashes, gates, and merge readiness.

Scope: after Track M P0 lands, run the standard external memory benchmarks with
operator-provided datasets and real judges. This SOP is for evidence production,
not new benchmark plumbing.

## Goal

Produce auditable real-run evidence for:

1. LoCoMo full dataset with SEAM adapter and a real judge.
2. LongMemEval full dataset dry-run validation, then real-run only after a
   judge adapter exists.
3. BEAM-1M full dataset dry-run validation, then real-run only after a judge
   adapter exists.
4. Optional mem0 and Zep comparator runs when local credentials and dependencies
   are present.
5. BIL-2 sealed bundles and verification reports for any real result.

Stub judge results remain smoke-only and must not be used as competitive
claims.

## Branch

Create:

```bash
git switch main
git pull --ff-only origin main
git switch -c deepseek/track-m-p1-real-benchmark-runs
```

## Required First Reads

Read in order:

1. `PROJECT_STATUS.md`
2. `REPO_LEDGER.md`
3. `HISTORY_INDEX.md`
4. `docs/CODE_LAYOUT.md`
5. `docs/DATA_ROUTING.md`
6. `docs/SOP_TRACK_M_P1_REAL_BENCHMARK_RUNS.md`
7. `docs/SOP_BENCHMARKABLE_STATE_ROADMAP.md`
8. `docs/SOP_CRITICAL_BENCHMARKABILITY_FIX.md`
9. `benchmarks/external/README.md`
10. `docs/ledgers/agents/deepseek.md`

Do not read all of `HISTORY.md`. Use bounded context packs only.

## Inputs Required From Operator

The agent must not download datasets into the repo. The operator provides local
paths outside git:

- `LOCOMO_DATASET_PATH`: full LoCoMo JSON.
- `LONGMEMEVAL_DATASET_PATH`: full LongMemEval JSON.
- `BEAM_1M_DATASET_PATH`: BEAM-1M dataset directory.
- `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`: real judge credential.
- Optional comparator credentials: `MEM0_API_KEY`, `ZEP_API_KEY`, or local
  service endpoints, depending on the comparator adapter.

If an input is missing, run the relevant dry-run or smoke validator and report
the missing variable/path. Do not fake a score.

## Hard Rules

1. Do not commit downloaded datasets, result bundles, API responses, local
   `.env` values, SQLite test artifacts, provider session URLs, or private
   conversation links.
2. Store real result bundles outside the repo, then record only command, path
   placeholder, result hash, fixture hash, BIL level, and verification status in
   the handback.
3. Use `--judge claude` or `--judge openai` for competitive evidence. `--judge
   stub` is smoke-only.
4. Every real result must be sealed with `seam bench seal --level BIL-2` and
   verified with `seam bench verify`.
5. A result is not publication-ready unless
   `validate_publication_readiness(...)` receives a passing BIL-2 verification
   report and returns `ready: true`.
6. If a full runner is not implemented yet, do not invent one during this run.
   Return the exact blocking implementation gap and stop that benchmark at
   dry-run validation.

## Pre-flight

```bash
git status --short --branch
python3 -m tools.history.verify_integrity
python3 -m tools.history.verify_routing
python3 -m tools.history.verify_continuity
python3 -m tools.streams.verify_streams
.venv/bin/python -m pytest test_seam_all/ tools/history/test_history_tools.py tools/streams/ tests/ -q
.venv/bin/python -m seam bench external --plan --format json
.venv/bin/python -m seam bench external --quickstart locomo --adapter seam --judge stub --format json
```

Acceptance for quickstart smoke: `context_recall_mean` must be greater than
`0.5`. If it is `0.0`, stop and report P0 regression.

## Runbook

### LoCoMo

Dry-run:

```bash
.venv/bin/python -m seam bench external locomo \
  --dataset-path "$LOCOMO_DATASET_PATH" \
  --dry-run --format json
```

Real run:

```bash
.venv/bin/python -m seam bench external locomo \
  --dataset-path "$LOCOMO_DATASET_PATH" \
  --adapter seam \
  --judge claude \
  --output /tmp/seam-track-m/locomo-seam-claude.json \
  --format json
```

Use `--judge openai` only if that is the available real judge credential.

Seal and verify:

```bash
.venv/bin/python -m seam bench seal /tmp/seam-track-m/locomo-seam-claude.json \
  --level BIL-2 \
  --output /tmp/seam-track-m/locomo-seam-claude.bil2.json \
  --format json
.venv/bin/python -m seam bench verify /tmp/seam-track-m/locomo-seam-claude.bil2.json \
  --format json
```

### LongMemEval

Dry-run:

```bash
.venv/bin/python -m seam bench external longmemeval \
  --dataset-path "$LONGMEMEVAL_DATASET_PATH" \
  --dry-run --format json
```

If full execution still reports "dry-run validation is supported" only, record
that implementation gap and do not fabricate a result.

### BEAM-1M

Dry-run:

```bash
.venv/bin/python -m seam bench external beam \
  --track 1m \
  --dataset-path "$BEAM_1M_DATASET_PATH" \
  --dry-run --format json
```

BEAM-10M remains deferred unless an operator explicitly approves a separate
infrastructure plan.

### Comparator Runs

Only run comparators when the local dependency and credentials are present.
Report missing extras or env vars exactly.

```bash
.venv/bin/python -m benchmarks.external.mem0_harness.adapter --dry-run
```

Do not commit upstream harness clones or comparator-generated stores.

## Publication Gate

For any real result and BIL-2 verification report, run a local Python check:

```bash
.venv/bin/python - <<'PY'
import json
from seam_runtime.benchmark_integrity import (
    load_json_payload,
    validate_publication_readiness,
    verify_benchmark_bundle,
)

result_path = "/tmp/seam-track-m/locomo-seam-claude.json"
bundle_path = "/tmp/seam-track-m/locomo-seam-claude.bil2.json"
result = load_json_payload(result_path)
bundle = load_json_payload(bundle_path)
verification = verify_benchmark_bundle(bundle)
report = validate_publication_readiness(
    result,
    git_sha="<HEAD_SHA>",
    fixture_hash="<DRY_RUN_FIXTURE_HASH>",
    dataset_name="locomo-full",
    bil_verification=verification,
)
print(json.dumps(report, indent=2, sort_keys=True))
raise SystemExit(0 if report["ready"] else 1)
PY
```

Replace placeholders before running. Do not put secrets in the snippet.

## Required Verification Before Handback

```bash
git diff --check
.venv/bin/python -m pytest tests/audit/test_locomo_adapter_evidence_text.py -q
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

## Final Report Format

```text
===== DEEPSEEK REPORT: TRACK_M_P1_REAL_RUNS =====
branch: deepseek/track-m-p1-real-benchmark-runs
head: <sha>
base: main

inputs_seen:
- locomo_dataset: <present/missing, path placeholder only>
- longmemeval_dataset: <present/missing, path placeholder only>
- beam_1m_dataset: <present/missing, path placeholder only>
- real_judge_env: <ANTHROPIC_API_KEY/OPENAI_API_KEY/missing>

benchmark_results:
- quickstart_locomo_stub: <command, context_recall_mean, smoke-only>
- locomo_full: <command, scores, fixture_hash, result_hash, BIL-2 verify>
- longmemeval: <dry-run/real-run status>
- beam_1m: <dry-run/real-run status>
- comparators: <mem0/zep run or missing prerequisites>

publication_gate:
- <result>: <ready true/false, blocked_by>

verification:
- <command> -> <result>

changed_files:
- <path or none>

artifacts_not_committed:
- <path placeholder, hash, reason>

deferred:
- <item, reason, required operator decision>

open_questions:
- <question or none>
```
