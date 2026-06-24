from pydantic import BaseModel, Field
from typing import TypeVar, Generic
from datetime import datetime

T = TypeVar('T')

class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T

class InventoryTransactionDTO(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0, description="Quantity must be greater than 0")

class InventoryResponseDTO(BaseModel):
    product_id: str
    available_quantity: int
    reserved_quantity: int
    updated_at: datetime

class InitializeInventoryDTO(BaseModel):
    product_id: str