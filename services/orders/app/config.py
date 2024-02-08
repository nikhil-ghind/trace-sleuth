import os

SERVICE_NAME = "orders-service"
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8002"))
JAEGER_ENDPOINT = os.getenv("JAEGER_ENDPOINT", "http://jaeger:4317")
CATALOG_SERVICE_URL = os.getenv("CATALOG_SERVICE_URL", "http://catalog:8001")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
