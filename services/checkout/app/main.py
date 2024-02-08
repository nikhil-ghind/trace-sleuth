from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from app.config import SERVICE_NAME
from app.tracing import setup_tracing
from app.routes.checkout import router as checkout_router

app = FastAPI(title="Checkout Service", version="1.0.0")

setup_tracing(SERVICE_NAME, app)
Instrumentator().instrument(app).expose(app)

app.include_router(checkout_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}
