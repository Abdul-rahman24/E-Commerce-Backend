import uuid
import requests
from datetime import datetime, timezone
from typing import List
from src.repositories.product_repository import DynamoDBProductRepository
from src.models.product import Product
from src.dto.product_dto import CreateProductDTO, UpdateProductDTO
from src.exceptions.app_exceptions import NotFoundError
from src.utils.logger import get_logger

logger = get_logger("ProductService")

# The address of our Inventory Service
INVENTORY_SERVICE_URL = "http://127.0.0.1:8001/api/v1/inventory"
SEARCH_SERVICE_URL = "http://127.0.0.1:8005/api/v1/search"

class ProductService:
    def __init__(self, repository: DynamoDBProductRepository):
        self.repository = repository

    def create_product(self, dto: CreateProductDTO) -> Product:
        new_product = Product(
            product_id=str(uuid.uuid4()),
            sku=dto.sku,
            name=dto.name,
            description=dto.description,
            category=dto.category,
            brand=dto.brand,
            price=dto.price,
            currency=dto.currency,
            status="DRAFT",
            images=dto.images,
            attributes=dto.attributes,
            is_deleted=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # 1. Save to the Product Database first
        saved_product = self.repository.create(new_product)

        # 2. The Chain Reaction: Tell Inventory to initialize stock to 0
        logger.info(f"Triggering inventory initialization for {saved_product.product_id}")
        try:
            response = requests.post(
                f"{INVENTORY_SERVICE_URL}/initialize",
                json={"product_id": saved_product.product_id},
                timeout=5
            )
            if response.status_code != 200:
                # We log the error, but we DO NOT crash the product creation
                logger.error(f"Failed to initialize inventory for {saved_product.product_id}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Inventory Service is offline: {str(e)}")

        

        # 3. The Chain Reaction: Tell Search Service to index this product
        try:
            requests.post(
                f"{SEARCH_SERVICE_URL}/index",
                json={
                    "product_id": saved_product.product_id,
                    "name": saved_product.name,
                    "description": saved_product.description,
                    "category": saved_product.category,
                    "price": saved_product.price,
                    "images": saved_product.images
                },
                timeout=5
            )
            logger.info(f"Triggered search indexing for {saved_product.product_id}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Search Service is offline: {str(e)}")
        
        return saved_product
    

    def get_product(self, product_id: str) -> Product:
        product = self.repository.find_by_id(product_id)
        if not product:
            raise NotFoundError(f"Product with ID {product_id} not found")
        return product

    def get_all_products(self) -> List[Product]:
        return self.repository.find_all()

    def update_product(self, product_id: str, dto: UpdateProductDTO) -> Product:
        product = self.get_product(product_id)
        
        update_data = dto.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(product, key):
                setattr(product, key, value)
                
        product.updated_at = datetime.now(timezone.utc)
        return self.repository.update(product)

    def delete_product(self, product_id: str) -> None:
        product = self.get_product(product_id)
        product.is_deleted = True
        product.updated_at = datetime.now(timezone.utc)
        self.repository.update(product)