from __future__ import annotations

import os
from types import TracebackType
from typing import Any

import httpx

from ._transport import connection_error, headers, payload
from .client import DEFAULT_BASE_URL, _partition
from .models import ContextResult, Health, RecallResult, RememberReceipt


class AsyncSeamClient:
    """Asynchronous client for SEAM's stable public agent-memory API."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str | None = None,
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers=headers(api_key),
            timeout=timeout,
            transport=transport,
        )

    @classmethod
    def from_env(cls, **kwargs: Any) -> AsyncSeamClient:
        return cls(
            base_url=os.environ.get("SEAM_BASE_URL", DEFAULT_BASE_URL),
            api_key=os.environ.get("SEAM_API_TOKEN"),
            **kwargs,
        )

    async def health(self) -> Health:
        return Health.from_dict(await self._request("GET", "/v1/health"))

    async def remember(
        self,
        text: str,
        *,
        namespace: str = "default",
        scope: str = "thread",
        session_id: str | None = None,
        agent_id: str | None = None,
    ) -> RememberReceipt:
        body = _partition(
            namespace=namespace,
            scope=scope,
            session_id=session_id,
        )
        body["text"] = text
        if agent_id is not None:
            body["agent_id"] = agent_id
        return RememberReceipt.from_dict(
            await self._request("POST", "/v1/memories", json=body)
        )

    async def recall(
        self,
        query: str,
        *,
        namespace: str = "default",
        scope: str = "thread",
        session_id: str | None = None,
        limit: int = 5,
    ) -> RecallResult:
        body = _partition(
            namespace=namespace,
            scope=scope,
            session_id=session_id,
        )
        body.update({"query": query, "limit": limit})
        return RecallResult.from_dict(
            await self._request("POST", "/v1/memories/recall", json=body)
        )

    async def context(
        self,
        query: str,
        *,
        namespace: str = "default",
        scope: str = "thread",
        session_id: str | None = None,
        limit: int = 5,
        max_chars: int = 8_000,
    ) -> ContextResult:
        body = _partition(
            namespace=namespace,
            scope=scope,
            session_id=session_id,
        )
        body.update({"query": query, "limit": limit, "max_chars": max_chars})
        return ContextResult.from_dict(
            await self._request("POST", "/v1/context", json=body)
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncSeamClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise connection_error(exc) from exc
        return payload(response)
