from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict

@dataclass
class CartItem:
    product_id: str
    name: str
    price: float
    quantity: int

@dataclass
class Cart:
    user_id: str
    items: Dict[str, CartItem] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: int = 0 # Unix epoch timestamp for DynamoDB TTL
    
    @property
    def total_price(self) -> float:
        return sum(item.price * item.quantity for item in self.items.values())