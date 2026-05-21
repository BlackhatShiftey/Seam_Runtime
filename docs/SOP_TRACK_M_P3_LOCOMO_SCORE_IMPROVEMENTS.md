# SOP - Track M P3 LoCoMo Score Improvements

Issued: 2026-05-21
Owner pattern: DeepSeek implements on its own branch; Claude reviews each
diff and merges per item; operator paste-relays.

Scope: P2 (`docs/SOP_TRACK_M_P2_LOCOMO_RETRIEVAL_WIRING.md`) wires the
existing fixes correctly. P3 adds the retrieval and reasoning changes that
move LoCoMo scores, plus a small architectural-hygiene batch that does not
affect scores but should land before the next benchmark publication.

This SOP exists because the worktree fixes (RAW indexing, conversation
compiler, per-category aggregation) only set up the foundation. The scoring
formula `0.40 lex + 0.35 sem + 0.15 graph + 0.10 temporal` still leans on a
Jaccard "lexical" channel and a Counter-cosine "semantic" channel that
collapse to the same bag-of-words signal when SBERT is not loaded. The
benchmark also does no decomposition for multi-hop, no temporal filtering,
and no abstention on adversarial rows. Each of those is a known LoCoMo
failure mode.

P3 prerequisites: **all six P2 fixes must be merged on `main` first.** Do
not start P3 until P2 lands and the quickstart smoke holds at
`context_recall_mean ≥ 0.90`.

## Goal

Move LoCoMo scores on the official 1,542-case answerable set by:

1. Replacing the Jaccard lexical channel with BM25 over RAW conversation
   text so common dialogue tokens stop dominating ranking.
2. Enforcing a real embedding model (SBERT or OpenAI-compatible) during
   benchmark runs so the "semantic" channel stops duplicating the lexical
   channel.
3. Adding multi-hop question decomposition for cases where the question
   requires evidence from more than one turn.
4. Adding a temporal-token filter that boosts candidates whose timestamp
   matches a date/window mentioned in the question.
5. Adding an abstention threshold so adversarial/answerless rows produce
   `"unknown"` instead of a confidently wrong answer.
6. Landing four architectural-hygiene items that are pre-publication
   blockers but do not move benchmark scores by themselves.

Each fix is scoped, measurable, and has a verification step that runs
without the full official dataset (smoke on the 10-case quickstart). Real
score deltas are produced at the end via a single full-dataset run gated by
`SOP_TRACK_M_P1_REAL_BENCHMARK_RUNS.md`.

## Branch

```bash
git switch main
git pull --ff-only origin main
git switch -c deepseek/track-m-p3-locomo-score-improvements
```

Refuse to start the branch if `git log origin/main..HEAD` is non-empty or if
any P2 fix is still un-merged. Surface that and stop.

## Required First Reads

1. `PROJECT_STATUS.md`
2. `REPO_LEDGER.md`
3. `HISTORY_INDEX.md`
4. `docs/CODE_LAYOUT.md`
5. `docs/DATA_ROUTING.md`
6. `docs/SOP_TRACK_M_P1_REAL_BENCHMARK_RUNS.md`
7. `docs/SOP_TRACK_M_P2_LOCOMO_RETRIEVAL_WIRING.md` (must already be merged)
8. `seam_runtime/retrieval.py`
9. `seam_runtime/runtime.py`
10. `seam_runtime/models.py`
11. `benchmarks/external/locomo/adapters/seam.py`
12. `benchmarks/external/common/runner.py`

Use bounded context packs; do not load all of `HISTORY.md`.

## Hard Rules

1. One commit per Fix. Do not bundle. If any verification step fails, stop
   and surface the diff and the failure verbatim. Do not stack
   "fix-the-fix" patches.
2. Do not retune the `0.40 / 0.35 / 0.15 / 0.10` score-weight constants in
   the same PR as any other change. Weight retuning is a separate decision
   that requires its own ablation evidence.
3. Do not commit downloaded datasets, real result bundles, judge API
   responses, local `.env` values, SQLite test artifacts, provider session
   URLs, or private conversation links. Result bundles for the final
   full-dataset run go to `/tmp/seam-track-m/` per P1 SOP.
4. `--judge stub` is smoke-only. Every quoted score number must come from a
   `--judge openai` or `--judge claude` run, paired with `seam bench seal
   --level BIL-2` and `seam bench verify`.
5. Do not patch upstream packages. If `sentence-transformers` is missing,
   surface a clear `RuntimeError`; do not silently fall back to the hash
   embedder during benchmark runs.
6. Do not add per-test sleeps, retries, or `xfail` markers to work around a
   failing change. Roll back the change instead.

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

Acceptance: quickstart `context_recall_mean ≥ 0.90`. If under, stop — P2 is
not actually landed and P3 will not stack cleanly.

## Fixes — Score Movers

### Fix 1 — BM25 lexical channel over RAW (P0, expected highest single impact)

**Problem.** `seam_runtime/retrieval.py:74-78` computes lexical score as
Jaccard intersection of query tokens with the record's textual fields:

```python
def _lexical_score(record, query_tokens):
    record_tokens = set(_tokens(" ".join(iter_textual_fields(record))))
    return len(set(query_tokens) & record_tokens) / max(len(set(query_tokens)), 1)
```

Common dialogue tokens ("thinking", "looked", "great", "thought") match
every turn equally. There is no IDF, no length normalization, no
collection-wide statistics. On LoCoMo, that makes lexical near-uniform and
the ranker effectively relies on the (often-degenerate) semantic channel.

**Change.** Add a BM25 scorer over the per-scope RAW corpus. Keep the
existing Jaccard as a fallback for the non-RAW kinds. Do not change the
weight constants.

New file `seam_runtime/bm25.py`:

```python
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable


_TOKEN = re.compile(r"[a-z0-9_:-]+")


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class BM25Index:
    """Per-corpus BM25 over plain text documents.

    Cheap to construct (one pass over the corpus). Designed to be built
    per-scope at search time; do not persist. Constants are the standard
    BM25 defaults (k1=1.5, b=0.75) — do not retune in this fix.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._doc_lens: list[int] = []
        self._doc_tokens: list[Counter[str]] = []
        self._df: Counter[str] = Counter()
        self._doc_ids: list[str] = []

    def add(self, doc_id: str, text: str) -> None:
        toks = _tokens(text)
        if not toks:
            return
        counts = Counter(toks)
        self._doc_ids.append(doc_id)
        self._doc_tokens.append(counts)
        self._doc_lens.append(len(toks))
        for term in counts.keys():
            self._df[term] += 1

    def score(self, query: str) -> dict[str, float]:
        if not self._doc_lens:
            return {}
        n = len(self._doc_lens)
        avgdl = sum(self._doc_lens) / n
        q_tokens = _tokens(query)
        if not q_tokens:
            return {}
        idf = {
            term: math.log(1 + (n - self._df[term] + 0.5) / (self._df[term] + 0.5))
            for term in set(q_tokens)
        }
        out: dict[str, float] = {}
        for i, doc_id in enumerate(self._doc_ids):
            counts = self._doc_tokens[i]
            dl = self._doc_lens[i]
            score = 0.0
            for term in q_tokens:
                if term not in counts:
                    continue
                f = counts[term]
                num = f * (self.k1 + 1)
                den = f + self.k1 * (1 - self.b + self.b * dl / avgdl)
                score += idf.get(term, 0.0) * (num / den)
            if score > 0:
                out[doc_id] = score
        return out
```

`seam_runtime/retrieval.py` — add an optional BM25 channel to
`search_batch` keyed on RAW records' `attrs["content"]`:

```python
from .bm25 import BM25Index

def search_batch(
    batch, query, scope=None, limit=5,
    vector_scores=None, namespace=None,
    include_raw=False,
    bm25_index: BM25Index | None = None,
) -> SearchResult:
    ...
    bm25_scores: dict[str, float] = bm25_index.score(query) if bm25_index else {}
    for record in records:
        if record.kind not in candidate_kinds:
            continue
        lexical = _lexical_score(record, tokens)
        if record.kind == RecordKind.RAW and record.id in bm25_scores:
            # BM25 dominates Jaccard for RAW when both are present; normalize
            # to roughly the same [0, 1] range by dividing by the per-query max.
            max_bm25 = max(bm25_scores.values()) or 1.0
            lexical = max(lexical, bm25_scores[record.id] / max_bm25)
        ...
```

`seam_runtime/runtime.py:122` — build a per-scope BM25 index at search time
from RAW records in the loaded batch, pass it down:

```python
def search_ir(self, query, lens="general", scope=None, budget=5, include_raw=False):
    batch = self.store.load_ir(scope=scope)
    vector_scores = self.vector_adapter.search(query, limit=max(budget * 3, 10))
    namespace = batch.records[0].ns if batch.records else None
    bm25 = None
    if include_raw:
        bm25 = BM25Index()
        for record in batch.records:
            if record.kind == RecordKind.RAW:
                content = record.attrs.get("content")
                if isinstance(content, str) and content:
                    bm25.add(record.id, content)
    return search_batch(
        batch, query=query, scope=scope, limit=max(1, budget),
        vector_scores=vector_scores, namespace=namespace,
        include_raw=include_raw, bm25_index=bm25,
    )
```

The LoCoMo adapter is already passing `include_raw=True` after P2 Fix 1; no
adapter change needed.

**Verification.**

Add `tests/audit/test_bm25_lexical_channel.py` with:
- two documents, one with the query term repeated 5 times and one with it
  once; assert BM25 ranks the first higher.
- a corpus where the query term appears in every document; assert BM25
  ranks them by length-normalized term frequency, not by raw count.
- a corpus where query terms are absent; assert empty result.

```bash
.venv/bin/python -m pytest tests/audit/test_bm25_lexical_channel.py -q
.venv/bin/python -m pytest tests/audit/test_raw_vector_indexable.py -q
.venv/bin/python -m pytest tests/audit/test_locomo_adapter_evidence_text.py -q
.venv/bin/python -m seam bench external --quickstart locomo --judge stub --format json
```

Quickstart `context_recall_mean` must not regress.

**Risk.** Adds a per-search per-scope build cost: O(N tokens) once per
question. On LoCoMo (~300 turns per scope), this is negligible.

### Fix 2 — Enforce real embedding model on benchmark runs (P0)

**Problem.** `seam_runtime/models.py:159-173` selects the embedding model
from `SEAM_EMBEDDING_PROVIDER`, defaulting to `hash`. The hash embedder
produces deterministic per-token hash vectors with **no semantic signal**.
With the hash embedder loaded, the `semantic` channel in `retrieval.py:27`
collapses to "tokens that hash-collide with query tokens" — which is
essentially the lexical channel a second time. The score formula's 35%
weight on semantic is wasted.

**Change.** When the LoCoMo adapter constructs a runtime, require a real
embedding model. Fail loudly if `sentence-transformers` is missing or the
provider is `hash`.

`benchmarks/external/locomo/adapters/seam.py`

```python
def _open_runtime(db_path: Path):
    from seam_runtime.runtime import SeamRuntime
    from seam_runtime.models import (
        SentenceTransformerModel,
        embedding_settings_from_env,
    )
    db_path.parent.mkdir(parents=True, exist_ok=True)

    settings = embedding_settings_from_env()
    if settings.provider in {"hash", "local", "deterministic"}:
        # Benchmark runs must use a real embedding model. The hash model
        # gives the "semantic" channel no real signal.
        try:
            model = SentenceTransformerModel(model_name="BAAI/bge-small-en-v1.5")
        except Exception as exc:
            raise RuntimeError(
                "LoCoMo benchmark requires a real embedding model. "
                "Install with `pip install sentence-transformers`, "
                "or set SEAM_EMBEDDING_PROVIDER=openai with a valid "
                "SEAM_EMBEDDING_API_KEY_ENV. "
                f"Default-model load failed: {exc}"
            ) from exc
        return SeamRuntime(str(db_path), embedding_model=model)

    return SeamRuntime(str(db_path))
```

Choice of `bge-small-en-v1.5` is deliberate: 384-dim, ~30 MB, fast on CPU,
and well-known to outperform `all-MiniLM-L6-v2` on retrieval benchmarks.
Do not change this default in the same commit; it is a real-data choice.

**Verification.**

```bash
.venv/bin/python -m pytest tests/audit/test_locomo_adapter_evidence_text.py -q
.venv/bin/python -m seam bench external --quickstart locomo --judge stub --format json
```

Add `tests/audit/test_locomo_adapter_real_embedding.py`:
- construct `SeamLocomoAdapter()`; call `_open_runtime` (or whichever
  internal hook the implementation exposes) and assert
  `runtime.embedding_model.name` does not start with `hash`.
- monkeypatch `SentenceTransformerModel.__init__` to raise; assert the
  RuntimeError surfaces the install hint above.

**Risk.** Adds a one-time model download on first run (~150 MB to the
HuggingFace cache). Document this in the SOP handback. The cache is
operator-controlled (`HF_HOME`); do not commit it.

### Fix 3 — Multi-hop question decomposition (P0, expected impact on multi-hop category only)

**Problem.** LoCoMo's `multi-hop` category requires evidence from more than
one turn. SEAM's current `answer` does a single search and returns the
top-k closure. If the question is "Where did Alice and Bob meet for the
trip they later cancelled?", a single search seeds on one of the three
entities; the closure may not reach the other two.

**Change.** Add an optional LLM-driven decomposer behind a flag. Default
off (no cost when unused).

`benchmarks/external/locomo/adapters/seam.py`

```python
class SeamLocomoAdapter:
    def __init__(
        self,
        db_path=None, budget=2000, include_evidence_closure=True,
        answerer=None, answerer_model=None,
        decomposer=None,         # "openai" | "claude" | None
        decomposer_model=None,
        decomposer_max_subq=3,
    ):
        ...
        self._decomposer = decomposer
        self._decomposer_model = decomposer_model
        self._decomposer_max_subq = decomposer_max_subq

    def answer(self, scope_id, question):
        ...
        questions = [question]
        if self._decomposer:
            sub = self._decompose(question)
            if sub:
                questions = sub[: self._decomposer_max_subq] + [question]
        rt = _open_runtime(self._db_path(scope_id))
        closures: list[set[str]] = []
        retrieval_latency_ms = 0.0
        for q in questions:
            t0 = _time.monotonic()
            result = rt.search_ir(q, scope="thread", budget=self.budget, include_raw=True)
            retrieval_latency_ms += (_time.monotonic() - t0) * 1000.0
            closures.append(self._collect_closure_ids(result))
        merged = set().union(*closures) if closures else set()
        retrieved_context = self._build_evidence_context_from_ids(rt, merged)
        ...

    def _decompose(self, question: str) -> list[str]:
        prompt = (
            "Decompose the question into 1-3 atomic sub-questions that each "
            "ask about a single fact, entity, or event. Reply with one "
            "sub-question per line and nothing else. If the question is "
            "already atomic, reply with the original question only.\n\n"
            f"Question: {question}\nSub-questions:"
        )
        if self._decomposer == "openai":
            text = _openai_short_answer(self._decomposer_model or "gpt-4o-mini", prompt, max_tokens=128)
        elif self._decomposer == "claude":
            text = _claude_short_answer(self._decomposer_model or "claude-haiku-4-5-20251001", prompt, max_tokens=128)
        else:
            return []
        return [line.strip() for line in text.splitlines() if line.strip()][: self._decomposer_max_subq]
```

`benchmarks/external/locomo/run.py` — add CLI flags:

```python
parser.add_argument("--decomposer", choices=["none", "openai", "claude"], default="none")
parser.add_argument("--decomposer-model", default=None)
parser.add_argument("--decomposer-max-subq", type=int, default=3)
```

Pass through to `build_adapter`. When `--decomposer none`, `_decompose` is
never called.

`_collect_closure_ids` and `_build_evidence_context_from_ids` are
refactors of the existing `_build_evidence_context` — split it so the
multi-search merge path can call the closure builder with a pre-merged ID
set.

**Verification.**

Add `tests/audit/test_locomo_decomposer.py` with a stubbed decomposer
(monkeypatch `_openai_short_answer` to return a fixed string) and assert
the search is called once per sub-question plus once for the original.

```bash
.venv/bin/python -m pytest tests/audit/test_locomo_decomposer.py -q
.venv/bin/python -m seam bench external --quickstart locomo --judge stub --format json
```

Decomposer off must produce identical scores to current. Decomposer on with
the stub must show `cases[*]` having higher retrieval_latency_ms (multiple
searches) but unchanged context_recall (quickstart questions are already
single-hop).

**Risk.** Cost: ~1.5x decomposer calls per question. Off by default.

### Fix 4 — Temporal-token filter (P0, expected impact on temporal category only)

**Problem.** LoCoMo's `temporal` category asks questions like "What did
Alice say about Japan in April 2023?" or "How long after the booking did
the cancellation happen?". `retrieval.py:_temporal_score` returns 1.0 if
`t0` is set, 0.2 otherwise — uniform across LoCoMo because every turn has
a timestamp. The temporal channel contributes no signal.

**Change.** Detect date/temporal tokens in the question. When present,
boost candidates whose RAW SPAN's parent turn timestamp falls inside the
mentioned window. Do not boost when the question has no temporal tokens.

`seam_runtime/temporal.py` (new):

```python
from __future__ import annotations

import re
from datetime import datetime, timedelta

_MONTH = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_DATE_PATTERNS = [
    rf"\b({_MONTH})\s+\d{{4}}\b",
    r"\b\d{1,2}\s+" + _MONTH + r"\s+\d{4}\b",
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
    r"\b(?:last|this|next)\s+(?:week|month|year)\b",
    r"\b(?:yesterday|today|tomorrow)\b",
    r"\b\d+\s+(?:days?|weeks?|months?|years?)\s+(?:ago|after|before|later)\b",
]
_TEMPORAL_RE = re.compile("|".join(_DATE_PATTERNS), re.IGNORECASE)


def detect_temporal_tokens(question: str) -> list[str]:
    return [m.group(0) for m in _TEMPORAL_RE.finditer(question)]


def parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(ts[: len(fmt) + 4], fmt)
        except ValueError:
            continue
    return None
```

`seam_runtime/retrieval.py` — extend `search_batch` with optional
`temporal_window: tuple[datetime, datetime] | None`. When present, boost
the temporal score for records whose own `t0` (or whose parent turn `t0`
via SPAN→RAW closure) falls inside the window:

```python
def search_batch(..., temporal_window=None):
    ...
    for record in records:
        ...
        if temporal_window is not None:
            t0_parsed = parse_iso(record.t0)
            if t0_parsed and temporal_window[0] <= t0_parsed <= temporal_window[1]:
                temporal = 1.0
            else:
                temporal = 0.0  # uniform-boost neutralized when filter is active
        else:
            temporal = _temporal_score(record)
        score = (0.4 * lexical) + (0.35 * semantic) + (0.15 * graph_bonus) + (0.10 * temporal)
```

LoCoMo adapter applies the window from the question's temporal tokens.
Conservative default: take the union of all detected months/dates and pad
by ±30 days. If parsing fails, pass `None` and the existing temporal score
is used unchanged.

**Verification.**

Add `tests/audit/test_temporal_filter.py`:
- question with "April 2023" — assert detect_temporal_tokens returns one
  match.
- question with no temporal tokens — assert empty list, search_batch
  receives `temporal_window=None`.
- two records with t0 in April vs December; query mentions April —
  assert April record ranks higher than December record after filter.

```bash
.venv/bin/python -m pytest tests/audit/test_temporal_filter.py -q
.venv/bin/python -m seam bench external --quickstart locomo --judge stub --format json
```

**Risk.** If parsing is wrong, temporal score drops to 0.0 for everything
instead of staying at the harmless uniform 0.2. Mitigated by the "fail
back to existing behavior" path when no tokens are detected.

### Fix 5 — Abstain threshold for adversarial rows (P0)

**Problem.** The official LoCoMo release contains 444 adversarial /
answerless rows (`PROJECT_STATUS.md`); P2's loader already skips them, but
the answerable rows still include "no answer in context" cases that scored
"correct" by accident under the prior judge-sees-blob setup. With a real
generated answer (P2 Fix 3), confidently-wrong answers will appear and tank
judge scores.

**Change.** After P2 Fix 3's `_generate_answer`, gate the output on
retrieval confidence. When the top candidate score is below a threshold,
emit `"unknown"` instead of forcing an answer.

`benchmarks/external/locomo/adapters/seam.py`

```python
class SeamLocomoAdapter:
    def __init__(self, ..., abstain_threshold: float = 0.0):
        ...
        self._abstain_threshold = abstain_threshold

    def answer(self, scope_id, question):
        ...
        top_score = result.candidates[0].score if result.candidates else 0.0
        if self._answerer and top_score < self._abstain_threshold:
            generated = "unknown"
        elif self._answerer:
            generated = self._generate_answer(question, retrieved_context)
        else:
            generated = None
        ...
```

CLI flag: `--abstain-threshold 0.15` (default 0.0 = never abstain; keep
behavior identical to P2 Fix 3 unless the operator opts in). The 0.15
default at opt-in time is heuristic — DeepSeek must add a comment that
"the optimal threshold should be tuned on a held-out split, not on the
full test set."

`benchmarks/external/common/runner.py` — when prediction is `"unknown"`,
the judge prompt must be told that abstention is an option. Update the
judge prompt template (or add a sister template for benchmarks that
support abstention):

```python
ABSTAINING_JUDGE_PROMPT = """You are an impartial scorer for a memory-benchmark question.

Question: {question}
Gold answer: {gold}
System answer: {pred}

Score the system answer:
- "correct" if it conveys the same meaning as the gold answer (paraphrasing is fine)
- "partial" if it contains the right entity/fact but is incomplete or has minor errors
- "incorrect" if it is wrong or unsupported by the context
- If the system answer is exactly "unknown", score as "abstain" — neither correct nor incorrect.

Respond ONLY with strict JSON in this exact shape:
{{"verdict": "correct" | "partial" | "incorrect" | "abstain", "rationale": "one short sentence"}}"""
```

Update `JudgeVerdict` to allow `"abstain"` with score `0.0` that does not
count toward `incorrect_count` aggregates. Add an `abstain_count` field to
`aggregate_judge_scores`.

**Verification.**

Add `tests/audit/test_abstain_threshold.py`:
- `--abstain-threshold 0.0` (default) — unchanged behavior.
- `--abstain-threshold 1.0` — every prediction becomes `"unknown"`;
  judge_score with stub remains 1.0 (stub always "correct") but with the
  abstaining judge prompt, verdict should be `"abstain"` and not counted
  as `incorrect`.

```bash
.venv/bin/python -m pytest tests/audit/test_abstain_threshold.py -q
.venv/bin/python -m pytest test_seam_all/test_locomo_judge.py -q
.venv/bin/python -m seam bench external --quickstart locomo --judge stub --format json
```

**Risk.** Wrong threshold can mass-abstain real answers. Mitigation: the
default is 0.0 — DeepSeek must not enable a non-zero threshold in this
SOP. Tuning is a separate operator-approved follow-up using a held-out
split.

## Fixes — Architectural Hygiene (P1, do not move scores)

### Fix 6 — Chroma `sync_on_search` defaults to False (P1)

**Problem.** `experimental/retrieval_orchestrator/adapters.py:139` sets
`sync_on_search: bool = True` by default. Every search triggers a
re-embed sync. Massive overhead on large stores.

**Change.** Flip the default to `False`. Callers that need sync (CLI
ingest, dashboard reload) already call `sync_persistent_indexes` explicitly
per `grep -n sync_persistent_indexes`. Add a deprecation note in the
adapter docstring that the flag remains for opt-in but the default has
flipped.

**Verification.**

```bash
.venv/bin/python -m pytest test_seam_all/test_seam.py -k chroma -q
.venv/bin/python -m pytest tests/ -q
```

Add `tests/audit/test_chroma_sync_default.py` asserting the default is now
`False` and that an opt-in `sync_on_search=True` still performs the sync.

### Fix 7 — Foreign-key constraints on `ir_edges` (P1)

**Problem.** `seam_runtime/storage.py:88-93` creates `ir_edges` with no
FK. Orphan edges can exist after record deletion; graph traversal in
`TraceGraph` can dereference missing records.

**Change.** Add an online schema migration that:
1. Deletes orphan rows (`delete from ir_edges where src_id not in (select id from ir_records) or dst_id not in (select id from ir_records)`).
2. Renames the existing `ir_edges` table to `ir_edges_legacy`.
3. Creates a new `ir_edges` with FKs:
   `foreign key (src_id) references ir_records(id) on delete cascade`,
   same for `dst_id`.
4. Copies rows from `ir_edges_legacy` into `ir_edges`.
5. Drops the legacy table.
6. Rebuilds the two existing indexes.

Wrap all six steps in one transaction. Run on schema-init for any database
where the FK is missing (detect via `pragma foreign_key_list(ir_edges)`).

**Verification.**

Add `tests/audit/test_ir_edges_fk_migration.py`:
- create a DB with the old schema (FK missing), insert an orphan edge,
  run the migration, assert orphan is gone and `pragma foreign_key_list`
  reports the FK.
- delete a record after migration, assert dependent edges are removed
  via cascade.

```bash
.venv/bin/python -m pytest tests/audit/test_ir_edges_fk_migration.py -q
.venv/bin/python -m pytest test_seam_all/ -q
```

### Fix 8 — MCP stdin line-size cap (P1)

**Problem.** `seam_runtime/mcp_protocol.py:46` reads `for line in
input_stream`. Unbounded line length. A malicious or buggy client can
exhaust memory.

**Change.** Read manually with a per-line byte cap:

```python
MAX_MCP_LINE_BYTES = 5_000_000  # 5 MiB default; cap protects against memory exhaustion

def _read_capped_lines(stream: TextIO, max_bytes: int) -> Iterator[str]:
    while True:
        line = stream.readline(max_bytes + 1)
        if not line:
            return
        if len(line.encode("utf-8")) > max_bytes:
            yield "__SEAM_MCP_OVERSIZED_LINE__"
            continue
        yield line
```

In `run_mcp_server`, route oversized lines to a JSON-RPC error response
(`-32600 Invalid Request`, with `data: {"reason": "request too large"}`)
instead of attempting to parse.

Make the cap overridable via `SEAM_MCP_MAX_LINE_BYTES` for benchmark/test
runs that legitimately exceed 5 MiB.

**Verification.**

Add `tests/audit/test_mcp_line_cap.py`:
- normal-size JSON-RPC line — parses normally.
- 10 MiB line — receives `-32600` error, no exception, no memory blowup.
- env override `SEAM_MCP_MAX_LINE_BYTES=20000000` — 10 MiB line parses.

```bash
.venv/bin/python -m pytest tests/audit/test_mcp_line_cap.py -q
.venv/bin/python -m pytest tests/ -k mcp -q
```

### Fix 9 — MCP `artifact_path` containment check (P1)

**Problem.** `seam_runtime/mcp.py:404-415` resolves an arbitrary path read
from SQLite. No containment vs an allowed root.

**Change.** Require the resolved path to live under `SEAM_SURFACE_ROOT`
(default: the SQLite store's directory). Reject anything outside with a
`PermissionError`-style JSON-RPC response.

```python
def _resolve_registered_surface_path(runtime, surface_ref):
    ...
    artifact_path = Path(str(row.get("artifact_path") or ""))
    resolved = artifact_path.resolve(strict=False)
    allowed_root = Path(os.environ.get("SEAM_SURFACE_ROOT", Path(runtime.store.path).parent)).resolve()
    try:
        resolved.relative_to(allowed_root)
    except ValueError:
        raise PermissionError(
            f"Surface artifact path {resolved} is outside the allowed root {allowed_root}. "
            "Set SEAM_SURFACE_ROOT to expand the allowed root if intentional."
        )
    if not resolved.exists():
        raise FileNotFoundError(...)
    return resolved
```

**Verification.**

Add `tests/audit/test_mcp_artifact_containment.py`:
- registered path under the store dir — resolves normally.
- registered path at `/etc/passwd` (or `tmp_path / ".." / "outside"`) —
  raises PermissionError.
- env override `SEAM_SURFACE_ROOT=/` — restores legacy permissive behavior
  for operator opt-in.

```bash
.venv/bin/python -m pytest tests/audit/test_mcp_artifact_containment.py -q
.venv/bin/python -m pytest tests/ -k mcp -q
```

## Final Score Run (after all P3 fixes land)

This is a single full-dataset run per `SOP_TRACK_M_P1_REAL_BENCHMARK_RUNS.md`,
with all P3 score-mover flags enabled:

```bash
export LOCOMO_DATASET_PATH=/home/terrabyte/seam_benchmarks/track_m/locomo/locomo10.json
export OPENAI_API_KEY=<from local env, do not commit>
export SEAM_EMBEDDING_PROVIDER=sentence-transformers
export SEAM_EMBEDDING_MODEL=BAAI/bge-small-en-v1.5

.venv/bin/python -m seam bench external locomo \
  --dataset-path "$LOCOMO_DATASET_PATH" \
  --adapter seam \
  --judge openai --judge-model gpt-4o-mini \
  --judge-cross openai --judge-cross-model gpt-4o \
  --answerer openai --answerer-model gpt-4o-mini \
  --decomposer openai --decomposer-model gpt-4o-mini \
  --workers 4 \
  --output /tmp/seam-track-m/locomo-seam-p3.json
```

Seal, verify, diff vs the P2-only baseline:

```bash
.venv/bin/python -m seam bench seal /tmp/seam-track-m/locomo-seam-p3.json \
  --level BIL-2 --output /tmp/seam-track-m/locomo-seam-p3.bil2.json
.venv/bin/python -m seam bench verify /tmp/seam-track-m/locomo-seam-p3.bil2.json
.venv/bin/python -m seam benchmark diff \
  /tmp/seam-track-m/locomo-seam-p2-baseline.json \
  /tmp/seam-track-m/locomo-seam-p3.json
```

Quote only the *per-category* deltas, never just the mean. A mean delta
that hides a multi-hop drop is not an improvement.

## Required Verification Before Handback

```bash
git diff --check
.venv/bin/python -m pytest tests/audit/test_bm25_lexical_channel.py -q
.venv/bin/python -m pytest tests/audit/test_locomo_adapter_real_embedding.py -q
.venv/bin/python -m pytest tests/audit/test_locomo_decomposer.py -q
.venv/bin/python -m pytest tests/audit/test_temporal_filter.py -q
.venv/bin/python -m pytest tests/audit/test_abstain_threshold.py -q
.venv/bin/python -m pytest tests/audit/test_chroma_sync_default.py -q
.venv/bin/python -m pytest tests/audit/test_ir_edges_fk_migration.py -q
.venv/bin/python -m pytest tests/audit/test_mcp_line_cap.py -q
.venv/bin/python -m pytest tests/audit/test_mcp_artifact_containment.py -q
.venv/bin/python -m pytest test_seam_all/ tools/history/test_history_tools.py tools/streams/ tests/ -q
.venv/bin/python -m py_compile seam.py
.venv/bin/python -m compileall -q seam_runtime benchmarks tools scripts installers
python3 -m tools.history.verify_integrity
python3 -m tools.history.verify_routing
python3 -m tools.history.verify_continuity
python3 -m tools.streams.verify_streams
.venv/bin/python -m seam bench external --quickstart locomo --judge stub --format json
```

## Final Report Format

```text
===== DEEPSEEK REPORT: TRACK_M_P3_LOCOMO_SCORE_IMPROVEMENTS =====
branch: deepseek/track-m-p3-locomo-score-improvements
head: <sha>
base: main

score_movers_landed:
- F1 bm25_lexical: <commit, files, quickstart_cr: <value>>
- F2 real_embedding: <commit, files, embedding_model: <name>>
- F3 decomposer: <commit, files, default: off>
- F4 temporal_filter: <commit, files>
- F5 abstain_threshold: <commit, files, default_threshold: 0.0>

architectural_hygiene_landed:
- F6 chroma_sync_default: <commit>
- F7 ir_edges_fk: <commit, orphans_purged: <n>>
- F8 mcp_line_cap: <commit, default_bytes: 5000000>
- F9 mcp_artifact_containment: <commit>

quickstart_after_all_fixes:
- context_recall_mean: <value>
- per_category: <dict snapshot>

regressions_introduced:
- <fix_id: description or none>

deferred_for_operator:
- full official LoCoMo run with real judges (requires operator API key approval)
- abstain_threshold tuning on held-out split
- score-weight retuning

verification:
- <command> -> <result>

changed_files:
- <path: lines added/removed>

artifacts_not_committed:
- <none expected; final-run bundles live outside the repo>

open_questions:
- <question or none>
```
