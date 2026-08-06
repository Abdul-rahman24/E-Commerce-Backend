import unittest
import urllib.error
import os
from unittest.mock import MagicMock, patch

# FIX: Inject a fake URL into the test environment BEFORE importing the service
os.environ["PRODUCT_SERVICE_URL"] = "http://fake-test-url.com/v1/products"

from src.services.inventory_service import InventoryService
from src.dto.inventory_dto import InventoryTransactionDTO
from src.exceptions.app_exceptions import BadRequestError, DatabaseError

class TestInventoryService(unittest.TestCase):
    def setUp(self):
        self.mock_repo = MagicMock()
        self.service = InventoryService(self.mock_repo)

    def test_get_inventory(self):
        self.service.get_inventory("p1")
        self.mock_repo.get_by_product_id.assert_called_once_with("p1")

    def test_initialize_stock(self):
        self.service.initialize_stock("p1")
        self.mock_repo.initialize_inventory.assert_called_once_with("p1", 0)

    @patch('src.services.inventory_service.urllib.request.urlopen')
    def test_restock_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        dto = InventoryTransactionDTO(product_id="p1", quantity=10)
        self.service.restock(dto)
        self.mock_repo.atomic_update.assert_called_once_with("p1", 10, 0)

    @patch('src.services.inventory_service.urllib.request.urlopen')
    def test_restock_product_not_found(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError('http://test', 404, 'Not Found', {}, None)
        dto = InventoryTransactionDTO(product_id="p1", quantity=10)
        with self.assertRaises(BadRequestError):
            self.service.restock(dto)

    @patch('src.services.inventory_service.urllib.request.urlopen')
    def test_restock_timeout(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError("Timeout")
        dto = InventoryTransactionDTO(product_id="p1", quantity=10)
        with self.assertRaises(DatabaseError):
            self.service.restock(dto)

    def test_reserve_stock(self):
        dto = InventoryTransactionDTO(product_id="p1", quantity=5)
        self.service.reserve_stock(dto)
        self.mock_repo.atomic_update.assert_called_once_with("p1", -5, 5)

    def test_handle_sqs_event_order_created(self):
        payload = {"event_type": "ORDER_CREATED", "order_id": "1", "items": [{"product_id": "p1", "quantity": 2}]}
        self.service.handle_sqs_event(payload)
        self.mock_repo.atomic_update.assert_called_once_with("p1", -2, 2)

    def test_handle_sqs_event_order_cancelled(self):
        payload = {"event_type": "ORDER_CANCELLED", "order_id": "1", "items": [{"product_id": "p1", "quantity": 2}]}
        self.service.handle_sqs_event(payload)
        self.mock_repo.atomic_update.assert_called_once_with("p1", 2, -2)

    def test_handle_sqs_event_error_raises_exception(self):
        self.mock_repo.atomic_update.side_effect = Exception("DB Error")
        payload = {"event_type": "ORDER_CREATED", "order_id": "1", "items": [{"product_id": "p1", "quantity": 2}]}
        with self.assertRaises(Exception):
            self.service.handle_sqs_event(payload)