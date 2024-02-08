"""MCP-based debug agent that correlates traces and generates root-cause summaries."""

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Any

from ai_debugger.config import OPENAI_API_KEY
from ai_debugger.tools import TOOL_DEFINITIONS, TOOL_DISPATCH

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a distributed systems debugging assistant. You have access to
Jaeger traces and Prometheus metrics for a microservices e-commerce platform with three
services: catalog-service, orders-service, and checkout-service.

When investigating an issue:
1. Query recent error traces across services.
2. Examine detailed span information for problematic traces.
3. Check service metrics for anomalies (high error rates, latency spikes).
4. Correlate findings across services to identify root cause.
5. Produce a clear root-cause analysis with recommendations.

Be specific: cite trace IDs, span names, durations, and error messages."""


@dataclass
class DebugReport:
    root_cause: str
    affected_services: list[str]
    timeline: list[str]
    recommendation: str
    evidence: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class DebugAgent:
    def __init__(self):
        self._has_llm = bool(OPENAI_API_KEY)

    async def investigate(self, issue_description: str) -> DebugReport:
        """Investigate an issue using tools, with LLM or heuristic fallback."""
        if self._has_llm:
            return await self._investigate_with_llm(issue_description)
        return await self._investigate_heuristic(issue_description)

    async def _investigate_with_llm(self, issue_description: str) -> DebugReport:
        """Use OpenAI function-calling to drive investigation."""
        try:
            import openai
        except ImportError:
            logger.warning("openai package not installed, falling back to heuristic")
            return await self._investigate_heuristic(issue_description)

        client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Investigate this issue: {issue_description}"},
        ]

        # Iterative tool-calling loop (max 10 rounds)
        for _ in range(10):
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
            )
            msg = response.choices[0].message
            messages.append(msg)

            if not msg.tool_calls:
                # LLM is done, parse the final answer
                return self._parse_llm_report(msg.content or "", issue_description)

            for tc in msg.tool_calls:
                fn_name = tc.function.name
                fn_args = json.loads(tc.function.arguments)
                handler = TOOL_DISPATCH.get(fn_name)
                if handler:
                    result = await handler(**fn_args)
                else:
                    result = {"error": f"Unknown tool: {fn_name}"}
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, default=str),
                })

        return DebugReport(
            root_cause="Investigation exceeded maximum iterations",
            affected_services=[],
            timeline=[],
            recommendation="Manual investigation recommended",
        )

    def _parse_llm_report(self, content: str, issue: str) -> DebugReport:
        """Parse LLM text into a DebugReport."""
        return DebugReport(
            root_cause=content,
            affected_services=self._extract_services(content),
            timeline=[f"Investigated: {issue}"],
            recommendation=content.split("Recommendation:")[-1].strip() if "Recommendation:" in content else "See root cause analysis above.",
        )

    @staticmethod
    def _extract_services(text: str) -> list[str]:
        services = []
        for svc in ["catalog-service", "orders-service", "checkout-service"]:
            if svc in text:
                services.append(svc)
        return services or ["unknown"]

    async def _investigate_heuristic(self, issue_description: str) -> DebugReport:
        """Heuristic-based investigation without LLM."""
        evidence: list[dict] = []
        affected_services: list[str] = []
        timeline: list[str] = []

        # Step 1: Check errors across all services
        timeline.append("Querying error spans across all services")
        errors = await TOOL_DISPATCH["get_error_spans"](time_range_minutes=30)
        error_spans = errors.get("error_spans", [])
        evidence.append({"step": "error_scan", "error_count": len(error_spans)})

        if error_spans:
            # Group by service
            error_by_svc: dict[str, list] = {}
            for s in error_spans:
                svc = s.get("service", "unknown")
                error_by_svc.setdefault(svc, []).append(s)
                if svc not in affected_services:
                    affected_services.append(svc)

            for svc, spans in error_by_svc.items():
                timeline.append(f"Found {len(spans)} error spans in {svc}")
                evidence.append({
                    "service": svc,
                    "error_spans": spans[:5],  # cap detail
                })

        # Step 2: Check for slow traces
        timeline.append("Checking for slow traces in checkout-service")
        slow = await TOOL_DISPATCH["query_traces"](
            service_name="checkout-service", min_duration_ms=3000, limit=5
        )
        slow_traces = slow.get("traces", [])
        if slow_traces:
            timeline.append(f"Found {len(slow_traces)} slow traces (>3s)")
            evidence.append({"step": "slow_trace_scan", "slow_traces": slow_traces})

        # Step 3: Check metrics
        timeline.append("Querying service metrics")
        for svc in ["catalog-service", "orders-service", "checkout-service"]:
            metrics = await TOOL_DISPATCH["get_service_metrics"](service_name=svc)
            m = metrics.get("metrics", {})
            error_rate = m.get("error_rate", 0)
            if isinstance(error_rate, (int, float)) and error_rate > 0.01:
                timeline.append(f"High error rate in {svc}: {error_rate:.4f}")
                if svc not in affected_services:
                    affected_services.append(svc)

        # Synthesize root cause
        if error_spans:
            top_error = error_spans[0]
            root_cause = (
                f"Detected {len(error_spans)} error(s) across services. "
                f"Primary error in {top_error.get('service', 'unknown')} "
                f"operation '{top_error.get('operation', 'unknown')}' "
                f"with tags: {top_error.get('tags', {})}."
            )
        elif slow_traces:
            root_cause = (
                f"No errors found, but {len(slow_traces)} slow traces detected "
                f"(>{3000}ms). Likely latency issue in downstream services."
            )
        else:
            root_cause = "No errors or anomalies detected in the observed time window."

        recommendation = (
            "Review the affected services' logs and traces in Jaeger. "
            "If payment failures are occurring, check the checkout-service process_payment span. "
            "For latency issues, examine inter-service call durations."
        )

        return DebugReport(
            root_cause=root_cause,
            affected_services=affected_services or ["none detected"],
            timeline=timeline,
            recommendation=recommendation,
            evidence=evidence,
        )

    async def health_check(self) -> dict:
        """Proactive anomaly scan."""
        anomalies = []

        for svc in ["catalog-service", "orders-service", "checkout-service"]:
            metrics = await TOOL_DISPATCH["get_service_metrics"](service_name=svc)
            m = metrics.get("metrics", {})
            error_rate = m.get("error_rate", 0)
            latency_p95 = m.get("latency_p95", 0)
            if isinstance(error_rate, (int, float)) and error_rate > 0.01:
                anomalies.append({"service": svc, "issue": "high_error_rate", "value": error_rate})
            if isinstance(latency_p95, (int, float)) and latency_p95 > 2.0:
                anomalies.append({"service": svc, "issue": "high_latency_p95", "value": latency_p95})

        errors = await TOOL_DISPATCH["get_error_spans"](time_range_minutes=10)
        error_count = errors.get("total", 0)
        if error_count > 0:
            anomalies.append({"issue": "recent_errors", "count": error_count})

        return {
            "status": "unhealthy" if anomalies else "healthy",
            "anomalies": anomalies,
        }
