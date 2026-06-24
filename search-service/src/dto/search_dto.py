from pydantic import BaseModel
from typing import List, TypeVar, Generic

T = TypeVar('T')

class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T

class IndexProductDTO(BaseModel):
    product_id: str
    name: str
    description: str
    category: str
    price: float
    images: List[str]

class SearchResultDTO(BaseModel):
    product_id: str
    name: str
    category: str
    price: float
    image_url: str