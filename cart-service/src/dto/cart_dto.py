from pydantic import BaseModel, Field
from typing import List, TypeVar, Generic
from datetime import datetime

T = TypeVar('T')

class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T

class AddCartItemDTO(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0)

class UpdateCartItemDTO(BaseModel):
    quantity: int = Field(..., ge=0)

class CartItemResponseDTO(BaseModel):
    product_id: str
    name: str
    price: float
    quantity: int
    item_total: float

class CartResponseDTO(BaseModel):
    user_id: str
    items: List[CartItemResponseDTO]
    cart_total: float
    updated_at: datetime