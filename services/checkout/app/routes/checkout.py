from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.checkout_service import checkout

router = APIRouter(prefix="/checkout", tags=["checkout"])


class CartItem(BaseModel):
    product_id: str
    quantity: int = 1


class CheckoutRequest(BaseModel):
    items: list[CartItem]
    customer_id: str = "anonymous"


@router.post("/")
async def do_checkout(req: CheckoutRequest):
    try:
        items = [{"product_id": i.product_id, "quantity": i.quantity} for i in req.items]
        result = await checkout(items, req.customer_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
