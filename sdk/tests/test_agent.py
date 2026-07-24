from __future__ import annotations

import asyncio
from typing import Any

from seam_client import AgentMemory, AsyncAgentMemory, ContextResult, RememberReceipt


def _receipt() -> RememberReceipt:
    return RememberReceipt(
        receipt_id="rcpt_test",
        accepted=True,
        memory_count=2,
        namespace="my-agent",
        scope="thread",
        session_id="thread-7",
        api_version="v1",
    )


def _context(text: str) -> ContextResult:
    return ContextResult(
        query="question",
        namespace="my-agent",
        scope="thread",
        session_id="thread-7",
        context=text,
        memories=(),
        api_version="v1",
    )


class StubClient:
    def __init__(self) -> None:
        self.remember_calls: list[tuple[str, dict[str, Any]]] = []
        self.context_calls: list[tuple[str, dict[str, Any]]] = []

    def remember(self, text: str, **kwargs: Any) -> RememberReceipt:
        self.remember_calls.append((text, kwargs))
        return _receipt()

    def context(self, query: str, **kwargs: Any) -> ContextResult:
        self.context_calls.append((query, kwargs))
        return _context("- Use evidence.")


class AsyncStubClient:
    def __init__(self) -> None:
        self.remember_calls: list[tuple[str, dict[str, Any]]] = []

    async def remember(self, text: str, **kwargs: Any) -> RememberReceipt:
        self.remember_calls.append((text, kwargs))
        return _receipt()

    async def context(self, query: str, **kwargs: Any) -> ContextResult:
        return _context("- Use evidence.")


def test_agent_memory_hooks_are_framework_neutral() -> None:
    client = StubClient()
    memory = AgentMemory(
        client=client,  # type: ignore[arg-type]
        namespace="my-agent",
        session_id="thread-7",
        agent_id="researcher",
    )
    messages = [{"role": "user", "content": "What changed?"}]
    augmented = memory.augment_messages(messages, user_input="What changed?")
    assert augmented[0] == {
        "role": "system",
        "content": "Relevant long-term memory:\n- Use evidence.",
    }
    assert augmented[1:] == messages
    assert messages == [{"role": "user", "content": "What changed?"}]

    receipt = memory.after_turn("What changed?", "The release was verified.")
    assert receipt.receipt_id == "rcpt_test"
    assert client.remember_calls[0][0] == (
        "User: What changed?\nAssistant: The release was verified."
    )
    assert client.remember_calls[0][1]["agent_id"] == "researcher"


def test_async_agent_memory_hooks() -> None:
    async def run() -> None:
        client = AsyncStubClient()
        memory = AsyncAgentMemory(
            client=client,  # type: ignore[arg-type]
            namespace="my-agent",
            session_id="thread-7",
        )
        augmented = await memory.augment_messages(
            [{"role": "user", "content": "What changed?"}],
            user_input="What changed?",
        )
        assert augmented[0]["role"] == "system"
        receipt = await memory.after_turn("Question", "Answer")
        assert receipt.accepted is True
        assert client.remember_calls[0][0] == "User: Question\nAssistant: Answer"

    asyncio.run(run())
