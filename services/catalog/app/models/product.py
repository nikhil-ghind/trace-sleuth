from pydantic import BaseModel
from typing import Optional


class Product(BaseModel):
    id: str
    name: str
    price: float
    stock: int


class ProductCreate(BaseModel):
    name: str
    price: float
    stock: int = 0
