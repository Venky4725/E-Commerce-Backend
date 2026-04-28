"""
Cart service for Redis-backed shopping cart
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.redis_client import redis_client
from app.schemas.cart_schema import CartCreate, CartResponse
from app.models.product import Product

class CartService:
    @staticmethod
    def _redis_error(exc: Exception) -> RuntimeError:
        return RuntimeError(f"Redis cart store is unavailable: {exc}")

    @staticmethod
    async def _get_cart_key(user_id: int) -> str:
        """Generate Redis key for user cart"""
        return f"cart:user:{user_id}"
    
    @staticmethod
    async def create_cart(user_id: int) -> CartResponse:
        """Create a new cart for user in Redis"""
        cart_key = await CartService._get_cart_key(user_id)
        now = datetime.utcnow()
        cart_data = {
            "user_id": user_id,
            "items": [],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        # Set cart in Redis with expiration (e.g., 7 days)
        try:
            redis_client.setex(cart_key, 604800, json.dumps(cart_data))
        except RedisError as exc:
            raise CartService._redis_error(exc)
        
        return CartResponse(
            id=user_id,  # Using user_id as cart ID for simplicity
            user_id=user_id,
            created_at=now,
            updated_at=now
        )

    @staticmethod
    async def get_cart(user_id: int) -> CartResponse:
        """Get cart for user from Redis"""
        cart_key = await CartService._get_cart_key(user_id)
        
        try:
            cart_json = redis_client.get(cart_key)
        except RedisError as exc:
            raise CartService._redis_error(exc)
        
        if cart_json:
            cart_data = json.loads(cart_json)
            return CartResponse(
                id=cart_data["user_id"],
                user_id=cart_data["user_id"],
                created_at=datetime.fromisoformat(cart_data.get("created_at", datetime.utcnow().isoformat())),
                updated_at=datetime.fromisoformat(cart_data.get("updated_at", datetime.utcnow().isoformat()))
            )
        return None

    @staticmethod
    async def add_item(user_id: int, product_id: int, quantity: int):
        """Add item to user's cart"""
        cart_key = await CartService._get_cart_key(user_id)
        
        # Get existing cart and update it
        try:
            cart_json = redis_client.get(cart_key)
        except RedisError as exc:
            raise CartService._redis_error(exc)
        
        if cart_json:
            cart_data = json.loads(cart_json)
        else:
            # Create new cart if it doesn't exist
            now = datetime.utcnow()
            cart_data = {
                "user_id": user_id,
                "items": [],
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }
            
        # Check if item already exists
        existing_item = next((item for item in cart_data["items"] if item["product_id"] == product_id), None)
        if existing_item:
            # Update quantity if item exists
            existing_item["quantity"] += quantity
        else:
            # Add new item
            cart_data["items"].append({
                "product_id": product_id,
                "quantity": quantity
            })
            
        # Update timestamp and save back to Redis
        cart_data["updated_at"] = datetime.utcnow().isoformat()
        try:
            redis_client.setex(cart_key, 604800, json.dumps(cart_data))
        except RedisError as exc:
            raise CartService._redis_error(exc)

    @staticmethod
    async def update_item(user_id: int, product_id: int, quantity: int):
        """Update item quantity in user's cart"""
        cart_key = await CartService._get_cart_key(user_id)
        
        try:
            cart_json = redis_client.get(cart_key)
        except RedisError as exc:
            raise CartService._redis_error(exc)
        
        if cart_json:
            cart_data = json.loads(cart_json)
            # Find and update the item
            for item in cart_data["items"]:
                if item["product_id"] == product_id:
                    item["quantity"] = quantity
                    break
                    
            # Update timestamp and save back to Redis
            cart_data["updated_at"] = datetime.utcnow().isoformat()
            try:
                redis_client.setex(cart_key, 604800, json.dumps(cart_data))
            except RedisError as exc:
                raise CartService._redis_error(exc)

    @staticmethod
    async def remove_item(user_id: int, product_id: int):
        """Remove item from user's cart"""
        cart_key = await CartService._get_cart_key(user_id)
        
        try:
            cart_json = redis_client.get(cart_key)
        except RedisError as exc:
            raise CartService._redis_error(exc)
        
        if cart_json:
            cart_data = json.loads(cart_json)
            # Filter out the item to remove
            cart_data["items"] = [item for item in cart_data["items"] if item["product_id"] != product_id]
            
            # Update timestamp and save back to Redis  
            cart_data["updated_at"] = datetime.utcnow().isoformat()
            try:
                redis_client.setex(cart_key, 604800, json.dumps(cart_data))
            except RedisError as exc:
                raise CartService._redis_error(exc)

    @staticmethod
    async def calculate_total(user_id: int, db: AsyncSession) -> float:
        """Calculate total for user's cart using Redis items and DB prices."""
        items = await CartService.get_cart_items(user_id)
        if not items:
            return 0.0

        product_ids = [item["product_id"] for item in items]
        result = await db.execute(select(Product).where(Product.id.in_(product_ids)))
        products = {product.id: product for product in result.scalars().all()}
        return sum(
            products[item["product_id"]].price * item["quantity"]
            for item in items
            if item["product_id"] in products
        )

    @staticmethod
    async def get_cart_items(user_id: int) -> list:
        """Get all items in user's cart"""
        cart_key = await CartService._get_cart_key(user_id)
        try:
            cart_json = redis_client.get(cart_key)
        except RedisError as exc:
            raise CartService._redis_error(exc)
        
        if cart_json:
            cart_data = json.loads(cart_json)
            return cart_data.get("items", [])
        return []
    
    @staticmethod
    async def update_cart(user_id: int, cart: CartCreate) -> CartResponse:
        """Update cart for a user"""
        cart_key = await CartService._get_cart_key(user_id)
        now = datetime.utcnow()
        
        # Retrieve existing cart or create new one
        try:
            cart_json = redis_client.get(cart_key)
        except RedisError as exc:
            raise CartService._redis_error(exc)
        
        if cart_json:
            cart_data = json.loads(cart_json)
        else:
            cart_data = {
                "user_id": user_id,
                "items": [],
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }
            
        # Update with new cart data or keep existing data
        cart_data["updated_at"] = now.isoformat()
        
        # Save back to Redis
        try:
            redis_client.setex(cart_key, 604800, json.dumps(cart_data))
        except RedisError as exc:
            raise CartService._redis_error(exc)
        
        return CartResponse(
            id=user_id,
            user_id=user_id,
            created_at=datetime.fromisoformat(cart_data.get("created_at", now.isoformat())),
            updated_at=now
        )
    
    @staticmethod
    async def delete_cart(user_id: int):
        """Delete cart for a user"""
        cart_key = await CartService._get_cart_key(user_id)
        try:
            redis_client.delete(cart_key)
        except RedisError as exc:
            raise CartService._redis_error(exc)
