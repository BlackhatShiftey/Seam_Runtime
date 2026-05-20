# DeepSeek Batch Prompt — Track K BIL Phase 1

Paste this prompt verbatim into the DeepSeek session. The canonical SOP
is `docs/SOP_TRACK_K_BIL_PHASE1_DEEPSEEK.md`. DeepSeek reads it once,
executes BIL1 → BIL2 → BIL3 → BIL4 in sequence on a single working tree,
emits ITEM_SUCCESS blocks for all completed items at the end, and STOPs
without staging, committing, or pushing.

---

You are executing the **Track K BIL Phase 1** SOP at
`docs/SOP_TRACK_K_BIL_PHASE1_DEEPSEEK.md`.

Goal: implement the first Benchmark Integrity Level slice for SEAM:
BIL-0 inspection, BIL-1 result hashing, and BIL-2 result hashing plus
deterministic input manifest hashing.

Hard rules:

1. Read `docs/SOP_TRACK_K_BIL_PHASE1_DEEPSEEK.md` from top to bottom once
   before touching code.
2. Do not read all of `HISTORY.md`. Use bounded context only if needed.
3. Failing tests first. Confirm RED, then implement the smallest fix.
4. Do NOT edit `HISTORY.md`, `HISTORY_INDEX.md`, `PROJECT_STATUS.md`,
   `REPO_LEDGER.md`, `.seam/`, `.github/workflows/`, `archive/`,
   `docs/archive/`, `build/`, `.venv/`, `test_seam/`, or
   `experimental/webui/`.
5. Do NOT stage, commit, or push. Codex reviews and commits.
6. Do NOT call live LLM providers. Use only the stub judge smoke.
7. Do NOT implement BIL-3 signing, BIL-4 audit-chain linkage, BIL-5
   transparency logs, or BIL-6 independent reruns.
8. Do NOT promote LLM judge scores into deterministic benchmark gates.
   BIL seals the evidence file only.

Pre-flight:

```bash
git status --short
git branch --show-current
git log --oneline -1
python -m pytest test_seam_all/ tools/history/ tools/streams/ tests/ -q
python -m tools.history.verify_integrity
python -m tools.history.verify_routing
python -m tools.history.verify_continuity
python -m tools.streams.verify_streams
```

Expected starting state:

- branch: `main`
- dirty files: 0
- latest commit subject after Codex closeout: `Add Track K BIL Phase 1 DeepSeek SOP`
- full active suite: 405 passed, 3 skipped, 3 subtests passed
- four SEAM gates: OK

If the worktree is dirty, STOP and emit `SCOPE_LIMIT_HIT` with reason
`ambiguous_owner`.

Execution order:

1. **BIL1** — Create `seam_runtime/benchmark_integrity.py` and
   `test_seam_all/test_benchmark_integrity.py`; implement pure
   deterministic BIL-0/BIL-1/BIL-2 seal, inspect, and verify helpers.
2. **BIL2** — Add CLI commands in `seam_runtime/cli.py`:
   `seam bench seal`, `seam bench verify`, and `seam bench inspect`.
3. **BIL3** — Add the quickstart smoke proving
   `seam bench external --quickstart locomo --adapter seam --judge stub`
   can be sealed as BIL-2 and verified.
4. **BIL4** — Document the new commands in `benchmarks/external/README.md`
   and add the BIL-0..BIL-2 implementation note under F13 in
   `docs/roadmap/TRUST_SECURITY_AUDITABILITY.md`.

Per-item gate:

```bash
python -m pytest test_seam_all/test_benchmark_integrity.py -q
python -m py_compile seam.py
python -m compileall -q seam_runtime benchmarks tools scripts installers
```

Final gate:

```bash
python -m pytest test_seam_all/test_benchmark_integrity.py -q
python -m pytest test_seam_all/ tools/history/ tools/streams/ tests/ -q
python -m py_compile seam.py
python -m compileall -q seam_runtime benchmarks tools scripts installers
python -m seam bench external --quickstart locomo --adapter seam --judge stub --output /tmp/seam-locomo-bil-result.json
python -m seam bench seal /tmp/seam-locomo-bil-result.json --level BIL-2 --output /tmp/seam-locomo-bil-bundle.json
python -m seam bench verify /tmp/seam-locomo-bil-bundle.json --format json
python -m seam bench inspect /tmp/seam-locomo-bil-bundle.json --format json
python -m tools.history.verify_integrity
python -m tools.history.verify_routing
python -m tools.history.verify_continuity
python -m tools.streams.verify_streams
git diff --check
```

Final report format:

```text
===== DEEPSEEK REPORT: ITEM_SUCCESS =====
  item_id: BIL1
  item_title: ...
  files_changed: [...]
  tests_added: [...]
  focused_test_cmd: ...
  focused_test_before_fix: FAIL (...)
  focused_test_after_fix: PASS (...)
  full_suite_result: PASS (...)
  compile_result: PASS (...)
  benchmark_smoke_result: PASS / N/A
  gates_result: PASS / N/A
  diff_stat: ...
  additional_observations: ...
  ready_for_next_item: yes / all_items_complete
===== END REPORT =====
```

If a stop condition fires, emit:

```text
===== DEEPSEEK REPORT: SCOPE_LIMIT_HIT =====
  item_id: ...
  reason: ...
  command: ...
  observed: ...
  files_changed_so_far: [...]
  suggested_operator_decision: ...
===== END REPORT =====
```

Then STOP.
