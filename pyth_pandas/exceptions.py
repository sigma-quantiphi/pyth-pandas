"""Pyth-specific exception hierarchy."""

from __future__ import annotations


class PythError(Exception):
    """Base exception for all pyth-pandas errors."""


class PythAPIError(PythError):
    """Raised when the API returns a non-2xx response."""

    def __init__(self, status_code: int, url: str, detail: object) -> None:
        self.status_code = status_code
        self.url = url
        self.detail = detail
        super().__init__(f"HTTP {status_code} from {url}: {detail}")


class PythAuthError(PythAPIError):
    """Raised on 401/403 responses, or when required credentials are missing."""

    def __init__(
        self,
        status_code: int = 0,
        url: str = "",
        detail: object = "",
    ) -> None:
        super().__init__(status_code, url, detail)


class PythRateLimitError(PythAPIError):
    """Raised on 429 Too Many Requests."""
