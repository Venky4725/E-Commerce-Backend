"""
Orders tests
"""
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_order():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/v1/orders/", json={
            "user_id": 1,
            "status": "pending",
            "total_amount": 100.00,
            "shipping_address": "123 Test St",
            "billing_address": "123 Test St"
        })
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_get_orders():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/orders/")
        assert response.status_code == 200