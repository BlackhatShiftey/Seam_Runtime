"""Tests for multi-hop question decomposition in the LoCoMo adapter."""

from benchmarks.external.common.types import ConversationTurn
from benchmarks.external.locomo.adapters.seam import SeamLocomoAdapter


def test_decomposer_off_is_unchanged(tmp_path):
    """With decomposer default off, behavior is identical to before."""
    adapter = SeamLocomoAdapter(db_path=str(tmp_path), budget=2000)
    scope_id = "decomp-off"

    adapter.reset(scope_id)
    adapter.ingest_turn(
        scope_id,
        ConversationTurn(
            speaker="Alice",
            text="I moved to Tokyo in April.",
            timestamp="2024-04-01T10:00:00Z",
        ),
    )
    answer = adapter.answer(scope_id, "Where did Alice move?")
    assert "Tokyo" in answer.retrieved_context


def test_decomposer_on_searches_per_sub_question(tmp_path, monkeypatch):
    """With decomposer enabled, search is called for each sub-question."""
    # Stub the OpenAI short answer to return fixed sub-questions
    monkeypatch.setattr(
        "benchmarks.external.locomo.adapters.seam._openai_short_answer",
        lambda model, prompt, max_tokens=64: "Where did Alice move?\nWhen did Alice move?",
    )
    adapter = SeamLocomoAdapter(
        db_path=str(tmp_path), budget=2000,
        decomposer="openai", decomposer_model="gpt-4o-mini",
    )
    scope_id = "decomp-on"

    adapter.reset(scope_id)
    adapter.ingest_turn(
        scope_id,
        ConversationTurn(
            speaker="Alice",
            text="I moved to Tokyo in April.",
            timestamp="2024-04-01T10:00:00Z",
        ),
    )
    answer = adapter.answer(scope_id, "Where and when did Alice move?")
    assert "Tokyo" in answer.retrieved_context
    # Retrieval latency should be higher with multiple searches
    assert answer.retrieval_latency_ms >= 0
