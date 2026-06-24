from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Payment:
    payment_id: str
    order_id: str
    user_id: str
    amount: float
    currency: str
    status: str # PENDING, SUCCESS, FAILED, REFUNDED
    provider: str # e.g., STRIPE, PAYPAL
    provider_transaction_id: Optional[str]
    created_at: datetime
    updated_at: datetime