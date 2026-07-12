"""The Invoice resource model."""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class Invoice:
    """An invoice.

    ``status`` is treated as an open string enum (e.g. ``"DRAFT"``,
    ``"SENT"``, ``"PAID"``, ...) rather than a closed set, since the server
    may add new values over time.
    """

    id: int
    notes: Optional[str]
    amount: float
    currency: str
    status: str
    due_date: Optional[str]
    asset_id: Optional[str]
    asset_symbol: Optional[str]
    network: Optional[str]
    deposit_address: Optional[str]
    customer_name: str
    invoice_number: str
    customer_email: Optional[str]
    business_name: str
    created_at: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Invoice":
        return cls(
            id=data["id"],
            notes=data.get("notes"),
            amount=data["amount"],
            currency=data["currency"],
            status=data["status"],
            due_date=data.get("due_date"),
            asset_id=data.get("asset_id"),
            asset_symbol=data.get("asset_symbol"),
            network=data.get("network"),
            deposit_address=data.get("deposit_address"),
            customer_name=data["customer_name"],
            invoice_number=data["invoice_number"],
            customer_email=data.get("customer_email"),
            business_name=data["business_name"],
            created_at=data["created_at"],
        )
