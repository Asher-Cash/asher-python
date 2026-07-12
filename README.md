# Asher Python SDK

Official Python client for the [Asher](https://asher.cash) API — accept stablecoin
payments and settle to local currency. This library wraps `/v1` of the Asher REST
API: payment links, invoices, transactions, and customers, plus a local webhook
signature-verification helper.

- Requires Python 3.8+
- One dependency: [`requests`](https://pypi.org/project/requests/)
- Fully typed (ships a `py.typed` marker; passes `mypy --strict`)

## Installation

```bash
pip install asher-payments
```

The importable package is `asher` (the PyPI distribution is named `asher-payments`
to avoid a name collision):

```python
import asher
```

## Quickstart

```python
import asher

client = asher.Client(api_key="sk_test_...")

# Create a payment link
link = client.payment_links.create(
    title="Consulting invoice",
    amount=250.0,
    currency="USD",
)
print(link.slug, link.id, link.is_active)

# List payment links (single page)
result = client.payment_links.list(page=1, limit=20)
print(result.total, len(result.data))

# Auto-paginate across every page
for link in client.payment_links.list_auto_paging():
    print(link.slug)
```

The secret key you pass (`sk_test_...` vs `sk_live_...`) determines which
environment (sandbox or live) your requests operate in — there's no separate
environment flag.

## Client configuration

```python
client = asher.Client(
    api_key="sk_test_...",       # required
    base_url=None,               # defaults to https://api.asher.cash/v1
    max_retries=None,            # defaults to 2 (3 attempts total)
    timeout=None,                # defaults to 30.0 seconds, per request
)
```

## Resources & methods

Every list method returns a `ListResult[T]` with `.data` (a list of typed items)
and `.total` (the grand total matching the query, across all pages — not just the
current page).

| Resource | Method | HTTP | Scope required | Notes |
|---|---|---|---|---|
| `client.payment_links` | `list(page=, limit=)` | `GET /v1/payment-links` | `payment_links:read` | one page |
| | `list_auto_paging(limit=)` | `GET /v1/payment-links` (repeated) | `payment_links:read` | generator, all pages |
| | `create(title=, amount=, ...)` | `POST /v1/payment-links` | `payment_links:write` | idempotent |
| | `deactivate(id)` | `PUT /v1/payment-links/{id}/deactivate` | `payment_links:write` | returns `None` |
| `client.invoices` | `list(page=, limit=, status=)` | `GET /v1/invoices` | `invoices:read` | one page |
| | `list_auto_paging(limit=, status=)` | `GET /v1/invoices` (repeated) | `invoices:read` | generator, all pages |
| | `create(customer_name=, amount=, ...)` | `POST /v1/invoices` | `invoices:write` | idempotent |
| | `update(id, customer_name=, amount=, ...)` | `PUT /v1/invoices/{id}` | `invoices:write` | only `DRAFT` invoices are editable (server-enforced) |
| | `send(id)` | `POST /v1/invoices/{id}/send` | `invoices:write` | idempotent, returns `None` |
| `client.transactions` | `list(page=, limit=, status=, search=, date_from=, date_to=)` | `GET /v1/transactions` | `transactions:read` | one page, read-only resource |
| | `list_auto_paging(...)` | `GET /v1/transactions` (repeated) | `transactions:read` | generator, all pages |
| | `export(status=, search=, date_from=, date_to=)` | `GET /v1/transactions/export` | `transactions:read` | returns raw CSV `bytes`, not JSON |
| `client.customers` | `list(page=, limit=, search=)` | `GET /v1/customers` | `customers:read` | one page |
| | `list_auto_paging(limit=, search=)` | `GET /v1/customers` (repeated) | `customers:read` | generator, all pages |
| | `create(email=, name=, phone=, notes=)` | `POST /v1/customers` | `customers:write` | idempotent |

### Auto-pagination

```python
for txn in client.transactions.list_auto_paging(status="COMPLETED"):
    print(txn.id, txn.amount, txn.customer_email)
```

Internally this walks `page=1, 2, 3, ...` until an empty (or short) page is
returned — you never have to manage `page`/`limit` yourself.

### Exporting transactions as CSV

`export()` doesn't return the standard JSON envelope — the API responds with a raw
`text/csv` file. The SDK hands you the raw bytes and lets you decide what to do
with them:

```python
csv_bytes = client.transactions.export(date_from="2026-01-01", date_to="2026-07-01")
with open("transactions.csv", "wb") as f:
    f.write(csv_bytes)
```

## Idempotency

Every mutating method that maps to a `POST` endpoint (`payment_links.create`,
`invoices.create`, `invoices.send`, `customers.create`) automatically generates a
random UUID v4 and sends it as the `Idempotency-Key` header. The API caches the
first response for a given key for 24 hours (scoped per API key) and replays it
verbatim on retry — including cached error responses — so it's always safe to
retry these calls.

Pass your own key if you want to control idempotency across process restarts or
coordinate it with your own request IDs:

```python
link = client.payment_links.create(
    title="Consulting invoice",
    amount=250.0,
    idempotency_key="order-42-payment-link",
)
```

`PUT` endpoints (`invoices.update`, `payment_links.deactivate`) are not
idempotency-keyed — the API doesn't treat them as idempotent-by-key endpoints
(they're naturally idempotent by virtue of being full-state updates / a one-way
status flip).

## Retries

The client automatically retries:

- Network/connection errors (no response received)
- HTTP `429`
- HTTP `500`, `502`, `503`, `504`

It does **not** retry other 4xx errors (400, 401, 403, 404, 422) — those indicate a
problem with the request itself, not a transient failure.

Backoff is exponential with jitter: starting around 0.5s, doubling each attempt,
capped at ~8s. On a `429`, the client prefers the server's `retry_after` value
(from the JSON response body) over its own computed backoff, when present.

`max_retries` (default `2`, i.e. 3 attempts total) is configurable on the client:

```python
client = asher.Client(api_key="sk_test_...", max_retries=5)
```

## Errors

All SDK errors are subclasses of `asher.AsherError`, which carries:

- `.message` — the server's (or a locally-generated) error message
- `.status_code` — the HTTP status code, if a response was received
- `.body` — the raw parsed JSON response body, if any

| Exception | HTTP status | Meaning |
|---|---|---|
| `asher.AuthenticationError` | 401 | Missing or invalid API key |
| `asher.PermissionError` | 403 | API key is missing a required scope |
| `asher.NotFoundError` | 404 | Resource doesn't exist |
| `asher.InvalidRequestError` | 400, 422 | Request validation failed (server messages are generic, not field-level) |
| `asher.RateLimitError` | 429 | Too many requests; also exposes `.retry_after` (seconds, float or `None`) |
| `asher.APIError` | any other non-2xx | Catch-all |
| `asher.ConnectionError` | — | Network failure, raised only after retries are exhausted |

```python
import asher

try:
    client.payment_links.create(title="Test")
except asher.RateLimitError as e:
    print("rate limited, retry after", e.retry_after)
except asher.InvalidRequestError as e:
    print("bad request:", e.message)
except asher.AsherError as e:
    print("request failed:", e.status_code, e.message)
```

## Webhook signature verification

Asher signs webhook deliveries with an `Asher-Signature` header shaped like
`t=<unix timestamp>,v1=<hex-encoded HMAC-SHA256>`. Verify it with
`asher.Webhook.construct_event(...)` before trusting the payload:

```python
import asher

event = asher.Webhook.construct_event(
    payload=raw_body,             # raw bytes, exactly as received
    sig_header=request.headers["Asher-Signature"],
    secret="whsec_...",            # your webhook signing secret
    tolerance=300,                 # optional, defaults to 300 seconds
)

if event.type == "payment.succeeded":
    data = event.data
    print(data["transaction_id"], data["amount"], data["customer_email"])
elif event.type == "invoice.paid":
    ...
elif event.type == "ping":
    print(event.data["message"])
```

`construct_event` raises `asher.SignatureVerificationError` if the header is
malformed, the computed signature doesn't match, or the timestamp is outside the
tolerance window — the exception message says which check failed.

### Flask example

**Important:** you must pass the *raw* request body to `construct_event`, not
`request.json`. Flask's `request.json` re-parses and re-serializes the body,
which can reorder keys or reformat numbers/whitespace — that would break signature
verification even for a perfectly genuine webhook, since the signature was
computed over the *exact* bytes Asher sent. Always use `request.get_data()`.

```python
from flask import Flask, request
import asher

app = Flask(__name__)
WEBHOOK_SECRET = "whsec_..."

@app.route("/webhooks/asher", methods=["POST"])
def asher_webhook():
    try:
        event = asher.Webhook.construct_event(
            payload=request.get_data(),  # raw bytes — NOT request.json
            sig_header=request.headers.get("Asher-Signature", ""),
            secret=WEBHOOK_SECRET,
        )
    except asher.SignatureVerificationError as e:
        return {"error": str(e)}, 400

    if event.type == "payment.succeeded":
        # fulfill the order, mark invoice paid, etc.
        pass

    return {"received": True}, 200
```

## Typed models

`PaymentLink`, `Invoice`, `Transaction`, and `Customer` are plain `dataclasses`
with `Optional[...]` on every nullable field, matching the API spec exactly.
Timestamp fields (`created_at`, `expires_at`, `due_date`, `last_transaction_at`)
are returned as raw ISO-8601 strings — the SDK does not parse them into
`datetime` objects, to avoid subtle timezone/format bugs. Convert them yourself
if needed:

```python
from datetime import datetime

created = datetime.fromisoformat(link.created_at.replace("Z", "+00:00"))
```

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

pytest
mypy asher/
black asher/ tests/
```

## Notes / deviations from the API spec

- The spec doesn't pin a default request timeout; this SDK defaults to 30
  seconds per request (configurable via `timeout=`).
- `base_url` defaults to `https://api.asher.cash/v1` (the spec's base URL plus
  the `/v1` mount point all routes live under), so resource paths in the SDK are
  relative to that (e.g. `/payment-links`).
- Idempotency keys are only auto-generated for `POST` endpoints, matching the
  spec's own wording ("Any mutating (POST) request..."); `PUT` endpoints
  (`invoices.update`, `payment_links.deactivate`) are not in the spec's
  idempotency-key contract and are left unkeyed.
