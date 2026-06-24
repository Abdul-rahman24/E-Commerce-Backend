import requests
from src.repositories.inventory_repository import DynamoDBInventoryRepository
from src.dto.inventory_dto import InventoryTransactionDTO
from src.models.inventory import Inventory
from src.exceptions.app_exceptions import BadRequestError, DatabaseError
from src.utils.logger import get_logger

logger = get_logger("InventoryService")

# Hardcoded for local development. In production, this goes in a .env file!
PRODUCT_SERVICE_URL = "http://127.0.0.1:8000/api/v1/products"

class InventoryService:
    def __init__(self, repository: DynamoDBInventoryRepository):
        self.repository = repository

    def get_inventory(self, product_id: str) -> Inventory:
        return self.repository.get_by_product_id(product_id)

    # --- NEW METHOD: Used by Product Service to set stock to 0 ---
    def initialize_stock(self, product_id: str) -> Inventory:
        logger.info(f"Initializing empty stock for new product {product_id}")
        return self.repository.initialize_inventory(product_id, 0)

    # --- UPDATED METHOD: Verifies with Product Service before restocking ---
    def restock(self, dto: InventoryTransactionDTO) -> Inventory:
        logger.info(f"Verifying product {dto.product_id} exists before restocking...")
        
        try:
            # The "Phone Call" to the Menu Manager
            response = requests.get(f"{PRODUCT_SERVICE_URL}/{dto.product_id}", timeout=5)
            
            if response.status_code == 404:
                raise BadRequestError(f"Cannot restock: Product ID {dto.product_id} does not exist.")
            elif response.status_code != 200:
                raise DatabaseError("Product Service is returning errors. Cannot verify product.")
                
        except requests.exceptions.RequestException:
            raise DatabaseError("Product Service is offline. Cannot verify product at this time.")

        # If the check passes, proceed with restocking
        logger.info("Product verified. Proceeding with restock.")
        try:
            return self.repository.atomic_update(dto.product_id, dto.quantity, 0)
        except Exception:
            return self.repository.initialize_inventory(dto.product_id, dto.quantity)

    def reserve_stock(self, dto: InventoryTransactionDTO) -> Inventory:
        return self.repository.atomic_update(dto.product_id, -dto.quantity, dto.quantity)

    def release_stock(self, dto: InventoryTransactionDTO) -> Inventory:
        return self.repository.atomic_update(dto.product_id, dto.quantity, -dto.quantity)

    def deduct_stock(self, dto: InventoryTransactionDTO) -> Inventory:
        return self.repository.atomic_update(dto.product_id, 0, -dto.quantity)