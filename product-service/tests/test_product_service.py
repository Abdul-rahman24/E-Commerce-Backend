# product-service/tests/test_product_service.py
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from src.services.product_service import ProductService
from src.dto.product_dto import CreateProductDTO
from src.models.product import Product

class TestProductService(unittest.TestCase):
    def setUp(self):
        # This runs before every test. We create a fake repository (DynamoDB mock)
        self.mock_repo = MagicMock()
        self.service = ProductService(repository=self.mock_repo)

    @patch('src.services.product_service.urllib.request.urlopen')
    def test_create_product_success(self, mock_urlopen):
        # 1. Arrange: Set up the fake data and fake responses
        mock_dto = CreateProductDTO(
            sku="SKU-TEST-123",
            name="Test Product",
            description="A product for unit testing",
            category="Electronics",
            brand="IDP",
            price=99.99,
            currency="USD"
        )
        
        # Tell our fake repository what to return when .create() is called
        fake_saved_product = Product(
            product_id="fake-uuid-1234",
            sku=mock_dto.sku,
            name=mock_dto.name,
            description=mock_dto.description,
            category=mock_dto.category,
            brand=mock_dto.brand,
            price=mock_dto.price,
            currency=mock_dto.currency,
            status="DRAFT",
            images=[],
            attributes={},
            is_deleted=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        self.mock_repo.create.return_value = fake_saved_product
        
        # Make the fake urllib (HTTP requests to Search/Inventory) pretend to succeed
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # 2. Act: Actually run the function we are testing
        result = self.service.create_product(mock_dto)

        # 3. Assert: Verify the function did exactly what it was supposed to do
        self.assertEqual(result.name, "Test Product")
        self.assertEqual(result.product_id, "fake-uuid-1234")
        self.mock_repo.create.assert_called_once() # Ensures DB was "called"
        self.assertEqual(mock_urlopen.call_count, 2) # Ensures Inventory and Search were "called"

    def test_get_product_success(self):
        # Arrange
        fake_product = Product(
            product_id="fake-uuid-1234", sku="SKU-123", name="Test", description="Test",
            category="Test", brand="Test", price=10.0, currency="USD", status="ACTIVE",
            images=[], attributes={}, is_deleted=False, created_at=datetime.now(), updated_at=datetime.now()
        )
        self.mock_repo.find_by_id.return_value = fake_product

        # Act
        result = self.service.get_product("fake-uuid-1234")

        # Assert
        self.assertEqual(result.product_id, "fake-uuid-1234")
        self.mock_repo.find_by_id.assert_called_with("fake-uuid-1234")