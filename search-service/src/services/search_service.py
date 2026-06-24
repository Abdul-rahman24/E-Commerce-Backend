from typing import List
from src.repositories.search_repository import DynamoDBSearchRepository
from src.models.search_item import SearchItem
from src.dto.search_dto import IndexProductDTO, SearchResultDTO
from src.exceptions.app_exceptions import NotFoundError
from src.utils.logger import get_logger

logger = get_logger("SearchService")

class SearchService:
    def __init__(self, repository: DynamoDBSearchRepository):
        self.repository = repository

    def index_product(self, dto: IndexProductDTO) -> None:
        # We combine text into a single lowercase string to make DynamoDB searching easier
        search_tags = f"{dto.name} {dto.description} {dto.category}".lower()
        
        item = SearchItem(
            product_id=dto.product_id,
            name=dto.name,
            description=dto.description,
            category=dto.category,
            price=dto.price,
            images=dto.images,
            search_tags=search_tags
        )
        self.repository.index_item(item)
        logger.info(f"Successfully indexed product: {dto.product_id}")

    def perform_search(self, query: str) -> List[SearchResultDTO]:
        if not query or len(query.strip()) == 0:
            return []
            
        logger.info(f"Performing search for: {query}")
        results = self.repository.search(query.strip())
        
        # --- NEW CODE: Check if results are empty ---
        if not results:
            logger.info(f"No products found for query: {query}")
            raise NotFoundError(" Products Unavailable ")
        # --------------------------------------------
        
        # Map the database model to the clean frontend DTO
        dtos = []
        for item in results:
            dtos.append(SearchResultDTO(
                product_id=item.product_id,
                name=item.name,
                category=item.category,
                price=item.price,
                image_url=item.images[0] if item.images else ""
            ))
        return dtos