from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    return value


def _optional_string(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _string(value, field)


@dataclass(frozen=True)
class Health:
    status: str
    api_version: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Health:
        return cls(
            status=_string(payload.get("status"), "status"),
            api_version=_string(payload.get("api_version"), "api_version"),
        )


@dataclass(frozen=True)
class RememberReceipt:
    receipt_id: str
    accepted: bool
    memory_count: int
    namespace: str
    scope: str
    session_id: str | None
    api_version: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> RememberReceipt:
        accepted = payload.get("accepted")
        memory_count = payload.get("memory_count")
        if not isinstance(accepted, bool):
            raise ValueError("accepted must be a boolean")
        if isinstance(memory_count, bool) or not isinstance(memory_count, int):
            raise ValueError("memory_count must be an integer")
        return cls(
            receipt_id=_string(payload.get("receipt_id"), "receipt_id"),
            accepted=accepted,
            memory_count=memory_count,
            namespace=_string(payload.get("namespace"), "namespace"),
            scope=_string(payload.get("scope"), "scope"),
            session_id=_optional_string(payload.get("session_id"), "session_id"),
            api_version=_string(payload.get("api_version"), "api_version"),
        )


@dataclass(frozen=True)
class Memory:
    id: str
    text: str
    score: float
    created_at: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Memory:
        score = payload.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise ValueError("score must be a number")
        return cls(
            id=_string(payload.get("id"), "id"),
            text=_string(payload.get("text"), "text"),
            score=float(score),
            created_at=_string(payload.get("created_at"), "created_at"),
        )


@dataclass(frozen=True)
class RecallResult:
    query: str
    namespace: str
    scope: str
    session_id: str | None
    memories: tuple[Memory, ...]
    api_version: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> RecallResult:
        raw_memories = payload.get("memories")
        if not isinstance(raw_memories, list):
            raise ValueError("memories must be a list")
        return cls(
            query=_string(payload.get("query"), "query"),
            namespace=_string(payload.get("namespace"), "namespace"),
            scope=_string(payload.get("scope"), "scope"),
            session_id=_optional_string(payload.get("session_id"), "session_id"),
            memories=tuple(Memory.from_dict(item) for item in raw_memories),
            api_version=_string(payload.get("api_version"), "api_version"),
        )


@dataclass(frozen=True)
class ContextResult:
    query: str
    namespace: str
    scope: str
    session_id: str | None
    context: str
    memories: tuple[Memory, ...]
    api_version: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ContextResult:
        raw_memories = payload.get("memories")
        if not isinstance(raw_memories, list):
            raise ValueError("memories must be a list")
        return cls(
            query=_string(payload.get("query"), "query"),
            namespace=_string(payload.get("namespace"), "namespace"),
            scope=_string(payload.get("scope"), "scope"),
            session_id=_optional_string(payload.get("session_id"), "session_id"),
            context=_string(payload.get("context"), "context"),
            memories=tuple(Memory.from_dict(item) for item in raw_memories),
            api_version=_string(payload.get("api_version"), "api_version"),
        )
