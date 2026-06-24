import requests
from datetime import datetime, timezone
from src.repositories.cart_repository import DynamoDBCartRepository
from src.models.cart import Cart, CartItem
from src.dto.cart_dto import AddCartItemDTO, UpdateCartItemDTO, CartResponseDTO, CartItemResponseDTO
from src.exceptions.app_exceptions import NotFoundError, BadRequestError, DatabaseError
from src.utils.logger import get_logger

logger = get_logger("CartService")

PRODUCT_SERVICE_URL = "http://127.0.0.1:8000/api/v1/products"
INVENTORY_SERVICE_URL = "http://127.0.0.1:8001/api/v1/inventory"

class CartService:
    def __init__(self, repository: DynamoDBCartRepository):
        self.repository = repository

    def _build_response_dto(self, cart: Cart) -> CartResponseDTO:
        item_dtos = [
            CartItemResponseDTO(
                product_id=item.product_id,
                name=item.name,
                price=item.price,
                quantity=item.quantity,
                item_total=item.price * item.quantity
            ) for item in cart.items.values()
        ]
        return CartResponseDTO(
            user_id=cart.user_id,
            items=item_dtos,
            cart_total=cart.total_price,
            updated_at=cart.updated_at
        )

    def get_cart(self, user_id: str) -> CartResponseDTO:
        cart = self.repository.get_cart(user_id)
        if not cart:
            cart = Cart(user_id=user_id)
        return self._build_response_dto(cart)

    def add_item(self, user_id: str, dto: AddCartItemDTO) -> CartResponseDTO:
        cart = self.repository.get_cart(user_id) or Cart(user_id=user_id)
        
        current_qty = cart.items[dto.product_id].quantity if dto.product_id in cart.items else 0
        desired_total_qty = current_qty + dto.quantity

        try:
            inv_resp = requests.get(f"{INVENTORY_SERVICE_URL}/{dto.product_id}", timeout=5)
            if inv_resp.status_code == 200:
                available = inv_resp.json()['data']['available_quantity']
                if desired_total_qty > available:
                    raise BadRequestError(f"Only {available} items available in stock.")
            elif inv_resp.status_code == 404:
                raise NotFoundError("Product not found in inventory.")
        except requests.exceptions.RequestException:
            logger.warning("Inventory service unreachable. Proceeding with risk.")

        try:
            prod_resp = requests.get(f"{PRODUCT_SERVICE_URL}/{dto.product_id}", timeout=5)
            if prod_resp.status_code == 404:
                raise NotFoundError("Product does not exist.")
            prod_data = prod_resp.json()['data']
        except requests.exceptions.RequestException:
            raise DatabaseError("Product service is unreachable.")

        cart.items[dto.product_id] = CartItem(
            product_id=dto.product_id,
            name=prod_data['name'],
            price=prod_data['price'],
            quantity=desired_total_qty
        )
        cart.updated_at = datetime.now(timezone.utc)
        
        saved_cart = self.repository.save_cart(cart)
        return self._build_response_dto(saved_cart)

    def update_item(self, user_id: str, product_id: str, dto: UpdateCartItemDTO) -> CartResponseDTO:
        cart = self.repository.get_cart(user_id)
        if not cart or product_id not in cart.items:
            raise NotFoundError("Item not found in cart.")

        if dto.quantity == 0:
            del cart.items[product_id]
        else:
            cart.items[product_id].quantity = dto.quantity
            
        cart.updated_at = datetime.now(timezone.utc)
        saved_cart = self.repository.save_cart(cart)
        return self._build_response_dto(saved_cart)

    def remove_item(self, user_id: str, product_id: str) -> CartResponseDTO:
        return self.update_item(user_id, product_id, UpdateCartItemDTO(quantity=0))

    def clear_cart(self, user_id: str) -> None:
        self.repository.delete_cart(user_id)