from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor


def setup_tracing(service_name: str, app: FastAPI):
    resource = Resource.create({"service.name": service_name})
    tracer_provider = TracerProvider(resource=resource)
    jaeger_exporter = OTLPSpanExporter(
        endpoint="http://jaeger:4317", insecure=True
    )
    tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
    trace.set_tracer_provider(tracer_provider)
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
