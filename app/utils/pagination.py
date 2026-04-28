"""
Pagination utilities
"""
from typing import List, TypeVar, Generic
from pydantic import BaseModel

T = TypeVar('T')

class Pagination(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    pages: int

def paginate(items: List[T], page: int, size: int) -> Pagination[T]:
    """Paginate a list of items"""
    total = len(items)
    start = (page - 1) * size
    end = start + size
    paginated_items = items[start:end]
    
    return Pagination(
        items=paginated_items,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size  # Ceiling division
    )