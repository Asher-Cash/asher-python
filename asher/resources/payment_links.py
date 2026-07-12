"""The ``client.payment_links`` resource."""

from typing import TYPE_CHECKING, Any, Dict, Iterator, Optional

from ..models.common import ListResult
from ..models.payment_link import PaymentLink

if TYPE_CHECKING:
    from ..client import Client

_DEFAULT_PAGE_SIZE = 20


class PaymentLinksResource:
    """Requires the ``payment_links:read`` scope for reads and
    ``payment_links:write`` for creates/deactivates."""

    def __init__(self, client: "Client") -> None:
        self._client = client

    def list(
        self, *, page: Optional[int] = None, limit: Optional[int] = None
    ) -> ListResult[PaymentLink]:
        """``GET /v1/payment-links`` — return a single page of payment links."""
        data = self._client.request_json(
            "GET",
            "/payment-links",
            params={"page": page, "limit": limit},
        )
        items = [PaymentLink.from_dict(item) for item in data.get("payment_links", [])]
        return ListResult(data=items, total=data.get("total", len(items)))

    def list_auto_paging(self, *, limit: Optional[int] = None) -> Iterator[PaymentLink]:
        """Transparently walk every page of payment links, yielding one
        :class:`PaymentLink` at a time until pages are exhausted."""
        page = 1
        page_size = limit or _DEFAULT_PAGE_SIZE
        while True:
            result = self.list(page=page, limit=page_size)
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
        title: str,
        amount: Optional[float] = None,
        asset_id: Optional[str] = None,
        currency: Optional[str] = None,
        expires_at: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        description: Optional[str] = None,
        redirect_url: Optional[str] = None,
        is_fixed_amount: Optional[bool] = None,
        is_single_use: Optional[bool] = None,
        is_recurring: Optional[bool] = None,
        idempotency_key: Optional[str] = None,
    ) -> PaymentLink:
        """``POST /v1/payment-links`` — create a payment link.

        Idempotent: auto-generates a UUID v4 ``Idempotency-Key`` unless
        ``idempotency_key`` is supplied.
        """
        body: Dict[str, Any] = {
            "title": title,
            "amount": amount,
            "asset_id": asset_id,
            "currency": currency,
            "expires_at": expires_at,
            "min_amount": min_amount,
            "max_amount": max_amount,
            "description": description,
            "redirect_url": redirect_url,
            "is_fixed_amount": is_fixed_amount,
            "is_single_use": is_single_use,
            "is_recurring": is_recurring,
        }
        data = self._client.request_json(
            "POST",
            "/payment-links",
            json_body=body,
            idempotency_key=idempotency_key,
        )
        return PaymentLink.from_dict(data["payment_link"])

    def deactivate(self, id: int) -> None:
        """``PUT /v1/payment-links/{id}/deactivate`` — deactivate a payment
        link. No resource is returned on success."""
        self._client.request_json("PUT", f"/payment-links/{id}/deactivate")
