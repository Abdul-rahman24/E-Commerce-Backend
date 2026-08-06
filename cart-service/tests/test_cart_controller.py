import os
os.environ["PRODUCT_SERVICE_URL"] = "http://fake-url.com/v1/products"
os.environ["INVENTORY_SERVICE_URL"] = "http://fake-url.com/v1/inventory"

import unittest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from src.main import app
from src.controllers.cart_controller import get_cart_service
from src.dto.cart_dto import CartResponseDTO, CartItemResponseDTO

class TestCartController(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.mock_service = MagicMock()
        app.dependency_overrides[get_cart_service] = lambda: self.mock_service
        
        # Standard fake response required by the DTOs
        self.fake_response = CartResponseDTO(
            user_id="u1",
            items=[CartItemResponseDTO(product_id="p1", name="Test", price=10.0, quantity=2, item_total=20.0)],
            cart_total=20.0,
            updated_at=datetime.now(timezone.utc)
        )
        self.headers = {"x-user-id": "u1"}

    def test_get_cart(self):
        self.mock_service.get_cart.return_value = self.fake_response
        response = self.client.get("/v1/cart", headers=self.headers)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_add_to_cart(self):
        self.mock_service.add_item.return_value = self.fake_response
        response = self.client.post("/v1/cart/items", json={"product_id": "p1", "quantity": 2}, headers=self.headers)
        
        self.assertEqual(response.status_code, 200)

    def test_update_cart_item(self):
        self.mock_service.update_item.return_value = self.fake_response
        response = self.client.patch("/v1/cart/items/p1", json={"quantity": 5}, headers=self.headers)
        
        self.assertEqual(response.status_code, 200)

    def test_remove_from_cart(self):
        self.mock_service.remove_item.return_value = self.fake_response
        response = self.client.delete("/v1/cart/items/p1", headers=self.headers)
        
        self.assertEqual(response.status_code, 200)

    def test_clear_cart(self):
        response = self.client.delete("/v1/cart", headers=self.headers)
        # Controller returns HTTP_204_NO_CONTENT for clear_cart
        self.assertEqual(response.status_code, 204)

    def test_missing_header_validation(self):
        # Omit the headers dictionary to trigger FastAPI validation error
        response = self.client.get("/v1/cart")
        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.json()["success"])