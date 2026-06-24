from dataclasses import dataclass
from datetime import datetime

@dataclass
class Inventory:
    product_id: str
    available_quantity: int
    reserved_quantity: int
    updated_at: datetime