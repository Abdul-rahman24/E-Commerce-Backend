import unittest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from src.main import app
from src.controllers.inventory_controller import get_inventory_service
from src.models.inventory import Inventory
from datetime import datetime, timezone

class TestInventoryController(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.mock_service = MagicMock()
        # Override the dependency so the controller uses our mock service instead of the real DB
        app.dependency_overrides[get_inventory_service] = lambda: self.mock_service

    def test_get_inventory(self):
        fake_inv = Inventory(
            product_id="p1", available_quantity=10, reserved_quantity=2, 
            updated_at=datetime.now(timezone.utc)
        )
        self.mock_service.get_inventory.return_value = fake_inv
        
        response = self.client.get("/p1")
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(response.json()["data"]["available_quantity"], 10)

    def test_restock(self):
        fake_inv = Inventory(
            product_id="p1", available_quantity=20, reserved_quantity=0, 
            updated_at=datetime.now(timezone.utc)
        )
        self.mock_service.restock.return_value = fake_inv
        
        response = self.client.post("/restock", json={"product_id": "p1", "quantity": 10})
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_reserve(self):
        fake_inv = Inventory(
            product_id="p1", available_quantity=10, reserved_quantity=10, 
            updated_at=datetime.now(timezone.utc)
        )
        self.mock_service.reserve_stock.return_value = fake_inv
        
        response = self.client.post("/reserve", json={"product_id": "p1", "quantity": 10})
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_release(self):
        fake_inv = Inventory(
            product_id="p1", available_quantity=20, reserved_quantity=0, 
            updated_at=datetime.now(timezone.utc)
        )
        self.mock_service.release_stock.return_value = fake_inv
        
        response = self.client.post("/release", json={"product_id": "p1", "quantity": 10})
        
        self.assertEqual(response.status_code, 200)

    def test_deduct(self):
        fake_inv = Inventory(
            product_id="p1", available_quantity=10, reserved_quantity=0, 
            updated_at=datetime.now(timezone.utc)
        )
        self.mock_service.deduct_stock.return_value = fake_inv
        
        response = self.client.post("/deduct", json={"product_id": "p1", "quantity": 10})
        
        self.assertEqual(response.status_code, 200)

    def test_initialize(self):
        fake_inv = Inventory(
            product_id="p1", available_quantity=0, reserved_quantity=0, 
            updated_at=datetime.now(timezone.utc)
        )
        self.mock_service.initialize_stock.return_value = fake_inv
        
        response = self.client.post("/initialize", json={"product_id": "p1"})
        
        self.assertEqual(response.status_code, 200)

    def test_validation_error(self):
        # Send an invalid request (missing the required 'quantity' field) to hit the exception handler
        response = self.client.post("/restock", json={"product_id": "p1"})
        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.json()["success"])