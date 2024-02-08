import uuid

# In-memory order store
ORDERS: list[dict] = []


def generate_order_id() -> str:
    return f"order-{uuid.uuid4().hex[:8]}"
