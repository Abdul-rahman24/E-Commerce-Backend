from pydantic import BaseModel
from typing import List, TypeVar, Generic
from datetime import datetime

T = TypeVar('T')

class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T

class OrderStatusUpdateDTO(BaseModel):
    status: str

class OrderItemResponseDTO(BaseModel):
    product_id: str
    name: str
    price: float
    quantity: int

class OrderResponseDTO(BaseModel):
    order_id: str
    user_id: str
    items: List[OrderItemResponseDTO]
    total_amount: float
    currency: str
    status: str
    created_at: datetime
    updated_at: datetime