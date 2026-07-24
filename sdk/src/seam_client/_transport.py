from __future__ import annotations

from typing import Any

import httpx

from .errors import APIError, AuthenticationError, ConnectionError, RateLimitError


def headers(api_key: str | None) -> dict[str, str]:
    resolved = {"accept": "application/json"}
    if api_key:
        resolved["authorization"] = f"Bearer {api_key}"
    return resolved


def payload(response: httpx.Response) -> dict[str, Any]:
    if response.is_success:
        try:
            parsed = response.json()
        except ValueError as exc:
            raise APIError(
                "SEAM returned invalid JSON",
                status_code=response.status_code,
                request_id=response.headers.get("x-request-id"),
            ) from exc
        if not isinstance(parsed, dict):
            raise APIError(
                "SEAM returned an unexpected response shape",
                status_code=response.status_code,
                request_id=response.headers.get("x-request-id"),
                detail=parsed,
            )
        return parsed

    detail: Any = None
    try:
        detail = response.json()
    except ValueError:
        detail = response.text[:500]
    message = _error_message(detail, response.status_code)
    error_type: type[APIError]
    if response.status_code in {401, 403}:
        error_type = AuthenticationError
    elif response.status_code == 429:
        error_type = RateLimitError
    else:
        error_type = APIError
    raise error_type(
        message,
        status_code=response.status_code,
        request_id=response.headers.get("x-request-id"),
        detail=detail,
    )


def connection_error(exc: httpx.HTTPError) -> ConnectionError:
    return ConnectionError(f"Could not reach SEAM: {exc}")


def _error_message(detail: Any, status_code: int) -> str:
    if isinstance(detail, dict):
        message = detail.get("detail") or detail.get("message")
        if isinstance(message, str) and message:
            return message
    if isinstance(detail, str) and detail:
        return detail
    return f"SEAM request failed with HTTP {status_code}"
