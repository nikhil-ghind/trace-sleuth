from pydantic import BaseModel


class OrderResponse(BaseModel):
    id: str
    customer_id: str
    items: list[dict]
    total: float
    status: str


class ErrorResponse(BaseModel):
    detail: str
