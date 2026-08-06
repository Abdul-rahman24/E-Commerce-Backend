import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from src.services.product_service import ProductService
from src.dto.product_dto import CreateProductDTO, UpdateProductDTO
from src.models.product import Product
from src.exceptions.app_exceptions import NotFoundError
import urllib.error
from src.exceptions.app_exceptions import NotFoundError

class TestProductService(unittest.TestCase):
    def setUp(self):
        # Create a fake database repository
        self.mock_repo = MagicMock()
        self.service = ProductService(repository=self.mock_repo)

    @patch('src.services.product_service.urllib.request.urlopen')
    def test_create_product_success(self, mock_urlopen):
        mock_dto = CreateProductDTO(
            sku="SKU-TEST-123", name="Test Product", description="A test product description",
            category="Electronics", brand="IDP", price=99.99, currency="USD", images=[], attributes={}
        )
        fake_saved_product = Product(
            product_id="fake-uuid-1234", sku=mock_dto.sku, name=mock_dto.name, description=mock_dto.description,
            category=mock_dto.category, brand=mock_dto.brand, price=mock_dto.price, currency=mock_dto.currency,
            status="DRAFT", images=[], attributes={}, is_deleted=False, created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
        )
        
        self.mock_repo.create.return_value = fake_saved_product
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.service.create_product(mock_dto)

        self.assertEqual(result.name, "Test Product")
        self.assertEqual(result.product_id, "fake-uuid-1234")
        self.mock_repo.create.assert_called_once()
        self.assertEqual(mock_urlopen.call_count, 2)

    def test_get_product_success(self):
        fake_product = Product(
            product_id="fake-uuid-1234", sku="SKU-123", name="Test", description="Test",
            category="Test", brand="Test", price=10.0, currency="USD", status="ACTIVE",
            images=[], attributes={}, is_deleted=False, created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
        )
        self.mock_repo.find_by_id.return_value = fake_product

        result = self.service.get_product("fake-uuid-1234")

        self.assertEqual(result.product_id, "fake-uuid-1234")
        self.mock_repo.find_by_id.assert_called_with("fake-uuid-1234")

    # --- NEW TESTS BELOW ---

    def test_get_product_not_found(self):
        # Simulate database returning None
        self.mock_repo.find_by_id.return_value = None

        # Verify that our service throws the correct custom error
        with self.assertRaises(NotFoundError):
            self.service.get_product("non-existent-id")

    def test_get_all_products(self):
        # Simulate returning an empty list
        self.mock_repo.find_all.return_value = []
        
        result = self.service.get_all_products()
        
        self.assertEqual(result, [])
        self.mock_repo.find_all.assert_called_once()

    def test_update_product_success(self):
        # 1. Arrange
        fake_existing_product = Product(
            product_id="fake-uuid-1234", sku="SKU-123", name="Old Name", description="Old",
            category="Test", brand="Test", price=10.0, currency="USD", status="ACTIVE",
            images=[], attributes={}, is_deleted=False, created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
        )
        self.mock_repo.find_by_id.return_value = fake_existing_product
        self.mock_repo.update.return_value = fake_existing_product
        
        update_dto = UpdateProductDTO(name="New Awesome Name", price=25.00)

        # 2. Act
        result = self.service.update_product("fake-uuid-1234", update_dto)

        # 3. Assert
        self.assertEqual(result.name, "New Awesome Name")
        self.assertEqual(result.price, 25.00)
        self.mock_repo.update.assert_called_once()

    def test_delete_product_success(self):
        # Arrange
        fake_existing_product = Product(
            product_id="fake-uuid-1234", sku="SKU-123", name="Old Name", description="Old",
            category="Test", brand="Test", price=10.0, currency="USD", status="ACTIVE",
            images=[], attributes={}, is_deleted=False, created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
        )
        # Mock get_product so the verification passes
        self.mock_repo.find_by_id.return_value = fake_existing_product
        
        # Act
        self.service.delete_product("fake-uuid-1234")

        # Assert
        self.mock_repo.delete.assert_called_once_with("fake-uuid-1234")

    @patch('src.services.product_service.urllib.request.urlopen')
    def test_create_product_network_failure_handled(self, mock_urlopen):
        """Tests that the product is still created even if Inventory/Search APIs fail"""
        # 1. Arrange
        mock_dto = CreateProductDTO(
            sku="SKU-ERR-123", name="Resilient Product", description="Test",
            category="Test", brand="Test", price=50.0, currency="USD", images=[], attributes={}
        )
        fake_saved_product = Product(
            product_id="fake-uuid-9999", sku=mock_dto.sku, name=mock_dto.name, description=mock_dto.description,
            category=mock_dto.category, brand=mock_dto.brand, price=mock_dto.price, currency=mock_dto.currency,
            status="DRAFT", images=[], attributes={}, is_deleted=False, 
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
        )
        
        self.mock_repo.create.return_value = fake_saved_product
        
        # Simulate a network error occurring when trying to call other services
        mock_urlopen.side_effect = urllib.error.URLError("Service unreachable")

        # 2. Act
        result = self.service.create_product(mock_dto)

        # 3. Assert
        # The service should catch the URLError, log it, and still return the product successfully
        self.assertEqual(result.product_id, "fake-uuid-9999")
        self.mock_repo.create.assert_called_once()
        self.assertEqual(mock_urlopen.call_count, 2) # Attempted both Inventory and Search calls

    def test_delete_product_not_found_throws_error(self):
        """Tests that deleting a non-existent product throws a NotFoundError"""
        # Simulate the database not finding the product
        self.mock_repo.find_by_id.return_value = None
        
        # Verify that calling delete throws the expected NotFoundError
        with self.assertRaises(NotFoundError):
            self.service.delete_product("missing-id-123")