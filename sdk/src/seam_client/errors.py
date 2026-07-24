from __future__ import annotations

from typing import Any


class SeamError(Exception):
    """Base exception raised by the public SEAM SDK."""


class ConnectionError(SeamError):
    """The SDK could not reach the configured SEAM service."""


class APIError(SeamError):
    """The SEAM service returned an unsuccessful response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        request_id: str | None = None,
        detail: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id
        self.detail = detail


class AuthenticationError(APIError):
    """The service rejected the configured bearer token."""


class RateLimitError(APIError):
    """The service rate limit was exceeded."""
