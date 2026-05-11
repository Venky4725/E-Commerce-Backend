"""
FastAPI E-Commerce Backend
"""
import logging
import traceback
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text

from app.api.routes import auth, products, cart, orders, websocket, notifications, admin, users
from app.core.config import settings
from app.core.database import engine, AsyncSessionLocal
from app.core.redis_client import is_redis_available
from app.core.admin_init import create_default_admin
from app.models import *  # noqa: F401,F403

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ── Lifespan Events ────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events - runs on startup and shutdown.
    Creates default admin user on startup.
    """
    # Startup
    logger.info("🚀 Starting E-Commerce Backend...")
    
    # Test database connection
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection successful")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        logger.error(traceback.format_exc())
    
    # Validate database schema
    try:
        async with engine.connect() as conn:
            # Check order_items table has required columns
            result = await conn.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='order_items' AND column_name IN ('product_name', 'product_image_url')
            """))
            columns = [row[0] for row in result]
            
            if 'product_name' not in columns or 'product_image_url' not in columns:
                logger.error("❌ Database schema mismatch detected!")
                logger.error("   Missing columns in order_items table")
                logger.error("   Run: python -m alembic upgrade head")
            else:
                logger.info("✅ Database schema validation passed")
    except Exception as e:
        logger.warning(f"⚠️  Schema validation failed: {e}")
    
    # Test Redis connection
    try:
        redis_status = await is_redis_available()
        if redis_status:
            logger.info("✅ Redis connection successful")
        else:
            logger.warning("⚠️  Redis unavailable - running without cache")
    except Exception as e:
        logger.warning(f"⚠️  Redis check failed: {e}")
    
    # Create default admin user
    async with AsyncSessionLocal() as db:
        try:
            await create_default_admin(db)
        except Exception as e:
            logger.error(f"❌ Failed to create admin user: {e}")
            logger.error(traceback.format_exc())
    
    logger.info("✅ Backend startup complete!")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down E-Commerce Backend...")


# ── FastAPI App ────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ── Global Exception Handlers ──────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return proper JSON response."""
    logger.error(f"❌ Unhandled exception on {request.method} {request.url.path}")
    logger.error(f"   Error: {str(exc)}")
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.DEBUG else "An unexpected error occurred",
            "path": str(request.url.path),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed messages."""
    logger.warning(f"⚠️  Validation error on {request.method} {request.url.path}")
    logger.warning(f"   Errors: {exc.errors()}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
            "path": str(request.url.path),
        },
    )


# ── CORS Middleware (MUST be added BEFORE routes) ─────────────────────────────

logger.info("🔧 Configuring CORS middleware...")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods: GET, POST, PUT, DELETE, OPTIONS, etc.
    allow_headers=["*"],  # Allow all headers
    expose_headers=["Content-Length", "Content-Type"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

logger.info("✅ CORS middleware configured")

# ── Routes ─────────────────────────────────────────────────────────────────────

logger.info("🔧 Registering routes...")

app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(products.router, prefix=f"{settings.API_V1_STR}/products", tags=["products"])
app.include_router(cart.router, prefix=f"{settings.API_V1_STR}/cart", tags=["cart"])
app.include_router(orders.router, prefix=f"{settings.API_V1_STR}/orders", tags=["orders"])
app.include_router(notifications.router, prefix=f"{settings.API_V1_STR}/notifications", tags=["notifications"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["admin"])
app.include_router(websocket.router, prefix=settings.API_V1_STR, tags=["websocket"])

logger.info("✅ Routes registered")

# ── Static Files ───────────────────────────────────────────────────────────────

upload_dir = Path(settings.UPLOAD_DIR)
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

# ── Root & Health Checks ───────────────────────────────────────────────────────


@app.get("/")
async def root():
    """Root endpoint — API welcome message."""
    return {
        "message": "Welcome to the E-Commerce Backend API",
        "docs": "/docs",
        "health": {
            "redis": "/health/redis",
            "database": "/health/database",
            "celery": "/health/celery",
        },
    }


@app.get("/health/redis")
async def redis_health():
    """Health check for Redis connection."""
    try:
        if await is_redis_available():
            return {"status": "healthy", "redis": "connected"}
        else:
            return {"status": "unhealthy", "redis": "disconnected"}
    except Exception as e:
        return {"status": "unhealthy", "redis": "error", "message": str(e)}


@app.get("/health/database")
async def database_health():
    """Health check for database connection."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "message": str(e)}


@app.get("/health/celery")
async def celery_health():
    """Health check for Celery."""
    try:
        from app.tasks.celery_worker import celery_app

        inspect = celery_app.control.inspect(timeout=1)
        pong = inspect.ping()
        if pong:
            return {"status": "healthy", "celery": "connected", "workers": pong}
        return {"status": "unhealthy", "celery": "no_workers"}
    except Exception as e:
        return {"status": "unhealthy", "celery": "disconnected", "message": str(e)}
