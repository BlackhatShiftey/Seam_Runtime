from __future__ import annotations

import httpx
import pytest

from seam_client import (
    APIError,
    AuthenticationError,
    RateLimitError,
    SeamClient,
)


def _memory() -> dict[str, object]:
    return {
        "id": "mem_1234567890abcdef12345678",
        "text": "The operator prefers concise answers.",
        "score": 0.91,
        "created_at": "2026-07-24T12:00:00Z",
    }


def test_sync_client_memory_flow_and_bearer_auth() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.headers["authorization"] == "Bearer test-token"
        if request.url.path == "/v1/health":
            return httpx.Response(200, json={"status": "ok", "api_version": "v1"})
        body = _json(request)
        assert body["namespace"] == "demo-agent"
        assert body["scope"] == "thread"
        assert body["session_id"] == "session-1"
        if request.url.path == "/v1/memories":
            assert body["agent_id"] == "demo-agent"
            return httpx.Response(
                200,
                json={
                    "api_version": "v1",
                    "accepted": True,
                    "receipt_id": "rcpt_123",
                    "memory_count": 5,
                    "namespace": "demo-agent",
                    "scope": "thread",
                    "session_id": "session-1",
                },
            )
        if request.url.path == "/v1/memories/recall":
            return httpx.Response(
                200,
                json={
                    "api_version": "v1",
                    "query": body["query"],
                    "namespace": "demo-agent",
                    "scope": "thread",
                    "session_id": "session-1",
                    "memories": [_memory()],
                },
            )
        if request.url.path == "/v1/context":
            return httpx.Response(
                200,
                json={
                    "api_version": "v1",
                    "query": body["query"],
                    "namespace": "demo-agent",
                    "scope": "thread",
                    "session_id": "session-1",
                    "context": "- The operator prefers concise answers.",
                    "memories": [_memory()],
                },
            )
        raise AssertionError(request.url.path)

    with SeamClient(
        base_url="https://seam.example",
        api_key="test-token",
        transport=httpx.MockTransport(handler),
    ) as client:
        assert client.health().status == "ok"
        receipt = client.remember(
            "User likes concise answers.",
            namespace="demo-agent",
            session_id="session-1",
            agent_id="demo-agent",
        )
        assert receipt.accepted is True
        assert receipt.receipt_id == "rcpt_123"
        recalled = client.recall(
            "answer style",
            namespace="demo-agent",
            session_id="session-1",
        )
        assert recalled.memories[0].text == "The operator prefers concise answers."
        context = client.context(
            "answer style",
            namespace="demo-agent",
            session_id="session-1",
        )
        assert context.context.startswith("- ")

    assert [request.url.path for request in requests] == [
        "/v1/health",
        "/v1/memories",
        "/v1/memories/recall",
        "/v1/context",
    ]


@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [
        (401, AuthenticationError),
        (403, AuthenticationError),
        (429, RateLimitError),
        (500, APIError),
    ],
)
def test_sync_client_maps_api_errors(
    status_code: int,
    error_type: type[APIError],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"detail": "request rejected"})

    with (
        SeamClient(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(error_type) as captured,
    ):
        client.health()
    assert captured.value.status_code == status_code
    assert str(captured.value) == "request rejected"


def test_sync_client_rejects_invalid_success_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=["not", "an", "object"])

    with (
        SeamClient(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(APIError, match="unexpected response shape"),
    ):
        client.health()


def _json(request: httpx.Request) -> dict[str, object]:
    import json

    payload = json.loads(request.content)
    assert isinstance(payload, dict)
    return payload
