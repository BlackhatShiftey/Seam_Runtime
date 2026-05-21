# SOP - Track M P2 LoCoMo Retrieval Wiring

Issued: 2026-05-21
Owner pattern: DeepSeek implements on its own branch; Claude reviews each diff
and merges per item; operator paste-relays.

Scope: the worktree on `main` (un-pushed) already lands three fixes from the
prior DeepSeek pass — RAW added to `INDEXABLE_KINDS`, new
`compile_conversation_turn` function in `seam_runtime/nl.py`, and per-category
score aggregation in the runner. This SOP cleans up what those fixes do not
yet do, and adds the remaining changes needed for an honest LoCoMo number on
the full official dataset.

This SOP is for **wiring and correctness fixes**, not new benchmarks. It
exists because three of the landed fixes are structurally incomplete: F1 (RAW
indexing) does not feed the default retrieval path; F2 (`compile_conversation_turn`)
is dead code with zero call-sites in the runtime or any adapter; and the new
storage stats query computes `max_degree` incorrectly. The publication-readiness
gate (Track M P1 SOP) is unchanged and remains the downstream consumer.

## Goal

Produce a SEAM LoCoMo pipeline where:

1. RAW conversation text is actually considered by the default retrieval
   ranker, not only by the chroma adapter path.
2. The LoCoMo adapter compiles each turn through `compile_conversation_turn`
   instead of `compile_nl`, so the structured CLM/ENT records carry useful
   speaker/date/location/action facts.
3. The `SeamLocomoAdapter` produces a real generated answer (one short LLM
   call against retrieved context) instead of returning the retrieved blob
   itself as the prediction. This is the change that makes SEAM comparable to
   mem0/Zep.
4. Storage stats `max_degree` reports the correct degree for any node whose
   degree is split across `src_id` and `dst_id`.
5. The per-judge cross-check is committed for any published LoCoMo number.
6. The mem0 comparator block on `gpt-5-mini` is documented as a comparator
   gap, not patched upstream.

## Branch

```bash
git switch main
git pull --ff-only origin main
git switch -c deepseek/track-m-p2-locomo-retrieval-wiring
```

The worktree must be clean of un-committed P1 work before this branch is
created. If P1 work is still un-pushed, surface that and stop — do not
overwrite it on a new branch.

## Required First Reads

1. `PROJECT_STATUS.md`
2. `REPO_LEDGER.md`
3. `HISTORY_INDEX.md`
4. `docs/CODE_LAYOUT.md`
5. `docs/DATA_ROUTING.md`
6. `docs/SOP_TRACK_M_P1_REAL_BENCHMARK_RUNS.md`
7. `benchmarks/external/README.md`
8. `seam_runtime/retrieval.py` (the file most fixes touch)
9. `seam_runtime/runtime.py` (the ingest/search entrypoints)
10. `benchmarks/external/locomo/adapters/seam.py` (the consumer)

Do not read all of `HISTORY.md`. Use bounded context packs only.

## Hard Rules

1. Do not commit downloaded datasets, result bundles, API responses, local
   `.env` values, SQLite test artifacts, provider session URLs, or private
   conversation links.
2. Each fix below is one commit. Do not bundle. If a fix breaks, revert that
   commit and stop, do not stack a "fix-the-fix" patch.
3. Do not change the `0.40 / 0.35 / 0.15 / 0.10` score-weight constants in
   `retrieval.py`. The weight formula is out of scope. If retrieval improves
   on the back of these fixes, that is the signal we want; do not also tune
   weights at the same time and call the combined delta a SEAM win.
4. No backwards-compatibility shims. Do not keep both `compile_nl` and a
   `compile_conversation_turn`-shim path conditionally selected by environment
   variable. The LoCoMo adapter selects per-turn; the default `ingest_text`
   keeps using `compile_nl` for non-dialog text.
5. `--judge stub` is smoke-only. Every number quoted in HISTORY or any commit
   message must come from a `--judge openai` or `--judge claude` run, paired
   with `seam bench seal --level BIL-2` and `seam bench verify`.
6. Do not patch `mem0ai` upstream. Document the comparator block in the
   handback and skip mem0 unless `mem0ai` is pinned to a model that accepts
   `max_tokens`.

## Pre-flight

```bash
git status --short --branch
python3 -m tools.history.verify_integrity
python3 -m tools.history.verify_routing
python3 -m tools.history.verify_continuity
python3 -m tools.streams.verify_streams
.venv/bin/python -m pytest test_seam_all/ tools/history/test_history_tools.py tools/streams/ tests/ -q
.venv/bin/python -m seam bench external --quickstart locomo --adapter seam --judge stub --format json
```

Acceptance for quickstart smoke: `context_recall_mean` must be ≥ `0.90` on
the 10-case fixture (current is `0.963`). If it regresses below `0.50`, stop
and report.

## Fixes

Each fix lists: **problem**, **change**, **verification**, **risk**.

### Fix 1 — Wire RAW into the default retrieval ranker (P0)

**Problem.** `seam_runtime/vector.py:14` now includes `RecordKind.RAW` in
`INDEXABLE_KINDS`, so RAW embeddings are written. The default retrieval path
in `seam_runtime/retrieval.py:23` still filters candidates to
`{CLM, STA, EVT, REL}`. That means the LoCoMo adapter's `search_ir` call
never returns a RAW candidate even when the RAW embedding is the best match.
Result: the prior fix improved chroma path only; the default path is
unchanged. The `test_seam_all/test_seam.py:1384` change widening the expected
top hit to `{"clm:2", "raw:1"}` is now non-deterministic and should be made
deterministic again after this fix.

**Change.** Add an opt-in flag, do not change default behavior:

`seam_runtime/retrieval.py`

```python
def search_batch(
    batch: IRBatch,
    query: str,
    scope: str | None = None,
    limit: int = 5,
    vector_scores: dict[str, float] | None = None,
    namespace: str | None = None,
    include_raw: bool = False,
) -> SearchResult:
    ...
    candidate_kinds = {RecordKind.CLM, RecordKind.STA, RecordKind.EVT, RecordKind.REL}
    if include_raw:
        candidate_kinds = candidate_kinds | {RecordKind.RAW}
    for record in records:
        if record.kind not in candidate_kinds:
            continue
        ...
```

`seam_runtime/runtime.py:122` — thread the flag through:

```python
def search_ir(
    self,
    query: str,
    lens: str = "general",
    scope: str | None = None,
    budget: int = 5,
    include_raw: bool = False,
) -> SearchResult:
    batch = self.store.load_ir(scope=scope)
    vector_scores = self.vector_adapter.search(query, limit=max(budget * 3, 10))
    namespace = batch.records[0].ns if batch.records else None
    return search_batch(
        batch,
        query=query,
        scope=scope,
        limit=max(1, budget),
        vector_scores=vector_scores,
        namespace=namespace,
        include_raw=include_raw,
    )
```

`benchmarks/external/locomo/adapters/seam.py:71` — enable in the adapter:

```python
result = rt.search_ir(question, scope="thread", budget=self.budget, include_raw=True)
```

Revert the `test_seam_all/test_seam.py:1384` widening to assert
`hits[0].record.id == "clm:2"` again (the chroma adapter test was the only
caller that needed widening; the chroma adapter does not go through
`search_batch`).

**Verification.**

```bash
.venv/bin/python -m pytest tests/audit/test_raw_vector_indexable.py -q
.venv/bin/python -m pytest test_seam_all/test_seam.py::SeamRuntimeTests::test_chroma_semantic_adapter_searches_via_fake_client -q
.venv/bin/python -m pytest tests/audit/test_locomo_adapter_evidence_text.py -q
.venv/bin/python -m seam bench external --quickstart locomo --judge stub --format json
```

Quickstart `context_recall_mean` must equal or exceed pre-fix value.

**Risk.** Other call-sites that use `search_ir` without `include_raw=True`
keep current behavior — no regression. The change is additive.

### Fix 2 — Wire `compile_conversation_turn` into the LoCoMo adapter (P0)

**Problem.** `seam_runtime/nl.py:96` defines `compile_conversation_turn` and
the test file `tests/audit/test_conversation_turn_compile.py` covers it, but
no production code calls it. `grep -rn compile_conversation_turn` returns
two hits: the def and the test. The LoCoMo adapter
(`benchmarks/external/locomo/adapters/seam.py:49`) still routes through
`rt.ingest_text(...)` which calls `compile_nl`. Result: the structured
speaker/date/location/action CLM facts the new compiler produces are not
generated for any benchmark run.

**Change.** Add a sister ingest entry point on `SeamRuntime` that uses the
conversation compiler, then point the adapter at it. Do not change the
existing `ingest_text` path; non-dialog ingest still wants `compile_nl`.

`seam_runtime/runtime.py`

```python
def ingest_conversation_turn(
    self,
    text: str,
    source_ref: str = "local://input",
    ns: str = "local.default",
    scope: str = "thread",
    persist: bool = True,
) -> IngestReport:
    from .nl import compile_conversation_turn
    document_id = stable_document_id(source_ref, text)
    batch = namespace_ingest_batch(
        compile_conversation_turn(text, source_ref=source_ref, ns=ns, scope=scope),
        document_id,
    )
    stored_ids: list[str] = []
    if persist:
        stored_ids = self.persist_ir(batch).stored_ids
        self.store.mark_document_superseded_by_source_ref(
            source_ref, except_document_id=document_id
        )
    document = self.store.upsert_document_status(
        document_id=document_id,
        ns=ns,
        scope=scope,
        source_ref=source_ref,
        source_hash=source_hash(text),
        byte_count=len(text.encode("utf-8")),
        chunk_count=max(1, len(batch.kind(RecordKind.SPAN))),
        extraction_status="compiled",
        indexed_status="indexed" if persist else "not_indexed",
        metadata={
            "record_count": len(batch.records),
            "indexable_count": len([
                r for r in batch.records
                if r.kind in {RecordKind.CLM, RecordKind.STA, RecordKind.EVT, RecordKind.REL, RecordKind.RAW}
            ]),
        },
    )
    return IngestReport(document=document, stored_ids=stored_ids)
```

`benchmarks/external/locomo/adapters/seam.py:42` — swap the call:

```python
def ingest_turn(self, scope_id: str, turn: ConversationTurn) -> None:
    text = _format_turn(turn)
    rt = _open_runtime(self._db_path(scope_id))
    rt.ingest_conversation_turn(
        text=text,
        source_ref=f"locomo:{scope_id}:turn",
        ns=f"locomo:{scope_id}",
        scope="thread",
        persist=True,
    )
```

ID-collision: `compile_conversation_turn` emits `raw:1`, `span:1`, `clm:N`
just like `compile_nl`. `namespace_ingest_batch` rewrites IDs using the
document_id suffix, so per-turn `source_ref` (`f"locomo:{scope_id}:turn"`) is
**not** unique per turn. The source_ref must include a per-turn
discriminator. Use the turn's deterministic source hash:

```python
import hashlib
turn_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
rt.ingest_conversation_turn(
    text=text,
    source_ref=f"locomo:{scope_id}:turn:{turn_hash}",
    ...
)
```

Without this discriminator, every turn's `stable_document_id` collides on
`locomo:{scope_id}:turn` and the second turn's persist will rewrite the
first turn's records. This is a real bug; do not skip the discriminator.

**Verification.**

```bash
.venv/bin/python -m pytest tests/audit/test_conversation_turn_compile.py -q
.venv/bin/python -m pytest tests/audit/test_locomo_adapter_evidence_text.py -q
.venv/bin/python -m seam bench external --quickstart locomo --judge stub --format json
```

Then add a tests/audit test that asserts after ingesting two distinct turns
through `SeamLocomoAdapter`, both turns' RAW content is retrievable. That
test is the regression gate for the collision discriminator.

**Risk.** Other ingest paths still call `compile_nl` and are unchanged.
The new method is additive on `SeamRuntime`. The biggest risk is the
collision discriminator: skip it and the benchmark silently loses data.

### Fix 3 — Generate a real answer in the LoCoMo adapter (P0)

**Problem.** `SeamLocomoAdapter.answer` returns `AdapterAnswer(retrieved_context=..., generated_answer=None)`.
`runner._score_case` then passes `answer.generated_answer or answer.retrieved_context`
to the judge, which means the judge scores its own ability to extract the
answer from a 2 KB blob. mem0 and Zep adapters generate real answers; SEAM
hands the judge the haystack. Any SEAM-vs-mem0 number reported under this
asymmetry is not a memory-system comparison.

**Change.** Add an optional answer-generator behind a flag. Default off so
existing smoke tests do not pay LLM cost.

`benchmarks/external/locomo/adapters/seam.py`

```python
class SeamLocomoAdapter:
    def __init__(
        self,
        db_path: str | None = None,
        budget: int = 2000,
        include_evidence_closure: bool = True,
        answerer: str | None = None,           # "openai" | "claude" | None
        answerer_model: str | None = None,
    ) -> None:
        ...
        self._answerer = answerer
        self._answerer_model = answerer_model

    def answer(self, scope_id, question) -> AdapterAnswer:
        ...
        retrieved_context = self._build_evidence_context(rt, result) if self.include_evidence_closure else ...
        generated = None
        answer_latency_ms = None
        if self._answerer:
            t1 = _time.monotonic()
            generated = self._generate_answer(question, retrieved_context)
            answer_latency_ms = (_time.monotonic() - t1) * 1000.0
        return AdapterAnswer(
            retrieved_context=retrieved_context,
            generated_answer=generated,
            retrieval_latency_ms=retrieval_latency_ms,
            answer_latency_ms=answer_latency_ms,
        )

    def _generate_answer(self, question: str, context: str) -> str:
        prompt = (
            "Answer the question using ONLY the context. "
            "If the answer is not in the context, say 'unknown'. "
            "Reply with the shortest possible answer, no preamble.\n\n"
            f"Context:\n{context}\n\nQuestion: {question}\nAnswer:"
        )
        if self._answerer == "openai":
            return _openai_short_answer(self._answerer_model or "gpt-4o-mini", prompt)
        if self._answerer == "claude":
            return _claude_short_answer(self._answerer_model or "claude-haiku-4-5-20251001", prompt)
        raise ValueError(f"unknown answerer {self._answerer!r}")
```

`_openai_short_answer` and `_claude_short_answer` are small helpers that
reuse the same env-var pattern (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) the
judges use, with the same gpt-5/o-series branch already encoded in
`benchmarks/external/common/judge.py:_uses_completion_token_budget`. Cap
output at 64 tokens, temperature 0.

`benchmarks/external/locomo/run.py` — add CLI flags:

```python
parser.add_argument("--answerer", choices=["none", "openai", "claude"], default="none")
parser.add_argument("--answerer-model", default=None)
```

Pass them through to `build_adapter`. When `--answerer none`, behavior is
identical to today (no LLM call, no extra cost).

`benchmarks/external/common/runner.py:_score_case` — separate metrics when
both retrieval context and generated answer are present:

```python
if answer.generated_answer is not None:
    case_entry["scores"]["answer_em"] = exact_match(answer.generated_answer, case.gold_answer)
    case_entry["scores"]["answer_f1"] = token_f1(answer.generated_answer, case.gold_answer)
    case_entry["scores"]["context_recall"] = context_recall(answer.retrieved_context, case.gold_answer)
else:
    # legacy: prediction = retrieved_context, EM/F1 are uninformative
    ...
```

**Verification.**

```bash
.venv/bin/python -m pytest test_seam_all/test_locomo_judge.py -q
.venv/bin/python -m seam bench external --quickstart locomo --judge stub --answerer none --format json
# Optional, requires OPENAI_API_KEY in the local env (do not commit):
.venv/bin/python -m benchmarks.external.locomo.run --quickstart --judge stub --answerer openai --answerer-model gpt-4o-mini
```

The optional smoke must show non-empty `cases[*].generated_answer` strings
with median length under 50 characters. Long answers indicate the prompt is
not constraining the model; tighten the prompt rather than the budget.

**Risk.** Adds an LLM dependency to any benchmark run that opts in. Cost on
the official 1,542-case set with `gpt-4o-mini` short answers is ~$0.50 at
current pricing; both the judge and the answerer total ~$1.50/run. Operator
must approve.

### Fix 4 — Correct `max_degree` aggregation in storage stats (P1)

**Problem.** `seam_runtime/storage.py:251-260` computes the highest-degree
node with:

```sql
select node_id, deg from (
  select src_id as node_id, count(*) as deg from ir_edges group by src_id
  union all
  select dst_id as node_id, count(*) as deg from ir_edges group by dst_id
) group by node_id order by sum(deg) desc limit 1
```

`order by sum(deg)` correctly identifies the top node, but the bare `deg`
column selected outside the aggregate is implementation-defined — SQLite
returns one of the two values, not their sum. A node with `src` degree 4 and
`dst` degree 4 (total degree 8) is reported as `max_degree=4`. Reproduction:

```python
import sqlite3
c = sqlite3.connect(":memory:")
c.execute("create table ir_edges (src_id text, dst_id text)")
for _ in range(4): c.execute("insert into ir_edges values ('HUB', 'X')")
for _ in range(4): c.execute("insert into ir_edges values ('Y', 'HUB')")
for _ in range(5): c.execute("insert into ir_edges values ('DECOY', 'Z')")
print(c.execute(
    "select node_id, deg from ("
    "  select src_id as node_id, count(*) as deg from ir_edges group by src_id "
    "  union all "
    "  select dst_id as node_id, count(*) as deg from ir_edges group by dst_id"
    ") group by node_id order by sum(deg) desc limit 1"
).fetchone())
# ('HUB', 4)  — should be 8
```

**Change.** Nest the aggregation so the outer select reads `sum(deg)`:

```sql
select node_id, total_deg from (
  select node_id, sum(deg) as total_deg from (
    select src_id as node_id, count(*) as deg from ir_edges group by src_id
    union all
    select dst_id as node_id, count(*) as deg from ir_edges group by dst_id
  ) group by node_id
) order by total_deg desc limit 1
```

Update the Python:

```python
max_degree_row = connection.execute("...above query...").fetchone()
max_degree = max_degree_row["total_deg"] if max_degree_row else 0
max_degree_node = max_degree_row["node_id"] if max_degree_row else None
```

**Verification.**

Add `tests/audit/test_storage_stats_max_degree.py` with the HUB/DECOY case
above. Assert `stats["max_degree"] == 8` and `stats["max_degree_node"] == "HUB"`.

```bash
.venv/bin/python -m pytest tests/audit/test_storage_stats_max_degree.py -q
.venv/bin/python -m pytest tests/ -k stats -q
```

**Risk.** None for the dashboard — the dashboard already reads `max_degree`
through `sysStats?.max_degree`; correcting it just shows true values.

### Fix 5 — Add `--judge-cross-check` to LoCoMo runner (P1)

**Problem.** The current runner reports a single judge's score. Two judges
disagree more often than a single judge admits; using only one judge inflates
confidence. The benchmark policy in `REPO_LEDGER.md` requires non-stub judge
for publication; it does not yet require cross-checking.

**Change.** Add an optional second-judge pass. Do not change the integrity
hash — it must remain `cases + scores`; add cross-check fields outside.

`benchmarks/external/locomo/run.py`

```python
parser.add_argument("--judge-cross", choices=["none", "openai", "claude"], default="none")
parser.add_argument("--judge-cross-model", default=None)
```

`benchmarks/external/common/runner.py` — after primary scoring, if the cross
judge is set, run it over the same `cases[*]` predictions and attach
`cases[*].judge_cross` and `scores.judge_cross_*` (mean, correct count,
agreement rate with primary). Document in the report's
`integrity_hash_excludes` field that judge_cross is not in the hash so the
hash remains reproducible across re-runs that swap the cross judge.

**Verification.**

```bash
.venv/bin/python -m pytest test_seam_all/test_locomo_judge.py -q
# Optional smoke with two stub judges, asserting agreement_rate == 1.0:
.venv/bin/python -m benchmarks.external.locomo.run --quickstart --judge stub --judge-cross stub
```

**Risk.** Doubles judge cost when enabled. Off by default.

### Fix 6 — Document mem0 comparator block (P1, no code change)

**Problem.** The prior DeepSeek pass reported that `mem0ai` sends
`max_tokens` to `gpt-5-mini` and gets rejected. The repo's own
`benchmarks/external/common/judge.py` has the same fix for the judge side,
but the comparator path runs mem0ai's internal LLM client, not our judge.
Patching `mem0ai` upstream is out of scope and would force a vendored fork.

**Change.** Documentation only. Update
`benchmarks/external/mem0_harness/README.md` with:

```
## Known comparator gaps

mem0ai's internal client sends `max_tokens` to OpenAI completion endpoints.
GPT-5 and o-series models reject `max_tokens` and require
`max_completion_tokens`. To run the mem0 comparator today, pin the mem0
client model to a chat-completion model that still accepts `max_tokens`:

  export MEM0_LLM_MODEL=gpt-4o-mini

When `MEM0_LLM_MODEL` is unset or names a gpt-5/o-series model, the mem0
comparator will fail; report the failure verbatim and skip the comparator
column rather than fabricating a mem0 score.
```

If mem0ai's later release accepts the modern parameter, remove this note in
the same commit that bumps the pin.

**Verification.** Manual: re-run the prior `python -m benchmarks.external.mem0_harness.adapter --dry-run`
with `MEM0_LLM_MODEL=gpt-4o-mini` and confirm it does not hit the
`max_tokens` error. Do not commit any captured payloads.

**Risk.** None — documentation only.

## Required Verification Before Handback

```bash
git diff --check
.venv/bin/python -m pytest tests/audit/test_raw_vector_indexable.py -q
.venv/bin/python -m pytest tests/audit/test_conversation_turn_compile.py -q
.venv/bin/python -m pytest tests/audit/test_locomo_adapter_evidence_text.py -q
.venv/bin/python -m pytest tests/audit/test_storage_stats_max_degree.py -q
.venv/bin/python -m pytest test_seam_all/test_locomo_judge.py -q
.venv/bin/python -m pytest test_seam_all/ tools/history/test_history_tools.py tools/streams/ tests/ -q
.venv/bin/python -m py_compile seam.py
.venv/bin/python -m compileall -q seam_runtime benchmarks tools scripts installers
python3 -m tools.history.verify_integrity
python3 -m tools.history.verify_routing
python3 -m tools.history.verify_continuity
python3 -m tools.streams.verify_streams
.venv/bin/python -m seam bench external --quickstart locomo --judge stub --format json
```

After landing all six fixes, hand off to Track M P1 SOP for the real-judge
run on the full official LoCoMo dataset.

## Final Report Format

```text
===== DEEPSEEK REPORT: TRACK_M_P2_LOCOMO_RETRIEVAL_WIRING =====
branch: deepseek/track-m-p2-locomo-retrieval-wiring
head: <sha>
base: main

fixes_landed:
- F1 raw_in_default_search: <commit, files>
- F2 conversation_compiler_wired: <commit, files, collision_discriminator: yes/no>
- F3 generated_answer_path: <commit, files, default_answerer: none>
- F4 max_degree_query: <commit, files, regression_test_added: yes>
- F5 judge_cross_check: <commit, files, default: off>
- F6 mem0_block_documented: <commit, files>

quickstart_after_all_fixes:
- context_recall_mean: <value>
- judge_score_mean (stub): <value, smoke-only>
- per_category: <dict snapshot>

regressions_introduced:
- <fix_id: description or none>

deferred_for_track_m_p1:
- full official LoCoMo real-judge run (out of P2 scope)

verification:
- <command> -> <result>

changed_files:
- <path: lines added/removed>

artifacts_not_committed:
- <none expected — this SOP does not produce result bundles>

open_questions:
- <question or none>
```
