"""The Transaction resource model."""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class Transaction:
    """A completed (or in-progress) payment. Read-only — transactions are
    produced by the payment flow itself, never created via the API.
    """

    id: int
    status: str
    tx_hash: Optional[str]
    amount: float
    asset_id: Optional[str]
    network: Optional[str]
    invoice_id: Optional[int]
    amount_usd: Optional[float]
    fee_amount: float
    customer_id: Optional[int]
    local_amount: Optional[float]
    """Currently always ``None`` — a known server-side gap. Don't rely on it."""
    fee_currency: str
    asset_symbol: Optional[str]
    asset_network: Optional[str]
    customer_email: Optional[str]
    payment_link_id: Optional[int]
    local_currency: str
    sender_address: Optional[str]
    receiver_address: Optional[str]
    created_at: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Transaction":
        return cls(
            id=data["id"],
            status=data["status"],
            tx_hash=data.get("tx_hash"),
            amount=data["amount"],
            asset_id=data.get("asset_id"),
            network=data.get("network"),
            invoice_id=data.get("invoice_id"),
            amount_usd=data.get("amount_usd"),
            fee_amount=data["fee_amount"],
            customer_id=data.get("customer_id"),
            local_amount=data.get("local_amount"),
            fee_currency=data["fee_currency"],
            asset_symbol=data.get("asset_symbol"),
            asset_network=data.get("asset_network"),
            customer_email=data.get("customer_email"),
            payment_link_id=data.get("payment_link_id"),
            local_currency=data["local_currency"],
            sender_address=data.get("sender_address"),
            receiver_address=data.get("receiver_address"),
            created_at=data["created_at"],
        )
