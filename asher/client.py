"""The Asher API client."""

import random
import time
import uuid
from typing import Any, Dict, Optional

import requests

from ._version import __version__
from .errors import (
    APIError,
    AsherError,
    AuthenticationError,
    ConnectionError,
    InvalidRequestError,
    NotFoundError,
)
from .errors import PermissionError as AsherPermissionError
from .errors import RateLimitError
from .resources.customers import CustomersResource
from .resources.invoices import InvoicesResource
from .resources.payment_links import PaymentLinksResource
from .resources.transactions import TransactionsResource

DEFAULT_BASE_URL = "https://api.asher.cash"
API_VERSION_PATH = "/v1"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 2

_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
_BACKOFF_BASE_SECONDS = 0.5
_BACKOFF_CAP_SECONDS = 8.0

_ERROR_CLASSES_BY_STATUS = {
    401: AuthenticationError,
    403: AsherPermissionError,
    404: NotFoundError,
    400: InvalidRequestError,
    422: InvalidRequestError,
}


class Client:
    """The main entry point for the Asher SDK.

    Example:
        >>> import asher
        >>> client = asher.Client(api_key="sk_test_...")
        >>> result = client.payment_links.list()
        >>> for link in result.data:
        ...     print(link.slug, link.title)

    Args:
        api_key: Your Asher secret key (``sk_test_...`` or ``sk_live_...``).
            The key itself determines which environment (sandbox/live) the
            request operates in.
        base_url: Override the API host. Defaults to ``https://api.asher.cash``.
            The ``/v1`` version prefix is always appended after this host,
            same as Asher's other SDKs, so overriding this to point at a
            local/staging backend still hits e.g. ``{base_url}/v1/payment-links``.
        max_retries: Maximum number of retries for retryable failures
            (network errors, 429, and 500/502/503/504). Defaults to 2 (i.e.
            3 attempts total).
        timeout: Per-request timeout in seconds, passed to ``requests``.
            Defaults to 30 seconds.
    """

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        max_retries: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required.")

        self.api_key = api_key
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.max_retries = DEFAULT_MAX_RETRIES if max_retries is None else max_retries
        self.timeout = DEFAULT_TIMEOUT if timeout is None else timeout

        self._session = requests.Session()

        self.payment_links = PaymentLinksResource(self)
        self.invoices = InvoicesResource(self)
        self.transactions = TransactionsResource(self)
        self.customers = CustomersResource(self)

    # -- internal transport -------------------------------------------------

    def request_json(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Perform a request and return the parsed JSON response body."""
        response = self._send(
            method,
            path,
            params=params,
            json_body=json_body,
            idempotency_key=idempotency_key,
        )
        if not response.content:
            return {}
        try:
            data: Dict[str, Any] = response.json()
        except ValueError:
            return {}
        return data

    def request_raw(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """Perform a request and return the raw response body bytes
        (used for the CSV transaction export, which isn't JSON)."""
        response = self._send(method, path, params=params)
        return response.content

    def _send(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> requests.Response:
        url = f"{self.base_url}{API_VERSION_PATH}{path}"
        method_upper = method.upper()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "User-Agent": f"asher-python/{__version__}",
        }
        if method_upper == "POST":
            headers["Idempotency-Key"] = idempotency_key or str(uuid.uuid4())

        clean_params = (
            {k: v for k, v in params.items() if v is not None} if params else None
        )

        max_attempts = self.max_retries + 1
        last_network_error: Optional[BaseException] = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = self._session.request(
                    method_upper,
                    url,
                    params=clean_params,
                    json=json_body,
                    headers=headers,
                    timeout=self.timeout,
                )
            except requests.exceptions.RequestException as exc:
                last_network_error = exc
                if attempt == max_attempts:
                    raise ConnectionError(
                        f"Network error after {attempt} attempt(s): {exc}"
                    ) from exc
                time.sleep(self._backoff_seconds(attempt))
                continue

            if response.status_code < 300:
                return response

            if self._is_retryable(response.status_code) and attempt < max_attempts:
                time.sleep(self._backoff_seconds(attempt, response=response))
                continue

            raise self._build_error(response)

        # Unreachable, but keeps mypy happy about the return type.
        if last_network_error is not None:
            raise ConnectionError(str(last_network_error))
        raise AsherError("Request failed for an unknown reason.")

    @staticmethod
    def _is_retryable(status_code: int) -> bool:
        return status_code in _RETRYABLE_STATUS_CODES

    @staticmethod
    def _backoff_seconds(
        attempt: int, response: Optional[requests.Response] = None
    ) -> float:
        if response is not None and response.status_code == 429:
            retry_after = Client._retry_after_from_response(response)
            if retry_after is not None:
                return max(0.0, retry_after)

        backoff = min(
            _BACKOFF_CAP_SECONDS, _BACKOFF_BASE_SECONDS * (2.0 ** (attempt - 1))
        )
        # Equal jitter: half fixed, half random, to avoid thundering herd
        # while still guaranteeing forward progress.
        return float((backoff / 2) + random.uniform(0, backoff / 2))

    @staticmethod
    def _retry_after_from_response(response: requests.Response) -> Optional[float]:
        try:
            body = response.json()
        except ValueError:
            body = None
        if isinstance(body, dict) and body.get("retry_after") is not None:
            try:
                return float(body["retry_after"])
            except (TypeError, ValueError):
                pass

        header_value = response.headers.get("Retry-After")
        if header_value is not None:
            try:
                return float(header_value)
            except ValueError:
                pass

        return None

    @staticmethod
    def _build_error(response: requests.Response) -> AsherError:
        try:
            body: Optional[Dict[str, Any]] = response.json()
        except ValueError:
            body = None

        message: Optional[str] = None
        if isinstance(body, dict):
            raw_message = body.get("message")
            if isinstance(raw_message, str):
                message = raw_message
        if not message:
            message = response.text or f"HTTP {response.status_code}"

        status_code = response.status_code

        if status_code == 429:
            retry_after = Client._retry_after_from_response(response)
            return RateLimitError(
                message, status_code=status_code, body=body, retry_after=retry_after
            )

        error_class = _ERROR_CLASSES_BY_STATUS.get(status_code, APIError)
        return error_class(message, status_code=status_code, body=body)
