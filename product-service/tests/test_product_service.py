import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from src.services.product_service import ProductService
from src.dto.product_dto import CreateProductDTO
from src.models.product import Product

class TestProductService(unittest.TestCase):
    def setUp(self):
        # Create a fake database repository
        self.mock_repo = MagicMock()
        self.service = ProductService(repository=self.mock_repo)

    # We patch urllib to prevent real API calls to AWS/Inventory during tests
    @patch('src.services.product_service.urllib.request.urlopen')
    def test_create_product_success(self, mock_urlopen):
        # 1. Arrange: Create a valid DTO exactly matching your requirements
        mock_dto = CreateProductDTO(
            sku="SKU-TEST-123",
            name="Test Product",
            description="A test product description",
            category="Electronics",
            brand="IDP",
            price=99.99,
            currency="USD",
            images=[],
            attributes={}
        )
        
        # Create a valid fake returned Product with timezone-aware datetimes
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
        
        # Tell the mock repo to return our fake product
        self.mock_repo.create.return_value = fake_saved_product
        
        # Tell the mock network request to return a successful 200 OK
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # 2. Act: Call the real service method
        result = self.service.create_product(mock_dto)

        # 3. Assert: Verify the logic worked as expected
        self.assertEqual(result.name, "Test Product")
        self.assertEqual(result.product_id, "fake-uuid-1234")
        self.mock_repo.create.assert_called_once()
        self.assertEqual(mock_urlopen.call_count, 2) # Inventory + Search calls

    def test_get_product_success(self):
        # Arrange
        fake_product = Product(
            product_id="fake-uuid-1234",
            sku="SKU-123",
            name="Test",
            description="Test",
            category="Test",
            brand="Test",
            price=10.0,
            currency="USD",
            status="ACTIVE",
            images=[],
            attributes={},
            is_deleted=False,
            created_at=datetime.now(timezone.utc), # Using timezone-aware datetime
            updated_at=datetime.now(timezone.utc)  # Using timezone-aware datetime
        )
        self.mock_repo.find_by_id.return_value = fake_product

        # Act
        result = self.service.get_product("fake-uuid-1234")

        # Assert
        self.assertEqual(result.product_id, "fake-uuid-1234")
        self.mock_repo.find_by_id.assert_called_with("fake-uuid-1234")