from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from app.api.routes import auth, products, cart, orders, websocket
from app.core.config import settings
from app.core.database import engine, Base
from app.models import *
from app.services.cache_service import CacheService
import os
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# auto create tables on startup
# Disabled - tables should be created with Alembic migrations in production
# Enable only for specific development testing


app.include_router(auth.router,prefix=settings.API_V1_STR,tags=["auth"])
app.include_router(products.router,prefix=f"{settings.API_V1_STR}/products",tags=["products"])
app.include_router(cart.router,prefix=f"{settings.API_V1_STR}/cart",tags=["cart"])
app.include_router(orders.router,prefix=f"{settings.API_V1_STR}/orders",tags=["orders"])
app.include_router(websocket.router,prefix=settings.API_V1_STR,tags=["websocket"])

# Serve static files (for uploaded images)
upload_dir = Path(settings.UPLOAD_DIR)
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

@app.get("/")
async def root():
    return {
        "message":"Welcome to the E-Commerce Backend API"
    }


@app.get("/health/redis")
async def redis_health():
    """Health check for Redis connection"""
    try:
        if await CacheService._is_redis_available():
            return {"status": "healthy", "redis": "connected"}
        else:
            return {"status": "unhealthy", "redis": "disconnected"}
    except Exception as e:
        return {"status": "unhealthy", "redis": "error", "message": str(e)}

@app.get("/health/database")
async def database_health():
    """Health check for database connection"""
    try:
        # Test database connection
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "message": str(e)}


@app.get("/health/celery")
async def celery_health():
    """Health check for Celery"""
    try:
        from app.tasks.celery_worker import celery_app
        inspect = celery_app.control.inspect(timeout=1)
        pong = inspect.ping()
        if pong:
            return {"status": "healthy", "celery": "connected", "workers": pong}
        return {"status": "unhealthy", "celery": "no_workers"}
    except Exception as e:
        return {"status": "unhealthy", "celery": "disconnected", "message": str(e)}
