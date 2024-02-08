import os

SERVICE_NAME = "checkout-service"
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8003"))
JAEGER_ENDPOINT = os.getenv("JAEGER_ENDPOINT", "http://jaeger:4317")
CATALOG_SERVICE_URL = os.getenv("CATALOG_SERVICE_URL", "http://catalog:8001")
ORDERS_SERVICE_URL = os.getenv("ORDERS_SERVICE_URL", "http://orders:8002")
