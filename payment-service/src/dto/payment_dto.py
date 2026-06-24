from pydantic import BaseModel, Field
from typing import Optional, TypeVar, Generic
from datetime import datetime

T = TypeVar('T')

class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T

class InitiatePaymentDTO(BaseModel):
    order_id: str
    amount: float = Field(..., gt=0)
    currency: str = "USD"
    provider: str = "STRIPE"

class VerifyPaymentDTO(BaseModel):
    payment_id: str
    provider_transaction_id: str

class WebhookPayloadDTO(BaseModel):
    event_type: str # e.g., "payment_intent.succeeded"
    provider_transaction_id: str
    status: str
    
class PaymentResponseDTO(BaseModel):
    payment_id: str
    order_id: str
    amount: float
    currency: str
    status: str
    provider: str
    client_secret: Optional[str] = None # Mock token returned to frontend
    created_at: datetime
    updated_at: datetime