from pydantic import BaseModel


class ProductResponse(BaseModel):
    id: str
    name: str
    price: float
    stock: int


class ErrorResponse(BaseModel):
    detail: str
