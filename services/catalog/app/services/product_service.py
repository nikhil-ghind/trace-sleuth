from opentelemetry import trace
from app.database import PRODUCTS, generate_id
from app.models.product import ProductCreate

tracer = trace.get_tracer(__name__)


def get_all_products() -> list[dict]:
    with tracer.start_as_current_span("product_service.get_all") as span:
        span.set_attribute("product.count", len(PRODUCTS))
        return PRODUCTS


def get_product_by_id(product_id: str) -> dict | None:
    with tracer.start_as_current_span("product_service.lookup") as span:
        span.set_attribute("product.id", product_id)
        for product in PRODUCTS:
            if product["id"] == product_id:
                span.set_attribute("product.found", True)
                return product
        span.set_attribute("product.found", False)
        return None


def create_product(data: ProductCreate) -> dict:
    with tracer.start_as_current_span("product_service.create") as span:
        product = {
            "id": generate_id(),
            "name": data.name,
            "price": data.price,
            "stock": data.stock,
        }
        PRODUCTS.append(product)
        span.set_attribute("product.id", product["id"])
        span.set_attribute("product.name", product["name"])
        return product
