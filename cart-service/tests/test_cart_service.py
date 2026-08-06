import os
# Inject environment variables to prevent URL parsing errors during tests
os.environ["PRODUCT_SERVICE_URL"] = "http://fake-url.com/v1/products"
os.environ["INVENTORY_SERVICE_URL"] = "http://fake-url.com/v1/inventory"

import unittest
import urllib.error
import json
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from src.services.cart_service import CartService
from src.models.cart import Cart, CartItem
from src.dto.cart_dto import AddCartItemDTO, UpdateCartItemDTO
from src.exceptions.app_exceptions import NotFoundError, BadRequestError, DatabaseError

class TestCartService(unittest.TestCase):
    def setUp(self):
        self.mock_repo = MagicMock()
        self.service = CartService(self.mock_repo)

    def test_get_cart_existing(self):
        fake_cart = Cart(user_id="u1", items={"p1": CartItem("p1", "Item 1", 10.0, 2)})
        self.mock_repo.get_cart.return_value = fake_cart
        
        result = self.service.get_cart("u1")
        self.assertEqual(result.cart_total, 20.0)
        self.assertEqual(len(result.items), 1)

    def test_get_cart_new(self):
        self.mock_repo.get_cart.return_value = None
        result = self.service.get_cart("u2")
        self.assertEqual(result.cart_total, 0.0)

    @patch('src.services.cart_service.urllib.request.urlopen')
    def test_add_item_success(self, mock_urlopen):
        # Mocking the two sequential API calls (Inventory, then Product)
        mock_inv_response = MagicMock()
        mock_inv_response.read.return_value = json.dumps({"data": {"available_quantity": 100}}).encode("utf-8")
        
        mock_prod_response = MagicMock()
        mock_prod_response.read.return_value = json.dumps({"data": {"name": "Test", "price": 15.0}}).encode("utf-8")
        
        # Return inventory response first, then product response
        mock_urlopen.return_value.__enter__.side_effect = [mock_inv_response, mock_prod_response]
        
        self.mock_repo.get_cart.return_value = Cart(user_id="u1")
        dto = AddCartItemDTO(product_id="p1", quantity=2)
        
        self.service.add_item("u1", dto)
        self.mock_repo.save_cart.assert_called_once()

    @patch('src.services.cart_service.urllib.request.urlopen')
    def test_add_item_insufficient_stock(self, mock_urlopen):
        mock_inv_response = MagicMock()
        mock_inv_response.read.return_value = json.dumps({"data": {"available_quantity": 1}}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_inv_response
        
        self.mock_repo.get_cart.return_value = Cart(user_id="u1")
        dto = AddCartItemDTO(product_id="p1", quantity=5)
        
        with self.assertRaises(BadRequestError):
            self.service.add_item("u1", dto)

    def test_update_item_success(self):
        fake_cart = Cart(user_id="u1", items={"p1": CartItem("p1", "Item 1", 10.0, 2)})
        self.mock_repo.get_cart.return_value = fake_cart
        
        dto = UpdateCartItemDTO(quantity=5)
        self.service.update_item("u1", "p1", dto)
        
        self.assertEqual(fake_cart.items["p1"].quantity, 5)
        self.mock_repo.save_cart.assert_called_once()

    def test_update_item_remove_zero_quantity(self):
        fake_cart = Cart(user_id="u1", items={"p1": CartItem("p1", "Item 1", 10.0, 2)})
        self.mock_repo.get_cart.return_value = fake_cart
        
        dto = UpdateCartItemDTO(quantity=0)
        self.service.update_item("u1", "p1", dto)
        
        self.assertNotIn("p1", fake_cart.items)

    def test_update_item_not_found(self):
        self.mock_repo.get_cart.return_value = None
        with self.assertRaises(NotFoundError):
            self.service.update_item("u1", "p1", UpdateCartItemDTO(quantity=5))

    def test_clear_cart(self):
        self.service.clear_cart("u1")
        self.mock_repo.delete_cart.assert_called_once_with("u1")

    def test_handle_sqs_event_order_created(self):
        payload = {"event_type": "ORDER_CREATED", "user_id": "u1", "order_id": "123"}
        self.service.handle_sqs_event(payload)
        self.mock_repo.delete_cart.assert_called_once_with("u1")

    def test_handle_sqs_event_error_raises_exception(self):
        self.mock_repo.delete_cart.side_effect = DatabaseError("DB Failed")
        payload = {"event_type": "ORDER_CREATED", "user_id": "u1", "order_id": "123"}
        with self.assertRaises(DatabaseError):
            self.service.handle_sqs_event(payload)