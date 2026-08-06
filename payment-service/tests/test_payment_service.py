import unittest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from src.services.payment_service import PaymentService
from src.models.payment import Payment
from src.dto.payment_dto import InitiatePaymentDTO, VerifyPaymentDTO, WebhookPayloadDTO
from src.exceptions.app_exceptions import NotFoundError

class TestPaymentService(unittest.TestCase):
    def setUp(self):
        self.mock_repo = MagicMock()
        # Mock save to return the exact entity it receives to prevent Pydantic Validation errors
        self.mock_repo.save.side_effect = lambda payment: payment
        
        self.service = PaymentService(self.mock_repo)
        
        self.fake_payment = Payment(
            payment_id="pay_123", order_id="ord_123", user_id="u1",
            amount=100.0, currency="USD", status="PENDING",
            provider="STRIPE", provider_transaction_id="tx_123",
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
        )

    def test_initiate_payment_success(self):
        dto = InitiatePaymentDTO(order_id="ord_123", amount=100.0, currency="USD", provider="STRIPE")
        
        result = self.service.initiate_payment("u1", dto)
        
        self.mock_repo.save.assert_called_once()
        self.assertEqual(result.order_id, "ord_123")
        self.assertEqual(result.amount, 100.0)
        self.assertEqual(result.status, "PENDING")
        self.assertIsNotNone(result.client_secret)

    def test_verify_payment_success(self):
        self.mock_repo.get_by_id.return_value = self.fake_payment
        dto = VerifyPaymentDTO(payment_id="pay_123", provider_transaction_id="tx_999")
        
        result = self.service.verify_payment(dto)
        
        self.mock_repo.save.assert_called_once()
        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual(self.fake_payment.provider_transaction_id, "tx_999")

    def test_verify_payment_not_found(self):
        self.mock_repo.get_by_id.return_value = None
        dto = VerifyPaymentDTO(payment_id="pay_123", provider_transaction_id="tx_999")
        
        with self.assertRaises(NotFoundError):
            self.service.verify_payment(dto)

    def test_process_webhook_succeeded(self):
        self.mock_repo.get_by_provider_tx_id.return_value = self.fake_payment
        payload = WebhookPayloadDTO(event_type="payment_intent.succeeded", provider_transaction_id="tx_123", status="succeeded")
        
        result = self.service.process_webhook(payload)
        
        self.mock_repo.save.assert_called_once()
        self.assertEqual(self.fake_payment.status, "SUCCESS")
        self.assertEqual(result["status"], "processed")

    def test_process_webhook_failed(self):
        self.mock_repo.get_by_provider_tx_id.return_value = self.fake_payment
        payload = WebhookPayloadDTO(event_type="payment_intent.payment_failed", provider_transaction_id="tx_123", status="failed")
        
        result = self.service.process_webhook(payload)
        
        self.mock_repo.save.assert_called_once()
        self.assertEqual(self.fake_payment.status, "FAILED")

    def test_process_webhook_unknown_transaction(self):
        self.mock_repo.get_by_provider_tx_id.return_value = None
        payload = WebhookPayloadDTO(event_type="payment_intent.succeeded", provider_transaction_id="tx_unknown", status="succeeded")
        
        result = self.service.process_webhook(payload)
        
        self.mock_repo.save.assert_not_called()
        self.assertEqual(result["status"], "ignored")