from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .async_client import AsyncSeamClient
from .client import SeamClient
from .models import RememberReceipt


class SupportsMemory(Protocol):
    def remember(self, text: str, **kwargs: Any) -> RememberReceipt: ...

    def context(self, query: str, **kwargs: Any) -> Any: ...


@dataclass
class AgentMemory:
    """Framework-neutral memory hooks for a synchronous custom agent."""

    client: SeamClient
    namespace: str
    session_id: str | None = None
    agent_id: str | None = None
    scope: str = "thread"
    recall_limit: int = 5
    max_context_chars: int = 8_000

    def remember(self, text: str) -> RememberReceipt:
        return self.client.remember(
            text,
            namespace=self.namespace,
            scope=self.scope,
            session_id=self.session_id,
            agent_id=self.agent_id,
        )

    def before_turn(self, user_input: str) -> str:
        return self.client.context(
            user_input,
            namespace=self.namespace,
            scope=self.scope,
            session_id=self.session_id,
            limit=self.recall_limit,
            max_chars=self.max_context_chars,
        ).context

    def after_turn(self, user_input: str, assistant_output: str) -> RememberReceipt:
        transcript = f"User: {user_input}\nAssistant: {assistant_output}"
        return self.remember(transcript)

    def system_message(self, user_input: str) -> dict[str, str] | None:
        context = self.before_turn(user_input)
        if not context:
            return None
        return {
            "role": "system",
            "content": "Relevant long-term memory:\n" + context,
        }

    def augment_messages(
        self,
        messages: list[dict[str, str]],
        *,
        user_input: str,
    ) -> list[dict[str, str]]:
        memory_message = self.system_message(user_input)
        if memory_message is None:
            return list(messages)
        return [memory_message, *messages]


@dataclass
class AsyncAgentMemory:
    """Framework-neutral memory hooks for an asynchronous custom agent."""

    client: AsyncSeamClient
    namespace: str
    session_id: str | None = None
    agent_id: str | None = None
    scope: str = "thread"
    recall_limit: int = 5
    max_context_chars: int = 8_000

    async def remember(self, text: str) -> RememberReceipt:
        return await self.client.remember(
            text,
            namespace=self.namespace,
            scope=self.scope,
            session_id=self.session_id,
            agent_id=self.agent_id,
        )

    async def before_turn(self, user_input: str) -> str:
        result = await self.client.context(
            user_input,
            namespace=self.namespace,
            scope=self.scope,
            session_id=self.session_id,
            limit=self.recall_limit,
            max_chars=self.max_context_chars,
        )
        return result.context

    async def after_turn(
        self,
        user_input: str,
        assistant_output: str,
    ) -> RememberReceipt:
        transcript = f"User: {user_input}\nAssistant: {assistant_output}"
        return await self.remember(transcript)

    async def system_message(self, user_input: str) -> dict[str, str] | None:
        context = await self.before_turn(user_input)
        if not context:
            return None
        return {
            "role": "system",
            "content": "Relevant long-term memory:\n" + context,
        }

    async def augment_messages(
        self,
        messages: list[dict[str, str]],
        *,
        user_input: str,
    ) -> list[dict[str, str]]:
        memory_message = await self.system_message(user_input)
        if memory_message is None:
            return list(messages)
        return [memory_message, *messages]
