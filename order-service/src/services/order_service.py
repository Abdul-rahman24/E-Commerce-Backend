import uuid
import requests
from datetime import datetime, timezone
from typing import List
from src.repositories.order_repository import DynamoDBOrderRepository
from src.models.order import Order, OrderItem
from src.dto.order_dto import OrderResponseDTO, OrderStatusUpdateDTO, OrderItemResponseDTO
from src.exceptions.app_exceptions import NotFoundError, BadRequestError, DatabaseError, ConflictError
from src.utils.logger import get_logger

logger = get_logger("OrderService")

CART_SERVICE_URL = "http://127.0.0.1:8002/api/v1/cart"
INVENTORY_SERVICE_URL = "http://127.0.0.1:8001/api/v1/inventory"

class OrderService:
    def __init__(self, repository: DynamoDBOrderRepository):
        self.repository = repository

    def _build_response_dto(self, order: Order) -> OrderResponseDTO:
        items = [OrderItemResponseDTO(**item.__dict__) for item in order.items]
        return OrderResponseDTO(
            order_id=order.order_id,
            user_id=order.user_id,
            items=items,
            total_amount=order.total_amount,
            currency=order.currency,
            status=order.status,
            created_at=order.created_at,
            updated_at=order.updated_at
        )

    def create_order_from_cart(self, user_id: str) -> OrderResponseDTO:
        # 1. Fetch Cart
        headers = {"x-user-id": user_id}
        try:
            cart_resp = requests.get(f"{CART_SERVICE_URL}/", headers=headers, timeout=5)
            cart_data = cart_resp.json().get('data')
            if not cart_data or not cart_data['items']:
                raise BadRequestError("Cannot create order: Cart is empty.")
        except requests.exceptions.RequestException:
            raise DatabaseError("Cart service is unreachable.")

        # 2. Reserve Inventory for each item
        for item in cart_data['items']:
            payload = {"product_id": item['product_id'], "quantity": item['quantity']}
            try:
                inv_resp = requests.post(f"{INVENTORY_SERVICE_URL}/reserve", json=payload, timeout=5)
                if inv_resp.status_code != 200:
                    # In a real system, you would reverse the already reserved items here (Saga Pattern)
                    raise ConflictError(f"Insufficient stock for {item['name']}")
            except requests.exceptions.RequestException:
                raise DatabaseError("Inventory service is unreachable.")

        # 3. Create Order
        order_items = [
            OrderItem(product_id=i['product_id'], name=i['name'], price=i['price'], quantity=i['quantity'])
            for i in cart_data['items']
        ]
        
        order = Order(
            order_id=f"ord_{uuid.uuid4().hex[:10]}",
            user_id=user_id,
            items=order_items,
            total_amount=cart_data['cart_total'],
            currency="USD",
            status="PENDING_PAYMENT",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        saved_order = self.repository.save(order)

        # 4. Clear the Cart
        try:
            requests.delete(f"{CART_SERVICE_URL}/", headers=headers, timeout=5)
        except requests.exceptions.RequestException:
            logger.warning(f"Failed to clear cart for user {user_id}. Order {order.order_id} created.")

        return self._build_response_dto(saved_order)

    def get_order(self, order_id: str) -> OrderResponseDTO:
        order = self.repository.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order not found")
        return self._build_response_dto(order)

    def get_user_orders(self, user_id: str) -> List[OrderResponseDTO]:
        orders = self.repository.get_by_user_id(user_id)
        return [self._build_response_dto(o) for o in orders]

    def update_status(self, order_id: str, dto: OrderStatusUpdateDTO) -> OrderResponseDTO:
        order = self.repository.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order not found")
            
        order.status = dto.status.upper()
        order.updated_at = datetime.now(timezone.utc)
        
        # If order is shipped/completed, deduct inventory permanently
        if order.status in ["SHIPPED", "COMPLETED"]:
            for item in order.items:
                try:
                    requests.post(f"{INVENTORY_SERVICE_URL}/deduct", json={"product_id": item.product_id, "quantity": item.quantity})
                except Exception as e:
                    logger.error(f"Failed to deduct stock for {item.product_id}: {str(e)}")

        return self._build_response_dto(self.repository.save(order))

    def cancel_order(self, order_id: str) -> OrderResponseDTO:
        order = self.repository.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order not found")
            
        if order.status in ["SHIPPED", "COMPLETED"]:
            raise BadRequestError("Cannot cancel a shipped or completed order.")
            
        order.status = "CANCELLED"
        order.updated_at = datetime.now(timezone.utc)
        
        # Release the reserved inventory back to available stock
        for item in order.items:
            try:
                requests.post(f"{INVENTORY_SERVICE_URL}/release", json={"product_id": item.product_id, "quantity": item.quantity})
            except Exception as e:
                logger.error(f"Failed to release stock for {item.product_id}: {str(e)}")

        return self._build_response_dto(self.repository.save(order))