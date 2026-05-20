# SOP - Track K BIL Phase 1 Repair Handoff

Issued: 2026-05-20 after the DeepSeek BIL Phase 1 repair audit.

Purpose: preserve the corrected operating contract for Benchmark Integrity
Level Phase 1 and give the next agent a bounded checklist for follow-up work.

## Current State

Track K BIL Phase 1 is implemented for BIL-0 through BIL-2:

- `seam bench inspect` reports BIL-0 for raw benchmark result files.
- `seam bench seal --level BIL-1|BIL-2` writes deterministic benchmark
  bundles.
- `seam bench verify` checks the result hash, BIL-2 input-manifest hash, and
  BIL-2 manifest/result consistency.
- Stub-judge results cannot be sealed above BIL-0 unless the operator passes
  `--allow-stub-seal`.
- BIL result hashes are computed from a stable projection that excludes
  volatile timing fields while leaving those fields in the sealed payload.

## Repaired Findings

1. BIL-2 result hashes were nondeterministic across identical quickstart runs
   because volatile fields were hashed. The fixed hash input excludes
   `run_started_at`, `elapsed_seconds`, `created_at`,
   `retrieval_latency_ms`, and `answer_latency_ms`.
2. Stub-judge seal refusal raised a raw traceback through the CLI. The fixed
   CLI exits non-zero with a concise operator message.
3. Active quickstart documentation omitted `--allow-stub-seal`; the documented
   command now matches the policy.
4. Automatic benchmark baseline discovery did not pass the current candidate
   path to the resolver, creating a self-baseline risk. The CLI now excludes
   the current candidate when auto-selecting a baseline.
5. Holdout exclusion used string-prefix matching, which could exclude sibling
   directories such as `holdout-extra`. The resolver now checks path parts.
6. An unused `_stable_timing()` helper and its audit test were removed because
   they did not stabilize real benchmark latency fields.

## Verification Baseline

Before handing off or committing future work in this area, run:

```bash
.venv/bin/python -m pytest test_seam_all/test_benchmark_integrity.py tests/audit/test_baseline_policy.py tests/audit/test_bench_stub_seal_gate.py tests/audit/test_benchmark_reproducibility.py -q
.venv/bin/python -m pytest test_seam_all/ tools/history/ tools/streams/ tests/ -q
.venv/bin/python -m py_compile seam.py
.venv/bin/python -m compileall -q seam_runtime benchmarks tools scripts installers
git diff --check
```

Expected as of this handoff:

- Focused BIL/baseline/stub/reproducibility tests: 24 passed.
- Full active suite: 429 passed, 3 skipped, 3 subtests passed.
- `py_compile`, `compileall`, and `git diff --check`: pass.

Benchmark smoke:

```bash
.venv/bin/python -m seam bench external --quickstart locomo --adapter seam --judge stub --output /tmp/seam-locomo-bil-result.json
.venv/bin/python -m seam bench seal /tmp/seam-locomo-bil-result.json --level BIL-2 --output /tmp/seam-locomo-bil-no-allow.json
.venv/bin/python -m seam bench seal /tmp/seam-locomo-bil-result.json --level BIL-2 --allow-stub-seal --output /tmp/seam-locomo-bil-bundle.json
.venv/bin/python -m seam bench verify /tmp/seam-locomo-bil-bundle.json --format json
.venv/bin/python -m seam bench inspect /tmp/seam-locomo-bil-bundle.json --format json
```

Expected:

- The no-allow seal command exits non-zero with
  `stub judge cannot be sealed above BIL-0; pass allow_stub_seal=True to override`.
- The allow seal, verify, and inspect commands exit zero.
- BIL-2 verify reports 4/4 checks passed.

## Deferred Work

Do not silently implement these in a repair patch:

- BIL-3 signing identity.
- BIL-4 audit-chain linkage.
- BIL-5 transparency-log target.
- BIL-6 independent rerun policy.
- Real benchmark latency stabilization. If this becomes required, wire it into
  `benchmarks/external/common/runner.py` or adapter execution paths and prove
  it changes emitted benchmark results, not just a private helper.
- CI baseline-source policy beyond local auto-selection. The resolver is local
  and intentionally returns `None` when no reachable public baseline exists.

## Next-Agent Rules

- Do not read all of `HISTORY.md`; use `HISTORY_INDEX.md` and context packs.
- Keep generated benchmark outputs in `/tmp` or operator storage, not in git.
- Do not call live LLM judges during local repair verification.
- If changing BIL hash inputs, add a reproducibility or tamper-detection test
  first and confirm RED before changing `seam_runtime/benchmark_integrity.py`.
- If changing `seam benchmark gate` baseline behavior, test both explicit
  `--baseline` and auto-baseline paths.
