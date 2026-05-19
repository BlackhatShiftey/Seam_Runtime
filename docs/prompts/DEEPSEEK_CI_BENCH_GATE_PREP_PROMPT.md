# DeepSeek Batch Prompt — CI Bench-Gate Prep (B1, B2, B3)

Paste this prompt verbatim into the DeepSeek session. The canonical SOP
is `docs/SOP_CI_BENCH_GATE_PREP_DEEPSEEK.md`. DeepSeek reads it once,
executes B1 → B2 → B3 in sequence on a single working tree, emits
ITEM_SUCCESS blocks for all three at the end, and STOPs without
committing.

---

You are executing the **CI Bench-Gate Prep** SOP at
`docs/SOP_CI_BENCH_GATE_PREP_DEEPSEEK.md`. This is the synchronous
**batch** sync-relay protocol, same shape as
`docs/SOP_CI_HARDENING_DEEPSEEK.md` which you executed cleanly in the
previous session (HISTORY#210, commit `b4fa1df`).

**Hard rules** (same as last batch):

1. Read the SOP from top to bottom **once** before touching any code.
2. Read only the file ranges the SOP cites, plus the per-item failing
   test path. Do NOT load `HISTORY.md`, `HISTORY_INDEX.md`,
   `PROJECT_STATUS.md`, `REPO_LEDGER.md`, `archive/`, `docs/archive/`,
   `build/`, `.venv/`, `test_seam/`, or `experimental/webui/`.
3. **Failing test first.** Write the test, confirm it FAILs (red), then
   apply the smallest fix in the cited file(s). Re-run the focused test
   and confirm GREEN. Run the per-item gate. Move on.
4. Do NOT stage, commit, or push. Claude reviews and commits at the end.
5. Do NOT touch `.github/workflows/external-memory-benchmarks.yml`.
6. Do NOT modify `seam_runtime/server.py` for B1 — the handler contract
   is correct; this is a test-side stability fix.
7. Do NOT touch `seam_runtime/vector_adapters.py` for B2 — the adapter
   is the system under test, not the change.
8. For B3, do NOT extend `tests/audit/test_mcp_stdio_smoke.py`. Write a
   new file `tests/audit/test_mcp_tools_call_smoke.py`.

**Pre-flight** (run before starting any item):

```
git status --short                                  # expect 0 dirty files
git branch --show-current                           # expect main
git log --oneline -1                                # expect b4fa1df CI hardening: ... (HISTORY#210)
python -m pytest test_seam_all/ tools/history/test_history_tools.py tools/streams/ tests/ -q
python -m tools.history.verify_integrity
python -m tools.history.verify_routing
python -m tools.history.verify_continuity
python -m tools.streams.verify_streams
```

If any of these fail with anything other than the known
`test_sys_metrics_live_on_linux` flake (which is exactly what B1 fixes),
STOP and emit SCOPE_LIMIT_HIT with reason `pre_existing_red_tdd` and the
failing ids.

**Execution order**:

1. **B1** — Stabilize `test_sys_metrics_live_on_linux` against the
   zero-delta /proc/stat read window. File:
   `tests/audit/test_sys_metrics_honesty.py`. Two parts: B1a retry-
   tolerant live test, B1b new dedicated zero-delta contract test.
2. **B2** — Real-postgres pgvector integration in CI. Two files:
   `.github/workflows/ci.yml` (new top-level `pgvector-integration`
   job, Linux-only, with services block), and
   `tests/audit/test_pgvector_real_adapter.py` (new, env-skipped via
   `pytestmark = pytest.mark.skipif(...)`).
3. **B3** — MCP `tools/call` round-trip smoke test. New file:
   `tests/audit/test_mcp_tools_call_smoke.py`. Skip on win32 like the
   CI3 sibling test.

**Per-item gate** (after each fix, before moving on):

```
python -m pytest tests/audit/<focused_test_file> -q
python -m pytest test_seam_all/ tools/history/test_history_tools.py tools/streams/ tests/ -q
python -m py_compile seam.py
python -m compileall -q seam_runtime experimental tools scripts installers
```

For B2 (CI YAML edit), additionally:

```
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" && echo "YAML OK"
python -c "import yaml; doc=yaml.safe_load(open('.github/workflows/ci.yml')); assert 'pgvector-integration' in doc['jobs']; print('job present')"
```

For B2, if you do not have a local docker compose pgvector running, the
new test will skip via pytestmark. That is the expected local behavior —
report ITEM_SUCCESS with `additional_observations` noting "local
SEAM_PGVECTOR_DSN not set; new test skipped locally; CI services block
is the first real exercise." Do NOT spin up docker compose from inside
your session.

**Watch-item / known flake**: `test_sys_metrics_live_on_linux` is the
flake you fix in B1. If it appears in the pre-flight full-suite run,
expect it to fail intermittently — that is the baseline. After B1 lands,
it must pass cleanly on two back-to-back full-suite runs.

**Final report**: emit three ITEM_SUCCESS blocks in execution order
(B1, B2, B3) in one paste, then STOP. Use the same block format you
used for CI1/CI2/CI3:

```
===== DEEPSEEK REPORT: ITEM_SUCCESS =====
  item_id: B1
  item_title: ...
  files_changed: [...]
  tests_added: [...]
  focused_test_cmd: ...
  focused_test_before_fix: FAIL/PASS/N/A (...)
  focused_test_after_fix: PASS (...)
  full_suite_cmd: ...
  full_suite_result: PASS (...)
  py_compile_result: PASS / N/A
  compileall_result: PASS / N/A
  yaml_lint_result: PASS / N/A
  diff_stat: ...
  diff_preview: ...
  additional_observations: ...
  ready_for_next_item: yes / all_items_complete
===== END REPORT =====
```

After the third block, append a one-line "Summary of changes:" recap and
the standard "Waiting for Claude review and commit." sign-off.

Begin with the pre-flight commands. Then read the SOP. Then execute.
