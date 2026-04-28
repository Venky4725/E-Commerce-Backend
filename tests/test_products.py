"""
Products tests
"""
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_product():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/v1/products/", json={
            "name": "Test Product",
            "description": "A test product",
            "price": 10.99,
            "stock_quantity": 100
        })
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_get_products():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/products/")
        assert response.status_code == 200