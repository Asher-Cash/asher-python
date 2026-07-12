"""Shared model types used across resources."""

from dataclasses import dataclass
from typing import Generic, List, TypeVar

T = TypeVar("T")


@dataclass
class ListResult(Generic[T]):
    """The result of a paginated ``list()`` call.

    ``total`` is the grand total of items matching the query across *all*
    pages (as returned by the API), not just the count in ``data``.
    """

    data: List[T]
    total: int
