from dataclasses import dataclass, field
from datetime import datetime
from typing import List

@dataclass
class OrderItem:
    product_id: str
    name: str
    price: float
    quantity: int

@dataclass
class Order:
    order_id: str
    user_id: str
    items: List[OrderItem]
    total_amount: float
    currency: str
    status: str # PENDING_PAYMENT, PAID, CANCELLED, SHIPPED, COMPLETED
    created_at: datetime
    updated_at: datetime