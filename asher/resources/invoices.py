"""The ``client.invoices`` resource."""

from typing import TYPE_CHECKING, Any, Dict, Iterator, Optional

from ..models.common import ListResult
from ..models.invoice import Invoice

if TYPE_CHECKING:
    from ..client import Client

_DEFAULT_PAGE_SIZE = 20


class InvoicesResource:
    """Requires the ``invoices:read`` scope for reads and
    ``invoices:write`` for creates/updates/sends."""

    def __init__(self, client: "Client") -> None:
        self._client = client

    def list(
        self,
        *,
        page: Optional[int] = None,
        limit: Optional[int] = None,
        status: Optional[str] = None,
    ) -> ListResult[Invoice]:
        """``GET /v1/invoices`` — return a single page of invoices.
        ``status`` is an optional exact-match filter."""
        data = self._client.request_json(
            "GET",
            "/invoices",
            params={"page": page, "limit": limit, "status": status},
        )
        items = [Invoice.from_dict(item) for item in data.get("invoices", [])]
        return ListResult(data=items, total=data.get("total", len(items)))

    def list_auto_paging(
        self, *, limit: Optional[int] = None, status: Optional[str] = None
    ) -> Iterator[Invoice]:
        """Transparently walk every page of invoices, yielding one
        :class:`Invoice` at a time until pages are exhausted."""
        page = 1
        page_size = limit or _DEFAULT_PAGE_SIZE
        while True:
            result = self.list(page=page, limit=page_size, status=status)
            if not result.data:
                return
            for item in result.data:
                yield item
            if len(result.data) < page_size:
                return
            page += 1

    def create(
        self,
        *,
        customer_name: str,
        amount: float,
        notes: Optional[str] = None,
        due_date: Optional[str] = None,
        asset_id: Optional[str] = None,
        customer_email: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Invoice:
        """``POST /v1/invoices`` — create an invoice.

        Idempotent: auto-generates a UUID v4 ``Idempotency-Key`` unless
        ``idempotency_key`` is supplied.
        """
        body: Dict[str, Any] = {
            "notes": notes,
            "amount": amount,
            "due_date": due_date,
            "asset_id": asset_id,
            "customer_name": customer_name,
            "customer_email": customer_email,
        }
        data = self._client.request_json(
            "POST", "/invoices", json_body=body, idempotency_key=idempotency_key
        )
        return Invoice.from_dict(data["invoice"])

    def update(
        self,
        id: int,
        *,
        customer_name: str,
        amount: float,
        notes: Optional[str] = None,
        due_date: Optional[str] = None,
        asset_id: Optional[str] = None,
        customer_email: Optional[str] = None,
    ) -> Invoice:
        """``PUT /v1/invoices/{id}`` — update an invoice. Only invoices in
        ``DRAFT`` status can be edited; the server returns a 400
        (:class:`~asher.errors.InvalidRequestError`) otherwise. Not
        idempotency-keyed (PUT, not POST — matches the API's own idempotency
        contract)."""
        body: Dict[str, Any] = {
            "notes": notes,
            "amount": amount,
            "due_date": due_date,
            "asset_id": asset_id,
            "customer_name": customer_name,
            "customer_email": customer_email,
        }
        data = self._client.request_json("PUT", f"/invoices/{id}", json_body=body)
        return Invoice.from_dict(data["invoice"])

    def send(self, id: int, *, idempotency_key: Optional[str] = None) -> None:
        """``POST /v1/invoices/{id}/send`` — email the invoice to the
        customer. No resource is returned on success.

        Idempotent: auto-generates a UUID v4 ``Idempotency-Key`` unless
        ``idempotency_key`` is supplied.
        """
        self._client.request_json(
            "POST", f"/invoices/{id}/send", idempotency_key=idempotency_key
        )
