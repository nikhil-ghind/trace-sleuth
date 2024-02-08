import os


SERVICE_NAME = "catalog-service"
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8001"))
JAEGER_ENDPOINT = os.getenv("JAEGER_ENDPOINT", "http://jaeger:4317")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
