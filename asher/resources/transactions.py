"""The ``client.transactions`` resource (read-only)."""

from typing import TYPE_CHECKING, Iterator, Optional

from ..models.common import ListResult
from ..models.transaction import Transaction

if TYPE_CHECKING:
    from ..client import Client

_DEFAULT_PAGE_SIZE = 20


class TransactionsResource:
    """Requires the ``transactions:read`` scope. Read-only — transactions
    are produced by completed payments, never created via the API."""

    def __init__(self, client: "Client") -> None:
        self._client = client

    def list(
        self,
        *,
        page: Optional[int] = None,
        limit: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> ListResult[Transaction]:
        """``GET /v1/transactions`` — return a single page of transactions.
        All filters are optional; ``date_from``/``date_to`` are ISO date
        strings, ``search`` is free text matched against tx hash/customer/etc.
        """
        data = self._client.request_json(
            "GET",
            "/transactions",
            params={
                "page": page,
                "limit": limit,
                "status": status,
                "search": search,
                "date_from": date_from,
                "date_to": date_to,
            },
        )
        items = [Transaction.from_dict(item) for item in data.get("transactions", [])]
        return ListResult(data=items, total=data.get("total", len(items)))

    def list_auto_paging(
        self,
        *,
        limit: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Iterator[Transaction]:
        """Transparently walk every page of transactions, yielding one
        :class:`Transaction` at a time until pages are exhausted."""
        page = 1
        page_size = limit or _DEFAULT_PAGE_SIZE
        while True:
            result = self.list(
                page=page,
                limit=page_size,
                status=status,
                search=search,
                date_from=date_from,
                date_to=date_to,
            )
            if not result.data:
                return
            for item in result.data:
                yield item
            if len(result.data) < page_size:
                return
            page += 1

    def export(
        self,
        *,
        status: Optional[str] = None,
        search: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> bytes:
        """``GET /v1/transactions/export`` — export every transaction
        matching the given filters (no pagination) as a CSV file. Returns
        the raw response bytes (``Content-Type: text/csv``) — decide how to
        handle them yourself (write to a file, parse with ``csv``, etc)."""
        return self._client.request_raw(
            "GET",
            "/transactions/export",
            params={
                "status": status,
                "search": search,
                "date_from": date_from,
                "date_to": date_to,
            },
        )
