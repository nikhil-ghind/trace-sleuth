"""MCP tool definitions for querying Jaeger and Prometheus."""

import time
from typing import Any

import httpx

from ai_debugger.config import JAEGER_API_URL, PROMETHEUS_API_URL


# --- Tool definitions for function-calling schema ---

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "query_traces",
            "description": "Query recent traces from Jaeger for a given service and optional operation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {"type": "string", "description": "Service to query traces for"},
                    "operation": {"type": "string", "description": "Operation name filter (optional)"},
                    "min_duration_ms": {"type": "integer", "description": "Minimum span duration in ms (optional)"},
                    "limit": {"type": "integer", "description": "Max traces to return", "default": 20},
                },
                "required": ["service_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_trace_detail",
            "description": "Get full trace detail including all spans for a given trace ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trace_id": {"type": "string", "description": "The trace ID to look up"},
                },
                "required": ["trace_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_error_spans",
            "description": "Find spans with errors in the given time range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "time_range_minutes": {"type": "integer", "description": "How far back to look", "default": 30},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_service_metrics",
            "description": "Query Prometheus for request rate, error rate, and latency for a service.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {"type": "string", "description": "Service to get metrics for"},
                },
                "required": ["service_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_traces",
            "description": "Compare two traces to find differences in span count and durations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trace_id_good": {"type": "string", "description": "Trace ID of a known good request"},
                    "trace_id_bad": {"type": "string", "description": "Trace ID of a problematic request"},
                },
                "required": ["trace_id_good", "trace_id_bad"],
            },
        },
    },
]


# --- Tool implementations ---

async def query_traces(
    service_name: str,
    operation: str | None = None,
    min_duration_ms: int | None = None,
    limit: int = 20,
) -> dict:
    params: dict[str, Any] = {
        "service": service_name,
        "limit": limit,
        "lookback": "1h",
    }
    if operation:
        params["operation"] = operation
    if min_duration_ms:
        params["minDuration"] = f"{min_duration_ms}ms"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{JAEGER_API_URL}/api/traces", params=params)
        if resp.status_code != 200:
            return {"error": f"Jaeger returned {resp.status_code}", "body": resp.text}
        data = resp.json()

    traces = []
    for t in data.get("data", []):
        spans = t.get("spans", [])
        trace_id = t.get("traceID", "")
        duration_us = max((s.get("duration", 0) for s in spans), default=0)
        has_error = any(
            any(tag.get("key") == "error" and tag.get("value") is True for tag in s.get("tags", []))
            for s in spans
        )
        traces.append({
            "trace_id": trace_id,
            "span_count": len(spans),
            "duration_ms": round(duration_us / 1000, 2),
            "has_error": has_error,
        })
    return {"traces": traces, "total": len(traces)}


async def get_trace_detail(trace_id: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{JAEGER_API_URL}/api/traces/{trace_id}")
        if resp.status_code != 200:
            return {"error": f"Jaeger returned {resp.status_code}"}
        data = resp.json()

    result_spans = []
    for t in data.get("data", []):
        for s in t.get("spans", []):
            tags = {tag["key"]: tag["value"] for tag in s.get("tags", [])}
            result_spans.append({
                "span_id": s.get("spanID", ""),
                "operation": s.get("operationName", ""),
                "service": s.get("process", {}).get("serviceName", ""),
                "duration_ms": round(s.get("duration", 0) / 1000, 2),
                "tags": tags,
                "has_error": tags.get("error", False) is True or tags.get("otel.status_code") == "ERROR",
            })
    return {"trace_id": trace_id, "spans": result_spans}


async def get_error_spans(time_range_minutes: int = 30) -> dict:
    services = ["catalog-service", "orders-service", "checkout-service"]
    all_errors = []

    for svc in services:
        result = await query_traces(svc, limit=50)
        for t in result.get("traces", []):
            if t.get("has_error"):
                detail = await get_trace_detail(t["trace_id"])
                error_spans = [s for s in detail.get("spans", []) if s.get("has_error")]
                all_errors.extend(error_spans)

    return {"error_spans": all_errors, "total": len(all_errors)}


async def get_service_metrics(service_name: str) -> dict:
    metrics: dict[str, Any] = {}
    queries = {
        "request_rate": f'rate(http_requests_total{{service="{service_name}"}}[5m])',
        "error_rate": f'rate(http_requests_total{{service="{service_name}",status=~"5.."}}[5m])',
        "latency_p95": f'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{{service="{service_name}"}}[5m]))',
    }

    async with httpx.AsyncClient(timeout=10) as client:
        for key, query in queries.items():
            try:
                resp = await client.get(
                    f"{PROMETHEUS_API_URL}/api/v1/query",
                    params={"query": query},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("data", {}).get("result", [])
                    if results:
                        metrics[key] = float(results[0].get("value", [0, 0])[1])
                    else:
                        metrics[key] = 0.0
                else:
                    metrics[key] = None
            except Exception as e:
                metrics[key] = f"error: {e}"

    return {"service": service_name, "metrics": metrics}


async def compare_traces(trace_id_good: str, trace_id_bad: str) -> dict:
    good = await get_trace_detail(trace_id_good)
    bad = await get_trace_detail(trace_id_bad)

    good_spans = good.get("spans", [])
    bad_spans = bad.get("spans", [])

    good_ops = {s["operation"]: s["duration_ms"] for s in good_spans}
    bad_ops = {s["operation"]: s["duration_ms"] for s in bad_spans}

    deltas = {}
    for op in set(list(good_ops.keys()) + list(bad_ops.keys())):
        g = good_ops.get(op, 0)
        b = bad_ops.get(op, 0)
        deltas[op] = {"good_ms": g, "bad_ms": b, "delta_ms": round(b - g, 2)}

    return {
        "good_trace": {"trace_id": trace_id_good, "span_count": len(good_spans)},
        "bad_trace": {"trace_id": trace_id_bad, "span_count": len(bad_spans)},
        "duration_deltas": deltas,
        "extra_spans_in_bad": len(bad_spans) - len(good_spans),
    }


# Dispatcher for the agent
TOOL_DISPATCH = {
    "query_traces": query_traces,
    "get_trace_detail": get_trace_detail,
    "get_error_spans": get_error_spans,
    "get_service_metrics": get_service_metrics,
    "compare_traces": compare_traces,
}
