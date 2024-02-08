# Trace Sleuth

## Project Overview
Distributed e-commerce backend with checkout, catalog, and orders microservices instrumented end-to-end with OpenTelemetry and Jaeger for distributed tracing. An MCP-powered LLM layer correlates traces across service boundaries and generates root-cause summaries for debugging.

## Tech Stack
- **Services:** Python (FastAPI) for each microservice
- **Tracing:** OpenTelemetry SDK, Jaeger
- **Messaging:** Apache Kafka
- **Monitoring:** Prometheus, Grafana
- **LLM:** Anthropic Claude or OpenAI, MCP protocol
- **Database:** PostgreSQL (per-service)
- **Container:** Docker, Docker Compose

## Architecture Overview
```
┌──────────┐    ┌──────────┐    ┌──────────┐
│ Catalog  │    │ Orders   │    │ Checkout │
│ Service  │◄──►│ Service  │◄──►│ Service  │
└────┬─────┘    └────┬─────┘    └────┬─────┘
     │               │               │
     └───────────────┴───────────────┘
                     │ OTel traces
              ┌──────▼───────┐
              │   Jaeger     │
              │  Collector   │
              └──────┬───────┘
                     │
              ┌──────▼───────┐
              │  AI Debug    │
              │  Agent (MCP) │
              └──────────────┘
```

## Phase 1: Microservices Scaffold
**Goal:** Build three microservices with inter-service communication.

### Tasks
1. Project structure:
   ```
   ecommerceMicroservicesAiDebugging/
   ├── services/
   │   ├── catalog/
   │   │   ├── app/
   │   │   │   ├── main.py
   │   │   │   ├── routes.py      # GET /products, GET /products/{id}
   │   │   │   ├── models.py      # Product, Category
   │   │   │   └── database.py
   │   │   ├── Dockerfile
   │   │   └── requirements.txt
   │   ├── orders/
   │   │   ├── app/
   │   │   │   ├── main.py
   │   │   │   ├── routes.py      # POST /orders, GET /orders/{id}
   │   │   │   ├── models.py      # Order, OrderItem
   │   │   │   ├── services.py    # calls catalog service for validation
   │   │   │   └── database.py
   │   │   ├── Dockerfile
   │   │   └── requirements.txt
   │   ├── checkout/
   │   │   ├── app/
   │   │   │   ├── main.py
   │   │   │   ├── routes.py      # POST /checkout
   │   │   │   ├── services.py    # orchestrates: validate cart → create order → process payment
   │   │   │   └── database.py
   │   │   ├── Dockerfile
   │   │   └── requirements.txt
   ├── ai_debugger/
   │   ├── agent.py               # MCP-based debug agent
   │   ├── tools.py               # MCP tool definitions
   │   └── requirements.txt
   ├── docker-compose.yml
   └── monitoring/
       ├── prometheus.yml
       └── grafana/dashboards/
   ```
2. Catalog service: CRUD for products, PostgreSQL storage. `GET /products/{id}` returns product with price and stock.
3. Orders service: creates orders, validates product exists by calling catalog service via HTTP. Publishes `order.created` event to Kafka.
4. Checkout service: orchestrates checkout flow — validates cart items (catalog), creates order (orders service), simulates payment processing. Publishes `checkout.completed` to Kafka.
5. Inter-service communication via `httpx.AsyncClient` with service discovery (Docker DNS).
6. Docker Compose with all services + PostgreSQL instances + Kafka.

## Phase 2: OpenTelemetry Instrumentation
**Goal:** Add distributed tracing across all services with context propagation.

### Tasks
1. Add to each service's `requirements.txt`:
   - `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-jaeger`
   - `opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-httpx`
   - `opentelemetry-instrumentation-sqlalchemy`, `opentelemetry-instrumentation-kafka-python`
2. Create shared `tracing.py` module (copy to each service):
   ```python
   def setup_tracing(service_name: str):
       resource = Resource.create({"service.name": service_name})
       tracer_provider = TracerProvider(resource=resource)
       jaeger_exporter = JaegerExporter(agent_host_name="jaeger", agent_port=6831)
       tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
       trace.set_tracer_provider(tracer_provider)
       FastAPIInstrumentor.instrument_app(app)
       HTTPXClientInstrumentor().instrument()
       SQLAlchemyInstrumentor().instrument()
   ```
3. Add custom spans for business logic:
   - Checkout: span for cart validation, span for payment processing
   - Orders: span for stock check, span for order persistence
4. Add span attributes: `order.id`, `product.id`, `payment.status`, `user.id`
5. Add Kafka trace context propagation using `opentelemetry-instrumentation-kafka-python`.
6. Docker Compose: add Jaeger all-in-one service, expose UI on port 16686.
7. Verify: make a checkout request → see full trace spanning all 3 services in Jaeger UI.

## Phase 3: Prometheus Metrics & Grafana
**Goal:** Add application metrics and monitoring dashboards.

### Tasks
1. Add `prometheus-fastapi-instrumentator` to each service.
2. Custom metrics per service:
   - Catalog: `product_lookups_total`, `cache_hit_ratio`
   - Orders: `orders_created_total`, `order_value_histogram`
   - Checkout: `checkouts_total` (by status: success/failed), `checkout_duration_seconds`
3. `monitoring/prometheus.yml`:
   ```yaml
   scrape_configs:
     - job_name: catalog
       static_configs: [{targets: ['catalog:8001']}]
     - job_name: orders
       static_configs: [{targets: ['orders:8002']}]
     - job_name: checkout
       static_configs: [{targets: ['checkout:8003']}]
   ```
4. Grafana dashboards:
   - Service health: RPS, error rate, latency per service
   - Business metrics: orders/minute, checkout conversion rate, avg order value
   - Infrastructure: Kafka consumer lag, DB connection pool usage

## Phase 4: AI Debug Agent (MCP)
**Goal:** Build an MCP-powered LLM agent that analyzes traces and generates root-cause summaries.

### Tasks
1. `ai_debugger/tools.py` — MCP tool definitions:
   - `query_traces(service_name, operation, min_duration_ms, limit)` — queries Jaeger API for slow/errored traces
   - `get_trace_detail(trace_id)` — fetches full trace with all spans and attributes
   - `get_service_metrics(service_name, metric_name, time_range)` — queries Prometheus
   - `get_service_logs(service_name, time_range, level)` — queries log aggregator
   - `get_error_spans(time_range)` — finds spans with error=true
   - `compare_traces(trace_id_good, trace_id_bad)` — diff two traces
2. `ai_debugger/agent.py`:
   - `class DebugAgent`:
     - Registers MCP tools
     - System prompt: "You are a distributed systems debugging assistant. Use the provided tools to analyze traces, metrics, and logs to identify root causes of errors and performance issues."
     - `async investigate(issue_description: str) -> DebugReport`:
       - Agent autonomously: queries recent error traces → examines span details → checks metrics for anomalies → correlates across services → generates report
     - `@dataclass class DebugReport`: `root_cause: str`, `affected_services: list[str]`, `timeline: list[Event]`, `recommendation: str`, `evidence: list[str]`
3. `ai_debugger/server.py`:
   - FastAPI app: `POST /debug/investigate` — accepts issue description, returns DebugReport
   - `GET /debug/health-check` — agent runs proactive analysis, returns any detected anomalies
4. Tests:
   - Inject a fault (add 2s delay to catalog service) → trigger checkout → agent identifies catalog as bottleneck
   - Inject an error (orders service returns 500) → agent traces error propagation through checkout
5. Docker Compose: add `ai-debugger` service connected to Jaeger and Prometheus.
