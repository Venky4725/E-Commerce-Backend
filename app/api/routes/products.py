"""
Products routes

GET  /products/           — list with search, sort, pagination (public)
GET  /products/{id}       — single product (public)
POST /products/           — create (admin)
PUT  /products/{id}       — full update (admin)
PATCH /products/{id}      — partial update (admin)
DELETE /products/{id}     — delete (admin)
POST /products/{id}/upload-image — image upload (admin)
"""
import logging
import math
import traceback
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, get_current_admin_user
from app.core.config import settings
from app.crud.product_crud import (
    create_product, get_product, get_products,
    update_product, delete_product,
)
from app.models.user import User
from app.schemas.product_schema import (
    ProductCreate, ProductUpdate, ProductResponse, PaginatedProductResponse,
)
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Public ─────────────────────────────────────────────────────────────────────

@router.get("/", response_model=PaginatedProductResponse)
async def list_products(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: str = Query(None, description="Search by name or description"),
    sort_by: str = Query("created_at", description="Field to sort by: price, name, created_at"),
    sort_order: str = Query("desc", description="asc or desc"),
    db: AsyncSession = Depends(get_db),
):
    """List products with search, sorting, and pagination."""
    try:
        # Validate sort_by
        allowed_sort = {"price", "name", "created_at", "stock_quantity"}
        if sort_by not in allowed_sort:
            raise HTTPException(status_code=400, detail=f"sort_by must be one of {allowed_sort}")

        skip = (page - 1) * size

        # Try cache only for default listing (no search/sort params)
        cache_key = f"products:{page}:{size}:{search}:{sort_by}:{sort_order}"
        if not search:
            try:
                cached = await CacheService.get(cache_key)
                if cached:
                    logger.debug("Products cache HIT: %s", cache_key)
                    return cached
            except Exception as exc:
                logger.warning("Cache GET failed (ignored): %s", exc)

        products, total = await get_products(
            db, skip=skip, limit=size, search=search,
            sort_by=sort_by, sort_order=sort_order,
        )

        response = PaginatedProductResponse(
            items=[ProductResponse.model_validate(p) for p in products],
            total=total,
            page=page,
            size=size,
            pages=math.ceil(total / size) if total else 0,
        )

        # Cache result
        if not search:
            try:
                await CacheService.set(cache_key, response.model_dump(mode="json"), expire=120)
            except Exception as exc:
                logger.warning("Cache SET failed (ignored): %s", exc)

        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error listing products: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch products: {str(e)}"
        )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_single_product(product_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single product by ID."""
    try:
        product = await get_product(db, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching product {product_id}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch product: {str(e)}"
        )


# ── Admin ──────────────────────────────────────────────────────────────────────

@router.post("/", response_model=ProductResponse, status_code=201)
async def create_new_product(
    product: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Create a new product. Requires admin access."""
    logger.info(f"🔧 Admin {current_admin.username} creating product: {product.name}")
    db_product = await create_product(db, product)
    return db_product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_existing_product(
    product_id: int,
    product: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Full product update. Requires admin access."""
    logger.info(f"🔧 Admin {current_admin.username} updating product: {product_id}")
    db_product = await update_product(db, product_id, product.model_dump())
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product


@router.patch("/{product_id}", response_model=ProductResponse)
async def partial_update_product(
    product_id: int,
    product: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Partial product update — only provided fields are changed. Requires admin access."""
    logger.info(f"🔧 Admin {current_admin.username} partially updating product: {product_id}")
    update_data = product.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided to update")
    db_product = await update_product(db, product_id, update_data)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product


@router.delete("/{product_id}", status_code=200)
async def delete_existing_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Delete a product. Requires admin access."""
    logger.info(f"🔧 Admin {current_admin.username} deleting product: {product_id}")
    db_product = await delete_product(db, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}


@router.post("/{product_id}/upload-image", response_model=ProductResponse)
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Upload or replace a product image. Requires admin access."""
    logger.info(f"🔧 Admin {current_admin.username} uploading image for product: {product_id}")
    db_product = await get_product(db, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    # Size check
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {settings.MAX_FILE_SIZE // (1024*1024)} MB",
        )

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename).suffix if file.filename else ".jpg"
    filename = f"{product_id}_{uuid4().hex}{ext}"
    file_path = upload_dir / filename

    with open(file_path, "wb") as f:
        f.write(content)

    db_product = await update_product(db, product_id, {"image_url": f"/uploads/{filename}"})
    return db_product
