"""Regression tests for SEAM LoCoMo adapter retrieved evidence text."""

from benchmarks.external.common.types import ConversationTurn
from benchmarks.external.locomo.adapters.seam import SeamLocomoAdapter


def test_locomo_adapter_returns_plain_evidence_text(tmp_path):
    adapter = SeamLocomoAdapter(db_path=str(tmp_path), budget=2000)
    scope_id = "evidence-text"

    adapter.reset(scope_id)
    adapter.ingest_turn(
        scope_id,
        ConversationTurn(
            speaker="user",
            text="I moved to Tokyo in April and my cat is named Pixel.",
            timestamp="2026-01-01T00:00:00Z",
        ),
    )

    answer = adapter.answer(scope_id, "Where did I move in April?")

    assert "Tokyo" in answer.retrieved_context
    assert "moved to Tokyo" in answer.retrieved_context
    assert answer.generated_answer is None
    assert answer.retrieval_latency_ms >= 0.0


def test_locomo_adapter_respects_context_budget(tmp_path):
    adapter = SeamLocomoAdapter(db_path=str(tmp_path), budget=120)
    scope_id = "budget"

    adapter.reset(scope_id)
    adapter.ingest_turn(
        scope_id,
        ConversationTurn(
            speaker="user",
            text="Tokyo " * 200,
            timestamp="2026-01-01T00:00:00Z",
        ),
    )

    answer = adapter.answer(scope_id, "Tokyo?")

    assert len(answer.retrieved_context) <= 120


def test_locomo_adapter_empty_scope_returns_empty_context(tmp_path):
    adapter = SeamLocomoAdapter(db_path=str(tmp_path), budget=2000)

    answer = adapter.answer("empty", "What do you remember?")

    assert answer.retrieved_context == ""
    assert answer.generated_answer is None
