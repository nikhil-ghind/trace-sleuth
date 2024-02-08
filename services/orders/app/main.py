from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from app.config import SERVICE_NAME
from app.tracing import setup_tracing
from app.routes.orders import router as orders_router

app = FastAPI(title="Orders Service", version="1.0.0")

setup_tracing(SERVICE_NAME, app)
Instrumentator().instrument(app).expose(app)

app.include_router(orders_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}
