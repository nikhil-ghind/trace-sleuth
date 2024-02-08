import uuid

# In-memory product store
PRODUCTS: list[dict] = [
    {
        "id": "prod-001",
        "name": "Mechanical Keyboard",
        "price": 129.99,
        "stock": 50,
    },
    {
        "id": "prod-002",
        "name": "Wireless Mouse",
        "price": 49.99,
        "stock": 120,
    },
    {
        "id": "prod-003",
        "name": "USB-C Hub",
        "price": 39.99,
        "stock": 200,
    },
    {
        "id": "prod-004",
        "name": "Monitor Stand",
        "price": 79.99,
        "stock": 30,
    },
]


def generate_id() -> str:
    return f"prod-{uuid.uuid4().hex[:6]}"
