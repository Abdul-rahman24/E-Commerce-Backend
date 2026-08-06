import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from botocore.exceptions import ClientError
from src.repositories.product_repository import DynamoDBProductRepository
from src.models.product import Product
from src.exceptions.app_exceptions import DatabaseError

class TestDynamoDBProductRepository(unittest.TestCase):
    @patch('boto3.resource')
    def setUp(self, mock_boto_resource):
        # Mock DynamoDB resource and table
        self.mock_table = MagicMock()
        mock_boto_resource.return_value.Table.return_value = self.mock_table
        self.repo = DynamoDBProductRepository()

    def test_create_success(self):
        prod = Product(
            product_id="p123", sku="SKU123", name="Test Product", description="Desc",
            category="Cat", brand="Brand", price=10.0, currency="USD", status="DRAFT",
            images=[], attributes={}, is_deleted=False,
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
        )
        result = self.repo.create(prod)
        self.assertEqual(result.product_id, "p123")
        self.mock_table.put_item.assert_called_once()

    def test_create_client_error_raises_database_error(self):
        self.mock_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "DynamoDB Error"}}, "put_item"
        )
        prod = Product(
            product_id="p123", sku="SKU123", name="Test Product", description="Desc",
            category="Cat", brand="Brand", price=10.0, currency="USD", status="DRAFT",
            images=[], attributes={}, is_deleted=False,
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
        )
        with self.assertRaises(DatabaseError):
            self.repo.create(prod)

    def test_find_by_id_success(self):
        now_iso = datetime.now(timezone.utc).isoformat()
        self.mock_table.get_item.return_value = {
            'Item': {
                'productId': 'p123', 'sku': 'SKU123', 'name': 'Test Product', 'description': 'Desc',
                'category': 'Cat', 'brand': 'Brand', 'price': 10.0, 'currency': 'USD',
                'status': 'DRAFT', 'images': [], 'attributes': {}, 'is_deleted': False,
                'created_at': now_iso, 'updated_at': now_iso
            }
        }
        res = self.repo.find_by_id('p123')
        self.assertIsNotNone(res)
        self.assertEqual(res.product_id, 'p123')

    def test_find_by_id_client_error_raises_database_error(self):
        self.mock_table.get_item.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "DynamoDB Error"}}, "get_item"
        )
        with self.assertRaises(DatabaseError):
            self.repo.find_by_id('p123')

    def test_find_all_success(self):
        now_iso = datetime.now(timezone.utc).isoformat()
        self.mock_table.scan.return_value = {
            'Items': [{
                'productId': 'p123', 'sku': 'SKU123', 'name': 'Test Product', 'description': 'Desc',
                'category': 'Cat', 'brand': 'Brand', 'price': 10.0, 'currency': 'USD',
                'status': 'DRAFT', 'images': [], 'attributes': {}, 'is_deleted': False,
                'created_at': now_iso, 'updated_at': now_iso
            }]
        }
        res = self.repo.find_all()
        self.assertEqual(len(res), 1)

    def test_delete_success(self):
        self.repo.delete('p123')
        self.mock_table.delete_item.assert_called_once_with(Key={'productId': 'p123'})

    def test_delete_client_error_raises_database_error(self):
        self.mock_table.delete_item.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "DynamoDB Error"}}, "delete_item"
        )
        with self.assertRaises(DatabaseError):
            self.repo.delete('p123')