from src.state import GraphState
from src.llm_config import get_llm
from src.tools.ast_tools import get_ast_tools
from src.tools.graph_rag_tools import get_graph_rag_tools
from langchain_core.messages import SystemMessage, HumanMessage
import os


def validator_agent_node(state: GraphState) -> dict:
    """
    Validates the generated technical specification against completeness criteria
    and the existing codebase structure (via AST + GraphRAG).
    Flags naming collisions with existing symbols and missing implementation details.
    """
    llm = get_llm()
    spec = state.get("spec", "")

    # Build tools for codebase-awareness
    workspace_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "workspace")
    )
    ast_tools = get_ast_tools()
    graph_rag_tools = get_graph_rag_tools()
    all_tools = ast_tools + graph_rag_tools
    llm_with_tools = llm.bind_tools(all_tools)

    # ------------------------------------------------------------------ #
    # Pass 1: LLM inspects the workspace graph to gather codebase context #
    # ------------------------------------------------------------------ #
    inspect_messages = [
        SystemMessage(content=(
            "You are an expert technical reviewer with access to code-analysis tools.\n"
            "Before reviewing a specification, call `summarise_code_graph` on the workspace "
            "to understand what already exists, then call `query_code_graph` for key terms "
            "from the spec to check for naming collisions or missing dependencies."
        )),
        HumanMessage(content=(
            f"Workspace path: {workspace_dir}\n"
            f"Specification to review:\n{spec}\n\n"
            "Use your tools to inspect the workspace and gather context."
        ))
    ]

    inspection_response = llm_with_tools.invoke(inspect_messages)

    # Execute any tool calls the LLM requests during inspection
    tool_results: list[str] = []
    if hasattr(inspection_response, "tool_calls") and inspection_response.tool_calls:
        for tool_call in inspection_response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            for t in all_tools:
                if t.name == tool_name:
                    result = t.invoke(tool_args)
                    tool_results.append(f"[{tool_name} result]:\n{result}")
    else:
        tool_results = ["No workspace tools were called — proceeding with spec-only review."]

    # --------------------------------------------------------- #
    # Pass 2: Final VALID / feedback verdict                     #
    # --------------------------------------------------------- #
    verdict_prompt = (
        "Review the technical specification below. Validate if it is complete and technically sound.\n"
        "Consider any naming collisions or gaps discovered in the workspace analysis above.\n"
        "If it is fully valid, respond with EXACTLY 'VALID'.\n"
        "If it needs changes, provide specific actionable feedback — do NOT say VALID.\n\n"
        f"Specification to review:\n{spec}\n\n"
        f"Workspace analysis results:\n" + "\n".join(tool_results)
    )

    messages = [
        SystemMessage(content=(
            "You are an expert technical reviewer. "
            "Your final answer must be either VALID or specific actionable feedback."
        )),
        HumanMessage(content=verdict_prompt)
    ]

    response = llm.invoke(messages)
    content = response.content.strip()

    # Handle the 'VALID' keyword precisely
    if content.upper().startswith("VALID"):
        return {"spec_feedback": "VALID"}
    else:
        return {"spec_feedback": content}
