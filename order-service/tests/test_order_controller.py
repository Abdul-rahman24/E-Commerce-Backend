import os
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime, timezone

os.environ["CART_SERVICE_URL"] = "http://fake-cart.com"

# We must mock boto3 BEFORE importing the controller, so it doesn't try to connect to AWS
with patch('boto3.resource'):
    from src.main import app
    from src.controllers.order_controller import get_order_service

from src.dto.order_dto import OrderResponseDTO, OrderItemResponseDTO

class TestOrderController(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.mock_service = MagicMock()
        app.dependency_overrides[get_order_service] = lambda: self.mock_service
        
        self.headers = {"x-user-id": "u1"}
        
        self.fake_response = OrderResponseDTO(
            order_id="ord_123", user_id="u1",
            items=[OrderItemResponseDTO(product_id="p1", name="Item 1", price=10.0, quantity=2)],
            total_amount=20.0, currency="USD", status="PENDING",
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
        )

    @patch('src.controllers.order_controller.order_table')
    def test_get_user_orders_by_header(self, mock_table):
        # Mocking the direct DynamoDB .scan() method in the controller
        mock_table.scan.return_value = {"Items": [{"order_id": "ord_123", "user_id": "u1"}]}
        
        response = self.client.get("/v1/orders/orders", headers=self.headers)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("orders", response.json())
        self.assertEqual(len(response.json()["orders"]), 1)

    def test_create_order(self):
        self.mock_service.create_order_from_cart.return_value = self.fake_response
        response = self.client.post("/v1/orders", headers=self.headers)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_get_order(self):
        self.mock_service.get_order.return_value = self.fake_response
        response = self.client.get("/v1/orders/ord_123", headers=self.headers)
        
        self.assertEqual(response.status_code, 200)

    def test_get_user_orders_by_param(self):
        self.mock_service.get_user_orders.return_value = [self.fake_response]
        response = self.client.get("/v1/orders/user/u1", headers=self.headers)
        
        self.assertEqual(response.status_code, 200)

    @patch('src.controllers.order_controller.order_table')
    def test_update_order_status_success(self, mock_table):
        # Mocking the direct DynamoDB .scan() and .put_item() methods in the controller
        mock_table.scan.return_value = {"Items": [{"order_id": "ord_123", "status": "PENDING"}]}
        mock_table.put_item.return_value = {}
        
        response = self.client.patch("/v1/orders/ord_123/status", json={"status": "COMPLETED"}, headers=self.headers)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    @patch('src.controllers.order_controller.order_table')
    def test_update_order_status_not_found(self, mock_table):
        mock_table.scan.return_value = {"Items": []}
        
        response = self.client.patch("/v1/orders/ord_123/status", json={"status": "COMPLETED"}, headers=self.headers)
        
        self.assertEqual(response.status_code, 404)

    def test_cancel_order(self):
        self.mock_service.cancel_order.return_value = self.fake_response
        response = self.client.patch("/v1/orders/ord_123/cancel", headers=self.headers)
        
        self.assertEqual(response.status_code, 200)