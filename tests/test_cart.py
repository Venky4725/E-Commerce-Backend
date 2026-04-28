"""
Cart tests
"""
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_cart():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/v1/cart/", json={
            "user_id": 1
        })
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_get_cart():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/cart/1")
        assert response.status_code == 200