"""Exception hierarchy for the Asher SDK.

Every error the SDK raises is a subclass of :class:`AsherError`, and carries
the HTTP status code (when one was received), the server's ``message``, and
the raw parsed JSON response body (when available), so callers can inspect
details beyond what the typed attributes expose.
"""

from typing import Any, Dict, Optional


class AsherError(Exception):
    """Base class for all errors raised by the Asher SDK."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.body = body

    def __str__(self) -> str:
        if self.status_code is not None:
            return f"[{self.status_code}] {self.message}"
        return self.message

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(message={self.message!r}, "
            f"status_code={self.status_code!r})"
        )


class AuthenticationError(AsherError):
    """HTTP 401 — missing or invalid API key."""


class PermissionError(AsherError):
    """HTTP 403 — the API key lacks a required scope."""


class NotFoundError(AsherError):
    """HTTP 404 — the requested resource does not exist."""


class InvalidRequestError(AsherError):
    """HTTP 400 / 422 — request validation failed.

    The Asher API returns generic messages for these (e.g. ``"Bad
    request."``) rather than field-level errors, so this exception does not
    attempt to expose per-field details — see ``.message`` / ``.body``.
    """


class RateLimitError(AsherError):
    """HTTP 429 — too many requests.

    ``retry_after`` mirrors the ``retry_after`` field from the response body
    (seconds), when the server included one.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        body: Optional[Dict[str, Any]] = None,
        retry_after: Optional[float] = None,
    ) -> None:
        super().__init__(message, status_code=status_code, body=body)
        self.retry_after = retry_after

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(message={self.message!r}, "
            f"status_code={self.status_code!r}, retry_after={self.retry_after!r})"
        )


class APIError(AsherError):
    """Any other non-2xx response not covered by a more specific subclass."""


class ConnectionError(AsherError):
    """A network-level failure (no HTTP response received), raised after all
    configured retries are exhausted."""


class SignatureVerificationError(AsherError):
    """Raised by :meth:`asher.Webhook.construct_event` when signature
    verification fails (malformed header, signature mismatch, or an
    out-of-tolerance timestamp). ``.message`` indicates which check failed.
    """
