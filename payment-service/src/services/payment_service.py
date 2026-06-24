import uuid
from datetime import datetime, timezone
from src.repositories.payment_repository import DynamoDBPaymentRepository
from src.models.payment import Payment
from src.dto.payment_dto import InitiatePaymentDTO, VerifyPaymentDTO, WebhookPayloadDTO, PaymentResponseDTO
from src.exceptions.app_exceptions import NotFoundError, BadRequestError
from src.utils.logger import get_logger

logger = get_logger("PaymentService")

class PaymentService:
    def __init__(self, repository: DynamoDBPaymentRepository):
        self.repository = repository

    def _build_response_dto(self, payment: Payment, client_secret: str = None) -> PaymentResponseDTO:
        return PaymentResponseDTO(
            payment_id=payment.payment_id,
            order_id=payment.order_id,
            amount=payment.amount,
            currency=payment.currency,
            status=payment.status,
            provider=payment.provider,
            client_secret=client_secret,
            created_at=payment.created_at,
            updated_at=payment.updated_at
        )

    def initiate_payment(self, user_id: str, dto: InitiatePaymentDTO) -> PaymentResponseDTO:
        payment_id = f"pay_{uuid.uuid4().hex[:12]}"
        
        # MOCK: Call to Stripe/External Provider would go here
        # E.g., stripe.PaymentIntent.create(amount=dto.amount, currency=dto.currency)
        mock_client_secret = f"secret_{uuid.uuid4().hex}"
        
        payment = Payment(
            payment_id=payment_id,
            order_id=dto.order_id,
            user_id=user_id,
            amount=dto.amount,
            currency=dto.currency,
            status="PENDING",
            provider=dto.provider,
            provider_transaction_id=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        saved_payment = self.repository.save(payment)
        logger.info(f"Payment {payment_id} initiated for Order {dto.order_id}")
        return self._build_response_dto(saved_payment, client_secret=mock_client_secret)

    def verify_payment(self, dto: VerifyPaymentDTO) -> PaymentResponseDTO:
        payment = self.repository.get_by_id(dto.payment_id)
        if not payment:
            raise NotFoundError("Payment record not found")

        # MOCK: Verify with provider using the transaction ID
        # If valid, update our database
        payment.status = "SUCCESS"
        payment.provider_transaction_id = dto.provider_transaction_id
        payment.updated_at = datetime.now(timezone.utc)
        
        saved_payment = self.repository.save(payment)
        logger.info(f"Payment {dto.payment_id} successfully verified")
        return self._build_response_dto(saved_payment)

    def process_webhook(self, payload: WebhookPayloadDTO) -> dict:
        """Handles asynchronous callbacks from the payment gateway."""
        logger.info(f"Received webhook event: {payload.event_type} for TxID {payload.provider_transaction_id}")
        
        payment = self.repository.get_by_provider_tx_id(payload.provider_transaction_id)
        if not payment:
            logger.warning("Webhook received for unknown transaction ID")
            return {"status": "ignored", "reason": "unknown_transaction"}
            
        if payload.event_type == "payment_intent.succeeded":
            payment.status = "SUCCESS"
        elif payload.event_type == "payment_intent.payment_failed":
            payment.status = "FAILED"
            
        payment.updated_at = datetime.now(timezone.utc)
        self.repository.save(payment)
        
        return {"status": "processed", "payment_id": payment.payment_id}