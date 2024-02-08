from fastapi import APIRouter, HTTPException
from app.models.order import OrderCreate
from app.services.order_service import create_order, get_order_by_id, get_all_orders

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/")
def list_orders():
    return get_all_orders()


@router.get("/{order_id}")
def get_order(order_id: str):
    order = get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return order


@router.post("/", status_code=201)
async def place_order(data: OrderCreate):
    try:
        return await create_order(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
