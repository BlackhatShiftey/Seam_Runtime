from __future__ import annotations

import asyncio

import httpx

from seam_client import AsyncSeamClient


def test_async_client_memory_flow() -> None:
    async def run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/v1/health":
                return httpx.Response(200, json={"status": "ok", "api_version": "v1"})
            if request.url.path == "/v1/memories":
                return httpx.Response(
                    200,
                    json={
                        "api_version": "v1",
                        "accepted": True,
                        "receipt_id": "rcpt_async",
                        "memory_count": 4,
                        "namespace": "async-agent",
                        "scope": "thread",
                        "session_id": None,
                    },
                )
            if request.url.path == "/v1/memories/recall":
                return httpx.Response(
                    200,
                    json={
                        "api_version": "v1",
                        "query": "preference",
                        "namespace": "async-agent",
                        "scope": "thread",
                        "session_id": None,
                        "memories": [],
                    },
                )
            if request.url.path == "/v1/context":
                return httpx.Response(
                    200,
                    json={
                        "api_version": "v1",
                        "query": "preference",
                        "namespace": "async-agent",
                        "scope": "thread",
                        "session_id": None,
                        "context": "",
                        "memories": [],
                    },
                )
            raise AssertionError(request.url.path)

        async with AsyncSeamClient(
            base_url="https://seam.example",
            transport=httpx.MockTransport(handler),
        ) as client:
            assert (await client.health()).api_version == "v1"
            assert (
                await client.remember("remember me", namespace="async-agent")
            ).receipt_id == "rcpt_async"
            assert (
                await client.recall("preference", namespace="async-agent")
            ).memories == ()
            assert (
                await client.context("preference", namespace="async-agent")
            ).context == ""

    asyncio.run(run())
