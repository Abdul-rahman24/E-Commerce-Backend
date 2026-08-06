import os
import unittest
from unittest.mock import MagicMock, patch
import json
import urllib.error
from datetime import datetime, timezone

from src.services.order_service import OrderService
from src.models.order import Order, OrderItem
from src.dto.order_dto import OrderStatusUpdateDTO
from src.exceptions.app_exceptions import NotFoundError, BadRequestError, DatabaseError

# FIX: Patch the module-level variable directly so it doesn't matter what order Pytest loads files
@patch('src.services.order_service.ORDER_EVENTS_TOPIC_ARN', 'arn:aws:sns:fake:123')
class TestOrderService(unittest.TestCase):
    
    @patch('src.services.order_service.boto3.client')
    def setUp(self, mock_boto_client):
        self.mock_repo = MagicMock()
        self.mock_repo.save.side_effect = lambda order: order
        
        self.mock_sns = MagicMock()
        mock_boto_client.return_value = self.mock_sns
        
        self.service = OrderService(self.mock_repo)
        
        self.fake_order = Order(
            order_id="ord_123", user_id="u1", 
            items=[OrderItem(product_id="p1", name="Item 1", price=10.0, quantity=2)],
            total_amount=20.0, currency="USD", status="PENDING_PAYMENT",
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
        )

    @patch('src.services.order_service.urllib.request.urlopen')
    def test_create_order_from_cart_success(self, mock_urlopen):
        mock_response = MagicMock()
        cart_payload = {
            "data": {
                "items": [{"product_id": "p1", "name": "Item 1", "price": 10.0, "quantity": 2}],
                "cart_total": 20.0
            }
        }
        mock_response.read.return_value = json.dumps(cart_payload).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.service.create_order_from_cart("u1")
        
        self.mock_repo.save.assert_called_once()
        self.mock_sns.publish.assert_called_once()
        self.assertEqual(result.total_amount, 20.0)

    @patch('src.services.order_service.urllib.request.urlopen')
    def test_create_order_from_cart_empty(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"data": {"items": []}}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with self.assertRaises(BadRequestError):
            self.service.create_order_from_cart("u1")

    def test_update_status_success_and_publish(self):
        self.mock_repo.get_by_id.return_value = self.fake_order
        dto = OrderStatusUpdateDTO(status="COMPLETED")
        
        result = self.service.update_status("ord_123", dto)
        
        self.assertEqual(result.status, "COMPLETED")
        self.mock_repo.save.assert_called_once()
        self.mock_sns.publish.assert_called_once()

    def test_update_status_not_found(self):
        self.mock_repo.get_by_id.return_value = None
        dto = OrderStatusUpdateDTO(status="COMPLETED")
        
        with self.assertRaises(NotFoundError):
            self.service.update_status("ord_123", dto)

    def test_cancel_order_success(self):
        self.mock_repo.get_by_id.return_value = self.fake_order
        
        result = self.service.cancel_order("ord_123")
        
        self.assertEqual(result.status, "CANCELLED")
        self.mock_sns.publish.assert_called_once()

    def test_cancel_order_already_shipped(self):
        self.fake_order.status = "SHIPPED"
        self.mock_repo.get_by_id.return_value = self.fake_order
        
        with self.assertRaises(BadRequestError):
            self.service.cancel_order("ord_123")

    def test_get_order_success(self):
        self.mock_repo.get_by_id.return_value = self.fake_order
        result = self.service.get_order("ord_123")
        self.assertEqual(result.order_id, "ord_123")

    def test_get_user_orders(self):
        self.mock_repo.get_by_user_id.return_value = [self.fake_order]
        result = self.service.get_user_orders("u1")
        self.assertEqual(len(result), 1)