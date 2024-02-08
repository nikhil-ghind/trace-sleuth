from fastapi import APIRouter, HTTPException
from app.models.product import ProductCreate
from app.services.product_service import get_all_products, get_product_by_id, create_product

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/")
def list_products():
    return get_all_products()


@router.get("/{product_id}")
def get_product(product_id: str):
    product = get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return product


@router.post("/", status_code=201)
def add_product(data: ProductCreate):
    return create_product(data)
