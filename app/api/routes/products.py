"""
Products routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.schemas.product_schema import ProductCreate, ProductResponse
from app.crud.product_crud import create_product, get_products, get_product, update_product, delete_product, get_products_by_name
from app.services.cache_service import CacheService
from app.core.config import settings
import json
import logging
import os
from uuid import uuid4
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=ProductResponse)
async def create_new_product(product: ProductCreate, db: AsyncSession = Depends(get_db)):
    db_product = await create_product(db, product)
    return db_product

@router.get("/", response_model=list[ProductResponse])
async def read_products(
    skip: int = 0, 
    limit: int = 100, 
    search: str = Query(None, description="Search products by name"),
    db: AsyncSession = Depends(get_db)
):
    # If search term is provided, filter products by name
    if search:
        products = await get_products_by_name(db, search)
    else:
        # Try to get from cache first
        cache_key = f"products_list:{skip}:{limit}"
        
        try:
            # Simple check if caching works, log hit/miss
            cached_products = await CacheService.get(cache_key)
            
            if cached_products is not None:
                logger.info(f"Cache hit for products list: {cache_key}")
                return cached_products
            else:
                logger.info(f"Cache miss for products list: {cache_key}")
                products = await get_products(db, skip=skip, limit=limit)
                
                # Serialize products to dict before caching (fixing serialization error)
                serialized_products = []
                for product in products:
                    # Convert sqlalchemy object to dict using model_dump or similar approach
                    if hasattr(product, 'model_dump'):
                        serialized_products.append(product.model_dump())
                    else:
                        # Fallback approach for objects that don't have model_dump
                        serialized_products.append({
                            "id": product.id,
                            "name": product.name,
                            "price": product.price,
                            "description": product.description,
                            "image_url": product.image_url
                        })
                
                # Cache the products for 300 seconds (5 minutes)
                await CacheService.set(cache_key, serialized_products, expire=300)
                return products
                
        except Exception as e:
            logger.error(f"Cache error: {e}")
            # Fall back to database-only approach
            products = await get_products(db, skip=skip, limit=limit)
    
    return products

@router.get("/{product_id}", response_model=ProductResponse)
async def read_product(product_id: int, db: AsyncSession = Depends(get_db)):
    db_product = await get_product(db, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

@router.put("/{product_id}", response_model=ProductResponse)
async def update_existing_product(
    product_id: int, 
    product: ProductCreate, 
    db: AsyncSession = Depends(get_db)
):
    """Update an existing product by ID"""
    db_product = await update_product(db, product_id, product.model_dump())
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

@router.delete("/{product_id}")
async def delete_existing_product(
    product_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """Delete a product by ID"""
    db_product = await delete_product(db, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}

@router.post("/{product_id}/upload-image", response_model=ProductResponse)
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload image for a product"""
    # Check if product exists
    db_product = await get_product(db, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Validate file type (only accept images)
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    
    # Define upload directory
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_extension = Path(file.filename).suffix
    filename = f"{product_id}_{uuid4().hex}{file_extension}"
    file_path = upload_dir / filename
    
    # Save file
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Update product with image URL
    image_url = f"/uploads/{filename}"
    db_product = await update_product(db, product_id, {"image_url": image_url})
    
    return db_product
