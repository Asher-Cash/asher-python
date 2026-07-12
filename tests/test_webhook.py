"""Smoke tests for Webhook.construct_event — pure logic, no network calls."""

import hashlib
import hmac
import json
import time
from typing import Optional

import pytest

from asher import SignatureVerificationError, Webhook
from asher.webhook import Event

SECRET = "whsec_test_secret"


def _sign(payload: bytes, secret: str = SECRET, timestamp: Optional[int] = None) -> str:
    ts = timestamp if timestamp is not None else int(time.time())
    signed_payload = f"{ts}".encode("utf-8") + b"." + payload
    signature = hmac.new(
        secret.encode("utf-8"), signed_payload, hashlib.sha256
    ).hexdigest()
    return f"t={ts},v1={signature}"


def _event_payload(event_type: str = "payment.succeeded") -> bytes:
    return json.dumps(
        {
            "id": "evt_123",
            "type": event_type,
            "created": int(time.time()),
            "data": {
                "transaction_id": 123,
                "status": "COMPLETED",
                "amount": 25.0,
                "amount_usd": 25.0,
                "local_amount": None,
                "local_currency": "NGN",
                "asset_symbol": "USDC",
                "network": "SOL",
                "tx_hash": "abc123",
                "customer_email": "buyer@example.com",
                "payment_link_id": 5,
                "invoice_id": None,
                "invoice_number": None,
                "created_at": "2026-07-12T10:00:00Z",
            },
        }
    ).encode("utf-8")


def test_construct_event_valid_signature() -> None:
    payload = _event_payload()
    sig_header = _sign(payload)

    event = Webhook.construct_event(payload, sig_header, SECRET)

    assert isinstance(event, Event)
    assert event.id == "evt_123"
    assert event.type == "payment.succeeded"
    assert event.data["transaction_id"] == 123
    assert event.data["local_amount"] is None


def test_construct_event_accepts_str_payload() -> None:
    payload = _event_payload()
    sig_header = _sign(payload)

    event = Webhook.construct_event(payload.decode("utf-8"), sig_header, SECRET)

    assert event.id == "evt_123"


def test_construct_event_ping() -> None:
    payload = json.dumps(
        {
            "id": "evt_ping",
            "type": "ping",
            "created": int(time.time()),
            "data": {"message": "This is a test event from Asher."},
        }
    ).encode("utf-8")
    sig_header = _sign(payload)

    event = Webhook.construct_event(payload, sig_header, SECRET)

    assert event.type == "ping"
    assert event.data["message"] == "This is a test event from Asher."


def test_construct_event_bad_signature_raises() -> None:
    payload = _event_payload()
    ts = int(time.time())
    bad_sig_header = f"t={ts},v1=" + ("0" * 64)

    with pytest.raises(SignatureVerificationError, match="Signature mismatch"):
        Webhook.construct_event(payload, bad_sig_header, SECRET)


def test_construct_event_wrong_secret_raises() -> None:
    payload = _event_payload()
    sig_header = _sign(payload, secret="wrong_secret")

    with pytest.raises(SignatureVerificationError, match="Signature mismatch"):
        Webhook.construct_event(payload, sig_header, SECRET)


def test_construct_event_tampered_payload_raises() -> None:
    payload = _event_payload()
    sig_header = _sign(payload)
    tampered_payload = payload.replace(b"25.0", b"99.0")

    with pytest.raises(SignatureVerificationError, match="Signature mismatch"):
        Webhook.construct_event(tampered_payload, sig_header, SECRET)


def test_construct_event_expired_timestamp_raises() -> None:
    payload = _event_payload()
    old_ts = int(time.time()) - 3600  # 1 hour ago
    sig_header = _sign(payload, timestamp=old_ts)

    with pytest.raises(SignatureVerificationError, match="tolerance"):
        Webhook.construct_event(payload, sig_header, SECRET, tolerance=300)


def test_construct_event_custom_tolerance_allows_older_timestamp() -> None:
    payload = _event_payload()
    old_ts = int(time.time()) - 3600  # 1 hour ago
    sig_header = _sign(payload, timestamp=old_ts)

    event = Webhook.construct_event(payload, sig_header, SECRET, tolerance=7200)

    assert event.id == "evt_123"


def test_construct_event_malformed_header_raises() -> None:
    payload = _event_payload()

    with pytest.raises(SignatureVerificationError, match="Malformed"):
        Webhook.construct_event(payload, "not-a-valid-header", SECRET)


def test_construct_event_missing_header_raises() -> None:
    payload = _event_payload()

    with pytest.raises(SignatureVerificationError, match="Missing"):
        Webhook.construct_event(payload, "", SECRET)


def test_construct_event_invalid_json_raises() -> None:
    payload = b"not json"
    sig_header = _sign(payload)

    with pytest.raises(SignatureVerificationError, match="JSON"):
        Webhook.construct_event(payload, sig_header, SECRET)
