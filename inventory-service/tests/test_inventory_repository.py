import unittest
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError
from src.repositories.inventory_repository import DynamoDBInventoryRepository
from src.exceptions.app_exceptions import DatabaseError, ConflictError, NotFoundError

class TestDynamoDBInventoryRepository(unittest.TestCase):
    @patch('src.repositories.inventory_repository.boto3.resource')
    def setUp(self, mock_boto_resource):
        self.mock_table = MagicMock()
        mock_boto_resource.return_value.Table.return_value = self.mock_table
        self.repo = DynamoDBInventoryRepository()

    def test_get_by_product_id_success(self):
        self.mock_table.get_item.return_value = {
            'Item': {'productId': 'p1', 'availableQuantity': 10, 'reservedQuantity': 2, 'updated_at': '2023-01-01T12:00:00+00:00'}
        }
        result = self.repo.get_by_product_id('p1')
        self.assertEqual(result.available_quantity, 10)

    def test_get_by_product_id_not_found(self):
        self.mock_table.get_item.return_value = {}
        with self.assertRaises(NotFoundError):
            self.repo.get_by_product_id('p1')

    def test_get_by_product_id_client_error(self):
        self.mock_table.get_item.side_effect = ClientError({"Error": {"Code": "500", "Message": "Error"}}, "get_item")
        with self.assertRaises(DatabaseError):
            self.repo.get_by_product_id('p1')

    def test_atomic_update_success(self):
        self.mock_table.update_item.return_value = {
            'Attributes': {'productId': 'p1', 'availableQuantity': 15, 'reservedQuantity': 0, 'updated_at': '2023-01-01T12:00:00+00:00'}
        }
        result = self.repo.atomic_update('p1', 5, 0)
        self.assertEqual(result.available_quantity, 15)

    def test_atomic_update_conflict(self):
        self.mock_table.update_item.side_effect = ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "update_item")
        with self.assertRaises(ConflictError):
            self.repo.atomic_update('p1', -50, 0)

    def test_atomic_update_client_error(self):
        self.mock_table.update_item.side_effect = ClientError({"Error": {"Code": "500"}}, "update_item")
        with self.assertRaises(DatabaseError):
            self.repo.atomic_update('p1', 5, 0)

    def test_initialize_inventory(self):
        result = self.repo.initialize_inventory('p1', 100)
        self.assertEqual(result.available_quantity, 100)
        self.mock_table.put_item.assert_called_once()