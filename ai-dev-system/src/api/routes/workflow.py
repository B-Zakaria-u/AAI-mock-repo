"""Workflow routes — SRP: HTTP request/response handling only."""
import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.api.schemas.workflow import RunResponse, TicketRequest
from src.graph import build_graph

router = APIRouter(prefix="/run", tags=["Workflow"])


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

def _build_initial_state(ticket_text: str) -> dict:
    import os
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


async def _sse_stream(ticket_text: str) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted progress events as agent nodes complete."""
    graph = build_graph()
    for output in graph.stream(_build_initial_state(ticket_text)):
        node_name = list(output.keys())[0]
        node_state = output[node_name]
        yield f"data: [node:{node_name}] {node_state}\n\n"
        await asyncio.sleep(0)


# --------------------------------------------------------------------------- #
# Routes                                                                       #
# --------------------------------------------------------------------------- #

@router.post("", response_model=RunResponse)
async def run_workflow(request: TicketRequest) -> RunResponse:
    """
    Run the full agent graph synchronously.

    Streams the graph internally and returns the aggregated final state.
    """
    if not request.ticket_text.strip():
        raise HTTPException(status_code=422, detail="ticket_text must not be empty.")

    graph = build_graph()
    final_state: dict = {}
    for output in graph.stream(_build_initial_state(request.ticket_text)):
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


@router.post("/stream")
async def stream_workflow(request: TicketRequest) -> StreamingResponse:
    """
    Run the agent graph and stream progress as Server-Sent Events.

    Each SSE event reports the node name and its partial state.
    """
    if not request.ticket_text.strip():
        raise HTTPException(status_code=422, detail="ticket_text must not be empty.")

    return StreamingResponse(
        _sse_stream(request.ticket_text),
        media_type="text/event-stream",
    )
