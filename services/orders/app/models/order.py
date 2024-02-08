from pydantic import BaseModel


class OrderItem(BaseModel):
    product_id: str
    quantity: int


class OrderCreate(BaseModel):
    items: list[OrderItem]
    customer_id: str = "anonymous"
