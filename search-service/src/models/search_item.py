from dataclasses import dataclass
from typing import List

@dataclass
class SearchItem:
    product_id: str
    name: str
    description: str
    category: str
    price: float
    images: List[str]
    search_tags: str # We concatenate fields into one lowercase string for easier searching