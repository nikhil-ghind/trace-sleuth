import os

SERVICE_NAME = "ai-debugger"
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8005"))
JAEGER_API_URL = os.getenv("JAEGER_API_URL", "http://jaeger:16686")
PROMETHEUS_API_URL = os.getenv("PROMETHEUS_API_URL", "http://prometheus:9090")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
