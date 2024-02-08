import asyncio
import json
import logging

import httpx
from opentelemetry import trace

from app.config import CATALOG_SERVICE_URL, KAFKA_BOOTSTRAP_SERVERS
from app.database import ORDERS, generate_order_id
from app.models.order import OrderCreate

tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)

_kafka_producer = None


async def _get_kafka_producer():
    global _kafka_producer
    if _kafka_producer is None:
        try:
            from aiokafka import AIOKafkaProducer
            _kafka_producer = AIOKafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            await _kafka_producer.start()
        except Exception as e:
            logger.warning(f"Kafka unavailable, skipping event publish: {e}")
            return None
    return _kafka_producer


async def validate_products(items: list[dict]) -> list[dict]:
    with tracer.start_as_current_span("validate_products") as span:
        validated = []
        async with httpx.AsyncClient() as client:
            for item in items:
                pid = item["product_id"]
                span.set_attribute("product.id", pid)
                resp = await client.get(f"{CATALOG_SERVICE_URL}/products/{pid}")
                if resp.status_code != 200:
                    raise ValueError(f"Product {pid} not found")
                product = resp.json()
                validated.append({
                    "product_id": pid,
                    "name": product["name"],
                    "price": product["price"],
                    "quantity": item["quantity"],
                })
        span.set_attribute("validated.count", len(validated))
        return validated


async def create_order(data: OrderCreate) -> dict:
    with tracer.start_as_current_span("create_order") as span:
        items_dicts = [{"product_id": i.product_id, "quantity": i.quantity} for i in data.items]
        validated_items = await validate_products(items_dicts)

        total = sum(i["price"] * i["quantity"] for i in validated_items)
        order = {
            "id": generate_order_id(),
            "customer_id": data.customer_id,
            "items": validated_items,
            "total": round(total, 2),
            "status": "created",
        }
        ORDERS.append(order)

        span.set_attribute("order.id", order["id"])
        span.set_attribute("order.total", order["total"])
        span.set_attribute("order.item_count", len(validated_items))

        # Publish to Kafka
        producer = await _get_kafka_producer()
        if producer:
            try:
                await producer.send_and_wait("order.created", order)
            except Exception as e:
                logger.warning(f"Failed to publish order event: {e}")

        return order


def get_order_by_id(order_id: str) -> dict | None:
    with tracer.start_as_current_span("get_order") as span:
        span.set_attribute("order.id", order_id)
        for order in ORDERS:
            if order["id"] == order_id:
                return order
        return None


def get_all_orders() -> list[dict]:
    return ORDERS
