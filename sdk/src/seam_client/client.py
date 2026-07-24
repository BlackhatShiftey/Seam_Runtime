from __future__ import annotations

import os
from types import TracebackType
from typing import Any

import httpx

from ._transport import connection_error, headers, payload
from .models import ContextResult, Health, RecallResult, RememberReceipt

DEFAULT_BASE_URL = "http://127.0.0.1:8765"


class SeamClient:
    """Synchronous client for SEAM's stable public agent-memory API."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str | None = None,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=headers(api_key),
            timeout=timeout,
            transport=transport,
        )

    @classmethod
    def from_env(cls, **kwargs: Any) -> SeamClient:
        return cls(
            base_url=os.environ.get("SEAM_BASE_URL", DEFAULT_BASE_URL),
            api_key=os.environ.get("SEAM_API_TOKEN"),
            **kwargs,
        )

    def health(self) -> Health:
        return Health.from_dict(self._request("GET", "/v1/health"))

    def remember(
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
        return RememberReceipt.from_dict(self._request("POST", "/v1/memories", json=body))

    def recall(
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
            self._request("POST", "/v1/memories/recall", json=body)
        )

    def context(
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
        return ContextResult.from_dict(self._request("POST", "/v1/context", json=body))

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> SeamClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise connection_error(exc) from exc
        return payload(response)


def _partition(
    *,
    namespace: str,
    scope: str,
    session_id: str | None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"namespace": namespace, "scope": scope}
    if session_id is not None:
        body["session_id"] = session_id
    return body
