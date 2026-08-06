import unittest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from src.main import app
from src.controllers.search_controller import get_search_service
from src.dto.search_dto import SearchResultDTO

class TestSearchController(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.mock_service = MagicMock()
        app.dependency_overrides[get_search_service] = lambda: self.mock_service

    def test_search_products_success(self):
        fake_result = SearchResultDTO(
            product_id="p_123", name="Test Product", category="Electronics", 
            price=99.99, image_url="img1.jpg"
        )
        self.mock_service.perform_search.return_value = [fake_result]
        
        response = self.client.get("/v1/search?q=Test")
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(len(response.json()["data"]), 1)
        
    def test_search_products_missing_query(self):
        # FastAPI should automatically throw a 422 if the required 'q' param is missing
        response = self.client.get("/v1/search")
        self.assertEqual(response.status_code, 422)

    def test_index_product(self):
        self.mock_service.index_product.return_value = None
        
        payload = {
            "product_id": "p_123",
            "name": "Test Product",
            "description": "A great product",
            "category": "Electronics",
            "price": 99.99,
            "images": ["img1.jpg"]
        }
        
        response = self.client.post("/v1/search/index", json=payload)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])