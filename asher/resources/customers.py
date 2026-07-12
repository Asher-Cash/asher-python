"""The ``client.customers`` resource."""

from typing import TYPE_CHECKING, Any, Dict, Iterator, Optional

from ..models.common import ListResult
from ..models.customer import Customer

if TYPE_CHECKING:
    from ..client import Client

_DEFAULT_PAGE_SIZE = 20


class CustomersResource:
    """Requires the ``customers:read`` scope for reads and
    ``customers:write`` for creates."""

    def __init__(self, client: "Client") -> None:
        self._client = client

    def list(
        self,
        *,
        page: Optional[int] = None,
        limit: Optional[int] = None,
        search: Optional[str] = None,
    ) -> ListResult[Customer]:
        """``GET /v1/customers`` — return a single page of customers.
        ``search`` optionally matches against name/email/phone."""
        data = self._client.request_json(
            "GET",
            "/customers",
            params={"page": page, "limit": limit, "search": search},
        )
        items = [Customer.from_dict(item) for item in data.get("customers", [])]
        return ListResult(data=items, total=data.get("total", len(items)))

    def list_auto_paging(
        self, *, limit: Optional[int] = None, search: Optional[str] = None
    ) -> Iterator[Customer]:
        """Transparently walk every page of customers, yielding one
        :class:`Customer` at a time until pages are exhausted."""
        page = 1
        page_size = limit or _DEFAULT_PAGE_SIZE
        while True:
            result = self.list(page=page, limit=page_size, search=search)
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
        email: str,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        notes: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Customer:
        """``POST /v1/customers`` — create a customer.

        Idempotent: auto-generates a UUID v4 ``Idempotency-Key`` unless
        ``idempotency_key`` is supplied.
        """
        body: Dict[str, Any] = {
            "email": email,
            "name": name,
            "phone": phone,
            "notes": notes,
        }
        data = self._client.request_json(
            "POST", "/customers", json_body=body, idempotency_key=idempotency_key
        )
        return Customer.from_dict(data["customer"])
