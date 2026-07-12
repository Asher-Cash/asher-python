"""The Customer resource model."""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class Customer:
    id: int
    email: str
    name: Optional[str]
    phone: Optional[str]
    notes: Optional[str]
    total_spent: float
    transaction_count: int
    last_transaction_at: Optional[str]
    created_at: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Customer":
        return cls(
            id=data["id"],
            email=data["email"],
            name=data.get("name"),
            phone=data.get("phone"),
            notes=data.get("notes"),
            total_spent=data["total_spent"],
            transaction_count=data["transaction_count"],
            last_transaction_at=data.get("last_transaction_at"),
            created_at=data["created_at"],
        )
