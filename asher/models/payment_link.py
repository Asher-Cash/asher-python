"""The PaymentLink resource model."""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class PaymentLink:
    """A shareable payment link.

    Timestamp fields (``expires_at``, ``created_at``) are returned as raw
    ISO-8601 strings, exactly as sent by the API — the SDK does not parse
    them into ``datetime`` objects. Convert with e.g.
    ``datetime.fromisoformat(value.replace("Z", "+00:00"))`` if you need one.
    """

    id: int
    slug: str
    title: str
    amount: Optional[float]
    asset_id: Optional[str]
    currency: str
    is_active: bool
    expires_at: Optional[str]
    min_amount: Optional[float]
    max_amount: Optional[float]
    description: Optional[str]
    asset_symbol: Optional[str]
    redirect_url: Optional[str]
    payment_count: int
    is_fixed_amount: bool
    is_single_use: bool
    is_recurring: bool
    source: str
    """``"dashboard"`` or ``"api"``."""
    total_collected: float
    created_at: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PaymentLink":
        return cls(
            id=data["id"],
            slug=data["slug"],
            title=data["title"],
            amount=data.get("amount"),
            asset_id=data.get("asset_id"),
            currency=data["currency"],
            is_active=data["is_active"],
            expires_at=data.get("expires_at"),
            min_amount=data.get("min_amount"),
            max_amount=data.get("max_amount"),
            description=data.get("description"),
            asset_symbol=data.get("asset_symbol"),
            redirect_url=data.get("redirect_url"),
            payment_count=data["payment_count"],
            is_fixed_amount=data["is_fixed_amount"],
            is_single_use=data["is_single_use"],
            is_recurring=data["is_recurring"],
            source=data["source"],
            total_collected=data["total_collected"],
            created_at=data["created_at"],
        )
