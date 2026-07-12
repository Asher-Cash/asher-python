"""Webhook signature verification.

This module is pure local logic — it makes no network calls. It lets a
merchant's server verify that an inbound webhook POST really came from
Asher (and hasn't been replayed) before trusting its contents.

IMPORTANT: always pass the *raw* request body bytes (e.g. Flask's
``request.get_data()``), never a re-serialized/re-parsed version (e.g.
Flask's ``request.json``) — re-serialization can reorder keys or change
whitespace/number formatting, which would break signature verification even
for a genuine, unmodified webhook.
"""

import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple, Union

from .errors import SignatureVerificationError


@dataclass
class Event:
    """A verified webhook event.

    ``type`` is one of ``"payment.succeeded"``, ``"payment.failed"``,
    ``"invoice.paid"``, or ``"ping"`` (treated as an open string, in case new
    event types are added later). ``data`` is intentionally a loosely-typed
    dict — its shape varies by ``type`` (see the Asher API docs / SDK
    README for the field list per event type).
    """

    id: str
    type: str
    created: int
    data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "Event":
        return cls(
            id=payload["id"],
            type=payload["type"],
            created=payload["created"],
            data=payload.get("data") or {},
        )


class Webhook:
    """Namespace for webhook-related helpers. Not instantiated —
    ``Webhook.construct_event(...)`` is a staticmethod, matching the
    ``Webhook.constructEvent`` helper in Asher's other SDKs.
    """

    @staticmethod
    def construct_event(
        payload: Union[bytes, str],
        sig_header: str,
        secret: str,
        tolerance: int = 300,
    ) -> Event:
        """Verify an inbound webhook delivery and return its parsed event.

        Args:
            payload: The exact raw request body, as bytes (preferred) or a
                str. Do NOT pass a re-serialized/re-parsed version of the
                body.
            sig_header: The raw value of the ``Asher-Signature`` request
                header, shaped like ``t=<unix ts>,v1=<hex hmac>``.
            secret: Your webhook signing secret (from the Asher dashboard).
            tolerance: Maximum allowed age, in seconds, of the webhook's
                timestamp relative to now. Defaults to 300 (5 minutes).
                Pass ``None`` to disable the timestamp check entirely.

        Returns:
            The verified :class:`Event`.

        Raises:
            SignatureVerificationError: if the header is malformed, the
                computed signature doesn't match, or the timestamp is
                outside ``tolerance``. The exception message states which
                check failed.
        """
        payload_bytes = payload.encode("utf-8") if isinstance(payload, str) else payload

        timestamp, signature = Webhook._parse_signature_header(sig_header)

        signed_payload = timestamp.encode("utf-8") + b"." + payload_bytes
        expected_signature = hmac.new(
            secret.encode("utf-8"), signed_payload, hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, signature):
            raise SignatureVerificationError(
                "Signature mismatch: the computed HMAC-SHA256 signature does "
                "not match the 'v1' value in the Asher-Signature header. "
                "This payload was not signed with the given secret, or the "
                "raw body was modified/re-serialized before verification."
            )

        try:
            event_ts = int(timestamp)
        except ValueError:
            raise SignatureVerificationError(
                f"Invalid timestamp in Asher-Signature header: {timestamp!r} "
                "is not an integer."
            )

        if tolerance is not None:
            age = abs(time.time() - event_ts)
            if age > tolerance:
                raise SignatureVerificationError(
                    f"Timestamp outside tolerance: webhook was signed {age:.0f}s "
                    f"ago, which exceeds the {tolerance}s tolerance. Possible "
                    "replay attack, or your server's clock is skewed."
                )

        try:
            decoded = payload_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SignatureVerificationError(
                f"Unable to decode webhook payload as UTF-8: {exc}"
            ) from exc

        try:
            body = json.loads(decoded)
        except ValueError as exc:
            raise SignatureVerificationError(
                f"Unable to parse webhook payload as JSON: {exc}"
            ) from exc

        if not isinstance(body, dict):
            raise SignatureVerificationError(
                "Webhook payload is valid JSON but not a JSON object."
            )

        return Event.from_dict(body)

    @staticmethod
    def _parse_signature_header(sig_header: str) -> Tuple[str, str]:
        if not sig_header:
            raise SignatureVerificationError(
                "Missing Asher-Signature header: no signature was provided."
            )

        parts: Dict[str, str] = {}
        for item in sig_header.split(","):
            if "=" not in item:
                continue
            key, _, value = item.partition("=")
            parts[key.strip()] = value.strip()

        timestamp = parts.get("t")
        signature = parts.get("v1")
        if not timestamp or not signature:
            raise SignatureVerificationError(
                "Malformed Asher-Signature header: expected the format "
                "'t=<unix timestamp>,v1=<hex-encoded hmac>', got "
                f"{sig_header!r}."
            )
        return timestamp, signature
