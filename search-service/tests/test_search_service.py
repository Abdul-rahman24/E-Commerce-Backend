import unittest
from unittest.mock import MagicMock
from src.services.search_service import SearchService
from src.models.search_item import SearchItem
from src.dto.search_dto import IndexProductDTO
from src.exceptions.app_exceptions import NotFoundError

class TestSearchService(unittest.TestCase):
    def setUp(self):
        self.mock_repo = MagicMock()
        self.service = SearchService(self.mock_repo)
        
    def test_index_product(self):
        # Create a mock DTO to pass into the service
        dto = MagicMock(spec=IndexProductDTO)
        dto.product_id = "p_123"
        dto.name = "Test Product"
        dto.description = "A great product"
        dto.category = "Electronics"
        dto.price = 99.99
        dto.images = ["img1.jpg"]
        
        self.service.index_product(dto)
        
        # Verify the repository was called to save the index item
        self.mock_repo.index_item.assert_called_once()
        
    def test_perform_search_success(self):
        # Mock the repository response
        mock_item = SearchItem(
            product_id="p_123", name="Test Product", description="A great product",
            category="Electronics", price=99.99, images=["img1.jpg"], search_tags="test product a great product electronics"
        )
        self.mock_repo.search.return_value = [mock_item]
        
        results = self.service.perform_search("Test")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].product_id, "p_123")
        self.assertEqual(results[0].image_url, "img1.jpg")
        
    def test_perform_search_empty_query(self):
        # Service should return an empty list immediately without hitting DB
        results = self.service.perform_search("   ")
        
        self.assertEqual(results, [])
        self.mock_repo.search.assert_not_called()
        
    def test_perform_search_not_found(self):
        # Mock empty database response
        self.mock_repo.search.return_value = []
        
        # Verify the custom exception is raised
        with self.assertRaises(NotFoundError):
            self.service.perform_search("UnknownProduct")