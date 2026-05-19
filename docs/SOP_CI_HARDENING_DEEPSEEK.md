# SOP — CI Hardening (Verify Gates + Pytest Scope + MCP Smoke), DeepSeek Execution Pass

Issued: 2026-05-19 (post HISTORY#209)
Owner pattern: Claude authors and verifies; DeepSeek executes all items in
sequence in a single session; Claude reviews the full diff at handback,
appends HISTORY entries, commits.

Scope: closes audit findings **H2** (CI does not run the four SEAM verify
gates), **H3a** (CI's pytest invocation skips `tools/streams/test_streams.py`
and the entire `tests/` tree including `tests/audit/`), and **H3b** (no MCP
stdio smoke test in CI). The pre-commit hook already gates locally; CI is the
backstop for `git commit --no-verify`, GitHub-web edits, and revert-merges.

Supersedes scope: extends `docs/SOP_DEEP_AUDIT_REMEDIATION_BLUEPRINT.md`
with per-item red-green specs. Reuses the batch sync-relay protocol from
`docs/SOP_WEBUI_BATCH_HARDENING_DEEPSEEK.md`; the same hard rules apply.

## How to use this SOP

For each item below DeepSeek must:

1. Read only the cited file ranges plus `tests/audit/__init__.py` plus
   `test_seam_all/test_seam.py`.
2. Write a failing test FIRST under the cited `tests/audit/` path (create
   the file if missing). Confirm it fails before any runtime/CI edit.
3. Apply the smallest fix in the cited file(s). Do not touch unrelated
   files. Do not edit `archive/`, `docs/archive/`, `build/`, `.venv/`,
   `test_seam/`, or `experimental/webui/`.
4. Re-run the failing test. Confirm green.
5. Run the per-item gate.
6. Move to the next item. Do NOT commit. Do NOT push.

After ALL items complete: emit one ITEM_SUCCESS block per item, in
execution order, in one final paste. Claude reviews the full diff and
commits.

If a stop condition fires for any item, STOP at that item — emit
ITEM_SUCCESS blocks for items that completed plus the appropriate stop
block for the failed item.

## Pre-flight (run once before starting)

```
git status --short                                  # expect 0 dirty files
git branch --show-current                           # expect main
git log --oneline -1                                # expect: 0fa383e WebUI batch hardening + audit quick-wins (HISTORY#208, #209)
python -m pytest test_seam_all/test_seam.py tools/history/ tools/streams/ tests/ -q
python -m tools.history.verify_integrity
python -m tools.history.verify_routing
python -m tools.history.verify_continuity
python -m tools.streams.verify_streams
```

Expected starting state at the time this SOP was written:
- Branch: `main`
- Dirty files: **0** (the WebUI batch landed at 0fa383e)
- Latest commit subject: `WebUI batch hardening + audit quick-wins (HISTORY#208, #209)`
- pytest across all four scopes: **268 passed** in ~52s
- All four gates: OK

If `git status --short | wc -l` is not 0, STOP and emit SCOPE_LIMIT_HIT
with reason `ambiguous_owner` (unexpected in-flight work — coordinate
with Claude before starting).

## Per-item gate (after each fix, before moving on)

```
python -m pytest tests/audit/<focused_test_file> -q
python -m pytest test_seam_all/test_seam.py tools/history/ tools/streams/ tests/ -q
python -m py_compile seam.py
python -m compileall -q seam_runtime experimental tools scripts installers
```

Item **CI1** edits `.github/workflows/ci.yml`. CI YAML is parsed by GitHub
Actions, not by Python, so `py_compile` and `compileall` will not catch
syntax errors there. Instead, after CI1's edit, run a YAML lint:

```
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" && echo "YAML OK"
```

Failure exits non-zero with a parse-error traceback — treat that as a
focused-test-style FAIL.

## Order of execution

1. **CI1** — Add four SEAM verify gates to `.github/workflows/ci.yml`
2. **CI2** — Expand the CI `pytest` invocation to cover `tools/streams/` and `tests/`
3. **CI3** — MCP stdio JSON-RPC smoke test (`tests/audit/test_mcp_stdio_smoke.py`)

---

## CI1 — Four SEAM verify gates in CI

**Files**: `.github/workflows/ci.yml`
**Failing test**: `tests/audit/test_ci_verify_gates.py`

Test asserts (read-only parse of `ci.yml`):
- Loading `.github/workflows/ci.yml` via `yaml.safe_load` succeeds (no
  YAML errors).
- The `jobs.test-and-benchmark.steps` list contains a step whose `run`
  field is exactly `python -m tools.history.verify_integrity`.
- Same assertion for the other three: `python -m tools.history.verify_continuity`,
  `python -m tools.history.verify_routing`, `python -m tools.streams.verify_streams`.
- All four `verify_*` steps appear BEFORE the step whose `run` begins
  `python -m seam benchmark run` (the gates protect history/streams
  integrity, which the benchmark step assumes is healthy).
- All four `verify_*` steps appear AFTER the existing "Install package"
  and "Install test dependencies" steps (so the Python environment is
  ready).

**Fix**:
- Insert four new steps in `.github/workflows/ci.yml` immediately AFTER
  the existing `Run tests` step and BEFORE the existing `Run benchmark suite`
  step. Maintain the existing two-space indentation; do not reformat
  surrounding YAML. Each step uses the exact form:

  ```yaml
      - name: Verify SEAM history integrity
        run: python -m tools.history.verify_integrity

      - name: Verify SEAM history continuity
        run: python -m tools.history.verify_continuity

      - name: Verify SEAM history routing
        run: python -m tools.history.verify_routing

      - name: Verify SEAM streams
        run: python -m tools.streams.verify_streams
  ```

  Order matters for the test: `verify_integrity` first, then
  `verify_continuity`, `verify_routing`, `verify_streams`. The four
  gates run on both `windows-latest` and `ubuntu-latest` matrix legs
  (the existing matrix config covers both — do not add an `if:` clause).

**Out of scope**:
- Adding new optional dependencies to `install` steps (the verify tools
  use only stdlib and existing extras).
- Caching pip / venv between matrix legs.
- Splitting `test-and-benchmark` into multiple jobs.
- Touching `external-memory-benchmarks.yml`.

**Verify**:
```
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" && echo "YAML OK"
python -m pytest tests/audit/test_ci_verify_gates.py -q
```

Both must pass. Locally execute the four verify modules to confirm they
work invoked exactly as the workflow runs them (DeepSeek's local env
should match the CI env's behavior):
```
python -m tools.history.verify_integrity   && \
python -m tools.history.verify_continuity  && \
python -m tools.history.verify_routing     && \
python -m tools.streams.verify_streams
```

---

## CI2 — Expand CI pytest scope

**Files**: `.github/workflows/ci.yml`
**Failing test**: `tests/audit/test_ci_pytest_scope.py`

Background: the current `Run tests` step runs only
`python -m pytest test_seam_all/ tools/history/test_history_tools.py`.
This misses:
- `tools/streams/test_streams.py` (~7 tests including streams atomic
  append and concurrent-append-no-interleaving)
- `tests/audit/` (the existing `test_vector_pragmas.py`,
  `test_vector_adapter_table_name_validation.py`, plus the seven W1-W4
  + H1 + H5 + M8 audit tests added by HISTORY#208/#209 — 28+ tests)
- any future tests under `tests/` outside `audit/`

Test asserts:
- Loading `.github/workflows/ci.yml` via `yaml.safe_load` succeeds.
- Exactly one step in `jobs.test-and-benchmark.steps` has `name: "Run tests"`.
- That step's `run` field includes BOTH of the substrings
  `tools/streams/` and `tests/` (in addition to the existing
  `test_seam_all/` and `tools/history/test_history_tools.py` substrings,
  which must remain).

**Fix**:
- In `.github/workflows/ci.yml`, replace the existing `Run tests` step's
  `run` line with:

  ```yaml
        run: python -m pytest test_seam_all/ tools/history/test_history_tools.py tools/streams/ tests/
  ```

  Single line; no leading flags, no `-q` (preserve current verbosity).
  Order of paths is not significant to pytest but the substring assertion
  expects them all to be present.

**Out of scope**:
- Adding `--strict-markers`, `--maxfail`, `-x`, or any other pytest flags.
- Splitting into parallel pytest jobs.
- Reorganizing the test discovery layout.

**Verify**:
```
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" && echo "YAML OK"
python -m pytest tests/audit/test_ci_pytest_scope.py -q
python -m pytest test_seam_all/ tools/history/test_history_tools.py tools/streams/ tests/ -q
```

The third command mirrors what CI will run — it must pass cleanly. If a
test elsewhere under `tools/streams/` or `tests/` fails when run via
this expanded scope, STOP and emit SCOPE_LIMIT_HIT with reason
`pre_existing_red_tdd` and the failing test ids; do not fix the
unrelated failure in this item.

---

## CI3 — MCP stdio JSON-RPC smoke test

**Files**: `tests/audit/test_mcp_stdio_smoke.py` (new)
**Failing test**: same file (the smoke test IS the assertion).

Background: the `seam-mcp` console entrypoint
(`seam_runtime.mcp_protocol:main`) is the canonical MCP stdio JSON-RPC
bridge for Gemini, Claude, Cursor, OpenCode, and other MCP clients per
REPO_LEDGER. It currently has no end-to-end test that exercises the
actual subprocess + stdio + JSON-RPC handshake — only unit tests of the
internal `_handle_jsonrpc_message` helpers via test_seam.py exist.

A subprocess-based smoke test catches real regressions: import errors,
entry-point registration drift, JSON-RPC envelope formatting, and tools-list
schema changes that unit tests miss.

Test (write the file from scratch — there is no existing template):
- Use Python's `subprocess.Popen` to spawn the entrypoint as a separate
  process. Prefer the module form `[sys.executable, "-m",
  "seam_runtime.mcp_protocol"]` over the `seam-mcp` console script — the
  module form is robust to PATH issues and consistent across CI matrix
  legs.
- Pipe stdin and stdout (`stdin=subprocess.PIPE,
  stdout=subprocess.PIPE`); redirect stderr to a pipe too so test
  failures can include the server's stderr in the assertion message.
- Send two JSON-RPC 2.0 messages, one per line, each terminated with `\n`:

  1. `initialize` — `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"seam-ci-smoke","version":"0.0.1"}}}`
  2. `tools/list` — `{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}`

- After writing both lines, close stdin so the server can finish reading.
- Read two response lines from stdout. Parse each as JSON.

- Assertions on response 1:
  - `response["jsonrpc"] == "2.0"`
  - `response["id"] == 1`
  - `"result" in response` (NOT `"error"`)
  - `response["result"]["protocolVersion"]` is a non-empty string
  - `response["result"]["capabilities"]` is a dict
  - `response["result"]["serverInfo"]["name"]` is a non-empty string

- Assertions on response 2:
  - `response["jsonrpc"] == "2.0"`
  - `response["id"] == 2`
  - `"result" in response`
  - `response["result"]["tools"]` is a list with `len >= 1`
  - Every tool entry has `name` (string), `description` (string), and
    `inputSchema` (dict)
  - At least one of the tool names matches the pattern `^seam_`
    (canonical SEAM tool prefix)

- After both reads succeed, terminate the subprocess cleanly:
  - Call `proc.terminate()`
  - Wait with a timeout: `proc.wait(timeout=10)`
  - On `TimeoutExpired`, escalate with `proc.kill()` and fail the test
    with a message that includes whatever stderr was captured

- Wrap the entire test in a `try/finally` that calls `proc.kill()` on
  failure so a hung subprocess does not pollute the CI runner.

- Pytest scaffolding: use `pytest.mark.skipif` with condition
  `sys.platform == "win32"` and reason `"Subprocess pipe handshake
  timing is unreliable on Windows-runner Python; revisit if a Windows
  MCP regression appears"`. The Linux matrix leg is sufficient
  coverage for this smoke check; the canonical pre-commit hook already
  gates locally on operator machines regardless of platform.

- Add a top-of-file docstring stating "CI3 — MCP stdio JSON-RPC handshake
  smoke test. Verifies the seam_runtime.mcp_protocol entrypoint
  responds to initialize and tools/list per JSON-RPC 2.0. Subprocess
  isolation catches import/entrypoint regressions unit tests miss."

**Fix**: write the test file. There is no production code change in this
item — the test exercises existing production code.

**Out of scope**:
- Testing `tools/call` round-trips (separate item next cycle).
- Testing OAuth / auth flows (no auth on MCP stdio).
- Asserting the exact tool count (it grows over time; the test must
  remain stable across SOPs).
- Testing the legacy `seam mcp serve` JSON-lines bridge (different
  entrypoint, deprecated path).
- Testing the FastAPI REST API surface (already covered by existing
  test_rest_api_* tests in test_seam_all/test_seam.py).

**Verify**:
```
python -m pytest tests/audit/test_mcp_stdio_smoke.py -q
python -m pytest test_seam_all/ tools/history/test_history_tools.py tools/streams/ tests/ -q
```

The smoke test must pass on the local machine. If the subprocess hangs
or fails to respond, STOP and emit REGRESSION with the captured stderr
in `suspected_cause` — do not "fix" by loosening assertions.

---

## After all items complete

Emit ITEM_SUCCESS blocks for CI1, CI2, CI3 in execution order in a
single paste. Then STOP. Do NOT stage, commit, push. Claude reviews the
full diff, appends a HISTORY entry, rebuilds the index, writes a
snapshot, runs the four verify gates, and commits.

If at any point a stop condition fires, emit ITEM_SUCCESS blocks for
completed items + the appropriate stop block for the failed item, then
STOP.

## Notes on what is deliberately NOT in this SOP

The following audit findings are intentionally deferred to later cycles
to keep this batch small and focused:

- **pgvector integration in CI** (audit H3 third leg) — requires GH
  Actions `services:` block, postgres+pgvector image, `SEAM_PGVECTOR_DSN`
  env wiring, and a new adapter-aware test. Bigger scope; separate SOP.
- **`seam benchmark gate --baseline` in CI** (audit M9) — requires a
  design decision about baseline source (artifact from prior main run?
  checked-in reference? remote URL?). Surface as a watch-list item; do
  not fix mechanically.
- **MCP `surface_artifact` path validation** (audit M6) — requires
  defining what the surface root is, which is an architectural decision
  about where stored surfaces live. Separate SOP.
- **`tools/call` round-trip MCP test** — useful extension of CI3 but
  expands the per-test runtime materially. Add in a follow-up cycle.
