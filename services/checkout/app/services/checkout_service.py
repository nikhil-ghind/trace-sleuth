import asyncio
import random

import httpx
from opentelemetry import trace
from opentelemetry.trace import StatusCode

from app.config import CATALOG_SERVICE_URL, ORDERS_SERVICE_URL

tracer = trace.get_tracer(__name__)


async def validate_cart(items: list[dict]) -> list[dict]:
    """Validate each cart item exists in catalog."""
    with tracer.start_as_current_span("validate_cart") as span:
        validated = []
        async with httpx.AsyncClient() as client:
            for item in items:
                pid = item["product_id"]
                resp = await client.get(f"{CATALOG_SERVICE_URL}/products/{pid}")
                if resp.status_code != 200:
                    span.set_status(StatusCode.ERROR, f"Product {pid} not found")
                    raise ValueError(f"Product {pid} not found in catalog")
                product = resp.json()
                validated.append({
                    "product_id": pid,
                    "name": product["name"],
                    "price": product["price"],
                    "quantity": item["quantity"],
                })
        span.set_attribute("cart.item_count", len(validated))
        return validated


async def place_order(items: list[dict], customer_id: str) -> dict:
    """Create order via the orders service."""
    with tracer.start_as_current_span("create_order") as span:
        payload = {
            "items": [{"product_id": i["product_id"], "quantity": i["quantity"]} for i in items],
            "customer_id": customer_id,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{ORDERS_SERVICE_URL}/orders/", json=payload)
            if resp.status_code not in (200, 201):
                span.set_status(StatusCode.ERROR, "Order creation failed")
                raise ValueError(f"Order creation failed: {resp.text}")
            order = resp.json()
            span.set_attribute("order.id", order["id"])
            return order


async def process_payment(order_id: str, amount: float) -> dict:
    """Simulate payment processing with 2s delay and 5% failure rate."""
    with tracer.start_as_current_span("process_payment") as span:
        span.set_attribute("payment.order_id", order_id)
        span.set_attribute("payment.amount", amount)

        # Simulate payment gateway latency
        await asyncio.sleep(2.0)

        # 5% failure rate
        if random.random() < 0.05:
            span.set_status(StatusCode.ERROR, "Payment declined")
            span.set_attribute("payment.status", "declined")
            raise ValueError("Payment declined by processor")

        span.set_attribute("payment.status", "approved")
        return {"status": "approved", "order_id": order_id, "amount": amount}


async def checkout(items: list[dict], customer_id: str = "anonymous") -> dict:
    """Full checkout flow: validate -> order -> pay."""
    with tracer.start_as_current_span("checkout_flow") as span:
        # Step 1: Validate cart
        validated_items = await validate_cart(items)

        # Step 2: Create order
        order = await place_order(validated_items, customer_id)

        # Step 3: Process payment
        payment = await process_payment(order["id"], order["total"])

        result = {
            "order": order,
            "payment": payment,
            "status": "completed",
        }
        span.set_attribute("checkout.status", "completed")
        span.set_attribute("checkout.order_id", order["id"])
        return result
