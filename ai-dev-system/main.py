import os
import asyncio
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.graph import build_graph

load_dotenv()

app = FastAPI(
    title="AI Dev System",
    description="Multi-agent AI system that takes a development ticket, writes a spec, implements code, runs tests in a Docker sandbox, and opens a GitLab MR.",
    version="1.0.0",
)

# --------------------------------------------------------------------------- #
# Request / Response models                                                    #
# --------------------------------------------------------------------------- #

class TicketRequest(BaseModel):
    ticket_text: str


class RunResponse(BaseModel):
    spec: str
    spec_feedback: str
    test_output: str
    tests_passed: bool
    pr_url: str
    iteration_count: int


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

def _build_initial_state(ticket_text: str) -> dict:
    os.makedirs("workspace", exist_ok=True)
    return {
        "ticket_text": ticket_text,
        "spec": "",
        "spec_feedback": "",
        "test_output": "",
        "tests_passed": False,
        "pr_url": "",
        "iteration_count": 0,
    }


async def _stream_graph(ticket_text: str) -> AsyncGenerator[str, None]:
    """Runs the LangGraph workflow and yields SSE-formatted progress events."""
    graph = build_graph()
    initial_state = _build_initial_state(ticket_text)

    for output in graph.stream(initial_state):
        node_name = list(output.keys())[0]
        node_state = output[node_name]
        yield f"data: [node:{node_name}] {node_state}\n\n"
        await asyncio.sleep(0)  # yield control back to the event loop


# --------------------------------------------------------------------------- #
# Routes                                                                       #
# --------------------------------------------------------------------------- #

@app.get("/health", tags=["Ops"])
async def health_check():
    """Returns the service health status."""
    return {"status": "ok"}


@app.post("/run", response_model=RunResponse, tags=["Workflow"])
async def run_workflow(request: TicketRequest):
    """
    Accepts a development ticket and runs the full multi-agent workflow
    synchronously, returning the final graph state on completion.
    """
    if not request.ticket_text.strip():
        raise HTTPException(status_code=422, detail="ticket_text must not be empty.")

    graph = build_graph()
    initial_state = _build_initial_state(request.ticket_text)

    # Collect and return aggregate final state
    final_state: dict = {}
    for output in graph.stream(initial_state):
        for node_state in output.values():
            final_state.update(node_state)

    return RunResponse(
        spec=final_state.get("spec", ""),
        spec_feedback=final_state.get("spec_feedback", ""),
        test_output=final_state.get("test_output", ""),
        tests_passed=final_state.get("tests_passed", False),
        pr_url=final_state.get("pr_url", ""),
        iteration_count=final_state.get("iteration_count", 0),
    )


@app.post("/run/stream", tags=["Workflow"])
async def stream_workflow(request: TicketRequest):
    """
    Accepts a development ticket and streams agent node progress as
    Server-Sent Events (SSE). Each event reports the completing node name
    and its output state.
    """
    if not request.ticket_text.strip():
        raise HTTPException(status_code=422, detail="ticket_text must not be empty.")

    return StreamingResponse(
        _stream_graph(request.ticket_text),
        media_type="text/event-stream",
    )


# --------------------------------------------------------------------------- #
# Dev server entry point                                                       #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
