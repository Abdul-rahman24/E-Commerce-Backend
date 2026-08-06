import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from src.main import app
from src.controllers.payment_controller import get_payment_service
from src.dto.payment_dto import PaymentResponseDTO

class TestPaymentController(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.mock_service = MagicMock()
        app.dependency_overrides[get_payment_service] = lambda: self.mock_service
        
        self.headers = {"x-user-id": "u1"}
        
        self.fake_response = PaymentResponseDTO(
            payment_id="pay_123", order_id="ord_123", amount=100.0, currency="USD", 
            status="PENDING", provider="STRIPE", client_secret="secret",
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
        )

    def test_initiate_payment(self):
        self.mock_service.initiate_payment.return_value = self.fake_response
        response = self.client.post("/v1/payments/initiate", json={"order_id": "ord_123", "amount": 100.0}, headers=self.headers)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_verify_payment(self):
        self.mock_service.verify_payment.return_value = self.fake_response
        response = self.client.post("/v1/payments/verify", json={"payment_id": "pay_123", "provider_transaction_id": "tx_123"})
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_payment_webhook(self):
        self.mock_service.process_webhook.return_value = {"status": "processed"}
        response = self.client.post("/v1/payments/webhook", json={"event_type": "success", "provider_transaction_id": "tx_123", "status": "ok"})
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "processed")

    @patch('src.controllers.payment_controller.time.sleep') # Patch sleep so the test runs fast!
    def test_process_direct_payment_success(self, mock_sleep):
        response = self.client.post("/v1/payments/pay", json={"order_id": "ord_123", "amount": 100.0}, headers=self.headers)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(response.json()["status"], "PAID")
        mock_sleep.assert_called_once_with(1)

    @patch('src.controllers.payment_controller.uuid.uuid4')
    def test_process_direct_payment_exception(self, mock_uuid):
        mock_uuid.side_effect = Exception("Simulated Failure")
        response = self.client.post("/v1/payments/pay", json={"order_id": "ord_123", "amount": 100.0}, headers=self.headers)
        
        self.assertEqual(response.status_code, 500)