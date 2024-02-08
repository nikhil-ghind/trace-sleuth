"""FastAPI server exposing the AI debug agent."""

from fastapi import FastAPI
from pydantic import BaseModel
from ai_debugger.agent import DebugAgent
from ai_debugger.tools import TOOL_DISPATCH

app = FastAPI(title="AI Debugger", version="1.0.0")
agent = DebugAgent()


class InvestigateRequest(BaseModel):
    issue: str


@app.post("/debug/investigate")
async def investigate(req: InvestigateRequest):
    report = await agent.investigate(req.issue)
    return report.to_dict()


@app.get("/debug/health-check")
async def health_check():
    return await agent.health_check()


@app.get("/debug/recent-errors")
async def recent_errors():
    errors = await TOOL_DISPATCH["get_error_spans"](time_range_minutes=30)
    return errors


@app.get("/health")
def health():
    return {"status": "ok", "service": "ai-debugger"}
